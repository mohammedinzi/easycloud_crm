# ==============================================================================
# easycloud_crm/hooks.py
#
# THIS IS THE APP'S "MANIFEST" -- START READING THE CODEBASE HERE.
#
# Frappe (the framework this app is built on) reads this single file to learn
# everything about how easycloud_crm plugs into the system: what extra fields
# it bolts onto standard doctypes (Lead, Task, ...), what JavaScript/CSS to
# load on which pages, what Python functions to run when a document is saved,
# etc. Every "hook" below is just a variable with a name Frappe already knows
# to look for -- nothing here is easycloud_crm-specific plumbing, it's all
# Frappe's own hook system. Anything NOT listed here (most business logic)
# lives in the doctype folders under easycloud_crm/easycloud_crm/doctype/.
#
# Most of the file below (all the "# commented_out_example = ..." blocks) is
# Frappe's own default scaffold that ships with every new app and was never
# deleted -- it's not in use. Only the *uncommented* assignments below
# (fixtures, app_include_js, doctype_js, jinja, doc_events,
# override_doctype_dashboards) are actually active.
# ==============================================================================

app_name = "easycloud_crm"
app_title = "Easycloud CRM"
app_publisher = "inzi"
app_description = "Manage Easycloud CRM"
app_email = "minzemam007@gmail.com"
app_license = "mit"

# Fixtures
# ------------------
# data that should ship with the app instead of living only in this database
#
# WHAT THIS IS: normally, if you add a field to a standard doctype (like Lead)
# through the Frappe UI, that change only lives in *this* site's database --
# it would NOT come along if you installed the app fresh somewhere else.
# "Fixtures" are the fix: every time someone runs
#   bench export-fixtures --app easycloud_crm
# Frappe looks at the filters below, finds the matching records in the
# database, and writes them out as JSON files under easycloud_crm/fixtures/.
# Those JSON files ARE tracked in git, so a fresh install of this app
# automatically recreates every custom field / property setter / etc. listed
# here. If you change one of these values in the UI, you MUST re-run
# export-fixtures and commit the updated fixtures/*.json, or your change will
# be invisible to every other environment (and will vanish on next migrate).
#
# Each block below targets one doctype and filters down to just the specific
# records this app owns (never "export everything of this type" -- that would
# also sweep up unrelated records other apps or the site owner created).
fixtures = [
	{
		# Custom Field: extra fields bolted onto STANDARD doctypes we don't own
		# (Task, Lead). Defined via the UI / scripts, not hand-written JSON --
		# see easycloud_crm/fixtures/custom_field.json for the actual field
		# definitions (fieldtype, label, options, etc.) this filter exports.
		"doctype": "Custom Field",
		"filters": [
			[
				"name",
				"in",
				[
					"Task-custom_lead",  # links a Task back to the Lead it's about
					"Task-custom_deal",  # links a Task back to the Deal it's about
					"Lead-source_received_date",  # when this lead actually arrived (vs. when we noticed it)
					"Lead-source_detail",  # free-text detail about the Lead Source (e.g. "ad:123 form:456" for Meta Ads)
					"Lead-stage",  # our own New/Contacted/Qualified/Do Not Contact pipeline -- see lead.py
					"Lead-do_not_contact_reason",  # required once stage = "Do Not Contact", see lead.py's validate()
					"Lead-meta_leadgen_id",  # Meta's own ID for a lead, used to de-dupe webhook replays -- see meta_leads.py
					"Lead-current_erp",  # captured from the Meta Ads form question about their current ERP
					"Lead-custom_crm_activities_html",  # placeholder field that renders the CRM Activity panel -- see public/js/crm_activities_panel.js
					"Lead-stage_changed_on",  # timestamp auto-set whenever `stage` changes, see lead.py's on_update()
				],
			]
		],
	},
	{
		# Lead Source: the dropdown options for "where did this lead come
		# from". These are plain data records (no custom fields involved) --
		# fixture-exporting them just means every environment gets the same
		# starting list instead of starting empty.
		"doctype": "Lead Source",
		"filters": [
			[
				"name",
				"in",
				[
					"Website",
					"Instagram",
					"Referral",
					"LinkedIn",
					"WhatsApp",
					"Email",
					"Partners for Sales",
					"Meta Ads",  # auto-assigned by meta_leads.py for every Lead created from the Meta webhook
				],
			]
		],
	},
	{
		# Assignment Rule: Frappe's native auto-assignment feature (Round
		# Robin/Load Balancing/etc.) -- routes every new Lead to a Sales
		# User automatically, creating a real ToDo, which in turn triggers
		# the "Assignment Email Notification" above for free.
		"doctype": "Assignment Rule",
		"filters": [["name", "=", "Lead Auto Assignment"]],
	},
	{
		# Role: a custom permission role (e.g. for marketing team members who
		# should see leads/reports but not edit deals). See each doctype's
		# .json "permissions" section for what this role can actually do.
		"doctype": "Role",
		"filters": [["name", "=", "Marketing User"]],
	},
	{
		# Notification: Frappe's built-in "email alert" feature (Settings >
		# Notification in the Desk UI). These two fire automatically -- no
		# custom Python needed -- see easycloud_crm/fixtures/notification.json
		# for the actual email subject/HTML template each one sends.
		"doctype": "Notification",
		"filters": [
			[
				"name",
				"in",
				[
					"Assignment Email Notification",  # emails whoever a Lead/Deal/CRM Activity/etc. gets assigned to (fires on ToDo "New")
					"New Lead Email to Shruti",  # emails shruti@easycloud.in every time a new Lead is created, any source
					"Stale Deal Follow-up Reminder",  # emails a Deal's owner if last_contacted_on is 3+ days old and the Deal is still active
				],
			]
		],
	},
	{
		# Property Setter: a tweak to a field/doctype's BEHAVIOR (hide it,
		# make it appear in list view, change its dropdown options, ...)
		# without touching that doctype's own JSON file directly -- the
		# sanctioned way to customize a standard doctype (Lead) or another
		# app's doctype without forking its source.
		"doctype": "Property Setter",
		"filters": [
			[
				"name",
				"in",
				[
					"User-default_workspace-default",  # makes "EasyCloud CRM" the default workspace every user lands on after login
					"Lead-main-show_title_field_in_link",  # shows Lead's computed title (not raw ID) wherever a Lead is picked/linked
					"Lead-status-hidden",  # hides stock Lead's own "status" field -- we use our own custom "stage" field instead
					"Lead-source-in_list_view",  # shows "Source" as a column in the Lead list view
					"Lead-no_of_employees-options",  # expanded to include Meta Ads' real employee-count buckets, see meta_leads.py
					"Lead-notes_tab-hidden",  # hides stock Lead's "Notes" tab -- it actually held Qualification fields, not notes, and confused users
				],
			]
		],
	},
]

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "easycloud_crm",
# 		"logo": "/assets/easycloud_crm/logo.png",
# 		"title": "Easycloud CRM",
# 		"route": "/easycloud_crm",
# 		"has_permission": "easycloud_crm.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
#
# WHAT THIS IS: these files load on EVERY Desk page (the admin/back-office UI),
# not just one doctype's form -- that's the difference from doctype_js below.
# The actual source lives at easycloud_crm/public/css/ and
# easycloud_crm/public/js/; "bench build" copies/symlinks it into
# sites/assets/easycloud_crm/... which is the path browsers actually request
# (see easycloud_crm_shared_assets_volume in project memory if these ever
# 404 in production -- it's an infra/deploy issue, not a code issue).
app_include_css = [
	"/assets/easycloud_crm/css/theme.css",  # site-wide colour/branding tweaks
	"/assets/easycloud_crm/css/easycloud_crm.css",  # this app's own custom styles
]
app_include_js = [
	"/assets/easycloud_crm/js/voice_note.js",  # defines window.open_voice_note_dialog(), used by Deal + CRM Activity's "🎤 Voice Note" buttons
	"/assets/easycloud_crm/js/workspace_icons.js",  # custom icons for the EasyCloud CRM workspace's shortcut/number-card tiles
	"/assets/easycloud_crm/js/crm_activities_panel.js",  # defines window.render_crm_activities_panel(), used by both lead.js and deal.js
]

# include js, css files in header of web template
# web_include_css = "/assets/easycloud_crm/css/easycloud_crm.css"
# web_include_js = "/assets/easycloud_crm/js/easycloud_crm.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "easycloud_crm/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
#
# doctype_js loads ONLY when that one doctype's FORM is open (unlike
# app_include_js above, which loads everywhere). Deal and CRM Activity each
# have their own controller file living right next to their .json/.py files
# (easycloud_crm/easycloud_crm/doctype/deal/deal.js and
# .../crm_activity/crm_activity.js) -- Frappe auto-discovers those by
# folder convention, so only Lead needs an explicit entry here (its
# controller lives at the top level, public/js/lead.js, not in a doctype
# folder, because Lead itself is a STANDARD doctype we don't own -- we can't
# add files inside erpnext's own folder structure).
doctype_js = {"Lead": "public/js/lead.js"}

# doctype_list_js loads on a doctype's LIST view (the table of records), not
# its form. Used here purely for cosmetics -- see crm_activity_list.js, which
# adds an icon (📞 🤝 📧 ...) next to each row based on its Activity Type;
# pipeline_list_colors.js does the same idea for Lead/Deal's `stage` column,
# turning the plain text into a colored pill (see theme.css's
# --ec-lead-*/--ec-deal-* tokens for the actual colors used).
doctype_list_js = {
	"CRM Activity": "public/js/crm_activity_list.js",
	"Lead": "public/js/pipeline_list_colors.js",
	"Deal": "public/js/pipeline_list_colors.js",
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "easycloud_crm/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
#
# Jinja is the templating language used inside things like the Notification
# email templates (fixtures/notification.json) -- e.g. their subject/message
# fields contain "{{ doc.company_name }}"-style placeholders. Those templates
# run in a locked-down "sandbox" that can't call arbitrary Python for
# security, so if we want a template to call OUR OWN helper function, we have
# to explicitly register it here. "methods": "easycloud_crm.utils" means
# "make every top-level function defined in utils.py available inside any
# Jinja template, site-wide". Right now that's just
# notification_reference_label() -- see utils.py for what it does and why it
# exists (short version: makes the assignment email show a Lead/Deal's name
# instead of a raw CRM Activity ID).
#
# GOTCHA (learned the hard way): this must point at the MODULE itself
# ("easycloud_crm.utils"), not at a dict of functions defined inside it
# (e.g. "easycloud_crm.utils.jinja_methods") -- Frappe's loader only
# understands "a whole module" or "one function", not "a dict constant".
jinja = {
	"methods": "easycloud_crm.utils",
}

# Installation
# ------------

# before_install = "easycloud_crm.install.before_install"
# after_install = "easycloud_crm.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "easycloud_crm.uninstall.before_uninstall"
# after_uninstall = "easycloud_crm.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "easycloud_crm.utils.before_app_install"
# after_app_install = "easycloud_crm.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "easycloud_crm.utils.before_app_uninstall"
# after_app_uninstall = "easycloud_crm.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "easycloud_crm.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events
#
# WHAT THIS IS: runs OUR functions automatically at specific moments in a
# document's lifecycle, without touching Lead's own (framework-owned) source
# code. "validate" fires every time a Lead is about to be saved (before the
# save actually happens -- can still block it by raising an error).
# "on_update" fires right after a successful save. Both point at plain
# functions in easycloud_crm/lead.py -- open that file next to see exactly
# what happens at each step (short version: validate() blocks saving a Lead
# as "Do Not Contact" with no reason given; on_update() auto-creates a Deal
# the moment a Lead's stage becomes "Qualified").
doc_events = {
	"Lead": {
		"validate": "easycloud_crm.lead.validate",
		"on_update": "easycloud_crm.lead.on_update",
	}
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"easycloud_crm.tasks.all"
# 	],
# 	"daily": [
# 		"easycloud_crm.tasks.daily"
# 	],
# 	"hourly": [
# 		"easycloud_crm.tasks.hourly"
# 	],
# 	"weekly": [
# 		"easycloud_crm.tasks.weekly"
# 	],
# 	"monthly": [
# 		"easycloud_crm.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "easycloud_crm.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "easycloud_crm.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "easycloud_crm.task.get_dashboard_data"
# }

# This is what makes a Lead's "Connections" sidebar (the little counters
# showing "2 Deals", "5 CRM Activities" linked to this Lead) show OUR related
# doctypes instead of Frappe's stock defaults for Lead. See dashboard.py.
override_doctype_dashboards = {"Lead": "easycloud_crm.dashboard.get_lead_dashboard_data"}

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["easycloud_crm.utils.before_request"]
# after_request = ["easycloud_crm.utils.after_request"]

# Job Events
# ----------
# before_job = ["easycloud_crm.utils.before_job"]
# after_job = ["easycloud_crm.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"easycloud_crm.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []
