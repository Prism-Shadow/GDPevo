---
name: reflection-skill-attempt-01
description: Use for task_group_005 ERP finance/compliance workflow tasks that require solving reimbursement/AP close, vendor onboarding or account-change release, prepaid reconciliation, stale AP export refresh, or related JSON-answer tasks using the shared API.
---

# Task Group 005 ERP Workflow

## Core SOP

1. Read the prompt, answer template, and local payloads first. Treat local CSV/JSON snapshots as scope or stale context, not the system of record unless the prompt says otherwise.
2. Use the runner-provided API base URL. If needed, call `/endpoints`; both `/api/...` and short endpoints may exist. Use exact-match query parameters by field name plus `limit`/`offset`.
3. Query only records in scope: claims, bills, payments, AP aging, close logs, vendors, compliance objects, prepaid invoices, and GL balances as required by the template.
4. Build decisions from current API evidence. Do not copy source `review_status`, stale bill rows, or local snapshot statuses without reconciling them.
5. Return exactly the template shape. Sort ID lists as instructed, preserve template key order when specified, and round currency fields to two decimals.

Useful endpoints:

- Claims/AP: `/claims`, `/bills`, `/payments`, `/api/ap/aging`, `/close/logs`
- Compliance/vendor: `/vendors`, `/compliance/objects`
- Prepaids: `/prepaids/invoices`, `/gl/balances`

## Reimbursement and AP Close

For each requested claim:

- Query `/claims?claim_id=...`, `/bills?claim_id=...`, and `/payments?bill_id=...` for every linked bill. Use `/api/ap/aging` only as supporting balance evidence; claim-linked bill/payment records are primary.
- A paid claim is settled only when there is a matching claim-linked bill for the claim amount/vendor with bill `status=paid` and a cleared payment for that amount.
- A payable/open claim can remain in an AP reimbursement queue when the claim is approved and has a valid claim-linked reimbursement bill for the same amount/vendor, even if payment is scheduled or processing.
- Block owner/AP cleanup when the claim is unapproved, missing a bill, linked only to a void/draft bill, has partial/missing support when the workflow asks for release readiness, or the bill amount/vendor/account clearly belongs to another AP item.
- Open AP balance for payable claims is the valid claim bill amount unless the task explicitly asks for cleared-payment aging balance. Do not let a processing payment zero out a reimbursement still in the release batch.
- Overall status: `blocked` if any requested item is blocked; otherwise `open_payables`/`needs_ap_refresh` when valid unpaid or refresh-needed AP rows remain; otherwise ready/closed.

Stale AP snapshot tasks:

- Treat the local export as stale context. Produce correction enums from current API facts:
  - `mark_in_flight_payment`: valid claim bill has scheduled/processing payment evidence.
  - `replace_with_matched_paid_bill`: stale row points to the wrong bill, but current API has a matching paid bill/payment.
  - `exclude_amount_or_vendor_mismatch`: linked bill does not match claim amount/vendor or is not a reimbursement bill for the claim.
  - `ignore_void_bill`: current bill is void.
  - `block_unapproved_claim`: current claim is not approved.
- Eligible can include valid paid/matched claims and valid in-flight payment claims if the task is an AP refresh rather than a fresh release.
- For `close_log_required`, query close logs and include the specific AP/close evidence related to the refresh or cleanup event. Prefer task-relevant AP close-log entries over generic open/ready review logs.

## Vendor Compliance and Release Control

Join each scoped business by `business_id` in `/compliance/objects`, then query `/vendors?vendor_id=...` for vendor status, tax ID, and bank last4.

Field rules:

- `bank_mismatch_ids`: compliance `bank_account_status == "name_mismatch"`.
- `invalid_tax_ids`: compliance tax ID is malformed or differs from the vendor tax ID.
- `expired_license_ids`: `license_expiry` is before the task `as_of_date` for account-change release tasks. For onboarding hard-stop enums, treat expired license as workflow-specific: use it when the expired license is a material hard stop, but use `missing_required_documents` instead when the record primarily shows missing license evidence.
- `risk_score_override_flags`: `risk_score >= 70`.
- UBO reportable count: count unique owner names with `ownership_pct >= 25`; duplicate owner rows count once.
- `vendor_on_hold`: vendor `status == "on_hold"`.
- `screening_not_run`: sanctions check is `not_run`; for onboarding, also treat missing required screening evidence as follow-up.
- `missing_required_documents`: `missing_fields` is non-empty; do not also add `expired_license` just because the missing field is `license` unless the template/task asks for expired license IDs separately.

Decision guidance:

- `release`/`approve`: vendor active, bank verified, tax valid, sanctions clear, no confirmed PEP, no material missing documents, no expired license for the workflow, and no override-level risk.
- `hold`/`awaiting_information`: remediable release blockers such as bank mismatch, closed bank, missing docs, screening not run, expired license, or risk override without confirmed sanctions/PEP/shell evidence.
- `escalate`: confirmed PEP, confirmed sanctions, shell-company suspicion, vendor hold plus other risk, invalid tax with other release blockers, or multiple severe compliance defects.
- `follow_up_business_ids`/`review_queue_ids`: every non-release business.
- `overall_release_ready` is true only when every scoped business is approved/released.

## Prepaid Close Reconciliation

Use selected invoice IDs from the local scope. Query each with `/prepaids/invoices?prepaid_invoice_id=...` and GL with `/gl/balances?entity=...&period=...&account=...`.

Calculations:

- Include only scoped accounts and invoices.
- Period amortization fields such as `march_amortization`: invoice `monthly_amortization` if the close month falls inside the service period; otherwise `0.00`.
- Cumulative-through-period fields: monthly amortization times the count of service months from service-start month through the close month, inclusive, capped by service end. Mid-month starts still count for that month when the source schedule does.
- `ending_balance`: `original_amount - cumulative_amortization_through_march`, rounded to two decimals. Small residuals such as `0.01` can remain from rounded monthly schedules.
- Account totals are sums of invoice-level values. `variance_amount = schedule_ending_balance - gl_ending_balance`.
- `variance_flag` is true when absolute variance exceeds the provided threshold. Any material variance means `account_status: "requires_reconciliation"`; otherwise use `reconciled` unless a template defines a softer review state.

Prepaid flags:

- `default_missing_term_flag`: true for missing/default term indicators such as `missing_contract_dates`.
- `exception_flag`: true for any invoice data-quality flag, including rounded amount flags.
- `default_missing_term_invoice_ids`: only invoices with default/missing-term flags, sorted ascending.
- `exception_invoice_ids`: all invoices with exception flags, sorted ascending by invoice ID.

## Common Pitfalls

- Do not read local environment files; the API is the source of truth.
- Do not use stale AP snapshot rows as balances or statuses after current API evidence disagrees.
- Do not classify a claim as settled without both a paid bill and cleared payment.
- Do not compare claim IDs lexically by suffix only; sort full IDs ascending as the template requests.
- Do not double-count duplicate UBO names.
- Do not let source `review_status` alone decide release posture.
- Do not include narrative text outside the JSON answer.
