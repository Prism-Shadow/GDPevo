# ERP Batch Decision Rules

These rules cover the recurring task patterns in this ERP/compliance task group. Use the prompt and `answer_template.json` to choose the relevant section.

## General Evidence Rules

- Use current API records as authoritative when they conflict with local snapshots, exports, or source-system review labels.
- Match records by explicit IDs first: `claim_id`, `bill_id`, `vendor_id`, `business_id`, `prepaid_invoice_id`, account, entity, and period.
- Treat amounts as matching only when they agree to the cent. Use `Decimal` or cent integers for calculations when possible.
- Ignore void AP bills for open-balance and payment-readiness decisions. Treat draft bills as not release-ready.
- A cleared payment is settlement evidence. Scheduled or processing payments are not settled; keep the payable/open balance unless the template asks for in-flight status.
- When a template asks for release-control decisions, infer readiness from evidence instead of copying `review_status` or `status` labels.

## Reimbursement Claims, AP Bills, and Payments

Fetch:

- claim: `/api/claims?claim_id=...`
- AP bills linked to the claim: `/api/ap/bills?claim_id=...`
- payments for each candidate bill: `/api/ap/payments?bill_id=...`
- close logs only when the prompt/template asks for them: `/api/close/logs`

Classify each claim:

- `paid` / settled: the claim has a current AP bill linked to the claim with amount matching the claim amount, bill status `paid`, and cleared payment(s) for the same bill and amount.
- payable / eligible open payable: the claim is approved, has usable support (`receipt_status` normally `attached`), and has a non-void, non-draft AP bill linked to the claim with amount and vendor matching the claim. Scheduled or processing payments do not settle it.
- blocked / not ready: the claim is not approved or already lacks case readiness, has missing or partial support that has not already settled, has no valid linked AP bill, has only void/draft bills, or has amount/vendor evidence that does not match the claim.

Open AP balance:

- Start with valid non-void, non-draft bills that match the claim amount and vendor evidence.
- Subtract cleared payments for those bills.
- Do not subtract scheduled or processing payments.
- For close templates that ask for a total open balance, sum only claims classified as payable/open.

Common stale snapshot correction labels:

- `current_snapshot_ok`: stale row still agrees with the current API evidence.
- `mark_in_flight_payment`: the current API shows a valid open bill with a scheduled or processing payment, so AP needs refresh but the claim can remain in the payable batch.
- `replace_with_matched_paid_bill`: the stale row points at old or mismatched AP evidence, while current API has a matching paid bill and cleared payment.
- `exclude_amount_or_vendor_mismatch`: the AP row linked to the claim does not match the claim amount or vendor evidence.
- `ignore_void_bill`: the relevant AP bill is void and should not support release or balance.
- `block_unapproved_claim`: the claim itself is not approved/release-ready, even if stale AP rows exist.

Batch status patterns:

- Use `blocked` when any requested claim is blocked/not ready and the template offers that value.
- Use `open_payables` or `needs_ap_refresh` when valid open payables remain and no stronger blocked status applies.
- Use `ready_to_close` or `ready_to_send` only when every requested item is settled or release-ready under the template's definitions.

## Vendor Onboarding Finance-Risk

Fetch:

- compliance object: `/api/compliance/objects?business_id=...`
- vendor record by `vendor_id`: `/api/vendors?vendor_id=...`
- use detail endpoints for confirmation when needed: ownership, registry, screening, and bank.

Reportable UBO count:

- Count unique beneficial-owner names with `ownership_pct >= 25`.
- Do not double-count repeated names.

Hard-stop flag mapping:

- `bank_closed`: compliance bank status is `closed`.
- `bank_name_mismatch`: compliance bank status is `name_mismatch`.
- `confirmed_pep`: screening `pep_status` is `confirmed_pep`.
- `expired_license`: `license_expiry` is before the batch as-of/review date, unless the license itself is missing and the expected flag set uses `missing_required_documents` instead.
- `missing_required_documents`: `missing_fields` is non-empty.
- `sanctions_confirmed`: sanctions status is `confirmed_match`.
- `screening_not_run`: PEP or sanctions status is `not_run`.
- `shell_company_suspected`: ownership evidence has `shell_company_suspected: true`.
- `vendor_on_hold`: vendor status is `on_hold`.

Decision pattern:

- `approve`: no hard-stop flags after current API review.
- `awaiting_information`: the only blockers are missing required documents or screening that has not been run.
- `escalate`: any severe hard stop exists, including confirmed PEP, confirmed sanctions, shell-company suspicion, bank closed/name mismatch, expired license, or vendor hold.
- `follow_up_business_ids`: every business not approved.
- `overall_release_ready`: true only when every business is approved/released.

Sort hard-stop flags alphabetically or in the enum order required by the template.

## Account-Change AP Payment Release

Use the local account-change payload for target IDs, requested bank last4 values, ticket metadata, review date, and batch IDs. Fetch current vendor and compliance evidence for each business.

List derivations:

- `bank_mismatch_ids`: business IDs where compliance `bank_account_status` is `name_mismatch`. If a template also asks for closed/not-verified banks, classify those separately.
- `invalid_tax_ids`: compliance/registry `tax_id` differs from the linked vendor `tax_id`, or the prompt defines the tax ID as invalid.
- `expired_license_ids`: `license_expiry` is before the review/as-of date.
- `risk_score_override_flags`: `risk_score >= 70` unless the prompt states a different threshold.
- `review_queue_ids`: every target business whose decision is not `release`.

Decision pattern:

- `release`: vendor is active, requested bank last4 agrees with the vendor record, compliance bank is verified, vendor and registry/compliance tax IDs agree, license is current, sanctions are clear, PEP is not confirmed, screening is complete, and no other template-specific hold/escalation evidence exists.
- `hold`: operational release blockers exist but no severe identity/compliance escalation is proven, such as bank closed/name mismatch/not verified, expired license, missing documents, screening not run, or risk score override.
- `escalate`: identity or compliance conflict needs higher review, such as tax mismatch, confirmed PEP, confirmed sanctions, shell-company suspicion, vendor hold paired with other risk evidence, or multiple severe inconsistencies.

If evidence supports both `hold` and `escalate`, choose `escalate`.

## Prepaid Close and GL Reconciliation

Use the local scope file for selected invoices, accounts, entity, close period, and variance threshold. Fetch:

- prepaid invoice records: `/api/prepaids/invoices?prepaid_invoice_id=...`
- GL balances: `/api/prepaids/gl-balances?period=YYYY-MM`

Schedule math:

- Use the invoice's `monthly_amortization` for straight-line schedules instead of recomputing from original amount unless it is missing.
- A service month counts if the close month overlaps the invoice service period. Mid-month starts still count as that month when the source schedule is monthly.
- `period_amortization` for the close month is the monthly amount when the service period includes that month; otherwise zero.
- `cumulative_amortization_through_period` is monthly amortization times counted service months from service start through close period, capped at the original amount.
- `ending_balance` is original amount minus cumulative amortization, rounded to two decimals.

Flags:

- `default_missing_term_flag`: true when data quality flags include missing contract/service terms, especially `missing_contract_dates`, or equivalent default-term flags described by the prompt.
- `exception_flag`: true when the invoice has any data quality flag or another prompt-defined invoice exception.
- `default_missing_term_invoice_ids`: all selected invoices with the default/missing-term flag, sorted as requested.
- `exception_invoice_ids`: all selected invoices with `exception_flag`, sorted as requested.

Account rollup:

- Sum selected invoice original amounts, close-period amortization, cumulative amortization, and ending balances by account.
- Pull `account_name` and `gl_ending_balance` from the GL balance record matching entity, period, and account.
- `variance_amount = schedule_ending_balance - gl_ending_balance`.
- `variance_flag` is true when `abs(variance_amount)` meets or exceeds the scope/template threshold.
- `account_status`:
  - `reconciled`: no material variance and no exception/default-term issue.
  - `variance_review`: material variance with otherwise clean invoice data.
  - `requires_reconciliation`: default/missing-term issues, invoice exceptions combined with variance, or other source-record defects requiring close cleanup.

Keep `invoice_results` in the same order as the scope file unless the template says otherwise.
