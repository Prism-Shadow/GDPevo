---
name: crescent-finance-ops
description: Handle Crescent Arts Collective finance operations tasks — branch close reporting, compensation summaries, payroll reviews, and regional/forecast views. Use when presented with prompt.txt, environment_access.json, request_memo.json, and answer_template.json payloads against the Crescent Finance Ops API.
---

# Crescent Finance Ops Skill

## Overview

This skill covers the end-to-end workflow for Crescent Arts Collective finance operations tasks. Each task follows a consistent pattern: read structured inputs, fetch live data from the Crescent Finance Ops API, compute results against an answer template, and return a single JSON response with strict formatting and ordering rules.

## Input File Conventions

Every task provides exactly four input artifacts:

| File | Purpose |
|------|---------|
| `prompt.txt` | Natural-language description of the business context, data sources to use, and what to produce. |
| `payloads/environment_access.json` | Base URL, service name, and a list of allowed API endpoints for this task. |
| `payloads/request_memo.json` | Task-specific parameters: identifiers (branch, ensemble, production, region, scenario), periods or years, focus areas, and optional memo notes. |
| `payloads/answer_template.json` | The required output schema with mandatory top-level keys, field types, rounding and ordering rules. |

When `environment_access.md` is present at the workspace root, its base URL takes precedence over the one in `environment_access.json`.

## API Interaction Protocol

### Base URL Resolution

1. Check `environment_access.json` for `base_url`. If the value is the placeholder `<TASK_ENV_BASE_URL>`, fall back to `environment_access.md` (if present) for the actual base URL.
2. Otherwise use the literal `base_url` from `environment_access.json`.

### Request Format

- **Method**: GET only.
- **Authentication**: No headers required.
- **Query strings**: Allowed when the task input or request memo implies filtering (e.g., by `branch_id`, `ensemble_id`, `production_id`, `period`, `fiscal_year`, etc.).
- **Path construction**: Concatenate the base URL with the endpoint path from `available_endpoints`. No trailing slash on the base.

### Endpoint Reference

The Crescent Finance Ops API exposes these endpoints across task types:

| Endpoint | Returns |
|----------|---------|
| `/api/finance/branches` | Branch master data (id, name, region). |
| `/api/finance/period-map` | Period-to-fiscal-year convention mapping (M1–M24). |
| `/api/finance/accounts` | Chart of accounts (account_id, type, category). |
| `/api/finance/records` | Ledger records (branch, account, period, amount, dimensions). |
| `/api/compensation/rate-book` | Compensation rate definitions by pay type, effective dates. |
| `/api/compensation/rosters` | Employee rosters with service periods, pay types, and flags. |
| `/api/compensation/scenarios` | Forecast scenarios with rate adjustments over time. |
| `/api/payroll/rate-book` | Payroll rate definitions by category and service type. |
| `/api/payroll/productions` | Production schedules, services, and musician assignments. |

### Data Strategy

Read every endpoint listed in `available_endpoints` even if some data appears redundant. Use query-string filters on `/api/finance/records` to scope results to the target branch, region, or period. For compensation and payroll, always load the full rate book and the full roster/production before computing totals.

## Output Construction Rules

### General Rules (apply to every task)

1. Return a **single JSON object** — never an array at the top level.
2. Include **every key** listed in `required_top_level_keys` of the answer template.
3. Match the **exact type** specified in `field_types`. If a field is listed as `currency`, output a number rounded to 2 decimal places. If listed as `decimal percent`, output a number rounded to 4 decimal places (0.1234 represents 12.34%).
4. **Lists must use ascending stable IDs** (branch_id, musician_id, etc.) unless the template or a rank field dictates descending order.
5. **Alphabetically sort** conflict flag lists.
6. When a field type is an **enum**, use exactly one of the listed string values.

### Rounding Reference

| Format | Decimal Places | Example |
|--------|---------------|---------|
| `currency` | 2 | 12345.67 |
| `decimal percent` | 4 | 0.1234 |
| `ratio` | 4 | 1.2345 |

### Ordering Reference

| Context | Order |
|---------|-------|
| Branch IDs | Ascending alphanumeric |
| Musician IDs | Ascending alphanumeric |
| Pay types (compensation) | Order from rate book |
| Conflict flags | Alphabetical |
| EBITDA ranking | Descending (rank 1 = highest) |

## Task Family Patterns

### Finance Branch Close / Regional Reporting

**Endpoints**: `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, `/api/finance/records`

**Key computations**:
- Map periods to fiscal years using the period map (M1–M12 → one FY, M13–M24 → the next).
- Construct income statements by summing `records` amounts grouped by account type (Revenue, COGS, SGA, Allocations).
- EBITDA = Revenue − COGS − SGA − Allocations (or Revenue − COGS = Gross Margin, then Gross Margin − SGA − Allocations = EBITDA).
- EBITDA Margin = EBITDA / Revenue.
- ARPU = Revenue / roster_count or relevant headcount dimension.
- Sales per Labor Headcount = Revenue / headcount dimension from branch data.
- Revenue growth = (current − prior) / prior, expressed as decimal percent.
- Region reconciliation: sum branch-level amounts and compare to any region-level total from the records endpoint; report the difference.

**Branch rankings**: Compute the metric (sales growth, ARPU, EBITDA) per branch, sort descending, and assign integer ranks (1 = top).

### Compensation Summaries

**Endpoints**: `/api/compensation/rate-book`, `/api/compensation/rosters`, optionally `/api/compensation/scenarios`

**Key computations**:
- Roster counts: count employees on the roster for the target ensemble.
- Pay types: use the ordered list from the rate book. Standard types: Minimum Weekly Scale, Titled Position Premium, Seniority, Overscale.
- Quarter totals: sum all compensation amounts whose effective dates fall within each quarter.
- Pay type totals: sum amounts grouped by pay type across the entire year.
- Annual total: sum of all pay type totals (must equal sum of quarter totals).
- Largest pay type: the pay type string with the highest annual total.
- Combined overscale employee count: count of employees who receive Overscale pay at any point.
- Partial quarter employee count: count of employees whose service period starts after Q1 or ends before Q4.

### Payroll Reviews

**Endpoints**: `/api/payroll/rate-book`, `/api/payroll/productions`

**Key computations**:
- Service counts: count of each service type (performance, rehearsal, sound_check, etc.) from the production schedule.
- Category totals: for each pay category, multiply applicable service counts by the rate from the rate book. Include adjustments for guarantee, substitution, vacation, premiums, and doubles.
- Per-musician totals: group services and rates by musician, summing to a per-musician total with a category breakdown (nonzero categories only).
- Top-paid musician: the musician_id with the highest per-musician total.
- Conflict flags: check production schedule against rate-book rules. Valid flags:
  - `REHEARSAL_EARLY_START` — rehearsal start before allowed earliest time.
  - `REHEARSAL_LATE_END` — rehearsal end after allowed latest time.
  - `SERVICE_OVER_TIME_LIMIT` — any service duration exceeds the contract maximum.
  - `SOUND_CHECK_DURATION_MISMATCH` — sound check duration does not match the contracted duration.

### Compensation Forecasts

**Endpoints**: `/api/compensation/rate-book`, `/api/compensation/rosters`, `/api/compensation/scenarios`

**Key computations**:
- Annual totals: compute total compensation for current year, year+1, and year+2 using scenario-adjusted rates.
- Growth rates: (year+1 − current) / current and (year+2 − year+1) / (year+1), both as decimal percent.
- Year+2 quarter and pay type totals: same logic as the compensation summary but applied to the year+2 forecast data.
- Largest growth pay type: identify the pay type with the largest absolute dollar increase between current and year+2, and return its enum string.

## Execution Checklist

1. Read `prompt.txt` to identify the task family and business context.
2. Load and parse all three payload files (`environment_access.json`, `request_memo.json`, `answer_template.json`).
3. Resolve the base URL and confirm the endpoint list.
4. Fetch **all** data from every available endpoint; apply query-string filters where the request memo implies scoping.
5. Compute every field required by the answer template, applying the task-family formulas above.
6. Apply rounding: currency → 2 decimals, percent/ratio → 4 decimals.
7. Apply ordering: ascending IDs by default, descending for rank fields, alphabetical for conflict flags.
8. Assemble the final JSON object with every `required_top_level_key` present and correctly typed.
9. Validate the output against the `field_types` specification before returning.
10. Never include extra keys beyond what the answer template requires. Do not embed commentary or metadata.
