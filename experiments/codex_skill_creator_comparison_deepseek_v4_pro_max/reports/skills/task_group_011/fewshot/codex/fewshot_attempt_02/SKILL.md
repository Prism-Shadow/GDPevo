---
name: credit-risk-committee
description: Prepare credit risk committee packets using a shared credit office REST API. Use when Codex needs to produce branch rating migration reviews, lending-committee allocation decisions, watch-list stress packets, competing CRE decisions, or credit-union segment posture pages from the task environment API.
---

# Credit Risk Committee

Use the shared credit office public API to prepare structured committee-ready JSON answers for branch reviews, allocation decisions, stress tests, and segment posture analysis.

## Quick Start

Every task starts the same way:

1. Fetch manifest and policies in parallel.
2. Read the supplied `answer_template.json` to know the required output shape.
3. Fetch branch details, loans, metrics, sector-exposures, and benchmarks as needed.
4. Apply policy rules to derive ratings, scores, stress results, and decisions.
5. Output valid JSON conforming to the template.

## API Endpoints

The base URL arrives as `<TASK_ENV_BASE_URL>`. All endpoints are GET-only. Call them with `curl -s` and pipe through `python3 -m json.tool` for readability. Use `python3 -c` for inline computation.

Always fetch in parallel where possible. The manifest and policies are needed for every task.

### Always Available

- `GET /api/manifest` -- record counts, versions, branches list
- `GET /api/policies` -- risk-rating thresholds, CDFI factor scores, stress formulas, CRE weights, concentration rules, enums
- `GET /api/benchmarks/fdic/q4-2024` -- five FDIC benchmark ratios
- `GET /api/benchmarks/ncua/q1-2025` -- per-state NCUA benchmarks with US national row

### Branch-Scoped

- `GET /api/branches/{branch_id}` -- lending_capacity_q1, sector_ceiling_pct, cre_policy_limit_pct, total_assets, state_code
- `GET /api/branches/{branch_id}/metrics` -- total_loans_outstanding, nonperforming_loans, delinquency_30_plus_pct
- `GET /api/branches/{branch_id}/loans` -- current_rating, dscr, ltv, fico, payment_status, debt_to_asset, liquidity_months, sector, outstanding_balance
- `GET /api/branches/{branch_id}/sector-exposures` -- sector-level exposure, limit_pct, grandfathered
- `GET /api/branches/{branch_id}/applications` -- pending applications with financial inputs

### Credit Union Segment

- `GET /api/credit-union-segments/{segment_id}` -- segment profile, quarterly_capacity, peer_states, risk_tolerance, minimum_checklist

## Core Business Rules

See [references/policies.md](references/policies.md) for the complete rule reference. Key rules to apply:

### Risk Rating Re-derivation

The final rating is the **worst (highest numeric)** from three independent factors. Apply only where data exists:

- **DSCR**: >=1.50 -> 3, >=1.25 -> 4, >=1.05 -> 5, >=1.00 -> 6, <1.00 -> 7
- **LTV**: <=0.65 -> 3, <=0.75 -> 4, <=0.85 -> 5, <=1.00 -> 6, >1.00 -> 7
- **Delinquency**: 30 Days -> 4, 60 Days -> 5, 90+ Days -> 7, Nonaccrual -> 8 (Current -> no factor)

Null dscr/ltv omit that factor. `final_rating = max(available factor ratings)`.

### CDFI Factor Scoring

Sum scores from 4 factors (0, 1, 3, or 5 each; see [references/policies.md](references/policies.md) for full table). Classify: Prime 0-5, Desirable 6-9, Satisfactory 10-13, Watch 14-18, Doubtful >=19, Projected Loss >=19 with ltv>1.0.

### CRE Weighted Scoring

`0.45*capacity + 0.03*capital + 0.05*character + 0.36*collateral_exposure + 0.11*conditions`. Each component 1-5. <=2.0 approve_quality, <=3.0 conditional, >3.0 weak.

### Stress Formulas

- **Watch-list +200bp**: `stressed_dscr = dscr / 1.18` (breach < 1.0)
- **CRE dual-stress**: `stressed_dscr = dscr * 0.85 / 1.18` (breach < 1.0)

### Concentration

Sector exposure / branch total_loans_outstanding. Compare to sector_ceiling_pct (general) or cre_policy_limit_pct (CRE). Grandfathered sectors may already exceed; new approvals may not worsen without mitigation. Variance bps: `(actual - limit) * 10000`.

### NPA Benchmark

`branch_npa_ratio = nonperforming_loans / total_loans_outstanding`. Variance: `ratio - fdic_benchmark`. BPS: `variance * 10000`.

### Watch-List Actions

Assign: monitor, watchlist, special_assets, workout, partial_chargeoff_review, legal_referral. Ratings >=7 with nonaccrual or breached DSCR warrant special_assets or stronger.

### Material Downgrades

`final_rating - current_rating >= 2`. List sorted by loan_id.

## Task Patterns

### Rating Migration Review

1. Fetch branch, metrics, loans, sector-exposures, policies, FDIC benchmark.
2. Filter loans where `current_rating >= target_min`.
3. Re-derive each loan rating. Sum exposure by final_rating.
4. Track migration for loans originally at target_min.
5. Assign watch-list actions to loans with final_rating >=6 or breached DSCR.
6. Compute NPA benchmark variance.
7. List material downgrades (>=2 notches).
8. Top problem credit: highest final_rating, then largest exposure.

### Lending Allocation

1. Fetch branch, metrics, sector-exposures, applications, policies.
2. Prioritize: DSCR, relationship_years, sector headroom, credit quality.
3. Allocate from lending_capacity_q1; track cumulative usage.
4. Decline reasons: weak_dscr when <1.05, high_ltv when >0.85, low_fico when <580, startup_risk when years_in_business <2, capacity_limit when exhausted, recent_bankruptcy, sector_breach when post-approval exceeds limit.
5. Flag sectors at or over limit_pct.
6. Post-approval concentrations: existing + approved.

### Watch-List Stress

1. Fetch branch, loans, policies.
2. Filter loans with `current_rating >= 6`.
3. Score CDFI risk class per adverse loan.
4. Apply +200bp DSCR stress. Breach when stressed_dscr < 1.0.
5. Workout queue sorted by descending exposure.
6. Assign recommended_action by severity.
7. Severe bucket counts: group by current_rating + payment_status.

### Competing CRE Decision

1. Fetch branch, metrics, loans, sector-exposures, target applications, policies, FDIC benchmark.
2. CRE weighted score per application.
3. CRE dual-stress formula.
4. CRE exposure and post-approval concentration vs cre_policy_limit_pct.
5. FDIC delinquency benchmark vs branch delinquency.
6. Recommend stronger credit; decline/defer unselected with reason codes.
7. List conditions for selected credit.

### Segment Posture

1. Fetch segment data, NCUA benchmarks.
2. Compare state to US national and peer medians.
3. Posture: continue, continue_with_tighter_conditions, or pause.
4. Escalation triggers from internal_context.
5. Interpretation: capacity_status, external_risk_status, risk_tolerance, committee_message.

## Guardrails

- Round currency to 2 decimals, ratios to 4 decimals.
- Sort as specified: ascending loan_id, application_id, rating, sector.
- Use only enum values from policies or template. No invented codes.
- Null factors are omitted, not guessed.
- Branch-scoped data only; do not merge across branches.
- Output only valid JSON matching the template. No narrative text.
