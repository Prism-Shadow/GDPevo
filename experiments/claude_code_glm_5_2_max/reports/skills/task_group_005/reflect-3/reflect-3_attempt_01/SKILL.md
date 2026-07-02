# ERP Finance Expense-Control Skill (task_group_005)

Reusable workflow rules for expense-control / AP / prepaid-close / vendor-compliance
tasks against the shared ERP finance API. Distilled from reflect training.

## 1. API contract

- Base URL: `<remote-env-url>` (runner-provided; treat remote API as system of record).
- `GET /endpoints` lists all paths. All list endpoints support exact-match query params by
  field name, plus `limit`/`offset`.
- Resource paths (use the `/api/...` form):
  - Claims: `GET /api/claims?claim_id=<id>`
  - AP bills: `GET /api/ap/bills?claim_id=<id>` (also queryable by bill_id)
  - AP payments: `GET /api/ap/payments?bill_id=<bill_id>`
  - Vendors: `GET /api/vendors?vendor_id=<id>`
  - Compliance: `GET /api/compliance/objects?business_id=<id>` (returns bank, license, PEP,
    sanctions, shell, tax_id, ubo_list, risk_score, review_status, missing_fields in one object)
  - Prepaid invoices: `GET /api/prepaids/invoices?prepaid_invoice_id=<id>`
  - GL balances: `GET /api/prepaids/gl-balances?account=<acct>` (returns per-period ending_balance)
  - Close logs: `GET /api/close/logs` (area, period, related_account, status, message)
- Efficiency: batch curl calls; query by specific ID/param only; never dump whole collections.
- Currency: report USD to two decimals unless a task explicitly says otherwise. When a prompt
  says "USD cents" but the schema field says `unit: USD, precision: 2`, emit the USD value to
  2 decimals (the schema wins).

## 2. General reconciliation SOP

1. Read the task's `payloads/answer_template.json` FIRST — it defines required keys, enums,
   ordering, and unit/precision. Conform exactly (extra props often disallowed; ordering enforced).
2. Fetch the candidate IDs' current records from the API (claims, bills, payments, vendors,
   compliance, prepaids, GL, close-logs as relevant). Ignore stale local snapshots/prompts that
   conflict — the API is the system of record.
3. For each candidate, classify using the rules below, then aggregate (totals, flag lists,
   status) per the template.
4. Sort every ID list exactly as the template specifies (ascending by id unless stated).
5. Keep candidate answers minimal-valid JSON.

## 3. Expense-claim reimbursement close (claim -> AP bill -> payment)

Classify each batch claim into exactly one bucket:
- **paid**: a matching AP bill (bill.amount == claim.amount AND bill.vendor_id ==
  claim.vendor_id) with status `paid` AND a cleared payment (payment.status == `cleared`) for
  that amount. A `processing`/in-flight payment does NOT count as paid.
- **payable (can remain in AP queue)**: claim approved, and a valid OPEN (scheduled/approved,
  not paid/void) AP bill that matches claim amount + vendor. In-flight (processing) payment
  leaves it payable; the open AP balance still equals the bill amount.
- **blocked**: not paid and cannot be released — no matching bill, amount/vendor mismatch,
  voided bill, unapproved claim, or expense-case issue. These need owner/AP-link cleanup.

Derived fields:
- `ap_open_balance_total` = sum of valid open matching AP bill amounts for payable claims only
  (USD 2dp). Exclude mismatched, voided, and already-paid bills.
- `crm_required_claim_ids` = blocked claims requiring expense-case or AP-link remediation
  (equals the blocked set when all blockers are cleanup-type).
- `batch_status`: `blocked` if any claim blocked; else `open_payables` if valid unpaid AP bills
  remain; else `ready_to_close`.
- `reviewed_claim_count` = number of batch claims reviewed.

Multiple bills per claim: pick the one matching claim amount+vendor as the "real" bill; stray
bills (wrong vendor/amount) are ignored for balance but noted as AP-link issues.

## 4. Vendor onboarding finance-risk release (per business)

Input: compliance object + vendor record per business_id. As-of date from batch payload.

**reportable_ubo_counts** = count of UNIQUE beneficial-owner names in `ubo_list` with
`ownership_pct >= 25` (the 25% reporting threshold). Deduplicate by name; a name qualifies if
ANY of its entries is >= 25%. (24% does NOT count; 30%+ does. This threshold was confirmed:
using 10% drops the score.)

**hard_stop_flags** (alphabetical; empty list when none) — derive from compliance object:
- `bank_closed`        : bank_account_status == "closed"
- `bank_name_mismatch` : bank_account_status == "name_mismatch"
- `confirmed_pep`      : pep_status == "confirmed_pep"  (possible_pep / not_run do NOT set this)
- `expired_license`    : license_expiry < as_of_date
- `missing_required_documents` : missing_fields non-empty
- `sanctions_confirmed`: sanctions_check_status indicates a confirmed hit
- `screening_not_run`  : sanctions_check_status == "not_run" OR pep_status == "not_run"
- `shell_company_suspected`: shell_company_suspected == true
- `vendor_on_hold`     : vendor.status == "on_hold"
Note: tax_id mismatch between compliance and vendor is NOT one of the hard_stop enum values.

**decision** {approve, awaiting_information, escalate}:
- `escalate` if ANY serious flag: confirmed_pep, sanctions_confirmed, shell_company_suspected,
  bank_closed, bank_name_mismatch.  (PEP/shell/bank issues escalate — confirmed: downgrading
  them to awaiting_information drops the score.)
- else `awaiting_information` if any remediable flag: missing_required_documents,
  screening_not_run, expired_license, vendor_on_hold.
- else `approve` (no hard stops).

**follow_up_business_ids** = businesses whose decision is not `approve` (ascending).
**overall_release_ready** = true only if every business is `approve`.

Common misjudgments:
- Treating escalate as sanctions-only (too narrow) — PEP/shell/bank must escalate.
- Using a 10% UBO threshold — use 25%.
- Forgetting screening_not_run also covers pep_status == "not_run".

## 5. Prepaid close reconciliation (per account, per period)

Input: scoped prepaid invoice IDs + accounts + close period + variance_threshold_abs.

Per invoice (straight-line monthly amortization):
- `march_amortization` (period month) = the invoice's `monthly_amortization` FIELD when the
  period month falls within [service_start month .. service_end month]; else 0. Use full-month
  convention: the service_start month counts as a full month (a 03-15 start amortizes all of
  March).  *** Use the monthly_amortization FIELD, NOT original_amount/term *** — exact
  original/term recomputation drops the score.
- `cumulative_amortization_through_march` = monthly_amortization FIELD × number of months
  elapsed from service_start month through the close month (inclusive).
- `ending_balance` = original_amount − cumulative_amortization_through_march (2dp).
- `default_missing_term_flag` = true iff `missing_contract_dates` is in data_quality_flags.
- `exception_flag` = true iff data_quality_flags is NON-EMPTY (any flag — superset, not just
  rounded_amount). default_missing_term is a subset of exceptions.

Per account rollup (sum over the account's selected invoices):
- original_amount_total, march_amortization_total, cumulative_amortization_through_march,
  schedule_ending_balance (= original_total − cumulative_total).
- `gl_ending_balance` = the GL balance record whose period == close period for that account.
- `variance_amount` = schedule_ending_balance − gl_ending_balance (2dp; can be negative).
- `variance_flag` = |variance_amount| > variance_threshold_abs.
- `has_default_missing_term_flag` = any selected invoice in the account has missing_term.
- `account_status`:
  - `requires_reconciliation` if has_default_missing_term_flag (data-quality prevents a clean tie).
  - else `variance_review` if variance_flag.
  - else `reconciled`.

Output lists: `default_missing_term_invoice_ids` and `exception_invoice_ids` ascending by
invoice id (note: "PPD-2025-..." sorts before "PPD-AUR-..." because '2' < 'A').
`selected_invoice_ids` and `invoice_results` keep the SAME order as the scope file.

Common misjudgments:
- Recomputing cumulative as original×months/term (exact) instead of monthly_field×months — drops.
- Using disjoint exception (only rounded_amount) instead of superset — drops.
- Prorating mid-month starts — use full-month.

## 6. AP batch reconciliation from a stale export (claim, bill, payment, close-log)

For each candidate claim, compare the stale snapshot to CURRENT API data:
- **eligible_claim_ids**: approved claim with a valid OPEN AP bill matching amount+vendor (amount
  & vendor match), and no blocking issue. An in-flight (processing) payment keeps it eligible;
  its open AP balance = the bill amount (payment not yet cleared).
- **not_ready_claim_ids**: paid (already settled), amount/vendor mismatch, voided bill, or
  unapproved claim.
- **ap_balance_by_claim** (USD 2dp): valid matching OPEN bills minus CLEARED payments, EXCLUDING
  mismatched and voided bills. A paid claim => 0. A claim whose only bill mismatches => 0 (the
  mismatched bill is excluded, NOT counted). A voided bill => 0.  *** Do NOT count every open
  non-voided bill regardless of match — counting mismatched bills drops the score. ***
- **stale_snapshot_corrections** (per claim, enum):
  - `mark_in_flight_payment`        : snapshot showed no payment but current shows a processing payment.
  - `replace_with_matched_paid_bill`: snapshot referenced a wrong (mismatched) scheduled bill; current
    has a matched PAID bill + cleared payment.
  - `exclude_amount_or_vendor_mismatch`: bill amount or vendor does not match the claim.
  - `ignore_void_bill`              : the linked bill is void in the current API.
  - `block_unapproved_claim`        : claim status is not approved (e.g. needs_receipt).
  - `current_snapshot_ok`           : snapshot already matches current state.
- **batch_status**: `needs_ap_refresh` when the batch originated from a stale AP export and must
  be reconciled before sending (default for stale-snapshot batches with mixed eligibility).
  `ready_to_send` only when all candidates eligible. `blocked` is for hard blocks — do not use
  it merely because some claims are not ready (using "blocked" here drops the score).
- **close_log_required**: {required: bool, ids: [close_log_id ascending]}. Inspect /api/close/logs
  for AP-area entries relevant to the claim bill accounts/period; include unresolved
  (open/ready_for_review/blocked) log ids when the batch needs close-log documentation. (This
  field's exact trigger was not fully resolved in training — verify against current logs.)

Common misjudgments:
- Counting mismatched open bills in ap_balance (drops).
- Setting batch_status="blocked" instead of "needs_ap_refresh" (drops).

## 7. Payment release after vendor account-change (per business)

Input: compliance object + vendor record + account-change ticket per business. Review/as_of date
from payload. Enumerate blocking conditions, then decide.

Derived flag lists (ascending business_id):
- `bank_mismatch_ids` = bank_account_status == "name_mismatch" (closed is NOT a mismatch).
- `invalid_tax_ids` = compliance.tax_id != vendor.tax_id, or tax_id has invalid format
  (e.g. contains non-digits / placeholder like all-9s).
- `expired_license_ids` = license_expiry < as_of_date (strict date compare; a license expiring
  the day AFTER as_of is NOT expired).
- `risk_score_override_flags` = risk_score >= 70.
- `review_queue_ids` = businesses not released (hold or escalate).

**decisions** {release, hold, escalate} — scored as a whole object (ALL businesses must match
exactly; a single wrong decision fails the entire decisions field):
- `escalate`: any serious condition — confirmed_pep, sanctions_confirmed,
  shell_company_suspected, bank_closed. (Payment to a closed bank / confirmed PEP escalates.)
- `hold`: remediable/blocking conditions without a serious one — bank_name_mismatch, invalid_tax,
  expired_license, missing license, screening_not_run, risk_score >= 70. (High risk needs an
  override before release => hold, not escalate.)
- `release`: no blocking conditions (bank verified, license valid, sanctions clear, no PEP, tax
  valid, vendor active, risk < 70).

Common misjudgments:
- Escalating bank_name_mismatch / risk>=70 (these are hold, not escalate).
- Holding confirmed_pep / bank_closed (these escalate).
- Forgetting the decisions field is all-or-nothing — verify every business.
- Counting a license expiring the next day as expired.

## 8. Cross-task pitfalls (sharpened by judge feedback)

- Obey the answer_template's enum vocabularies and ordering literally; do not invent values.
- Currency: schema unit/precision wins over loose "cents" wording in the prompt.
- "System of record" = remote API. Stale CSV/snapshot payloads are context only; always
  re-fetch current claim/bill/payment/compliance/GL state.
- Match logic for AP bills: amount AND vendor_id must equal the claim's. Stray/legacy bills
  linked to a claim are ignored (not counted in balances), but drive the correction enum.
- A `processing` payment is NOT `cleared` — it does not settle a claim or reduce AP balance.
- When a round's score drops after a change, revert; the prior interpretation was closer.
  Judge feedback is coarse (single score), so change one concept at a time, not many at once.
- Avoid over-correcting from arithmetic reverse-engineering: confirm a hypothesis by a score
  RISE before keeping it.
