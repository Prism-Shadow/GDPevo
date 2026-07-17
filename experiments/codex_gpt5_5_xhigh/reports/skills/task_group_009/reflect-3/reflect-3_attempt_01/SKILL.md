---
name: reflect-3
description: Use this skill for Crescent Finance Ops tasks that require calculating branch finance metrics, orchestra compensation, production payroll, or cross-domain business rollups from the remote Crescent API. Trigger whenever the user asks for Crescent Finance Ops analysis, fiscal period comparisons, compensation forecasts, production payroll totals, service-rule exceptions, or exact JSON answers over the Crescent data.
---

# Crescent Finance Ops Workflow

## Core Habit

Start by identifying the exact grain the user requested before doing arithmetic: company, region, branch, fiscal year, month/period, ensemble, quarter, scenario, production, service, or musician. Broad rollup dumps are risky. Produce the narrow requested answer and include only the supporting fields needed to make it auditable.

Use the remote Crescent Finance Ops API described in the environment access material. Do not assume there is a local task environment or local source files. Pull the manifest first when endpoint names are uncertain, then fetch only the business endpoints needed for the question.

## Endpoint Use

Use these data families:

- Finance: branches, period map, accounts, and records.
- Compensation: rate book, rosters, and scenarios.
- Payroll: rate book and productions.

Keep identifiers and display names together in outputs. For example, pair `branch_id` with `branch_name`, `region_id` with `region_name`, `ensemble_id` with `ensemble_name`, and `production_id` with `title`. This prevents correct numbers from becoming ambiguous.

## Finance Rules

Map fiscal periods through the period map rather than assuming calendar labels. In this data, periods are named `M1`, `M2`, etc.; fiscal year and month name come from the period map.

Use account categories from the accounts endpoint:

- Revenue = `product_revenue + service_revenue`.
- COGS = `direct_materials_cogs + direct_labor_cogs`.
- Gross profit = revenue minus COGS.
- SG&A = `sales_sga + admin_sga + occupancy_sga`.
- Operating income = gross profit minus SG&A minus `shared_service_allocations`.
- Gross margin = gross profit divided by revenue.
- Operating margin = operating income divided by revenue.

When aggregating, sum raw account values across the requested branches and periods first, then calculate derived metrics from those sums. Do not average branch margins unless the user explicitly asks for an unweighted average.

For growth and variance questions, report both absolute change and percentage change when useful:

```text
change = current - prior
change_pct = change / prior
```

## Compensation Rules

Calculate employee weekly compensation from the compensation rate book and roster rows:

```text
weekly_total =
  minimum_weekly_scale
  + seniority_weekly
  + title_premium_weekly
  + overscale_weekly
```

Important conventions:

- Seniority comes from the band containing the employee's years of service.
- Title premium is `minimum_weekly_scale * title_premium_pct[title]`.
- If `combined_overscale_includes_title` is true, add overscale but do not add a separate title premium.
- Use each employee's `weeks_by_quarter`; do not replace partial-quarter schedules with a fixed 13 weeks.
- Quarter compensation is `weekly_total * employee_weeks`, summed across employees.

For forecast scenarios:

- Year + 1 adds one year of service before selecting the seniority band.
- Year + 2 adds two years of service before selecting the seniority band.
- Apply the scenario's MWS, overscale, seniority, and title percentage changes for the relevant forecast year.
- Keep current totals, forecast totals, and deltas separate so the answer is easy to audit.

## Payroll Rules

Calculate production payroll from the payroll rate book and production roster/schedule:

- Rehearsal pay is hourly with a three-hour minimum call: `rehearsal_rate * max(duration_hours, 3)`.
- Performance, audit, and sound-check pay are per service.
- Premiums apply to the musician's base service pay before vacation.
- Doubles premium is 25% for the first extra instrument plus 10% for each additional extra instrument.
- Add electronic, principal-or-lead, and quartet premiums when their roster flags apply.
- Vacation is 4% of base service pay plus premiums when `vacation_eligible` is true.
- Weekly guarantee adjustment applies only to guaranteed regular players when base service pay is below the weekly guarantee. Treat substitutes as non-guaranteed.

Keep payroll components separate:

```text
total_pay =
  base_service_pay
  + premium_pay
  + vacation_pay
  + weekly_guarantee_adjustment
```

For service-rule exceptions, compare schedule rows to the rate-book limits:

- Flag services whose duration exceeds the service type's time limit.
- Flag rehearsals that start before the earliest allowed rehearsal start or end after the latest allowed rehearsal end.

## Output Shape

Match the user's requested schema exactly. If they ask for JSON, return plain JSON-compatible values with stable keys. Prefer a narrow object such as:

```json
{
  "branch_id": "BR-000",
  "branch_name": "Example",
  "fiscal_year": 2025,
  "revenue": 0.0,
  "operating_income": 0.0,
  "operating_margin": 0.0
}
```

For ranked results, use an array of row objects sorted in the requested direction. Include the rank only if helpful or requested.

For scalar answers, still include the unit or metric name unless the user explicitly asks for only the number.

## Rounding

Use raw values for intermediate calculations, then round final outputs:

- Currency and count-like totals: 2 decimal places.
- Ratios and percentages as decimal ratios: 4 decimal places.
- If presenting percentages as percent values, make the label clear and round to 2 decimal places.

Do not round inputs before summing. Do not mix decimal ratios and percent-formatted numbers under the same key.

## Pitfalls

- Do not answer with a broad dump when the task asks for a specific grain; graders often expect exact fields.
- Do not average precomputed margins across branches or regions unless asked.
- Do not infer fiscal year from `M` period numbers without the period map.
- Do not add a title premium when overscale already includes the title premium.
- Do not ignore partial-quarter employees in compensation rosters.
- Do not use a fixed 13-week quarter for every compensation employee.
- Do not forget forecast seniority year increments before choosing bands.
- Do not apply vacation before payroll premiums; vacation is on base plus premiums.
- Do not apply weekly guarantee adjustments to substitutes.
- Do not collapse IDs into names only; retain both for traceability.
