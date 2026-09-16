---
name: credit-office-packet-solver
description: Solve staged public credit-office API committee packets into schema-matched JSON for branch rating regrades, lending allocations, segment posture reviews, watch-list stress packets, and competing CRE decisions. Use when prompts reference TASK_ENV_BASE_URL, branch/segment IDs, loan or application reviews, public policy or benchmark endpoints, or `input/payloads/answer_template.json`.
---

# Credit Office Packet Solver

## Overview
Use this skill for staged public credit-office API tasks that require a committee-ready JSON answer from branch, segment, loan, application, policy, and benchmark data.

See [references/public-credit-office-playbook.md](references/public-credit-office-playbook.md) for the shared policy constants, endpoint map, and task-family notes.

## Workflow
1. Read the prompt and the matching `input/payloads/answer_template.json`.
2. Read `environment_access.md` if needed to resolve the runner-supplied base URL, then call only the public endpoints listed in `/api/manifest`.
3. Read `/api/policies` before any scoring, stress, or concentration calculation.
4. Fetch only the branch, segment, application, loan, and benchmark records needed for the prompt.
5. Assemble the JSON exactly to schema and return JSON only.

## Task Families
### Branch regrade
- Regrade the requested loan population from the prompt's current-rating floor.
- Use the policy DSCR, LTV, and delinquency thresholds. Take the worst numeric outcome across available factors.
- Treat 2+ notch moves as material downgrades.
- Build watch-list action coverage only for loans that need follow-up after the regrade.

### Lending allocation
- Score applications with the policy CRE weights; lower scores are better.
- Compare requested exposure, current sector exposure, sector ceilings, and policy mitigations.
- Put approved and conditionally approved applications into `priority_ranking` by committee priority, not by `application_id`.
- Sort decline reasons alphabetically and keep concentration flags tied to the post-approval sector check.

### Segment posture
- Compare the state to the US row and the named peer states on every metric in the template.
- Keep checklist gates and added controls aligned to the branch context and the control issues in the segment payload.
- Use tighter conditions rather than a pause when capacity remains available and the benchmark gap is adverse but not extreme.

### Watch-list stress
- Treat `current_rating >= 6` as the adverse population.
- Map factor scores with the policy CDFI table, then compute +200bp stressed DSCR with the watch-list formula.
- Queue workout actions from most exposed to least exposed.
- Count severe buckets by rating and payment status in schema order.

### CRE comparison
- Compute weighted CRE score with the policy weights and pick the lower score as stronger.
- Use the dual-stress formula for coverage and concentration checks.
- Prefer `participation_required` or `conditional_approve` when the credit is good but concentration or coverage needs mitigation.
- Keep unselected reason codes limited to the template's controlled set.

## Output Rules
- Emit valid JSON only.
- Preserve schema order and list ordering from the template.
- Round currency to 2 decimals, ratios to 4 decimals, and integer benchmark values exactly.
- Do not invent enums, extra keys, or prose.
