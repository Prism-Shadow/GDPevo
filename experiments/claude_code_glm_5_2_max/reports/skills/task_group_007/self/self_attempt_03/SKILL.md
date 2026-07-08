# Northwind ERP Dispatch / Replenishment / Supplier-Quality Skill

Executable experience for solving Northwind Components ERP decision tasks against the
shared live ERP API. These tasks give you a memo + an answer_template.json and ask for a
structured JSON decision file. There are NO gold answers and NO judge endpoint — derive
correctness from internal consistency and the business semantics below.

## 0. Golden rules that apply to EVERY task

### 0.1 Effective available stock (the central formula)
```
effective_available(sku, warehouse) = on_hand - reserved - quarantined - safety_stock
```
- `on_hand`, `reserved`, `quarantined` come from `/inventory?warehouse_id=<wh>&sku=<sku>`.
- `safety_stock` comes from the PRODUCT MASTER (`/products/<sku>`), NOT from inventory.
- `quarantined` is held-quality stock; `reserved` is already spoken for; `safety_stock` is
  the protected operating buffer. NONE of these are freely shippable.
- The raw value CAN BE NEGATIVE (on-hand already below safety). Keep it raw for the
  target/planning warehouse — a negative `target_effective_available` correctly inflates
  the procurement gap to *restore the safety buffer*. Only floor-at-0 when computing the
  *transferable spare* at another warehouse (you cannot transfer negative stock).
- When computing a SHIPPABLE quantity from effective available, clamp at 0:
  `ship_quantity = min(quantity, max(effective_available, 0))`. A negative effective
  available means nothing can ship from that warehouse — never emit a negative ship_quantity.

### 0.2 Rounding
- Currency → 2 decimals (`round(x, 2)`).
- Percentages (incident share) → 1 decimal.
- Durations → 2 decimals.
- Counts, quantities, service_days, zone_distance → integers.

### 0.3 Ordering
- SKU lists and coverage_po_ids → sort ascending lexicographically.
- Records/lines → sort by order_id ascending, then line_id ascending.
- Suppliers → supplier_id ascending.
- BOMs/kits → bom_id ascending.
- Transfers (train_002) → sku ascending, then quantity descending, then from_warehouse_id ascending.
- Transfers (train_004) → order_id ascending, then line_id ascending.

### 0.4 The remote API
```
Base URL: <remote-env-url>     (do NOT use 127.0.0.1 — that is a decoy in the prompts)
```
- HTTP/1.0, closes the connection EVERY call. Each call is a fresh connection.
- Call with: `curl -sS --max-time 30 '<url>'`. Parse with python3 `json` (or `jq`).
- All endpoints are GET. Query params are filters (all optional unless noted).
- `/health` returns a manifest with record_counts (boms:9, customers:40, incidents:212,
  inventory:162, orders:88, products:54, purchase_orders:92, suppliers:12, warehouses:3,
  seed:7007, generated 2026-06-01).

### 0.5 Endpoint field reference (verified)
- `/products` and `/products/<sku>` → `{sku, name, category, supplier_id, unit_cost,
  weight_lb, safety_stock, overstock_threshold, active}`. `active` is a bool.
- `/customers` and `/customers/<id>` → `{customer_id, name, tier, account_status,
  risk_flag, margin_band}`. `account_status` ∈ {active, blocked, review_required}.
  `risk_flag` ∈ {none, fraud_watch, credit_watch}.
- `/warehouses` → `{warehouse_id, name, zip, region}`. The 3 warehouses are WH_NORTH,
  WH_CENTRAL, WH_WEST.
- `/inventory?warehouse_id=&sku=` → `{sku, warehouse_id, on_hand, reserved, quarantined,
  last_count_date}`. Returns a list (filter by both params to get one record).
- `/orders?wave=&required_date=&customer_id=` and `/orders/<order_id>` → `{order_id,
  customer_id, warehouse_id, required_date, shipping_speed, destination_zip, priority,
  wave, lines:[{line_id, sku, quantity, unit_price}]}`.
- `/purchase_orders?supplier_id=&sku=&status=` → `{po_id, sku, quantity, eta, status,
  supplier_id, warehouse_id}`. `status` ∈ {open, confirmed, received, cancelled}.
- `/shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=` → returns a cost plus
  `service_days` and a `zone_distance`. (Inspect the actual response object for exact keys.)
  `speed` ∈ {standard, expedited, overnight}.
- `/incidents?start=&end=&supplier_id=&sku=&incident_type=&status=` → `{incident_id,
  incident_type, open_date, close_date, resolution_cost, root_cause, severity, sku, status,
  supplier_id, warehouse_id}`. `incident_type` ∈ {RMA, WORK_ORDER}. `severity` ∈
  {low, medium, high, critical}. `status` ∈ {open, closed}. `close_date` is null when open.
  `start`/`end` filter on `open_date` INCLUSIVELY.
- `/suppliers` → `{supplier_id, name, quality_status, ...}`. `quality_status` ∈
  {approved, watch, quality_hold}.
- `/boms` and `/boms/<bom_id>` → `{bom_id, name, components:[{sku, quantity_per_kit}],
  warehouse_id, target_date}`.

### 0.6 Universal working order
1. Read prompt + answer_template.json + memo. The template is the authoritative shape —
   match every key and enum exactly.
2. Pull the relevant orders/customers/products/inventory from the API.
3. Apply account/risk precedence FIRST, then product-status, then inventory.
4. Compute, round, sort, assemble.
5. Sanity-check: counts sum, currency rounds, enums are from the allowed set, lists sorted.

---

## 1. Task family A — Expedite queue dispatch (wave decision per order)

**Example: train_001, wave TRAIN_EXPEDITE_A.** Output: `{wave_id, records[], summary}`.

### 1.1 Per-order record
For each order in the memo's order list, produce:
`{order_id, inventory_status, customer_exception, final_decision, next_action,
shortage_skus, inactive_skus, low_stock_skus, shipping_quote}`.

### 1.2 Effective available per line
`eff = on_hand - reserved - quarantined - safety_stock` for the line's SKU at the ORDER's
`warehouse_id`. Compare `eff` to the line `quantity`.

**Shortage boundary:** a line is a *shortage* when `eff < quantity`. `eff >= quantity` is
fulfillable (even `eff == quantity` ships, with 0 remaining). A line is *low_stock* when it
is NOT a shortage (`eff >= quantity`) AND the remaining stock after allocation would breach
the safety buffer: `(eff - quantity) < safety_stock`.

### 1.3 Decision PRECEDENCE (apply top-down; first match wins for final_decision/next_action)

1. **Account blocked** — `account_status == "blocked"`:
   `customer_exception = "account_blocked"`, `final_decision = "reject_hold"`,
   `next_action = "hold_credit_or_fraud"`. Goes in `blocked_order_ids`.
   - blocked dominates EVERYTHING and SUPPRESSES coexisting risk flags. A customer who is
     both `blocked` AND `risk_flag=credit_watch` is reported as `account_blocked` only
     (credit_watch is not surfaced). Precedence: blocked > review_required > fraud_watch >
     credit_watch.

2. **Account review** — `account_status == "review_required"`:
   `customer_exception = "review_required"`, `final_decision = "manual_review"`,
   `next_action = "send_account_review"`. Goes in `manual_review_order_ids`.

3. **Fraud watch** — `risk_flag == "fraud_watch"`:
   `customer_exception = "fraud_watch"`, `final_decision = "manual_review"`,
   `next_action = "hold_credit_or_fraud"`. manual_review.

4. **Credit watch** — `risk_flag == "credit_watch"` (account active but credit-flagged):
   `customer_exception = "credit_watch"`, `final_decision = "manual_review"`,
   `next_action = "hold_credit_or_fraud"`. manual_review.

   If account_status is active AND risk_flag is none → `customer_exception = "none"`,
   fall through to inventory/product logic.

5. **Inactive product** (account ok): if ANY line SKU has `active == false`:
   - that SKU → `inactive_skus`.
   - `final_decision = "manual_review"`, `next_action = "escalate_product_master"`.
   - This takes precedence over shortage/low-stock BUT is computed alongside them so the
     inventory_status enum can be `inactive_sku` or `inactive_and_shortage`.
   - IMPORTANT: when an account exception (review/fraud/credit) ALSO coexists with an
     inactive SKU, the ACCOUNT exception's `next_action` wins (e.g. send_account_review),
     but the inactive SKU is still surfaced in `inactive_skus` and the order still appears
     in `inactive_sku_order_ids`. Only when account is ok does inactive alone drive
     `escalate_product_master`.

6. **Shortage** (account ok, no inactive — or with inactive, see enum): any line where
   `eff < quantity` → SKU in `shortage_skus`. `final_decision = "backorder"`,
   `next_action = "create_backorder"` (when no inactive). Goes in `backorder_order_ids`.

7. **Low stock** (account ok, no inactive, no shortage): a line where the order CAN be
   fulfilled (`eff >= quantity`) BUT allocating it would breach the safety buffer, i.e.
   `eff - quantity < safety_stock`. → SKU in `low_stock_skus`.
   `final_decision = "delayed_release"`, `next_action = "delay_and_monitor"`.

8. **Ready**: all lines `eff >= quantity` and `eff - quantity >= safety_stock` (no breach).
   `final_decision = "ship_now"`, `next_action = "release_to_pick"`.

### 1.4 inventory_status enum (combine the per-line findings)
- `ready` — no shortage, no low, no inactive.
- `low_stock` — ≥1 low_stock_sku, no shortage, no inactive.
- `shortage` — ≥1 shortage_sku, no inactive.
- `inactive_sku` — ≥1 inactive_sku, no shortage.
- `inactive_and_shortage` — ≥1 inactive_sku AND ≥1 shortage_sku.
(Presence of inactive forces manual_review regardless, but inventory_status still
reflects the shortage reality.)

### 1.5 Shipping quote (compute for EVERY order, even rejected ones)
- Total parcel `weight_lb = Σ(product.weight_lb × line.quantity)` over ALL lines of the order.
- Call `/shipping/quote?warehouse_id=<order.warehouse_id>&destination_zip=<order.destination_zip>&weight_lb=<total>&speed=<order.shipping_speed>`.
- The response object contains `total_cost`, `service_days` (already an int), and
  `zone_distance` (an int; may be 0 for a local/ground zone — report the API value verbatim),
  plus `base_rate`, `carrier`, `fuel_surcharge_rate`. Map:
  `shipping_quote = {zone_distance: <response.zone_distance>, service_days:
  <response.service_days>, total_cost_usd: round(response.total_cost, 2)}`.
- The memo explicitly requires a quote even when the decision is not release (e.g. overnight
  quote needed regardless).
- `summary.total_shipping_cost_usd = round(Σ all order quotes, 2)`.

### 1.4b Compute inventory fields for ALL orders
`inventory_status`, `shortage_skus`, `inactive_skus`, `low_stock_skus` are computed for
EVERY order — including those with an account exception — because the inventory_status enum
has no "skipped" value and `inactive_sku_order_ids` must reflect real inactive-SKU presence.
The account exception overrides only `customer_exception`, `final_decision`, and
`next_action`; the inventory facts are still surfaced and the order still lands in
`inactive_sku_order_ids` if it has an inactive SKU.

### 1.6 Summary
- `order_count` = number of records.
- `decision_counts` = counts of each final_decision value over the 5 enums
  {ship_now, delayed_release, manual_review, backorder, reject_hold}.
- `blocked_order_ids`, `manual_review_order_ids`, `backorder_order_ids`,
  `inactive_sku_order_ids` — sorted ascending. (inactive_sku_order_ids = orders that have
  ≥1 inactive_sku, regardless of their final decision.)

### 1.7 Common misjudgments (train_001)
- Forgetting the quote is required for ALL orders (not just ship_now).
- Applying inventory logic before account status — account overrides come FIRST.
- Using `on_hand` alone instead of effective available.
- Mis-mapping credit_watch vs fraud_watch next_actions.
- Not sorting SKU lists ascending.

---

## 2. Task family B — BOM kit replenishment (WH_WEST build run)

**Example: train_002.** Output: `{task_id, plan_date, kit_targets, component_plan,
transfer_requests, purchase_requisitions, excluded_components, summary}`.

### 2.1 Demand
- `total_required(sku) = Σ over builds of (quantity_per_kit × build_quantity)`.
- A SKU appearing in multiple BOMs (e.g. NW-1014 in both BOM-300 and BOM-301) SUMS across
  both builds: 6×18 + 6×18 = 216.
- `build_date` for a shared SKU = MAX of its builds' target_build_dates (conservative
  cutoff that admits more timely POs). Single-build SKUs use that build's date.
- Use the MEMO's build dates (e.g. 2026-06-06, 2026-06-10), NOT the stale
  `/boms` `target_date` field (which is a default, often in the past).

### 2.2 Target stock at the planning warehouse
- `target_effective_available(sku) = on_hand - reserved - quarantined - safety_stock`
  at WH_WEST. RAW (may be negative — the gap then exceeds the raw build qty because it must
  also restore the safety buffer).
- `gap = max(0, total_required - target_effective_available)`.

### 2.3 Timely PO coverage
- A PO is timely for a SKU iff: `status ∈ {open, confirmed}` AND `eta <= build_date(sku)`
  AND `warehouse_id == <planning warehouse, WH_WEST>`.
- `received` and `cancelled` POs are NEVER timely (already consumed / void).
- A PO at a DIFFERENT warehouse is NOT timely even if the eta is fine (strict same-warehouse).
- `timely_po_qty = Σ quantity of timely POs`. `coverage_po_ids` = sorted timely PO ids.
- If `timely_po_qty >= gap` → the gap is PO-covered:
  `exclusion_reason = "timely_po_covers_gap"`, `final_action = "timely_po_covered"`,
  `transfer_qty = 0`, `purchase_requisition_qty = 0`. Goes in excluded_components.

### 2.4 Overstock / stocked exclusion (no-gap SKUs)
- If `target_effective_available >= total_required` (no gap):
  - AND `target_effective_available >= product.overstock_threshold` →
    `exclusion_reason = "target_overstock"`, `final_action = "overstock_excluded"`.
  - else (`< overstock_threshold`) →
    `exclusion_reason = "stocked_no_gap"`, `final_action = "no_action_stocked"`.
- Both go in excluded_components (supporting_po_ids = [] for these).
- `overstock_threshold` is on the product master.

### 2.5 Transfer (inter-warehouse)
- After timely PO coverage, `remaining_gap = gap - timely_po_qty`.
- For each OTHER warehouse (not WH_WEST), compute
  `spare = max(0, on_hand - reserved - quarantined - safety_stock)` (FLOORED at 0 — the
  safety_stock is already preserved by subtracting it; you cannot transfer negative).
- Pick ONE source warehouse: largest `spare`, then warehouse_id ascending.
- `transfer_qty = min(remaining_gap, spare)`. Partial transfer is allowed; residual → purchase.
- `needed_by = build_date(sku)`. `from_warehouse_id = <source>`, `to_warehouse_id = WH_WEST`.
- If `transfer_qty > 0` and `purchase_requisition_qty == 0` (transfer fully covers residual)
  → `final_action = "transfer_only"`.

### 2.6 Purchase requisition
- `purchase_requisition_qty = max(0, gap - timely_po_qty - transfer_qty)`.
- If > 0 → `final_action = "purchase_required"`.
- `supplier_id` and `unit_cost` from the product master. `warehouse_id = WH_WEST`.
- `needed_by = build_date(sku)`. `extended_cost = round(unit_cost × qty, 2)`.

### 2.7 excluded_components list
All SKUs with `exclusion_reason != "none"`: `{sku, reason, supporting_po_ids}`.
- timely_po_covers_gap → supporting_po_ids = coverage_po_ids.
- target_overstock / stocked_no_gap → supporting_po_ids = [].

### 2.8 Summary
- `component_count` = number of unique SKUs across all builds.
- `total_purchase_units` = Σ purchase_requisition_qty.
- `total_purchase_cost` = round(Σ extended_cost, 2).
- `total_transfer_units` = Σ transfer_qty.
- `timely_po_covered_units` = Σ timely_po_qty over SKUs whose gap was PO-covered
  (exclusion_reason == timely_po_covers_gap). (Do NOT sum timely_po_qty for other SKUs.)

### 2.9 final_action enum
`no_action_stocked | transfer_only | purchase_required | timely_po_covered | overstock_excluded`
exclusion_reason enum: `none | target_overstock | timely_po_covers_gap | stocked_no_gap`.

### 2.10 Common misjudgments (train_002)
- Using `/boms` target_date instead of memo build_date.
- Including received/cancelled POs as timely, or POs at the wrong warehouse.
- Not flooring the transfer spare at 0 (transferring "negative" stock).
- Forgetting a shared SKU sums demand across both builds.
- Mis-classifying a no-gap overstocked SKU as stocked_no_gap (check overstock_threshold).
- Negative target_effective_available is intentional — do not floor the planning value.
- plan_date = the memo's issued_at date (YYYY-MM-DD), not today.

---

## 3. Task family C — Supplier incident scorecard

**Example: train_003 (Q1 scorecard).** Output: `{analysis_window, summary,
supplier_scorecard[], top_escalation_suppliers[], highest_cost_supplier_id,
highest_share_supplier_id}`.

### 3.1 Filter
- Incidents with `open_date` in `[start, end]` INCLUSIVE. The `/incidents?start=&end=`
  endpoint filters on open_date inclusively (verified).
- `filtered_incident_count` = size of that set.
- Only suppliers with ≥1 filtered incident appear in `supplier_scorecard`.

### 3.2 Per-supplier row
- `incident_count` = that supplier's filtered incidents.
- `incident_percentage = round(incident_count / filtered_incident_count × 100, 1)`.
- `total_resolution_cost = round(Σ resolution_cost, 2)`.
- `avg_duration_days = round(mean(duration), 2)` where:
  - closed: `(close_date - open_date).days`
  - open: `(analysis_date - open_date).days`  (analysis_date from the memo, e.g. 2026-03-31)
  - NOTE: closed incidents whose close_date falls AFTER the window end are STILL included
    (filter is on open_date) and use the real close_date for duration (not capped).
- `rma_count` = incident_type == RMA. `work_order_count` = WORK_ORDER.
- `open_incident_count` = status == open.
- `severe_incident_count` = severity ∈ {high, critical} (regardless of type).
- `supplier_name`, `quality_status` from `/suppliers`.

### 3.3 Recommendation precedence (apply top-down; first match wins)
Order: ESCALATE_SUPPLIER > PROCESS_REVIEW > WATCHLIST > MONITOR.

- **ESCALATE_SUPPLIER** — supplier `quality_status == "quality_hold"` AND
  `incident_count >= 3`; OR any **critical RMA** (incident_type==RMA AND severity==critical);
  OR (`rma_count >= 3` AND `total_resolution_cost >= 15000.00`). All scoped to FILTERED incidents.
- **PROCESS_REVIEW** — `work_order_count >= 3` AND `work_order_count > rma_count`.
- **WATCHLIST** — `quality_status ∈ {watch, quality_hold}`; OR `incident_count >= 4`; OR
  `total_resolution_cost >= 12000.00`; OR `severe_incident_count >= 2`.
- **MONITOR** — none of the above.

Key subtleties:
- "critical RMA" = type RMA AND severity critical (a critical WORK_ORDER does NOT trigger
  this branch).
- A supplier can satisfy a WATCHLIST condition yet receive a higher code (PROCESS_REVIEW
  or ESCALATE). Always apply precedence top-down.
- ESCALATE "≥3 RMAs AND ≥15000" requires BOTH conditions.

### 3.4 Top escalation & extremes
- `top_escalation_suppliers` = suppliers with recommendation_code == ESCALATE_SUPPLIER,
  ordered by incident_count DESC, then total_resolution_cost DESC, then supplier_id ASC.
  The train_003 template calls this a **list of supplier_id strings** (not objects) — emit
  just the supplier_id strings in that order. (If a test task's template shows object items,
  follow THAT template's row shape instead; always match the provided template.)
- `highest_cost_supplier_id` = max total_resolution_cost (ties → supplier_id ASC).
- `highest_share_supplier_id` = max incident_count (ties → supplier_id ASC).

### 3.5 Summary
- `supplier_count` = suppliers with ≥1 filtered incident.
- `total_resolution_cost` = round(Σ over all filtered incidents, 2).
- `overall_rma_count` / `overall_work_order_count` = type totals across ALL filtered incidents.

### 3.6 Common misjudgments (train_003)
- Filtering on close_date instead of open_date.
- Capping closed-incident duration at the window end (use real close_date).
- Treating any critical incident as "critical RMA" (must be type RMA).
- Applying WATCHLIST before PROCESS_REVIEW, or PROCESS_REVIEW before ESCALATE.
- Forgetting quality_status-driven WATCHLIST (watch/quality_hold suppliers with few incidents).
- Rounding incident_percentage to 2 decimals (use 1).

---

## 4. Task family D — Mixed-warehouse allocation / transfer (line-level)

**Example: train_004, wave TRAIN_TRANSFER_B.** Output: `{wave_id, line_actions[],
transfer_requests[], blocked_orders[], order_rollup[], summary}`.

### 4.1 Per-line action
Pull all orders in the wave (`/orders?wave=<wave>`). Each order has `lines[]`. For each line
produce `{order_id, line_id, sku, requested_warehouse, requested_effective_available,
action, ship_quantity, transfer_from, transfer_quantity, backorder_quantity, primary_reason}`.

`requested_warehouse` = order's `warehouse_id`.
`requested_effective_available = on_hand - reserved - quarantined - safety_stock` for the
line SKU at the requested warehouse.

### 4.2 Account/risk precedence (ORDER-level, affects ALL lines)
Determine from `/customers/<order.customer_id>`. Apply FIRST; account/risk cases force ALL
of an order's lines to `action = "manual_review"` with ship/transfer/backorder qty = 0:
- `account_status == "blocked"` → `primary_reason = "account_blocked"`. Order → blocked_orders.
- `account_status == "review_required"` → `primary_reason = "account_review_required"`. Order → blocked_orders.
- `risk_flag == "fraud_watch"` (account active) → `primary_reason = "fraud_watch"`. Order → blocked_orders.

**IMPORTANT — credit_watch is NOT a block trigger in family D.** The train_004
`primary_reason` allowed set is {none, account_blocked, account_review_required,
fraud_watch, inactive_product, insufficient_effective_stock} — there is NO credit_watch
value. So an active account with `risk_flag == "credit_watch"` does NOT block in family D;
it falls through to normal inventory logic. (Contrast family A, where credit_watch IS a
customer_exception → manual_review. Always let the template's allowed-enum set decide which
flags are triggers.) A `blocked` customer who also carries `credit_watch` is reported as
`account_blocked` (blocked dominates; the credit flag is suppressed).

`blocked_orders` = orders stopped at account/customer-risk level = {blocked,
review_required, fraud_watch}. This is ORDER-level, NOT line-level product reviews — an
inactive-product line does NOT put the order in blocked_orders.

### 4.3 Line-level inactive product (account ok ONLY)
If the line's SKU `active == false` AND the account is ok → that single LINE:
`action = "manual_review"`, `primary_reason = "inactive_product"`, qty = 0. The ORDER is
NOT in blocked_orders (it's a product-master issue, not an account block).

**Account precedence over inactive product:** if an order has an account-level block
(blocked/review/fraud) AND contains inactive SKUs, the ACCOUNT-level reason wins for every
line (e.g. account_review_required), NOT inactive_product. Inactive_product fires ONLY when
the account is active and the SKU is inactive. (Verified: SO-70064 was review_required with
inactive NW-1048/NW-1019 → all lines account_review_required, not inactive_product.)

### 4.4 Normal line (account ok, product active)
- If `requested_effective_available >= quantity` → `action = "ship"`,
  `ship_quantity = quantity`, `primary_reason = "none"`, transfer/backorder = 0.
- Else (requested WH can't clear the line):
  - **CLAMP at 0:** `ship_quantity = min(quantity, max(requested_effective_available, 0))`.
    Requested effective available is frequently NEGATIVE (on_hand below
    reserved+quarantined+safety_stock). The literal `min(quantity, req_ea)` would yield a
    negative ship_quantity and an `uncovered`/backorder/transfer LARGER than the order
    quantity — physically absurd. Always clamp: `ship_quantity = min(quantity, max(req_ea, 0))`.
    When req_ea <= 0, ship_quantity = 0 and uncovered = quantity (the whole line transfers
    or backorders). (Verified: many lines had req_ea of -53, -30, -7, etc.)
  - `uncovered = quantity - ship_quantity`.
  - Look at the OTHER two warehouses; `spare = on_hand - reserved - quarantined -
    safety_stock` (floor at 0 conceptually). **A source must cover the FULL uncovered in a
    single warehouse — do NOT split across multiple warehouses.** If any single other WH has
    `spare >= uncovered`:
    `action = "transfer"`, `transfer_from = <source>` (largest spare, then warehouse_id
    ASC), `transfer_quantity = uncovered`, `backorder_quantity = 0`,
    `primary_reason = "none"` (the transfer resolved the shortfall — reason is none).
    Add a transfer_requests entry. (Verified: SO-70001 9+19=28, SO-70085 0+27=27.)
  - Else NO single other warehouse can cover the full uncovered → `action = "backorder"`,
    `ship_quantity = min(quantity, max(requested_effective_available, 0))`,
    `backorder_quantity = quantity - ship_quantity`, `primary_reason =
    "insufficient_effective_stock"`, transfer = 0. (Verified: SO-70036 NW-1003 and
    SO-70071 NW-1017 backordered because both other WHs were also negative.)

### 4.5 transfer_requests
For each line with action == transfer: `{order_id, line_id, sku, from_warehouse,
to_warehouse = <requested_warehouse>, quantity = transfer_quantity}`. Sorted by order_id
then line_id.

### 4.6 order_rollup outcome
Per order, by the SET of its line actions:
- all `ship` → `ready_to_ship`
- `ship`+`transfer` only (no backorder/manual) → `needs_transfer`
- contains `backorder`, no manual_review, no transfer → `has_backorder`
- contains `manual_review` AND any other action → `mixed_actions`
- all `manual_review` → `manual_review`
- `transfer`+`backorder` mix (no manual) → `mixed_actions`
- any other 2+ non-ship action combination → `mixed_actions`
Rule of thumb: if exactly one non-ship action type is present, use its specific outcome;
if ≥2 non-ship action types (or manual mixed with shippable actions) → mixed_actions;
all-manual → manual_review.

### 4.7 Summary
- `total_orders`, `total_lines` = order/line counts in the wave.
- `ship_lines`/`transfer_lines`/`backorder_lines`/`manual_review_lines` = count by action.
- `blocked_orders` = count of blocked_orders list.
- `transfer_units` = Σ transfer_quantity. `backorder_units` = Σ backorder_quantity.

### 4.8 Common misjudgments (train_004)
- Putting inactive-product orders in `blocked_orders` (only account/risk blocks go there).
- Treating credit_watch as a block trigger in family D — it is NOT (only fraud_watch is; the
  template's primary_reason enum has no credit_watch value).
- Letting inactive_product override an account-level block (account wins; inactive_product
  fires only when account is active).
- Using the LITERAL `min(quantity, requested_effective_available)` without clamping at 0 —
  negative req_ea yields absurd negative ship_quantity and oversized backorder/transfer.
  Always `ship_quantity = min(quantity, max(req_ea, 0))`.
- Splitting a transfer across multiple warehouses — forbidden. A single source must cover
  the full uncovered, else backorder.
- Using `primary_reason = "insufficient_effective_stock"` for transfer lines (use "none";
  the transfer resolved it — insufficient_effective_stock is for backorder).
- Applying per-line logic before checking account status (account affects ALL lines).
- Forgetting to floor transfer spare at 0 / using on_hand alone.
- rollup: marking an order with manual+ship as "manual_review" instead of "mixed_actions";
  or marking a {transfer}-only single-line order as anything other than needs_transfer.

---

## 5. Task family E — Supplier quality-hold / replenishment control review

**Example: train_005.** Output: `{analysis_window, supplier_decisions[],
held_po_ids, release_supplier_ids, summary}`. Reviews a fixed list of target supplier_ids.

### 5.1 Per-supplier decision row
For each target supplier:
- `quality_status`, `supplier_name` from `/suppliers`.
- `recent_incident_count` = incidents with `open_date` in `[start, end]` inclusive
  (`/incidents?supplier_id=<s>&start=<start>&end=<end>`).
- `recent_rma_count` = type RMA. `severe_or_critical_count` = severity ∈ {high, critical}.
  `open_incident_count` = status open.
- `affected_skus` = sorted unique SKUs among recent incidents.
- `sample_incident_ids` = sorted incident_ids, **CAPPED AT 5** (if >5, take the 5 smallest
  after ascending sort).
- `held_po_ids` = sorted PO ids for that supplier with `status ∈ {open, confirmed}`.

### 5.2 Decision thresholds (status-driven; confirmed by data)
The memo does not state exact thresholds. The live data supports a clean STATUS-driven
mapping (verified on train_005):
- `quality_status == "quality_hold"` → **freeze_new_replenishment** (hold open/confirmed POs;
  SUP-003 was quality_hold → freeze).
- `quality_status == "watch"` → **buyer_review_required** (SUP-006 and SUP-010 were both
  watch → buyer_review; recent severe/open incidents reinforce but watch alone suffices).
- `quality_status == "approved"` → **monitor_only** (release POs; no hold). If an approved
  supplier shows heavy recent risk (e.g. severe_or_critical_count >= 2, or
  open_incident_count >= 1, or recent_incident_count >= 3), consider escalating to
  buyer_review_required — but the base case is monitor_only. None of the train targets were
  approved, so this branch was not exercised; follow the template/data in a real task.

In train_005 all three targets were non-approved, so `monitor_count = 0` and
`release_supplier_ids = []`.

### 5.3 held_po_ids (top-level) & release lists
- Top-level `held_po_ids` = sorted union of held POs across suppliers with decision
  freeze OR buyer_review (these are the POs under control).
- `release_supplier_ids` = sorted supplier_ids with decision == monitor_only.

### 5.4 Summary
- `suppliers_reviewed` = number of target suppliers.
- `freeze_count` / `buyer_review_count` / `monitor_count`.
- `held_po_count` = len(top-level held_po_ids).
- `total_recent_incidents` = Σ recent_incident_count.

### 5.5 Common misjudgments (train_005)
- Forgetting the sample_incident_ids cap of 5.
- Holding POs for monitor_only suppliers (only freeze + buyer_review hold POs).
- Not unioning held_po_ids across the controlled suppliers.
- Filtering incidents on close_date instead of open_date.
- Treating "watch" as monitor (watch → buyer_review_required).

---

## 6. Reusable test-time SOP

1. **Identify the family.** Read the prompt + answer_template.json. The top-level
   required keys and enums tell you which family (A–E) you are in. Match enums EXACTLY.
2. **Base URL.** Always use the remote base from environment_access.md
   (<remote-env-url>), never 127.0.0.1 (the prompt's local URL is a decoy; the
   real env is remote). Confirm with `curl /health` first.
3. **Pull masters once.** Cache `/products`, `/customers`, `/warehouses`, `/suppliers`,
   `/boms` in a python dict so you don't re-fetch per record.
4. **Effective stock everywhere.** Every inventory decision uses
   `on_hand - reserved - quarantined - safety_stock`. Memorize it. Floor at 0 only for
   transferable spare at a *source* warehouse.
5. **Precedence before inventory.** Account/risk status → product active status →
   inventory. A blocked account rejects regardless of stock.
6. **Date filters = open_date inclusive** for incidents. Use real close_date for closed
   durations; analysis_date for open durations.
7. **Timely PO = open/confirmed + eta ≤ need date + same warehouse.** received/cancelled
   never count.
8. **Round per the template**: currency 2dp, percentages 1dp, durations 2dp.
9. **Sort everything** per the template's ordering clauses.
10. **Sanity-check**: decision_counts sum to order_count; summary counts consistent with
    line_actions; enums within allowed sets; no extra keys.

### 6.1 Quick dispatch-decision table (families A & D)
| Condition | final_decision / action | next_action / primary_reason |
|---|---|---|
| account blocked | reject_hold / manual_review | hold_credit_or_fraud / account_blocked |
| review_required | manual_review | send_account_review / account_review_required |
| fraud_watch | manual_review | hold_credit_or_fraud / fraud_watch |
| credit_watch | manual_review | hold_credit_or_fraud / credit_watch |
| inactive product (account ok) | manual_review | escalate_product_master / inactive_product |
| shortage (no inactive) | backorder | create_backorder / insufficient_effective_stock |
| low-stock only | delayed_release | delay_and_monitor / none |
| ready | ship_now | release_to_pick / none |

### 6.2 Quick replenishment table (families B & E)
| Situation | action |
|---|---|
| eff ≥ required AND eff ≥ overstock_threshold | overstock_excluded (target_overstock) |
| eff ≥ required AND eff < overstock_threshold | no_action_stocked (stocked_no_gap) |
| gap covered by timely PO | timely_po_covered (timely_po_covers_gap) |
| gap covered by transfer | transfer_only |
| gap needs purchase | purchase_required |
| supplier quality_hold | freeze_new_replenishment |
| supplier watch / approved+risk | buyer_review_required |
| supplier approved, low risk | monitor_only |

### 6.3 Quick supplier-scorecard precedence (family C)
ESCALATE_SUPPLIER (quality_hold+≥3 inc | critical RMA | ≥3 RMA & ≥$15k) >
PROCESS_REVIEW (WO≥3 & WO>RMA) >
WATCHLIST (watch/hold status | inc≥4 | cost≥$12k | severe≥2) >
MONITOR.
