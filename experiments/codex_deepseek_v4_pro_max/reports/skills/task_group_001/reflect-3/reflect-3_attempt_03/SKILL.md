 # HarborCRM Reconciliation Skill

 This skill provides reusable patterns for solving HarborCRM data reconciliation, preparation, and handoff tasks. It covers event post-mortems, trade-show prospecting, import-batch preparation, and CRM handoff generation.

 ## Environment

 - HarborCRM REST API at `{BASE_URL}` (GET-only for business endpoints; no authentication required).
 - Answer schemas are provided via `input/payloads/answer_template.json`. Output must conform to the template exactly.
 - Responses must be a single JSON object with no explanatory prose outside the JSON.

 ## Data Normalization

 - **Emails**: lowercase, trim leading/trailing whitespace. Set to `""` when absent.
 - **Phones**: digits only (strip all non-digit characters). Set to `""` when absent.
 - **Dates**: `YYYY-MM-DD` strings.
 - **Currency**: integer USD (no decimals, no dollar signs).
 - **Company names**: use the canonical CRM account name when an account match is found; otherwise use the source-provided name.

 ## Core Reconciliation Loop

 For any event or trade-show task, follow this sequence:

 1. **Gather all relevant data** from the API endpoints listed in the task prompt.
 2. **Load policies** (`GET /api/policies`) for controlled enums and qualification rules.
 3. **Cross-reference** event/orders/badges against finance/invoices and CRM accounts/contacts/campaign-members.
 4. **Classify every record** using the controlled values from the answer template and policies.
 5. **Count and aggregate** according to the template's required keys.
 6. **Sort** as directed by the template (usually by name ascending, rank ascending, or badge/row ID ascending).

 ## Sponsor Classification

 Determine sponsor status by checking orders and invoices together:

- **paid_deferred**: order is confirmed, invoice exists with status `paid_deferred` (or fully paid).
- **open_invoice**: order is confirmed, invoice exists with status `open` (has unpaid balance).
- **proposal_only**: order has status `proposal_sent` or similar, and no corresponding invoice exists.
- **inactive/canceled**: order status is `canceled`. Do not include in active sponsor summaries; treat as excluded.

 For each active sponsor, capture: account_id, account_name, package_amount (from order), invoice_id (nullable), paid_amount, and open_balance (amount minus paid_amount).

 Sponsor revenue totals aggregate by status using the package amount (not paid portion). Track `open_invoice_balance` separately as the sum of open balances.

 Sponsor finance follow-up targets only sponsors with unpaid amounts (open_invoice or proposal_only). Follow-up due date = event end_date + sponsor_followup_days_after_end.

 ## Lead Qualification from Badge Scans

 Start with all badge scans for the event and remove:

 1. **Sponsor contacts** — any contact listed in a sponsor order's `ticket_contacts` array.
 2. **Inactive/canceled sponsor records** — badges from companies whose sponsor order was canceled.
 3. **Non-business badges** — badge types `student`, `press`, `guest`, `exhibitor` (non-sponsor), etc.
 4. **CRM-disqualified accounts** — badge companies whose CRM account has a non-null `disqualified_reason`.

 Surviving badges are qualified non-sponsor leads. For each:

- If a CRM account exists for the company → `crm_account_action: "update_existing"`.
- If no CRM account exists → `crm_account_action: "create_account"`.
- If the contact does not exist in CRM contacts → `crm_contact_action: "create_contact"`.
- If the contact already exists in CRM → `crm_contact_action: "update_existing"` and set `existing_contact_id`.
- All qualified leads get `campaign_member_action: "add_campaign_member"`.
- Each qualified lead gets the event's `lead_opportunity_amount` in USD.

 ## Trade-Show Prospecting

 When working with trade-show exhibitors:

 1. Fetch exhibitors, meeting interest, CRM accounts, and policies.
 2. Use the **prospecting policy** `qualification_note` and **exhibitor descriptions** to decide whether each exhibitor builds target platforms or is only adjacent.
 3. **Platform enums** come from the policy (`AUV`, `ROV`, `Underwater Camera`). An exhibitor can have multiple platforms.
 4. Qualify exhibitors that manufacture or OEM-build the target platform types (robotics, cameras, etc.).
 5. Exclude distributors, service-only firms, sensor-only vendors, and research-only organizations using the appropriate exclusion reasons.

 ### Priority Tiers

 When priority rules are specified:

- **A**: demo-requested qualified leads with score ≥ threshold (often 90). Opportunity estimate: high (e.g., $120,000).
- **B**: demo-requested qualified leads with score between a lower and upper bound. Opportunity estimate: medium (e.g., $90,000).
- **C**: all other qualified leads. Opportunity estimate: low (e.g., $50,000).

 If no explicit tier rules are given, use meeting-interest scores and demo requests to infer tiers: score ≥ 90 → A, score ≥ 80 → B, else C.

 ### Ranking

 When ranking is required, sort by: demo request first (true before false), then interest score descending, then broader platform coverage (more platforms first), then company name ascending.

 ## Import Batch Preparation

 Processing a raw contact import batch:

 1. **Normalize** every raw contact (email lowercase+trim, phone digits only).
 2. **Deduplicate** by normalized email. For each duplicate group, keep the row with the earliest `captured_at` timestamp. Track removed row IDs per duplicate key.
 3. **Check suppression**: compare normalized email and phone against the batch's suppression list. Mark matching rows as suppressed and remove them.
 4. **Remove unusable**: rows with both email and phone empty/missing after normalization.
 5. **CRM cross-reference** survivors:
    - Match by company name against CRM accounts to find `existing_account_id`.
    - Match by normalized email against CRM contacts to find `existing_contact_id`.
    - Determine `crm_action`: `"create_account"` (no CRM account), `"update_existing"` (CRM account exists), `"no_import"` (no usable data), or `"suppress"` (matched suppression).
 6. **Build clean_contacts** from survivors with normalized fields, using the winning row's data.
 7. **Count actions** for import_action_totals across all original rows (not just survivors).
 8. **Campaign member import count** = number of surviving clean contacts.

 ## Campaign Member Reconciliation

 When reconciling campaign members for an event:

- Existing campaign members whose status matches the determined outcome → `no_action`.
- Existing campaign members needing a status change → `update` with the new `target_status`.
- New attendees (not in campaign members) → `create`.
- Excluded records → `no_import`.
- `target_status` values: `attended_sponsor`, `registered_sponsor`, `attended`, `excluded`.
- Subject keys should uniquely identify an account-contact pair.

 ## Exclusion Tracking

 Count exclusions by reason:
- `sponsor_attendee`: badge from a sponsor company or sponsor ticket contact.
- `non_business_badge`: badge_type is student, press, guest, etc.
- `existing_disqualified`: CRM account has a non-null `disqualified_reason`.
- `missing_contact`: badge has no email and no phone.
- `inactive_sponsor_record`: canceled sponsor order for the badge's company.

 ## Sorting Conventions

 Unless an answer template specifies otherwise:

- Account/company lists: ascending by `account_name` or `company_name`.
- Badge lists: ascending by `badge_id`.
- Row lists: ascending by `row_id`.
- Contact lists: by `company_name` ascending, then `contact_name` ascending.
- Ranked lists: by explicit rank field ascending.
- Platform lists within an item: AUV, ROV, Underwater Camera enum order.

 ## Key API Endpoint Patterns

- **Event detail**: `GET /api/events/{event_id}` — provides dates, opportunity amounts, follow-up timing.
- **Orders / sponsor packages**: `GET /api/events/{event_id}/orders` — sponsor commitments with amounts and contacts.
- **Badges**: `GET /api/events/{event_id}/badges` — scanned attendee records.
- **Invoices**: `GET /api/finance/invoices?event_id={event_id}` — payment status for sponsor orders.
- **CRM accounts**: `GET /api/crm/accounts` — existing CRM account records with status and disqualification info.
- **CRM contacts**: `GET /api/crm/contacts` — existing CRM person records.
- **Campaign members**: `GET /api/crm/campaign_members?event_id={event_id}` — existing event participation records.
- **Opportunities**: `GET /api/crm/opportunities?event_id={event_id}` — sponsor-related sales opportunities.
- **Trade shows**: `GET /api/tradeshows/{show_id}`, plus exhibitor and meeting-interest sub-resources.
- **Import batches**: `GET /api/import_batches/{batch_id}`, plus raw_contacts and suppression sub-resources.
- **Policies**: `GET /api/policies` — controlled vocabularies and qualification rules.

 ## General Principles

- Always read the answer template first to understand the exact output shape.
- Use the policy endpoint for controlled enum values rather than hardcoding.
- When in doubt between two interpretations, prefer the one that keeps the output more structured and complete.
- Check CRM accounts for disqualification (`disqualified_reason` not null) before including in qualified lists.
- Check CRM contacts for `opted_out` status before including as contactable leads.
- Follow-up date calculations: end_date + corresponding followup_days_after_end from event data.
- Nulls in JSON output: use `null` (not the string "null") for absent account IDs, contact IDs, and invoice IDs.
- Empty strings: use `""` for absent emails and phones after normalization.
