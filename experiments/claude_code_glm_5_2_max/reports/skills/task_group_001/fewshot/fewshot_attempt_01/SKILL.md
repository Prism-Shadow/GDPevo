# HarborCRM CRM-Marketing Task Skill

A transferable playbook for solving HarborCRM post-event / prospecting / import-batch
handoff tasks. The remote dataset is deterministic and the business conventions below
are stable across tasks; only the event, tradeshow, or import batch varies.

## 0. Environment & ground rules

- Base URL (the only allowed API): `<remote-env-url>`
- All endpoints are read-only GET. Pipe `curl -s <url>` through `python3 -m json.tool`.
- Always read the task's own `answer_template.json` first. The template is the contract:
  it dictates the exact top-level keys, item keys, **allowed enum values**, **ordering
  rules**, and number formatting. Two tasks that look similar can use slightly different
  enum vocabularies (e.g. `sensor_vendor_only` vs `sensor_only`) — always emit the
  template's allowed values, never a synonym from memory.
- Return ONE JSON object only, no prose, no extra fields.

### Endpoint reference

| Endpoint | Use |
|---|---|
| `GET /api/events` | List events (campaign_code, dates, followup day offsets, lead_opportunity_amount) |
| `GET /api/events/{event_id}` | Single event detail |
| `GET /api/events/{event_id}/orders` | Sponsor orders (= sponsor_packages) |
| `GET /api/events/{event_id}/sponsor_packages` | Same sponsor order data |
| `GET /api/events/{event_id}/badges` | Badge scans for the event |
| `GET /api/finance/invoices?event_id={event_id}` | Invoices for sponsors |
| `GET /api/crm/accounts` | All CRM accounts (account_id, domain, status, disqualified_reason) |
| `GET /api/crm/contacts` | All CRM contacts (contact_id, account_id, email, phone, opted_out) |
| `GET /api/crm/opportunities` | CRM opportunities (mostly informational; lead opp $ comes from the event) |
| `GET /api/crm/campaign_members?event_id={event_id}` | Existing campaign members for an event |
| `GET /api/tradeshows` | Tradeshow list |
| `GET /api/tradeshows/{show_id}/exhibitors` | Exhibitor rows (incl. `crm_account_id` field) |
| `GET /api/tradeshows/{show_id}/meeting_interest` | Per-company interest_score + requested_demo (keyed by company_name) |
| `GET /api/import_batches` | Batch metadata (campaign_code) |
| `GET /api/import_batches/{batch_id}/raw_contacts` | Rows to clean |
| `GET /api/import_batches/{batch_id}/suppression` | Suppression list for the batch |
| `GET /api/policies` | Policy enums (platform_enums, sponsor status_enums) |

### Task-type detection
Map the prompt to a type by the entity it names:
- **Event handoff** — prompt names an `event_id` and talks about sponsors/badges/invoices/reconciliation. Endpoints: events, orders, badges, invoices, crm/accounts, crm/contacts, crm/opportunities, campaign_members, policies. (train_001 and train_004 shapes.)
- **Tradeshow prospecting** — prompt names a `show_id` / trade show and qualified leads/exhibitors. Endpoints: tradeshows, exhibitors, meeting_interest, crm/accounts, policies. (train_002 and train_005 shapes.)
- **Import-batch cleaning** — prompt names a `batch_id` and asks to prepare contacts for CRM import. Endpoints: import_batches, raw_contacts, suppression, crm/accounts, crm/contacts, policies. (train_003 shape.)

---

## 1. Universal normalization conventions

### Email normalization
- `lowercase` + `trim` surrounding whitespace.
- Example: `" Dana.Ruiz@HelioWare.example "` → `dana.ruiz@helioware.example`; `"KENJI.SATO@monarchfoods.example"` → `kenji.sato@monarchfoods.example`.
- A field that is only whitespace → empty string `""`.

### Phone normalization
- **Strip every non-digit character.** Keep all digits that remain, *including a leading
  country-code `1` if it was present in the source.*
- Do NOT force 10 digits; do NOT strip a leading `1`.
- `"+1 (512) 555-0121"` → `"15125550121"`; `"1.206.555.0177"` → `"12065550177"`; `"212-555-0166"` → `"2125550166"`; `"(415) 555-0188"` → `"4155550188"`.
- No phone supplied → `""` (empty string, not null).

### Account matching (for badge leads & import rows)
- Match a row to an existing CRM account by **email domain**: take the part of the
  normalized email after `@`, compare to `account.domain` (case-insensitive).
  - `dana.ruiz@helioware.example` → domain `helioware.example` → account `acct_helio_ware`.
- If the account exists → `update_existing` (account action). If not → `create_account`.
- If a row has no email, you cannot match by domain → `create_account` (unless suppressed/missing).

### Contact matching
- Match to an existing CRM contact by **normalized email equality** against `contact.email`
  (lowercased). If no exact email match → the contact is new (`existing_contact_id: null`,
  create the contact). Do not infer a contact match from name alone when emails differ.

---

## 2. Event-handoff conventions (sponsor + badge reconciliation)

### 2.1 Sponsor-status classification
For each sponsor order/package at the event, classify using `order_status` and the
matching invoice (match invoice by `account_id` within the event's invoices):

| order_status | invoice state | sponsor_status | invoice_id | paid_amount | open_balance |
|---|---|---|---|---|---|
| `confirmed` | invoice.status `paid_deferred` OR paid_amount >= amount | `paid_deferred` | invoice.id | invoice.paid_amount | `0` |
| `confirmed` | invoice.status `open` (paid_amount < amount) | `open_invoice` | invoice.id | invoice.paid_amount | `amount - paid_amount` |
| `proposal_sent` | no invoice | `proposal_only` | `null` | `0` | `0` |
| `canceled` | (any) | **excluded entirely** from sponsor_statuses | — | — | — |

- `amount_usd` / `package_amount` reported = the sponsor package `amount`.
- An account that is not a sponsor at all (no order, not canceled) would be `not_sponsor`
  (enum value; rarely appears in the sponsor list).
- `paid_deferred` means paid in full (deferred revenue recognition) — it is **not** a
  collection follow-up target.

### 2.2 Sponsor revenue rollup (when the schema has a totals block)
- `paid_deferred` total = Σ package `amount` of all `paid_deferred` sponsors.
- `open_invoice` total = Σ package `amount` of all `open_invoice` sponsors.
- `proposal_only` total = Σ package `amount` of all `proposal_only` sponsors.
- `open_invoice_balance` = Σ `open_balance` of `open_invoice` sponsors (i.e. Σ (amount − paid)).
- (Totals use package amounts, not paid amounts.)

### 2.3 Badge classification & exclusion precedence
Classify each badge for the event, in this precedence order:

1. **existing_disqualified** — if the badge company matches a CRM account whose
   `status == "disqualified"` (any `disqualified_reason`). This wins over everything.
2. **sponsor_attendee** — else if the badge company is an **active** sponsor (has a
   non-`canceled` sponsor order at this event), OR `badge_type == "sponsor"`.
3. **non_business_badge** — else if `badge_type` is a non-business type
   (`student`, `press`, and similar). Reason `non_business_badge`.
4. **missing_contact** — else if the badge has no contact name / no contactable info.
5. **qualified_non_sponsor_lead** — otherwise (an `attendee`-type badge on a valid,
   non-disqualified, non-sponsor company). These go to the qualified-lead list.

Notes:
- A `canceled` sponsor whose account is also disqualified shows as `existing_disqualified`
  (rule 1 wins). A `canceled` sponsor whose account is *not* disqualified would surface as
  `inactive_sponsor_record` (enum value) — apply this when you see a canceled order with a
  non-disqualified account and an associated badge/contact.
- `existing_disqualified` covers any badge/contact whose CRM account is disqualified,
  even if it has no sponsor relationship.

### 2.4 Enumerating excluded sponsor attendees (event-handoff schemas that lump them)
Some schemas collect sponsor attendees into an `excluded_records` list. For each
**active** (non-canceled) sponsor account, emit **exactly one** `sponsor_attendee` record:
- Prefer a badge captured for that sponsor company (the contact on that badge).
- If the sponsor has no badge at the event, fall back to the **first** `ticket_contact`
  in the sponsor package.
- Do **not** enumerate companion / additional ticket contacts beyond the one
  representative per account (e.g. a platinum sponsor listing two ticket contacts emits
  one excluded record, the attendee of record).

Plus all non-qualifying badges (non-business, disqualified) become their own excluded
records. De-duplicate so a contact isn't listed twice.

### 2.5 Qualified non-sponsor leads (event handoff)
- Source: `attendee`-type badges whose company is NOT an active sponsor and whose CRM
  account is NOT disqualified.
- Account action: `create_account` if no existing account by email domain, else `update_existing`.
- Contact action: `create_contact` if no existing contact by email, else `update_existing`
  (no example of update_existing in trains, but follow the email-match rule).
- Campaign-member action: `add_campaign_member` (create) if the contact is not already a
  campaign member for this event; if already a member, treat as update/no new create.
- Normalized email/phone come from the badge (apply §1 rules).
- `opportunity_amount` per qualified lead = the event's `lead_opportunity_amount`
  (a single field on the event object). Pipeline/total = (qualified lead count) ×
  event.lead_opportunity_amount.

### 2.6 Opportunity / pipeline math (per schema wording)
- If the schema asks for a **per-lead** amount (e.g. `lead_opportunity_amount_usd`):
  report the event's `lead_opportunity_amount` as-is.
- If it asks for a **total** (e.g. `open_opportunity_total_usd`, `lead_pipeline_total`):
  (qualified non-sponsor lead count) × event.lead_opportunity_amount.
- `open_opportunity_count` / lead task count = number of qualified non-sponsor leads.

### 2.7 Follow-up due dates (date arithmetic)
- `lead_followup_due_date` = event.`end_date` + event.`followup_days_after_end` days
  (plain calendar days; not business days).
- `sponsor_followup_due_date` = event.`end_date` + event.`sponsor_followup_days_after_end` days.
- Format `YYYY-MM-DD`. Validate: e.g. end `2026-09-16` + 7 = `2026-09-23`; end `2026-11-05` + 2 = `2026-11-07`.

### 2.8 Sponsor finance follow-up targets
- Targets = sponsors that are **not** paid in full = `open_invoice` + `proposal_only`
  (exclude `paid_deferred` and canceled).
- `unpaid_sponsor_total_usd` / sponsor-finance total = Σ package `amount` of those targets.
- `sponsor_finance_task_count` = number of those target accounts.
- `sponsor_finance_accounts` = their account names, sorted ascending.
- Due date = sponsor_followup_due_date (§2.7).

### 2.9 CRM action counting (event handoff, count-style schemas)
For the qualified non-sponsor leads only (sponsor attendees that already exist are not
counted as creates):
- `accounts_create` = # leads with no existing account.
- `accounts_update` = # leads with an existing account.
- `contacts_create` = # leads whose contact is new (no email match).
- `contacts_update` = # leads with an existing contact (email match). (0 when none.)
- `campaign_members_create` = # leads not already a campaign member for the event.
- `campaign_members_update` = # leads already a member (0 when none).
- `lead_task_count` = qualified lead count.
Do NOT count sponsor attendees as new creates when they already exist; do NOT count
excluded/disqualified badges.

### 2.10 Campaign-member action list (event-handoff schemas with per-subject rows)
Build a row per subject that needs action, combining:
- **Existing campaign members** for the event → `action: "no_action"`, `target_status`
  = their existing status (`attended_sponsor`, `registered_sponsor`, `attended`, …).
  `subject_key` = `"{account_id}:{contact_id}"`.
- **New badge-derived actions**:
  - Qualified non-sponsor lead badge → `action: "create"`, `target_status: "attended"`,
    `subject_key: "badge:{badge_id}"`.
  - Sponsor-attendee badge whose contact/CM is new → `action: "create"`,
    `target_status: "attended_sponsor"`, `subject_key: "badge:{badge_id}"`.
  - Sponsor-attendee already an existing CM → covered by the existing-CM row (no_action).
- `target_status` enum: `attended_sponsor` (sponsor who attended), `registered_sponsor`
  (sponsor registered, not attended), `attended` (non-sponsor lead attended), `excluded`.
- Sort by `subject_key` ascending (`acct_*` keys sort before `badge:*` keys).

### 2.11 Badge-only contacts list (when schema asks for normalized badge contacts)
- Include badges that require **contact creation**: qualified non-sponsor leads that need
  a new account+contact, and sponsor-attendee badges whose contact is new.
- Exclude badges whose contact already exists and exclude non-business/disqualified badges.
- Fields: `company_name`, `contact_name`, `normalized_email` (lowercase trim; `""` if none),
  `normalized_phone` (digits only; `""` if none).
- Sort by `company_name` ascending.

### 2.12 Badge crm_action enum (combined-action schemas)
- No existing account → `create_account_contact_campaign_member`.
- Existing account, new contact → `create_contact_campaign_member`.
- Existing account + contact, no CM → `add_campaign_member`.
- Existing account + contact + CM → `no_action`.
- Excluded badge → `no_import`.
- Sponsor-attendee with existing everything → `no_action` (still classified `sponsor_attendee`).

### 2.13 Event-handoff sorting
- `sponsor_statuses` → `account_name` ascending.
- `excluded_records` → `company_name` ascending, then `contact_name` ascending.
- `qualified_lead_accounts` → `account_name` ascending.
- `badge_decisions` → `badge_id` ascending.
- `campaign_member_actions` → `subject_key` ascending.
- `badge_only_contacts` → `company_name` ascending.
- `exclusion_counts` → object, fixed keys (sponsor_attendee, non_business_badge, existing_disqualified, missing_contact).
- `opportunity_summary.qualified_non_sponsor_account_names` / `sponsor_followup.unpaid_sponsor_account_names` → account names ascending.

---

## 3. Tradeshow prospecting conventions

### 3.1 Qualification vs exclusion
An exhibitor is **qualified** iff it *makes / manufactures / OEM-builds* a target platform.
classify from `description` + context (policy says: "decide whether an account builds
target underwater platforms or is only adjacent to them"). Exclude exhibitors that are
merely adjacent:

| Inferred relationship_type | Exclusion reason (use the template's enum) |
|---|---|
| `distributor` / reseller / dealer ("does not manufacture", "reseller", "sales agent") | `distributor_only` |
| `service_provider` / consulting / operates rented gear / analytics-only dashboard | `service_only` (template may say `service_only`) |
| `sensor_vendor` / sensor-only probes ("sensor-only", "probes") | `sensor_vendor_only` (train_002) **or** `sensor_only` (train_005) — match the template |
| `research` / academic lab | `research_only` |
| otherwise not a target market | `not_target_market` (if the template lists it) |

Always use the **exact** exclusion-reason enum strings declared in that task's template.

### 3.2 Platform coverage inference
From the qualified exhibitor's `description`, detect platforms by keyword:
- `AUV` (autonomous underwater vehicle) — words "AUV".
- `ROV` (remotely operated vehicle) — words "ROV".
- `Underwater Camera` — words "camera" / "underwater camera" / "camera array/module".
- Output the list sorted in the policy/enum order: `AUV`, `ROV`, `Underwater Camera`.
  (Use `/api/policies` → `prospecting.platform_enums` for the canonical order.)
- An exhibitor can map to multiple platforms (e.g. "ROVs with camera arrays" → `[ROV, Underwater Camera]`).

### 3.3 CRM action (tradeshow)
- Use the exhibitor's **`crm_account_id`** field directly (not domain matching).
- Non-null → `crm_action: "update_existing"`, `crm_account_id`: that id.
- Null → `crm_action: "create_account"`, `crm_account_id: null`.
- Excluded exhibitors → `crm_action: "no_import"`.

### 3.4 interest_score / requested_demo
- Join exhibitor to `meeting_interest` by `company_name` (the meeting_interest rows are
  keyed by company_name, not by company_id).
- `requested_demo` (boolean) and `interest_score` (integer) come from that row.
- If a qualified exhibitor has no meeting_interest row, treat `requested_demo: false`,
  `interest_score: 0` (no example of this; fall back conservatively).

### 3.5 Priority tier (universal prospecting convention)
Even when a terse prompt doesn't state it, assign tier from demo + score:
- **A** — `requested_demo == true` AND `interest_score >= 90`.
- **B** — `requested_demo == true` AND `interest_score >= 80` (and < 90).
- **C** — all other qualified leads (no demo, or score < 80).
If the prompt explicitly overrides, follow the prompt.

### 3.6 Opportunity sizing (when an `opportunity_estimate_usd` field exists)
Standard fixed sizing by tier:
- A → `120000`, B → `90000`, C → `50000` (USD integer).
- `total_estimated_opportunity_usd` = Σ across ranked leads.
(If the prompt states different numbers, use the prompt's.)

### 3.7 Ranking qualified leads
Sort key (in order):
1. `requested_demo` descending (`true` before `false`).
2. `interest_score` descending.
3. Broader platform coverage descending (count of platforms, more first).
4. `company_name` ascending.
Assign `rank` as 1-based contiguous integers in that order.

### 3.8 Aggregates
- `qualified_lead_count` / `qualified_total` = # qualified exhibitors.
- `excluded_count` / `excluded_near_misses_total` = # excluded exhibitors.
- `existing_crm_overlap_count` = # qualified exhibitors with non-null `crm_account_id`.
- `existing_crm_overlap_account_ids` = those ids, sorted ascending.
- `platform_coverage_counts` / `platform_counts` = for each platform enum, count of
  qualified exhibitors that cover it (an exhibitor covering 2 platforms counts once in
  each). Keys are all platform enums; value type integer.
- `priority_counts` (if required) = count of A / B / C among qualified leads.
- `total_estimated_opportunity_usd` = Σ opportunity_estimate (§3.6).

### 3.9 Tradeshow sorting
- `qualified_exhibitors` → `company_name` ascending.
- `ranked_leads` → `rank` ascending (per §3.7).
- `excluded_exhibitors` / `excluded_near_misses` → `company_name` ascending.

---

## 4. Import-batch cleaning conventions

### 4.1 Inputs
- Raw rows: `/api/import_batches/{batch_id}/raw_contacts`.
- Suppression: `/api/import_batches/{batch_id}/suppression`.
- `campaign_code` and `batch_id` come from `/api/import_batches` (match by batch_id).
- Existing accounts/contacts via `/api/crm/accounts`, `/api/crm/contacts`.

### 4.2 Normalization (apply to every row)
- `email` → lowercase + trim (§1). Whitespace-only → `""`.
- `phone` → digits only (§1). Whitespace-only → `""`.

### 4.3 Removal pipeline (in order)
1. **missing_contact** — after normalization, if `email == ""` AND `phone == ""` → remove
   with reason `missing_contact`. (A row with email XOR phone is usable.)
2. **duplicate** — group remaining rows by normalized `email` (only rows that have an
   email are candidates; rows without email are not deduped by phone). Within a group:
   - Winner = the row with the **latest `captured_at`**.
   - On an exact `captured_at` tie, prefer the source earlier in this priority:
     `badge_scan` > `sponsor_form` > `partner_upload` > `webinar_form` > `exhibitor_form`
     > `manual_upload` (equivalently, the higher row_id).
   - All non-winner rows in the group → remove with reason `duplicate`.
   - Duplicate key reported as `"email:{normalized_email}"`.
3. **suppressed** — for each remaining (winner) row, remove with reason `suppressed` if
   its normalized email matches any suppression `email` **OR** its normalized phone matches
   any suppression `phone`. (Suppression entries with empty phone match by email only;
   empty-email entries match by phone only.)
4. Survivors = `clean_contacts`.

### 4.4 clean_contacts fields
- `clean_contact_id` = `source_row_id` = the **winner's** `row_id`.
- `company_name`, `contact_name` from the winning row (as-is).
- `email` = normalized email (or `""`).
- `phone` = normalized digits-only phone (or `""`).
- `source_name` = winner's `source_name` (enum: badge_scan, sponsor_form, partner_upload,
  webinar_form, exhibitor_form, manual_upload).
- `captured_at` = winner's ISO timestamp.
- `existing_account_id` = matched account id by email domain (§1), else `null`.
- `existing_contact_id` = matched contact id by normalized email (§1), else `null`.
- `crm_action`:
  - `update_existing` — if an existing account matched (by domain).
  - `create_account` — if no existing account matched.
  - (Rows that are removed never reach this list; suppressed/missing/duplicate are not
    clean_contacts.)

### 4.5 duplicate_summary
- `duplicate_removed_count` = total number of rows removed as duplicates.
- `duplicate_keys` = list of `{ "key": "email:{normalized_email}", "winner_row_id": <id>,
  "removed_row_ids": [<ids>] }`, sorted by `key` ascending.

### 4.6 removal_summary
- `unusable_removed_count` = # rows removed as `missing_contact` ONLY. (Duplicates are NOT
  "unusable" — each duplicate group has a surviving winner, so the losers are redundant, not
  unusable. Duplicates are counted in `duplicate_summary.duplicate_removed_count`, not here.)
- `suppressed_removed_count` = # rows removed as `suppressed`.
- `removed_rows` = ALL removed rows (duplicates + missing + suppressed) as
  `{ "row_id": <id>, "reason": <enum> }`, where reason ∈ {`duplicate`, `missing_contact`,
  `suppressed`}, sorted by `row_id` ascending. (Note: `removed_rows` is the union;
  `unusable_removed_count` + `suppressed_removed_count` will NOT sum to `len(removed_rows)`
  because duplicate rows appear in `removed_rows` but in neither count.)

### 4.7 import_action_totals
Count of clean + removed rows by final action (integers):
- `create_account` = # clean rows with no existing account.
- `update_existing` = # clean rows with an existing account.
- `no_import` = # rows removed as `duplicate` + `missing_contact`.
- `suppress` = # rows removed as `suppressed`.
- Sanity: `create_account + update_existing + no_import + suppress` = total raw rows.
- `campaign_member_import_count` = # clean rows (`create_account + update_existing`) —
  every surviving contact becomes a member of the batch's campaign.

### 4.8 Import-batch sorting
- `clean_contacts` → `clean_contact_id` ascending.
- `duplicate_summary.duplicate_keys` → `key` ascending.
- `removal_summary.removed_rows` → `row_id` ascending.

---

## 5. Field-by-field quick reference (most common schemas)

### Event handoff (sponsor_statuses item)
`account_id`, `account_name`, `sponsor_status` (paid_deferred|open_invoice|proposal_only|not_sponsor),
`amount_usd`/`package_amount` (= package amount, integer), `invoice_id` (or null),
`paid_amount` (integer), `open_balance` (= amount − paid; 0 for paid/proposal).

### Event handoff (qualified_lead_accounts item)
`account_name`, `account_id` (null if new), `primary_contact` (badge contact_name),
`normalized_email`, `normalized_phone`, `crm_account_action` (create_account|update_existing),
`crm_contact_action` (create_contact|update_existing), `campaign_member_action`
(add_campaign_member), `opportunity_amount` (= event.lead_opportunity_amount).

### Event handoff (excluded_records item)
`company_name`, `contact_name`, `reason`
(sponsor_attendee|existing_disqualified|inactive_sponsor_record|non_business_badge).

### Event handoff (follow_up)
`lead_due_date` (end + lead days), `lead_task_count` (= # qualified leads),
`sponsor_finance_due_date` (end + sponsor days), `sponsor_finance_task_count`
(= # unpaid sponsors), `sponsor_finance_accounts` (unpaid sponsor names ascending).

### Tradeshow (ranked_leads item)
`rank`, `company_id`, `company_name`, `booth`, `country`, `website`, `platforms` (enum
order), `crm_account_id` (or null), `crm_action` (create_account|update_existing|no_import),
`requested_demo`, `interest_score`, `priority_tier` (A|B|C), `opportunity_estimate_usd`.

### Tradeshow (excluded item)
`company_id`, `company_name`, `relationship_type` (distributor|service_provider|sensor_vendor|research),
`exclusion_reason` (template enum), `crm_action` (`no_import`).

### Import (clean_contacts item)
`clean_contact_id`, `source_row_id`, `company_name`, `contact_name`, `email`, `phone`,
`source_name`, `captured_at`, `crm_action` (create_account|update_existing|no_import|suppress),
`existing_account_id` (or null), `existing_contact_id` (or null).

---

## 6. Common pitfalls

- **Don't strip a leading `1` from phones.** Just remove non-digits.
- **Don't dedupe import rows by phone** — only by normalized email, and only when an email
  exists.
- **`paid_deferred` is paid** — exclude it from sponsor finance follow-up targets.
- **Canceled sponsors are excluded from `sponsor_statuses`** entirely; if their account is
  also CRM-disqualified, their badge lists as `existing_disqualified`.
- **Exclusion-reason enums differ between templates** (`sensor_vendor_only` vs `sensor_only`,
  `service_only` always). Read the template's `allowed_values`.
- **Opportunity $ per lead = the event's `lead_opportunity_amount`**, not the CRM
  `opportunities` amounts (those are sponsor/opportunity records, not the lead sizing).
- **Tradeshow CRM match uses the exhibitor's `crm_account_id` field directly**; do not
  re-derive by domain for tradeshow tasks.
- **One excluded sponsor_attendee per active sponsor account** (badge contact preferred,
  else first ticket_contact); don't enumerate companion tickets.
- **Date arithmetic is calendar days** off `event.end_date`, using the event's own
  `followup_days_after_end` and `sponsor_followup_days_after_end` fields.
- **meeting_interest is keyed by `company_name`**, not company_id — join on name.
- Always obey the template's `ordering` clauses and `numeric_precision` (integers, USD).
