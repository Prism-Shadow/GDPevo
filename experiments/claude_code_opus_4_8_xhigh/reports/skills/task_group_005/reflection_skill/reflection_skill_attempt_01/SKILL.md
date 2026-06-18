---
name: erp-finance-close-tasks
description: >-
  Solve ERP finance close/compliance tasks against the shared task_group_005 JSON
  API. Use this whenever a task involves the finance API at http://127.0.0.1:8029
  (claims, AP bills, payments, vendors, compliance, prepaids, GL, close logs) and
  asks you to decide a status/decision per item and return JSON matching an
  answer_template. Covers all six recurring task types: reimbursement-to-AP close
  triage, vendor onboarding finance-risk release, prepaid-to-GL close
  reconciliation, stale AP snapshot reconciliation, AP payment release after
  account-change events, and month-end exception reporting. Trigger even when the
  prompt only says "shared ERP/finance API", "task_group_005", "reimbursement
  close", "onboarding release", "prepaid close", "AP refresh", or "release
  posture" without naming this skill.
---

# ERP Finance Close & Compliance Tasks

You are answering finance-close / compliance questions whose **system of record is a
live JSON API**, returning a JSON object that conforms to a provided
`answer_template.json`. These tasks look simple but are full of traps where the
"obvious" reading of a field is wrong. This skill encodes the corrected rules.

## 0. Universal rules (apply to every task)

1. **Base URL is always `http://127.0.0.1:8029`.** Prompts often embed a stale URL
   (e.g. `http://127.0.0.1:8005`). Ignore it. If 8029 is unreachable, retry a few
   times before giving up — it is the only valid source.
2. **The API is the system of record.** Any CSV/JSON payload bundled with the task
   (snapshots, batches, scopes) is *context/scope*, never truth. Re-fetch every
   referenced entity live and reconcile against current state.
3. **List endpoints are paginated.** Responses wrap rows as
   `{endpoint,count,total,offset,limit,data:[...]}`. Read `data`. Default
   `limit=100`, max `500`. If `total > count`, page with `offset` until you have
   every row. Always pass `limit=500` for full pulls. Exact-match query params by
   field name are supported (e.g. `/bills?status=paid&limit=500`).
4. **Currency = USD with 2 decimals, NOT cents.** Prompt text sometimes says "use
   USD cents" — this is a decoy. The **answer_template wins**: when it says
   `unit:USD, precision:2`, emit dollars rounded to 2 decimals (e.g. `1842.36`).
   Only emit integer cents if the template itself defines the unit as cents.
5. **Follow the template literally.** Honor exact key names, key order
   (`top_level_order`), allowed enum values, list ordering (almost always
   *ascending by id*), and `additional_properties_allowed:false`. Round every
   numeric to the stated precision. Re-read the template's per-field `description`/
   `definition` — they encode the grading rule (e.g. "payable claims only",
   "schedule minus GL").
6. **Disambiguate duplicate IDs.** The same `bill_id` can appear on multiple rows
   with different vendor/amount/claim links. Never match on id alone — match on the
   tuple `(claim_id, vendor_id, amount)`. A bill that merely shares an id but has a
   different vendor/amount is a *wrong link*, not the real bill.
7. **Payment reality:** only `status == "cleared"` is real cash out. `scheduled`
   and `processing` are in-flight (NOT paid).
8. **Aging caveat:** `/api/ap/aging?as_of=YYYY-MM-DD` computes
   `balance = amount − payments`, but it nets **all** payments (scheduled +
   processing + cleared), not just cleared. So an aging `balance == 0` does **not**
   prove a bill is paid. Decide "paid" from `bill.status == paid` **plus** a matched
   **cleared** payment — do not trust aging balance for paid/open classification.

## Workflow for any task

1. `GET /health` then fetch the entities the task names. Pull full lists with
   `limit=500` and filter client-side; trust the live data over any payload.
2. Identify the task type (section below) from the template's top-level keys.
3. Apply that section's classification rules item by item.
4. Map results into the template; sort lists ascending by id; round numbers.
5. Re-read every field `description` and confirm enums/ordering before returning.

---

## Task type A — Reimbursement-to-AP close triage

Template keys: `payable_claim_ids`, `blocked_claim_ids`, `paid_claim_ids`,
`ap_open_balance_total`, `crm_required_claim_ids`, `batch_status`,
`reviewed_claim_count`.

Per claim, find its **valid** AP bill by matching `(claim_id, vendor_id, amount)`,
then look at the bill's payments. Classify:

- **paid** — a matched bill with `status == paid` AND a **cleared** payment for the
  claim amount. (Ignore extra/wrong-linked bills on the same claim.)
- **payable** — a valid open bill exists (e.g. `scheduled`/`approved`) but no cleared
  payment yet (a `processing` payment is still NOT paid). Stays in the AP queue.
- **blocked** — no valid bill, OR the only bill has a mismatched amount/vendor, OR
  the bill is `void`, OR there is an expense-case problem. Not releasable until
  fixed.

Fields:
- `ap_open_balance_total` = sum of open AP bill amounts **for payable claims only**
  (exclude paid, blocked). USD 2-dp.
- `crm_required_claim_ids` = the blocked claims (the template description covers both
  expense-case cleanup *and* AP-link remediation, so all blocked items go here).
- `batch_status` precedence: **any** blocked → `blocked`; else any payable →
  `open_payables`; else `ready_to_close`.
- `reviewed_claim_count` = count of requested claim ids.

## Task type B — Vendor onboarding finance-risk release

Template keys: `per_business`, `reportable_ubo_counts`, `hard_stop_flags`,
`follow_up_business_ids`, `overall_release_ready`. Use the batch's `as_of_date`.

Pull each business from `/compliance/objects` (rolled up) or the per-business
endpoints (`profile/ownership/registry/screening/bank/risk`).

**hard_stop_flags** (per business, list sorted alphabetically by enum value; `[]`
when none). Compute each independently:
- `bank_closed` — `bank_account_status == closed`
- `bank_name_mismatch` — `bank_account_status == name_mismatch`
- `confirmed_pep` — `pep_status == confirmed_pep`
- `sanctions_confirmed` — `sanctions_check_status == confirmed_match`
- `screening_not_run` — sanctions OR pep status `== not_run`
- `shell_company_suspected` — the shell-company flag is true
- `vendor_on_hold` — the vendor record `status == on_hold`
- `missing_required_documents` — required-documents/missing-fields list is non-empty
- `expired_license` — **trap, I got this wrong.** Flag ONLY when a license expiry
  date **exists on file** AND `license_expiry < as_of`. If the license/expiry is
  **absent** (no date on record), it is **NOT** `expired_license` — that absence is
  already captured by `missing_required_documents`. (Blind error: I flagged
  `expired_license` for businesses that simply had no license on file, e.g. ones
  also flagged `missing_required_documents` or `shell_company_suspected`. Only flag
  when there is a real past-dated expiry.) When a real date is present, the pure
  `expiry < as_of` comparison is correct.

**reportable_ubo_counts** = count of **unique beneficial-owner NAMES** with
`ownership_pct >= 25` (the reporting threshold is 25%). The ownership data contains
**duplicate UBO rows for the same person** — de-duplicate by name before counting,
or you will over-count. A business with no >=25% owners → `0`.

**decision** enum {`approve`, `awaiting_information`, `escalate`}:
- `escalate` — any **severe / integrity** hard stop: `confirmed_pep`,
  `sanctions_confirmed`, `shell_company_suspected`, `vendor_on_hold`,
  `bank_closed`, or `bank_name_mismatch`.
- `awaiting_information` — no severe stop, but a **remediable** gap remains:
  `missing_required_documents`, `screening_not_run`, or `expired_license`.
- `approve` — no hard stops at all.

`follow_up_business_ids` = every business that is **not** `approve` (i.e. escalate +
awaiting_information), ascending. `overall_release_ready` = `true` only if **every**
business is `approve` (so basically always `false` if any follow-up exists).

## Task type C — Prepaid-to-GL close reconciliation

Template keys: `period`, `entity`, `selected_invoice_ids`, `account_rollup`,
`invoice_results`, `default_missing_term_invoice_ids`, `exception_invoice_ids`.
Scope = the invoice ids and accounts in the scope payload; preserve scope order in
`selected_invoice_ids` and `invoice_results`.

Fetch invoices from `/api/prepaids/invoices` and GL from
`/api/prepaids/gl-balances` (or `/gl/balances?account=&period=`).

**Amortization (straight-line, trust the invoice's stated monthly figure):**
- Use each invoice's `monthly_amortization` directly. Do **not** recompute monthly
  from term dates — several invoices have `monthly * term != original_amount`; the
  stated monthly is authoritative.
- `cumulative_through_march` = `monthly * (#months from service start through the
  close month inclusive)`, **capped at `original_amount`**.
- `march_amortization` = `monthly` if the close month is within the service window,
  else `0` (or the final partial month).
- `ending_balance` = `original_amount − cumulative` (clamp tiny negatives to 0; leave
  legitimate small residuals like `0.01` as-is — do not force a final-month true-up
  unless the template says to).
- Round all to 2 dp. (These numeric rules produced exactly-correct totals in
  training — keep them.)

**default_missing_term_flag** (per invoice) / `default_missing_term_invoice_ids` =
invoices whose `data_quality_flags` include the missing-contract-dates flag (a
missing/defaulted term). Ascending.

**exception_flag** (per invoice) / `exception_invoice_ids` — **trap, I got this
wrong.** This is a **SUPERSET** of missing-term, not equal to it. An invoice is an
exception if its `data_quality_flags` array is **non-empty for ANY reason** —
including seemingly benign flags (e.g. rounded-amount / schedule-doesn't-tie /
partial-support), not just missing dates. (Blind error: I only flagged the
missing-term invoices and missed several that carried other quality flags.) Rule:
`exception_flag = (invoice has any data_quality_flag present)`. Read each invoice's
flags array; non-empty → exception. `exception_invoice_ids` is ascending.

**account_rollup** per account: `account_name`, `selected_invoice_count`,
`original_amount_total`, `march_amortization_total`,
`cumulative_amortization_through_march`, `schedule_ending_balance` (sum of invoice
ending balances), `gl_ending_balance` (from GL for that account+period),
`variance_amount = schedule_ending_balance − gl_ending_balance`,
`variance_flag = |variance| >= variance_threshold_abs`.

**account_status** enum {`reconciled`, `variance_review`, `requires_reconciliation`}
— **trap, I got this wrong.** Precedence:
- `requires_reconciliation` if the account has a missing-term invoice **OR ANY
  exception invoice** (any invoice with `exception_flag=true` in that account).
- else `variance_review` if `variance_flag` is true but no exceptions/missing-term.
- else `reconciled`.
(Blind error: I returned `variance_review` for an account that had an exception
invoice but no missing-term — it should have been `requires_reconciliation`. Any
data-quality exception in the account escalates it to requires_reconciliation.)

## Task type D — Stale AP snapshot reconciliation

Template keys: `eligible_claim_ids`, `not_ready_claim_ids`, `ap_balance_by_claim`,
`stale_snapshot_corrections`, `close_log_required`, `batch_status`. The CSV snapshot
is stale context; reconcile each candidate against live claim/bill/payment/close-log
data.

For each candidate, pick the `stale_snapshot_corrections` enum that describes the
live state, then derive eligibility from it:

- `current_snapshot_ok` — snapshot already matches live, clean. → **eligible**
- `mark_in_flight_payment` — valid open bill, payment now `processing`/`scheduled`
  (in-flight). → **eligible** (`ap_balance` = open bill amount).
- `replace_with_matched_paid_bill` — snapshot bill was a wrong/stale link; the real
  matched bill is `paid` + cleared. → **eligible** (`ap_balance = 0`). **Trap, I got
  this wrong:** a settled-by-correct-paid-bill claim **stays eligible** to remain in
  the batch (it is correctly resolved after the correction), it is NOT not_ready.
- `exclude_amount_or_vendor_mismatch` — the bill's amount/vendor disagrees with the
  claim. → **not_ready** (`ap_balance = 0`).
- `ignore_void_bill` — the bill is now `void`. → **not_ready** (`ap_balance = 0`).
- `block_unapproved_claim` — the claim itself is no longer approved (e.g.
  `needs_receipt`). Claim-state issue dominates any bill issue. → **not_ready**
  (`ap_balance = 0`).

So: **eligible** = {current_snapshot_ok, mark_in_flight_payment,
replace_with_matched_paid_bill}; **not_ready** = {exclude_amount_or_vendor_mismatch,
ignore_void_bill, block_unapproved_claim}. Both lists ascending.

`ap_balance_by_claim` (keyed by every candidate): open AP balance after cleared
payments, ignoring stale/void rows. Paid/void/mismatch → `0.00`; live open bill →
its amount. USD 2-dp.

`close_log_required` — **trap, I got this wrong (returned false/empty).** Do **not**
assume no close log applies. When a candidate is resolved by a settlement that landed
in a closed/closing period (notably `replace_with_matched_paid_bill`, i.e. a paid
bill that needs a period adjustment), a **close log entry IS required**. Query
`/close/logs` (or `/api/close/logs`, pull all with `limit=500`) and find the log(s)
that reference the resolved claim/bill or its settlement period; put the close-log
id(s) in `ids` (ascending) and set `required=true`. Only return
`{required:false, ids:[]}` if, after actually searching the logs, no log references
any reconciled item.

`batch_status`: `ready_to_send` if all candidates eligible and no corrections needed;
`needs_ap_refresh` if stale rows need correction but a path forward exists (typical
when some are eligible and some not_ready but nothing is hard-blocked); `blocked` only
if the batch cannot proceed.

## Task type E — AP payment release after account-change events

Template keys: `task_id`, `batch_id`, `as_of_date`, `target_business_ids`,
`decisions`, `bank_mismatch_ids`, `invalid_tax_ids`, `expired_license_ids`,
`review_queue_ids`, `risk_score_override_flags`. Echo required literal values
(`task_id`, `batch_id`, `as_of_date`) from the template; `additional_properties_allowed:false`.

Per business pull compliance (bank/tax/license/screening/risk/pep) + vendor status.

Evidence lists (all ascending by business_id):
- `bank_mismatch_ids` — `bank_account_status == name_mismatch` ONLY. `closed` is a
  *different* condition and does NOT belong here.
- `expired_license_ids` — `license_expiry < as_of_date` (date rule; same
  existence caveat as Task B — only when a date is on file).
- `risk_score_override_flags` — `risk_score >= 70` (inclusive; exactly 70 counts).
- `invalid_tax_ids` — **trap, I got this wrong (regex-only).** A tax id is invalid if
  it (a) fails the expected format (e.g. not `^TIN\d{6}$`, like `TIN12X899`), **OR**
  (b) is a placeholder/dummy (e.g. all-9s such as `TIN999999`), **OR** (c)
  vendor-record `tax_id` disagrees with the compliance/registry `tax_id`
  (cross-source mismatch). Check format **and** cross-source consistency — a
  syntactically valid placeholder that disagrees with the registry is invalid.

`decisions` enum {`release`, `hold`, `escalate`} — **trap, I mis-tiered this.**
Corrected tiering:
- `escalate` — **integrity/fraud** stops OR many stacked remediable gaps:
  `confirmed_pep`, `vendor_on_hold`, `sanctions_confirmed`,
  `shell_company_suspected`; OR **three or more** distinct remediable evidence gaps
  stacking (e.g. bank name_mismatch + invalid tax + expired license together).
- `hold` — a limited/remediable problem that needs review but is not an integrity
  stop: `risk_score >= 70` (by itself → **hold**, NOT escalate), `bank_closed`
  (→ hold), `screening_not_run` (→ hold), or one/two remediable gaps (single bank
  mismatch, single expired license, etc.).
- `release` — no issues at all.

Key blind corrections to remember: **risk_score>=70 alone = hold** (not escalate);
**bank_closed / screening_not_run = hold** (not escalate); **confirmed_pep /
vendor_on_hold = escalate**; **three stacked remediable gaps = escalate** even with
no pep/hold/sanctions/shell.

`review_queue_ids` = every business whose decision is **not** `release` (hold +
escalate), ascending.

## Task type F — Month-end exception reporting

Not seen in training, but it draws on the same primitives: pull the relevant lists
(claims/bills/payments/prepaids/GL/close logs) with `limit=500`, apply the same
field definitions and traps above (cleared-only cash, aging caveat, duplicate-id
disambiguation, exception = any data-quality flag, USD 2-dp), and emit exactly the
template's keys/enums/ordering. Re-read each field description for its precise rule.

---

## Pitfall checklist (read before returning)

- [ ] Used base URL **8029**, ignored any other URL in the prompt.
- [ ] Treated bundled CSV/JSON payload as scope only; reconciled against live API.
- [ ] Paged all lists (`limit=500`, checked `total`).
- [ ] Currency in **USD 2-dp**, ignored "cents" decoy unless template says cents.
- [ ] Matched bills by `(claim_id, vendor_id, amount)`, not bill_id alone.
- [ ] "paid" requires bill.status=paid **and** a cleared payment (not aging=0).
- [ ] `expired_license` only when an expiry date exists and is past as_of (absence =
      missing_required_documents, not expired).
- [ ] UBO count = unique NAMES at >=25%, de-duplicated.
- [ ] `exception_flag` = any non-empty data_quality_flags (superset of missing-term).
- [ ] `account_status=requires_reconciliation` if missing-term **or any exception**.
- [ ] `replace_with_matched_paid_bill` → still **eligible**.
- [ ] Actually searched `/close/logs` before setting close_log_required=false.
- [ ] `invalid_tax` checks format **and** placeholder **and** cross-source mismatch.
- [ ] Decision tiering: pep/on_hold/sanctions/shell or 3+ stacked gaps → escalate;
      risk>=70 / bank_closed / screening_not_run / 1-2 gaps → hold; clean → release.
- [ ] All id lists sorted ascending; key order and enums match template exactly.
