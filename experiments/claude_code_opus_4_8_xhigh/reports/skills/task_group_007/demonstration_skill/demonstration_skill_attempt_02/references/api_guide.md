# Northwind ERP API Guide

Read-only JSON over HTTP GET. **Base URL: use the exact one in `environment_access.md`** (currently `http://127.0.0.1:8015`). Ignore any other port mentioned in task prose. Filters are exact string match; omitting a filter returns all rows. Single-record endpoints return an object; list endpoints return an array.

## Table of contents
1. Endpoints and fields
2. Which endpoint answers which question
3. Date-window semantics (`/incidents`)
4. Shipping quote semantics
5. Quick recipes

---

## 1. Endpoints and fields

### `GET /health`
Service status + manifest: `record_counts` per collection and `generation_timestamp` (the dataset "as-of" instant). Hit this first.

### `GET /products` , `GET /products/<sku>`
Product master. Fields:
- `sku`, `name`, `category`
- `active` (**boolean** — `false` means inactive/discontinued; there is no string `status` field)
- `safety_stock` (int — protected buffer, subtract from availability)
- `overstock_threshold` (int — used to detect overstock/no-replenish situations)
- `unit_cost` (number — use for purchase requisition `unit_cost`)
- `supplier_id` (the SKU's source supplier — use for requisitions; do NOT trust a supplier guessed from the memo)
- `weight_lb` (number — per-unit weight for shipping)

### `GET /suppliers`
Fields: `supplier_id`, `name`, `region`, `quality_status` ∈ {`approved`, `watch`, `quality_hold`}.

### `GET /customers` , `GET /customers/<customer_id>`
Fields: `customer_id`, `name`, `tier` ∈ {`economy`,`standard`,`strategic`}, `margin_band` ∈ {`low`,`medium`,`high`}, `account_status` ∈ {`active`,`blocked`,`review_required`}, `risk_flag` ∈ {`none`,`credit_watch`,`fraud_watch`}.

### `GET /warehouses`
Three warehouses: `WH_NORTH`, `WH_CENTRAL`, `WH_WEST`, each with `name`, `region`, `zip`.

### `GET /inventory?warehouse_id=&sku=`
One row per (sku, warehouse). Fields: `sku`, `warehouse_id`, `on_hand`, `reserved`, `quarantined`, `last_count_date`. A SKU may have a row in 0–3 warehouses (no row ⇒ treat as 0 stock there).

### `GET /purchase_orders?supplier_id=&sku=&status=`
Fields: `po_id`, `sku`, `supplier_id`, `warehouse_id`, `quantity`, `eta`, `status` ∈ {`open`,`confirmed`,`received`,`cancelled`}. "Live/incoming" POs are **open or confirmed**; `received` and `cancelled` do not provide incoming supply.

### `GET /orders?wave=&required_date=&customer_id=` , `GET /orders/<order_id>`
Fields: `order_id`, `customer_id`, `warehouse_id` (requested fulfillment WH), `wave`, `priority`, `required_date`, `destination_zip`, `shipping_speed` ∈ {`ground`,`two_day`,`overnight`}, and `lines` = list of `{line_id, sku, quantity, unit_price}`. Filter a wave with `?wave=<WAVE_ID>` to get every order in it.

### `GET /boms` , `GET /boms/<bom_id>`
Fields: `bom_id`, `name`, `warehouse_id`, `target_date`, `components` = list of `{sku, quantity_per_kit}`. Note the memo's `build_quantity`/`build_date` override the BOM's own `target_date`; the BOM gives the `name` and `warehouse_id` (build site).

### `GET /incidents?start=&end=&supplier_id=&sku=&incident_type=&status=`
Fields: `incident_id`, `supplier_id`, `sku`, `warehouse_id`, `incident_type` ∈ {`RMA`,`WORK_ORDER`}, `severity` ∈ {`low`,`medium`,`high`,`critical`}, `status` ∈ {`open`,`closed`}, `open_date`, `close_date` (present when closed), `resolution_cost`, `root_cause`.

### `GET /shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=`
Returns `zone_distance` (int), `service_days` (int), `total_cost` (number), plus `base_rate`, `fuel_surcharge_rate`, `carrier`. `weight_lb` is **required** (400 error if omitted). `speed` defaults to `ground`.

---

## 2. Which endpoint answers which question

- "Can this order/line ship?" → `/orders/<id>` for lines + requested WH, `/inventory?sku=` for stock in all WHs, `/products/<sku>` for `safety_stock` & `active`, `/customers/<id>` for risk gates.
- "What incoming supply exists?" → `/purchase_orders?sku=` (keep `open`/`confirmed`, check `warehouse_id` and `eta` vs the need date).
- "What does a build need?" → `/boms/<id>` for components, then `/inventory` + `/products` per component.
- "Supplier quality?" → `/suppliers` for `quality_status`, `/incidents?supplier_id=&start=&end=` for the population.
- "How much to ship it?" → `/shipping/quote` (don't compute).

---

## 3. Date-window semantics (`/incidents`)

- `start`/`end` filter on **`open_date`**, **inclusive** on both ends, by ISO-string comparison (`YYYY-MM-DD`). `?start=2026-01-01&end=2026-03-31` returns incidents opened on Jan 1 through Mar 31 inclusive.
- The filter does **not** consider `close_date` or `status`. "Still open" is a separate `status == "open"` test on the filtered rows.
- Always pass the window from the task payload into the query so the population is exactly the filtered set the task wants.
- **Duration**: closed incident = `close_date − open_date` in calendar days; open incident = `analysis_date − open_date` (use the analysis/as-of date from the payload). Average to the precision the payload states.

---

## 4. Shipping quote semantics

The endpoint already returns the answer fields; map them straight through:
- output `zone_distance` ← response `zone_distance`
- output `service_days` ← response `service_days`
- output `total_cost_usd` (or similar) ← `round(response.total_cost, 2)`

Choosing the **inputs** is the only judgment:
- `warehouse_id` = the order's `warehouse_id` (the WH it ships from).
- `destination_zip` = the order's `destination_zip`.
- `weight_lb` = total order weight = `Σ over lines (quantity × product.weight_lb)`. (For a single-line quote it's that line's `quantity × weight_lb`.)
- `speed` = whatever the memo/operator note or the task asks for that order; if a note says "overnight quote", use `overnight`; if it says "use the order's requested shipping speed", use the order's `shipping_speed`; otherwise default `ground`.
- `service_days` depends only on `speed` (overnight→1, two_day→2, ground→varies by zone). Provide a quote even when the fulfillment decision is not "ship" if the task asks for one.

---

## 5. Quick recipes

Fetch + compute deterministically in Python rather than by hand:

```python
import urllib.request, json
BASE = "http://127.0.0.1:8015"   # confirm against environment_access.md
def get(path):
    with urllib.request.urlopen(BASE + path) as r:
        return json.load(r)

def effective(sku, wh):
    rows = [r for r in get(f"/inventory?sku={sku}") if r["warehouse_id"] == wh]
    if not rows:
        ss = get(f"/products/{sku}")["safety_stock"]
        return -ss            # no inventory row ⇒ on_hand=reserved=quar=0
    r = rows[0]
    ss = get(f"/products/{sku}")["safety_stock"]
    return r["on_hand"] - r["reserved"] - r["quarantined"] - ss
```

Always round currency at the end with `round(x, 2)`; build summary counts by tallying the per-row results you already computed so the rollup is internally consistent.
