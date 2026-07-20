# ==============================================================================
# patches/show_last_contacted_on_kanban_cards.py -- one-time patch (see
# patches.txt). Adds the `last_contacted_on` field (kept up to date by
# doctype/crm_activity/crm_activity.py's update_deal_last_contacted()) to
# the set of fields shown on each card of the Deal Pipeline Kanban board --
# so at a glance, without opening any Deal, you can see how recently each
# one was actually followed up on.
# ==============================================================================

import json

import frappe
from frappe.desk.doctype.kanban_board.kanban_board import save_settings


def execute():
	if not frappe.db.exists("Kanban Board", "Deal Pipeline"):
		return

	board = frappe.get_doc("Kanban Board", "Deal Pipeline")
	# `fields` is stored as a JSON-encoded string on the board record (a
	# list of fieldnames to show on every card) -- has to be decoded before
	# it can be checked/modified like a normal Python list.
	current_fields = json.loads(board.fields or "[]")
	if "last_contacted_on" in current_fields:
		return  # already there (e.g. someone added it manually, or this patch already ran) -- nothing to do

	frappe.set_user("Administrator")
	current_fields.append("last_contacted_on")
	# save_settings() is the Kanban Board framework's own helper for
	# updating a board's config -- used instead of a plain
	# board.save() because Kanban Board settings have their own dedicated
	# save path with extra validation/side effects the framework expects.
	save_settings(
		board_name="Deal Pipeline",
		settings=json.dumps({"fields": current_fields, "show_labels": 1}),
	)
