---
name: crescent-finance-ops
description: Compute structured finance, compensation, and payroll reports from the Crescent Finance Ops API. Use this skill whenever a task involves the Crescent Finance Ops API, branch close packages, income statements, revenue variance, fiscal-year comparisons, regional reporting, branch rankings, compensation summaries by quarter or pay type, compensation forecasts, ensemble roster analysis, weekly payroll calculations, musician pay breakdowns, or CBA/contract conflict flagging. The skill provides domain rules for every supported endpoint group so the agent can fetch raw API data and produce a single JSON answer matching a supplied template.
---

# Crescent Finance Ops Reporting

This skill covers computing structured reporting results from a staged task
environment that exposes a Crescent Finance Ops API. Every task follows the
same input pattern: three payload files plus a prompt that names them.

## Quick-start workflow

1. Read all staged inputs: `prompt.txt`, `payloads/environment_access.json`,
   `payloads/request_memo.json`, `payloads/answer_template.json`.

2. Fetch every raw data endpoint listed in the environment access file, using the
   `base_url` it provides. Never substitute a different base URL. The API
   returns JSON arrays; use `curl` or an equivalent HTTP tool.

3. Identify which domain applies from the endpoints `environment_access.json`
   lists and from the request memo's focus:
   - **Finance** (`/api/finance/*`): branch P&L, regional views, rankings.
     Read `references/finance.md`.
   - **Compensation** (`/api/compensation/*`): ensemble pay summaries, forecasts.
     Read `references/compensation.md`.
   - **Payroll** (`/api/payroll/*`): weekly production payroll, musician detail,
     contract conflict flags. Read `references/payroll.md`.

4. Compute every value the answer template requires. Derive each field from the
   raw API data using the domain rules in the appropriate reference file. Do not
   fabricate numbers; every currency, percent, ratio, and ranking must be
   traceable through the API payloads.

5. Format the output exactly as the answer template specifies:
   - Currency values: round to 2 decimals.
   - Percent and ratio fields: round to 4 decimals.
   - Lists: ascending stable ID order unless a rank field explicitly states
     descending order.
   - Per-entity arrays (e.g., `per_musician`): sorted by the entity's ID field
     in ascending order.
   - Sorted lists of flags or labels: alphabetical order.
   - Every key in `required_top_level_keys` must be present; do not add extra
     keys.

6. Validate the JSON output against the template's `required_top_level_keys` and
   `field_types` before returning. Run `scripts/validate_template.py` against
   the output for a machine check.

## Input file conventions

| File | Purpose |
|------|---------|
| `prompt.txt` | Scenario narrative (who, what, why). Read for context but do not let it override explicit fields in the other files. |
| `payloads/environment_access.json` | `base_url` and list of `available_endpoints`. Fetch every endpoint listed. |
| `payloads/request_memo.json` | Target entity IDs, periods, focus areas. Drives data scoping. |
| `payloads/answer_template.json` | Exact output schema: `required_top_level_keys`, `field_types`, and formatting rules in `description`. |

## API behavior

All endpoints under the base URL return JSON. Fetch them with a single HTTP GET
per endpoint. The data is static for the lifetime of a task — no mutations,
pagination, or authentication are needed.

### Endpoint groups

| Group | Endpoints | Key entities |
|-------|-----------|-------------|
| Finance | `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, `/api/finance/records` | branches, periods (M1–M24, FY2024=FY2025), account categories |
| Compensation | `/api/compensation/rate-book`, `/api/compensation/rosters`, `/api/compensation/scenarios` | ensembles, employees, pay types, forecast scenarios |
| Payroll | `/api/payroll/rate-book`, `/api/payroll/productions` | productions, musicians, schedules, service rates |

## Answer template compliance

The `answer_template.json` `description` field contains formatting rules
(rounding, sort order). The `required_top_level_keys` list is authoritative —
return exactly those keys, no more. The `field_types` block shows the expected
type and structure of each key; match it precisely. When `field_types` lists a
value as an "enum", use exactly one of the listed strings.

## Domain reference files

- `references/finance.md` — income statement construction, FY aggregation,
  ratios, regional context, branch rankings.
- `references/compensation.md` — per-employee pay calculation, quarter/week
  logic, forecast growth application, roster treatment counts.
- `references/payroll.md` — per-musician service pay, premiums, vacation,
  guarantees, substitute adjustments, conflict flag detection.

Read the relevant reference file after identifying the domain from the
endpoints. If a task spans multiple domains (unusual but possible), read
each referenced file.

## Validation script

Run `scripts/validate_template.py` with the output JSON file and the answer
template file to catch missing keys, type mismatches, and obvious formatting
errors before delivering the result. Fix anything it reports and re-run.
