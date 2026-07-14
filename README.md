### Easycloud CRM

Manage Easycloud CRM

---

## What is this thing? (Explained like you're 5)

Imagine you have a lemonade stand.

Every day, people walk by. Some of them stop and say "maybe I'll buy lemonade later." Some of them buy it right away. Some of them say "no thanks" and walk off.

If you had a magic notebook, you could write down:
- Who said "maybe" (we call this a **Lead**)
- What you're trying to sell them, and how close you are to a "yes" (we call this a **Deal**)
- Whether they said **yes** (a **Won** deal) or **no** (a **Lost** deal)

That magic notebook is what this app is. It's called a **CRM**, which just means "a notebook for keeping track of people you're trying to sell things to." We didn't build the whole notebook from scratch — we started from a big, already-built notebook called **ERPNext** (it already knows how to keep track of Leads, Contacts, Customers, Projects, and To-Do lists), and we added a few new pages to it just for our sales notebook needs.

---

## The Big Picture

Here's the whole journey a person goes through, from "stranger" to "happy customer" (or "maybe later"):

```
Someone shows interest
        |
        v
      Lead                    <- "Hi, I might be interested"
        |
        v
      Deal                    <- "Let's talk about what you'd buy"
        |
        v
   drag the card across the board:
   New -> Contacted -> Qualified -> Proposal -> Negotiation
        |
        +-------------------+
        v                   v
      WON                 LOST
   (they said yes!)     (they said no)
        |                   |
        v                   v
  Customer is made      We write down WHY
  Project is made       We decide: is this
  5 Tasks are made      person worth trying
  automatically!        to reach again later
                         with an ad?
                              |
                              v
                     If yes -> they go on
                     Marketing's "try again
                     later" list
```

Both paths matter. A "yes" becomes real work to do. A "no" isn't necessarily the end of the story — some "no, not right now" people are worth a friendly reminder ad a few months later.

---

## Part 1: When someone says YES (the "Won" path)

1. Someone becomes a **Lead** (their name goes in the notebook, along with where we found them — website, Instagram, a friend's referral, etc).
2. We write down a **Deal** for them — what they might buy, and how much it might cost.
3. We drag their card across a board with columns like `New`, `Contacted`, `Qualified`, `Proposal`, `Negotiation`, all the way to `Won`.
4. The moment we do that, the app does something neat **all by itself**:
   - It creates a **Customer** record for them (so accounting/everyone else now knows they're a real customer, not just a maybe).
   - It creates a **Project** for the work.
   - It creates **5 starter to-do Tasks** for that project: Requirement Gathering, Implementation, Testing, Go Live, Training.
5. It only does this ONCE. If someone accidentally saves the same Won deal again, it does NOT make a second Customer or a second Project or five more Tasks. It's smart enough to notice "oh, I already did this."

---

## Part 2: When someone says NO (the "Lost" path)

Losing a deal isn't just "delete and forget." Here's what happens instead:

1. We drag the Deal card to `Lost`.
2. The app **won't let us save it** until we say *why* it was lost — was it the price? A competitor? Budget? They just went quiet (No Response)? This is a rule the app enforces, not a suggestion.
3. Once we've written the reason, we get to make one more choice: **is this person worth trying to reach again later with an ad?** (`Eligible` or `Not Eligible`). This is a person's choice, not something the computer decides automatically — because someone who picked a competitor is a totally fine person to advertise to again later, but someone who was rude or asked never to be contacted again is not, and the app can't tell those two apart on its own.
4. If we say "Eligible," that Deal shows up on a special report for the Marketing team called the **Retarget Marketing List** — a clean table of just Company / Email / Phone (plus why they said no, and when), for exactly the people worth showing an ad to again.
5. Marketing clicks the built-in **Export** button and gets a CSV file (a simple spreadsheet file). They then take that file to Facebook Ads, Google Ads, Instagram, or LinkedIn and upload it there directly (as their own "Custom Audience" tool). This app's job stops at "give marketing a clean list" — actually uploading it to each ad platform is a separate job outside this app, done by whoever runs those ad accounts. (Also: sending someone's contact info to an ad platform has real privacy rules attached to it — GDPR, CAN-SPAM, and each platform's own rules — so that's a legal/marketing-ops question to check on, not something this app decides for you.)

---

## What's Actually Inside This App (for the grown-ups)

Everything below lives inside `easycloud_crm/easycloud_crm/`, and was built on top of stock ERPNext v15 — nothing here recreates Lead, Contact, Customer, Task, Project, or User; it only adds the thin layer needed to connect them into a sales pipeline.

### New DocTypes (new kinds of records)

| DocType | What it's for |
|---|---|
| **Deal** | The pipeline record itself. Has a `stage` (New/Contacted/Qualified/Proposal/Negotiation/Won/Lost), an `amount`, a `probability`, links back to the `lead` and (once Won) the `customer` and `project`. |
| **CRM Activity** | A log of a call, meeting, email, or note against a Lead or a Deal — so there's a paper trail of contact history. |

### New fields on existing DocTypes

| DocType | New field(s) | Why |
|---|---|---|
| **Task** | `custom_lead`, `custom_deal` | So a Task created by the automation (or by hand) can point back to the Lead/Deal it came from. |
| **Deal** | `lost_reason` (Select: Price / Competitor / Budget / No Response) | Required before a Deal can be saved as Lost. |
| **Deal** | `retarget_status` (Select: Eligible / Not Eligible) | A deliberate human choice — never auto-set — about whether this contact is worth advertising to again later. |
| **Deal** | `company_name`, `contact_email`, `contact_phone` | Read-only, auto-filled from the linked Lead's `company_name` / `email_id` / `mobile_no`, so the retarget report has clean contact data without retyping anything. |

### Automation (`doctype/deal/deal.py`)

- **`validate()`** — blocks saving a Deal as `Lost` with no `lost_reason` set. Runs *before* save.
- **`on_update()`** — when a Deal's `stage` changes to `Won`, automatically creates a Customer, a Project, and 5 starter Tasks (Requirement Gathering, Implementation, Testing, Go Live, Training). Runs *after* save, and is guarded so it only ever fires once per Deal, no matter how many times you save it afterward.

### Other pieces

- **Kanban Board** ("Deal Pipeline") — a drag-and-drop board for Deals, one column per `stage`.
- **Workspace** ("EasyCloud CRM") — one home screen with shortcuts to Lead, Deal, CRM Activity, Task, Project, the Kanban board, and the retarget report; plus number cards (Total Leads, Open Deals, Won Deals, Revenue, Projects) and charts (Leads by Source, Deals by Stage, Won Deals by Month).
- **Lead dashboard** — opening any Lead now also shows how many Deals/Activities are linked to it, right in the existing "Connections" panel.
- **Reports** — Lead Report, Deal Report, Project Handover Report, and the Retarget Marketing List (Lost + Eligible deals only), all built as simple Report Builder reports so the native **Export** button works with zero extra code.
- **Lead Source** master data — Website, Instagram, Referral, LinkedIn, WhatsApp, Email.
- **Roles** — `Sales User` and `Sales Manager` (both already existed in ERPNext, reused rather than recreated) get edit access to Deal/CRM Activity; `Projects Manager` (also already existed) gets Task access it didn't have before; a new `Marketing User` role gets read-only access, just enough to pull the retarget list without full sales permissions.

---

## How to Run This

This app runs inside Docker, alongside the rest of the ERPNext stack, using the wrapper script at the top of the project:

```bash
./dc.sh ps                                    # see if everything is running
./dc.sh restart backend scheduler queue-short queue-long frontend websocket
                                               # restart after a Python change
./dc.sh exec backend bench --site easycloudcrm.synorion.com migrate
                                               # apply schema/field changes
```

If you change a Python file (a controller, a hook), the backend needs a restart to notice. If you add or change a *field*, run `bench migrate` too. If you restart the backend, restart `frontend` and `websocket` as well — otherwise the site can show a "502 Bad Gateway" error because the web server is still trying to talk to the old, no-longer-there version of the backend.

### Installing this app fresh somewhere else

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app easycloud_crm
```

---

## How We Know It Works

Both pipeline flows were tested end-to-end against the real running site, not just imagined:

**The "Won" story:**
1. Make a Lead, source = Website.
2. Log a Call against it.
3. Make a Deal from that Lead.
4. Drag the Deal across the Kanban board through a few stages.
5. Drag it to Won.
6. Confirm: exactly one new Customer, one new Project, five new Tasks — all pointing back to the Deal.
7. Save the Won Deal again — confirm nothing gets created a second time.

**The "Lost" story:**
1. Make a Lead for an obviously fake test company, source = Website.
2. Make a Deal, move it to Proposal, then Negotiation.
3. Try moving it to Lost with no reason — confirm the app blocks it.
4. Set Lost Reason = Budget, Retarget Status = Eligible, save — confirm it saves, and Company/Email/Phone fill in automatically.
5. Open the Retarget Marketing List report — confirm the test Deal shows up with the right columns.
6. Export the report — confirm the CSV has clean Company/Email/Phone columns.
7. On a *different* test Deal, run through the Won story again — confirm it still behaves exactly as before.

Both checklists passed, on the real site, with obviously-fake test data (prefixed `ZZTEST`/`ZZDEMO` so it's easy to find and clean up later).

### Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/easycloud_crm
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

### License

mit
