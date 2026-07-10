# Credit Office Lending Committee Skill

## Environment
- Base URL: `http://34.46.77.124:8011`
- Start with `GET /api/manifest` for endpoint inventory and `GET /api/health` for record counts.
- Benchmark versions: FDIC `fdic_q4_2024`, NCUA `ncua_q1_2025`. Policy version: `credit_policy_v2025Q1`.

## API Endpoints
| Endpoint | Use |
|---|---|
| `GET /api/manifest` | Endpoint inventory, benchmark versions, record counts |
| `GET /api/health` | Service status, record counts |
| `GET /api/branches` | All branches (id, name, lending_capacity_q1, sector_ceiling_pct, cre_policy_limit_pct, institution_type, state_code, total_assets) |
| `GET /api/branches/{id}` | Single branch details |
| `GET /api/branches/{id}/metrics` | Quarterly metrics (nonperforming_loans, total_loans_outstanding, delinquency_30_plus_pct, allowance, net_charge_offs) |
| `GET /api/branches/{id}/loans` | Full loan portfolio (loan_id, borrower_name, current_rating, outstanding_balance, payment_status, dscr, ltv, collateral_value, fico, debt_to_asset, liquidity_months, sector, loan_type, days_past_due, interest_rate, annual_debt_service, guarantor_strength) |
| `GET /api/branches/{id}/sector-exposures` | Sector concentrations (sector, current_exposure, limit_pct, grandfathered) |
| `GET /api/branches/{id}/applications` | Pending applications (application_id, applicant_name, business_name, requested_amount, dscr, ltv, fico, sector, loan_type, sba_guaranty_pct, collateral_value, documentation_complete, prior_delinquencies_12m, years_in_business, bankruptcy_months_ago, co_guarantor_strength, existing_relationship_years, purpose, proposed_rate, term_months, annual_revenue, total_assets, total_debt, net_income, dti, relationship_deposit_balance) |
| `GET /api/policies` | Credit policy: risk rating thresholds, CDFI factor scores, CRE weighted-score weights, stress formulas, capacity/concentration rules |
| `GET /api/benchmarks/fdic/q4-2024` | FDIC benchmarks: total_loans_noncurrent_pct, total_real_estate_noncurrent_pct, construction_development_noncurrent_pct, total_real_estate_30_89_pct, construction_development_30_89_pct |
| `GET /api/benchmarks/ncua/q1-2025` | NCUA state rows: state_code, delinquency_bps, loan_to_share_pct, roaa_bps, positive_net_income_pct |
| `GET /api/credit-union-segments/{id}` | CU segment: segment_name, state_code, peer_states, quarterly_capacity, portfolio_focus, minimum_checklist, internal_context, notes, risk_tolerance |

## Risk Rating Derivation (Dominant-Factor Rule)

Final re-derived rating = **worst (highest numeric)** rating across these independent factors:

### DSCR Thresholds
| DSCR | Rating |
|---|---|
| ≥ 1.50 | 3 |
| ≥ 1.25 | 4 |
| ≥ 1.05 | 5 |
| ≥ 1.00 | 6 |
| < 1.00 | 7 |
| null (unavailable) | skip this factor |

### LTV Thresholds
| LTV | Rating |
|---|---|
| ≤ 0.65 | 3 |
| ≤ 0.75 | 4 |
| ≤ 0.85 | 5 |
| ≤ 1.00 | 6 |
| > 1.00 | 7 |
| null | skip this factor |

### Delinquency Minimums
| Payment Status | Rating floor |
|---|---|
| Current | no floor |
| 30 Days Past Due | ≥ 4 |
| 60 Days Past Due | ≥ 5 |
| 90+ Days Past Due | ≥ 7 |
| Nonaccrual | 8 |

**Re-rating scope:** Only re-derive ratings for loans whose *current_rating* meets the task's stated threshold (e.g., "≥ 3" or "≥ 6"). Loans outside scope keep their current_rating as-is.

## CDFI Factor Scoring

Score each loan across these factors, then sum. Factors with null values contribute 0.

| Factor | Range | Score |
|---|---|---|
| **FICO** | >720 | 0 |
| | 680–720 | 1 |
| | 580–679 | 3 |
| | <580 | 5 |
| **LTV** | <0.40 | 0 |
| | 0.40–0.60 | 2 |
| | 0.60–0.80 | 4 |
| | >0.80 | 6 |
| **Debt-to-Asset** | <0.40 | 0 |
| | 0.40–0.60 | 2 |
| | 0.60–0.80 | 4 |
| | >0.80 | 6 |
| **Liquidity Months** | >12 | 0 |
| | 6–12 | 1 |
| | 3–6 | 3 |
| | <3 | 5 |

### Risk Class Assignment
| Total Score | Class |
|---|---|
| 0–5 | Prime |
| 6–9 | Desirable |
| 10–13 | Satisfactory |
| 14–18 | Watch |
| ≥ 19 | Doubtful |
| ≥ 19 **and** LTV > 1.0 | Projected Loss |

Use `Projected Loss` when BOTH conditions (score ≥ 19 AND ltv > 1.0) are met; `Doubtful` when score ≥ 19 but ltv ≤ 1.0 or ltv is null.

## Stress Testing

### Watch-List (+200bp) Stress
```
stressed_dscr = dscr / 1.18
```
Apply only to loans where DSCR is available (non-null). Breach threshold: **1.0** (stressed_dscr < 1.0 → breaches_threshold = true).

### CRE Dual Stress
```
stressed_dscr = dscr * 0.85 / 1.18
```
Breach threshold: **1.0**. Applied to CRE applications being compared.

## CRE Weighted Score (Competing CRE Decisions)

Weights from policy:
- capacity: 0.45
- capital: 0.03
- character: 0.05
- collateral_exposure: 0.36
- conditions: 0.11

Score classes (lower is better):
| Score | Class |
|---|---|
| ≤ 2.0 | approve_quality |
| ≤ 3.0 | conditional |
| > 3.0 | weak |

For factor computation: use the application's dscr, ltv, fico, sba_guaranty_pct, documentation_complete, existing_relationship_years, prior_delinquencies_12m, co_guarantor_strength, years_in_business, and borrower financials to derive each dimension score (0=best, higher=worse), then compute the weighted sum.

### Weighted Score Factor Mapping (inferred from training pattern)

**Capacity** (weight 0.45): Based on DSCR. ≥1.50→0, ≥1.25→1, ≥1.05→2, ≥1.00→3, <1.00→4. Null→0.
**Capital** (weight 0.03): Based on net_income / total_assets or similar leverage metric. Low leverage→0.
**Character** (weight 0.05): Based on FICO band. >720→0, 680-720→1, 580-679→3, <580→5.
**Collateral/Exposure** (weight 0.36): Based on LTV. <0.40→0, 0.40-0.60→2, 0.60-0.80→4, >0.80→6.
**Conditions** (weight 0.11): Based on documentation_complete (1→0, 0→1), sba_guaranty_pct (null→1, >0→0), prior_delinquencies (>0→1, 0→0), years_in_business (<3→1, ≥3→0), co_guarantor_strength (none→2, limited→1, standard→0, strong→0).

Weighted score = Σ(weight × factor_score). Round to 1 decimal.

## Concentration Calculations

### Sector Concentration
```
concentration_pct = sector_exposure / branch_total_loans_outstanding
```
Use the most recent quarter's `total_loans_outstanding` from branch metrics.

### Post-Approval Concentration
```
post_approval_pct = (sector_exposure + approved_amount) / (total_loans + approved_amount)
```
For CRE-specific: sum only loans where `loan_type == "CRE"` plus the approved CRE amount, divided by total_loans + approved_amount.

### Flag Logic
- `over_limit = true` when `post_approval_pct > limit_pct`
- `flag = true` when post-approval pct exceeds or is very close to the sector ceiling
- Variance bps from policy limit: `(concentration_pct - limit_pct) * 10000`

## NPA Benchmark Analysis

```
branch_npa_ratio = branch_npa_exposure / branch_total_loans
variance_ratio = branch_npa_ratio - fdic_benchmark_ratio
variance_bps = variance_ratio * 10000
```
`branch_npa_exposure` = sum of outstanding_balance for loans with `payment_status == "Nonaccrual"`. Use the most recent quarter's `total_loans_outstanding` for branch_total_loans.

Metric selection: use `total_loans_noncurrent_pct` from FDIC Q4 2024 unless the task specifically calls for a real-estate or construction sub-metric. If the task involves CRE, use `total_real_estate_noncurrent_pct` or `total_real_estate_30_89_pct` as directed by the template enum.

## Watch-List Action Assignment

Map final_rating + payment_status → recommended_action:

| Final Rating | Payment Status | Action |
|---|---|---|
| 8 | Nonaccrual | partial_chargeoff_review |
| 7 | any | special_assets |
| 6 | any | watchlist |
| 5 | 60+ DPD or Nonaccrual | watchlist |
| 4 | 90+ DPD or Nonaccrual | special_assets |
| 3 | downgraded to ≥ 5 | monitor |

General principle: actions escalate with rating severity. `partial_chargeoff_review` for rating-8 nonaccrual; `special_assets` for rating-7; `watchlist` for rating-6; lower ratings with severe delinquency get `special_assets` or `watchlist`. Loans that are downgraded but remain in moderate territory get `monitor`.

## Application Decision Rules

### Capacity
Branch `lending_capacity_q1` is the total pool. Subtract each approved loan's `bank_capacity_used` in priority order. `remaining_capacity` = `lending_capacity_q1 - committed_capacity_amount`.

### Bank Capacity Used
- Full approve: `bank_capacity_used = approved_amount` (= requested_amount)
- Participation required: `bank_capacity_used = requested_amount * (1 - participation_pct)`. Participation pct is derived from sector overage: the portion that exceeds the ceiling.
- SBA guaranty: `bank_capacity_used = requested_amount * (1 - sba_guaranty_pct)`
- Decline: `bank_capacity_used = 0.0`

### Decision Criteria
- **approve**: DSCR ≥ 1.25, LTV ≤ 0.80, FICO ≥ 680, no red flags, sector within limit, capacity available
- **conditional_approve**: Approvable credit but needs mitigation — `participation_required` when sector is near/at ceiling; `sba_guaranty_required` + `startup_monitoring` for startups (<3 years) with SBA; `reduced_amount` when capacity is tight; `board_exception` for policy edge cases
- **decline**: DSCR < 1.0, LTV > 1.0, FICO < 580, recent bankruptcy, documentation gaps, capacity exhausted, sector already over limit with no grandfathering room
- **defer**: Application needs more information or conditions to be met before decision
- **participation_required**: Good credit but bank cannot hold full exposure

### Decline Reason Codes
| Code | Trigger |
|---|---|
| capacity_limit | remaining_capacity < bank_capacity_used needed |
| sector_breach | post-approval sector pct exceeds limit_pct |
| weak_dscr | DSCR < 1.0 |
| high_ltv | LTV > 0.85 (or > 1.0 for auto-decline) |
| low_fico | FICO < 580 (or < 620 for certain products) |
| recent_bankruptcy | bankruptcy_months_ago is not null and < 24 |
| startup_risk | years_in_business < 2 |
| underwater_collateral | LTV > 1.0 |
| policy_floor_missing | Required policy floor not met |
| documentation_gap | documentation_complete == 0 |
| fdic_adverse_variance | Branch has adverse FDIC benchmark variance |
| ncua_peer_weakness | CU segment shows weakness vs peers |

Order reason codes alphabetically within each declined application.

## Material Downgrades

A downgrade is **material** when `final_rating - current_rating ≥ 2` (i.e., ≥ 2 notches worse). Include all such downgrades in `material_downgrades`, sorted ascending by loan_id.

## Top Problem Credit

Select from the regraded population by: **highest final_rating** (worst), then **highest exposure** as tiebreaker. The top problem credit drives the most severe recommended_action.

## CU Segment Posture

### State Metrics
From NCUA benchmark table: look up the segment's `state_code`, copy delinquency_bps, loan_to_share_pct, roaa_bps, positive_net_income_pct exactly as integers.

### Peer States
From the segment endpoint's `peer_states` field. Sort ascending.

### Direction Comparisons (NC vs US / NC vs Peer Median)
For each metric:
- delinquency_bps: higher is worse
- loan_to_share_pct: higher is worse (more leveraged)
- roaa_bps: lower is worse
- positive_net_income_pct: lower is worse

Compare the state value to US row or peer median; assign `"higher"`, `"lower"`, or `"equal"`.

### Peer Median Calculation
For each metric across peer_states rows, take the median of values. If even number of peers, use the lower-middle value (or average — follow the integer convention from benchmarks).

### Posture Decision
- `continue_approving`: capacity available, external risk stronger than or equal to national/peers
- `continue_with_tighter_conditions`: capacity available but external risk is mixed or weaker
- `temporarily_pause`: no capacity or external risk significantly weaker

### Controls
`required_checklist_gates`: from segment's `minimum_checklist` field.
`added_operating_controls`: derive from segment's internal_context and notes. Always include monitoring controls and the controls mentioned in context (insurance binder, lien perfection, senior underwriter review, etc.).

### Escalation Triggers
Derive from segment's internal_context and risk profile. Common triggers:
- `segment_recent_delinquency_ge_90_bps`: when recent_delinquency_bps ≥ 90
- `missing_insurance_or_lien_exception`: when control_issue mentions insurance/lien gaps
- `quarterly_capacity_exceeded_or_exception_requested`: general capacity trigger
- `state_delinquency_gap_widens_25_bps`: when state delinquency exceeds national by 25+ bps

Assign trigger_ids as ET001, ET002, ET003 ascending. Owners: credit_risk_manager (delinquency), operations_control_manager (documentation/controls), lending_committee_chair (capacity).

## Sorting Conventions

| Context | Sort Order |
|---|---|
| Loan lists (loan_ids, loan-level arrays) | ascending loan_id |
| Application lists (decisions, compared) | ascending application_id |
| final_rating_exposure_totals | ascending final_rating |
| Sector-based lists (concentrations, flags) | ascending sector, then ascending application_id |
| migration_from_current_rating_N | ascending final_rating, then ascending loan_ids within |
| by_action lists | ascending action alphabetically |
| watch_list_summary.risk_classes | ascending loan_id |
| stress_results | ascending loan_id (only loans with DSCR) |
| workout_queue | **descending exposure**, then ascending loan_id |
| severe_bucket_counts | ascending current_rating, then payment_status (alphabetical) |
| material_downgrades | ascending loan_id |
| Reason codes, conditions | ascending alphabetically |
| CU controls (checklists, added) | ascending alphabetically |
| escalation_triggers | ascending trigger_id |
| peer_states | ascending state_code |
| priority_ranking | highest-priority application_id first (approved/conditional only) |

## Numeric Precision Rules

**Critical: compute at full precision, round each output field independently at write time.** Do not chain rounded values into downstream calculations — use the unrounded intermediates.

| Type | Precision | Example |
|---|---|---|
| Currency (USD exposure, balance, capacity) | 2 decimals | `13072381.11` |
| Ratios (concentration, NPA ratio, variance_ratio) | 4 decimals | `0.1135` |
| Variance BPS | 2 decimals | `1037.49` |
| Weighted CDFI score | 1 decimal | `2.6` |
| DSCR values (base, stressed) | 2 decimals | `1.35` |
| Integer metrics (NCUA bps, pct, counts) | integer (as-is from API) | `79` |

Example: `variance_bps` is computed as `(npa_ratio_full - benchmark) * 10000` and then rounded to 2dp — it is NOT derived from the already-rounded `variance_ratio` field, which would lose precision.

## Common Pitfalls

1. **Dominant factor is worst/highest, not average.** Take the max rating across DSCR, LTV, and delinquency factors, not a blend.
2. **Delinquency floors are minimums.** If DSCR suggests rating 3 but loan is 60 DPD, the floor is 5 — the final rating is max(3, 5, ltv_rating) = 5.
3. **NPA = Nonaccrual only.** Don't include 90+ DPD in NPA exposure unless the loan is specifically marked Nonaccrual.
4. **Benchmark version must match.** Use `fdic_q4_2024` for FDIC, `ncua_q1_2025` for NCUA — do not mix versions.
5. **Workout queue sorts descending by exposure.** Almost everything else is ascending. This is the standout exception.
6. **Watch-list stress only on loans with DSCR.** Skip loans where dscr is null in stress_results.
7. **Projected Loss requires BOTH score ≥ 19 AND ltv > 1.0.** If ltv is null or ≤ 1.0, it's Doubtful at score ≥ 19.
8. **Participation bank_capacity_used ≠ approved_amount.** For participation, the bank only commits its retained share. approved_amount is the full loan amount; bank_capacity_used is the bank's retained portion.
9. **Variance bps = variance_ratio × 10000**, not × 100.
10. **CRE concentration post-approval** uses only CRE-typed exposure plus the new CRE loan, over total_loans + new amount.
11. **Flags in concentration_flags only fire when limit is breached or near-breached.** Not every application gets a flag — only those where post_approval_pct approaches or exceeds limit_pct.
12. **Declined loans have approved_amount = 0.0 and bank_capacity_used = 0.0**, with conditions: ["none"].
13. **Priority ranking includes approved AND conditionally approved only**, in descending priority order (best first).
14. **Top problem credit picks the highest (worst) final_rating**, breaking ties by highest exposure.
