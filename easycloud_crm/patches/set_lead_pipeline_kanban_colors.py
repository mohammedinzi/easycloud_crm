# ==============================================================================
# patches/set_lead_pipeline_kanban_colors.py -- one-time patch (see
# patches.txt) that colour-codes the Lead Pipeline Kanban board's columns
# (created by create_lead_pipeline_kanban_board.py, which must run first).
# Unlike the Deal version of this patch, Lead's stage list HASN'T changed
# since this was written, so STAGE_INDICATORS below still matches
# lead.py's actual New/Contacted/Qualified/Do Not Contact pipeline exactly.
# ==============================================================================

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
