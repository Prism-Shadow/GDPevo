# Credit Methodology Reference

All thresholds, formulas, and rules derive from . Always fetch policies
first before performing any analysis, since policy values are authoritative.

## Risk Rating Re-derivation

Used to reassign loan ratings from objective factor data. Apply the dominant-factor rule:
final rating = worst (highest numeric) rating from available DSCR, LTV/collateral, and
delinquency-floor factors.

### Step 1: DSCR-derived rating

| Condition | Rating |
|-----------|--------|
| DSCR >= 1.50 | 3 |
| DSCR >= 1.25 | 4 |
| DSCR >= 1.05 | 5 |
| DSCR >= 1.00 | 6 |
| DSCR < 1.00  | 7 |
| DSCR is null | skip factor |

### Step 2: LTV/collateral-derived rating

| Condition | Rating |
|-----------|--------|
| LTV <= 0.65 | 3 |
| LTV <= 0.75 | 4 |
| LTV <= 0.85 | 5 |
| LTV <= 1.00 | 6 |
| LTV > 1.00  | 7 |
| LTV is null | skip factor |

### Step 3: Delinquency floor

| Payment Status | Floor Rating |
|----------------|-------------|
| Current | none |
| 30 Days Past Due | 4 |
| 60 Days Past Due | 5 |
| 90+ Days Past Due | 7 |
| Nonaccrual | 8 |

### Step 4: Combine

final_rating = max(DSCR_rating, LTV_rating, delinquency_floor, 1).
Skip factors where the input value is null.

### Material downgrades

A downgrade is material when final_rating - current_rating >= 2.

## Watch-List and Workout Action Assignment

Assign actions by risk severity:

| Condition | Action |
|-----------|--------|
| Nonaccrual with ltv > 1.0 | partial_chargeoff_review |
| Nonaccrual, ltv <= 1.0 | special_assets |
| final_rating >= 7 | special_assets |
| final_rating == 6 | watchlist |
| final_rating <= 5, downgraded >= 2 notches | watchlist |
| final_rating <= 5, downgraded < 2 notches | monitor |

For 90+ Days Past Due loans not yet Nonaccrual, prefer special_assets.

## Watch-List DSCR Stress (+200bp)

Formula from policies: stressed_dscr = dscr / 1.18

This is equivalent to a 200 basis point parallel rate shock.

Apply only to loans where dscr is available (non-null). The breach threshold is 1.0:
a loan breaches if stressed_dscr < 1.0.

## CRE Dual Stress

Formula: stressed_dscr = dscr * 0.85 / 1.18

The 0.85 factor represents a 15% vacancy/income reduction. The 1.18 denominator
represents the +200bp rate shock combined with the income stress.

Breach threshold is also 1.0.

## CDFI Factor Scoring

Score each available factor from the policy lookup tables. Sum scores across factors.
Skip factors where the value is null. Classify by total score:

| Class | Score Range |
|-------|------------|
| Prime | 0-5 |
| Desirable | 6-9 |
| Satisfactory | 10-13 |
| Watch | 14-18 |
| Doubtful | >=19 |
| Projected Loss | >=19 and ltv > 1.0 |

Factor scoring tables (from policies):

**FICO**: >720→0, 680-720→1, 580-679→3, <580→5

**Debt-to-Asset**: <0.40→0, 0.40-0.60→2, 0.60-0.80→4, >0.80→6

**Liquidity Months**: >12→0, 6-12→1, 3-6→3, <3→5

**LTV**: <0.40→0, 0.40-0.60→2, 0.60-0.80→4, >0.80→6

## CRE Weighted Score

From policies: five sub-scores (1-5 each, lower is better), weighted sum:

weighted = 0.45 * capacity + 0.03 * capital + 0.05 * character
         + 0.36 * collateral_exposure + 0.11 * conditions

Sub-score derivation is judgment-based using available application and branch data:
- **capacity** (0.45): consider lending_capacity_q1 remaining after existing commitments,
  requested amount relative to capacity
- **capital** (0.03): consider guarantor strength, net income, total_assets vs total_debt
- **character** (0.05): consider years_in_business, existing_relationship_years,
  prior_delinquencies_12m, bankruptcy history
- **collateral_exposure** (0.36): consider ltv, collateral_value vs requested_amount
- **conditions** (0.11): consider loan_type matchup to purpose, term alignment, sector risk

Classification: approve_quality (<= 2.0), conditional (<= 3.0), weak (> 3.0).

## Sector Concentration

For a branch-sector pair, the effective limit is the per-sector limit_pct from the
sector-exposures endpoint if present, otherwise the branch sector_ceiling_pct.

Post-approval concentration = (current_exposure + approved_amount) / total_loans_outstanding.

If post-approval exceeds the limit and the sector is not grandfathered, a concentration
flag is raised. Mitigations: participation_required, reduced_amount, board_exception.

Existing grandfathered sectors may remain over-ceiling but new approvals must not worsen
that sector without mitigation.

## FDIC Benchmark Comparison

From /api/benchmarks/fdic/q4-2024, pick the metric relevant to the task (e.g.
total_loans_noncurrent_pct for NPA, total_real_estate_30_89_pct for CRE delinquency).

Branch ratio: compute from branch metrics endpoint using the most recent quarter.
- NPA ratio: nonperforming_loans / total_loans_outstanding
- Delinquency ratio for CRE: use delinquency_30_plus_pct from metrics.

Variance: branch_ratio - benchmark_ratio. Variance in bps: variance_ratio * 10000.

## NCUA State Benchmark Comparison

From /api/benchmarks/ncua/q1-2025, extract the target state row, the US row, and
the named peer state rows from the segment.

Compare NC vs US direction, and NC vs peer median direction, on four metrics:
- delinquency_bps
- loan_to_share_pct
- roaa_bps
- positive_net_income_pct

Direction: "higher", "lower", or "equal" (equal when values match exactly).

Peer median: sort the peer state values and take the middle. For an even number of
peers, take the average of the two middle values.

## Credit Union Segment Posture

Posture choices: "continue_approving", "continue_with_tighter_conditions", "temporarily_pause".

Derive from:
- capacity_status: compare quarterly_capacity to current_outstanding. If capacity is
  well above outstanding -> capacity_available. If tight -> capacity_constrained.
- external_risk_status: from NCUA comparison. If NC is worse than both US and peers on
  most metrics -> weaker_than_national_and_peers.
- risk_tolerance: from the segment object directly, or moderate if mixed signals.

Committee message is an enum from the answer templates: "capacity_available_but_external_risk_weaker",
"pause_until_state_metrics_recover", "routine_approval_path_supported".

## Allocation and Priority Ranking

For allocation tasks:
1. Compute lending_capacity_q1 from the branch object.
2. Screen applications: decline applications with clear fatal issues (high_ltv, weak_dscr,
   low_fico, recent_bankruptcy, startup_risk with no SBA, documentation_gap).
3. Rank remaining applications by priority: stronger DSCR, longer relationship,
   lower LTV, larger deposit relationship all suggest higher priority.
4. Allocate capacity in priority order. For applications near a sector ceiling, flag
   and apply mitigation (participation_required, sba_guaranty_required).
5. committed_capacity_amount: for conditionally approved applications, only count the
   bank-retained portion (e.g., for SBA 75% guaranty, bank retains 25% of approved amount;
   for participation, count only the retained share).
6. remaining_capacity = lending_capacity_q1 - committed_capacity_amount.
