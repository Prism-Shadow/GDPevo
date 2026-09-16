---
name: credit-office-api-json
description: Solve public credit-office API tasks that require a JSON-only committee packet for branch regrades, lending allocations, credit-union segment posture, watch-list stress packets, or competing CRE decisions. Use this skill whenever the prompt mentions <TASK_ENV_BASE_URL>, answer_template.json, branch metrics, loans, applications, sector exposures, credit-union segments, or FDIC/NCUA benchmark comparisons.
---

# Credit Office API JSON

Use this skill for the staged public credit-office committee tasks. The deliverable is always one valid JSON object that matches the supplied template exactly.

## Workflow
1. Read the prompt, then read the provided payload template before doing anything else.
2. Identify the task family from the prompt:
   - branch regrade or rating migration
   - allocation or application decision packet
   - credit-union segment posture
   - watch-list stress and workout queue
   - competing CRE decision
3. Pull data from the public API at `$TASK_ENV_BASE_URL`.
4. Use `/api/manifest` first to confirm the available benchmark versions and policy version.
5. Use `/api/policies` for scoring rules, thresholds, stress formulas, allowed mitigation enums, and concentration policy.
6. Build the JSON in the template's shape and return JSON only.

## Task Family Map
- Branch regrade or rating migration: use `/api/branches/{branch_id}`, `/metrics`, `/loans`, `/sector-exposures`, and `/benchmarks/fdic/q4-2024`.
- Allocation or application decisions: use `/api/branches/{branch_id}`, `/applications`, `/sector-exposures`, and `/policies`.
- Credit-union segment posture: use `/api/credit-union-segments/{segment_id}`, `/benchmarks/ncua/q1-2025`, and `/policies`.
- Watch-list stress or workout queue: use `/api/branches/{branch_id}/loans`, `/metrics`, and `/policies`.
- Competing CRE decision: use `/api/branches/{branch_id}/applications`, `/sector-exposures`, `/benchmarks/fdic/q4-2024`, and `/policies`.

## How To Work
Read the template as the contract. The prompt tells you which fields matter; the template tells you the exact keys, enum values, ordering, and precision.

For every response:
- Echo the prompt's branch_id, segment_id, or review_date exactly.
- Use enum values verbatim from the template.
- Respect every ordering rule. If the template does not specify an order, use a stable deterministic order, usually ascending IDs.
- Round currency to 2 decimals and ratio or percentage fields to 4 decimals when the template asks for ratios.
- Keep counts as integers.
- Do not add narrative text, markdown, or code fences outside the JSON object.

For common derived fields:
- Re-derived ratings: apply the policy thresholds from `references/public_credit_office.md` and take the worst applicable numeric rating across DSCR, LTV or collateral, and delinquency.
- Concentration checks: compare the branch or selected deal against the policy limit, the sector ceiling, and any grandfathering or mitigation rule in `/api/policies`.
- Stress results: use the exact formula named by `/api/policies`; the watch-list +200bp stress and the CRE dual-stress formula are not the same.
- Benchmark comparisons: compare against the exact FDIC or NCUA table named in the manifest, not a stale external source.

## Final Check
Before answering, verify that:
- every required key is present,
- every list is in the required order,
- every enum value comes from the template,
- every numeric field has the expected precision,
- the response parses as strict JSON.

See `references/public_credit_office.md` for the shared API map and policy summary.
