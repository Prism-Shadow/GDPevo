---
name: erp-finance-control-review
description: Use this skill for task_group_005 ERP finance API tasks, especially reimbursement-to-AP close reviews, stale AP batch refreshes, vendor onboarding or account-change release controls, prepaid close reconciliations, AP aging, payments, vendors, compliance, claims, bills, GL balances, and close-log checks. Trigger whenever the prompt asks for JSON decisions from the shared ERP finance API, even when local payloads look sufficient, because the API is the system of record and the templates have strict field, ordering, and precision rules.
---

# ERP Finance Control Review

Use this SOP to solve task_group_005 finance-control tasks from the shared API. The common shape is: a prompt gives a narrow batch, local payloads define scope and output shape, and the remote ERP API supplies current evidence. Local exports can be stale context; do not treat them as authoritative unless the prompt explicitly asks you to compare against them.

## First Pass

1. Read the prompt, every local input payload, and the answer template before querying. Extract:
   - Target IDs only: claim IDs, business IDs, invoice IDs, accounts, periods, entity, as-of date, review date, thresholds, and batch IDs.
   - Required top-level keys, enum values, list ordering, and numeric precision.
2. Use the runner-provided API base URL. If an environment note is present, prefer that value over prompt examples such as localhost. Do not read local environment source or data directories.
3. Start with `/health`, `/api/health`, or `/endpoints` if the API shape is uncertain. Object-list endpoints return `count`, `data`, `limit`, `offset`, and `total`.
4. Query only the scoped records. Endpoints support exact-match query parameters by field name plus `limit` and `offset`.
5. Treat current API records as the source of truth. Use local CSV or JSON snapshots only for scope, ticket context, stale-row correction labels, or requested metadata.
6. Keep evidence categories separate in your notes:
   - Case readiness evidence: claim status, receipt/support status, policy flags, approval dates.
   - AP/payment evidence: matching bills, bill status, amount/vendor match, payments and payment status.
   - Compliance evidence: bank, registry/license, screening, ownership, vendor, tax, risk.
   - Reconciliation evidence: invoice schedules, data-quality flags, GL balances, close logs.
7. Build the final object directly from the answer template. Return JSON only when requested. Do not add narrative text.

## API Habits

Use the `/api/...` routes when available, with the non-API route as a fallback only if needed.

- Claims: `/api/claims`, filter by `claim_id`.
- AP bills: `/api/ap/bills`, filter by `claim_id`, `bill_id`, `vendor_id`, `status`, or `account`.
- Payments: `/api/ap/payments`, filter by `bill_id`, `vendor_id`, or `status`.
- Vendors: `/api/vendors`, filter by `vendor_id`.
- Compliance aggregate: `/api/compliance/objects`, filter by `business_id`.
- Compliance detail: `/api/compliance/profile/{business_id}`, `/api/compliance/ownership/{business_id}`, `/api/compliance/registry/{business_id}`, `/api/compliance/screening/{business_id}`, `/api/compliance/bank/{business_id}`, `/api/compliance/risk/{business_id}`.
- Prepaids: `/api/prepaids/invoices`, filter by `prepaid_invoice_id`, `account`, `entity` when present.
- GL balances: `/api/prepaids/gl-balances`, filter by `entity`, `period`, and `account`.
- Close logs: `/api/close/logs`, filter by `area`, `period`, `status`, or `related_account`.

If an exact-match filter returns no rows, verify the field name and endpoint, then record the missing object as an exception instead of silently dropping it.

## Reimbursement and AP Close Reviews

For each candidate claim ID:

1. Query the claim by `claim_id`.
2. Query all AP bills with that `claim_id`.
3. For each bill, query payments by `bill_id`.
4. When a stale AP snapshot is supplied, compare it to the current API but let the API decide readiness.

Use these controls:

- A claim is ready for unpaid AP release only when the current claim is approved, support is complete enough for release, the currency is USD, and there is a valid matching non-void AP bill.
- A claim is settled only when a matching AP bill is `paid` and a cleared payment matches the bill or claim amount. Do not include settled claims in open AP balance totals.
- A valid reimbursement bill should have the same `claim_id`, the expected vendor when the claim has a vendor, the same currency, and an amount that matches the claim amount at cent precision. Mismatched vendor, mismatched amount, unrelated account context, missing bill, or void bill is AP evidence failure.
- `processing` or scheduled payments are not cleared. Treat them as open or in-flight according to the template wording.
- Partial or missing receipts, unapproved claim statuses, pending owner comments, or unresolved policy/support issues are case-readiness failures unless the task only asks whether a claim is already settled.
- Keep blocked case-cleanup IDs separate from AP/payment evidence fields when the template distinguishes them.

Common stale-snapshot correction labels:

- `current_snapshot_ok`: the current claim, bill, and payment evidence still supports the snapshot row.
- `mark_in_flight_payment`: current bill remains valid but a non-cleared payment is in process.
- `replace_with_matched_paid_bill`: the stale row points at the wrong bill or status, while current API has a matching paid bill and cleared payment.
- `exclude_amount_or_vendor_mismatch`: current AP evidence does not match the claim amount, vendor, or reimbursement context.
- `ignore_void_bill`: the current bill is void and should not support release.
- `block_unapproved_claim`: the current claim itself is not approved or still needs owner/support cleanup.

For close-log fields, query current close logs and include non-closed logs that relate to the requested AP, expense, or account issue. Set the boolean from whether any such IDs remain.

Batch status usually follows the template definition:

- If any requested item is blocked or not ready, use the blocked status value.
- Otherwise, if valid unpaid AP balances remain, use the open-payables or send-ready status value named by the schema.
- Otherwise, use the ready-to-close value named by the schema.

## Vendor Onboarding and Account-Change Release

For each scoped `business_id`:

1. Query the compliance aggregate object. Use detail endpoints if the aggregate is missing a needed field or you need to confirm one control domain.
2. Query the linked vendor by `vendor_id`.
3. If the local batch has account-change tickets, compare the ticket `vendor_id` and requested bank last4 against the current vendor record, but use compliance bank status for bank control flags when the schema defines them that way.

Control mappings:

- Reportable UBO count: count unique owner names with `ownership_pct >= 25`. Do not double-count duplicate name rows.
- Expired license: `license_expiry` before the as-of or review date. A future date is not expired.
- `bank_closed`: compliance `bank_account_status == "closed"`.
- `bank_name_mismatch`: compliance `bank_account_status == "name_mismatch"`.
- `confirmed_pep`: screening `pep_status == "confirmed_pep"`.
- `sanctions_confirmed`: sanctions status indicates a confirmed match.
- `screening_not_run`: sanctions or PEP screening is `not_run`.
- `shell_company_suspected`: compliance shell-company flag is true.
- `missing_required_documents`: `missing_fields` is non-empty.
- `expired_license`: license is expired as of the review date.
- `vendor_on_hold`: linked vendor status is `on_hold`.
- Invalid tax: tax ID is malformed for the local convention or the compliance tax ID conflicts with the linked vendor tax ID.
- Risk override: include IDs with `risk_score >= 70` when the template asks for risk override flags.

Decision posture:

- Approve or release only when vendor is active, bank is verified, tax evidence is valid and consistent, license is current, required documents are present, sanctions are clear, no confirmed PEP exists, no shell-company concern exists, and risk/review evidence does not require manual review.
- Hold or awaiting-information fits remediable gaps such as missing documents, not-run screening, possible PEP, not-started/in-review status, expired license needing renewal, or bank/tax evidence that needs AP/compliance review but is not a confirmed severe risk.
- Escalate fits confirmed PEP or sanctions, suspected shell company, closed or mismatched bank on a payment release, vendor on hold, invalid or conflicting tax evidence, high risk overrides, or any combination that makes release-control unsafe.

Do not copy `review_status` as the decision. It is evidence, not the release answer.

## Prepaid Close Reconciliation

Use scoped invoice IDs and accounts only.

1. Query every selected prepaid invoice by `prepaid_invoice_id`.
2. Query GL balances by `entity`, `period`, and each scoped account.
3. Preserve invoice ordering from the scope payload when the template requests it.

Schedule math:

- Use the API's `monthly_amortization`; do not recompute monthly amounts from original amount unless the field is missing and the template requires a fallback.
- For the close period, monthly amortization is the invoice monthly amount when the close month falls within the service term, including mid-month service starts and ends. Otherwise it is zero.
- Cumulative amortization through the close period is monthly amortization times the count of service months from the service-start month through the close period, clipped to the service term. Round to two decimals.
- Ending balance is original amount minus cumulative amortization, rounded to two decimals and not below zero unless the source data explicitly requires an over-amortized exception.
- Account schedule ending balance is the sum of selected invoice ending balances for that account, not the full API population.
- Variance is `schedule_ending_balance - gl_ending_balance`.
- Use the payload variance threshold when present; otherwise use the threshold specified by the prompt or template. Flag variance when the absolute variance exceeds the threshold.

Data-quality flags:

- Default or missing-term invoice flags come from missing service dates, missing term data, or source flags such as missing contract dates.
- Invoice exception flags include missing selected invoices, account outside scope, non-straight-line method when straight-line is required, and any source data-quality flag that affects close reliability.
- Account `has_default_missing_term_flag` is true when any selected invoice in that account has a default or missing-term flag.

Account status:

- `reconciled`: no variance flag and no selected-invoice exceptions requiring cleanup.
- `variance_review`: variance flag exists but invoice data is otherwise clean enough for a variance-only review.
- `requires_reconciliation`: missing invoices, missing/default terms, data-quality exceptions, missing GL balance, or variance combined with invoice exceptions.

## Output Discipline

- Follow the answer template exactly, including required constants such as `task_id`, `batch_id`, and `as_of_date`.
- Sort ID lists exactly as requested: usually ascending by ID, sometimes same order as the input scope.
- Sort enum flag lists alphabetically when the template says so.
- Use the template precision. If the prompt says cent-level USD and the schema says number precision 2, return dollars with two decimal places. Use integer cents only when the schema explicitly requires integer cents.
- Use booleans as JSON booleans, not strings.
- Include every required key even when the value is an empty list, empty object, zero, or false.
- Do not include additional properties when the template disallows them.
- Before finalizing, re-read the template and check: all scoped IDs accounted for, no unscoped IDs included, current API evidence used, stale context not over-trusted, numbers rounded once at output, and JSON parses cleanly.
