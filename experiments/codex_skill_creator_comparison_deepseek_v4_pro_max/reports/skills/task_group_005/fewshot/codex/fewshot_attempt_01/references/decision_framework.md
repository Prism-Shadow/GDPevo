# Decision Framework

This reference defines reusable decision logic for every task type in the finance-close-operations domain. Load the relevant section during Phase 3 of the core workflow. Do not guess classification rules from answer examples alone; apply the logic described here against live API evidence.

## Table of Contents

- [Claim/AP Reconciliation](#claimap-reconciliation)
- [Vendor Compliance Review](#vendor-compliance-review)
- [Prepaid Close](#prepaid-close)
- [Payment Release Risk Review](#payment-release-risk-review)

---

## Claim/AP Reconciliation

Used for tasks that classify claims into paid, payable (ready for AP), and blocked (needs owner cleanup) categories. Also covers stale snapshot corrections.

### Data sources

| Source | Purpose |
|--------|---------|
| GET /api/claims/{claim_id} | Claim status and amount |
| GET /api/ap/bills | Match bills to claims |
| GET /api/ap/payments | Match payments to bills and claims |
| GET /api/close/logs | Check for open close-period issues |

### Classification logic

For each claim ID in the batch:

1. Fetch the claim. A claim with status `approved` can proceed. A claim with any other status (`draft`, `pending`, `rejected`, `void`) is blocked.

2. Find the matching AP bill. Match on `bill.claim_id == claim_id` or on matching vendor/amount where no direct link exists. A void bill means the claim is blocked. A bill with `status == "paid"` and a matching cleared payment means the claim can be classified as paid. A bill with `status == "scheduled"` or `"approved"` and no cleared payment means the claim is payable if the claim is approved and the amounts align.

3. Check for cleared payments. A cleared payment linked to the bill settles the obligation. If a payment exists but is not cleared (e.g., `"scheduled"`), treat the bill as still open.

4. Amount and vendor alignment. When a claim amount does not match the bill amount within reasonable tolerance, or the vendor on the bill differs from the claim's vendor, flag the item as blocked with a vendor/amount mismatch reason.

### Classification categories

| Category | Conditions |
|----------|------------|
| payable | Claim approved, bill exists and is scheduled or approved (not void, not paid), no cleared payment, amounts aligned |
| paid | Claim approved, bill paid, a cleared payment exists for the claim amount |
| blocked | Claim not approved, OR bill void, OR vendor/amount mismatch, OR payment issues, OR missing bill |

### CRM (case-management) requirement

A blocked claim requires CRM/owner cleanup when the blocking issue is on the expense-case side:
- Claim status is not approved: owner must approve or correct
- Claim-bill link is broken (no bill found, wrong vendor): requires AP-link remediation
- Bill is void and needs reissue

### Open AP balance

For payable claims, the open AP balance is the bill amount minus any cleared payments. For paid claims, it is 0.00. For blocked claims without a valid bill, record 0.00 (the obligation cannot be quantified from available records).

### Stale snapshot corrections

When a task provides a stale AP snapshot CSV, classify each claim against current API state:

| Correction | Trigger |
|------------|---------|
| current_snapshot_ok | Current state matches snapshot |
| mark_in_flight_payment | Bill scheduled/approved, payment scheduled but not yet cleared |
| replace_with_matched_paid_bill | Bill and payment are now cleared; snapshot shows stale status |
| exclude_amount_or_vendor_mismatch | Claim amount does not match bill amount, or vendor differs |
| ignore_void_bill | Bill is void in current API |
| block_unapproved_claim | Claim is not approved in current API |

### Batch status derivation

| Batch status | Conditions |
|-------------|------------|
| blocked | Any claim is blocked |
| open_payables | At least one claim is payable and none are blocked |
| ready_to_close | All claims are paid or payable with no blockers |

### Close log requirement

When a close period has an open or pending_review close log referencing any batch claim, set close_log_required.required = true and list the relevant close log IDs.

---

## Vendor Compliance Review

Used for vendor onboarding release decisions and hard-stop flag enumeration.

### Data sources

| Source | Purpose |
|--------|---------|
| GET /api/vendors | Vendor status and risk score |
| GET /api/compliance/ownership/{business_id} | Beneficial owner records |
| GET /api/compliance/registry/{business_id} | Registration, license, tax ID |
| GET /api/compliance/screening/{business_id} | Watchlist and adverse media |
| GET /api/compliance/bank/{business_id} | Bank account verification |

### Per-business decision logic

For each business ID, evaluate all compliance dimensions and assign one of three decisions:

| Decision | Rule |
|----------|------|
| approve | No hard-stop flags present. All compliance evidence is clean: vendor active, bank verified, license active, screening clear, tax ID valid, no ownership red flags, risk score below 70. |
| awaiting_information | Some evidence is missing or pending (e.g., screening not run, documents missing) but no confirmed violations (no PEP, no sanctions, no expired license, no closed bank, no on-hold). These are informational gaps, not confirmed risks. |
| escalate | At least one confirmed violation: PEP confirmed, sanctions hit, expired license, closed bank, bank name mismatch, vendor on hold, shell company suspected, or any combination that makes the business unfit for release without investigation. |

### UBO (Ultimate Beneficial Owner) counting

Count distinct owner names from the ownership endpoint whose ownership_percentage >= 25. Count unique names only. If no owners meet the threshold, the count is 0.

### Hard-stop flags

Derive flags from compliance evidence. Always list flags alphabetically. Use an empty list when none apply.

| Flag | Source endpoint | Trigger condition |
|------|----------------|-------------------|
| bank_closed | bank | bank_account_status == "closed" |
| bank_name_mismatch | bank | bank_account_status == "name_mismatch" |
| confirmed_pep | screening | pep_flag == true |
| expired_license | registry | license_status == "expired" or license_expiry_date < as_of_date |
| missing_required_documents | registry | Required registration fields absent or incomplete |
| sanctions_confirmed | screening | sanctions_flag == true |
| screening_not_run | screening | screening_status == "not_run" |
| shell_company_suspected | screening | shell_company_risk == "suspected" |
| vendor_on_hold | vendor | vendor.status == "on_hold" |

### Follow-up list

All business IDs not classified as approve belong in the follow-up list, sorted ascending.

### Overall release readiness

overall_release_ready is true only when every business in the batch is approve. Otherwise it is false.

---

## Prepaid Close

Used for reconciling prepaid invoice amortization schedules against GL balances for a close period.

### Data sources

| Source | Purpose |
|--------|---------|
| GET /api/prepaids/invoices | Invoice schedules, original amounts, term data |
| GET /api/prepaids/gl-balances | GL period-end balances per account |

### Scope filtering

Only invoice IDs listed in the close scope payload are in scope. Only the accounts specified in the scope are reconciled. The close period determines which GL balances and amortization entries are relevant.

### Invoice-level calculations

For each scoped invoice, compute:

- march_amortization (or close-period amortization): The monthly amortization amount for the close-period month. Read from the invoice record's monthly_amortization field or from the schedule entry for the close-month period.
- cumulative_amortization_through_march: Total amortization recognized through the close month. Read from cumulative_amortization or sum schedule entries through the close month.
- ending_balance: original_amount - cumulative_amortization_through_march. Must be >= 0. A negative ending balance is an exception.

### Default/missing term detection

A prepaid invoice has a default or missing term when:
- term_months is 0, 1, or absent from the record
- The amortization schedule is inconsistent with straight-line (e.g., monthly amount * term_months != original_amount)
- The schedule shows a single lump amortization suggesting no formal term

Flag these invoices in default_missing_term_invoice_ids.

### Exception detection

An invoice is an exception when any of these hold:
- ending_balance is non-zero but less than 1.00 USD (e.g., 0.01 -- a rounding residual)
- cumulative_amortization > original_amount (over-amortized)
- The schedule is incomplete (fewer months amortized than expected for the term)
- The invoice has structural anomalies (missing start date, inconsistent amounts)

Flag these in exception_invoice_ids.

### Account rollup

For each account, aggregate across its scoped invoices:

- selected_invoice_count: Count of scoped invoices in this account
- original_amount_total: Sum of original_amount
- march_amortization_total: Sum of close-month amortization
- cumulative_amortization_through_march: Sum of cumulative amortization
- schedule_ending_balance: original_amount_total - cumulative_amortization_through_march
- gl_ending_balance: Read from the GL balance record for this account and period
- variance_amount: schedule_ending_balance - gl_ending_balance
- variance_flag: true when abs(variance_amount) > variance_threshold_abs (use > not >=). Default threshold is 0.01 if unspecified.
- has_default_missing_term_flag: true when any scoped invoice in this account has a default or missing term
- account_status:
  - reconciled: variance_flag == false and no exceptions and no default/missing terms
  - variance_review: variance_flag == true but no data-quality exceptions
  - requires_reconciliation: Any exception or default/missing term, regardless of variance

---

## Payment Release Risk Review

Used for assessing whether vendor payments can be released after account-change events.

### Data sources

| Source | Purpose |
|--------|---------|
| GET /api/vendors | Vendor status, risk score, bank last4 |
| GET /api/compliance/ownership/{business_id} | Ownership verification |
| GET /api/compliance/registry/{business_id} | License, tax ID validation |
| GET /api/compliance/screening/{business_id} | PEP, sanctions, shell company |
| GET /api/compliance/bank/{business_id} | Bank account verification |

### Per-business decision logic

For each business ID in the batch, cross-reference the compliance evidence against the account-change context:

| Decision | Rule |
|----------|------|
| release | All checks pass: vendor active, bank verified (no mismatch, not closed), license active (not expired), tax ID valid, screening clear (no PEP, no sanctions), shell company risk none or low, risk score < 70. The account change is consistent with current compliance evidence. |
| hold | Issues that require review before release but are not confirmed violations: bank name mismatch, risk score >= 70, pending screening or documents, but no PEP, sanctions, expired license, closed bank, or on-hold. These block release temporarily pending investigation. |
| escalate | Confirmed violations: PEP confirmed, sanctions hit, expired license, closed bank, vendor on hold, shell company suspected, or invalid tax ID. These require escalation beyond the normal release review process. |

### Derived flag lists

| List | Derivation |
|------|-----------|
| bank_mismatch_ids | Business IDs where bank_account_status == "name_mismatch" |
| invalid_tax_ids | Business IDs where tax_id_status == "invalid" |
| expired_license_ids | Business IDs where license_expiry_date < as_of_date |
| review_queue_ids | All business IDs not classified as release |
| risk_score_override_flags | Business IDs where vendor risk_score >= 70 |

All lists sorted ascending by business_id.

### Decision tiebreaking

When multiple conditions apply, the most severe governs: escalate > hold > release.

An expired license with a bank mismatch is escalate, not hold. A PEP flag with a clean bank is escalate. An invalid tax ID alone is escalate (it is a confirmed non-compliance).

### Account-change cross-reference

When a batch includes account-change tickets with requested_bank_last4, cross-reference against the vendor's bank_last4 from the API:
- If the requested bank last4 matches the vendor's current bank last4, the change is consistent
- If they differ, this does not itself trigger escalate unless the bank compliance endpoint also shows name_mismatch or closed
- A change_type of reactivation_after_closed_bank_notice combined with a currently closed bank is escalate
- A change_type of new_account_after_remittance_failure combined with bank name mismatch is hold
