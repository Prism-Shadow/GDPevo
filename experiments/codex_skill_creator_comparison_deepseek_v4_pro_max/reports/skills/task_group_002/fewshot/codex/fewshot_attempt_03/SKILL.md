---
name: medbridge-reconciliation
description: Cross-check MedBridge Sales Ops API records for quote revision packages, RFQ module quotes, and engagement/milestone reconciliations. Use when answering tasks that require verifying customer, quote, catalog, freight, policy, opportunity, invoice, payment, revenue-journal, event, and voucher data from the MedBridge Sales Ops API and filling a structured JSON answer template.
---

# MedBridge Reconciliation

Query the MedBridge Sales Ops REST API and fill a structured JSON answer template. The task runner provides the base URL as `<TASK_ENV_BASE_URL>`; the API is read-only with no authentication required.

## Workflow selection

Read the task prompt and the provided answer template (`input/payloads/answer_template.json`) to determine which workflow applies:

- **Quote revision with freight** — prompt mentions a quote ID (e.g. `Q-TR-*-*`), a product code, and freight options. See [references/quote_revision.md](references/quote_revision.md).
- **RFQ module quote** — prompt mentions an RFQ ID (e.g. `RFQ-TR-*-*`), module-level quoting, and EXW-only terms. See [references/module_rfq.md](references/module_rfq.md).
- **Engagement reconciliation** — prompt mentions an opportunity ID (e.g. `OPP-TR-*`), milestone phases, invoices, payments, revenue recognition, events, and vouchers. See [references/engagement_reconciliation.md](references/engagement_reconciliation.md).

For API endpoint descriptions and data model details, see [references/api_schema.md](references/api_schema.md).

## General rules

### Money

All USD amounts as numbers with exactly two decimal places. Compute totals by summing source amounts, not by rounding intermediate values separately.

### Dates

ISO `YYYY-MM-DD` format. Nullable date fields use `null` (JSON null literal) when there is no date.

### Enum values

Use only the enum values declared in the provided `answer_template.json`. Map API string values to template enums as described in each workflow reference.

### ID stability

Use stable record IDs from the API. Do not invent IDs.

### Quote date as reference date

When the task provides a `quote_date`, use it as the reference date for determining freight validity and offer expiration. When the task provides a current business date or "as of" date, use that for aging comparisons (due dates, collections).

### Policy precedence

Policy rules from the API's `/api/policies` endpoint encode the business logic. When a policy exists for a decision point, follow it. Do not hardcode payment terms or freight rules; derive them from the customer record and applicable policies.

### Freight reconfirmation

All freight rates are subject to reconfirmation at final order (POL-FREIGHT-RECONFIRM). Always set `freight_reconfirmation_required: true`.

### Output format

Return only valid JSON matching the provided `input/payloads/answer_template.json`. No markdown, no explanatory text outside the JSON.

### Cautious API handling

- Fetch collection lists (e.g. `GET /api/freight-quotes`) and filter client-side by the linking field. The API has no query parameters beyond `/api/search?q=`.
- Use individual lookups (`GET /api/{collection}/{id}`) only when a specific record ID is already known.
- Do not call judge, health, reset, or reseed endpoints.
