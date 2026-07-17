# ERP Finance Expense-Control Skill

## Overview

This skill covers five expense-control workflows in the ERP finance domain:
1. **Claims-to-AP close review** — classify reimbursement claims against AP bills/payments
2. **Vendor onboarding release control** — compliance screening for vendor access decisions
3. **Prepaid close reconciliation** — schedule-to-GL variance analysis with straight-line amortization
4. **Stale AP snapshot reconciliation** — reconcile candidate claims against current ERP state vs stale export
5. **Account-change payment release** — compliance-gated payment release after vendor account-change events

All workflows use a shared ERP finance API. **Always query the API for current data** — never rely on stale snapshots or local files as the system of record.

---

## API Reference

### Base URL

Use the environment-provided base URL. All endpoints accept exact-match query parameters by field name, plus `limit` and `offset` for pagination.

### Endpoints

| Endpoint | Purpose |
|---|---|
| `/api/claims` | Expense claim records. Query by `claim_id`. |
| `/api/ap/bills` | AP reimbursement bills. Query by `claim_id`, `bill_id`. |
| `/api/ap/payments` | Payment records. Query by `bill_id`. |
| `/api/vendors` | Vendor master data. Query by `vendor_id`. |
| `/api/compliance/objects` | Compliance screening records. Query by `business_id`. |
| `/api/prepaids/invoices` | Prepaid invoice schedules. Query by `prepaid_invoice_id`. |
| `/api/prepaids/gl-balances` | GL ending balances by account/period/entity. Query by `account`, `period`, `entity`. |
| `/api/close/logs` | Close/review log entries. Query by `period`, `area`, `related_account`. |
| `/health`, `/endpoints` | Service health and endpoint listing. |

### Data Field Reference

**Claims** (`/api/claims`):
- `claim_id`, `amount` (USD), `status` (submitted/needs_receipt/approved/paid/rejected)
- `approved_date`, `submitted_date`, `category`, `department`, `employee_name`
- `policy_flags` (array: `manual_rate`, `late_receipt`, `over_limit`, `weekend_spend`, `duplicate_amount`)
- `receipt_status` (attached/partial/missing), `vendor_id`, `notes`, `currency`

**AP Bills** (`/api/ap/bills`):
- `bill_id`, `claim_id` (nullable — null means non-reimbursement bill), `vendor_id`
- `amount` (USD), `status` (scheduled/approved/paid/void), `account`, `currency`
- `bill_date`, `due_date`, `invoice_number`, `memo`

**AP Payments** (`/api/ap/payments`):
- `payment_id`, `bill_id`, `vendor_id`, `amount` (USD), `method`
- `status` (scheduled/processing/cleared), `payment_date`, `bank_reference`

**Vendors** (`/api/vendors`):
- `vendor_id`, `vendor_name`, `legal_name`, `status` (active/inactive/on_hold)
- `bank_account_last4`, `tax_id`, `industry`, `payment_terms`, `default_account`, `updated_at`

**Compliance Objects** (`/api/compliance/objects`):
- `business_id`, `business_name`, `vendor_id`, `jurisdiction`, `registration_number`
- `bank_account_status` (verified/name_mismatch/closed)
- `pep_status` (none/possible_pep/confirmed_pep/not_run)
- `sanctions_check_status` (clear/possible_match/confirmed_match/not_run)
- `license_expiry` (date string), `missing_fields` (array)
- `risk_score` (integer 0-100), `review_status` (not_started/in_review/awaiting_information/approved/escalated)
- `shell_company_suspected` (boolean), `ownership_layer_count` (integer)
- `tax_id`, `ubo_list` (array of `{name, ownership_pct}`)

**Prepaid Invoices** (`/api/prepaids/invoices`):
- `prepaid_invoice_id`, `account`, `description`, `vendor_id`
- `original_amount`, `monthly_amortization`, `recognition_method` (straight_line)
- `service_start`, `service_end`, `invoice_date`, `invoice_number`, `source_document`
- `data_quality_flags` (array: `rounded_amount`, `missing_contract_dates`, `manual_override`, `duplicate_invoice_number`)

**GL Balances** (`/api/prepaids/gl-balances`):
- `account`, `account_name`, `entity`, `period` (YYYY-MM)
- `ending_balance`, `source`, `loaded_at`

**Close Logs** (`/api/close/logs`):
- `log_id`, `period`, `area` (AP/Expense/Prepaids/GL/Treasury/Compliance)
- `status` (open/ready_for_review/closed/blocked), `message`, `owner`
- `related_account`, `created_at`

---

## Workflow 1: Claims-to-AP Close Review

### Business Rules

**Classification logic for each claim in the batch:**

1. **PAID** — ALL of the following must be true:
   - A bill exists linked to the claim (`bill.claim_id == claim.claim_id`)
   - The bill's `status` is `"paid"`
   - A payment exists for that bill with `status` `"cleared"`
   - The bill amount matches the claim amount (exact match)

2. **PAYABLE** (can stay in AP queue) — ALL of:
   - Claim `status` is `"approved"`
   - At least one bill exists linked to the claim
   - The bill amount matches the claim amount (exact match)
   - The bill `status` is NOT `"void"`
   - No blocking conditions apply

3. **BLOCKED** — ANY of:
   - Claim `status` is NOT `"approved"` (and not already marked paid) — e.g., `submitted`, `needs_receipt`, `rejected`
   - No AP bill exists linked to the claim
   - All linked bills are `"void"`
   - Bill amount does NOT match claim amount (amount mismatch indicates wrong AP link)
   - Bill memo contains `"Duplicate check required"` with a mismatched amount
   - Claim has `receipt_status: "partial"` combined with policy issues (over_limit, late_receipt)

**CRM-required classification (subset of blocked):**
- Claims needing **expense-case owner cleanup**: missing bill, partial receipt, policy flags (`over_limit`, `late_receipt`), claim not approved
- Claims needing **AP-link remediation**: amount mismatch between claim and bill, void bill, duplicate check memo

**AP Open Balance Total:**
- Sum bill amounts for **payable claims only**
- Use the matching bill (same amount as claim) linked to the claim
- Report in USD cents (multiply by 100) or as a decimal with 2 decimal places (check template)
- Ignore void bills and mismatched bills in the balance computation

**Batch Status:**
- `"blocked"` — any batch item is blocked
- `"open_payables"` — no blocked items, but valid unpaid AP bills remain
- `"ready_to_close"` — all items are paid, no open payables

### Source Precedence
1. Current API claim record (authoritative for claim status/amount)
2. Current API bill records linked by claim_id (authoritative for bill status/amount)
3. Current API payment records linked by bill_id (authoritative for payment status)

### Common Pitfalls
- **Multiple bills per claim**: A claim can have multiple bills (e.g., legacy + current). Match by amount equality to the claim. Ignore stale/legacy bills with different amounts.
- **Bill amount ≠ claim amount**: This is always a blocking mismatch — do not assume the bill is correct.
- **Void bills**: A void bill linked to a claim makes the claim blocked unless another valid paid bill+payment exists.
- **Processing payments**: A bill with a `processing` payment is NOT paid — payment must be `cleared`.
- **Scheduled payments**: A `scheduled` payment is NOT cleared — do not classify as paid.

---

## Workflow 2: Vendor Onboarding Release Control

### Business Rules

**Decision matrix per business:**

| Condition | Decision |
|---|---|
| Any hard-stop flag present, OR vendor `on_hold`, OR review `escalated` | `escalate` |
| `review_status` is `in_review` or `awaiting_information`, no hard stops | `awaiting_information` |
| `review_status` is `approved` or `not_started`, no hard stops, no blocking issues | `approve` |
| `sanctions_check_status` is `possible_match` without hard stops | `awaiting_information` |
| `pep_status` is `possible_pep` without other hard stops | `awaiting_information` |

**Hard-stop flag mapping (compliance → flag):**

| Compliance Field Value | Hard-Stop Flag |
|---|---|
| `bank_account_status: "closed"` | `bank_closed` |
| `bank_account_status: "name_mismatch"` | `bank_name_mismatch` |
| `pep_status: "confirmed_pep"` | `confirmed_pep` |
| `license_expiry` < as_of_date (expired) | `expired_license` |
| `missing_fields` is non-empty (contains `"license"`, `"beneficial_owner_id"`, `"bank_statement"`, `"website"`, etc.) | `missing_required_documents` |
| `sanctions_check_status: "confirmed_match"` | `sanctions_confirmed` |
| `sanctions_check_status: "not_run"` | `screening_not_run` |
| `shell_company_suspected: true` | `shell_company_suspected` |
| Vendor `status: "on_hold"` | `vendor_on_hold` |

**UBO reporting threshold: 25% ownership.**

- Count unique UBO **names** across all ownership layers
- Aggregate multiple entries for the same name (sum their `ownership_pct`)
- Count the name if the aggregated percentage ≥ 25%
- `pep_status: "not_run"` does NOT trigger `screening_not_run` (that flag is for sanctions check not run)

### Output Conventions
- All ID lists sorted **ascending** (lexicographic for business IDs, claim IDs, log IDs)
- Hard-stop flag lists sorted **alphabetically** by flag enum value
- Empty lists `[]` when no items, never `null`
- `overall_release_ready`: `true` only when ALL businesses in the batch have decision `"approve"`; `false` if any business is `"awaiting_information"` or `"escalate"`
- `follow_up_business_ids`: all business IDs whose decision is NOT `"approve"` (i.e., `"awaiting_information"` or `"escalate"`)

### Common Pitfalls
- **`pep_status: "not_run"` ≠ `screening_not_run`**: `screening_not_run` refers to sanctions screening, not PEP screening. Only `sanctions_check_status: "not_run"` triggers `screening_not_run`.
- **`pep_status: "possible_pep"`** is NOT a hard stop — only `confirmed_pep` is.
- **License expiry date comparison**: Use the `as_of_date` from the batch payload. If `license_expiry < as_of_date`, the license is expired.
- **Vendor status `on_hold`** maps to the `vendor_on_hold` hard-stop flag, not a separate category.
- **Multiple UBO entries for same name**: Aggregate ownership percentages before checking the 25% threshold.
- **`missing_fields` containing `"license"`**: This is `missing_required_documents`, NOT `expired_license`. Only use `expired_license` when the license date has passed.

---

## Workflow 3: Prepaid Close Reconciliation

### Business Rules

**Amortization method: Straight-line monthly.**

- `monthly_amortization` is provided in the invoice record — use it directly
- For March 2025 period: March is month index relative to `service_start`
  - If `service_start` is 2025-01-01: January=month 1, February=month 2, March=month 3
  - March amortization = `monthly_amortization` (one month's worth)

**Cumulative amortization through March:**
- Count full months from `service_start` through the close period end
- If `service_start <= 2025-03-01`: count months from start through March inclusive
- `cumulative = monthly_amortization × months_elapsed`

**Schedule ending balance:**
- `original_amount - cumulative_amortization_through_march`

**Invoice-level fields:**
- `march_amortization`: the monthly amortization for March (same as `monthly_amortization` unless the service started/ended mid-March)
  - If `service_start` is after March 2025, amortization is 0
  - If `service_end` is before March 2025, amortization is 0
  - Otherwise, use the full `monthly_amortization` value
- `cumulative_amortization_through_march`: see formula above
- `ending_balance`: `original_amount - cumulative_amortization_through_march`
- `default_missing_term_flag`: `true` if `data_quality_flags` contains `"missing_contract_dates"` or `"manual_override"` or if the invoice is missing service dates
- `exception_flag`: `true` if `data_quality_flags` is non-empty (any quality flag is present)

**Account-level rollup (for each account):**
- `selected_invoice_count`: number of scoped invoices in that account
- `original_amount_total`: sum of `original_amount` for all scoped invoices in that account
- `march_amortization_total`: sum of `march_amortization`
- `cumulative_amortization_through_march`: sum of cumulative across invoices
- `schedule_ending_balance`: `original_amount_total - cumulative_amortization_through_march`
- `gl_ending_balance`: from GL balances API for the account/period/entity
- `variance_amount`: `schedule_ending_balance - gl_ending_balance`
- `variance_flag`: `true` if `abs(variance_amount) > variance_threshold_abs` (from scope config)

**Account status:**
- `"reconciled"` — `variance_flag` is false AND no invoice in the account has an exception flag AND no default/missing term flag
- `"variance_review"` — `variance_flag` is true (regardless of exceptions)
- `"requires_reconciliation"` — `variance_flag` is false BUT exceptions or default/missing terms exist

**Default/missing term flag at account level:**
- `true` if ANY invoice in the account has `default_missing_term_flag: true`

### Output Ordering
- `selected_invoice_ids`: same order as `prepaid_close_scope.json`
- `invoice_results`: same order as `prepaid_close_scope.json`
- `default_missing_term_invoice_ids`: ascending by invoice ID
- `exception_invoice_ids`: ascending by invoice ID

### Common Pitfalls
- **Service period boundaries**: If `service_start` is mid-month (e.g., 2025-03-15), March is month 1. Full amortization applies for that partial month (no proration).
- **Months elapsed calculation**: Count calendar months from start through the close period. A service starting 2025-01-15 has January as month 1, February as month 2, March as month 3.
- **`data_quality_flags` drives exceptions**: Any non-empty flag array means `exception_flag: true`. The specific flag determines `default_missing_term_flag`.
- **GL balance lookup**: Match exactly on `account`, `period` (YYYY-MM), and `entity` from the scope config.

---

## Workflow 4: Stale AP Snapshot Reconciliation

### Business Rules

**Source precedence (always):**
1. Current API claims (authoritative for claim status/amount)
2. Current API bills (authoritative for bill status/amount)
3. Current API payments (authoritative for payment status)
4. Stale CSV snapshot (context only — do NOT use as system of record)

**Eligibility (eligible_claim_ids):**
A claim can remain in the batch if:
- Claim `status` is `"approved"` (current API)
- At least one non-void bill linked to the claim exists with a matching amount
- No blocking conditions (see not_ready below)

**Not ready (not_ready_claim_ids):**
- Claim `status` is not `"approved"` (e.g., `needs_receipt`, `submitted`, `rejected`)
- All linked bills are void
- Bill amount ≠ claim amount (amount mismatch)
- Claim has `receipt_status: "partial"` or `"missing"` with no cleared payment
- Bill is paid+cleared but for a different amount than the claim

**AP balance computation:**
- For each candidate claim, find the matching non-void bill (same amount as claim)
- Subtract any cleared payment amount for that bill
- `ap_balance = bill_amount - sum(cleared_payment_amounts)`
- For claims with no bill or only void bills: balance is 0 (not in AP)
- For paid claims: balance is 0 (fully paid)

**Stale snapshot corrections — map each claim to ONE correction:**

| Current State | Correction |
|---|---|
| Payment exists in API (cleared/processing) but snapshot shows `none`/0 | `mark_in_flight_payment` |
| Bill+payment match claim amount, snapshot shows different bill or status | `replace_with_matched_paid_bill` |
| Bill amount or vendor differs between current API and snapshot | `exclude_amount_or_vendor_mismatch` |
| Bill status is `void` in current API | `ignore_void_bill` |
| Claim status is NOT `approved` in current API | `block_unapproved_claim` |
| Snapshot matches current API state (same bill status, same payment status) | `current_snapshot_ok` |

**Close log requirements:**
- Check close logs API for entries where:
  - `area` is `"AP"` or `"Expense"`
  - `period` matches the relevant close period
  - `status` is NOT `"closed"` (i.e., `open`, `ready_for_review`, `blocked`)
- `close_log_required.required`: `true` if ANY non-closed AP/Expense log exists
- `close_log_required.ids`: list of matching log IDs, ascending

**Batch status:**
- `"ready_to_send"` — all claims eligible, no stale corrections needed beyond `current_snapshot_ok`
- `"needs_ap_refresh"` — some claims eligible but snapshot corrections needed (stale data)
- `"blocked"` — any claim is not ready

### Common Pitfalls
- **Snapshot is NOT authoritative**: Always cross-reference against current API. The snapshot can be outdated (bill status changed, payment arrived after snapshot).
- **One correction per claim**: Choose the most severe/descriptive correction that applies.
- **Multiple bills per claim**: A claim can have both a stale/legacy bill and a current paid bill. Match by amount equality to the claim amount.
- **`processing` vs `cleared` payment**: Only `cleared` payments reduce the AP balance. `processing` payments are in flight but not yet settled.

---

## Workflow 5: Account-Change Payment Release

### Business Rules

**Decision matrix per business (release/hold/escalate):**

| Condition | Decision |
|---|---|
| Any hard compliance flag (see below), OR vendor `on_hold`, OR `risk_score >= 70` | `escalate` |
| `review_status` is `in_review` or `awaiting_information`, no hard flags, risk < 70 | `hold` |
| `review_status` is `not_started`, no hard flags, risk < 70 | `hold` |
| `sanctions_check_status: "not_run"`, no other hard flags | `hold` |
| `sanctions_check_status: "possible_match"`, no other hard flags | `hold` |
| `pep_status: "possible_pep"`, no other hard flags | `hold` |
| `review_status: "approved"`, no hard flags, risk < 70, sanctions clear, bank verified | `release` |

**Bank mismatch check:**
- Compare the `requested_bank_last4` from the account-change event to the vendor's `bank_account_last4`
- If they differ, flag as bank mismatch AND check compliance `bank_account_status` for `name_mismatch`

**Hard compliance flags (same mapping as Workflow 2):**
- `bank_account_status: "closed"` → escalate
- `bank_account_status: "name_mismatch"` → escalate
- `pep_status: "confirmed_pep"` → escalate
- `license_expiry < as_of_date` → escalate
- `missing_fields` non-empty → escalate
- `sanctions_check_status: "confirmed_match"` → escalate
- `sanctions_check_status: "not_run"` → hold (not escalate)
- `shell_company_suspected: true` → escalate

**Specific output lists:**
- `bank_mismatch_ids`: business IDs where compliance `bank_account_status == "name_mismatch"`
- `invalid_tax_ids`: business IDs where the vendor `tax_id` does not match the compliance `tax_id`
- `expired_license_ids`: business IDs where `license_expiry < as_of_date`
- `review_queue_ids`: business IDs where decision is `hold` OR `escalate` (any non-release)
- `risk_score_override_flags`: business IDs where `risk_score >= 70`

### Common Pitfalls
- **Tax ID validation**: Compare the tax_id from `/api/vendors` against the tax_id from `/api/compliance/objects`. Non-matching or non-standard format tax IDs (e.g., containing letters beyond the TIN prefix) mean the business belongs in `invalid_tax_ids`.
- **Risk score threshold of 70**: `>= 70` means `escalate` and inclusion in `risk_score_override_flags`.
- **Bank matching uses compliance data**: `bank_mismatch_ids` is populated from compliance `bank_account_status: "name_mismatch"`, not from comparing last4 digits. The last4 comparison from the account-change event is additional context.
- **`review_status: "escalated"`** in compliance means automatic `escalate` decision.

---

## Cross-Cutting Conventions

### Amount Handling
- All amounts in **USD**
- Report to **2 decimal places** unless the template specifies USD cents (integer)
- When computing balances, sum exact values then round the final result to 2 decimals

### Sort Order
- All ID lists: **ascending** lexicographic order (standard string sort)
- Hard-stop flag lists: **alphabetical** by enum value
- Invoice result lists: **same order as input scope file**
- Business ID lists: **ascending** by business_id

### ID Formats
- Claims: `CLM-YYYY-NNNN` or `CLM-YYYY-CATEGORY-NNN`
- Bills: `AP-YYYY-NNNN` or `AP-YYYY-REIM-NNN`
- Payments: `PAY-YYYY-NNNN`
- Businesses: `BUS-YYYY-NNNN`
- Vendors: `VEN-NNNN`
- Prepaid invoices: `PPD-YYYY-NNNN` or `PPD-AUR-ACCT-XXX-NNN`
- Close logs: `CLOSE-YYYY-MM-NNN`
- Account-change tickets: `ACT-YYMMDD-NNN`

### API Query Pattern
1. Query the relevant list endpoint with the exact-match field parameter
2. The API returns `{count, data[], endpoint, limit, offset, total}`
3. Use `limit` and `offset` for pagination when `total > count`
4. Filtering is exact-match only — query one ID at a time for precision

### Data Quality Signals
- **`policy_flags` on claims**: Non-empty flags indicate data quality or policy issues — these affect CRM-required classification
- **`data_quality_flags` on prepaid invoices**: Non-empty flags trigger exception flags and may trigger default/missing term flags
- **`missing_fields` on compliance objects**: Non-empty means `missing_required_documents` hard stop
- **`memo` fields on bills**: Look for keywords like `"Duplicate check required"`, `"Imported from AP inbox"`, `"Accrual review"`, `"Partial receipt support noted"` — these signal potential issues

### Error Recovery
- If an API endpoint returns empty results for a known ID, treat it as "no record exists" (not an error)
- If a claim has no linked bill, it has no AP representation — classify accordingly
- If a bill has no linked payment, treat the payment amount as 0
