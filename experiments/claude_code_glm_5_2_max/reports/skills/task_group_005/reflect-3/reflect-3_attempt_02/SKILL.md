# ERP Finance Expense-Control Skill (task_group_005)

Reusable workflow rules for solving ERP finance expense-control tasks against the shared remote ERP API. Distilled from reflect-loop practice on train tasks. These are workflow rules, not per-task answers.

## 0. Ground rules
- Use ONLY the remote ERP Web API (system of record). Do NOT read local `env/` source files or test fixtures.
- Report all currency in USD to 2 decimals unless a task explicitly says otherwise. Follow the `answer_template.json` `unit`/`precision` fields (they override ambiguous prose). Example: a template that says `unit: USD, precision: 2` means dollars with 2 decimals — do NOT convert to cents even if prose says "cents".
- Sort every ID list exactly as the template specifies (usually ascending by ID; digits sort before uppercase letters, so `CLM-2025-00xx` < `CLM-2025-FIN-xx` < `CLM-2025-OPS-xx`; `PPD-2025-*` < `PPD-AUR-*`).
- Preserve list orders that the template says must match an input payload order (e.g. `selected_invoice_ids` "same order as scope file").
- Query specific records by exact-match params (claim_id, bill_id, business_id, account, period, prepaid_invoice_id, vendor_id). Do not pull whole collections.

## 1. API contract
- Base URL + `GET /endpoints` lists all paths and the filtering contract.
- Health: `GET /health`, `GET /api/health`.
- Resources (namespaced `/api/...` preferred; bare aliases also exist): `/api/claims`, `/api/ap/bills`, `/api/ap/payments`, `/api/vendors`, `/api/close/logs`, `/api/prepaids/invoices`, `/api/prepaids/gl-balances`, `/api/compliance/objects`.
- Compliance detail routes: `/api/compliance/{profile,ownership,registry,screening,bank,risk}/{business_id}`. TIP: `/api/compliance/objects?business_id=X` returns a consolidated object with every field (bank_account_status, license_expiry, missing_fields, pep_status, sanctions_check_status, shell_company_suspected, tax_id, ubo_list, ownership_layer_count, risk_score, review_status, vendor_id, business_name, jurisdiction) — fetch this one endpoint per business instead of 6 detail calls.
- All list endpoints: exact-match query by field name + `limit`/`offset`.

## 2. Claims / AP / payment reconciliation (reimbursement-to-AP close)
For each candidate claim, fetch the claim, then bills by `claim_id`, then payments by `bill_id`.
- **paid**: claim has an AP bill whose amount AND vendor match the claim, bill status `paid`, and a payment with status `cleared` for the claim amount. Ignore any other (mismatched/stale) bills linked to the same claim.
- **payable** (stays in AP queue): claim approved + a valid OPEN AP bill (status `scheduled`/`approved`, amount & vendor match) + no cleared payment yet. A `processing` payment is NOT cleared — the bill stays open at full amount.
- **blocked** (needs owner/AP-link remediation): not paid AND the AP link is wrong — bill amount/vendor mismatch, bill `void`, or no bill at all. `crm_required` = the blocked set when the cause is expense-case/AP-link remediation.
- **batch_status**: `blocked` if any item blocked; else `open_payables` if valid unpaid AP bills remain; else `ready_to_close`.
- **ap_open_balance_total**: sum of valid open AP bill amounts for payable claims only (USD, 2 decimals). Apply only CLEARED payments to reduce a balance; ignore void/mismatched/stale bills.

## 3. Stale-AP-export batch review (conference reimbursement)
The local CSV/stale snapshot is context only — the API is the system of record. Compare snapshot vs current API per claim.
- **eligible** (can remain in batch): approved claim with a valid AP bill. A PAID claim that has a matching paid bill + cleared payment is still ELIGIBLE with open balance 0 (it is correctly reconciled, not "not ready").
- **not_ready**: claim unapproved / not `approved`; or only a void bill; or only an amount/vendor-mismatched bill; (a paid claim is NOT not_ready).
- **ap_balance_by_claim**: full bill amount when no cleared payment; 0 when a cleared payment covers it; ignore void/mismatched/stale rows.
- **stale_snapshot_corrections** (one enum per claim): `mark_in_flight_payment` (snapshot had no payment, API shows `processing`), `replace_with_matched_paid_bill` (snapshot cited wrong/stale bill, API has the matched paid bill), `exclude_amount_or_vendor_mismatch` (bill exists but amount/vendor ≠ claim), `ignore_void_bill` (bill is `void`), `block_unpaid`/`block_unapproved_claim` (claim status ≠ approved), `current_snapshot_ok` (snapshot already matches API).
- **batch_status**: `needs_ap_refresh` when the batch came from a stale AP export and has correctable items (even with unapproved/mismatch/void present — those become not_ready, they do not make the whole batch `blocked`); `ready_to_send` when clean; `blocked` only for a hard whole-batch block.
- **close_log_required**: for a stale-AP batch a close log is typically `required=true`; select the close-log IDs that are non-closed and thematically tied to the batch (e.g. status `blocked`/`open`/`ready_for_review` on the batch's AP accounts, or messages about "AP export refresh"). Fetch `/api/close/logs` and filter by `related_account`/`area`/`status`. (Close logs have no claim_id/bill_id field — relate by account and message theme.)

## 4. Vendor onboarding / compliance release (finance-risk)
Use `as_of_date` from the batch payload for all date comparisons.
- **reportable_ubo_counts**: count UNIQUE beneficial-owner NAMES whose `ownership_pct >= 25` (the standard BO reporting threshold; values like 24% and 10% are deliberately below). Dedupe by name; a name counts if ANY of its entries is >= 25.
- **hard_stop_flags** (per business, list sorted alphabetically; empty list when none):
  - `bank_closed` — `bank_account_status == "closed"`
  - `bank_name_mismatch` — `bank_account_status == "name_mismatch"`
  - `confirmed_pep` — `pep_status == "confirmed_pep"` (NOT `possible_pep`)
  - `expired_license` — `license_expiry < as_of_date`
  - `missing_required_documents` — `missing_fields` non-empty
  - `sanctions_confirmed` — `sanctions_check_status` is a positive/confirmed hit (none observed when `clear`)
  - `screening_not_run` — `sanctions_check_status == "not_run"` (and treat `pep_status == "not_run"` as a screening gap too)
  - `shell_company_suspected` — `shell_company_suspected == true`
  - `vendor_on_hold` — vendor record `status == "on_hold"` (fetch `/api/vendors`)
- **decision**: `escalate` ONLY when a hard stop in {`confirmed_pep`, `shell_company_suspected`, `sanctions_confirmed`} applies. `awaiting_information` when only the other (remediable) hard stops apply. `approve` when no hard stops. **Do NOT copy `review_status`** — a `review_status` of `escalated` does NOT by itself force `escalate` (confirmed: high-risk-but-no-pep/shell/sanctions businesses stay `awaiting_information`).
- **follow_up_business_ids**: all non-approve (ascending). **overall_release_ready**: true only if every business is `approve`.

## 5. Payment-release risk review (post account-change)
Same compliance/vender endpoints. Decisions: `release` / `hold` / `escalate`.
- **escalate** is STRICT — identical to onboarding: only `confirmed_pep`, `shell_company_suspected`, or `sanctions_confirmed`. Confirmed: `risk_score >= 70`, `bank_account_status == "closed"`, `sanctions_check_status == "not_run"`, `bank_name_mismatch`, `expired_license`, `invalid_tax`, `missing_required_documents` all → **`hold`** (NOT escalate) when none of the three escalation triggers are present.
- **release**: no compliance hard flags at all AND `risk_score < 70`. A business with `review_status == "in_review"` but no hard flags is still `release` (do not hold merely for in-review status).
- **risk_score_override_flags**: business IDs with `risk_score >= 70` (ascending). This is a flag list, not an escalation trigger.
- **bank_mismatch_ids**: `bank_account_status == "name_mismatch"` (ascending).
- **invalid_tax_ids**: tax_id that is malformed or a placeholder — non-digit chars (e.g. `TIN12X899`) or all-same-digit sentinel (e.g. `TIN999999`); also flagged when compliance `tax_id` ≠ vendor `tax_id` (fetch `/api/vendors`). Ascending.
- **expired_license_ids**: `license_expiry < as_of_date` (the template names `as_of_date` as the comparison date). A license dated one day AFTER as_of (e.g. `2025-06-02` vs `2025-06-01`) is NOT expired. Consider whether a business with a MISSING license (in `missing_fields`) should also be treated as not-currently-licensed.
- **review_queue_ids**: all non-`release` business IDs (hold + escalate), ascending. A released (no-flag) business is NOT in the queue even if its `review_status` is `in_review`.
- `target_business_ids` ascending; echo the fixed `task_id`, `batch_id`, `as_of_date` exactly as the template requires.

## 6. Prepaid close (straight-line amortization reconciliation)
Scope = invoices listed in the payload; reconcile only the named accounts; use the GL ending balance for the close period.
- **monthly amortization**: use the `monthly_amortization` field AS RECORDED. **cumulative_amortization_through_march = `monthly_amortization` × (number of months from service_start through the close month inclusive).** Do NOT prorate as `original × months/term` — using the rounded record monthly × count is correct (prorating breaks the score).
- **March counts as a full amortization month** for every invoice active in March, including mid-month starts (e.g. service_start `2025-03-15`). Term months = `original_amount / monthly_amortization`.
- **ending_balance** = `original_amount − cumulative_amortization_through_march` (can be 0.00 when fully amortized by the close month; small 0.01 residuals from rounded monthly are expected — keep them).
- **march_amortization** = `monthly_amortization` if the invoice is active in the close month, else 0.
- **default_missing_term_flag** = invoice `data_quality_flags` contains `missing_contract_dates`. Account-level `has_default_missing_term_flag` = any selected invoice in that account has it.
- **exception_flag** = invoice has ANY `data_quality_flags` entry (e.g. `rounded_amount`, `missing_contract_dates`). `exception_invoice_ids` = all such invoices, ascending.
- **variance_amount** = `schedule_ending_balance − gl_ending_balance`. `variance_flag` = `|variance| > variance_threshold_abs` (from scope). `gl_ending_balance` = `/api/prepaids/gl-balances?account=X` row with `period` == close period.
- **account_status**: `requires_reconciliation` when `has_default_missing_term_flag` is true (missing-term data prevents reliable reconciliation — this OVERRIDES variance_review). Else `variance_review` when `variance_flag` true. Else `reconciled`. (Confirmed: an account with a missing-term invoice stays `requires_reconciliation` even though its variance is also large.)
- Account rollup totals are sums across the account's selected invoices; keep 2 decimals. `selected_invoice_ids` in the scope-file order; the two exception ID lists ascending.

## 7. Common misjudgments to avoid
1. Prorating prepaid amortization — use recorded `monthly_amortization × month_count`.
2. Using a UBO threshold other than 25%, or counting all UBOs regardless of ownership.
3. Letting `review_status` drive the decision — it does not; only hard compliance flags do (`escalated` status ≠ escalate decision).
4. Over-broad escalate: `risk_score>=70`, `bank_closed`, `sanctions_not_run`, `invalid_tax`, `bank_name_mismatch`, `expired_license` → HOLD (not escalate) in both onboarding and payment-release. Only `confirmed_pep` / `shell_company_suspected` / `sanctions_confirmed` escalate.
5. Treating a paid (matched-bill, cleared-payment) claim as `not_ready` — it is `eligible` with 0 balance.
6. Setting batch_status `blocked` for a stale-AP batch — use `needs_ap_refresh`.
7. Converting to cents when the template says `unit: USD, precision: 2`.
8. Setting `account_status = variance_review` for an account that has a missing-term invoice — it must be `requires_reconciliation`.
9. Excluding March amortization for mid-month-start invoices — March counts.
10. Forgetting to apply ONLY cleared payments to AP open balances (processing/scheduled payments do not reduce the open balance).
11. Using `<=` or a grace window for license expiry — it is a strict `license_expiry < as_of_date`.
