# Copyright (c) 2026, inzi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Deal(Document):
	def validate(self):
		if self.stage == "Lost" and not self.lost_reason:
			frappe.throw("Select a Lost Reason before marking this Deal as Lost.")

	def on_update(self):
		if self.has_value_changed("stage"):
			frappe.get_doc(
				{
					"doctype": "Deal Stage Log",
					"deal": self.name,
					"stage": self.stage,
					"changed_by": frappe.session.user,
				}
			).insert(ignore_permissions=True)

		if self.stage == "Won" and self.has_value_changed("stage"):
			self.convert_to_customer()

	def convert_to_customer(self):
		company_name = (
			frappe.db.get_value("Lead", self.lead, "company_name") if self.lead else None
		) or self.deal_name

		if self.customer:
			return

		existing_customer = frappe.db.get_value("Customer", {"customer_name": company_name})
		if existing_customer:
			self.db_set("customer", existing_customer)
			frappe.msgprint(f"Customer already exists for {company_name}")
			return

		customer = frappe.new_doc("Customer")
		customer.customer_name = company_name
		customer.insert(ignore_permissions=True)
		self.db_set("customer", customer.name)
		frappe.msgprint(f"Customer created for {company_name}")
