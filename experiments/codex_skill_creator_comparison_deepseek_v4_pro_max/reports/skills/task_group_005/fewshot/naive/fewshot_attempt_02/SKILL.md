---
name: erp-finance-review
description: Cross-reference ERP finance REST API endpoints with local batch payloads to produce classification, reconciliation, and risk-review decisions formatted to strict JSON answer templates.
---

# ERP Finance Batch Review

Use this skill when a task asks you to review a batch of claims, vendors, invoices, or account-change events against a shared ERP/compliance REST API and produce a JSON answer that conforms to a provided template. The pattern appears in four task families: claim-AP reconciliation, vendor compliance onboarding, prepaid close reconciliation, and stale-export refresh with account-change risk review.

## Core Workflow

Every task in this family follows the same skeleton. Follow it exactly, adapting only the endpoints and business rules to the task type.

1. **Read the answer template first.** The template file (usually `input/payloads/answer_template.json`) defines required keys, allowed enum values, ordering constraints, and field types. Every output must satisfy every constraint in the template.

2. **Read local payloads.** These provide the batch scope (claim IDs, business IDs, invoice IDs) and optionally context like stale snapshots or review notes. Local payloads are context, not system of record -- the API is always authoritative for current state.

3. **Use the API base URL from `<TASK_ENV_BASE_URL>`.** The runner injects this value. Do not hardcode it. The API supports dual-path routing: a short path (e.g. `/claims`) and a `/api/`-prefixed path (e.g. `/api/claims`). Try one and fall back to the other if the first returns an empty result or a 404. Both paths return the same schema.

4. **Fetch data from every relevant endpoint.** Cross-reference claims with bills, payments, close logs; vendors with compliance objects, ownership, registry, screening, and bank endpoints. Do not trust local payload claims about current state -- verify every item through the API.

5. **Apply the decision logic for the task type.** Use the classification tables in this skill. Decisions must be grounded in current API evidence, not in snapshot data or review notes.

6. **Format output exactly to the template.** Sorted lists ascending by ID, numeric precision to 2 decimal places (USD), enum values exactly as allowed, all required keys present. No extra keys. No narrative text outside the JSON.

## API Reference

All endpoints are GET. All return JSON arrays or objects. The API is read-only -- no POST, PUT, or DELETE.

| Resource | Short Path | `/api/` Path |
|---|---|---|
| Claims | `/claims` | `/api/claims` |
| Single claim | `/claims/{claim_id}` | `/api/claims/{claim_id}` |
| AP Bills | `/bills` | `/api/ap/bills` |
| Payments | `/payments` | `/api/ap/payments` |
| AP Aging | -- | `/api/ap/aging` |
| Vendors | `/vendors` | `/api/vendors` |
| Compliance objects | `/compliance/objects` | `/api/compliance/objects` |
| Compliance ownership | -- | `/api/compliance/ownership/{business_id}` |
| Compliance registry | -- | `/api/compliance/registry/{business_id}` |
| Compliance screening | -- | `/api/compliance/screening/{business_id}` |
| Compliance bank | -- | `/api/compliance/bank/{business_id}` |
| Prepaid invoices | `/prepaids/invoices` | `/api/prepaids/invoices` |
| GL balances | `/gl/balances` | `/api/prepaids/gl-balances` |
| Close logs | `/close/logs` | `/api/close/logs` |
| Health | `/health` | `/api/health` |

**Fetching strategy:** For list endpoints, fetch the full collection and filter client-side by the IDs in the batch scope. For single-resource endpoints (compliance ownership, registry, screening, bank), call once per business ID. Parallelize calls when the order does not matter.

**Dual-path fallback:** When fetching from a short path, if the response is `[]`, `{}`, or a 404, retry with the `/api/`-prefixed equivalent. The same applies in reverse. This handles environment variance without manual inspection.

## Data Handling Rules

These rules apply to every task type in this family.

- **ID lists are always sorted ascending.** Treat claim IDs, business IDs, and invoice IDs as strings and sort lexicographically ascending. Example: `CLM-2025-0037` before `CLM-2025-0038` before `CLM-2025-OPS-017` (digits sort before letters).

- **Currency amounts are USD with 2 decimal places.** Use standard rounding (half-up). Compute totals from individual line items, not from snapshot summaries.

- **Enum values must match the template exactly.** If the template allows `"blocked"`, do not write `"Blocked"` or `"BLOCKED"`. If the template allows `"escalate"`, do not write `"escalated"` or `"Escalate"`.

- **Empty lists use `[]`, not `null` or omission.** If no IDs qualify for a list field, output an empty array.

- **Count fields must include all scoped items.** `reviewed_claim_count`, `selected_invoice_count`, and similar counts must match the cardinality of the batch scope regardless of classification outcome.

- **Missing API data is not the same as clean data.** If an API endpoint returns no record for a given ID, treat it as an exception condition (block, flag, escalate) rather than assuming a clean pass.

## Task Type A: Claim-to-AP Reconciliation

Matches tasks where the prompt asks to classify expense claims against AP bill and payment records. The local payload may include a stale CSV snapshot.

**Relevant endpoints:** `/claims`, `/claims/{id}`, `/bills` or `/api/ap/bills`, `/payments` or `/api/ap/payments`, `/close/logs` (if close logs are referenced in the template or prompt).

**Classification logic:**

For each claim ID in the batch scope, look up the current claim, its associated AP bill, and payment records from the API. Use the most recent API state, not the snapshot.

*Payable:* The claim is approved, an AP bill exists for the claim amount, and no clearing payment has been recorded against that bill. Include it in `payable_claim_ids` (or `eligible_claim_ids`). The `ap_open_balance_total` sums the bill amounts for these claims.

*Paid:* A matching AP bill exists and a cleared payment exists for the full bill amount. Include in `paid_claim_ids`. These claims are already settled and should not enter the AP queue.

*Blocked / Not Ready:* Any claim that is not approved, has no AP bill, has a bill with a mismatched amount, has a voided bill, or has only partial payment support. Include in `blocked_claim_ids` (or `not_ready_claim_ids`). All blocked claims where the root cause is in the claim/expense system (not the AP/payment layer) go into `crm_required_claim_ids`.

**Stale snapshot corrections** (when a CSV export is provided as context): For each claim, compare the snapshot row to current API state and assign one of:

- `current_snapshot_ok` -- snapshot matches current API state.
- `mark_in_flight_payment` -- a payment was recorded after the snapshot was taken.
- `replace_with_matched_paid_bill` -- the snapshot bill was replaced or matched with a paid bill.
- `exclude_amount_or_vendor_mismatch` -- the bill amount or vendor does not match the claim.
- `ignore_void_bill` -- the bill has been voided since the snapshot.
- `block_unapproved_claim` -- the claim itself is not in an approved state.

**Batch status logic:**

- `blocked` -- any batch item is blocked.
- `needs_ap_refresh` or `open_payables` -- no items are blocked but unpaid AP bills remain.
- `ready_to_close` or `ready_to_send` -- all items are paid or have no open AP balance.

**Close log requirement:** When the template includes a `close_log_required` field, fetch from `/close/logs` and include any close log IDs relevant to the batch claims. Set `required: true` only when at least one relevant close log exists.

## Task Type B: Vendor Compliance Onboarding

Matches tasks where the prompt asks to review business/vendor IDs for onboarding release using compliance endpoints.

**Relevant endpoints:** `/vendors`, `/api/compliance/objects`, `/api/compliance/ownership/{business_id}`, `/api/compliance/registry/{business_id}`, `/api/compliance/screening/{business_id}`, `/api/compliance/bank/{business_id}`.

**Classification logic:**

For each business ID in the batch, fetch the vendor record and all four per-business compliance endpoints. Synthesize the evidence into a decision.

*Approve:* No hard-stop flags are present. All compliance checks pass (clean screening, valid bank, unexpired license, no sanctions, no PEP hits, vendor not on hold). Required documents are present. UBO data is complete.

*Awaiting Information:* The business has informational gaps that are not security-critical -- missing documents, screening not yet run, or incomplete UBO data -- but no confirmed sanctions, PEP, or shell-company indicators.

*Escalate:* Any hard-stop flag is triggered: confirmed PEP, sanctions confirmed, shell company suspected, expired license, bank closed, bank name mismatch, vendor on hold, or screening not run combined with other red flags.

**Hard stop flags** are drawn from the following vocabulary (use exactly these strings):

- `bank_closed`
- `bank_name_mismatch`
- `confirmed_pep`
- `expired_license`
- `missing_required_documents`
- `sanctions_confirmed`
- `screening_not_run`
- `shell_company_suspected`
- `vendor_on_hold`

Sort hard stop flags alphabetically per business. Use an empty list `[]` when none apply.

**UBO counts:** From the ownership endpoint, count distinct beneficial owner names at or above the reporting threshold. Report as a whole-number integer per business ID.

**Follow-up list:** Include every business ID that did not receive an `approve` decision. Sort ascending.

**overall_release_ready:** `true` only if every business in the batch received `approve`. Otherwise `false`.

## Task Type C: Prepaid Close Reconciliation

Matches tasks where the prompt asks to reconcile prepaid invoice schedules against GL balances for specific accounts and a specific period.

**Relevant endpoints:** `/prepaids/invoices` (or `/api/prepaids/invoices`), `/gl/balances` (or `/api/prepaids/gl-balances`).

**Amortization method:** Straight-line monthly. Each invoice record carries an `original_amount`, `term_months`, and `start_date`. Monthly amortization = `original_amount / term_months`.

**Cumulative amortization:** Count months from the start date through the close period (inclusive). Multiply the monthly amortization by that count. If the invoice starts after the close period, cumulative amortization is zero.

**Ending balance:** `original_amount - cumulative_amortization_through_period`. Clamp to zero (do not report negative balances).

**Invoice-level flags:**

- `default_missing_term_flag` -- `true` when the invoice record shows a term of 12 months (the system default) or when the term field is missing/null. This indicates the invoice term may not be the true contractual term.
- `exception_flag` -- `true` when the invoice has any data quality issue: zero or missing original amount, term of 1 month or less, start date after the close period but still included in scope, ending balance of exactly 0.00 but with nonzero cumulative amortization, or a term marked as default/missing.

**Account-level rollup:**

- `original_amount_total` -- sum of `original_amount` for all scoped invoices in the account.
- `period_amortization_total` -- sum of the current period's amortization for all scoped invoices in the account.
- `cumulative_amortization_through_period` -- sum of cumulative amortization through the close period.
- `schedule_ending_balance` -- sum of invoice-level ending balances.
- `gl_ending_balance` -- value from the GL balances endpoint for the account and period.
- `variance_amount` -- `schedule_ending_balance - gl_ending_balance`.
- `variance_flag` -- `true` when `|variance_amount|` exceeds the threshold specified in the scope payload (typically 100.00).
- `has_default_missing_term_flag` -- `true` when any invoice in the account has the default/missing term flag.
- `account_status` -- `"reconciled"` when no variance flag and no default term flag; `"variance_review"` when variance flag is true but no default term issues; `"requires_reconciliation"` when either variance flag is true and default term issues exist, or when the account has exception invoices.

**Invoice ordering:** Preserve the order from the scope payload for `invoice_results`. Account-level lists (`default_missing_term_invoice_ids`, `exception_invoice_ids`) are sorted ascending.

## Task Type D: Account-Change Payment Release

Matches tasks where the prompt asks to review vendor payment releases after bank account change events.

**Relevant endpoints:** `/vendors`, `/api/compliance/bank/{business_id}`, `/api/compliance/registry/{business_id}`, `/api/compliance/screening/{business_id}`, `/api/compliance/objects`, `/api/compliance/ownership/{business_id}`.

**Classification logic:**

For each business ID, fetch vendor data and all compliance endpoints. Cross-reference the vendor's bank details with the account-change ticket's requested bank last 4 digits and the compliance bank endpoint.

*Release:* All compliance checks pass. Bank details match between vendor record, compliance bank endpoint, and the change ticket. License is valid as of the review date. Screening is clean. No risk score override. Tax ID is valid.

*Hold:* One or more issues exist that are not immediate hard stops -- bank name mismatch (but account number still matches), expired license, or a risk score at or above 70. These require review but do not necessarily block release.

*Escalate:* A hard-stop condition exists -- bank mismatch where account number also changed, sanctions hit, confirmed PEP, shell company suspected, vendor on hold, or screening not run with other red flags.

**Derived lists** (all sorted ascending by business ID):

- `bank_mismatch_ids` -- business IDs where the compliance bank endpoint shows `account_status: "name_mismatch"` or where the change ticket's requested bank last 4 does not match the vendor's bank account.
- `invalid_tax_ids` -- business IDs where the registry endpoint shows an invalid or missing tax ID.
- `expired_license_ids` -- business IDs where the registry endpoint shows a license expiration date before the review date.
- `review_queue_ids` -- business IDs that did not receive a `release` decision.
- `risk_score_override_flags` -- business IDs where the vendor or compliance object shows a risk score of 70 or greater.

## Troubleshooting

**Empty API response:** Retry with the alternate path prefix. If both return empty, treat as missing data (escalate/block/flag).

**Claim with no matching bill:** Block the claim. The bill may not have been created yet or may exist under a different ID. Check the claims endpoint for a `bill_id` field to disambiguate.

**Payment amount mismatch:** If a payment exists but the amount does not match the bill, the claim is not fully paid. Treat the difference as an open AP balance.

**Invoice with zero term:** Treat as a data exception. Set `default_missing_term_flag: true` and `exception_flag: true`. Skip amortization calculation (monthly = 0) but still report the invoice in all rollups.

**GL balance not found for account/period:** Report the GL ending balance as 0.00 and set `variance_flag: true`. This ensures the reconciliation flags the missing data rather than silently passing.

**Multiple bills for one claim:** Use the most recent non-voided bill. If all bills are voided, the claim is blocked.

**Business ID not found in vendor endpoint:** Treat as escalate -- the vendor record may have been removed or the ID is invalid.

**Review date handling:** For license expiry checks, compare `license_expiry_date` from the registry endpoint against the `as_of_date` or `review_date` from the prompt. Expiry on or before the review date means the license is expired.
