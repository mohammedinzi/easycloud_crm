import frappe

STAGE_INDICATORS = {
	"New": "Gray",
	"Contacted": "Light Blue",
	"Qualified": "Blue",
	"Proposal": "Yellow",
	"Negotiation": "Orange",
	"Won": "Green",
	"Lost": "Red",
}


def execute():
	if not frappe.db.exists("Kanban Board", "Deal Pipeline"):
		return

	board = frappe.get_doc("Kanban Board", "Deal Pipeline")
	changed = False
	for column in board.columns:
		wanted = STAGE_INDICATORS.get(column.column_name)
		if wanted and column.indicator != wanted:
			column.indicator = wanted
			changed = True

	if changed:
		frappe.set_user("Administrator")
		board.save(ignore_permissions=True)
