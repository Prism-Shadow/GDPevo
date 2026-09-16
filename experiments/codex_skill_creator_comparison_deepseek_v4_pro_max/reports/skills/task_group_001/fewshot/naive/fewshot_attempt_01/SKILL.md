---
name: harborcrm-handoff
description: Reconcile HarborCRM API data into structured handoff summaries covering event sponsors, qualified leads, badge-only contacts, import-batch preparation, and trade-show exhibitor prospecting. Use the read-only HarborCRM API, cross-reference across CRM entities, apply controlled classification and normalization rules, then return a single JSON object conforming to the provided answer template.
---

# HarborCRM Handoff

## Quick Start

When the task asks you to audit, reconcile, prepare, or prospect against
HarborCRM data for an event, trade show, or import batch:

1. Read the answer template at `input/payloads/answer_template.json` first -- it
   is the authoritative output schema.
2. Fetch every API endpoint the prompt references. Use parallel GET requests
   whenever possible.
3. Cross-reference all fetched data: events to sponsors, badges to CRM accounts
   and contacts, exhibitors to CRM and meeting-interest records, raw contacts to
   suppression lists and CRM.
4. Apply the classification, normalization, deduplication, and sorting rules
   below.
5. Return exactly one JSON object matching the template. No markdown fences, no
   explanatory prose outside the JSON.

## API

The runner supplies the base URL as `<TASK_ENV_BASE_URL>`. All endpoints are
read-only GET. Append paths directly:
`<TASK_ENV_BASE_URL>/api/events`.

### Endpoint Inventory

**Events**
- `GET /api/events` -- list all events
- `GET /api/events/{event_id}` -- single event detail
- `GET /api/events/{event_id}/orders` -- sponsor orders for the event
- `GET /api/events/{event_id}/badges` -- badge scans for the event
- `GET /api/events/{event_id}/sponsor_packages` -- sponsor package definitions

**Finance**
- `GET /api/finance/invoices?event_id={event_id}` -- invoices for an event

**CRM**
- `GET /api/crm/accounts` -- all CRM accounts
- `GET /api/crm/accounts/{account_id}` -- single CRM account
- `GET /api/crm/contacts` -- all CRM contacts
- `GET /api/crm/opportunities` -- all CRM opportunities
- `GET /api/crm/campaign_members` -- all campaign members; filter with
  `?event_id={event_id}`

**Trade Shows**
- `GET /api/tradeshows` -- list all trade shows
- `GET /api/tradeshows/{show_id}` -- single trade show detail
- `GET /api/tradeshows/{show_id}/exhibitors` -- exhibitors for a show
- `GET /api/tradeshows/{show_id}/meeting_interest` -- meeting interest records
  for a show

**Import Batches**
- `GET /api/import_batches` -- list all import batches
- `GET /api/import_batches/{batch_id}` -- single batch detail
- `GET /api/import_batches/{batch_id}/raw_contacts` -- raw contact rows
- `GET /api/import_batches/{batch_id}/suppression` -- suppression-list entries
  for the batch

**Policies**
- `GET /api/policies` -- policy metadata (qualification rules, opportunity
  amounts, date offsets)

**Health**
- `GET /health`
- `GET /api/manifest`

Fetch endpoints in parallel. Use API results as the sole source of truth; do
not invent data.

## Answer Templates

Every task provides a JSON answer template at
`input/payloads/answer_template.json`. Read it **before** fetching data.

The template declares:
- Every required top-level key.
- Field types and allowed enum values.
- Sort order for every list.
- Numeric precision (counts are integers, amounts are integers in USD).
- Whether a field is nullable or expects an empty string.

Conform to the template exactly. Do not add undeclared fields. Do not change
key names. Match the declared sort order and enum values precisely.

## Controlled Vocabularies

### Sponsor Statuses

| Value | Meaning |
|---|---|
| `paid_deferred` | Invoice exists and is fully paid; revenue recognized |
| `open_invoice` | Invoice exists with a non-zero open balance |
| `proposal_only` | Sponsor package selected but no invoice generated |
| `not_sponsor` | Account has no sponsor order for the event |

### Exclusion Reasons -- Attendee / Badge

| Value | Meaning |
|---|---|
| `sponsor_attendee` | Contact's company is a sponsor account |
| `inactive_sponsor_record` | Sponsor record is canceled or inactive |
| `non_business_badge` | Badge type is press, student, speaker-only, or similar |
| `existing_disqualified` | CRM account is already marked disqualified |
| `missing_contact` | No contact name on the badge or row |
| `duplicate` | Row is a duplicate of a winning row |
| `suppressed` | Contact matches a suppression-list entry |

### Exclusion Reasons -- Trade-Show Exhibitor

| Value | Meaning |
|---|---|
| `distributor_only` | Exhibitor resells, does not OEM-build |
| `service_only` | Exhibitor provides services, not platforms |
| `sensor_vendor_only` | Sells sensors but does not build platform hardware |
| `research_only` | Academic or research institution |
| `not_target_market` | Market does not match the campaign scope |

### CRM Actions -- Accounts

| Value | Meaning |
|---|---|
| `create_account` | No matching CRM account; create one |
| `update_existing` | Matching CRM account exists; update it |
| `no_import` | Do not import into CRM |

### CRM Actions -- Contacts

| Value | Meaning |
|---|---|
| `create_contact` | No matching CRM contact; create one |
| `update_existing` | Matching CRM contact exists; update it |

### CRM Actions -- Campaign Members

| Value | Meaning |
|---|---|
| `add_campaign_member` / `create` | Add a new campaign member record |
| `update_campaign_member` / `update` | Update an existing campaign member |
| `no_action` | Existing member needs no change |
| `no_import` | Do not create a campaign member record |

### Platform Coverage

| Value | Meaning |
|---|---|
| `AUV` | Autonomous Underwater Vehicle |
| `ROV` | Remotely Operated Vehicle |
| `Underwater Camera` | Underwater imaging platform |

Sort platform lists in this enum order: `AUV`, `ROV`, `Underwater Camera`.

### Priority Tiers

| Value | Meaning |
|---|---|
| `A` | Highest priority |
| `B` | Medium priority |
| `C` | Lower priority |

### Source Names -- Import Batches

| Value |
|---|
| `badge_scan` |
| `sponsor_form` |
| `partner_upload` |
| `webinar_form` |
| `exhibitor_form` |
| `manual_upload` |

### Relationship Types -- Exhibitors

| Value | Meaning |
|---|---|
| `distributor` | Reseller / dealer |
| `service_provider` | Services-only business |
| `sensor_vendor` | Sensor component vendor |
| `research` | Academic or research entity |

### Campaign Member Target Statuses

| Value | Meaning |
|---|---|
| `attended` | Attended the event as a qualified lead |
| `attended_sponsor` | Attended the event as a sponsor |
| `registered_sponsor` | Registered but did not attend; sponsor |
| `excluded` | Excluded from campaign membership |

## Cross-Referencing & Classification

### Sponsor Determination (Event Reconciliation)

1. Fetch event orders, sponsor packages, and invoices in parallel.
2. For each sponsor order: locate the matching invoice (match on invoice ID from
   the order or look up by account). If an invoice exists and its open balance
   is zero, status is `paid_deferred`. If an invoice exists with a positive open
   balance, status is `open_invoice`. If no invoice exists, status is
   `proposal_only`.
3. Package amount comes from the order or sponsor package. Paid amount and open
   balance come from the invoice. Revenue totals sum package amounts within each
   status bucket. `open_invoice_balance` sums only open balances.
4. Accounts with no sponsor order are `not_sponsor` when that status is
   required.

### Lead Qualification (Event Reconciliation)

1. Fetch badge scans, CRM accounts, CRM contacts, and campaign members in
   parallel.
2. Build lookup maps: CRM accounts by name (case-insensitive) and by ID; CRM
   contacts by normalized email.
3. Classify each badge:
   - Company matches a sponsor account → `sponsor_attendee`, CRM action
     `no_action`.
   - Badge type is non-business → `non_business_badge`, CRM action `no_import`.
   - Company matches a disqualified CRM account → `existing_disqualified`, CRM
     action `no_import`.
   - Contact name is missing → `missing_contact`, CRM action `no_import`.
   - Otherwise → `qualified_non_sponsor_lead`.
4. For each qualified lead, determine CRM actions:
   - If a CRM account exists for the company → `update_existing`; otherwise
     `create_account`.
   - If a CRM contact exists with the same normalized email → `update_existing`;
     otherwise `create_contact`.
   - Campaign member: `add_campaign_member`.
5. Use the event's lead opportunity amount (from policy or event metadata) for
   each qualified non-sponsor account.

### Campaign Member Reconciliation

When the template requires campaign member action decisions:
- Existing campaign members tied to sponsors → `no_action` with status
  `attended_sponsor` or `registered_sponsor`.
- Existing campaign members tied to qualified leads → decide `no_action` or
  `update` based on whether their status needs correction.
- New qualified leads not yet campaign members → `create` with status
  `attended`.
- Badge-only sponsor contacts (sponsor attendee not yet a campaign member) →
  `create` with status `attended_sponsor`.

### Trade-Show Exhibitor Qualification

1. Fetch exhibitors, meeting interest, CRM accounts, and policies in parallel.
2. Build a CRM account lookup by company name (case-insensitive) and by ID.
3. Map meeting interest records to exhibitors by company ID; extract demo
   requests and interest scores.
4. Classify each exhibitor:
   - Relationship is `distributor` → `distributor_only`, CRM action `no_import`.
   - Relationship is `service_provider` → `service_only`, CRM action
     `no_import`.
   - Relationship is `sensor_vendor` → `sensor_only`, CRM action `no_import`.
   - Relationship is `research` → `research_only`, CRM action `no_import`.
   - Platforms do not match the campaign target → `not_target_market`, CRM
     action `no_import`.
   - Otherwise → qualified.
5. For each qualified exhibitor:
   - If a CRM account exists → `update_existing`; otherwise `create_account`.
   - Capture enrichment fields: booth, country, website.
   - Record platform coverage using only the allowed platform enums.
6. When priority tiers are assigned:
   - `A`: demo requested AND interest score ≥ 90.
   - `B`: demo requested AND interest score ≥ 80 (but not ≥ 90).
   - `C`: all other qualified leads.
7. When opportunity sizing by tier is required, check the policy or prompt for
   per-tier amounts; otherwise use `A` = $120,000, `B` = $90,000, `C` = $50,000
   (integers, USD).
8. When rank-ordering is required, sort by: demo request first, then interest
   score descending, then platform count descending, then company name
   ascending.

### Import Batch Processing

1. Fetch raw contacts, suppression list, CRM accounts, CRM contacts, and
   policies in parallel.
2. Normalize every email (see Normalization Rules below).
3. Build a suppression lookup: normalize suppression-list emails and phones,
   then flag any raw contact whose normalized email or phone matches.
4. Deduplicate by normalized email:
   - Group rows sharing the same normalized email.
   - Pick one winner per group. Prefer sources in this order: `badge_scan`,
     `sponsor_form`, `partner_upload`, `webinar_form`, `exhibitor_form`,
     `manual_upload`. Within the same source, prefer the earliest `captured_at`
     timestamp.
   - Mark all other rows in the group as `duplicate`.
5. Classify each cleaned row:
   - Suppressed → `suppress`.
   - Missing contact name → `missing_contact`, CRM action `no_import`.
   - Otherwise inspect CRM:
     - CRM account exists → `update_existing`.
     - No CRM account → `create_account`.
6. The campaign member import count is the number of cleaned rows whose CRM
   action is `create_account` or `update_existing`.

## Normalization Rules

**Email**
- Lowercase the entire string.
- Trim leading and trailing whitespace.
- If no email is present, output `""` (empty string).

**Phone**
- Strip every non-digit character (spaces, dashes, parentheses, dots, plus
  signs).
- If no phone is present, output `""` (empty string).
- Preserve the numeric country code that follows `+`.

## Sorting Conventions

Always follow the template's explicit sort instructions. When the template is
silent, use these defaults:

| List | Sort Key(s) | Direction |
|---|---|---|
| Sponsor statuses | `account_name` | ascending, case-sensitive |
| Qualified lead accounts | `account_name` | ascending, case-sensitive |
| Excluded records | `company_name`, then `contact_name` | ascending |
| Badge decisions | `badge_id` | ascending |
| Campaign member actions | `subject_key` | ascending |
| Clean contacts | `clean_contact_id` | ascending |
| Duplicate keys | `key` | ascending |
| Removed rows | `row_id` | ascending |
| Qualified exhibitors | when rank-ordered: `rank` ascending; otherwise `company_name` ascending |
| Excluded exhibitors | `company_name` | ascending |
| Platforms within an item | enum order: `AUV`, `ROV`, `Underwater Camera` |
| CRM account ID lists | ascending string sort |
| Account name lists | ascending string sort |

## Follow-Up Dates

- Lead follow-up due date: 30 calendar days after the event end date.
- Sponsor finance follow-up due date: 14 calendar days after the event end
  date.
- If the policy endpoint or event metadata provides explicit dates, those take
  precedence over the default offsets.
- Format all dates as `YYYY-MM-DD`.

## Counts and Totals

- All counts are integers.
- Revenue and opportunity amounts are integers in USD. No decimal places, no
  currency symbols.
- Pipeline totals are the sum of individual opportunity amounts.
- Platform coverage counts: tally each qualified exhibitor's platforms. One
  exhibitor covering both AUV and ROV increments both counters.
- CRM action counts: count every record that receives each action.
- Sponsor finance task count: number of sponsor accounts requiring finance
  follow-up (those with `open_invoice` or `proposal_only` status).
- Lead task count: number of qualified lead accounts.

## Output Rules

1. Return exactly one JSON object.
2. No explanatory prose, markdown fences, or commentary outside the JSON.
3. Do not add fields not declared in the answer template.
4. All keys must match the template exactly, including case.
5. Use `null` when the template shows `null`; use `""` when the template shows
   an empty string.
6. Numeric values must match the template's declared type (integers where it
   says integer).
7. Enum values must be drawn from the template's allowed-values list, exactly as
   spelled.

## Workflow Sequence

1. Read `input/payloads/answer_template.json`. Internalize every required key,
   allowed enum, sort order, and type constraint.
2. Read `input/prompt.txt`. Extract the entity identifier (event_id, show_id, or
   batch_id), the campaign context, and any task-specific overrides.
3. Fetch all API data the prompt references. Prefer parallel GET requests --
   there is no write access, so order does not matter.
4. Build lookup maps from the raw API responses: accounts by name and ID,
   contacts by normalized email, invoices by account, meeting interest by
   exhibitor ID, suppression entries by normalized email and phone.
5. Apply the classification and cross-referencing logic for the task type
   (event, trade show, or import batch).
6. Normalize every email and phone that enters the output.
7. Sort every list according to the template's instructions.
8. Fill the template, verify every key is present, and return the single JSON
   object.
