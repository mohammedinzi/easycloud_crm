// Copyright (c) 2026, inzi and contributors
// For license information, please see license.txt

frappe.ui.form.on("Deal", {
	refresh(frm) {
		frm.add_custom_button("🎤 Voice Note", () => {
			open_voice_note_dialog((result) => {
				frappe.new_doc("CRM Activity", {
					activity_type: "Voice Note",
					deal: frm.doc.name,
					lead: frm.doc.lead,
					date: frappe.datetime.now_datetime(),
					audio_file: result.audio_file,
					transcript: result.transcript,
				});
			});
		});
	},
});
