# Crescent Finance Ops Reporting Skill

Use the remote Finance Ops API from environment_access.md, not localhost. Fetch the endpoint family implied by the task: finance branch/period/account/record endpoints for branch or regional reporting, compensation rate-book/roster/scenario endpoints for compensation summaries and forecasts, and payroll rate-book/production endpoints for weekly payroll reviews.

Return exactly one JSON object matching the provided answer_template.json. Currency fields are rounded to 2 decimals. Percent, growth, ratio, and margin fields are rounded to 4 decimals. Sort stable ID lists ascending unless a rank field explicitly implies ranked order. Per-musician rows should be ordered by musician_id and conflict_flags alphabetically.

For finance tasks, map M1-M12 to FY2024 and M13-M24 to FY2025. Revenue is product_revenue plus service_revenue. COGS is direct_materials_cogs plus direct_labor_cogs. Gross margin is revenue minus COGS. SG&A is sales_sga plus admin_sga plus occupancy_sga. EBITDA is gross margin minus SG&A minus shared_service_allocations. Growth is (new-old)/old. ARPU and sales_per_labor_headcount are FY revenue divided by the matching FY operating totals. Rankings are descending, with rank 1 as highest.

For compensation tasks, join the rate book, rosters, and scenarios by ensemble_id and scenario_id. Compute quarter totals, pay-type totals, annual totals, largest pay type or largest growth pay type, combined overscale/title treatment counts, and partial-quarter counts from active roster records. Forecast years require applying scenario changes consistently before aggregating.

For payroll tasks, join production schedule, roster, and payroll rate book. Count services by normalized service type, compute category totals, weekly total, per-musician nonzero category totals, top-paid musician, doubles, substitute/electronic treatment, vacation, guarantee adjustments, and contract conflict flags from schedule timing and duration rules.

Avoid rounding intermediate values; round only final fields. Preserve exact enum strings and template keys. Do not include extra keys.
