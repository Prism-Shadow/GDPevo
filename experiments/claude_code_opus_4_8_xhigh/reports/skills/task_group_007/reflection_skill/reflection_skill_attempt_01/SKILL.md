---
name: northwind-erp-ops
description: >-
  Solve Northwind Components ERP operations tasks against the shared read-only ERP API:
  expedite/dispatch queue decisions, mixed-warehouse allocation and transfer files, kit-build
  replenishment plans, supplier incident scorecards, and procurement quality / replenishment-control
  reviews. Use this skill whenever a task references the Northwind ERP, a wave of orders, an
  allocation or expedite or transfer "decision file", a BOM kit build replenishment plan, a supplier
  incident scorecard, a quality-hold/freeze review, or asks you to return JSON matching an
  answer_template.json built from /orders, /inventory, /products, /customers, /boms,
  /purchase_orders, /incidents, /suppliers, or /shipping/quote. Trigger it even when the prompt only
  hands you a memo + answer template and says "use the shared ERP API", because the business rules,
  thresholds, tie-breakers, and JSON conventions below are easy to get subtly wrong.
---

# Northwind Components ERP Operations

This skill encodes the business rules, API usage, and output conventions for the Northwind
Components ERP benchmark. The tasks vary, but they share a small set of primitives (effective
available stock, safety-stock-protected availability, account/risk gating, incident windows,
PO eligibility) and a shared JSON style (sorted lists, 2-decimal money, capped sample lists,
summary rollups). Getting the primitives exactly right is what separates a passing answer from a
near-miss, so internalize them before computing anything.

## 0. Golden rules (read first — these are the usual failure points)

1. **"Effective available" = `on_hand - reserved - quarantined`** at a specific warehouse. A
   missing inventory row means 0. This number can be reported as-is and may be negative.
2. **"Safety stock" is a protected operating buffer, not free stock.** Many decisions need a
   *safety-protected* view: `protected_available = effective_available - safety_stock`. Whether a
   task uses the raw or the safety-protected view depends on the field/decision — the per-task
   sections below tell you which. When in doubt, the field name and memo wording are the tell:
   words like "target", "operating buffer", "freely available", "without using protected stock"
   all mean *subtract safety stock*.
3. **Stock thresholds use `quantity + safety_stock`, not bare `quantity`.** A line that can be
   filled but would drop the warehouse to/below safety stock is NOT "ready". See §2.
4. **Transfer source selection is greedy by MOST protected-available stock, not alphabetical.**
   When several warehouses can source a transfer, pick the one with the largest
   `effective_available - safety_stock` first, then the next largest, until covered. Never default
   to a fixed WH_NORTH→WH_CENTRAL→WH_WEST order. This is the single most common tie-breaker error.
5. **PO eligibility = `status in {open, confirmed}`.** `received` stock is assumed already folded
   into `on_hand`; `cancelled` is dead. Filter POs to open/confirmed everywhere unless a task says
   otherwise.
6. **Sample/held list caps are real.** Lists described as "maximum 5" or "sample" are truncated to
   the first 5 by ascending id, even if more qualify (see §5 held_po_ids and incident samples).
7. **Always use the live API, base URL `http://127.0.0.1:8015`.** Ignore any other port (e.g. 8007)
   mentioned in task text or memos. Memos can be stale — reconcile every memo claim against live
   records and trust the API.
8. **JSON conventions:** sort exactly as the template says; round money to 2 decimals; keep
   integers as integers; emit empty lists `[]` (not null) when nothing qualifies; output only the
   JSON object, no prose.

## 1. API usage

Base URL: `http://127.0.0.1:8015` (read-only JSON over HTTP GET). Endpoints and the fields you'll
actually use:

- `GET /health` — record counts + `generation_timestamp` (the "as-of" date for the dataset; useful
  as a default `plan_date`/analysis anchor).
- `GET /products` / `GET /products/<sku>` — `active` (bool), `safety_stock`, `overstock_threshold`,
  `unit_cost`, `weight_lb`, `supplier_id`.
- `GET /suppliers` — `supplier_id`, `name`, `quality_status` in {approved, watch, quality_hold}.
- `GET /customers` / `GET /customers/<id>` — `account_status` (e.g. active, review_required,
  blocked), `risk_flag` (e.g. none, credit_watch, fraud_watch).
- `GET /warehouses` — warehouse master.
- `GET /inventory?warehouse_id=&sku=` — `on_hand`, `reserved`, `quarantined` per (warehouse, sku).
- `GET /purchase_orders?supplier_id=&sku=&status=` — `po_id`, `sku`, `warehouse_id`, `status`,
  `quantity`, `eta`, `supplier_id`.
- `GET /orders?wave=&required_date=&customer_id=` / `GET /orders/<id>` — `warehouse_id`,
  `customer_id`, `shipping_speed`, `destination_zip`, and `lines` (each line has `line_id`, `sku`,
  `quantity`, `unit_price`).
- `GET /boms` / `GET /boms/<id>` — `name`, `warehouse_id`, `target_date`, and `components`
  (`sku`, `quantity_per_kit`).
- `GET /incidents?start=&end=&supplier_id=&sku=&incident_type=&status=` — see §6 for date-window
  semantics. Fields: `incident_id`, `supplier_id`, `sku`, `open_date`, `close_date` (null when
  open), `status` (open/closed), `incident_type` (RMA/WORK_ORDER), `severity`
  (low/medium/high/critical), `resolution_cost`.
- `GET /shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=` — returns `zone_distance`,
  `service_days`, `total_cost`, and echoes inputs. `speed` in {ground, two_day, overnight},
  default ground.

Filters are exact string match; omitting a filter returns everything. Prefer server-side filtering
for incidents and POs, but it's fine to pull a collection once and filter in code — just match the
server's semantics (string compare for dates).

### Reconciling stale memos against live records
Memos give you the *request* (which orders/SKUs/suppliers, target quantities, dates, policy), but
their embedded data can be out of date. Pull the corresponding live records and compute from those.
If a memo's API base URL or port disagrees with §0.7, use §0.7. If a memo names a kit/BOM/supplier,
fetch it live to get the authoritative name, warehouse, components, and statuses.

## 2. Core stock classification (shared by allocation & expedite tasks)

For an order line at the order's warehouse, with `eff = effective_available`, `q = line.quantity`,
`ss = product.safety_stock`:

- **shortage** when `eff < q + ss`. Rationale: a line is only safely fulfillable if filling it
  still leaves safety stock intact. This catches both "can't even fill" (`eff < q`) and "fills but
  breaches the buffer" cases. Do NOT use the naive `eff < q` test — it under-reports shortages.
- **low_stock** when it is NOT a shortage but serving the *whole wave's* demand for that
  (warehouse, sku) would drop the warehouse to/below safety:
  `eff - wave_demand(warehouse, sku) < ss`, where `wave_demand` is the summed quantity of that SKU
  across **every order in the wave** at that warehouse. A SKU can be low_stock in one order purely
  because *other* orders in the wave also draw it down. Compute `wave_demand` once per
  (warehouse, sku) up front.
- **ready** otherwise.
- **inactive** is an independent flag: `product.active == false`. A line can be both inactive and a
  shortage.

These per-line tags feed the per-SKU exception lists (`shortage_skus`, `low_stock_skus`,
`inactive_skus`) — and crucially, **report all applicable tags even when the order-level status is
driven by something else.** A shortage order can still carry low_stock SKUs; list them. (Missing
low_stock SKUs on shortage orders is a classic error.)

**Order-level `inventory_status` precedence:** combine an order's line tags into one status by:
`inactive_and_shortage` (has ≥1 inactive line AND ≥1 shortage line) > `inactive_sku` (inactive but
no shortage) > `shortage` > `low_stock` > `ready`.

## 3. Account / risk gating (shared by allocation & expedite tasks)

Customer account state and risk flags gate fulfillment **before** inventory is considered. Evaluate
gates in this precedence (first match wins):

1. `account_status == blocked` → blocked.
2. `risk_flag == fraud_watch` → fraud watch.
3. `risk_flag == credit_watch` → credit watch.
4. `account_status == review_required` → review required.
5. otherwise no account exception.

How these map to decisions/reasons is task-specific (see §4 and §7), but the precedence above is
stable. An order stopped at the account/customer-risk level (blocked / fraud_watch / credit_watch /
review_required) is an "account-level" stop; a stop caused only by an inactive product is a
*line-level* product review and is NOT an account-level block — keep that distinction when building
`blocked_orders` lists.

## 4. SOPs by task type

The full field-by-field recipes live in `references/task_playbooks.md`. Read it when you've
identified the task type. Quick index:

- **Expedite / dispatch queue** (memo lists order_ids; output per-order inventory_status,
  customer_exception, final_decision, next_action, SKU exception lists, shipping_quote, summary):
  §"Expedite queue" in the playbook. Key logic: §2 + §3, account gate beats inventory, then map
  status→decision; shipping quote from `/shipping/quote` taken verbatim.
- **Mixed-warehouse allocation / transfer file** (wave of orders, line-level
  ship/transfer/backorder/manual_review): §"Allocation" in the playbook. Uses the
  **safety-protected** effective available as `requested_effective_available` and for transfer
  sourcing.
- **Kit-build replenishment plan** (BOMs + build quantities → component plan, transfers, purchase
  requisitions, exclusions): §"Replenishment plan" in the playbook. Uses
  `target_effective_available = eff - safety_stock` and `gap = total_required -
  target_effective_available`.
- **Supplier incident scorecard** (Q1-style window → per-supplier counts, %, costs, durations,
  recommendation codes): §"Incident scorecard" in the playbook.
- **Procurement quality / replenishment-control review** (target suppliers → freeze / buyer_review /
  monitor + held POs): §"Quality control review" in the playbook.

If you can't tell which type it is, match on the answer_template's top-level keys and the memo's
`decision_choices` / enum fields — those name the task.

## 5. Purchase orders, transfers, and held lists

- **PO eligibility:** open/confirmed only (§0.5). For "timely" coverage of a future build, also
  require same destination warehouse and `eta <= needed_by`.
- **Transfer sourcing:** cover the remaining gap from other warehouses, taking from the source with
  the greatest `effective_available - safety_stock` first, then the next, never exceeding a source's
  protected availability (protect each source's own safety stock). Split across multiple sources
  when one isn't enough *unless the task explicitly says choose a single source* (allocation tasks
  often say "choose one source warehouse" — then pick the single best source and if it alone can't
  cover, backorder).
- **Held PO lists with a cap:** when a task holds a supplier's POs and the field is described as a
  sample / "maximum N", hold the **first N open/confirmed POs by `po_id` ascending** — not all of
  them, and not SKU-filtered. (In the observed environment N was 5 and the cap matched the sample
  incident-id cap. Treat any "maximum 5"/"sample" wording as the same first-N-by-id rule.)

## 6. Incident date-window semantics

`/incidents?start=&end=` filters on **`open_date`**, inclusive, by **ISO-string comparison**. So
`start=2026-01-01&end=2026-03-31` keeps incidents whose `open_date` is in that closed interval.
This is the population for scorecards and quality reviews — apply the same window when counting
incidents, RMAs, severe counts, costs, etc.

- **Open vs closed:** `status == open` ⇔ `close_date` is null.
- **Duration:** closed incident = calendar days `open_date → close_date`; open incident = calendar
  days `open_date → analysis_date`. Use the *actual* `close_date` even if it falls after the
  analysis date (do not cap it) unless a task says otherwise.
- **Severe** = `severity in {high, critical}` (this is "severe_or_critical").
- **Costs and durations include open incidents** (they still carry a `resolution_cost`).
- A supplier's `affected_skus` over a window = the sorted unique SKUs of its filtered incidents.

## 7. Decision policies (validated defaults)

When a task supplies an explicit `recommendation_policy` / precedence in its payload, follow it
literally and in the given precedence order. When a task only gives you the set of allowed decisions
(no thresholds), use these validated defaults — confirmed against live data:

### Quality / replenishment-control (freeze / buyer_review / monitor)
Evaluate in precedence order; first match wins:

1. **freeze_new_replenishment** — supplier `quality_status == quality_hold`.
2. **buyer_review_required** — supplier `quality_status == watch` AND `severe_or_critical_count >= 2`
   in the window.
3. **monitor_only** — otherwise (includes a `watch` supplier with `< 2` severe incidents).

Notes that matter:
- A single critical incident does **not** by itself force a freeze; status drives the freeze.
- **Both** freeze and buyer_review *hold POs* (the first 5 open/confirmed by po_id, §5). Only
  `monitor_only` holds none. `release_supplier_ids` = the suppliers whose decision is
  `monitor_only`.

### Expedite final_decision / next_action (when not otherwise specified)
Account/risk gate first (§3), then inventory:
`account_blocked → reject_hold / hold_credit_or_fraud`;
`fraud_watch → reject_hold / hold_credit_or_fraud`;
`credit_watch → manual_review / hold_credit_or_fraud`;
`review_required → manual_review / send_account_review`;
then (no account issue) inventory: `inactive → manual_review / escalate_product_master`;
`shortage → backorder / create_backorder`;
`low_stock → delayed_release / delay_and_monitor`;
`ready → ship_now / release_to_pick`.
Note: when an order has BOTH an account/review exception and inventory issues, the account
disposition drives `final_decision`/`next_action`, but the SKU exception lists still report the
inventory facts.

## 8. Output conventions checklist (run before returning)

- Top-level keys exactly match the template; values like a fixed `wave_id`/`task_id` are set to the
  required literal.
- Every list sorted as specified (often by id ascending; transfer lists may have multi-key sorts
  like sku asc, then quantity desc, then warehouse asc — follow the template's exact wording).
- Money fields rounded to 2 decimals; per-line costs rounded before summing into totals where the
  template implies it; integer fields are integers.
- Exception/id lists are sorted, de-duplicated where the template says "unique", and `[]` when empty.
- Summary rollups (counts, totals, id lists) are internally consistent with the per-record rows
  (recount from the rows you actually emitted; don't hand-maintain a separate tally).
- Output is a single JSON object and nothing else.

See `references/task_playbooks.md` for the detailed, field-by-field SOP for each task type and the
specific pitfalls the playbook calls out.
