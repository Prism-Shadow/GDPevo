# SKILL: ERP Finance Close & Compliance Decisions (task_group_005)

Executable experience for answering month-end / release-control finance tasks against a
read-only ERP+compliance JSON API. Five recurring task families: (1) reimbursement-to-AP
close, (2) vendor onboarding compliance gating, (3) prepaid/GL reconciliation,
(4) stale-AP-snapshot batch review, (5) AP payment-release after account-change events.

The unifying principle across every family: **the live API is the system of record.**
Any CSV/JSON snapshot, "current review status," `review_status` field, or base URL in the
prompt is *context only* — re-derive every decision from current API records.

---

## 0. THE API (your only data source)

Base URL is provided by the runner. **IGNORE any base URL written inside a prompt or
payload (e.g. `http://127.0.0.1:8005`).** Query with `curl`.

- `GET /endpoints` lists all routes. `GET /health` returns `{status, task_group}`.
- Two prefixes exist for most resources and return identical data: bare (`/claims`) and
  `/api/...` (`/api/claims`). Prefer the `/api/...` form.
- Object list endpoints return `{endpoint,count,total,offset,limit,data:[...]}`.
- **Filtering = exact-match query params by field name** + `limit`/`offset`. e.g.
  `/api/ap/bills?claim_id=CLM-2025-0090`, `/api/compliance/objects?business_id=BUS-2025-0009`,
  `/api/ap/payments?bill_id=AP-2025-0079`. Always pass `limit=100`+ to avoid truncation when
  scanning (defaults are small; totals: ~100s of rows per resource).

### Endpoint map (which endpoint answers which question)
| Need | Endpoint |
|---|---|
| Expense claim record (status, amount, vendor_id, receipt_status, policy_flags) | `/api/claims?claim_id=...` |
| AP bills linked to a claim | `/api/ap/bills?claim_id=...` (a claim may have 0, 1, or many bills) |
| AP bills by id | `/api/ap/bills?bill_id=...` |
| Payments against a bill | `/api/ap/payments?bill_id=...` |
| Open AP balance as of a date | `/api/ap/aging?as_of=YYYY-MM-DD` (filter by `bill_id`/`claim_id`/`vendor_id`) |
| Vendor master (status, bank_account_last4, tax_id, payment_terms) | `/api/vendors?vendor_id=...` |
| Full denormalized compliance record | `/api/compliance/objects?business_id=...` |
| Compliance field-by-field (authoritative) | `/api/compliance/{profile\|ownership\|registry\|screening\|bank\|risk}/{business_id}` |
| Prepaid amortization schedules | `/api/prepaids/invoices?prepaid_invoice_id=...` |
| GL ending balances by account/period | `/api/prepaids/gl-balances` (a.k.a. `/gl/balances`) |
| Month-end close log entries | `/api/close/logs?area=...&period=...&status=...` |

### Compliance detail endpoints — field split
`profile`→business_name,jurisdiction,registration_number,tax_id,missing_fields,vendor_id;
`ownership`→ownership_layer_count,shell_company_suspected,ubo_list[{name,ownership_pct}];
`registry`→jurisdiction,license_expiry,registration_number,tax_id;
`screening`→pep_status,sanctions_check_status;
`bank`→bank_account_status;
`risk`→review_status,risk_score.
The `/api/compliance/objects` record is the union of these. In this dataset the detail
endpoints and the object snapshot AGREE — but treat the **detail endpoints as authoritative**
if they ever differ (the object table is the candidate for a "stale snapshot"). Always pull
the live record; do not trust a `review_status` of "approved" as a release signal — re-check
the underlying evidence (bank/screening/license/risk/tax) yourself.

---

## 1. ENUM VALUE SETS (observed in live data — memorize these)

- claim.status: `approved`, `submitted`, `needs_receipt`, `paid`, `rejected`
- bill.status: `draft`, `approved`, `scheduled`, `paid`, `void`
- payment.status: `scheduled`, `processing`, `cleared`  (**only `cleared` = money actually out**)
- vendor.status: `active`, `inactive`, `on_hold`
- compliance.bank_account_status: `verified`, `not_verified`, `name_mismatch`, `closed`
- compliance.pep_status: `none`, `possible_pep`, `confirmed_pep`, `not_run`
- compliance.sanctions_check_status: `clear`, `possible_match`, `confirmed_match`, `not_run`
- compliance.review_status: `not_started`, `in_review`, `awaiting_information`, `approved`, `escalated`
- close_log.status: `open`, `ready_for_review`, `blocked`, `closed`
- close_log.area: `AP`, `Expense`, `Prepaids`, `GL`, `Compliance`, `Treasury`
- prepaid.recognition_method: `straight_line`; prepaid.data_quality_flags seen:
  `rounded_amount`, `missing_contract_dates`, `manual_override`, `duplicate_invoice_number`
- tax_id canonical format: `TIN` + exactly 6 digits (e.g. `TIN615593`). Anything else
  (letters in the numeric part, e.g. `TIN12X899`) is **structurally invalid**.

---

## 2. REIMBURSEMENT-to-AP CLOSE  (families 1 & 4)

Goal: split a batch of claim IDs into payable / blocked / paid (or
eligible / not_ready), compute an AP open-balance, and pick a batch status.

### Per-claim decision algorithm (apply to EACH candidate claim)
1. **Pull the live claim** `/api/claims?claim_id=`. If `status` is `rejected`,
   `needs_receipt`, or `submitted` → the expense case is not approved → **blocked /
   not_ready** (reason `block_unapproved_claim`). Do this even if a snapshot says "approved"
   or "paid" — the snapshot is stale.
2. **Pull live bills** `/api/ap/bills?claim_id=`. A claim can have several bills; you must
   pick the **valid matching bill**: amount equals claim `amount` (to the cent) AND vendor
   matches claim `vendor_id` when the claim has one. Discard bills that are `void` and bills
   whose amount/vendor don't match.
   - No bill at all → **blocked** (missing AP link / `exclude_amount_or_vendor_mismatch`).
   - Only a `void` bill matches → **blocked** (`ignore_void_bill`).
   - A bill exists but amount or vendor mismatches → **blocked**
     (`exclude_amount_or_vendor_mismatch`). (Snapshots often carry a wrong/old bill_id.)
3. **Pull payments for the matched bill** `/api/ap/payments?bill_id=`.
   - Bill `paid` **and** a payment with status `cleared` for the claim amount →
     **PAID / settled** (reason `replace_with_matched_paid_bill`). Exclude from the open
     payables queue.
   - Bill open (`approved`/`scheduled`) with a payment that is `processing` or `scheduled`
     (NOT cleared) → **PAYABLE / eligible** but flagged in-flight
     (reason `mark_in_flight_payment`). It still counts as an OPEN payable.
   - Bill open with no payment → **PAYABLE** (reason `current_snapshot_ok`). Open balance =
     bill amount.

### CRITICAL distinctions (the classic mistakes)
- **`cleared` is the only payment status that settles a claim.** `processing`/`scheduled`
  payments do NOT make a claim "paid"; the claim stays an open payable.
- **The `/api/ap/aging` balance can read 0.00 for a bill that is NOT settled**, because aging
  computes `balance = amount − sum(ALL payments)` clamped ≥0 and counts `processing` payments.
  So aging-balance==0 ≠ paid. For "is it paid?" you must check **payment.status == cleared**;
  use aging only for *magnitude* of an open balance, then re-derive settlement from payment
  status. (Example seen: a scheduled bill with a `processing` payment shows aging balance 0.0
  but is still an open payable.)
- **Open-balance total includes payable claims only** — never include paid or blocked claims.
- Keep "reimbursement-case issues" (bad/unapproved claim) distinct from "AP/payment-evidence
  issues" (void bill, mismatch, missing link) when populating reason/CRM fields — templates
  ask you to preserve that distinction.

### Output conventions
- Currency: read the template carefully. Some templates say **USD cents (integer)**
  (family 1: "Use USD cents for currency totals"); others say **USD with 2 decimals**
  (family 4). Match the unit the template states, exactly.
- All claim-id lists sorted **ascending by claim_id** (string sort).
- `reviewed_claim_count` = number of IDs in the requested batch (count of candidates, not of
  any subset).
- Batch status enums:
  - family 1: `blocked` if ANY item blocked; else `open_payables` if any valid unpaid AP
    reimbursement bill remains; else `ready_to_close`.
  - family 4: `blocked` if any candidate is not-ready due to a hard problem; else
    `needs_ap_refresh` if the live data diverges from the snapshot (stale rows needing
    correction) but items are otherwise fine; else `ready_to_send`.
- `stale_snapshot_corrections` (family 4) — pick ONE enum per claim by the *true* live state:
  `current_snapshot_ok` (live agrees, payable) · `mark_in_flight_payment` (payment
  processing/scheduled, not cleared) · `replace_with_matched_paid_bill` (settled via a
  different correctly-matched paid+cleared bill) · `exclude_amount_or_vendor_mismatch`
  (linked bill amount/vendor wrong, or no link) · `ignore_void_bill` (matched bill is void) ·
  `block_unapproved_claim` (claim not approved).
- `close_log_required` (family 4): consult `/api/close/logs?area=Expense` (and `area=AP`).
  Treat logs with status `open`/`blocked`/`ready_for_review` in the relevant period as
  unresolved. If unresolved Expense/AP close items exist that gate the batch, set
  `required=true` and list those `log_id`s (ascending); otherwise `required=false, ids=[]`.

---

## 3. VENDOR ONBOARDING / COMPLIANCE GATING  (family 2)

Goal: per-business decision (`approve` / `awaiting_information` / `escalate`), a
`reportable_ubo_counts` map, `hard_stop_flags` per business, `follow_up_business_ids`, and
`overall_release_ready`.

### Hard-stop flags — exact derivation (flag name ← condition)
- `bank_closed` ← bank_account_status == `closed`
- `bank_name_mismatch` ← bank_account_status == `name_mismatch`
- `confirmed_pep` ← pep_status == `confirmed_pep`
- `expired_license` ← `license_expiry` < as_of_date (string/date compare; use the batch
  `as_of_date`, e.g. payload `as_of_date` or review date)
- `missing_required_documents` ← `missing_fields` is non-empty (e.g. contains `license`,
  `beneficial_owner_id`)
- `sanctions_confirmed` ← sanctions_check_status == `confirmed_match`
- `screening_not_run` ← sanctions_check_status == `not_run` (screening not performed)
- `shell_company_suspected` ← shell_company_suspected == true
- `vendor_on_hold` ← the linked vendor's `/api/vendors` status == `on_hold`
  (join via compliance `vendor_id`; do NOT infer from compliance alone)

Per-business `hard_stop_flags` = the list of all conditions that fire, **sorted
alphabetically by enum value**; empty list `[]` when none apply.

### Decision mapping (per business)
- ANY hard-stop flag fires → **`escalate`** (cannot be released; a hard stop is a block).
- No hard stop, but evidence is incomplete/in-progress (e.g. review_status
  `awaiting_information`/`in_review`/`not_started`, `possible_pep`, `possible_match`,
  `not_verified` bank) → **`awaiting_information`** (needs follow-up before release).
- Clean: bank `verified`, screening run & `clear`, no PEP/sanctions hit, license current,
  no missing fields, vendor not on hold → **`approve`**.
- `follow_up_business_ids` = every business whose decision is NOT `approve` (i.e. escalate +
  awaiting_information), ascending by business_id.
- `overall_release_ready` = true ONLY if EVERY listed business is `approve`.

### reportable_ubo_counts — the UBO reporting threshold
- Threshold is **ownership_pct ≥ 25%** (inclusive). 24% is deliberately below; 25% qualifies.
  (The data is salted with 24 vs 25 values precisely to test this boundary.)
- Count **unique beneficial-owner NAMES** at/above 25%. The `ubo_list` contains duplicate
  rows and split stakes for the same person — **dedupe by `name`**, and a person qualifies if
  ANY of their rows is ≥25% (equivalently, if their max single-row pct ≥25%). Do not sum
  stakes across rows unless a task explicitly says to; the observed rule is per-row max with
  name dedupe. Return whole-number counts, key by business_id for every listed business.

### Output conventions
- `per_business` list ascending by business_id; each item `{business_id, decision}` (these
  required keys; respect any `additionalProperties:false`).
- `reportable_ubo_counts` / `hard_stop_flags` are objects keyed by ALL listed business_ids.
- Emit keys in the template's `top_level_order` when one is given.

---

## 4. PREPAID / GL RECONCILIATION  (family 3)

Goal: for a scoped set of prepaid invoice IDs and scoped accounts (e.g. 1250, 1251) and a
close period (e.g. 2025-03), produce account rollups, GL variances, flags, and exception lists.

### Data
- Each prepaid invoice: `account`, `original_amount`, `monthly_amortization`, `service_start`,
  `service_end`, `recognition_method` (=`straight_line`), `data_quality_flags`.
- GL ending balances: `/api/prepaids/gl-balances`, one row per (account, period). Use the row
  for the **scoped account AND the close period** (e.g. account 1250, period 2025-03).

### Straight-line amortization (per invoice, through the close month inclusive)
1. Calendar term = inclusive whole months from `service_start` month to `service_end` month.
2. Months recognized through close = inclusive months from start month to the close month,
   clamped to `[0, term]`.
3. `march_amortization` (current-period) = `monthly_amortization` if the close month is within
   `[start, end]`, else 0.
4. `cumulative_amortization_through_<month>` = `monthly_amortization × months_recognized`,
   clamped to not exceed `original_amount`.
5. `ending_balance` = `original_amount − cumulative` (≈0 once fully amortized at term end).
6. Round every currency value to **2 decimals**.

### Data-quality / term exceptions (the judgment call)
- A clean invoice satisfies `monthly_amortization × calendar_term ≈ original_amount`
  (implied term = original/monthly equals the date-derived term).
- An invoice is a **default/missing-term exception** when the schedule is internally
  inconsistent — the implied term (`original_amount / monthly_amortization`) does not match
  the calendar term from the contract dates, OR it carries `missing_contract_dates`
  (or otherwise lacks reliable term data). These get `default_missing_term_flag = true` and
  belong in `default_missing_term_invoice_ids`. (`rounded_amount` alone, with a consistent
  term, is NOT a term exception.)
- `exception_flag` per invoice → true when the invoice has a default/missing-term problem or
  any other data-quality issue that makes its schedule unreliable. Collect these into
  `exception_invoice_ids`.
- Be explicit and consistent in HOW you amortize term-mismatched invoices; this is the main
  source of uncertainty. A defensible convention: recognize at the recorded
  `monthly_amortization` but never let cumulative exceed `original_amount`.

### Account rollup + status
- For each scoped account: `selected_invoice_count`, and totals (sum over that account's
  scoped invoices) of original_amount, march_amortization, cumulative_through_month,
  schedule_ending_balance.
- `variance_amount` = `schedule_ending_balance − gl_ending_balance`.
- `variance_flag` = `abs(variance_amount) > variance_threshold_abs` (e.g. 100.0 from scope).
- `has_default_missing_term_flag` = true if any invoice in that account is a term exception.
- `account_status` enum:
  `reconciled` (no variance flag, no term exceptions) ·
  `variance_review` (variance over threshold but data otherwise clean) ·
  `requires_reconciliation` (term/data-quality exceptions present, i.e. the schedule itself
  is unreliable — the stronger problem).

### Output conventions
- `selected_invoice_ids` and `invoice_results` follow the SAME order as the scope payload.
- `default_missing_term_invoice_ids` and `exception_invoice_ids` sorted **ascending by id**.
- `account_rollup` keyed by account string ("1250","1251"); include `account_name` from the
  GL row (e.g. "Prepaid Expenses", "Prepaid Insurance"). 2-decimal precision everywhere.

---

## 5. AP PAYMENT-RELEASE AFTER ACCOUNT CHANGE  (family 5)

Goal: per business `decision` (`release`/`hold`/`escalate`) plus several diagnostic ID lists.
This combines compliance gating (family 3 rules) with vendor/bank verification of the
account-change request.

### Per-business evaluation (use as_of/review date from payload, e.g. 2025-06-01)
Pull `/api/compliance/objects` (+ detail endpoints) AND `/api/vendors?vendor_id=` for the
business's vendor. Build the diagnostic lists:
- `bank_mismatch_ids` ← bank_account_status == `name_mismatch`.
- `invalid_tax_ids` ← tax_id not matching `TIN`+6 digits (structurally invalid, e.g.
  `TIN12X899`). (Also watch vendor↔compliance tax_id mismatches as a review trigger, but the
  field as defined keys on structural validity.)
- `expired_license_ids` ← `license_expiry` < as_of_date.
- `risk_score_override_flags` ← `risk_score ≥ 70`.
- `review_queue_ids` ← anything needing compliance/AP review before release: bank not
  `verified`, screening `not_run`/`possible_match`/`confirmed_match`, pep `possible_pep`/
  `confirmed_pep`, missing fields, vendor `on_hold`/`inactive`, review_status not approved,
  or an unverified requested bank-change.
- Optional bank-change check: the ticket's `requested_bank_last4` vs vendor
  `bank_account_last4` — equal = consistent; differing/unverifiable = a review trigger.

### Decision mapping
- `escalate` ← a confirmed hard stop: bank `closed`, `confirmed_match` sanctions,
  `confirmed_pep`, invalid tax id, expired license, vendor `on_hold`, or multiple stacked
  red flags. (A change requested onto a closed/mismatched bank is an escalation, not a quiet
  hold.)
- `hold` ← a recoverable gating issue: in_review / not_started / awaiting info, bank
  `name_mismatch` to re-verify, `possible_*`, unverified bank change, or risk ≥70 without a
  hard confirmed stop — release is paused pending evidence.
- `release` ← clean: bank `verified`, screening `clear` & run, no PEP, license current, valid
  tax, vendor `active`, risk below override, and the requested bank change verified.

### Output conventions
- Echo required literal fields exactly (`task_id`, `batch_id`, `as_of_date`).
- `decisions` is an object keyed by business_id over ALL target ids.
- Every ID list sorted **ascending by business_id**. Respect `additional_properties_allowed:
  false` — emit only the template's keys.

---

## 6. UNIVERSAL CHECKLIST (apply to every task)

1. Use the runner base URL; ignore any URL inside prompt/payload.
2. Re-derive every decision from LIVE API records; treat any snapshot/CSV/"current status"
   /`review_status` as context, never as truth.
3. Pull every candidate id individually with exact-match filters; verify counts.
4. Settlement = payment.status `cleared` only; aging balance==0 does not prove settlement.
5. Match a claim to its bill by amount AND vendor; drop void/mismatched bills.
6. Compliance hard stops force escalate/block; "approved" review_status is not a release
   green-light by itself.
7. UBO reporting threshold = ≥25%, dedupe by owner name.
8. Tax-id valid = `TIN`+6 digits.
9. Prepaid: straight-line through close month, cumulative clamped to original; term
   exceptions = implied term ≠ date term or missing contract dates.
10. Honor the template EXACTLY: required keys, key order, enum value sets, sort order
    (ascending by id), numeric precision, the stated currency unit (cents vs 2-decimal USD),
    and `additionalProperties` rules. Return JSON only — no prose.
