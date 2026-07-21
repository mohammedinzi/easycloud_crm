# Copyright (c) 2026, inzi and Contributors
# See license.txt

# ==============================================================================
# easycloud_crm/test_dashboard.py -- confirms Task is correctly wired into
# both Lead's Connections tab (dashboard.py, hooked via hooks.py's
# override_doctype_dashboards) and Deal's (doctype/deal/deal_dashboard.py,
# auto-discovered by folder convention). Calls the real
# frappe.get_meta(...).get_dashboard_data() rather than the two get_data
# functions directly, since that's the actual integration point Frappe
# itself uses to build the Connections tab -- testing that path is what
# actually proves the wiring works, not just that the functions return the
# right shape in isolation.
# ==============================================================================

from frappe.tests.utils import FrappeTestCase

import frappe


class TestDashboards(FrappeTestCase):
	def test_lead_dashboard_includes_task(self):
		data = frappe.get_meta("Lead").get_dashboard_data()
		# erpnext's own stock transactions list has at least one entry with
		# no "label" key at all (an unlabeled default group) -- .get(),
		# not [], to skip past that without a KeyError.
		pipeline = next(t for t in data["transactions"] if t.get("label") == "Pipeline")
		self.assertIn("Task", pipeline["items"])
		self.assertIn("Deal", pipeline["items"])
		self.assertIn("CRM Activity", pipeline["items"])
		self.assertEqual(data["non_standard_fieldnames"]["Task"], "custom_lead")

	def test_deal_dashboard_includes_task(self):
		data = frappe.get_meta("Deal").get_dashboard_data()
		tasks_section = next(t for t in data["transactions"] if t.get("label") == "Tasks")
		self.assertIn("Task", tasks_section["items"])
		self.assertEqual(data["non_standard_fieldnames"]["Task"], "custom_deal")
