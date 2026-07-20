# ==============================================================================
# patches/create_deal_pipeline_kanban_board.py -- one-time setup patch (see
# patches.txt for how patches work). Creates the "Deal Pipeline" Kanban
# board -- the drag-and-drop board view of all Deals grouped by their
# `stage` field, linked from the workspace as the "Deal Pipeline" shortcut.
# Runs once, the first time this app is migrated onto a site; does nothing
# on every migrate after that (see the exists-check below).
# ==============================================================================

import frappe
from frappe.desk.doctype.kanban_board.kanban_board import quick_kanban_board


def execute():
	# Idempotency guard: if a site somehow already has a "Deal Pipeline"
	# board (e.g. re-running migrations, or restoring from a backup that
	# already had one), don't try to create a second one.
	if frappe.db.exists("Kanban Board", "Deal Pipeline"):
		return

	# quick_kanban_board() (a Frappe framework helper) needs a user context
	# to attribute the board's creation to -- Administrator is the safe
	# default for automated setup code like this, since a real logged-in
	# user isn't the one triggering this (it runs during `bench migrate`).
	frappe.set_user("Administrator")
	quick_kanban_board("Deal", "Deal Pipeline", "stage")  # (doctype, board name, field to group columns by)
