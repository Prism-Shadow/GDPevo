# Risk Rating Guide

The shared credit office uses an 8-point internal risk rating scale. Rating 1
is the strongest (minimal risk) and rating 8 represents loss.

## The 8-Point Scale

| Rating | Label | Description |
|--------|-------|-------------|
| 1 | Superior | Exceptional credit quality, minimal default risk |
| 2 | Strong | Very strong capacity to repay, minor vulnerabilities |
| 3 | Good | Adequate capacity, some sensitivity to adverse conditions |
| 4 | Acceptable | Sufficient capacity but may weaken under stress |
| 5 | Fair | Marginal capacity; adverse conditions could impair repayment |
| 6 | Watch | Potentially weak; requiring closer monitoring |
| 7 | Substandard | Inadequately protected; distinct weakness in repayment |
| 8 | Doubtful/Loss | Collection in full is questionable or improbable |

Ratings 6-8 are considered **adversely rated**. Ratings 3-5 are the performing
but monitored band. Ratings 1-2 are strong.

---

## Regrade Methodology

When the task asks to re-derive or regrade risk ratings, evaluate each loan
against its objective factors. The goal is an independent assessment based on
observable data, not merely copying the current rating.

### Factor Hierarchy (strongest to weakest signal)

1. **Payment status** — the single most important factor
   - Nonaccrual: forces rating 8 (loss) regardless of other factors
   - 90+ Days Past Due: forces at least rating 7
   - 60 Days Past Due: forces at least rating 6
   - 30 Days Past Due: forces at least rating 5
   - Current: no floor; rate on other factors

2. **DSCR (Debt Service Coverage Ratio)**
   - Below 0.80: severe cash flow deficiency (suggest rating 7-8)
   - 0.80 - 0.99: inadequate coverage (suggest rating 6)
   - 1.00 - 1.19: marginal coverage (suggest rating 5)
   - 1.20 - 1.49: adequate coverage (suggest rating 4)
   - 1.50 - 1.99: good coverage (suggest rating 3)
   - 2.00+: strong coverage (suggest rating 1-2)

3. **LTV (Loan-to-Value)**
   - Above 100%: underwater collateral (suggest +2 notch penalty)
   - 90% - 100%: high leverage (suggest +1 notch penalty)
   - 70% - 89%: moderate leverage (neutral)
   - Below 70%: strong collateral position (suggest -1 notch benefit)

4. **FICO / Credit Score** (if available)
   - Below 580: poor credit (suggest +2 notch penalty)
   - 580-669: fair credit (suggest +1 notch penalty)
   - 670-739: good credit (neutral)
   - 740+: excellent credit (suggest -1 notch benefit)

5. **Sector Risk**
   - High-risk sectors (construction, hospitality, startup-heavy): +1 notch
   - Moderate-risk sectors (retail, healthcare): neutral
   - Low-risk sectors (government, essential services): -1 notch

### Regrade Procedure

For each loan in the target population:

1. Start with the current_rating as baseline
2. Apply the payment-status floor first (it can only raise the rating number)
3. Adjust by DSCR signal (+/- based on the range)
4. Adjust by LTV signal (+/- based on the range)
5. Adjust by FICO signal (+/- based on the range, if available)
6. Adjust by sector risk
7. Clamp the result to [1, 8]

Each factor adjustment is typically 1 notch, or 2 notches for extreme values.
The payment-status floor is the only hard constraint; all other adjustments
are cumulative signals that push the rating in the indicated direction.

The final rating should reflect a holistic assessment. When factors are mixed
(e.g., strong DSCR but weak LTV), let the dominant signals drive the outcome
rather than simply averaging adjustments.

### Policy Override

Always read `GET /api/policies` first. If the policy endpoint provides explicit
rating rules, thresholds, or factor weights, use those instead of the
conventions above. Policy rules take precedence.

---

## Material Downgrades

After regrading the population, identify material downgrades:

```
downgrade_notches = final_rating - current_rating
material if downgrade_notches >= 2
```

List material downgrades sorted ascending by loan_id. Include loan_id,
current_rating, final_rating, downgrade_notches, and exposure.

---

## Migration from Specific Current Ratings

When the template asks for migration from a specific current rating (e.g.,
"migration from current rating 3"), include only loans whose current_rating
was that value AND whose final_rating is different (the rating migrated).

Group by final_rating, list loan_ids ascending within each group.

Loans that stayed at the same rating after regrade are not migration events.
