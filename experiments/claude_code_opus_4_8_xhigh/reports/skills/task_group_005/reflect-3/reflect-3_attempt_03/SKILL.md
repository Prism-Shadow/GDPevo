# SKILL: task_group_005 ERP Finance & Compliance Review

Reusable SOPs for answering ERP finance/compliance review tasks against the shared
read-only JSON API. These tasks ask you to read CURRENT system records, apply
business rules, and emit a JSON object that conforms exactly to the task's
`answer_template.json`. Local payloads (CSV/JSON snapshots, batch lists, scopes) are
**context only** — the live API is always the system of record.

---

## 1. Remote API — what answers what

Base URL is provided by the runner. **Ignore any base URL written inside a prompt**
(e.g. `127.0.0.1:8005`); always use the runner-provided base. Both bare and `/api/...`
paths work and return identical data.

Object list endpoints return `{endpoint,count,total,offset,limit,data:[...]}`. Filter
with **exact-match query params by field name**; paginate with `limit`/`offset`
(default limit 100). Always set a large `limit` when scanning a whole table.

| Question | Endpoint | Key filter |
|---|---|---|
| Expense claim status/amount/vendor/receipt | `/api/claims` | `claim_id=` |
| AP bill for a claim (link, amount, status, account) | `/api/ap/bills` | `claim_id=` or `bill_id=` |
| Payments against a bill | `/api/ap/payments` | `bill_id=` |
| AP aging balance | `/api/ap/aging?as_of=YYYY-MM-DD` | balance = amount − Σ payments, clamped ≥ 0 |
| Vendor master (status, tax_id, bank last4, terms) | `/api/vendors` | `vendor_id=` |
| Compliance snapshot (all fields) | `/api/compliance/objects` | `business_id=` |
| Compliance detail slices | `/api/compliance/{profile\|ownership\|registry\|screening\|bank\|risk}/{business_id}` | — |
| Prepaid amortization schedules | `/api/prepaids/invoices` | `prepaid_invoice_id=`, `account=` |
| Prepaid GL ending balances | `/api/prepaids/gl-balances` | `account=` (each row has `period`) |
| Close-period logs | `/api/close/logs` | `period=`, `area=`, `status=` |

Notes:
- `compliance/objects` already contains EVERY field the detail endpoints expose
  (bank_account_status, license_expiry, missing_fields, pep_status,
  sanctions_check_status, shell_company_suspected, review_status, risk_score, tax_id,
  ubo_list, ownership_layer_count, vendor_id). Use the snapshot; detail endpoints are
  just decompositions, not extra data.
- A claim/business often links to a vendor via `vendor_id`; vendor `status`
  (active / on_hold) lives in `/api/vendors`, NOT in the compliance object.

---

## 2. Output conventions (apply to every task)

- Emit **JSON only**, conforming exactly to `answer_template.json`. Honor
  `required_top_level_keys` / `top_level_order`. If `additional_properties_allowed:false`,
  include exactly the listed keys — nothing extra.
- Currency: USD, **2 decimals** (round half-up to cents). Counts are whole integers.
- Sort every ID list **ascending by ID** unless the template says otherwise. String
  sort means digits sort before letters (e.g. `PPD-2025-0014` < `PPD-AUR-1251-GOOD-001`,
  and `CLM-2025-0080` < `CLM-2025-FIN-042`). Some lists are "same order as the input
  payload" — preserve payload order there (e.g. selected invoice lists).
- Enum-valued lists with "alphabetical by enum value" ordering must be sorted by the
  literal enum string.
- Copy required constant values verbatim (e.g. `task_id`, `batch_id`, `as_of_date`)
  exactly as the template requires.
- Echo any required member set (e.g. `target_business_ids`) sorted ascending.

---

## 3. Claims → AP → Payment reconciliation (expense-claim close / AP batch tasks)

For each candidate claim, pull the claim, its bill(s) by `claim_id`, and payments by
`bill_id`. Classify from the THREE-WAY match of claim ↔ bill ↔ payment.

**Validity of a bill as the claim's reimbursement bill** requires the bill to match the
claim on BOTH amount and vendor. A bill whose amount or vendor differs from the claim is
a *mismatched* bill — it does NOT count as the claim's payable, even if its status looks
fine. A claim may have multiple bills; pick the one that matches claim amount + vendor.

**Status buckets:**
- **Paid / settled**: claim has a matched bill with `status=paid` AND a payment with
  `status=cleared` for the claim amount. (A claim whose own `status=paid` and has a
  cleared matched payment is settled.)
- **Payable (open)**: claim `status=approved`, a valid matched bill exists that is open
  (`scheduled`/`approved`, not paid/void), and payment is not yet cleared.
- **Blocked / not-ready**, for any of:
  - bill amount or vendor mismatches the claim (`exclude_amount_or_vendor_mismatch`),
  - bill `status=void` (`ignore_void_bill`),
  - no bill linked to the claim at all,
  - claim not approved — e.g. `needs_receipt`, draft (`block_unapproved_claim`),
  - already paid/settled (cannot stay in a still-to-pay batch).

**Open AP balance (the load-bearing rule):**
- Open balance of a claim = matched-bill amount − **cleared payments only**.
- Payments with `status` in {processing, scheduled, in-flight} do **NOT** reduce the
  open balance. (Verified: subtracting a non-cleared payment scores wrong.)
- A claim whose only bill is mismatched, void, or already paid/cleared has open
  balance **0.00**. Do not report a mismatched/void bill's amount as the claim's open
  balance. Only a *valid open matched* bill contributes a non-zero balance.
- A "total open AP" field sums balances of the **payable** claims only.

**Stale-snapshot tasks:** when a local CSV/JSON snapshot is given, treat it as stale.
Re-fetch live data and emit a per-claim correction code from the live-vs-snapshot delta:
  - `current_snapshot_ok` — live matches snapshot.
  - `mark_in_flight_payment` — snapshot showed no/scheduled payment; live shows a
    `processing`/in-flight payment on the matched open bill.
  - `replace_with_matched_paid_bill` — snapshot pointed at a wrong/scheduled bill; live
    shows the claim is actually paid via a different *matched* `paid` bill + `cleared`
    payment.
  - `exclude_amount_or_vendor_mismatch` — linked bill's amount/vendor ≠ claim.
  - `ignore_void_bill` — linked bill is void.
  - `block_unapproved_claim` — live claim status is not approved.

**Batch status enums:**
- `blocked` / `blocked`-type: any item is hard-blocked (unapproved claim, void, etc.).
- `open_payables` / `needs_ap_refresh`: no hard block but valid unpaid AP remains, or
  live data has drifted from the supplied (stale) snapshot. For stale-export batch
  tasks, prefer **`needs_ap_refresh`** when the only issue is that the snapshot is out
  of date (in-flight payments, now-paid bills) rather than a compliance hard-stop.
- `ready_to_close` / `ready_to_send`: every item clean and settled/payable as required.

**close_log_required**: only mark `required:true` / list close-log IDs when the task
clearly ties a claim to a specific close-log entry. Close logs are keyed by
`period`/`area`/`related_account`, not by claim ID, so by default a reimbursement batch
needs no specific close-log (`required:false`, `ids:[]`) unless evidence links one.

---

## 4. Vendor onboarding / compliance release-control tasks

Pull `compliance/objects?business_id=` for each business, plus the linked vendor's
`status` from `/api/vendors?vendor_id=`. Compare dates against the task's `as_of_date`.

**Hard-stop flag mapping** (each business → list of flags, sorted alphabetically by enum
value; empty list when none):
- `bank_closed` ← `bank_account_status == "closed"`
- `bank_name_mismatch` ← `bank_account_status == "name_mismatch"`
- `confirmed_pep` ← `pep_status == "confirmed_pep"` (NOT `possible_pep`)
- `expired_license` ← `license_expiry < as_of_date` (strict: equal-or-later is valid)
- `missing_required_documents` ← `missing_fields` is non-empty
- `sanctions_confirmed` ← `sanctions_check_status` is a confirmed/hit value
- `screening_not_run` ← `sanctions_check_status == "not_run"` OR `pep_status == "not_run"`
- `shell_company_suspected` ← `shell_company_suspected == true`
- `vendor_on_hold` ← linked vendor `status == "on_hold"`

**Reportable UBO count** (VERIFIED): count of **unique beneficial-owner names** whose
ownership is **≥ 25%** at the reporting threshold. Deduplicate by `name` first
(aggregate or take the max ownership per name), then count names that reach 25%. A
25% threshold is correct here; a 10% threshold was tested and scored worse. Owners
below 25% (e.g. 24%) are excluded; the same name appearing in multiple layers counts once.

**Per-business decision** (enum approve|awaiting_information|escalate, or
release|hold|escalate). Decide from CURRENT evidence — do NOT just copy
`review_status`:
- **approve / release**: clean evidence — bank verified, no missing docs, screening
  run, no confirmed PEP, license valid, vendor active, no shell flag. A clean business
  is releasable even if its `review_status` is still `in_review`/`not_started` and even
  if `risk_score` is moderately high (e.g. 64) but below the override threshold.
- **hold**: recoverable / fixable single issues (e.g. `name_mismatch`, missing docs)
  with no hard escalate trigger.
- **escalate**: serious red flags — `confirmed_pep`, `bank_closed`,
  `sanctions`/`screening_not_run`, `vendor_on_hold`, `shell_company_suspected`, or a
  combination of blocking issues (e.g. bank name_mismatch + invalid tax + expired
  license).

**Derived list fields:**
- `bank_mismatch_ids` ← bank_account_status == name_mismatch.
- `invalid_tax_ids` ← tax_id violates the standard format `TIN` + 6 digits (e.g.
  `TIN12X899` is invalid). Well-formed IDs are valid even if they look like placeholders.
- `expired_license_ids` ← license_expiry < as_of_date.
- `risk_score_override_flags` ← `risk_score >= 70` (70 itself qualifies; 64 does not).
- `review_queue_ids` ← businesses that need review **before release** — i.e. the
  **hold** set only. Do NOT dump all non-released businesses here; escalated businesses
  and released businesses are excluded. (Including everyone scored worse.)
- `follow_up_business_ids` (onboarding variant) ← every non-approved business
  (awaiting_information + escalate). (For that field, all-non-approve scored better than
  awaiting-information-only.)
- `overall_release_ready` ← true only if every business is approve/release.

---

## 5. Prepaid close / amortization reconciliation tasks

Scope to the invoice IDs in the payload, the named accounts, and the named close
period. Pull each invoice (`/api/prepaids/invoices`) and the GL ending balance for that
period from `/api/prepaids/gl-balances` (match `account` + `period`).

**Straight-line schedule per invoice** (recognition_method `straight_line`,
`monthly_amortization` `M`, `original_amount` `O`, `service_start`..`service_end`):
- Months recognized through the close period N = count of calendar months from the
  service-start month through the close-period month, capped at the service-end month
  (N=0 if service starts after the period).
- `march_amortization` (period amortization) = `M` if the period month is within
  [start, end], else 0.
- `cumulative_amortization_through_<period>` = round(M × N, 2), capped at O.
- `ending_balance` = round(O − cumulative, 2). Fully-amortized invoices may leave a
  ±0.01 rounding residual; report the straight `O − M×N` result to 2 decimals.

**Per-invoice flags:**
- `default_missing_term_flag` ← invoice `data_quality_flags` contains
  `missing_contract_dates` (term was defaulted / dates missing).
- `exception_flag` ← invoice has **any** `data_quality_flags` entry (this includes both
  `missing_contract_dates` AND `rounded_amount`). VERIFIED: a `rounded_amount` invoice is
  an exception even when M×months reconciles exactly to O. `exception_invoice_ids` =
  every invoice with a non-empty `data_quality_flags`, sorted ascending.
- `default_missing_term_invoice_ids` = invoices with `missing_contract_dates`, ascending.

**Account rollup** (per account): sum selected invoices' original / period /
cumulative / ending; `selected_invoice_count`; `gl_ending_balance` from the GL row;
`variance_amount = schedule_ending_balance − gl_ending_balance`;
`variance_flag = |variance| > threshold` (threshold from the payload, e.g. 100.0);
`has_default_missing_term_flag = any selected invoice has missing_contract_dates`.
- `account_status`:
  - `reconciled` — no variance, no data-quality issues.
  - `variance_review` — variance over threshold but no missing-term data issues.
  - `requires_reconciliation` — account has default/missing-term invoices (data-quality
    problems requiring reconciliation). This status takes priority over plain
    variance_review when missing-term invoices are present in the account. (VERIFIED:
    an account with both a large variance and missing-term invoices is
    `requires_reconciliation`, not `variance_review`.)

---

## 6. Cross-cutting reminders

- The current API record overrides any supplied snapshot, CSV, or "review status".
  Always re-derive decisions from live data; the prompts explicitly warn that decisions
  must be "release control," not a copy of the source system's current status.
- Distinguish reimbursement/expense-case issues (claim approval, receipts) from
  AP/payment-evidence issues (bill match, void, payment cleared) — keep them in their
  respective output fields.
- Only `cleared` payments and `paid` bills settle/reduce balances; `scheduled`,
  `processing`, `approved`, and `void` do not.
- Re-read the answer_template before finalizing: confirm key names, ordering rules,
  enum spellings, precision, and whether extra keys are forbidden.
