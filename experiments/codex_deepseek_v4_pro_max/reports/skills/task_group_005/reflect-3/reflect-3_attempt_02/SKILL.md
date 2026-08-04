 # Finance ERP Close & Compliance Review Skill

 ## Overview
 This skill provides reusable patterns for interacting with a shared finance ERP API to perform close reviews, vendor onboarding checks, prepaid amortization reconciliation, stale AP snapshot correction, and account-change payment release reviews. The environment exposes RESTful GET endpoints for claims, AP bills, payments, vendors, compliance objects, prepaid invoices, GL balances, and close logs.

 ## API Interaction Rules

 - Use the API base URL supplied by the runner as `<TASK_ENV_BASE_URL>` (typically `http://task-env:9005/`).
 - All GET endpoints support exact-match query parameters by field name where the field exists, plus optional `limit` and `offset` integers.
 - Detail endpoints use path placeholders (e.g., `/api/claims/{claim_id}`); replace the placeholder with the identifier string.
 - Always query the live API rather than relying on local snapshots or cached data files. Local payloads (CSV, JSON) are context only — the API is the system of record.
 - Return all currency amounts in USD to two decimal places.
 - Sort all ID lists in ascending alphanumeric order.

 ## Claims-to-AP Reconciliation

 When reconciling expense claims against AP bills and payments:

 1. **Query all three endpoints**: claims (`/api/claims`), AP bills (`/api/ap/bills`), and payments (`/api/ap/payments`).
 2. **Match claims to bills** via the `claim_id` field on bills.
 3. **Match bills to payments** via the `bill_id` field on payments.
 4. **Classification logic**:
    - **Settled (paid)**: A claim is settled when its status is `"paid"` AND there is a cleared payment whose amount matches the claim amount, even if the payment routes through a different bill than the one linked to the claim (check claim `notes` for cross-reference hints like "Payment matched to bill AP-XXXXXX").
    - **Payable**: A claim is payable when its status is `"approved"` AND it has a linked AP bill with a non-void, non-problematic status. Claims without any bill at all are not payable — they need bill creation first.
    - **Blocked**: A claim is blocked when it has receipt or policy issues that prevent AP release, OR when its linked bill is void, missing, or has a severe amount mismatch.
 5. **AP open balance**: Sum the bill amounts for all payable claims. Use bill amounts straight from the API (not claim amounts). Exclude void bills.
 6. **Batch status**:
    - `"blocked"` when any batch claim is blocked.
    - `"open_payables"` when no claims are blocked and valid unpaid AP reimbursement bills remain.
    - `"ready_to_close"` when no claims are blocked and no unpaid bills remain.
 7. **CRM vs AP distinction**: Separately identify blocked claims that need expense-case owner cleanup (receipt issues, policy-flag violations) versus those that only have AP-link problems (void bills, missing bills).

 ## Stale AP Snapshot Correction

 When a local AP snapshot is provided as context but the live API is the system of record:

 1. For each claim in the batch, compare the snapshot row against the current API state.
 2. **Correction categories**:
    - `"current_snapshot_ok"`: Snapshot matches current ERP state.
    - `"mark_in_flight_payment"`: A payment exists in the current API that is processing (not yet cleared); the snapshot showed no payment.
    - `"replace_with_matched_paid_bill"`: The snapshot references the wrong bill; the claim is actually settled through a different bill with a cleared payment matching the claim amount.
    - `"exclude_amount_or_vendor_mismatch"`: The bill amount or vendor in the snapshot does not match the current claim or API records.
    - `"ignore_void_bill"`: The snapshot bill is now void in the current API.
    - `"block_unapproved_claim"`: The snapshot treated the claim as approved, but the current API shows it is not yet approved.
 3. **AP balance per claim**: Open balance = bill amount minus cleared payments only (ignore processing/scheduled payments). If the bill is void or the claim is already paid, balance is 0.
 4. **Close log review**: Check `/api/close/logs` for any logs in AP or Expense areas with status `"blocked"`, `"open"`, or `"ready_for_review"` that are relevant to the batch. If none are blocking, `close_log_required` may be `false`.

 ## Vendor Onboarding Compliance Review

 For vendor/business onboarding release decisions:

 1. **Query compliance endpoints**: `/api/compliance/objects` (bulk), plus detail endpoints for ownership, registry, screening, and bank per business ID.
 2. **Query vendor endpoint** (`/api/vendors`) to cross-check vendor status, tax ID, and bank account last-4 digits.
 3. **Decision framework**:
    - `"approve"`: No hard-stop issues; all checks pass.
    - `"awaiting_information"`: Review is in progress or minor issues need clarification.
    - `"escalate"`: Multiple hard-stop flags or serious compliance concerns (confirmed PEP, sanctions match, shell company suspected, vendor on hold, bank closed).
 4. **Hard-stop flags** (apply alphabetically when multiple):
    - `"bank_closed"`: Bank account status is `"closed"`.
    - `"bank_name_mismatch"`: Bank account status is `"name_mismatch"`.
    - `"confirmed_pep"`: PEP status is `"confirmed_pep"`.
    - `"expired_license"`: License expiry date is before the review date.
    - `"missing_required_documents"`: `missing_fields` is non-empty on the compliance object.
    - `"sanctions_confirmed"`: Sanctions check status is `"confirmed_match"`.
    - `"screening_not_run"`: Sanctions check status or PEP status is `"not_run"`.
    - `"shell_company_suspected"`: `shell_company_suspected` is `true`.
    - `"vendor_on_hold"`: Vendor status is `"on_hold"`.
 5. **Reportable UBO counts**: Count unique beneficial-owner **names** (not entries) whose ownership percentage is at or above 25%. When the same name appears in multiple UBO entries, count the name only once.
 6. **Follow-up list**: All business IDs that are not approved.
 7. **Overall release ready**: `true` only if every listed business can be released (all decisions are `"approve"`).

 ## Account-Change Payment Release Review

 When reviewing a payment release batch after vendor account-change events:

 1. Query compliance endpoints and vendor endpoint for every target business ID.
 2. **Decisions** (`"release"`, `"hold"`, `"escalate"`):
    - `"release"`: No hard-stop flags, review is complete or minor, risk below override threshold.
    - `"hold"`: Some issues exist but are resolvable (e.g., bank name mismatch with approved review, review still in progress without other flags).
    - `"escalate"`: Multiple flags, serious compliance concerns, vendor on hold, bank closed, or confirmed PEP/sanctions issues.
 3. **Flag lists**:
    - `bank_mismatch_ids`: Business IDs whose compliance `bank_account_status` is exactly `"name_mismatch"` (not `"closed"` or `"verified"`).
    - `invalid_tax_ids`: Business IDs where the compliance registry `tax_id` does not match the vendor record `tax_id`.
    - `expired_license_ids`: Business IDs whose `license_expiry` is strictly before the `as_of_date`.
    - `review_queue_ids`: Business IDs whose compliance `review_status` is not `"approved"`.
    - `risk_score_override_flags`: Business IDs with `risk_score >= 70`.

 ## Prepaid Expense Amortization Reconciliation

 For prepaid close checks using straight-line amortization:

 1. Query `/api/prepaids/invoices` and `/api/prepaids/gl-balances`.
 2. Filter invoices to the selected IDs from the scope file.
 3. Filter GL balances to the target accounts, entity, and close period.
 4. **Invoice-level computation** (using full-month amortization — do NOT prorate partial months):
    - `march_amortization` = the invoice's `monthly_amortization` value (full month, regardless of mid-month start dates).
    - `cumulative_amortization_through_march` = `monthly_amortization × number_of_full_months_from_service_start_through_march`.
    - `ending_balance` = `original_amount − cumulative_amortization_through_march`.
 5. **Data quality flags**:
    - `default_missing_term_flag`: `true` when `data_quality_flags` includes `"missing_contract_dates"`.
    - `exception_flag`: `true` when `data_quality_flags` is non-empty (any flag at all).
 6. **Account rollup**: For each account, sum the selected invoices' metrics (`original_amount`, `march_amortization`, `cumulative`, `ending_balance`).
 7. **Variance**: `schedule_ending_balance − gl_ending_balance`. Flag as `true` when absolute variance exceeds the configured threshold.
 8. **Account status**:
    - `"reconciled"`: Variance within threshold, no data quality issues.
    - `"variance_review"`: Variance exceeds threshold but may be explainable.
    - `"requires_reconciliation"`: Variance exceeds threshold AND/OR there are data quality issues requiring manual reconciliation.
 9. **Exception and missing-term lists**: Collect invoice IDs with `exception_flag=true` and `default_missing_term_flag=true`, sorted ascending.

 ## Cross-Cutting Conventions

 - Always compute amounts from live API data; never hard-code values from training examples.
 - When the answer template specifies allowed values for a field, use only those exact values.
 - When the answer template specifies sort order, apply it exactly.
 - When a template provides a `required_value` for a field (like `task_id` or `batch_id`), use that exact value.
 - For fields with `additional_properties_allowed: false`, do not include any extra keys.
 - Always check for data consistency across endpoints (e.g., vendor tax ID vs compliance registry tax ID).
