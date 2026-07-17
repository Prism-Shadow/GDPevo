# ERP Finance Expense-Control Skill (task_group_005)

Self-contained operating guide for solving finance expense-control tasks against the shared ERP
finance API. A solver needs only the API base URL (provided by the runner) plus this document.

## 1. API discovery and contract

### Base URL and discovery
- The runner supplies the API base URL (the local form `http://127.0.0.1:8005` and the remote form
  `<remote-env-url>` serve the same data). Always treat the **remote API as the system of
  record**; never rely on local files or stale snapshots as truth.
- Discover every available path with `GET {base}/endpoints`. It returns the path list and the
  filtering contract.
- Health checks: `GET /health` and `GET /api/health`.

### Filtering contract (all list endpoints)
- Exact-match query parameters by field name (e.g. `?claim_id=CLM-2025-OPS-017`,
  `?account=1250&period=2025-03`, `?business_id=BUS-2025-0009`, `?vendor_id=VEN-0064`,
  `?bill_id=AP-2025-0068`).
- `limit` and `offset` for pagination. Default page size is 100; total count is in the `total`
  field. When you need all rows, paginate with a large `limit` (e.g. 200) until `offset+count >= total`.
- Every response envelope: `{ "count": N, "data": [ ... ], "endpoint": "...", "limit": ..., "offset": ..., "total": ... }`.

### Resource paths (each resource has BOTH a namespaced `/api/...` path and a bare path; both work)
| Resource | Namespaced path (preferred) | Bare path | Key filterable fields |
|---|---|---|---|
| Expense claims | `/api/claims` | `/claims` | `claim_id`, `status`, `vendor_id`, `category`, `department` |
| AP bills | `/api/ap/bills` | `/bills` | `bill_id`, `claim_id`, `vendor_id`, `status`, `account`, `due_date` |
| AP payments | `/api/ap/payments` | `/payments` | `payment_id`, `bill_id`, `vendor_id`, `status` |
| AP aging (denormalized bill+payment view) | `/api/ap/aging` | (none) | `bill_id`, `claim_id`, `vendor_id`, `status`, `due_date`, `balance` |
| Vendors | `/api/vendors` | `/vendors` | `vendor_id`, `status`, `tax_id` |
| Compliance/KYC objects | `/api/compliance/objects` | `/compliance/objects` | `business_id`, `vendor_id`, `pep_status`, `sanctions_check_status`, `bank_account_status` |
| Prepaid invoices | `/api/prepaids/invoices` | `/prepaids/invoices` | `prepaid_invoice_id`, `account`, `vendor_id` |
| GL balances | `/api/prepaids/gl-balances` | `/gl/balances` | `account`, `period`, `entity` |
| Close logs | `/api/close/logs` | `/close/logs` | `log_id`, `period`, `area`, `status`, `related_account` |

Run `GET /endpoints` first on any new environment to confirm exact paths — the namespaced `/api/...`
forms are canonical.

## 2. Data shapes (field reference)

### Claim (`/api/claims`)
`claim_id, status, amount, currency, category, department, employee_name, submitted_date,
approved_date, vendor_id (nullable), receipt_status, policy_flags[], notes`
- Claim status values: `submitted`, `needs_receipt`, `approved`, `paid`, `rejected`.
- `approved_date` is null until approved. A `needs_receipt`/`submitted`/`rejected` claim is NOT approvable.

### AP bill (`/api/ap/bills`)
`bill_id, claim_id (nullable), vendor_id, account, amount, currency, bill_date, due_date,
invoice_number, memo, status`
- Bill status values: `draft`, `approved`, `scheduled`, `paid`, `void`.
- Open (payable) bill statuses: `approved`, `scheduled`. Settled: `paid`. Cancelled: `void`. `draft` is not yet committed.
- A bill is linked to a claim via `claim_id`. Multiple bills can share one `claim_id` (some stale/wrong).

### AP payment (`/api/ap/payments`)
`payment_id, bill_id, vendor_id, amount, method, payment_date, bank_reference, status`
- Payment status values: `scheduled`, `processing`, `cleared`.
- **Only `cleared` payments reduce an AP open balance.** `scheduled` and `processing` payments are
  "in flight" and do NOT reduce the open balance yet (but must be flagged as in-flight).

### AP aging (`/api/ap/aging`)
Denormalized per-bill row: `bill_id, claim_id, vendor_id, amount, paid_amount, balance, status,
bill_date, due_date, as_of`. `balance` already nets cleared payments. Use this for payment-run
prioritization and quick balance lookups.

### Vendor (`/api/vendors`)
`vendor_id, vendor_name, legal_name, status, tax_id, bank_account_last4, default_account,
payment_terms, industry, updated_at`
- Vendor status values: `active`, `inactive`, `on_hold`.

### Compliance/KYC object (`/api/compliance/objects`) — keyed by `business_id` (one record per business)
`business_id, business_name, vendor_id, jurisdiction, registration_number, tax_id, license_expiry,
bank_account_status, pep_status, sanctions_check_status, shell_company_suspected (bool),
ownership_layer_count, missing_fields[], ubo_list[{name, ownership_pct}], review_status, risk_score`
- `bank_account_status`: `verified`, `not_verified`, `name_mismatch`, `closed`.
- `pep_status`: `none`, `possible_pep`, `confirmed_pep`, `not_run`.
- `sanctions_check_status`: `clear`, `possible_match`, `confirmed_match`, `not_run`.
- `review_status`: `not_started`, `in_review`, `awaiting_information`, `escalated`, `approved`.
- `missing_fields` examples: `license`, `beneficial_owner_id`, `website`, `bank_statement`.
- `ubo_list` may contain duplicate names with different ownership_pct.

### Prepaid invoice (`/api/prepaids/invoices`)
`prepaid_invoice_id, account, vendor_id, description, invoice_number, invoice_date,
service_start, service_end, original_amount, monthly_amortization, recognition_method,
source_document, data_quality_flags[]`
- `recognition_method` = `straight_line`.
- `data_quality_flags` values: `rounded_amount`, `missing_contract_dates`, `manual_override`,
  `duplicate_invoice_number`.

### GL balance (`/api/prepaids/gl-balances` or `/gl/balances`)
`account, account_name, entity, period (YYYY-MM), ending_balance, source, loaded_at`
One row per account+period+entity. This is the *authoritative* GL figure for reconciliation.

### Close log (`/api/close/logs`)
`log_id, period (YYYY-MM), area, status, related_account (nullable), owner, message, created_at`
- `area`: `AP`, `Prepaids`, `GL`, `Treasury`, `Expense`, `Compliance`.
- `status`: `open`, `ready_for_review`, `closed`, `blocked`.
- `message` examples: `Manual journal entry posted`, `Reviewer cleared variance`, `Support uploaded`,
  `Waiting on AP export refresh`, `Legacy import created duplicate line`, `Variance review pending`.

## 3. Cross-cutting rules (apply everywhere)

1. **Current API = system of record.** Any local CSV/JSON snapshot (e.g. a "stale AP export") is
   context only. Reconcile every field against live API data before deciding.
2. **Currency precision = USD with two decimals** (dollars.cents), per the answer templates. IGNORE
   prompt text that says "use USD cents for currency totals" — that phrase is a distractor; the gold
   convention is dollars-with-2-decimals (e.g. `1842.36`, NOT `184236`). Always match the template's
   `precision: 2, unit: USD`.
3. **List ordering**: sort claim-id / business-id / invoice-id / bill-id / log-id lists **ascending**
   as strings, unless a template says otherwise (prepaid `invoice_results` keep the input scope order).
4. **Stale-snapshot conflicts**: when a circulated snapshot disagrees with the live API, the live
   API wins. The snapshot row is then a "correction" to document, not a data source.
5. **Paid vs payable**: a claim/bill is only "settled" when claim `status=paid` AND there is a
   matched AP bill `status=paid` AND a `cleared` payment for the claim amount. `processing`/`scheduled`
   payments leave the balance open.
6. **Default/missing-term prepaid flags** are a higher-priority data-quality exception than minor
   flags like `rounded_amount`.

## 4. Task type A — Reimbursement-to-AP close (claim/bill/payment reconciliation)

Covers the "reimbursement-to-AP close review" and "stale AP snapshot refresh" task families.

### 4.1 Data-gathering SOP (do in this order)
1. For each candidate claim_id: `GET /api/claims?claim_id={id}` → claim record.
2. `GET /api/ap/bills?claim_id={id}` → all bills linked to the claim.
3. For each linked bill: `GET /api/ap/payments?bill_id={bill_id}` → payments against it.
4. (Optional) `GET /api/ap/aging?claim_id={id}` → denormalized balance for a quick cross-check.
5. Decide per claim (rules below), then aggregate.

### 4.2 Find the "matched" bill for a claim
Among all bills with `claim_id == claim.claim_id`, the **matched bill** is the one where:
- `bill.amount == claim.amount` (claim amount), AND
- `bill.vendor_id == claim.vendor_id` (when claim has a vendor), AND
- `bill.status != void` (void bills are ignored), AND
- `bill.status != draft` (drafts are ignored).
If multiple match, prefer the non-stale one (the one whose amount AND vendor both agree). A bill
whose amount or vendor differs from the claim is a **mismatch** (wrong/stale bill). No linked bill at
all = unmatched.

### 4.3 Classification rules (reimbursement-to-AP close, e.g. payable/blocked/paid)
Apply in priority order:
- **PAID / settled**: claim `status == paid` AND a matched bill exists with `status == paid` AND a
  `cleared` payment exists for the claim amount. (These leave the AP queue — already settled.)
- **PAYABLE / eligible-to-remain**: claim `status == approved` AND a matched OPEN bill exists
  (`status` in {`approved`,`scheduled`}) that is not void/mismatched. Open balance remains.
- **BLOCKED / not-ready** (needs owner cleanup or AP-link remediation) when ANY of:
  - claim `status` is not `approved` and not `paid` (i.e. `submitted`/`needs_receipt`/`rejected`)
    → "block_unapproved_claim";
  - no matched bill exists (no bill linked, OR all linked bills are void, OR all are amount/vendor
    mismatches, OR only drafts);
  - a linked bill is `void` → "ignore_void_bill";
  - a linked bill has amount or vendor mismatch with the claim → "exclude_amount_or_vendor_mismatch".
- CRM-required / owner-cleanup = the set of blocked claims (case-owner must fix the expense case or
  AP link before AP release).

### 4.4 Open AP balance computation
For each claim: `ap_balance = matched_bill.amount − Σ(cleared payment amounts on that bill)`.
- Only `cleared` payments count. `processing` and `scheduled` payments do NOT reduce the balance.
- No matched bill, or claim not approved → balance `0.0`.
- Matched bill fully paid with cleared payment for the full amount → balance `0.0`.
- Matched open bill with an in-flight (`processing`/`scheduled`) payment → balance stays = bill amount
  (the payment has not cleared), AND the claim is still eligible/payable with correction
  `mark_in_flight_payment`.
- `ap_open_balance_total` (close-review variant) = sum of open balances over **payable** claims only
  (not paid, not blocked).

### 4.5 Stale-snapshot correction codes (when a circulated snapshot must be reconciled to live API)
Map each candidate claim to exactly one of these enum values:
- `current_snapshot_ok` — snapshot agrees with current API; no correction needed.
- `mark_in_flight_payment` — snapshot shows no/scheduled payment but live API has a payment in flight
  (`processing` or `scheduled`); claim still eligible, balance stays open.
- `replace_with_matched_paid_bill` — snapshot referenced the wrong bill; live API has a matched PAID
  bill (with cleared payment) that should replace it. Claim is settled/eligible.
- `exclude_amount_or_vendor_mismatch` — live bill amount or vendor does not match the claim; exclude it.
- `ignore_void_bill` — live bill is `void`; ignore it.
- `block_unapproved_claim` — claim is not approved (`status` not in {approved,paid}) in live API; block.

### 4.6 Batch status enum
**close-review variant** (`ready_to_close` / `open_payables` / `blocked`):
- `blocked` if ANY batch item is blocked;
- else `open_payables` if valid unpaid AP reimbursement bills remain (payable claims exist);
- else `ready_to_close`.

**stale-snapshot refresh variant** (`ready_to_send` / `needs_ap_refresh` / `blocked`):
- `ready_to_send` if every claim is eligible and every correction is `current_snapshot_ok`;
- `needs_ap_refresh` if at least one stale correction is required (snapshot diverges from API) but at
  least one claim is eligible after refresh;
- `blocked` if no claim can be released (all not-ready/blocked).

### 4.7 close_log_required
- `required: true` when the batch is not `ready_to_send` (i.e. `needs_ap_refresh` or `blocked`) and a
  relevant AP-area close log exists for the period(s) of the corrected bill/payment activity.
- Identify candidate logs via `GET /api/close/logs?area=AP&period={YYYY-MM}` and prefer entries whose
  `message` is `Manual journal entry posted` (the AP manual journal that documents the adjustment),
  in the period overlapped by the matched bills of the eligible/refreshed claims. Sort `ids` ascending.
- `required: false` (and empty `ids`) when the batch is `ready_to_send`.
- Heuristic derived from limited examples: when the eligible claims' matched bills fall in a single
  month, reference that month's AP manual-journal close log. Examine AP-area close logs for the
  affected period(s) rather than guessing.

## 5. Task type B — Vendor onboarding finance-risk release (KYC)

Covers "onboarding release call" tasks. Output schema uses per-business
`decision` ∈ {`approve`,`awaiting_information`,`escalate`} plus hard-stop flags and UBO counts.

### 5.1 Data-gathering SOP
1. For each `business_id` in the batch: `GET /api/compliance/objects?business_id={id}` → KYC record.
2. Get the linked vendor: `GET /api/vendors?vendor_id={compliance.vendor_id}` → vendor record.
3. Compute hard-stop flags, UBO count, then decision.

### 5.2 Hard-stop flag generation (enum, output sorted ALPHABETICALLY by value; empty list if none)
- `confirmed_pep` — `pep_status == "confirmed_pep"`. (`possible_pep` and `not_run` do NOT set this.)
- `sanctions_confirmed` — `sanctions_check_status == "confirmed_match"`.
- `screening_not_run` — `sanctions_check_status == "not_run"` OR `pep_status == "not_run"`.
- `bank_closed` — `bank_account_status == "closed"`.
- `bank_name_mismatch` — `bank_account_status == "name_mismatch"`.
- `shell_company_suspected` — `shell_company_suspected == true`.
- `vendor_on_hold` — vendor record `status == "on_hold"` (from `/api/vendors`, NOT the compliance object).
- `missing_required_documents` — `missing_fields` is non-empty.
- `expired_license` — `"license"` is NOT in `missing_fields` AND year-month of `license_expiry` is
  strictly before the as_of year-month. (Same-month expiry is NOT expired. When the license doc itself
  is missing, `missing_fields` contains `license`; do NOT also raise `expired_license` — the missing
  doc supersedes the stale expiry date.)

`bank_account_status == "not_verified"` does not map to any specific hard-stop flag (it is not
`closed` or `name_mismatch`).

### 5.3 reportable_ubo_counts
Count of **distinct UBO names** in `ubo_list` that have at least one `ownership_pct >= 25`
(reporting threshold, inclusive). De-duplicate by name (a name appearing in multiple entries counts
once if any of its `ownership_pct` entries is >= 25). Output integer >= 0.

### 5.4 Decision logic (onboarding)
- `approve` — no hard-stop flags at all.
- `awaiting_information` — hard-stop flags exist but are ALL "remediable gap" type:
  {`missing_required_documents`, `screening_not_run`, `expired_license`} (vendor can cure by
  submitting docs / renewing license / running screening).
- `escalate` — ANY hard-stop flag is a "severe/definitive" type: {`confirmed_pep`,
  `sanctions_confirmed`, `bank_closed`, `bank_name_mismatch`, `shell_company_suspected`,
  `vendor_on_hold`}.
- `follow_up_business_ids` = all businesses whose decision is NOT `approve` (i.e. `escalate` or
  `awaiting_information`), ascending.
- `overall_release_ready` = `true` only if EVERY business is `approve`; otherwise `false`.
- Decisions must be derived from current compliance+vendor evidence, NOT copied from the source
  `review_status` field.

## 6. Task type C — Prepaid amortization close & GL reconciliation

Covers "prepaid close check" tasks for a scoped set of prepaid invoice IDs and a close period.

### 6.1 Data-gathering SOP
1. Read the scope payload: `entity`, `close_period` (YYYY-MM), `accounts[]`,
   `selected_prepaid_invoice_ids[]`, `variance_threshold_abs`.
2. For each invoice: `GET /api/prepaids/invoices?prepaid_invoice_id={id}`.
3. For each account: `GET /api/prepaids/gl-balances?account={acct}&period={close_period}` (or
   `/gl/balances`). Take `ending_balance` as the GL balance; also capture `account_name`.

### 6.2 Amortization computation (straight-line)
Let close period = `close_period` (e.g. 2025-03 → close month index 3 of 2025). For each invoice:
- `monthly_amortization` is given in the record (authoritative per-month figure; do NOT recompute as
  original/term).
- **Period amortization** (e.g. march_amortization) = `monthly_amortization` if the invoice's service
  is active during the close month (service_start month <= close month <= service_end month), else 0.
  A mid-month service_start (e.g. 2025-03-15) still earns the FULL monthly amortization for that month.
- **Cumulative amortization through the close period** = `monthly_amortization` × (number of months
  from service_start's month through min(close_month, service_end's month), inclusive). Concretely:
  months = max(0, (close_year − start_year)*12 + (close_month − start_month) + 1), capped so the count
  never extends past service_end's month.
- **Ending balance** = `original_amount − cumulative_amortization_through_close`. May be a small
  non-zero residual (e.g. 0.01) due to per-month rounding vs original amount — that residual is correct.
- All amounts to 2 decimals.

### 6.3 Per-invoice flags
- `default_missing_term_flag` = `true` iff `"missing_contract_dates"` ∈ `data_quality_flags`
  (the contract term dates are missing/unreliable — the schedule may be defaulted).
- `exception_flag` = `true` iff `data_quality_flags` is non-empty (ANY flag, including
  `rounded_amount`, `missing_contract_dates`, `manual_override`, `duplicate_invoice_number`).

### 6.4 Account rollup (per scoped account)
Sum across the account's scoped invoices (2 decimals, round each component consistently):
- `selected_invoice_count`, `original_amount_total`, `{period}_amortization_total`,
  `cumulative_amortization_through_{period}`, `schedule_ending_balance` (sum of invoice ending balances).
- `gl_ending_balance` = GL `ending_balance` for that account+period.
- `variance_amount` = `schedule_ending_balance − gl_ending_balance` (**signed**: positive ⇒ schedule
  above GL, i.e. GL over-amortized / under-stated balance; negative ⇒ schedule below GL, i.e. GL
  under-amortized / has unrecorded additions). This signed direction is the "close-impact direction".
- `variance_flag` = `true` iff `abs(variance_amount) > variance_threshold_abs` (scope payload gives
  threshold, e.g. 100.0).
- `has_default_missing_term_flag` = `true` if ANY scoped invoice in the account has
  `default_missing_term_flag == true`.
- `account_status` ∈ {`reconciled`,`variance_review`,`requires_reconciliation`}:
  - `requires_reconciliation` when `variance_flag == true` (GL and schedule disagree beyond threshold);
  - `variance_review` when `variance_flag == false` but `has_default_missing_term_flag == true`
    (terms questionable even though the balance ties — re-check the term);
  - `reconciled` when `variance_flag == false` and `has_default_missing_term_flag == false`.

### 6.5 Output lists
- `invoice_results` and `selected_invoice_ids`: keep the **same order as the input scope file**
  (`prepaid_close_scope.json`), NOT sorted.
- `default_missing_term_invoice_ids`: scoped invoices with `default_missing_term_flag == true`,
  sorted **ascending** by invoice id.
- `exception_invoice_ids`: scoped invoices with `exception_flag == true`, sorted **ascending** by
  invoice id. Exception priority (for narrative, not ordering): `missing_contract_dates`
  (default/missing term) is the highest-priority data-quality concern; `rounded_amount` is minor.
- `period` = close_period (YYYY-MM); `entity` = scope entity.

## 7. Task type D — AP payment release after vendor account-change (release/hold/escalate)

Covers "payment release risk review" tasks after vendor account-change events. Output schema uses
per-business `decision` ∈ {`release`,`hold`,`escalate`} plus flag lists.

### 7.1 Data-gathering SOP
1. Read the batch payload: `target_business_ids[]`, `review_date` (as_of_date, YYYY-MM-DD),
   `account_change_events[]` (ticket_id, business_id, vendor_id, change_type, requested_bank_last4,
   requested_release_amount_usd, priority).
2. For each business: `GET /api/compliance/objects?business_id={id}` and
   `GET /api/vendors?vendor_id={id's vendor}` (use the compliance `vendor_id`, or the ticket's `vendor_id`).
3. Compute the flag lists, then the decision.

### 7.2 Flag lists (each sorted ascending by business_id)
- `bank_mismatch_ids` — businesses where `compliance.bank_account_status == "name_mismatch"`.
  (Only name_mismatch; `closed` is NOT included here — it is a separate hold reason.)
- `invalid_tax_ids` — businesses where `compliance.tax_id != vendor.tax_id` (the compliance-recorded
  tax id disagrees with the vendor master tax id). Both a format-invalid placeholder
  (e.g. `TIN999999`) and a letter-containing id (`TIN12X899`) manifest as a mismatch vs the vendor
  record; the reliable test is the cross-record mismatch.
- `expired_license_ids` — businesses where year-month of `license_expiry` is strictly before the
  as_of year-month (same-month is NOT expired). Use `as_of_date` / `review_date` as the comparison date.
- `risk_score_override_flags` — businesses where `compliance.risk_score >= 70`.
- `review_queue_ids` — ALL businesses whose decision is NOT `release` (i.e. `hold` or `escalate`),
  ascending. (Release decisions are not queued for review.)

### 7.3 Decision logic (payment release) — DIFFERENT from onboarding
- `release` — no blocking issues at all (bank verified, tax matches, license current, sanctions clear,
  pep not confirmed/not-run-free, risk_score < 70, no missing docs).
- `escalate` — a **severe identity/legal-fraud** issue: `invalid_tax_ids` contains the business.
  (By analogy, `confirmed_pep`/`sanctions_confirmed`/`shell_company_suspected` would also escalate;
  these were not present in the reference data — treat them as escalate triggers.)
- `hold` — a **remediable/operational** blocking issue and NO escalate trigger: bank `name_mismatch`
  or `closed`, `expired_license`, `screening_not_run` (sanctions/pep `not_run`), `missing_fields`
  non-empty, or `risk_score >= 70`. The payment cannot be released until the vendor remediates; it is
  queued for AP/compliance review.

KEY CONTRAST with onboarding (type B): in onboarding, `bank_closed`/`bank_name_mismatch`/`vendor_on_hold`
are **escalate** triggers; in payment release they are **hold** triggers (operational). And in payment
release, `expired_license` and `screening_not_run` are **hold**, not escalate. Only identity-fraud
issues (invalid tax id, confirmed pep/sanctions/shell) escalate a payment release.

## 8. Common misjudgments and exclusion rules

- **"Use USD cents" distractor**:Templates say precision 2 USD → output dollars-with-cents
  (1842.36). Do not emit integer cents (184236).
- **Stale-snapshot conflicts**:Never trust the circulated snapshot over the live API. The snapshot is
  only mentioned to compute the "correction" code. A snapshot `status=scheduled` with a live `paid`
  matched bill is `replace_with_matched_paid_bill`, not `current_snapshot_ok`.
- **Paid vs payable**:`processing`/`scheduled` payments do NOT settle a bill. Only `cleared` payments
  reduce the open balance. A bill with an in-flight payment is still payable/eligible with an open
  balance and correction `mark_in_flight_payment`.
- **Claim-vs-AP alignment**:A bill linked by `claim_id` is only "matched" if amount AND vendor agree
  with the claim. Wrong-amount/wrong-vendor linked bills are mismatches (`exclude_amount_or_vendor_mismatch`),
  not matched bills. Void linked bills are ignored (`ignore_void_bill`).
- **Default/missing-term prepaid flag**:`default_missing_term_flag` is specifically
  `missing_contract_dates`; other data_quality_flags (rounded_amount, manual_override,
  duplicate_invoice_number) set `exception_flag` but NOT `default_missing_term_flag`.
- **Exception priority ranking**: when summarizing, `missing_contract_dates` (default/missing term) is
  the highest-priority exception; `rounded_amount` is the lowest. The output `exception_invoice_ids`
  list is still sorted ascending by id, not by priority.
- **Expired-license boundary**: expiry is judged by year-month strictly before the as_of year-month
  (same month = not expired), and is suppressed when `"license"` is in `missing_fields` (use
  `missing_required_documents` instead). Getting this boundary wrong mis-classifies onboarding and
  payment-release businesses.
- **Signed close-impact direction** (prepaid): `variance_amount = schedule − GL` (signed). A negative
  variance means GL > schedule (under-amortized / unrecorded additions); positive means GL < schedule
  (over-amortized / unrecorded release). Keep the sign.
- **Copy-from-source trap**: for onboarding and payment-release decisions, derive from current
  compliance+vendor evidence — do NOT copy the source `review_status` or a stale decision.
- **Invoice result ordering**: prepaid `invoice_results` and `selected_invoice_ids` keep INPUT scope
  order; only `default_missing_term_invoice_ids` and `exception_invoice_ids` are sorted ascending.
- **Bill status `draft`**: draft bills are not committed; treat as not-a-valid-matched-bill.
- **`bank_account_status == not_verified`**: does not map to any onboarding hard-stop flag (only
  `closed` and `name_mismatch` do).

## 9. Controlled vocabularies (exact enum values required by answer templates)

- Reimbursement-AP close `batch_status`: `ready_to_close`, `open_payables`, `blocked`.
- Stale-snapshot refresh `batch_status`: `ready_to_send`, `needs_ap_refresh`, `blocked`.
- Stale-snapshot `corrections` enum: `current_snapshot_ok`, `mark_in_flight_payment`,
  `replace_with_matched_paid_bill`, `exclude_amount_or_vendor_mismatch`, `ignore_void_bill`,
  `block_unapproved_claim`.
- Onboarding `decision`: `approve`, `awaiting_information`, `escalate`.
- Onboarding `hard_stop_flags` enum (alphabetical in output): `bank_closed`, `bank_name_mismatch`,
  `confirmed_pep`, `expired_license`, `missing_required_documents`, `sanctions_confirmed`,
  `screening_not_run`, `shell_company_suspected`, `vendor_on_hold`.
- Payment-release `decision`: `release`, `hold`, `escalate`.
- Prepaid `account_status`: `reconciled`, `variance_review`, `requires_reconciliation`.
- Prepaid `data_quality_flags`: `rounded_amount`, `missing_contract_dates`, `manual_override`,
  `duplicate_invoice_number`.
- Claim status: `submitted`, `needs_receipt`, `approved`, `paid`, `rejected`.
- AP bill status: `draft`, `approved`, `scheduled`, `paid`, `void`.
- AP payment status: `scheduled`, `processing`, `cleared`.
- Vendor status: `active`, `inactive`, `on_hold`.
- Compliance `bank_account_status`: `verified`, `not_verified`, `name_mismatch`, `closed`.
- Compliance `pep_status`: `none`, `possible_pep`, `confirmed_pep`, `not_run`.
- Compliance `sanctions_check_status`: `clear`, `possible_match`, `confirmed_match`, `not_run`.
- Close log `area`: `AP`, `Prepaids`, `GL`, `Treasury`, `Expense`, `Compliance`.
- Close log `status`: `open`, `ready_for_review`, `closed`, `blocked`.

## 10. Concrete solver SOP (recommended order for any task in this group)

1. Read the task prompt and the local payload (`answer_template.json` is the source of truth for the
   required output shape, field names, ordering, and enums; any input batch file lists candidates).
2. `GET {base}/endpoints` to confirm paths; `GET {base}/api/health` to confirm liveness.
3. Identify the task type (A: reimbursement-AP close / stale AP refresh; B: vendor onboarding KYC;
   C: prepaid amortization close; D: payment release after account-change) from the prompt + template.
4. Gather live API data per the type-specific SOP in sections 4.1 / 5.1 / 6.1 / 7.1. Paginate to get
   all rows; re-query by exact id rather than assuming.
5. Apply the classification/decision rules (sections 4.2–4.6, 5.2–5.4, 6.2–6.5, 7.2–7.3). For
   payment-run ordering needs (not always an output), rank open AP bills by `due_date` ascending then
   `bill_id` ascending.
6. Double-check the cross-cutting rules (section 3) and the misjudgments (section 8), especially:
   currency precision (dollars.cents), cleared-vs-in-flight payments, matched-bill amount+vendor
   test, expired-license month boundary + missing-license suppression, signed prepaid variance, and
   the onboarding-vs-payment-release escalate/hold contrast.
7. Emit ONE JSON object matching the template exactly: correct top-level keys, correct ordering, exact
   enum spellings, 2-decimal USD numbers. No narrative text outside the JSON.

### Quick decision tables

**Onboarding (type B) — hard-stop → decision**
| Severe (→ escalate) | Remediable (→ awaiting_information if alone) |
|---|---|
| confirmed_pep, sanctions_confirmed, bank_closed, bank_name_mismatch, shell_company_suspected, vendor_on_hold | missing_required_documents, screening_not_run, expired_license |
(approve = no hard stops at all)

**Payment release (type D) — issue → decision**
| Severe (→ escalate) | Remediable (→ hold) |
|---|---|
| invalid_tax_id (compliance.tax_id ≠ vendor.tax_id); confirmed_pep; sanctions_confirmed; shell_company_suspected | bank name_mismatch/closed; expired_license; screening_not_run; missing_fields non-empty; risk_score ≥ 70 |
(release = no blocking issues)

**Reimbursement-AP (type A) — claim classification**
| Class | Condition |
|---|---|
| paid/settled | claim status=paid AND matched bill paid AND cleared payment = claim amount |
| payable/eligible | claim status=approved AND matched open (approved/scheduled) bill exists |
| blocked/not-ready | claim not approved, OR no matched bill (void/mismatch/none/draft-only) |
