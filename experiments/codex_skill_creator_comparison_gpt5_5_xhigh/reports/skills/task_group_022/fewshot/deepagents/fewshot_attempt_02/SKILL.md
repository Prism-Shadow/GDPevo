---
name: atlas-commerce-ops-analysis
description: Use for Atlas Commerce Operations tasks that ask Codex to query the authenticated workplace API, compute cutoff-based operational metrics, apply an explicitly approved canonical correction, and write a strict JSON answer file from a provided request payload and answer template.
---

# Atlas Commerce Ops Analysis

## Purpose

Solve Atlas Commerce Operations tasks by turning the prompt, request payload, live schema, and data dictionary into reproducible SQL, then writing exactly the JSON object required by the answer template.

## Standard Workflow

1. Read the task prompt, every file under `input/payloads/`, and especially `answer_template.json`.
2. Fetch the live service metadata before writing metric SQL:
   - `GET /api/schema`
   - `GET /api/data-dictionary`
3. Treat the request payload as the source of truth for cohort filters, cutoff boundaries, status/risk rules, ordering, rounding, and mutation authorization.
4. Build SQL in small CTEs that make each business definition inspectable. Run diagnostic count queries before the final answer query.
5. Use only read-only SQL unless the request explicitly authorizes a controlled correction. Never alter raw source values or unrelated rows.
6. Write `answer.json` as one JSON object with exactly the required keys. No prose, no extra fields.
7. Validate the file against the template and re-query any suspicious metric or ordered array before finishing.

## API Helpers

This skill includes two optional deterministic helpers:

- `scripts/atlas_api.py`: calls the task environment endpoints. It reads `TASK_ENV_BASE_URL` if set, otherwise defaults to `http://task-env:9022/`, and sends `Authorization: Bearer $TASK_ENV_API_TOKEN` when that token exists.
- `scripts/validate_answer.py`: performs dependency-free structural checks against the provided answer template, including required keys, extra keys, scalar types, enum, pattern, array length, uniqueness, and common precision hints.

Typical use:

```bash
python skill/scripts/atlas_api.py schema > /tmp/schema.json
python skill/scripts/atlas_api.py dictionary > /tmp/data_dictionary.json
python skill/scripts/atlas_api.py sql /tmp/query.sql > /tmp/result.json
python skill/scripts/validate_answer.py input/payloads/answer_template.json answer.json
```

For a controlled correction, pass the transaction request body through unchanged:

```bash
python skill/scripts/atlas_api.py transaction /tmp/transaction_payload.json
python skill/scripts/atlas_api.py audit
```

## Query Rules

- Use UTC timestamp text comparisons directly when values use the stored ISO-8601 `Z` format.
- Honor inclusive/exclusive wording exactly. Do not turn a strict `before` cutoff into `<=`.
- For ratios, keep incomplete or unresolved records in the denominator when the request says the denominator is the eligible population.
- Use floating-point division deliberately, such as `1.0 * numerator / denominator`.
- Round only final reported numbers. Keep unrounded values for ranking and risk classification.
- Sort arrays exactly as specified. Apply every tie-breaker before limiting.
- Return IDs sorted ascending when the template or request says so, even if the discovery query found them in another order.
- For money, convert minor units to currency units and join `fx_rates` on the row service date and row currency when USD reporting is requested.
- When a task depends on current state at a cutoff, prefer effective event history over convenience `current_status` fields unless the request or dictionary specifically says the snapshot is the source.

Read `references/atlas_patterns.md` when building SQL for source-row dedupe, cutoff state, fulfillment, refunds, warehouse productivity, support active-clock metrics, or canonical corrections.

## Controlled Corrections

Only mutate data when the prompt and request payload explicitly authorize it. A valid correction flow has all of these properties:

- The target row is identified by live records and the request policy, not by guessing.
- The mutation is minimal, usually one canonical field plus correction metadata where the schema provides it.
- Raw source fields, source identity fields, and unrelated business rows are unchanged.
- The transaction appends exactly the requested audit record with the requested idempotency key or correction key.
- A post-change query confirms the corrected canonical value.
- The final answer reports `APPLIED` only when the request's success rule is satisfied; otherwise report `NOT_APPLIED` with the observed result.

## Final Answer Discipline

Build `answer.json` from the template, not from memory. Omit null placeholders unless the schema requires them. Do not include comments, calculations, SQL, or explanation in the final JSON file.
