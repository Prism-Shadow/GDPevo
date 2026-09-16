# Credit Policy Rules Reference

This document explains how to apply each rule section from the policies endpoint. Read this alongside the raw policy JSON.

## Risk rating re-derivation

### Dominant factor rule

The final re-derived rating for a loan is the **maximum** (worst) of these three components:

```
final_rating = max(DSCR_rating, LTV_rating, delinquency_floor)
```

Null factors are skipped and contribute no rating.

### DSCR thresholds

Map the loan's `dscr` value to a rating. Use the first matching threshold from the `risk_rating.dscr_thresholds` array in the policy JSON.

| DSCR range | Rating |
|---|---|
| >= 1.50 | 3 |
| 1.25 – 1.49 | 4 |
| 1.05 – 1.24 | 5 |
| 1.00 – 1.04 | 6 |
| < 1.00 | 7 |

If DSCR is null, this factor contributes no rating.

### LTV thresholds

Map the loan's `ltv` value to a rating from `risk_rating.ltv_thresholds`:

| LTV range | Rating |
|---|---|
| <= 0.65 | 3 |
| 0.66 – 0.75 | 4 |
| 0.76 – 0.85 | 5 |
| 0.86 – 1.00 | 6 |
| > 1.00 | 7 |

If LTV is null, this factor contributes no rating.

### Delinquency floors

The `delinquency_minimums` map from policy JSON provides rating floors:

| Payment status | Minimum rating |
|---|---|
| Current | (none) |
| 30 Days Past Due | 4 |
| 60 Days Past Due | 5 |
| 90+ Days Past Due | 7 |
| Nonaccrual | 8 |

A loan's final rating cannot be better than its delinquency floor, regardless of DSCR and LTV factors.

### Rating migration

A downgrade is **material** when `final_rating - current_rating >= material_downgrade_notches` (typically 2). Compute this per loan and include only loans meeting the threshold in the material_downgrades list.

### Regrade population

The `target_current_rating_min` from the answer template defines which loans to regrade. For example, if min is 3, regrade all loans with `current_rating >= 3`. Loans with rating 1 or 2 are outside the regrade scope.

## CDFI factor scoring

For watch-list and risk classification tasks, score each of four factors. A null factor contributes 0 to the total.

### FICO score

| FICO range | Score |
|---|---|
| > 720 | 0 |
| 680–720 | 1 |
| 580–679 | 3 |
| < 580 | 5 |
| null | 0 |

### LTV score (CDFI factor table, not risk-rating table)

| LTV range | Score |
|---|---|
| < 0.40 | 0 |
| 0.40–0.60 | 2 |
| 0.60–0.80 | 4 |
| > 0.80 | 6 |
| null | 0 |

Note: the CDFI LTV factor ranges differ from the risk-rating LTV thresholds — use this table for CDFI scoring.

### Debt-to-asset score

| Debt/asset range | Score |
|---|---|
| < 0.40 | 0 |
| 0.40–0.60 | 2 |
| 0.60–0.80 | 4 |
| > 0.80 | 6 |
| null | 0 |

### Liquidity months score

| Liquidity range | Score |
|---|---|
| > 12 | 0 |
| 6–12 | 1 |
| 3–6 | 3 |
| < 3 | 5 |
| null | 0 |

### Class assignment

Sum the four factor scores to get `factor_score`, then classify:

| Class | Score range |
|---|---|
| Prime | 0–5 |
| Desirable | 6–9 |
| Satisfactory | 10–13 |
| Watch | 14–18 |
| Doubtful | >= 19 |
| Projected Loss | >= 19 AND ltv > 1.0 |

The Projected Loss class overrides Doubtful when both conditions hold (score >= 19 and ltv > 1.0).

## CRE weighted credit scoring

For comparing competing CRE applications, compute a weighted score using `cre_weighted_score.weights` from the policy.

### Factor scoring for CRE applications

**Capacity** (weight 0.45) — score based on application DSCR; use the same thresholds as risk-rating DSCR but mapped to integer scores:

| DSCR range | Score |
|---|---|
| >= 1.50 | 0 |
| 1.25–1.49 | 1 |
| 1.05–1.24 | 2 |
| 1.00–1.04 | 3 |
| < 1.00 | 4 |

**Capital** (weight 0.03) — score from CDFI LTV factor table using application LTV. Null LTV contributes 0.

**Character** (weight 0.05) — score from CDFI FICO factor table using application FICO. Null FICO contributes 0.

**Collateral/exposure** (weight 0.36) — score from CDFI debt_to_asset factor table using `total_debt / total_assets` if both are available; otherwise 0.

**Conditions** (weight 0.11) — score from `prior_delinquencies_12m`: 0 if 0, 1 if 1–2, 2 if 3+.

### Weighted score formula

```
weighted_cdfi_score = (capacity * 0.45) + (capital * 0.03) + (character * 0.05) + (collateral * 0.36) + (conditions * 0.11)
```

Round the final weighted score to 1 decimal place.

### Score class

| Weighted score | Class |
|---|---|
| <= 2.0 | approve_quality |
| 2.1 – 3.0 | conditional |
| > 3.0 | weak |

## Stress testing

### Watch-list stress (+200bp)

For watch-list tasks, apply the rate shock to loans with available DSCR:

```
stressed_dscr = dscr / 1.18
```

Or equivalently: `stressed_dscr = dscr / (1 + 0.18)`. The shock label is `"+200bp"`.

A loan **breaches** when `stressed_dscr < 1.0`. The `coverage_breach_threshold` from policy is 1.0.

### CRE dual-stress

For CRE comparison tasks:

```
stressed_dscr = dscr * 0.85 / 1.18
```

Equivalently: `stressed_dscr = dscr * 0.85 / (1 + 0.18)`. This applies a 15% income haircut and a +200bp rate shock simultaneously.

Breach threshold is 1.0: `stressed_dscr < 1.0` is a breach.

## Concentration analysis

### Sector concentration

Each sector has a `limit_pct` from the sector-exposures table. If a sector is not in the table, use the branch's `sector_ceiling_pct` as default.

```
existing_concentration = sector_exposure / total_loans_outstanding
post_approval_concentration = (sector_exposure + approved_amount) / (total_loans_outstanding + approved_amount)
```

A flag is raised when `post_approval_concentration > limit_pct` (for the sector-specific limit) or when the approval would worsen an already over-limit sector.

Use the `handling` enum from the answer template for concentration flag resolution: `approve`, `conditional_approve`, `decline`, `participation_required`, `none`.

### CRE concentration

For CRE-specific concentration:
- Sum all existing loans where `loan_type == "CRE"` for `existing_cre_exposure`
- `existing_cre_concentration = existing_cre_exposure / total_loans_outstanding`
- For post-approval: add the selected CRE application amount to both numerator and denominator
- `selected_policy_variance_bps = (post_approval_cre_concentration - cre_policy_limit_pct) * 10000`

### Grandfathering

If a sector's `grandfathered == 1`, existing over-ceiling exposure is allowed to stand. However, new approvals should not increase that overage without mitigation (`participation_required`, `reduced_amount`, or `board_exception`).

## Benchmark comparison

### FDIC benchmark (bank branches)

```
branch_npa_ratio = nonperforming_loans / total_loans_outstanding
variance_ratio = branch_npa_ratio - fdic_benchmark_ratio
variance_bps = variance_ratio * 10000
```

For delinquency benchmarks:
```
branch_delinquency_ratio = delinquency_30_plus_pct from metrics
variance_ratio = branch_delinquency_ratio - fdic_benchmark_ratio
```

The `benchmark_version` field in output should match the FDIC benchmark version string from the manifest or benchmark response (e.g., `"fdic_q4_2024"`).

### NCUA benchmark (credit unions)

For segment posture:
1. Find the target state row in NCUA benchmark rows
2. Find the US row for national comparison
3. Compute peer median for each metric across the listed peer states
4. Compare directionally: for each metric, is the state value higher, lower, or equal to the comparison value?

Peer comparison fields in the NCUA benchmark are integers (bps or pct). Compute median: for an even number of peer states, sort and take the average of the middle two values.

## Watch-list action assignment

Actions escalate by severity:
1. `monitor` — light oversight
2. `watchlist` — active monitoring with periodic review
3. `special_assets` — transfer to special assets team
4. `workout` — formal workout plan required
5. `partial_chargeoff_review` — review for partial charge-off
6. `legal_referral` — refer to legal for recovery

### Assignment guidelines

Consider risk_class, payment_status, stress breach, and severity of credit weakness:

- **Risk class Desirable (6–9) + Current + no breach** → `watchlist`
- **Risk class Desirable (6–9) + 90+ DPD** → `special_assets`
- **Risk class Watch (14–18) + Current + breached** → `special_assets`
- **Risk class Watch (14–18) + Nonaccrual** → `workout`
- **Risk class Doubtful/Projected Loss + Nonaccrual + underwater** → `partial_chargeoff_review`
- **Projected Loss + Nonaccrual** → `partial_chargeoff_review`

For loans where stress cannot be computed (no DSCR), base action on risk_class and payment_status alone.

### Top problem credit selection

The top problem credit is the loan with:
1. The worst (highest) final_rating first
2. Then worst payment_status (Nonaccrual > 90+ > 60 > 30 > Current)
3. Then highest exposure as tiebreaker

## Application decline reason codes

Map from the answer template's `reason_code_enum`:

| Reason code | When to apply |
|---|---|
| `capacity_limit` | Remaining capacity < requested_amount |
| `sector_breach` | Post-approval would exceed sector limit without mitigation |
| `weak_dscr` | DSCR below policy floor (< 1.05) |
| `high_ltv` | LTV > 0.80 |
| `low_fico` | FICO < 580 |
| `recent_bankruptcy` | `bankruptcy_months_ago` is not null |
| `startup_risk` | `years_in_business` < 2 |
| `underwater_collateral` | LTV > 1.0 |
| `policy_floor_missing` | DSCR < 1.0 and LTV missing or DSCR/fico both deficient |
| `documentation_gap` | `documentation_complete == 0` |
| `fdic_adverse_variance` | Branch NPA/delinquency significantly above FDIC benchmark |
| `ncua_peer_weakness` | State metrics worse than peers (for credit union segments) |

For an application with multiple reasons, list reason codes sorted alphabetically.

## Posture determination (credit union segments)

Determine posture based on external risk and capacity:

- `continue_approving` — strong state metrics, capacity available
- `continue_with_tighter_conditions` — mixed state metrics, capacity available but external risk elevated
- `temporarily_pause` — weak state metrics, delinquency trending up

The interpretation combines capacity_status, external_risk_status, risk_tolerance, and committee_message.

### External risk status

- `stronger_than_national_and_peers` — most metrics better than US and peer median
- `mixed_vs_national_and_peers` — metrics mixed (some better, some worse)
- `weaker_than_national_and_peers` — most metrics worse than US and peer median

### Escalation triggers

Select triggers from the template's `condition_choices` that align with the segment's risk profile:

- `segment_recent_delinquency_ge_90_bps` — when recent delinquency is elevated (check `internal_context.recent_delinquency_bps`)
- `missing_insurance_or_lien_exception` — when internal context shows control issues
- `quarterly_capacity_exceeded_or_exception_requested` — capacity management
- `state_delinquency_gap_widens_25_bps` — when state is already above peer median

## Numeric precision rules

Apply these consistently:

| Unit | Precision | Example |
|---|---|---|
| USD amounts | 2 decimal places | `13072381.11` |
| Ratios (concentration, variances) | 4 decimal places | `0.1135` |
| Basis points | 2 decimal places | `1037.49` |
| Weighted CRE scores | 1 decimal place | `2.6` |
| NCUA metrics (delinquency_bps, etc.) | Integer (as reported) | `79` |

Round only in the final output, not in intermediate calculations. Use `round(value, n)` in Python.

## Ordering rules

Follow the `ordering` field from the answer template for each list:

- `ascending by loan_id` — sort strings lexicographically
- `ascending by application_id` — sort strings lexicographically
- `ascending by final_rating` — sort integers
- `ascending by sector` — sort strings lexicographically
- `ascending by current_rating` — sort integers
- `ascending by action` — sort action enum strings lexicographically
- `ascending by trigger_id` — sort strings lexicographically
- `ascending alphabetically` — sort strings lexicographically
- `descending exposure, then ascending loan_id` — sort numerically descending first, then lexicographically ascending for ties
