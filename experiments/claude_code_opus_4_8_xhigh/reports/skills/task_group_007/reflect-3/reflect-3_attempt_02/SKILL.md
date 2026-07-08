# SKILL: Northwind Components ERP — Inventory / Order-Fulfillment Operations

Reusable workflow for solving Northwind Components ERP tasks (expedite dispatch, kit
replenishment, supplier incident scorecards, mixed-warehouse allocation, procurement quality
control). Rules below were verified/refined against task feedback. Read the task `prompt.txt`,
its `input/payloads/*` memo, and the `answer_template.json`, then follow the matching SOP.

> Do NOT call any scoring/judge endpoint at solve time. Build the answer purely from the ERP API
> and the task payloads, and emit only the JSON the template requires.

---

## 1. ERP API (read-only data source)

Base URL is provided by the runner. Ignore any "start a local env / 127.0.0.1" wording in prompts;
use the runner-provided base URL. All endpoints return JSON.

GET endpoints:
- `/health`
- `/products` , `/products/<sku>`
  fields: sku, name, category, active(bool), supplier_id, unit_cost, weight_lb,
  safety_stock, overstock_threshold
- `/customers` , `/customers/<id>`
  fields: customer_id, name, account_status(active|review_required|blocked),
  risk_flag(none|credit_watch|fraud_watch), tier(strategic|standard|economy), margin_band
- `/suppliers` — supplier_id, name, region, quality_status(approved|watch|quality_hold)
- `/warehouses` — warehouse_id(WH_NORTH|WH_CENTRAL|WH_WEST), name, region, zip
- `/inventory?warehouse_id=&sku=` — per (warehouse,sku): on_hand, reserved, quarantined,
  last_count_date. One row per warehouse/sku. Missing row => treat as 0 stock.
- `/purchase_orders?supplier_id=&sku=&status=` — po_id, sku, supplier_id, warehouse_id,
  quantity, eta, status(open|confirmed|received|cancelled)
- `/orders?wave=&required_date=&customer_id=` , `/orders/<order_id>`
  order: order_id, wave, customer_id, warehouse_id, destination_zip, priority,
  required_date, shipping_speed(ground|two_day|overnight), lines[{line_id,sku,quantity,unit_price}]
- `/shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=` (speed: ground|two_day|overnight)
  returns: zone_distance(int), service_days(int), total_cost(float), base_rate, fuel_surcharge_rate
- `/incidents?start=&end=&supplier_id=&sku=&incident_type=&status=` — the date window applies to
  `open_date`. incident: incident_id, supplier_id, sku, warehouse_id, incident_type(RMA|WORK_ORDER),
  severity(low|medium|high|critical), status(open|closed), open_date, close_date, resolution_cost,
  root_cause
- `/boms` , `/boms/<bom_id>` — bom_id, name, warehouse_id, target_date,
  components[{sku, quantity_per_kit}]

Practical notes:
- It is efficient to pull whole collections once (`/products`, `/inventory`, `/customers`,
  `/purchase_orders`, `/incidents`, `/boms`, `/suppliers`) and index them in memory.
- Date fields are `YYYY-MM-DD`; lexicographic string comparison is a valid date comparison.
- `/incidents?start=&end=` filters on open_date; you can also filter locally with the same logic.

---

## 2. THE core inventory rule (most important, cost the most score)

**Effective available for planning/fulfillment =
`on_hand − reserved − quarantined − safety_stock`.**

Reserved, quarantined, AND safety_stock (the "normal operating buffer") are all NON-freely-available.
- This value may be **negative**; report the raw signed integer — do NOT clamp to 0.
- A line is a **shortage / cannot ship in full** when `effective_available < line.quantity`.
- When deciding inter-warehouse transfers, a source warehouse can only contribute its own
  effective available (same formula); never draw a source below its safety/reserved/quarantine.
- Verified: omitting the `− safety_stock` term is the single most common scoring error. Always
  subtract it for any "available to fulfill/build/transfer" decision.

When a separate "freely available without safety" figure is ever needed it would be
`on_hand − reserved − quarantined`, but the planning/allocation tasks here use the
safety-subtracted figure.

---

## 3. Customer / account exception precedence

For order-release decisions, evaluate customer state first (it can stop the whole order):

| Condition                              | exception code            | effect                              |
|----------------------------------------|---------------------------|-------------------------------------|
| account_status == blocked              | account_blocked           | hard stop, order-level block        |
| risk_flag == fraud_watch               | fraud_watch               | hard stop, order-level block        |
| account_status == review_required      | review_required / account_review_required | order-level review (blocked)|
| risk_flag == credit_watch              | credit_watch              | review/hold (account-level)         |
| else                                   | none                      | proceed to inventory/product checks |

- "Order-level block" = every line on the order gets the account/risk reason, the order goes into
  the wave's blocked/manual-review list, and inventory is not auto-released.
- Inactive product (`product.active == false`) is a **line-only** review (manual_review with reason
  inactive_product); it does NOT put the order in the account-level blocked list.

---

## 4. SOP A — Expedite dispatch-control wave (per-order decision)

Inputs: a queue memo listing a SUBSET of order_ids for a wave (use ONLY the memo's order_ids, even
though `/orders?wave=` returns more), plus live ERP records.

Per order:
1. For each line compute `effective_available = on_hand − reserved − quarantined − safety_stock`
   at the order's warehouse. Build three SKU lists (each SKU in at most one list):
   - `inactive_skus`: product.active == false
   - `shortage_skus`: effective_available < line.quantity
   - `low_stock_skus`: can cover the line but the post-fulfillment buffer is thin
     (effective_available ≥ qty yet still below safety margin)
2. inventory_status (order-level rollup of the lists):
   inactive+shortage → `inactive_and_shortage`; inactive only → `inactive_sku`;
   shortage only → `shortage`; low only → `low_stock`; else `ready`.
3. customer_exception per Section 3 (enum: none|review_required|account_blocked|fraud_watch|credit_watch).
4. final_decision / next_action — account hard-stops dominate inventory:
   - account_blocked or fraud_watch → `reject_hold` / `hold_credit_or_fraud`
   - credit_watch or review_required → `manual_review` / `send_account_review`
   - inactive SKU present → `manual_review` / `escalate_product_master`
   - shortage → `backorder` / `create_backorder`
   - low_stock → `delayed_release` / `delay_and_monitor`
   - else ready → `ship_now` / `release_to_pick`
5. shipping_quote: GET `/shipping/quote` with the order's warehouse_id, destination_zip,
   `weight_lb = Σ(line.quantity × product.weight_lb)`, and the order's shipping_speed.
   Emit `{zone_distance:int, service_days:int, total_cost_usd: round(total_cost,2)}`. Produce a
   quote for every order even when the decision is not "ship".
6. summary: order_count; decision_counts (all 5 keys, integers); total_shipping_cost_usd
   (Σ rounded, 2dp); blocked_order_ids (account_blocked), manual_review_order_ids,
   backorder_order_ids, inactive_sku_order_ids — each sorted ascending.

Sort `records` by order_id; all SKU lists sorted ascending.
(Note: the exact shortage/low boundary and decision precedence for this wave were the hardest to
pin down; always subtract safety_stock per Section 2 before classifying.)

## 5. SOP B — Kit-build replenishment from BOMs

Inputs: production memo with planning_site (warehouse), and target_builds[{bom_id,
target_build_quantity, target_build_date}].

1. kit_targets: for each target build, look up the BOM → {bom_id, kit_name(=bom.name),
   warehouse_id(=bom.warehouse_id), build_quantity, build_date}. Sort by bom_id.
2. Per component SKU across all target BOMs:
   - `total_required` = Σ over BOMs (quantity_per_kit × build_quantity)
   - `needed_by` = earliest target_build_date among BOMs that use the SKU
   - `target_effective_available` = on_hand − reserved − quarantined − safety_stock at the
     planning site (Section 2; can be negative)
   - `timely_po_qty` = Σ quantity of POs that are same-warehouse AND status in {open, confirmed}
     (exclude received/cancelled) AND `eta ≤ needed_by`. coverage_po_ids = those po_ids sorted.
   - gap_before_po = total_required − target_effective_available; gap = gap_before_po − timely_po_qty
3. final_action / exclusion_reason:
   - target_effective_available ≥ overstock_threshold → `overstock_excluded` / target_overstock
   - gap_before_po ≤ 0 → `no_action_stocked` / stocked_no_gap
   - gap ≤ 0 (timely POs close it) → `timely_po_covered` / timely_po_covers_gap
   - else cover the gap by inter-warehouse transfer first, then purchase:
     transfer_qty from another warehouse's effective available (Section 2; protect source safety);
     purchase_requisition_qty = remaining gap. `transfer_only` if fully covered by transfer,
     else `purchase_required`.
4. transfer_requests: {sku, from_warehouse_id, to_warehouse_id(=site), quantity, needed_by}.
   purchase_requisitions: {sku, supplier_id(=product.supplier_id), warehouse_id(=site), quantity,
   needed_by, unit_cost(2dp), extended_cost = round(unit_cost×quantity,2)}.
   excluded_components: {sku, reason, supporting_po_ids} for the three exclusion reasons.
5. summary: component_count; total_purchase_units; total_purchase_cost(2dp); total_transfer_units;
   `timely_po_covered_units` = Σ of the gap that timely POs actually closed (the gap_before_po for
   timely_po_covered SKUs) — NOT the full PO quantity.
6. Sort: component_plan & purchase_requisitions & excluded_components by sku asc;
   transfer_requests by sku asc, then quantity desc, then from_warehouse_id asc.
   task_id and plan_date must match the template's required values.

## 6. SOP C — Supplier incident scorecard (deterministic; scores perfectly)

Inputs: a request payload with the date filter, duration rule, precision rules, severe-severity
set, and an explicit recommendation policy with a precedence list. Follow the payload literally.

1. Filter incidents to `start_date ≤ open_date ≤ end_date` (inclusive). This filtered set is the
   population; its size is the percentage denominator.
2. Group by supplier_id (only suppliers with ≥1 filtered incident appear).
3. Per supplier:
   - incident_count; incident_percentage = count×100/N rounded to 1 decimal
   - rma_count (incident_type==RMA), work_order_count (==WORK_ORDER)
   - open_incident_count (status==open)
   - severe_incident_count (severity in the payload's severe set, typically {high,critical})
   - total_resolution_cost = Σ resolution_cost (2dp)
   - avg_duration_days = mean of per-incident durations (2dp), where duration =
     (close_date − open_date) days for closed, (analysis_date − open_date) days for open
4. recommendation_code by the payload precedence (first match wins). Example policy used:
   - ESCALATE_SUPPLIER: (quality_status==quality_hold AND count≥3) OR any critical RMA OR
     (rma_count≥3 AND total_cost≥15000)
   - PROCESS_REVIEW: work_order_count≥3 AND work_order_count>rma_count
   - WATCHLIST: quality_status in {watch,quality_hold} OR count≥4 OR total_cost≥12000 OR severe≥2
   - MONITOR: otherwise
   Always read the actual thresholds from the request payload — they are authoritative.
5. summary: filtered_incident_count, supplier_count, total_resolution_cost(2dp),
   overall_rma_count, overall_work_order_count.
   top_escalation_suppliers: only ESCALATE rows, ordered incident_count desc, total_resolution_cost
   desc, supplier_id asc → list of supplier_id strings.
   highest_cost_supplier_id = max total_resolution_cost; highest_share_supplier_id = max
   incident_count. supplier_scorecard sorted supplier_id asc.

## 7. SOP D — Mixed-warehouse line allocation (scores perfectly)

Inputs: a wave of orders; classify every line as ship | transfer | backorder | manual_review.

Per order (account state first, Section 3):
1. If order has an account/risk stop (account_blocked, fraud_watch, review_required): set EVERY
   line action = `manual_review` with that primary_reason, and add order_id to `blocked_orders`.
2. Else per line, with `requested_effective_available = on_hand − reserved − quarantined −
   safety_stock` at the requested warehouse (Section 2; report this signed integer):
   - product inactive → `manual_review`, primary_reason `inactive_product` (NOT a blocked order)
   - requested eff ≥ qty → `ship`, ship_quantity = qty
   - else ship the usable requested qty (max(0, eff)); for the remainder, if ONE other warehouse's
     running effective available can cover it → `transfer` (transfer_from = that source,
     transfer_quantity = remainder), primary_reason insufficient_effective_stock
   - else `backorder` (backorder_quantity = remainder), primary_reason insufficient_effective_stock
   Maintain a running per-(warehouse,sku) remaining-availability map so ship/transfer allocations
   across lines don't double-spend the same stock.
3. transfer_requests: {order_id, line_id, sku, from_warehouse, to_warehouse(=requested), quantity}.
4. order_rollup outcome — handle `mixed_actions` carefully (this was the subtle scoring trap):
   - actions == {ship} → ready_to_ship
   - actions ⊆ {ship,transfer} and a transfer present → needs_transfer
   - actions == {manual_review} → manual_review
   - actions ⊆ {ship,transfer,backorder} and a backorder present → has_backorder
   - else → `mixed_actions`  (e.g. manual_review combined with backorder/ship/transfer)
5. blocked_orders = order-level account/risk stops only (sorted unique); line-only inactive reviews
   are NOT blocked orders.
6. summary integers: total_orders, total_lines, ship_lines, transfer_lines, backorder_lines,
   manual_review_lines, blocked_orders(count), transfer_units(Σ transfer_quantity),
   backorder_units(Σ backorder_quantity).
   Sort line_actions and transfer_requests by (order_id, line_id); order_rollup & blocked by order_id.

## 8. SOP E — Procurement quality-control decision (partially specified)

Inputs: an analysis window, a list of target supplier_ids, and decision_choices
(freeze_new_replenishment | buyer_review_required | monitor_only). The memo gives little numeric
policy; compute the data fields exactly and apply conservative status-driven logic.

Per supplier (incidents filtered to `start ≤ open_date ≤ end`):
- recent_incident_count, recent_rma_count, severe_or_critical_count (high|critical),
  open_incident_count (status==open), affected_skus (sorted unique incident SKUs),
  sample_incident_ids (sorted, max 5).
- held_po_ids = the supplier's open/confirmed purchase order ids (sorted) when the supplier is
  frozen.
- decision:
  - `freeze_new_replenishment` when quality_status == quality_hold (verified) — hold its
    open/confirmed POs.
  - `buyer_review_required` when quality_status == watch with elevated recent risk
    (e.g. RMAs, open incidents, or multiple severe/critical incidents).
  - `monitor_only` otherwise.
- summary: suppliers_reviewed, freeze_count, buyer_review_count, monitor_count, held_po_count,
  total_recent_incidents. held_po_ids(top-level) = sorted unique across suppliers;
  release_supplier_ids = suppliers whose decision is monitor_only.

CAUTION (unresolved): the exact watch→{buyer_review vs monitor} threshold and whether held_po_ids
should be filtered to affected SKUs are not fully nailed down. Prefer the supplier's quality_status
as the primary driver, compute every numeric field precisely, and keep held_po_ids = the frozen
supplier's full open/confirmed PO set unless the payload says otherwise.

---

## 9. Output formatting conventions (apply to every task)

- Emit ONLY the JSON object matching `answer_template.json`. No prose, no extra keys, all required
  keys present.
- Honor `required_value` fields exactly (e.g. wave_id, task_id literals).
- Currency / cost fields: round to 2 decimals. Percentages: round to 1 decimal unless told otherwise.
  Durations: 2 decimals.
- Integer fields (counts, quantities, units, zone_distance, service_days,
  requested_effective_available) must be integers — including negative effective-availability values.
- Enums: use only the template's allowed values; never invent new ones.
- Apply every stated sort order exactly (usually order_id/line_id/sku/supplier_id ascending, with
  the documented multi-key tiebreakers). Sort SKU/id lists ascending and de-duplicate.
- Build summary counts/totals from the per-record results you actually emitted (keep them consistent).

## 10. Common scoring pitfalls (and the fix)

1. Forgetting `− safety_stock` in effective availability → cascades wrong everywhere. Always
   subtract reserved + quarantined + safety_stock (Section 2).
2. Clamping negative effective availability to 0 → keep it signed.
3. Using ALL wave orders when the memo lists a subset → use only the memo's order_ids.
4. Counting received/cancelled POs as coverage → only open/confirmed POs count, and (for timely
   coverage) only those with eta ≤ needed_by.
5. `timely_po_covered_units` reported as full PO quantity instead of the gap actually closed.
6. order_rollup: labeling an order has_backorder/needs_transfer when it also has a manual_review
   line → that mix is `mixed_actions`.
7. Treating a line-only inactive-product review as an account-level blocked order → it is not.
8. Incident windows filter on `open_date`; open-incident duration runs to the analysis_date, not
   today.
