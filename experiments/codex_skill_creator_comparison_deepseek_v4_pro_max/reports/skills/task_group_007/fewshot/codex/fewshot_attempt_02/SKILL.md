---
name: northwind-erp
description: Supply-chain decision workflows for the Northwind Components ERP system including expedite dispatch, allocation desk transfers, kit replenishment planning, supplier incident scorecards, and procurement quality controls. Use when tasks involve Northwind ERP API calls to products, inventory, orders, customers, suppliers, purchase orders, BOMs, incidents, or shipping quote endpoints, or when filling structured JSON decision templates for supply-chain operations.
---

# Northwind ERP

Supply-chain decision automation for the Northwind Components ERP. Covers five
workflows: expedite dispatch, allocation transfers, kit replenishment, supplier
incident scorecards, and procurement quality controls.

## Workflow Selection

Identify the task type from the prompt and input materials:

1. **Expedite Dispatch** — a queue memo (JSON) with order IDs, operator notes,
   and an answer template requiring inventory status, customer exception,
   final decision, next action, SKU exception lists, and shipping quote
   per order. See [references/business_rules.md](references/business_rules.md)
   sections 1-3.

2. **Allocation Desk** — a transfer wave memo (markdown or JSON) with per-line
   warehouse actions (ship, transfer, backorder, manual review),
   transfer requests, and blocked orders. See
   [references/business_rules.md](references/business_rules.md) section 4.

3. **Kit Replenishment** — a production memo (JSON) with BOM targets,
   build quantities, and build dates. Requires component-level coverage,
   transfer requests, purchase requisitions, and exclusions. See
   [references/business_rules.md](references/business_rules.md) section 5.

4. **Supplier Incident Scorecard** — a scorecard request (JSON) with a date
   filter, recommendation policy, and an answer template requiring
   supplier-level aggregation, percentages, and recommendation codes. See
   [references/business_rules.md](references/business_rules.md) section 6.

5. **Procurement Quality Control** — a quality hold review memo (JSON) listing
   target supplier IDs with a recent-incident window and decision choices
   (freeze, buyer review, monitor). See
   [references/business_rules.md](references/business_rules.md) section 7.

## API Reference

See [references/api.md](references/api.md) for the full endpoint catalog,
response shapes, effective-available formula, timely-PO rules, shipping quote
parameters, and incident duration calculations.

## Core Patterns

### Before Solving Any Workflow

1. **Read the memo/payload and the answer template** from the task input.
   Understand what keys, enumerations, sort orders, and precision rules the
   template enforces.

2. **Fetch all live data in one batch**: call all list endpoints once and cache
   in Python dicts keyed by ID. These collections are small enough to hold
   entirely in memory.

3. **Fetch shipping quotes per order** only when the template requires them.
   Compute total order weight as the sum over all lines of quantity times
   product weight_lb, then call the shipping quote endpoint with the order's
   warehouse ID, destination ZIP, total weight, and shipping speed.

### Effective Available Formula

```
effective = on_hand - reserved - quarantined - safety_stock
```

Apply per SKU per warehouse. Safety stock comes from the product record.
See [references/api.md](references/api.md) for details.

### Customer Exception Precedence

For each order, look up the customer by ID. Apply in order:
1. fraud_watch if risk_flag matches
2. credit_watch if risk_flag matches
3. account_blocked if account_status is blocked
4. review_required if account_status requires review
5. none otherwise

Full decision tables in [references/business_rules.md](references/business_rules.md)
sections 2-4.

### Shipping Quote

```
GET /shipping/quote?warehouse_id=...&destination_zip=...&weight_lb=...&service=...
```

Compute total weight by summing line quantity times product weight_lb across
all lines. Use the order's shipping speed as the service parameter. Return
zone_distance (int), service_days (int), and total_cost (number, 2 decimals).

### Formatting Rules

- Currency values: round to 2 decimal places.
- Percentages: round to 1 decimal place.
- Durations in days: round to 2 decimal places.
- Sort all lists ascending by the primary key specified in the answer template.
- Output only the JSON object, no narrative text outside it.
- Derive all values from live API calls, never hard-code from memos.

## Reference Files

- [references/api.md](references/api.md) — Complete API endpoint catalog with
  field descriptions, response shapes, and parameter rules.
- [references/business_rules.md](references/business_rules.md) — Decision
  tables for all five workflows, inventory classification, customer exception
  rules, recommendation policies, and procurement control logic.
