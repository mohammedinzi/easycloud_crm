# Copyright (c) 2026, inzi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Deal(Document):
	def validate(self):
		if self.stage == "Lost" and not self.lost_reason:
			frappe.throw("Select a Lost Reason before marking this Deal as Lost.")

	def on_update(self):
		if self.stage == "Won" and self.has_value_changed("stage"):
			self.convert_to_customer_and_project()

	def convert_to_customer_and_project(self):
		if not self.customer:
			customer = frappe.new_doc("Customer")
			customer.customer_name = self.deal_name
			customer.insert(ignore_permissions=True)
			self.db_set("customer", customer.name)
		else:
			customer = frappe.get_doc("Customer", self.customer)

		if not self.project:
			project = frappe.new_doc("Project")
			project.project_name = self.deal_name
			project.customer = customer.name
			project.insert(ignore_permissions=True)
			self.db_set("project", project.name)

			for subject in [
				"Requirement Gathering",
				"Implementation",
				"Testing",
				"Go Live",
				"Training",
			]:
				task = frappe.new_doc("Task")
				task.subject = subject
				task.project = project.name
				task.custom_deal = self.name
				task.insert(ignore_permissions=True)

			frappe.msgprint(f"Customer and Project created for {self.deal_name}")
