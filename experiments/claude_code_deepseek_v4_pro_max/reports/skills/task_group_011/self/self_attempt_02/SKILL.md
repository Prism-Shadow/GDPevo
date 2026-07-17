# Bank Branch Credit-Risk Lending-Committee Skill

## API Workflow

**Base URL**: `http://34.46.77.124:8011` (override any localhost/setup.sh references).

**Discovery**: Start with `GET /api/manifest` (lists endpoints, benchmark versions, counts). Then `GET /api/health`.

**Key endpoints** (see manifest for all):
| Endpoint | Use |
|---|---|
| `/api/branches` | Branch list with `lending_capacity_q1`, `sector_ceiling_pct`, `cre_policy_limit_pct`, `total_assets`, `institution_type`, `fdic_benchmark_set`, `state_code` |
| `/api/branches/{id}/metrics` | Quarterly metrics: `nonperforming_loans`, `total_loans_outstanding`, `delinquency_30_plus_pct`, `total_deposits`, `allowance_for_loan_losses`, `net_charge_offs`. Use latest (`2025Q1`). |
| `/api/branches/{id}/loans` | Full loan book: ratings, DSCR, LTV, payment_status, collateral_value, sectors, etc. |
| `/api/branches/{id}/sector-exposures` | Per-sector `current_exposure`, `limit_pct`, `grandfathered` flag |
| `/api/branches/{id}/applications` | Pending applications with underwriting fields |
| `/api/policies` | Risk-rating rules, CDFI scoring, CRE weighting, stress formulas, concentration rules |
| `/api/benchmarks/fdic/q4-2024` | FDIC benchmark ratios |
| `/api/benchmarks/ncua/q1-2025` | NCUA state-level benchmarks (array of rows keyed by `state_code`) |
| `/api/credit-union-segments/{id}` | Segment profile: `quarterly_capacity`, `peer_states`, `minimum_checklist`, `risk_tolerance`, `state_code` |

---

## Risk Rating Derivation (Dominant Factor Rule)

**Rule**: Final rating = **worst (highest numeric) rating** from DSCR, LTV/collateral, and delinquency factors. If a factor is missing (null), skip it.

### DSCR → Rating
| DSCR Range | Rating |
|---|---|
| ≥ 1.5 | 3 |
| ≥ 1.25 | 4 |
| ≥ 1.05 | 5 |
| ≥ 1.0 | 6 |
| < 1.0 | 7 |

### LTV → Rating (use `collateral_value` / `outstanding_balance` if ltv field is null)
| LTV Range | Rating |
|---|---|
| ≤ 0.65 | 3 |
| ≤ 0.75 | 4 |
| ≤ 0.85 | 5 |
| ≤ 1.0 | 6 |
| > 1.0 | 7 |

### Delinquency → Rating Floor
| Payment Status | Minimum Rating |
|---|---|
| Current | (no floor) |
| 30 Days Past Due | 4 |
| 60 Days Past Due | 5 |
| 90+ Days Past Due | 7 |
| Nonaccrual | 8 |

**Material downgrade**: ≥ 2 notches worsening from current_rating to final_rating.

### NPA
NPA = loans where `payment_status` is "Nonaccrual" OR "90+ Days Past Due". NPA exposure = sum of outstanding_balance for NPA loans.

---

## CDFI Factor Scoring (for watch-list / adverse-rated loans)

Score each factor by ranges. Null factor → skip (contribute 0).

| Factor | <0.40 | 0.40-0.60 | 0.60-0.80 | >0.80 |
|---|---|---|---|---|
| LTV | 0 | 2 | 4 | 6 |
| Debt-to-Asset | 0 | 2 | 4 | 6 |

| Factor | >12 | 6-12 | 3-6 | <3 |
|---|---|---|---|---|
| Liquidity Months | 0 | 1 | 3 | 5 |

| Factor | >720 | 680-720 | 580-679 | <580 |
|---|---|---|---|---|
| FICO | 0 | 1 | 3 | 5 |

**Risk Class from total score**:
- Prime: 0-5
- Desirable: 6-9
- Satisfactory: 10-13
- Watch: 14-18
- Doubtful: ≥19
- Projected Loss: ≥19 AND LTV > 1.0

---

## CRE Weighted Score (for CRE applications)

Weights: `capacity` 0.45, `capital` 0.03, `character` 0.05, `collateral_exposure` 0.36, `conditions` 0.11.

Each dimension scored 1–5 (lower is better). Compute weighted sum:
```
weighted_score = Σ (dimension_score × weight)
```

**Score classes**: approve_quality (≤ 2.0), conditional (≤ 3.0), weak (> 3.0).

---

## Stress Tests

### Watch-List Stress (+200bp parallel shock)
```
stressed_dscr = dscr / (1 + 0.18)
```
Apply only to loans with DSCR available. Breach if `stressed_dscr < 1.0`.

### CRE Dual Stress
```
stressed_dscr = dscr × 0.85 / (1 + 0.18)
```
Used for CRE competing-decision analysis. Coverage breach threshold = 1.0.

---

## Concentration Rules

- **Lending capacity**: `branches.lending_capacity_q1` (hard cap for gross approvals).
- **Sector ceiling**: `branches.sector_ceiling_pct` is the default. The `sector_exposures` table provides per-sector `limit_pct` overrides.
- **CRE policy limit**: `branches.cre_policy_limit_pct` — total CRE exposure / total assets must not exceed this.
- **Grandfathering**: Existing over-ceiling exposure may be grandfathered, but **new approvals may not worsen** that sector's overage without mitigation.
- **Allowed mitigations**: `participation_required`, `reduced_amount`, `board_exception`.
- **Sector exposure pct** = sector current_exposure / branch total_assets. Post-approval adds the approved amount.
- **CRE concentration** = sum of all CRE-type loan outstanding_balances / total_assets. Post-approval adds approved CRE amounts.

---

## Application Decisioning

### Decision Enums
`approve` | `conditional_approve` | `decline` | `defer` | `participation_required`

### Conditions
`participation_required` | `reduced_amount` | `board_exception` | `sba_guaranty_required` | `startup_monitoring` | `none`

### Decline Reason Codes
`capacity_limit` | `sector_breach` | `weak_dscr` | `high_ltv` | `low_fico` | `recent_bankruptcy` | `startup_risk` | `underwater_collateral` | `policy_floor_missing` | `documentation_gap` | `fdic_adverse_variance` | `ncua_peer_weakness`

### Watch-List / Workout Actions
`monitor` | `watchlist` | `special_assets` | `workout` | `partial_chargeoff_review` | `legal_referral`

---

## Credit Union Segment Posture

### Posture Enums
`continue_approving` | `continue_with_tighter_conditions` | `temporarily_pause`

### NCUA Benchmark Metrics
Compare `state_code` row vs `US` row and vs `peer_states` median for: `delinquency_bps`, `loan_to_share_pct`, `roaa_bps`, `positive_net_income_pct`.

### Controls
**Required checklist gates**: `board_authorization` | `equipment_invoice` | `fleet_replacement_plan` | `payer_contract_summary` | `public_contract_or_tax_support` | `proof_of_insurance` | `ucc_or_title_lien`

**Added operating controls**: `pre_close_insurance_binder_verification` | `lien_perfection_prior_to_funding` | `senior_underwriter_second_review` | `quarterly_state_benchmark_monitoring` | `monthly_segment_delinquency_watch` | `committee_exception_for_capacity_overrun`

### Escalation Triggers
Condition choices: `segment_recent_delinquency_ge_90_bps` | `missing_insurance_or_lien_exception` | `quarterly_capacity_exceeded_or_exception_requested` | `state_delinquency_gap_widens_25_bps`

Owner choices: `credit_risk_manager` | `operations_control_manager` | `lending_committee_chair`

---

## Benchmark Comparison

### FDIC Benchmarks
`fdic_q4_2024` fields:
- `total_loans_noncurrent_pct` (0.0098)
- `total_real_estate_noncurrent_pct` (0.0121)
- `construction_development_noncurrent_pct` (0.0076)
- `total_real_estate_30_89_pct` (0.0051)
- `construction_development_30_89_pct` (0.0042)

### Computation
```
branch_npa_ratio = branch_npa_exposure / branch_total_loans
variance_ratio = branch_npa_ratio - fdic_benchmark_ratio
variance_bps = variance_ratio × 10000
```
Branch delinquency ratio for 30-89 comparison: `delinquency_30_plus_pct` from metrics. Convert to ratio (divide pct by 100) if needed.

---

## Output Field Conventions

### Precision
- **Currency / exposure (USD)**: 2 decimal places
- **Ratios / percentages (as decimals)**: 4 decimal places
- **BPS (basis points)**: 2 decimal places (except NCUA metrics which are integer BPS as-reported)
- **Weighted CDFI score**: 1 decimal place
- **Integers**: loan counts, ratings, notches, factor scores, NCUA BPS

### Sorting
- Lists sorted **ascending** by the key field specified in the answer template (loan_id, application_id, sector, final_rating, current_rating, action, trigger_id, etc.)
- For multi-key sorts: primary key first as specified (e.g., `descending exposure, then ascending loan_id` for workout_queue)
- `reason_codes` arrays: ascending alphabetically
- `loan_ids` arrays: ascending loan_id
- List items sorted as specified in template; when template says "ascending by X", sort by X ascending.

### Null/Missing Handling
- When computing derived ratings, skip factors where the underlying field is null
- When DSCR is null, skip DSCR-based rating and stress computation
- When LTV field is null but collateral_value and outstanding_balance exist, compute LTV = outstanding_balance / collateral_value
- When both LTV field and collateral_value are null, skip LTV-based rating
- For CDFI scoring, null factors contribute 0 to the total score
- `fico` may be null for business loans; skip FICO scoring when null

---

## Common Pitfalls

1. **Rating re-derivation scope**: Only re-derive ratings for loans meeting the stated criteria (e.g., "currently rated 3 or worse" or "rated 6 or worse"). Do NOT re-derive for all loans unless instructed.

2. **Dominant factor = worst**: The final rating is the maximum (worst) of DSCR, LTV, and delinquency ratings — not an average or weighted combination.

3. **Delinquency is a floor**: The delinquency rating sets a minimum. If DSCR and LTV suggest 3 but the loan is 60 DPD, the final rating is at least 5.

4. **Nonaccrual always maps to 8**: Overrides all other factors per the delinquency minimum table.

5. **CRE vs C&I vs other loan types**: CRE concentration uses only `loan_type == "CRE"` loans. Sector concentration uses all loans regardless of type.

6. **Sector ceiling vs CRE limit**: These are separate constraints. The sector ceiling applies per-sector across all loan types. The CRE policy limit applies only to CRE-type loans relative to total assets.

7. **Grandfathered exposure**: Sector entries with `grandfathered: 1` are already over-ceiling. New applications in that sector cannot be approved without mitigation, even if the overall capacity exists.

8. **Capacity computation**: `remaining_capacity = lending_capacity_q1 - committed_capacity_amount` where committed includes all approved/conditional amounts.

9. **Stress DSCR for watch-list**: Uses the formula `dscr / (1 + 0.18)`, NOT the CRE dual-stress formula. The CRE dual-stress (`dscr * 0.85 / (1 + 0.18)`) is only for CRE competing decisions.

10. **Benchmark metric selection**: Match the benchmark metric to the context. Use `total_loans_noncurrent_pct` for general NPA comparisons. Use `total_real_estate_noncurrent_pct` or `construction_development_noncurrent_pct` when the analysis focuses on real estate / construction segments.

11. **Percentage format**: When computing concentration ratios, divide by total_assets or total_loans (whichever is appropriate) and express as a decimal ratio (e.g., 0.1523 not 15.23%).

12. **Peer median for NCUA**: Compute the median across peer_states values for each metric. For even numbers of peers, take the mean of the two middle values (standard median).

13. **Application priority ranking**: Only approved and conditionally approved applications appear in the priority_ranking list, ordered highest priority first.

14. **Documentation gap**: Applications with `documentation_complete: 0` get a `documentation_gap` decline/defer reason code.
