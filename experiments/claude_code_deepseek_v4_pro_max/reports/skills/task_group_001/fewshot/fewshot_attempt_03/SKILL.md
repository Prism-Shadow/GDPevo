# HarborCRM Skill

## Environment

Base URL: `GDPEVO_ENV_BASE_URL` (supplied by runner). All API calls use this as the root. Never use localhost unless the env var points there.

## API Endpoints Reference

| Resource | Endpoint |
|---|---|
| Policies | `GET /api/policies` |
| Events | `GET /api/events/{event_id}` |
| Event orders | `GET /api/events/{event_id}/orders` |
| Event badges | `GET /api/events/{event_id}/badges` |
| Sponsor packages | `GET /api/events/{event_id}/sponsor_packages` |
| Invoices | `GET /api/finance/invoices?event_id={event_id}` |
| CRM accounts | `GET /api/crm/accounts` |
| CRM contacts | `GET /api/crm/contacts` |
| CRM opportunities | `GET /api/crm/opportunities` |
| Campaign members | `GET /api/crm/campaign_members?event_id={event_id}` |
| Trade shows | `GET /api/tradeshows` |
| Trade show exhibitors | `GET /api/tradeshows/{show_id}/exhibitors` |
| Meeting interest | `GET /api/tradeshows/{show_id}/meeting_interest` |
| Import batches | `GET /api/import_batches` |
| Raw contacts | `GET /api/import_batches/{batch_id}/raw_contacts` |
| Suppression list | `GET /api/import_batches/{batch_id}/suppression` |

Always start by fetching `/api/policies` — it contains follow-up offset days, campaign codes, lead opportunity amounts, priority-tier amount mappings, platform inclusion lists, and other configuration.

## Task Type: Event Reconciliation

Used when the task asks for post-event CRM handoff involving sponsors, badge scans, and lead qualification.

### Sponsor Status Classification

For each sponsor order/package, check invoices to determine status:

- **paid_deferred**: An invoice exists for the sponsor AND `paid_amount >= package_amount` (fully paid).
- **open_invoice**: An invoice exists AND `0 < paid_amount < package_amount` (partially paid). Report `open_balance = package_amount - paid_amount`.
- **proposal_only**: No invoice exists for this sponsor package. `invoice_id` is null, `paid_amount` is 0.

Only include active sponsor records. Skip canceled/inactive sponsor packages.

### Revenue Totals

Sum `package_amount` by status into `sponsor_revenue_totals` (integer USD). For open_invoice, include a separate `open_invoice_balance` sum of all `open_balance` values.

### Lead Qualification from Badge Scans

A badge scan is a **qualified non-sponsor lead** when ALL of:
1. The contact's company is NOT a sponsor company
2. The badge type is a business badge (exclude: student, press, exhibitor-only, staff, etc.)
3. The CRM account is NOT already disqualified
4. The badge is for an active attendee (not canceled)

### Exclusion Reasons (badge-level)

| Reason | When to Apply |
|---|---|
| `sponsor_attendee` | Contact works for a company that is an active event sponsor |
| `non_business_badge` | Badge type is not a business/professional badge |
| `existing_disqualified` | CRM account exists and is marked disqualified |
| `inactive_sponsor_record` | Sponsor package is canceled/inactive |

### CRM Action Determination

For each qualified lead, cross-reference CRM accounts and contacts:
- **Account**: If an account with matching name/ID exists → `update_existing`. Otherwise → `create_account`.
- **Contact**: If a contact with matching normalized email exists in CRM → `update_existing`. Otherwise → `create_contact`.
- **Campaign member**: If not already a campaign member for this event → `add_campaign_member`.

### Lead Opportunity Amount

Use the event's lead opportunity amount from the event data or policies. All qualified non-sponsor leads get this same amount. `lead_pipeline_total` = sum of all qualified leads' opportunity amounts.

### Follow-up Dates

Computed from the event's end date plus policy-defined offset days:
- **Lead follow-up due date**: event_end_date + lead_followup_offset_days (from policy)
- **Sponsor finance due date**: event_end_date + sponsor_finance_offset_days (from policy)

### Sponsor Finance Follow-up

`sponsor_finance_accounts` lists account names of sponsors with status `open_invoice` or `proposal_only` (unpaid/partially-paid), sorted ascending. `sponsor_finance_task_count` = length of this list.

### CRM Action Counts

Count each CRM action across all qualified leads:
- `accounts_create`, `accounts_update`
- `contacts_create`, `contacts_update`
- `campaign_members_create`, `campaign_members_update`

### Badge-Only Contact Normalization

For contacts that appeared only via badge scan (no CRM contact record), normalize:
- **email**: lowercase, trim. Empty string `""` if not provided.
- **phone**: digits only (strip all non-digit characters). Empty string `""` if not provided.

## Task Type: Trade Show Prospecting

Used when the task asks for qualified exhibitor lists from a trade show for a campaign.

### Qualification

An exhibitor qualifies when their business type is an OEM/manufacturer of platforms covered by the campaign policy. Exclude:
- `distributor_only` — company is a distributor, not a manufacturer
- `service_only` — company provides services only
- `sensor_vendor_only` / `sensor_only` — company only sells sensors/components
- `research_only` — academic/research institution

### Platform Matching

Platforms must be from the controlled enum: `AUV`, `ROV`, `Underwater Camera`. Sort platform lists in this enum order. Only include platforms the exhibitor actually covers that are also in the campaign's target platform set.

### Priority Tier Assignment

Based on demo request and meeting interest score:
- **A**: `requested_demo == true` AND `interest_score >= 90`
- **B**: `requested_demo == true` AND `interest_score >= 80`
- **C**: all other qualified leads

### Opportunity Sizing

Map priority tier to USD amount using policy or task-specified mappings:
- A → 120000
- B → 90000
- C → 50000

### CRM Action (Trade Show)

- If the exhibitor's company has an existing CRM account → `update_existing`, include `crm_account_id`
- If no CRM account exists → `create_account`, `crm_account_id` is null
- Excluded exhibitors → `no_import`

### Ranking (when specified)

Sort qualified leads by:
1. `requested_demo == true` first (demo requests before non-demo)
2. `interest_score` descending
3. Platform count descending (more platforms = broader coverage = higher rank)
4. `company_name` ascending (alphabetical tiebreaker)

Assign contiguous 1-based `rank`.

### Aggregate Counts

- `qualified_total`: count of qualified exhibitors
- `excluded_count` / `excluded_near_misses_total`: count of excluded exhibitors
- `platform_counts`: per-platform count across qualified exhibitors
- `priority_counts`: per-tier count (A, B, C) — include 0 for empty tiers
- `existing_crm_overlap_count`: count of qualified leads with existing CRM accounts
- `existing_crm_overlap_account_ids`: their account IDs, sorted ascending
- `total_estimated_opportunity_usd`: sum of all opportunity estimates

## Task Type: Batch Import

Used when preparing raw import contacts for CRM ingestion.

### Deduplication

Group raw contacts by normalized email (lowercase, trimmed). Within each group, pick one winner:
- Prefer the row with the most complete contact data (has both email AND phone)
- If tied, prefer the earliest `captured_at` timestamp
- If still tied, prefer lowest `row_id` lexicographically

Removed duplicates are tracked in `duplicate_summary` with key format `email:{normalized_email}`.

### Suppression

Check each raw contact against the suppression list. A contact is suppressed if their normalized email matches a suppression entry. Suppressed contacts go to `removal_summary` with reason `suppressed`.

### Unusable Contacts

A contact is unusable (`missing_contact`) if it has no email AND no phone after normalization.

### Removal Summary

- `unusable_removed_count`: count of `missing_contact` rows
- `suppressed_removed_count`: count of `suppressed` rows
- `removed_rows`: all removed rows (duplicates, suppressed, unusable) sorted by `row_id` ascending

### CRM Action for Clean Contacts

For each surviving clean contact:
- If company matches an existing CRM account → `update_existing`, set `existing_account_id`
- If no CRM account match → `create_account`, `existing_account_id` is null
- `existing_contact_id`: the matching CRM contact ID if email matches, otherwise null

### Import Action Totals

Count across ALL raw contacts (not just clean):
- `create_account`: clean contacts needing new accounts
- `update_existing`: clean contacts matching existing accounts
- `no_import`: rows removed as unusable (missing_contact)
- `suppress`: rows removed as suppressed

### Campaign Member Count

`campaign_member_import_count` = number of clean contacts (surviving after dedup, suppression, and unusable removal).

## General Rules

### Data Normalization

- **Email**: Always lowercase, trim whitespace. Use `""` (empty string) when no email provided — never null for normalized fields.
- **Phone**: Strip ALL non-digit characters. US/international leading digits are preserved. Use `""` when no phone provided.
- **Dollar amounts**: Always integer USD. No decimal places, no cents.

### Sorting Conventions

- Sponsor lists: by `account_name` ascending (case-sensitive, lexicographic)
- Qualified lead account lists: by `account_name` ascending
- Excluded records: by `company_name` ascending, then `contact_name` ascending
- Badge decisions: by `badge_id` ascending
- Campaign member actions: by `subject_key` ascending
- Clean contacts: by `clean_contact_id` ascending
- Duplicate keys: by `key` ascending
- Removed rows: by `row_id` ascending
- Platform lists within items: in enum order (`AUV`, `ROV`, `Underwater Camera`)
- Account ID lists: ascending

### Null vs Empty

- Use `null` for object references that don't exist (e.g., `invoice_id`, `existing_account_id`, `existing_contact_id`, `crm_account_id`)
- Use `""` (empty string) for missing normalized text fields (`normalized_email`, `normalized_phone`, `email`, `phone`)
- Use `null` for `exclusion_reason` when the item is NOT excluded

### Controlled Vocabularies

Always use the exact string values from the answer template or listed in this skill. Do not invent new statuses, reasons, or action names.

### Workflow Order

1. Fetch policies first — they define offsets, thresholds, and configuration
2. Fetch all relevant entity endpoints in parallel (event/show, CRM, finance)
3. Cross-reference: match badges to accounts, invoices to sponsors, contacts to CRM
4. Classify each record (sponsor status, lead qualification, exclusion reason)
5. Compute aggregates and follow-up data
6. Sort all lists per the sorting rules
7. Output JSON conforming to the answer template — no extra keys, no prose outside JSON
