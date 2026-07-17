# Northwind ERP Fulfillment — Solver Skill

Executable experience for solving Northwind Components ERP fulfillment tasks against the
shared remote API. Five recurring task families are covered. Apply the rules below at
test time; they were reverse-engineered from the live API and internal business
consistency (there are no gold answers to check against).

---

## 0. Environment & API Reference

**Base URL:** the URL given in the task's `environment_access.md` (a remote host, e.g.
`<remote-env-url>`). Tasks reference `http://127.0.0.1:8007` in prose, but the
REAL entrypoint is the remote base URL in `environment_access.md`. Always use that.

**Calling notes (critical):**
- The server speaks HTTP/1.0 and closes each connection. Use a fresh connection per call:
  `curl -sS --max-time 30 '<url>'` or Python `urllib.request` with `timeout=30`.
- All endpoints are GET. Parameters are query-string.
- Do NOT try to read `env/`, `server.py`, data files, or start a local server. Only the API.

**Endpoints:**
| Endpoint | Returns | Notes |
|---|---|---|
| `GET /health` | manifest (record counts, seed) + status | sanity check first |
| `GET /products` , `/products/<sku>` | SKU master | `active`, `safety_stock`, `overstock_threshold`, `unit_cost`, `weight_lb`, `supplier_id`, `category` |
| `GET /customers` , `/customers/<id>` | account/risk | `account_status`∈{active,blocked,review_required}, `risk_flag`∈{none,fraud_watch,credit_watch}, `tier` |
| `GET /warehouses` | `warehouse_id`∈{WH_NORTH,WH_CENTRAL,WH_WEST}, `zip`, `region` | 3 warehouses |
| `GET /inventory?warehouse_id=&sku=` | stock row | `on_hand`, `reserved`, `quarantined`, `last_count_date` |
| `GET /purchase_orders?supplier_id=&sku=&status=` | POs | `status`∈{open,confirmed,received,cancelled}, `eta`, `quantity`, `warehouse_id`, `supplier_id` |
| `GET /orders?wave=&required_date=&customer_id=` , `/orders/<id>` | orders | `wave`, `warehouse_id`, `customer_id`, `destination_zip`, `shipping_speed`∈{ground,two_day,overnight}, `lines[]`{line_id,sku,quantity,unit_price} |
| `GET /shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=` | quote | `zone_distance`, `service_days`, `total_cost` (USD, 2dp), also `base_rate`,`fuel_surcharge_rate` |
| `GET /incidents?start=&end=&supplier_id=&sku=&incident_type=&status=` | incidents | `open_date`,`close_date`(null if open),`incident_type`∈{RMA,WORK_ORDER},`severity`∈{low,medium,high,critical},`status`∈{open,closed},`resolution_cost`,`supplier_id`,`sku`,`warehouse_id` |
| `GET /suppliers` | suppliers | `supplier_id`, `name`, `quality_status`∈{approved,watch,quality_hold}, `region` |
| `GET /boms` , `/boms/<id>` | BOMs | `bom_id`, `name`, `warehouse_id`, `target_date`, `components[]`{sku, quantity_per_kit} |

**Data scale (manifest seed 7007):** 54 products, 40 customers, 3 warehouses, 9 BOMs,
92 POs, 88 orders, 162 inventory rows, 212 incidents, 12 suppliers.

**SOP: pull-and-cache.** At the start of any task, fetch `/products`, `/customers`,
`/inventory`, `/purchase_orders`, `/suppliers`, `/boms` once and index them in memory
(dict by sku / customer_id / (warehouse_id,sku) / supplier_id / bom_id). Then fetch only
the task-specific orders. This minimizes round-trips (server closes connections).

---

## 1. Core Business Primitives (used by ALL task families)

### 1.1 Effective available stock
```
effective_available = on_hand - reserved - quarantined
```
- `on_hand`, `reserved`, `quarantined` come from `/inventory` for a (warehouse_id, sku).
- Reserved and quarantined units are NOT freely shippable. Always subtract both.
- `effective_available` can be NEGATIVE (e.g. on_hand=0, quarantined=1 → -1). Treat
  negative as 0 usable when computing shippable quantity, but REPORT the raw value where a
  field asks for "effective available" / "requested_effective_available".

### 1.2 Safety stock & overstock threshold (from /products)
- `safety_stock`: protected buffer. A warehouse's **spare** (donatable) stock =
  `effective_available - safety_stock`. Only POSITIVE spare can be transferred/donated.
- `overstock_threshold`: if a warehouse's effective_available EXCEEDS this, the SKU is
  OVERSTOCKED there → do NOT add more stock (exclusion). Used in BOM replenishment.

### 1.3 Product active flag
- `active: false` means the SKU is discontinued/inactive. Inactive SKUs cannot be
  auto-shipped or replenished regardless of on-hand quantity — they force a manual review
  (escalate to product master) in dispatch tasks, and block transfer/ship in allocation.
- Known inactive SKUs in this dataset: NW-1007, NW-1019, NW-1033, NW-1048 (4 total). Always
  check `active` per SKU; do not assume.

### 1.4 Customer/account exception precedence
Derived from `account_status` + `risk_flag`:
| account_status | risk_flag | customer_exception |
|---|---|---|
| blocked | (any) | **account_blocked** |
| review_required | (any) | **review_required** |
| active | fraud_watch | **fraud_watch** |
| active | credit_watch | **credit_watch** |
| active | none | **none** |

Precedence (most severe first): account_blocked > fraud_watch > credit_watch > review_required > none.
`account_status` drives blocked/review; `risk_flag` only matters when `account_status == active`

### 1.5 Shipping quote computation
```
weight_lb = sum over ALL order lines of (product.weight_lb * line.quantity)
quote = GET /shipping/quote?warehouse_id=<order.warehouse_id>
                        &destination_zip=<order.destination_zip>
                        &weight_lb=<computed weight>
                        &speed=<order.shipping_speed>
```
- Use the ORDER's own `shipping_speed` (ground / two_day / overnight), even if the order
  is not going to be released. Quotes are required for every order in the queue/memo.
- The API returns `total_cost` (already 2dp), `service_days` (int), `zone_distance` (int).
- Sum `total_cost` across all records for the summary `total_shipping_cost_usd`.

### 1.6 Timely purchase-order coverage
A PO is **eligible / timely** for a build/need at warehouse W with deadline D iff:
- `status` ∈ {open, confirmed}  (NOT received, NOT cancelled)
- `warehouse_id == W` (same warehouse as the build)
- `eta <= D` (arrival on or before the build/need date)
- `received` POs are EXCLUDED — their stock is already inside `on_hand` (would double-count).
- `timely_po_qty` = sum of `quantity` over all eligible POs for that SKU at that warehouse
  (report the full eligible PO quantity, do NOT cap to the gap).

### 1.7 Rounding & formatting
- Currency (USD): round to 2 decimals everywhere (`round(x, 2)`).
- Percentages (incident share): round to 1 decimal.
- Durations (days): round to 2 decimals.
- Counts/quantities: integers.
- Lists of IDs/SKUs: sorted ascending (strings sort lexicographically — "NW-1003" < "NW-1011" < "NW-1049").
- Always keep records sorted by the field the template names (usually order_id / sku / supplier_id ascending).

---

## 2. Task Family A — Expedite Queue Dispatch (wave decision)

**Inputs:** a queue memo listing `order_ids` + `wave_id`. **Output:** records (per order) +
summary. See the answer_template for exact keys: `wave_id`, `records[]`, `summary{}`.

### 2.1 Per-order computation
For each order (sorted ascending by order_id):
1. Fetch `/orders/<order_id>`. Note `customer_id`, `warehouse_id`, `destination_zip`,
   `shipping_speed`, `lines[]`.
2. **Customer exception:** look up customer, apply §1.4 table.
3. **Per-line classification** (for each line: sku, quantity):
   - product = `/products/<sku>`; inventory = `/inventory?warehouse_id=<wh>&sku=<sku>`
   - `eff = on_hand - reserved - quarantined`
   - shortage line if `eff < quantity` → add sku to `shortage_skus`
   - inactive line if `product.active == false` → add sku to `inactive_skus`
   - low_stock line if `quantity <= eff < product.safety_stock` (can fill but below
     safety buffer) → add sku to `low_stock_skus`
     (a shortage line is NOT also low_stock; low_stock requires eff >= quantity)
4. **inventory_status** (order rollup, in this priority):
   - has inactive SKU AND has shortage → `inactive_and_shortage`
   - has inactive SKU (no shortage) → `inactive_sku`
   - has shortage (no inactive) → `shortage`
   - has any low_stock (no inactive, no shortage) → `low_stock`
   - else → `ready`
5. **final_decision + next_action** — apply the PRECEDENCE LADDER (first match wins):
   | Priority | Condition | final_decision | next_action |
   |---|---|---|---|
   | 1 | customer_exception == account_blocked | `reject_hold` | `hold_credit_or_fraud` |
   | 2 | inventory_status in {inactive_sku, inactive_and_shortage} | `manual_review` | `escalate_product_master` |
   | 3 | customer_exception == fraud_watch | `manual_review` | `hold_credit_or_fraud` |
   | 4 | customer_exception == credit_watch | `manual_review` | `hold_credit_or_fraud` |
   | 5 | customer_exception == review_required | `manual_review` | `send_account_review` |
   | 6 | inventory_status == shortage | `backorder` | `create_backorder` |
   | 7 | inventory_status == low_stock | `delayed_release` | `delay_and_monitor` |
   | 8 | inventory_status == ready | `ship_now` | `release_to_pick` |
   - Account/risk/product issues (manual_review / reject_hold) take PRECEDENCE over
     inventory issues (backorder / delayed_release). Rationale: an order under account
     review or with a discontinued product cannot be released regardless of stock.
   - The inactive-product rung (escalate_product_master) sits ABOVE the account-review
     rung: when both an inactive product and a review_required account are present, the
     next_action is escalate_product_master (product-master risk is the primary blocker).
6. **shipping_quote:** compute per §1.5, store `{zone_distance, service_days, total_cost_usd}`.
7. SKU exception lists: `shortage_skus`, `inactive_skus`, `low_stock_skus` — each sorted
   ascending, only the SKUs that qualify (empty list `[]` if none).

### 2.2 Summary
- `order_count`: number of records.
- `decision_counts`: object keyed by the 5 final_decision values → integer counts
  (include all 5 keys even if 0).
- `total_shipping_cost_usd`: sum of every record's `shipping_quote.total_cost_usd`, 2dp.
- `blocked_order_ids`: orders with final_decision == reject_hold, sorted.
- `manual_review_order_ids`: final_decision == manual_review, sorted.
- `backorder_order_ids`: final_decision == backorder, sorted.
- `inactive_sku_order_ids`: orders whose inventory_status is inactive_sku OR
  inactive_and_shortage (i.e. any inactive SKU present), sorted.

### 2.3 Common misjudgments (Family A)
- Forgetting that `review_required`/`fraud_watch`/`credit_watch` BLOCK release even when
  stock is plentiful → wrongly shipping instead of manual_review.
- Putting a low_stock SKU into shortage_skus (it must have eff >= quantity to be low_stock).
- Computing shipping weight with only some lines — use ALL lines, and multiply
  weight_lb by quantity per line.
- Letting a shortage override an inactive product or account review — inventory NEVER
  overrides account/product manual-review conditions in this family.

---

## 3. Task Family B — Kit Build Replenishment (BOM expansion)

**Inputs:** a production memo with `target_builds[]` (bom_id, target_build_quantity,
target_build_date) at a planning warehouse. **Output:** `task_id`, `plan_date`,
`kit_targets[]`, `component_plan[]`, `transfer_requests[]`, `purchase_requisitions[]`,
`excluded_components[]`, `summary{}`.

### 3.1 BOM expansion → total_required
- For each build: fetch `/boms/<bom_id>`. For each component `{sku, quantity_per_kit}`:
  `component_required = quantity_per_kit * target_build_quantity`.
- A SKU appearing in multiple BOMs: **sum** its requirements across all builds.
- `total_required[sku]` = summed requirement.
- Each SKU's relevant **build date** = the EARLIEST `target_build_date` among the BOMs
  that contain it (stock must be on hand by the first build that needs it). Use this date
  as the need deadline for timely-PO and needed_by.

### 3.2 Per-component plan (one row per SKU, sorted by sku ascending)
For each SKU in total_required:
1. `target_effective_available` = effective_available at the planning warehouse (§1.1).
2. `timely_po_qty` = sum of eligible PO qty (§1.6) at the planning warehouse with
   `eta <= earliest_build_date`.
3. `stock_gap = total_required - target_effective_available`
4. Determine **exclusion / final_action** in this priority:
   | Priority | Condition | exclusion_reason | final_action |
   |---|---|---|---|
   | 1 | target_effective_available > product.overstock_threshold | `target_overstock` | `overstock_excluded` |
   | 2 | stock_gap > 0 AND timely_po_qty >= stock_gap | `timely_po_covers_gap` | `timely_po_covered` |
   | 3 | stock_gap <= 0 (stock already covers, not overstock) | `stocked_no_gap` | `no_action_stocked` |
   | 4 | stock_gap - timely_po_qty > 0 (real remaining gap) | `none` | (transfer/purchase, see 3.3) |
   - `coverage_po_ids`: for the timely case, the eligible PO ids (sorted). Empty list
     otherwise (including overstock — overstock exclusion has no coverage POs).
   - Report `transfer_qty = 0` and `purchase_requisition_qty = 0` for all excluded rows.

### 3.3 Filling a real remaining gap (exclusion_reason == none)
```
remaining_gap = stock_gap - timely_po_qty     # > 0
spare[other_wh] = effective_available(other_wh) - product.safety_stock   # only if > 0
```
- Draw transfers from OTHER warehouses' positive spare. Take from the warehouse with the
  LARGEST spare first; if one warehouse's spare already covers `remaining_gap`, take only
  what's needed from that single warehouse; otherwise exhaust the largest, then the next,
  until the gap is filled or all spare is used.
- `transfer_qty = min(remaining_gap, sum_of_all_positive_spare)`
- `purchase_requisition_qty = remaining_gap - transfer_qty`
- `final_action`: if `purchase_requisition_qty > 0` → `purchase_required`;
  elif `transfer_qty > 0` → `transfer_only`.
- Each transfer draw becomes a `transfer_requests` row: `{sku, from_warehouse_id,
  to_warehouse_id=<planning warehouse>, quantity, needed_by=<earliest build date>}`.

### 3.4 transfer_requests (list)
Sorted by: sku ascending, then quantity descending, then from_warehouse_id ascending.
So within one SKU, the biggest transfer batch is listed first.

### 3.5 purchase_requisitions (list)
One row per SKU that needs purchasing (purchase_requisition_qty > 0), sorted by sku ascending.
- `supplier_id`: from `product.supplier_id`.
- `warehouse_id`: the planning warehouse.
- `quantity`: purchase_requisition_qty.
- `needed_by`: earliest build date for that SKU.
- `unit_cost`: `product.unit_cost` (2dp).
- `extended_cost = quantity * unit_cost` (2dp).

### 3.6 excluded_components (list)
One row per SKU whose exclusion_reason != none, sorted by sku ascending.
- `reason`: target_overstock | timely_po_covers_gap | stocked_no_gap (matches exclusion_reason).
- `supporting_po_ids`: for timely_po_covers_gap → the coverage PO ids (sorted); for
  target_overstock and stocked_no_gap → empty list `[]`.

### 3.7 kit_targets (list)
Sorted by bom_id ascending. Each: `{bom_id, kit_name (from BOM .name), warehouse_id
(planning warehouse), build_quantity, build_date}`.

### 3.8 summary
- `component_count`: number of rows in component_plan.
- `total_purchase_units`: sum of purchase_requisition_qty.
- `total_purchase_cost`: sum of extended_cost (2dp).
- `total_transfer_units`: sum of transfer_qty across all components.
- `timely_po_covered_units`: sum of `timely_po_qty` across all components (the full
  eligible PO quantities, not capped to gaps).

### 3.9 plan_date
Use the memo's `issued_at` date portion (YYYY-MM-DD), or an `as_of_date`/planning date if
the memo provides one.

### 3.10 Common misjudgments (Family B)
- Counting `received` POs as timely coverage (they're already in on_hand → double count).
- Using the LATEST build date for timeliness on a multi-BOM component — use the EARLIEST.
- Forgetting overstock exclusion takes precedence over stocked_no-gap when
  effective > overstock_threshold AND effective >= required.
- Drawing transfer from a warehouse whose spare is negative (below its own safety stock).
- Splitting a transfer across extra warehouses when one warehouse's spare already covers
  the gap (take from the single largest-spare source).
- Capping timely_po_qty to the gap — report the full eligible PO quantity.

---

## 4. Task Family C — Supplier Incident Scorecard

**Inputs:** a scorecard request with an `incident_date_filter` (field=open_date,
start/end inclusive), `analysis_date`, duration/percentage/recommendation rules.
**Output:** `analysis_window`, `summary`, `supplier_scorecard[]`, `top_escalation_suppliers`,
`highest_cost_supplier_id`, `highest_share_supplier_id`.

### 4.1 Filter the incident population
- Filter `/incidents` by `open_date` within [start_date, end_date] INCLUSIVE.
- The filter field is `open_date` (NOT close_date, NOT a created_at). Confirmed by the
  request's `incident_date_filter.field`.
- `total_filtered = len(filtered)`.

### 4.2 Per-supplier rollup (only suppliers with >= 1 filtered incident)
For each such supplier (sorted by supplier_id ascending):
- `incident_count`: count of that supplier's filtered incidents.
- `incident_percentage`: `incident_count / total_filtered * 100`, rounded to 1 decimal.
- `total_resolution_cost`: sum of `resolution_cost`, 2dp.
- `rma_count`: filtered incidents with `incident_type == RMA`.
- `work_order_count`: filtered incidents with `incident_type == WORK_ORDER`.
- `open_incident_count`: filtered incidents with `status == open`.
- `severe_incident_count`: filtered incidents with `severity in {high, critical}`.
- `avg_duration_days`:
  - closed incident → calendar days from `open_date` to `close_date`.
  - open incident (close_date null) → calendar days from `open_date` to `analysis_date`.
  - average over the supplier's filtered incidents, rounded to 2 decimals.
- `supplier_name`: from `/suppliers`.
- `recommendation_code`: see §4.3.

### 4.3 Recommendation code (precedence: ESCALATE > PROCESS_REVIEW > WATCHLIST > MONITOR)
Evaluate top-down; assign the first matching code.
- **ESCALATE_SUPPLIER** — supplier `quality_status == quality_hold` AND `incident_count >= 3`,
  OR supplier has any critical-severity RMA incident (`incident_type==RMA` AND
  `severity==critical`), OR (`rma_count >= 3` AND `total_resolution_cost >= 15000.00`).
- **PROCESS_REVIEW** — `work_order_count >= 3` AND `work_order_count > rma_count`.
- **WATCHLIST** — `quality_status in {watch, quality_hold}`, OR `incident_count >= 4`,
  OR `total_resolution_cost >= 12000.00`, OR `severe_incident_count >= 2`.
- **MONITOR** — none of the above.

NOTE: thresholds (3, 15000, 12000, 4, 2) and the severe set {high,critical} come from the
request's `recommendation_policy`. If a future request changes them, read and apply the
request's stated values, not these constants.

### 4.4 Derived outputs
- `top_escalation_suppliers`: supplier_id list where recommendation_code ==
  ESCALATE_SUPPLIER, ordered by incident_count DESC, then total_resolution_cost DESC,
  then supplier_id ASC.
- `highest_cost_supplier_id`: supplier_id with the max total_resolution_cost (ties →
  supplier_id ascending).
- `highest_share_supplier_id`: supplier_id with the max incident_count (ties → max cost,
  then supplier_id ascending).

### 4.5 analysis_window
`{start_date, end_date, analysis_date}` from the request (YYYY-MM-DD).

### 4.6 summary
- `filtered_incident_count`: total_filtered.
- `supplier_count`: number of suppliers with >= 1 filtered incident.
- `total_resolution_cost`: sum across ALL filtered incidents, 2dp.
- `overall_rma_count`: RMA incidents in the filtered population.
- `overall_work_order_count`: WORK_ORDER incidents in the filtered population.

### 4.7 Common misjudgments (Family C)
- Filtering on close_date or created_at instead of open_date.
- Computing open-incident duration to today instead of to `analysis_date`.
- Wrong precedence: applying WATCHLIST before ESCALATE/SUPPLIER checks, or checking
  PROCESS_REVIEW before ESCALATE. The policy precedence is ESCALATE > PROCESS_REVIEW >
  WATCHLIST > MONITOR — evaluate strictly in that order.
- Forgetting that quality_hold + >=3 incidents triggers ESCALATE even without critical
  RMAs or cost thresholds.
- Rounding percentage to 2 decimals (use 1) or duration to 0/1 (use 2).

---

## 5. Task Family D — Mixed-Warehouse Allocation / Transfer Wave

**Inputs:** an allocation memo naming a wave (e.g. TRAIN_TRANSFER_B). **Output:**
`wave_id`, `line_actions[]`, `transfer_requests[]`, `blocked_orders[]`, `order_rollup[]`,
`summary{}`.

### 5.1 Per-line action (sorted by order_id, then line_id ascending)
For each order in the wave, for each line:
1. **Account-level gate (applies to the WHOLE order):**
   - `account_status == blocked` → action `manual_review`, primary_reason `account_blocked`,
     all quantities 0.
   - `account_status == review_required` → `manual_review`, `account_review_required`, 0s.
   - `account_status == active` and `risk_flag == fraud_watch` → `manual_review`,
     `fraud_watch`, 0s.
   - (active + credit_watch: not exercised in train data. Treat as a manual_review risk
     gate consistent with Family A — reason: account_review_required — but verify if a
     test task exposes it.)
   These account gates apply to EVERY line of the order (the whole order is stopped).
2. **Product gate (per line):** if `product.active == false` → `manual_review`,
   `inactive_product`, 0s. (Only reached when the account is clean.)
3. **Inventory decision (account & product clean):**
   - `eff = effective_available` at the line's `requested_warehouse` for the sku.
   - `usable = max(0, eff)`.
   - if `eff >= quantity`: action `ship`, ship_quantity=quantity, primary_reason `none`.
   - else (shortfall): `gap = quantity - usable`. Look for ONE other warehouse whose
     **spare** (`effective_available - safety_stock`, §1.2) is `>= gap`. If found →
     action `transfer`: ship_quantity=usable, transfer_from=that warehouse,
     transfer_quantity=gap, backorder=0. Choose the warehouse with the LARGEST spare
     (ties → warehouse_id alphabetical). Only ONE source warehouse per line ("choose one
     source warehouse").
   - if no single warehouse can cover the full gap → action `backorder`:
     ship_quantity=usable (ship what's available), backorder_quantity=`quantity - usable`,
     primary_reason `insufficient_effective_stock`, transfer 0.
     (Symmetric with transfer: the usable requested-warehouse stock ships; the uncovered
     remainder is backordered. The explicit "leave usable as ship_quantity" instruction in
     the memo covers transfer; apply the same usable-ship convention to backorder.)
4. `requested_effective_available` field: report the raw `eff` (may be negative).

### 5.2 transfer_requests (list)
One row per transfer line, with `{order_id, line_id, sku, from_warehouse, to_warehouse,
quantity}`. Sorted by order_id, then line_id ascending.

### 5.3 blocked_orders (list of order_id strings)
Orders stopped at the ACCOUNT or customer-RISK level (blocked / review_required /
fraud_watch) — NOT orders stopped only by inactive-product lines. Sorted ascending.
Rationale (template meaning): "Orders stopped at account or customer-risk level, not
line-only product reviews."

### 5.4 order_rollup (list, sorted by order_id)
Outcome per order (based on the set of its line actions):
- all lines `ship` → `ready_to_ship`
- all lines `transfer` → `needs_transfer`
- all lines `backorder` → `has_backorder`
- all lines `manual_review` → `manual_review`
- any mix of different actions → `mixed_actions`

### 5.5 summary (all integers)
`total_orders`, `total_lines`, `ship_lines`, `transfer_lines`, `backorder_lines`,
`manual_review_lines` (counts of lines by action), `blocked_orders` (count of blocked
order ids), `transfer_units` (sum of transfer_quantity), `backorder_units` (sum of
backorder_quantity).

### 5.6 Common misjudgments (Family D)
- Classifying an inactive-product line as `ship`/`backorder` because stock exists —
  inactive products are ALWAYS manual_review.
- Putting inactive-product-only orders into `blocked_orders` — they are line-level product
  reviews, not account/risk stops. Only account/risk-stopped orders belong there.
- Allowing a transfer from a warehouse whose spare is below zero (ignoring its own safety
  stock) — spare must be positive AND cover the full gap.
- Splitting one line's shortfall across multiple source warehouses — only ONE source per
  line; if no single source covers the full gap, the line is backorder.
- Forgetting that account-level gates (blocked/review/fraud) stop ALL lines of an order,
  including lines that would otherwise ship.
- Reporting `requested_effective_available` as 0 when it is negative — report the raw
  computed value.

---

## 6. Task Family E — Procurement Quality-Hold Review

**Inputs:** a memo with `analysis_window`{start,end}, `target_supplier_ids[]`, policy.
**Output:** `analysis_window`, `supplier_decisions[]`, `held_po_ids`, `release_supplier_ids`,
`summary{}`.

### 6.1 Per-supplier decision (sorted by supplier_id ascending)
For each target supplier, fetch its incidents filtered by `open_date` within
[window.start, window.end] inclusive, and its POs:
- `recent_incident_count`: count of filtered incidents.
- `recent_rma_count`: filtered incidents with `incident_type == RMA`.
- `severe_or_critical_count`: filtered incidents with `severity in {high, critical}`.
- `open_incident_count`: filtered incidents with `status == open`.
- `affected_skus`: sorted unique SKUs from the filtered incidents.
- `sample_incident_ids`: sorted incident_ids, capped at 5 (the first 5 when sorted
  ascending).
- `quality_status`: from `/suppliers`.
- `held_po_ids`: the supplier's open/confirmed PO ids that are HELD (see §6.3), sorted.

### 6.2 Decision policy (inferred — apply top-down)
- **freeze_new_replenishment** — `quality_status == quality_hold`. (The hold itself freezes
  all replenishment.) Hold ALL open/confirmed POs.
- **buyer_review_required** — NOT quality_hold, but elevated risk: has at least one
  CRITICAL-severity incident in the window, OR `open_incident_count >= 1`. Hold ALL
  open/confirmed POs pending buyer review.
- **monitor_only** — otherwise (no critical incident and no open incident). No PO holds;
  release proceeds.

Result: a clean three-way split. `release_supplier_ids` = suppliers whose decision is
monitor_only (sorted).

NOTE: this policy is reverse-engineered. If a test memo states explicit thresholds, use
those instead. The signal that matters most: quality_hold → freeze; critical or open
recent incident → buyer_review; otherwise monitor. Severe-but-closed (high, closed)
incidents alone trend toward monitor, not buyer_review, in this framing.

### 6.3 held_po_ids
- For `freeze_new_replenishment` and `buyer_review_required` suppliers: hold ALL of the
  supplier's open/confirmed POs (every PO with `status in {open, confirmed}`,
  regardless of SKU, regardless of eta/warehouse). Sorted unique.
  (Rationale: both decisions halt automatic PO release — freeze stops everything, buyer
  review holds pending the buyer's decision. Only monitor_only releases.)
  Alternative reading: only freeze holds POs, buyer_review holds none. If a test task's
  numbers seem off, re-evaluate whether buyer_review holds. The conservative default here
  is to hold for both freeze and buyer_review.
- For `monitor_only`: held_po_ids = `[]`.

### 6.4 held_po_ids (top-level)
Sorted unique union of every supplier's held_po_ids (the distinct set of all held PO ids).

### 6.5 summary
- `suppliers_reviewed`: count of target suppliers.
- `freeze_count`, `buyer_review_count`, `monitor_count`: counts by decision.
- `held_po_count`: length of the top-level held_po_ids list.
- `total_recent_incidents`: sum of recent_incident_count across reviewed suppliers.

### 6.6 analysis_window
`{start, end}` (YYYY-MM-DD) from the memo.

### 6.7 Common misjudgments (Family E)
- Filtering incidents by close_date or by a different field instead of open_date.
- Counting received/cancelled POs as held (only open/confirmed are held).
- Holding POs for monitor_only suppliers (they are released).
- Not capping sample_incident_ids at 5.
- Using POs for ALL suppliers in top-level held_po_ids instead of only reviewed suppliers'
  held POs.

---

## 7. Cross-Cutting Reusable SOPs

1. **Read the answer_template FIRST.** It defines exact key names, allowed enum values,
   ordering, and types. Match them verbatim — a valid enum string spelled differently or a
   missing key fails. Re-read it before emitting JSON.

2. **Pull + cache core entities** (§0) before per-task logic. Index by natural key.

3. **Effective stock is always `on_hand - reserved - quarantined`.** Never use on_hand
   alone. Never ignore quarantined. Report raw (can be negative); use max(0,·) for shippable.

4. **Check product.active and customer account_status/risk_flag before inventory.**
   Account and product gates precede inventory logic in Families A and D.

5. **Spare = effective - safety_stock; only positive spare donates.** A warehouse below
   its own safety stock cannot be a transfer source.

6. **POs: only open/confirmed are future supply; received is already in on_hand.**
   Timely = open/confirmed + same warehouse + eta <= deadline.

7. **One source warehouse per transfer line** (Family D). All eligible sources for Family B
   can combine (multiple transfer_requests rows), drawing largest-spare first.

8. **Incident filtering is on open_date, inclusive** of both endpoints.

9. **Sort everything as the template dictates.** Default ascending by the natural id
   (order_id / sku / supplier_id / bom_id). For multi-key sort, follow the template's
   stated tie-breakers exactly.

10. **Round: currency 2dp, percentage 1dp, duration 2dp.** Quantities/counts are integers.

11. **Emit ONLY the JSON object** (no narrative, no markdown fences) unless the prompt
    explicitly allows text. Match the template's top-level key set exactly.

12. **Sanity-check internally:** sums in the summary must reconcile with the line/record
    lists (e.g. total_shipping_cost = sum of quotes; decision_counts sum to order_count;
    ship+transfer+backorder+manual_review lines = total_lines). Reconciliation is the only
    correctness signal available (no gold/judge).

13. **Dates:** parse as YYYY-MM-DD. Calendar-day differences use date subtraction
    (later - earlier).days. Inclusive range means `start <= d <= end`.

14. **Wave filtering:** `GET /orders?wave=<WAVE_ID>` returns exactly that wave's orders.
    For expedite/allocation tasks, this is the order set.

---

## 8. Quick Reference — Decision Precedence Summaries

**Family A (expedite) final_decision ladder:**
account_blocked→reject_hold ▸ inactive_sku→manual_review(escalate) ▸
fraud_watch→manual_review(hold) ▸ credit_watch→manual_review(hold) ▸
review_required→manual_review(account_review) ▸ shortage→backorder ▸
low_stock→delayed_release ▸ ready→ship_now.

**Family B (BOM) component resolution:**
overstock(exclusion) ▸ timely_po_covers(exclusion) ▸ stocked_no_gap(exclusion) ▸
[remaining gap] → transfer from largest spare, then purchase the rest.

**Family C (scorecard) recommendation:**
ESCALATE(buyback) ▸ PROCESS_REVIEW ▸ WATCHLIST ▸ MONITOR.

**Family D (allocation) line action:**
account_blocked ▸ review_required ▸ fraud_watch ▸ inactive_product ▸
ship(eff>=qty) ▸ transfer(one source covers gap) ▸ backorder(no source covers gap).

**Family E (procurement):**
quality_hold→freeze ▸ critical-or-open incident→buyer_review ▸ else→monitor.

---

## 9. Field-Shapes Cheat Sheet (per family)

- **A records:** `{order_id, inventory_status, customer_exception, final_decision,
  next_action, shortage_skus[], inactive_skus[], low_stock_skus[], shipping_quote{zone_distance,service_days,total_cost_usd}}`
  + `summary{order_count, decision_counts{...}, total_shipping_cost_usd, blocked_order_ids[], manual_review_order_ids[], backorder_order_ids[], inactive_sku_order_ids[]}`.

- **B:** `{task_id, plan_date, kit_targets[], component_plan[], transfer_requests[],
  purchase_requisitions[], excluded_components[], summary{}}`.
  component_plan row: `{sku, total_required, target_effective_available, timely_po_qty,
  transfer_qty, purchase_requisition_qty, final_action, coverage_po_ids[], exclusion_reason}`.

- **C:** `{analysis_window, summary{}, supplier_scorecard[], top_escalation_suppliers[],
  highest_cost_supplier_id, highest_share_supplier_id}`.

- **D:** `{wave_id, line_actions[], transfer_requests[], blocked_orders[],
  order_rollup[], summary{}}`.
  line_action row: `{order_id, line_id, sku, requested_warehouse, requested_effective_available,
  action, ship_quantity, transfer_from(nullable), transfer_quantity, backorder_quantity, primary_reason}`.

- **E:** `{analysis_window, supplier_decisions[], held_po_ids[], release_supplier_ids[], summary{}}`.
  supplier_decision row: `{supplier_id, supplier_name, quality_status, recent_incident_count,
  recent_rma_count, severe_or_critical_count, open_incident_count, affected_skus[],
  sample_incident_ids[], decision, held_po_ids[]}`.

---

*End of skill. Apply the rules; reconcile summary totals against record lists; emit only
the JSON object matching the template.*
