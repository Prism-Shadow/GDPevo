# Policy Rules Reference

This document captures the static credit policy rules used across all five committee workflows. The live policy is also available at `/api/policies` and should be read once per task for the specific benchmark versions.

## Risk Rating Re-derivation

### Dominant Factor Rule

Take the **worst** (highest numeric) rating from all available factors:

```
final_rating = max(dscr_rating, ltv_rating, delinquency_rating)
```

Skip any factor whose input data is null.

### DSCR Thresholds

| DSCR Range      | Rating |
|-----------------|--------|
| DSCR >= 1.50    | 3      |
| 1.25 <= DSCR < 1.50 | 4 |
| 1.05 <= DSCR < 1.25 | 5 |
| 1.00 <= DSCR < 1.05 | 6 |
| DSCR < 1.00     | 7      |

### LTV Thresholds

| LTV Range       | Rating |
|-----------------|--------|
| LTV <= 0.65     | 3      |
| 0.65 < LTV <= 0.75 | 4  |
| 0.75 < LTV <= 0.85 | 5  |
| 0.85 < LTV <= 1.00 | 6  |
| LTV > 1.00      | 7      |

### Delinquency Minimums

| Payment Status        | Rating Floor |
|-----------------------|-------------|
| Current               | (none)      |
| 30 Days Past Due      | 4           |
| 60 Days Past Due      | 5           |
| 90+ Days Past Due     | 7           |
| Nonaccrual            | 8           |

### Material Downgrade Threshold

A downgrade is **material** when `final_rating - current_rating >= 2`.

## CDFI Factor Scoring

Used for watch-list risk classification. Sum points from available factors.

### FICO

| Range   | Score |
|---------|-------|
| >720    | 0     |
| 680-720 | 1     |
| 580-679 | 3     |
| <580    | 5     |

### LTV

| Range   | Score |
|---------|-------|
| <0.40   | 0     |
| 0.40-0.60 | 2   |
| 0.60-0.80 | 4   |
| >0.80   | 6     |

### Debt-to-Asset

| Range   | Score |
|---------|-------|
| <0.40   | 0     |
| 0.40-0.60 | 2   |
| 0.60-0.80 | 4   |
| >0.80   | 6     |

### Liquidity Months

| Range   | Score |
|---------|-------|
| >12     | 0     |
| 6-12    | 1     |
| 3-6     | 3     |
| <3      | 5     |

### Risk Classes from Total Score

| Class           | Score Range     |
|-----------------|-----------------|
| Prime           | 0-5             |
| Desirable       | 6-9             |
| Satisfactory    | 10-13           |
| Watch           | 14-18           |
| Doubtful        | >=19            |
| Projected Loss  | >=19 and LTV > 1.0 |

"Projected Loss" overrides "Doubtful" when both conditions hold.

## CRE Weighted Score

Used for competing CRE decisions. Each of five factors is scored (0-5 from CDFI table or DSCR mapping), then multiplied by its weight.

### Weights

| Factor             | Weight |
|--------------------|--------|
| capacity (DSCR)    | 0.45   |
| capital (D/A)      | 0.03   |
| character (FICO)   | 0.05   |
| collateral (LTV)   | 0.36   |
| conditions (Liq)   | 0.11   |

### DSCR-to-points Mapping

Map the DSCR-based rating to points: rating 3→1, 4→2, 5→3, 6→4, 7→5.

When a factor is null, score it as 3 (neutral).

### Score Classes

| Class            | Threshold |
|------------------|-----------|
| approve_quality  | <= 2.0    |
| conditional      | <= 3.0    |
| weak             | > 3.0     |

## Stress Formulas

### Watch-List DSCR Stress (+200bp)

```
stressed_dscr = dscr / 1.18
```

Breach threshold: 1.0 (breaches if stressed_dscr < 1.0).

### CRE Dual Stress

```
stressed_dscr = dscr * 0.85 / 1.18
```

Breach threshold: 1.0 (breaches if stressed_dscr < 1.0).

## Concentration and Capacity

### Sector Concentration

- Each sector has a `limit_pct` from `/api/branches/{branch_id}/sector-exposures`.
- The branch-level default is `sector_ceiling_pct` on the branch record.
- Sectors with `grandfathered > 0` may exceed limits, but new approvals must not worsen the breach.
- Post-approval ratio = (current_sector_exposure + approved_amount) / total_loans_outstanding.

### CRE Policy Limit

- `cre_policy_limit_pct` on the branch record governs CRE-governed sectors (sectors whose limit_pct equals cre_policy_limit_pct).
- Existing CRE exposure = sum of outstanding_balance for loans with `loan_type == "CRE"` plus exposure in CRE-governed sectors.

### Capacity Consumption

- Default: bank_capacity_used = approved_amount
- `participation_required`: bank_capacity_used = approved_amount * 0.75
- `sba_guaranty_required`: bank_capacity_used = approved_amount * 0.25

## Benchmark Versions

- FDIC: `fdic_q4_2024` (verify from `/api/manifest`)
- NCUA: `ncua_q1_2025` (verify from `/api/manifest`)

FDIC benchmark fields:
- `total_loans_noncurrent_pct` — for general NPA comparisons
- `total_real_estate_noncurrent_pct` — CRE noncurrent
- `total_real_estate_30_89_pct` — CRE 30-89 day delinquency (used for competing CRE)
- `construction_development_noncurrent_pct`, `construction_development_30_89_pct`

NCUA benchmark fields per state row:
- `delinquency_bps`
- `loan_to_share_pct`
- `roaa_bps`
- `positive_net_income_pct`

## Watch-List Actions

| Action                   | When                                                    |
|--------------------------|---------------------------------------------------------|
| partial_chargeoff_review | Rating 8 (Nonaccrual) or Projected Loss + Nonaccrual    |
| special_assets           | Rating 7, or 90+ Days / Nonaccrual, or Projected Loss   |
| workout                  | (available, use when moderate stress + deterioration)   |
| watchlist                | Rating 6, or stress breach without severe delinquency   |
| monitor                  | Ratings 3-5, no breach                                  |
| legal_referral           | (available for worst cases, not observed in train data) |

## Decline and Condition Enums

**Decline reason codes**: capacity_limit, sector_breach, weak_dscr, high_ltv, low_fico, recent_bankruptcy, startup_risk, underwater_collateral, policy_floor_missing, documentation_gap, fdic_adverse_variance, ncua_peer_weakness

**Decision enums**: approve, conditional_approve, decline, defer, participation_required

**Conditions for applications**: participation_required, reduced_amount, board_exception, sba_guaranty_required, startup_monitoring, none

**Conditions for CRE decisions**: bank_retained_exposure_cap, committee_cre_exception, updated_appraisal_before_close, tenant_roll_and_lease_review, minimum_dscr_covenant_1_25, quarterly_financial_reporting, no_additional_cre_without_committee_review

**Posture enums**: continue_approving, continue_with_tighter_conditions, temporarily_pause

**Escalation condition enums**: segment_recent_delinquency_ge_90_bps, missing_insurance_or_lien_exception, quarterly_capacity_exceeded_or_exception_requested, state_delinquency_gap_widens_25_bps

**Escalation owners**: credit_risk_manager, operations_control_manager, lending_committee_chair

**Interpretation capacity**: capacity_available, capacity_constrained, no_capacity

**Interpretation external risk**: stronger_than_national_and_peers, mixed_vs_national_and_peers, weaker_than_national_and_peers

**Interpretation risk_tolerance**: restrained, moderate, expansive

**Interpretation committee_message**: capacity_available_but_external_risk_weaker, pause_until_state_metrics_recover, routine_approval_path_supported

**Segment controls (checklist gates)**: board_authorization, equipment_invoice, fleet_replacement_plan, payer_contract_summary, public_contract_or_tax_support, proof_of_insurance, ucc_or_title_lien

**Segment added controls**: pre_close_insurance_binder_verification, lien_perfection_prior_to_funding, senior_underwriter_second_review, quarterly_state_benchmark_monitoring, monthly_segment_delinquency_watch, committee_exception_for_capacity_overrun
