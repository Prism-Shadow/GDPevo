# SKILL: Northwind Components ERP — Inventory / Order-Fulfillment Operations

Transferable playbook for the Northwind Components ERP domain (inventory status,
order release/allocation, kit replenishment, supplier incident scorecards,
procurement quality control, shipping quotes). Built by working real records on
the shared API. Use it to solve unseen TEST tasks in the same domain.

---

## 0. REMOTE API — how to use it

Base URL (always use the runner-provided remote one; ignore any `127.0.0.1:8007`
or `task_group/.../env` path mentioned in prompts):

    <remote-env-url>

GET endpoints (all JSON):
- `/health` — manifest + record counts (sanity check; data is seeded/static).
- `/products`  /  `/products/<sku>`
- `/customers`  /  `/customers/<customer_id>`
- `/suppliers`
- `/warehouses`  (3: WH_NORTH 07102, WH_CENTRAL 60607, WH_WEST 89502)
- `/inventory?warehouse_id=&sku=`  (omit params to list all; filters are ANDed)
- `/purchase_orders?supplier_id=&sku=&status=`
- `/orders?wave=&required_date=&customer_id=`  /  `/orders/<order_id>`
- `/shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=`  (speed: ground|two_day|overnight)
- `/incidents?start=&end=&supplier_id=&sku=&incident_type=&status=`
- `/boms`  /  `/boms/<bom_id>`

Practical notes:
- Pull the wave/order set first (`/orders?wave=...`), then fan out to
  `/products/<sku>`, `/customers/<id>`, `/inventory?...` for each referenced id.
- `/incidents` date window filters on `open_date` and is INCLUSIVE on both ends
  (`start` and `end` are both kept). Open incidents have `close_date: null`.
- `/shipping/quote` returns the fully-computed quote server-side
  (`zone_distance`, `service_days`, `base_rate`, `fuel_surcharge_rate`,
  `total_cost`). DO NOT recompute it — call the endpoint and read the fields.
  The only thing you must compute is the input `weight_lb` (see §6).
- Always answer ONLY with JSON matching the task's `answer_template.json`. No prose.

### Record shapes (field names you will rely on)
- product: `sku, name, active(bool), category, supplier_id, unit_cost,
  weight_lb, safety_stock, overstock_threshold`
- customer: `customer_id, name, account_status(active|review_required|blocked),
  risk_flag(none|credit_watch|fraud_watch), tier, margin_band`
- inventory (per warehouse+sku): `warehouse_id, sku, on_hand, reserved,
  quarantined, last_count_date`
- order: `order_id, customer_id, warehouse_id, destination_zip, shipping_speed,
  priority, required_date, wave, lines[{line_id, sku, quantity, unit_price}]`
- purchase_order: `po_id, sku, supplier_id, warehouse_id, quantity, status
  (open|confirmed|received|cancelled), eta`
- supplier: `supplier_id, name, region, quality_status(approved|watch|quality_hold)`
- incident: `incident_id, supplier_id, sku, warehouse_id, incident_type
  (RMA|WORK_ORDER), severity(low|medium|high|critical), status(open|closed),
  open_date, close_date(nullable), resolution_cost, root_cause`
- bom: `bom_id, name, warehouse_id, target_date, components[{sku, quantity_per_kit}]`

---

## 1. CORE CONCEPT — Effective Available stock

The single most important quantity across fulfillment/allocation/replenishment.
Protected stock is NOT freely usable: subtract reserved, quarantined, AND the
product's safety_stock ("normal operating buffer"). Floor at zero.

    effective_available = max(0, on_hand - reserved - quarantined - safety_stock)

- Compute it PER (warehouse, sku). Inventory is warehouse-scoped.
- A missing inventory row (no record for that warehouse+sku) = 0 on hand → 0.
- The allocation/replenishment templates expose this as
  `requested_effective_available` / `target_effective_available`.
- A separate "net available" (on_hand - reserved - quarantined, WITHOUT safety)
  is used only to detect a low-buffer condition (see §2 low_stock).

---

## 2. INVENTORY STATUS classification (per order, expedite/release tasks)

Enum: `ready | low_stock | shortage | inactive_sku | inactive_and_shortage`.

Per line of the order (at the order's `warehouse_id`):
- inactive line: `product.active == false`.
- shortage line: product active AND `quantity > effective_available`.
- low line: product active, line is fillable (`quantity <= net_available`), but
  the warehouse buffer is thin — `net_available < safety_stock`
  (net_available = on_hand - reserved - quarantined). [Tie-break convention; if a
  task spec gives an explicit low_stock rule, follow that instead.]

Roll lines up to the order status (precedence):
1. has inactive line AND has shortage line → `inactive_and_shortage`
2. has inactive line (no shortage)        → `inactive_sku`
3. has shortage line                      → `shortage`
4. has low line                           → `low_stock`
5. otherwise                              → `ready`

SKU exception lists (always sorted ascending, de-duplicated):
`shortage_skus`, `inactive_skus`, `low_stock_skus`.

---

## 3. CUSTOMER EXCEPTION classification

Enum: `none | review_required | account_blocked | fraud_watch | credit_watch`.
Derive from the customer record with this PRECEDENCE (a blocked account that is
also credit_watch is `account_blocked`):
1. `account_status == "blocked"`        → `account_blocked`
2. `risk_flag == "fraud_watch"`         → `fraud_watch`
3. `risk_flag == "credit_watch"`        → `credit_watch`
4. `account_status == "review_required"`→ `review_required`
5. else                                 → `none`

---

## 4. EXPEDITE / RELEASE DECISION (expedite-queue tasks)

`final_decision` ∈ ship_now | delayed_release | manual_review | backorder | reject_hold
`next_action`    ∈ release_to_pick | delay_and_monitor | send_account_review |
                   create_backorder | hold_credit_or_fraud | escalate_product_master

Decision precedence — ACCOUNT/RISK gates first, then product master, then stock:
1. account_blocked → `reject_hold` / `hold_credit_or_fraud`
2. fraud_watch or credit_watch → `manual_review` / `hold_credit_or_fraud`
   (a hard risk hold; a same-week customer ask does NOT override an account block)
3. review_required → `manual_review` / `send_account_review`
4. inventory has inactive sku (inactive_sku or inactive_and_shortage) →
   `manual_review` / `escalate_product_master`
5. inventory shortage → `backorder` / `create_backorder`
6. inventory low_stock → `delayed_release` / `delay_and_monitor`
7. clean & ready → `ship_now` / `release_to_pick`

ALWAYS produce a `shipping_quote` for EVERY order, even when the decision is not a
release (memos explicitly request the quote regardless of disposition). Use the
order's own `shipping_speed` and warehouse (see §6).

Summary block (typical keys): `order_count`, `decision_counts` (one int per
final_decision enum value, zeros included), `total_shipping_cost_usd` (sum of all
order quote totals, 2 dp), and id lists sorted ascending —
`blocked_order_ids` (reject_hold), `manual_review_order_ids`,
`backorder_order_ids`, `inactive_sku_order_ids` (orders with any inactive sku).
Records sorted by `order_id` ascending.

---

## 5. MIXED-WAREHOUSE ALLOCATION (line-level transfer/backorder tasks)

`action` ∈ ship | transfer | backorder | manual_review
`primary_reason` ∈ none | account_blocked | account_review_required | fraud_watch |
                   inactive_product | insufficient_effective_stock

Per line (requested warehouse = order.warehouse_id):
1. Account/risk gate (whole order): blocked / review_required / fraud / credit →
   `manual_review`, reason = matching account reason, ship=transfer=backorder=0.
   These orders also go into `blocked_orders` (account/risk level only — NOT
   product-only line reviews).
2. Inactive product line → `manual_review`, reason `inactive_product`.
3. Else compare line `quantity` vs requested-warehouse `effective_available`:
   - qty <= eff → `ship`, ship_quantity = qty.
   - eff partially covers, and ANOTHER warehouse's effective_available can cover
     the remainder → `transfer`: ship_quantity = eff at requested wh,
     transfer_quantity = remaining, transfer_from = the source warehouse,
     backorder_quantity = 0. Pick ONE source warehouse for the uncovered qty;
     do not draw on protected stock at the source (use its effective_available).
   - no combination clears it → `backorder`: backorder_quantity = uncovered qty,
     ship_quantity = eff used at requested wh, reason `insufficient_effective_stock`.
4. Emit a `transfer_requests` row for each transfer line
   (order_id, line_id, sku, from_warehouse, to_warehouse, quantity).
5. `order_rollup` outcome per order: all ship → `ready_to_ship`; any
   manual_review (account/product) → `manual_review`; single action type →
   `needs_transfer` / `has_backorder`; multiple differing actions → `mixed_actions`.
Sort line_actions by order_id then line_id. Summary keys are integer counts/units.

---

## 6. SHIPPING QUOTE

Per order: `weight_lb = Σ over lines (product.weight_lb * line.quantity)` using the
EXACT float (do not pre-round the weight). Then call:

    /shipping/quote?warehouse_id=<order.warehouse_id>&destination_zip=<order.destination_zip>
        &weight_lb=<total>&speed=<order.shipping_speed>

Read `zone_distance` (int), `service_days` (int), `total_cost` from the response.
Output object keys are typically `zone_distance`, `service_days`,
`total_cost_usd` (= response `total_cost`, rounded to 2 dp).

Formula the server uses (for sanity-checking only — prefer the live endpoint):
- `base_rate = 18.95 + 1.18*weight_lb + 3.4*(zone_distance - 3)`
- `total_cost = base_rate * (1 + fuel_surcharge_rate) * speed_multiplier`
  with fuel ≈ 0.0925 and speed_multiplier ground=1.0, two_day=1.75, overnight=2.65.
- `zone_distance`/`service_days` come from warehouse↔destination-zip distance;
  ground service_days grows with zone, two_day=2, overnight=1.

---

## 7. KIT / BOM REPLENISHMENT (production replenishment tasks)

For each target build {bom_id, build_quantity, build_date} pull the BOM components.
Plan at the BOM's planning warehouse (the memo's `planning_site`, e.g. WH_WEST).

Per component sku (aggregate across all builds that use it):
- `total_required = Σ (quantity_per_kit * build_quantity)` over every build using it.
- `needed_by` = EARLIEST build_date among builds requiring that sku.
- `target_effective_available` = effective_available at the planning warehouse
  (§1: on_hand - reserved - quarantined - safety_stock, floored).
- `gap = max(0, total_required - target_effective_available)`.

Coverage decision (in order; `final_action` enum:
no_action_stocked | transfer_only | purchase_required | timely_po_covered | overstock_excluded):
1. gap == 0:
   - if `target_effective_available > overstock_threshold` →
     `overstock_excluded` (exclusion_reason `target_overstock`); never add stock.
   - else `no_action_stocked` (exclusion_reason `stocked_no_gap`).
2. gap > 0 — check TIMELY POs first:
   - `timely_po_qty` = Σ quantity of POs that are SAME planning warehouse,
     status in {open, confirmed}, AND `eta <= needed_by`. (received/cancelled and
     wrong-warehouse and late-eta POs are NOT timely.)
   - if `timely_po_qty >= gap` → `timely_po_covered`
     (exclusion_reason `timely_po_covers_gap`; `coverage_po_ids` = those PO ids,
     sorted). No transfer/purchase.
3. gap still uncovered — TRANSFER from other warehouses:
   - `transfer_qty` = min(gap, Σ effective_available of OTHER warehouses) using
     each source's effective_available (respect protected stock).
   - if transfer fully covers the gap → `transfer_only`.
4. Remainder after transfer → PURCHASE:
   - `purchase_requisition_qty = gap - transfer_qty` (only the still-uncovered part).
   - `final_action = purchase_required`. Requisition uses
     `supplier_id = product.supplier_id`, `unit_cost = product.unit_cost`,
     `extended_cost = unit_cost * quantity` (2 dp), `warehouse_id = planning site`,
     `needed_by`.

Emit `transfer_requests` (sku, from_warehouse_id, to_warehouse_id, quantity,
needed_by) and `purchase_requisitions`. `excluded_components` lists components with
final_action overstock_excluded / timely_po_covered / no-gap, with their reason +
supporting_po_ids. Summary: component_count, total_purchase_units,
total_purchase_cost (2 dp), total_transfer_units, timely_po_covered_units.
Sort component_plan / requisitions / exclusions by sku; transfer_requests by sku,
then quantity desc, then from_warehouse_id asc.

---

## 8. SUPPLIER INCIDENT SCORECARD (quality-review tasks)

Filter incidents by the requested window on `open_date` (inclusive both ends), e.g.
`/incidents?start=2026-01-01&end=2026-03-31`. Group by supplier_id. Per supplier:
- `incident_count`, `incident_percentage` = 100*count/filtered_total (1 dp).
- `total_resolution_cost` = Σ resolution_cost (2 dp).
- `avg_duration_days` (2 dp) where per-incident duration is calendar days:
  - closed: `close_date - open_date`.
  - open:   `analysis_date - open_date` (analysis_date from the request).
- `rma_count` (incident_type RMA), `work_order_count` (WORK_ORDER).
- `open_incident_count` (status open).
- `severe_incident_count` = severity in {high, critical}.

`recommendation_code` — apply in STRICT precedence, FIRST match wins
(ESCALATE_SUPPLIER > PROCESS_REVIEW > WATCHLIST > MONITOR):
- ESCALATE_SUPPLIER: supplier `quality_status == quality_hold` AND >=3 filtered
  incidents; OR any critical RMA (incident_type RMA & severity critical);
  OR >=3 RMAs AND total filtered resolution cost >= 15000.00.
- PROCESS_REVIEW: WORK_ORDER count >= 3 AND WORK_ORDER count > RMA count.
- WATCHLIST: quality_status in {watch, quality_hold}; OR incident_count >= 4;
  OR total resolution cost >= 12000.00; OR severe_incident_count >= 2.
- MONITOR: none of the above.

Scorecard rows sorted by supplier_id asc. Include a supplier row only if it has
>=1 filtered incident. `summary`: filtered_incident_count, supplier_count,
total_resolution_cost (2 dp), overall_rma_count, overall_work_order_count.
`top_escalation_suppliers` = supplier_ids with code ESCALATE_SUPPLIER, ordered by
incident_count desc, then total_resolution_cost desc, then supplier_id asc.
`highest_cost_supplier_id` = supplier with max total_resolution_cost;
`highest_share_supplier_id` = supplier with max incident_count/share.

---

## 9. PROCUREMENT QUALITY CONTROL (replenishment-freeze tasks)

For each target supplier over the requested window (filter `/incidents` by
supplier_id + start/end on open_date). Compute recent_incident_count,
recent_rma_count, severe_or_critical_count (high|critical), open_incident_count,
affected_skus (sorted unique), sample_incident_ids (sorted, MAX 5).

`held_po_ids` for a supplier = that supplier's purchase orders with status in
{open, confirmed} (received/cancelled never held), sorted.

`decision` ∈ freeze_new_replenishment | buyer_review_required | monitor_only:
- freeze_new_replenishment: supplier `quality_status == quality_hold`
  (hard quality hold → freeze and hold all its open/confirmed POs).
- buyer_review_required: `quality_status == watch`, OR recent quality signals are
  elevated (e.g. recent RMAs, severe/critical incidents, or open incidents present).
- monitor_only: approved supplier with no concerning recent signals.

Top-level `held_po_ids` = sorted unique union of all suppliers' held POs.
`release_supplier_ids` = suppliers whose decision is monitor_only (sorted).
Summary: suppliers_reviewed, freeze_count, buyer_review_count, monitor_count,
held_po_count, total_recent_incidents. Sort supplier_decisions by supplier_id asc.

---

## 10. OUTPUT / FORMATTING CONVENTIONS (apply everywhere)

- Return ONLY the JSON object the template specifies; no narrative, no extra keys.
- Honor every `required_value` literally (e.g. wave_id, task_id).
- Currency / cost fields: round to 2 decimals. Percentages: 1 decimal (unless the
  request says otherwise). Durations: 2 decimals. Counts/units/zone/days: integers.
- Round at the OUTPUT field; sum unrounded then round totals (avoid double-rounding
  drift on `total_*` fields).
- Sorting: respect each list's stated order. Default for id/sku lists is ascending,
  de-duplicated. Records usually sort by order_id (then line_id) or by sku/supplier_id.
- Enum fields must use EXACTLY the allowed literal values; include all required keys
  even when a list is empty `[]`, a count is `0`, or a reason is `"none"`.
- Use `null` for nullable enum fields (e.g. transfer_from when no transfer).

---

## 11. COMMON MISJUDGMENTS / EXCLUSION RULES (avoid these)

- Forgetting safety_stock: effective_available MUST subtract reserved AND
  quarantined AND safety_stock. Using raw on_hand overstates availability.
- Treating reserved/quarantined stock as shippable. It is protected.
- Letting a customer "exception request" override a hard account block or risk
  flag. Account/risk gates win over inventory; never ship a blocked account.
- Counting `received` or `cancelled` POs as coverage. Only open/confirmed POs are
  active; a PO is only "timely" if same-warehouse AND eta <= needed_by.
- Adding replenishment to an already overstocked component
  (target_effective_available > overstock_threshold → overstock_excluded).
- Shipping/replenishing an inactive SKU (`active == false`) → escalate/manual_review.
- Incident window off-by-one: window is inclusive both ends on open_date; open
  incidents have null close_date — use analysis_date for their duration.
- Misordering recommendation/decision precedence — always evaluate highest-severity
  condition first and stop at the first match.
- Recomputing shipping cost by hand and drifting from the endpoint — call the API.
- Omitting required template keys, empty lists, zero counts, or `"none"` reasons.
