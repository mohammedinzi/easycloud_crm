import frappe


def notification_reference_label(reference_type, reference_name):
	if reference_type == "CRM Activity":
		return frappe.db.get_value("CRM Activity", reference_name, "activity_title") or reference_name
	return reference_name
