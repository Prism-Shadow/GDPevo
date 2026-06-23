---
name: task-group-005-erp-finance-control
description: Solve task_group_005 ERP finance-control evaluations by reconciling current API data for reimbursement AP close, vendor onboarding/account-change release, prepaid close, and stale AP snapshots.
---

# Task Group 005 ERP Finance Control

Use this skill when a task asks for JSON decisions from the task_group_005 ERP finance API. The recurring pattern is: local files define the scope and answer schema, while the API is the system of record.

## Ground Rules

- Read the prompt, local scope/batch payload, and `answer_template.json` first. Build the answer shape from the template, not from memory.
- Use the runner-provided API base URL when present. Otherwise use the task group's environment access base URL or local `<environment_base_url>` if the runner says it is active.
- Use only documented API endpoints. Do not inspect local environment source or data directories.
- Treat local CSV exports as stale context unless the prompt explicitly says otherwise. Current API records override stale snapshots.
- API list endpoints return `{count,data,total,...}` and support exact-match query params, `limit`, and `offset`. Paginate if `total > count`.
- Return JSON only when requested. Do not add narrative, comments, markdown fences, or extra keys.
- Obey each schema's ordering and units exactly: some reimbursement totals are integer USD cents, while other templates require USD numbers with two decimals.

## Useful Endpoints

- Claims: `GET /api/claims/{claim_id}` or `/claims`; bills: `/api/ap/bills?claim_id=...`; payments: `/api/ap/payments?bill_id=...`.
- Close logs: `/api/close/logs` with exact filters such as `area`, `status`, `period`, or `related_account`.
- Vendors: `/api/vendors?vendor_id=...`. Vendor lookup is keyed by `vendor_id`, not `business_id`.
- Compliance: `/api/compliance/profile/{business_id}`, `/ownership/{business_id}`, `/registry/{business_id}`, `/screening/{business_id}`, `/bank/{business_id}`, `/risk/{business_id}`. `/api/compliance/objects` is useful for broad inspection but can be large.
- Prepaids: `/api/prepaids/invoices?prepaid_invoice_id=...` and `/api/prepaids/gl-balances?entity=...&period=...&account=...`.

## Reimbursement and AP Close

For each scoped claim ID:

1. Fetch the claim, all AP bills with matching `claim_id`, and payments for each bill.
2. A valid reimbursement AP bill should match the claim amount, currency, and vendor when the claim has a vendor, and it must not be `void`. A bill with the same `claim_id` but mismatched amount or vendor is AP evidence of a problem, not proof that the claim is payable.
3. A settled claim needs a matching paid bill and cleared payment evidence for the same amount/vendor. Scheduled or processing payments are not cleared.
4. Open AP balance is based on valid non-void bills less cleared payments only. Ignore void bills and stale export rows.
5. Separate expense-case cleanup from AP/payment evidence issues:
   - Expense/CRM cleanup: non-approved claim status, missing owner/vendor where needed, partial/missing support, or policy/receipt issues that block release.
   - AP/payment cleanup: missing bill, void bill, amount/vendor mismatch, stale bill reference, non-cleared payment, or duplicate/mismatched AP row.
6. Overall status normally follows the template logic: any blocked item makes the batch blocked; otherwise open valid unpaid bills mean open payables/needs refresh; otherwise the batch is ready/closed.

For stale AP snapshot tasks, classify each snapshot row by current API evidence:

- `current_snapshot_ok`: current claim/bill/payment state still matches the snapshot and remains eligible.
- `mark_in_flight_payment`: a valid bill has a scheduled or processing payment that is not cleared.
- `replace_with_matched_paid_bill`: the stale row points to the wrong AP evidence, but the API has a correct paid bill and cleared payment.
- `exclude_amount_or_vendor_mismatch`: current AP evidence does not match the claim amount/vendor.
- `ignore_void_bill`: the stale row is void or the only linked AP bill is void.
- `block_unapproved_claim`: the current claim itself is not releasable.

For `close_log_required`, include unresolved logs only when they are relevant to the batch issue. Use `open` or `ready_for_review` statuses, the relevant AP/Expense/Treasury area, matching period/account/message context, and sort log IDs ascending.

## Vendor Onboarding and Account-Change Release

For each scoped `business_id`, gather all current evidence:

- `profile`: business name, missing fields, registry/tax identity, `vendor_id`.
- `ownership`: UBO list, ownership layers, shell-company indicator.
- `registry`: license expiry and registered tax ID.
- `screening`: sanctions and PEP statuses.
- `bank`: bank-account status.
- `risk`: risk score and review status.
- `vendor`: active/on-hold status, bank last4, and vendor tax ID by `vendor_id`.

Do not copy `review_status` as the decision. Use it as context; concrete control evidence decides release posture.

Hard-stop and review conventions:

- `bank_closed`: bank status is `closed`.
- `bank_name_mismatch`: bank status is `name_mismatch`.
- `vendor_on_hold`: vendor status is `on_hold`.
- `expired_license`: registry license expiry is before the task's as-of/review date.
- `missing_required_documents`: `missing_fields` is non-empty.
- `screening_not_run`: sanctions or PEP screening says `not_run`.
- `sanctions_confirmed`: sanctions status is a confirmed match.
- `confirmed_pep`: PEP status is confirmed.
- `shell_company_suspected`: ownership record says shell company is suspected.
- `invalid_tax_ids`: vendor tax ID and registry/profile tax ID disagree, are malformed, or otherwise fail the task's tax rule.
- `risk_score_override_flags`: risk score is at or above the template threshold, commonly `>= 70`.

For UBO counts, group owners by name, aggregate/de-duplicate ownership evidence, and count unique names at or above the reporting threshold. Use 25% unless the prompt gives another threshold. Do not count the same owner twice.

Decision posture:

- Approve/release only when vendor is active, bank is verified and matches any requested last4, tax IDs reconcile, license is current, required docs are present, screening is clear, no shell concern exists, and risk is below any override threshold.
- Await information/hold for remediable missing or not-run evidence when there is no stronger escalation trigger.
- Escalate for identity or risk concerns such as bank name mismatch, invalid tax, expired license, vendor hold, confirmed PEP/sanctions, shell suspicion, or high risk override.
- Follow-up or review-queue lists should include every business that cannot be released immediately. Overall release readiness is true only when every scoped business is releasable.

## Prepaid Close Reconciliation

Use the local scope payload for entity, close period, accounts, selected invoice IDs, and any variance threshold. Preserve selected invoice order where the template requires it.

For each selected prepaid invoice:

1. Fetch the invoice by `prepaid_invoice_id`.
2. Use the API's `monthly_amortization` value; do not recompute it unless sanity-checking.
3. For a monthly close period, count service months inclusively by month:
   - current-period amortization is `monthly_amortization` if the close month falls between `service_start` and `service_end`, otherwise `0`.
   - cumulative amortization through the close month is monthly amortization times the number of active service months through that month, capped at `original_amount`.
   - ending balance is `original_amount - cumulative_amortization`, floored at zero for fully amortized invoices.
4. Round reported amounts to two decimals. Sum selected invoices only.
5. Default/missing-term flags come from missing service dates, default term usage, or `data_quality_flags` such as `missing_contract_dates`.
6. Exception invoice IDs should include invoices with material data-quality flags or task-defined exception flags. Keep the default/missing-term list separate when the schema asks for both.

For each account rollup:

- Fetch the GL ending balance for the scoped entity, account, and period.
- `schedule_ending_balance` is the sum of selected invoice ending balances for that account.
- `variance_amount = schedule_ending_balance - gl_ending_balance`.
- `variance_flag` is true when the absolute variance exceeds the local threshold; if no threshold is provided, treat any non-zero material variance as flagged.
- `has_default_missing_term_flag` is true when any selected invoice in that account has the default/missing-term flag.
- Use `reconciled` when there are no material variances or exceptions, `variance_review` for variance-only issues, and `requires_reconciliation` when data-quality/default-term issues or multiple unresolved close issues require correction.

## Final Validation Checklist

- Every requested ID is present in the appropriate output object or list; no out-of-scope IDs are added.
- Lists are sorted ascending unless the schema says to preserve input order.
- Amounts use the requested unit and precision; integer cents are not mixed with decimal dollars.
- Paid/open/blocked classifications reconcile to the detailed evidence and totals.
- Vendor release decisions reconcile to hard-stop flags, follow-up/review queues, and overall readiness.
- Prepaid rollups reconcile to invoice-level rows, GL balances, variances, and exception lists.
- The final object has exactly the required top-level keys and no extras when `additional_properties_allowed` is false.
