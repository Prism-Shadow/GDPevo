---
name: erp-finance-close-compliance
description: >-
  Solve task_group_005 ERP finance close and compliance tasks against the shared
  local JSON API. Use this whenever a task involves reimbursement-to-AP close
  triage, vendor onboarding finance-risk release, prepaid-to-GL close
  reconciliation, stale AP snapshot reconciliation, AP payment release after
  vendor account changes, or month-end AP/compliance exception reporting — i.e.
  anything that reads claims, AP bills, payments, vendors, compliance objects,
  prepaid invoices, GL balances, or close logs and returns a JSON answer matching
  an answer_template.json. Trigger this skill even when the prompt only mentions
  "close batch", "payable/blocked/paid", "hard stops", "release posture",
  "variance flag", "amortization", "in-flight payment", "void bill", or a
  BUS-/CLM-/AP-/PPD-/VEN- ID, because these tasks have specific, easy-to-miss
  rules that this skill encodes.
---

# ERP Finance Close & Compliance Tasks

These tasks all read from one shared ERP finance JSON API and return a single
JSON object that must conform exactly to a provided `answer_template.json`. The
data is full of traps (mismatched links, void bills, placeholder tax IDs,
in-flight-but-not-cleared payments). The grader checks field values exactly, so
the win comes from applying the precise rules below, not from intuition.

## 0. Universal rules (apply to every task)

**Base URL.** Always `http://127.0.0.1:8029`. Prompts often print a different
base (e.g. `http://127.0.0.1:8005`) — **ignore it**; use 8029. Confirm with
`GET /health`. List responses are wrapped: `{"count","total","offset","limit","data":[...]}`
— read `.data`. Paginate with `limit` (max 500) and `offset` until you have
every row. Object/list endpoints accept exact-match query params by field name.

**Endpoints you will use.** `/claims`, `/api/claims/{id}`; `/bills`,
`/api/ap/bills`; `/payments`, `/api/ap/payments`; `/api/ap/aging?as_of=YYYY-MM-DD`;
`/vendors`; `/compliance/objects` and `/api/compliance/{profile|ownership|registry|screening|bank|risk}/{business_id}`;
`/prepaids/invoices`; `/gl/balances` (a.k.a. `/api/prepaids/gl-balances`);
`/close/logs`.

**`/api/ap/aging` is unreliable for "is it paid" decisions — do NOT trust its
balance.** It computes per-bill balance = amount − (sum of ALL payments
regardless of status), so a bill with only a `scheduled`/`processing` payment
shows balance 0 even though nothing cleared. For any "settled / cleared / open
balance" determination, fetch `/payments` for the bill and check
`payment.status == "cleared"` yourself. Use aging only as a cross-check.

**Currency / units.** The **answer_template field spec wins over the prompt
text.** If the template says `"unit":"USD","precision":2`, return dollars with 2
decimals (e.g. `1842.36`) even when the prompt says "use USD cents." (Train 001:
prompt said cents, template said USD precision 2 — the dollar value `1842.36` was
correct, `184236` was wrong.) Round monetary results to 2 decimals.

**Sorting & shape.** Sort every ID list as the template says (almost always
ascending by the ID string). Emit object keys for every required member, even
when the value is `0`, `0.00`, `[]`, or `false`. When the template sets
`additional_properties_allowed: false`, output *exactly* the listed top-level
keys — no more, no less. Echo required literal values (`task_id`, `batch_id`,
`as_of_date`, `period`, `entity`) verbatim from the template/payload.

**Validating a claim↔bill link (used by AP tasks).** A bill carrying
`claim_id == X` is NOT automatically a valid link. Accept a link only if the bill
**amount matches the claim amount AND the bill vendor matches the claim vendor**,
and the bill is not `void`. `bill_id` is not unique (e.g. `AP-2025-0068` appears
twice for different vendors) — match on the full record, not the id. A claim can
have several linked bills; pick the one that truly matches and ignore the rest.

---

## 1. Reimbursement-to-AP close batch triage

Template fields: `payable_claim_ids`, `blocked_claim_ids`, `paid_claim_ids`,
`ap_open_balance_total`, `crm_required_claim_ids`, `batch_status`,
`reviewed_claim_count`.

Per claim in the batch, find its valid matched bill (Section 0 link rule), then
classify:

- **paid** — claim is settled: a matched bill with status `paid` AND a payment
  with `status=="cleared"` for the claim amount. (`paid_claim_ids`)
- **payable** — approved claim with a valid open AP reimbursement bill (matched
  amount+vendor, not void), but no cleared payment yet (payment missing or only
  `scheduled`/`processing`). Stays in the queue. (`payable_claim_ids`)
- **blocked** — anything else: no linked bill at all, linked bill is `void`, or
  amount/vendor mismatch, or the claim itself is unapproved. These need owner
  cleanup. Put the SAME ids in both `blocked_claim_ids` and
  `crm_required_claim_ids`.

`ap_open_balance_total` = sum of open balances of **payable** claims' bills only
(bill amount − cleared payments; for payable claims that's the full bill amount).
Exclude paid and blocked claims. Report in template units (dollars, 2 dp).

`batch_status`: `blocked` if any item is blocked; else `open_payables` if any
payable bills remain; else `ready_to_close`.

`reviewed_claim_count` = number of claim IDs requested.

---

## 2. Vendor onboarding finance-risk release

Template fields: `per_business[{business_id,decision}]`, `reportable_ubo_counts`,
`hard_stop_flags`, `follow_up_business_ids`, `overall_release_ready`. Read each
business from `/compliance/objects` (bulk; consistent with the per-business
sub-endpoints). Use the batch's `as_of_date` for date comparisons.

**hard_stop_flags** (per business, alphabetical, empty list if none). Build each
flag from the compliance object:

| flag | condition |
|---|---|
| `bank_closed` | `bank_account_status == "closed"` |
| `bank_name_mismatch` | `bank_account_status == "name_mismatch"` |
| `confirmed_pep` | `pep_status == "confirmed_pep"` |
| `expired_license` | license expired beyond grace — see below |
| `missing_required_documents` | `missing_fields` is non-empty |
| `sanctions_confirmed` | `sanctions_check_status == "confirmed_match"` |
| `screening_not_run` | `sanctions_check_status == "not_run"` OR `pep_status == "not_run"` |
| `shell_company_suspected` | `shell_company_suspected == true` |
| `vendor_on_hold` | the linked vendor's `status == "on_hold"` (fetch `/vendors`) |

**PITFALL — `expired_license` here is NOT a plain `license_expiry < as_of`
comparison; it uses a ~90-day grace period.** A license that lapsed only a few
weeks/months ago is treated as a curable lapse, not a hard stop. The flag fires
only when expired by MORE than ~90 days. (Train 002 at as_of 2025-05-31: a license
that expired 14 days and 76 days earlier did NOT get the flag; ones expired 108
and 150 days earlier DID. The boundary sits between 76 and 90 days — use a 90-day
grace.) This is the opposite of the Section 5 release task, which uses a plain
comparison for its separate `expired_license_ids` list. Do not copy that rule
here. Still read `license_expiry` for every business — just apply the grace.

**decision — three tiers based on flag SEVERITY** (release-control, NOT a copy of
`review_status`). Partition the hard stops:
- CURABLE flags: `missing_required_documents`, `screening_not_run`.
- SEVERE flags: everything else (`bank_closed`, `bank_name_mismatch`,
  `confirmed_pep`, `expired_license`, `sanctions_confirmed`,
  `shell_company_suspected`, `vendor_on_hold`).

Then:
- `approve` — **zero** hard_stop_flags. An incomplete `review_status` (e.g.
  `in_review`) does NOT block approval if there are no hard stops.
- `escalate` — at least one **SEVERE** flag is present.
- `awaiting_information` — has flags, but **only CURABLE** ones (missing docs
  and/or screening not run) and no severe flag. (Train 002: a business with only
  `missing_required_documents` + `screening_not_run` was `awaiting_information`,
  not escalate.)

PITFALL: do not blanket-escalate on "any flag." Missing docs / screening-not-run
alone are awaiting_information. Conversely don't downgrade a severe flag.

**reportable_ubo_counts** = count of **unique owner names** in `ubo_list` with
`ownership_pct >= 25`. De-duplicate by name (the same name can appear twice; it
counts once if any of its entries reaches 25%). A 24% entry does not qualify.

**follow_up_business_ids** = every non-`approve` business (ascending).
**overall_release_ready** = `true` only if every business is releasable (all
`approve`); otherwise `false`.

---

## 3. Prepaid-to-GL close reconciliation

Scope is given in the payload (`entity`, `close_period` e.g. `2025-03`, the
account list, the selected `prepaid_invoice_id` list, `variance_threshold_abs`).
Pull invoices from `/prepaids/invoices` and account ending balances from
`/gl/balances` (filter by account + period + entity).

**Straight-line amortization (per invoice), confirmed exact:**
- `march_amortization` (the close-month amount) = the invoice's
  `monthly_amortization` for every invoice active in the close month (one month).
- `cumulative_amortization_through_march` = `monthly_amortization × N`, where
  `N` = number of calendar months from the `service_start` month through the
  close month **inclusive** (Jan-start, March close → N=3; March-start → N=1).
  Cap at `original_amount`.
- `ending_balance` = `original_amount − cumulative` (round 2 dp). Do not force to
  0; tiny artifacts like `0.01` are real and expected for `rounded_amount`
  invoices (monthly × term differs from original by pennies).

**Flags (per invoice):**
- `default_missing_term_flag` = `data_quality_flags` contains
  `missing_contract_dates`.
- `exception_flag` = **any** `data_quality_flags` entry is present — including the
  benign `rounded_amount`. (Broad reading is correct: don't filter to "serious"
  flags.)

**Account rollup** (per account): sum the selected invoices' originals, march
amort, cumulative, and ending. `gl_ending_balance` = GL period ending for that
account+entity. `variance_amount = schedule_ending_balance − gl_ending_balance`
(this sign/order is fixed by the template). `variance_flag = |variance_amount| > variance_threshold_abs`.
Large variances are normal — the scoped invoices are a subset of the full GL
account, so expect big gaps. `has_default_missing_term_flag` = any selected
invoice on that account has the default/missing-term flag.

**account_status (order matters):**
1. `requires_reconciliation` if `has_default_missing_term_flag` is true;
2. else `variance_review` if `variance_flag` is true;
3. else `reconciled`.

PITFALL: An account can have a huge variance but NO missing-term flag → that is
`variance_review`, not `requires_reconciliation`. (Train 003: account 1251 had a
~79k variance, no missing-term flag → `variance_review`.) Don't conflate "big
variance" with "requires reconciliation."

`default_missing_term_invoice_ids` / `exception_invoice_ids` = the invoices whose
respective flag is true, ascending.

---

## 4. Stale AP snapshot reconciliation

A stale CSV snapshot is **context only** — the live API is the system of record.
Template fields: `eligible_claim_ids`, `not_ready_claim_ids`, `ap_balance_by_claim`,
`stale_snapshot_corrections`, `close_log_required`, `batch_status`.

For each candidate claim, compare the snapshot row to the current ERP state and
pick the correction enum, then decide eligibility:

| correction enum | when |
|---|---|
| `current_snapshot_ok` | live matches snapshot, nothing to fix |
| `mark_in_flight_payment` | a valid matched bill now has a `scheduled`/`processing` (not cleared) payment the snapshot didn't show |
| `replace_with_matched_paid_bill` | snapshot pointed at the wrong bill; a correctly matched **paid+cleared** bill exists |
| `exclude_amount_or_vendor_mismatch` | the linked bill's amount or vendor doesn't match the claim |
| `ignore_void_bill` | the linked bill is `void` |
| `block_unapproved_claim` | the claim status is unapproved (e.g. `needs_receipt`) |

**Eligibility — key correction:** `eligible_claim_ids` = claims that are
**correctly reconciled against current ERP state**, which INCLUDES already-settled
paid claims, not just ones with an open balance. So a payable claim
(`mark_in_flight_payment`) AND a fully-paid claim (`replace_with_matched_paid_bill`,
cleared) are BOTH eligible to stay in the batch. `not_ready_claim_ids` = mismatch,
void, or unapproved cases. (Train 004: the paid FIN-042 was *eligible*, not
not_ready — I wrongly excluded it.)

`ap_balance_by_claim` (key for every candidate): open AP balance = matched bill
amount − cleared payments, ignoring stale/void rows. In-flight (not cleared) →
full amount still open; paid+cleared → `0.00`; void/mismatch/unapproved → `0.00`.

`close_log_required`: corrections were applied, so a documented close entry is
required → `required: true`. For `ids`, select from `/close/logs` the **AP-area
close log for the latest close period** (it documents the corrective journal
entry for this cleanup). PITFALL: do NOT pick "the only open/ready_for_review AP
log" — the right one is the most-recent-period AP log even if its status is
`closed`. (Train 004: correct id was the period-2025-04 AP log `CLOSE-2025-04-009`
with message "Manual journal entry posted", not the older ready_for_review one.)

`batch_status`: `needs_ap_refresh` when stale-AP corrections are needed but all
are identifiable (typical); `blocked` only if something can't be resolved at all;
`ready_to_send` if everything already matches.

---

## 5. AP payment release after vendor account changes

Payload lists account-change tickets per business and a `review_date`. Template
(`additional_properties_allowed: false`) fields: `task_id`, `batch_id`,
`as_of_date`, `target_business_ids`, `decisions`, `bank_mismatch_ids`,
`invalid_tax_ids`, `expired_license_ids`, `review_queue_ids`,
`risk_score_override_flags`. Echo `task_id`/`batch_id`/`as_of_date` literals;
`target_business_ids` ascending.

Pull each business from `/compliance/objects`. Component lists:
- `bank_mismatch_ids` = `bank_account_status == "name_mismatch"`.
- `expired_license_ids` = **plain** `license_expiry < as_of_date` (the template
  says `comparison_date: as_of_date`). NOTE: unlike the Section 2 onboarding
  hard-stop, this list uses a strict comparison with NO grace period — a license
  that lapsed even a few days ago belongs here. (Train 005: a license expired 9
  days before as_of was included.)
- `risk_score_override_flags` = `risk_score >= 70`.
- `invalid_tax_ids` = a `tax_id` that fails integrity. Flag it if **any** of:
  (a) bad format — not `TIN` followed by exactly 6 digits (e.g. `TIN12X899`);
  (b) placeholder — all identical digits (e.g. `TIN999999`, `TIN111111`);
  (c) it differs from the vendor's `tax_id` on file. PITFALL: I previously
  treated the all-9s `TIN999999` as valid because its format was fine — it is
  invalid (placeholder + vendor mismatch). Check placeholders and vendor match,
  not just the regex.

**decisions** (`release` / `hold` / `escalate`) — note this uses a DIFFERENT
severity tier than Section 2 onboarding:
- `escalate` — identity/integrity red flags: a PEP flag (`confirmed_pep` or
  `possible_pep`) OR an invalid `tax_id`.
- `hold` — has curable issues (bank `name_mismatch` or `closed`, missing docs,
  expired license, screening `not_run`, `risk_score >= 70`) but NO escalation
  trigger above.
- `release` — a fully clean profile: no PEP, no invalid tax, no bank issue, no
  expired license, no missing docs, no screening gap, risk < 70. An incomplete
  `review_status` (`in_review`) does NOT block release.

PITFALL: do not over-escalate. A closed bank + screening-not-run + expired
license, with no PEP and a valid tax id, is `hold`, not `escalate`. (Train 005:
BUS-...0056 had bank closed + sanctions not_run + expired license + review
escalated, yet the answer was `hold`; and BUS-...0018, clean but `in_review`, was
`release`.)

`review_queue_ids` = every business that is NOT `release` (i.e. all `hold` +
`escalate`), ascending. A released business is not in the queue.

---

## Pre-submit checklist

1. Used base URL 8029; paginated; read `.data`.
2. Decided "paid/cleared/open balance" from `payment.status=="cleared"`, never
   from `/api/ap/aging`.
3. Validated every claim↔bill link by amount AND vendor; excluded `void` bills.
4. Currency in template units (dollars, 2 dp) — template spec beats prompt text.
5. Applied the RIGHT license-expiry rule for the task: onboarding hard-stop uses
   a ~90-day grace; the release task's `expired_license_ids` uses a plain
   comparison. Checked `license_expiry` for every business either way.
6. tax_id validity covers bad format, placeholder, and vendor mismatch.
7. Correct severity tier for the task. Onboarding (Sec 2) is THREE tiers:
   approve / awaiting_information (curable-only: missing docs, screening not run)
   / escalate (any severe flag). Release (Sec 5) is release / hold / escalate
   (escalate = PEP or invalid tax). These severity maps are different.
8. All required object keys present (zeros/empties included); ID lists sorted; no
   extra keys when `additional_properties_allowed:false`; literals echoed.
