import json

import frappe
from frappe.desk.doctype.kanban_board.kanban_board import save_settings


def execute():
	if not frappe.db.exists("Kanban Board", "Deal Pipeline"):
		return

	board = frappe.get_doc("Kanban Board", "Deal Pipeline")
	current_fields = json.loads(board.fields or "[]")
	if "last_contacted_on" in current_fields:
		return

	frappe.set_user("Administrator")
	current_fields.append("last_contacted_on")
	save_settings(
		board_name="Deal Pipeline",
		settings=json.dumps({"fields": current_fields, "show_labels": 1}),
	)
