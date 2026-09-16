# Control Review Workflows

## API Evidence

Use current API data for decisions. Typical endpoints are:

- Claims: `/api/claims` or `/api/claims/{claim_id}`
- AP bills and payments: `/api/ap/bills`, `/api/ap/payments`, and sometimes `/api/ap/aging`
- Vendors: `/api/vendors`
- Compliance: `/api/compliance/objects`, plus direct ownership, registry, screening, and bank endpoints when present
- Prepaids: `/api/prepaids/invoices` and `/api/prepaids/gl-balances`
- Close logs: `/api/close/logs`

Collection endpoints support exact-match query parameters by field name and may return `data`, `total`, `limit`, and `offset`. Fetch all relevant pages if `total` exceeds the returned `count`.

## Reimbursement and AP Close

For each scoped claim:

1. Fetch the current claim by `claim_id`.
2. Fetch AP bills where `claim_id` equals the claim ID.
3. Fetch payments for every candidate bill ID.
4. If the template asks about stale snapshots, compare the local snapshot row to current API records and classify the correction from current evidence.
5. If the template asks for close logs, fetch current close logs and include only IDs relevant to the requested AP, expense, treasury, period, or refresh context.

Classify records with these rules:

- Claim case readiness: the claim must be approved or already paid, have USD currency when the template asks for USD, and have adequate support. Missing or partial support is a case cleanup issue unless a matched paid bill and cleared payment fully settle the claim.
- Matching AP bill: use non-void current bills linked to the claim. A valid reimbursement bill should match the claim amount and vendor when a vendor is present. Draft, void, missing, amount-mismatched, vendor-mismatched, or unrelated-account bills do not make a claim payable.
- Paid claim: require a current paid bill with a cleared payment for the bill or claim amount. Scheduled or processing payments are in flight, not cleared.
- Open payable: require a valid current open bill, normally `approved` or `scheduled`, without a cleared full payment. Its open balance is bill amount minus cleared payments, never below zero.
- Blocked or not ready: use when the claim is not approved, support is unresolved, no valid current bill exists, the only bill is void/draft, or current bill evidence mismatches claim evidence.

For stale AP snapshot correction enums, derive from the current-vs-snapshot difference:

- `current_snapshot_ok`: local row still matches the current open-bill posture.
- `mark_in_flight_payment`: the current bill is valid but payment evidence is scheduled or processing.
- `replace_with_matched_paid_bill`: the stale row points to an old or wrong bill, while a current matched paid bill and cleared payment settle the claim.
- `exclude_amount_or_vendor_mismatch`: the current bill does not match the claim amount or vendor.
- `ignore_void_bill`: the current linked bill is void.
- `block_unapproved_claim`: the current claim is not approved or lacks required claim-side support.

Batch status should follow the template wording. For close batches, any blocked claim normally makes the batch `blocked`; otherwise open valid bills make it an open-payables status, and all cleared items make it ready to close. For stale snapshot refresh tasks, use the refresh status when current API evidence can identify AP corrections even if some candidate rows are not ready.

## Vendor Onboarding Finance-Risk Release

For each scoped business:

1. Fetch the compliance object by `business_id`.
2. Fetch the linked vendor by `vendor_id`.
3. Use direct ownership, registry, screening, or bank endpoints when the aggregate compliance object is absent or the prompt asks for source-specific checks.

Reportable UBO count is the number of unique owner names with any ownership percentage at or above 25 percent. Deduplicate repeated names before counting.

Map hard-stop flags from current evidence:

- `bank_closed`: compliance bank account status is `closed`.
- `bank_name_mismatch`: compliance bank account status is `name_mismatch`.
- `confirmed_pep`: PEP status is `confirmed_pep`.
- `sanctions_confirmed`: sanctions status indicates a confirmed match.
- `screening_not_run`: sanctions or PEP screening has not been run.
- `shell_company_suspected`: shell-company evidence is true.
- `missing_required_documents`: required fields or documents are missing.
- `expired_license`: authoritative registry/license evidence is expired as of the review date. If license evidence is missing, use the missing-document flag unless the template explicitly asks for both.
- `vendor_on_hold`: vendor status is `on_hold`.

Decision posture:

- `approve`: no hard-stop flags remain.
- `awaiting_information`: only remediable information gaps remain, such as missing required documents or screening not run, and no severe risk flag is present.
- `escalate`: severe risk is present, including confirmed PEP, confirmed sanctions, bank closed or name mismatch, shell-company suspicion, vendor hold, or expired authoritative license evidence.

`follow_up_business_ids` are all non-approved businesses. `overall_release_ready` is true only when every scoped business is approved.

## Prepaid Close

Use the local close-scope payload for entity, period, account list, selected invoice IDs, and variance threshold. Fetch current prepaid invoices and GL balances for that entity and period.

For each selected invoice:

1. Keep `selected_invoice_ids` and `invoice_results` in the same order as the scope payload unless the template says otherwise.
2. Use the record's `monthly_amortization`; do not recompute it from original amount and term.
3. Count amortization months inclusively from the invoice service-start month through the close period, capped at the service-end month. If the close period is before service start, use zero months.
4. Current-period amortization is the monthly amount when the close period overlaps the service period; otherwise it is zero.
5. Cumulative amortization is monthly amount times counted months, rounded to two decimals.
6. Ending balance is original amount minus cumulative amortization, rounded to two decimals. Preserve small cent differences caused by straight-line rounding.
7. `default_missing_term_flag` is true for missing or default term flags such as `missing_contract_dates`.
8. `exception_flag` is true when any data-quality flag is present, when required invoice data is missing, or when the recognition method is not the expected straight-line method.

For each account rollup:

- Sum selected invoices for that account only.
- Compare `schedule_ending_balance` to the current GL ending balance.
- `variance_amount` is schedule ending balance minus GL ending balance.
- `variance_flag` is true when absolute variance exceeds the scope/template threshold.
- `has_default_missing_term_flag` is true when any selected invoice for the account has the default or missing-term flag.
- Use `reconciled` only when there is no variance and no account-level exception. Use `variance_review` for reviewable exceptions or immaterial variance. Use `requires_reconciliation` when variance exceeds threshold, GL evidence is missing, or default/missing-term issues affect the account.

## Account-Change Payment Release

Use the account-change payload for target business IDs, ticket vendor IDs, requested bank last4 values, and review date. Fetch current vendor and compliance evidence for every target.

Field rules:

- `target_business_ids`: sort ascending if required by the template.
- `bank_mismatch_ids`: businesses whose compliance bank status is `name_mismatch`. Treat `closed` bank status as a review issue even when it is not part of this specific list.
- `invalid_tax_ids`: vendor and compliance tax IDs are missing, malformed for the task's expected pattern, or disagree.
- `expired_license_ids`: license expiry is before the review/as-of date.
- `risk_score_override_flags`: risk score is at or above 70 unless the prompt gives a different threshold.
- `review_queue_ids`: every business that is not releasable because of bank, tax, license, document, screening, vendor status, PEP, sanctions, shell-company, or high-risk evidence.

Decision posture:

- `release`: current vendor is active, requested bank last4 matches the current vendor bank, compliance bank is verified, tax IDs align, license is current, screening is clear, no PEP/sanctions/shell-company issue is present, and risk score is below the override threshold.
- `hold`: remediable operational or evidence issues block release, such as bank mismatch/closed status, missing license/documents, screening not run, or high risk without a severe integrity mismatch.
- `escalate`: severe integrity or compliance issues exist, especially tax ID mismatch, vendor hold, confirmed or possible PEP requiring escalation, confirmed sanctions, shell-company suspicion, or multiple severe blockers.
