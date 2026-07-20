import frappe


def validate(doc, method=None):
	if doc.stage == "Do Not Contact" and not doc.do_not_contact_reason:
		frappe.throw("Select a reason before marking this Lead as Do Not Contact.")


def on_update(doc, method=None):
	if doc.has_value_changed("stage"):
		doc.db_set("stage_changed_on", frappe.utils.now_datetime(), update_modified=False)

	if doc.stage != "Qualified" or not doc.has_value_changed("stage"):
		return

	open_deal_exists = frappe.db.exists("Deal", {"lead": doc.name, "stage": ["not in", ["Won", "Lost"]]})
	if open_deal_exists:
		return

	company_name = doc.company_name or doc.lead_name
	deal = frappe.new_doc("Deal")
	deal.deal_name = company_name
	deal.lead = doc.name
	deal.stage = "Qualified"
	deal.insert(ignore_permissions=True)
	frappe.msgprint(f"Deal created for {company_name}")
