function open_voice_note_dialog(on_save) {
	const MIME_CANDIDATES = ["audio/webm;codecs=opus", "audio/mp4", "audio/ogg;codecs=opus"];
	const MAX_SECONDS = 300;

	let mediaRecorder = null;
	let stream = null;
	let chunks = [];
	let usedMimeType = "";
	let seconds = 0;
	let timerHandle = null;

	const dialog = new frappe.ui.Dialog({
		title: "Voice Note",
		fields: [
			{ fieldname: "recorder_html", fieldtype: "HTML" },
			{ fieldname: "transcript", label: "Transcript", fieldtype: "Text Editor" },
		],
		primary_action_label: "Save",
		primary_action: () => {
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
				stream.getTracks().forEach((t) => t.stop());
			}
		},
	});

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
		try {
			stream = await navigator.mediaDevices.getUserMedia({ audio: true });
		} catch (err) {
			frappe.msgprint("Microphone permission was not granted.");
			return;
		}

		const supported = MIME_CANDIDATES.find((t) => MediaRecorder.isTypeSupported(t));
		mediaRecorder = supported ? new MediaRecorder(stream, { mimeType: supported }) : new MediaRecorder(stream);

		chunks = [];
		mediaRecorder.ondataavailable = (e) => e.data.size && chunks.push(e.data);
		mediaRecorder.onstop = handle_recording_stopped;
		mediaRecorder.start();

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
		mediaRecorder.stop();
		stream.getTracks().forEach((t) => t.stop());
		$stop.hide();
		$status.text("Processing…");
	});

	function handle_recording_stopped() {
		usedMimeType = mediaRecorder.mimeType || "audio/webm";
		const blob = new Blob(chunks, { type: usedMimeType });
		$playback.attr("src", URL.createObjectURL(blob)).show();
		$status.text("Transcribing…");

		const extension = usedMimeType.includes("mp4") ? "m4a" : usedMimeType.includes("ogg") ? "ogg" : "webm";
		const form_data = new FormData();
		form_data.append("file", blob, `voice_note_${Date.now()}.${extension}`);

		fetch("/api/method/easycloud_crm.api.record_voice_note", {
			method: "POST",
			headers: { "X-Frappe-CSRF-Token": frappe.csrf_token },
			body: form_data,
		})
			.then((r) => r.json())
			.then((r) => {
				const data = r.message || {};
				dialog.audio_file_url = data.audio_file;
				dialog.set_value("transcript", data.transcript || "");
				$status.text(`Done${data.language ? ` (detected language: ${data.language})` : ""}`);
			})
			.catch(() => {
				$status.text("Transcription failed — the audio above is still fine to save; add the transcript by hand if it matters.");
			});
	}

	dialog.show();
}
