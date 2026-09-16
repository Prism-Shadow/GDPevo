## API Endpoints Reference

Base URL: `<TASK_ENV_BASE_URL>` (supplied by the runner). No credentials required.

### GET /api/manifest

Returns metadata about available endpoints, benchmark versions, record counts.

```json
{
  "benchmark_versions": {"fdic": "fdic_q4_2024", "ncua": "ncua_q1_2025"},
  "policy_version": "credit_policy_v2025Q1",
  "public_api_endpoints": ["..."],
  "record_counts": {"branches": 10, "loans": 161, "applications": 59, ...}
}
```

### GET /api/policies

Returns the full credit policy document: risk-rating rules, CDFI factor scores, CRE weighted-score weights, stress formulas, capacity/concentration rules.

**Top-level keys and what they contain:**

- `policy_version` — e.g. `"credit_policy_v2025Q1"`
- `risk_rating` — delinquency minimums, DSCR thresholds, LTV thresholds, dominant-factor rule, material-downgrade notches
- `cdfi_factor_scores` — factor tables (`fico`, `ltv`, `debt_to_asset`, `liquidity_months`) with score ranges and class thresholds
- `cre_weighted_score` — weights (`capacity`, `collateral_exposure`, `conditions`, `capital`, `character`) and class thresholds
- `stress` — `watch_list_formula`, `cre_dual_stress_formula`, `coverage_breach_threshold`, `watch_list_parallel_shock`
- `capacity_concentration` — lending-capacity field name, sector-ceiling field name, allowed mitigations, grandfathering note

### GET /api/branches

Returns array of all branches with:

| Field | Description |
|---|---|
| `branch_id` | Stable identifier (e.g. `REDWOOD`, `LAKEVIEW`, `SUMMIT`, `HARBOR`) |
| `branch_name` | Display name |
| `institution_type` | `"bank"` or `"credit_union"` |
| `lending_capacity_q1` | Q1 dollars available for new originations |
| `sector_ceiling_pct` | Per-sector concentration limit (ratio, e.g. 0.23) |
| `cre_policy_limit_pct` | CRE-specific concentration limit (ratio) |
| `fdic_benchmark_set` | Benchmark set or `""` for credit unions |
| `state_code` | Two-letter state |
| `total_assets` | Total branch assets |

### GET /api/branches/{branch_id}

Same single-branch shape as above.

### GET /api/branches/{branch_id}/loans

Array of loan objects. Each loan has:

| Field | Description |
|---|---|
| `loan_id` | String identifier |
| `borrower_name` | Name |
| `branch_id` | Branch |
| `sector` | Sector label |
| `loan_type` | `CRE`, `C&I`, `SBA`, `HELOC`, `Term`, etc. |
| `current_rating` | Integer 1-8 |
| `outstanding_balance` | USD exposure (float) |
| `dscr` | Debt-service coverage ratio (float or null) |
| `ltv` | Loan-to-value ratio (float or null) |
| `collateral_value` | USD (float or null) |
| `fico` | Integer or null |
| `debt_to_asset` | Float or null |
| `liquidity_months` | Float or null |
| `guarantor_strength` | `"strong"`, `"standard"`, `"limited"`, `"none"` |
| `payment_status` | `"Current"`, `"30 Days Past Due"`, `"60 Days Past Due"`, `"90+ Days Past Due"`, `"Nonaccrual"` |
| `days_past_due` | Integer |
| `annual_debt_service` | Float |
| `interest_rate` | Float |
| `annual_review_date` | String date |
| `notes` | String description |

### GET /api/branches/{branch_id}/metrics

Array of quarterly metric objects (current quarter first):

| Field | Description |
|---|---|
| `quarter` | e.g. `"2025Q1"` |
| `total_loans_outstanding` | Float |
| `nonperforming_loans` | Float |
| `total_deposits` | Float |
| `delinquency_30_plus_pct` | Ratio (float) |
| `allowance_for_loan_losses` | Float |
| `net_charge_offs` | Float |

### GET /api/branches/{branch_id}/sector-exposures

Array per sector:

| Field | Description |
|---|---|
| `sector` | Sector name |
| `current_exposure` | USD (float) |
| `limit_pct` | Sector limit ratio |
| `grandfathered` | Integer |

### GET /api/branches/{branch_id}/applications

Array of pending application objects. Each application has:

| Field | Description |
|---|---|
| `application_id` | String identifier |
| `applicant_name` | Person name |
| `business_name` | Business name |
| `branch_id` | String |
| `sector` | Sector label |
| `loan_type` | `CRE`, `C&I`, `SBA`, etc. |
| `requested_amount` | USD |
| `purpose` | Description |
| `fico` | Integer or null |
| `ltv` | Float |
| `dscr` | Float |
| `collateral_value` | Float |
| `annual_revenue` | Float |
| `net_income` | Float |
| `total_assets` | Float |
| `total_debt` | Float |
| `debt_to_asset` | Float or null |
| `years_in_business` | Float |
| `existing_relationship_years` | Float |
| `relationship_deposit_balance` | Float |
| `bankruptcy_months_ago` | Integer or null |
| `prior_delinquencies_12m` | Integer |
| `documentation_complete` | 0 or 1 |
| `proposed_rate` | Float |
| `term_months` | Integer |
| `sba_guaranty_pct` | Float or null |
| `co_guarantor_strength` | `"strong"`, `"standard"`, `"limited"`, `"none"` |
| `dti` | Float or null |
| `notes` | String |

### GET /api/benchmarks/fdic/q4-2024

Single object:

| Field | Description |
|---|---|
| `benchmark_version` | `"fdic_q4_2024"` |
| `total_loans_noncurrent_pct` | Ratio |
| `total_real_estate_noncurrent_pct` | Ratio |
| `construction_development_noncurrent_pct` | Ratio |
| `total_real_estate_30_89_pct` | Ratio |
| `construction_development_30_89_pct` | Ratio |

### GET /api/benchmarks/ncua/q1-2025

Object with `benchmark_version` and `rows` array. Each row:

| Field | Description |
|---|---|
| `state_code` | Two-letter (including `"US"` for national) |
| `delinquency_bps` | Integer basis points |
| `loan_to_share_pct` | Integer percentage |
| `roaa_bps` | Integer basis points |
| `positive_net_income_pct` | Integer percentage |

### GET /api/credit-union-segments/{segment_id}

Single object:

| Field | Description |
|---|---|
| `segment_id` | Stable identifier |
| `segment_name` | Display name |
| `state_code` | Two-letter |
| `member_profile` | Description of member base |
| `portfolio_focus` | Array of equipment categories |
| `quarterly_capacity` | USD |
| `current_outstanding` | USD |
| `risk_tolerance` | `"moderate"` or `"restrained"` or (implied) `"expansive"` |
| `peer_states` | Array of state codes for comparison |
| `minimum_checklist` | Array of required gate strings |
| `internal_context` | Object with `recent_delinquency_bps`, `control_issue`, `staffing_constraint`, `portfolio_yield_pct` |
| `notes` | String context |

### Common patterns

- Numeric values with `null` signal unavailable data; compute accordingly (skip nulls, note unavailability).
- Loan `current_rating` is the existing rating assigned to the loan before re-derivation.
- When the task asks for "loans rated X or worse," filter `current_rating >= X`.
- Sorted outputs must follow the ordering specified in the answer template.
