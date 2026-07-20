# Copyright (c) 2026, inzi and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestLeadStage(FrappeTestCase):
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

	def test_qualified_creates_deal(self):
		lead = self.make_lead("ZZTEST Stage Co")
		lead.stage = "Contacted"
		lead.save(ignore_permissions=True)
		lead.stage = "Qualified"
		lead.save(ignore_permissions=True)

		deals = frappe.get_all("Deal", filters={"lead": lead.name}, fields=["name", "stage", "deal_name"])
		self.assertEqual(len(deals), 1)
		self.assertEqual(deals[0].stage, "Qualified")
		self.assertEqual(deals[0].deal_name, "ZZTEST Stage Co")

	def test_resaving_at_qualified_does_not_duplicate(self):
		lead = self.make_lead("ZZTEST Stage Resave Co")
		lead.stage = "Qualified"
		lead.save(ignore_permissions=True)

		# no real transition this time -- has_value_changed("stage") should be False
		lead.mobile_no = "9999999999"
		lead.save(ignore_permissions=True)

		self.assertEqual(frappe.db.count("Deal", {"lead": lead.name}), 1)

	def test_second_engagement_after_won_creates_new_deal(self):
		lead = self.make_lead("ZZTEST Repeat Business Co")
		lead.stage = "Qualified"
		lead.save(ignore_permissions=True)

		first_deal_name = frappe.db.get_value("Deal", {"lead": lead.name})
		first_deal = frappe.get_doc("Deal", first_deal_name)
		first_deal.stage = "Won"
		first_deal.save(ignore_permissions=True)

		lead.reload()
		lead.stage = "Contacted"
		lead.save(ignore_permissions=True)
		lead.stage = "Qualified"
		lead.save(ignore_permissions=True)

		deals = frappe.get_all("Deal", filters={"lead": lead.name}, fields=["name", "stage"])
		self.assertEqual(len(deals), 2)

		first_deal.reload()
		self.assertEqual(first_deal.stage, "Won")

	def test_do_not_contact_requires_reason(self):
		lead = self.make_lead("ZZTEST No Reason Co")
		lead.stage = "Do Not Contact"
		self.assertRaises(frappe.ValidationError, lead.save, ignore_permissions=True)

		lead.reload()
		lead.stage = "Do Not Contact"
		lead.do_not_contact_reason = "Not Interested"
		lead.save(ignore_permissions=True)
		lead.reload()
		self.assertEqual(lead.stage, "Do Not Contact")
