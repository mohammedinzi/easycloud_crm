# Copyright (c) 2026, inzi and contributors
# For license information, please see license.txt

import frappe
import requests
from frappe.model.document import Document


class CRMActivity(Document):
	def validate(self):
		if not self.lead and not self.deal:
			frappe.throw("CRM Activity must be linked to a Lead or a Deal")

	def on_update(self):
		if (
			self.activity_type == "Voice Note"
			and self.audio_file
			and not self.transcript
			and self.has_value_changed("audio_file")
		):
			frappe.enqueue(
				"easycloud_crm.easycloud_crm.doctype.crm_activity.crm_activity.transcribe_voice_note",
				queue="long",
				activity_name=self.name,
			)

		if self.deal and self.date:
			self.update_deal_last_contacted()

	def update_deal_last_contacted(self):
		current = frappe.db.get_value("Deal", self.deal, "last_contacted_on")
		new_date = frappe.utils.get_datetime(self.date)
		if not current or new_date > frappe.utils.get_datetime(current):
			frappe.db.set_value("Deal", self.deal, "last_contacted_on", new_date)


def transcribe_voice_note(activity_name):
	activity = frappe.get_doc("CRM Activity", activity_name)
	file_doc = frappe.get_doc("File", {"file_url": activity.audio_file})

	with open(file_doc.get_full_path(), "rb") as f:
		response = requests.post(
			"http://whisper:8500/transcribe",
			files={"file": (file_doc.file_name, f)},
			timeout=300,
		)
	response.raise_for_status()
	transcript = response.json().get("transcript", "")

	frappe.db.set_value("CRM Activity", activity_name, "transcript", transcript)
	frappe.db.commit()
