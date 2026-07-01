---
name: task-group-005-fewshot-attempt-03
description: Solve PanofyBench task_group_005 ERP, AP, prepaid close, vendor onboarding, and account-change release tasks by using the shared JSON API and returning schema-exact JSON outputs.
---

# Task Group 005 ERP Solver

Use this skill when a task asks for finance/AP close, prepaid reconciliation, vendor onboarding release control, or account-change payment release decisions from the task_group_005 shared API.

## API workflow

- Use the API base URL from the prompt or runner. Local variants observed include `<environment_base_url>`; in this environment the same API may be served on another loopback port.
- First call `/endpoints`. The API advertises exact-match query parameters by field name plus `limit` and `offset`.
- Prefer current API records over local snapshots or source review statuses. Local CSV/JSON payloads define scope and output shape; they are not the system of record.
- Common endpoints: `/api/claims`, `/api/ap/bills`, `/api/ap/payments`, `/api/ap/aging`, `/api/close/logs`, `/api/vendors`, `/api/compliance/objects`, `/api/prepaids/invoices`, `/api/prepaids/gl-balances`. Non-`/api` aliases may also exist.
- Return only JSON matching the local `answer_template.json`. Preserve required top-level key order when the template specifies it. Sort ID lists by the template rule, usually ascending ID, except prepaid invoice result lists often preserve payload order.

## Claim and AP close rules

For reimbursement/AP batch tasks, join each scoped claim to current AP bills and payments.

- A payable/open reimbursement needs a current approved claim and a non-void AP bill linked to that claim whose amount, currency, and vendor evidence match the claim. `approved` or `scheduled` AP bill statuses can be open/payable.
- A paid claim needs a matching AP bill for the claim amount and a cleared payment for that bill amount. Do not treat scheduled or processing payments as cleared.
- Compute open AP balance from valid current AP bills minus cleared payments only. Ignore void bills, stale snapshot rows, and AP rows whose amount/vendor/account evidence does not fit the claim.
- Block claims with unapproved claim status, missing AP link, void-only AP evidence, amount/vendor mismatch, draft/invalid bills, or unresolved receipt/support/policy issues that prevent AP release.
- Keep reimbursement-case cleanup separate from AP/payment evidence issues when the output has separate blocked/CRM fields.
- Overall close status: `blocked` if any scoped claim is blocked; otherwise `open_payables` if valid unpaid AP remains; otherwise `ready_to_close`.

For stale AP snapshot tasks:

- Treat the snapshot as historical context. Reconcile every candidate against current claims, bills, payments, aging, and close logs.
- Correction flags map to current evidence:
  - `mark_in_flight_payment`: valid current bill has a non-cleared in-flight payment.
  - `replace_with_matched_paid_bill`: stale row points to the wrong bill/status but a current matched paid bill and cleared payment exist.
  - `exclude_amount_or_vendor_mismatch`: current AP evidence is linked but amount/vendor does not match the claim.
  - `ignore_void_bill`: linked AP bill is void and should not contribute balance.
  - `block_unapproved_claim`: claim is not currently approved/releasable.
  - `current_snapshot_ok`: snapshot agrees with current valid evidence.
- Set `close_log_required.required` when AP refresh or close remediation evidence is needed; include relevant AP close-log IDs sorted ascending.
- Use `needs_ap_refresh` when current evidence supports some release/cleanup but stale rows require AP refresh or close-log action; use `ready_to_send` only when all candidates are currently releasable without refresh; reserve `blocked` for unresolved release blockers.

## Prepaid close rules

Use scoped prepaid invoice IDs only and reconcile only requested accounts/period/entity.

- Pull selected records from `/api/prepaids/invoices` and GL ending balances from `/api/prepaids/gl-balances`.
- Use the invoice's `monthly_amortization` for straight-line schedules. Count service months from `service_start` through the close month when the invoice is active in that month; mid-month starts still count as that month when represented by the source schedule.
- For each invoice:
  - `march_amortization` or period amortization is the monthly amount if active in the close month, else `0.00`.
  - cumulative amortization through the close month is monthly amount times included service months, capped/rounded so ending balance is not negative except for cent-level source rounding.
  - ending balance is `original_amount - cumulative_amortization`, rounded to two decimals.
- `default_missing_term_flag` is true for missing/defaulted term evidence such as `missing_contract_dates`.
- `exception_flag` is true when invoice `data_quality_flags` is non-empty or other source quality exceptions apply. Keep this separate from account-level variance.
- Account rollups sum selected invoices by account. `variance_amount = schedule_ending_balance - gl_ending_balance`; flag variance when absolute variance exceeds the payload threshold.
- Use `requires_reconciliation` for material variances or missing-term/default flags, `variance_review` for review-only exceptions/immaterial variance, and `reconciled` only when schedule, GL, and invoice evidence are clean.

## Vendor onboarding release rules

For finance-risk onboarding, query compliance by `business_id` and linked vendor by `vendor_id`.

- Reportable UBO count is the number of unique UBO names with `ownership_pct >= 25`; do not double-count duplicate names.
- Hard-stop flags:
  - `bank_closed`: `bank_account_status == "closed"`.
  - `bank_name_mismatch`: `bank_account_status == "name_mismatch"`.
  - `confirmed_pep`: `pep_status == "confirmed_pep"`.
  - `expired_license`: `license_expiry` is before the task as-of date.
  - `missing_required_documents`: `missing_fields` is non-empty.
  - `sanctions_confirmed`: sanctions check is confirmed/positive.
  - `screening_not_run`: sanctions or PEP screening is `not_run`.
  - `shell_company_suspected`: source boolean is true.
  - `vendor_on_hold`: linked vendor status is `on_hold`.
- Sort each business's hard-stop flags alphabetically by enum value.
- Decision: `approve` only when release evidence is clean. Use `awaiting_information` for missing documents or not-run screening without a more severe stop. Use `escalate` for confirmed PEP, sanctions, shell suspicion, closed/mismatched bank, vendor hold, expired license with other hard stops, or other high-risk blocks.
- `follow_up_business_ids` are all non-approved businesses. `overall_release_ready` is true only when every scoped business is approved.

## Account-change payment release rules

Use the local account-change payload for target IDs, ticket bank last4, requested amounts, and review date; use API compliance/vendor records for current evidence.

- `target_business_ids` and all ID lists follow the template order, usually ascending `business_id`.
- `bank_mismatch_ids` include only compliance `bank_account_status == "name_mismatch"` unless the template says to include closed banks.
- `invalid_tax_ids` include businesses where compliance tax ID is malformed or does not match the linked vendor tax ID.
- `expired_license_ids` compare `license_expiry` to the task `as_of_date`; expired means strictly before that date.
- `risk_score_override_flags` include `risk_score >= 70`.
- `review_queue_ids` are all businesses that are not released.
- Decision: `release` only when bank, vendor status, requested bank last4, tax, license, sanctions/PEP, and risk evidence are clean. Use `hold` for remediable operational blocks such as name mismatch, closed bank, expired license, missing documents, not-run screening, or risk override when no severe contradiction exists. Use `escalate` for invalid tax, vendor hold, confirmed PEP/sanctions, shell suspicion, or combined severe evidence.

## Output discipline

- Use numeric dollars with two decimals unless the template explicitly asks for cents.
- Do not add explanatory text, comments, or unrequested keys.
- Do not copy current `review_status` or source `status` fields blindly; derive release/close posture from all required evidence.
- When multiple current records exist for the same scoped ID, choose the record that matches the business object: exact claim/business ID, amount, vendor, currency, and current payment state.
