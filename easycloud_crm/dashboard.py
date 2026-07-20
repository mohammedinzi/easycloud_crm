def get_lead_dashboard_data(data):
	data.setdefault("transactions", []).append({"label": "Pipeline", "items": ["Deal", "CRM Activity"]})
	return data
