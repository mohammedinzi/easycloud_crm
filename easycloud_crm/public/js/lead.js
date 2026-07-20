// ==============================================================================
// public/js/lead.js -- client-side controller for the Lead FORM. Wired up
// via hooks.py's doctype_js = {"Lead": "public/js/lead.js"} -- Lead itself
// is a STANDARD erpnext doctype we don't own, so unlike Deal/CRM Activity
// (which each have a .js file living right inside their own doctype
// folder, auto-discovered by convention), this file has to live here at
// the top level and be pointed to explicitly in hooks.py.
//
// Deliberately tiny: this is the ONLY custom JS Lead's form needs. All the
// actual widget logic (the activity feed + quick-log dialog) is shared
// code living in crm_activities_panel.js, called here with "lead" so it
// knows to filter/create CRM Activity records using Lead's own field.
// ==============================================================================

frappe.ui.form.on("Lead", {
	refresh(frm) {
		// custom_crm_activities_html is a Custom Field (see
		// ../../hooks.py's fixtures list, "Lead-custom_crm_activities_html")
		// spliced into Lead's own Activities tab -- a blank placeholder
		// this line fills with the shared CRM Activities panel.
		render_crm_activities_panel(frm, frm.fields_dict.custom_crm_activities_html.wrapper, "lead");
	},
});
