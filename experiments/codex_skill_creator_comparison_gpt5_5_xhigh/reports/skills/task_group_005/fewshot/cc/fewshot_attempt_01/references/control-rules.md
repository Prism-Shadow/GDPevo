# Control Rules

These rules describe the reusable patterns for task-group finance-control JSON tasks. Apply the prompt and template first; use these rules to choose and reconcile evidence.

## Shared API Rules

- API responses commonly wrap lists as `{count, data, endpoint, limit, offset, total}`. Page through until all rows are fetched when using broad endpoint reads.
- Exact-match filters use field names, for example `claim_id`, `bill_id`, `vendor_id`, `business_id`, `entity`, or `period`.
- Duplicate or stale-looking identifiers can exist. Match records by the full control key: ID plus claim/business/vendor, amount, status, date, and memo/context.
- Prefer scoped exact reads for requested IDs. Use broad reads only when the task needs discovery, close logs, or an endpoint does not expose a direct single-record route.

## AP Reimbursement and Stale Snapshot Reviews

Use `/api/claims`, `/api/ap/bills`, `/api/ap/payments`, and `/api/close/logs` when the task concerns reimbursement close, AP batches, stale exports, claim release, paid claims, or open AP balances.

For each candidate claim:

- Current claim evidence:
  - A releasable unpaid claim normally needs `status: approved`, a usable receipt/support state, USD currency, and a current AP bill that matches the claim.
  - `paid` claims can be treated as settled only when there is a matching paid AP bill and a cleared payment for the claim amount.
  - Unapproved, rejected, needs-receipt, partial-support, or otherwise unresolved expense-case states require owner cleanup unless current paid evidence fully settles the claim.
- Bill matching:
  - Match current AP bills by `claim_id` when possible.
  - The valid reimbursement bill should match the claim amount and vendor when those fields are present.
  - Ignore void bills for open balance and release eligibility.
  - Treat draft, amount mismatch, vendor mismatch, unrelated account, or stale replacement rows as not release-ready unless the prompt defines a different rule.
- Payment matching:
  - A settled claim needs a cleared payment matching the valid bill and amount.
  - Scheduled or processing payments are in flight, not cleared. They may explain stale-snapshot correction fields but do not reduce open AP balance unless the template explicitly asks for pending-payment exposure.
  - Open AP balance is valid open bill amount minus cleared payments against that bill, never including void or stale mismatched rows.
- Stale export corrections:
  - Compare each snapshot row to current claim, bill, and payment records.
  - Use correction enums according to the current defect: in-flight payment, replacement paid bill, amount/vendor mismatch, void bill, unapproved claim, or snapshot still current.
  - When a template asks for close-log IDs, include only current close-log records tied to the stated stale-refresh, AP, or close-control context.
- Batch status:
  - If any candidate is blocked/not ready, use the blocked or refresh-needed enum supplied by the template.
  - If no candidates are blocked but valid open payables remain, use the open-payables enum.
  - If every candidate is already settled and no action remains, use the ready-to-close/send enum.

## Vendor Onboarding Release Control

Use `/api/compliance/objects`, `/api/compliance/ownership/{business_id}`, `/api/compliance/registry/{business_id}`, `/api/compliance/screening/{business_id}`, `/api/compliance/bank/{business_id}`, and `/api/vendors`.

- Reportable UBO count:
  - Use the prompt threshold if given; otherwise use 25 percent.
  - Count unique owner names whose `ownership_pct` is at or above the threshold.
  - Deduplicate repeated names after threshold filtering.
- Hard-stop flags:
  - `bank_closed`: compliance bank status is closed.
  - `bank_name_mismatch`: compliance bank status is name mismatch.
  - `confirmed_pep`: screening PEP status is confirmed.
  - `expired_license`: license exists and expiry date is before the review/as-of date.
  - `missing_required_documents`: required fields or documents are missing.
  - `sanctions_confirmed`: sanctions screening indicates a confirmed hit.
  - `screening_not_run`: PEP or sanctions screening has not been run.
  - `shell_company_suspected`: ownership evidence marks shell-company suspicion.
  - `vendor_on_hold`: vendor status is on hold.
- Decisions:
  - `approve` only when no hard-stop or follow-up evidence remains.
  - Use `awaiting_information` when the remaining issue is missing or incomplete information that can be supplied without escalation.
  - Use `escalate` for confirmed PEP, confirmed sanctions, bank closed/name mismatch, shell-company suspicion, vendor hold, expired current license, or combinations of screening/document issues that block release control.
- Overall release is ready only when every scoped business is approved/releasable.

## Account-Change Payment Release

For payment release after account-change events, combine the local ticket payload with current vendor and compliance evidence.

- Validate the target businesses from the local batch payload, then sort output ID lists as requested.
- `bank_mismatch_ids` should follow the template definition. When it says name mismatch, include only `bank_account_status: name_mismatch`; treat closed bank accounts as review issues but not name mismatches.
- `invalid_tax_ids` includes businesses whose registry tax ID is malformed for the local pattern or does not match the current vendor tax ID.
- `expired_license_ids` uses the task's as-of date; include license expiry dates earlier than that date.
- `risk_score_override_flags` uses the threshold in the prompt/template; if only examples imply it, use `risk_score >= 70`.
- `review_queue_ids` includes any business that cannot be released without compliance/AP review: bank not verified, invalid tax, expired license, missing required fields, screening not run, PEP/sanctions concerns, vendor not active, shell-company suspicion, or risk-score override.
- Decision mapping:
  - `release`: no review-queue evidence.
  - `hold`: remediable AP/compliance issues such as bank closed/name mismatch, missing documents, screening not run, expired license, or risk override when no escalation trigger is present.
  - `escalate`: invalid tax evidence, vendor hold, confirmed PEP, confirmed sanctions, shell-company suspicion, or serious combined risk that release control cannot resolve as a simple hold.

## Prepaid Close Reconciliation

Use `/api/prepaids/invoices` and `/api/prepaids/gl-balances` for prepaid schedule and GL comparisons.

- Scope:
  - Use the invoice IDs, entity, period, accounts, and threshold from local payloads and the prompt.
  - Preserve invoice result order if the template says to match the scope file order.
- Schedule calculation:
  - Use the API `monthly_amortization` value for straight-line monthly amortization.
  - A month counts when the service period overlaps that month. Count months from service start through the close period, capped by service end.
  - Cumulative amortization through the close period is monthly amortization times counted months, capped at original amount where necessary.
  - Ending balance is original amount minus cumulative amortization, rounded to the requested precision.
- Flags:
  - `default_missing_term_flag` should be true for missing/defaulted contract dates or term data-quality flags.
  - `exception_flag` should be true for any data-quality flag or prompt-specific exception condition.
  - Keep separate lists for missing/defaulted term invoices and all exception invoices when requested.
- Account rollup:
  - Sum selected invoices by account for original amount, current-period amortization, cumulative amortization, and schedule ending balance.
  - Join GL balances by entity, account, and close period.
  - Variance is schedule ending balance minus GL ending balance.
  - Use the threshold in the scope payload or prompt for variance flags.
  - Choose account status from the template enums: reconciled when no variance/exception remains, variance review for variance-only issues if available, and requires reconciliation when variance or data-quality exceptions block close.
