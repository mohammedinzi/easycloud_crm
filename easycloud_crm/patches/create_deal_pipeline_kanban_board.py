import frappe
from frappe.desk.doctype.kanban_board.kanban_board import quick_kanban_board


def execute():
	if frappe.db.exists("Kanban Board", "Deal Pipeline"):
		return

	frappe.set_user("Administrator")
	quick_kanban_board("Deal", "Deal Pipeline", "stage")
