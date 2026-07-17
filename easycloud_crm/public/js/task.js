frappe.ui.form.on("Task", {
	refresh(frm) {
		if (frm.doc.custom_lead) {
			frm.add_custom_button("Open Lead", () => frappe.set_route("Form", "Lead", frm.doc.custom_lead));
		}
	},
});
