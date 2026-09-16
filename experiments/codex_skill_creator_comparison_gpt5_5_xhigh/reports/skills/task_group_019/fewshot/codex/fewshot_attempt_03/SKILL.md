---
name: licensing-review-json
description: Produce strict JSON answers for licensing-environment review tasks involving contractor eligibility batches, restricted liquor-license staff packages, and alcohol renewal manual-review queues. Use when a task references licensing APIs, /api/policies, contractor/liquor/alcohol endpoints, answer_template.json, eligibility determinations, restricted issuance controls, or renewal queue ranking.
---

# Licensing Review JSON

## Core Workflow

1. Read the task prompt and every file in `input/payloads/`, especially `answer_template.json`.
2. Resolve `<TASK_ENV_BASE_URL>` from the prompt or environment access notes. Use only the endpoints named in the prompt unless the same family requires `/api/policies` or `/api/renewal/rules`.
3. Fetch enough rows to include the target records. Public GET endpoints may cap default responses; append a larger `limit` query parameter when needed.
4. Parse embedded JSON fields such as `details_json` and `controls_json` before applying rules.
5. Choose the matching workflow in [references/review-workflows.md](references/review-workflows.md):
   - contractor application eligibility batches
   - restricted liquor-license staff packages
   - alcohol renewal manual-review queues
6. Build the JSON from facts in the API records and the local template. Use only keys, enum spellings, and ordering rules allowed by the template.
7. Return only the final JSON object. Do not add markdown, citations, comments, or explanatory prose.

## Fetch Helper

Use [scripts/fetch_endpoint.py](scripts/fetch_endpoint.py) when repeated endpoint fetching or pagination-safe capture would reduce error:

```bash
python skill/scripts/fetch_endpoint.py "$TASK_ENV_BASE_URL" \
  /api/policies \
  /api/contractor/applications \
  /api/contractor/bonds \
  --limit 1000 \
  --output-dir /tmp/licensing-data
```

The helper uses only Python standard-library modules. It performs GET requests, appends `limit` when absent, and writes one JSON file per endpoint when `--output-dir` is supplied.

## Output Discipline

- Treat the local answer template as the contract. If template wording conflicts with general guidance, follow the template.
- Use empty arrays for absent codes or IDs.
- Sort arrays exactly as the template requests. When no ordering is specified, prefer stable lexical order except where an operational sequence is requested.
- Recompute summary counts and summary ID lists from the item-level result after all item decisions are finalized.
- Do not memorize or reproduce training application IDs, license numbers, violation IDs, answer records, or other task-specific final values.
