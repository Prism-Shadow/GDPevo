---
name: harborcrm-front-of-funnel-handoff
description: SOP for HarborCRM front-of-funnel tasks — event sponsor-handoff reconciliation, trade-show exhibitor prospecting, and raw contact-import hygiene — using the read-only HarborCRM data API to produce strict JSON answers.
---

# HarborCRM Front-of-Funnel Handoff Skill

You are given a single task `prompt.txt` plus an `answer_template.json` that defines the exact
output shape, key names, value enums and sort order. Produce ONE JSON object that conforms to the
template. No prose outside the JSON. Never invent fields not in the template; always emit every
required key (use `[]`, `{}`, `0`, `""`, or `null` where there is no data).

## 0. Environment / API usage

- Base URL is supplied by the runner; it is **HTTP-only**. Call with `curl` (Bash tool) or python
  `urllib`/`requests`. **Do NOT use WebFetch** (it forces HTTPS and fails).
- First two calls every time: `GET /health` (sanity + record counts) and `GET /api/policies`
  (status/platform enums and hygiene notes). The policy `status_enums` =
  `paid_deferred, open_invoice, proposal_only, not_sponsor`; `platform_enums` =
  `AUV, ROV, Underwater Camera`.
- Read-only endpoints (combine per sub-goal):
  - Events: `GET /api/events`, `/api/events/{id}`, `/api/events/{id}/orders`,
    `/api/events/{id}/badges`, `/api/events/{id}/sponsor_packages`,
    `GET /api/finance/invoices?event_id={id}`, `GET /api/crm/campaign_members?event_id={id}`.
  - Trade shows: `GET /api/tradeshows`, `/api/tradeshows/{id}/exhibitors`,
    `/api/tradeshows/{id}/meeting_interest`.
  - Imports: `GET /api/import_batches`, `/api/import_batches/{id}/raw_contacts`,
    `/api/import_batches/{id}/suppression`.
  - Shared CRM (NOT event-scoped; filter client-side): `GET /api/crm/accounts`,
    `/api/crm/contacts`, `/api/crm/opportunities`.
- There are NO answer/judge endpoints. Do not look for one.

## 1. Identify the task family

- Mentions an `event_id` + sponsor/badge/finance reconciliation -> **Family A: Sponsor handoff**.
- Mentions a `show_id` + exhibitors/prospecting/platforms -> **Family B: Trade-show prospecting**.
- Mentions an `import_batches` / `batch_id` + raw contacts -> **Family C: Import hygiene**.

## 2. Shared normalization & matching rules (used by all families)

- **Email normalize**: trim surrounding whitespace, lowercase. Empty/whitespace-only -> `""`.
- **Phone normalize**: keep digits only (`re.sub(r"\D","",p)`). Keep a leading country-code digit if
  present in the source; do NOT synthesize one. Empty -> `""`. (CRM stores e.g. `14155550101`;
  `+1 (415) 555-0101`, `415-555-0101`, `1.206.555.0177` all collapse to digits.)
- **Email domain** = substring after `@` of the normalized email.
- **Match a record to an existing CRM account**: by exact company `name`, OR by account `domain`
  == email domain. **Match an existing CRM contact**: by normalized email == contact email
  (fallback: exact contact name). CRM accounts carry `status`
  (`customer|prospect|disqualified`) and `disqualified_reason`. Contacts carry `opted_out`.
- A CRM account with `status == "disqualified"` (any `disqualified_reason`) is NOT a valid lead.

## 3. Family A — Event sponsor handoff reconciliation

Endpoints: event detail, orders (== sponsor_packages, same records), invoices, badges,
campaign_members, crm/accounts, crm/contacts, crm/opportunities.

### 3a. Sponsor status (reconcile order_status + invoice.status). One row per sponsor order:
- `order_status == "canceled"` -> NOT an active sponsor. This is an **inactive/canceled sponsor
  record**: exclude from sponsor_statuses and its revenue; surface its attendee under the badge
  exclusion list (reason `inactive_sponsor_record`).
- `order_status == "proposal_sent"` (no paid invoice yet) -> **`proposal_only`**; amount = order/package amount.
- `order_status == "confirmed"` + matching invoice:
  - invoice `status == "paid_deferred"` (paid_amount covers amount) -> **`paid_deferred`**.
  - invoice `status == "open"` -> **`open_invoice`**; `open_balance = invoice.amount - invoice.paid_amount`.
- `not_sponsor` is the enum for an account that never sponsored (used in templates that classify
  every account, e.g. when a template requires emitting all four enums).
- Revenue totals: sum package/order `amount` by status (integer USD). Report
  `open_invoice_balance` (sum of open balances) separately from `open_invoice` (sum of full
  package amounts). paid_deferred/proposal_only contribute full amount, zero open balance.

### 3b. Badge handling -> qualified leads vs exclusions
Active sponsor = company/contact on a non-canceled order (proposal_sent counts as active for
attendee purposes). For each badge, classify with this **precedence (first match wins):**
1. `non_business_badge` — badge_type not a business type. Business = `sponsor`, `attendee`.
   Non-business = `student`, `press`, `media`, `analyst`, `academic`, etc.
2. `sponsor_attendee` — company is an active sponsor OR contact is on an active order's
   `ticket_contacts`.
3. `inactive_sponsor_record` — company/contact tied to a **canceled** sponsor order.
4. `existing_disqualified` — matched CRM account has `status == "disqualified"`.
5. Otherwise -> **qualified non-sponsor lead**.

### 3c. Qualified non-sponsor lead fields & CRM actions
- `opportunity_amount` for every qualified lead = the event's `lead_opportunity_amount`
  (same for all of them). `lead_pipeline_total` = (#qualified leads) × lead_opportunity_amount.
- `crm_account_action`: `update_existing` if the badge matches an existing (non-disqualified) CRM
  account (by name or domain); else `create_account`.
- `crm_contact_action`: `update_existing` if an existing CRM contact matches (email/name); else
  `create_contact`.
- `campaign_member_action`: `add_campaign_member` for a new qualified lead not already a member;
  `update_campaign_member` if already a member whose status must change; `no_action` if already a
  member with the correct status.
- `normalized_email` / `normalized_phone`: per section 2.

### 3d. crm_action_counts (roll-up of the qualified-lead work)
Count create vs update for accounts/contacts/campaign_members across the qualified leads only
(sponsors and excluded badges produce no create/update here). campaign_members_create =
qualified leads being added; campaign_members_update = members needing a status change.

### 3e. Follow-up dates & tasks
- `lead_due_date` (qualified-lead handoff) = event `end_date` + `followup_days_after_end` days.
- `sponsor_finance_due_date` = event `end_date` + `sponsor_followup_days_after_end` days.
- `lead_task_count` = number of qualified leads (one follow-up task each).
- `sponsor_finance_task_count` / `sponsor_finance_accounts` / `unpaid_sponsor_*` = sponsors that
  still owe money = those with status `open_invoice` (and, if asked, `proposal_only`). Use
  `open_invoice` accounts for "unpaid finance follow-up"; `unpaid_sponsor_total_usd` = sum of their
  open balances. Account-name lists are sorted ascending.

### 3f. Richer event templates (e.g. badge_decisions / campaign_member_actions)
- `badge_decisions`: one row per badge, sorted by `badge_id`. `classification` ∈
  `sponsor_attendee | qualified_non_sponsor_lead | excluded`. `crm_action` ∈
  `create_account_contact_campaign_member` (new lead, no CRM account) /
  `create_contact_campaign_member` (account exists, contact new) / `add_campaign_member` /
  `update_campaign_member` / `no_action` (sponsor already a correct member) / `no_import`
  (excluded). `exclusion_reason` is the 3b reason or `null` when not excluded.
- `campaign_member_actions`: sorted by `subject_key`. `action` ∈ `create|update|no_action|no_import`;
  `target_status` ∈ `attended_sponsor|registered_sponsor|attended|excluded`. Existing member with
  matching status -> `no_action`; existing member needing a status change -> `update`; new
  attendee/lead -> `create`; excluded -> `no_import`.
- `badge_only_contacts`: qualified non-sponsor leads sourced only from badges (not already full CRM
  contacts), with normalized email/phone; sort by company_name.
- `opportunity_summary`: `qualified_non_sponsor_account_names` (sorted), `lead_opportunity_amount_usd`
  = event lead amount; `open_opportunity_total_usd` = (#qualified non-sponsor leads) ×
  lead amount; `open_opportunity_count` = #qualified non-sponsor leads. (If a template instead asks
  for CRM open opportunities, use `/api/crm/opportunities` filtered to the event with non-closed
  `stage`.)
- `exclusion_counts`: tally of badge exclusions by reason
  (`sponsor_attendee`, `non_business_badge`, `existing_disqualified`, `missing_contact`).
  `missing_contact` = a badge/lead with neither email nor phone.

## 4. Family B — Trade-show exhibitor prospecting

Endpoints: tradeshow detail, exhibitors, meeting_interest, crm/accounts (and crm/opportunities if
sizing needs it). The campaign theme (e.g. OEM dissolved-oxygen sensor; aquaculture robotics)
defines the target platforms among the policy enums `AUV, ROV, Underwater Camera`.

### 4a. Qualify by what the company *builds*
Read each exhibitor `description`. **Qualify only companies that manufacture / build / "OEM-build"
the target platforms.** Assign `platforms` (subset of the enum, output **in enum order**
`AUV, ROV, Underwater Camera`) based ONLY on platforms they make:
- "Builds/Manufactures/Designs ... AUV/ROV" -> include those platforms.
- "underwater camera modules/manufacturer" -> `Underwater Camera`.
- Sensors/probes that are third-party or "embedded" do NOT make the company a sensor platform and
  do NOT add a platform; the camera/robot they build is what counts.

### 4b. Exclude the near-misses (do NOT add platforms for these)
Each excluded exhibitor stays visible in the exclusion list with a controlled reason. Map
description signal -> reason (use the exact enum spellings the template lists; note they differ by
template):
- Distributor / reseller / sales agent / "imported ... brands", "does not manufacture" ->
  `distributor_only` (relationship `distributor`).
- Consulting / operates-rented gear / analytics dashboard / "no hardware manufacturing" /
  services-only -> `service_only` (template variants: `service_only`; relationship `service_provider`).
- Sensor-only / probe vendor "for integration by platform partners" -> `sensor_vendor_only`
  (some templates use `sensor_only`; relationship `sensor_vendor`).
- Research lab / university / "research only" -> `research_only` (relationship `research`).
- `not_target_market` only if it builds platforms but none in scope / wrong domain entirely.
- Excluded exhibitors always get `crm_action = no_import`.

### 4c. CRM overlap & action
- exhibitor `crm_account_id` non-null (and account exists) -> `update_existing`; this exhibitor is
  an "existing CRM overlap". null -> `create_account`. (Excluded -> `no_import` regardless.)
- `existing_crm_overlap_account_ids` = sorted list of the qualified leads' non-null crm_account_ids;
  `existing_crm_overlap_count` = its length.

### 4d. Priority tier, opportunity sizing, ranking
Join exhibitor to its `meeting_interest` by `company_name` (`requested_demo` bool, `interest_score`).
Default tiering (also stated explicitly in some prompts — follow the prompt's numbers if given):
- `A` = requested_demo AND interest_score >= 90.
- `B` = requested_demo AND interest_score >= 80.
- `C` = everything else qualified (incl. no-demo or lower score).
Opportunity sizing by tier (use the prompt's USD if stated): A = 120000, B = 90000, C = 50000.
`total_estimated_opportunity_usd` = sum over qualified leads.

Ranking (when a ranked list is required), tie-break in order:
1. requested_demo true before false;
2. interest_score descending;
3. broader platform coverage (more platforms) first;
4. company_name ascending.
Then assign 1-based contiguous `rank`.

### 4e. Counts
- `qualified_total` / `qualified_lead_count` = #qualified.
- `platform_counts` = per-enum count of qualified leads whose `platforms` include that enum
  (a lead with two platforms increments two counters). Keys always include all three enums (0 ok).
- `priority_counts` = count of qualified leads per tier A/B/C.
- `excluded_*_total` / `excluded_count` = #excluded.
- Qualified list sorted by `company_name` ascending (unless a `rank` order is required).

## 5. Family C — Raw contact-import hygiene

Endpoints: import_batches (for `campaign_code`), batch raw_contacts, batch suppression,
crm/accounts, crm/contacts.

Pipeline (apply in this order):
1. **Normalize** every row's email/phone (section 2).
2. **Drop unusable** rows = no email AND no phone -> removal reason `missing_contact`
   (template enum `missing_contact`). These do NOT appear in `clean_contacts`.
3. **Deduplicate** the remaining rows by contact key = normalized email if present, else
   `phone:<digits>`. Within a duplicate group the **winner = earliest `captured_at`, tie-break by
   `row_id` ascending** (this matters when timestamps are identical). Losers -> removal reason
   `duplicate`; record `{key, winner_row_id, removed_row_ids (sorted)}` in `duplicate_keys`
   (sorted by key).
4. **Suppression check** on surviving winners: a row is suppressed if its normalized email matches a
   suppression `email` OR its normalized phone matches a suppression `phone`. Suppressed survivors
   get `crm_action = "suppress"` and ALSO appear in `removed_rows` with reason `suppressed`. They are
   NOT counted as campaign members.
5. **CRM action** for non-suppressed survivors: existing CRM contact (email match) OR existing CRM
   account (domain match) -> `update_existing`; otherwise `create_account`. (`no_import` is reserved
   for a survivor that should not import, e.g. maps to a disqualified account — use only if data
   warrants it.)

Output:
- `clean_contacts` = surviving winners (including suppressed ones, flagged `suppress`), sorted by
  `clean_contact_id` ascending. `clean_contact_id` == `source_row_id` == the winning row's `row_id`.
  Carry `company_name`, `contact_name`, normalized `email`/`phone`, `source_name` (enum: badge_scan,
  sponsor_form, partner_upload, webinar_form, exhibitor_form, manual_upload), winning row's
  `captured_at`, `crm_action`, and `existing_account_id`/`existing_contact_id` (string or null).
- `duplicate_summary`: `duplicate_removed_count` = # losers; `duplicate_keys` as above.
- `removal_summary`: `unusable_removed_count` (= #missing_contact), `suppressed_removed_count`
  (= #suppressed survivors), `removed_rows` = every removed row `{row_id, reason}` where reason ∈
  `duplicate|missing_contact|suppressed`, sorted by `row_id`.
- `import_action_totals`: counts of `crm_action` over `clean_contacts`
  (`create_account, update_existing, no_import, suppress`).
- `campaign_member_import_count` = # surviving clean contacts that will actually import =
  those with action `create_account` or `update_existing` (excludes `suppress` and `no_import`).
- `campaign_code` / `batch_id` come from the import_batch record.

## 6. Output formatting (all families)

- All money is **integer USD** (no decimals, no currency symbol).
- All dates `YYYY-MM-DD`; date math is plain calendar-day addition (`end_date + N days`).
- Emit enums with the EXACT spelling/casing the template lists (watch the cross-template variants:
  `sensor_vendor_only` vs `sensor_only`; `service_only`; relationship vs reason fields).
- Apply every `ordering`/`sort` rule from the template precisely (e.g. account_name asc;
  company_name asc then contact_name asc; badge_id asc; clean_contact_id asc; rank asc; platforms in
  enum order). Sorts are ascending and case-sensitive on the given field.
- Return exactly the declared keys; include all required keys even when empty.

## 7. Common misjudgments to avoid

- Counting a platform a company merely **distributes, operates, resells, or imports** — only count
  what they **build/manufacture/OEM-build**.
- Treating a canceled sponsor order as an active sponsor (it is `inactive_sponsor_record`, excluded
  from revenue) — but a `proposal_sent` order IS an active sponsor (`proposal_only`) and its
  attendees are `sponsor_attendee`.
- For `open_invoice`: reporting the open balance as the revenue. Revenue by status uses the full
  package amount; the open balance is a separate field.
- Forgetting that disqualified CRM accounts (`status == "disqualified"`) and non-business badges are
  excluded even if the person attended or is already a campaign member/contact.
- Dedup tie-break: when two rows share a `captured_at`, fall back to `row_id` ascending — don't pick
  arbitrarily.
- Suppressed rows: still surface them (action `suppress` + a `suppressed` removed_row) and never
  count them as campaign members.
- Phone normalization: keep the leading country-code digit if present; never add one that isn't
  there; strip ALL non-digits.
- Using the wrong follow-up offset: `followup_days_after_end` for LEAD follow-up vs
  `sponsor_followup_days_after_end` for SPONSOR finance follow-up.
- Lead opportunity amounts come from the EVENT (`lead_opportunity_amount`), not from CRM
  opportunities; every qualified lead gets the same amount.
- Emit integers (not floats) for all counts and USD; emit `null` (not `"null"`) where the template
  allows null.
