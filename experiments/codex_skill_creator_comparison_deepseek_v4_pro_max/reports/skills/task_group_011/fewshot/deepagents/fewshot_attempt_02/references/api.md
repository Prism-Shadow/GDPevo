# API Endpoint Reference

Base URL is always provided as `<TASK_ENV_BASE_URL>`. All endpoints return JSON. No authentication.

## /api/manifest

Response fields:
- `benchmark_versions`: { `fdic`, `ncua` } — active benchmark version strings
- `policy_version`: e.g. `credit_policy_v2025Q1`
- `generated_seed`: integer
- `record_counts`: counts of applications, branches, loans, etc.
- `public_api_endpoints`: list of available endpoints

## /api/policies

Response is a JSON object with keys:
- `risk_rating`: { `delinquency_minimums`, `dominant_factor_rule`, `dscr_thresholds`, `ltv_thresholds`, `material_downgrade_notches` }
- `cdfi_factor_scores`: { `classes`, `debt_to_asset`, `fico`, `liquidity_months`, `ltv` }
- `cre_weighted_score`: { `classes`, `weights` }
- `stress`: { `coverage_breach_threshold`, `cre_dual_stress_formula`, `watch_list_formula`, `watch_list_parallel_shock` }
- `capacity_concentration`: { `allowed_mitigations`, `branch_sector_override_table`, `grandfathering_note`, `lending_capacity_field`, `single_sector_default_field` }

## /api/branches

Returns array of all branches. Each branch has:
- `branch_id`, `branch_name`, `institution_type` ("bank" or "credit_union")
- `state_code`, `total_assets`, `lending_capacity_q1`, `sector_ceiling_pct`
- `cre_policy_limit_pct` (for banks)
- `fdic_benchmark_set` (e.g. "fdic_q4_2024", or empty for credit unions)

## /api/branches/{branch_id}

Same shape as an item in `/api/branches`.

## /api/branches/{branch_id}/metrics

Returns array of quarterly metrics, newest first. Each entry:
- `quarter`, `total_loans_outstanding`, `nonperforming_loans`
- `delinquency_30_plus_pct` (ratio), `net_charge_offs`, `allowance_for_loan_losses`
- `total_deposits`

Always use the **latest quarter** (first in array) for current metrics.

## /api/branches/{branch_id}/loans

Returns array of all loans for the branch. Each loan:
- `loan_id`, `borrower_name`, `branch_id`, `sector`, `loan_type`
- `current_rating` (integer 1-8), `payment_status`, `days_past_due`
- `outstanding_balance` (float, USD), `annual_debt_service`
- `dscr` (float, nullable), `ltv` (float, nullable), `fico` (integer, nullable)
- `collateral_value` (float, nullable), `debt_to_asset` (float, nullable)
- `liquidity_months` (float, nullable), `guarantor_strength`, `interest_rate`
- `annual_review_date`, `notes`

## /api/branches/{branch_id}/sector-exposures

Returns array of sector exposure records:
- `sector`, `current_exposure` (float, USD), `limit_pct` (ratio)
- `grandfathered` (0 or 1), `branch_id`

The `limit_pct` here overrides the branch's `sector_ceiling_pct` for that specific sector.

## /api/branches/{branch_id}/applications

Returns array of pending applications. Each application:
- `application_id`, `applicant_name`, `business_name`, `branch_id`
- `sector`, `loan_type`, `requested_amount` (float, USD)
- `dscr`, `ltv`, `fico` (nullable), `dti` (nullable)
- `collateral_value`, `net_income`, `total_assets`, `total_debt`
- `annual_revenue`, `years_in_business`, `existing_relationship_years`
- `relationship_deposit_balance`, `prior_delinquencies_12m`
- `bankruptcy_months_ago` (nullable), `documentation_complete` (0 or 1)
- `sba_guaranty_pct` (nullable), `co_guarantor_strength`
- `proposed_rate`, `purpose`, `term_months`, `notes`

## /api/benchmarks/fdic/q4-2024

Returns a single object:
- `benchmark_version`: "fdic_q4_2024"
- `total_loans_noncurrent_pct` (ratio)
- `total_real_estate_noncurrent_pct` (ratio)
- `total_real_estate_30_89_pct` (ratio)
- `construction_development_30_89_pct` (ratio)
- `construction_development_noncurrent_pct` (ratio)

## /api/benchmarks/ncua/q1-2025

Returns an object with `benchmark_version` and `rows` array. Each row:
- `state_code`, `delinquency_bps` (int), `loan_to_share_pct` (int)
- `roaa_bps` (int), `positive_net_income_pct` (int)

The row with `state_code == "US"` is the national aggregate.

## /api/credit-union-segments/{segment_id}

Returns a single segment object:
- `segment_id`, `segment_name`, `state_code`
- `member_profile`, `portfolio_focus` (array of strings)
- `peer_states` (array of state_code strings)
- `minimum_checklist` (array of gate strings)
- `quarterly_capacity` (float), `current_outstanding` (float)
- `internal_context`: { `recent_delinquency_bps` (int), `control_issue` (string), `portfolio_yield_pct`, `staffing_constraint` }
- `risk_tolerance`: "restrained" | "moderate" | "expansive"
- `notes`
