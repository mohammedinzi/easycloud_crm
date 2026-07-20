// ==============================================================================
// public/js/crm_activity_list.js -- wired up via hooks.py's
// doctype_list_js = {"CRM Activity": ...}, so this loads ONLY when CRM
// Activity's LIST view (the table of records) is open -- unlike
// crm_activities_panel.js/voice_note.js, which load everywhere via
// app_include_js. Purely cosmetic: adds an emoji icon in front of each
// row's "Activity Type" column value.
//
// Extends the icon-first pattern already used on the Voice Note button (🎤)
// to every CRM Activity type, so the list is scannable by shape before
// reading any text. frappe.listview_settings[...].formatters is the
// framework's own per-field list-view formatter hook (confirmed in
// frappe/public/js/frappe/list/list_view.js -- settings.formatters[fieldname]
// is called with (value, df, doc) and its return value used directly as the
// column's HTML) rather than a hand-rolled DOM patch.
// ==============================================================================
frappe.listview_settings["CRM Activity"] = {
	formatters: {
		// `value` here is whatever this specific row's activity_type field
		// holds (e.g. "Call", "Voice Note", ...) -- must exactly match one
		// of CRM Activity's Select options (see
		// doctype/crm_activity/crm_activity.json) for its icon to show;
		// anything unrecognised just falls back to plain text, no icon.
		activity_type: function (value) {
			const icons = {
				Call: "📞",
				Meeting: "🤝",
				Email: "📧",
				WhatsApp: "💬",
				Note: "📝",
				"Voice Note": "🎤",
			};
			const icon = icons[value] || "";
			// escape_html guards against the activity type text ever being
			// rendered as raw HTML -- defensive, since this value is
			// currently always one of a fixed Select list, but doesn't
			// rely on that staying true forever.
			return `${icon ? icon + " " : ""}${frappe.utils.escape_html(value || "")}`;
		},
	},
};
