# Policy & API Reference

Re-fetch live each run; values below are the **structure** and the meaning of each field, not
a substitute for the call. Policy numbers shown are the v2025Q1 snapshot — confirm them from
`/api/policies` because future tasks may use a different policy version.

## Base URL & endpoints

Base: `http://127.0.0.1:8003`. All JSON. `branch_id`/`segment_id` matched case-insensitively.

| Endpoint | Use |
|---|---|
| `GET /api/health` | record counts / sanity check |
| `GET /api/manifest` | versions (`fdic`, `ncua`), `policy_version`, endpoint list |
| `GET /api/policies` | **authoritative thresholds** (see below) |
| `GET /api/branches` (`?institution_type=bank\|credit_union`) | branch list |
| `GET /api/branches/{id}` | one branch: `cre_policy_limit_pct`, `sector_ceiling_pct`, `lending_capacity_q1`, `fdic_benchmark_set`, `institution_type`, `state_code`, `total_assets` |
| `GET /api/branches/{id}/metrics` (`?quarter=YYYYQn`) | quarterly metrics |
| `GET /api/branches/{id}/loans` (`?loan_type=`, `?payment_status=`, `?min_current_rating=`) | loan rows |
| `GET /api/branches/{id}/sector-exposures` | sector rows: `sector`, `current_exposure`, `limit_pct`, `grandfathered` |
| `GET /api/branches/{id}/applications` (`?loan_type=`) | pending applications |
| `GET /api/benchmarks/fdic/q4-2024` | FDIC ratios |
| `GET /api/benchmarks/ncua/q1-2025` (`?state_code=XX`) | NCUA rows (`{"benchmark_version", "rows":[...]}`) |
| `GET /api/credit-union-segments/{id}` | segment detail |

### Fields that matter per surface

- **Loan**: `loan_id`, `borrower_name`, `outstanding_balance` (= exposure), `current_rating`,
  `payment_status`, `dscr`, `ltv`, `debt_to_asset`, `fico`, `liquidity_months`,
  `collateral_value`, `loan_type`, `sector`, `days_past_due`, `annual_debt_service`. Any of
  dscr/ltv/fico/etc. may be `null` — handle nulls per the rules.
- **Application**: `application_id`, `requested_amount`, `dscr`, `ltv`, `fico`,
  `total_assets`, `total_debt` (debt_to_asset = total_debt/total_assets when needed),
  `co_guarantor_strength` (strong/standard/limited/none), `sba_guaranty_pct`,
  `bankruptcy_months_ago`, `years_in_business`, `prior_delinquencies_12m`,
  `documentation_complete`, `sector`, `loan_type`, `purpose`, `collateral_value`,
  `relationship_deposit_balance`, `existing_relationship_years`, `notes` (qualitative
  mitigants — read them; they often signal the intended condition/disposition).
- **Branch metrics**: `total_loans_outstanding`, `nonperforming_loans`,
  `delinquency_30_plus_pct`, `net_charge_offs`, `allowance_for_loan_losses`,
  `total_deposits`, `quarter`. Use the `2025Q1` quarter for as-of 2025-03-31 reviews.
- **FDIC**: `total_loans_noncurrent_pct`, `total_real_estate_noncurrent_pct`,
  `total_real_estate_30_89_pct`, `construction_development_noncurrent_pct`,
  `construction_development_30_89_pct`.
- **NCUA row**: `state_code`, `delinquency_bps`, `loan_to_share_pct`, `roaa_bps`,
  `positive_net_income_pct` (integers; report verbatim). The `US` row is the national line.
- **Segment**: `state_code`, `peer_states`, `quarterly_capacity`, `current_outstanding`,
  `risk_tolerance`, `minimum_checklist`, `internal_context` (`recent_delinquency_bps`,
  `control_issue`, `staffing_constraint`, `portfolio_yield_pct`), `notes`.

## `/api/policies` structure

```
risk_rating:
  dscr_thresholds: [{min:1.5,rating:3},{min:1.25,rating:4},{min:1.05,rating:5},
                    {min:1.0,rating:6},{max_below:1.0,rating:7}]   # pick worst applicable
  ltv_thresholds:  [{max:0.65,rating:3},{max:0.75,rating:4},{max:0.85,rating:5},
                    {max:1.0,rating:6},{min_above:1.0,rating:7}]
  delinquency_minimums: {"Current":null,"30 Days Past Due":4,"60 Days Past Due":5,
                         "90+ Days Past Due":7,"Nonaccrual":8}     # rating FLOORS
  material_downgrade_notches: 2          # material if final-current >= this
  dominant_factor_rule: worst numeric rating from available DSCR/LTV/collateral + delinquency

cdfi_factor_scores:            # additive, lower better; missing factor -> 0
  fico:           {>720:0, 680-720:1, 580-679:3, <580:5}
  ltv:            {<0.40:0, 0.40-0.60:2, 0.60-0.80:4, >0.80:6}     # bands inclusive of upper
  debt_to_asset:  {<0.40:0, 0.40-0.60:2, 0.60-0.80:4, >0.80:6}
  liquidity_months:{>12:0, 6-12:1, 3-6:3, <3:5}
  classes: Prime 0-5 | Desirable 6-9 | Satisfactory 10-13 | Watch 14-18 |
           Doubtful >=19 | Projected Loss (>=19 and ltv>1.0)
           # OBSERVED: Watch-band-or-worse credit with ltv>1.0 is reported Projected Loss.

cre_weighted_score:
  weights: {capacity:0.45, collateral_exposure:0.36, conditions:0.11,
            character:0.05, capital:0.03}
  classes: approve_quality max 2.0 | conditional max 3.0 | weak min_above 3.0

stress:
  watch_list_parallel_shock: "+200bp"
  watch_list_formula:    stressed_dscr = dscr / (1 + 0.18)
  cre_dual_stress_formula: stressed_dscr = dscr * 0.85 / (1 + 0.18)
  coverage_breach_threshold: 1.0          # breach when stressed_dscr < 1.0

capacity_concentration:
  lending_capacity_field: branches.lending_capacity_q1
  single_sector_default_field: branches.sector_ceiling_pct  # sector rows override via limit_pct
  branch_sector_override_table: sector_exposures
  allowed_mitigations: [participation_required, reduced_amount, board_exception]
  grandfathering_note: existing over-ceiling exposure may be grandfathered, but new
                       approvals may not worsen that sector without mitigation.
```

## Band-edge conventions (verified against standard answers)

- DSCR thresholds use `>=` on `min` (1.50 → rating 3; exactly 1.25 → rating 4; below 1.0 → 7).
- LTV thresholds use `<=` on `max` (0.65 → 3; 0.85 → 5; exactly 1.0 → 6; >1.0 → 7).
- CDFI band labels: "0.40-0.60" means `0.40 <= x <= 0.60` (upper inclusive); ">0.80" is the
  worst band. FICO ">720" is strict; "680-720" is `680 <= f <= 720`.
- Delinquency floors are minimums: the final rating is at least the floor but can be higher if
  DSCR/LTV is worse.
- `variance_bps` always from unrounded ratio difference × 10000, then round 2 dp.
