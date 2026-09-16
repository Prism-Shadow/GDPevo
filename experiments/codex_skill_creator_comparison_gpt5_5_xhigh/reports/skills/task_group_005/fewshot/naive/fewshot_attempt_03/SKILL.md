---
name: api-finance-close-review
description: Solve API-backed finance close, reimbursement/AP release, vendor compliance release, account-change review, and prepaid reconciliation tasks using local payload scope plus a runner-provided JSON API.
---

# API Finance Close Review

Use this skill for tasks that ask you to return a JSON decision or reconciliation result from a local batch/scope payload and a shared finance, ERP, or compliance API.

## First Steps

1. Read the user prompt, every local payload file under `input/payloads/` or `payloads/`, and the answer template if present.
2. Treat the runner-provided API base URL as the system of record. Do not use local exports, snapshots, or stale payload records as current truth when they conflict with the API.
3. Inspect `/endpoints` when available. Prefer `/api/...` endpoints and fall back to unprefixed equivalents only if needed.
4. Query only the scoped IDs from the prompt or payload unless the template asks for a broader rollup. Use exact-match query parameters by field name, with `limit` and `offset` for pagination.
5. Return one JSON object matching the template exactly. Preserve requested units, date, casing, status labels, and list sort order. Do not include narrative text outside JSON.

Use `Decimal` or equivalent fixed-point arithmetic for money. If the prompt asks for cents, output integer cents; if it asks for dollars, output two-decimal numbers.

## Reimbursement And AP Batch Reviews

For each scoped claim, fetch:

- Current claim: `/api/claims` or `/api/claims/{claim_id}`
- AP bills: `/api/ap/bills?claim_id=...`
- Payments for candidate bill IDs: `/api/ap/payments?bill_id=...`
- Close logs when stale exports or close refreshes are mentioned: `/api/close/logs`
- Aging only as supporting context; live claim, bill, and payment records determine release posture.

Evaluate current records, not stale AP snapshots:

- A claim is release-ready only when the claim is approved or otherwise already paid, the claim has required receipt/support status for the task, and there is a live bill that matches the claim amount, currency, and vendor when vendor data is present.
- Ignore void bills. Treat draft bills as not released. Treat amount, currency, vendor, or claim-link mismatches as AP evidence exceptions, even if the stale export showed a row.
- A cleared payment on a matched bill means the claim is settled. Processing or scheduled payments are in flight and do not make the claim settled unless the template specifically treats in-flight payments as eligible.
- If a paid claim has multiple bills, prefer the matched bill with cleared payment evidence over an older mismatched or scheduled bill.
- If the claim itself is not approved or paid, or required receipts/support are missing or partial for an unpaid claim, classify it as needing owner cleanup rather than AP release.
- Open AP balance for release fields should be based on valid matched bills minus cleared payments. Do not reduce open balance for merely processing or scheduled payments unless the prompt defines that behavior.

When a template asks for stale snapshot corrections, map current API facts to the template's correction codes:

- Unapproved or receipt-blocked claim: block or mark not ready.
- Void bill: ignore or replace the stale row.
- Amount, vendor, currency, or claim mismatch: exclude or correct the AP evidence.
- Current matched paid bill: replace stale evidence with the paid bill.
- Current matched bill with processing/scheduled payment: mark as in flight, not settled.

Sort claim ID lists ascending. Set batch status from the classified results: clean only if every scoped item is settled or release-ready under the prompt; otherwise use the template's blocked, refresh, or not-ready status label.

## Vendor Onboarding Release Reviews

For each scoped business ID, fetch:

- Compliance object: `/api/compliance/objects?business_id=...`
- Ownership: `/api/compliance/ownership/{business_id}`
- Registry: `/api/compliance/registry/{business_id}`
- Screening: `/api/compliance/screening/{business_id}`
- Bank: `/api/compliance/bank/{business_id}`
- Vendor master by the compliance object's `vendor_id`: `/api/vendors?vendor_id=...`

Use the review or as-of date from the prompt or payload for date-sensitive checks.

Reportable UBO count is the count of unique owner names with `ownership_pct >= 25`; duplicate owner names count once.

Build hard-stop flags from current facts and sort each flag list lexicographically:

- `confirmed_pep`: screening or object `pep_status` is `confirmed_pep`.
- `shell_company_suspected`: ownership or object marks shell-company suspicion.
- `bank_closed`: bank status is `closed`.
- `bank_name_mismatch`: bank status is `name_mismatch`.
- `expired_license`: registry license expiry is before the review/as-of date.
- `screening_not_run`: sanctions or PEP screening is `not_run`.
- `missing_required_documents`: required fields or documents are missing.
- `vendor_on_hold`: linked vendor master status is `on_hold`.
- Add an analogous sanctions-hit flag if the API returns a non-clear sanctions result and the template supports it.

Decision pattern for onboarding release:

- `approve` only when there are no hard-stop flags.
- `awaiting_information` when the only blockers are information gaps such as missing documents or screening not run.
- `escalate` when any severe blocker is present: confirmed PEP, sanctions hit, shell-company suspicion, bank closure/name mismatch, expired license, vendor hold, or registry identity defect.

Follow-up or queue ID lists are the non-approved businesses. Overall release readiness is true only when every scoped business is approved.

## Account-Change Payment Release Reviews

For account-change batches, use the same compliance, registry, bank, screening, ownership, and vendor records, but apply payment-release posture rather than onboarding labels.

Common derived lists:

- Bank mismatch IDs: bank status `name_mismatch`. Keep bank-closed records in the broader review/hold set unless the template names a separate closed-bank list.
- Invalid tax IDs: registry tax ID fails the expected `TIN` plus six digits pattern, or the registry tax ID conflicts with the linked vendor master tax ID.
- Expired license IDs: license expiry is before the review/as-of date.
- Risk score override flags: risk score meets or exceeds the local high-risk threshold in the prompt/payload; when no threshold is supplied, treat `>= 70` as requiring override review.
- Review queue IDs: every scoped business whose final decision is not release.

Decision precedence:

- `escalate` for identity or compliance-judgment issues such as invalid tax/registry identity, PEP concern, sanctions hit, shell-company suspicion, or contradictory registry/vendor identity.
- `hold` for operational remediation issues such as bank not verified or closed, expired license, missing documents, screening not run, vendor hold, or risk-score override when no escalation issue is present.
- `release` only when all release-control checks pass.

Do not copy the source system's current review status as the decision; derive the release posture from current control evidence.

## Prepaid Close Reconciliations

Read the local prepaid scope for selected invoice IDs, accounts, entity, and close period. Fetch:

- Invoices: `/api/prepaids/invoices` or `/prepaids/invoices`
- GL balances: `/api/prepaids/gl-balances` or `/gl/balances`

Filter to the scoped invoice IDs and requested accounts. Use the GL ending balance for the requested period and entity.

For straight-line invoices, use the invoice record's `monthly_amortization`; do not recalculate a daily amount. Count service months by calendar month inclusively:

- Target-month amortization is `monthly_amortization` if the close month falls between the service start month and service end month, inclusive; otherwise it is zero.
- Cumulative amortization through the close month is `monthly_amortization * number_of_service_months_elapsed`, capped to the invoice's service months and original amount when necessary.
- Ending balance is `original_amount - cumulative_amortization`, rounded to two decimals and not below zero except for harmless rounding residuals.

For each account rollup:

- Sum selected invoice count, original amount, target-month amortization, cumulative amortization, and schedule ending balance.
- `variance_amount = schedule_ending_balance - gl_ending_balance`.
- Set `variance_flag` when the absolute variance exceeds the prompt/template tolerance; if no tolerance is given, use more than one cent.
- Set account status to the template's reconciliation-required label when there is a variance, missing/default term flag, or invoice exception; otherwise use the reconciled/clean label from the template.

Invoice flags:

- `default_missing_term_flag` is true for data-quality flags such as missing contract dates, missing terms, or default terms.
- `exception_flag` is true when `data_quality_flags` is non-empty, the recognition method is unsupported, required dates/amounts are missing, or the invoice violates prompt-specific scope rules.

Sort invoice IDs and business/claim IDs as requested by the prompt or template.
