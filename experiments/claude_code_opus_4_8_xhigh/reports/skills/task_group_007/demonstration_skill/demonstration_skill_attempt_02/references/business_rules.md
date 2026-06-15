# Northwind ERP Business Rules and Playbooks

These are the transferable decision rules. **The task payload always wins** — if a payload states a policy, date window, threshold, or ordering explicitly, implement that exactly and use the rules here only to fill gaps. Read the playbook matching your task.

## Table of contents
0. Shared building blocks
1. Expedite queue playbook
2. Line allocation playbook
3. Kit replenishment playbook
4. Incident scorecard playbook
5. Replenishment control playbook

---

## 0. Shared building blocks

**Effective available** (per sku, per warehouse): `on_hand - reserved - quarantined - safety_stock`. Can be negative; the negative magnitude is the shortfall. Used identically for requested WH, transfer-source WH, and build-target WH.

**Customer exception** (resolve ONE per customer, by precedence — account_status outranks risk_flag):
`account_status==blocked` → `account_blocked` ➜ `account_status==review_required` → `review_required` ➜ `risk_flag==fraud_watch` → `fraud_watch` ➜ `risk_flag==credit_watch` → `credit_watch` ➜ else `none`.
(Different tasks expose different label spellings — e.g. allocation uses `account_review_required` instead of `review_required`. Map to the enum the template lists.)

**Inactive product**: `product.active == false`. A master-data problem; never auto-ship or auto-purchase. Flag per the playbook.

**Money / rounding**: currency → 2 decimals; `extended_cost = round(unit_cost × qty, 2)`; summary money = sum of per-row rounded values. Percentages/durations → the precision the payload states.

**Set vs list**: id/SKU "sets" → dedupe + sort ascending. "Sample" lists → sort ascending then cap at the stated max (e.g. 5). Apply multi-key sorts exactly as written.

---

## 1. Expedite queue playbook
*Per-order release/hold/review/backorder decision plus a shipping quote. One record per order in the memo's `order_ids`, sorted by `order_id`.*

For each order, pull the order (lines, warehouse, customer, destination_zip, shipping_speed), its customer, and for each line SKU the product + inventory at the order's warehouse.

**Per-SKU inventory classification** (at the order's requested warehouse):
- `inactive` if `product.active == false`.
- `shortage` if `effective_available < line.quantity` (can't fully cover the line).
- `low_stock` if the line *can* be covered but stock is thin — i.e. fulfilling the line leaves the warehouse at/below its safety buffer (effective barely covers; on_hand near `safety_stock`). Treat "covered but skating on the buffer" as low_stock, "cannot cover" as shortage.
- otherwise `ready`.

**SKU exception lists** (per order, deduped + sorted ascending): `shortage_skus`, `inactive_skus`, `low_stock_skus`. A SKU can be in both `inactive_skus` and `shortage_skus` if it's inactive and also short.

**Order-level `inventory_status`** (worst-case rollup over the order's lines):
- any inactive AND any shortage → `inactive_and_shortage`
- else any inactive → `inactive_sku`
- else any shortage → `shortage`
- else any low_stock → `low_stock`
- else → `ready`

**`customer_exception`**: the single resolved exception (above), mapped to the template enum.

**`final_decision` ladder** (risk first, product next, stock last):
1. `account_blocked` → `reject_hold`
2. `fraud_watch` or `credit_watch` → `reject_hold` (held for credit/fraud)
3. `review_required` → `manual_review`
4. inactive SKU present (and no customer exception) → `manual_review` (escalate product master)
5. shortage (and clean account, no blocking inactive) → `backorder`
6. low_stock but coverable, clean account → `ship_now`
7. clean account + `ready` → `ship_now`

**`next_action`** maps from the decision: `ship_now`→`release_to_pick`; `delayed_release`→`delay_and_monitor`; `manual_review` from account→`send_account_review`; `manual_review` from product-master→`escalate_product_master`; `reject_hold` from account/credit/fraud→`hold_credit_or_fraud`; `backorder`→`create_backorder`. (Use the action that matches *why* the decision was made — account review vs product-master escalation are different next_actions even though both are manual_review.)

**`shipping_quote`**: always produce it (even when the decision isn't ship) if the template requires it. Inputs per the api guide: order's warehouse, order's destination_zip, total order weight, speed from the operator note or the order's requested speed. Map `zone_distance`, `service_days`, `total_cost`→`total_cost_usd` (2 dp).

**Summary**: `order_count`; `decision_counts` (tally each `final_decision` value, include zeros for unused ones); `total_shipping_cost_usd` = sum of per-order quote costs (2 dp); and the id lists — `blocked_order_ids` (final_decision `reject_hold`), `manual_review_order_ids`, `backorder_order_ids`, `inactive_sku_order_ids` (orders whose `inactive_skus` is non-empty) — each deduped + sorted.

---

## 2. Line allocation playbook
*Per-line ship/transfer/backorder/manual_review across mixed warehouses. One record per order line in the wave, sorted by order_id then line_id.*

Pull the wave's orders (`/orders?wave=`), each customer, and per line the product + inventory in all warehouses.

**Account/risk gate (whole order):** if the order's customer has any exception (blocked / review_required / fraud_watch / credit_watch), **every line** of that order becomes `action = manual_review`, with `ship/transfer/backorder` quantities 0 and `transfer_from = null`. `primary_reason` is the mapped exception (`account_blocked`, `account_review_required`, `fraud_watch`, `credit_watch`). Such orders go in `blocked_orders`. Do this before any stock math.

**Otherwise, per line** (clean customer):
- If `product.active == false` → `action = manual_review`, `primary_reason = inactive_product`, all quantities 0. (This is line-level: it does NOT block the order or put it in `blocked_orders`; other lines proceed normally.)
- Else compute `requested_effective_available` = effective at the line's requested warehouse (output this field, signed).
  - If `effective ≥ line.quantity` → `action = ship`, `ship_quantity = line.quantity`, reason `none`.
  - If `0 < effective < line.quantity` → ship the available part (`ship_quantity = effective`), then cover the remainder `R = line.quantity − effective` by transfer if a single other warehouse can; else backorder R.
  - If `effective ≤ 0` → `ship_quantity = 0`; cover the full `line.quantity` by transfer if possible, else backorder it.
  - **Transfer**: a transfer needs **one** source warehouse whose own effective available ≥ the uncovered quantity (sources also subtract reserved/quarantined/safety_stock). If one or more qualify, `action = transfer`, set `transfer_from` and `transfer_quantity = R`, `backorder_quantity = 0`, reason `none`. If several qualify, prefer the source with the **most** effective available (this also satisfies alphabetical tie-breaks seen in practice). A line allocation transfer is single-source — do not split across warehouses.
  - **Backorder**: if no single warehouse can cover R → `action = backorder`, `backorder_quantity = R` (= line.quantity − ship_quantity), reason `insufficient_effective_stock`.

**`transfer_requests`**: one entry per transferred line — `{order_id, line_id, sku, from_warehouse, to_warehouse (=requested WH), quantity}`. Sort by order_id then line_id.

**`blocked_orders`**: orders stopped at account/customer-risk level (not line-only product reviews). Sorted, deduped.

**`order_rollup`** (`outcome` per order, from its lines): all lines manual_review → `manual_review`; all ship → `ready_to_ship`; any backorder (with the rest ship/transfer) → `has_backorder`; all needing transfer (no backorder, no review) → `needs_transfer`; a genuine mix (e.g. some ship + a line in manual_review for inactive product, or ship+backorder+review) → `mixed_actions`. When in doubt: uniform action → that outcome; heterogeneous → `mixed_actions`.

**Summary** (all integers): `total_orders`, `total_lines`, `ship_lines`, `transfer_lines`, `backorder_lines`, `manual_review_lines`, `blocked_orders` (count), `transfer_units` (sum of transfer_quantity), `backorder_units` (sum of backorder_quantity).

---

## 3. Kit replenishment playbook
*Cover one or more BOM builds at a planning site. component_plan (one row per distinct component SKU across all target BOMs, sorted by sku), plus transfers, purchase requisitions, exclusions, summary.*

`kit_targets`: per target build, `bom_id`, `kit_name` (= BOM `name`), `warehouse_id` (= BOM build site / planning site), `build_quantity` and `build_date` (from the memo, overriding BOM `target_date`).

For each distinct component SKU:
1. **`total_required`** = Σ over all target BOMs containing it of `quantity_per_kit × that BOM's build_quantity`.
2. **`target_effective_available`** = effective available at the **build/planning warehouse** (signed; subtract safety_stock).
3. **Gap** = `total_required − target_effective_available`. If gap ≤ 0 → component is overstocked/covered at target → `final_action = overstock_excluded`, `exclusion_reason = target_overstock`, all qtys 0, also list it in `excluded_components` (reason `target_overstock`).
4. **Timely PO coverage**: incoming POs for this SKU that are **same warehouse as the build site**, status `open` or `confirmed`, and `eta` on/before the build need date. `timely_po_qty` = their total quantity; `coverage_po_ids` = their po_ids (sorted). If `timely_po_qty ≥ gap` → fully covered → `final_action = timely_po_covered`, `exclusion_reason = timely_po_covers_gap`, transfer/purchase 0, and add to `excluded_components` (reason `timely_po_covers_gap`, `supporting_po_ids` = those POs). The *covered* contribution counted in the summary is the gap covered (cap at gap), not the raw PO quantity.
5. **Transfers** (only if gap not covered by timely POs): pull from other warehouses' effective available. Multi-source allowed — take available effective from each other warehouse until the gap (after timely POs) is filled or sources are exhausted. `transfer_qty` = total transferred. Emit transfer_requests `{sku, from_warehouse_id, to_warehouse_id (=build site), quantity, needed_by}`; `needed_by` = the earliest build_date among BOMs needing this SKU. (Kit transfers may split across warehouses — unlike line allocation.)
6. **Purchase requisition** (remaining gap after timely POs and transfers): `purchase_requisition_qty = remaining`. Emit `{sku, supplier_id (=product.supplier_id), warehouse_id (=build site), quantity, needed_by (=latest build_date among BOMs needing it), unit_cost (=product.unit_cost), extended_cost (=round(unit_cost×qty,2))}`.
7. **`final_action`**: `overstock_excluded` / `timely_po_covered` / `no_action_stocked` (gap>0 but… typically not; usually) / `transfer_only` (transfers fully close the gap, no purchase) / `purchase_required` (any purchase qty). Choose the one that reflects how the gap was closed.

**Orderings**: component_plan & purchase_requisitions & excluded_components by sku asc; transfer_requests by sku asc, then quantity desc, then from_warehouse_id asc.

**Summary**: `component_count` (distinct SKUs in component_plan), `total_purchase_units`, `total_purchase_cost` (2 dp), `total_transfer_units`, `timely_po_covered_units` (sum of the gap covered by timely POs across SKUs).

---

## 4. Incident scorecard playbook
*Supplier-quality scorecard over a date window. One row per supplier with ≥1 filtered incident, sorted by supplier_id.*

**This task usually embeds the full policy in its payload** (date filter, duration rule, percentage rule, precisions, severe-severity set, recommendation precedence + per-code conditions). **Implement that payload policy literally.** The shape below is the typical structure; the thresholds/precedence come from the payload.

1. **Filter**: `/incidents?start=&end=` on `open_date`, inclusive, plus any other given filters. This is the denominator population.
2. **Per supplier**: `incident_count`; `incident_percentage` = count / filtered_total × 100 (1 dp); `total_resolution_cost` (2 dp); `avg_duration_days` (closed: close−open days; open: analysis_date−open days; average to 2 dp); `rma_count`, `work_order_count` (by `incident_type`); `open_incident_count` (`status==open`); `severe_incident_count` (`severity` in the payload's severe set, typically {high, critical}).
3. **`recommendation_code`**: apply the payload's precedence top-down — first matching code wins. A typical policy:
   - **ESCALATE_SUPPLIER** if (quality_status `quality_hold` AND count ≥ 3) OR any **critical RMA** OR (RMA count ≥ 3 AND total cost ≥ threshold).
   - **PROCESS_REVIEW** if WORK_ORDER count ≥ 3 AND WORK_ORDER > RMA.
   - **WATCHLIST** if quality_status in {watch, quality_hold} OR count ≥ threshold OR total cost ≥ threshold OR severe ≥ 2.
   - **MONITOR** otherwise.
   Use the exact numbers/conditions from the payload, not these placeholders.
4. **`summary`**: `filtered_incident_count`, `supplier_count` (suppliers with ≥1 filtered incident), `total_resolution_cost`, `overall_rma_count`, `overall_work_order_count`.
5. **`top_escalation_suppliers`**: supplier_ids whose code is ESCALATE_SUPPLIER, ordered by the payload's top-escalation order (e.g. incident_count desc, then total_resolution_cost desc, then supplier_id asc).
6. **`highest_cost_supplier_id`** = supplier with max total_resolution_cost; **`highest_share_supplier_id`** = supplier with max incident_count (ties → lowest supplier_id, or the payload's stated tie-break).

---

## 5. Replenishment control playbook
*Quality-control review of named suppliers → freeze / buyer_review / monitor + held POs. One decision per `target_supplier_ids`, sorted by supplier_id.*

The payload gives the analysis window and the decision choices but often **not** an explicit formula — infer a sensible ladder and apply it consistently. Use the recent window from the payload (this is usually a *different*, more recent window than a Q1 scorecard).

Per supplier:
1. **Recent incident metrics** over the payload window: `recent_incident_count`, `recent_rma_count` (RMA), `severe_or_critical_count` (severity in {high, critical}), `open_incident_count` (`status==open`), `affected_skus` (distinct SKUs, sorted), `sample_incident_ids` (sorted, cap 5). Pull `quality_status` from `/suppliers`.
2. **Decision ladder** (precedence top-down; tune thresholds to the payload but keep the ordering):
   - `freeze_new_replenishment` — strongest control: supplier on `quality_hold` (especially with recent incident activity / multiple recent incidents). This is the hard stop.
   - `buyer_review_required` — elevated but not frozen: notable severe/critical activity (e.g. severe_or_critical_count ≥ 2) or a `watch` status with concerning signals, warranting a buyer to look before releasing.
   - `monitor_only` — none of the above triggers; routine watching only.
   Apply the same thresholds to every supplier in the batch; do not special-case.
3. **`held_po_ids`** (per supplier): if the decision is `freeze_new_replenishment` or `buyer_review_required`, hold the supplier's **open or confirmed** POs, sorted ascending by po_id, capped at the first 5. If the decision is `monitor_only`, hold **none** (empty list). The hold is driven by the *decision*, not by which SKUs were affected — take the earliest 5 of all the supplier's open/confirmed POs.
4. **Top level**: `held_po_ids` (sorted unique union of all suppliers' held POs); `release_supplier_ids` (suppliers whose decision is `monitor_only`, sorted).
5. **`summary`**: `suppliers_reviewed`, `freeze_count`, `buyer_review_count`, `monitor_count`, `held_po_count` (size of the union), `total_recent_incidents` (sum of per-supplier `recent_incident_count`).

---

## Cross-task reconciliation checklist
- Memo names entities; live ERP supplies all numbers, statuses, costs, supplier links, and active flags. Re-derive everything from the API.
- Same effective-stock formula everywhere (sources included).
- Risk gate → product gate → stock math, in that order.
- Use the date window, precisions, enums, and orderings from THIS task's payload/template.
- Output only the JSON the template defines; verify every key, enum, ordering, dedupe, rounding, and that summary totals equal the detail they roll up.
