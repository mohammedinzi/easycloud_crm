# Copyright (c) 2026, inzi and Contributors
# See license.txt

# ==============================================================================
# easycloud_crm/test_meta_leads.py -- automated tests for the whole Meta
# Lead Ads integration: api.py's webhook signature verification, and
# meta_leads.py's field-mapping/conversion logic. Split into three test
# classes, each covering one layer of the flow described at the top of
# meta_leads.py:
#   TestMetaLeadMapping     -- pure functions, no network/database needed
#   TestMetaWebhookSignature -- the HMAC signature check that guards api.py's webhook
#   TestProcessMetaLead      -- the full process_meta_lead() flow, with Meta's
#                                Graph API call mocked out (see below for why)
# ==============================================================================

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from easycloud_crm.api import _is_valid_meta_signature
from easycloud_crm.meta_leads import (
	_build_source_detail,
	map_field_data_to_lead,
	normalize_employee_bucket,
	parse_revenue_lower_bound_in_cr,
	prettify_bucket_label,
	process_meta_lead,
)

# A realistic stand-in for what Meta's Graph API actually returns for one
# lead -- shared across most tests below so each one doesn't have to build
# its own copy from scratch. Deliberately includes one entry
# ("some_unmapped_question") that ISN'T in meta_leads.py's FIELD_MAP, to
# double-check unknown questions get silently ignored rather than crashing
# or leaking into the mapped result.
SAMPLE_FIELD_DATA = [
	{"name": "full_name", "values": ["Jane Doe"]},
	{"name": "company_name", "values": ["ZZTEST Scoops Ice Cream"]},
	{"name": "email", "values": ["jane@zztestscoops.example"]},
	{"name": "phone", "values": ["p:+919999999999"]},
	{"name": "which_industry_does_your_business_belong_to?", "values": ["Food & Beverage"]},
	{"name": "which_erp_are_you_currently_using?", "values": ["None"]},
	{"name": "number_of_employees_at_your_company?", "values": ["51_-_100"]},
	{"name": "you_company's_annual_revenue", "values": ["above_₹500_cr"]},
	{"name": "some_unmapped_question", "values": ["ignore me"]},
]


class TestMetaLeadMapping(FrappeTestCase):
	"""Tests the pure data-transformation functions in meta_leads.py --
	none of these touch the network or need a real Meta account, since
	map_field_data_to_lead() and its helpers only operate on plain Python
	data structures passed straight in.
	"""

	def test_maps_known_fields(self):
		"""End-to-end check across every field FIELD_MAP knows about at
		once: confirms simple 1-to-1 mappings (lead_name, company_name,
		email_id, current_erp) AND the three "bucketed" conversions
		(industry/no_of_employees/annual_revenue) all come out correctly
		from one realistic payload, and the one unmapped question is
		dropped.
		"""
		values = map_field_data_to_lead(SAMPLE_FIELD_DATA)

		self.assertEqual(values["lead_name"], "Jane Doe")
		self.assertEqual(values["company_name"], "ZZTEST Scoops Ice Cream")
		self.assertEqual(values["email_id"], "jane@zztestscoops.example")
		self.assertEqual(values["industry"], "Food & Beverage")
		self.assertEqual(values["current_erp"], "None")
		self.assertEqual(values["no_of_employees"], "51-100")
		self.assertEqual(values["annual_revenue"], 500.0)  # "above_₹500_cr" -> lower bound 500.0, see parse_revenue_lower_bound_in_cr
		self.assertNotIn("some_unmapped_question", values)

	def test_prettify_bucket_label(self):
		self.assertEqual(prettify_bucket_label("retail_&_distribution"), "Retail & Distribution")

	def test_normalize_employee_bucket(self):
		self.assertEqual(normalize_employee_bucket("101_-_200"), "101-200")

	def test_parse_revenue_lower_bound_handles_range(self):
		"""A normal bounded range: "100–500" -> the LOWER bound, 100."""
		self.assertEqual(parse_revenue_lower_bound_in_cr("₹100–500_cr"), 100.0)

	def test_parse_revenue_lower_bound_handles_above(self):
		"""The open-ended "above X" case -- after stripping the "above_"
		prefix, the only number left (500) becomes the result, same as if
		it were the lower bound of a range.
		"""
		self.assertEqual(parse_revenue_lower_bound_in_cr("above_₹500_cr"), 500.0)

	def test_strips_meta_phone_prefix(self):
		"""Meta prefixes phone answers with "p:" -- confirms that gets
		stripped off, leaving just the dialable number.
		"""
		values = map_field_data_to_lead(SAMPLE_FIELD_DATA)
		self.assertEqual(values["mobile_no"], "+919999999999")

	def test_phone_number_field_name_also_maps_to_mobile_no(self):
		"""Meta isn't consistent about which question NAME a given form
		uses for a phone number -- confirms the alternate name
		"phone_number" (not just "phone") also lands in mobile_no.
		"""
		field_data = [{"name": "phone_number", "values": ["+919888888888"]}]
		values = map_field_data_to_lead(field_data)
		self.assertEqual(values["mobile_no"], "+919888888888")

	def test_email_falls_back_to_work_email_field(self):
		"""Same idea as the phone number test above, but for email --
		confirms "work_email_address" (Meta's alternate name) also maps
		to email_id when plain "email" isn't present.
		"""
		field_data = [
			{"name": "full_name", "values": ["John Roe"]},
			{"name": "work_email_address", "values": ["john@zztest.example"]},
		]
		values = map_field_data_to_lead(field_data)
		self.assertEqual(values["email_id"], "john@zztest.example")

	def test_first_matching_field_wins_on_duplicate_target(self):
		"""Both "email" and "work_email_address" map to the SAME Lead field
		(email_id) -- if a form somehow answers both questions, confirms
		whichever one appears FIRST in Meta's list wins, and the second one
		is silently ignored rather than overwriting it. Order matters here:
		"email" is listed before "work_email_address" in this test's input.
		"""
		field_data = [
			{"name": "email", "values": ["primary@zztest.example"]},
			{"name": "work_email_address", "values": ["secondary@zztest.example"]},
		]
		values = map_field_data_to_lead(field_data)
		self.assertEqual(values["email_id"], "primary@zztest.example")

	def test_ignores_entries_with_no_values(self):
		"""A question Meta lists but with an EMPTY answer (values: [])
		should be skipped entirely, not stored as a blank string.
		"""
		field_data = [{"name": "full_name", "values": []}]
		values = map_field_data_to_lead(field_data)
		self.assertNotIn("lead_name", values)

	def test_source_detail_combines_ad_and_form(self):
		self.assertEqual(_build_source_detail("f:123", "ag:456"), "ad:ag:456 form:f:123")

	def test_source_detail_none_when_nothing_available(self):
		"""When both IDs are missing, the result should be None (a genuinely
		empty field), not an empty string.
		"""
		self.assertIsNone(_build_source_detail(None, None))


def _set_conf(key, value):
	"""Small test helper: temporarily overrides one site_config.json-style
	setting (frappe.conf) for the duration of a test, and returns whatever
	value was there before so it can be restored afterwards (see setUp
	methods below, which pair this with self.addCleanup to guarantee the
	restore happens even if a test fails partway through).
	"""
	original = frappe.conf.get(key)
	frappe.conf[key] = value
	return original


class TestMetaWebhookSignature(FrappeTestCase):
	"""Tests api.py's _is_valid_meta_signature() -- the HMAC check that
	decides whether an incoming webhook POST genuinely came from Meta.
	"""

	def setUp(self):
		# Every test in this class needs a known, fixed "meta_app_secret" to
		# sign against -- using a fake ZZTEST secret here means these tests
		# never depend on (or risk leaking) the real production secret.
		self._original_app_secret = _set_conf("meta_app_secret", "ZZTEST-secret")
		self.addCleanup(lambda: _set_conf("meta_app_secret", self._original_app_secret))

	def test_accepts_correctly_signed_payload(self):
		import hashlib
		import hmac

		body = b'{"leadgen_id": "123"}'
		# Manually recreate exactly what Meta's servers would compute:
		# an HMAC-SHA256 of the raw body, using the shared secret.
		signature = "sha256=" + hmac.new(b"ZZTEST-secret", body, hashlib.sha256).hexdigest()

		self.assertTrue(_is_valid_meta_signature(body, signature))

	def test_rejects_tampered_payload(self):
		"""Signs one body but presents a DIFFERENT body to the checker --
		simulates a payload that was altered in transit (or a forgery
		attempt) after the signature was computed. Must be rejected.
		"""
		import hashlib
		import hmac

		body = b'{"leadgen_id": "123"}'
		signature = "sha256=" + hmac.new(b"ZZTEST-secret", b'{"leadgen_id": "999"}', hashlib.sha256).hexdigest()

		self.assertFalse(_is_valid_meta_signature(body, signature))

	def test_rejects_missing_signature_header(self):
		"""No signature at all (header is None) must fail closed, not be
		treated as "no signature to check, so allow it".
		"""
		self.assertFalse(_is_valid_meta_signature(b"{}", None))


class TestProcessMetaLead(FrappeTestCase):
	"""Tests process_meta_lead() end-to-end -- the ONE function that ties
	the whole file together: given just a leadgen_id, it should produce a
	real, correctly-populated Lead record.
	"""

	def setUp(self):
		self._original_token = _set_conf("meta_access_token", "ZZTEST-token")
		self.addCleanup(lambda: _set_conf("meta_access_token", self._original_token))

	@patch("easycloud_crm.meta_leads.requests.get")
	def test_creates_lead_and_dedupes_on_replay(self, mock_get):
		"""The `@patch` decorator replaces meta_leads.py's `requests.get`
		call with a fake that returns SAMPLE_FIELD_DATA instead of actually
		reaching out to Meta's real servers -- this test needs to run
		offline, repeatably, and without a real Meta account/access token,
		so mocking the ONE network call is what makes that possible while
		still exercising all the REAL mapping/insert logic around it.

		Covers two things in one test: (1) a fresh leadgen_id produces a
		correctly-populated Lead, and (2) processing that SAME leadgen_id
		again (simulating Meta re-delivering the same webhook notification,
		which is normal and expected) must NOT create a second, duplicate
		Lead -- see meta_leads.py's de-dupe guard at the top of
		process_meta_lead().
		"""
		mock_response = MagicMock()
		mock_response.json.return_value = {"field_data": SAMPLE_FIELD_DATA}
		mock_response.raise_for_status.return_value = None
		mock_get.return_value = mock_response

		lead_name = process_meta_lead(
			leadgen_id="ZZTEST-leadgen-1", form_id="f:1", ad_id="ag:1", created_time="2026-07-17T10:00:00+0000"
		)

		lead = frappe.get_doc("Lead", lead_name)
		self.assertEqual(lead.meta_leadgen_id, "ZZTEST-leadgen-1")
		self.assertEqual(lead.source, "Meta Ads")
		self.assertEqual(lead.company_name, "ZZTEST Scoops Ice Cream")
		self.assertEqual(lead.source_detail, "ad:ag:1 form:f:1")

		# a redelivered webhook for the same leadgen_id must not create a second Lead
		result = process_meta_lead(leadgen_id="ZZTEST-leadgen-1")

		self.assertIsNone(result)  # the de-dupe guard returns early with no value
		self.assertEqual(frappe.db.count("Lead", {"meta_leadgen_id": "ZZTEST-leadgen-1"}), 1)

	@patch("easycloud_crm.meta_leads.requests.get")
	def test_dedupes_same_person_with_a_different_leadgen_id(self, mock_get):
		"""The leadgen_id-based guard above only catches an exact replay of
		the SAME webhook notification. This covers the other case
		_find_existing_lead_by_contact exists for: the same person
		submitting the form again (a different ad, or just re-filling it
		out), which Meta gives a brand new leadgen_id -- confirms that
		still doesn't create a second Lead, since the email already
		matches an existing one.

		Uses its own field_data (not the shared SAMPLE_FIELD_DATA) with a
		email unique to this test -- FrappeTestCase shares one transaction
		across every test method in a class, so reusing SAMPLE_FIELD_DATA's
		email here would collide with the Lead test_creates_lead_and_dedupes_on_replay
		already created earlier in this same class, rather than testing
		what this test is actually meant to check.
		"""
		field_data = [
			{"name": "full_name", "values": ["ZZTEST John Repeat"]},
			{"name": "company_name", "values": ["ZZTEST Repeat Submission Co"]},
			{"name": "email", "values": ["zztest.repeat.submission@example.com"]},
		]
		mock_response = MagicMock()
		mock_response.json.return_value = {"field_data": field_data}
		mock_response.raise_for_status.return_value = None
		mock_get.return_value = mock_response

		first = process_meta_lead(leadgen_id="ZZTEST-leadgen-first")
		self.assertTrue(first)

		# same field_data (same email) but a completely different
		# leadgen_id -- the first guard alone wouldn't catch this
		second = process_meta_lead(leadgen_id="ZZTEST-leadgen-second")

		self.assertIsNone(second)
		self.assertEqual(frappe.db.count("Lead", {"email_id": "zztest.repeat.submission@example.com"}), 1)
