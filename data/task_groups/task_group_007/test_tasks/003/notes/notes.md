# test_003 Notes

## English

### Data and source lineage

This task belongs to `task_group_007`, scenario `SCN_007_erp_inventory_order_fulfillment`, using source examples `E001`, `E002`, and `E003`. It implements the incident analytics operation family described in `scratch/task_group_design.md` and the assigned `test_003` brief in `scratch/task_builder_briefs.md`.

The task uses the shared Northwind Components ERP environment under `task_group/task_group_007/env/`. Solvers should access only the public API, especially `/incidents` and `/suppliers`; they should not inspect environment source files. Task-local visible payloads are `input/payloads/full_year_supplier_incident_request.json` and `input/payloads/answer_template.json`.

### Task definition and material map

The business request is an annual supplier-quality and operations review for incidents opened from `2025-01-01` through `2025-12-31`, inclusive. The expected output is a structured JSON scorecard with the analysis window, overall summary, supplier-level metrics, supplier ranking, highest-cost and highest-share suppliers, and controlled management action sets.

`full_year_supplier_incident_request.json` defines the date window, use of `open_date` for filtering, the analysis date for open incidents, percentage denominators, numeric precision, severe severity values, ranking order, and recommendation-code policy. `answer_template.json` defines the required schema, enum values, rounding rules, and stable ordering requirements.

### Solution and evaluation basis

The standard answer filters incidents by `open_date` in calendar year 2025. It then joins supplier names and `quality_status` from `/suppliers`. Duration is calendar days from `open_date` to `close_date` for closed incidents; for open incidents it is calendar days from `open_date` to `2025-12-31`. Percentages use the filtered full-year population or filtered full-year total cost, not all generated incidents.

The answer contains 152 filtered incidents across 12 suppliers, total resolution cost `545296.07`, 71 RMA incidents, 81 WORK_ORDER incidents, overall RMA average duration `79.10` days, and overall WORK_ORDER average duration `69.16` days. Supplier rows are ordered by `supplier_id`; `supplier_ranking` is ordered by incident count descending, then total cost descending, then `supplier_id` ascending. Management recommendations use the request policy precedence exactly.

The evaluator has 8 exact-match scoring points with raw weights:

- `SP001` weight 2: correct analysis window and full-year summary totals.
- `SP002` weight 3: correct supplier set, names, quality statuses, incident counts, and incident percentages.
- `SP003` weight 2: correct supplier ranking, top-five ranking, and highest-share supplier.
- `SP004` weight 2: correct supplier total costs, cost percentages, and highest-cost supplier.
- `SP005` weight 3: correct overall and supplier RMA/work-order duration averages.
- `SP006` weight 2: correct RMA, work-order, open, severe, and critical-RMA counts by supplier.
- `SP007` weight 3: correct controlled management recommendation code by supplier.
- `SP008` weight 2: correct controlled management action supplier sets.

Likely pitfalls include using all 212 generated incidents instead of the 2025 population, filtering by `close_date`, using the whole dataset as the incident-percentage denominator, treating open incidents as zero-duration, failing to separate RMA from WORK_ORDER duration averages, and applying management recommendation rules without precedence.

### Transfer design

The primary train anchor is `train_003`, which establishes incident filtering, supplier aggregation, filtered-population denominators, duration rules, severe/open counts, ranking, and controlled recommendation codes. The second anchor is `train_005`, which connects supplier incident patterns to procurement-quality hold decisions and replenishment-freeze style recommendations. This test changes the date window to a complete calendar year, increases the filtered population, adds cost-share percentages, and separates per-supplier RMA and WORK_ORDER duration averages.

Transfer-dependent scoring points are `SP002`, `SP004`, `SP005`, `SP006`, and `SP007`, because they depend on the same aggregation, duration, incident-type separation, severity, quality-status, and recommendation-precedence conventions learned from the train tasks. `SP003` and `SP008` also benefit from train experience but require task-specific ranking and policy application over the larger full-year population.

### Construction record

Author: task-builder subagent `test_003`. Created: 2026-06-01. Updated: 2026-06-01. Major changes: created solver prompt, request payload, answer template, standard answer, exact-match evaluator, and notes for the full-year supplier incident analysis task.

