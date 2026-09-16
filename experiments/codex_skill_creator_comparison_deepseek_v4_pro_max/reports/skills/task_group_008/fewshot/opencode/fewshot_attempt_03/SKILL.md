---
name: wealth-advisory-planner
description: Complete private wealth advisory planning tasks for trust and estate practitioners. Use when the request involves structured planning output for a client identified by a CLT-* ID, requires JSON output conforming to an answer template, mentions Roth conversions/RMD projections, ILIT/Crummey funding, GRAT vs CRAT comparisons, estate liquidity action plans, or references a task-group advisory API with endpoints like /api/clients, /api/source-documents, /api/retirement-accounts, /api/life-insurance, /api/trust-candidates, /api/policies/tax, or /api/rmd-factors. Also use when the prompt mentions an "API_BASE" variable or a local request memo paired with an answer template.
---

# Wealth Advisory Planner

Support a private wealth advisory team by producing structured JSON planning outputs from the task-group advisory API. The environment always contains client records, source documents, account exports, life-insurance records, trust candidates, tax policy constants, and RMD factors.

## Output discipline

Return only a JSON object that matches the answer template provided in the task payload. Do not include prose, markdown fences, explanations, or surrounding text. The response must start with `{` and end with `}`.

Every field in the template's `required_top_level_keys` must appear. Use the types and enums specified in the template's `fields` section. USD amounts must be JSON numbers rounded to two decimal places (cents). Dates must be ISO strings (`YYYY-MM-DD`). Boolean fields must be JSON `true` or `false`, not strings. Enum values must be exactly one of the allowed strings.

If the template specifies an ordering rule (e.g. `action_set` sorted alphabetically), follow it. Otherwise object key order is not constrained but the top-level keys listed in `required_top_level_keys` must all be present.

## API interaction

The task-group advisory API is reachable at the base URL supplied by the harness, typically exposed as the environment variable `API_BASE`. All endpoints are read-only GET requests; the API does not accept writes.

Always start by fetching these data sources. Run all independent GET requests in parallel.

1. `GET {API_BASE}/api/clients/{client_id}` — Client record with age, marital status, filing status, estate value, liquid assets, and planning year.
2. `GET {API_BASE}/api/source-documents` — All source documents. Filter in-memory by `client_id` to get the subset for this engagement. Each document has a `source_type` field identifying its origin.
3. `GET {API_BASE}/api/policies/tax` — One global record: annual gift exclusion, estate tax exemption, estate tax rate, conversion bracket targets, CRAT term cap, and charitable deduction rate. Fetch once per engagement.
4. `GET {API_BASE}/api/rmd-factors` — One global record: map from integer age to RMD divisor. Fetch once per engagement.

Then fetch only the subsets relevant to the engagement type:

5. `GET {API_BASE}/api/retirement-accounts` — Filter by `client_id`. Use for Roth conversion and RMD analysis types.
6. `GET {API_BASE}/api/life-insurance` — Filter by `client_id`. Use for ILIT, Crummey, and estate liquidity analysis types.
7. `GET {API_BASE}/api/trust-candidates` — Filter by `client_id`. Use for trust comparison and estate liquidity analysis types.

After fetching all relevant data, read the detailed per-engagement instructions from [references/analysis-types.md](references/analysis-types.md). That reference covers data requirements per engagement, computation steps, and decision rules.

## Source conflict resolution

Source documents for the same client may disagree because they were imported from different advisory systems at different times. The API returns documents with `source_type` values: `SIGNED_PROFILE`, `ATTORNEY_MEMO`, `CUSTODIAN_EXPORT`, `CRM_NOTE`, and `STALE_MARKETING_INTAKE`.

Read [references/source-resolution.md](references/source-resolution.md) for the full priority order and resolution rules. The controlling source is always the one with the highest priority among documents that contain the relevant fact. Resolve fields point-by-point: a document may control one fact but not another.

In all cases, document your resolution in the output's `source_resolution` block using the enums from the answer template.

## Endpoint catalog

For a full listing of every API endpoint with its URL, response shape, and field meanings, read [references/api-endpoints.md](references/api-endpoints.md). Use it when you need to look up what a particular endpoint returns or what fields are available.
