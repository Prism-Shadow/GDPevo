---
name: crescent-finance-ops-reporting
description: >-
  Prepare Crescent Arts Collective / Finance Ops management reporting deliverables from the
  read-only Finance Ops HTTP API: branch monthly-close packages, regional management views,
  ensemble compensation summaries, multi-year compensation forecasts, and weekly touring
  payroll reviews. Use this whenever a task references the Finance Ops base URL, a
  request_memo + answer_template payload triple, branch/region income statements, EBITDA /
  ARPU / per-headcount metrics, fiscal-year (FY2024/FY2025) comparisons, musician/ensemble
  compensation (minimum weekly scale, seniority, overscale, titled premium), or weekly
  payroll for a production (services, doubles, guarantee, substitutes, CBA conflict flags).
  Trigger even if the user only hands you the payload files and says "fill out the template."
---

# Crescent Finance Ops Reporting

You produce ONE JSON object per task that exactly follows the task's
`payloads/answer_template.json`. The data lives behind a read-only HTTP API. The answer
template tells you the keys, types, and rounding; the `request_memo.json` tells you the
target entity, period, and focus. There are five task families that share conventions but
differ in the formula library. Identify the family first, then apply the matching SOP below.

These instructions encode mistakes that are easy to make and expensive to get wrong. Read
the "Universal conventions" and "Pitfalls" sections every time — the per-field scope and
rounding rules are where outputs silently go wrong.

## How to work a task

1. Read all three payload files: `environment_access.json` (base URL + allowed endpoints),
   `request_memo.json` (what to compute, for whom), `answer_template.json` (output shape,
   types, rounding, ordering).
2. Pull the data you need from the API (curl or python). Cache responses; you'll reuse them.
3. Pick the task family (see "Task families") and compute every required field.
4. Emit a single JSON object with exactly the `required_top_level_keys`, correct types,
   correct rounding, and correct list ordering. Do not add extra keys.

## Environment / API

Base URL comes from `environment_access.json` (e.g. `http://127.0.0.1:8028`). All endpoints
are read-only GET. `GET /api/manifest` lists endpoints and files. Available endpoints
(a task may allow only a subset — check `available_endpoints`):

- Finance: `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`,
  `/api/finance/records` (filters: `?branch_id=` `?region=` `?account=`)
- Compensation: `/api/compensation/rate-book`, `/api/compensation/rosters?ensemble_id=`,
  `/api/compensation/scenarios`
- Payroll: `/api/payroll/rate-book`, `/api/payroll/productions?production_id=`

The API never returns answers, rubrics, or rounding rules — only operating data and rate
books. Derive everything else from the data + the rules below.

**Use current/active operating data, not memo prose.** Memos may mention a "draft
workbook," "background notes," or instruct you to "reconcile against active operations
data." That is a directive to compute from the live API records, NOT to copy numbers out of
the memo. Treat memo notes as context/flags, never as a data source that overrides the API.

## Universal conventions (apply to every task)

### Rounding — this is a top error source
- **Currency: 2 decimals.** Percent/ratio fields: 4 decimals. Counts/ranks: integers.
- **Round HALF-UP, not banker's rounding.** Python's built-in `round()` uses round-half-EVEN,
  which gives the wrong answer on `.xx5` boundaries (e.g. `round(424.125, 2)` -> `424.12`,
  but the correct figure is `424.13`). Use half-up explicitly:
  ```python
  from decimal import Decimal, ROUND_HALF_UP
  def r2(x): return float(Decimal(str(x)).quantize(Decimal('0.01'), ROUND_HALF_UP))
  def r4(x): return float(Decimal(str(x)).quantize(Decimal('0.0001'), ROUND_HALF_UP))
  ```
  Round at the LAST step (when populating the output field), computing on full-precision
  intermediates. Do not round-then-sum.

### "decimal percent" / ratio fields are FRACTIONS at 4dp
A field typed `"decimal percent"` or `"ratio"` (ebitda_margin, growth pct, variance pct,
ARPU-as-ratio, etc.) is the raw fraction, not a 0-100 number. 8.95% -> `0.0895`, NOT `8.95`.
A 6.56% growth is `0.0656`. Margin 22.58% is `0.2258`. Never multiply by 100.

### Period / fiscal-year mapping
Periods are labels `M1..M24`. The FY mapping comes from `/api/finance/period-map`
(`period -> fiscal_year`). In the seen data: M1-M12 = FY2024, M13-M24 = FY2025. Always read
period-map rather than assuming; build `FY -> [periods]` and aggregate over that period set.
For monthly close: the close month is its own single period; the prior month is the adjacent
label (M24 close -> M23 prior).

### Ordering & ties
Lists default to ascending stable IDs (branch_ids, employee/musician order) unless a field
name says otherwise (e.g. a `_rank_desc` field, or "ordered by musician_id"). Conflict-flag
lists are sorted alphabetically. Ranks are 1-based, descending by the stated metric.

### Output hygiene
Emit exactly the `required_top_level_keys`. Match enum spellings verbatim
(e.g. `"Minimum Weekly Scale"`). Include conditionally-present fields only when applicable
(see per-task notes), and per-entity category maps should list nonzero entries only when the
template says "nonzero".

## Income-statement model (finance tasks 1 & 4)

Accounts carry a `category`; build the income statement from category membership (confirm
against `/api/finance/accounts`):

| Line | Accounts (category) |
|---|---|
| revenue | product_revenue + service_revenue (revenue) |
| cogs | direct_materials_cogs + direct_labor_cogs (cogs) |
| gross_margin | revenue - cogs |
| sga | sales_sga + admin_sga + occupancy_sga (sga) |
| allocations | shared_service_allocations (allocations) |
| ebitda | gross_margin - sga - allocations |

`ebitda_margin = ebitda / revenue` (4dp fraction).
Growth: `(current - prior) / prior` (4dp fraction). MoM variance amount is currency;
MoM variance pct is the 4dp fraction.

Operating-count accounts (metric_type `count`): active_customers, labor_headcount,
admin_headcount, orders, revenue_units, backlog. These are MONTHLY SNAPSHOTS.

### ARPU and per-headcount metrics — SCOPE PITFALL (very high error)
For an FY ratio whose denominator is a monthly count account (ARPU, sales_per_labor_headcount,
sales per anything), the denominator is the **SUM of the monthly counts over the FY periods**
("customer-months" / "labor-months"), NOT the 12-month average and NOT a single month.

```
arpu_FY                     = FY revenue / sum(active_customers over FY periods)
sales_per_labor_headcount   = FY revenue / sum(labor_headcount over FY periods)
```

Averaging the denominator inflates the result by exactly 12x — a classic wrong answer.
At region level: numerator = region FY revenue (sum of branches); denominator = sum over
branches of the summed monthly counts.

### Region rollups & ranking
- A region's branch set = ascending `branch_id`s whose `region_id` matches.
- Region FY block = sum of member branches' account totals for that FY.
- `region_reconciliation_variance` = region aggregate EBITDA - sum of member-branch EBITDA
  = `0.0` (it ties out by construction). The "tie back" memo note is a reconciliation
  instruction, not a clue that a hidden figure exists.
- Region EBITDA rank (in `region_context`) = rank of the REGION among all regions by FY
  EBITDA, descending. Branch top/bottom EBITDA = rank branches within the region by FY EBITDA.
- Sales-growth rank / "top sales growth branch" = by revenue growth PERCENT across branches,
  descending. "Top ARPU branch" = highest FY ARPU across branches.

## Compensation model (tasks 2 & 5)

Source: `/api/compensation/rate-book` and `/api/compensation/rosters?ensemble_id=`
(scenarios from `/api/compensation/scenarios` for forecasts).

- `current_year` comes from the rate-book field, not the system clock.
- `roster_count` = number of roster employees.
- `pay_types` order = the rate-book `pay_types` list verbatim:
  `["Minimum Weekly Scale", "Titled Position Premium", "Seniority", "Overscale"]`.

Per employee, per quarter (multiply each weekly amount by that quarter's weeks):

| Pay type | Weekly amount |
|---|---|
| Minimum Weekly Scale | `minimum_weekly_scale` (e.g. 2520) |
| Titled Position Premium | `title_premium_pct[title] * minimum_weekly_scale` (base is the MWS, not overscale/seniority) |
| Seniority | seniority band `weekly_amount` for `years_of_service` (bands: min_years..max_years inclusive; null max = open-ended) |
| Overscale | `overscale_weekly` |

- Use the roster's `weeks_by_quarter`, NOT a flat 13, so partial-quarter employees are
  handled (rate-book business rule). `quarter_totals` sum over employees+pay-types per
  quarter; `annual_*` sum across all quarters.
- **`combined_overscale_includes_title == true`**: suppress that employee's Titled Position
  Premium (it's folded into overscale). `combined_overscale_employee_count` = count of
  employees with this FLAG true. Do NOT confuse with "count of employees with overscale > 0".
- **`partial_quarter_employee_count`** = count of employees with ANY quarter where
  weeks != the full-quarter weeks (i.e. != 13).
- `largest_pay_type` (single-year summary, task 2) = pay type with the largest ANNUAL TOTAL
  (a LEVEL comparison; MWS typically wins).

### Forecast specifics (task 5)
Scenario provides per-year `mws_growth`, `overscale_growth`, `seniority_growth`,
`title_pct_multiplier`.

- **Growth COMPOUNDS across years.** Year+2 multiplier = `(1 + y1_growth) * (1 + y2_growth)`
  for each of MWS, overscale, and the seniority weekly amount. Apply separately per pay type.
- **Seniority has TWO effects, both applied:** (1) add years of service before banding
  (+1 yr for Year+1, +2 yrs for Year+2, per the business rule — this can move an employee
  into a higher band), AND (2) multiply the band amount by the compounded seniority growth.
- `title_pct_multiplier` multiplies the title premium percentage (1.0 = no effect).
- Growth-rate fields are 4dp fractions of total comp year-over-year.
- **`largest_growth_pay_type` = pay type with the largest RELATIVE (percentage) growth**
  current -> Year+2, NOT the largest absolute dollar change. Seniority often wins here
  because the band shifts + compounding outpace MWS's larger-but-smaller-% dollar increase.
  Contrast with task 2's `largest_pay_type` (a level comparison). When a field says
  "growth"/"driver", compare percentages unless it explicitly says "amount"/"dollar".
- `combined_overscale_employee_count` / `partial_quarter_employee_count`: same definitions
  as task 2.

## Weekly payroll model (task 3)

Source: `/api/payroll/rate-book` and `/api/payroll/productions?production_id=`. The
production has a `schedule` (services) and a `roster` (musicians with flags + assigned
service IDs).

- `service_counts` = count of each `service_type` in the schedule.
- Base service pay per service:
  - Rehearsal: hourly `Rehearsal` rate * `max(duration_hours, 3.0)` (3-hour minimum call).
  - Performance / Audit / Sound Check: per-service flat rate from `service_rates`.
- Premiums apply to the musician's base service pay BEFORE vacation. From `premium_pct`:
  - principal_or_lead (0.15 if principal or lead), quartet (0.15), electronic (0.25),
    concertmaster (0.20 if flagged). Stack additively as a percentage of base.
  - Doubles: `first_double` (0.25) for the first extra instrument + `additional_double`
    (0.10) for each further extra; `doubles = N` -> `0.25 + 0.10*(N-1)` of base.
- Vacation = `vacation` pct (0.04) * (base + premiums) ONLY when `vacation_eligible` is true.
- Weekly guarantee = `max(0, weekly_guarantee - base service pay)`, for guaranteed REGULAR
  players only (NOT substitutes). Goes in `guarantee_adjustment`.

### Substitutes — PITFALL: they ARE paid, and can be the top earner
A roster entry with `substitute: true` is NOT excluded and does NOT get `substitute_adjustment = 0`.
A substitute earns MORE than the flat base, via:
- A performance-rate uplift (Performance services paid at ~1.5x; Audit is NOT uplifted), and
- A separate `substitute_adjustment` line item (must appear in `category_totals` whenever any
  substitute exists; appears in that musician's `categories`).
- Premiums (electronic/doubles/etc.) are computed on the substitute's uplifted base.
- A substitute gets NO weekly guarantee. Vacation still gates on the `vacation_eligible`
  flag (independent of substitute status).
- Because substitute pay is higher, RECOMPUTE `top_paid_musician_id` AFTER applying it — the
  top earner can flip to the substitute.

### CBA / conflict flags
Enum: `REHEARSAL_EARLY_START`, `REHEARSAL_LATE_END`, `SERVICE_OVER_TIME_LIMIT`,
`SOUND_CHECK_DURATION_MISMATCH`. Derive from the schedule vs rate-book thresholds:
- REHEARSAL_EARLY_START: a rehearsal `start_time` earlier than `rehearsal_earliest_start`.
- REHEARSAL_LATE_END: a rehearsal `end_time` later than `rehearsal_latest_end`.
- SERVICE_OVER_TIME_LIMIT: any service `duration_hours` exceeding its `service_time_limits` entry.
- SOUND_CHECK_DURATION_MISMATCH: a sound-check duration not matching its nominal length.
Output the flags sorted alphabetically (deduplicated).

### Output ordering (task 3)
`per_musician` ordered by `musician_id`; each `categories` map lists nonzero categories only;
`category_totals` includes `substitute_adjustment` only when applicable; `weekly_total` =
sum of per-musician totals; currency at 2dp half-up.

## Task families (quick selector)

| Memo signal | Family | Output anchor keys |
|---|---|---|
| target_branch_id, close_period/prior_period | Branch monthly close | period_convention, m24_income_statement, mom_revenue_variance, fy2025_vs_fy2024, region_context, branch_rankings |
| target_region_id, comparison years | Regional view | fy2024, fy2025, revenue_growth_pct, top/bottom_ebitda_branch_id, region_reconciliation_variance |
| ensemble_id, current_year_by_quarter_and_pay_type | Comp summary | quarter_totals, annual_pay_type_totals, largest_pay_type, combined_overscale/partial counts |
| ensemble_id + scenario_id, year_plus_1/2 | Comp forecast | annual_totals, growth_rates, year_plus_2_* , largest_growth_pay_type |
| production_id, service/roster | Weekly payroll | service_counts, category_totals, per_musician, weekly_total, conflict_flags, top_paid_musician_id |

## Pitfalls checklist (verify before emitting)

- [ ] Currency 2dp, ratios/percents 4dp, counts integer — and rounded HALF-UP (not Python `round`).
- [ ] Every "decimal percent" is a fraction (0.0895), never 8.95.
- [ ] FY mapping read from period-map; FY sums over the correct period set.
- [ ] ARPU / per-headcount denominators = SUM of monthly counts over the FY (not average, not 1 month).
- [ ] Region rank = region-among-regions; branch top/bottom = within region; growth ranks by %.
- [ ] region_reconciliation_variance = 0.0 (ties out).
- [ ] Comp: title premium based on MWS; use roster weeks_by_quarter; combined-overscale &
      partial counts are FLAG/weeks counts, not overscale>0.
- [ ] Forecast: growth compounds; seniority gets band-shift + growth; largest_growth_pay_type
      by PERCENT growth.
- [ ] Payroll: substitutes are PAID (uplift + substitute_adjustment); guarantee excludes subs;
      recompute top-paid after substitute pay; conflict flags sorted; categories nonzero only.
- [ ] Exactly the required_top_level_keys; enum strings verbatim; correct list ordering.
- [ ] Data taken from the live API, not from memo prose.
