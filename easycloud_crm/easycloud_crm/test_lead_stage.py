# Copyright (c) 2026, inzi and Contributors
# See license.txt

# ==============================================================================
# easycloud_crm/test_lead_stage.py -- automated tests for lead.py's
# validate()/on_update() logic (the Lead pipeline and its auto-Deal-creation
# behaviour). Lives at the app's top level (not inside a doctype folder)
# because lead.py itself lives there too -- Lead is a STANDARD erpnext
# doctype we extend, not one we own, so there's no doctype/lead/ folder of
# ours to put this next to. See test_deal.py for the FrappeTestCase /
# automatic-rollback pattern shared by every test file in this app.
# ==============================================================================

import frappe
from frappe.tests.utils import FrappeTestCase


class TestLeadStage(FrappeTestCase):
	def make_lead(self, company_name):
		"""Shared setup helper, not a test itself (no "test_" prefix)."""
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
		"""The core behaviour of lead.py's on_update(): moving a Lead's
		stage to "Qualified" should auto-create exactly one Deal, named
		after the company, also starting at "Qualified". Goes through
		"Contacted" first deliberately -- this confirms the Deal only
		appears on the SPECIFIC transition into "Qualified", not just
		because the Lead exists.
		"""
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
		"""Confirms the has_value_changed("stage") guard in lead.py: saving
		an ALREADY-Qualified lead again (here, because some unrelated field
		like the phone number changed) must NOT create a second Deal.
		Without this guard, every single save of a Qualified lead would spam
		a new Deal.
		"""
		lead = self.make_lead("ZZTEST Stage Resave Co")
		lead.stage = "Qualified"
		lead.save(ignore_permissions=True)

		# no real transition this time -- has_value_changed("stage") should be False
		lead.mobile_no = "9999999999"
		lead.save(ignore_permissions=True)

		self.assertEqual(frappe.db.count("Deal", {"lead": lead.name}), 1)

	def test_second_engagement_after_won_creates_new_deal(self):
		"""Confirms lead.py's "only skip if an OPEN Deal exists" logic
		(rather than "skip if ANY Deal exists at all"): if the first Deal
		for this Lead was already Won, cycling the Lead back through
		Contacted -> Qualified again (e.g. the same customer coming back
		for repeat business) should create a SECOND, brand new Deal --
		while leaving the first, already-Won Deal completely untouched.
		"""
		lead = self.make_lead("ZZTEST Repeat Business Co")
		lead.stage = "Qualified"
		lead.save(ignore_permissions=True)

		first_deal_name = frappe.db.get_value("Deal", {"lead": lead.name})
		first_deal = frappe.get_doc("Deal", first_deal_name)
		first_deal.stage = "Won"
		first_deal.save(ignore_permissions=True)

		lead.reload()  # pick up whatever changed on the Lead's own record since we last loaded it, before mutating it again
		lead.stage = "Contacted"
		lead.save(ignore_permissions=True)
		lead.stage = "Qualified"
		lead.save(ignore_permissions=True)

		deals = frappe.get_all("Deal", filters={"lead": lead.name}, fields=["name", "stage"])
		self.assertEqual(len(deals), 2)

		first_deal.reload()
		self.assertEqual(first_deal.stage, "Won")  # the original Deal should be completely unaffected by this second cycle

	def test_do_not_contact_requires_reason(self):
		"""Confirms lead.py's validate() guard: setting stage to
		"Do Not Contact" with no reason given must be REJECTED, but the
		exact same change WITH a reason attached must be ACCEPTED.
		"""
		lead = self.make_lead("ZZTEST No Reason Co")
		lead.stage = "Do Not Contact"
		self.assertRaises(frappe.ValidationError, lead.save, ignore_permissions=True)

		lead.reload()  # the failed save above didn't persist -- reload to get back to a clean, saved starting point
		lead.stage = "Do Not Contact"
		lead.do_not_contact_reason = "Not Interested"
		lead.save(ignore_permissions=True)
		lead.reload()
		self.assertEqual(lead.stage, "Do Not Contact")
