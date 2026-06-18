---
name: harborcrm-front-of-funnel
description: >-
  Solve HarborCRM front-of-funnel CRM/marketing tasks against the shared read-only HarborCRM
  JSON API. Use this whenever a task references HarborCRM, an event_id / show_id / import batch_id,
  sponsor reconciliation, badge scans, trade-show exhibitor prospecting/qualification, raw
  contact-import hygiene/dedup/suppression, sponsor or lead follow-up planning, or CRM
  create/update/no-action decisions — even if the task only says "reconcile the event", "prepare
  the qualified lead list", "clean the import batch", or "prospecting summary". The output is
  always a single strict JSON object matching the provided answer_template; this skill explains
  the business rules (source precedence, sponsor status enums, normalization, exclusion logic,
  follow-up due dates, rollups) that determine the correct values.
---

# HarborCRM Front-of-Funnel Solver

HarborCRM is a shared marketing/CRM workspace exposed as a **read-only JSON API**. Tasks give you a
scope key (`event_id`, `show_id`, or import `batch_id`) and an `answer_template` that defines the
exact output shape. You fetch the relevant records, apply HarborCRM's business rules, and return
**one JSON object** that conforms to the template — no prose, no extra fields.

There are five recurring task families. Identify which one you're in from the scope key and the
required top-level keys, then follow the matching SOP below.

| Family | Trigger | Core endpoints |
|---|---|---|
| A. Event sponsor + lead reconciliation | `event_id`; keys like `sponsor_statuses`, `qualified_lead_accounts`/`badge_decisions`, `follow_up`/`sponsor_followup` | events, orders, sponsor_packages, finance/invoices, badges, crm/accounts, crm/contacts, crm/opportunities, crm/campaign_members |
| B. Trade-show prospecting / qualification | `show_id`; keys like `qualified_exhibitors`/`ranked_leads`, `excluded_*`, platform/priority counts | tradeshows, tradeshows/{id}/exhibitors, tradeshows/{id}/meeting_interest, crm/accounts, policies |
| C. Raw contact-import hygiene | `batch_id`; keys like `clean_contacts`, `duplicate_summary`, `removal_summary`, `import_action_totals` | import_batches, import_batches/{id}/raw_contacts, import_batches/{id}/suppression, crm/accounts, crm/contacts, policies |

(Families A covers both the "audit/handoff" and "post-event reconciliation" variants — they share
all the same rules but differ in output shape.)

## Golden rules (apply everywhere)

1. **The answer_template is law.** Use only the declared top-level keys, item keys, and enum
   values. Never invent fields. Respect every stated sort order exactly. Currency is **integer
   USD** unless told otherwise. Counts are integers.
2. **Read `GET /api/policies` first.** It declares the controlled enums actually in force:
   `sponsor_handoff.status_enums` = `paid_deferred | open_invoice | proposal_only | not_sponsor`;
   `prospecting.platform_enums` = `AUV | ROV | Underwater Camera`. The template may expose a subset.
3. **Match accounts by domain, not by name.** Exhibitors carry `crm_account_id` directly. For
   badges/import rows, derive the email domain and match it to a CRM account's `domain` field.
   Company-name strings vary ("HelioWare Manufacturing" vs "HelioWare Mfg.") and must not be the
   join key.
4. **Normalization is literal, not smart** (see below). Do not add or remove country codes.
5. **Derive every number; never hardcode.** Follow-up dates, opportunity amounts, and tier money
   all come from the event/policy/template records for *that* scope. The same person can have a
   different normalized phone in two tasks because the *source string* differs.

## Contact normalization rules

- **Email**: trim surrounding whitespace, lowercase the whole string. `" Dana.Ruiz@HelioWare.example "`
  → `dana.ruiz@helioware.example`. If no usable email, use empty string `""` (never null) where the
  schema says "empty string allowed".
- **Phone**: **strip every non-digit character** (drop `+`, spaces, `(`, `)`, `.`, `-`). That is the
  whole rule. Do NOT normalize to a canonical length and do NOT force a leading `1`.
  - `"415-555-0188"` → `4155550188` (stays 10 digits)
  - `"1.206.555.0177"` → `12065550177` (the source's leading 1 is kept)
  - `"+1 (512) 555-0121"` → `15125550121` (the `+` is dropped, the `1` stays)
  - `"+358 40 555 0190"` → `358405550190` (international code kept verbatim)
  - empty/whitespace phone → `""`.

## Sponsor status classification (Family A)

For each account that has a sponsor **order / sponsor_package** for the event, classify from the
order's `order_status` joined with the matching finance invoice (`/api/finance/invoices?event_id=...`,
keyed by `account_id`):

- **`paid_deferred`** — order confirmed AND invoice `status == "paid_deferred"` (or fully paid:
  `paid_amount == amount`). `open_balance = 0`.
- **`open_invoice`** — order confirmed AND an invoice exists that is not fully paid
  (`status == "open"`, `paid_amount < amount`). Report `paid_amount` and
  `open_balance = amount - paid_amount` separately. The **status revenue uses the full package
  `amount`**, while `open_invoice_balance` rolls up the unpaid remainder only.
- **`proposal_only`** — order `order_status == "proposal_sent"`, no/empty invoice. `invoice_id`
  null, `paid_amount` 0, `open_balance` 0.
- **`not_sponsor`** — only when the schema includes it: an account with no qualifying sponsor order.
- **Canceled / inactive sponsor orders** (`order_status == "canceled"`) are **excluded** from
  sponsor statuses entirely. If that account also appears as a disqualified CRM account or a badge,
  it falls through to the lead/exclusion logic (typically `existing_disqualified`).

**Sponsor revenue rollups**: sum package `amount` per status into `paid_deferred`/`open_invoice`/
`proposal_only`; `open_invoice_balance` = sum of open balances. **`unpaid_sponsor_total`** (the
reconciliation variant) = sum of amounts for sponsors that are not fully paid, i.e. `open_invoice` +
`proposal_only` accounts (paid_deferred is excluded because it's collected).

## Lead qualification & exclusion logic (Family A)

Candidate leads come from event **badges** (and sometimes from CRM accounts tied to the event). A
badge becomes a **qualified non-sponsor lead** only if ALL of these hold:

- Badge is a **business** badge. Exclude `badge_type in {student, press}` and any non-business badge
  → reason `non_business_badge`.
- The attendee's company is **not a sponsor**. Anyone whose company has a sponsor order (any active
  status, including `proposal_only`) is a `sponsor_attendee`, regardless of their badge_type. Sponsor
  ticket contacts (from order `ticket_contacts`) are also `sponsor_attendee` even if they have no
  badge.
- The matched CRM account is **not disqualified** (`status == "disqualified"` or a non-null
  `disqualified_reason`) → reason `existing_disqualified`. This also catches accounts whose only
  sponsor order was canceled.
- (Import/reconciliation variants) the contact is present → otherwise `missing_contact`.

Exclusion reason enum (Family A): `sponsor_attendee | non_business_badge | existing_disqualified |
missing_contact`. The template's enum is authoritative; use only the values it lists.

**Opportunity amount for qualified leads** = the event's `lead_opportunity_amount` (a flat per-event
figure on the event record), applied to *each* qualified non-sponsor account. `lead_pipeline_total`
/ `open_opportunity_total` = that amount × count of qualified non-sponsor accounts;
`open_opportunity_count` = that count.

### CRM action decisions (Family A)

Decide per qualified lead / per badge by checking existing CRM state (match account by email domain;
match contact by account + name/email):

- Account exists in CRM → `update_existing` (account action) or include the `existing_account_id`.
  Account absent → `create_account`.
- Contact exists for that account → reuse it; contact absent → `create_contact`.
- Campaign member exists for that account+contact+event (`/api/crm/campaign_members?event_id=...`) →
  `update`/`no_action`; absent → `add_campaign_member` / `create`.

In the badge-reconciliation variant the per-badge `crm_action` is a composite enum:
`create_account_contact_campaign_member` (nothing exists yet), `create_contact_campaign_member`
(account exists, contact + member don't — typical for a sponsor attendee with a new face),
`add_campaign_member`, `update_campaign_member`, `no_action` (sponsor attendee already a campaign
member), `no_import` (excluded non-business badge). Campaign-member `target_status` mirrors the
sponsor/attendee relationship: `attended_sponsor`, `registered_sponsor`, `attended`, `excluded`.

**`badge_only_contacts`** (when requested) = the set of badges for which a **new CRM contact must be
created** (qualified leads + sponsor attendees lacking an existing contact). Contacts that already
exist in CRM are not listed. Emit normalized email/phone per the rules above.

**crm_action_counts** are simple tallies of the above decisions across the handoff. `no_action` and
`no_import` records do not add to create/update counts.

## Follow-up due dates & task counts (Family A)

Dates are **derived from the event record**, never guessed:

- `lead_followup_due_date` = event `end_date` + `followup_days_after_end` days.
- `sponsor_followup_due_date` = event `end_date` + `sponsor_followup_days_after_end` days.

Example: NeuralOps `end_date 2026-09-16`, `followup_days_after_end 7` → `2026-09-23`;
`sponsor_followup_days_after_end 3` → `2026-09-19`. Format `YYYY-MM-DD`.

- `lead_task_count` = number of qualified leads getting a follow-up (one task each).
- `sponsor_finance_task_count` / `sponsor_finance_accounts` = the sponsors needing finance follow-up
  = the unpaid sponsors (`open_invoice` + `proposal_only`), sorted by `account_name`. paid_deferred
  sponsors need no finance follow-up.

## Trade-show prospecting & qualification (Family B)

Goal: from `/api/tradeshows/{show_id}/exhibitors` decide who builds **target underwater platforms**
(the campaign target, e.g. dissolved-oxygen-sensor-capable robotics). Judge from the exhibitor
`description`:

- **Qualified** = the company **manufactures / builds / designs / OEM-builds** a platform in the
  enum set: AUVs, ROVs, or underwater cameras. Phrases like "Builds compact AUVs and inspection-class
  ROVs", "Designs rugged underwater camera modules", "Manufactures pen-cleaning ROVs with camera
  arrays", "OEM underwater camera manufacturer" all qualify. A company can map to multiple platforms.
- **`platforms`** = the subset of `[AUV, ROV, Underwater Camera]` the description supports, always
  emitted **in that enum order**. (A camera maker that merely "embeds third-party probes" still
  qualifies as Underwater Camera — it builds the camera platform; the probe is just integrated.)
- **Excluded near-misses** (adjacent but not platform makers), with controlled reasons:
  - distributor / reseller / sales agent, "does not manufacture" → `distributor_only`
    (relationship `distributor`)
  - consulting / operates rented gear / services → `service_only` (relationship `service_provider`)
  - sensor/probe-only vendor (makes the sensor, not the platform) → `sensor_vendor_only` /
    `sensor_only` (relationship `sensor_vendor`) — match whichever spelling the template lists
  - research lab / academic → `research_only` (relationship `research`)
  - `not_target_market` for in-scope-but-off-target makers when the template offers it.
  Excluded exhibitors carry `crm_action = no_import`.

**Priority tier & opportunity sizing**: join exhibitors to `/api/tradeshows/{show_id}/meeting_interest`
by `company_name` to get `interest_score` and `requested_demo`. Standard rule (confirm against the
prompt, which may restate it):

- Tier **A** = `requested_demo == true` AND `interest_score >= 90`.
- Tier **B** = `requested_demo == true` AND `interest_score >= 80` (and not A).
- Tier **C** = everyone else qualified.
- Opportunity money per tier is given **in the prompt** (e.g. A=120000, B=90000, C=50000). Use those
  figures; do not assume. `total_estimated_opportunity_usd` = sum across qualified leads.

**CRM overlap / action**: exhibitor `crm_account_id` present → `update_existing` and count it in
`existing_crm_overlap_*`; absent (null) → `create_account`.

**Ranking** (when `ranked_leads` with `rank` is requested) follows the prompt's tiebreak chain,
typically: `requested_demo` desc → `interest_score` desc → broader platform coverage (more platforms
first) → `company_name` asc. Assign `rank` as 1-based contiguous integers.

**Aggregate counts**: `platform_counts`/`platform_coverage_counts` count how many qualified leads
cover each platform (a multi-platform lead increments multiple buckets). `priority_counts` tally
A/B/C. Always include every required key even when the value is 0.

## Raw contact-import hygiene (Family C)

Process `/api/import_batches/{batch_id}/raw_contacts` into an import-ready set. Apply the steps in
this order (order matters for which row is "removed" vs "winner"):

1. **Normalize** every row's email and phone (rules above).
2. **Suppression** — `/api/import_batches/{batch_id}/suppression` lists opted-out emails/phones. Any
   row whose normalized email OR phone matches a suppression entry → removed with reason
   `suppressed`, `crm_action = suppress`. (A row can be suppressed even if its company/name look
   fine — match on the contact identity, not the company. Note suppression can hit a row whose
   company was renamed, e.g. a personal email reused under a different company.)
3. **Missing contact** — a row with no usable contact identity (empty email AND empty phone, or
   otherwise uncontactable) → removed with reason `missing_contact`, `crm_action = no_import`.
4. **Deduplicate** survivors by a stable key (normalized **email** when present, else normalized
   phone). Within a duplicate group pick ONE **winner**; the rest are removed with reason
   `duplicate`, `crm_action = no_import`.
   - Winner selection: prefer the **most recent `captured_at`**; break ties by **source
     precedence** (trusted enrichment sources beat raw form fills — e.g. `partner_upload` /
     `badge_scan` over `webinar_form`). Do NOT tie-break by row_id ascending.
   - The winning row supplies the surviving `company_name`, `email`, `phone`, `source_name`,
     `captured_at`, and `clean_contact_id`/`source_row_id` (= winner's row_id).
   - `duplicate_keys` entries: `{key: "email:<addr>", winner_row_id, removed_row_ids:[...]}`.
5. **CRM action for survivors**: match the winner's email domain to a CRM account `domain`. Account
   found → `update_existing` with `existing_account_id` (set `existing_contact_id` only if a CRM
   contact for that account+person already exists, else null). No account → `create_account`.

**Counts**: `import_action_totals` tallies every original row across the four `crm_action` buckets
(`create_account + update_existing + no_import + suppress` = total raw rows). `removal_summary`:
`unusable_removed_count` = missing_contact rows; `suppressed_removed_count` = suppressed rows;
`duplicate_removed_count` = duplicates removed. `removed_rows` lists each removed row with its reason
(`duplicate | missing_contact | suppressed`). `campaign_member_import_count` = number of surviving
clean contacts (they all become members of the batch campaign). `campaign_code` comes from the batch
record.

## How to call the API

Base URL is in `environment_access.md` (e.g. `http://127.0.0.1:8080`; some prompts cite a different
port — use the runner-supplied base). All responses are JSON. Use `curl -s`. Start with:

```
curl -s $BASE/health            # sanity: record counts
curl -s $BASE/api/policies      # controlled enums in force
```

Then, by family:

- **A (event):** `GET /api/events/{event_id}` (dates, lead_opportunity_amount, followup days,
  campaign_code) · `.../orders` & `.../sponsor_packages` (sponsor orders + ticket_contacts) ·
  `.../badges` · `GET /api/finance/invoices?event_id={id}` · `GET /api/crm/accounts` ·
  `GET /api/crm/contacts` · `GET /api/crm/opportunities?event_id={id}` ·
  `GET /api/crm/campaign_members?event_id={id}`.
- **B (trade show):** `GET /api/tradeshows` · `GET /api/tradeshows/{show_id}/exhibitors` ·
  `GET /api/tradeshows/{show_id}/meeting_interest` · `GET /api/crm/accounts`.
- **C (import):** `GET /api/import_batches` · `GET /api/import_batches/{batch_id}/raw_contacts` ·
  `GET /api/import_batches/{batch_id}/suppression` · `GET /api/crm/accounts` ·
  `GET /api/crm/contacts`.

The API exposes only shared domain records; there are no task-answer endpoints. Do not look for
server source.

## Common output conventions

- Sort lists exactly as the template states (commonly `account_name` / `company_name` ascending,
  `badge_id` / `clean_contact_id` / `row_id` ascending, `rank` ascending). When a secondary sort is
  named (e.g. then `contact_name`), apply it.
- Use `""` (empty string) where the schema says empty allowed; use `null` only where it explicitly
  allows null (`existing_account_id`, `crm_account_id`, etc.).
- Include every required object key on every item, and every required key in count objects (emit
  `0`, don't omit).
- Return strict JSON only — no markdown, no comments, no trailing prose.

## Common misjudgments to avoid

- Treating `proposal_only` (proposal_sent, no invoice) as an open invoice, or counting paid_deferred
  in the unpaid follow-up list.
- Letting a **canceled** sponsor order create a sponsor status row (it should drop out / route to
  exclusion).
- Classifying a sponsor's attendee as a qualified lead because their badge_type is "attendee" — if
  the company is a sponsor, the person is a sponsor_attendee.
- Forgetting that sponsor `ticket_contacts` without badges are still sponsor_attendees to exclude.
- Joining accounts by company name instead of email domain (names are intentionally noisy).
- Over-normalizing phones (inserting/removing a leading 1) — extract digits literally.
- Hardcoding follow-up dates or tier amounts instead of computing them from the event record /
  prompt.
- In imports: dropping a suppressed row into `no_import` instead of the distinct `suppress` action;
  or tie-breaking duplicates by row_id instead of recency + source precedence.
- Qualifying distributors/resellers, pure sensor/probe vendors, service/consulting firms, or
  research labs as platform makers in prospecting tasks.
- Emitting platforms out of enum order, or omitting zero-valued count keys.
