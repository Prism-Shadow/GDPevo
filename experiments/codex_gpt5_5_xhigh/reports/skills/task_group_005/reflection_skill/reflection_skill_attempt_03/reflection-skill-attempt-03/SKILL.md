---
name: reflection-skill-attempt-03
description: Solve task_group_005 ERP finance/compliance workflow tasks using the shared JSON API, including AP reimbursement close reviews, stale AP refresh decisions, prepaid reconciliations, vendor onboarding, and account-change payment release risk.
---

# Task Group 005 Workflow

## Core SOP

1. Read the prompt and local payload/template first. Use only the candidate IDs, period, entity, accounts, and response shape requested.
2. Call the runner API, not local env files. Start with `GET /endpoints`; use exact-match query parameters by field name plus `limit`/`offset` when needed.
3. Pull current source records for every requested ID. Treat local CSV snapshots as stale context unless the prompt says otherwise.
4. Join records by stable IDs:
   - Claims: `claim_id`
   - AP bills/payments: `bill_id`, and bills back to `claim_id`
   - Vendors/compliance: `vendor_id`, `business_id`
   - Prepaids/GL: `prepaid_invoice_id`, `account`, `period`, `entity`
5. Return JSON only, matching the template exactly. Preserve requested ordering; sort ID lists ascending when requested. Round money to two decimals.

## API Endpoints

Use the canonical `/api/...` endpoints when available:

- `/api/claims`
- `/api/ap/bills`
- `/api/ap/payments`
- `/api/close/logs`
- `/api/vendors`
- `/api/compliance/objects`
- `/api/prepaids/invoices`
- `/api/prepaids/gl-balances`

Filtering is exact-match: `?claim_id=...`, `?bill_id=...`, `?business_id=...`, `?vendor_id=...`, `?prepaid_invoice_id=...`, `?period=...`.

## AP Reimbursement Logic

Classify each requested claim from current API evidence:

- `paid`: claim has a current paid AP bill for the claim amount and a cleared payment for that bill/amount.
- `payable` or `eligible`: claim is approved and has a valid current open AP bill for the claim amount. Scheduled/processing payment evidence means the item is in flight, not cleared.
- `blocked` or `not_ready`: claim is not approved, has partial/missing support when support matters, lacks an AP bill, has only a void bill, or has AP amount/vendor evidence that does not match the claim.

Compute open AP balance from valid current bills only. Ignore voided bills, stale snapshot rows, amount/vendor mismatches, and already-cleared paid bills. For stale export reviews, a paid claim with a matched paid bill can be `eligible` with a `0.00` open balance if the field means "can remain after reconciliation."

Common stale correction meanings:

- `mark_in_flight_payment`: valid bill exists but payment is scheduled/processing.
- `replace_with_matched_paid_bill`: stale bill row should be replaced by current paid bill/payment evidence.
- `exclude_amount_or_vendor_mismatch`: current/stale AP row does not match claim amount/vendor.
- `ignore_void_bill`: bill is void.
- `block_unapproved_claim`: claim is not currently approved or still needs owner/support cleanup.

For close-log fields, query `/api/close/logs` and select the AP/close refresh log that supports the requested stale-batch correction context. Do not assume only open logs count; closed logs can be the required evidence when they document the AP refresh/manual correction.

## Prepaid Reconciliation

Use scoped invoice IDs only, in payload order. Reconcile only requested accounts and the requested GL period/entity.

For each invoice:

- Use `monthly_amortization` from the invoice record.
- Count full represented monthly amortization for each active month through the close period; do not prorate mid-month service dates unless the record provides prorated values.
- `march_amortization` or period amortization is the monthly amount if the invoice is active in the close month, else `0.00`.
- `cumulative_amortization_through_<period>` is monthly amount times active months through the period, capped by original amount only when necessary.
- `ending_balance = original_amount - cumulative_amortization`, rounded to two decimals.
- `default_missing_term_flag` is true for missing/default contract-term flags such as `missing_contract_dates`.
- `exception_flag` is true for any invoice data-quality flag, including `rounded_amount` and missing-term flags.

Roll up by account:

- Sum original amounts, period amortization, cumulative amortization, and ending balances from invoice rows. Use a calculator or script; arithmetic slips are common.
- `variance_amount = schedule_ending_balance - gl_ending_balance`.
- `variance_flag` is true when absolute variance exceeds the prompt threshold.
- Use `requires_reconciliation` when the account has a material variance or missing/default-term exceptions; otherwise use `reconciled` unless the template/prompt defines a lighter review state.

## Vendor/Compliance Logic

Join `/api/compliance/objects` to `/api/vendors` by `vendor_id`. Compare:

- `business_id`, `business_name`, `vendor_id`
- Vendor `status`, `tax_id`, and `bank_account_last4`
- Compliance `bank_account_status`, `tax_id`, `license_expiry`, `missing_fields`, `sanctions_check_status`, `pep_status`, `shell_company_suspected`, `risk_score`, `ubo_list`

Beneficial-owner counts usually mean unique owner names with `ownership_pct >= 25`; duplicate names count once.

Hard-stop flag mapping:

- `bank_closed`: compliance bank status is `closed`.
- `bank_name_mismatch`: compliance bank status is `name_mismatch`.
- `vendor_on_hold`: vendor status is `on_hold`.
- `confirmed_pep`: PEP status is confirmed.
- `sanctions_confirmed`: sanctions status is confirmed.
- `screening_not_run`: sanctions or PEP screening was not run.
- `shell_company_suspected`: boolean true.
- `missing_required_documents`: required items are present in `missing_fields`.
- `expired_license`: license is expired as of the task date when the task expects license expiry as an explicit hard stop. If `missing_fields` already includes license, prefer `missing_required_documents` over duplicating the license issue unless the answer schema/prompt asks for all reasons.

## Release Decisions

Do not copy `review_status` directly. Make a release-control decision:

- `approve`/`release`: no hard stops, vendor is active, bank/tax/license/screening are acceptable, and requested bank last4 matches vendor bank when an account-change payload is present. A non-final source review status alone is not enough to block release.
- `awaiting_information`/`hold`: remediable missing docs, screening not run, bank closed/name mismatch, risk-score override, or other operational review issues without severe escalation triggers.
- `escalate`: severe risk such as confirmed PEP, confirmed sanctions, shell-company suspicion, vendor hold, invalid/tampered tax ID, or multiple high-risk indicators together.

For account-change payment release:

- `bank_mismatch_ids`: compliance `bank_account_status == "name_mismatch"`.
- `invalid_tax_ids`: vendor tax ID and compliance tax ID differ, are placeholders, or are malformed.
- `expired_license_ids`: `license_expiry` is before the review date.
- `risk_score_override_flags`: `risk_score >= 70`.
- `review_queue_ids`: all non-release IDs that need AP/compliance action before payment.

## Pitfalls

- Local snapshots may be stale; current API records win.
- A claim can have multiple AP bills. Choose the bill that matches claim amount/vendor and current payment evidence.
- Payment `scheduled` or `processing` is not cleared.
- Void, mismatched, and stale AP rows contribute `0.00` open balance.
- Do not include paid/currently resolved items in not-ready lists unless the template defines not-ready as "not open."
- Sort list fields exactly as requested; keep scoped prepaid invoice order when requested.
- Do not include extra keys, narratives, or answer-dump evidence in final JSON.
