# Finance Review Workflows

## 1. Claims Reimbursement Close

**When the prompt asks** to decide close status for a batch of expense claims (e.g., "reimbursement-to-AP close review" with claim IDs and an answer_template with fields like `payable_claim_ids`, `blocked_claim_ids`, `paid_claim_ids`, `ap_open_balance_total`, `crm_required_claim_ids`, `batch_status`, `reviewed_claim_count`).

### Steps

1. Fetch claims for every claim ID in the batch via `/api/claims?claim_id=...&claim_id=...`.
2. Fetch all bills linked to those claim IDs via `/api/ap/bills?claim_id=...&claim_id=...`.
3. Fetch all payments for the returned bill IDs via `/api/ap/payments?bill_id=...&bill_id=...`.
4. For each claim, classify:

   **Paid**: claim `status == "paid"` AND there is a bill for the claim with `status == "paid"` AND a payment for that bill with `status == "cleared"` AND the payment amount matches the bill amount.
   - Note: a single claim may have multiple bills (e.g., a paid bill and a scheduled bill). Use the paid bill for the "paid" classification; the scheduled bill is ignored for that purpose.

   **Blocked**: any claim that is NOT paid and meets any of:
   - No bill linked to the claim in the API (no bill with matching `claim_id`).
   - Bill exists but `status == "void"`.
   - Bill amount does not match the claim amount (mismatch).
   - Bill's vendor does not match the claim's vendor (mismatch).
   - Claim `status` is not `"approved"` or `"paid"` (e.g., `needs_receipt`, `rejected`, `submitted`).
   - Claim has `receipt_status == "partial"` or `"missing"` with no cleared payment.
   - Bill has `status == "approved"` with `memo` containing "Duplicate check required" — this indicates a potential duplicate that needs investigation.

   **Payable**: claim is NOT paid and NOT blocked. It has `status == "approved"`, a matching bill with `status` of `"scheduled"` or `"approved"`, and no blocking conditions.

5. **CRM-required claims** (`crm_required_claim_ids`): subset of blocked claims where the issue is claim-level (claim status not approved, partial receipts, no bill, vendor mismatch, amount mismatch) rather than purely a payment/bill status issue. In practice, this is all blocked claims unless a claim is blocked solely because its bill is `"approved"` with a duplicate memo — those are AP-sourcing issues, not CRM issues.

6. **AP open balance total** (`ap_open_balance_total`): sum of bill amounts for payable claims where the bill `status` is `"scheduled"` or `"approved"` (not `"paid"` or `"void"`).

7. **Batch status**:
   - `"blocked"` if any claim in the batch is blocked.
   - `"open_payables"` if any payable claims remain (and none blocked).
   - `"ready_to_close"` if all claims are paid.

8. Sort all claim ID lists ascending. Set `reviewed_claim_count` to the count of claim IDs in the batch.

---

## 2. Vendor Onboarding Compliance

**When the prompt asks** to perform an onboarding release call for vendor access with business IDs and an answer template with fields like `per_business`, `reportable_ubo_counts`, `hard_stop_flags`, `follow_up_business_ids`, `overall_release_ready`.

### Steps

1. Fetch compliance objects for all business IDs via `/api/compliance/objects?business_id=...&business_id=...`. This merged endpoint provides all compliance fields including `ubo_list`, `bank_account_status`, `pep_status`, `sanctions_check_status`, `shell_company_suspected`, `license_expiry`, `missing_fields`.

2. For vendors linked to business IDs, fetch vendor data via `/api/vendors?vendor_id=...` to check `status` (for `vendor_on_hold` flag).

3. For each business, compute:

   **reportable_ubo_counts**: Count of unique UBO **names** where any ownership record for that name has `ownership_pct >= 25`. A name appearing multiple times at different percentages counts once if at least one record meets the 25% threshold.

   **hard_stop_flags**: Derived per the rules in [api-guide.md](api-guide.md). Sort alphabetically. Empty list if none.

   **decision**: Per the onboarding decision table in [api-guide.md](api-guide.md).

4. **follow_up_business_ids**: all business IDs where `decision != "approve"`.

5. **overall_release_ready**: `true` only if every business has `decision == "approve"`.

6. Sort all ID lists ascending by `business_id`.

---

## 3. Prepaid Close Reconciliation

**When the prompt asks** to prepare a prepaid close check for a specific entity and period with a list of invoice IDs and account codes, and an answer template with fields like `account_rollup`, `invoice_results`, `default_missing_term_invoice_ids`, `exception_invoice_ids`.

### Steps

1. Fetch prepaid invoices for the scoped invoice IDs via `/api/prepaids/invoices?prepaid_invoice_id=...&prepaid_invoice_id=...`.

2. Fetch GL balances for the scoped accounts and period via `/api/prepaids/gl-balances?account=...&account=...&period=YYYY-MM`.

3. For each invoice, compute as described in [api-guide.md](api-guide.md):
   - **march_amortization**: `monthly_amortization` field value.
   - **cumulative_amortization_through_march**: `monthly_amortization * N` where N = months from `service_start` through the close month (inclusive count).
   - **ending_balance**: `original_amount - cumulative_amortization_through_march`. Floor at 0.00 if negative.
   - **default_missing_term_flag**: `true` if `data_quality_flags` contains `missing_contract_dates`.
   - **exception_flag**: `true` if `data_quality_flags` is non-empty.

4. Aggregate per account:
   - **original_amount_total**: sum of `original_amount` for all invoices in the account.
   - **march_amortization_total**: sum of `monthly_amortization` for all invoices in the account.
   - **cumulative_amortization_through_march**: sum of per-invoice cumulative amortizations.
   - **schedule_ending_balance**: `original_amount_total - cumulative_amortization_through_march`.
   - **variance_amount**: `schedule_ending_balance - gl_ending_balance`.
   - **variance_flag**: per [api-guide.md](api-guide.md).
   - **has_default_missing_term_flag**: per [api-guide.md](api-guide.md).
   - **account_status**: per [api-guide.md](api-guide.md).

5. **default_missing_term_invoice_ids**: invoice IDs where `default_missing_term_flag == true`, sorted ascending.

6. **exception_invoice_ids**: invoice IDs where `exception_flag == true`, sorted ascending.

7. Preserve the invoice order from the scope file for `selected_invoice_ids` and `invoice_results`.

---

## 4. Stale AP Batch Refresh

**When the prompt asks** to review a stale AP export snapshot against current ERP data, with candidate claim IDs and an answer template with fields like `eligible_claim_ids`, `not_ready_claim_ids`, `ap_balance_by_claim`, `stale_snapshot_corrections`, `close_log_required`, `batch_status`.

### Steps

1. Fetch current claims for all candidate IDs via `/api/claims?claim_id=...`.

2. Fetch current bills for all candidate claim IDs via `/api/ap/bills?claim_id=...`.

3. Fetch current payments for all returned bill IDs via `/api/ap/payments?bill_id=...`.

4. Fetch close logs via `/api/close/logs` (filter by relevant claim IDs, areas "AP" or "Expense").

5. For each claim, compare the snapshot CSV row against current API data:

   **Snapshot correction codes** (pick exactly one per claim):

   - `current_snapshot_ok`: snapshot matches current API state for bill status, payment status, and amounts.
   - `mark_in_flight_payment`: snapshot shows no payment but current API shows a payment in `processing` or `scheduled` status for the bill.
   - `replace_with_matched_paid_bill`: snapshot bill is `scheduled` but current API shows the bill is `paid` with a `cleared` payment matching the final paid amount.
   - `exclude_amount_or_vendor_mismatch`: current bill amount does not match the claim amount, OR bill vendor does not match claim vendor, OR bill memo indicates a problem.
   - `ignore_void_bill`: current API shows the bill is `void`.
   - `block_unapproved_claim`: current claim `status` is not `"approved"` or `"paid"` (e.g., `needs_receipt`, `submitted`, `rejected`).

6. **eligible_claim_ids**: claims with correction `current_snapshot_ok` or `mark_in_flight_payment` (snapshot is stale but the underlying data is fine and payments are in flight) AND claim status is `approved` or `paid`.

7. **not_ready_claim_ids**: all other claims.

8. **ap_balance_by_claim**: open AP balance per claim. For `void` bills, the balance is 0.00. For paid bills, balance is 0.00. For scheduled/approved bills, balance is the bill amount minus any cleared payment amount. Two decimals.

9. **close_log_required**: check if any relevant close log exists with `status == "ready_for_review"`. If so, `required: true` and include those log IDs in `ids` (sorted ascending).

10. **batch_status**:
    - `"ready_to_send"`: all claims are eligible and no close log is ready_for_review.
    - `"needs_ap_refresh"`: some claims are not ready due to stale data or corrections needed but none are blocked at the claim level.
    - `"blocked"`: any claim has `block_unapproved_claim` or `ignore_void_bill` correction.

---

## 5. Account-Change Payment Release

**When the prompt asks** to review an AP payment release batch after vendor account-change events, with business IDs and account-change tickets, and an answer template with fields like `decisions`, `bank_mismatch_ids`, `invalid_tax_ids`, `expired_license_ids`, `review_queue_ids`, `risk_score_override_flags`.

### Steps

1. Fetch compliance objects for all target business IDs via `/api/compliance/objects?business_id=...`.

2. Fetch vendor data for all vendors linked to the business IDs via `/api/vendors?vendor_id=...`.

3. For each business, apply the account-change decision logic from [api-guide.md](api-guide.md).

4. Derive the per-business lists:
   - `bank_mismatch_ids`: per [api-guide.md](api-guide.md)
   - `invalid_tax_ids`: per [api-guide.md](api-guide.md)
   - `expired_license_ids`: per [api-guide.md](api-guide.md)
   - `review_queue_ids`: per [api-guide.md](api-guide.md)
   - `risk_score_override_flags`: per [api-guide.md](api-guide.md)

5. Sort all ID lists ascending by business ID.

6. Fill the fixed fields (`task_id`, `batch_id`, `as_of_date`, `target_business_ids`) from the input payload exactly as provided.
