---
name: demonstration-skill-attempt-01
description: Solve task_group_005 finance/API JSON-output tasks involving reimbursement AP close, stale AP snapshots, prepaid close reconciliation, vendor onboarding controls, and account-change payment release risk reviews.
---

# Task Group 005 Finance API Solver

Use this skill when a task asks for a JSON answer from the shared ERP/compliance API for claims, AP, prepaids, vendors, compliance objects, or close logs.

## API Workflow

- Use the runner-provided API base URL. If unsure, call `/endpoints`; endpoints also exist under `/api/...`.
- Responses are wrapped as `{count, data, endpoint, limit, offset, total}`. Use `data`.
- Exact-match filters work by field name, e.g. `?claim_id=...`, `?bill_id=...`, `?business_id=...`, `?vendor_id=...`, `?account=...`, `?period=...`.
- Treat local payloads and CSV snapshots as scope/context only. Current API records are the system of record.
- Preserve the answer template exactly: no extra keys, JSON only, required ordering, and two-decimal USD numbers where requested.

## AP Reimbursement / Claim Close Rules

For each scoped claim, fetch:

- `/claims` for current claim amount, vendor, status, receipt/support state.
- `/ap/bills` by `claim_id` for linked AP evidence.
- `/ap/payments` by `bill_id` for payment evidence.
- `/close/logs` when the template asks for close-log IDs or AP refresh support.

Classify using current records:

- A valid open AP reimbursement bill must be non-void, linked to the claim, match claim amount/currency, and not conflict with vendor evidence. Scheduled/approved bills are open unless a matching cleared payment already settles them.
- A claim is paid/settled only when the claim is currently paid or otherwise supported by a matching paid AP bill and a cleared payment for the bill amount. Scheduled or processing payments are not cleared.
- Block/not-ready claims with unapproved claim status, missing/partial receipt/support when the prompt asks for release readiness, no usable AP link, void bills, or bill amount/vendor mismatches.
- Open AP balance is valid bill amount minus cleared payments only. Ignore void bills and stale snapshot rows; do not subtract scheduled or processing payments.
- Keep reimbursement case defects separate from AP/payment evidence defects when the template has separate fields such as CRM cleanup vs AP correction.

Stale AP snapshot correction labels commonly map as:

- `current_snapshot_ok`: snapshot agrees with current valid open AP evidence.
- `mark_in_flight_payment`: current AP has a valid open bill with a scheduled/processing payment that is not cleared.
- `replace_with_matched_paid_bill`: stale row points to the wrong bill, but a current paid bill plus cleared payment settles the claim.
- `exclude_amount_or_vendor_mismatch`: current bill does not match claim amount/vendor evidence.
- `ignore_void_bill`: only stale/linked AP row is void.
- `block_unapproved_claim`: claim case is not approved/releasable even if AP rows exist.

Batch status pattern: blocked if any item is blocked by claim/support/AP mismatch; otherwise open/needs refresh if valid unpaid AP or stale snapshot corrections remain; otherwise ready/closed.

## Vendor Onboarding / Payment Release Rules

For each scoped `business_id`, fetch `/compliance/objects?business_id=...`, then `/vendors?vendor_id=...` from the compliance object.

Important derived fields:

- Reportable UBO count: count unique owner names with `ownership_pct >= 25`; duplicates count once.
- `bank_name_mismatch`: `bank_account_status == "name_mismatch"`.
- `bank_closed`: `bank_account_status == "closed"`.
- `screening_not_run`: sanctions or PEP screening status is `not_run` when the template lists that flag.
- `confirmed_pep`: `pep_status == "confirmed_pep"`; `possible_pep` is review context, not the confirmed flag.
- `sanctions_confirmed`: confirmed sanctions match, not merely possible/clear.
- `shell_company_suspected`: compliance boolean is true.
- `expired_license_ids`: `license_expiry` before the task `as_of_date`/review date.
- `missing_required_documents`: nonempty required missing fields, especially license, bank statement, beneficial owner ID, address, or website when requested.
- `vendor_on_hold`: vendor status is `on_hold`; inactive vendors are not release-ready.
- `invalid_tax_ids`: vendor tax ID and compliance tax ID differ, or the compliance tax ID is visibly invalid for the task.
- `risk_score_override_flags`: `risk_score >= 70`.

Decision guidance:

- Release/approve only when current vendor is active, requested bank last4 matches vendor bank last4 when given, bank is verified, tax IDs match, license is current, screenings are clear, no hard-stop flags exist, and risk score is below override threshold.
- Awaiting information/hold for remediable missing docs, screening not run, bank closed/mismatch, expired license, or risk override when no severe compliance escalation is present.
- Escalate for confirmed PEP, confirmed sanctions, shell-company suspicion, vendor hold/inactive with release request, invalid tax identity, or multiple severe hard stops.
- `overall_release_ready` is true only if every scoped business is releasable. Follow-up/review queues include every non-release/non-approve business.

## Prepaid Close Rules

Use `/prepaids/invoices` for selected invoice IDs and `/prepaids/gl-balances` for the scoped entity, accounts, and close period.

- Use the input scope order for `selected_invoice_ids` and per-invoice result rows.
- Use the API `monthly_amortization`; do not recompute the monthly amount from original amount.
- Straight-line cumulative through a close month is `monthly_amortization * number_of_included_months`, where included months are whole calendar months from service start month through close month, capped by service end month. A mid-month start still counts the full month represented by the source schedule.
- `march_amortization` or period amortization is the monthly amount when the invoice service period includes that close month; otherwise 0.
- Ending balance is `original_amount - cumulative_amortization`, rounded to two decimals and not below zero except for penny rounding already implied by source values.
- Account rollups sum only selected invoices for that account. Variance is `schedule_ending_balance - gl_ending_balance`; flag when `abs(variance)` exceeds the template threshold.
- `default_missing_term_flag` is true for `data_quality_flags` containing `missing_contract_dates`.
- `exception_flag` is true for any data quality flag such as rounded amount, manual override, duplicate invoice number, or missing contract dates.
- Account status should be `requires_reconciliation` when a material variance or default/missing-term issue exists, `reconciled` when no variance/exceptions remain, and `variance_review` only for nonblocking review variance states if the template distinguishes them.

## Output Pitfalls

- Sort ID lists exactly as requested, usually ascending lexicographic ID; keep per-record lists in payload order when the template says so.
- Do not copy current `review_status` or snapshot status as the final decision; derive release/close posture from source evidence.
- Paid AP rows do not rescue an unapproved expense claim unless the prompt defines the field as stale-row correction rather than release eligibility.
- Scheduled/processing payments prove in-flight activity, not settlement.
- Possible PEP/sanctions are not the same as confirmed flags unless the template asks for possible matches.
