# Copyright (c) 2026, inzi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CRMActivity(Document):
	def validate(self):
		if not self.lead and not self.deal:
			frappe.throw("CRM Activity must be linked to a Lead or a Deal")
