# HarborCRM Task Solving Skill

## 1. Preparation
- Read `MANIFEST.md`, `environment_access.md`, and the staged train prompt/answer template.
- **Do not assume train tasks share the same schema.** Each train task may use a different event/show/batch and a different JSON template.
- The remote base URL is `http://34.46.77.124:8001`. Do not use localhost unless explicitly overridden.

## 2. Data Fetching Rules
- Query **only** the endpoint paths and entity IDs explicitly named in the prompt.
- Do **not** call global list/index endpoints to discover unrelated IDs (e.g., do not scan `/api/tradeshows` to find test shows).
- For each task, fetch **all** explicitly listed endpoints before building the answer.

## 3. Event / Trade-Show Handoff Tasks (e.g., neuralops_2026, edgeai_field_2026)

### 3.1 Sponsors
- Use **orders** and **sponsor_packages** to identify sponsors.
- Use **invoices** to determine finance state.
- Map invoice `status` to controlled enum values:
  - `paid_deferred` — invoice status is `"paid_deferred"`.
  - `open_invoice` — invoice status is `"open"`.
  - `proposal_only` — no invoice exists and order status is `"proposal_sent"`.
  - Exclude canceled/inactive sponsors from `sponsor_statuses`.
- `open_balance` for an open invoice = `amount - paid_amount`.
- `sponsor_revenue_totals` group by the same status enum.
- `sponsor_finance_accounts` should list only sponsors needing follow-up (open_invoice and proposal_only), sorted ascending.

### 3.2 Badges (Leads)
- Iterate every badge.
- Exclude:
  - **sponsor contacts** (any badge from a sponsor company),
  - **non-business badges** (`student`, `press`, etc.),
  - **contacts whose CRM account is disqualified**,
  - **inactive/canceled sponsor records**.
- Qualified non-sponsor leads are the remaining business attendees.
- Use the event’s `lead_opportunity_amount` for each qualified lead.

### 3.3 Normalization
- **Email**: lowercase, trim whitespace.
- **Phone**: strip **all** non-digit characters. Then ensure the country code is present:
  - If the badge/record `country` is `"United States"` (or inferred US) and the stripped string does **not** start with `1`, prepend `1`.
  - If the badge already supplies a leading `1` (e.g., `"+1 206 555 0177"`), keep it.
  - Examples:
    - `"(415) 555-0188"` → `"14155550188"`
    - `"+1 907 555 0108"` → `"19075550108"`
    - `"+1 (206) 555-0150"` → `"12065550150"`

### 3.4 Campaign Members
- Reconcile existing `campaign_members` with badges.
- If a sponsor has a campaign member but no badge scan for the contact, still update the member to `attended_sponsor` when the event is completed and the sponsor is active.
- Sort `campaign_member_actions` by `subject_key` ascending using standard string ordering.

### 3.5 Follow-up Dates
- `lead_due_date` = `end_date + followup_days_after_end`
- `sponsor_finance_due_date` = `end_date + sponsor_followup_days_after_end`

## 4. Prospecting Tasks (e.g., aquafarm_robotics_2026, marinesense_2026)

### 4.1 Qualification
- Read the exhibitor `description` and classify:
  - **Qualified**: makes or OEM-builds robotics or underwater-camera platforms.
  - **Excluded**: distributors, service-only, sensor-only, research-only.
- Assign platforms from the enum `["AUV", "ROV", "Underwater Camera"]` based on explicit description text.
  - If a company builds ROVs **with camera arrays**, include **both** `ROV` and `Underwater Camera` when the camera is called out as a built-in/integrated platform.

### 4.2 Ranking & Tiers
- Sort qualified leads by:
  1. `requested_demo` (true first)
  2. `interest_score` descending
  3. Broader platform coverage (more platforms first)
  4. `company_name` ascending
- Priority tiers:
  - **A** ($120,000): demo requested + score ≥ 90
  - **B** ($90,000): demo requested + score ≥ 80
  - **C** ($50,000): all other qualified leads

### 4.3 CRM Action
- `update_existing` if `crm_account_id` is present in exhibitor data.
- `create_account` if absent.

### 4.4 Excluded Exhibitors
- Populate `relationship_type` and `exclusion_reason` from controlled enums.
- Sort by `company_name` ascending.

## 5. Batch Import Tasks (e.g., fall_webinar_import)

### 5.1 Deduplication
- Normalize email (lowercase, trim) and use it as the duplicate key.
- When multiple rows share the same normalized email, choose a **winner**:
  - Prefer the row with the **earlier** `captured_at` or the **lower** `row_id` when timestamps tie.
- The `removal_summary.removed_rows` **must include every removed row**: duplicates, suppressed, and missing-contact rows.

### 5.2 Suppression
- Match raw contacts against the suppression list by **normalized email** or **normalized phone**.
- Remove matches with reason `"suppressed"`.

### 5.3 Missing Contact Removal
- Remove rows where **both** email and phone are blank/empty after normalization.
- Reason: `"missing_contact"`.

### 5.4 Clean Contacts
- For each surviving row, set:
  - `clean_contact_id` = winning `row_id`
  - `existing_account_id` = matching CRM account ID (by company name/domain), or `null`
  - `existing_contact_id` = matching CRM contact ID **only if the contact name/email actually matches**; otherwise `null`
  - `crm_action`:
    - `update_existing` when the account exists
    - `create_account` when no account matches

### 5.5 Counts
- `import_action_totals` reflect the `crm_action` values of the surviving clean contacts.
- `campaign_member_import_count` = number of surviving clean contacts.

## 6. Sorting & Ordering
- Adhere strictly to every `ordering` rule in the answer template.
- Common sorts:
  - `company_name` / `account_name` ascending
  - `rank` ascending (1-based contiguous)
  - `badge_id` ascending
  - `subject_key` ascending (standard string order)
  - `row_id` ascending
- Sorting errors are a frequent cause of partial credit.

## 7. Test-Specific Rules
- Do **not** query or inspect entity IDs that are not explicitly named in the current staged prompt.
- Do **not** call global list/index endpoints to discover other events, shows, batches, tasks, or IDs.
- Query **only** endpoint paths and entity IDs explicitly named in the staged prompt.

## 8. Common Pitfalls
- **Do not mix up tasks.** Each train task uses a different event/show/batch ID and schema. Verify the ID in the prompt before querying.
- **Do not omit removed rows.** `removed_rows`, `excluded_records`, etc. must be exhaustive.
- **Do not forget country-code normalization for US phone numbers.** The CRM stores digits-only phones with country codes.
- **Do not set `existing_contact_id` unless the contact truly matches.** An existing account does not imply an existing contact.
- **Do not include sponsor contacts in qualified leads.** Any badge from a sponsor company is excluded.
- **Do not update campaign members for excluded/disqualified accounts** unless the template explicitly requires it.
