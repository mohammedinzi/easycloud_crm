// Extends the icon-first pattern already used on the Voice Note button (🎤)
// to every CRM Activity type, so the list is scannable by shape before
// reading any text. frappe.listview_settings[...].formatters is the
// framework's own per-field list-view formatter hook (confirmed in
// frappe/public/js/frappe/list/list_view.js -- settings.formatters[fieldname]
// is called with (value, df, doc) and its return value used directly as the
// column's HTML) rather than a hand-rolled DOM patch.
frappe.listview_settings["CRM Activity"] = {
	formatters: {
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
			return `${icon ? icon + " " : ""}${frappe.utils.escape_html(value || "")}`;
		},
	},
};
