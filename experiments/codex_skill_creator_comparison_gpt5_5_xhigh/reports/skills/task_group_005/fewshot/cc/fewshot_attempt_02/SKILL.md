---
name: erp-finance-control-review
description: Use this skill for finance close, AP reimbursement release, vendor onboarding, account-change payment release, prepaid reconciliation, or other task_group ERP/compliance reviews that require querying a runner-provided JSON API and returning a strict JSON answer. Trigger when the user mentions claims, AP bills, payments, stale AP exports, close logs, vendors, compliance objects, UBOs, licenses, bank mismatches, prepaid schedules, GL balances, or an answer_template.json schema.
---

# ERP Finance Control Review

Use the runner-provided API as the system of record. Local payloads define scope, schema, review date, and any stale context, but do not override current API records unless the prompt explicitly says so.

## First Pass

1. Read the prompt, `input/payloads/answer_template.json`, and every local payload file.
2. Extract the exact IDs, entity, period, accounts, review/as-of date, thresholds, and ordering rules from the prompt and payloads.
3. Resolve `<TASK_ENV_BASE_URL>` from the runner context or environment. Confirm available routes with `GET /endpoints` when uncertain.
4. Fetch only scoped current records using exact-match query parameters where possible. The API supports `limit` and `offset`; paginate if a collection is larger than the returned page.
5. Build the answer from current API evidence, then validate against the template before responding with JSON only.

If useful, use [`scripts/collect_task_records.py`](scripts/collect_task_records.py) to collect scoped API data for claims, business compliance, or prepaids.

## API Routes

Prefer `/api/...` routes, with the non-API routes as fallbacks:

- Claims/AP: `/api/claims`, `/api/claims/{claim_id}`, `/api/ap/bills`, `/api/ap/payments`, `/api/ap/aging`, `/api/close/logs`.
- Vendor/compliance: `/api/vendors`, `/api/compliance/objects`, `/api/compliance/ownership/{business_id}`, `/api/compliance/registry/{business_id}`, `/api/compliance/screening/{business_id}`, `/api/compliance/bank/{business_id}`.
- Prepaids: `/api/prepaids/invoices`, `/api/prepaids/gl-balances`.

## AP Reimbursement Claims

For each candidate claim, fetch the claim, all AP bills linked by `claim_id`, and all payments linked to those bills.

Classify current AP evidence, not stale exports:

- A claim is paid only when there is a current linked AP bill for the claim amount and vendor, the bill is paid/current, and a cleared payment for the same bill amount/vendor exists.
- A claim is payable or eligible when the claim is approved, support is ready, and a current linked AP bill matches the claim amount and vendor and is not void or draft. A scheduled or processing payment is not a cleared payment; treat it as still open unless the prompt defines a different meaning.
- A claim is blocked or not ready when the claim is not approved, support is missing/partial for an unpaid release, no valid linked bill exists, the linked bill is void/draft, or the linked bill amount/vendor/account evidence does not match the claim.
- When a schema separates `paid_claim_ids` from `payable_claim_ids`, put settled claims only in the paid list. When a stale-export schema uses `eligible_claim_ids`, include both valid open claims and already-settled claims that can remain after correction.

Open AP balance should be computed from valid linked bills minus cleared payments only. Ignore void/draft bills, unrelated stale rows, and scheduled/processing payments when reducing balance. Use numeric USD values rounded to two decimals unless the template explicitly asks for integer cents.

For stale snapshot correction enums, choose the correction that explains the stale local row against current evidence:

- `current_snapshot_ok`: snapshot agrees with current valid bill/payment state.
- `mark_in_flight_payment`: current bill is valid and has a non-cleared payment in flight.
- `replace_with_matched_paid_bill`: snapshot points to old or mismatched AP evidence, but a different current paid bill and cleared payment match the claim.
- `exclude_amount_or_vendor_mismatch`: current linked AP evidence does not match claim amount/vendor or is otherwise the wrong AP item.
- `ignore_void_bill`: linked/current bill is void and should not drive release.
- `block_unapproved_claim`: current claim status/support makes the claim unreleasable regardless of AP rows.

If the prompt asks for close-log requirements, fetch close logs and include the relevant AP/Expense close log IDs for periods implicated by the stale correction or payment cleanup. Sort close-log IDs ascending.

## Vendor And Compliance Reviews

For each scoped business ID, fetch `/api/compliance/objects?business_id=...`; if fields are missing, join the ownership, registry, screening, and bank endpoints. Use the object's `vendor_id` to fetch `/api/vendors?vendor_id=...`.

Beneficial-owner counts are counts of unique names at or above the reporting threshold, usually 25%. When the same name appears multiple times, aggregate ownership by name before applying the threshold.

Map hard-stop flags from current evidence:

- `bank_closed`: `bank_account_status == "closed"`.
- `bank_name_mismatch`: `bank_account_status == "name_mismatch"`.
- `confirmed_pep`: `pep_status == "confirmed_pep"`.
- `expired_license`: `license_expiry` is before the task as-of/review date. For dedicated fields such as `expired_license_ids`, use strict date comparison. For onboarding `hard_stop_flags`, avoid overpopulating this flag for very recent in-month expiries unless the prompt or source context treats them as a release hard stop; if the license itself is missing, use `missing_required_documents`.
- `missing_required_documents`: `missing_fields` is non-empty.
- `sanctions_confirmed`: sanctions status is confirmed or matched.
- `screening_not_run`: PEP or sanctions screening status is `not_run`.
- `shell_company_suspected`: `shell_company_suspected` is true.
- `vendor_on_hold`: vendor status is `on_hold`.

Order flag lists alphabetically by enum value. Do not copy `review_status` as the final decision; decide from the underlying evidence.

For onboarding release decisions:

- `approve` when no hard-stop or information-gap flags remain.
- `awaiting_information` when the only blockers are missing documents or screening not run.
- `escalate` when evidence includes confirmed PEP, confirmed sanctions, shell suspicion, bank closed, bank name mismatch, vendor hold, invalid/expired licensing, or another hard identity/risk stop.
- `overall_release_ready` is true only when every scoped business is approved. Follow-up IDs are every non-approved business.

For account-change payment release:

- `bank_mismatch_ids` means bank status is exactly `name_mismatch`; do not include closed-bank records unless the template says to.
- `invalid_tax_ids` includes vendor tax IDs that differ from registry/compliance tax IDs or fail the expected tax-ID format.
- `expired_license_ids` use a strict date comparison against the review date.
- `risk_score_override_flags` includes risk scores greater than or equal to the prompt/template threshold, commonly 70.
- `release` requires active vendor, matching requested bank last4, verified bank status, valid/matching tax ID, current license, clear screening, no missing required evidence, and no risk override.
- `hold` fits remediable blockers such as bank closed/name mismatch, missing documents, screening not run, expired license, or risk override without a stronger escalation reason.
- `escalate` fits invalid tax identity, confirmed/possible PEP, confirmed sanctions, vendor hold, shell suspicion, or multiple severe identity inconsistencies. If both hold and escalation reasons are present, escalate.
- Review-queue IDs are every business not released.

## Prepaid Close Reconciliation

Use only invoice IDs, accounts, entity, and period in the scope payload/prompt.

For each selected prepaid invoice:

- Use `monthly_amortization` from the invoice record; do not recompute it from original amount unless the field is absent.
- A month counts if any part of the service period overlaps that month. This means a mid-month service start still receives that month's straight-line amortization when the source schedule does.
- `period_amortization` is the monthly amount when the close period overlaps the service period; otherwise zero.
- `cumulative_amortization_through_period` is monthly amount times the number of active service months from service start through the close period, capped by service end.
- `ending_balance = original_amount - cumulative_amortization_through_period`, rounded to two decimals. Preserve small rounding residuals.
- `default_missing_term_flag` is true for missing/default contract-term flags such as `missing_contract_dates`.
- `exception_flag` is true when any `data_quality_flags` are present.

For each account rollup:

- Sum selected invoice count, original amounts, period amortization, cumulative amortization, and schedule ending balance by account.
- Fetch the GL ending balance for the same entity, period, and account.
- `variance_amount = schedule_ending_balance - gl_ending_balance`.
- `variance_flag` is true when `abs(variance_amount)` exceeds the threshold in the scope payload; default to any nonzero variance only if no threshold is supplied.
- `has_default_missing_term_flag` is true when any invoice in the account has that flag.
- Use `requires_reconciliation` when there is a variance flag or default/missing-term issue, `variance_review` for below-threshold variances or non-term exceptions that still need review, and `reconciled` only when the account is clean.

Sort exception invoice lists as the template requires. Preserve selected invoice order for per-invoice result arrays when requested.

## Output Discipline

- Return one JSON object and no narrative when the prompt asks for JSON only.
- Match required top-level keys, enum values, and key order from the template. Use `top_level_order` when present.
- Sort ID lists ascending unless the template says to preserve input order.
- Keep all scoped IDs in required mapping fields, even when their balance is zero or their flag list is empty.
- Round currency to two decimals and counts to integers.
- Before final response, check that every decision is backed by current API records and every output field is derivable from the prompt, payloads, or API evidence.
