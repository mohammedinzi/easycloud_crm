# ==============================================================================
# easycloud_crm/utils.py
#
# WARNING: every top-level function defined in this file is automatically
# exposed to Jinja email/print templates site-wide (see hooks.py's
# `jinja = {"methods": "easycloud_crm.utils"}`). Don't add unrelated helper
# functions here just because it's a convenient place to put them -- only put
# something here if it's meant to be callable from a template.
# ==============================================================================

import frappe


def notification_reference_label(reference_type, reference_name):
	"""Used inside the "Assignment Email Notification" template (see
	fixtures/notification.json) to decide what text to show for whatever got
	assigned. Called like:
	    {{ notification_reference_label(doc.reference_type, doc.reference_name) }}
	where `doc` there is the ToDo record created by Frappe's standard
	"Assign To" feature.

	Problem this solves: for most doctypes, reference_name (the raw
	document ID, e.g. "DEAL-2026-00097") is already a fine, readable label.
	But CRM Activity's own ID looks like "CRM-ACT-2026-00236" -- meaningless
	to a human. So specifically for CRM Activity, we look up its
	`activity_title` field instead (a friendlier computed label like
	"Lead: Saksham Strategy Group" or "Deal: ADP" -- see
	doctype/crm_activity/crm_activity.py for where that field gets set).
	Every other doctype just gets its own name back unchanged.
	"""
	if reference_type == "CRM Activity":
		return frappe.db.get_value("CRM Activity", reference_name, "activity_title") or reference_name
	return reference_name
