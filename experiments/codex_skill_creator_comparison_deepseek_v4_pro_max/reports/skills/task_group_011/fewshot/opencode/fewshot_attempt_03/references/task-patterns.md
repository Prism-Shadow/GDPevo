# Credit Risk Task Patterns

Step-by-step workflows for each task type. Read the relevant section when you know which task type you are handling.

## Portfolio Regrade (Rating Migration Review)

Task signature: mentions ratings 3+, re-derive ratings, rating migration, material downgrades, NPA benchmark, top problem credit.

### Step 1: Fetch data

```
GET /api/policies
GET /api/manifest
GET /api/branches/{branch_id}
GET /api/branches/{branch_id}/loans
GET /api/branches/{branch_id}/metrics
GET /api/benchmarks/fdic/q4-2024
```

### Step 2: Identify the regrade population

Filter loans whose `current_rating` >= `target_current_rating_min` (from the prompt, e.g., 3).

### Step 3: Re-derive each loan's final rating

For every loan in the target population:
- Compute rating from DSCR (use policy thresholds)
- Compute rating from LTV (use policy thresholds; if LTV is null but collateral_value exists, compute LTV)
- Take the delinquency floor from payment_status
- Final rating = maximum of all available factor ratings

### Step 4: Compute final_rating_exposure_totals

Group regraded loans by final_rating. For each rating, count loans and sum exposure. Sort ascending by final_rating.

### Step 5: Compute migration_from_current_rating_3

Filter to loans whose `current_rating == 3`. Group by final_rating. For each group: loan_count, exposure sum, loan_ids (ascending). Sort ascending by final_rating.

### Step 6: Identify material downgrades

Any loan with `final_rating - current_rating >= 2`. List all material downgrades sorted ascending by loan_id. Include loan_id, current_rating, final_rating, downgrade_notches, exposure.

### Step 7: NPA benchmark

- NPA exposure = sum of outstanding_balance for all Nonaccrual loans across the entire branch portfolio
- branch_npa_ratio = npa_exposure / total_loans_outstanding (latest quarter)
- benchmark_version = "fdic_q4_2024"
- benchmark_metric = "total_loans_noncurrent_pct"
- fdic_benchmark_ratio: from /api/benchmarks/fdic/q4-2024
- variance_ratio = branch_npa_ratio - fdic_benchmark_ratio
- variance_bps = variance_ratio * 10000

### Step 8: Assign watch-list actions

For each loan with final_rating >= 5: assign the minimum action from the rating-action table, escalating as warranted by payment status. Group by action, sorted ascending by action. Include covered_loan_count, covered_exposure, and by_action array with loan_ids.

### Step 9: Top problem credit

Select the single worst problem credit: highest final_rating, then worst payment_status, then highest exposure as tiebreaker. Include loan_id, borrower_name, exposure, current_rating, final_rating, payment_status, recommended_action.

## Lending Allocation Package

Task signature: mentions allocation, pending applications, concentration flags, decline reasons, post-approval concentrations.

### Step 1: Fetch data

```
GET /api/policies
GET /api/manifest
GET /api/branches/{branch_id}
GET /api/branches/{branch_id}/metrics
GET /api/branches/{branch_id}/applications
GET /api/branches/{branch_id}/sector-exposures
```

### Step 2: Read capacity

lending_capacity_q1 is from the branch object.

### Step 3: Evaluate each application

For each application, check:
1. Financial strength (DSCR, LTV, FICO, debt-to-asset, liquidity)
2. Sector concentration (existing exposure + requested amount vs sector limit)
3. Capacity availability (bank's retained portion vs remaining capacity)
4. Qualitative factors (years in business, prior delinquencies, guarantor strength, relationship)

Assign decision: approve, conditional_approve (with conditions), decline, defer, or participation_required.

### Step 4: Compute allocation totals

- gross_approved_amount: sum of approved_amount across all approved and conditionally approved apps
- committed_capacity_amount: sum of bank_capacity_used across approved/conditionally approved apps
- remaining_capacity: lending_capacity_q1 - committed_capacity_amount
- priority_ranking: ordered list of approved and conditionally approved application_ids, highest priority first

### Step 5: Concentration flags

For each sector that has an approved or conditionally approved application: compute post_approval_pct. Flag when post_approval_pct > limit_pct.

### Step 6: Decline reasons

For each declined application, list the reason codes from the template enum that apply.

### Step 7: Post-approval concentrations

For each sector: exposure_after_approval = existing_exposure + sum of approved amounts in that sector. Compute post_approval_pct and over_limit flag.

## Credit Union Segment Posture

Task signature: mentions credit union segment, segment_id, NCUA benchmarks, posture recommendation, peer comparison, controls, escalation triggers.

### Step 1: Fetch data

```
GET /api/policies
GET /api/manifest
GET /api/credit-union-segments/{segment_id}
GET /api/benchmarks/ncua/q1-2025
```

### Step 2: State metrics

Find the state row in NCUA data matching the segment's state_code. Extract delinquency_bps, loan_to_share_pct, roaa_bps, positive_net_income_pct.

### Step 3: Peer comparison

Get peer_states from segment data. Find rows for each peer state in NCUA data. Compute peer_median for each metric. Compare NC vs US (national row) and NC vs peer_median: "higher", "lower", or "equal".

### Step 4: Posture

Based on state metrics vs benchmarks:
- If metrics are weaker than national and peers but internal capacity remains → `continue_with_tighter_conditions`
- If metrics are strong and capacity available → `continue_approving`
- If metrics are severely weak → `temporarily_pause`

### Step 5: Controls

required_checklist_gates: from the segment's minimum_checklist field.
added_operating_controls: select from template enum based on identified risks and the segment's internal_context.control_issue.

### Step 6: Escalation triggers

Select 3-4 from the template's condition_choices based on segment risks. Assign each to an owner from the template.

### Step 7: Interpretation

capacity_status: based on quarterly_capacity and outstanding.
external_risk_status: based on peer comparison results.
risk_tolerance: from segment data.
committee_message: from template enum that matches the combination.

## Watch-List Stress and Workout

Task signature: mentions watch-list stress, adverse-rated loans, rating 6+, CDFI risk classes, DSCR stress, workout queue, severe bucket counts.

### Step 1: Fetch data

```
GET /api/policies
GET /api/manifest
GET /api/branches/{branch_id}
GET /api/branches/{branch_id}/loans
GET /api/branches/{branch_id}/metrics
```

### Step 2: Identify adverse population

Filter loans with current_rating >= adverse_rating_min (from prompt, e.g., 6).

### Step 3: CDFI risk class assignment

For each adverse loan, compute the CDFI factor score (fico + ltv + debt_to_asset + liquidity_months). Null factors score 0. If LTV null but collateral_value exists, compute LTV first. Map total score to risk_class.

### Step 4: Monitoring cadence

Based on the risk class distribution: if any Projected Loss or Doubtful → "monthly". If mostly Watch → "quarterly". If mostly Desirable or better → "semiannual".

### Step 5: DSCR stress

For each adverse loan with DSCR available:
- stressed_dscr = dscr / (1 + 0.18)
- breaches_threshold = (stressed_dscr < 1.0)
Sort results ascending by loan_id. Collect breach_loan_ids ascending.

### Step 6: Workout queue

All adverse loans, ordered by descending exposure, then ascending loan_id. Assign recommended_action based on risk_class and payment_status:
- Projected Loss + Nonaccrual → partial_chargeoff_review, projected_loss: true
- Watch + Current → special_assets, projected_loss: false
- 90+ Days Past Due → special_assets, projected_loss: false
- Desirable risk class with stress breach → watchlist
- Others: escalate based on payment_status severity

### Step 7: Severe bucket counts

For the full branch portfolio (not just adverse), group loans with current_rating >= 6 by (current_rating, payment_status). Count loans and sum exposure. Sort ascending by current_rating, then payment_status.

## Competing CRE Decision

Task signature: mentions competing CRE, two applications to compare, weighted CRE score, dual stress, concentration, recommended path.

### Step 1: Fetch data

```
GET /api/policies
GET /api/manifest
GET /api/branches/{branch_id}
GET /api/branches/{branch_id}/metrics
GET /api/branches/{branch_id}/applications
GET /api/branches/{branch_id}/loans
GET /api/branches/{branch_id}/sector-exposures
GET /api/benchmarks/fdic/q4-2024
```

### Step 2: Compute weighted CDFI scores

For each of the two applications, compute the CDFI factor score from the available application fields (same factors: fico, ltv, debt_to_asset, liquidity_months — use application data where available). Then apply the CRE weighted-score dimensions:
- capacity: branch capacity utilization
- capital: branch capital position
- character: applicant credit factors (FICO, prior delinquencies, relationship)
- collateral_exposure: LTV and concentration risk
- conditions: loan purpose, term, existing relationship, years in business

Compute weighted sum using policy weights. Lower is better.

### Step 3: Assign score class and decision

Map weighted score to class (approve_quality, conditional, weak). Assign decision and reason codes per application.

### Step 4: Recommended path

Select the stronger application (lower weighted score). If tied, prefer better DSCR. Assign path and unselected disposition.

### Step 5: Stress test

Apply CRE dual-stress formula to both applications: stressed_dscr = dscr * 0.85 / (1 + 0.18). Report base_dscr, stressed_dscr, and breach for each.

### Step 6: Concentration analysis

- cre_policy_limit_pct: from branch
- existing_cre_exposure: sum of outstanding_balance for all CRE-type loans in the branch
- existing_cre_concentration: existing_cre_exposure / total_loans_outstanding
- selected_post_approval_cre_concentration: (existing_cre_exposure + selected_amount) / total_loans_outstanding
- selected_policy_variance_bps: (selected_post_approval_cre_concentration - cre_policy_limit_pct) * 10000
- fdic_benchmark_metric: "total_real_estate_30_89_pct"
- branch_delinquency_ratio: from branch metrics delinquency_30_plus_pct
- fdic_benchmark_ratio: from FDIC data
- fdic_variance_ratio and fdic_variance_bps: computed as difference

### Step 7: Conditions

Select applicable conditions from template enum based on risk factors identified.
