---
name: finance-api-batch-review
description: Review finance/ERP batch operations by querying a shared task-environment API, cross-referencing records across multiple endpoints, and producing structured JSON classification results. Use this skill whenever the user needs claims reconciliation, vendor onboarding compliance checks, prepaid amortization close, stale AP snapshot correction, account-change payment release, or any finance-operations batch review that depends on a task-environment API and answer templates. Even if the user describes the task in operational rather than technical terms (e.g., "close out these expense claims", "review this vendor batch", "reconcile prepaid accounts"), use this skill.
---

# Finance API Batch Review

This skill covers finance-operations batch review tasks where you query a shared ERP/Finance API, cross-reference evidence from multiple endpoints, and produce a structured JSON classification result.

## Core workflow

Every task in this domain follows the same sequence. Execute steps in order and do not skip any.

### 1. Read the task prompt and all payload files

Start by reading the prompt (`input/prompt.txt` or equivalent) and every file under `input/payloads/`. The payloads always include an answer template that defines the exact output schema. Other payloads provide task-specific inputs like candidate ID lists, snapshot CSVs, or batch JSON. Do not proceed until you understand:

- Which record types are in scope (claims, vendors, invoices, businesses, etc.)
- Which API endpoints you need to query
- The output schema and its required fields, ordering, and precision rules

### 2. Discover the API

The task environment provides a base URL through `<TASK_ENV_BASE_URL>`. Use this to reach all endpoints. Start by calling `GET /endpoints` to confirm which routes are available. Endpoints may appear under plain paths (like `/claims`) or under `/api/` prefixes (like `/api/claims`). Prefer the `/api/` variant when both exist.

Query every relevant endpoint. These are the common categories and how to use them:

- **Records by ID**: `/api/claims/{claim_id}`, `/api/vendors/{vendor_id}`, `/api/compliance/ownership/{business_id}`, `/api/compliance/registry/{business_id}`, `/api/compliance/screening/{business_id}`, `/api/compliance/bank/{business_id}`. Query one per candidate ID. Parallelize these calls when you have multiple IDs.

- **List endpoints**: `/api/claims`, `/api/ap/bills`, `/api/ap/payments`, `/api/vendors`, `/api/compliance/objects`, `/api/prepaids/invoices`, `/api/prepaids/gl-balances`, `/api/ap/aging`, `/api/close/logs`. These return collections. Query each once, then filter client-side for the IDs you care about. Do not page through them with looped calls; the API returns what is relevant.

- **Idiosyncratic patterns**: Some endpoints behave differently from the others. Read every response you get and note its actual structure rather than assuming it matches a generic pattern. If an endpoint returns a top-level object keyed by IDs rather than an array, work with what you receive.

### 3. Collect and cross-reference evidence

For each candidate ID in the batch, gather all relevant records and link them.

- **Claims tasks**: For each claim ID, retrieve the claim record, then find the associated AP bill (match by claim ID or vendor context), then find any payment records linked to that bill. Distinguish between approved/paid/void/scheduled bill statuses and cleared/pending/none payment statuses.

- **Vendor/compliance tasks**: For each business ID, retrieve the vendor record and the compliance records (ownership, registry, screening, bank). Compare compliance data against the task's review date or thresholds.

- **Prepaid reconciliation tasks**: Retrieve the invoice records for the scoped IDs and the GL balances for the scoped accounts. Compute amortization from the invoice's term and start-date fields using straight-line monthly amortization (original_amount / term_months). Derive cumulative amortization through the close period and the remaining schedule balance.

- **Multi-source correction tasks**: When the task provides a stale snapshot alongside the live API, treat the API as the system of record. Compare every field in the snapshot to the live data and flag discrepancies. Never trust the snapshot over the API.

When linking records across endpoints, match by the same ID field that appears in the local batch payload. If the API returns records keyed or filtered by a different identifier, use the logical connection (e.g., claim to bill by claim ID, bill to payment by bill ID, business to vendor by business ID through the vendor record).

### 4. Apply classification logic

Each task asks you to categorize candidates based on the evidence. Build your classification from the evidence, not from the snapshot or from assumptions about what "should" be present.

Common classification patterns:

- **Paid/settled**: A claim is settled only when the linked AP bill matches the claim amount AND the bill has a cleared payment for the full bill amount. Partial payments are not settled.

- **Payable/releasable**: A claim has a valid unpaid AP bill (status approved or scheduled, amount matches) with no blocking conditions. The AP open balance for such claims is the bill amount minus cleared payments.

- **Blocked/escalated**: A candidate is blocked when the claim status is not approved, the bill is void, the amount mismatches, the vendor is on hold, compliance flags are present, the license is expired relative to the review date, a bank is closed or name-mismatched, screening did not run, or required documents are missing.

- **Close/ready status**: The batch-level status is `blocked` when any candidate is blocked. It is `open_payables` (or `needs_ap_refresh`) when no items are blocked but valid unpaid AP bills remain. It is `ready_to_close` (or `ready_to_send`) when every candidate is paid or requires no further AP action.

- **Stale snapshot corrections**: For each candidate, compare the snapshot row to the live API data and assign the correction that best describes the discrepancy. Common corrections: mark an in-flight payment when the snapshot says "none" but the API shows a payment in progress; replace with matched paid bill when the snapshot shows scheduled but the API shows paid; exclude for amount/vendor mismatch; ignore a void bill the snapshot listed as active; block an unapproved claim the snapshot listed as approved.

Do not invent new classification values. Use only the values that appear in the answer template's allowed-value lists.

### 5. Build the output JSON

Populate the answer template exactly. Follow these rules for every task:

- **Key ordering**: The answer template often specifies a `top_level_order` or `required_top_level_keys` array. Produce keys in that exact order. If no explicit order is given, list keys in the order they appear in the template fields object.

- **List ordering for IDs**: Sort ID lists ascending by their natural string sort order unless the template specifies a different ordering. Use lexical ascending for strings like `CLM-YYYY-NNNN` (digits sort before letters, and numeric subfields sort numerically).

- **Currency values**: All amounts are in USD. Use two decimal places (cents). Round to two decimals after every arithmetic operation to avoid floating-point drift. Store and transmit as numbers, not strings.

- **Booleans**: Use JSON `true`/`false`, not string `"true"`/`"false"`.

- **Enums**: Use the exact string values from the template's `allowed_values` array. Match case exactly.

- **Empty lists**: Use `[]`, not `null` or omitted keys, when a list field has no members.

- **Descending from template**: Every field the answer template defines as required must appear in the output. Do not add extra fields beyond what the template declares unless `additional_properties_allowed` is explicitly true.

### 6. Verify before returning

Before delivering the output, check these common pitfalls:

- Did you query all relevant endpoints, not just the ones you thought you needed?
- Did you interpret bill and payment statuses correctly (the status string values, not assumptions about what they mean)?
- Did you compute the AP open balance as bill amount minus cleared payments, using only payable claims?
- Did you count reviewed claims as the number of claim IDs in the batch, not some subset?
- Did you set `close_log_required.required` to true only when close log IDs actually exist?
- Did you flag an invoice as exceptional when its ending balance is zero or near-zero, or when it has a default or missing term, or when it begins amortizing in the close month itself (zero cumulative before current month)?
- Did you use the review date (not today's date) for license-expiry and other date-sensitive checks?
- Did you sort every ID list the template asks you to sort?
- Did you format all currency values to exactly two decimal places?

## Exception and flag patterns

These patterns recur across task types. Apply them based on what the specific template asks for.

**Default/missing term**: An invoice has a default or missing term when its `term_months` field is absent, null, zero, or matches a common default value that the invoice metadata or the task itself signals as a system default rather than a negotiated term.

**Exception invoices**: Flag an invoice as exceptional when any of these is true: the ending balance after amortization through the close period is zero or within one cent of zero, the invoice has a default or missing term, the invoice began amortizing in the close month (cumulative amortization through the prior month is zero), or the invoice's amortization schedule produces an anomalous pattern compared to others in the same account.

**Variance flag**: The variance flag is true when the absolute difference between schedule ending balance and GL ending balance exceeds the task's stated threshold, or when any discrepancy exists if no threshold is stated.

## Handling the API

- Use the base URL exactly as provided. Do not strip or add path segments beyond what the endpoint requires.
- Call list endpoints once and filter in memory. Do not paginate or loop.
- When an endpoint is listed both as `/something` and `/api/something`, call the `/api/` variant. If only one variant exists, use it.
- If an endpoint returns an unexpected structure, read the full response and adapt. The API is the system of record; trust it over local snapshots.
- For tasks that reference `close/logs` or `/api/close/logs`, filter logs by the claim IDs in scope, not by arbitrary date ranges.

## Task environment reference

See [references/api-endpoints.md](references/api-endpoints.md) for the endpoint catalog and common query patterns.
