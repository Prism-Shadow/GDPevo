---
name: crescent-finance-ops-reporting
description: >-
  Produce Crescent Arts Collective "Finance Ops" reporting deliverables from the read-only Finance Ops
  HTTP API: branch monthly-close packages, regional management views, current-year and multi-year
  compensation summaries/forecasts, and weekly touring-production payroll packages. Use this whenever a
  task references Crescent Arts Collective, a "Finance Ops" base URL / environment_access.json, a
  request_memo.json plus answer_template.json, or asks for income-statement/EBITDA/ARPU/per-headcount
  metrics, FY comparisons and branch rankings, ensemble compensation by quarter and pay type, board comp
  forecasts, or weekly payroll totals/category totals/per-musician pay/CBA conflict flags. It encodes the
  exact API endpoints, the income-statement and compensation/payroll formulas, the rounding/format
  conventions, and the high-error pitfalls (sum-vs-average denominators, growth-rate vs absolute-dollar
  "largest growth", substitute pay uplift, vacation base) that silently produce wrong numbers.
---

# Crescent Finance Ops Reporting

You build JSON reporting deliverables for Crescent Arts Collective from a read-only HTTP API. Every task
gives you three payload files plus a prompt:

- `payloads/environment_access.json` — base URL + the endpoints this task may use.
- `payloads/request_memo.json` — the specific request (target id, period, focus list, sometimes a memo note).
- `payloads/answer_template.json` — the REQUIRED output keys, nested field shapes, and rounding/format rules.

Your output is ONE JSON object that exactly matches the template's `required_top_level_keys` and field
shapes. Produce numbers by querying the live API and applying the formulas below. Never invent data and
never read answers — the API does not expose them.

## Golden rules (these are where blind attempts lose points)

1. **The answer_template is law.** Emit exactly its `required_top_level_keys`, the nested keys it names, and
   nothing it forbids. Match the stated ordering and sorting (ascending IDs, alphabetical flags, rank order).
2. **Rounding/format conventions, read literally from the template:**
   - "currency" → round to **2 decimals**.
   - "decimal percent" / "ratio" / "growth rate" → a **FRACTION rounded to 4 decimals**. 8.95% is
     `0.0895`, NOT `8.95`. A margin of 24.59% is `0.2459`. Never multiply by 100.
   - Use **round half up** at the final precision. Round-half-even or truncation produces 1-cent misses on
     values like 344.125 → must be `344.13`, 111.895 → `111.90`.
   - Round each reported field independently from full precision; do not round intermediates. (A category sum
     may then differ from a displayed total by a cent — that is expected.)
   - JSON serialization may drop a trailing zero (`4390313.80` prints as `4390313.8`); that is the same
     value at 2dp, not an error.
3. **Per-headcount / per-customer denominators are AVERAGES, not sums.** See the dedicated pitfall below —
   this is the single most common silent error.
4. **"Largest growth" means largest growth RATE (%), not largest absolute dollar change.** See the comp
   forecast pitfall.
5. **Use current/active operating data; ignore stale memo/workbook notes.** When a `memo_note` says things
   like "reconcile against the active operations data" or "tie back to the active operating data," it is
   warning you that draft/background notes may be stale — trust the live API records, not the note.

## Environment / API usage

Base URL is in `environment_access.json` (e.g. `http://127.0.0.1:8028`). All endpoints are read-only HTTP
GET. Query with curl or python; prefer python for the arithmetic. Only use endpoints this task lists.

| Endpoint | Returns | Key filters |
|---|---|---|
| `/api/manifest` | endpoint + entity overview | — |
| `/api/finance/branches` | branch_id, branch_name, region_id | — |
| `/api/finance/period-map` | period ("M1".."M24") → fiscal_year, month | — |
| `/api/finance/accounts` | account → category, metric_type (currency/count) | — |
| `/api/finance/records` | per-branch, per-account `values` map keyed by period | `?branch_id= ?region= ?account=` |
| `/api/compensation/rate-book` | scale, pay_types, seniority bands, title pct, business_rules | — |
| `/api/compensation/rosters` | ensemble roster rows | `?ensemble_id=` |
| `/api/compensation/scenarios` | dict keyed by scenario_id with year_plus_1/2 growth factors | — |
| `/api/payroll/rate-book` | service_rates, premium_pct, guarantee, thresholds, business_rules | — |
| `/api/payroll/productions` | production with `schedule` and `roster` | `?production_id=` |

Finance `records` shape: each row is `{branch_id, branch_name, region_id, account, values:{"M1":num,...,"M24":num}}`.
There is no period column — index the `values` map by the periods you need.

**Always read the rate-book `business_rules` array.** Both rate-books embed the authoritative, task-specific
rules (three-hour rehearsal minimum, combined-overscale-includes-title, add years of service before banding,
guarantee only for regulars, etc.). Treat those as overriding any assumption.

## Period / fiscal-year mapping

Derive FY membership from `/api/finance/period-map`; do not hardcode. In the train environment:
M1–M12 = FY2024, M13–M24 = FY2025. A "current close period" like M24 implies prior = M23 and the current
FY = the 12 periods of M24's fiscal year. `period_convention` fields in the template just restate this map.

- Single-month income statement = that one period's values.
- Month-over-month variance = current period − prior period.
- FY total = sum of that FY's 12 periods.

## Income statement composition (finance tasks)

Accounts roll up by their `category`:
- `revenue` = product_revenue + service_revenue
- `cogs` = direct_materials_cogs + direct_labor_cogs
- `gross_margin` = revenue − cogs
- `sga` = sales_sga + admin_sga + occupancy_sga
- `allocations` = shared_service_allocations
- `ebitda` = gross_margin − sga − allocations
- Operating counts (metric_type `count`): orders, revenue_units, active_customers, labor_headcount,
  admin_headcount, backlog. These are point-in-time stocks per month.

Derived ratios/metrics (all over the chosen period, e.g. a full FY):
- `ebitda_margin` = ebitda / revenue  (4dp fraction)
- `revenue_growth_pct` = (FY_curr_rev − FY_prior_rev) / FY_prior_rev  (4dp fraction)
- `ebitda_growth_pct` = (FY_curr_ebitda − FY_prior_ebitda) / FY_prior_ebitda  (4dp fraction)
- `mom_revenue_variance.pct` = amount / prior_month_revenue  (4dp fraction)
- `arpu` = FY revenue / **average** monthly active_customers
- `sales_per_labor_headcount` = FY revenue / **average** monthly labor_headcount

### PITFALL — sum vs average denominator (most common error)
For ARPU and any per-headcount metric, the denominator is the **average of the monthly counts over the
period** (sum of the 12 monthly counts ÷ 12), NOT the sum. Counts are stocks, not flows; summing them yields
a meaningless "customer-months" figure that is ~12× too large and tanks the ratio.
- Correct: `rev / (sum(monthly counts)/months)`.
- Wrong (silent): `rev / sum(monthly counts)` — produces a number ~1/12 the true value.
For a region, divide region revenue by the **sum over member branches of each branch's average monthly
headcount** (equivalently, region revenue ÷ (total monthly headcount ÷ months)) — same result either way.

## Regional rollups, rankings, tie-outs

- A region's branch set comes from `/api/finance/branches` filtered by `region_id`. List `branch_ids`
  ascending unless a rank field says otherwise.
- Region income statement = element-wise sum of member branches' statements (same composition above).
- `region_reconciliation_variance` = 0.00 when the region total is defined as the sum of branches and no
  independent region-level record exists (records are branch-scoped). Compute it as (independent region
  rollup − sum of branches); it is genuinely 0 here.

### Ranking & tie-break rules
- **Scope:** `branch_rankings` (top_*, sales_growth_rank) are **company-wide across all branches**.
  A region-scoped rank (e.g. `region_context.ebitda_rank_desc`) ranks **only the branches in that region**.
  The template's nesting tells you the scope — region_context holds region-scoped ranks.
- `*_rank_desc`: 1 = highest. Sort the relevant metric descending and take the target's 1-based position.
  Recompute the rank from the SAME metric values you already produced — do not eyeball it.
- top_/bottom_ branch ids: argmax/argmin of the metric (e.g. FY2025 EBITDA, FY revenue growth, ARPU).
- "sales growth" for ranking = FY-over-FY revenue growth. "ARPU" ranking uses the avg-customer ARPU above.
- For ties or lists without an explicit rank, break by ascending stable branch_id.

## Compensation model (ensemble summaries and forecasts)

Endpoints: `/api/compensation/rate-book`, `/rosters?ensemble_id=`, `/scenarios`. `current_year` and the
base `minimum_weekly_scale` come from the rate-book. Four pay types, in rate-book order:
`Minimum Weekly Scale`, `Titled Position Premium`, `Seniority`, `Overscale`.

Per employee, per quarter, weekly amount × that quarter's weeks. **Use `weeks_by_quarter` from the roster,
not a fixed 13** — partial-quarter employees have quarters with fewer weeks.

- Minimum Weekly Scale = minimum_weekly_scale × weeks
- Titled Position Premium = minimum_weekly_scale × title_premium_pct[title] × weeks
  - 0 if the employee has no title.
  - **0 if `combined_overscale_includes_title == true`** for that employee — their overscale already
    includes the title premium, so do not add it again (rate-book rule).
- Seniority = seniority_weekly(years_of_service) × weeks. Bands are inclusive `[min_years, max_years]`;
  the top band has `max_years: null` (open-ended). Years below the first band pay 0.
- Overscale = overscale_weekly × weeks

Aggregations:
- `quarter_totals[Q]` = sum over all employees of (MWS+TPP+Sen+Ovr) for that quarter.
- `annual_pay_type_totals[type]` = sum of that pay type across all quarters and employees.
- `annual_total` = sum of all four pay types.
- `largest_pay_type` (summary task) = pay type with the largest annual dollar **total** (largest bucket).
- `roster_count` = number of roster rows.

### Roster treatment counts (review these before sending)
- `combined_overscale_employee_count` = count of roster rows with `combined_overscale_includes_title == true`
  (a FLAG count, not "employees who happen to have both overscale and a title").
- `partial_quarter_employee_count` = count of roster rows where ANY quarter's weeks differ from the standard
  `quarter_weeks` (13). These rows are the partial-quarter employees.

### Forecast (multi-year) extension
Scenario `case_*` provides per-year `mws_growth`, `overscale_growth`, `seniority_growth`,
`title_pct_multiplier` for `year_plus_1` and `year_plus_2`. Apply **compounding** year over year, not
additive-from-base:
- Year+1 factor = (1 + y1_growth); Year+2 factor = (1 + y1_growth) × (1 + y2_growth). `title_pct_multiplier`
  multiplies cumulatively the same way.
- **Add +1 year of service for Year+1 and +2 years for Year+2 BEFORE assigning seniority bands** (rate-book
  rule). This band migration is a real driver of Seniority growth.
- `annual_totals` = current / year_plus_1 / year_plus_2 totals; `growth_rates` = (y1−cur)/cur and
  (y2−y1)/y1 (4dp fractions).
- `year_plus_2_quarter_totals` / `year_plus_2_pay_type_totals` are computed in the Year+2 world.

### PITFALL — "largest growth pay type" is by RATE, not dollars
`largest_growth_pay_type` = the pay type whose growth **rate (percentage)** from current to Year+2 is
largest, NOT the one with the biggest absolute dollar increase. The largest bucket (usually Minimum Weekly
Scale) grows the most dollars but only at its rate; Seniority often grows fastest in % because the +2 years
of service push employees into higher bands on top of the seniority_growth rate. Rank pay types by
`(y2 − current) / current` and pick the max. For the driver classification, name WHY: e.g. Seniority is a
structural/volume driver (band migration) compounded by the rate; MWS/TPP are pure rate drivers.

## Weekly payroll model (touring production)

Endpoints: `/api/payroll/rate-book`, `/productions?production_id=`. The production has a `schedule` (services
with service_id, service_type, date, times, duration_hours) and a `roster` (musicians with
assigned_service_ids and flags: principal, lead, quartet, electronic, substitute, doubles, vacation_eligible).

`service_counts` = count of each service_type across the schedule.

Per service base pay:
- Performance / Audit / Sound Check (1hr/2hr) = flat `service_rates[type]`.
- Rehearsal = `service_rates["Rehearsal"]` × max(duration_hours, 3.0)  — three-hour minimum call.

Per musician (sum over their assigned services):
1. **Base service pay** = sum of per-service amounts, by category (performance/audit/rehearsal/sound_check).
2. **Substitute uplift:** if the musician is a substitute, each Performance is paid **1.5×** the rate. Put
   the full 1.5× amount in the `performance` category, and put the extra 0.5× in a separate
   `substitute_adjustment` category. (Only Performance is uplifted — audit etc. stay flat.) The 1.5×
   performance amount is what premiums/doubles/vacation are computed on.
3. **Premiums** (`premium` category) = base service pay × Σ applicable pcts, which STACK additively:
   principal_or_lead 0.15 (if principal OR lead), quartet 0.15, electronic 0.25, concertmaster 0.20.
4. **Doubles** (`doubles` category) = base service pay × (first_double 0.25 + additional_double 0.10 ×
   (doubles − 1)), when doubles ≥ 1.
5. **Vacation** (`vacation` category, if vacation_eligible) = 0.04 × (base service pay + premiums +
   **doubles**). Doubles ARE part of the vacation base.
6. **Guarantee adjustment** (`guarantee_adjustment`) — ONLY for non-substitute ("guaranteed regular")
   players: if base service pay < `weekly_guarantee`, add (weekly_guarantee − base service pay). Compare
   against BASE service pay (pre-premium).

`category_totals` = sum each category across all musicians. `weekly_total` = sum of all categories.
`per_musician` ordered by musician_id; each `categories` object lists only NONZERO categories; `total` =
sum of that musician's categories. `top_paid_musician_id` = highest per-musician total — recompute this
AFTER the substitute uplift, which can change who is on top.

### CBA conflict flags
Sorted alphabetically, each listed once, from `conflict_thresholds` + `service_time_limits`:
- `REHEARSAL_EARLY_START` — a rehearsal starts before `rehearsal_earliest_start` (e.g. 09:00).
- `REHEARSAL_LATE_END` — a rehearsal ends after `rehearsal_latest_end` (e.g. 18:30).
- `SERVICE_OVER_TIME_LIMIT` — any service's duration exceeds `service_time_limits[type]`.
- `SOUND_CHECK_DURATION_MISMATCH` — a sound check's duration != its declared time limit.

### PITFALLS — payroll (all observed as real misses)
- Forgetting the substitute 1.5× uplift and the `substitute_adjustment` category → understates performance,
  premium, doubles, vacation, weekly_total, and can pick the wrong top-paid musician.
- Excluding doubles from the vacation base → vacation low for musicians with doubles.
- Rounding half-even/truncation → 1-cent misses on guarantee and vacation; use round-half-up.

## Suggested workflow

1. Read the three payload files. List the required output keys and each field's format from the template.
2. Map the request_memo to a task type (branch close / regional / comp summary / comp forecast / payroll).
3. Pull only the allowed endpoints; read the relevant rate-book `business_rules`.
4. Compute in python from full precision; apply formulas above; treat counts as period averages.
5. Round per the template (currency 2dp, ratios 4dp fraction, half-up), order/sort as specified.
6. Self-check the high-error fields: per-headcount denominators (avg), "largest growth" (rate),
   rank scope (region vs company), substitute uplift, vacation base, combined-overscale title suppression.
7. Emit exactly the template's keys — no extras, no omissions.
