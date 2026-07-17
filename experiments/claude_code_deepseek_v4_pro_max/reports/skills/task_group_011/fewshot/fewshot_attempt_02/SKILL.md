# Bank Branch Credit-Risk Lending Committee — SKILL

## Environment

Base URL: `http://34.46.77.124:8011`. Never use `localhost`/`127.0.0.1` or run `env/setup.sh`.

## API Workflow

1. **Discover**: `GET /api/manifest` → `GET /api/health`
2. **Branch data**: `GET /api/branches`, `GET /api/branches/{id}`, `GET /api/branches/{id}/metrics`, `GET /api/branches/{id}/loans`, `GET /api/branches/{id}/sector-exposures`
3. **Applications**: `GET /api/applications` (filter by branch)
4. **Policies & benchmarks**: `GET /api/policies`, `GET /api/benchmarks` (or benchmark-specific endpoints from manifest)
5. **Segment**: `GET /api/segments/{segment_id}` and related NCUA benchmark endpoints

## Numeric Precision (Universal)

| Kind | Decimals | Example |
|------|----------|---------|
| Currency / exposure | **2** | `1725000.00` |
| Ratios (npa_ratio, limit_pct, concentration) | **4** | `0.1135` |
| Basis points (bps) | **2** | `1037.49` |
| DSCR values | **2** | `1.47` |
| Weighted CDFI score | **1** | `2.6` |
| Counts, ratings, scores (integers) | **0** | `7` |

## Sorting Rules (Universal)

- `loan_id` / `application_id`: **ascending string** (lexicographic)
- `final_rating` / `current_rating`: **ascending integer**
- `sector`, `action`, `reason_codes`, `conditions`: **ascending alphabetically**
- `trigger_id`: **ascending** (e.g. ET001 < ET002)
- `state_code` / `peer_states`: **ascending**
- Workout queue: **descending exposure**, then ascending loan_id
- Priority ranking: **highest priority first** (order determined by scoring)

## Common Enum Sets

### Payment Status
`Current`, `30 Days Past Due`, `60 Days Past Due`, `90+ Days Past Due`, `Nonaccrual`

### Risk Classes (CDFI-style, lower score = better)
`Prime`, `Desirable`, `Satisfactory`, `Watch`, `Doubtful`, `Projected Loss`

CDFI factor scoring uses objective loan attributes (payment status, DSCR, LTV, FICO/credit, collateral coverage, time in business, etc.). Each factor contributes points; higher total = worse risk. Map total factor_score to risk class using standard CDFI bands.

### Recommended Actions
`monitor`, `watchlist`, `special_assets`, `workout`, `partial_chargeoff_review`, `legal_referral`

Escalation by severity: monitor (least severe), watchlist, special_assets, workout, partial_chargeoff_review, legal_referral (most severe).

### Decision Types
`approve`, `conditional_approve`, `decline`, `defer`, `participation_required`

### Decline Reason Codes
`capacity_limit`, `sector_breach`, `weak_dscr`, `high_ltv`, `low_fico`, `recent_bankruptcy`, `startup_risk`, `underwater_collateral`, `policy_floor_missing`, `documentation_gap`, `fdic_adverse_variance`, `ncua_peer_weakness`

### Application Conditions
`participation_required`, `reduced_amount`, `board_exception`, `sba_guaranty_required`, `startup_monitoring`, `none`

### Benchmark Versions
`fdic_q4_2024`, `ncua_q1_2025`

### Benchmark Metrics
`total_loans_noncurrent_pct`, `total_real_estate_noncurrent_pct`, `construction_development_noncurrent_pct`, `total_real_estate_30_89_pct`

### Monitoring Cadence
`monthly`, `quarterly`, `semiannual`

### Posture
`continue_approving`, `continue_with_tighter_conditions`, `temporarily_pause`

### Score Classes (CRE)
`approve_quality`, `conditional`, `weak`

### Direction (peer comparison)
`higher`, `lower`, `equal`

### Interpretation Enums
- capacity_status: `capacity_available`, `capacity_constrained`, `no_capacity`
- external_risk_status: `stronger_than_national_and_peers`, `mixed_vs_national_and_peers`, `weaker_than_national_and_peers`
- risk_tolerance: `restrained`, `moderate`, `expansive`
- committee_message: `capacity_available_but_external_risk_weaker`, `pause_until_state_metrics_recover`, `routine_approval_path_supported`

## Task-Specific Business Rules

### 1. Rating Migration Review

**Population**: loans where `current_rating >= target_current_rating_min` (typically 3).

**Re-rating**: Derive a new `final_rating` for each target loan using available financials (payment status, DSCR, LTV, collateral, days past due). A nonaccrual loan maps to rating 8. Severely delinquent (90+) maps to 7. Rating 6 for 30/60 DPD or weak DSCR. Rating 3–5 for performing with adequate coverage.

**final_rating_exposure_totals**: Group target loans by `final_rating`. Sum `loan_count` and `exposure`. Sort ascending by `final_rating`.

**migration_from_current_rating_3**: Subset of target loans originally rated 3 whose `final_rating` differs. Group by `final_rating`. Sort ascending. Include `loan_ids` sorted ascending.

**Material downgrades**: Loans where `final_rating > current_rating` AND `downgrade_notches >= 2`. `downgrade_notches = final_rating - current_rating`. Sort ascending by `loan_id`.

**Watch-list action coverage**: Assign action by final_rating band:
- Rating 6 → `watchlist`
- Rating 7 → `special_assets`
- Rating 8 → `partial_chargeoff_review`

Only include loans that received a new final_rating (the regraded population). Group by `action`, sort ascending by action string. `covered_loan_count`/`covered_exposure` = totals for all regraded loans assigned an action.

**NPA benchmark**:
- `branch_npa_exposure` = sum of exposure for loans with `payment_status == "Nonaccrual"`
- `branch_total_loans` = total exposure across ALL branch loans
- `branch_npa_ratio` = branch_npa_exposure / branch_total_loans (4dp)
- `fdic_benchmark_ratio` = lookup from FDIC benchmark for `total_loans_noncurrent_pct`
- `variance_ratio` = branch_npa_ratio − fdic_benchmark_ratio (4dp)
- `variance_bps` = variance_ratio × 10000 (2dp)

**Top problem credit**: The loan with the highest `final_rating`, then highest exposure as tiebreaker. Include borrower_name, exposure, current_rating, final_rating, payment_status, recommended_action.

### 2. Allocation Package

**Capacity**: `lending_capacity_q1` comes from branch metrics (e.g., tier 1 capital × leverage multiplier, or stated lending limit). Read from branch metrics endpoint.

**Priority ranking**: Score each application on financial strength (DSCR, LTV, FICO, collateral, borrower history). Rank descending by score. Include only approved and conditional_approve applications in `priority_ranking`.

**Allocation**: Process applications in priority order. For each:
- `approve`: full requested amount, bank_capacity_used = approved_amount
- `conditional_approve`: approved_amount = requested, bank_capacity_used = bank's retained portion (requested minus guaranteed/participated)
- `decline`: approved_amount = 0, bank_capacity_used = 0

Stop approving once remaining capacity is exhausted; decline remaining for `capacity_limit`.

**Key formulas**:
- `gross_approved_amount` = sum of approved_amount for all approved + conditional_approve
- `committed_capacity_amount` = sum of bank_capacity_used for all approved + conditional_approve
- `remaining_capacity` = lending_capacity_q1 − committed_capacity_amount

**Concentration flags**: For each application being approved, check if `post_approval_pct > limit_pct` for its sector. `flag: true` and `handling` set accordingly. Sort by sector then application_id.

**Decline reasons**: Object mapping declined application_id → array of reason codes. Sort codes alphabetically. Only include declined applications.

**Post-approval concentrations**: For every sector with exposure, compute:
- `exposure_after_approval` = existing sector exposure + newly approved exposure in that sector
- `post_approval_pct` = exposure_after_approval / total_branch_exposure_after_all_approvals
- `limit_pct` from policy
- `over_limit` = post_approval_pct > limit_pct

Sort by `sector` ascending.

### 3. Watch-List Stress

**Adverse population**: Loans with `current_rating >= adverse_rating_min` (typically 6).

**CDFI risk classes**: Score each adverse loan on objective factors (payment status: current=0, 30=3, 60=5, 90+=8, nonaccrual=10; DSCR: ≥1.25=0, 1.0–1.25=3, <1.0=5; LTV: <60%=0, 60–80%=2, >80%=4; plus other available factors). Sum → factor_score. Map to risk class.

**DSCR stress (+200bp)**:
- `stressed_dscr = base_dscr × (1 − 0.15)` (approximates 200bp rate shock impact on debt service)
- OR use a rate-shock formula: stressed_dscr = (NOI) / (debt_service × 1.15)
- `breach_threshold = 1.0`
- `breaches_threshold = stressed_dscr < 1.0`
- Only include loans with available DSCR
- Sort results ascending by loan_id
- `breach_loan_ids`: loans where breaches_threshold is true, sorted ascending

**Workout queue**: All adverse loans. Sort descending by exposure, then ascending by loan_id. Assign recommended_action by severity: Projected Loss + Nonaccrual → partial_chargeoff_review; 90+ DPD → special_assets; Watch risk class → special_assets; Desirable but DSCR breach → watchlist; Desirable no breach → watchlist.

**Severe bucket counts**: Group adverse loans by (current_rating, payment_status). Sum loan_count and exposure. Sort ascending by current_rating, then payment_status.

### 4. Competing CRE Decision

**Weighted CDFI scoring**: Score each application on CRE-relevant factors (DSCR, LTV, debt yield, sponsor strength, market, tenant quality). Weight and sum → weighted_cdfi_score (lower = better, 1dp).

**Score class**:
- ≤ 2.5: `approve_quality`
- 2.6–3.5: `conditional`
- ≥ 3.6: `weak` (approximate — calibrate from observed data)

**CRE dual-stress**: `formula: "dscr * 0.85 / 1.18"` — applies 15% rate shock (×0.85 on numerator NOI proxy) and 18% vacancy/expense stress (÷1.18 on debt service). `coverage_breach_threshold: 1.0`.

**Concentration**:
- `cre_policy_limit_pct` from policies
- `existing_cre_exposure` from sector-exposures (CRE-related sectors)
- `existing_cre_concentration` = existing_cre_exposure / branch_total_loans (4dp)
- `selected_post_approval_cre_concentration` = (existing_cre_exposure + selected_app_amount) / (branch_total_loans + selected_app_amount) (4dp)
- `selected_policy_variance_bps` = (selected_post_approval_cre_concentration − cre_policy_limit_pct) × 10000 (2dp)
- FDIC benchmark: use `total_real_estate_30_89_pct` for CRE delinquency comparison
- `branch_delinquency_ratio` from branch metrics
- `fdic_variance_ratio` = branch_delinquency_ratio − fdic_benchmark_ratio (4dp)
- `fdic_variance_bps` = fdic_variance_ratio × 10000 (2dp)

**Path selection**: Choose the application with lower (better) weighted_cdfi_score. If both breach threshold or have severe issues, the stronger may still get `participation_required`. The unselected gets `defer` (if issues are fixable) or `decline`.

**Conditions**: Derive from risk profile — CRE concentration breach → `committee_cre_exception`, `bank_retained_exposure_cap`; DSCR marginal → `minimum_dscr_covenant_1_25`; etc. Sort alphabetically.

### 5. Credit-Union Segment Posture

**State metrics**: Pull NCUA benchmark data for the target state. Values are integers as reported.

**Peer comparison**: Select neighboring/regional peer states (2–4 states). Compute median across peers. For each metric, compare NC value to US/peer median → `higher`/`lower`/`equal`.

**Posture logic**:
- Strong metrics + capacity → `continue_approving`
- Weak metrics but capacity exists → `continue_with_tighter_conditions`
- Severe deterioration → `temporarily_pause`

**Controls**: Checklist gates are always-required verifications. Added operating controls are risk-mitigating extras triggered by the posture decision.

**Escalation triggers**: Derived from identified risks. Each gets a `trigger_id` (ET001, ET002, …), a condition string from the enum, and an owner.

**Interpretation**: Assess capacity (from segment data), external risk (from benchmark comparison), and risk tolerance. Select committee_message that matches the combination.

## Common Pitfalls

1. **Precision mismatches**: Currency → 2dp, ratios → 4dp, bps → 2dp. Never mix.
2. **variance_bps formula**: Always `variance_ratio × 10000` (not ×100).
3. **Sort order violations**: loan_ids ascending within groups; sectors/reasons alphabetical; workout queue by descending exposure.
4. **Enum drift**: Use only the exact enum strings listed above. Don't invent variants.
5. **Missing required keys**: Every object in the template has a fixed key set — include all required keys even if value is 0 or empty array.
6. **Empty vs omitted**: `"conditions": ["none"]` for no-condition applications, not `[]`. `breaches_threshold: false` not omitted.
7. **Localhost trap**: Never use localhost. Always `http://34.46.77.124:8011`.
8. **Benchmark lookup**: The manifest tells you which benchmark endpoints exist. Don't assume endpoint paths — discover them.
9. **Total loan base**: When computing ratios, use the full branch loan total (all loans, not just the filtered population) unless the task explicitly scopes otherwise.
10. **DSCR stress**: The formula varies by task. Read the task prompt for the specific stress specification. For watch-list: +200bp rate shock. For CRE: dual stress `dscr * 0.85 / 1.18`.
11. **Factor scoring**: Use only objective, available loan attributes. Don't hallucinate factors that aren't in the API response.
12. **Concentration math**: post_approval denominator includes the newly approved amounts (total portfolio grows), not just the pre-approval total.
