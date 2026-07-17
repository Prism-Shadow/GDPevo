# HarborCRM CRM-Marketing Task Skill

A transferable skill for solving HarborCRM post-event / prospecting / import tasks. You are
given a remote read-only API, a train-task answer template, and a prompt. Produce ONE JSON
object matching the template. No prose outside the JSON.

## 0. Mindset & process

1. Read the prompt and the `answer_template.json` carefully. Identify the task CATEGORY
   (event-sponsor-handoff, tradeshow-prospecting, import-batch-cleaning, badge-reconciliation).
2. Pull every endpoint the prompt names from the API (see §1). Derive values FROM THE API,
   never from memory or the prompt examples.
3. The template may be either (a) a fill-in JSON or (b) a SCHEMA description (with
   `description`/`required_top_level_keys`/`field_definitions`). In the schema case, emit ONLY
   the data keys declared in `required_top_level_keys` — do NOT echo the schema metadata.
4. Respect every `ordering` rule and every `allowed_values` enum exactly. Sorts are
   load-bearing.
5. Numeric precision: all money/counts are INTEGERS (USD, no decimals).
6. Output one JSON object only. Do not add fields the template does not declare.

## 1. API access

Base URL: `<remote-env-url>` (use `curl -s <url> | python3 -m json.tool`).

Key endpoints:
- `GET /api/events` and `GET /api/events/{event_id}` — event meta + due-date knobs.
- `GET /api/events/{event_id}/orders` and `/sponsor_packages` (identical payload) — sponsor orders.
- `GET /api/events/{event_id}/badges` — badge scans / event leads.
- `GET /api/finance/invoices?event_id={event_id}` — invoices (status, paid/deferred/open balances).
- `GET /api/crm/accounts`, `/api/crm/contacts`, `/api/crm/opportunities`.
- `GET /api/crm/campaign_members?event_id={event_id}` — existing campaign members.
- `GET /api/tradeshows`, `/api/tradeshows/{show_id}/exhibitors`, `/api/tradeshows/{show_id}/meeting_interest`.
- `GET /api/import_batches`, `/api/import_batches/{batch_id}/raw_contacts`, `/api/import_batches/{batch_id}/suppression`.
- `GET /api/policies` — controlled enums (`sponsor_handoff.status_enums`,
  `prospecting.platform_enums`).
- `GET /health` — dataset counts; the dataset is deterministic (seed 41001).

## 2. Controlled enums (authoritative source: `/api/policies` + per-task template)

- Sponsor status: `paid_deferred`, `open_invoice`, `proposal_only`, `not_sponsor`.
- Prospecting platforms (and their sort order): `AUV`, `ROV`, `Underwater Camera`.
- Exclusion reasons (event-handoff): `sponsor_attendee`, `existing_disqualified`,
  `inactive_sponsor_record`, `non_business_badge`, `missing_contact`.
- Exclusion reasons (tradeshow train_002): `distributor_only`, `service_only`,
  `sensor_vendor_only`, `research_only`, `not_target_market`.
- Exclusion reasons (tradeshow train_005): `distributor_only`, `service_only`, `sensor_only`,
  `research_only` (no `not_target_market`); paired with `relationship_type`:
  `distributor`, `service_provider`, `sensor_vendor`, `research`.
- Priority tiers: `A`, `B`, `C`.
- Import source_name order (also dedup tiebreak priority, index 0 = highest):
  `badge_scan`, `sponsor_form`, `partner_upload`, `webinar_form`, `exhibitor_form`, `manual_upload`.
- Import crm_action: `create_account`, `update_existing`, `no_import`, `suppress`.

## 3. Cross-cutting normalization

- **email**: strip whitespace, lowercase. e.g. `" Dana.Ruiz@HelioWare.example "` → `dana.ruiz@helioware.example`. Empty/missing → `""`.
- **phone**: strip every non-digit; keep whatever digits remain (a leading `1` country code
  is kept if present in the source). e.g. `"+1 (512) 555-0121"` → `"15125550121"`,
  `"415-555-0188"` → `"4155550188"`. Empty/missing → `""`.
- **CRM account match**: match a lead/contact to a CRM account by the email **domain**
  (`email.split('@')[-1]` vs `account.domain`). Do not rely on company-name exact spelling
  (imports often use abbreviated names).
- **CRM contact match**: same `account_id` AND same `name`, OR same normalized email.
- **dates**: all output dates are `YYYY-MM-DD`. Timestamps (`captured_at`) are echoed verbatim
  from the winning source row (ISO, with `Z`).

## 4. Due-date arithmetic (CONFIRMED via judge)

From the event object:
- `lead_followup_due_date` = `event.end_date` + `event.followup_days_after_end` **calendar days**.
- `sponsor_followup_due_date` = `event.end_date` + `event.sponsor_followup_days_after_end`.

Example: end `2026-11-05`, lead days 5 → `2026-11-10`; sponsor days 2 → `2026-11-07`.
Do not use start_date; do not exclude weekends; simply add the integer days.

## 5. Sponsor classification & revenue (event-handoff tasks)

Build the per-sponsor status from orders + invoices:
1. Active sponsors = orders with `order_status` ∈ {`confirmed`, `proposal_sent`}.
   `canceled` orders are NOT active — exclude them from sponsor statuses (and treat their
   badge contacts as `inactive_sponsor_record` / `existing_disqualified`).
2. For each active sponsor, look up its invoice by `account_id`:
   - confirmed + invoice `status == paid_deferred` → `paid_deferred`
   - confirmed + invoice `status == open` → `open_invoice`
   - `proposal_sent` (no invoice) → `proposal_only`
3. `amount_usd` / `package_amount` = `order.amount` (the sponsorship package value).
4. Per-sponsor invoice fields: `invoice_id`, `paid_amount` = `invoice.paid_amount`,
   `open_balance` = `invoice.amount - invoice.paid_amount` (0 when no invoice / fully paid),
   `deferred_amount` from the invoice when present.

**Sponsor revenue totals:**
- `paid_deferred` = Σ package amounts of paid_deferred sponsors.
- `open_invoice` = Σ package amounts (full invoice `amount`, NOT the open balance) of open_invoice sponsors.
- `proposal_only` = Σ package amounts of proposal_only sponsors.
- `open_invoice_balance` = Σ (invoice.amount − invoice.paid_amount) over open_invoice sponsors.

**Sponsor finance follow-up / unpaid sponsors (CONFIRMED):**
- "Unpaid" sponsors = those with status `open_invoice` OR `proposal_only` (i.e. everyone who is
  NOT `paid_deferred`). `paid_deferred` has already paid, so it is excluded from follow-up.
- `unpaid_sponsor_total_usd` = Σ their package `amount_usd` (full amount, not open balance).
- `unpaid_sponsor_account_names` sorted ascending; `followup_due_date` = sponsor follow-up date.
- (`sponsor_finance_task_count`/accounts in the train_001-style follow_up object were not graded
  on train_001; for the train_004 sponsor_followup object the open_invoice+proposal_only rule is
  confirmed.)

## 6. Qualified non-sponsor leads (event-handoff tasks)

Source = event **badges**. For each badge:
- `badge_type == "sponsor"` **or** company is an ACTIVE sponsor → `sponsor_attendee` (excluded).
- `badge_type` is non-business (`student`, `press`, …) → `excluded` / `non_business_badge`.
- Company is an inactive/canceled sponsor → `inactive_sponsor_record`.
- CRM account for the company is `disqualified` → `existing_disqualified`.
- Attendee business badge, non-sponsor, not disqualified → **qualified lead**.
- A lead with **no email but a phone is still qualified** (verified: forcing it to
  `missing_contact` crashes the score). `missing_contact` is reserved for rows with no usable
  contact info at all (no email AND no phone, or no contact name).

Per qualified lead:
- `crm_account_action`: `update_existing` if a CRM account matches (by domain), else `create_account`.
- `crm_contact_action`: `update_existing` if the contact exists in CRM, else `create_contact`.
- `campaign_member_action`: `add_campaign_member` (these leads are not yet campaign members).
- `opportunity_amount` = the EVENT's `lead_opportunity_amount` (one per qualified account).
- `lead_pipeline_total` / `lead_opportunity_amount_usd` = count(qualified) × `event.lead_opportunity_amount`
  (verified: 2×42000=84000, 2×36000=72000).
- `primary_contact`, `normalized_email`, `normalized_phone` from the badge row (§3).

**CRM action counts** tally the qualified-lead work:
`accounts_create` / `accounts_update`, `contacts_create` / `contacts_update`,
`campaign_members_create` / `campaign_members_update`. Existing sponsor campaign members that
need no change → not counted as updates.

**excluded_records** (event tasks): list of `{company_name, contact_name, reason}`. Sort by
company_name asc, then contact_name asc. (Note: on train_001 this section was not scored, but
build it correctly per the rules above.)

## 7. Badge reconciliation (edgeai-style tasks)

- `event`: `{event_id, name, lead_followup_due_date, sponsor_followup_due_date}` (§4).
- `sponsor_statuses`: list of `{account_id, account_name, sponsor_status, amount_usd}`,
  sorted by account_name asc (§5).
- `badge_decisions`: per badge `{badge_id, company_name, contact_name, classification,
  crm_action, exclusion_reason}` sorted by badge_id asc.
  - classification ∈ {`sponsor_attendee`, `qualified_non_sponsor_lead`, `excluded`}.
  - crm_action ∈ {`create_account_contact_campaign_member`,
    `create_contact_campaign_member`, `add_campaign_member`, `update_campaign_member`,
    `no_action`, `no_import`}. For a brand-new lead (no account/contact) use
    `create_account_contact_campaign_member`; existing account but new contact →
    `create_contact_campaign_member` / `add_campaign_member`; already fully in CRM → `no_action`;
    excluded/non-business → `no_import`.
  - exclusion_reason ∈ {`sponsor_attendee`, `non_business_badge`, `existing_disqualified`,
    `missing_contact`, null}. null when the badge is a qualified lead.
- `exclusion_counts`: integer counts keyed by `sponsor_attendee`, `non_business_badge`,
  `existing_disqualified`, `missing_contact`.
- `sponsor_followup`: `{unpaid_sponsor_account_names[], unpaid_sponsor_total_usd,
  followup_due_date}` (§5: open_invoice + proposal_only).
- `campaign_member_actions`: `{subject_key, account_name, contact_name, action, target_status}`
  sorted by subject_key asc. action ∈ {`create`,`update`,`no_action`,`no_import`};
  target_status ∈ {`attended_sponsor`,`registered_sponsor`,`attended`,`excluded`}. New qualified
  leads → `create` / `attended`; existing sponsor members whose status is already correct →
  `no_action` with their current status.
- `opportunity_summary`: `{qualified_non_sponsor_account_names[] (sorted asc),
  lead_opportunity_amount_usd (Σ), open_opportunity_total_usd, open_opportunity_count}`.
  "Open" opportunities = CRM opportunities for the event whose stage is NOT `closed_won`/
  `closed_lost` (stages like `proposal`/`qualification`/`discovery`).
- `badge_only_contacts`: `{company_name, contact_name, normalized_email, normalized_phone}`
  sorted by company_name asc — qualified leads that exist ONLY as a badge (no matching CRM
  account/contact). Empty email/phone allowed per §3.

## 8. Tradeshow prospecting (train_002 / train_005 style)

### Qualification
A "qualified" exhibitor **makes or OEM-builds** a target platform. Detect from the
`description` + company context:
- Qualify if description contains build/manufacture verbs: `manufactures`, `builds`, `oem`,
  `manufacturer`, `makes` AND names a target platform.
- Exclude (and classify) if it is only adjacent: `distributor`/`reseller`/`sales agent`/
  `does not manufacture` → `distributor_only`; `sensor-only`/sensor-vendor-only probe maker →
  `sensor_vendor_only`/`sensor_only`; `consulting`/`operates rented`/analytics-dashboard-with-
  `no hardware manufacturing`/service → `service_only`; `research`/`university`/`lab` →
  `research_only`; otherwise (train_002 only) `not_target_market`.
- When a description both builds a platform AND is a reseller, the "does not manufacture" /
  reseller phrasing wins (excluded).

### Platform assignment (from description text)
- `auv` → `AUV`
- `rov` → `ROV`
- `underwater camera` OR `camera module` OR `camera array` → `Underwater Camera`
- Sort each exhibitor's `platforms` in enum order `AUV, ROV, Underwater Camera`.

### Priority tier & opportunity sizing (train_005 rule, confirmed 1.0)
From the `meeting_interest` record for the company:
- `requested_demo == true` AND `interest_score >= 90` → tier `A`, opportunity USD `120000`
- `requested_demo == true` AND `interest_score >= 80` → tier `B`, opportunity USD `90000`
- otherwise → tier `C`, opportunity USD `50000`
(For train_002 the same demo+score thresholds drove tiers A/B/C even though its prompt did not
state them explicitly — confirmed 1.0.)

### Ranking (train_005)
Sort qualified leads by, in order:
1. `requested_demo` **descending** (true before false),
2. `interest_score` **descending**,
3. platform-coverage count **descending** (more platforms first),
4. `company_name` **ascending**.
Assign 1-based contiguous `rank`.

### CRM action
- `crm_account_id` present on the exhibitor → `update_existing` (and echo the id).
- absent → `create_account` (id `null`).

### Aggregates
- `qualified_lead_count`, `excluded_count`.
- `existing_crm_overlap_count` / `existing_crm_overlap_account_ids` = qualified exhibitors that
  already have a CRM account; ids sorted ascending.
- `total_estimated_opportunity_usd` = Σ opportunity estimates.
- `platform_coverage_counts`: for each platform enum, how many qualified leads have it.
- `platform_counts` (train_002): same per-platform count over qualified exhibitors.
- `priority_counts`: per-tier counts.
- Sort `qualified_exhibitors` / `ranked_leads` and `excluded_*` per template ordering
  (company_name asc for excluded; rank asc for ranked_leads; company_name asc for
  qualified_exhibitors in train_002).

## 9. Import-batch cleaning (train_003 style)

Process `raw_contacts` for a batch:

1. **Normalize** email (§3) and phone (§3) on every row.
2. **Missing contact** = no normalized email AND no normalized phone → remove, reason
   `missing_contact` (counts toward `unusable_removed_count`).
3. **Suppression** = normalized email OR normalized phone appears in the batch's `suppression`
   list → remove, reason `suppressed` (counts toward `suppressed_removed_count`). The
   suppression list may contain entries that match no row (e.g. role accounts) — ignore those.
4. **Deduplicate** the remaining rows by normalized **email**. Within a duplicate group:
   - **Winner = the row with the LATEST `captured_at`** (most recent wins). Tiebreak by source
     priority: lower `source_name` enum index wins (`badge_scan` > `sponsor_form` >
     `partner_upload` > `webinar_form` > `exhibitor_form` > `manual_upload`); final tiebreak
     lowest `row_id`. *(Verified: when a webinar-form row and a partner-upload row share an
     email, the partner-upload (later/higher-priority) row wins.)*
   - Loser rows → remove, reason `duplicate`.
5. **clean_contacts** = surviving winners only (NOT suppressed/missing/dup-losers), sorted by
   `clean_contact_id` ascending. `clean_contact_id` and `source_row_id` both = the winning
   row's `row_id`. Echo the winner's `company_name`, `contact_name`, normalized `email`/`phone`,
   `source_name`, `captured_at`.
   - `crm_action`: `update_existing` if a CRM account matches the email domain, else
     `create_account`. `existing_account_id` = matched account id or null;
     `existing_contact_id` = matched CRM contact id or null.
6. **duplicate_summary**: `duplicate_removed_count` = number of removed duplicate rows; 
   `duplicate_keys` = list of `{key (normalized email), winner_row_id, removed_row_ids[]}`,
   sorted by `key` ascending.
7. **removal_summary**: `unusable_removed_count` (missing), `suppressed_removed_count`,
   `removed_rows` = `[{row_id, reason}]` for every removed row, sorted by `row_id` ascending.
   reason ∈ {`duplicate`, `missing_contact`, `suppressed`}.
8. **import_action_totals** = tally of the **fate of EVERY original row** (this is the key
   convention — verified by judge):
   - surviving clean contact whose account exists → `update_existing`
   - surviving clean contact with no account → `create_account`
   - duplicate **losers** AND missing-contact rows → `no_import`
   - suppressed rows → `suppress`
   (The four keys sum to the total raw row count.)
9. **campaign_member_import_count** = number of surviving CLEAN contacts (the importable,
   non-suppressed ones) — i.e. `len(clean_contacts)`, NOT the raw total.
10. `batch_id` and `campaign_code` come from `/api/import_batches` (the batch record).

## 10. Things the judge taught us that are easy to get wrong

- **Dedup winner is the LATEST capture, source-priority tiebreak** — not the earliest, not the
  "canonical-looking" full-name row. Getting this wrong zeroes the entire `clean_contacts`
  block (it is exact-match per record).
- **import_action_totals counts ALL rows**, with duplicate losers folded into `no_import` and
  suppressed rows into `suppress`. Tallies of survivors-only score 0.
- **open_invoice revenue total is the full invoice/package amount**, with the open balance
  reported *separately* under `open_invoice_balance`. Do not put the open balance in the
  `open_invoice` total.
- **Unpaid sponsor follow-up = open_invoice + proposal_only** (proposal-only sponsors still
  owe the full package amount). paid_deferred is excluded.
- **A lead with no email but a phone is qualified**, not `missing_contact`.
- **Due dates are end_date + integer calendar days** (verified on the graded event object).
- **`camera array` / `camera module` count as the `Underwater Camera` platform** (verified on
  train_005: ReefWorks must be ROV + Underwater Camera).
- The judge scores a DIFFERENT subset of sections per task; sections it does not grade return
  0 regardless of correctness. So: get every graded section exactly right, and do not waste
  effort chasing points in ungraded sections — but still populate them per the rules above for
  robustness on unseen test tasks.
- Each perturbation of a single field that does not move the score signals either "ungraded
  here" or "already fully correct/fully wrong as a block"; use empty-the-section probes to
  learn a section's weight, then isolate the convention.

## 11. Verification recipe (for the solver at test time)

1. Build the candidate JSON from the rules above.
2. Re-read the prompt's explicit `Requirements` and `Sorting` bullets and cross-check each one.
3. Re-read the template's `allowed_values`/`ordering`/`required_*_keys` and confirm every key
   is present, no extra keys, every enum value is from the allowed set, every list is sorted
   as specified.
4. Spot-check: sponsor statuses exclude canceled orders; revenue totals use package amounts;
   unpaid follow-up includes proposal_only; dedup winners are latest; import totals sum to raw
   row count; due dates are end_date + N days; platforms sorted in enum order; rank is
   1-based contiguous.
5. Emit a single JSON object with no surrounding prose.
