# Finance Close Reconciliation Patterns

Every task in this domain follows a common shape: a batch of candidate IDs is
provided, a JSON answer template defines the output schema, and the shared API
is the system of record. The solver cross-references records across endpoints,
applies business rules, and populates the template.

## General Workflow

1. Read the prompt and identify the candidate IDs and the answer template path.
2. Read the answer template to understand output fields and their allowed values.
3. Query the API for each candidate ID across all relevant endpoints.
4. Apply the business rules described below for the task type.
5. Populate the template with computed values and sorted lists.

**Sorting rules** (universal):
- Claim ID lists: ascending lexicographically by claim_id
- Business ID lists: ascending lexicographically by business_id
- Close log ID lists: ascending lexicographically by log_id
- Invoice ID lists as specified in the template (typically ascending)

**Currency rules** (universal):
- All amounts in USD with 2-decimal precision
- No rounding until final output; intermediate computations keep full precision

---

## Pattern A: Claims-to-AP Reconciliation

**Triggering signals in the prompt:** "expense claims", "AP batch", "reimbursement",
"close review", claim IDs in the batch as CLM-YYYY-XXXX-XXX or CLM-YYYY-NNNN.

### Endpoints needed

- `/api/claims` — get claim status, amount, vendor_id
- `/api/ap/bills` — find bills linked by claim_id
- `/api/ap/payments` — find payments linked to those bills
- `/api/ap/aging` — pre-joined billing+payment view with balances

### Classification logic

For each claim_id in the batch:

1. **Fetch the claim** from `/api/claims?claim_id=...`. If status is not approved
   (or has blocking flags like `over_limit`, `missing_receipt`, `late_receipt`,
   `weekend_spend`), classify as **blocked** — the claim itself is not ready.

2. **Fetch linked AP bills** from `/api/ap/aging?claim_id=...` or
   `/api/ap/bills?claim_id=...`. Typically one bill per claim for reimbursement
   batches.

3. **Check bill and payment state:**
   - If a bill is `paid` and has a corresponding `cleared` payment for the claim
     amount → **paid** (settled).
   - If a bill is `scheduled` or `approved` with no payment → **payable** (can
     stay in batch).
   - If a bill is `void` → the claim is **blocked**.
   - If no bill exists → the claim is **blocked**.
   - If bill amount does not match claim amount, or vendor mismatch → **blocked**.

4. **AP open balance**: sum of bill `balance` fields (or `amount - paid_amount`)
   for payable claims only.

5. **CRM required**: blocked claims where the issue is on the claim side (missing
   receipt, policy flag, unapproved). AP-link issues (missing bill, void bill,
   amount mismatch) are blocked but distinguished in prompts that ask for this
   split. When the output has both `blocked_claim_ids` and `crm_required_claim_ids`,
   `crm_required_claim_ids` is a subset of `blocked_claim_ids`.

6. **Batch status**:
   - `blocked`: any claim is blocked
   - `open_payables`: no blocked claims, at least one payable claim
   - `ready_to_close`: no blocked claims and no payable claims (all paid)

### Stale snapshot variant

When the prompt includes a "stale AP snapshot" (CSV or JSON payload with
pre-recorded AP data), the workflow is:

1. Read the snapshot for context only — never treat it as current truth.
2. Query the live API for current claim, bill, and payment state.
3. For each candidate, compare snapshot fields to live API fields and assign a correction:
   - `current_snapshot_ok`: snapshot matches live state
   - `mark_in_flight_payment`: payment exists in live data that snapshot missed
   - `replace_with_matched_paid_bill`: live bill is paid with cleared payment,
     differing from snapshot
   - `exclude_amount_or_vendor_mismatch`: live bill amount or vendor differs
     from claim
   - `ignore_void_bill`: bill is void in live data
   - `block_unapproved_claim`: claim status is not approved in live data
4. Check close logs for the relevant period. If any open or in_review logs exist,
   `close_log_required.required` = true and list those log IDs.
5. `batch_status`:
   - `ready_to_send`: all eligible, no blocking issues
   - `needs_ap_refresh`: snapshot corrections needed but no blocking issues
   - `blocked`: any candidate is not ready

---

## Pattern B: Vendor Onboarding / Compliance Release

**Triggering signals:** "vendor onboarding", "finance-risk", "release call",
"compliance", "UBO", "hard stop", "sanctions", "screening", "PEP".

### Endpoints needed

- `/api/compliance/objects?business_id=...` — for each business ID
- `/api/vendors?vendor_id=...` — cross-reference vendor status for hold checks

### Classification logic

For each business_id:

1. Fetch compliance object. Derive hard-stop flags using the mapping in
   [api_catalog.md](api_catalog.md).
2. Fetch vendor to check for `vendor_on_hold` flag.
3. **Decision**:
   - `escalate`: any hard-stop flag that requires sanctions/legal intervention
     (`sanctions_confirmed`, `confirmed_pep`, `shell_company_suspected`,
     `bank_closed`, `bank_name_mismatch`, or `vendor_on_hold`).
   - `awaiting_information`: missing required documents, expired license,
     `screening_not_run`, or other incomplete checks — issues the business
     can remedy.
   - `approve`: no hard-stop flags present.
4. **reportable_ubo_counts**: count unique UBO names with total ownership at or
   above 25%. Sum ownership percentages per unique name; if the sum is >= 25,
   that UBO is reportable.
5. **follow_up_business_ids**: all business IDs whose decision is not `approve`,
   sorted ascending.
6. **overall_release_ready**: true only if all decisions are `approve`.

### Priority tie-break

When multiple hard-stop flags apply, escalate takes precedence over
awaiting_information. The presence of any escalate-triggering flag makes the
decision `escalate`.

---

## Pattern C: Prepaid Amortization Close

**Triggering signals:** "prepaid close", "amortization", "GL balance",
"prepaid schedule", "straight-line", "accounts 1250/1251".

### Endpoints needed

- `/api/prepaids/invoices?prepaid_invoice_id=...` — for each scoped invoice ID
- `/api/prepaids/gl-balances?account=...&period=...&entity=...` — for GL ending
  balances

### Classification logic

1. Fetch each prepaid invoice from the API.
2. Compute per-invoice results using the amortization rules in
   [api_catalog.md](api_catalog.md).
3. Roll up per account:
   - Sum `original_amount`, target month amortization, cumulative amortization
   - `schedule_ending_balance` = sum of per-invoice `ending_balance`
   - `variance_amount` = `schedule_ending_balance` - `gl_ending_balance`
   - `variance_flag` = true when |variance| > threshold (default 100.00 unless
     otherwise specified)
   - `has_default_missing_term_flag` = true if any invoice in the account has
     the flag set
   - `account_status`:
     - `reconciled`: no variance flag, no default/missing term for any invoice
     - `variance_review`: no variance flag but default/missing term invoices exist
     - `requires_reconciliation`: variance flag is true
4. `default_missing_term_invoice_ids`: invoice IDs where the flag is true,
   sorted ascending.
5. `exception_invoice_ids`: invoice IDs where `exception_flag` is true,
   sorted ascending.

### Exception flag criteria

An invoice is exceptional when:
- It has any `data_quality_flags` populated, OR
- Its `ending_balance` does not match a clean amortization expectation (non-zero
  balance past service_end, rounding anomalies, zero balance when partial
  amortization expected)

---

## Pattern D: Account-Change Payment Release

**Triggering signals:** "account-change", "payment release", "risk review",
"vendor account", "bank last4", "compliance review".

### Endpoints needed

- `/api/vendors?vendor_id=...` — for each business's linked vendor
- `/api/compliance/objects?business_id=...` — compliance and risk data

### Classification logic

For each business_id:

1. Fetch compliance object. Check:
   - `bank_account_status`: `name_mismatch` → add to `bank_mismatch_ids`
   - `tax_id`: if it appears invalid (e.g. from vendor cross-check or compliance
     inconsistency) → add to `invalid_tax_ids`
   - `license_expiry`: if < as_of_date → add to `expired_license_ids`
   - `risk_score`: if >= 70 → add to `risk_score_override_flags`
   - Any blocking compliance issue → add to `review_queue_ids`

2. **Decision**:
   - `escalate`: sanctions confirmed, PEP confirmed, shell company suspected,
     bank closed, or vendor on hold
   - `hold`: bank name mismatch, expired license, screening not run,
     missing documents, risk score >= 70 — issues requiring review but not
     immediate escalation
   - `release`: no flags or only minor flags that don't block payment

### Decision priority

`escalate` > `hold` > `release`. Any single escalate-triggering condition makes
the overall decision `escalate`. Hold-triggering conditions produce `hold` only
when no escalate conditions exist.

### ID list rules

All ID lists sorted ascending lexicographically. Use empty lists when no IDs
qualify.
