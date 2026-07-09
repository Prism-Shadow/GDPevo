# Bank Branch Credit-Risk Lending Committee Skill

## API Usage

- **Base URL**: `http://34.46.77.124:8011` (from `environment_access.md` — ALWAYS override localhost references)
- **Start**: `GET /api/manifest` and `GET /api/health` to confirm connectivity and see record counts
- **Key endpoints**:
  - `GET /api/branches` — all branches (id, state, ceilings, capacity)
  - `GET /api/branches/{id}` — single branch detail
  - `GET /api/branches/{id}/metrics` — quarterly metrics (NPA, deposits, delinquency, charge-offs)
  - `GET /api/branches/{id}/loans` — loan portfolio with ratings, DSCR, LTV, FICO, payment status
  - `GET /api/branches/{id}/sector-exposures` — per-sector exposure, limit_pct, grandfathered flag
  - `GET /api/branches/{id}/applications` — pending applications
  - `GET /api/policies` — credit policy (ratings, CDFI, CRE score, stress, concentration rules)
  - `GET /api/benchmarks/fdic/q4-2024` — FDIC benchmark ratios
  - `GET /api/benchmarks/ncua/q1-2025` — NCUA state-level benchmarks
  - `GET /api/credit-union-segments/{segment_id}` — CU segment details, peer states, controls

## Risk Rating Re-derivation (Dominant Factor Rule)

For ANY loan, re-derive the **final_rating** as the **worst (highest numeric)** rating from THREE factors:

### Factor 1: DSCR Thresholds
| DSCR Range | Rating |
|------------|--------|
| >= 1.50       | 3 |
| >= 1.25       | 4 |
| >= 1.05       | 5 |
| >= 1.00       | 6 |
| < 1.00        | 7 |
| **null / missing** | **skip — no contribution** |

### Factor 2: LTV / Collateral Thresholds
| LTV Range | Rating |
|-----------|--------|
| <= 0.65       | 3 |
| <= 0.75       | 4 |
| <= 0.85       | 5 |
| <= 1.00       | 6 |
| > 1.00        | 7 |
| **null / missing** | **skip — no contribution** |

### Factor 3: Delinquency Floor (from payment_status)
| Payment Status | Minimum Rating |
|----------------|---------------|
| Current | `null` (no floor) |
| 30 Days Past Due | 4 |
| 60 Days Past Due | 5 |
| 90+ Days Past Due | 7 |
| Nonaccrual | 8 |

**Final rating** = `max(rating_dscr ?? 0, rating_ltv ?? 0, rating_delinquency ?? 0)`. Skip null factors. If ALL three factors are null/missing, keep the existing current_rating.

### Material Downgrade
A downgrade is **material** when `final_rating - current_rating >= 2` notches.

## CDFI Factor Scoring (for watch-list / workout tasks)

Score each loan on 4 objective factors, then sum for total factor_score. Score null/missing factors as 0.

| Factor | Range | Score |
|--------|-------|-------|
| **FICO** | >720 / 680-720 / 580-679 / <580 / null | 0 / 1 / 3 / 5 / 0 |
| **LTV** | <0.40 / 0.40-0.60 / 0.60-0.80 / >0.80 / null | 0 / 2 / 4 / 6 / 0 |
| **Debt-to-Asset** | <0.40 / 0.40-0.60 / 0.60-0.80 / >0.80 / null | 0 / 2 / 4 / 6 / 0 |
| **Liquidity (months)** | >12 / 6-12 / 3-6 / <3 / null | 0 / 1 / 3 / 5 / 0 |

**Risk Class from factor_score total:**
| Score | Class |
|-------|-------|
| 0-5 | Prime |
| 6-9 | Desirable |
| 10-13 | Satisfactory |
| 14-18 | Watch |
| >=19 AND ltv<=1.0 | Doubtful |
| >=19 AND ltv>1.0 | Projected Loss |

**Projected Loss** field in workout queue: `true` when risk class is "Projected Loss", otherwise `false`.

## CRE Weighted Scoring (for competing CRE decisions)

Five components, each scored 1-3 (lower is better), multiplied by weights:

| Component | Weight | Typically derived from |
|-----------|--------|------------------------|
| capacity | 0.45 | lending capacity available, debt service coverage |
| capital | 0.03 | net worth, collateral cushion |
| character | 0.05 | FICO, relationship years, prior delinquencies |
| collateral_exposure | 0.36 | LTV, sector exposure vs limit |
| conditions | 0.11 | loan type, term, rate environment |

**Score = sum(component_score × weight)**. Rounded to 1 decimal.

**Score classes:** ≤2.0 → approve_quality, ≤3.0 → conditional, >3.0 → weak.

Default scoring logic (reasonable inferences from loan/application data):
- **capacity**: dscr>=1.50→1, >=1.25→2, <1.25→3 (or if docs incomplete → 3)
- **capital**: ltv<=0.60→1, <=0.80→2, >0.80 or null→3
- **character**: fico>720→1, 680-720→2, <680 or null→3; demote if prior_delinquencies>0 or existing_relationship_years<2
- **collateral_exposure**: sector current_exposure/sector_limit well within→1, near ceiling→2, over or close→3
- **conditions**: full docs_and_strong_purpose→1, incomplete_docs→2, adverse_terms→3

## Stress Testing

### Watch-List +200bp DSCR Stress (Summit style)
Formula: `stressed_dscr = dscr / (1 + 0.18)`
Breach threshold: `1.00` (breaches when stressed_dscr < 1.00)
Only apply to loans where DSCR is available (non-null).

### CRE Dual-Stress (Harbor competing CRE style)
Formula: `stressed_dscr = dscr * 0.85 / (1 + 0.18)`
Breach threshold: `1.00` (breaches when stressed_dscr < 1.00)

Label the watch-list shock as `"+200bp"` and the CRE formula as `"dscr*0.85/(1+0.18)"`.

## NPA Benchmark Variance (FDIC)

From metrics endpoint, use the **most recent quarter** (typically 2025Q1).

`branch_npa_ratio = branch_npa_exposure / branch_total_loans` (both from metrics)

Which FDIC metric and benchmark to use depends on the review type:
- For general portfolio: `total_loans_noncurrent_pct` (0.0098)
- For real-estate focused: `total_real_estate_noncurrent_pct` (0.0121)
- For construction: `construction_development_noncurrent_pct` (0.0076)
- For delinquency (30-89 day): `total_real_estate_30_89_pct` (0.0051)

`variance_ratio = branch_npa_ratio - fdic_benchmark_ratio`
`variance_bps = variance_ratio * 10000` (rounded to 2 decimals)

All ratios should be in **decimal form** (e.g., 0.0121 for 1.21%), precision 4 for ratios, precision 2 for bps and currency.

## Concentration Rules

### Sector Concentration
- Each sector has a `limit_pct` (from sector-exposures or branch.sector_ceiling_pct as default)
- `current_exposure_pct = sector_exposure / branch.total_loans_outstanding` (use metrics 2025Q1 total_loans)
- A sector is **over limit** when `current_exposure_pct > limit_pct`
- However, **grandfathered** sectors (grandfathered=1) — existing over-ceiling exposure may be grandfathered, but new approvals MUST NOT worsen it without mitigation
- After approving an application in a sector, recalculate: `post_approval_pct = (sector_exposure + approved_amount) / total_loans`

### CRE-Specific Concentration
- `cre_policy_limit_pct` from branch detail
- `existing_cre_exposure` = sum of outstanding balances for all loans with loan_type "CRE"
- `existing_cre_concentration = existing_cre_exposure / total_loans_outstanding`
- `selected_post_approval_cre_concentration = (existing_cre_exposure + selected_app_amount) / total_loans_outstanding`
- `selected_policy_variance_bps = (selected_post_approval_cre_concentration - cre_policy_limit_pct) * 10000`

### Lending Capacity
- `lending_capacity_q1` is the branch's Q1 capacity
- `committed_capacity_amount` = sum of approved amounts for all approved/conditional applications
- `remaining_capacity = lending_capacity_q1 - committed_capacity_amount`
- `bank_capacity_used` per application = `approved_amount` if approved, 0 if declined
- All capacity and exposure fields: precision 2, units USD

### Application Mitigations (from policy)
Allowed mitigations for concentration breaches: `participation_required`, `reduced_amount`, `board_exception`

## Application Decision Logic

### Decision Values (enum)
`approve`, `conditional_approve`, `decline`, `defer`, `participation_required`

### Conditions (enum)
`participation_required`, `reduced_amount`, `board_exception`, `sba_guaranty_required`, `startup_monitoring`, `none`

### Decline Reason Codes
`capacity_limit`, `sector_breach`, `weak_dscr`, `high_ltv`, `low_fico`, `recent_bankruptcy`, `startup_risk`, `underwater_collateral`, `policy_floor_missing`, `documentation_gap`, `fdic_adverse_variance`, `ncua_peer_weakness`

### Priority Ranking
Sorted list of application_ids from highest to lowest priority among **approved and conditionally approved** only. Prioritize by: strongest DSCR → lowest LTV → strongest FICO → most relationship years.

### Decision Heuristics
- **approve**: meets all credit metrics (DSCR≥1.25, LTV≤0.80, FICO≥680), no sector breach, capacity available
- **conditional_approve**: meets most metrics but has a mitigatable weakness (sector near ceiling, startup risk, thin DSCR≥1.05), needs conditions like `sba_guaranty_required` or `reduced_amount`
- **decline**: multiple adverse factors (DSCR<1.0, LTV>1.0, FICO<580, recent bankruptcy, sector breach with no mitigation)
- **defer**: documentation incomplete, missing key data
- **participation_required**: credit quality is acceptable but branch lacks capacity or sector ceiling breached — use participation

## Credit Union Segment Posture

### Posture Choices
`continue_approving`, `continue_with_tighter_conditions`, `temporarily_pause`

### State Benchmark Metrics (from NCUA)
- `delinquency_bps`: integer as reported
- `loan_to_share_pct`: integer as reported
- `roaa_bps`: integer as reported
- `positive_net_income_pct`: integer as reported

### Peer Comparison
For each metric, compare NC's value to the comparison (peer median or US):
- `higher` / `lower` / `equal`

NCUA "US" row represents national values. Peer median is the median of the segment's peer_states values.

### Controls
**Required checklist gates** (from segment minimum_checklist plus constraints): `board_authorization`, `equipment_invoice`, `fleet_replacement_plan`, `payer_contract_summary`, `public_contract_or_tax_support`, `proof_of_insurance`, `ucc_or_title_lien`

**Added operating controls** based on segment risk: `pre_close_insurance_binder_verification`, `lien_perfection_prior_to_funding`, `senior_underwriter_second_review`, `quarterly_state_benchmark_monitoring`, `monthly_segment_delinquency_watch`, `committee_exception_for_capacity_overrun`

### Escalation Triggers
Match conditions to owners:
- `segment_recent_delinquency_ge_90_bps` → `credit_risk_manager`
- `missing_insurance_or_lien_exception` → `operations_control_manager`
- `quarterly_capacity_exceeded_or_exception_requested` → `lending_committee_chair`
- `state_delinquency_gap_widens_25_bps` → `credit_risk_manager`

### Interpretation
- `capacity_status`: `capacity_available` if remaining capacity > 0, `capacity_constrained` if near limit, `no_capacity` if exhausted
- `external_risk_status`: compare NC to national and peers on delinquency and ROAA — `stronger_than_national_and_peers`, `mixed_vs_national_and_peers`, `weaker_than_national_and_peers`
- `risk_tolerance`: from segment or policy — `restrained`, `moderate`, `expansive`
- `committee_message`: `routine_approval_path_supported`, `capacity_available_but_external_risk_weaker`, `pause_until_state_metrics_recover`

## Watch-List Actions Enum
`monitor`, `watchlist`, `special_assets`, `workout`, `partial_chargeoff_review`, `legal_referral`

Escalation mapping (by risk severity):
- Prime → `monitor`
- Desirable → `monitor`
- Satisfactory → `monitor`
- Watch → `watchlist`
- Doubtful → `workout` or `special_assets`
- Projected Loss → `partial_chargeoff_review` or `legal_referral`
- Nonaccrual payment status → escalate one tier higher
- 90+ Days Past Due → `special_assets` minimum

### Payment Status Enum
`Current`, `30 Days Past Due`, `60 Days Past Due`, `90+ Days Past Due`, `Nonaccrual`

## Sorting / Ordering Conventions (CRITICAL — the templates enforce these)

| Field | Sort Order |
|-------|-----------|
| final_rating_exposure_totals | ascending final_rating |
| migration buckets | ascending final_rating |
| loan_ids within any list | ascending lexicographic |
| application decisions | ascending application_id |
| concentration_flags | sector then application_id ascending |
| post_approval_concentrations | sector ascending |
| material_downgrades | loan_id ascending |
| risk_classes | loan_id ascending |
| stress results | loan_id ascending (DSCR-available only) |
| breach_loan_ids | loan_id ascending |
| workout_queue | **descending exposure**, then ascending loan_id |
| severe_bucket_counts | current_rating ascending, then payment_status ascending |
| applications_compared (CRE) | application_id ascending |
| reason_codes (lists) | **alphabetically ascending** |
| conditions list | alphabetically ascending |
| priority_ranking | highest priority first (by credit quality: DSCR desc, LTV asc, FICO desc) |
| peer_states | state_code ascending |
| escalation_triggers | trigger_id ascending |

## Rounding / Precision Rules

| Field Type | Precision | Example |
|-----------|-----------|---------|
| Currency (USD, exposure, balance, capacity) | 2 decimals | 1151319.25 |
| Ratios (DSCR, LTV, concentration, NPA, variance_ratio) | 4 decimals | 0.0121 |
| Basis points (bps) | 2 decimals | 121.00 |
| Weighted CRE score | 1 decimal | 2.3 |
| Factor scores, notches, counts | integer | 7 |
| NCUA benchmark metrics | integer (as reported) | 79 |
| Percentages in concentration flags | ratio, 4 decimals | 0.2200 |

## Common Pitfalls

1. **Delinquency floor applies even when DSCR/LTV are strong** — a 90+ Days Past Due loan with great DSCR still gets a rating floor of 7
2. **Null factors are SKIPPED, not scored as 0** — if only payment_status is "Current" (no floor) and DSCR/LTV are both null, keep the existing rating; don't force it to 0
3. **Nonaccrual is rating-8 floor**, not 7 — per the delinquency minimums table
4. **FDIC benchmarks are in decimal form** — multiply by 10000 for bps comparisons, not 100
5. **CRE concentration uses CRE loan_type only**, not all real estate loans — check total CRE balance, not just sector
6. **Grandfathered sectors** can remain over-limit but new approvals must not increase the breach
7. **Sector limit_pct varies per sector** — check sector-exposures, don't blindly use branch.sector_ceiling_pct for every sector
8. **DSCR stress ONLY applies to loans where DSCR is available** — skip null-DSCR loans in stress_results list
9. **Material downgrade is >= 2 notches** — downgrades of exactly 1 notch are NOT material
10. **Projected Loss requires both factor_score >= 19 AND ltv > 1.0** — if only one condition meets, it's Doubtful
11. **bank_capacity_used = 0 for declined/deferred applications**, not the requested amount
12. **Watch-list formula uses `/(1+0.18)`**, while CRE dual-stress uses `*0.85/(1+0.18)` — they are different
13. **The `by_action` array in watch_list_action_coverage** must use action enum values: monitor, watchlist, special_assets, workout, partial_chargeoff_review, legal_referral
14. **For competing CRE**: only ONE application gets selected; the unselected gets disposition "decline" or "defer" with reason codes from the unselected_reason_codes enum (sector_breach, weak_dscr, high_ltv, fdic_adverse_variance)
15. **Answer template enums are EXACT** — never invent values; use only what the template or policy allows
