---
name: northstar-payer-ops
description: Solve Northstar Health Plan payer-operations tasks that require live task-environment evidence and strict JSON output for prior authorization UM reviews, pharmacy appeals and assistance intake, payment-integrity claim repricing, peer-to-peer dispositions, or therapy finance margin queues. Use when prompts mention Northstar, payer operations, TASK_ENV_BASE_URL, sql/query, authorization cases, appeals, claims, P2P, rate schedules, or service margin queues.
---

# Northstar Payer Operations

## Core Workflow

1. Read the user prompt, `input/payloads/task_context.json`, and `input/payloads/answer_template.json` before querying. Treat the template as the output contract.
2. Get the target ID, reporting date or period, base URL, SQL endpoint, and bearer token from the prompt/context. Use only the exposed business endpoints and SQL endpoint; do not inspect environment source, database, generated data, manifests, or setup files.
3. Discover records from the live environment, not from local examples. Start with `/api/tables` when schema is uncertain. For SQL, use [scripts/query_northstar.py](scripts/query_northstar.py).
4. Pull every record family that can affect the requested disposition: case, member, plan, request lines, policy, criteria, documents, facts, authorizations, appeals, assistance screens, drug trials, claims, claim lines, payment benchmarks, P2P events, or service margin rows as applicable.
5. Resolve the business result using the source-precedence rule implied by the work type and answer template. See [references/northstar_operations.md](references/northstar_operations.md) for task-specific checklists.
6. Build only the JSON object requested by the template. Match required keys, enum values, null handling, ordering rules, date formats, and numeric precision exactly. Do not add prose or markdown.

## Basis Audit

Every observed task requires `basis_audit`. Populate it from the records that actually decide the answer:

- `source_precedence`: choose the template enum matching the decisive rule, such as current clinical records over stale exports, payer appeal before manufacturer assistance, effective benchmark by plan/modifier/date, new patient-specific P2P information, margin threshold before charge sensitivity, or appeal deadline before clinical/payment-integrity routing.
- `controlling_record_ids`: IDs for records that directly establish the result, in operational evidence order.
- `exception_record_ids`: IDs or criterion/gap identifiers explaining exclusions, missing information, denial reasons, stale sources, or route priority.
- `precedence_record_order`: controlling and exception records in precedence order, highest priority first.

## Validation Before Final

Before returning, compare the draft JSON against `answer_template.json` field by field. Recompute arithmetic independently, sort lists as specified by the template, use JSON `null` for absent nullable values, and omit fields that the template does not allow.
