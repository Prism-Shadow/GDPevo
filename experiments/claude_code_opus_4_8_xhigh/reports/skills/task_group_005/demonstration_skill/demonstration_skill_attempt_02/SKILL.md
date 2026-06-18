---
name: erp-finance-close-api
description: >-
  Solve ERP finance close, AP, and vendor-compliance review tasks that read from the shared
  task_group_005 ERP finance JSON API (base http://127.0.0.1:8029). Use this WHENEVER a task asks
  you to decide claim/AP/reimbursement close status, compute AP open balances or aging,
  reconcile a stale AP snapshot, run a prepaid-to-GL close (straight-line amortization, GL
  variance), make vendor onboarding / intake compliance release calls (UBO counts, hard-stop
  flags), decide AP payment release after vendor account-change events, or produce month-end
  exception reports — and the answer must conform to an answer_template.json. Triggers include
  mentions of claims (CLM-*), AP bills (AP-*), payments, vendors/business IDs (BUS-*, VEN-*),
  compliance (PEP/sanctions/UBO/license/bank/tax/risk), prepaids (PPD-*), GL balances, close
  logs, "batch_status", "release posture", "reportable UBO", "hard_stop_flags", "variance_flag",
  or any instruction to return JSON matching a finance answer template. Use it even if the prompt
  cites a different base URL (e.g. 8005) — the live base URL below always wins.
---

# ERP Finance Close & Compliance API Solver

You are answering finance close / AP / compliance review questions for ERP "task_group_005".
The shared JSON API is the **only** system of record. Decisions must reflect the *current* API
state, never the review/status field copied from the source system and never a local snapshot.

## 0. Golden rules (read first)

1. **API is truth.** Base URL is always `http://127.0.0.1:8029`. If a prompt names another URL
   (e.g. `8005`), ignore it. Never read local server files; only HTTP GET the API.
2. **Local payloads define scope, not answers.** A payload (CSV/JSON) tells you *which* IDs to
   review and the required output shape. Snapshots are stale context to be corrected against the API.
3. **Conform exactly to `answer_template.json`.** Match key names, top-level ordering, enum spellings,
   list ordering, and numeric precision. Output JSON only — no prose. Read the template before computing.
4. **Sort all ID lists ascending** by their string ID unless the template says otherwise (prepaid
   `selected_invoice_ids` and `invoice_results` keep the scope file's original order; their *flag*
   lists sort ascending).
5. **Rounding:** currency to 2 decimals (`round(x, 2)`). Claim/AP tasks may ask USD *cents* (integers)
   vs USD *dollars with 2 decimals* — re-read the template's `unit`. Compute totals from already-rounded
   per-item values, then round the sum.
6. **Don't trust API roll-ups blindly.** `/api/ap/aging` `balance` counts *all* payments regardless of
   status; the business "open balance" counts **cleared payments only** (see §3). Recompute yourself.

## 1. The API

List endpoints return `{"data":[...], "count":..., "total":..., "offset":..., "limit":...}` — read `data`.
Default `limit=100`, max `500`. Always pass `limit=500`; if `total > 500`, page with `offset`.
Filter by any exact field name, e.g. `?status=paid`, `?claim_id=...`, `?business_id=...`,
`?account=1250&period=2025-03`. Use `curl -s`.

Core endpoints (both `/x` and `/api/x` work):
- `GET /api/claims`, `GET /api/claims/{claim_id}` — expense claims.
- `GET /api/ap/bills` — AP bills (the `?claim_id=` filter links a bill to a claim).
- `GET /api/ap/payments` — payments (filter `?bill_id=`).
- `GET /api/ap/aging?as_of=YYYY-MM-DD` — per-bill `amount`, `paid_amount`, `balance` (see caveat above).
- `GET /api/vendors`, `?vendor_id=` — vendor master (`status` field: active / on_hold / ...).
- `GET /api/compliance/objects?business_id=` — the rich, one-shot compliance record (use this).
  Sub-endpoints carve out subsets of the same data: `profile`, `ownership`, `registry`, `screening`,
  `bank`, `risk` (all `/{business_id}`). The merged `compliance/objects` row has every field you need.
- `GET /api/prepaids/invoices`, `?prepaid_invoice_id=` — prepaid schedules.
- `GET /api/prepaids/gl-balances?account=&period=` — GL ending balances.
- `GET /api/close/logs` — month-end close-log entries (`area`, `period`, `status`, `message`, `related_account`).

### Key field shapes
- **claim**: `claim_id, status (approved|paid|needs_receipt|...), amount, vendor_id (may be null), receipt_status, policy_flags[]`.
- **bill**: `bill_id, claim_id, amount, status (scheduled|approved|paid|void), vendor_id`.
  ⚠ A `bill_id` can be **duplicated** across unrelated bills — always disambiguate by the bill row
  whose `claim_id` matches *and* whose `amount`+`vendor_id` match the claim, not just by `bill_id`.
- **payment**: `bill_id, amount, status (cleared|processing|scheduled), ...`. Only `cleared` reduces balance.
- **compliance object**: `business_id, vendor_id, bank_account_status (verified|name_mismatch|closed),
  pep_status (none|possible_pep|confirmed_pep|not_run), sanctions_check_status (clear|not_run|confirmed),
  license_expiry (YYYY-MM-DD), missing_fields[], shell_company_suspected (bool), risk_score (int),
  review_status, tax_id, ubo_list:[{name, ownership_pct}]`.
- **prepaid invoice**: `prepaid_invoice_id, account, original_amount, monthly_amortization,
  service_start, service_end, recognition_method, data_quality_flags[]`.

## 2. Pick the task type, then run the matching SOP

| Signals in prompt | Task type | SOP |
|---|---|---|
| claims + AP bills + payments, "close status", payable/blocked/paid | Reimbursement-to-AP close | §3 |
| "stale AP export/snapshot" CSV, "needs correction", reason codes | Stale-snapshot reconciliation | §4 |
| prepaid invoice IDs, accounts 12xx, GL ending balance, amortization, variance | Prepaid-to-GL close | §5 |
| business/BUS IDs, onboarding/intake, "release call", approve/escalate, UBO, hard-stop | Vendor onboarding compliance | §6 |
| BUS IDs + account-change tickets, release/hold/escalate, bank/tax/license/risk | AP payment release after account changes | §7 |
| "month-end exception report", mixed signals | Exception reporting | combine the relevant SOPs; one row/flag per anomaly |

## 3. Reimbursement-to-AP close (payable / blocked / paid)

For each candidate claim: GET the claim, GET bills `?claim_id=<id>`, GET payments `?bill_id=` for each bill.

Define the **matched reimbursement bill** = a bill on this claim that is **not `void`**, with
`bill.amount == claim.amount` (±0.005) **and** `bill.vendor_id == claim.vendor_id`. (A claim may have
extra unrelated bills — wrong amount or vendor — ignore those.) `cleared_paid` = sum of payments on
that bill whose `status == "cleared"`.

Classify:
- **paid** — claim has a matched bill, `claim.status == "paid"`, and `cleared_paid >= claim.amount`.
- **payable** — claim has a matched bill, `claim.status == "approved"`, and not fully cleared
  (open). Its **open balance** = matched bill amount − cleared payments.
- **blocked** — everything else: no bill, only a `void` bill, amount/vendor mismatch, or claim not
  approved/paid (e.g. `needs_receipt`).

Outputs (per template):
- `payable_claim_ids`, `paid_claim_ids`, `blocked_claim_ids` — ascending.
- `ap_open_balance_total` = sum of open balances for **payable** claims only (exclude paid & blocked).
- `crm_required_claim_ids` = blocked claims needing owner/AP-link cleanup (in practice = blocked set).
- `batch_status`: `blocked` if any blocked; else `open_payables` if any payable; else `ready_to_close`.
- `reviewed_claim_count` = number of candidate IDs requested.

## 4. Stale AP snapshot reconciliation

The CSV snapshot is stale; reconcile each candidate against the live API exactly as in §3
(matched-bill test, cleared-only payments). Then per claim assign one **correction reason**
(`stale_snapshot_corrections`) from the template enum, evaluated in this priority order:

1. claim not approved/paid (e.g. `needs_receipt`) → `block_unapproved_claim` → **not ready**.
2. only linked bill is `void` (no matched valid bill) → `ignore_void_bill` → **not ready**.
3. no matched valid bill for another reason (amount/vendor mismatch, or none) →
   `exclude_amount_or_vendor_mismatch` → **not ready**.
4. matched bill, `claim.status == paid`, fully cleared → `replace_with_matched_paid_bill` → **eligible**.
5. matched bill with an in-flight (`processing`/`scheduled`, not cleared) payment →
   `mark_in_flight_payment` → **eligible** (still has open balance).
6. matched bill, current and correct, no correction needed → `current_snapshot_ok` → **eligible**.

Outputs:
- `eligible_claim_ids` (eligible set) and `not_ready_claim_ids` — ascending.
- `ap_balance_by_claim` = open balance per candidate = matched-bill amount − cleared payments
  (0.00 when paid/cleared or no valid bill; only an in-flight matched bill shows a positive balance). 2 decimals.
- `close_log_required`: if any correction needs a journal entry (in-flight payment booked / paid-bill
  replacement), set `required=true` and `ids` = the **AP-area** close log(s) for the **period the
  corrected payment posted** whose message documents the entry (e.g. "Manual journal entry posted").
  Find it via `GET /api/close/logs` filtered to `area=AP`, matching `period`. Sort ids ascending.
- `batch_status`: `blocked` if a candidate is unsalvageable and there is nothing left to send;
  `needs_ap_refresh` when eligible claims remain but the snapshot required corrections;
  `ready_to_send` only when every candidate is current with no corrections.

## 5. Prepaid-to-GL close (straight-line amortization)

Scope = invoice IDs from the scope payload; accounts and period from the prompt/payload. GET each
invoice and the GL ending balance per scoped account+period.

Per invoice (straight-line; the record already gives `monthly_amortization`):
- `total_months` = inclusive months from `service_start` to `service_end`
  = `(end.y-start.y)*12 + (end.m-start.m) + 1`.
- `elapsed_months` (through close month) = `(close.y-start.y)*12 + (close.m-start.m) + 1`,
  **capped** at `total_months` and floored at 0 (0 if service starts after the close month).
- `march_amortization` (the close-month amount) = `monthly_amortization` if the close month is within
  service (start ≤ close month ≤ end), else `0.00`.
- `cumulative_amortization_through_<month>` = `round(monthly_amortization * elapsed_months, 2)`.
- `ending_balance` = `round(original_amount - cumulative, 2)`. **Do not clamp to 0** — rounding
  residuals like `0.01` are correct and expected; a fully-elapsed clean invoice lands at `0.00`.
- `default_missing_term_flag` = `"missing_contract_dates" in data_quality_flags`.
- `exception_flag` = `len(data_quality_flags) > 0` (any data-quality flag at all — independent of variance).

Account roll-up (per account, over its scoped invoices): `selected_invoice_count`; and `round(sum(...),2)`
of `original_amount`, close-month amortization, cumulative, and ending balance (the schedule ending balance).
Then:
- `gl_ending_balance` from the GL endpoint for that account+period.
- `variance_amount` = `round(schedule_ending_balance - gl_ending_balance, 2)`.
- `variance_flag` = `abs(variance_amount) > variance_threshold_abs` (threshold from the scope payload, default 100.0).
- `has_default_missing_term_flag` = any scoped invoice on the account has the missing-term flag.
- `account_status` (ladder, most-severe wins): `requires_reconciliation` if `variance_flag` is true OR
  any invoice has a default/missing-term flag (a real reconciliation need); `variance_review` for a soft
  variance concern that does not require reconciliation; `reconciled` when no variance and no defaults.

Output: `period`, `entity`, `selected_invoice_ids` (scope order), `account_rollup` keyed by account
string, `invoice_results` (scope order, keys per template), and ascending `default_missing_term_invoice_ids`
and `exception_invoice_ids`. Keep `account` as the string code (e.g. `"1250"`).

## 6. Vendor onboarding / intake compliance release

For each business: `GET /api/compliance/objects?business_id=`, and `GET /api/vendors?vendor_id=` (for vendor `status`).
`as_of_date` comes from the batch payload.

**reportable UBO count** = count of **unique owner names** in `ubo_list` having `ownership_pct >= 25`
(reporting threshold). Dedupe by name across all qualifying entries (an owner listed twice, or once
below and once at/above 25%, counts once iff any entry is ≥ 25%).

**hard_stop_flags** (per business; emit only those that apply, sorted alphabetically by enum value):
- `bank_closed` — `bank_account_status == "closed"`.
- `bank_name_mismatch` — `bank_account_status == "name_mismatch"`.
- `confirmed_pep` — `pep_status == "confirmed_pep"`.
- `sanctions_confirmed` — `sanctions_check_status == "confirmed"`.
- `screening_not_run` — `sanctions_check_status == "not_run"` OR `pep_status == "not_run"`.
- `shell_company_suspected` — `shell_company_suspected == true`.
- `missing_required_documents` — `missing_fields` is non-empty.
- `vendor_on_hold` — the linked vendor record's `status == "on_hold"`.
- `expired_license` — license is expired **with a grace window**: `license_expiry < as_of_date - 30 days`
  **and** `"license" not in missing_fields` (if the license is a missing document it is captured by
  `missing_required_documents` instead, not double-flagged). Note: this onboarding hard-stop is more
  lenient than the §7 reporting list — keep them distinct.

**decision** per business:
- `approve` — no hard-stop flags.
- `awaiting_information` — only "soft" info/doc flags (`missing_required_documents` and/or
  `screening_not_run`) and nothing else.
- `escalate` — any "serious" flag (anything other than those two: bank_closed, bank_name_mismatch,
  confirmed_pep, expired_license, sanctions_confirmed, shell_company_suspected, vendor_on_hold).

Outputs: `per_business` (ascending by business_id, objects `{business_id, decision}`);
`reportable_ubo_counts` and `hard_stop_flags` keyed by business_id; `follow_up_business_ids` =
every non-`approve` business (ascending); `overall_release_ready` = true only if **all** decisions are `approve`.

## 7. AP payment release after vendor account-change events

For each business in the batch: `GET /api/compliance/objects?business_id=` (and vendor record if needed).
`as_of_date` is the review date from the payload.

Independent reporting lists (these are literal field reports, evaluated strictly):
- `bank_mismatch_ids` — `bank_account_status == "name_mismatch"`.
- `invalid_tax_ids` — `tax_id` fails the canonical format `^TIN\d{6}$` (e.g. contains a letter) OR is the
  placeholder `TIN999999` (all-nines). Both count as invalid.
- `expired_license_ids` — **strict**: `license_expiry < as_of_date` (no grace window here — even a
  few days expired counts; this differs from the §6 onboarding hard-stop on purpose).
- `risk_score_override_flags` — `risk_score >= 70`.

**decision** per business (ladder; escalate beats hold beats release):
- `escalate` — any integrity / financial-crime signal: `pep_status` is `confirmed_pep` or `possible_pep`,
  OR invalid tax_id, OR `sanctions_check_status == "confirmed"`, OR `shell_company_suspected`.
- `hold` — no escalate signal but a blocking operational issue: bank `name_mismatch`/`closed`,
  expired license (strict `< as_of`), non-empty `missing_fields`, `sanctions_check_status == "not_run"`,
  or `risk_score >= 70`.
- `release` — none of the above (clean for release).

Outputs: echo `task_id`, `batch_id`, `as_of_date` and `target_business_ids` (ascending) exactly as the
template requires; `decisions` keyed by business_id; `review_queue_ids` = every business not `release`
(i.e. all `hold` ∪ `escalate`, ascending); plus the four reporting lists above (each ascending).
Respect `additional_properties_allowed: false` — emit only the required keys.

## 8. Verify before returning

Always write a small Python script to compute and assemble the answer rather than doing arithmetic by
hand — it avoids rounding and dedup mistakes and is reproducible. Then check:
- Every required template key present; no extras when the template forbids them; correct top-level order.
- Enum values spelled exactly as in `allowed_values`; booleans real booleans; counts integers.
- Currency to 2 decimals (or cents if requested); totals derived from rounded parts.
- Every list sorted as the template specifies (ascending IDs, or scope order where stated;
  hard_stop_flags alphabetical).
- Cross-check counts (e.g. `reviewed_claim_count`, `selected_invoice_count`) against the input scope.
Return JSON only.
