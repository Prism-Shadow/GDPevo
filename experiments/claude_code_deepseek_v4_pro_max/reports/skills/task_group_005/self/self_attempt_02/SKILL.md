# ERP Finance Expense-Control Skill

## Overview

This skill covers five expense-control workflows in the task_group_005 ERP finance
environment. All data is accessed through a shared JSON API. The skill describes
transferable business rules, API usage patterns, output conventions, calculation
rules, source precedence, and common pitfalls for held-out tests.

## API Reference

### Base URL

Use the environment-provided base URL. The remote environment serves both the
prefixed (`/api/...`) and unprefixed (`/...`) paths for every endpoint.
The two are interchangeable; prefer the prefixed form for clarity.

### Endpoints

| Endpoint                          | Key Fields                                                                                     | Filterable By                |
|-----------------------------------|-------------------------------------------------------------------------------------------------|------------------------------|
| `/api/claims`                     | claim_id, amount, status, approved_date, currency, department, employee_name, receipt_status, policy_flags, notes, vendor_id | claim_id                     |
| `/api/ap/bills`                   | bill_id, claim_id, vendor_id, amount, status, account, bill_date, due_date, memo, invoice_number, currency | bill_id, claim_id, vendor_id |
| `/api/ap/payments`                | payment_id, bill_id, vendor_id, amount, status, method, payment_date, bank_reference           | bill_id, vendor_id           |
| `/api/ap/aging`                   | bill_id, amount, balance, paid_amount, status, claim_id, vendor_id, due_date                    | bill_id, claim_id, vendor_id |
| `/api/vendors`                    | vendor_id, vendor_name, legal_name, status, tax_id, bank_account_last4, default_account, payment_terms, industry, updated_at | vendor_id                    |
| `/api/compliance/objects`         | business_id, vendor_id, business_name, bank_account_status, license_expiry, tax_id, risk_score, review_status, pep_status, sanctions_check_status, shell_company_suspected, missing_fields, ubo_list, jurisdiction, ownership_layer_count | business_id, vendor_id       |
| `/api/prepaids/invoices`          | prepaid_invoice_id, account, original_amount, monthly_amortization, service_start, service_end, recognition_method, data_quality_flags, vendor_id | prepaid_invoice_id           |
| `/api/prepaids/gl-balances`       | account, account_name, period, ending_balance, entity, source                                                              | account, period, entity      |
| `/api/close/logs`                 | log_id, period, area, status, message, owner, created_at, related_account                                                    | area, period, related_account |

All endpoints support `?field=value` exact-match filtering, `limit`, and `offset` for pagination.
Results wrap data in `{"count": N, "data": [...], "total": T}`.

### Data Model Relationships

```
claim ──(claim_id)──> AP bill ──(bill_id)──> AP payment
                           │
                           └──(bill_id)──> AP aging (computed balance)
                           
vendor ──(vendor_id)──> AP bills, AP payments, claims, compliance objects

compliance object ──(business_id)──> vendor ──(vendor_id)──> bills/payments

prepaid invoice ──(account)──> GL balance
```

**Claim-to-Bill Linking**: Bills reference claims via the `claim_id` field.
One claim may have multiple AP bills. Always use the bill whose amount matches
the claim amount, unless the only bill is void or the claim notes reference a
specific bill ID.

**Bill-to-Payment Linking**: Payments reference bills via `bill_id`.
One bill may have multiple partial payments (though the training data uses
one-payment-per-bill).

**Vendor-Business Mapping**: Compliance objects link to vendors via `vendor_id`.
Business IDs (`BUS-YYYY-NNNN`) map to vendor IDs (`VEN-NNNN`) through the
compliance object.

---

## Workflow 1: Reimbursement-to-AP Close Review

### Purpose

Classify a batch of expense claims as paid (settled), payable (ready for AP), or
blocked (needs owner cleanup before AP release).

### Endpoints Used

`/api/claims`, `/api/ap/bills`, `/api/ap/payments`, `/api/ap/aging`, `/api/close/logs`

### Business Rules

#### Claim Classification

**Paid** (`paid_claim_ids`):
- The claim has a linked AP bill whose amount matches the claim amount, AND
- That bill has a linked payment with status `"cleared"`, AND
- The payment amount equals the bill amount.
- A claim may also be considered settled if the claim status is `"paid"` AND
  there is a matching paid bill + cleared payment — even if another stale bill
  also links to the same claim.

**Payable** (`payable_claim_ids`):
- Claim status is `"approved"` (not `"submitted"`, `"needs_receipt"`, `"rejected"`,
  or `"paid"`), AND
- Has a valid (non-void) AP bill linked, AND
- No cleared payment fully settling the bill exists, AND
- The bill amount matches the claim amount, AND
- No blocking condition applies (see Blocked).

**Blocked** (`blocked_claim_ids`):
Any of the following makes a claim blocked:
- Claim status is NOT `"approved"` (e.g., `"submitted"`, `"needs_receipt"`,
  `"rejected"`, or `"paid"` when the paid bill doesn't match the current batch).
  Exception: a claim marked `"paid"` that has a cleared bill+payment matching the
  batch goes to paid, not blocked.
- The linked AP bill has status `"void"`.
- Bill amount does NOT match the claim amount (even if both are positive).
- No AP bill exists for the claim (empty bill query result).
- Claim has `"receipt_status": "partial"` combined with policy flags like
  `"over_limit"` — this indicates incomplete documentation.
- Policy flag `"over_limit"` alone may block depending on the batch context.

**CRM-required** (`crm_required_claim_ids`):
A subset of blocked claims that require expense-case owner cleanup or AP-link
remediation. These typically involve:
- Receipt/documentation issues (`"receipt_status": "partial"`)
- Policy violations (`"over_limit"`, `"duplicate_amount"`)
- Void bills that need re-creation
- Missing AP bill linkage
- Claims where the only linked bill is for a wildly different amount (possible
  cross-claim contamination)

#### Amount Matching Rules

- Compare the claim's `amount` field with the bill's `amount` field.
- Use USD with two-decimal precision (the API returns amounts this way).
- A mismatch > 0.005 USD is considered a mismatch.
- When a claim has multiple bills, prefer the bill whose amount equals the claim
  amount. If none match, the claim is blocked.

#### AP Open Balance

- Sum of bill amounts for **payable** claims only.
- Do NOT include blocked or paid claims in the total.
- Report in USD with two decimals.

#### Batch Status

The batch status cascades:
1. `"blocked"` — at least one claim is blocked.
2. `"open_payables"` — no blocked claims, but at least one payable claim exists.
3. `"ready_to_close"` — all claims are paid (no blocked, no payable).

#### Reviewed Claim Count

Count all claim IDs provided in the batch, regardless of status.

### Source Precedence

1. **Current API data is the system of record.** Always query claims, bills,
   and payments fresh from the API.
2. When a stale snapshot (CSV) is provided as context, treat it as **background
   only**. Decisions must be based on current API state.
3. Even if the snapshot says a bill is scheduled/approved, check the current
   bill and payment status in the API.

---

## Workflow 2: Vendor Onboarding Finance-Risk Release Control

### Purpose

Determine whether a batch of business entities can be released for vendor access
based on compliance screening, UBO reporting, and risk checks.

### Endpoints Used

`/api/compliance/objects`, `/api/vendors`

### Business Rules

#### UBO (Ultimate Beneficial Owner) Counting

- The **reporting threshold** is **25%** ownership.
- Count **unique UBO names** where any individual `ownership_pct` entry for that
  name is ≥ 25%.
- Aggregate by name: if the same name appears in multiple `ubo_list` entries,
  count the name once if ANY of their entries meets the threshold.
- Example: Samir Bell at 25% and Samir Bell at 10% → 1 reportable UBO (the 25%
  entry triggers it). Samir Bell at 10% only → 0.

#### Hard Stop Flags

Derive from compliance object and vendor data. Return alphabetically sorted.

| Flag                        | Condition                                                          |
|-----------------------------|--------------------------------------------------------------------|
| `bank_closed`               | `bank_account_status` is `"closed"`                                |
| `bank_name_mismatch`        | `bank_account_status` is `"name_mismatch"`                         |
| `confirmed_pep`             | `pep_status` is `"confirmed_pep"`                                  |
| `expired_license`           | `license_expiry` < `as_of_date`                                    |
| `missing_required_documents`| `missing_fields` contains entries like `"license"`, `"beneficial_owner_id"`, `"bank_statement"`, `"website"` |
| `sanctions_confirmed`       | `sanctions_check_status` is `"confirmed_match"`                    |
| `screening_not_run`         | `sanctions_check_status` is `"not_run"` OR `pep_status` is `"not_run"` |
| `shell_company_suspected`   | `shell_company_suspected` is `true`                                |
| `vendor_on_hold`            | Vendor `status` is `"on_hold"` OR `"inactive"`                     |

#### Decision Logic

| Decision               | Criteria                                                                                     |
|------------------------|----------------------------------------------------------------------------------------------|
| `approve`              | No hard stop flags AND `review_status` is `"approved"` or the business appears ready.        |
| `awaiting_information` | Has fixable issues (expired license, missing documents, in-review status) but no critical escalation triggers. |
| `escalate`             | Has critical red flags: `confirmed_pep`, `sanctions_confirmed`, `bank_closed`, `vendor_on_hold`, or `shell_company_suspected`. Multiple moderate issues may also escalate. |

#### Follow-up vs. Escalation

- `follow_up_business_ids`: Businesses with `"awaiting_information"` decisions
  that need additional documents or clarification before approval.
- `escalate` decisions go to a different workflow (compliance escalation), not
  to the follow-up list.

#### Overall Release Readiness

`overall_release_ready` is `true` **only if every** listed business has decision
`"approve"`. A single non-approve decision makes it `false`.

---

## Workflow 3: Prepaid Expense Close Check

### Purpose

Reconcile prepaid invoice schedules against GL ending balances for a specific
close period and set of accounts.

### Endpoints Used

`/api/prepaids/invoices`, `/api/prepaids/gl-balances` (also at `/gl/balances`)

### Calculation Rules

All amounts in USD with two-decimal precision.

#### Monthly Amortization

Use `monthly_amortization` directly from the invoice record. The recognition
method is always `"straight_line"`. The invoice record provides the authoritative
monthly amount — do not recalculate from `original_amount / number_of_months`.

#### Period-Specific Amortization

For month M of the close period:
- **march_amortization** (or the specific month being closed) = `monthly_amortization`
  if the invoice's service period covers that month; otherwise 0.
- An invoice covers month M if `service_start` ≤ last-day-of-month-M AND
  `service_end` ≥ first-day-of-month-M.

#### Cumulative Amortization

`cumulative_amortization_through_march` = `monthly_amortization × N`

where N = number of whole months from `service_start` through the close month
(inclusive). Count the number of month-boundary crossings:
- For an invoice starting Jan 1 with a Mar close: 3 months (Jan, Feb, Mar).
- For an invoice starting Mar 15 with a Mar close: 1 month (March only, partial
  month counts as 1).
- For an invoice ending Mar 31 with a Mar close: full service period, count all
  months from start through March.

**Calculation method**: N = (close_year - start_year) × 12 + (close_month - start_month) + 1,
using calendar months. The closing month always counts once for an active invoice.

#### Schedule Ending Balance

`schedule_ending_balance` = `original_amount` - `cumulative_amortization_through_march`

#### GL Balance

Query `/api/prepaids/gl-balances` for the target entity, account, and period
(e.g., `?entity=Aurisic+US&account=1250&period=2025-03`). Use `ending_balance`.

#### Variance

`variance_amount` = `schedule_ending_balance` - `gl_ending_balance`

`variance_flag` = `true` when `|variance_amount| >= variance_threshold_abs`

#### Default/Missing Term Flag

An invoice has `default_missing_term_flag = true` if its `data_quality_flags`
include `"missing_contract_dates"`.

An account has `has_default_missing_term_flag = true` if ANY invoice in that
account's scope has a default/missing term flag.

#### Exception Invoices

An invoice is an exception if ANY of:
- `data_quality_flags` is non-empty
- The invoice's recorded `account` does not match the expected account from the
  scope (applies only when scope defines per-invoice account expectations)
- The invoice has unusual amortization patterns (e.g., zero monthly_amortization)

#### Account Status

For each account in the scope, determine status as the most severe condition present:

| Status                     | Condition                                                                 |
|----------------------------|---------------------------------------------------------------------------|
| `requires_reconciliation`  | Any invoice in the account has `default_missing_term_flag = true`         |
| `variance_review`          | `variance_flag = true` AND no invoice has default/missing term            |
| `reconciled`               | `variance_flag = false` AND no invoice has default/missing term           |

The cascade: `requires_reconciliation` takes priority over `variance_review`,
which takes priority over `reconciled`.

#### Account-Level Rollup

For each account:
- `original_amount_total` = sum of `original_amount` for all scoped invoices in that account
- `march_amortization_total` = sum of `march_amortization` for those invoices
- `cumulative_amortization_through_march` = sum of cumulative amortization
- `schedule_ending_balance` = sum of per-invoice ending balances
- `gl_ending_balance` = GL balance from the balances endpoint for that account/period

---

## Workflow 4: Stale AP Export Reconciliation

### Purpose

Compare a stale AP snapshot (CSV) against current ERP state and determine which
claims can remain in a conference reimbursement batch.

### Endpoints Used

`/api/claims`, `/api/ap/bills`, `/api/ap/payments`, `/api/ap/aging`, `/api/close/logs`

### Source Precedence

1. **Current API state is authoritative.** The stale CSV snapshot is context only.
2. The snapshot's bill IDs, amounts, and statuses are from a prior point in time
   and may be outdated.
3. Payments that have since cleared, bills that have been voided, and claims that
   have changed status all take precedence over snapshot values.

### Business Rules

#### Claim Eligibility

**Eligible** (`eligible_claim_ids`):
- Claim is currently approved, AND
- Has a valid matching AP bill (not void), AND
- No blocking conditions (as defined in Workflow 1).

**Not Ready** (`not_ready_claim_ids`):
- Claim fails any eligibility check (not approved, void bill, amount mismatch,
  no bill, payment issues).

#### AP Balance by Claim

For each candidate claim ID, compute the open AP balance:

`ap_balance` = bill `amount` - sum of payment `amount` where payment status is
`"cleared"` (not just scheduled or processing).

- If the bill has no cleared payment: balance = bill amount.
- If the bill has a cleared payment matching the full amount: balance = 0.
- If the bill is void: balance = 0 (void bills do not represent payable obligations
  in the current state).
- Use only the bill(s) that are valid (non-void) and relevant to the claim.

#### Stale Snapshot Corrections

For each candidate claim, compare the snapshot row against current API state:

| Correction                          | When to Use                                                                                       |
|-------------------------------------|---------------------------------------------------------------------------------------------------|
| `current_snapshot_ok`               | Snapshot correctly reflects the current claim/bill/payment state.                                 |
| `mark_in_flight_payment`            | A payment exists but is not yet `"cleared"` (status is `"processing"` or `"scheduled"`).         |
| `replace_with_matched_paid_bill`    | Snapshot references a stale bill; the API shows a different bill ID with a matching amount that is fully paid. |
| `exclude_amount_or_vendor_mismatch` | Bill amount doesn't match claim amount OR vendor mismatch between claim and bill.                 |
| `ignore_void_bill`                  | The bill linked in the snapshot is now `"void"`.                                                  |
| `block_unapproved_claim`            | Claim status is not `"approved"` (e.g., `"needs_receipt"`, `"submitted"`, `"rejected"`).         |

#### Close Log Requirements

- Query close logs for the relevant period and area (typically Expense area).
- `close_log_required.required` is `true` if there are open or ready_for_review
  close log entries that relate to the batch.
- `close_log_required.ids` lists the relevant log IDs, sorted ascending.

#### Batch Status

| Status            | Condition                                                                                   |
|-------------------|---------------------------------------------------------------------------------------------|
| `ready_to_send`   | All candidate claims are eligible and have matching bills+payments settled.                 |
| `needs_ap_refresh`| Some claims are payable (awaiting payment) but none are blocked.                            |
| `blocked`         | At least one candidate claim is blocked/not-ready.                                          |

---

## Workflow 5: AP Payment Release After Account-Change Events

### Purpose

Review a batch of business IDs with vendor account-change events and determine
whether payments can be released, held, or escalated.

### Endpoints Used

`/api/compliance/objects`, `/api/vendors`

### Business Rules

#### Decision Framework

Each business receives one of: `"release"`, `"hold"`, `"escalate"`.

**Escalate** — ANY of these critical triggers:
- `sanctions_check_status` is `"confirmed_match"`
- `pep_status` is `"confirmed_pep"`
- `bank_account_status` is `"closed"`
- Vendor `status` is `"on_hold"` or `"inactive"`
- `shell_company_suspected` is `true`
- `sanctions_check_status` is `"not_run"` (unverified screening is an escalate
  in a payment-release context)

**Hold** — NO escalate triggers, but ANY of:
- `bank_account_status` is `"name_mismatch"` (bank mismatch)
- `license_expiry` < `review_date` (expired license)
- `tax_id` in the compliance record does not match the vendor's `tax_id`
- `tax_id` has an invalid format (non-numeric characters like `"X"`, sentinel
  values like all-9s or all-1s)
- `review_status` is `"not_started"`, `"awaiting_information"`, or `"in_review"`
- `pep_status` is `"possible_pep"` (needs verification)

**Release** — ALL of:
- No escalate triggers
- No hold triggers
- Bank verified, license valid, sanctions clear, PEP clear, vendor active,
  tax ID valid and matching, review complete

#### Bank Mismatch Detection

`bank_mismatch_ids`: Business IDs where `compliance.bank_account_status == "name_mismatch"`.

Also cross-check: if the batch specifies a `requested_bank_last4`, compare it
against the vendor's `bank_account_last4`. A mismatch between requested and
vendor bank last 4 is additional evidence but pre-existing `name_mismatch`
status is definitive.

#### Tax ID Validation

A tax ID is invalid if:
- It does not match the vendor record's `tax_id` (cross-reference via
  `compliance.vendor_id → vendor.tax_id`)
- Its format is non-standard (contains letters like `"X"`, is a sentinel like
  `"TIN999999"`, `"TIN111111"`, or `"TIN000000"`)

#### Expired License Detection

`expired_license_ids`: Business IDs where `license_expiry < as_of_date` (review date).
Compare as dates, not strings.

#### Review Queue

`review_queue_ids`: Business IDs where compliance/AP review is still needed:
- `review_status` is NOT `"approved"`
- OR has any hold-level issue that needs human review before release
- Businesses that are escalated are NOT in the review queue (they go to a
  different escalation queue).

#### Risk Score Override

`risk_score_override_flags`: Business IDs where `risk_score >= 70`.
These require additional approval regardless of other checks.

---

## Output Conventions (All Workflows)

### Sorting

- Claim ID lists: **ascending** alphanumeric by claim ID string.
- Business ID lists: **ascending** by business ID string.
- Invoice ID lists in prepaid: preserve the **same order** as the input scope file
  (for `invoice_results` and `selected_invoice_ids`).
- Aggregated lists (exceptions, defaults): **ascending** by ID string.
- Close log IDs: **ascending** by log ID.
- Hard stop flags: **alphabetical** by the enum value string.

### Currency

- All amounts in **USD**.
- Report with **two decimal places** (e.g., `1842.36`, not `1842.4` or `1842`).
- Use the amounts as returned by the API (no rounding beyond what the API provides).

### JSON Structure

- Always match the provided `answer_template.json` exactly in key names,
  nesting, and types.
- Do not add extra keys beyond what the template specifies.
- Empty lists use `[]`, not `null`.
- Boolean fields use `true`/`false`, not strings.

### Claim ID Format Notes

Claims may use either a numeric or alphabetic suffix:
- `CLM-2025-NNNN` — standard format (e.g., `CLM-2025-0080`)
- `CLM-2025-OPS-NNN` — departmental format (e.g., `CLM-2025-OPS-017`)
- `CLM-2025-FIN-NNN` — departmental format (e.g., `CLM-2025-FIN-042`)

All are valid claim IDs. Sort them as strings (lexicographic).

---

## Common Pitfalls

### Claim-Bill Amount Mismatch

A bill can link to a claim (`claim_id` field) but have a completely different
amount. This indicates either a data error, a cross-claim contamination, or a
consolidated bill. Always compare claim.amount to bill.amount. A mismatch is
a blocking condition for release workflows.

### Multiple Bills Per Claim

A single claim may have multiple AP bills. This can happen when:
- An old bill was imported from a legacy system and a corrected bill was created
- A void bill coexists with an active bill
- Different departments created bills for the same claim

Always check ALL bills for a claim and use the one whose amount matches. If
multiple bills match the claim amount, prefer the non-void, most recently dated
one that is paid or scheduled.

### Payment Status vs. Aging Balance

The `/api/ap/aging` endpoint may show `balance = 0` even when payments are only
`"scheduled"` or `"processing"`. For claim settlement classification, only
`"cleared"` payments count as fully settled. Use the `/api/ap/payments` endpoint
to determine actual payment status, not the aging endpoint's computed balance.

### Void Bills

A void bill (`status: "void"`) is not a valid payable obligation. It should be:
- Excluded from AP open balance calculations
- Treated as a blocking condition for the linked claim (the claim needs a new,
  valid bill)
- Flagged as `"ignore_void_bill"` in snapshot corrections

### Claim Status vs. Bill Status

A claim with status `"approved"` may have a bill with status `"paid"` if another
process settled it. Conversely, a claim with status `"paid"` does NOT guarantee
the bill is settled — always verify through payments.

The claim status `"paid"` generally indicates the expense case is closed, but
the AP bill and payment status are the definitive sources for financial settlement.

### Shared Bill IDs

The bill ID `AP-2025-0068` appears twice in the system with different claim
linkages and amounts. This can happen when a bill ID is reused across systems.
When querying by bill_id, always check which result row has the relevant
claim_id and amount.

### GL Balance Period Matching

When querying GL balances, match on the exact period string (e.g., `"2025-03"`)
AND the entity (e.g., `"Aurisic US"`). The balances endpoint may return rows for
multiple entities, accounts, and periods — filter to only the requested scope.

### Partial-Month Amortization

For invoices starting mid-month (e.g., `service_start: "2025-03-15"`), the
closing month (March) still counts as one full month of amortization for
cumulative calculations. The `monthly_amortization` is the full month amount;
there is no pro-rating for partial months.

### Tax ID Cross-Validation

Tax ID validation requires cross-referencing the compliance object against the
vendor master. The compliance record's `tax_id` must match the vendor's `tax_id`.
Even if both look valid individually, a mismatch is a blocking issue.

### UBO Deduplication

UBO names may appear multiple times in `ubo_list` with different ownership
percentages. Count each unique name once if ANY entry for that name meets the
25% threshold. Do NOT sum ownership percentages across entries — evaluate each
entry independently against the threshold.

### Expired License Date Comparison

Compare `license_expiry` against `as_of_date` (or `review_date`) using date
comparison, not string comparison. A license expiring on the same day as the
review date is NOT expired (expiry ≥ review_date means valid).

### Close Log Status Propagation

Close log entries with `status: "ready_for_review"` or `"open"` indicate
unresolved issues. These should trigger `close_log_required: true` and the
relevant log IDs should be listed.

### Review Status Interpretation

- `"approved"` — cleared for release
- `"in_review"` — under active review; typically a `"hold"` decision
- `"awaiting_information"` — waiting for documents; typically `"hold"` or
  `"awaiting_information"` in onboarding
- `"not_started"` — review hasn't begun; `"hold"` in payment release
- `"escalated"` — already escalated; may require `"escalate"` decision

### Policy Flags and Receipt Status

For expense claims:
- `policy_flags: ["over_limit"]` — amount exceeds policy limit; may block release
- `policy_flags: ["duplicate_amount"]` — possible duplicate; investigate before release
- `policy_flags: ["late_receipt"]` — receipt submitted after deadline
- `receipt_status: "partial"` — incomplete documentation; blocking if combined
  with other flags
- `receipt_status: "attached"` — complete documentation

---

## Workflow Quick Reference

| Workflow                     | Key Decision Fields          | Primary Endpoints                              | Special Rules                                      |
|------------------------------|------------------------------|------------------------------------------------|----------------------------------------------------|
| 1. Reimbursement Close       | payable/blocked/paid IDs     | claims, bills, payments, close-logs            | Amount matching, bill-payment cascading            |
| 2. Vendor Onboarding         | per_business decision, flags | compliance, vendors                            | UBO 25% threshold, hard stop detection             |
| 3. Prepaid Close             | account status, variance     | prepaids/invoices, prepaids/gl-balances        | Cumulative amortization, variance threshold        |
| 4. Stale AP Reconciliation   | eligible/not_ready, balances | claims, bills, payments, aging, close-logs     | Snapshot correction, current state as authority    |
| 5. Account-Change Release    | release/hold/escalate        | compliance, vendors                            | Tax ID cross-validation, risk score override       |
