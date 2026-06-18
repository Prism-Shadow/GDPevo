---
name: harborcrm-front-of-funnel
description: >-
  Solve HarborCRM front-of-funnel CRM/marketing tasks against the read-only
  HarborCRM JSON API: post-event sponsor reconciliation and CRM handoff,
  trade-show exhibitor prospecting/qualification, raw contact-import hygiene
  (dedupe/suppress/normalize), sponsor/lead follow-up planning, and CRM
  create/update/no-action decisions. Use whenever a task references HarborCRM,
  an event_id (sponsor orders/badges/invoices), a trade-show show_id
  (exhibitors/meeting_interest), or an import batch of raw contacts, and asks
  for a structured JSON answer matching an answer_template.
---

# HarborCRM Front-of-Funnel Solver

HarborCRM is a read-only JSON CRM/marketing workspace. Tasks ask you to read
shared domain records over HTTP, apply business rules, and emit ONE JSON object
that conforms exactly to a supplied `answer_template.json`. There are no
answer endpoints — you must compute everything yourself.

## Golden rules (apply to every task)

1. **The answer template is law.** Read `input/payloads/answer_template.json`
   first. Emit exactly the declared top-level keys and item keys, use only the
   declared enum values, respect the declared ordering, and add NO extra fields.
   Output JSON only — no prose, no markdown fences.
2. **Enum vocabularies vary per task.** Do not assume enums carry across tasks.
   Example: a "sensor vendor" exclusion is `sensor_vendor_only` in one task and
   `sensor_only` in another. Always copy enum spellings from the active template.
3. **Currency is integer USD.** Never emit floats for money/counts.
4. **Sort exactly as specified** (usually `account_name`/`company_name`
   ascending; ranked lists by computed rank). When two sort keys are given,
   apply them in order.
5. **Derive, don't guess.** Every classification traces to a concrete field
   (order_status, invoice status, account.status/disqualified_reason,
   badge_type, exhibitor description text, suppression list, captured_at).

## API access

Base URL is supplied by the runner (e.g. `http://127.0.0.1:8080` or `:8067`);
read it from the task's environment/prompt. All responses are JSON. Use `curl`.

Endpoints (all GET):
- `/health` — record counts/sanity check.
- `/api/policies` — controlled enums + notes (status_enums, platform_enums).
- `/api/events`, `/api/events/{event_id}` — dates, `lead_opportunity_amount`,
  `followup_days_after_end`, `sponsor_followup_days_after_end`, `campaign_code`.
- `/api/events/{event_id}/orders` and `/sponsor_packages` — sponsor orders
  (`account_id`, `amount`, `order_status`, `package_level`, `ticket_contacts`).
- `/api/events/{event_id}/badges` — badge scans (`badge_id`, `badge_type`,
  `company_name`, `contact_name`, `email`, `phone`, ...).
- `/api/finance/invoices?event_id=` (or `account_id=`) — `status`, `amount`,
  `paid_amount`, `deferred_amount`.
- `/api/crm/accounts` (`?status=`, `?owner_region=`) — `account_id`, `name`,
  `domain`, `status`, `disqualified_reason`.
- `/api/crm/contacts` (`?account_id=`) — `contact_id`, `email`, `phone`,
  `opted_out`, `account_id`.
- `/api/crm/opportunities` (`?event_id=`, `?account_id=`).
- `/api/crm/campaign_members?event_id=` (or `account_id=`) — `account_id`,
  `contact_id`, `status`.
- `/api/tradeshows`, `/api/tradeshows/{show_id}/exhibitors`,
  `/api/tradeshows/{show_id}/meeting_interest`.
- `/api/import_batches`, `/api/import_batches/{batch_id}/raw_contacts`,
  `/api/import_batches/{batch_id}/suppression`.

Always fetch the full data you need up front; join records by `account_id`,
`company_name`, `email` domain, and `contact_name`.

## Normalization rules (used everywhere contacts appear)

- **Email**: trim whitespace, lowercase. If empty/whitespace-only after trim,
  emit `""`. (e.g. `" Dana.Ruiz@HelioWare.example "` -> `dana.ruiz@helioware.example`.)
- **Phone**: strip ALL non-digit characters; keep the remaining digits exactly
  as they appear. Do NOT add or remove a leading country code. So
  `"415-555-0188"` -> `4155550188`, `"+1 415 555 0188"` -> `14155550188`,
  `"+1 (512) 555-0121"` -> `15125550121`, `"212-555-0166"` -> `2125550166`.
  Empty -> `""`.
- A contact is **usable** only if it has a non-empty normalized email OR a
  non-empty normalized phone. Neither present -> `missing_contact`.

## Workflow A — Post-event sponsor reconciliation & CRM handoff

(events with orders/invoices/badges; e.g. "reconcile", "post-event handoff")

### A1. Sponsor status (enum: paid_deferred / open_invoice / proposal_only / not_sponsor)
For each sponsor **order** on the event, classify by joining order_status +
finance invoice:
- `order_status == "canceled"` -> NOT an active sponsor. Drop from the active
  sponsor list. If a person from that account shows up via a badge, they are
  handled in the lead/exclusion path (usually `existing_disqualified` because
  such accounts are typically `disqualified` in CRM).
- `order_status == "proposal_sent"` and no invoice -> `proposal_only`.
- Has an invoice:
  - invoice `status == "paid_deferred"` (paid_amount == amount) -> `paid_deferred`.
  - invoice `status == "open"` (paid_amount < amount) -> `open_invoice`;
    `open_balance = amount - paid_amount`.
- `not_sponsor` (when the template includes it) = a CRM account that is not a
  sponsor at all but is being listed for completeness.
- `amount`/`package_amount` = the order/package `amount` (full package value),
  regardless of how much is paid.

### A2. Sponsor revenue rollups
Sum `amount` per status into integer USD. For open invoices, also report the
open balance separately (`open_invoice_balance` = sum of `amount - paid_amount`).

### A3. Badge classification -> lead qualification & exclusions
Walk every badge AND every sponsor `ticket_contacts` person:
- **Sponsor people** (sponsor badge, or named in an active sponsor order's
  `ticket_contacts`) -> classification `sponsor_attendee`. They are excluded
  from the qualified-lead list. Exclusion reason `sponsor_attendee`.
- **Non-business badges** (`badge_type` in {student, press, ...} i.e. not
  attendee/sponsor; academic/press/media companies) -> excluded
  `non_business_badge`.
- **Account already disqualified** (CRM account `status == "disqualified"`,
  any `disqualified_reason`) -> excluded `existing_disqualified`.
- **Canceled-sponsor-account attendees** -> usually `existing_disqualified`
  (the CRM account is disqualified). Only use an `inactive_sponsor_record`
  reason if that exact enum is in the template AND the account is not otherwise
  disqualified.
- **Missing contact info** (no usable email/phone) -> `missing_contact`
  (only if the template has this reason).
- Everything else = **qualified non-sponsor lead**.

### A4. CRM create/update/no-action for qualified leads
Resolve against existing CRM:
- **Account match** = CRM account whose `domain` matches the lead's email
  domain (or an obvious name match). Match -> `update_existing`; no match ->
  `create_account`.
- **Contact match** = CRM contact whose normalized `email` equals the lead's
  normalized email (scope to the matched account). Match -> contact already
  exists (`update_existing`/`no_action`); no match -> `create_contact`.
  Note: an account can exist while the specific person does not (e.g. only an
  unrelated/opted-out contact is on file) -> `update_existing` account +
  `create_contact`.
- **Campaign member**: if the lead is not already a campaign member for the
  event -> `add_campaign_member` / `create`. If a sponsor person already has a
  campaign member with the right status -> `no_action`. If the member exists
  but status is stale relative to the target -> `update`.
- **Sponsor attendees who lack a CRM contact/campaign member** still get
  `create_contact` + `add_campaign_member` (the account already exists) — being
  a sponsor attendee excludes them from the *lead pipeline*, not from CRM hygiene.

### A5. Campaign-member target_status (when required)
- Sponsor attendee who physically attended -> `attended_sponsor`.
- Sponsor who only registered (no badge/attendance) -> `registered_sponsor`
  (leave existing status as-is -> `no_action`).
- Qualified non-sponsor lead with a badge (attended) -> `attended`.
- Excluded -> `excluded` / `no_import`.

### A6. Opportunity totals
- Each qualified non-sponsor lead is sized at the event's
  `lead_opportunity_amount` (same value for every lead).
- `lead_pipeline_total` / `open_opportunity_total_usd` = lead_opportunity_amount
  x (number of qualified leads). `open_opportunity_count` = number of qualified
  leads. Do NOT include pre-existing sponsor CRM opportunities here.

### A7. Follow-up due dates & task counts
- `lead_followup_due_date` = event `end_date` + `followup_days_after_end` days.
- `sponsor_followup_due_date` = event `end_date` + `sponsor_followup_days_after_end` days.
- Add calendar days to `end_date` (e.g. end 2026-09-16 + 7 -> 2026-09-23; + 3 -> 2026-09-19). Format `YYYY-MM-DD`.
- `lead_task_count` = number of qualified leads needing follow-up.
- **Unpaid sponsors / sponsor finance follow-up** = sponsors NOT fully paid =
  `open_invoice` accounts PLUS `proposal_only` accounts (everything except
  `paid_deferred`). `sponsor_finance_task_count` = count of those accounts;
  `unpaid_sponsor_total_usd` = sum of their package `amount`s.

### A8. CRM action counts
Aggregate the per-lead/per-badge decisions: count `create_account` vs
`update_existing`, `create_contact` vs `update`, `campaign_members_create` vs
`update`. Sponsor accounts that already exist contribute `accounts_update=0`
unless a decision row explicitly updates them.

## Workflow B — Trade-show exhibitor prospecting / qualification

(show_id + exhibitors + meeting_interest; "qualified leads", "prospecting")

### B1. Qualification = does the exhibitor BUILD/OEM a target platform?
Read each exhibitor `description`. Platform enums are typically
`AUV`, `ROV`, `Underwater Camera` (confirm via `/api/policies` and template).
- **Qualified** if the company *manufactures / builds / designs / OEM-integrates*
  one or more target platforms. Assign every platform it builds, sorted in the
  template's enum order (AUV, ROV, Underwater Camera).
  - "Builds compact AUVs and inspection ROVs" -> [AUV, ROV].
  - "Designs underwater camera modules" / "OEM underwater camera manufacturer"
    -> [Underwater Camera].
  - "Manufactures ROVs with camera arrays" -> [ROV, Underwater Camera].
- **Excluded near-misses** — adjacent but not a platform maker:
  - Distributor / reseller / sales agent (sells others' platforms, does not
    manufacture) -> `distributor` / `distributor_only`.
  - Service / consulting / operates rented platforms -> `service_provider` /
    `service_only`.
  - Sensor-only vendor (probes/sensors integrated by others) ->
    `sensor_vendor`/`sensor_vendor_only` or `sensor_only` (use template spelling).
  - Research / academic only -> `research` / `research_only`.
  - Not the target market -> `not_target_market`.
  Use the exact `relationship_type` and `exclusion_reason` enums from the
  template; their spellings differ across tasks.

### B2. CRM overlap & action
- Exhibitor `crm_account_id` non-null (already in CRM) -> `update_existing`;
  qualified but `crm_account_id == null` -> `create_account`.
- Excluded exhibitors -> `no_import`.
- `existing_crm_overlap_*` = the qualified leads whose `crm_account_id` is set;
  report count and sorted list of those account IDs.

### B3. Priority tier & opportunity sizing
Join `meeting_interest` by `company_name` (`requested_demo`, `interest_score`).
Standard tier rule (use the prompt's amounts):
- **A**: `requested_demo == true` AND `interest_score >= 90`.
- **B**: `requested_demo == true` AND `interest_score >= 80` (and not A).
- **C**: everything else qualified (no demo, or lower score).
Opportunity amount per tier comes from the prompt (e.g. A=120000, B=90000,
C=50000). `total_estimated_opportunity_usd` = sum over qualified leads.

### B4. Ranking (when a ranked list is required)
Sort qualified leads by, in order:
1. `requested_demo` (true before false),
2. `interest_score` descending,
3. broader platform coverage (more platforms first),
4. `company_name` ascending.
Assign 1-based contiguous `rank`. Non-ranked lists sort by `company_name` asc.

### B5. Aggregate counts
- `qualified_total` / `qualified_lead_count`, `excluded_..._total`.
- `platform_counts` / `platform_coverage_counts`: count how many qualified
  leads include each platform (a company counts once per platform it builds).
- `priority_counts`: count qualified leads per tier (include zero-count tiers).

## Workflow C — Raw contact-import hygiene

(import batch + raw_contacts + suppression; "prepare batch for CRM import")

Process each raw row through this pipeline, in this order:

1. **Normalize** email and phone (rules above). Capture `source_name`,
   `captured_at`, `company_name`, `contact_name`.
2. **Missing contact**: if normalized email AND phone are both empty ->
   removed, reason `missing_contact` (counts toward `unusable_removed_count`
   and `no_import`).
3. **Suppression**: the suppression list is GLOBAL (applies across batches).
   A row is `suppressed` if its normalized email matches a suppression `email`
   (or its normalized phone matches a suppression `phone`). Removed, reason
   `suppressed` (counts toward `suppressed_removed_count` and `suppress`).
   Note: a CRM contact being `opted_out` does not by itself suppress an import
   row unless that email/phone is on the suppression list.
4. **Deduplicate** survivors by key. Primary key = `email:<normalized_email>`
   (fall back to `phone:<normalized_phone>` when email is empty). Within a
   duplicate group:
   - **Winner = latest `captured_at`.**
   - **Tie-break (equal `captured_at`)**: prefer the higher-trust source.
     Observed precedence puts `partner_upload` above `webinar_form`; in general
     prefer the more authoritative/enriched source. The winner keeps ITS own
     normalized fields (e.g. its phone).
   - Losers -> removed, reason `duplicate` (counts toward `no_import`).
   - Record `{key, winner_row_id, removed_row_ids}` in `duplicate_keys`.
5. **CRM action** for each surviving (winner) row:
   - Account match by email **domain** vs CRM account `domain` -> if match,
     `update_existing` with `existing_account_id`; else `create_account` with
     `existing_account_id = null`.
   - Contact match by normalized email vs CRM contact `email` ->
     `existing_contact_id` if found, else `null`. (An existing account with no
     matching contact still yields `update_existing` + `existing_contact_id null`.)
   - `clean_contact_id` and `source_row_id` = the WINNING row's `row_id`.
6. **Counts**:
   - `import_action_totals`: count surviving rows by `crm_action`
     (`create_account`, `update_existing`), then `no_import` = duplicate-removed
     + missing_contact removed, and `suppress` = suppressed removed.
     (`no_import` and `suppress` count REMOVED rows, not survivors.)
   - `duplicate_removed_count` = number of duplicate losers.
   - `unusable_removed_count` = missing_contact removals only.
   - `suppressed_removed_count` = suppressed removals.
   - `removed_rows` = every removed row `{row_id, reason}`, reason in
     {duplicate, missing_contact, suppressed}.
   - `campaign_member_import_count` = number of surviving clean contacts
     (they all become members of the batch campaign).
   - `campaign_code` = the batch's `campaign_code`.

## Common misjudgments to avoid

- Emitting money/counts as floats, or omitting zero-count enum buckets.
- Adding a leading `1` to phones (only strip non-digits; never fabricate digits).
- Counting `paid_deferred` sponsors as needing finance follow-up — only
  open_invoice + proposal_only are "unpaid".
- Treating canceled sponsor orders as active sponsors.
- Putting pre-existing sponsor opportunities into the lead pipeline total
  (lead total is `count_of_qualified_leads x event.lead_opportunity_amount`).
- Listing sponsor attendees as qualified leads (they are excluded from leads),
  while forgetting they may still need a CRM contact/campaign-member create.
- Qualifying distributors/resellers/service operators/sensor-only vendors as
  platform makers in prospecting (they are near-miss exclusions).
- Using suppression that doesn't match, or letting a CRM `opted_out` flag
  suppress an import row (suppression list is the authority for imports).
- Wrong dedup winner: winner is the LATEST captured_at; only break ties by
  source precedence.
- Reusing enum spellings across tasks instead of copying from the active
  template (`sensor_vendor_only` vs `sensor_only`, etc.).

## Final checklist before returning

1. Output is a single JSON object with exactly the template's top-level keys.
2. All enums are valid per the active template.
3. Lists are sorted as specified; ranks are 1-based and contiguous.
4. Money/counts are integers; dates are `YYYY-MM-DD`.
5. No fields beyond the template; no prose outside the JSON.
