// ==============================================================================
// public/js/voice_note.js -- loaded on EVERY Desk page (see hooks.py's
// app_include_js), so open_voice_note_dialog() below is a plain GLOBAL
// function, callable from any form's controller. Currently used by two
// places: doctype/deal/deal.js and doctype/crm_activity/crm_activity.js,
// both of which add a "🎤 Voice Note" button that calls this.
//
// THE FULL FLOW, START TO FINISH:
//   1. open_voice_note_dialog() opens a small dialog with Start/Stop
//      recording buttons.
//   2. Recording uses the browser's own MediaRecorder API -- audio never
//      leaves the browser until Stop is pressed.
//   3. On Stop, the recorded audio is uploaded to our backend
//      (easycloud_crm.api.record_voice_note, see ../../api.py), which saves
//      it as a File and sends it to our self-hosted Whisper service for
//      transcription, returning both the saved file's URL and the
//      transcript text.
//   4. Once that response comes back, `on_save(...)` (a callback the
//      CALLER provides -- see deal.js/crm_activity.js) is fired with the
//      result, letting each caller decide what to do with it (create a new
//      CRM Activity, or fill in the current record's own fields).
// ==============================================================================

/**
 * Opens the Voice Note recording dialog.
 * @param {(result: {audio_file: string, transcript: string}) => void} on_save
 *        Called once the user clicks "Save" in the dialog, with the
 *        uploaded audio file's URL and its transcript (transcript may have
 *        been hand-edited by the user in the dialog before saving, or may
 *        be empty if transcription failed/is still pending).
 */
function open_voice_note_dialog(on_save) {
	// Try these audio formats in order of preference -- MediaRecorder's
	// browser support varies (webm/opus is the best-supported/highest
	// quality option on Chrome/Firefox, mp4 covers Safari, ogg is a last
	// resort fallback). MediaRecorder.isTypeSupported (used below) picks
	// the first one THIS particular browser actually supports.
	const MIME_CANDIDATES = ["audio/webm;codecs=opus", "audio/mp4", "audio/ogg;codecs=opus"];
	const MAX_SECONDS = 300; // hard cap of 5 minutes per recording, to keep uploads/transcription jobs reasonably sized

	// All of this state lives in variables local to this ONE call of
	// open_voice_note_dialog() (a fresh dialog = fresh state each time),
	// captured by the click handlers below via closures rather than being
	// attached to `dialog` or the DOM.
	let mediaRecorder = null; // the browser's MediaRecorder instance, created once recording starts
	let stream = null; // the raw microphone audio stream from getUserMedia
	let chunks = []; // audio data collected in small pieces as MediaRecorder produces them
	let usedMimeType = ""; // whichever MIME type actually got used, needed later to name the uploaded file correctly
	let seconds = 0; // elapsed recording time, for the on-screen timer
	let timerHandle = null; // setInterval handle, so we can stop the timer cleanly

	const dialog = new frappe.ui.Dialog({
		title: "Voice Note",
		fields: [
			// A blank HTML field we manually fill with our own
			// record/stop/playback controls below (Frappe's Dialog doesn't
			// have a built-in "audio recorder" field type).
			{ fieldname: "recorder_html", fieldtype: "HTML" },
			// Editable transcript textbox -- pre-filled automatically once
			// transcription finishes, but the user can correct it by hand
			// before saving (Whisper isn't perfect, especially with names).
			{ fieldname: "transcript", label: "Transcript", fieldtype: "Text Editor" },
		],
		primary_action_label: "Save",
		primary_action: () => {
			// dialog.audio_file_url only gets set once a recording has been
			// successfully uploaded (see handle_recording_stopped below) --
			// if it's still unset, nothing was ever recorded, so there's
			// nothing to save yet.
			if (!dialog.audio_file_url) {
				frappe.msgprint("Record something first.");
				return;
			}
			on_save({
				audio_file: dialog.audio_file_url,
				transcript: dialog.get_value("transcript"),
			});
			dialog.hide();
		},
		onhide: () => {
			// stop the mic if someone closes the dialog mid-recording
			clearInterval(timerHandle);
			if (mediaRecorder && mediaRecorder.state !== "inactive") {
				mediaRecorder.stop();
			}
			if (stream) {
				// Crucial: just stopping the MediaRecorder does NOT release
				// the microphone itself -- without this, the browser's
				// "mic in use" indicator would stay on and the mic would
				// stay locked even after the dialog is closed.
				stream.getTracks().forEach((t) => t.stop());
			}
		},
	});

	// Build the actual record/stop/status/playback UI by hand inside the
	// blank recorder_html field from above.
	const $wrapper = dialog.fields_dict.recorder_html.$wrapper;
	$wrapper.html(`
        <button class="btn btn-primary btn-sm" data-action="start">Start Recording</button>
        <button class="btn btn-danger btn-sm" data-action="stop" style="display:none;">Stop</button>
        <span class="voice-note-timer" style="margin-left:10px;"></span>
        <div class="voice-note-status" style="margin-top:10px;"></div>
        <audio class="voice-note-playback" controls style="display:none; margin-top:10px; width:100%;"></audio>
    `);

	const $start = $wrapper.find('[data-action="start"]');
	const $stop = $wrapper.find('[data-action="stop"]');
	const $timer = $wrapper.find(".voice-note-timer");
	const $status = $wrapper.find(".voice-note-status");
	const $playback = $wrapper.find(".voice-note-playback");

	$start.on("click", async () => {
		// getUserMedia is called directly inside this click handler on purpose —
		// deferring it (setTimeout, an intervening await chain, dialog-open instead
		// of button-click) is what makes iOS Safari silently refuse it.
		stream = await request_microphone_access();
		if (!stream) return; // a message was already shown above — nothing else to do here

		// Pick the first MIME type from our preference list that this
		// specific browser actually supports; if somehow NONE of them are
		// (very old/unusual browser), fall back to MediaRecorder's own
		// default rather than failing outright.
		const supported = MIME_CANDIDATES.find((t) => MediaRecorder.isTypeSupported(t));
		mediaRecorder = supported ? new MediaRecorder(stream, { mimeType: supported }) : new MediaRecorder(stream);

		chunks = [];
		// MediaRecorder delivers audio in small chunks as it records
		// (rather than all at once at the end) -- collect every non-empty
		// one; they get combined into a single Blob once recording stops.
		mediaRecorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);
		mediaRecorder.onstop = handle_recording_stopped;
		mediaRecorder.start();

		// Simple MM:SS elapsed-time display, updated once per second, with
		// an automatic stop once MAX_SECONDS is reached (simulates the
		// user clicking Stop themselves, reusing that exact same code path).
		seconds = 0;
		$timer.text("0:00");
		timerHandle = setInterval(() => {
			seconds += 1;
			$timer.text(`${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`);
			if (seconds >= MAX_SECONDS) $stop.trigger("click");
		}, 1000);

		$start.hide();
		$stop.show();
		$status.text("Recording…");
	});

	$stop.on("click", () => {
		clearInterval(timerHandle);
		mediaRecorder.stop(); // triggers the "onstop" handler set above (handle_recording_stopped), asynchronously
		stream.getTracks().forEach((t) => t.stop()); // release the microphone immediately, don't wait for anything else
		$stop.hide();
		$status.text("Processing…");
	});

	function handle_recording_stopped() {
		// mediaRecorder.mimeType reflects whichever format the browser
		// actually ended up using (should match what we requested above,
		// but reading it back here is the more reliable source of truth).
		usedMimeType = mediaRecorder.mimeType || "audio/webm";
		const blob = new Blob(chunks, { type: usedMimeType });
		// Lets the user immediately play back what they just recorded,
		// entirely locally -- URL.createObjectURL doesn't touch the
		// network, this works even before the upload below completes.
		$playback.attr("src", URL.createObjectURL(blob)).show();
		$status.text("Transcribing…");

		// Pick a sensible file extension matching the actual recorded
		// format, so the saved File on the server has a sane filename
		// rather than always ending in something misleading.
		const extension = usedMimeType.includes("mp4") ? "m4a" : usedMimeType.includes("ogg") ? "ogg" : "webm";
		const form_data = new FormData();
		form_data.append("file", blob, `voice_note_${Date.now()}.${extension}`);

		// Uploads to our own backend endpoint (see ../../api.py's
		// record_voice_note), which saves the file AND calls Whisper for
		// transcription before responding -- so this fetch only resolves
		// once BOTH steps are done.
		fetch("/api/method/easycloud_crm.api.record_voice_note", {
			method: "POST",
			headers: { "X-Frappe-CSRF-Token": frappe.csrf_token }, // required by Frappe for any state-changing POST from the browser
			body: form_data,
		})
			.then((r) => r.json())
			.then((r) => {
				// Frappe wraps whitelisted Python functions' return values
				// in {"message": ...} automatically -- r.message is the
				// actual dict record_voice_note() returned.
				const data = r.message || {};
				dialog.audio_file_url = data.audio_file; // stashed directly on the dialog object so primary_action (above) can check it later
				dialog.set_value("transcript", data.transcript || "");
				$status.text(`Done${data.language ? ` (detected language: ${data.language})` : ""}`);
			})
			.catch(() => {
				// Even if transcription/upload fails, the recording itself
				// is still safely playable locally (see $playback above) --
				// this message makes clear the failure is recoverable, not
				// a reason to re-record from scratch.
				$status.text("Transcription failed — the audio above is still fine to save; add the transcript by hand if it matters.");
			});
	}

	dialog.show();
}

/**
 * Asks the browser for microphone access, handling every realistic outcome
 * (granted, denied, no mic present, mic busy elsewhere, previously denied)
 * with a specific, actionable message for each -- rather than one generic
 * "couldn't access microphone" error that leaves the user stuck.
 *
 * @returns {Promise<MediaStream|null>} the live audio stream, or null if
 *          access wasn't granted (a message has already been shown to the
 *          user in every null case, so callers don't need to show their own).
 */
async function request_microphone_access() {
	// navigator.permissions.query for 'microphone' works on Chrome/Firefox/Edge but
	// throws on Safari (confirmed) — so this is a best-effort pre-check, never a
	// requirement. Safari always falls through to calling getUserMedia directly below.
	let priorState = null;
	try {
		if (navigator.permissions && navigator.permissions.query) {
			const status = await navigator.permissions.query({ name: "microphone" });
			priorState = status.state; // 'granted' | 'denied' | 'prompt'
		}
	} catch (e) {
		priorState = null;
	}

	if (priorState === "denied") {
		// We already KNOW this will fail before even trying -- skip
		// straight to the recovery instructions instead of triggering a
		// getUserMedia call that's guaranteed to be rejected.
		show_microphone_recovery_instructions();
		return null;
	}

	try {
		// If permission hasn't been decided yet, this line is what makes the browser's
		// own native "Allow microphone?" pop-up appear — nothing extra is needed for that.
		return await navigator.mediaDevices.getUserMedia({ audio: true });
	} catch (err) {
		// Different browsers/situations throw different named errors --
		// each one gets its own specific, actionable message rather than a
		// single generic "failed" message.
		if (err.name === "NotAllowedError" || err.name === "SecurityError") {
			show_microphone_recovery_instructions();
		} else if (err.name === "NotFoundError" || err.name === "OverconstrainedError") {
			frappe.msgprint("No microphone was found on this device.");
		} else if (err.name === "NotReadableError") {
			frappe.msgprint(
				"The microphone couldn't be accessed — it may already be in use by another app or browser tab. Close anything else using it and try again."
			);
		} else {
			frappe.msgprint(`Couldn't access the microphone (${err.name || "unknown error"}).`);
		}
		return null;
	}
}

/**
 * Shows browser/device-specific step-by-step instructions for re-enabling
 * a previously-denied microphone permission. Once a user says "block" to a
 * site's permission prompt, browsers deliberately stop asking again
 * automatically -- the only way back is the user manually changing the
 * site's permission setting, and where to find that setting differs
 * enough between iOS Safari / desktop Safari / everything else that one
 * generic instruction wouldn't actually help most people.
 */
function show_microphone_recovery_instructions() {
	const ua = navigator.userAgent;
	const isIOS = /iPad|iPhone|iPod/.test(ua);
	// This regex specifically excludes Chrome and Android browsers, both of
	// which also include the word "Safari" in their own user-agent strings
	// for legacy compatibility reasons -- without excluding them, EVERY
	// Chrome/Android browser would incorrectly match "is Safari" too.
	const isSafari = /^((?!chrome|android).)*safari/i.test(ua);

	let steps;
	if (isIOS && isSafari) {
		steps = `<b>On this iPhone/iPad, in Safari:</b>
            <ol>
                <li>Tap the <b>"Aa"</b> icon at the left of the address bar</li>
                <li>Tap <b>Website Settings</b></li>
                <li>Set <b>Microphone</b> to <b>Allow</b>, then reload this page</li>
            </ol>
            If that option isn't there: Settings app → Safari → Microphone → Ask or Allow.`;
	} else if (isSafari) {
		steps = `<b>In Safari, on this Mac:</b>
            <ol>
                <li>Safari menu → <b>Settings</b> → <b>Websites</b> tab → <b>Microphone</b></li>
                <li>Find this site and set it to <b>Allow</b>, then reload this page</li>
            </ol>`;
	} else {
		// Covers Chrome, Firefox, Edge, and everything else -- all of
		// these share roughly the same "padlock icon in the address bar"
		// pattern for site permissions.
		steps = `<b>In this browser:</b>
            <ol>
                <li>Click the lock/info icon next to the address bar</li>
                <li>Find <b>Microphone</b> under site permissions and set it to <b>Allow</b></li>
                <li>Reload this page</li>
            </ol>`;
	}

	frappe.msgprint({
		title: "Microphone access is blocked",
		indicator: "orange",
		message: `Microphone permission was denied for this site previously, so the browser won't ask again on its own — it has to be turned back on manually.<br><br>${steps}`,
	});
}
