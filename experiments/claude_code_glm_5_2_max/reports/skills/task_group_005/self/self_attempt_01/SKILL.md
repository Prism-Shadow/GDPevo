# SKILL.md — task_group_005 ERP Finance Expense-Control (SELF mode)

Executable, transferable rules for the task_group_005 ERP finance/compliance API.
Derived by working the 5 train tasks from the remote API directly (no gold answers).
This file contains RULES and FIELD MAPPINGS, not per-task answer cheat-sheets.

---

## 1. API contract

- Base URL is given in `environment_access.md` (a single host:port). The local `http://127.0.0.1:8005`
  mentioned in some prompts is an alias of the same system; ALWAYS treat the runner-provided
  base URL / `environment_access.md` value as system of record. Do NOT read any local `env/` source.
- Discovery: `GET /endpoints` returns the authoritative path list. Two alias trees exist —
  `/api/<resource>` and `/<resource>` — both return identical data. Prefer the `/api/...` forms.
- Filtering: **exact-match query parameters by field name** (e.g. `?claim_id=...`, `?bill_id=...`,
  `?business_id=...`, `?vendor_id=...`, `?prepaid_invoice_id=...`, `?account=...`, `?period=...`,
  `?status=...`, `?area=...`). Pagination via `limit` (default 100) and `offset`.
- Every response envelope: `{ "count", "data": [...], "endpoint", "limit", "offset", "total" }`.
  Always check `total` — a query may match 0 rows (real signal), so do not assume a missing
  record means an endpoint is broken.

### Endpoints used
| Path (canonical) | Key filter fields | Purpose |
|---|---|---|
| `/api/claims` | `claim_id` | Expense reimbursement claims |
| `/api/ap/bills` | `bill_id`, `claim_id` | AP bills (one claim may map to ≥1 bill) |
| `/api/ap/payments` | `payment_id`, `bill_id` | Payments keyed by `bill_id` (NO `claim_id` on payments) |
| `/api/ap/aging` | — | AP aging (not needed for these tasks) |
| `/api/vendors` | `vendor_id` | Vendor master: `status`, `tax_id`, `bank_account_last4`, `payment_terms`, `default_account` |
| `/api/compliance/objects` | `business_id` | KYC/risk object: bank status, license, PEP, sanctions, shell, UBOs, risk_score, `review_status` |
| `/api/prepaids/invoices` | `prepaid_invoice_id`, `account` | Prepaid amortization schedules |
| `/api/prepaids/gl-balances` (alias `/api/gl/balances`) | `account`, `period` | GL ending balances; one row per (account, period) |
| `/api/close/logs` | `log_id`, `period`, `area`, `status`, `related_account` | Month-end close log items |

### Critical data-model facts (cross-cutting)
- **Payments do not carry `claim_id`.** Join claim→bill via `claim_id`, then bill→payment via `bill_id`.
- A single `claim_id` can map to **multiple bills** (e.g. one stale/mismatched bill + one true paid bill).
- The **compliance object** and the **vendor master** are separate records that can DISAGREE:
  `compliance/objects.tax_id` is the screened value and may be a placeholder (e.g. `TIN999999`) or
  malformed, while `vendors.tax_id` is the master value. Cross-check both.
- `vendors.status` can be `on_hold` independently of compliance `review_status`.
- `compliance/objects.bank_account_status` is the screened bank state; `vendors.bank_account_last4`
  is the master bank last4 used to confirm the account-change ticket's `requested_bank_last4`.
- GL balances are per (account, period). The schedule you build from selected invoices is a SUBSET
  of the account; comparing selected-schedule total to the full GL ending balance will normally
  show a variance unless the scope = all invoices on the account.

---

## 2. Reimbursement-to-AP close (claim/bill/payment reconciliation)

Applies to the close-review tasks. Core principle: an expense claim is "paid" only when there is a
**matching PAID AP bill AND a cleared payment for the claim amount**. Otherwise classify it.

### Claim record fields (decision-relevant)
`claim_id`, `amount`, `status` (`approved`/`paid`/`rejected`/`needs_receipt`/...), `receipt_status`
(`attached`/`partial`), `policy_flags`, `vendor_id` (may be null), `approved_date` (null ⇒ not yet
approved), `notes`.

### Decision algorithm (per candidate claim)
1. Fetch claim by `claim_id`. Fetch ALL bills by `claim_id`. For each bill, fetch payments by `bill_id`.
2. **Already paid?** If there exists a bill whose `status` == `paid` (or `approved`→ with a payment)
   AND a payment with `status` == `cleared` whose `amount` == claim `amount` ⇒ **paid**. The claim's
   own `status` == `paid` corroborates but is not sufficient alone; require the bill+payment evidence.
   Ignore any other non-matching bills on the claim as stale/duplicate.
3. **Blocked** if not paid AND any of:
   - claim `status` is not `approved` (e.g. `needs_receipt`, `rejected`) or `approved_date` is null,
   - the only/linked bill is `void`,
   - the linked bill `amount` ≠ claim `amount` (claim-vs-AP alignment failure),
   - a bill `vendor_id` ≠ claim `vendor_id` (vendor mismatch),
   - no AP bill exists at all for the claim.
   Blocked claims need expense-case owner cleanup or AP-link remediation ⇒ also go in the
   "crm_required"/"not_ready" list.
4. **Payable** if not paid and not blocked: claim is approved, and there is a valid **open**
   (status `scheduled` or `approved`, not `void`/`paid`) AP bill whose amount matches the claim.
   These remain in the AP reimbursement queue.

### Open-balance / totals
- "ap_open_balance_total" = sum of **valid open AP bill amounts for PAYABLE claims only**.
  Exclude paid claims' bills, void bills, amount/vendor-mismatched bills. Count each payable claim's
  matching open bill once.
- Per-claim open balance = open bill amount minus any **cleared** payment on that bill. Ignore
  in-flight (`scheduled`/`processing`) payments — they are not yet cleared evidence. Ignore void bills.

### Batch status precedence
`blocked` (any item blocked) > `open_payables` (valid unpaid AP bills remain, none blocked) >
`ready_to_close` (everything paid, nothing open).

### Stale-snapshot handling (when a local CSV/snapshot is provided as "context, not system of record")
Map each candidate to one correction enum by comparing snapshot row vs current ERP:
- `current_snapshot_ok` — snapshot row matches current claim/bill/payment state.
- `replace_with_matched_paid_bill` — snapshot shows an old/scheduled bill but current ERP shows the
  claim settled via a different **paid** bill + cleared payment (the snapshot bill is stale).
- `mark_in_flight_payment` — snapshot shows payment `none`/`scheduled` but a payment now exists that
  is `processing`/`scheduled` (not yet cleared) — i.e. payment in flight.
- `ignore_void_bill` — snapshot showed a bill as `approved`/`scheduled` but current ERP marks it `void`.
- `exclude_amount_or_vendor_mismatch` — the bill's amount or vendor does not match the claim.
- `block_unapproved_claim` — snapshot showed the claim `approved` but current claim status is
  `needs_receipt`/`rejected`/not-approved (snapshot is stale on claim state).

### Close-log integration
`/api/close/logs` items have `status`: `closed` | `open` | `ready_for_review` | `blocked`.
A batch requires close-log attention when any **open / ready_for_review / blocked** log item relates
to the batch (match on `related_account` against the bills' `account`, or `area` `Expense`/`AP`).
Return `close_log_required.required = true` and the matching `log_id`s (ascending). `closed` logs are
historical and do not require action.

### Close-batch status (stale-snapshot variant)
`blocked` (any claim is unapproved or only-void-bill — not fixable by AP refresh) >
`needs_ap_refresh` (claims valid but AP/payment data is stale — refreshable) >
`ready_to_send` (all eligible with current data).

---

## 3. Vendor onboarding / KYC release (compliance-derived decisions)

Per business, derive decision from the **compliance object** + **vendor master**, NOT by copying
`review_status`. Decision enum: `approve` / `awaiting_information` / `escalate`.

### hard_stop_flags mapping (compliance → flag) — collect ALL that apply, sort alphabetically
| Compliance / vendor signal | hard_stop_flag |
|---|---|
| `bank_account_status` == `closed` | `bank_closed` |
| `bank_account_status` == `name_mismatch` | `bank_name_mismatch` |
| `pep_status` == `confirmed_pep` | `confirmed_pep` |
| `license_expiry` < as_of_date | `expired_license` |
| `missing_fields` non-empty | `missing_required_documents` |
| `sanctions_check_status` == `confirmed` / hit | `sanctions_confirmed` |
| `sanctions_check_status` == `not_run` | `screening_not_run` |
| `shell_company_suspected` == true | `shell_company_suspected` |
| `vendors.status` == `on_hold` | `vendor_on_hold` |

Note: `pep_status` `possible_pep` and `not_run` are NOT `confirmed_pep` (no confirmed_pep flag).
`screening_not_run` keys off **sanctions** `not_run`, not `pep_status` `not_run`.

### reportable_ubo_counts
Count **unique UBO names** that have AT LEAST ONE `ubo_list` entry with `ownership_pct` ≥ the
reporting threshold (standard AML beneficial-owner threshold = **25%**). Deduplicate by name; if a
name has multiple entries, it counts once if any entry ≥ 25%. (24% entries are deliberately below
threshold — do not count them; 25% is "at or above".) A business may legitimately have 0 reportable UBOs.

### Decision logic
- `escalate` if **any** hard_stop_flag applies, OR compliance `review_status` == `escalated`.
- else `approve` if no hard stops AND `review_status` == `approved` AND no `missing_fields` AND
  sanctions `clear` AND license valid AND bank `verified` AND pep not confirmed.
- else `awaiting_information` (covers `review_status` `in_review`/`awaiting_information`/`not_started`,
  or minor gaps without a hard stop).
- `follow_up_business_ids` = all businesses whose decision ≠ `approve` (ascending).
- `overall_release_ready` = true ONLY if **every** business decision is `approve`.

---

## 4. Payment release after account-change events

Per business in the account-change batch, integrate: the account-change ticket
(`change_type`, `priority`, `requested_bank_last4`) + compliance object + vendor master.

Decision enum: `release` / `hold` / `escalate`.

### Derived ID lists (ascending by business_id)
- `bank_mismatch_ids` — compliance `bank_account_status` == `name_mismatch`.
- `invalid_tax_ids` — compliance `tax_id` is not a well-formed TIN (expected pattern `TIN` + 6 digits).
  Both **malformed** values (contains a non-digit, e.g. `TIN12X899`) and **placeholder/sentinel**
  values (e.g. all-9s `TIN999999`) are invalid. Cross-check against `vendors.tax_id`: a compliance
  tax_id that equals an all-9s sentinel while the vendor master has a real TIN is a placeholder ⇒ invalid.
- `expired_license_ids` — `license_expiry` strictly before `as_of_date` (comparison_date = as_of_date).
  A license expiring the day AFTER the review date is NOT expired (deliberate boundary).
- `risk_score_override_flags` — `risk_score` ≥ 70.
- `review_queue_ids` — all businesses whose decision ≠ `release` (need compliance/AP review first).

### Decision logic
- `escalate` if any of: bank `closed`, sanctions `not_run`/confirmed, confirmed PEP, shell suspected,
  invalid tax_id, vendor `on_hold`, OR compliance `review_status` == `escalated`/`not_started`.
- `hold` if compliance `review_status` == `in_review`/`awaiting_information`, OR bank `name_mismatch`,
  OR license expired (but otherwise recoverable), OR `risk_score` ≥ 70, OR missing required fields —
  needs review but not full escalation.
- `release` only if bank `verified`, license valid vs as_of_date, sanctions `clear`, pep not confirmed,
  tax_id valid, no missing fields, vendor `active` (not on_hold), risk_score < 70, AND the
  `requested_bank_last4` matches `vendors.bank_account_last4`.
- change_type context elevates scrutiny (e.g. `new_account_after_remittance_failure`,
  `reactivation_after_closed_bank_notice`) but the gate is the compliance/vendor evidence above.

### Bank last4 confirmation
Compare the ticket's `requested_bank_last4` to `vendors.bank_account_last4`. A mismatch is an
additional hold/escalate trigger; a match does NOT override a bad compliance `bank_account_status`.

---

## 5. Prepaid amortization & GL reconciliation

For prepaid close: build a per-invoice straight-line schedule for the scoped invoice IDs, roll up to
the scoped accounts, and compare to that account's GL ending balance for the close period.

### Invoice fields
`prepaid_invoice_id`, `account`, `original_amount`, `monthly_amortization`, `service_start`,
`service_end`, `recognition_method` (`straight_line`), `data_quality_flags`
(`rounded_amount`, `missing_contract_dates`, ...), `invoice_date`, `vendor_id`.

### Per-invoice computation (close period = YYYY-MM, e.g. 2025-03)
- **Active in period?** Invoice is active for month M if `service_start` ≤ last day of M AND
  `service_end` ≥ first day of M.
- `march_amortization` (period amortization) = `monthly_amortization` if active in the period, else 0.
- `cumulative_amortization_through_march` = `monthly_amortization` × (number of active months from
  `service_start` through the close period inclusive). Count a month as active if the service window
  overlaps it; for an invoice starting mid-month, the start month still counts as one full month
  (the schedule uses whole-month straight-line, not prorated days).
- `ending_balance` = `original_amount` − `cumulative_amortization_through_march` (never negative;
  once fully amortized the balance is 0; small rounding residuals like 0.01 may remain when
  `monthly_amortization × term` ≠ `original_amount`).
- `default_missing_term_flag` = true iff `data_quality_flags` contains `missing_contract_dates`
  (a default term was applied — flag for term validation).
- `exception_flag` = true iff the invoice carries any `data_quality_flag` (rounded_amount,
  missing_contract_dates, …) OR its straight-line schedule does not fully amortize to the original
  amount (nonzero residual at end of term). default_missing_term is a subset of exception.

### Account rollup (per scoped account: 1250, 1251)
- `selected_invoice_count`, `original_amount_total`, `march_amortization_total`,
  `cumulative_amortization_through_march`, `schedule_ending_balance` — sums over the account's
  selected invoices. (`schedule_ending_balance` ≡ `original_amount_total` − `cumulative...`.)
- `gl_ending_balance` = `/api/prepaids/gl-balances?account=<acct>&period=<YYYY-MM>` `ending_balance`.
  `account_name` comes from that GL row.
- `variance_amount` = `schedule_ending_balance` − `gl_ending_balance` (**schedule minus GL**, signed).
- `variance_flag` = `abs(variance_amount)` > `variance_threshold_abs` (from scope JSON; e.g. 100.0).
- `has_default_missing_term_flag` = OR of the account's invoice default flags.

### `account_status` enum: `reconciled` / `variance_review` / `requires_reconciliation`
- `requires_reconciliation` if `has_default_missing_term_flag` (data gap blocks clean reconciliation).
- else `variance_review` if `variance_flag` (schedule vs GL outside tolerance).
- else `reconciled` (no variance, no default-term issues).
Priority: default/missing-term > variance > reconciled.

### Output ordering
- `selected_invoice_ids` and `invoice_results`: **same order as `prepaid_close_scope.json`** (NOT sorted).
- `default_missing_term_invoice_ids`, `exception_invoice_ids`: ascending by invoice id.

---

## 6. Currency, ordering & format conventions

- Currency precision = 2 decimals (USD). **Prefer the per-field `unit`/`precision` metadata in the
  answer_template over a generic "USD cents" phrase in the prompt** — when a template field says
  `unit: USD, precision: 2`, emit decimal dollars (e.g. `1842.36`), not integer cents. If a prompt
  says "USD cents" AND the template has no precision field, reconcile carefully; the template field
  definition is the contract.
- Round only at the final reported value; keep full precision in intermediate sums. Two-decimal
  residuals (0.01) from rounded monthly amortization are real and must be reported as-is.
- Claim/business/invoice ID lists: sort **ascending by ID string** (lexicographic). Note `PPD-2025-*`
  sorts before `PPD-AUR-*` because digit `2` < letter `A`. Close-log IDs ascending by log_id.
- `target_business_ids` / `per_business` lists: ascending by business_id.
- hard_stop_flags lists: alphabetical by enum value; empty list `[]` when none apply.
- Booleans: `variance_flag`, `has_default_missing_term_flag`, `default_missing_term_flag`,
  `exception_flag`, `close_log_required.required`, `overall_release_ready` — strict booleans.
- Required fixed values: copy required_value fields exactly (e.g. `task_id`, `batch_id`,
  `as_of_date` in the payment-release template).

---

## 7. Common misjudgments / exclusion rules (watch-list)

1. **Paid vs payable**: a claim whose own `status`==`paid` still needs a paid bill + cleared payment
   to be classified "paid"; conversely a `scheduled` payment is NOT cleared evidence — it is in-flight.
2. **Multiple bills per claim**: do not let a stale/mismatched secondary bill flip a paid claim to
   payable/blocked. Identify the bill whose amount == claim amount and whose payment cleared.
3. **Void bill = no valid AP**: a claim with only a `void` bill is blocked (needs AP-link), not payable.
4. **Amount/vendor mismatch = blocked, not payable**: bill amount ≠ claim amount, or bill vendor ≠
   claim vendor ⇒ exclude that bill and block/flag the claim for remediation.
5. **Stale snapshot ≠ system of record**: always re-query the API; the snapshot's `snapshot_*` statuses
   are pre-cleanup. Pick the correction enum by what changed between snapshot and current ERP.
6. **PEP possible ≠ confirmed**: only `confirmed_pep` raises the `confirmed_pep` flag.
7. **screening_not_run keys off sanctions**, not pep_status. `pep_status: not_run` has no dedicated flag.
8. **UBO threshold is 25%** ("at or above"); 24% entries are below the line. Deduplicate by name;
   a name with one ≥25% entry counts once.
9. **License expiry boundary**: strictly less than as_of_date. Day-after-as_of is still valid.
10. **invalid tax_id**: malformed (non-digit) OR all-9s placeholder sentinel. Check the COMPLIANCE
    tax_id (screened value), and reconcile with the vendor master tax_id.
11. **risk_score ≥ 70** (inclusive) triggers risk_score_override; in onboarding it is a hold signal.
12. **vendor_on_hold** comes from `vendors.status`, independent of compliance `review_status`.
13. **Prepaid variance direction**: `variance = schedule_ending_balance − gl_ending_balance` (signed).
    Reporting GL−schedule flips the sign — keep schedule-minus-GL.
14. **Prepaid selected-set ≠ full account**: a large schedule-vs-GL variance is expected when the
    scope is a subset; still report `variance_review`/`requires_reconciliation` per the rules.
15. **Close-log "closed" items need no action**; only `open`/`ready_for_review`/`blocked` items relevant
    to the batch drive `close_log_required.required = true`.
16. **Ordering discipline**: scope-order (not sorted) for prepaid invoice lists; ascending for all ID
    lists and business lists; alphabetical for hard_stop_flags.

---

## 8. SOP — query order per task type

### Reimbursement-to-AP close (T1) / stale snapshot batch (T4)
1. `GET /endpoints` to confirm paths.
2. For each candidate claim: `GET /api/claims?claim_id=X` → record amount, status, approved_date, vendor.
3. `GET /api/ap/bills?claim_id=X` (may return 0, 1, or many). For each bill: `GET /api/ap/payments?bill_id=Y`.
4. Classify paid / payable / blocked per §2; compute per-claim open balance and batch total.
5. (T4) Map each candidate to a stale-snapshot correction enum by diffing the local CSV row vs current ERP.
6. `GET /api/close/logs?area=Expense&limit=...` (and/or `?area=AP`) — collect open/ready/blocked items
   whose `related_account` matches the bills' accounts; set `close_log_required`.
7. Set batch_status per §2 precedence. Emit lists ascending; amounts USD 2-dp.

### Vendor onboarding / KYC (T2)
1. Read the onboarding batch JSON for the business_id list and `as_of_date`.
2. For each business: `GET /api/compliance/objects?business_id=B` and `GET /api/vendors?vendor_id=V`
   (vendor_id is on the compliance object).
3. Build hard_stop_flags per §3 mapping (alphabetical). Count reportable UBOs (≥25%, unique names).
4. Decide approve/awaiting_information/escalate per §3. follow_up = non-approve; overall_ready = all approve.

### Prepaid close (T3)
1. Read `prepaid_close_scope.json` (entity, close_period, accounts, invoice ids, variance_threshold_abs).
2. For each invoice id: `GET /api/prepaids/invoices?prepaid_invoice_id=P`.
3. For each scoped account: `GET /api/prepaids/gl-balances?account=A&period=2025-03`.
4. Per invoice: compute march_amortization, cumulative through March, ending_balance, default/exception
   flags per §5. Roll up per account; compute variance = schedule − GL; set account_status.
5. Emit invoice_results in scope order; default/exception id lists ascending.

### Payment release after account-change (T5)
1. Read `account_change_batch.json` (target_business_ids, review_date, account_change_events).
2. For each business: `GET /api/compliance/objects?business_id=B` and `GET /api/vendors?vendor_id=V`.
3. Derive bank_mismatch_ids, invalid_tax_ids, expired_license_ids (vs as_of_date), risk_score_override_flags
   (≥70) per §4. Confirm ticket `requested_bank_last4` vs `vendors.bank_account_last4`.
4. Decide release/hold/escalate per §4. review_queue_ids = non-release. Emit fixed required_value fields.
