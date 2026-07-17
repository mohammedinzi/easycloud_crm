def get_lead_dashboard_data(data):
	data.setdefault("transactions", []).append(
		{"label": "Pipeline", "items": ["Deal", "CRM Activity", "Task"]}
	)
	data.setdefault("non_standard_fieldnames", {})["Task"] = "custom_lead"
	return data
