---
name: credit-office-committee-sop
description: Produce committee-ready JSON answers for the task_group_011 credit office API tasks. Use when Codex must answer branch credit-risk, pending-application allocation, CRE comparison, watch-list stress, or credit-union segment posture prompts using only the public credit-office HTTP API and an answer_template.json.
---

# Credit Office Committee SOP

## Workflow

1. Read the prompt and `answer_template.json`; use the template as the output contract for keys, enums, sort orders, precision, and whether a field is a ratio or currency.
2. Use only the public API base URL supplied by the user. Do not inspect local environment source/data files.
3. Start with `/api/manifest` to confirm endpoints, then fetch only needed public resources:
   - `/api/branches/{branch_id}`
   - `/api/branches/{branch_id}/metrics`
   - `/api/branches/{branch_id}/loans`
   - `/api/branches/{branch_id}/sector-exposures`
   - `/api/branches/{branch_id}/applications`
   - `/api/policies`
   - `/api/benchmarks/fdic/q4-2024`
   - `/api/benchmarks/ncua/q1-2025`
   - `/api/credit-union-segments/{segment_id}`
4. Normalize list responses: command-line clients may wrap arrays as `value`, but direct HTTP JSON returns arrays.
5. Compute first, then format. Round currency to 2 decimals, ratios to 4 decimals, scores to requested precision, and bps to 2 decimals.

## Common Fields

- Use `2025Q1` branch metrics for Q1/as-of 2025-03-31 answers unless the prompt says otherwise.
- `branch_total_loans` is `total_loans_outstanding`.
- FDIC/NCUA benchmark versions come from the benchmark payload.
- Variance ratio is branch ratio minus benchmark ratio; variance bps is `variance_ratio * 10000`.
- Sort arrays exactly as requested: usually ascending ID/rating/sector, except workout queues sort by descending exposure then ascending ID.

## Risk Regrade

For loans with current rating at or worse than the prompt threshold, re-derive final rating as the worst numeric rating from available DSCR, LTV, and delinquency factors. If all such factors are missing, fall back to current rating.

DSCR ratings:

- `>= 1.50` -> 3
- `>= 1.25` -> 4
- `>= 1.05` -> 5
- `>= 1.00` -> 6
- `< 1.00` -> 7

LTV ratings:

- `<= 0.65` -> 3
- `<= 0.75` -> 4
- `<= 0.85` -> 5
- `<= 1.00` -> 6
- `> 1.00` -> 7

Delinquency minimums: `30 Days Past Due` -> 4, `60 Days Past Due` -> 5, `90+ Days Past Due` -> 7, `Nonaccrual` -> 8.

Material downgrades are final rating minus current rating greater than or equal to `risk_rating.material_downgrade_notches`.

For migration watch-list action coverage, include final ratings 6 or worse only:

- final 6 -> `watchlist`
- final 7 -> `special_assets`
- final 8+ -> `partial_chargeoff_review`

Do not include final rating 5 in action coverage.

## Watch-List Stress

Adverse-rated loans are those with `current_rating >= adverse_rating_min` from the prompt. CDFI factor score sums available policy scores for debt-to-asset, FICO, liquidity months, and LTV. Skip missing factors rather than penalizing them.

Classes: 0-5 `Prime`, 6-9 `Desirable`, 10-13 `Satisfactory`, 14-18 `Watch`, 19+ `Doubtful`, and `Projected Loss` when underwater/nonaccrual/projected-loss facts indicate loss exposure even if skipped factors keep the numeric score below 19.

Stress only loans with DSCR. Watch-list stress formula is `stressed_dscr = dscr / 1.18`; breach when stressed DSCR is below 1.00.

Workout action mapping:

- `Projected Loss` -> `partial_chargeoff_review`
- `Watch` or `90+ Days Past Due` -> `special_assets`
- `Desirable` and current -> `watchlist`

## Pending Applications

Application outputs use two approval amounts:

- `approved_amount`: gross application amount approved for the borrower.
- `bank_capacity_used`: retained bank exposure after SBA guaranty or participation.

For SBA guaranties, `bank_capacity_used = requested_amount * (1 - sba_guaranty_pct)` while `approved_amount` remains the full request.

Use `conditional_approve` with condition `participation_required` for strong credits needing retained-exposure mitigation. Use `participation_required` as the decision when the template asks for a path/disposition and the selected path itself is participation.

Allocation totals:

- `gross_approved_amount` is the sum of approved gross amounts.
- `committed_capacity_amount` is the sum of retained bank exposure.
- `remaining_capacity = lending_capacity_q1 - committed_capacity_amount`.
- `priority_ranking` includes approved and conditionally approved applications only, ranked by credit strength, strategic fit, and mitigation quality.

Post-approval sector concentration:

- Denominator is `Q1 total_loans_outstanding + gross_approved_amount`.
- Exposure numerator uses current sector exposure plus gross approved amount for that sector.
- Include only sectors affected by approved/conditional approvals, including new sectors that were absent from `/sector-exposures`.
- Concentration flags should include only approvals requiring handling, usually retained-exposure participation; use boolean `flag` if the official shape does not define a string enum.

Decline reason codes should be sparse and causal. Common rules: weak DSCR, high LTV, startup risk, recent bankruptcy, low FICO, or capacity/concentration limits. Do not pile on every possible code if one or two controlled reasons explain the decision.

## CRE Comparison

For CRE decision tasks:

- Existing CRE exposure is the sum of existing loans with `loan_type == "CRE"`, not a sum of CRE-like sector names.
- CRE stress formula is `dscr * 0.85 / 1.18`; breach below 1.00.
- Weighted CRE score is separate from CDFI factor score. Use `cre_weighted_score.weights` over capacity, capital, character, collateral/exposure, and conditions. Lower is better; adverse FDIC variance and sector/CRE concentration can move an otherwise acceptable credit to conditional.
- When the selected path is participation, post-approval CRE concentration should add retained/capped bank exposure, not always the full requested amount.
- Include `updated_appraisal_before_close` when CRE collateral/concentration risk is material, even if LTV is not an outright decline reason.
- Defer, rather than decline, the weaker competing CRE request when it is not fatally deficient but loses to a stronger credit under capacity/concentration constraints.

## Credit-Union Segment Posture

Use NCUA rows for exact integer state metrics. Compare target state to `US` and to the median of named peer states; peer state list is sorted ascending in the output.

Preserve source checklist gate order from the segment payload. Added controls come from segment issues and posture: insurance binder verification, lien perfection, senior second review, monthly segment delinquency watch, and quarterly state benchmark monitoring.

Escalation trigger IDs use `ET001`, `ET002`, `ET003`, sorted ascending. Include only triggered conditions that match the segment facts; do not include every allowed enum.

For the North Carolina fire/EMS pattern, external risk is weaker when delinquency and loan-to-share are higher while ROAA and positive-net-income share are lower than both national and peer medians. Capacity can still be available with a `continue_with_tighter_conditions` posture.

## Pitfalls

- Do not use local env/data files when the API is available.
- Do not use current rating itself as a regrade factor except as a no-data fallback.
- Do not include final-rating-5 loans in migration action coverage.
- Do not compute post-approval concentration on the old loan denominator.
- Do not use gross requested amount where retained bank exposure is required.
- Do not sort checklist gates alphabetically when the segment payload provides a deliberate order.
- Do not treat all allowed enum values as required output rows.
