---
name: harborcrm-front-of-funnel-handoff
description: SOP for HarborCRM front-of-funnel CRM tasks — event sponsor handoff/reconciliation, trade-show prospecting qualification & ranking, and raw-contact import hygiene — driven entirely from the read-only HarborCRM data API.
---

# HarborCRM Front-of-Funnel Handoff — Executable SOP

This skill covers four recurring task families in the HarborCRM domain. All of them are
solved by fetching shared, read-only records from the HarborCRM API and reconciling them
into a single JSON object that matches the task's `answer_template.json`. There are NO
answer endpoints and no judge — you derive every value yourself from the data + the rules
below.

## 0. General rules (apply to every task)

1. **Read the template first.** The `answer_template.json` is authoritative for: the exact
   top-level keys, every field name, every controlled enum value, and the sorting rules.
   Emit ONLY the declared keys/shape. Some templates are literal answer skeletons (train_001
   style — copy the shape and fill it); others are *schema descriptors* (list
   `required_top_level_keys`, `field_definitions`, enums). In the descriptor case, build a
   plain JSON object whose keys/types match the spec — do NOT echo the descriptor metadata
   (no `field_definitions`, `required_value`, etc. in your output).
2. **Always GET `/api/policies` first.** It supplies the controlled enums:
   - sponsor `status_enums`: `paid_deferred`, `open_invoice`, `proposal_only`, `not_sponsor`
   - prospecting `platform_enums`: `AUV`, `ROV`, `Underwater Camera`
3. **API access:** HTTP only (`http://<host>`); use `curl`/`urllib`, never WebFetch (it forces
   HTTPS). Base URL is supplied by the runner / `environment_access.md`.
4. **Output discipline:** Return one JSON object, no prose. Integers for all USD amounts and
   all counts (no decimals, no currency symbols). Respect every "Sort by X ascending" rule.
   When a list value is required but empty, emit `[]`; when a scalar id is absent emit `null`
   (or `""` only where the template explicitly says empty string is allowed).
5. **Normalization (used everywhere a contact appears):**
   - email → `trim()` then `lowercase()`. If blank/whitespace → empty string `""`.
   - phone → keep digits only (strip `+ ( ) - . spaces`). If blank → `""`.
   - Do not invent a country code; keep exactly the digits present (e.g. `415-555-0188` →
     `4155550188`; `+1 415 555 0188` → `14155550188` — these can legitimately differ).

## API endpoint map (which calls serve which sub-goal)

- Event facts / dates / amounts: `GET /api/events/{event_id}` (fields: `start_date`,
  `end_date`, `followup_days_after_end`, `sponsor_followup_days_after_end`,
  `lead_opportunity_amount`, `campaign_code`).
- Sponsor orders / packages: `GET /api/events/{id}/orders` and
  `GET /api/events/{id}/sponsor_packages` (these mirror each other; `order_status` ∈
  `confirmed | proposal_sent | canceled`, plus `amount`, `package_level`, `ticket_contacts`).
- Attendance: `GET /api/events/{id}/badges` (`badge_type`, `company_name`, `contact_name`,
  `email`, `phone`, `scan_score`).
- Finance: `GET /api/finance/invoices?event_id={id}` (`status` ∈ `paid_deferred | open | ...`,
  `amount`, `paid_amount`, `deferred_amount`, `invoice_id`).
- CRM state: `GET /api/crm/accounts` (`account_id`, `name`, `domain`, `status`,
  `disqualified_reason`), `GET /api/crm/contacts` (`account_id`, `name`, `email`, `phone`,
  `opted_out`), `GET /api/crm/opportunities`, and
  `GET /api/crm/campaign_members?event_id={id}` (`account_id`, `contact_id`, `status`).
- Trade shows: `GET /api/tradeshows`, `/api/tradeshows/{show_id}/exhibitors`
  (`company_id`, `company_name`, `description`, `booth`, `country`, `website`,
  `crm_account_id`), `/api/tradeshows/{show_id}/meeting_interest`
  (`company_name`, `interest_score`, `requested_demo`, `notes`).
- Imports: `GET /api/import_batches`, `/api/import_batches/{batch_id}/raw_contacts`,
  `/api/import_batches/{batch_id}/suppression`.

---

## FAMILY A — Post-event sponsor handoff / reconciliation

(train_001 "audit handoff" style and train_004 "reconciliation" style. Same engine; the
template decides how much detail to emit. Read the template to know which sub-objects exist:
the simpler form wants `sponsor_statuses` + `qualified_lead_accounts` + `excluded_records` +
`follow_up` + `crm_action_counts`; the richer form adds `badge_decisions`,
`campaign_member_actions`, `opportunity_summary`, `badge_only_contacts`, `exclusion_counts`.)

### A1. Classify each sponsor (one row per sponsor ORDER account)

For every order/package account, reconcile order_status + invoice:
- `order_status == "canceled"` → **not an active sponsor**. In the 4-status schema this is
  `not_sponsor`; in the 3-status schema (`paid_deferred|open_invoice|proposal_only`) the
  canceled account is dropped from `sponsor_statuses` and instead appears in
  `excluded_records` with reason `inactive_sponsor_record`.
- `order_status == "proposal_sent"` AND no matching invoice → `proposal_only`.
- `order_status == "confirmed"` (has an invoice): use the invoice `status`:
  - invoice `status == "paid_deferred"` (or fully paid: `paid_amount >= amount`) → `paid_deferred`.
  - invoice `status == "open"` / not fully paid → `open_invoice`.
- **Amounts:** `package_amount` / `amount_usd` = the order/package `amount` (integer).
  For `open_invoice`, the **open balance = `amount - paid_amount`** (report it separately,
  e.g. `open_balance`, and aggregate into `open_invoice_balance`). `paid_amount` comes from
  the invoice. For `paid_deferred`, open_balance = 0.
- `invoice_id` = the invoice's id, or `null` when there is no invoice (proposal_only).
- Sort `sponsor_statuses` by `account_name` ascending.

### A2. Sponsor revenue totals (when required)
Group by status and sum the **package amount** (not the paid amount):
- `paid_deferred` = Σ package amount of paid_deferred sponsors.
- `open_invoice` = Σ package amount of open_invoice sponsors.
- `proposal_only` = Σ package amount of proposal_only sponsors.
- `open_invoice_balance` = Σ (amount − paid_amount) over open_invoice sponsors.

### A3. Classify each badge / find qualified non-sponsor leads
Walk the event badges. A badge becomes a **qualified non-sponsor lead** only if ALL hold:
- `badge_type` is a **business** type (`attendee`; treat `sponsor` as sponsor, and
  `student`, `press`, and other non-business types as non-business). Exclude non-business.
- The badge's company is NOT one of the sponsor accounts, and the contact is not a sponsor
  ticket contact → otherwise exclude as `sponsor_attendee`.
- The matching CRM account (match by company name / domain) is NOT `status == "disqualified"`
  → otherwise exclude as `existing_disqualified`.
- The badge has a usable contact (a contact_name plus at least one of email/phone). If it has
  neither email nor phone (and richer schema cares), exclude as `missing_contact`.

**Exclusion reason precedence** (first match wins, matching the prompt's listed order):
`sponsor_attendee` → `inactive_sponsor_record` (canceled-sponsor company) → `non_business_badge`
→ `existing_disqualified` → `missing_contact`. (A canceled-sponsor company attendee is an
`inactive_sponsor_record`, not `existing_disqualified`, even if the account is also flagged
disqualified.)

`excluded_records` sort: by `company_name` asc, then `contact_name` asc.

### A4. CRM create-vs-update decisions for qualified leads
For each qualified lead, match the badge company to CRM accounts (by name/domain) and the
badge person to CRM contacts (by normalized email/name under that account):
- Account: exists → `update_existing`; not found → `create_account`.
- Contact: a contact with same normalized email/name under that account exists →
  `update_existing`; else → `create_contact`.
- Campaign member: if an existing `campaign_members` row already covers that account+contact
  for this event → `update_campaign_member` (richer schema) / count as
  `campaign_members_update`; else `add_campaign_member` / `campaign_members_create`.
- `opportunity_amount` for each qualified non-sponsor = the event's `lead_opportunity_amount`.
- `lead_pipeline_total` / `open_opportunity_total_usd` = `lead_opportunity_amount` ×
  (number of qualified leads); the matching count is the number of qualified leads.

`crm_action_counts` are tallied **over the qualified leads only** (do not count excluded or
sponsor rows): `accounts_create`, `accounts_update`, `contacts_create`, `contacts_update`,
`campaign_members_create`, `campaign_members_update`.

### A5. badge_decisions (richer schema only) — one row per badge, sorted by `badge_id`
- `classification` ∈ `sponsor_attendee | qualified_non_sponsor_lead | excluded`.
- `crm_action` for a qualified lead: account+contact both new → `create_account_contact_campaign_member`;
  account exists, contact new → `create_contact_campaign_member`; both exist, member new →
  `add_campaign_member`; member exists but needs status change → `update_campaign_member`;
  nothing to do → `no_action`; excluded/non-importable → `no_import`.
- `exclusion_reason` ∈ `sponsor_attendee | non_business_badge | existing_disqualified |
  missing_contact | null` (null for non-excluded).

### A6. campaign_member_actions (richer schema only) — sorted by `subject_key`
Reconcile each subject (sponsor ticket contacts + qualified leads + excluded) against
existing `campaign_members`:
- `target_status`: sponsor who has an attended badge → `attended_sponsor`; sponsor with no
  attended badge (registered only) → `registered_sponsor`; qualified non-sponsor who attended
  → `attended`; excluded → `excluded`.
- `action`: target == existing status → `no_action`; member exists but status differs →
  `update`; no member yet and importable → `create`; excluded/non-importable → `no_import`.

### A7. Follow-up dates & finance handoff
- **Lead follow-up due date** = event `end_date` + `followup_days_after_end` (calendar days).
- **Sponsor finance / sponsor follow-up due date** = `end_date` + `sponsor_followup_days_after_end`.
  Format `YYYY-MM-DD`.
- `lead_task_count` = number of qualified leads.
- **Sponsor finance / unpaid follow-up** targets the sponsors who still owe money:
  `open_invoice` sponsors (invoice open / not fully paid). `paid_deferred` are settled (no
  follow-up); `proposal_only` have no invoice (no finance follow-up). Provide their account
  names (sorted asc), the count, and the unpaid total (= Σ open balance = Σ amount − paid).

### A8. opportunity_summary (richer schema)
- `qualified_non_sponsor_account_names` = sorted-asc names of qualified leads.
- `lead_opportunity_amount_usd` = event `lead_opportunity_amount`.
- `open_opportunity_total_usd` = lead_opportunity_amount × count(qualified leads);
  `open_opportunity_count` = count(qualified leads).

### A9. badge_only_contacts (richer schema)
Normalized contact facts for qualified non-sponsor (badge-only) leads: `company_name`,
`contact_name`, `normalized_email`, `normalized_phone` (empty string allowed for a missing
side). Sort by `company_name` asc.

---

## FAMILY B — Trade-show prospecting qualification + ranking

(train_002 "qualified list" style and train_005 "ranked prospecting" style. Same
qualification engine; train_005 adds ranking + opportunity sizing + CRM overlap.)

### B1. Qualify each exhibitor from its `description`
Qualified = the company **manufactures / OEM-builds** one or more **target underwater
platforms** (`AUV`, `ROV`, `Underwater Camera`). Read the description for build/make/OEM
language. Detect platforms (a company may cover several):
- "AUV", "autonomous underwater vehicle" → `AUV`
- "ROV", "remotely operated vehicle" → `ROV`
- "underwater camera", "camera module/array", "optics manufacturer" → `Underwater Camera`
Emit `platforms` in **enum order**: AUV, then ROV, then Underwater Camera.

### B2. Exclusion (near-miss) classification — the critical discrimination
A company that only touches the space adjacently is EXCLUDED. Map the description to a reason:
- Distributor / dealer / reseller / sales agent (does not build) → `distributor_only`
  (train_005 `relationship_type` = `distributor`).
- Consulting / operates rented gear / services / analytics-dashboard / software-only with no
  hardware manufacturing → `service_only` (train_005 `relationship_type` = `service_provider`).
- Sensor / probe vendor only (builds the payload, not the platform) →
  `sensor_vendor_only` (train_002) / `sensor_only` (train_005);
  `relationship_type` = `sensor_vendor`.
- Research lab / academic only → `research_only`; `relationship_type` = `research`.
- (train_002 also allows `not_target_market` for clearly off-theme exhibitors.)
**Watch the near misses:** a distributor of ROVs, a service firm that *operates* ROVs, and a
sensor-only vendor all mention platform words but are NOT qualified. Qualification requires
*building/OEM-manufacturing the platform itself*. Excluded rows get `crm_action = no_import`.
Sort `excluded_*` by `company_name` asc.

### B3. CRM overlap & action (per qualified lead)
- Use the exhibitor's `crm_account_id`. If non-null and present in `/api/crm/accounts` →
  existing account → `crm_action = update_existing` and `crm_account_id` = that id.
- If null / not in CRM → `crm_action = create_account`, `crm_account_id = null`.
- `existing_crm_overlap_count` = number of qualified leads with an existing CRM account;
  `existing_crm_overlap_account_ids` = those account ids, sorted ascending.

### B4. Priority tier & opportunity sizing (join exhibitor → meeting_interest by company_name)
From `meeting_interest`: `requested_demo` (bool) and `interest_score` (int). Default missing
interest to `requested_demo=false`, score 0.
- Tier `A` = `requested_demo == true` AND `interest_score >= 90`.
- Tier `B` = `requested_demo == true` AND `interest_score >= 80` (and not A).
- Tier `C` = everything else (qualified but lower interest / no demo).
- Opportunity sizing by tier (train_005 explicit; reuse when sizing is requested):
  `A = 120000`, `B = 90000`, `C = 50000`. `total_estimated_opportunity_usd` = Σ over leads.

### B5. Ranking (train_005 style; `rank` is 1-based contiguous)
Sort qualified leads by, in order:
1. `requested_demo` true before false,
2. `interest_score` descending,
3. broader platform coverage (more platforms first),
4. `company_name` ascending.
Assign rank 1..N in that order. (train_002 has no ranking — there, sort qualified
exhibitors by `company_name` asc.)

### B6. Aggregate counts
- `qualified_total` / `qualified_lead_count`, `excluded_*_total` / `excluded_count`.
- `platform_counts` / `platform_coverage_counts`: count of qualified leads covering each
  platform — keys exactly `AUV`, `ROV`, `Underwater Camera` (a multi-platform lead increments
  each platform it covers).
- `priority_counts`: counts of tiers `A`, `B`, `C` among qualified leads.

---

## FAMILY C — Raw-contact import hygiene (train_003 style)

Goal: turn `raw_contacts` for a batch into clean, dedup'd, suppressed-filtered import rows.
`campaign_code` comes from the batch record in `/api/import_batches`.

### C1. Normalize every row
email → trim+lowercase; phone → digits only (as in §0.5). Keep `row_id`, `company_name`,
`contact_name`, `source_name`, `captured_at`.

### C2. Removal pipeline (apply in this order; first disqualifier wins, with its reason)
1. **Missing contact** (`reason = missing_contact`, counts toward `unusable_removed_count`):
   the row has no usable contact identity — i.e. normalized email is empty AND normalized
   phone is empty (a row with only an email *or* only a phone is still usable; the missing
   side becomes `""`).
2. **Suppressed** (`reason = suppressed`, counts toward `suppressed_removed_count`): the
   normalized email OR normalized phone matches any entry in the batch `suppression` list
   (match on normalized email or normalized phone; suppression reasons like global_opt_out /
   privacy_request / role_account all suppress). Suppress regardless of which company name the
   row claims (a suppressed person who shows up under a different company is still suppressed).
3. **Duplicate** (`reason = duplicate`, counts toward `duplicate_removed_count`): group the
   remaining rows by **dedup key = normalized email** (primary identity; fall back to
   normalized phone only when email is absent). Each group with >1 row keeps one **winner**
   and removes the rest.
   - Winner rule: prefer the most recent `captured_at`; break ties by lowest `row_id`.
     (This tie-break is the main uncertain point — apply it consistently.)

### C3. Surviving clean contacts
For each survivor emit: `clean_contact_id` and `source_row_id` = the **winning row's**
`row_id`; `company_name`, `contact_name`, normalized `email`/`phone`, `source_name`,
`captured_at` from the winning row; plus CRM resolution:
- Match company → CRM account by domain (email domain) / name. Account exists →
  `crm_action = update_existing`, `existing_account_id` = that id; else `create_account`,
  `existing_account_id = null`.
- Match person → CRM contact (normalized email/name under that account). Found →
  `existing_contact_id` = that id; else `null`. (A found existing contact also implies
  `update_existing`.)
Sort `clean_contacts` by `clean_contact_id` ascending.

### C4. Summaries
- `duplicate_summary.duplicate_keys`: one item per duplicate group, each
  `{key, winner_row_id, removed_row_ids[]}`; sort by `key` asc. `duplicate_removed_count` =
  total removed duplicates.
- `removal_summary.removed_rows`: every removed row `{row_id, reason}` with reason ∈
  `duplicate | missing_contact | suppressed`; sort by `row_id` asc. Plus
  `unusable_removed_count` (missing_contact) and `suppressed_removed_count`.
- `import_action_totals`: tally the `crm_action` over the FINAL set (surviving clean contacts
  contribute `create_account`/`update_existing`; missing-contact removals contribute
  `no_import`; suppressed removals contribute `suppress`). Duplicate-loser rows are not
  tallied here (only their winner is). Keys: `create_account`, `update_existing`, `no_import`,
  `suppress`.
- `campaign_member_import_count` = number of surviving clean contacts.

---

## Common misjudgments to avoid

- Don't classify a **canceled** sponsor order as `proposal_only` — canceled = `not_sponsor` /
  `inactive_sponsor_record`, and it must be excluded from active sponsor revenue.
- Don't treat the **paid_amount** as the sponsor's revenue contribution for totals — group on
  the **package amount**; the open balance (`amount − paid`) is reported separately.
- Don't mark a **distributor/reseller, a service/operator firm, or a sensor-only vendor** as a
  qualified platform builder just because the description mentions ROV/AUV/camera words.
- Don't drop a lead for a missing email when a phone is present (or vice-versa) — normalize
  the present side and leave the other as `""`. `missing_contact` requires BOTH missing.
- Don't forget suppression matches on **email OR phone**, and that suppression/missing-contact
  are evaluated **before** dedup so a removed row never becomes a dedup winner.
- Don't count excluded/sponsor rows in `crm_action_counts` or in qualified-lead pipeline math.
- Sponsor finance follow-up targets **open_invoice** sponsors only (paid_deferred settled,
  proposal_only has no invoice).
- Date math is plain calendar-day addition on the event **end_date**; use the right offset
  (`followup_days_after_end` for leads vs `sponsor_followup_days_after_end` for sponsors).
- Emit values, not schema metadata: when the template is a descriptor, your output is the
  real object, never the descriptor's `field_definitions`/`required_value` text.
- Honor every sort rule exactly, and keep `platforms` in fixed enum order regardless of the
  order they appear in the description.
