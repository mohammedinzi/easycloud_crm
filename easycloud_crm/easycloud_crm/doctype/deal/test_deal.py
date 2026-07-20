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
				"stage": "Qualified",
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
				"stage": "Qualified",
			}
		)
		deal.insert(ignore_permissions=True)

		deal.stage = "Won"
		deal.save(ignore_permissions=True)
		deal.reload()

		self.assertEqual(deal.customer, existing_customer.name)
		self.assertEqual(frappe.db.count("Customer", {"customer_name": company_name}), 1)

	def test_stage_change_creates_stage_log(self):
		lead = self.make_lead("ZZTEST Stage Log Co")
		deal = frappe.get_doc(
			{
				"doctype": "Deal",
				"deal_name": "ZZTEST Stage Log Deal",
				"lead": lead.name,
				"stage": "Qualified",
			}
		)
		deal.insert(ignore_permissions=True)

		deal.stage = "Proposal Sent"
		deal.save(ignore_permissions=True)

		deal.stage = "Demo Given"
		deal.save(ignore_permissions=True)

		logs = frappe.get_all(
			"Deal Stage Log", filters={"deal": deal.name}, fields=["stage"], order_by="changed_on asc"
		)
		self.assertEqual([l.stage for l in logs], ["Qualified", "Proposal Sent", "Demo Given"])

	def test_resaving_without_stage_change_does_not_duplicate_log(self):
		lead = self.make_lead("ZZTEST Stage Log Resave Co")
		deal = frappe.get_doc(
			{
				"doctype": "Deal",
				"deal_name": "ZZTEST Stage Log Resave Deal",
				"lead": lead.name,
				"stage": "Qualified",
			}
		)
		deal.insert(ignore_permissions=True)

		deal.notes = "just touching the doc"
		deal.save(ignore_permissions=True)

		self.assertEqual(frappe.db.count("Deal Stage Log", {"deal": deal.name}), 1)
