# Computation Recipes

This reference covers every computation pattern seen across the Crescent Finance
Ops reporting domains. When a task's answer template requires a metric, find the
matching recipe here.

---

## Income statement (branch / region finance)

### From records to income statement

Given a set of financial records filtered by period and branch/region:

1. Map each record's `account_id` to its `account_type` via the accounts table.
2. Group records by `account_type`.
3. Sum `amount` per group.

The income statement fields are:

```
revenue       = sum(amount for account_type = Revenue)
cogs          = sum(amount for account_type = COGS)
gross_margin  = revenue - cogs
sga           = sum(amount for account_type = SGA)
allocations   = sum(amount for account_type = Allocations)
ebitda        = gross_margin - sga - allocations
```

`gross_margin` is always positive when `revenue > cogs`. Do not force-sign it.

### Period mapping

The period map uses labels M1 through M24:

```
M1  .. M12  → FY2024
M13 .. M24  → FY2025
```

When the request memo gives a `close_period` (e.g. `"<close_period>"`) and a `prior_period`
(e.g. `"<prior_period>"`), filter records accordingly. For fiscal-year views, sum across
all periods in the fiscal year.

### Region aggregation

A region's financials are the sum of its branches' financials:

1. From the branches table, find all branches whose `region_id` matches the
   target.
2. Sum records for those branches.
3. For reconciliation: compute the region-level total by summing branches and
   compare to any direct region query. The variance is `direct - sum_of_branches`.
   If both methods agree, variance is `0.00`.

### Growth rates

```
revenue_growth_pct = (fy2025_revenue - fy2024_revenue) / |fy2024_revenue|
ebitda_growth_pct  = (fy2025_ebitda  - fy2024_ebitda)  / |fy2024_ebitda|
```

Use absolute value of the denominator. When the denominator is zero, the growth
rate is `null` or `0.0000` — check the answer template for the expected behavior.

Month-over-month revenue variance:

```
mom_revenue_variance.amount = <current_period_revenue> - <prior_period_revenue>
mom_revenue_variance.pct    = (<current_period_revenue> - <prior_period_revenue>) / |<prior_period_revenue>|
```

### Ratios

```
ebitda_margin            = ebitda / revenue
arpu                     = revenue / <headcount or roster_count>
sales_per_labor_headcount = revenue / labor_headcount
```

For `arpu`, the denominator depends on the domain. Use `roster_count` from the
roster if the template is compensation-related. For branch reporting, the
branches table may carry a separate headcount field.

### Rankings

Rank branches by a metric (e.g. EBITDA, sales growth) in descending order.
The branch with the highest value gets rank 1.

- For `sales_growth_rank_desc`, rank across **all** branches in the organization
  by `revenue_growth_pct`, descending.
- For `ebitda_rank_desc` within a region, rank only the region's branches by
  `fy2025_ebitda`, descending.
- `top_sales_growth_branch_id` is the branch with rank 1 in sales growth.
- `top_arpu_branch_id` is the branch with the highest ARPU across all branches.
- `top_ebitda_branch_id` is the branch with the highest FY2025 EBITDA within the
  region.
- `bottom_ebitda_branch_id` is the branch with the lowest FY2025 EBITDA within
  the region.

---

## Compensation (current-year summary)

### Data sources

- Rate book: pay type definitions and base rates.
- Rosters: employee-to-ensemble assignments with pay type, weekly rate or
  multiplier, and active period range.

### Computing quarterly and annual totals

For a target ensemble and current year:

1. From the roster, collect every entry where `ensemble_id` matches the target
   and the active period overlaps the current calendar year.
2. A year has 52 weeks, split into quarters: Q1 (13 weeks), Q2 (13 weeks),
   Q3 (13 weeks), Q4 (13 weeks).
3. For each employee entry, compute pay per quarter:
   - Base weekly rate × weeks active in that quarter.
   - If the employee is active for only part of a quarter, count only the
     overlapping weeks.
4. Sum amounts across employees, grouped by pay type.

The pay types are always:

```
Minimum Weekly Scale
Titled Position Premium
Seniority
Overscale
```

The `pay_types` list in the answer must use this order.

### Quarter totals

```
Q1 = sum of (weekly_rate × active_weeks_in_Q1) across all employees and pay types
Q2 = same for Q2
Q3 = same for Q3
Q4 = same for Q4
```

### Annual pay type totals

Sum each pay type's contribution across all four quarters.

### Roster treatment counts

**`combined_overscale_employee_count`**: Count distinct employees on the
ensemble's roster who have at least one roster row with `pay_type = Overscale`
during any part of the current year, regardless of the overscale dollar amount
(including zero).

**`partial_quarter_employee_count`**: Count distinct employees who are active
for only part of a quarter during the current year. An employee counts if they
started after the first week of any quarter or ended before the last week of
any quarter.

### Largest pay type

The pay type with the highest `annual_pay_type_totals` value. If there is a tie,
pick the one that appears first in the standard pay type order.

---

## Payroll (weekly production review)

### Data sources

- Rate book: per-service-type rates, premium percentages, doubles multipliers,
  guarantee thresholds, vacation credits, substitute rules.
- Productions: schedule of services for a given week, and a roster of musicians
  with instrument assignments and any special flags (vacation accrued,
  substitute status).

### Service counts

From the production schedule for the target week, count each distinct service
type. Common service types:

```
Performance
Rehearsal
Audit
1hr Sound Check
```

The `service_counts` object keys use the exact service type names from the API.

### Category totals

For each service in the schedule:

1. **Performance**: base performance rate from the rate book × number of
   musicians who played the service.
2. **Audit**: base audit rate × number of musicians.
3. **Rehearsal**: base rehearsal rate × number of musicians × rehearsal hours
   (if the rate book specifies an hourly rate for rehearsals).
4. **Sound Check**: base sound check rate × number of musicians.

On top of base service pay, compute:

- **Premium**: additional percentage of the service pay applied per the rate
  book's premium rules (e.g. a premium applies when certain conditions are met,
  such as a musician playing a principal role).
- **Doubles**: additional pay when a musician plays multiple instruments on a
  service. The rate book defines the doubles multiplier (e.g. 1.5× for the first
  double, 2× for the second).
- **Vacation**: vacation pay accrued by musicians per the roster's vacation
  credits.
- **Guarantee adjustment**: when a musician's total pay for the week falls
  below the guaranteed minimum, the difference is added as a guarantee
  adjustment.
- **Substitute adjustment**: pay adjustments when a musician substitutes for
  another.

### Per-musician totals

For each musician in the production roster, sum their earnings across all
categories in which they have nonzero pay. Sort `per_musician` by `musician_id`
ascending.

The `categories` sub-object for each musician includes only the categories with
nonzero amounts for that musician. Category names match the keys in
`category_totals`.

### Top paid musician

The musician with the highest `total` in `per_musician`. If there is a tie, use
the lower `musician_id`.

### Weekly total

Sum of all entries in `category_totals`. This must equal the sum of all
`per_musician[*].total` values.

### Conflict flags

Compare the production schedule against CBA (collective bargaining agreement)
rules stored in the rate book:

- **`REHEARSAL_EARLY_START`**: any rehearsal starts before the CBA-defined
  earliest start hour.
- **`REHEARSAL_LATE_END`**: any rehearsal ends after the CBA-defined latest
  end hour.
- **`SERVICE_OVER_TIME_LIMIT`**: any day's total service time exceeds the
  CBA daily limit.
- **`SOUND_CHECK_DURATION_MISMATCH`**: any sound check's scheduled duration
  differs from the rate book's standard sound check duration.

Flags must be sorted alphabetically. Only include flags that actually apply.

---

## Forecast (board compensation forecast)

### Data sources

- Rate book and rosters: same as the compensation summary domain, used to
  compute current-year base compensation.
- Scenarios: multiplier tables from `/api/compensation/scenarios` that define
  year-over-year adjustments per pay type.

### Computing forecast totals

1. Compute the current-year annual total using the compensation recipe above.
2. Read the scenario from the API using `scenario_id` from the request memo.
3. For each pay type, apply the scenario's Year+1 multiplier to the current-year
   pay type total to get Year+1 amounts. Similarly apply Year+2 multipliers to
   Year+1 amounts (or to the current base, depending on how the scenario is
   structured — follow the API's scenario format).
4. Sum across pay types for each year's total.

### Year+2 quarter totals

For the Year+2 projection, split the annual total into quarters:

- If the scenario provides quarterly distributions, use them.
- If not, split evenly: Q1 = Q2 = Q3 = Q4 = annual_total / 4. But if the API
  provides quarter-specific multipliers, apply those.

### Growth rates

```
year_plus_1_vs_current   = (year_plus_1_total - current_total) / |current_total|
year_plus_2_vs_year_plus_1 = (year_plus_2_total - year_plus_1_total) / |year_plus_1_total|
```

### Largest growth pay type

Compute the absolute dollar increase for each pay type from current to Year+2:

```
delta = year_plus_2_pay_type_total - current_pay_type_total
```

The pay type with the largest positive `delta` is the `largest_growth_pay_type`.
Classify using the exact enum string from the template's `field_types`. If
multiple pay types have the same delta, pick the one appearing first in the
standard pay type order.

### Roster treatment counts

Same definitions as the compensation summary:

- **`combined_overscale_employee_count`**: distinct employees with any Overscale
  roster row during the forecast window.
- **`partial_quarter_employee_count`**: distinct employees active for only part
  of any quarter in the forecast window.

Apply these counts across all forecast years (current, Year+1, Year+2).

---

## Rounding

All rounding uses standard round-half-up (Python's `round()` for positive
numbers; for negative values the behavior should still be half-up).

| Type | Decimal places | Example |
|------|---------------|---------|
| currency | 2 | `123456.78` |
| decimal percent | 4 | `0.0966` |
| ratio | 4 | `0.2459` |

Always round intermediate results as well as final values. When computing a
ratio, compute the division with full precision, then round the result to 4
decimal places.

---

## Formatting conventions summary

| Rule | Applies to |
|------|-----------|
| IDs ascending | `branch_ids`, `per_musician` musician_id order |
| Keys match template exactly | all top-level and nested keys |
| Enum values verbatim | `largest_pay_type`, `conflict_flags` entries |
| Nonzero categories only | `per_musician[*].categories` |
| Zero included for schema completeness | top-level `category_totals` |
| Alphabetical sorting | `conflict_flags` |
| Rank-descending | `sales_growth_rank_desc`, `ebitda_rank_desc` |
