# ERP Finance Expense-Control Skill

## Overview

This skill covers expense claim close review, vendor onboarding risk assessment,
prepaid-expense close reconciliation, stale AP snapshot correction, and
account-change payment-release review in the shared ERP finance API.

**API base URL:** Use the runner-provided base URL. All endpoints support both
`/api/<resource>` and `/<resource>` paths with exact-match query parameters,
`limit`, and `offset` for pagination.

## Core Endpoints

| Resource | Endpoints | Key Fields |
|---|---|---|
| Claims | `/api/claims` | claim_id, amount, status, approved_date, receipt_status, policy_flags, vendor_id, notes |
| AP Bills | `/api/ap/bills` | bill_id, claim_id, amount, status, vendor_id, account, memo |
| AP Payments | `/api/ap/payments` | payment_id, bill_id, amount, status, method, payment_date |
| Vendors | `/api/vendors` | vendor_id, vendor_name, status, tax_id, bank_account_last4 |
| Compliance | `/api/compliance/objects` | business_id, vendor_id, bank_account_status, pep_status, license_expiry, sanctions_check_status, shell_company_suspected, risk_score, missing_fields, tax_id, ubo_list, review_status |
| Prepaid Invoices | `/api/prepaids/invoices` | prepaid_invoice_id, account, original_amount, monthly_amortization, service_start, service_end, data_quality_flags |
| GL Balances | `/api/prepaids/gl-balances` or `/gl/balances` | account, account_name, entity, period, ending_balance |
| Close Logs | `/api/close/logs` | log_id, area, message, status, period, related_account |

## Expense Claim Close Review Workflow

### Data Gathering
1. Fetch all claims from `/api/claims` and filter to the requested claim IDs.
2. Fetch all AP bills from `/api/ap/bills`. Bills link to claims via `claim_id`.
3. Fetch all AP payments from `/api/ap/payments`. Payments link to bills via `bill_id`.

### Claim Classification

**Paid claims** (`paid_claim_ids`):
- Claim status is `"paid"` **AND**
- At least one bill linked to the claim has the **same amount** as the claim **AND** that bill has status `"paid"` **AND**
- A cleared payment exists for that bill matching the claim amount.
- A claim may have multiple bills linked. Only the bill with matching amount and cleared payment confirms paid status; ignore other linked bills for paid determination.

**Payable claims** (`payable_claim_ids`):
- Claim is approved **AND**
- A bill exists linked to the claim with the **same amount** **AND**
- The bill status is not `"void"` **AND**
- No cleared payment exists for the bill (payment may be scheduled, processing, or absent).
- These remain in the AP reimbursement queue.

**Blocked claims** (`blocked_claim_ids`):
- No bill linked to the claim, **OR**
- Bill amount does **not** match claim amount, **OR**
- Bill status is `"void"`, **OR**
- Claim has unresolved policy issues without a valid AP link.
- A claim with an amount-mismatched bill is blocked regardless of claim-level data quality.

**CRM-required claims** (`crm_required_claim_ids`):
- **All blocked claims** are CRM-required. Every blocked claim needs either
  expense-case owner cleanup or AP-link remediation.

### AP Open Balance
- `ap_open_balance_total`: Sum the bill amounts (in USD, 2 decimal places) of
  all payable claims' open bills, subtracting only **cleared** payments.
  Scheduled and processing payments do **not** reduce the balance.
- Only bills for **payable** claims contribute.

### Batch Status
- `"blocked"`: Any claim in the batch is blocked.
- `"open_payables"`: No blocked claims, but payable claims remain with unpaid bills.
- `"ready_to_close"`: All claims are paid (no blocked, no payable).

### Output Conventions
- `reviewed_claim_count`: Total number of claim IDs in the requested batch.
- All claim ID lists sorted **ascending** by claim ID.
- Currency amounts in USD with exactly 2 decimal places.

---

## Vendor Onboarding Finance-Risk Review

### Data Gathering
1. Fetch compliance objects from `/api/compliance/objects` for the target business IDs.
2. Fetch vendor records from `/api/vendors`. Match vendors to compliance records via `vendor_id`.
3. Use `as_of_date` from the batch payload for all date comparisons.

### Hard Stop Flags (alphabetical order per business)

| Flag | Condition |
|---|---|
| `bank_closed` | compliance `bank_account_status` is `"closed"` |
| `bank_name_mismatch` | compliance `bank_account_status` is `"name_mismatch"` |
| `confirmed_pep` | compliance `pep_status` is `"confirmed_pep"` |
| `expired_license` | `license_expiry` < `as_of_date` |
| `missing_required_documents` | compliance `missing_fields` is non-empty |
| `screening_not_run` | `sanctions_check_status` is `"not_run"` |
| `shell_company_suspected` | `shell_company_suspected` is `true` |
| `vendor_on_hold` | vendor `status` is `"on_hold"` |

### Per-Business Decision Logic
- **`approve`**: No hard stop flags apply, vendor is active, all verifications passed.
- **`awaiting_information`**: No hard stop flags, but review is incomplete or information is pending.
- **`escalate`**: One or more hard stop flags apply.

Do **not** simply copy the current `review_status` from the source system.
Make an independent release-control assessment.

### Reportable UBO Counts
- Count **unique beneficial-owner names** (deduplicate by name) where `ownership_pct >= 25`.
- The reporting threshold is **25%**. Owners below 25% are not counted.
- If the same name appears in multiple UBO entries, count them once; use the highest
  ownership percentage for threshold comparison (do not aggregate across entries).

### Follow-Up and Release Readiness
- `follow_up_business_ids`: All business IDs whose decision is not `"approve"`, sorted ascending.
- `overall_release_ready`: `true` only if **every** listed business has decision `"approve"`.

### Output Conventions
- `per_business` sorted ascending by `business_id`.
- `hard_stop_flags` values sorted **alphabetically** within each business's list.
- Use empty list `[]` for businesses with no hard stop flags.
- `reportable_ubo_counts`: integer values, keyed by business_id.

---

## Prepaid-Expense Close Reconciliation

### Data Gathering
1. Fetch prepaid invoices from `/api/prepaids/invoices` and filter to the
   invoice IDs in the scope file.
2. Fetch GL balances from `/api/prepaids/gl-balances` filtered by:
   - `entity` matching the scope file entity
   - `account` in the scope file's account list
   - `period` matching the close period (format `YYYY-MM`)
3. Use the `variance_threshold_abs` from the scope file for variance flagging.

### Invoice-Level Calculations

For each invoice, using straight-line amortization **exactly as provided by the API**
(do not recalculate from original_amount / months):

- **march_amortization** (or current-period amortization): The `monthly_amortization`
  value from the API for the close period month.
- **cumulative_amortization_through_march**: `monthly_amortization × number_of_months`
  from `service_start` month through the close period month, inclusive.
  - Example: service_start=2025-01-01, close period=2025-03 → 3 months.
  - Example: service_start=2025-03-15, close period=2025-03 → 1 month (March only).
- **ending_balance**: `original_amount - cumulative_amortization_through_march`.
  Report to 2 decimal places.
- **default_missing_term_flag**: `true` if `data_quality_flags` includes
  `"missing_contract_dates"`. `"rounded_amount"` alone does **not** trigger this flag.
- **exception_flag**: `true` if `data_quality_flags` is **non-empty** (any data quality
  issue: `"rounded_amount"`, `"missing_contract_dates"`, etc.).

### Account-Level Rollup (per account)

- **selected_invoice_count**: Number of scoped invoices in this account.
- **original_amount_total**: Sum of all invoice `original_amount` values.
- **march_amortization_total**: Sum of all invoice march amortization values.
- **cumulative_amortization_through_march**: Sum of all invoice cumulative values.
- **schedule_ending_balance**: Sum of all invoice `ending_balance` values.
- **gl_ending_balance**: The GL `ending_balance` for this account/entity/period.
- **variance_amount**: `schedule_ending_balance - gl_ending_balance`.
- **variance_flag**: `true` if `|variance_amount| > variance_threshold_abs`.
- **has_default_missing_term_flag**: `true` if **any** invoice in this account
  has `default_missing_term_flag = true`.
- **account_status**:
  - `"reconciled"`: `variance_flag` is `false`.
  - `"requires_reconciliation"`: `variance_flag` is `true`.

### Output Conventions
- `invoice_results` ordered the same as the scope file's `selected_prepaid_invoice_ids`.
- `selected_invoice_ids` ordered the same as the scope file.
- `default_missing_term_invoice_ids` sorted ascending.
- `exception_invoice_ids` sorted ascending.
- All amounts in USD with 2 decimal places.
- `period` formatted as `YYYY-MM`.

---

## Stale AP Snapshot Reconciliation

### Data Gathering
1. Fetch current claims, bills, payments, and close logs from the API.
2. Treat the provided stale CSV snapshot as **context only**, not the system of record.
3. Compare the current API state against the snapshot for each candidate claim ID.

### Claim Eligibility
- **eligible_claim_ids**: Claims that can remain in the AP batch.
  - Claim is approved and has a matching bill (same amount) with no blockers.
- **not_ready_claim_ids**: Claims that should be removed from the batch.
  - Already paid/settled, amount mismatch, void bill, unapproved claim, or
    any other blocker that prevents the claim from being in the batch.

### AP Balance by Claim
- Report the **current** open AP balance for each candidate claim ID.
- Use the bill amount from the **current** API state, minus any **cleared** payments.
- For void bills: balance is `0.00` (void bills are ignored).
- For claims with no valid bill: balance is `0.00`.
- Processing and scheduled payments do **not** reduce the balance.

### Stale Snapshot Corrections (per claim)

| Correction | When to Use |
|---|---|
| `current_snapshot_ok` | Snapshot accurately reflects current state; no correction needed. |
| `mark_in_flight_payment` | A payment exists now that was not in the snapshot. |
| `replace_with_matched_paid_bill` | Snapshot referenced the wrong bill; a matching paid bill with cleared payment exists in current data. |
| `exclude_amount_or_vendor_mismatch` | Bill amount does not match claim amount, or vendor mismatch exists. |
| `ignore_void_bill` | The snapshot's bill is now `"void"` in current data. |
| `block_unapproved_claim` | The claim is not in `"approved"` status in current data. |

### Close Logs and Batch Status
- `close_log_required.required`: `true` if there are relevant blocked or
  ready-for-review close log entries related to legacy import duplicates or
  AP export refresh issues.
- `close_log_required.ids`: Relevant close log IDs, sorted ascending by log ID.
- `batch_status`:
  - `"ready_to_send"`: All claims eligible.
  - `"needs_ap_refresh"`: Some claims eligible but others need correction.
  - `"blocked"`: No claims are eligible.

### Output Conventions
- All claim ID lists sorted ascending by claim ID.
- All amounts in USD with 2 decimal places.
- `ap_balance_by_claim` keys are the candidate claim IDs.

---

## Account-Change Payment Release Review

### Data Gathering
1. Fetch compliance objects from `/api/compliance/objects` for the target business IDs.
2. Fetch vendor records from `/api/vendors`. Match to compliance via `vendor_id`.
3. Use `as_of_date` (from the template, typically `"2025-06-01"`) for all date comparisons.
4. Cross-reference the account-change event payload (bank_last4, change_type, priority)
   against compliance and vendor data.

### Decision Rules
- **`release`**: No compliance issues, vendor active, bank verified, tax ID matches,
  license valid, risk score acceptable, no sanctions/PEP concerns.
- **`hold`**: Issues exist but are potentially resolvable without escalation.
- **`escalate`**: Confirmed PEP, bank name mismatch combined with other flags,
  sanctions screening not run combined with expired license, tax ID mismatch, or
  multiple hard stops. Urgent priority combined with compliance flags is an
  escalation trigger.

### Special Lists

- **bank_mismatch_ids**: Business IDs where compliance `bank_account_status` is
  `"name_mismatch"`. Bank `"closed"` is **not** a name mismatch.
- **invalid_tax_ids**: Business IDs where the **compliance `tax_id`** does **not**
  match the **vendor `tax_id`**.
- **expired_license_ids**: Business IDs where `license_expiry` < `as_of_date`.
  Use strict less-than comparison.
- **review_queue_ids**: Business IDs whose decision is **not** `"release"`.
  Sorted ascending.
- **risk_score_override_flags**: Business IDs where `risk_score >= 70`.

### Output Conventions
- `target_business_ids`: All business IDs from the batch, sorted ascending.
- `decisions` keyed by business_id; values from `["release", "hold", "escalate"]`.
- All ID lists sorted **ascending** by business_id.
- `task_id`, `batch_id`, `as_of_date` must match the required template values exactly.

---

## General Conventions (All Tasks)

### Sorting
- Claim IDs, business IDs, invoice IDs, and close log IDs: **ascending** sort.
- Hard stop flag lists: **alphabetical** sort within each business.
- Invoice results and selected invoice IDs: preserve the **input scope file order**.

### Currency and Precision
- All monetary amounts in **USD**.
- Report to exactly **2 decimal places**.
- Use the amounts exactly as provided by the API; do not recalculate amortization
  from original_amount / months. The `monthly_amortization` field is authoritative.

### Source Precedence
1. **Current API data** is the system of record.
2. Stale snapshots, CSVs, and batch payloads are **context only** — they may be
   outdated or incorrect.
3. Vendor data and compliance data must be cross-referenced. When they disagree
   (e.g., different tax_id values), the discrepancy itself is a finding.

### Common Pitfalls
- **Bill-claim amount mismatch**: A bill linked to a claim with a different amount
  makes the claim blocked, even if the claim looks clean otherwise.
- **Multiple bills per claim**: A claim may have more than one bill linked. Only
  the bill with matching amount and cleared payment confirms paid status. Other
  linked bills may indicate data quality issues like duplicate imports.
- **Void bills**: A void bill means there is no valid AP instrument for the claim.
  Ignore void bills for balance calculations and flag the claim as blocked.
- **Processing vs. cleared payments**: Only `"cleared"` payments reduce AP balances.
  `"scheduled"` and `"processing"` payments do not.
- **License expiry comparisons**: Use strict less-than (`expiry < as_of_date`).
  A license expiring the day after the review date is **not** expired.
- **UBO deduplication**: Count unique names, not unique entries. The same person
  appearing multiple times counts once. Use the threshold comparison per-entry;
  do not aggregate percentages across entries.
- **Vendor on_hold**: Check vendor `status` in addition to compliance data.
  An on-hold vendor triggers a hard stop even if compliance data looks clean.
- **Tax ID cross-referencing**: Always compare compliance `tax_id` with vendor
  `tax_id`. A mismatch means the tax ID is invalid for release purposes.
- **GL balance filtering**: Match by account, entity, AND period. Using the wrong
  period or entity will produce incorrect variances.
- **Invoice result ordering**: Must follow the scope file order, not alphabetical
  or account order.
- **Straight-line amortization**: Use the API's `monthly_amortization` field directly.
  Do not recalculate; rounding differences between `monthly_amortization × n` and
  `original_amount` are expected and should be preserved as-is.
