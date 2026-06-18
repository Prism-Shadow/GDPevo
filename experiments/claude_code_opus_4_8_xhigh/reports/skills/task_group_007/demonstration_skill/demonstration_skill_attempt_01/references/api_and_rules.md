# Northwind ERP — Data Model, API, Rules & SOPs

Reference for the `northwind-erp-ops` skill. Read the relevant section while solving.

## Table of contents
1. API access & endpoints
2. Record shapes (fields you rely on)
3. Core formulas & shared rules
4. SOP — Expedite / dispatch-control queue
5. SOP — Mixed-warehouse allocation
6. SOP — Kit / BOM replenishment
7. SOP — Supplier incident scorecard
8. SOP — Supplier quality-hold / replenishment-control review

---

## 1. API access & endpoints

Base URL comes from `environment_access.md` (read it; trust it over any port in the task text).
Read-only JSON over plain HTTP GET. List endpoints return JSON arrays; single-record endpoints
return an object. Filters are exact string match; omit a filter to get everything.

- `GET /health` — manifest with record counts and `generation_timestamp` (a good "as-of" anchor).
- `GET /products` / `GET /products/<sku>`
- `GET /suppliers`
- `GET /customers` / `GET /customers/<customer_id>`
- `GET /warehouses`
- `GET /inventory?warehouse_id=&sku=`
- `GET /purchase_orders?supplier_id=&sku=&status=`
- `GET /orders?wave=&required_date=&customer_id=` / `GET /orders/<order_id>`
- `GET /boms` / `GET /boms/<bom_id>`
- `GET /incidents?start=&end=&supplier_id=&sku=&incident_type=&status=`
  — `start`/`end` filter on **`open_date`**, inclusive, **string compare on ISO dates**. So a
  Q1 filter is `start=2026-01-01&end=2026-03-31` and you can let the server do the filtering.
- `GET /shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=` — `speed` ∈
  {ground, two_day, overnight}, default ground.

Get the whole wave with `GET /orders?wave=<WAVE>` rather than fetching order-by-order from a memo
list — but cross-check the memo's order_ids against what the wave returns (the memo defines the
set you must answer for).

Recommended harness: Python `urllib.request` + `json`, one small `get(path)` helper, then compute
everything locally so rounding/sorting are deterministic.

---

## 2. Record shapes

**product** (`/products/<sku>`): `sku, name, category, active(bool), supplier_id, unit_cost,
weight_lb, safety_stock, overstock_threshold`.

**inventory row** (`/inventory`): `sku, warehouse_id, on_hand, reserved, quarantined,
last_count_date`. There is at most one row per (sku, warehouse); a SKU may be missing at a
warehouse entirely.

**customer** (`/customers/<id>`): `customer_id, name, account_status` {active, review_required,
blocked}, `risk_flag` {none, credit_watch, fraud_watch}, `tier`, `margin_band`.

**warehouse** (`/warehouses`): `warehouse_id` {WH_NORTH, WH_CENTRAL, WH_WEST}, `name, region, zip`.

**order** (`/orders/<id>`): `order_id, customer_id, warehouse_id` (the requested/origin
warehouse), `destination_zip, priority, required_date, shipping_speed, wave`, and `lines[]` each
`{line_id, sku, quantity, unit_price}`.

**bom** (`/boms/<id>`): `bom_id, name (the kit_name), warehouse_id, target_date, components[]`
each `{sku, quantity_per_kit}`.

**purchase_order** (`/purchase_orders`): `po_id, sku, supplier_id, warehouse_id, quantity, status`
{open, confirmed, received, cancelled}, `eta`.

**supplier** (`/suppliers`): `supplier_id, name, region, quality_status` {approved, watch,
quality_hold}.

**incident** (`/incidents`): `incident_id, supplier_id, sku, warehouse_id, incident_type`
{RMA, WORK_ORDER}, `severity` {low, medium, high, critical}, `status` {open, closed},
`open_date, close_date` (close_date present when closed), `resolution_cost, root_cause`.

---

## 3. Core formulas & shared rules

**Effective available** (per sku, warehouse) — the freely usable quantity:
```
raw       = on_hand - reserved - quarantined          # 0 for each missing field if no inv row
effective = raw - safety_stock
```
Reserved, quarantined, and safety_stock are all protected buffer. Missing inventory row →
`effective = -safety_stock`.

**Account/risk/product gate** — see SKILL.md "Account / risk / product precedence". blocked >
review_required > fraud_watch > credit_watch > inactive_product > none.

**Severe incident** = `severity in {high, critical}`.

**Timely / coverage PO** = status in {open, confirmed} (received and cancelled never count).
For kit builds, additionally require the PO's `warehouse_id == build site` **and** `eta <=
build_date`.

**Duration (days)** = `(end_date - open_date).days` where end_date = close_date for closed
incidents, else the analysis/as-of date.

**Shipping quote**: weight = `sum(line.quantity * product.weight_lb)` over the **whole order**.
Call `/shipping/quote?warehouse_id=<order.warehouse_id>&destination_zip=<order.destination_zip>
&weight_lb=<total>&speed=<order.shipping_speed>`. Copy the returned `zone_distance`,
`service_days`, and `total_cost` straight through (total_cost is already 2-decimal). Use the
order's `shipping_speed` unless the task names a specific speed for that order.

**Money**: `round(value, 2)`. `extended_cost = round(qty * unit_cost, 2)`.

---

## 4. SOP — Expedite / dispatch-control queue

Input: a memo with `order_ids` (and per-order operator notes). Output per order: `inventory_status`,
`customer_exception`, `final_decision`, `next_action`, `shortage_skus`, `inactive_skus`,
`low_stock_skus`, `shipping_quote`; plus a `summary`. Records sorted by order_id ascending.

For each order, fetch the order, its customer, and for each line the product + the inventory row
at the **order's warehouse**.

### 4a. Per-line inventory classification (uses effective stock + a low-stock test)
For each line, with `effective = raw - safety_stock`:
- **shortage** when `effective < line.quantity` (can't fully cover the line from free stock).
- else **low_stock** when `effective < safety_stock` (it covers the line, but free stock is below
  the safety level — a thin position worth flagging).
- else **ready**.
- Independently, if the product is `active == false`, add the SKU to `inactive_skus` (a SKU can be
  both inactive and shortage).

Collect `shortage_skus`, `low_stock_skus`, `inactive_skus` as unique, ascending lists.

### 4b. Order-level `inventory_status` (precedence over the line flags)
```
has_inactive and has_shortage  -> "inactive_and_shortage"
has_inactive                   -> "inactive_sku"
has_shortage                   -> "shortage"
has_low_stock                  -> "low_stock"
else                           -> "ready"
```

### 4c. `customer_exception`
Map from the account/risk gate:
- blocked        -> `account_blocked`
- review_required-> `review_required`
- fraud_watch    -> `fraud_watch`
- credit_watch   -> `credit_watch`
- else           -> `none`

### 4d. `final_decision` + `next_action`
The customer exception dominates the inventory state (you cannot ship/backorder an order you must
hold for account reasons). Decide top-down:
- `account_blocked`                         -> `reject_hold`     / `hold_credit_or_fraud`
- `fraud_watch` or `credit_watch`           -> `reject_hold`     / `hold_credit_or_fraud`
- `review_required`                         -> `manual_review`   / `send_account_review`
- else (no account/risk exception), by inventory_status:
  - `inactive_sku` or `inactive_and_shortage` (no account issue) -> `manual_review` /
    `escalate_product_master` (a product-master problem still needs human review; use the
    product-master next action when the block is purely the inactive SKU)
  - `shortage`                              -> `backorder`       / `create_backorder`
  - `low_stock`                             -> `delayed_release` / `delay_and_monitor`
  - `ready`                                 -> `ship_now`        / `release_to_pick`

Note from the data: when a customer needs review AND a line is inactive, the account review wins
(`manual_review` / `send_account_review`) because account precedence is higher than product status.
Only escalate product-master when there is no account/risk exception.

### 4e. Shipping quote
Always attach a quote (even for held/backordered orders — the desk may still want it). Use the
whole-order weight and the order's `shipping_speed`, unless an operator note specifies a speed.

### 4f. Summary
- `order_count` = number of records.
- `decision_counts` = count of each `final_decision` enum value (include zeros for unused values).
- `total_shipping_cost_usd` = `round(sum of every record's shipping total_cost, 2)`.
- `blocked_order_ids` = orders whose final_decision is `reject_hold` (the account/risk-blocked ones).
- `manual_review_order_ids` = orders with final_decision `manual_review`.
- `backorder_order_ids` = orders with final_decision `backorder`.
- `inactive_sku_order_ids` = orders whose `inactive_skus` is non-empty.
All ID lists ascending.

---

## 5. SOP — Mixed-warehouse allocation

Input: a wave + an allocation memo. Decide each **order line**: `ship` / `transfer` / `backorder` /
`manual_review`. Output: `line_actions`, `transfer_requests`, `blocked_orders`, `order_rollup`,
`summary`. `requested_effective_available` in the output uses the standard effective formula
(raw - safety_stock) at the line's requested warehouse.

For each line, in order:

1. **Account/risk/product gate first.** If the order's customer is blocked / review_required /
   fraud_watch / credit_watch, OR the product is inactive, the line is `manual_review` with
   `ship_quantity=0, transfer_from=null, transfer_quantity=0, backorder_quantity=0` and
   `primary_reason` = `account_blocked` / `account_review_required` / `fraud_watch` /
   `inactive_product` (account/risk precedence as in §3; inactive_product only when there's no
   account/risk issue). Account/risk holds put the order in `blocked_orders`. An inactive-product
   line does **not** put the order in `blocked_orders`.

2. **Otherwise do stock math** at the requested warehouse:
   - `eff = effective_available(sku, requested_warehouse)`
   - `ship_quantity = min(line.quantity, max(0, eff))`
   - `uncovered = line.quantity - ship_quantity`
   - If `uncovered == 0` -> action `ship`, `primary_reason = none`.
   - If `uncovered > 0`, look for a **single other** warehouse whose `effective_available >= uncovered`.
     Among qualifying warehouses pick the one with the **largest effective available** (tie-break by
     warehouse_id ascending). If one exists -> action `transfer`: `transfer_from` = that warehouse,
     `transfer_quantity = uncovered`, keep the usable `ship_quantity` at the requested warehouse,
     `backorder_quantity = 0`, `primary_reason = none`. Add a `transfer_requests` entry
     `{order_id, line_id, sku, from_warehouse, to_warehouse=requested_warehouse, quantity=uncovered}`.
   - If no single warehouse can cover the full uncovered amount -> action `backorder`,
     `backorder_quantity = uncovered`, `ship_quantity` stays as computed, `primary_reason =
     insufficient_effective_stock`.

`line_actions` and `transfer_requests` sort by order_id asc, then line_id asc.

**order_rollup** (one outcome per order):
```
all lines == ship                                   -> ready_to_ship
all lines == manual_review                          -> manual_review
manual_review present alongside any other action    -> mixed_actions
else any backorder                                  -> has_backorder
else any transfer                                   -> needs_transfer
```
(Apply in this order: pure-manual and pure-ship are the clean cases; any mix that includes a
manual_review is `mixed_actions`; otherwise backorder beats transfer.)

**blocked_orders**: orders stopped at the account/customer-risk level (blocked / review_required /
fraud_watch / credit_watch) — **not** orders that only have inactive-product line reviews. Sorted,
unique.

**summary** integers: `total_orders`, `total_lines`, `ship_lines`, `transfer_lines`,
`backorder_lines`, `manual_review_lines`, `blocked_orders` (count), `transfer_units`
(sum of transfer_quantity), `backorder_units` (sum of backorder_quantity).

---

## 6. SOP — Kit / BOM replenishment

Input: a production memo naming a build site, and target builds `{bom_id, target_build_quantity,
target_build_date}`. Output: `kit_targets`, `component_plan`, `transfer_requests`,
`purchase_requisitions`, `excluded_components`, `summary`. `plan_date` is the memo's plan/as-of
date — use the date portion (`YYYY-MM-DD`) of the memo's issue/as-of timestamp; fall back to the
`/health` `generation_timestamp` date if the memo gives none. Echo the task_id required by the
template.

`kit_targets`: one row per BOM `{bom_id, kit_name (=bom.name), warehouse_id (build site),
build_quantity, build_date}`, sorted by bom_id.

### 6a. Requirements
For every component SKU across all BOMs:
`total_required[sku] = sum over BOMs( bom.component.quantity_per_kit * that BOM's build_quantity )`.
A SKU used by multiple BOMs sums across them.

For per-SKU build dates: the **earliest** build_date among BOMs that use the SKU is its
transfer `needed_by`; the **latest** build_date among them is its purchase `needed_by`. (Transfers
must arrive for the first build; purchases are timed to the last build.)

### 6b. Effective stock at the build site & the gap
`target_effective_available[sku] = effective_available(sku, build_site)` (raw - safety_stock).
`gap = total_required - target_effective_available` (can be negative).

### 6c. Exclusions (compute before transfers/purchases)
- If `target_effective_available >= overstock_threshold` -> exclude, reason `target_overstock`,
  final_action `overstock_excluded`. (Already over the overstock line; do not add stock even if a
  naive gap looks positive.)
- Else if `gap <= 0` (site already covers the build): if a **timely PO** also exists it's still
  "stocked_no_gap"; the key point is **no transfer/purchase**. final_action `no_action_stocked`,
  reason `stocked_no_gap`.

### 6d. Timely PO coverage
`timely_po_qty[sku]` = sum of quantities of POs that are (status open or confirmed) AND
(warehouse_id == build site) AND (eta <= the SKU's build_date). Record their `po_id`s as
`coverage_po_ids` (sorted). If `timely_po_qty >= gap` (gap > 0), the gap is covered by inbound POs:
final_action `timely_po_covered`, reason `timely_po_covers_gap`, transfer_qty=0,
purchase_requisition_qty=0, and the SKU also goes in `excluded_components` with reason
`timely_po_covers_gap` and `supporting_po_ids = coverage_po_ids`. (POs at the wrong warehouse, or
with eta after the build date, or received/cancelled, do NOT count — those gaps still need filling.)

### 6e. Transfers then purchase for the remaining gap
When `gap > 0` and timely POs do not cover it, the remaining need is `gap` (timely POs that only
partially cover can be netted against the gap; if a SKU has both, subtract timely_po_qty first).
Fill from sister warehouses using their effective_available:
- For each other warehouse with `effective_available > 0`, you may transfer up to that amount.
  Take as much as available from each (greedily) until the gap is met. This can yield multiple
  transfer rows for one SKU (one per source warehouse).
- `transfer_qty[sku]` = total transferred (capped at the gap).
- `purchase_requisition_qty[sku]` = `gap - transfer_qty` (whatever sister stock can't cover).
- final_action: `transfer_only` if purchase qty is 0 and transfer qty > 0; `purchase_required` if
  any purchase qty > 0 (even if some transfer also happens).

`transfer_requests` rows: `{sku, from_warehouse_id, to_warehouse_id (=build site), quantity,
needed_by (=SKU's transfer needed_by = earliest build date)}`. Sort by sku asc, then quantity desc,
then from_warehouse_id asc.

`purchase_requisitions` rows: `{sku, supplier_id (=product.supplier_id), warehouse_id (=build site),
quantity (=purchase_requisition_qty), needed_by (=SKU's purchase needed_by = latest build date),
unit_cost (=product.unit_cost), extended_cost (=round(qty*unit_cost,2))}`. Sort by sku asc.

`component_plan` rows carry: `sku, total_required, target_effective_available, timely_po_qty,
transfer_qty, purchase_requisition_qty, final_action, coverage_po_ids, exclusion_reason`
(reason is `none` for active transfer/purchase lines). Sort by sku asc.

`excluded_components`: one row per excluded SKU `{sku, reason, supporting_po_ids}` (supporting POs
only for timely_po_covers_gap; `[]` otherwise). Sort by sku asc.

`summary`: `component_count` (distinct components considered), `total_purchase_units`,
`total_purchase_cost` (round 2dp), `total_transfer_units`, `timely_po_covered_units` (sum over
timely_po_covered SKUs of the **gap that the POs cover**, i.e. `min(timely_po_qty, gap)` where
`gap = total_required - target_effective_available` — count the demand satisfied, not the full
inbound PO quantity).

---

## 7. SOP — Supplier incident scorecard

Input: a scorecard request with a date filter (open_date window), an `analysis_date`, a
`duration_rule`, `percentage_rule`, `severe_severity_values`, and an explicit
`recommendation_policy` with a `precedence` list and per-code conditions. **Use the policy
verbatim from the request payload** — thresholds may vary between tasks. Below is the structure;
plug in the request's numbers.

1. Pull the filtered population: `/incidents?start=<start>&end=<end>` (server filters open_date,
   inclusive). `filtered_incident_count` = its length.
2. Group by `supplier_id`. `supplier_count` = number of suppliers with ≥1 filtered incident.
3. Per supplier row (sorted supplier_id asc):
   - `incident_count`, `incident_percentage = round(count/total*100, <pct precision>)`.
   - `total_resolution_cost = round(sum(resolution_cost), 2)`.
   - `avg_duration_days = round(mean(duration), 2)` with duration per §3 (closed→close_date,
     open→analysis_date).
   - `rma_count` (incident_type RMA), `work_order_count` (WORK_ORDER).
   - `open_incident_count` (status open), `severe_incident_count` (severity in
     `severe_severity_values`).
   - `recommendation_code`: evaluate the policy's conditions **in precedence order** and take the
     first that matches; default to the lowest (MONITOR). A typical policy:
     - ESCALATE_SUPPLIER: supplier on quality_hold with ≥3 filtered incidents, OR any critical RMA,
       OR (≥3 RMAs AND total filtered cost ≥ threshold).
     - PROCESS_REVIEW: WORK_ORDER incidents ≥3 AND work_order_count > rma_count.
     - WATCHLIST: quality_status in {watch, quality_hold}, OR incident_count ≥ threshold, OR total
       cost ≥ threshold, OR severe_incident_count ≥ 2.
     - MONITOR: none of the above.
     Read each threshold from the request; do not assume.
4. `summary`: `filtered_incident_count`, `supplier_count`, `total_resolution_cost` (round 2dp over
   the whole population), `overall_rma_count`, `overall_work_order_count`.
5. `top_escalation_suppliers`: supplier_ids whose code is ESCALATE_SUPPLIER, sorted by the request's
   `top_escalation_order` (e.g. incident_count desc, then total_resolution_cost desc, then
   supplier_id asc).
6. `highest_cost_supplier_id`: supplier with max total_resolution_cost (tie-break by the same
   escalation order / supplier_id asc). `highest_share_supplier_id`: supplier with max
   incident_count (same tie-break).
7. `analysis_window` echoes start/end/analysis_date from the request.

---

## 8. SOP — Supplier quality-hold / replenishment-control review

Input: a review memo with `target_supplier_ids`, an analysis window (start/end on incident
open_date), and `decision_choices` {freeze_new_replenishment, buyer_review_required, monitor_only}.
The decision policy is usually **not** spelled out — infer it from supplier signals as below.
Output: `analysis_window`, `supplier_decisions` (sorted by supplier_id), `held_po_ids`,
`release_supplier_ids`, `summary`.

Per supplier:
1. Recent incidents: `/incidents?start=<start>&end=<end>&supplier_id=<id>`.
   - `recent_incident_count`, `recent_rma_count` (RMA), `severe_or_critical_count`
     (severity high/critical), `open_incident_count` (status open).
   - `affected_skus` = unique sorted SKUs across those incidents.
   - `sample_incident_ids` = incident_ids sorted ascending, **capped at 5** (sort, then first 5).
2. `quality_status` from `/suppliers`.
3. **Decision** (precedence, firmest first):
   - `quality_status == quality_hold` -> `freeze_new_replenishment`.
   - else if the supplier shows elevated recent quality risk -> `buyer_review_required`. The
     observed trigger is `severe_or_critical_count >= 2`; also treat a `watch` status with multiple
     RMAs or open incidents as buyer-review candidates. (If the memo provides explicit thresholds,
     use those instead of this heuristic.)
   - else -> `monitor_only`.
4. **Held POs** (`held_po_ids` per supplier): the supplier's open/confirmed POs (status in
   {open, confirmed}), sorted by po_id ascending, **capped at 5** (sort, take first 5). Hold POs
   **only** when the decision is `freeze_new_replenishment` or `buyer_review_required`; for
   `monitor_only` the held list is empty.

Top-level:
- `held_po_ids` = sorted unique union of every supplier's held POs.
- `release_supplier_ids` = supplier_ids whose decision is `monitor_only` (sorted).
- `summary`: `suppliers_reviewed`, `freeze_count`, `buyer_review_count`, `monitor_count`,
  `held_po_count` (length of the global held list), `total_recent_incidents` (sum of
  recent_incident_count across suppliers).

Note: the quality_hold→freeze rule is the firmest, verified mapping. The watch→buyer_review vs
monitor split keys on recent severity (severe/critical ≥ 2 → buyer_review). If a task gives an
explicit policy, follow it; otherwise apply this and sanity-check against the supplier's
quality_status and incident profile.
