# Skill: Northwind Components ERP Decision Tasks (task_group_007)

## Overview
These tasks require querying a shared Northwind ERP API (default `http://127.0.0.1:8007`) and producing strictly-formatted JSON decisions. The output schema is always defined in `input/payloads/answer_template.json` and must be matched exactly. Each task is driven by a memo or request file in `input/payloads/`.

## General Workflow
1. Read the task prompt (`input/prompt.txt`) to identify the decision type.
2. Read the answer template (`input/payloads/answer_template.json`) to learn the exact required keys, types, enums, and sorting rules.
3. Read any memo/request payload in `input/payloads/` for target IDs, date windows, or policy rules.
4. Start or connect to the ERP API (base URL from prompt/memo, typically `http://127.0.0.1:8007`).
5. Fetch live records for every entity referenced. Do not use cached or assumed inventory snapshots.
6. Apply the business rules described in the memo/template, compute derived values, and assemble the JSON.
7. Validate: correct keys, correct enum values, all lists sorted per template, currency rounded to 2 decimals, percentages rounded as specified.
8. Return **only** the JSON object.

## API Usage Habits
- **Base URL**: Usually `http://127.0.0.1:8007`; may be provided in the memo. Start the environment from `task_group/task_group_007/env` if needed.
- **Key endpoints** (inspect OpenAPI/docs at runtime to confirm paths):
  - `/orders` or `/orders/{id}` — lines, requested warehouse, quantities.
  - `/customers` or `/accounts` — status flags: `blocked`, `review_required`, `fraud_watch`, `credit_watch`.
  - `/products` — SKU master, `active`/`inactive` status.
  - `/inventory` or `/warehouses/{id}/inventory` — on-hand, reserved, quarantined, buffer. Compute **effective available** as what is truly free for the wave (exclude reserved, quarantined, and normal operating buffer).
  - `/purchase_orders` — open or confirmed POs by warehouse/SKU for coverage checks.
  - `/suppliers` — `quality_status` (`approved`, `watch`, `quality_hold`), supplier name.
  - `/incidents` — filter by date range, supplier, severity, type (`rma`, `work_order`).
  - `/shipping_quotes` or `/quotes` — zone distance, service days, total cost in USD.
  - `/boms` — bill-of-materials lines for kit builds.
- **Live data rule**: Always use current API records. Never assume a SKU is active/inactive or that stock matches a prior run.

## Controlled Vocabularies & Enums
Memorize these common enum sets; the template will reference them but may not repeat the full list:

### Inventory Status
- `ready`
- `low_stock`
- `shortage`
- `inactive_sku`
- `inactive_and_shortage`

### Customer Exception
- `none`
- `review_required`
- `account_blocked`
- `fraud_watch`
- `credit_watch`

### Final Decision (Expedite / Allocation)
- `ship_now`
- `delayed_release`
- `manual_review`
- `backorder`
- `reject_hold`

### Next Action (Expedite)
- `release_to_pick`
- `delay_and_monitor`
- `send_account_review`
- `create_backorder`
- `hold_credit_or_fraud`
- `escalate_product_master`

### Line Action (Allocation)
- `ship`
- `transfer`
- `backorder`
- `manual_review`

### Primary Reason (Allocation)
- `none`
- `account_blocked`
- `account_review_required`
- `fraud_watch`
- `inactive_product`
- `insufficient_effective_stock`

### Component Final Action (Replenishment)
- `no_action_stocked`
- `transfer_only`
- `purchase_required`
- `timely_po_covered`
- `overstock_excluded`

### Exclusion Reason (Replenishment)
- `none`
- `target_overstock`
- `timely_po_covers_gap`
- `stocked_no_gap`

### Supplier Recommendation Code (Scorecard / Quality)
Precedence order matters: evaluate top-to-bottom and stop at first match.
1. `ESCALATE_SUPPLIER`
2. `PROCESS_REVIEW`
3. `WATCHLIST`
4. `MONITOR`

### Quality Hold Review Decisions
- `freeze_new_replenishment`
- `buyer_review_required`
- `monitor_only`

### Supplier Quality Status
- `approved`
- `watch`
- `quality_hold`

## Sorting & Ordering Rules
Always sort lists exactly as the answer template specifies. Common patterns:
- **By ID ascending**: `order_id`, `sku`, `supplier_id`, `po_id`, `bom_id`.
- **Compound sorts**:
  - Allocation lines: `order_id` asc, then `line_id` asc.
  - Transfer requests (replenishment): `sku` asc, then `quantity` desc, then `from_warehouse_id` asc.
  - Top escalation suppliers: `incident_count` desc, then `total_resolution_cost` desc, then `supplier_id` asc.
- **SKU exception lists** (shortage, inactive, low_stock): ascending by SKU.
- **Incident IDs / PO IDs**: ascending string sort.
- **Sample lists** (e.g., top 5 incident IDs): sort ascending, then truncate to max length.

## Rounding & Precision
- **Currency** (USD): always round to **2 decimal places** in the final JSON.
- **Percentages**: typically **1 decimal place** (e.g., `23.7`).
- **Duration / averages**: typically **2 decimal places**.
- Use standard rounding (half-up) unless the template states otherwise.

## Business Logic Patterns

### 1. Account / Customer Risk Checks
- Query the customer/account record for the order.
- If `blocked` → decision often becomes `reject_hold` or `manual_review` with action `hold_credit_or_fraud`.
- If `review_required` → `manual_review` / `send_account_review`.
- If `fraud_watch` or `credit_watch` → line-level `manual_review` with matching primary reason.
- **Blocked orders list**: include orders where account-level risk stops the entire order, not just a single line.

### 2. Inventory & SKU Status
- For each order line, read the product master. If `inactive` → include SKU in `inactive_skus` and set inventory status to `inactive_sku` or `inactive_and_shortage`.
- Compute **effective available** at the requested warehouse after excluding reserved, quarantined, and normal operating buffer stock.
- If effective available < requested quantity → shortage. If 0 < effective < requested but not zero → can be `low_stock`.
- **Important**: In allocation tasks, transfer only the *uncovered* quantity from another warehouse; any quantity the requested warehouse can fulfill stays as `ship_quantity`.

### 3. Shipping Quotes
- Always request the quote using the live API with the order’s shipping parameters (speed, zone, weight).
- Include `zone_distance` (int), `service_days` (int), `total_cost_usd` (number, 2 decimals) even when the final decision is not release.

### 4. Replenishment / Kit Builds
- Explode BOMs to component-level total required quantities.
- Compute gap = required − effective available at target warehouse.
- Check for **timely PO coverage**: open or confirmed POs for the *same* warehouse with delivery before the build date. If a timely PO covers the gap, action = `timely_po_covered` and exclude from purchases.
- Check **inter-warehouse transfers**: source from other warehouses’ *unprotected* stock (exclude their reserved/buffer). Transfer only what is needed; prefer one or multiple sources as the data allows.
- If effective available > required (overstock) → `overstock_excluded`.
- Purchase requisition quantity = remaining gap after transfers and timely POs.
- `extended_cost` = `quantity` × `unit_cost`, rounded to 2 decimals.

### 5. Supplier Scorecards
- Filter incidents by the memo’s date window (usually on `open_date`, inclusive).
- Severity values considered severe: `high`, `critical`.
- `incident_percentage` = supplier incident count / total filtered incident count × 100, rounded to 1 decimal.
- `avg_duration_days`:
  - Closed incidents: calendar days from `open_date` to `close_date`.
  - Open incidents: calendar days from `open_date` to `analysis_date`.
- Apply recommendation policy in strict precedence order; do not fall through to a lower code if a higher one matches.
- `top_escalation_suppliers` includes only those with code `ESCALATE_SUPPLIER`, sorted by incident count desc, then cost desc, then supplier_id asc.
- `highest_cost_supplier_id` = supplier with greatest total resolution cost in the filtered set.
- `highest_share_supplier_id` = supplier with greatest incident count in the filtered set (or use cost if tied, per typical logic; follow template instructions).

### 6. Quality Hold Review
- Review only the target suppliers listed in the memo.
- Gather incidents in the analysis window, count RMAs, severe/critical incidents, open incidents.
- Collect affected SKUs and up to 5 sample incident IDs (sorted, truncated).
- Collect **open or confirmed** purchase order IDs for the supplier → `held_po_ids`.
- Decision mapping example:
  - `quality_hold` + incidents → `freeze_new_replenishment`
  - `watch` + incidents → `buyer_review_required` or `monitor_only` depending on severity/open counts
  - Clean record → `monitor_only`
- Summary counts must reconcile with the supplier decisions list.

## Common Pitfalls
- **Ignoring sorting**: many tasks fail if lists are not in the exact order required by the template.
- **Using gross inventory instead of effective available**: always subtract reserved, quarantined, and buffer.
- **Missing transfer requests in allocation**: when `action` is `transfer`, you must emit a corresponding entry in `transfer_requests`.
- **Forgetting blocked orders rollup**: account-level blocks must appear in both `blocked_orders` and every line of that order set to `manual_review` with the appropriate reason.
- **Currency rounding errors**: round at the final output step; do not truncate.
- **Not checking product active status**: inactive SKUs must be flagged even if there is physical stock.
- **Exceeding max list lengths**: e.g., `sample_incident_ids` limited to 5; sort first, then slice.
- **Null vs omitted fields**: the template may require `transfer_from: null` rather than omitting the key.

## File Conventions
- Task prompt: `input/prompt.txt`
- Answer template (schema): `input/payloads/answer_template.json`
- Task-specific memos/requests: `input/payloads/*.json` or `*.md`
- Output: a single JSON object only, no markdown wrapper.
