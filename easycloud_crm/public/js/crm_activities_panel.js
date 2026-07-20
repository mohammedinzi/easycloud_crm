// ==============================================================================
// public/js/crm_activities_panel.js -- loaded on EVERY Desk page (see
// hooks.py's app_include_js), same pattern as voice_note.js: a global
// function meant to be called from other forms' controllers. This is the
// small "recent activity feed + quick log" widget embedded on BOTH Lead's
// form (see ../lead.js) and Deal's form (see
// ../../easycloud_crm/doctype/deal/deal.js) -- written ONCE here so both
// doctypes get an identical widget instead of two near-duplicate copies.
//
// render_crm_activities_panel(frm, wrapper, link_fieldname) is the one
// entry point callers use. `link_fieldname` (either "lead" or "deal") is
// what tells this shared code WHICH CRM Activity field to filter/create
// against -- that's the entire trick that makes one panel work for two
// different doctypes.
// ==============================================================================

/**
 * Builds and inserts the whole panel: a header with a "+ Log Activity"
 * button, and a live-loaded list of recent activities below it.
 *
 * @param {object} frm - the current form (Lead or Deal)
 * @param {HTMLElement|jQuery} wrapper - the blank HTML field to render into
 *        (frm.fields_dict.<some_html_field>.wrapper on the caller's side)
 * @param {"lead"|"deal"} link_fieldname - which CRM Activity field
 *        (lead / deal) links back to records of frm's doctype
 */
function render_crm_activities_panel(frm, wrapper, link_fieldname) {
	// A brand-new, unsaved Lead/Deal has no name yet to filter/link
	// activities against -- nothing meaningful to show until it's saved
	// at least once.
	if (frm.is_new()) return;

	const $section = $(wrapper).empty().append(`
		<div class="crm-activities-section">
			<div class="d-flex justify-content-between align-items-center" style="margin-bottom: 8px;">
				<h6 style="margin: 0;">${__("CRM Activities")}</h6>
				<button class="btn btn-xs btn-default log-activity-btn">${__("+ Log Activity")}</button>
			</div>
			<div class="crm-activities-list"></div>
		</div>
	`);

	$section.find(".log-activity-btn").on("click", () => open_log_activity_dialog(frm, wrapper, link_fieldname));

	load_crm_activities(frm, $section, link_fieldname);
}

/**
 * Fetches and renders the most recent CRM Activities linked to this
 * record. Split out as its own function (rather than inlined into
 * render_crm_activities_panel) specifically so open_log_activity_dialog's
 * save callback (below) can call it again afterwards to refresh the list
 * without re-building the whole panel from scratch.
 */
function load_crm_activities(frm, $section, link_fieldname) {
	const $list = $section.find(".crm-activities-list");

	// frappe.client.get_list is Frappe's generic "fetch records" API
	// method -- usable directly from form JS without needing a dedicated
	// backend endpoint for this simple a query.
	frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "CRM Activity",
			// Computed property key: becomes {"lead": frm.doc.name} when
			// called from lead.js, or {"deal": frm.doc.name} from deal.js
			// -- this one line is what makes the shared panel filter
			// correctly for whichever doctype it's embedded in.
			filters: { [link_fieldname]: frm.doc.name },
			fields: ["name", "activity_type", "date", "notes"],
			order_by: "date desc", // most recent first
			limit_page_length: 10, // a quick-glance preview, not a full list -- open CRM Activity's own list view for everything
		},
		callback(r) {
			const activities = r.message || [];
			$list.empty();

			if (!activities.length) {
				$list.append(`<div class="text-muted small">${__("No activities logged yet.")}</div>`);
				return;
			}

			activities.forEach((a) => {
				// Notes are rich-text (HTML) -- strip the markup and trim
				// to a short preview so the feed stays scannable rather
				// than each entry ballooning to full-note length.
				const notes_text = frappe.utils.strip_html(a.notes || "").slice(0, 100);
				$(`
					<div class="crm-activity-row" style="padding: 6px 0; border-bottom: 1px solid var(--border-color); cursor: pointer;">
						<strong>${frappe.utils.escape_html(a.activity_type)}</strong>
						<span class="text-muted small">&middot; ${frappe.datetime.str_to_user(a.date) || ""}</span>
						${notes_text ? `<div class="small text-muted">${frappe.utils.escape_html(notes_text)}</div>` : ""}
					</div>
				`)
					.on("click", () => frappe.set_route("Form", "CRM Activity", a.name)) // click a row to open the full record
					.appendTo($list);
			});
		},
	});
}

/**
 * Opens a small "quick add" dialog for logging a new activity WITHOUT
 * leaving the current Lead/Deal form (as opposed to navigating away to
 * CRM Activity's own New form). Deliberately offers only the essentials
 * (type/date/notes) -- NOT the full CRM Activity field set (e.g. no Voice
 * Note option here; that has its own dedicated button, see
 * ../../easycloud_crm/doctype/crm_activity/crm_activity.js).
 */
function open_log_activity_dialog(frm, wrapper, link_fieldname) {
	const dialog = new frappe.ui.Dialog({
		title: __("Log Activity"),
		fields: [
			{
				fieldname: "activity_type",
				fieldtype: "Select",
				label: __("Activity Type"),
				options: "Call\nMeeting\nEmail\nWhatsApp\nNote",
				default: "Call", // the single most common activity type, saves a click for the common case
				reqd: 1,
			},
			{
				fieldname: "date",
				fieldtype: "Datetime",
				label: __("Date"),
				default: frappe.datetime.now_datetime(), // assume "just happened" by default; easy to change for logging something after the fact
			},
			{
				fieldname: "notes",
				fieldtype: "Text Editor",
				label: __("Notes"),
			},
		],
		primary_action_label: __("Save"),
		primary_action(values) {
			// frappe.client.insert is the generic "create a record" API
			// method -- same idea as get_list above, no custom backend
			// endpoint needed for a plain create.
			frappe.call({
				method: "frappe.client.insert",
				args: {
					doc: {
						doctype: "CRM Activity",
						[link_fieldname]: frm.doc.name, // links the new activity back to whichever Lead/Deal this panel is embedded in
						activity_type: values.activity_type,
						date: values.date,
						notes: values.notes,
					},
				},
				freeze: true, // shows a loading overlay -- prevents double-submitting by clicking Save twice quickly
				callback() {
					dialog.hide();
					// Refresh the feed immediately so the newly-logged
					// activity shows up right away, without requiring the
					// user to manually reload the whole Lead/Deal form.
					load_crm_activities(frm, $(wrapper), link_fieldname);
				},
			});
		},
	});

	dialog.show();
}
