---
name: atlas-commerce-ops-solver
description: Solve Atlas Commerce Operations benchmark tasks that provide a prompt, request payload JSON, answer_template.json, and authenticated task-environment API. Use for SQL-based operational analytics, cutoff/as-of metrics, strict answer.json generation, and approved canonical corrections with correction_audit verification.
---

# Atlas Commerce Ops Solver

## Core Workflow

1. Read the task prompt, every request payload under `input/payloads/`, and `answer_template.json` before querying data. Treat the request payload as the business contract and the template as the output contract.
2. Load the live schema and data dictionary from the task environment. Use [references/api.md](references/api.md) for the endpoint contract and `scripts/atlas_api.py` for repeatable calls.
3. Build the answer from SQL, not from denormalized intuition. Start with a cohort CTE, add one CTE per metric, then run independent count checks for every requested denominator, numerator, and sorted list.
4. Use [references/metric-patterns.md](references/metric-patterns.md) when the task involves effective source rows, cutoff state, refunds, fulfillment, carrier corrections, warehouse productivity, support health, or inventory movements.
5. Write exactly one JSON object to `answer.json`. Match required keys, nesting, array lengths, sorting, number precision, enum values, and `additionalProperties` restrictions from the template. Do not include commentary outside the JSON document.

## Query Discipline

- Preserve UTC text timestamps and compare them lexicographically only when they are all ISO-8601 UTC strings. Apply inclusive and exclusive boundaries exactly as stated.
- Distinguish current snapshot columns from append-only event/scans tables. When the request says `effective`, `as of cutoff`, or similar, derive state from the relevant source event stream at or before the cutoff.
- For imported source rows with `source_system`, `external_event_id`, and `ingested_at`, dedupe retries before aggregating. Keep the row with the latest `ingested_at`; use the table's stable row id as a deterministic tie-breaker.
- Use canonical fields for operational analytics and approved corrections. Never mutate raw fields, source identity fields, or unrelated rows.
- Convert minor monetary units to major units before FX conversion. Join `fx_rates` on the row currency and the request-specified service date or event date.
- Round only final reported values, using the decimal places required by the template or request. Keep unrounded values for ranking and threshold comparisons.
- Sort identifier arrays exactly as requested, usually ascending. For ranked objects, sort by the stated metric before applying the stated tie-breaker.

## Validation Checklist

- Confirm the SQL endpoint did not return `truncated: true`; if it did, aggregate further or narrow the query.
- Re-run at least one alternate query for each high-risk result: cohort count, breach count, correction target, top or worst ranking, and any list of identifiers.
- For correction tasks, report `APPLIED` only after the transaction response and post-change verification satisfy the request's success rule. Otherwise report the observed `NOT_APPLIED` result.
- Validate `answer.json` syntax with `python3 -m json.tool answer.json` before finishing.
