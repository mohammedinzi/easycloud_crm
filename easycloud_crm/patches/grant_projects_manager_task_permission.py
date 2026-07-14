import frappe
from frappe.permissions import setup_custom_perms


def execute():
	if frappe.db.exists("Custom DocPerm", {"parent": "Task", "role": "Projects Manager", "permlevel": 0}):
		return

	setup_custom_perms("Task")
	frappe.get_doc(
		{
			"doctype": "Custom DocPerm",
			"parent": "Task",
			"parenttype": "DocType",
			"parentfield": "permissions",
			"role": "Projects Manager",
			"permlevel": 0,
			"read": 1,
			"write": 1,
			"create": 1,
			"delete": 1,
			"report": 1,
			"email": 1,
			"print": 1,
			"share": 1,
		}
	).insert(ignore_permissions=True)
	frappe.clear_cache(doctype="Task")
