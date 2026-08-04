## Credit Risk Committee Analysis

This skill covers assembling committee-ready credit risk reports using the shared credit office public API. It encodes the reusable patterns observed across rating migration reviews, lending-committee allocation packages, credit-union segment posture pages, watch-list stress packets, and competing CRE decisions.

### API Data Sources

The base URL is provided by the runner as `<TASK_ENV_BASE_URL>`. All endpoints are read-only GET unless noted. Do not use `/api/health`, reset/reseed, evaluator, or judge endpoints. Replace `{branch_id}` and `{segment_id}` with the identifiers from the task input.

| Endpoint | Use |
|---|---|
| `/api/manifest` | Lists available data, benchmark versions, and record counts. |
| `/api/policies` | Credit policy rules: risk rating thresholds, CDFI factor scores, CRE weighted score weights, stress formulas, capacity/concentration rules. Always fetch first. |
| `/api/branches` | All branch metadata (lending capacity, sector ceiling, CRE policy limit, state, institution type). |
| `/api/branches/{branch_id}` | Single branch detail. |
| `/api/branches/{branch_id}/metrics` | Quarterly metrics: delinquency, NPA, total loans outstanding, total deposits. |
| `/api/branches/{branch_id}/loans` | Loan portfolio with current rating, DSCR, LTV, payment status, collateral value, DTA, FICO, liquidity months, sector. |
| `/api/branches/{branch_id}/sector-exposures` | Per-sector current exposure, limit_pct, grandfathered flag. |
| `/api/branches/{branch_id}/applications` | Pending applications with DSCR, LTV, FICO, sector, requested amount, co-guarantor strength, years in business, bankruptcy history. |
| `/api/benchmarks/fdic/q4-2024` | FDIC benchmark ratios for NPA and delinquency comparisons. |
| `/api/benchmarks/ncua/q1-2025` | NCUA state-level benchmark rows for credit union segment analysis. |
| `/api/credit-union-segments/{segment_id}` | Segment profile: portfolio focus, peer states, minimum checklist, quarterly capacity, risk tolerance, internal context. |

### Risk Rating Re-Derivation

When re-deriving loan risk ratings, apply the `risk_rating` rules from `/api/policies`:

1. **Delinquency minimums** set a floor rating based on payment status:
   - 30 Days Past Due → 4
   - 60 Days Past Due → 5
   - 90+ Days Past Due → 7
   - Nonaccrual → 8
   - Current → no floor (null)

2. **DSCR thresholds** assign a rating from the DSCR value:
   - ≥1.50 → 3 | ≥1.25 → 4 | ≥1.05 → 5 | ≥1.00 → 6 | <1.00 → 7

3. **LTV thresholds** assign a rating from the LTV value:
   - ≤0.65 → 3 | ≤0.75 → 4 | ≤0.85 → 5 | ≤1.00 → 6 | >1.00 → 7

4. **Dominant factor rule**: The final re-derived rating is the highest (worst) numeric rating among all available DSCR, LTV, and delinquency factor ratings. If a factor is null/missing, skip it. If no factors are available, retain the current rating.

5. **Material downgrades** are defined as downgrades of ≥2 notches (final − current ≥ 2). The threshold is in the policy under `risk_rating.material_downgrade_notches`.

### CDFI Risk Class Assignment

Use the `cdfi_factor_scores` from `/api/policies` to compute a composite score and risk class:

**Factor scoring** (score 0 = best):
- FICO: >720 → 0 | 680–720 → 1 | 580–679 → 3 | <580 → 5 | null → 0
- LTV: <0.40 → 0 | 0.40–0.60 → 2 | 0.60–0.80 → 4 | >0.80 → 6 | null → 0
- Debt-to-Asset: <0.40 → 0 | 0.40–0.60 → 2 | 0.60–0.80 → 4 | >0.80 → 6 | null → 0
- Liquidity months: >12 → 0 | 6–12 → 1 | 3–6 → 3 | <3 → 5 | null → 0

**Risk class from total score**:
- 0–5 → Prime
- 6–9 → Desirable
- 10–13 → Satisfactory
- 14–18 → Watch
- ≥19 → Doubtful
- ≥19 AND LTV > 1.0 → Projected Loss

Additionally, any loan with Nonaccrual payment status AND LTV > 1.0 (underwater collateral) should be treated as Projected Loss regardless of factor score.

### Stress Testing

Two stress formulas are defined in `policies.stress`:

**CRE dual-stress** (for CRE applications/decisions):
```
stressed_dscr = dscr × 0.85 / (1 + 0.18)
```
Breach threshold: 1.0 (from `coverage_breach_threshold`).

**Watch-list +200bp parallel shock** (for adversely rated loan watch lists):
```
stressed_dscr = dscr / (1 + 0.18)
```
Breach threshold: 1.0. Only apply to loans where DSCR is available.

### Concentration and Sector Limits

- Each branch has a `sector_ceiling_pct` as a default limit. Individual sectors may override this in `/api/branches/{branch_id}/sector-exposures` via their `limit_pct`.
- CRE concentration uses `cre_policy_limit_pct` from the branch.
- Compute concentration as: `(current_exposure + new_amount) / total_loans_outstanding`.
- Over-limit sectors may be grandfathered, but new approvals that worsen an already-over sector require mitigation (`participation_required`, `reduced_amount`, or `board_exception`).
- Variance in basis points = (concentration − limit) × 10,000.

### FDIC Benchmark Comparison

The FDIC Q4 2024 benchmark provides these ratios:
- `total_loans_noncurrent_pct` — for overall NPA comparison
- `total_real_estate_noncurrent_pct` — for real-estate NPA
- `total_real_estate_30_89_pct` — for delinquency comparison
- `construction_development_noncurrent_pct` — for construction NPA

Select the metric most relevant to the task context. Compute:
- Branch ratio = branch metric / branch total loans
- Variance ratio = branch ratio − FDIC benchmark ratio
- Variance bps = variance ratio × 10,000

### NCUA Benchmark and Peer Comparison

For credit union segment analysis, fetch `/api/benchmarks/ncua/q1-2025`. Each row contains `state_code`, `delinquency_bps`, `loan_to_share_pct`, `roaa_bps`, `positive_net_income_pct`. Compute peer median from the segment's `peer_states` list. Compare the target state to both US row and peer median using "higher"/"lower"/"equal".

### Workout Action Assignment

Assign recommended actions based on risk class and payment status:
- Projected Loss → `partial_chargeoff_review`
- Nonaccrual payment status → `legal_referral`
- Doubtful → `workout`
- 90+ or 60 Days Past Due → `workout`
- Watch → `special_assets`
- Desirable / Satisfactory / Prime → `special_assets` (for adverse-rated populations) or `monitor` (for rating migration reviews)
- For rating migration reviews on loans rated 3+: use `monitor` for final ratings 3–4, `watchlist` for 5, `special_assets` for 6, `workout` for 7, `legal_referral` for 8/Nonaccrual.

### JSON Output Rules

1. Match the `answer_template.json` shape exactly. Every required key must be present.
2. Sort lists as specified: by `application_id` ascending, by `loan_id` ascending, by `sector` then `application_id`, etc.
3. Use only enum values from the template and policy. Do not invent new values.
4. All currency amounts must be rounded to 2 decimal places.
5. Percentages and ratios must match the specified precision (4 decimal places for ratios, 2 for bps).
6. Sort `loan_ids` arrays in ascending order.
7. For `reason_codes` arrays, sort alphabetically in ascending order.
8. For `conditions` arrays, sort alphabetically in ascending order.

### Task Type Recognition

Identify the task type from the prompt and template shape:

- **Rating migration review** (template has `portfolio_regrade`, `material_downgrades`, `top_problem_credit`): Filter loans by `current_rating ≥ target_current_rating_min`, re-derive ratings, compute migration, identify material downgrades, select top problem credit.
- **Lending committee allocation** (template has `allocation`, `decisions`, `concentration_flags`): Evaluate applications against capacity and sector limits, assign decisions, flag concentration breaches, provide decline reasons.
- **Credit union segment posture** (template has `posture`, `state_metrics`, `peer_comparison`, `escalation_triggers`): Use segment profile and NCUA benchmarks to recommend posture, controls, triggers, and interpretation.
- **Watch-list stress** (template has `watch_list_summary`, `stress_results`, `workout_queue`, `severe_bucket_counts`): Filter by adverse rating threshold, assign CDFI risk classes, run watch-list stress, queue workouts, bucket by rating and payment status.
- **Competing CRE decision** (template has `applications_compared`, `recommended_path`, `stress`, `concentration`): Compare exactly two applications using CDFI scoring, CRE dual-stress, and concentration analysis. Select the stronger credit and provide reason codes for the unselected.
