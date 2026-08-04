---
name: finance-erp-batch-review
description: >
  Reusable methodology for finance/ERP batch review tasks that reconcile
  local payloads against a shared REST API.  Covers claims close, vendor
  onboarding, prepaid close, stale-AP snapshot reconciliation, and
  account-change release reviews.  Use this skill whenever the task
  involves batch decisions backed by a finance API and an answer template.
---

# Finance ERP Batch Review Skill

## When to Use

Apply this skill when the task:

- Relies on a shared ERP/finance REST API with a base URL supplied by the
  runner (typically via `<TASK_ENV_BASE_URL>` or similar substitution).
- Includes an `environment_access.md` or equivalent file listing allowed
  endpoints, query mechanics, and authentication rules.
- Provides a local payload directory (`input/payloads/`) containing a
  task-specific batch payload plus an `answer_template.json` that defines
  the exact output schema.
- Requires cross-referencing multiple API resources to make per-item
  decisions (release, block, hold, reconcile, etc.).

## Generic Workflow

### 1. Inventory the Task Inputs

Read every file in the task input directory.  At minimum you will find:

| File | Role |
|------|------|
| `prompt.txt` | Task-specific instructions, batch scope, and business context. |
| `payloads/answer_template.json` | Output schema — types, enums, orderings, precision, and unit rules. |
| `payloads/*.json` (batch payloads) | Local batch data (candidate IDs, scope lists, snapshots). |
| `payloads/*.csv` (optional snapshots) | Stale or reference exports; **not** the system of record. |

### 2. Read the Environment Access File

Locate `environment_access.md` (or equivalent) at the workspace root.  It
defines:

- **Base URL** — the API root (e.g., `http://task-env:9005/`).  The
  runner substitutes this; use it literally as provided.
- **Authentication** — typically none for these task-group environments.
- **Allowed GET endpoints** — the definitive list of callable resources.
- **Query mechanics** — exact-match field-name query parameters, optional
  `limit` and `offset` integers.
- **Detail mechanics** — replace path placeholders (e.g., `{claim_id}`)
  with the identifier string.

### 3. Query the API

For each identifier in the batch, fetch current data from the API:

1. Start with the resource most directly tied to the batch item (e.g.,
   `/claims/{claim_id}`, `/api/vendors/{vendor_id}`).
2. Follow with related resources needed for cross-validation (e.g., bills,
   payments, compliance endpoints).
3. Prefer detail endpoints (`GET /resource/{id}`) for targeted lookups.
   Use collection endpoints (`GET /resource?field=value`) only when
   detail endpoints are unavailable or when bulk context is needed.
4. Respect the endpoint list — do not attempt endpoints not listed in
   `environment_access.md`.

### 4. Reconcile and Decide

**Core principle:** The API is the system of record.  Local payloads
(JSON batches, CSV snapshots) are context only, not authoritative.

For each batch item, apply the decision logic implied by the answer
template's enum values and field descriptions.  Common decision patterns:

- **Binary status checks** — does the item exist in the API?  Is a
  required linked resource present and in the expected state?
- **Field matching** — compare API values against batch-provided
  expectations (e.g., bank last-4, amounts, statuses).  Flag mismatches.
- **Threshold comparisons** — flag when numeric deltas exceed a given
  absolute or relative threshold.
- **Date comparisons** — flag items whose effective dates are expired
  relative to the review date.
- **Count aggregations** — for reporting fields that tally items meeting
  a criterion (e.g., UBO counts, exception counts).

When the answer template distinguishes between "case-level" and
"payment/AP-level" issues, preserve that distinction in your output.

### 5. Build the Output

1. Start from `answer_template.json`.  Read every field's type, enum
   values, units, precision, ordering, and description.
2. Populate every required top-level key.
3. Apply ordering rules:
   - ID lists: **ascending** by the identifier string.
   - Per-item arrays: match the **order of the input payload** (scope
     list or batch file order) unless the template specifies otherwise.
4. Use the precision and unit specified by the template (USD with 2
   decimals unless the template says otherwise).
5. Do **not** include narrative text, commentary, or extra fields outside
   the template schema.
6. Return the JSON object directly.

## Domain-Specific Patterns

These patterns recur across task types.  Use them as starting points;
always defer to the specific answer template and prompt.

### Claims Close Review

- **Endpoints**: `/claims`, `/api/claims`, `/bills`, `/api/ap/bills`,
  `/payments`, `/api/ap/payments`, `/close/logs`, `/api/close/logs`.
- **Classification**: For each claim, determine whether it is *paid*
  (matching paid bill + cleared payment), *payable* (valid open AP bill,
  no blockers), or *blocked* (missing/invalid link, case issue, or
  unapproved claim).
- **CRM vs AP distinction**: "CRM required" means the expense-case owner
  must fix something; other blocked claims need AP-link remediation.
- **Batch status**: `blocked` if *any* item is blocked; otherwise
  `open_payables` if valid unpaid bills remain; otherwise
  `ready_to_close`.
- **AP open balance**: Sum of valid open AP bill amounts for payable
  claims only.

### Vendor Onboarding / Compliance Review

- **Endpoints**: Vendor detail plus compliance sub-resources:
  `/compliance/ownership/{business_id}`,
  `/compliance/registry/{business_id}`,
  `/compliance/screening/{business_id}`,
  `/compliance/bank/{business_id}` (and `/api/...` variants).
- **Per-business decision**: `approve`, `awaiting_information`, or
  `escalate`.
- **UBO counts**: Count unique beneficial-owner names at or above the
  reporting threshold from the ownership endpoint.
- **Hard-stop flags**: Derive from screening, bank status, license
  validity, sanctions, PEP status, and document completeness.  Use the
  exact enum values from the answer template.
- **Overall release**: `true` only if *every* listed business can be
  released.

### Prepaid Close / Amortization Reconciliation

- **Endpoints**: `/prepaids/invoices`, `/gl/balances` (and `/api/...`
  variants).
- **Amortization**: Straight-line monthly from the invoice records.
  March amortization = one month.  Cumulative = months from start through
  the close period.
- **Ending balance**: Original amount minus cumulative amortization.
- **GL variance**: Schedule ending balance minus GL ending balance.
- **Variance flag**: True when `|variance| > threshold`.
- **Default/missing term flag**: Derived from invoice fields indicating
  incomplete or defaulted term data.
- **Account status**: `reconciled`, `variance_review`, or
  `requires_reconciliation` based on variance and term flags.
- **Invoice-level**: Per-invoice amortization, cumulative, ending
  balance, default/missing term flag, and exception flag.

### Stale AP Snapshot Reconciliation

- **Endpoints**: Claims, bills, payments, and close logs.
- **Snapshot vs API**: The local CSV is a past export.  Compare each
  snapshot row against current API state.
- **Correction types**: `current_snapshot_ok` (matches current API),
  `mark_in_flight_payment` (payment appeared after snapshot),
  `replace_with_matched_paid_bill` (different bill ID is now correct),
  `exclude_amount_or_vendor_mismatch` (amounts diverge),
  `ignore_void_bill` (bill is void), `block_unapproved_claim` (claim not
  approved).
- **AP balance**: Open AP balance after applying cleared payments and
  ignoring stale/void rows.
- **Close logs**: Identify close-log entries relevant to the batch and
  report whether they are required.
- **Batch status**: `ready_to_send`, `needs_ap_refresh`, or `blocked`.

### Account-Change Release Review

- **Endpoints**: `/vendors`, `/api/vendors`, plus all compliance
  sub-resources (`/compliance/objects`, ownership, registry, screening,
  bank).
- **Decision**: `release`, `hold`, or `escalate` per business ID.
- **Bank mismatch**: Flag when compliance `bank_account_status` is
  `name_mismatch` or when the bank last-4 does not match the requested
  value in the batch payload.
- **Tax ID validation**: Flag invalid or missing tax IDs from registry or
  vendor records.
- **License expiry**: Flag when the license `valid_until` is before the
  review date.
- **Risk score override**: Flag business IDs with `risk_score >= 70`.
- **Review queue**: Aggregate IDs that need compliance/AP review before
  release.

## Data Formatting Rules

- **Currency**: USD unless the template specifies otherwise.  Use the
  precision stated in the template (typically 2 decimals).
- **ID lists**: Always sorted ascending as strings.
- **Object keys**: Match the template exactly — case-sensitive, no extra
  keys.
- **Enums**: Use only the `allowed_values` listed in the template.  Do
  not invent new values.
- **Booleans**: JSON `true`/`false`, not strings.
- **Integers**: Whole numbers only where the template says `integer`.

## Error Handling

- If an API endpoint returns an empty response or 404 for a known
  identifier, treat the resource as absent — this is evidence for a
  decision, not a fatal error.
- If the API is unreachable, stop and report the connection failure; do
  not guess.
- If a batch payload contains an identifier not found in any API
  response, flag it according to the template's "not ready" or "blocked"
  conventions.

## Checklist

Before returning the result, verify:

- [ ] Every required top-level key from the answer template is present.
- [ ] All ID lists are sorted ascending.
- [ ] Per-item arrays follow the input payload order (unless the template
  specifies otherwise).
- [ ] Currency amounts use the correct precision (typically 2 decimals).
- [ ] Enum values are from the template's `allowed_values` only.
- [ ] No narrative text or extra fields outside the JSON.
- [ ] All API lookups used endpoints listed in `environment_access.md`.
- [ ] The API was treated as the system of record; local payloads were
  used as context only.
