---
name: investigation-review-hub
description: Use when the user asks you to produce structured investigation, gap-analysis, remediation, or production-readiness deliverables from the Investigation Review Hub API. The skill teaches you how to explore the hub, run SQL queries, and map findings to a provided answer template. Do not use for tasks that do not mention the Investigation Review Hub, the `<TASK_ENV_BASE_URL>` token, or the hub API endpoints.
---

# Investigation Review Hub Analysis

## Overview

This skill covers structured investigation-review tasks where the deliverable is a single JSON object that conforms to a payload `answer_template.json`. The data source is a shared Investigation Review Hub reachable at `<TASK_ENV_BASE_URL>`. The hub exposes read-only REST endpoints and a parameterised SQL query endpoint. Task-specific context lives in `input/payloads/`; answers and evaluation files must never be inspected.

## Discovery phase

### 1. Read the environment access file

Look for an `environment_access.md` file (or similar) in the task root. It contains:

- The resolved base URL for `<TASK_ENV_BASE_URL>`.
- The list of allowed GET endpoints.
- The POST `/api/query` contract: required headers, JSON body shape, and an example `curl` invocation.

Memorise these values. The SQL endpoint always requires the header `X-API-Key` with the value shown in the file.

### 2. Read the task payloads

Inside `input/payloads/` there are at least two files:

- **`answer_template.json`** — the authoritative output schema. It defines required top-level keys, field types, enum choices, ordering rules, and numeric precision. Everything you return must conform to this schema exactly.
- **A second context file** — named `request_context.json`, `review_scope.json`, or `matter_context.json`. It provides the `matter_id`, environment configuration hints, and an output contract section. Use the `matter_id` to scope all hub queries.

### 3. Read the task prompt

`input/prompt.txt` describes the analysis the user needs. Extract:

- The **analysis type** (gap analysis, retention review, remediation dashboard, production-readiness review).
- The **matter identifier** (usually in the prompt as well as the context payload).
- Any **specific focus areas** the user highlights (e.g., privilege log gaps, personal device collection, QC miscoding).

## Hub exploration strategy

### Phase 1: Schema discovery

Call `GET /api/schema` first. It returns table/column metadata so you can write correct SQL later. Pay attention to column names, types, and foreign-key relationships.

### Phase 2: Broad GET exploration

Use the GET endpoints to gather reference data and understand the scope. Prioritise those most relevant to the analysis type:

| Analysis type | Priority GET endpoints |
|---|---|
| Gap / production-readiness | `/api/matters`, `/api/subpoena-categories`, `/api/productions`, `/api/custodian-sources`, `/api/documents/search` |
| Retention / preservation | `/api/matters`, `/api/subpoena-categories`, `/api/retention-events`, `/api/custodian-sources` |
| Remediation dashboard | `/api/matters`, `/api/subpoena-categories`, `/api/retention-events`, `/api/qc-findings`, `/api/privilege-log`, `/api/remediation-actions` |

You may also query `/api/documents/search`, `/api/privilege-log`, and `/api/qc-findings` to collect numeric metrics (document counts, withheld/logged/unlogged tallies).

### Phase 3: Targeted SQL queries

When GET endpoints do not give precise enough results, use `POST /api/query`. Always:

- Send `Content-Type: application/json`.
- Send the `X-API-Key` header from the environment access file.
- Use parameterised queries: `{"sql": "SELECT ... WHERE matter_id = ?", "params": ["<matter_id>"]}`.
- Filter by matter_id or by record IDs discovered during Phase 2.
- Prefer `SELECT` with explicit column lists; avoid `SELECT *` without `LIMIT`.

Common query patterns:

- Count documents by category, coding, or production status.
- Count privilege entries by log status (logged vs. unlogged).
- Find QC findings linked to a matter or specific document.
- List retention events with their status and affected categories.
- List remediation actions with owners and priorities.
- Cross-reference sources with subpoena categories.

## Schema conformance rules

### General rules

1. **Return exactly one JSON object.** No prose before, after, or around the JSON.
2. **Use stable IDs.** Every record reference (matter, source, event, QC finding, document, action, category) must use the exact identifier string from the hub, not a generated or guessed value.
3. **Honour ordering rules.** The template specifies sort orders (e.g., "by finding_id ascending", "by priority_rank ascending"). Apply them.
4. **Use only valid enum values.** Every string field constrained by an enum must use one of the listed values verbatim. If the template defines an `enums` or `enum_choices` block, those are the only allowed values.
5. **Respect required keys.** Every object inside a list must contain all keys listed under `item_required_keys` (or `required_top_level_keys` for the root). Do not add extra keys.
6. **Numeric precision.** All counts and metrics are whole integers. Use `0` when a count is not applicable, not `null` and not omitted. Boolean fields must be `true` or `false`.
7. **Null handling.** Some fields allow `null` — only use `null` where the template explicitly permits it. When in doubt, check the field type definition: if it says `"string or null"`, `null` is allowed; otherwise default to a safe value (`0` for integers, `""` for strings, `[]` for lists).

### Template-driven field mapping

The answer template uses either a `fields` object, a `schema` object, or inline `item_field_types` to describe each output field. Regardless of style:

- Match every required key listed in the template.
- Use the field-level `description` to understand what data belongs in that field.
- Map hub data to template fields by data type, not by name matching.
- Lists of category codes must use the exact codes from the hub (e.g., `R07`, `SEC-1`, `A`), sorted ascending.
- Lists of record references must contain stable hub IDs, sorted ascending.

### Metrics object

Every template defines a `metrics` object with specific `required_keys`. Compute these from hub data:

- Count documents, sources, events, or categories by filtering hub records against the matter.
- Derive unlogged counts as `withheld - logged` when both are available.
- Set boolean readiness flags based on whether any open gaps remain.
- List affected categories in the order they appear in the hub.

## Validation before returning

1. Check the output against `required_top_level_keys` — every key must be present.
2. For every list item, verify all `item_required_keys` are present.
3. Confirm every enum field uses one of the allowed values from the template.
4. Verify sort order on every keyed list.
5. Check that every count is a whole integer.
6. Ensure no prose or commentary outside the JSON.
