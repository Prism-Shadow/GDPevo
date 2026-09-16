# Reporting Playbook

## Data Sources

- `GET /api/manifest`: resolve public branch, ensemble, and production IDs when the memo uses names or when you need the full entity list.
- `GET /api/finance/branches`: map `branch_id` to branch and region names.
- `GET /api/finance/period-map`: map `M1` to `M24` to fiscal years and months.
- `GET /api/finance/accounts`: map account names to reporting categories and metric types.
- `GET /api/finance/records`: read per-branch account values by period.
- `GET /api/compensation/rate-book`: read current-year pay rules, quarter weeks, seniority bands, title premiums, and business rules.
- `GET /api/compensation/rosters`: read ensemble rosters, service weeks, title flags, overscale, and service-year data.
- `GET /api/compensation/scenarios`: read forecast growth assumptions by scenario and year horizon.
- `GET /api/payroll/rate-book`: read service rates, time limits, premium rules, and weekly guarantee rules.
- `GET /api/payroll/productions`: read production schedules and musician rosters.

## Finance Branch And Region Reports

- Build revenue from `product_revenue + service_revenue`.
- Build COGS from `direct_materials_cogs + direct_labor_cogs`.
- Build SG&A from `sales_sga + admin_sga + occupancy_sga`.
- Use `shared_service_allocations` for allocations.
- Compute `gross_margin = revenue - cogs`.
- Compute `ebitda = gross_margin - sga - allocations`.
- Use `M1-M12` for FY2024 and `M13-M24` for FY2025 unless the memo asks for another period slice.
- Use the requested `current_month` and `prior_month` directly for month-over-month variance.
- Compute branch revenue growth from FY2025 revenue versus FY2024 revenue.
- Keep `branch_ids` ascending by `branch_id`.
- Rank `region_context.ebitda_rank_desc` within the region's branch set.
- Rank `sales_growth_rank_desc` across the requested comparison set, usually all branches unless the memo narrows the scope.
- Derive `top_arpu_branch_id` from the highest FY2025 revenue divided by the FY2025 active_customers sum.
- Derive `sales_per_labor_headcount` from revenue divided by the matching labor_headcount sum for the requested fiscal year.
- Treat `region_context.fy2025_ebitda` as the sum of FY2025 branch EBITDA across the requested region.
- Derive `top_ebitda_branch_id` and `bottom_ebitda_branch_id` from the requested region or comparison set.
- Set `region_reconciliation_variance` to the signed difference between the region total and the sum of the included branch figures.

## Compensation Current-Year Reports

- Preserve the pay type order from the rate book.
- Use roster rows to build `quarter_totals`, `annual_pay_type_totals`, and `annual_total`.
- Count `combined_overscale_employee_count` as roster rows where `combined_overscale_includes_title` is true.
- Count `partial_quarter_employee_count` as roster rows whose `weeks_by_quarter` is not uniform.
- Use `weeks_by_quarter` directly; do not assume a fixed 13-week quarter when the roster says otherwise.
- If `combined_overscale_includes_title` is true, do not add a separate title premium for that employee.

## Compensation Forecast Reports

- Read the selected scenario by `scenario_id`.
- Apply the scenario's year-plus-one and year-plus-two growth rates to the current-year pay structure.
- Add one year of service for Year + 1 and two years for Year + 2 before assigning seniority bands.
- Apply the scenario's `title_pct_multiplier` to title premiums.
- Use the same roster flags and quarter-week logic as the current-year summary.
- Build `annual_totals`, `growth_rates`, `year_plus_2_quarter_totals`, `year_plus_2_pay_type_totals`, and `largest_growth_pay_type` from that adjusted forecast.

## Payroll Weekly Reports

- Count service types from the production schedule by `service_type`.
- Compute per-musician totals from the roster and schedule, then sort `per_musician` by `musician_id`.
- Include only nonzero category amounts in each musician's `categories` object.
- Use the payroll rate book for service rates, sound-check limits, premium percentages, vacation rules, and weekly guarantee rules.
- Derive `REHEARSAL_EARLY_START` and `REHEARSAL_LATE_END` from the rehearsal time thresholds.
- Derive `SOUND_CHECK_DURATION_MISMATCH` from the sound-check duration rules.
- Derive `SERVICE_OVER_TIME_LIMIT` from the service-time limits and any weekly cap implied by the production rules.
- Sort `conflict_flags` alphabetically.
- Set `top_paid_musician_id` to the musician with the highest total; break ties deterministically by `musician_id`.
- Set `weekly_total` to the common sum implied by the musician totals and the category totals.

## Output Discipline

- Match every enum label exactly.
- Keep nested object keys in the order used by the template or source ranking rule.
- Emit one JSON object only.
