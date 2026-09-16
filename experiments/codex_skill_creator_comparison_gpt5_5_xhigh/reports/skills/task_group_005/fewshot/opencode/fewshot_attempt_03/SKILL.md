---
name: erp-finance-release-control
description: Use this skill for task_group_005 style ERP finance/compliance API tasks that ask for strict JSON decisions about reimbursement AP batches, stale AP exports, prepaid close reconciliations, vendor onboarding release, or payment release after account-change events. It helps join local batch payloads to the shared API, apply close/release-control rules, calculate currency fields, and return only schema-conforming JSON.
---

# ERP Finance Release Control

Use this when a task asks you to decide finance close or release posture from a local prompt/payload plus the shared ERP/compliance API. The API is the current system of record unless the prompt explicitly says otherwise; local CSV exports and batch files define scope and context.

## Operating Pattern

1. Read the prompt and every local payload. Treat `answer_template.json` as the output contract: keys, enum values, ordering, precision, and fixed required values come from the template.
2. Get the API base URL from the runner-provided `TASK_ENV_BASE_URL` or the prompt placeholder. Use only the task API, not local source data, to resolve current ERP/compliance facts.
3. Query exact-match filters by field name, and paginate when `total` exceeds returned `count`. Prefer `/api/...` endpoints, falling back to the non-`/api` aliases if needed.
4. Build a small evidence table before writing JSON: one row per claim, business, invoice, or account with the decisive source fields and final classification.
5. Emit exactly one JSON object, with no narrative. Sort IDs ascending unless the template says to preserve payload order. Output currency as numbers rounded to two decimals.

Optional helper: `scripts/fetch_task_group_005.py` fetches filtered API snapshots without third-party packages.

```bash
python skill/scripts/fetch_task_group_005.py --base-url "$TASK_ENV_BASE_URL" \
  --claim CLAIM_ID --business BUSINESS_ID --prepaid PREPAID_ID \
  --account 1250 --period YYYY-MM --entity "Entity Name" --out /tmp/task_snapshot.json
```

## Endpoint Map

- Claims: `/api/claims` or `/claims`.
- AP bills, payments, aging, close logs: `/api/ap/bills`, `/api/ap/payments`, `/api/ap/aging`, `/api/close/logs`.
- Vendors: `/api/vendors`.
- Compliance: `/api/compliance/objects`, plus `/api/compliance/ownership/{business_id}`, `/registry/{business_id}`, `/screening/{business_id}`, and `/bank/{business_id}` when a split-out field needs confirmation.
- Prepaids and GL: `/api/prepaids/invoices`, `/api/prepaids/gl-balances`.

Do not rely on a broad all-record dump if it is truncated. Query by the candidate IDs from the payload/prompt.

## Reimbursement/AP Batch Rules

Use these for reimbursement close reviews, stale AP snapshots, and AP payment batch eligibility.

### Current claim readiness

- Current claim records decide case readiness.
- A claim is case-ready for unpaid AP release only when it is approved, has an approval date, and has attached support.
- A claim with status other than approved/paid, a missing approval date, or missing/partial receipt support is not ready unless it is already fully settled by matched paid AP evidence.
- Distinguish case issues from AP evidence issues when the template has separate fields.

### Valid AP evidence

- Keep AP bill rows linked by `claim_id`; if a `bill_id` appears on multiple rows, keep the row whose `claim_id`, vendor, and amount match the target claim. Do not join by `bill_id` alone.
- Ignore `void` and `draft` bills for release/payable balances.
- A matched reimbursement bill normally has the current claim amount, matching claim/vendor evidence when a vendor is present, and a non-void status.
- Treat amount or vendor mismatches as AP evidence problems, even if the stale local snapshot looked plausible.
- Only `cleared` payments settle a bill. `scheduled` and `processing` payments are in-flight and do not reduce release-control open balance.

### Classifications

- Paid/settled: a current paid claim has a linked paid AP bill for the claim amount and cleared payments totaling the claim amount.
- Payable/open: a case-ready claim has a valid non-void AP bill for the claim amount, but no cleared payment has settled it.
- Blocked/not ready: case readiness fails, no valid linked AP bill exists, the current bill is void/draft, or the active bill has amount/vendor mismatch.
- Open AP balance by claim: sum valid linked non-void bill amounts minus cleared payments on those valid bill rows, floored at zero for output.
- For close status fields, use the template's precedence: blocked if any blocked item exists; otherwise open/payable when valid unpaid bills remain; otherwise ready/closed.

### Stale Snapshot Correction Labels

When a template asks for stale snapshot corrections, apply the first matching reason:

- `block_unapproved_claim`: current claim is not approved/paid or lacks required support.
- `ignore_void_bill`: current linked bill is void and should not drive release.
- `exclude_amount_or_vendor_mismatch`: active current bill does not match the claim amount/vendor.
- `replace_with_matched_paid_bill`: stale row points to the wrong bill but a current matched paid bill and cleared payment settle the claim.
- `mark_in_flight_payment`: valid current bill exists and payment is scheduled/processing rather than cleared.
- `current_snapshot_ok`: current API evidence agrees with the local snapshot and no correction is needed.

When close-log output is requested, fetch close logs and include the relevant AP/Expense close-log IDs that evidence the stale export refresh, support cleanup, or manual journal activity for the affected period. Sort close-log IDs ascending.

## Prepaid Close Rules

Use these for prepaid schedule to GL reconciliation.

1. Scope invoices from the local payload and preserve that order in invoice-level output when requested.
2. Query each selected prepaid invoice and the GL ending balance for each scoped account, entity, and close period.
3. Use invoice `monthly_amortization` as authoritative. For straight-line schedules, count whole calendar months inclusively from `service_start` month through the close period, capped at `service_end` month. Do not prorate partial months.
4. Current-period amortization is the monthly amortization if the close month falls within the service month range; otherwise zero.
5. Cumulative amortization through close is monthly amortization times active months through close, rounded to cents.
6. Ending balance is original amount minus cumulative amortization, rounded to cents. Preserve small rounding residuals instead of forcing zero unless the rounded result is exactly zero.
7. `default_missing_term_flag` is true for missing service dates/terms or a `missing_contract_dates` style quality flag.
8. `exception_flag` is true for any invoice data-quality flag, missing required schedule field, non-straight-line recognition in a straight-line task, or other schedule anomaly. A rounding residual alone is not an exception unless the source flags it.
9. Account rollups sum selected invoice results by account. Variance is schedule ending balance minus GL ending balance. Use the payload threshold for `variance_flag`.
10. Account status: `requires_reconciliation` when threshold variance or default/missing-term issues exist; `variance_review` for smaller nonzero variances or non-default exceptions; `reconciled` only when no variance and no exceptions remain.

## Vendor Onboarding Rules

Use these for vendor access or finance-risk onboarding release calls.

For each business ID:

- Query compliance object and vendor master record. Use specialized compliance endpoints if a split-out value must be confirmed.
- Count reportable UBOs as unique owner names with ownership percentage at or above 25%. Do not double-count duplicate names.
- Generate hard-stop flags only from the template's allowed enum values, sorted alphabetically.

Flag mapping:

- `bank_closed`: compliance bank account status is closed.
- `bank_name_mismatch`: compliance bank account status is name mismatch.
- `confirmed_pep`: screening PEP status is confirmed PEP.
- `expired_license`: available license expiry is before the batch as-of date; if the license document itself is missing, prefer `missing_required_documents`.
- `missing_required_documents`: compliance missing fields/documents are present.
- `sanctions_confirmed`: sanctions screening shows a confirmed match.
- `screening_not_run`: PEP or sanctions screening was not run.
- `shell_company_suspected`: compliance says shell company is suspected.
- `vendor_on_hold`: vendor master status is on hold.

Decision precedence:

- `approve`: no hard-stop flags.
- `awaiting_information`: only information-gathering flags are present, typically missing documents and/or screening not run.
- `escalate`: any substantive risk flag is present, such as bank closed/name mismatch, confirmed PEP, sanctions confirmed, shell suspicion, expired license, or vendor on hold.

Follow-up IDs are all non-approved businesses. Overall release readiness is true only when every business is approved.

## Account-Change Payment Release Rules

Use these when a batch lists account-change tickets, requested bank last-four values, and target business IDs.

For each target business:

- Join the local ticket to compliance object and vendor master by business/vendor ID.
- Compare requested bank last four to vendor `bank_account_last4`. A mismatch requires review even if it is not the same as compliance `bank_account_status`.
- `bank_mismatch_ids` should contain only businesses whose compliance bank account status is `name_mismatch`. Closed bank accounts still require review, but do not belong in that specific list unless the template says otherwise.
- `invalid_tax_ids` includes businesses where compliance/registry tax ID is malformed or does not match the vendor master tax ID.
- `expired_license_ids` includes businesses with available license expiry before the review/as-of date. Missing license documents drive review but are not an expired-license finding by themselves.
- `risk_score_override_flags` includes businesses with `risk_score >= 70`.
- `review_queue_ids` includes any business with bank mismatch/closed status, bank last-four mismatch, invalid tax, expired or missing license evidence, missing required documents, screening not run or not clear, PEP status other than none, shell suspicion, vendor not active/on hold, or risk-score override.

Decision precedence:

- `escalate`: invalid tax, confirmed or possible PEP, confirmed sanctions, shell suspicion, vendor on hold, or another severe compliance contradiction.
- `hold`: review-queue issues exist but no escalation trigger, such as bank closed/name mismatch, expired license, missing documents, screening not run, or risk override.
- `release`: no review-queue issues.

## Final Checks

- Confirm every required key is present and there are no extra keys when the template disallows them.
- Confirm enum strings exactly match the template.
- Confirm all required IDs from the prompt/payload are represented.
- Confirm all ordering rules: payload order for invoice result lists when requested, otherwise ascending ID order.
- Recompute totals from the evidence table immediately before final JSON.
