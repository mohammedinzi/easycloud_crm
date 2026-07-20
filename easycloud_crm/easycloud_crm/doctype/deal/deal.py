# Copyright (c) 2026, inzi and contributors
# For license information, please see license.txt

# ==============================================================================
# doctype/deal/deal.py -- server-side (Python) controller for the "Deal"
# doctype. Deal is an app-owned doctype (unlike Lead, which is a standard
# erpnext doctype we only extend) -- its fields are defined in deal.json
# right next to this file, and its FORM behaviour (the stage progress bar,
# timeline, etc.) lives in deal.js also right next to this file. This file
# is only the SERVER-side rules: validation, and what happens automatically
# after a save.
#
# THE BIG PICTURE this file implements: a Deal moves through its own
# `stage` field, similar in spirit to Lead's `stage` (see ../../../lead.py)
# but a separate pipeline for the actual sales process once a Lead has been
# qualified:
#   Qualified -> Proposal Sent -> Demo Given -> Negotiation -> Won
#                                                            \-> Cold/Lost/
#                                                               Not worth our
#                                                               time/Too Large
# The moment a Deal reaches "Won", this file automatically creates (or
# reuses) a Customer record for it -- turning "a deal we closed" into "a
# real paying customer" elsewhere in the system.
# ==============================================================================

import frappe
from frappe.model.document import Document


class Deal(Document):
	"""Frappe auto-discovers this class by its doctype folder location --
	nothing in hooks.py points here directly. Any doctype's methods named
	validate/on_update/etc. are called automatically at the matching point
	in that doctype's own save lifecycle (same idea as Lead's doc_events in
	hooks.py, just declared differently because Deal is a doctype THIS app
	owns, so it gets a real Python class instead of a hooks.py entry).
	"""

	def validate(self):
		"""Runs right before every save. Raising an error here blocks the save."""
		# Business rule: a Deal can't be silently marked "Lost" -- the team
		# needs to record WHY (Price? Competitor? Budget? ...) so this is
		# useful for reporting later (see the "Lost Deals by Reason" chart).
		if self.stage == "Lost" and not self.lost_reason:
			frappe.throw("Select a Lost Reason before marking this Deal as Lost.")

	def on_update(self):
		"""Runs right after a successful save. Two independent jobs, same
		pattern as Lead's on_update in ../../../lead.py:
		  1. Keep a full history log of every stage this Deal has passed
		     through (powers the Stage Timeline tab -- see deal.js).
		  2. The moment a Deal reaches "Won", convert it into a real Customer.
		"""
		# --- Job 1: log every stage change to Deal Stage Log --------------
		# has_value_changed() is True only on the exact save where `stage`
		# moved to a new value -- not on every save of an already-set stage.
		if self.has_value_changed("stage"):
			# Deal Stage Log is a simple, append-only doctype (see
			# ../deal_stage_log/deal_stage_log.py) -- one row per transition,
			# never edited or deleted afterwards. This is what makes the
			# Stage Timeline tab possible: without this log, the Deal record
			# itself only ever remembers its CURRENT stage, not the history
			# of how it got there.
			frappe.get_doc(
				{
					"doctype": "Deal Stage Log",
					"deal": self.name,
					"stage": self.stage,
					"changed_by": frappe.session.user,
				}
			).insert(ignore_permissions=True)

		# --- Job 2: auto-convert to Customer when stage becomes "Won" -----
		if self.stage == "Won" and self.has_value_changed("stage"):
			self.convert_to_customer()

	def convert_to_customer(self):
		"""Creates (or reuses, if one already matches) a Customer record for
		this Deal and links it back via self.customer. Called only from
		on_update() above, exactly once per Deal (the moment it's first
		marked Won) -- but written defensively so calling it again would be
		a safe no-op (see the `if self.customer: return` guard below), in
		case this ever needs to be called from anywhere else in future.
		"""
		# Prefer the ORIGINAL Lead's company name if this Deal came from one
		# (more likely to be the real, correctly-spelled company name);
		# fall back to the Deal's own name if there's no linked Lead, or the
		# Lead never had a company name recorded.
		company_name = (
			frappe.db.get_value("Lead", self.lead, "company_name") if self.lead else None
		) or self.deal_name

		# Already converted (e.g. this Deal was Won once, then somehow
		# re-saved as Won again) -- nothing to do.
		if self.customer:
			return

		# Guard against creating duplicate Customers: if a Customer with
		# this exact name already exists (perhaps from a different Deal with
		# the same company, or created manually), just link to that one
		# instead of making a second, confusing duplicate.
		existing_customer = frappe.db.get_value("Customer", {"customer_name": company_name})
		if existing_customer:
			# db_set() writes directly to the database without re-triggering
			# validate/on_update -- calling self.save() here would recurse
			# back into this same on_update() method.
			self.db_set("customer", existing_customer)
			frappe.msgprint(f"Customer already exists for {company_name}")
			return

		# No existing match -- create a brand new Customer. ignore_permissions
		# is needed because this is a side effect of saving a DEAL, triggered
		# by whatever permissions the person saving the Deal has, not
		# necessarily Customer-creation rights specifically.
		customer = frappe.new_doc("Customer")
		customer.customer_name = company_name
		customer.insert(ignore_permissions=True)
		self.db_set("customer", customer.name)
		frappe.msgprint(f"Customer created for {company_name}")
