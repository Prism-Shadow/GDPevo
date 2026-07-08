# SKILL: ERP Finance & Compliance Close / Release Reviews (task_group_005)

This skill solves read-only ERP finance and vendor-compliance review tasks for the
shared task_group_005 environment. Each task gives a prompt, local payload files
(batch lists, snapshots, scope files), and an `answer_template.json` that defines the
exact output shape. Your job: query the shared API, apply the business rules below,
and emit one JSON object that conforms exactly to the template.

---

## 0. Golden rules (read first)

1. **The shared API is the system of record.** Any local CSV/JSON snapshot, "current
   review status," or base URL written *inside* a prompt (e.g. `127.0.0.1:8005`) is
   **context only**. Use the runner-provided API base URL; reconcile every claim,
   bill, payment, vendor, and compliance fact against the live API before deciding.
2. **Decide for control, not to echo source state.** A record's stored
   `status`/`review_status` is an input, not the answer. Re-derive the decision.
3. **Conform to `answer_template.json` literally.** Return JSON only (no prose).
   Honor: required top-level keys, key sets/orderings, enum `allowed_values`, numeric
   precision, and `additional_properties_allowed: false` (emit ONLY the listed keys,
   nothing extra). Echo any fixed `required_value` fields (task_id, batch_id,
   as_of_date) exactly.
4. **Ordering & precision.** Sort every ID list **ascending by id** unless the template
   says "same order as <payload>" (then preserve the payload's order). Currency =
   number rounded to **2 decimals**, USD. Counts = whole integers. Flag lists of enum
   values = sorted **alphabetically by enum value**; use `[]` when none apply.
5. **Compute, then double-check totals** with a small script. Sum component values for
   any "_total" field rather than eyeballing.

---

## 1. Using the shared API

Base URL is runner-provided. Both `/<name>` and `/api/...` forms exist. Object
endpoints return `{endpoint,count,total,offset,limit,data:[...]}`. Filter with
**exact-match query params by field name**; paginate with `limit`/`offset`.

| Need | Endpoint | Key filters |
|------|----------|-------------|
| Liveness / task group | `/health`, `/api/health` | — |
| Endpoint list | `/endpoints` | — |
| Expense claims | `/api/claims` | `claim_id` |
| AP bills | `/api/ap/bills` | `claim_id`, `bill_id`, `vendor_id` |
| AP payments | `/api/ap/payments` | `bill_id`, `vendor_id`, `payment_id` |
| AP aging | `/api/ap/aging?as_of=YYYY-MM-DD` | `bill_id` (balance = amount − sum(payments), clamped ≥0) |
| Vendors | `/api/vendors` | `vendor_id` |
| Compliance (full record) | `/api/compliance/objects` | `business_id` |
| Compliance sub-views | `/api/compliance/{profile|ownership|registry|screening|bank|risk}/{business_id}` | path id |
| Prepaid invoices | `/api/prepaids/invoices` | `prepaid_invoice_id`, `account` |
| Prepaid GL balances | `/api/prepaids/gl-balances` | `account`, `period`, `entity` |
| Close logs | `/api/close/logs` | `period`, `area`, `status` |

Workflow tips:
- For claim work, fetch the claim, then `bills?claim_id=...`, then
  `payments?bill_id=...` for each bill. A claim may have multiple bills (one matched,
  one stale/wrong).
- `/api/compliance/objects?business_id=X` returns everything you need (bank, pep,
  sanctions, license, missing_fields, risk_score, shell flag, ubo_list, vendor_id).
  The sub-view endpoints are just slices of that record.
- **Aging caveat:** `/api/ap/aging` folds *scheduled* and *processing* payments into
  `paid_amount`, so its `balance` can read 0 even when no payment has cleared. Do NOT
  use aging `balance` for "open balance after CLEARED payments" — compute it yourself
  from the bill amount minus only payments whose `status == "cleared"`. Aging values
  can also disagree with `/bills` for the same id; trust `/bills` + `/payments` as the
  current record.

---

## 2. Domain rule set A — Expense-claim → AP reimbursement close

Use when a batch of `CLM-...` claim IDs must be triaged into payable / paid / blocked
(or eligible / not-ready) buckets.

For each claim gather: claim (`status`, `amount`, `vendor_id`), its bill(s)
(`status`, `amount`, `vendor_id`, `claim_id`), and each bill's payment(s) (`status`,
`amount`).

**A "matched/valid" AP bill** for a claim requires the bill's `amount` AND `vendor_id`
to match the claim, and the bill not be `void`. Watch for:
- a claim linked to a bill whose amount/vendor differ → **mismatch** (broken AP link),
- a `void` bill,
- **no bill at all**,
- a claim with `vendor_id: null` (often signals a bad/placeholder link).

**Payment clearing:** a claim is settled only when a matched bill has a payment with
`status == "cleared"` for the claim amount. Payment `status` ∈
{processing, scheduled, cleared}. `processing`/`scheduled` = **in-flight, NOT cleared**.

### Bucketing
- **paid / settled**: claim `status == "paid"` AND a matched, paid bill with a
  **cleared** payment for the claim amount. (A fully-settled claim should NOT remain in
  an unpaid AP batch — it goes to the "not ready / not eligible to remain" bucket if
  the field's intent is "can stay in the open batch.")
- **payable / eligible**: approved claim with a valid matched bill, not yet cleared
  (payment in-flight or none). It can stay in the open AP queue.
- **blocked / not-ready / crm-required**: amount/vendor mismatch, `void` bill, missing
  bill, or an **unapproved** claim (`status` not `approved`/`paid`, e.g.
  `needs_receipt`). These need owner cleanup before AP release.

### Money fields
- **Open AP balance for a payable claim = the bill's gross `amount`** minus only
  **cleared** payments (in-flight payments do NOT reduce it). For blocked/mismatch/void
  claims the claim's open AP balance is **0.00** (the bad row is excluded).
- A "total of open AP bills for payable claims only" = **sum of gross bill amounts**
  of the payable bucket (NOT the aging net-of-in-flight balance). Validated: using the
  in-flight-net balance instead of the gross amount scores lower.

### Batch status enum
- `blocked` / equivalent: any item is hard-blocked (e.g. unapproved claim, void) — but
  see the stale-snapshot exception below.
- `open_payables` / `needs_ap_refresh`: valid unpaid AP bills / stale rows remain.
- `ready_to_close` / `ready_to_send`: nothing blocked and nothing open.

`reviewed_claim_count` = number of candidate claim IDs requested.

---

## 3. Domain rule set B — Stale AP snapshot reconciliation

When the payload includes a **stale AP export** (CSV/JSON "snapshot"), treat it as a
prior picture, then for each candidate claim compare snapshot vs current API and emit a
**correction code** describing what changed. Typical enum and mapping:

| Current-vs-snapshot situation | correction code |
|---|---|
| Snapshot showed no/none payment; a payment is now in-flight (processing/scheduled) | `mark_in_flight_payment` |
| Snapshot pointed at a wrong/scheduled bill, but a matched **paid** bill now exists | `replace_with_matched_paid_bill` |
| Linked bill's amount or vendor does not match the claim | `exclude_amount_or_vendor_mismatch` |
| Bill is now `void` | `ignore_void_bill` |
| Claim is not approved (e.g. `needs_receipt`) | `block_unapproved_claim` |
| Snapshot already matches current and is fine | `current_snapshot_ok` |

Pick the **dominant** issue per claim (an unapproved claim is `block_unapproved_claim`
even if its bill also mismatches).

`ap_balance_by_claim`: per-claim open balance = gross bill amount − cleared payments;
mismatch/void/unapproved → 0.00.

**Batch status under stale snapshots leans `needs_ap_refresh`** (the export must be
refreshed), even when one candidate is an unapproved/blocked claim. Validated:
`needs_ap_refresh` scored higher than `blocked` for a stale-snapshot conference batch.

`close_log_required` ({required: bool, ids: [...]}): when corrections/AP-refresh are
needed, `required` is **true**; only list `ids` of existing close-log records that
clearly tie to this batch/period (sorted ascending) — otherwise use an empty `ids`
list. Query `/api/close/logs` (filter by `period`/`area`/`status`); messages like
"Waiting on AP export refresh" are the relevant ones, but do not invent ids.

---

## 4. Domain rule set C — Vendor compliance: onboarding & payment-release reviews

Use for `BUS-...` business batches (vendor onboarding release, or AP payment release
after account-change events). Pull `/api/compliance/objects?business_id=...` for each,
plus `/api/vendors?vendor_id=...` for vendor `status` and `bank_account_last4`.

### Field vocabularies (observed)
- `bank_account_status` ∈ {verified, name_mismatch, not_verified, closed}
- `pep_status` ∈ {none, possible_pep, confirmed_pep, not_run}
- `sanctions_check_status` ∈ {clear, possible_match, confirmed_match, not_run}
- `review_status` ∈ {not_started, in_review, awaiting_information, escalated, approved}
- vendor `status` ∈ {active, inactive, on_hold}

### Condition detection (compare dates to the batch `as_of_date`)
- **expired_license**: `license_expiry` strictly **before** `as_of_date`. Equal-to or
  after = NOT expired (e.g. expiry 2025-06-02 with as_of 2025-06-01 is valid).
- **bank issues**: `name_mismatch` → bank-name-mismatch; `closed` → bank-closed.
- **screening not run**: `pep_status == "not_run"` OR `sanctions_check_status ==
  "not_run"`.
- **confirmed financial-crime/PEP**: `pep_status == "confirmed_pep"` or
  `sanctions_check_status == "confirmed_match"`.
- **shell_company_suspected**: boolean field true.
- **missing required documents**: `missing_fields` non-empty.
- **vendor on hold**: vendor record `status == "on_hold"`.
- **invalid tax id**: `tax_id` does not match the standard format (`TIN` + 6 digits);
  e.g. a tax_id containing letters/odd length like `TIN12X899` is invalid.
- **high risk override**: `risk_score >= 70`.

### Hard-stop flag set (onboarding tasks)
Allowed enum (alphabetical): bank_closed, bank_name_mismatch, confirmed_pep,
expired_license, missing_required_documents, sanctions_confirmed, screening_not_run,
shell_company_suspected, vendor_on_hold. Emit the sorted list of flags that apply.

> **Key exclusion rule (validated):** when `license` is already listed in
> `missing_fields`, flag it as **`missing_required_documents` only** — do NOT also add
> `expired_license` for that business. `expired_license` applies only when the license
> date is in the past AND license is not already a missing document.

### Reportable UBO count
`ubo_list` may contain duplicate names and multiple rows per name. Count the number of
**unique beneficial-owner names** that meet the reporting threshold of **25%
ownership** (a name qualifies if it reaches ≥25%; aggregating a name's rows vs taking
its max gives the same result in practice). Return a whole number per business.

### Decision enums

**Onboarding** decisions ∈ {approve, awaiting_information, escalate}:
- **escalate**: a serious/irrecoverable risk flag present — `confirmed_pep`,
  `sanctions_confirmed`, `bank_closed`, `bank_name_mismatch`, `shell_company_suspected`,
  or `vendor_on_hold`.
- **awaiting_information**: only recoverable/info-pending conditions present —
  `missing_required_documents`, `screening_not_run`, and/or `expired_license`, with no
  escalate-level flag.
- **approve**: no flags at all.

**Payment-release-after-account-change** decisions ∈ {release, hold, escalate}:
- **escalate**: `confirmed_pep` (or confirmed sanctions / shell). Identity / financial-
  crime level.
- **hold**: recoverable / operational issues — `bank name_mismatch`, **`bank closed`**,
  `expired_license`, invalid tax id, `screening not_run`, missing documents,
  `possible_pep`, high `risk_score`. (Validated: `bank_closed` and `screening_not_run`
  map to **hold**, not escalate, in the release context.)
- **release**: fully clean — bank `verified`, license valid, tax id valid, screening
  clear, no missing fields, not high-risk.

### Summary / list fields
- `bank_mismatch_ids`: businesses with `bank_account_status == name_mismatch`.
- `invalid_tax_ids`: businesses with malformed `tax_id`.
- `expired_license_ids`: license expired vs `as_of_date` (strict-before).
- `risk_score_override_flags`: businesses with `risk_score >= 70`.
- `review_queue_ids`: **all businesses NOT decided `release`** (both `hold` and
  `escalate` require review before release). Validated: excluding escalations from the
  review queue scores lower than including them.
- `follow_up_business_ids` (onboarding): all non-`approve` businesses.
- `overall_release_ready`: true only if every listed business is `approve`/`release`.

For the release-after-change batch, the requested bank `last4` from the local ticket
usually matches the vendor's `bank_account_last4`; `bank_mismatch_ids` comes from the
compliance `bank_account_status`, not the last4 comparison.

---

## 5. Domain rule set D — Prepaid amortization close & GL reconciliation

When given scoped `PPD-...` invoice IDs, target accounts, a close period (YYYY-MM), and
a variance threshold:

1. Pull each invoice (`original_amount`, `monthly_amortization`, `service_start`,
   `service_end`, `recognition_method` straight_line, `data_quality_flags`, `account`).
2. Pull GL ending balances for each account for the close period
   (`/api/prepaids/gl-balances?account=...&period=YYYY-MM&entity=...`).

### Per-invoice straight-line math (validated)
- **Use a flat monthly amount, NO final-month residual plug.** Adding a remainder in
  the last month to force the balance to exactly 0 scores lower.
- `months_elapsed` = full calendar months from `service_start`'s month through the
  close month, inclusive (e.g. start 2025-01 → close 2025-03 = 3).
- `march_amortization` (current-period) = `monthly_amortization` when the close month is
  within [service_start, service_end]; else 0.
- `cumulative_amortization_through_<month>` = `monthly_amortization × months_elapsed`,
  **capped at `original_amount`**. (Small residuals like 0.01 are expected and correct
  — do not zero them out.)
- `ending_balance` = `original_amount − cumulative` (rounded to 2 decimals).

### Invoice flags
- `default_missing_term_flag` = `data_quality_flags` contains `missing_contract_dates`
  (the invoice used a default/assumed term).
- `exception_flag` = `data_quality_flags` is **non-empty** (ANY flag, e.g.
  `rounded_amount` or `missing_contract_dates`). Validated: restricting exceptions to
  only the missing-term invoices scores lower than "any data-quality flag."
- `default_missing_term_invoice_ids` / `exception_invoice_ids` = sorted-ascending id
  lists from the two flags above.

### Account rollup (per account)
Sum the account's selected invoices for: `original_amount_total`,
`march_amortization_total` (current-period), `cumulative_amortization_through_<month>`,
`schedule_ending_balance`. Then:
- `gl_ending_balance` = the account's GL ending balance for the close period.
- `variance_amount` = `schedule_ending_balance − gl_ending_balance` (sign matters; can
  be negative).
- `variance_flag` = `abs(variance_amount) > variance_threshold` (e.g. 100.0).
- `has_default_missing_term_flag` = any selected invoice in the account has the
  missing-term flag.
- `account_status` ∈ {reconciled, variance_review, requires_reconciliation}:
  - `reconciled`: no material variance and no data-quality problems.
  - `variance_review`: variance over threshold but invoice data is clean.
  - `requires_reconciliation`: variance over threshold **and** a default/missing-term
    data-quality issue exists.

`selected_invoice_ids` and `invoice_results` follow the **payload's order**;
`account_rollup` is keyed by the requested accounts. Report all currency to 2 decimals.

---

## 6. General SOP for any new task

1. Read the prompt and **`answer_template.json`**; list required keys, enum sets,
   orderings, precision, and whether extra keys are forbidden.
2. Identify which domain rule set(s) above apply (claims/AP, stale snapshot,
   compliance onboarding/release, prepaid close).
3. Pull the live API records for every entity in scope; ignore stale snapshots/embedded
   URLs except as context to reconcile against.
4. Re-derive each field from the rules — never copy a stored status as the decision.
5. Build the JSON with a script; sort lists, round money to 2 dp, drop any key the
   template does not list (when additionalProperties is false), and echo fixed values.
6. Sanity-check totals, enum membership, and orderings before returning JSON only.
