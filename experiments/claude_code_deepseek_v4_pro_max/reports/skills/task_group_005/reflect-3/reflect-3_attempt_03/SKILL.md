# ERP Finance Expense-Control Skill

## API Overview

Base the API entrypoint on the URL provided by the task runner. The ERP finance environment exposes these endpoints used across expense-control tasks:

| Endpoint | Purpose |
|---|---|
| `/api/claims` | Expense claim records |
| `/api/ap/bills` | AP bill/invoice records |
| `/api/ap/payments` | Payment records linked to bills |
| `/api/vendors` | Vendor master data (bank, tax ID, status) |
| `/api/compliance/objects` | Compliance & risk screening per business |
| `/api/prepaids/invoices` | Prepaid invoice schedules |
| `/api/prepaids/gl-balances` or `/gl/balances` | GL ending balances by account/period |
| `/api/close/logs` | Close/reconciliation log entries |

**Filtering:** All endpoints support exact-match query parameters by field name (e.g., `?claim_id=CLM-2025-0090`, `?business_id=BUS-2025-0009`). Use `limit` and `offset` for pagination.

**Source precedence:** The live API is always the system of record. Treat any local data payloads (snapshots, CSVs, batch JSON) as stale context — they must be validated against the current API state. When the API and a local payload disagree, the API wins.

---

## 1. Expense Claim Close Review (AP Reimbursement Batch)

### Workflow
1. Query `/api/claims?claim_id=<id>` for each claim in the batch.
2. For each claim, query `/api/ap/bills?claim_id=<id>` to find linked AP bills.
3. For each bill found, query `/api/ap/payments?bill_id=<bid>` to check payment status.
4. Classify each claim into one of three buckets. Sort all ID lists ascending.

### Classification Rules

**Paid (`paid_claim_ids`):** A claim is settled when ALL of these hold:
- Claim status is `paid` (or the claim has a matching bill with `paid` status and a `cleared` payment).
- There exists an AP bill whose `amount` matches the claim `amount` AND whose `vendor_id` matches the claim `vendor_id`.
- There exists a payment for that bill with `status: "cleared"` and `amount` matching the claim amount.

**Payable (`payable_claim_ids`):** A claim stays in the AP reimbursement queue when:
- Claim status is `approved`.
- There exists an AP bill whose `amount` matches the claim `amount` AND whose `vendor_id` matches the claim `vendor_id`.
- The bill status is not `void`.
- The claim has NOT been fully settled (no cleared payment for the full matching amount).

**Blocked (`blocked_claim_ids`):** A claim must be held back when any of:
- No AP bill exists for the claim.
- The bill `amount` does not equal the claim `amount`.
- The bill `vendor_id` does not match the claim `vendor_id` (including when the claim has `vendor_id: null`).
- The bill `status` is `void`.
- The claim `status` is something other than `approved` or `paid` (e.g., `needs_receipt`).

**CRM-Required (`crm_required_claim_ids`):** Subset of blocked claims requiring expense-case owner or AP-link remediation. Include all blocked claims whose issue is a broken claim-to-bill link (amount mismatch, vendor mismatch, missing bill, void bill, or missing vendor).

### Output Fields

| Field | Type | Rule |
|---|---|---|
| `payable_claim_ids` | list[string] | Ascending by claim_id |
| `blocked_claim_ids` | list[string] | Ascending by claim_id |
| `paid_claim_ids` | list[string] | Ascending by claim_id |
| `ap_open_balance_total` | number (USD, 2dp) | Sum of bill amounts for **payable claims only** (not blocked, not paid) |
| `crm_required_claim_ids` | list[string] | Ascending by claim_id |
| `batch_status` | enum | `blocked` if any claim is blocked; `open_payables` if no blocked claims but unpaid payable bills remain; `ready_to_close` if all claims are paid |
| `reviewed_claim_count` | integer | Total number of claim IDs in the requested batch |

### Traps
- A claim may have MULTIPLE bills. Check all of them — one matching bill with cleared payment means the claim is paid, even if another bill for the same claim is stale.
- Do NOT count void bills toward `ap_open_balance_total`.
- A payment with status `processing` or `scheduled` does NOT settle a claim. Only `cleared` payments settle.
- Vendor matching must be exact by `vendor_id`. A claim with `vendor_id: null` can never have a matching bill.

---

## 2. Vendor Onboarding Finance-Risk Review

### Workflow
1. Query `/api/compliance/objects?business_id=<id>` for each business in the batch.
2. Query `/api/vendors?vendor_id=<vid>` using the `vendor_id` from the compliance record. Also try `/api/vendors?business_id=<id>` for cross-reference.
3. Merge findings from both sources. The vendor record provides `status` and `tax_id`; the compliance record provides all screening results.

### UBO Reporting Threshold

The beneficial-owner reporting threshold is **25%** (`ownership_pct >= 25`). Count **unique owner names** at or above 25%. If the same name appears on multiple UBO records, count it once regardless of aggregate ownership.

### Hard Stop Flags (alphabetically sorted per business)

| Flag | Trigger |
|---|---|
| `bank_closed` | Compliance `bank_account_status == "closed"` |
| `bank_name_mismatch` | Compliance `bank_account_status == "name_mismatch"` |
| `confirmed_pep` | Compliance `pep_status == "confirmed_pep"` |
| `expired_license` | Compliance `license_expiry` date is before the review/as-of date |
| `missing_required_documents` | Compliance `missing_fields` is non-empty |
| `sanctions_confirmed` | Compliance `sanctions_check_status` reports confirmed sanctions |
| `screening_not_run` | Compliance `sanctions_check_status == "not_run"` |
| `shell_company_suspected` | Compliance `shell_company_suspected == true` |
| `vendor_on_hold` | Vendor record `status == "on_hold"` |

`possible_pep` is NOT a hard stop flag. `pep_status == "not_run"` has no corresponding hard stop flag.

### Decision Rules

- **`approve`**: No hard stop flags present. Release for vendor access.
- **`awaiting_information`**: Issues exist but are resolvable with more data (e.g., missing documents, expired license that can be renewed). The business is not yet releasable.
- **`escalate`**: Multiple hard stop flags, confirmed PEP, shell company suspected, sanctions confirmed, or bank closed. Requires senior review.

### Output Fields

| Field | Type | Rule |
|---|---|---|
| `per_business` | list[object] | Ascending by `business_id`. Each: `{business_id, decision}` |
| `reportable_ubo_counts` | object | Keyed by `business_id`. Value = count of unique UBO names at ≥25% |
| `hard_stop_flags` | object | Keyed by `business_id`. Value = list of flag enums, alphabetical. Empty list `[]` when none apply |
| `follow_up_business_ids` | list[string] | All businesses NOT decided as `approve`. Ascending by business_id |
| `overall_release_ready` | boolean | `true` ONLY if every business decision is `approve` |

### Traps
- Always check the vendor API for `status: "on_hold"` — this is a hard stop NOT visible in compliance data alone.
- Compare vendor `tax_id` against compliance `tax_id`. A mismatch is a data integrity issue (though no hard stop flag exists for it; use it to inform the decision).
- The review `as_of_date` in the batch payload determines license expiry comparison. Use it, not the API query date.
- Do NOT treat `possible_pep` or `pep_status: "not_run"` as hard stop flags.

---

## 3. Prepaid Expense Close Reconciliation

### Workflow
1. Read the scope file for `selected_prepaid_invoice_ids`, target `accounts`, `close_period`, and `variance_threshold_abs`.
2. Query `/api/prepaids/invoices?prepaid_invoice_id=<id>` for each invoice.
3. Query `/api/prepaids/gl-balances?account=<acct>` and select the GL balance entry for the close period (e.g., `"2025-03"`).
4. Compute per-invoice amortization and per-account rollups.

### Amortization Calculation (Straight-Line Monthly)

For each invoice:
- **`march_amortization`**: The `monthly_amortization` value from the invoice record (1 month's amortization).
- **`cumulative_amortization_through_march`**: `monthly_amortization × months_from_start_through_close_period`. Count months inclusively from `service_start` month through the close period month. For a service starting January 1 with a March close: 3 months (Jan, Feb, Mar). For a service starting March 15 with a March close: 1 month.
- **`ending_balance`**: `original_amount − cumulative_amortization_through_march`, rounded to 2 decimal places.

### Per-Account Rollup

- **`selected_invoice_count`**: Number of scoped invoices for this account.
- **`original_amount_total`**: Sum of `original_amount` across scoped invoices.
- **`march_amortization_total`**: Sum of `monthly_amortization` across scoped invoices.
- **`cumulative_amortization_through_march`**: Sum of per-invoice cumulative amortization.
- **`schedule_ending_balance`**: `original_amount_total − cumulative_amortization_through_march`.
- **`gl_ending_balance`**: GL balance from `/api/prepaids/gl-balances` for the close period.
- **`variance_amount`**: `schedule_ending_balance − gl_ending_balance`.
- **`variance_flag`**: `true` when `abs(variance_amount) > variance_threshold_abs`.
- **`has_default_missing_term_flag`**: `true` if any scoped invoice for this account has a missing `service_start` or `service_end`, or if the invoice's `data_quality_flags` indicate default/missing contract terms.
- **`account_status`**: `reconciled` when variance_flag is false; `requires_reconciliation` when variance_flag is true.

### Invoice-Level Flags

- **`exception_flag`**: `true` when the invoice's `data_quality_flags` array is non-empty (any flag present: `rounded_amount`, `missing_contract_dates`, etc.).
- **`default_missing_term_flag`**: `true` when `service_start` or `service_end` is missing or the amortization term appears to use a default rather than the actual contract period.

### Output Ordering
- `selected_invoice_ids`: Same order as the scope file.
- `invoice_results`: Same order as the scope file.
- `default_missing_term_invoice_ids` and `exception_invoice_ids`: Ascending by invoice ID (ASCIIbetical).

### Traps
- The `monthly_amortization` from the API is the value to use — do not recalculate it from `original_amount / months`.
- GL balances may include invoices outside the scope. The variance compares the SCHEDULE total (scoped only) against the FULL GL balance — large variances are expected when many unscheduled items exist.
- Always use 2 decimal places for USD amounts.
- Rounding differences of $0.01 are common with straight-line amortization. They should not cause exception flags unless the `data_quality_flags` field already flags `rounded_amount`.

---

## 4. Stale AP Snapshot Reconciliation

### Workflow
1. Query current API state for each claim: `/api/claims`, `/api/ap/bills`, `/api/ap/payments`.
2. Compare each claim against its stale snapshot row (CSV or equivalent).
3. Identify discrepancies between the snapshot and the live system.
4. Determine eligibility, AP balances, corrections, and close-log needs.

### Eligibility

- **`eligible_claim_ids`**: Claims whose current state supports remaining in the AP batch. The claim must be `approved`, have a matching bill (amount + vendor match), and have no blocking issues.
- **`not_ready_claim_ids`**: Claims that should leave the batch because they are already paid, have mismatched bills, void bills, are unapproved, or have other blockers.

### AP Balance Per Claim

`ap_balance = bill_amount − sum_of_cleared_payments`. Ignore void bills. If no valid open bill exists, the balance is `0.00`. Use 2 decimal places.

### Stale Snapshot Corrections (one per claim)

| Correction Value | When to Use |
|---|---|
| `current_snapshot_ok` | Current API state matches the snapshot; no material discrepancy |
| `mark_in_flight_payment` | A payment now exists (processing/scheduled) that was absent from the snapshot |
| `replace_with_matched_paid_bill` | The snapshot referenced a wrong/mismatched bill; the correct matching bill is paid with cleared payment |
| `exclude_amount_or_vendor_mismatch` | The bill amount or vendor does not match the claim |
| `ignore_void_bill` | The bill was `approved` in the snapshot but is now `void` in the API |
| `block_unapproved_claim` | The claim status changed from `approved` (in snapshot) to a non-approved status (e.g., `needs_receipt`) in the live API |

### Close Logs

- `close_log_required.required`: `true` when the reconciliation reveals discrepancies requiring close-log entries (blocked claims, void bills, mismatches, payment status changes).
- `close_log_required.ids`: Relevant close-log IDs, sorted ascending by log ID. These come from `/api/close/logs` filtered by area (`AP` or `Expense`) and non-`closed` status.

### Batch Status

- `ready_to_send`: All claims eligible, no issues.
- `needs_ap_refresh`: Some claims need updated AP data but no hard blocks.
- `blocked`: At least one claim has a hard blocker (unapproved claim, void bill, amount/vendor mismatch).

All claim ID lists sorted ascending.

### Traps
- The snapshot is NOT the system of record. Always validate against the live API.
- Multiple bills may exist for one claim. The correction should address the bill REFERENCED in the snapshot.
- A claim can be `paid` in the API but still appear in a stale snapshot as `approved` — always check the current claim status first.
- Void bills contribute $0 to AP balances. Treat them as if they don't exist.

---

## 5. AP Payment Release After Account-Change Events

### Workflow
1. Query `/api/compliance/objects?business_id=<id>` for each target business.
2. Query `/api/vendors?vendor_id=<vid>` using the `vendor_id` from the compliance record and from the account-change batch.
3. Compare vendor bank details against the requested bank account in the change ticket.
4. Cross-reference tax IDs between vendor and compliance records.
5. Evaluate license expiry against the `as_of_date`.

### Decision Rules

- **`release`**: No hard stops. Bank last4 matches the requested account. Tax IDs match between vendor and compliance. License is valid. Compliance screening is clear. Risk score < 70.
- **`hold`**: Minor issues that need resolution before release (e.g., review still in progress, single moderate flag). Payment should wait but may not need escalation.
- **`escalate`**: Serious compliance flags (confirmed PEP, bank closed, sanctions issues, multiple hard stops), risk score ≥ 70 with other issues, invalid tax ID, or the compliance review is `escalated`/`not_started` with multiple flags.

### List Field Rules

| Field | Rule | Source |
|---|---|---|
| `bank_mismatch_ids` | Compliance `bank_account_status == "name_mismatch"` | `/api/compliance/objects` |
| `invalid_tax_ids` | Vendor `tax_id` ≠ Compliance `tax_id` (or tax ID has non-numeric format) | Compare vendor vs compliance |
| `expired_license_ids` | Compliance `license_expiry` < `as_of_date` | `/api/compliance/objects` |
| `review_queue_ids` | Businesses whose compliance `review_status` is not final/complete AND need compliance/AP review before release (e.g., `awaiting_information`, `not_started`) | `/api/compliance/objects` |
| `risk_score_override_flags` | Compliance `risk_score >= 70` | `/api/compliance/objects` |

All ID lists ascending by `business_id`.

### Traps
- Always fetch BOTH the vendor and compliance records. The vendor record may show a different `tax_id` or `status` than the compliance record.
- The `as_of_date` in the template determines license expiry. Use it, not today's date.
- A business can have `risk_score >= 70` AND be in other lists simultaneously — list membership is not mutually exclusive.
- Even if the bank last4 matches the requested account, check `bank_account_status` — a `name_mismatch` status means the bank account name doesn't match and the item goes in `bank_mismatch_ids`.

---

## General Conventions

### Currency & Precision
- All amounts in USD with exactly 2 decimal places (cents).
- Use standard rounding. Values like `0.00` must have two decimal places.

### Sorting
- Claim IDs: ASCIIbetical ascending (e.g., `CLM-2025-0015` before `CLM-2025-FIN-042` before `CLM-2025-OPS-017`).
- Business IDs: ASCIIbetical ascending (e.g., `BUS-2025-0006` before `BUS-2025-0009`).
- Close log IDs: ASCIIbetical ascending.
- Hard stop flags: Alphabetical by enum value string.
- Invoice results: Same order as the input scope file, NOT sorted.

### Shared API Patterns
- All list endpoints support `?field=value` exact-match filtering.
- Use `?limit=100` or higher to avoid pagination issues.
- When a query returns `count: 0` and `data: []`, the record does not exist — do not assume a default.

### Common Pitfalls
- **Vendor mismatch**: A claim with `vendor_id: null` can never have a matching AP bill. Always validate both amount and vendor.
- **Multiple bills per claim**: Always inspect all bills returned — one matching paid bill with cleared payment settles the claim regardless of other stale bills.
- **Stale snapshots**: Local payloads (CSVs, batch JSON) reflect a point-in-time snapshot that may be out of date. The live API is authoritative.
- **UBO deduplication**: Count unique owner names, not total records. The same person appearing at 24% and 45% counts as one reportable UBO (at the higher %).
- **License expiry comparison**: Use the review date or `as_of_date` from the batch, not the current date. A license expiring the day after the review date is NOT expired.
- **Variance direction**: `variance_amount = schedule − gl`. A negative variance means the GL balance exceeds the schedule balance (common when there are unscoped prepaid items in the GL).
