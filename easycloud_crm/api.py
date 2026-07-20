# ==============================================================================
# easycloud_crm/api.py
#
# Every function here decorated with @frappe.whitelist() is a real HTTP API
# endpoint, callable at:
#     https://<your-site>/api/method/easycloud_crm.api.<function_name>
# Nothing calls these functions directly from other Python files in this app
# (except meta_leads.py, which is triggered BY the webhook below, not the
# other way round) -- they only exist to be hit over the network, either by
# a browser (voice notes) or by Meta's own servers (the lead-ads webhook).
#
# This file holds TWO unrelated features that both happen to be "public API
# endpoints" -- that's the only thing they have in common:
#   1. record_voice_note()     -- upload+transcribe a voice note (Whisper)
#   2. meta_lead_webhook()      -- receive new leads pushed by Meta Ads
# ==============================================================================

import hashlib
import hmac

import frappe
import requests
from frappe.utils.file_manager import save_file


@frappe.whitelist()
def record_voice_note():
	"""Called from the browser (see public/js/voice_note.js) once someone
	finishes recording audio in the "🎤 Voice Note" dialog on a Deal or CRM
	Activity form. Saves the audio as a File in Frappe, sends it to our
	self-hosted Whisper speech-to-text container for transcription, and
	hands both the saved file's URL and the transcript text back to the
	browser so it can pre-fill the form.

	Note: no explicit permission check beyond the plain @frappe.whitelist()
	(which just requires *some* logged-in session) -- anyone who can reach
	the Desk UI at all can call this. That's intentional: recording a voice
	note isn't a sensitive action gated by doctype-level permissions.
	"""
	# frappe.request is Frappe's wrapper around the raw Werkzeug/Flask
	# request object for the current HTTP call. The browser sends the
	# recorded audio as multipart/form-data under the field name "file"
	# (see voice_note.js's `form_data.append("file", blob, ...)`).
	uploaded = frappe.request.files.get("file")
	if not uploaded:
		frappe.throw("No audio file received.")

	# save_file() is Frappe's standard helper for turning raw bytes into a
	# proper "File" document (the same mechanism behind every attachment in
	# Frappe). is_private=1 means the audio is NOT publicly downloadable by
	# guessing its URL -- only users with permission on the linked document
	# can fetch it, same as any other private attachment.
	file_doc = save_file(
		uploaded.filename,
		uploaded.read(),
		None,  # attached_to_doctype -- left blank; we don't know which CRM Activity/Deal this belongs to yet at upload time
		None,  # attached_to_name -- same reason; the browser links it to a real record afterwards via its own save
		is_private=1,
	)

	# Whisper (the transcription service) only accepts a real file upload,
	# not raw bytes in memory, so we re-open the file we just saved to disk
	# and stream it over. "whisper" here is a Docker Compose service name --
	# see monitoring/../docker-compose.yml's `whisper` container; this only
	# resolves inside the same Docker network, it isn't a public hostname.
	with open(file_doc.get_full_path(), "rb") as f:
		response = requests.post(
			"http://whisper:8500/transcribe",
			files={"file": (file_doc.file_name, f)},
			timeout=120,  # transcription can take a while for longer recordings
		)
	response.raise_for_status()  # turns a non-2xx response into a raised exception instead of silently continuing
	result = response.json()

	# This dict becomes the JSON body of the API response (Frappe wraps
	# whatever a whitelisted function returns in {"message": ...}
	# automatically) -- voice_note.js reads `r.message.audio_file` etc.
	return {
		"audio_file": file_doc.file_url,
		"transcript": result.get("transcript", ""),
		"language": result.get("language", ""),
	}


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def meta_lead_webhook():
	"""The single URL Meta (Facebook/Instagram Lead Ads) is configured to call:
	https://<your-site>/api/method/easycloud_crm.api.meta_lead_webhook

	Meta uses ONE endpoint for two very different purposes, distinguished
	purely by HTTP method:
	  - GET  -> Meta is verifying you actually own this URL (done once, when
	            you first register the webhook in their dashboard).
	  - POST -> Meta is telling you "a new lead just came in, go fetch it".

	allow_guest=True is required because Meta's servers aren't logged into
	your Frappe site -- they can't be, they're not a real user. Security here
	comes from a totally different mechanism than a login session: the
	verify_token (for GET) and the HMAC signature (for POST) -- see below.
	"""
	if frappe.request.method == "GET":
		return _verify_meta_webhook_subscription()
	return _handle_meta_webhook_notification()


def _verify_meta_webhook_subscription():
	"""Handles Meta's one-time "prove you own this URL" handshake.

	Meta sends a GET request with a `hub.challenge` value and expects the
	exact same value echoed straight back -- but ONLY if `hub.verify_token`
	matches a secret we chose ourselves when registering the webhook (stored
	in site_config.json as `meta_webhook_verify_token`, never in git). This
	stops a random stranger from pointing their own Meta app at your URL and
	tricking it into "verifying" for them.
	"""
	args = frappe.request.args  # the URL's ?query=string parameters
	verify_token = frappe.conf.get("meta_webhook_verify_token")

	if (
		verify_token
		and args.get("hub.mode") == "subscribe"
		and args.get("hub.verify_token") == verify_token
	):
		challenge = args.get("hub.challenge", "")
		# Meta expects the challenge value back as plain text, not as
		# Frappe's usual JSON-wrapped response -- these frappe.response
		# fields override the default JSON behaviour for this one request.
		frappe.response["type"] = "download"
		frappe.response["filename"] = "challenge.txt"
		frappe.response["filecontent"] = challenge
		frappe.response["content_type"] = "text/plain"
		frappe.response["display_content_as"] = "inline"
		return

	# Wrong or missing token: refuse the handshake outright.
	frappe.local.response.http_status_code = 403
	return "Verification failed."


def _handle_meta_webhook_notification():
	"""Handles the real, ongoing traffic: Meta POSTing "a lead just came in".

	Crucially, Meta's webhook payload does NOT contain the lead's actual
	answers (name, email, phone, ...) -- just a `leadgen_id` pointer. This
	function's only job is to verify the request is genuinely from Meta, then
	hand off to a background job (meta_leads.process_meta_lead) that goes
	back to Meta's Graph API to fetch the real answers using that ID. See
	meta_leads.py for that part of the flow.
	"""
	raw_body = frappe.request.get_data()  # the exact raw bytes Meta sent, needed unmodified for signature checking below
	if not _is_valid_meta_signature(raw_body, frappe.request.headers.get("X-Hub-Signature-256")):
		# Someone (or something) sent us a POST that doesn't carry a valid
		# Meta signature -- could be a replay, a bug, or a random attacker
		# probing the endpoint. Refuse it rather than trusting the payload.
		frappe.local.response.http_status_code = 403
		return {"error": "Invalid signature"}

	payload = frappe.parse_json(raw_body.decode("utf-8"))
	# Meta's payload can bundle MULTIPLE lead notifications into one HTTP
	# call (e.g. several leads arriving close together), hence the nested
	# loop: one webhook call -> multiple "entry" objects -> each entry can
	# have multiple "changes" -> each change is (usually) one new lead.
	for entry in payload.get("entry", []):
		for change in entry.get("changes", []):
			value = change.get("value", {})
			leadgen_id = value.get("leadgen_id")
			if not leadgen_id:
				continue  # not a lead-generation event we care about; skip it

			# frappe.enqueue hands this off to a BACKGROUND worker instead of
			# processing it right here in the web request. Two reasons this
			# matters: (1) fetching the lead's real data from Meta's Graph
			# API is a slow network call we don't want to make Meta's own
			# webhook request wait on, and (2) Meta expects a fast HTTP
			# response and will consider the webhook "unhealthy" and retry
			# aggressively (or eventually disable it) if we're slow to
			# respond. queue="long" just picks which worker pool handles it
			# (see the `queue-long` container in docker-compose.yml).
			frappe.enqueue(
				"easycloud_crm.meta_leads.process_meta_lead",
				queue="long",
				leadgen_id=leadgen_id,
				form_id=value.get("form_id"),
				ad_id=value.get("ad_id"),
				created_time=value.get("created_time"),
			)

	# Meta just needs to see SOME 200-ish response quickly to know we
	# received the notification -- it doesn't inspect this body.
	return {"status": "ok"}


def _is_valid_meta_signature(raw_body, signature_header):
	"""Confirms a webhook POST genuinely came from Meta and wasn't tampered
	with in transit, using the same technique most webhook providers use:
	Meta signs the exact request body with a shared secret
	(`meta_app_secret`, from your Meta App's dashboard, stored only in
	site_config.json) and sends the signature in the X-Hub-Signature-256
	header. We recompute that same signature ourselves from the raw bytes we
	received and compare.

	If even a single byte of the payload changed in transit (or someone is
	trying to forge a fake "new lead" notification without knowing the
	secret), the signatures won't match.
	"""
	app_secret = frappe.conf.get("meta_app_secret")
	if not app_secret or not signature_header or not signature_header.startswith("sha256="):
		return False

	expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
	provided = signature_header.split("=", 1)[1]  # strip the "sha256=" prefix, keep just the hex digest
	# hmac.compare_digest (rather than `==`) deliberately takes the same
	# amount of time to run regardless of where the strings first differ --
	# a plain `==` would leak, via response timing, how many leading
	# characters of a forged signature happened to be correct, giving an
	# attacker a way to guess the right signature one byte at a time.
	return hmac.compare_digest(expected, provided)
