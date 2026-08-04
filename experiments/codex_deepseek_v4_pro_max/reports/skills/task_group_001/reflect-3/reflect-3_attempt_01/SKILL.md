 # HarborCRM Data Reconciliation & Prospecting Skill

 ## Overview

 This skill covers HarborCRM API-based data tasks: event CRM handoff reconciliation, trade-show exhibitor prospecting, and import-batch contact cleaning. Use the shared REST API at the base URL supplied by the runner (typically as `<TASK_ENV_BASE_URL>` or an environment variable). All endpoints are public GET; no authentication is required.

 ## API Reference

 The HarborCRM API exposes these endpoint families. Always fetch all relevant endpoints for a task before building the answer.

 ### Events
 - `GET /api/events/{event_id}` — event metadata (dates, followup windows, lead opportunity amount, campaign code)
 - `GET /api/events/{event_id}/orders` — sponsor orders (account, amount, status, ticket contacts)
 - `GET /api/events/{event_id}/badges` — badge scans (type, contact info, company)
 - `GET /api/events/{event_id}/sponsor_packages` — same as orders

 ### Finance
 - `GET /api/finance/invoices?event_id={event_id}` — invoices with payment status, paid/deferred amounts

 ### CRM
 - `GET /api/crm/accounts` — all CRM accounts (name, domain, status, disqualified_reason, owner_region)
 - `GET /api/crm/contacts` — all CRM contacts (name, email, phone, opted_out flag, account linkage)
 - `GET /api/crm/opportunities` — opportunities (account, amount, stage, event linkage)
 - `GET /api/crm/campaign_members?event_id={event_id}` — campaign member records for an event

 ### Trade Shows
 - `GET /api/tradeshows` — all trade shows
 - `GET /api/tradeshows/{show_id}` — single show metadata
 - `GET /api/tradeshows/{show_id}/exhibitors` — exhibitors (company, booth, description, CRM linkage)
 - `GET /api/tradeshows/{show_id}/meeting_interest` — meeting interest records (scores, demo requests)

 ### Import Batches
 - `GET /api/import_batches` — all batches
 - `GET /api/import_batches/{batch_id}` — batch metadata (campaign code, source system)
 - `GET /api/import_batches/{batch_id}/raw_contacts` — raw contact rows to clean
 - `GET /api/import_batches/{batch_id}/suppression` — email/phone suppression list for the batch

 ### Policies
 - `GET /api/policies` — global policies (contact hygiene rules, platform enums, qualification notes, sponsor status enums)

 ## Data Normalization Rules

 ### Email
 - Trim leading/trailing whitespace
 - Convert to lowercase

 ### Phone
 - Strip all non-digit characters
 - Do not strip leading country codes (e.g. `+1 415 555 0188` → `14155550188`); keep the digits exactly as they appear after stripping formatting

 ### Company Names
 - Use exact string match against CRM `account.name` for account lookups
 - When company names vary across duplicate rows, prefer the more complete/formal name from the earliest-captured row

 ## Event CRM Handoff (Reconciliation Pattern)

 This pattern applies when a prompt asks you to reconcile post-event data — sponsor orders, badges, invoices, CRM accounts/contacts/campaign members, and opportunities — into a structured handoff JSON.

 ### Sponsor Status Classification

 Determine each sponsor account's status by cross-referencing orders and invoices:

 1. **paid_deferred** — confirmed order with a paid invoice (invoice `status` is `paid_deferred`)
 2. **open_invoice** — confirmed order with an unpaid or partially paid invoice (invoice `status` is `open`)
 3. **proposal_only** — order exists (status `proposal_sent`) but no invoice has been issued
 4. **not_sponsor** — used only when the template explicitly requires it; otherwise, canceled orders (`order_status: canceled`) are excluded from the active sponsor list

 ### Sponsor Revenue Aggregation

 - Sum `package_amount` (from the order) grouped by sponsor status
 - For `open_invoice`, compute `open_balance` as `invoice.amount - invoice.paid_amount` (not deferred_amount)
 - `paid_deferred` and `proposal_only` have `open_balance: 0`

 ### Lead Qualification from Badges

 From the badges list, a contact is a **qualified non-sponsor lead** when ALL of the following hold:
 - `badge_type` is `attendee` (not `sponsor`, `student`, `press`, or any other non-business type)
 - The company is NOT a sponsor (check orders: no order exists for that company, or the only order is `canceled`)
 - The CRM account (if it exists) is NOT disqualified (`disqualified_reason` is `null`)

 ### Exclusion Reasons for Non-Qualified Records

 Apply the most specific applicable reason:
 - **sponsor_attendee** — the contact's company has ANY sponsor order (confirmed, proposal_sent, or canceled)
 - **inactive_sponsor_record** — the company had a sponsor order that was canceled (`order_status: canceled`)
 - **non_business_badge** — the badge type is `student`, `press`, or any type other than `attendee`/`sponsor`
 - **existing_disqualified** — the CRM account exists and has a non-null `disqualified_reason`

 When multiple reasons apply, prefer the most specific: `inactive_sponsor_record` over `existing_disqualified` for a canceled sponsor whose CRM account is also disqualified.

 ### Lead Opportunity Amount

 Use the event's `lead_opportunity_amount` field (from `GET /api/events/{event_id}`) for each qualified non-sponsor account. The `lead_pipeline_total` is the sum across all qualified leads.

 ### Follow-Up Dates

 - **lead_due_date**: `event.end_date` + `event.followup_days_after_end` days
 - **sponsor_finance_due_date**: `event.end_date` + `event.sponsor_followup_days_after_end` days

 Compute by parsing the end date, adding the integer days, and formatting as `YYYY-MM-DD`.

 ### Sponsor Finance Follow-Up Targets

 Include sponsor accounts that need finance attention:
 - Accounts with `open_invoice` status
 - Accounts with `proposal_only` status (need follow-up to close the proposal)
 - Exclude fully paid (`paid_deferred`) accounts

 `sponsor_finance_task_count` equals the number of accounts in `sponsor_finance_accounts`.

 ### CRM Action Counts

 Count implied CRM work across the entire handoff (qualified leads only — not sponsor contacts or excluded records):
 - **accounts_create**: qualified leads whose company has no CRM account
 - **accounts_update**: qualified leads whose company already has a CRM account
 - **contacts_create**: qualified lead contacts not found in CRM contacts (match by name AND email)
 - **contacts_update**: qualified lead contacts already in CRM contacts
 - **campaign_members_create**: qualified leads without an existing campaign member for this event
 - **campaign_members_update**: existing campaign members for this event that need a status change (e.g. an attended disqualified account whose campaign member status should become `excluded`)

 ### Campaign Member Handling

 For the campaign_member_actions list (when the template requires it):
 - Existing campaign members with correct status → `no_action`
 - Sponsor contacts who attended (badge exists) but lack a campaign member → `create` with `target_status: attended_sponsor`
 - Sponsor contacts who registered but have no badge → `no_action` with `target_status: registered_sponsor`
 - Qualified non-sponsor leads → `create` with `target_status: attended`
 - Excluded badge holders → `no_import`

 ## Trade-Show Exhibitor Prospecting Pattern

 This pattern applies when a prompt asks you to identify qualified exhibitors from a trade show for a specific campaign, classify their platform coverage, assign priority tiers, and rank them.

 ### Qualification

 Read each exhibitor's `description` field and decide whether the company **builds or OEM-manufactures** platforms covered by the campaign's target platform list (from `GET /api/policies` → `prospecting.platform_enums`). The policy's `qualification_note` provides semantic guidance.

 A company qualifies when its description indicates it **makes** the target platforms. A company is **not qualified** when it only:
 - Resells or distributes (→ `distributor_only`)
 - Provides services/consulting using rented equipment (→ `service_only`)
 - Makes sensors/probes but not the platforms themselves (→ `sensor_vendor_only` / `sensor_only`)
 - Conducts research only (→ `research_only`)

 ### Platform Classification

 For each qualified exhibitor, list the target platforms they build. Use only the enums from the policy. Order platforms in the enum declaration order (e.g. `AUV`, `ROV`, `Underwater Camera`).

 ### Priority Tier Assignment

 When the prompt provides tier criteria (or when meeting-interest data is available with demo requests and scores), apply the rules exactly:
 - **A**: demo requested AND interest score ≥ 90
 - **B**: demo requested AND interest score ≥ 80 (but < 90)
 - **C**: all other qualified leads (no demo, or demo with score < 80)

 ### Opportunity Sizing

 Multiply by tier when amounts are specified:
 - Tier A → highest amount (e.g. USD 120,000)
 - Tier B → middle amount (e.g. USD 90,000)
 - Tier C → base amount (e.g. USD 50,000)

 If no tier amounts are specified in the prompt but the template requires `opportunity_estimate_usd`, derive from the event's `lead_opportunity_amount` or use the tier amounts given in the ranking instructions.

 ### Ranking

 When ranking instructions are provided, apply them in order as a compound sort:
 1. Primary: demo requested first (true before false)
 2. Secondary: interest score descending
 3. Tertiary: broader platform coverage (more platforms first)
 4. Quaternary: company name ascending

 ### CRM Overlap

 For each qualified exhibitor, check `crm_account_id`:
 - Non-null → `crm_action: update_existing`, include in `existing_crm_overlap_account_ids`
 - Null → `crm_action: create_account`

 ### Excluded Exhibitors

 Record every non-qualified exhibitor in the exclusion list with:
 - `relationship_type` matching the exclusion category (`distributor`, `service_provider`, `sensor_vendor`, `research`)
 - `exclusion_reason` using the `_only` suffix form (`distributor_only`, `service_only`, `sensor_only`, `research_only`)
 - `crm_action: no_import`

 ## Import Batch Cleaning Pattern

 This pattern applies when a prompt asks you to prepare raw contacts from an import batch for CRM import — deduplicating, suppressing, normalizing, and matching against existing CRM records.

 ### Contact Normalization

 For each raw contact row:
 - **email**: trim whitespace, convert to lowercase; if result is empty string, treat as missing
 - **phone**: strip all non-digit characters; keep resulting digits as-is (including country codes)

 ### Deduplication

 Group raw contacts by **normalized email** (case-insensitive). Within each group:
 - The **winner** is the row with the earliest `captured_at` timestamp
 - On timestamp ties, prefer the lower `row_id` (lexicographic)
 - All other rows in the group are removed as duplicates

 Record each duplicate group in `duplicate_summary`:
 - `key`: the normalized email
 - `winner_row_id`: the winning row's id
 - `removed_row_ids`: list of other row ids in the group

 ### Suppression

 After deduplication, check each surviving row against:
 1. The batch's suppression list (`GET /api/import_batches/{batch_id}/suppression`) — match by normalized email
 2. CRM contacts with `opted_out: true` — match by normalized email

 A match on either list means the row is **suppressed**. Suppressed rows are removed from the clean import list.

 ### Unusable Rows

 A row is **unusable** (`missing_contact`) when:
 - Normalized email is empty string AND normalized phone is empty string
 - Or contact_name is a clear placeholder (e.g. "Blank Fields")

 ### CRM Matching for Survivors

 For each surviving clean contact:
 - Match `company_name` (exact string match) against CRM `account.name` → if found, `existing_account_id` is the CRM account's id, `crm_action` is `update_existing`
 - If no company match, `existing_account_id` is `null`, `crm_action` is `create_account`
 - Match normalized email against CRM `contact.email` → if found, `existing_contact_id` is the CRM contact's id

 ### Import Action Totals

 Count `crm_action` values across all surviving clean contacts:
 - `create_account`: count of rows with no CRM account match
 - `update_existing`: count of rows with a CRM account match
 - `no_import`: count of rows that should not be imported (if any remain with this classification)
 - `suppress`: count of rows removed due to suppression (these appear in `removal_summary.suppressed_removed_count`)

 ### Campaign Member Count

 `campaign_member_import_count` equals the number of surviving clean contacts (those with `crm_action` of `create_account` or `update_existing`).

 ### Removal Summary

 List all removed rows in `removed_rows`, sorted by `row_id` ascending, with reasons:
 - `duplicate` — removed by deduplication
 - `suppressed` — matched suppression list or CRM opt-out
 - `missing_contact` — no usable contact information

 ## General Guidelines

 ### Sorting

 Unless the template or prompt specifies otherwise:
 - Sort lists of objects by `name` or `id` ascending
 - Sort platform enums in the order declared by the policy
 - Sort exclusion/removal lists by the primary sort key specified in the template

 ### Dates

 - All dates in output use `YYYY-MM-DD` format
 - Compute follow-up dates by adding integer days to the event's `end_date`
 - Use standard date arithmetic (not calendar months)

 ### Currency

 - All monetary values are integers (whole USD)
 - Sum at the appropriate level of aggregation; do not double-count

 ### Answer Format

 - Return exactly one JSON object matching the provided answer template
 - Do not include explanatory prose, markdown fences, or extra fields outside the template
 - Use `null` (not the string `"null"`) for absent optional fields
 - Use `""` (empty string) for empty normalized values when the template allows it

 ### Policy Awareness

 Always fetch `GET /api/policies` and apply the enums and rules it declares:
 - `sponsor_handoff.status_enums` for sponsor status values
 - `prospecting.platform_enums` for allowed platform values
 - `contact_hygiene.note` for import preparation philosophy
 - `prospecting.qualification_note` for exhibitor qualification semantics
