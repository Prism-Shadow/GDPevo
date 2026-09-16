---
name: credit-office-committee-json
description: Solve credit office public-API committee packet tasks by deriving branch, loan, application, benchmark, and credit-union metrics into the requested JSON template.
---

# Credit Office Committee JSON

Use this skill when a task asks for a committee-ready JSON answer using the shared credit office API. The task will provide a base URL placeholder and an `input/payloads/answer_template.json` shape. Always return only valid JSON matching that template.

## Operating Rules

1. Read the prompt and answer template first. Treat the template as the output contract for keys, enums, ordering, and precision.
2. Fetch public API data from the task base URL. Useful endpoints are:
   - `/api/manifest`
   - `/api/policies`
   - `/api/benchmarks/fdic/q4-2024`
   - `/api/benchmarks/ncua/q1-2025`
   - `/api/branches`
   - `/api/branches/{branch_id}`
   - `/api/branches/{branch_id}/metrics`
   - `/api/branches/{branch_id}/loans`
   - `/api/branches/{branch_id}/sector-exposures`
   - `/api/branches/{branch_id}/applications`
   - `/api/credit-union-segments/{segment_id}`
3. Use the latest quarter in branch metrics unless the prompt specifies otherwise. Keep full precision during calculations; round only when writing the final JSON.
4. Sort exactly as the template says. If it says a set, use a stable deterministic order, preferably the enum/template order unless a sort order is specified.
5. Do not include prose outside the JSON.

## Task Dispatch

Use the template top-level keys to identify the workstream:

- `portfolio_regrade`: branch loan rating migration review.
- `allocation`: pending application allocation package.
- `posture` and `state_metrics`: credit-union segment posture page.
- `watch_list_summary`: adverse-rated watch-list stress packet.
- `applications_compared`: competing CRE application decision.

## Shared Calculations

Currency fields are rounded to 2 decimals. Ratio fields are rounded to the precision in the template, usually 4 decimals. Basis points are `ratio * 10000`, rounded to 2 decimals when requested.

For FDIC variance fields:

```text
branch_ratio = branch_metric / relevant_total
variance_ratio = branch_ratio - fdic_benchmark_ratio
variance_bps = variance_ratio * 10000
```

For direct branch delinquency comparisons, use the latest `delinquency_30_plus_pct` metric. For NPA comparisons, use `nonperforming_loans / total_loans_outstanding`.

## Branch Rating Migration

Fetch branch details, latest metrics, loans, policies, and FDIC benchmarks.

Target loans are those whose `current_rating` is at least the minimum named in the prompt or template. Re-derive each target loan's final rating from objective policy factors, not by anchoring to the current rating:

- DSCR thresholds from policy:
  - `dscr >= 1.50` -> rating 3
  - `1.25 <= dscr < 1.50` -> rating 4
  - `1.05 <= dscr < 1.25` -> rating 5
  - `1.00 <= dscr < 1.05` -> rating 6
  - `dscr < 1.00` -> rating 7
- LTV thresholds from policy:
  - `ltv <= 0.65` -> rating 3
  - `0.65 < ltv <= 0.75` -> rating 4
  - `0.75 < ltv <= 0.85` -> rating 5
  - `0.85 < ltv <= 1.00` -> rating 6
  - `ltv > 1.00` -> rating 7
- Payment status minimums from policy:
  - `30 Days Past Due` -> rating at least 4
  - `60 Days Past Due` -> rating at least 5
  - `90+ Days Past Due` -> rating at least 7
  - `Nonaccrual` -> rating at least 8

The final rating is the worst numeric rating from available DSCR, LTV/collateral, and delinquency factors. If none are available, keep the current rating.

Build:

- `target_loan_count` and `target_exposure` from the target population.
- `final_rating_exposure_totals` grouped by final rating, ordered ascending by rating.
- `migration_from_current_rating_3` from target loans whose current rating is 3, grouped by final rating with sorted loan IDs.
- `material_downgrades` where `final_rating - current_rating` is at least the policy material-downgrade notch threshold, sorted by loan ID.
- `watch_list_action_coverage` for loans whose final rating requires follow-up. Map final ratings 6, 7, and 8+ to `watchlist`, `special_assets`, and `partial_chargeoff_review`, respectively. Group by action, sort action groups alphabetically if the template says ascending by action, and sort loan IDs.
- `top_problem_credit` as the loan with the highest final rating; break ties by more severe payment status, then larger exposure.

For NPA benchmark output, use the FDIC benchmark metric named by the prompt/template. Use the manifest benchmark version string if the output asks for it.

## Watch-List Stress Packet

Fetch branch details, loans, policies, and metrics if needed. The prompt defines the adverse population, commonly `current_rating >= 6`.

Calculate CDFI-style factor score by summing available factor scores from policy. Skip missing factors rather than assigning a penalty.

- Debt-to-asset and LTV:
  - `< 0.40` -> 0
  - `0.40-0.60` -> 2
  - `0.60-0.80` -> 4
  - `> 0.80` -> 6
- FICO:
  - `> 720` -> 0
  - `680-720` -> 1
  - `580-679` -> 3
  - `< 580` -> 5
- Liquidity months:
  - `> 12` -> 0
  - `6-12` -> 1
  - `3-6` -> 3
  - `< 3` -> 5

Classify by policy score ranges. Use `Projected Loss` for severe underwater/nonaccrual credits when objective factors support projected loss treatment; otherwise use the score range class.

For the watch-list stress:

```text
stressed_dscr = dscr / (1 + 0.18)
```

Use only adverse loans with DSCR available in stress results. `breaches_threshold` is true when stressed DSCR is below the policy threshold. Sort stress rows and breach IDs by loan ID.

Workout action mapping:

- `Nonaccrual`, projected loss, or underwater collateral with severe status -> `partial_chargeoff_review`
- `90+ Days Past Due` or rating 7+ -> `special_assets`
- rating 6 or weaker current credit without severe delinquency -> `watchlist`
- otherwise -> `monitor`

Sort the workout queue by descending exposure, then ascending loan ID. For severe bucket counts, group adverse loans by `current_rating` and `payment_status`; sort by current rating, then payment-status string.

Use monthly monitoring when the adverse population contains severe ratings, stress breaches, or noncurrent credits.

## Pending Application Allocation

Fetch branch details, latest metrics, sector exposures, applications, policies, and benchmarks if reason codes require them.

Screen every pending application. Keep decisions and reason codes to the template enums.

Common reason-code triggers:

- `weak_dscr`: DSCR below policy comfort, or stressed DSCR below threshold when stress is required.
- `high_ltv`: LTV materially above collateral tolerance, especially above 0.80 for business or CRE-type credit.
- `low_fico`: FICO below 580.
- `recent_bankruptcy`: bankruptcy within roughly 24 months.
- `startup_risk`: short operating history, especially under 2 years without a strong guaranty/SBA mitigant.
- `underwater_collateral`: LTV above 1.00.
- `documentation_gap`: incomplete documentation.
- `capacity_limit`: branch capacity or retained-exposure capacity is insufficient.
- `sector_breach`: approval would worsen a sector or CRE limit without acceptable mitigation.
- `fdic_adverse_variance` or `ncua_peer_weakness`: benchmark comparison is materially adverse and the template allows the code.

Decision approach:

- Decline hard-stop applications with unmitigated low FICO/recent bankruptcy, weak DSCR plus high LTV, underwater collateral, missing core documentation, or unmitigated capacity/sector breaches.
- Approve clean applications that fit branch capacity and concentration limits.
- Use `conditional_approve` with conditions for viable applications needing participation, reduced amount, SBA guaranty, startup monitoring, board exception, or similar mitigants.
- For SBA-guaranteed approvals, `approved_amount` is the full requested amount and `bank_capacity_used = requested_amount * (1 - sba_guaranty_pct)`.
- For participations, `approved_amount` is usually the full borrower request, while `bank_capacity_used` is the retained bank amount that fits the binding sector or branch capacity.

When a sector limit is binding, compute the maximum retained amount after already selected committed bank exposures:

```text
retained_x = (limit_pct * (existing_total_exposure + committed_other) - current_sector_exposure) / (1 - limit_pct)
```

Cap `retained_x` between 0 and the requested amount. If the request is larger than `retained_x` but still viable, use `participation_required` or `conditional_approve` with `participation_required`.

Allocation fields:

- `gross_approved_amount`: sum full approved amounts for approve and conditional-approve paths.
- `committed_capacity_amount`: sum retained bank capacity used.
- `remaining_capacity`: branch `lending_capacity_q1 - committed_capacity_amount`.
- `priority_ranking`: approved and conditionally approved application IDs only, ordered from strongest committee priority to weakest. Rank by credit quality, DSCR/LTV, guarantor strength, relationship depth, mitigants, and strategic fit; do not rank declined applications.

Post-approval concentration view:

```text
denominator = sum(current sector exposures) + gross_approved_amount
exposure_after_approval = current_sector_exposure + gross approved amount in that sector
post_approval_pct = exposure_after_approval / denominator
```

Use each sector's override `limit_pct` when present; otherwise use the branch default sector ceiling. Include concentration flags for applications requiring special handling or ending near/over limit. Sort declined reason-code lists alphabetically.

## Competing CRE Decision

Fetch branch details, latest metrics, loans, sector exposures, applications, policies, and FDIC benchmarks. Compare only the application IDs named in the prompt.

CRE stress uses the policy dual-stress formula:

```text
stressed_dscr = dscr * 0.85 / (1 + 0.18)
```

Use threshold 1.00 unless policy/template says otherwise. A stressed DSCR below threshold triggers `weak_dscr`.

Existing CRE exposure is the sum of outstanding balances for loans with `loan_type == "CRE"`. Existing CRE concentration is:

```text
existing_cre_exposure / latest_total_loans_outstanding
```

Selected post-approval CRE concentration is:

```text
(existing_cre_exposure + selected_requested_amount) /
(latest_total_loans_outstanding + selected_requested_amount)
```

Policy variance bps is `(selected_post_approval_cre_concentration - branch.cre_policy_limit_pct) * 10000`.

Weighted CRE score:

1. Use policy weights for `capacity`, `capital`, `character`, `collateral_exposure`, and `conditions`.
2. Score `capacity` from DSCR, floored worse when the CRE stress breaches threshold: strong coverage 0, acceptable coverage 2, thin coverage 4, sub-1.00 coverage 6.
3. Score `capital` from debt-to-asset using the CDFI debt-to-asset table.
4. Score `collateral_exposure` from LTV using the CDFI LTV table.
5. Score `character` from guarantor strength, prior delinquencies, relationship history, FICO, and bankruptcy where available: strong clean support is 0, standard/mixed support is 2, weak or absent support is 4 or worse.
6. Score `conditions` from objective external and portfolio conditions: assign adverse points for FDIC underperformance, existing CRE limit breach, sector breach or grandfathered sector worsening, and stressed DSCR breach. Cap extreme condition scores so the weighted score remains a concise one-decimal committee score.
7. Weighted score is `sum(component_score * policy_weight)`, rounded to 1 decimal. Lower is better.

Map score class from policy: at or below the approve-quality max is `approve_quality`; at or below the conditional max is `conditional`; above that is `weak`.

Choose the lower-score application unless hard-stop reason codes require otherwise. If the stronger credit breaches CRE/sector concentration but is otherwise acceptable, the recommended path is usually `participation_required` or `conditional_approve` with concentration controls. Defer or decline the unselected application using sorted reason codes allowed by the template.

Typical CRE concentration/credit conditions include retained exposure caps, committee CRE exception, updated appraisal, tenant-roll review, DSCR covenant, quarterly reporting, and no additional CRE without committee review. Include only enum values supported by the template and sort as requested.

## Credit-Union Segment Posture

Fetch manifest, policies, NCUA benchmark, and `/api/credit-union-segments/{segment_id}`.

`state_metrics` comes directly from the NCUA row for the segment `state_code`. Use exact integer benchmark values and the benchmark version string.

Peer comparison:

1. Sort `peer_states` ascending.
2. Compare the segment state to the `US` row for `nc_vs_us`.
3. Compute each peer metric median and compare the segment state to the peer median for `nc_vs_peer_median`.
4. Direction values are `higher`, `lower`, or `equal`.

Posture and interpretation:

- `capacity_available`: quarterly capacity remains available.
- `capacity_constrained`: capacity is tight or would need an exception.
- `no_capacity`: no practical capacity remains.
- `stronger_than_national_and_peers`: state metrics are broadly better than both US and peers.
- `weaker_than_national_and_peers`: delinquency and leverage are higher while earnings/profitability are lower versus both US and peers.
- `mixed_vs_national_and_peers`: anything in between.
- Use the segment `risk_tolerance` if the template asks for it.
- If capacity exists but external risk is weaker, posture is normally `continue_with_tighter_conditions`, with committee message `capacity_available_but_external_risk_weaker`.
- If no capacity or external risk is severely weak, use `temporarily_pause` and the pause message.
- If capacity and external metrics are supportive, use `continue_approving` and the routine approval message.

Controls:

- `required_checklist_gates`: use the segment `minimum_checklist`.
- Add insurance binder verification when context mentions missing insurance.
- Add lien perfection control when collateral/lien/UCC controls are relevant.
- Add senior underwriter second review when staffing or underwriting constraints appear.
- Add quarterly state benchmark monitoring and monthly segment delinquency watch when external metrics are weak or internal delinquency is elevated.
- Add committee capacity exception control only when capacity is constrained or an overrun is requested.

Escalation triggers should use controlled enum conditions and owners:

- Segment delinquency threshold trigger -> `credit_risk_manager`
- Missing insurance or lien exception -> `operations_control_manager`
- Capacity exceeded or exception requested -> `lending_committee_chair`
- State delinquency gap widening -> `credit_risk_manager`

Assign stable trigger IDs in ascending order such as `ET001`, `ET002`, and so on, and sort by trigger ID.

## Final Validation

Before answering:

1. Confirm every required top-level key is present and no extra narrative text exists.
2. Confirm enums exactly match the template.
3. Confirm sorting and rounding.
4. Recompute sums from unrounded data and verify grouped totals equal their parent totals after normal currency rounding.
