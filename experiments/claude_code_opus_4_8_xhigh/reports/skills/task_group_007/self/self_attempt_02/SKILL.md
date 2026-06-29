# SKILL: Northwind Components ERP — Inventory / Order-Fulfillment Operations

Transferable, executable playbook for the Northwind Components ERP benchmark
(inventory status, order release, allocation/transfer, replenishment, supplier
incident scorecards, quality-hold control). Built from working the live API.

---

## 0. REMOTE API — how to use it

Base URL (ALWAYS use this; ignore any "127.0.0.1:8007" or local-env mention in
task prompts — those are stale):

    <remote-env-url>

GET endpoints (all JSON):
- `/health` — manifest, record counts, seed.
- `/products`  `/products/<sku>` — product master.
- `/customers`  `/customers/<customer_id>` — account/risk master.
- `/suppliers` — supplier master (incl. `quality_status`).
- `/warehouses` — 3 warehouses: WH_NORTH (07102), WH_CENTRAL (60607), WH_WEST (89502).
- `/inventory?warehouse_id=&sku=` — stock rows.
- `/purchase_orders?supplier_id=&sku=&status=` — POs. status ∈ open|confirmed|received|cancelled.
- `/orders?wave=&required_date=&customer_id=`  `/orders/<order_id>` — sales orders.
- `/shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=` — speed ∈ ground|two_day|overnight.
- `/incidents?start=&end=&supplier_id=&sku=&incident_type=&status=` — quality incidents.
- `/boms`  `/boms/<bom_id>` — kit bills of material.

All listed query params work as filters and compose (AND). Always pull a wave with
`/orders?wave=WAVE_ID` and fetch `/orders/<id>` only if you need a single record.

### Key record fields
- **product**: `sku, name, category, active(bool), safety_stock(int), overstock_threshold(int), unit_cost, weight_lb, supplier_id`
- **customer**: `customer_id, name, account_status(active|review_required|blocked), risk_flag(none|credit_watch|fraud_watch), tier(strategic|standard|economy), margin_band`
- **inventory**: `warehouse_id, sku, on_hand, reserved, quarantined, last_count_date`
- **purchase_order**: `po_id, supplier_id, sku, warehouse_id, quantity, status, eta`
- **order**: `order_id, customer_id, warehouse_id, destination_zip, shipping_speed, required_date, priority, wave, lines[{line_id, sku, quantity, unit_price}]`
- **incident**: `incident_id, supplier_id, sku, warehouse_id, incident_type(RMA|WORK_ORDER), severity(low|medium|high|critical), status(open|closed), open_date, close_date(nullable), resolution_cost, root_cause`
- **bom**: `bom_id, name, warehouse_id, target_date, components[{sku, quantity_per_kit}]`

---

## 1. CORE FORMULAS (memorize — used everywhere)

**Effective available** (the only "freely usable" quantity; reserved + quarantined
are protected and NOT available):

    effective_available = on_hand - reserved - quarantined

If no inventory row exists for (warehouse, sku), treat effective_available = 0.
Effective available can be negative; clamp ship quantities at 0 (never ship < 0).

**Transferable surplus** from a *source* warehouse (do not dip into safety stock):

    transfer_surplus(src, sku) = effective_available(src, sku) - safety_stock(sku)

Only positive surplus is movable. Safety stock and quarantine/reserved are protected.

**Shipping quote** — call the API; it returns the answer directly. Do NOT recompute.
The endpoint internally uses
`base_rate = 8.75 + 3.40*zone_distance + 1.18*weight_lb`, then
`total_cost = base_rate * speed_mult * (1 + fuel_surcharge_rate)` with
speed_mult ground=1.0, two_day=1.75, overnight=2.65 and fuel_surcharge_rate≈0.0925.
You only need to: compute the order's total weight, hit the endpoint, and copy
`zone_distance`(int), `service_days`(int), `total_cost`(→`total_cost_usd`, 2 dp).

    order_weight_lb = sum(product.weight_lb * line.quantity) over ALL order lines

Quote per order using the order's own `warehouse_id`, `destination_zip`, total
weight, and the order's `shipping_speed` (unless a memo names a specific speed).

---

## 2. INVENTORY STATUS CLASSIFICATION (per order, rolled up from lines)

Classify each line, then roll the order up by the precedence below.

Per line at the order's requested warehouse:
- **shortage** if line is active but `effective_available < quantity`.
- **inactive** if `product.active == false` (a product-master problem).
- **low_stock** if active and ships fully (`effective_available >= quantity`) but
  `effective_available < safety_stock` (stock already below safety buffer).
- otherwise **ready**.

A single line can be BOTH inactive and short (inactive product whose eff_avail <
quantity) → it goes in both lists.

Order-level `inventory_status` enum precedence (highest first):
1. `inactive_and_shortage` — any inactive SKU AND any shortage SKU present.
2. `inactive_sku` — any inactive SKU (no shortage).
3. `shortage` — any shortage SKU.
4. `low_stock` — any low-stock SKU.
5. `ready` — none of the above.

Per-order SKU lists (each sorted ascending):
- `shortage_skus` = active SKUs with eff_avail < qty (plus inactive-and-short SKUs).
- `inactive_skus` = SKUs whose product.active is false.
- `low_stock_skus` = active, fully-shippable SKUs with eff_avail < safety_stock.

---

## 3. CUSTOMER EXCEPTION CLASSIFICATION

From the customer master. `customer_exception` enum, precedence (highest first):
1. `account_blocked` — `account_status == blocked` (HARD stop, beats any risk flag).
2. `fraud_watch` — `risk_flag == fraud_watch`.
3. `credit_watch` — `risk_flag == credit_watch`.
4. `review_required` — `account_status == review_required`.
5. `none` — active account, risk none.

A blocked account that is also credit_watch resolves to `account_blocked`.

---

## 4. ORDER-RELEASE DECISION MATRIX (expedite/dispatch tasks)

Decide `final_decision` + `next_action` by precedence — **customer/account issues
outrank product and stock issues**:

| condition (first match wins)            | final_decision   | next_action            |
|-----------------------------------------|------------------|------------------------|
| account_blocked                         | reject_hold      | hold_credit_or_fraud   |
| fraud_watch OR credit_watch             | reject_hold      | hold_credit_or_fraud   |
| review_required                         | manual_review    | send_account_review    |
| inactive_sku / inactive_and_shortage    | manual_review    | escalate_product_master|
| shortage                                | backorder        | create_backorder       |
| low_stock                               | delayed_release  | delay_and_monitor      |
| ready                                   | ship_now         | release_to_pick        |

Notes:
- A same-week/expedite "exception" request from the customer does NOT override an
  account block or risk flag — still reject_hold.
- Always produce the shipping quote even when the decision is not "ship" (a quote
  may be explicitly requested regardless of release).

### Summary block (expedite task)
- `order_count` = number of orders.
- `decision_counts` = object with integer counts for EACH of the 5 final_decision
  enums (include zeros).
- `total_shipping_cost_usd` = sum of every order's quote total_cost (2 dp).
- `blocked_order_ids` = orders with final_decision reject_hold (account/risk holds).
- `manual_review_order_ids`, `backorder_order_ids` = by final_decision.
- `inactive_sku_order_ids` = orders containing any inactive SKU.
- Records sorted by `order_id`; every SKU list sorted ascending; all order-id lists sorted.

---

## 5. MIXED-WAREHOUSE ALLOCATION (line-level transfer/backorder tasks)

For every line in the wave, choose ONE `action` ∈ ship | transfer | backorder |
manual_review and a `primary_reason` ∈ none | account_blocked |
account_review_required | fraud_watch | inactive_product | insufficient_effective_stock.

Per-line precedence:
1. **Account/customer-risk stop → manual_review** (and the WHOLE order's lines all
   become manual_review). Reason mapping:
   - account_status blocked → `account_blocked`
   - risk_flag fraud_watch → `fraud_watch`
   - account_status review_required → `account_review_required`
2. **Inactive product → manual_review**, reason `inactive_product` (line-only; does
   NOT block the rest of the order).
3. **Enough at requested WH** (`requested_effective_available >= quantity`) →
   `ship`, ship_quantity = quantity, reason `none`.
4. **Partial + transfer**: ship the usable requested-WH quantity
   (`ship_quantity = max(0, requested_effective_available)`), then cover the
   remainder `need = quantity - ship_quantity` from ONE source warehouse whose
   `transfer_surplus(src) >= need` (surplus above that warehouse's safety stock).
   → `transfer`, transfer_from = that source, transfer_quantity = need,
   reason `insufficient_effective_stock`. Emit a row in `transfer_requests`.
5. **Otherwise → backorder**: ship the usable part, backorder_quantity = remainder,
   reason `insufficient_effective_stock`.

`requested_effective_available` reported on each line = effective_available at the
order's own warehouse (may be negative — report as computed).

### Roll-ups & summary
- `blocked_orders` (top-level list AND summary count) = orders stopped at the
  account/customer-risk level (account_blocked, fraud_watch, account_review_required).
  NOT line-only product (inactive) reviews.
- `order_rollup.outcome` per order ∈ ready_to_ship | needs_transfer | has_backorder
  | manual_review | mixed_actions. If an order's lines have a single action class
  use that; if it mixes (e.g. one inactive manual_review line + one backorder line),
  use `mixed_actions`.
- summary integers: total_orders, total_lines, ship_lines, transfer_lines,
  backorder_lines, manual_review_lines, blocked_orders, transfer_units (sum of
  transfer_quantity), backorder_units (sum of backorder_quantity).
- Sort line_actions and transfer_requests by order_id then line_id; rollup by order_id.

---

## 6. KIT REPLENISHMENT PLANNING (BOM build run)

Goal: for each component SKU needed by a kit run at a planning warehouse, decide
no-action / transfer / purchase, honoring existing PO coverage and overstock.

Steps:
1. Pull each BOM in the memo. `total_required(sku)` = Σ over builds of
   `quantity_per_kit * build_quantity` (aggregate a shared SKU across BOMs).
2. `needed_by(sku)` = the earliest build_date among builds that consume the SKU.
3. `target_effective_available(sku)` = effective_available at the PLANNING warehouse.
4. `gap = total_required - target_effective_available`.
5. **Timely PO coverage**: `timely_po_qty` = Σ quantity of POs that are
   **same planning warehouse**, status **open OR confirmed** (NOT received — received
   stock is already in on_hand; NOT cancelled), AND `eta <= needed_by`. Collect
   their `coverage_po_ids` (sorted).
6. **Decision waterfall** (sets `final_action` + `exclusion_reason`):
   - `gap <= 0` and `target_effective_available >= overstock_threshold` →
     `overstock_excluded` / reason `target_overstock` (already over-stocked; add nothing).
   - `gap <= 0` (stocked, not overstocked) → `no_action_stocked` / reason `stocked_no_gap`.
   - `timely_po_qty >= gap` → `timely_po_covered` / reason `timely_po_covers_gap`.
   - else remaining = `gap - timely_po_qty`; cover as much as possible with
     transfers (surplus above safety from other warehouses), set `transfer_qty`;
     `purchase_requisition_qty = max(0, remaining - transfer_qty)`.
     - if purchase_requisition_qty == 0 → `transfer_only` / reason `none`.
     - else → `purchase_required` / reason `none`.
7. `transfer_requests`: one row per source per SKU (sku, from_warehouse_id,
   to_warehouse_id=planning WH, quantity, needed_by). Sort by sku asc, then
   quantity desc, then from_warehouse_id asc.
8. `purchase_requisitions`: sku, supplier_id (= product.supplier_id), warehouse_id
   (planning WH), quantity = purchase_requisition_qty, needed_by, unit_cost
   (= product.unit_cost, 2 dp), extended_cost = round(quantity*unit_cost, 2). Sort by sku.
9. `excluded_components`: components whose final_action is overstock_excluded /
   timely_po_covered / no_action_stocked, with `reason` ∈ target_overstock |
   timely_po_covers_gap | stocked_no_gap and `supporting_po_ids` (the covering POs,
   sorted; empty for overstock/stocked).
10. `kit_targets`: one row per BOM (bom_id, kit_name=BOM name, warehouse_id,
    build_quantity, build_date), sorted by bom_id.
11. summary: component_count (rows in component_plan), total_purchase_units,
    total_purchase_cost (2 dp), total_transfer_units, timely_po_covered_units
    (Σ timely_po_qty actually used to close a gap).

`component_plan` sorted by sku; `task_id`/`plan_date` per template.

---

## 7. SUPPLIER INCIDENT SCORECARD (period quality review)

1. Filter incident population with the API date window:
   `/incidents?start=<start>&end=<end>` — the window applies to **open_date** and is
   **inclusive on both ends**. (Q1 example: start=2026-01-01&end=2026-03-31.)
2. Group by supplier_id. A supplier is "in scope" only if it has >=1 filtered incident.
3. Per supplier compute:
   - `incident_count`, `incident_percentage` = count / total_filtered_population * 100,
     rounded to **1 decimal**.
   - `total_resolution_cost` = Σ resolution_cost (2 dp).
   - `avg_duration_days` (2 dp). Duration per incident = calendar days:
     closed → open_date→close_date; open → open_date→analysis_date.
   - `rma_count` (incident_type RMA), `work_order_count` (WORK_ORDER).
   - `open_incident_count` (status open).
   - `severe_incident_count` = severity in {high, critical}.
   - `recommendation_code` by precedence (first match):
     - **ESCALATE_SUPPLIER**: supplier `quality_status == quality_hold` with >=3 filtered
       incidents; OR any **critical RMA**; OR (rma_count >= 3 AND total cost >= 15000.00).
     - **PROCESS_REVIEW**: work_order_count >= 3 AND work_order_count > rma_count.
     - **WATCHLIST**: quality_status in {watch, quality_hold}; OR incident_count >= 4;
       OR total cost >= 12000.00; OR severe_incident_count >= 2.
     - **MONITOR**: none of the above.
4. `supplier_scorecard` sorted by supplier_id ascending.
5. `top_escalation_suppliers` = supplier_ids with code ESCALATE_SUPPLIER, sorted by
   incident_count desc, then total_resolution_cost desc, then supplier_id asc.
6. `highest_cost_supplier_id` = supplier with max total_resolution_cost.
   `highest_share_supplier_id` = supplier with max incident_count (i.e. highest share).
7. summary: filtered_incident_count, supplier_count, total_resolution_cost (2 dp),
   overall_rma_count, overall_work_order_count.

---

## 8. QUALITY-HOLD REPLENISHMENT CONTROL (per named supplier)

1. Window from the request (`start`,`end`); filter incidents per supplier with
   `/incidents?start=&end=&supplier_id=`.
2. Per supplier compute: recent_incident_count, recent_rma_count,
   severe_or_critical_count (severity high|critical), open_incident_count,
   affected_skus (sorted unique), sample_incident_ids (sorted, **max 5**),
   quality_status (from /suppliers).
3. `held_po_ids` per supplier = that supplier's POs with status **open OR confirmed**
   (`/purchase_orders?supplier_id=&status=...`), sorted.
4. `decision` precedence:
   - `freeze_new_replenishment`: quality_status == quality_hold (hard stop).
   - `buyer_review_required`: quality_status == watch (or, if approved, elevated
     recent risk: recent_rma_count >= 2 OR severe_or_critical_count >= 2 OR
     open_incident_count >= 2).
   - `monitor_only`: approved supplier with no/low recent risk.
5. A supplier's `held_po_ids` are reported for frozen suppliers (and any whose
   replenishment is being stopped). `monitor_only` suppliers release their POs.
6. Top-level: `held_po_ids` = sorted unique union of all held PO ids;
   `release_supplier_ids` = suppliers whose decision is monitor_only (sorted).
7. summary: suppliers_reviewed, freeze_count, buyer_review_count, monitor_count,
   held_po_count (size of unique held set), total_recent_incidents.
8. supplier_decisions sorted by supplier_id ascending.

---

## 9. OUTPUT CONVENTIONS (apply to every task)

- Return **only** the JSON object matching the task's `answer_template.json` — no
  prose, no markdown fences around it.
- Include EXACTLY the required top-level keys and every required item key; use the
  exact enum spellings from the template.
- **Currency** (`*_cost*`, `*_usd`, unit_cost, extended_cost, total_resolution_cost):
  round to **2 decimals**.
- **Percentages**: round to **1 decimal** (scorecard) unless template says otherwise.
- **Durations**: 2 decimals. **Quantities / counts / zone_distance / service_days /
  line_id**: integers.
- **Sorting**: obey the template's stated order exactly. Defaults: records by
  order_id; line lists by order_id then line_id; SKU lists ascending; supplier lists
  by supplier_id ascending; id lists ascending. Apply secondary/tertiary keys when
  specified (e.g. transfer_requests: sku asc, qty desc, from_warehouse asc).
- Emit zero-valued entries for required enum count maps (don't omit a decision class).
- Use the wave_id / task_id `required_value` from the template verbatim.

---

## 10. COMMON MISJUDGMENTS — explicit exclusion rules

- **Do not** count reserved or quarantined as available. Available = on_hand −
  reserved − quarantined.
- **Do not** transfer below a source warehouse's safety stock. Only surplus moves.
- **Inactive SKUs** (`product.active == false`) never auto-ship — they go to
  manual_review / escalate_product_master, even if stock is plentiful.
- **Account block / fraud_watch / credit_watch / review_required** outrank stock and
  product status. A blocked or risk-flagged customer's order is held even with full
  stock; in allocation, ALL lines of that order become manual_review.
- **Overstock exclusion**: if a planning-WH SKU's effective_available already meets/
  exceeds its `overstock_threshold`, exclude it from replenishment (target_overstock)
  — never add stock to an overstocked item.
- **Timely-PO coverage** counts only **same-warehouse, open/confirmed** POs with
  `eta <= needed_by`. `received` POs are already in on_hand (don't double-count);
  `cancelled` never counts; a PO arriving after the build is not timely.
- **Critical RMA** alone forces ESCALATE_SUPPLIER regardless of count/cost.
- **Incident date window** filters `open_date` and is inclusive on both endpoints —
  use the API's `start`/`end` rather than client-side filtering when possible.
- **Open incidents** have `close_date == null`; their duration runs to the analysis
  date, and they count toward open_incident_count.
- Shipping weight is the **whole order's** summed line weight, not a single line; and
  quote from the order's own warehouse/zip/speed. Trust the API's returned total_cost.
- Watch out for missing inventory rows → effective_available = 0 (treat as shortage,
  not error).
