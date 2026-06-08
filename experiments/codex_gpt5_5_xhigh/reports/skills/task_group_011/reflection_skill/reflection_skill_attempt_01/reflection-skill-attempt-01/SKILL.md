---
name: reflection-skill-attempt-01
description: Solve task_group_011 credit-office committee JSON evaluations using only the public credit API. Use for branch rating migration, lending allocation, credit-union segment posture, watch-list stress, and competing CRE application tasks that reference the shared credit office API, FDIC/NCUA benchmarks, policies, branch loans, metrics, sector exposures, and pending applications.
---

# Credit Office Committee JSON SOP

## Access Rules

Use only the public API base URL supplied in the task, commonly `http://127.0.0.1:8028`. Do not read local environment data, source files, test tasks, notes, reports, generated skills, or private folders. Read only the task prompt and `input/payloads/answer_template.json`, then query public endpoints.

Start with:

- `GET /api/manifest` for endpoint names and benchmark versions.
- `GET /api/policies` for rating thresholds, stress formulas, score weights, capacity rules, and enums.
- Branch tasks: `GET /api/branches/{branch_id}`, `/metrics`, `/loans`, `/sector-exposures`, and `/applications` as needed.
- Benchmarks: `GET /api/benchmarks/fdic/q4-2024` or `/api/benchmarks/ncua/q1-2025`.
- Segment tasks: `GET /api/credit-union-segments/{segment_id}`.

Build the answer directly from the template. Preserve required keys, enum spellings, list ordering, and numeric precision. Round currency to 2 decimals, ratios to 4 decimals, and basis points to 2 decimals. Compute bps as `ratio * 10000`. Use `2025Q1` branch metrics for March 31, 2025 reviews unless the prompt asks otherwise.

## Rating Migration Reviews

Population: loans for the target branch with `current_rating >= target_current_rating_min`.

Re-derive final rating from objective factors:

- DSCR: `>=1.50 -> 3`, `>=1.25 -> 4`, `>=1.05 -> 5`, `>=1.00 -> 6`, `<1.00 -> 7`.
- LTV: `<=0.65 -> 3`, `<=0.75 -> 4`, `<=0.85 -> 5`, `<=1.00 -> 6`, `>1.00 -> 7`.
- Delinquency minimums: `30 Days Past Due -> 4`, `60 Days Past Due -> 5`, `90+ Days Past Due -> 7`, `Nonaccrual -> 8`.
- Final rating is the worst numeric rating from available objective factors. Do not use current rating as a floor when objective factors support an improved grade. If no objective factor is available, keep the current rating.

Material downgrade means `final_rating - current_rating >= policies.risk_rating.material_downgrade_notches`.

Watch-list action coverage should include credits needing follow-up, normally final rating `>=6` or explicit severe actions. Do not include ordinary `monitor` entries for rating 4 or 5 just because the loan is in the regrade population. Recommended action mapping:

- `Nonaccrual` with LTV above 1.0 or projected-loss evidence -> `partial_chargeoff_review`.
- Final rating 7 -> `special_assets`.
- Final rating 6 -> `watchlist`.
- Lower ratings usually receive no watch-list action in coverage.

NPA benchmark:

- Use branch metric `nonperforming_loans / total_loans_outstanding`.
- Use FDIC `total_loans_noncurrent_pct` unless the prompt specifies a real-estate or construction benchmark.
- `variance_ratio = branch_ratio - benchmark_ratio`.

## Lending Allocation Packages

For pending applications, combine policy-quality rules with capacity and concentration.

Decline obvious policy problems using controlled reason codes:

- Weak DSCR: generally DSCR below 1.20 for business credits.
- High LTV: generally LTV above 0.80 for ordinary applications; for CRE competing-decision reason codes, use a stricter material breach such as above 0.80, not a marginal 0.76.
- Low FICO: below 600.
- Recent bankruptcy: bankruptcy within about 24 months.
- Startup risk: business age below 2 years unless mitigated by SBA guaranty and relationship support.
- Capacity limit: use when an otherwise possible approval cannot fit branch/sector capacity and no mitigation is selected.
- Documentation gap: missing documentation.

Participation-required retained-capacity rule:

1. Decide the full `approved_amount` first.
2. For SBA loans, `bank_capacity_used = approved_amount * (1 - sba_guaranty_pct)`.
3. For participation caps, solve retained exposure so the retained sector concentration fits the sector limit using committed retained capacity as the denominator:

   `retained = (limit_pct * (current_total_loans + other_committed_capacity) - current_sector_exposure) / (1 - limit_pct)`

4. Cap at the requested amount and round to 2 decimals. Put `participation_required` in `conditions`, but the decision may still be `conditional_approve` if the approval proceeds with that condition.

Post-approval concentration view:

- Include sectors affected by approvals, not every sector in the branch table unless the template asks for all.
- `exposure_after_approval` uses full approved amounts, even when bank retained exposure is lower because of participation.
- `post_approval_pct = exposure_after_approval / (current_total_loans + gross_approved_amount)`.
- For new sectors absent from `/sector-exposures`, use current exposure `0` and branch `sector_ceiling_pct`.
- Concentration flag entries are for approvals requiring concentration handling. Use the template's type for `flag`; in training answers it is boolean `true`.

## Credit-Union Segment Posture

Use the segment endpoint for state, peer states, required checklist gates, capacity, risk tolerance, internal issues, and recent segment delinquency. Use NCUA rows for state metrics.

Peer comparison:

- Sort `peer_states` ascending.
- Compare NC against US and against the median of peer-state values.
- Direction values are literal numeric direction: `higher`, `lower`, or `equal`.
- Interpret risk direction separately: higher delinquency and loan-to-share are weaker; lower ROAA and positive-net-income percentages are weaker. If all four risk directions are adverse versus US and peers, use `weaker_than_national_and_peers`.

Controls:

- Required checklist gates come from `segment.minimum_checklist`, sorted according to template expectations.
- Add controls tied to observed risk: insurance binder issues -> `pre_close_insurance_binder_verification`; lien/control risk -> `lien_perfection_prior_to_funding`; staffing or constrained expertise -> `senior_underwriter_second_review`; external benchmark weakness -> `quarterly_state_benchmark_monitoring`; recent segment delinquency near 90 bps -> `monthly_segment_delinquency_watch`.

Escalation triggers should be grounded in actual segment risks. Use IDs like `ET001`, `ET002`, `ET003` sorted ascending. Avoid hypothetical triggers not supported by segment data.

## Watch-List Stress Packets

Population: target-branch loans with `current_rating >= adverse_rating_min`, usually 6.

CDFI factor score:

- Sum LTV, debt-to-asset, liquidity months, and FICO scores from policy ranges. Treat missing factors as 0.
- Classes by score: `0-5 Prime`, `6-9 Desirable`, `10-13 Satisfactory`, `14-18 Watch`, `>=19 Doubtful`.
- Override to `Projected Loss` when evidence indicates loss severity, especially nonaccrual with LTV above 1.0, current rating 8, or notes indicating projected loss review, even if the summed score is below 19.

Stress:

- Watch-list stress formula is `stressed_dscr = dscr / (1 + 0.18)` for `+200bp`.
- Include only loans with DSCR available in stress results.
- Breach threshold is `1.00`; breach if rounded stressed DSCR is below 1.00.

Workout actions:

- `Projected Loss` -> `partial_chargeoff_review`.
- Nonaccrual without projected loss -> `workout`.
- Current rating 7, 90+ past due, or structurally weak watch credits -> `special_assets`.
- Current rating 6 adverse credits -> `watchlist`, even if CDFI class is Desirable.
- Sort workout queue by descending exposure, then ascending loan ID.

Severe bucket counts group adverse loans by `current_rating` and `payment_status`; sort by current rating then payment status.

## Competing CRE Decisions

Use both `/applications` and `/loans`. For existing branch CRE exposure, sum outstanding balances from `/loans` where `loan_type == "CRE"`; do not substitute sector-exposure categories such as Construction or Hospitality.

Weighted CRE score:

- Use `policies.cre_weighted_score.weights`.
- Lower score is better. Do not reuse the watch-list CDFI factor-score scale.
- Translate score to class using policy classes: `approve_quality` up to 2.0, `conditional` up to 3.0, otherwise `weak`.
- Include concentration, stressed repayment, sponsor support, documentation, relationship, collateral, and capital leverage in component judgments. Existing branch CRE over-limit and FDIC adverse variance should push otherwise strong credits to `conditional`/`participation_required`.

Stress:

- Use CRE dual-stress formula `dscr * 0.85 / 1.18`.
- Use compact formula text if the official shape expects it.

Concentration:

- `existing_cre_concentration = existing_cre_exposure / branch_total_loans`.
- If a participation path is selected, selected post-approval CRE concentration uses the retained bank exposure, not necessarily the full requested amount.
- `selected_policy_variance_bps = (selected_post_approval_cre_concentration - cre_policy_limit_pct) * 10000`.
- Use FDIC `total_real_estate_30_89_pct` when the prompt asks for real-estate delinquency underperformance.

Reason codes and conditions:

- Selected CRE may still carry `fdic_adverse_variance` and `sector_breach` when mitigated by participation.
- Do not assign `high_ltv` to marginal CRE LTV around 0.76 if the official threshold is materially higher.
- Include `updated_appraisal_before_close` when collateral values or CRE concentration make collateral refresh important.

## Common Pitfalls

- Do not read local `env` files; the API manifest exposes all permitted routes.
- Do not make current risk rating a hard floor during regrade.
- Do not include low-risk `monitor` loans in watch-list action coverage unless the template explicitly asks for all actions.
- Do not compute post-approval sector percentages over current loans only; include approved volume in the denominator.
- Do not use sector-exposure buckets to calculate branch CRE exposure when loan-level `loan_type == "CRE"` is available.
- Do not treat textual `higher/lower` benchmark directions as risk status without considering whether higher is good or bad.
- Always sort lists exactly as the template states and keep empty/decline condition arrays to the allowed enum values.
