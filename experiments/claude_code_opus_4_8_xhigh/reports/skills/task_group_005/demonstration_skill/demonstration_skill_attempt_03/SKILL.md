---
name: erp-finance-close-reviewer
description: >-
  Executable playbook for the task_group_005 ERP finance JSON API: reimbursement-to-AP
  close reviews, vendor onboarding/intake compliance release, prepaid-to-GL close
  reconciliation, stale AP-snapshot reconciliation, AP payment release after vendor
  account changes, and month-end exception reporting. Use this whenever a task references
  expense claims, AP bills/payments/aging, vendor onboarding or compliance gates
  (profile/ownership/registry/screening/bank/risk), prepaid amortization vs GL balances,
  close logs, or asks for a JSON answer matching an answer_template against this ERP API —
  even if the prompt only mentions "the shared finance API", a batch of claim IDs, or a
  batch of business IDs. It encodes the exact field definitions, decision rules, enum
  values, rounding, sorting, and pitfalls (stale snapshots, voided bills, amount/vendor
  mismatches, non-unique bill IDs, cleared-vs-processing payments) needed to reproduce
  the official answers.
---

# ERP Finance Close Reviewer

This skill turns the shared ERP finance API into correct, template-shaped JSON answers.
The rules below were reverse-engineered from real task inputs and their official answers and
re-verified against the live API. Follow them literally; the grading is exact-match on
values, enums, rounding, and sort order.

## 1. API access (always do this first)

- **Base URL:** `http://127.0.0.1:8029`. **Ignore any other base URL** a prompt mentions
  (e.g. `:8005`, `:8029` variants in narrative text). Confirm with `GET /health`.
- Fetch only via HTTP GET + `curl`. Never read local server files.
- **List endpoints wrap rows:** `{"endpoint","count","total","offset","limit","data":[...]}`.
  Read `data`. Default `limit=100`, max `500`. If `total > count`, paginate with
  `offset`, or just pass `limit=500`. Always check `total` to be sure you got everything.
- **Exact-match filters by field name** work on list endpoints, e.g.
  `/api/ap/bills?claim_id=CLM-2025-0001`, `/gl/balances?account=1250&period=2025-03`.
- Single-object endpoints exist for claims (`/api/claims/{id}`) and compliance
  (`/api/compliance/{profile|ownership|registry|screening|bank|risk}/{business_id}`).

### Endpoint map
| Domain | Endpoint(s) | Key fields |
|---|---|---|
| Claims | `/api/claims`, `/api/claims/{id}` | claim_id, status, amount, vendor_id, approved_date, receipt_status |
| AP bills | `/api/ap/bills` (alias `/bills`) | bill_id, claim_id, vendor_id, amount, status, due_date |
| Payments | `/api/ap/payments` (alias `/payments`) | payment_id, bill_id, vendor_id, amount, status |
| AP aging | `/api/ap/aging?as_of=YYYY-MM-DD` | per-bill `paid_amount`, `balance = amount − paid_amount` |
| Vendors | `/api/vendors` (alias `/vendors`) | vendor_id, status, payment_terms |
| Compliance | `/api/compliance/{type}/{business_id}` | see §3 |
| Prepaids | `/api/prepaids/invoices` (alias `/prepaids/invoices`) | original_amount, monthly_amortization, service_start/end, account, data_quality_flags |
| GL balances | `/api/prepaids/gl-balances` (alias `/gl/balances`) | account, period, ending_balance, account_name |
| Close logs | `/api/close/logs` (alias `/close/logs`) | log_id, area, period, status, related_account, message |

> **Pitfall — `bill_id` is NOT unique.** The same `bill_id` can return multiple rows with
> different vendor/amount/claim_id. Always disambiguate by also matching `claim_id`,
> `vendor_id`, and `amount`. The same applies in `/api/ap/aging`.

## 2. Reimbursement / AP close & stale-snapshot review (claim batches)

Task types: "reimbursement-to-AP close" (train_001 family) and "stale AP snapshot
reconciliation" (train_004 family). Both take a list of candidate `claim_id`s and ask which
can stay in the AP batch.

### Per-claim procedure
For each candidate claim:
1. `GET /api/claims/{claim_id}` → record `status`, `amount`, `vendor_id`.
2. `GET /api/ap/bills?claim_id={claim_id}` → its linked bill(s).
3. **Match a valid bill:** a bill is the claim's valid bill only if
   `bill.amount == claim.amount` AND `bill.vendor_id == claim.vendor_id` AND
   `bill.status != "void"`. (Claim `vendor_id` may be `null`; then a bill with a real
   vendor does NOT match → mismatch.)
4. For the matched bill, `GET /api/ap/payments?bill_id={bill_id}` and keep only payments
   whose `bill_id`+`vendor_id` line up with this claim's bill.

### Disposition decision tree (apply top-down)
- `claim.status` not in {`approved`,`paid`} → **blocked** (reason `block_unapproved_claim`).
- No bill at all for the claim → **blocked** (no AP evidence).
- Matched bill is `void` → **blocked** (reason `ignore_void_bill`).
- Bill amount ≠ claim amount OR bill vendor ≠ claim vendor (and not void) → **blocked**
  (reason `exclude_amount_or_vendor_mismatch`).
- Matched valid bill with `status=="paid"` AND a `cleared` payment for the full claim
  amount → **paid** (reason `replace_with_matched_paid_bill` when a stale snapshot listed a
  different/scheduled bill).
- Matched valid open bill (scheduled/approved), payment exists but is `processing`/
  `scheduled` (not `cleared`) → **payable**, in-flight (reason `mark_in_flight_payment`).
- Matched valid open bill, no payment, snapshot agrees → **payable**
  (reason `current_snapshot_ok`).

> "eligible to stay in batch" = **payable ∪ paid**. "blocked"/"not_ready" = everything else.
> In train_001 the template separates `paid` from `payable`; in train_004 both are `eligible`.
> Read the template to see which split it wants.

### AP open balance (CRITICAL: cleared-payments-only)
Compute the open balance yourself — **do NOT trust `/api/ap/aging` `balance`/`paid_amount`**,
because aging counts `processing`/`scheduled` payments toward `paid_amount`, hiding real
open balances.
```
open_balance(claim) =
  0.00                                   if no matched valid bill, or bill status == "paid"
  bill.amount − sum(payments where status == "cleared")   otherwise
```
Round to 2 decimals. Example: an in-flight reimbursement (bill scheduled, payment
`processing`) has open balance = full bill amount even though aging shows balance 0.
- `ap_open_balance_total` (train_001) = sum of `open_balance` over **payable claims only**.
- `ap_balance_by_claim` (train_004) = map every candidate claim → its `open_balance`.

### Stale-snapshot correction enum
Map each candidate claim to its reason from the disposition tree above. Allowed values:
`current_snapshot_ok`, `mark_in_flight_payment`, `replace_with_matched_paid_bill`,
`exclude_amount_or_vendor_mismatch`, `ignore_void_bill`, `block_unapproved_claim`.

### Close-log requirement (train_004 family)
When an in-flight payment / replaced-paid-bill correction means AP must be re-posted, find
the supporting close log: the **AP-area** log (`area=="AP"`) for the **period** of that bill
(e.g. bill_date 2025-04-* → period `2025-04`) documenting the journal entry
(`message` ~ "Manual journal entry posted"). Return `close_log_required.required=true` and
its `log_id`(s) sorted ascending. If no correction needs posting, `required=false`, `ids=[]`.

### batch_status enum
- train_001 (`ready_to_close` / `open_payables` / `blocked`): `blocked` if any item blocked;
  else `open_payables` if any valid unpaid AP bill remains; else `ready_to_close`.
- train_004 (`ready_to_send` / `needs_ap_refresh` / `blocked`): `blocked` if a candidate is
  hard-blocked in a way that stops the batch; else `needs_ap_refresh` if any candidate
  required a stale-snapshot correction (in-flight/replaced/void/mismatch) but eligible items
  remain; else `ready_to_send`.

## 3. Compliance gates: onboarding release & AP payment release

Two task types share the compliance endpoints, keyed by `business_id`:
fetch `profile`, `ownership`, `registry`, `screening`, `bank`, `risk`. Find the linked vendor
via `profile.vendor_id` then `/api/vendors?vendor_id=...` for vendor `status`.

### Shared field definitions
- **bank mismatch:** `bank.bank_account_status == "name_mismatch"`. (`closed` is separate.)
- **invalid tax id:** `profile.tax_id` (or `registry.tax_id`) is NOT `^TIN\d{6}$`, OR equals
  the placeholder `TIN999999`. (Letters like `TIN12X899` → invalid; all-9s → invalid.)
- **expired license:** compare `registry.license_expiry` to the task's as_of date. Default
  rule (payment-release / train_005): `license_expiry < as_of_date` (plain).
  **Read the answer_template** — it states the comparison date. (Onboarding/train_002 behaved
  like a ~30-day grace: `license_expiry < as_of − 30d`; when in doubt use the template's
  `comparison_date`.) If `license` is in `profile.missing_fields`, treat it as a missing
  document, not an expired license.
- **screening not run:** `screening.sanctions_check_status == "not_run"`
  (also surfaces as the `screening_not_run` hard stop).
- **confirmed PEP:** `screening.pep_status == "confirmed_pep"` (`possible_pep` does NOT count).
- **sanctions confirmed:** `screening.sanctions_check_status` is a confirmed hit.
- **shell company:** `ownership.shell_company_suspected == true`.
- **vendor on hold:** linked vendor `status == "on_hold"`.
- **missing required documents:** `profile.missing_fields` non-empty.
- **risk score override:** `risk.risk_score >= 70`.

### 3a. Vendor onboarding intake (train_002 family)
Output: per-business `decision`, `reportable_ubo_counts`, `hard_stop_flags`,
`follow_up_business_ids`, `overall_release_ready`.

**reportable_ubo_counts:** from `ownership.ubo_list`, count **unique owner names** with
`ownership_pct >= 25`. Dedupe by name (the same name listed twice counts once); owners below
25% are excluded.

**hard_stop_flags** (per business, **alphabetical**, empty list if none). Allowed enum:
`bank_closed` (bank_account_status=="closed"), `bank_name_mismatch`, `confirmed_pep`,
`expired_license` (only when license present & expired, see grace note), `sanctions_confirmed`,
`screening_not_run`, `shell_company_suspected`, `missing_required_documents`, `vendor_on_hold`.

**decision** per business:
- `approve` — no hard-stop flags.
- `awaiting_information` — only *curable* flags present: `missing_required_documents` and/or
  `screening_not_run`, and nothing more serious.
- `escalate` — any *serious* flag present (`confirmed_pep`, `sanctions_confirmed`,
  `bank_name_mismatch`, `bank_closed`, `expired_license`, `shell_company_suspected`,
  `vendor_on_hold`). Serious-flag presence dominates even if curable flags also exist.

**follow_up_business_ids:** every business with ≥1 hard-stop flag (i.e. decision ≠ approve),
ascending. **overall_release_ready:** `true` only if every business is `approve`.

### 3b. AP payment release after account changes (train_005 family)
Output: `decisions`, `bank_mismatch_ids`, `invalid_tax_ids`, `expired_license_ids`,
`review_queue_ids`, `risk_score_override_flags`. Echo `task_id`/`batch_id`/`as_of_date`/
`target_business_ids` exactly as the template/payload requires.

**decision** per business (enum `release`/`hold`/`escalate`):
- `escalate` — identity-integrity failure: `invalid_tax_id` OR `confirmed_pep` OR sanctions
  hit.
- `release` — no issues at all (bank verified, valid tax, license current, screening run,
  pep none, sanctions clear). Note: `risk.review_status` like `in_review` and a high
  `risk_score` alone do NOT block a release if everything else is clean.
- `hold` — has operational issues (bank `name_mismatch`/`closed`, expired license,
  screening not run, missing docs, risk_score ≥ 70) but identity is intact (valid tax, no
  confirmed pep, no sanctions hit).

**ID lists** (each ascending by business_id):
- `bank_mismatch_ids` = bank_account_status == "name_mismatch".
- `invalid_tax_ids` = invalid tax id rule above.
- `expired_license_ids` = `license_expiry < as_of_date` (this family uses plain comparison;
  template confirms `comparison_date: as_of_date`).
- `risk_score_override_flags` = `risk_score >= 70`.
- `review_queue_ids` = every business that is NOT released (i.e. decision ∈ {hold, escalate}).

## 4. Prepaid-to-GL close reconciliation (train_003 family)

Inputs: an entity, a close period `YYYY-MM`, a scoped list of prepaid invoice IDs, the
accounts to reconcile, and a `variance_threshold_abs`. Use straight-line amortization as
encoded in each invoice (`monthly_amortization`, `original_amount`, `service_start/end`).

### Per-invoice math (round each money value to 2 decimals)
Let `months_elapsed = (period_year − start_year)*12 + (period_month − start_month) + 1`
(inclusive of both the service-start month and the close-period month), **capped** at the
invoice's total service months `(end_y−start_y)*12 + (end_m−start_m) + 1`, and floored at 0.
```
march_amortization        = monthly_amortization          (the period's monthly figure)
cumulative_amortization   = min(monthly_amortization * months_elapsed, original_amount)
ending_balance            = round(original_amount − cumulative_amortization, 2)
```
Keep tiny rounding residuals as-is (e.g. ending `0.01`); do NOT force to 0. A fully-elapsed
invoice (months_elapsed ≥ total months) ends at `original_amount − original_amount`.

### Per-invoice flags
- `default_missing_term_flag` = `"missing_contract_dates" in data_quality_flags`.
- `exception_flag` = `data_quality_flags` is non-empty (ANY flag, e.g. `rounded_amount` OR
  `missing_contract_dates`).
Emit `invoice_results` in the **same order as the scope list** (not sorted).

### Account rollup (per account key, e.g. "1250", "1251")
- `account_name` from the GL balance row. `selected_invoice_count` = scoped invoices on that
  account.
- `original_amount_total`, `march_amortization_total`, `cumulative_amortization_through_march`,
  `schedule_ending_balance` = sums of the per-invoice values for that account (2 decimals).
- `gl_ending_balance` = `GET /api/prepaids/gl-balances?account={acct}&period={period}` →
  `ending_balance`.
- `variance_amount = schedule_ending_balance − gl_ending_balance` (round 2).
- `variance_flag = abs(variance_amount) > variance_threshold_abs`.
- `has_default_missing_term_flag` = any invoice on the account has `default_missing_term_flag`.
- `account_status` enum: `requires_reconciliation` when `variance_flag` is true (material
  variance); else `variance_review` when no material variance but data-quality/missing-term
  exceptions exist; else `reconciled`.

### Top-level lists
- `selected_invoice_ids` = scope list, **same order**.
- `default_missing_term_invoice_ids` and `exception_invoice_ids` = the matching invoice IDs,
  **ascending**.

## 5. Output discipline (applies to every task type)

- Return **only** the JSON object that conforms to `answer_template.json`. No prose.
- Honor `required_top_level_keys` / `top_level_order` and `additional_properties_allowed`.
- **Currency:** USD, **2 decimals** (cents). When a template says "USD cents", confirm
  whether it wants integer cents vs a 2-decimal number — match the template's `unit`/`type`.
- **Sorting:** every ID list ascending by ID **unless** the template says otherwise
  (prepaid `selected_invoice_ids`/`invoice_results` keep scope order).
- **Enums:** use the exact allowed strings; never invent values.
- Re-read the template's per-field `description`/`definition` before finalizing — it often
  states the exact computation (e.g. "schedule_ending_balance minus gl_ending_balance",
  "risk_score >= 70", "bank_account_status is name_mismatch").

## 6. Quick SOP per task type
1. Identify task type from the prompt + payload (claim batch → §2; business batch with
   onboarding/intake → §3a; business batch with account-change/payment-release → §3b;
   prepaid invoices + accounts + period → §4).
2. Read the payload (scope/batch IDs, as_of/period, thresholds) and the `answer_template.json`
   (keys, enums, ordering, precision).
3. Pull every needed record from the API at `http://127.0.0.1:8029` (paginate to `total`).
4. Apply the rules above; compute money to 2 decimals; dedupe and sort as specified.
5. Emit JSON exactly matching the template; do a final pass against each field's description.
