# ERP Finance Expense-Control — Reusable SKILL.md

## Environment & API

- **Base URL**: `http://34.46.77.124:8005` (use `/api/*` variants).
- **Filtering**: Exact-match query parameters by field name (e.g. `?claim_id=CLM-2025-0001`, `?business_id=BUS-2025-0009`, `?account=1250&period=2025-03`).
- **Pagination**: `limit` and `offset` query params.
- **Key endpoints**:
  - `/api/claims` — expense claims (status, amount, vendor_id, policy_flags, receipt_status)
  - `/api/ap/bills` — AP bills (status, amount, claim_id, vendor_id, bill_id, account)
  - `/api/ap/payments` — payments (status, amount, bill_id, payment_id, method)
  - `/api/vendors` — vendor master data (status, bank_account_last4, tax_id, legal_name)
  - `/api/compliance/objects` — compliance records (bank_account_status, pep_status, license_expiry, risk_score, sanctions_check_status, shell_company_suspected, missing_fields, ubo_list, tax_id)
  - `/api/prepaids/invoices` — prepaid schedules (monthly_amortization, original_amount, service_start/end, data_quality_flags, account)
  - `/api/prepaids/gl-balances` — GL ending balances by account+period+entity
  - `/api/close/logs` — close/review log entries (area, status, period, log_id)

---

## Workflow 1: Expense Claim Reimbursement-to-AP Close Review

### Input
A list of claim IDs to review.

### Data Sources (query each claim)
1. `GET /api/claims?claim_id=<id>` — claim status, amount, vendor_id, policy_flags
2. `GET /api/ap/bills?claim_id=<id>` — all bills linked to the claim
3. For each bill: `GET /api/ap/payments?bill_id=<id>` — payment records

### Classification Rules

#### paid_claim_ids — Settled Claims
A claim is **paid** when:
- The claim status is `"paid"` in `/api/claims`, **AND**
- At least one linked AP bill has status `"paid"` with amount matching the claim amount, **AND**
- That matching bill has a corresponding payment with status `"cleared"` and amount matching the bill.

#### payable_claim_ids — Open Payables (Keep in Batch)
A claim is **payable** (releasable to AP) when:
- Claim status is `"approved"` (not paid, not rejected, not needs_receipt, not submitted), **AND**
- At least one linked AP bill exists with status NOT `"void"`, **AND**
- The bill amount matches the claim amount, **AND**
- The bill's vendor_id matches the claim's vendor_id (if claim has a vendor_id), **AND**
- No fully-cleared payment exists that would settle the bill.

#### blocked_claim_ids — Cannot Release to AP
A claim is **blocked** in ANY of these cases:
- Claim status is NOT `"approved"` and NOT `"paid"` (e.g., `"needs_receipt"`, `"submitted"`, `"rejected"`)
- No AP bill exists for the claim
- The only linked AP bill has status `"void"`
- Amount mismatch: claim.amount ≠ bill.amount (for all non-void bills)
- Vendor mismatch: claim.vendor_id is set but doesn't match bill.vendor_id

#### crm_required_claim_ids
All blocked_claim_ids that need expense-case owner cleanup or AP-link remediation. In practice: all blocked claims.

### Computed Fields

- **ap_open_balance_total**: Sum of `bill.amount` for all non-void, non-fully-paid AP bills belonging to **payable_claim_ids** only. Round to 2 decimal places.
- **batch_status** (enum):
  - `"blocked"` — any claim in the batch is blocked
  - `"open_payables"` — no blocked claims, but at least one payable claim with open balance > 0
  - `"ready_to_close"` — no blocked claims and no open payables (all paid)
- **reviewed_claim_count**: Total number of claim IDs in the input batch.

### Sorting
All claim-ID lists output in **ascending lexicographic order** by claim_id.

---

## Workflow 2: Vendor Onboarding Finance-Risk Release

### Input
- List of business IDs for vendor onboarding
- `as_of_date` (the review date)

### Data Sources
- `GET /api/compliance/objects?business_id=<id>` — per business
- `GET /api/vendors?vendor_id=<id>` — vendor status for on-hold detection

### Hard-Stop Flag Derivation
Map compliance fields to flags (alphabetical order in output lists):

| Flag | Trigger Condition |
|---|---|
| `bank_closed` | `bank_account_status == "closed"` |
| `bank_name_mismatch` | `bank_account_status == "name_mismatch"` |
| `confirmed_pep` | `pep_status == "confirmed_pep"` |
| `expired_license` | `license_expiry < as_of_date` |
| `missing_required_documents` | `missing_fields` array is non-empty |
| `sanctions_confirmed` | `sanctions_check_status == "confirmed_match"` |
| `screening_not_run` | `sanctions_check_status == "not_run"` OR `pep_status == "not_run"` |
| `shell_company_suspected` | `shell_company_suspected == true` |
| `vendor_on_hold` | vendor's `status` is `"on_hold"` or `"inactive"` |

### Decision Taxonomy

- **`"approve"`**: Zero hard-stop flags. All checks pass.
- **`"escalate"`**: Any of these escalation triggers present:
  - `confirmed_pep`, `bank_closed`, `bank_name_mismatch`, `sanctions_confirmed`, `shell_company_suspected`, `vendor_on_hold`
- **`"awaiting_information"`**: Hard-stop flags present but NONE of the escalation triggers above (only `missing_required_documents`, `screening_not_run`, `expired_license`).

### Reportable UBO Counts
Count **unique beneficial owner names** from `ubo_list` whose `ownership_pct >= 25`. A name that appears in multiple ubo_list entries with different percentages only counts once; use the max percentage across entries for the threshold check.

### Follow-up Business IDs
All business IDs whose decision is NOT `"approve"`. Sorted ascending.

### Overall Release Readiness
`true` only if ALL businesses in the batch have decision `"approve"`.

---

## Workflow 3: Prepaid Expense Close Check

### Input
- `close_period` (YYYY-MM)
- `entity` (e.g., "Aurisic US")
- `accounts` array (e.g., ["1250", "1251"])
- `selected_prepaid_invoice_ids` list
- `variance_threshold_abs` (e.g., 100.00)

### Data Sources
1. `GET /api/prepaids/invoices?prepaid_invoice_id=<id>` — for each invoice
2. `GET /api/prepaids/gl-balances?account=<acct>&period=<period>` — GL ending balances

### Invoice-Level Calculations
For each invoice, using the close period as the reference month:

- **march_amortization** (monthly amortization for the close month): Use `monthly_amortization` from the API record directly. This is the straight-line monthly amount.
- **cumulative_amortization_through_march**: `monthly_amortization × number_of_months` where number_of_months = count of months from `service_start` month through the close-period month, inclusive. If `service_start` is after the close month, cumulative = 0.
- **ending_balance**: `original_amount - cumulative_amortization_through_march`. Round to 2 decimals. Floor at 0.00 (never negative).
- **default_missing_term_flag**: `true` if `data_quality_flags` array contains `"missing_contract_dates"`.
- **exception_flag**: `true` if `data_quality_flags` array is non-empty (any flag triggers this).

### Account-Level Rollup
For each account in scope:

- **original_amount_total**: Sum of `original_amount` across account's invoices
- **march_amortization_total**: Sum of `march_amortization` across account's invoices
- **cumulative_amortization_through_march**: Sum of cumulative amortization across account's invoices
- **schedule_ending_balance**: Sum of `ending_balance` across account's invoices
- **gl_ending_balance**: From GL balances API for that account+period
- **variance_amount**: `schedule_ending_balance - gl_ending_balance`
- **variance_flag**: `true` if `abs(variance_amount) > variance_threshold_abs`
- **has_default_missing_term_flag**: `true` if ANY invoice in that account has `default_missing_term_flag == true`
- **account_status**:
  - `"reconciled"` — variance_flag is false
  - `"requires_reconciliation"` — variance_flag is true

### List Outputs
- **selected_invoice_ids**: Same order as the input scope
- **invoice_results**: Same order as the input scope
- **default_missing_term_invoice_ids**: Ascending, only invoices with flag=true
- **exception_invoice_ids**: Ascending, only invoices with exception_flag=true
- All currency amounts to 2 decimal places.

---

## Workflow 4: Stale AP Snapshot Reconciliation

### Input
- List of candidate claim IDs
- Stale snapshot CSV/JSON (context only, NOT the system of record)
- Close period context

### Data Sources (system of record)
1. `GET /api/claims?claim_id=<id>` — current claim state
2. `GET /api/ap/bills?claim_id=<id>` — current AP bills
3. `GET /api/ap/payments?bill_id=<id>` — current payment state for each bill
4. `GET /api/close/logs?period=<period>` — close log entries

### Classification

#### eligible_claim_ids
Claims that pass current reconciliation: claim is approved/paid, has a valid AP bill (not void, amount match, vendor match if applicable), no blockers.

#### not_ready_claim_ids
Claims failing any of: unapproved status, void bill, amount/vendor mismatch, no bill.

### Stale Snapshot Correction Codes
Compare snapshot vs current API state and assign ONE code per claim:

| Code | When to Use |
|---|---|
| `current_snapshot_ok` | No material difference between snapshot and current state |
| `mark_in_flight_payment` | Snapshot had no payment; current API shows a payment in `"processing"` or `"scheduled"` status against the correct bill |
| `replace_with_matched_paid_bill` | Snapshot linked wrong bill; current API shows a different bill that is paid+cleared matching the claim amount |
| `exclude_amount_or_vendor_mismatch` | Claim amount ≠ bill amount, OR vendor mismatch between claim and bill |
| `ignore_void_bill` | Snapshot bill is now `"void"` in current API |
| `block_unapproved_claim` | Claim is NOT approved (e.g., `"needs_receipt"`, `"submitted"`) regardless of bill/payment state |

### AP Balance by Claim
For each candidate claim, compute the open AP balance:
- If claim is not approved → 0.00
- If only void bills exist → 0.00
- If amount/vendor mismatch → 0.00
- Otherwise → sum of `bill.amount` for non-void, unpaid bills (bills where no cleared payment exists for the full amount)
- Always return all candidate claim IDs as keys

### Close Log Requirement
- `required`: `true` when ANY snapshot-vs-current discrepancy exists (any correction other than `current_snapshot_ok`), OR when any claim is not ready. `false` otherwise.
- `ids`: Ascending list of relevant close-log IDs. Include the most recent AP-area close log for the period if close_log is required.

### Batch Status
- `"ready_to_send"` — all claims eligible, no corrections needed
- `"needs_ap_refresh"` — some eligible but corrections exist; outdated snapshot
- `"blocked"` — all claims not_ready

---

## Workflow 5: Account-Change Payment Release Review

### Input
- Account-change event batch (tickets with business_id, vendor_id, requested_bank_last4, change_type, requested_release_amount)
- `as_of_date` (review date)

### Data Sources
1. `GET /api/compliance/objects?business_id=<id>` — compliance status per business
2. `GET /api/vendors?vendor_id=<id>` — vendor details

### Per-Business Decision Rules

- **`"release"`**: ALL conditions met:
  - `bank_account_status == "verified"` (not name_mismatch, not closed)
  - `license_expiry >= as_of_date` (not expired)
  - `pep_status == "none"` (not confirmed_pep, not possible_pep)
  - `sanctions_check_status == "clear"`
  - `risk_score < 70`
  - `tax_id` is valid (see below)
  - `missing_fields` is empty
  - `shell_company_suspected == false`

- **`"escalate"`**: ANY escalation trigger present:
  - `pep_status == "confirmed_pep"`
  - `tax_id` is invalid (non-numeric chars, or all digits identical, or wrong format)
  - `sanctions_check_status == "confirmed_match"`
  - `shell_company_suspected == true`
  - **OR** 3+ issues from the hold-trigger list below

- **`"hold"`**: Issues present but NONE of the escalation triggers above. Hold-trigger issues:
  - `bank_account_status in ["name_mismatch", "closed"]`
  - `license_expiry < as_of_date` (expired license)
  - `sanctions_check_status == "not_run"` or `pep_status == "not_run"` or `pep_status == "possible_pep"`
  - `risk_score >= 70`
  - `missing_fields` non-empty

### Tax ID Validation
A tax_id is **valid** when it matches the pattern `TIN` followed by exactly 6 numeric digits (0-9), with at least two distinct digits (e.g., `TIN111111` and `TIN999999` are invalid). Any non-numeric character in the digits portion (e.g., `TIN12X899`) is also invalid. Use the **compliance object's** tax_id field (not the vendor's tax_id).

### Derived Lists (all ascending by business_id)

- **bank_mismatch_ids**: `compliance.bank_account_status == "name_mismatch"` (NOT "closed" — only name_mismatch)
- **invalid_tax_ids**: Failed tax ID validation
- **expired_license_ids**: `compliance.license_expiry < as_of_date`
- **review_queue_ids**: All business IDs NOT decided as `"release"`
- **risk_score_override_flags**: `compliance.risk_score >= 70`

---

## General Conventions

### Sorting
- Claim-ID lists: **ascending lexicographic** (string sort, e.g., `CLM-2025-0037` before `CLM-2025-0080` before `CLM-2025-OPS-017` before `CLM-2025-FIN-042` — note: digits sort before letters in standard ASCII, and uppercase letters sort before lowercase)
- Business-ID lists: **ascending lexicographic** (e.g., `BUS-2025-0006` before `BUS-2025-0009`)
- Invoice-ID lists: **ascending lexicographic** unless template says "same order as input scope"
- Hard-stop flag lists within a business: **alphabetical** by flag name

### Currency
- All amounts in **USD**, reported to **2 decimal places**.
- Use **dollars** (not cents) — e.g., `1842.36` not `184236`.
- Round after each arithmetic operation; floor ending balances at 0.00.

### API / System-of-Record Precedence
- The live API (`/api/*`) is **always the system of record**.
- Local payloads (CSV snapshots, batch JSON) are **context only** — never override current API data.
- If the API returns no data for a claim/business, treat it as missing/blocked.

### Common Pitfalls
1. **Void bills**: A void bill does NOT represent an open payable. Exclude void bills from AP balance totals and from payable classification.
2. **Multiple bills per claim**: A claim may link to multiple AP bills. Check ALL bills, not just the first. Use the bill whose amount matches the claim amount for payment matching.
3. **Bill amount ≠ claim amount**: This is a mismatch and blocks the claim, even if the bill status is "approved" or "paid". The AP bill must match the claim amount.
4. **Processing vs cleared payments**: A payment with status `"processing"` or `"scheduled"` does NOT settle a bill — only `"cleared"` payments settle. However, in-flight (processing) payments on a correct bill indicate the claim should still be classified as payable (open) rather than blocked.
5. **Vendor mismatch**: When a claim has a non-null `vendor_id`, the AP bill must belong to the same vendor. If the claim has `vendor_id: null`, skip vendor matching (only amount matching applies).
6. **UBO duplicate names**: The same person may appear in multiple `ubo_list` entries. Count unique names, not entries. Use the highest ownership_pct for the threshold check.
7. **Straight-line amortization**: The `monthly_amortization` field in the API is already computed. Use it directly — do not recalculate from original_amount and service period.
8. **Month counting for cumulative amortization**: Count from `service_start` month through the close-period month, inclusive. January through March = 3 months.
9. **Prepaid ending balance flooring**: If cumulative amortization exceeds original amount due to rounding, floor ending_balance at `0.00`, never go negative.
10. **Close log period matching**: When fetching close logs, use the period relevant to the task (e.g., the claim's close period, not the current date).
11. **Snapshot is stale by definition**: Never trust the snapshot's amounts, statuses, or bill/payment links over current API data.
12. **Tax ID from compliance, not vendor**: The verification uses the compliance object's tax_id, which may differ from the vendor master's tax_id.
