# Northwind Components ERP Skill — Task Group 007

## Overview
Tasks in this group involve querying a shared Northwind ERP API (`http://127.0.0.1:8007`) and producing strictly-structured JSON outputs. There are four main task families:
1. **Expedite queue decisions** — per-order release/hold/backorder/review decisions.
2. **Allocation / transfer desk** — per-line warehouse action (ship, transfer, backorder, manual_review).
3. **Kit replenishment / production planning** — BOM component coverage with POs, transfers, and purchase requisitions.
4. **Supplier quality / procurement control** — incident scorecards and freeze/buyer-review decisions.

## Environment & API Setup
- Start the API with `bash setup.sh start` or `python server.py --host 127.0.0.1 --port 8007`.
- Base URL: `http://127.0.0.1:8007`
- Query live endpoints; never rely on cached snapshots. Relevant endpoints include `/orders`, `/products`, `/customers`, `/inventory`, `/warehouses`, `/shipping_quotes`, `/boms`, `/purchase_orders`, `/incidents`, `/suppliers`.

## Universal Sorting Rules
Apply ascending sort unless the task template specifies otherwise:
- **Order IDs**: `SO-70000` style — sort ascending lexicographically.
- **SKU strings**: `NW-1000` style — sort ascending.
- **Supplier IDs**: `SUP-001` style — sort ascending.
- **PO IDs**: `PO-50001` style — sort ascending.
- **Incident IDs**: `INC-90001` style — sort ascending.
- **Line-level lists**: sort by `order_id` ascending, then `line_id` ascending.
- **Transfer-request tie-breaking** (kit planning): sort by `sku` ascending, then `quantity` descending, then `from_warehouse_id` ascending.

## Rounding & Precision
- **Currency (USD)**: round to exactly 2 decimal places in all fields named `*_cost_usd`, `total_cost_usd`, `unit_cost`, `extended_cost`.
- **Percentages**: round to 1 decimal place.
- **Durations (days)**: round to 2 decimal places.
- **Quantities**: integers, no rounding needed.

## Controlled Vocabularies
Learn the exact enums allowed by each template. Common ones across tasks:

### Inventory Status (expedite tasks)
`ready`, `low_stock`, `shortage`, `inactive_sku`, `inactive_and_shortage`

### Customer Exception (expedite tasks)
`none`, `review_required`, `account_blocked`, `fraud_watch`, `credit_watch`

### Final Decision (expedite tasks)
`ship_now`, `delayed_release`, `manual_review`, `backorder`, `reject_hold`

### Next Action (expedite tasks)
`release_to_pick`, `delay_and_monitor`, `send_account_review`, `create_backorder`, `hold_credit_or_fraud`, `escalate_product_master`

### Allocation Line Actions
`ship`, `transfer`, `backorder`, `manual_review`

### Allocation Primary Reasons
`none`, `account_blocked`, `account_review_required`, `fraud_watch`, `inactive_product`, `insufficient_effective_stock`

### Kit Component Final Actions
`no_action_stocked`, `transfer_only`, `purchase_required`, `timely_po_covered`, `overstock_excluded`

### Exclusion Reasons (kit planning)
`none`, `target_overstock`, `timely_po_covers_gap`, `stocked_no_gap`

### Supplier Recommendation Codes (scorecards)
`ESCALATE_SUPPLIER`, `PROCESS_REVIEW`, `WATCHLIST`, `MONITOR` — evaluated in that precedence order.

### Procurement Decisions
`freeze_new_replenishment`, `buyer_review_required`, `monitor_only`

### Supplier Quality Status
`approved`, `watch`, `quality_hold`

## Inventory & Availability Rules
- **Effective available** for a warehouse = on-hand minus reserved, quarantined, and normal operating buffer quantities. Do not treat protected stock as freely available.
- In allocation tasks, if the requested warehouse cannot fully cover a line but another warehouse has sufficient effective stock without dipping into protected stock, the action is `transfer` (not `backorder`).
- In kit planning, compute `target_effective_available` = current effective available − total required for the build.
- An SKU is **inactive** when the product master status is inactive/discontinued.

## Order & Account Rules
- Account flags (`account_blocked`, `review_required`, `fraud_watch`, `credit_watch`) on a customer override inventory decisions and force `manual_review` or `reject_hold` at the order level.
- If any line forces `manual_review` because of account risk, the whole order is typically blocked or rolled up to `manual_review`.
- Inactive product master on a line forces `manual_review` with reason `inactive_product`.

## Shipping Quotes
- Requested via the API per order (or per order + speed). Return fields: `zone_distance` (int), `service_days` (int), `total_cost_usd` (number, 2 decimals).
- Even if the order decision is not release, the memo may still require a quote.

## Kit Replenishment Logic
1. Compute `total_required` = BOM qty per unit × build_quantity, summed across all target builds.
2. Check **timely POs**: open or confirmed purchase orders for the same warehouse that arrive before the build date. Their quantities can cover the gap.
3. Check **inter-warehouse transfers**: other warehouses with surplus effective stock. Prefer feasible transfers before raising purchase requisitions.
4. **Final action**:
   - If `target_effective_available` ≥ 0 and no gap exists → `overstock_excluded` or `no_action_stocked`.
   - If timely PO covers the gap → `timely_po_covered`.
   - If transfer covers the gap → `transfer_only`.
   - Else → `purchase_required` for remaining gap.
5. **Excluded components** list gets its own section with reason and supporting PO IDs.
6. **Purchase requisitions** require `supplier_id`, `warehouse_id`, `quantity`, `needed_by`, `unit_cost`, `extended_cost` (qty × unit_cost, rounded to 2 decimals).

## Supplier Scorecard & Quality Rules
1. **Filter incidents** by `open_date` within the requested window (inclusive).
2. **Duration**:
   - Closed incidents: calendar days from `open_date` to `close_date`.
   - Open incidents: calendar days from `open_date` to `analysis_date`.
3. **Incident percentage** = supplier incident count ÷ total filtered incident count × 100, rounded to 1 decimal.
4. **Severe incidents**: severity in `high` or `critical`.
5. **Recommendation precedence** (evaluate in order; first match wins):
   - **ESCALATE_SUPPLIER**: supplier on `quality_hold` with ≥3 filtered incidents, OR any critical RMA, OR ≥3 RMAs and ≥15,000 total resolution cost.
   - **PROCESS_REVIEW**: WORK_ORDER incidents ≥3 and exceed RMA incidents.
   - **WATCHLIST**: quality status is `watch` or `quality_hold`, OR incident count ≥4, OR total resolution cost ≥12,000, OR severe incident count ≥2.
   - **MONITOR**: default.
6. **Top escalation suppliers**: only those with `ESCALATE_SUPPLIER`, sorted by incident count descending, then total resolution cost descending, then supplier_id ascending.
7. **Highest cost supplier**: supplier with greatest total resolution cost.
8. **Highest share supplier**: supplier with greatest incident percentage.

## Procurement Control Desk Logic
1. Review target suppliers for recent incidents in the analysis window.
2. Collect open/confirmed PO IDs for each supplier.
3. Decision mapping:
   - `freeze_new_replenishment` for serious risk (e.g., `quality_hold` with multiple incidents).
   - `buyer_review_required` for moderate risk (e.g., `watch` status with incidents).
   - `monitor_only` when risk is acceptable.
4. `held_po_ids` in output = sorted unique union of all PO IDs from suppliers not released (`monitor_only`).
5. `release_supplier_ids` = sorted list of suppliers whose decision is `monitor_only`.
6. `sample_incident_ids` = up to 5 most representative incident IDs, sorted ascending.
7. `affected_skus` = sorted unique SKUs from filtered incidents.

## JSON Output Discipline
- Return **only** the JSON object; no markdown fences, no narrative text.
- Include every key required by the task-specific `answer_template.json`.
- Use exact enum strings; never paraphrase.
- Empty lists are preferred over `null` for missing collections.
- For transfer fields that are optional, use `null` when the action does not involve a transfer.

## Common Pitfalls
1. **Using raw on-hand instead of effective available** — always subtract reserved, quarantined, and buffer stock.
2. **Sorting incorrectly** — almost every list must be ascending by its primary key; double-check composite sorts (e.g., transfer requests).
3. **Currency precision** — forgetting to round `total_cost_usd` or `extended_cost` to exactly 2 decimals.
4. **Missing summary keys** — the summary block usually requires explicit zero counts and sorted ID lists.
5. **Wrong precedence in recommendations** — supplier scorecards and procurement decisions have strict precedence; do not default to the safest code without checking higher-precedence rules.
6. **Not filtering POs by warehouse or status** — timely POs must be open/confirmed and directed to the correct warehouse.
7. **Including protected stock in transfers** — only surplus effective stock above buffer may be transferred.
8. **Wave ID or task ID mismatch** — always echo the exact `wave_id` or `task_id` from the memo/template.
