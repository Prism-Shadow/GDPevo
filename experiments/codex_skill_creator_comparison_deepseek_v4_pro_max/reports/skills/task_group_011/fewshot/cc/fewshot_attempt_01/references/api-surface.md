# Credit Office API Reference

Base URL is supplied as `{TASK_ENV_BASE_URL}`. All endpoints return JSON arrays or objects.

## GET /api/manifest

Returns the system manifest — available endpoints, benchmark versions, record counts, and policy version.

```json
{
  "benchmark_versions": {"fdic": "fdic_q4_2024", "ncua": "ncua_q1_2025"},
  "generated_at": "2025-03-31T00:00:00Z",
  "public_api_endpoints": ["/api/health", "/api/manifest", ...],
  "policy_version": "credit_policy_v2025Q1"
}
```

Key fields: `benchmark_versions` tells you which benchmark version name to use in output fields. `policy_version` confirms the policy set you are applying.

## GET /api/policies

Returns the full credit policy document. See `references/policy-rules.md` for how to apply each section.

Key top-level fields:

- `policy_version` — version identifier string
- `risk_rating` — rating derivation rules
  - `dominant_factor_rule` — description of the worst-of rule
  - `dscr_thresholds` — array of {min, rating} or {max_below, rating}
  - `ltv_thresholds` — array of {max, rating} or {min_above, rating}
  - `delinquency_minimums` — map of payment_status to integer rating floor
  - `material_downgrade_notches` — integer, usually 2
- `cdfi_factor_scores` — factor scoring tables
  - `fico`, `ltv`, `debt_to_asset`, `liquidity_months` — each an array of {range, score}
  - `classes` — risk class definitions with score ranges
- `cre_weighted_score` — CRE scoring framework
  - `weights` — {capacity, capital, character, collateral_exposure, conditions}
  - `classes` — class definitions with max/min thresholds
- `stress` — stress formulas and thresholds
  - `watch_list_formula` and `watch_list_parallel_shock`
  - `cre_dual_stress_formula`
  - `coverage_breach_threshold`
- `capacity_concentration` — concentration rules and allowed mitigations

## GET /api/branches

Returns all branches as an array. Each branch object:

| Field | Type | Description |
|---|---|---|
| `branch_id` | string | Unique branch identifier |
| `branch_name` | string | Display name |
| `institution_type` | string | "bank" or "credit_union" |
| `lending_capacity_q1` | number | Q1 lending capacity in USD |
| `sector_ceiling_pct` | number | Default single-sector limit (ratio, not percent) |
| `cre_policy_limit_pct` | number | CRE concentration limit (ratio) |
| `fdic_benchmark_set` | string | Benchmark version tag (empty for credit unions) |
| `state_code` | string | Two-letter state code |
| `total_assets` | number | Total branch assets in USD |

## GET /api/branches/{branch_id}

Same shape as a single element from `/api/branches`.

## GET /api/branches/{branch_id}/metrics

Returns quarterly metrics array, latest quarter first. Each record:

| Field | Type | Description |
|---|---|---|
| `quarter` | string | "2025Q1", "2024Q4", etc. |
| `total_deposits` | number | Total deposits in USD |
| `total_loans_outstanding` | number | Total loan portfolio in USD |
| `nonperforming_loans` | number | NPA exposure in USD |
| `delinquency_30_plus_pct` | number | 30+ day delinquency ratio |
| `allowance_for_loan_losses` | number | ALLL reserve in USD |
| `net_charge_offs` | number | Net charge-offs in USD |

For NPA calculations, use `nonperforming_loans / total_loans_outstanding`.

## GET /api/branches/{branch_id}/loans

Returns all loans for the branch as an array. Each loan object:

| Field | Type | Description |
|---|---|---|
| `loan_id` | string | Unique loan identifier |
| `borrower_name` | string | Borrower entity name |
| `branch_id` | string | Owning branch |
| `loan_type` | string | CRE, C&I, Equipment, SBA, HELOC, Consumer, Residential Mortgage |
| `sector` | string | Industry sector |
| `outstanding_balance` | number | Current exposure in USD |
| `current_rating` | integer | Assigned risk rating (1-8, higher is worse) |
| `payment_status` | string | Current, 30 Days Past Due, 60 Days Past Due, 90+ Days Past Due, Nonaccrual |
| `days_past_due` | integer | Days delinquent |
| `dscr` | number or null | Debt service coverage ratio |
| `ltv` | number or null | Loan-to-value ratio |
| `collateral_value` | number or null | Appraised collateral value in USD |
| `fico` | integer or null | Borrower FICO score |
| `debt_to_asset` | number or null | Total debt to total assets ratio |
| `liquidity_months` | number or null | Months of liquidity |
| `interest_rate` | number | Contract rate |
| `annual_debt_service` | number | Annual debt service in USD |
| `guarantor_strength` | string | none, limited, standard, strong |
| `annual_review_date` | string | Last annual review date |
| `notes` | string | Analyst commentary |

## GET /api/branches/{branch_id}/sector-exposures

Returns sector-level exposure summary per branch. Each record:

| Field | Type | Description |
|---|---|---|
| `sector` | string | Industry sector name |
| `current_exposure` | number | Current sector exposure in USD |
| `limit_pct` | number | Sector-specific limit (ratio) — may differ from branch default |
| `grandfathered` | integer | 1 if existing over-limit exposure is grandfathered, 0 otherwise |

## GET /api/branches/{branch_id}/applications

Returns pending applications for the branch. Each application:

| Field | Type | Description |
|---|---|---|
| `application_id` | string | Unique application identifier |
| `applicant_name` | string | Individual applicant name |
| `business_name` | string | Business entity (may be empty for consumer) |
| `loan_type` | string | CRE, C&I, Equipment, SBA, Consumer, Residential Mortgage |
| `sector` | string | Industry sector |
| `requested_amount` | number | Amount requested in USD |
| `dscr` | number or null | Proposed DSCR |
| `ltv` | number or null | Proposed LTV |
| `fico` | integer or null | Applicant FICO |
| `collateral_value` | number | Collateral value in USD |
| `annual_revenue` | number or null | Annual business revenue |
| `net_income` | number or null | Net income |
| `total_assets` | number or null | Total assets |
| `total_debt` | number or null | Total debt |
| `years_in_business` | number or null | Years in business |
| `prior_delinquencies_12m` | integer | Delinquencies in past 12 months |
| `bankruptcy_months_ago` | integer or null | Months since bankruptcy (null = none) |
| `existing_relationship_years` | number | Years of relationship |
| `relationship_deposit_balance` | number | Deposit balance with bank |
| `documentation_complete` | integer | 1 if complete, 0 if incomplete |
| `co_guarantor_strength` | string | none, limited, standard, strong |
| `sba_guaranty_pct` | number or null | SBA guaranty percentage |
| `proposed_rate` | number | Proposed interest rate |
| `term_months` | integer | Loan term in months |
| `purpose` | string | Stated purpose |
| `notes` | string | Analyst commentary |

## GET /api/benchmarks/fdic/q4-2024

Returns a single object with FDIC benchmark ratios:

| Field | Type | Description |
|---|---|---|
| `benchmark_version` | string | "fdic_q4_2024" |
| `total_loans_noncurrent_pct` | number | National NPA ratio |
| `total_real_estate_noncurrent_pct` | number | Real estate NPA ratio |
| `construction_development_noncurrent_pct` | number | Construction NPA ratio |
| `total_real_estate_30_89_pct` | number | Real estate 30-89 day delinquency ratio |
| `construction_development_30_89_pct` | number | Construction 30-89 day delinquency ratio |

## GET /api/benchmarks/ncua/q1-2025

Returns an object with `benchmark_version` and `rows` — an array of state-level NCUA metrics. Each row:

| Field | Type | Description |
|---|---|---|
| `state_code` | string | State code; "US" row is the national aggregate |
| `delinquency_bps` | integer | Delinquency in basis points |
| `loan_to_share_pct` | integer | Loan-to-share ratio as percent |
| `roaa_bps` | integer | Return on average assets in basis points |
| `positive_net_income_pct` | integer | Percent of institutions with positive net income |

Peer comparisons: find the target state row, compute medians across listed peer state rows, and compare directionally (higher/lower/equal). The "US" row is the national comparison.

## GET /api/credit-union-segments/{segment_id}

Returns segment detail for a credit-union segment. Fields:

| Field | Type | Description |
|---|---|---|
| `segment_id` | string | Segment identifier |
| `segment_name` | string | Display name |
| `state_code` | string | Primary state |
| `member_profile` | string | Description of member base |
| `portfolio_focus` | array | Equipment types in scope |
| `quarterly_capacity` | number | Lending capacity in USD |
| `current_outstanding` | number | Current portfolio in USD |
| `risk_tolerance` | string | moderate, restrained, expansive |
| `peer_states` | array | State codes for peer comparison |
| `minimum_checklist` | array | Required closing checklist items |
| `internal_context` | object | Internal risk metrics and notes |
| `notes` | string | Segment-level commentary |

Use `internal_context.recent_delinquency_bps` for escalation trigger evaluation.
