// ==============================================================================
// public/js/pipeline_list_colors.js -- wired up via hooks.py's
// doctype_list_js for BOTH "Lead" and "Deal", so this loads only when
// either doctype's LIST view (the table of records) is open. Same
// technique already proven in crm_activity_list.js: a
// frappe.listview_settings[...].formatters.<fieldname> function, the
// framework's own per-field list-view formatter hook -- not a hand-rolled
// DOM patch.
//
// Turns the plain text `stage` column into a small colored pill, using
// the exact same color tokens as the Kanban board's column indicators
// (see theme.css's --ec-lead-*/--ec-deal-* variables) and the recolor
// patch (patches/recolor_deal_pipeline_kanban_stages.py) -- all three
// share one palette on purpose, so a Deal's color means the same thing
// whether you're looking at the list view, the Kanban board, or the
// Deal's own stage progress bar.
// ==============================================================================

const EC_STAGE_COLORS = {
	// Lead's pipeline (see lead.py)
	New: "var(--ec-lead-new)",
	Contacted: "var(--ec-lead-contacted)",
	Qualified: "var(--ec-lead-qualified)", // shared name, but Lead and Deal use the same blue for "Qualified" on purpose -- it's the same milestone concept in both pipelines
	"Do Not Contact": "var(--ec-lead-do-not-contact)",

	// Deal's pipeline (see doctype/deal/deal.json)
	"Proposal Sent": "var(--ec-deal-proposal-sent)",
	"Demo Given": "var(--ec-deal-demo-given)",
	Negotiation: "var(--ec-deal-negotiation)",
	Won: "var(--ec-deal-won)",
	Cold: "var(--ec-deal-cold)",
	Lost: "var(--ec-deal-lost)",
	"Not worth our time": "var(--ec-deal-not-worth-our-time)",
	"Too Large": "var(--ec-deal-too-large)",
};

function ec_stage_pill(value) {
	const color = EC_STAGE_COLORS[value];
	if (!color) return frappe.utils.escape_html(value || "");

	return `<span class="ec-stage-pill" style="--ec-pill-color: ${color};">${frappe.utils.escape_html(value)}</span>`;
}

frappe.listview_settings["Lead"] = Object.assign({}, frappe.listview_settings["Lead"], {
	formatters: Object.assign({}, (frappe.listview_settings["Lead"] || {}).formatters, {
		stage: ec_stage_pill,
	}),
});

frappe.listview_settings["Deal"] = Object.assign({}, frappe.listview_settings["Deal"], {
	formatters: Object.assign({}, (frappe.listview_settings["Deal"] || {}).formatters, {
		stage: ec_stage_pill,
	}),
});
