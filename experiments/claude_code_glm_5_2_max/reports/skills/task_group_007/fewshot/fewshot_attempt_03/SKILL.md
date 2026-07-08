# Northwind Components ERP Fulfillment — Solver Skill

Executable experience for solving Northwind Components ERP fulfillment/procurement tasks against the shared remote API. Distilled from the five train task families and verified field-by-field against live API records.

The base business object is the same across all tasks: this is a **components distributor** with SKUs, warehouses, inventory (with reserved/quarantined/safety-stock layers), customer account/risk state, purchase orders, BOMs, shipping quotes, and supplier quality incidents. Tasks ask for a structured JSON decision file. **Always read `input/payloads/answer_template.json` first** — it defines the exact required keys, enums, and ordering for that task. Match its shape precisely.

---

## 1. Remote environment & API

Base URL (use exactly this; do NOT start a local server or read `env/`):
```
<remote-env-url>
```

Calling notes:
- The server speaks HTTP/1.0 and closes each connection. Use `curl -sS --max-time 30 '<url>'` per call, or `urllib.request.urlopen(url, timeout=30)`. Each call is a fresh connection.
- All endpoints are GET. Parse JSON with python3 `json` or `jq`.
- Endpoints return **lists** (or a single object for `/<id>` detail routes). Some list endpoints accept filter query params; when a needed filter is not honored, fetch the full list and filter client-side.

Endpoints:
- `GET /health` — manifest (record counts, seed). Useful sanity check.
- `GET /products` and `GET /products/<sku>` — SKU master. Fields: `sku, name, category, active, supplier_id, unit_cost, weight_lb, safety_stock, overstock_threshold`.
- `GET /customers` and `GET /customers/<customer_id>` — account/risk. Fields: `customer_id, name, tier, margin_band, account_status, risk_flag`. `account_status` ∈ {active, review_required, blocked}. `risk_flag` ∈ {none, credit_watch, fraud_watch}.
- `GET /warehouses` — `warehouse_id, name, zip, region`. Three warehouses: `WH_NORTH`, `WH_CENTRAL`, `WH_WEST`.
- `GET /inventory?warehouse_id=&sku=` — returns a list. Fields: `sku, warehouse_id, on_hand, reserved, quarantined, last_count_date`. May return empty for a sku/warehouse with no stock record.
- `GET /purchase_orders?supplier_id=&sku=&status=` — POs. Fields include `po_id, supplier_id, sku, warehouse_id, quantity, eta, status`. `status` ∈ {open, confirmed, received, cancelled}.
- `GET /orders?wave=&required_date=&customer_id=` and `GET /orders/<order_id>` — order detail. Fields: `order_id, wave, customer_id, warehouse_id, destination_zip, shipping_speed, priority, required_date, lines[]`. Each line: `line_id, sku, quantity, unit_price`.
- `GET /shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=` — returns `base_rate, fuel_surcharge_rate, carrier, zone_distance, service_days, total_cost, ...`. **`total_cost` maps to the output field `total_cost_usd`.**
- `GET /incidents?start=&end=&supplier_id=&sku=&incident_type=&status=` — incident records. Fields: `incident_id, supplier_id, sku, warehouse_id, incident_type, severity, status, open_date, close_date, resolution_cost, root_cause`. `incident_type` ∈ {RMA, WORK_ORDER}. `severity` ∈ {low, medium, high, critical}. `status` ∈ {open, closed}. `close_date` is null when open.
- `GET /suppliers` — `supplier_id, name, region, quality_status`. `quality_status` ∈ {approved, watch, quality_hold}.
- `GET /boms` and `GET /boms/<bom_id>` — Bill of Materials. Fields: `bom_id, name, warehouse_id, target_date, components[]`. Each component: `sku, quantity_per_kit`.

---

## 2. Core domain formulas (used by every task family)

### Effective available stock
For a SKU at a warehouse:
```
effective_available = on_hand - reserved - quarantined - safety_stock
```
- `safety_stock` comes from the **product master** (`/products`), NOT the inventory record.
- This is the freely-usable stock. Reserved, quarantined, and the safety buffer are all protected and must NOT be treated as available.
- A line is **short** (shortage) when `effective_available < line.quantity`.
- A line is **low stock** when `effective_available >= line.quantity` BUT `effective_available < product.safety_stock` (i.e. usable but dipping into the safety buffer). Low-stock and shortage are mutually exclusive per line (use shortage first).
- **Inactive** = `product.active == false` (independent of stock; a SKU can be both inactive and short).
- Effective available can be **negative** (committed beyond on-hand). Preserve the negative value in output fields that ask for it.

### Shipping quote (full shipment weight)
For an order, compute the **total shipment weight** = Σ over ALL order lines of `line.quantity * product.weight_lb`, using the FULL ordered quantities (do not adjust for shortages or backorders — the quote is for the whole order). Then:
```
GET /shipping/quote?warehouse_id=<order.warehouse_id>&destination_zip=<order.destination_zip>&weight_lb=<total_weight>&speed=<order.shipping_speed>
```
Map the response: `zone_distance` → output zone_distance, `service_days` → output service_days, `total_cost` → output `total_cost_usd`. Compute the quote for EVERY order in the queue, regardless of the fulfillment decision (even backorder/reject orders get a quote).

### BOM expansion
`quantity_per_kit` × `build_quantity`, summed across every BOM that contains the SKU, gives `total_required` per component. A component needed by two kits gets both contributions.

### Rounding
- Currency (USD): 2 decimals everywhere (`total_cost_usd`, `unit_cost`, `extended_cost`, `total_purchase_cost`, `total_resolution_cost`, `total_shipping_cost_usd`). `extended_cost = quantity * unit_cost` rounded to 2 dp.
- Percentages: 1 decimal (`incident_percentage = count / filtered_total * 100`).
- Durations: 2 decimals (`avg_duration_days`).
- Counts: integers. Use `round(x, n)`; for currency sums, sum then round to 2 dp.

### Ordering (apply the template's stated ordering exactly)
- Records/lines sorted ascending by `order_id` (then `line_id` for line-level tasks).
- SKU lists sorted ascending by SKU.
- ID lists (po_ids, incident_ids, order_ids) sorted ascending as strings.

---

## 3. Task family A — Expedite-queue dispatch decision

**Input**: a queue memo listing `order_ids` for a `wave_id`. **Output**: `{wave_id, records[], summary}`.

### Per order, compute three SKU lists (each line classified independently)
1. If `product.active == false` → add SKU to `inactive_skus`.
2. If `effective_available < line.quantity` → add SKU to `shortage_skus` (can overlap with inactive for the same SKU).
3. Else if `effective_available < product.safety_stock` → add SKU to `low_stock_skus` (exclusive with shortage).
Sort each list ascending, de-duplicate.

### inventory_status (highest-priority classification wins)
| Condition | inventory_status |
|---|---|
| has inactive AND has shortage | `inactive_and_shortage` |
| has inactive, no shortage | `inactive_sku` |
| has shortage, no inactive | `shortage` |
| has low stock, no shortage/inactive | `low_stock` |
| none of the above | `ready` |

### customer_exception (account/risk classification, precedence top-down)
1. `customer.account_status == "blocked"` → `account_blocked`
2. `customer.risk_flag == "fraud_watch"` → `fraud_watch`
3. `customer.risk_flag == "credit_watch"` → `credit_watch`
4. `customer.account_status == "review_required"` → `review_required`
5. else → `none`

(account_status=blocked dominates risk_flag — confirmed: a blocked+credit_watch customer is classified `account_blocked`.)

### final_decision / next_action (precedence: customer exception dominates inventory)
| customer_exception | inventory_status | final_decision | next_action |
|---|---|---|---|
| account_blocked / credit_watch / fraud_watch | (any) | `reject_hold` | `hold_credit_or_fraud` |
| review_required | (any) | `manual_review` | `send_account_review` |
| none | shortage OR inactive_and_shortage | `backorder` | `create_backorder` |
| none | inactive_sku | `manual_review` | `escalate_product_master` |
| none | low_stock | `delayed_release` | `delay_and_monitor` |
| none | ready | `ship_now` | `release_to_pick` |

Key confirmed behaviors:
- An account/risk exception **overrides** inventory: a shortage order with `review_required` still goes `manual_review/send_account_review`, not backorder.
- `reject_hold` is the hardest stop (account blocked / credit or fraud hold). The `hold_credit_or_fraud` next_action exists specifically for credit/fraud/blocked cases.
- The `inactive_sku` (no shortage, no exception) row and `low_stock`/`ready` rows are derived from the enum semantics and next_action set — the train set only exercised shortage/backorder, account-blocked/reject_hold, and review/manual_review rows, so confirm against the template's allowed enums.

### shipping_quote (per order)
Compute as in §2 using the order's warehouse, destination_zip, full-line weight, and the order's own `shipping_speed`. Always present.

### summary
- `order_count`: number of records.
- `decision_counts`: object with the 5 decision keys → integer counts.
- `total_shipping_cost_usd`: Σ of all records' `shipping_quote.total_cost_usd`, 2 dp.
- `blocked_order_ids`: orders with `final_decision == reject_hold` (account-blocked/credit/fraud), sorted ascending.
- `manual_review_order_ids`: orders with `final_decision == manual_review`, sorted.
- `backorder_order_ids`: orders with `final_decision == backorder`, sorted.
- `inactive_sku_order_ids`: orders that have any SKU in `inactive_skus`, sorted.

---

## 4. Task family B — BOM kit replenishment package

**Input**: a production memo naming BOM ids with `target_build_quantity` and `target_build_date` for a single planning warehouse (e.g. WH_WEST). **Output**: `{task_id, plan_date, kit_targets[], component_plan[], transfer_requests[], purchase_requisitions[], excluded_components[], summary}`.

### kit_targets
Echo each BOM: `bom_id, kit_name` (from BOM record `name`), `warehouse_id` (planning site), `build_quantity, build_date`. Sort by `bom_id` ascending.

### Per-component plan (target warehouse = planning site WH_WEST)
For each distinct component SKU across all target BOMs:
- `total_required` = Σ `quantity_per_kit * build_quantity` over BOMs containing it.
- `target_effective_available` = **effective available stock AT THE TARGET WAREHOUSE** (on_hand − reserved − quarantined − safety_stock). This is the raw stock position, NOT net of total_required. (Can be negative; preserve.)
- `gap = max(0, total_required - target_effective_available)`.
- `timely_po_qty` = Σ quantity of POs for this SKU at the **target warehouse** with `status ∈ {open, confirmed}` AND `eta <= build_date` (the build date of the BOM needing this SKU; for a component needed by multiple BOMs, a PO is timely if its eta is on/before the relevant build date). Only same-warehouse POs count; cancelled/received POs are excluded. (This reports the full eligible PO quantity, not capped to the gap.)
- `coverage_po_ids` = sorted list of the timely PO ids that cover a gap.

### Coverage / decision logic (check in this order)
1. **No gap** (`gap == 0`, i.e. `target_effective_available >= total_required`):
   - If `target_effective_available >= product.overstock_threshold` → `final_action=overstock_excluded`, `exclusion_reason=target_overstock`. Add to `excluded_components`.
   - Else → `final_action=no_action_stocked`, `exclusion_reason=stocked_no_gap`. Add to `excluded_components. (Counterpart inferred from the enum; the train exercised only the overstock branch.)
   - `transfer_qty=0, purchase_requisition_qty=0, coverage_po_ids=[]`.
2. **Gap covered by timely PO** (`gap > 0` AND timely PO quantity `>= gap`):
   - `final_action=timely_po_covered`, `exclusion_reason=timely_po_covers_gap`. Add to `excluded_components` with supporting_po_ids = coverage_po_ids.
   - `transfer_qty=0, purchase_requisition_qty=0`.
3. **Gap needs transfer + purchase** (`gap > 0`, timely PO does not fully cover):
   - Transfers: pull effective stock from the **other** warehouses, **greedy by descending effective_available**, taking `min(other_eff, remaining_gap)` from each (only warehouses with `effective_available > 0`). Stop when the gap is filled or no positive stock remains. (If a timely PO partially covers, subtract its covered quantity from the gap first — partial-PO coverage is not exercised in train but follows the same residual-gap logic.)
   - `transfer_qty` = total quantity transferred (capped at gap).
   - `purchase_requisition_qty` = remaining gap after transfers.
   - `final_action`: if `purchase_requisition_qty > 0` → `purchase_required`; elif `transfer_qty > 0` and purchase==0 → `transfer_only`.
   - `exclusion_reason=none`.

### transfer_requests (one row per source warehouse actually used)
`sku, from_warehouse_id, to_warehouse_id(=planning site), quantity, needed_by`.
- `needed_by` = the **earliest** build date among BOMs containing this SKU (transfers are expedited for the first build).
- Sort: by `sku` ascending, then `quantity` descending, then `from_warehouse_id` ascending.

### purchase_requisitions (one row per SKU needing purchase)
`sku, supplier_id, warehouse_id(=planning site), quantity(=purchase_requisition_qty), needed_by, unit_cost, extended_cost`.
- `supplier_id` and `unit_cost` from the **product master** (`product.supplier_id`, `product.unit_cost`).
- `needed_by` = the **latest** build date among BOMs containing this SKU (PO lead time aligns to the last build).
- `extended_cost = quantity * unit_cost`, 2 dp.
- Sort by `sku` ascending.

### excluded_components
`sku, reason (target_overstock | timely_po_covers_gap | stocked_no_gap), supporting_po_ids` (sorted; empty for overstock/stocked). Sort by `sku` ascending.

### summary
- `component_count`: number of distinct components.
- `total_purchase_units`: Σ `purchase_requisition_qty`.
- `total_purchase_cost`: Σ `extended_cost`, 2 dp.
- `total_transfer_units`: Σ `transfer_qty`.
- `timely_po_covered_units`: Σ of the **gap** covered by timely POs (= `max(0, total_required - target_effective_available)` for each timely-po-covered component). This is the gap covered, NOT the full PO quantity.

---

## 5. Task family C — Supplier incident scorecard

**Input**: a scorecard request (`incident_date_filter` on `open_date`, `analysis_date`, `duration_rule`, `percentage_rule`, `recommendation_policy`). **Output**: `{analysis_window, summary, supplier_scorecard[], top_escalation_suppliers, highest_cost_supplier_id, highest_share_supplier_id}`.

### Filtering
Filter incidents by `open_date` within `[start_date, end_date]` **inclusive** (string comparison on YYYY-MM-DD works). The filter field is `open_date` (NOT close_date). Recommend fetching all `/incidents` and filtering client-side to be certain of the field.

### summary
- `filtered_incident_count`: count after filter.
- `supplier_count`: distinct suppliers with ≥1 filtered incident.
- `total_resolution_cost`: Σ `resolution_cost`, 2 dp.
- `overall_rma_count`: filtered incidents with `incident_type == RMA`.
- `overall_work_order_count`: filtered with `incident_type == WORK_ORDER`.

### Per supplier (only suppliers with ≥1 filtered incident; sort `supplier_id` ascending)
- `incident_count`, `total_resolution_cost` (2 dp).
- `incident_percentage` = `incident_count / filtered_incident_count * 100`, 1 dp.
- `avg_duration_days`: for each incident, calendar days = (close_date − open_date) if closed, else (analysis_date − open_date) if open. Average over the supplier's filtered incidents, 2 dp.
- `rma_count`, `work_order_count`, `open_incident_count` (status==open).
- `severe_incident_count`: `severity ∈ {high, critical}`.
- `recommendation_code`: apply the policy below (precedence: ESCALATE > PROCESS_REVIEW > WATCHLIST > MONITOR).

### Recommendation policy (apply in this precedence order; first match wins)
1. `ESCALATE_SUPPLIER` — supplier `quality_status == quality_hold` AND `incident_count >= 3`; OR any **critical** severity RMA (`severity == critical` AND `incident_type == RMA`); OR (`rma_count >= 3` AND `total_resolution_cost >= 15000.00`).
2. `PROCESS_REVIEW` — `work_order_count >= 3` AND `work_order_count > rma_count`.
3. `WATCHLIST` — `quality_status ∈ {watch, quality_hold}`; OR `incident_count >= 4`; OR `total_resolution_cost >= 12000.00`; OR `severe_incident_count >= 2`.
4. `MONITOR` — none of the above.

Note: a supplier can satisfy multiple codes; assign the **highest-precedence** one. (e.g. severity≥2 also satisfies WATCHLIST, but if PROCESS_REVIEW applies it wins.)

### Derived outputs
- `top_escalation_suppliers`: supplier_ids with `recommendation_code == ESCALATE_SUPPLIER`, ordered by `incident_count` desc, then `total_resolution_cost` desc, then `supplier_id` asc.
- `highest_cost_supplier_id`: supplier with max `total_resolution_cost` (tie-break: supplier_id asc).
- `highest_share_supplier_id`: supplier with max `incident_count` (tie-break: supplier_id asc).

---

## 6. Task family D — Allocation / transfer decision file

**Input**: a wave id (e.g. `<WAVE_ID>`) plus an allocation memo. **Output**: `{wave_id, line_actions[], transfer_requests[], blocked_orders[], order_rollup[], summary}`.

### Fetch the wave's orders
`GET /orders?wave=<wave_id>`, then for each order fetch `/orders/<order_id>` (the wave list may already include lines; use whichever is complete) and `/customers/<customer_id>`.

### Blocked-order detection (account/risk level)
An order is **blocked** if `customer.account_status ∈ {blocked, review_required}` OR `customer.risk_flag ∈ {fraud_watch, credit_watch}`. Blocked orders are added to `blocked_orders` (sorted ascending) and EVERY line gets `action=manual_review`. The `primary_reason`:
- `account_status == blocked` → `account_blocked`
- `account_status == review_required` → `account_review_required`
- `risk_flag == fraud_watch` → `fraud_watch`
(account_status dominates risk_flag for the reason; a blocked+credit_watch order → `account_blocked`.)

### Line action (for non-blocked orders)
For each line, compute `requested_effective_available` = effective available at the order's `requested_warehouse` (= `order.warehouse_id`).

Decision branch (after the blocked check):
1. **Inactive product** (`product.active == false`) → `action=manual_review`, `primary_reason=inactive_product`. ship/transfer/backorder = 0. (This applies even if the order is not account-blocked.)
2. **`requested_effective_available >= line.quantity`** (full coverage) → `action=ship`, `ship_quantity=line.quantity`, primary_reason=`none`.
3. **Partial or no coverage, active product**:
   - `ship_quantity = max(0, min(line.quantity, requested_effective_available))` (retain usable stock from the requested warehouse).
   - `remaining = line.quantity - ship_quantity`.
   - Look at the **other** warehouses' effective available stock. Pick the **single** warehouse with the **highest** effective available (tie-break: `warehouse_id` ascending).
   - If that best other warehouse has `effective_available >= remaining` → `action=transfer`, `transfer_from=best`, `transfer_quantity=remaining`, `backorder_quantity=0`, primary_reason=`none`.
   - Else → `action=backorder`, `backorder_quantity=remaining`, `transfer_from=null`, `transfer_quantity=0`, primary_reason=`insufficient_effective_stock`.
     (The partial-stock-at-requested-wh + no-other-covers edge is not exercised in train; the rule above retains `ship_quantity` and backorders the remainder, consistent with "backorder = cannot be cleared from current effective stock" plus retaining usable stock.)

### line_actions fields
`order_id, line_id, sku, requested_warehouse, requested_effective_available, action, ship_quantity, transfer_from (or null), transfer_quantity, backorder_quantity, primary_reason`. Sort by `order_id` asc, then `line_id` asc.

### transfer_requests
One row per transfer line: `order_id, line_id, sku, from_warehouse, to_warehouse(=requested_warehouse), quantity(=transfer_quantity)`. Sort by `order_id` asc, then `line_id` asc.

### order_rollup (one per order, sort by order_id asc)
Precedence (first match):
1. all lines `manual_review` → `manual_review`
2. any line `manual_review` (mixed with other actions) → `mixed_actions`
3. any line `backorder` → `has_backorder`
4. any line `transfer` → `needs_transfer`
5. all lines `ship` → `ready_to_ship`

### summary
`total_orders, total_lines, ship_lines, transfer_lines, backorder_lines, manual_review_lines, blocked_orders (count), transfer_units (Σ transfer_quantity), backorder_units (Σ backorder_quantity)`.

---

## 7. Task family E — Quality-hold replenishment review

**Input**: a `quality_hold_review_memo` with `analysis_window {start, end}` and `target_supplier_ids[]`. **Output**: `{analysis_window, supplier_decisions[], held_po_ids, release_supplier_ids, summary}`.

### Per target supplier
Filter `/incidents` to this supplier with `open_date` in `[start, end]` inclusive:
- `recent_incident_count`: count.
- `recent_rma_count`: `incident_type == RMA`.
- `severe_or_critical_count`: `severity ∈ {high, critical}`.
- `open_incident_count`: `status == open`.
- `affected_skus`: sorted unique SKUs from filtered incidents.
- `sample_incident_ids`: sorted incident_ids, **capped at 5** (the first 5 ascending).
- `quality_status`: from `/suppliers`.

### decision (inferred from train: 3 cases; apply this rule)
1. `quality_status == quality_hold` → `freeze_new_replenishment`
2. else if `severe_or_critical_count >= 2` → `buyer_review_required`
3. else → `monitor_only`

(The train exercised exactly these three suppliers: quality_hold→freeze, watch+severe≥2→buyer_review, watch+severe<2→monitor. The severe≥2 threshold is the clean differentiator. quality_hold always freezes regardless of severe count.)

### held_po_ids (per supplier)
Fetch `GET /purchase_orders?supplier_id=<sid>`. For `freeze_new_replenishment` or `buyer_review_required` suppliers: `held_po_ids` = the **first 5** open/confirmed PO ids sorted ascending by `po_id` (cap = **5**, analogous to the sample_incident_ids cap — confirmed: one train supplier had 11 open/confirmed POs but only 5 were held; another had 7 and 5 were held). For `monitor_only`: `held_po_ids = []` (released, no holds).
- Include POs with `status ∈ {open, confirmed}` only. Exclude `received` and `cancelled`.

### Top-level outputs
- `held_po_ids`: sorted unique union of all per-supplier `held_po_ids`.
- `release_supplier_ids`: sorted list of supplier_ids whose decision is `monitor_only`.
- `summary`: `suppliers_reviewed, freeze_count, buyer_review_count, monitor_count, held_po_count (= len(top-level held_po_ids)), total_recent_incidents (Σ recent_incident_count)`.

---

## 8. Common misjudgments & exclusion rules (do NOT do these)

- **Do NOT** compute effective stock as `on_hand − reserved − quarantined` only — you must also subtract `safety_stock` (from the product master, not the inventory record). All four terms.
- **Do NOT** subtract `safety_stock` twice or add it back. `effective_available = on_hand − reserved − quarantined − safety_stock`. Period.
- **Do NOT** apply account/risk overrides AFTER inventory. Account-blocked / review / fraud / credit blocks are checked FIRST and override inventory outcomes (a shortage order with `review_required` is `manual_review`, not `backorder`).
- **Do NOT** count received or cancelled POs as timely coverage. Timely PO = `status ∈ {open, confirmed}` AND `eta <= build_date` AND at the **target/ same** warehouse. A confirmed PO at a different warehouse does not cover the target warehouse.
- **Do NOT** count a timely PO at another warehouse as coverage for the planning warehouse — an open/confirmed PO sitting at WH_CENTRAL does not cover a target build at WH_WEST. The PO's `warehouse_id` must equal the target/planning warehouse.
- **Do NOT** exclude a component as overstock when it still has a gap. Overstock exclusion only applies when `target_effective_available >= total_required` (no gap); within that, use `overstock_threshold` to label `target_overstock` vs `stocked_no_gap`.
- **Do NOT** filter incidents by `close_date` — the date filter is on `open_date`.
- **Do NOT** list ALL open/confirmed POs as held in family E — there is a **cap of 5** per supplier (first 5 by `po_id` ascending); only freeze/buyer_review suppliers hold POs; monitor suppliers release.
- **Do NOT** put fraud_watch/credit_watch orders in `manual_review` for family A — they are holds (`reject_hold`/`hold_credit_or_fraud`). (In family D they collapse to `manual_review` because that family has no `reject_hold` action, but they still appear in `blocked_orders`.)
- **Do NOT** forget the shipping quote on backorder/reject orders — compute it for every order using the FULL order weight.
- **Do NOT** treat `target_effective_available` (family B) as net of `total_required` — it is the raw effective stock at the target warehouse.
- **Do NOT** reverse the replenishment transfer greedy order — pull from highest-effective warehouse first, capped at remaining gap.
- **Do NOT** forget `needed_by` date semantics in family B: transfers use the **earliest** build date; purchase requisitions use the **latest** build date for that SKU.
- **Recommendation precedence**: ESCALATE > PROCESS_REVIEW > WATCHLIST > MONITOR — assign the first match, do not let a lower code override a higher one even if its condition also holds.

---

## 9. Reusable solving SOP

1. **Read the prompt + every payload.** Identify the task family (expedite / replenishment / scorecard / allocation / quality-hold) and open `answer_template.json`. Note the required top-level keys, per-item keys, allowed enum values, and ordering rules.
2. **Probe the live API** (`/health` first) and fetch the master data you need: `/products` (build a sku→product map), `/suppliers`, `/warehouses`, and the task-specific records (`/orders?wave=`, `/incidents`, `/boms/<id>`, `/purchase_orders?...`).
3. **Apply the core formula** (effective stock = on_hand − reserved − quarantined − safety_stock) consistently. Always pull `safety_stock`, `weight_lb`, `unit_cost`, `active`, `overstock_threshold`, `supplier_id` from the product master.
4. **Apply precedence in the documented order** for that family (customer exception before inventory; recommendation code precedence; blocked-order before inactive-product before inventory; exclusion branches in order).
5. **Build the output object** matching the template's keys and enums exactly. Apply sorting. Round currency to 2 dp, percentages to 1 dp, durations to 2 dp.
6. **Self-check**: re-derive 2–3 records independently; verify summary totals equal the sum of the parts (decision_counts, total_shipping_cost, total_purchase_cost, total_recent_incidents, transfer/backorder units). Confirm no forbidden values (e.g. `reject_hold` only where account-blocked/credit/fraud; `manual_review` only where the rules allow).
7. **Return only the JSON** (no narrative), as the prompt requires.

### Transferable heuristics
- When a task gives specific order IDs in a memo, fetch each by `/orders/<id>` (don't rely on wave filtering alone).
- When an endpoint filter is uncertain (e.g. `/incidents?start=`), fetch broadly and filter client-side on the exact field (`open_date`).
- Preserve negative effective-available values in output — they are meaningful (stock committed beyond on-hand) and expected in the result.
- The `overstock_threshold` field distinguishes `target_overstock` from `stocked_no_gap`; both are "no replenishment needed" but labeled differently.
- "Sample" lists (`sample_incident_ids`, and empirically `held_po_ids` per supplier) are **capped at 5**, sorted ascending.
- Currency in the API is already 2 dp; computed extended costs may need explicit rounding — sum then round.
