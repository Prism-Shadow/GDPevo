# ERP Finance Expense-Control — Skill Reference

## Environment & API

All tasks use the shared ERP finance REST API. Filter records with exact-match query
parameters by field name (`claim_id`, `business_id`, `vendor_id`, `account`, `period`,
`bill_id`). Paginate with `limit` and `offset`. The API is read-only; no
create/update/delete operations are needed.

Key endpoints:

| Endpoint | Use |
|---|---|
| `/api/claims` | Expense claim records |
| `/api/ap/bills` | AP bills linked to claims |
| `/api/ap/payments` | Payments linked to bills |
| `/api/vendors` | Vendor master data (by `vendor_id`) |
| `/api/compliance/objects` | Compliance records (by `business_id`) |
| `/api/prepaids/invoices` | Prepaid invoice schedules (by `prepaid_invoice_id`) |
| `/api/prepaids/gl-balances` | GL ending balances (by `account` + `period`) |
| `/api/close/logs` | Close-period log entries |

---

## 1. Expense Claim Close Review (Reimbursement-to-AP)

### Claim Classification

For each claim ID in the batch, fetch the claim, its AP bills, and their payments.

| Category | Condition |
|---|---|
| **Paid** | Claim has a bill whose amount matches the claim amount, the bill is `paid`, AND a payment for that bill is `cleared`. A claim is paid even if it also has stale/wrong-amount bills linked — the matched paid bill controls. |
| **Payable** | Claim is `approved`, has at least one valid AP bill (not `void`) whose amount matches the claim amount, and the bill is NOT settled (payment not yet `cleared`). |
| **Blocked** | Claim has NO valid matching bill, OR the bill is `void`, OR the bill amount does not match the claim amount, OR the claim status is not `approved`. |

### CRM-Required Claims

All blocked claims that need expense-case owner cleanup or AP-link remediation are
`crm_required`. In practice this is typically all blocked claims — the distinction
between reimbursement-case issues (missing receipts, policy flags) and AP/payment
evidence issues (void bills, amount mismatches, missing bills) is preserved in how
the claim is categorized, but both types require owner follow-up.

### AP Open Balance

Sum the bill amounts for **payable claims only**, where the bill is valid (not void,
amount matches the claim). Do not include paid claims or blocked claims.
Report in USD to 2 decimal places.

### Batch Status

- `blocked` — any claim in the batch is blocked.
- `open_payables` — no blocked claims, but at least one payable claim remains.
- `ready_to_close` — no blocked claims and no payable claims (all paid).

### Reviewed Claim Count

The number of claim IDs in the requested batch (not all claims in the system).

### Output Ordering

All claim-ID lists must be sorted **ascending by claim ID**.

---

## 2. Vendor Onboarding Finance-Risk Release

### Data Sources

Cross-reference `/api/compliance/objects` (by `business_id`) with `/api/vendors`
(by `vendor_id` from the compliance record). The onboarding batch payload provides
the `business_ids` and an `as_of_date`.

### Per-Business Decision

| Decision | Criteria |
|---|---|
| `approve` | No hard-stop flags; vendor is active; license is valid as of `as_of_date`; PEP, sanctions, and bank checks are clear; tax ID matches between compliance and vendor. Review status of `in_review` alone does NOT block approval if all checks pass. |
| `awaiting_information` | Some checks are inconclusive or data is missing, but no clear hard-stop flag exists. |
| `escalate` | One or more hard-stop flags are present, OR the vendor is `on_hold`, OR there is a confirmed PEP, OR multiple red flags combine to create elevated risk. |

### Hard-Stop Flags

Available flags (alphabetical per business):

| Flag | Trigger |
|---|---|
| `bank_closed` | Compliance `bank_account_status` is `closed`. |
| `bank_name_mismatch` | Compliance `bank_account_status` is `name_mismatch`. |
| `confirmed_pep` | Compliance `pep_status` is `confirmed_pep`. |
| `expired_license` | Compliance `license_expiry` date is **strictly before** the `as_of_date`. A license expiring on the as_of_date itself is NOT expired. |
| `missing_required_documents` | Compliance `missing_fields` is non-empty. |
| `sanctions_confirmed` | Compliance `sanctions_check_status` is `confirmed`. |
| `screening_not_run` | Compliance `sanctions_check_status` is `not_run`. |
| `shell_company_suspected` | Compliance `shell_company_suspected` is `true`. |
| `vendor_on_hold` | Vendor `status` is `on_hold`. |

Sort each business's flags **alphabetically**. Return an empty list `[]` when none apply.

### Reportable UBO Counts

Count **unique beneficial-owner names** whose `ownership_pct` is **≥ 25%**.
If the same name appears in multiple UBO entries for the same business, count
that name once — deduplicate by name, not by entry. Report as an integer.

### Follow-Up Business IDs

All business IDs whose decision is not `approve`. Sorted ascending.

### Overall Release Ready

`true` only if **every** listed business has decision `approve`.

### Tax ID Validation

Compare compliance `tax_id` with vendor `tax_id`. A mismatch means the tax ID
is invalid/untrusted. Non-standard TIN formats (e.g. containing "X") are also
a red flag.

---

## 3. Prepaid Close Check

### Invoice-Level Calculations

For each invoice in the prepaid scope, using the close period (e.g. March 2025):

- **Months elapsed through the close period**: Count full calendar months from
  `service_start` through the close month, inclusive. For a service starting
  January 1 with a March close, that is 3 months (Jan, Feb, Mar). For a service
  starting mid-month (e.g. March 15), the March period counts as 1.

- **March amortization** (single-month): Use `monthly_amortization` from the API
  as-is.

- **Cumulative amortization through March**: `monthly_amortization × months_elapsed`,
  capped at `original_amount` for fully-amortized contracts. Use the API's
  `monthly_amortization` value directly for multiplication; do NOT recompute from
  `original_amount ÷ total_months`.

- **Ending balance**: `original_amount − cumulative_amortization`. When the contract
  is fully amortized (all months elapsed), ending balance is `0.00`.

### Data Quality Flags

| Flag | Meaning |
|---|---|
| `default_missing_term_flag` | Invoice has `missing_contract_dates` in its `data_quality_flags`. |
| `exception_flag` | Invoice has a non-empty `data_quality_flags` list (any flag: `rounded_amount`, `missing_contract_dates`, etc.). |

### Account Rollup

Group invoices by `account` (1250 or 1251). For each account compute:

- `selected_invoice_count` — number of scoped invoices for that account
- `original_amount_total` — sum of `original_amount`
- `march_amortization_total` — sum of March amortizations
- `cumulative_amortization_through_march` — sum of cumulative amortizations
- `schedule_ending_balance` — `original_amount_total − cumulative_amortization_through_march`
- `gl_ending_balance` — from `/api/prepaids/gl-balances`
- `variance_amount` — `schedule_ending_balance − gl_ending_balance`
- `variance_flag` — `true` if `|variance_amount| > variance_threshold_abs` (default: 100.00)
- `has_default_missing_term_flag` — `true` if ANY invoice in the account has `default_missing_term_flag`
- `account_status`:
  - `reconciled` — variance within threshold AND no default/missing term invoices
  - `variance_review` — variance exceeds threshold but no default/missing term invoices
  - `requires_reconciliation` — any invoice has default/missing term issues OR variance is extreme

### Output Ordering

- `selected_invoice_ids`: same order as in `prepaid_close_scope.json`
- `invoice_results`: same order as in `prepaid_close_scope.json`
- `default_missing_term_invoice_ids`: ascending by invoice ID
- `exception_invoice_ids`: ascending by invoice ID

All currency amounts in USD to 2 decimal places.

---

## 4. Stale AP Snapshot Reconciliation

### Approach

The stale CSV snapshot is **context only**, not the system of record. Reconcile each
candidate claim against current API data (claim, bills, payments). The snapshot
correction field records what the stale snapshot got wrong.

### Snapshot Correction Values

| Correction | When to Use |
|---|---|
| `current_snapshot_ok` | Current API data matches the snapshot — no correction needed. |
| `mark_in_flight_payment` | Snapshot showed no payment, but a payment is now `processing` or `scheduled`. The bill amount matches the claim. |
| `replace_with_matched_paid_bill` | Snapshot referenced the wrong bill; the correct bill (matching claim amount) is `paid` with a `cleared` payment. |
| `exclude_amount_or_vendor_mismatch` | The bill amount does not match the claim amount, OR the vendor on the bill does not match the claim's expected vendor. |
| `ignore_void_bill` | The snapshot's bill is now `void` in current data. |
| `block_unapproved_claim` | The claim's current status is NOT `approved` (e.g. `needs_receipt`, `submitted`, `rejected`). |

### AP Balance by Claim

For each claim, compute the open AP balance as:

> Bill amount − sum of cleared payment amounts

Only consider bills that are NOT void. If no valid bill exists for the claim,
balance is `0.00`. If the only bill has an amount mismatch with the claim,
the mismatch takes precedence (the bill should be excluded), and balance is `0.00`.

### Eligibility

- **Eligible**: Claim is approved, has a valid matching bill (amount matches, not void), and payment is either in-flight or the claim is settled through a correct paid bill.
- **Not ready**: All other claims — unapproved, void bill, amount/vendor mismatch, or no bill.

### Close Log Required

Set `required: true` when the batch contains stale/incorrect snapshot rows that
need documentation. Include specific close-log IDs from `/api/close/logs` that
reference stale AP exports, legacy imports, or duplicate lines related to the
claims in scope. Use an empty list if no specific log entries are relevant.

### Batch Status

- `ready_to_send` — all claims are eligible, no corrections needed.
- `needs_ap_refresh` — some snapshot rows are stale/incorrect, but claims themselves are ready once AP data is refreshed.
- `blocked` — one or more claims have blocking issues (unapproved, void bill, no bill, amount mismatch).

### Output Ordering

All claim-ID lists sorted **ascending by claim ID**.

---

## 5. AP Payment Release After Account-Change Events

### Data Sources

For each `business_id` in the batch, fetch `/api/compliance/objects` and the
linked `/api/vendors` record. Cross-reference with the account-change ticket
(`requested_bank_last4`, `change_type`, `priority`, `requested_release_amount_usd`).

Review date is the batch `as_of_date`.

### Decision Logic

| Decision | Criteria |
|---|---|
| `release` | All checks pass: bank verified, license valid, PEP clear/none, sanctions clear, no shell-company flag, vendor active, tax ID matches between compliance and vendor, review complete, risk score below override threshold. |
| `hold` | One or two issues exist that can be resolved without escalation: bank name mismatch, review in progress, missing documents, moderate risk, sanctions not yet run. The ticket's `change_type` may address the issue (e.g. reactivation after closed bank). |
| `escalate` | Multiple severe issues: confirmed PEP, vendor on hold, tax ID mismatch, multiple flags, or a combination that creates elevated risk beyond routine hold. Also escalate when the compliance review is `escalated` or `not_started` AND other flags exist. |

### Flag Lists (all sorted ascending by business_id)

| Field | Definition |
|---|---|
| `bank_mismatch_ids` | Compliance `bank_account_status` is `name_mismatch`. |
| `invalid_tax_ids` | Compliance `tax_id` ≠ Vendor `tax_id`, OR tax ID contains non-standard characters (e.g. "X" in a TIN). |
| `expired_license_ids` | License `expiry` date is strictly before `as_of_date`. |
| `review_queue_ids` | Business requires compliance/AP review before release. Include when `review_status` is NOT `approved`. (A review status of `approved` means review is complete even if other issues exist.) |
| `risk_score_override_flags` | Compliance `risk_score` ≥ 70. |

---

## General Conventions

### Currency

All monetary values in **USD**, reported to **2 decimal places** (cents). Use
standard rounding (half-up).

### Sorting

- Claim-ID lists: **ascending by claim ID** (lexicographic string order).
- Business-ID lists: **ascending by business_id** (lexicographic string order).
- Hard-stop flags within a business: **alphabetical**.
- Invoice lists: same order as the scope input file.

### Source Precedence

1. Current API data is the **system of record**.
2. Stale snapshots and batch payloads are **context only**.
3. When API data contradicts a snapshot/payload, the API wins.

### Common Pitfalls

- **Partial-month contracts**: For prepaid amortization, count the start month as
  month 1 even if the service starts mid-month. Do not prorate the monthly amount.
- **Rounding in fully-amortized contracts**: Cap cumulative amortization at
  `original_amount` so ending balance is exactly `0.00`, not `0.01`.
- **Multiple bills per claim**: A claim may have several bills. Classify based on
  the bill that matches the claim amount. Ignore stale/wrong-amount bills for
  balance and eligibility purposes, but they may still need a snapshot correction.
- **License expiry vs as_of_date**: A license expiring **on** the as_of_date is
  NOT expired. Only licenses with expiry dates **strictly before** the as_of_date
  are expired.
- **UBO deduplication**: Count unique names, not unique entries. The same person
  listed multiple times at different ownership percentages counts as one UBO if
  any of their entries meets the 25% threshold.
- **Tax ID validation**: Check both format validity (no "X" or placeholder patterns)
  AND cross-system consistency (compliance vs vendor).
- **Void bills**: Always exclude void bills from AP balance calculations and
  eligibility determinations.
- **Payment status `processing`**: A payment that is `processing` is NOT `cleared`.
  The bill amount remains in the open AP balance.
