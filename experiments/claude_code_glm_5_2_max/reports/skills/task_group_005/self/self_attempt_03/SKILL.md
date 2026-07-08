# SKILL — task_group_005 ERP Finance Expense-Control Close

Transferable, executable experience for solving ERP finance expense-control tasks in the
`task_group_005` shared API environment. Covers four task archetypes that recur across
train/test pairs:

- **A. Reimbursement-to-AP close review** (claim → AP bill → payment reconciliation; payable/blocked/paid partition; stale AP-snapshot correction).
- **B. Vendor onboarding / KYC release board** (compliance hard-stop flags, UBO reporting, release decisions).
- **C. Prepaid amortization & GL reconciliation close** (straight-line monthly schedule vs. GL ending balance, variance + data-quality flags).
- **D. Payment-release risk review after vendor account-change events** (compliance + vendor + bank/tax/license/risk gating, release/hold/escalate).

The rules below are derived from working the 5 train tasks against the live API. They are
**rules and decision criteria**, not a lookup of any answer set.

---

## 1. API contract

### Base URL & discovery
- Remote API base: `<remote-env-url>` (a prompt may print `http://127.0.0.1:8005`; the
  remote URL above is the shared system of record — use it).
- `GET /endpoints` → lists all paths and the filtering contract.
- `GET /health` and `GET /api/health` → `{status, task_group}`.
- **Currency convention:** report all amounts to **2 decimals in USD** unless a task says
  otherwise (see §9 for the "USD cents" trap).

### Endpoints (canonical + alias)
Every resource has a namespaced `/api/...` path and, for most, a bare alias. Both return
identical data. Use the `/api/...` form.

| Resource | Canonical path | Alias |
|---|---|---|
| Claims | `/api/claims` | `/claims` |
| AP bills | `/api/ap/bills` | `/bills` |
| AP payments | `/api/ap/payments` | `/payments` |
| AP aging | `/api/ap/aging` | — |
| Vendors | `/api/vendors` | `/vendors` |
| Compliance (KYC) objects | `/api/compliance/objects` | `/compliance/objects` |
| Prepaid invoices | `/api/prepaids/invoices` | `/prepaids/invoices` |
| GL balances (general) | `/api/prepaids/gl-balances` | `/gl/balances` |
| Close logs | `/api/close/logs` | `/close/logs` |

### Filtering contract
- **Exact-match query parameters by field name.** Examples: `?claim_id=CLM-2025-0038`,
  `?business_id=BUS-2025-0009`, `?vendor_id=VEN-0064`, `?account=1250`, `?period=2025-03`,
  `?status=blocked`.
- Paginate with `limit` (default 100) and `offset`. **Always pass `limit`** when you need the
  full set; default page may be smaller than `total`.
- A list by a unique field returns `{count, data:[...], total, limit, offset}`. Filter by a
  join key that can repeat (e.g. `?claim_id=`) returns **all** matching rows — use this to
  pull every bill/payment for one claim.
- Path-style single fetch (`/api/claims/<id>`) works for claims but **not** for bills
  (`/api/ap/bills/<id>` returns `not_found`). Prefer the query-param form.

---

## 2. Data model — fields that matter

### Claims `/api/claims`
`claim_id, status, amount, currency, submitted_date, approved_date, category, department,
employee_name, receipt_status, policy_flags[], notes, vendor_id`.
- `status` values seen: `needs_receipt`, `approved`, `paid` (also `rejected`/`draft` possible).
- `policy_flags` values seen: `manual_rate`, `duplicate_amount`, `over_limit`, `late_receipt`.
  **Policy flags do not by themselves block AP release** once the claim is `approved`.
- `receipt_status`: `attached` vs `partial`.
- `vendor_id` may be `null` (employee reimbursement) — do not treat null vendor as a mismatch
  against a bill vendor; use amount alignment instead.

### AP bills `/api/ap/bills`
`bill_id, claim_id, vendor_id, account, amount, currency, bill_date, due_date, invoice_number,
memo, status`.
- `status` values: `draft`, `approved`, `scheduled`, `paid`, `void`.
- `account` is the GL account hit (e.g. `6200` expense, `2100` AP clearing, `1250/1251` prepaid,
  `6500` T&E). A bill linked to a reimbursement claim but on a **prepaid account** with a
  **non-matching amount/vendor** is not that claim's reimbursement bill.
- A single `claim_id` can map to **multiple** bills (e.g. a prepaid bill + the real paid
  reimbursement bill). Always fetch all bills for the claim and pick the one matching claim
  amount (+ vendor).

### AP payments `/api/ap/payments`
`payment_id, bill_id, vendor_id, amount, status, method, payment_date, bank_reference`.
- `status` values: `none`(implicit), `processing`, `scheduled`, `cleared`, `failed`.
- **Paid = bill `status=paid` AND a payment with `status=cleared` for the bill/claim amount.**
- `processing` / `scheduled` payments are **in-flight, not cleared** → the bill is still an
  open payable.

### AP aging `/api/ap/aging`
`bill_id, claim_id, vendor_id, amount, paid_amount, balance, bill_date, due_date, status, as_of`.
- Used for payment-priority ranking. **Note:** aging rows can overlap/duplicate canonical
  bills with the same `bill_id` but different status — do not age-rank from here unless the
  task explicitly asks for aging; rank from `/api/ap/bills` + `/api/ap/payments` instead.

### Vendors `/api/vendors`
`vendor_id, vendor_name, legal_name, status, tax_id, bank_account_last4, default_account,
industry, payment_terms, updated_at`.
- `status`: `active`, `on_hold`, (others possible). `on_hold` is a release hard-stop.
- `tax_id` here is the **vendor-master** tax id — compare against `compliance.tax_id` to find
  corrupted/placeholder tax ids.
- `bank_account_last4` — compare against the account-change ticket's `requested_bank_last4`.

### Compliance objects `/api/compliance/objects`
`business_id, business_name, vendor_id, jurisdiction, registration_number, tax_id,
bank_account_status, license_expiry, missing_fields[], ownership_layer_count, ubo_list[],
pep_status, sanctions_check_status, shell_company_suspected, review_status, risk_score`.
- `bank_account_status`: `verified`, `name_mismatch`, `closed`.
- `pep_status`: `none`, `possible_pep`, `confirmed_pep`, `not_run`.
- `sanctions_check_status`: `clear`, `not_run`, (`confirmed`).
- `review_status`: `not_started`, `in_review`, `awaiting_information`, `approved`, `escalated`.
- `risk_score`: integer 0–100.
- `ubo_list[]`: `{name, ownership_pct}`.
- `missing_fields[]`: document names e.g. `license`, `beneficial_owner_id`.

### Prepaid invoices `/api/prepaids/invoices`
`prepaid_invoice_id, account, vendor_id, invoice_number, invoice_date, service_start,
service_end, original_amount, monthly_amortization, recognition_method, description,
source_document, data_quality_flags[]`.
- `recognition_method`: `straight_line`.
- `data_quality_flags` values seen: `rounded_amount`, `missing_contract_dates`.

### GL balances `/api/prepaids/gl-balances` (= `/gl/balances`)
`account, account_name, entity, period (YYYY-MM), ending_balance, source, loaded_at`.
- Multiple periods per account; filter by `account` and `period`. Entity = legal entity string.

### Close logs `/api/close/logs`
`log_id, area, period, related_account, message, owner, status, created_at`.
- `area`: `AP`, `Expense`, `Prepaids`, `Treasury`, `GL`, `Compliance`.
- `status`: `closed`, `ready_for_review`, `open`, `blocked`.
- `message` patterns: `Waiting on AP export refresh`, `Variance review pending`,
  `Reviewer cleared variance`, `Manual journal entry posted`, `Support uploaded`,
  `Legacy import created duplicate line`.

---

## 3. Task A — Reimbursement-to-AP close review

**Goal:** partition a list of candidate claim IDs into payable / blocked / paid, compute the
open AP balance, and set an overall batch status. Variant with a stale CSV snapshot also
classifies a per-claim snapshot correction.

### SOP — query order
1. `GET /api/claims?claim_id=<each>` → claim status, amount, vendor_id, policy_flags.
2. `GET /api/ap/bills?claim_id=<each>` → every bill linked to the claim.
3. For each bill, `GET /api/ap/payments?bill_id=<each bill_id>` → payment evidence.
4. Reconcile per claim (rules below). Sum open AP for payable claims only.

### Claim classification rules
- **paid:** claim has an AP bill whose `status=paid` AND whose `amount` equals the claim
  amount AND a payment with `status=cleared` for that amount. (Claim `status=paid` is a hint;
  the paid bill + cleared payment is the proof.)
- **payable (eligible):** claim `status=approved` AND there is an **open** AP bill
  (`status` in `approved`/`scheduled` — i.e. not paid, not void, not draft-blocking) whose
  `amount` equals the claim amount and (when claim has a vendor) vendor matches. In-flight
  payments (`processing`/`scheduled`) **do not** make it paid — the bill is still an open
  payable.
- **blocked:** not paid AND not payable, because the AP link is wrong/missing. Reasons:
  - no bill at all for the claim;
  - the only linked bill is `void`;
  - the linked bill's `amount` ≠ claim amount, or (when both have a vendor) vendor mismatch
    (these are AP-link problems); or
  - the claim itself is unapproved (`needs_receipt`/`rejected`) — blocked until the expense
    case is fixed.
- Policy flags (`over_limit`, `late_receipt`, `manual_rate`, `duplicate_amount`) and
  `partial` receipts do **not** auto-block an *approved* claim; they are case-side metadata.
  They only matter when the claim is not approved, or to explain a separate case-cleanup need.

### crm_required vs blocked
`crm_required_claim_ids` = blocked claims that need **expense-case owner cleanup OR AP-link
remediation**. In practice this equals the blocked set (every blocked claim needs one or the
other). Do not put payable or paid claims here.

### ap_open_balance_total
Sum of open AP balances for **payable claims only**. Open AP balance per claim =
`bill.amount` − (sum of `cleared` payments on that bill). In-flight payments are not
subtracted. Void/mismatched bills contribute 0 (excluded).

### batch_status (A, simple template)
`blocked` if any claim is blocked; else `open_payables` if any payable (valid unpaid AP
remains); else `ready_to_close`.

### Stale-snapshot variant (separate template) — `stale_snapshot_corrections`
Compare the circulated CSV snapshot to the current API. Per candidate claim pick **one** enum:
- `current_snapshot_ok` — snapshot matches current ERP (bill id/amount/status, payment) and
  claim is an open payable → keep as-is.
- `mark_in_flight_payment` — snapshot shows payment `none/0.00` but current ERP has a
  `processing`/`scheduled` (uncleared) payment on the bill.
- `replace_with_matched_paid_bill` — snapshot points to a wrong/scheduled bill (often a
  non-matching prepaid bill) but the real matched bill is `paid` + cleared for the claim
  amount; replace the snapshot row with that matched paid bill (claim is settled, not in the
  open batch).
- `exclude_amount_or_vendor_mismatch` — the snapshot/current bill `amount` ≠ claim amount or
  vendor mismatches; exclude that AP row from the claim's balance.
- `ignore_void_bill` — snapshot shows the bill as `approved` but current ERP `status=void`;
  ignore it (contributes 0 to AP balance).
- `block_unapproved_claim` — the claim is not approved (`needs_receipt`/`rejected`); block it
  regardless of bill state.

### ap_balance_by_claim (stale variant)
Keys = **all candidate claim IDs**. Value = open AP balance after applying `cleared` payments
and **ignoring stale/voided/mismatched** rows. Paid claims and blocked/mismatched/void claims
= `0.00`.

### not_ready_claim_ids (stale variant)
Claims that should not remain in the batch: paid (settled), unapproved, void-bill-only, or
amount/vendor-mismatched. (A paid claim is "not ready" for the *open* batch because it is
already settled.)

### close_log_required (stale variant)
- `required: true` when non-closed close logs whose `message` is `Waiting on AP export refresh`
  exist for accounts touched by the batch's bills.
- `ids` = those non-closed (`ready_for_review`/`open`/`blocked`) `Waiting on AP export refresh`
  log IDs, ascending. Filter to `related_account` ∈ the set of bill accounts in the candidate
  batch. (Closed `Waiting on AP export refresh` logs do **not** count.)
- `required: false`, `ids: []` only when no such pending AP-refresh log touches the batch.

### batch_status (stale variant)
`ready_to_send` | `needs_ap_refresh` | `blocked`.
- `needs_ap_refresh` when the batch was built from a stale AP export and non-closed
  AP-refresh logs are pending (typical). `blocked` only when a candidate is hard-blocked
  (e.g. unapproved claim) and nothing is eligible; otherwise prefer `needs_ap_refresh` if at
  least one claim is eligible.

---

## 4. Task B — Vendor onboarding / KYC release board

**Goal:** for a list of `business_id`s, produce per-business `decision`
(`approve`/`awaiting_information`/`escalate`), `reportable_ubo_counts`,
`hard_stop_flags`, `follow_up_business_ids`, `overall_release_ready`.

### SOP
1. `GET /api/compliance/objects?business_id=<each>` → KYC evidence.
2. `GET /api/vendors?vendor_id=<compliance.vendor_id>` → master status, tax_id, bank last4.
3. Derive hard-stop flags; then decision; then summary fields.

### hard_stop_flags (alphabetical within each business; `[]` if none)
Map each condition to its enum value:
- `bank_closed` ← `bank_account_status == "closed"`
- `bank_name_mismatch` ← `bank_account_status == "name_mismatch"`
- `confirmed_pep` ← `pep_status == "confirmed_pep"`  *(possible_pep is NOT this flag)*
- `expired_license` ← `license_expiry < as_of_date`
- `missing_required_documents` ← `missing_fields` non-empty
- `sanctions_confirmed` ← `sanctions_check_status == "confirmed"` (sanctioned)
- `screening_not_run` ← `sanctions_check_status == "not_run"` **OR** `pep_status == "not_run"`
- `shell_company_suspected` ← `shell_company_suspected == true`
- `vendor_on_hold` ← vendor `status == "on_hold"`
If none apply → `[]`.

### Decision (approve / awaiting_information / escalate)
- **escalate** if any `hard_stop_flag` is set.
- **approve** if **all** evidence is clean: no hard stops, `bank verified`, `pep` `none`,
  `sanctions` `clear`, `shell` false, license valid, `missing_fields` empty, vendor `active`,
  tax id matches master, risk below threshold. **`review_status=in_review` alone does not
  block approval** — decisions are evidence-based ("suitable for release control, not just a
  copy of the current review status"), so clean evidence with an in-progress review still
  approves.
- **awaiting_information** otherwise (moderate issues without a hard stop):
  `bank_name_mismatch` (already a hard stop, so escalates), `possible_pep`, pending screening,
  missing docs, or `review_status` in `not_started`/`awaiting_information`.

(If a business has `bank_name_mismatch` it is in `hard_stop_flags` and therefore escalates;
`bank_name_mismatch` is treated as a hard stop in onboarding.)

### reportable_ubo_counts
- **Reporting threshold = 25% ownership.** Count **unique UBO `name`s** with
  `ownership_pct >= 25`. Duplicate name entries count once. (Design cue: 24% entries sit just
  below the threshold and must be excluded.)
- Whole-number integer, 0 if none qualify.

### follow_up_business_ids / overall_release_ready
- `follow_up_business_ids` = all businesses whose decision ≠ `approve`, ascending by
  `business_id`.
- `overall_release_ready` = `true` only if **every** business is `approve`.

---

## 5. Task C — Prepaid amortization & GL reconciliation close

**Goal:** for a scoped set of prepaid invoice IDs, accounts, entity, and close period
(`YYYY-MM`), build the straight-line amortization schedule, reconcile to GL ending balances,
flag variances and data-quality exceptions, and set per-account status.

### SOP
1. Read scope: `entity`, `close_period`, `accounts[]`, `selected_prepaid_invoice_ids[]`
   (preserve their order — outputs use "same order as scope"), `variance_threshold_abs`.
2. `GET /api/prepaids/invoices?prepaid_invoice_id=<each>` → schedule inputs.
3. For each account, `GET /api/prepaids/gl-balances?account=<acct>&period=<close_period>` →
   `gl_ending_balance` (the period's `ending_balance`).
4. Compute per-invoice amortization and roll up per account.

### Amortization math (straight-line monthly)
- Use the stored `monthly_amortization` as the per-month charge (do not recompute from
  `original_amount`/months; the stored value is what the schedule represents).
- A month counts as a full month if it falls within `[service_start month … service_end
  month]`; the start month counts in full even when `service_start` is mid-month.
- `march_amortization` (period amortization) = `monthly_amortization` if the close period
  month is within the service window, else `0`.
- `cumulative_amortization_through_<period>` = `monthly_amortization` × (number of service
  months from `service_start` through the end of the close period).
- `ending_balance` = `original_amount − cumulative_amortization_through_period` (≥ 0;
  small rounding residuals such as 0.01 from `monthly×n` ≠ `original` are kept as-is — do not
  true-up the final month unless a task says so).
- All currency to 2 decimals.

### Account rollup (per account)
- `selected_invoice_count` = invoices in scope for that account.
- `original_amount_total`, `march_amortization_total`,
  `cumulative_amortization_through_march`, `schedule_ending_balance` = sums of the per-invoice
  values. (Check: `schedule_ending_balance == original_amount_total −
  cumulative_total`.)
- `gl_ending_balance` = GL `ending_balance` for that `account`+`period`.
- `variance_amount` = `schedule_ending_balance − gl_ending_balance` (**signed**:
  schedule minus GL).
- `variance_flag` = `abs(variance_amount) >= variance_threshold_abs`.
- `has_default_missing_term_flag` = any invoice on the account has a default/missing-term flag.

### Flags & lists
- `default_missing_term_flag` (per invoice) = invoice `data_quality_flags` contains
  `missing_contract_dates`. (`rounded_amount` is **not** a missing-term flag.)
- `default_missing_term_invoice_ids` = invoices with that flag, ascending by invoice id.
- `exception_flag` (per invoice) = invoice `data_quality_flags` is **non-empty** (any data
  quality issue: `rounded_amount`, `missing_contract_dates`, …). "Invoice-level data quality
  exceptions from the source records."
- `exception_invoice_ids` = invoices with any data-quality flag, ascending by invoice id.
- `selected_invoice_ids` and `invoice_results` keep the **scope file's order** (not sorted).

### account_status enum mapping (priority order)
1. `requires_reconciliation` — account `has_default_missing_term_flag` is true (schedule is
   unreliable without source remediation), regardless of variance.
2. `variance_review` — else if `variance_flag` is true (variance exceeds threshold, but no
   missing-term issues).
3. `reconciled` — else (variance within threshold, no missing-term issues).

### Ordering gotcha
Invoices prefixed `PPD-2025-NNNN` sort **before** `PPD-AUR-…` / `PPD-xxx-…` because digit
`2` (0x32) < letter `A` (0x41). When a list says "ascending by invoice id," apply plain string
sort (so `PPD-2025-0001` precedes `PPD-AUR-1251-GOOD-001`).

---

## 6. Task D — Payment-release risk review after account-change events

**Goal:** for a batch of account-change tickets (`business_id`, `vendor_id`,
`requested_bank_last4`, `change_type`, `requested_release_amount_usd`, `priority`), decide
`release` / `hold` / `escalate` per business and surface `bank_mismatch_ids`,
`invalid_tax_ids`, `expired_license_ids`, `review_queue_ids`, `risk_score_override_flags`.
`as_of_date` from the batch (e.g. `2025-06-01`).

### SOP
1. `GET /api/compliance/objects?business_id=<each>` and `GET /api/vendors?vendor_id=<each>`.
2. Per business compute the derived lists, then the decision.

### Derived lists (ascending by business_id)
- `bank_mismatch_ids` ← `compliance.bank_account_status == "name_mismatch"`.
- `invalid_tax_ids` ← `compliance.tax_id != vendors.tax_id` (mismatch) **or** malformed
  placeholder (e.g. `TIN999999`, `TIN12X899` with a letter). Both a mismatch and a placeholder
  qualify; a clean master-matching tax id does not.
- `expired_license_ids` ← `license_expiry < as_of_date` (pure date compare; a license whose
  doc is `missing_fields` but whose `license_expiry` is in the future is **not** expired by
  this list — it is a separate missing-docs concern).
- `risk_score_override_flags` ← `risk_score >= 70` (the threshold is ">= 70"; 70 qualifies).
- `review_queue_ids` ← businesses not `release`d (i.e. `hold` or `escalate`) — those that
  require review before release.

### Decision (release / hold / escalate) — evidence-based, not a copy of review_status
- **escalate** if any hard block: `confirmed_pep`, `sanctions_check_status` `not_run`/`confirmed`,
  `bank_account_status == "closed"`, `shell_company_suspected`, **tax invalid**, **license
  expired**, vendor `on_hold`, or `review_status == "escalated"`.
- **hold** if moderate issues without a hard block: `bank_account_status == "name_mismatch"`,
  `possible_pep`, `missing_fields` non-empty, `risk_score >= 70`, risky `change_type`
  (`new_account_after_remittance_failure`, `reactivation_after_closed_bank_notice`), or
  `review_status` in `not_started`/`awaiting_information`.
- **release** if clean: `bank_account_status == "verified"`, `requested_bank_last4` ==
  `vendors.bank_account_last4`, license valid, `sanctions` clear, `pep` `none`, `shell` false,
  tax matches master, vendor `active`, `risk_score < 70`. **`review_status == "in_review"`
  alone does not block release** when all evidence is clean — decisions are evidence-based.

### Bank account-change sanity check
Always compare `requested_bank_last4` to `vendors.bank_account_last4`. A mismatch means the
requested payout account is not the on-file account → cannot release (hold/escalate). In this
environment the tickets generally match the master last4; a mismatch is a red flag.

---

## 7. Common misjudgments & exclusion rules (apply across all task types)

1. **Stale snapshot vs. current ERP:** a circulated CSV/export is **context only**, never the
   system of record. Always re-pull claims/bills/payments from the API and compare.
2. **Paid vs. payable:** `processing`/`scheduled` payments are **not** cleared → the bill is
   still an open payable. Only `status=cleared` payment (and `paid` bill) means settled.
3. **Claim-vs-AP alignment:** a bill `claim_id` link is not enough — require **amount match**
   (and vendor match when both exist). A prepaid-account bill with a different amount/vendor
   that happens to share `claim_id` is **not** the claim's reimbursement bill.
4. **Void bills:** a `void` bill is ignored for AP balance and cannot make a claim payable or
   paid.
5. **Multiple bills per claim:** fetch all; the matching bill is the one whose amount equals
   the claim amount (and matching vendor). Non-matching bills are excluded.
6. **`possible_pep` is not `confirmed_pep`:** only `confirmed_pep` is a hard stop. `possible_pep`
   is a moderate/hold signal.
7. **`screening_not_run`:** triggers on `sanctions_check_status == "not_run"` **or**
   `pep_status == "not_run"` (any screening channel not run).
8. **License expiry vs. license-document-missing:** `expired_license` is a pure
   `license_expiry < as_of_date` date compare. A license listed in `missing_fields` but with a
   future `license_expiry` is a missing-docs issue, not an expired-license issue. Both can
   apply simultaneously when the date is also in the past.
9. **Tax id:** compare `compliance.tax_id` to `vendors.tax_id`. Placeholders
   (`TIN999999`) and malformed (`TIN12X899`) or simple mismatches all → invalid.
10. **UBO threshold:** 25%. 24% entries are deliberately below — exclude them. Count unique
    names, not entries.
11. **risk_score threshold:** `>= 70` for the override flag (70 inclusive). `64`/`57` etc. do
    **not** qualify.
12. **review_status is not the decision:** `review_status=approved` with hard stops must
    escalate; `review_status=in_review` with clean evidence can release/approve. Drive the
    decision from evidence, not the status string. (This is the explicit "not just a copy of
    the current review status" instruction.)
13. **Policy flags ≠ block:** `over_limit`/`late_receipt`/`manual_rate`/`duplicate_amount` on
    an `approved` claim do not block AP release. They are case metadata.
14. **Variance direction:** `variance_amount = schedule_ending_balance − gl_ending_balance`
    (schedule minus GL). Keep the sign; `variance_flag` uses the absolute value.
15. **Missing-term ≠ rounded-amount:** `missing_contract_dates` drives
    `default_missing_term_flag`/`requires_reconciliation`; `rounded_amount` drives only the
    generic `exception_flag`.
16. **ap/aging duplicates:** aging rows can share `bill_id` with the canonical bills endpoint
    under a different status. Do not age-rank from `/api/ap/aging` unless explicitly asked; use
    `/api/ap/bills` + `/api/ap/payments`.
17. **Ordering strings:** "ascending by claim_id/business_id/invoice id" = plain string sort.
    `CLM-2025-00…` precedes `CLM-2025-FIN-…`; `PPD-2025-…` precedes `PPD-AUR-…`. Numbers
    inside are zero-padded so lexical sort works.
18. **List all keys:** when a template says "keys: candidate claim/business IDs," include
    **every** candidate in the object even if the value is 0/empty — don't omit settled/
    blocked ones.

---

## 8. Output field & controlled-vocabulary reference

### Task A (reimbursement-to-AP, simple)
Top-level: `payable_claim_ids[]`, `blocked_claim_ids[]`, `paid_claim_ids[]`,
`ap_open_balance_total` (USD 2dp), `crm_required_claim_ids[]`, `batch_status`, 
`reviewed_claim_count`.
- `batch_status` ∈ {`ready_to_close`, `open_payables`, `blocked`}.
- All claim-id lists ascending by claim_id.

### Task A stale-snapshot variant
Top-level: `eligible_claim_ids[]`, `not_ready_claim_ids[]`, `ap_balance_by_claim{}`,
`stale_snapshot_corrections{}`, `close_log_required{required, ids[]}`, `batch_status`.
- `stale_snapshot_corrections` value ∈ {`current_snapshot_ok`, `mark_in_flight_payment`,
  `replace_with_matched_paid_bill`, `exclude_amount_or_vendor_mismatch`, `ignore_void_bill`,
  `block_unapproved_claim`}.
- `close_log_required.ids` ascending by log id.
- `batch_status` ∈ {`ready_to_send`, `needs_ap_refresh`, `blocked`}.
- All claim-id lists ascending by claim_id; `ap_balance_by_claim` values USD 2dp.

### Task B (onboarding/KYC)
Top-level order: `per_business[]`, `reportable_ubo_counts{}`, `hard_stop_flags{}`,
`follow_up_business_ids[]`, `overall_release_ready`.
- `per_business[].decision` ∈ {`approve`, `awaiting_information`, `escalate`}; list ascending
  by `business_id`.
- `hard_stop_flags` value ∈ {`bank_closed`, `bank_name_mismatch`, `confirmed_pep`,
  `expired_license`, `missing_required_documents`, `sanctions_confirmed`,
  `screening_not_run`, `shell_company_suspected`, `vendor_on_hold`} — alphabetical within each
  list; `[]` when none.
- `reportable_ubo_counts` integer ≥ 0.
- `follow_up_business_ids` ascending; `overall_release_ready` boolean.

### Task C (prepaid close)
Top-level: `period` (YYYY-MM), `entity`, `selected_invoice_ids[]` (scope order),
`account_rollup{}`, `invoice_results[]` (scope order), `default_missing_term_invoice_ids[]`,
`exception_invoice_ids[]`.
- Per invoice object keys: `prepaid_invoice_id, account, march_amortization,
  cumulative_amortization_through_march, ending_balance, default_missing_term_flag,
  exception_flag` (2dp numbers).
- `account_rollup.<acct>` value fields: `account_name, selected_invoice_count,
  original_amount_total, march_amortization_total, cumulative_amortization_through_march,
  schedule_ending_balance, gl_ending_balance, variance_amount, variance_flag,
  has_default_missing_term_flag, account_status`.
- `account_status` ∈ {`reconciled`, `variance_review`, `requires_reconciliation`}.
- `variance_amount = schedule_ending_balance − gl_ending_balance`.
- `default_missing_term_invoice_ids` / `exception_invoice_ids` ascending by invoice id.

### Task D (payment-release risk)
Top-level: `task_id`, `batch_id`, `as_of_date (YYYY-MM-DD)`, `target_business_ids[]`,
`decisions{}`, `bank_mismatch_ids[]`, `invalid_tax_ids[]`, `expired_license_ids[]`,
`review_queue_ids[]`, `risk_score_override_flags[]`.
- `decisions` value ∈ {`release`, `hold`, `escalate`}.
- `task_id`, `batch_id`, `as_of_date`, `target_business_ids` are fixed by the batch payload.
- All id lists ascending by business_id.

---

## 9. Currency / precision conventions & the "USD cents" trap

- **Default:** USD, 2 decimals (dollars), per `environment_access.md` and the templates'
  `precision:2, unit:USD`. This applies to AP balances, prepaid totals, variance, etc.
- **The trap:** some prompts say "Use USD cents for currency totals" while the matching
  template field still declares `precision:2, unit:USD`. The template field schema is the
  machine-validated output contract, so emit **dollars with 2 decimals** (e.g. `1842.36`) into
  a `precision:2, unit:USD` field — do **not** emit bare integer cents. Treat "USD cents" as
  "cent-level precision (2 decimal dollars)." Always confirm against the template's
  `precision`/`unit` for each numeric field rather than the prompt wording alone.
- Variance/amortization math: compute in full precision, round only the final reported values
  to 2 decimals.

---

## 10. Concrete SOPs (quick reference)

### Reconciliation close (A)
1. Pull claims (status, amount, vendor).
2. Pull bills by `claim_id`; for each pull payments by `bill_id`.
3. Classify: paid (paid bill + cleared payment = amount) / payable (approved + open matching
   bill) / blocked (no valid matching bill or unapproved).
4. `ap_open_balance_total` = sum over payable of (bill.amount − cleared payments).
5. `batch_status` = blocked if any blocked else open_payables if any payable else ready_to_close.

### Stale-snapshot reconciliation (A variant)
1. Same pulls as above; diff against the CSV snapshot.
2. Assign one correction enum per candidate (see §3). Payable+clean snapshot →
   `current_snapshot_ok`.
3. `ap_balance_by_claim` for every candidate (0 for paid/blocked/mismatched/void).
4. `close_log_required`: collect non-closed `Waiting on AP export refresh` close logs whose
   `related_account` is among the batch's bill accounts; required=true if any.
5. `batch_status`: `needs_ap_refresh` if a stale refresh is pending and ≥1 eligible;
   `blocked` if hard-blocked with nothing eligible; `ready_to_send` if all eligible and
   current (rare).

### Onboarding / payment release (B / D)
1. Pull compliance + vendor per business.
2. Build hard-stop/derived lists (§4/§6).
3. Decision = escalate (any hard block) → hold (moderate) → release/approve (clean). Evidence
   drives it; `review_status=in_review` does not override clean evidence; `review_status=
   approved` does not override hard blocks.
4. Summary lists ascending; `overall_release_ready`/`review_queue` per rules.

### Prepaid close (C)
1. Pull scoped invoices + GL balances for each account@period.
2. Per invoice: `march_amortization` (monthly if period in window else 0),
   `cumulative = monthly × months service_start→end-of-period`,
   `ending_balance = original − cumulative`.
3. Roll up per account (sums), then `variance_amount = schedule − gl`,
   `variance_flag = |variance| >= threshold`.
4. Flags: `default_missing_term_flag` ← `missing_contract_dates`; `exception_flag` ← any
   data_quality_flag.
5. `account_status`: missing-term → `requires_reconciliation`; else variance_flag →
   `variance_review`; else `reconciled`.
6. Preserve scope order for `selected_invoice_ids`/`invoice_results`; sort the two id lists
   ascending.

### Payment-priority ranking (general, when a task asks to rank payable bills)
- Candidates: open bills (`balance > 0`, payable status `approved`/`scheduled`) from
  `/api/ap/bills`, excluding `void`/`draft` and fully-paid.
- **Rank by `due_date` ascending, then `bill_id` ascending.** Apply cleared payments first to
  derive each bill's open balance.
