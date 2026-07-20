# ==============================================================================
# patches/create_lead_pipeline_kanban_board.py -- one-time setup patch (see
# patches.txt). Same idea as create_deal_pipeline_kanban_board.py, but for
# Lead's own New/Contacted/Qualified/Do Not Contact pipeline (see
# ../lead.py for the business logic behind that pipeline).
# ==============================================================================

import frappe
from frappe.desk.doctype.kanban_board.kanban_board import quick_kanban_board


def execute():
	# Idempotency guard, same reasoning as the Deal version of this patch.
	if frappe.db.exists("Kanban Board", "Lead Pipeline"):
		return

	frappe.set_user("Administrator")
	quick_kanban_board("Lead", "Lead Pipeline", "stage")
