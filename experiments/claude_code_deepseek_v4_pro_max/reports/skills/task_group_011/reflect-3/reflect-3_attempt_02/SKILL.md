# Credit Risk Lending Committee Skill

## API Workflow

Base URL from environment (not localhost). Start with:
- `GET /api/manifest` — lists endpoints, benchmark versions, record counts
- `GET /api/health` — confirms service status
- `GET /api/policies` — risk-rating thresholds, CDFI factor tables, stress formulas, CRE weights, concentration rules

Key data endpoints:
- `GET /api/branches` / `GET /api/branches/{id}` — branch metadata, lending capacity, sector ceiling, CRE limit, state, institution type
- `GET /api/branches/{id}/metrics` — quarterly metrics (NPA, total loans, delinquency, deposits)
- `GET /api/branches/{id}/loans` — loan portfolio with ratings, DSCR, LTV, payment status, FICO, debt-to-asset, liquidity
- `GET /api/branches/{id}/sector-exposures` — per-sector current exposure, limit_pct, grandfathered flag
- `GET /api/branches/{id}/applications` — pending applications with DSCR, LTV, FICO, DTI, guarantor, relationship, SBA, bankruptcy
- `GET /api/benchmarks/fdic/q4-2024` — FDIC noncurrent/delinquency benchmarks
- `GET /api/benchmarks/ncua/q1-2025` — NCUA state-level metrics (delinquency_bps, loan_to_share_pct, roaa_bps, positive_net_income_pct)
- `GET /api/credit-union-segments/{id}` — segment details, peer states, minimum checklist, internal context, quarterly capacity

## Risk Rating Re-derivation (Dominant Factor Rule)

Final rating = worst (highest numeric) of available DSCR, LTV, and delinquency factors:

**DSCR thresholds:**
| DSCR Range | Rating |
|---|---|
| ≥ 1.50 | 3 |
| ≥ 1.25 | 4 |
| ≥ 1.05 | 5 |
| ≥ 1.00 | 6 |
| < 1.00 | 7 |

**LTV thresholds:**
| LTV Range | Rating |
|---|---|
| ≤ 0.65 | 3 |
| ≤ 0.75 | 4 |
| ≤ 0.85 | 5 |
| ≤ 1.00 | 6 |
| > 1.00 | 7 |

**Delinquency minimums:**
| Payment Status | Minimum Rating |
|---|---|
| Current | (none) |
| 30 Days Past Due | 4 |
| 60 Days Past Due | 5 |
| 90+ Days Past Due | 7 |
| Nonaccrual | 8 |

**Material downgrade = ≥ 2 notches** (per policy `material_downgrade_notches`).

When a loan has no DSCR, LTV, or delinquency-based factors available, retain its current rating.

## CDFI Factor Scoring

Factor score = FICO score + LTV score + Debt-to-Asset score + Liquidity score. Null/missing factors score 0.

| Factor | Range | Score |
|---|---|---|
| FICO | >720 / 680-720 / 580-679 / <580 | 0 / 1 / 3 / 5 |
| LTV | <0.40 / 0.40-0.60 / 0.60-0.80 / >0.80 | 0 / 2 / 4 / 6 |
| Debt-to-Asset | <0.40 / 0.40-0.60 / 0.60-0.80 / >0.80 | 0 / 2 / 4 / 6 |
| Liquidity (months) | >12 / 6-12 / 3-6 / <3 | 0 / 1 / 3 / 5 |

**Risk classes:** Prime (0-5), Desirable (6-9), Satisfactory (10-13), Watch (14-18), Doubtful (≥19), Projected Loss (≥19 and LTV > 1.0).

For Nonaccrual loans with underwater collateral (LTV > 1.0), "Projected Loss" classification may apply even when the numeric score is below 19, reflecting the credit's actual loss exposure.

## Stress-Test Formulas

**Watch-list parallel shock (+200bp):**
```
stressed_dscr = dscr / (1 + 0.18)
breach_threshold = 1.0
```

**CRE dual-stress formula:**
```
stressed_dscr = dscr × 0.85 / (1 + 0.18)
breach_threshold = 1.0
```

## CRE Weighted Scoring (Competing Credit)

Score each application 1-5 (1=best) on five dimensions, then compute weighted sum. Lower total is better.

| Dimension | Weight | Key Drivers |
|---|---|---|
| Capacity | 0.45 | DSCR (≥1.5→1, ≥1.35→2, ≥1.25→3, ≥1.10→4, <1.10→5) |
| Capital | 0.03 | Debt/Asset ratio |
| Character | 0.05 | Guarantor strength, relationship years, prior delinquencies |
| Collateral/Exposure | 0.36 | LTV |
| Conditions | 0.11 | Loan purpose, sector stability, term |

**Score classes:** approve_quality (≤ 2.0), conditional (≤ 3.0), weak (> 3.0).

## Concentration Rules

**Sector concentration limit** = `limit_pct × total_loans_outstanding`. Per-sector overrides live in sector-exposures (e.g., Healthcare may have a tighter limit_pct than the branch default `sector_ceiling_pct`).

Existing over-ceiling exposure is grandfathered, but new approvals may not worsen that sector without mitigation: `participation_required`, `reduced_amount`, or `board_exception`.

**CRE exposure** = sum of outstanding balances for loans with `loan_type = "CRE"`. CRE concentration = CRE exposure / total_loans_outstanding. Compare against `cre_policy_limit_pct`.

For SBA-guaranteed loans, only the unguaranteed portion (`approved_amount × (1 - sba_guaranty_pct)`) counts against `bank_capacity_used`, but the full approved amount counts toward sector/CRE concentration.

## Benchmark Conventions

**NPA benchmark:** Use `total_loans_noncurrent_pct` from FDIC Q4 2024. Branch NPA = `nonperforming_loans` from branch metrics. Ratios computed against `total_loans_outstanding`.

**FDIC delinquency benchmark:** Use `total_real_estate_30_89_pct` for CRE-related reviews. Branch ratio = branch-level delinquency metric (from branch metrics or computed from loan-level data).

**NCUA benchmarks:** Use exact integer values from the NCUA Q1 2025 table. Peer median = median of listed peer states for each metric. Direction comparisons: "higher", "lower", or "equal" relative to US national or peer median.

## Output Field Conventions

- **Exposure/balance fields:** rounded to 2 decimal places (USD)
- **Ratios (percentages as decimals):** rounded to 4 decimal places
- **Basis points (bps):** rounded to 2 decimal places; bps = ratio × 10000
- **Weighted CDFI CRE score:** rounded to 1 decimal place
- **NCUA metric integers:** exact values as reported (no rounding)
- **factor_score:** integer
- **Sorting:** loan_ids ascending within lists; final_rating ascending in exposure totals; sector then application_id for concentration flags; descending exposure then ascending loan_id for workout queues
- **Lists with no items:** use empty array `[]`, not omitted
- **Enum values:** use exact string values from templates; do not invent new ones

## Common Pitfalls

1. **Sector limit computation:** Always use `limit_pct × total_loans_outstanding` (not total_assets or lending_capacity). Verify by summing sector_exposures — they should equal total_loans_outstanding.

2. **Re-derivation population:** Only loans meeting the rating threshold (e.g., current_rating ≥ 3) are re-derived. Loans below threshold keep their current rating and are excluded from target counts but included in portfolio-wide exposure totals.

3. **Final rating exposure totals:** Include only the re-derived (target) population, not all branch loans. Each loan's final re-derived rating is its assigned bucket.

4. **Watch-list action coverage:** All target-population loans receive an action assignment. Action tiers: monitor (ratings 3-4), watchlist (5-6), special_assets (7, current), workout (7, past due), partial_chargeoff_review or legal_referral (8).

5. **Delinquency factor is a minimum, not additive:** If a loan is 30 DPD, the rating cannot be better than 4 regardless of DSCR/LTV.

6. **SBA capacity treatment:** `bank_capacity_used = approved_amount × (1 - sba_guaranty_pct)`. The SBA-guaranteed portion reduces the bank's capital commitment. But full amount counts toward gross and sector exposure.

7. **Post-approval concentrations:** Only include sectors with approved applications or existing exposure changes. Unaffected sectors may be omitted from the summary.

8. **Monitoring cadence for mixed adverse portfolios:** Use `quarterly` as default when the population spans multiple risk classes; use `monthly` only when most credits are Watch or worse.

9. **DSCR-stressed rounding:** Compute stressed DSCR from raw base DSCR first, then round the result to 2 decimals.

10. **NCUA peer median:** Sort peer state values, take middle. For 3 peers, it's the 2nd value. Compare NC against this median for each of the 4 metrics independently.
