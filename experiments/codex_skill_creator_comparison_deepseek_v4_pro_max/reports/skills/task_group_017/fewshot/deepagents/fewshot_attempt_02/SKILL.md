---
name: investigation-review-hub
description: Collect evidence from the Investigation Review Hub REST API, analyze structured answer templates, and produce strictly-typed JSON outputs for legal/regulatory review workflows. Use when the task provides an Investigation Review Hub base URL, a template JSON schema, and asks for a gap analysis, remediation dashboard, retention review, privilege review, or production-readiness deliverable. Trigger on prompts containing TASK_ENV_BASE_URL, Investigation Review Hub, answer_template.json, or structured investigation deliverables with enumerated JSON schemas.
license: MIT
compatibility: designed for deepagents-code
---

# Investigation Review Hub

## Workflow

Every investigation task follows the same sequence:

1. **Read all task payloads** — `prompt.txt`, every file under `input/payloads/`, especially the request-context JSON and `answer_template.json`. The template defines the exact output schema, enums, ordering rules, and numeric precision.

2. **Discover hub resources** — Call `GET /` and `GET /api/schema` at the base URL to confirm available endpoints and data shapes.

3. **Gather evidence** — Call the relevant GET endpoints (matters, subpoena-categories, productions, custodian-sources, documents/search, privilege-log, qc-findings, retention-events, remediation-actions). Use `POST /api/query` with SQL when cross-entity joins are needed.

4. **Build the answer** — Construct a single JSON object conforming exactly to the template. Return no prose outside the JSON.

## API Access

The base URL is provided as `TASK_ENV_BASE_URL` in request-context payloads. Replace this placeholder with the actual URL before calling endpoints.

All GET endpoints return JSON arrays or objects. Call them with `curl -s` or equivalent.

**SQL endpoint**: `POST /api/query` accepts a JSON body `{"query": "<SQL>"}` and requires the `X-API-Key` header. Read the API key from task payloads (typically `query_api_key` or `query_header` fields) — do not hardcode it.

For the full endpoint catalog and field schemas, read [references/hub_api_reference.md](references/hub_api_reference.md).

## Answer Construction Rules

These rules apply to every answer regardless of review type.

### Schema compliance

- Use every required top-level key from the template.
- Every object in a list must include every required key listed under `item_required_keys`.
- Use exactly the enum values defined in the template. Never invent or abbreviate values.
- Read `item_field_types` for every object to understand what each field means.

### Stable record IDs

- Use IDs exactly as returned by the hub endpoints. Do not invent, transform, or abbreviate them.
- Every `_id` field (finding_id, issue_id, risk_id, correction_id, action_id) must anchor to a specific hub record — a retention event ID, privilege log entry ID, QC finding ID, source ID, or document ID.
- When the template asks for `source_refs`, `record_refs`, `target_refs`, `blocking_refs`, or `issue_refs`, list the hub IDs that support that entry. Sort them ascending.

### Ordering rules

- Sort every list per the template's `ordering_rules`. The common rule is "sort by X ascending" — apply it.
- Within category lists, sort category codes ascending.

### Numeric precision

- All counts are whole integers. Never use floats, decimals, or strings for count fields.
- Use `0` for counts when the measure is not applicable to the current issue.
- For boolean fields, return `true` or `false` (JSON boolean, not string).

### Cross-entity linking

- When a QC finding references a privilege log entry, include both IDs in `source_refs`/`record_refs`.
- When a retention event affects multiple categories, list all of them in `affected_categories`.
- When a source is a remediation path for categories, list those categories in the limits-loss field.
- A single source, event, or finding can impact multiple categories; the same ID should appear in every relevant category's ref list.

### Category codes

- Use category codes exactly as they appear in hub data or task payloads.
- Task payloads like `review_scope.json` or `matter_context.json` provide code-to-description mappings.
- Never convert codes to descriptions in output fields that expect codes.

### Action plans

- Assign the highest priority rank (1) to the most urgent action.
- P0 actions are disclosure/waiver items with legal exposure. P1 actions are immediate remediation. P2 actions are important but less time-sensitive. P3 are monitoring items.
- Use owner enums from the template — do not invent new owners.
- For `due_days` fields, use short windows (3–7 days) for P0/P1 and longer windows (10+ days) for P2/P3.

## SQL Query Patterns

Use `POST /api/query` when you need joins across hub entities. Common patterns:

- Join documents to QC findings to get document-level coding details.
- Join privilege-log entries to documents to get withheld/logged/unlogged counts per category.
- Join retention events to sources to verify archive availability.
- Use `SELECT … FROM … WHERE matter_id = '<id>'` to scope to the current matter.
- When counting, use `COUNT(*)` and cast results to integers.

Always include the `X-API-Key` header with the value from task payloads.

## References

- [Hub API Reference](references/hub_api_reference.md) — Full endpoint catalog, field schemas, and query examples.
- [Analysis Patterns](references/analysis_patterns.md) — Patterns organized by review type with field-mapping guidance.
