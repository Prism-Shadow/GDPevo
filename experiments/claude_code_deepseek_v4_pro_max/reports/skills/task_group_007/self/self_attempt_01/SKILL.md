# Northwind Components ERP — Operations Skill

Shared ERP API for dispatch, replenishment, supplier quality, allocation, and procurement control desk workflows.

## API Reference

**Base URL:** provided by the runner (see `environment_access.md` — do not assume localhost).

### Endpoints

| Endpoint | Query Parameters | Notes |
|---|---|---|
| `GET /products` | — | All products; key fields: `active`, `safety_stock`, `overstock_threshold`, `unit_cost`, `weight_lb`, `supplier_id` |
| `GET /products/<sku>` | — | Single-product lookup |
| `GET /customers` | — | All customers; `account_status` (`active`/`blocked`/`review_required`), `risk_flag` (`none`/`fraud_watch`/`credit_watch`) |
| `GET /customers/<id>` | — | Single-customer lookup |
| `GET /warehouses` | — | Three sites: `WH_NORTH` (07102), `WH_CENTRAL` (60607), `WH_WEST` (89502) |
| `GET /inventory` | `warehouse_id`, `sku` (both optional) | `on_hand`, `reserved`, `quarantined`; filter by warehouse, SKU, or both |
| `GET /orders` | `wave`, `required_date`, `customer_id` (all optional) | Order with `lines[]`; each line has `line_id`, `sku`, `quantity`, `unit_price` |
| `GET /orders/<id>` | — | Single order |
| `GET /shipping/quote` | `warehouse_id`, `destination_zip`, `weight_lb`, `speed` (all required) | Returns `zone_distance` (int), `service_days` (int), `total_cost` (float) |
| `GET /incidents` | `start`, `end`, `supplier_id`, `sku`, `incident_type`, `status` (all optional) | `incident_type`: `RMA` or `WORK_ORDER`; `severity`: `low`/`medium`/`high`/`critical`; `status`: `open`/`closed` |
| `GET /suppliers` | — | `quality_status`: `approved`/`watch`/`quality_hold` |
| `GET /boms` | — | All BOMs with `components[]` (`sku`, `quantity_per_kit`) |
| `GET /boms/<id>` | — | Single BOM |
| `GET /purchase_orders` | `supplier_id`, `sku`, `status` (all optional) | Statuses: `open`, `confirmed`, `received`, `cancelled` |

**Shipping speeds:** `ground`, `two_day`, `overnight`.

## Core Data Model Relationships

```
Product.supplier_id → Supplier.supplier_id
Product.sku → Inventory.sku (per warehouse)
Product.sku → Order.lines[].sku
Product.sku → BOM.components[].sku
Product.sku → PurchaseOrder.sku
Order.customer_id → Customer.customer_id
Order.warehouse_id → Warehouse.warehouse_id
Order.wave → groups orders by wave label
Incident.supplier_id → Supplier.supplier_id
Incident.sku → Product.sku
```

## Key Calculations

### Effective Available Inventory

Two variants exist — use the one the task specifies:

**Standard (dispatch/expedite):**
```
effective_available = on_hand − reserved − quarantined
```

**Allocation desk (with operating buffer):**
```
effective_available = max(0, on_hand − reserved − quarantined − safety_stock)
```

Always clamp to `max(0, …)` — negative effective stock is zero.

### Incident Duration

```
closed incidents:  (close_date − open_date) in calendar days
open incidents:    (analysis_date − open_date) in calendar days
```

Use `date.fromisoformat()` for reliable day-count arithmetic. Round to 2 decimal places.

### Incident Percentages

```
incident_percentage = (supplier_incident_count / total_filtered_population) × 100
```
Round to 1 decimal place.

### Currency

Always `round(value, 2)` for USD amounts. Applies to: `total_cost_usd`, `unit_cost`, `extended_cost`, `total_resolution_cost`, `total_purchase_cost`.

Unit costs come from `Product.unit_cost`, not from order line prices.

### Shipping Quote

Obtain total shipment weight: `sum(product.weight_lb × line.quantity)` for all order lines (even lines that are short or inactive — quote the full order). Pass the order's `shipping_speed` and `destination_zip` to the quote endpoint. The `total_cost` field in the response already includes fuel surcharge.

## Decision Frameworks (SOPs)

### 1. Expedite Queue (Dispatch Control)

**Inventory status** — check each line against the order's warehouse:

| Condition | Status |
|---|---|
| Any SKU `active=false` AND any SKU `effective_available ≤ 0` | `inactive_and_shortage` |
| Any SKU `active=false` (no shortage) | `inactive_sku` |
| Any SKU `effective_available ≤ 0` (all active) | `shortage` |
| Any SKU `0 < effective_available < quantity` (no shortages) | `low_stock` |
| All SKUs `effective_available ≥ quantity` | `ready` |

Only report a SKU in ONE of `shortage_skus` / `low_stock_skus` — a SKU that is short (eff ≤ 0) does not also belong in low_stock. Inactive SKUs always appear in `inactive_skus`; they may also be short/low_stock (check inventory).

**Customer exception** — precedence order (pick the first match):

1. `account_status == "blocked"` → `account_blocked`
2. `risk_flag == "fraud_watch"` → `fraud_watch`
3. `risk_flag == "credit_watch"` → `credit_watch`
4. `account_status == "review_required"` → `review_required`
5. Otherwise → `none`

**Final decision & next action** — precedence from top (first match wins):

| # | Condition | final_decision | next_action |
|---|---|---|---|
| 1 | `customer_exception == "account_blocked"` | `reject_hold` | `hold_credit_or_fraud` |
| 2 | `customer_exception == "fraud_watch"` | `manual_review` | `send_account_review` |
| 3 | `inactive_skus` non-empty | `manual_review` | `escalate_product_master` |
| 4 | `shortage_skus` non-empty | `backorder` | `create_backorder` |
| 5 | `customer_exception == "credit_watch"` | `delayed_release` | `delay_and_monitor` |
| 6 | `customer_exception == "review_required"` | `manual_review` | `send_account_review` |
| 7 | `low_stock_skus` non-empty | `delayed_release` | `delay_and_monitor` |
| 8 | All clear | `ship_now` | `release_to_pick` |

**Summary totals:** sum `total_cost_usd` across all records regardless of decision. Blocked = `customer_exception == "account_blocked"`. Manual review = `final_decision == "manual_review"`. Backorder = `final_decision == "backorder"`. Inactive = records with non-empty `inactive_skus`.

### 2. Replenishment Desk (Kit Build)

**Total required:** `Σ(quantity_per_kit × target_build_quantity)` across all target builds that share the component SKU.

**Effective available:** standard formula at the planning warehouse (WH_WEST in the train tasks).

**Timely PO:** open or confirmed POs for the same SKU + same warehouse with `eta ≤ build_date`. If a component is needed across multiple build dates, use the earliest `needed_by`.

**Coverage gap:** `total_required − (effective_available + timely_po_qty)`.

**Final action** — precedence:

| Condition | final_action | exclusion_reason |
|---|---|---|
| `effective_available > overstock_threshold` | `overstock_excluded` | `target_overstock` |
| `effective_available ≥ total_required` | `no_action_stocked` | `stocked_no_gap` |
| `effective_available + timely_po_qty ≥ total_required` | `timely_po_covered` | `timely_po_covers_gap` |
| Gap fully covered by transfers from other WH | `transfer_only` | `none` |
| After transfers, still need purchase | `purchase_required` | `none` |

**Excluded components:** only add an entry when `exclusion_reason ≠ "none"` (i.e., `target_overstock`, `timely_po_covers_gap`, or `stocked_no_gap`). Include the `supporting_po_ids` sorted ascending.

**Transfers:** from other warehouses, respecting their own `effective_available − safety_stock` buffer at the source. For each source warehouse: `transferrable = max(0, source_eff_avail − safety_stock)`. One transfer row per source warehouse per SKU.

**Purchase requisitions:** use the product's `supplier_id` and `unit_cost`. `extended_cost = round(quantity × unit_cost, 2)`. The `needed_by` is the earliest build date for that component.

### 3. Supplier Incident Scorecard

**Filter:** incidents where `open_date` is within the analysis window (inclusive on both ends).

**Group by supplier**, then compute per supplier:

- `incident_count`: total filtered incidents
- `incident_percentage`: `round(count / total_population × 100, 1)`
- `total_resolution_cost`: `round(sum(resolution_cost), 2)`
- `avg_duration_days`: `round(mean(durations), 2)` — open incidents use `analysis_date − open_date`
- `rma_count` / `work_order_count`: by `incident_type`
- `open_incident_count`: `status == "open"`
- `severe_incident_count`: `severity ∈ {high, critical}`

**Recommendation code** — test conditions in precedence order (first match wins):

| # | Code | Conditions (ANY) |
|---|---|---|
| 1 | `ESCALATE_SUPPLIER` | `quality_status == "quality_hold" AND incident_count ≥ 3`; OR any incident is RMA + critical; OR `rma_count ≥ 3 AND total_resolution_cost ≥ 15000.00` |
| 2 | `PROCESS_REVIEW` | `work_order_count ≥ 3 AND work_order_count > rma_count` |
| 3 | `WATCHLIST` | `quality_status ∈ {watch, quality_hold}`; OR `incident_count ≥ 4`; OR `total_resolution_cost ≥ 12000.00`; OR `severe_incident_count ≥ 2` |
| 4 | `MONITOR` | None of the above |

**Top escalation suppliers:** only those with `ESCALATE_SUPPLIER`, ordered by `incident_count` desc → `total_resolution_cost` desc → `supplier_id` asc.

**highest_cost_supplier_id / highest_share_supplier_id:** single string (not list). Tiebreak by `supplier_id` ascending.

### 4. Allocation Desk (Transfer Review)

**Effective available:** use the **allocation variant** (includes `safety_stock`).

**Line-level decision** — check in this order:

| # | Condition | action | primary_reason |
|---|---|---|---|
| 1 | `account_status == "blocked"` | `manual_review` | `account_blocked` |
| 2 | `risk_flag == "fraud_watch"` | `manual_review` | `fraud_watch` |
| 3 | `risk_flag == "credit_watch"` | `manual_review` | `account_review_required` |
| 4 | `account_status == "review_required"` | `manual_review` | `account_review_required` |
| 5 | `product.active == false` | `manual_review` | `inactive_product` |
| 6 | `effective_available ≥ quantity` | `ship` | `none` |
| 7 | Transfer can fully cover shortfall | `transfer` | `insufficient_effective_stock` |
| 8 | Transfer partial, remainder insufficient | `transfer` | `insufficient_effective_stock` |
| 9 | No transfer source has stock | `backorder` | `insufficient_effective_stock` |

**Ship quantity for transfer lines:** use the requested warehouse's effective available as `ship_quantity` (can be 0 if no effective stock). The `transfer_quantity` covers the remainder. For ship lines, `ship_quantity = line.quantity`. For manual_review lines, all quantities are 0.

**Transfer source selection:** choose the one other warehouse with the highest effective available. `transfer_from` is `null` for non-transfer lines.

**Blocked orders:** only `account_status == "blocked"` at the account level (not risk flags or review_required — those are line-level manual_review).

**Order rollup outcome:**

| Lines contain | outcome |
|---|---|
| Only `ship` | `ready_to_ship` |
| Only `transfer` | `needs_transfer` |
| Only `backorder` | `has_backorder` |
| Only `manual_review` | `manual_review` |
| Mixed actions | `mixed_actions` |

### 5. Procurement Quality Control

**Window:** review incidents in the given date range (inclusive) for the listed suppliers.

**Decision** — precedence:

| # | Decision | Trigger |
|---|---|---|
| 1 | `freeze_new_replenishment` | `quality_status == "quality_hold" AND incident_count > 0`; OR `severe_or_critical_count ≥ 2` |
| 2 | `buyer_review_required` | `quality_status == "watch"`; OR `incident_count ≥ 4` |
| 3 | `monitor_only` | None of the above (`quality_status == "approved"`, few incidents) |

**Held PO IDs:** all open or confirmed POs for suppliers whose decision is NOT `monitor_only`. Deduplicate and sort across all suppliers.

**Release supplier IDs:** suppliers with `monitor_only` decision, sorted ascending.

**Affected SKUs:** unique SKUs from the supplier's filtered incidents, sorted ascending. **Sample incident IDs:** sorted, max 5.

## Enum Quick Reference

### Account / Risk
`account_status`: `active`, `blocked`, `review_required`
`risk_flag`: `none`, `fraud_watch`, `credit_watch`

### Quality
`quality_status`: `approved`, `watch`, `quality_hold`
`severity`: `low`, `medium`, `high`, `critical`

### Incident
`incident_type`: `RMA`, `WORK_ORDER`
`status`: `open`, `closed`

### Order decisions
`inventory_status`: `ready`, `low_stock`, `shortage`, `inactive_sku`, `inactive_and_shortage`
`customer_exception`: `none`, `review_required`, `account_blocked`, `fraud_watch`, `credit_watch`
`final_decision`: `ship_now`, `delayed_release`, `manual_review`, `backorder`, `reject_hold`
`next_action`: `release_to_pick`, `delay_and_monitor`, `send_account_review`, `create_backorder`, `hold_credit_or_fraud`, `escalate_product_master`

### Allocation
`action`: `ship`, `transfer`, `backorder`, `manual_review`
`primary_reason`: `none`, `account_blocked`, `account_review_required`, `fraud_watch`, `inactive_product`, `insufficient_effective_stock`

### Replenishment
`final_action`: `no_action_stocked`, `transfer_only`, `purchase_required`, `timely_po_covered`, `overstock_excluded`
`exclusion_reason`: `none`, `target_overstock`, `timely_po_covers_gap`, `stocked_no_gap`

### Procurement
`decision`: `freeze_new_replenishment`, `buyer_review_required`, `monitor_only`

### Recommendation
`recommendation_code`: `ESCALATE_SUPPLIER`, `PROCESS_REVIEW`, `WATCHLIST`, `MONITOR`

## Ordering Rules (Sort Conventions)

**Default:** string fields sort ascending lexicographically unless otherwise stated.

| Context | Sort key(s) |
|---|---|
| Order records / line actions | `order_id` asc, then `line_id` asc |
| Supplier scorecard rows | `supplier_id` asc |
| Transfer requests | `sku` asc → `quantity` desc → `from_warehouse_id` asc |
| Purchase requisitions | `sku` asc |
| Component plan / excluded components | `sku` asc |
| SKU exception lists (shortage, inactive, low_stock) | `sku` asc |
| Coverage PO IDs / supporting PO IDs / sample incident IDs | string asc |
| Blocked/manual_review/backorder/inactive order ID lists | string asc |
| Held PO IDs / release supplier IDs | string asc |
| Top escalation suppliers | `incident_count` desc → `total_resolution_cost` desc → `supplier_id` asc |
| Kit targets | `bom_id` asc |

## Common Pitfalls

1. **Overlapping SKU lists:** A SKU with `effective_available ≤ 0` is `shortage`, not `low_stock`. A SKU already in `inactive_skus` should still be checked for shortage/low_stock classification in the inventory status roll-up.

2. **Customer exception vs. primary_reason:** Different tasks use different enum sets. `customer_exception` uses `review_required`; `primary_reason` uses `account_review_required`. Match the answer template exactly.

3. **Effective available → 0 floor:** Always `max(0, on_hand − reserved − quarantined − safety_stock)`. Negative effective stock means zero availability, not negative.

4. **Cancelled POs:** Do not count `cancelled` purchase orders as coverage. Only `open` and `confirmed` statuses are eligible.

5. **Date inclusivity:** When a filter says "Q1" or specifies `"inclusive": true`, include incidents where `open_date` falls exactly on the boundary dates. Use `start <= open_date <= end`.

6. **Shipping quotes for ALL orders:** Request quotes even for orders that are blocked, backordered, or under manual review. The quote informs the cost summary regardless of fulfillment decision.

7. **Weight calculation for shipping:** Multiply `product.weight_lb × line.quantity` for ALL lines in the order, including lines with inactive SKUs (the courier charges by total package weight). Use the product catalog weight, not a zero default for lookups that fail.

8. **Supplier-level analysis windows:** For scorecards (train_003), filter by `open_date`. For procurement control (train_005), the window is the review period — filter incidents whose `open_date` falls in that range.

9. **Exclusion reason "none" vs. excluded_components:** Only add entries to `excluded_components` when the `exclusion_reason` is not `"none"`. Components with `exclusion_reason: "none"` that still appear in `component_plan` do not go in `excluded_components`.

10. **Transfer source buffer:** When pulling inventory from a source warehouse, respect its own safety stock — `transferrable = max(0, source_eff_avail − safety_stock)`. Don't drain a warehouse below its operating buffer.

11. **RMA critical check:** For ESCALATE_SUPPLIER, check if ANY incident has `incident_type == "RMA" AND severity == "critical"` — not just RMAs overall.

12. **top_escalation_suppliers:** This is a list of supplier_id strings, not objects. Only suppliers with `recommendation_code == "ESCALATE_SUPPLIER"`.

13. **PO status for held POs:** Include both `open` and `confirmed` POs. Exclude `received` and `cancelled`.

14. **Order rollup edge case:** If an order has multiple lines with different actions, outcome is `mixed_actions` regardless of whether one action dominates.
