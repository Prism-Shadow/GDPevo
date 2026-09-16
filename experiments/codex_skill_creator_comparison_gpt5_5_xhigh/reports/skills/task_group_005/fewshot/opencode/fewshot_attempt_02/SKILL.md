---
name: erp-finance-api-reconciler
description: Use this skill for task-group ERP finance/compliance reconciliation prompts that require querying a runner-provided JSON API and returning exact JSON. It is especially relevant for reimbursement-to-AP close batches, stale AP snapshot reviews, prepaid close checks, vendor onboarding release decisions, account-change payment release reviews, and prompts mentioning claims, AP bills, payments, close logs, vendors, compliance objects, ownership, registry, screening, bank checks, prepaid invoices, or GL balances.
---

# ERP Finance API Reconciler

Use this skill when a task asks for finance/compliance release or close decisions from a shared ERP-style API. The work is evidence reconciliation, not summarization: local payloads define scope and output shape, while the current API records are the system of record.

## Core Workflow

1. Read the prompt and every local payload. Treat `answer_template.json` as the output contract: top-level keys, enum values, ordering, required constants, and numeric precision come from the template.
2. Get the API base URL from the runner placeholder or environment. Do not hardcode training URLs. Discover `/endpoints` when useful.
3. Pull current records for only the scoped IDs, accounts, periods, and entities. The API supports exact-match query parameters by field name plus `limit` and `offset`; paginate until all relevant records are available.
4. Build a short evidence table before finalizing: one row per scoped claim, business, invoice, or account, with the source fields that drive each decision.
5. Produce only the requested JSON. Do not include narrative text, citations, or extra keys unless the template asks for them.

When a prompt says "USD cents" in this task family, interpret it as USD amounts reported to cent precision unless the template explicitly requires integer cents.

## API Discipline

Prefer current API evidence over local snapshots, exports, or current review status fields. Local files usually identify candidates, review dates, stale context, or the JSON schema.

Common endpoint groups:

- Claims/AP: `/claims` or `/api/claims`, `/bills` or `/api/ap/bills`, `/payments` or `/api/ap/payments`, `/api/ap/aging`, `/close/logs` or `/api/close/logs`.
- Vendor/compliance: `/vendors` or `/api/vendors`, `/compliance/objects` or `/api/compliance/objects`, plus per-business ownership, registry, screening, and bank endpoints.
- Prepaids: `/prepaids/invoices` or `/api/prepaids/invoices`, `/gl/balances` or `/api/prepaids/gl-balances`.

If both shorthand and `/api/...` paths exist, either is acceptable; prefer the path named in the prompt. Use current endpoint records even when a local snapshot names stale bill/payment/review states.

## Reimbursement And AP Close Rules

For each scoped claim, reconcile claim, bill, payment, aging, and close-log evidence.

- Start from the claim record. A releasable unpaid claim is normally `approved`, has adequate support, and has a current AP bill linked to that claim.
- Treat `paid` claims as settled only when there is a matching paid AP bill and a cleared payment for the claim amount. A stale scheduled bill for the same claim should not override a later exact paid match.
- A valid reimbursement bill should be linked to the claim, not `void` or `draft`, and should match the claim amount and vendor evidence when those fields are present. Mismatched amount, vendor, or account evidence blocks AP release even if the claim itself is approved.
- For release/open-balance calculations, subtract only cleared payments from valid current bills. Scheduled or processing payments are in-flight evidence, not cleared settlement.
- Void bills, absent bills, stale AP rows, partial/missing support on unpaid claims, non-approved claim statuses, and amount/vendor mismatches produce blocked or not-ready outcomes according to the template's field names.
- Keep case issues separate from AP/payment evidence issues. For example, an unapproved or unsupported claim is an owner cleanup item; a bad bill link, void bill, or stale payment state is an AP evidence issue.

For stale AP snapshot review templates, map current evidence to correction enums rather than copying the snapshot:

- `mark_in_flight_payment`: valid current bill has a non-cleared payment in process.
- `replace_with_matched_paid_bill`: stale row should be replaced by a current exact paid bill with cleared payment.
- `exclude_amount_or_vendor_mismatch`: current bill evidence does not match the claim amount/vendor or is not a valid reimbursement bill.
- `ignore_void_bill`: the relevant AP bill is void.
- `block_unapproved_claim`: the claim status/support is not releasable.
- `current_snapshot_ok`: use only when the snapshot still matches current API evidence and no correction is needed.

Set batch status from the requested enum. A blocked/not-ready item usually makes the batch blocked; otherwise use the open-payable/needs-refresh status when valid unpaid or in-flight AP items remain; use the ready status only when nothing requires AP or owner action.

## Vendor Onboarding And Account-Change Rules

Do not copy `review_status` as the decision. Decide release posture from current vendor, compliance, ownership, registry, screening, and bank evidence.

Evidence and flags:

- Count reportable beneficial owners as unique owner names at or above the reporting threshold, usually 25 percent. Collapse duplicate owner names before reporting counts.
- `bank_closed`: compliance bank status is closed.
- `bank_name_mismatch`: compliance bank status is name mismatch.
- `confirmed_pep`: screening PEP status is confirmed PEP.
- `sanctions_confirmed`: sanctions screening is confirmed or matched.
- `screening_not_run`: required PEP or sanctions screening is not run.
- `shell_company_suspected`: ownership evidence marks shell-company suspicion.
- `vendor_on_hold`: vendor master status is on hold.
- `expired_license`: license expiry is before the review/as-of date, unless the license document itself is missing and the template expects a missing-document flag instead.
- `missing_required_documents`: required compliance fields/documents are missing.
- `invalid_tax`: registry tax ID is malformed or does not agree with vendor-master tax evidence when both are available.
- `risk_score_override`: risk score meets or exceeds the threshold named by the prompt/template; in this task family, use 70 when no other threshold is provided.

Decision posture:

- Approve/release only when no hard stop or review-queue condition remains.
- Use awaiting-information or hold for remediable missing documents, screening not run, closed/mismatched bank evidence, or risk-score override without a stronger escalation trigger.
- Escalate for legal/compliance severity such as confirmed PEP, confirmed sanctions, shell-company suspicion, vendor hold, invalid tax evidence, or combinations of multiple hard stops.
- Review/follow-up queues normally include every business that is not approved/released.

Sort hard-stop flags alphabetically when requested. Sort business ID lists ascending unless the template says to preserve input order.

## Prepaid Close Rules

Use only the scoped invoice IDs and accounts from the local payload. Reconcile the selected invoice schedule against the GL ending balance for the requested period/entity.

For each selected invoice:

- Use the invoice's `monthly_amortization` as the authoritative straight-line monthly amount.
- Count amortization months inclusively from the service-start month through the close period, capped by the service-end month. If the close period is before service start, cumulative amortization is zero.
- March/current-period amortization is the monthly amount only when the close period falls inside the service period; otherwise it is zero.
- Cumulative amortization is monthly amount times recognized months, rounded to two decimals. Ending balance is original amount minus cumulative amortization, rounded to two decimals; do not force away small rounding residuals unless the template says to.
- `default_missing_term_flag` applies to missing/default contract-term evidence such as missing contract dates.
- `exception_flag` applies to any invoice-level data-quality flag that should be surfaced, including rounded amounts and missing terms.

For each account rollup:

- Sum selected invoice original amounts, period amortization, cumulative amortization, and ending balances by account.
- Pull the GL ending balance for the same entity, period, and account.
- Variance is schedule ending balance minus GL ending balance.
- Set `variance_flag` using the absolute threshold from the local scope/template when provided.
- Mark account status as reconciled only when there is no material variance and no selected-invoice exception requiring close action. Use the template's stronger review/reconciliation status when variance or default/missing-term issues remain.

Preserve selected invoice ordering for invoice-result arrays when the template requires it; sort exception/default ID lists only when the template requires ascending order.

## Final JSON Check

Before responding:

- Every required key from the template is present, and no disallowed extra key is present.
- Enum values exactly match the template.
- IDs are ordered according to the template, not according to API return order.
- Amounts are numeric JSON values rounded to the requested precision.
- Boolean readiness fields are false if any scoped item requires hold, escalation, AP refresh, reconciliation, or owner cleanup.
- The result is a single JSON object or file as requested, with no prose outside it.
