---
name: rating-matrix
description: Reusable risk-rating derivation logic for credit risk committee analyses.
---

# Risk Rating Derivation

## Loan Risk Rating Scale

| Rating | Label | Description |
|--------|-------|-------------|
| 1 | Minimal Risk | Investment-grade borrower, strong cash flow, low LTV. |
| 2 | Low Risk | Solid credit metrics, minor weaknesses. |
| 3 | Acceptable Risk | Adequate repayment capacity, manageable LTV. |
| 4 | Watch | Some weakness in cash flow or collateral. |
| 5 | Special Mention | Potential weakness deserves close attention. |
| 6 | Substandard | Inadequate protection; well-defined weakness. |
| 7 | Doubtful | Full collection unlikely; loss probable but not estimable. |
| 8 | Loss | Considered uncollectible; nonaccrual or charge-off. |

## Rating Downgrade Triggers

When re-deriving a rating for a loan in a migration review, start from its `current_rating` and apply objective downgrades based on the following thresholds. The final rating is the highest (worst) rating triggered by any single factor.

| Factor | Threshold | Minimum Downgrade To |
|--------|-----------|---------------------|
| LTV > 1.00 | Underwater collateral | Rating 7 |
| LTV > 0.90 | High leverage | Rating 6 |
| LTV > 0.80 | Elevated leverage | Rating 5 |
| DSCR < 1.00 | Negative cash flow | Rating 7 |
| DSCR < 1.15 | Weak coverage | Rating 6 |
| DSCR < 1.25 | Marginal coverage | Rating 5 |
| Payment: Nonaccrual | Ceased interest accrual | Rating 8 |
| Payment: 90+ Days Past Due | Severe delinquency | Rating 7 |
| Payment: 60 Days Past Due | Significant delinquency | Rating 6 |
| Payment: 30 Days Past Due | Early delinquency | Rating 5 |
| FICO < 580 | Deep subprime | Rating 6 |
| FICO < 620 | Subprime | Rating 5 |
| Recent bankruptcy | Within past 7 years | Rating 7 |

## CDFI Factor Scoring

For watch-list risk classification, compute a factor score by summing points from each risk dimension:

| Dimension | Condition | Points |
|-----------|-----------|--------|
| Payment Status | Nonaccrual | 8 |
| Payment Status | 90+ Days Past Due | 6 |
| Payment Status | 60 Days Past Due | 4 |
| Payment Status | 30 Days Past Due | 2 |
| Payment Status | Current | 0 |
| LTV | > 1.00 | 8 |
| LTV | 0.90–1.00 | 5 |
| LTV | 0.80–0.90 | 3 |
| LTV | < 0.80 | 0 |
| DSCR | < 1.00 | 6 |
| DSCR | 1.00–1.15 | 4 |
| DSCR | 1.15–1.25 | 2 |
| DSCR | >= 1.25 | 0 |
| FICO | < 580 | 4 |
| FICO | 580–619 | 2 |
| FICO | 620–679 | 1 |
| FICO | >= 680 | 0 |
| Bankruptcy Flag | true | 4 |
| Startup Flag | true | 2 |

Factor score to risk class mapping:
- 0–5: `Prime`
- 6–10: `Desirable`
- 11–14: `Satisfactory`
- 15–18: `Watch`
- 19–22: `Doubtful`
- 23+: `Projected Loss`

## Watch-List Action Mapping

| Final Rating Range | Recommended Action |
|--------------------|-------------------|
| 8 | `partial_chargeoff_review` |
| 7 | `special_assets` |
| 6 | `watchlist` |
| 5 | `monitor` |

## DSCR Stress Formulas

- **Commercial/Industrial (+200bp shock):** `stressed_dscr = base_dscr - 0.15`
- **CRE dual-stress:** `stressed_dscr = base_dscr * 0.85 / 1.18`
- **Breach threshold:** `stressed_dscr < 1.0`

## CDFI Score Classification (CRE)

| Weighted CDFI Score | Score Class | Decision Path |
|--------------------|-------------|---------------|
| 0.0 – 2.99 | `strong` | `approve` |
| 3.0 – 3.99 | `conditional` | `conditional_approve` or `participation_required` |
| 4.0+ | `weak` | `defer` |
