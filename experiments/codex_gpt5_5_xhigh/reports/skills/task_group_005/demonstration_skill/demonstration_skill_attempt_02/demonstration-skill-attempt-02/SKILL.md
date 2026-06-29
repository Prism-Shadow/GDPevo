---
name: task-group-005-fewshot-attempt-02
description: Solve PanofyBench task_group_005 finance/API fewshot tasks for reimbursement/AP close, stale AP batch refresh, vendor onboarding/release risk, prepaid close reconciliation, and account-change payment release. Use when Codex must read local scope/template payloads, query the shared ERP/compliance API, apply finance-control rules, and return strict JSON matching an answer_template.json.
---

# Task Group 005 Input/Output Solver

## Workflow

1. Read the prompt, local scope/batch payloads, and `answer_template.json`. Treat local payloads as candidate scope and output contract, not as the system of record.
2. Query the runner-provided API base URL. Check `/endpoints`; task_group_005 supports exact-match query parameters by field name plus `limit` and `offset`. `/api/...` and bare endpoints are aliases.
3. Fetch current records by requested IDs:
   - Claims: `/api/claims?claim_id=...`
   - AP bills: `/api/ap/bills?claim_id=...`
   - AP payments: `/api/ap/payments?bill_id=...`
   - Close logs: `/api/close/logs?...`
   - Compliance: `/api/compliance/objects?business_id=...`
   - Vendors: `/api/vendors?vendor_id=...`
   - Prepaids: `/api/prepaids/invoices?prepaid_invoice_id=...`
   - GL balances: `/api/prepaids/gl-balances?period=...`
4. Return only JSON. Preserve required top-level keys and order when the template specifies it. Sort ID lists ascending unless the template says to preserve payload order.

For localhost calls in a proxied shell, use `curl --noproxy '*'`.

## Reimbursement And AP Close

Use current claim, bill, and payment records together.

- A valid reimbursement AP bill must match the claim ID, USD amount, and vendor when the claim has a vendor. Ignore voided bills and bills whose amount/vendor/account clearly belong to a different AP item.
- Treat only `cleared` payments as settled cash. `processing` or `scheduled` payments leave an open AP balance.
- Put a claim in a paid/settled field only when a matching bill is paid and has a cleared payment for the claim amount.
- Put a claim in a payable/eligible open field when the claim is approved and has a valid open AP bill with no cleared full payment.
- Block claims that are unapproved, missing a valid AP link, attached only to void bills, or attached to mismatched AP rows. These usually also belong in owner-cleanup/CRM/remediation fields.
- Compute open AP balance only from valid AP bills for payable claims, less cleared payments. Invalid, voided, unapproved, or stale rows contribute `0.00`.
- Overall close status precedence: blocked items first; otherwise open payables/needs refresh if valid unpaid AP remains; otherwise ready/closed.

For stale AP snapshot tasks, use the local CSV only to explain corrections:

- `mark_in_flight_payment`: current bill is valid but payment is not cleared.
- `replace_with_matched_paid_bill`: stale row points to the wrong bill, while a current matching paid/cleared bill exists.
- `exclude_amount_or_vendor_mismatch`: linked AP row fails claim amount/vendor validation.
- `ignore_void_bill`: current or snapshot bill is void.
- `block_unapproved_claim`: claim itself is not approved, even if AP rows exist.
- `current_snapshot_ok`: current API evidence still matches the snapshot and is releasable.

If an AP refresh/close-log field is requested, include relevant AP close-log IDs supporting the refresh or correction, sorted ascending, and set the boolean consistently with whether such IDs are present.

## Vendor Onboarding And Release Risk

For each business ID, fetch the compliance object, then fetch the vendor by `vendor_id`. Do not copy `review_status` as the decision; make a release-control decision from evidence.

Hard-stop and review signals:

- `bank_account_status=name_mismatch` -> bank mismatch; `closed` -> closed bank.
- `vendor.status=on_hold` -> vendor hold.
- `pep_status=confirmed_pep` is a hard stop; `possible_pep` is escalation evidence for payment release.
- `sanctions_check_status=not_run` means screening not run; confirmed sanctions are a hard stop.
- `missing_fields` nonempty means missing required documents.
- `shell_company_suspected=true` is a hard stop.
- Compare `license_expiry` to the task `as_of_date`/review date for expired-license fields.
- Compare vendor and compliance `tax_id`; mismatches or malformed tax IDs are invalid-tax evidence.
- Count reportable UBOs as unique owner names with `ownership_pct >= 25`; duplicate names count once.
- `risk_score >= 70` belongs in risk override flags.

Decision posture:

- Approve/release only when bank, tax, license, screening, sanctions, PEP, shell, required-doc, vendor status, and requested bank account evidence are clean.
- Await information or hold for fixable gaps such as missing documents, screening not run, closed/mismatched bank, expired license, or high risk when no escalation trigger is present.
- Escalate for invalid tax, confirmed/possible PEP, sanctions, shell-company evidence, vendor hold, or multiple severe contradictions. If both hold and escalation signals exist, use escalation.
- Follow-up/review-queue IDs are all non-approved/non-release businesses.
- Overall release readiness is true only if every target business is approved/released.

## Prepaid Close Reconciliation

Use only the selected invoice IDs and target accounts from the local scope. Keep invoice result order exactly as the scope payload.

- Use the invoice record's `monthly_amortization` as the straight-line amount.
- A month counts when the service period overlaps that month; mid-month starts/ends still use the full monthly amount represented by the record.
- `march_amortization` is the monthly amount if the invoice is active in March 2025, otherwise `0.00`.
- `cumulative_amortization_through_march` is monthly amortization times active months from service start through March, capped at the original amount.
- `ending_balance = original_amount - cumulative_amortization_through_march`, rounded to two decimals.
- `default_missing_term_flag` is true when data quality flags show missing/defaulted contract terms, especially `missing_contract_dates`.
- `exception_flag` is true when `data_quality_flags` is nonempty.
- Account rollups sum selected invoices by account, then compare to the period GL ending balance. `variance_amount = schedule_ending_balance - gl_ending_balance`; `variance_flag` is true when absolute variance exceeds the scope threshold.
- Use `requires_reconciliation` for material variance, `variance_review` for nonmaterial exceptions or review-only differences, and `reconciled` only when the account is clean.

## Output Pitfalls

- Follow the template's units and precision. Most task_group_005 currency fields are numeric USD dollars with two decimals.
- Include only requested candidates or scoped invoices. Do not add API records outside the batch.
- Preserve field names exactly; do not add narrative text or extra properties.
- Use empty arrays, not omitted fields, when no IDs match a requested list.
- Re-query current API evidence when local snapshots, prompt notes, and API records disagree; the API wins.
