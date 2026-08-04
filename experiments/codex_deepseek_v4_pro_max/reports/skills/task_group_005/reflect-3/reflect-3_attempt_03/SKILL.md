## When to use

Use this skill for ERP finance-operations tasks that require reconciling expense claims, AP bills, payments, vendor compliance, prepaid amortization schedules, or account-change release reviews against a shared JSON API. The skill applies when the task involves:

- Expense reimbursement close reviews (claims → bills → payments)
- Vendor onboarding finance-risk assessments (compliance, ownership, screening, bank)
- Prepaid-expense close reconciliations (invoice schedules vs. GL balances)
- Stale AP snapshot reconciliations (snapshot vs. live ERP state)
- Account-change payment-release risk reviews (vendor, compliance, tax, license)

## API interaction rules

**Base URL:** The runner supplies `<TASK_ENV_BASE_URL>`. Always use this as the prefix for every request. Do not hardcode a URL.

**Collection endpoints** accept exact-match query parameters by field name plus optional `limit` and `offset` integers:

- `GET /api/claims` — all expense claims
- `GET /api/claims/{claim_id}` — single claim detail
- `GET /api/ap/bills` — AP bills; filter with `claim_id` or `bill_id`
- `GET /api/ap/payments` — payments; filter with `bill_id`
- `GET /api/vendors` — vendor master; filter with `vendor_id`
- `GET /api/compliance/objects` — combined compliance records; filter with `business_id`
- `GET /api/compliance/ownership/{business_id}` — UBO ownership
- `GET /api/compliance/registry/{business_id}` — jurisdiction, license, tax ID
- `GET /api/compliance/screening/{business_id}` — PEP and sanctions status
- `GET /api/compliance/bank/{business_id}` — bank account status
- `GET /api/prepaids/invoices` — prepaid invoice schedules; filter with `prepaid_invoice_id`
- `GET /api/prepaids/gl-balances` — GL balances by account and period
- `GET /api/close/logs` — close log entries

All detail endpoints replace `{claim_id}` or `{business_id}` with the literal identifier. Collection endpoints return `count`, `data[]`, `limit`, `offset`, and `total`.

## Cross-entity reconciliation patterns

### Claims → Bills → Payments

When reconciling claims for reimbursement:

1. Fetch each claim by ID from `/api/claims/{claim_id}`.
2. Fetch linked bills via `/api/ap/bills?claim_id=...`.
3. Fetch payments for each bill via `/api/ap/payments?bill_id=...`.
4. A claim is **settled** only when: the claim status is `paid` or `approved`, a bill exists with matching amount and vendor, that bill is `paid`, and a payment exists for that bill with status `cleared`.
5. A claim is **payable** when: claim is `approved`, a bill exists with matching amount and vendor, the bill is `scheduled` or `approved`, and the payment is either absent or not yet `cleared`.
6. A claim is **blocked** when: no bill exists, the bill amount differs from the claim amount, the bill vendor differs from the claim vendor (and claim vendor is not null), or the bill is `void`.
7. Use the claim's own amount as the reference value; a bill with a different amount is a mismatch even if the bill exists.

**AP open balance:** Sum the amounts of non-void bills for the claim, then subtract the sum of `cleared` payment amounts for those bills. Processing/scheduled payments do not reduce the open balance.

**CRM-required claims:** Claims blocked because the expense case or AP link needs owner cleanup. This includes claims with no bill, amount/vendor mismatched bills, void bills, and claims with unapproved status.

### Stale-snapshot correction mapping

When a stale snapshot row disagrees with the live API, assign exactly one correction per claim:

| Live state vs. snapshot | Correction |
|---|---|
| Payment now exists (processing/scheduled/cleared) that was absent in snapshot | `mark_in_flight_payment` |
| Snapshot bill is wrong; a different bill with matching amount/vendor exists and is paid with cleared payment | `replace_with_matched_paid_bill` |
| Bill amount != claim amount, or bill vendor != claim vendor | `exclude_amount_or_vendor_mismatch` |
| Bill is `void` in live API | `ignore_void_bill` |
| Claim status is not `approved` in live API | `block_unapproved_claim` |

### Batch status (claims close)

- `blocked` — any claim in the batch is blocked.
- `open_payables` — no blocked claims, but valid unpaid AP reimbursement bills remain.
- `ready_to_close` — no blocked claims and no open payables.

### Batch status (stale AP reconciliation)

- `blocked` — any claim is unapproved or has an uncorrectable issue.
- `needs_ap_refresh` — claims need the stale snapshot updated/replaced.
- `ready_to_send` — all claims are clean after reconciliation.

## Compliance decision rules

### Vendor onboarding / account-change release

For each business ID, gather records from:
- `/api/compliance/objects?business_id=...` (or individual detail endpoints)
- `/api/vendors?vendor_id=...` for the vendor linked in the compliance object

Then evaluate these factors:

**Hard-stop flags to collect per business (use empty list when none apply):**

| Condition | Flag |
|---|---|
| `bank_account_status` is `closed` | `bank_closed` |
| `bank_account_status` is `name_mismatch` | `bank_name_mismatch` |
| `pep_status` is `confirmed_pep` | `confirmed_pep` |
| `license_expiry` < as_of_date | `expired_license` |
| `missing_fields` is non-empty | `missing_required_documents` |
| `sanctions_check_status` is `not_run` | `screening_not_run` |
| `shell_company_suspected` is true | `shell_company_suspected` |
| Vendor `status` is `on_hold` | `vendor_on_hold` |

Sort flags alphabetically per business.

**Decision (approve / awaiting_information / escalate):**

- `approve` — no hard-stop flags, license valid, bank verified, PEP clear/none, sanctions clear, vendor active.
- `awaiting_information` — minor issues that can be resolved with more data (e.g., missing documents where the rest looks clean).
- `escalate` — one or more serious hard-stop flags (bank closed, confirmed PEP, sanctions issues, vendor on hold, or multiple flags).

Do not copy the `review_status` field from the compliance object; make an independent assessment.

**UBO reporting threshold:** Count unique beneficial-owner names where at least one ownership entry meets or exceeds 25%. Count unique names, not entries (duplicate names with multiple ownership slices count once if any slice >= 25%).

**Additional lists for account-change release:**

- `bank_mismatch_ids` — business IDs where compliance `bank_account_status` is `name_mismatch` only (not `closed`).
- `invalid_tax_ids` — business IDs where the vendor's `tax_id` does not match the compliance registry `tax_id`.
- `expired_license_ids` — business IDs where `license_expiry` < `as_of_date`.
- `risk_score_override_flags` — business IDs where compliance `risk_score` >= 70.
- `review_queue_ids` — business IDs that require compliance/AP review before release; include all non-release businesses.

## Prepaid close reconciliation

### Per-invoice calculations

For each prepaid invoice in the scope:

1. **Period amortization:** Use the `monthly_amortization` value directly. Mid-month starts still count as a full period's amortization for that month.
2. **Cumulative amortization through close period:** Count the number of months from `service_start` through the close period (inclusive of the start month). Multiply by `monthly_amortization`. For the final period of a fully-amortized invoice, cap cumulative at `original_amount` to avoid negative balances.
3. **Ending balance** = `original_amount` - `cumulative_amortization_through_period`. Small rounding residuals (e.g., 0.01) are expected and should be preserved as-is in the output.
4. **default_missing_term_flag** = true if `data_quality_flags` contains `missing_contract_dates`.
5. **exception_flag** = true if `data_quality_flags` is non-empty.

### Account rollup

Group invoices by account. For each account compute:

- `selected_invoice_count` — count of scoped invoices in that account.
- `original_amount_total` — sum of original amounts.
- `period_amortization_total` — sum of period amortizations.
- `cumulative_amortization_through_period` — sum of cumulative amortizations.
- `schedule_ending_balance` — sum of per-invoice ending balances.
- `gl_ending_balance` — from `/api/prepaids/gl-balances`, match the account and close period.
- `variance_amount` = `schedule_ending_balance` - `gl_ending_balance`.
- `variance_flag` = true if `|variance_amount|` > configured threshold.
- `has_default_missing_term_flag` = true if any invoice in the account has the flag.
- `account_status`:
  - `requires_reconciliation` — variance at or above threshold. Use this for both accounts when variance is significant.
  - `variance_review` — moderate variance needing review.
  - `reconciled` — variance within threshold.

### Data-quality lists

- `default_missing_term_invoice_ids` — invoice IDs where `default_missing_term_flag` is true, sorted ascending.
- `exception_invoice_ids` — invoice IDs where `exception_flag` is true, sorted ascending.

## General conventions

- All currency amounts in USD with 2-decimal precision.
- Sort ID lists ascending (lexicographic for claim IDs, business IDs, invoice IDs).
- Preserve the distinction between reimbursement case issues (claim-level) and AP/payment evidence issues (bill/payment-level) when populating output fields.
- When a field allows an enum, use exactly the allowed values; do not invent new ones.
- Boolean flags are true/false, not 1/0.
- Output only the JSON object matching the answer template; no narrative text outside JSON.
- Read all payload files from `input/payloads/` for task-specific batch lists, scope definitions, and answer templates.
