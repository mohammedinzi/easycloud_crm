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
