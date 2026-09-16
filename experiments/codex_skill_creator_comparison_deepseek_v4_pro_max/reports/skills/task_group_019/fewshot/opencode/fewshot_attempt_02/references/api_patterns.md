# API Patterns for Licensing Review

This reference covers the shared environment conventions for all three licensing review domains.

## Base URL and Credentials

The task's `environment_access.md` file provides:
- `<TASK_ENV_BASE_URL>` — the base URL to use in all API calls
- `X-Task-Token` header value — required for `POST /api/sql`

Replace every `<TASK_ENV_BASE_URL>` reference in the prompt with the actual base URL.

## Fetch Pattern

All GET endpoints return JSON arrays. Run independent GET calls in parallel. Chain only when a later call depends on a result from an earlier one.

```bash
# Example: parallel fetch for contractor review
curl -s "${BASE}/api/policies" &
curl -s "${BASE}/api/contractor/applications" &
curl -s "${BASE}/api/contractor/bonds" &
curl -s "${BASE}/api/contractor/insurance" &
curl -s "${BASE}/api/contractor/license-history" &
curl -s "${BASE}/api/contractor/violations" &
curl -s "${BASE}/api/contractor/correspondence" &
curl -s "${BASE}/api/contractor/inspections" &
wait
```

## SQL Endpoint

`POST /api/sql` accepts a JSON body with a `query` field:

```bash
curl -s -X POST "${BASE}/api/sql" \
  -H 'Content-Type: application/json' \
  -H 'X-Task-Token: <token-value>' \
  -d '{"query": "SELECT * FROM violations WHERE license_no = '\''EXAMPLE-LIC-001'\'' AND violation_date <= '\''2025-04-10'\''"}'
```

Use SQL when:
- A GET endpoint returns records for all entities but you need only a subset
- Multiple datasets need joining (e.g., licensees joined with violations by address)
- Records have non-obvious identifiers that require a join to resolve
- You need date-range filtering not supported by the GET endpoint

## Answer Template Conventions

Every task provides an `input/payloads/answer_template.json`. Read it before producing output. The template is authoritative for:
- Allowed top-level keys (do not add extras)
- Allowed enum values for each field
- Ordering rules (ascending, chronological, rank-order)
- Empty-value conventions (use `[]`, not `null`)

Never invent field names, codes, or structure beyond what the template defines.
