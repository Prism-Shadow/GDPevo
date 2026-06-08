---
name: reflection-skill-attempt-03
description: Solve task_group_011 credit-office evaluation tasks that require public HTTP API review of branch loans, pending applications, policy rules, FDIC/NCUA benchmarks, and credit-union segments, then return committee-ready JSON matching a supplied answer_template.
---

# Credit Office Evaluation SOP

Use this skill for credit-office benchmark and lending-committee JSON tasks. Work only from the task prompt, its answer template, and the public API. Do not use local env/data files when an API is available.

## API Workflow

1. Read the prompt and answer template first. Copy enum values, required keys, precision, and ordering rules exactly.
2. Query `/api/manifest` to confirm routes. Typical public routes:
   - `/api/branches/{branch_id}`
   - `/api/branches/{branch_id}/metrics`
   - `/api/branches/{branch_id}/loans`
   - `/api/branches/{branch_id}/sector-exposures`
   - `/api/branches/{branch_id}/applications`
   - `/api/policies`
   - `/api/benchmarks/fdic/q4-2024`
   - `/api/benchmarks/ncua/q1-2025`
   - `/api/credit-union-segments/{segment_id}`
3. Use the latest/as-of branch metric row, usually `2025Q1`, for current total loans, delinquency, and NPA ratios.
4. Round only at output boundaries: currency to 2 decimals, ratios to 4 decimals, basis points to 2 decimals, and weighted scores to 1 decimal where requested.
5. Sort arrays exactly as the template says. Keep controlled enum strings unchanged.

## Risk Rating Migration

For branch regrade tasks, include loans whose `current_rating` is at or above the prompt threshold, for example current rating 3 or worse.

Re-derive `final_rating` as the worst numeric result from available factors:

- DSCR: `>=1.50 -> 3`, `>=1.25 -> 4`, `>=1.05 -> 5`, `>=1.00 -> 6`, `<1.00 -> 7`.
- LTV: `<=0.65 -> 3`, `<=0.75 -> 4`, `<=0.85 -> 5`, `<=1.00 -> 6`, `>1.00 -> 7`.
- Payment status minimums from policy, especially `30 Days Past Due -> 4`, `60 Days Past Due -> 5`, `90+ Days Past Due -> 7`, `Nonaccrual -> 8`.

If no factor is available, retain the current rating. Material downgrades are final rating minus current rating greater than or equal to the policy `material_downgrade_notches`.

Action bucket rule for regrade/watch coverage:

- Final rating 5 or 6: `watchlist`.
- Final rating 7: `special_assets`.
- Final rating 8 or projected loss/nonaccrual severe credit: `partial_chargeoff_review`.

Do not emit `monitor` rows for the watch-list action coverage if the official template asks for credits needing follow-up. Top problem credit is the highest final rating, then largest exposure if tied. NPA benchmark variance is:

`branch_npa_ratio = nonperforming_loans / total_loans_outstanding`

`variance_ratio = branch_npa_ratio - fdic_benchmark_ratio`

`variance_bps = variance_ratio * 10000`

## Pending Application Allocation

For allocation packages, decide every pending application, but post-approval concentration views should include only sectors touched by approved or conditionally approved applications.

Common reason codes:

- `weak_dscr`: base DSCR below the policy/committee floor, commonly below 1.20 for general lending or stressed DSCR below 1.00 for CRE comparison.
- `high_ltv`: collateral leverage above the product/committee tolerance; in these tasks CRE/SBA can flag around or above 0.80 even if the generic risk-rating LTV band is less strict.
- `startup_risk`: business history below 2 years.
- `low_fico`: low consumer score, especially below 580.
- `recent_bankruptcy`: recent bankruptcy in the application.
- `capacity_limit`: a residual or low-priority request is not selected after the committee allocation is built, even if it has no independent credit defect.
- `sector_breach`: approval would worsen a sector or CRE concentration limit without mitigation.
- `fdic_adverse_variance` or `ncua_peer_weakness`: external benchmark is materially worse than the comparison.

SBA guarantees reduce bank capacity used: `bank_capacity_used = requested_amount * (1 - sba_guaranty_pct)`. Keep the full requested amount as `approved_amount` when the full credit is approved.

Participation/concentration mitigation:

- Use full requested amount for `gross_approved_amount`.
- Use retained bank exposure for `committed_capacity_amount`.
- For final post-approval concentration ratios, denominator is `current total_loans_outstanding + gross_approved_amount`.
- Use retained bank exposure, not full approved amount, in the sector numerator when participation is required.
- A concentration flag can be `flag: true` because the original full request would breach, while the final post-approval concentration is under limit after participation.
- In Lakeview-style packages, `decision` may be `conditional_approve` with condition `participation_required`; the concentration flag `handling` is `participation_required`.

Priority ranking contains approved and conditionally approved applications only, highest committee priority first. Favor strong strategic credits with mitigants, then clean strong credits, then guaranteed/monitored startups, then lower-risk consumer credits.

## CRE Comparison

For competing CRE requests:

1. Compare only the application IDs named in the prompt.
2. Compute stressed DSCR with the compact formula `dscr * 0.85 / 1.18`; breach threshold is `1.00`.
3. Existing CRE exposure is the sum of outstanding balances for current loans with `loan_type == "CRE"`.
4. Existing CRE concentration uses current total loans as denominator.
5. Selected post-approval CRE concentration uses `(existing_cre_exposure + selected_requested_amount) / (current total_loans_outstanding + selected_requested_amount)`.
6. Policy variance bps is `(selected_post_approval_cre_concentration - cre_policy_limit_pct) * 10000`.
7. For FDIC adverse variance in these tasks, use branch `delinquency_30_plus_pct` against FDIC `total_real_estate_30_89_pct`.

Use policy `cre_weighted_score.weights` and lower-is-better factor scores. Capacity is driven by repayment coverage, collateral exposure by LTV, capital by debt/assets, character by relationship/delinquency/guarantor strength, and conditions by documentation, sector stress, and external benchmark pressure. Classify by policy thresholds: up to 2.0 `approve_quality`, up to 3.0 `conditional`, above 3.0 `weak`.

Reason-code treatment: selected credits can still require `participation_required` when CRE/sector exposure and FDIC variance are adverse. For an unselected CRE that breaches stressed DSCR, include `weak_dscr`; do not add `high_ltv` unless LTV crosses the task's high-LTV threshold.

## CDFI Watch-List Stress

For adversely rated watch-list tasks, use loans with current rating at or above the adverse threshold, usually 6.

CDFI factor score is the sum of available policy scores for:

- Debt/assets: `<0.40 -> 0`, `0.40-0.60 -> 2`, `0.60-0.80 -> 4`, `>0.80 -> 6`.
- FICO: `>720 -> 0`, `680-720 -> 1`, `580-679 -> 3`, `<580 -> 5`.
- Liquidity months: `>12 -> 0`, `6-12 -> 1`, `3-6 -> 3`, `<3 -> 5`.
- LTV: `<0.40 -> 0`, `0.40-0.60 -> 2`, `0.60-0.80 -> 4`, `>0.80 -> 6`.

Missing factors contribute 0. Class bands are `Prime 0-5`, `Desirable 6-9`, `Satisfactory 10-13`, `Watch 14-18`, `Doubtful >=19`. Treat underwater nonaccrual/projected-loss notes as `Projected Loss` even if the factor score is below 19.

Watch-list DSCR stress is `dscr / 1.18`; include only loans with DSCR. Queue actions by severity:

- `Projected Loss` or rating 8/nonaccrual: `partial_chargeoff_review`.
- Rating 7 or 90+ past due: `special_assets`.
- Rating 6 current: `watchlist`.

Severe bucket counts group by `current_rating` and `payment_status`, sorted by rating then payment-status string.

## Credit-Union Segment Posture

For NCUA segment posture tasks:

1. Pull the segment endpoint and the NCUA benchmark table.
2. Copy the segment's `minimum_checklist` as `required_checklist_gates`, sorted if the template asks for a set.
3. Compare the segment state against `US` and the median of the named peer states for every requested metric. Direction is from the target state's perspective.
4. If delinquency and loan-to-share are higher while ROAA and positive-net-income are lower than both national and peers, use `external_risk_status: weaker_than_national_and_peers`.
5. When capacity is available but external risk is weaker, use posture `continue_with_tighter_conditions`, risk tolerance from the segment, and message `capacity_available_but_external_risk_weaker`.

Common added controls are `pre_close_insurance_binder_verification`, `lien_perfection_prior_to_funding`, `senior_underwriter_second_review`, `quarterly_state_benchmark_monitoring`, and `monthly_segment_delinquency_watch` when the segment notes binder gaps, staffing constraints, or elevated delinquency. Use escalation IDs like `ET001`, `ET002`, `ET003`; include only triggers supported by the segment facts and template choices.

## Pitfalls

- Do not divide post-approval sector concentration by current total loans only; add gross approved amount to the denominator.
- Do not use full approved exposure as bank capacity when SBA guarantees or participation reduce retained exposure.
- Do not let a mitigated concentration flag disappear; report the flag and show final `over_limit: false` when mitigation works.
- Do not map final rating 7 to `workout` in these committee outputs; use `special_assets` unless the template or policy explicitly says otherwise.
- Do not treat NCUA posture as "mixed" when every requested NC metric is worse in the risk direction than both national and peer median.
- Do not invent free-text conditions or reason codes. Use only template enums.
