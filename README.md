# Easycloud CRM

A sales CRM built as a [Frappe](https://frappeframework.com/) app on top of [ERPNext](https://erpnext.com/) v15. It adds two new record types (Deal, CRM Activity), extends the standard Lead record with its own pipeline, and wires the two together into one connected sales workflow — plus a live Meta (Facebook/Instagram) Lead Ads integration, voice-note transcription, and automated email notifications.

This README has two audiences in mind:
- **Skim "What Is This, Really?" first** if you're new to CRMs/Frappe and just want the shape of the thing.
- **Jump straight to "Codebase Map"** if you already know what a CRM is and just need to find where something lives.

Every source file in this app (every `.py` and `.js`) has a comment block at the top explaining what it does, how it's wired in, and what to read next — this README is the map; the files themselves are the territory.

---

## What Is This, Really? (the simple version)

Imagine a lemonade stand. People walk by. Some say "maybe later," some buy right away, some say "no thanks."

If you kept a notebook, you'd write down:
- Who said "maybe" (a **Lead**)
- What they might buy, and how close you are to a "yes" (a **Deal**)
- Whether they actually said **yes** (**Won**) or **no** (**Lost**, along with *why*)

That notebook is this app. We didn't build a notebook from scratch — we started from ERPNext, which already knows about Leads, Contacts, Customers, and Users, and added just the pages we needed on top: Deal, CRM Activity, and a proper pipeline for both Lead and Deal.

### The actual journey, end to end

```
                    Someone shows interest
                            |
                            v
                     ┌─────────────┐
                     │    LEAD     │   New -> Contacted -> Qualified -> Do Not Contact
                     └─────────────┘        (see easycloud_crm/lead.py)
                            |
              the moment stage = "Qualified"...
                            |
                            v
                 a DEAL is created automatically
                     ┌─────────────┐
                     │    DEAL     │   Qualified -> Proposal Sent -> Demo Given
                     └─────────────┘        -> Negotiation -> Won
                       |            \
                       |             `-> Cold / Lost / Not worth our time / Too Large
                       v                        |
                a Customer record          you record WHY (a Lost Reason)
                is created automatically   and whether they're worth
                (see doctype/deal/deal.py)  advertising to again later
                                                  |
                                                  v
                                     if "Eligible", they show up on the
                                     Retarget Marketing List report for
                                     the marketing team to export
```

Every step above either happens by itself (the code enforces it) or is a deliberate human choice the code refuses to skip (e.g. you cannot mark a Deal "Lost" without saying why).

### Where Leads actually come from

Two ways, both ending up as an ordinary Lead record — nothing downstream cares which one was used:
1. **A person on your team types one in by hand.**
2. **Meta Ads (Facebook/Instagram) sends one automatically.** Someone fills out a Lead Ad form on Facebook or Instagram → Meta calls our webhook → we fetch their real answers and create a Lead, fully automatically, usually within seconds. See `easycloud_crm/meta_leads.py`.

Either way, the moment a new Lead is created, `shruti@easycloud.in` gets an email about it (see `fixtures/notification.json`).

---

## Codebase Map

Frappe apps have a somewhat unusual folder shape — the app folder contains ANOTHER folder with the exact same name inside it (that inner one is the actual Python package). It looks like this:

```
easycloud_crm/                          <- the git repo root
├── README.md                           <- you are here
├── hooks.py ... wait, no               <- (see below, hooks.py is one level deeper)
└── easycloud_crm/                      <- the actual Python package (note: same name again)
    ├── hooks.py                        <- START HERE. The app's manifest -- see below.
    ├── api.py                          <- public HTTP endpoints (voice note upload, Meta webhook)
    ├── lead.py                         <- custom logic bolted onto the standard Lead doctype
    ├── meta_leads.py                   <- turns a Meta Ads submission into a real Lead
    ├── dashboard.py                    <- what shows in a Lead's "Connections" sidebar
    ├── utils.py                        <- helper functions exposed to email templates
    ├── patches.txt                     <- list of one-time migration scripts (see patches/)
    │
    ├── public/js/                      <- JS that loads site-wide (see hooks.py's app_include_js)
    │   ├── voice_note.js                    the record/transcribe dialog, used by Deal + CRM Activity
    │   ├── crm_activities_panel.js          the activity feed widget, shared by Lead + Deal forms
    │   ├── crm_activity_list.js             icons on CRM Activity's list view
    │   ├── workspace_icons.js               icons on the workspace's number cards
    │   └── lead.js                          Lead's form controller (Lead is a standard doctype, so
    │                                        its controller can't live inside a doctype/ folder below)
    │
    ├── patches/                        <- one-time setup scripts, each run exactly once ever
    │   ├── create_lead_pipeline_kanban_board.py
    │   ├── create_deal_pipeline_kanban_board.py
    │   ├── set_lead_pipeline_kanban_colors.py
    │   ├── set_deal_pipeline_kanban_colors.py
    │   ├── grant_projects_manager_task_permission.py
    │   └── show_last_contacted_on_kanban_cards.py
    │
    ├── fixtures/                       <- data exported from the database, tracked in git (see
    │   ├── custom_field.json               hooks.py's `fixtures` list for what/why). This is how
    │   ├── property_setter.json             custom fields on standard doctypes, Notification email
    │   ├── notification.json                templates, Lead Sources, and Roles ship with the app
    │   ├── lead_source.json                 instead of only existing in one database.
    │   └── role.json
    │
    ├── test_lead_stage.py              <- tests for lead.py (top-level, same reason as lead.js above)
    ├── test_meta_leads.py              <- tests for meta_leads.py + api.py's webhook signature check
    │
    └── easycloud_crm/                  <- THIS app's OWN doctypes live one level deeper still
        ├── doctype/
        │   ├── deal/                       Deal: the sales pipeline record
        │   │   ├── deal.json                   field definitions (schema)
        │   │   ├── deal.py                     server-side logic (Won -> Customer, stage logging)
        │   │   ├── deal.js                     client-side UI (progress bar, timeline, activity panel)
        │   │   └── test_deal.py
        │   ├── crm_activity/                CRM Activity: one logged Call/Meeting/Email/Note/Voice Note
        │   │   ├── crm_activity.json
        │   │   ├── crm_activity.py             validation, title computation, Whisper transcription
        │   │   ├── crm_activity.js
        │   │   └── test_crm_activity.py
        │   ├── deal_stage_log/              Deal Stage Log: append-only history of every Deal's stages
        │   └── deal_product/                Deal Product: child-table row for Deal's Products picker
        │
        ├── report/                     <- Report Builder reports (Lead Report, Deal Report,
        │                                   Retarget Marketing List)
        ├── dashboard_chart/             <- the 4 charts on the workspace (Leads by Source, etc.)
        ├── number_card/                 <- the 8 stat tiles on the workspace (Total Leads, etc.)
        └── workspace/easycloud_crm/     <- the "EasyCloud CRM" home screen layout itself
```

**The one-sentence version of the folder-depth rule:** if a file is *about* a doctype THIS app owns (Deal, CRM Activity, Deal Stage Log, Deal Product), it lives inside `easycloud_crm/easycloud_crm/doctype/<name>/`. Everything else (app-wide config, integrations, code that touches a doctype we DON'T own like Lead) lives one level up, directly inside `easycloud_crm/easycloud_crm/`.

### Where to start reading

1. **`easycloud_crm/hooks.py`** — the app's manifest. Every single way this app plugs into Frappe is listed there, with a comment explaining each one. Genuinely the best starting point.
2. **`easycloud_crm/lead.py`** and **`doctype/deal/deal.py`** — the two files that implement the actual pipeline logic described in the diagram above.
3. From there, hooks.py's comments point you to whichever specific file handles whatever you're curious about next.

---

## The DocTypes (data model)

### New doctypes this app owns

| DocType | What it is | Key fields | Defined in |
|---|---|---|---|
| **Deal** | One sales opportunity, from Qualified through Won/Lost | `stage`, `amount`, `lost_reason`, `retarget_status`, `lead` (link back), `customer` (set once Won) | `doctype/deal/` |
| **CRM Activity** | One logged interaction (Call/Meeting/Email/WhatsApp/Note/Voice Note) | `activity_type`, `date`, `notes`, one of `lead`/`deal`/`customer`/`contact`, `activity_title` (computed) | `doctype/crm_activity/` |
| **Deal Stage Log** | Append-only history row, one per real stage transition | `deal`, `stage`, `changed_on`, `changed_by` | `doctype/deal_stage_log/` |
| **Deal Product** | Child-table row behind Deal's "Products" multi-select | `item` | `doctype/deal_product/` |

### Standard doctypes we extend (never fork — see "Custom Field" in hooks.py)

| DocType | New fields we add | Why |
|---|---|---|
| **Lead** | `stage` (New/Contacted/Qualified/Do Not Contact), `do_not_contact_reason`, `stage_changed_on`, `meta_leadgen_id`, `current_erp`, `source_received_date`, `source_detail`, `custom_crm_activities_html` | Our own pipeline (see `lead.py`) and Meta Ads integration (see `meta_leads.py`) |
| **Task** | `custom_lead`, `custom_deal` | Lets a Task point back to the Lead/Deal it's about (manual linking — no automation creates Tasks) |

### The Lead pipeline (`easycloud_crm/lead.py`)

`New → Contacted → Qualified → (Deal auto-created here) → ... → Do Not Contact`

- Marking a Lead "Do Not Contact" without picking a reason is blocked.
- The moment (and *only* the moment) a Lead's stage becomes "Qualified", a Deal is auto-created for it — unless one already exists and isn't Won/Lost yet, so re-qualifying doesn't spam duplicates, but a genuinely NEW round of business with a past customer correctly gets its own new Deal.

### The Deal pipeline (`doctype/deal/deal.py`)

`Qualified → Proposal Sent → Demo Given → Negotiation → Won`, with `Cold` / `Lost` / `Not worth our time` / `Too Large` as exit points off that main line at any stage.

- Marking a Deal "Lost" without picking a Lost Reason is blocked.
- The moment a Deal's stage becomes "Won", a Customer record is auto-created (or reused, if one with that company name already exists) — and nothing else. *(An earlier version of this app also auto-created a Project and 5 starter Tasks at this point; that was deliberately removed — see `test_deal.py`'s `test_won_creates_customer_only`, whose name and assertions exist specifically to keep that removed behaviour from silently coming back.)*
- Every real stage change writes one row to Deal Stage Log — this is what powers the clickable progress bar and the Stage Timeline tab on the Deal form (`deal.js`).

### The "Lost" path and retargeting

Marking a Deal Lost requires a reason (Price / Competitor / Budget / No Response / Too Big for Us / Too Small for Us / Not a Fit / Cold), and then a genuinely separate, deliberate human choice: is this contact worth advertising to again later (`Eligible` / `Not Eligible`)? The code never guesses this — someone who picked a competitor is fine to re-target; someone who was rude or asked not to be contacted isn't, and no automated rule can tell those two cases apart.

Everyone marked `Eligible` shows up on the **Retarget Marketing List** report (Lost + Eligible Deals, with clean Company/Email/Phone columns fetched straight from the linked Lead). Marketing exports that as a CSV and uploads it to whichever ad platform's own "Custom Audience" tool — actually uploading it is a separate, manual step outside this app. *(Sending someone's contact info to an ad platform has real privacy-law implications — GDPR, CAN-SPAM, each platform's own rules — that's a legal/marketing-ops question, not something this app decides for you.)*

---

## Integrations

### Meta (Facebook/Instagram) Lead Ads — `api.py` + `meta_leads.py`

A live webhook at `/api/method/easycloud_crm.api.meta_lead_webhook`. Meta calls it the instant someone submits a Lead Ad form; we verify the request is genuinely from Meta (HMAC signature check), then fetch the real answers from Meta's Graph API and create a Lead — mapping Meta's free-text bucket answers (industry, employee count, revenue range) onto the SAME standard Lead fields a human would fill in by hand, not separate custom fields, so nothing downstream needs to know or care whether a Lead came from Meta or a person typing it in. See `meta_leads.py`'s header comment for the full field-by-field mapping logic and its reasoning.

### Voice notes — `api.py`, `public/js/voice_note.js`, `doctype/crm_activity/crm_activity.py`

Deal and CRM Activity forms both offer a "🎤 Voice Note" button. Recording happens entirely in the browser (no plugin, no app); on Stop, the audio uploads to our backend, which saves it and sends it to a **self-hosted Whisper** speech-to-text container (`http://whisper:8500`, a Docker Compose service — see the deployment's `docker-compose.yml`) for transcription. If transcription is triggered from a saved CRM Activity's own `audio_file` field changing (rather than the live dialog), it runs as a background job instead — see `crm_activity.py`'s `transcribe_voice_note()`.

### Email notifications — `fixtures/notification.json`, `utils.py`

Two automated emails, both built as plain Frappe **Notification** records (Desk → Settings → Notification — editable there without touching code):
- **Assignment Email Notification** — fires on ANY "Assign To" action, any doctype, emailing whoever it was assigned to. When the thing assigned is a CRM Activity (whose own ID looks like meaningless `CRM-ACT-2026-00236`), the email shows the linked Lead/Deal's name instead — that lookup is `utils.py`'s `notification_reference_label()`, exposed to the email template via `hooks.py`'s `jinja` hook.
- **New Lead Email to Shruti** — fires on every new Lead, any source.

Both require a working outgoing Email Account configured on the site (Desk → Settings → Email Account) — without one, they sit silently inactive rather than erroring.

---

## Running & Deploying

This app is designed to run inside the standard [frappe_docker](https://github.com/frappe/frappe_docker) stack, with this app's source code **bind-mounted** into the containers (for fast iteration) rather than baked into a custom image. That trade-off has real, documented consequences worth knowing before you touch the deployment:

- **A Python/hooks.py change needs the `backend` (and usually `scheduler`/`queue-short`/`queue-long`) container restarted** to be picked up — Python only re-reads a module the first time it's imported per process.
- **A schema change (a doctype .json field, a fixture) needs `bench migrate`** run against the site.
- **Recreating (not just restarting) the `backend` container** — via `docker compose up -d` rather than `restart` — wipes this app's `pip install -e` registration from that container's throwaway filesystem layer, taking the whole site down with `ModuleNotFoundError: No module named 'easycloud_crm'` until it's manually reinstalled. If you ever hit that error right after a `docker compose up -d`, that's almost certainly why.
- **`frontend`'s nginx serves `/assets/*` (all JS/CSS) from its own local disk**, separate from `backend`'s — a shared Docker volume keeps the two in sync, but if you ever see a JS/CSS file 404 on the live site despite existing on `backend`, that sync is the first thing to check.

None of the above needs to block day-to-day feature work — they're the kind of thing that bites you once, briefly, during a deploy/infra change, not during normal development.

### Running the tests

```bash
bench --site <your-site> set-config allow_tests true
bench --site <your-site> run-tests --app easycloud_crm
bench --site <your-site> set-config allow_tests false
```

Every test extends `FrappeTestCase`, which wraps each test in a database transaction that's automatically rolled back when the test finishes — nothing a test creates (Leads, Deals, Customers, ...) is ever left behind in the real database, even though the test code calls real `.insert()`/`.save()`. You'll notice every test record is named with a `ZZTEST` prefix — that's purely a human convenience (instantly recognisable as test data if you're ever poking around mid-run), not part of the actual cleanup mechanism.

To run just one file's tests:
```bash
bench --site <your-site> run-tests --module easycloud_crm.easycloud_crm.doctype.deal.test_deal
```

### Installing this app fresh somewhere else

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO
bench install-app easycloud_crm
```

### Keeping fixtures in sync

If you change a Custom Field, Property Setter, Notification, Lead Source, or Role through the UI, that change only lives in the current site's database until you export it:

```bash
bench --site <your-site> export-fixtures --app easycloud_crm
```

...then commit the updated files under `fixtures/`. Forgetting this step is the most common way a real change quietly fails to travel to any other environment.

---

### Contributing

This app uses `pre-commit` for code formatting and linting:

```bash
cd apps/easycloud_crm
pre-commit install
```

Configured tools: `ruff`, `eslint`, `prettier`, `pyupgrade`.

### License

mit
