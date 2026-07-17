# HarborCRM CRM-Marketing Handoff, Prospecting & Import Skill

Self-contained conventions for solving HarborCRM task-group tasks against the shared
read-only API. Three task families share one dataset and one set of conventions:

1. **Event handoff / reconciliation** — post-event CRM handoff for a completed event
   (sponsor status reconciliation, badge→lead classification, opportunity totals,
   finance follow-up, due dates, CRM action counts).
2. **Trade-show prospecting** — qualify exhibitors at a trade show into a CRM-ready
   lead list (platform coverage, priority tiers, opportunity sizing, CRM
   create/update decisions, ranking, exclusions).
3. **Import cleaning** — prepare a raw contact batch for CRM import (normalize,
   de-duplicate, suppress, drop unusable, decide create/update, count campaign
   members).

## 0. Environment & API access

- Base URL (the ONLY allowed data source): `<remote-env-url>`
- Read-only GET endpoints only. Never POST/PUT/DELETE. Never call any judge/eval endpoint.
- Call with `curl -s <remote-env-url><endpoint>` and parse JSON (pipe to
  `python3 -m json.tool` or `jq`). The dataset is deterministic (seed 41001).

Public endpoints:

```
GET /health
GET /api/policies                                   # authoritative rule constants
GET /api/events
GET /api/events/{event_id}
GET /api/events/{event_id}/orders                   # sponsor orders
GET /api/events/{event_id}/badges                   # badge scans
GET /api/events/{event_id}/sponsor_packages         # same shape as orders
GET /api/finance/invoices?event_id={event_id}       # invoices for the event
GET /api/crm/accounts
GET /api/crm/contacts
GET /api/crm/opportunities
GET /api/crm/campaign_members?event_id={event_id}
GET /api/tradeshows
GET /api/tradeshows/{show_id}/exhibitors
GET /api/tradeshows/{show_id}/meeting_interest
GET /api/import_batches
GET /api/import_batches/{batch_id}/raw_contacts
GET /api/import_batches/{batch_id}/suppression      # global suppression list
```

## 1. Authoritative constants — read `/api/policies` first

`/api/policies` returns the controlled vocabularies. Always conform to these enums:

- `sponsor_handoff.status_enums`: `paid_deferred`, `open_invoice`, `proposal_only`, `not_sponsor`
- `prospecting.platform_enums` (and the required output order): `AUV`, `ROV`, `Underwater Camera`
- `prospecting.qualification_note`: an exhibitor qualifies only if it **builds or OEM-builds**
  target underwater platforms; an exhibitor that is merely *adjacent* (distributor,
  service/rental, sensor-only, research, software-only) does **not** qualify.

Values stated explicitly in a task prompt (e.g. tier→opportunity amounts, tier score
thresholds) take precedence over the defaults in section 5; if the prompt does not state
them, use the defaults documented there.

## 2. Cross-cutting conventions

### Value normalization
- **Email**: trim surrounding whitespace, lowercase. Empty string `""` when absent/blank.
- **Phone**: keep digits only (strip everything else). Do NOT add or strip a leading
  country code — `"415-555-0188"` → `"4155550188"`, `"+1 (206) 555-0150"` → `"12065550150"`.
  Empty string `""` when no digits present.
- **Currency**: integer USD. Never float.
- **Dates**: `YYYY-MM-DD`. Due dates are computed by calendar-day addition (see 2.3).

### CRM record matching
- **Existing account**: a lead/contact matches an existing CRM account when the normalized
  email **domain** equals a CRM account `domain`, or the company name matches a CRM account
  `name`. Use the matched `account_id`.
- **Existing contact**: match by normalized email against a CRM contact `email`; if no email
  match, fall back to same `account_id` + same `contact_name`. Use the matched `contact_id`.
- A CRM account with `status == "disqualified"` (non-null `disqualified_reason`) is an
  **existing_disqualified** exclusion — leads for these accounts are not imported/qualified.

### Due-date arithmetic (uses event constants from `/api/events/{event_id}`)
- `lead_followup_due_date` = `event.end_date` + `event.followup_days_after_end` (calendar days).
- `sponsor_followup_due_date` = `event.end_date` + `event.sponsor_followup_days_after_end`.
- Both rendered `YYYY-MM-DD`. These constants are per-event; never assume fixed offsets.

### Output discipline
- Return exactly ONE JSON object conforming to the provided `answer_template.json`.
- Do not add fields not in the template. Do not include prose outside the JSON.
- Enum values must exactly match the template's `allowed_values` (note family-specific
  spelling variants, e.g. `sensor_only` vs `sensor_vendor_only` — see section 5).
- Apply every template `ordering` rule. Common sort keys summarized in section 7.

## 3. Family A — Event handoff / reconciliation

Inputs: `/api/events/{id}`, `/orders` (or `/sponsor_packages`), `/badges`,
`/api/finance/invoices?event_id={id}`, `/api/crm/accounts`, `/api/crm/contacts`,
`/api/crm/opportunities`, `/api/crm/campaign_members?event_id={id}`, `/api/policies`.

### 3.1 Sponsor status reconciliation
Sponsor orders carry `order_status`. Treat order statuses as:
- **Active** = `confirmed` or `proposal_sent` → appears in `sponsor_statuses`.
- **Inactive** = `canceled` or `no_show` → **excluded** from `sponsor_statuses`; their
  ticket contacts become `inactive_sponsor_record` exclusions (section 3.2).

For each **active** sponsor order, aggregate that account's invoices for the event
(match on `account_id` + `event_id`). Compute:
- `package_amount` = the sponsor order `amount`.
- `paid_amount` = sum of `paid_amount` across the account's invoices for this event.
- `open_balance` = `package_amount` − `paid_amount`.
- Status decision:
  - `proposal_sent` with **no invoice** → `proposal_only`; `invoice_id = null`;
    `paid_amount = 0`; `open_balance = 0`.
  - Has invoice(s) and `open_balance > 0` → `open_invoice`; `invoice_id` = the open
    invoice's id (the one with unpaid balance).
  - Has invoice(s) and fully paid (`open_balance == 0`) → `paid_deferred`;
    `invoice_id` = the paid invoice's id.
  - (A sponsor may have multiple invoices, e.g. one paid-deferred + one open; the
    overall status is `open_invoice` whenever any balance remains.)

Revenue totals (integer USD):
- `paid_deferred` = Σ `package_amount` of `paid_deferred` sponsors.
- `open_invoice` = Σ `package_amount` of `open_invoice` sponsors.
- `proposal_only` = Σ `package_amount` of `proposal_only` sponsors.
- `open_invoice_balance` = Σ `open_balance` of `open_invoice` sponsors.

Sort `sponsor_statuses` by `account_name` ascending.

### 3.2 Badge → lead classification (precedence order)
Apply in this order; first match wins:

1. **Non-business badge** — `badge_type` not a business type (e.g. `student`, `press`)
   → classification `excluded`, reason `non_business_badge`, crm_action `no_action`/`no_import`.
2. **Sponsor attendee** — `badge_type == "sponsor"`, **or** the (company_name, contact_name)
   is a `ticket_contacts` entry of a **confirmed** sponsor order → classification
   `sponsor_attendee`, excluded from leads. (Campaign-member target status
   `attended_sponsor` if scanned/attended, else `registered_sponsor`.)
3. **Inactive sponsor record** — the contact is a ticket contact of a `canceled`/`no_show`
   sponsor order → classification `excluded`, reason `inactive_sponsor_record`.
4. **Existing disqualified** — the company's CRM account `status == "disqualified"` →
   classification `excluded`, reason `existing_disqualified`. (Sponsor-order reasons in
   steps 2–3 take precedence over this for companies that also had a sponsor order.)
5. **Missing contact** — the badge has **neither** a normalizable email **nor** a
   normalizable phone → classification `excluded`, reason `missing_contact`.
6. **Qualified non-sponsor lead** — otherwise → classification
   `qualified_non_sponsor_lead`. These are the sales-handoff leads.

> Note on `proposal_sent` sponsors: only **confirmed** sponsors' ticket contacts are
> `sponsor_attendee`. A `proposal_sent` sponsor's ticket contact who attended on a regular
> (attendee) badge is treated as a normal lead subject to steps 4–6, while the company
> still appears in `sponsor_statuses` as `proposal_only` (a finance/proposal matter, not a
> lead-exclusion matter).

### 3.3 Qualified non-sponsor leads
- Each qualified lead's `opportunity_amount` = `event.lead_opportunity_amount` (per-lead
  constant from the event record).
- `lead_pipeline_total` (Family-A1 schema) = (number of qualified leads) × `lead_opportunity_amount`.
- `opportunity_summary.open_opportunity_total_usd` / `open_opportunity_count` (Family-A2
  schema) = same total / count of qualified non-sponsor leads (the new open opportunities
  being handed off). `lead_opportunity_amount_usd` = the per-lead unit.
- `qualified_non_sponsor_account_names` = company (account) names of qualified leads,
  sorted ascending.
- CRM action per qualified lead:
  - Account exists (section 2.2) → `crm_account_action = update_existing`; else `create_account`.
  - Contact exists → `crm_contact_action = update_existing`; else `create_contact`.
  - Campaign member: if a campaign member already exists for (account, contact, event) →
    `update` (or `no_action` if its status is already the correct target); else `create`
    (`add_campaign_member`). Target status `attended` for non-sponsor leads.
- For badge-only leads (no CRM contact), emit `normalized_email` / `normalized_phone`
  (empty string allowed when absent).

CRM action counts (Family-A1): `accounts_create`, `accounts_update`, `contacts_create`,
`contacts_update`, `campaign_members_create`, `campaign_members_update` — counts of the
above actions across all qualified leads.

### 3.4 Sponsor finance follow-up
- Targets = sponsors with `open_balance > 0` (i.e. `open_invoice` sponsors).
- `sponsor_finance_accounts` / `unpaid_sponsor_account_names` = their account names
  (sorted ascending). `unpaid_sponsor_total_usd` / `open_invoice_balance` = Σ open balances.
- `sponsor_finance_task_count` = number of such accounts.
- `sponsor_finance_due_date` / `sponsor_followup.followup_due_date` =
  `event.end_date` + `event.sponsor_followup_days_after_end`.
- `proposal_only` sponsors are **not** finance collection targets (no invoice, no balance).

### 3.5 Exclusions & sorting
- `excluded_records` (Family-A1): `{company_name, contact_name, reason}` where reason ∈
  `sponsor_attendee | existing_disqualified | inactive_sponsor_record | non_business_badge`.
  Sort by `company_name` asc, then `contact_name` asc.
- `badge_decisions` (Family-A2): one row per badge with `classification`, `crm_action`,
  `exclusion_reason` (null when qualified). Sort by `badge_id` asc.
- `exclusion_counts` (Family-A2): counts for `sponsor_attendee`, `non_business_badge`,
  `existing_disqualified`, `missing_contact` (integer, may be 0).
- `campaign_member_actions` (Family-A2): `{subject_key, account_name, contact_name, action,
  target_status}`. `action` ∈ `create|update|no_action|no_import`; `target_status` ∈
  `attended_sponsor|registered_sponsor|attended|excluded`. `subject_key` = a stable sort
  key for the contact (contact_name, or account_name+contact_name). Sort by `subject_key` asc.
- `badge_only_contacts` (Family-A2): `{company_name, contact_name, normalized_email,
  normalized_phone}`. Sort by `company_name` asc.

## 4. Family B — Trade-show prospecting

Inputs: `/api/tradeshows/{show}/exhibitors`, `/api/tradeshows/{show}/meeting_interest`,
`/api/crm/accounts`, `/api/crm/contacts`, `/api/policies`.

`meeting_interest` is a list keyed by `company_name`; match an exhibitor to its
meeting-interest entry (if any) by `company_name`. An exhibitor with no
meeting-interest entry has `requested_demo = false` and `interest_score = 0`.

### 4.1 Qualification & platform classification
From each exhibitor's `description` (and company context), decide whether it **builds or
OEM-builds** one or more target platforms. Assign the platform enums it builds:
- `AUV` — builds autonomous/autonomous underwater vehicles, AUV scouts/pods/mapping pods.
- `ROV` — builds (manufactures) ROVs / inspection-class / pen-cleaning / resident ROVs.
- `Underwater Camera` — OEM-builds underwater camera modules/systems/cameras.

A description may yield multiple platforms. Output `platforms` in enum order:
`AUV, ROV, Underwater Camera`. Qualified = builds/OEM-builds ≥1 target platform.

### 4.2 Exclusion classification (relationship type)
Exhibitors that do **not** build a target platform are excluded. Classify the relationship:
- **distributor** — reseller, dealer, sales agent, distributor of others' platforms.
- **service_provider** — consulting, rental fleet, inspection *services* that operate
  others' rented/platforms; or a software/analytics-only company with no hardware.
- **sensor_vendor** — makes sensors/probes only (no platform).
- **research** — academic / research lab.
- **other / not target market** — anything else non-adjacent (only when the template allows
  a `not_target_market`-style reason).

Map the relationship to the exclusion-reason enum **the specific template permits**:
- distributor → `distributor_only`
- service_provider → `service_only`
- sensor_vendor → `sensor_only` (Family-B2) **or** `sensor_vendor_only` (Family-B1)
- research → `research_only`
- other → `not_target_market` (Family-B1 only)

Emit exactly the strings in the template's `allowed_values`. Family-B2 also requires a
`relationship_type` field (`distributor|service_provider|sensor_vendor|research`).

### 4.3 Priority tier (shared rule)
Default thresholds (override per task prompt if it states different numbers):
- **A** = `requested_demo == true` AND `interest_score ≥ 90`.
- **B** = `requested_demo == true` AND `interest_score ≥ 80`.
- **C** = all other qualified leads.

### 4.4 Opportunity sizing (Family-B2)
Default amounts (override per task prompt): A = USD 120000, B = USD 90000, C = USD 50000.
`opportunity_estimate_usd` per lead by tier; `total_estimated_opportunity_usd` = Σ.

### 4.5 CRM action (Family-B2)
- Qualified exhibitor with non-null `crm_account_id` → `crm_action = update_existing`;
  `crm_account_id` echoed.
- Qualified exhibitor with null `crm_account_id` → `crm_action = create_account`;
  `crm_account_id = null`.
- Excluded exhibitors → `crm_action = no_import`.
- `existing_crm_overlap_count` / `existing_crm_overlap_account_ids` = qualified exhibitors
  that already have a CRM account; account IDs sorted ascending.

### 4.6 Ranking & counts
- **Family-B2 `ranked_leads`** sort: (1) `requested_demo` true first, (2) `interest_score`
  descending, (3) broader platform coverage (count of platforms) descending,
  (4) `company_name` ascending. `rank` is 1-based contiguous.
- **Family-B1 `qualified_exhibitors`** sort: `company_name` ascending (no ranking).
- `excluded_*` lists sort by `company_name` ascending.
- `platform_coverage_counts` / `platform_counts`: for each platform enum, the number of
  qualified leads that cover it (a lead covering 2 platforms counts in both).
- `priority_counts`: {A, B, C} counts of qualified leads.
- `qualified_total` / `qualified_lead_count` = number of qualified leads.
- `excluded_count` / `excluded_near_misses_total` = number of excluded exhibitors.

## 5. Family C — Import cleaning

Inputs: `/api/import_batches` (batch metadata incl. `campaign_code`),
`/api/import_batches/{batch}/raw_contacts`, `/api/import_batches/{batch}/suppression`
(the suppression list is global/shared across batches), `/api/crm/accounts`,
`/api/crm/contacts`, `/api/policies`.

### 5.1 Normalize every raw row
- `email` → normalized (trim+lowercase) or `""`.
- `phone` → digits-only or `""`.
- Keep `row_id`, `source_name`, `captured_at`, `company_name`, `contact_name` from the row.

### 5.2 Removal decisions (apply in this order)
1. **Duplicate** — group rows by normalized email (primary duplicate key). Within a group:
   - **Winner** = the row with the **earliest `captured_at`**; tie-break by **lowest
     `row_id`** ascending. (Earliest capture = original record; its data is kept.)
   - All other rows in the group are removed with reason `duplicate`.
   - Record in `duplicate_summary`: per key `{key, winner_row_id, removed_row_ids}`;
     `duplicate_keys` sorted by `key` ascending; `duplicate_removed_count` = total losers.
   - The winner's `clean_contact_id` and `source_row_id` = the winner `row_id`;
     `captured_at` = the winner's timestamp.
2. **Suppressed** — if the row's normalized email OR normalized phone matches any
   suppression-list entry → removed with reason `suppressed`; action `suppress`.
3. **Missing contact** — if the row has **neither** a normalized email **nor** a normalized
   phone → removed with reason `missing_contact`; action `no_import`.

> A row with email but no phone (or phone but no email) is **not** missing-contact — it is
> usable. Only the total absence of both contact channels makes a row unusable.
> Duplicates are resolved before suppression/missing checks; only the surviving winner of
> a duplicate group is screened against suppression/missing.

### 5.3 Clean contacts (survivors)
For each surviving (non-removed) row:
- `crm_action`:
  - `update_existing` if an existing CRM account matches (email domain or company name);
    set `existing_account_id`.
  - else `create_account`; `existing_account_id = null`.
- `existing_contact_id`: set if a CRM contact matches (by normalized email, else same
  account + same `contact_name`); else `null`.
- `email`/`phone` = normalized values (or `""`).
- `source_name` ∈ `badge_scan|sponsor_form|partner_upload|webinar_form|exhibitor_form|manual_upload`.

### 5.4 Totals & counts
- `import_action_totals` = `{create_account, update_existing, no_import, suppress}`:
  - `create_account` = clean survivors that are new accounts.
  - `update_existing` = clean survivors matching an existing account.
  - `no_import` = removed-as-missing-contact rows.
  - `suppress` = removed-as-suppressed rows.
  - (Duplicate losers are tracked in `duplicate_summary`, not in `import_action_totals`.)
- `removal_summary`:
  - `unusable_removed_count` = `missing_contact` removals.
  - `suppressed_removed_count` = `suppressed` removals.
  - `removed_rows` = **all** removed rows (duplicates + missing + suppressed), each
    `{row_id, reason}` with reason ∈ `duplicate|missing_contact|suppressed`; sort by
    `row_id` ascending.
- `campaign_member_import_count` = number of clean survivors (each becomes a member of the
  batch's `campaign_code`).
- `batch_id` and `campaign_code` come from `/api/import_batches`.
- `clean_contacts` sorted by `clean_contact_id` ascending.

## 6. Opportunity / pipeline math summary

- Event handoff: per-qualified-lead amount = `event.lead_opportunity_amount`; pipeline =
  count × amount. (Do not use CRM opportunity records for the lead pipeline.)
- CRM `opportunities` are sponsor/opportunity records tied to accounts via `event_id`;
  `stage == "closed_won"` is closed; other stages (`proposal`, `qualification`,
  `discovery`) are open. Use these only where a template explicitly asks about existing
  open opportunities.
- Prospecting: per-lead amount by priority tier (prompt-specified; defaults A=120000,
  B=90000, C=50000); total = Σ.

## 7. Sort-key reference

| List | Sort key |
|---|---|
| `sponsor_statuses` | `account_name` asc |
| `qualified_lead_accounts` | `account_name` asc |
| `excluded_records` | `company_name` asc, then `contact_name` asc |
| `badge_decisions` | `badge_id` asc |
| `badge_only_contacts` | `company_name` asc |
| `campaign_member_actions` | `subject_key` asc |
| `qualified_non_sponsor_account_names` | string asc |
| `unpaid_sponsor_account_names` | string asc |
| `qualified_exhibitors` (B1) | `company_name` asc |
| `excluded_near_misses` (B1) | `company_name` asc |
| `ranked_leads` (B2) | `rank` asc (1-based contiguous) |
| `excluded_exhibitors` (B2) | `company_name` asc |
| `existing_crm_overlap_account_ids` | account ID asc |
| `clean_contacts` | `clean_contact_id` asc |
| `duplicate_keys` | `key` asc |
| `removed_rows` | `row_id` asc |

## 8. Execution checklist for any task

1. Read the task prompt; identify the family (event handoff / prospecting / import) and the
   target `event_id` / `show_id` / `batch_id`.
2. Read the `answer_template.json` — it defines the exact required keys, enums, and
   ordering. Conform to **its** allowed_values (mind spelling variants).
3. `GET /api/policies`; conform sponsor-status and platform enums to it.
4. Fetch the family's input endpoints (section 3/4/5).
5. Apply the family's decision procedure (precedence order matters).
6. Compute due dates from the event's own `followup_days_after_end` /
   `sponsor_followup_days_after_end` constants.
7. Normalize all emails/phones; match CRM accounts/contacts per section 2.2.
8. Apply every template sort rule (section 7); use integers for USD and counts.
9. Emit exactly one JSON object matching the template — no extra fields, no prose.

## 9. Reasoning notes & judgment calls (apply consistently)

- **Duplicate winner = earliest `captured_at`, tie-break lowest `row_id`.** The earliest
  capture is the original record and tends to carry the canonical company spelling that
  matches the CRM account name.
- **Sponsor status precedence**: any unpaid balance ⇒ `open_invoice` (even if a separate
  invoice for the same sponsor is `paid_deferred`). Handle multi-invoice sponsors by
  aggregating per (account, event).
- **Badge classification precedence**: non-business → sponsor-attendee (confirmed) →
  inactive-sponsor (canceled/no_show) → existing-disqualified → missing-contact →
  qualified lead. Sponsor-order reasons outrank CRM-disqualified for companies that had a
  sponsor order.
- **Sponsor finance follow-up = open-balance sponsors only** (`open_invoice`).
  `proposal_only` and fully-paid `paid_deferred` sponsors are not collection targets.
- **Missing-contact = neither email nor phone** (symmetric: email-only and phone-only rows
  are usable).
- **Prospecting exclusions**: the relationship classification is stable, but the emitted
  enum string must match the template (`sensor_only` vs `sensor_vendor_only`;
  `not_target_market` only where allowed).
- When a field is genuinely ambiguous and the template does not disambiguate, choose the
  reading that keeps the dataset internally consistent (e.g. totals reconcile with the
  row counts; CRM action counts reconcile with the lead list).
