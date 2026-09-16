# ERP API Reference

## Base URL

The runner supplies the API base URL as `<TASK_ENV_BASE_URL>`. Substitute it in every `curl` call.

## Common patterns

- All list responses wrap results in `{"count": N, "data": [...], "endpoint": "...", "limit": N, "offset": N, "total": N}`.
- Filtering uses exact-match query parameters named after the field. Repeat a parameter for multiple values.
- Pagination: `?limit=N&offset=N`.

## Claims (`/api/claims`)

Filter: `claim_id` (repeatable)

Response fields per claim:

| Field | Type | Description |
|---|---|---|
| `claim_id` | string | Unique claim identifier |
| `amount` | number | Claim amount in USD |
| `status` | string | `submitted`, `needs_receipt`, `approved`, `rejected`, `paid` |
| `approved_date` | string or null | ISO date when approved |
| `submitted_date` | string | ISO date when submitted |
| `category` | string | Expense category (Travel, Software, Meals, etc.) |
| `department` | string | Department name |
| `employee_name` | string | Claimant name |
| `currency` | string | Always `USD` |
| `receipt_status` | string | `attached`, `partial`, `missing` |
| `policy_flags` | list[string] | `late_receipt`, `over_limit`, `manual_rate`, `duplicate_amount`, `weekend_spend` |
| `notes` | string | Internal notes |
| `vendor_id` | string or null | Linked vendor |

## AP Bills (`/api/ap/bills`)

Filter: `claim_id`, `bill_id`

| Field | Type | Description |
|---|---|---|
| `bill_id` | string | Unique bill identifier |
| `claim_id` | string or null | Linked claim ID |
| `amount` | number | Bill amount in USD |
| `status` | string | `scheduled`, `approved`, `paid`, `void` |
| `bill_date` | string | ISO date |
| `due_date` | string | ISO date |
| `invoice_number` | string | Invoice reference |
| `account` | string | GL account code |
| `currency` | string | Always `USD` |
| `memo` | string | Internal memo |
| `vendor_id` | string | Linked vendor |

## AP Payments (`/api/ap/payments`)

Filter: `bill_id`, `vendor_id`

| Field | Type | Description |
|---|---|---|
| `payment_id` | string | Unique payment identifier |
| `bill_id` | string | Bill being paid |
| `amount` | number | Payment amount in USD |
| `status` | string | `scheduled`, `processing`, `cleared` |
| `payment_date` | string | ISO date |
| `method` | string | `ACH`, `Check`, `Wire`, `Virtual card` |
| `bank_reference` | string | Bank reference number |
| `vendor_id` | string | Linked vendor |

## Vendors (`/api/vendors`)

Filter: `vendor_id`

| Field | Type | Description |
|---|---|---|
| `vendor_id` | string | Unique vendor identifier |
| `vendor_name` | string | Short display name |
| `legal_name` | string | Legal entity name |
| `status` | string | `active`, `inactive`, `on_hold` |
| `industry` | string | Payroll, Travel, Legal, etc. |
| `bank_account_last4` | string | Last 4 digits of bank account |
| `default_account` | string | Default GL account |
| `payment_terms` | string | Net 30, Net 45, Due on receipt |
| `tax_id` | string | Tax identifier |
| `updated_at` | string | ISO date of last update |

## Compliance Objects (`/api/compliance/objects`)

Filter: `business_id` (repeatable)

Returns the merged compliance view for each business.

| Field | Type | Description |
|---|---|---|
| `business_id` | string | Unique business identifier |
| `business_name` | string | Business display name |
| `vendor_id` | string | Linked vendor |
| `jurisdiction` | string | Registration jurisdiction |
| `registration_number` | string | Company registration number |
| `tax_id` | string | Tax identifier (format: `TIN` + digits, or `TIN` + alphanumeric) |
| `license_expiry` | string | ISO date of license expiry |
| `bank_account_status` | string | `verified`, `name_mismatch`, `closed` |
| `pep_status` | string | `none`, `possible_pep`, `confirmed_pep`, `not_run` |
| `sanctions_check_status` | string | `clear`, `possible_match`, `confirmed_match`, `not_run` |
| `shell_company_suspected` | boolean | Shell company flag |
| `ownership_layer_count` | integer | Number of ownership layers |
| `ubo_list` | list[object] | Beneficial owners, each with `name` (string) and `ownership_pct` (number) |
| `missing_fields` | list[string] | Required fields not yet provided |
| `review_status` | string | `not_started`, `in_review`, `awaiting_information`, `approved`, `escalated` |
| `risk_score` | integer | 0-100 risk score |

### Reporting UBO count

Count unique UBO **names** (not records) where `ownership_pct >= 25`. Duplicate names at different percentages count once.

### Hard-stop flags derivation

Derive from compliance object fields as follows:

| Flag | Condition |
|---|---|
| `bank_closed` | `bank_account_status == "closed"` |
| `bank_name_mismatch` | `bank_account_status == "name_mismatch"` |
| `confirmed_pep` | `pep_status == "confirmed_pep"` |
| `expired_license` | `license_expiry` date is before the review date (strictly less than) |
| `missing_required_documents` | `missing_fields` is non-empty |
| `sanctions_confirmed` | `sanctions_check_status == "confirmed_match"` |
| `screening_not_run` | `pep_status == "not_run"` OR `sanctions_check_status == "not_run"` |
| `shell_company_suspected` | `shell_company_suspected == true` |
| `vendor_on_hold` | Check vendor record; `vendor.status == "on_hold"` |

Sort flags alphabetically. Use an empty list when none apply.

### Decision logic for onboarding

| Decision | Condition |
|---|---|
| `escalate` | `pep_status == "confirmed_pep"`, OR `sanctions_check_status == "confirmed_match"`, OR `shell_company_suspected == true`, OR (`pep_status == "possible_pep"` AND `bank_account_status` is `name_mismatch` or `closed`) |
| `awaiting_information` | `missing_fields` is non-empty, OR `pep_status == "not_run"`, OR `sanctions_check_status == "not_run"` or `possible_match`, OR `license_expiry` is expired, OR `bank_account_status` is `name_mismatch` or `closed` |
| `approve` | None of the above conditions met |

### Decision logic for account-change payment release

| Decision | Condition |
|---|---|
| `escalate` | `pep_status == "confirmed_pep"`, OR `sanctions_check_status == "confirmed_match"`, OR `shell_company_suspected == true`, OR `vendor.status == "on_hold"`, OR (`pep_status == "possible_pep"` AND `bank_account_status` is `name_mismatch` or `closed`) |
| `hold` | `missing_fields` non-empty, OR `pep_status == "not_run"` or `possible_pep`, OR `sanctions_check_status == "not_run"` or `possible_match`, OR `license_expiry` expired before review date, OR `bank_account_status` is `name_mismatch` or `closed`, OR `risk_score >= 70`, OR `tax_id` does not match regex `^TIN\d{6}$` or where all digits are identical placeholder (e.g., `TIN999999`) |
| `release` | None of the above conditions met |

### Deriving per-business lists for account-change release

- **`bank_mismatch_ids`**: business IDs where `bank_account_status == "name_mismatch"`
- **`invalid_tax_ids`**: business IDs where `tax_id` does not match regex `^TIN\d{6}$` or where all digits are identical placeholder (e.g., `TIN999999`)
- **`expired_license_ids`**: business IDs where `license_expiry` is strictly before `as_of_date`
- **`review_queue_ids`**: business IDs that need review: any with `escalate` or `hold` decision, or any flag present
- **`risk_score_override_flags`**: business IDs where `risk_score >= 70`

### Compliance sub-endpoints

- `/api/compliance/ownership/{business_id}` — Returns `business_id`, `ownership_layer_count`, `shell_company_suspected`, `ubo_list`
- `/api/compliance/registry/{business_id}` — Returns `business_id`, `jurisdiction`, `license_expiry`, `registration_number`, `tax_id`
- `/api/compliance/screening/{business_id}` — Returns `business_id`, `pep_status`, `sanctions_check_status`
- `/api/compliance/bank/{business_id}` — Returns `business_id`, `bank_account_status`

## Prepaid Invoices (`/api/prepaids/invoices`)

Filter: `prepaid_invoice_id` (repeatable), `account`

| Field | Type | Description |
|---|---|---|
| `prepaid_invoice_id` | string | Unique identifier |
| `account` | string | GL account code (e.g., `1250`, `1251`) |
| `description` | string | Invoice description |
| `invoice_date` | string | ISO date |
| `invoice_number` | string | Invoice reference |
| `original_amount` | number | Total invoice amount in USD |
| `monthly_amortization` | number | Straight-line monthly amortization in USD |
| `recognition_method` | string | Always `straight_line` |
| `service_start` | string | ISO date of service start |
| `service_end` | string | ISO date of service end |
| `data_quality_flags` | list[string] | `rounded_amount`, `missing_contract_dates` |
| `source_document` | string | Source document type |
| `vendor_id` | string | Linked vendor |

### Amortization calculations (straight-line, monthly)

For a given close period (e.g., `2025-03` for March 2025):

- **March amortization**: `monthly_amortization` field from the invoice record.
- **Cumulative amortization through March**: `monthly_amortization * N` where N is the number of complete months from `service_start` through March.
  - A month is complete if the close-period month is at or after the service-start month.
  - Example: `service_start = 2025-01-01`, March 2025 close → N = 3 months (Jan, Feb, Mar).
  - Example: `service_start = 2025-03-01`, March 2025 close → N = 1 month (only March).
- **Ending balance**: `original_amount - cumulative_amortization_through_march`. Minimum 0.00 (do not allow negative net book value unless the data supports it).
- **Rounding**: All values to two decimals using standard rounding (round half to even or half-up, consistent within the task).

### Invoice-level flags

- **`default_missing_term_flag`**: `true` when `data_quality_flags` contains `missing_contract_dates`.
- **`exception_flag`**: `true` when `data_quality_flags` is non-empty (any flag present).

### Account-level flags

- **`has_default_missing_term_flag`**: `true` when any invoice in the account has `default_missing_term_flag == true`.
- **`variance_flag`**: `true` when `abs(schedule_ending_balance - gl_ending_balance) > variance_threshold_abs`.
- **`account_status`**: `reconciled` when variance within threshold; `variance_review` when variance exceeds threshold but under 5x threshold; `requires_reconciliation` when variance exceeds 5x threshold or any invoice-level exception exists.

## GL Balances (`/api/prepaids/gl-balances`)

Filter: `account`, `period` (format YYYY-MM)

| Field | Type | Description |
|---|---|---|
| `account` | string | GL account code |
| `account_name` | string | Account display name |
| `period` | string | Period in YYYY-MM format |
| `ending_balance` | number | GL ending balance in USD |
| `entity` | string | Entity name |
| `source` | string | Source system |
| `loaded_at` | string | ISO timestamp when loaded |

## Close Logs (`/api/close/logs`)

Filter: `claim_id`, `period`, `area`

| Field | Type | Description |
|---|---|---|
| `log_id` | string | Unique log identifier |
| `area` | string | Domain: `Expense`, `AP`, `Compliance`, `Treasury`, `Prepaids` |
| `period` | string | Period in YYYY-MM format |
| `status` | string | `ready_for_review`, `closed` |
| `message` | string | Log message |
| `owner` | string | Person assigned |
| `related_account` | string or null | GL account |
| `created_at` | string | ISO timestamp |
