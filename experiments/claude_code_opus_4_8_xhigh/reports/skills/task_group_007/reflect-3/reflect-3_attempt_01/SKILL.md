# SKILL: Northwind Components ERP Decision Tasks

Reusable workflow for the Northwind Components inventory / order-fulfillment domain.
These tasks give you a memo/request payload plus an `answer_template.json`, and you
must query a live ERP API, apply the embedded business rules, and return one JSON
object matching the template exactly. This skill captures the domain rules, API
behavior, output conventions, and exclusion pitfalls that were verified by feedback.

There is NO judge available at solve time. Solve deterministically from the payload
rules + live API data. Do not call any scoring/feedback endpoint.

---

## 1. ERP API — endpoints and how to use them

Base URL is provided by the runner (treat it as `$BASE`). Ignore any prompt text that
tells you to start a local `127.0.0.1:8007` server or read an `env/` directory — always
use the remote base URL the runner gives you. All responses are JSON.

GET endpoints:
- `/health` — manifest with record counts (sanity check the dataset is loaded).
- `/products` , `/products/<sku>` — product master.
- `/customers` , `/customers/<customer_id>` — customer master.
- `/suppliers` — supplier master (includes `quality_status`).
- `/warehouses` — 3 warehouses: `WH_NORTH` (07102), `WH_CENTRAL` (60607), `WH_WEST` (89502).
- `/inventory?warehouse_id=&sku=` — stock rows (omit params to pull all 162 rows once).
- `/purchase_orders?supplier_id=&sku=&status=` — POs.
- `/orders?wave=&required_date=&customer_id=` , `/orders/<order_id>` — sales orders.
- `/shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=` — parcel quote
  (`speed` ∈ ground | two_day | overnight).
- `/incidents?start=&end=&supplier_id=&sku=&incident_type=&status=` — quality incidents.
- `/boms` , `/boms/<bom_id>` — bills of material.

Performance / mechanics:
- Prefer `curl` for fetching; pull whole collections ONCE (`/products`, `/customers`,
  `/inventory`, `/purchase_orders`, `/suppliers`) and index them locally by key, rather
  than many per-id calls. (Some HTTP clients are very slow per-request; curl is fast.)
- The remote can occasionally return an empty reply (curl exit 52). Just retry the call.

### Record shapes (fields you will use)
- product: `sku, active(bool), category, safety_stock, overstock_threshold, supplier_id,
  unit_cost, weight_lb, name`.
- customer: `customer_id, name, account_status(active|review_required|blocked),
  risk_flag(none|fraud_watch|credit_watch), tier(strategic|standard|economy),
  margin_band(high|medium|low)`.
- inventory row: `warehouse_id, sku, on_hand, reserved, quarantined, last_count_date`.
- order: `order_id, customer_id, warehouse_id, destination_zip, priority, required_date,
  shipping_speed, wave, lines[{line_id, sku, quantity, unit_price}]`.
- purchase_order: `po_id, sku, supplier_id, warehouse_id, status(open|confirmed|received|
  cancelled), quantity, eta`.
- incident: `incident_id, supplier_id, sku, warehouse_id, incident_type(RMA|WORK_ORDER),
  severity(low|medium|high|critical), status(open|closed), open_date, close_date,
  resolution_cost, root_cause`.
- supplier: `supplier_id, name, region, quality_status(approved|watch|quality_hold)`.
- bom: `bom_id, name, warehouse_id, target_date, components[{sku, quantity_per_kit}]`.

### Incident date-window behavior
`/incidents?start=&end=` filters on `open_date` and is INCLUSIVE of both ends. The API
window matches the payload's `incident_date_filter` exactly; you can trust it as the
filtered population (no client-side re-filtering needed if you pass the payload dates).
Quote endpoint: `total_cost` is deterministic given (warehouse, zip, weight_lb, speed);
it scales with weight to the cent, so the weight you pass matters. `zone_distance` and
`service_days` depend only on warehouse→zip and speed, not on weight.

---

## 2. Core business definitions (used across multiple task types)

### Effective / available-to-promise (ATP) stock — CRITICAL
"Effective available" stock is NOT raw on_hand. The allocation memos state that stock
"already reserved, quarantined, or held as normal operating buffer" is not freely
available. The normal operating buffer = the product's `safety_stock`. So:

    effective_available(wh, sku) = max(0, on_hand - reserved - quarantined - safety_stock)

Use this for line allocation decisions and for the `requested_effective_available`
output field. (A simpler `on_hand - reserved - quarantined` ATP exists, but when a memo
mentions "normal operating buffer" / "protected stock", subtract `safety_stock` too.)
When deciding transfers, a source warehouse may only contribute its OWN effective
available (never dipping into its protected/safety stock).

### Customer exception precedence (account/risk gating)
From customer master, map to an exception, hardest first:
1. `account_status == blocked`  -> account_blocked
2. `risk_flag == fraud_watch`   -> fraud_watch
3. `risk_flag == credit_watch`  -> credit_watch
4. `account_status == review_required` -> account_review_required (a.k.a. review_required)
5. else -> none

"Blocked orders" (orders stopped at account / customer-risk level) include ALL
account-level holds: account_blocked, fraud_watch, AND review_required. Verified: a
product-only review (inactive SKU) is a LINE-level review and does NOT make the order a
"blocked order". (Removing review_required from the blocked set produced wrong results —
keep it in.)

### Product status gating
`active == false` => the line needs `manual_review` with reason `inactive_product`. This
is a line-level product-master review, not an account block.

### Severity
"Severe" / "severe_or_critical" = severity in {high, critical}.

### Incident duration (days)
- closed incident: calendar days from `open_date` to `close_date`.
- open incident: calendar days from `open_date` to the `analysis_date` in the payload.
Round per the payload's `duration_precision` (usually 2 decimals).

### Purchase-order eligibility
- "Timely" / coverage POs for a build: same target warehouse, `status ∈ {open, confirmed}`,
  and `eta <= needed_by` (the build/needed date). `received` POs are already reflected in
  on_hand — do not double-count them. `cancelled` POs never count.
- For supplier "held PO" controls: open or confirmed POs for that supplier.

---

## 3. Output conventions (apply to every task)

- Return ONLY the JSON object; no prose, no markdown fences.
- Include EVERY `required_top_level_key` and every `item_required_keys` field, even when
  empty (`[]`, `0`, `"none"`, or `null` where the enum allows null).
- Respect enums exactly — never invent values outside `allowed_values`.
- Sorting: follow each list's stated `ordering` precisely. Common ones:
  - records/line_actions: by `order_id` asc, then `line_id` asc.
  - SKU lists: ascending by SKU string.
  - scorecards: `supplier_id` ascending.
  - tie-break chains (e.g. top-escalation): `incident_count` desc, then
    `total_resolution_cost` desc, then `supplier_id` asc — implement the FULL chain.
  - transfer_requests sometimes: sku asc, then quantity desc, then from_warehouse asc.
- Currency: round to 2 decimals (`unit_cost`, `extended_cost`, `total_*_cost`,
  `total_cost_usd`). `extended_cost = round(unit_cost * quantity, 2)`.
- Percentages: round to 1 decimal; denominator = the full filtered population unless the
  payload says otherwise.
- Integer fields stay integers (counts, unit quantities, zone_distance, service_days).
- `required_value` fields (e.g. `wave_id`, `task_id`) must equal the literal required value.
- Summary list fields (blocked_order_ids, manual_review_order_ids, etc.) must be sorted
  and consistent with the per-record results.
- `sample_incident_ids`: sorted list, capped at MAX 5.
- `affected_skus`: sorted unique set of SKUs from the filtered incidents.

---

## 4. SOP per task archetype

### A. Supplier incident scorecard (fully rule-specified — most reliable)
The request payload supplies the entire policy (filter window, duration rule, percentage
rule, severe values, recommendation precedence + code conditions). Follow it literally.
1. GET `/incidents?start=&end=` with the payload window; GET `/suppliers`.
2. Group incidents by `supplier_id`. supplier_count = suppliers with >=1 filtered incident.
3. Per supplier compute: incident_count, incident_percentage (of full population, 1 dp),
   total_resolution_cost (2 dp), avg_duration_days (2 dp, per duration rule),
   rma_count, work_order_count, open_incident_count, severe_incident_count (high|critical).
4. recommendation_code — evaluate the precedence list TOP-DOWN, first match wins. Read each
   code's conditions exactly (e.g. ESCALATE if on quality_hold with >=N incidents, OR any
   critical RMA, OR >=N RMAs with >= $X cost; PROCESS_REVIEW if WORK_ORDER>=3 and
   WORK_ORDER>RMA; WATCHLIST if quality_status in {watch,quality_hold} or count>=4 or
   cost>=12000 or severe>=2; else MONITOR). Use the exact thresholds from the payload.
5. top_escalation_suppliers = only ESCALATE rows, sorted by the stated tie-break chain.
6. highest_cost_supplier_id / highest_share_supplier_id = argmax (tie-break supplier_id asc).
This archetype is fully deterministic when the payload rules are followed exactly.

### B. Wave allocation / transfer decision (line-level)
1. GET the wave: `/orders?wave=<WAVE_ID>`. GET customers, products, inventory.
2. For each order line in sort order:
   a. Customer gate first: blocked/fraud/review_required => `manual_review`, primary_reason
      = account_blocked | fraud_watch | account_review_required; add order to blocked_orders.
   b. Product gate: inactive => `manual_review`, primary_reason = inactive_product (NOT a
      blocked order).
   c. Else allocate from requested warehouse effective_available (ATP minus safety stock):
      - eff_avail >= qty  -> `ship`, ship_quantity = qty.
      - eff_avail < qty but one other warehouse's effective stock can cover the remainder ->
        `transfer`: ship_quantity = usable requested-wh qty, pick ONE source warehouse for
        the uncovered quantity (transfer_from / transfer_quantity), add a transfer_request.
      - otherwise -> `backorder`, backorder_quantity = qty, reason insufficient_effective_stock.
   d. Consume allocated stock as you go so later lines see the reduced availability.
3. order_rollup outcome per order from its line action set:
   - all ship -> ready_to_ship
   - involves transfer (with/without ship) -> needs_transfer
   - has a backorder line (e.g. ship+backorder) -> has_backorder
   - all manual_review -> manual_review
   - other combinations (e.g. manual_review + transfer/backorder) -> mixed_actions
   (Verified: ship+backorder => has_backorder, NOT mixed_actions.)
4. blocked_orders = account-level holds (blocked, fraud, review_required), sorted.
5. summary counts: total_orders, total_lines, ship/transfer/backorder/manual_review_lines,
   blocked_orders (count), transfer_units (sum transfer_quantity), backorder_units.

### C. Replenishment / kit MRP from BOMs
1. GET each BOM (`/boms/<id>`). total_required per component = sum over builds of
   (build_quantity * quantity_per_kit), aggregated across BOMs that share a SKU.
2. target_effective_available at the planning warehouse (ATP). Gap = required - available.
3. timely_po_qty = same-warehouse open/confirmed POs with eta <= needed_by; if they cover
   the gap -> final_action timely_po_covered / exclusion timely_po_covers_gap.
4. If a gap remains, cover from other warehouses' effective stock (transfer_only), else
   raise a purchase_requisition for the shortfall (purchase_required) at the product's
   supplier_id and unit_cost (extended_cost = unit_cost*qty, 2 dp).
5. If available already meets required -> no_action_stocked / stocked_no_gap. If a SKU is
   already over `overstock_threshold`, exclude it (target_overstock) and do not add stock.
6. needed_by = earliest build_date among BOMs using that component. Sort/round per template.

### D. Supplier replenishment-control (incidents + quality + POs)
1. GET `/incidents?start=&end=&supplier_id=` per target supplier and `/suppliers`,
   `/purchase_orders?supplier_id=`.
2. Per supplier compute recent_incident_count, recent_rma_count, severe_or_critical_count,
   open_incident_count, affected_skus (sorted unique), sample_incident_ids (sorted, <=5).
3. decision ∈ {freeze_new_replenishment, buyer_review_required, monitor_only}. Baseline:
   quality_hold -> freeze; watch -> buyer_review; approved -> monitor; and let recent
   incident activity (open incidents / severity / counts) escalate or de-escalate per any
   thresholds the payload states. held_po_ids for a supplier = its open/confirmed PO ids
   when the decision is not monitor_only.
4. held_po_ids (top level) = sorted unique union; release_supplier_ids = monitor_only
   suppliers; summary tallies the decision counts, held_po_count, total_recent_incidents.

---

## 5. Common misjudgments that cause wrong answers (avoid these)

- Using raw on_hand (or even on_hand-reserved-quarantined) as "available" when the memo
  says protected/normal-buffer stock is excluded — you must subtract `safety_stock` too.
- Dropping review_required orders from `blocked_orders`. Account review IS account-level;
  it belongs in blocked_orders. Only inactive-product (line-level) reviews are excluded.
- Treating an inactive-product manual_review as an account block (it is line-level only).
- Counting `received`/`cancelled` POs as coverage. Only open/confirmed, and only with
  `eta <= needed_by`, are "timely".
- Forgetting the full multi-key sort/tie-break chains; partial sorts fail ordering checks.
- Currency not rounded to exactly 2 dp, percentages not 1 dp, or putting floats where the
  template demands integers.
- Passing the wrong weight to `/shipping/quote` (it changes `total_cost` to the cent).
- Omitting required keys when empty — always emit `[]`, `0`, `"none"`, or `null`.
- Misreading the recommendation/decision precedence: evaluate top-down, FIRST match wins,
  and use the exact numeric thresholds from the payload rather than guessing.

---

## 6. General execution checklist

1. Read the prompt + every payload file (memo + answer_template.json). The payload often
   contains the EXACT policy/thresholds — encode them literally; do not improvise rules.
2. Identify the archetype (A/B/C/D above) and the key entities to pull.
3. Pull whole collections once via curl; index locally; query targeted endpoints (wave,
   incidents window, supplier POs) as needed.
4. Compute with effective-stock, customer/product gating, and date-window rules above.
5. Build output strictly to the template: keys, enums, sort orders, rounding, integers.
6. Validate: every required key present, enums valid, lists sorted, currency 2 dp,
   summary consistent with detail rows, required_value literals correct.
7. Emit only the JSON object.
