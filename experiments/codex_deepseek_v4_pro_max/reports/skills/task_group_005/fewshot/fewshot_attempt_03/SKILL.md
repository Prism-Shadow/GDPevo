---
name: erp-finance-ops
description: ERP finance operations agent for AP close, vendor onboarding, prepaid reconciliation, stale-snapshot review, and account-change payment release. Use when the task involves claims-to-bills reconciliation, compliance screening, prepaid amortization schedules, stale AP snapshot correction, or vendor payment release review against the shared task_group_005 REST API.
---

# ERP Finance Operations Skill

## Overview

This skill provides reusable instructions for an agent that performs finance operations review tasks against a shared ERP/compliance REST API. The environment provides GET-only JSON endpoints for claims, AP bills, payments, vendors, compliance objects, prepaid invoices, GL balances, and close logs.

## API Mechanics

The runner provides the API base URL as `<TASK_ENV_BASE_URL>`. All endpoints are read-only (GET). There are no POST endpoints available for task execution.

### Endpoint Reference

Every endpoint is accessible through both a bare path and an `/api/`-prefixed path. The following endpoints are available:

| Resource | Collection Endpoint | Detail Endpoint |
|----------|-------------------|-----------------|
| Claims | `/claims` or `/api/claims` | `/api/claims/{claim_id}` |
| AP Bills | `/bills` or `/api/ap/bills` | — |
| Payments | `/payments` or `/api/ap/payments` | — |
| AP Aging | `/api/ap/aging` | — |
| Vendors | `/vendors` or `/api/vendors` | — |
| Compliance Objects | `/compliance/objects` or `/api/compliance/objects` | — |
| Compliance Ownership | — | `/api/compliance/ownership/{business_id}` |
| Compliance Registry | — | `/api/compliance/registry/{business_id}` |
| Compliance Screening | — | `/api/compliance/screening/{business_id}` |
| Compliance Bank | — | `/api/compliance/bank/{business_id}` |
| Prepaid Invoices | `/prepaids/invoices` or `/api/prepaids/invoices` | — |
| GL Balances | `/gl/balances` or `/api/prepaids/gl-balances` | — |
| Close Logs | `/close/logs` or `/api/close/logs` | — |

### Query Mechanics

- **Collection endpoints** accept exact-match query parameters by field name (e.g., `?claim_id=CLM-2025-0001`).
- Optional `limit` and `offset` query parameters are integers for pagination.
- **Detail endpoints** replace path placeholders such as `{claim_id}` or `{business_id}` with the identifier string.
- When a field is not filterable, fetch the full collection and filter client-side.
- Try the bare path first; if it returns an error, retry with the `/api/` prefix.

## Entity Model and Relationships

### Core Financial Entities

- **Claim**: An expense/reimbursement claim with fields including `claim_id`, `status` (e.g., `approved`, `pending`, `rejected`), `amount`, and metadata.
- **AP Bill**: An accounts-payable bill linked to a claim. Fields include `bill_id`, `claim_id`, `status` (e.g., `approved`, `scheduled`, `paid`, `void`), `amount`, and vendor/linkage fields.
- **Payment**: A cleared payment against a bill. Fields include `payment_id`, `bill_id`, `status` (e.g., `cleared`, `scheduled`, `none`), and `amount`.
- **Vendor**: A vendor record with fields including `vendor_id`, `business_id`, `status` (e.g., `active`, `on_hold`), `bank_last4`, and metadata.

### Compliance Entities

Compliance detail endpoints return objects keyed by `business_id`:

- **Ownership** (`/api/compliance/ownership/{business_id}`): Returns `ubo_records` — a list of ultimate beneficial owners with `name`, `ownership_percentage`, and `reporting_threshold_met` fields.
- **Registry** (`/api/compliance/registry/{business_id}`): Returns business registry information including `license_expiry_date`, `tax_id`, `tax_id_status`, and legal entity metadata.
- **Screening** (`/api/compliance/screening/{business_id}`): Returns screening results with fields like `screening_status` (e.g., `completed`, `not_run`), `pep_flag`, `sanctions_flag`, `adverse_media_flag`.
- **Bank** (`/api/compliance/bank/{business_id}`): Returns bank verification data with `bank_account_status` (e.g., `verified`, `name_mismatch`, `closed`), `bank_name`, and `last4`.

### Prepaid/GL Entities

- **Prepaid Invoice**: Fields include `prepaid_invoice_id`, `account` (e.g., `1250`, `1251`), `original_amount`, `term_months`, `start_date`, `monthly_amortization`, and `status`.
- **GL Balance**: Fields include `account`, `period` (e.g., `2025-03`), and `ending_balance`.

### Close Logs

- **Close Log**: Fields include `close_log_id` (e.g., `CLOSE-YYYY-MM-NNN`), `period`, `status`, and `claim_ids` or related references.

## Task Type 1: Claim-to-AP Reimbursement Close Review

Use when the task asks to review a batch of expense claim IDs and classify them for AP reimbursement close.

### Workflow

1. For each claim ID in the batch:
   - **Fetch the claim** via `GET /api/claims/{claim_id}`. Record its `status` and `amount`.
   - **Find matching AP bills** via `GET /bills?claim_id={claim_id}` (or `/api/ap/bills?claim_id={claim_id}`). There may be zero, one, or multiple bills.
   - **For each bill** with a non-void status, find payments via `GET /payments?bill_id={bill_id}` (or `/api/ap/payments?bill_id={bill_id}`).

2. Classify each claim:
   - **paid**: The claim has a paid/settled bill with a matching cleared payment for the claim amount.
   - **payable**: The claim is approved and has an approved or scheduled AP bill with an unpaid balance — it can stay in the reimbursement queue.
   - **blocked**: The claim is not paid and should not be released. Reasons include: no matching bill, void bill, amount mismatch between claim and bill, unapproved claim status, or payment/bill status inconsistency.
   - **crm_required**: A subset of blocked claims that need expense-case owner cleanup or AP-link remediation.

3. Compute `ap_open_balance_total`: Sum of open (unpaid) bill amounts for payable claims only, in USD with 2 decimal precision.

4. Set `batch_status`:
   - `"blocked"` if any claim in the batch is blocked.
   - `"open_payables"` if no blocked claims but unpaid AP bills remain.
   - `"ready_to_close"` if all claims are settled (paid) with no open balances.

5. Set `reviewed_claim_count` to the number of claim IDs examined.

6. All claim ID lists must be sorted ascending alphabetically.

### Output Fields

- `payable_claim_ids` — list of claim IDs that can stay in the AP queue.
- `blocked_claim_ids` — list of claim IDs not ready for AP release.
- `paid_claim_ids` — list of claim IDs with matching paid bills and cleared payments.
- `ap_open_balance_total` — number (USD, 2 decimals), total of open AP bills for payable claims.
- `crm_required_claim_ids` — subset of blocked claims needing owner cleanup.
- `batch_status` — one of `"ready_to_close"`, `"open_payables"`, `"blocked"`.
- `reviewed_claim_count` — integer count of claims reviewed.

## Task Type 2: Vendor Onboarding Finance-Risk Release Review

Use when the task asks to evaluate vendor onboarding candidates for release readiness using compliance evidence.

### Workflow

1. For each business ID in the onboarding batch:
   - **Fetch vendor** via `GET /vendors?business_id={business_id}` (or `/api/vendors`). Check `status` (e.g., `active`, `on_hold`).
   - **Fetch compliance ownership** via `GET /api/compliance/ownership/{business_id}`. Count unique UBO names where `reporting_threshold_met` is true for `reportable_ubo_counts`.
   - **Fetch compliance registry** via `GET /api/compliance/registry/{business_id}`. Check `license_expiry_date` against the review date and `tax_id_status`.
   - **Fetch compliance screening** via `GET /api/compliance/screening/{business_id}`. Check `screening_status`, `pep_flag`, `sanctions_flag`.
   - **Fetch compliance bank** via `GET /api/compliance/bank/{business_id}`. Check `bank_account_status`.

2. Collect hard stop flags (alphabetical order per business):
   - `"bank_closed"` — bank_account_status is `closed`.
   - `"bank_name_mismatch"` — bank_account_status is `name_mismatch`.
   - `"confirmed_pep"` — screening PEP flag is true.
   - `"expired_license"` — license_expiry_date is before the review date.
   - `"missing_required_documents"` — required compliance documents are absent or incomplete.
   - `"sanctions_confirmed"` — sanctions flag is true.
   - `"screening_not_run"` — screening_status is `not_run` or absent.
   - `"shell_company_suspected"` — ownership/registry indicates shell risk.
   - `"vendor_on_hold"` — vendor status is `on_hold`.

3. Determine `decision` per business:
   - `"approve"` — no hard stop flags, all evidence is clean.
   - `"awaiting_information"` — some evidence is missing/incomplete but no hard stop.
   - `"escalate"` — one or more hard stop flags are present.

4. `follow_up_business_ids`: All business IDs not approved, sorted ascending.

5. `overall_release_ready`: `true` only if every business decision is `"approve"`.

### Output Fields

- `per_business` — list of objects with `business_id` and `decision`, sorted ascending by business_id.
- `reportable_ubo_counts` — object mapping business_id to integer count of reportable UBOs.
- `hard_stop_flags` — object mapping business_id to list of flag strings (empty list if none, sorted alphabetically).
- `follow_up_business_ids` — list of business IDs needing follow-up.
- `overall_release_ready` — boolean.

## Task Type 3: Prepaid Amortization Close Reconciliation

Use when the task asks to prepare a prepaid expense close check with invoice-to-GL reconciliation for specific accounts.

### Amortization Methodology

Use **straight-line monthly amortization** as represented in the invoice records:

- **Monthly amortization**: `original_amount / term_months` (use the invoice record's `monthly_amortization` field when available).
- **Cumulative amortization through target month**: `monthly_amortization × months_passed` where `months_passed` is the number of months from `start_date` through the target period (inclusive).
- **Ending balance**: `original_amount - cumulative_amortization_through_march` (or through the target period). Floor at `0.00`.

### Workflow

1. Fetch all prepaid invoices via `GET /prepaids/invoices` (or `/api/prepaids/invoices`).
2. Filter to only the invoice IDs specified in the scope payload.
3. For each invoice, compute:
   - `march_amortization` (or target-period amortization) — the monthly amount.
   - `cumulative_amortization_through_march` (or through target period).
   - `ending_balance` — `original_amount - cumulative_amortization`.
   - `default_missing_term_flag` — `true` when `term_months` is absent, null, zero, or a default placeholder value.
   - `exception_flag` — `true` when the invoice has anomalies: zero or negative ending balance, rounding discrepancies, missing/inconsistent data, or amortization that doesn't match the straight-line expectation.

4. Fetch GL balances via `GET /gl/balances?account={account}&period={period}` (or `/api/prepaids/gl-balances`).

5. Per account, compute rollup:
   - `selected_invoice_count`, `original_amount_total`, `march_amortization_total`, `cumulative_amortization_through_march`, `schedule_ending_balance`.
   - `gl_ending_balance` — from the GL endpoint for that account and period.
   - `variance_amount` — `schedule_ending_balance - gl_ending_balance`.
   - `variance_flag` — `true` if `variance_amount != 0`.
   - `has_default_missing_term_flag` — `true` if any invoice in the account has `default_missing_term_flag` true.
   - `account_status` — `"requires_reconciliation"` if variance_flag is true or has_default_missing_term_flag is true; otherwise `"balanced"`.

6. Collect `default_missing_term_invoice_ids` and `exception_invoice_ids`, sorted ascending.

### Output Fields

- `period` — string in `YYYY-MM` format.
- `entity` — entity name string.
- `selected_invoice_ids` — list of invoice IDs in the same order as the scope payload.
- `account_rollup` — object keyed by account code with rollup fields.
- `invoice_results` — list of per-invoice objects, in scope payload order.
- `default_missing_term_invoice_ids` — sorted ascending.
- `exception_invoice_ids` — sorted ascending.

## Task Type 4: Stale AP Snapshot Reconciliation

Use when the task provides a localized AP export snapshot that must be reconciled against current API data.

### Workflow

1. For each candidate claim ID:
   - **Fetch the current claim** via `GET /api/claims/{claim_id}`.
   - **Fetch current AP bills** via `GET /bills?claim_id={claim_id}` (or `/api/ap/bills`).
   - **Fetch current payments** via `GET /payments?bill_id={bill_id}` for each bill.
   - Compare against the stale snapshot row for that claim.

2. Determine `stale_snapshot_corrections` per claim:
   - `"current_snapshot_ok"` — snapshot matches current system state.
   - `"mark_in_flight_payment"` — bill is scheduled with no payment yet in snapshot, but current state shows payment in flight.
   - `"replace_with_matched_paid_bill"` — snapshot shows a scheduled bill, but current state shows a paid bill with cleared payment.
   - `"exclude_amount_or_vendor_mismatch"` — snapshot amount or vendor differs from current API data.
   - `"ignore_void_bill"` — snapshot bill is now void in current state.
   - `"block_unapproved_claim"` — claim is not approved in current state, or has no valid bill.

3. Compute `ap_balance_by_claim`: For each candidate claim, determine the open AP balance using current data (ignoring stale or voided rows). A paid/cleared bill has balance 0.00.

4. Classify claims:
   - `eligible_claim_ids` — claims that can remain in the batch after reconciliation.
   - `not_ready_claim_ids` — claims that should not remain in the batch.

5. Check close logs via `GET /close/logs` (or `/api/close/logs`). Filter for logs relevant to the batch (e.g., by period or claim reference). Set `close_log_required.required` to `true` if any relevant close log exists, and include the log IDs.

6. Set `batch_status`:
   - `"ready_to_send"` — all claims eligible and no issues.
   - `"needs_ap_refresh"` — some claims need updated AP data but batch is not fully blocked.
   - `"blocked"` — critical issues prevent batch processing.

### Output Fields

- `eligible_claim_ids` — sorted ascending.
- `not_ready_claim_ids` — sorted ascending.
- `ap_balance_by_claim` — object mapping claim ID to open balance (USD, 2 decimals).
- `stale_snapshot_corrections` — object mapping claim ID to correction enum.
- `close_log_required` — object with `required` (boolean) and `ids` (list of close log IDs, sorted ascending).
- `batch_status` — one of `"ready_to_send"`, `"needs_ap_refresh"`, `"blocked"`.

## Task Type 5: Account-Change Payment Release Review

Use when the task asks to review vendor payment release after account-change events, using vendor and compliance endpoints.

### Workflow

1. For each business ID in the batch:
   - **Fetch vendor** via `GET /vendors?business_id={business_id}` (or `/api/vendors`). Record `vendor_id`, `status`, and `bank_last4`.
   - **Fetch compliance bank** via `GET /api/compliance/bank/{business_id}`. Check `bank_account_status`.
   - **Fetch compliance registry** via `GET /api/compliance/registry/{business_id}`. Check `tax_id_status`, `license_expiry_date`.
   - **Fetch compliance screening** via `GET /api/compliance/screening/{business_id}`. Check for risk indicators.
   - Determine `risk_score` from available compliance data.

2. Populate flag lists (sorted ascending by business_id):
   - **`bank_mismatch_ids`**: business IDs where `bank_account_status` is `"name_mismatch"`.
   - **`invalid_tax_ids`**: business IDs where `tax_id_status` indicates an invalid or unverified tax ID.
   - **`expired_license_ids`**: business IDs where `license_expiry_date` is before the `as_of_date` (review date).
   - **`review_queue_ids`**: business IDs that require compliance/AP review before release — any ID that is not a clean `"release"`.
   - **`risk_score_override_flags`**: business IDs with `risk_score >= 70`.

3. Determine `decisions` per business:
   - `"release"` — no blocking flags, all compliance evidence clean, risk score acceptable.
   - `"hold"` — non-critical issues present (e.g., missing documents, pending screening, moderate risk) that block immediate release but can be resolved.
   - `"escalate"` — critical flags present (e.g., bank mismatch, expired license, PEP, sanctions, high risk score) requiring manual intervention.

### Output Fields

- `task_id` — task identifier string.
- `batch_id` — batch identifier string.
- `as_of_date` — review date in `YYYY-MM-DD` format.
- `target_business_ids` — sorted ascending list of all business IDs in scope.
- `decisions` — object mapping each business_id to `"release"`, `"hold"`, or `"escalate"`.
- `bank_mismatch_ids` — sorted ascending.
- `invalid_tax_ids` — sorted ascending.
- `expired_license_ids` — sorted ascending.
- `review_queue_ids` — sorted ascending.
- `risk_score_override_flags` — sorted ascending.

## General Conventions

### Currency and Numeric Precision

- All monetary amounts are in **USD**.
- Report amounts to **2 decimal places** (e.g., `1842.36`).
- Use integer values for counts (e.g., `reviewed_claim_count`, UBO counts).
- When computing amortization, carry full precision through intermediate calculations and round only the final values to 2 decimals.
- Floor ending balances at `0.00` (never report negative).

### Sorting

- **Claim ID lists**: ascending alphabetical order (e.g., `CLM-2025-0037` before `CLM-2025-0080` before `CLM-2025-FIN-042` before `CLM-2025-OPS-017`).
- **Business ID lists**: ascending alphabetical order.
- **Hard stop flag lists**: alphabetical by flag enum value.
- **Invoice ID lists**: unless the template specifies scope-payload order, sort ascending.
- **Invoice results**: preserve the order from the scope payload when specified.

### API Error Handling

- If a detail endpoint returns 404, the entity does not exist — treat accordingly (e.g., no bill found for a claim).
- If a collection endpoint returns an empty list, no records match the query.
- Retry with the `/api/` prefix if the bare path returns an unexpected error.
- Use `limit` and `offset` to paginate large collections; default page size is typically returned by the API.

### Decision-Making Principles

- **Evidence from API is authoritative**: always prefer current API data over local payload snapshots. Local payloads are context, not system of record.
- **Preserve the distinction** between reimbursement case issues (claim-level problems like unapproved claims, missing receipts) and AP/payment evidence issues (bill mismatches, payment status discrepancies).
- **Be conservative on release decisions**: when in doubt between `hold` and `release`, prefer `hold`. When in doubt between `escalate` and `hold`, prefer `escalate`.
- **Cross-reference entities**: a claim's status must be consistent with its bills' statuses and the payments' statuses. Inconsistency is itself a blocking signal.
