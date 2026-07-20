# ==============================================================================
# easycloud_crm/meta_leads.py
#
# Turns a Meta (Facebook/Instagram) Lead Ads submission into a real Lead
# record in this CRM. This file does NOT get called by a user clicking
# anything -- it's triggered automatically, in the background, by
# api.py's meta_lead_webhook() every time Meta notifies us of a new lead
# (see api.py's _handle_meta_webhook_notification, which calls
# process_meta_lead() below via frappe.enqueue).
#
# THE FULL JOURNEY OF ONE LEAD, START TO FINISH:
#   1. Someone fills out a lead form on Facebook/Instagram.
#   2. Meta POSTs to our webhook (api.py) with just an ID, not the answers.
#   3. api.py hands off to process_meta_lead() below (this file), which
#      calls Meta's Graph API to fetch the actual answers using that ID.
#   4. Meta's answers come back as a flat list of {question, answer} pairs,
#      keyed by Meta's own internal question names (e.g.
#      "which_industry_does_your_business_belong_to?") -- not our field
#      names. map_field_data_to_lead() below translates between the two.
#   5. Three of Meta's answers are coarse text "buckets" (e.g. "51_-_100"
#      employees, "above_₹500_cr" revenue) that don't match our standard
#      Lead fields' expected formats -- the three small converter functions
#      near the bottom of this file clean those up.
#   6. A real Lead document gets created with everything mapped and cleaned.
# ==============================================================================

import re

import frappe
import requests

GRAPH_API_VERSION = "v19.0"

# Meta's own internal field/question names (left side) mapped to the Lead
# doctype's actual fieldnames (right side). Anything from Meta NOT listed
# here is silently ignored -- Meta's forms can include arbitrary questions we
# don't care about, and we only want the ones we know what to do with.
#
# The three fieldnames starting with an underscore (_meta_..._raw) are NOT
# real Lead fields -- they're temporary holding names. Meta's raw text for
# industry/employee-count/revenue doesn't match the format our actual Lead
# fields expect, so map_field_data_to_lead() stashes the raw text under these
# throwaway keys first, then _apply_bucketed_field_conversions() (below)
# converts each one into its real field (industry / no_of_employees /
# annual_revenue) and removes the throwaway key.
FIELD_MAP = {
	"full_name": "lead_name",
	"company_name": "company_name",
	"email": "email_id",
	"work_email_address": "email_id",  # some of Meta's form templates use this name instead of plain "email"
	"phone": "mobile_no",
	"phone_number": "mobile_no",  # same idea -- Meta isn't consistent about which name a given form uses
	"which_industry_does_your_business_belong_to?": "_meta_industry_raw",
	"which_erp_are_you_currently_using?": "current_erp",
	"number_of_employees_at_your_company?": "_meta_employee_count_raw",
	"you_company's_annual_revenue": "_meta_annual_revenue_raw",
}


def process_meta_lead(leadgen_id, form_id=None, ad_id=None, created_time=None):
	"""The entry point for this whole file -- runs in a background worker
	(see api.py's frappe.enqueue call). Fetches one lead's real answers from
	Meta's Graph API using its ID, and creates a Lead record from them.

	leadgen_id: Meta's unique ID for this specific lead submission -- this is
	            ALL Meta's webhook notification actually contains; everything
	            else has to be looked up using it.
	form_id / ad_id: which Lead Ad form/ad this came from, purely for our own
	            record-keeping (stored in the Lead's `source_detail` field).
	created_time: when Meta says the lead was submitted (may differ slightly
	            from when our webhook processes it, especially if Meta
	            retries a delayed delivery).
	"""
	# De-duplication guard: Meta's webhooks are "at-least-once" delivery --
	# it's normal and expected for the same notification to arrive more than
	# once (e.g. if our webhook was briefly slow to respond and Meta
	# retried). Without this check, a replay would create a second, duplicate
	# Lead for the same person. meta_leadgen_id is a custom field we added
	# specifically to make this check possible (see hooks.py's fixtures).
	if frappe.db.exists("Lead", {"meta_leadgen_id": leadgen_id}):
		return

	# meta_access_token is a long-lived Page access token from Meta's
	# developer dashboard, stored only in site_config.json (never in git --
	# whoever holds this token can read every lead your Meta ad account
	# collects). Graph API calls authenticate via a plain Bearer header.
	access_token = frappe.conf.get("meta_access_token")
	response = requests.get(
		f"https://graph.facebook.com/{GRAPH_API_VERSION}/{leadgen_id}",
		headers={"Authorization": f"Bearer {access_token}"},
		timeout=30,
	)
	response.raise_for_status()
	# Meta's response shape is `{"field_data": [{"name": "...", "values": ["..."]}]}`
	# -- a flat list of question/answer pairs, in whatever order the person
	# filled out the form fields.
	field_data = response.json().get("field_data", [])

	lead_values = map_field_data_to_lead(field_data)
	lead_values["meta_leadgen_id"] = leadgen_id  # store the ID so the de-dupe check above works for any future replay
	lead_values["source"] = "Meta Ads"  # sets the Lead Source dropdown, see hooks.py's fixtures for this option
	lead_values["source_detail"] = _build_source_detail(form_id, ad_id)
	if created_time:
		# Meta sends an ISO datetime string; Lead's `source_received_date`
		# field only cares about the date part, not the exact time.
		lead_values["source_received_date"] = frappe.utils.get_datetime(created_time).date()

	# {"doctype": "Lead", **lead_values} builds the dict Frappe needs to
	# construct a new document: "doctype" tells it what kind of record this
	# is, and the ** spreads every mapped field (lead_name, email_id, ...)
	# in alongside it. ignore_permissions=True is needed because this runs
	# in a background worker with no logged-in user attached to check
	# permissions against -- there's no "user" here to grant or deny.
	lead = frappe.get_doc({"doctype": "Lead", **lead_values})
	lead.insert(ignore_permissions=True)
	return lead.name


def map_field_data_to_lead(field_data):
	"""Converts Meta's raw field_data list into a dict of {Lead fieldname: value},
	ready to build a Lead document from. Exposed as its own function (rather
	than being inlined into process_meta_lead) so it can be unit-tested
	without needing a real network call to Meta or a real database -- see
	test_meta_leads.py.
	"""
	values = {}
	for entry in field_data:
		fieldname = FIELD_MAP.get(entry.get("name"))
		if not fieldname:
			continue  # a question we don't recognise/care about -- skip it
		entry_values = entry.get("values") or []
		if not entry_values or fieldname in values:
			# Skip empty answers, and skip if we've ALREADY filled this
			# fieldname from an earlier entry (e.g. both "email" and
			# "work_email_address" map to the same email_id field --
			# whichever one appears FIRST in Meta's list wins, later
			# duplicates are ignored rather than overwriting it).
			continue
		value = entry_values[0]  # Meta wraps every answer in a list even though these questions only ever have one answer
		if fieldname == "mobile_no" and value.startswith("p:"):
			# Meta prefixes phone numbers with "p:" (their own internal
			# marker for "this is a phone-type answer") -- strip it so we
			# store a clean, dialable number.
			value = value[2:]
		values[fieldname] = value

	return _apply_bucketed_field_conversions(values)


def _apply_bucketed_field_conversions(values):
	"""Takes the raw, Meta-flavoured text sitting under the three throwaway
	_meta_..._raw keys (see FIELD_MAP's comment above) and converts each into
	the real Lead field it belongs in, using the small helper functions
	below. Mutates and returns the same `values` dict map_field_data_to_lead
	was building.
	"""
	# Industry: Meta sends free text like "retail_&_distribution". Lead's
	# real `industry` field is a Link to the Industry Type doctype (a fixed
	# list of proper doctype records, not free text) -- so we look up (or
	# create, if this is a brand new industry we've never seen from Meta
	# before) a matching Industry Type record and link to it.
	industry_raw = values.pop("_meta_industry_raw", None)
	if industry_raw:
		values["industry"] = get_or_create_industry_type(industry_raw)

	# Employee count: Meta sends underscore-separated ranges like
	# "51_-_100". Lead's real `no_of_employees` field is a Select whose
	# options use plain hyphens ("51-100") -- see hooks.py's fixtures for
	# the Property Setter that expanded this Select's options to match every
	# bucket Meta's forms actually use.
	employee_raw = values.pop("_meta_employee_count_raw", None)
	if employee_raw:
		values["no_of_employees"] = normalize_employee_bucket(employee_raw)

	# Annual revenue: Meta sends a RANGE as text (e.g. "₹100–500_cr" or
	# "above_₹500_cr"), but Lead's real `annual_revenue` field is a plain
	# Currency number, not a range. We can't store a range in a number
	# field, so by agreed convention we store the LOWER BOUND of the range,
	# in Crores (e.g. "₹100–500_cr" -> 100). If the text genuinely doesn't
	# contain a parseable number, we leave the field unset rather than
	# guessing.
	revenue_raw = values.pop("_meta_annual_revenue_raw", None)
	if revenue_raw:
		lower_bound = parse_revenue_lower_bound_in_cr(revenue_raw)
		if lower_bound is not None:
			values["annual_revenue"] = lower_bound

	return values


def prettify_bucket_label(raw):
	"""'retail_&_distribution' -> 'Retail & Distribution'

	Turns Meta's underscore-separated, all-lowercase text into a normal,
	human-looking title. Used for both Industry names below. Every word
	gets capitalised except a bare "&", which gets upper-cased instead of
	capitalised (capitalize() on a single punctuation character would just
	leave it as "&" anyway -- the special case exists so this reads
	correctly even if a future bucket used some other short connector word).
	"""
	words = raw.replace("_", " ").split()
	return " ".join(w.upper() if w == "&" else w.capitalize() for w in words)


def get_or_create_industry_type(raw_industry):
	"""Looks up an Industry Type record matching Meta's raw industry text,
	creating one on the fly if this is the first time we've seen it. This
	means the list of Industry Types in this CRM grows organically as new
	kinds of businesses fill out the Meta Ads form -- nobody has to
	pre-populate every possible industry in advance.
	"""
	name = prettify_bucket_label(raw_industry)
	if not frappe.db.exists("Industry Type", name):
		# Industry Type's autoname is "field:industry" -- meaning the
		# record's own ID literally IS this "industry" value (no separate
		# auto-generated ID), so this insert both creates the record and
		# fixes its name in one step.
		frappe.get_doc({"doctype": "Industry Type", "industry": name}).insert(ignore_permissions=True)
	return name


def normalize_employee_bucket(raw_bucket):
	"""'101_-_200' -> '101-200'"""
	return raw_bucket.replace("_", "")


def parse_revenue_lower_bound_in_cr(raw_bucket):
	"""'₹100–500_cr' -> 100.0, 'above_₹500_cr' -> 500.0 (lower bound, in Cr)

	Strips Meta's currency/unit decoration down to plain numbers, then grabs
	the FIRST number in whatever's left -- which is always the lower bound
	of the range, whether the text is a normal "100–500" range or an
	open-ended "above_500" one (after stripping the "above_" prefix, "500"
	becomes the only, and therefore first, number).
	"""
	cleaned = raw_bucket.replace("₹", "").replace("_cr", "").replace("cr", "")
	if cleaned.lower().startswith("above_"):
		cleaned = cleaned[len("above_") :]
	# Matches one or more digits, allowing comma thousands-separators
	# (e.g. "1,000") -- takes just the FIRST match, which is always the
	# lower/only bound once "above_" has already been stripped above.
	first_number = re.search(r"[\d,]+", cleaned)
	if not first_number:
		return None  # text we didn't expect/can't parse -- better to leave the field blank than guess wrong
	return float(first_number.group().replace(",", ""))


def _build_source_detail(form_id, ad_id):
	"""Builds a short human-readable string like "ad:123 form:456" for
	Lead's `source_detail` field, so anyone looking at a Meta-sourced Lead
	can trace it back to exactly which ad and form produced it. Returns
	None (not an empty string) when both IDs are missing, so the field is
	left genuinely blank rather than showing an empty string in the UI.
	"""
	parts = []
	if ad_id:
		parts.append(f"ad:{ad_id}")
	if form_id:
		parts.append(f"form:{form_id}")
	return " ".join(parts) or None
