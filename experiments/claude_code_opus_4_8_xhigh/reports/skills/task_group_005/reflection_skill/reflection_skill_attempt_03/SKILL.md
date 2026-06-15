---
name: erp-finance-close-tasks
description: >-
  Solve ERP finance "close / release" tasks against the shared local finance JSON API.
  Use this whenever a task asks you to decide statuses for a batch of expense claims, AP bills,
  payments, vendor onboarding/intake compliance, prepaid-to-GL close reconciliation, a stale AP
  snapshot reconciliation, or AP payment release after vendor account changes, and to return a
  JSON object matching a provided answer_template.json. Triggers include prompts mentioning
  claims/CLM-*, AP bills/AP-*, payments, vendors/BUS-*, compliance hard-stops/UBO, prepaid
  amortization/variance, GL balances, close logs, "payable/blocked/paid", "release/hold/escalate",
  "eligible/not_ready", or a base URL like 127.0.0.1:8005 / 127.0.0.1:8029. Use it even when the
  task only says "reconcile" or "release call" without naming the API.
---

# ERP Finance Close / Release Tasks

These tasks give you a short prompt, one or more payloads (a batch list, a CSV snapshot, a scope
file), and an `answer_template.json`. You must read live data from a shared ERP finance JSON API,
apply finance business rules, and return JSON that conforms exactly to the template. The grader
checks your fields against an official answer, so precision on enums, units, sorting, and inclusion
rules matters more than narrative.

## 0. Golden rules (the mistakes that cost points)

1. **The answer_template is the contract, not the prompt.** When the prompt and the template
   disagree on a detail, follow the template. The clearest example: a prompt may say "use USD
   cents," but if the template field declares `"unit": "USD", "precision": 2`, return **dollars
   with 2 decimals** (e.g. `1842.36`, NOT `184236`). Read every field's `type`, `unit`,
   `precision`, `ordering`, `allowed_values`, and `description` and obey them literally.
2. **Use the correct base URL.** Prompts hardcode `http://127.0.0.1:8005`. The real, live base URL
   is given in the environment/runner (in this distribution it has been `http://127.0.0.1:8029`).
   If a prompt URL and the environment URL differ, the environment URL wins. Probe `/health` first.
3. **Evaluate every gate for every entity, independently.** Do not stop scanning an entity's flags
   once you have enough to decide. A flag (e.g. `expired_license`) still belongs in the flag list
   even when the final decision is `escalate` for another reason. In blind runs, missed flags came
   from short-circuiting after the decision was already determined.
4. **Sort exactly as specified** (almost always ascending by id) and include **every requested key**
   in object-valued fields (one entry per candidate id, even when the value is empty `[]` or `0.00`).
5. **Match claims to bills by amount + vendor + claim_id, not by bill_id.** Bill IDs are reused and
   one claim can link to several bills; pick the bill whose amount and vendor and claim_id all match.

## 1. API usage

Base URL (verify against the environment): `http://127.0.0.1:8029`. List responses are wrapped:
`{"endpoint":..., "count":..., "total":..., "offset":..., "limit":..., "data":[...]}` — read `data`.
Use `limit` (default 100, max 500) and `offset` to page; pass `limit=500` and confirm
`count == total` so you don't silently miss rows. Endpoints support exact-match query params by
field name.

Key endpoints (each has a `/...` and an `/api/...` form; both work):
- `GET /health`, `GET /endpoints`
- `GET /api/claims`, `GET /api/claims/{claim_id}`
- `GET /api/ap/bills`, `GET /api/ap/payments`
- `GET /api/ap/aging?as_of=YYYY-MM-DD`
- `GET /api/vendors`
- `GET /api/compliance/objects` and per-area: `profile`, `ownership`, `registry`, `screening`,
  `bank`, `risk`, each `/api/compliance/<area>/{business_id}`
- `GET /api/prepaids/invoices`, `GET /api/prepaids/gl-balances` (or `/gl/balances?account=&period=`)
- `GET /api/close/logs`

**Aging caveat (important):** `/api/ap/aging` computes per-bill `balance = amount − ALL payments`,
counting scheduled/processing payments toward paid. So a bill with only a *scheduled* payment shows
balance 0 there. **Do not trust aging for "is it actually paid/cleared" decisions.** Recompute open
balance yourself using only **`payment.status == "cleared"`**.

**Compliance source:** `/api/compliance/objects` is a consolidated record whose fields match the
per-area sub-endpoints; you can use it as the single source, but spot-check a sub-endpoint if a field
looks off.

### Status / enum vocabulary observed
- Payment `status`: `cleared`, `processing`, `scheduled`. Only `cleared` reduces open AP balance.
- Bill `status`: `paid`, `approved`, `scheduled`, `draft`, `void`. `void` bills are ignored entirely.
- Compliance: `bank_account_status` ∈ {verified, name_mismatch, closed, ...};
  `pep_status` ∈ {none, possible_pep, confirmed_pep, not_run};
  `sanctions_check_status` ∈ {clear, confirmed_match, not_run};
  plus booleans like `shell_company_suspected`, a `risk_score` int, a `review_status`, and
  `license_expiry` / `missing_fields` / tax id fields.
- Vendor `status` can be `on_hold` (a serious integrity signal).

## 2. Shared field definitions

- **Open AP balance for a claim/bill** = matched bill amount − sum of that bill's **cleared**
  payments. Report in **dollars, 2 decimals** unless the template says otherwise.
- **expired_license** = `license_expiry < as_of_date` (strictly before). A license expiring **on**
  the as_of date is still valid. Apply this to every entity.
- **invalid tax id** = the tax id is malformed (non-digit characters in the numeric portion, e.g.
  `TIN12X899`) **or** a placeholder/all-same-digit value (e.g. `TIN999999`). A compliance-vs-vendor
  tax mismatch reinforces "invalid." Pure format-validity alone is too narrow — include placeholders.
- **risk_score override** = `risk_score >= 70` (70 itself qualifies; `>=`, not `>`).
- **bank mismatch** = compliance `bank_account_status == name_mismatch`.

## 3. Task playbooks

Identify the task type from the template's top-level keys, then follow the matching playbook.

### 3.1 Reimbursement-to-AP close triage
Template keys: `payable_claim_ids`, `blocked_claim_ids`, `paid_claim_ids`, `ap_open_balance_total`,
`crm_required_claim_ids`, `batch_status`, `reviewed_claim_count`.

For each batch claim, find its matching bill (amount+vendor+claim_id) and that bill's payments:
- **paid** → claim has a matching `paid` bill **and** a `cleared` payment for the claim amount.
- **payable** → matching, valid, *open* AP bill (e.g. `scheduled`/`approved`) with no cleared
  payment yet (a `processing` payment is NOT cleared, so the bill is still payable/open).
- **blocked** → no linked bill, amount/vendor mismatch, or a `void` bill. These need cleanup.
- `ap_open_balance_total` = sum of open balances of **payable** bills only (dollars, 2 decimals).
- `crm_required_claim_ids` = blocked claims needing owner/AP-link remediation (typically == blocked
  set when all blocks are AP/evidence issues).
- `batch_status`: `blocked` if any item blocked; else `open_payables` if any valid unpaid bill
  remains; else `ready_to_close`.
- `reviewed_claim_count` = number of claims in the requested batch.

### 3.2 Vendor onboarding / intake compliance release
Template keys: `per_business` (decision per id), `reportable_ubo_counts`, `hard_stop_flags`,
`follow_up_business_ids`, `overall_release_ready`.

Compute `hard_stop_flags` per business from compliance data — **list ALL that apply**, then sort
**alphabetically by enum value**. Flag mapping:
- `bank_closed` ← bank_account_status closed
- `bank_name_mismatch` ← bank_account_status name_mismatch
- `confirmed_pep` ← pep_status confirmed_pep
- `expired_license` ← license_expiry < as_of (check this for EVERY business; it was missed in blind
  runs for businesses that already had other flags)
- `missing_required_documents` ← missing_fields non-empty
- `sanctions_confirmed` ← sanctions_check_status confirmed_match
- `screening_not_run` ← sanctions OR pep status `not_run`
- `shell_company_suspected` ← that boolean true
- `vendor_on_hold` ← vendor.status on_hold

Decision (3-way `approve` / `awaiting_information` / `escalate`):
- **escalate** if any **integrity** flag present:
  `confirmed_pep`, `sanctions_confirmed`, `shell_company_suspected`, `vendor_on_hold`,
  `bank_closed`, `bank_name_mismatch`.
- else **awaiting_information** if only **info-gap** flags present:
  `expired_license`, `missing_required_documents`, `screening_not_run`.
- else **approve** (no flags).

`follow_up_business_ids` = the **awaiting_information** set ONLY (do NOT add escalated ids — that
was a blind-run error). Escalated cases go to a risk owner, not the info follow-up queue.
`reportable_ubo_counts` = count of **unique beneficial-owner names** at/above the reporting
threshold (**25%**). `overall_release_ready` = true only if every business is `approve`.

### 3.3 Prepaid-to-GL close reconciliation
Template keys: `period`, `entity`, `selected_invoice_ids`, `account_rollup` (per account),
`invoice_results` (per invoice), `default_missing_term_invoice_ids`, `exception_invoice_ids`.

Limit to the scoped invoice ids and accounts. Order `selected_invoice_ids` and `invoice_results`
**in the same order as the scope file**; order the id lists **ascending**. All amounts: 2 decimals.

Per invoice (straight-line, using the invoice's own `monthly_amortization`):
- `march_amortization` = one month of amortization if the close month is within the service window
  (service_start month ≤ period ≤ service_end month), else 0.
- `cumulative_amortization_through_march` = months from service_start through min(period,
  service_end), inclusive, × monthly_amortization, **capped at original_amount** (small rounding
  residue like `0.01` at full amortization is expected — don't force it to 0).
- `ending_balance` = original_amount − cumulative.
- `default_missing_term_flag` = data_quality_flags contains a missing-term marker
  (`missing_contract_dates`).
- `exception_flag` = invoice has **ANY** data_quality_flag (including benign ones like
  `rounded_amount`). This makes exceptions a superset of the missing-term set — verified correct.

Per account rollup: sum the per-invoice values; `gl_ending_balance` from the GL endpoint for that
account+period; `variance_amount = schedule_ending_balance − gl_ending_balance`;
`variance_flag = |variance_amount| > variance_threshold_abs` (from the scope file, e.g. 100);
`has_default_missing_term_flag` = any scoped invoice in the account has the missing-term flag.

`account_status`:
- **requires_reconciliation** if the account has a missing-term flag **OR any exception invoice**
  (i.e. any invoice with `exception_flag=true`). Note: an account can be requires_reconciliation
  purely from an exception invoice even with no missing-term flag — this was the blind-run miss
  (an account was wrongly set to `variance_review`).
- else **variance_review** if `variance_flag` true but the account's schedule data is clean
  (no missing-term, no exception invoices).
- else **reconciled**.

`default_missing_term_invoice_ids` and `exception_invoice_ids`: ascending, scoped invoices only.

### 3.4 Stale AP snapshot reconciliation
Template keys: `eligible_claim_ids`, `not_ready_claim_ids`, `ap_balance_by_claim` (per candidate),
`stale_snapshot_corrections` (per candidate enum), `close_log_required` {required, ids},
`batch_status`.

Treat the CSV snapshot as **context only**; the live API is the system of record. For each
candidate, find the correct matching bill (amount+vendor+claim_id) and its current
status/payments, then assign a correction:
- `current_snapshot_ok` — snapshot matches live state.
- `mark_in_flight_payment` — payment now in-flight (`processing`); snapshot said none.
- `replace_with_matched_paid_bill` — snapshot pointed at a wrong/distractor bill; the correct
  matched bill is `paid`/`cleared`.
- `exclude_amount_or_vendor_mismatch` — the snapshot's bill has amount/vendor mismatch.
- `ignore_void_bill` — the matched bill is `void`.
- `block_unapproved_claim` — the claim is no longer approved (e.g. `needs_receipt`).

**Eligibility (key correction):** "eligible" means the claim **reconciles cleanly** to current ERP
state — a matched, non-mismatch, non-void, approved bill. A correctly-matched claim that turns out
**already paid** (`replace_with_matched_paid_bill`) is **still eligible** (it just carries a 0.00
open balance). An in-flight payment (`mark_in_flight_payment`) is also **eligible**.
- `eligible_claim_ids` = corrections `current_snapshot_ok`, `mark_in_flight_payment`,
  `replace_with_matched_paid_bill`.
- `not_ready_claim_ids` = corrections `exclude_amount_or_vendor_mismatch`, `ignore_void_bill`,
  `block_unapproved_claim`.
- `ap_balance_by_claim` = open balance per candidate (cleared payments only, ignore stale/void rows);
  0.00 for paid/void/mismatch/unapproved. Include EVERY candidate key.
- `close_log_required`: if corrections were applied, set `required: true` and **populate `ids` with
  the matching existing close-log entry/entries** from `/api/close/logs`. Do NOT leave `ids` empty
  when a close log documents the cleanup (blind-run error). The matching log may link by
  period / AP account / correction theme (e.g. the late-payment & partial-support cleanup), not
  necessarily by claim_id — query `/api/close/logs`, inspect, and include the relevant id(s),
  sorted ascending.
- `batch_status`: `needs_ap_refresh` when the snapshot is stale but reconcilable (in-flight/paid
  corrections present); `blocked` if hard blocks dominate; `ready_to_send` if everything is clean.

### 3.5 AP payment release after vendor account changes
Template keys (often): `task_id`, `batch_id`, `as_of_date`, `target_business_ids`, `decisions`
(per business enum), `bank_mismatch_ids`, `invalid_tax_ids`, `expired_license_ids`,
`review_queue_ids`, `risk_score_override_flags`. Echo required literal values (`task_id`,
`batch_id`, `as_of_date`) exactly from the template/payload. `additional_properties_allowed: false`
means add nothing extra.

Build the evidence lists (each ascending by business_id, evaluated for every target):
- `bank_mismatch_ids` ← bank_account_status name_mismatch
- `expired_license_ids` ← license_expiry < as_of_date
- `invalid_tax_ids` ← malformed OR placeholder tax id (see §2)
- `risk_score_override_flags` ← risk_score >= 70

Decision (3-way `release` / `hold` / `escalate`) — **the escalate set is NARROWER than in onboarding**:
- **escalate** ONLY for confirmed integrity issues:
  `confirmed_pep`, `sanctions_confirmed` (sanctions confirmed_match), `shell_company_suspected`,
  or vendor `on_hold`.
- **hold** if not escalated but any release gate fails: bank `name_mismatch` or `closed`,
  `expired_license`, invalid tax id, `risk_score >= 70`, sanctions/pep `not_run`, or a non-clean
  `review_status` (e.g. in_review / escalated).
- **release** only when fully clean (verified bank with matching requested last4, valid license/tax,
  risk < 70, no red flags).

Critical correction from blind runs: in *this* release context, `bank_closed`, `possible_pep`
(not confirmed), `sanctions not_run`, and `review_status = escalated` are **HOLD**, not escalate —
they are payment gates, not confirmed integrity findings. (Contrast §3.2 onboarding, where
bank_closed/bank_name_mismatch DO escalate. The escalation bar differs by task type; don't carry the
onboarding rule into payment release.)

`review_queue_ids` = every business whose decision is **not** `release` (i.e. all `hold` + `escalate`),
ascending.

## 4. Output checklist before returning
- Conforms to `answer_template.json`: every required key present; object fields have one entry per
  candidate/business id; no extra keys when `additional_properties_allowed: false`.
- Enums are exactly from `allowed_values`; lists sorted as specified (usually ascending by id; for
  prepaid invoice_results/selected list use scope-file order; hard_stop_flags alphabetical).
- Currency in the **unit/precision the template declares** (dollars + 2 decimals unless stated),
  even if the prose says "cents."
- Open balances use **cleared payments only**, never the raw `/aging` balance.
- Each gate/flag evaluated for **every** entity, independently of the final decision.
- Return JSON only — no narrative around it.
