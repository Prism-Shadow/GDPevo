---
name: demonstration-skill-attempt-03
description: Use for Northwind Components ERP decision tasks that require JSON answers built from task memos/templates plus the shared ERP API, including expedite dispatch, transfer allocation, kit replenishment, supplier incident scorecards, and procurement quality holds.
---

# Northwind ERP Decision Skill

## Core Workflow

1. Read the prompt, payload memo, and answer template first. The template is the contract: preserve its top-level keys, field names, enums, sorting rules, and rounding precision.
2. Use the public ERP API for live records. Do not inspect environment source files or cached internal data.
3. Resolve only the population requested by the memo:
   - If the memo lists explicit order IDs or supplier IDs, use only those IDs, even when an API wave/query returns additional records.
   - If the memo asks for an entire wave, include every order/line in that wave.
   - If the memo defines an incident window, filter incidents by `open_date` inclusively.
4. Join records from the relevant endpoints, compute the requested classifications and summaries, then return one JSON object only.
5. Sort every list exactly as the template states. Sort IDs lexicographically unless a different ordering is specified.

## API Usage

Use the task-provided base URL when present. In this benchmark setup, the local shared API is normally:

```text
http://127.0.0.1:8100
```

Bypass proxies for localhost calls:

```bash
curl --noproxy '*' -sS "$BASE/orders?wave=WAVE_ID"
curl --noproxy '*' -sS "$BASE/products/SKU"
curl --noproxy '*' -sS "$BASE/inventory?warehouse_id=WH_WEST&sku=SKU"
```

Public endpoints exposed by the service:

- `/products`, `/products/<sku>`
- `/customers`, `/customers/<customer_id>`
- `/warehouses`
- `/inventory?warehouse_id=&sku=`
- `/purchase_orders?supplier_id=&sku=&status=`
- `/orders?wave=&required_date=&customer_id=`, `/orders/<order_id>`
- `/shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=`
- `/incidents?start=&end=&supplier_id=&sku=&incident_type=&status=`
- `/suppliers`
- `/boms`, `/boms/<bom_id>`

Join patterns:

- Orders need customers, products, inventory, and usually shipping quotes.
- Allocation tasks need orders by wave, customers, products, and all warehouses' inventory for each SKU.
- Kit tasks need BOMs, products, target-warehouse inventory, other-warehouse inventory, and purchase orders.
- Supplier-quality tasks need incidents plus supplier master data; procurement holds also need purchase orders.

## Shared Business Rules

### Inventory math

Use protected-stock availability, not raw on-hand:

```text
effective_available = on_hand - reserved - quarantined - product.safety_stock
```

Never treat reserved, quarantined, or safety-stock/buffer units as freely available.

For transferable surplus, use only positive effective availability from a non-target warehouse. Do not move protected stock.

### Customer exceptions

Map customer status/risk with this precedence:

1. `account_status == "blocked"`: hard account block.
2. `account_status == "review_required"`: account review.
3. Active account with `risk_flag == "fraud_watch"`: fraud watch.
4. Active account with `risk_flag == "credit_watch"`: credit watch when the target enum supports it; otherwise use the closest account-review/customer-risk enum allowed by the template.
5. Otherwise no customer exception.

Blocked accounts outrank credit-watch risk. Account-level exceptions usually apply to every line in the order.

### Product exceptions

Inactive products prevent automatic release for the affected SKU/line. Product inactivity is separate from stock shortage; if both occur, preserve both facts when the output has separate inactive and shortage fields.

### Dates and rounding

- Incident date filters use `open_date` and are inclusive of both start and end.
- Calendar duration is `(close_date or analysis_date) - open_date` in days, not inclusive-count days.
- Round currency to 2 decimals, durations to 2 decimals, and percentages to the precision specified in the request/template.
- For money totals, compute from unrounded components when possible, then round the final displayed value.

## Task Patterns

### Expedite dispatch queue

Inputs identify an expedite wave and often a specific list of order IDs. Include only memo-listed orders when that list exists.

Per order:

- Fetch the order, customer, all line products, requested-warehouse inventory for each line SKU, and a shipping quote.
- Compute each line's effective availability at the order warehouse.
- `shortage_skus`: active line SKUs where effective availability is less than line quantity.
- `inactive_skus`: inactive line SKUs.
- `low_stock_skus`: active SKUs with small positive effective availability even if the line can still be covered. In observed tasks, low stock is positive effective availability below 10 units.
- `inventory_status`:
  - `inactive_and_shortage` if there is at least one inactive SKU and at least one shortage.
  - `inactive_sku` if inactive exists without shortage.
  - `shortage` if shortage exists without inactive.
  - `low_stock` if no shortage/inactive but low stock exists.
  - `ready` otherwise.
- `customer_exception` follows the customer mapping and the template enum.
- Decision precedence:
  - Hard account/risk hold: `reject_hold`, next action `hold_credit_or_fraud`.
  - Account review: `manual_review`, next action `send_account_review`.
  - Product-only inactive exception: `manual_review`, next action `escalate_product_master`.
  - Stock shortage: `backorder`, next action `create_backorder`.
  - Low stock only: `delayed_release`, next action `delay_and_monitor`.
  - Otherwise: `ship_now`, next action `release_to_pick`.

Shipping quote:

- Total shipment weight is `sum(line.quantity * product.weight_lb)`.
- Call `/shipping/quote` with order `warehouse_id`, `destination_zip`, total weight, and order `shipping_speed`.
- Return `zone_distance`, `service_days`, and `total_cost_usd` from the quote, rounded to 2 decimals.

Summary fields usually count decisions, sum shipping costs, and list blocked/manual/backorder/inactive orders sorted ascending.

### Mixed-warehouse allocation

Use every order in the requested wave. Return one line action per order line, sorted by `order_id`, then `line_id`.

For each line:

- `requested_effective_available` is the effective availability at the order's requested warehouse.
- If the customer has an account/risk exception, set `action: "manual_review"` for all lines in that order, zero all quantities, and use the account/risk reason.
- Else if the product is inactive, set `manual_review` for that line only with `primary_reason: "inactive_product"`.
- Else if requested effective availability covers the full line, set `ship`, `ship_quantity = line.quantity`.
- Else if one alternate warehouse can cover the uncovered quantity from positive effective availability, set `transfer`.
  - `ship_quantity = max(requested_effective_available, 0)`.
  - `transfer_quantity = line.quantity - ship_quantity`.
  - Choose one source warehouse deterministically from eligible sources, preferring larger effective surplus, then stable warehouse ordering.
- Else set `backorder`, `ship_quantity = 0`, and `backorder_quantity = line.quantity`.

`transfer_requests` mirrors transfer lines. `blocked_orders` includes only account/customer-risk stopped orders, not product-only manual-review lines.

Order rollup:

- `ready_to_ship`: all lines ship.
- `needs_transfer`: transfer lines exist, with no manual review or backorder.
- `has_backorder`: backorder exists, with no manual review.
- `manual_review`: all lines are held by account/customer review.
- `mixed_actions`: product-only manual review or a mixture that does not fit the prior categories.

### Kit replenishment

Use memo target builds, not stale BOM target dates, for build quantity/date. Fetch each BOM to get kit name, warehouse, and components.

Component planning:

- For each SKU, `total_required = sum(quantity_per_kit * target_build_quantity)` across all requested BOMs.
- `target_effective_available` uses the shared effective-availability formula at the planning warehouse.
- If target effective availability is at or above `product.overstock_threshold`, exclude as `target_overstock`.
- Else if no gap remains, exclude as `stocked_no_gap`.
- Eligible timely POs are same-SKU, same-target-warehouse POs with status `open` or `confirmed` and ETA on or before the relevant build need date. Cancelled and received POs do not cover future needs.
- If timely PO quantity covers the gap, use final action `timely_po_covered`, list supporting PO IDs, and put the covered gap units into the summary's timely-PO coverage total.
- Otherwise, consume positive effective surplus from other warehouses as transfers without dipping into protected stock.
- Any remaining gap becomes a purchase requisition from `product.supplier_id` at `product.unit_cost`.

Transfer requests are sorted by SKU, then quantity descending, then source warehouse. Purchase requisitions are sorted by SKU. `extended_cost = quantity * unit_cost`, rounded to 2 decimals.

Final action guide:

- `no_action_stocked`: stocked with no gap.
- `overstock_excluded`: target already meets/exceeds overstock threshold.
- `timely_po_covered`: eligible same-warehouse PO coverage closes the gap.
- `transfer_only`: transfers close the remaining gap.
- `purchase_required`: any purchase requisition quantity remains.

### Supplier incident scorecard

Use incidents whose `open_date` falls in the requested inclusive window. Group only suppliers with at least one filtered incident.

Per supplier:

- Join supplier name and `quality_status`.
- Count incidents, RMA incidents, WORK_ORDER incidents, open incidents, and severe incidents where severity is `high` or `critical`.
- `incident_percentage = supplier_incident_count / total_filtered_incidents * 100`.
- `total_resolution_cost` is the sum of filtered incident costs.
- `avg_duration_days` averages calendar durations, using analysis date for open incidents.
- Apply the request's recommendation policy in its stated precedence order. Do not reorder policy clauses by intuition.

Typical recommendation policy:

- `ESCALATE_SUPPLIER`: quality hold with enough incidents, any critical RMA, or high RMA/cost combination.
- `PROCESS_REVIEW`: WORK_ORDER incidents meet the threshold and exceed RMA count.
- `WATCHLIST`: supplier is watch/hold, incident count/cost/severity threshold is met.
- `MONITOR`: no higher-precedence rule applies.

`top_escalation_suppliers` includes only escalation-code suppliers and uses the template's tie-breakers. Highest-cost/share supplier fields are single supplier IDs selected after grouping.

### Procurement quality hold review

Use only memo-listed supplier IDs and the memo's inclusive incident window.

Per supplier:

- Join supplier master data.
- Count recent incidents, recent RMAs, high/critical incidents, and open incidents.
- `affected_skus`: sorted unique SKUs from recent incidents.
- `sample_incident_ids`: sorted incident IDs, capped at 5 when the template requests a sample.
- Decision pattern:
  - `quality_hold` suppliers freeze new replenishment.
  - `watch` suppliers with multiple high/critical recent incidents require buyer review.
  - Otherwise monitor only.
- For freeze or buyer-review decisions, list sorted open/confirmed PO IDs for the supplier. Ignore cancelled and received POs. When many POs qualify, keep the first five sorted IDs to match observed sample-style hold outputs.
- For monitor-only suppliers, `held_po_ids` is empty and the supplier ID belongs in `release_supplier_ids`.

Top-level `held_po_ids` is the sorted unique union of held supplier PO IDs. Summary counts must reconcile with the supplier rows.

## Output Field Checklist

Expedite queue outputs commonly contain:

- `wave_id`
- `records[]`: `order_id`, `inventory_status`, `customer_exception`, `final_decision`, `next_action`, `shortage_skus`, `inactive_skus`, `low_stock_skus`, `shipping_quote`
- `summary`: order count, decision counts, shipping total, blocked/manual/backorder/inactive order ID lists

Allocation outputs commonly contain:

- `wave_id`
- `line_actions[]`: line identity, requested warehouse, requested effective availability, action, quantities, transfer source, primary reason
- `transfer_requests[]`
- `blocked_orders[]`
- `order_rollup[]`
- `summary`

Kit replenishment outputs commonly contain:

- `task_id`, `plan_date`
- `kit_targets[]`
- `component_plan[]`
- `transfer_requests[]`
- `purchase_requisitions[]`
- `excluded_components[]`
- `summary`

Supplier scorecard outputs commonly contain:

- `analysis_window`
- `summary`
- `supplier_scorecard[]`
- `top_escalation_suppliers[]`
- `highest_cost_supplier_id`
- `highest_share_supplier_id`

Procurement hold outputs commonly contain:

- `analysis_window`
- `supplier_decisions[]`
- `held_po_ids[]`
- `release_supplier_ids[]`
- `summary`

## Common Pitfalls

- Do not use raw `on_hand` as availability. Always subtract reserved, quarantined, and product safety stock.
- Do not include extra API records just because a wave query returns them. Respect memo-listed IDs.
- Do not let account-review orders proceed to transfer/backorder actions; account/customer exceptions usually dominate stock decisions.
- Do not put product-only inactive lines in `blocked_orders`; those are line-level product reviews.
- Do not count cancelled or received POs as timely coverage or held replenishment.
- Do not use BOM `target_date` when the memo supplies build dates.
- Do not calculate shipping with a unit weight; quote the full order weight.
- Do not use inclusive day counts for incident duration; use date subtraction.
- Do not emit explanatory text outside the JSON answer.
