---
name: northwind-erp-ops
description: >-
  Solve Northwind Components ERP operations tasks against the shared read-only ERP API: expedite/dispatch
  queue decisions, kit-build replenishment packages (BOMs, transfers, purchase requisitions), supplier
  incident scorecards, mixed-warehouse allocation/transfer decision files, and procurement quality-hold
  replenishment-control reviews. Use this whenever a task references the Northwind ERP, a wave of sales
  orders, inventory effective availability, safety stock, BOM kit builds, inter-warehouse transfers,
  purchase requisitions/orders, /incidents date windows, supplier quality_status, shipping quotes, or asks
  for a structured JSON decision file that conforms to an answer_template.json. Triggers even when the task
  only hands you a memo/payload plus an answer template and says "use the live ERP records."
---

# Northwind Components ERP Operations

You produce structured JSON decision files for Northwind Components operations desks by combining a local
memo/payload with **live** records from a shared read-only ERP HTTP API. The answers are graded field by
field against a hidden standard answer, so precision on formulas, precedence, exclusion rules, rounding,
sorting, and "max-N" caps matters more than narrative.

## The five task families

| Task signature in the prompt | Family | SOP file |
|---|---|---|
| "expedite queue", dispatch release/hold/review/backorder per order, shipping quote | Expedite/dispatch queue | `references/expedite_queue.md` |
| "kit build", BOM components, transfers + purchase requisitions, exclusions | Kit-build replenishment | `references/kit_replenishment.md` |
| "supplier incident scorecard", Q-window, recommendation codes | Incident scorecard | `references/incident_scorecard.md` |
| "allocation desk", classify every order line as ship/transfer/backorder/manual_review | Mixed-warehouse allocation | `references/allocation_transfer.md` |
| "replenishment-control decision", suppliers, freeze/buyer_review/monitor, hold POs | Quality-hold review | `references/quality_hold_review.md` |

Read the matching SOP file before computing — each encodes the exact, validated decision logic for that
family. The rest of this file is shared across all of them. **Always also read the task's own
`answer_template.json` and any policy block inside the payload** — when the payload spells out a rule
(precedence order, thresholds, severity sets, rounding, tie-breakers), the payload wins over any default
here.

## Using the ERP API (read these carefully)

Base URL is given in `environment_access.md` for the run. Use that exact base URL and **ignore any port
or `start the environment` instruction baked into a task prompt or memo** (memos often carry a stale
`http://127.0.0.1:8007` or a `setup.sh start` note from when they were authored — the API is already
running at the documented base URL). Everything is JSON over plain HTTP GET.

Endpoints and the fields that matter:

- `GET /health` — record counts + `generation_timestamp` (the data "as-of" date; good default for a
  `plan_date`/`analysis_date` if the task does not state one).
- `GET /products` / `GET /products/<sku>` — `active` (bool), `safety_stock`, `overstock_threshold`,
  `weight_lb`, `unit_cost`, `supplier_id`, `category`.
- `GET /customers` / `GET /customers/<id>` — `account_status` (e.g. active, review_required, blocked),
  `risk_flag` (e.g. none, credit_watch, fraud_watch), `tier`, `margin_band`.
- `GET /suppliers` — `quality_status` (approved, watch, quality_hold), `name`.
- `GET /warehouses` — `warehouse_id`, `zip`, `region`.
- `GET /inventory?warehouse_id=&sku=` — rows with `on_hand`, `reserved`, `quarantined`. One row per
  (sku, warehouse). A missing row means zero on hand at that warehouse.
- `GET /purchase_orders?supplier_id=&sku=&status=` — `po_id`, `status` (open, confirmed, received,
  cancelled), `sku`, `warehouse_id`, `eta`.
- `GET /orders?wave=&required_date=&customer_id=` and `GET /orders/<id>` — `customer_id`,
  `warehouse_id`, `destination_zip`, `shipping_speed`, `priority`, `required_date`, `lines`
  (each line: `line_id`, `sku`, `quantity`, `unit_price`).
- `GET /boms` / `GET /boms/<id>` — kit `name`, components with per-kit quantities.
- `GET /incidents?start=&end=&supplier_id=&sku=&incident_type=&status=` — `incident_id`, `supplier_id`,
  `sku`, `incident_type` (RMA, WORK_ORDER), `severity` (low, medium, high, critical), `status`
  (open, closed), `open_date`, `close_date`, `resolution_cost`, `root_cause`, `warehouse_id`.
- `GET /shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=` — returns `zone_distance`,
  `service_days`, `total_cost`, plus base_rate/fuel info. `speed` in {ground, two_day, overnight}.

### /incidents date-window semantics (do not get this wrong)
`start`/`end` filter on **`open_date`**, inclusive on both ends, as a **string compare on ISO dates**
(`start <= open_date <= end`). You can filter server-side with the query params or pull all and filter
locally — both give the same population. An incident belongs to the window by its `open_date` only;
`close_date` does not affect membership. Severity-based "severe" sets and `incident_type` are separate
axes — apply them after the date filter.

### Shipping quote usage
Compute the parcel weight as **`sum over ALL order lines of quantity * product.weight_lb`** (the whole
order, regardless of whether some lines are short or the order won't actually ship — the desks want the
quote either way). Call `/shipping/quote` with the order's own `warehouse_id`, its `destination_zip`, that
total `weight_lb`, and the `speed` the task tells you to use (usually the order's own `shipping_speed`;
some memos override per order, e.g. "quote overnight"). Take `zone_distance` and `service_days` straight
from the response and round `total_cost` to 2 decimals for `total_cost_usd`.

### Reconcile stale memos against live records
Memos and payloads are point-in-time notes and can be stale or partial. The live API is the source of
truth for account status, product status, inventory, POs, and incidents. The memo defines **scope**
(which orders/suppliers/BOMs/wave, target quantities, dates, the policy) — never invent records it does
not name, and never drop ones it does. When a memo's operator note and the live data disagree, follow the
live data and the policy, and still report the structured flags (e.g. report a SKU's low_stock status
even if the operator note only mentioned an account question).

## Effective availability — the single most important formula

Almost every inventory decision uses **effective available**, not gross on-hand. Reserved, quarantined,
and the product's safety-stock buffer are all *protected* and not freely usable for the wave:

```
gross     = on_hand - reserved - quarantined
effective = gross - safety_stock          # safety_stock defaults to 0 if null/missing
```

Per-line inventory classification is driven by **effective vs. the line quantity** (this is the most
common blind-phase error — do NOT use gross for the shortage test):

- `shortage`  ⟺  `effective < quantity`     (cannot fill without dipping into protected stock)
- `low_stock` ⟺  `effective >= quantity` AND `effective < safety_stock`
                 (fillable now, but the post-fill buffer is below the safety line)
- `ready`     ⟺  `effective >= quantity` AND `effective >= safety_stock`

A line can be a shortage even when gross on-hand looks like it could cover the quantity, because the
safety buffer is reserved. Report `requested_effective_available` / `target_effective_available` as the
**signed** effective number (it can be negative); do not floor it at 0 when reporting it. When you compute
a shortfall/gap to fill, treat negative effective as the literal signed driver: `gap = required - effective`
(a negative effective makes the gap larger), and `shippable_now = max(0, effective)`.

## Customer / account gating (expedite + allocation families)

Customer status gates the decision ahead of inventory. Evaluate most-severe-first and stop at the first
match:

1. `account_status == blocked`        → most severe (hold / reject)
2. `risk_flag == fraud_watch`         → hold / reject
3. `risk_flag == credit_watch`        → review
4. `account_status == review_required`→ review
5. otherwise                          → no customer exception

Map these to the specific decision/next-action/reason enums **allowed by that task's answer_template**
(the enum sets differ per task — e.g. the allocation task collapses to `manual_review` and only allows
`account_blocked` / `fraud_watch` / `account_review_required` / `inactive_product` /
`insufficient_effective_stock` reasons, with no credit_watch reason). Never emit an enum value that the
template does not list.

## Shared output conventions

- **Conform exactly to `answer_template.json`**: every required top-level key, every required item key,
  in the allowed enum vocabulary. Emit only JSON, no narrative.
- **Sorting**: apply the exact ordering the template states for each list (usually `order_id` asc, then
  `line_id` asc; SKU lists asc; supplier rows by `supplier_id` asc). Multi-key sorts must be applied in
  the stated order (e.g. transfers "sku asc, then quantity desc, then from_warehouse asc").
- **Money**: round to 2 decimals. Compute `extended_cost = round(unit_cost, 2-dp value) * quantity` then
  round to 2 dp; sum costs from already-rounded line values for totals.
- **Counts/units**: integers. Percentages to 1 dp unless the policy says otherwise; durations and other
  derived numbers per the stated precision.
- **Sets vs. lists**: SKU/PO/incident-id collections are sorted and de-duplicated (a SKU appearing on
  multiple lines is listed once). "maximum N" fields (e.g. `sample_incident_ids` max 5, and the held-PO
  cap of 5 in the quality-hold task) are the **first N after sorting ascending**, not all of them.
- **Summary rollups** must be recomputed from your own per-item results, not estimated — counts of each
  decision, total units, total cost, id-lists, etc. Cross-check that, e.g., `decision_counts` sums to
  `order_count` and id-lists match the rows that produced them.
- **Report all applicable flags independently.** A line/order can carry several structured signals at
  once. Even when one gate decides the headline action, still populate every flag list the row earns
  (e.g. a backordered order still lists its `low_stock_skus`; a manual-review order still lists its
  shortage/inactive SKUs). These lists describe the underlying state, not the chosen action.

## General SOP (every task)

1. Read the task `prompt.txt`, the payload/memo, and `answer_template.json`. Extract scope (orders/
   suppliers/BOMs/wave), dates, target quantities, and any embedded policy/precedence/thresholds.
2. Identify the task family and read the matching `references/*.md` SOP.
3. Pull the live records you need (orders/lines, products, customers, suppliers, inventory, POs,
   incidents, warehouses, BOMs). Prefer fetching all of a small collection once and indexing locally.
4. Compute per-item per the SOP's validated rules (effective availability, gates, precedence,
   exclusions, transfers, costs).
5. Build the output object: per-item rows (sorted), derived sub-lists (transfers, requisitions,
   blocked/held ids), and the summary recomputed from your rows.
6. Validate against the template: keys present, enums legal, lists sorted/deduped/capped, money 2 dp,
   summary internally consistent. Emit JSON only.

## Pitfalls the blind phase hit (avoid these)

- **Used gross instead of effective for the shortage test.** A line is `shortage` whenever
  `effective < quantity`, even if gross could cover it. Re-derive every classification from effective.
- **Dropped `low_stock_skus` on orders whose headline status was shortage.** Report every line's
  low_stock membership regardless of the order's aggregate status.
- **Reported a coverage field as the covering record's full size instead of the gap covered.** A
  "covered units" rollup is the **gap amount cleared**, not the full PO/lot quantity.
- **Left `primary_reason: "none"` on backorder lines.** A backorder is caused by
  `insufficient_effective_stock`; `none` is only for cleanly shippable or fully transfer-covered lines.
- **Held every open/confirmed PO with no cap, and only for frozen suppliers.** The held-PO list is the
  first 5 (sorted asc) open/confirmed POs, applied to every supplier whose decision is not the
  lowest "monitor" tier — see the quality-hold SOP.
- **Anchored a decision on coarse status (e.g. quality_status==watch) instead of the metric threshold.**
  Watch/approved alone do not determine the tier; the severity-count threshold does.
- **Trusted a memo's port/start instructions or stale availability.** Use the documented base URL and
  live records.
