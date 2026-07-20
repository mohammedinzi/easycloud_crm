// Copyright (c) 2026, inzi and contributors
// For license information, please see license.txt

// ==============================================================================
// doctype/crm_activity/crm_activity.js -- client-side controller for the
// CRM Activity FORM itself (as opposed to public/js/crm_activity_list.js,
// which only affects its LIST view). Small file, two small jobs: offer the
// same Voice Note recording button Deal's form has, and add a shortcut back
// to the parent Lead when this activity is logged against one.
// ==============================================================================

frappe.ui.form.on("CRM Activity", {
	refresh(frm) {
		// Same voice-note flow as deal.js's button -- open_voice_note_dialog
		// is defined in public/js/voice_note.js (loaded site-wide). The
		// difference from deal.js's version of this button: THIS form IS a
		// CRM Activity already, so the result fills in the CURRENT record's
		// own fields directly, instead of creating a brand new one.
		frm.add_custom_button("🎤 Voice Note", () => {
			open_voice_note_dialog((result) => {
				frm.set_value("activity_type", "Voice Note");
				frm.set_value("audio_file", result.audio_file);
				frm.set_value("transcript", result.transcript);
			});
		});

		// Convenience shortcut: if this activity is linked to a Lead,
		// offer a one-click way back to that Lead's own form -- saves
		// having to search for it manually.
		if (frm.doc.lead) {
			frm.add_custom_button("Open Lead", () => frappe.set_route("Form", "Lead", frm.doc.lead));
		}
	},
});
