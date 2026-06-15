# Northwind ERP — Task Family Playbooks

Detailed decision logic for each task family. Read the section for the family you are solving.
All families share the core `eff_avail` formula and JSON conventions from `SKILL.md`.

## Table of contents
1. [Expedite queue (dispatch control)](#1-expedite-queue-dispatch-control)
2. [Kit replenishment (BOM build)](#2-kit-replenishment-bom-build)
3. [Incident scorecard (supplier quality)](#3-incident-scorecard-supplier-quality)
4. [Allocation desk (mixed-warehouse)](#4-allocation-desk-mixed-warehouse)
5. [Procurement quality (replenishment control)](#5-procurement-quality-replenishment-control)

---

## 1. Expedite queue (dispatch control)

**Goal:** for each order in the memo, classify inventory, customer exception, a final decision, a
next action, three per-SKU exception lists, and a parcel quote; then a summary.

**Scope:** exactly the order_ids the memo lists — not the whole wave.

### Per-line inventory (at the order's `warehouse_id`)
Use the core classification: `shortage` if `eff_avail < qty`; `low_stock` if
`eff_avail >= qty AND eff_avail < safety_stock`; else `ready`. Inactive if `product.active == false`.

### Per-SKU exception lists (independent; sorted asc; report regardless of order-level status)
- `shortage_skus`: every line SKU classified shortage.
- `low_stock_skus`: every line SKU classified low_stock.
- `inactive_skus`: every line SKU with `active == false`.

> A SKU that is both inactive and short appears in both `inactive_skus` and `shortage_skus`.
> `low_stock_skus` can be non-empty even when the order's overall `inventory_status` is `shortage`.

### Order-level `inventory_status` (precedence, first match)
1. `inactive_and_shortage` — any inactive SKU AND any shortage SKU
2. `inactive_sku` — any inactive SKU (no shortage)
3. `shortage` — any shortage SKU
4. `low_stock` — any low_stock SKU
5. `ready` — otherwise

### `customer_exception` (from the order's customer; precedence top-down)
`account_blocked` (account_status blocked) → `fraud_watch` (risk_flag fraud_watch) →
`credit_watch` (risk_flag credit_watch) → `review_required` (account_status review_required) →
`none`.

### `final_decision` + `next_action` (precedence, first match wins)
| # | Condition | final_decision | next_action |
|---|-----------|----------------|-------------|
| 1 | account_blocked OR fraud_watch OR credit_watch | `reject_hold` | `hold_credit_or_fraud` |
| 2 | customer review_required | `manual_review` | `send_account_review` |
| 3 | any inactive SKU | `manual_review` | `escalate_product_master` |
| 4 | any shortage SKU | `backorder` | `create_backorder` |
| 5 | any low_stock SKU | `delayed_release` | `delay_and_monitor` |
| 6 | else (ready) | `ship_now` | `release_to_pick` |

> Key precedence fix: **account review_required (#2) is ABOVE inactive product (#3).** When both
> apply the line is `manual_review` either way, but `next_action` must be `send_account_review`,
> not `escalate_product_master`. Account/risk reasons always outrank product-master ones.

### `shipping_quote`
Always quote (even for non-release decisions — the desk may still need the number).
`weight_lb = sum over ALL lines of quantity * product.weight_lb`; `speed = order.shipping_speed`.
Output `zone_distance`, `service_days`, `total_cost_usd = total_cost` from the quote response.

### Summary
- `order_count`, `decision_counts` (one integer per final_decision enum — include zeros).
- `total_shipping_cost_usd` = sum of all `total_cost_usd`, rounded 2dp.
- `blocked_order_ids` = orders with `reject_hold`. `manual_review_order_ids` = orders with
  `manual_review`. `backorder_order_ids` = orders with `backorder`. `inactive_sku_order_ids` =
  orders whose `inactive_skus` is non-empty. All sorted ascending; recompute from your records.

---

## 2. Kit replenishment (BOM build)

**Goal:** aggregate component demand for the requested builds at the planning warehouse, net live
stock, cover gaps with timely POs → transfers → purchases, and flag exclusions.

**Scope:** the BOMs/builds named in the memo, built at the memo's planning warehouse (e.g. WH_WEST).

### Demand
- `total_required[sku] = sum over builds of (quantity_per_kit * build_quantity)`. A SKU in multiple
  BOMs sums across them.
- `target_effective_available[sku]` (`tea`) = `eff_avail` at the **planning warehouse** (report as-is,
  may be negative).
- `gap = total_required - tea`.

### Dates (per SKU, by the build_date(s) of the BOMs that consume it)
- **Transfer `needed_by` = the EARLIEST consuming build_date** (transfers must support the first build).
- **Purchase requisition `needed_by` = the LATEST consuming build_date** (the purchase covers the
  later-dated remainder; longer lead time only needs to land by the final build).

> Pitfall: for a SKU shared across builds, do not put the same date on transfers and purchases.
> A SKU built on both 06-06 and 06-10 takes transfer `needed_by = 06-06` and purchase
> `needed_by = 06-10`. Conceptually, earliest-due demand is filled first (by on-hand + transfers)
> and the residual that purchases cover is the later-dated bucket.

### Timely POs
A **timely PO** is a purchase order at the **planning warehouse** with `status in {open, confirmed}`
and `eta <= needed_by` (an open PO with a past ETA is overdue but still counts as inbound). Filter
to the component SKUs.
- Component field `timely_po_qty` = the **full PO quantity** of qualifying POs (sum), per the field
  definition. `coverage_po_ids` = those PO ids, sorted.

### Coverage waterfall (per SKU, in order)
1. `tea >= overstock_threshold` → `overstock_excluded` / exclusion_reason `target_overstock`. No
   transfer/purchase. (Overstock outranks a zero gap.)
2. `gap <= 0` → `no_action_stocked` / `stocked_no_gap`.
3. `timely_po_qty >= gap` → `timely_po_covered` / `timely_po_covers_gap`.
4. Otherwise cover `remaining = gap - timely_po_qty` with transfers, then purchase the residual:
   - all of `remaining` cleared by transfers → `transfer_only`
   - residual after transfers → `purchase_required`
   - exclusion_reason `none` for 4.

### Transfers — source selection (greedy, largest first)
Candidate sources = other warehouses (not the planning warehouse) with positive `eff_avail` for the
SKU. Allocate `remaining` greedily from sources in **descending `eff_avail`**:
- If a single source's `eff_avail >= remaining`, take it all from that one source → **one transfer
  row**.
- Otherwise drain the largest source fully, then the next, until covered. Each row = one source.

> Pitfall: do not arbitrarily cap the top source or split unnecessarily. When the biggest source
> can cover the whole remaining quantity alone, emit a single transfer row from it. Only split when
> no single source suffices. (`transfer_qty` on the component = total transferred.)

Each transfer row: `sku`, `from_warehouse_id`, `to_warehouse_id` (= planning warehouse),
`quantity`, `needed_by` (earliest build date). Sort transfers per template: sku asc, then quantity
desc, then from_warehouse_id asc.

### Purchase requisitions
`quantity` = residual after timely-PO + transfers. `supplier_id = product.supplier_id`,
`warehouse_id` = planning warehouse, `needed_by` = latest consuming build date,
`unit_cost = round(product.unit_cost, 2)`, `extended_cost = round(unit_cost * quantity, 2)`.

### Excluded components
List SKUs whose action is an exclusion (`overstock_excluded`, `timely_po_covered`,
`no_action_stocked`) with the matching `reason` and `supporting_po_ids` (the coverage PO ids for the
timely-covered case, else `[]`).

### Summary
- `component_count` = distinct components planned.
- `total_purchase_units` = sum of purchase quantities; `total_purchase_cost` = sum of extended_costs (2dp).
- `total_transfer_units` = sum of transfer quantities.
- **`timely_po_covered_units` = sum over timely-covered components of `min(gap, timely_po_qty)`** —
  i.e. the GAP actually covered, **not** the full PO quantity.

> Pitfall: the component-level `timely_po_qty` keeps the full PO size, but the summary
> `timely_po_covered_units` rollup is the demand actually covered (`min(gap, timely_po_qty)`).
> Mixing these up inflates the summary.

---

## 3. Incident scorecard (supplier quality)

**Goal:** scorecard over the filtered incident population for the window, one row per supplier with
≥1 filtered incident, plus escalation list and overall summary. The request payload carries the
exact policy — follow it; the rules below are the validated baseline.

### Population
`GET /incidents?start=<start>&end=<end>` (server filters `open_date` inclusive). Join to `/suppliers`
for `name` and `quality_status`.

### Per-supplier metrics
- `incident_count` = filtered incidents for the supplier.
- `incident_percentage = round(incident_count / total_filtered * 100, 1)` (denominator = full
  filtered population, not a per-type subset).
- `total_resolution_cost` = sum `resolution_cost` (2dp).
- `avg_duration_days` = mean per-incident duration (2dp). Duration = `close_date - open_date` in
  calendar days for closed incidents; `analysis_date - open_date` for open/unclosed ones.
- `rma_count` / `work_order_count` = `incident_type` RMA / WORK_ORDER.
- `open_incident_count` = `status == open`.
- `severe_incident_count` = `severity in {high, critical}`.

### `recommendation_code` (precedence: ESCALATE → PROCESS_REVIEW → WATCHLIST → MONITOR)
Apply the payload's `recommendation_policy.codes`. Validated reading:
1. **ESCALATE_SUPPLIER** if `quality_status == quality_hold AND incident_count >= 3`, OR any
   **critical RMA** (incident_type RMA AND severity critical), OR (`rma_count >= 3 AND
   total_resolution_cost >= 15000.00`).
2. **PROCESS_REVIEW** if `work_order_count >= 3 AND work_order_count > rma_count`.
3. **WATCHLIST** if `quality_status in {watch, quality_hold}` OR `incident_count >= 4` OR
   `total_resolution_cost >= 12000.00` OR `severe_incident_count >= 2`.
4. **MONITOR** otherwise.

> "critical RMA" means an RMA-type incident with critical severity — a critical WORK_ORDER does not
> trigger that branch (it may still escalate via the 3-RMA/cost branch). Watch this distinction.

### Derived outputs
- `top_escalation_suppliers` = supplier_ids with ESCALATE_SUPPLIER, ordered by `incident_count` desc,
  then `total_resolution_cost` desc, then `supplier_id` asc.
- `highest_cost_supplier_id` / `highest_share_supplier_id` = supplier with max total_resolution_cost /
  max incident_count (ties → supplier_id asc).
- `summary`: `filtered_incident_count`, `supplier_count` (suppliers with ≥1 filtered incident),
  `total_resolution_cost`, `overall_rma_count`, `overall_work_order_count`.

---

## 4. Allocation desk (mixed-warehouse)

**Goal:** classify every order line in the wave as ship / transfer / backorder / manual_review,
emit single-source transfer requests, blocked orders, an order rollup, and a summary.

**Scope:** all orders in the wave (`GET /orders?wave=<wave>`), all lines.

### Per-line decision (precedence, first match)
1. **Account/risk block (order-level):** customer `blocked` → manual_review /
   `account_blocked`; `fraud_watch` → manual_review / `fraud_watch`; `review_required` →
   manual_review / `account_review_required`. Every line of such an order is manual_review and the
   order joins `blocked_orders`. (`account_blocked` outranks `account_review_required`;
   credit_watch alone is not a line reason here.)
2. **Inactive product (line-level):** `active == false` → manual_review / `inactive_product`.
3. **Ship:** requested-warehouse `eff_avail >= qty` → `ship`, `ship_quantity = qty`.
4. **Transfer:** requested warehouse can't cover alone, but ONE other warehouse can cover the
   remainder. `ship_quantity = max(eff_avail, 0)` from the requested warehouse; choose a **single**
   source warehouse whose `eff_avail >= remainder` (`remainder = qty - ship_quantity`);
   `transfer_quantity = remainder`. Emit a transfer_request.
5. **Backorder:** no single warehouse can cover the remainder → `backorder`,
   `ship_quantity = max(eff_avail, 0)`, `backorder_quantity = qty - ship_quantity`, reason
   `insufficient_effective_stock`.

`requested_effective_available` is always the true `eff_avail` (may be negative), even on blocked /
manual_review lines.

> The transfer source is a single warehouse per row (the template has one `from_warehouse`). If you
> would need to split across two warehouses to cover the remainder, that is a backorder, not a
> transfer. Prefer the source with enough standalone `eff_avail`.

### `order_rollup.outcome` (per order, from its line actions)
- all lines `manual_review` → `manual_review`
- all lines `ship` → `ready_to_ship`
- ship + transfer (a transfer present, no backorder/review) → `needs_transfer`
- ship + backorder (a backorder present, no transfer/review) → `has_backorder`
- otherwise multiple distinct action types → `mixed_actions`

### `blocked_orders` and summary
`blocked_orders` = orders stopped at the account/customer-risk level (case 1) — **not** line-only
product reviews. Sorted ascending.
`summary` integers: `total_orders`, `total_lines`, `ship_lines`, `transfer_lines`,
`backorder_lines`, `manual_review_lines`, `blocked_orders` (count), `transfer_units` (sum of
transfer quantities), `backorder_units` (sum of backorder quantities). Recompute all from records.

---

## 5. Procurement quality (replenishment control)

**Goal:** for each target supplier, compute recent-incident metrics, pick a control decision, and
hold the right POs; then global rollups.

**Scope:** the `target_supplier_ids` in the memo, over the memo's analysis window.

### Per-supplier metrics (incidents in window, by `open_date`)
`GET /incidents?start=<start>&end=<end>&supplier_id=<id>`:
- `recent_incident_count` = count; `recent_rma_count` = RMA-type;
  `severe_or_critical_count` = `severity in {high, critical}`; `open_incident_count` = `status open`.
- `affected_skus` = sorted unique incident SKUs.
- `sample_incident_ids` = incident ids sorted ascending, **capped at 5** (sort first, then take 5).
- `quality_status` from `/suppliers`.

### `decision` (precedence, first match)
1. `freeze_new_replenishment` if `quality_status == quality_hold`.
2. `buyer_review_required` if `severe_or_critical_count >= 2`.
3. `monitor_only` otherwise.

> Pitfall (high impact): `quality_status == watch` does **NOT** by itself force buyer_review, and a
> single lone `critical` incident does **NOT** either. The escalation trigger for a non-hold
> supplier is the **severe-or-critical count reaching 2**. A `watch` supplier with only 1
> severe/critical incident (even if that one is critical) is `monitor_only`. Do not map status→action.

### Held POs
- `monitor_only` suppliers hold **no** POs (`held_po_ids = []`).
- Suppliers with `freeze_new_replenishment` or `buyer_review_required` hold POs from their
  `open`/`confirmed` purchase orders, sorted by `po_id` ascending and **capped at the first 5**.

> Pitfall: do not hold every open/confirmed PO. The held set is the first 5 by `po_id` (same cap
> pattern as `sample_incident_ids`), and only for non-monitor suppliers.

### Rollups
- `held_po_ids` (top-level) = sorted unique union of all suppliers' held POs.
- `release_supplier_ids` = supplier_ids whose decision is `monitor_only`, sorted.
- `summary`: `suppliers_reviewed`, `freeze_count`, `buyer_review_count`, `monitor_count`,
  `held_po_count` (= len of the top-level held list), `total_recent_incidents` (sum of
  `recent_incident_count`). Recompute from records.
