---
name: harborcrm-front-of-funnel
description: End-to-end SOP for HarborCRM front-of-funnel CRM marketing tasks — post-event sponsor/lead handoff reconciliation, trade-show OEM/robotics prospecting with ranking & tiering, and raw contact-import hygiene — producing strict JSON that matches the per-task answer_template.
---

# HarborCRM Front-of-Funnel Solver

You produce one JSON object that conforms EXACTLY to the task's `answer_template.json`
(`input/payloads/answer_template.json`). No prose outside the JSON. Do not add or drop
keys. Match every enum value verbatim. Sort every list exactly as the template's
`ordering`/sorting rules say. Integers for all USD and counts (no decimals, no strings).

## Environment
- HTTP-only data API. Use `curl` (or python urllib/requests). Never use a tool that forces HTTPS.
- Base URL is supplied by the runner (e.g. `http://<host>:<port>`). All endpoints below are
  relative to it. Always `GET /api/policies` first; it carries the controlled enums
  (`status_enums`, `platform_enums`) even though most decision logic lives in the record data.
- Read-only endpoints:
  `/health`, `/api/policies`, `/api/events`, `/api/events/{id}`, `/api/events/{id}/orders`,
  `/api/events/{id}/badges`, `/api/events/{id}/sponsor_packages`,
  `/api/finance/invoices?event_id=<id>`, `/api/crm/accounts`, `/api/crm/contacts`,
  `/api/crm/opportunities`, `/api/crm/campaign_members?event_id=<id>`, `/api/tradeshows`,
  `/api/tradeshows/{show}/exhibitors`, `/api/tradeshows/{show}/meeting_interest`,
  `/api/import_batches`, `/api/import_batches/{batch}/raw_contacts`,
  `/api/import_batches/{batch}/suppression`.

## Universal normalization rules (apply everywhere a normalized value is requested)
- **Email**: trim leading/trailing whitespace, then lowercase the whole string. A value that
  is empty or only whitespace normalizes to `""` (empty string), never null.
- **Phone**: keep digits only (strip `+`, spaces, `()`, `-`, `.`). Do NOT strip a leading `1`
  — keep every digit the source supplied. So `+1 415 555 0188` -> `14155550188`, but
  `415-555-0188` -> `4155550188`. Empty/absent phone -> `""`.
- A contact is "contactable" if it has a non-empty normalized email OR a non-empty normalized
  phone. A row/badge with neither is a `missing_contact` exclusion.

## Universal date arithmetic
- `lead_followup_due_date` / lead follow-up = event `end_date` + `followup_days_after_end` days.
- `sponsor_followup_due_date` / sponsor finance follow-up = event `end_date` +
  `sponsor_followup_days_after_end` days.
- Add calendar days to `end_date` (YYYY-MM-DD), output `YYYY-MM-DD`. Use end_date, not start_date.

---

# TASK FAMILY A — Post-event sponsor/lead handoff reconciliation
(e.g. `neuralops_2026`, `edgeai_field_2026`)

Endpoints to combine: `/api/events/{id}` (dates, lead_opportunity_amount, *_days_after_end),
`/api/events/{id}/orders` (= sponsor_packages; sponsor order_status + amount + ticket_contacts),
`/api/finance/invoices?event_id=` (paid/deferred/open per sponsor),
`/api/events/{id}/badges` (attendees/leads), `/api/crm/accounts` (status, disqualified_reason),
`/api/crm/contacts`, `/api/crm/opportunities`, `/api/crm/campaign_members?event_id=`.

## A1. Sponsor status (controlled enum: paid_deferred | open_invoice | proposal_only | not_sponsor)
For each sponsor ORDER, decide status by combining order_status + invoice status:
- order_status `canceled` -> NOT an active sponsor. Exclude it from `sponsor_statuses`
  entirely, and exclude its ticket contact from leads (reason `inactive_sponsor_record`).
- order_status `proposal_sent` and NO invoice -> `proposal_only` (invoice_id null, paid 0,
  open_balance 0; package_amount = order amount).
- order_status `confirmed` WITH an invoice:
  - invoice.status `paid_deferred` (paid_amount == amount) -> `paid_deferred`
    (open_balance = 0).
  - invoice.status `open` -> `open_invoice`, paid_amount = invoice.paid_amount,
    **open_balance = invoice.amount − invoice.paid_amount** (NOT amount−paid−deferred).
- `package_amount` = the sponsor order/invoice amount (integer USD).
- Sort `sponsor_statuses` by `account_name` ascending.

## A2. Sponsor revenue totals (when the template asks)
- `paid_deferred` = sum of package amounts of paid_deferred sponsors.
- `open_invoice` = sum of package amounts of open_invoice sponsors (the FULL package amount,
  not the open balance).
- `proposal_only` = sum of package amounts of proposal_only sponsors.
- `open_invoice_balance` = sum of open balances of open_invoice sponsors (amount − paid).

## A3. Sponsor finance follow-up  (LESSON — do X not Y)
- Finance follow-up targets = **all active sponsors that are NOT fully paid**, i.e.
  `open_invoice` AND `proposal_only`. Do NOT restrict it to open_invoice only.
- `paid_deferred` sponsors are settled -> never in finance follow-up.
- `sponsor_finance_task_count` = number of those accounts; list their account_names
  (`sponsor_finance_accounts` / `unpaid_sponsor_account_names`) sorted ascending.
- `unpaid_sponsor_total_usd` = sum of their package amounts (open_invoice amount +
  proposal_only amount), integer USD.
- Due date = sponsor finance follow-up date (see date arithmetic).

## A4. Qualified non-sponsor leads from badges
Walk badges. A badge becomes a qualified non-sponsor lead only if ALL hold:
- badge_type is a business attendee type (`attendee`). EXCLUDE non-business badges:
  `student`, `press`, and similar -> exclusion reason `non_business_badge`.
- The company is NOT an active sponsor and the contact is NOT a sponsor ticket_contact
  (those are `sponsor_attendee`).
- The matching CRM account is NOT disqualified. A CRM account with status `disqualified`
  / non-null `disqualified_reason` -> exclude reason `existing_disqualified`.
- The badge is contactable (has email or phone); otherwise `missing_contact`.
- Exclusion-reason precedence for a badge that hits several rules: sponsor_attendee >
  inactive_sponsor_record > non_business_badge > existing_disqualified > missing_contact.
  (A canceled-sponsor ticket contact whose CRM account is also disqualified is reported as
  `inactive_sponsor_record` — the more specific sponsor-side reason.)

For each qualified lead:
- `opportunity_amount` / lead opp = the EVENT's `lead_opportunity_amount` (same for every lead).
- `account_id`: existing CRM account_id if the company already exists in CRM, else null.
- `crm_account_action`: `update_existing` if the account already exists, else `create_account`.
- `crm_contact_action`: `create_contact` when the badge person is a new contact (a different
  existing contact at that account, or an opted-out/suppressed existing contact, does NOT make
  the new badge person an update). Use `update_existing` only when that exact contact already
  exists and is being refreshed.
- `campaign_member_action`: `add_campaign_member` for a brand-new event member.
- `lead_pipeline_total` = (#qualified leads) × lead_opportunity_amount.

## A5. CRM action counts (the work implied by the handoff)
Count only the lead/handoff work:
- `accounts_create` = new accounts among qualified leads; `accounts_update` = existing accounts.
- `contacts_create` = new badge contacts; `contacts_update` = refreshed existing contacts.
- `campaign_members_create` = new event members added for qualified leads;
  `campaign_members_update` = existing members whose status is being changed.

## A6. Badge decisions / campaign member actions (richer reconciliation variant, e.g. edgeai)
`badge_decisions` (sort by `badge_id`): each badge -> {classification, crm_action, exclusion_reason}.
- classification enum: `sponsor_attendee` | `qualified_non_sponsor_lead` | `excluded`.
- A sponsor ticket-contact badge -> classification `sponsor_attendee`, exclusion_reason
  `sponsor_attendee`. If that sponsor member already exists and is already correct in the
  campaign -> crm_action `no_action` (keep badge crm_action consistent with the campaign-member
  action for the same person; do not say update when nothing changes).
- A new business attendee -> `qualified_non_sponsor_lead`. crm_action:
  `create_account_contact_campaign_member` when the account is brand new;
  `create_contact_campaign_member` when the account exists but the contact is new;
  `add_campaign_member` when account+contact exist but no member yet.
- non-business badge -> classification `excluded`, crm_action `no_import`,
  exclusion_reason `non_business_badge`. exclusion_reason is `null` for qualified leads.

`campaign_member_actions` (sort by `subject_key`):
- `subject_key` is an account/CRM-style key (e.g. the `account_id`), NOT the contact name.
  (Using contact names here scored worse.)
- action enum: `create` | `update` | `no_action` | `no_import`.
  target_status enum: `attended_sponsor` | `registered_sponsor` | `attended` | `excluded`.
- Existing member already at the right status -> `no_action` keeping its current target_status
  (attended_sponsor / registered_sponsor). A sponsor with no attendance badge stays
  `registered_sponsor`.
- New qualified non-sponsor lead -> `create`, target_status `attended`.

`opportunity_summary`:
- `qualified_non_sponsor_account_names` = sorted account names of qualified non-sponsor leads.
- `lead_opportunity_amount_usd` = event lead_opportunity_amount.
- `open_opportunity_total_usd` / `open_opportunity_count` = the NEW lead opportunities created
  for qualified non-sponsor leads: count = #qualified-non-sponsor leads, total = count ×
  lead_opportunity_amount. (Confirmed: this beat using existing CRM open-stage opps = 0.)

`badge_only_contacts` (sort by `company_name`): one row per qualified non-sponsor (badge-only)
lead with normalized_email / normalized_phone per the universal normalization rules.

`exclusion_counts`: integer tally per reason key (`sponsor_attendee`, `non_business_badge`,
`existing_disqualified`, `missing_contact`). Count each excluded badge once under its reason.

NOTE / residual uncertainty (Family A): the handling of a *proposal-only* sponsor's attending
ticket contact (sponsor_attendee vs lead) and the exact target_status for that person were the
hardest calls and may need re-derivation per task; default to treating any sponsor ticket-contact
(even proposal_only) as `sponsor_attendee`.

---

# TASK FAMILY B — Trade-show OEM / robotics prospecting (FULLY VALIDATED, score 1.0)
(e.g. `marinesense_2026` dissolved-oxygen sensor, `aquafarm_robotics_2026` aquaculture robotics)

Endpoints: `/api/tradeshows/{show}/exhibitors` (company_id, name, booth, country, website,
description, crm_account_id), `/api/tradeshows/{show}/meeting_interest`
(interest_score, requested_demo, by company_name), `/api/crm/accounts`, `/api/policies`.

## B1. Platform classification (enum order ALWAYS: AUV, ROV, Underwater Camera)
Read the exhibitor `description` and assign every target platform the company **makes / OEM-builds**:
- "AUV" / "autonomous underwater vehicle" / "AUV scout" -> AUV.
- "ROV" / "remotely operated" / pen-cleaning/inspection ROV builder -> ROV.
- "underwater camera" / "camera module/array" maker -> Underwater Camera.
- A company can have multiple platforms (e.g. ROVs WITH camera arrays -> [ROV, Underwater Camera]).
- Always emit the platforms list sorted in enum order AUV, ROV, Underwater Camera.

## B2. Qualify vs exclude (a company must MANUFACTURE/OEM-BUILD a target platform)
Exclude near-misses and give a controlled reason. Two reason vocabularies appear; pick the one
in THIS task's template:
- distributor / reseller / sales agent / "does not manufacture" ->
  reason `distributor_only`; relationship_type `distributor`.
- consulting / operates-rented / service team -> reason `service_only`;
  relationship_type `service_provider`.
- sensor-/probe-only vendor (sells sensors for others to integrate, no platform) ->
  reason `sensor_vendor_only` (marinesense vocab) or `sensor_only` (aquafarm vocab);
  relationship_type `sensor_vendor`.
- research-only org -> `research_only` / relationship_type `research`.
- analytics/software-only "dashboard, no hardware manufacturing" -> treat as service ->
  `service_only` / `service_provider`.
- excluded exhibitors always get crm_action `no_import` and stay visible in the exclusion list.
- Sort exclusion list by `company_name` ascending.

## B3. CRM action for qualified exhibitors
- If exhibitor `crm_account_id` is non-null (already in CRM) -> crm_action `update_existing`,
  carry that crm_account_id.
- Else -> crm_action `create_account`, crm_account_id null.
- `existing_crm_overlap_*` = qualified leads whose crm_account_id is non-null: count + the
  account_ids sorted ascending.

## B4. Priority tier + opportunity sizing (demo + interest_score)
- Tier A = requested_demo true AND interest_score >= 90  -> USD 120000.
- Tier B = requested_demo true AND interest_score >= 80  -> USD 90000.
- Tier C = everything else (no demo, or demo with score < 80) -> USD 50000.
- (For marinesense, the same A/B/C demo+score thresholds applied; tier A=demo&>=90, B=demo&>=80.)
- `total_estimated_opportunity_usd` = sum of opportunity_estimate over qualified leads.
- A company with no meeting_interest record = no demo, treat interest_score per template
  (if a score field is required and none exists, it is not demo-requested -> tier C).

## B5. Ranking (when `rank` is required, e.g. aquafarm)
Sort qualified leads by, in order:
1. requested_demo DESC (demo-requested first),
2. interest_score DESC,
3. broader platform coverage first (more platforms first),
4. company_name ascending.
Then assign 1-based contiguous `rank`. (When no rank field, just sort by company_name ascending.)

## B6. Aggregate counts
- `qualified_total` / `qualified_lead_count`, `excluded_*_total` / `excluded_count` = list lengths.
- `platform_counts` / `platform_coverage_counts` = per-platform count of qualified leads whose
  platforms include that enum (a 2-platform company increments two buckets). Keys AUV, ROV,
  Underwater Camera, integer values.
- `priority_counts` = count of qualified leads per tier A/B/C.

---

# TASK FAMILY C — Raw contact-import hygiene
(e.g. `fall_webinar_import`)

Endpoints: `/api/import_batches` (campaign_code), `/api/import_batches/{batch}/raw_contacts`,
`/api/import_batches/{batch}/suppression`, `/api/crm/accounts`, `/api/crm/contacts`, `/api/policies`.

## C1. Per-row pipeline (apply in this order)
1. Normalize email + phone for every raw row (universal rules above).
2. **Suppression**: a row whose normalized email OR normalized phone matches any suppression
   entry is suppressed (reason `suppressed`). Suppression matches on email and on phone
   independently.
3. **Missing contact**: a row with neither a usable email nor phone after normalization is
   unusable (reason `missing_contact`).
4. **Deduplicate** the remaining rows. Dedup KEY = normalized email (the two HelioWare rows
   with different company spellings still collide because email matches; the two Quartz rows
   collide on identical email). Within a duplicate group, choose ONE winner; the others are
   removed with reason `duplicate`. For the duplicate-key entries report
   {key, winner_row_id, removed_row_ids}. Sort duplicate_keys by `key` ascending.
   - Tie-break when timestamps are equal: lowest `row_id` wins.
   - Winner selection by `captured_at` was ambiguous in training (latest-wins and earliest-wins
     both scored the same low number) — see the warning below; pick a single deterministic rule
     (recommend: most-recent `captured_at`, tie -> lowest row_id) and apply it consistently.

## C2. CRM action per surviving contact (enum: create_account | update_existing | no_import | suppress)
- Account already exists in CRM (match by email domain to an `/api/crm/accounts` domain) ->
  `update_existing`, set existing_account_id (and existing_contact_id if that exact contact
  exists, else null).
- New company -> `create_account`, existing ids null.
- A missing-contact row -> `no_import`; a suppressed row -> `suppress`.
- `clean_contact_id` and `source_row_id` = the winning source row_id. `captured_at`,
  `source_name`, company_name, contact_name come from the WINNING row.
- `source_name` enum: badge_scan, sponsor_form, partner_upload, webinar_form, exhibitor_form,
  manual_upload.
- Sort `clean_contacts` by `clean_contact_id` ascending.

## C3. Summaries
- `duplicate_summary.duplicate_removed_count` = number of rows removed as duplicates (losers).
- `removal_summary`: `unusable_removed_count` (missing_contact rows),
  `suppressed_removed_count` (suppressed rows), and `removed_rows` = every removed row as
  {row_id, reason} with reason in {duplicate, missing_contact, suppressed}, sorted by row_id asc.
- `import_action_totals` = integer tally over the per-row crm_action dispositions
  (create_account, update_existing, no_import, suppress).
- `campaign_member_import_count` = number of importable cleaned contacts (the create_account +
  update_existing survivors) to add as members of the batch campaign.

## C4. WARNING — unresolved membership shape (Family C)
Training could not fully pin down the exact `clean_contacts` membership/field expectations for
this family within the available feedback (multiple plausible models scored identically low).
Two candidate models exist and you must decide per the template wording:
  (a) `clean_contacts` = only the importable survivors (create_account + update_existing);
      suppressed/missing rows live ONLY in `removal_summary`.
  (b) `clean_contacts` = every deduplicated survivor INCLUDING suppressed (`suppress`) and
      missing-contact (`no_import`) rows, each carrying its crm_action; those rows ALSO appear
      in removal_summary.
The crm_action enum containing `suppress` and `no_import` hints toward model (b); but verify
against the template's field_types/descriptions for the specific task and keep
`import_action_totals` consistent with whichever membership you choose. Do NOT assume either
blindly — re-read the template's `clean_contacts.field_types` and `campaign_member_import_count`
description and let them decide.

---

# Cross-cutting output discipline (mistakes the feedback punished — do X, not Y)
- DO include open_invoice AND proposal_only sponsors in finance follow-up; do NOT limit to open_invoice.
- DO compute open_balance as invoice.amount − paid_amount; do NOT subtract deferred_amount again.
- DO set open_invoice revenue total to the full package amount; the open money goes in the
  separate `open_invoice_balance` field only.
- DO use lead opportunities (count × lead_opportunity_amount) for `open_opportunity_total/count`;
  do NOT report existing CRM open-stage opps (which were 0) for that field.
- DO use account-id-style `subject_key` in campaign_member_actions; do NOT use contact names.
- DO keep a badge's crm_action consistent with that person's campaign-member action (no_action
  when nothing changes); do NOT mark `update` when the member is already correct.
- DO keep every digit when normalizing phones (including a leading country `1`).
- DO treat a new badge person at an account whose only existing contact is opted-out/suppressed
  as `create_contact`, not update.
- DO sort exactly as the template states, emit integers, and never add undeclared fields.
