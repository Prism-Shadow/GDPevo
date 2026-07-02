# Northwind ERP Fulfillment — Solver Skill (fewshot)

Transferable operating knowledge for solving Northwind Components fulfillment tasks against the
shared remote ERP API. Read the task prompt + payload memo + `answer_template.json` first; they
define the exact required keys, enums, ordering, and rounding. This skill supplies the business
semantics that the templates leave implicit.

---

## 0. Remote API usage

- Base URL: `<remote-env-url>` (the live environment). Ignore any prompt text telling you
  to run `server.py` / `setup.sh` locally — do NOT read or start `env/`; use only this API.
- The server speaks **HTTP/1.0 and closes each connection**. Every call is a fresh connection.
  Always use: `curl -sS --max-time 30 '<url>'`.
- Parse JSON with `python3 -c "import json,sys; ..."` or `jq`.
- Endpoints (all GET, query params shown):
  - `/health` — manifest with record_counts (products 54, customers 40, warehouses 3, inventory 162,
    purchase_orders 92, orders 88, incidents 212, suppliers 12, boms 9) and seed.
  - `/products` and `/products/<sku>` — `{sku, name, category, active, safety_stock,
    overstock_threshold, unit_cost, weight_lb, supplier_id}`.
  - `/customers` and `/customers/<customer_id>` — `{customer_id, name, tier, margin_band,
    account_status, risk_flag}`. `account_status` ∈ {active, blocked, review_required};
    `risk_flag` ∈ {none, fraud_watch, credit_watch}.
  - `/warehouses` — `{warehouse_id, name, region, zip}`. IDs: WH_NORTH, WH_CENTRAL, WH_WEST.
  - `/inventory?warehouse_id=&sku=` — `{warehouse_id, sku, on_hand, reserved, quarantined,
    last_count_date}`. Filterable by warehouse and/or sku; returns a list.
  - `/purchase_orders?supplier_id=&sku=&status=` — `{po_id, sku, warehouse_id, supplier_id,
    quantity, eta, status}`. status ∈ {open, confirmed, received, cancelled}.
  - `/orders?wave=&required_date=&customer_id=` and `/orders/<order_id>` — `{order_id, wave,
    customer_id, warehouse_id, required_date, shipping_speed, destination_zip, priority,
    lines:[{line_id, sku, quantity, unit_price}]}`. shipping_speed ∈ {overnight, expedited,
    standard, ground}.
  - `/shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=` — `{total_cost, service_days,
    zone_distance, carrier, base_rate, fuel_surcharge_rate, ...}`.
  - `/incidents?start=&end=&supplier_id=&sku=&incident_type=&status=` — `{incident_id, supplier_id,
    sku, warehouse_id, incident_type, severity, status, open_date, close_date, resolution_cost,
    root_cause}`. incident_type ∈ {RMA, WORK_ORDER}; severity ∈ {low, medium, high, critical};
    status ∈ {open, closed}. `start`/`end` filter on `open_date` (inclusive on both ends).
  - `/suppliers` — `{supplier_id, name, region, quality_status}`. quality_status ∈ {approved,
    watch, quality_hold}.
  - `/boms` and `/boms/<bom_id>` — `{bom_id, name, warehouse_id, target_date,
    components:[{sku, quantity_per_kit}]}`.

### Effective available stock (the core primitive)

```
effective_available(wh, sku) = on_hand - reserved - quarantined - safety_stock
```

`on_hand`, `reserved`, `quarantined` come from `/inventory`; `safety_stock` comes from
`/products/<sku>`. This single number drives every inventory decision across all task families.
It can be negative. Always compute it fresh per warehouse+sku; never use `on_hand` alone.

A warehouse has **spare transferable stock** for a sku when its effective_available > 0; the
transferable amount equals that effective_available (the safety_stock is already preserved by the
subtraction, so the full effective amount may be moved out).

---

## 1. Task family: Expedite-queue dispatch (per-order decision + shipping quote)

**Trigger:** prompt mentions an "expedite queue" for a wave, a queue memo listing order_ids, and an
answer template with `records[].{inventory_status, customer_exception, final_decision, next_action,
shortage_skus, inactive_skus, low_stock_skus, shipping_quote}`.

**Per order**, using the order's `warehouse_id` and each line's `quantity`:

1. Compute `effective_available` for every line sku at the order's warehouse.
2. Classify each line sku:
   - **inactive** if `product.active == false`.
   - **shortage** if `effective_available < ordered_quantity`.
   - **low_stock** if NOT shortage AND `effective_available - ordered_quantity < safety_stock`
     (i.e., the line can ship but the remaining effective drops below safety_stock).
3. `shortage_skus`, `inactive_skus`, `low_stock_skus` = sorted-ascending lists of the matching skus.
   (A sku can appear in `inactive_skus` and `shortage_skus` simultaneously; `low_stock_skus`
   excludes shortage skus.)
4. `inventory_status` (whole order):
   - `inactive_and_shortage` if any inactive sku AND any shortage sku.
   - `inactive_sku` if any inactive sku (and no shortage).
   - `shortage` if any shortage sku (and no inactive).
   - `low_stock` if no shortage/inactive but any low_stock sku.
   - `ready` otherwise.
5. `customer_exception` from the customer record (precedence for reporting: blocked wins):
   - `account_status == blocked` → `account_blocked`
   - elif `account_status == review_required` → `review_required`
   - elif `risk_flag == fraud_watch` → `fraud_watch`
   - elif `risk_flag == credit_watch` → `credit_watch`
   - else `none`
6. **Decision precedence (apply top-down, first match wins; account state is checked BEFORE
   inventory):**
   - `account_blocked` → `final_decision=reject_hold`, `next_action=hold_credit_or_fraud`.
   - `review_required` | `fraud_watch` | `credit_watch` → `manual_review` /
     `send_account_review`.
   - `inactive_sku` or `inactive_and_shortage` (no account exception) → `manual_review` /
     `escalate_product_master`.
   - `shortage` (no exception, no inactive) → `backorder` / `create_backorder`.
   - `low_stock` (no exception, no inactive, no shortage) → `delayed_release` /
     `delay_and_monitor`.
   - `ready` → `ship_now` / `release_to_pick`.
7. `shipping_quote`: total weight = Σ `product.weight_lb × line.quantity` over all lines (round to
   2 dp). Call `/shipping/quote?warehouse_id=<order wh>&destination_zip=<order dest>&weight_lb=<w>&speed=<order shipping_speed>`.
   Output object = `{zone_distance:int, service_days:int, total_cost_usd: round(total_cost,2)}`.

**Summary:** `order_count`; `decision_counts` over the 5 final_decision values; `total_shipping_cost_usd`
= Σ records' `total_cost_usd` (2 dp); `blocked_order_ids`, `manual_review_order_ids`,
`backorder_order_ids`, `inactive_sku_order_ids` = sorted lists of order_ids matching those outcomes
(blocked = reject_hold; manual_review includes both account-review and inactive-driven). Records
sorted ascending by order_id.

---

## 2. Task family: BOM component replenishment planning

**Trigger:** prompt has a production memo with `kit_targets[]` (bom_id, warehouse_id,
build_quantity, build_date) and `plan_date`; template has `component_plan[]`,
`transfer_requests[]`, `purchase_requisitions[]`, `excluded_components[]`, `summary`.

**Per component sku** used by any target build at the target warehouse:

1. `total_required` = Σ `quantity_per_kit × build_quantity` over ALL target builds whose BOM
   contains this sku (a sku may appear in multiple BOMs; sum across them). Only builds at the
   target warehouse count.
2. `target_effective_available` = `effective_available(target_warehouse, sku)`.
3. `gap` = `total_required - target_effective_available`.
4. **If `gap <= 0`** (effective ≥ required): `final_action=overstock_excluded`,
   `exclusion_reason=target_overstock`, no transfer, no purchase. Add to `excluded_components`
   with reason `target_overstock`.
5. **Timely PO check:** find POs for this sku at the target warehouse with `status` ∈ {open,
   confirmed} AND `eta <= build_date` of the consuming build (the earliest consuming build's
   build_date). Sum their `quantity` = `timely_po_qty`; collect `coverage_po_ids`.
   - If `timely_po_qty >= gap`: `final_action=timely_po_covered`,
     `exclusion_reason=timely_po_covers_gap`, transfer_qty=0, purchase_requisition_qty=0. Add to
     `excluded_components` with reason `timely_po_covers_gap` and `supporting_po_ids=coverage_po_ids`.
     `timely_po_covered_units` in summary = Σ of these gaps covered.
6. **Otherwise** (`remaining_gap = gap - timely_po_qty > 0`): try transfers.
   - For every OTHER warehouse, transferable = `effective_available(other_wh, sku)` (may be 0/negative;
     only positive counts). Sort other warehouses by transferable DESC. Allocate from largest first
     until `remaining_gap` is met or all spare is exhausted.
   - Each source warehouse that contributes → one `transfer_requests` entry:
     `{sku, from_warehouse_id, to_warehouse_id=target, quantity, needed_by=<consuming build_date>}`.
     `transfer_qty` = total transferred.
   - `purchase_requisition_qty` = `remaining_gap - transfer_qty` (the residual still unmet).
   - `final_action`: `transfer_only` if `purchase_requisition_qty == 0` (and transfer_qty>0);
     `purchase_required` if `purchase_requisition_qty > 0`. `exclusion_reason=none`.
7. `purchase_requisitions[]` entries (for each sku with purchase_requisition_qty>0):
   `{sku, supplier_id=product.supplier_id, warehouse_id=target, quantity=purchase_requisition_qty,
   needed_by=<latest build_date across the plan's kit_targets>, unit_cost=product.unit_cost,
   extended_cost=round(unit_cost×quantity,2)}`.
   - NOTE: transfer `needed_by` = the consuming build's own build_date; purchase-requisition
     `needed_by` = the latest build_date in the whole plan (plan horizon end).
8. **Summary:** `component_count` = distinct skus; `total_purchase_units` = Σ purchase qty;
   `total_purchase_cost` = Σ extended_cost (2 dp); `total_transfer_units` = Σ transfer qty;
   `timely_po_covered_units` = Σ gaps covered by timely POs.

**Common mistakes:** do NOT transfer from a warehouse leaving its safety_stock uncovered — the
effective formula already protects it, so transfer up to the full effective amount. Do NOT count a
PO as timely if its eta is after the build date or its status is received/cancelled. Do NOT create
a purchase requisition for an overstocked sku (gap≤0).

---

## 3. Task family: Supplier quality scorecard (quarterly)

**Trigger:** prompt has a scorecard request with `analysis_window {start_date, end_date,
analysis_date}`; template has `summary`, `supplier_scorecard[]`, `top_escalation_suppliers`,
`highest_cost_supplier_id`, `highest_share_supplier_id`.

1. Filter incidents: `/incidents?start=<start_date>&end=<end_date>`. The window filters on
   `open_date`, **inclusive on both ends**. `filtered_incident_count` = len of this set.
2. `supplier_count` = number of distinct suppliers appearing in the filtered incidents.
3. Per supplier in the filtered set, compute:
   - `incident_count`, `incident_percentage` = `round(100 × incident_count / filtered_incident_count, 1)`.
     (Denominator is the TOTAL filtered population, not per-supplier.)
   - `total_resolution_cost` = Σ `resolution_cost` (2 dp).
   - `avg_duration_days` = mean of per-incident durations, **1 decimal**: for `closed` incidents
     `close_date - open_date` (days); for `open` incidents `analysis_date - open_date` (days).
   - `rma_count` = incidents with `incident_type == RMA`; `work_order_count` = `WORK_ORDER`.
   - `open_incident_count` = status `open`; `severe_incident_count` = severity in {high, critical}.
4. `recommendation_code` — 4-level precedence **ESCALATE_SUPPLIER > PROCESS_REVIEW > WATCHLIST >
   MONITOR**. The cutoff is multi-factor over (incident_count, incident_percentage,
   total_resolution_cost, severe_incident_count, open_incident_count, rma_count, work_order_count,
   avg_duration_days). Calibration guidance from observed boundaries:
   - ESCALATE_SUPPLIER is reached by suppliers combining a critical/high severe incident presence
     with elevated cost (≈ ≥15000) or high count (≈ ≥9) or high share; a single critical incident
     with otherwise modest volume can also escalate.
   - PROCESS_REVIEW: multiple high/critical incidents (severe_or_critical ≥ ~2) but cost/share below
     the escalate band.
   - WATCHLIST: at least one open incident, or a single high-severity incident with low count.
   - MONITOR: minimal activity, no open, no high/critical (or a single closed high-severity only).
   - When uncertain, assign the lower tier; the precedence is strict, so never place a WATCHLIST
     case above a PROCESS_REVIEW one.
   (The exact cutoff resist a clean single-threshold formula from exposed fields; compute all
   metrics and calibrate. Do not invent fields.)
5. `top_escalation_suppliers` = supplier_ids with `recommendation_code == ESCALATE_SUPPLIER`,
   sorted ascending.
6. `highest_cost_supplier_id` = supplier with max `total_resolution_cost`;
   `highest_share_supplier_id` = supplier with max `incident_percentage`.
7. `summary`: `total_resolution_cost` (Σ, 2 dp), `overall_rma_count` (Σ rma_count),
   `overall_work_order_count` (Σ work_order_count).

**Common mistakes:** percentage denominator is the whole filtered population (38 in the sample), not
per-supplier. Open-incident duration uses the analysis_date, not today. severe = {high, critical}
(not a value named "severe"; that severity does not exist).

---

## 4. Task family: Mixed-warehouse allocation / transfer (per-line)

**Trigger:** prompt has an allocation memo (markdown) over a wave; template has `line_actions[]`,
`transfer_requests[]`, `blocked_orders[]`, `order_rollup[]`, `summary`.

**Per order line** (order's requested warehouse, line sku, line quantity):

1. Compute `requested_effective_available` = `effective_available(requested_wh, sku)`.
2. **Customer/product overrides (apply first; customer-level blocks the whole order):**
   - Customer `account_status == blocked` → `action=manual_review`,
     `primary_reason=account_blocked`, ship=0, transfer=0, backorder=0. Add order to `blocked_orders`.
   - Customer `account_status == review_required` → `manual_review` /
     `account_review_required`.
   - Customer `risk_flag == fraud_watch` → `manual_review` / `fraud_watch`.
   - `product.active == false` (inactive) → `manual_review` / `inactive_product` (per-line).
3. **Inventory decision** (no override): let `ship = min(quantity, max(requested_effective_available, 0))`;
   `needed = quantity - ship`.
   - If `needed == 0` → `action=ship`, ship_quantity=quantity.
   - If `needed > 0`: look at OTHER warehouses' transferable effective (positive effective). Pick
     sources largest-first. If the needed quantity can be covered → `action=transfer`,
     `ship_quantity=ship`, `transfer_quantity=needed`, `transfer_from` = the source warehouse
     (if a single source covers it; if multiple sources are required, emit one
     `transfer_requests` row per source warehouse, all sharing the line's order_id/line_id, and
     set line-level `transfer_from` to the largest source / null per template).
   - If the needed quantity cannot be covered by transfers → `action=backorder`,
     `ship_quantity=ship`, `backorder_quantity=quantity - ship - transfer_quantity`,
     `primary_reason=insufficient_effective_stock`. (In the all-negative case `ship=0` and the
     full `quantity` is backordered.)
4. `transfer_requests[]` rows: `{order_id, line_id, sku, from_warehouse, to_warehouse=requested_wh,
   quantity}` — one per source warehouse actually drawn from. Sorted by order_id then line_id.
5. `blocked_orders` = order_ids stopped at account/risk level (blocked, and fraud/review-driven
   manual_review), sorted ascending — NOT line-only inactive-product reviews.
6. `order_rollup[]`: per order, `outcome` ∈
   {ready_to_ship (all lines ship), needs_transfer (any transfer, rest ship),
   has_backorder (any backorder), manual_review (any manual_review line),
   mixed_actions (≥2 distinct non-ship actions)}.
   Precedence: manual_review > has_backorder > needs_transfer > ready_to_ship; use mixed_actions
   when truly heterogeneous. Sort by order_id.
7. `summary`: total_orders, total_lines, ship_lines, transfer_lines, backorder_lines,
   manual_review_lines, blocked_orders (count), transfer_units (Σ transfer_quantity),
   backorder_units (Σ backorder_quantity).

**Common mistakes:** don't ship from a warehouse whose effective is negative (cap ship at
max(eff,0)). Don't backorder a line that could be fully transferred. Manual_review from an account
override zeroes everything else for that line. blocked_orders is at order granularity, not line.

---

## 5. Task family: Quality-hold PO review

**Trigger:** prompt has a `quality_hold_review_memo.json` with `analysis_window {start, end}`,
`target_supplier_ids[]`, and `decision_choices` (freeze_new_replenishment, buyer_review_required,
monitor_only); template has `held_po_ids`, `release_supplier_ids`, `supplier_decisions[]`, `summary`.

The reviewed suppliers come from the memo's `target_supplier_ids` (a fixed list), NOT from scanning
all suppliers.

**Per target supplier:**

1. Fetch recent incidents: `/incidents?start=<window.start>&end=<window.end>&supplier_id=<sid>`
   (open_date inclusive). Also fetch `/suppliers/<sid>` for `quality_status`.
2. Metrics:
   - `recent_incident_count` = len.
   - `recent_rma_count` = incident_type == RMA.
   - `open_incident_count` = status == open.
   - `severe_or_critical_count` = severity ∈ {high, critical}.
   - `affected_skus` = sorted unique incident skus.
   - `sample_incident_ids` = sorted incident_ids, **capped at 5**.
3. `decision`:
   - `quality_status == quality_hold` → `freeze_new_replenishment`.
   - `quality_status == watch` → `buyer_review_required` if `severe_or_critical_count >= 2`
     (multiple high/critical incidents); else `monitor_only`.
4. `held_po_ids`: for `freeze` and `buyer_review` decisions only, take the supplier's open/confirmed
   POs (`/purchase_orders?supplier_id=<sid>` filtered to status ∈ {open, confirmed}), sort ascending
   by po_id, and **cap at 5**. For `monitor_only` → `[]`.
5. `release_supplier_ids` = target suppliers whose decision is `monitor_only`, sorted.
6. `summary`: `suppliers_reviewed` = len(target_supplier_ids); `held_po_count` = total held across
   all freeze/buyer_review suppliers; `freeze_count`, `buyer_review_count`, `monitor_count` =
   decisions per type; `total_recent_incidents` = Σ `recent_incident_count`.

**Common mistakes:** the reviewed set is the memo's list, not all non-approved suppliers. held_po_ids
is capped at 5 (sorted), not all open POs — a supplier may have many open POs but only 5 are held.
sample_incident_ids is also capped at 5. severe_or_critical = {high, critical} (no "severe" value
exists).

---

## 6. Cross-cutting rules & common misjudgments

- **Effective stock is the only stock number that matters.** `on_hand` alone is never the answer.
  Always subtract reserved + quarantined + safety_stock.
- **Decision precedence is account/risk FIRST, then product-inactive, then inventory.** A blocked
  account → reject/manual_review regardless of huge on-hand; a fraud/credit/review flag →
  manual_review; an inactive product → manual_review; only then do shortage/low-stock/ship apply.
- **Sorting:** SKU lists and ID lists are always ascending. Records sorted by order_id; line actions
  by order_id then line_id.
- **Rounding:** currency to 2 decimals; percentages to 1 decimal; durations to 1 decimal
  (scorecards) or integer days (durations themselves are integer day differences).
- **Exclusion rules:**
  - BOM: overstocked at target (gap≤0) → exclude (`target_overstock`); timely PO covers gap →
    exclude (`timely_po_covers_gap`). Everything else with a gap → transfer and/or purchase.
  - Quality review: monitor_only suppliers release POs (held_po_ids = []).
  - Allocation: blocked/review/fraud orders never ship or transfer; inactive-product lines never
    ship.
- **Shipping quote:** weight = Σ(weight_lb × quantity) over ALL lines of the order (not just
  shortage lines). speed = order's shipping_speed. Use the order's warehouse_id and
  destination_zip.
- **PO timeliness:** open OR confirmed with eta ≤ the relevant date (build date for BOM; the PO must
  be at the same warehouse). Received/cancelled POs never count.
- **Transfer sourcing:** only positive effective stock at the OTHER warehouse; largest first; the
  full effective amount is available (safety_stock already preserved in the formula).
- **Incident filtering & dating:** `start`/`end` filter on `open_date`, inclusive both ends. Closed
  duration = close_date − open_date; open duration = analysis_date − open_date. Percentage
  denominator = total filtered incidents (population), not per-supplier.
- **Never** call any judge/evaluator endpoint. Never read `env/`, `server.py`, or data JSON files.
  Use only the documented GET endpoints.

---

## 7. Reusable solver SOP (any task)

1. Read `input/prompt.txt` → identify the task family (expedite / BOM / scorecard / allocation /
   quality-hold) and the wave/plan identifiers.
2. Read the payload memo(s) and `answer_template.json` — the template is the contract: required
   keys, enum values, ordering, precision. Mirror its key names exactly.
3. Pull the needed entity sets from the API (orders in the wave, customers, products, inventory,
   POs, incidents, boms, suppliers as relevant). Cache locally in python dicts to avoid re-fetching.
4. Apply the family's SOP above, computing effective_available and applying precedence in the
   documented order.
5. Assemble the output dict matching the template's shape exactly (keys, enums, sorting, rounding).
   Re-check every enum value is from the allowed set; re-check every list is sorted as specified.
6. Sanity-check summary aggregates (counts sum, costs add up, blocked/manual_review/backorder
   id lists match the records).
7. Return only the JSON.
