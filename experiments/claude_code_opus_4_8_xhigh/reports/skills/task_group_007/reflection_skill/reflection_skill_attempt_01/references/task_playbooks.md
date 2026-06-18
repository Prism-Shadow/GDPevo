# Northwind ERP Task Playbooks

Field-by-field SOPs for each task type. Read the section that matches your task after identifying it
from the answer_template's top-level keys. All shared primitives (effective available, safety
protection, account gating, classification, incident windows, PO eligibility, decision policies,
output conventions) are defined in SKILL.md §0–§8 — this file assumes them and focuses on the
per-task wiring and the pitfalls that bit a prior solver.

## Table of contents
1. Expedite queue (dispatch control)
2. Allocation (mixed-warehouse transfer file)
3. Replenishment plan (kit build)
4. Incident scorecard
5. Quality control review (replenishment freeze)

---

## 1. Expedite queue (dispatch control)

Template keys: `wave_id`, `records[]`, `summary`. Each record:
`order_id, inventory_status, customer_exception, final_decision, next_action, shortage_skus,
inactive_skus, low_stock_skus, shipping_quote`.

### Steps
1. Read the memo's `order_ids` (a subset of the wave). Fetch each via `GET /orders/<id>`.
2. **Compute `wave_demand` per (warehouse, sku)** by summing line quantities across **all the memo's
   orders** at each warehouse — you need this for low_stock (SKILL.md §2). Do this before
   classifying any line.
3. For each order, classify every line at the order's warehouse (SKILL.md §2):
   - `shortage_skus` = SKUs with `eff < qty + safety_stock`.
   - `low_stock_skus` = non-shortage SKUs with `eff - wave_demand < safety_stock`.
   - `inactive_skus` = SKUs with `active == false`.
   - Sort each list ascending; `[]` if none.
   - Derive order-level `inventory_status` by the precedence in SKILL.md §2.
4. `customer_exception` from SKILL.md §3 precedence, mapped to the enum
   {none, review_required, account_blocked, fraud_watch, credit_watch}.
5. `final_decision` / `next_action` from SKILL.md §7 (account gate beats inventory).
6. `shipping_quote`: weight_lb = `sum(line.quantity * product.weight_lb)` over the order;
   call `GET /shipping/quote?warehouse_id=<order.warehouse>&destination_zip=<order.destination_zip>
   &weight_lb=<weight>&speed=<order.shipping_speed>`. Copy `zone_distance`, `service_days`, and
   `total_cost` (→ `total_cost_usd`, 2 dp) **verbatim from the API** — do not recompute the rate.
   Use the order's own `shipping_speed` unless a memo note explicitly overrides the speed for that
   order.
7. Sort `records` by `order_id` ascending.

### Summary
`order_count`; `decision_counts` (one integer per final_decision enum, including zeros);
`total_shipping_cost_usd` (2 dp sum of the quotes); and the id lists
`blocked_order_ids` (account_blocked), `manual_review_order_ids` (final_decision == manual_review),
`backorder_order_ids` (final_decision == backorder), `inactive_sku_order_ids` (orders with ≥1
inactive sku). Recount all of these from the records you emitted.

### Pitfalls (observed)
- **Reporting low_stock SKUs only on otherwise-clean orders.** low_stock is a per-(warehouse,sku)
  flag and must appear on shortage orders too if the SKU qualifies. Missing these also corrupts the
  decision_counts (a low_stock-only order that you misread as ready, or a shortage order you misread
  as low_stock, flips backorder↔delayed_release).
- **Using `eff < qty` for shortage.** Use `eff < qty + safety_stock`; otherwise lines that fill but
  breach safety are wrongly called ready/low_stock instead of shortage.
- **Forgetting wave_demand for low_stock.** A SKU shared across multiple orders in the wave can be
  low_stock purely from the combined draw.

---

## 2. Allocation (mixed-warehouse transfer file)

Template keys: `wave_id`, `line_actions[]`, `transfer_requests[]`, `blocked_orders[]`,
`order_rollup[]`, `summary`. Each line action:
`order_id, line_id, sku, requested_warehouse, requested_effective_available, action, ship_quantity,
transfer_from, transfer_quantity, backorder_quantity, primary_reason`.

### Effective available here is SAFETY-PROTECTED
The memo language ("reserved, quarantined, or held as normal operating buffer should not be treated
as freely available") means:
`requested_effective_available = on_hand - reserved - quarantined - safety_stock` at the requested
warehouse. Report it as-is (can be negative). Usable-to-ship from the requested warehouse =
`max(0, requested_effective_available)`.

### Per-line decision (first applicable)
1. **Account/risk gate** (order-wide, SKILL.md §3) → `action = manual_review`, `primary_reason` in
   {account_blocked, fraud_watch, account_review_required}. (credit_watch, if present, also routes
   to manual_review.) These orders go in `blocked_orders`.
2. **Inactive product** (line-only) → `action = manual_review`, `primary_reason = inactive_product`.
   NOT added to `blocked_orders` (it's a line-level product review, not an account stop).
3. **Inventory** (active product, no account gate):
   - usable-here `>= qty` → `ship`, `ship_quantity = qty`, `primary_reason = none`.
   - else if a single other warehouse's protected availability (`eff - safety_stock`) covers the
     remainder `qty - usable_here` → `transfer`: `ship_quantity = usable_here`,
     `transfer_quantity = remainder`, `transfer_from = the single source with the greatest protected
     availability` (SKILL.md §0.4 / §5). `primary_reason = none`.
   - else → `backorder`: `ship_quantity = usable_here`, `backorder_quantity = remainder`,
     `primary_reason = insufficient_effective_stock`.

`transfer_requests`: one row per transfer line (`order_id, line_id, sku, from_warehouse,
to_warehouse, quantity`), sorted by order_id then line_id.

### Order rollup (`outcome` per order)
- account/risk-blocked order → `manual_review`.
- all lines ship → `ready_to_ship`.
- lines all one fulfillment type: only transfers (+ships) → `needs_transfer`; backorders (+ships,
  no transfer) → `has_backorder`.
- a mix of fulfillment types, or fulfillment mixed with a line-level product review →
  `mixed_actions`.

### Summary
Integer counts: `total_orders, total_lines, ship_lines, transfer_lines, backorder_lines,
manual_review_lines, blocked_orders, transfer_units` (sum of transfer_quantity),
`backorder_units` (sum of backorder_quantity). Recount from the emitted lines.

### Pitfalls (observed)
- **Transfer source chosen by fixed warehouse order instead of most-available.** Pick the source
  with the largest `eff - safety_stock`. This was the only error in an otherwise-correct allocation
  answer — it silently changed `transfer_from` and the transfer_requests rows.
- Forgetting to subtract safety_stock from `requested_effective_available`.
- Putting inactive-product line reviews into `blocked_orders` (they don't belong there).

---

## 3. Replenishment plan (kit build)

Template keys: `task_id`, `plan_date`, `kit_targets[]`, `component_plan[]`, `transfer_requests[]`,
`purchase_requisitions[]`, `excluded_components[]`, `summary`.

### Demand
For each BOM in the memo, fetch it live (name, warehouse, components). For each component SKU,
`total_required = sum over BOMs that use it of (quantity_per_kit * build_quantity)`. A SKU used in
multiple BOMs sums across them.

`needed_by` per SKU:
- Build dates come from the memo's `target_builds` (use the memo's `target_build_date`, not the
  BOM's internal `target_date`, when the memo supplies build dates).
- A SKU in a single build → that build's date for both transfer and purchase rows.
- A SKU spanning multiple builds → **transfer rows use the earliest build date; purchase
  requisition uses the latest build date.** (The earliest build is what pulls transfers forward;
  the residual purchase can land by the last build.)

### Per-component waterfall (at the build warehouse, e.g. WH_WEST)
Let `eff = effective_available` at the build warehouse, `ss = safety_stock`,
`over = overstock_threshold`.

1. **`target_effective_available = eff - safety_stock`.** Report this field as that value (can be
   negative). This is THE field a prior solver got wrong by reporting plain `eff`.
2. **Overstock exclusion:** if `eff > over` → `final_action = overstock_excluded`,
   `exclusion_reason = target_overstock`, no replenishment. (Test against raw `eff`, not the
   safety-adjusted target.)
3. **`gap = total_required - target_effective_available`** = `total_required - (eff - ss)`. The gap
   therefore already reserves destination safety stock. If `gap <= 0` (and not overstock) →
   `no_action_stocked` / `stocked_no_gap`, transfer 0, purchase 0.
4. **Timely PO coverage:** eligible PO = same build warehouse AND `status in {open, confirmed}` AND
   `eta <= needed_by`. `timely_po_qty` = sum of eligible PO quantities (report the full eligible
   quantity). If `timely_po_qty >= gap` → `timely_po_covered` / `timely_po_covers_gap`,
   `coverage_po_ids` = sorted eligible PO ids, transfer 0, purchase 0.
5. **Transfers:** cover the post-PO remaining gap from other warehouses, greedily from the source
   with the greatest protected availability (`eff_source - safety_stock`) first, never exceeding a
   source's protected availability (SKILL.md §5). Sum into `transfer_qty`; emit one
   `transfer_requests` row per (sku, source).
6. **Purchase requisition:** any units still uncovered → `purchase_requisition_qty`, purchased at
   the build warehouse from `product.supplier_id`, `unit_cost = product.unit_cost`,
   `extended_cost = round(unit_cost * quantity, 2)`. `final_action = transfer_only` if transfers
   clear the gap with purchase 0; else `purchase_required`. `exclusion_reason = none`.

`excluded_components` = components with a non-`none` exclusion_reason (overstock or timely-PO or
stocked-no-gap), with `supporting_po_ids` (the timely PO ids for timely_po_covers_gap, else `[]`).

### Summary
`component_count`; `total_purchase_units` (sum purchase qty); `total_purchase_cost` (sum extended,
2 dp); `total_transfer_units` (sum transfer qty); `timely_po_covered_units` = the **gap covered by
timely POs**, i.e. the sum of `min(gap, timely_po_qty)` over timely-covered components (NOT the full
PO quantity).

### Sorts
`component_plan`, `purchase_requisitions`, `excluded_components`, `kit_targets` by sku/bom_id
ascending. `transfer_requests` by sku asc, then quantity desc, then from_warehouse_id asc.

### Pitfalls (observed)
- **`target_effective_available` reported as plain `eff`** instead of `eff - safety_stock`. This
  also makes every `gap` too small, undercounting purchases and transfers across the board.
- **Gap computed against plain `eff`** rather than the safety-adjusted target — under-transfers and
  under-purchases.
- **Transfers split across sources by fixed order** rather than greedy-most-available; a single rich
  source should be used alone if it covers the gap.
- **`timely_po_covered_units` set to the full PO quantity** instead of the covered gap.

---

## 4. Incident scorecard

Template keys: `analysis_window`, `summary`, `supplier_scorecard[]`, `top_escalation_suppliers[]`,
`highest_cost_supplier_id`, `highest_share_supplier_id`. Driven by a request payload that gives the
window, precision rules, severe values, and an explicit `recommendation_policy` — **follow that
policy literally and in its stated precedence.**

### Steps
1. Filter incidents by the payload window on `open_date` (SKILL.md §6). The simplest robust call is
   `GET /incidents?start=<start>&end=<end>`; this is the whole population.
2. Group by `supplier_id`. For each supplier with ≥1 filtered incident:
   - `incident_count`; `incident_percentage = round(incident_count / total_filtered * 100, 1)`.
   - `total_resolution_cost = round(sum(resolution_cost), 2)` (open incidents included).
   - `avg_duration_days = round(mean(duration), 2)` where duration is per SKILL.md §6 (open → to
     analysis_date; closed → actual close_date, uncapped).
   - `rma_count` / `work_order_count` by `incident_type`.
   - `open_incident_count` = status open.
   - `severe_incident_count` = severity in the payload's `severe_severity_values` (high/critical).
   - `recommendation_code` from the payload's policy precedence (first match). Read each condition
     literally (e.g. "quality_hold with ≥3 incidents", "any critical RMA", "≥3 RMAs and ≥ $X cost",
     "WORK_ORDER ≥3 and exceeding RMAs", watch/cost/severe thresholds, else MONITOR).
3. Sort `supplier_scorecard` by `supplier_id` ascending.
4. `top_escalation_suppliers` = supplier_ids whose code is ESCALATE_SUPPLIER, sorted by
   incident_count desc, then total_resolution_cost desc, then supplier_id asc.
5. `highest_cost_supplier_id` = supplier with max total_resolution_cost; `highest_share_supplier_id`
   = supplier with max incident_count (share). Break ties by supplier_id ascending.
6. Summary: `filtered_incident_count`, `supplier_count` (suppliers with ≥1 filtered incident),
   `total_resolution_cost` (2 dp), `overall_rma_count`, `overall_work_order_count`.

### Pitfalls
- Capping `close_date` at the analysis date (don't, unless told) or excluding open incidents from
  cost (don't). This task type is a high-fidelity one — when the payload spells out the rules,
  precision in following them is the whole game.

---

## 5. Quality control review (replenishment freeze)

Template keys: `analysis_window`, `supplier_decisions[]`, `held_po_ids`, `release_supplier_ids`,
`summary`. Driven by a request with `target_supplier_ids`, an analysis window, `decision_choices`,
and a (often non-numeric) `policy`. Per supplier row:
`supplier_id, supplier_name, quality_status, recent_incident_count, recent_rma_count,
severe_or_critical_count, open_incident_count, affected_skus, sample_incident_ids, decision,
held_po_ids`.

### Steps
1. For each target supplier, fetch incidents in the window
   (`GET /incidents?start=&end=&supplier_id=`, SKILL.md §6) and compute:
   - `recent_incident_count`, `recent_rma_count` (incident_type RMA),
     `severe_or_critical_count` (severity high/critical), `open_incident_count` (status open).
   - `affected_skus` = sorted unique SKUs of those incidents.
   - `sample_incident_ids` = the **first 5** incident ids by ascending id (the "maximum 5" cap).
2. `quality_status` and `supplier_name` from `GET /suppliers`.
3. `decision` via the policy. If the payload gives explicit thresholds, use them. If not, use the
   validated default (SKILL.md §7): freeze ⇔ quality_hold; buyer_review ⇔ watch AND
   severe_or_critical_count ≥ 2; else monitor_only. A lone critical incident does not force a freeze.
4. `held_po_ids` per supplier: if the decision **holds** POs (freeze OR buyer_review — monitor holds
   none), list the **first 5 open/confirmed POs by `po_id` ascending** for that supplier
   (`GET /purchase_orders?supplier_id=`, filter status in {open, confirmed}, sort by po_id, take 5).
   No SKU/ETA filter. monitor_only → `[]`.
5. Sort `supplier_decisions` by supplier_id ascending.
6. Top-level `held_po_ids` = sorted unique union of all per-supplier held lists.
   `release_supplier_ids` = sorted supplier_ids whose decision is `monitor_only`.
7. Summary: `suppliers_reviewed`, `freeze_count`, `buyer_review_count`, `monitor_count`,
   `held_po_count` (len of the top-level held set), `total_recent_incidents` (sum of
   recent_incident_count).

### Pitfalls (observed — this task type was the most error-prone)
- **Assuming only freeze holds POs.** buyer_review also holds POs; only monitor releases.
- **Holding ALL open/confirmed POs.** Hold only the first 5 by po_id (the cap mirrors the sample
  cap). Holding all inflates held_po_ids and held_po_count.
- **Letting a critical incident on a watch supplier force a freeze.** It doesn't — status drives the
  freeze; a watch supplier needs the severe-count threshold to even reach buyer_review.
- **Forgetting `release_supplier_ids`** = the monitor_only suppliers (often non-empty even when no
  one is "released" in plain English).
