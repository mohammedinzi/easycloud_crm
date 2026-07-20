// Copyright (c) 2026, inzi and contributors
// For license information, please see license.txt

const DEAL_LINEAR_STAGES = ["Qualified", "Proposal Sent", "Demo Given", "Negotiation", "Won"];
const DEAL_EXIT_STAGES = ["Cold", "Lost", "Not worth our time", "Too Large"];

frappe.ui.form.on("Deal", {
	refresh(frm) {
		frm.add_custom_button("🎤 Voice Note", () => {
			open_voice_note_dialog((result) => {
				frappe.new_doc("CRM Activity", {
					activity_type: "Voice Note",
					deal: frm.doc.name,
					lead: frm.doc.lead,
					date: frappe.datetime.now_datetime(),
					audio_file: result.audio_file,
					transcript: result.transcript,
				});
			});
		});

		render_stage_progress(frm);
		render_deal_timeline(frm);
		render_crm_activities_panel(frm, frm.fields_dict.custom_deal_activities_html.wrapper, "deal");
	},
	stage(frm) {
		render_stage_progress(frm);
	},
});

function render_stage_progress(frm) {
	const wrapper = frm.fields_dict.custom_stage_progress_html.wrapper;
	if (frm.is_new()) {
		$(wrapper).empty();
		return;
	}

	const current_stage = frm.doc.stage;
	const is_exit = DEAL_EXIT_STAGES.includes(current_stage);

	if (!is_exit) {
		draw_stage_progress(frm, wrapper, DEAL_LINEAR_STAGES.indexOf(current_stage), null);
		return;
	}

	frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "Deal Stage Log",
			filters: { deal: frm.doc.name, stage: ["in", DEAL_LINEAR_STAGES] },
			fields: ["stage"],
			order_by: "changed_on desc",
			limit_page_length: 1,
		},
		callback(r) {
			const last_linear = (r.message && r.message[0] && r.message[0].stage) || "Qualified";
			draw_stage_progress(frm, wrapper, DEAL_LINEAR_STAGES.indexOf(last_linear), current_stage);
		},
	});
}

function draw_stage_progress(frm, wrapper, active_index, exit_stage) {
	const $wrapper = $(wrapper).empty();
	const $bar = $(`<div class="stage-progress-bar" style="display:flex; align-items:center; margin: 10px 0 20px;"></div>`).appendTo($wrapper);

	DEAL_LINEAR_STAGES.forEach((stage, i) => {
		const filled = i <= active_index;
		const color = filled ? "#2490ef" : "#d1d8dd";

		$(`
			<div class="stage-dot" title="${frappe.utils.escape_html(stage)}" data-stage="${frappe.utils.escape_html(stage)}"
				style="display:flex; flex-direction:column; align-items:center; cursor:pointer; min-width:70px;">
				<div style="width:16px; height:16px; border-radius:50%; background:${color};"></div>
				<div class="small text-muted" style="margin-top:4px; white-space:nowrap;">${frappe.utils.escape_html(stage)}</div>
			</div>
		`)
			.on("click", () => frm.set_value("stage", stage))
			.appendTo($bar);

		if (i < DEAL_LINEAR_STAGES.length - 1) {
			const connector_color = i < active_index ? "#2490ef" : "#d1d8dd";
			$(`<div style="flex:1; height:2px; background:${connector_color}; margin: 0 4px 18px;"></div>`).appendTo($bar);
		}
	});

	if (exit_stage) {
		$(`<div style="flex:0 0 30px; height:2px; background:#e24c4c; margin: 0 4px 18px;"></div>`).appendTo($bar);
		$(`
			<div class="stage-dot" title="${frappe.utils.escape_html(exit_stage)}"
				style="display:flex; flex-direction:column; align-items:center; min-width:90px;">
				<div style="width:16px; height:16px; border-radius:50%; background:#e24c4c;"></div>
				<div class="small" style="margin-top:4px; white-space:nowrap; color:#e24c4c;">${frappe.utils.escape_html(exit_stage)}</div>
			</div>
		`).appendTo($bar);
	}
}

function render_deal_timeline(frm) {
	const wrapper = frm.fields_dict.custom_deal_timeline_html.wrapper;
	if (frm.is_new()) {
		$(wrapper).empty();
		return;
	}

	const $section = $(wrapper).empty().append(`
		<div class="deal-timeline-section">
			<h6 style="margin-bottom: 10px;">${__("Stage Timeline")}</h6>
			<div class="deal-timeline-list"></div>
		</div>
	`);
	const $list = $section.find(".deal-timeline-list");

	frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "Deal Stage Log",
			filters: { deal: frm.doc.name },
			fields: ["stage", "changed_on", "changed_by"],
			order_by: "changed_on asc",
			limit_page_length: 100,
		},
		callback(r) {
			const entries = r.message || [];
			$list.empty();

			if (!entries.length) {
				$list.append(`<div class="text-muted small">${__("No stage history recorded yet.")}</div>`);
				return;
			}

			entries.forEach((e) => {
				const is_exit = DEAL_EXIT_STAGES.includes(e.stage);
				$(`
					<div style="padding: 6px 0; border-left: 2px solid ${is_exit ? "#e24c4c" : "#2490ef"}; padding-left: 10px; margin-bottom: 4px;">
						<strong style="color:${is_exit ? "#e24c4c" : "inherit"};">${frappe.utils.escape_html(e.stage)}</strong>
						<span class="text-muted small">&middot; ${frappe.datetime.str_to_user(e.changed_on) || ""}${e.changed_by ? " · " + frappe.utils.escape_html(e.changed_by) : ""}</span>
					</div>
				`).appendTo($list);
			});
		},
	});
}
