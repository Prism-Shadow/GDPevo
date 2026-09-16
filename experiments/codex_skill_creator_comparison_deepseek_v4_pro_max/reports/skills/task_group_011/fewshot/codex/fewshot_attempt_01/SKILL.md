---
name: credit-office
description: Shared credit office lending committee workflows for bank and credit-union branches. Use when the task involves branch loan portfolio reviews, risk-rating regrades, lending allocations, credit-union segment posture pages, watch-list stress tests, or competing CRE decisions against the public credit office API. Covers re-deriving risk ratings from policy rules, CDFI factor scoring, concentration analysis, benchmark variance (FDIC Q4 2024 / NCUA Q1 2025), DSCR stress, and watch-list actions.
---

# Credit Office

Shared credit office platform for branch-level lending committee analytics.

## API

Base URL is supplied by the runner as `<TASK_ENV_BASE_URL>`. All endpoints are public; no credentials required. Fetch data with standard HTTP GETs.

Endpoints and their payload shapes are documented in [references/api_endpoints.md](references/api_endpoints.md). Read it before calling any endpoint for the first time in a task.

General pattern:

```
curl -s <TASK_ENV_BASE_URL>/api/<endpoint>
```

Always round currency to 2 decimal places and ratio percentages to 4 decimal places unless a template specifies integers.

## Policy Rules

Credit policy rules (risk-rating thresholds, CDFI scoring tables, stress formulas, concentration and capacity rules) are documented in [references/policy_rules.md](references/policy_rules.md). Read it before performing any regrade, allocation, or stress computation.

The policy is also available live at `/api/policies`; read it once per task to pick up the specific benchmark versions.

## Workflows

Five committee workflows are covered. Each requires fetching the relevant API data, applying policy rules, and returning JSON in the template shape provided by the task input.

### 1. Rating Migration Review

For a given `branch_id` and review date, re-derive risk ratings for loans currently rated at or above a stated minimum (typically 3), then summarize migration, material downgrades, NPA benchmark variance, and the most severe problem credit.

**Data to fetch:**
- `/api/branches/{branch_id}` for branch metadata
- `/api/branches/{branch_id}/loans` for the loan portfolio
- `/api/branches/{branch_id}/metrics` for branch financial metrics
- `/api/policies` for risk-rating rules
- `/api/benchmarks/fdic/q4-2024` for FDIC benchmark data

**Steps:**

1. Filter loans where `current_rating >= target_min`.
2. For each loan, re-derive the rating using the dominant-factor rule: take the **worst** numeric rating from available DSCR, LTV, and delinquency factors. Only use factors where data is available; skip null factors. The delinquency rating floor comes from `payment_status` alone (see policy_rules.md for the table).
3. Group final ratings into exposure totals: one bucket per distinct `final_rating` with `loan_count` and `exposure` sum, sorted ascending by final_rating.
4. Count loans that moved **from** `current_rating=3` to a worse final rating; group by final_rating with `loan_ids` sorted ascending.
5. Identify material downgrades: any loan whose `final_rating - current_rating >= 2`. List sorted by loan_id ascending with loan_id, current_rating, final_rating, downgrade_notches, exposure.
6. Compute NPA benchmark:
   - `branch_npa_exposure` = `nonperforming_loans` from metrics
   - `branch_total_loans` = `total_loans_outstanding` from metrics
   - `branch_npa_ratio` = npa / total_loans (4 decimal precision)
   - `fdic_benchmark_ratio` = `total_loans_noncurrent_pct` from FDIC benchmark
   - `variance_ratio` = branch_npa_ratio - fdic_benchmark_ratio
   - `variance_bps` = variance_ratio * 10000 (2 decimal precision)
7. Assign watch-list actions to each regraded loan:
   - Rating 8: `partial_chargeoff_review`
   - Rating 7: `special_assets`
   - Rating 6: `watchlist`
   - Rating 5: `monitor`
   - Rating 4: `monitor`
   - Rating 3: `monitor`
   Aggregate by action: group loans by action with loan_count, exposure sum, and loan_ids sorted ascending.
   - `covered_loan_count`: count of loans receiving an action other than `monitor`
   - `covered_exposure`: sum of exposure for those covered loans
8. Identify `top_problem_credit`: the loan with the worst final_rating; if tied, worst payment_status; if still tied, highest exposure. Include loan_id, borrower_name, exposure, current_rating, final_rating, payment_status, recommended_action.

### 2. Lending Allocation Package

For a given `branch_id`, evaluate all pending applications against lending capacity, sector concentration limits, and credit quality.

**Data to fetch:**
- `/api/branches/{branch_id}` for capacity and sector ceiling
- `/api/branches/{branch_id}/metrics` for total loans outstanding
- `/api/branches/{branch_id}/applications` for pending applications
- `/api/branches/{branch_id}/sector-exposures` for current sector exposures
- `/api/policies` for concentration rules

**Steps:**

1. `lending_capacity_q1` comes from the branch record.
2. **Priority sort** applications: by highest DSCR descending, then lowest LTV ascending, then longest existing_relationship_years, then highest relationship_deposit_balance, then ascending application_id. Only approved and conditional applications consume capacity.
3. **Credit screen** each application in priority order:
   - Decline if LTV > 1.0: reason `high_ltv`
   - Decline if DSCR < 1.0: reason `weak_dscr`
   - Decline if fico is not null and < 580: reason `low_fico`
   - Decline if years_in_business is not null and < 1: reason `startup_risk`
   - Decline if bankruptcy_months_ago is not null and < 36: reason `recent_bankruptcy`
   - Decline if documentation_complete == 0: reason `documentation_gap`
   - Decline if `bank_capacity_used` would exceed `remaining_capacity`: reason `capacity_limit`
4. **Sector concentration check** for non-declined applications:
   - Compute post-approval exposure for the application's sector
   - `post_approval_pct` = (current_sector_exposure + approved_amount) / total_loans_outstanding
   - If `post_approval_pct > sector_limit_pct`:
     - If the sector has `grandfathered > 0` and the breach is not worsened by this approval: allow
     - Otherwise flag with `concentration_flags` and apply mitigation (`participation_required` or `reduced_amount`)
5. **Capacity consumption**:
   - For regular approvals: `bank_capacity_used = approved_amount`
   - For `participation_required`: `bank_capacity_used = approved_amount * 0.75`
   - For `sba_guaranty_required`: `bank_capacity_used = approved_amount * 0.25`
   - `committed_capacity_amount` = sum of bank_capacity_used for approve/conditional_approve
   - `remaining_capacity` = lending_capacity_q1 - committed_capacity_amount
6. `priority_ranking`: ordered list of application_ids for approve and conditional_approve only, in priority order.
7. **Post-approval concentrations**: for each sector with an approved or conditional application:
   - `exposure_after_approval` = current_sector_exposure + sum of approved amounts in that sector
   - `post_approval_pct` = exposure_after_approval / total_loans_outstanding
   - `over_limit` = post_approval_pct > sector_limit_pct

**Decline reason codes**: `capacity_limit`, `sector_breach`, `weak_dscr`, `high_ltv`, `low_fico`, `recent_bankruptcy`, `startup_risk`, `underwater_collateral`, `policy_floor_missing`, `documentation_gap`, `fdic_adverse_variance`, `ncua_peer_weakness`.

### 3. Credit Union Segment Posture

For a given `segment_id`, evaluate state-level NCUA benchmarks and return a controlled posture recommendation.

**Data to fetch:**
- `/api/credit-union-segments/{segment_id}` for segment profile and internal context
- `/api/benchmarks/ncua/q1-2025` for NCUA state benchmarks
- `/api/policies`

**Steps:**

1. Extract the segment's `state_code`, `peer_states`, `risk_tolerance`, `quarterly_capacity`, and internal context.
2. From NCUA benchmark rows, find the row matching `state_code` for state_metrics, the `US` row for national comparison, and rows for each peer state.
3. Compute **peer median**: for each of the four metrics, take the median across peer state rows. For even number of peers, use the lower of the two middle values.
4. **Direction comparisons** (nc_vs_us, nc_vs_peer_median): compare each metric:
   - `delinquency_bps`: higher → `higher` (worse)
   - `loan_to_share_pct`: higher → `higher` (worse)
   - `roaa_bps`: lower → `lower` (worse)
   - `positive_net_income_pct`: lower → `lower` (worse)
5. **Posture determination**:
   - `continue_approving`: state metrics stronger than both US and peers
   - `continue_with_tighter_conditions`: capacity available but external risk mixed/weaker
   - `temporarily_pause`: capacity constrained and external risk weaker
   Default to `continue_with_tighter_conditions` when capacity is available even with some risk signals.
6. `required_checklist_gates`: use the segment's `minimum_checklist` field directly.
7. `added_operating_controls`: derive from internal context. Typical patterns:
   - Insurance issue noted → `pre_close_insurance_binder_verification`
   - Always include `lien_perfection_prior_to_funding` and `quarterly_state_benchmark_monitoring`
   - Elevated recent delinquency → `monthly_segment_delinquency_watch`
   - Staffing constraint → `senior_underwriter_second_review`
   - Include all that apply from the context; sort alphabetically.
8. **Escalation triggers**: create triggers for key risks. Use trigger_ids `ET001`, `ET002`, etc. Common conditions:
   - `segment_recent_delinquency_ge_90_bps` → `credit_risk_manager`
   - `missing_insurance_or_lien_exception` → `operations_control_manager`
   - `quarterly_capacity_exceeded_or_exception_requested` → `lending_committee_chair`
   - `state_delinquency_gap_widens_25_bps` → `credit_risk_manager`
   Sort triggers by trigger_id ascending.
9. **Interpretation**:
   - `capacity_status`: `capacity_available` if quarterly_capacity > 0, `capacity_constrained` if tight, `no_capacity` if zero
   - `external_risk_status`: from direction comparisons: if all four signal weaker → `weaker_than_national_and_peers`; if mixed → `mixed_vs_national_and_peers`; if stronger → `stronger_than_national_and_peers`
   - `risk_tolerance`: from the segment
   - `committee_message`: `capacity_available_but_external_risk_weaker`, `pause_until_state_metrics_recover`, or `routine_approval_path_supported`

### 4. Watch-List Stress Packet

For a given `branch_id`, identify adversely rated loans (current_rating >= 6), assign CDFI risk classes, stress DSCRs at +200bp, and queue workout actions.

**Data to fetch:**
- `/api/branches/{branch_id}/loans` for the loan portfolio
- `/api/policies` for CDFI scoring tables and stress formulas

**Steps:**

1. Filter loans where `current_rating >= 6`.
2. **CDFI factor scoring** for each loan: sum points from policy CDFI tables for fico, ltv, debt_to_asset, and liquidity_months. Skip null factors. The score ranges are in policy_rules.md.
3. **Risk class** from total factor score:
   - 0-5: `Prime`, 6-9: `Desirable`, 10-13: `Satisfactory`, 14-18: `Watch`, >=19: `Doubtful`
   - Special: if score >= 19 **and** ltv > 1.0 → `Projected Loss`
4. **Monitoring cadence**:
   - `monthly` if any loan is `Projected Loss` or `Doubtful`
   - `quarterly` if any is `Watch`
   - `semiannual` otherwise
5. **DSCR stress**: for loans with available DSCR:
   - `stressed_dscr = dscr / 1.18` (the +200bp watch-list shock)
   - Breach threshold = 1.0
   - Loan breaches if stressed_dscr < 1.0
   - Sort results by loan_id ascending
6. **Workout queue** sorted by descending exposure then ascending loan_id:
   - `Projected Loss` + Nonaccrual → `partial_chargeoff_review`, projected_loss=true
   - `Projected Loss` but Current → `special_assets`, projected_loss=true
   - `Watch` or worse + (90+ Days or Nonaccrual) → `special_assets`, projected_loss=false
   - 90+ Days or Nonaccrual → `special_assets`
   - Breaches stress threshold → `watchlist`
   - Otherwise → `monitor`
7. **Severe bucket counts**: for loans with current_rating >= 7, group by (current_rating, payment_status). Sort by current_rating ascending, then payment_status in this order: Current, 30 Days Past Due, 60 Days Past Due, 90+ Days Past Due, Nonaccrual.

### 5. Competing CRE Decision

For a given `branch_id` and two `application_id` values, score both CRE applications, stress repayment, assess concentration, and recommend one.

**Data to fetch:**
- `/api/branches/{branch_id}` for CRE policy limit and branch details
- `/api/branches/{branch_id}/metrics` for total loans and delinquency
- `/api/branches/{branch_id}/loans` for existing CRE/sector exposure
- `/api/branches/{branch_id}/sector-exposures` for sector concentration
- `/api/branches/{branch_id}/applications` (filter to the two target apps)
- `/api/policies` for CRE weighted scoring, stress formula, concentration rules
- `/api/benchmarks/fdic/q4-2024` for FDIC benchmark

**Steps:**

1. **Weighted CDFI score** per CRE weights from policy (`cre_weighted_score.weights`):
   - capacity (0.45): score DSCR using policy risk-rating thresholds. Map DSCR rating to factor points: DSCR rating 3→1, 4→2, 5→3, 6→4, 7→5
   - capital (0.03): score debt_to_asset from CDFI table. If null, use 3.
   - character (0.05): score fico from CDFI table. If null, use 3.
   - collateral_exposure (0.36): score LTV from CDFI table. If null, use 3.
   - conditions (0.11): score liquidity_months from CDFI table. If null, use 3.
   Weighted score = sum(factor_score * weight) for all five factors. Round to 1 decimal.
2. **Score class**: score <= 2.0 → `approve_quality`, <= 3.0 → `conditional`, > 3.0 → `weak`.
3. **Stress**: `stressed_dscr = dscr * 0.85 / 1.18`. Breach threshold = 1.0. Breaches if stressed_dscr < 1.0.
4. **Concentration**:
   - `existing_cre_exposure`: sum of loan balances with `loan_type == "CRE"` plus exposure in sectors where the sector's limit_pct equals the branch's `cre_policy_limit_pct` (these are CRE-governed sectors)
   - `existing_cre_concentration` = existing_cre_exposure / total_loans_outstanding
   - `selected_post_approval_cre_concentration` = (existing_cre_exposure + selected amount) / total_loans_outstanding
   - `selected_policy_variance_bps` = (post_approval - cre_policy_limit_pct) * 10000
   - FDIC benchmark: use `total_real_estate_30_89_pct`. `branch_delinquency_ratio` = `delinquency_30_plus_pct` from metrics.
   - `fdic_variance_ratio` = branch_delinquency_ratio - fdic_benchmark_ratio
   - `fdic_variance_bps` = variance_ratio * 10000
5. **Select winner**: the application with the lower weighted score. If tied, higher DSCR. If still tied, lower LTV.
6. **Decision for each**:
   - Selected: `approve` if score_class=approve_quality; `conditional_approve` if conditional; `participation_required` if weak
   - Unselected: `decline` or `defer`. Prefer `defer` when issues are remediable; `decline` when structural
7. **Reason codes**: based on what drove the decision:
   - Sector breach → `sector_breach`
   - DSCR stress breach → `weak_dscr`
   - High LTV → `high_ltv`
   - FDIC adverse variance → `fdic_adverse_variance`
   Sort reason codes alphabetically.
8. **Conditions** for the selected application: derive from risk factors. Typical set:
   - CRE limit breached → `committee_cre_exception`, `bank_retained_exposure_cap`, `no_additional_cre_without_committee_review`
   - Always include: `updated_appraisal_before_close`, `tenant_roll_and_lease_review`, `minimum_dscr_covenant_1_25`, `quarterly_financial_reporting`
   Sort alphabetically.
