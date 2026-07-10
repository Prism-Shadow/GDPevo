# Bank Branch Credit-Risk Lending-Committee Skill

## Environment & API Entry

Base URL: `http://34.46.77.124:8011` (from `environment_access.md`; overrides any localhost refs in task prompts).

Start every session with `GET /api/manifest` to confirm benchmark versions and available endpoints.

### Core Endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/manifest` | Benchmark versions, record counts, endpoint list |
| `GET /api/branches` | All branches with `branch_id`, `institution_type`, `lending_capacity_q1`, `sector_ceiling_pct`, `cre_policy_limit_pct`, `state_code`, `total_assets` |
| `GET /api/branches/{id}` | Single branch detail |
| `GET /api/branches/{id}/metrics` | Quarterly metrics (2025Q1, 2024Q4): `total_loans_outstanding`, `nonperforming_loans`, `total_deposits`, `delinquency_30_plus_pct`, `net_charge_offs`, `allowance_for_loan_losses` |
| `GET /api/branches/{id}/loans` | All loans: `loan_id`, `current_rating`, `dscr`, `ltv`, `fico`, `payment_status`, `outstanding_balance`, `collateral_value`, `debt_to_asset`, `liquidity_months`, `sector`, `loan_type`, `borrower_name`, `days_past_due`, `guarantor_strength`, `interest_rate`, `notes` |
| `GET /api/branches/{id}/sector-exposures` | Per-sector: `sector`, `current_exposure`, `limit_pct`, `grandfathered` |
| `GET /api/branches/{id}/applications` | Pending applications: `application_id`, `requested_amount`, `dscr`, `ltv`, `fico`, `sector`, `loan_type`, `documentation_complete`, `prior_delinquencies_12m`, `bankruptcy_months_ago`, `years_in_business`, `sba_guaranty_pct`, `co_guarantor_strength`, `existing_relationship_years`, `relationship_deposit_balance`, `proposed_rate`, `term_months`, `purpose`, `business_name`, `total_assets`, `total_debt`, `annual_revenue`, `net_income`, `notes` |
| `GET /api/policies` | Credit policy: `risk_rating`, `cdfi_factor_scores`, `cre_weighted_score`, `capacity_concentration`, `stress` |
| `GET /api/benchmarks/fdic/q4-2024` | FDIC benchmark ratios (single object, not an array) |
| `GET /api/benchmarks/ncua/q1-2025` | NCUA state rows: `state_code`, `delinquency_bps`, `loan_to_share_pct`, `roaa_bps`, `positive_net_income_pct` |
| `GET /api/credit-union-segments/{id}` | Segment detail: `state_code`, `peer_states`, `risk_tolerance`, `quarterly_capacity`, `current_outstanding`, `recent_delinquency_bps`, `minimum_checklist`, `notes` |

---

## Risk Rating Re-Derivation (Dominant Factor Rule)

**Rule**: Final re-derived rating = **worst (highest numeric)** rating from all available factors among DSCR, LTV, and delinquency.

### DSCR → Rating
| DSCR Range | Rating |
|---|---|
| ≥ 1.50 | 3 |
| ≥ 1.25 | 4 |
| ≥ 1.05 | 5 |
| ≥ 1.00 | 6 |
| < 1.00 | 7 |

### LTV → Rating
| LTV Range | Rating |
|---|---|
| ≤ 0.65 | 3 |
| ≤ 0.75 | 4 |
| ≤ 0.85 | 5 |
| ≤ 1.00 | 6 |
| > 1.00 | 7 |

### Delinquency Floor (minimum rating from payment status)
| Payment Status | Minimum Rating |
|---|---|
| Current | *no floor* |
| 30 Days Past Due | 4 |
| 60 Days Past Due | 5 |
| 90+ Days Past Due | 7 |
| Nonaccrual | 8 |

**Null/missing factors**: If DSCR or LTV is `null`, skip that factor entirely (it contributes nothing). Delinquency floor always applies regardless of other factors.

**Material downgrade**: A re-derived final_rating that is ≥ 2 notches worse than current_rating (final_rating − current_rating ≥ 2).

---

## CDFI Risk-Class Scoring

Assign each loan a risk class by summing independent factor scores. Score each factor where data is available; skip nulls.

| Factor | Range | Score |
|---|---|---|
| **FICO** | > 720 | 0 |
| | 680–720 | 1 |
| | 580–679 | 3 |
| | < 580 | 5 |
| **LTV** | < 0.40 | 0 |
| | 0.40–0.60 | 2 |
| | 0.60–0.80 | 4 |
| | > 0.80 | 6 |
| **Debt-to-Asset** | < 0.40 | 0 |
| | 0.40–0.60 | 2 |
| | 0.60–0.80 | 4 |
| | > 0.80 | 6 |
| **Liquidity Months** | > 12 | 0 |
| | 6–12 | 1 |
| | 3–6 | 3 |
| | < 3 | 5 |

**Risk class from total score**:
- 0–5: **Prime**
- 6–9: **Desirable**
- 10–13: **Satisfactory**
- 14–18: **Watch**
- ≥ 19: **Doubtful**
- ≥ 19 **AND** LTV > 1.0: **Projected Loss**

---

## CRE Weighted Credit Scoring

Used for competing CRE application decisions. Weights: capacity 0.45, capital 0.03, character 0.05, collateral_exposure 0.36, conditions 0.11.

Score classes (lower is better):
- ≤ 2.0: **approve_quality**
- ≤ 3.0: **conditional**
- > 3.0: **weak**

---

## Stress-Test Formulas

### Watch-list +200bp DSCR Stress
```
stressed_dscr = base_dscr / 1.18
```
Applied to watch-list loans where DSCR is available. Breach threshold = 1.00.

### CRE Dual Stress
```
stressed_dscr = dscr × 0.85 / 1.18
```
Coverage breach threshold = 1.00.

---

## Concentration Rules

### Sector Concentration
- Each branch has a default `sector_ceiling_pct` on the branch object.
- The `/sector-exposures` endpoint provides **per-sector** `limit_pct` which may differ from the default.
- `grandfathered: 1` = existing over-limit exposure is tolerated but new approvals must not worsen that sector without mitigation.
- Allowed mitigations: `participation_required`, `reduced_amount`, `board_exception`.
- **Concentration ratio** = sector_exposure / total_loans_outstanding (use most recent quarter, Q1).

### CRE Concentration
- Branch `cre_policy_limit_pct` caps total CRE exposure as a fraction of total loans.
- Post-approval CRE = (existing CRE exposure + selected app amount) / total_loans_outstanding.
- FDIC benchmark: `total_real_estate_30_89_pct` for delinquency comparison.

### Capacity
- `lending_capacity_q1` from branch is the Q1 lending budget.
- Bank capacity used = requested_amount (or approved amount).
- Committed capacity = sum of approved amounts.

---

## NPA Benchmark Calculation

Metric: `total_loans_noncurrent_pct` from FDIC Q4 2024 (`0.0098`).

```
branch_npa_exposure = nonperforming_loans (from 2025Q1 metrics)
branch_total_loans  = total_loans_outstanding (from 2025Q1 metrics)
branch_npa_ratio    = branch_npa_exposure / branch_total_loans
variance_ratio      = branch_npa_ratio - fdic_benchmark_ratio
variance_bps        = variance_ratio × 10000
```

---

## Credit Union Segment Posture

From segment endpoint: `risk_tolerance`, `recent_delinquency_bps`, `state_code`, `peer_states`, `quarterly_capacity`, `current_outstanding`, `minimum_checklist`, internal `control_issue`, `staffing_constraint`, `notes`.

### State Metrics
Read from NCUA benchmark row matching the segment's `state_code`. Values are integers exactly as reported.

### Peer Comparison
Compare NC state metrics to US national row (`state_code: "US"`) and peer-state median.
Direction: `higher`, `lower`, or `equal` for each of delinquency_bps, loan_to_share_pct, roaa_bps, positive_net_income_pct.

### Posture Decision
- `continue_approving` — capacity available, external risk stronger/neutral, risk_tolerance expansive or moderate with strong metrics.
- `continue_with_tighter_conditions` — capacity available but external risk mixed or requires added controls.
- `temporarily_pause` — severe external risk weakness or capacity exhausted.

### Controls & Triggers
- `required_checklist_gates`: from segment `minimum_checklist` plus any additional required gates.
- `added_operating_controls`: derived from internal context (control issues, staffing constraints) and posture.
- `escalation_triggers`: conditions like `segment_recent_delinquency_ge_90_bps`, `missing_insurance_or_lien_exception`, `quarterly_capacity_exceeded_or_exception_requested`, `state_delinquency_gap_widens_25_bps`. Owners: `credit_risk_manager`, `operations_control_manager`, `lending_committee_chair`.

---

## Allocation & Decision Logic

### Priority Ranking
Rank applications by credit quality signals: higher DSCR, higher FICO, lower LTV, longer relationship, lower risk sector concentration impact. Applications with `documentation_complete: 0` or red flags (recent bankruptcy, very low FICO, startup with no mitigants) rank lower.

### Decision Codes
`approve`, `conditional_approve`, `decline`, `defer`, `participation_required`

### Condition Codes
`participation_required`, `reduced_amount`, `board_exception`, `sba_guaranty_required`, `startup_monitoring`, `none`

### Decline Reason Codes
`capacity_limit`, `sector_breach`, `weak_dscr`, `high_ltv`, `low_fico`, `recent_bankruptcy`, `startup_risk`, `underwater_collateral`, `policy_floor_missing`, `documentation_gap`, `fdic_adverse_variance`, `ncua_peer_weakness`

### Recommended Action Codes
`monitor`, `watchlist`, `special_assets`, `workout`, `partial_chargeoff_review`, `legal_referral`

---

## Output Conventions (MUST FOLLOW)

### Numeric Precision
| Field Type | Decimals | Example |
|---|---|---|
| Currency (USD) | 2 | `1234567.89` |
| Ratios / percentages (as decimal) | 4 | `0.0523` |
| Basis points (bps) | 2 | `52.30` |
| Weighted CDFI score | 1 | `2.5` |
| NCUA integer metrics | integers (as reported) | `79` |

### Sorting
- Lists of loans/ratings: **ascending by the key field** (final_rating, loan_id, application_id, sector, trigger_id, payment_status).
- Exception: `workout_queue` sorts **descending exposure, then ascending loan_id**.
- `material_downgrades`: ascending loan_id.
- `decline_reasons`: reason codes sorted alphabetically within each application.
- `conditions` (Harbor): ascending alphabetically.

### Enum Values — Exact Strings Required
Payment status: `"Current"`, `"30 Days Past Due"`, `"60 Days Past Due"`, `"90+ Days Past Due"`, `"Nonaccrual"`
Risk class: `"Prime"`, `"Desirable"`, `"Satisfactory"`, `"Watch"`, `"Doubtful"`, `"Projected Loss"`
Score class: `"approve_quality"`, `"conditional"`, `"weak"`
Monitoring cadence: `"monthly"`, `"quarterly"`, `"semiannual"`
Posture: `"continue_approving"`, `"continue_with_tighter_conditions"`, `"temporarily_pause"`

---

## Common Pitfalls

1. **Nonaccrual dominates**: A loan with payment_status `"Nonaccrual"` gets rating 8 regardless of DSCR/LTV — the delinquency floor is a hard minimum, and 8 is the worst possible.
2. **Missing DSCR/LTV**: When `dscr` or `ltv` is `null`, skip that factor in dominant-factor rating. Do NOT assign a rating from it.
3. **Material downgrade threshold is 2, not 1**: Only report downgrades where final_rating − current_rating ≥ 2.
4. **FDIC benchmark is one object, not an array**: `GET /api/benchmarks/fdic/q4-2024` returns `{}` with named fields, not `[]`.
5. **Sorting `migration_from_current_rating_3`**: Sort by `final_rating` ascending, not by loan_id.
6. **`variance_bps = variance_ratio × 10000`**: 1% = 100 bps, so ratio 0.01 = 100 bps. Multiply ratio by 10000 to get bps.
7. **NCUA `US` row**: The national row has `state_code: "US"` — use it for the national comparison.
8. **Peer median, not mean**: For NCUA peer comparison, compute the median of peer-state values, not the mean.
9. **Watch-list stress only for loans with DSCR**: Loans without DSCR are excluded from `stress_results`; only include loans where `dscr` is not null.
10. **Grandfathering is per-sector**: Check `grandfathered` field in sector-exposures. Sectors with grandfathered=1 may show exposure above limit_pct.
11. **Top problem credit**: Select the loan with the worst (highest) final_rating. If tied, pick the one with the highest exposure. Include `recommended_action` from the action-code enum.
12. **`watch_list_action_coverage`**: Count loans from the regrade population that received a watch-list action. Group by action type with loan_ids sorted ascending.
13. **CRE dual-stress formula is `dscr * 0.85 / 1.18`**: Apply the 0.85 revenue haircut AND the 1.18 rate shock multiplicatively, not additively.
14. **`approved_amount` vs `requested_amount`**: For conditional approvals, `approved_amount` may be less than `requested_amount` (e.g., reduced_amount condition).
15. **Post-approval concentration**: Recompute sector exposure after adding approved amounts to the relevant sectors.
