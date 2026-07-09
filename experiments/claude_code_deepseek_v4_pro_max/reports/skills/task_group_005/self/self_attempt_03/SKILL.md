# ERP Finance Expense-Control — Reusable Skill

## Overview

This skill covers five related expense-control workflows in a shared ERP finance environment:
1. **Claims close review** — classify reimbursement claims as paid, payable, or blocked
2. **Vendor onboarding risk review** — make release-control decisions with compliance checks
3. **Prepaid expense close reconciliation** — reconcile prepaid schedules against GL balances
4. **Stale AP snapshot reconciliation** — correct stale AP exports against current ERP data
5. **Account-change payment release review** — assess risk for payment releases after vendor account changes

All workflows share the same API base, common sorting/output conventions, and a consistent source-precedence rule.

---

## Environment

- **Base URL**: provided by the runner (see `environment_access.md`); do not hardcode.
- **API style**: REST with exact-match query parameters (`?field=value`). Pagination via `limit` and `offset`.
- **All endpoints** return `{"count": N, "data": [...]}` with optional `endpoint`, `limit`, `offset`, `total` fields.

### Key Endpoints

| Endpoint | Primary Use |
|---|---|
| `/api/claims` | Claim status, amount, policy flags, receipt status |
| `/api/ap/bills` | AP bills linked to claims; bill status, amount, vendor |
| `/api/ap/payments` | Payment status (cleared, scheduled, processing) per bill |
| `/api/ap/aging` | Current AP balance (amount - paid_amount) per bill |
| `/api/vendors` | Vendor status, bank last-4, tax ID, payment terms |
| `/api/compliance/objects` | Business compliance: UBO, PEP, sanctions, risk score, bank status, license |
| `/api/prepaids/invoices` | Prepaid schedules: monthly amortization, service dates, data-quality flags |
| `/api/prepaids/gl-balances` | GL ending balances by account, period, entity |
| `/api/close/logs` | Close-period log entries for AP refresh, variance, legacy issues |

---

## Workflow 1: Claims Close Review (Reimbursement-to-AP)

### Goal

Classify a batch of claim IDs into **paid**, **payable**, and **blocked** buckets, compute the total open AP balance for payable claims, identify claims needing expense-case owner (CRM) intervention, and assign an overall batch status.

### API Workflow

For each claim ID in the batch:
1. `GET /api/claims?claim_id=<id>` → claim record (status, amount, policy_flags, receipt_status, notes)
2. `GET /api/ap/bills?claim_id=<id>` → linked AP bill(s) — bill status, amount, vendor, memo
3. `GET /api/ap/payments?bill_id=<bill_id>` → payment records for that bill
4. `GET /api/ap/aging?bill_id=<bill_id>` → current balance and paid_amount for the bill

### Classification Rules

#### paid_claim_ids
A claim is **paid / settled** when ALL of:
- Claim `status` is `"approved"` or `"paid"`
- At least one linked bill has `status` `"paid"` AND its `amount` **equals** the claim `amount`
- That bill has a **cleared** payment whose `amount` matches the bill/claim amount

Do NOT classify as paid when:
- The payment status is `"scheduled"` or `"processing"` (not yet cleared)
- The bill amount differs from the claim amount (amount mismatch → blocked)
- Only a different, higher-amount bill exists (e.g., a stale bill from a different AP inbox)

#### payable_claim_ids
A claim is **payable** (can remain in the AP reimbursement queue) when ALL of:
- Claim `status` is `"approved"`
- A linked AP bill exists and its `status` is NOT `"void"`
- No cleared payment has settled the bill
- No blocking expense-case issue (see blocked rules)

#### blocked_claim_ids
A claim is **blocked** (needs correction before AP release) when ANY of:
- Claim `status` is NOT `"approved"` (e.g., `"submitted"`, `"needs_receipt"`, `"rejected"`)
- No AP bill is linked to the claim (`GET /api/ap/bills` returns empty)
- The linked bill `status` is `"void"` — void bills must be ignored, they are not valid payables
- The bill `amount` does NOT equal the claim `amount` (amount mismatch on the correct bill)
- The bill memo contains risk flags like `"Duplicate check required"`
- Policy flags (`"over_limit"`, `"manual_rate"`) combined with partial receipt — signals incomplete support

#### crm_required_claim_ids (subset of blocked)
Claims where the root cause is on the **expense-case / owner side** (not AP):
- Receipt status is `"partial"` — missing full documentation
- Claim status is `"needs_receipt"` — formal receipt gap
- Policy flags present that require owner explanation (`"over_limit"`, `"late_receipt"`, `"weekend_spend"`)
- Notes indicating manager review pending (`"Manager comment pending"`)
- Claim is not yet approved

#### ap_open_balance_total
Sum of `balance` (from `/api/ap/aging`) for **payable claims only**. The aging endpoint returns `balance = amount - paid_amount`. Use this value directly. Exclude void bills and paid bills. Report in USD with 2 decimals.

#### batch_status
```
blocked        — any claim in the batch is blocked
open_payables  — no blocked claims, but at least one payable claim with unpaid balance remains
ready_to_close — all claims are paid/settled, no open payables
```

### Key Pitfalls
- **Claim amount ≠ bill amount**: Always compare. A bill linked to a claim may carry a different amount (stale link, duplicate). Classify as blocked/amount-mismatch.
- **Multiple bills per claim**: Some claims have two bills (e.g., an old stale bill and a corrected one). Use the bill whose amount matches the claim amount for paid classification; flag the stale one.
- **Void bills**: A void bill means the bill was canceled. Ignore it for AP balance; the claim is blocked.
- **Scheduled vs. cleared payments**: Only `"cleared"` payment status counts as settled. `"scheduled"` payments are in-flight, not final.
- **"Imported from legacy expense feed"** notes: May indicate data quality issues; treat the current API state as authoritative.

---

## Workflow 2: Vendor Onboarding Risk Review

### Goal

For a batch of business IDs, determine per-business release decisions, count reportable UBOs, identify hard-stop compliance flags, list follow-up IDs, and compute overall release readiness.

### API Workflow

For each business ID:
1. `GET /api/compliance/objects?business_id=<id>` → UBO list, PEP, sanctions, bank status, license, risk score, missing fields, shell company flag
2. `GET /api/vendors?vendor_id=<vendor_id>` (from compliance record) → vendor status, legal name, bank last-4, tax ID

### Decision Logic

| Decision | Criteria |
|---|---|
| `approve` | Vendor active, bank verified, license not expired, no sanctions/PEP/shell-company flags, all required docs present |
| `awaiting_information` | Moderate issues: missing fields, expired license, sanctions/pep screening not yet run, compliance review not yet started or in progress, possible PEP (not confirmed) |
| `escalate` | Serious issues: confirmed PEP, sanctions confirmed match, bank closed or name mismatch, vendor on hold, shell company suspected |

### Hard-Stop Flags

Derived from the compliance object (and vendor record for `vendor_on_hold`):

| Flag | Source Field | Condition |
|---|---|---|
| `bank_closed` | `bank_account_status` | `== "closed"` |
| `bank_name_mismatch` | `bank_account_status` | `== "name_mismatch"` |
| `confirmed_pep` | `pep_status` | `== "confirmed_pep"` |
| `expired_license` | `license_expiry` | `< as_of_date` (strictly before) |
| `missing_required_documents` | `missing_fields` | array is non-empty |
| `sanctions_confirmed` | `sanctions_check_status` | `== "confirmed_match"` |
| `screening_not_run` | `sanctions_check_status` or `pep_status` | `== "not_run"` |
| `shell_company_suspected` | `shell_company_suspected` | `== true` |
| `vendor_on_hold` | vendor `status` | `== "on_hold"` |

- Hard-stop flags per business: list alphabetically by enum value. Empty list `[]` if none.
- `screening_not_run` triggers when EITHER sanctions or PEP screening is `"not_run"`.

### UBO Count (reportable_ubo_counts)

- Threshold: **25%** ownership (>= 25%, i.e., at or above the reporting threshold).
- Count **unique beneficial-owner names** where any `ownership_pct` >= 25.
- If a name appears multiple times in `ubo_list`, combine their ownership — but the uniqueness test is on the name. A name with any single entry >= 25% qualifies.
- Report as integer.

### follow_up_business_ids

All business IDs whose `decision` is not `"approve"`. Sorted ascending.

### overall_release_ready

`true` **only** if every per-business decision is `"approve"`.

### Key Pitfalls
- **License expiry comparison**: Use strict less-than (`expiry < as_of_date`). If expiry equals the as_of date, the license is still valid on that day.
- **Possible PEP vs. confirmed PEP**: `"possible_pep"` does NOT trigger the `confirmed_pep` hard stop (but contributes to `awaiting_information`).
- **Vendor vs. compliance tax ID**: They may differ — the compliance record is authoritative for the business; the vendor record may have a different tax ID. Flag discrepancies.
- **UBO duplicates**: The same person appearing multiple times with different percentages counts as one unique name.

---

## Workflow 3: Prepaid Close Reconciliation

### Goal

Reconcile a scoped set of prepaid invoices against GL ending balances for specified accounts, computing account-level rollups, variances, and invoice-level exceptions.

### API Workflow

1. For each invoice ID in the scope: `GET /api/prepaids/invoices?prepaid_invoice_id=<id>`
2. For each account: `GET /api/prepaids/gl-balances?account=<account>&period=<YYYY-MM>`

### Straight-Line Amortization Formula

For each invoice, use the API-provided `monthly_amortization` value directly (it is already rounded):

```
march_amortization = monthly_amortization  (the month's charge)
cumulative_amortization_through_march = monthly_amortization × months_elapsed
schedule_ending_balance = original_amount - cumulative_amortization_through_march
```

**Months elapsed**: Count from `service_start` month through the close period month (inclusive). A service starting mid-month still counts the full starting month.

- Service start 2025-01-01, close March 2025 → 3 months (Jan, Feb, Mar)
- Service start 2025-03-15, close March 2025 → 1 month (March)
- Service start 2025-01-01, end 2025-03-31, close March 2025 → 3 months; ending balance may reach 0.00

### Account Rollup

For each account, sum across all scoped invoices assigned to that account:
- `original_amount_total`
- `march_amortization_total`
- `cumulative_amortization_through_march`
- `schedule_ending_balance` = sum of individual ending balances

Then:
- `gl_ending_balance` = from GL balances endpoint for that account/period
- `variance_amount` = `schedule_ending_balance - gl_ending_balance`
- `variance_flag` = `true` if `abs(variance_amount) > variance_threshold_abs` (from scope config, typically 100.00)
- `has_default_missing_term_flag` = `true` if **any** scoped invoice in that account has `data_quality_flags` containing `"missing_contract_dates"` or `"rounded_amount"`
- `account_status`:
  - `"reconciled"` — variance_flag is false AND has_default_missing_term_flag is false
  - `"variance_review"` — variance_flag is true (regardless of term flag)
  - `"requires_reconciliation"` — has_default_missing_term_flag is true (and variance_flag is false)

### Invoice-Level Flags

- **default_missing_term_flag** (`true`/`false`): Set `true` when `data_quality_flags` includes `"missing_contract_dates"` — indicates the service period dates may not be reliable.
- **exception_flag** (`true`/`false`): Set `true` when `data_quality_flags` is non-empty (any of: `"rounded_amount"`, `"missing_contract_dates"`, `"manual_override"`, `"duplicate_invoice_number"`).
- Invoices with NO `data_quality_flags` have both flags set to `false`.

### default_missing_term_invoice_ids

All invoice IDs where `default_missing_term_flag` is `true`. Sorted ascending.

### exception_invoice_ids

All invoice IDs where `exception_flag` is `true`. Sorted ascending.

### Ordering

- `invoice_results`: same order as the input scope (`prepaid_close_scope.json`)
- `selected_invoice_ids`: same order as the input scope

### Key Pitfalls
- **Rounding in monthly amortization**: The API's `monthly_amortization` is already rounded. Use it as-is; don't recalculate from `original_amount / months`. This means `monthly_amortization × months` may not exactly equal `original_amount` — a residual ending balance of a few cents is expected.
- **Mid-month service starts**: Count the starting month as month 1 for cumulative amortization.
- **GL balance lookup**: Must match exact period (`YYYY-MM`) and account. The same endpoint serves multiple entities; filter by both account and period.
- **Account names**: Account 1250 = "Prepaid Expenses", Account 1251 = "Prepaid Insurance".

---

## Workflow 4: Stale AP Snapshot Reconciliation

### Goal

Compare a stale AP snapshot (CSV) against current ERP API data, determine which claims are eligible for the batch, compute current AP balances, identify required stale-snapshot corrections, and check whether close-log entries are needed.

### API Workflow

For each candidate claim ID from the prompt (NOT from the stale snapshot):
1. `GET /api/claims?claim_id=<id>` → current claim state
2. `GET /api/ap/bills?claim_id=<id>` → current bill(s)
3. `GET /api/ap/payments?bill_id=<bill_id>` → current payment(s)
4. `GET /api/ap/aging?bill_id=<bill_id>` → current balance
5. `GET /api/close/logs` → check for open/blocked/ready_for_review log entries

### Source Precedence

**Current API data is the system of record.** The stale snapshot CSV is advisory context only. Always base decisions on live API responses.

### Classification

#### eligible_claim_ids
Claims that can remain in the batch after current API reconciliation:
- Claim `status` is `"approved"` (or `"paid"`)
- Has a valid (non-void) linked AP bill
- Bill has a cleared payment matching the amount, OR bill is payable with no blocking issues

#### not_ready_claim_ids
Claims that should NOT remain:
- Claim not approved (`"submitted"`, `"needs_receipt"`, `"rejected"`)
- Bill is void
- Bill amount ≠ claim amount (mismatch)
- No AP bill linked

### AP Balance (ap_balance_by_claim)

For each claim, the **open AP balance** from `/api/ap/aging?bill_id=<bill_id>`:
- Use the `balance` field (= amount - paid_amount)
- For claims with multiple bills, use the bill that matches the claim amount (the "correct" bill)
- Ignore void bills (balance = 0.00, not applicable)
- For paid claims with cleared payments, balance will be 0.00

### Stale Snapshot Corrections (stale_snapshot_corrections)

Compare the stale CSV row against current API data. One correction per claim:

| Correction | When to Apply |
|---|---|
| `current_snapshot_ok` | Snapshot data matches current API state |
| `mark_in_flight_payment` | Payment exists but status is `"processing"` or `"scheduled"` (not yet cleared) |
| `replace_with_matched_paid_bill` | Snapshot has wrong bill_id/amount; current API shows a different paid bill |
| `exclude_amount_or_vendor_mismatch` | Bill amount ≠ claim amount, or vendor mismatch between snapshot and API |
| `ignore_void_bill` | Bill status in API is `"void"` — the snapshot bill row is stale |
| `block_unapproved_claim` | Claim status is not `"approved"` in current API |

### Close Log Check (close_log_required)

- `required`: `true` if any close-log entry has `status` `"open"`, `"ready_for_review"`, or `"blocked"` AND relates to the expense/AP area for the relevant period
- `ids`: the `log_id` values of those log entries, sorted ascending

### Batch Status
```
ready_to_send   — all claims eligible, no blocking issues
needs_ap_refresh — AP data stale, some claims need recheck after refresh
blocked          — at least one claim is not ready (not_ready non-empty)
```

### Key Pitfalls
- **Snapshot is NOT authoritative**: Never use snapshot amounts/statuses for final decisions. The CSV may reflect old bill IDs, stale amounts, or voided bills.
- **Multiple bills per claim**: A claim may have both a stale bill (from the snapshot) and a current bill. Use the current one.
- **Payment status granularity**: `"scheduled"` ≠ `"cleared"`. Only `"cleared"` means settled.
- **Snapshot `snapshot_bill_amount` may differ from current API bill amount**: Always use current.

---

## Workflow 5: Account-Change Payment Release Review

### Goal

After vendor account-change events, assess whether each business can receive payment release. Check vendor status, compliance data, bank account, tax ID, license, and risk score.

### API Workflow

For each business ID in the batch:
1. `GET /api/vendors?vendor_id=<vendor_id>` (from the account-change event) → vendor status, bank last-4, tax ID
2. `GET /api/compliance/objects?business_id=<business_id>` → full compliance record

### Decision Matrix

Cross-reference vendor + compliance data:

| Decision | Criteria |
|---|---|
| `release` | Vendor active, bank verified (and last-4 matches ticket), license valid, tax ID valid format and matches across vendor/compliance, sanctions clear, risk < 70, review approved |
| `hold` | Minor issues: license expired but otherwise clean, screening not run, review in progress, moderate risk, missing minor fields |
| `escalate` | Serious: bank closed or name_mismatch, vendor on_hold, sanctions confirmed, PEP confirmed, risk >= 70, tax ID invalid format or mismatch, shell company suspected |

### Flag Lists (all sorted ascending by business_id)

#### bank_mismatch_ids
Compliance `bank_account_status` is `"name_mismatch"`.

#### invalid_tax_ids
Tax ID does not match pattern `TIN` followed by **digits only** (e.g., `TIN12X899` is invalid because of the `X`). Check both vendor and compliance tax IDs; either being invalid qualifies. Also flag if compliance tax_id differs from vendor tax_id (mismatch across systems).

#### expired_license_ids
Compliance `license_expiry` < `as_of_date` (review date, typically provided in the batch payload).

#### review_queue_ids
Business IDs where compliance `review_status` is NOT `"approved"` — i.e., `"in_review"`, `"awaiting_information"`, `"not_started"`, or `"escalated"`.

#### risk_score_override_flags
Business IDs where compliance `risk_score` >= 70.

### Key Pitfalls
- **Vendor bank last-4 vs. ticket requested bank**: The vendor record's `bank_account_last4` should match the `requested_bank_last4` in the account-change ticket. Mismatch = escalation.
- **Tax ID cross-check**: Vendor record and compliance record may have different tax IDs — flag discrepancies.
- **License expiry on the review date**: `expiry < as_of_date` is expired. If expiry equals the review date, it is still valid.
- **Vendor status `on_hold`**: This is a hard escalation trigger regardless of other clean signals.
- **Sanctions `possible_match` vs. `confirmed_match`**: Only `confirmed_match` is a hard stop; `possible_match` contributes to `hold`.
- **PEP `possible_pep` vs. `confirmed_pep`**: Only `confirmed_pep` is a hard stop.

---

## Cross-Cutting Conventions

### Sorting Rules
| Context | Order |
|---|---|
| Claim ID lists | Ascending string sort by claim_id |
| Business ID lists | Ascending string sort by business_id |
| Hard-stop flag lists (per business) | Alphabetical by enum value |
| Invoice result lists | Same order as input scope file |
| Close log ID lists | Ascending string sort by log_id |

### Numeric Conventions
- Currency amounts: USD, 2 decimal places (cents precision)
- Use values from API directly; do not recompute unless specified
- Rounding: if API provides a pre-rounded `monthly_amortization`, use it as-is
- Empty/zero values: `0.00` for amounts, `0` for integers, `[]` for empty lists, `false` for booleans

### API Query Pattern
- All endpoints support `?field=value` exact-match filtering
- All return `{"count": N, "data": [...]}`
- The `data` array may contain zero, one, or multiple records
- Always handle the case where `data` is empty (no bill, no payment, etc.)

### Source Precedence (universal rule)
1. **Current API response** — always the system of record
2. **Task batch payload** — provides scope (which IDs to review) and parameters (dates, thresholds)
3. **Stale snapshots / CSVs** — advisory context only; never authoritative for final decisions

### Common Data-Quality Signals
| Signal | Meaning |
|---|---|
| `"Duplicate check required"` in bill memo | Possible duplicate — risk flag |
| `"Imported from legacy expense feed"` in claim notes | Data migration artifact — verify current state |
| `"Imported from AP inbox"` in bill memo | Bill may be from a bulk import — verify linkage |
| `"Accrual review"` in bill memo | Bill is under accrual review, may not be finalized |
| `"Manager comment pending"` in claim notes | Claim awaiting manager input — not ready |
| Policy flag `"over_limit"` | Amount exceeds policy limit — needs review |
| Policy flag `"manual_rate"` | Rate manually entered — needs verification |
| Policy flag `"late_receipt"` | Receipt submitted late — compliance gap |
| Receipt status `"partial"` | Incomplete documentation — not fully supported |

### Payment/Bill Status Lifecycle
```
Bill:  approved → scheduled → paid  (or void)
Payment: scheduled → processing → cleared
```
- Only `"paid"` bill + `"cleared"` payment = settled
- `"void"` bills = canceled, exclude from all calculations
- `"scheduled"` or `"processing"` payments = in-flight, not final

### Close-Log Statuses
| Status | Meaning |
|---|---|
| `closed` | Review complete, no action needed |
| `open` | Issue identified, not yet addressed |
| `ready_for_review` | Work done, awaiting reviewer sign-off |
| `blocked` | Cannot proceed, dependency or data issue |

### Account Reference
| Account | Name |
|---|---|
| 1250 | Prepaid Expenses |
| 1251 | Prepaid Insurance |
| 2100 | Accounts Payable |
| 6200 | Employee Reimbursements |
| 6100 | (General expense) |
| 6250 | (General expense) |
| 6500 | (General expense) |

---

## End-to-End Workflow Checklist

1. **Read** the batch payload (scope IDs, parameters, dates, thresholds)
2. **Query** the API for each ID — always use current endpoints, never rely on local files
3. **Cross-reference** claims ↔ bills ↔ payments (or vendors ↔ compliance)
4. **Classify** each item according to the rules above
5. **Compute** rollups, balances, variances using API-provided values
6. **Sort** all ID lists according to the conventions
7. **Assign** overall status based on the worst item in the batch
8. **Return** JSON matching the answer template — extra keys not allowed unless template permits
