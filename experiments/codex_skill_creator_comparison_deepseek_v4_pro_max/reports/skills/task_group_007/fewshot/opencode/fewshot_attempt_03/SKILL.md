---
name: northwind-erp-ops
description: Solve Northwind Components ERP operational desk tasks using the shared REST API and structured JSON answer templates. Use this skill whenever the task involves expedite-queue dispatch, production replenishment, supplier quality scorecards, allocation-desk transfer decisions, procurement quality controls, or any Northwind operational workflow that references a REST API at a task-environment base URL and expects a JSON output conforming to a provided template.
---

# Northwind ERP Operations Desk

This skill covers reusable patterns for solving Northwind Components operational desk tasks. Every task in this family follows the same skeleton: read a desk memo, query the shared REST API for live records, apply decision logic, and return a structured JSON response matching a supplied answer template.

## Core workflow

When a memo or prompt arrives, follow this sequence:

1. Read every payload file the prompt points to. These contain the task parameters (target wave, BOMs, supplier list, date ranges, decision policies).
2. Read the answer template. Note every required key, allowed enum value, ordering rule, and numeric precision constraint.
3. Query the API for live records. Pull fresh data for every entity the task touches -- orders, products, inventory, customers, suppliers, warehouses, POs, BOMs, incidents, shipping quotes. Do not reuse stale data from previous calls.
4. Compute derived values. Effective inventory is always `on_hand - reserved - quarantined`. Percentages and costs always round to the precision stated in the template.
5. Apply decision logic by mapping the live data to the enums in the template. Decision rules come from the memo or the template itself, not from any hardcoded policy outside the task.
6. Sort every list and every sub-list exactly as the template dictates (usually ascending by ID or SKU).
7. Return only the JSON. No narrative, no markdown fences, no commentary.

## API conventions

The API is a plain REST service reachable at the base URL supplied by the task runner as `<TASK_ENV_BASE_URL>`. All endpoints return JSON arrays or objects. There is no authentication, pagination, or filtering DSL -- pass query parameters as standard URL query strings.

The full endpoint catalog and field-level reference is in [references/api-catalog.md](references/api-catalog.md). Read it when you need field names, value sets, or to understand how entities relate.

Key behaviors to remember:

- **Single-record lookups** use `/endpoint/{id}` (e.g. `/orders/SO-70001`).
- **Filtering** uses query parameters on the collection endpoint (e.g. `/orders?wave=WAVE_ID`).
- **Effective inventory** for one SKU at one warehouse: fetch the matching inventory record and compute `on_hand - reserved - quarantined`. Reserve and quarantine are already committed; only the remainder is available for new allocations.
- **Shipping quotes** call `/shipping/quote` with `warehouse_id`, `destination_zip`, `weight_lb`, and optionally `shipping_speed`. The response includes `zone_distance`, `service_days`, and `total_cost_usd`.
- **Dates** in the API use ISO-8601 (`YYYY-MM-DD`). Compute date differences as calendar days. When a task supplies an analysis date, open incidents use `analysis_date - open_date` as their duration.

## Decision logic

Every operational desk task maps live ERP data to a fixed set of output enums. The mapping is task-specific and defined by the memo and template, but these patterns repeat:

- **Inventory classification** compares effective availability against demand. A SKU with effective inventory >= 0 and covering the requested quantity is ready; effective < 0 means shortage; an inactive product record (`active: false`) overrides availability calculations.
- **Customer risk** derives from `account_status` and `risk_flag` on the customer record. Blocked accounts, fraud watches, and credit watches typically force manual review or hold regardless of inventory.
- **Supplier quality decisions** apply a precedence chain (e.g. ESCALATE > PROCESS_REVIEW > WATCHLIST > MONITOR). Evaluate conditions top-down and assign the first matching code. Memo-provided policy documents define the exact thresholds.
- **Replenishment coverage** checks inventory first, then transfer availability from peer warehouses, then purchase orders (only open/confirmed, same-warehouse, with ETA no later than the target build date), then purchase requisitions as the residual.
- **Line-level allocation** processes order lines independently. Account/product risks block all lines on an order uniformly; inventory shortages affect individual lines.

For detailed reusable decision frameworks, see [references/decision-logic.md](references/decision-logic.md).

## Output discipline

- Match the answer template exactly. If a key is marked required, it must appear. If a field has a `required_value`, use that literal string.
- Sort every list as the template prescribes. The default sort is ascending by the primary identifier (order_id, sku, supplier_id, bom_id). Sub-lists within records (like SKU lists) also sort ascending.
- Currency fields round to 2 decimal places. Percentages round to 1 decimal place unless the template says otherwise. Duration fields round to 2 decimal places when specified.
- Empty lists use `[]`, not `null` and not omission.
- When the template defines an enum, use only those exact strings. Do not invent new values.
- When a field like `transfer_from` allows `null`, use JSON `null` (not the string `"null"`).

## Working efficiently

- Fetch collection endpoints once and filter client-side rather than making many single-record calls, unless the task explicitly has a small target set. For example, fetch all `/inventory` once and index by SKU+warehouse rather than requesting each SKU individually.
- Cross-reference entity data by their foreign keys: orders carry `customer_id`, `warehouse_id`, and `warehouse_id`+`destination_zip` for shipping; products carry `supplier_id`; inventory carries `warehouse_id`+`sku`.
- Verify every data assumption. If a task says an order is in a wave, confirm the order record's `wave` field matches before processing it.
