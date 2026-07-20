# Copyright (c) 2026, inzi and contributors
# For license information, please see license.txt

# ==============================================================================
# doctype/crm_activity/crm_activity.py -- server-side controller for the
# "CRM Activity" doctype: a single logged interaction (Call, Meeting, Email,
# WhatsApp, Note, or Voice Note) attached to a Lead, Deal, Customer, or
# Contact. This is the "diary entry" doctype of the whole CRM -- both
# lead.js and deal.js render a live feed of these on their forms via the
# shared public/js/crm_activities_panel.js.
#
# THIS FILE HAS TWO JOBS:
#   1. validate() / get_activity_title() -- compute a human-readable title
#      for every CRM Activity (e.g. "Lead: Saksham Strategy Group" instead
#      of the raw ID "CRM-ACT-2026-00236"), used as the doctype's title_field
#      (see crm_activity.json) so this friendly text shows up everywhere the
#      raw ID otherwise would -- list views, link fields, the assignment
#      email (see ../../../utils.py's notification_reference_label).
#   2. on_update() -- two independent side effects after every save: kick
#      off background transcription for Voice Notes, and keep a Deal's
#      "last contacted" date up to date whenever an activity is logged
#      against it.
# ==============================================================================

import frappe
import requests
from frappe.model.document import Document


class CRMActivity(Document):
	def validate(self):
		"""Runs right before every save."""
		# Business rule: a CRM Activity floating with no parent record makes
		# no sense -- it always has to be "about" something specific.
		if not (self.lead or self.deal or self.customer or self.contact):
			frappe.throw("CRM Activity must be linked to a Lead, Deal, Customer, or Contact")

		# Recompute the friendly title on every save (not just once at
		# creation) -- so if, say, the Lead this activity is linked to gets
		# renamed later, this activity's title stays in sync next time it's
		# touched.
		self.activity_title = self.get_activity_title()

	def get_activity_title(self):
		"""Builds the "Lead: X" / "Deal: X" / etc. label described at the
		top of this file. Checked in this specific order (Lead, then Deal,
		then Customer, then Contact) because that's the order they appear as
		fields on the form -- in practice a CRM Activity only ever has ONE
		of these set, so the order rarely matters, but if a record somehow
		had more than one link filled in, this order decides which wins.
		"""
		if self.lead:
			# get_cached_value (not get_value) reads from Frappe's
			# in-process cache when possible -- cheaper than a fresh
			# database query, worth it here since this runs on every single
			# save of every CRM Activity. Lead's own "title" field is
			# itself a computed field (handled by erpnext's stock Lead
			# controller, not by this app) that's usually the company name.
			title = frappe.get_cached_value("Lead", self.lead, "title") or self.lead
			return f"Lead: {title}"
		if self.deal:
			title = frappe.get_cached_value("Deal", self.deal, "deal_name") or self.deal
			return f"Deal: {title}"
		if self.customer:
			return f"Customer: {self.customer}"
		if self.contact:
			title = frappe.get_cached_value("Contact", self.contact, "full_name") or self.contact
			return f"Contact: {title}"
		# Unreachable in practice (validate() above already guarantees one
		# of the four is set before this method ever runs) -- kept as a
		# harmless fallback rather than assuming that invariant can never
		# change in the future.
		return self.activity_type

	def on_update(self):
		"""Runs right after a successful save. Two unrelated side effects:"""
		# --- Side effect 1: transcribe Voice Notes in the background ------
		# Only kick off transcription when ALL of these are true: this is a
		# Voice Note, it actually has an audio file attached, it doesn't
		# already have a transcript, AND the audio_file specifically is what
		# just changed on THIS save (not e.g. someone editing the notes text
		# of an already-transcribed voice note, which would otherwise
		# re-trigger transcription every time this record is touched).
		if (
			self.activity_type == "Voice Note"
			and self.audio_file
			and not self.transcript
			and self.has_value_changed("audio_file")
		):
			# Runs in a background worker (queue="long") rather than
			# blocking this save, because calling out to the Whisper
			# transcription service can take a while for longer recordings
			# -- the user shouldn't have to sit and wait for that just to
			# save the record. See transcribe_voice_note() at the bottom of
			# this file for what actually happens in that background job.
			frappe.enqueue(
				"easycloud_crm.easycloud_crm.doctype.crm_activity.crm_activity.transcribe_voice_note",
				queue="long",
				activity_name=self.name,
			)

		# --- Side effect 2: keep the parent Deal's "last contacted" fresh -
		if self.deal and self.date:
			self.update_deal_last_contacted()

	def update_deal_last_contacted(self):
		"""Bumps the linked Deal's `last_contacted_on` field forward if this
		activity's date is more recent than whatever's currently stored --
		this is what makes Deal's "Last Contacted" column meaningful without
		anyone having to manually update it: it's always the date of the
		most recent CRM Activity logged against that Deal.
		"""
		current = frappe.db.get_value("Deal", self.deal, "last_contacted_on")
		new_date = frappe.utils.get_datetime(self.date)
		# Only move the date FORWARD, never backward -- important because
		# activities aren't always logged in chronological order (e.g.
		# someone might log an older call a few days late), and we don't
		# want a late-logged old activity to make the Deal look LESS
		# recently contacted than it actually is.
		if not current or new_date > frappe.utils.get_datetime(current):
			# db.set_value (not self.db_set) because `self` here is the CRM
			# Activity, not the Deal -- we're updating a DIFFERENT record.
			frappe.db.set_value("Deal", self.deal, "last_contacted_on", new_date)


def transcribe_voice_note(activity_name):
	"""The actual background job body enqueued by on_update() above. Runs in
	a separate worker process, completely detached from the original save
	request -- by the time this runs, the user has usually already moved on
	and the form may not even be open anymore, which is why this writes its
	result straight to the database (db.set_value + commit) rather than
	returning anything to a waiting browser.

	activity_name: the CRM Activity's docname, passed in rather than the
	whole document object, because background jobs are serialized and run
	later/elsewhere -- passing a plain string ID is safe and cheap; passing
	a live in-memory Document object across that boundary would not be.
	"""
	activity = frappe.get_doc("CRM Activity", activity_name)
	# The audio was saved as a private File attachment (see api.py's
	# record_voice_note) -- look it up by its stored URL to get the real
	# file on disk.
	file_doc = frappe.get_doc("File", {"file_url": activity.audio_file})

	with open(file_doc.get_full_path(), "rb") as f:
		response = requests.post(
			"http://whisper:8500/transcribe",  # same self-hosted Whisper container api.py's record_voice_note talks to
			files={"file": (file_doc.file_name, f)},
			timeout=300,  # generous timeout -- background jobs aren't blocking a user's browser, so it's safe to wait longer here than in api.py's synchronous version
		)
	response.raise_for_status()
	transcript = response.json().get("transcript", "")

	frappe.db.set_value("CRM Activity", activity_name, "transcript", transcript)
	# Background jobs don't get an automatic commit at the end the way a
	# normal web request does -- without this explicit commit, the
	# transcript would be silently lost when the job finishes.
	frappe.db.commit()
