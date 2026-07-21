# ==============================================================================
# easycloud_crm/dashboard.py
#
# Wired up via hooks.py's override_doctype_dashboards = {"Lead": ...}.
# Controls what shows up in a Lead form's "Connections" sidebar tab -- the
# little grouped counters like "2 Deals" / "5 CRM Activities" that link to
# everything related to this specific Lead.
# ==============================================================================


def get_lead_dashboard_data(data):
	"""Frappe calls this with `data` already pre-filled with Lead's stock
	dashboard config (whatever erpnext ships by default for Lead); we just
	add our own extra section on top rather than replacing anything.

	data: a dict Frappe builds and expects back in the same shape --
	      "transactions" is the list of grouped-counter sections shown in
	      the Connections tab, each one a {"label": ..., "items": [...]}
	      dict where "items" are DOCTYPE NAMES to count and link to. Frappe
	      finds documents of that doctype by looking for a Link field
	      pointing back at this Lead named "lead" by default -- Deal and
	      CRM Activity's own linking fields happen to already be called
	      exactly that, so they need no extra config. Task's equivalent
	      field is called `custom_lead` instead (a non-standard name), so
	      it has to be spelled out explicitly in non_standard_fieldnames
	      below, or Frappe would look for a field that doesn't exist and
	      show nothing.
	"""
	# Adds one new section titled "Pipeline" showing how many Deals, CRM
	# Activities, and Tasks are linked to this Lead. setdefault(...) means:
	# if Lead's stock config didn't already have a "transactions"/
	# "non_standard_fieldnames" entry for some reason, start a new empty
	# one instead of crashing on a missing key.
	data.setdefault("transactions", []).append({"label": "Pipeline", "items": ["Deal", "CRM Activity", "Task"]})
	data.setdefault("non_standard_fieldnames", {})["Task"] = "custom_lead"
	return data
