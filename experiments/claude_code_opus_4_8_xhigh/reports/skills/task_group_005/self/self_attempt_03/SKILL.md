# SKILL: ERP Finance Close & Compliance-Gating (task_group_005)

Executable playbook for solving month-end finance/compliance review tasks that read
from a shared read-only ERP JSON API and emit a JSON answer matching a provided
`answer_template.json`. Covers five recurring task families:

1. Reimbursement-to-AP close (claims -> bills -> payments classification)
2. Stale-AP-snapshot reconciliation (CSV export vs live API)
3. Vendor onboarding finance-risk release (compliance gating + UBO counts)
4. Payment-release risk review after vendor account-change events
5. Prepaid / GL reconciliation (straight-line amortization vs GL ending balance)

---

## 0. GOLDEN RULES (apply to every task)

- **The live API is the system of record.** Any base URL written in a prompt
  (e.g. `http://127.0.0.1:8005`) is a decoy — always use the runner-provided base URL.
  In this environment that base is `<remote-env-url>`. Query it with `curl`.
- **Local payloads (CSV exports, snapshots, batch files) are CONTEXT, not truth.**
  They are deliberately stale/wrong. Always re-pull current claim/bill/payment/compliance
  records and decide from those. The local file usually tells you *which IDs* to review
  and *what shape* to return — nothing more.
- **Read `answer_template.json` first and obey it literally.** It dictates required keys,
  enum value sets, list ordering, numeric precision, and whether extra keys are allowed
  (`additional_properties_allowed: false` => emit ONLY the listed keys, nothing else).
- **Output discipline:** JSON only, no prose. USD numbers to 2 decimals. Whole-number
  counts as integers. Sort every ID list ascending by its ID (string sort works for the
  zero-padded IDs here). Echo any `required_value` fields verbatim (e.g. `task_id`,
  `batch_id`, `as_of_date`).
- **Only decide on the IDs the task names.** Do not add or drop candidates.

---

## 1. THE API

Two interchangeable route prefixes return identical data: bare (`/claims`) and `/api`
(`/api/claims`). Object list endpoints return an envelope:
`{endpoint, count, total, offset, limit, data:[...]}`. Read `total`, then page with
`limit`/`offset` (default limit ~100; bump `limit` to pull everything at once).

Filtering = **exact-match query params by field name**, e.g.
`/api/ap/bills?claim_id=CLM-2025-0090`, `/api/claims?status=paid`,
`/api/compliance/objects?business_id=BUS-2025-0009`.

| Need | Endpoint | Key fields |
|---|---|---|
| Expense claims | `/api/claims`, `/api/claims/{claim_id}` | `claim_id, amount, status, vendor_id, receipt_status, approved_date, policy_flags` |
| AP bills | `/api/ap/bills?claim_id=...` or `?bill_id=...` | `bill_id, claim_id, amount, status, vendor_id, account` |
| Payments | `/api/ap/payments?bill_id=...` | `payment_id, bill_id, amount, status, payment_date` |
| AP aging | `/api/ap/aging?as_of=YYYY-MM-DD` | `bill_id, amount, paid_amount, balance, status` |
| Vendors | `/api/vendors?vendor_id=...` | `vendor_id, status, bank_account_last4, tax_id, payment_terms` |
| Compliance (merged) | `/api/compliance/objects?business_id=...` | ALL compliance fields in one record |
| Compliance facets | `/api/compliance/{profile\|ownership\|registry\|screening\|bank\|risk}/{business_id}` | facet subsets |
| Prepaid invoices | `/api/prepaids/invoices` | `prepaid_invoice_id, account, original_amount, monthly_amortization, service_start, service_end, data_quality_flags` |
| GL balances | `/api/prepaids/gl-balances` (or `/gl/balances`) | `account, period(YYYY-MM), ending_balance, account_name, entity` |
| Close logs | `/api/close/logs` | `log_id, area, period, status, related_account` |

### Linking model
- Bill links to its claim via `bill.claim_id`. Filter bills by `claim_id` (NOT bill_id)
  to find the claim's reimbursement bill.
- Payment links to its bill via `payment.bill_id`.
- Compliance business links to a vendor via `vendor_id` (use it to pull vendor `status`).

### Compliance facet endpoints
`/api/compliance/objects` returns the **full merged record** (easiest — use it).
The facet endpoints just slice that same record:
- `profile`: business_name, jurisdiction, missing_fields, registration_number, tax_id, vendor_id
- `ownership`: ownership_layer_count, shell_company_suspected, ubo_list
- `registry`: jurisdiction, license_expiry, registration_number, tax_id
- `screening`: pep_status, sanctions_check_status
- `bank`: bank_account_status
- `risk`: review_status, risk_score

### CRITICAL aging caveat
`/api/ap/aging` computes `balance = amount - sum(payments)` clamped to >= 0, but
`paid_amount`/`balance` **count EVERY payment regardless of status (scheduled,
processing, cleared) and regardless of `as_of` vs payment_date.** So a bill with only a
`processing` or `scheduled` payment still shows `balance: 0.0`.
=> **Never use aging balance to decide "paid / cleared / payable."** Pull the actual
payment records and inspect `payment.status` yourself. Use aging only for headline
open-balance roll-ups when the task explicitly asks for the aging definition.

### Duplicate IDs
The same `bill_id` can appear on multiple records with different `claim_id`/`amount`/
`vendor_id`. Always select the record whose `claim_id` matches the claim under review
(and cross-check amount + vendor), not the first row returned.

---

## 2. REIMBURSEMENT-TO-AP CLOSE (claims close-status)

Goal: split a named batch of claim IDs into **paid / payable / blocked** and roll up an
open AP total. For each claim, pull the claim, its bill(s) via `claim_id`, and each
bill's payment(s).

Define a bill as a **valid reimbursement match** when:
`bill.claim_id == claim_id` AND `bill.amount == claim.amount` (to the cent) AND
(`claim.vendor_id` is null OR `bill.vendor_id == claim.vendor_id`) AND
`bill.status != void`.

Classification:
- **PAID** — valid matched bill with status `paid` AND a payment whose `status == cleared`
  and amount == claim amount. (A `processing`/`scheduled` payment is NOT cleared => not paid.)
- **PAYABLE** (stays in the AP queue) — claim is `approved`, has a valid matched bill that
  is open (`scheduled`/`approved`) and not yet cleared. This is a real open reimbursement.
- **BLOCKED** — anything that should not release to AP, i.e. ANY of:
  - no bill linked to the claim at all (no AP evidence);
  - linked bill amount or vendor mismatches the claim (wrong AP link);
  - linked bill status `void`;
  - claim not in an approved/paid state (e.g. `needs_receipt`, `submitted`, `rejected`);
  - (use judgment) receipt/support clearly broken with no offsetting paid evidence.
  Distinguish *expense-case* issues (claim not approved, partial/missing receipt) from
  *AP/payment-evidence* issues (void/mismatched/missing bill) when the template has
  separate fields for them. Blocked items usually populate a `crm_required` /
  remediation list.

Roll-ups & status:
- Open AP total = sum of bill amounts for **PAYABLE** claims only (exclude paid, blocked,
  voided, and mismatched bills). Watch the unit the template asks for: some templates say
  "USD precision 2", others say "USD cents" — read it.
- `reviewed_claim_count` = number of claim IDs requested.
- Batch status precedence: **blocked** if any item is blocked; else **open_payables**
  (valid unpaid bills remain); else **ready_to_close**.

Worked signal patterns seen in train data: an `approved` claim with a matching
`scheduled` reimbursement bill + `processing` payment => PAYABLE (not paid). A `paid`
claim whose matched bill is `paid` with a `cleared` payment => PAID, and any *other*
bill linked to it with a different amount/vendor is a stray to ignore. Amount/vendor
mismatch, void bill, or no bill => BLOCKED.

---

## 3. STALE-AP-SNAPSHOT RECONCILIATION

You get a CSV/JSON snapshot (e.g. `stale_ap_snapshot.csv`) plus candidate claim IDs.
Ignore the snapshot's status columns; re-pull live claim/bill/payment/close-log data and
classify into **eligible / not_ready**, then assign a per-claim correction reason.

Per-claim correction reason enum (derived from snapshot-vs-live diff):
- `current_snapshot_ok` — live state matches snapshot and claim is genuinely eligible.
- `mark_in_flight_payment` — snapshot showed no/older payment, but live bill now has an
  uncleared (`processing`/`scheduled`) payment.
- `replace_with_matched_paid_bill` — snapshot pointed at a wrong/mismatched bill; the
  correct matched bill is `paid`/`cleared` under a different `bill_id`.
- `exclude_amount_or_vendor_mismatch` — live linked bill's amount or vendor does not
  match the claim.
- `ignore_void_bill` — live bill status is `void`.
- `block_unapproved_claim` — live claim is not approved (e.g. `needs_receipt`).

Eligibility: a claim is **eligible** only if approved with a valid matched open bill (or
matched in-flight) suitable to stay in the batch; otherwise **not_ready**. Anything paid &
settled also drops out of an "open batch" (it is done, not "eligible to send").

`ap_balance_by_claim`: open AP balance per claim AFTER applying cleared payments and
**ignoring stale/void/mismatched rows**. Compute from live bill amount minus cleared
payments; report `0.00` for paid/void/mismatched/blocked. Use 2 decimals for every key.

`close_log_required`: query `/api/close/logs` for entries tied to the affected period/
account/area; set `required=true` with the sorted `log_id` list when corrections imply a
close-log entry is needed, else `required=false` with `ids: []`.

Batch status: **blocked** if any unapproved/void/mismatch blocker; else
**needs_ap_refresh** if the snapshot is stale but fixable (in-flight payments, replace
bill); else **ready_to_send**.

---

## 4. VENDOR ONBOARDING FINANCE-RISK RELEASE

Per business: pull `/api/compliance/objects?business_id=...` and the linked vendor
(`/api/vendors?vendor_id=...`) for vendor `status`.

### Hard-stop flags (presence => business cannot be released)
Map evidence to the template's enum set, then **sort flags alphabetically by enum value**,
empty list when none:
- `vendor_on_hold` — linked vendor `status == on_hold`.
- `bank_closed` — `bank_account_status == closed`.
- `bank_name_mismatch` — `bank_account_status == name_mismatch`.
- `confirmed_pep` — `pep_status == confirmed_pep`. (`possible_pep` is NOT a hard stop.)
- `expired_license` — `license_expiry < as_of_date`.
- `missing_required_documents` — `missing_fields` non-empty.
- `sanctions_confirmed` — `sanctions_check_status == confirmed`.
- `screening_not_run` — `sanctions_check_status == not_run` (screening not performed).
- `shell_company_suspected` — `shell_company_suspected == true`.
Always validate the exact enum set against the template; only emit values it lists.

### Reportable UBO count
Count **unique beneficial-owner NAMES with `ownership_pct >= 25`** (25% reporting
threshold). De-duplicate by name first (the same name appears multiple times, sometimes
with several stakes) — count each distinct qualifying name once. A name appearing only
with sub-25% stakes is not reportable.

### Decision (per template's enum, typically approve / awaiting_information / escalate)
- `approve` — no hard-stop flags and nothing pending.
- `awaiting_information` — fixable/pending gaps (missing docs, expired license, screening
  not run, bank issues) that just need information/remediation.
- `escalate` — serious risk requiring investigation (confirmed PEP, shell company,
  confirmed sanctions, vendor on hold). When in doubt between the two, escalate the
  irreversible/investigatory issues and leave document/expiry/bank fixes as awaiting_info.
- `follow_up_business_ids`: every business that is not a clean `approve`.
- `overall_release_ready`: true only if EVERY listed business is releasable (no hard
  stops anywhere). One blocked business => false.
Do NOT just copy the source `review_status` — that is the current workflow state, not a
release-control decision. Re-derive the decision from the evidence.

---

## 5. PAYMENT-RELEASE RISK REVIEW (after account-change events)

Pull live compliance + vendor for each business. The local account-change batch gives
review date (`as_of_date`) and requested bank last4 — the requested last4 typically
already matches the vendor's current `bank_account_last4`; the real gating comes from
compliance evidence.

Derived list fields (each ascending by business_id):
- `bank_mismatch_ids` — `bank_account_status == name_mismatch`.
- `invalid_tax_ids` — `tax_id` not matching the canonical format. Canonical = `TIN` + 6
  digits. Invalid = malformed (a letter in the digits, e.g. `TIN12X899`) OR an obvious
  repeated-digit placeholder (e.g. `TIN999999`, `TIN111111`). A vendor-vs-compliance
  tax_id mismatch is a corroborating signal.
- `expired_license_ids` — `license_expiry < as_of_date`.
- `risk_score_override_flags` — `risk_score >= 70`.
- `review_queue_ids` — businesses needing compliance/AP review before release (any
  unresolved gate: bank issue, invalid tax, expired license, missing docs, screening not
  run, in_review/not_started status, etc.).

Decision enum (release / hold / escalate):
- `escalate` — irreversible/serious: `confirmed_pep`, `screening_not_run`/`not_run`,
  `bank_closed`, `shell_company_suspected`, confirmed sanctions, or vendor `on_hold`.
- `hold` — fixable operational blockers: `bank_name_mismatch`, `expired_license`,
  `invalid_tax`, `missing_required_documents`.
- `release` — only when fully clean (verified bank, valid tax, current license, no
  screening/PEP/shell issues, vendor active). A high risk_score alone (>=70) flags an
  override but, with no other blocker, is a borderline hold/review rather than automatic
  release — read the template's intent.
Echo `task_id`, `batch_id`, `as_of_date`, and the sorted `target_business_ids` exactly.
If `additional_properties_allowed: false`, emit only the listed top-level keys.

---

## 6. PREPAID / GL RECONCILIATION (straight-line amortization)

Scope: a payload lists `selected_prepaid_invoice_ids`, the accounts to reconcile
(e.g. 1250, 1251), the close period (e.g. 2025-03), the entity, and a
`variance_threshold_abs` (e.g. 100.0). Pull each invoice from `/api/prepaids/invoices`
and the GL ending balance for each account+period from `/api/prepaids/gl-balances`.

### Per-invoice straight-line schedule (use the RECORDED `monthly_amortization`)
Term months = inclusive month span `service_start .. service_end`
(`(ey-sy)*12 + (em-sm) + 1`). Let close be the last day of the close period.
- `months_elapsed_through_close` = inclusive months from service_start month to close
  month, capped at `[0, term]` (0 if service starts after close).
- `march_amortization` (close-month amortization) = `monthly_amortization` if the close
  date is within `[service_start, service_end]`, else `0`.
- `cumulative_amortization_through_close` = `monthly_amortization * months_elapsed`,
  capped at `original_amount`.
- `ending_balance` = `original_amount - cumulative`, floored at 0.
- Round every amount to 2 decimals. Tiny residuals (e.g. 0.01) from rounded monthly
  rates are expected and acceptable.

### Data-quality / default-or-missing-term flag (`default_missing_term_flag`)
Set true when the invoice's amortization basis is untrustworthy:
- it carries a data-quality flag implying term problems (e.g. `missing_contract_dates`),
  OR
- the recorded `monthly_amortization` does NOT equal `original_amount / term` (the
  straight-line rate implied by the dates) within a cent — i.e. a default/override rate
  was used instead of a true date-driven schedule.
`rounded_amount` alone (where recorded ~= implied) is benign and need not flag.
`exception_flag` per invoice = it has any data-quality issue or default/missing-term
condition (the invoice needs review).

### Account roll-up & status
Sum the per-invoice figures by account: `selected_invoice_count`,
`original_amount_total`, `march_amortization_total`,
`cumulative_amortization_through_march`, and `schedule_ending_balance`
(sum of per-invoice ending balances).
- `gl_ending_balance` = GL `ending_balance` for that account at the close period.
  (Note GL covers ALL prepaids in the account, so the selected subset's schedule will
  often differ materially from GL — large variances are normal and should be flagged,
  not "fixed.")
- `variance_amount` = `schedule_ending_balance - gl_ending_balance` (this exact sign/
  order; round to 2 dp).
- `variance_flag` = `abs(variance_amount) > variance_threshold_abs`.
- `has_default_missing_term_flag` = any selected invoice in the account is flagged.
- `account_status`:
  - `requires_reconciliation` — variance over threshold AND/OR default/missing-term data
    issues present (cannot trust the schedule).
  - `variance_review` — variance over threshold but data is otherwise clean.
  - `reconciled` — within threshold and clean.

### Output ordering
`selected_invoice_ids` and `invoice_results` keep the SAME order as the scope file.
`default_missing_term_invoice_ids` and `exception_invoice_ids` are sorted ascending by
invoice id. Echo `period` (YYYY-MM) and `entity` exactly.

---

## 7. COMMON MISJUDGMENTS (do not repeat)

1. Trusting the local snapshot/CSV/batch status instead of re-pulling live API data.
2. Using aging `balance`/`paid_amount` to judge "paid" — it counts uncleared payments.
   Always check `payment.status == cleared`.
3. Matching a bill by `bill_id` alone when duplicate bill_ids exist — match by `claim_id`
   plus amount + vendor.
4. Treating an amount/vendor-mismatched or `void` bill as valid AP evidence.
5. Counting non-unique UBO names, or counting owners below the 25% threshold.
6. Copying source `review_status`/workflow state as the release decision instead of
   re-deriving it.
7. Confusing `possible_pep` (not a hard stop) with `confirmed_pep`, or `not_run` (a
   screening gap / screening_not_run) with `clear`.
8. Wrong variance sign — it is `schedule_ending_balance - gl_ending_balance`.
9. Emitting extra keys when `additional_properties_allowed: false`, or skipping required
   echoed values (task_id/batch_id/as_of_date) and required object keys.
10. Forgetting precision/ordering: 2-dp USD, integer counts, ascending ID sorts, and
    list orders that must follow the scope file vs. ascending-by-id (read which one each
    field wants).

## 8. EXECUTION CHECKLIST

1. Read prompt + `answer_template.json` + any payload; note candidate IDs, as_of/period,
   required keys, enums, ordering, precision, additionalProperties rule.
2. Pull live records for each ID from the correct endpoints (claims+bills+payments;
   compliance+vendor; prepaid invoices+GL). Ignore decoy base URLs and stale local data.
3. Apply the family's rules above to derive each field.
4. Build JSON exactly per template: correct keys only, enums from the allowed set, sorted
   lists, 2-dp numbers, echoed constants.
5. Re-read the template once more and diff your keys/enums/ordering against it before
   emitting. Output JSON only.
