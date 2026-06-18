---
name: erp-finance-close-tasks
description: >-
  Executable playbook for the shared ERP finance JSON API (claims, AP bills, payments,
  vendors, compliance, prepaids, GL, close logs). Use this whenever a task asks you to
  make a finance close/release decision from this API and return a JSON answer matching a
  provided answer_template.json — including reimbursement-to-AP close, expense-claim batch
  triage, vendor onboarding / intake compliance release, prepaid-to-GL amortization
  reconciliation, stale AP snapshot reconciliation, AP payment release after vendor
  account-change events, and month-end exception reporting. Trigger this skill even when
  the prompt only mentions "claim IDs", "business IDs", "AP batch", "prepaid close",
  "onboarding decision", "release posture", "aging", or "answer_template" without naming
  the workflow explicitly. It encodes the exact field definitions, decision enums, and
  rounding/sorting rules these graders check.
---

# ERP Finance Close & Release Tasks

You are answering finance-operations tasks against a shared ERP JSON API. Each task gives you
a small batch (claim IDs or business IDs), a local payload, and an `answer_template.json`. Your
job is to fetch the **live** records, apply the correct business rules, and emit one JSON object
matching the template exactly. Graders check exact enum values, list membership, ascending
sorting, and 2-decimal rounding — so precision matters more than prose.

## 0. Golden rules (apply to every task)

- **The live API is the system of record.** Local payloads (CSV snapshots, batch JSON, "current
  review status") are *context only*. If the prompt cites a base URL that differs from the one in
  your environment access notes, ignore the prompt's URL and use the environment's. Never read
  server source or local env data files; only HTTP GET the API.
- **Pagination:** list endpoints return `{count,total,offset,limit,data:[...]}`. Read `data`.
  Always pass `limit=500` (the max) and page with `offset` until you have all `total` rows.
  Default limit is only 100, so a naive call silently truncates.
- **Money:** round every currency value to 2 decimals. Some templates say "USD cents" (integers);
  read the template's `unit`/`precision` and match it (cents = round(dollars*100) as integer).
- **Sorting:** every list of IDs is sorted **ascending by ID string** unless the template says
  otherwise (e.g. prepaid `selected_invoice_ids` keep the scope order). Object keys for ID-keyed
  maps are also typically ascending.
- **Output only the JSON object** the template defines, with exactly its keys. If the template
  lists `required_top_level_keys` or `top_level_order`, honor it and add nothing extra.
- **Identify the task type** from the template's keys, then follow the matching SOP below. The six
  recognizable shapes:
  - `payable_claim_ids/paid_claim_ids/blocked_claim_ids/batch_status` → §2 reimbursement close
  - `per_business/reportable_ubo_counts/hard_stop_flags/overall_release_ready` → §3 onboarding
  - `account_rollup/invoice_results/march_amortization...` → §4 prepaid close
  - `eligible_claim_ids/stale_snapshot_corrections/close_log_required` → §5 stale AP snapshot
  - `decisions(release/hold/escalate)/bank_mismatch_ids/risk_score_override_flags` → §6 AP release

## 1. The API surface (base URL from environment access notes)

| Endpoint | Holds | Key fields |
|---|---|---|
| `/api/claims?limit=500` or `/api/claims/{id}` | expense claims | `claim_id, status, amount, vendor_id, receipt_status, policy_flags, approved_date` |
| `/api/ap/bills?limit=500` | AP bills | `bill_id, claim_id, amount, vendor_id, status, account, due_date` |
| `/api/ap/payments?limit=500` | payments | `payment_id, bill_id, amount, status, vendor_id, payment_date` |
| `/api/ap/aging?as_of=YYYY-MM-DD` | per-bill aging | `bill_id, amount, paid_amount, balance, status` |
| `/api/vendors?limit=500` | vendor master | `vendor_id, status, tax_id, bank_account_last4, payment_terms` |
| `/api/compliance/profile/{business_id}` | KYC profile | `vendor_id, tax_id, missing_fields[]` |
| `/api/compliance/ownership/{business_id}` | UBOs | `ubo_list[{name,ownership_pct}], shell_company_suspected, ownership_layer_count` |
| `/api/compliance/registry/{business_id}` | registry | `license_expiry, tax_id, registration_number` |
| `/api/compliance/screening/{business_id}` | screening | `pep_status, sanctions_check_status` |
| `/api/compliance/bank/{business_id}` | bank | `bank_account_status` |
| `/api/compliance/risk/{business_id}` | risk | `risk_score, review_status` |
| `/api/prepaids/invoices?limit=500` | prepaid schedule | `prepaid_invoice_id, account, original_amount, monthly_amortization, service_start, service_end, recognition_method, data_quality_flags[]` |
| `/api/prepaids/gl-balances?limit=500` | GL ending balances | `account, period, entity, account_name, ending_balance` |
| `/api/close/logs?limit=500` | close-log entries | `log_id, area, period, related_account, message, status` |

**Critical aging caveat:** `/api/ap/aging` computes `balance = amount − paid_amount`, but its
`paid_amount` includes **scheduled and processing payments**, not just cleared ones. The business
"open AP balance" you must report counts **cleared payments only**. So do **not** trust the aging
`balance` directly for payable/open figures — recompute it (see §2). Aging is still handy for a
quick read of `paid_amount` totals and for spotting which bills have any payment activity.

**Duplicate IDs exist.** The same `bill_id` can appear on two different bill rows (one unrelated,
one the real reimbursement bill linked to the claim). Always match on the row whose `claim_id`,
`amount`, and `vendor_id` line up with the claim — don't grab the first row with that ID.

A helper script that fetches and paginates everything is in `scripts/fetch.py` (use it or curl).

## 2. Reimbursement-to-AP close (payable / paid / blocked)

For each requested `claim_id`: pull the claim, then find its linked AP bill(s) via
`/api/ap/bills` filtered/scanned on `claim_id`, then the bill's payments via `/api/ap/payments`
on `bill_id`. Classify the claim into exactly one bucket.

Define a bill as a **valid matched reimbursement bill** for a claim when ALL hold:
- `bill.claim_id == claim.claim_id`
- `bill.amount == claim.amount` (to the cent)
- `bill.vendor_id == claim.vendor_id` (and the claim's `vendor_id` is not null)
- `bill.status != "void"`

Compute the bill's **cleared total** = sum of payments on that bill with `status == "cleared"`.
**Open balance** = `bill.amount − cleared total` (round 2 dp).

Buckets:
- **paid** — claim `status == "paid"` AND a valid matched bill exists whose cleared total equals
  the bill amount (open balance 0). These are already settled; they leave the open queue.
- **payable** — claim `status == "approved"`, has a valid matched bill, and open balance > 0
  (i.e. payment is missing or only scheduled/processing, not cleared). These stay in the batch.
- **blocked** — anything else: claim not approved (e.g. `needs_receipt`, `draft`), no linked bill,
  bill is `void`, or the linked bill's amount/vendor doesn't match the claim. Vendor-null claims
  whose bill cannot be validated land here too.

Assemble the template fields:
- `payable_claim_ids` = payable bucket; `paid_claim_ids` = paid; `blocked_claim_ids` = blocked.
- `ap_open_balance_total` = sum of open balances of **payable claims only** (not paid, not blocked).
- `crm_required_claim_ids` = the blocked claims that need owner cleanup / AP-link remediation
  (in practice = the blocked set, since each needs a fix before release).
- `batch_status`: `blocked` if any claim is blocked; else `open_payables` if any payable remain;
  else `ready_to_close`.
- `reviewed_claim_count` = number of requested IDs.
- Sort every ID list ascending. Read the template's `unit` — if "cents", convert.

*Illustrative:* an approved travel claim whose only payment is still `processing` (not cleared)
is **payable** with open balance = full amount; a claim marked `paid` with a cleared payment equal
to a vendor/amount-matched bill is **paid**; a claim whose linked bill has a wildly different
amount and vendor is **blocked**.

## 3. Vendor onboarding / intake compliance release

For each `business_id`, pull all six compliance endpoints plus the vendor record (via
`profile.vendor_id` → `/api/vendors?vendor_id=...`). Compute hard-stop flags, then a decision.

**`hard_stop_flags`** (list, alphabetical, empty if none) — raise each that applies:
- `bank_closed` — `bank.bank_account_status == "closed"`
- `bank_name_mismatch` — `bank.bank_account_status == "name_mismatch"`
- `confirmed_pep` — `screening.pep_status == "confirmed_pep"`
- `sanctions_confirmed` — `screening.sanctions_check_status` indicates a confirmed hit
- `screening_not_run` — `screening.sanctions_check_status == "not_run"` OR `pep_status == "not_run"`
- `expired_license` — license is expired **by month granularity**: `(license_expiry.year,
  license_expiry.month) < (as_of.year, as_of.month)`. Use the batch `as_of_date`. **But** if
  `license` is in `profile.missing_fields`, raise `missing_required_documents` instead (there is
  no license to expire). Month granularity matters: a license expiring on the 17th of the as_of
  month is NOT yet expired for a month-end as_of.
- `missing_required_documents` — `profile.missing_fields` is non-empty
- `shell_company_suspected` — `ownership.shell_company_suspected == true`
- `vendor_on_hold` — vendor master `status == "on_hold"`

**`decision`** enum `approve | awaiting_information | escalate`:
- `escalate` — any **severe** hard stop present: `confirmed_pep`, `sanctions_confirmed`,
  `shell_company_suspected`, `vendor_on_hold`, `bank_closed`, or `expired_license`.
- `awaiting_information` — only **fixable/info** hard stops present:
  `missing_required_documents`, `screening_not_run`, `bank_name_mismatch`.
- `approve` — no hard stops at all.

**`reportable_ubo_counts`** — per business, count **unique beneficial-owner names** whose
`ownership_pct >= 25` (the reporting threshold). De-duplicate by name (the same name can appear
multiple times); count distinct names, not rows. A name below 25% does not count.

**Summary fields:**
- `per_business` — one `{business_id, decision}` per business, ascending by business_id.
- `follow_up_business_ids` — every business whose decision is not `approve`, ascending.
- `overall_release_ready` — `true` only if every business decision is `approve`.

## 4. Prepaid-to-GL close reconciliation

Scope: the invoice IDs in the payload, the named accounts (e.g. 1250/1251), and the close period
(e.g. 2025-03 = March). Pull invoices from `/api/prepaids/invoices` and GL ending balances from
`/api/prepaids/gl-balances` (filter by `account`, `period`, and `entity`).

Per invoice, with straight-line monthly amortization (`monthly_amortization` = ma,
`original_amount` = orig):
- `term_months` = `(service_end.y - service_start.y)*12 + (service_end.m - service_start.m) + 1`.
- `months_through_period` = `(period.y - service_start.y)*12 + (period.m - service_start.m) + 1`.
- `march_amortization` (period amortization) = `ma` if the period falls within
  `[service_start, service_end]` else `0`.
- `cumulative_amortization_through_march` = `min(months_through_period, term_months) * ma`,
  rounded 2 dp. **Do not cap at original_amount** — cumulative is months×ma even if that differs
  from orig by a rounding cent (this is intentional; ending balances of 0.00 or 0.01 are normal).
- `ending_balance` = `round(orig − cumulative, 2)`.
- `default_missing_term_flag` = `"missing_contract_dates"` is in `data_quality_flags`.
- `exception_flag` = `data_quality_flags` is **non-empty** (ANY flag, e.g. `rounded_amount`,
  `missing_contract_dates`, etc.). Empty flags ⇒ no exception.

`account_rollup` per account (key = account number as string):
- `account_name` from the GL row; `selected_invoice_count` = scoped invoices on that account.
- `original_amount_total`, `march_amortization_total`, `cumulative_amortization_through_march`,
  `schedule_ending_balance` = **sums of the per-invoice (already-rounded) values**, then round.
- `gl_ending_balance` = the GL row's `ending_balance` for that account/period/entity.
- `variance_amount` = `schedule_ending_balance − gl_ending_balance` (round 2 dp).
- `variance_flag` = `abs(variance_amount) > variance_threshold_abs` (default threshold 100.0 from
  the payload).
- `has_default_missing_term_flag` = any scoped invoice on that account has the missing-term flag.
- `account_status`: `requires_reconciliation` if `variance_flag` is true (a real GL break);
  `variance_review` for a within-tolerance soft difference needing eyes; `reconciled` if no
  variance and clean. In practice a tripped variance flag dominates → `requires_reconciliation`.

Top-level: `period`, `entity`, `selected_invoice_ids` (in scope order), `invoice_results` (in
scope order), `default_missing_term_invoice_ids` and `exception_invoice_ids` (each ascending).

## 5. Stale AP snapshot reconciliation

A stale CSV/JSON snapshot is provided as context only. Re-derive everything from the live API for
each candidate `claim_id`, then describe how the snapshot must be corrected.

For each claim, find its valid matched bill and cleared total exactly as in §2.
- `ap_balance_by_claim[claim]` = open AP balance = `bill.amount − cleared total`, ignoring stale
  or voided AP rows and amount/vendor-mismatched rows (those contribute 0). A paid/cleared bill ⇒
  0; an approved bill with only an in-flight (scheduled/processing) payment ⇒ full amount.

`stale_snapshot_corrections[claim]` — pick the one enum that explains the snapshot↔live delta:
- `block_unapproved_claim` — live claim status is not approved (e.g. `needs_receipt`).
- `ignore_void_bill` — the linked bill is `void` in live data.
- `exclude_amount_or_vendor_mismatch` — the linked bill's amount or vendor doesn't match the claim.
- `replace_with_matched_paid_bill` — the snapshot pointed at the wrong/old bill; live data has a
  correctly matched **paid** bill that should replace it.
- `mark_in_flight_payment` — a payment exists but is not cleared (scheduled/processing); mark the
  payment as in-flight rather than treating the claim as settled or unpaid.
- `current_snapshot_ok` — snapshot already matches live (rare).

Buckets:
- `eligible_claim_ids` — claims that can stay in the batch: those with a valid matched bill that is
  either a settled/paid match (replace_with_matched_paid_bill) or an in-flight payable
  (mark_in_flight_payment).
- `not_ready_claim_ids` — the rest (unapproved, void, mismatch).

`close_log_required` — when corrections required an AP refresh (in-flight payment or
replace-with-matched-paid-bill present), a close log documenting the AP manual journal entry for
the relevant period is required: set `required=true` and list the matching `close/logs` IDs
(`area == "AP"`, message about a manual journal entry, for the affected period), ascending. If no
such correction is needed, `required=false` with an empty list.

`batch_status`: `blocked` if a candidate is fundamentally unworkable; `needs_ap_refresh` if the
batch is usable but the AP export must be refreshed (corrections like in-flight / replace / exclude
are present); `ready_to_send` if everything already reconciles.

## 6. AP payment release after vendor account changes

For each `business_id` in the batch, pull all six compliance endpoints plus the vendor record, as
of the review/`as_of_date`. Build the list fields, then the decision.

List fields (each ascending by business_id):
- `bank_mismatch_ids` — `bank.bank_account_status == "name_mismatch"`.
- `invalid_tax_ids` — tax_id is malformed or a placeholder: not matching `TIN` + exactly 6 digits
  (e.g. a letter inside like `TIN12X899`), or an obvious sentinel like `TIN999999`. Use the
  compliance `tax_id` (profile/registry).
- `expired_license_ids` — same month-granularity expiry rule as §3, comparing `license_expiry` to
  `as_of_date`; skip businesses whose `license` is in `missing_fields`.
- `risk_score_override_flags` — `risk.risk_score >= 70`.
- `review_queue_ids` — every business whose decision is **not** `release` (needs review first).

`decisions[business_id]` enum `release | hold | escalate`:
- `escalate` — a serious compliance/screening red flag: `confirmed_pep`, confirmed sanctions,
  vendor `on_hold`, OR multiple stacked data-integrity failures (e.g. invalid tax **and** expired
  license together).
- `hold` — a single fixable blocker: bank name_mismatch or closed, expired license, missing docs,
  invalid tax, screening not run, or `risk_score >= 70`.
- `release` — no blockers at all (note: a `risk_score` below 70 and an in-review risk status do
  not by themselves block release).

Echo the required literal fields from the template (`task_id`, `batch_id`, `as_of_date`,
`target_business_ids` ascending). `additional_properties_allowed:false` means emit exactly the
template's keys — nothing more.

## 7. Pre-submit checklist

- Re-derived everything from the **live API**, not the local snapshot/status.
- Paginated to `total` rows; matched bills on claim_id + amount + vendor (handling duplicate IDs).
- Used **cleared payments only** for open balances; did not trust aging `balance` directly.
- Excluded void / mismatched / unapproved items per the task's rules.
- Rounded money to 2 dp (or cents per template); sorted ID lists ascending; kept scope order where
  the template requires it.
- Used the exact enum spellings from the template; emitted only the template's keys.
