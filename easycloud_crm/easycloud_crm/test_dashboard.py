# Copyright (c) 2026, inzi and Contributors
# See license.txt

from frappe.tests.utils import FrappeTestCase

from easycloud_crm.dashboard import get_lead_dashboard_data


class TestLeadDashboard(FrappeTestCase):
	def test_task_included_with_correct_fieldname_mapping(self):
		data = get_lead_dashboard_data({})
		pipeline = next(t for t in data["transactions"] if t["label"] == "Pipeline")
		self.assertIn("Task", pipeline["items"])
		self.assertEqual(data["non_standard_fieldnames"]["Task"], "custom_lead")
