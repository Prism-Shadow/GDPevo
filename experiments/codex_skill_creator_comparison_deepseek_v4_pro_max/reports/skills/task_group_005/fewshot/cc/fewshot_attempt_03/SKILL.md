---
name: erp-finance-api-audit
description: >
  Audit and reconcile ERP finance operations using a shared JSON API environment.
  Use this skill whenever the task involves cross-referencing claims, AP bills,
  payments, compliance records, prepaid schedules, GL balances, vendor records,
  close logs, or any combination across those domains to produce structured
  JSON decisions for close, release, onboarding, or reconciliation workflows.
  Trigger on phrases like "reimbursement-to-AP close", "onboarding release",
  "prepaid close check", "stale AP reconciliation", "account-change release",
  "ERP audit", "finance API review", "payment release risk review", or any
  request to reconcile or decide across multiple finance/ERP endpoints.
---

# ERP Finance API Audit

Work exclusively with the shared ERP JSON API at the base URL supplied by the
runner as `<TASK_ENV_BASE_URL>`. Never use local files as the system of record
when the API is available. Treat any local payloads (CSV snapshots, JSON batch
files) as context only, not as the authoritative data source.

## API Navigation

All endpoints accept filtering via exact-match query parameters named after the
record fields. Use `limit` and `offset` for pagination. Call `/endpoints` first
to confirm which endpoints are live.

Common endpoints and their record shapes:

### Claims (`/claims` or `/api/claims`)

Key fields: `claim_id`, `amount`, `status`, `approved_date`, `policy_flags`,
`receipt_status`, `vendor_id`, `department`, `employee_name`, `category`,
`notes`.

Status values include: `approved`, `paid`, `needs_receipt`, `submitted`,
`rejected`. A claim is "approved" only when status is `approved` or `paid`. A
claim is not ready for AP when status is `needs_receipt` or `submitted` or
`rejected`.

### AP Bills (`/bills` or `/api/ap/bills`)

Key fields: `bill_id`, `claim_id`, `amount`, `status`, `vendor_id`, `account`,
`balance` (aging view only), `paid_amount` (aging view only).

Status values: `paid`, `scheduled`, `approved`, `draft`, `void`.

A bill is "settled" when status is `paid`. A bill is void/unusable when status
is `void`. A bill is in-flight when status is `scheduled` or `approved` with a
non-zero balance or pending payment. When multiple bills share the same
`claim_id`, prefer the bill whose `amount` matches the claim `amount`; a
mismatch is evidence of a data-quality problem.

### Payments (`/payments` or `/api/ap/payments`)

Key fields: `payment_id`, `bill_id`, `amount`, `status`, `payment_date`,
`vendor_id`, `method`, `bank_reference`.

Status values: `cleared`, `processing`, `scheduled`. A bill with a `cleared`
payment is fully settled. A `processing` or `scheduled` payment means the
cash has not definitively landed.

### AP Aging (`/api/ap/aging`)

Provides a consolidated bill view with `balance` (= `amount` minus
`paid_amount`). Use this as a shortcut when only the net AP position is needed,
but prefer the raw bills and payments endpoints when you need status details.

### Vendors (`/vendors` or `/api/vendors`)

Key fields: `vendor_id`, `vendor_name`, `legal_name`, `status`, `tax_id`,
`bank_account_last4`, `default_account`, `industry`, `payment_terms`,
`updated_at`.

Vendor status values include `active`, `on_hold`. A vendor on hold is a risk
signal.

### Compliance (`/compliance/objects` or `/api/compliance/objects`)

Consolidated per-business view. Key fields: `business_id`, `business_name`,
`vendor_id`, `jurisdiction`, `registration_number`, `tax_id`, `license_expiry`,
`bank_account_status`, `pep_status`, `sanctions_check_status`,
`shell_company_suspected`, `risk_score`, `review_status`, `missing_fields`,
`ownership_layer_count`, `ubo_list`.

Single-facet endpoints also available:
- `/api/compliance/ownership/{business_id}` — `ubo_list`,
  `ownership_layer_count`, `shell_company_suspected`
- `/api/compliance/registry/{business_id}` — `tax_id`, `license_expiry`,
  `jurisdiction`, `registration_number`
- `/api/compliance/screening/{business_id}` — `pep_status`,
  `sanctions_check_status`
- `/api/compliance/bank/{business_id}` — `bank_account_status`

### Prepaid Invoices (`/prepaids/invoices` or `/api/prepaids/invoices`)

Key fields: `prepaid_invoice_id`, `account`, `original_amount`,
`monthly_amortization`, `service_start`, `service_end`, `recognition_method`,
`data_quality_flags`, `invoice_date`, `vendor_id`, `description`,
`source_document`.

Recognition method is always `straight_line`. Amortization is the
`monthly_amortization` value from the record.

### GL Balances (`/gl/balances` or `/api/prepaids/gl-balances`)

Key fields: `account`, `account_name`, `period`, `ending_balance`, `entity`.

Filter by `account` and `period` to get the GL ending balance for a specific
close period.

### Close Logs (`/close/logs` or `/api/close/logs`)

Key fields: `log_id`, `area`, `period`, `status`, `message`, `owner`,
`related_account`.

Areas include `AP`, `Expense`, `Prepaids`, `GL`, `Compliance`, `Treasury`.
Status values: `closed`, `ready_for_review`.

## Cross-Reference Patterns

### Claims → Bills → Payments

For a batch of candidate claim IDs:

1. Fetch each claim by `claim_id`.
2. Fetch all bills and filter to those whose `claim_id` appears in the batch.
   A single claim may link to multiple bills; check amounts against the claim.
3. Fetch payments and match to bills by `bill_id`.
4. Classify each claim by the combined evidence.

### Business → Compliance

For a batch of candidate business IDs:

1. Fetch `/api/compliance/objects` for each business (consolidated). Supplement
   with individual facet endpoints when deeper detail is needed.
2. Cross-reference `vendor_id` from compliance with `/api/vendors` to check
   vendor status, bank last-4, and tax ID consistency.

### Prepaid → GL Reconciliation

1. Fetch prepaid invoices filtered to the scope invoice IDs.
2. Fetch GL balances for the target accounts and close period.
3. For each invoice compute:
   - `months_elapsed` = number of whole months from `service_start` through the
     close-period end (inclusive).
   - `period_amortization` = `monthly_amortization` (the amortization for the
     target close month).
   - `cumulative_amortization` = `months_elapsed` × `monthly_amortization`.
   - `ending_balance` = round(`original_amount` − `cumulative_amortization`, 2).
4. Sum per-account totals and compare to GL ending balances.
5. **Variance rounding**: When `original_amount` and `monthly_amortization`
   produce a non-zero ending balance < 0.02 due to floating-point rounding,
   treat the variance as a rounding artifact, not a material variance. Check
   whether `original_amount` is evenly divisible by `monthly_amortization` to
   confirm this.

## Decision Frameworks

### Claim Reimbursement Status

For each claim in a batch, classify into one of three buckets:

**Paid** — ALL of:
- Claim status is `paid`, AND
- A matching bill exists (amount matches claim amount), AND
- The bill status is `paid` or has a `cleared` payment covering it, AND
- No unresolved policy flags that would block settlement.

**Payable** — ALL of:
- Claim status is `approved`, AND
- A matching bill exists with amount matching the claim, AND
- The bill is not void, AND
- Either the bill has a positive balance or a payment is
  `processing`/`scheduled` (not yet `cleared`), AND
- No policy-flag or receipt-status issues that require CRM intervention.

**Blocked** — ANY of:
- Claim status is not `approved` and not `paid`, OR
- No matching AP bill exists, OR
- The matching bill is `void`, OR
- The claim amount differs materially from the bill amount, OR
- The vendor on the bill does not match the claim's vendor (when the claim has
  one), OR
- Policy flags (`over_limit`, `late_receipt`, `duplicate_amount`, etc.) or
  receipt status (`partial`, `missing`) indicate the expense case needs owner
  cleanup before AP release, OR
- A matching bill exists but the payment chain has unresolved problems (stale
  scheduled payment, amount mismatch between bill and payment).

Within blocked, separate **CRM-required** claims (those with policy-flag or
receipt-status root causes) from AP-only issues. CRM-required means the expense
owner must fix the case before AP can proceed.

**Batch status**: `blocked` if any claim is blocked; otherwise `open_payables`
if any payable claims remain; otherwise `ready_to_close`.

### Open AP Balance

Sum the valid open AP reimbursement bill amounts for payable claims only.
Exclude paid, void, and blocked-claim bills. For claims where a payment is
processing, use the bill amount (not zero) because the payment has not cleared.

### Compliance / Vendor Onboarding Risk

**Hard-stop flags** — check all that apply per business:

| Flag | Source / Condition |
|---|---|
| `confirmed_pep` | `pep_status` is `confirmed_pep` |
| `sanctions_confirmed` | `sanctions_check_status` is `confirmed` |
| `screening_not_run` | `pep_status` is `not_run` or `sanctions_check_status` is `not_run` |
| `expired_license` | `license_expiry` is before the review date AND license is not listed in `missing_fields` |
| `missing_required_documents` | `missing_fields` is non-empty |
| `bank_closed` | `bank_account_status` is `closed` |
| `bank_name_mismatch` | `bank_account_status` is `name_mismatch` |
| `shell_company_suspected` | `shell_company_suspected` is `true` |
| `vendor_on_hold` | Vendor `status` is `on_hold` |

**Decision per business**:
- `escalate` — Any hard-stop flag that represents a confirmed risk or
  compliance violation: `confirmed_pep`, `sanctions_confirmed`,
  `bank_closed`, `bank_name_mismatch`, `shell_company_suspected`,
  `expired_license`, `vendor_on_hold`. Escalate also when multiple
  lesser flags combine to create an unacceptable risk profile.
- `awaiting_information` — Only information-gap flags without confirmed
  risks: `screening_not_run`, `missing_required_documents` (and no
  escalate-level flags present).
- `approve` — No hard-stop flags of any kind.

**UBO counts**: Count **unique owner names** from `ubo_list` whose
`ownership_pct` meets whatever reporting threshold the task specifies.
When the task does not specify a threshold, default to 25% (inclusive).
Two entries for the same name count as one UBO.

**Follow-up**: Every business not decided `approve` goes into
`follow_up_business_ids`.

**Overall release**: `true` only when every business is `approve`.

### Prepaid Close Check

**Per-invoice computation** for a given close period:

1. `months_elapsed` = count of calendar months where the service is active,
   from `service_start` month through the close month (inclusive). A service
   starting Jan 1 with close in March = 3 months.
2. `period_amortization` = `monthly_amortization` (for the close month).
3. `cumulative_amortization` = `months_elapsed` × `monthly_amortization`.
4. `ending_balance` = round(`original_amount` − `cumulative_amortization`, 2).

**Exception flag**: `true` when the invoice has any `data_quality_flags` or
the `ending_balance` is exactly 0.00 (fully amortized, which may indicate the
invoice is complete and no longer needs active accrual tracking).

**Default/missing term flag**: `true` when `data_quality_flags` includes
`missing_contract_dates` or equivalent indicators that contract terms are
incomplete.

**Account rollup**: For each account:

- Sum `original_amount`, `period_amortization`, `cumulative_amortization`
  across all selected invoices for that account.
- `schedule_ending_balance` = sum of per-invoice `ending_balance`.
- `variance_amount` = `schedule_ending_balance` − `gl_ending_balance`.
- `variance_flag` = `true` if `abs(variance_amount)` > the task's variance
  threshold (default 100.00 if none given).
- `has_default_missing_term_flag` = `true` if any invoice in the account has a
  default/missing term flag.
- `account_status`: `requires_reconciliation` if `variance_flag` is true;
  otherwise `variance_review` if within threshold but non-zero; otherwise
  `reconciled`.

### Stale AP Snapshot Reconciliation

When a local CSV or JSON snapshot provides prior AP state, compare each
snapshot row to the live API:

1. Fetch the claim by `claim_id` from `/api/claims`.
2. Fetch all bills for that claim and identify the correct current bill.
3. Fetch payments for each bill.
4. Classify the correction needed:

| Correction | Condition |
|---|---|
| `current_snapshot_ok` | Snapshot matches current API state. |
| `mark_in_flight_payment` | A payment now exists that the snapshot did not record. |
| `replace_with_matched_paid_bill` | The snapshot references a stale/wrong bill; the correct bill is now paid/cleared. |
| `exclude_amount_or_vendor_mismatch` | Claim amount ≠ bill amount, or vendor mismatch between claim and bill. |
| `ignore_void_bill` | The snapshot's bill is now void in the API. |
| `block_unapproved_claim` | The claim is not approved in the current API (status is `needs_receipt`, `submitted`, etc.). |

**Eligibility**: A claim is eligible for the batch only when its current API
state is clean (approved claim, valid matching bill, no amount/vendor mismatch,
no void bill, matching cleared payment or in-flight payment with no blocking
issues).

**Close log relevance**: When the API contains close logs in the `AP` or
`Expense` area for the relevant period, include them in the output when they
provide evidence for corrections (manual journal entries, variance reviews,
support uploads). Reference specific `log_id` values from the API, not
fabricated ones.

**Batch status**: `ready_to_send` when all claims are eligible and have
`current_snapshot_ok`; `blocked` when no claims are eligible;
`needs_ap_refresh` when some claims need correction but eligible claims remain.

### Account-Change Payment Release Review

When a local batch payload lists business IDs with account-change events and
requested bank last-4 values:

1. Fetch `/api/compliance/objects` and `/api/vendors` for each business.
2. Compare the requested `bank_last4` from the payload against the vendor's
   `bank_account_last4`. Mismatch → `bank_mismatch_ids`.
3. Check `tax_id` from compliance registry. A valid tax ID follows the
   pattern `TIN` + exactly 6 decimal digits. Flag tax IDs that contain
   non-digit characters after the `TIN` prefix, have unusual lengths, or are
   all-9s placeholders (e.g. `TIN999999`). Flag in `invalid_tax_ids`.
4. Check `license_expiry` against the review date. Flag expired licenses in
   `expired_license_ids`.
5. Check `risk_score` from compliance objects. Flag scores ≥ 70 in
   `risk_score_override_flags`.

**Decision per business**:
- `release` — No flags of any kind. Bank matches, license valid, tax ID valid,
  PEP/sanctions clear, vendor active, risk score acceptable, bank account
  verified, screening complete.
- `hold` — Flags present but manageable (bank name mismatch, expired license,
  screening not run, closed bank). Not severe enough to require escalation
  but needs review before release.
- `escalate` — Severe flags: `confirmed_pep`, `sanctions_confirmed`,
  `shell_company_suspected`, `vendor_on_hold`, an invalid tax ID combined
  with other issues, or multiple serious flags together.

**Review queue**: Every business not decided `release` goes into
`review_queue_ids`.

## Output Conventions

### JSON Format

- Always return valid JSON matching the provided answer template exactly.
- Do not include narrative text, markdown fences, or commentary outside the
  JSON object.
- Use the template's key names, ordering, and types precisely.

### Currency

- All amounts in USD with exactly two decimal places.
- Use the raw numeric values from the API; do not apply rounding beyond what
  is needed for floating-point precision at the hundredths place.

### ID Lists

- Sort claim IDs, business IDs, and invoice IDs **ascending** unless the
  template explicitly specifies a different order (e.g., matching a scope
  file's order).
- Use empty lists (`[]`) when no items qualify, never `null` or omitted keys.

### Enum Values

- Use only the enum values defined in the answer template. Do not invent new
  status strings. If a template field restricts to `["release", "hold",
  "escalate"]`, use only those three.

## Workflow Order

When a task spans multiple data domains, follow this sequence:

1. **Fetch all API data first** — query every needed endpoint in parallel
   before making decisions. Batch queries by claim_id, business_id, or
   invoice_id using filters when the API supports it.
2. **Cross-reference in memory** — build in-memory maps (claim→bills,
   bill→payments, business→compliance facets) to resolve links.
3. **Apply decision rules** — classify each item using the frameworks above.
4. **Compute aggregates** — sum totals, count flags, determine batch status.
5. **Validate against the template** — check that every required key is
   present, every enum is valid, and every list is in the correct order.
6. **Output the single JSON object**.

## Edge Cases

- **Multiple bills per claim**: A claim may have several bills. Match by
  amount first; if amounts differ, flag the mismatch. If one bill is paid and
  another is not, prefer the paid one when the claim is paid.
- **Payment amounts not matching bills**: The payment `amount` may differ from
  the bill `amount` (partial payments). Use the `aging` endpoint's
  `paid_amount` and `balance` fields to verify net position.
- **Round-trip precision**: When `original_amount` divided by
  `monthly_amortization` does not produce an integer, the cumulative
  amortization may have a sub-cent discrepancy. Accept ending balances in
  [−0.01, 0.01] as essentially zero.
- **Missing vendor link**: A claim without a `vendor_id` is not necessarily
  blocked; only flag a vendor mismatch when both sides have a vendor and
  they differ.
- **Review date vs license expiry**: Use the task's explicit review date or
  `as_of_date`. When none is given, use the latest `payment_date` or
  `approved_date` from the data as a reasonable proxy.
- **Empty hard-stop flags**: Use an empty list `[]`, not `null`.
