---
name: harbor-crm-handoff
description: Solve HarborCRM data-reconciliation tasks by following reusable patterns for sponsor handoffs, lead qualification, badge classification, import-batch cleaning, trade-show prospecting, campaign-member management, and contact normalization. This skill covers the HarborCRM REST API entity model and the cross-entity business rules that the API data itself does not declare.
---

# HarborCRM Handoff Skill

This skill teaches reusable patterns for solving HarborCRM event-handoff, trade-show prospecting, and import-batch cleaning tasks. HarborCRM is a self-describing REST API whose entity model and cross-entity business rules remain consistent across related task types. The skill does not contain task-specific answer values; it encodes only the reusable domain logic, entity relationships, normalization rules, and workflow patterns.

## Conventions

- The API base URL is always supplied by the runner as `<TASK_ENV_BASE_URL>`.
- Every task supplies an `answer_template.json` in `input/payloads/`. Read it first so you understand the exact output shape before fetching any API data.
- Sort rules appear in the prompt or template. Default sorts when unspecified: `company_name` ascending, `row_id` ascending, `rank` ascending.
- All monetary values are integer USD. Round down after summing (use floor).
- Dates use `YYYY-MM-DD` format.

## Core API Endpoints

HarborCRM exposes GET-only endpoints. `/health` gives a counts summary that helps you discover which entity collections are populated.

### Events

- `GET /api/events` -- all events
- `GET /api/events/{event_id}` -- single event with `campaign_code`, `lead_opportunity_amount`, `followup_days_after_end`, `sponsor_followup_days_after_end`, `start_date`, `end_date`
- `GET /api/events/{event_id}/sponsor_packages` -- sponsor orders with `order_status` (`confirmed`, `proposal_sent`, `canceled`), `amount`, `account_id`, `account_name`, `ticket_contacts`
- `GET /api/events/{event_id}/badges` -- badge scans with `badge_type` (`sponsor`, `attendee`, `student`, `press`), `company_name`, `contact_name`, `email`, `phone`, `scan_score`
- `GET /api/finance/invoices?event_id={event_id}` -- invoices with `status` (`paid_deferred`, `open`), `amount`, `paid_amount`, `deferred_amount`
- `GET /api/crm/campaign_members?event_id={event_id}` -- campaign members with `status` (`attended_sponsor`, `registered_sponsor`, `attended`, `excluded`), `account_id`, `contact_id`

### CRM

- `GET /api/crm/accounts` -- all accounts with `account_id`, `name`, `status` (`customer`, `prospect`, `disqualified`), `disqualified_reason`
- `GET /api/crm/contacts` -- all contacts with `contact_id`, `account_id`, `name`, `email`, `phone`, `opted_out`
- `GET /api/crm/opportunities` -- all opportunities with `stage`, `amount`, `account_id`
- `GET /api/crm/campaign_members` -- all campaign members (optionally filter with `?event_id=`)

### Trade-shows

- `GET /api/tradeshows` -- all trade-shows
- `GET /api/tradeshows/{show_id}` -- single trade-show with `name`, `theme`, `start_date`, `end_date`, `city`, `country`
- `GET /api/tradeshows/{show_id}/exhibitors` -- exhibitors with `company_id`, `company_name`, `description`, `booth`, `website`, `country`, `crm_account_id` (nullable)
- `GET /api/tradeshows/{show_id}/meeting_interest` -- meeting interest with `company_id`, `requested_demo` (boolean), `interest_score` (integer)

### Import Batches

- `GET /api/import_batches` -- all batches
- `GET /api/import_batches/{batch_id}` -- single batch with `campaign_code`, `source_system`, `received_at`
- `GET /api/import_batches/{batch_id}/raw_contacts` -- raw rows with `row_id`, `company_name`, `contact_name`, `email`, `phone`, `source_name`, `captured_at`
- `GET /api/import_batches/{batch_id}/suppression` -- suppression list with `email`, `phone`, `reason`

### Policies

- `GET /api/policies` -- global enums: `sponsor_handoff.status_enums` (`paid_deferred`, `open_invoice`, `proposal_only`, `not_sponsor`) and `prospecting.platform_enums` (`AUV`, `ROV`, `Underwater Camera`)

Read `/api/policies` early in any task; it provides the canonical enum values and qualification guidance.

## Contact Normalization

Apply these transformations to every email and phone value:

- **Email**: `.strip()` then `.lower()`. Empty after stripping becomes `""`.
- **Phone**: Remove every non-digit character (spaces, dashes, parentheses, dots, plus signs). Empty after digit extraction becomes `""`.

These normalizations are used for deduplication, CRM matching, suppression matching, and output formatting.

## Business Rules

### 1. Sponsor Status Reconciliation

For a given `event_id`, cross-reference three sources: sponsor packages, finance invoices, and CRM accounts.

**Active sponsors**: Start from `/api/events/{event_id}/sponsor_packages`. Exclude any with `order_status` of `canceled` -- these are inactive sponsor records.

**Per-sponsor status** (match by `account_id` across sponsor packages and invoices):

- If an invoice exists and its `status` is `paid_deferred` (or `paid`): status = `paid_deferred`
- If an invoice exists and its `status` is `open`: status = `open_invoice`
- If no invoice exists and the package `order_status` is `proposal_sent`: status = `proposal_only`
- If no invoice exists and the package `order_status` is `confirmed`: status = `open_invoice`

**Financial fields**: `package_amount` from the sponsor package `amount`. `invoice_id` from the matching invoice (null if none). `paid_amount` from invoice `paid_amount` (0 if no invoice). `open_balance` = `amount - paid_amount` when invoice status is `open`, otherwise 0.

**Revenue totals**: Sum `package_amount` by status group (integer USD). `open_invoice_balance` is the sum of `open_balance` across all `open_invoice` entries.

**Sponsor finance follow-up**: Accounts with `open_invoice` or `proposal_only` status need follow-up tasks. One task per account.

### 2. Badge Classification

Badges from `/api/events/{event_id}/badges` have a `badge_type` field:

- `sponsor` -- sponsor attendee
- `attendee` -- standard business attendee
- `student` -- non-business (exclude from leads)
- `press` -- non-business (exclude from leads)

**Sponsor attendee determination**: A badge is a sponsor attendee if (a) its `badge_type` is `sponsor`, OR (b) its `company_name` matches an active sponsor's `account_name` from the sponsor packages (case-insensitive exact match). The second case handles sponsor contacts who received an `attendee` badge but belong to a sponsor organization.

**Qualified non-sponsor lead**: An `attendee` badge whose associated CRM account (matched by company name, case-insensitive) is NOT disqualified and whose company is NOT an active sponsor. If no CRM account exists, the lead is still qualified and needs account creation.

**Exclusion reasons**:
- `sponsor_attendee` -- badge belongs to an active sponsor company
- `non_business_badge` -- `badge_type` is `student` or `press`
- `existing_disqualified` -- CRM account matched by company name has `status` = `disqualified`
- `missing_contact` -- `contact_name` is blank or whitespace-only after trimming

### 3. Lead Qualification for Events

For each non-sponsor `attendee` badge with a business badge type:

1. Match `company_name` (case-insensitive) against CRM accounts.
2. If the matched account is disqualified -> exclude as `existing_disqualified`.
3. If matched and not disqualified -> qualified lead, `crm_account_action` = `update_existing`.
4. If no match -> qualified lead, `crm_account_action` = `create_account`.

**Opportunity amount**: Use `lead_opportunity_amount` from the event record (integer USD). Apply this same amount to every qualified lead.

**CRM contact action**: Always `create_contact` for badge contacts (they are new to CRM unless already matched by exact normalized email).

**Campaign member action**: Always `add_campaign_member` for qualified leads.

**Lead pipeline total**: Sum of opportunity amounts across all qualified leads.

**Follow-up dates**: `lead_due_date` = event `end_date` + `followup_days_after_end`. `sponsor_finance_due_date` = event `end_date` + `sponsor_followup_days_after_end`.

**Task counts**: Lead task count = number of qualified lead accounts. Sponsor finance task count = number of `open_invoice` + `proposal_only` accounts.

### 4. Campaign Member Management

Campaign members link contacts to events. Their `status` values: `attended_sponsor`, `registered_sponsor`, `attended`, `excluded`.

**Decision logic by badge/contact pair**:

- Sponsor attendee already in campaign members (any sponsor status) -> `no_action`
- Sponsor attendee NOT in campaign members -> `create` with `target_status` = `attended_sponsor`
- Non-sponsor qualified lead NOT in campaign members -> `create` with `target_status` = `attended`
- Non-sponsor qualified lead already in campaign members -> `update` or `no_action` per context
- Excluded badge -> `no_import`

**Subject key format**: `{account_id}:{contact_id}` for known CRM contacts; `badge:{badge_id}` for badge-only leads without existing CRM records.

### 5. Trade-show Exhibitor Prospecting

**Platform qualification**: Use the `prospecting.platform_enums` from `/api/policies`: `AUV`, `ROV`, `Underwater Camera`. Classify each exhibitor by reading its `description` field.

An exhibitor qualifies when its description indicates it **manufactures or OEM-integrates** one or more of the target platform types. Qualifying language includes: "Builds", "manufactures", "Designs", "OEM", "integrates", "embeds", "payload", "platform maker", "produces". The exhibitor must actually build or integrate the platform hardware, not merely use or resell it.

**Exclusion categories** (non-qualified near misses):

- `distributor_only` -- reseller, distributor, dealer; does not build platforms
- `service_only` -- consulting, operating, renting equipment; no manufacturing
- `sensor_vendor_only` -- makes sensors/probes only, not the platforms that carry them
- `research_only` -- academic/research institution only
- `not_target_market` -- completely unrelated to the platform types

**CRM cross-reference**: Match exhibitor `crm_account_id` (or `company_name` when `crm_account_id` is null) against CRM accounts. If an exhibitor maps to a CRM account with `status` = `disqualified`, include that in the exclusion decision.

If a task asks for the `crm_action` per exhibitor:
- `create_account` for qualified exhibitors with no existing CRM match
- `update_existing` for qualified exhibitors with a CRM match
- `no_import` for excluded exhibitors

**Platform coverage counting**: Count each exhibitor once for each qualifying platform. A single exhibitor covering both AUV and ROV contributes 1 to each count. Always include all three platform keys in counts even when the value is zero.

**Priority tiers** (task-specific, but the default pattern): Tier A = USD 120000, Tier B = USD 90000, Tier C = USD 50000. Tier assignment rules are defined per task but typically: tier A for demo-requested leads with interest score at least 90, tier B for demo-requested leads with score at least 80, tier C for all other qualified leads.

**Ranking** (when required): Sort by demo request first (true before false), then interest score descending, then broader platform coverage (more platforms first), then company name ascending.

### 6. Import Batch Cleaning

Full workflow for cleaning a raw contact batch:

#### Step 1: Deduplicate

Group all raw contacts by normalized email (lowercase, trimmed). Within each group sharing the same normalized email, select one winner:

- Prefer the row with the latest `captured_at` timestamp.
- If timestamps tie, prefer the lower `row_id` (string comparison).

The winner becomes the clean contact; all other rows in the group are removed as duplicates.

Track each duplicate group with: `key` = `"email:{normalized_email}"`, `winner_row_id`, and `removed_row_ids` (sorted ascending).

#### Step 2: Suppress

Match each surviving row against the suppression list. A row is suppressed if:
- Its normalized email (lowercase, trimmed) matches a suppression entry's `email` (case-insensitive, trimmed), **OR**
- Its normalized phone (digits only) matches a suppression entry's `phone` (digits only).

Suppressed rows are removed from the clean set.

#### Step 3: Remove Missing Contacts

Remove any row where `contact_name` is blank or whitespace-only after trimming.

#### Step 4: CRM Matching

For each surviving clean row, match the normalized email against CRM contacts. If a CRM contact exists with the same normalized email, that contact's `account_id` links the row to an existing CRM account.

- Matched to existing CRM account: `crm_action` = `update_existing`, set `existing_account_id` to the account's `account_id`.
- No CRM match: `crm_action` = `create_account`, `existing_account_id` = `null`.
- `existing_contact_id`: set to the matched CRM contact's `contact_id` when found, otherwise `null`.

#### Output Fields

**`clean_contact_id`**: Use the winning `source_row_id`.

**`source_row_id`**: Same as `clean_contact_id` (the winning row_id).

**Duplicates**: `duplicate_removed_count` = total removed duplicate rows. `duplicate_keys` sorted by `key` ascending; each entry has `key`, `winner_row_id`, and `removed_row_ids` sorted ascending.

**Removals**: `removed_rows` sorted by `row_id` ascending; each entry has `row_id` and `reason` from `["duplicate", "missing_contact", "suppressed"]`. `unusable_removed_count` counts `missing_contact` removals. `suppressed_removed_count` counts `suppressed` removals.

**Import action totals**: Count `crm_action` values across surviving clean contacts: `create_account`, `update_existing`. Also count `no_import` (all removed rows that are not suppressed) and `suppress` (suppressed rows). Fill all four keys.

**Campaign member import count**: Number of surviving cleaned contacts (those with `crm_action` of `create_account` or `update_existing`).

## Workflow Pattern

When solving any HarborCRM handoff task:

1. **Read the answer template** from `input/payloads/answer_template.json`. Internalize every required key, enum constraint, and sort rule before fetching any API data.

2. **Read the prompt** for task-specific identifiers (`event_id`, `show_id`, `batch_id`), campaign context, and any special rules that override the defaults in this skill.

3. **Fetch `/api/policies`** for canonical enums and business notes.

4. **Fetch primary entities** (event details, exhibitors, raw contacts) by the task identifier.

5. **Fetch supporting entities** (CRM accounts, contacts, invoices, badges, campaign members, suppression) needed by the template.

6. **Apply business rules** in order: classify badges/exhibitors, reconcile sponsor finances, normalize contacts, deduplicate, suppress, cross-reference CRM, determine actions.

7. **Sort every list** exactly as specified by the prompt or template.

8. **Validate the output**: every required key present, enum values match canonical sets, counts are integers, currency is integer USD, nullable fields are explicit `null` not omitted, empty lists are `[]`.

## Output Rules

- Return exactly one JSON object matching the template structure.
- Do not add fields not declared in the template.
- Do not include explanatory prose outside the JSON object.
- Use `null` for nullable fields, never omit them.
- Use `[]` for empty lists, never omit them.
- All monetary values must be integers.
