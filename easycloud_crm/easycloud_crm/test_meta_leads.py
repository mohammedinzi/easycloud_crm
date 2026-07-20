# Copyright (c) 2026, inzi and Contributors
# See license.txt

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
	def test_maps_known_fields(self):
		values = map_field_data_to_lead(SAMPLE_FIELD_DATA)

		self.assertEqual(values["lead_name"], "Jane Doe")
		self.assertEqual(values["company_name"], "ZZTEST Scoops Ice Cream")
		self.assertEqual(values["email_id"], "jane@zztestscoops.example")
		self.assertEqual(values["industry"], "Food & Beverage")
		self.assertEqual(values["current_erp"], "None")
		self.assertEqual(values["no_of_employees"], "51-100")
		self.assertEqual(values["annual_revenue"], 500.0)
		self.assertNotIn("some_unmapped_question", values)

	def test_prettify_bucket_label(self):
		self.assertEqual(prettify_bucket_label("retail_&_distribution"), "Retail & Distribution")

	def test_normalize_employee_bucket(self):
		self.assertEqual(normalize_employee_bucket("101_-_200"), "101-200")

	def test_parse_revenue_lower_bound_handles_range(self):
		self.assertEqual(parse_revenue_lower_bound_in_cr("₹100–500_cr"), 100.0)

	def test_parse_revenue_lower_bound_handles_above(self):
		self.assertEqual(parse_revenue_lower_bound_in_cr("above_₹500_cr"), 500.0)

	def test_strips_meta_phone_prefix(self):
		values = map_field_data_to_lead(SAMPLE_FIELD_DATA)
		self.assertEqual(values["mobile_no"], "+919999999999")

	def test_phone_number_field_name_also_maps_to_mobile_no(self):
		field_data = [{"name": "phone_number", "values": ["+919888888888"]}]
		values = map_field_data_to_lead(field_data)
		self.assertEqual(values["mobile_no"], "+919888888888")

	def test_email_falls_back_to_work_email_field(self):
		field_data = [
			{"name": "full_name", "values": ["John Roe"]},
			{"name": "work_email_address", "values": ["john@zztest.example"]},
		]
		values = map_field_data_to_lead(field_data)
		self.assertEqual(values["email_id"], "john@zztest.example")

	def test_first_matching_field_wins_on_duplicate_target(self):
		field_data = [
			{"name": "email", "values": ["primary@zztest.example"]},
			{"name": "work_email_address", "values": ["secondary@zztest.example"]},
		]
		values = map_field_data_to_lead(field_data)
		self.assertEqual(values["email_id"], "primary@zztest.example")

	def test_ignores_entries_with_no_values(self):
		field_data = [{"name": "full_name", "values": []}]
		values = map_field_data_to_lead(field_data)
		self.assertNotIn("lead_name", values)

	def test_source_detail_combines_ad_and_form(self):
		self.assertEqual(_build_source_detail("f:123", "ag:456"), "ad:ag:456 form:f:123")

	def test_source_detail_none_when_nothing_available(self):
		self.assertIsNone(_build_source_detail(None, None))


def _set_conf(key, value):
	original = frappe.conf.get(key)
	frappe.conf[key] = value
	return original


class TestMetaWebhookSignature(FrappeTestCase):
	def setUp(self):
		self._original_app_secret = _set_conf("meta_app_secret", "ZZTEST-secret")
		self.addCleanup(lambda: _set_conf("meta_app_secret", self._original_app_secret))

	def test_accepts_correctly_signed_payload(self):
		import hashlib
		import hmac

		body = b'{"leadgen_id": "123"}'
		signature = "sha256=" + hmac.new(b"ZZTEST-secret", body, hashlib.sha256).hexdigest()

		self.assertTrue(_is_valid_meta_signature(body, signature))

	def test_rejects_tampered_payload(self):
		import hashlib
		import hmac

		body = b'{"leadgen_id": "123"}'
		signature = "sha256=" + hmac.new(b"ZZTEST-secret", b'{"leadgen_id": "999"}', hashlib.sha256).hexdigest()

		self.assertFalse(_is_valid_meta_signature(body, signature))

	def test_rejects_missing_signature_header(self):
		self.assertFalse(_is_valid_meta_signature(b"{}", None))


class TestProcessMetaLead(FrappeTestCase):
	def setUp(self):
		self._original_token = _set_conf("meta_access_token", "ZZTEST-token")
		self.addCleanup(lambda: _set_conf("meta_access_token", self._original_token))

	@patch("easycloud_crm.meta_leads.requests.get")
	def test_creates_lead_and_dedupes_on_replay(self, mock_get):
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

		self.assertIsNone(result)
		self.assertEqual(frappe.db.count("Lead", {"meta_leadgen_id": "ZZTEST-leadgen-1"}), 1)
