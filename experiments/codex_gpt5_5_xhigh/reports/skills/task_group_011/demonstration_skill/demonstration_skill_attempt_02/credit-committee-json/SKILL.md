---
name: credit-committee-json
description: Produce strict JSON answers for credit-office committee tasks using only public API data and the provided answer_template.json. Use for branch loan regrades, watch-list stress packets, pending-application allocations, competing CRE decisions, and credit-union segment posture recommendations that require policies, branch or segment metrics, FDIC/NCUA benchmarks, controlled enums, sorted lists, and reconciled numeric totals.
---

# Credit Committee JSON

## Access Rules

- Use the public HTTP API base URL supplied by the task or environment. If a setup script is mentioned but an API base URL is already provided, use the provided URL directly.
- Do not read local environment source/data files, test tasks, reports, generated skills, notes, or task metadata. For benchmark tasks, read only the prompt and its `input/payloads/answer_template.json` unless the user explicitly grants more.
- Prefer public API endpoints over local files for branch details, branch metrics, sector exposure, loans, pending applications, policies, benchmarks, manifests, and credit-union segment data.
- Return only the JSON object requested by the template. Do not add markdown, comments, or explanatory text outside the JSON.

## Core Workflow

1. Read the prompt and `answer_template.json` first.
2. Extract the target identifier, as-of/review date, population rule, named applications, required benchmark version, and every enum/order/precision rule from the template.
3. Discover and fetch public API data for the requested surfaces:
   - Branch tasks: branch details, branch metrics, loans, sector exposures, pending applications, credit policies, FDIC benchmarks.
   - Credit-union segment tasks: manifest if available, policies, segment record, NCUA benchmarks, peer-state data.
4. Normalize source data into tables keyed by `loan_id`, `application_id`, `sector`, `branch_id`, or `segment_id`.
5. Apply policy thresholds from the API before using fallback heuristics. Treat controlled policy codes, rating classes, reason codes, actions, and checklist gates as authoritative.
6. Compute all intermediate totals with full precision. Round only when assigning output fields.
7. Reconcile every aggregate against the row-level records:
   - Counts equal the number of included records.
   - Exposure totals equal the sum of included balances or approved amounts.
   - Capacity remaining equals available capacity minus retained bank commitment.
   - Variance ratios equal branch/state metric minus benchmark metric; basis points equal variance ratio times 10000.
8. Sort arrays exactly as the template says. For maps of reason codes, sort each code list alphabetically unless the template says otherwise.
9. Validate that every required key is present, no enum value falls outside the template, and numeric precision matches the template.

## Common Calculations

- Currency fields: output numbers rounded to 2 decimals.
- Ratio fields: output as decimal ratios, not percentages, rounded to the precision requested, usually 4 decimals.
- Basis points: `(observed_ratio - benchmark_ratio) * 10000`, rounded to 2 decimals unless the template says otherwise.
- Downgrade notches: `final_rating - current_rating`; higher ratings are worse.
- Material downgrade: include loans with downgrade notches of at least 2 unless the prompt or policy gives a different threshold.
- DSCR breach: compare stressed DSCR to the template or policy breach threshold, commonly `1.00`.
- If a template says "integer values exactly as reported", do not recompute or round those benchmark values.

## Rating Regrade Tasks

Use this pattern for branch rating migration reviews.

1. Select the target branch loans whose `current_rating` is at or above the requested minimum rating.
2. Re-derive `final_rating` using the public rating policy and objective loan factors such as payment status, DSCR, LTV, FICO, collateral position, bankruptcy, nonaccrual status, documentation gaps, and any policy overrides.
3. Build final-rating exposure totals grouped by `final_rating`, ordered ascending by rating.
4. Build migration slices only for the specific current-rating bucket requested by the template, grouped by `final_rating` with sorted `loan_ids`.
5. Build watch-list action coverage from loans that require follow-up after regrade. Group by recommended action and include only actionable follow-up categories requested by the template, such as `watchlist`, `special_assets`, `workout`, `partial_chargeoff_review`, or `legal_referral`.
6. Identify material downgrades with `final_rating - current_rating >= 2`, sorted by `loan_id`.
7. Select the top problem credit by the most severe final rating, then by nonaccrual or delinquent payment status, then exposure if needed.
8. For NPA benchmark fields, use the branch NPA exposure/ratio definition exposed by the API or policy. Pair it with the requested FDIC benchmark metric and version.

## Pending Application Allocation Tasks

Use this pattern for lending-committee allocation packages.

1. Fetch pending applications, branch lending capacity, existing sector exposures, branch metrics, and approval policy.
2. Evaluate each application against policy floors and hard stops: DSCR, LTV, FICO, bankruptcy, collateral, documentation, startup risk, sector concentration, capacity, and external benchmark weaknesses.
3. Assign a decision from the template enum. Use `conditional_approve` or `participation_required` when the credit is acceptable but needs retained-exposure reduction, SBA guaranty, monitoring, board exception, or other listed conditions.
4. Set `approved_amount` to the gross approved credit amount. Set `bank_capacity_used` to the retained bank exposure after participation, guaranty, or amount reduction.
5. Compute:
   - `gross_approved_amount` as the sum of approved gross amounts.
   - `committed_capacity_amount` as the sum of retained bank capacity used.
   - `remaining_capacity` as lending capacity minus committed capacity.
6. Build `priority_ranking` from approved and conditionally approved applications only, ordered by the policy priority score or committee priority rule.
7. Create decline reason code lists only for declined applications; use allowed codes and sort them.
8. Recompute post-approval concentration by sector after approved retained exposure or gross exposure according to the API policy definition. Flag applications that breach or press against concentration limits, and set handling to the actual decision path.

## Credit-Union Segment Posture Tasks

Use this pattern for segment posture pages.

1. Fetch the target segment record, public policy, NCUA benchmark version requested by the prompt, national metrics, state metrics, and named peer states.
2. Copy state benchmark metrics exactly when the template asks for reported integers.
3. Sort peer state codes ascending.
4. For each direction field, compare the target state value with the national value and with the peer-state median:
   - `higher` if the state value is greater.
   - `lower` if it is less.
   - `equal` if it matches.
5. Choose posture from policy and evidence:
   - Use `continue_approving` when capacity is available and external metrics support routine risk.
   - Use `continue_with_tighter_conditions` when capacity exists but state or peer metrics are weaker, or segment controls need tightening.
   - Use `temporarily_pause` when capacity is exhausted or external/segment risk violates pause triggers.
6. Include required checklist gates from the product/segment policy and add operating controls that directly address the observed weakness.
7. Add escalation triggers from policy, sorted by `trigger_id`, with owner enums from the template.
8. Keep the interpretation concise and controlled: capacity status, external risk status, risk tolerance, and one allowed committee message.

## Watch-List Stress Tasks

Use this pattern for adversely rated branch-loan stress packets.

1. Select target branch loans with `current_rating` at or above the adverse minimum in the prompt.
2. Assign CDFI-style risk classes and factor scores from the public policy or endpoint. Do not invent class names outside the template.
3. Compute the requested DSCR stress only for loans with DSCR available. For a `+200bp` watch-list stress, use the public policy formula or stress factor exposed by the API.
4. Mark breaches when stressed DSCR is below the breach threshold.
5. Build `breach_loan_ids` sorted ascending.
6. Queue workout actions from policy. Typical severity mapping is:
   - Projected loss or nonaccrual: `partial_chargeoff_review`.
   - Severe delinquency or doubtful credit: `special_assets` or `workout` as policy indicates.
   - Adverse current loans needing close follow-up: `watchlist`.
   - Legal/default path: `legal_referral` only when supported by policy facts.
7. Sort workout queue by descending exposure, then ascending `loan_id`.
8. Group severe bucket counts by current rating and payment status using the template sort rule.

## Competing CRE Decision Tasks

Use this pattern for comparing named CRE applications.

1. Fetch both application records, branch metrics, CRE/sector exposure, loan portfolio, credit policy, and FDIC benchmark data.
2. Score each application with the weighted CRE/CDFI scoring policy. Lower scores are better when the template states that convention.
3. Classify scores with the policy thresholds, then assign decisions and reason codes.
4. Apply the CRE dual-stress formula from policy. If the policy names a compact formula, use that string in the output, and compute stressed DSCR from base DSCR.
5. Select the stronger application by score, stress result, collateral/DSCR quality, and concentration impact. If concentration or benchmark underperformance prevents full approval, use the controlled conditional or participation path.
6. Give the unselected application a `decline` or `defer` disposition with only allowed reason codes.
7. Compute CRE concentration:
   - Existing concentration from existing CRE exposure over the policy denominator.
   - Post-approval concentration after the selected application or retained bank exposure, following policy.
   - Policy variance in bps as `(post_approval_concentration - policy_limit) * 10000`.
8. Add closing/monitoring conditions that directly mitigate the selected path, then sort conditions alphabetically.

## Output QA Checklist

- The top-level keys exactly match the required template shape.
- Every required nested key is present, even when a list is empty.
- Enum strings are copied exactly from the template.
- IDs are sorted according to the template and are stable strings from the API.
- Exposure and count subtotals tie to their detail rows.
- Ratios and basis points are recomputed independently before finalizing.
- The answer is valid JSON and contains no trailing comments or markdown.
