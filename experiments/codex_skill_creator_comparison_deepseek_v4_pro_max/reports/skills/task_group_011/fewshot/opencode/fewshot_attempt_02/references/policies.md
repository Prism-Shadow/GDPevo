# Policy Rules Reference

Reproduced from the credit office API policies endpoint for quick lookup.
Always cross-reference with the live API response; this document is a
snapshot for computation convenience.

## Risk Rating Rules

Final re-derived rating is the **worst (highest numeric) rating** from the
available DSCR, LTV/collateral, and delinquency factors. If a factor is
unavailable (null/missing), skip it.

### DSCR Thresholds

| DSCR range       | Rating |
|------------------|--------|
| >= 1.50          | 3      |
| >= 1.25          | 4      |
| >= 1.05          | 5      |
| >= 1.00          | 6      |
| < 1.00 (or null) | 7      |

### LTV Thresholds

| LTV range       | Rating |
|------------------|--------|
| <= 0.65          | 3      |
| <= 0.75          | 4      |
| <= 0.85          | 5      |
| <= 1.00          | 6      |
| > 1.00 (or null) | 7      |

### Delinquency Minimums

| Payment Status      | Minimum Rating |
|---------------------|----------------|
| Current             | (no floor)     |
| 30 Days Past Due    | 4              |
| 60 Days Past Due    | 5              |
| 90+ Days Past Due   | 7              |
| Nonaccrual          | 8              |

### Material Downgrade Threshold

A downgrade is material when final_rating minus current_rating >= 2.

## CDFI Factor Scores

Sum individual contributions from fico, liquidity_months, ltv, and
debt_to_asset. Map total to a risk class.

### FICO Score

| FICO Range | Score |
|------------|-------|
| > 720      | 0     |
| 680 - 720  | 1     |
| 580 - 679  | 3     |
| < 580      | 5     |
| null       | 3     |

### Liquidity Months

| Range  | Score |
|--------|-------|
| > 12   | 0     |
| 6 - 12 | 1     |
| 3 - 6  | 3     |
| < 3    | 5     |
| null   | 3     |

### LTV (CDFI)

| Range   | Score |
|---------|-------|
| < 0.40  | 0     |
| 0.40 - 0.60 | 2 |
| 0.60 - 0.80 | 4 |
| > 0.80  | 6     |
| null    | 4     |

### Debt-to-Asset

| Range   | Score |
|---------|-------|
| < 0.40  | 0     |
| 0.40 - 0.60 | 2 |
| 0.60 - 0.80 | 4 |
| > 0.80  | 6     |
| null    | 2     |

### Risk Class Mapping

| Total Score | Risk Class     |
|-------------|----------------|
| 0 - 5       | Prime          |
| 6 - 9       | Desirable      |
| 10 - 13     | Satisfactory   |
| 14 - 18     | Watch          |
| >= 19, ltv <= 1.0 | Doubtful |
| >= 19, ltv > 1.0  | Projected Loss |

**Override rule**: if payment_status is Nonaccrual, risk class is always
Projected Loss regardless of factor score.

## CRE Weighted Score

Used for competing CRE decisions. Five dimensions, each scored from 0 (best)
to 5 (worst) using factor tables, then weighted and summed.

### Weights

| Dimension           | Weight |
|---------------------|--------|
| Capacity            | 0.45   |
| Capital             | 0.03   |
| Character           | 0.05   |
| Collateral/Exposure | 0.36   |
| Conditions          | 0.11   |

Weighted score = sum(dimension_score * weight). Lower is better.

### Score Class Mapping

| Weighted Score | Class            |
|----------------|------------------|
| <= 2.0         | approve_quality  |
| 2.1 - 3.0      | conditional      |
| > 3.0          | weak             |

### Dimension Scoring Guidelines

Score each dimension from 0 (strongest) to 5 (weakest) using available
application data. Apply these mappings:

**Capacity** (based on DSCR and net_income):
- DSCR >= 1.50 -> 0
- DSCR >= 1.25 -> 1
- DSCR >= 1.05 -> 3
- DSCR >= 1.00 -> 4
- DSCR < 1.00 or null -> 5

**Capital** (based on LTV and applicant leverage):
- LTV <= 0.65 -> 0
- LTV <= 0.75 -> 1
- LTV <= 0.85 -> 3
- LTV <= 1.00 -> 4
- LTV > 1.00 or null -> 5

**Character** (based on FICO and prior delinquencies):
- FICO > 720 and no prior delinquencies -> 0
- FICO 680-720 -> 1
- FICO 580-679 -> 3
- FICO < 580 or prior delinquencies -> 4
- FICO null or bankruptcy -> 5

**Collateral/Exposure** (based on LTV and sector risk):
- LTV <= 0.60 -> 0
- LTV <= 0.75 -> 1
- LTV <= 0.85 -> 3
- LTV <= 1.00 -> 4
- LTV > 1.00 -> 5

**Conditions** (based on documentation completeness, purpose, and term):
- Documentation complete, standard purpose -> 0
- Documentation complete, non-standard purpose -> 2
- Documentation incomplete -> 4
- Documentation incomplete AND long term (>60 months) -> 5

## Stress Formulas

### +200bp DSCR Stress (Watch List)

stressed_dscr = dscr / 1.18

Breach threshold: stressed_dscr < 1.0.

### CRE Dual-Factor Stress (Competing Decision)

stressed_dscr = dscr * 0.85 / 1.18

Breach threshold: stressed_dscr < 1.0.

This models simultaneous rate shock (+200bp) and revenue decline (-15%).

## Concentration and Capacity Rules

### Sector Concentration

For each sector, limit_pct comes from the sector-exposures endpoint.
concentration = (total sector exposure + new approval amount) /
total_loans_outstanding.

When post_approval_pct > limit_pct:
- An existing application must be flagged.
- Mitigation options: participation_required, reduced_amount, board_exception.
- Grandfathered exposure does not trigger new flags but existing over-ceiling
exposure may not be worsened.

### Lending Capacity

- lending_capacity_q1 from branch details is the total quarterly budget.
- bank_capacity_used for participation_required: only the bank's retained
  portion counts (approved_amount minus participation share).
- For SBA-guaranteed loans: bank_capacity_used = approved_amount *
  (1 - sba_guaranty_pct).
- remaining_capacity = lending_capacity_q1 - committed_capacity_amount.

## NCUA Benchmark Metrics

The NCUA benchmark table contains per-state rows with:
delinquency_bps, loan_to_share_pct, roaa_bps, positive_net_income_pct.

The US row provides national aggregates.

Peer median: for each metric, collect values from the listed peer_states,
sort, and take the middle value. For an even number of peer states, average
the two middle values and round to the nearest integer.

Direction comparison: "higher" when NC > comparison, "lower" when
NC < comparison, "equal" when identical.

## CU Posture Decision Matrix

| External Risk vs National | External Risk vs Peers | Internal Delinquency | Risk Tolerance | Posture |
|---------------------------|------------------------|---------------------|----------------|---------|
| stronger                  | stronger               | < 90 bps           | expansive      | continue_approving |
| stronger                  | mixed                  | < 90 bps           | moderate       | continue_approving |
| mixed                     | mixed                  | < 90 bps           | moderate       | continue_with_tighter_conditions |
| weaker                    | weaker                 | < 90 bps           | moderate       | continue_with_tighter_conditions |
| weaker                    | weaker                 | >= 90 bps          | restrained     | temporarily_pause |
| any                       | any                    | >= 90 bps          | any            | temporarily_pause |

## FDIC Benchmarks

From the fdic_q4_2024 dataset (fetch live; values listed here are the
reference snapshot):

| Metric                              | Value  |
|-------------------------------------|--------|
| total_loans_noncurrent_pct          | 0.0098 |
| total_real_estate_noncurrent_pct    | 0.0121 |
| total_real_estate_30_89_pct         | 0.0051 |
| construction_development_30_89_pct  | 0.0042 |
| construction_development_noncurrent_pct | 0.0076 |
