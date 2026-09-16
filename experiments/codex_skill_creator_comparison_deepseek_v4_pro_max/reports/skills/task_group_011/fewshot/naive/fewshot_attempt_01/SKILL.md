---
name: credit-risk-analysis
description: Analyze credit risk for branch and credit-union segments using the shared credit office API. Covers risk rating re-derivation, CDFI factor scoring, lending capacity allocation, concentration analysis, DSCR stress testing, watch-list actions, NPA benchmarking, CRE weighted scoring, and committee-ready report generation.
---

# Credit Risk Analysis

Use the shared credit office public API to analyze branch loan portfolios,
pending applications, and credit-union segments for lending-committee
decisions. The API base URL is always provided as `<TASK_ENV_BASE_URL>`.
There is no authentication requirement.

## API Reference

All data is read-only. Every endpoint returns JSON.

| Endpoint | What it returns |
|---|---|
| `GET /api/health` | Service status and record counts. |
| `GET /api/manifest` | Generated dataset metadata: benchmark versions, policy version, endpoint list. |
| `GET /api/policies` | Credit policy rules: risk rating thresholds, CDFI factor scores, CRE weighted score, stress formulas, concentration rules, delinquency minimums. |
| `GET /api/branches` | List of all branch objects. |
| `GET /api/branches/{branch_id}` | Single branch: `branch_id`, `branch_name`, `lending_capacity_q1`, `sector_ceiling_pct`, `cre_policy_limit_pct`, `total_assets`, `state_code`, `institution_type`. |
| `GET /api/branches/{branch_id}/metrics` | Quarterly branch metrics: `nonperforming_loans`, `total_loans_outstanding`, `delinquency_30_plus_pct`, `allowance_for_loan_losses`, `net_charge_offs`, `total_deposits`. Most recent quarter first. |
| `GET /api/branches/{branch_id}/loans` | All loans for the branch. See Loan Fields below. |
| `GET /api/branches/{branch_id}/sector-exposures` | Per-sector concentration: `sector`, `current_exposure`, `limit_pct`, `grandfathered`. |
| `GET /api/branches/{branch_id}/applications` | Pending lending applications. See Application Fields below. |
| `GET /api/benchmarks/fdic/q4-2024` | One object with FDIC benchmark ratios: `total_loans_noncurrent_pct`, `total_real_estate_noncurrent_pct`, `construction_development_noncurrent_pct`, `total_real_estate_30_89_pct`, `construction_development_30_89_pct`. |
| `GET /api/benchmarks/ncua/q1-2025` | NCUA rows per state including `US`: `state_code`, `delinquency_bps`, `loan_to_share_pct`, `roaa_bps`, `positive_net_income_pct`. |
| `GET /api/credit-union-segments/{segment_id}` | Single segment: `segment_id`, `segment_name`, `state_code`, `quarterly_capacity`, `risk_tolerance`, `peer_states`, `minimum_checklist`, `portfolio_focus`, `member_profile`, `internal_context`, `notes`, `current_outstanding`. |

### Loan Fields

Each loan object: `loan_id`, `borrower_name`, `branch_id`, `sector`, `loan_type`,
`outstanding_balance`, `current_rating`, `payment_status`, `days_past_due`,
`dscr`, `ltv`, `collateral_value`, `fico`, `debt_to_asset`, `liquidity_months`,
`guarantor_strength`, `interest_rate`, `annual_debt_service`, `annual_review_date`, `notes`.

Fields may be `null`. Treat null fields as unavailable for that loan.

### Application Fields

Each application: `application_id`, `applicant_name`, `business_name`, `branch_id`,
`sector`, `loan_type`, `requested_amount`, `dscr`, `ltv`, `collateral_value`,
`fico`, `years_in_business`, `existing_relationship_years`,
`relationship_deposit_balance`, `bankruptcy_months_ago`,
`prior_delinquencies_12m`, `documentation_complete`, `proposed_rate`, `purpose`,
`term_months`, `co_guarantor_strength`, `sba_guaranty_pct`, `total_assets`,
`total_debt`, `annual_revenue`, `net_income`, `dti`, `notes`.

Fields may be `null`. Treat null fields as unavailable.

## Policy Rules

Always fetch `GET /api/policies` first. The response contains the authoritative
rule set for the run. The rules described below are from `credit_policy_v2025Q1`
but the live policy response is canonical.

### Risk Rating Re-derivation

The **dominant factor rule**: take the worst (highest integer) numeric rating
from DSCR, LTV (or collateral), and delinquency factors. When a factor is
unavailable (null DSCR, null LTV, or Current payment status), skip it.

**DSCR thresholds** (from `policies.risk_rating.dscr_thresholds`):

| DSCR     | Rating |
|----------|--------|
| >= 1.50  | 3      |
| >= 1.25  | 4      |
| >= 1.05  | 5      |
| >= 1.00  | 6      |
| < 1.00   | 7      |

**LTV thresholds** (from `policies.risk_rating.ltv_thresholds`):

| LTV     | Rating |
|---------|--------|
| <= 0.65 | 3      |
| <= 0.75 | 4      |
| <= 0.85 | 5      |
| <= 1.00 | 6      |
| > 1.00  | 7      |

**Delinquency minimums** (from `policies.risk_rating.delinquency_minimums`):

| Payment Status       | Minimum Rating |
|----------------------|----------------|
| Current              | no minimum     |
| 30 Days Past Due     | 4              |
| 60 Days Past Due     | 5              |
| 90+ Days Past Due    | 7              |
| Nonaccrual           | 8              |

A material downgrade is a final_rating >= current_rating +
`policies.risk_rating.material_downgrade_notches` (default 2).

### CDFI Factor Scoring

Each loan is scored by summing points from four available factors. Null factors
are omitted from the sum.

From `policies.cdfi_factor_scores`:

**FICO**: >720:0, 680-720:1, 580-679:3, <580:5
**LTV**: <0.40:0, 0.40-0.60:2, 0.60-0.80:4, >0.80:6
**Debt-to-Asset**: <0.40:0, 0.40-0.60:2, 0.60-0.80:4, >0.80:6
**Liquidity Months**: >12:0, 6-12:1, 3-6:3, <3:5

Total factor_score = sum of available factor points.

**Risk class mapping** (from `policies.cdfi_factor_scores.classes`):

| Score    | Class           |
|----------|-----------------|
| 0-5      | Prime           |
| 6-9      | Desirable       |
| 10-13    | Satisfactory    |
| 14-18    | Watch           |
| >=19     | Doubtful        |
| >=19 and ltv > 1.0 | Projected Loss |

The Projected Loss rule overrides Doubtful when ltv > 1.0.

### CRE Weighted Scoring

From `policies.cre_weighted_score`. Weights: capacity 0.45, capital 0.03,
character 0.05, collateral_exposure 0.36, conditions 0.11.

Compute sub-scores for each dimension using CDFI-style factor scoring on
application data, then apply weighted sum:

```
weighted_score = capacity_score*0.45 + capital_score*0.03 + character_score*0.05
               + collateral_exposure_score*0.36 + conditions_score*0.11
```

Map weighted_score to class:

| Score  | Class           |
|--------|-----------------|
| <= 2.0 | approve_quality |
| <= 3.0 | conditional     |
| > 3.0  | weak            |

### DSCR Stress Formulas

From `policies.stress`:

**Watch-list stress (+200bp parallel shock)**:
```
stressed_dscr = dscr / (1 + 0.18)
```

**CRE dual stress**:
```
stressed_dscr = dscr * 0.85 / (1 + 0.18)
```

Coverage breach threshold is always **1.0** (from `policies.stress.coverage_breach_threshold`).

Apply stress only to loans or applications where DSCR is available (not null).

### Concentration Rules

From `policies.capacity_concentration`:

- Sector exposure comes from `/api/branches/{branch_id}/sector-exposures`.
- Each row has `limit_pct` and `current_exposure`.
- Compute concentration ratio: `current_exposure / total_loans_outstanding`
  (use latest-quarter `total_loans_outstanding` from branch metrics).
- Post-approval: add approved amounts to the relevant sector's current_exposure,
  recompute ratio, compare to limit_pct.
- If `grandfathered` is 1, existing over-ceiling exposure may remain, but new
  approvals may not worsen that sector without mitigation.
- When a concentration flag fires, allowed mitigations from the policy are:
  `participation_required`, `reduced_amount`, `board_exception`.

## Workflow Patterns

### Pattern A: Rating Migration Review (branch-level)

1. Fetch: branch details, branch metrics, all branch loans, policies, FDIC benchmark.
2. Filter loans with `current_rating >= target_min` (typically 3).
3. For each targeted loan, re-derive risk rating using the dominant factor rule.
4. Classify migration from each current rating bucket to final rating.
5. Identify material downgrades (final - current >= material_downgrade_notches).
6. Compute NPA benchmark: `nonperforming_loans / total_loans_outstanding` vs
   FDIC `total_loans_noncurrent_pct`. Variance in ratio and bps.
7. Assign watch-list actions to each loan based on final rating:
   - 4: monitor
   - 5-6: watchlist
   - 7: special_assets
   - 8 with Nonaccrual: partial_chargeoff_review
   - 8 without Nonaccrual: legal_referral
8. Select top problem credit: the loan with the worst combination of final
   rating and exposure (typically the highest-rated, highest-exposure loan).
   Report its loan_id, borrower_name, exposure, current_rating, final_rating,
   payment_status, and recommended_action.
9. Produce final_rating_exposure_totals: group by final_rating, sum loan_count
   and exposure. Order by final_rating ascending.
10. Produce migration_from_current_rating_3: for loans that started at rating 3,
    group by final_rating, collect loan_ids.
11. Produce watch_list_action_coverage: count covered loans/exposure, break down
    by action with loan_ids.

### Pattern B: Lending Allocation (branch-level)

1. Fetch: branch details, branch metrics, sector exposures, pending applications, policies.
2. For each application, decide approve/conditional_approve/decline/defer/participation_required.
3. Decision logic: Start with the most creditworthy applications. Respect
   capacity. Check sector limits. Apply policy thresholds.
4. Decline reasons (use controlled reason codes):
   - `capacity_limit`: total committed capacity would exceed `lending_capacity_q1`
   - `sector_breach`: sector concentration would exceed its limit_pct
   - `weak_dscr`: DSCR well below policy floor (typically < 1.05 or < 1.0)
   - `high_ltv`: LTV > 0.85 or > 1.0
   - `low_fico`: FICO < 580 or in weakest band
   - `recent_bankruptcy`: bankruptcy within recent history
   - `startup_risk`: years_in_business < 2
   - `underwater_collateral`: LTV > 1.0
   - `policy_floor_missing`: required underwriting data missing (null DSCR, etc.)
   - `documentation_gap`: documentation_complete == 0
   - `fdic_adverse_variance`: branch metric is adverse vs FDIC benchmark
   - `ncua_peer_weakness`: state metrics weaker than peers
5. Conditional approve conditions:
   - `participation_required`: sector concentration flagged
   - `reduced_amount`: cut the approved amount
   - `board_exception`: policy override needed
   - `sba_guaranty_required`: SBA-backed loan with insufficient guaranty
   - `startup_monitoring`: startup requiring oversight
   - `none`: no conditions
6. For approved and conditional apps: `bank_capacity_used` for
   `participation_required` = the bank-retained portion; for `sba_guaranty_required`
   = bank's unguaranteed share. For standard approves, full amount counts.
7. Priority ranking: list approved/conditionally-approved applications in
   priority order (highest first). Priority factors: credit quality, relationship
   depth, strategic fit, concentration impact.
8. Post-approval concentrations: for each sector, add approved amounts,
   recompute ratio, flag if over limit.

### Pattern C: Credit Union Segment Posture

1. Fetch: manifest, policies, NCUA benchmarks, segment endpoint.
2. Extract segment state's metrics from NCUA benchmark rows.
3. Compute US comparison: for each metric (delinquency, loan_to_share, roaa,
   positive_net_income), compare state value to US row. Direction: higher/lower/equal.
4. Compute peer median comparison: compute the median of the peer_states values
   for each metric, compare state to peer median.
   - For even number of peers, median = average of middle two values.
5. Determine posture:
   - `continue_approving`: capacity available AND external risk stronger or mixed
   - `continue_with_tighter_conditions`: capacity available BUT external risk weaker
   - `temporarily_pause`: no capacity OR severely adverse external risk
6. Required checklist gates come from `segment.minimum_checklist`.
7. Added operating controls: based on `internal_context.control_issue` and
   external risk posture. Options: `pre_close_insurance_binder_verification`,
   `lien_perfection_prior_to_funding`, `senior_underwriter_second_review`,
   `quarterly_state_benchmark_monitoring`, `monthly_segment_delinquency_watch`,
   `committee_exception_for_capacity_overrun`.
8. Escalation triggers: match conditions to owners.
   - `segment_recent_delinquency_ge_90_bps` → `credit_risk_manager`
   - `missing_insurance_or_lien_exception` → `operations_control_manager`
   - `quarterly_capacity_exceeded_or_exception_requested` → `lending_committee_chair`
   - `state_delinquency_gap_widens_25_bps` → `credit_risk_manager`
9. Interpretation: capacity_status based on quarterly_capacity vs
   current_outstanding, external_risk_status based on benchmark comparisons,
   risk_tolerance from segment, committee_message synthesized from posture and statuses.

### Pattern D: Watch-List Stress (branch-level, adverse loans)

1. Fetch: branch details, branch metrics, all branch loans, policies.
2. Filter loans with `current_rating >= adverse_rating_min` (typically 6).
3. For each adverse loan, compute CDFI factor score and assign risk class.
4. For each adverse loan with available DSCR, compute +200bp stress:
   `stressed_dscr = dscr / 1.18`. Flag if stressed_dscr < 1.0.
5. Set monitoring cadence:
   - `monthly` if any Projected Loss or Doubtful loans
   - `quarterly` if all are Watch or better
   - `semiannual` if all are Satisfactory or better
6. Build workout queue sorted by descending exposure, then ascending loan_id:
   - Projected Loss → `partial_chargeoff_review`, projected_loss: true
   - Doubtful → `special_assets`, projected_loss: false
   - Watch → `special_assets` if payment_status is 90+ or Nonaccrual, else `watchlist`
   - Satisfactory → `watchlist`
   - Desirable → `watchlist` if payment_status not Current, else `monitor`
   - Prime → `monitor`
   For each item report: loan_id, exposure, risk_class, payment_status,
   recommended_action, projected_loss.
7. Severe bucket counts: for ratings >= 6, group by (current_rating, payment_status),
   count loans and sum exposure. Order by current_rating ascending, then payment_status.

### Pattern E: Competing CRE Decision (branch-level, two applications)

1. Fetch: branch details, branch metrics, all branch loans, sector exposures,
   the two target applications, policies, FDIC benchmark.
2. For each application, compute CRE weighted score. Sub-score dimensions:
   - **capacity** (0.45): score from DSCR and capacity availability at branch level.
     Map DSCR to score: >=1.50→0, >=1.25→2, >=1.05→4, >=1.00→6, <1.00→8.
   - **capital** (0.03): score from borrower capital position. Map
     debt_to_asset using CDFI bands. If null, use net_income/total_assets ratio
     as proxy, or score 3 (midpoint) if unavailable.
   - **character** (0.05): score from FICO (CDFI bands), relationship_years
     (<2→5, 2-5→3, >5→0), prior_delinquencies, guarantor strength
     (strong→0, standard→1, limited→3, none→5).
   - **collateral_exposure** (0.36): score from LTV (CDFI bands) and exposure
     size relative to branch capacity.
   - **conditions** (0.11): score from loan_type (CRE→0, other→2), purpose
     (refinance→0, other→2), documentation_complete (1→0, 0→3).
3. Apply CRE dual stress: `stressed_dscr = dscr * 0.85 / 1.18`.
4. Compute branch CRE concentration:
   - Identify all branch loans that are CRE-type. These span sectors that
     commercially would be considered CRE (Multifamily, Office, Retail CRE,
     Industrial CRE, Hospitality, and any sector whose loan_type is explicitly
     CRE). Sum their outstanding_balance for existing CRE exposure.
   - `existing_cre_concentration` = existing CRE exposure / total_loans_outstanding.
   - `selected_post_approval_cre_concentration` = (existing + selected app amount) / total_loans_outstanding.
   - `selected_policy_variance_bps` = (post_approval_cre_concentration - cre_policy_limit_pct) * 10000.
5. FDIC benchmark comparison: compare branch `delinquency_30_plus_pct` to
   FDIC `total_real_estate_30_89_pct`. Variance in ratio and bps.
6. Decide path for the better-scored application:
   - `approve_quality` → approve, add conditions as needed
   - `conditional` → conditional_approve or participation_required
   - `weak` → decline or defer
7. Unselected disposition: decline or defer with reason codes.
8. Conditions for selected: include `committee_cre_exception` when CRE policy
   limit is breached, `no_additional_cre_without_committee_review` for
   over-limit situations, `bank_retained_exposure_cap` for participation
   scenarios, `minimum_dscr_covenant_1_25` for moderate DSCR,
   `quarterly_financial_reporting` for monitoring, `tenant_roll_and_lease_review`
   for CRE, `updated_appraisal_before_close` when LTV is elevated.

### Pattern F: Application-Level Decision Logic

When determining approve/decline for individual applications independently of
the competing workflow, follow this priority:

1. **Hard declines** (any one is fatal):
   - `documentation_complete == 0` → `documentation_gap`
   - `ltv > 1.0` → `underwater_collateral` (unless SBA guaranteed mitigates)
   - `fico < 580` → `low_fico`
   - `bankruptcy_months_ago` is recent (within 24 months) → `recent_bankruptcy`
   - `years_in_business < 2` → `startup_risk` (unless strong mitigating factors)
   - DSCR available and < 1.0 → `weak_dscr`
2. **Capacity check**: if committed_capacity + requested_amount > lending_capacity_q1 → `capacity_limit` for all remaining, lower-priority apps.
3. **Sector check**: for each application, compute post-approval sector concentration.
   If > sector limit_pct AND sector not grandfathered → `sector_breach`.
   If > sector limit_pct AND grandfathered → can still approve with mitigation.
4. **Policy thresholds**:
   - `ltv > 0.85` → `high_ltv`
   - `dscr < 1.05` → `weak_dscr`
5. **Benchmark comparison**: if branch delinquency materially exceeds FDIC benchmark → `fdic_adverse_variance`.

## Reason Codes Reference

| Code | When to use |
|---|---|
| `capacity_limit` | Branch Q1 lending capacity exhausted. |
| `sector_breach` | Post-approval sector concentration exceeds limit_pct. |
| `weak_dscr` | DSCR below policy minimum (typically < 1.05). |
| `high_ltv` | LTV above policy ceiling (typically > 0.85). |
| `low_fico` | FICO score below 580 or in weakest band. |
| `recent_bankruptcy` | Bankruptcy within recent history. |
| `startup_risk` | Business operating under 2 years. |
| `underwater_collateral` | LTV > 1.0. |
| `policy_floor_missing` | Required underwriting data missing (null DSCR, etc.). |
| `documentation_gap` | Incomplete application documentation. |
| `fdic_adverse_variance` | Branch delinquency materially exceeds FDIC benchmark. |
| `ncua_peer_weakness` | State metrics significantly weaker than peers (NCUA). |

## Decision Enum Reference

**Decision values**: `approve`, `conditional_approve`, `decline`, `defer`, `participation_required`

**Condition values**: `participation_required`, `reduced_amount`, `board_exception`, `sba_guaranty_required`, `startup_monitoring`, `none`

**Action values**: `monitor`, `watchlist`, `special_assets`, `workout`, `partial_chargeoff_review`, `legal_referral`

**Payment status values**: `Current`, `30 Days Past Due`, `60 Days Past Due`, `90+ Days Past Due`, `Nonaccrual`

**Posture values**: `continue_approving`, `continue_with_tighter_conditions`, `temporarily_pause`

**Risk class values**: `Prime`, `Desirable`, `Satisfactory`, `Watch`, `Doubtful`, `Projected Loss`

**Score class values**: `approve_quality`, `conditional`, `weak`

## Computation Checklist

- All currency values: round to 2 decimal places.
- All percentages/ratios: round to 4 decimal places.
- Basis points (bps): round to 2 decimal places.
- List ordering: follow the template's `ordering` directive (ascending by the
  specified field).
- When a field is null and required for computation, exclude that dimension.
- Always use the **latest quarter** from branch metrics (first element in the
  metrics array).
- For FDIC benchmarks, use the `/api/benchmarks/fdic/q4-2024` endpoint unless the manifest or
  branch specifies otherwise.
- For NCUA benchmarks, use the `/api/benchmarks/ncua/q1-2025` endpoint unless the manifest
  specifies otherwise.
- When the branch's `institution_type` is `bank`, use FDIC benchmarks.
- When analyzing a `credit_union_segments` endpoint, use NCUA benchmarks.
- For CRE concentration: sum outstanding_balance for loans where `loan_type` is
  `CRE`, regardless of sector. Also include loans in sectors typically
  classified as CRE even if loan_type differs (based on sector_exposure rows
  with CRE-relevant limit_pct values).

## Output Rules

- Always produce valid JSON matching the provided answer template.
- Do not include narrative text outside the JSON.
- Respect all enum choices in the template.
- Sort lists exactly as the template's ordering directive specifies.
- Include all required top-level keys.
- Use null only when the template explicitly allows it.

## Error Handling

- If an API endpoint returns an error or empty response, re-request once.
- If a loan or application field is null, treat the factor as unavailable and
  skip it in scoring, but include the loan in population counts.
- If a branch has no loans matching the target criteria, report zero counts and
  empty lists as appropriate.
