# SKILL: Northwind Components ERP Operations (inventory / fulfillment / replenishment / supplier-quality)

Transferable playbook for solving Northwind Components ERP decision tasks. Each task
gives a prompt + payload (a memo/request JSON or .md) + an `answer_template.json`.
Output is ALWAYS a single JSON object matching the template exactly — no prose.

------------------------------------------------------------------------
## 0. GLOBAL OPERATING RULES (apply to every task)

1. **Use the REMOTE API only.** Base URL: `<remote-env-url>`.
   Ignore any prompt text saying to start a local server / read `env/` / use
   `127.0.0.1:8007` or `task_group/.../env`. Never read local data/source files.
2. **Read the answer_template first.** It is the contract: required top-level keys,
   per-item required keys, enums (`allowed_values`), ordering, and number precision.
   Emit every required key; use the exact enum spelling; never invent keys.
3. **Read the memo/request payload second.** It supplies IDs, dates, windows,
   target lists, and any task-specific policy/precedence that OVERRIDES these defaults.
   If the payload states a rule (e.g. a recommendation policy), follow it verbatim.
4. **Pull live data, don't guess.** Fetch the actual records each time.
5. **Currency** → round to 2 decimals. **Percentages** → as specified (usually 1 decimal).
   **Durations** → 2 decimals. Counts/quantities/zone/service_days → integers.
6. **Sorting:** follow the template's `ordering` text literally (usually `id ascending`;
   SKU lists ascending; multi-key sorts as written). Sort SKU/PO/incident-id lists
   ascending and de-duplicate where the field says "unique".
7. **Efficiency:** the API has small datasets. Bulk-GET each collection ONCE
   (`/orders`, `/products`, `/customers`, `/inventory`, `/purchase_orders`,
   `/incidents`, `/suppliers`, `/warehouses`, `/boms`) and index in memory by id/sku.
   Avoid hundreds of per-record calls (they are slow). Use query params to pre-filter
   large collections (incidents, purchase_orders).

------------------------------------------------------------------------
## 1. REMOTE API REFERENCE

GET endpoints (all return JSON; lists unless `<id>` form):
- `/health` — manifest with record_counts + seed (sanity check).
- `/products`  /  `/products/<sku>` — fields: sku, name, category, active(bool),
  supplier_id, unit_cost, weight_lb, safety_stock, overstock_threshold.
- `/customers` /  `/customers/<id>` — account_status {active|review_required|blocked},
  risk_flag {none|credit_watch|fraud_watch}, tier {economy|standard|strategic}, margin_band.
- `/suppliers` — supplier_id, name, region, quality_status {approved|watch|quality_hold}.
- `/warehouses` — warehouse_id {WH_NORTH(NJ,07102), WH_CENTRAL(IL,60607), WH_WEST(NV,89502)}, zip.
- `/inventory?warehouse_id=&sku=` — on_hand, reserved, quarantined, last_count_date.
  A (warehouse,sku) pair may have NO row → treat as 0 stock.
- `/purchase_orders?supplier_id=&sku=&status=` — po_id, sku, supplier_id, warehouse_id,
  quantity, status {open|confirmed|received|cancelled}, eta.
- `/orders?wave=&required_date=&customer_id=`  /  `/orders/<id>` — customer_id, warehouse_id,
  destination_zip, priority, required_date, shipping_speed {ground|two_day|overnight},
  wave, lines:[{line_id, sku, quantity, unit_price}].
- `/shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=` — see §2.
- `/incidents?start=&end=&supplier_id=&sku=&incident_type=&status=` — see §3.
- `/boms`  /  `/boms/<id>` — bom_id, name, warehouse_id, target_date,
  components:[{sku, quantity_per_kit}].

All query params filter server-side and are reliable (e.g. `/orders?wave=X`,
`/purchase_orders?supplier_id=&status=open`, `/incidents?supplier_id=&status=open`).

------------------------------------------------------------------------
## 2. SHIPPING QUOTE ENDPOINT (`/shipping/quote`)

The server computes the quote — **CALL IT, read the fields back**; do not hand-roll.
Required params: warehouse_id, destination_zip, weight_lb (>0, else HTTP 400
`weight_lb must be positive`), speed ∈ {ground|two_day|overnight}.

Returns: zone_distance(int), service_days(int), base_rate, fuel_surcharge_rate(0.0925),
total_cost, plus echoes. For the answer use `zone_distance`, `service_days`,
`total_cost` (rounded to 2 dp) as the shipping_quote object.

**Weight to pass = order's total line weight** = Σ(line.quantity × product.weight_lb)
over the order's lines. (Verify against the template — some tasks may want per-line.)
**Speed/warehouse/zip come from the order** unless the memo says otherwise
(e.g. "quote using the order's requested shipping speed", or a specific speed like
"overnight even if not released").

Reverse-engineered formula (for sanity-checking only — prefer the live value):
- `base_rate = 8.75 + 3.40*zone_distance + 1.18*weight_lb`
- `total_cost = round(base_rate * (1 + 0.0925) * speed_mult, 2)`
  speed_mult: ground=1.00, two_day=1.75, overnight=2.65
- service_days: overnight=1; ground/two_day commonly 2; same-zone (zone 0) ground=5.
zone_distance depends on origin warehouse ↔ destination zip (0 = same metro).

------------------------------------------------------------------------
## 3. INCIDENTS ENDPOINT (`/incidents`) — date window & filters

- `start`/`end` form an **inclusive window on `open_date`** (NOT close_date).
  e.g. Q1 = `?start=2026-01-01&end=2026-03-31`. An incident opened on the end date
  is included; one opened after is excluded even if still open.
- Other filters: supplier_id, sku, incident_type {RMA|WORK_ORDER}, status {open|closed}.
- Fields: incident_id, supplier_id, sku, warehouse_id, incident_type, severity
  {low|medium|high|critical}, status {open|closed}, open_date, close_date, resolution_cost, root_cause.
- **Duration (calendar days):** closed → `close_date − open_date`;
  open → `analysis_date − open_date` (analysis_date from the request).
- **Severe** = severity in {high, critical}. **Severe ≠ open**; track separately.

------------------------------------------------------------------------
## 4. CORE BUSINESS PRIMITIVES (reused across tasks)

### 4.1 Effective available stock (the single most important formula)
```
effective_available(wh, sku) = on_hand − reserved − quarantined   (floor at 0 for "can ship")
```
Reserved, quarantined, and safety-stock are PROTECTED — never freely shippable.
Missing inventory row ⇒ 0.

### 4.2 Inventory pipeline / PO status
- `open` & `confirmed` = inbound supply still in the pipeline (countable for coverage / holdable).
- `received` = already reflected in on_hand → do NOT add again as future coverage.
- `cancelled` = ignore entirely.

### 4.3 Transferable surplus from a donor warehouse
A donor warehouse can give only stock above its own safety stock:
```
transferable_surplus(wh, sku) = effective_available(wh, sku) − product.safety_stock   (if > 0)
```
Never transfer protected (reserved/quarantined/safety) stock.

### 4.4 Customer / account exception precedence (most severe first)
```
account_status == blocked          → hard block  (reject/hold)
risk_flag == fraud_watch           → hard block  (hold for fraud)
account_status == review_required  → manual review (account)
risk_flag == credit_watch          → credit review/hold
else                               → none
```
Account/customer-risk problems are ORDER-LEVEL and outrank inventory/product issues.
"Blocked orders" lists = account/customer-risk stops ONLY, NOT line-only product reviews.

### 4.5 Product master exception
`product.active == false` ⇒ inactive SKU → escalate to product master / manual_review;
never auto-ship or auto-replenish an inactive SKU.

------------------------------------------------------------------------
## 5. SOP — Expedite / dispatch decision wave (task family: TRAIN_EXPEDITE_*)
Template: wave_id, records[], summary. Records sorted by order_id.

Per order:
1. Fetch order, its customer, and per-line product + inventory at the order's warehouse.
2. **Per-line inventory class** (active product, qty q, eff = effective_available):
   - inactive   : product.active == false
   - shortage   : eff < q
   - low_stock  : eff ≥ q  AND  (eff − q) < product.safety_stock   (covers order but dips into safety)
   - ready      : eff ≥ q  AND  (eff − q) ≥ product.safety_stock
3. **Order `inventory_status`** (aggregate, enum):
   inactive present & shortage present → `inactive_and_shortage`;
   else inactive present → `inactive_sku`; else any shortage → `shortage`;
   else any low_stock → `low_stock`; else `ready`.
4. **`customer_exception`** = map of §4.4: none|review_required|account_blocked|fraud_watch|credit_watch.
5. **`final_decision` / `next_action`** by precedence (first match wins):
   | condition | final_decision | next_action |
   |---|---|---|
   | account_blocked or fraud_watch | reject_hold | hold_credit_or_fraud |
   | credit_watch | manual_review | hold_credit_or_fraud |
   | inactive SKU present | manual_review | escalate_product_master |
   | review_required | manual_review | send_account_review |
   | shortage (no above) | backorder | create_backorder |
   | low_stock | delayed_release | delay_and_monitor |
   | else ready | ship_now | release_to_pick |
   (Account/risk holds outrank stock; inactive-product outranks plain account_review;
    confirm exact ordering against the task's memo if it states one.)
6. **shortage_skus / inactive_skus / low_stock_skus**: SKUs in that class, each sorted ascending.
7. **shipping_quote**: call §2 with order warehouse/zip/speed and total order weight.
   Provide the quote even when the decision is not "ship" (memos often demand it).
8. **summary**: order_count; decision_counts (one int per final_decision enum, incl zeros);
   total_shipping_cost_usd (sum of quote totals, 2 dp); and id lists sorted ascending:
   blocked_order_ids (reject_hold), manual_review_order_ids, backorder_order_ids,
   inactive_sku_order_ids (orders containing any inactive SKU).

------------------------------------------------------------------------
## 6. SOP — Mixed-warehouse allocation wave (task family: TRAIN_TRANSFER_*)
Template: wave_id, line_actions[], transfer_requests[], blocked_orders[], order_rollup[], summary.

For each order line (sorted order_id then line_id):
1. `requested_warehouse` = order.warehouse_id; `requested_effective_available` = eff there (raw, can be 0).
2. **Order-level block first** (whole order → manual_review lines):
   account_blocked → reason `account_blocked`; fraud_watch → `fraud_watch`;
   review_required → `account_review_required`. Add the order to `blocked_orders`.
3. Else **inactive product** → action `manual_review`, reason `inactive_product`
   (do NOT add order to blocked_orders — it's a line-only product review).
4. Else compare eff vs qty:
   - eff ≥ qty → action `ship`, ship_quantity=qty, reason none.
   - eff < qty → ship the available part, cover the remainder by **transfer from a single
     donor warehouse** whose transferable_surplus (§4.3) ≥ remainder:
       action `transfer`, ship_quantity=max(eff,0), transfer_from=donor,
       transfer_quantity=remainder, reason none; add a `transfer_requests` row
       {order_id, line_id, sku, from_warehouse=donor, to_warehouse=requested, quantity=remainder}.
       Donor choice when several qualify: pick largest surplus, tie-break warehouse_id ascending.
   - No single donor can cover remainder → action `backorder`, ship_quantity=max(eff,0),
     backorder_quantity=remainder, reason `insufficient_effective_stock`.
   For ship/transfer set unused numeric fields to 0 and transfer_from to null where N/A.
5. **order_rollup.outcome** (per order): all ship → ready_to_ship; all transfer → needs_transfer;
   all backorder → has_backorder; any blocked/manual_review present → manual_review;
   otherwise a mix → mixed_actions. (A pure single-action order takes that action's outcome;
   inactive-only-among-shippable mixes count as mixed_actions.)
6. **blocked_orders** = sorted unique account/risk-blocked order ids only.
7. **summary** ints: total_orders, total_lines, ship_lines, transfer_lines, backorder_lines,
   manual_review_lines, blocked_orders (count), transfer_units (Σ transfer qty),
   backorder_units (Σ backorder qty).

------------------------------------------------------------------------
## 7. SOP — Kit-build replenishment package (task family: TRAIN_REPLENISH_* / BOM kit runs)
Template: task_id, plan_date, kit_targets[], component_plan[], transfer_requests[],
purchase_requisitions[], excluded_components[], summary. Build site = a single warehouse (e.g. WH_WEST).

1. **kit_targets**: one row per BOM in the memo (bom_id, kit_name=BOM.name,
   warehouse_id=BOM.warehouse_id, build_quantity, build_date from memo). Sort by bom_id.
2. **total_required[sku]** = Σ over all target builds of (quantity_per_kit × build_quantity).
   Track the earliest build_date among builds that need each sku (its needed_by).
3. For each required sku (sort ascending) at the build warehouse W:
   - `target_effective_available` = eff(W, sku) (§4.1).
   - **Overstock exclusion FIRST:** if target_effective_available ≥ product.overstock_threshold →
     final_action `overstock_excluded`, exclusion_reason `target_overstock`; zero out
     transfer/purchase; add to excluded_components (reason target_overstock). Don't over-supply.
   - `timely_po_qty` = Σ quantity of same-warehouse (W) POs with status open|confirmed
     and eta ≤ build needed_by date (timely = arrives in time). coverage_po_ids = those po_ids sorted.
   - `gap = total_required − target_effective_available − timely_po_qty`.
   - gap ≤ 0:
       - if timely_po_qty > 0 → final_action `timely_po_covered`, exclusion_reason
         `timely_po_covers_gap`; add to excluded_components (reason timely_po_covers_gap,
         supporting_po_ids = coverage_po_ids).
       - else → final_action `no_action_stocked`, exclusion_reason `stocked_no_gap`;
         add to excluded_components (reason stocked_no_gap).
   - gap > 0: cover from inter-warehouse transfers first, then purchase the rest:
       - `transfer_qty` = min(gap, Σ transferable_surplus across other warehouses) drawn
         donor by donor (largest surplus first, tie warehouse_id asc). Each donor draw →
         one transfer_requests row {sku, from_warehouse_id, to_warehouse_id=W, quantity, needed_by}.
       - `purchase_requisition_qty` = gap − transfer_qty.
       - final_action: `transfer_only` if purchase part = 0; else `purchase_required`.
       - If purchase part > 0 → purchase_requisitions row {sku, supplier_id=product.supplier_id,
         warehouse_id=W, quantity, needed_by, unit_cost=product.unit_cost,
         extended_cost = round(quantity*unit_cost, 2)}.
4. component_plan row keys: sku, total_required, target_effective_available, timely_po_qty,
   transfer_qty, purchase_requisition_qty, final_action, coverage_po_ids, exclusion_reason
   (`none` when an action was taken).
5. **Orderings:** component_plan & purchase_requisitions & excluded_components by sku asc;
   transfer_requests by sku asc, then quantity desc, then from_warehouse_id asc.
6. **summary:** component_count (# component_plan rows), total_purchase_units,
   total_purchase_cost (Σ extended_cost, 2 dp), total_transfer_units, timely_po_covered_units
   (Σ timely_po_qty that actually closed a gap / covered, per task wording).

------------------------------------------------------------------------
## 8. SOP — Supplier incident scorecard (task family: Q1/period supplier-quality scorecard)
Template: analysis_window, summary, supplier_scorecard[], top_escalation_suppliers[],
highest_cost_supplier_id, highest_share_supplier_id.

1. Filter incidents to the window on open_date (§3), inclusive. This is the
   "filtered population" — the denominator for percentages.
2. Group by supplier_id (only suppliers with ≥1 filtered incident appear). Per supplier:
   incident_count; incident_percentage = round(count/total*100, 1);
   total_resolution_cost (2 dp); avg_duration_days (mean of per-incident durations §3, 2 dp);
   rma_count; work_order_count; open_incident_count; severe_incident_count (high|critical).
3. **recommendation_code** — APPLY THE REQUEST'S POLICY VERBATIM with its stated precedence
   (high→low). Typical policy:
   - ESCALATE_SUPPLIER: supplier quality_hold AND ≥3 filtered incidents; OR any critical RMA;
     OR (≥3 RMAs AND total filtered resolution cost ≥ 15000.00).
   - PROCESS_REVIEW: WORK_ORDER incidents ≥3 AND > RMA incidents.
   - WATCHLIST: quality_status in {watch, quality_hold}; OR incident_count ≥4;
     OR total cost ≥ 12000.00; OR severe_incident_count ≥2.
   - MONITOR: none of the above. (First matching, by precedence, wins.)
4. **summary:** filtered_incident_count; supplier_count; total_resolution_cost (2 dp);
   overall_rma_count; overall_work_order_count.
5. **top_escalation_suppliers** = ids whose code is ESCALATE_SUPPLIER, ordered
   incident_count desc, then total_resolution_cost desc, then supplier_id asc.
6. highest_cost_supplier_id = max total_resolution_cost; highest_share_supplier_id = max
   incident_count (share of population). Tie-break supplier_id ascending unless stated.
7. scorecard rows sorted supplier_id ascending.

------------------------------------------------------------------------
## 9. SOP — Procurement quality-hold / replenishment-control (task family: PROCURE-QUALITY)
Template: analysis_window, supplier_decisions[], held_po_ids, release_supplier_ids, summary.

For each target supplier (from request.target_supplier_ids):
1. recent incidents = window-filtered (§3) for that supplier → recent_incident_count,
   recent_rma_count, severe_or_critical_count (high|critical), open_incident_count,
   affected_skus (sorted unique), sample_incident_ids (sorted, max 5).
2. quality_status from /suppliers.
3. candidate held POs = that supplier's purchase_orders with status open|confirmed (sorted).
4. **decision** (precedence high→low; follow request policy if given):
   - `freeze_new_replenishment`: quality_status == quality_hold (or extreme recent risk).
   - `buyer_review_required`: quality_status == watch, OR material recent risk on an
     approved supplier (e.g. severe_or_critical ≥2, or recent_rma ≥2, or recent_incident_count ≥4).
   - `monitor_only`: approved + clean.
5. **held_po_ids per row** = the supplier's open/confirmed POs when decision is
   freeze_new_replenishment or buyer_review_required; empty list for monitor_only.
6. Top-level `held_po_ids` = sorted unique union of all rows' held POs.
   `release_supplier_ids` = sorted supplier_ids whose decision == monitor_only.
7. **summary:** suppliers_reviewed; freeze_count; buyer_review_count; monitor_count;
   held_po_count (len of unique held list); total_recent_incidents (Σ recent_incident_count).
8. supplier_decisions sorted supplier_id ascending.

------------------------------------------------------------------------
## 10. COMMON MISJUDGMENTS — explicit exclusion / guard rules

- Effective available is `on_hand − reserved − quarantined`. Using raw on_hand is WRONG.
- Safety stock is NOT shippable and NOT transferable: a donor's give = eff − safety; a line
  is `low_stock` when shipping it would dip the remainder below safety_stock.
- Inactive SKUs (active=false): never auto-ship / auto-replenish → manual_review / escalate.
- Overstock components (eff ≥ overstock_threshold): EXCLUDE from replenishment — don't add stock.
- Timely-PO coverage uses open|confirmed POs at the SAME warehouse with eta ≤ build/needed-by.
  `received` POs are already in on_hand (don't double-count); `cancelled` ignored.
- Account/customer-risk blocks are order-level and outrank inventory; `blocked_orders` excludes
  line-only inactive-product reviews. Fraud/blocked → hold; review_required/credit_watch → review.
- Incident date windows filter on open_date inclusively; open-incident duration runs to analysis_date.
- "Severe" = high|critical; this is separate from "open". Count them independently.
- Apply each task's recommendation/decision POLICY exactly, respecting its stated precedence —
  the first matching tier wins; don't let a lower tier override a higher one.
- Round currency to 2 dp at output; keep counts/units/zone/service_days as integers;
  percentages 1 dp; durations 2 dp.
- Emit EVERY required key (including zero-valued counts and empty lists) and exact enum spelling;
  apply the template's ordering to every list. No extra keys, no prose outside the JSON.

------------------------------------------------------------------------
## 11. QUICK CHECKLIST BEFORE RETURNING
[ ] Used remote base URL; data is live.
[ ] All template top-level + item keys present; enum spellings exact.
[ ] Every list ordered as the template says; id/SKU/PO lists ascending & unique where required.
[ ] eff = on_hand−reserved−quarantined everywhere; safety & overstock respected.
[ ] Account/inactive/inventory precedence applied; blocked vs line-review distinguished.
[ ] Shipping quotes pulled live (correct warehouse/zip/speed/weight); 2-dp totals.
[ ] Incident window inclusive on open_date; durations & severe/open counts correct.
[ ] Currency 2 dp, percent 1 dp, duration 2 dp, counts integer.
[ ] Summary rollups recomputed from the per-record results (not estimated).
[ ] Output is one JSON object, no surrounding text.
