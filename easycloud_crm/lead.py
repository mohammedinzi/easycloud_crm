# ==============================================================================
# easycloud_crm/lead.py
#
# Custom behaviour bolted onto the STANDARD "Lead" doctype (Lead itself is
# defined by erpnext, in erpnext/crm/doctype/lead/lead.json -- we never touch
# that file directly). Frappe calls the two functions below automatically;
# see the "doc_events" section of hooks.py for exactly when/why.
#
# THE BIG PICTURE this file implements: every Lead in this CRM moves through
# our own pipeline via its "stage" field --
#   New -> Contacted -> Qualified -> (Deal created automatically) -> Won/Lost
#                     \-> Do Not Contact (dead end, requires a reason)
# "stage" is a custom field we added via a fixture (see hooks.py's fixtures
# list, and easycloud_crm/fixtures/custom_field.json for its Select options).
# ==============================================================================

import frappe


def validate(doc, method=None):
	"""Runs right before a Lead is saved. Raising an error here blocks the save.

	doc: the Lead document that's about to be saved (Frappe passes this in
	     automatically -- it's the record with all its field values on it).
	method: unused here, but Frappe always passes the hook name as a second
	        argument, so this parameter has to exist even though we ignore it.
	"""
	# Business rule: you can't silently mark a Lead as "Do Not Contact" --
	# the team needs to know WHY (Not Interested? Bad Timing? etc.) so this
	# information is useful later. "do_not_contact_reason" is a custom Select
	# field that only becomes visible on the form once stage is set to
	# "Do Not Contact" (see its "depends_on" in fixtures/custom_field.json).
	if doc.stage == "Do Not Contact" and not doc.do_not_contact_reason:
		frappe.throw("Select a reason before marking this Lead as Do Not Contact.")

	if doc.is_new():
		warn_if_duplicate_contact(doc)


def warn_if_duplicate_contact(doc):
	"""Flags (but never blocks) a brand-new Lead that shares a phone number
	with an existing Lead. Deliberately a warning, not a frappe.throw --
	unlike "Do Not Contact needs a reason" above, this isn't a rule the
	computer can safely enforce: a rep might genuinely be creating a
	second, real opportunity for a past contact (e.g. a former customer
	coming back with a brand new inquiry). The goal is just making sure
	they SEE it before deciding, same reasoning already used for Deal's
	retarget_status field -- some judgment calls are for a human, not a
	validation rule.

	Phone only, deliberately NOT email: erpnext's own stock Lead controller
	(erpnext/crm/doctype/lead/lead.py) already has a check_email_id_is_unique()
	that hard-blocks a duplicate email outright (a frappe.throw, gated by a
	"CRM Settings" toggle) -- confirmed by hitting it directly while testing
	this. Duplicating that here would be redundant at best, and dead code
	at worst, since that native check runs first and would already have
	stopped the save before this ever got a chance to run. Phone numbers
	have no equivalent native check, which is the actual gap this closes.
	"""
	match = None
	if doc.mobile_no:
		match = frappe.db.get_value("Lead", {"mobile_no": doc.mobile_no, "name": ["!=", doc.name]}, "name")

	if match:
		match_link = frappe.utils.get_link_to_form("Lead", match)
		frappe.msgprint(
			f"Possible duplicate: {match_link} already has this phone number.",
			title="Possible Duplicate Lead",
			indicator="orange",
		)


def on_update(doc, method=None):
	"""Runs right after a Lead is successfully saved.

	Two independent jobs happen here:
	  1. Keep a timestamp of the last time `stage` actually changed.
	  2. The moment a Lead reaches "Qualified", automatically create a Deal
	     for it -- this is what turns "someone we're talking to" into
	     "an active sales opportunity we're tracking numbers for".
	"""
	# --- Job 1: track when the stage last changed --------------------------
	# has_value_changed() compares the value on `doc` right now against what
	# was in the database before this save -- True only on the save where the
	# field actually moved to a new value, not on every save of this record.
	if doc.has_value_changed("stage"):
		# db_set() writes directly to the database and skips re-running
		# validate/on_update again (calling doc.save() here would recurse
		# back into this same on_update function). update_modified=False
		# means this silent timestamp update won't show up as "last edited"
		# in the UI -- from a user's point of view, nothing happened.
		doc.db_set("stage_changed_on", frappe.utils.now_datetime(), update_modified=False)

	# --- Job 2: auto-create a Deal when the Lead becomes Qualified ---------
	# Bail out immediately unless this save is the SPECIFIC moment the stage
	# became "Qualified" (not every save of an already-Qualified lead, and
	# not a save that changed some other field like the phone number).
	if doc.stage != "Qualified" or not doc.has_value_changed("stage"):
		return

	# Guard against duplicates: if this Lead already has an open Deal (one
	# that hasn't been Won or Lost yet), don't create a second one. This
	# matters because a Lead can bounce back to "Contacted" and forward to
	# "Qualified" again (e.g. after a Deal was Lost, they re-engage later) --
	# in THAT case we do want a new Deal, which is exactly why Won/Lost deals
	# are excluded from this check rather than checking "any Deal at all".
	open_deal_exists = frappe.db.exists("Deal", {"lead": doc.name, "stage": ["not in", ["Won", "Lost"]]})
	if open_deal_exists:
		return

	# Prefer the company name for the Deal's title; fall back to the
	# person's own name if we never captured a company (e.g. a solo/individual
	# lead with no organisation attached).
	company_name = doc.company_name or doc.lead_name

	# frappe.new_doc() builds an in-memory Deal document (not saved yet);
	# setting `.lead = doc.name` is what links this Deal back to this exact
	# Lead record (Deal's own "lead" field is a Link to Lead -- see
	# doctype/deal/deal.json). insert() is what actually writes it to the
	# database. ignore_permissions=True is needed because this code runs
	# as a side effect of saving a LEAD -- the user doing that save might not
	# individually have "create" rights on Deal, but they don't need to; this
	# is the system acting on their behalf, not them directly creating a Deal.
	deal = frappe.new_doc("Deal")
	deal.deal_name = company_name
	deal.lead = doc.name
	deal.stage = "Qualified"
	deal.insert(ignore_permissions=True)

	# A friendly on-screen confirmation so the person qualifying this Lead
	# immediately sees that a Deal now exists for it, instead of it being an
	# invisible background action they'd only discover later.
	frappe.msgprint(f"Deal created for {company_name}")
