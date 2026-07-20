# ==============================================================================
# patches/set_deal_pipeline_kanban_colors.py -- one-time patch (see
# patches.txt) that colour-codes the Deal Pipeline Kanban board's columns
# (created by create_deal_pipeline_kanban_board.py, which must run first).
#
# HISTORICAL NOTE: STAGE_INDICATORS below reflects Deal's stage list AS IT
# WAS the day this patch was written (stages were literally
# "New/Contacted/Qualified/Proposal/Negotiation/Won/Lost" back then). Deal's
# actual stage options have since changed (see doctype/deal/deal.json --
# now "Qualified/Proposal Sent/Demo Given/Negotiation/Won/Cold/Lost/Not
# worth our time/Too Large") -- but per patches.txt's explanation, a patch
# runs exactly ONCE per site and is never re-run, so this file staying
# "out of date" relative to the current stage list is expected and
# harmless, not a bug to fix here. If the Kanban board's colours need
# updating for the CURRENT stage list, that calls for a NEW patch, not an
# edit to this one.
# ==============================================================================

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
	# If the board doesn't exist yet (e.g. its own creation patch hasn't
	# run for some reason), there's nothing to colour -- bail out quietly
	# rather than erroring.
	if not frappe.db.exists("Kanban Board", "Deal Pipeline"):
		return

	board = frappe.get_doc("Kanban Board", "Deal Pipeline")
	changed = False
	for column in board.columns:
		wanted = STAGE_INDICATORS.get(column.column_name)
		# Only touch columns that both (a) match a stage we have a colour
		# for, and (b) aren't ALREADY that colour -- avoids an unnecessary
		# save() when nothing would actually change.
		if wanted and column.indicator != wanted:
			column.indicator = wanted
			changed = True

	if changed:
		frappe.set_user("Administrator")
		board.save(ignore_permissions=True)
