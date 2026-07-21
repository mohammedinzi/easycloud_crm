# Copyright (c) 2026, inzi and Contributors
# See license.txt

# ==============================================================================
# doctype/crm_activity/test_crm_activity.py -- automated tests for
# crm_activity.py's validation, title-computation, and "keep the parent
# Deal's last-contacted date fresh" logic. See test_deal.py for a fuller
# explanation of the FrappeTestCase / automatic-rollback / "ZZTEST" pattern
# used throughout this app's tests -- the short version: everything created
# below is automatically deleted when each test finishes, nothing is left
# behind in the real database.
# ==============================================================================

import frappe
from frappe.tests.utils import FrappeTestCase

from easycloud_crm.easycloud_crm.doctype.deal.deal import get_default_customer_group


class TestCRMActivity(FrappeTestCase):
	def test_requires_lead_or_deal(self):
		"""A CRM Activity with none of Lead/Deal/Customer/Contact set should
		be rejected by validate()'s guard clause -- this is the "floating
		activity attached to nothing" case that guard exists to prevent.
		"""
		activity = frappe.get_doc(
			{
				"doctype": "CRM Activity",
				"activity_type": "Note",
				"notes": "ZZTEST no lead or deal",
			}
		)
		self.assertRaises(frappe.ValidationError, activity.insert, ignore_permissions=True)

	def test_customer_only_link_is_valid(self):
		"""Confirms Customer alone (no Lead/Deal) satisfies the "must be
		linked to something" rule -- e.g. logging a support call with an
		existing customer that isn't tied to any specific Deal.
		"""
		customer = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": "ZZTEST Activity Customer",
				"customer_type": "Company",
				# see test_deal.py's test_won_reuses_existing_customer for why
				# this is needed -- erpnext's own test setup resets Selling
				# Settings' default customer_group to a Group-type node.
				"customer_group": get_default_customer_group(),
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
		"""Same idea as the Customer test above, but for Contact -- the
		fourth and last of the four acceptable link types.
		"""
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
		"""Confirms get_activity_title() produces "Lead: <lead's own title>"
		when linked to a Lead. lead.title is itself a computed field
		(erpnext's stock Lead controller sets it, usually to the company
		name) -- this test doesn't hard-code what that value looks like, it
		just checks our label wraps whatever it actually is.
		"""
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
		"""Same idea, but for the "Deal: <deal_name>" branch of
		get_activity_title().
		"""
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
		"""Confirms update_deal_last_contacted()'s "only ever move the date
		FORWARD" rule: logging a NEWER activity first should set
		last_contacted_on to that newer date, and then logging an OLDER
		activity afterwards should NOT push that date backwards again --
		activities aren't always logged in chronological order (e.g. someone
		catching up on notes a few days late), and the Deal's
		"last contacted" field should always reflect the most recent real
		contact, regardless of the order they were typed into the system.
		"""
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

		# Log the NEWER activity first...
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

		# ...then log an OLDER one afterwards. The Deal's last_contacted_on
		# should stay at the 15th, not regress back to the 1st.
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
