---
name: task-group-011-fewshot-attempt-01
description: Prepare strict committee-ready JSON answers for task_group_011 credit-office input/output evaluation tasks using only the provided prompt, answer_template.json, and public credit-office API endpoints. Use when a task asks for branch rating migration, lending allocation, credit-union segment posture, watch-list stress/workout queues, or competing CRE application recommendations with controlled enums, ordered lists, rounded numeric fields, and no narrative outside JSON.
---

# Input-Output Credit JSON

## Guardrails

- Use only the prompt, its `input/payloads/answer_template.json`, and public HTTP API endpoints supplied by the user or printed by setup.
- Do not read local `env/`, `test_tasks/`, notes, reports, run artifacts, other generated skills, or task metadata files.
- Treat `answer_template.json` as authoritative for required keys, enums, ordering, precision, and empty-list/object behavior.
- Return one valid JSON object only. Do not include Markdown, comments, or explanatory prose outside the JSON.

## Public API Workflow

1. Read the task prompt and template. Extract target `branch_id`, `segment_id`, application IDs, as-of date, review date, rating cutoff, and requested benchmark period.
2. Discover the public API from `/api/manifest` when needed. Expected surfaces include:
   - `/api/branches/{branch_id}`
   - `/api/branches/{branch_id}/metrics`
   - `/api/branches/{branch_id}/loans`
   - `/api/branches/{branch_id}/sector-exposures`
   - `/api/branches/{branch_id}/applications`
   - `/api/policies`
   - `/api/benchmarks/fdic/q4-2024`
   - `/api/benchmarks/ncua/q1-2025`
   - `/api/credit-union-segments/{segment_id}`
3. Fetch only the surfaces relevant to the prompt. Prefer the branch/segment specified by the task rather than listing all records.
4. Use the latest relevant metric row unless the prompt specifies a quarter. For 2025-03-31 tasks, this is generally `2025Q1`; FDIC benchmark tasks use `fdic_q4_2024`; NCUA tasks use `ncua_q1_2025`.
5. Build calculations in a scratch table, then shape the final JSON from the template. Sort every list exactly as the template says.

## Numeric Conventions

- Currency fields: sum raw values, then round final outputs to 2 decimals.
- Ratio fields: output decimals, not percentages; round final outputs to 4 decimals unless the template says otherwise.
- Basis points: `(branch_ratio - benchmark_ratio) * 10000`, rounded to 2 decimals.
- Use `outstanding_balance` for loan exposure and existing portfolio sums. Use `requested_amount`, approved amount, and bank-retained amount separately for applications.
- For boolean fields, emit JSON booleans `true`/`false`, not strings.

## Rating Migration Tasks

- Filter the branch loans by the prompt's current-rating cutoff, such as `current_rating >= 3` or adversely rated `current_rating >= 6`.
- Re-derive final risk rating from public policy rules. Compute available component ratings and take the worst numeric rating:
  - DSCR: `>=1.50 -> 3`, `>=1.25 -> 4`, `>=1.05 -> 5`, `>=1.00 -> 6`, `<1.00 -> 7`.
  - LTV: `<=0.65 -> 3`, `<=0.75 -> 4`, `<=0.85 -> 5`, `<=1.00 -> 6`, `>1.00 -> 7`.
  - Payment status minimums: `30 Days Past Due -> 4`, `60 Days Past Due -> 5`, `90+ Days Past Due -> 7`, `Nonaccrual -> 8`; `Current` has no minimum.
- A material downgrade is normally `final_rating - current_rating >= policy.risk_rating.material_downgrade_notches`.
- Group rating exposure totals by final rating; group migrations by the requested starting current rating when the template asks for it.
- For NPA/noncurrent benchmark comparisons, identify nonperforming exposure from nonaccrual or public metric fields as the prompt/template implies. Divide by total loans outstanding and compare to the named FDIC metric.
- Pick the top problem credit by severity first, then exposure: nonaccrual/projected-loss indicators, highest final rating, most severe payment status, and largest exposure.

## CDFI Factor Scoring And Watch Lists

- Score objective factors from `policy.cdfi_factor_scores`:
  - Debt-to-asset, FICO, liquidity months, and LTV each contribute the bucket score shown by policy.
  - Sum only available factor scores; do not invent missing FICO or DSCR factor scores.
- Map total score to policy classes: `Prime`, `Desirable`, `Satisfactory`, `Watch`, `Doubtful`; apply `Projected Loss` when policy conditions and credit facts show loss severity, especially underwater collateral plus nonaccrual/projected-loss notes.
- For watch-list DSCR stress, use `policy.stress.watch_list_formula`: `stressed_dscr = dscr / (1 + 0.18)`. Include only loans with DSCR available, round DSCRs to 2 decimals, and flag breaches below the policy threshold.
- Queue actions by severity using controlled enum values. Use public policy, payment status, notes, and risk class together:
  - `partial_chargeoff_review` for projected loss, nonaccrual, or clear loss-review facts.
  - `special_assets` for 90+ past due, rating 7+ severity, or structurally severe credits needing active handling.
  - `watchlist` for rating 6 or stressed/weak credits needing close monitoring.
  - Use `monitor`, `workout`, or `legal_referral` only when the facts support those exact paths.

## Lending Allocation Tasks

- Start with `branch.lending_capacity_q1`. Approved applications consume bank capacity unless participation, guaranty, decline, or deferral changes the retained exposure.
- Apply policy floors and reason codes from objective facts:
  - `weak_dscr` for DSCR below policy/task minimums or stress breach.
  - `high_ltv` or `underwater_collateral` for collateral weakness.
  - `low_fico`, `recent_bankruptcy`, `startup_risk`, `documentation_gap`, or `policy_floor_missing` when those fields trigger.
  - `capacity_limit` when the remaining branch capacity cannot support the request.
  - `sector_breach` when a new approval would exceed the sector limit without mitigation.
  - `fdic_adverse_variance` or `ncua_peer_weakness` only when the relevant benchmark comparison is adverse.
- Participation may leave `approved_amount` equal to the full request while `bank_capacity_used` is capped. For sector caps, solve retained exposure so `(current_sector_exposure + retained_amount) / (current_total_loans + other_committed_retained_amounts + retained_amount) <= limit_pct`.
- For SBA guaranty, bank capacity used is usually `requested_amount * (1 - sba_guaranty_pct)` when the guaranty is the risk mitigant.
- Priority ranking includes approved and conditionally approved applications only, ordered by credit strength, strategic fit, mitigated concentration impact, and capacity use.
- Post-approval concentration views generally use full approved exposure for sector exposure and the post-approval total loan base. Mark `over_limit` after rounding only if the raw ratio exceeds the limit.

## Competing CRE Tasks

- Compare only the application IDs named by the prompt.
- Calculate the CRE weighted score from `policy.cre_weighted_score.weights`; lower is better. Use the public application facts for capacity/DSCR, capital leverage, character/relationship/delinquency, collateral/LTV/exposure, and external conditions. Round the weighted result to 1 decimal and map it to policy score classes.
- Apply the CRE dual stress from policy: `stressed_dscr = dscr * 0.85 / (1 + 0.18)`; breach threshold is usually `1.00`.
- Evaluate concentration using branch CRE limits, existing CRE/sector exposure, selected approval amount, and FDIC underperformance. Existing over-limit exposure may be grandfathered, but new approvals should not worsen it without participation or committee exception.
- Select the stronger credit by lower weighted score, stress result, collateral quality, relationship strength, and manageable concentration treatment. Give the unselected credit only enum reason codes allowed by the template.

## Credit-Union Segment Posture Tasks

- Fetch the segment and NCUA benchmark rows. Use `segment.state_code`, `segment.peer_states`, quarterly capacity, current outstanding, checklist, internal context, and risk tolerance.
- Compare the target state against `US` and the median of peer states for `delinquency_bps`, `loan_to_share_pct`, `roaa_bps`, and `positive_net_income_pct`. Output directions as `higher`, `lower`, or `equal`.
- Choose posture from capacity and external risk:
  - Use `continue_approving` only when capacity and benchmark posture are routine.
  - Use `continue_with_tighter_conditions` when capacity exists but peer/national metrics or internal controls are weaker.
  - Use `temporarily_pause` when capacity is unavailable or external/control risk is unacceptable.
- Preserve segment checklist gates. Add operating controls that directly respond to benchmark weakness, missing close controls, lien/insurance risk, capacity exceptions, or senior-review needs.
- Escalation triggers should have stable ascending IDs and owners that match the control area: credit risk for delinquency/benchmarks, operations for lien/insurance exceptions, committee chair for capacity exceptions.

## Final Validation

- Confirm all required top-level keys exist and no extra narrative is present.
- Confirm all enum strings exactly match the template.
- Confirm every list's ordering rule, including nested `loan_ids`, reason codes, trigger IDs, ratings, sectors, and application IDs.
- Confirm numeric precision after all calculations.
- Confirm output parses as JSON before submitting.
