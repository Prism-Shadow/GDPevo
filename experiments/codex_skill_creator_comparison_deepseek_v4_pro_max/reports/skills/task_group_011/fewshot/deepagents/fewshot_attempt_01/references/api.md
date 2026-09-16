# Credit Office API Reference

Base URL: supplied by the runner as `<TASK_ENV_BASE_URL>` (defaults to `http://task-env:9011`).

All endpoints are public GET; no authentication required.

## Endpoints

### Manifest
`GET /api/manifest`
Returns metadata about the data set including benchmark versions, policy version, and record counts.

### Policies
`GET /api/policies`
Returns the complete credit policy: risk rating rules, CDFI factor scoring, CRE weighted scoring, concentration limits, and stress formulas. This is the authoritative source for all classification and computation rules.

### Branches
`GET /api/branches`
Returns list of all branch objects. Each branch has: `branch_id`, `branch_name`, `institution_type` (`"bank"` or `"credit_union"`), `state_code`, `lending_capacity_q1`, `sector_ceiling_pct`, `cre_policy_limit_pct`, `total_assets`, `fdic_benchmark_set`.

### Branch Detail
`GET /api/branches/{branch_id}`
Returns a single branch object.

### Branch Metrics
`GET /api/branches/{branch_id}/metrics`
Returns list of quarterly metrics snapshots. Each has: `quarter`, `total_loans_outstanding`, `total_deposits`, `nonperforming_loans`, `delinquency_30_plus_pct`, `net_charge_offs`, `allowance_for_loan_losses`. Use the most recent quarter for current metrics.

### Branch Loans
`GET /api/branches/{branch_id}/loans`
Returns all loans for a branch. Each loan has: `loan_id`, `borrower_name`, `branch_id`, `sector`, `loan_type`, `current_rating` (1-8), `outstanding_balance`, `payment_status`, `days_past_due`, `dscr`, `ltv`, `collateral_value`, `fico`, `debt_to_asset`, `liquidity_months`, `guarantor_strength`, `interest_rate`, `annual_debt_service`, `annual_review_date`, `notes`. Fields may be null.

### Branch Sector Exposures
`GET /api/branches/{branch_id}/sector-exposures`
Returns sector-level exposure data. Each record: `sector`, `current_exposure`, `limit_pct`, `grandfathered` (0 or 1).

### Branch Applications
`GET /api/branches/{branch_id}/applications`
Returns pending applications. Each application has: `application_id`, `applicant_name`, `business_name`, `branch_id`, `sector`, `loan_type`, `requested_amount`, `dscr`, `ltv`, `collateral_value`, `fico`, `proposed_rate`, `term_months`, `purpose`, `documentation_complete` (0 or 1), `sba_guaranty_pct`, `years_in_business`, `bankruptcy_months_ago`, `prior_delinquencies_12m`, `total_assets`, `total_debt`, `annual_revenue`, `net_income`, `existing_relationship_years`, `relationship_deposit_balance`, `co_guarantor_strength`, `dti`, `notes`. Fields may be null.

### FDIC Benchmarks
`GET /api/benchmarks/fdic/q4-2024`
Returns the FDIC Q4 2024 national aggregate benchmark object.

### NCUA Benchmarks
`GET /api/benchmarks/ncua/q1-2025`
Returns the NCUA Q1 2025 state-level benchmark table.

### Credit Union Segments
`GET /api/credit-union-segments/{segment_id}`
Returns segment detail including: `segment_id`, `segment_name`, `state_code`, `member_profile`, `portfolio_focus`, `peer_states`, `quarterly_capacity`, `risk_tolerance`, `current_outstanding`, `minimum_checklist`, `internal_context`, `notes`.
