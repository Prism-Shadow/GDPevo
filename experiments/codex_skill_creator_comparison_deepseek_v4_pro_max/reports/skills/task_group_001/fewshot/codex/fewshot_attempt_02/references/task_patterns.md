# HarborCRM Task Pattern Workflows

This reference describes the step-by-step data flow for each of the three
HarborCRM task families. The answer template controls the exact output shape;
this guide explains **how to derive the values** for each template field.

---

## Post-Event Handoff

**Trigger**: Prompt gives an `event_id` and mentions sponsor reconciliation,
badge scans, or post-event CRM handoff.

### Step 1: Gather Data

Fetch these in parallel:

- `GET /api/events/{event_id}` — event name, dates, opportunity amount
- `GET /api/events/{event_id}/orders` — sponsor orders
- `GET /api/events/{event_id}/badges` — badge scans
- `GET /api/events/{event_id}/sponsor_packages` — package definitions
- `GET /api/finance/invoices?event_id={event_id}` — finance invoices
- `GET /api/crm/accounts` — all CRM accounts
- `GET /api/crm/contacts` — all CRM contacts
- `GET /api/crm/opportunities?event_id={event_id}` — event opportunities
- `GET /api/crm/campaign_members?event_id={event_id}` — existing campaign members
- `GET /api/policies` — business rules

### Step 2: Sponsor Reconciliation

For each **active** sponsor order from `/api/events/{event_id}/orders`:

1. Find matching invoice by `invoice_id` from finance invoices
2. Determine status:
   - No invoice found → `proposal_only`, package_amount from order, paid=0, balance=0
   - Invoice balance == 0 → `paid_deferred`, package_amount from order, paid=invoice.paid_amount, balance=0
   - Invoice balance > 0 → `open_invoice`, package_amount from order, paid=invoice.paid_amount, balance=invoice.balance
3. Skip **canceled** orders (unless the template requires listing them separately)
4. Sort by `account_name` ascending

The `sponsor_revenue_totals` object sums package_amounts by status. `open_invoice_balance` is the sum of open balances across all open_invoice sponsors.

### Step 3: Badge Classification

For each badge from `/api/events/{event_id}/badges`:

1. **Determine if sponsor company**: match badge `company_name` to sponsor order `account_name` (via CRM account). Sponsor attendees are excluded from qualified leads.
2. **Check badge type**: non-business badge types (defined in policies) → exclude as `non_business_badge`
3. **Check CRM account status**: match badge `company_name` to CRM account. If account status is `disqualified` → exclude as `existing_disqualified`
4. **Remaining badges** → `qualified_non_sponsor_lead`

### Step 4: Qualified Lead Accounts

For each qualified non-sponsor badge:

1. Group by `company_name` (one account per company, pick the primary contact — typically the first badge scanned)
2. Match to CRM account by `company_name`. If found → `crm_account_action: "update_existing"`, `account_id` from CRM. If not found → `crm_account_action: "create_account"`, `account_id: null`
3. Match contact by normalized email to CRM contacts. If found → `crm_contact_action: "update_existing"`. If not → `crm_contact_action: "create_contact"`
4. `campaign_member_action` is `"add_campaign_member"` (or the template's equivalent action)
5. `opportunity_amount` comes from the event's `lead_opportunity_amount` (integer)
6. Normalize email (lowercase, trimmed) and phone (digits only)
7. Sort by `account_name` ascending

### Step 5: Excluded Records

For every badge that did NOT qualify:

- `sponsor_attendee`: badge company matches an active sponsor
- `existing_disqualified`: badge company's CRM account has status `disqualified`
- `non_business_badge`: badge type is not business-qualifying (per policies)
- `inactive_sponsor_record`: badge company matches a **canceled** sponsor order

Sort excluded records by `company_name` ascending, then `contact_name` ascending.

### Step 6: Follow-Up Dates and Counts

From policies, read `lead_followup_offset_days` and `sponsor_finance_followup_offset_days`.

- `lead_due_date` = event end date + lead_followup_offset_days
- `sponsor_finance_due_date` = event end date + sponsor_finance_followup_offset_days
- `lead_task_count` = number of qualified lead accounts
- `sponsor_finance_task_count` = number of sponsors with `open_invoice` or `proposal_only` status
- `sponsor_finance_accounts` = list of account names for those unpaid sponsors, sorted

### Step 7: CRM Action Counts

Count across all qualified lead accounts:

- `accounts_create` = leads with `crm_account_action: "create_account"`
- `accounts_update` = leads with `crm_account_action: "update_existing"`
- `contacts_create` = leads with `crm_contact_action: "create_contact"`
- `contacts_update` = leads with `crm_contact_action: "update_existing"`
- `campaign_members_create` = leads with `campaign_member_action: "add_campaign_member"` or equivalent
- `campaign_members_update` = leads with campaign member update action (if template separates these)

### Variant: Extended Post-Event Handoff

Some templates (like train_004) decompose the output further with `badge_decisions`,
`campaign_member_actions`, `badge_only_contacts`, and separate sponsor/opportunity summary
objects. The same data flows apply; map results to the template's specific structure.

**Badge decisions** record each badge with classification, crm_action, and exclusion_reason.
**Campaign member actions** record each known campaign member subject with its target status.
**Badge-only contacts** are qualified leads where no CRM contact exists — their normalized
contact facts populate this list.

---

## Trade-Show Prospecting

**Trigger**: Prompt gives a `show_id` and mentions exhibitors, trade show,
meeting interest, or campaign prospecting.

### Step 1: Gather Data

- `GET /api/tradeshows/{show_id}` — show metadata
- `GET /api/tradeshows/{show_id}/exhibitors` — exhibitor list
- `GET /api/tradeshows/{show_id}/meeting_interest` — demo requests, scores
- `GET /api/crm/accounts` — CRM accounts for matching
- `GET /api/crm/contacts` — CRM contacts
- `GET /api/policies` — qualification rules, platform definitions, opportunity amounts

### Step 2: Classify Exhibitors

For each exhibitor:

1. Check `relationship_type` against the campaign's target criteria (from policies)
2. Check `platforms` against campaign platform coverage (AUV, ROV, Underwater Camera)
3. If both checks pass → **qualified**
4. If not qualified but close (wrong relationship_type) → **near miss** for exclusion list

Exclusion reasons map from relationship_type:
- Distributor → `distributor_only`
- Service provider → `service_only`
- Sensor vendor → `sensor_vendor_only` (or `sensor_only` depending on template enum)
- Research/academic → `research_only`
- Wrong platform coverage → `not_target_market`

### Step 3: Assign Priority Tiers

From meeting interest data, for each qualified exhibitor:

1. If `requested_demo` and `interest_score` meets threshold for Tier A → `A`
2. If `requested_demo` and `interest_score` meets threshold for Tier B → `B`
3. All other qualified exhibitors → `C`

The exact score thresholds are defined in the prompt or policies. If not specified, use
the answer template's field descriptions for guidance.

### Step 4: CRM Matching

For each qualified exhibitor, match to CRM accounts by `company_name`:

- Found in CRM → `crm_action: "update_existing"`, `crm_account_id` from CRM
- Not found → `crm_action: "create_account"`, `crm_account_id: null`

### Step 5: Sort Qualified Leads

If the template specifies a ranking order:

1. Demo-requested first (`requested_demo: true` before `false`)
2. Then by `interest_score` descending
3. Then by platform count descending (more platforms = broader coverage)
4. Then by `company_name` ascending

Otherwise, sort by the field declared in the template (typically `company_name` or `rank`).

Assign contiguous 1-based rank numbers after sorting.

### Step 6: Compute Aggregates

From the output template's aggregate/summary object:

- `qualified_total` (or `qualified_lead_count`) = number of qualified exhibitors
- `platform_counts` = count of qualified exhibitors covering each platform enum
- `priority_counts` = count of qualified exhibitors per priority tier
- `excluded_near_misses_total` (or `excluded_count`) = number of near misses
- `existing_crm_overlap_count` = number of qualified exhibitors matched to CRM
- `total_estimated_opportunity_usd` = sum of opportunity estimates
- `lead_pipeline_total` = number of qualified leads × event opportunity amount (if applicable)

### Step 7: Excluded Exhibitors

List all near-miss exhibitors with their `company_id`, `company_name`, `relationship_type`
(or `exclusion_reason`), and `crm_action: "no_import"`. Sort by `company_name` ascending.

---

## Import Batch Preparation

**Trigger**: Prompt gives a batch id, mentions raw contacts, suppression,
or CRM import preparation.

### Step 1: Gather Data

- `GET /api/import_batches/{batch_id}` — batch metadata, campaign code
- `GET /api/import_batches/{batch_id}/raw_contacts` — raw rows
- `GET /api/import_batches/{batch_id}/suppression` — suppressed identifiers
- `GET /api/crm/accounts` — CRM accounts
- `GET /api/crm/contacts` — CRM contacts
- `GET /api/policies` — dedup rules, source priorities, suppression rules

### Step 2: Remove Unusable Rows

Remove rows where `contact_name` is empty or missing. Reason: `missing_contact`.
These go into `removal_summary.removed_rows`.

### Step 3: Apply Suppression

For each surviving row, check if normalized email or domain matches any
suppression-list entry. Remove suppressed rows. Reason: `suppressed`.

### Step 4: Deduplicate

Within the surviving rows:

1. Normalize the dedup field (typically email: lowercase, trimmed)
2. Group rows by the normalized dedup key
3. For each group with multiple rows, select the winner:
   - Pick the row with the highest-priority source (source priority is defined in policies)
   - Tiebreaker: earliest `captured_at` timestamp
4. All other rows in the group are duplicates. Reason: `duplicate`
5. Build `duplicate_keys` entries: one per dedup group that had multiples, with `key`, `winner_row_id`, and `removed_row_ids` list

### Step 5: Classify Survivors

For each winning (non-removed) row:

1. Match to CRM account by `company_name`. If found → `crm_action: "update_existing"`, set `existing_account_id`. If not → `crm_action: "create_account"`, `existing_account_id: null`
2. Match contact to CRM contacts by normalized email within the matched account. If found → set `existing_contact_id`. If not → `existing_contact_id: null`
3. Normalize email and phone:
   - Email: lowercase, trimmed. Empty string if none.
   - Phone: digits only. Empty string if none.
4. `clean_contact_id` = `source_row_id` (the winning row's id)

### Step 6: Build Summaries

**duplicate_summary**:
- `duplicate_removed_count` = total rows removed as duplicates
- `duplicate_keys` list sorted by `key` ascending

**removal_summary**:
- `unusable_removed_count` = rows removed for missing contact
- `suppressed_removed_count` = rows removed for suppression
- `removed_rows` list sorted by `row_id` ascending, each with `row_id` and `reason`

**import_action_totals**:
- `create_account` = clean contacts with `crm_action: "create_account"`
- `update_existing` = clean contacts with `crm_action: "update_existing"`
- `no_import` = rows that were removed (unusable + suppressed + duplicates)
- `suppress` = rows removed by suppression

**campaign_member_import_count** = number of clean contacts (survivors)

### Step 7: Sort Clean Contacts

Sort `clean_contacts` by `clean_contact_id` ascending (or as template specifies).

---

## Cross-Family Patterns

### Fetch Order

Always call `GET /api/policies` in the first batch of parallel requests. Policies
inform classification decisions that cascade through all subsequent steps.

### Normalization Is Required

Every task requires email normalization (lowercase, trimmed) and phone normalization
(digits only). Do this at the point of contact extraction, not as a final pass.

### Template Is Canonical

The answer template defines: key names, allowed enum values, sort orders, numeric types,
date formats, and which fields are required vs optional. If the template uses
`sponsor_status` (train_004) instead of `status` (train_001), use that exact key.
Map the business logic to the template's vocabulary — do not force the template into
a single vocabulary.

### Entity Joins Use Business Keys

Join entities across endpoints using business keys, not internal IDs unless
available:

- Sponsors ↔ Invoices: by `invoice_id`
- Badges ↔ CRM Accounts: by `company_name` matching `account_name`
- Badges ↔ CRM Contacts: by normalized email
- Exhibitors ↔ CRM Accounts: by `company_name` matching `account_name`
- Import rows ↔ CRM Accounts: by `company_name` matching `account_name`
