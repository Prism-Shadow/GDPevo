---
name: atlas-ops-json-solver
description: Solve Atlas Commerce Operations workplace tasks that require using TASK_ENV_BASE_URL, /api/schema, /api/data-dictionary, /api/sql, or documented controlled correction endpoints to produce an exact answer.json matching input/payloads/answer_template.json. Use for operational analytics, settlement reconciliation, fulfillment scorecards, warehouse productivity reviews, support-health reviews, and narrowly authorized data-quality corrections against the Atlas task service.
---

# Atlas Ops JSON Solver

Use this skill when a task asks for an exact JSON answer from the Atlas Commerce Operations workplace service. The common pattern is: read the local prompt, request payload, and answer template; discover the live schema; compute the requested business metrics with SQL; validate the JSON contract; write only `answer.json`.

## Workflow

1. Read the task prompt, every file under `input/payloads/`, and especially `input/payloads/answer_template.json`. Treat the template as the output contract: required keys, no extra keys, exact nesting, ordering requirements, rounding, enum values, and array uniqueness.
2. Resolve the task environment base URL from the prompt, environment variables, or any provided environment-access file. Use that file only for connection details such as base URL and auth. Do not inspect server source, evaluator code, test answers, or unrelated task material.
3. Fetch the live schema and data dictionary before writing SQL. Use the bundled client at [scripts/atlas_api.py](scripts/atlas_api.py). From the task workspace, run it with the path to this skill directory:
   - `python <skill_dir>/scripts/atlas_api.py schema`
   - `python <skill_dir>/scripts/atlas_api.py dictionary`
   - `python <skill_dir>/scripts/atlas_api.py sql path/to/query.sql`
4. Translate the request payload into a cohort query before calculating metrics. Keep the cohort in a CTE with one row per business entity in the denominator, such as order, shipment, task, case, refund, or account. Apply production flags, account/warehouse/region/campaign filters, inclusive or strict timestamp boundaries, and cutoff semantics exactly as stated.
5. Build metric CTEs from the cohort. Prefer explicit `COUNT(DISTINCT ...)`, `EXISTS`/`NOT EXISTS`, window functions, and grouped rollups over manual sampling. Avoid row multiplication when joining one-to-many tables such as shipments, scans, refunds, reversals, events, tasks, or cases.
6. Run focused cross-check queries for denominators, numerators, exception lists, ranked outputs, and risk-status thresholds. Preserve unrounded values for ranking and threshold decisions; round only final reported numbers.
7. Assemble `answer.json` from query results. Sort arrays exactly as the template or request says. For tied rankings, apply every stated tie-breaker in order. Use stable IDs from the database, not labels or inferred names.
8. Validate before finalizing with [scripts/validate_answer.py](scripts/validate_answer.py):
   - `python <skill_dir>/scripts/validate_answer.py input/payloads/answer_template.json answer.json`
   - Recheck counts against the final arrays and risk classification rules.

## SQL Guidance

- Discover names from `/api/schema` and definitions from `/api/data-dictionary`; do not assume table or column names from memory.
- Use UTC timestamps literally. If the request says inclusive boundaries, use `>= start` and `<= end`; if it says strictly before a cutoff, use `< cutoff`.
- For "as of cutoff" state, select the latest effective event, scan, status, or timestamp at or before the cutoff. Do not use future records.
- For "all associated rows satisfy X", implement the negative test: include the parent only when no associated row violates X, and handle "no associated rows" according to the request definition.
- For active-time SLA tasks, unresolved or unresponded records use elapsed active time at the cutoff. Resolved records use active time through resolution. Apply priority-specific thresholds from the payload.
- For money tasks, convert every monetary row using the requested service-date FX rate and currency. Net logical activity by subtracting linked reversals only when the request policy says they are effective.
- For medians, compute from the eligible resolved population only. If the count is even, average the two middle values, then round for display.
- For rates and status policies, keep incomplete or active entities in the denominator when the request says so. Evaluate better statuses first, then fall through to the final "otherwise" status.

## Controlled Corrections

Only mutate data when the prompt explicitly requests an authorized controlled correction and the API documents a transaction endpoint.

1. Identify the unique contradiction or correction target from SQL first. Record the source row ID, business entity ID, field, old canonical value, and new canonical value.
2. Compute the pre-correction metric requested by the task.
3. Submit the minimal transaction that changes only the approved canonical field and inserts exactly the requested audit record. Keep raw source values, source identity fields, and unrelated rows unchanged.
4. Query after the transaction to verify the corrected value, affected business-row count, audit-row count, and post-correction metric.
5. Report an applied status only when the request's success rule is fully satisfied. Otherwise report the observed result and the non-applied status required by the template.

## Output Discipline

- Produce one JSON object only, with no Markdown, comments, or narrative.
- Do not include fields absent from the template, even if they were useful during analysis.
- Preserve string identifier formats and sort orders exactly.
- Use JSON numbers for numeric fields, not strings.
- If the template uses nonstandard schema keys such as `additional_properties`, `min_items`, `unique_items`, `decimal_places`, or `precision`, treat them as binding instructions.
