---
name: credit-office-committee-json
description: Solve credit office public API lending-committee JSON tasks, including branch loan regrades, pending application allocation, CRE comparisons, watch-list stress reviews, and credit-union segment posture packets.
---

# Credit Office Committee JSON

Use this skill when a task asks for a committee-ready JSON answer based on the shared credit office public API and an `input/payloads/answer_template.json` file.

## Core Workflow

1. Read the task prompt and the answer template before fetching data.
2. Identify the target object: `branch_id`, `segment_id`, named `application_id`s, review/as-of date, benchmark period, adverse-rating threshold, and required JSON keys.
3. Use the task environment base URL from the runner or prompt. Fetch only public read endpoints:
   - `/api/manifest`
   - `/api/policies`
   - `/api/benchmarks/fdic/q4-2024`
   - `/api/benchmarks/ncua/q1-2025`
   - `/api/branches/{branch_id}`
   - `/api/branches/{branch_id}/metrics`
   - `/api/branches/{branch_id}/loans`
   - `/api/branches/{branch_id}/sector-exposures`
   - `/api/branches/{branch_id}/applications`
   - `/api/credit-union-segments/{segment_id}`
4. Treat `/api/policies` as authoritative for thresholds, weights, stress formulas, versions, and allowed mitigations. Do not hard-code benchmark values; fetch them.
5. Use the metric row matching the prompt date/quarter. For quarter-end dates like March 31, use `2025Q1`; otherwise use the most recent row unless the prompt specifies another quarter.
6. Build exactly the template shape. Preserve required keys, enum spellings, requested ordering, precision, and JSON-only output.

## Precision And Ordering

- Currency and exposure fields: round to 2 decimals.
- Ratios: round to the template precision, usually 4 decimals.
- Basis points: `(ratio_variance * 10000)`, rounded to 2 decimals when requested.
- Lists sorted by identifier should use lexical ascending order.
- For grouped exposure totals, sum unrounded source values first, then round the emitted total.
- If a template says a field is a set, still emit a stable list ordered as the template choices or alphabetically when no template order is obvious.

## Risk Rating Regrade

For branch rating migration reviews:

1. Fetch branch details, metrics, loans, policies, and FDIC benchmark data.
2. Select loans in the prompt population, usually `current_rating >= target_current_rating_min`.
3. Re-derive each selected loan's final rating using the policy risk-rating rules:
   - DSCR thresholds map to ratings from best to worst.
   - LTV/collateral thresholds map to ratings from best to worst.
   - Payment status applies policy delinquency minimums.
   - Final rating is the worst numeric rating from all available DSCR, LTV/collateral, and delinquency factors. Ignore missing factors rather than assigning a penalty unless policy says otherwise.
4. Aggregate final-rating exposure totals by final rating.
5. For requested migrations from a starting rating, filter original `current_rating`, group by final rating, and include sorted loan IDs.
6. Material downgrades are `final_rating - current_rating >= policies.risk_rating.material_downgrade_notches`; sort by loan ID.
7. Watch-list follow-up coverage normally includes final ratings requiring action:
   - rating 6: `watchlist`
   - rating 7: `special_assets`
   - rating 8 or clear projected-loss/nonaccrual case: `partial_chargeoff_review`
   - rating 5 only when the prompt asks for monitor coverage: `monitor`
8. Choose the top problem credit by most severe final rating, then most severe payment status, then exposure. Include borrower, exposure, current/final rating, payment status, and recommended action.
9. NPA benchmark variance:
   - `branch_npa_exposure = metrics.nonperforming_loans`
   - `branch_total_loans = metrics.total_loans_outstanding`
   - `branch_npa_ratio = branch_npa_exposure / branch_total_loans`
   - `variance_ratio = branch_ratio - fdic_metric_ratio`
   - `variance_bps = variance_ratio * 10000`

## Pending Application Allocation

For branch pending-application packages:

1. Fetch branch details, latest metrics, sector exposures, applications, and policies.
2. Evaluate each application for hard risk reasons using controlled template reason codes:
   - `weak_dscr`: DSCR below policy floor or stressed DSCR breaches the required threshold.
   - `high_ltv`: LTV exceeds the relevant policy/collateral tolerance.
   - `low_fico`: FICO is materially below policy consumer floor.
   - `recent_bankruptcy`: recent bankruptcy is reported.
   - `startup_risk`: operating history is short; SBA guaranty and monitoring can mitigate.
   - `documentation_gap`: `documentation_complete` is false.
   - `sector_breach`: approval worsens a sector or CRE concentration above its limit without mitigation.
   - `capacity_limit`: bank-retained exposure cannot fit branch capacity or a capped sector.
   - `fdic_adverse_variance` or `ncua_peer_weakness`: external benchmark weakness is material and the template permits the code.
3. Use decisions conservatively:
   - `approve` for applications passing credit, capacity, and concentration checks without special mitigation.
   - `conditional_approve` when approval needs SBA guaranty, monitoring, reduced amount, board exception, or other template condition.
   - `participation_required` when the full gross request can be approved only by limiting bank-retained exposure.
   - `defer` when the credit is not selected in a competing allocation but is not an outright decline.
   - `decline` for hard policy failures or unmitigated capacity/concentration failures.
4. Track both gross and retained exposure:
   - `approved_amount` is normally the gross request approved.
   - `bank_capacity_used` is the retained exposure after participation, guaranty, or reduction.
   - With an SBA guaranty, retained exposure is usually `requested_amount * (1 - sba_guaranty_pct)`.
   - With participation, cap retained exposure so pro-forma retained sector exposure stays at or below its limit when possible.
5. Allocation totals:
   - `gross_approved_amount = sum(approved_amount for approved/conditional/participation_required)`
   - `committed_capacity_amount = sum(bank_capacity_used for approved/conditional/participation_required)`
   - `remaining_capacity = branch.lending_capacity_q1 - committed_capacity_amount`
6. Post-approval concentration views generally use gross approved exposure:
   - numerator: current sector exposure plus approved gross amounts in that sector
   - denominator: latest total loans outstanding plus total gross approved amount
   - compare to the sector-specific `limit_pct` from sector exposures, falling back to branch default.
7. Emit concentration flags for applications that breach, approach, or require handling for a sector limit. Sort as the template requires.
8. Priority rankings include only approved, conditional, and participation-required applications. Rank stronger credits and committee priorities first; when unclear, prefer stronger DSCR, lower LTV, stronger guaranty/relationship, and mitigated concentration use.

## CRE Competing Decisions

For tasks comparing CRE applications:

1. Fetch the named applications, branch details, latest metrics, existing loans, sector exposures, policies, and FDIC benchmark data.
2. Existing CRE exposure is the sum of existing loans with `loan_type == "CRE"`; CRE concentration is existing CRE exposure divided by latest total loans.
3. Compute CRE dual-stress using the policy expression, typically `stressed_dscr = dscr * 0.85 / (1 + 0.18)`, and compare to the policy coverage threshold.
4. Compute weighted CDFI score using `policies.cre_weighted_score.weights`. Lower is better.
   - Capacity: DSCR and stressed repayment coverage.
   - Capital: debt-to-asset, deriving `total_debt / total_assets` when needed.
   - Character: guarantor strength, prior delinquencies, relationship depth, bankruptcy, and documentation.
   - Collateral/exposure: LTV and collateral support.
   - Conditions: sector/CRE concentration, branch capacity, benchmark underperformance, and external conditions.
5. Map weighted score to the policy classes: approve-quality up to the lower max, conditional up to the next max, weak above that.
6. Add reason codes from objective failures: stressed DSCR breach, high LTV, sector/CRE breach, FDIC adverse variance, documentation gaps, and other template-approved reasons.
7. Select the stronger application by lower score, stress pass, better collateral, and feasible concentration handling. If the selected credit still worsens an over-limit CRE book, use a conditional or participation path and include committee/retained-exposure conditions.
8. CRE concentration for the selected path:
   - `selected_post_approval_cre_concentration = (existing_cre_exposure + selected_gross_amount) / (latest_total_loans + selected_gross_amount)`
   - `selected_policy_variance_bps = (selected_post_approval_cre_concentration - branch.cre_policy_limit_pct) * 10000`
9. FDIC delinquency variance usually compares branch `delinquency_30_plus_pct` to `total_real_estate_30_89_pct` for CRE delinquency tasks.

## Watch-List Stress And Workout Queue

For adversely rated loan watch-list packets:

1. Select loans with `current_rating >= adverse_rating_min` from the prompt.
2. `adverse_balance` is the selected loans' outstanding balance total.
3. Compute CDFI factor score from available objective factors using policy tables:
   - debt-to-asset score
   - LTV score
   - liquidity-months score
   - FICO score when present
   Missing factors contribute no points unless the prompt or policy says otherwise.
4. Map factor score to CDFI class using policy class ranges. Override to `Projected Loss` for underwater collateral with nonaccrual or similarly clear loss facts when the template asks for projected-loss identification.
5. Watch-list DSCR stress uses the policy formula, typically `stressed_dscr = dscr / (1 + 0.18)`, with shock label from policy. Include only loans with DSCR available.
6. `breaches_threshold` is true when stressed DSCR is below the policy threshold; `breach_loan_ids` are sorted ascending.
7. Workout queue includes the selected adverse population sorted by descending exposure, then loan ID. Recommended actions:
   - current/final rating 6: `watchlist`
   - current/final rating 7 or 90+ days past due: `special_assets`
   - rating 8, nonaccrual, projected loss, or underwater collateral with loss indication: `partial_chargeoff_review`
   - use `workout` or `legal_referral` only when the prompt/data clearly points there and the template permits it.
8. Severe bucket counts group selected loans by current rating and payment status; sort by current rating, then the template's payment-status ordering or lexical order if no order is provided.
9. Monitoring cadence is `monthly` when any selected loan is rating 7+, nonaccrual/projected loss, or breaches stress; `quarterly` for moderate watch-list populations; `semiannual` only for stable low-severity populations.

## Credit-Union Segment Posture

For segment posture pages:

1. Fetch manifest, policies, NCUA benchmark data, and the target credit-union segment.
2. Select the segment state row, the `US` row, and the segment's peer states from the NCUA benchmark.
3. For peer medians, sort the peer values and use the middle value for three peers; for even counts use the arithmetic median.
4. Direction fields compare the segment state value to the comparison value:
   - `higher` if state value is greater
   - `lower` if less
   - `equal` if equal
5. Interpret external risk with metric polarity:
   - Higher delinquency and loan-to-share are weaker.
   - Lower ROAA and positive-net-income percentage are weaker.
   - Weaker on most metrics versus both national and peers means `weaker_than_national_and_peers`; mixed signs mean `mixed_vs_national_and_peers`; stronger signs mean `stronger_than_national_and_peers`.
6. Capacity status:
   - positive current quarterly capacity: `capacity_available`
   - limited or nearly consumed capacity: `capacity_constrained`
   - no remaining capacity: `no_capacity`
7. Posture:
   - Capacity available with weaker or mixed external risk usually supports `continue_with_tighter_conditions`.
   - No capacity or severe external weakness supports `temporarily_pause`.
   - Capacity available with strong external metrics and no control issues supports `continue_approving`.
8. Required checklist gates come from the segment `minimum_checklist`, constrained to template choices.
9. Added operating controls should be tied to objective facts:
   - insurance issue: `pre_close_insurance_binder_verification`
   - lien/UCC/title issue: `lien_perfection_prior_to_funding`
   - external benchmark weakness: `quarterly_state_benchmark_monitoring`
   - elevated or near-threshold segment delinquency: `monthly_segment_delinquency_watch`
   - staffing/complexity or tighter posture: `senior_underwriter_second_review`
   - capacity overrun/exception: `committee_exception_for_capacity_overrun`
10. Escalation triggers use template IDs/owners. Include only fact-supported triggers, commonly recent segment delinquency near or above threshold, missing insurance/lien exceptions, capacity exceptions, and widening state delinquency gaps.

## Final JSON Checks

Before finalizing:

- Re-open the answer template and verify every required key is present.
- Check enum values against the template exactly.
- Confirm branch/segment/application IDs come from the prompt/API, not memory.
- Recalculate every subtotal from source rows.
- Ensure arrays are in the required order.
- Return only valid JSON, with no markdown or explanatory text.
