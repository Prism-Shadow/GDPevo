# Bank Branch Credit-Risk Lending-Committee Skill

## API Workflow

1. Start with `GET /api/manifest` to discover endpoints, benchmark versions, and record counts.
2. `GET /api/policies` for business rules: risk-rating thresholds, CDFI factor scores, CRE scoring weights, stress formulas, concentration policies.
3. Fetch target-branch data: `GET /api/branches/{id}` (metadata, limits), `GET /api/branches/{id}/metrics` (financials — use most recent quarter), `GET /api/branches/{id}/loans` (portfolio), `GET /api/branches/{id}/sector-exposures` (concentrations), `GET /api/branches/{id}/applications` (pending apps).
4. Benchmarks: `GET /api/benchmarks/fdic/q4-2024` and `GET /api/benchmarks/ncua/q1-2025`.
5. Credit-union segments: `GET /api/credit-union-segments/{id}`.
6. Use the base URL from `environment_access.md`; never hardcode localhost.

## Risk-Rating Rules

**Dominant-factor rule:** Final re-derived rating = **worst** (maximum numeric) rating from *available* DSCR, LTV/collateral, and delinquency factors. Skip null factors.

**DSCR thresholds:** ≥1.50→3, ≥1.25→4, ≥1.05→5, ≥1.00→6, <1.00→7

**LTV thresholds:** ≤0.65→3, ≤0.75→4, ≤0.85→5, ≤1.00→6, >1.00→7

**Delinquency minimums (floor):** 30 Days Past Due→4, 60 Days Past Due→5, 90+ Days Past Due→7, Nonaccrual→8, Current→no floor

**Material downgrade:** ≥2 notches worse (final_rating − current_rating ≥ 2).

## CDFI Factor Scoring (for Risk Classes)

| Factor | <0.40 / >720 / >12 | 0.40–0.60 / 680–720 / 6–12 | 0.60–0.80 / 580–679 / 3–6 | >0.80 / <580 / <3 |
|--------|---------------------|----------------------------|----------------------------|---------------------|
| debt_to_asset | 0 | 2 | 4 | 6 |
| fico | 0 | 1 | 3 | 5 |
| liquidity_months | 0 | 1 | 3 | 5 |
| ltv | 0 | 2 | 4 | 6 |

- Null factors contribute 0 to the total.
- **Classes:** 0–5→Prime, 6–9→Desirable, 10–13→Satisfactory, 14–18→Watch, ≥19→Doubtful, ≥19 *and* ltv>1.0→Projected Loss.

## CRE Weighted Score

**Weights:** capacity=0.45, capital=0.03, character=0.05, collateral_exposure=0.36, conditions=0.11. Lower score is better.

Score each dimension 1–5 (best to worst), then compute weighted sum.

**Classes:** ≤2.0→approve_quality, ≤3.0→conditional, >3.0→weak.

## Stress-Test Conventions

**Watch-list (+200bp):** `stressed_dscr = dscr / 1.18`, breach threshold = 1.00.

**CRE dual-stress:** `stressed_dscr = dscr × 0.85 / 1.18`, breach threshold = 1.00.

Shock label: `"+200bp"` (watch-list) or the compact formula string (CRE).

## Concentration Rules

- **Sector ceiling:** `branches.sector_ceiling_pct` (default) or per-sector `limit_pct` from sector-exposures.
- **CRE limit:** `branches.cre_policy_limit_pct`.
- **Denominator:** `total_loans_outstanding` from the most recent quarterly metrics (*not* including new approvals).
- **Post-approval pct:** (existing sector/CRE exposure + approved amounts) / total_loans_outstanding.
- **Over-limit mitigation:** `board_exception`, `participation_required`, or `reduced_amount`. Existing over-ceiling may be grandfathered; new approvals may not worsen that sector without mitigation.
- **NPA ratio:** `nonperforming_loans / total_loans_outstanding`.
- **Variance ratio:** branch_ratio − benchmark_ratio.
- **Variance bps:** variance_ratio × 10,000.

## Numeric Precision

| Type | Decimals |
|------|----------|
| Currency (USD) | 2 |
| Percentages / ratios | 4 |
| Basis points (bps) | 2 |
| Weighted CDFI score | 1 |
| NCUA integer values | as-reported (no decimals) |

## Sorting Conventions

- **final_rating_exposure_totals:** ascending by final_rating.
- **migration lists:** ascending by destination final_rating.
- **loan_ids within any list:** ascending.
- **material_downgrades:** ascending by loan_id.
- **by_action / conditions:** ascending alphabetically by action/condition name.
- **decisions:** ascending by application_id.
- **concentration_flags:** ascending by sector, then application_id.
- **post_approval_concentrations:** ascending by sector.
- **decline_reason_codes per app:** ascending alphabetically.
- **stress results:** ascending by loan_id / application_id.
- **workout_queue:** descending by exposure, then ascending by loan_id.
- **severe_bucket_counts:** ascending by current_rating, then payment_status (Current < 30DPD < 60DPD < 90+DPD < Nonaccrual).
- **peer_states:** ascending state_code.
- **escalation_triggers:** ascending trigger_id.
- **priority_ranking:** highest quality first (strongest credit).

## Key Enum Values

**payment_status:** Current, 30 Days Past Due, 60 Days Past Due, 90+ Days Past Due, Nonaccrual

**decision:** approve, conditional_approve, decline, defer, participation_required

**conditions:** participation_required, reduced_amount, board_exception, sba_guaranty_required, startup_monitoring, none

**recommended_action:** monitor, watchlist, special_assets, workout, partial_chargeoff_review, legal_referral

**reason_codes (decline):** capacity_limit, sector_breach, weak_dscr, high_ltv, low_fico, recent_bankruptcy, startup_risk, underwater_collateral, policy_floor_missing, documentation_gap, fdic_adverse_variance, ncua_peer_weakness

**unselected_reason_codes:** sector_breach, weak_dscr, high_ltv, fdic_adverse_variance

**posture:** continue_approving, continue_with_tighter_conditions, temporarily_pause

**risk_class:** Prime, Desirable, Satisfactory, Watch, Doubtful, Projected Loss

**monitoring_cadence:** monthly, quarterly, semiannual

**NPA benchmark_metric:** total_loans_noncurrent_pct (general), total_real_estate_noncurrent_pct, construction_development_noncurrent_pct

**CRE benchmark_metric:** total_real_estate_30_89_pct

## Common Pitfalls

1. **Delinquency is a floor, not standalone:** for 30DPD, rating must be ≥4; other factors can push it worse.
2. **Null factors are unavailable, not zero-rated:** skip them from the worst-of computation. When ALL rating factors (DSCR, LTV, delinquency) are null/unavailable, keep current_rating unchanged.
3. **Use the most recent metrics quarter** (typically Q1 2025) for total_loans_outstanding, nonperforming_loans, and delinquency rates.
4. **SBA guaranty does not reduce bank_capacity_used:** committed capacity = full approved_amount, not the bank's retained portion.
5. **Match benchmark metric to context:** NPA loans → total_loans_noncurrent_pct; CRE delinquency → total_real_estate_30_89_pct.
6. **Material downgrade is ≥2 notches,** not ≥1.
7. **Denominator for concentrations is current total_loans_outstanding,** not post-approval total.
8. **Sector limits:** branch sector_ceiling_pct is the default; individual sectors may have different limit_pct values in sector-exposures (e.g., Healthcare at 0.19 vs default 0.21).
9. **Conditions field is an array of strings** even when single-valued (e.g., `["none"]` or `["board_exception"]`).
10. **Priority ranking includes only approved and conditional_approve** applications, ordered by credit quality (strongest first).
11. **Weighted CDFI score is lower-is-better** (1=best, 5=worst per dimension).
12. **FDIC benchmark values** vary by metric — use the field matching the analysis context, not an arbitrary one.
13. **NCUA peer median** is the median of the specified peer_states, not the average.
14. **Outstanding balance is exposure** for loans; **requested_amount** is exposure for applications.
15. **Credit union segment data** comes from `/api/credit-union-segments/{id}`, not the branches endpoint.
