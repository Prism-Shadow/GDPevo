# train_003 Notes

## English

This task belongs to `task_group_007` for scenario `SCN_007_erp_inventory_order_fulfillment`, using source examples `E001`, `E002`, and especially `E003`. The assigned brief is a Q1 supplier incident scorecard for Northwind Components. The shared generated environment under `task_group/task_group_007/env/` supplies the public ERP API and generated incident and supplier records. The task-local payloads are `input/payloads/q1_scorecard_request.json` and `input/payloads/answer_template.json`.

The solver-visible request asks for a Q1 2026 scorecard using the shared API, not the hidden environment files. The intended work is to query `/incidents?start=2026-01-01&end=2026-03-31` and `/suppliers`, aggregate incidents by `supplier_id`, join supplier names and `quality_status`, and return the structured JSON shape in the template. The date filter is on `open_date`, inclusive. The filtered population has 38 incidents and 12 suppliers with at least one incident.

Material map: `/incidents` provides `incident_type`, `supplier_id`, `open_date`, `close_date`, `status`, `severity`, and `resolution_cost`; `/suppliers` provides supplier names and quality statuses used by the recommendation policy. `q1_scorecard_request.json` fixes the analysis window, duration treatment for open incidents, rounding precision, severe severity values, row ordering, escalation ordering, and controlled recommendation policy. `answer_template.json` defines the output contract without exposing answers.

The standard answer filters incidents opened from 2026-01-01 through 2026-03-31. Duration is calendar days from `open_date` to `close_date`; open incidents use the explicit analysis date 2026-03-31. Percentages use the filtered 38-incident denominator, rounded to one decimal. Costs are rounded to cents and average durations to two decimals. Rows are sorted by supplier id. Recommendation codes use the policy precedence: `ESCALATE_SUPPLIER`, then `PROCESS_REVIEW`, then `WATCHLIST`, then `MONITOR`.

The eight exact-match scoring points are: `SP001` analysis window and summary totals, weight 2; `SP002` supplier set, names, counts, and percentages, weight 3; `SP003` supplier costs and highest-cost supplier, weight 2; `SP004` average duration by supplier, weight 2; `SP005` RMA and work-order split, weight 2; `SP006` open and severe counts, weight 1; `SP007` controlled recommendation codes, weight 3; `SP008` escalation ordering and highest-share supplier, weight 2. These points emphasize business aggregates rather than formatting or free-form rationale.

Likely model pitfalls include using all 2026 incidents rather than Q1, filtering on `close_date` instead of `open_date`, using each supplier's own count as the percentage denominator, excluding open incidents from duration, confusing RMA with work orders, treating supplier display names as stable identifiers, or ignoring recommendation precedence. This train task anchors transferable incident-analytics conventions for later test tasks: filtered-population denominators, duration handling, incident-type separation, supplier-id joins, and controlled management recommendations.

Construction record: authored by task-builder subagent `train_003` on 2026-06-01. Created files for prompt, request payload, answer template, answer, evaluator, and notes. No shared environment, task-group metadata, calibration, seed scenario, or other task folders were edited.

