---
name: wealth-advisory
description: Private wealth advisory planning engine that produces structured JSON analyses from an advisory API environment. Use when the user asks to prepare a planning output for a client using a supplied API base URL, or when the task involves Roth conversion RMD analysis, ILIT Crummey funding, GRAT-versus-CRAT trust comparison, or estate liquidity action plans. Triggers on phrases like "Prepare the requested structured planning output for client", "advisory API", "Roth conversion", "ILIT", "GRAT", "CRAT", "Crummey", "estate liquidity", "retirement accounts", "trust comparison", or when answer templates with enums like STAGED_ROTH_CONVERSION or FUND_WITH_CRUMMEY_NOTICES appear in context.
license: MIT
compatibility: designed for deepagents-code
---

# Wealth Advisory Planning

## Overview

Deliver structured planning JSON for private wealth advisory engagements:
Roth conversion RMD projections, ILIT Crummey funding cycles, GRAT-versus-CRAT
trust comparisons, and estate liquidity action plans. Data comes from a
task-environment advisory API; source documents may conflict because they were
imported from different advisory systems at different times.

## Workflow

Follow these steps for every advisory task:

1.  Identify the client ID and analysis type from the request memo.
2.  Determine the answer template by reading the template file supplied in the
    task payloads (usually `input/payloads/answer_template.json`). Every output
    field in the template must be present in the final JSON.
3.  Fetch all relevant data from the API. Start all GET calls in parallel.
    Use `API_BASE` as the base URL (supplied by the harness).
4.  Resolve source conflicts using the fixed hierarchy in
    [source_resolution.md](references/source_resolution.md). Conflicts are
    resolved field-by-field; record which source controlled each category.
5.  Compute all quantitative fields using the formulas and rules in
    [analysis_types.md](references/analysis_types.md).
6.  Assemble the output as a single JSON object. Every key declared as
    `required_top_level_keys` in the template must appear. Use `null` only
    when the template explicitly allows it; otherwise provide a zero value
    for absent numeric fields.

## Reference Files

Read these based on what you need:

- [api_endpoints.md](references/api_endpoints.md) — all API endpoints, their
  response shapes, and filter patterns. Read this first when you need to call
  the advisory API.
- [source_resolution.md](references/source_resolution.md) — the fixed hierarchy
  for resolving conflicts across SIGNED_PROFILE, ATTORNEY_MEMO, CUSTODIAN_EXPORT,
  CRM_NOTE, and STALE_MARKETING_INTAKE sources. Read this before resolving
  any client data conflicts.
- [analysis_types.md](references/analysis_types.md) — computation formulas,
  enum selection rules, and field-by-field guidance for each of the four
  analysis types. Read this after you have fetched data and resolved sources.

## API Call Strategy

Every analysis type requires several endpoints. Determine the client ID from
the request memo, then fetch in parallel:

```
GET /api/clients/{client_id}
GET /api/source-documents
GET /api/policies/tax
GET /api/rmd-factors
GET /portal/client/{client_id}
```

Add type-specific endpoints:

- Roth conversion RMD: `GET /api/retirement-accounts`
- ILIT Crummey: `GET /api/life-insurance`
- Trust comparison: `GET /api/trust-candidates`
- Estate liquidity: `GET /api/life-insurance` and `GET /api/trust-candidates`

Filter collection endpoints by `client_id` in code after fetching — the API may
not support query-parameter filtering.

## Output Format

- Return only a single JSON object. No markdown fences, no prose outside the JSON.
- `task_id`: use the stable task identifier provided in the task context
  (e.g. `train_001`, `test_001`). Do not hardcode it.
- `client_id`: the client ID from the request memo.
- `analysis_type`: the enum value declared in the answer template.
- All USD amounts must be JSON numbers rounded to cents.
- All dates must be ISO 8601 strings (`YYYY-MM-DD`).
- Enums must match the template values exactly (uppercase with underscores).
- The `action_set` list (Type 4) must be sorted alphabetically.

## Conflict Resolution Rules

When source documents disagree on a field value, apply the hierarchy.
The controlling source for each category goes into `source_resolution`.
If a higher-tier source is missing the field, fall through to the next tier.
Never average or blend conflicting values — pick one and record the source.

Full hierarchy tables are in [source_resolution.md](references/source_resolution.md).
