---
name: reflection-skill-attempt-02
description: Use for PanofyBench task_group_005 finance close, reimbursement AP, prepaid reconciliation, vendor onboarding, and account-change payment-release tasks that require solving from the shared ERP/compliance API and returning schema-exact JSON.
---

# Task Group 005 Solver SOP

## Start Every Task

1. Read the prompt and local input payload/template. Use only the candidate IDs and fields requested.
2. Discover the API with `GET /endpoints`. Use the runner-provided base URL; do not use local environment files.
3. Query current records with exact-match parameters and pagination (`limit`, `offset`). Prefer `/api/...` endpoints, but shorthand paths are equivalent when listed.
4. Return JSON only, matching the template exactly. Preserve requested key names, enum values, numeric precision, and ordering.

Core endpoints:

- Claims/AP: `/api/claims`, `/api/ap/bills`, `/api/ap/payments`, `/api/close/logs`
- Vendors/compliance: `/api/vendors`, `/api/compliance/objects`
- Prepaids: `/api/prepaids/invoices`, `/api/prepaids/gl-balances`

## Reimbursement And AP Close

Use the current API as source of truth. Treat stale exports as context only.

For each candidate claim:

- Fetch claim by `claim_id`, all AP bills by `claim_id`, and payments by each `bill_id`.
- A paid claim needs a current paid AP bill for the claim amount and a cleared payment for that same bill/amount.
- A payable/open claim needs an approved claim and a valid current AP reimbursement bill with matching amount/vendor evidence. Scheduled or processing payments are not cleared; keep the open balance unless the task explicitly asks for settled-only classification.
- Block or mark not ready when the claim is not approved, receipts/support are unresolved, the AP bill is missing, void, stale, mismatched by amount/vendor, or linked to the wrong claim/vendor.

Balance rules:

- Count only valid non-void current AP rows.
- Cleared payments reduce balance; scheduled/processing payments do not.
- Invalid, voided, stale, or amount/vendor-mismatched AP rows contribute `0.00`, even if the AP export showed an amount.
- If a template has separate `paid_claim_ids`, put settled items there. If it has only eligible/not-ready lists, a corrected matched paid bill can be eligible with `0.00` balance.

Common stale correction mapping:

- Processing/scheduled current payment found after stale no-payment export: `mark_in_flight_payment`.
- Stale bill replaced by matched paid bill and cleared payment: `replace_with_matched_paid_bill`.
- Current amount/vendor mismatch: `exclude_amount_or_vendor_mismatch`.
- Current AP bill is void: `ignore_void_bill`.
- Current claim is not approved or still needs receipt/support: `block_unapproved_claim`.

When `close_log_required` is requested, select only close-log IDs directly relevant to the batch evidence in the prompt and current API. Do not dump every open/blocked log for a related account.

## Vendor Onboarding

For each business ID:

- Fetch `/api/compliance/objects?business_id=...`, then fetch `/api/vendors?vendor_id=...`.
- Count reportable UBOs as unique owner names with `ownership_pct >= 25`; dedupe repeated names.
- Do not copy `review_status` blindly. Decide release posture from evidence.

Hard-stop flags:

- `bank_account_status=closed` -> `bank_closed`; `name_mismatch` -> `bank_name_mismatch`.
- `pep_status=confirmed_pep` -> `confirmed_pep`; `possible_pep` is not the same flag.
- `sanctions_check_status=confirmed` or equivalent -> `sanctions_confirmed`; `not_run` screening in sanctions or PEP evidence -> `screening_not_run`.
- `shell_company_suspected=true` -> `shell_company_suspected`.
- Nonempty `missing_fields` -> `missing_required_documents`. If the missing field is license evidence, do not also double-count it as expired license.
- Vendor `status=on_hold` -> `vendor_on_hold`.
- Use `expired_license` only when the task treats license expiry as a hard-stop evidence item and the license date is before the task as-of date.

Decision guidance:

- `approve`: no hard-stop flags, even if the source review status is merely `in_review`.
- `awaiting_information`: missing documents or unrun screening without confirmed adverse findings.
- `escalate`: confirmed PEP/sanctions, suspected shell company, bank closed/name mismatch with serious risk evidence, vendor hold, or multiple severe hard stops.
- Follow-up business IDs are the businesses with nonempty hard-stop flags.

## Account-Change Payment Release

Join each account-change ticket to compliance and vendor records.

- `bank_mismatch_ids`: business IDs where compliance `bank_account_status` is `name_mismatch` only. A closed bank is a hold/review issue, not this list unless the template says otherwise.
- `invalid_tax_ids`: vendor and compliance tax IDs disagree, are malformed, or are missing.
- `expired_license_ids`: `license_expiry` before `as_of_date`.
- `risk_score_override_flags`: `risk_score >= 70`.
- `review_queue_ids`: any non-release business requiring AP/compliance review before payment, including bank mismatch/closed bank, invalid tax, expired or missing license, vendor hold, screening not run, PEP, sanctions, shell suspicion, or risk override.

Decision guidance:

- `release`: bank verified, requested/vendor bank evidence matches, tax IDs agree, license current, screening clear, vendor active, and risk below override threshold.
- `hold`: remediable release blockers such as bank mismatch/closed bank, missing license, screening not run, or risk override without confirmed adverse evidence.
- `escalate`: confirmed PEP/sanctions, invalid tax combined with other serious blockers, vendor hold with adverse compliance evidence, shell suspicion, or not-started/escalated compliance with multiple control failures.

## Prepaid Close

Use only invoice IDs in the scope payload and only requested accounts.

For each selected invoice:

- Fetch the current prepaid invoice record and March/close-period GL balance.
- Use API `monthly_amortization` as authoritative.
- March amortization is the monthly amount when the service period includes March; otherwise `0.00`.
- Cumulative amortization through the close month is monthly amount times included months from service start through the close month, rounded to two decimals.
- Ending balance is `original_amount - cumulative_amortization`. Preserve normal rounding residuals such as `0.01`.

Rollups:

- Sum original amount, period amortization, cumulative amortization, and ending balance by account.
- `variance_amount = schedule_ending_balance - gl_ending_balance`.
- `variance_flag = abs(variance_amount) > variance_threshold_abs`.
- `default_missing_term_flag` is true for `data_quality_flags` containing `missing_contract_dates`.
- `exception_flag` is true for any nonempty `data_quality_flags`.
- `account_status = requires_reconciliation` when variance is over threshold or the account has default/missing-term exceptions; otherwise `reconciled` unless the template defines a softer review state.

Ordering:

- `selected_invoice_ids` and `invoice_results`: same order as the scope payload.
- Exception/default ID lists: ascending invoice ID.
- Business and claim ID lists: ascending ID unless the template says otherwise.

## Pitfalls

- Do not trust stale AP snapshots or source `review_status` alone.
- Do not count duplicate UBO names twice.
- Do not treat scheduled/processing payments as cleared.
- Do not count invalid/mismatched AP bills in balances.
- Recalculate arithmetic after rounding; many failures are one-field math errors.
- Keep output schema-exact: no narrative, no extra keys, and exact enum spelling.
