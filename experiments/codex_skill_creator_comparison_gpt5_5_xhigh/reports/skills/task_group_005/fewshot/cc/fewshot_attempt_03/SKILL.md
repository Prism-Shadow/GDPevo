---
name: task-group-005-finance-reconciliation
description: Use this skill for task_group_005 finance, ERP, AP, reimbursement, prepaid close, vendor onboarding, compliance, or account-change release tasks that require using the shared JSON API plus local payload templates to return a decision JSON. Trigger whenever the prompt mentions the runner-provided API base URL, current ERP/compliance evidence, AP bills/payments, claims, vendors, UBOs, bank/tax/license screening, GL balances, or prepaid schedules.
---

# Task Group 005 Finance Reconciliation

Use this skill to solve finance close and compliance release tasks backed by the shared task API. The local files define the requested scope and JSON schema; the API is the current system of record.

## Core Workflow

1. Read the prompt, every file under `input/payloads/`, and especially the answer template.
2. Get the API base URL from the prompt placeholder replacement, the runner environment, or the provided task environment variable. Check `/endpoints` first when endpoint names are uncertain.
3. Prefer `/api/...` endpoints, with the non-`/api` alternatives as fallbacks. The API supports exact-match query parameters by field name and `limit`/`offset` pagination.
4. Fetch only the records in scope whenever possible. Do not treat local stale snapshots, batch notes, or review status fields as final evidence when current API records disagree.
5. Build the response exactly to the template:
   - Use the template's top-level keys and required values.
   - Preserve any specified ordering: ID lists usually sort ascending, while invoice result lists often preserve payload order.
   - Return JSON only, with no commentary.
   - Use two-decimal USD values unless the template explicitly asks for integer cents.

Use decimal arithmetic for currency. Round final money fields to two decimals, not intermediate source values unless the template says otherwise.

## API Map

Use these endpoints by evidence type:

- Claims: `/api/claims`, `/api/claims/{claim_id}`
- AP bills: `/api/ap/bills`
- AP payments: `/api/ap/payments`
- AP aging, if useful for checking balances: `/api/ap/aging`
- Vendors: `/api/vendors`
- Compliance object summary: `/api/compliance/objects`
- Ownership and UBOs: `/api/compliance/ownership/{business_id}`
- Registry and tax/license: `/api/compliance/registry/{business_id}`
- Screening: `/api/compliance/screening/{business_id}`
- Bank status: `/api/compliance/bank/{business_id}`
- Prepaid invoices: `/api/prepaids/invoices`
- Prepaid GL balances: `/api/prepaids/gl-balances`
- Close logs: `/api/close/logs`

When a list endpoint is used, filter with exact query parameters such as `?claim_id=...`, `?business_id=...`, `?vendor_id=...`, `?period=...`, or `?prepaid_invoice_id=...`. If the returned `total` exceeds the returned `count`, page through all records needed for the requested scope.

## Reimbursement and AP Close

Use this branch when the task asks about expense claims, reimbursement batches, AP release, stale AP exports, bills, payments, or close-log corrections.

For each candidate claim:

1. Fetch the current claim.
2. Fetch all AP bills where `claim_id` equals the claim ID.
3. Fetch payments for each candidate bill.
4. Compare current API records to any local AP snapshot, but use the API for the decision.

Classify AP evidence this way:

- A valid reimbursement bill is linked to the claim, not `void` or `draft`, in USD, and matches the claim amount and vendor when the claim has a vendor.
- A claim is paid only when there is a matching paid AP bill and cleared payment evidence for the claim amount. Scheduled or processing payments are not cleared.
- Open AP balance is the valid bill amount minus cleared payments only. Do not reduce open balance for scheduled or processing payments.
- A currently paid, amount-matched bill with a cleared payment can make a stale scheduled row obsolete.
- A void bill should be ignored as payable evidence and called out as stale/invalid when the template asks for corrections.
- Amount mismatches, vendor mismatches, missing AP links, non-approved claim status, and unsupported receipts make a claim blocked or not ready unless the template has a more specific bucket.

Use the template field names to choose the exact categories:

- `paid_claim_ids`: claims with matching paid bill and cleared payment evidence.
- `payable_claim_ids`, `eligible_claim_ids`: claims that can remain in the AP workflow because current evidence is valid. Depending on the template, this can include open scheduled bills and already settled claims that need stale snapshot replacement.
- `blocked_claim_ids`, `not_ready_claim_ids`: claims with unresolved claim, receipt, AP-link, amount, vendor, void-bill, or payment evidence problems.
- `crm_required_claim_ids`: blocked claims needing expense-case owner cleanup or AP-link remediation, not claims that are merely already paid.
- `ap_open_balance_total` or `ap_balance_by_claim`: valid open AP balance after cleared payments only.

For stale snapshot correction enums, use this mapping:

- `current_snapshot_ok`: snapshot and current API evidence materially agree.
- `mark_in_flight_payment`: a valid current bill has a scheduled or processing payment that is not cleared yet, or the snapshot missed an in-flight payment.
- `replace_with_matched_paid_bill`: a stale row should be replaced by a current matching paid bill with cleared payment.
- `exclude_amount_or_vendor_mismatch`: the current or snapshot bill does not match the claim amount or vendor.
- `ignore_void_bill`: the linked bill is void and should not support release.
- `block_unapproved_claim`: the claim itself is not currently approved or paid.

For close logs, query `/api/close/logs` only when the template asks. Include log IDs that are directly relevant to the AP close correction or refresh evidence in the task context, such as AP-area logs for the relevant period and correction type. Do not include unrelated closed logs just because they exist.

Batch status rules:

- Use a blocked status if any item is truly blocked or not ready.
- Use an open-payables or refresh-needed status when valid unpaid AP items or stale-snapshot corrections remain.
- Use ready status only when every item is either settled or valid for release under the template semantics.

## Vendor Compliance and Release

Use this branch for vendor onboarding, finance-risk release, account-change payment release, compliance review, bank/tax/license screening, or UBO reporting.

For each target business ID:

1. Fetch the compliance object summary.
2. Fetch ownership, registry, screening, and bank detail endpoints for that business.
3. Fetch the vendor record by `vendor_id`.
4. Use the review or as-of date from the prompt/payload for date comparisons.

Field rules:

- Reportable UBO count is the number of unique owner names with at least 25 percent ownership. If the same name appears multiple times, count it once if any occurrence is at or above the threshold.
- `bank_name_mismatch` or `bank_mismatch_ids`: bank status is `name_mismatch`.
- `bank_closed`: bank status is `closed`.
- `vendor_on_hold`: vendor status is `on_hold`.
- `confirmed_pep`: screening `pep_status` is `confirmed_pep`.
- Treat `possible_pep` as escalation evidence for release decisions, even when no hard-stop enum exists for it.
- `sanctions_confirmed`: sanctions status indicates a confirmed sanctions hit.
- `screening_not_run`: sanctions or PEP screening status is `not_run`.
- `shell_company_suspected`: ownership detail marks shell-company suspicion.
- `missing_required_documents`: `missing_fields` is non-empty, or the prompt/template identifies missing license, owner, registry, bank, tax, or support documents as required.
- `expired_license`: registry `license_expiry` is before the as-of date. If the license itself is missing and the template has a missing-document bucket, prefer the missing-document flag instead of double-counting unless the template explicitly asks for expired license IDs.
- `invalid_tax_ids`: registry/compliance tax ID is missing, malformed, or differs from the current vendor tax ID.
- `risk_score_override_flags`: risk score is 70 or higher.

Decision guidance:

- `approve` or `release`: no current bank, vendor, tax, license, screening, missing-document, UBO, sanctions, PEP, shell-company, or risk-score blocker.
- `awaiting_information`: only remediable information gaps exist, such as missing documents or screening not run, and there is no severe escalation evidence.
- `hold`: payment should not release because of operational blockers such as bank mismatch/closed status, expired license, missing documents, screening not run, or high risk score, but without escalation evidence.
- `escalate`: use for confirmed sanctions, confirmed or possible PEP concerns, shell-company suspicion, invalid or mismatched tax ID, vendor on hold, or multiple serious hard stops that make finance-risk release unsuitable for routine follow-up.

Populate follow-up or review-queue ID lists with every business that is not approved/released or that has any template-specific blocker list membership. Sort business IDs ascending unless the template says otherwise. Sort hard-stop flag lists alphabetically by enum value.

## Prepaid Close Reconciliation

Use this branch for prepaid close, prepaid schedule, amortization, GL balance, account rollup, or variance tasks.

1. Read the scope payload for entity, close period, accounts, selected prepaid invoice IDs, and variance threshold.
2. Fetch each selected prepaid invoice from `/api/prepaids/invoices`.
3. Fetch GL balances for the close period from `/api/prepaids/gl-balances` and filter to the scoped entity and accounts.
4. Compute invoice results in the same order as the selected IDs.
5. Aggregate account rollups over selected invoices only.

Straight-line monthly amortization:

- Use `monthly_amortization` from the invoice record.
- Count whole calendar months from the service start month through the close month, inclusive, capped by the service end month.
- Do not prorate partial months; the API monthly amount already represents the schedule.
- Current-period amortization is the monthly amount only when the close month falls within the service period.
- Cumulative amortization through the close month is `monthly_amortization * recognized_month_count`, rounded to two decimals.
- Ending balance is `original_amount - cumulative_amortization_through_close`, rounded to two decimals. Clamp only immaterial negative rounding noise to zero.

Invoice flags:

- `default_missing_term_flag` is true for missing/default service-term evidence such as a `missing_contract_dates` data-quality flag.
- `exception_flag` is true when `data_quality_flags` is non-empty or the invoice has other source-record quality problems the template asks to identify.
- `default_missing_term_invoice_ids` includes invoices with the default/missing-term flag.
- `exception_invoice_ids` includes all invoice-level exceptions, including rounded amount flags and missing-term flags.

Account rollup:

- Sum original amount, current-period amortization, cumulative amortization, and ending balance by account.
- `selected_invoice_count` counts only scoped invoices for that account.
- `gl_ending_balance` comes from the GL balance endpoint for the same entity, period, and account.
- `variance_amount` is schedule ending balance minus GL ending balance.
- `variance_flag` is true when `abs(variance_amount)` is greater than the scoped absolute threshold.
- `has_default_missing_term_flag` is true when any selected invoice in the account has that flag.
- Use `requires_reconciliation` when the account has a threshold variance or default/missing-term issue. Use `variance_review` for non-threshold residual variance or invoice exceptions needing review. Use `reconciled` only when the account has no material variance or exception under the template.

## Final Checks

Before returning:

- Confirm every scoped ID from the prompt or payload was reviewed.
- Confirm all required template keys are present and no disallowed extra keys are present.
- Confirm sorted lists and payload-order lists match their required ordering.
- Confirm enum values exactly match the template.
- Confirm booleans are booleans, numbers are numbers, and money has the requested precision.
- Return only the final JSON object.
