# API Endpoints Reference

Base URL: `<TASK_ENV_BASE_URL>`. All endpoints return JSON. No authentication required.

## List of Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/manifest` | Environment metadata, benchmark versions, record counts |
| `/api/branches` | All 10 branches with metadata |
| `/api/branches/{branch_id}` | Single branch record |
| `/api/branches/{branch_id}/metrics` | Quarterly financial metrics for the branch |
| `/api/branches/{branch_id}/loans` | Loan portfolio for the branch |
| `/api/branches/{branch_id}/sector-exposures` | Sector-level exposure and limits |
| `/api/branches/{branch_id}/applications` | Pending loan applications |
| `/api/policies` | Credit policy rules (risk ratings, CDFI, stress, concentration) |
| `/api/benchmarks/fdic/q4-2024` | FDIC Q4 2024 benchmark ratios |
| `/api/benchmarks/ncua/q1-2025` | NCUA Q1 2025 state-level benchmark rows |
| `/api/credit-union-segments/{segment_id}` | Credit union segment profile |

---

## `/api/manifest`

```json
{
  "benchmark_versions": { "fdic": "fdic_q4_2024", "ncua": "ncua_q1_2025" },
  "policy_version": "credit_policy_v2025Q1",
  "public_api_endpoints": [ ... ],
  "record_counts": { "branches": 10, "loans": 161, "applications": 59, ... }
}
```

---

## `/api/branches` and `/api/branches/{branch_id}`

Branch record fields:

| Field | Type | Description |
|-------|------|-------------|
| branch_id | string | Stable identifier (e.g. BRANCH-ID) |
| branch_name | string | Human-readable name |
| institution_type | string | "bank" or "credit_union" |
| state_code | string | Two-letter state code |
| lending_capacity_q1 | number | Q1 lending capacity in USD |
| sector_ceiling_pct | number | Default single-sector concentration limit (ratio) |
| cre_policy_limit_pct | number | CRE-specific concentration limit (ratio) |
| fdic_benchmark_set | string | FDIC benchmark version, empty for credit unions |
| total_assets | number | Total branch assets in USD |

---

## `/api/branches/{branch_id}/metrics`

Array of quarterly metrics. Use the most recent quarter (first element).

| Field | Type | Description |
|-------|------|-------------|
| branch_id | string | Branch identifier |
| quarter | string | e.g. "2025Q1" |
| total_loans_outstanding | number | Total loan portfolio in USD |
| total_deposits | number | Total deposits in USD |
| nonperforming_loans | number | NPA exposure in USD |
| delinquency_30_plus_pct | number | 30+ day delinquency ratio |
| allowance_for_loan_losses | number | ALLL reserve in USD |
| net_charge_offs | number | Net charge-offs in USD |

---

## `/api/branches/{branch_id}/loans`

Array of loan records. Each loan:

| Field | Type | Description |
|-------|------|-------------|
| loan_id | string | Unique loan identifier (e.g. BR-LN-001) |
| branch_id | string | Branch identifier |
| borrower_name | string | Borrower legal name |
| loan_type | string | CRE, C&I, SBA, Equipment, HELOC, Consumer, Residential Mortgage |
| sector | string | Industry sector |
| outstanding_balance | number | Current exposure in USD |
| current_rating | integer | 1-8 risk rating (1=best, 8=worst) |
| payment_status | string | Current / 30 Days Past Due / 60 Days Past Due / 90+ Days Past Due / Nonaccrual |
| days_past_due | integer | Days delinquent |
| dscr | number or null | Debt Service Coverage Ratio |
| ltv | number or null | Loan-to-Value ratio |
| collateral_value | number or null | Appraised collateral value in USD |
| fico | integer or null | Borrower FICO score |
| debt_to_asset | number or null | Debt-to-asset ratio |
| liquidity_months | number or null | Months of liquidity |
| annual_debt_service | number or null | Annual debt service in USD |
| interest_rate | number | Contract rate (decimal, e.g. 5.86 = 5.86%) |
| guarantor_strength | string | strong / standard / limited / none |
| annual_review_date | string | Last annual review date (YYYY-MM-DD) |
| notes | string | Analyst notes |

---

## `/api/branches/{branch_id}/sector-exposures`

Array of sector concentration records:

| Field | Type | Description |
|-------|------|-------------|
| branch_id | string | Branch identifier |
| sector | string | Industry sector |
| current_exposure | number | Current exposure in USD |
| limit_pct | number | Sector concentration limit (ratio) |
| grandfathered | integer | 0 or 1; if 1, existing over-limit exposure may be grandfathered |

---

## `/api/branches/{branch_id}/applications`

Array of pending applications. Each application:

| Field | Type | Description |
|-------|------|-------------|
| application_id | string | e.g. BR-APP-001 |
| branch_id | string | Branch identifier |
| applicant_name | string | Applicant name |
| business_name | string | Business name (may be empty) |
| loan_type | string | CRE, C&I, SBA, Consumer, etc. |
| sector | string | Industry sector |
| requested_amount | number | Amount requested in USD |
| purpose | string | Loan purpose |
| term_months | integer | Proposed term |
| proposed_rate | number | Proposed interest rate |
| dscr | number or null | Debt service coverage ratio |
| ltv | number or null | Loan-to-value ratio |
| fico | integer or null | Applicant FICO |
| collateral_value | number or null | Collateral value in USD |
| annual_revenue | number or null | Annual revenue |
| net_income | number or null | Net income |
| total_assets | number or null | Total assets |
| total_debt | number or null | Total debt |
| years_in_business | number or null | Years in business |
| existing_relationship_years | number | Years as existing customer |
| relationship_deposit_balance | number | Deposit balance in USD |
| prior_delinquencies_12m | integer | Prior 12-month delinquencies |
| bankruptcy_months_ago | integer or null | Months since bankruptcy, null if none |
| sba_guaranty_pct | number or null | SBA guaranty percentage |
| co_guarantor_strength | string | strong / standard / limited / none |
| documentation_complete | integer | 1=complete, 0=incomplete |
| notes | string | Analyst notes |

---

## `/api/policies`

Returns the full credit policy document. Key sections:

- `risk_rating`: DSCR/LTV thresholds, delinquency minimums, dominant factor rule
- `cdfi_factor_scores`: CDFI scoring tables and risk class ranges
- `cre_weighted_score`: Weights and score class thresholds
- `stress`: Watch-list and CRE stress formulas and breach threshold
- `capacity_concentration`: Sector limit rules, mitigation options
- `policy_version`: Current policy version string

See [references/policy_rules.md](policy_rules.md) for the detailed reference tables.

---

## `/api/benchmarks/fdic/q4-2024`

Single object:

| Field | Type | Description |
|-------|------|-------------|
| benchmark_version | string | "fdic_q4_2024" |
| total_loans_noncurrent_pct | number | All loans noncurrent ratio |
| total_real_estate_noncurrent_pct | number | Real estate noncurrent ratio |
| total_real_estate_30_89_pct | number | Real estate 30-89 day delinquency ratio |
| construction_development_noncurrent_pct | number | C&D noncurrent ratio |
| construction_development_30_89_pct | number | C&D 30-89 day delinquency ratio |

---

## `/api/benchmarks/ncua/q1-2025`

Object with `benchmark_version` and `rows` array. Each row:

| Field | Type | Description |
|-------|------|-------------|
| state_code | string | Two-letter state code (or "US" for national) |
| delinquency_bps | integer | Delinquency in basis points |
| loan_to_share_pct | integer | Loan-to-share ratio as integer percent |
| roaa_bps | integer | Return on average assets in basis points |
| positive_net_income_pct | integer | Percent of CUs with positive net income |

---

## `/api/credit-union-segments/{segment_id}`

Segment profile object:

| Field | Type | Description |
|-------|------|-------------|
| segment_id | string | Segment identifier |
| segment_name | string | Human-readable name |
| state_code | string | State code |
| member_profile | string | Description of member base |
| portfolio_focus | array | List of equipment/loan types |
| quarterly_capacity | number | Quarterly lending capacity in USD |
| current_outstanding | number | Current portfolio outstanding in USD |
| risk_tolerance | string | restrained / moderate / expansive |
| minimum_checklist | array | Required checklist gate enums |
| peer_states | array | Peer state codes for comparison |
| internal_context | object | Internal notes: control_issue, recent_delinquency_bps, staffing_constraint, portfolio_yield_pct |
| notes | string | Analyst notes |
