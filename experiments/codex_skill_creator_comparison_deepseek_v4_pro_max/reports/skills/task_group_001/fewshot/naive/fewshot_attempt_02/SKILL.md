---
name: harbor-crm-handoff
description: Reusable patterns for HarborCRM post-event reconciliation, trade-show prospecting, and batch import cleaning. Use when a task references the HarborCRM API and an answer template with controlled vocabularies, policy-driven filtering, CRM cross-referencing, contact normalization, and deduplication.
---

# HarborCRM Handoff Skill

## Overview

This skill covers three HarborCRM workflow families that recur across the
training examples: post-event CRM reconciliation, trade-show exhibitor
prospecting, and batch import cleaning. Every task in this family shares a
core pattern: read the provided answer template, fetch data from the
HarborCRM REST API, apply policy rules, cross-reference existing CRM records,
normalize contact fields, and produce a JSON-only answer.

## General HarborCRM Patterns

### API Conventions

The HarborCRM REST API is served at a base URL the runner supplies as
`<TASK_ENV_BASE_URL>`. All endpoints return JSON. The `GET` only catalog of
public endpoints includes:

- `/api/events/{event_id}` – event details
- `/api/events/{event_id}/orders` – sponsor orders for the event
- `/api/events/{event_id}/badges` – badge scans
- `/api/events/{event_id}/sponsor_packages` – package pricing
- `/api/events/{event_id}/sponsors` – sponsor relationships
- `/api/finance/invoices?event_id={event_id}` – invoices linked to event
- `/api/crm/accounts` – all CRM accounts
- `/api/crm/contacts` – all CRM contacts
- `/api/crm/opportunities` – opportunity pipeline
- `/api/crm/campaign_members?event_id={event_id}` – existing campaign members
- `/api/tradeshows` – all tradeshow records
- `/api/tradeshows/{show_id}` – single tradeshow detail
- `/api/tradeshows/{show_id}/exhibitors` – exhibitors for a show
- `/api/tradeshows/{show_id}/meeting_interest` – interest scores and demo requests
- `/api/import_batches` – list of import batches
- `/api/import_batches/{batch_id}` – batch detail
- `/api/import_batches/{batch_id}/raw_contacts` – raw contact rows
- `/api/import_batches/{batch_id}/suppression` – suppression list for batch
- `/api/policies` – policy metadata (qualification rules, platform coverage, campaign codes)

Always fetch policies first — they define the qualification rules, controlled
vocabularies, and campaign metadata for the task.

### Template-First Workflow

1. Read the `answer_template.json` from `input/payloads/` first. Understand
   every required key, allowed enum value, and sort order.
2. Fetch all relevant API data.
3. Apply policy-driven qualification rules.
4. Cross-reference against `/api/crm/accounts` and `/api/crm/contacts` to
   decide `create_account` vs `update_existing`.
5. Build the output object field by field, matching the template exactly.
6. Do not add undeclared fields.
7. Return only the JSON object — no explanatory prose before or after it.

### Contact Normalization

Apply these transformations to every email and phone value:

- **Email**: trim whitespace, lowercase. If the value is null, missing, or an
  empty string after trimming, use `""` (empty string).
- **Phone**: strip all non-digit characters. If the result is empty or the
  original was null/missing, use `""` (empty string).

### CRM Cross-Reference

For every company or contact being evaluated:

1. Exact-match the company name against CRM accounts or exhibitor records.
2. If a match exists, use the CRM `account_id` and set `crm_action` to
   `update_existing`. If no match exists, set `crm_action` to `create_account`
   and `account_id` to `null`.
3. Contact-level matching uses the normalized email as the primary key.
   If a CRM contact already shares the same normalized email, set
   `existing_contact_id` to the CRM contact ID.

### Deduplication

When cleaning raw contact lists:

1. Build keys from the normalized email (format: `email:{normalized_email}`).
2. For rows sharing the same key, select one winner by source priority. The
   priority order is: `webinar_form` > `partner_upload` > `manual_upload` >
   `badge_scan` > `sponsor_form` > `exhibitor_form`.
3. For ties at the same source priority level, prefer the row with the earlier
   `captured_at` timestamp.
4. All non-winning duplicate rows are removed with reason `duplicate`.
5. Rows with `null` or empty `contact_name` and `email` are removed with
   reason `missing_contact`.
6. Rows whose email matches the batch's suppression list are removed with
   reason `suppressed`.

### Sorting Conventions

When the task or template specifies a sort order, apply it strictly:

- **account_name ascending**: case-insensitive lexicographic sort.
- **company_name ascending**: case-insensitive lexicographic sort.
- **contact_name ascending**: case-insensitive lexicographic sort.
- **badge_id / row_id / clean_contact_id ascending**: lexicographic string
  sort.
- **rank ascending**: numeric 1-based ordering.
- **Platform lists**: sort in the enum order declared in the template (e.g.
  `["AUV", "ROV", "Underwater Camera"]`).
- **Tiered multi-key sorts**: apply keys in the order stated. For example,
  "demo request first, then interest score descending, then platform count
  descending, then company name ascending" — sort demo=true rows before
  demo=false rows, within each group sort by score descending, etc.

---

## Workflow Family 1: Post-Event CRM Reconciliation

This pattern appears when a task asks to "audit the post-event CRM handoff" or
"reconcile badge scans, sponsor orders, and CRM campaign members."

### Data Sources

| Endpoint | Purpose |
|----------|---------|
| `/api/events/{event_id}` | Event name, dates |
| `/api/events/{event_id}/orders` | Sponsor orders with package amounts |
| `/api/events/{event_id}/badges` | Every badge scan at the event |
| `/api/events/{event_id}/sponsor_packages` | Package pricing by sponsor level |
| `/api/finance/invoices?event_id={event_id}` | Invoice state: paid amounts, open balances |
| `/api/crm/accounts` | Existing CRM account records |
| `/api/crm/contacts` | Existing CRM contact records |
| `/api/crm/campaign_members?event_id={event_id}` | Already-created campaign members |
| `/api/crm/opportunities` | Existing opportunities |
| `/api/policies` | Qualification rules, follow-up offsets, opportunity amounts |

### Sponsor Classification

Classify every sponsor order into one of three statuses:

| Status | Condition |
|--------|-----------|
| `paid_deferred` | Invoice exists and `paid_amount >= package_amount` (fully paid) |
| `open_invoice` | Invoice exists and `paid_amount < package_amount` (partially paid) |
| `proposal_only` | No invoice found for the order |

For `paid_deferred`: `open_balance` is 0.
For `open_invoice`: `open_balance = package_amount - paid_amount`.
For `proposal_only`: `paid_amount = 0`, `open_balance = 0`, `invoice_id = null`.

### Badge Classification

Each badge scan falls into one of three classes:

1. **sponsor_attendee**: The badge's company is a sponsor (active or
   inactive). Sponsor attendee badges do not generate new CRM accounts or
   opportunities.
2. **qualified_non_sponsor_lead**: The badge's company is not a sponsor,
   the badge type is a business badge (not press, student, or exhibitor-only),
   and the company is not already disqualified in CRM. These generate
   opportunities and CRM records.
3. **excluded**: Everything else — non-business badge types, companies already
   disqualified in CRM, missing contact info.

For excluded badges, use the controlled `exclusion_reason` values:

- `sponsor_attendee` — company is a sponsor
- `non_business_badge` — badge type is not a business badge
- `existing_disqualified` — CRM account has a disqualified status
- `missing_contact` — no usable contact name or email

### Campaign Member Actions

For every sponsor contact and every qualified lead, determine the campaign
member action:

- `no_action`: Already exists in campaign members and already has the correct
  status. No change needed.
- `create`: Not yet a campaign member, or exists but needs a different target
  status.
- `update`: Already a campaign member but with a different status. Set the
  new `target_status`.

Target status values:

- `attended_sponsor` — a sponsor contact who attended (badge scanned)
- `registered_sponsor` — a sponsor contact who registered but did not attend
- `attended` — a non-sponsor lead who attended

### Opportunity Assignment

For each qualified non-sponsor lead account, use the opportunity amount from
the event policy. The policy typically defines a per-lead amount (e.g. 40000,
20000). Multiply by the number of qualified leads from that account if the
policy specifies per-contact opportunities; otherwise assign one opportunity
per account.

### Follow-Up Dates

Derive follow-up due dates from the event date plus a policy-defined offset:

- Lead follow-up due date: event end date + lead follow-up offset days
- Sponsor finance follow-up due date: event end date + sponsor finance offset days

The policy specifies both offsets as integers.

---

## Workflow Family 2: Trade-Show Exhibitor Prospecting

This pattern appears when a task asks to "prepare a qualified lead list" or
"prospecting summary" for a trade-show campaign.

### Data Sources

| Endpoint | Purpose |
|----------|---------|
| `/api/tradeshows/{show_id}` | Show metadata |
| `/api/tradeshows/{show_id}/exhibitors` | All exhibitors with booth, country, website |
| `/api/tradeshows/{show_id}/meeting_interest` | Interest scores, demo requests per exhibitor |
| `/api/crm/accounts` | Existing CRM accounts for cross-reference |
| `/api/crm/contacts` | Existing CRM contacts |
| `/api/policies` | Qualification rules: target platforms, exclusion relationship types, priority tiering |

### Qualification Logic

The policy for the campaign defines which exhibitors qualify:

1. An exhibitor qualifies if its `relationship_type` is in the policy's
   target relationship types (typically `oem` or `manufacturer`).
2. An exhibitor qualifies only if it covers at least one platform listed in
   the policy's target platforms (`AUV`, `ROV`, `Underwater Camera`).
3. Exhibitors whose relationship type is `distributor`, `service_provider`,
   `sensor_vendor`, or `research` are excluded.

### Platform Coverage

List the platforms an exhibitor covers from the policy's target set. Sort the
list in the enum order declared in the template (e.g. `AUV`, `ROV`,
`Underwater Camera`). Only include platforms the exhibitor actually covers.

### Priority Tiering

When the task uses priority tiers (`A`, `B`, `C`) tied to opportunity
estimates:

1. Read the policy for tier definitions. Default pattern:
   - `A`: demo requested, interest score >= 90
   - `B`: demo requested, interest score >= 80
   - `C`: all other qualified leads
2. Assign the corresponding per-tier opportunity estimate (from the policy
   or task instructions).

### Exclusion Near-Misses

Non-qualified exhibitors still appear in the exclusion list. Use the
controlled `exclusion_reason` values:

| Reason | Meaning |
|--------|---------|
| `distributor_only` | Exhibitor is a distributor, not a manufacturer/OEM |
| `service_only` | Exhibitor provides services only |
| `sensor_vendor_only` | Exhibitor sells sensors but does not build platforms |
| `research_only` | Academic or research institution |
| `not_target_market` | Outside the campaign's target market |

The `relationship_type` on excluded exhibitors maps to the exclusion reason
according to the policy. Typical mapping:

- `distributor` → `distributor_only`
- `service_provider` → `service_only`
- `sensor_vendor` → `sensor_vendor_only` or `sensor_only`
- `research` → `research_only`

### Ranking Leads

When ranking qualified leads, follow the task's ranking rules. Common pattern:

1. Demo requested first (boolean, true sorts before false).
2. Interest score descending within each demo group.
3. Broader platform coverage (more platforms = higher rank) as a tiebreaker.
4. Company name ascending as the final tiebreaker.

### CRM Action for Exhibitors

- Exhibitors matching an existing CRM account by name → `update_existing`,
  include the `crm_account_id`.
- Exhibitors with no CRM match → `create_account`, `crm_account_id = null`.
- Excluded exhibitors → `no_import`.

---

## Workflow Family 3: Batch Import Cleaning

This pattern appears when a task asks to "prepare a batch for CRM import."

### Data Sources

| Endpoint | Purpose |
|----------|---------|
| `/api/import_batches` | List all batches |
| `/api/import_batches/{batch_id}` | Batch metadata including campaign code |
| `/api/import_batches/{batch_id}/raw_contacts` | Raw rows from all sources |
| `/api/import_batches/{batch_id}/suppression` | Email suppression list for the batch |
| `/api/crm/accounts` | CRM accounts for cross-reference |
| `/api/crm/contacts` | CRM contacts for cross-reference |
| `/api/policies` | Duplicate resolution source priority order |

### Cleaning Pipeline

Process the raw contacts in three phases:

**Phase 1: Remove unusable rows.**
Rows with `null` or empty `contact_name` and `email` → `missing_contact`.

**Phase 2: Deduplicate.**
Email-based dedup as described in the general deduplication section above.

**Phase 3: Suppression.**
Rows whose normalized email matches the batch suppression list → `suppressed`.

A single row is removed only once, even if it matches multiple removal
criteria. Apply phases in order: missing_contact first, then duplicate, then
suppressed.

### Duplicate Summary

For each duplicate key, record:
- `key`: the dedup key (e.g. `email:jane.doe@example.com`)
- `winner_row_id`: the row ID of the winning contact
- `removed_row_ids`: list of row IDs that were removed as duplicates

Sort `duplicate_keys` by `key` ascending.

### Removal Summary

Record all removed rows in `removed_rows` sorted by `row_id` ascending.
Each entry has:
- `row_id`: the raw contact row ID
- `reason`: one of `duplicate`, `missing_contact`, `suppressed`

Separate counts: `unusable_removed_count` covers `missing_contact` rows,
`suppressed_removed_count` covers `suppressed` rows. Duplicate counts are
tracked in `duplicate_removed_count`.

### Clean Contacts

The surviving rows after all three phases. For each:

- `clean_contact_id`: same as the winning `source_row_id`
- `source_row_id`: same as `clean_contact_id`
- `company_name`, `contact_name`: as from the winning row
- `email`: normalized (lowercase, trimmed, empty string allowed)
- `phone`: normalized (digits only, empty string allowed)
- `source_name`: from the winning row's source field
- `captured_at`: ISO timestamp from the winning row
- `crm_action`: `create_account` (no CRM match), `update_existing` (CRM
  account match), `no_import` (not used for clean contacts), `suppress`
  (not used for clean contacts)
- `existing_account_id`: CRM account ID if matched, else `null`
- `existing_contact_id`: CRM contact ID if matched by email, else `null`

Sort clean contacts by `clean_contact_id` ascending.

### Action Totals

Count every raw row by its final disposition:

- `create_account`: surviving rows with no CRM account match
- `update_existing`: surviving rows with a CRM account match
- `no_import`: rows removed for any reason other than suppression
- `suppress`: rows removed by the suppression list

`campaign_member_import_count` equals the number of clean contacts (all
surviving rows).

---

## JSON Output Rules

Every task in this family is a JSON-only output task. Follow these rules
without exception:

1. **Match the template exactly.** The answer template defines every allowed
   key, every allowed enum value, and every sort order. Do not invent keys.
2. **No prose.** The response is a single JSON object with no surrounding
   text, markdown fences, or commentary.
3. **Controlled values only.** Every enum field must use one of the values
   listed in the template. Do not use variants like `suppress` when the
   template says `suppressed`.
4. **Null vs empty string.** Use `null` only where the template or task
   instructions explicitly permit it (e.g. `invoice_id`, `account_id`,
   `existing_contact_id`). Use `""` for absent email/phone after
   normalization.
5. **Integer counts and amounts.** Currency amounts and counts are always
   integers. No decimals, no currency symbols, no formatting.
6. **Dates in YYYY-MM-DD.** All date fields use ISO 8601 date format.
7. **Strict sorting.** Apply the sort order declared in the template exactly.
   When the template says "Sort by X ascending" with multiple levels, apply
   them in the stated order.

## Policy as Truth

The `/api/policies` endpoint is the single source of truth for:

- Which relationship types qualify for a campaign
- Which platforms are in scope
- Source priority order for deduplication
- Lead opportunity amounts
- Follow-up date offsets
- Campaign codes
- Suppression lists
- Priority tier thresholds

Do not hard-code any of these values. Always fetch policies and use the
returned data to drive decisions.
