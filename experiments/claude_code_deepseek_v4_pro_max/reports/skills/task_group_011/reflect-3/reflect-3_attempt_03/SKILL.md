# Bank Branch Credit-Risk Lending Committee — Skill Reference

## API Usage Workflow

1. **GET /api/manifest** — discover available endpoints, benchmark versions, and record counts.
2. **GET /api/branches/{branch_id}** — branch metadata: lending capacity, policy limits, sector ceilings, state, institution type.
3. **GET /api/branches/{branch_id}/metrics** — quarterly metrics: total loans outstanding, nonperforming loans, delinquency pct, deposits, ALLL, net charge-offs. Use the most recent quarter (typically 2025Q1) unless the task specifies otherwise.
4. **GET /api/branches/{branch_id}/loans** — full loan portfolio with ratings, DSCR, LTV, payment status, CDFI factors, exposure, sector, borrower details.
5. **GET /api/branches/{branch_id}/sector-exposures** — per-sector current exposure, limit_pct, and grandfathered flag.
6. **GET /api/branches/{branch_id}/applications** — pending applications with credit metrics, sector, and requested amounts.
7. **GET /api/policies** — risk-rating thresholds, CDFI factor scores, CRE weighted-score weights, DSCR stress formulas, concentration rules, action enums.
8. **GET /api/benchmarks/fdic/q4-2024** — FDIC benchmark ratios (total_loans_noncurrent_pct, total_real_estate_noncurrent_pct, total_real_estate_30_89_pct, construction_development_noncurrent_pct).
9. **GET /api/benchmarks/ncua/q1-2025** — state-level NCUA metrics: delinquency_bps, loan_to_share_pct, roaa_bps, positive_net_income_pct.
10. **GET /api/credit-union-segments/{segment_id}** — segment details: capacity, peer states, minimum checklist, risk tolerance, internal context.

Always use the base URL from `environment_access.md`; never localhost.

---

## Risk Rating Re-derivation (Dominant Factor Rule)

Final re-derived rating = **maximum** (worst numeric value) from available DSCR, LTV, and delinquency factors. If no factors are available, the loan retains its current rating.

### DSCR → Rating

| DSCR     | Rating |
|----------|--------|
| ≥ 1.50   | 3      |
| ≥ 1.25   | 4      |
| ≥ 1.05   | 5      |
| ≥ 1.00   | 6      |
| < 1.00   | 7      |

### LTV → Rating

| LTV       | Rating |
|-----------|--------|
| ≤ 0.65    | 3      |
| ≤ 0.75    | 4      |
| ≤ 0.85    | 5      |
| ≤ 1.00    | 6      |
| > 1.00    | 7      |

### Delinquency Minimums

| Payment Status      | Min Rating |
|---------------------|------------|
| Current             | none       |
| 30 Days Past Due    | 4          |
| 60 Days Past Due    | 5          |
| 90+ Days Past Due   | 7          |
| Nonaccrual          | 8          |

### Material Downgrade

A downgrade of **≥ 2 notches** (final_rating − current_rating ≥ 2) is material.

---

## CDFI Factor Scoring

Sum available factor scores; skip factors where the value is null. Lower total is better.

| Factor           | < 0.40 | 0.40–0.60 | 0.60–0.80 | > 0.80 |
|------------------|--------|-----------|-----------|--------|
| debt_to_asset    | 0      | 2         | 4         | 6      |
| ltv              | 0      | 2         | 4         | 6      |

| Factor           | > 12 | 6–12 | 3–6  | < 3 |
|------------------|------|------|------|-----|
| liquidity_months | 0    | 1    | 3    | 5   |

| Factor | > 720 | 680–720 | 580–679 | < 580 |
|--------|-------|---------|---------|-------|
| fico   | 0     | 1       | 3       | 5     |

### Risk Classes

| Class           | Score Range      |
|-----------------|------------------|
| Prime           | 0–5              |
| Desirable       | 6–9              |
| Satisfactory    | 10–13            |
| Watch           | 14–18            |
| Doubtful        | ≥ 19             |
| Projected Loss  | ≥ 19 **and** ltv > 1.0 |

---

## Watch-List Action Mapping

Map final rating or CDFI risk class to a recommended action from this enum:

`monitor` · `watchlist` · `special_assets` · `workout` · `partial_chargeoff_review` · `legal_referral`

Typical mapping: lower ratings (3–4) → `monitor`/`watchlist`; mid ratings (5–6) → `special_assets`/`workout`; high ratings (7) → `workout`/`partial_chargeoff_review`; rating 8 → `legal_referral`. Adjust based on payment status — a delinquent borrower with a moderate risk class may warrant a stronger action than a current borrower with the same class. Projected Loss → `partial_chargeoff_review` or `legal_referral`.

---

## DSCR Stress Tests

### Watch-List (+200bp Parallel Shock)

```
stressed_dscr = dscr / 1.18
```

### CRE Dual Stress

```
stressed_dscr = dscr × 0.85 / 1.18
```

Breach threshold for both: **1.00** (stressed_dscr < 1.00 → breaches).

Only include loans/applications where DSCR is available. Sort stress results ascending by loan_id or application_id.

---

## CRE Weighted Score

Five components weighted: capacity (0.45), collateral_exposure (0.36), conditions (0.11), character (0.05), capital (0.03). Score each component 1–5 (1 = best) using objective factors:

- **capacity**: DSCR risk-rating tier mapped to 1–5 scale.
- **collateral_exposure**: LTV risk-rating tier mapped to 1–5 scale.
- **capital**: debt/assets ratio (lower is better; debt/assets > 1.0 → 5).
- **character**: guarantor strength (strong → 1, none → 4–5), years in business, prior delinquencies, relationship length.
- **conditions**: sector stability and loan purpose risk.

Weighted score = sum(component × weight), rounded to **1 decimal**.

| Class            | Range     |
|------------------|-----------|
| approve_quality  | ≤ 2.0     |
| conditional      | ≤ 3.0     |
| weak             | > 3.0     |

---

## Concentration and Sector Limits

### Branch-Level

- **lending_capacity_q1**: total dollar capacity available for new originations in Q1.
- **sector_ceiling_pct**: default per-sector exposure / total_loans limit (unless overridden).
- **cre_policy_limit_pct**: separate limit for total CRE exposure / total_loans.

### Sector Exposure

- `current_exposure` / `total_loans_outstanding` = current concentration ratio.
- Post-approval concentration = `(current_exposure + approved_amount) / total_loans_outstanding`.
- Grandfathered sectors (`grandfathered: 1`) allow existing over-ceiling exposure but new approvals may not worsen the breach without mitigation (participation_required, board_exception).

### Concentration Handling

- If post-approval pct > limit_pct: flag = true, handling = `participation_required` or `decline`.
- Concentration ratios stored as decimals with **4 decimal precision**.

---

## FDIC Benchmark Comparisons

FDIC Q4 2024 benchmark metrics (choose based on task context):

| Metric                                 | Value   |
|----------------------------------------|---------|
| total_loans_noncurrent_pct             | 0.0098  |
| total_real_estate_noncurrent_pct       | 0.0121  |
| total_real_estate_30_89_pct            | 0.0051  |
| construction_development_noncurrent_pct| 0.0076  |

- `branch_npa_ratio` = branch NPA exposure / total loans (4 decimal precision).
- `variance_ratio` = branch_ratio − fdic_benchmark_ratio (4 decimal precision).
- `variance_bps` = variance_ratio × 10000 (2 decimal precision).

---

## NCUA Benchmark Comparisons

NCUA Q1 2025 provides per-state: `delinquency_bps`, `loan_to_share_pct`, `roaa_bps`, `positive_net_income_pct`.

Peer comparison: compute **median** of listed peer states for each metric, then compare NC to both US national row and peer median. Direction keywords: `higher`, `lower`, `equal`. Note that higher delinquency and higher loan-to-share are **worse**; higher ROAA and higher positive-net-income are **better**.

---

## Output Field Conventions

### Sorting

- **loan_ids** arrays: ascending (string sort).
- **final_rating_exposure_totals**: ascending by `final_rating`.
- **migration lists**: ascending by `final_rating`.
- **decisions**: ascending by `application_id`.
- **concentration_flags**: sort by `sector` then `application_id`.
- **post_approval_concentrations**: ascending by `sector`.
- **severe_bucket_counts**: ascending by `current_rating`, then `payment_status`.
- **workout_queue**: descending `exposure`, then ascending `loan_id`.
- **decline reason_codes**: ascending alphabetically.
- **escalation_triggers**: ascending by `trigger_id`.
- **conditions list**: ascending alphabetically.

### Rounding

| Type                  | Precision |
|-----------------------|-----------|
| Currency (USD)        | 2 decimals |
| Ratios / percentages  | 4 decimals |
| Variance bps          | 2 decimals |
| Weighted CDFI score   | 1 decimal  |
| CDFI factor_score     | integer    |
| Counts                | integer    |

### Enum Discipline

Use template-provided enum values exactly as spelled. Never invent new values. Common enums:

- **Decision**: `approve`, `conditional_approve`, `decline`, `defer`, `participation_required`
- **Condition**: `none`, `participation_required`, `reduced_amount`, `board_exception`, `sba_guaranty_required`, `startup_monitoring`
- **Payment status**: `Current`, `30 Days Past Due`, `60 Days Past Due`, `90+ Days Past Due`, `Nonaccrual`
- **Action**: `monitor`, `watchlist`, `special_assets`, `workout`, `partial_chargeoff_review`, `legal_referral`
- **Posture**: `continue_approving`, `continue_with_tighter_conditions`, `temporarily_pause`
- **Risk tolerance**: `restrained`, `moderate`, `expansive`
- **Capacity status**: `capacity_available`, `capacity_constrained`, `no_capacity`
- **External risk**: `stronger_than_national_and_peers`, `mixed_vs_national_and_peers`, `weaker_than_national_and_peers`

---

## Common Pitfalls

1. **Target population boundaries**: "Rating X or worse" means current_rating ≥ X (higher = worse). Double-check which ratings the task includes.

2. **Missing factors**: Loans with null DSCR, null LTV, and Current payment have no re-derivable factors — they keep their current rating but may need special handling in count/exposure totals.

3. **CRE vs sector exposure**: Branch-level CRE concentration uses `cre_policy_limit_pct` and sums loans with CRE loan types. Sector-level concentration uses `sector_ceiling_pct` and the sector_exposures table.

4. **Grandfathered sectors**: A sector with `grandfathered: 1` already exceeds its limit. New applications in that sector still require mitigation (participation or board exception) per the policy grandfathering note.

5. **Benchmark metric selection**: Match the FDIC metric to the loan type: `total_loans_noncurrent_pct` for overall NPA, `total_real_estate_noncurrent_pct` or `total_real_estate_30_89_pct` for real-estate-specific comparisons.

6. **NCUA direction semantics**: "Higher" for delinquency and loan-to-share means worse; "higher" for ROAA and positive-net-income means better. The direction values are simple greater-than/less-than comparisons — don't invert based on desirability.

7. **DSCR stress**: Only stress-test loans/applications where DSCR is available (not null). Sort results ascending by loan_id/application_id.

8. **Projected Loss override**: Even when the CDFI score is below 19 (e.g., 17), if the loan has ltv > 1.0 and is on nonaccrual status, the task may expect `Projected Loss` classification based on descriptive notes.

9. **Capacity arithmetic**: `gross_approved_amount` sums the face value of all approved (including conditional and participation). `committed_capacity_amount` reflects the bank's retained portion. `remaining_capacity = lending_capacity_q1 − committed_capacity_amount`.

10. **Conditions for declined/deferred applications**: Use an empty list `[]` or `["none"]` as specified by the template — check the template's conditions_enum for the correct sentinel.

11. **Priority ranking**: Include only `approve` and `conditional_approve` decisions unless the template explicitly includes `participation_required`. Order highest credit quality first.
