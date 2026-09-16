# Decision Rules

## API and Evidence Handling

- Prefer `/api/...` endpoints when both root and `/api` variants exist.
- Use exact-match filters for scoped IDs, for example `claim_id`, `business_id`, `vendor_id`, `bill_id`, `prepaid_invoice_id`, `period`, and `account`.
- Page list endpoints until all data is collected. A response with `data`, `total`, `limit`, and `offset` may omit later pages if only the first page is read.
- Keep local payload fields for scope, constants, review dates, and stale context. Do not use local stale AP rows as current status.

## Reimbursement and AP Claim Close

Collect, for each candidate claim:

- Claim record from `/api/claims`.
- AP bills from `/api/ap/bills?claim_id=...`.
- Payments from `/api/ap/payments?bill_id=...` for each related bill.
- AP aging from `/api/ap/aging?bill_id=...` when the template asks for balances.
- Close logs from `/api/close/logs` when the prompt asks whether close-log action is required.

Classify current AP evidence:

- A claim is case-ready only when its current claim status is `approved` or already `paid` and the prompt does not require additional owner cleanup for receipt/support state.
- A current AP bill is usable only when it is not `void` or `draft`, is linked to the claim, and agrees with the claim amount and vendor evidence. Treat amount or vendor mismatch as invalid AP support for that claim.
- A paid claim requires a usable paid bill and cleared payment evidence for the claim amount. Scheduled or processing payments are not settled evidence.
- An open payable requires a case-ready approved claim plus a usable unpaid/non-void AP bill. Compute open balance as bill amount minus cleared payments only; do not reduce the balance for scheduled or processing payments.
- A blocked or not-ready claim includes unapproved claim status, missing/partial support when the task distinguishes expense-case cleanup, no usable AP link, void bills, amount mismatch, vendor mismatch, or missing cleared payment evidence for a claimed paid state.

Common stale-snapshot correction labels:

- `current_snapshot_ok`: current API agrees with the local row.
- `mark_in_flight_payment`: the current bill is valid but payment is only scheduled or processing.
- `replace_with_matched_paid_bill`: the local row points to stale or mismatched AP evidence but a different current matched bill is paid and cleared.
- `exclude_amount_or_vendor_mismatch`: the AP row is linked but amount or vendor does not support the claim.
- `ignore_void_bill`: the current bill exists but is void.
- `block_unapproved_claim`: the claim itself is not approved/currently releasable.

For batch status, follow the template definitions. Typical reimbursement close schemas use `blocked` if any candidate is blocked, `open_payables` if valid unpaid bills remain and nothing is blocked, and `ready_to_close` when all scoped items are settled. Stale AP refresh schemas may use `needs_ap_refresh` when corrections or close-log updates are required even if some candidate rows are not ready.

## Prepaid Close Reconciliation

For each selected prepaid invoice:

- Use the invoice record's `monthly_amortization`, `original_amount`, `account`, `service_start`, `service_end`, and `data_quality_flags`.
- A period amortization amount is the monthly amount when the close month falls between the service start and service end months, inclusive; otherwise it is zero.
- Cumulative amortization through the close month is monthly amount times the number of active service months from service start through the earlier of service end or close period. Cap at original amount if rounding would over-amortize.
- Ending balance is original amount minus cumulative amortization, rounded to two decimals.
- `default_missing_term_flag` is true when data quality flags indicate missing/default term or missing contract dates.
- `exception_flag` is true when data quality flags are non-empty or the prompt identifies another invoice-level data quality exception.

For each requested prepaid account:

- Sum selected invoice count, original amount, period amortization, cumulative amortization, and ending balance from selected invoices in that account only.
- Pull the GL ending balance for the requested entity, period, and account.
- Variance is schedule ending balance minus GL ending balance.
- Use the prompt or scope variance threshold. If no threshold is supplied, treat any material non-zero variance as a variance flag.
- Mark `requires_reconciliation` when the account has a threshold variance or missing/default term issue. Use `variance_review` for non-blocking exceptions without a threshold variance, and `reconciled` only when no variance or exception remains.

## Vendor Onboarding and Account-Change Release

Collect, for each business:

- Compliance object from `/api/compliance/objects?business_id=...`.
- Per-business ownership, registry, screening, and bank endpoints.
- Vendor record from `/api/vendors?vendor_id=...`, using the vendor ID in the compliance object or local account-change event.

Reusable derived fields:

- Reportable UBO count is the number of unique owner names with `ownership_pct >= 25`.
- `bank_name_mismatch` comes from bank status `name_mismatch`.
- `bank_closed` comes from bank status `closed`.
- `confirmed_pep` comes from screening or compliance PEP status `confirmed_pep`; do not treat `possible_pep` as confirmed unless the prompt says to.
- `sanctions_confirmed` comes from a confirmed sanctions status.
- `screening_not_run` comes from sanctions or PEP status `not_run`.
- `shell_company_suspected` comes from ownership/compliance shell flags.
- `missing_required_documents` comes from non-empty `missing_fields`.
- `vendor_on_hold` comes from vendor status `on_hold`.
- `expired_license` is true when license expiry is before the review/as-of date, unless the prompt gives a grace period or a separate missing-document rule supersedes it.
- `invalid_tax` is true when vendor tax ID and compliance/registry tax ID disagree.
- `risk_score_override` is true at `risk_score >= 70` unless the prompt gives a different threshold.

Decision posture:

- Onboarding release calls usually approve only when no hard-stop flags apply. Use `awaiting_information` for missing documents or screening gaps without a severe escalation trigger. Use `escalate` for confirmed PEP, confirmed sanctions, shell-company suspicion, bank closure, vendor hold, invalid/expired legal evidence, or multiple hard stops.
- Account-change payment release reviews usually `release` only when bank, tax, license, screening, vendor, and risk evidence are clean. Use `hold` for bank closure/name mismatch, missing documents, screening gaps, expired license, or risk-score override when no escalation trigger is present. Use `escalate` for invalid tax, confirmed PEP, confirmed sanctions, vendor hold, shell-company suspicion, or any prompt-defined severe issue.
- If both hold and escalation triggers apply, choose the escalation decision unless the template gives a stricter label.

## Final JSON Checks

- Include required constants from the template exactly.
- Do not add keys when `additional_properties_allowed` is false.
- For list-valued flags, use empty lists for businesses or claims with no flags.
- For object-valued per-ID sections, include every required scoped ID even when the derived value is zero, false, or an empty list.
