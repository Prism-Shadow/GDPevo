---
name: erp-finance-control-review
description: Solve ERP finance-control review tasks that require querying a runner-provided JSON API and returning strict JSON. Use for reimbursement/AP batch close, stale AP snapshot reconciliation, vendor onboarding or account-change release risk, and prepaid close reconciliation tasks involving claims, bills, payments, vendors, compliance records, prepaid invoices, GL balances, and answer templates.
---

# ERP Finance Control Review

## Core Workflow

1. Read the prompt, local payloads, and answer template before querying. Treat payloads as scope and schema contracts; treat the API as the current system of record unless the prompt says otherwise.
2. Use the runner-provided API base URL. Call `/endpoints` first when unsure. Prefer `/api/...` endpoints, and use exact-match query parameters by field name where possible.
3. Fetch only records needed for the scoped IDs, but paginate with `limit` and `offset` if a query may return more than one page.
4. Build a small evidence table per scoped claim, business, invoice, account, or close log. Do not rely on a source `review_status` alone; derive decisions from current supporting records.
5. Return only JSON matching the template. Preserve required top-level keys, required constant values, list ordering, enum values, numeric precision, and object key coverage.

Common endpoints:

- Claims: `/api/claims`, `/claims`
- AP bills, payments, aging: `/api/ap/bills`, `/api/ap/payments`, `/api/ap/aging`
- Vendors: `/api/vendors`
- Compliance: `/api/compliance/objects`, `/api/compliance/ownership/{business_id}`, `/api/compliance/registry/{business_id}`, `/api/compliance/screening/{business_id}`, `/api/compliance/bank/{business_id}`
- Prepaids and GL: `/api/prepaids/invoices`, `/api/prepaids/gl-balances`
- Close logs: `/api/close/logs`

## Output Discipline

- Sort ID lists exactly as the template says. If it says ascending by ID, sort lexicographically by the full ID string.
- If the template says "same order as payload", preserve the payload order.
- Use two decimal numbers for currency fields unless the template asks for cents. For cents, multiply dollars by 100 and round to an integer.
- Include every required candidate key in keyed objects, even when the value is `0.0`, `false`, or an empty list.
- Do not copy template metadata such as `type`, `description`, or `allowed_values` into the answer.

## Reimbursement and AP Claim Batches

For scoped claim IDs:

1. Fetch each claim by `claim_id`.
2. Fetch linked AP bills by `claim_id`.
3. Fetch payments for each linked `bill_id`.
4. If the prompt mentions stale exports or close logs, also read the local snapshot and query close logs; use the API to override stale snapshot rows.

Classify evidence this way:

- A claim is release-ready only when the current claim is approved or already paid, case support is sufficient for release, and there is either a valid open reimbursement bill or a valid settled bill.
- Case blockers include unapproved claim statuses such as submitted, rejected, or needs-receipt, missing or partial support on an unpaid release, and missing AP linkage for an unpaid approved claim.
- A valid AP bill must be linked to the claim, non-void, in a payable or settled status, and match the claim amount and vendor when those values are present. Ignore voided bills and rows with amount or vendor mismatches.
- A settled claim needs a valid paid bill and a cleared payment matching that bill and amount. Scheduled or processing payments do not clear open AP.
- Open AP balance is the sum of valid non-void bill amounts minus cleared payments. Do not count invalid, mismatched, void, or stale rows.

When a stale AP snapshot is part of the task, map the current evidence to correction enums if requested:

- `current_snapshot_ok`: snapshot row still matches current claim, bill, and payment evidence.
- `mark_in_flight_payment`: valid bill remains open because payment evidence exists but is not cleared.
- `replace_with_matched_paid_bill`: stale row points to the wrong bill, but another current valid paid bill and cleared payment settle the claim.
- `exclude_amount_or_vendor_mismatch`: linked or snapshot AP row does not match current claim amount or vendor.
- `ignore_void_bill`: linked or snapshot AP row is void.
- `block_unapproved_claim`: current claim is not approved or paid, regardless of stale AP evidence.

For close statuses, follow the template definitions. A common pattern is: any blocked claim makes a close batch `blocked`; otherwise unpaid valid bills make it `open_payables` or an AP-refresh equivalent; all settled claims make it ready. For stale-snapshot templates, use a refresh status when current API evidence differs from the snapshot even if some claims remain eligible.

## Vendor and Compliance Release

For each scoped business ID:

1. Fetch the compliance object by `business_id`.
2. Fetch ownership, registry, screening, and bank details if available. Use the compliance object as a compact source, but subresources can confirm fields.
3. Fetch the vendor by the compliance `vendor_id` when vendor status, bank last4, or vendor tax ID matters.

Reusable controls:

- Reportable UBO count: count unique beneficial-owner names with `ownership_pct >= 25`. Deduplicate names before counting.
- `bank_closed`: `bank_account_status == "closed"`.
- `bank_name_mismatch`: `bank_account_status == "name_mismatch"`.
- `confirmed_pep`: `pep_status == "confirmed_pep"`.
- `sanctions_confirmed`: sanctions status indicates a confirmed sanctions hit.
- `screening_not_run`: PEP or sanctions screening status is `not_run`.
- `shell_company_suspected`: ownership evidence says shell-company suspected.
- `vendor_on_hold`: current vendor status is `on_hold`.
- `missing_required_documents`: `missing_fields` is non-empty. If the missing field is the license, use this instead of double-counting the same issue as an expired license.
- `expired_license`: license expiry is before the task as-of or review date and the license is present.
- Invalid tax evidence includes a missing or malformed tax ID, or a mismatch between vendor tax ID and registry/compliance tax ID.
- Account-change bank evidence should also compare requested bank last4 from the local payload with current vendor bank last4 when both are present.

Decision patterns:

- Approve or release only when no review-triggering control issues remain.
- Use awaiting-information or hold for remediable issues such as missing documents, screening not run, bank mismatch, closed bank, expired license, or high risk score without stronger escalation evidence.
- Escalate for confirmed PEP, confirmed sanctions, shell-company suspicion, vendor hold, invalid tax evidence, or combinations of serious release-control failures.
- For account-change batches, risk score override flags use `risk_score >= 70` when the template asks for them.
- Review queue or follow-up lists should include every business whose decision is not approve/release, plus any business with a requested flag category.

## Prepaid Close Reconciliation

Use the local scope payload for entity, close period, accounts, selected invoice IDs, and variance threshold.

For each selected prepaid invoice:

1. Fetch by `prepaid_invoice_id`.
2. Keep only scoped accounts unless the prompt says to report mismatches.
3. Use the invoice `monthly_amortization`; do not recalculate a different straight-line amount from dates unless monthly amortization is absent.
4. Treat a service month as active when the close period month overlaps the service-start through service-end month range. Do not prorate partial months.
5. Current-period amortization is monthly amortization if the period is active, otherwise `0.00`.
6. Cumulative amortization through the close period is monthly amortization times the number of active months from service start through the close period, capped at the service-end month.
7. Ending balance is original amount minus cumulative amortization.

Flagging:

- `default_missing_term_flag` is true for missing or defaulted contract/service terms, including data-quality flags such as `missing_contract_dates`.
- `exception_flag` is true when any invoice-level data-quality flag is present or required schedule fields are missing.
- Account `variance_amount` is schedule ending balance minus GL ending balance.
- `variance_flag` is true when absolute variance exceeds the scope threshold, or when the template defines a different threshold.
- Use `requires_reconciliation` for material variance. Use `variance_review` for non-material exceptions that still need review. Use `reconciled` only when the account has no material variance and no unresolved exceptions.

Round invoice and account amounts to two decimals at output time. For rollups, sum the rounded invoice-level amounts used in the output unless the prompt explicitly requires unrounded intermediate sums.
