---
name: finance-audit-api
description: Execute finance and ERP audit tasks that cross-reference records from a shared JSON REST API. Use this skill whenever the user asks you to review expense claims, vendor onboarding batches, prepaid close reconciliations, stale AP exports, account-change payment releases, or any similar audit workflow that involves calling a task-environment API, cross-referencing multiple record types, and filling a structured JSON answer template with sorted IDs and USD-cent precision.
---

# Finance Audit API Task Solver

This skill covers the recurring pattern of finance/ERP audit tasks that use a
shared JSON REST API as the system of record. The solver must query multiple
API endpoints, cross-reference records (claims against bills against payments,
vendors against compliance checks), derive evidence-based decisions, and output
a JSON result that exactly matches a provided answer template.

## Core principles

**The API is the system of record.** When the task supplies local payload files
alongside an API, the live API responses always take precedence over local
snapshots, CSVs, or cached data. Treat local files as context or hints, never
as authoritative.

**Every field in the answer template must be populated.** Read the template
carefully before starting. Note required keys, enum allowed-values, numeric
precision, and list-ordering rules. Never omit a required field or invent keys
not defined in the template.

**Decisions flow from evidence, not assumptions.** For every classification
(release vs hold, payable vs blocked, reconcile vs variance), point back to
specific API record fields that support the choice. If the API data is
ambiguous or contradictory, flag the item for review rather than guessing.

## Workflow sequence

Follow these steps in order for every audit task:

### 1. Orient from the prompt and template

Read the task prompt and every payload file under `input/payloads/`. Identify:
- The candidate IDs (claim IDs, business IDs, invoice IDs) that scope the review.
- The answer template JSON, including its required keys, enum values, numeric
  precision, and list-ordering rules.
- Which API endpoints the task expects you to call. The prompt will name
  the record types (claims, bills, payments, vendors, compliance, prepaids,
  GL balances, close logs); map each to its endpoint from the API reference.
- The `<TASK_ENV_BASE_URL>` placeholder, which the runner replaces with the
  actual base URL at solve time.

If either file list or exact endpoint list is unclear, infer from the template
fields: each field category usually maps to one or two API endpoints.

### 2. Fetch all relevant API data

Call every endpoint that could hold records for the candidate IDs. Use the
endpoints listed in `references/api_endpoints.md`. Prefer the `/api/`-prefixed
variants when both exist.

For **list endpoints** (`/api/claims`, `/api/ap/bills`, `/api/ap/payments`,
`/api/vendors`, `/api/prepaids/invoices`, `/api/prepaids/gl-balances`,
`/api/close/logs`), fetch the full collection and filter client-side by
candidate IDs. Do not assume the API supports query parameters for filtering.

For **single-resource endpoints** (`/api/claims/{claim_id}`), you may use them
for spot-checks, but prefer the list endpoints for completeness.

For **compliance endpoints** (`/api/compliance/objects`,
`/api/compliance/ownership/{business_id}`, `/api/compliance/registry/{business_id}`,
`/api/compliance/screening/{business_id}`, `/api/compliance/bank/{business_id}`),
call each scoped endpoint for every candidate business ID. The ownership,
registry, screening, and bank endpoints take a business_id path parameter.

### 3. Cross-reference records

Build a mental (or literal) join table linking each candidate ID to every
related record:

- **Claims tasks**: claim -> bill (by claim_id or amount/vendor match) -> payment
  (by bill_id or amount/vendor match). Watch for void bills, paid bills with
  cleared payments, and unmatched amounts.
- **Vendor/compliance tasks**: vendor -> compliance objects -> ownership ->
  registry -> screening -> bank. Each business/vendor ID fans out across
  multiple compliance dimensions.
- **Prepaid tasks**: invoice -> account -> schedule amortization -> GL balance.
  The GL balance is the external control total; the schedule is what the
  invoice records compute.
- **Account-change tasks**: vendor -> compliance (bank, tax ID, license,
  screening) -> risk scores. The account-change events in the payload describe
  what the requester wants; the API data determines whether it is safe.

### 4. Derive classifications and flags

Move systematically from raw API evidence to output fields:

- **Boolean flags**: Set true only when the API record explicitly shows the
  condition. Do not infer a flag from absence of data unless the template
  defines absence as the trigger.
- **Enum decisions** (approve/release vs hold vs escalate, reconciled vs
  variance_review vs requires_reconciliation): choose the most restrictive
  category supported by evidence. If any sub-check fails, the item is at
  minimum not ready/blocked. Reserve escalate for hard-stop conditions
  (sanctions, PEP, closed bank, expired license, vendor on hold).
- **Lists of IDs**: derive from evidence, not from the prompt. For example,
  `crm_required_claim_ids` should list only those claims where the API evidence
  shows an expense-case or AP-link issue, not every blocked claim.
- **Numeric totals**: sum values from the API records that correspond to the
  qualifying subset. For `ap_open_balance_total`, sum bill amounts for payable
  claims that have open (unpaid) bills, ignoring void bills and already-paid
  bills.

### 5. Format the output

- **JSON only**. Unless the template explicitly includes a narrative field,
  return pure JSON. No markdown fences, no explanatory text outside the JSON
  object.
- **Sort all ID lists ascending** by their natural string order (which matches
  the claim-id / business-id format). Use standard lexicographic sort.
- **USD amounts**: always two decimal places, in dollars (not cents unless the
  template explicitly says "cents"). When summing, use full-precision
  arithmetic and round only the final result to two decimals.
- **Empty lists**: use `[]`, never `null` or omission.
- **Boolean fields**: use JSON `true`/`false`, never strings.
- **Enum fields**: use exactly the string values from the template's
  `allowed_values`. Case and spelling must match.
- **Object key ordering**: match the template's `required_top_level_keys` or
  `top_level_order` when provided. For account-level objects, match the key
  order shown in the template.

### 6. Verify before returning

Before delivering the answer, check:
- Every required top-level key is present.
- Every candidate ID appears in at least one output field (classification,
  decision, or balance entry).
- All ID lists are sorted ascending.
- All numeric fields match the template's precision.
- Boolean fields are actual booleans.
- The output parses as valid JSON (no trailing commas, no unquoted keys).

## Common decision patterns

These patterns appear across multiple audit task types. Use them as reasoning
guides, not as hard-coded mappings.

### Claim-to-payment reconciliation

| API evidence | Classification |
|---|---|
| Approved claim + scheduled/approved bill + no payment | Payable (AP open) |
| Approved claim + paid bill + cleared payment matching claim amount | Paid / eligible |
| Claim with void bill | Not ready / blocked |
| Claim missing from API entirely | Not ready / blocked |
| Claim amount != bill amount (and no partial-payment evidence) | Not ready / blocked |
| Bill paid but payment amount != bill amount | Flag for review |

### Vendor compliance decision

| Evidence | Decision |
|---|---|
| All compliance checks clean, license valid, bank matches, no PEP/sanctions | Approve / Release |
| Minor issue (missing document, screening not run) but no hard stops | Awaiting information / Hold |
| Hard stop found (sanctions, PEP, closed bank, expired license, vendor on hold, shell company) | Escalate |

### Prepaid variance

| Condition | Account status |
|---|---|
| |variance| <= threshold, no exception invoices | Reconciled |
| |variance| <= threshold, but exception invoices present | Variance review |
| |variance| > threshold | Requires reconciliation |

### Stale snapshot correction

Compare the local snapshot against live API data row by row. For each claim:
- If the snapshot says "paid" but API shows an active bill: `mark_in_flight_payment`.
- If the snapshot bill is void in the API: `ignore_void_bill`.
- If the snapshot bill is paid in the API with a matching cleared payment: `replace_with_matched_paid_bill`.
- If the API bill amount or vendor differs from the snapshot: `exclude_amount_or_vendor_mismatch`.
- If the API claim status is not approved: `block_unapproved_claim`.
- If the snapshot matches current API state: `current_snapshot_ok`.

## Precision and sorting conventions

- **USD**: always two decimal places (`1234.56`, not `1234.5` or `1234.567`).
  When a balance is zero, write `0.00` or `0.0` as the template specifies.
- **Sorting**: lexicographic ascending. `CLM-2025-0100` comes before
  `CLM-2025-0101` because `"0100" < "0101"`. Use the natural string sort of
  your language — do not parse numeric segments unless the template explicitly
  requires numeric sort.
- **Object key ordering**: when the template provides a `top_level_order` or
  `required_top_level_keys` array, follow that order. For nested objects
  with explicit key lists, follow the template order.
- **Rounding**: compute totals from raw API values (which may have more than
  two decimal places internally), sum at full precision, then round the final
  sum to two decimals using standard round-half-up.

## API interaction notes

- The API base URL arrives as `<TASK_ENV_BASE_URL>` in the prompt. Replace this
  token with the actual URL before making any call.
- All endpoints return JSON. Expect arrays for list endpoints and objects for
  single-resource endpoints.
- The API does not require authentication (as documented in the task
  environment access file).
- If an endpoint returns an empty array or 404 for a specific ID, treat that
  ID as missing from the system of record — this is evidence for
  blocked/not-ready classification.
- Call endpoints in parallel when they are independent of each other.
  For example, fetch all compliance endpoints for all business IDs
  simultaneously rather than sequentially.

## References

- [API endpoints reference](references/api_endpoints.md) — complete list of
  available endpoints, their response shapes, and field meanings inferred from
  the task domain.
