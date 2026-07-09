# Credit Office Lending Committee Skill

## Environment

- **Base URL**: `http://34.46.77.124:8011` (never use localhost)
- **Policy version**: `credit_policy_v2025Q1`
- **Benchmarks**: FDIC Q4 2024 (`fdic_q4_2024`), NCUA Q1 2025 (`ncua_q1_2025`)

## API Workflow

Always start with `GET /api/manifest` to confirm endpoints, then fetch data in parallel where possible:

| Endpoint | Returns |
|---|---|
| `GET /api/health` | Service status, record counts |
| `GET /api/manifest` | Endpoint list, versions, seed |
| `GET /api/branches` | All 10 branches with capacities, limits |
| `GET /api/branches/{id}` | Single branch details (state, sector_ceiling_pct, cre_policy_limit_pct, lending_capacity_q1) |
| `GET /api/branches/{id}/metrics` | Quarterly metrics (nonperforming_loans, total_loans_outstanding, delinquency_30_plus_pct, allowance, net_charge_offs) — use **latest quarter** |
| `GET /api/branches/{id}/loans` | Full loan portfolio with DSCR, LTV, FICO, payment_status, collateral_value, debt_to_asset, liquidity_months, etc. |
| `GET /api/branches/{id}/sector-exposures` | Per-sector current_exposure plus limit_pct; total across sectors = branch total loans |
| `GET /api/branches/{id}/applications` | Pending applications (bank branches only) |
| `GET /api/policies` | Risk-rating rules, CDFI factor scores, CRE weighted scoring, stress formulas, concentration rules |
| `GET /api/benchmarks/fdic/q4-2024` | FDIC benchmark ratios (noncurrent %, 30-89 day delinquency %) |
| `GET /api/benchmarks/ncua/q1-2025` | Per-state NCUA benchmark rows (delinquency_bps, loan_to_share_pct, roaa_bps, positive_net_income_pct) |
| `GET /api/credit-union-segments/{id}` | Segment details (peer_states, minimum_checklist, quarterly_capacity, recent_delinquency_bps, risk_tolerance, internal_context) |

## Business Rules

### 1. Risk Rating Derivation (Rating Migration tasks)

The **dominant factor rule**: Final rating = **worst (highest numeric)** rating from:
- **DSCR thresholds**: `≥1.50→3`, `≥1.25→4`, `≥1.05→5`, `≥1.0→6`, `<1.0→7`
- **LTV thresholds**: `≤0.65→3`, `≤0.75→4`, `≤0.85→5`, `≤1.0→6`, `>1.0→7`
- **Delinquency minimums**: Current→no floor, 30 Days→4, 60 Days→5, 90+ Days→7, Nonaccrual→8

When DSCR or LTV/collateral is null, skip that factor. When all factors produce a rating lower than the delinquency floor, the delinquency floor wins.

A **material downgrade** is defined as `downgrade_notches ≥ 2` (from policy: `material_downgrade_notches: 2`).

**Watch-list actions by final rating** (for regraded population):
- Rating 8 (Nonaccrual) → `partial_chargeoff_review`
- Rating 7 → `special_assets`
- Rating 6 → `watchlist`
- Rating 3-5 with no change or upgrade → `monitor` (if no delinquency concern)

### 2. NPA Benchmark (Rating Migration tasks)

- **NPA** = loans with `payment_status == "Nonaccrual"` (typically rating 8)
- `branch_npa_exposure` = sum of outstanding_balance for nonaccrual loans
- `branch_npa_ratio` = npa_exposure / total_loans_outstanding (latest quarter)
- `variance_ratio` = branch_npa_ratio − fdic_benchmark_ratio
- `variance_bps` = variance_ratio × 10000
- FDIC metric: use `total_loans_noncurrent_pct` unless task specifies otherwise

### 3. CDFI Factor Scoring (Watch-list & CRE tasks)

Score each loan/application by summing these factors (from `/api/policies` → `cdfi_factor_scores`):

| Factor | <0.40 | 0.40-0.60 | 0.60-0.80 | >0.80 |
|---|---|---|---|---|
| LTV | 0 | 2 | 4 | 6 |
| Debt-to-Asset | 0 | 2 | 4 | 6 |

| Factor | >720 | 680-720 | 580-679 | <580 |
|---|---|---|---|---|
| FICO | 0 | 1 | 3 | 5 |

| Factor | >12 | 6-12 | 3-6 | <3 |
|---|---|---|---|---|
| Liquidity (months) | 0 | 1 | 3 | 5 |

Risk classes from total score:
- **Desirable**: 6–9
- **Satisfactory**: 10–13
- **Watch**: 14–18
- **Projected Loss**: ≥19 AND LTV > 1.0
- **Doubtful**: ≥19 AND LTV ≤ 1.0
- Null/missing factors contribute 0. Null FICO → skip that factor.

### 4. CRE Weighted Scoring (Competing CRE tasks)

Weights from policy:
- capacity: 0.45, capital: 0.03, character: 0.05, collateral_exposure: 0.36, conditions: 0.11

Score classes:
- `approve_quality`: ≤ 2.0
- `conditional`: 2.1 – 3.0
- `weak`: > 3.0

Lower score is better. The scoring maps each 1-5 C's sub-score through the weights to produce the weighted CDFI score.

### 5. Stress Testing

**Watch-list DSCR stress (+200bp)**:
```
stressed_dscr = base_dscr / (1 + 0.18)
```
The +200bp parallel shock is modeled as an 18% increase in debt service. Breach threshold = 1.0.

**CRE dual stress**:
```
stressed_dscr = dscr × 0.85 / (1 + 0.18)
```
15% NOI decline (×0.85) plus 18% debt-service increase. Breach threshold = 1.0.

When base_dscr is null, skip that loan from stress results.

### 6. Application Allocation (Capacity tasks)

1. **Score each application** on credit factors (DSCR, LTV, FICO, guarantees, relationship).
2. **Rank by credit quality**: strongest credits get priority. For equal quality, prefer higher exposure.
3. **Approve in priority order** until `lending_capacity_q1` is exhausted.
4. **Decline reasons** map from policy thresholds:
   - `high_ltv`: LTV > 0.80 (or branch policy threshold)
   - `weak_dscr`: DSCR < 1.25 (coverage floor)
   - `low_fico`: FICO < 580 or < 640 (policy-dependent)
   - `startup_risk`: years_in_business < 2
   - `recent_bankruptcy`: bankruptcy_months_ago < 36
   - `capacity_limit`: remaining capacity insufficient
   - `sector_breach`: post-approval sector concentration exceeds limit_pct
5. **bank_capacity_used** = approved_amount minus participation/SBA portion:
   - For `conditional_approve` with `participation_required`: bank_capacity_used = retained exposure (typically 25% of approved amount for branches)
   - For `conditional_approve` with `sba_guaranty_required`: bank_capacity_used = unguaranteed portion
   - For plain `approve`: bank_capacity_used = approved_amount
6. `committed_capacity_amount` = sum of all bank_capacity_used
7. `remaining_capacity` = lending_capacity_q1 − committed_capacity_amount
8. `gross_approved_amount` = sum of approved_amount for non-declined applications

### 7. Concentration

- **Sector concentration** = sector_exposure / total_loans_outstanding
- **Post-approval concentration** = (existing sector exposure + new approved amount for that sector) / total_loans_outstanding
- **Flag** = true when post_approval_pct > limit_pct (from sector_exposures)
- **CRE concentration** = CRE loans total / total_loans_outstanding
- `selected_policy_variance_bps` = (post_approval_cre_concentration − cre_policy_limit_pct) × 10000
- `over_limit` = post_approval_pct > limit_pct

### 8. Credit Union Segment Posture

- **Peer states**: taken from segment endpoint; adjacent states
- **Direction** (higher/lower/equal): Compare NC metric to US row and to peer median
  - Peer median = median of peer states' metric values
  - delinquency_bps: higher is worse → `higher` when NC > comparator
  - roaa_bps and positive_net_income_pct: higher is better → `higher` when NC > comparator
- **Posture decision**:
  - `continue_approving`: capacity available + external risk not weaker
  - `continue_with_tighter_conditions`: capacity available but external risk weaker
  - `temporarily_pause`: no capacity or severe risk
- **Controls**: `required_checklist_gates` from segment minimum_checklist; `added_operating_controls` based on risk gaps
- **Escalation triggers** with trigger IDs (ET001, ET002, ...), condition enum, and owner enum
- **Interpretation**: synthesize capacity_status, external_risk_status, risk_tolerance

## Output Conventions

### Numeric Precision
| Field type | Precision |
|---|---|
| USD amounts (exposure, balance, capacity) | 2 decimals |
| Ratios (concentration, variance, NPA ratio) | 4 decimals |
| bps (basis points) | 2 decimals |
| DSCR values | 2 decimals |
| CDFI weighted scores | 1 decimal |
| Percentages from NCUA (delinquency_bps, etc.) | integer |
| Factor scores, loan counts, rating notches | integer |

### Sorting Rules (by task type)

**Rating Migration**:
- `final_rating_exposure_totals`: ascending by final_rating
- `migration_from_current_rating_3`: ascending by final_rating; loan_ids within each group ascending
- `material_downgrades`: by downgrade_notches descending, then exposure descending, then loan_id ascending
- `by_action`: ascending by action enum value; loan_ids within each group ascending
- `watch_list_action_coverage` → `by_action`: ascending by action string

**Allocation**:
- `decisions`: ascending by application_id
- `priority_ranking`: approved/conditional first, by priority (highest credit quality first), then by exposure descending
- `concentration_flags`: by sector then application_id
- `post_approval_concentrations`: ascending by sector
- `decline_reasons`: keys are application_id; reason codes sorted alphabetically

**Watch-list Stress**:
- `risk_classes`: ascending by loan_id
- `stress_results`: ascending by loan_id (only loans with DSCR available)
- `breach_loan_ids`: ascending
- `workout_queue`: descending exposure, then ascending loan_id
- `severe_bucket_counts`: ascending current_rating, then payment_status (Current < 30 Days < 60 Days < 90+ Days < Nonaccrual)

**Competing CRE**:
- `applications_compared`: ascending by application_id
- `reason_codes` and `unselected_reason_codes`: alphabetically ascending
- `stress.results`: ascending by application_id
- `conditions`: alphabetically ascending

**Segment Posture**:
- `peer_states`: ascending state code
- `required_checklist_gates`: alphabetically
- `added_operating_controls`: alphabetically
- `escalation_triggers`: ascending trigger_id

### Enum Reference

**Payment Status**: `Current`, `30 Days Past Due`, `60 Days Past Due`, `90+ Days Past Due`, `Nonaccrual`

**Decision**: `approve`, `conditional_approve`, `decline`, `defer`, `participation_required`

**Conditions**: `none`, `participation_required`, `reduced_amount`, `board_exception`, `sba_guaranty_required`, `startup_monitoring`

**Actions**: `monitor`, `watchlist`, `special_assets`, `workout`, `partial_chargeoff_review`, `legal_referral`

**Decline Reasons**: `capacity_limit`, `sector_breach`, `weak_dscr`, `high_ltv`, `low_fico`, `recent_bankruptcy`, `startup_risk`, `underwater_collateral`, `policy_floor_missing`, `documentation_gap`, `fdic_adverse_variance`, `ncua_peer_weakness`

**CDFI Risk Classes**: `Prime`, `Desirable`, `Satisfactory`, `Watch`, `Doubtful`, `Projected Loss`

**Score Classes** (CRE weighted): `approve_quality`, `conditional`, `weak`

**Posture**: `continue_approving`, `continue_with_tighter_conditions`, `temporarily_pause`

**Monitoring Cadence**: `monthly`, `quarterly`, `semiannual`

**Capacity Status**: `capacity_available`, `capacity_constrained`, `no_capacity`

**External Risk Status**: `stronger_than_national_and_peers`, `mixed_vs_national_and_peers`, `weaker_than_national_and_peers`

**Risk Tolerance**: `restrained`, `moderate`, `expansive`

**Committee Message**: `capacity_available_but_external_risk_weaker`, `pause_until_state_metrics_recover`, `routine_approval_path_supported`

## Common Pitfalls

1. **Using localhost**: Always use `http://34.46.77.124:8011`. Ignore any task text that references `env/setup.sh` or localhost.
2. **Wrong metric quarter**: Branch metrics are quarterly; always use the latest quarter's data (current period, e.g., 2025Q1).
3. **NPA definition**: NPA = nonaccrual loans only, NOT all delinquent loans. Nonaccrual ≠ 90+ days past due.
4. **Dominant factor**: Risk rating takes the WORST (highest number) across DSCR, LTV, and delinquency factors — not an average.
5. **DSCR stress formula**: Watch-list stress is `dscr / 1.18`, NOT `dscr × 0.85 / 1.18` (that's the CRE dual stress). The task context determines which formula to use.
6. **Null handling**: When DSCR, LTV, collateral_value, or FICO is null, skip that factor in rating/scoring. Don't default to zero.
7. **Concentration denominator**: Use `total_loans_outstanding` from latest metrics, NOT sum of sector exposures (which may differ due to rounding).
8. **bank_capacity_used vs approved_amount**: For conditional approvals, bank_capacity_used is the retained portion after participation or SBA guaranty, NOT the full approved amount.
9. **Sorting precision**: Sort keys are case-sensitive strings for enums, numeric for ratings/amounts. Don't mix.
10. **Template compliance**: Read the task's `answer_template.json` to confirm required keys, enums, and ordering. Templates are authoritative over general conventions.
11. **Branch vs credit union**: Credit union branches (CIVIC_NC_FIRE_EMS, TRISTATE_GA_AMBULANCE) have `institution_type: "credit_union"` and use NCUA benchmarks, not FDIC.
12. **benchmark_metric enum**: Only `total_loans_noncurrent_pct`, `total_real_estate_noncurrent_pct`, `construction_development_noncurrent_pct` are valid. Match to the task context or use the most general.
13. **Loan type filtering**: CRE-specific tasks should filter by `loan_type == "CRE"` when computing CRE exposure/concentration.
14. **Score class edge cases**: `Projected Loss` requires both score ≥19 AND LTV > 1.0. Score ≥19 with LTV ≤ 1.0 is `Doubtful`.
15. **Exposure precision**: Always round to 2 decimal places for USD. Sums may drift if intermediate values aren't rounded consistently.
