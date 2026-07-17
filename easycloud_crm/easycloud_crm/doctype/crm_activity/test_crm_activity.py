# Copyright (c) 2026, inzi and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestCRMActivity(FrappeTestCase):
	def test_requires_lead_or_deal(self):
		activity = frappe.get_doc(
			{
				"doctype": "CRM Activity",
				"activity_type": "Note",
				"notes": "ZZTEST no lead or deal",
			}
		)
		self.assertRaises(frappe.ValidationError, activity.insert, ignore_permissions=True)

	def test_update_deal_last_contacted_does_not_regress(self):
		lead = frappe.get_doc(
			{
				"doctype": "Lead",
				"lead_name": "ZZTEST Activity Co",
				"company_name": "ZZTEST Activity Co",
			}
		)
		lead.insert(ignore_permissions=True)

		deal = frappe.get_doc(
			{
				"doctype": "Deal",
				"deal_name": "ZZTEST Activity Deal",
				"lead": lead.name,
			}
		)
		deal.insert(ignore_permissions=True)

		newer = frappe.get_doc(
			{
				"doctype": "CRM Activity",
				"activity_type": "Call",
				"deal": deal.name,
				"date": "2026-07-15 10:00:00",
			}
		)
		newer.insert(ignore_permissions=True)
		self.assertEqual(
			str(frappe.db.get_value("Deal", deal.name, "last_contacted_on")), "2026-07-15 10:00:00"
		)

		older = frappe.get_doc(
			{
				"doctype": "CRM Activity",
				"activity_type": "Note",
				"deal": deal.name,
				"date": "2026-07-01 09:00:00",
			}
		)
		older.insert(ignore_permissions=True)
		self.assertEqual(
			str(frappe.db.get_value("Deal", deal.name, "last_contacted_on")), "2026-07-15 10:00:00"
		)
