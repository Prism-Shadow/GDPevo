---
name: erp-finance-review
description: Solve finance-review tasks against the shared ERP/compliance API, including reimbursement/AP close batches, stale AP snapshot reconciliation, vendor onboarding release control, account-change payment release reviews, and prepaid close reconciliations. Use when a prompt provides a TASK_ENV_BASE_URL plus local payload templates/scope files and asks for a JSON decision or close report from current API records.
---

# ERP Finance Review

## Core Workflow

1. Read the prompt, answer template, and all local payload files for the task. Extract the requested IDs, period/as-of date, entity, account scope, thresholds, and required output ordering.
2. Treat the API as the system of record. Use local CSV/JSON payloads only for scope, stale context, and output schema.
3. Use the runner-provided base URL. Prefer `/api/...` endpoints, falling back to non-`/api` variants named in the prompt. `/endpoints` lists available paths; exact-match query parameters by field name are supported.
4. Query only records needed for the scoped IDs. Paginate with `limit` and `offset` if a collection result reports `total > count`.
5. Preserve the answer template exactly: required keys only when `additional_properties_allowed` is false, correct enum values, requested top-level order, and list ordering.
6. Use decimal arithmetic for money. Report USD amounts to two decimals unless the template asks for cents. Compare money after rounding to cents, but keep source amounts as authoritative.
7. Return JSON only unless the user explicitly requests explanation.

## API Map

- Claims: `/api/claims`, `/api/claims/{claim_id}`.
- AP bills: `/api/ap/bills`.
- AP payments: `/api/ap/payments`.
- AP aging: `/api/ap/aging`.
- Close logs: `/api/close/logs`.
- Vendors: `/api/vendors`.
- Compliance object rollups: `/api/compliance/objects`.
- Compliance details: `/api/compliance/ownership/{business_id}`, `/api/compliance/registry/{business_id}`, `/api/compliance/screening/{business_id}`, `/api/compliance/bank/{business_id}`.
- Prepaid invoices: `/api/prepaids/invoices`.
- Prepaid GL balances: `/api/prepaids/gl-balances`.

## Reimbursement And AP Batch Rules

Use these rules for reimbursement close, AP release, and stale snapshot tasks.

1. For each candidate claim, fetch the current claim, all bills with that `claim_id`, payments for relevant bill IDs, and any close logs requested by the template.
2. A claim is owner-clean only when the current claim status is releasable and support is complete. Treat `approved` with `receipt_status: attached` as releasable for unpaid claims. Treat `submitted`, `needs_receipt`, `rejected`, missing approval, missing receipts, or partial receipts as not owner-clean unless the claim is already paid with matching paid AP evidence.
3. A bill is valid AP evidence for a claim only when it is not `void` or `draft`, the amount equals the claim amount, currency matches, and the vendor matches when the claim has a vendor. Ignore bills with amount or vendor mismatches even if they carry the candidate claim ID.
4. A claim is paid only when a valid bill has `status: paid` and a cleared payment for the same bill/vendor/amount. Scheduled or processing payments do not make a claim paid.
5. A claim is open payable when it is owner-clean, has a valid unpaid bill in `approved` or `scheduled` status, and has no matching cleared full payment. Open AP balance is valid bill amount minus cleared payments only; do not subtract scheduled or processing payments.
6. A claim is blocked/not ready when owner cleanup is needed, no valid AP bill exists, only void/draft AP rows exist, or AP rows mismatch amount/vendor. Keep owner cleanup fields separate from AP/payment evidence fields when the template distinguishes them.
7. For stale AP snapshots, classify each candidate from current API data, not from the snapshot. Use snapshot rows only to explain correction codes:
   - `current_snapshot_ok`: stale row still agrees with current claim, bill, and payment state.
   - `mark_in_flight_payment`: current valid bill has a non-cleared payment or the stale row misses current in-flight payment evidence.
   - `replace_with_matched_paid_bill`: stale row points at old AP evidence but current data has a different matched paid bill with cleared payment.
   - `exclude_amount_or_vendor_mismatch`: current AP rows for the claim do not match the claim amount/vendor.
   - `ignore_void_bill`: the relevant AP row is void.
   - `block_unapproved_claim`: the current claim itself is not releasable.
8. For close-log fields, inspect `/api/close/logs` for records whose area, period, and message match the prompt's requested AP refresh, cleanup, or close support context. Return matching IDs sorted as the template requires.
9. Overall status depends on the template. For close-status templates, use `blocked` if any scoped item is blocked, otherwise `open_payables` if valid unpaid bills remain, otherwise `ready_to_close`. For stale snapshot release templates, use `needs_ap_refresh` when current reconciliation requires snapshot corrections or close-log support; use `ready_to_send` only when all current rows are clean and unchanged; reserve `blocked` for batches with no releasable path or when the prompt defines any not-ready item as blocking.

## Vendor Onboarding Release Control

Use these rules for onboarding decisions with `approve`, `awaiting_information`, and `escalate`.

1. For each scoped business ID, fetch the compliance object and, when needed, the ownership, registry, screening, bank, and vendor records.
2. Count reportable UBOs as unique owner names with `ownership_pct >= 25`. Duplicate rows for the same name count once.
3. Build hard-stop flags from current fields:
   - `bank_closed`: bank account status is `closed`.
   - `bank_name_mismatch`: bank account status is `name_mismatch`.
   - `confirmed_pep`: PEP status is `confirmed_pep`.
   - `expired_license`: license expiry is before the applicable review/as-of date. For monthly onboarding close prompts, treat licenses expiring during the same calendar month as the as-of date as current unless the prompt asks for strict daily comparison.
   - `missing_required_documents`: `missing_fields` is non-empty.
   - `sanctions_confirmed`: sanctions status indicates a confirmed match or hit.
   - `screening_not_run`: PEP or sanctions screening status is `not_run`.
   - `shell_company_suspected`: ownership record indicates shell-company suspicion.
   - `vendor_on_hold`: vendor status is `on_hold`.
4. Sort each business's hard-stop flags alphabetically by enum value.
5. Decision:
   - `approve` when no hard-stop flags apply.
   - `awaiting_information` when only information-gathering flags apply, especially missing required documents or screening not run, and no severe escalation flag is present.
   - `escalate` when any severe flag is present: bank closed, bank name mismatch, confirmed PEP, sanctions confirmed, shell-company suspicion, vendor on hold, or expired license.
6. Follow-up business IDs are all non-approved businesses, sorted ascending. Overall release is ready only when every business is approved.

## Account-Change Payment Release

Use these rules for account-change or payment-release risk reviews with `release`, `hold`, and `escalate`.

1. Use the local account-change payload for target business IDs, ticket/vendor IDs, requested bank last-four values, requested release amounts, and review date.
2. Fetch the vendor by `vendor_id` and current compliance records by `business_id`.
3. Sort `target_business_ids` and all output ID lists ascending by business ID unless the template says otherwise.
4. Populate diagnostic lists directly from source evidence:
   - `bank_mismatch_ids`: compliance bank status is `name_mismatch`; do not include `closed` here unless the template says to.
   - `invalid_tax_ids`: registry/compliance tax ID is missing, malformed, or differs from the vendor tax ID.
   - `expired_license_ids`: license expiry is strictly before the review/as-of date.
   - `risk_score_override_flags`: `risk_score >= 70`.
   - `review_queue_ids`: every business whose decision is not `release`.
5. Treat requested bank last-four mismatches, closed bank accounts, missing required documents, not-run screening, expired licenses, bank-name mismatches, and high risk scores as review blockers.
6. Decision:
   - `release` only when vendor is active, requested bank details match the vendor record, bank status is verified, tax ID is valid and consistent, license is current, screening is clear or none, no shell/sanctions/PEP escalation exists, and risk score is below the override threshold.
   - `escalate` for identity/compliance severity such as invalid tax ID, confirmed or possible PEP requiring review, sanctions confirmed, vendor on hold, shell-company suspicion, or a combination of severe blockers.
   - `hold` for remediable operational blockers such as closed/name-mismatched bank status, requested bank mismatch, missing documents, not-run screening, expired license, or risk override when no escalation trigger is present.

## Prepaid Close Reconciliation

Use these rules for prepaid close tasks.

1. Read the scope payload for entity, close period, account list, selected prepaid invoice IDs, and variance threshold. Keep `selected_invoice_ids` and `invoice_results` in the same order as the scope payload.
2. Fetch selected invoices from `/api/prepaids/invoices` and GL balances from `/api/prepaids/gl-balances` for the close period and entity.
3. Reconcile only scoped accounts. Ignore non-scoped invoices or GL accounts unless the prompt asks to report them as exceptions.
4. For straight-line records, use the source `monthly_amortization` amount. A service month counts when the close month overlaps the invoice service period; do not prorate partial first or last months unless the prompt explicitly says to.
5. Cumulative amortization through the close period is `monthly_amortization * number_of_service_months_through_close`, bounded by the service start and service end months. Round to two decimals. Ending balance is `original_amount - cumulative_amortization_through_close`, rounded to two decimals.
6. `march_amortization` or equivalent period amortization is the monthly amount when the close month is in the service period; otherwise it is zero.
7. `exception_flag` is true when source `data_quality_flags` is non-empty or required schedule fields are missing/inconsistent. `default_missing_term_flag` is true for defaulted or missing-term/date flags such as `missing_contract_dates`, missing terms, or default-term indicators.
8. Account rollups sum only selected invoices by account:
   - selected invoice count
   - original amount total
   - period amortization total
   - cumulative amortization total
   - schedule ending balance
   - GL ending balance
   - variance amount as schedule ending balance minus GL ending balance
9. `variance_flag` is true when `abs(variance_amount)` exceeds the scope threshold. `has_default_missing_term_flag` is true when any selected invoice in the account has a default/missing-term flag.
10. Account status: use `requires_reconciliation` when variance is over threshold or default/missing-term issues exist; use `variance_review` for non-default invoice exceptions with no material GL variance; otherwise use `reconciled`.

## Output Hygiene

- Sort IDs by the exact key requested, usually lexical ascending by claim ID, business ID, invoice ID, or close-log ID.
- Use empty lists and zero amounts when the schema requires keys but no evidence applies.
- Do not copy source review statuses into decisions. Decisions must reflect release/close control based on current evidence.
- Do not include training IDs, answer records, or unexplained narrative in final JSON.
