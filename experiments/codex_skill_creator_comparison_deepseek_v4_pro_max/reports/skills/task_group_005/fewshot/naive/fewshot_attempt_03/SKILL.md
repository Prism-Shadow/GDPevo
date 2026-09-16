---
name: finance-operations-review
description: Reconcile finance and compliance review batches against a shared ERP/compliance API. Covers claim-to-AP matching, vendor onboarding risk review, prepaid close reconciliations, stale AP snapshot corrections, and account-change payment-release decisions. Use when a task provides a batch of IDs to review against the task_env API and expects a structured JSON decision output.
---

# Finance Operations Batch Review

## API Access

The task environment exposes a shared ERP/compliance API at the base URL the runner provides as `<TASK_ENV_BASE_URL>`. All endpoints return JSON arrays wrapped in `{"count": N, "data": [...]}`. Use exact-match query parameters by field name; paginate with `limit` and `offset`.

### Available Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/claims` | Employee expense claims |
| `GET /api/ap/bills` | AP bills (may link to claims via `claim_id`) |
| `GET /api/ap/payments` | Payment records linked to bills via `bill_id` |
| `GET /api/ap/aging` | AP aging with `balance`, `paid_amount` per bill |
| `GET /api/vendors` | Vendor master with bank, tax, status |
| `GET /api/compliance/objects` | Consolidated compliance records per business_id |
| `GET /api/compliance/ownership/{business_id}` | UBO list with ownership_pct and shell_company flag |
| `GET /api/compliance/registry/{business_id}` | Jurisdiction, license_expiry, tax_id, registration |
| `GET /api/compliance/screening/{business_id}` | PEP status, sanctions check |
| `GET /api/compliance/bank/{business_id}` | Bank account verification status |
| `GET /api/prepaids/invoices` | Prepaid invoice schedules with monthly_amortization |
| `GET /api/prepaids/gl-balances` or `GET /api/gl/balances` | GL ending balances per account/period/entity |
| `GET /api/close/logs` | Period-close log entries with area, status, message |

Both `/api/prepaids/gl-balances` and `/api/gl/balances` return the same data; use whichever is available. Similarly, `/claims` is an alias for `/api/claims`, `/bills` for `/api/ap/bills`, etc.

---

## Cross-Reference Patterns

### Claims to AP Bills to Payments

Link claims to AP using `claim_id` on bills. Link bills to payments using `bill_id` on payments.

**Claim status values**: `approved`, `paid`, `rejected`, `submitted`, `needs_receipt`, `in_review`, `denied`.

**Bill status values**: `approved`, `scheduled`, `paid`, `void`, `pending`, `rejected`.

**Payment status values**: `cleared`, `processing`, `scheduled`, `failed`.

**Key rules**:

- A claim is **paid** (settled) only when: a bill with matching `claim_id` exists, the bill status is `paid`, and at least one `cleared` payment exists for that bill covering the full bill amount. Do not rely on `claim.status === "paid"` alone; verify the bill and payment chain.
- A claim is **blocked** (not ready for AP release) when: the claim status is not `approved` (e.g., `rejected`, `denied`, `needs_receipt`, `submitted`), or the linked bill has a blocking status (`void`, `rejected`), or no bill exists at all, or there is a vendor mismatch between the claim's vendor_id (if present) and the bill's vendor_id, or there is a material amount mismatch between claim and bill.
- A claim is **payable** when: the claim is `approved`, a valid linked bill exists and is not `paid` or `void`, and no blocking conditions apply.
- **AP open balance** for a payable claim = bill.amount minus the sum of all cleared payments for that bill. Use the `balance` field from `/api/ap/aging` when available; otherwise compute from bills and payments.
- A **scheduled** payment is not a cleared payment. Only `cleared` payments close out a bill balance.

### Business IDs to Compliance Records

Cross-reference each business ID across four compliance dimensions:

1. **Ownership** (`/api/compliance/ownership/{business_id}`): Count unique beneficial owner **names** (not entries) with `ownership_pct >= 25` as reportable UBOs. A person appearing twice with different percentages counts as one UBO. `shell_company_suspected: true` is a hard stop.
2. **Screening** (`/api/compliance/screening/{business_id}`): `pep_status: "confirmed_pep"` is a hard stop. `sanctions_check_status: "confirmed_match"` is a hard stop.
3. **Registry** (`/api/compliance/registry/{business_id}`): `license_expiry` before the as-of/review date is a hard stop. Missing or invalid `tax_id` is a concern.
4. **Bank** (`/api/compliance/bank/{business_id}`): `bank_account_status: "closed"` is a hard stop. `bank_account_status: "name_mismatch"` means the bank account name does not match the business name.

The consolidated endpoint `/api/compliance/objects` provides `review_status`, `missing_fields`, `risk_score`, `pep_status`, `sanctions_check_status`, `bank_account_status`, `license_expiry`, `ubo_list`, `shell_company_suspected`, and `vendor_id`. Use it as the primary source, then drill into sub-endpoints for deeper detail when needed.

**Decision logic** for per-business decisions:

- **escalate** — any hard-stop flag applies: `confirmed_pep`, `sanctions_confirmed`, `expired_license`, `bank_closed`, `shell_company_suspected`, `vendor_on_hold`, or `screening_not_run` combined with other red flags.
- **awaiting_information** — non-blocking issues exist: `missing_required_documents`, isolated `screening_not_run` (no other red flags), `bank_name_mismatch` (needs verification), or incomplete review status.
- **approve** — zero hard-stop flags and zero follow-up concerns. The business is clean.

**Hard-stop flags** (derive from compliance data, list alphabetically):

| Flag | Condition |
|---|---|
| `bank_closed` | bank_account_status is `closed` |
| `bank_name_mismatch` | bank_account_status is `name_mismatch` |
| `confirmed_pep` | pep_status is `confirmed_pep` |
| `expired_license` | license_expiry date is before the review/as_of date |
| `missing_required_documents` | missing_fields is non-empty |
| `sanctions_confirmed` | sanctions_check_status is `confirmed_match` |
| `screening_not_run` | pep_status or sanctions_check_status is missing, null, or `not_run` |
| `shell_company_suspected` | shell_company_suspected is true |
| `vendor_on_hold` | vendor/business status is inactive or suspended |

**`follow_up_business_ids`** includes every business_id whose decision is not `approve`.

**`overall_release_ready`** is `true` only when every listed business decision is `approve`.

### Business IDs to Vendor Records (Account-Change Payment Release)

When reviewing payment release after account-change events, cross-reference the batch business IDs against vendor and compliance data:

- Check `requested_bank_last4` from the change ticket against `bank_account_last4` from `/api/vendors` (filter by `vendor_id`). Mismatch is a blocking concern.
- Check `tax_id` consistency between `/api/compliance/registry/{business_id}` and `/api/vendors`. Mismatch = `invalid_tax_ids`.
- Check `license_expiry` against the review date. Expired = `expired_license_ids`.
- Check `risk_score >= 70` from compliance = `risk_score_override_flags`.
- Decision: `release` when zero issues; `hold` when non-critical issues (bank mismatch, expired license, missing docs, no sanctions/PEP risk); `escalate` when critical flags (confirmed PEP, sanctions match, shell company, multiple red flags, or vendor_on_hold).
- `review_queue_ids` contains every business_id that is not `release`.

### Prepaid Invoices to GL Balances

All prepaid invoices use **straight-line monthly amortization**.

**Per-invoice computations**:

- `monthly_amortization` — the value from the invoice record.
- `cumulative_amortization_through_period` — count full calendar months from `service_start` month through the close period month, inclusive (e.g., Jan 1 through March = 3 months), capped at `service_end`. Multiply by `monthly_amortization`.
- `ending_balance` = `original_amount` - `cumulative_amortization_through_period`. Floor at 0.00.
- `default_missing_term_flag` — true when `data_quality_flags` includes `missing_contract_dates` or `rounded_amount`, or when `monthly_amortization` is 0/null and a default was assumed.
- `exception_flag` — true when (a) `ending_balance` is 0.00 (fully amortized, possibly stale), or (b) `data_quality_flags` is non-empty, or (c) there is an amortization anomaly (e.g., original_amount does not align with expected term).

**Account-level rollup** (`account_rollup`):

- `account_name` — from GL balance record.
- `selected_invoice_count` — count of scoped invoices for that account.
- `original_amount_total` — sum of all scoped invoice `original_amount` values.
- `march_amortization_total` (or period equivalent) — sum of all scoped invoice `monthly_amortization` values.
- `cumulative_amortization_through_period` — sum of per-invoice cumulative values.
- `schedule_ending_balance` — sum of per-invoice `ending_balance` values.
- `gl_ending_balance` — from `/api/prepaids/gl-balances` filtered by period, account, entity.
- `variance_amount` = `schedule_ending_balance` - `gl_ending_balance`.
- `variance_flag` — true when `|variance_amount| > variance_threshold_abs`.
- `has_default_missing_term_flag` — true when any scoped invoice has that flag.
- `account_status` — `reconciled` when variance_flag is false and has_default_missing_term_flag is false; `variance_review` when variance_flag is true but the variance is modest; `requires_reconciliation` when variance_flag is true and has_default_missing_term_flag is also true, or when variance is very large.

**GL balance lookup**: filter `/api/prepaids/gl-balances` by `period`, `account`, and `entity`. Use the `ending_balance` field for the close period.

---

## Stale Snapshot Reconciliation

When a task provides a local CSV/JSON snapshot of AP data and directs you to reconcile against the live API:

1. Fetch current claim, bill, and payment records for each candidate `claim_id` from the live API.
2. For each claim, compare the snapshot row against current state and assign a correction code:
   - `current_snapshot_ok` — snapshot matches current live state.
   - `mark_in_flight_payment` — a payment exists but has not cleared yet; the snapshot shows `none`/`0.00` for payment.
   - `replace_with_matched_paid_bill` — snapshot `bill_id` is stale/wrong; the live system has a different bill that is paid.
   - `exclude_amount_or_vendor_mismatch` — claim amount or vendor does not match the linked bill.
   - `ignore_void_bill` — snapshot `bill_id` now has status `void` in the live system.
   - `block_unapproved_claim` — current claim status in the live API is not `approved` (e.g., `rejected`, `denied`, `submitted`).
3. Compute `ap_balance_by_claim`: for each claim, the open AP balance from current bill/payment data (bill amount minus cleared payments). Paid/settled claims = `0.00`.
4. `eligible_claim_ids` — claims where live data supports keeping them in the batch (approved claims with valid unpaid or in-flight bills).
5. `not_ready_claim_ids` — blocked or already settled claims.
6. `close_log_required` — check `/api/close/logs` for relevant period entries with `status: "open"` or `status: "ready_for_review"` related to AP or Expense area. Include those log IDs.
7. `batch_status` — `ready_to_send` when all claims are eligible and no close log blocks; `needs_ap_refresh` when corrections are needed or close logs remain open; `blocked` when any claim is blocked.

---

## General Output Conventions

- **Sorting**: All ID lists sorted ascending by ID (lexicographic for claim IDs, business IDs, invoice IDs, close log IDs).
- **Currency**: All amounts in USD, reported to 2 decimal places as numbers (not strings). Use `0.00` not `0` when the template expects decimal precision.
- **JSON only**: Return only the JSON object conforming to the answer template. No explanatory text or markdown outside the JSON.
- **Template fidelity**: Match every required key exactly. Preserve the key ordering shown in the template. Use only the allowed enum values.
- **Zero vs. empty**: Empty lists use `[]`. Zero amounts use `0` or `0.00` as appropriate. Never use `null` for a required field.
- **Counts match**: The sum of IDs across categories (payable + blocked + paid, or eligible + not_ready) must equal the total reviewed claim count.

---

## General Workflow

1. Read the prompt to identify the task type and target batch of IDs.
2. Locate the answer template in `input/payloads/` and understand every required field, enum, and ordering constraint.
3. Fetch data from the live API for all relevant IDs. Make parallel requests when endpoints are independent (claims, bills, payments, vendors, compliance, prepaids, GL, close logs).
4. Cross-reference data following the patterns in this document.
5. Apply the business rules to classify each ID and detect exceptions.
6. Compute summary totals (balances, counts, flags) at both item and aggregate levels.
7. Assemble the JSON output conforming exactly to the template structure.
8. Validate sorting, precision, enum values, and that every required key is present before finalizing.

---

## Common Pitfalls

- **Do not trust `claim.status === "paid"`** without verifying a bill and cleared payment exist. The claim status may be stale.
- **A scheduled payment is not a cleared payment.** Only `cleared` payments reduce an AP balance.
- **UBO counts**: Count unique owner names, not list entries. A single person with two ownership percentage entries counts as one UBO. Only include those with `ownership_pct >= 25`.
- **Period boundaries**: When computing cumulative amortization, count full calendar months inclusive. A March 1 start with a March close period = 1 month of amortization. A January 1 start with a March close period = 3 months.
- **Close log relevance**: Filter by period and area (AP, Expense, Prepaids, Compliance). An open or ready_for_review log in a related area means the close cycle is not complete and blocks finalization.
- **License expiry comparison**: Compare the expiry date string against the review/as_of date string. If expiry is strictly before (less than) the review date, the license is expired.
- **Amount matching precision**: When comparing claim.amount to bill.amount, tolerate small rounding differences (under $1) but flag material mismatches.
- **Vendor_id on claims**: A claim may have `vendor_id: null`. That is not a mismatch; only compare when both claim and bill have non-null vendor_ids and they differ.
