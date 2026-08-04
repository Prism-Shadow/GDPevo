## When to Use

Use this skill when a task supplies `payloads/environment_access.json`, `payloads/request_memo.json`, and `payloads/answer_template.json` and asks for a single JSON result from the Crescent Finance Ops API. The task involves financial reporting, compensation summaries, compensation forecasts, payroll reviews, or regional management views.

## Workflow

### 1. Gather Inputs

Read every file under `payloads/`:

- `environment_access.json` — `base_url` and `available_endpoints`.
- `request_memo.json` — target entities, periods, scenario IDs, and `review_focus`.
- `answer_template.json` — required output keys, field types, and formatting rules (rounding, ordering).

### 2. Map the Domain to API Endpoints

Identify the business domain from `available_endpoints` and call every endpoint listed:

| Domain       | Endpoints                                                                    |
|-------------|------------------------------------------------------------------------------|
| Finance Ops | `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, `/api/finance/records` |
| Compensation | `/api/compensation/rate-book`, `/api/compensation/rosters` (add `/api/compensation/scenarios` for forecasts) |
| Payroll     | `/api/payroll/rate-book`, `/api/payroll/productions`                         |

Fetch all needed data before computing. Query parameters (e.g., `?branch_id=`, `?period=`) may be appended when implied by `request_memo.json` fields.

### 3. Build the Answer

Use the `answer_template.json` `required_top_level_keys` as the exact output shape. Compute each field from the API responses:

**Finance domain computations:**
- `period_convention`: M1–M12 map to one fiscal year, M13–M24 map to the next. Read `/api/finance/period-map` for the mapping.
- `m24_income_statement`: revenue, cogs, gross_margin (= revenue − cogs), sga, allocations, ebitda (= gross_margin − sga − allocations). Read from `/api/finance/records` filtered to the target branch and close period.
- `mom_revenue_variance`: revenue difference (current − prior month) for the target branch; `pct` = amount ÷ prior-month revenue.
- `fy20xx_vs_fy20yy`: Sum records across all months in each fiscal year for the branch, computing ebitda_margin (= ebitda ÷ revenue), arpu (= revenue ÷ active roster count), sales_per_labor_headcount (= revenue ÷ labor headcount). Growth rates = (current − prior) ÷ prior.
- `region_context`: Read `/api/finance/branches` to find which branches belong to the target's region. Sum their fy20xx ebitda and rank the target branch within the region (1 = highest ebitda).
- `branch_rankings`: Compute sales growth rank by comparing revenue growth across all branches. Identify top arpu and top sales growth branches from the full branch set.
- `region_reconciliation_variance`: Sum of branch-level ebitda minus region-rollup ebitda (should net to zero when data is consistent).

**Compensation domain computations:**
- `roster_count`: Count of employees on the target ensemble's active roster.
- `pay_types`: Ordered list of pay type names from the rate book.
- `quarter_totals` / `annual_pay_type_totals`: Sum compensation by quarter and by pay type across all roster members. Read `/api/compensation/rosters` for roster entries and `/api/compensation/rate-book` for rates.
- `annual_total`: Sum of all quarterly or pay-type totals.
- `largest_pay_type`: The pay type with the highest annual total.
- `combined_overscale_employee_count`: Count of roster members who receive Overscale pay under any combined (multi-type) arrangement.
- `partial_quarter_employee_count`: Count of roster members whose service spans only part of a quarter (start/end dates within the year but outside quarter boundaries).
- For forecasts, read `/api/compensation/scenarios` and compute `growth_rates` and `year_plus_2` projections accordingly.

**Payroll domain computations:**
- `service_counts`: Count each service type appearing in the production schedule.
- `category_totals`: Sum pay for each category (performance, audit, rehearsal, sound_check, premium, doubles, vacation, guarantee_adjustment). Include `substitute_adjustment` only when its value is nonzero.
- `weekly_total`: Sum of all category totals.
- `per_musician`: For each musician on the production roster, compute total pay and nonzero category breakdowns. Order by `musician_id` ascending.
- `top_paid_musician_id`: The musician_id with the highest total.
- `conflict_flags`: Inspect the production schedule and roster for CBA violations and emit only the enum values that actually apply: `REHEARSAL_EARLY_START`, `REHEARSAL_LATE_END`, `SERVICE_OVER_TIME_LIMIT`, `SOUND_CHECK_DURATION_MISMATCH`. Sort the resulting list alphabetically.

### 4. Apply Formatting Rules

Every template declares its own rules. Apply the following universally unless a template explicitly overrides:

- **Currency values**: round to 2 decimal places.
- **Percent / ratio values**: round to 4 decimal places.
- **Lists**: ascending order by stable ID (branch_id, musician_id, etc.) unless a rank field dictates descending order.
- **Conflict flag lists**: sorted alphabetically.
- **`substitute_adjustment`**: omit from the output when its value is zero or null.
- **`per_musician` categories**: include only nonzero categories.
- **Output**: exactly one JSON object with all `required_top_level_keys` present.

### 5. Validate

Before returning the answer, verify:
- Every key in `required_top_level_keys` is present.
- Rounding matches the template specification.
- Lists are in the declared order.
- Summations are internally consistent (e.g., category totals sum to weekly total, quarterly totals sum to annual total).
