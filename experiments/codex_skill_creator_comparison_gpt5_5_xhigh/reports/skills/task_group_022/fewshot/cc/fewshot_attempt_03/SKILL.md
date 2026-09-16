---
name: atlas-commerce-ops-sql
description: Use this skill whenever a task asks for Atlas Commerce Operations workplace analysis, scorecards, reconciliations, SLA reviews, warehouse or fulfillment metrics, refund/payment exposure, carrier scan corrections, inventory operations, or strict answer.json generation from the task environment SQL APIs. It guides schema discovery, safe SQL, controlled correction transactions, metric construction from payload rules, and exact JSON output validation.
---

# Atlas Commerce Ops SQL

Use this skill to solve Atlas Commerce Operations tasks that provide a prompt, request payloads, an `answer_template.json`, and a task environment URL. The expected result is almost always a single strict `answer.json` object.

## Workflow

1. Read the prompt, every file under `input/payloads/`, and the answer template before querying. Treat request payload definitions as the source of truth for cohort, cutoff, ranking, rounding, risk/status rules, and whether mutation is allowed.
2. Load schema context from the task environment: `GET /api/schema` and `GET /api/data-dictionary`. See [API and schema](references/api-and-schema.md) for endpoint usage and schema relationships.
3. Build the SQL around the requested cohort first. Apply production exclusions, account/campaign/warehouse/region filters, inclusive or strict time boundaries, and cutoff-as-of logic exactly as stated.
4. Prefer source-of-truth event history for "at cutoff", "effective", "latest", or active-clock language. Denormalized `current_status` fields are useful for sanity checks, but historical state should come from append-only events or scans when a cutoff is involved.
5. Deduplicate imported source rows before deriving facts when a table has `source_system`, `external_event_id`, and `ingested_at`. Keep the latest ingested copy per source event unless the request explicitly wants raw import attempts.
6. Decompose the metric into auditable CTEs: cohort rows, effective events, per-entity facts, aggregate counts, ranking tables, and final scalar output. Run intermediate count/list queries before trusting the final JSON.
7. Use unrounded values for comparisons and ordering. Round only final reported fields, with the precision from the template or request.
8. If the request is analytical only, use only `POST /api/sql`. If it explicitly approves a correction, use the controlled transaction endpoint and post-change verification; never mutate raw source fields or unrelated rows.
9. Write exactly `answer.json` and validate it against the provided template. The helper [validate_answer.py](scripts/validate_answer.py) checks the common template subset used by these tasks.

## Metric Recipes

Read [metric patterns](references/metric-patterns.md) when the task involves:

- fulfillment or shipment completeness and severe exceptions
- refund settlement, reversals, FX, leakage, or reason ranking
- carrier scan raw/canonical correction and audit reporting
- warehouse task productivity, rework, delayed work, or team ranking
- support case response/resolution active-time SLAs

The recipes are patterns, not answer keys. Always rederive the SQL from the current prompt and payloads.

## Final JSON Discipline

- Preserve the template's property names exactly.
- Do not add commentary, wrapper objects, markdown fences, or extra fields.
- Sort arrays exactly as specified, usually by stable IDs after applying metric-specific ranking.
- For rates and medians, compute with full precision and then format the JSON number at the requested precision.
- For enum status/risk fields, evaluate the listed rules in order and use the fallback only when earlier rules fail.
- If a mutation partially fails or verification does not match the request's success rule, report the observed result and the non-applied status required by the request.
