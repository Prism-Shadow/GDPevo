# ERP Finance Expense-Control Skill (task_group_005)

Reusable workflow rules for solving ERP finance expense-control / close / release-control tasks against the shared ERP API. Distilled from reflect-loop practice on train tasks. Contains no test answers and no test-time judge usage.

## 1. ERP API contract

- Remote API base URL: `<remote-env-url>` (the system of record; do not read local `env/` files).
- Discover paths with `GET /endpoints`. Health: `GET /health`, `GET /api/health`.
- Filtering: exact-match query parameters by field name, plus `limit`/`offset` for pagination. Always query by the specific ID/param (e.g. `?claim_id=CLM-...`, `?business_id=BUS-...`, `?bill_id=AP-...`, `?prepaid_invoice_id=PPD-...`, `?account=1250&period=2025-03`), never whole collections.
- Namespaced resource paths:
  - Claims: `/api/claims`
  - AP: `/api/ap/bills`, `/api/ap/payments`, `/api/ap/aging`
  - Vendors: `/api/vendors`
  - Compliance: `/api/compliance/objects` (flat object with all fields) + detail slices `/api/compliance/{profile,ownership,registry,screening,bank,risk}/{business_id}`
  - Prepaids: `/api/prepaids/invoices`, `/api/prepaids/gl-balances`
  - Close logs: `/api/close/logs` (fields: log_id, area, period, status, related_account, message, owner)
- Currency: report all amounts as USD with two decimals (follow the answer template's `unit`/`precision`; this overrides prompt wording such as "USD cents").

## 2. Claim / AP close-batch reconciliation (reimbursement-to-AP)

For each candidate claim, fetch claim → bills by `claim_id` → payments by `bill_id`. Match bill to claim by amount AND vendor.

Classify each claim:
- **Paid/settled**: a bill whose amount equals the claim amount, status `paid`, with a `cleared` payment for that amount.
- **Payable (in batch)**: an open (non-paid: `scheduled`/`approved`) AP reimbursement bill whose amount equals the claim amount; payment absent or not cleared.
- **Blocked / not-ready**: bill amount or vendor mismatches the claim, bill is `void`, no bill linked, or the claim is not `approved`.
- Open balance = open bill amount minus **cleared** payments only. In-flight/`processing` payments are NOT applied (they reduce balance only when cleared). Mismatched/void/wrong-vendor bills are excluded (balance 0).

Batch status:
- `ready_to_close` when all items paid and no blocks.
- `open_payables` when valid unpaid reimbursement bills remain and nothing is blocked.
- `blocked` when any item is blocked.
- For stale-AP-export release batches (`ready_to_send` / `needs_ap_refresh` / `blocked`): use `needs_ap_refresh` when the snapshot is stale and needs AP refresh (in-flight payments, wrong/void bills); do NOT jump to `blocked` merely because one claim is unapproved — `blocked` is for hard blocks.

Stale-snapshot correction vocabulary (`stale_snapshot_corrections` per claim):
`current_snapshot_ok`, `mark_in_flight_payment` (snapshot showed no payment but a processing payment now exists), `replace_with_matched_paid_bill` (snapshot referenced the wrong bill; use the matched paid bill), `exclude_amount_or_vendor_mismatch`, `ignore_void_bill`, `block_unapproved_claim`.

## 3. Compliance / vendor onboarding & payment-release review

Pull `/api/compliance/objects?business_id=X` (gives `bank_account_status`, `license_expiry`, `tax_id`, `missing_fields`, `pep_status`, `sanctions_check_status`, `shell_company_suspected`, `risk_score`, `review_status`, `ubo_list`, `vendor_id`) plus `/api/vendors?vendor_id=X` (vendor `status`, `bank_account_last4`, `tax_id`) and the detail slices if a field is missing.

**hard_stop_flags** vocabulary (set only when the explicit status is present):
- `bank_closed` (bank_account_status == `closed`)
- `bank_name_mismatch` (bank_account_status == `name_mismatch`)
- `confirmed_pep` (pep_status == `confirmed_pep` only; `possible_pep`/`not_run` do NOT set it)
- `missing_required_documents` (missing_fields non-empty)
- `sanctions_confirmed` (sanctions hit/confirmed)
- `screening_not_run` (sanctions_check_status == `not_run` OR pep_status == `not_run`)
- `shell_company_suspected` (shell flag true)
- `vendor_on_hold` (vendor.status == `on_hold`)
- Do NOT set `expired_license` as a hard_stop from `license_expiry` date alone — there is no license status field, so past-due dates do not fire this flag in the hard_stop list. (But see §4: tasks that ask for a separate `expired_license_ids` field DO report date-expired licenses.)

**reportable UBO count**: 25% reporting threshold. Count DISTINCT owner names whose ownership_pct (aggregated per name) is >= 25. Ownership values of 10% and 24% are below-threshold traps — exclude them. Do not count all distinct names.

**Decision vocabulary** (`approve`/`release` vs `awaiting_information`/`hold` vs `escalate`):
- `escalate`: any intrinsic blocker — sanctions_confirmed, shell_company_suspected, bank_closed, screening_not_run.
- `awaiting_information` / `hold`: only remediable flags — confirmed_pep, bank_name_mismatch, missing_required_documents, vendor_on_hold, invalid_tax, expired_license.
- `approve` / `release`: no hard stops and no remediable flags (clean).
- Derive decisions from the EVIDENCE, not from the source `review_status`; deliberately differ from `review_status` where evidence conflicts (e.g. review_status `approved` but bank_closed → escalate; review_status `in_review` but clean → approve/release). A `confirmed_pep` is a HOLD (needs EDD), NOT an escalate.
- `risk_score_override_flags`: list business IDs with `risk_score >= 70` (a separate factual flag; it flags high risk but does not by itself force escalate).
- `follow_up_business_ids` / `review_queue_ids`: all NON-approved / NON-released business IDs (hold + escalate), ascending.
- `overall_release_ready`: true only if every business is approved/released.
- Decision objects are often scored as an all-or-nothing set — get ALL per-business decisions right simultaneously.

**Factual separate-field checks** (report regardless of decision, per the task's template):
- `bank_mismatch_ids`: bank_account_status == `name_mismatch`.
- `invalid_tax_ids`: compliance `tax_id` != vendor `tax_id`, or malformed/placeholder (contains non-digit, all-9s sentinel).
- `expired_license_ids`: `license_expiry` < as_of_date (these tasks DO report expired licenses by date).
- `risk_score_override_flags`: `risk_score >= 70`.

## 4. Prepaid close reconciliation

For each scoped prepaid invoice, fetch `/api/prepaids/invoices?prepaid_invoice_id=X`; fetch GL balances `/api/prepaids/gl-balances?account=A&period=YYYY-MM`.

Straight-line monthly amortization:
- `march_amortization` (or the close month's amortization) = the invoice's `monthly_amortization` field value if the close month is within [service_start, service_end], else 0.
- `cumulative_amortization_through_march` = (number of months from service_start month through the close month, inclusive — the start month counts as month 1) × `monthly_amortization`. Use the field value as-is; do NOT cap at `original_amount` and do NOT absorb rounding residuals (a fully-elapsed invoice may legitimately show a small positive ending balance like 0.01).
- `ending_balance` = `original_amount` − cumulative. Term months = original_amount / monthly_amortization (verify it's a whole number).
- For mid-month service starts (e.g. 2025-03-15), the start calendar month still counts as a full amortization month.

Account rollup (sum selected invoices per account):
- `original_amount_total`, `march_amortization_total`, `cumulative_amortization_through_march`, `schedule_ending_balance` (= original_total − cumulative_total).
- `gl_ending_balance` from the GL balance record for that account+period.
- `variance_amount` = schedule_ending_balance − gl_ending_balance.
- `variance_flag` = |variance_amount| > variance_threshold_abs.
- `has_default_missing_term_flag` = any selected invoice in the account has a missing/default term.
- `account_status` (`reconciled` / `variance_review` / `requires_reconciliation`): pure variance-driven — `requires_reconciliation` when variance_flag is true (exceeds threshold); `variance_review` when variance within threshold but default/missing-term flags present; `reconciled` when within threshold and clean. Default/missing terms do NOT change an over-threshold account's status.

Per-invoice flags:
- `default_missing_term_flag` = data_quality_flags contains `missing_contract_dates`.
- `exception_flag` = any non-empty data_quality_flags (superset; an invoice can be both a default-missing-term and an exception).
- `default_missing_term_invoice_ids` and `exception_invoice_ids`: ascending string sort (note: `PPD-2025-*` sorts before `PPD-AUR-*` because digits precede letters).

## 5. Common misjudgments (avoid)

1. Flagging `expired_license` as a hard_stop from a past-due `license_expiry` date — do not (no license status field confirms revocation). But DO populate `expired_license_ids` in tasks that ask for it as a standalone field.
2. Counting all distinct UBO names instead of applying the 25% threshold (10% and 24% must be excluded).
3. Reporting currency in "cents" — follow the template's USD 2-decimals.
4. Capping/absorbing prepaid amortization residuals — use the `monthly_amortization` field value; a 0.01 ending residual is valid.
5. Treating `confirmed_pep` or `vendor_on_hold` as escalate — they are HOLD/awaiting (remediable).
6. Using `blocked` batch status just because a claim is unapproved — use `needs_ap_refresh` for stale-data batches.
7. Copying `review_status` into the decision — derive from evidence.
8. Applying in-flight (`processing`) payments to the open balance — only `cleared` payments reduce it.
9. Treating `possible_pep` as `confirmed_pep` — only `confirmed_pep` fires the flag.
10. Forgetting `screening_not_run` also fires when `pep_status == "not_run"` (not just sanctions `not_run`).

## 6. Output hygiene

- Match the answer template's required top-level keys exactly; `additional_properties_allowed` is usually false.
- Order all ID lists as specified (ascending by ID; for prepaid IDs, string sort puts `PPD-2025-*` before `PPD-AUR-*`).
- Preserve any required ordering that says "same order as the input payload scope file."
- Use exact enum strings from the template's `allowed_values`.
- Set fixed-value fields (`task_id`, `batch_id`, `as_of_date`) to the template's `required_value`.
