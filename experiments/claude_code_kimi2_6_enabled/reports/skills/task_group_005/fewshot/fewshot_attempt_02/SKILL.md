Now I have all the data I need. Let me write the SKILL.md file.

```markdown
# Task Group 005 Skill: ERP Finance & Compliance API Operations

## 1. Environment & API Access
- **Base URL**: `http://127.0.0.1:8005` (shared ERP/compliance API for task_group_005).
- **Key endpoint families** (exact paths may vary by task; prefer names stated in prompt):
  - Prepaid invoices: `/prepaids/invoices` or `/api/prepaids/invoices`
  - GL balances: `/gl/balances` or `/api/prepaids/gl-balances`
  - Vendor/compliance endpoints (onboarding, account-change review)
  - Claims, AP bills, payments, close-log records (reimbursement close tasks)
- Always use the runner-provided API base URL rather than local files as the system of record, unless the prompt explicitly says otherwise.

## 2. Output Conventions
- Return **exactly one JSON object** matching the provided `answer_template.json` schema.
- Do not include narrative text outside the JSON.
- **No extra properties** are allowed unless the template explicitly permits them.
- All ID lists must be sorted **ascending** (lexicographically) unless the template specifies a different order (e.g., "same order as scope JSON").
- Currency amounts:
  - Default: **USD with 2 decimal places** (e.g., `1842.36`).
  - When template says "USD cents": use integer cents.
- Boolean values: use JSON `true`/`false` (not strings).

## 3. Task-Type Decision Rules

### 3.1 Reimbursement-to-AP Close Review (train_001 style)
**Goal**: Separate claims into paid, payable, and blocked categories.

- **`paid_claim_ids`**: Claims with a matching paid AP bill **and** cleared payment for the claim amount.
- **`payable_claim_ids`**: Approved claims with valid open AP reimbursement bills that can remain in the queue.
- **`blocked_claim_ids`**: Claims not paid and should not be released to AP until expense case or AP link is corrected.
- **`crm_required_claim_ids`**: Subset of blocked claims specifically requiring expense-case owner cleanup or AP-link remediation.
- **`ap_open_balance_total`**: Sum of valid open AP reimbursement bills for **payable** claims only, USD 2 decimals.
- **`batch_status`** (priority order):
  1. `"blocked"` — if any batch item is blocked.
  2. `"open_payables"` — if valid unpaid AP reimbursement bills remain (and nothing is blocked).
  3. `"ready_to_close"` — if all items are either paid or clean with no open payables.
- **`reviewed_claim_count`**: Total number of claim IDs reviewed in the requested batch.

### 3.2 Vendor Onboarding Release (train_002 style)
**Goal**: Determine per-business release decisions based on compliance flags.

- **`per_business`**: List of objects, each with `business_id` and `decision`, sorted ascending by `business_id`.
  - `"escalate"`: Any hard-stop compliance flag is present.
  - `"awaiting_information"`: Missing information or screening not run (no hard stops).
  - `"approve"`: Clean — no hard stops and all required info present.
- **`hard_stop_flags`**: Object mapping each `business_id` to a list of applicable flags, sorted **alphabetically**.
  - Known flag values: `bank_closed`, `bank_name_mismatch`, `confirmed_pep`, `expired_license`, `missing_required_documents`, `sanctions_confirmed`, `screening_not_run`, `shell_company_suspected`, `vendor_on_hold`.
  - Use empty list `[]` when none apply.
- **`reportable_ubo_counts`**: Integer count of unique beneficial-owner names at or above the reporting threshold (0 if none).
- **`follow_up_business_ids`**: All business IDs that are **not** approved (escalate + awaiting_information), sorted ascending.
- **`overall_release_ready`**: `true` only if **every** listed business can be released (i.e., all decisions are `"approve"`). Otherwise `false`.

### 3.3 Prepaid Close Reconciliation (train_003 style)
**Goal**: Reconcile prepaid invoice schedules against GL balances for a close period.

- **Amortization**: Use straight-line monthly amortization as represented in the invoice records.
- **`account_rollup`**: One entry per scoped account (e.g., `"1250"`, `"1251"`).
  - `variance_amount` = `schedule_ending_balance` - `gl_ending_balance` (signed value).
  - `variance_flag` = `true` if `|variance_amount| > variance_threshold_abs` (from scope JSON).
  - `has_default_missing_term_flag` = `true` if any invoice in the account uses a default/missing term.
  - `account_status`:
    - `"reconciled"` — no variance, no missing terms.
    - `"variance_review"` — variance exists but no missing terms.
    - `"requires_reconciliation"` — missing terms exist or large variance.
- **`invoice_results`**: One object per `selected_prepaid_invoice_id`, in the **same order as the scope JSON**.
  - `default_missing_term_flag`: `true` when the invoice lacks explicit term info and uses a default.
  - `exception_flag`: `true` for data quality issues (zero ending balance with remaining amortization, amount mismatches, etc.).
- **`default_missing_term_invoice_ids`**: All invoices with `default_missing_term_flag: true`, sorted ascending.
- **`exception_invoice_ids`**: All invoices with `exception_flag: true`, sorted ascending.
- All currency fields: USD with 2 decimals.

### 3.4 Stale AP Snapshot Reconciliation (train_004 style)
**Goal**: Reconcile a stale AP export against live API data.

- Treat the local snapshot as **context only**, not the system of record. Use live API for claim, bill, payment, and close-log records.
- **`eligible_claim_ids`**: Claims that can remain in the batch after current ERP reconciliation, sorted ascending.
- **`not_ready_claim_ids`**: Claims that should not remain due to current claim/bill/payment/support issues, sorted ascending.
- **`ap_balance_by_claim`**: Open AP balance per candidate claim after applying cleared payments and ignoring stale/voided rows. Include **all** candidate claims, zero if none.
- **`stale_snapshot_corrections`**: Object mapping each candidate claim ID to a correction code:
  - `"current_snapshot_ok"`, `"mark_in_flight_payment"`, `"replace_with_matched_paid_bill"`, `"exclude_amount_or_vendor_mismatch"`, `"ignore_void_bill"`, `"block_unapproved_claim"`.
- **`close_log_required`**:
  - `required`: `true` if any close log IDs are found in the API.
  - `ids`: Close log IDs, sorted ascending.
- **`batch_status`**:
  - `"blocked"` — if any claim is blocked.
  - `"needs_ap_refresh"` — if stale corrections are needed but not blocked.
  - `"ready_to_send"` — if everything is clean.

### 3.5 Account-Change Release Review (train_005 style)
**Goal**: Determine release posture after vendor account-change events.

- **`task_id`**, **`batch_id`**, **`as_of_date`**: Use exact required values from the template.
- **`target_business_ids`**: All business IDs in the batch, sorted ascending.
- **`decisions`**: Object mapping each `business_id` to:
  - `"escalate"` — hard compliance issues (expired license, invalid tax, confirmed PEP/sanctions, etc.).
  - `"hold"` — moderate issues (bank mismatch, elevated risk, missing docs).
  - `"release"` — clean for payment.
- **`bank_mismatch_ids`**: Business IDs where compliance `bank_account_status` is `name_mismatch`, sorted ascending.
- **`invalid_tax_ids`**: Business IDs with failed tax validation, sorted ascending.
- **`expired_license_ids`**: Business IDs with license expired as of `as_of_date`, sorted ascending.
- **`review_queue_ids`**: All business IDs requiring compliance/AP review before release (typically hold + escalate), sorted ascending.
- **`risk_score_override_flags`**: Business IDs with `risk_score >= 70`, sorted ascending.

## 4. Sorting & Rounding Rules
| Field Type | Sort Order | Precision |
|------------|-----------|-----------|
| Claim IDs | Ascending lexicographic | — |
| Business IDs | Ascending lexicographic | — |
| Invoice IDs | Ascending (or scope order if template says so) | — |
| Hard-stop flags | Alphabetical | — |
| Close log IDs | Ascending lexicographic | — |
| USD amounts | — | 2 decimal places |
| Integer counts | — | Whole number |

## 5. Common Pitfalls
- **Do not use local files as the system of record** when the prompt says to use the API. Local payloads are context, not truth.
- **Batch status priority**: `blocked` always wins over `open_payables`/`needs_ap_refresh`, which always wins over `ready_to_close`/`ready_to_send`.
- **`overall_release_ready`** is `true` only if **all** businesses are approved — one escalation makes it `false`.
- **Empty lists vs. missing keys**: Always include keys from the template; use empty lists `[]` or `0` or `false` when nothing applies.
- **Variance sign matters**: `schedule_ending_balance - gl_ending_balance` (not absolute value).
- **Prepaid invoice order**: `invoice_results` must follow the scope JSON order, but `default_missing_term_invoice_ids` and `exception_invoice_ids` must be sorted ascending.
- **Do not guess endpoint names** — use the exact paths mentioned in the prompt or `environment_access.md`.
```
