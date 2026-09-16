---
name: northwind-erp
description: "Northwind Components ERP operations for supply-chain decision tasks. Use when the task involves dispatch control (expedite queues), multi-warehouse allocation, kit-build replenishment planning, supplier quality incident scorecards, or procurement quality-control reviews against the Northwind ERP REST API. The skill covers inventory classification, customer exception mapping, decision matrices, shipping quotes, BOM-based component planning, supplier recommendation policies, and purchase-order hold/release logic. Trigger when the user references Northwind Components, Northwind ERP, order waves, expedite queues, allocation desks, replenishment desks, supplier scorecards, procurement control, or any operational decision file using ERP live records."
license: MIT
compatibility: designed for deepagents-code
---

# Northwind ERP Operations

Use the shared Northwind Components REST API to prepare operational decisions for supply-chain desks. The API is read-only and requires no authentication.

## Quick Start

1. Read the task prompt and any payload files (memos, answer templates, request JSON).
2. Identify the base URL (`<TASK_ENV_BASE_URL>`, typically `http://task-env:9007`).
3. Fetch the relevant API collections — prefer full-list endpoints over individual lookups.
4. Cross-reference live API data against the task memo to build the answer.
5. Return only the JSON object matching the provided answer template.

## API Reference

Full endpoint documentation, field definitions, and data-model relationships are in [references/api_reference.md](references/api_reference.md). Load it when the task involves any ERP endpoint you have not already memorized.

## Operational Patterns

Detailed reusable rules for inventory classification, customer exception mapping, decision matrices, replenishment planning, supplier scorecards, and procurement controls are in [references/operations_guide.md](references/operations_guide.md). Load it for any task that requires:

- **Expedite / dispatch control** — classify inventory status and customer exceptions to produce ship/hold/backorder/review decisions with shipping quotes.
- **Multi-warehouse allocation** — evaluate line-level availability across warehouses, generate transfer requests, and block orders with account or product issues.
- **Kit-build replenishment** — compute component requirements from BOMs, check timely POs, plan inter-warehouse transfers, and raise purchase requisitions.
- **Supplier incident scorecards** — filter incidents by date range, compute per-supplier metrics (cost, duration, RMA/WO split, severity), and apply recommendation policies.
- **Procurement quality control** — review targeted suppliers for recent quality risk, decide freeze/review/monitor, and identify POs to hold.

## Core Conventions

Every task follows these conventions unless the answer template says otherwise:

- **Effective available** = `on_hand` − `reserved` − `quarantined`. Whether `safety_stock` is subtracted depends on the desk; see the operations guide.
- **Currency** is always USD, rounded to exactly 2 decimal places.
- **Percentages** are rounded to 1 decimal place.
- **Duration averages** are rounded to 2 decimal places.
- **Lists** are sorted by the primary key ascending (order_id, supplier_id, SKU, etc.) unless otherwise specified.
- **Date ranges** are inclusive of both start and end dates.
- **JSON output** must match the answer template exactly — no extra keys, no missing keys.

## Workflow

### Step 1: Gather inputs

Read the task prompt and every payload file. Note the wave ID, target orders or suppliers, warehouse focus, date windows, and decision policies. Identify which API collections you need.

### Step 2: Pull live data

Fetch from the API in parallel where possible. Start with the broad collections:

```
curl -s <BASE>/orders | python3 -m json.tool
curl -s <BASE>/products | python3 -m json.tool
curl -s <BASE>/inventory | python3 -m json.tool
curl -s <BASE>/customers | python3 -m json.tool
curl -s <BASE>/suppliers | python3 -m json.tool
curl -s <BASE>/warehouses | python3 -m json.tool
curl -s <BASE>/incidents | python3 -m json.tool
curl -s <BASE>/purchase_orders | python3 -m json.tool
curl -s <BASE>/boms | python3 -m json.tool
```

Filter in memory to the relevant subset (by wave, order_id list, supplier_id list, date window, etc.).

### Step 3: Compute decisions

Apply the rules from the operations guide. For each entity (order, line, component, supplier), compute:

- Numeric values from live records (inventory positions, costs, dates).
- Classification enums by applying the decision rules in precedence order.
- Composite rollups (summaries, counts, blocked lists, sorted collections).

### Step 4: Request shipping quotes

For dispatch tasks, request `/shipping/quote` for each order. Use the order's `warehouse_id`, `destination_zip`, total line weight, and `shipping_speed`. Total weight = sum of `product.weight_lb × line.quantity` for each line on the order.

### Step 5: Build the answer JSON

Construct the JSON object exactly matching the answer template. Use a Python script or in-memory assembly. Validate:

- All required top-level keys are present.
- Every list is sorted by the specified key.
- Currency values have exactly 2 decimal places.
- No narrative text outside the JSON.

### Step 6: Validate and return

Before returning, spot-check:

- Numeric sums in the summary section match the detail rows.
- Enum values are from the allowed set.
- Sort order is correct everywhere.
- Blocked/manual-review lists are consistent with per-record decisions.

Return only the JSON. Do not include markdown fences, explanatory text, or commentary around the output.

## Task-Type Quick Reference

| Task type | Key collections | Decision output |
|-----------|----------------|-----------------|
| Expedite dispatch | orders, products, inventory, customers, warehouses, shipping | Per-order decisions with inventory status, customer exception, shipping quote |
| Allocation/transfer | orders, products, inventory, customers, warehouses | Per-line actions (ship/transfer/backorder/manual_review) with transfer requests |
| Replenishment | boms, products, inventory, purchase_orders, suppliers, warehouses | Component plan, transfer requests, purchase requisitions |
| Supplier scorecard | incidents, suppliers | Per-supplier metrics and recommendation codes |
| Procurement control | incidents, suppliers, purchase_orders, products | Per-supplier decisions with held PO lists |
