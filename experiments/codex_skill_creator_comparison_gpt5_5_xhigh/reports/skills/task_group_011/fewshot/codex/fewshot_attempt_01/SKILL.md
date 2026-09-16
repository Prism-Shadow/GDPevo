---
name: credit-office-solver
description: Solve staged credit-office public API tasks that require strict JSON answers for branch portfolio regrades, lending allocations, credit-union segment posture pages, watch-list stress packets, or competing CRE decisions. Use when the prompt references the runner-supplied TASK_ENV_BASE_URL, public API endpoints, or a required answer_template.json.
---

# Credit Office Solver

## Overview

Use this skill when the prompt asks for a committee-ready JSON answer from the staged credit-office API. The answer template is the source of truth for keys, ordering, and enums; the prompt and policy files determine which data to fetch and which calculations to apply.

## Workflow

1. Identify the family from the required top-level keys in `answer_template.json`.
2. Read `/api/manifest` and `/api/policies` first.
3. Fetch only the endpoints needed for that family.
4. Compute with full precision, then round only at serialization.
5. Return raw JSON only.

## Family Map

- `branch_id` + `portfolio_regrade`: branch rating migration review.
- `branch_id` + `allocation`: lending allocation package.
- `segment_id` + `posture`: credit-union segment posture page.
- `branch_id` + `watch_list_summary`: adverse watch-list stress review.
- `branch_id` + `applications_compared`: competing CRE decision.

## Shared Rules

- Use only IDs, metrics, enums, and field names from the prompt, API, and template.
- Treat the template as authoritative for keys, ordering, and allowed values.
- Keep calculations in full precision until the end.
- Serialize currency to 2 decimals, ratios to 4 decimals, bps to 2 decimals, and benchmark integers exactly.
- Do not add narrative text, markdown fences, or extra keys.
- Sort any list exactly as the template requires.

## Branch Portfolio Regrade

- Fetch branch details, loans, sector exposures, metrics, and the FDIC benchmark.
- Recompute each in-scope loan's final rating from the policy's DSCR, LTV, and delinquency floors. Use the worst numeric rating from all available factors.
- Use the prompt's current-rating floor to define the population.
- Set `downgrade_notches` to `final_rating - current_rating`.
- Treat downgrades at or above the policy material threshold as material.
- Roll up `watch_list_action_coverage` only for active follow-up actions such as `watchlist`, `special_assets`, `workout`, `partial_chargeoff_review`, or `legal_referral`.
- Choose the benchmark metric that matches the prompt's stated focus; otherwise use the broad loan noncurrent metric.
- Compute variance as `branch_npa_ratio - fdic_benchmark_ratio`, then convert to bps.

## Lending Allocation Package

- Fetch branch details, metrics, sector exposures, applications, and policies.
- Rank only approved and conditionally approved applications in `priority_ranking`.
- Use `approved_amount` as the gross commitment and `bank_capacity_used` as the retained capacity after any participation or guaranty mitigation.
- Compute `gross_approved_amount`, `committed_capacity_amount`, and `remaining_capacity` from the selected decisions.
- Compare post-approval sector exposure against post-approval total loans outstanding, not against the current base alone.
- Flag a sector when the post-approval percentage reaches or practically collides with the sector limit or when mitigation is required to stay within policy.
- Use only the template's decline reason codes, sorted alphabetically.

## Segment Posture Page

- Fetch the segment endpoint, the NC row from the NCUA benchmark table, and the policy.
- Compare North Carolina to both US and the peer median on all four benchmark measures.
- Use `higher`, `lower`, or `equal` exactly as the template expects.
- Pick `continue_approving` only when capacity and the benchmark picture are comfortable; use `continue_with_tighter_conditions` when capacity exists but external risk is weaker; use `temporarily_pause` only for severe deterioration or binding capacity pressure.
- Serialize the required gates and operating controls as arrays of template enums.
- Order escalation triggers by trigger ID and assign explicit owners.

## Watch-List Stress Review

- Filter the adverse population by the prompt's current-rating floor.
- Build `risk_classes` from the policy's objective-factor rubric and the loan record's objective fields.
- Treat clearly impaired nonaccrual or underwater credits as `Projected Loss` even if the raw score sits near the `Watch` band.
- Use the policy watch-list stress formula for DSCR (`dscr / 1.18`) and mark a breach when stressed DSCR falls below 1.0.
- Include only loans with DSCR available in the stress results.
- Sort the workout queue by exposure descending, then `loan_id` ascending.
- Group severe bucket counts by `current_rating` and `payment_status`.

## Competing CRE Decision

- Score both applications with the policy weights across capacity, capital, character, collateral exposure, and conditions.
- Lower weighted score is better; map the score to the class bands in policy.
- Use the policy CRE stress formula for DSCR and compare branch delinquency to FDIC `total_real_estate_30_89_pct`.
- Compute post-approval CRE concentration from existing CRE exposure plus the selected gross approval over current total loans plus that approval.
- Select the stronger credit, assign the weaker credit a disposition, and keep reason codes and conditions within the template enums.
- Use the branch's policy limit when deciding whether a participation, conditional approval, or defer path is needed.

## Final Check

- Match the template shape exactly.
- Never copy example values into the reusable skill.
- Return only the JSON object the prompt requests.
