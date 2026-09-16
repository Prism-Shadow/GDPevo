---
name: task-group-005-finance-reconciliation
description: Solve task_group_005 finance close, AP reimbursement, prepaid, vendor onboarding, and payment-release tasks using local scope payloads plus the current ERP/compliance API.
---

# Task Group 005 Finance Reconciliation

Use this skill when a task asks for a finance close, AP reimbursement, prepaid schedule, vendor onboarding, or vendor account-change release decision from the shared `task_group_005` API.

## Core Workflow

1. Read the prompt, every local payload, and the answer template. Treat local payloads as scope, batch context, stale snapshots, or output schemas. Treat the API as the system of record unless the prompt explicitly says otherwise.
2. Use the runner-provided `<TASK_ENV_BASE_URL>`. Strip any trailing slash. Start with `GET /endpoints` if endpoint names are uncertain.
3. Prefer `/api/...` endpoints and fall back to the non-API aliases when needed. Use exact-match query parameters by field name. Paginate list endpoints with `limit` and `offset` until all records are fetched.
4. Fetch only records needed for the scoped IDs, accounts, entity, period, and review date. Cross-check linked records rather than trusting a single status field.
5. Follow the answer template exactly: required keys, enum values, top-level order when specified, JSON only, no narrative. Sort IDs ascending unless the template says to preserve local scope order.
6. Use `Decimal` or integer cents internally for money. Round output amounts to the template precision, usually two decimal JSON numbers. If the prompt conflicts with the template, the template's type and precision control the final JSON shape.

Useful endpoints:

- Claims and AP: `/api/claims`, `/api/claims/{claim_id}`, `/api/ap/bills`, `/api/ap/payments`, `/api/ap/aging`, `/api/close/logs`
- Vendors and compliance: `/api/vendors`, `/api/compliance/objects`, `/api/compliance/ownership/{business_id}`, `/api/compliance/registry/{business_id}`, `/api/compliance/screening/{business_id}`, `/api/compliance/bank/{business_id}`
- Prepaids and GL: `/api/prepaids/invoices`, `/api/prepaids/gl-balances`

## AP Reimbursement And Stale Snapshot Tasks

For each scoped claim ID:

- Fetch the current claim, all AP bills linked by `claim_id`, payments for each bill, and AP aging if balances are needed.
- A valid reimbursement bill is non-void, linked to the claim, same currency, same amount as the claim, and same vendor when both sides have a vendor ID. Ignore stale AP rows whose amount, vendor, status, or bill ID does not match current evidence.
- A claim is settled only when a valid bill is paid and has a cleared payment matching the bill amount and vendor. Scheduled or processing payments are in-flight evidence, not cleared settlement.
- A claim is payable or eligible for release when the current claim is approved, required support is not missing, and it has a valid open AP bill. If a payment exists but is not cleared, keep the bill open and flag it as in flight when the template asks.
- A claim is blocked or not ready when the current claim is not approved or paid, support/receipt is incomplete for an unpaid claim, no valid AP link exists, the linked bill is void, or current AP evidence has amount/vendor mismatch.
- Open AP balance for release decisions is the valid non-void bill amount minus cleared payments. Do not reduce the releasable balance for scheduled or processing payments unless the template specifically asks for AP aging balance.

For stale AP snapshot correction enums, use current API evidence:

- `current_snapshot_ok`: local row already matches current valid claim, bill, and payment posture.
- `mark_in_flight_payment`: current bill is valid but payment is scheduled or processing rather than cleared.
- `replace_with_matched_paid_bill`: stale row points at an old or wrong bill, while a different current bill is valid, paid, and cleared.
- `exclude_amount_or_vendor_mismatch`: current linked AP row fails claim amount or vendor matching.
- `ignore_void_bill`: current linked bill is void.
- `block_unapproved_claim`: current claim is not approved/paid or required claim support is missing.

Batch status is template-specific. In close-review templates, any blocked claim makes the batch `blocked`; otherwise use an open-payables status when valid unpaid bills remain, and ready-to-close only when everything is settled. In stale-snapshot release templates, use `needs_ap_refresh` when corrections or close-log refresh evidence are required; reserve `blocked` for unreleasable batches or unresolved blockers specified by the prompt.

When close logs are requested, query `/api/close/logs` by the relevant area, period, message, or account from the prompt and stale context. Return matching log IDs sorted as required; do not invent log IDs.

## Prepaid Close Tasks

Use the scope payload for entity, close period, accounts, selected invoice IDs, and variance threshold.

For each selected prepaid invoice:

- Fetch the current invoice from `/api/prepaids/invoices` and keep the selected invoice order in `invoice_results`.
- Use the record's `monthly_amortization` and straight-line monthly schedule. Count calendar months inclusively from the service-start month through the close period, limited by service end. A mid-month start still contributes the full monthly amount for that month when the source record supplies a monthly amortization.
- Current-period amortization is the monthly amount if the close period falls within the service term by month; otherwise it is zero.
- Cumulative amortization is monthly amortization times recognized month count, capped only to avoid a negative ending balance from rounding. Ending balance is original amount minus cumulative amortization.
- `default_missing_term_flag` applies when source flags or missing fields indicate missing/defaulted contract dates, term, service start/end, or recognition term. If the flag says the license/term is missing, do not double-count a derived expiry-style flag unless the prompt requires it.
- `exception_flag` applies when any invoice `data_quality_flags` exist or a default/missing-term condition is present.

For account rollups:

- Group selected invoices by account. Sum original amount, current-period amortization, cumulative amortization, and schedule ending balance.
- Fetch GL balances for the entity and close period from `/api/prepaids/gl-balances`; use GL `account_name` and `ending_balance`.
- `variance_amount = schedule_ending_balance - gl_ending_balance`.
- `variance_flag` is true when absolute variance exceeds the threshold in the scope/prompt, or when the template defines a stricter rule.
- Use `reconciled` only when there is no material variance and no blocking data-quality issue. Use `requires_reconciliation` for material variances, missing GL, or default/missing-term issues. Use `variance_review` for non-material review conditions when the template allows it.
- Sort exception invoice ID lists ascending, but preserve scope order for selected IDs and invoice result rows when requested.

## Vendor Onboarding Risk Tasks

For each scoped business ID:

- Fetch the compliance object plus ownership, registry, screening, and bank detail endpoints. Fetch the vendor record by the `vendor_id` found in the compliance object or local account-change event.
- Count reportable UBOs as unique owner names with `ownership_pct >= 25`. Duplicate names count once.
- Build hard-stop flags from current evidence and sort flag lists alphabetically by enum value:
  - `bank_closed`: bank account status is closed.
  - `bank_name_mismatch`: bank account status is name mismatch.
  - `confirmed_pep`: screening PEP status is confirmed.
  - `expired_license`: registry/license expiry is before the as-of date, unless the license document itself is missing and the template expects `missing_required_documents` instead of double-counting expiry.
  - `missing_required_documents`: required document or compliance fields are missing.
  - `sanctions_confirmed`: sanctions status is a confirmed hit.
  - `screening_not_run`: PEP or sanctions screening has not run or is missing.
  - `shell_company_suspected`: ownership/compliance says shell company is suspected.
  - `vendor_on_hold`: current vendor status is on hold.
- Decide release control from risk, not from source `review_status`: approve only when no hard-stop flags apply; use awaiting-information when only missing documents or unrun screening remain; escalate for severe flags such as bank closed/mismatch, confirmed PEP, sanctions hit, shell suspicion, expired license, or vendor hold.
- Follow-up business IDs are all non-approved businesses. Overall release readiness is true only when every scoped business is approved/releasable.

## Vendor Account-Change Payment Release Tasks

Use the local batch to identify target business IDs, account-change tickets, requested bank last four, review date, and fixed template values. Return target IDs sorted ascending unless the template says otherwise.

For each target business:

- Fetch current vendor, compliance object, registry, screening, bank, and ownership evidence. Use the ticket's `vendor_id` when supplied; otherwise use the compliance object's `vendor_id`.
- `bank_mismatch_ids` should follow the template description. When it is defined as compliance bank name mismatch, include only businesses whose current compliance `bank_account_status` is `name_mismatch`; do not include closed-bank records unless the field asks for all bank failures.
- Validate account-change bank evidence by comparing requested last four to current vendor bank last four when the prompt asks for account-change review.
- `invalid_tax_ids` includes businesses where vendor tax ID and registry/compliance tax ID disagree, or where the registry tax ID is malformed.
- `expired_license_ids` includes license expiries before the review/as-of date.
- `risk_score_override_flags` includes risk scores at or above the template threshold; if none is given, use `>= 70`.
- `review_queue_ids` is the sorted union of businesses with bank failure, requested-bank mismatch, invalid tax, expired license, missing required documents, screening not run, risk override, vendor hold, PEP/sanctions risk, or shell-company suspicion.
- Decision precedence is `escalate` over `hold` over `release`. Escalate for PEP concerns, sanctions hits, shell suspicion, vendor hold, or tax/identity issues combined with other compliance failures. Hold for remediable bank failures, expired licenses, missing documents, unrun screening, or risk-score override when no escalation trigger exists. Release only when the current evidence is clean.

## Final Validation

Before answering, parse the JSON, verify all required keys and enum values against the template, verify list ordering, and recheck every computed money total against the per-record details. Do not include training-case IDs, amounts, or answer records in reusable notes or final output.
