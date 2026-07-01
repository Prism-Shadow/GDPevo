---
name: task-group-011-fewshot-attempt-03
description: Produce committee-ready JSON answers for credit-office API tasks involving branch loan regrades, lending allocation decisions, CRE application comparisons, watch-list stress packets, and credit-union segment posture reviews. Use when a prompt provides a credit office public API base URL, branch_id or segment_id, and an answer_template.json with required fields, enum choices, ordering, and precision rules.
---

# Credit Office JSON

## Core Workflow

1. Read the user prompt and `input/payloads/answer_template.json`. Treat the template as the output contract: required keys, enum values, list ordering, numeric precision, and allowed identifiers override assumptions.
2. Use only the public API. Start with `GET /api/manifest` when available; expected public routes include:
   - `/api/branches`, `/api/branches/{branch_id}`, `/api/branches/{branch_id}/metrics`
   - `/api/branches/{branch_id}/loans`, `/api/branches/{branch_id}/sector-exposures`, `/api/branches/{branch_id}/applications`
   - `/api/policies`
   - `/api/benchmarks/fdic/q4-2024`, `/api/benchmarks/ncua/q1-2025`
   - `/api/credit-union-segments/{segment_id}`
3. Do not use local env files, database files, source data, notes, reports, runs, test task folders, or other generated skills. If setup is mentioned but the base URL is already known, call the public API directly.
4. Compute from raw API values using unrounded intermediates. Round only final JSON values to the precision in the template. Ratios are decimals, not percentages; basis points are `ratio * 10000`.
5. Emit only one valid JSON object. Do not include Markdown or explanatory text outside the JSON.

## General Output Rules

- Preserve identifiers exactly as reported by the API.
- Include all required keys even when a list is empty.
- Use only enum values present in the template.
- Sort every list exactly as the template states. If no sort is stated, use stable ascending identifier order.
- For object maps such as decline reasons, include only applicable IDs and sort each reason-code list alphabetically unless the template says otherwise.
- Prefer explicit API metric fields over reconstructing totals when both are available.

## Policy Rules To Reuse

Fetch `/api/policies` for the authoritative version, but the recurring rules are:

- Re-derived loan risk rating: take the worst numeric rating from available DSCR, LTV/collateral, and delinquency factors.
- DSCR rating thresholds: `>=1.50 -> 3`, `>=1.25 -> 4`, `>=1.05 -> 5`, `>=1.00 -> 6`, `<1.00 -> 7`.
- LTV rating thresholds: `<=0.65 -> 3`, `<=0.75 -> 4`, `<=0.85 -> 5`, `<=1.00 -> 6`, `>1.00 -> 7`.
- Delinquency minimum ratings: `30 Days Past Due -> 4`, `60 Days Past Due -> 5`, `90+ Days Past Due -> 7`, `Nonaccrual -> 8`; `Current` has no floor.
- Material downgrade means `final_rating - current_rating >= material_downgrade_notches` from policy, usually 2.
- Watch-list stress: use policy `watch_list_formula`, normally `stressed_dscr = dscr / (1 + 0.18)`, label `+200bp`, breach threshold `1.00`.
- CRE dual stress: use policy `cre_dual_stress_formula`, normally `stressed_dscr = dscr * 0.85 / (1 + 0.18)`, breach threshold `1.00`.
- CRE weighted score: multiply available score components by policy weights; lower is better. Classify by policy cutoffs.
- CDFI factor score: add policy factor scores for available FICO, LTV, liquidity months, and debt-to-asset values. Map total score to the policy class; use `Projected Loss` instead of `Doubtful` when the score qualifies and LTV is over 1.0.

## Branch Rating Migration Reviews

Use branch details, metrics, loans, policies, and FDIC benchmarks.

1. Select the regrade population from the prompt, commonly loans for the target branch with `current_rating >= 3` or another stated threshold.
2. Recalculate each final rating using the policy dominant-factor rule.
3. Aggregate target count and exposure, then group exposure totals by `final_rating`.
4. For requested migration views, filter the target population by the named current rating, group by `final_rating`, and list loan IDs ascending.
5. Material downgrades include loans where the final rating worsens by at least the policy notch threshold.
6. For watch-list action coverage, include credits whose final grade or payment status requires follow-up. Use API-provided or policy-implied actions where available; otherwise apply conservative mappings:
   - nonaccrual or projected loss: `partial_chargeoff_review`
   - final rating 7 or 90+ days past due: `special_assets`
   - final rating 6, stressed DSCR breach, or elevated but not severe weakness: `watchlist`
   - milder follow-up: `monitor`
7. For NPA and FDIC variance, use the benchmark metric requested by the template or prompt. Compute `variance_ratio = branch_ratio - fdic_benchmark_ratio` and `variance_bps = variance_ratio * 10000`.
8. Top problem credit is the most severe credit by final rating, then adverse payment status, then exposure.

## Pending Application Allocation

Use branch details, branch metrics, sector exposures, applications, and policies.

1. Determine Q1 lending capacity from branch details or metrics. Capacity consumed is retained bank exposure, not necessarily gross approved amount.
2. Evaluate applications against policy floors and common decline reasons: capacity limit, sector breach, weak DSCR, high LTV, low FICO, recent bankruptcy, startup risk, underwater collateral, missing policy floor, documentation gap, FDIC/NCUA adverse variance.
3. Approve stronger credits while capacity remains and sector limits are not worsened. Use `conditional_approve` or `participation_required` when participation, SBA guaranty, reduced amount, board exception, or monitoring controls are needed.
4. `gross_approved_amount` is the sum of approved amounts. `committed_capacity_amount` is the sum of bank-retained exposure after participation or guarantees. `remaining_capacity = lending_capacity_q1 - committed_capacity_amount`.
5. `priority_ranking` includes only approved and conditionally approved applications, ordered by committee priority or strongest risk-adjusted use of capacity.
6. Post-approval concentration for each relevant sector is `(existing sector exposure + approved retained or gross amount as dictated by the API/prompt) / post-approval total loans`. Flag sectors at or near policy limit or where new approval needs mitigation.

## Competing CRE Decisions

Use the named applications, branch CRE/sector exposure, branch metrics, policies, and FDIC real-estate benchmarks.

1. Compute each application weighted CRE score from policy weights and classify it using policy cutoffs.
2. Compute CRE dual-stress DSCR for each application and mark threshold breaches.
3. Select the stronger credit by score, stressed coverage, collateral/LTV, and policy fit. If the branch is already over CRE or sector limits, choose `participation_required` or another mitigated path rather than unconditional approval.
4. Assign reason codes for each unselected or weak application from template enums. Include `sector_breach` for concentration violations, `weak_dscr` for stress breaches, `high_ltv` for collateral weakness, and `fdic_adverse_variance` when branch delinquency materially exceeds the FDIC benchmark metric.
5. Concentration variance to policy is `(post_approval_concentration - policy_limit_pct) * 10000`.
6. Conditions should directly mitigate the selected path: retained exposure cap, committee exception, appraisal update, tenant/lease review, DSCR covenant, quarterly reporting, and no additional CRE without review.

## Watch-List Stress Packets

Use branch loans and policies.

1. Select adversely rated loans using the threshold in the prompt, commonly `current_rating >= 6`.
2. Summarize count and exposure. Monitoring cadence is usually `monthly` for adverse populations with severe ratings, delinquencies, nonaccruals, or stress breaches.
3. Assign CDFI risk classes from factor scores using policy rules. Sort risk class rows by loan ID.
4. Stress only loans with DSCR available. Compute stressed DSCR, flag breaches below the policy threshold, and list breach loan IDs ascending.
5. Workout queue includes all adverse loans, sorted by descending exposure then ascending loan ID. Recommended action should reflect severity:
   - `partial_chargeoff_review` for projected loss or nonaccrual
   - `special_assets` for 90+ days past due, final/current rating 7+, or severe watch credits
   - `watchlist` for adverse but less severe credits
   - `monitor` only when template/prompt asks for lighter follow-up
6. Severe bucket counts group adverse loans by current rating and payment status, sorted by current rating then payment status as requested.

## Credit-Union Segment Posture

Use `/api/credit-union-segments/{segment_id}`, `/api/benchmarks/ncua/q1-2025`, policies, and the manifest.

1. Pull the segment record for peer states, required gates, capacity, recent delinquency, and any segment-specific operating guidance.
2. Use the state row from the NCUA benchmark table exactly as reported. Compare the state to `US` and to the median of named peer states for delinquency, loan-to-share, ROAA, and positive net income. Direction values are `higher`, `lower`, or `equal`.
3. Choose posture from template enums:
   - `continue_approving` when capacity is available and external metrics are not weaker.
   - `continue_with_tighter_conditions` when capacity exists but benchmark posture, segment delinquency, or controls call for restraint.
   - `temporarily_pause` when capacity is unavailable or risk triggers are severe.
4. Required checklist gates usually come from the segment record. Added operating controls should address the observed weakness: insurance/lien verification, second review, benchmark monitoring, delinquency watch, or committee exception for capacity overrun.
5. Escalation triggers should use controlled IDs and owners. Sort by trigger ID and include only triggers supported by the segment facts and template choices.
6. Interpretation fields must be controlled enum summaries of capacity, external risk, risk tolerance, and committee message.

## Final Validation

Before answering, verify:

- The JSON parses.
- Top-level keys exactly satisfy the template.
- All enum values are allowed by the template.
- Numeric precision and ratio/bps conversions match template instructions.
- Required sorting rules are followed.
- Totals reconcile to component rows within rounding tolerance.
