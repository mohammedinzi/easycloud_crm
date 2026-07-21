# Copyright (c) 2026, inzi and Contributors
# See license.txt

# ==============================================================================
# doctype/deal/test_deal.py -- automated tests for deal.py's server-side
# logic (Won -> Customer conversion, and the Deal Stage Log history).
#
# HOW TO RUN JUST THIS FILE (from inside the backend container):
#   bench --site <site> set-config allow_tests true
#   bench --site <site> run-tests --module easycloud_crm.easycloud_crm.doctype.deal.test_deal
#   bench --site <site> set-config allow_tests false
#
# FrappeTestCase (which every test class in this app extends) wraps each
# test method in a database transaction that gets ROLLED BACK automatically
# when the test finishes -- so nothing created here (Leads, Deals,
# Customers, ...) is ever left behind in the real database, even though the
# code below calls real .insert()/.save() like it's touching production
# data. The "ZZTEST" prefix on every name is just a human convenience (so a
# person skimming the database mid-test-run, or debugging a failed rollback,
# can instantly recognise test data at a glance) -- it plays no role in the
# actual cleanup.
# ==============================================================================

import frappe
from frappe.tests.utils import FrappeTestCase

from easycloud_crm.easycloud_crm.doctype.deal.deal import get_default_customer_group


class TestDeal(FrappeTestCase):
	def make_lead(self, company_name):
		"""Small shared helper so every test below doesn't have to repeat
		the same 5 lines to get a Lead to attach a Deal to. Not a test
		itself -- doesn't start with "test_", so Frappe's test runner
		won't try to run it on its own.
		"""
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
		"""Confirms deal.py's convert_to_customer() fires when a Deal
		becomes Won, and ONLY creates a Customer -- this test's name says
		"only" because an earlier version of this app also auto-created a
		Project and a Task at this point; that behaviour was deliberately
		removed (see the "Remove Project dependency from Deal-Won
		automation" commit), and the two assertFalse/assertEqual lines below
		exist specifically to make sure that removed behaviour never
		silently comes back.
		"""
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
		deal.reload()  # pulls the record back from the database, so deal.customer reflects what db_set() actually wrote, not just in-memory state

		self.assertTrue(frappe.db.exists("Customer", deal.customer))
		self.assertFalse(deal.project)
		self.assertEqual(frappe.db.count("Task", {"custom_deal": deal.name}), 0)

	def test_won_reuses_existing_customer(self):
		"""Confirms the de-duplication guard in convert_to_customer(): if a
		Customer with this exact company name already exists, we link to
		THAT one instead of creating a confusing second Customer with the
		same name.
		"""
		company_name = "ZZTEST Existing Customer Co"
		existing_customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": company_name,
				"customer_type": "Company",
				# Same helper convert_to_customer() itself uses -- without this,
				# Customer creation depends on Selling Settings' own default
				# customer_group, which erpnext's own test setup
				# (erpnext.setup.utils.set_defaults_for_tests) deliberately
				# resets to the Customer Group tree's ROOT (a Group-type node)
				# before every test run -- Customer's controller correctly
				# rejects that, so this test needs a real leaf group of its own.
				"customer_group": get_default_customer_group(),
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
		# The real point of this assertion: still exactly ONE Customer with
		# this name in the database -- proves we reused it rather than
		# creating a duplicate.
		self.assertEqual(frappe.db.count("Customer", {"customer_name": company_name}), 1)

	def test_stage_change_creates_stage_log(self):
		"""Confirms every real stage transition writes one Deal Stage Log
		row, in order -- this is what powers the Stage Timeline tab in
		deal.js's render_deal_timeline(). Note the very FIRST log entry
		("Qualified") comes from the Deal's own insert() above, not from an
		explicit stage change -- because has_value_changed("stage") is also
		True on a brand-new document's first save (there's no "previous"
		value to compare against, so any set value counts as "changed").
		"""
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
		"""Confirms the has_value_changed("stage") guard in deal.py's
		on_update() actually does something -- saving the Deal again with
		some UNRELATED field changed (notes, here) should NOT add a second
		"Qualified" log entry. Without this guard, every single save of a
		Deal (regardless of what changed) would spam a new stage-log row.
		"""
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

		# Still just the one entry from insert() above -- not two.
		self.assertEqual(frappe.db.count("Deal Stage Log", {"deal": deal.name}), 1)
