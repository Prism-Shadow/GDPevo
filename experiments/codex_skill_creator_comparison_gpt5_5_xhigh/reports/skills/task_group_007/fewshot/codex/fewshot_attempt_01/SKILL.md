---
name: northwind-erp-desk
description: Solve Northwind ERP memo-and-template tasks from live ERP data, including order release, mixed-warehouse allocation, replenishment planning, supplier incident scorecards, and supplier quality controls. Use when a task references the Northwind ERP API, staged payload files, or an answer template and requires strict JSON output.
---

# Northwind ERP Desk

## Workflow

1. Read the memo, payload files, and answer template first.
2. Identify the task family and the governing window, wave, BOMs, orders, or supplier list.
3. Query only the live ERP records needed for that family.
4. Compute the requested fields from current records, not cached snapshots.
5. Emit JSON that matches the template exactly.

## Shared Calculations

- Use `effective available = on_hand - reserved - quarantined - safety_stock`.
- Use `shipping weight = sum(line quantity * product weight_lb)`.
- Treat open or confirmed POs with `eta` on or before the needed date as timely coverage when the template asks for it.
- Use `open_date` through `analysis_date` for open incidents, and `open_date` through `close_date` for closed incidents.
- Round currency and percentages exactly to the precision in the template.

## Task Families

### Order release

- Classify each order from customer, product, inventory, warehouse, and shipping quote data.
- Derive customer exception states from account and risk fields.
- Sort order records by `order_id` and sort SKU lists ascending.

### Mixed-warehouse allocation

- Compute line-level effective availability at the requested warehouse.
- Use `ship` when the requested warehouse can clear the line.
- Use `transfer` when another warehouse can cover the uncovered quantity without protected stock.
- Use `backorder` when effective stock cannot clear the line.
- Use `manual_review` when account, risk, or product status blocks automatic release.
- Keep blocked orders separate from line-only product exceptions.

### Replenishment planning

- Sum component demand across all target builds.
- Reduce the gap with timely same-warehouse POs before planning purchases.
- Use transfers only from usable effective stock at source warehouses.
- Exclude components that are already covered, overstocked, or fully covered by timely POs.
- Follow the template's sorting for components, transfer requests, purchases, and exclusions.

### Supplier incident scorecards

- Filter incidents by the requested window, inclusive.
- Aggregate by supplier using counts, percentages, costs, durations, open counts, and severe counts.
- Apply the supplied recommendation policy in precedence order.
- Build escalation lists only from suppliers whose final code is escalation.

### Supplier quality controls

- Combine recent incidents, supplier quality status, and open or confirmed POs.
- Hold POs for suppliers that must freeze replenishment or require buyer review.
- Release only suppliers whose final decision is monitor-only.

## Output Checks

- Match the template keys exactly.
- Do not add narration, markdown fences, or helper fields.
- Sort all lists exactly as requested.
- Recheck ID lists for ordering and deduplication.
- See [Northwind ERP reference](references/northwind_erp.md) for the live API map and task-specific formulas.
