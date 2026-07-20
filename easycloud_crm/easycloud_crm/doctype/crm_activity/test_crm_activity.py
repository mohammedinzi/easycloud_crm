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

	def test_customer_only_link_is_valid(self):
		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "ZZTEST Activity Customer",
				"customer_type": "Company",
			}
		)
		customer.insert(ignore_permissions=True)

		activity = frappe.get_doc(
			{
				"doctype": "CRM Activity",
				"activity_type": "Note",
				"customer": customer.name,
				"notes": "ZZTEST customer-only activity",
			}
		)
		activity.insert(ignore_permissions=True)
		self.assertTrue(activity.name)

	def test_contact_only_link_is_valid(self):
		contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "ZZTEST Activity Contact",
			}
		)
		contact.insert(ignore_permissions=True)

		activity = frappe.get_doc(
			{
				"doctype": "CRM Activity",
				"activity_type": "Note",
				"contact": contact.name,
				"notes": "ZZTEST contact-only activity",
			}
		)
		activity.insert(ignore_permissions=True)
		self.assertTrue(activity.name)

	def test_activity_title_reflects_lead_source(self):
		lead = frappe.get_doc(
			{
				"doctype": "Lead",
				"lead_name": "ZZTEST Title Lead",
				"company_name": "ZZTEST Title Co",
			}
		)
		lead.insert(ignore_permissions=True)

		activity = frappe.get_doc(
			{
				"doctype": "CRM Activity",
				"activity_type": "Note",
				"lead": lead.name,
				"notes": "ZZTEST lead title check",
			}
		)
		activity.insert(ignore_permissions=True)
		self.assertEqual(activity.activity_title, f"Lead: {lead.title}")

	def test_activity_title_reflects_deal_source(self):
		lead = frappe.get_doc(
			{
				"doctype": "Lead",
				"lead_name": "ZZTEST Title Deal Lead",
				"company_name": "ZZTEST Title Deal Co",
			}
		)
		lead.insert(ignore_permissions=True)

		deal = frappe.get_doc(
			{
				"doctype": "Deal",
				"deal_name": "ZZTEST Title Deal",
				"lead": lead.name,
			}
		)
		deal.insert(ignore_permissions=True)

		activity = frappe.get_doc(
			{
				"doctype": "CRM Activity",
				"activity_type": "Call",
				"deal": deal.name,
				"notes": "ZZTEST deal title check",
			}
		)
		activity.insert(ignore_permissions=True)
		self.assertEqual(activity.activity_title, "Deal: ZZTEST Title Deal")

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
