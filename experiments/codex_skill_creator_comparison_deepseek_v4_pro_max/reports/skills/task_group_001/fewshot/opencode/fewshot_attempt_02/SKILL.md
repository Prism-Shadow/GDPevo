---
name: harbor-crm-handoff
description: Prepare CRM-ready handoff JSON for HarborCRM post-event, trade-show, and import-batch workflows. Use whenever the task references HarborCRM, a CRM handoff, event reconciliation, trade-show lead qualification, import-batch cleaning, campaign-member preparation, or producing structured JSON output from the HarborCRM REST API (events, CRM, finance, trade-shows, import-batches, policies). Even if the prompt does not name HarborCRM explicitly, use this skill when the task involves querying multiple API endpoints to cross-reference and classify business records into a structured handoff document.
---

# HarborCRM Handoff Skill

Prepare structured CRM handoff JSON by querying the HarborCRM REST API, cross-referencing records across endpoints, applying policy-driven rules, normalizing data, and conforming precisely to a supplied answer template.

## Core workflow

Every HarborCRM handoff task follows the same sequence. Execute it in order unless the task prompt or template clearly overrides a step.

### Step 1: Read the answer template

Identify the answer template file (typically `input/payloads/answer_template.json`). Read it first — it defines the exact output shape, required keys, allowed enum values, sorting rules, and field types. Treat every constraint in the template as mandatory.

### Step 2: Read the task prompt

The prompt contains the business context: which event / trade-show / import-batch to operate on, which campaign code to use, any special filtering or tier-assignment rules, and follow-up due-date logic. Read it alongside the template.

### Step 3: Fetch policy data

Call `GET /api/policies` first. Policies contain the rules that drive classification: platform-to-relationship mappings, suppression criteria, tier thresholds, opportunity amounts, and exclusion logic. Use policy data as the authority for all classification decisions. Re-read relevant policy sections when a classification question arises.

### Step 4: Fetch domain data

Using the API base URL supplied by the runner (`<TASK_ENV_BASE_URL>` or the task environment URL), fetch all relevant endpoints. Fetch in parallel when endpoints are independent. The reference [API reference](references/api-reference.md) documents every endpoint and its response shape.

Fetch all endpoints that the template or prompt implies you need. Common combinations:

- **Event handoff**: `/api/events/{event_id}`, `/api/events/{event_id}/orders`, `/api/events/{event_id}/badges`, `/api/events/{event_id}/sponsor_packages`, `/api/finance/invoices?event_id={event_id}`, `/api/crm/accounts`, `/api/crm/contacts`, `/api/crm/opportunities`, `/api/crm/campaign_members?event_id={event_id}`
- **Trade-show prospecting**: `/api/tradeshows/{show_id}`, `/api/tradeshows/{show_id}/exhibitors`, `/api/tradeshows/{show_id}/meeting_interest`, `/api/crm/accounts`, `/api/crm/contacts`
- **Import-batch cleaning**: `/api/import_batches/{batch_id}`, `/api/import_batches/{batch_id}/raw_contacts`, `/api/import_batches/{batch_id}/suppression`, `/api/crm/accounts`, `/api/crm/contacts`
- **Finance-heavy**: add `/api/finance/invoices?account_id={account_id}` when you need per-account invoice detail

### Step 5: Cross-reference and classify

This is the core intellectual step. See [Cross-referencing patterns](references/patterns.md) for detailed rules for each handoff type. In brief:

1. Join records across endpoints by IDs (`account_id`, `event_id`, `show_id`, `batch_id`)
2. Apply policy rules to classify each record (sponsor status, lead qualification, exclusion reason, CRM action, campaign-member action)
3. Assign controlled enum values from the template's allowed-value lists
4. Normalize contact facts: email → lowercase trimmed; phone → digits only
5. Compute aggregate counts and totals

### Step 6: Sort output

Sort every list exactly as the template specifies. Common sort orders:
- Accounts by `account_name` ascending
- Contacts within a company by `contact_name` ascending
- Badge decisions by `badge_id` ascending
- Ranks by rank number ascending
- Platforms in enum order: `AUV`, `ROV`, `Underwater Camera`
- Excluded records by `company_name` ascending, then `contact_name` ascending
- Duplicate keys and removed rows by their ID ascending

### Step 7: Produce the JSON

Return exactly one JSON object. Match every required top-level key from the template. Use only the field names, types, and enum values declared in the template — do not invent new fields. Write no explanatory prose outside the JSON object. Use integer types for counts and USD amounts.

If the template declares a `required_value` for a string field (like `"show_id": "marinesense_2026"`), use that exact value.

## When the template is sparse

Some templates describe the output shape with field specs rather than populated example objects. When that happens, infer the exact keys and types from the template's `field_definitions`, `required_keys`, `item_required_keys`, and `allowed_values`. Build the output object from those declarations.

Some templates use notation like `"type": "list<object>"` or `"type": "list[object]"` — treat these as arrays of objects with the listed `required_object_keys` or `item_required_keys`.

## Cross-referencing resources

- [API reference](references/api-reference.md): Every endpoint, its response shape, and how records join
- [Processing patterns](references/patterns.md): Step-by-step classification rules for each handoff type (event handoff, trade-show prospecting, import-batch cleaning, event reconciliation)
