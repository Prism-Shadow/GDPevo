---
name: investigation-hub
description: E-discovery and legal investigation review using a shared Investigation Review Hub REST API. Use when producing structured JSON gap analyses, retention reviews, production-readiness assessments, or remediation dashboards for litigation/regulatory matters by querying the hub's matter, subpoena-category, document, privilege-log, QC-finding, retention-event, custodian-source, and production endpoints.
---

# Investigation Hub

Use the Investigation Review Hub REST API to gather evidence and produce a structured JSON deliverable. Every task supplies:

- A **prompt** describing the review type and deliverable
- An **answer template** (`answer_template.json`) defining the exact output schema
- An **environment base URL** (`<TASK_ENV_BASE_URL>`) for the hub API
- Optionally, a **review scope** payload with client-facing context

## API

See [references/api_endpoints.md](references/api_endpoints.md) for all endpoint paths and response shapes.

### Key patterns

- **All GET endpoints return JSON arrays**; iterate over them, do not assume a single result.
- **The read-only SQL endpoint is `POST /api/query`** and requires header `X-API-Key: review-key-017` when the prompt supplies that key. The request body accepts `{"sql": "<statement>"}`.
- **Every entity has a stable ID field** (`matter_id`, `doc_id`, `source_id`, `event_id`, `finding_id`, `action_id`, `category_code`). Always use these as-is from hub responses — never invent or rewrite them.
- **Use the schema endpoint** (`GET /api/schema`) to confirm table and column names before writing SQL.

## Workflow

### 1. Gather context

Read the prompt, `answer_template.json`, and any review-scope or matter-context payload files. Note:

- The `matter_id`
- The environment base URL (substitute `<TASK_ENV_BASE_URL>` with the actual URL)
- The SQL API key if mentioned
- The required top-level keys and ordering rules in the template

### 2. Discover the hub

Fetch `GET /api/schema` to confirm available tables and column names. Also fetch the matter and subpoena categories for this matter:

- `GET /api/matters` — filter by the prompt's `matter_id`
- `GET /api/subpoena-categories` — request-category codes and descriptions for the matter

### 3. Gather evidence by review type

Match the review type described in the prompt to the relevant endpoints. Common mappings:

| Review type | Primary endpoints to query |
|---|---|
| Rolling production gap analysis | `/api/productions`, `/api/custodian-sources`, `/api/documents/search`, `/api/privilege-log`, `/api/qc-findings` |
| Retention / litigation-hold gap review | `/api/retention-events`, `/api/custodian-sources`, `/api/remediation-actions` |
| Cross-system remediation dashboard | `/api/retention-events`, `/api/custodian-sources`, `/api/privilege-log`, `/api/qc-findings`, `/api/documents/search`, `/api/remediation-actions` |
| Production-readiness / privilege QC review | `/api/privilege-log`, `/api/qc-findings`, `/api/documents/search`, `/api/custodian-sources` |

When a prompt calls for cross-system or combined analysis, query all relevant endpoints. Use `POST /api/query` when you need counts, groupings, or joins that the GET endpoints cannot express directly. See [references/sql_query_patterns.md](references/sql_query_patterns.md) for common query templates.

### 4. Build the deliverable

Follow the answer template's schema exactly:

- **Top-level keys**: Include every `required_top_level_key` in order.
- **Ordering rules**: Sort arrays as specified (typically ascending by id/code/rank).
- **Category sets**: Sort category codes ascending within any list.
- **Enums**: Use only values listed in the template's `enums` or `enum_choices` blocks. Never invent a value.
- **Counts**: All numeric fields must be whole integers. Use `0` when a field is not applicable, never `null` for count fields.
- **Stable IDs**: Every record reference must use the exact ID from hub responses.

The entity model used across these templates is documented in [references/entity_model.md](references/entity_model.md).

### 5. Return the answer

Return a single JSON object — no prose, no markdown wrapping, no extra commentary outside the JSON.

## Common pitfalls

- **Don't invent IDs** — every record reference must come from a hub response.
- **Don't use `null` for numeric counts** — use `0`.
- **Don't ignore ordering rules** — sort arrays and sub-arrays exactly as specified.
- **Don't assume GET responses are filtered** — always filter by `matter_id` in client code or via SQL.
- **Don't use local files as source of truth** — the hub is authoritative. Local payloads provide review scope context only (category descriptions, task framing).
