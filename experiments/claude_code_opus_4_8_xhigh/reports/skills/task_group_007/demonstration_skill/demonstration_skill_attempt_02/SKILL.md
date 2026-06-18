---
name: northwind-erp-ops
description: >-
  Solve Northwind Components ERP operations tasks by querying the live read-only ERP API and
  returning the exact JSON decision file the task asks for. Use this whenever a task references
  the Northwind ERP, a wave/expedite/allocation/transfer/replenishment/kit-build queue, a
  supplier incident or quality scorecard, a procurement/replenishment-control review, a shipping
  quote, or any prompt that hands you a memo/request payload plus an answer_template.json and asks
  for fulfillment, allocation, backorder, transfer, purchase-requisition, hold/freeze, or
  recommendation decisions. Trigger even if the task only mentions SKUs (NW-####), orders
  (SO-#####), suppliers (SUP-###), POs (PO-#####), incidents (INC-#####), warehouses
  (WH_NORTH/WH_CENTRAL/WH_WEST), BOMs, or "effective available" / "safety stock" inventory math.
---

# Northwind Components ERP Operations

You are an operations analyst for the **Northwind Components** ERP. Each task gives you a **memo / request payload** (the planning intent) plus an **`answer_template.json`** (the required output shape), and asks you to produce a structured JSON decision file. The memo is *planning input* — it can be stale or wrong. **The live ERP API is the source of truth. Always reconcile the memo against live records.**

## The single most important habit: read the payload first, then the template

Before computing anything, read the task's request/memo payload **and** `answer_template.json` end to end. They are not boilerplate — they carry the actual decision logic for *this* task:

- The payload often spells out the **exact policy**: date windows, precedence ladders, thresholds, recommendation codes, rounding, tie-break orderings, severity sets, "effective available" rules. **When a policy is given, follow it literally** — do not substitute remembered rules. (Example: an incident scorecard request may embed a full `recommendation_policy` with precedence + per-code conditions. Implement exactly those conditions in exactly that precedence.)
- The `answer_template.json` defines required keys, enum value sets, list orderings, rounding, and which fields are sets vs lists. Your output must match its shape precisely — same keys, same enums, same sort orders, nothing extra, nothing missing.
- When the payload is silent on a rule, fall back to the conventions in this skill (`references/business_rules.md`).

Echo back fixed values the template demands (e.g. a `wave_id` / `task_id` `required_value`) verbatim. Copy date windows from the payload into the output's `analysis_window` exactly.

## Use the live API (read-only)

Base URL: read `environment_access.md` in the task directory and use the **exact base URL it specifies** (currently `http://127.0.0.1:8015`). If task text mentions a different port (e.g. `8007`/`8015`), the access doc wins. Query with `curl` or Python `urllib`. All list endpoints return JSON arrays; single-record endpoints return objects; filters are exact string match; omitting a filter returns everything.

Hit `GET /health` first to see record counts and the data `generation_timestamp` (the "as-of" clock for the dataset). Then pull only what you need. See `references/api_guide.md` for every endpoint, its fields, and which one answers which question. Key points you will need constantly:

- **Inventory** rows (`/inventory?sku=&warehouse_id=`) carry `on_hand`, `reserved`, `quarantined`. **Products** (`/products/<sku>`) carry `active`, `safety_stock`, `overstock_threshold`, `unit_cost`, `supplier_id`, `weight_lb`.
- **Incidents** (`/incidents?start=&end=&supplier_id=&sku=&incident_type=&status=`): `start`/`end` filter on **`open_date`**, inclusive, as ISO-string comparison. Push the date window into the query — do not pull everything and filter loosely.
- **Shipping** (`/shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=`) **returns** `zone_distance`, `service_days`, and `total_cost` directly. Do not invent a formula — read these off the response. `weight_lb` is required; `speed` defaults to `ground`.

## The two formulas everything depends on

**Effective available stock (per SKU, per warehouse):**

```
effective_available = on_hand - reserved - quarantined - safety_stock
```

This is the universal definition of "freely usable" stock across every fulfillment/allocation/replenishment task. `reserved`, `quarantined`, and the product's `safety_stock` buffer are all protected and **never** count as available — it can go negative, and a negative value is meaningful (it quantifies the shortfall). Use the *same* formula for the requested warehouse, for transfer-source warehouses, and for kit-build target stock.

**Component requirement (kit builds):** `total_required = Σ over BOMs ( quantity_per_kit × build_quantity )`, summed across every BOM that contains the SKU.

## Pick the right playbook

Match the task to one of these and follow the corresponding SOP in `references/business_rules.md`. They share the formulas above but differ in structure:

| If the task is about… | Playbook | Output centers on |
|---|---|---|
| An expedite/dispatch queue: per-order release/hold/review/backorder + a shipping quote | **Expedite queue** | per-order `inventory_status`, `customer_exception`, `final_decision`, `next_action`, SKU exception lists, `shipping_quote` |
| Mixed-warehouse allocation: per-**line** ship/transfer/backorder/manual_review | **Line allocation** | per-line actions, transfer_requests, blocked_orders, order_rollup |
| Kit/BOM build replenishment: transfers + purchase requisitions to cover a build | **Kit replenishment** | component_plan, transfer_requests, purchase_requisitions, exclusions |
| Supplier incident scorecard over a date window | **Incident scorecard** | per-supplier counts/cost/duration/recommendation_code, escalation list |
| Procurement/replenishment quality-control review of named suppliers | **Replenishment control** | per-supplier decision (freeze/review/monitor) + held PO ids |

`references/business_rules.md` is the heart of this skill: it gives the decision ladder, thresholds, tie-breaks, exclusion rules, and rollup/summary math for each playbook. Read it for the playbook you're running.

## Decision precedence that holds across playbooks

These principles recur; internalize them:

1. **Account/customer risk gates everything.** A customer's `account_status` (`blocked` / `review_required`) or `risk_flag` (`fraud_watch` / `credit_watch`) stops automatic release regardless of stock. Resolve a *single* exception per customer by precedence: **blocked > review_required > fraud_watch > credit_watch > none** (account_status outranks risk_flag). In order-level tasks this makes the whole order manual_review / blocked, not just one line.
2. **Product status before stock.** An **inactive** product (`active == false`) is a master-data problem — flag it (manual_review / escalate / exclusion), don't try to ship or buy it.
3. **Stock math last.** Only after risk and product checks pass do you compare `effective_available` to demand to decide ship vs transfer vs backorder.
4. **Set vs list discipline.** Fields described as a set of ids/SKUs must be **deduplicated and sorted**; "sample" lists are capped (e.g. max 5) and sorted. Follow the template's stated ordering keys *exactly*, including multi-key sorts (e.g. "sku asc, then quantity desc, then warehouse asc").
5. **Money to 2 decimals; percentages and durations to the stated precision.** Round only at the field the template specifies. `extended_cost = round(unit_cost × quantity, 2)`. Summary totals are sums of the per-row rounded values unless told otherwise.

## Common pitfalls (read before you finalize)

- **Trusting the memo's numbers.** Memos list order/BOM ids and intent, but stock, statuses, costs, supplier links, and even which SKUs are inactive come from **live** records. Re-derive everything.
- **Forgetting `safety_stock` (and `quarantined`).** Many wrong answers compute `on_hand - reserved` only. The buffer and quarantine are protected — always subtract both, for sources too.
- **Letting effective stock go "to zero" instead of negative.** Keep the signed value; it's the backorder/purchase quantity driver and is often a required output field.
- **Re-implementing the shipping formula.** The quote endpoint returns the numbers; use them. The only judgment is *inputs*: warehouse = the order's warehouse, zip = the order's `destination_zip`, weight = total order weight `Σ(line.quantity × product.weight_lb)`, speed = what the memo/note/order requests (else default ground).
- **Misusing the incident date filter.** It keys on `open_date`. "Open at end of window" is a `status`/`close_date` question, not a filter question. Compute open-duration to the *analysis date*, closed-duration to *close_date*.
- **Wrong window per task.** A "Q1 scorecard" and a "recent quality review" use **different** date windows — take each from its own payload.
- **Over- or under-scoping `blocked_orders` / held lists.** Account/customer-risk stops are "blocked"; line-only product reviews are not. Held-PO rules can depend on the *decision*, not just the SKU — check the playbook.
- **Adding narrative.** Return only the JSON object the template defines. No prose, no extra keys.

## Workflow

1. Read `environment_access.md`, the request/memo payload, and `answer_template.json`. Note the fixed values, enums, orderings, rounding, and any embedded policy.
2. `GET /health`; identify the playbook from the table above.
3. Pull live records (orders/lines, customers, products, inventory, BOMs, POs, incidents, quotes) per `references/api_guide.md` — only what the playbook needs.
4. Apply the playbook's decision ladder from `references/business_rules.md`, using the effective-stock formula and the precedence rules above. Prefer writing a small Python script that fetches via `urllib` and computes deterministically over hand calculation.
5. Build the output to the template's exact shape: required keys, enum values, sorted/deduped lists, rounded money, and computed summary/rollup totals.
6. Self-check: every template key present and correctly typed? orderings applied? sets deduped? money rounded? fixed values echoed? summary counts equal to what the detail rows imply? Output is pure JSON, nothing else.
