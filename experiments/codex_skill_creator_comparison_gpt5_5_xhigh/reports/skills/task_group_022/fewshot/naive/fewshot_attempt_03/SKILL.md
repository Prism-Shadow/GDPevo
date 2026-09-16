---
name: atlas-ops-solver
description: Solve Atlas Commerce Operations tasks that require querying the authenticated workplace API, computing exact operational metrics from the Atlas Commerce database, emitting schema-conformant JSON answers, or applying narrowly approved canonical data corrections with audit records. Use for Atlas fulfillment, refund reconciliation, carrier quality, warehouse productivity, support health, inventory, order, payment, and similar cutoff-based analytics tasks.
---

# Atlas Ops Solver

Use this skill for Atlas Commerce Operations database tasks. The common shape is: read a prompt plus request payloads, query the workplace API, compute metrics with SQL, and write exactly one `answer.json` object matching the supplied answer template.

## Required Workflow

1. Read the task prompt, every file under `input/payloads/`, and the answer template before querying.
2. Treat the request payload as the metric contract and the answer template as the output contract. If the prompt and payload differ, follow the payload for business rules and the template for field names/types.
3. Resolve the runtime base URL and token from the task prompt or environment. Do not hard-code training URLs, tokens, request IDs, entity IDs, dates, counts, or answer values.
4. Call `GET /api/schema` and `GET /api/data-dictionary` before writing SQL. Use the returned schema as authoritative.
5. For analytical requests, use only `POST /api/sql`. Do not mutate data.
6. For correction requests, mutate only when the prompt explicitly asks for a controlled correction and the request payload supplies an approved correction. Use pre-change queries, the controlled transaction endpoint, audit verification, and post-change queries before reporting `APPLIED`.
7. Never call `POST /api/judge`.
8. Write only valid JSON to `answer.json`. Include no commentary, no markdown, no extra keys, and no trailing text.

## API Helper

You may use the bundled standard-library helper instead of hand-written `curl`:

```bash
python scripts/atlas_api.py --base-url "$TASK_ENV_BASE_URL" --token "$ATLAS_API_TOKEN" schema
python scripts/atlas_api.py --base-url "$TASK_ENV_BASE_URL" --token "$ATLAS_API_TOKEN" dictionary
python scripts/atlas_api.py --base-url "$TASK_ENV_BASE_URL" --token "$ATLAS_API_TOKEN" sql --file query.sql
python scripts/atlas_api.py --base-url "$TASK_ENV_BASE_URL" --token "$ATLAS_API_TOKEN" audit
```

The helper also accepts bearer tokens with or without the `Bearer ` prefix. If the task environment provides different variable names, pass the values explicitly.

## SQL And Metric Patterns

Read [references/query-patterns.md](references/query-patterns.md) when constructing any nontrivial query. It contains the reusable Atlas conventions for:

- production-account filtering;
- effective source-row de-duplication;
- historical cutoff state;
- fulfillment, refund, carrier, warehouse, and support report metrics;
- controlled canonical corrections and audit reporting;
- final JSON ordering and rounding checks.

## Output Discipline

- Build the answer object from the template's required keys in the same order unless the task says otherwise.
- Use integers for counts, JSON numbers for rounded rates/amounts, strings for IDs and enums, and arrays sorted exactly as requested.
- Round only final displayed numbers. Use unrounded values for ranking, threshold comparisons, and status/risk classification.
- Validate that every required key exists and no additional key exists before finishing.
