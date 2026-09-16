# API Control Patterns

## General Evidence Rules

- Use `TASK_ENV_BASE_URL` and the endpoints advertised by `/endpoints`.
- List responses normally have `data`, `count`, `limit`, `offset`, and `total`. Paginate until all relevant records are collected.
- Use local payloads to determine scope and schema. Use API rows to determine current status, amount, vendor, tax, bank, screening, and GL evidence.
- Join records by explicit IDs first: `claim_id`, `bill_id`, `payment_id`, `vendor_id`, `business_id`, `prepaid_invoice_id`, `account`, and `period`.
- When records conflict, prefer the current API row over stale CSV or memo context.

## AP Reimbursement And Close Batches

Fetch:

- Claims from `/api/claims` or `/claims`.
- AP bills from `/api/ap/bills` or `/bills`.
- Payments from `/api/ap/payments` or `/payments`.
- Close logs from `/api/close/logs` or `/close/logs` when stale snapshots, close refreshes, or cleanup logs are mentioned.

Classify a claim with the template's requested buckets:

- A settled claim needs a matching AP bill for the claim amount and vendor, bill status `paid`, and a cleared payment for that bill and amount.
- An open payable needs an approved claim, complete support when the prompt requires it, and a valid non-void AP bill that matches the claim amount and vendor. Payments with `processing` or `scheduled` status are in-flight, not cleared; do not subtract them when computing open AP balance unless the prompt says to.
- Block or mark not ready when the claim is not approved/releasable, receipt/support is incomplete for an unpaid claim, no valid linked bill exists, the bill is `void` or `draft`, or the bill amount/vendor/account evidence does not match the claim.
- Ignore voided bills as payment evidence. Treat draft bills as not release-ready.
- Calculate open balance from valid bills minus cleared payments only. Use zero for blocked or already settled claims when the requested field asks for current open AP balance.

For stale AP snapshots, compare each snapshot row to current claim, bill, and payment evidence:

- Use `mark_in_flight_payment` for a valid current bill with a non-cleared payment in process.
- Use `replace_with_matched_paid_bill` when the stale row points to an obsolete/wrong bill but a current matched paid bill has cleared.
- Use `exclude_amount_or_vendor_mismatch` when the current linked bill does not match the claim amount or vendor.
- Use `ignore_void_bill` when the relevant AP row is void.
- Use `block_unapproved_claim` when the current claim is not approved or otherwise fails owner/support readiness, even if a stale bill appears paid.
- Include close-log IDs only when the prompt asks for them and the current close-log row documents the relevant AP refresh, cleanup, or manual correction.

## Vendor Onboarding And Account-Change Reviews

Fetch:

- Vendor rows from `/api/vendors` or `/vendors`.
- Compliance objects from `/api/compliance/objects`.
- Detail endpoints `/api/compliance/ownership/{business_id}`, `/api/compliance/registry/{business_id}`, `/api/compliance/screening/{business_id}`, and `/api/compliance/bank/{business_id}` when the answer requires ownership, tax, license, screening, or bank-specific fields.

Common flags:

- Reportable UBO count is the number of unique owner names with `ownership_pct >= 25`; do not add duplicate rows for the same name.
- `bank_account_status == "closed"` maps to `bank_closed`.
- `bank_account_status == "name_mismatch"` maps to `bank_name_mismatch` or the template's bank mismatch list.
- `pep_status == "confirmed_pep"` maps to a confirmed PEP hard stop. Treat possible PEP as review evidence unless the template escalates possible matches.
- `sanctions_check_status == "confirmed_match"` maps to a confirmed sanctions hard stop.
- `sanctions_check_status == "not_run"` or `pep_status == "not_run"` maps to screening not run.
- `shell_company_suspected == true` maps to a shell-company hard stop.
- Non-empty `missing_fields` maps to missing required documents. Avoid double-counting a missing license as both missing documents and expired license unless the template asks for both.
- Vendor `status == "on_hold"` maps to a vendor-on-hold hard stop.
- Compare registry/compliance `tax_id` to vendor `tax_id`; mismatches or malformed values are invalid tax evidence when the template asks for tax flags.
- Compare `license_expiry` to the task's as-of/review date when the template asks for expired license IDs or flags.
- For account-change tickets, compare requested bank suffix to the current vendor bank suffix as well as compliance bank status.
- `risk_score >= 70` is a risk override when the template defines that threshold.

Decision posture:

- Approve or release only when current vendor, bank, tax, license, screening, ownership, and risk evidence has no hard stop or required review blocker.
- Await information or hold for remediable blockers such as missing required documents, screening not run, bank closed/name mismatch, or risk override when no severe compliance/legal blocker is present.
- Escalate for severe compliance/legal blockers such as confirmed PEP, confirmed sanctions, suspected shell company, vendor hold, invalid tax identity, or combinations of hard stops. Escalation outranks hold; hold outranks release.
- Populate follow-up/review queues with every non-approved/non-release business ID unless the template defines a narrower queue.

## Prepaid Close Reconciliation

Fetch:

- Prepaid invoice schedules from `/api/prepaids/invoices` or `/prepaids/invoices`.
- GL balances from `/api/prepaids/gl-balances` or `/gl/balances`.

Calculate:

- Use the scoped invoice IDs and accounts from the local payload.
- Use invoice `monthly_amortization` as the source monthly amount for straight-line schedules; do not recompute it from original amount unless the prompt requires it.
- Count a month as amortized when the service period overlaps that month. For a close period, current-period amortization is the monthly amount if the invoice is active in that period, otherwise zero.
- Cumulative amortization through the close period is monthly amortization times the number of active months from service start through the close period, capped by service end and original amount.
- Ending balance is `original_amount - cumulative_amortization_through_close`, rounded to the requested precision and not forced negative.
- Account rollups sum only selected invoices for that account. Variance is schedule ending balance minus GL ending balance.
- Set `variance_flag` using the absolute threshold from the payload/template when present; otherwise flag any nonzero material variance.
- Treat non-empty invoice `data_quality_flags` as invoice exceptions. Missing/default-term flags include names such as `missing_contract_dates`, `missing_term`, `default_term`, or equivalent prompt wording.
- Use a conservative account status: `reconciled` only with no material variance and no selected invoice exceptions; `variance_review` for variance-only review when allowed; `requires_reconciliation` when material variance or data-quality exceptions prevent close.
