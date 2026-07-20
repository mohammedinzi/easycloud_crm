# Copyright (c) 2026, inzi and contributors
# For license information, please see license.txt

# ==============================================================================
# doctype/deal_stage_log/deal_stage_log.py -- "Deal Stage Log" is a plain,
# STANDALONE doctype (not a child table like Deal Product -- see its .json:
# no "istable"), but nobody creates or edits these by hand through the UI.
# Every row is written automatically by deal.py's on_update(), one row per
# real stage transition (Deal X moved to "Proposal Sent" at this time, by
# this user) -- an append-only audit trail. Deal itself only ever remembers
# its CURRENT stage; this doctype is what lets deal.js's Stage Timeline tab
# and stage-progress bar reconstruct the full history of how a Deal got
# there. No custom logic needed here either -- it's a pure data record.
# ==============================================================================

from frappe.model.document import Document


class DealStageLog(Document):
	pass
