// Copyright (c) 2026, inzi and contributors
// For license information, please see license.txt

frappe.ui.form.on("CRM Activity", {
	refresh(frm) {
		frm.add_custom_button("🎤 Voice Note", () => {
			open_voice_note_dialog((result) => {
				frm.set_value("activity_type", "Voice Note");
				frm.set_value("audio_file", result.audio_file);
				frm.set_value("transcript", result.transcript);
			});
		});

		if (frm.doc.lead) {
			frm.add_custom_button("Open Lead", () => frappe.set_route("Form", "Lead", frm.doc.lead));
		}
	},
});
