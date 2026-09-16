---
name: atlas-ops-analytics
description: "Atlas Commerce Operations analytics platform access for business scorecards, operational reconciliations, quality reviews, productivity reports, and support health reviews. Use when working with the Atlas Commerce Operations API to query business records through schema discovery and SQL analysis, compute operational metrics from business request definitions, apply business classification rules to produce structured answer templates, or execute controlled data corrections with audit records. Trigger when a task references an Atlas Commerce Operations workplace, the /api/schema or /api/sql endpoint, answer_template.json, a cutoff-based operational scorecard, or payloads containing business definitions and classification rules."
license: MIT
compatibility: designed for deepagents-code
---

# Atlas Operations Analytics

## Connection

Every Atlas task provides a base URL and an authorization header. Always start by
confirming connectivity and reading the live schema:



Available endpoints:
- `GET /api/schema` -- table and column listings
- `GET /api/data-dictionary` -- human-readable field descriptions
- `POST /api/sql` -- read-only analytical SQL queries
- `POST /api/sql/transaction` -- controlled data corrections (single-row updates)
- `GET /api/correction-audit` -- audit records for past corrections

Use [scripts/query_atlas.py](scripts/query_atlas.py) for all HTTP calls. It accepts
the base URL, auth token, SQL string, and endpoint name (default `sql`).

## Workflow

All analytical tasks follow a four-step pattern:

### Step 1: Schema Discovery

Call `GET /api/schema` and `GET /api/data-dictionary` before writing any query.
These return plain JSON listing every table, column, and a human-readable
description of what each field means. Read both entirely -- assumptions about
column semantics without the dictionary are the leading source of wrong answers.

Identify which tables hold the core entities (orders, shipments, scans, tasks,
cases, refunds, accounts, warehouses, campaigns, fx rates) and their join keys.

### Step 2: Understand the Business Request

The business request JSON (always named in the prompt) contains the complete
domain logic. Extract these critical sections before writing SQL:

- **scope / cohort** -- which rows qualify (time window, account tier, warehouse,
  campaign, region, segment). Boundary rules: `inclusive` means `>=` start and
  `<=` end; treat timestamps as exact UTC.
- **business definitions** -- what "complete", "on time", "severe exception",
  "backlog", "breach", or "leakage candidate" mean in SQL terms.
- **metric formulas** -- how rates, ratios, and aggregates are computed.
  Rates always use the eligible population as denominator; incomplete items
  remain in the denominator unless the definition explicitly excludes them.
- **rounding rules** -- typically "round only final reported rates to N decimal
  places."
- **classification rules** -- tiered status logic (HEALTHY/WATCH/CRITICAL,
  STABLE/PRESSURED/AT_RISK, CONTROLLED/ELEVATED/SEVERE, LOW/MODERATE/HIGH).
  Apply rules in order; the first matching rule wins. A final "otherwise" or
  "all other outcomes" rule catches everything else.
- **output ordering** -- how arrays must be sorted (ascending, descending,
  multi-key tie-breaks).

See [references/business_patterns.md](references/business_patterns.md) for
common SQL translations of recurring business definitions.

### Step 3: SQL Analysis

Write queries that match the cohort and compute the required metrics. Key
disciplines:

- Build the cohort first as a CTE or sub-select to keep later queries aligned.
- Compute intermediate states (per-order, per-shipment, per-case) before
  aggregating.
- For time arithmetic: subtract timestamps and convert to hours or minutes. Do
  not use string manipulation.
- For currency conversions: join `fx_rates` on the service date and currency,
  multiply the local amount by `usd_per_unit`.
- For medians: when the result count is even, average the two central values.
- Where exact lists are required (e.g. severe exception IDs, delayed task IDs),
  include the `ORDER BY` clause specified in the request.

Submit read-only queries to `POST /api/sql`. The endpoint accepts a JSON body
with a `sql` key.

### Step 4: Compute and Format Answer

Do not write the final JSON from SQL alone. Pull raw results into the
execution context and perform final computations:

- Apply rounding only at the final step and only where specified.
- Apply classification rules using the computed rates.
- Sort arrays exactly as specified (multi-key with explicit direction per key).
- Check every field name, type, and constraint against the answer template.
- The output must be valid JSON with no extra keys, no commentary, and no
  deviation from the template schema.

## Transaction Workflow (Correction Tasks)

When the task includes a correction (always signaled by `POST /api/sql/transaction`
and an `approved_correction` section in the request payload):

1. Query the raw data to find the contradictory row. Use the import batch,
   warehouse, and cutoff from the request to narrow the search.
2. Resolve the contradiction by comparing carrier raw status against the
   canonical status. The correction is always to update the canonical field
   to match the raw/true value.
3. Submit the transaction via `POST /api/sql/transaction`. The body is JSON
   with `sql` (an UPDATE on a single row), `audit_id`, `correction_key`,
   `reason_code`, `actor`, `corrected_at`, and the field/value details.
4. Verify: run a post-change query on the corrected row to confirm the value.
5. Query `GET /api/correction-audit` to confirm exactly one audit row was
   created.
6. Report `APPLIED` only when exactly one business row and one audit row
   committed and the post-change query confirms the correction. Otherwise
   report `NOT_APPLIED`.

## Resources

- [references/api_endpoints.md](references/api_endpoints.md) -- full endpoint
  reference with request/response formats.
- [references/business_patterns.md](references/business_patterns.md) -- common
  SQL patterns for translating business definitions into queries.
- [scripts/query_atlas.py](scripts/query_atlas.py) -- reusable Python script for
  all Atlas HTTP API calls.
