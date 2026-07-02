# ERP Finance Expense-Control Skill (task_group_005)

## API Contract

Base URL: provided by the runner (e.g. `<remote-env-url>`). Discover with `GET /endpoints`.

### Endpoints (namespaced canonical paths)

| Path | Resource | Key filter params |
|------|----------|-------------------|
| `/api/claims` | Expense claims | `claim_id` |
| `/api/ap/bills` | AP bills (vendor invoices) | `claim_id`, `bill_id`, `vendor_id`, `status` |
| `/api/ap/payments` | AP payments | `bill_id`, `payment_id`, `vendor_id`, `status` |
| `/api/ap/aging` | AP aging summary | — |
| `/api/vendors` | Vendor master | `vendor_id` |
| `/api/compliance/objects` | Compliance/KYC objects | `business_id`, `vendor_id` |
| `/api/prepaids/invoices` | Prepaid invoices | `prepaid_invoice_id`, `account`, `vendor_id` |
| `/api/prepaids/gl-balances` | GL balances | `account`, `period`, `entity` |
| `/api/close/logs` | Month-end close logs | `log_id`, `area`, `period`, `status` |

Non-namespaced aliases also exist (`/claims`, `/bills`, `/payments`, `/vendors`, `/compliance/objects`, `/prepaids/invoices`, `/gl/balances`, `/close/logs`). Always prefer the `/api/...` namespaced path.

All list endpoints return `{ "count": N, "data": [...], "endpoint": "...", "limit": N, "offset": N, "total": N }`. Filter via exact-match query params by field name; paginate with `limit`/`offset`. Fetch specific records by ID to avoid large dumps. Health: `GET /health`, `GET /api/health`.

Report all currency amounts to two decimals in USD.

---

## Data Model Field Reference

### Claims (`/api/claims`)
`claim_id`, `status` (`approved`|`paid`|`needs_receipt`|...), `amount`, `vendor_id` (may be `null`), `currency`, `department`, `employee_name`, `category`, `receipt_status` (`attached`|...), `policy_flags` (`manual_rate`|`late_receipt`|...), `submitted_date`, `approved_date`, `notes`.

### AP Bills (`/api/ap/bills`)
`bill_id`, `claim_id`, `amount`, `status` (`scheduled`|`approved`|`paid`|`void`), `vendor_id`, `account` (GL acct: `2100`=AP, `1250`/`1251`=prepaids, `61xx`/`62xx`/`65xx`=expense), `bill_date`, `due_date`, `invoice_number`, `memo`, `currency`.

### AP Payments (`/api/ap/payments`)
`payment_id`, `bill_id`, `amount`, `status` (`cleared`|`processing`|`scheduled`), `vendor_id`, `method` (`Wire`|`Virtual card`|`Check`|...), `payment_date`, `bank_reference`.

### Vendors (`/api/vendors`)
`vendor_id`, `vendor_name`, `legal_name`, `status` (`active`|`on_hold`), `tax_id`, `bank_account_last4`, `default_account`, `payment_terms` (`Net 30`|...), `industry`, `updated_at`.

### Compliance Objects (`/api/compliance/objects`)
`business_id`, `business_name`, `vendor_id`, `bank_account_status` (`verified`|`name_mismatch`|`closed`), `license_expiry` (YYYY-MM-DD), `missing_fields` (`[]` or `["license","beneficial_owner_id",...]`), `ownership_layer_count`, `pep_status` (`none`|`possible_pep`|`confirmed_pep`|`not_run`), `registration_number`, `review_status` (`not_started`|`in_review`|`approved`|`escalated`|`awaiting_information`), `risk_score` (0-100 integer), `sanctions_check_status` (`clear`|`not_run`), `shell_company_suspected` (boolean), `tax_id` (`TIN`+digits), `ubo_list` (`[{name, ownership_pct}]`).

### Prepaid Invoices (`/api/prepaids/invoices`)
`prepaid_invoice_id`, `account` (`1250`=Prepaid Expenses, `1251`=Prepaid Insurance), `original_amount`, `monthly_amortization`, `service_start`, `service_end`, `invoice_date`, `recognition_method` (`straight_line`), `data_quality_flags` (`[]` or `["rounded_amount","missing_contract_dates",...]`), `vendor_id`, `description`.

### GL Balances (`/api/prepaids/gl-balances`)
`account`, `account_name`, `entity` (e.g. `Aurisic US`), `period` (`YYYY-MM`), `ending_balance`, `source`, `loaded_at`.

### Close Logs (`/api/close/logs`)
`log_id`, `area` (`AP`|`Prepaids`|`Expense`|`Compliance`), `period` (`YYYY-MM`), `status` (`closed`|`ready_for_review`), `message`, `owner`, `created_at`, `related_account` (nullable).

---

## Task Type 1: Reimbursement-to-AP Close Review

**Output fields** (`answer_template.json`): `payable_claim_ids`, `blocked_claim_ids`, `paid_claim_ids`, `ap_open_balance_total`, `crm_required_claim_ids`, `batch_status`, `reviewed_claim_count`.

### Controlled Vocabulary — batch_status
`ready_to_close` | `open_payables` | `blocked`

### SOP
1. For each `claim_id` in the batch:
   - `GET /api/claims?claim_id={id}` → claim `status`, `amount`, `vendor_id`.
   - `GET /api/ap/bills?claim_id={id}` → all linked bills.
   - For each bill: `GET /api/ap/payments?bill_id={bill_id}` → payment `status`.
2. Classify each claim:
   - **paid**: An AP bill exists with `amount` = claim amount AND `vendor_id` = claim vendor AND `status` = `paid`, plus a payment with `status` = `cleared` for the same amount. If multiple bills exist, find the one matching amount + vendor that is paid + cleared.
   - **payable**: Claim `status` = `approved` AND an open bill (`scheduled` or `approved`, not `void`/`paid`) matches the claim amount AND `vendor_id`. Add the bill amount to `ap_open_balance_total`.
   - **blocked**: None of the above — no AP bill linked; bill `void`; bill amount/vendor mismatch (including `vendor_id` = `null` on claim); bill on a non-reimbursement account (e.g. prepaid `1250`); or claim status not `approved`.
3. `crm_required_claim_ids` = all blocked claim IDs (need owner cleanup / AP-link remediation).
4. `batch_status`: `blocked` if any blocked claim; else `open_payables` if any payable; else `ready_to_close`.
5. Sort all ID lists ascending by `claim_id`.

### Key Rules
- A payment with `status` = `processing` (not `cleared`) means the bill is still open — claim is payable, balance is the bill amount.
- Vendor mismatch: if claim `vendor_id` is `null`, any vendor on the bill is a mismatch.
- A bill on account `1250` (Prepaid Expenses) is not a reimbursement bill → mismatch.
- `ap_open_balance_total` sums only valid open bills for payable claims (not paid, not blocked).

---

## Task Type 2: Stale-Snapshot AP Reconciliation (Conference Reimbursement)

**Output fields**: `eligible_claim_ids`, `not_ready_claim_ids`, `ap_balance_by_claim`, `stale_snapshot_corrections`, `close_log_required`, `batch_status`.

### Controlled Vocabulary — stale_snapshot_corrections
`current_snapshot_ok` | `mark_in_flight_payment` | `replace_with_matched_paid_bill` | `exclude_amount_or_vendor_mismatch` | `ignore_void_bill` | `block_unapproved_claim`

### Controlled Vocabulary — batch_status
`ready_to_send` | `needs_ap_refresh` | `blocked`

### SOP
1. For each candidate claim, query claim + bills + payments (same as Task Type 1).
2. Determine `stale_snapshot_corrections` per claim:
   - `current_snapshot_ok`: claim is approved, bill matches amount+vendor, payment status is appropriate.
   - `block_unapproved_claim`: claim `status` != `approved` (e.g. `needs_receipt`).
   - `ignore_void_bill`: AP bill `status` = `void`.
   - `exclude_amount_or_vendor_mismatch`: bill amount or vendor does not match the claim.
   - `replace_with_matched_paid_bill`: multiple bills exist; the matching one is `paid` + payment `cleared`; the stale scheduled bill is ignored.
   - `mark_in_flight_payment`: payment `status` = `processing` (in flight, not cleared). The bill is still open — balance counts.
3. `ap_balance_by_claim`: Open AP balance after applying corrections:
   - Void bill → 0.00
   - Amount/vendor mismatch → 0.00
   - Paid + cleared → 0.00
   - In-flight payment (processing) → bill amount (still open)
   - Scheduled bill → bill amount
   - Unapproved claim → 0.00
4. `eligible_claim_ids`: claims that can remain in the batch after reconciliation (claim approved, bill matches amount+vendor, payment is appropriate). Sort ascending.
5. `not_ready_claim_ids`: claims that cannot remain (blocked, void, mismatch, unapproved). Sort ascending.
6. `close_log_required`:
   - `GET /api/close/logs?area=AP&period={batch_period}` → check for AP-area close logs in the batch's review period.
   - If found → `{ "required": true, "ids": [ascending log_ids] }`.
   - Else → `{ "required": false, "ids": [] }`.
7. `batch_status`: `blocked` if no claims can remain; `needs_ap_refresh` if some stale corrections or close log required but eligible claims remain; `ready_to_send` if all eligible with no corrections.

### Key Rules
- `ap_balance_by_claim` includes ALL candidate claims (eligible and not-ready), each with a balance.
- A `processing` payment keeps the bill balance open (mark_in_flight_payment).
- A `cleared` payment zeros the balance for the matched paid bill.
- Close logs with `area=AP` in the batch period indicate manual journal entries requiring AP refresh.

---

## Task Type 3: Vendor Onboarding KYC Release

**Output fields**: `per_business` (`[{business_id, decision}]`), `reportable_ubo_counts`, `hard_stop_flags`, `follow_up_business_ids`, `overall_release_ready`.

### Controlled Vocabulary — decision
`approve` | `awaiting_information` | `escalate`

### Controlled Vocabulary — hard_stop_flags (alphabetical, empty list if none)
`bank_closed` | `bank_name_mismatch` | `confirmed_pep` | `expired_license` | `missing_required_documents` | `sanctions_confirmed` | `screening_not_run` | `shell_company_suspected` | `vendor_on_hold`

### SOP
1. Parse `as_of_date` and `business_ids` from the onboarding batch payload.
2. For each `business_id`:
   - `GET /api/compliance/objects?business_id={id}` → compliance data.
   - `GET /api/vendors?vendor_id={vendor_id}` (from compliance object) → vendor record.
3. Determine `hard_stop_flags` (collect all that apply, sort alphabetically):

| Flag | Condition |
|------|-----------|
| `bank_closed` | `bank_account_status` = `closed` |
| `bank_name_mismatch` | `bank_account_status` = `name_mismatch` |
| `confirmed_pep` | `pep_status` = `confirmed_pep` |
| `expired_license` | `"license"` NOT in `missing_fields` AND `license_expiry` year-month < `as_of_date` year-month |
| `missing_required_documents` | `missing_fields` is non-empty |
| `sanctions_confirmed` | `sanctions_check_status` = `confirmed` (if present in data) |
| `screening_not_run` | `sanctions_check_status` = `not_run` OR `pep_status` = `not_run` |
| `shell_company_suspected` | `shell_company_suspected` = `true` |
| `vendor_on_hold` | vendor `status` = `on_hold` |

4. Determine `decision`:
   - `approve`: hard_stop_flags is empty.
   - `awaiting_information`: only soft stops present (`missing_required_documents`, `screening_not_run`) — no critical stops.
   - `escalate`: any critical stop (`bank_closed`, `bank_name_mismatch`, `confirmed_pep`, `expired_license`, `sanctions_confirmed`, `shell_company_suspected`, `vendor_on_hold`).

5. `reportable_ubo_counts`: For each business, count unique UBO names where that name's **maximum** `ownership_pct` across all ubo_list entries >= 25 (the reporting threshold). Duplicate names count once.

6. `follow_up_business_ids`: all business IDs where decision != `approve` (i.e. `escalate` or `awaiting_information`), sorted ascending.

7. `overall_release_ready`: `true` only if every business decision is `approve`.

### Key Rules
- `expired_license` uses **year-month** comparison: `license_expiry` YM < `as_of_date` YM. A license expiring in the same month as the review is NOT yet expired.
- If `"license"` is in `missing_fields`, use `missing_required_documents` — do NOT also flag `expired_license` (cannot check expiry of a missing field).
- `screening_not_run` covers both sanctions and PEP screening: triggered by `sanctions_check_status = not_run` OR `pep_status = not_run`.
- UBO count uses unique names, not entries. A name appearing twice at 30% and 10% counts once with max = 30%.
- The current `review_status` field in compliance data is NOT the decision — derive the decision from hard stops independently.

---

## Task Type 4: Prepaid Amortization & GL Reconciliation

**Output fields**: `period`, `entity`, `selected_invoice_ids`, `account_rollup` (per account), `invoice_results`, `default_missing_term_invoice_ids`, `exception_invoice_ids`.

### Controlled Vocabulary — account_status
`reconciled` | `variance_review` | `requires_reconciliation`

### SOP
1. Parse invoice IDs, accounts (e.g. `1250`, `1251`), `period` (e.g. `2025-03`), and `entity` from the prepaid close scope payload.
2. For each `prepaid_invoice_id`:
   - `GET /api/prepaids/invoices?prepaid_invoice_id={id}` → invoice data (use the provided `monthly_amortization` field; alternatively verify: `original_amount` / months_in_service_period, rounded to 2 decimals).
   - **March amortization** = `monthly_amortization` value (full month, no mid-month proration), if the service period includes March. Else 0.
   - **Cumulative amortization through March** = `monthly_amortization` × (number of months from `service_start` month through March, inclusive). E.g. Jan start = 3 months (Jan, Feb, Mar); Mar start = 1 month.
   - **Ending balance** = `original_amount` − `cumulative_amortization_through_march`.
   - `default_missing_term_flag` = `true` if `"missing_contract_dates"` is in `data_quality_flags`, else `false`.
   - `exception_flag` = `true` if `data_quality_flags` is non-empty (any flag, including `rounded_amount`), else `false`.

3. For each account in scope:
   - `GET /api/prepaids/gl-balances?account={acct}&period={period}` → `gl_ending_balance`.
   - Roll up: `selected_invoice_count`, `original_amount_total`, `march_amortization_total`, `cumulative_amortization_through_march`, `schedule_ending_balance` (all sums of invoice values).
   - `variance_amount` = `schedule_ending_balance` − `gl_ending_balance`.
   - `variance_flag` = `true` if `variance_amount` != 0.
   - `has_default_missing_term_flag` = `true` if any invoice in the account has `default_missing_term_flag` = `true`.
   - `account_status`: `requires_reconciliation` if `variance_flag` = true; `variance_review` if variance is 0 but any invoice has `exception_flag` = true; `reconciled` if variance is 0 and no exceptions.

4. `default_missing_term_invoice_ids`: all invoice IDs with `default_missing_term_flag` = true, sorted ascending.
5. `exception_invoice_ids`: all invoice IDs with `exception_flag` = true, sorted ascending.
6. `invoice_results` ordered same as `selected_invoice_ids` (scope file order).

### Key Rules
- `monthly_amortization` is provided in the API data — use it directly. (It equals `original_amount` / service_months, rounded to 2 decimals.)
- Months-in-service = number of month-boundaries from `service_start` to `service_end` inclusive. E.g. Mar 15 → Sep 14 = 6 months; Jan 1 → Dec 31 = 12 months; Mar 1 → Nov 30 = 9 months.
- Rounding can leave a small residual ending balance (e.g. 0.01) even when a service fully amortizes through March. This is expected.
- `default_missing_term_flag` ≠ `exception_flag`: the former is specifically `missing_contract_dates`; the latter is any data quality flag.

---

## Task Type 5: Payment Release after Account-Change Events

**Output fields**: `task_id`, `batch_id`, `as_of_date`, `target_business_ids`, `decisions` (per business_id), `bank_mismatch_ids`, `invalid_tax_ids`, `expired_license_ids`, `review_queue_ids`, `risk_score_override_flags`.

### Controlled Vocabulary — decision
`release` | `hold` | `escalate`

### SOP
1. Parse `batch_id`, `review_date` (= `as_of_date`), `target_business_ids`, and `account_change_events` from the account-change batch payload.
2. For each `business_id`:
   - `GET /api/compliance/objects?business_id={id}` → compliance data.
   - `GET /api/vendors?vendor_id={vendor_id}` → vendor record (optional, for additional context).
3. Detect and collect issue IDs (separate output lists):

| Issue List | Condition |
|------------|-----------|
| `bank_mismatch_ids` | `bank_account_status` = `name_mismatch` |
| `invalid_tax_ids` | `tax_id` is non-numeric after `TIN` prefix OR all-same-digit pattern (e.g. `TIN999999`) |
| `expired_license_ids` | `"license"` NOT in `missing_fields` AND `license_expiry` year-month < `as_of_date` year-month |
| `risk_score_override_flags` | `risk_score` >= 70 |

4. Determine `decision` per business:

| Decision | Condition |
|----------|-----------|
| `release` | No issues detected (clean bank, valid tax, valid license, no PEP risk, risk_score < 70) |
| `hold` | Operational/remediable issues only (bank mismatch/closed, expired license, missing docs, screening not run, risk >= 70) — but NO PEP and NO invalid tax |
| `escalate` | Any of: `pep_status` = `confirmed_pep`, `pep_status` = `possible_pep`, OR `invalid_tax_id` detected |

5. `review_queue_ids` = all business IDs where decision != `release` (i.e. `hold` + `escalate`), sorted ascending.
6. All ID lists sorted ascending by `business_id`.
7. Echo `task_id`, `batch_id`, `as_of_date`, `target_business_ids` from the payload (sorted ascending).

### Key Rules
- Escalation triggers (PEP or invalid tax) override hold — if both an escalation trigger and a hold trigger exist, the decision is `escalate`.
- `bank_closed` (as opposed to `name_mismatch`) → hold (operational, bank needs replacement), NOT escalate.
- `sanctions_check_status = not_run` → hold (screening incomplete), not escalate.
- Tax ID validation: `TIN` prefix + 6 digits. Invalid if: (a) non-numeric chars in the digit portion (e.g. `TIN12X899`), or (b) all digits identical (sentinel/placeholder pattern, e.g. `TIN999999`, `TIN111111`).
- `expired_license` uses **year-month** comparison (same as Task Type 3).
- `risk_score_override_flags` uses `>=` 70 (inclusive).

---

## Common Misjudgments / Exclusion Rules

1. **Stale-snapshot conflicts**: A claim may have multiple AP bills — one stale (wrong vendor/amount or scheduled) and one correct (paid + cleared). Always check the matching bill by amount + vendor, not just the first bill returned.
2. **Paid vs payable**: A `processing` payment (not `cleared`) means the bill is still open. Only `cleared` payments zero the balance.
3. **Claim-vs-AP alignment**: Bill must match claim `amount` AND `vendor_id`. If claim `vendor_id` is `null`, any vendor on the bill is a mismatch. Bills on prepaid accounts (`1250`/`1251`) instead of expense/AP accounts are mismatches for reimbursement batches.
4. **Default/missing-term prepaid flags**: `missing_contract_dates` in `data_quality_flags` → `default_missing_term_flag`. ANY non-empty `data_quality_flags` → `exception_flag`. These are separate: an invoice can have `exception_flag = true` but `default_missing_term_flag = false` (e.g. `rounded_amount` only).
5. **Exception priority ranking**: `default_missing_term_invoice_ids` is always a subset of `exception_invoice_ids`. Both sorted ascending by invoice ID.
6. **License expiry direction**: Compare year-month of `license_expiry` < year-month of `as_of_date`. Same-month expiry is NOT expired. If `"license"` in `missing_fields`, use `missing_required_documents` (cannot assess expiry of a missing license).
7. **UBO counting**: Count unique names (deduplicate), using max `ownership_pct` per name. Threshold is >= 25%.
8. **Tax ID validation**: `TIN` + digits only. All-same-digit (e.g. `999999`) = invalid sentinel. Non-numeric char = invalid.
9. **Decision context matters**: Onboarding KYC (Task 3) uses `approve`/`awaiting_information`/`escalate`. Payment release (Task 5) uses `release`/`hold`/`escalate`. The same PEP flag means `escalate` in both, but bank issues map to `awaiting_information` (KYC) vs `hold` (payment release).
10. **Do not use `review_status` from compliance data as the decision**: Derive decisions from hard-stop evidence, not the source-system review status.
11. **Currency precision**: Report all amounts to 2 decimal places in USD. Despite prompts mentioning "USD cents," answers use dollar amounts with cent precision (e.g. `1842.36`, not `184236`).
12. **Variance direction**: `variance_amount` = `schedule_ending_balance` − `gl_ending_balance`. Positive = schedule over GL; negative = schedule under GL.

---

## Payment-Priority Ranking (for AP payment release ordering)

When ranking AP bills for payment release:
1. Sort by `due_date` ascending (earliest due first).
2. Break ties by `bill_id` ascending.
3. This determines the order in which scheduled/approved bills should be released for payment.

---

## Query Order Cheat Sheet

1. `GET /endpoints` — confirm available paths.
2. **Reimbursement close**: `/api/claims?claim_id=` → `/api/ap/bills?claim_id=` → `/api/ap/payments?bill_id=`
3. **Vendor KYC**: `/api/compliance/objects?business_id=` → `/api/vendors?vendor_id=`
4. **Prepaid close**: `/api/prepaids/invoices?prepaid_invoice_id=` → `/api/prepaids/gl-balances?account=&period=`
5. **Close logs**: `/api/close/logs?area=AP&period=`
6. Always query specific records by ID/param to avoid dumping entire collections.
