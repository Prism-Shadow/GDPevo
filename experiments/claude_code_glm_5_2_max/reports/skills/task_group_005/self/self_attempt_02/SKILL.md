# SKILL.md — ERP Finance Expense-Control (task_group_005)

Transferable executable skill for solving ERP finance expense-control tasks against the shared remote API. Distilled from independent analysis of five train tasks (reimbursement-to-AP close, vendor intake/KYC, prepaid amortization & GL reconciliation, stale-snapshot AP payment board, account-change payment release). No gold answers or judge feedback were used.

---

## 1. API Contract

**Base URL:** `<remote-env-url>` (use this, not 127.0.0.1 which may appear in prompts).

**Discovery:** `GET /endpoints` returns all paths + the filtering contract.

**Namespaced resource paths (use the `/api/...` form):**

| Resource | Path | Alt path | ~Total |
|---|---|---|---|
| Claims | `/api/claims` | `/claims` | 92 |
| AP bills | `/api/ap/bills` | `/bills` | 112 |
| AP payments | `/api/ap/payments` | `/payments` | 74 |
| AP aging | `/api/ap/aging` | — | — |
| Vendors | `/api/vendors` | `/vendors` | 80 |
| Compliance objects | `/api/compliance/objects` | `/compliance/objects` | 65 |
| Prepaid invoices | `/api/prepaids/invoices` | `/prepaids/invoices` | 44 |
| Prepaid GL balances | `/api/prepaids/gl-balances` | `/gl/balances` | 20 |
| Close logs | `/api/close/logs` | `/close/logs` | 36 |

**Filtering:** exact-match query params by field name (e.g. `?claim_id=CLM-2025-OPS-017`, `?bill_id=AP-2025-0068`, `?business_id=BUS-2025-0009`, `?prepaid_invoice_id=PPD-2025-0001`, `?account=1250&period=2025-03`). Plus `limit` (default 100) and `offset` for pagination.

**Response envelope:** `{ "count": N, "data": [...], "endpoint": "...", "limit": ..., "offset": ..., "total": ... }`. Always read `data[]`; check `count` for emptiness.

**Health:** `GET /health`, `GET /api/health`.

**Token economy:** query specific records by ID/param, never dump whole collections. chain bill→payment by `bill_id`; chain claim→bill by `claim_id`; chain compliance→vendor by `vendor_id` (compliance objects carry `vendor_id`).

**Currency:** report all amounts to 2 decimals in USD unless a task says otherwise. When a prompt says "USD cents," interpret as 2-decimal USD precision (matching the answer template's `precision: 2, unit: USD`), NOT integer cents.

---

## 2. Record Schemas & Controlled Vocabularies

### Claims (`/api/claims`)
`claim_id, amount, status, approved_date, submitted_date, category, department, employee_name, policy_flags, receipt_status, vendor_id, notes, currency`
- `status`: `approved` | `paid` | `needs_receipt` (others possible)
- `receipt_status`: `attached` | `partial` | (missing)
- `policy_flags`: e.g. `manual_rate`, `duplicate_amount`, `late_receipt`, `over_limit`, `weekend_spend`
- `vendor_id`: nullable (null = no vendor linked)
- `approved_date`: nullable (null = not yet approved, e.g. `needs_receipt`)

### AP Bills (`/api/ap/bills`)
`bill_id, claim_id, amount, status, bill_date, due_date, invoice_number, account, vendor_id, memo, currency`
- `status`: `paid` | `scheduled` | `approved` | `void`
- `claim_id`: nullable (not all bills are claim-linked)
- `account`: GL account string (e.g. `6200`, `1250`, `2100`, `6500`)

### AP Payments (`/api/ap/payments`)
`payment_id, bill_id, amount, status, payment_date, method, bank_reference, vendor_id`
- `status`: `cleared` | `scheduled` | `processing`
- `cleared` = settled/confirmable; `scheduled`/`processing` = in-flight (NOT yet a cleared offset)

### Vendors (`/api/vendors`)
`vendor_id, vendor_name, legal_name, status, tax_id, bank_account_last4, default_account, industry, payment_terms, updated_at`
- `status`: `active` | `on_hold`
- `tax_id`: e.g. `TIN905045`. Malformed/placeholder values seen: `TIN999999` (all-9s placeholder), `TIN12X899` (non-digit char). These indicate invalid tax IDs.

### Compliance Objects (`/api/compliance/objects`)
`business_id, business_name, vendor_id, bank_account_status, license_expiry, missing_fields, pep_status, sanctions_check_status, shell_company_suspected, risk_score, review_status, tax_id, ubo_list, ownership_layer_count, jurisdiction, registration_number`
- `bank_account_status`: `verified` | `name_mismatch` | `closed`
- `pep_status`: `none` | `confirmed_pep` | `possible_pep` | `not_run`
- `sanctions_check_status`: `clear` | `not_run` | `confirmed`
- `review_status`: `approved` | `in_review` | `awaiting_information` | `escalated` | `not_started`
- `missing_fields`: list (e.g. `["license","beneficial_owner_id"]`). Non-empty => missing required documents.
- `ubo_list`: `[{name, ownership_pct}]`. A name may appear more than once (aggregate by unique name; a UBO counts as reportable if ANY entry ≥ threshold).
- `tax_id` on compliance may DIFFER from the linked vendor's `tax_id` — treat mismatches + malformed values as invalid.

### Prepaid Invoices (`/api/prepaids/invoices`)
`prepaid_invoice_id, account, account_name, original_amount, monthly_amortization, service_start, service_end, recognition_method, invoice_date, invoice_number, description, source_document, vendor_id, data_quality_flags`
- `recognition_method`: `straight_line`
- `data_quality_flags`: `rounded_amount` | `missing_contract_dates` | (others possible)
  - `missing_contract_dates` => default/missing term flag (dates are estimates/defaults, term unreliable)
  - `rounded_amount` => minor rounding on monthly amortization (still a data-quality exception, but NOT a missing-term flag)

### Prepaid GL Balances (`/api/prepaids/gl-balances`)
`account, account_name, entity, period (YYYY-MM), ending_balance, loaded_at, source`
- One row per account+period+entity. Query by `?account=1250&period=2025-03`.

### Close Logs (`/api/close/logs`)
`log_id, area, period (YYYY-MM), status, related_account, message, owner, created_at`
- `area`: `AP` | `Prepaids` | `GL` | `Compliance` | `Treasury` | `Expense`
- `status`: `closed` | `ready_for_review` | `open` | `blocked`
- `related_account`: account string or `None`
- `message` patterns: `Waiting on AP export refresh`, `Legacy import created duplicate line`, `Variance review pending`, `Reviewer cleared variance`, `Support uploaded`, `Manual journal entry posted`
- Only non-`closed` logs are actionable; `closed` logs are resolved.

---

## 3. Business Rules & SOPs by Task Type

### 3A. Reimbursement-to-AP Close (train_001 pattern)

**Goal:** for a batch of claim IDs, partition into paid / payable / blocked, compute open AP balance, and determine batch status.

**SOP (query order):**
1. For each `claim_id`: `GET /api/claims?claim_id=...` → capture amount, status, vendor_id, receipt_status, policy_flags.
2. `GET /api/ap/bills?claim_id=...` → all bills linked to the claim.
3. For each bill: `GET /api/ap/payments?bill_id=...` → payments.
4. Classify each claim:

| Classification | Rule |
|---|---|
| **paid** | claim has a bill whose `amount` == claim `amount` AND bill `status`==`paid` AND a payment with `status`==`cleared` for that bill/amount. (All three: matching paid bill + cleared payment for the CLAIM amount.) |
| **payable** (can remain in AP queue) | claim `status`==`approved` AND a bill exists with `amount`==claim amount, bill `status` in {`scheduled`,`approved`} (open, not void, not paid), AND no cleared payment for that amount. |
| **blocked** (not paid, must not release) | none of the above: no AP bill at all; bill amount ≠ claim amount (mislink); bill `status`==`void`; vendor mismatch between claim and bill; or claim not approved. |

5. **ap_open_balance_total** = sum of `amount` of valid OPEN AP reimbursement bills (status scheduled/approved, amount matches claim, not void, not paid) for PAYABLE claims ONLY. Do NOT include bills for blocked or paid claims. Do NOT include mismatched/void bills.
6. **crm_required_claim_ids** = all blocked claims (they all need expense-case owner cleanup or AP-link remediation: missing link, wrong link, void bill, etc.).
7. **batch_status:** `blocked` if any blocked claim exists; else `open_payables` if any payable (valid unpaid AP bills remain); else `ready_to_close`.
8. **reviewed_claim_count** = count of claim IDs in the requested batch.

**Key gotchas:**
- A bill with a much larger amount than the claim (`amount` mismatch) is a mislinked bill → blocked, even if bill status is `approved`.
- A `void` bill is never a valid AP link → blocked.
- `policy_flags`/`receipt_status` imperfections do NOT by themselves block a claim if the AP link (matching open bill) is valid — the AP evidence drives payable vs blocked.
- The "matching paid AP bill" must match the CLAIM amount, not just any paid bill on the claim. A claim can have a non-matching scheduled bill AND a matching paid bill simultaneously (the matching paid one settles the claim).

### 3B. Vendor Onboarding / KYC Finance-Risk (train_002 pattern)

**Goal:** for a batch of `business_id`s, produce per-business release decision, reportable UBO counts, hard-stop flag lists, follow-up IDs, and overall release readiness.

**SOP:**
1. For each `business_id`: `GET /api/compliance/objects?business_id=...` → compliance record (carries `vendor_id`).
2. `GET /api/vendors?vendor_id=...` → vendor record (check `status`==`on_hold`, `tax_id`).
3. Determine `as_of_date` from the local batch payload (e.g. `as_of_date` field).
4. Compute **hard_stop_flags** (alphabetical sort, empty list if none):

| Flag enum | Trigger |
|---|---|
| `bank_closed` | `bank_account_status` == `closed` |
| `bank_name_mismatch` | `bank_account_status` == `name_mismatch` |
| `confirmed_pep` | `pep_status` == `confirmed_pep` (NOT `possible_pep`) |
| `expired_license` | `license_expiry` < `as_of_date` (string/date compare) |
| `missing_required_documents` | `missing_fields` non-empty |
| `sanctions_confirmed` | `sanctions_check_status` == `confirmed` |
| `screening_not_run` | `sanctions_check_status` == `not_run` OR `pep_status` == `not_run` |
| `shell_company_suspected` | `shell_company_suspected` == true |
| `vendor_on_hold` | vendor `status` == `on_hold` |

5. **decision** (`approve` | `awaiting_information` | `escalate`):
   - `escalate` if ANY hard-stop flag other than `missing_required_documents` applies (PEP, bank, sanctions, shell, expired license, vendor on hold, screening not run).
   - `awaiting_information` if `missing_required_documents` is the ONLY hard-stop (docs must be collected).
   - `approve` if no hard-stop flags AND no other blockers.
   - Note: when missing_required_documents co-occurs with another hard stop (e.g. expired license), decision = `escalate`.
6. **reportable_ubo_counts:** count UNIQUE UBO names whose ownership_pct ≥ 25 (reporting threshold) in ANY entry. Dedup by name; a UBO with a 24% entry AND a 45% entry counts (the 45% entry qualifies).
7. **follow_up_business_ids:** all businesses whose decision ≠ `approve`, ascending by business_id.
8. **overall_release_ready:** `true` ONLY if every business decision == `approve`.

### 3C. Prepaid Amortization & GL Reconciliation (train_003 pattern)

**Goal:** for a scoped set of prepaid invoice IDs, compute March (or given close-period) amortization, cumulative amortization through the period, schedule ending balances, and reconcile against GL ending balances per account.

**SOP:**
1. Read the local scope payload (`prepaid_close_scope.json`): `entity`, `close_period` (e.g. `2025-03`), `accounts` (e.g. `["1250","1251"]`), `selected_prepaid_invoice_ids`, `variance_threshold_abs` (e.g. 100.0).
2. For each invoice ID: `GET /api/prepaids/invoices?prepaid_invoice_id=...`.
3. For each account+period: `GET /api/prepaids/gl-balances?account=...&period=...`.
4. **Amortization math (straight-line, full-month):**
   - A month counts for amortization if it falls within [service_start month, service_end month] inclusive. Mid-month starts (e.g. 2025-03-15) still count the start month as a full month. No proration.
   - `march_amortization` (for close period month) = `monthly_amortization` if the close period month is within the service window, else 0.
   - `cumulative_amortization_through_march` = (number of months from service_start month through close-period month, capped by service_end month) × `monthly_amortization`.
   - `ending_balance` = `original_amount` − `cumulative_amortization_through_march`. (Ending balance can be 0.00 when fully amortized, or 0.01 due to rounding.)
5. **Per-invoice flags:**
   - `default_missing_term_flag` = true if `data_quality_flags` contains `missing_contract_dates`.
   - `exception_flag` = true if `data_quality_flags` is non-empty (ANY flag, including `rounded_amount`).
6. **Account rollup** (per account in scope):
   - `selected_invoice_count`, `original_amount_total`, `march_amortization_total`, `cumulative_amortization_through_march` = sums over invoices on that account.
   - `schedule_ending_balance` = sum of invoice `ending_balance`.
   - `gl_ending_balance` = from GL balance record.
   - `variance_amount` = `schedule_ending_balance` − `gl_ending_balance` (CAN be large/negative because scoped invoices are a subset of the full GL balance).
   - `variance_flag` = `|variance_amount|` > `variance_threshold_abs`.
   - `has_default_missing_term_flag` = any invoice on the account has default_missing_term_flag.
   - `account_status`: `requires_reconciliation` if `has_default_missing_term_flag` (missing terms prevent reliable reconciliation); else `variance_review` if `variance_flag` true; else `reconciled`.
7. **default_missing_term_invoice_ids:** invoices with `missing_contract_dates` flag, ascending by ID.
8. **exception_invoice_ids:** invoices with ANY `data_quality_flags`, ascending by ID. (Superset of default_missing_term list when `rounded_amount` invoices exist.)
9. `selected_invoice_ids` and `invoice_results` preserve the ORDER from the scope file (NOT sorted).
10. `period` = scope's `close_period`; `entity` = scope's `entity`.

**Rounding note:** `monthly_amortization` × month-count may differ from `original_amount` by ~0.01 due to `rounded_amount`. Carry actual arithmetic; do not force clean totals.

### 3D. Stale-Snapshot AP Payment Board (train_004 pattern)

**Goal:** reconcile a stale local AP export against current ERP data; decide which candidate claims stay (eligible), which are not-ready, what stale-row correction applies per claim, whether close logs are required, and the batch status.

**SOP:**
1. Read the local stale snapshot (CSV/JSON) — treat as CONTEXT, not system of record.
2. For each candidate `claim_id`: query current `claims`, `bills` (by `claim_id`), and `payments` (by `bill_id`) from the API.
3. Classify each claim:
   - **eligible** (`can remain in batch`): claim `status`==`approved`, a valid OPEN bill exists (amount == claim amount, status scheduled/approved, not void), and no cleared payment already settled it.
   - **not_ready**: claim already `paid` (settled, shouldn't be in batch); claim not approved (`needs_receipt`/no `approved_date`); bill amount or vendor mismatches claim; bill is `void`; or no valid AP link.
4. **ap_balance_by_claim** (all candidate claims, USD 2dp): open AP balance after applying CLEARED payments and ignoring stale/voided/mismatched rows.
   - eligible claim with open bill + no cleared payment → bill amount (e.g. 1842.36).
   - paid claim (cleared payment matches bill) → 0.00.
   - mismatched/void/unapproved → 0.00 (the bad bill is excluded).
5. **stale_snapshot_corrections** (ONE enum per candidate claim):

| Enum | When to apply (priority order: top first) |
|---|---|
| `block_unapproved_claim` | current claim `status` is not approved (e.g. `needs_receipt`). Highest priority. |
| `ignore_void_bill` | current bill `status` == `void`. |
| `exclude_amount_or_vendor_mismatch` | bill `amount` ≠ claim `amount` OR bill `vendor_id` ≠ claim `vendor_id`. |
| `replace_with_matched_paid_bill` | stale snapshot pointed at the wrong/larger bill, but a DIFFERENT matched bill (amount==claim) exists and is `paid` with a `cleared` payment. |
| `mark_in_flight_payment` | stale snapshot missed a current `scheduled`/`processing` payment on the CORRECT bill (in-flight, not yet cleared). |
| `current_snapshot_ok` | stale and current agree; claim valid and eligible. |

6. **close_log_required:** `required` = true when the batch has stale corrections / blocked items. `ids` = non-`closed` close-log IDs that are relevant: prefer `area`==`AP` non-closed logs AND any non-closed logs whose `message` == `Waiting on AP export refresh` for accounts touched by the batch's bills. Sort ascending by log_id.
7. **batch_status:** `blocked` if any claim is fundamentally blocked (unapproved claim, void bill, permanent amount/vendor mismatch); `needs_ap_refresh` if the only issue is stale payment/bill-status data that an AP export refresh would fix (no hard blockers); `ready_to_send` if all candidate claims are eligible.

**Key distinction — paid vs payable:** a claim already settled (matching paid bill + cleared payment) does NOT remain in the batch → `not_ready`, correction `replace_with_matched_paid_bill`, ap_balance 0.00. A claim with an open matching bill and no cleared payment → `eligible`, correction `current_snapshot_ok` (if stale agrees) or `mark_in_flight_payment` (if a scheduled payment appeared).

### 3E. Account-Change Payment Release (train_005 pattern)

**Goal:** after vendor account-change events, decide release/hold/escalate per business, plus flag bank mismatches, invalid tax IDs, expired licenses, review queue, and high-risk overrides.

**SOP:**
1. Read local batch payload (`account_change_batch.json`): `review_date` (= `as_of_date`, e.g. 2025-06-01), `target_business_ids`, account-change tickets.
2. For each `business_id`: `GET /api/compliance/objects?business_id=...` then `GET /api/vendors?vendor_id=...`.
3. Compute derived lists (all ascending by business_id):

| Output field | Rule |
|---|---|
| `bank_mismatch_ids` | `bank_account_status` == `name_mismatch` (NOT `closed`). |
| `invalid_tax_ids` | compliance `tax_id` is malformed/placeholder (e.g. all-9s, non-digit chars) OR differs from the linked vendor's `tax_id`. |
| `expired_license_ids` | `license_expiry` < `as_of_date` (comparison date = `as_of_date`). Use strict `<`; a license expiring ON the as_of date is expired; one day after is current. |
| `risk_score_override_flags` | `risk_score` >= 70. |
| `review_queue_ids` | all businesses whose decision ≠ `release` (i.e. hold + escalate) — they require compliance/AP review before release. |

4. **decision** (`release` | `hold` | `escalate`):
   - `escalate` if any hard stop: `confirmed_pep`, `bank_account_status` == `closed`, `sanctions_check_status` == `not_run`/`confirmed`, invalid/mismatched `tax_id`, vendor `status` == `on_hold`.
   - `hold` if reviewable issues remain but no hard stop: `bank_account_status` == `name_mismatch`, `missing_fields` non-empty, `possible_pep`, expired license (when not already escalated by another factor), or `risk_score` >= 70 without a hard stop.
   - `release` if ALL evidence checks pass: bank `verified`, tax valid+matching, license current, sanctions `clear`, `pep_status` == `none`, `risk_score` < 70, vendor `active`. (Administrative `review_status` like `in_review` does NOT by itself block release if all evidence is clean — the decision is evidence-driven.)
5. Return the fixed required-value fields verbatim (`task_id`, `batch_id`, `as_of_date`, `target_business_ids`).

---

## 4. Common Misjudgments & Exclusion Rules

1. **Stale-snapshot conflicts:** the local payload (CSV/JSON export) is CONTEXT only. Always re-query the live API for claims/bills/payments/vendors. A stale row showing `approved`+`paid` may mask a current `needs_receipt` claim (block_unapproved_claim) or a now-`void` bill (ignore_void_bill).

2. **Paid vs payable:** a claim with a matching `paid` bill and `cleared` payment is SETTLED — it must not remain in an AP batch (→ not_ready / paid list), and its open AP balance is 0.00. Do not confuse "has a paid bill" with "can be paid" (payable).

3. **Claim-vs-AP alignment:** a bill linked to a claim is only a valid AP link if the bill `amount` equals the claim `amount` AND (for paid) the cleared payment equals that amount. A bill 10× the claim amount is a mislink → blocked / excluded, even if bill status is `approved`.

4. **Bill `void` status:** a `void` bill is never a valid AP link. Exclude it from balance and mark `ignore_void_bill`; do not treat it as an open payable.

5. **In-flight payments (`scheduled`/`processing`) are NOT cleared offsets.** Only `cleared` payments reduce open AP balance. A scheduled payment is "in-flight" → correction `mark_in_flight_payment`, but the balance is NOT reduced unless cleared.

6. **Default/missing-term prepaid flags:** `data_quality_flags` containing `missing_contract_dates` => default_missing_term_flag = true. `rounded_amount` is a data-quality exception (exception_flag = true) but NOT a missing-term flag. The exception list is a SUPERSET of the default_missing_term list.

7. **Prepaid variance CAN be large** and that is expected: scoped invoices are a subset of the full GL account balance. Report the actual variance; do not zero it out. `variance_flag` fires on `|variance|` > threshold (e.g. 100). `requires_reconciliation` (not just `variance_review`) when the account has any default_missing_term invoice.

8. **Exception priority ranking (stale corrections):** apply in order — `block_unapproved_claim` > `ignore_void_bill` > `exclude_amount_or_vendor_mismatch` > `replace_with_matched_paid_bill` > `mark_in_flight_payment` > `current_snapshot_ok`. Each claim gets exactly ONE correction.

9. **Signed close-impact direction:** `variance_amount` = schedule_ending_balance MINUS gl_ending_balance (schedule minus GL). A negative variance means the scoped schedule is below the GL (unscoped prepaid amounts exist); a positive variance means the schedule exceeds the GL.

10. **UBO reportable count:** dedup by NAME; a UBO qualifies if ANY ownership entry ≥ 25% (not the sum, not the average, not the max-alone-if-below). Multiple entries for the same name count once.

11. **`confirmed_pep` vs `possible_pep`:** only `confirmed_pep` triggers the `confirmed_pep` hard-stop flag. `possible_pep` is a review item (hold), not a confirmed hard stop.

12. **`screening_not_run`:** triggers on `sanctions_check_status` == `not_run` OR `pep_status` == `not_run` (either screening gap).

13. **License expiry boundary:** compare `license_expiry` strictly against `as_of_date`. `license_expiry == as_of_date` → expired (the date has passed). `license_expiry` one day after `as_of_date` → current.

14. **Tax ID validity:** both malformed format (non-digit chars, all-9s placeholder) AND vendor-vs-compliance `tax_id` mismatch count as invalid. Always cross-check the vendor record's `tax_id` against the compliance object's `tax_id`.

15. **`bank_mismatch_ids` specifically = `name_mismatch`**, NOT `closed`. Bank `closed` is a harder issue (escalate) but is not a "name mismatch."

16. **Decision framework consistency across tasks:** train_002 uses `approve/awaiting_information/escalate`; train_005 uses `release/hold/escalate`. Both are evidence-driven (not administrative-review-status-driven). Escalate = hard stops; the intermediate value = reviewable/missing-info; the positive value = all evidence clean.

17. **`risk_score` override threshold = 70** (inclusive). A business at exactly 70 is flagged.

18. **Output ordering:** read each answer template's `ordering` field carefully. Common requirements: claim_id lists ascending; business_id lists ascending; close-log IDs ascending; invoice lists preserving SCOPE FILE order (NOT sorted); hard_stop_flags ALPHABETICAL by enum value.

19. **`ap_open_balance` scope:** sum ONLY over payable claims' valid open bills. Never include paid claims, blocked claims' mismatched/void bills, or already-cleared amounts.

20. **Close-log selection for `close_log_required`:** prefer non-closed logs where `area`==`AP` or `message`==`Waiting on AP export refresh`, filtered to accounts touched by the batch's bills. Do NOT list every non-closed log in the system.

---

## 5. Quick Reference — Query Order Cheat-Sheet

```
GET /endpoints                         # confirm paths
GET /api/claims?claim_id=<ID>          # claim record
GET /api/ap/bills?claim_id=<ID>        # bills linked to claim
GET /api/ap/payments?bill_id=<BILL>    # payments per bill
GET /api/vendors?vendor_id=<VID>       # vendor (status, tax_id)
GET /api/compliance/objects?business_id=<BID>  # KYC/compliance
GET /api/prepaids/invoices?prepaid_invoice_id=<PID>  # schedule
GET /api/prepaids/gl-balances?account=<ACCT>&period=<YYYY-MM>  # GL
GET /api/close/logs?limit=40           # scan for non-closed relevant logs
```

Always: exact-match params + limit/offset; read `data[]`; check `count`; chain by IDs. Report USD 2dp. Sort lists per the answer template's `ordering` field. Preserve scope-file order where the template says "same order as ... scope".
