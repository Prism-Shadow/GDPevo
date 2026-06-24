# SKILL: Northwind Components ERP Decision Tasks

Reusable workflow for the Northwind Components inventory / order-fulfillment
domain. These tasks give you a memo + an `answer_template.json`, and ask you to
query the shared ERP API, apply business rules, and emit one JSON object that
matches the template exactly. Rules below were verified/refined against task
feedback during training.

---

## 1. ENVIRONMENT / API USAGE

Base URL is provided by the runner (a remote host). Ignore any prompt text that
tells you to "start a local environment" or use `127.0.0.1:8007` or read an
`env/` directory — always use the runner-provided base URL and the public HTTP
API only. Never read env source, data files, or gold answers.

GET endpoints (all return JSON):
- `/health` — manifest with record counts (sanity check; confirms dataset).
- `/products` , `/products/<sku>` — product master.
- `/customers` , `/customers/<customer_id>`.
- `/suppliers` — list (no per-id route needed; small set).
- `/warehouses` — id, name, region, zip. Three warehouses:
  WH_NORTH (07102), WH_CENTRAL (60607), WH_WEST (89502).
- `/inventory?warehouse_id=&sku=` — returns a LIST (filter by either/both).
  Omit `warehouse_id` to get one row per warehouse for a SKU (needed for
  transfer sourcing).
- `/purchase_orders?supplier_id=&sku=&status=`.
- `/orders?wave=&required_date=&customer_id=` , `/orders/<order_id>`.
- `/shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=`
  (speed in `ground|two_day|overnight`).
- `/incidents?start=&end=&supplier_id=&sku=&incident_type=&status=`
  — the date window applies to `open_date` (inclusive on both ends).
- `/boms` , `/boms/<bom_id>`.

Practical fetching notes:
- Use `curl` (reliable, ~1s/call). If you script in Python, set an explicit
  per-request timeout — bare `urllib` with no timeout can hang indefinitely.
- Cache per-URL results in memory; many tasks request the same product /
  inventory repeatedly.
- An inactive or missing SKU's `/products/<sku>` may 404 — handle gracefully.
- The shipping quote endpoint COMPUTES `total_cost` from the `weight_lb` you
  pass. `total_cost ≈ base_rate * (1 + fuel_surcharge_rate)`, and `base_rate`
  scales (almost) linearly with weight. So the weight you send is load-bearing —
  send the exact intended weight at full precision, then round the returned
  `total_cost` to 2 decimals. `zone_distance` and `service_days` come straight
  from the response (do not recompute).

Record shapes you will use constantly:
- product: `{sku, name, active(bool), category, supplier_id, unit_cost,
  weight_lb, safety_stock, overstock_threshold}`.
- inventory row: `{warehouse_id, sku, on_hand, reserved, quarantined,
  last_count_date}`.
- customer: `{customer_id, name, tier, margin_band, account_status, risk_flag}`.
  - `account_status` in {active, review_required, blocked}.
  - `risk_flag` in {none, credit_watch, fraud_watch}.
- supplier: `{supplier_id, name, region, quality_status}` with
  `quality_status` in {approved, watch, quality_hold}.
- order: `{order_id, wave, customer_id, warehouse_id, destination_zip,
  priority, required_date, shipping_speed, lines:[{line_id, sku, quantity,
  unit_price}]}`.
- PO: `{po_id, sku, supplier_id, warehouse_id, quantity, status, eta}` with
  `status` in {open, confirmed, received, cancelled}.
- incident: `{incident_id, supplier_id, sku, warehouse_id, incident_type
  (RMA|WORK_ORDER), severity (low|medium|high|critical), status (open|closed),
  open_date, close_date, resolution_cost, root_cause}`.
- BOM: `{bom_id, name, warehouse_id, target_date, components:[{sku,
  quantity_per_kit}]}`.

---

## 2. THE CORE INVENTORY RULE (USED IN MULTIPLE TASKS)

**Effective (freely usable) available stock** at a warehouse:

```
effective_available = on_hand - reserved - quarantined - safety_stock
```

Reserved, quarantined, AND the safety-stock buffer ("normal operating buffer")
are all PROTECTED and must NOT be counted as available for new demand. This
4-term formula was verified correct (it produced perfect scores on the
allocation and replenishment tasks).

Critical detail: **DO NOT clamp `effective_available` to zero.** Keep it raw,
including negative values (e.g. `on_hand 1, reserved 0, quarantined 0,
safety 52` → `-51`). The reported "effective available" field and any gap math
(`gap = required - effective_available`) depend on the negative value. Clamping
to 0 understated gaps and cost score.

Caveat for the "expedite queue" style task (Section 6): that task has a separate
`low_stock` vs `shortage` distinction and a standalone `safety_stock` concept,
so there `shortage` is judged on `on_hand - reserved - quarantined` versus the
order quantity; treat safety stock only as the low-stock threshold there. Use
the full 4-term protected formula for ALLOCATION and REPLENISHMENT tasks.

For transfer sourcing, a donor warehouse's lendable quantity is its own
`effective_available` (same 4-term formula) — never lend protected stock.

---

## 3. CUSTOMER / ACCOUNT GATING (release decisions)

Precedence for customer-driven holds (highest first):
1. `account_status == blocked`            → account-level block.
2. `risk_flag == fraud_watch`             → account-level block.
3. `risk_flag == credit_watch`            → credit hold (account-level).
4. `account_status == review_required`    → account-level review.
5. otherwise                              → none.

Account/risk holds (blocked, fraud_watch, review_required, and credit_watch)
stop the order at the ACCOUNT level → these orders go on the "blocked orders"
list and their lines become `manual_review`.

Product-master problems are LINE-ONLY, NOT account blocks:
- `product.active == false` → that line is `manual_review` with reason
  `inactive_product`, but the ORDER is NOT added to blocked_orders (unless it
  also has an account/risk hold). An order with one inactive line and other
  normal lines is `mixed_actions`, not blocked.

---

## 4. ALLOCATION / TRANSFER TASK SOP (verified 1.0)

Goal: classify every order line in a wave as `ship | transfer | backorder |
manual_review`, emit transfer requests, blocked orders, per-order rollup, and a
summary.

Per line:
1. Resolve customer gating (Section 3). If an account/risk hold applies →
   `action = manual_review`, `ship_quantity = 0`, `transfer_quantity = 0`,
   `backorder_quantity = 0`, `primary_reason` = the matching reason
   (`account_blocked | fraud_watch | account_review_required`). Add the order to
   `blocked_orders`.
2. Else if product inactive → `manual_review`, reason `inactive_product`
   (line only; order NOT blocked).
3. Else compute `req_ea = effective_available(requested_warehouse)` (raw, may be
   negative):
   - `req_ea >= qty` → `ship`, ship_quantity = qty, reason `none`.
   - else `ship_part = max(req_ea, 0)`, `remaining = qty - ship_part`:
     - Find ONE other warehouse whose own effective_available `>= remaining`
       (prefer the largest such donor; tie-break by warehouse_id ascending).
       If found → `transfer`: `ship_quantity = ship_part`,
       `transfer_from = donor`, `transfer_quantity = remaining`,
       reason `insufficient_effective_stock`. Emit a transfer_request row.
     - else → `backorder`: `ship_quantity = ship_part`,
       `backorder_quantity = remaining`, reason `insufficient_effective_stock`.
   - Choose a SINGLE source warehouse for a transfer line; leave any usable
     requested-warehouse quantity as `ship_quantity`.

`primary_reason` enum: `none | account_blocked | account_review_required |
fraud_watch | inactive_product | insufficient_effective_stock`.

Order rollup outcome enum: `ready_to_ship | needs_transfer | has_backorder |
manual_review | mixed_actions`:
- all lines ship → `ready_to_ship`.
- all lines manual_review → `manual_review`.
- any manual_review mixed with other actions → `mixed_actions`.
- only ship/transfer (≥1 transfer) → `needs_transfer`.
- any backorder (no manual_review) → `has_backorder`.

Summary integer keys: total_orders, total_lines, ship_lines, transfer_lines,
backorder_lines, manual_review_lines, blocked_orders (count), transfer_units,
backorder_units.

Ordering: `line_actions` and `transfer_requests` sorted by order_id asc then
line_id asc; `blocked_orders` and `order_rollup` sorted by order_id asc.

---

## 5. KIT REPLENISHMENT TASK SOP (verified ~0.83)

Goal: for BOM builds at a planning warehouse, produce per-component coverage,
transfer requests, purchase requisitions, exclusions, and totals.

1. `total_required[sku] = Σ over builds (build_quantity * quantity_per_kit)`.
   A SKU appearing in multiple BOMs sums across them.
2. `target_effective_available` = effective_available at the planning warehouse
   (4-term formula, RAW / may be negative). This is the reported field.
3. `gap = total_required - target_effective_available`.
4. `timely_po_qty` = sum of quantities of purchase orders that are
   **same planning warehouse**, status `open` or `confirmed`, AND
   `eta <= needed_by` (the component's earliest required build date). POs that
   are `received`, `cancelled`, at another warehouse, or arriving after the
   build date are NOT timely. `coverage_po_ids` = sorted ids of those timely POs.
5. Decision cascade per component (`final_action` / `exclusion_reason`):
   - `gap <= 0` and `target_effective_available >= overstock_threshold`
        → `overstock_excluded` / `target_overstock`.
   - `gap <= 0` (otherwise) → `no_action_stocked` / `stocked_no_gap`.
   - `target_effective_available >= overstock_threshold` (gap>0)
        → `overstock_excluded` / `target_overstock` (do not add to an
          already-overstocked SKU).
   - `timely_po_qty >= gap` → `timely_po_covered` / `timely_po_covers_gap`.
   - else cover `gap - timely_po_qty` first by TRANSFERS from other warehouses'
     effective_available (largest donor first, tie by warehouse_id asc):
       - fully covered by transfers → `transfer_only` / reason `none`.
       - residual remains → `purchase_required` / reason `none`, and create a
         purchase requisition for the residual quantity.
6. Purchase requisition: `supplier_id` from product master, `warehouse_id` =
   planning warehouse, `quantity` = residual, `needed_by` = component build date,
   `unit_cost` = product.unit_cost (2 dp), `extended_cost = unit_cost*quantity`
   (2 dp).
7. `excluded_components` list contains every component whose `exclusion_reason`
   is not `none` (`target_overstock | timely_po_covers_gap | stocked_no_gap`),
   with `supporting_po_ids` = the timely PO ids for `timely_po_covers_gap`,
   else `[]`.

Summary:
- `component_count` = number of components.
- `total_purchase_units` = Σ requisition quantities.
- `total_purchase_cost` = Σ extended_cost (2 dp).
- `total_transfer_units` = Σ transfer quantities.
- `timely_po_covered_units` = Σ of the **gap covered by timely POs** for
  `timely_po_covered` components — i.e. the gap amount, NOT the full PO quantity.
  (Reporting full PO qty here cost score; report `min(gap, timely_po_qty)` = the
  gap.)

Ordering: `component_plan`, `purchase_requisitions`, `excluded_components`
sorted by sku asc. `transfer_requests` sorted by sku asc, then quantity desc,
then from_warehouse_id asc. `kit_targets` sorted by bom_id asc.

Open question (lower confidence): when a component has no gap AND is at/above
overstock_threshold, whether the label should be `overstock_excluded` vs
`no_action_stocked` — prefer `overstock_excluded` when
`effective_available >= overstock_threshold` since that condition is literally
true.

---

## 6. EXPEDITE-QUEUE / DISPATCH-CONTROL TASK SOP (partial)

Goal: per order, report `inventory_status`, `customer_exception`,
`final_decision`, `next_action`, the three SKU exception lists, and a shipping
quote; plus a wave summary.

Per-line inventory classification (this task tracks safety stock separately):
- `available = on_hand - reserved - quarantined` (do NOT subtract safety here).
- `inactive` line: product.active == false.
- `shortage` line: `available < quantity`.
- `low_stock` line: can fulfill but the buffer is breached (available below /
  dropping below safety_stock).

Order-level `inventory_status` enum (priority high→low):
`inactive_and_shortage` (has both) > `inactive_sku` > `shortage` >
`low_stock` > `ready`.

`customer_exception` enum mirrors Section 3:
`account_blocked | fraud_watch | credit_watch | review_required | none`.

`final_decision` enum {ship_now, delayed_release, manual_review, backorder,
reject_hold} paired with `next_action` {release_to_pick, delay_and_monitor,
send_account_review, create_backorder, hold_credit_or_fraud,
escalate_product_master}. Natural pairings:
- account_blocked/fraud_watch/credit_watch → reject_hold / hold_credit_or_fraud.
- review_required → manual_review / send_account_review.
- inactive SKU → manual_review / escalate_product_master.
- shortage → backorder / create_backorder.
- low_stock → delayed_release / delay_and_monitor.
- clean & ready → ship_now / release_to_pick.

Shipping quote: speed = the ORDER's `shipping_speed` (memo may explicitly say
"use the order's requested shipping speed"; quotes are required even when the
queue decision is not "release"). weight = Σ(product.weight_lb * quantity) over
all lines. Report `zone_distance`, `service_days` from the response and
`total_cost_usd` = round(total_cost, 2).

Summary: `order_count`, `decision_counts` (one integer per decision enum value),
`total_shipping_cost_usd` (2 dp), and id lists `blocked_order_ids` (reject_hold),
`manual_review_order_ids`, `backorder_order_ids`, `inactive_sku_order_ids` — all
sorted ascending. Records sorted by order_id asc; SKU lists sorted asc.

CAUTION (unresolved): this task scored low in training and was insensitive to
decision-precedence changes, meaning the dominant error was in the per-line
classification and/or shipping-cost basis rather than the decision mapping.
When you face this task, treat the available-stock formula and the shipping
WEIGHT basis as the highest-risk fields: double-check whether quarantine should
be subtracted and whether weight is the full Σ(weight_lb*qty). The precedence
ordering above is plausible but the score was driven by the numeric fields.

---

## 7. SUPPLIER INCIDENT SCORECARD SOP (verified 1.0)

Filter incidents by `open_date` within the requested window (the `/incidents`
`start`/`end` params do this, inclusive both ends). Group by supplier.

Per supplier row:
- `incident_count`.
- `incident_percentage` = count / (total filtered incidents) * 100, rounded to
  the requested precision (commonly 1 decimal). Denominator = the WHOLE filtered
  population, not per-type.
- `total_resolution_cost` = Σ resolution_cost (2 dp).
- `avg_duration_days` (2 dp). Duration per incident:
  - closed: `close_date - open_date` in calendar days.
  - open:   `analysis_date - open_date` in calendar days.
- `rma_count` (incident_type RMA), `work_order_count` (WORK_ORDER).
- `open_incident_count` (status open).
- `severe_incident_count` = severity in {high, critical}.
- `recommendation_code` via the task's recommendation policy. Apply codes in the
  stated PRECEDENCE order (first match wins), e.g. a typical policy:
  - `ESCALATE_SUPPLIER`: quality_hold with ≥3 filtered incidents, OR any
    critical RMA (incident_type RMA and severity critical), OR ≥3 RMAs with
    ≥ a cost threshold.
  - `PROCESS_REVIEW`: WORK_ORDER count ≥3 AND greater than RMA count.
  - `WATCHLIST`: quality_status in {watch, quality_hold}, OR incident_count ≥4,
    OR total cost ≥ a threshold, OR severe_incident_count ≥2.
  - `MONITOR`: none of the above.
  Always read the exact thresholds and precedence from the task payload — they
  are spelled out and must be applied literally.

Derived outputs:
- `top_escalation_suppliers` = supplier_ids whose code is ESCALATE_SUPPLIER,
  ordered by incident_count desc, then total_resolution_cost desc, then
  supplier_id asc.
- `highest_cost_supplier_id` = supplier with max total_resolution_cost
  (tie-break supplier_id asc).
- `highest_share_supplier_id` = supplier with max incident_count
  (tie-break supplier_id asc).
- summary: filtered_incident_count, supplier_count (suppliers with ≥1 incident),
  total_resolution_cost (2 dp), overall_rma_count, overall_work_order_count.

Rows sorted by supplier_id asc.

---

## 8. SUPPLIER REPLENISHMENT-CONTROL SOP (partial)

For each target supplier over an analysis window, compute the same incident
stats as Section 7 (filtered on `open_date` in the window):
`recent_incident_count`, `recent_rma_count`, `severe_or_critical_count`
(high|critical), `open_incident_count`, `affected_skus` (sorted unique),
`sample_incident_ids` (sorted, max 5). Compute these EXACTLY — they are the bulk
of the score and must match the raw filtered population precisely. Verify your
window endpoints and that you filter on `open_date`.

`held_po_ids` per supplier = that supplier's `open`/`confirmed` POs that are
held because of the control decision. Top-level `held_po_ids` = sorted union;
`release_supplier_ids` = suppliers whose decision is `monitor_only`.

Decision enum {freeze_new_replenishment, buyer_review_required, monitor_only}.
Lower-confidence policy (no fully-specified rule was given in training; reason
from quality_status + active/open risk):
- `freeze_new_replenishment`: supplier on `quality_hold` (strongest control).
- `buyer_review_required`: `watch` status, or unresolved/open incidents, or a
  critical incident on an otherwise-OK supplier.
- `monitor_only`: approved with no active risk.
Held POs follow the decision: freeze and buyer_review suppliers' open/confirmed
POs are held; monitor_only suppliers are released. If a task payload spells out a
decision policy, apply it literally instead of the heuristic above.

Summary: suppliers_reviewed, freeze_count, buyer_review_count, monitor_count,
held_po_count, total_recent_incidents.

---

## 9. OUTPUT / FORMATTING CONVENTIONS (ALL TASKS)

- Return ONLY the JSON object that matches `answer_template.json`. No prose.
- Include EVERY `required_top_level_key` and every `item_required_keys` field,
  even when empty (`[]`, `0`, `"none"`, or `null` per the template's enum).
- Respect each field's declared type: integer fields must be ints (not floats),
  enum fields must use an allowed value verbatim, currency fields are numbers
  rounded to 2 decimals.
- Set required constant fields exactly (e.g. `wave_id`, `task_id`,
  `required_value`).
- Apply the template's declared sort order to every list (commonly ascending by
  id/sku; some lists have multi-key orders — follow them precisely).
- SKU/id sub-lists are sorted ascending and de-duplicated.
- `effective_available`-style fields are reported RAW (can be negative); do not
  clamp unless the template says otherwise.
- Currency rounding is the LAST step (round each line, and round summary totals
  from the rounded/exact components consistently to 2 dp).
- Quote `total_cost` is rounded to 2 dp; `zone_distance` and `service_days` come
  from the quote response unchanged.

---

## 10. COMMON MISJUDGMENTS THAT COST SCORE

- Clamping effective availability to 0 instead of keeping negative values
  (breaks gap math and the reported field).
- Forgetting to subtract `safety_stock` (the "normal operating buffer") from
  available stock in allocation/replenishment tasks.
- Counting `received`/`cancelled` POs, other-warehouse POs, or late-ETA POs as
  "timely" coverage. Timely = same warehouse, open/confirmed, eta ≤ needed_by.
- Reporting full PO quantity for "covered units" instead of the gap actually
  covered.
- Treating an inactive-product line as an account block (it is line-only;
  it does NOT put the order on the blocked list).
- Splitting a transfer across multiple source warehouses when the task wants a
  single source per line.
- Wrong incident date semantics: the window applies to `open_date`, inclusive;
  open incidents' duration runs to the analysis_date, closed incidents'
  duration runs to close_date.
- Misordering recommendation precedence (first matching tier wins) or using the
  wrong percentage denominator (use the whole filtered population).
- Sending the wrong weight or speed to the shipping quote (use the order's
  shipping_speed and the full Σ(weight_lb*qty)); recomputing zone/service_days
  instead of taking them from the response.
- Emitting floats where integers are required, or skipping required keys with
  empty values.
