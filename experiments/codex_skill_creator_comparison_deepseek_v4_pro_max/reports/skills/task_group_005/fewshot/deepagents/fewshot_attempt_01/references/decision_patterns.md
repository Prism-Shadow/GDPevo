# Decision Pattern Reference

This document catalogs the decision frameworks used across ERP finance review tasks. Each framework specifies how to classify entities based on evidence gathered from the API.

## Claim Close Framework

Reviews a batch of claim IDs against current claims, bills, and payments to produce a close disposition.

### Classification

For each claim ID in the batch:

1. Fetch the claim from `/api/claims/{claim_id}`. If the claim does not exist or is not `approved`, the claim is **blocked**.
2. Fetch bills for the claim. Look for a bill matching the claim amount with status `approved`, `paid`, or `scheduled`. If no such bill exists, the claim is **blocked** (CRM required — expense case or AP-link issue).
3. For the matched bill:
   - If the bill is `paid` and has a `cleared` payment matching the bill amount: the claim is **paid**.
   - If the bill is `scheduled` or `approved` with no cleared payment: the claim is **payable**.
   - If the bill is `void`: the claim is **blocked**.
   - If payment evidence is inconsistent (e.g., partial payment, mismatched amounts): the claim is **blocked**.

### Output Fields

- `payable_claim_ids`: claims with valid unpaid AP bills (sorted ascending).
- `blocked_claim_ids`: claims that should not be released (sorted ascending).
- `paid_claim_ids`: claims with matching paid bill and cleared payment (sorted ascending).
- `ap_open_balance_total`: sum of open AP bill amounts for payable claims only.
- `crm_required_claim_ids`: blocked claims requiring expense-case owner cleanup.
- `batch_status`: `blocked` if any claim is blocked; `open_payables` if payable claims exist and none are blocked; otherwise `ready_to_close`.
- `reviewed_claim_count`: total count of claims in the batch.

### CRM vs. AP Issue Distinction

- **CRM required** (expense case issue): claim not approved, claim has no matching approved bill, bill amount mismatches, bill is void, or partial receipt support under review.
- **AP evidence issue**: payment not yet cleared but bill is valid (these are `payable`, not blocked).

## Vendor Release Framework

Reviews a batch of business IDs for onboarding or account-change release approval.

### Classification

For each `business_id`:

1. Fetch vendor record and compliance records (ownership, registry, screening, bank).
2. Check for hard-stop conditions (any one of these → `escalate`):
   - `sanctions_confirmed` or `confirmed_pep` in screening
   - `expired_license` in registry (license expiry before review date)
   - `bank_closed` or `bank_name_mismatch` in bank verification
   - `vendor_on_hold` in vendor status
   - `shell_company_suspected` in compliance
   - `screening_not_run` (missing or stale screening)
   - `missing_required_documents` in registry
3. If no hard-stop flags but minor issues exist (e.g., missing documents that can be requested): `awaiting_information`.
4. If all checks pass with no flags: `approve`.

### UBO Counts

Count unique beneficial owner names from `/api/compliance/ownership/{business_id}` where `ownership_percentage` is at or above the reporting threshold (typically 25%).

### Hard-Stop Flags

Collect all applicable hard-stop flags per business. Sort flags alphabetically. Use an empty list `[]` when none apply.

### Output Fields

- `per_business`: list of `{business_id, decision}` objects, sorted ascending by business_id.
- `reportable_ubo_counts`: object mapping each business_id to its UBO count.
- `hard_stop_flags`: object mapping each business_id to its flag list.
- `follow_up_business_ids`: all business_ids not marked `approve`, sorted ascending.
- `overall_release_ready`: `true` only if every business is `approve`.

## Account Change Release Framework

A variant of the release framework focused on payment release after account-change events.

### Additional Checks

Beyond standard release review, verify:

- **Bank match**: Compare the bank last4 from the account-change ticket to the compliance bank record. Mismatch → `bank_mismatch_ids`.
- **Tax ID validity**: Check `tax_id_status` in registry. Invalid → `invalid_tax_ids`.
- **License expiry**: Compare `license_expiry` against `as_of_date`. Expired → `expired_license_ids`.
- **Risk score**: If any endpoint returns a risk score >= 70, add to `risk_score_override_flags`.

### Classification

- **release**: All checks pass, no flags.
- **hold**: Non-critical issues (bank mismatch, missing screening) without hard stops.
- **escalate**: Hard-stop conditions (sanctions, PEP, expired license, closed bank).

## Prepaid Reconciliation Framework

Reconciles prepaid invoice schedules against GL balances for a given close period.

### Per-Invoice Computation

For each prepaid invoice in the scope:

1. Retrieve the invoice record from `/api/prepaids/invoices`.
2. Identify the `monthly_amortization` for the target period. If the API provides per-period breakdowns, use the target period amount. Otherwise, use straight-line computation: `monthly = original_amount / term_months`.
3. `cumulative_amortization_through_period` is the sum of all monthly amortization from start through the target period.
4. `ending_balance = original_amount - cumulative_amortization_through_period`.
5. Set `default_missing_term_flag` from the invoice record.
6. Set `exception_flag` if any of: missing amortization term, ending balance zero with remaining schedule, ending balance negative, amortization not matching expected straight-line pattern.

### Account Rollup

For each account in scope:

- Sum `original_amount`, `march_amortization` (the target period amortization), `cumulative_amortization_through_period` across invoices in that account.
- `schedule_ending_balance = original_amount_total - cumulative_amortization_total`.
- Retrieve `gl_ending_balance` from `/gl/balances` for the account and period.
- `variance_amount = schedule_ending_balance - gl_ending_balance`.
- `variance_flag`: `true` if `|variance_amount| > variance_threshold_abs`.
- `account_status`: `reconciled` if no variance flag, no default/missing terms, and no exceptions. `variance_review` if variance within threshold but other flags present. `requires_reconciliation` if variance exceeds threshold or multiple issues present.

### Output Fields

- `invoice_results`: list of per-invoice objects in scope order.
- `account_rollup`: per-account totals and flags.
- `default_missing_term_invoice_ids`: invoices with missing terms, sorted ascending.
- `exception_invoice_ids`: invoices flagged for exceptions, sorted ascending.
