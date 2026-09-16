---
name: harbor-crm-integration
description: Build HarborCRM post-event reconciliation, trade-show prospecting, and import-batch cleaning workflows. Use this skill whenever the task involves HarborCRM, event-to-CRM handoff, sponsor reconciliation, lead qualification from trade shows, import-batch deduplication and suppression, or preparing CRM-ready structured JSON from HarborCRM API data. Trigger on any mention of HarborCRM, event reconciliation, trade-show lead lists, badge-scan handoff, CRM import preparation, or cleaning raw contact imports — even if the user does not use the exact product name.
---

# HarborCRM Integration

## Overview

HarborCRM is a shared CRM marketing workspace with a REST API at a runner-supplied base URL (typically `<TASK_ENV_BASE_URL>`). This skill guides tasks that query HarborCRM, cross-reference data across its API domains, apply business rules from the policies endpoint, and produce a structured JSON output that conforms to a provided answer template.

The skill covers three recurrent job families seen in the API surface:

1. **Post-event reconciliation** — combine event metadata, orders, badges, invoices, CRM accounts/contacts/opportunities/campaign-members, and policy rules into sponsor statuses, qualified-lead lists, exclusion lists, follow-up dates, and CRM action counts.
2. **Trade-show prospecting** — merge trade-show exhibitors, meeting-interest data, CRM accounts/contacts, and qualification policy rules into ranked/qualified lead lists with platform coverage, priority tiers, opportunity sizing, and near-miss exclusion reasons.
3. **Import-batch cleaning** — deduplicate and suppress raw import contacts, normalize contact fields, cross-reference against existing CRM records, classify each row's CRM action, and summarize duplicate/removal/action counts.

All three families share a common skeleton: read the task prompt and answer template, discover the relevant API surface, fetch all needed data, normalize contacts, cross-reference records, apply business rules, and return a single JSON object.

## General workflow

Always follow this sequence. The steps are ordered to minimize round-trips and avoid rework.

### 1. Orient from the prompt and template

Read the task prompt first. Extract:

- The **task type** (event reconciliation, trade-show prospecting, or import-batch cleaning).
- The **primary identifier**: `event_id`, `show_id`, or `batch_id`.
- Any **task-specific business rules** (priority tiers, opportunity amounts, ranking order, exclusion rules, follow-up day offsets).
- The **answer template** from `input/payloads/answer_template.json` — this is the output contract. Every field, enum value, sort order, and nullability constraint declared there is binding.

Note every controlled enum declared in the template (e.g., `paid_deferred | open_invoice | proposal_only`) and every sort rule. Deviating from the template's shape, enums, or order is the most common cause of task failure.

### 2. Read the policies endpoint

Always call `GET /api/policies` first. It returns the shared business rules across all task families. The response has three sections:

- `contact_hygiene` — rules for normalizing contacts before CRM import.
- `prospecting` — platform enums (`AUV`, `ROV`, `Underwater Camera`) and qualification guidance (use exhibitor descriptions and company context to decide qualification).
- `sponsor_handoff` — sponsor status enums (`paid_deferred`, `open_invoice`, `proposal_only`, `not_sponsor`) and reconciliation note.

The enum values from policies are authoritative; the answer template may echo a subset of them. When a policy-defined enum appears in a template field, use its exact value.

### 3. Fetch all relevant API data

Query the full set of endpoints relevant to the task type. Always fetch in parallel where independent. The endpoint catalog is in [references/api.md](references/api.md).

**For event reconciliation** (task has `event_id`):

- `GET /api/events/{event_id}` — event metadata (dates, campaign_code, followup day offsets, lead_opportunity_amount).
- `GET /api/events/{event_id}/orders` — sponsor orders (account, amount, status, ticket contacts). Canceled orders are included here.
- `GET /api/events/{event_id}/badges` — badge scans with contact info, badge_type, scan_score.
- `GET /api/events/{event_id}/sponsor_packages` — if referenced by the template.
- `GET /api/finance/invoices?event_id={event_id}` — invoice status, paid amounts, deferred amounts.
- `GET /api/crm/accounts` — all CRM accounts (name, status, disqualified_reason, domain, owner_region).
- `GET /api/crm/contacts` — all CRM contacts (account_id, contact_id, name, email, phone, opted_out).
- `GET /api/crm/opportunities?event_id={event_id}` — event-linked opportunities (account_id, amount, stage).
- `GET /api/crm/campaign_members?event_id={event_id}` — existing campaign-member records (account_id, contact_id, status).

**For trade-show prospecting** (task has `show_id`):

- `GET /api/tradeshows/{show_id}` — show metadata.
- `GET /api/tradeshows/{show_id}/exhibitors` — exhibitor list with descriptions, booth, country, website, crm_account_id.
- `GET /api/tradeshows/{show_id}/meeting_interest` — interest scores and demo requests.
- `GET /api/crm/accounts` — all CRM accounts for overlap detection.
- `GET /api/crm/contacts` — all CRM contacts for enrichment.
- `GET /api/policies` — prospecting rules and platform enums.

**For import-batch cleaning** (task has `batch_id`):

- `GET /api/import_batches/{batch_id}` — batch metadata (campaign_code).
- `GET /api/import_batches/{batch_id}/raw_contacts` — the raw rows to clean.
- `GET /api/import_batches/{batch_id}/suppression` — suppression list (email+phone pairs to block).
- `GET /api/crm/accounts` — existing accounts for matching.
- `GET /api/crm/contacts` — existing contacts for matching and dedup detection.

### 4. Normalize contact data

Every task family involves contacts from at least one source (badge scans, raw import rows, or exhibitor data). Normalize them uniformly before any cross-referencing.

**Email normalization**: trim whitespace, convert to lowercase. An email that is only whitespace after trimming is treated as empty/missing.

**Phone normalization**: strip every character that is not a digit. Keep the leading country code digit — do not strip a leading `1`. Empty string if no digits remain.

Both normalizations are idempotent. Apply them once when the record is first loaded; use the normalized values for all matching and for output fields labeled `normalized_email` / `normalized_phone`.

### 5. Cross-reference and classify

Merge the fetched data by joining on shared keys. The joining strategy depends on task family.

#### Event reconciliation joins

| Join | Left side | Right side | Key | Purpose |
|------|-----------|------------|-----|---------|
| Sponsor finance | orders | invoices | account_id | Determine sponsor status (paid_deferred, open_invoice, proposal_only) |
| Sponsor CRM | orders | accounts | account_id | Confirm active/non-disqualified sponsor accounts |
| Badge accounts | badges | accounts | company_name (case-insensitive match after trim) | Detect whether badge company is a known CRM account, and whether it is disqualified |
| Badge contacts | badges | contacts | normalized email | Detect whether badge contact already exists in CRM |
| Badge campaign | badges | campaign_members | (account_id, contact_id) pair after cross-reference | Detect existing campaign-member records for sponsor attendees |
| Lead opportunities | qualified leads | event metadata | n/a | Use `lead_opportunity_amount` from event as the per-account opportunity amount |

**Sponsor classification** (from orders + invoices):

- If `order_status` is `canceled` — the order is not an active sponsor. Exclude it from sponsor statuses.
- If invoice `status` is `paid_deferred` — sponsor status is `paid_deferred`.
- If invoice `status` is `open` (and order is `confirmed`) — sponsor status is `open_invoice`. Open balance = `amount - paid_amount`.
- If no invoice exists but order is `confirmed` or `proposal_sent` — sponsor status is `proposal_only`.

**Exclusion classification** (for badges):

- Badge belongs to a sponsor account (matched by company_name to an active sponsor order that is not canceled) — `sponsor_attendee`.
- Badge has `badge_type` `student` or other clearly non-business category — `non_business_badge`.
- Account is disqualified (`status: "disqualified"` or non-null `disqualified_reason`) — `existing_disqualified`.
- Contact is missing (no name, or blank) — `missing_contact`.

**Qualified lead**: A non-excluded badge whose company is not a sponsor (no active non-canceled order) and whose CRM account is not disqualified.

#### Trade-show prospecting joins

| Join | Left side | Right side | Key | Purpose |
|------|-----------|------------|-----|---------|
| Interest enrichment | exhibitors | meeting_interest | company_name (exact match) | Attach interest_score and requested_demo |
| CRM overlap | exhibitors | accounts | crm_account_id or company_name | Detect existing CRM accounts |

**Qualification**: Read each exhibitor's `description` and apply the prospecting policy. An exhibitor qualifies when its description shows it *manufactures* or *OEM-builds* underwater platforms (AUVs, ROVs, underwater cameras), not just distributes, services, or builds only sensors. Use the exhibitor descriptions and company context to make this call.

**Platform classification**: Examine the exhibitor's `description` text. If it mentions building AUVs — `AUV` platform. If it mentions ROVs — `ROV` platform. If it mentions underwater cameras or camera modules — `Underwater Camera` platform. An exhibitor can have multiple platforms. Sort platforms in enum order: AUV, ROV, Underwater Camera.

**Exclusion reasons**: Use the template's allowed exclusion enum values. Common categories:

- `distributor_only` — description mentions distribution, reselling, importing, or sales agency without manufacturing.
- `service_only` — description mentions consulting, renting, or operating equipment without building platforms.
- `sensor_vendor_only` / `sensor_only` — description mentions sensors/probes but no platform manufacturing.
- `research_only` — description indicates academic or research lab status.
- `not_target_market` — catch-all for other non-qualifying exhibitors.

**Priority tiers and opportunity sizing**: Follow task-specific rules from the prompt exactly. The prompt may define tier thresholds based on demo requests and interest scores, and assign opportunity amounts per tier.

**Ranking**: The prompt defines ranking order. When the prompt specifies "demo request first, then interest score descending, then broader platform coverage, then company name ascending", implement exactly that multi-key sort.

#### Import-batch cleaning joins

| Join | Left side | Right side | Key | Purpose |
|------|-----------|------------|-----|---------|
| Dedup detection | raw_contacts | raw_contacts | normalized email | Find duplicate rows by same normalized email |
| Suppression | raw_contacts | suppression | normalized email + normalized phone | Flag rows whose email or phone matches suppression list |
| CRM account match | raw_contacts | accounts | company_name (case-insensitive normalized match) | Find existing CRM accounts |
| CRM contact match | raw_contacts | contacts | normalized email | Find existing CRM contacts |

**Deduplication**: For rows sharing the same normalized email (after trim+lowercase), pick the winner by the **latest `captured_at` timestamp**. If timestamps tie, prefer the row with `source_name` `partner_upload` over `webinar_form` (partner uploads are generally higher-fidelity than self-registration). The winning row becomes the `clean_contact_id`; removed dupes get reason `duplicate`.

**Suppression**: Check each row's normalized email and normalized phone against the suppression list. For any match, the row gets `crm_action: "suppress"` (or `no_import` if the template's `crm_action` enum uses that), and removal reason `suppressed`.

**CRM action classification**:

- If row is suppressed — `suppress` (or `no_import` if suppressed rows are not imported).
- If no contact name is usable (trimmed empty) — `no_import` with removal reason `missing_contact`.
- If row matches an existing CRM account by company_name AND an existing contact by normalized email — `update_existing` with the matched `existing_account_id` and `existing_contact_id`.
- If row matches an existing CRM account but NOT an existing contact — `update_existing` for the account; contact creation is implied.
- If row matches no existing account — `create_account`.

The `crm_action` field's allowed values come from the answer template. Use exactly the enum values declared there.

### 6. Compute follow-up dates

When the template requires follow-up dates:

- **Lead follow-up due date**: `event.end_date + event.followup_days_after_end` days.
- **Sponsor finance follow-up due date**: `event.end_date + event.sponsor_followup_days_after_end` days.
- The `end_date` is ISO date format; add the integer offset, format the result as `YYYY-MM-DD`.
- For event reconciliation, the sponsor follow-up targets are the accounts with status `open_invoice` or `proposal_only` (unpaid sponsors).

**Task counts**: Lead task count = number of qualified lead accounts. Sponsor finance task count = number of unpaid sponsor accounts.

### 7. Compute CRM action counts

Aggregate across all classified records:

- **Accounts create**: count of qualified records with `crm_action: "create_account"`.
- **Accounts update**: count with `crm_action: "update_existing"`.
- **Contacts create**: count of records where the contact does not exist in CRM and needs creation.
- **Contacts update**: count where existing CRM contact is matched.
- **Campaign members create**: count of records needing `add_campaign_member`.
- **Campaign members update**: count of records where a campaign member already exists and needs status update.

The specific field names in the output must match the answer template exactly.

### 8. Build and validate the JSON output

Construct the JSON object field by field, adhering exactly to the answer template's shape.

**Sorting checklist** — before finalizing, verify every sort rule from the template:

- Sort `sponsor_statuses` by `account_name` ascending.
- Sort `qualified_lead_accounts` by `account_name` ascending.
- Sort `excluded_records` by `company_name` ascending, then `contact_name` ascending.
- Sort `qualified_exhibitors` / `ranked_leads` according to prompt ranking rules (read the prompt carefully; ranking is usually a multi-key compound sort).
- Sort `excluded_exhibitors` / `excluded_near_misses` by `company_name` ascending.
- Sort `clean_contacts` by `clean_contact_id` ascending.
- Sort `duplicate_keys` by `key` ascending.
- Sort `removed_rows` by `row_id` ascending.
- Sort list-of-string arrays (e.g., `qualified_non_sponsor_account_names`, `unpaid_sponsor_account_names`, `existing_crm_overlap_account_ids`) ascending.

**Null handling**: Use `null` (JSON null) for fields declared as nullable in the template, such as `invoice_id` for proposal-only sponsors, `existing_account_id` for unknown accounts, or `exclusion_reason` for non-excluded records. Do not use empty strings `""` or `"null"` for nullable fields. Use empty strings `""` only for fields declared as optional string with fallback to empty string (such as `normalized_email` or `normalized_phone` when no data is available).

**Integer precision**: Financial amounts and counts must be integers. `package_amount`, `paid_amount`, `open_balance`, `opportunity_amount`, `lead_opportunity_amount_usd`, all count fields — output as JSON numbers without decimal points.

**Validate before returning**:
- Every required top-level key from the template is present.
- No extra keys beyond the template's schema.
- All arrays are sorted as specified.
- All enum values match the allowed set.
- All integer fields are integers, not strings.
- The root output is a single JSON object (no wrapping array, no explanatory text).

## Common pitfalls

- **Forgetting to normalize emails before matching** — a case mismatch (`Jane.Smith@bigco.example` vs `jane.smith@bigco.example`) causes false negatives in CRM contact lookup and dedup. Always normalize before matching, not after.
- **Counting canceled orders as sponsors** — canceled orders (status `canceled` in the orders endpoint) are not active sponsors. Exclude them from sponsor statuses and from the sponsor-attendee exclusion logic.
- **Using the wrong opportunity amount for leads** — the event's `lead_opportunity_amount` applies per qualified non-sponsor account. The pipeline total is `lead_opportunity_amount x number_of_qualified_accounts`.
- **Mixing up sponsor revenue totals** — `paid_deferred` total = sum of package amounts for paid_deferred sponsors. `open_invoice` total = sum of package amounts for open_invoice sponsors. `open_invoice_balance` = sum of (amount - paid_amount) for open_invoice sponsors. These are distinct aggregations.
- **Including sponsor badge contacts in the lead list** — badge contacts whose company matches a non-canceled sponsor order are sponsor attendees, not qualified leads. Exclude them regardless of badge scan score.
- **Not checking the suppression list first** — in import-batch cleaning, check suppression before CRM matching. A suppressed contact should not be matched against CRM records; it is removed entirely.
- **Outputting string amounts** — JSON numbers must be bare integers, not `"60000"`.

## When the template uses a schema the API data does not directly supply

Some template fields are derived, not raw API responses. Examples:

- `normalized_email` / `normalized_phone` — apply the normalization rules from section 4.
- `crm_account_action` / `crm_contact_action` / `campaign_member_action` — derive from cross-reference results per section 5.
- `opportunity_amount` for qualified leads — use the event's `lead_opportunity_amount` value.
- Follow-up dates — compute from event dates as described in section 6.
- `rank` — assign contiguous 1-based integers after sorting.
- `sponsor_finance_accounts` — list the account names of sponsors with open_invoice or proposal_only status, sorted ascending.
- `lead_pipeline_total` — sum of opportunity amounts across all qualified lead accounts.
- `campaign_member_import_count` — number of surviving cleaned contacts whose `crm_action` is `create_account` or `update_existing` (i.e., not `no_import` or `suppress`).

## Reference files

- [references/api.md](references/api.md) — Full HarborCRM API endpoint catalog with field descriptions and relationships.
- [references/rules.md](references/rules.md) — Detailed business rules for contact hygiene, sponsor classification, lead qualification, and import cleaning.
