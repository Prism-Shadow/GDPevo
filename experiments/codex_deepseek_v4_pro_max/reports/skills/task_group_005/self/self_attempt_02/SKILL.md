---
name: erp-finance-batch-ops
description: >
  Shared-API ERP finance batch operations covering AP reimbursement, vendor
  onboarding compliance, prepaid close reconciliation, stale-AP export cleanup,
  and account-change payment risk review. Use when processing finance batch
  tasks that require cross-referencing claims, AP bills, payments, vendors,
  compliance records, prepaid invoices, GL balances, or close logs against a
  shared JSON API. Triggers on finance operations tasks involving batch-close
  decisions, release control, reconciliation, or risk review in a task-group-005
  ERP environment where the API base URL is supplied as `<TASK_ENV_BASE_URL>`.
---

# ERP Finance Batch Operations

## Core operating model

Every task follows the same pattern:

1. **Read the prompt** — identifies the domain, the candidate batch, and the
   required output template.
2. **Read the answer template** (`input/payloads/answer_template.json`) — defines
   the exact output shape, required keys, allowed values, ordering rules, and
   numeric precision. Never deviate from the template.
3. **Read the batch payload** (if present) — provides the candidate IDs and
   task-specific context. Treat local payloads as *context, not system of
   record*.
4. **Query the shared API** — use `<TASK_ENV_BASE_URL>` as the base URL. All
   decisions must be based on current API state.
5. **Cross-reference endpoints** — reconcile data across related endpoints to
   make decisions (e.g., claims ↔ bills ↔ payments).
6. **Produce JSON output** — match the answer template exactly.

## API endpoints

The environment exposes a JSON API with these GET endpoints. No POST endpoints
are available for non-judge use.

### Claims & AP

| Endpoint | Alternate | Purpose |
|----------|-----------|---------|
| `/claims` | `/api/claims` | List all expense claims |
| `/api/claims/{claim_id}` | — | Single claim detail |
| `/bills` | `/api/ap/bills` | List AP bills |
| `/payments` | `/api/ap/payments` | List payment records |
| `/api/ap/aging` | — | AP aging data |

### Vendors & Compliance

| Endpoint | Alternate | Purpose |
|----------|-----------|---------|
| `/vendors` | `/api/vendors` | Vendor master data |
| `/compliance/objects` | `/api/compliance/objects` | Full compliance records |
| `/api/compliance/ownership/{business_id}` | — | Beneficial ownership |
| `/api/compliance/registry/{business_id}` | — | Business registry details |
| `/api/compliance/screening/{business_id}` | — | Watchlist/sanctions screening |
| `/api/compliance/bank/{business_id}` | — | Bank account validation |

### Prepaids & GL

| Endpoint | Alternate | Purpose |
|----------|-----------|---------|
| `/prepaids/invoices` | `/api/prepaids/invoices` | Prepaid amortization schedules |
| `/gl/balances` | `/api/prepaids/gl-balances` | GL ending balances |

### Close

| Endpoint | Alternate | Purpose |
|----------|-----------|---------|
| `/close/logs` | `/api/close/logs` | Period-close event logs |

### Query mechanics

- Collection endpoints accept exact-match query parameters by field name when
  the field exists on the resource.
- Optional `limit` and `offset` query parameters (integers) control pagination.
- Detail endpoints use path placeholders: replace `{claim_id}` or
  `{business_id}` with the identifier string.

## Batch-processing patterns

### Claims reconciliation (AP close)

For each claim in the batch, cross-reference:

- **Claim record**: status, amount, expense type, supporting evidence.
- **AP bill record**: bill status (approved, scheduled, paid, void), amount,
  vendor match.
- **Payment record**: payment status (cleared, scheduled, none), payment
  amount, match to bill.

**Decision rules:**

- **Paid / settled**: claim has a matched paid AP bill AND a cleared payment
  covering the claim amount → `paid_claim_ids` or excluded from payable batch.
- **Payable / eligible**: claim is approved, has a valid open AP bill, no
  blocking issues → `payable_claim_ids` / `eligible_claim_ids`.
- **Blocked / not ready**: claim is unapproved, bill is void, amount mismatch,
  missing support, vendor mismatch, or payment evidence inconsistent →
  `blocked_claim_ids` / `not_ready_claim_ids`.

When distinguishing reimbursement case issues from AP/payment evidence issues:
case-level problems (status, support, approval) → `crm_required_claim_ids`;
AP-level problems (bill/payment mismatch, void bill) stay in blocked but not
crm_required.

### Vendor onboarding compliance

For each business, fetch and cross-reference:

- **Vendor record**: status flags, onboarding state.
- **Compliance objects**: aggregated compliance status.
- **Ownership**: UBO list with ownership percentages; count distinct UBO names
  at or above the reporting threshold.
- **Registry**: business registration validity, license expiry.
- **Screening**: sanctions, PEP, adverse-media hits.
- **Bank**: account status (`active`, `closed`, `name_mismatch`).

**Decision rules:**

- **`approve`**: all compliance checks pass, bank is active, no hard stops.
- **`awaiting_information`**: missing documents, screening not run, or gaps
  that can be remediated without escalation.
- **`escalate`**: confirmed sanctions, confirmed PEP, shell-company indicators,
  bank closed, or multiple unresolved hard stops.

**Hard-stop flags** are never optional — if a compliance endpoint returns a
flag that matches a hard-stop value, it must appear in the output, even if
overall decision is not escalate.

### Prepaid close reconciliation

For each prepaid invoice in scope:

1. Fetch invoice schedule from `/prepaids/invoices`.
2. Compute schedule values: monthly amortization, cumulative amortization,
   ending balance = original amount − cumulative amortization through close
   period.
3. Fetch GL ending balance for the period from `/gl/balances`.
4. Compute variance = schedule ending balance − GL ending balance.

**Flags and status:**

- **`variance_flag`**: `true` when `|variance| > variance_threshold_abs`.
- **`default_missing_term_flag`**: `true` when the invoice record has a
  default or missing amortization term.
- **`exception_flag`**: `true` when the invoice has data-quality issues
  (zero amounts, missing schedules, negative balances, or term anomalies).
- **`account_status`**:
  - `reconciled` — variance within threshold, no exceptions.
  - `variance_review` — variance exceeds threshold but no data exceptions.
  - `requires_reconciliation` — exceptions present regardless of variance.

Use straight-line monthly amortization as represented in the invoice records.

### Stale-AP export reconciliation

When a local export/snapshot accompanies a batch:

- **Treat the snapshot as context only.** All decisions come from the current
  API state.
- Compare snapshot fields against live API data and classify each claim:

| Correction | When to use |
|---|---|
| `current_snapshot_ok` | Snapshot matches current API state. |
| `mark_in_flight_payment` | Payment exists in API that was not in snapshot. |
| `replace_with_matched_paid_bill` | Bill found in API with different ID but matching amount and payment. |
| `exclude_amount_or_vendor_mismatch` | Bill amount or vendor doesn't match claim. |
| `ignore_void_bill` | Bill exists but is void in current API. |
| `block_unapproved_claim` | Claim is not in approved state in current API. |

### Account-change payment risk review

For each account-change ticket's business:

1. Fetch vendor data for the business.
2. Fetch all compliance endpoints: ownership, registry, screening, bank.
3. Validate the requested bank last-4 against compliance bank record.
4. Check tax ID validity, license expiry, screening results, risk score.

**Decision rules:**

- **`release`**: bank matches, no compliance flags, license valid, tax ID
  valid, risk score < 70, screening clear.
- **`hold`**: minor compliance gaps (missing docs, screening stale) that can
  be remediated; bank last-4 mismatch if the compliance bank status is not
  `name_mismatch`.
- **`escalate`**: bank `name_mismatch`, sanctions hit, expired license,
  invalid tax ID, risk score ≥ 70, or multiple flags.

**Output list rules:**

- `bank_mismatch_ids` — businesses where compliance bank status is
  `name_mismatch`.
- `risk_score_override_flags` — businesses with `risk_score >= 70`.
- `review_queue_ids` — businesses needing compliance/AP review before release.
- `expired_license_ids` — businesses with license expiry before `as_of_date`.

## Data conventions

- **Sorting**: All ID lists (claim IDs, business IDs, close log IDs) must be
  sorted in **ascending** order unless the answer template explicitly states
  otherwise (e.g., "same order as prepaid_close_scope.json").
- **Currency**: All amounts are **USD with 2 decimal places** (cents
  precision). Use numbers, not strings.
- **Empty lists**: Use `[]`, never `null` or omitted keys.
- **Zero values**: Use `0` or `0.00`, never `null` for numeric fields.
- **Boolean flags**: Must be JSON `true`/`false`, not strings.

## Batch status taxonomy

Common batch-status values across workflows:

| Status | Meaning |
|---|---|
| `ready_to_close` / `ready_to_send` | All items resolved, batch can proceed. |
| `open_payables` / `needs_ap_refresh` | Valid unpaid bills remain; batch is active but not complete. |
| `blocked` | One or more items have unresolved issues; batch cannot proceed. |

Select based on the **most severe** condition across all batch items.

## Close-log handling

When a task references close logs (`/close/logs`):

- Close logs document period-close events and may flag reconciliation issues.
- If any batch claim appears in a close log with an unresolved flag, the claim
  must be blocked or escalated.
- `close_log_required.required` is `true` when any batch item has had a close
  event that needs acknowledgment; `close_log_required.ids` lists the relevant
  close log IDs in ascending order.
