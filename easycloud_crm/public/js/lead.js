frappe.ui.form.on("Lead", {
	refresh(frm) {
		render_crm_activities_panel(frm, frm.fields_dict.custom_crm_activities_html.wrapper, "lead");
	},
});
