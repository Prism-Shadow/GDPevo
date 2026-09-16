---
name: harborcrm-task-solver
description: "HarborCRM API task solver for event CRM handoff, trade show prospecting, and import batch preparation. Use when the task involves: (1) Fetching data from HarborCRM public API endpoints (events, trade shows, CRM, finance, imports, policies), (2) Cross-referencing CRM accounts, contacts, opportunities, campaign members, sponsor orders, invoices, badges, exhibitors, or import batches, (3) Producing a JSON output that conforms to a provided answer template, (4) Post-event CRM reconciliation or lead handoff, (5) Trade show exhibitor prospecting and lead qualification, (6) Import batch deduplication, suppression, and CRM import preparation. Trigger on mentions of HarborCRM, event_id, show_id, batch_id, sponsor_statuses, qualified_lead_accounts, campaign_member_actions, badge_decisions, crm_action, clean_contacts, ranked_leads, or answer_template.json with HarborCRM data."
license: MIT
compatibility: deepagents-code
---

# HarborCRM Task Solver

Solve HarborCRM data-processing tasks by fetching the answer template first, then all relevant API data in parallel, then cross-referencing, classifying, and normalizing to produce a single sorted JSON output.

## Core Workflow

1. Read `input/payloads/answer_template.json` — let it define every field and value constraint.
2. Read `input/prompt.txt` — extract the event_id, show_id, or batch_id and determine the task type.
3. Fetch all API endpoints listed in the prompt in parallel, using the base URL provided by the runner.
4. Fetch `GET /api/policies` — it holds configuration rules for thresholds, amounts, and qualification.
5. Process the data following the task-type rules below.
6. Produce one JSON object matching the template exactly; no prose outside the JSON.

## API Reference

See [references/api_endpoints.md](references/api_endpoints.md) for all endpoint shapes, URL patterns, and field definitions.

## Domain Rules

See [references/domain_model.md](references/domain_model.md) for entity relationships, classification logic, matching rules, deduplication, normalization, sorting conventions, and CRM action counting.

## Contact Normalization

Use [scripts/normalize.py](scripts/normalize.py) to normalize emails (lowercase, trim) and phones (digits only) consistently:

```
echo '{"email":" User@Example.Com ","phone":"+1 (415) 555-0188"}' | python scripts/normalize.py
```

Or import the functions directly in your own code.

## Task Type 1: Event CRM Handoff

Triggered when the prompt references an `event_id`, `orders`, `badges`, `invoices`, `campaign_members`, and expects sponsor statuses plus qualified lead accounts.

### Data to Fetch (all in parallel)

- `GET /api/events/{event_id}`
- `GET /api/events/{event_id}/orders`
- `GET /api/events/{event_id}/badges`
- `GET /api/finance/invoices?event_id={event_id}`
- `GET /api/crm/accounts`
- `GET /api/crm/contacts`
- `GET /api/crm/opportunities`
- `GET /api/crm/campaign_members?event_id={event_id}`
- `GET /api/policies`

### Processing Steps

1. **Build sponsor index** from orders. Mark orders with status `cancelled` as inactive — they still own their attendees but do not appear in `sponsor_statuses`.

2. **Classify sponsor status** by cross-referencing each active order with its invoice (match by `invoice_id`):
   - Order `confirmed` + invoice fully paid (`paid_amount == total_amount`) → `paid_deferred`
   - Order `confirmed` + invoice not fully paid → `open_invoice`
   - Order `pending` or `draft` (any invoice state or none) → `proposal_only`

3. **Classify every badge** into one of four categories:
   - Company matches any sponsor account (including cancelled sponsors) → `sponsor_attendee`
   - `badge_type` is neither `business` nor `sponsor` → `non_business_badge`
   - Company matches a CRM account with `status` = `disqualified` → `existing_disqualified`
   - Everything else → `qualified_non_sponsor_lead`

4. **Build qualified lead accounts** from qualified_non_sponsor_lead badges:
   - Group by company. Match company to CRM account by name (case-insensitive, trimmed).
   - Match found → `crm_account_action`: `update_existing`, with the matched `account_id`.
   - No match → `crm_account_action`: `create_account`, `account_id`: null.
   - `crm_contact_action`: `create_contact` (event handoff always creates contacts for new leads).
   - `campaign_member_action`: `add_campaign_member`.
   - Primary contact: the first person from that company among qualified badges. Normalize their email and phone.
   - `opportunity_amount`: the event's `lead_opportunity_amount` (from the event detail).

5. **Compute follow-up dates**:
   - `lead_due_date` = `event.end_date` + `event.lead_followup_days` calendar days, formatted YYYY-MM-DD.
   - `sponsor_finance_due_date` = `event.end_date` + `event.sponsor_followup_days` calendar days, formatted YYYY-MM-DD.

6. **Counts**:
   - `lead_task_count` = number of qualified lead accounts.
   - `sponsor_finance_task_count` = number of sponsors with status `open_invoice` or `proposal_only`.
   - `sponsor_finance_accounts` = list of account names for those sponsors, sorted ascending.

7. **CRM action counts**: sum `create_account` / `update_existing` / `create_contact` / `update_existing` / `add_campaign_member` across all handoff records.

8. **Excluded records**: one entry per excluded badge with `company_name`, `contact_name`, and reason.

9. **Sponsor revenue totals**: sum `package_amount` by status; `open_invoice_balance` = sum of `open_balance` for open_invoice sponsors.

## Task Type 2: Trade Show Prospecting

Triggered when the prompt references a `show_id`, `exhibitors`, `meeting_interest`, platform enums (`AUV`, `ROV`, `Underwater Camera`), and expects ranked qualified leads.

### Data to Fetch (all in parallel)

- `GET /api/tradeshows/{show_id}`
- `GET /api/tradeshows/{show_id}/exhibitors`
- `GET /api/tradeshows/{show_id}/meeting_interest`
- `GET /api/crm/accounts`
- `GET /api/crm/contacts`
- `GET /api/policies`

### Processing Steps

1. **Read policy configuration**: `prospecting_platforms` (list of qualifying platform strings), priority tier score thresholds (typically tier A: 90, tier B: 80), and opportunity amounts per tier (common values: A=120000, B=90000, C=50000).

2. **Join meeting interest to exhibitors** by `company_id`. An exhibitor without a meeting-interest record has `requested_demo`: false and `interest_score`: 0.

3. **Qualify exhibitors**:
   - `relationship_type` must be `manufacturer`.
   - At least one platform in the exhibitor's `platforms` list must appear in the policy's `prospecting_platforms`.
   - All others go to excluded list.

4. **Map exclusion reasons** from `relationship_type`:
   - `distributor` → `distributor_only`
   - `service_provider` → `service_only`
   - `sensor_vendor` → `sensor_vendor_only` (or `sensor_only` — check the template/policies for which form is required)
   - `research` → `research_only`

5. **Assign priority tier** using meeting interest and policy thresholds:
   - `A`: `requested_demo` is true AND `interest_score` >= tier A threshold (typically 90).
   - `B`: `requested_demo` is true AND `interest_score` >= tier B threshold (typically 80).
   - `C`: all other qualified exhibitors.

6. **Map opportunity amounts** from the policy tier definitions.

7. **CRM matching**: match `company_id` to CRM accounts by `company_id`. Set `crm_action` to `update_existing` if found, `create_account` if not. Set `crm_account_id` to the matched account's `account_id` or null. Excluded exhibitors get `crm_action`: `no_import`.

8. **Rank qualified leads** (highest priority first):
   1. `requested_demo` = true before false.
   2. `interest_score` descending.
   3. Platform count (number of qualifying platforms) descending.
   4. `company_name` ascending (alphabetical tiebreaker).

9. **Platform list ordering** within each item: `AUV`, `ROV`, `Underwater Camera` (the enum order from the template).

10. **Compute aggregate counts**: qualified total, per-platform counts, per-tier counts, excluded total.

## Task Type 3: Import Batch Preparation

Triggered when the prompt references a `batch_id`, `raw_contacts`, `suppression`, and expects `clean_contacts` with `crm_action` decisions.

### Data to Fetch (all in parallel)

- `GET /api/import_batches/{batch_id}`
- `GET /api/import_batches/{batch_id}/raw_contacts`
- `GET /api/import_batches/{batch_id}/suppression`
- `GET /api/crm/accounts`
- `GET /api/crm/contacts`
- `GET /api/policies`

### Processing Steps

1. **Normalize all raw contacts**: run every email and phone through the normalization functions (see [scripts/normalize.py](scripts/normalize.py)).

2. **Build suppression set**: collect all normalized emails and normalized phones from the suppression endpoint entries.

3. **Deduplicate**: group raw contact rows by `email:{normalized_email}` (skip rows with empty normalized email from grouping). Within each group:
   - **Winner**: row with the most recent `captured_at` timestamp.
   - **Tiebreaker**: lowest `row_id` alphanumerically.
   - All non-winner rows are marked for removal with reason `duplicate`.

4. **Apply removals** (three reasons):
   - `duplicate`: non-winner rows from the dedup step.
   - `missing_contact`: rows where `contact_name` is empty, null, or only whitespace.
   - `suppressed`: rows whose normalized email or normalized phone appears in the suppression set.
   A single row can be removed for only one reason — check in order and keep the first match.

5. **Clean contacts**: the surviving rows after removals.
   - `clean_contact_id` = the winning `source_row_id` (same as `row_id` for non-duplicate survivors).
   - Preserve normalized email and phone from the winning row.

6. **CRM cross-reference** for each clean contact:
   - Match account by `company_name` (case-insensitive, trimmed comparison).
   - Match found and account status is `active` → `crm_action`: `update_existing`, `existing_account_id` populated.
   - No match → `crm_action`: `create_account`, `existing_account_id`: null.
   - Match contact by normalized email within the matched account. If not found, try normalized phone. Populate `existing_contact_id` if a match is found.

7. **Import action totals**:
   - `create_account`: clean contacts with `crm_action` = `create_account`.
   - `update_existing`: clean contacts with `crm_action` = `update_existing`.
   - `no_import`: rows removed for `duplicate` or `missing_contact` (not suppressed).
   - `suppress`: rows removed for `suppressed`.

8. **campaign_member_import_count** = number of clean contacts.

9. **Sort**: clean_contacts by `clean_contact_id` ascending; duplicate_keys by `key` ascending; removed_rows by `row_id` ascending.

## Key Output Rules

- **Read the answer template first.** Use its field names, enum values, and sorting instructions exactly as specified. If a template sorting rule differs from the conventions in the domain model, follow the template.
- **All USD amounts**: integers.
- **All dates**: YYYY-MM-DD format.
- **All counts**: integers.
- **Empty phone/email**: use `""` (empty string), not null, unless the template specifically requires null.
- **Do not add fields** not declared in the answer template.
- **Return one JSON object only**, with no explanatory prose outside it.
