---
name: northwind-erp
description: Deterministic helpers, API reference, and business rules for solving Northwind Components ERP tasks (expedite, allocation, replenishment, supplier quality, procurement control). Use this skill when the task input references a Northwind Components ERP API, a shared ERP environment, the Northwind Parcel shipping API, or task descriptions mentioning Northwind manufacturing/supply-chain workflows such as expedite queues, allocation waves, BOM-based kit replenishment, supplier incident scorecards, or procurement quality reviews.
---

# Northwind ERP Skill

## Quick Start

1. Read the task prompt and identify which Northwind workflow it follows
   (expedite, allocation, replenishment, scorecard, or procurement control).
2. Read the input payloads (memo JSON, answer template, etc.).
3. Open [references/api_reference.md](references/api_reference.md) for endpoint
   details if you need field names or parameter shapes.
4. Open [references/business_rules.md](references/business_rules.md) for the
   rule set applicable to the identified workflow.
5. Import [scripts/northwind_api.py](scripts/northwind_api.py) into your Python
   solver for deterministic HTTP, math, and classification helpers.

## Python Helper Script

**[scripts/northwind_api.py](scripts/northwind_api.py)** is the core reusable
module. It exposes:

- **HTTP**: `get_json`, `fetch_index`, `fetch_one`, `index_by`
- **Inventory**: `effective_available`, `usable_for_transfer`, `inventory_lookup`,
  `warehouse_effective_availabilities`
- **Products**: `product_weight`, `order_total_weight`
- **Customers**: `classify_customer`
- **Orders**: `classify_inventory_status`, `shortage_skus`, `inactive_skus`,
  `low_stock_skus`
- **Shipping**: `get_shipping_quote`, `shipping_quote_for_order`
- **Purchase Orders**: `timely_pos`, `timely_po_quantity`
- **Incidents**: `filter_incidents_by_date`, `incident_duration_days`,
  `group_incidents_by_supplier`
- **BOMs**: `bom_component_totals`
- **Decisions**: `expedite_decision`, `EXPEDITE_DECISION_TABLE`,
  `allocation_primary_reason`, `is_allocation_blocked`
- **Rounding**: `usd`, `pct1`, `dur`

Use the module by copying it into the solving workspace or running Python with
it on `sys.path`. Do not re-implement these functions from scratch.

### API Base URL

The task runner provides the API base URL as `<TASK_ENV_BASE_URL>` in the prompt
or as the `TASK_ENV_BASE_URL` environment variable. Pass it explicitly to every
function that accepts `base_url=`.

## Workflow Reference

Open **[references/business_rules.md](references/business_rules.md)** for the
full rule set. The key workflows covered:

### Expedite Queue

Given a list of order IDs, for each order:
- Fetch the order, its customer, products for each line SKU, and inventory at the order's warehouse.
- Classify inventory status (ready/shortage/etc.) and customer exception.
- Look up the (status, exception) pair in the decision table to get final_decision and next_action.
- Collect shortage_skus, inactive_skus, low_stock_skus.
- Get a shipping quote using the order's warehouse, destination_zip, total weight, and shipping_speed.
- Build summary: decision_counts, blocked/manual_review/backorder lists, total shipping cost.

### Kit Replenishment

Given one or more BOM IDs with build quantities at a target warehouse:
- Fetch BOMs, products, inventory (all warehouses), purchase orders.
- Compute total_required per SKU from BOM component quantities.
- Compute target_effective_available at the build warehouse.
- Identify the gap and cover it via timely POs, inter-warehouse transfers, then purchase requisitions.
- Exclude overstock and PO-covered components. Build transfer and purchase lists sorted per the answer template.

### Allocation Desk

Given a wave ID:
- Fetch all orders in that wave (filter by `wave` field), plus customers, products, inventory, and POs.
- For each line: check customer block status, product active status, then effective inventory.
- Decide ship/transfer/backorder/manual_review per line.
- Build transfer requests, blocked order list, order rollup, and summary counts.

### Supplier Incident Scorecard

Given a date window and recommendation policy:
- Fetch all incidents, filter to window.
- Group by supplier, compute counts, costs, durations, severity/status tallies.
- Apply recommendation code logic (ESCALATE_SUPPLIER → PROCESS_REVIEW → WATCHLIST → MONITOR).
- Identify top escalation suppliers, highest cost, highest share.

### Procurement Quality Review

Given target supplier IDs and an analysis window:
- Fetch incidents in window, filter to target suppliers.
- Compute per-supplier metrics and apply freeze/buyer_review/monitor_only decision logic.
- Collect held PO IDs from open/confirmed POs for freeze and buyer_review suppliers.
- Compute summary counts.

## Answer Templates

Every task provides an `answer_template.json` in `input/payloads/`. Parse it
cautiously: the template defines the required JSON shape, field types, enums,
and sort orders, but the solver must fill all fields with live ERP values. Do
not copy template field descriptions or example values into the answer.

Return only the complete JSON object matching the template. No narrative text
outside the JSON.

## Key Principles

- **Effective available only.** Never use `on_hand` directly for decisions.
  `effective_available = on_hand - reserved - quarantined`.
- **Customer exception dominates inventory.** A blocked or fraud-watch customer
  overrides stock availability. A review_required customer pushes to manual review.
- **Sorted lists.** All SKU lists, ID lists, and record arrays must be sorted as
  specified by the answer template (typically ascending by string key).
- **Currency precision.** All USD values rounded to 2 decimal places.
- **Use the live API only.** Do not read environment files, cached data, or
  embedded payload values for decisions that should come from the ERP.
- **One API call pattern.** Fetch full indexes once (`/products`, `/orders`,
  `/customers`, `/inventory`, `/suppliers`, `/purchase_orders`, `/incidents`,
  `/boms`) and filter in memory. Avoid per-ID loops that would call
  `/orders/{id}` for each order.
