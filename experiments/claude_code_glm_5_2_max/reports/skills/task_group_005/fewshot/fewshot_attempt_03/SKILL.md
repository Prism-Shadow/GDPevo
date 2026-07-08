# ERP Finance Expense-Control Skill (task_group_005)

A self-contained playbook for solving ERP finance expense-control tasks against the shared
remote API. The solver only needs the remote API base URL (provided per task in
`environment_access.md` or the prompt). Discover everything else from the API itself.

> NEVER call any `/api/judge` endpoint. NEVER read local `env/` sources, evaluator files, or
> test/train answer keys. The remote API is the only system of record. Staged local payloads
> (answer templates, batch/scope files, stale CSVs) are inputs only.

---

## 1. API access & discovery contract

- **Base URL:** the runner-provided remote URL (e.g. `<remote-env-url>`). Prompts may
  also mention `http://127.0.0.1:8005`; always use the remote URL from `environment_access.md`.
- **Discover endpoints:** `GET {base}/endpoints` returns the list of paths and the filtering
  contract. Health: `GET /health`, `GET /api/health`.
- **Filtering:** list endpoints accept **exact-match query parameters by field name**, plus
  `limit` and `offset` for pagination. Default limit is 100. There is no fuzzy/partial matching.
- **Namespaced vs bare paths:** most resources exist under BOTH a namespaced `/api/...` path and
  a bare root path (aliases). Prefer the `/api/...` form. Known pairs:
  - `/api/claims` == `/claims`
  - `/api/ap/bills` == `/bills`
  - `/api/ap/payments` == `/payments`
  - `/api/ap/aging` (aging view, no bare alias documented)
  - `/api/vendors` == `/vendors`
  - `/api/compliance/objects` == `/compliance/objects`
  - `/api/prepaids/invoices` == `/prepaids/invoices`
  - `/api/prepaids/gl-balances` == `/gl/balances`
  - `/api/close/logs` == `/close/logs`
- **Response shape (every list endpoint):** `{ "count", "data": [...], "endpoint", "limit",
  "offset", "total" }`. Read `data`; use `total`/`offset` to paginate when a set may exceed 100.

### Endpoint catalog (key fields)

| Resource | Filterable keys (used) | Key fields returned |
|---|---|---|
| `/api/claims` | `claim_id` | `claim_id, status, amount, currency, vendor_id, department, category, receipt_status, policy_flags, submitted_date, approved_date, notes` |
| `/api/ap/bills` | `bill_id`, `claim_id`, `status`, `vendor_id` | `bill_id, claim_id, vendor_id, account, amount, currency, status, bill_date, due_date, invoice_number, memo` |
| `/api/ap/payments` | `payment_id`, **`bill_id`** (NOT `claim_id`) | `payment_id, bill_id, vendor_id, amount, status, method, payment_date, bank_reference` |
| `/api/ap/aging` | `bill_id`, `status`, `vendor_id`, `claim_id` | `bill_id, claim_id, vendor_id, amount, paid_amount, balance, status, bill_date, due_date, as_of` |
| `/api/vendors` | `vendor_id` (NOT `business_id`) | `vendor_id, vendor_name, legal_name, status, tax_id, bank_account_last4, payment_terms, default_account, industry, updated_at` |
| `/api/compliance/objects` | `business_id`, `vendor_id` | `business_id, business_name, vendor_id, review_status, risk_score, bank_account_status, tax_id, license_expiry, pep_status, sanctions_check_status, shell_company_suspected, ownership_layer_count, missing_fields, ubo_list[{name,ownership_pct}]` |
| `/api/prepaids/invoices` | `prepaid_invoice_id`, `account`, `vendor_id` | `prepaid_invoice_id, account, vendor_id, original_amount, monthly_amortization, recognition_method, service_start, service_end, invoice_date, invoice_number, data_quality_flags, description, source_document` |
| `/api/prepaids/gl-balances` | `account`, `entity`, `period` | `account, account_name, entity, period, ending_balance, loaded_at, source` |
| `/api/close/logs` | `log_id`, `area`, `period`, `status` | `log_id, area, period, status, message, owner, related_account, created_at` |

### Linking keys (critical — most mistakes come from wrong joins)

- **Claim → AP bill:** join on `claim_id` (bills carry `claim_id`; some bills have `claim_id: null`).
- **AP bill → payment:** join on **`bill_id`**. Payments do NOT carry `claim_id` (filtering
  payments by `claim_id` returns 0). To get all payments for a claim: claim → bills(`claim_id`)
  → payments(`bill_id` for each bill).
- **Compliance → vendor:** compliance object carries BOTH `business_id` and `vendor_id`. Fetch
  the vendor with `/api/vendors?vendor_id=<compliance.vendor_id>`. Vendors are NOT filterable by
  `business_id`.
- **Account-change batch → compliance/vendor:** the batch payload lists `business_id` per ticket
  (and `vendor_id` and `requested_bank_last4`). Use `business_id` to pull compliance, then
  `vendor_id` to pull the vendor master.
- **Prepaid invoice → GL:** both share `account` (+ `entity` + `period` on GL). GL balances are
  keyed by (account, entity, period).

---

## 2. Task archetypes & SOPs

Five recurring archetypes appear in this group. Identify which one a prompt asks for by its
answer template, then follow the matching SOP. Always return a single JSON object matching the
provided `answer_template.json` (key names, ordering, types, enums, and precision matter).

### Archetype A — Reimbursement-to-AP close (claim triage)
Template fields: `payable_claim_ids, blocked_claim_ids, paid_claim_ids, ap_open_balance_total,
crm_required_claim_ids, batch_status, reviewed_claim_count`.

**SOP — for each candidate `claim_id` (in the prompt's batch):**
1. `GET /api/claims?claim_id=<id>` → claim record (`status, amount, vendor_id`).
2. `GET /api/ap/bills?claim_id=<id>` → all bills linked to the claim.
3. For each bill, `GET /api/ap/payments?bill_id=<bill_id>` → payments.
4. Classify the claim:
   - **Paid** — there is a *matching* AP bill where `bill.amount == claim.amount` AND
     `bill.vendor_id == claim.vendor_id` AND (`bill.status == "paid"` OR a payment with
     `status == "cleared"` exists for the full amount). (Claim `status == "paid"` corroborates.)
   - **Payable** — claim is approved (`status == "approved"`) AND there is a valid OPEN AP bill:
     `bill.status` in `{scheduled, approved}` (not void/paid), and `bill.amount`/`bill.vendor_id`
     match the claim. The bill has an outstanding (not fully cleared) balance.
   - **Blocked** — everything else: claim not approved, OR no AP bill, OR bill is `void`, OR
     `bill.amount != claim.amount`, OR `bill.vendor_id != claim.vendor_id`.
5. `ap_open_balance_total` = sum over **payable** claims of `bill.amount − cleared_payment_total`
   (only payments with `status == "cleared"` reduce the balance; `processing`/`scheduled`
   payments do NOT). Blocked and paid claims contribute 0. Use 2 decimals.
6. `crm_required_claim_ids` = blocked claims (they need expense-case owner cleanup or AP-link
   remediation). Sorted ascending.
7. `batch_status`: `"blocked"` if any claim is blocked; else `"open_payables"` if any payable
   claim remains; else `"ready_to_close"`.
8. `reviewed_claim_count` = number of claim IDs in the requested batch. All ID lists ascending.

### Archetype B — Stale-snapshot AP batch (eligibility + corrections)
Template fields: `eligible_claim_ids, not_ready_claim_ids, ap_balance_by_claim,
stale_snapshot_corrections, close_log_required, batch_status`.

The staged CSV (`stale_ap_snapshot.csv`) is a CIRCULATED EXPORT, not the system of record. Treat
it as context; reconcile every candidate against the live API.

**SOP — for each candidate claim:**
1. Pull live claim + bills + payments (same as Archetype A). Also read the CSV row for that claim.
2. Decide eligibility to STAY in the batch:
   - **Eligible** — claim is approved AND has a valid matching AP bill (non-void, amount & vendor
     match). This includes a fully paid/matched claim (balance 0) and an open/in-flight payable.
   - **Not ready** — claim not approved, or bill void, or amount/vendor mismatch, or no valid bill.
3. `ap_balance_by_claim` (one entry per candidate claim): for eligible claims, open balance =
   valid matched bill amount − cleared payments (in-flight/processing payments do NOT reduce it);
   for not-ready claims, `0.0`.
4. `stale_snapshot_corrections` — pick ONE enum per candidate by comparing CSV vs live API, in
   this precedence:
   1. `block_unapproved_claim` — claim `status != "approved"` (e.g. `needs_receipt`,
      `rejected`, `submitted`; `approved_date` null).
   2. `ignore_void_bill` — the linked bill `status == "void"`.
   3. `exclude_amount_or_vendor_mismatch` — bill exists & non-void but `bill.amount !=
      claim.amount` OR `bill.vendor_id != claim.vendor_id`.
   4. `replace_with_matched_paid_bill` — CSV shows a scheduled/old bill but the live API has a
      DIFFERENT bill that matches the claim and is `paid` with a cleared payment.
   5. `mark_in_flight_payment` — CSV shows no payment (or `none`/0) but live API has a payment in
      `processing`/`scheduled` (in-flight, not yet cleared).
   6. `current_snapshot_ok` — CSV and live API agree (no correction needed).
5. `close_log_required`: `{required: bool, ids: [...]}`.
   - `required = true` when the batch needs correction/refresh (any correction that is not
     `current_snapshot_ok`, equivalently when `batch_status != "ready_to_send"`).
   - `ids` = AP-area close logs that document a manual AP correction superseding the stale export:
     `GET /api/close/logs?area=AP` (optionally scoped to the period(s) of the batch's AP bills)
     and select logs whose `message == "Manual journal entry posted"`. Sorted ascending by
     `log_id`. Empty list if none.
6. `batch_status`: `"ready_to_send"` if all candidates eligible and every correction is
   `current_snapshot_ok`; `"blocked"` if zero candidates are eligible (all not-ready); otherwise
   `"needs_ap_refresh"` (mixed eligible + corrections needed).

### Archetype C — Vendor onboarding / KYC release
Template fields: `per_business[{business_id, decision}], reportable_ubo_counts,
hard_stop_flags, follow_up_business_ids, overall_release_ready`.

**SOP — for each `business_id` in the onboarding batch:**
1. `GET /api/compliance/objects?business_id=<id>` → compliance record; get `vendor_id`.
2. `GET /api/vendors?vendor_id=<vendor_id>` → vendor master.
3. Determine `as_of_date` from the batch payload.
4. Build `hard_stop_flags` (alphabetical, empty list if none) per the table in §4.
5. Compute `reportable_ubo_counts[business_id]` = number of DISTINCT `ubo_list` names whose
   **aggregated (summed across all entries for that name) `ownership_pct >= 25`**. Deduplicate by
   name. Whole number ≥ 0.
6. `decision`:
   - `approve` — no hard stop flags at all.
   - `awaiting_information` — hard stops present but EVERY one is a remediable/info flag
     (`missing_required_documents`, `screening_not_run`).
   - `escalate` — at least one SEVERE hard stop (`confirmed_pep`, `sanctions_confirmed`,
     `bank_closed`, `bank_name_mismatch`, `expired_license`, `shell_company_suspected`,
     `vendor_on_hold`).
7. `follow_up_business_ids` = businesses with `decision != "approve"` (escalate or
   awaiting_information), ascending.
8. `overall_release_ready` = `true` only if EVERY business is `approve`.

### Archetype D — Prepaid amortization & GL reconciliation
Template fields: `period, entity, selected_invoice_ids, account_rollup{...},
invoice_results[{...}], default_missing_term_invoice_ids, exception_invoice_ids`.

Inputs come from a `prepaid_close_scope.json`: `entity, close_period (YYYY-MM), accounts,
selected_prepaid_invoice_ids, variance_threshold_abs`.

**SOP:**
1. `period` = scope `close_period`; `entity` = scope `entity`; `selected_invoice_ids` = scope
   list **in the same order** (do NOT re-sort these two arrays; the scope order is required).
2. For each scoped invoice: `GET /api/prepaids/invoices?prepaid_invoice_id=<id>`.
3. Compute, for the close period `P` (e.g. 2025-03, treat as year=2025, month=3):
   - `months_through_P` = clamp( (Py*12+Pm) − (start_y*12+start_m) + 1, 0, total_term_months )
     where `total_term_months` = (end_y*12+end_m) − (start_y*12+start_m) + 1.
     (Counting is by calendar month inclusive of start and end months; mid-month start dates
     still count the start month as a full month — NOT prorated by day.)
   - `<period>_amortization` = `monthly_amortization` if P's month is within
     [start month … end month] inclusive, else `0`.
   - `cumulative_amortization_through_<P>` = `monthly_amortization × months_through_P`, 2 decimals.
   - `ending_balance` = `original_amount − cumulative_amortization_through_P`, 2 decimals
     (may be a small rounding residual like `0.01`; do NOT clamp to 0).
   - `default_missing_term_flag` = `("missing_contract_dates" in data_quality_flags)`.
   - `exception_flag` = `(data_quality_flags is non-empty)` — ANY data-quality flag is an exception.
4. `account_rollup[account]` (one entry per scope account) — aggregate the invoices whose
   `account` matches:
   - `account_name`, `selected_invoice_count`, `original_amount_total`, `<period>_amortization_total`,
     `cumulative_amortization_through_<P>`, `schedule_ending_balance` (sums of the per-invoice
     values; 2 decimals).
   - `gl_ending_balance` = `GET /api/prepaids/gl-balances?account=<acct>&entity=<entity>&period=<P>`
     → `ending_balance`.
   - `variance_amount` = `schedule_ending_balance − gl_ending_balance` (SIGNED; positive = schedule
     over GL, negative = GL over schedule). This is the "signed close-impact direction."
   - `variance_flag` = `abs(variance_amount) > variance_threshold_abs` (from scope).
   - `has_default_missing_term_flag` = any invoice in the account has `default_missing_term_flag == true`.
   - `account_status`: `"reconciled"` if `variance_flag == false` AND
     `has_default_missing_term_flag == false`; otherwise `"requires_reconciliation"`.
     (`"variance_review"` is a reserved intermediate value; when variance_flag is true the
     demonstrated, safe choice is `requires_reconciliation`.)
5. `default_missing_term_invoice_ids` = invoices with `default_missing_term_flag == true`,
   ascending. `exception_invoice_ids` = invoices with `exception_flag == true`, ascending.

### Archetype E — Account-change payment release (compliance-gated)
Template fields: `task_id, batch_id, as_of_date, target_business_ids, decisions,
bank_mismatch_ids, invalid_tax_ids, expired_license_ids, review_queue_ids,
risk_score_override_flags` (these identifiers/`task_id`/`batch_id`/`as_of_date` come from the
account-change batch payload).

**SOP — for each `business_id` (use the batch `review_date`/`as_of_date`, e.g. 2025-06-01):**
1. `GET /api/compliance/objects?business_id=<id>`; then `GET /api/vendors?vendor_id=<vendor_id>`.
2. Compute per-business booleans:
   - `bank_mismatch` = `compliance.bank_account_status == "name_mismatch"`.
   - `bank_closed` = `compliance.bank_account_status == "closed"`.
   - `invalid_tax` = `compliance.tax_id != vendor.tax_id` (compliance-vs-vendor mismatch).
   - `expired_license` = license expired vs `as_of_date` per the month rule in §5 (AND `"license"`
     not in `missing_fields`; a missing license is an info gap, not an expiry).
   - `risk_override` = `compliance.risk_score >= 70`.
3. Aggregate lists (ascending): `bank_mismatch_ids` = business_ids with `bank_mismatch` (name
   mismatch ONLY; `closed` does NOT go in this list). `invalid_tax_ids`, `expired_license_ids` =
   their respective booleans. `risk_score_override_flags` = `risk_override` business_ids.
4. `decisions[business_id]` (precedence — first match wins):
   1. `escalate` — if `invalid_tax` is true (tax mismatch = highest-severity fraud signal).
   2. `hold` — if any of `bank_mismatch`, `bank_closed`, `expired_license`, `risk_override` is true.
   3. `release` — otherwise (no compliance issues at all).
5. `review_queue_ids` = all business_ids with `decision != "release"` (i.e. hold or escalate),
   ascending.

### Archetype F — Payment release board / payment-run priority
(When a prompt asks to sequence open AP bills into a payment run, rank by due date.)
1. Pull open bills: `GET /api/ap/aging?status=scheduled` and `?status=approved` (or pull all and
   filter to those with `balance > 0` and `status` in `{approved, scheduled}` — i.e. NOT `paid`,
   `void`, or `draft`-only).
2. Rank **ascending by `due_date`, then ascending by `bill_id`** as the tiebreaker. The earliest
   due date is highest payment priority.
3. Optionally enrich with vendor (`/api/vendors?vendor_id=`) for payment_terms/bank info, and
   payment evidence (`/api/ap/payments?bill_id=`) to confirm no cleared payment exists. Payments
   that are `cleared` already should have `balance == 0` and be excluded; `processing` payments
   mean the bill is in-flight (treat balance as still open unless the task says otherwise).

---

## 3. Output field definitions & required enums

Use EXACTLY these enum values (matching the answer templates). Lists must be sorted as the
template specifies (usually ascending by ID). Currency: 2 decimals USD unless the template says
otherwise (one Reimbursement-to-AP template asks for "USD cents" — follow that template's unit
field literally).

**Archetype A — batch_status:** `ready_to_close` | `open_payables` | `blocked`.
**Archetype B — stale_snapshot_corrections:** `current_snapshot_ok` | `mark_in_flight_payment` |
`replace_with_matched_paid_bill` | `exclude_amount_or_vendor_mismatch` | `ignore_void_bill` |
`block_unapproved_claim`. **batch_status:** `ready_to_send` | `needs_ap_refresh` | `blocked`.
**close_log_required:** `{required: bool, ids: [log_id, ...]}`.
**Archetype C — decision:** `approve` | `awaiting_information` | `escalate`. **hard_stop_flags
enum:** `bank_closed` | `bank_name_mismatch` | `confirmed_pep` | `expired_license` |
`missing_required_documents` | `sanctions_confirmed` | `screening_not_run` |
`shell_company_suspected` | `vendor_on_hold` (alphabetical within each list; empty list if none).
**Archetype D — account_status:** `reconciled` | `variance_review` | `requires_reconciliation`.
**Prepaid data_quality_flags observed:** `duplicate_invoice_number` | `manual_override` |
`missing_contract_dates` | `rounded_amount`.
**Archetype E — decision:** `release` | `hold` | `escalate`.
**Domain enum values (from the API) for reference:** claim `status` ∈
`{approved, needs_receipt, paid, rejected, submitted}`; claim `receipt_status` ∈
`{attached, missing, partial}`; bill `status` ∈ `{approved, draft, paid, scheduled, void}`;
payment `status` ∈ `{cleared, processing, scheduled}`; payment `method` ∈
`{ACH, Check, Virtual card, Wire}`; vendor `status` ∈ `{active, inactive, on_hold}`;
compliance `bank_account_status` ∈ `{closed, name_mismatch, not_verified, verified}`;
`pep_status` ∈ `{confirmed_pep, none, not_run, possible_pep}`; `sanctions_check_status` ∈
`{clear, confirmed_match, not_run, possible_match}`; `review_status` ∈
`{approved, awaiting_information, escalated, in_review, not_started}`; close-log `area` ∈
`{AP, Compliance, Expense, GL, Prepaids, Treasury}`; close-log `status` ∈
`{blocked, closed, open, ready_for_review}`; close-log `message` ∈
`{Legacy import created duplicate line, Manual journal entry posted, Reviewer cleared variance,
Support uploaded, Variance review pending, Waiting on AP export refresh}`.

---

## 4. Compliance → hard_stop_flags mapping (Archetype C)

Build the alphabetical list from these field checks (all use the COMPLIANCE object unless noted;
each maps to one hard_stop enum value):

| hard_stop enum | Trigger condition |
|---|---|
| `bank_closed` | `compliance.bank_account_status == "closed"` |
| `bank_name_mismatch` | `compliance.bank_account_status == "name_mismatch"` |
| `confirmed_pep` | `compliance.pep_status == "confirmed_pep"` |
| `expired_license` | license expired vs as_of (§5 month rule) AND `"license"` NOT in `compliance.missing_fields` |
| `missing_required_documents` | `compliance.missing_fields` is non-empty |
| `sanctions_confirmed` | `compliance.sanctions_check_status == "confirmed_match"` |
| `screening_not_run` | `compliance.pep_status == "not_run"` OR `compliance.sanctions_check_status == "not_run"` |
| `shell_company_suspected` | `compliance.shell_company_suspected == true` |
| `vendor_on_hold` | `vendor.status == "on_hold"` (VENDOR master) |

Notes:
- `possible_pep` / `possible_match` do NOT set a hard stop (they are inconclusive, not confirmed).
- A license that is `missing` (in `missing_fields`) sets `missing_required_documents`, NOT
  `expired_license` (suppress the expiry flag in that case).
- `bank_account_status == "not_verified"` is not a hard_stop in the enum; treat as a soft flag
  (does not by itself block — but if other evidence is missing it may surface via
  `missing_required_document`-type logic). When in doubt, only set the enumerated hard stops above.

---

## 5. Computation rules that are easy to get wrong

- **License expiry — MONTH granularity:** a license is expired when the calendar MONTH of
  `license_expiry` is STRICTLY BEFORE the calendar month of `as_of_date`. Equivalently, a license
  stays valid through the LAST DAY of its expiry month. Compare `YYYY-MM(license_expiry) <
  YYYY-MM(as_of_date)`. (A license expiring 2025-05-17 is NOT expired as of 2025-05-31 — same
  month — but IS expired as of 2025-06-01 — next month.) Suppress when `"license"` ∈
  `missing_fields` (then it is `missing_required_documents`, not expired).
- **Reportable UBO count:** aggregate (SUM) `ownership_pct` across ALL entries that share the
  SAME `name` (the same person can appear at multiple ownership layers); count DISTINCT names
  whose aggregated ownership is **≥ 25%**. Do not double-count names; do not count names below 25%.
- **Tax validity (Archetype E):** `invalid_tax` = `compliance.tax_id != vendor.tax_id`
  (compliance record vs vendor master). A placeholder/malformed compliance tax_id will typically
  also mismatch the vendor tax_id; the robust test is the cross-record mismatch.
- **Open AP balance:** only `cleared` payments reduce the open balance. `processing` and
  `scheduled` payments are in-flight and do NOT reduce it. `void` bills contribute 0. For
  not-ready/blocked claims (no valid matched bill), the balance is `0.0`.
- **Prepaid amortization:** always use the stored `monthly_amortization` field × full calendar
  months (no day-proration). `ending_balance = original_amount − cumulative`; keep rounding
  residuals (e.g. `0.01`) — do NOT force to 0. A bill whose service period ends exactly at the
  close month fully amortizes (cumulative may equal original minus a 0.01 residual).
- **Variance sign:** `variance_amount = schedule_ending_balance − gl_ending_balance` (signed,
  per template definition). Negative means GL exceeds the schedule; positive means schedule
  exceeds GL. `variance_flag` uses `abs(variance_amount) > variance_threshold_abs`.
- **Batch status precedence (A):** blocked (any blocked claim) > open_payables (any payable) >
  ready_to_close. **(E) decision precedence:** invalid_tax→escalate > (mismatch/closed/expired/
  risk)→hold > release.
- **ID list ordering:** sort claim/bill/business/log/invoice ID lists ascending as strings
  unless the template says otherwise (Archetype D's `selected_invoice_ids`/`invoice_results`
  keep the SCOPE order, not sorted).

---

## 6. Common misjudgments & exclusion rules

- **Stale-snapshot conflict (Archetype B):** the circulated CSV is NOT the system of record. A
  CSV row showing `payment_status=none` while the live API shows a `processing` payment means
  `mark_in_flight_payment` (the balance is still open). A CSV showing a `scheduled` bill while
  the live API shows a different, matched, `paid`+cleared bill means `replace_with_matched_paid_bill`
  (balance 0). Never trust the CSV amounts/statuses over the API.
- **Paid vs payable (Archetypes A/B):** a claim with a matching `paid` bill + `cleared` payment
  is PAID (balance 0), not payable. A scheduled/processing payment does NOT make a claim "paid."
- **Claim-vs-AP alignment:** the link is `claim_id` (claim→bill) then `bill_id` (bill→payment).
  Do not join payments to claims directly (no shared key). A bill is "valid" for a claim only if
  amount AND vendor match AND status is not void/draft. Mismatched amount or vendor → block/exclude.
- **Bill status `void`:** a void bill is ignored entirely (open balance 0; correction
  `ignore_void_bill`). `draft` bills are not valid open AP either.
- **Bank "closed" vs "name_mismatch" (Archetype E):** `bank_mismatch_ids` contains ONLY
  `name_mismatch` businesses. A `closed` bank still drives a `hold` decision but is NOT listed in
  `bank_mismatch_ids`.
- **License in missing_fields:** do not double-flag as expired; it is a missing-document issue.
- **PEP/sanctions "possible_*":** inconclusive — not a hard stop. Only `confirmed_pep` and
  `confirmed_match` block.
- **UBO duplicates:** the same name at multiple layers must be SUMMED then tested against 25%,
  not counted per entry.
- **Exception vs default-missing-term (Archetype D):** `default_missing_term_flag` is specifically
  `missing_contract_dates`; `exception_flag` is ANY data-quality flag. An invoice can be an
  exception (e.g. `rounded_amount`) without being a default-missing-term invoice.
- **Exception priority / list ordering:** `default_missing_term_invoice_ids` ⊆
  `exception_invoice_ids` (a missing-term invoice is always also an exception). Both lists sorted
  ascending; do not dedupe across the two fields (they are separate outputs).
- **Signed close-impact direction:** report `variance_amount` with its sign (schedule − GL).
  Flipping the sign is a common error.
- **reviewed_claim_count (Archetype A):** count the CLAIMS IN THE REQUESTED BATCH (from the
  prompt), not the number of bills/payments returned.

---

## 7. Recommended query order (general)

1. `GET /endpoints` once to confirm available paths (cache it).
2. Read the task's staged payload (`answer_template.json` is the contract; batch/scope/CSV files
   are inputs). Identify the archetype from the template fields.
3. Fetch the candidate entities (claims/businesses/invoices) and ALL their linked records BEFORE
   classifying — a claim can have multiple bills, a bill can have multiple payments, a business
   has both a compliance object and a vendor record.
4. Classify per the archetype SOP, applying the precedence rules in §5.
5. Round currency to 2 decimals; sort ID lists per template; emit exactly the template's keys
   with the exact enum strings. Return one JSON object only (no narrative).
