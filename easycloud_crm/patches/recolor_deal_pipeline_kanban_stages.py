# ==============================================================================
# patches/recolor_deal_pipeline_kanban_stages.py -- one-time patch (see
# patches.txt for how patches work).
#
# set_deal_pipeline_kanban_colors.py (an earlier patch) only covers Deal's
# *old* stage list from before the pipeline was redesigned
# (New/Contacted/Qualified/Proposal/Negotiation/Won/Lost) -- per that
# file's own comment and patches.txt's rule, a patch runs exactly once per
# site and editing an old one after it's already run does nothing on
# existing sites. This is the correct way to fix it: a NEW patch, covering
# Deal's actual current stage list (see doctype/deal/deal.json), using the
# same color language as theme.css's --ec-deal-* tokens and
# public/js/pipeline_list_colors.js's stage pills, so the Kanban board,
# the list view, and the Deal form's own stage progress bar all agree
# visually about what each stage means.
#
# Indicator values are Kanban Board Column's fixed Select options (Blue,
# Cyan, Gray, Green, Light Blue, Orange, Pink, Purple, Red, Yellow --
# confirmed via that doctype's own JSON) -- not free-form colors.
# ==============================================================================

import frappe

STAGE_INDICATORS = {
	"Qualified": "Blue",
	"Proposal Sent": "Purple",
	"Demo Given": "Yellow",
	"Negotiation": "Orange",
	"Won": "Green",
	"Cold": "Light Blue",  # went quiet -- not a rejection, just faded
	"Lost": "Red",  # an explicit no
	"Not worth our time": "Gray",  # our own call, not theirs
	"Too Large": "Cyan",  # neutral -- a fit/size mismatch, not a rejection
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
