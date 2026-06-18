# Policy schema, bands, and formula reference

This mirrors the structure of `GET /api/policies` (`policy_version: credit_policy_v2025Q1`)
and records the exact computations confirmed against the standard answers. **Always re-fetch
`/api/policies` at runtime** — if a band here differs from the live policy, the live policy
wins. This file exists so you recognize the schema and apply boundaries correctly (the
inclusive/exclusive edges are the easy thing to get wrong).

## Table of contents
1. risk_rating (regrade bands)
2. cdfi_factor_scores (watch-list risk classes)
3. cre_weighted_score (CRE 5-C scoring)
4. stress formulas
5. capacity_concentration
6. Benchmark fields (FDIC / NCUA)
7. Worked numeric checks

---

## 1. risk_rating — regrade bands

`dominant_factor_rule`: "Final re-derived rating is the worst numeric rating from available
DSCR, LTV or collateral, and delinquency factors." → `final = max(available factor ratings)`.
`material_downgrade_notches`: 2 → material when `final - current >= 2`.

**dscr_thresholds** (descending; first match wins):
| condition | rating |
|---|---|
| dscr >= 1.5 | 3 |
| dscr >= 1.25 | 4 |
| dscr >= 1.05 | 5 |
| dscr >= 1.0 | 6 |
| dscr < 1.0 | 7 |

**ltv_thresholds**:
| condition | rating |
|---|---|
| ltv <= 0.65 | 3 |
| ltv <= 0.75 | 4 |
| ltv <= 0.85 | 5 |
| ltv <= 1.0 | 6 |
| ltv > 1.0 | 7 |

**delinquency_minimums** (a floor from `payment_status`; `Current` → no contribution):
| payment_status | min rating |
|---|---|
| Current | null |
| 30 Days Past Due | 4 |
| 60 Days Past Due | 5 |
| 90+ Days Past Due | 7 |
| Nonaccrual | 8 |

If DSCR and LTV are both null and payment is `Current`, every factor is null → keep the
existing `current_rating`.

---

## 2. cdfi_factor_scores — watch-list risk classes

Sum per-factor points over the **available** factors (skip nulls). Boundary reading:
"0.40-0.60" includes the upper edge (`<= 0.60`); ">0.80" is strictly greater. FICO
"680-720" means `>=680 and <=720`; ">720" is strictly greater.

**fico**: `>720 → 0`, `680-720 → 1`, `580-679 → 3`, `<580 → 5`.
**ltv**: `<0.40 → 0`, `0.40-0.60 → 2`, `0.60-0.80 → 4`, `>0.80 → 6`.
**debt_to_asset**: `<0.40 → 0`, `0.40-0.60 → 2`, `0.60-0.80 → 4`, `>0.80 → 6`.
**liquidity_months**: `>12 → 0`, `6-12 → 1`, `3-6 → 3`, `<3 → 5`.

**classes** (report base sum as `factor_score`, map to class):
| class | score range |
|---|---|
| Prime | 0-5 |
| Desirable | 6-9 |
| Satisfactory | 10-13 |
| Watch | 14-18 |
| Doubtful | >=19 |
| Projected Loss | >=19 and ltv>1.0 (operationally: ltv>1.0 in a loss/Nonaccrual posture, even if the base score is in the Watch band) |

Worked check (Summit adverse loans):
`SUM-LN-003` ltv0.9511(6)+d2a0.3579(0)+liq11.6(1) = 7 → Desirable.
`SUM-LN-901` ltv0.93(6)+d2a0.82(6)+liq2.4(5) = 17 → Watch (ltv<=1.0, Current).
`SUM-LN-902` same base 17 but ltv1.18>1.0 and Nonaccrual → **Projected Loss**.

---

## 3. cre_weighted_score — CRE 5-C scoring

Weighted average of five sub-scores, each 1–5 where **lower is better**. Sub-scores come
from objective factors (capacity ← DSCR; collateral_exposure ← LTV / concentration; plus
conditions, character, capital from documentation, relationship, leverage). Report the
weighted result to **1 decimal**.

**weights**: capacity 0.45, collateral_exposure 0.36, conditions 0.11, character 0.05,
capital 0.03. (Capacity and collateral dominate; capital/character are tie-breakers.)

**classes**: `<= 2.0 → approve_quality`, `<= 3.0 → conditional`, `> 3.0 → weak`.

Observed: HAR-APP-901 → 2.6 (conditional), HAR-APP-902 → 4.4 (weak). The exact sub-score
table is not uniquely recoverable from the totals; assign each sub-score from its objective
factor on a 1–5 scale (better factor → lower number), compute `Σ weight*subscore`, then
classify by the bands above. The grader keys on the rounded score and the class.

---

## 4. stress formulas

| name | formula | threshold | used by |
|---|---|---|---|
| watch_list_formula (+200bp) | `stressed = dscr / (1 + 0.18)` | 1.0 | SOP D |
| cre_dual_stress_formula | `stressed = dscr * 0.85 / (1 + 0.18)` | 1.0 | SOP E |

`coverage_breach_threshold = 1.0`. `breaches_threshold = stressed_dscr < 1.0` (strict).
Round `stressed_dscr` to 2 dp for output. Only loans/apps with a non-null DSCR appear in
stress results. Report the literal formula string the template asks for (e.g.
`"+200bp"` shock label, or `"dscr * 0.85 / 1.18"` as the CRE formula expression).

Worked check: SUM-LN-011 base 1.14 → 1.14/1.18 = 0.966 → 0.97 → breach (True).
HAR-APP-902 base 1.32 → 1.32*0.85/1.18 = 0.951 → 0.95 → breach (True);
HAR-APP-901 base 1.47 → 1.06 → no breach.

---

## 5. capacity_concentration

- `lending_capacity_field`: `branches.lending_capacity_q1` (the quarter's capacity).
- `single_sector_default_field`: `branches.sector_ceiling_pct` (default sector ceiling;
  individual sectors may carry their own `limit_pct` in `sector-exposures`, which overrides
  the default — `branch_sector_override_table: sector_exposures`).
- `allowed_mitigations`: `participation_required`, `reduced_amount`, `board_exception`.
- `grandfathering_note`: existing over-ceiling exposure may be grandfathered, but **new
  approvals may not worsen a sector without mitigation**. Check the `grandfathered` flag on
  the sector row.

**Capacity charge rules** (`bank_capacity_used`):
- Plain approve: `= approved_amount`.
- SBA: `= approved_amount * (1 - sba_guaranty_pct)`.
- Participation (sector breach): retain `R` solving
  `(existing_sector_exposure + R) / (total_loans_outstanding + other_retained + R) = limit_pct`
  ⇒ `R = (limit_pct*(total_loans + other_retained) - existing_sector_exposure) / (1 - limit_pct)`.

**Concentration bases:**
- Allocation post-approval sector pct: `base = total_loans_outstanding + gross_approved_amount`;
  `exposure_after = existing_sector_exposure + full_approved_amount`.
- CRE post-approval pct (single selected app): `(existing_cre + approved) / (total_loans + approved)`.

Worked check (Lakeview): base = 14,334,094.87 + 4,574,253.45 = 18,908,348.32.
Healthcare after = 1,937,814.40 + 1,650,000 = 3,587,814.40 → 0.1897.
901 participation retained R: limit 0.19, other_retained = 1,168,328.59 + 915,924.86 +
210,000 = 2,294,253.45 → R = (0.19*(14,334,094.87+2,294,253.45) − 1,937,814.40)/0.81 =
1,508,113.31.

---

## 6. Benchmark fields

**FDIC (`fdic_q4_2024`)** — branch-level noncurrent/delinquency comparison metrics:
- `total_loans_noncurrent_pct` (all-loans NPA review)
- `total_real_estate_noncurrent_pct`
- `construction_development_noncurrent_pct`
- `total_real_estate_30_89_pct` (30–89 day delinquency; used for CRE delinquency variance)
- `construction_development_30_89_pct`

Variance: `variance_ratio = branch_ratio - benchmark_ratio` (4 dp);
`variance_bps = (branch_ratio - benchmark_ratio) * 10000` from **unrounded** ratios (2 dp).

**NCUA (`ncua_q1_2025`)** — per-state credit-union rows (integers, copy exactly):
`delinquency_bps`, `loan_to_share_pct`, `roaa_bps`, `positive_net_income_pct`. A `US` row
is included when you fetch without a state filter — use it for national comparison and use
the peer-state set for the peer median. Polarity: higher delinquency = worse; higher
loan_to_share = more aggressive; lower roaa / lower positive_net_income = worse.

---

## 7. Worked numeric checks (sanity anchors — re-derive from live data, don't copy)

These confirm the procedures; they are NOT answers to reuse. Always recompute from the API.

- NPA (Redwood): npa 1,725,000 / total 15,191,701.54 = 0.11354… → ratio 0.1135;
  vs FDIC 0.0098 → variance 0.1037, bps 1037.49 (from unrounded ratio).
- Regrade worst-factor: RED-LN-008 dscr0.87(7)/ltv0.8206(5)/Current(–) → final 7 (was 3) →
  4-notch material downgrade.
- Peer direction (NC): delq79 vs US58 → higher; vs peer-median(SC72,TN64,VA53)=64 → higher.
  roaa44 vs US62 → lower; vs peer-median(51,59,65)=59 → lower.
- CRE concentration (Harbor): CRE Σ = 7,011,570.24 / 14,933,688.02 = 0.4695; selected 901
  +2,100,000 → (7,011,570.24+2,100,000)/(14,933,688.02+2,100,000) = 0.5349; vs limit 0.29 →
  2449.15 bps.
