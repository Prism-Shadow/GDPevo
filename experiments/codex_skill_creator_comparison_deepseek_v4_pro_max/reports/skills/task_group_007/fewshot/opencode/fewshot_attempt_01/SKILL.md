---
name: northwind-erp-desk
description: Solve Northwind Components operational desk tasks — expedite queues, replenishment planning, supplier scorecards, allocation decisions, and procurement quality reviews — using a shared ERP JSON API. Use this skill whenever the prompt mentions Northwind Components, Northwind ERP, a task-environment API at TASK_ENV_BASE_URL, or operational desk workflows like dispatch control, kit-run replenishment, supplier-quality review, allocation desk, or procurement-control decisions. Also trigger when the user talks about expedite queues, BOM kit builds, incident scorecards, mixed-warehouse transfer allocation, or supplier-quality hold review against a shared JSON API.
---

# Northwind ERP Operational Desk Skill

## Overview

This skill guides a Codex solver through Northwind Components operational desk tasks.
Five desk types appear in practice: expedite queue, kit-run replenishment, supplier
scorecard, allocation desk, and procurement quality review. Every task follows the
same core loop: read the local input payloads, inspect a shared ERP JSON API, apply
business rules from the task materials, and return strictly conformant JSON.

The API is a simple read-only REST service. Fetch wide, cross-reference locally,
and let the answer template drive every output decision.

## Immediate First Steps

When you receive a Northwind desk task, do these four things in your first turn:

1. Read the task prompt, the input memo, and the **answer template JSON**.
   The answer template is the authoritative schema. Every key, enum, sorting rule,
   and precision constraint in it is non-negotiable.

2. Call `GET <TASK_ENV_BASE_URL>/manifest` to confirm the available endpoints.
   The manifest lists every collection. If no `/manifest` endpoint responds, read
   [references/api_endpoints.md](references/api_endpoints.md) for the known catalog.

3. Fetch all top-level collections you might need in one parallel batch. It is
   always faster to fetch `/products`, `/orders`, `/customers`, `/inventory`,
   `/warehouses`, `/suppliers`, `/purchase_orders`, `/incidents`, and `/boms`
   upfront than to chase individual records one-by-one. Some tasks only need a
   subset; skip the endpoints the answer template never references.

4. After fetching, cross-reference the records that the memo names (order IDs,
   supplier IDs, BOM IDs) against the collections to build the local picture.

## The Answer Template Is the Contract

Every task includes a JSON file that defines exactly what the solver must return.
Treat it as a machine-readable spec with these conventions:

- **Sorting**: any list with an `ordering` field must be sorted exactly as stated
  (typically ascending by ID, then line number, then quantity descending). Do not
  assume default ordering.
- **Enums**: any field with `allowed_values` must use exactly those strings.
- **Currency**: fields with `precision: 2 decimal places` or `currency rounded to
  2 decimals` must be rounded to two decimal places with `round(..., 2)`.
- **Required keys**: do not omit keys listed under `required_keys` even when their
  value is zero, empty list, or null.
- **Null vs empty**: use `null` only when the schema explicitly allows it (e.g.,
  `"transfer_from": null`); otherwise use `[]` or `0`.

## Effective Available Stock

Several task types require a calculation of how much inventory is truly usable:

```
effective_available = on_hand - reserved - quarantined - normal_buffer
```

The inventory endpoint returns per-SKU, per-warehouse records. Look for `on_hand`,
`reserved`, `quarantined`, and `buffer` (or `normal_buffer`) fields. Use these
exact field names from the live API; do not guess.

A negative effective-available value means the warehouse is short: the line cannot
be fully cleared from stock at that location.

Protected stock (`reserved`, `quarantined`, `buffer`) is never eligible for
transfers either: when sourcing from another warehouse for a transfer, use only
the non-protected portion.

## Shipping Quotes

When a task asks for shipping quotes, call the endpoint per order (or per line,
depending on the template):

```
GET <TASK_ENV_BASE_URL>/shipping/quote?order_id=SO-XXXXX
```

The response includes `zone_distance`, `service_days`, and `total_cost_usd`.
Round `total_cost_usd` to two decimals.

If the task says a quote is needed "even if the decision is not release," still
fetch it — shipping cost is independent of the fulfillment outcome.

## Cross-Referencing Patterns

These are the join patterns the five desk types use. Follow the one that matches
the task, not all of them at once.

**Orders → Customers**: Each order has a `customer_id`. Look up the customer in
`/customers` to get `account_status`, `fraud_flag`, `credit_hold`, and any
review-required flags. These drive `customer_exception` and `manual_review`
decisions.

**Orders → Inventory → Warehouses**: Each order line has a `sku` and typically
a `warehouse_id` or the order-level `requested_warehouse`. Look up the inventory
record for that SKU at that warehouse, compute effective available stock, and
compare against the requested quantity.

**BOMs → Products → Inventory**: Fetch the BOM by ID. Each BOM entry lists
component SKUs and quantities per kit. Multiply by the target build quantity to
get `total_required`. Cross-reference inventory at the planning warehouse, then
check purchase orders for timely coverage.

**Incidents → Suppliers**: Filter incidents by `open_date` range, then group by
`supplier_id`. For each supplier, compute counts, sums, and averages as the
template requires. The incidents endpoint returns `severity`, `type` (e.g., `RMA`,
`WORK_ORDER`), `resolution_cost`, `open_date`, `close_date`, supplier reference.

**Purchase Orders → Suppliers + Inventory**: POs have `supplier_id`, `sku`,
`warehouse_id`, `status` (`open`, `confirmed`, `received`, `cancelled`), `quantity`,
`delivery_date`, `unit_cost`. Only `open` and `confirmed` POs count toward
timely coverage. Check `delivery_date` against the target build or review date
to decide if coverage is "timely."

## Decision Rules

The business rules for classification and decision-making are always stated in
the task's own input materials, not in this skill. The answer template's enums
tell you what the options are; the memo or policy document tells you when to use
each one.

Read the task materials carefully and apply the stated conditions literally.
Common patterns from the few-shot evidence include (but are not limited to):

- Account-blocked customers prevent automatic release regardless of stock.
- Fraud-watch customers stop all lines on the order, not just one.
- Inactive products stop the line even when stock is available.
- Shortage is a line-level problem; the decision may be per-line.
- When a line has both an account problem and a stock problem, the account problem
  takes precedence for the `primary_reason` (the order stays blocked, not backordered).
- Recommendation policies with cascading precedence (like ESCALATE_SUPPLIER before
  PROCESS_REVIEW before WATCHLIST before MONITOR) mean: check the highest-precedence
  conditions first; if they match, assign that code and stop.

## Summary Sections

Most answer templates end with a `summary` object. Compute it from the records
you have already classified, not by separate API calls:

- Counts: iterate the decision list and tally.
- Total costs: sum from the per-record values you already computed.
- Lists of IDs: collect from the records, sort ascending, deduplicate.

## Output Procedure

1. Build the output JSON in memory. Do not write intermediate files unless you
   need scratch space.
2. Verify against the answer template one section at a time: top-level keys,
   then list ordering, then field types, then enum values, then precision.
3. Keep currency values as raw numbers (e.g., `12345.67`, not `"$16,412.62"`).
4. Return only the JSON. No markdown fences, no narrative text, no trailing
   explanation — the answer template says what to return.

## Common Pitfalls

- **Fetching one record at a time**: Always fetch the whole collection first,
  then filter locally. The API returns full arrays from list endpoints.
- **Missing the manifest step**: If you skip `/manifest` and guess endpoints,
  you may miss an endpoint the task expects. The `/shipping/quote` endpoint
  in particular is sometimes needed.
- **Sorting bugs**: Every list in the answer template has an explicit sort rule.
  Apply it even when the natural API order happens to match — the evaluator checks.
- **Rounding prematurely**: Carry full precision through intermediate calculations,
  round only the final value in the output.
- **Wrong enum casing**: `"ship_now"` vs `"ShipNow"` vs `"SHIP_NOW"` — copy
  the exact string from the answer template's `allowed_values`.
- **Omitting zero-value keys**: If `required_keys` includes `shortage_skus`,
  it must be present as `[]` even when empty.
- **Mixing up order-level and line-level decisions**: Some tasks decide per
  order, others per line. The answer template's record structure tells you which.
- **Treating all inventory as available**: Always subtract reserved, quarantined,
  and buffer before comparing against demand.

## Reference Files

- [references/api_endpoints.md](references/api_endpoints.md) — Full endpoint catalog
  with response shapes, field names, and query parameters. Read this if `/manifest`
  is unavailable or to confirm field names during cross-referencing.
