---
name: credit-office-analyst
description: Use when the user asks you to produce a committee-ready credit analysis, lending-committee packet, rating migration review, watch-list stress report, CRE competing-credit comparison, credit-union segment posture assessment, or any other structured lending or risk report that draws on a shared credit office REST API. This skill covers re-deriving risk ratings from policy thresholds, computing CDFI factor scores and risk classes, applying concentration limits and stress formulas, assembling allocation decisions with reason codes, and formatting results into controlled JSON templates. Use it whenever the task mentions branch-level loan portfolios, credit policy rules, FDIC or NCUA benchmarks, pending applications, sector exposures, watch-list or workout actions, or credit committee deliverables.
---

# Shared Credit Office Analyst

You are preparing a credit-analysis deliverable for a lending or risk
committee. The data you need lives in a shared credit office REST API.
Read the full policy first, then work outward through branch loans,
metrics, applications, sector exposures, and benchmarks as the specific
task requires.

## How to work with this API

The API base URL is always provided by the runner as `<TASK_ENV_BASE_URL>`.

### Always start here

Read these two endpoints before fetching any branch-specific data:

1. `GET <TASK_ENV_BASE_URL>/api/manifest` -- inventory of available data, policy version, seed, record counts.
2. `GET <TASK_ENV_BASE_URL>/api/policies` -- the credit policy for the current quarter. This defines risk-rating thresholds, CDFI factor scores and classes, concentration rules, stress formulas, and CRE weighted-score weights.

When you reach the policies endpoint, study every section:
- `risk_rating` -- the dominant-factor rule and numeric rating tables for DSCR, LTV, and delinquency minimums.
- `cdfi_factor_scores` -- per-factor tables (FICO, LTV, debt-to-asset, liquidity months) and the class ranges.
- `capacity_concentration` -- lending capacity field, sector ceiling field, and allowed mitigations.
- `stress` -- the watch-list and CRE dual-stress formulas and breach threshold.
- `cre_weighted_score` -- the five C weights, their weight values, and the score-class ranges.
- `policy_version` -- record this whenever the template asks for a benchmark or policy version string.

### Branch and segment data

- `GET <TASK_ENV_BASE_URL>/api/branches` -- all branches. The response includes each branch's `lending_capacity_q1`, `sector_ceiling_pct`, `cre_policy_limit_pct`, `institution_type`, and `fdic_benchmark_set`.
- `GET <TASK_ENV_BASE_URL>/api/branches/{branch_id}` -- single branch detail, plus `total_assets`.
- `GET <TASK_ENV_BASE_URL>/api/branches/{branch_id}/loans` -- all loans at that branch.
- `GET <TASK_ENV_BASE_URL>/api/branches/{branch_id}/metrics` -- quarterly metrics including `total_loans_outstanding`, `nonperforming_loans`, `delinquency_30_plus_pct`, and `net_charge_offs`.
- `GET <TASK_ENV_BASE_URL>/api/branches/{branch_id}/sector-exposures` -- per-sector current exposure, limit_pct, and grandfathered flag. The `limit_pct` here acts as a per-sector override of the branch's `sector_ceiling_pct`; where a sector has its own `limit_pct`, use it instead of the branch default.
- `GET <TASK_ENV_BASE_URL>/api/branches/{branch_id}/applications` -- pending applications with applicant details, financials, and credit metrics.
- `GET <TASK_ENV_BASE_URL>/api/credit-union-segments/{segment_id}` -- credit-union segment detail with internal context, peer states, quarterly capacity, checklist, and notes.

### Benchmarks

- `GET <TASK_ENV_BASE_URL>/api/benchmarks/fdic/q4-2024` -- a single object with five numeric fields. The benchmark version string is the JSON key `benchmark_version`.
- `GET <TASK_ENV_BASE_URL>/api/benchmarks/ncua/q1-2025` -- an object containing `benchmark_version` and a `rows` array of state-level metrics. State codes include `"US"` for national aggregates. Each row has `state_code`, `delinquency_bps`, `loan_to_share_pct`, `roaa_bps`, and `positive_net_income_pct`.

## Core credit rules you must apply

### Risk-rating re-derivation (dominant-factor rule)

When a task requires re-deriving risk ratings, always use the policy's dominant-factor rule: **the final rating is the worst (highest numeric) rating from DSCR, LTV, and delinquency factors.**

1. **DSCR rating**: Map the loan's `dscr` against the `risk_rating.dscr_thresholds` table. If `dscr` is missing (null), skip this factor.
2. **LTV rating**: Map the loan's `ltv` against the `risk_rating.ltv_thresholds` table. If `ltv` is missing (null), skip this factor.
3. **Delinquency minimum**: Map `payment_status` using the `risk_rating.delinquency_minimums` mapping. `"Current"` maps to `null` (no impact). Each status below that maps to an integer rating floor.

The final re-derived rating is `max(dscr_rating, ltv_rating, delinquency_floor)`, where any null factor is treated as a non-contributing 0. If all three factors are null, preserve the existing `current_rating`.

A material downgrade is any case where `final_rating - current_rating >= risk_rating.material_downgrade_notches` (typically 2).

### CDFI factor scores and risk classes

For tasks that require CDFI-style risk classification, compute an additive factor score from the four factors in `cdfi_factor_scores`:

- **FICO** (fico field): Map against the FICO score table.
- **LTV** (ltv field): Map against the LTV score table.
- **Debt-to-Asset** (debt_to_asset field): Map against that table.
- **Liquidity Months** (liquidity_months field): Map against that table.

Every factor with a null or missing value contributes 0 to the total. Sum the four scores, then assign a risk class from the `classes` table in `cdfi_factor_scores`:

- 0-5: Prime
- 6-9: Desirable
- 10-13: Satisfactory
- 14-18: Watch
- >=19 and ltv <= 1.0: Doubtful
- >=19 and ltv > 1.0: Projected Loss

### +200bp watch-list DSCR stress

For watch-list stress tasks, compute the stressed DSCR using the policy formula:

```
stressed_dscr = dscr / (1 + 0.18)
```

where 0.18 represents the +200bp parallel shock. The breach threshold is `stress.coverage_breach_threshold` (usually 1.0). A loan `breaches_threshold` when `stressed_dscr < breach_threshold`. Only loans that actually have a `dscr` value appear in stress results; skip loans where `dscr` is null.

The `shock_label` for this stress is `"+200bp"`.

### CRE dual-stress formula

For CRE comparison tasks, use the policy's CRE dual-stress formula exactly as written:

```
stressed_dscr = dscr * 0.85 / (1 + 0.18)
```

Record the formula string as the compact expression: `"dscr * 0.85 / 1.18"`.

### CRE weighted CDFI scoring

For CRE competing-credit tasks, compute a weighted score from the five C factors defined in `cre_weighted_score.weights`. Each factor is a binary 0 (satisfactory) or 1 (unsatisfactory):

| Factor | Weight | Unsatisfactory if |
|--------|--------|-------------------|
| capacity | 0.45 | dscr < 1.25 |
| collateral_exposure | 0.36 | ltv > 0.80 |
| conditions | 0.11 | loan_type is not CRE |
| character | 0.05 | fico < 680 (if fico missing, treat as satisfactory/0) |
| capital | 0.03 | debt_to_asset > 0.60 (if missing, treat as satisfactory/0) |

Weighted score = sum of (unsatisfactory_flag * weight) across all five factors. Lower is better.

Map the score to a class from `cre_weighted_score.classes`:
- <= 2.0: approve_quality
- <= 3.0: conditional
- > 3.0: weak

### Concentration rules

For tasks involving lending allocations and sector concentrations:

1. **Branch default sector limit**: `branches.sector_ceiling_pct`
2. **Per-sector override**: `sector-exposures.limit_pct` -- some sectors have their own ceiling (e.g. Healthcare might have 0.19 while the branch default is 0.21). Always use the sector-specific limit when present.
3. **CRE limit**: `branches.cre_policy_limit_pct` -- a separate ceiling for CRE loan concentration.
4. **Grandfathered exposure**: `sector-exposures.grandfathered` -- existing over-ceiling exposure may be grandfathered, but new approvals must not worsen that sector without mitigation.
5. **Concentration flag**: A concentration flag activates when `post_approval_pct > limit_pct` (for a sector that isn't grandfathered) or when `post_approval_pct > limit_pct AND grandfathered == 0` for any sector. The `handling` for a flagged concentration is determined by consulting `capacity_concentration.allowed_mitigations`.
6. **Post-approval concentration**: After allocating approvals, recompute each sector's exposure by adding the approved amounts of loans in that sector to the existing `current_exposure`, divide by `total_loans_outstanding` (from branch metrics, most recent quarter), and compare to the sector's `limit_pct`. Set `over_limit: true` when `post_approval_pct > limit_pct`.

7. **Allocation priority ranking**: Rank approved and conditionally-approved applications in priority order. Unless the task specifies a different ordering, use: highest priority goes to applications with the strongest credit metrics (highest DSCR, lowest LTV), and within ties, the largest relationship deposit balance or longest existing relationship.

### NPA benchmark variance

When computing NPA benchmark variance:
- `branch_npa_exposure` = `nonperforming_loans` from the most recent branch metrics quarter
- `branch_total_loans` = `total_loans_outstanding` from the same quarter
- `branch_npa_ratio` = `branch_npa_exposure / branch_total_loans`
- `fdic_benchmark_ratio` = the relevant FDIC benchmark field value
- `variance_ratio` = `branch_npa_ratio - fdic_benchmark_ratio`
- `variance_bps` = `variance_ratio * 10000`

Always use `"fdic_q4_2024"` as the benchmark version for FDIC comparisons and `"ncua_q1_2025"` for NCUA comparisons.

### Decline reason codes

When declining an application, assign reason codes from this controlled vocabulary, selecting the most specific codes that apply:

| Code | When to use |
|------|------------|
| `capacity_limit` | Remaining branch capacity cannot cover the request |
| `sector_breach` | Approval would push the sector over its concentration limit |
| `weak_dscr` | DSCR below 1.25 (or below policy minimum for loan type) |
| `high_ltv` | LTV above 0.80 |
| `low_fico` | FICO below 580 |
| `recent_bankruptcy` | `bankruptcy_months_ago` is not null and <= 36 |
| `startup_risk` | `years_in_business` < 2.0 |
| `underwater_collateral` | LTV > 1.0 |
| `policy_floor_missing` | Required policy floor (like DSCR min) not met |
| `documentation_gap` | `documentation_complete` is 0 (incomplete) |
| `fdic_adverse_variance` | Branch delinquency ratio exceeds FDIC benchmark by a material margin |
| `ncua_peer_weakness` | State metrics are materially weaker than peer or national benchmarks |

### Workout action assignment

When assigning recommended actions for watch-list or problem credits:

- `monitor`: Satisfactory or better risk class, no stress breach, payment current
- `watchlist`: Marginal credit (near policy floors) but still performing
- `special_assets`: Rating >= 7, or severe delinquency (90+), or breached stress with marginal DSCR
- `workout`: Rating >= 7 with breached DSCR
- `partial_chargeoff_review`: Nonaccrual, or rating 8, or Projected Loss risk class
- `legal_referral`: Nonaccrual with clear collateral deficiency and no cooperative borrower engagement

### Peer comparison for credit-union segments

For NCUA state-level comparisons:
- `peer_states`: The list from the credit-union segment endpoint.
- Compute the **peer median** for each metric by taking the median of the peer states' values. If an even number of peer states, use the lower median.
- Compare NC's value to US and to peer median, assigning `"higher"`, `"lower"`, or `"equal"` for each metric. Use `"equal"` only when values are exactly identical.

## Answer template discipline

Every task includes an `input/payloads/answer_template.json` that defines the required JSON output shape. Do these things for every task:

1. **Read the template first.** It contains required top-level keys, field types, enum choices, ordering rules, and numeric precisions. The template is authoritative -- use its enum values, key names, and structure exactly.
2. **Preserve enum values.** When the template specifies `allowed_values` or `choices`, use only those strings. Do not invent your own.
3. **Follow ordering rules.** Sort lists as directed (e.g. "ascending by loan_id", "ascending by sector then application_id"). Use stable, deterministic sorts.
4. **Honor numeric precision.** Round to the stated number of decimal places. Currency fields round to 2 decimals unless the template says otherwise. Percentage fields expressed as ratios round to 4 decimals. Basis points round to 2 decimals.
5. **Return only valid JSON.** No narrative text, no markdown fences around the JSON, no trailing commentary. If the prompt says "Return a single JSON object" or "Write your response as JSON", the entire response body is pure JSON.
6. **Include every required key.** Required keys in the template must appear in the output even if their value is an empty list or 0. The template's `required_top_level_keys` are the minimum set; all nested `required_keys` must also be present.

## General workflow

For any credit-office task, follow this sequence:

1. Read the prompt and the answer template together. Understand what deliverable is being asked for.
2. Fetch the manifest and policies.
3. Identify which branch(es) or segment(s) are needed. Fetch their details.
4. Determine which supporting data is needed (loans, metrics, applications, sector exposures, benchmarks). Fetch all of it in parallel where possible.
5. Apply the relevant credit rules from this skill to compute derived values (risk ratings, scores, stresses, concentrations, comparisons).
6. Build the JSON answer by walking the template structure and populating every key with computed or fetched data.
7. Validate that all enum values match the template, all sorts are correct, and all numeric precisions are honored.
8. Output only the JSON.

## Reference documents

- [references/policy-translation.md](references/policy-translation.md) -- Detailed translation of policy JSON into concrete rule tables and formulas.
- [references/answer-patterns.md](references/answer-patterns.md) -- Patterns extracted from the train answers that show how rules translate into JSON structure.
