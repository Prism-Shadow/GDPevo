# SKILL: ERP Finance / Compliance Close & Release Reviews (task_group_005)

This skill solves ERP finance review tasks: AP/reimbursement close batches, vendor
onboarding/release-control, prepaid amortization close, stale-snapshot AP reconciliation,
and account-change payment-release risk reviews. Each task gives a `prompt.txt`, local
`payloads/` (batch scope + `answer_template.json`), and is answered ONLY from the shared
read-only ERP API. Always return strict JSON matching the task's `answer_template.json`.

---

## 1. The remote API (the only system of record)

Base URL is provided by the runner. IGNORE any base URL written inside a prompt
(e.g. `http://127.0.0.1:8005`). Use the runner-provided base URL.

Treat the live API as the system of record. ANY local CSV/JSON snapshot in `payloads/`
(e.g. `stale_ap_snapshot.csv`) is CONTEXT ONLY — never the answer source. Re-pull every
field from the API and reconcile against it.

Query with exact-match query params by field name, plus `limit`/`offset`. Object list
endpoints return `{endpoint,count,total,offset,limit,data:[...]}`. Both `/x` and `/api/x`
forms work.

Endpoints and what they answer:
- `/api/claims?claim_id=...` → expense claim: `status`, `amount`, `vendor_id`,
  `receipt_status`, `policy_flags`, `approved_date`.
- `/api/ap/bills?claim_id=...` or `?bill_id=...` → AP bill: `status`
  (paid/scheduled/approved/void), `amount`, `vendor_id`, `account`. A claim may have
  0, 1, or several linked bills.
- `/api/ap/payments?bill_id=...` → payment: `status` (cleared/processing/scheduled),
  `amount`, `vendor_id`, `payment_date`.
- `/api/ap/aging?as_of=YYYY-MM-DD` → balance = amount − sum(payments), clamped ≥ 0.
- `/api/vendors?vendor_id=...` → `status` (active/on_hold), `tax_id`,
  `bank_account_last4`, `legal_name`, `default_account`.
- `/api/compliance/objects?business_id=...` → FULL compliance snapshot per business
  (preferred). Fields: `bank_account_status`, `pep_status`, `sanctions_check_status`,
  `license_expiry`, `missing_fields`, `risk_score`, `shell_company_suspected`,
  `review_status`, `tax_id`, `ubo_list[{name,ownership_pct}]`, `ownership_layer_count`,
  `vendor_id`, `jurisdiction`.
- `/api/compliance/{profile|ownership|registry|screening|bank|risk}/{business_id}` →
  same data as a subset/projection of the object. The detail endpoints are CONSISTENT
  with `/compliance/objects` (no "current vs stale" divergence between them); prefer the
  single `/compliance/objects` call.
- `/api/prepaids/invoices?prepaid_invoice_id=...` → `original_amount`,
  `monthly_amortization`, `service_start`, `service_end`, `account`,
  `recognition_method`, `data_quality_flags`.
- `/api/prepaids/gl-balances` → GL ending balance per `account` per `period` (filter
  the row whose `period` == the close month, e.g. `2025-03`).
- `/api/close/logs` → close-task log entries (`log_id`,`area`,`status`,`period`,
  `related_account`,`message`).

To link records: claim → bills via `bills?claim_id=`; bill → payments via
`payments?bill_id=`; business → vendor via the compliance object's `vendor_id`.

---

## 2. Output conventions (apply to every task)

- Match `answer_template.json` EXACTLY: required keys, key order if `top_level_order`
  is given, enum spelling, and `additional_properties_allowed:false` (emit no extra keys).
- All ID lists: sort ASCENDING by the id string (claim_id / business_id / invoice_id /
  log_id). Enum-value lists (e.g. hard-stop flags): sort ALPHABETICALLY by enum value.
  Use `[]` (empty list) when none apply, never null.
- Currency: USD, 2 decimals (unless a template explicitly says cents, e.g. one variant
  of the reimbursement task says "USD cents"). Read the template's `unit`/`precision`
  per field — do not assume.
- UBO / counts: whole integers.
- Echo required literal values verbatim (`task_id`, `batch_id`, `as_of_date`,
  `period`, `entity`) when the template pins them.
- Reviewed/selected counts = number of IDs in the requested batch.

---

## 3. Reimbursement / AP close batch (claims → bills → payments)

Classify each candidate claim into paid / payable / blocked using CURRENT API state:

- **paid**: matching AP bill with `status == "paid"` AND a payment with
  `status == "cleared"` for the claim amount, vendor matching. (Claim `status` is
  often already "paid" too.)
  - A payment that is `processing` or `scheduled` is NOT cleared → NOT paid. It is an
    in-flight payment; the bill is still an open payable. (Verified: treating a
    `processing` payment as paid lowers the score.)
- **payable / can remain in batch**: claim approved, has a VALID linked AP bill whose
  `amount` and `vendor_id` match the claim, bill not yet paid/void; payment absent or
  in-flight. Open AP balance for these = bill amount − cleared payments (≥ 0).
- **blocked / needs cleanup (CRM/owner remediation)**: any of:
  - no linked AP bill at all;
  - linked bill `status == "void"`;
  - bill `amount` ≠ claim `amount`, or bill `vendor_id` ≠ claim `vendor_id`
    (amount/vendor mismatch — a wrong AP link);
  - claim not approved (e.g. `needs_receipt`).

`ap_open_balance_total` (when asked "for payable claims only") sums ONLY the valid open
AP bills of the payable set — exclude paid claims and exclude blocked/mismatched/void
bills.

Batch status enum (reimbursement-close variant): `blocked` if ANY item is blocked;
else `open_payables` if valid unpaid AP bills remain; else `ready_to_close`.

### Stale-snapshot AP reconciliation variant
When a local AP snapshot (CSV/JSON) is provided, re-pull live data and assign a
per-claim correction code from the template enum:
- `current_snapshot_ok` — live state matches the snapshot.
- `mark_in_flight_payment` — snapshot showed no/older payment, but live has a
  `processing`/`scheduled` payment on the matching bill.
- `replace_with_matched_paid_bill` — snapshot pointed at the wrong bill; live shows the
  claim settled via a DIFFERENT bill that is paid+cleared and matches amount/vendor.
- `exclude_amount_or_vendor_mismatch` — live linked bill's amount or vendor doesn't
  match the claim.
- `ignore_void_bill` — live linked bill is `void`.
- `block_unapproved_claim` — live claim status is not approved (this takes priority over
  bill/payment observations).
- Per-claim open AP balance = matched valid bill amount − cleared payments, clamped ≥ 0;
  excluded/void/mismatched/unapproved → 0.00. Settled (paid+cleared) → 0.00.
- A claim that is settled, void-linked, mismatched, or unapproved is NOT "eligible to
  remain in the batch"; only an approved claim with a valid open matching bill stays.
- Batch status for a stale export with reconcilable issues = `needs_ap_refresh`
  (NOT `blocked`). Reserve `blocked` only when nothing can proceed.
- (Open question, low confidence: which `close_log` IDs are "required" for the refresh.
  When unsure, prefer the close-log entries whose `message` references the AP export
  refresh and that are not yet `closed`; this part is not fully nailed down.)

---

## 4. Vendor onboarding / account-change release reviews (compliance)

Derive decisions from EVIDENCE, never copy the compliance `review_status`. The prompt
explicitly wants release-control decisions, not a mirror of current review state.

### Per-business evidence → hard-stop flags
Map compliance/vendor fields to flags (use only the enum values the template lists):
- `bank_closed` ← `bank_account_status == "closed"`
- `bank_name_mismatch` ← `bank_account_status == "name_mismatch"`
- `confirmed_pep` ← `pep_status == "confirmed_pep"` (NOT `possible_pep`)
- `sanctions_confirmed` ← `sanctions_check_status == "confirmed"`
- `screening_not_run` ← `sanctions_check_status == "not_run"` OR `pep_status == "not_run"`
- `expired_license` ← `license_expiry < as_of_date` …BUT see next bullet
- `missing_required_documents` ← `missing_fields` is non-empty
- IMPORTANT: if `"license"` is in `missing_fields`, flag `missing_required_documents`
  and do NOT also flag `expired_license` for that business — a missing license is
  "missing", not "expired" (verified: double-flagging lowered the score).
- `shell_company_suspected` ← `shell_company_suspected == true`
- `vendor_on_hold` ← vendor `status == "on_hold"`
Sort each business's flag list alphabetically; `[]` when none.

### Reportable UBO count
Count UNIQUE beneficial-owner names (dedupe by name) whose ownership meets the reporting
threshold. Use a 25% threshold (ownership_pct ≥ 25) as the working rule. (The exact
threshold was not fully confirmed by feedback — treat counts as the lower-confidence
field and double-check against the template's wording.)

### Cross-source checks (account-change variant)
- `bank_mismatch_ids` = businesses with `bank_account_status == "name_mismatch"`.
- `invalid_tax_ids` = businesses where the compliance `tax_id` does NOT equal the
  linked vendor's `tax_id` (a CROSS-SOURCE mismatch). This is NOT mere string-format
  validation — compare compliance vs vendor records. (Verified: switching from
  format-check to cross-source mismatch raised the score.)
- `expired_license_ids` = `license_expiry < as_of_date` (strict; equal date = not
  expired). Use the review/as_of date from the batch payload.
- `risk_score_override_flags` = businesses with `risk_score >= 70`.

### Decision enum
- Onboarding variant enum: `approve` / `awaiting_information` / `escalate`.
- Account-change variant enum: `release` / `hold` / `escalate`.
- `approve`/`release` ONLY when the business is fully clean: bank verified, license
  valid and present, screening run, no PEP/sanctions/shell, vendor active, tax matches,
  risk below override. (In practice very few qualify — typically one.)
- `escalate` for serious or STACKED issues: confirmed_pep, sanctions/screening problem,
  bank_closed, bank_name_mismatch combined with other issues, shell, vendor on_hold,
  tax mismatch, `risk_score >= 70`, or multiple simultaneous remediable issues.
  (Verified: businesses carrying several issues, or a risk-override, score correct as
  `escalate`, not as the softer `hold`/`awaiting_information`.)
- `awaiting_information` (onboarding) is appropriate when the ONLY problems are benign
  remediable data gaps (missing docs and/or screening_not_run) with no hard red flag.
- `hold` (account-change) is the soft option for a single isolated remediable item;
  prefer `escalate` once issues stack or a hard stop appears.

`follow_up_business_ids` / `review_queue_ids` = every business that is NOT cleanly
released/approved (i.e., all hold/escalate/awaiting). `overall_release_ready` =
true only if EVERY listed business is releasable (almost always false).

---

## 5. Prepaid amortization close (straight-line)

For each scoped prepaid invoice, recognize the period's amortization straight-line from
the invoice's own `monthly_amortization`:
- `months_elapsed_through_close` = inclusive count of months from `service_start`'s
  month through the close month (0 if service starts after the close month).
- `<month>_amortization` = `monthly_amortization` if the close month is within
  `[service_start, service_end]`, else 0.
- `cumulative_amortization_through_<month>` = `monthly_amortization × months_elapsed`,
  capped at `original_amount`. DO NOT "true up" the final service month to force the
  ending to exactly 0 — use the literal monthly figure. A small residual (e.g. ending
  0.01) is EXPECTED and correct. (Verified: adding a final-month true-up lowered the
  score; the plain monthly × months rule is correct.)
- `ending_balance` = `original_amount − cumulative` (≥ 0), 2 decimals.

Per-invoice flags:
- `default_missing_term_flag` = invoice has `"missing_contract_dates"` in
  `data_quality_flags`. (`default_missing_term_invoice_ids` lists these, sorted.)
- `exception_flag` = invoice has ANY non-empty `data_quality_flags` (e.g.
  `rounded_amount` OR `missing_contract_dates`). (`exception_invoice_ids` lists these,
  sorted. Verified: exceptions are ALL flagged invoices, a superset of the
  missing-term set.)

Account rollup (per scoped account, e.g. 1250/1251):
- `account_name` from the GL row; `selected_invoice_count`; and totals = sums of the
  per-invoice `original_amount`, period amortization, cumulative, and ending balance.
- `gl_ending_balance` = the GL row for that account where `period` == close period.
- `variance_amount` = `schedule_ending_balance − gl_ending_balance`.
- `variance_flag` = `abs(variance_amount) > variance_threshold_abs` (threshold from the
  scope payload, e.g. 100.0).
- `has_default_missing_term_flag` = any invoice in the account has the missing-term flag.
- `account_status` working rule: `requires_reconciliation` if the account has a
  default/missing-term invoice; else `variance_review` if `variance_flag`; else
  `reconciled`. (Account-status exact thresholds are the lower-confidence part —
  apply this rule but re-read the template wording.)

Preserve `selected_invoice_ids` and `invoice_results` in the SAME order as the scope
payload (not sorted); sort only the dedicated `_ids` summary lists ascending.

---

## 6. General SOP for any task here

1. Read `prompt.txt` + every file in `payloads/` (scope + `answer_template.json`).
   Identify the period/as_of date, the exact ID set, scoped accounts, thresholds, and
   the required output keys/enums/precision.
2. Treat local snapshots as context; pull CURRENT data from the runner-provided API for
   every entity in scope.
3. Walk the linkage graph (claim→bill→payment, or business→vendor + compliance object,
   or invoice + GL row) and apply the rules above.
4. Derive decisions/flags from raw evidence; do NOT echo source `status`/`review_status`.
5. Build the JSON to the template: correct keys/order, enums spelled exactly, lists
   sorted as specified, USD to the template's precision, no extra keys when
   `additional_properties_allowed:false`.
6. Re-read each template field's `description`/`definition`/`ordering` before finalizing
   — field semantics (e.g. "valid open bills only", "cross-source mismatch",
   "at or above threshold") drive correctness.
