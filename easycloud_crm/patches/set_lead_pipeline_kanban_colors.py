import frappe

STAGE_INDICATORS = {
	"New": "Gray",
	"Contacted": "Light Blue",
	"Qualified": "Blue",
	"Do Not Contact": "Red",
}


def execute():
	if not frappe.db.exists("Kanban Board", "Lead Pipeline"):
		return

	board = frappe.get_doc("Kanban Board", "Lead Pipeline")
	changed = False
	for column in board.columns:
		wanted = STAGE_INDICATORS.get(column.column_name)
		if wanted and column.indicator != wanted:
			column.indicator = wanted
			changed = True

	if changed:
		frappe.set_user("Administrator")
		board.save(ignore_permissions=True)
