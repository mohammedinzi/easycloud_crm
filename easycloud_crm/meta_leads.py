import re

import frappe
import requests

GRAPH_API_VERSION = "v19.0"

FIELD_MAP = {
	"full_name": "lead_name",
	"company_name": "company_name",
	"email": "email_id",
	"work_email_address": "email_id",
	"phone": "mobile_no",
	"phone_number": "mobile_no",
	"which_industry_does_your_business_belong_to?": "_meta_industry_raw",
	"which_erp_are_you_currently_using?": "current_erp",
	"number_of_employees_at_your_company?": "_meta_employee_count_raw",
	"you_company's_annual_revenue": "_meta_annual_revenue_raw",
}


def process_meta_lead(leadgen_id, form_id=None, ad_id=None, created_time=None):
	if frappe.db.exists("Lead", {"meta_leadgen_id": leadgen_id}):
		return

	access_token = frappe.conf.get("meta_access_token")
	response = requests.get(
		f"https://graph.facebook.com/{GRAPH_API_VERSION}/{leadgen_id}",
		headers={"Authorization": f"Bearer {access_token}"},
		timeout=30,
	)
	response.raise_for_status()
	field_data = response.json().get("field_data", [])

	lead_values = map_field_data_to_lead(field_data)
	lead_values["meta_leadgen_id"] = leadgen_id
	lead_values["source"] = "Meta Ads"
	lead_values["source_detail"] = _build_source_detail(form_id, ad_id)
	if created_time:
		lead_values["source_received_date"] = frappe.utils.get_datetime(created_time).date()

	lead = frappe.get_doc({"doctype": "Lead", **lead_values})
	lead.insert(ignore_permissions=True)
	return lead.name


def map_field_data_to_lead(field_data):
	values = {}
	for entry in field_data:
		fieldname = FIELD_MAP.get(entry.get("name"))
		if not fieldname:
			continue
		entry_values = entry.get("values") or []
		if not entry_values or fieldname in values:
			continue
		value = entry_values[0]
		if fieldname == "mobile_no" and value.startswith("p:"):
			value = value[2:]
		values[fieldname] = value

	return _apply_bucketed_field_conversions(values)


def _apply_bucketed_field_conversions(values):
	industry_raw = values.pop("_meta_industry_raw", None)
	if industry_raw:
		values["industry"] = get_or_create_industry_type(industry_raw)

	employee_raw = values.pop("_meta_employee_count_raw", None)
	if employee_raw:
		values["no_of_employees"] = normalize_employee_bucket(employee_raw)

	revenue_raw = values.pop("_meta_annual_revenue_raw", None)
	if revenue_raw:
		lower_bound = parse_revenue_lower_bound_in_cr(revenue_raw)
		if lower_bound is not None:
			values["annual_revenue"] = lower_bound

	return values


def prettify_bucket_label(raw):
	"""'retail_&_distribution' -> 'Retail & Distribution'"""
	words = raw.replace("_", " ").split()
	return " ".join(w.upper() if w == "&" else w.capitalize() for w in words)


def get_or_create_industry_type(raw_industry):
	name = prettify_bucket_label(raw_industry)
	if not frappe.db.exists("Industry Type", name):
		frappe.get_doc({"doctype": "Industry Type", "industry": name}).insert(ignore_permissions=True)
	return name


def normalize_employee_bucket(raw_bucket):
	"""'101_-_200' -> '101-200'"""
	return raw_bucket.replace("_", "")


def parse_revenue_lower_bound_in_cr(raw_bucket):
	"""'₹100–500_cr' -> 100.0, 'above_₹500_cr' -> 500.0 (lower bound, in Cr)"""
	cleaned = raw_bucket.replace("₹", "").replace("_cr", "").replace("cr", "")
	if cleaned.lower().startswith("above_"):
		cleaned = cleaned[len("above_") :]
	first_number = re.search(r"[\d,]+", cleaned)
	if not first_number:
		return None
	return float(first_number.group().replace(",", ""))


def _build_source_detail(form_id, ad_id):
	parts = []
	if ad_id:
		parts.append(f"ad:{ad_id}")
	if form_id:
		parts.append(f"form:{form_id}")
	return " ".join(parts) or None
