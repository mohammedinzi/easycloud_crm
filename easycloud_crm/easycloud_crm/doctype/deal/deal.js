// Copyright (c) 2026, inzi and contributors
// For license information, please see license.txt

// ==============================================================================
// doctype/deal/deal.js -- client-side (browser) controller for the Deal FORM.
// Frappe auto-loads this file whenever someone opens a Deal record, purely
// by folder convention (no hooks.py entry needed -- compare to Lead, which
// DOES need one in hooks.py because its controller lives outside a doctype
// folder, in public/js/lead.js).
//
// This file is 100% presentation/UI -- it reads data and draws HTML, but
// never decides business rules (e.g. it does NOT decide when a Deal
// converts to a Customer; that's server-side, in deal.py). Three separate
// pieces of UI get built here, each into its own placeholder HTML field
// defined in deal.json:
//   1. render_stage_progress() -> the clickable dot-and-line progress bar
//      at the top of the Details tab (custom_stage_progress_html field)
//   2. render_deal_timeline()  -> the chronological stage history list on
//      the Timeline tab (custom_deal_timeline_html field)
//   3. render_crm_activities_panel() -> the call/meeting/note log on the
//      Activities tab (custom_deal_activities_html field) -- this function
//      is actually DEFINED in a different file, public/js/crm_activities_panel.js,
//      and shared between Deal and Lead; deal.js just calls it.
// ==============================================================================

// The "happy path" a Deal is meant to travel through, in order. Used both to
// decide how far along the progress bar to fill, and to draw the dots
// themselves (see draw_stage_progress below).
const DEAL_LINEAR_STAGES = ["Qualified", "Proposal Sent", "Demo Given", "Negotiation", "Won"];
// The four "this Deal is over, and not in a good way" stages. A Deal in one
// of these doesn't fit neatly on the linear progress bar (it didn't reach
// "Won" by going forward) -- see render_stage_progress()'s handling below.
const DEAL_EXIT_STAGES = ["Cold", "Lost", "Not worth our time", "Too Large"];

frappe.ui.form.on("Deal", {
	// refresh runs every time the form loads or re-renders (opening the
	// record, after a save, after certain field changes) -- so everything
	// in here needs to be safe to run repeatedly, not just once.
	refresh(frm) {
		// Adds the "🎤 Voice Note" button to the form's toolbar.
		// open_voice_note_dialog is defined in public/js/voice_note.js
		// (loaded site-wide via hooks.py's app_include_js) -- it handles
		// the actual recording+transcription and hands the result back
		// here via this callback, which then creates a new CRM Activity
		// pre-filled with the recording and its transcript, linked to
		// both this Deal AND its parent Lead (if any).
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
		// "deal" here (the third argument) tells the shared activities
		// panel which Link field on CRM Activity to filter/create against
		// -- the SAME function is called from lead.js with "lead" instead,
		// which is what makes this one panel work for both doctypes.
		render_crm_activities_panel(frm, frm.fields_dict.custom_deal_activities_html.wrapper, "deal");
	},
	// Runs specifically when the `stage` field's value changes on the form
	// (e.g. the user picks a new stage from the dropdown) -- redraws just
	// the progress bar immediately, without waiting for a full save+refresh,
	// so the UI feels responsive.
	stage(frm) {
		render_stage_progress(frm);
	},
});

/**
 * Draws the clickable stage progress bar into the Details tab.
 *
 * Two different situations to handle:
 *   - Normal Deal moving through the pipeline: fill the bar up to its
 *     current stage, nothing more.
 *   - Deal that has EXITED (Cold/Lost/etc.): the bar should still show how
 *     far it got before exiting (e.g. "got to Demo Given, then went Cold"),
 *     which means looking up its LAST linear stage from the history log --
 *     the Deal's own current `stage` field only holds "Cold" right now, it
 *     doesn't remember what came before that.
 */
function render_stage_progress(frm) {
	const wrapper = frm.fields_dict.custom_stage_progress_html.wrapper;
	if (frm.is_new()) {
		// A Deal that hasn't been saved yet has no history to show, and no
		// real stage transitions have happened -- just show nothing rather
		// than a misleading empty bar.
		$(wrapper).empty();
		return;
	}

	const current_stage = frm.doc.stage;
	const is_exit = DEAL_EXIT_STAGES.includes(current_stage);

	if (!is_exit) {
		// Simple case: current_stage IS one of the linear stages, so we
		// already know exactly how far to fill the bar without any extra
		// lookup.
		draw_stage_progress(frm, wrapper, DEAL_LINEAR_STAGES.indexOf(current_stage), null);
		return;
	}

	// Exit-stage case: ask the server for this Deal's most recent stage log
	// entry that WAS one of the linear stages -- that tells us how far it
	// got before falling off the happy path. frappe.client.get_list is
	// Frappe's generic "fetch records" API method, usable from any form's
	// JS without writing a dedicated backend endpoint.
	frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "Deal Stage Log",
			filters: { deal: frm.doc.name, stage: ["in", DEAL_LINEAR_STAGES] },
			fields: ["stage"],
			order_by: "changed_on desc",
			limit_page_length: 1, // we only need the single most recent matching entry
		},
		callback(r) {
			// Fallback to "Qualified" (the very first stage) if, for
			// whatever reason, no linear-stage history exists yet (e.g. a
			// Deal created directly in an exit stage, which shouldn't
			// normally happen but is defended against here anyway).
			const last_linear = (r.message && r.message[0] && r.message[0].stage) || "Qualified";
			draw_stage_progress(frm, wrapper, DEAL_LINEAR_STAGES.indexOf(last_linear), current_stage);
		},
	});
}

/**
 * Actually builds and inserts the progress bar's HTML. Pure rendering --
 * takes numbers/strings in, produces DOM, doesn't fetch anything itself
 * (that's the caller's job above).
 *
 * active_index: how many of the linear stages should show as "filled"
 *               (blue) rather than "not reached yet" (grey).
 * exit_stage:   null for a normal in-progress Deal, or one of
 *               DEAL_EXIT_STAGES if this Deal fell off the happy path --
 *               when set, an extra red dot is appended after the bar.
 */
function draw_stage_progress(frm, wrapper, active_index, exit_stage) {
	const $wrapper = $(wrapper).empty();
	const $bar = $(`<div class="stage-progress-bar" style="display:flex; align-items:center; margin: 10px 0 20px;"></div>`).appendTo($wrapper);

	DEAL_LINEAR_STAGES.forEach((stage, i) => {
		const filled = i <= active_index;
		const color = filled ? "#2490ef" : "#d1d8dd"; // Frappe's standard blue vs. a neutral grey

		// Every dot is clickable -- clicking one jumps the Deal straight to
		// that stage (a quick shortcut instead of using the Stage dropdown
		// field). frappe.utils.escape_html guards against a stage NAME
		// somehow containing HTML-special characters breaking this markup
		// (defensive, since these names come from a fixed Select list today,
		// but doesn't rely on that staying true forever).
		$(`
			<div class="stage-dot" title="${frappe.utils.escape_html(stage)}" data-stage="${frappe.utils.escape_html(stage)}"
				style="display:flex; flex-direction:column; align-items:center; cursor:pointer; min-width:70px;">
				<div style="width:16px; height:16px; border-radius:50%; background:${color};"></div>
				<div class="small text-muted" style="margin-top:4px; white-space:nowrap;">${frappe.utils.escape_html(stage)}</div>
			</div>
		`)
			.on("click", () => frm.set_value("stage", stage))
			.appendTo($bar);

		// A connecting line between this dot and the next one -- skipped
		// after the very last stage, since there's nothing to connect to.
		if (i < DEAL_LINEAR_STAGES.length - 1) {
			const connector_color = i < active_index ? "#2490ef" : "#d1d8dd";
			$(`<div style="flex:1; height:2px; background:${connector_color}; margin: 0 4px 18px;"></div>`).appendTo($bar);
		}
	});

	// If this Deal exited the happy path, draw one extra red connector +
	// dot after the normal stages, branching off from wherever it got to.
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

/**
 * Draws the chronological "Stage Timeline" list on the Timeline tab --
 * every stage this Deal has ever passed through, oldest first, each entry
 * showing who changed it and when. Purely a read-only history view (as
 * opposed to the progress bar above, which is also clickable/interactive).
 */
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

	// Fetch every Deal Stage Log row for this Deal, oldest first (asc) --
	// deliberately the opposite order from render_stage_progress()'s lookup
	// above, which wants the newest matching row (desc) instead.
	frappe.call({
		method: "frappe.client.get_list",
		args: {
			doctype: "Deal Stage Log",
			filters: { deal: frm.doc.name },
			fields: ["stage", "changed_on", "changed_by"],
			order_by: "changed_on asc",
			limit_page_length: 100, // more than enough for any real Deal's stage history
		},
		callback(r) {
			const entries = r.message || [];
			$list.empty();

			if (!entries.length) {
				// A brand-new Deal that was just created (its very first
				// on_update hasn't logged anything yet, or logging somehow
				// failed) -- show a friendly empty state instead of a blank
				// area that looks broken.
				$list.append(`<div class="text-muted small">${__("No stage history recorded yet.")}</div>`);
				return;
			}

			entries.forEach((e) => {
				const is_exit = DEAL_EXIT_STAGES.includes(e.stage);
				// Colour-codes exit stages in red, everything else in the
				// standard blue -- the same colour language as the progress
				// bar above, so the two views feel consistent.
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
