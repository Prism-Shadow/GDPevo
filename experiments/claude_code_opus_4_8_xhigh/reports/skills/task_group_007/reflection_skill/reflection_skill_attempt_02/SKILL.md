---
name: northwind-erp-ops
description: >-
  Solve Northwind Components ERP operations tasks that require querying the live read-only ERP
  HTTP API and returning a strict JSON decision file. Use this whenever a task references the
  Northwind ERP, a wave (e.g. TRAIN_EXPEDITE_A, TRAIN_TRANSFER_B), an expedite/dispatch queue,
  a kit/BOM replenishment run, a supplier incident scorecard, a mixed-warehouse allocation
  decision, a procurement quality / replenishment-control review, or any prompt that hands you
  a memo plus an answer_template.json and asks for inventory status, fulfillment decisions,
  transfer/purchase requisitions, supplier recommendation codes, or PO holds. Apply this skill
  even when the task only mentions "effective available stock", "safety stock", "quality_hold",
  "incidents", "shipping quote", or "backorder" without naming the wave explicitly.
---

# Northwind Components ERP Operations

You are answering operations tasks against a shared, read-only **Northwind Components ERP API**.
Each task hands you (1) a short memo/payload and (2) an `answer_template.json` describing the
required JSON output. Your job is to query the live API, apply the business rules, and emit JSON
that exactly matches the template. The memo and any cached snapshots may be stale — the **live
API is always the source of truth**.

This skill encodes rules that were validated by reflecting on solved tasks. The pitfalls listed
are real mistakes that produce wrong answers; the "why" is given so you can adapt to new but
similar tasks rather than pattern-matching the examples.

## Golden rules (read first)

1. **The API is ground truth.** Reconcile every memo claim (PO ids, quantities, statuses, names)
   against live records. If the memo and the API disagree, trust the API.
2. **Match the template exactly.** Use only the keys, enum values, ordering, and rounding the
   `answer_template.json` specifies. Emit JSON only — no prose, no markdown fences.
3. **Effective available stock is the universal inventory primitive.** Almost every task depends
   on it, and the single most common error is computing it or its thresholds wrong. See below.
4. **Solve only the scope you are given.** If a memo lists specific order_ids / supplier_ids /
   BOMs, operate on exactly those — not the whole wave or the whole collection.

## API quick reference

Base URL: **`http://127.0.0.1:8015`** (use this exact one; ignore any other port a task or memo
mentions, e.g. 8007 — always use 8015). All GET, JSON, read-only. Filters are exact string match;
omitting a filter returns everything.

| Endpoint | Use |
|----------|-----|
| `GET /health` | manifest + record counts (sanity / `generation_timestamp` = plan/as-of date) |
| `GET /products` , `/products/<sku>` | `active`, `safety_stock`, `overstock_threshold`, `unit_cost`, `supplier_id`, `weight_lb` |
| `GET /suppliers` | `supplier_id`, `name`, `quality_status` (approved / watch / quality_hold) |
| `GET /customers` , `/customers/<id>` | `account_status` (active / review_required / blocked), `risk_flag` (none / credit_watch / fraud_watch) |
| `GET /warehouses` | warehouse list |
| `GET /inventory?warehouse_id=&sku=` | `on_hand`, `reserved`, `quarantined` per (warehouse, sku) |
| `GET /purchase_orders?supplier_id=&sku=&status=` | `po_id`, `sku`, `status`, `warehouse_id`, `eta`, `quantity` |
| `GET /orders?wave=&required_date=&customer_id=` , `/orders/<id>` | order header + `lines[]` (line_id, sku, quantity), `warehouse_id`, `customer_id`, `destination_zip`, `shipping_speed` |
| `GET /boms` , `/boms/<id>` | `kit_name`/`name`, `warehouse_id`, `components[]` (sku, quantity_per_kit) |
| `GET /incidents?start=&end=&supplier_id=&sku=&incident_type=&status=` | quality incidents |
| `GET /shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=` | parcel quote |

`/incidents` `start`/`end` filter on **`open_date`**, inclusive, by ISO-string compare. Pass the
window exactly as given (e.g. `start=2026-01-01&end=2026-03-31`) and let the server filter; do not
re-filter client-side except to bucket per supplier/type.

`/shipping/quote` returns the cost already computed and rounded: read `zone_distance`,
`service_days`, and `total_cost` straight from the response. Quote **weight = sum over ALL order
lines of `quantity * product.weight_lb`**, and **speed = the order's own `shipping_speed`** (unless
a memo explicitly overrides it). A memo note like "quote overnight" is usually already the order's
speed — verify against the order record rather than assuming.

## Effective available stock — the core formula

For a (warehouse, sku):

```
eff_avail = on_hand - reserved - quarantined - safety_stock
```

`reserved`, `quarantined`, and the `safety_stock` buffer are **all protected** and never freely
allocatable. `eff_avail` can be negative; report it as-is when the template asks for it
(`requested_effective_available`, `target_effective_available`) — do not floor at 0.

**Per-line inventory classification** (compare a line's order `quantity` against `eff_avail`):

| Status | Condition |
|--------|-----------|
| `shortage` | `eff_avail < quantity` |
| `low_stock` | `eff_avail >= quantity` AND `eff_avail < safety_stock` |
| `ready` | `eff_avail >= quantity` AND `eff_avail >= safety_stock` |

> Pitfall (high impact): do **not** decide shortage with a pre-safety number like
> `on_hand - reserved - quarantined >= quantity`. The cutoff between shortage and low_stock is
> `eff_avail` (safety already subtracted) vs the line quantity. A line you can only fill by eating
> into safety stock is a **shortage**, not low_stock. `low_stock` is the narrow band where you can
> fill the line AND keep a non-negative buffer, but the buffer itself is below the safety target
> (`eff_avail < safety_stock`). Getting this wrong cascades into the wrong status, decision,
> next_action, and every summary rollup.

A SKU is **inactive** when `product.active == false`.

## Task families

There are five recurring task families. Identify which one from the template's top-level keys and
the memo, then open the matching playbook in `references/playbooks.md` for the exact decision
tables, precedence, field definitions, and summary rollups:

| If the template / memo is about... | Family | Key output keys |
|------------------------------------|--------|-----------------|
| expedite/dispatch queue per order, release/hold/backorder | **Expedite queue** | `records[]`, `inventory_status`, `final_decision`, `next_action`, `shipping_quote`, `summary` |
| kit/BOM build, replenishment, transfers + purchase reqs | **Kit replenishment** | `component_plan[]`, `transfer_requests[]`, `purchase_requisitions[]`, `excluded_components[]` |
| Q1/quarter supplier incident scorecard | **Incident scorecard** | `supplier_scorecard[]`, `recommendation_code`, `top_escalation_suppliers` |
| mixed-warehouse allocation, line-level ship/transfer/backorder | **Allocation desk** | `line_actions[]`, `transfer_requests[]`, `blocked_orders`, `order_rollup` |
| procurement quality / replenishment-control, freeze/hold POs | **Procurement quality** | `supplier_decisions[]`, `decision`, `held_po_ids`, `release_supplier_ids` |

Read `references/playbooks.md` for the family you are solving. The cross-cutting rules below apply
to all families.

## Cross-cutting rules

### Customer / account precedence
When a customer status gates an order, evaluate top-down (first match wins):
`account_status == blocked` → `risk_flag == fraud_watch` → `risk_flag == credit_watch` →
`account_status == review_required` → else none. Account/risk gates outrank inventory: a blocked,
fraud, credit, or review-required order does not ship on stock alone.

> Pitfall: when an order is gated at the account/risk level, that gate applies to **every line**
> of the order, and the order goes on the blocked/manual-review list — regardless of each line's
> stock or product status.

### Inactive product vs account review (next_action / reason precedence)
If a line needs `manual_review` for more than one reason, the reported reason/next_action follows a
precedence. **Account review_required outranks inactive-product escalation.**

> Pitfall: a line with both an inactive SKU and a `review_required` customer reports the
> account-review action (`send_account_review`), not the product-master action
> (`escalate_product_master`). The product-master path only owns the line when there is no
> higher account/risk reason.

### Severe-incident threshold (reused across families)
"Severe" = `severity in {high, critical}`. A recurring threshold across this environment is
**`severe_or_critical_count >= 2`**. Notably, supplier `quality_status == watch` by itself, or a
single lone `critical` incident, does **not** by itself escalate a supplier — use the count
threshold the task specifies, not the bare status.

### JSON conventions
- **Sorting:** obey the template's stated ordering precisely (by order_id, then line_id; by sku;
  by supplier_id; transfers often "sku asc, then quantity desc, then warehouse asc"). When a tie
  remains, fall back to ascending id/string.
- **Money:** round to 2 decimals. `extended_cost = round(unit_cost * quantity, 2)` using the
  rounded `unit_cost`. Quote `total_cost` is already rounded.
- **Percentages / durations:** follow the stated precision (often 1 decimal for percent, 2 for
  durations). Durations are simple calendar-day differences (`close_date - open_date`, or
  `analysis_date - open_date` for still-open incidents), not business days.
- **Lists:** SKU/PO/id lists are sorted and usually de-duplicated (sets, not multisets) unless the
  template says otherwise. Per-SKU exception lists (e.g. `low_stock_skus`) are independent — fill
  them even when the order's overall status is something else.
- **`max N` caps:** when a field says "maximum N" (e.g. sample ids max 5), sort first, then take
  the first N.
- **Summary rollups** must be recomputed from your own records so counts/totals are internally
  consistent (decision_counts, *_order_ids, unit totals, costs). Double-check that every list and
  count agrees with the per-record decisions.

## Suggested workflow

1. `GET /health`; note `generation_timestamp` — it is typically the plan/as-of date.
2. Read the memo and `answer_template.json`; identify the task family and the exact scope
   (which orders / suppliers / BOMs / SKUs).
3. Pull master data once (`/products`, `/customers`, `/suppliers`, `/warehouses`) and build lookup
   maps; pull `/inventory`, `/orders`, `/purchase_orders`, `/boms`, `/incidents` as the family
   needs.
4. Reconcile memo references against live records.
5. Open `references/playbooks.md` for the family and apply its decision table line-by-line / SKU-by-
   SKU / supplier-by-supplier.
6. Build sorted records, then compute every summary rollup from those records.
7. Validate against the template: keys present, enums valid, ordering correct, money rounded,
   caps applied. Emit JSON only.
