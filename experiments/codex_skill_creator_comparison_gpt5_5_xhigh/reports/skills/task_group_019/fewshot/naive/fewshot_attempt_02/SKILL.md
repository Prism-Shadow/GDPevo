---
name: licensing-review-solver
description: Solve structured licensing review tasks that use a read-only task environment and require strict JSON answers, including contractor eligibility batches, restricted liquor-license staff packages, and alcohol renewal manual-review queues. Use when the prompt references licensing endpoints, policies, contractor applications/bonds/insurance/history/violations, liquor applications/settlements/privileges/incidents/site evidence, alcohol renewal licensees/violations/rules, or an answer_template.json schema.
---

# Licensing Review Solver

## Core Workflow

1. Read the prompt, `input/payloads/answer_template.json`, and the task's `environment_access.md`.
2. Use only endpoints and SQL access allowed by `environment_access.md`. Never call `/api/judge`.
3. Fetch policies first, then fetch every business endpoint named in the prompt. Prefer SQL for targeted joins or filtering when a token is provided.
4. Parse JSON-in-string fields such as policy `details_json` and settlement `controls_json`.
5. Build the answer from source records and the template. Use exactly the required keys, allowed enum values, casing, ordering rules, and empty arrays where nothing applies.
6. Before finalizing, validate that summary counts and ID lists are consistent with item-level records. Return only the JSON object.

Useful helpers:

```bash
python skill/scripts/fetch_licensing_data.py --base-url "$TASK_ENV_BASE_URL" --out /tmp/licensing-data \
  --endpoint /api/policies --endpoint /api/contractor/applications

python skill/scripts/check_answer_template.py input/payloads/answer_template.json answer.json
```

For domain rules and field mappings, read [references/licensing-patterns.md](references/licensing-patterns.md).

## Evidence Handling

- Treat the answer template as authoritative. If a record suggests a problem but no matching allowed code exists, do not invent a new code.
- Use target IDs, locations, date boundaries, queue size, and review dates from the prompt. If no contractor review date is explicit, infer it from the batch's source/record dates rather than the conversation date.
- For dates, compare as `YYYY-MM-DD` strings only after normalizing to that format.
- For list fields, remove duplicates and apply the template's ordering. If the template says no ordering is required, still use a stable, defensible order.
- Prefer direct identifiers over fuzzy matches. Mark lower confidence when using successor, same-address, or name-based matches.

## SQL Pattern

Use parameterized SQL for target filtering:

```json
{
  "query": "select * from contractor_applications where application_id in (?, ?) order by application_id",
  "params": ["TARGET-001", "TARGET-002"],
  "limit": 100
}
```

Send `X-Task-Token` only when `environment_access.md` provides one. Use SQL for reads only.

## Final Checks

- The JSON must parse.
- Top-level keys must match the template exactly.
- Application decisions must be sorted as requested.
- Queue ranks must be contiguous, with no gaps.
- Summary counts, high-risk IDs, board-review IDs, excluded post-boundary IDs, and stale/unverified correspondence IDs must be derived from the item-level evidence.
