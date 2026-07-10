# ERP Finance Expense-Control — Reusable Skill

## Environment

All tasks use a shared remote ERP finance API. The base URL is provided by the
runner (see `environment_access.md` at the task root). Do not use localhost,
127.0.0.1, or local setup scripts. Always query the remote API for current
state.

Public endpoints (prefer the `/api/…` variant when both exist):

| Domain | Endpoints |
|---|---|
| Claims | `/claims`, `/api/claims` |
| AP Bills | `/bills`, `/api/ap/bills` |
| Payments | `/payments`, `/api/ap/payments` |
| AP Aging | `/api/ap/aging` |
| Vendors | `/vendors`, `/api/vendors` |
| Compliance | `/compliance/objects`, `/api/compliance/objects` |
| Prepaid Invoices | `/prepaids/invoices`, `/api/prepaids/invoices` |
| GL Balances | `/gl/balances`, `/api/prepaids/gl-balances` |
| Close Logs | `/close/logs`, `/api/close/logs` |

## Source Precedence (Critical)

**The API is always the system of record.** Any local payload — CSV snapshot,
batch JSON, or onboarding manifest — is context only. When the API and a local
payload disagree, the API wins.

Common local context payloads and their role:

- **CSV snapshot (`stale_ap_snapshot.csv`)**: A point-in-time export circulated
  before late payments or cleanup. Use it to understand which rows are now
  stale, but decide eligibility from current API data.
- **Batch JSON (`onboarding_batch.json`, `account_change_batch.json`)**: Lists
  the candidate business/claim IDs and high-level review context. The batch
  tells you *what* to review; the API tells you the *current state* of each
  item.
- **Scope JSON (`prepaid_close_scope.json`)**: Names the invoice IDs, accounts,
  close period, entity, and variance threshold. Use it to scope queries and
  thresholds; derive numbers from the API.

## General Conventions

### Currency
All monetary amounts are **USD**. Report to **two decimal places** (cents
precision). The API returns amounts in dollars; no conversion is needed.

### Sorting
- **Claim IDs**: ascending, lexicographic (e.g. `CLM-2025-0015` before
  `CLM-2025-0037`).
- **Business IDs**: ascending, lexicographic (e.g. `BUS-2025-0006` before
  `BUS-2025-0009`).
- **Close-log IDs**: ascending, lexicographic.
- **Invoice IDs**: ascending, lexicographic — **unless** the answer template
  says "same order as prepaid_close_scope.json", in which case preserve the
  scope file's original order.
- **Hard-stop flags**: alphabetical by enum value string (e.g. `"bank_closed"`
  before `"bank_name_mismatch"`).

### ID List Rules
- Every element in an ID list must belong to the candidate batch (don't invent
  IDs the task didn't ask about).
- Empty lists (`[]`) are valid when no items match.
- An ID can appear in multiple lists when the classification is overlapping
  (e.g. `blocked_claim_ids` and `crm_required_claim_ids`).

---

## Workflow 1: Reimbursement Claim Close Review

**Typical task prompt keywords**: "close review", "reimbursement-to-AP",
"close status", "expense claims batch".

### API Data Needed
1. **Claims** (`/api/claims`) — filter by the candidate claim IDs. Check
   `status` (approved / not approved).
2. **AP Bills** (`/api/ap/bills`) — find bills linked to each claim. Check
   `status` (scheduled, approved, paid, void), `amount`, and vendor info.
3. **Payments** (`/api/ap/payments`) — find payments linked to the claim's
   bill(s). Check `status` (cleared, scheduled, none) and `amount`.

### Classification Rules

**`paid_claim_ids`** — ALL of the following must be true:
- Claim status is `approved`.
- A linked AP bill exists with `bill.amount` matching the claim amount.
- That bill has a linked payment with `payment.status == "cleared"` and
  `payment.amount` covering the bill.

**`payable_claim_ids`** — ALL of the following must be true:
- Claim status is `approved`.
- A linked AP bill exists that is NOT paid (status is `scheduled` or
  `approved`, but no cleared payment covers it).
- No blocking condition (see below) applies.

**`blocked_claim_ids`** — ANY of the following:
- Claim status is NOT `approved` (pending, rejected, draft, etc.).
- AP bill is missing or `void`.
- Bill amount does not match the claim amount.
- Bill vendor or account information is inconsistent.
- Payment evidence is conflicting (partial payment that doesn't settle the
  bill).
- Support documentation is incomplete (check claim metadata or close-log
  references).

**`crm_required_claim_ids`** — subset of `blocked_claim_ids` where the issue
is on the expense-case side (claim owner action needed) rather than a pure
AP/payment problem. Indicators:
- Claim status is not approved (owner hasn't submitted or manager hasn't
  approved).
- Missing receipts, policy violation flags, or category mismatch on the
  claim itself.
- AP-link remediation needed (wrong vendor, wrong amount coded on claim).

### Batch Status
```
blocked        — any candidate claim is in blocked_claim_ids
open_payables  — no blocked claims, but payable_claim_ids is non-empty
ready_to_close — no blocked claims AND payable_claim_ids is empty
                                         (all candidates are paid)
```

### Output Fields
| Field | Type | Meaning |
|---|---|---|
| `payable_claim_ids` | list[string] | Approved, bill exists, unpaid, no blockers |
| `blocked_claim_ids` | list[string] | Not payable — needs correction |
| `paid_claim_ids` | list[string] | Matched paid bill + cleared payment |
| `ap_open_balance_total` | number | Sum of open AP bill amounts for `payable_claim_ids` only (USD, 2 decimals) |
| `crm_required_claim_ids` | list[string] | Blocked subset needing owner cleanup |
| `batch_status` | enum | `ready_to_close` / `open_payables` / `blocked` |
| `reviewed_claim_count` | integer | Total number of claim IDs in the candidate batch |

### Common Pitfalls
- Counting a `scheduled` payment as settled — only `cleared` payments close a
  bill.
- Blocking a claim solely because the snapshot is stale — always re-check the
  API.
- Including paid-claim amounts in `ap_open_balance_total` — only payable claims
  contribute.

---

## Workflow 2: Vendor Onboarding Finance-Risk Review

**Typical task prompt keywords**: "onboarding release", "vendor access",
"finance-risk", "UBO", "hard stop".

### API Data Needed
1. **Vendors** (`/api/vendors`) — resolve `business_id` → `vendor_id`, check
   vendor status, bank accounts, registration.
2. **Compliance Objects** (`/api/compliance/objects`) — per business/vendor:
   - UBO (ultimate beneficial owner) records — names and ownership percentages.
   - Sanctions screening results.
   - PEP (politically exposed person) flags.
   - Bank account validation status (`bank_account_status`).
   - License validity and expiration dates.
   - Required documents checklist.
   - Shell-company risk indicators.
   - Vendor hold status.

### Decision Logic

**Per-business decision** (`approve` / `awaiting_information` / `escalate`):

| Decision | Criteria |
|---|---|
| `approve` | All compliance checks pass. No hard-stop flags. Documents complete. |
| `awaiting_information` | Non-critical issues: missing documents that can be supplied, screening not yet run (but no adverse flags), minor data gaps. Business is not blocked but not fully ready. |
| `escalate` | Hard-stop flag present (see below). Serious risk indicators. |

**`overall_release_ready`**: `true` only if **every** business in the batch
has decision `approve`. Any `awaiting_information` or `escalate` → `false`.

### UBO Count (`reportable_ubo_counts`)
Count **unique beneficial-owner names** per business whose ownership percentage
meets or exceeds the reporting threshold (typically ≥25%, but confirm from the
compliance record's threshold field). Use distinct names, not distinct
person-IDs — two records with the same person name count once.

### Hard-Stop Flags
Flag enum values (alphabetical order in output):
```
bank_closed                — bank account has been closed
bank_name_mismatch         — bank account name ≠ vendor legal name
confirmed_pep              — politically exposed person confirmed
expired_license            — business license expired as of review date
missing_required_documents — required compliance docs not submitted
sanctions_confirmed        — sanctions match confirmed
screening_not_run          — required screening has not been executed
shell_company_suspected    — shell-company risk indicators present
vendor_on_hold             — vendor flagged as on-hold in the system
```

Derive these from compliance object fields (e.g., `bank_account_status ==
"name_mismatch"` → `bank_name_mismatch`; `pep_flag == true` →
`confirmed_pep`; `license_expiry_date < as_of_date` → `expired_license`).

### `follow_up_business_ids`
All business IDs whose decision is NOT `approve`.

### Output Fields
| Field | Type | Sorted |
|---|---|---|
| `per_business` | list[{business_id, decision}] | ascending business_id |
| `reportable_ubo_counts` | object[business_id → int] | — |
| `hard_stop_flags` | object[business_id → list[enum]] | flags alphabetical |
| `follow_up_business_ids` | list[string] | ascending business_id |
| `overall_release_ready` | boolean | — |

### Common Pitfalls
- Forgetting to sort hard-stop flags alphabetically — they are enum strings,
  not insertion order.
- Counting UBOs by record count instead of distinct names.
- Setting `overall_release_ready = true` when even one business is not
  `approve`.

---

## Workflow 3: Prepaid Expense Close Reconciliation

**Typical task prompt keywords**: "prepaid close", "amortization", "GL
balance", "variance", "reconciliation".

### API Data Needed
1. **Prepaid Invoices** (`/api/prepaids/invoices`) — filter by the invoice IDs
   in the scope file. Each invoice record includes:
   - `prepaid_invoice_id`, `account` (GL account number)
   - `original_amount` (total invoice value)
   - `march_amortization` / monthly amortization for the close period
   - `cumulative_amortization_through_march` / through the close period
   - `ending_balance` (schedule-calculated remaining balance)
   - `default_missing_term_flag` — true when term data is incomplete/missing
   - Exception indicators from the source system
2. **GL Balances** (`/api/prepaids/gl-balances` or `/gl/balances`) — filter by
   account (e.g. 1250, 1251) and period (e.g. 2025-03). Get
   `ending_balance` per account.

### Calculation Rules

**Amortization method**: Straight-line monthly amortization as represented in
the invoice record. Do not recalculate; use the values the API returns.

**Schedule ending balance** (per invoice):
```
schedule_ending_balance = original_amount - cumulative_amortization
```
(Use the API's values directly when available; verify with this formula to
catch data errors.)

**Account-level rollup** (sum across all invoices in the account):
| Field | How to compute |
|---|---|
| `selected_invoice_count` | Count of scope invoices in this account |
| `original_amount_total` | sum(`original_amount`) |
| `march_amortization_total` | sum(`march_amortization`) |
| `cumulative_amortization_through_march` | sum(`cumulative_amortization`) |
| `schedule_ending_balance` | sum(`ending_balance`) |
| `gl_ending_balance` | From the GL balances endpoint for the account/period |
| `variance_amount` | `schedule_ending_balance - gl_ending_balance` |
| `variance_flag` | `true` if `abs(variance_amount) >= variance_threshold_abs` (from scope file) |
| `has_default_missing_term_flag` | `true` if ANY invoice in the account has `default_missing_term_flag == true` |

**Account status**:
```
reconciled              — variance_flag == false && has_default_missing_term_flag == false
requires_reconciliation — variance_flag == true || has_default_missing_term_flag == true
variance_review         — reserved for borderline cases (variance near threshold with no data-quality flags);
                          not commonly triggered in routine close
```

### Invoice-Level Exception Flag
An invoice is marked `exception_flag: true` when:
- `default_missing_term_flag == true` (incomplete term data), OR
- `ending_balance == 0.00` (fully amortized but still in the active scope), OR
- The source system flags the invoice with a data-quality exception indicator.

### Output Ordering
- `invoice_results` and `selected_invoice_ids`: preserve the **exact order**
  from `prepaid_close_scope.json`.
- `default_missing_term_invoice_ids` and `exception_invoice_ids`: **ascending**
  by invoice ID.

### Output Fields
| Field | Type | Notes |
|---|---|---|
| `period` | string | `YYYY-MM` from scope |
| `entity` | string | Entity name from scope |
| `selected_invoice_ids` | list[string] | Same order as scope |
| `account_rollup` | object[account → rollup] | One entry per scoped account |
| `invoice_results` | list[object] | Same order as scope |
| `default_missing_term_invoice_ids` | list[string] | Ascending |
| `exception_invoice_ids` | list[string] | Ascending |

### Common Pitfalls
- Reordering `invoice_results` alphabetically instead of preserving the scope
  file's order.
- Using `variance_amount` sign inconsistently — it's always
  `schedule - GL`, so a negative variance means GL > schedule.
- Confusing `march_amortization` (single month) with year-to-date or
  cumulative.

---

## Workflow 4: Stale AP Snapshot Reconciliation

**Typical task prompt keywords**: "stale AP", "conference reimbursement",
"snapshot", "AP batch", "corrections".

### API Data Needed
1. **Claims** (`/api/claims`) — current status of candidate claim IDs.
2. **AP Bills** (`/api/ap/bills`) — current bills linked to claims. Check
   status, amount, vendor.
3. **Payments** (`/api/ap/payments`) — current payment status for each bill.
4. **Close Logs** (`/api/close/logs`) — any pending close entries for the
   claims or bills.

### Correction Logic

Compare the stale snapshot row against the current API state. Classify each
claim:

| Correction | When to apply |
|---|---|
| `current_snapshot_ok` | Snapshot row matches current API state — same bill, same status, same amounts. |
| `mark_in_flight_payment` | Bill is scheduled/approved and a payment exists but is not yet `cleared`. The snapshot shows `none` payment. |
| `replace_with_matched_paid_bill` | Snapshot references a different bill than what the API shows. The current API bill is paid/cleared. |
| `exclude_amount_or_vendor_mismatch` | Bill amount doesn't match claim amount, OR vendor on the bill doesn't match the claim's expected vendor. |
| `ignore_void_bill` | Current API bill status is `void`. The snapshot bill was valid at capture time but is now void. |
| `block_unapproved_claim` | Claim status in current API is not `approved` (pending, rejected, draft). |

### AP Balance (`ap_balance_by_claim`)
For each candidate claim, compute the **open AP balance** as:
- Start with the current (non-void, non-stale) AP bill amount.
- Subtract any cleared payment amount.
- If no open bill exists or the bill is void, balance = `0.00`.
- If the bill is paid with a cleared payment covering the full amount, balance = `0.00`.

### Close Log
Check `/api/close/logs` for entries related to the batch period or any of the
candidate claims/bills. A close log is **required** when any correction is not
`current_snapshot_ok` — i.e., when at least one snapshot row is stale.

### Batch Status
```
ready_to_send   — all candidate claims are eligible (no not_ready claims)
needs_ap_refresh — some claims are not_ready, but no hard blocks (corrections are addressable)
blocked          — at least one claim has a hard block (unapproved, void with no replacement)
```

### Output Fields
| Field | Type | Sorted |
|---|---|---|
| `eligible_claim_ids` | list[string] | ascending |
| `not_ready_claim_ids` | list[string] | ascending |
| `ap_balance_by_claim` | object[claim_id → number] | — |
| `stale_snapshot_corrections` | object[claim_id → enum] | — |
| `close_log_required.required` | boolean | — |
| `close_log_required.ids` | list[string] | ascending |
| `batch_status` | enum | — |

### Common Pitfalls
- Using the snapshot amounts for `ap_balance_by_claim` instead of current API
  amounts.
- Marking a claim as `replace_with_matched_paid_bill` when the current bill is
  void — use `ignore_void_bill` instead.
- Forgetting to set `close_log_required.required = true` when any snapshot row
  is stale.

---

## Workflow 5: Post-Account-Change Payment Release

**Typical task prompt keywords**: "account change", "payment release",
"vendor account-change", "risk review", "AP gate".

### API Data Needed
1. **Vendors** (`/api/vendors`) — current vendor record per business_id:
   bank account details (last 4), vendor status.
2. **Compliance Objects** (`/api/compliance/objects`) — per business:
   - `bank_account_status` — check for `name_mismatch`, `closed`, etc.
   - Tax ID validation status.
   - License expiration date (compare against `as_of_date`).
   - Sanctions screening status.
   - PEP flags.
   - Risk score.
   - Required documents status.

### Decision Logic

For each business in the batch:

1. **Cross-check the bank last 4** from the change ticket against the current
   vendor bank account in the API. A mismatch between the requested last 4 and
   the API's bank record is a warning sign but not necessarily a hard stop
   (the change may be in progress).

2. **Evaluate compliance flags** (see below).

3. **Assign decision**:
   - `release` — all checks pass: bank validated, tax ID valid, license current,
     screening clean, documents complete, risk score acceptable, no sanctions/PEP
     flags.
   - `hold` — issues exist that can be resolved: bank name mismatch, screening
     not run, documents missing, moderate risk. These block release until
     addressed but don't require escalation.
   - `escalate` — serious flags: confirmed PEP, sanctions confirmed, expired
     license, bank closed, shell company suspected, vendor on hold, OR multiple
     concurrent issues from the hold category.

### Derived ID Lists

| List | Condition |
|---|---|
| `bank_mismatch_ids` | Compliance `bank_account_status == "name_mismatch"` |
| `invalid_tax_ids` | Compliance tax ID validation failed or missing |
| `expired_license_ids` | `license_expiry_date < as_of_date` |
| `review_queue_ids` | Decision is NOT `release` (i.e., `hold` or `escalate`) |
| `risk_score_override_flags` | Compliance `risk_score >= 70` |

### Output Fields
| Field | Type | Sorted |
|---|---|---|
| `task_id` | string | from template |
| `batch_id` | string | from template |
| `as_of_date` | string | `YYYY-MM-DD` |
| `target_business_ids` | list[string] | ascending |
| `decisions` | object[business_id → enum] | — |
| `bank_mismatch_ids` | list[string] | ascending |
| `invalid_tax_ids` | list[string] | ascending |
| `expired_license_ids` | list[string] | ascending |
| `review_queue_ids` | list[string] | ascending |
| `risk_score_override_flags` | list[string] | ascending |

### Common Pitfalls
- Using the ticket date instead of `as_of_date` for license expiration checks.
- Setting decision to `release` when `risk_score >= 70` — high risk scores
  should at minimum trigger `hold`, often `escalate` when combined with other
  flags.
- Bank last-4 mismatch from the ticket is not the same as compliance
  `bank_name_mismatch` — the ticket last-4 is the *requested* new account;
  `bank_name_mismatch` is a compliance finding on the *existing* bank record.

---

## Cross-Cutting Rules

### API Query Pattern
1. Read the input payload (batch JSON, CSV, or scope JSON) to get the candidate
   IDs, period, entity, and thresholds.
2. Query the relevant API endpoints using those IDs as filters.
3. Cross-reference: claims ↔ bills ↔ payments; vendors ↔ compliance; prepaid
   invoices ↔ GL balances.
4. Apply the classification logic in the order: identify clean items first,
   then categorize the remaining issues by severity.

### Currency & Precision
- Always USD. Always two decimal places.
- Sum before rounding. Round only the final reported value.
- `0` amounts should be reported as `0.00` or `0.0` as the template requires.

### Dealing with Missing or Stale Data
- A missing bill for a claim doesn't mean the claim is paid — it means the
  claim hasn't been processed. Classify accordingly (usually `blocked` or
  `not_ready`).
- A void bill still visible in a snapshot should be reported as
  `ignore_void_bill` — don't silently drop it or treat it as paid.
- When the API returns no compliance record for a business, treat it as
  `screening_not_run` + `missing_required_documents` until proven otherwise.

### Response Format
Return **JSON only** matching the answer template. Do not include narrative
text, explanations, or markdown fences outside the JSON object. The output must
be valid, parseable JSON.
