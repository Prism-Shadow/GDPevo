# Northwind Components ERP Fulfillment — Solver Skill

Transferable operating procedure for the Northwind Components ERP fulfillment
evaluation. Distilled from the 5 train tasks and verified against the live API.
Use this at TEST time to solve unseen variants of the same task families.

This skill is self-contained. It never instructs calling any judge/scoring
endpoint — only the public ERP API.

---

## 0. Meta-SOP (do this first, every task)

1. **Read the prompt + every payload file (`input/payloads/*`) and
   `answer_template.json` literally.** Memos frequently embed the exact
   business rules you must follow: the incident date-filter field, severity
   values that count as "severe", recommendation policy + precedence,
   decision thresholds, sort orders, caps, and rounding precision. The
   `answer_template.json` is the schema CONTRACT (field names, enums, types,
   ordering, required-value literals like `wave_id`). When a memo/template
   states a rule, follow it exactly — it overrides any "default" below.
2. **Identify the task family** (Section 2) and reuse the matching SOP.
3. **Query the live ERP API** (Section 1) for the real records. Do NOT use
   cached snapshots, do NOT read `env/` source, do NOT start a local server.
4. **Return ONLY a single JSON object** matching the template — no narrative,
   no markdown fences, no extra keys beyond what the template requires.
5. **Sort every list** exactly as the template specifies (most are ascending
   by id/sku; some are "quantity descending, then id ascending"). Getting
   ordering wrong fails the match.

---

## 1. The Remote ERP API

Base URL and endpoints come from the task's `environment_access.md` / runner.
Endpoints (all GET, JSON):

- `GET /health` — status + manifest (record counts, seed). Call once to
  confirm liveness and see dataset size.
- `GET /products` and `GET /products/<sku>` — SKU master. Fields: `sku`,
  `name`, `category`, `active` (bool), `supplier_id`, `unit_cost`,
  `weight_lb`, `safety_stock`, `overstock_threshold`.
- `GET /customers` and `GET /customers/<customer_id>` — account/risk state.
  Fields: `customer_id`, `name`, `tier`, `account_status`
  (`active` | `review_required` | `blocked`), `risk_flag`
  (`none` | `credit_watch` | `fraud_watch`), `margin_band`.
- `GET /warehouses` — `warehouse_id` (`WH_NORTH` / `WH_CENTRAL` / `WH_WEST`),
  `name`, `zip`, `region`.
- `GET /inventory?warehouse_id=&sku=` — `on_hand`, `reserved`, `quarantined`,
  `last_count_date`. Returns a list (may be empty if no stock record).
- `GET /purchase_orders?supplier_id=&sku=&status=` — `po_id`, `supplier_id`,
  `sku`, `warehouse_id`, `quantity`, `eta` (YYYY-MM-DD), `status`
  (`open` | `confirmed` | others).
- `GET /orders?wave=&required_date=&customer_id=` and `GET /orders/<order_id>`
  — `order_id`, `customer_id`, `warehouse_id`, `destination_zip`,
  `shipping_speed` (`ground` | `two_day` | `overnight`), `required_date`,
  `line_items[]` (`line_id`, `sku`, `quantity`, `unit_price`).
- `GET /shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=` —
  returns `zone_distance` (int), `service_days` (int), `total_cost` (float,
  already 2 dp), plus `base_rate`, `fuel_surcharge_rate`, `carrier`.
- `GET /incidents?start=&end=&supplier_id=&sku=&incident_type=&status=` —
  `incident_id`, `supplier_id`, `sku`, `warehouse_id`, `incident_type`
  (`RMA` | `WORK_ORDER`), `open_date`, `close_date` (may be null/absent if
  open), `status` (`open` | `closed`), `severity`
  (`low` | `medium` | `high` | `critical`), `resolution_cost`, `root_cause`.
- `GET /suppliers` — `supplier_id`, `name`, `region`, `quality_status`
  (`approved` | `watch` | `quality_hold`).
- `GET /boms` and `GET /boms/<bom_id>` — `bom_id`, `name`, `warehouse_id`,
  `components[]` (`sku`, `quantity_per_kit`), `target_date`.

Calling notes: the server speaks HTTP/1.0 and closes each connection. Use
`curl -sS --max-time 30 '<url>'` per call (or `urllib` with a timeout). Parse
JSON with python3 `json`. Filter `incidents` by `open_date` yourself when the
query params do not give you the exact inclusive window you need.

---

## 2. Task families and their output shapes

### Family A — Expedite-queue dispatch decision (one record per order)
Output: `wave_id`, `records[]` (one per memo order_id, sorted ascending),
`summary`. Each record classifies inventory status, customer exception, final
decision, next action, SKU exception lists, and a shipping quote.

### Family B — BOM replenishment package (kit build)
Output: `task_id`, `plan_date`, `kit_targets[]`, `component_plan[]`,
`transfer_requests[]`, `purchase_requisitions[]`, `excluded_components[]`,
`summary`. Explodes BOMs against target-warehouse stock, applies timely-PO
coverage, inter-warehouse transfers, then purchase requisitions.

### Family C — Supplier incident scorecard
Output: `analysis_window`, `summary`, `supplier_scorecard[]`,
`top_escalation_suppliers[]`, `highest_cost_supplier_id`,
`highest_share_supplier_id`. Aggregates incidents over a date window with a
controlled recommendation code per supplier.

### Family D — Allocation / transfer-wave decision (one action per order LINE)
Output: `wave_id`, `line_actions[]`, `transfer_requests[]`,
`blocked_orders[]`, `order_rollup[]`, `summary`. Classifies every line as
ship/transfer/backorder/manual_review.

### Family E — Quality-hold / replenishment-control review
Output: `analysis_window`, `supplier_decisions[]`, `held_po_ids[]`,
`release_supplier_ids[]`, `summary`. Decides freeze / buyer-review / monitor
per listed supplier and lists held POs.

---

## 3. Core business rule: effective (available) stock

**`effective_stock = on_hand − reserved − quarantined − safety_stock`**

- `safety_stock` comes from the PRODUCT master (not the inventory record). The
  allocation memo calls it the "normal operating buffer".
- This is the single most important rule and the most common misjudgment:
  subtract ALL of `reserved`, `quarantined`, AND `safety_stock`. Subtracting
  only reserved+quarantined (forgetting safety_stock) gives wrong numbers.
  Subtracting nothing (using raw `on_hand`) is also wrong.
- "Non-protected / freely usable" stock at a warehouse = this effective value.
  Transfers and shipments may use only non-protected stock.
- Negative effective stock is valid (means stock is below all protections).
- Verified against gold: e.g. NW-1025 @ WH_NORTH on=124, reserved=14,
  quarantined=21, safety_stock=14 → effective=75, matching the recorded
  `requested_effective_available`.

---

## 4. Decision precedence (applies across families)

Customer/account state is evaluated at the ORDER level and overrides inventory.
Product state (inactive) is evaluated at the LINE level. Among good-account
lines, stock outcome is decided last.

### 4.1 Customer exception mapping (account/risk → exception)
Map the customer record to a single exception value (Family A enum:
`none` | `review_required` | `account_blocked` | `fraud_watch` |
`credit_watch`). Family D folds the same signals into `primary_reason`:

1. `account_status == blocked` → **account_blocked** (this dominates any
   risk_flag; e.g. a blocked customer with `credit_watch` is
   `account_blocked`).
2. else `risk_flag == fraud_watch` → **fraud_watch**.
3. else `risk_flag == credit_watch` → **credit_watch** (Family A). In Family D
   there is no `credit_watch` reason — fold it to **account_review_required**
   (treat like a credit review) unless the test memo says otherwise.
4. else `account_status == review_required` → **review_required**
   (Family D: **account_review_required**).
5. else (`active` + `none`) → **none**.

The customer `tier` (strategic, etc.) does NOT change these decisions.

### 4.2 Family A (expedite) final_decision / next_action precedence
Per order, after classifying each line's stock (Section 5.1):

1. `account_blocked` → **reject_hold** / `hold_credit_or_fraud`.
2. `review_required` (account) → **manual_review** / `send_account_review`
   (overrides inventory).
3. `fraud_watch` (or `credit_watch`) on an otherwise-active account →
   **manual_review** / `hold_credit_or_fraud`.
4. any inactive SKU on the order (and no account/risk block) →
   **manual_review** / `escalate_product_master`.
5. any shortage (effective < line qty for an active SKU) → **backorder** /
   `create_backorder`.
6. any low_stock (but no shortage, no inactive) → **delayed_release** /
   `delay_and_monitor`.
7. otherwise → **ship_now** / `release_to_pick`.

### 4.3 Family D (allocation) line action precedence
1. Order-level account/risk blocker (blocked / review_required / fraud_watch /
   credit_watch) → EVERY line of that order is **manual_review** with the
   matching `primary_reason` (`account_blocked` / `account_review_required` /
   `fraud_watch`); `ship_quantity` 0, no transfer, no backorder. The whole
   order goes into `blocked_orders`.
2. Else, per line: if `product.active == false` → **manual_review** /
   `inactive_product` (regardless of stock).
3. Else per line, decide by stock (Section 5.2): **ship** / **transfer** /
   **backorder** with `primary_reason` `none` or `insufficient_effective_stock`.

`blocked_orders` = orders stopped at the ACCOUNT/RISK level only (NOT
product-only manual-review orders). Sort ascending.

### 4.4 order_rollup outcomes (Family D)
For each order, after line actions, choose the outcome:
- if any line is `manual_review`: if ALL lines are manual_review →
  `manual_review`; else → `mixed_actions`.
- else if any `backorder` line → `has_backorder`.
- else if any `transfer` line → `needs_transfer`.
- else (all `ship`) → `ready_to_ship`.
Sort `order_rollup` by order_id ascending.

---

## 5. Stock classification & line outcomes

### 5.1 Per-SKU classification (Family A SKU lists + inventory_status)
For each order line, compute `effective_stock` at the order's warehouse for
that SKU (Section 3). Then:
- **shortage**: `effective_stock < line.quantity` AND `product.active == true`.
  (An inactive SKU can ALSO be a shortage if its effective < qty — it appears
  in BOTH `shortage_skus` and `inactive_skus`.)
- **inactive**: `product.active == false`.
- **low_stock**: `line.quantity <= effective_stock < product.safety_stock`
  (coverable but below the safety buffer; only for active SKUs that are not
  shortages).

Sort each list ascending by SKU. These lists are INDEPENDENT — a SKU may
appear in more than one.

`inventory_status` for the order (precedence):
1. `inactive_and_shortage` — has at least one inactive SKU AND at least one
   shortage SKU.
2. `inactive_sku` — has an inactive SKU, no shortage.
3. `shortage` — has a shortage SKU, no inactive.
4. `low_stock` — has a low_stock SKU, no shortage, no inactive.
5. `ready` — none of the above.

### 5.2 Family D line stock outcome (ship / transfer / backorder)
Let `qty` = line quantity, `eff_req` = effective_stock at the REQUESTED
warehouse, `ship_qty = max(0, min(qty, eff_req))`, `uncovered = qty − ship_qty`.

- If `eff_req >= qty` → **ship**, `ship_quantity = qty`, transfer 0, backorder 0.
- Else if SOME other (non-requested) warehouse has `effective_stock >= uncovered`
  (a single source that can fully cover the deficit without protected stock) →
  **transfer**: `ship_quantity = ship_qty`,
  `transfer_from` = the source warehouse with the LARGEST available
  effective_stock (ties → follow memo/template; if unspecified pick lowest
  warehouse_id for determinism), `transfer_quantity = uncovered`,
  `backorder_quantity = 0`, `primary_reason = "none"`.
- Else (no single source can cover the deficit) → **backorder**:
  `ship_quantity = 0`, `transfer_from = null`, `transfer_quantity = 0`,
  `backorder_quantity = qty`, `primary_reason = "insufficient_effective_stock"`.

Family D uses ONE source warehouse per transfer line (the transfer_requests
list has one entry per transfer line). This differs from Family B (which may
split a transfer across multiple warehouses).

Verified: SO-70001 NW-1042 @ WH_WEST (eff=9, qty=28) → ship 9 + transfer 19
from WH_CENTRAL (eff=49, the largest of WH_CENTRAL=49 / WH_NORTH=33). Lines
where every other warehouse's effective < uncovered (e.g. NW-1003, NW-1017)
→ backorder.

---

## 6. Shipping quote (Families A, and any task that requests quotes)

For an order:
- `warehouse_id` = order's warehouse; `destination_zip` = order's destination.
- `weight_lb` = Σ over all line items of `line.quantity × product.weight_lb`
  (use the product master weight). Pass the full precision sum to the quote.
- `speed` = the order's `shipping_speed` (ground / two_day / overnight).
  Quotes are computed for EVERY order in the queue using the order's own
  speed — even when the decision is backorder/reject/manual_review. Operator
  notes in the memo ("overnight quote needed even if not released", "quote
  using the order's requested speed") just confirm this default.
- Call `GET /shipping/quote?...`. The record to emit:
  `zone_distance` (int, as returned), `service_days` (int, as returned),
  `total_cost_usd` = the API's `total_cost` (already 2 dp). `zone_distance`
  can be 0 when warehouse and destination are in the same zone.

`summary.total_shipping_cost_usd` = Σ of every record's `total_cost_usd`,
rounded to 2 decimals.

Verified: SO-70070 (WH_NORTH→02128, ground, 27×9.68=261.36 lb) → zone 0,
service_days 5, total_cost 346.49 — matches gold exactly.

---

## 7. Family B — BOM replenishment algorithm

Inputs: a production memo listing BOMs with `target_build_quantity` and
`target_build_date` at a planning warehouse; product master; inventory at all
warehouses; purchase orders.

### 7.1 Aggregate component demand
For each BOM, `total_required(sku) = Σ (quantity_per_kit × target_build_quantity)`
across the BOMs that contain the SKU (a SKU can appear in multiple BOMs —
sum across all of them). E.g. a SKU at 6/kit in two 18-unit kits → 216.

### 7.2 Per-component coverage (component_plan row)
Let `target_eff = effective_stock(sku) at the PLANNING warehouse`.
`gap = total_required − target_eff` (can be negative).

Decision tree:
1. **No gap** (`target_eff >= total_required`):
   - if `target_eff >= product.overstock_threshold` →
     `final_action = overstock_excluded`, `exclusion_reason = target_overstock`;
     add to `excluded_components` with `supporting_po_ids = []`. (Warehouse is
     already at/above its overstock ceiling — do not add stock.)
   - else → `final_action = no_action_stocked`,
     `exclusion_reason = stocked_no_gap`; add to `excluded_components`
     (reason `stocked_no_gap`).
   - Both no-gap cases: `transfer_qty = 0`, `purchase_requisition_qty = 0`,
     `coverage_po_ids = []`.
2. **Gap** (`target_eff < total_required`):
   a. **Timely PO coverage**: `timely_po_qty` = Σ `quantity` of POs for that
      SKU at the PLANNING warehouse with `status` in {`open`,`confirmed`} AND
      `eta <= build_date`. The relevant `build_date` is the BOM build date for
      that component (if the SKU is in multiple BOMs, use the EARLIEST build
      date that needs it). `coverage_po_ids` = those PO ids sorted ascending.
      - If `timely_po_qty >= gap` → the gap is covered: `final_action =
        timely_po_covered`, `exclusion_reason = timely_po_covers_gap`,
        `transfer_qty = 0`, `purchase_requisition_qty = 0`; add to
        `excluded_components` (`reason = timely_po_covers_gap`,
        `supporting_po_ids = coverage_po_ids`).
   b. Otherwise, fill `gap` with transfers then purchases:
      - `transfer_qty = min(gap, Σ effective_stock(sku) over all OTHER
        warehouses)`. Source across the non-planning warehouses, taking from
        each up to its effective_stock, ordered by available quantity
        DESCENDING (largest surplus first), then by warehouse_id. Emit one
        `transfer_requests` entry per source warehouse used (Section 7.3).
      - `purchase_requisition_qty = gap − transfer_qty`.
      - `final_action`: if `purchase_requisition_qty > 0` →
        `purchase_required`; elif `transfer_qty > 0` → `transfer_only`.
      - `exclusion_reason = "none"` (not excluded).

Verified: NW-1039 @ WH_WEST eff=166, required=144, threshold=162 → no gap AND
166≥162 → overstock_excluded. NW-1005 @ WH_WEST eff=−16, required=90, gap=106,
PO-50066 (open, eta 2026-03-02 ≤ build 2026-06-10, WH_WEST, qty 335) covers →
timely_po_covered. NW-1014: gap=195, transferable=66(WH_NORTH)+24(WH_CENTRAL)=90
→ transfer 90, purchase 105.

### 7.3 transfer_requests (Family B)
Fields: `sku`, `from_warehouse_id`, `to_warehouse_id` (the planning
warehouse), `quantity`, `needed_by`. `needed_by` = the EARLIEST build date of
the BOM(s) containing the SKU (transfers must arrive before the first build).
Order: sku ascending, then quantity descending, then from_warehouse_id
ascending.

### 7.4 purchase_requisitions (Family B)
Fields: `sku`, `supplier_id` (= `product.supplier_id`), `warehouse_id` (the
planning warehouse), `quantity`, `needed_by`, `unit_cost` (=
`product.unit_cost`), `extended_cost` = `quantity × unit_cost` rounded to 2 dp.
`needed_by` = the LATEST build date of the BOM(s) containing the SKU (purchases
cover the later build). Order: sku ascending. (When a SKU is in only one BOM,
both transfer `needed_by` and purchase `needed_by` equal that BOM's build date.)

### 7.5 summary (Family B)
- `component_count` = number of component_plan rows.
- `total_purchase_units` = Σ purchase_requisition_qty.
- `total_purchase_cost` = Σ extended_cost, 2 dp.
- `total_transfer_units` = Σ transfer_qty (component-level) = Σ transfer_requests.quantity.
- `timely_po_covered_units` = Σ of the GAPs covered by timely POs (= the
  shortfall each timely-po-covered component had, NOT the raw PO quantity).

---

## 8. Family C — Supplier incident scorecard

The request payload (`q1_scorecard_request.json` or equivalent) embeds the
authoritative rules. Parse it for: `incident_date_filter` (field, start, end,
inclusive — almost always `open_date`, inclusive), `analysis_date`,
`duration_rule`, `percentage_rule`, precision values, `severe_severity_values`
(often `["high","critical"]`), `scorecard_row_order`,
`top_escalation_order`, and the `recommendation_policy` (precedence + code
conditions). Apply these LITERALLY.

### 8.1 Filter the incident population
Filter incidents where `open_date` is in [start_date, end_date] inclusive
(field = `open_date`, NOT `close_date`). `filtered_incident_count` = size of
this population. `supplier_count` = distinct suppliers with ≥1 filtered
incident.

### 8.2 Per-supplier row
Group filtered incidents by supplier. For each supplier with ≥1 incident:
- `incident_count`, `incident_percentage` = incident_count /
  filtered_incident_count × 100, 1 dp.
- `total_resolution_cost` = Σ `resolution_cost`, 2 dp.
- `avg_duration_days` = mean duration, 2 dp. Duration:
  - closed incident: calendar days `close_date − open_date`.
  - open incident: calendar days `analysis_date − open_date`.
- `rma_count` = incidents with `incident_type == "RMA"`.
- `work_order_count` = incidents with `incident_type == "WORK_ORDER"`.
- `open_incident_count` = incidents with `status == "open"`.
- `severe_incident_count` = incidents with `severity` in the payload's
  `severe_severity_values` (typically high + critical).
- `recommendation_code` (Section 8.3).
Sort rows by supplier_id ascending.

### 8.3 recommendation_code — apply the payload's precedence in order
Typical precedence (highest first): `ESCALATE_SUPPLIER` → `PROCESS_REVIEW` →
`WATCHLIST` → `MONITOR`. Use the FIRST code whose condition is met. Example
conditions from the train payload (use the test payload's wording if it
differs):
- `ESCALATE_SUPPLIER`: supplier is `quality_hold` with ≥3 filtered incidents,
  OR has any critical RMA, OR has ≥3 RMAs and ≥15000.00 total filtered
  resolution cost.
- `PROCESS_REVIEW`: WORK_ORDER incidents ≥3 and exceed RMA incidents
  (`work_order_count >= 3 and work_order_count > rma_count`).
- `WATCHLIST`: quality_status is `watch` or `quality_hold`, OR
  incident_count ≥4, OR total resolution cost ≥12000.00, OR
  severe_incident_count ≥2.
- `MONITOR`: none of the above.
Then re-check ESCALATE before PROCESS_REVIEW before WATCHLIST (precedence).

### 8.4 Top-level rollups
- `top_escalation_suppliers` = supplier_ids with recommendation_code ==
  ESCALATE_SUPPLIER, ordered by: incident_count DESC, then
  total_resolution_cost DESC, then supplier_id ASC.
- `highest_cost_supplier_id` = supplier with max total_resolution_cost
  (ties → lowest supplier_id).
- `highest_share_supplier_id` = supplier with max incident_count (ties →
  lowest supplier_id).
- `summary.overall_rma_count` / `overall_work_order_count` = totals across the
  filtered population.

---

## 9. Family E — Quality-hold / replenishment-control review

Inputs: a memo giving `analysis_window` (start/end), `target_supplier_ids`,
decision choices, and a policy note. Use the live API for incidents, supplier
quality_status, and POs.

### 9.1 Per-supplier decision inputs (over the analysis window, open_date in [start,end] inclusive)
- `recent_incident_count` = incidents in window.
- `recent_rma_count` = incidents in window with incident_type `RMA`.
- `severe_or_critical_count` = incidents in window with severity high or
  critical.
- `open_incident_count` = incidents in window with status `open`.
- `affected_skus` = distinct SKUs in window incidents, sorted ascending.
- `sample_incident_ids` = up to 5 incident ids from window incidents, sorted
  ascending (cap = 5).
- `quality_status` from supplier master.

### 9.2 Decision (precedence; confirm thresholds against the test memo)
1. `freeze_new_replenishment` — `quality_status == quality_hold`.
2. `buyer_review_required` — (not quality_hold) and
   `severe_or_critical_count >= 2`.
3. `monitor_only` — otherwise.

Observed: SUP-003 (quality_hold) → freeze; SUP-006 (watch, severe=2) →
buyer_review; SUP-010 (watch, severe=1, recent=5, open=1) → monitor. Note
`recent_incident_count` and `open_incident_count` do NOT by themselves
escalate to buyer_review in the train data — `severe_or_critical_count >= 2`
is the differentiator. If the test memo gives explicit thresholds, use those.

### 9.3 held_po_ids (per supplier)
- For `freeze_new_replenishment` and `buyer_review_required` suppliers:
  take that supplier's purchase orders with `status` in {`open`,`confirmed`},
  sort ascending by `po_id`, and take the FIRST 5. (The output caps the
  per-supplier held list at 5 — mirroring the sample-incident cap — even
  though more open/confirmed POs may exist.)
- For `monitor_only` suppliers: held_po_ids = `[]` (they are released).
- `held_po_ids` (top-level) = sorted unique union of all per-supplier held
  PO ids.
- `release_supplier_ids` = sorted supplier_ids whose decision is
  `monitor_only`.

### 9.4 summary
`suppliers_reviewed`, `freeze_count`, `buyer_review_count`, `monitor_count`
(decision tallies), `held_po_count` = size of top-level held_po_ids,
`total_recent_incidents` = Σ recent_incident_count across reviewed suppliers.

---

## 10. Common misjudgments — explicit exclusions

- **Effective stock**: subtract `reserved + quarantined + safety_stock` (all
  three). NOT on_hand alone. NOT reserved+quarantined only. `safety_stock`
  lives on the PRODUCT, not the inventory row.
- **Account overrides BEFORE inventory**: a blocked/review/fraud account
  forces manual_review/reject on every line regardless of how much stock
  exists. Do not ship a ready line just because stock is ample if the account
  is flagged.
- **Inactive product BEFORE stock**: an inactive SKU (`active=false`) →
  manual_review/escalate even if stock is ample. In Family A an inactive SKU
  still appears in `inactive_skus` and (if also understocked) in
  `shortage_skus`.
- **Timely PO coverage = open OR confirmed** POs at the PLANNING/TARGET
  warehouse with **eta ≤ build_date**. Not closed/cancelled POs; not POs at
  other warehouses; not eta after the build.
- **Overstock exclusion** only when there is NO gap (`eff >= required`) AND
  `eff >= overstock_threshold`. A component with a real gap is never
  "overstock_excluded" — it gets replenished.
- **Incident date filter** uses `open_date` (inclusive), not `close_date`.
  Open incidents contribute duration from open_date to analysis_date.
- **Recommendation precedence**: evaluate ESCALATE → PROCESS_REVIEW →
  WATCHLIST → MONITOR and take the first match; a supplier meeting WATCHLIST
  but also ESCALATE conditions is ESCALATE.
- **Caps**: `sample_incident_ids` ≤ 5 (sorted). Family-E per-supplier
  `held_po_ids` ≤ 5 (first 5 open/confirmed by po_id). Do NOT cap the
  top-level held_po_ids (it is the full union) and do NOT cap Family-C
  `top_escalation_suppliers`.
- **Shipping quotes** for everyone in the queue (not only releases), using
  each order's own `shipping_speed`, weight = Σ qty×weight_lb.
- **Rounding**: currency/money → 2 dp; incident percentage → 1 dp; duration
  → 2 dp. Quantities and counts are integers.
- **Sort orders**: never omit them — most lists must be sorted (id/sku
  ascending unless the template says otherwise, e.g. transfer_requests is
  "quantity descending then from_warehouse ascending"; top_escalation is
  "incident_count desc, cost desc, supplier_id asc").

---

## 11. Reusable checklist before submitting

- [ ] Output is a single JSON object; no markdown, no trailing prose.
- [ ] Every top-level key from `answer_template.json` is present (and any
      `required_value` literals like `wave_id`/`task_id` match exactly).
- [ ] Every list is sorted exactly as the template specifies.
- [ ] All enums use ONLY the template's allowed values (e.g.
      `final_action`, `action`, `primary_reason`, `recommendation_code`,
      `decision`, `quality_status`).
- [ ] Money fields are 2 dp; percentages 1 dp; durations 2 dp; counts/quantities integers.
- [ ] effective_stock used `on_hand − reserved − quarantined − safety_stock`
      everywhere (line classification, transfers, replenishment, overstock).
- [ ] Account/risk/inactive precedence applied before stock outcomes.
- [ ] Shipping quotes computed for all required orders with correct weight +
      the order's own speed.
- [ ] Filters use the right date field (`open_date`) and inclusive bounds.
- [ ] Caps applied (sample incidents ≤5; Family-E held POs ≤5/supplier).
- [ ] Summary tallies recomputed from the rows (not hardcoded).
