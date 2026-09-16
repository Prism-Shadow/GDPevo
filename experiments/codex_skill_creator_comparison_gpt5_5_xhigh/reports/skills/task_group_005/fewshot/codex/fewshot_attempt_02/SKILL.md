---
name: erp-finance-risk-review
description: Solve ERP/compliance JSON API finance-risk tasks for reimbursement/AP close review, stale AP export refresh, vendor onboarding release control, account-change payment release, and prepaid close reconciliation. Use when a prompt provides a runner API base URL plus local payloads or answer templates and asks for current-system JSON decisions from task_group_005-style claims, AP bills/payments, vendors, compliance, prepaids, GL balances, or close logs.
---

# ERP Finance Risk Review

## Core Workflow

1. Read the prompt, every local payload, and the answer template before querying.
2. Use the runner-provided API base URL as the system of record. Prefer `/api/...` endpoints, but fall back to the non-`/api` equivalents named by the prompt or `/endpoints`.
3. Fetch only records in scope. The API supports exact-match query parameters by field name plus `limit` and `offset`; paginate when totals exceed the first page.
4. Treat local snapshots as scope/context only. Current API claim, bill, payment, vendor, compliance, prepaid, GL, and close-log records override stale local exports.
5. Preserve the answer template exactly: required keys, enum values, list order, numeric precision, and JSON-only output.
6. Sort ID lists as the template says. When the template says ascending by ID, use lexical ascending order.

Use `scripts/finance_api_helper.py` when useful:

```bash
python3 skill/scripts/finance_api_helper.py claims --base-url "$TASK_ENV_BASE_URL" --claim-ids CLM-1,CLM-2
python3 skill/scripts/finance_api_helper.py compliance --base-url "$TASK_ENV_BASE_URL" --business-ids BUS-1,BUS-2 --as-of-date 2025-06-01 --account-change-json input/payloads/account_change_batch.json
python3 skill/scripts/finance_api_helper.py prepaids --base-url "$TASK_ENV_BASE_URL" --scope-json input/payloads/prepaid_close_scope.json
```

The helper emits generic evidence and suggested classifications. Adapt its output to the exact task template; do not add fields the template does not allow.

## Claim And AP Review

Fetch claims from `/api/claims`, AP bills from `/api/ap/bills`, payments from `/api/ap/payments`, and close logs from `/api/close/logs` when the prompt mentions close-log evidence.

Use current records to classify each candidate claim:

- A valid reimbursement bill is linked by `claim_id`, is not `void`, has USD amount equal to the claim amount, and has matching vendor when both claim and bill provide vendor IDs.
- A claim is paid only when a valid bill is `paid` and cleared payments for that bill cover the bill amount. Scheduled or processing payments are not cleared.
- Open AP balance is the valid non-void bill amount less cleared payments, floored at zero and rounded to two decimals. Ignore void bills and amount/vendor mismatches.
- A claim can remain payable/eligible when the claim is approved, receipt support is attached, and it has a valid unpaid AP bill with remaining balance or in-flight payment evidence.
- Block owner cleanup when the claim is not approved/paid, receipt support is missing or partial for an unpaid claim, no valid AP link exists, the linked bill is void, or the current bill amount/vendor does not match the claim.
- Keep reimbursement case issues separate from AP/payment evidence issues if the template has separate fields.

For stale AP snapshot tasks, assign correction labels from current evidence:

- `replace_with_matched_paid_bill`: a current valid paid bill and cleared payment now settle the claim.
- `mark_in_flight_payment`: a current valid bill remains open and has scheduled or processing payment evidence, or the bill itself is scheduled.
- `ignore_void_bill`: the snapshot row points to a bill that is currently void and no current valid bill replaces it.
- `exclude_amount_or_vendor_mismatch`: current AP evidence exists but does not match the claim amount or vendor.
- `block_unapproved_claim`: the current claim status is not approved/paid.
- `current_snapshot_ok`: none of the above corrections are needed.

For batch status, follow the template wording. In reimbursement close templates, any blocked item makes the batch `blocked`; otherwise open valid unpaid bills imply `open_payables`, and no blocked/open items imply `ready_to_close`. In stale-export refresh templates, use `needs_ap_refresh` when current evidence requires AP snapshot corrections even if some claims are not ready.

## Vendor And Compliance Review

Fetch compact records from `/api/compliance/objects?business_id=...` and the linked vendor from `/api/vendors?vendor_id=...`. Use split endpoints (`ownership`, `registry`, `screening`, `bank`) when the prompt asks for named evidence or the compact object is incomplete.

Onboarding release-control rules:

- Count reportable UBOs as unique owner names with `ownership_pct >= 25`.
- Add hard-stop flags alphabetically:
  - `bank_closed` when `bank_account_status == "closed"`.
  - `bank_name_mismatch` when `bank_account_status == "name_mismatch"`.
  - `confirmed_pep` when `pep_status == "confirmed_pep"`.
  - `expired_license` when `license_expiry` is before the prompt as-of month and the license document itself is not listed as missing. If a template gives an exact `comparison_date`, use the exact date instead.
  - `missing_required_documents` when `missing_fields` is non-empty.
  - `sanctions_confirmed` when sanctions status indicates a confirmed match.
  - `screening_not_run` when PEP or sanctions screening is `not_run`.
  - `shell_company_suspected` when the ownership record says true.
  - `vendor_on_hold` when the vendor status is `on_hold`.
- Decide `approve` only with no hard-stop flags. Decide `awaiting_information` when the only flags are missing documents and/or screening not run. Decide `escalate` for any severe flag such as bank closed/name mismatch, confirmed PEP, expired license, sanctions confirmed, shell-company suspicion, or vendor hold.
- Follow-up business IDs are all non-approved businesses. Overall release readiness is true only when every scoped business is approved.

Account-change payment-release rules:

- Compare the local requested bank last four to the vendor record, and use compliance `bank_account_status` for bank status lists. `bank_mismatch_ids` means compliance status `name_mismatch`; a `closed` bank is a review blocker but not a name-mismatch ID.
- Treat tax as invalid when the compliance tax ID does not match the vendor tax ID or is malformed for the source pattern.
- Treat licenses as expired when `license_expiry` is before the review/as-of date and the license document itself is not listed as missing; a missing license is a document follow-up instead.
- Flag risk overrides when `risk_score >= 70`.
- Decide `release` only when vendor status is active, requested bank last four matches the vendor bank, bank status is verified, tax and license are valid, screening is clear, required documents are present, no confirmed PEP/sanctions/shell-company issue exists, and risk is below the override threshold.
- Decide `escalate` for confirmed PEP, sanctions confirmed, shell-company suspicion, vendor hold, or invalid tax. Decide `hold` for operational blockers without escalatory flags, such as bank closed/name mismatch, requested-bank mismatch, missing documents, screening not run, expired license, or risk override.
- Review queue IDs are all non-release businesses. Sort every ID list as the template requests.

## Prepaid Close Reconciliation

Fetch invoices from `/api/prepaids/invoices` and GL balances from `/api/prepaids/gl-balances`. Scope to the payload invoice IDs, entity, accounts, and close period.

Use the invoice record’s `monthly_amortization` for straight-line schedules:

- The period amortization is the monthly amount when the close period month is within the service-start and service-end months, inclusive; otherwise it is zero.
- Cumulative amortization through the close period is monthly amount times the count of active service months from service start through the close period, capped to the invoice term and not below zero.
- Ending balance is original amount minus cumulative amortization, rounded to two decimals and not below zero.
- `default_missing_term_flag` is true when data quality flags indicate missing contract dates, default term, or missing term.
- `exception_flag` is true for any invoice data-quality flag, unsupported recognition method, missing service dates, or other schedule-quality issue.

For each account, roll up selected invoice count, original amount, period amortization, cumulative amortization, and schedule ending balance. Join the GL ending balance for the same entity/period/account. Variance is `schedule_ending_balance - gl_ending_balance`; flag it when absolute variance exceeds the payload threshold. Use `requires_reconciliation` for material variances or default/missing-term issues, `variance_review` for non-material exceptions requiring review, and `reconciled` only when variance and exception checks are clear.
