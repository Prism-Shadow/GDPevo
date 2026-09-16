# Credit Policy Reference v2025Q1

Complete policy rules from `GET /api/policies`. This document supplements SKILL.md with the full lookup tables and edge-case handling.

## Risk Rating Thresholds

### DSCR-to-Rating Map

| DSCR range | Rating |
|---|---|
| >= 1.50 | 3 |
| >= 1.25 | 4 |
| >= 1.05 | 5 |
| >= 1.00 | 6 |
| < 1.00 | 7 |

### LTV-to-Rating Map

| LTV range | Rating |
|---|---|
| <= 0.65 | 3 |
| <= 0.75 | 4 |
| <= 0.85 | 5 |
| <= 1.00 | 6 |
| > 1.00 | 7 |

### Delinquency Minimums

| Payment Status | Minimum Rating |
|---|---|
| Current | (no factor) |
| 30 Days Past Due | 4 |
| 60 Days Past Due | 5 |
| 90+ Days Past Due | 7 |
| Nonaccrual | 8 |

**Dominant-factor rule**: Final rating = max(DSCR rating, LTV rating, delinquency minimum), using only factors with non-null inputs.

### Material Downgrade Threshold

A downgrade is material when `final_rating - current_rating >= 2` (2 notches or more).

## CDFI Factor Score Tables

Each factor returns a score of 0, 1, 3, or 5.

### FICO

| Range | Score |
|---|---|
| > 720 | 0 |
| 680-720 | 1 |
| 580-679 | 3 |
| < 580 | 5 |

### LTV

| Range | Score |
|---|---|
| < 0.40 | 0 |
| 0.40-0.60 | 2 |
| 0.60-0.80 | 4 |
| > 0.80 | 6 |

### Debt-to-Asset

| Range | Score |
|---|---|
| < 0.40 | 0 |
| 0.40-0.60 | 2 |
| 0.60-0.80 | 4 |
| > 0.80 | 6 |

### Liquidity Months

| Range | Score |
|---|---|
| > 12 | 0 |
| 6-12 | 1 |
| 3-6 | 3 |
| < 3 | 5 |

### Risk Class Buckets

| Total Score | Class |
|---|---|
| 0-5 | Prime |
| 6-9 | Desirable |
| 10-13 | Satisfactory |
| 14-18 | Watch |
| >= 19 | Doubtful |
| >= 19 and ltv > 1.0 | Projected Loss |

**Edge case**: When a factor is null, score that factor as 0 (neutral). Projected Loss requires both total >= 19 AND ltv > 1.0. Doubtful otherwise for total >= 19.

## CRE Weighted Scoring

Formula: `weighted_score = 0.45*c + 0.03*k + 0.05*h + 0.36*e + 0.11*n`

Where each component is an integer 1-5. Lower is better.

### Score Classes

| Range | Class |
|---|---|
| <= 2.0 | approve_quality |
| <= 3.0 | conditional |
| > 3.0 | weak |

### Component Guidance

- **capacity (c)**: DSCR strength. 1 = strongest, 5 = weakest. Map DSCR: >=1.50->1, >=1.25->2, >=1.05->3, >=1.00->4, <1.00->5.
- **capital (k)**: Leverage. debt_to_asset or ltv quality. 1 = low leverage, 5 = high leverage.
- **character (h)**: FICO, years_in_business, prior_delinquencies, bankruptcy history. 1 = strong, 5 = weak.
- **collateral_exposure (e)**: Collateral coverage and LTV. 1 = well-secured, 5 = underwater.
- **conditions (n)**: Loan purpose, term, industry/collateral type risk. 1 = favorable, 5 = adverse.

When data is missing for a component, estimate conservatively (score 3-4) based on available indicators.

## Stress Formulas

### Watch-List +200bp Parallel Shock

```
stressed_dscr = dscr / (1 + 0.18) = dscr / 1.18
```

Breach defined as `stressed_dscr < 1.0`.

### CRE Dual-Stress

```
stressed_dscr = dscr * 0.85 / (1 + 0.18) = dscr * 0.85 / 1.18
```

Breach defined as `stressed_dscr < 1.0`.

### Coverage Breach Threshold

Always 1.0 for both stress models.

## Concentration Rules

### Sector Concentration

Each sector has a `limit_pct` from `GET /api/branches/{branch_id}/sector-exposures`.
- `post_approval_pct = (current_exposure + approved_amount) / total_loans_outstanding`
- Flag when `post_approval_pct > limit_pct`.

### Grandfathering

Sectors with `grandfathered = 1` may currently exceed their limit. New approvals may not worsen the overage without mitigation. Allowed mitigations: `participation_required`, `reduced_amount`, `board_exception`.

### General Sector Ceiling

Branch has `sector_ceiling_pct` for non-CRE sectors. CRE-specific uses `cre_policy_limit_pct`. When a sector has no explicit entry in sector-exposures, use `sector_ceiling_pct` as the default limit.

### Variance in Basis Points

`variance_bps = (actual_ratio - limit_ratio) * 10000`

## FDIC Benchmark Metrics

From `GET /api/benchmarks/fdic/q4-2024`:

- `total_loans_noncurrent_pct` — nonperforming loans / total loans
- `total_real_estate_noncurrent_pct` — NPA for total real estate
- `total_real_estate_30_89_pct` — 30-89 day delinquency for real estate
- `construction_development_noncurrent_pct`
- `construction_development_30_89_pct`

## NCUA Benchmark Metrics

From `GET /api/benchmarks/ncua/q1-2025` (per state):

- `delinquency_bps` — delinquency in basis points
- `loan_to_share_pct` — loans / shares ratio
- `roaa_bps` — return on average assets in bps
- `positive_net_income_pct` — percent of CUs with positive net income
- US national row has `state_code: "US"`

### Comparison Direction

- delinquency_bps: higher = weaker
- loan_to_share_pct: higher = more leveraged
- roaa_bps: higher = stronger
- positive_net_income_pct: higher = stronger

## Lending Capacity

- `lending_capacity_q1` from branch detail. This is the gross quarterly allocation.
- `committed_capacity_amount` = sum of approved_amount values (full request for approve; partial for conditional/participation).
- For `participation_required`, bank capacity used is the retained portion (e.g., `approved_amount * (1 - participation_share)`).
- `remaining_capacity = lending_capacity_q1 - committed_capacity_amount`.

## Decision and Condition Enums

### Application Decisions

`approve`, `conditional_approve`, `decline`, `defer`, `participation_required`

### Conditions

`participation_required`, `reduced_amount`, `board_exception`, `sba_guaranty_required`, `startup_monitoring`, `none`

### Decline Reason Codes

`capacity_limit`, `sector_breach`, `weak_dscr`, `high_ltv`, `low_fico`, `recent_bankruptcy`, `startup_risk`, `underwater_collateral`, `policy_floor_missing`, `documentation_gap`, `fdic_adverse_variance`, `ncua_peer_weakness`

### Watch-List Actions

`monitor`, `watchlist`, `special_assets`, `workout`, `partial_chargeoff_review`, `legal_referral`

### CRE Conditions (for competing decisions)

`bank_retained_exposure_cap`, `committee_cre_exception`, `updated_appraisal_before_close`, `tenant_roll_and_lease_review`, `minimum_dscr_covenant_1_25`, `quarterly_financial_reporting`, `no_additional_cre_without_committee_review`

## Action Assignment Heuristics

Use these mappings when assigning watch-list or workout actions:

- final_rating 6, payment_status Current, no stress breach -> `watchlist`
- final_rating 6, payment_status Current, stress breach -> `watchlist`
- final_rating 7, payment_status Current -> `special_assets`
- final_rating 7, payment_status 90+ Days -> `special_assets`
- final_rating 8 (Nonaccrual) -> `partial_chargeoff_review`
- Any nonaccrual regardless of rating -> at least `special_assets`
- Any loan with stressed_dscr < 1.0 and final_rating >= 7 -> `special_assets` or stronger
