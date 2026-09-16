# Workflow Patterns

These are reusable computational and reasoning patterns for credit-risk committee
analysis. Each pattern describes how to go from API data to a structured answer field.
The patterns are independent of any specific branch or segment.

## Pattern 1: Risk Rating Re-derivation

**Inputs**: Loans endpoint, Policies endpoint
**Output**: final_rating for each target loan, plus material downgrade list

1. Fetch /api/policies to get rating thresholds.
2. Fetch /api/branches/{branch_id}/loans to get loan data.
3. Filter loans by target criterion (e.g. current_rating >= N).
4. For each filtered loan:
   a. Derive DSCR rating from dscr field using policy thresholds (skip if null).
   b. Derive LTV rating from ltv field using policy thresholds (skip if null).
   c. Get delinquency floor from payment_status.
   d. final_rating = max(rating_dscr or 1, rating_ltv or 1, delinquency_floor or 1).
5. Compute downgrade_notches = final_rating - current_rating.
6. Material downgrades: downgrade_notches >= 2.
7. Group results by final_rating for exposure totals.
8. For migration analysis, isolate a specific current_rating cohort.

## Pattern 2: Watch-List Action Assignment

**Inputs**: Re-derived ratings, loan data
**Output**: Action per loan (monitor, watchlist, special_assets, partial_chargeoff_review)

Assign based on final_rating and payment_status:

- Nonaccrual with ltv > 1.0: partial_chargeoff_review
- Nonaccrual or final_rating >= 7: special_assets
- final_rating == 6: watchlist
- downgrade_notches >= 2: watchlist
- Otherwise: monitor

Group loans by action for watch_list_action_coverage summaries.

## Pattern 3: NPA Benchmark Variance

**Inputs**: Branch metrics, FDIC benchmark
**Output**: npa_benchmark object

1. Fetch /api/branches/{branch_id}/metrics, use index 0 (most recent quarter).
2. Fetch /api/benchmarks/fdic/q4-2024.
3. branch_npa_exposure = metrics[0].nonperforming_loans
4. branch_total_loans = metrics[0].total_loans_outstanding
5. branch_npa_ratio = branch_npa_exposure / branch_total_loans (4 decimal places)
6. fdic_benchmark_ratio = benchmark.total_loans_noncurrent_pct
7. variance_ratio = branch_npa_ratio - fdic_benchmark_ratio
8. variance_bps = variance_ratio * 10000
9. benchmark_metric = "total_loans_noncurrent_pct"
10. benchmark_version = benchmark.benchmark_version

## Pattern 4: Top Problem Credit

**Inputs**: All loans, re-derived ratings
**Output**: Single most severe credit

Select the loan with:
1. Highest final_rating first.
2. Within same rating, highest exposure.
3. Within same rating and exposure, Nonaccrual or worst payment_status.

Output: loan_id, borrower_name, exposure, current_rating, final_rating,
payment_status, recommended_action.

## Pattern 5: CDFI Watch-List Analysis

**Inputs**: Policies, adversely rated loans (current_rating >= 6)
**Output**: risk_classes, stress_results, workout_queue, severe_bucket_counts

1. For each adverse loan, compute CDFI factor score:
   a. Score fico, debt_to_asset, liquidity_months, ltv using policy tables.
   b. Skip null factors. Sum available scores.
   c. Assign risk_class from total score.
2. For DSCR stress:
   a. Only loans with non-null dscr.
   b. stressed_dscr = dscr / 1.18.
   c. breaches_threshold = stressed_dscr < 1.0.
   d. Collect breach_loan_ids.
3. Build workout_queue ordered by descending exposure, then ascending loan_id.
   Assign recommended_action from risk_class and payment_status.
4. Build severe_bucket_counts: group by (current_rating, payment_status),
   count loans and sum exposure.

## Pattern 6: Application Screening and Allocation

**Inputs**: Branch data, applications, policies, sector exposures
**Output**: allocation, decisions, decline_reasons, concentration_flags

1. Fetch branch, applications, sector exposures, policies.
2. For each application, screen for fatal issues:
   - ltv > 0.90 for consumer/residential to flag high_ltv
   - ltv > 0.85 for commercial to flag high_ltv
   - dscr < 1.00 to flag weak_dscr
   - fico < 580 to flag low_fico
   - bankruptcy_months_ago is not null and < 36 to flag recent_bankruptcy
   - years_in_business < 2 and no SBA guaranty to flag startup_risk
   - documentation_complete == 0 to flag documentation_gap
3. Rank surviving applications by priority (DSCR, relationship length, LTV, deposit).
4. Allocate capacity_q1 in priority order. Track committed_capacity_amount.
5. For conditionally approved (SBA), committed = approved * (1 - sba_guaranty_pct).
   For participation_required, committed = retained share.
6. For each approved/conditional application, compute post-approval sector concentration.
   Flag if over limit and not grandfathered.
7. Decline reasons: map each declined app to relevant reason codes from the
   controlled enum.

## Pattern 7: NCUA Segment Posture

**Inputs**: Credit union segment, NCUA benchmarks
**Output**: posture, state_metrics, peer_comparison, controls, escalation_triggers

1. Fetch segment and benchmark data.
2. Extract state row for segment.state_code, US row, and peer state rows.
3. Compute peer median for each metric across peer states.
4. Compare state vs US and state vs peer_median for each metric direction.
5. Determine capacity_status from quarterly_capacity vs current_outstanding.
6. Determine external_risk_status from comparison directions.
7. Select posture enum value.
8. Build controls from segment minimum_checklist plus added operating controls.
9. Build escalation triggers with trigger_id, condition, owner.

## Pattern 8: Competing CRE Decision

**Inputs**: Two applications, branch data, loans, sector exposures, policies, FDIC benchmark
**Output**: applications_compared, recommended_path, stress, concentration, conditions

1. Fetch both applications, branch, loans, sector exposures, policies, FDIC benchmark.
2. Compute CRE weighted score for each application (5 sub-scores, weighted sum).
3. Classify each as approve_quality, conditional, or weak.
4. Run CRE dual stress: stressed_dscr = dscr * 0.85 / 1.18, breach at 1.0.
5. Compute CRE concentration:
   a. Identify all CRE-type loans (loan_type == "CRE") in branch portfolio.
   b. Sum outstanding_balance as existing_cre_exposure.
   c. existing_cre_concentration = existing_cre_exposure / total_loans_outstanding.
   d. selected_post_approval = (existing_cre_exposure + selected_requested_amount)
      / total_loans_outstanding.
   e. selected_policy_variance_bps =
      (selected_post_approval - cre_policy_limit_pct) * 10000.
   f. FDIC variance: use total_real_estate_30_89_pct benchmark.
6. Select the stronger credit (lower weighted score, non-breaching DSCR stress).
7. Assign reason codes to the unselected application.
8. Build conditions list for the selected application.

## General Numerical Rules

- Exposure and currency amounts: round to 2 decimal places.
- Ratios: round to 4 decimal places unless the template says otherwise.
- NCUA integer metrics (bps, pct): keep as integers from the API.
- Variance bps: round to 2 decimal places.
- Weighted CDFI score: round to 1 decimal place.
- Lists: sort as specified by the answer template ordering rules.
