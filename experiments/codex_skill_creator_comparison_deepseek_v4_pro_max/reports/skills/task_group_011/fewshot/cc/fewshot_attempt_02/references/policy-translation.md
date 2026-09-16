# Policy Translation Reference

This document translates the policy JSON structure into concrete decision
tables. When you fetch `/api/policies`, read this side-by-side to make sure
you apply rules correctly.

## Risk Rating Tables

### DSCR -> Rating

| DSCR range | Rating |
|------------|--------|
| >= 1.50   | 3      |
| 1.25 to < 1.50 | 4 |
| 1.05 to < 1.25 | 5 |
| 1.00 to < 1.05 | 6 |
| < 1.00    | 7      |

If DSCR is null, skip this factor (contributes 0).

### LTV -> Rating

| LTV range | Rating |
|-----------|--------|
| <= 0.65   | 3      |
| 0.65 to <= 0.75 | 4 |
| 0.75 to <= 0.85 | 5 |
| 0.85 to <= 1.00 | 6 |
| > 1.00    | 7      |

If LTV is null, skip this factor (contributes 0).

### Delinquency Minimum Rating

| Payment Status      | Minimum Rating |
|---------------------|----------------|
| Current             | (none, skip)   |
| 30 Days Past Due    | 4              |
| 60 Days Past Due    | 5              |
| 90+ Days Past Due   | 7              |
| Nonaccrual          | 8              |

### Dominant-Factor Rule

```
final_rating = max(dscr_rating or 0, ltv_rating or 0, delinquency_floor or 0)
```

If all three factors are null for a loan, keep its `current_rating` unchanged.

### Material Downgrade Threshold

A downgrade is "material" when `final_rating - current_rating >= 2`.

## CDFI Factor Score Tables

### FICO Scoring

| FICO range | Score |
|------------|-------|
| > 720      | 0     |
| 680-720    | 1     |
| 580-679    | 3     |
| < 580      | 5     |
| null       | 0     |

### LTV Scoring

| LTV range  | Score |
|------------|-------|
| < 0.40     | 0     |
| 0.40-0.60  | 2     |
| 0.60-0.80  | 4     |
| > 0.80     | 6     |
| null       | 0     |

### Debt-to-Asset Scoring

| D/A range  | Score |
|------------|-------|
| < 0.40     | 0     |
| 0.40-0.60  | 2     |
| 0.60-0.80  | 4     |
| > 0.80     | 6     |
| null       | 0     |

### Liquidity Months Scoring

| Liquidity range | Score |
|-----------------|-------|
| > 12            | 0     |
| 6-12            | 1     |
| 3-6             | 3     |
| < 3             | 5     |
| null            | 0     |

### Risk Class Assignment

| Total Score | Risk Class     | Special Condition           |
|-------------|----------------|-----------------------------|
| 0-5         | Prime          |                             |
| 6-9         | Desirable      |                             |
| 10-13       | Satisfactory   |                             |
| 14-18       | Watch          |                             |
| >= 19       | Doubtful       | if ltv <= 1.0               |
| >= 19       | Projected Loss | if ltv > 1.0                |

## Stress Formulas

### Watch-List DSCR Stress (+200bp)

```
stressed_dscr = base_dscr / 1.18
breaches_threshold = stressed_dscr < 1.0
```

The shock label is `"+200bp"`. The breach threshold is `1.0`.

### CRE Dual Stress

```
stressed_dscr = base_dscr * 0.85 / 1.18
breaches_threshold = stressed_dscr < 1.0
```

The formula string is `"dscr * 0.85 / 1.18"`. The breach threshold is `1.0`.

## CRE Weighted Score Components

Five factors, each scored 0 (satisfactory) or 1 (unsatisfactory):

| Factor             | Weight | Unsatisfactory (1) when        |
|--------------------|--------|--------------------------------|
| capacity           | 0.45   | dscr < 1.25                    |
| collateral_exposure| 0.36   | ltv > 0.80                     |
| conditions         | 0.11   | loan_type is not "CRE"         |
| character          | 0.05   | fico < 680 (0 if fico null)    |
| capital            | 0.03   | debt_to_asset > 0.60 (0 if null) |

Weighted score = sum(product of each factor).

### Score Classes

| Score range | Class            |
|-------------|------------------|
| <= 2.0      | approve_quality  |
| <= 3.0      | conditional      |
| > 3.0       | weak             |

## Concentration Rules

- **Branch default**: `branches.sector_ceiling_pct` applies to all sectors that lack a per-sector override.
- **Per-sector override**: `sector-exposures.limit_pct` overrides the branch default for that specific sector.
- **CRE ceiling**: `branches.cre_policy_limit_pct` is a separate cap on total CRE exposure.
- **Grandfathering**: `sector-exposures.grandfathered` indicates existing over-ceiling exposure. Do not worsen a grandfathered sector without `participation_required`, `reduced_amount`, or `board_exception` mitigation.
- **Post-approval pct**: `(existing_exposure + approved_amounts_in_sector) / total_loans_outstanding`

## FDIC Benchmark Fields

From `GET /api/benchmarks/fdic/q4-2024`:

| Field                                    | Meaning                                    |
|------------------------------------------|--------------------------------------------|
| `total_loans_noncurrent_pct`             | All loans 90+ DPD or nonaccrual / total    |
| `total_real_estate_noncurrent_pct`       | RE loans noncurrent / total RE loans       |
| `total_real_estate_30_89_pct`            | RE loans 30-89 DPD / total RE loans        |
| `construction_development_noncurrent_pct`| C&D loans noncurrent / total C&D           |
| `construction_development_30_89_pct`     | C&D loans 30-89 DPD / total C&D            |

`benchmark_version` is `"fdic_q4_2024"`.

## NCUA Benchmark Structure

From `GET /api/benchmarks/ncua/q1-2025`:

Each row contains `state_code`, `delinquency_bps`, `loan_to_share_pct`, `roaa_bps`, and `positive_net_income_pct`. The row with `state_code == "US"` is the national aggregate.

`benchmark_version` is `"ncua_q1_2025"`.

## Credit Union Segment Fields

From `GET /api/credit-union-segments/{segment_id}`:

- `segment_id`, `segment_name`, `state_code`: identifiers
- `member_profile`, `portfolio_focus`: descriptive
- `quarterly_capacity`: dollar amount available for the segment
- `risk_tolerance`: "restrained", "moderate", or "expansive"
- `peer_states`: list of state codes for peer comparison
- `minimum_checklist`: required closing gates
- `notes`: qualitative guidance
- `internal_context`: staffing constraints, control issues, recent delinquency, portfolio yield
