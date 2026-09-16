# Credit Office API Reference

Base URL is supplied by the runner as `<TASK_ENV_BASE_URL>`. All endpoints return JSON. No
authentication is required.

## Table of Contents

- [GET /api/manifest](#get-apimanifest)
- [GET /api/policies](#get-apipolicies)
- [GET /api/branches](#get-apibranches)
- [GET /api/branches/{branch_id}](#get-apibranchesbranch_id)
- [GET /api/branches/{branch_id}/metrics](#get-apibranchesbranch_idmetrics)
- [GET /api/branches/{branch_id}/loans](#get-apibranchesbranch_idloans)
- [GET /api/branches/{branch_id}/sector-exposures](#get-apibranchesbranch_idsector-exposures)
- [GET /api/branches/{branch_id}/applications](#get-apibranchesbranch_idapplications)
- [GET /api/benchmarks/fdic/q4-2024](#get-apibenchmarksfdicq4-2024)
- [GET /api/benchmarks/ncua/q1-2025](#get-apibenchmarksncuaq1-2025)
- [GET /api/credit-union-segments/{segment_id}](#get-apicredit-union-segmentssegment_id)

---

## GET /api/manifest

Summary metadata about the API and data set. Useful for discovering available endpoints
and record counts.

```
{
  "benchmark_versions": { "fdic": "fdic_q4_2024", "ncua": "ncua_q1_2025" },
  "policy_version": "credit_policy_v2025Q1",
  "record_counts": {
    "applications": 59, "branches": 10, "loans": 161,
    "sector_exposures": 85, "branch_metrics": 20,
    "credit_union_segments": 2, "fdic_benchmarks": 1,
    "ncua_benchmarks": 12, "policies": 1
  }
}
```

---

## GET /api/policies

Single object containing all credit policy rules. No query params.

Top-level keys: `policy_version`, `capacity_concentration`, `cdfi_factor_scores`,
`cre_weighted_score`, `risk_rating`, `stress`.

### capacity_concentration

- `lending_capacity_field`: `"branches.lending_capacity_q1"`
- `single_sector_default_field`: `"branches.sector_ceiling_pct"`
- `branch_sector_override_table`: `"sector_exposures"` — per-sector override limit_pct
- `allowed_mitigations`: `["participation_required", "reduced_amount", "board_exception"]`
- Grandfathering note: existing over-ceiling exposure may be grandfathered, but new approvals
  may not worsen that sector without mitigation.

### cdfi_factor_scores

Risk classes:

| Class | Score Range |
|-------|------------|
| Prime | 0-5 |
| Desirable | 6-9 |
| Satisfactory | 10-13 |
| Watch | 14-18 |
| Doubtful | >=19 |
| Projected Loss | >=19 and ltv > 1.0 |

Factor scoring tables — sum across available factors. Skip null factors.

**FICO**: >720→0, 680-720→1, 580-679→3, <580→5

**Debt-to-Asset**: <0.40→0, 0.40-0.60→2, 0.60-0.80→4, >0.80→6

**Liquidity Months**: >12→0, 6-12→1, 3-6→3, <3→5

**LTV**: <0.40→0, 0.40-0.60→2, 0.60-0.80→4, >0.80→6

### cre_weighted_score

Weights: capacity 0.45, capital 0.03, character 0.05, collateral_exposure 0.36,
conditions 0.11. Each sub-score is 1-5, lower is better.

Weighted score = sum(weight_i * sub_score_i). Classes:

| Class | Threshold |
|-------|-----------|
| approve_quality | <= 2.0 |
| conditional | <= 3.0 |
| weak | > 3.0 |

### risk_rating

Dominant factor rule: final re-derived rating = worst (highest) numeric rating from
available DSCR, LTV/collateral, and delinquency factors. If the payment-status minimum
exceeds the factor-derived rating, use the delinquency floor.

DSCR thresholds:

| Condition | Rating |
|-----------|--------|
| DSCR >= 1.50 | 3 |
| DSCR >= 1.25 | 4 |
| DSCR >= 1.05 | 5 |
| DSCR >= 1.00 | 6 |
| DSCR < 1.00 | 7 |
| DSCR is null | skip |

LTV thresholds:

| Condition | Rating |
|-----------|--------|
| LTV <= 0.65 | 3 |
| LTV <= 0.75 | 4 |
| LTV <= 0.85 | 5 |
| LTV <= 1.00 | 6 |
| LTV > 1.00 | 7 |
| LTV is null | skip |

Delinquency minimums (payment status floor):

| Payment Status | Floor Rating |
|----------------|-------------|
| Current | none (null) |
| 30 Days Past Due | 4 |
| 60 Days Past Due | 5 |
| 90+ Days Past Due | 7 |
| Nonaccrual | 8 |

Material downgrade: 2 or more notches (final_rating - current_rating >= 2).

### stress

- `coverage_breach_threshold`: 1.0
- `watch_list_formula`: `stressed_dscr = dscr / (1 + 0.18)` — +200bp parallel shock
- `cre_dual_stress_formula`: `stressed_dscr = dscr * 0.85 / (1 + 0.18)` — vacancy + rate

---

## GET /api/branches

List of all branch objects. Each branch:

| Field | Type | Description |
|-------|------|-------------|
| branch_id | string | e.g. "REDWOOD" |
| branch_name | string | |
| institution_type | string | "bank" or "credit_union" |
| state_code | string | Two-letter |
| total_assets | number | USD |
| lending_capacity_q1 | number | USD |
| sector_ceiling_pct | number | Default per-sector ceiling ratio |
| cre_policy_limit_pct | number | CRE portfolio limit ratio |
| fdic_benchmark_set | string | Set name or empty for credit unions |

## GET /api/branches/{branch_id}

Same shape as a single branch entry.

---

## GET /api/branches/{branch_id}/metrics

Quarterly metrics list, most recent first. Use index 0 for current quarter.

| Field | Type |
|-------|------|
| quarter | string, e.g. "2025Q1" |
| total_loans_outstanding | number, USD |
| total_deposits | number, USD |
| nonperforming_loans | number, USD |
| delinquency_30_plus_pct | number, ratio |
| allowance_for_loan_losses | number, USD |
| net_charge_offs | number, USD |

---

## GET /api/branches/{branch_id}/loans

Full loan portfolio. Key fields:

| Field | Type | Notes |
|-------|------|-------|
| loan_id | string | |
| borrower_name | string | |
| loan_type | string | C&I, CRE, Equipment, SBA, HELOC, Consumer, Residential Mortgage |
| sector | string | |
| outstanding_balance | number | USD, use as exposure |
| current_rating | integer | 1-8, lower is better |
| payment_status | string | Current, 30 Days Past Due, 60 Days Past Due, 90+ Days Past Due, Nonaccrual |
| days_past_due | integer | |
| dscr | number or null | |
| ltv | number or null | |
| fico | integer or null | |
| debt_to_asset | number or null | |
| liquidity_months | number or null | |
| guarantor_strength | string or null | strong, standard, limited, none |
| interest_rate | number | as percentage |
| collateral_value | number or null | USD |
| annual_debt_service | number or null | USD |
| annual_review_date | string | ISO date |
| notes | string | |

---

## GET /api/branches/{branch_id}/sector-exposures

Per-sector concentration data:

| Field | Type |
|-------|------|
| sector | string |
| current_exposure | number, USD |
| limit_pct | number, ratio (sector override) |
| grandfathered | integer, 1 if existing over-ceiling exposure grandfathered |

---

## GET /api/branches/{branch_id}/applications

Pending applications. Key fields:

| Field | Type | Notes |
|-------|------|-------|
| application_id | string | |
| applicant_name | string | |
| business_name | string | |
| loan_type | string | |
| sector | string | |
| requested_amount | number | USD |
| purpose | string | |
| term_months | integer | |
| proposed_rate | number | as percentage |
| dscr | number or null | |
| ltv | number or null | |
| dti | number or null | |
| fico | integer or null | |
| collateral_value | number or null | USD |
| annual_revenue | number or null | USD |
| net_income | number or null | USD |
| total_assets | number or null | USD |
| total_debt | number or null | USD |
| years_in_business | number or null | |
| existing_relationship_years | number | |
| relationship_deposit_balance | number | USD |
| prior_delinquencies_12m | integer | |
| bankruptcy_months_ago | integer or null | |
| co_guarantor_strength | string or null | strong, standard, limited, none |
| sba_guaranty_pct | number or null | 0.0-1.0 |
| documentation_complete | integer | 1 = complete, 0 = incomplete |
| notes | string | |

---

## GET /api/benchmarks/fdic/q4-2024

| Field | Type |
|-------|------|
| benchmark_version | string |
| total_loans_noncurrent_pct | number, ratio |
| total_real_estate_noncurrent_pct | number, ratio |
| total_real_estate_30_89_pct | number, ratio |
| construction_development_noncurrent_pct | number, ratio |
| construction_development_30_89_pct | number, ratio |

Compute NPA ratio: branch `nonperforming_loans / total_loans_outstanding` from the most
recent metrics quarter. Variance: `branch_ratio - benchmark_ratio`. Variance in bps:
`variance_ratio * 10000`.

---

## GET /api/benchmarks/ncua/q1-2025

| Field | Type |
|-------|------|
| benchmark_version | string |
| rows | array of per-state records |

Each row: `state_code`, `delinquency_bps` (int), `loan_to_share_pct` (int),
`roaa_bps` (int), `positive_net_income_pct` (int). Includes a `"US"` row for national.

Peer median: median across the named peer state rows only (exclude target state and US).

---

## GET /api/credit-union-segments/{segment_id}

| Field | Type |
|-------|------|
| segment_id | string |
| segment_name | string |
| state_code | string |
| member_profile | string |
| portfolio_focus | array of strings |
| current_outstanding | number, USD |
| quarterly_capacity | number, USD |
| risk_tolerance | string: moderate, restrained, expansive |
| minimum_checklist | array of enum strings |
| peer_states | array of state codes |
| notes | string |
| internal_context | object |
| internal_context.recent_delinquency_bps | integer |
| internal_context.portfolio_yield_pct | number |
| internal_context.control_issue | string |
| internal_context.staffing_constraint | string |
