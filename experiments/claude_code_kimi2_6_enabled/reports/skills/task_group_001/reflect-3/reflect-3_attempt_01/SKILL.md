# HarborCRM Task Solving Skill

## Overview

This skill describes the workflow for solving HarborCRM data-reconciliation and CRM-import tasks. Each task requires querying a shared HarborCRM REST API, applying business rules from the prompt and from policy metadata, and producing a single JSON object that matches a strict answer template.

## API Base URL

- Use the base URL supplied by the task runner (e.g. `http://34.46.77.124:8001`).
- Do **not** start a local environment or read env source files.
- Only query endpoints and entity IDs explicitly named in the task prompt.

## General Workflow

1. **Read the prompt** – identify the event / batch / show ID and the required output schema.
2. **Fetch all relevant data** from the named API endpoints. Common endpoints include:
   - `/api/events/{event_id}`
   - `/api/events/{event_id}/orders`
   - `/api/events/{event_id}/badges`
   - `/api/events/{event_id}/sponsor_packages`
   - `/api/finance/invoices?event_id={event_id}`
   - `/api/crm/accounts`
   - `/api/crm/contacts`
   - `/api/crm/opportunities`
   - `/api/crm/campaign_members?event_id={event_id}`
   - `/api/tradeshows/{show_id}/exhibitors`
   - `/api/tradeshows/{show_id}/meeting_interest`
   - `/api/import_batches/{batch_id}/raw_contacts`
   - `/api/import_batches/{batch_id}/suppression`
   - `/api/policies`
3. **Apply business rules** (see sections below).
4. **Produce JSON** matching the answer template exactly. No extra keys, no prose outside the JSON.
5. **Respect sorting rules** explicitly stated in each template.

## Sponsor Reconciliation Rules

- Use `sponsor_packages` (or `orders`) as the authoritative list of sponsor accounts.
- Map each sponsor to a status using finance invoices:
  - `paid_deferred` – invoice status is `paid_deferred`.
  - `open_invoice` – invoice status is `open` (unpaid or partially paid).
  - `proposal_only` – order status is `proposal_sent` and there is no invoice.
- **Exclude** inactive/canceled sponsor records from the sponsor status list.
- For open invoices, compute `open_balance = amount - paid_amount`.
- Revenue totals are integer USD. `open_invoice_balance` is the sum of open balances.
- Unpaid sponsors (open invoice or proposal only) are finance follow-up targets.

## Lead Qualification Rules (Event Handoff)

- Qualified leads are **non-sponsor** attendees with business badges.
- Exclude:
  - Sponsor contacts (any badge from a sponsoring company).
  - Non-business badges (`student`, `press`, etc.).
  - Contacts whose CRM account status is `disqualified`.
- Use the event's `lead_opportunity_amount` for each qualified lead account.
- If a company already exists in CRM, mark `crm_account_action: update_existing`; otherwise `create_account`.
- If the contact already exists in CRM, mark `crm_contact_action: update_existing`; otherwise `create_contact`.
- Campaign member action is `add_campaign_member` for qualified leads.

## Contact Hygiene

- **Normalize email**: lowercase, trim whitespace. Empty string if missing / blank.
- **Normalize phone**: digits only (strip `+`, `-`, `(`, `)`, spaces, dots). Empty string if missing / blank.
- For US/Canada numbers that start with `1` after stripping `+`, keep the leading `1` (e.g. `+1 415 555 0101` → `14155550101`).

## Import Batch Cleaning (Duplicate / Suppression / Missing)

- **Duplicates**: group raw contacts by normalized email. Keep the earliest `captured_at` row as winner; remove the rest with reason `duplicate`.
- **Suppression**: remove any row whose normalized email or normalized phone appears in the suppression list. Reason: `suppressed`.
- **Missing contact**: remove rows with blank normalized email AND blank normalized phone. Reason: `missing_contact`.
- `crm_action` for surviving cleaned contacts:
  - `update_existing` if the company name matches an existing CRM account.
  - `create_account` otherwise.
  - `no_import` or `suppress` for removed rows (counted in `import_action_totals`).
- `campaign_member_import_count` = number of surviving cleaned contacts.

## Trade-Show Prospecting Rules

- Read exhibitor descriptions and the `prospecting` policy to decide qualification.
- Qualified exhibitors **build or OEM-build** target platforms (AUV, ROV, Underwater Camera).
- Exclude:
  - Distributors → `distributor_only`
  - Service-only providers → `service_only`
  - Sensor-only vendors (no platform manufacturing) → `sensor_only`
  - Research-only organizations → `research_only`
- Map each qualified exhibitor to applicable `platforms` enums, ordered: `AUV`, `ROV`, `Underwater Camera`.
- Priority tier rules (from prompt):
  - `A` for demo-requested qualified leads with score ≥ 90 (opportunity USD 120000).
  - `B` for demo-requested qualified leads with score ≥ 80 (opportunity USD 90000).
  - `C` for all other qualified leads (opportunity USD 50000).
- Rank qualified leads by: demo request first, then interest score descending, then broader platform coverage, then company name ascending.
- Existing CRM accounts get `crm_action: update_existing`; new ones get `create_account`.

## Campaign Member Actions

- For existing campaign members at the event, decide `action`:
  - `update` if current status is `registered_sponsor` and the attendee actually attended.
  - `no_action` if already `attended_sponsor` and no change needed.
  - `create` for new qualified non-sponsor leads.
- `target_status` values: `attended_sponsor`, `registered_sponsor`, `attended`, `excluded`.

## Sorting Rules (Critical)

- `sponsor_statuses` → by `account_name` ascending.
- `qualified_lead_accounts` → by `account_name` ascending.
- `excluded_records` → by `company_name` ascending, then `contact_name` ascending.
- `qualified_exhibitors` → by `company_name` ascending.
- `excluded_near_misses` → by `company_name` ascending.
- `ranked_leads` → by `rank` ascending (1-based contiguous).
- `clean_contacts` → by `clean_contact_id` ascending.
- `duplicate_keys` → by `key` ascending.
- `removed_rows` → by `row_id` ascending.
- `badge_decisions` → by `badge_id` ascending.
- `campaign_member_actions` → by `subject_key` ascending.
- `badge_only_contacts` → by `company_name` ascending.
- `existing_crm_overlap_account_ids` → CRM account IDs ascending.

## Due-Date Calculation

- `lead_due_date` = event `end_date` + `followup_days_after_end` days.
- `sponsor_finance_due_date` = event `end_date` + `sponsor_followup_days_after_end` days.
- Use calendar date arithmetic (simple date addition).

## Common Pitfalls

1. **Do not include canceled/inactive sponsors** in sponsor statuses.
2. **Do not include sponsor attendees** in qualified leads.
3. **Do not include press, student, or other non-business badges** in leads.
4. **Normalize emails and phones** consistently before deduplication or suppression checks.
5. **Use the exact enum values** from the template; do not invent new ones.
6. **Compute open balance** for open invoices as `amount - paid_amount`, not `deferred_amount`.
7. **Count all removed rows** (duplicate + suppressed + missing) in `removal_summary.removed_rows`, but the summary also needs separate `unusable_removed_count` and `suppressed_removed_count` tallies.
8. **Do not add extra top-level keys** or omit required keys.
9. **Opportunity totals** for non-sponsor leads = number of qualified leads × event `lead_opportunity_amount`.
10. For import batches, `import_action_totals` must include counts for all four actions (`create_account`, `update_existing`, `no_import`, `suppress`), even if some are zero.

## Output Convention

- Return **only** the JSON object. No markdown fences, no explanatory text.
- All monetary values are integers (USD).
- All dates are `YYYY-MM-DD`.
- All timestamps are ISO-8601 strings from the source data.
