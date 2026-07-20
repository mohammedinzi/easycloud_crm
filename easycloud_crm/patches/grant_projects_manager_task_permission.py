# ==============================================================================
# patches/grant_projects_manager_task_permission.py -- one-time patch (see
# patches.txt). Gives the standard erpnext "Projects Manager" role full
# access (read/write/create/delete/...) to the standard "Task" doctype.
# A one-off permissions fix, not something that needs to run again once
# applied -- that's why it's a patch rather than, say, a fixture (fixtures
# are for data that should be RE-applied/kept in sync on every install;
# this is a single corrective action).
# ==============================================================================

import frappe
from frappe.permissions import setup_custom_perms


def execute():
	# Idempotency guard: if this exact permission row already exists (e.g.
	# patch somehow ran twice, or was manually added already), don't create
	# a duplicate.
	if frappe.db.exists("Custom DocPerm", {"parent": "Task", "role": "Projects Manager", "permlevel": 0}):
		return

	# setup_custom_perms() is a Frappe framework helper that makes sure a
	# doctype has its OWN "Custom DocPerm" override table ready to add rows
	# to (rather than only relying on Task's built-in, framework-owned
	# permission rules) -- required once before the insert() below can work.
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
	# Frappe caches doctype permission rules for performance -- without
	# this, the newly-added permission row might not take effect until
	# something else happens to clear the cache (e.g. a server restart).
	frappe.clear_cache(doctype="Task")
