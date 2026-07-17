# Copyright (c) 2026, inzi and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestDeal(FrappeTestCase):
	def make_lead(self, company_name):
		lead = frappe.get_doc(
			{
				"doctype": "Lead",
				"lead_name": company_name,
				"company_name": company_name,
			}
		)
		lead.insert(ignore_permissions=True)
		return lead

	def test_won_creates_customer_only(self):
		lead = self.make_lead("ZZTEST Won Automation Co")
		deal = frappe.get_doc(
			{
				"doctype": "Deal",
				"deal_name": "ZZTEST Won Automation Deal",
				"lead": lead.name,
				"stage": "New",
			}
		)
		deal.insert(ignore_permissions=True)

		deal.stage = "Won"
		deal.save(ignore_permissions=True)
		deal.reload()

		self.assertTrue(frappe.db.exists("Customer", deal.customer))
		self.assertFalse(deal.project)
		self.assertEqual(frappe.db.count("Task", {"custom_deal": deal.name}), 0)

	def test_won_reuses_existing_customer(self):
		company_name = "ZZTEST Existing Customer Co"
		existing_customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": company_name,
				"customer_type": "Company",
			}
		)
		existing_customer.insert(ignore_permissions=True)

		lead = self.make_lead(company_name)
		deal = frappe.get_doc(
			{
				"doctype": "Deal",
				"deal_name": "ZZTEST Reuse Customer Deal",
				"lead": lead.name,
				"stage": "New",
			}
		)
		deal.insert(ignore_permissions=True)

		deal.stage = "Won"
		deal.save(ignore_permissions=True)
		deal.reload()

		self.assertEqual(deal.customer, existing_customer.name)
		self.assertEqual(frappe.db.count("Customer", {"customer_name": company_name}), 1)
