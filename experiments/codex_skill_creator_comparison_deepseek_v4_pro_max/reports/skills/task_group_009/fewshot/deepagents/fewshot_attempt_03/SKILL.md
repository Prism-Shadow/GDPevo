---
name: crescent-finance-ops
description: "Prepare management reports for Crescent Arts Collective by querying the Crescent Finance Ops API. Use this skill when working with Crescent payroll, compensation, or finance branch/region reporting tasks. The skill covers: (1) Monthly branch close packages with income statements, variance analysis, fiscal-year comparisons, regional context, and branch rankings, (2) Ensemble compensation summaries by quarter and pay type with roster treatment counts, (3) Compensation forecasts with multi-year growth scenarios, (4) Weekly payroll review for theatre productions with service counts, category totals, per-musician breakdowns, contract conflict detection, and (5) Regional management views with cross-year comparisons and branch-level EBITDA rankings. All tasks follow a common pipeline: fetch from the Finance Ops API, apply domain-specific computation rules, and format a JSON answer per the provided answer template."
---

# Crescent Finance Ops

## Overview

Prepare structured JSON management reports for Crescent Arts Collective using
the Crescent Finance Ops API (`base_url` from `environment_access.json`). Every
task follows the same pipeline:

1. Read `environment_access.json` for the API base URL
2. Read `request_memo.json` for the target entity and reporting focus
3. Read `answer_template.json` for the output schema and formatting rules
4. Fetch data from the API endpoints listed in `environment_access.json`
5. Compute results following the domain rules in the reference files
6. Return a single JSON object matching `answer_template.json`

The API serves three domains; use only the endpoints relevant to the request:

| Domain | Endpoints | Reference |
|--------|-----------|-----------|
| Finance | `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, `/api/finance/records` | [finance.md](references/finance.md) |
| Compensation | `/api/compensation/rate-book`, `/api/compensation/rosters`, `/api/compensation/scenarios` | [compensation.md](references/compensation.md) |
| Payroll | `/api/payroll/rate-book`, `/api/payroll/productions` | [payroll.md](references/payroll.md) |

## Common Pipeline

### Step 1: Read Input Payloads

Every task provides three files under the input directory:

- `payloads/environment_access.json` — `base_url` and allowed endpoints
- `payloads/request_memo.json` — target entity ID, reporting focus, memo notes
- `payloads/answer_template.json` — output schema with required keys, field types, and formatting rules

### Step 2: Fetch API Data

Query every endpoint listed in `environment_access.json` with HTTP GET. Each
returns JSON. Always prefer the live API data over any cached or memo values.

### Step 3: Apply Domain Rules

Use the relevant reference file for computation rules:

- **Finance tasks** → [references/finance.md](references/finance.md): income
  statement construction, period mapping, ratio computations (EBITDA margin,
  ARPU, sales per labor headcount), branch rankings, region context, MoM
  variance

- **Compensation tasks** → [references/compensation.md](references/compensation.md):
  per-employee pay computation (MWS, title premium, seniority, overscale),
  quarter and annual totals, combined overscale handling, partial-quarter
  detection, forecast scenario growth, largest pay type identification

- **Payroll tasks** → [references/payroll.md](references/payroll.md): per-service
  pay computation, premiums (doubles, principal/lead, concertmaster, quartet,
  electronic), vacation, weekly guarantee adjustments, substitute adjustments,
  service counts, conflict flag detection

### Step 4: Format the Answer

Follow `answer_template.json` exactly:

- **Required keys**: include every key listed in `required_top_level_keys`
- **Field types**: match the type and structure described in `field_types`
- **Rounding**: currency values to 2 decimals; percent/ratio values to 4
  decimals, as stated in the template's `description` field
- **Ordering**: lists in ascending stable IDs unless a rank field states
  otherwise; `per_musician` lists ordered by musician_id; `conflict_flags`
  sorted alphabetically
- **Omissible keys**: leave out keys whose value would be zero when the field
  type says "when applicable" (e.g. `substitute_adjustment` in payroll category
  totals)

## Domain Quick Reference

### Finance Reports

Two report types:

**Branch close package**: target a single branch + close period. Compute M24
income statement, MoM revenue variance (vs M23), FY2025 vs FY2024 comparison
with ratios, region context, and branch rankings.

**Regional view**: target a region. Compute FY2024 and FY2025 aggregates across
all branches in the region, revenue growth, branch-level EBITDA ranking within
region, and reconciliation variance.

### Compensation Reports

Two report types:

**Current-year summary**: target an ensemble. Compute per-employee pay, quarter
totals, annual pay type totals, largest pay type, and roster treatment counts
(combined overscale employees, partial-quarter employees).

**Forecast**: target an ensemble + scenario. Compute current, Year+1, and Year+2
annual totals using scenario growth rates, growth rates between years, Year+2
quarter and pay type detail, largest growth pay type, and roster counts.

### Payroll Reports

Target a production. For each musician on the roster, compute pay per assigned
service following the rate book rules. Aggregate into category totals and
service counts. Detect conflict flags from the schedule against rate book
thresholds. Identify the top-paid musician.

## Rounding Summary

| Value Type | Precision | Example |
|------------|-----------|---------|
| Currency (revenue, EBITDA, pay, etc.) | 2 decimals | `3483871.60` |
| Percent / ratio (growth, margin, ARPU) | 4 decimals | `0.0966` |
| Counts (roster, headcount, services) | integer | `26` |

## Pay Type Enumeration

All compensation reports use the same ordered pay type list from the rate book:

```
Minimum Weekly Scale
Titled Position Premium
Seniority
Overscale
```

## Conflict Flag Enumeration (Payroll)

```
REHEARSAL_EARLY_START
REHEARSAL_LATE_END
SERVICE_OVER_TIME_LIMIT
SOUND_CHECK_DURATION_MISMATCH
```

Output these alphabetically sorted when present.
