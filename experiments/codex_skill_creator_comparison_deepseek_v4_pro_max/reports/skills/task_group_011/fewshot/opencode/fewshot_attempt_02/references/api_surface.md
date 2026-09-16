# API Surface Reference

Base URL: `<TASK_ENV_BASE_URL>`

All endpoints are GET. No authentication required.

## Endpoints

### GET /api/manifest

Returns dataset metadata: benchmark_versions, record_counts, policy_version,
public_api_endpoints list.

Key fields:
- `benchmark_versions.fdic` — e.g. "fdic_q4_2024"
- `benchmark_versions.ncua` — e.g. "ncua_q1_2025"
- `policy_version` — e.g. "credit_policy_v2025Q1"
- `record_counts` — counts of branches, loans, applications, etc.

### GET /api/policies

Returns the full credit policy framework. Key sections:

- `risk_rating` — dscr_thresholds, ltv_thresholds, delinquency_minimums,
  dominant_factor_rule, material_downgrade_notches
- `cdfi_factor_scores` — fico, liquidity_months, ltv, debt_to_asset score
  tables and risk class mapping
- `cre_weighted_score` — weights (capacity, capital, character,
  collateral_exposure, conditions), score_class thresholds
- `stress` — watch_list_formula, cre_dual_stress_formula,
  coverage_breach_threshold
- `capacity_concentration` — lending_capacity_field, sector_ceiling_field,
  allowed_mitigations, grandfathering_note

### GET /api/branches

Returns a list of all branches. Each branch has:

- `branch_id` (string) — ex: "BRANCH-01", "BRANCH-02"
- `branch_name` (string)
- `institution_type` — "bank" or "credit_union"
- `state_code` (string)
- `lending_capacity_q1` (number) — quarterly lending budget
- `total_assets` (number)
- `sector_ceiling_pct` (number) — single-sector concentration limit as ratio
- `cre_policy_limit_pct` (number) — CRE concentration limit as ratio
- `fdic_benchmark_set` (string) — empty for credit unions

### GET /api/branches/{branch_id}

Single branch detail, same shape as list item.

### GET /api/branches/{branch_id}/metrics

Returns quarterly metrics (1-4 quarters). Each record has:

- `branch_id`, `quarter`
- `total_loans_outstanding` (number) — denominator for concentration ratios
- `total_deposits` (number)
- `nonperforming_loans` (number)
- `delinquency_30_plus_pct` (number) — ratio of 30+ DPD loans
- `net_charge_offs` (number)
- `allowance_for_loan_losses` (number)

Use the most recent quarter (e.g. 2025Q1) for current metrics.

### GET /api/branches/{branch_id}/loans

Returns all loans for the branch. Each loan has:

- `loan_id` (string) — ex: "LN-001"
- `borrower_name` (string)
- `branch_id` (string)
- `loan_type` (string) — "CRE", "C&I", "SBA", "Equipment", "Consumer", etc.
- `sector` (string) — "Office", "Healthcare", "Construction", "Retail CRE", etc.
- `outstanding_balance` (number, USD)
- `current_rating` (integer, 1-8)
- `payment_status` (enum) — "Current", "30 Days Past Due", "60 Days Past Due",
  "90+ Days Past Due", "Nonaccrual"
- `dscr` (number or null)
- `ltv` (number or null)
- `fico` (integer or null)
- `debt_to_asset` (number or null)
- `liquidity_months` (number or null)
- `collateral_value` (number)
- `annual_debt_service` (number or null)
- `interest_rate` (number)
- `days_past_due` (integer)
- `guarantor_strength` (string or null)
- `annual_review_date` (string)
- `notes` (string)

### GET /api/branches/{branch_id}/sector-exposures

Returns sector concentration data. Each record has:

- `branch_id` (string)
- `sector` (string)
- `current_exposure` (number, USD) — total outstanding in that sector
- `limit_pct` (number) — sector concentration limit as ratio
- `grandfathered` (integer) — 0 or 1

### GET /api/branches/{branch_id}/applications

Returns pending loan applications for the branch. Each application has
varying fields depending on loan type. Common fields:

- `application_id` (string) — ex: "LAK-APP-001"
- `applicant_name` (string)
- `business_name` (string)
- `branch_id` (string)
- `loan_type` (string) — "CRE", "SBA", "Equipment", "Consumer", "C&I"
- `sector` (string)
- `requested_amount` (number, USD)
- `dscr` (number or null)
- `ltv` (number or null)
- `fico` (integer or null)
- `collateral_value` (number or null)
- `term_months` (integer)
- `proposed_rate` (number)
- `sba_guaranty_pct` (number or null)
- `documentation_complete` (0 or 1)
- `years_in_business` (number or null)
- `prior_delinquencies_12m` (integer or null)
- `bankruptcy_months_ago` (integer or null)
- `existing_relationship_years` (number or null)
- `net_income` (number or null)
- `total_assets` (number or null)
- `total_debt` (number or null)
- `annual_revenue` (number or null)
- `purpose` (string)
- `relationship_deposit_balance` (number)
- `notes` (string)

**Field name variations across endpoints**: the loans and applications
endpoints use different field names for the same concepts. Loans use
`outstanding_balance`, `borrower_name`, `current_rating`. Applications
use `requested_amount`, `applicant_name`, and have no rating field. Always
check the actual API response for exact field names.

### GET /api/benchmarks/fdic/q4-2024

FDIC Q4 2024 benchmark ratios. Single object with:

- `total_loans_noncurrent_pct`
- `total_real_estate_noncurrent_pct`
- `total_real_estate_30_89_pct`
- `construction_development_30_89_pct`
- `construction_development_noncurrent_pct`

All values are ratios (e.g. 0.0098 = 0.98%).

### GET /api/benchmarks/ncua/q1-2025

NCUA Q1 2025 benchmark table. Returns an object with `rows` array. Each row:

- `state_code` (string) — "AL", "NC", "US", etc.
- `delinquency_bps` (integer)
- `loan_to_share_pct` (integer)
- `roaa_bps` (integer)
- `positive_net_income_pct` (integer)

### GET /api/credit-union-segments/{segment_id}

Returns credit-union segment detail. Key fields:

- `segment_id` (string)
- `segment_name` (string)
- `state_code` (string)
- `member_profile` (string)
- `portfolio_focus` (array of strings)
- `peer_states` (array of state codes)
- `quarterly_capacity` (number)
- `risk_tolerance` (enum) — "restrained", "moderate", "expansive"
- `current_outstanding` (number)
- `minimum_checklist` (array of enum strings)
- `internal_context` — object with `recent_delinquency_bps`, `control_issue`,
  `staffing_constraint`, `portfolio_yield_pct`
- `notes` (string)

## Data Relationships

- Branch `lending_capacity_q1` drives the allocation archetype.
- Branch `total_loans_outstanding` (from metrics, most recent quarter) is the
  denominator for all concentration ratios.
- Branch `sector_ceiling_pct` is the default sector limit; sector-exposures
  may have per-sector overrides.
- Branch `cre_policy_limit_pct` is the CRE-specific concentration limit.
- Credit-union branches have `institution_type` "credit_union" and empty
  `fdic_benchmark_set`; they use NCUA benchmarks and the segment endpoint.
- Bank branches have `institution_type` "bank" and use FDIC benchmarks.
