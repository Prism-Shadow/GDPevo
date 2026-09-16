# Decision Frameworks by Task Subtype

Each section below describes the classification logic for one family of
finance-close task. These rules are derived from the known task types in the
ERP environment. The exact field names and enum values depend on the current
answer template -- always cross-check the template before writing output.

## Claims close / reimbursement-AP

**When the prompt asks for close status of a batch of claim IDs**, you are
reconciling expense claims against AP bills and payments.

### Data to fetch

For every claim_id in the batch:
1. Fetch the claim record from `/api/claims`.
2. If the claim has a `bill_id`, fetch the bill from `/api/ap/bills`.
3. If the bill exists and has a payment linkage, fetch the payment from
   `/api/ap/payments`.

The prompt may also reference close logs -- fetch `/api/close/logs` filtered
to the relevant claims if the template requires it.

### Classification

Assign each claim_id to exactly one of these buckets:

- **paid**: The claim has a linked bill whose `status` is `paid`, AND there is
  a payment record with `status` `cleared` and an amount matching the claim
  amount. The payment must be for the full claim amount; partial payments do
  not settle the claim.

- **payable**: The claim `status` is `approved`, the linked bill `status` is
  `scheduled` or `approved`, and no cleared payment exists. The claim is
  waiting for AP release. Sum the `bill.amount` for all payable claims to
  produce `ap_open_balance_total`.

- **blocked**: The claim falls into any of these conditions:
  * Claim `status` is not `approved` (e.g., `voided`, `draft`, `rejected`).
  * The linked bill `status` is `voided`.
  * A payment exists but is uncleared (status `scheduled` or `none`) with an
    amount that doesn't match the claim.

Within blocked claims, distinguish:
- **CRM-required** (`crm_required_claim_ids`): Blocked claims where the
  underlying issue is with the expense case itself (unapproved claim, voided
  claim, missing bill) rather than a downstream AP/payment problem. These
  need owner cleanup before AP release.
- The remaining blocked claims have AP/payment evidence issues.

### Batch status

- `blocked`: any claim in the batch is blocked.
- `open_payables`: no blocked claims, but at least one payable claim exists.
- `ready_to_close`: every claim is paid or the batch is fully settled.

---

## Vendor onboarding risk

**When the prompt asks for a release call on a vendor access batch**, you are
checking whether each business can be released for vendor access.

### Data to fetch

For every `business_id` in the batch:
1. Fetch the vendor record from `/api/vendors` (filter by `business_id`).
2. Fetch `/api/compliance/ownership/{business_id}` for UBO information.
3. Fetch `/api/compliance/registry/{business_id}` for registration/license.
4. Fetch `/api/compliance/screening/{business_id}` for PEP/sanctions/risk.
5. Fetch `/api/compliance/bank/{business_id}` for bank account status.

### UBO counting

Count `reportable_ubo_counts` per business_id as the number of unique
beneficial-owner names whose ownership percentage is at or above the
reporting threshold. The threshold is 25% by default; use a different
threshold only if the prompt or template explicitly states one.

### Hard-stop flags

Check each condition below. When the condition is met, add the corresponding
enum value to that business's `hard_stop_flags` list. Sort flags
alphabetically.

| Condition | Flag |
|-----------|------|
| Compliance bank status is `closed` | `bank_closed` |
| Compliance bank status is `name_mismatch` | `bank_name_mismatch` |
| Screening returns a confirmed PEP match | `confirmed_pep` |
| Registry license expiry is before the review date (or `as_of_date`) | `expired_license` |
| Registry shows missing required documents | `missing_required_documents` |
| Screening confirms sanctions hit | `sanctions_confirmed` |
| Screening status is `not_run` or missing | `screening_not_run` |
| Screening flags shell-company indicators | `shell_company_suspected` |
| Vendor status is `on_hold` | `vendor_on_hold` |

### Decision per business

- **approve**: No hard stops triggered, all required documents present,
  screening completed without hits, bank is active.
- **awaiting_information**: Some checks are incomplete (e.g., screening not
  run, missing documents) but no definitive blocking signals exist. The
  business needs more evidence before release.
- **escalate**: Any hard-stop flag applies that requires manual intervention
  (PEP, sanctions, closed bank, expired license, shell company, vendor on
  hold).

### Batch-level fields

- `follow_up_business_ids`: every business_id that did not get `approve`,
  sorted ascending.
- `overall_release_ready`: `true` only if every business in the batch got
  `approve`.

---

## Prepaid close reconciliation

**When the prompt asks for a prepaid close check for specific accounts and
invoices**, you are reconciling prepaid amortization schedules against GL
balances.

### Data to fetch

1. Fetch every prepaid invoice listed in the scope file from
   `/api/prepaids/invoices` (one at a time or by filtering `?prepaid_invoice_id=`).
2. Fetch GL ending balances from `/api/prepaids/gl-balances` (or `/gl/balances`)
   for each account and the close period.

### Per-invoice calculations

For each invoice:
- `march_amortization`: the `monthly_amortization` value from the invoice
  record for the close-period month. If the invoice record provides a single
  monthly amortization figure rather than per-month values, that figure is the
  amortization for every month including the close period.
- `cumulative_amortization_through_march`: sum of monthly amortizations from
  the invoice start month through the close-period month. For a straight-line
  schedule, this is `monthly_amortization * months_elapsed` where
  `months_elapsed` is the number of months from the start month to (and
  including) the close-period month, capped at `amortization_term_months`.
- `ending_balance`: `original_amount - cumulative_amortization_through_march`.
  This can be zero; it should never be negative unless the data is anomalous
  (flag it as an exception if it is).

### Default/missing term detection

An invoice has `default_missing_term_flag: true` when:
- `amortization_term_months` is 0, null, or absent from the invoice record.

### Exception detection

An invoice has `exception_flag: true` when:
- `amortization_term_months` is 0/null/absent (overlaps with default flag).
- `ending_balance` is negative.
- `monthly_amortization * amortization_term_months` exceeds `original_amount`.
- The cumulative amortization has already fully consumed the original amount
  before the close period (invoices that finished amortizing in prior periods
  may still appear with a zero ending balance).

### Account rollup

For each account:
1. Sum per-invoice fields across all invoices in that account: `original_amount_total`,
   `march_amortization_total`, `cumulative_amortization_through_march`,
   `schedule_ending_balance`.
2. `gl_ending_balance`: the fetched GL balance for that account for the period.
3. `variance_amount`: `schedule_ending_balance - gl_ending_balance`.
4. `variance_flag`: `true` when `|variance_amount| > variance_threshold_abs`
   (default 100.00 unless the template or scope file specifies otherwise).
5. `has_default_missing_term_flag`: `true` when any invoice in the account has
   `default_missing_term_flag: true`.
6. `account_status`:
   - `reconciled`: no variance flag, no default/missing term flag.
   - `variance_review`: variance flag is true but no default/missing term issues
     and no per-invoice exceptions.
   - `requires_reconciliation`: variance flag is true AND either a
     default/missing term flag or per-invoice exceptions exist.

---

## Stale AP snapshot cleanup

**When the prompt gives you a stale AP export (CSV or JSON snapshot) and asks
you to reconcile it against the live API**, you are determining which rows are
still accurate and which need correction.

### Data to fetch

For every claim_id in the batch:
1. Fetch the current claim from `/api/claims`.
2. Fetch the current AP bill from `/api/ap/bills`.
3. Fetch any payments from `/api/ap/payments`.
4. Check `/api/close/logs` for prior close activity on these claims if the
   template includes `close_log_required`.

### Stale snapshot correction categories

Compare each snapshot row against live API data and assign exactly one
category per claim_id:

| Category | When to use |
|----------|-------------|
| `current_snapshot_ok` | Snapshot and live data agree on claim status, bill ID, bill status, bill amount, payment status, and payment amount. No correction needed. |
| `mark_in_flight_payment` | The claim and bill are correctly recorded in the snapshot, but the payment status has changed (e.g., snapshot says `none`/`scheduled` but live API shows no cleared payment yet, or a payment is pending). The AP balance should reflect the current open amount. |
| `replace_with_matched_paid_bill` | The snapshot bill_id is wrong or refers to a different bill than the one actually linked in the live API; the live bill is `paid` with a cleared payment. Replace the snapshot row with the live data. |
| `exclude_amount_or_vendor_mismatch` | The live bill amount differs materially from the snapshot amount, or the vendor/entity on the bill does not match expectations. The claim should be removed from the batch. |
| `ignore_void_bill` | The live bill `status` is `voided`. The claim is not payable through this bill. |
| `block_unapproved_claim` | The live claim `status` is not `approved` (e.g., `voided`, `draft`). The claim cannot proceed to AP. |

### AP balance by claim

`ap_balance_by_claim` reflects the open AP balance after applying cleared
payments. For a claim with a linked bill:
- If the bill is paid with a cleared payment matching the bill amount, the
  balance is 0.00.
- If the bill is scheduled/approved with no payment, the balance is the bill
  amount.
- If the bill is voided or the claim is unapproved, the balance is 0.00
  (nothing is payable).

### Batch status

- `ready_to_send`: every claim in the batch is eligible and no stale
  corrections are needed beyond `current_snapshot_ok`.
- `needs_ap_refresh`: some claims are eligible but at least one stale row
  needs correction; the batch can be updated and sent.
- `blocked`: at least one claim is not ready (unapproved claim, voided bill,
  or amount/vendor mismatch) requiring owner intervention.

### Close log check

When the template includes `close_log_required`:
- Query `/api/close/logs` filtered by claim_id.
- `required: true` when: at least one stale row needs a category other than
  `current_snapshot_ok`, AND no existing close log entry covers the correction.
- `ids`: list any existing close log IDs that reference the corrected claims,
  sorted ascending.

---

## Account-change payment release

**When the prompt asks for a payment-release review after vendor account-change
events**, you are checking each business_id against vendor and compliance
records to decide whether the payment can be released.

### Data to fetch

For every `business_id` in the batch:
1. Fetch the vendor record from `/api/vendors` (filter by `business_id`).
   Pay attention to: vendor `status`, `tax_id` validity, `risk_score`, bank
   account last-4.
2. Fetch `/api/compliance/bank/{business_id}` for bank account status.
3. Fetch `/api/compliance/registry/{business_id}` for license expiry.
4. Fetch `/api/compliance/screening/{business_id}` for risk indicators.
5. Fetch `/api/compliance/ownership/{business_id}` only if the template
   requires UBO data (rare in this subtype but possible).

### Decision per business

- **release**: Vendor is active, bank account matches and is active, tax ID is
  valid, license is not expired, risk score is below the override threshold
  (70), and no compliance screening issues exist.
- **hold**: A non-critical issue exists that should block payment until
  resolved. Examples: bank name mismatch (the requested bank last-4 differs
  from the compliance bank record), screening was not run, license is expired,
  risk score is at or above 70.
- **escalate**: A critical blocking signal exists: bank is closed, sanctions
  confirmed, vendor is on hold, or multiple hold conditions stack up. These
  need manual compliance review.

### Flag lists

- **bank_mismatch_ids**: Business IDs where compliance bank status is
  `name_mismatch`, OR where the account-change ticket's `requested_bank_last4`
  does not match the bank last-4 from the compliance bank endpoint.
- **invalid_tax_ids**: Business IDs where the vendor record shows an invalid,
  missing, or expired tax ID.
- **expired_license_ids**: Business IDs where the compliance registry license
  expiry date is before the review date (`as_of_date`).
- **review_queue_ids**: All business IDs that did not get `release`. These
  need compliance or AP review before the payment can go out.
- **risk_score_override_flags**: Business IDs where `risk_score >= 70`.
