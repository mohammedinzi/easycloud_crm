# ==============================================================================
# doctype/deal/deal_dashboard.py -- powers the "Connections" tab on the Deal
# form (the sidebar section showing counts + links to related records).
# Frappe auto-discovers this file purely by its name/location -- living
# next to deal.json in Deal's own doctype folder -- no hooks.py entry
# needed (compare to Lead's dashboard.py, which DOES need a hooks.py
# `override_doctype_dashboards` entry, because Lead is a standard doctype
# whose own folder lives inside erpnext, not this app).
#
# Confirmed this convention against erpnext's own Project doctype, which
# shows its Tasks the exact same way via
# erpnext/projects/doctype/project/project_dashboard.py.
# ==============================================================================


def get_data():
	"""Frappe calls this to build Deal's Connections tab.

	"fieldname": the Link field most linked doctypes would use to point
	    back at a Deal, if they used the default/expected name "deal" --
	    acts as a fallback for anything not listed in
	    non_standard_fieldnames below (nothing currently needs it, since
	    Task's field is a non-standard name, but it's still expected by
	    the framework's own dashboard renderer).
	"non_standard_fieldnames": Task's field pointing back at Deal is
	    called `custom_deal`, not `deal` -- this tells Frappe to filter
	    Task by THAT field instead of assuming the default name.
	"transactions": the actual sections shown, each a group of doctypes
	    under one label. Deliberately just Task here, not CRM Activity --
	    CRM Activity already has its own rich, always-visible panel
	    directly on the Activities tab (see deal.js), so repeating it here
	    would just be a redundant, buried second copy of the same thing.
	"""
	return {
		"fieldname": "deal",
		"non_standard_fieldnames": {"Task": "custom_deal"},
		"transactions": [{"label": "Tasks", "items": ["Task"]}],
	}
