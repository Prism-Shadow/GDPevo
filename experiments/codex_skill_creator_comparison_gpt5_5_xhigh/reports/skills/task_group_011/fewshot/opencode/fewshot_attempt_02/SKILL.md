---
name: skill
description: Solve public credit-office committee tasks that require querying <TASK_ENV_BASE_URL>, the branch or segment API, FDIC or NCUA benchmarks, and the provided answer_template.json to produce an exact JSON answer. Use this whenever the prompt mentions branch_id, segment_id, loan regrades, pending applications, DSCR stress, concentration limits, CRE comparisons, watch lists, or a committee-ready JSON output.
---

# Credit Office JSON Workflow

Use this skill for the staged credit-office prompts. The target output is always a single JSON object that matches the supplied `input/payloads/answer_template.json` exactly. Do not write prose outside the JSON.

## Start here

1. Read the prompt and the matching `input/payloads/answer_template.json`.
2. Read `/api/manifest` and `/api/policies` from the public task environment.
3. Use the prompt type and the template keys to decide which branch, segment, loans, applications, and benchmark tables you need.
4. Fetch only the API data needed for that template. The public API is the source of truth; do not guess from memory.

## API order

Prefer this sequence when you need a full picture:

1. `GET /api/manifest`
2. `GET /api/policies`
3. `GET /api/branches/{branch_id}` or `GET /api/credit-union-segments/{segment_id}`
4. `GET /api/branches/{branch_id}/metrics`
5. `GET /api/branches/{branch_id}/loans`
6. `GET /api/branches/{branch_id}/sector-exposures`
7. `GET /api/branches/{branch_id}/applications`
8. `GET /api/benchmarks/fdic/q4-2024` or `GET /api/benchmarks/ncua/q1-2025`

Use the base URL from the runner or `environment_access.md`. Do not use any other network source.

## Shared rules

- Follow the template field order, sorting rules, and enum restrictions literally.
- Round currency to 2 decimals and ratios to 4 decimals only at the end.
- Keep IDs and dates exactly as provided.
- Use the latest quarter or benchmark row that matches the prompt date.
- Never invent values when the API already exposes the needed field.

## Policy math to reuse

- Risk rating candidates come from DSCR, LTV, and delinquency minimums.
  - DSCR: `>= 1.5 -> 3`, `>= 1.25 -> 4`, `>= 1.05 -> 5`, `>= 1.0 -> 6`, `< 1.0 -> 7`
  - LTV: `<= 0.65 -> 3`, `<= 0.75 -> 4`, `<= 0.85 -> 5`, `<= 1.0 -> 6`, `> 1.0 -> 7`
  - Delinquency: `Current -> none`, `30 Days Past Due -> 4`, `60 Days Past Due -> 5`, `90+ Days Past Due -> 7`, `Nonaccrual -> 8`
  - Final rating = worst supported numeric candidate.
- Material downgrade threshold = 2 notches.
- CRE stress formula = `stressed_dscr = dscr * 0.85 / 1.18`.
- Watch-list stress formula = `stressed_dscr = dscr / 1.18`.
- NPA or CRE benchmark variance = branch ratio minus benchmark ratio; bps = ratio delta * 10000.
- For CRE concentration, treat the current CRE book as the sum of existing loans with `loan_type == "CRE"` and divide by `total_loans_outstanding`.
- For sector concentration, use the sector-specific `limit_pct` from `sector-exposures` when present; otherwise use the branch ceiling. Grandfathered excess may stay in place, but new approvals should not worsen it without mitigation.
- For NCUA posture, compare the North Carolina row to the US row and the median of the listed peer states, not to an average.

## Task playbooks

### 1. Branch regrade review

Use this when the prompt asks to re-rate loans, summarize migration, or report NPA variance.

- Filter the loan book to the requested current-rating floor.
- Re-derive each loan's final rating from the policy thresholds above.
- Group exposure by final rating.
- For the migration section, include only loans that started at the referenced current rating.
- Treat loans with downgrade notches of 2 or more as material downgrades.
- For watch-list action coverage, map the most severe follow-up action supported by the facts:
  - `watchlist` for moderate deterioration
  - `special_assets` for severe delinquency or regrade stress
  - `partial_chargeoff_review` for nonaccrual or projected loss
  - `legal_referral` only when the facts clearly warrant it
- Pick the top problem credit by worst final rating, then payment status severity, then exposure.

### 2. Allocation package for pending applications

Use this when the prompt asks for decisions, priority ranking, concentration flags, and decline reasons.

- Score each application using the branch policy and the application facts.
- Use the CRE weighted score classes from the policy:
  - `approve_quality` if score `<= 2.0`
  - `conditional` if score `<= 3.0`
  - `weak` otherwise
- Approve clean credits, conditionally approve credits that need a permitted mitigation, and decline credits that remain weak after mitigation.
- Use only the controlled decision and condition enums from the template.
- Build `priority_ranking` from approved and conditionally approved applications only. Put the most committee-relevant and highest-priority credits first.
- Compute `gross_approved_amount` from approved amounts and `committed_capacity_amount` from the bank capital actually retained.
- Set `remaining_capacity = lending_capacity_q1 - committed_capacity_amount`.
- Flag concentrations when the post-approval ratio reaches or meaningfully threatens the sector ceiling.
- Sort decline reasons alphabetically and use only the allowed reason-code enum.

### 3. Credit-union segment posture

Use this when the prompt asks for a posture page, state metrics, peer comparison, controls, and escalation triggers.

- Pull the segment record, the NCUA benchmark table, and the relevant state row.
- Build `state_metrics` from the state row for the requested state.
- Build `peer_comparison.peer_states` by sorting the listed peer states alphabetically.
- Set `posture` from the combined picture:
  - `continue_approving` when metrics and controls are clearly strong
  - `continue_with_tighter_conditions` when capacity is usable but risk is mixed
  - `temporarily_pause` only when the risk picture is materially adverse
- For controls, include the gates already required by the segment and add the operating controls that directly address the segment's notes and internal context.
- Escalation triggers are the conditions the committee will monitor, not just the ones currently breached.

### 4. Watch-list stress packet

Use this when the prompt asks for adverse-rated loans, factor-based classes, +200bp stress, and workout actions.

- Select loans at or beyond the adverse-rating floor.
- Compute a factor score from the policy tables and the loan facts.
- Map the score to `Prime`, `Desirable`, `Satisfactory`, `Watch`, or `Doubtful`.
- Promote nonaccrual or clearly underwater credits to `Projected Loss` when the facts warrant it.
- Apply the +200bp watch-list stress formula only where DSCR is available.
- Order the workout queue by descending exposure, then ascending loan_id.
- Summarize severe bucket counts by current rating and payment status.

### 5. Competing CRE decision

Use this when the prompt asks you to compare two applications and recommend one path.

- Compute a weighted CDFI-style score for each application using the branch policy and the application facts.
- Score lower-is-better.
- Run the CRE stress formula for both applications and note any DSCR breach.
- Compare the existing CRE concentration, the selected post-approval concentration, the policy limit, and the FDIC benchmark variance.
- Select the stronger credit, then give the losing credit a clean decline or defer disposition with the relevant reason codes.
- Put the selected application first only if the template asks for ranking; otherwise follow the template order exactly.

## Field-by-field reminders

- Regrade template:
  - `final_rating_exposure_totals` sorted ascending by `final_rating`
  - `migration_from_current_rating_3` sorted ascending by `final_rating`
  - `watch_list_action_coverage.by_action` sorted ascending by `action`
- Allocation template:
  - `decisions` sorted by `application_id`
  - `concentration_flags` sorted by sector, then `application_id`
  - `post_approval_concentrations` sorted by sector
- Segment template:
  - `peer_states` sorted ascending
  - `escalation_triggers` sorted ascending by `trigger_id`
- Watch-list template:
  - `risk_classes` sorted by `loan_id`
  - `stress_results` sorted by `loan_id`
  - `workout_queue` sorted by descending exposure, then ascending `loan_id`
  - `severe_bucket_counts` sorted by `current_rating`, then `payment_status`
- CRE comparison template:
  - `applications_compared` sorted by `application_id`
  - `stress.results` sorted by `application_id`
  - `conditions` sorted alphabetically

## Final check

Before you answer, verify:

- Every required top-level key is present.
- Every enum is one of the template's allowed values.
- Every list is in the template's order.
- Every number is rounded correctly.
- The final response is valid JSON and nothing else.
