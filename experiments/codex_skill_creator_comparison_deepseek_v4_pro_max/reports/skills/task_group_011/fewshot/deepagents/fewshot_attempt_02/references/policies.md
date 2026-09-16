# Credit Policy Reference

This document captures the full credit policy rules from `/api/policies`. It is a snapshot of the rule structure; always fetch the live endpoint during a task to get current values.

## risk_rating

### Dominant Factor Rule

The final re-derived rating is the **worst (highest numeric) rating** from the available DSCR, LTV/collateral, and delinquency factors. When a factor value is null, omit that factor.

### delinquency_minimums

| Payment Status | Minimum Rating |
|---|---|
| 30 Days Past Due | 4 |
| 60 Days Past Due | 5 |
| 90+ Days Past Due | 7 |
| Current | (no floor) |
| Nonaccrual | 8 |

When payment_status is "Current", delinquency does not impose a floor — the rating comes solely from DSCR and LTV.

### dscr_thresholds

| DSCR Range | Rating |
|---|---|
| >= 1.50 | 3 |
| >= 1.25 | 4 |
| >= 1.05 | 5 |
| >= 1.00 | 6 |
| < 1.00 | 7 |

### ltv_thresholds

| LTV Range | Rating |
|---|---|
| <= 0.65 | 3 |
| <= 0.75 | 4 |
| <= 0.85 | 5 |
| <= 1.00 | 6 |
| > 1.00 | 7 |

### material_downgrade_notches

A downgrade is material when `final_rating - current_rating >= 2`.

## cdfi_factor_scores

### Factor Score Tables

**FICO:**
| FICO Range | Score |
|---|---|
| > 720 | 0 |
| 680-720 | 1 |
| 580-679 | 3 |
| < 580 | 5 |

**LTV:**
| LTV Range | Score |
|---|---|
| < 0.40 | 0 |
| 0.40-0.60 | 2 |
| 0.60-0.80 | 4 |
| > 0.80 | 6 |

**Debt-to-Asset:**
| D/A Range | Score |
|---|---|
| < 0.40 | 0 |
| 0.40-0.60 | 2 |
| 0.60-0.80 | 4 |
| > 0.80 | 6 |

**Liquidity (months):**
| Liquidity Range | Score |
|---|---|
| > 12 | 0 |
| 6-12 | 1 |
| 3-6 | 3 |
| < 3 | 5 |

### Risk Class Thresholds

| Class | Score Range |
|---|---|
| Prime | 0-5 |
| Desirable | 6-9 |
| Satisfactory | 10-13 |
| Watch | 14-18 |
| Doubtful | >= 19 |
| Projected Loss | >= 19 **and** ltv > 1.0 |

The factor_score is the sum of all available individual factor scores. Null factors are omitted from the sum.

## cre_weighted_score

### Weights

| Factor | Weight |
|---|---|
| Capacity (DSCR) | 0.45 |
| Collateral/Exposure (LTV) | 0.36 |
| Conditions (sector concentration) | 0.11 |
| Capital (net income / total assets) | 0.03 |
| Character (relationship years) | 0.05 |

### Sub-score Mapping (1-5 scale, 1 is best)

**Capacity (DSCR):**
| DSCR | Score |
|---|---|
| >= 1.50 | 1 |
| >= 1.25 | 2 |
| >= 1.05 | 3 |
| >= 1.00 | 4 |
| < 1.00 | 5 |

**Collateral/Exposure (LTV):**
| LTV | Score |
|---|---|
| < 0.40 | 1 |
| < 0.60 | 2 |
| < 0.80 | 3 |
| < 1.00 | 4 |
| >= 1.00 | 5 |

**Conditions (sector concentration):** Score 4-5 when the application's sector is near or over its concentration limit; score 3 for moderate exposure; score 1-2 for low exposure. Evaluate using the sector's `current_exposure + requested_amount` vs `limit_pct * total_loans`.

**Capital (net_income / total_assets):**
| Ratio | Score |
|---|---|
| >= 0.20 | 1 |
| >= 0.10 | 2 |
| >= 0.05 | 3 |
| >= 0.00 | 4 |
| < 0.00 | 5 |

**Character (relationship years):**
| Years | Score |
|---|---|
| >= 10 | 1 |
| >= 5 | 2 |
| >= 2 | 3 |
| >= 1 | 4 |
| < 1 | 5 |

### Score Classes

| Class | Range |
|---|---|
| approve_quality | <= 2.0 |
| conditional | <= 3.0 |
| weak | > 3.0 |

weighted_cdfi_score = sum(weight_i * sub_score_i), rounded to 1 decimal.

## stress

| Field | Value |
|---|---|
| watch_list_formula | `stressed_dscr = dscr / (1 + 0.18)` |
| watch_list_parallel_shock | +200bp |
| cre_dual_stress_formula | `stressed_dscr = dscr * 0.85 / (1 + 0.18)` |
| coverage_breach_threshold | 1.0 |

All DSCR values rounded to 2 decimals. A loan breaches when stressed_dscr < 1.0.

## capacity_concentration

- `lending_capacity_field`: `branches.lending_capacity_q1`
- `single_sector_default_field`: `branches.sector_ceiling_pct`
- `branch_sector_override_table`: `sector_exposures` (sector-specific `limit_pct` overrides branch default)
- `allowed_mitigations`: `participation_required`, `reduced_amount`, `board_exception`
- Grandfathering rule: Existing over-ceiling exposure may be grandfathered, but new approvals may not worsen that sector without mitigation.

### Sector Concentration Computation

- `post_approval_pct = (current_exposure + approved_amount) / total_loans_outstanding`
- Sector limit is `sector_exposures[i].limit_pct` if it exists, otherwise `branch.sector_ceiling_pct`.
- Sector breach when `post_approval_pct > limit_pct`.
- When a sector has `grandfathered == 1` and is already over limit, new approvals still require mitigation (`participation_required`) and should not worsen the overage.

### Lending Capacity

- `remaining_capacity = lending_capacity_q1 - sum(bank_capacity_used for approved/conditional)`
- Priority ranking: approved and conditionally approved applications, ordered by dscr descending, then relationship_deposit_balance descending, then existing_relationship_years descending.
