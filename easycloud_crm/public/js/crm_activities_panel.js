function render_crm_activities_panel(frm, wrapper, link_fieldname) {
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

function load_crm_activities(frm, $section, link_fieldname) {
	const $list = $section.find(".crm-activities-list");

	frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "CRM Activity",
			filters: { [link_fieldname]: frm.doc.name },
			fields: ["name", "activity_type", "date", "notes"],
			order_by: "date desc",
			limit_page_length: 10,
		},
		callback(r) {
			const activities = r.message || [];
			$list.empty();

			if (!activities.length) {
				$list.append(`<div class="text-muted small">${__("No activities logged yet.")}</div>`);
				return;
			}

			activities.forEach((a) => {
				const notes_text = frappe.utils.strip_html(a.notes || "").slice(0, 100);
				$(`
					<div class="crm-activity-row" style="padding: 6px 0; border-bottom: 1px solid var(--border-color); cursor: pointer;">
						<strong>${frappe.utils.escape_html(a.activity_type)}</strong>
						<span class="text-muted small">&middot; ${frappe.datetime.str_to_user(a.date) || ""}</span>
						${notes_text ? `<div class="small text-muted">${frappe.utils.escape_html(notes_text)}</div>` : ""}
					</div>
				`)
					.on("click", () => frappe.set_route("Form", "CRM Activity", a.name))
					.appendTo($list);
			});
		},
	});
}

function open_log_activity_dialog(frm, wrapper, link_fieldname) {
	const dialog = new frappe.ui.Dialog({
		title: __("Log Activity"),
		fields: [
			{
				fieldname: "activity_type",
				fieldtype: "Select",
				label: __("Activity Type"),
				options: "Call\nMeeting\nEmail\nWhatsApp\nNote",
				default: "Call",
				reqd: 1,
			},
			{
				fieldname: "date",
				fieldtype: "Datetime",
				label: __("Date"),
				default: frappe.datetime.now_datetime(),
			},
			{
				fieldname: "notes",
				fieldtype: "Text Editor",
				label: __("Notes"),
			},
		],
		primary_action_label: __("Save"),
		primary_action(values) {
			frappe.call({
				method: "frappe.client.insert",
				args: {
					doc: {
						doctype: "CRM Activity",
						[link_fieldname]: frm.doc.name,
						activity_type: values.activity_type,
						date: values.date,
						notes: values.notes,
					},
				},
				freeze: true,
				callback() {
					dialog.hide();
					load_crm_activities(frm, $(wrapper), link_fieldname);
				},
			});
		},
	});

	dialog.show();
}
