# ERP Finance Expense-Control Skill

## Environment

All API calls use the shared remote base URL from `environment_access.md`:
`http://34.46.77.124:8005`. Never use localhost, 127.0.0.1, or local env scripts.

## Available API Endpoints

Every endpoint is available both with and without the `/api/` prefix:

| Short Path | Long Path | Returns |
|---|---|---|
| `/claims` | `/api/claims` | Expense claim records (id, status, amount, vendor, submitter, etc.) |
| `/bills` | `/api/ap/bills` | AP bill records (id, claim_id, status, amount, vendor_id, etc.) |
| `/payments` | `/api/ap/payments` | Payment records (id, bill_id, amount, status, cleared_date, etc.) |
| `/vendors` | `/api/vendors` | Vendor master data (id, name, bank info, tax_id, status, etc.) |
| `/compliance/objects` | `/api/compliance/objects` | Compliance records per business/vendor (bank_account_status, pep_flag, sanctions_flag, screening_status, license_expiry, risk_score, ubo records, shell_company_flag, on_hold_flag, tax_id_status, required_docs) |
| `/prepaids/invoices` | `/api/prepaids/invoices` | Prepaid invoice schedules (id, account, original_amount, start_date, term_months, monthly_amortization, cumulative_amortization, default_term_flag, etc.) |
| `/gl/balances` | `/api/prepaids/gl-balances` | GL ending balances by account and period |
| `/close/logs` | `/api/close/logs` | Close log entries (id, period, status, unresolved_items, etc.) |
| `/health` | — | Health check |
| `/endpoints` | — | Lists available endpoints |

## General Conventions

### Currency
- All amounts in **USD**.
- **Two decimal places**. Use cents representation where the template says "USD cents"; otherwise report dollar amounts with `.NN` precision.
- When summing: sum raw values, then round to 2 decimals.

### Sorting
- All ID lists (claim IDs, business IDs, invoice IDs, close-log IDs) must be sorted **ascending** (lexicographic for strings like `CLM-2025-*`, `BUS-2025-*`, `PPD-*`).
- Invoice result arrays and selected-invoice-ID arrays preserve the **input scope order** (the order given in the payload).

### Source of Truth
- **Live API data is authoritative.** Provided CSV snapshots, local payloads, or batch manifests are context only. Always cross-reference against current API records.
- If a snapshot says a bill is scheduled but the live API shows it as void, the live status wins.
- If a snapshot says a claim is approved but the live API shows it as pending or rejected, the live status wins.

### Enum Values
- Use only the exact allowed values listed in each answer template. Do not invent or abbreviate.

---

## Domain 1: Claims & AP Reimbursement Close (Train 001, 004)

### Data Sources
1. **Claims** (`/claims`) — claim status, claim amount, vendor, submitter.
2. **AP Bills** (`/bills`) — bill status, bill amount, bill-to-claim linkage via `claim_id`, vendor_id.
3. **Payments** (`/payments`) — payment status (`cleared`, `scheduled`, `none`), amount, linked `bill_id`.
4. **Close Logs** (`/close/logs`) — unresolved close entries that may block batch release.

### Claim Classification Rules

#### Paid Claims (`paid_claim_ids` / similar)
A claim is **paid** when ALL of:
- The claim exists in `/claims` with status `approved`.
- A matching AP bill exists (linked by claim_id) with status `paid`.
- A payment exists for that bill with status `cleared` and amount matching the bill amount.

#### Payable / Eligible Claims (`payable_claim_ids` / `eligible_claim_ids`)
A claim is **payable/eligible** when ALL of:
- The claim exists in `/claims` with status `approved`.
- A matching AP bill exists with status `scheduled` or `approved` (NOT `void`, NOT `paid`).
- No blocking issues (see below).
- The bill amount matches the claim amount (within reasonable tolerance).
- The vendor on the bill matches the vendor on the claim.

#### Blocked / Not-Ready Claims (`blocked_claim_ids` / `not_ready_claim_ids`)
A claim is **blocked/not-ready** when ANY of:
- Claim status is NOT `approved` (e.g., `pending`, `rejected`, `draft`).
- The linked AP bill is `void`.
- The linked AP bill has a vendor mismatch with the claim.
- The linked AP bill has an amount mismatch with the claim.
- Unresolved partial-support or receipt-review flags exist.
- A close log entry for the period is unresolved and relates to the claim.

### CRM vs AP Issue Distinction
When populating `crm_required_claim_ids`:
- **CRM required**: The issue is with the expense case itself — claim not approved, submitter documentation missing, receipt support under review, expense policy violation.
- **AP-only issue**: The claim is fine but the AP bill link is broken — void bill, vendor mismatch on bill, stale bill record.
- A claim can appear in both `blocked_claim_ids` and `crm_required_claim_ids`.

### AP Open Balance
- `ap_open_balance_total`: Sum of (bill amount − cleared payment amount) for all **payable** claims only.
- Per-claim `ap_balance_by_claim`: For each candidate claim, bill amount minus sum of cleared payments. If no bill exists or bill is void, balance is `0.00`. If bill is paid and payment cleared, balance is `0.00`.

### Stale Snapshot Corrections (Train 004)
When a stale CSV snapshot is provided alongside live API data, assign one of:
- `current_snapshot_ok` — snapshot matches live state.
- `mark_in_flight_payment` — bill is scheduled/approved, payment not yet cleared, snapshot shows none.
- `replace_with_matched_paid_bill` — snapshot shows old bill; live API shows a different bill that is paid.
- `exclude_amount_or_vendor_mismatch` — bill exists but amount or vendor doesn't match the claim.
- `ignore_void_bill` — snapshot bill is now void in live API.
- `block_unapproved_claim` — claim is not approved in live API.

### Close Log Requirements
- Check `/close/logs` for unresolved entries related to the period under review.
- If any unresolved close-log entry exists for the reviewed period, set `close_log_required.required = true` and list the relevant close-log IDs in `close_log_required.ids`.

### Batch Status (Claims Domain)
- `ready_to_close` — all claims paid (no payable, no blocked).
- `open_payables` — at least one payable claim, zero blocked.
- `blocked` — at least one blocked claim.
- `ready_to_send` — all candidate claims eligible, zero not-ready.
- `needs_ap_refresh` — mix of eligible and not-ready, or close-log action needed.
- `blocked` — no eligible claims, or hard blocks present.

---

## Domain 2: Vendor Onboarding & Compliance Release (Train 002, 005)

### Data Sources
1. **Vendors** (`/vendors`) — vendor_id, business_id, bank info (last4), tax_id, license_expiry, status.
2. **Compliance Objects** (`/compliance/objects`) — per business_id: bank_account_status, pep_flag, sanctions_flag, screening_status, license_expiry, risk_score, ubo records (name + ownership_pct), shell_company_flag, on_hold_flag, tax_id_status, required_documents_status.

### Decision Logic

#### Per-Business Decision (`approve` / `release`)
A business can be **approved/released** when ALL of:
- Bank account status is `verified` (no `name_mismatch`, no `closed`).
- No PEP flag confirmed.
- No sanctions match confirmed.
- Screening has been run and is clear.
- License is not expired relative to the review/as_of date.
- Tax ID is valid.
- All required documents are present.
- Not flagged as shell company.
- Not on hold.
- Risk score < 70 (or below the applicable override threshold).
- UBO information is complete.

#### `awaiting_information` / `hold`
Use when:
- Some compliance checks are incomplete (screening not run, missing documents) but no hard-stop flags are present.
- Minor issues that can be resolved with additional information.
- Bank mismatch exists but can potentially be corrected.

#### `escalate`
Use when ANY hard-stop flag is present:
- `confirmed_pep`
- `sanctions_confirmed`
- `shell_company_suspected`
- `vendor_on_hold`
- `bank_closed`
- Multiple severe flags in combination.
- Expired license combined with other flags.

### Hard-Stop Flags (Train 002)
Flag values (alphabetical order in output):
- `bank_closed` — compliance bank_account_status is `closed`.
- `bank_name_mismatch` — compliance bank_account_status is `name_mismatch`.
- `confirmed_pep` — compliance pep_flag is true/confirmed.
- `expired_license` — license_expiry date < as_of_date/review_date.
- `missing_required_documents` — required_documents_status is incomplete/missing.
- `sanctions_confirmed` — compliance sanctions_flag is true/confirmed.
- `screening_not_run` — compliance screening_status is not_run/pending.
- `shell_company_suspected` — compliance shell_company_flag is true.
- `vendor_on_hold` — compliance on_hold_flag is true.

Assign flags per business_id. Use an empty list `[]` when none apply.

### UBO Reporting (Train 002)
- Count unique beneficial owner **names** (not records) where `ownership_pct` >= the reporting threshold (typically 25%).
- Report as an integer per business_id in `reportable_ubo_counts`.

### Account-Change Specific Fields (Train 005)

#### Bank Mismatch
- `bank_mismatch_ids`: Business IDs where compliance `bank_account_status` is `name_mismatch`.
- Also cross-check: if the change ticket's `requested_bank_last4` doesn't match the vendor's bank last4 in the compliance record, flag as mismatch.

#### Invalid Tax IDs
- `invalid_tax_ids`: Business IDs where compliance `tax_id_status` is `invalid` or equivalent.

#### Expired Licenses
- `expired_license_ids`: Business IDs where `license_expiry` < `as_of_date` (review date). Use the `as_of_date` field from the template as the comparison date.

#### Review Queue
- `review_queue_ids`: Any business_id that has at least one flag, mismatch, invalid tax ID, expired license, or risk_score concern. In other words, every business that is NOT a clean `release`.

#### Risk Score Override
- `risk_score_override_flags`: Business IDs where compliance `risk_score >= 70`.

### Overall Release Ready
- `overall_release_ready = true` ONLY if every listed business has decision `approve`/`release`.
- If any business is `awaiting_information`, `hold`, or `escalate`, set `false`.

---

## Domain 3: Prepaid Expense Close (Train 003)

### Data Sources
1. **Prepaid Invoices** (`/prepaids/invoices`) — prepaid_invoice_id, account (chart-of-account code), original_amount, start_date, term_months, monthly_amortization, cumulative_amortization (through current period), default_term_flag.
2. **GL Balances** (`/gl/balances`) — ending_balance by account and period.

### Amortization Model
- **Straight-line monthly amortization** as represented in the invoice records.
- `monthly_amortization = original_amount / term_months` (already computed in source records).
- `cumulative_amortization_through_march` = sum of monthly amortizations from `start_date` through the close period (inclusive). The source records provide this pre-computed.

### Invoice-Level Fields
For each invoice in the scope (output in scope order):
- `prepaid_invoice_id`: as given.
- `account`: chart-of-account code (1250 or 1251).
- `march_amortization`: the monthly amortization amount for the close period (March).
- `cumulative_amortization_through_march`: total amortization from start through March.
- `ending_balance`: `original_amount - cumulative_amortization_through_march`. Rounded to 2 decimals.
- `default_missing_term_flag`: `true` if the invoice has `default_term_flag` set in source data.
- `exception_flag`: `true` when:
  - The invoice has a `default_missing_term_flag`.
  - The ending balance is 0.00 (or very near zero, e.g., 0.01) while the invoice still has remaining term — indicates potential early write-off.
  - Any data quality issue (negative balances, mismatched cumulative amortization, etc.).

### Account-Level Rollup
For each account (1250, 1251):
- `account_name`: from GL or prepaid source (e.g., "Prepaid Expenses" for 1250, "Prepaid Insurance" for 1251).
- `selected_invoice_count`: number of scoped invoices for that account.
- `original_amount_total`: sum of `original_amount` across scoped invoices.
- `march_amortization_total`: sum of `march_amortization` across scoped invoices.
- `cumulative_amortization_through_march`: sum of `cumulative_amortization_through_march` across scoped invoices.
- `schedule_ending_balance`: `original_amount_total - cumulative_amortization_through_march`.
- `gl_ending_balance`: from `/gl/balances` for that account and period.
- `variance_amount`: `schedule_ending_balance - gl_ending_balance` (can be negative).
- `variance_flag`: `true` when `|variance_amount| > variance_threshold_abs` (typically 100.00 USD).
- `has_default_missing_term_flag`: `true` if ANY scoped invoice in that account has `default_missing_term_flag = true`.
- `account_status`:
  - `reconciled` — variance_flag is false AND has_default_missing_term_flag is false.
  - `variance_review` — variance_flag is true but no default/missing term issues (small or explainable variance).
  - `requires_reconciliation` — variance_flag is true with other flags, or has_default_missing_term_flag is true, or significant unexplained variance.

### Default/Missing Term & Exception Invoice ID Lists
- `default_missing_term_invoice_ids`: All scoped invoice IDs where `default_missing_term_flag = true`, sorted ascending.
- `exception_invoice_ids`: All scoped invoice IDs where `exception_flag = true`, sorted ascending.

---

## Cross-Cutting Workflow

### API Query Strategy
1. **Fetch all relevant data in parallel** where possible — claims, bills, payments, vendors, compliance objects, prepaid invoices, and GL balances are independent.
2. **Filter by scope** after fetching — the APIs may return more records than needed; filter to the candidate IDs from the task batch.
3. **Join records** by linking keys: `claim_id` between claims and bills, `bill_id` between bills and payments, `business_id` between vendors and compliance, `vendor_id` between vendors and change tickets.

### Common Pitfalls
1. **Using stale/snapshot data as truth.** Always verify against live API. The snapshot is context, not authority.
2. **Mixing up claim status and bill status.** A claim can be `approved` while its bill is `void` — this means the claim is blocked, not payable.
3. **Forgetting to deduct cleared payments** when computing AP open balances.
4. **Not distinguishing CRM issues from AP issues.** CRM required means the expense case owner must act; AP issues mean the AP team must correct the bill/payment link.
5. **Incorrect amortization math.** Always use `original_amount - cumulative_amortization` for ending balance, not `monthly * remaining_months` (which can drift due to rounding).
6. **Including void/paid bills in open AP balance.** Only include scheduled/approved (unpaid) bills.
7. **Sorting errors.** ID lists must be ascending; invoice arrays preserve input order.
8. **Missing close-log cross-reference.** Always check `/close/logs` for unresolved entries that may affect batch release.
9. **Rounding errors.** Sum raw values, then round the total to 2 decimals. Don't round intermediate values.
10. **Enum value typos.** Copy enum values exactly from the answer template — they are case-sensitive and must match precisely.
11. **Overlooking the `overall_release_ready` / `batch_status` derivation.** These are derived fields that must be consistent with the per-item decisions.
12. **Not handling edge cases**: zero ending balances, fully amortized invoices with 0.00 or 0.01 remaining, claims with no matching bills, bills with no payments.

### Output Validation Checklist
Before finalizing, verify:
- [ ] All ID lists are sorted ascending.
- [ ] All currency fields have exactly 2 decimal places.
- [ ] All required top-level keys are present per the answer template.
- [ ] Enum values match the template exactly (case, underscores).
- [ ] Derived fields (`batch_status`, `overall_release_ready`, `account_status`) are consistent with per-item decisions.
- [ ] Count fields (`reviewed_claim_count`, `selected_invoice_count`, `reportable_ubo_counts`) are integers.
- [ ] Invoice result arrays preserve the input scope order.
- [ ] No extra keys beyond what the template specifies.
