---
name: harbor-crm-handoff
description: Prepare HarborCRM import-ready handoffs from event, tradeshow, and batch data. Use whenever the task mentions HarborCRM, CRM handoff, CRM reconciliation, post-event audit, trade-show prospecting, lead qualification, contact import batch preparation, sponsor finance reconciliation, campaign member import, or any API that exposes events, tradeshows, import batches, finance, or CRM endpoints. Also use when the user gives you a JSON template and asks you to fill it from a REST API that looks like a CRM integration task.
---

# HarborCRM Handoff

Prepare CRM-ready handoffs using the HarborCRM REST API. HarborCRM is a shared marketing workspace that exposes event, tradeshow, finance, import-batch, policy, and CRM data through a set of read-only REST endpoints. The task environment provides the base API URL as `<TASK_ENV_BASE_URL>` — always substitute this placeholder with the actual URL before making requests.

## Core disciplines

HarborCRM handoffs fall into three disciplines that share a common API surface. A single task may combine elements from more than one discipline.

### 1. Post-event handoff (sponsors, leads, campaign members)

Pull event metadata, sponsor orders, badges, invoices, CRM accounts/contacts/opportunities/campaign-members, and policy data. Reconcile everything into an import-ready summary.

Typical workflow:
- Fetch `/api/events/{event_id}`, then its orders, badges, and sponsor_packages
- Fetch `/api/finance/invoices?event_id={event_id}`
- Fetch CRM accounts, contacts, opportunities filtered by event_id, and campaign members
- Fetch `/api/policies` for controlled status enums
- Cross-reference badge contacts against sponsor ticket_contacts and CRM records
- Classify each sponsor's finance status, each badge, and each campaign member
- Compute follow-up dates from the event end_date plus followup_days_after_end

### 2. Trade-show prospecting

Qualify exhibitors from a tradeshow for a specific campaign using exhibition and meeting-interest data.

Typical workflow:
- Fetch `/api/tradeshows/{show_id}`, then its exhibitors and meeting_interest
- Fetch `/api/crm/accounts` and `/api/contacts` for existing CRM overlap
- Fetch `/api/policies` for platform enums and qualification guidance
- Read exhibitor descriptions to classify platform coverage and relationship type
- Apply tier rules from the policy and ranking instructions in the prompt
- List qualified leads with enrichment and excluded near-misses with controlled reasons

### 3. Batch import preparation

Clean a raw contact batch for CRM import: deduplicate, suppress, normalize, and classify.

Typical workflow:
- Fetch `/api/import_batches/{batch_id}`, its raw_contacts, and its suppression records
- Fetch `/api/crm/accounts` and `/api/contacts` for existing-record matching
- Fetch `/api/policies` for hygiene rules
- Deduplicate on normalized email, keeping the row with the richest data
- Remove rows that match a suppression record (email or phone)
- Remove rows with unusable contact data (blank email AND blank phone, or blank contact_name)
- Classify each surviving clean contact as create_account, update_existing, no_import, or suppress
- Tally import action totals and campaign-member counts

## API endpoint reference

See [references/api_endpoints.md](references/api_endpoints.md) for the complete catalog of HarborCRM endpoints, response shapes, and field descriptions. Read that reference when you need to understand the exact fields returned by any endpoint.

## Cross-cutting rules

These rules apply across all three disciplines unless the prompt overrides them.

### Email normalization

Normalize every email address to its canonical form before matching or writing it into output:
- Trim leading and trailing whitespace
- Convert to lowercase
- An empty or whitespace-only email after trimming becomes the empty string `""`

Always match on normalized emails. A deduplication key like `email:dana.ruiz@helioware.example` must use the normalized form.

### Phone normalization

Normalize every phone number to digits-only:
- Strip all non-digit characters: spaces, parentheses, hyphens, dots, plus signs
- If the result is empty (no digits), write `""`
- Leading `1` (US country code) is kept as-is; do not strip it unless the prompt says otherwise

### Date calculations

Follow-up dates are computed from the event end_date:
- `lead_followup_due_date` = event end_date + followup_days_after_end
- `sponsor_finance_due_date` = event end_date + sponsor_followup_days_after_end
- Use ISO 8601 date format (YYYY-MM-DD)

### CRM action classification

When deciding whether a lead requires account creation or an update:
- If a matching CRM account exists (matched by account_id, domain, or normalized company name), the account action is `update_existing`
- If no matching CRM account exists, the action is `create_account`
- Existing CRM contacts matched by normalized email trigger `update_existing` for the contact; otherwise the contact action is `create_contact`
- Campaign member actions are always `add_campaign_member` for new leads or when the contact is not already a campaign member for this event; use `update_campaign_member` for existing members whose status needs to change

### Sorting

Every output list must be sorted exactly as specified in the answer template:
- Account/company lists are sorted by `account_name` or `company_name` ascending (lexicographic, case-sensitive)
- Platform lists are sorted in the enum order given in the policy or template: `["AUV", "ROV", "Underwater Camera"]`
- Removal/duplicate summaries are sorted by their natural key ascending (row_id, key, etc.)
- When the template says nothing about sorting, default to ascending by the primary name field

### Controlled enums

Always read `/api/policies` first. The policy response defines the allowed enum values for each business domain:
- Sponsor statuses: `paid_deferred`, `open_invoice`, `proposal_only`, `not_sponsor`
- Platform enums: `AUV`, `ROV`, `Underwater Camera`
- Exclusion reasons: `sponsor_attendee`, `existing_disqualified`, `inactive_sponsor_record`, `non_business_badge`, `distributor_only`, `service_only`, `sensor_only` (or `sensor_vendor_only`), `research_only`, `not_target_market`, `duplicate`, `missing_contact`, `suppressed`

Never invent enum values. Use exactly the ones from the policies endpoint and the answer template.

### Sponsor finance reconciliation

When reconciling sponsor orders and invoices:
- `paid_deferred`: invoice status is `paid_deferred` and paid_amount equals the deferred amount
- `open_invoice`: invoice status is `open` and paid_amount is less than amount; open_balance = amount - paid_amount
- `proposal_only`: an order exists with order_status `proposal_sent` but no invoice exists for that account/event
- `not_sponsor`: an order exists with order_status `canceled` — these are excluded from active sponsor statuses

For sponsor revenue totals, sum the package amounts (order amounts) by status. `open_invoice_balance` is the sum of open_balance across all open-invoice sponsors.

### Badge classification

When processing event badges:
- `sponsor` badge_type → classify as `sponsor_attendee`; crm_action is `no_action`; exclusion_reason is `sponsor_attendee`
- Non-business badge types (`press`, `student`, `academic`) → `excluded` with reason `non_business_badge`; crm_action is `no_import`
- Badges from accounts with a non-null CRM disqualified_reason → `excluded` with reason `existing_disqualified`; crm_action is `no_import`
- Badges with missing contact data (no contact_name) → `excluded` with reason `missing_contact`; crm_action is `no_import`
- All other attendee badges → `qualified_non_sponsor_lead`

### Batch deduplication

When cleaning an import batch:
- Deduplicate on normalized email as the key
- For duplicate rows, pick the winner by: highest data richness (has both email and phone > has only email), then most recent captured_at timestamp, then lowest row_id
- Removed duplicate rows get reason `duplicate`
- Suppressed rows (matching email or phone in the suppression list) get reason `suppressed` and crm_action `suppress`
- Rows with blank contact_name, or blank email AND blank phone after normalization, get reason `missing_contact` and crm_action `no_import`

### Opportunity amounts

When assigning opportunity amounts to qualified non-sponsor leads:
- Default: use the event's `lead_opportunity_amount` from the event metadata
- If the prompt specifies tiered amounts (e.g., A=$120000, B=$90000, C=$50000), use those instead
- For events without an explicit lead_opportunity_amount, use the amount from the answer template's guidance

## Response format

Always return a single JSON object with no explanatory prose outside it. The output must match the provided answer template exactly: every required key present, every field typed correctly, every list sorted as specified. Do not add keys the template does not declare. Use `null` for absent values, `""` for empty strings, and `0` for zero amounts.

Currency amounts are always integers (whole USD).

## Parallel fetches

When the task requires data from multiple endpoints, fetch them in parallel. The HarborCRM API supports concurrent reads. Group independent calls together to minimize round-trips. A typical post-event handoff needs: event metadata, orders, badges, invoices, CRM accounts, CRM contacts, opportunities, campaign members, and policies — all of which can be fetched simultaneously.
