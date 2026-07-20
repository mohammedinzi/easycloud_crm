import hashlib
import hmac

import frappe
import requests
from frappe.utils.file_manager import save_file


@frappe.whitelist()
def record_voice_note():
	uploaded = frappe.request.files.get("file")
	if not uploaded:
		frappe.throw("No audio file received.")

	file_doc = save_file(
		uploaded.filename,
		uploaded.read(),
		None,
		None,
		is_private=1,
	)

	with open(file_doc.get_full_path(), "rb") as f:
		response = requests.post(
			"http://whisper:8500/transcribe",
			files={"file": (file_doc.file_name, f)},
			timeout=120,
		)
	response.raise_for_status()
	result = response.json()

	return {
		"audio_file": file_doc.file_url,
		"transcript": result.get("transcript", ""),
		"language": result.get("language", ""),
	}


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def meta_lead_webhook():
	if frappe.request.method == "GET":
		return _verify_meta_webhook_subscription()
	return _handle_meta_webhook_notification()


def _verify_meta_webhook_subscription():
	args = frappe.request.args
	verify_token = frappe.conf.get("meta_webhook_verify_token")

	if (
		verify_token
		and args.get("hub.mode") == "subscribe"
		and args.get("hub.verify_token") == verify_token
	):
		challenge = args.get("hub.challenge", "")
		frappe.response["type"] = "download"
		frappe.response["filename"] = "challenge.txt"
		frappe.response["filecontent"] = challenge
		frappe.response["content_type"] = "text/plain"
		frappe.response["display_content_as"] = "inline"
		return

	frappe.local.response.http_status_code = 403
	return "Verification failed."


def _handle_meta_webhook_notification():
	raw_body = frappe.request.get_data()
	if not _is_valid_meta_signature(raw_body, frappe.request.headers.get("X-Hub-Signature-256")):
		frappe.local.response.http_status_code = 403
		return {"error": "Invalid signature"}

	payload = frappe.parse_json(raw_body.decode("utf-8"))
	for entry in payload.get("entry", []):
		for change in entry.get("changes", []):
			value = change.get("value", {})
			leadgen_id = value.get("leadgen_id")
			if not leadgen_id:
				continue
			frappe.enqueue(
				"easycloud_crm.meta_leads.process_meta_lead",
				queue="long",
				leadgen_id=leadgen_id,
				form_id=value.get("form_id"),
				ad_id=value.get("ad_id"),
				created_time=value.get("created_time"),
			)

	return {"status": "ok"}


def _is_valid_meta_signature(raw_body, signature_header):
	app_secret = frappe.conf.get("meta_app_secret")
	if not app_secret or not signature_header or not signature_header.startswith("sha256="):
		return False

	expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
	provided = signature_header.split("=", 1)[1]
	return hmac.compare_digest(expected, provided)
