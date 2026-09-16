---
name: harborcrm-handoff
description: Post-event and post-tradeshow CRM handoff workflows for HarborCRM, including sponsor reconciliation, lead qualification, import-batch cleaning, and tradeshow-prospecting campaigns. Use when a task requires cross-referencing HarborCRM event, tradeshow, finance, CRM, import-batch, and policy endpoints to produce a template-conforming JSON handoff, qualification, or import summary. Triggers on event/show/batch identifiers combined with HarborCRM API URLs and structured output templates. Not for general CRM administration or ad-hoc API exploration.
---

# HarborCRM Handoff

## Overview

This skill covers multi-endpoint HarborCRM reconciliation and handoff workflows: post-event sponsor audits, tradeshow lead qualification, import-batch cleaning, and ranked prospecting summaries. Every task follows the same core loop: fetch all relevant endpoints, cross-reference records, apply policy rules, compute finances, classify CRM actions, and produce template-conforming JSON.

## Workflow

Follow these steps in order. Every step is required unless the task template omits the relevant data category.

### 1. Identify the subject and template

Read the task prompt to extract:

- The subject identifier (event_id, show_id, or batch_id)
- The output template from input/payloads/answer_template.json
- The base API URL (supplied by the runner as TASK_ENV_BASE_URL)

Read the template carefully. Every key, enum value, and ordering rule it declares is a hard constraint on the output. Do not add keys the template does not declare. Sort lists exactly as the template specifies.

### 2. Fetch all relevant data

Use scripts/fetch_api.py to gather all endpoints needed for the task in one call, or issue individual curl/HTTP requests. Which endpoints to fetch depends on the subject type:

Event-based tasks (event_id):
- /api/events/{event_id}
- /api/events/{event_id}/orders
- /api/events/{event_id}/badges
- /api/events/{event_id}/sponsor_packages
- /api/finance/invoices?event_id={event_id}
- /api/crm/accounts
- /api/crm/contacts
- /api/crm/opportunities?event_id={event_id}
- /api/crm/campaign_members?event_id={event_id}
- /api/policies

Tradeshow-based tasks (show_id):
- /api/tradeshows/{show_id}
- /api/tradeshows/{show_id}/exhibitors
- /api/tradeshows/{show_id}/meeting_interest
- /api/crm/accounts
- /api/crm/contacts
- /api/policies

Import-batch tasks (batch_id):
- /api/import_batches/{batch_id}
- /api/import_batches/{batch_id}/raw_contacts
- /api/import_batches/{batch_id}/suppression
- /api/crm/accounts
- /api/crm/contacts
- /api/policies

Always include /api/policies. Policy payloads contain business rules (allowed statuses, exclusion criteria, follow-up windows, opportunity amounts, qualifying platforms) that govern classification and arithmetic. Do not hard-code policy values; read them fresh.

For the full endpoint catalog including optional filters and response shapes, see [references/api_reference.md](references/api_reference.md).

### 3. Cross-reference records

Build in-memory lookup maps after fetching:

- Accounts: index by account_id and by normalized company name (lowercase, stripped)
- Contacts: index by account_id and by normalized email
- Campaign members: index by event_id + account_id or contact_id
- Invoices: index by event_id + account_id
- Badges: group by event_id
- Orders / sponsor packages: group by event_id + account_id
- Exhibitors: index by company_id
- Meeting interest: index by company_id
- Suppression list: index by email (lowercase, trimmed)
- Policies: parse into structured lookup by rule name

Use these maps for every classification and decision step that follows.

### 4. Apply policy rules

Policy documents from /api/policies contain the rules that govern:

- Which platform/product types qualify an exhibitor or lead
- Which badge types are business vs non-business
- Sponsor status mappings (paid_deferred, open_invoice, proposal_only)
- Exclusion criteria (sponsor attendees, disqualified accounts, non-business badges, suppressed contacts)
- Follow-up due date offsets (business days from a base date, typically event end or today)
- Opportunity amounts per event/show or per priority tier
- Deduplication keys and winner-selection rules for import batches
- Suppression-match rules

Parse the policy document fully before making any classification decisions. If a policy value seems missing, infer the nearest matching rule or use reasonable defaults, but note the assumption.

### 5. Classify records

#### Sponsor status (event tasks)

For each account that has an order for the event:
- If invoice exists and paid_amount >= total_amount: status is paid_deferred
- If invoice exists and paid_amount < total_amount: status is open_invoice
- If no invoice but a sponsor order exists: status is proposal_only
- Package amount comes from the order or sponsor package

#### Lead qualification (event tasks)

A non-sponsor badge is a qualified lead when:
- The badge type is a business badge per policy
- The account is not disqualified in CRM (check CRM account status)
- The contact/company is not associated with any sponsor account for this event

#### Exhibitor qualification (tradeshow tasks)

An exhibitor is qualified when:
- Its platforms (from exhibitor data and meeting interest) match the campaign target platforms per policy
- It is not a distributor-only, service-only, sensor-vendor-only, or research-only entity per policy

#### Import-batch classification

For each raw contact row:
- Check suppression: if email matches suppression list, mark suppress
- Check duplicates: group by dedup key (typically email), select winner per policy (earliest timestamp, or highest-quality source), mark others duplicate
- Check missing contact: if contact name is empty/missing, mark missing_contact
- Check CRM existence: if company matches an existing CRM account and contact matches an existing CRM contact, mark update_existing; if company matches but contact does not, mark update_existing with existing_account_id set; if neither matches, mark create_account

### 6. Compute financial summaries

- Sponsor revenue: sum package amounts by status. open_invoice_balance is the sum of (total_amount - paid_amount) across open invoices.
- Lead pipeline: multiply each qualified lead account count by the event lead opportunity amount (from policy or event data).
- Opportunity estimates: for tiered tasks, apply the tier-to-USD mapping from policy or the task prompt.

All monetary values are integers (USD).

### 7. Determine CRM actions

For each record that makes it into the output, assign a CRM action:

- create_account: account does not exist in CRM
- update_existing: account exists in CRM; update with new data
- create_contact: contact does not exist in CRM under the matched account
- update_existing (contact): contact already exists
- add_campaign_member / create (campaign member): not yet a campaign member for this event
- no_action: already a campaign member with correct status
- no_import: suppressed, excluded, or unusable

Derive action counts from the final classification results, not from intermediate steps.

### 8. Compute follow-up dates and task counts

Follow-up due dates are typically:
- Lead follow-up: N business days after the event end date (from /api/events/{event_id})
- Sponsor finance follow-up: N business days after the event end date, or an earlier offset

Read the offset from policy. Count business days by skipping Saturdays and Sundays.

Task counts:
- Lead task count = number of qualified lead accounts
- Sponsor finance task count = number of sponsor accounts with open_invoice or proposal_only status
- Sponsor finance accounts = the account names for those statuses, sorted ascending

### 9. Rank and sort (tradeshow ranking tasks)

When the template requires ranked output:
- Primary sort: requested_demo true first
- Secondary sort: interest_score descending
- Tertiary sort: platform count descending (broader coverage first)
- Quaternary sort: company_name ascending

Assign ranks as 1-based contiguous integers. Assign priority tiers and opportunity amounts per the task tier-assignment rules.

### 10. Produce the output

Construct the JSON object with exactly the keys and shape declared in the template. Validate before submitting:

- All required keys are present
- No extra keys beyond the template
- All enum values match allowed values exactly
- All lists are sorted per template ordering rules
- All counts match the records listed
- Monetary values are integers
- Dates use YYYY-MM-DD format
- Normalized emails are lowercase and trimmed
- Normalized phones are digits only

Return the JSON object with no surrounding prose.
