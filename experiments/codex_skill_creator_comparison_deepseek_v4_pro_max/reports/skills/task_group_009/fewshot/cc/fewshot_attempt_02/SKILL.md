---
name: crescent-finance-ops
description: |
  Use this skill whenever the task involves Crescent Arts Collective finance
  operations reporting. Trigger when you see payloads named environment_access.json,
  request_memo.json, and answer_template.json, or when asked to prepare branch close
  packages, compensation summaries, payroll reviews, regional management reports, or
  board compensation forecasts. Also use when the task references a Finance Ops API
  with endpoints under /api/finance, /api/compensation, or /api/payroll. This skill
  covers the full workflow: resolving the API base URL, fetching operational data,
  computing financial metrics, and formatting JSON answers that match strict output
  templates.
---

# Crescent Finance Ops

## Workflow overview

Every Crescent Arts Collective reporting task follows the same three-phase
workflow. Follow these steps in order; do not skip or reorder them.

1. **Load and resolve** — read the three payloads, resolve the real API base URL
   from the task environment file (`environment_access.md` in the workspace root).
2. **Fetch** — call every API endpoint listed in the environment payload. Read
   every response fully before computing anything.
3. **Compute and format** — build the answer JSON using the computation recipes
   in [references/computations.md](references/computations.md). Match the
   answer template exactly.

If a memo or template field is unclear, resolve the ambiguity by reading the API
data first — the live data is authoritative.

## Phase 1: Load and resolve

### The three payloads

Every task provides these three payload files under `payloads/`:

| File | Purpose |
|------|---------|
| `environment_access.json` | `base_url` (with `<TASK_ENV_BASE_URL>` placeholder) and `available_endpoints` |
| `request_memo.json` | Target entity (branch, ensemble, production, region), reporting focus, parameters |
| `answer_template.json` | Required keys, field types, rounding rules, ordering conventions |

### Resolve the base URL

The `environment_access.json` file contains `"base_url": "<TASK_ENV_BASE_URL>"`.
This is a placeholder. Read `environment_access.md` in the workspace root to
find the real base URL. Use **that** URL for all API calls. Do not use the
placeholder string.

The `environment_access.md` file also lists which endpoints are available in
the task environment. Cross-check this against the `available_endpoints` in
the environment payload — only endpoints present in both are callable.

### Read the answer template carefully

The `answer_template.json` is the contract. It defines:

- **`required_top_level_keys`** — every key must appear in the answer. Missing
  a key is a hard error.
- **`field_types`** — the type and shape of every field. Nested objects are
  described recursively. When a field type says `"currency"`, the value must be
  a number rounded to 2 decimal places. When it says `"decimal percent"`, round
  to 4 decimal places.
- **`description`** — carries global formatting rules and ordering conventions
  (e.g. "Lists must use ascending stable IDs unless a rank field states
  otherwise").

When the template lists a key like `"<period>_income_statement"` whose label embeds
a period ID from the request memo, treat the label as a schema slot — use the
period ID from the memo, not the literal string.

## Phase 2: Fetch API data

### Calling the API

All endpoints return JSON arrays of objects. Call each endpoint exactly as
listed — the path is relative to the resolved base URL. For example, if the
base URL is `http://task-env:9009/` and the endpoint is `/api/finance/branches`,
call `http://task-env:9009/api/finance/branches`.

Use standard HTTP GET. No authentication headers are needed. Each response is
a JSON array. Read the full array into memory before processing.

### Finance endpoints

These endpoints serve branch-level financial reporting:

- **`/api/finance/branches`** — every branch in the organization. Each entry
  has at minimum `branch_id`, `branch_name`, `region_id`, and labor headcount
  fields.
- **`/api/finance/period-map`** — maps period labels (M1 through M24) to fiscal
  years. By convention M1–M12 belong to FY2024, M13–M24 to FY2025.
- **`/api/finance/accounts`** — the chart of accounts. Each account has an
  `account_id` and an `account_type` (e.g. Revenue, COGS, SGA, Allocations).
- **`/api/finance/records`** — the transaction ledger. Each record has
  `period_id`, `branch_id`, `account_id`, and `amount`. Summing amounts grouped
  by these dimensions produces financial statements.

### Compensation endpoints

- **`/api/compensation/rate-book`** — pay rates by pay type. The standard pay
  types are Minimum Weekly Scale, Titled Position Premium, Seniority, and
  Overscale.
- **`/api/compensation/rosters`** — employee assignments. Each entry ties an
  employee to an ensemble for one or more periods, with a pay type and weekly
  rate or rate multiplier.
- **`/api/compensation/scenarios`** — forecast adjustments. A scenario applies
  multipliers or overrides to base compensation for future years.

### Payroll endpoints

- **`/api/payroll/rate-book`** — rates for each service type (Performance,
  Rehearsal, Sound Check, Audit) plus premium, doubles, vacation, and guarantee
  rules.
- **`/api/payroll/productions`** — production schedules and rosters. Each
  production has a schedule of services and a roster of musicians with their
  assignments.

### Verify you have complete data

After fetching, sanity-check:

- You have data for every entity referenced in the request memo (branch,
  ensemble, production, region, scenario).
- Periods referenced in the memo exist in the period map.
- Account types needed for the income statement exist in the chart of accounts.
- For compensation, the ensemble's roster members span the requested time
  window. For forecast tasks, the scenario data covers the requested years.

## Phase 3: Compute and format

### General formatting rules

These rules apply to every answer regardless of domain:

- **Currency**: round to exactly 2 decimal places. Use standard rounding
  (half-up).
- **Percent / ratio**: round to exactly 4 decimal places. Express as a decimal,
  not a percentage string (e.g. `0.0966`, not `"9.66%"`).
- **Lists of IDs**: sort ascending by the stable identifier unless a field name
  ends in `_rank` or `_ranking`, in which case sort by the rank value.
- **Object keys**: use exactly the key names from the template. Do not reorder
  top-level keys; keep the order from `required_top_level_keys`.
- **Missing or zero categories**: for payroll `per_musician` categories, only
  include keys whose value is nonzero. For top-level category totals, include
  every category listed in the template's `category_totals` schema — use `0`
  for categories with no activity.

### Computation recipes

Detailed recipes for each domain are in
[references/computations.md](references/computations.md). Read that file when
you need the exact formula. Here are the core patterns:

**Income statement** — group records by account type, then compute:

```
revenue   = sum(records where account_type = Revenue)
cogs      = sum(records where account_type = COGS)
gross_margin = revenue - cogs
ebitda    = gross_margin - sga - allocations
```

**Growth rates** — for any metric X across two periods:

```
growth_pct = (X_later - X_earlier) / |X_earlier|
```

If `X_earlier` is negative or zero, use absolute value in the denominator.

**Ratios** — the most common ones:

```
ebitda_margin = ebitda / revenue
arpu          = revenue / <headcount or roster_count>
sales_per_labor_headcount = revenue / labor_headcount
```

**Rankings** — rank entities by a metric in descending order (1 = highest).
When ranking across all branches in the organization, use every branch, not
just the target region's branches, unless the template says otherwise.

**Reconciliation** — when a region total is constructed by summing its
branches, verify that the sum matches a direct region-level query result. The
variance is `region_direct - sum_of_branches`. Report 0.00 if the two agree.

**Compensation** — for an ensemble over a time window:

1. From the roster, collect every employee assigned to the ensemble in the
   target periods.
2. For each employee, multiply their weekly rate × number of weeks in the
   period. If the employee started or ended mid-period, pro-rate by the number
   of active weeks.
3. Sum by pay type across all employees.
4. "Combined overscale" count = number of roster members who carry any
   Overscale pay component during any part of the window (even if zero amount).
5. "Partial quarter" count = number of roster members who are active for only
   part of a quarter (started after quarter began or ended before quarter end).

**Payroll** — for a production over one week:

1. From the production schedule, count each service by type.
2. For each service, look up the base rate per musician in the rate book.
3. Apply premiums, doubles multipliers, and guarantee adjustments per the rate
   book rules and the production's roster details.
4. Vacation and substitute adjustments are applied per the roster (vacation
   credits, substitute pay rules).
5. Sum across categories for each musician, then across musicians for the
   weekly total.
6. Conflict flags come from comparing the production schedule against CBA
   rules: rehearsal start before a threshold hour, rehearsal ending after a
   threshold, total service time exceeding a daily limit, sound check duration
   not matching the booked slot. The flag names are the exact enum values from
   the template: `REHEARSAL_EARLY_START`, `REHEARSAL_LATE_END`,
   `SERVICE_OVER_TIME_LIMIT`, `SOUND_CHECK_DURATION_MISMATCH`. Sort flags
   alphabetically.

**Forecast** — for an ensemble across future years:

1. Read the scenario from `/api/compensation/scenarios` using the scenario ID
   from the request memo.
2. The scenario contains year-over-year multipliers or rate adjustments per pay
   type.
3. Apply adjustments to the current-year base compensation (computed from the
   rate book and roster as described above) to project Year+1 and Year+2.
4. The "largest growth pay type" is the pay type with the greatest absolute
   dollar increase between the current year and Year+2. Classify it using the
   exact enum value from the template.
5. Roster treatment counts follow the same rules as the compensation summary
   but applied across the full forecast window.

### Before returning the answer

1. Verify every key in `required_top_level_keys` is present.
2. Verify every nested field described in `field_types` is present.
3. Check all rounding: 2 decimals for currency, 4 for percent/ratio.
4. Check all list orderings.
5. Check that all ID values match exactly what the API returned (do not invent
   or transform IDs).
6. If the template defines an enum for a field (like `largest_pay_type`), use
   exactly one of the listed values.

---

## Reference files

- [references/computations.md](references/computations.md) — detailed
  computation recipes with formulas and edge-case handling.
