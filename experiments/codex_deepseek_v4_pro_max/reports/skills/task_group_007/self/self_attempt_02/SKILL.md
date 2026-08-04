## Northwind ERP Operations Agent

Solve Northwind Components supply-chain operations tasks by reasoning over a live, read-only ERP API and conforming exactly to a provided JSON answer template.

### Core Workflow

For any Northwind Components task, follow this order without skipping steps:

1. **Read the prompt** (`prompt.txt`) to identify the task type and required inputs.
2. **Read all payload files** in `input/payloads/` — always at least one task-specific memo and `answer_template.json`.
3. **Collect live data** from the ERP API. Start broad (list endpoints) then narrow (entity-scoped endpoints) to minimize round-trips.
4. **Compute decisions** using the memo's business rules combined with live ERP records.
5. **Return exactly one JSON object** that passes every constraint in `answer_template.json`. Do not wrap the JSON in markdown fences or add any surrounding text.

### API Protocol

- **Base URL**: supplied by the runner as `<TASK_ENV_BASE_URL>`. Substitute this placeholder with the environment-specific URL at runtime.
- **Method**: GET only. All endpoints return JSON arrays or objects.
- **Authentication**: none required.
- **Forbidden endpoints**: never call `/health`, any `/reset` or `/reseed` endpoint, or any `/judge` endpoint.

Allowed GET endpoints (see also `api_reference.md`):

| Endpoint | Returns |
|---|---|
| `/manifest` | List of all available endpoints |
| `/products`, `/products/{product_id}` | Product master records |
| `/inventory`, `/inventory/{sku}` | Inventory records per warehouse |
| `/warehouses`, `/warehouses/{warehouse_id}` | Warehouse records |
| `/orders`, `/orders/{order_id}` | Sales orders and line items |
| `/customers`, `/customers/{customer_id}` | Customer account records |
| `/suppliers`, `/suppliers/{supplier_id}` | Supplier master records |
| `/purchase_orders`, `/purchase_orders/{po_id}` | Purchase orders |
| `/boms`, `/boms/{bom_id}` | Bills of materials |
| `/incidents`, `/incidents/{incident_id}` | Supplier incident records |
| `/shipping/quote` | Parcel shipping quotes |

### Output Conventions

Every answer must conform exactly to the task's `answer_template.json`. Follow these invariant rules:

- **Sorting**: sort lists as dictated by the template. When not specified, default to the entity's primary key (`order_id`, `sku`, `supplier_id`, etc.) ascending.
- **Currency**: all USD amounts rounded to 2 decimal places.
- **Percentages**: when the template calls for a percentage, round to 1 decimal place unless a different precision is specified.
- **Durations**: round to 2 decimal places when the template specifies duration precision.
- **Nulls**: use JSON `null` (not the string `"null"`) for optional fields that have no value.
- **Empty lists**: use `[]`, never omit a required list key.
- **No commentary**: the response body must be raw JSON — no markdown fences, no preamble, no trailing text.

### Data Model Relationships

Understand these cross-entity links before querying:

- An **Order** has a `customer_id`, a list of `lines` (each with `sku` and `quantity`), and a warehouse assignment per line.
- A **Product** is keyed by `sku` (string). Key fields: `product_name`, `is_active` (boolean), `unit_price`.
- A **Customer** has `account_status` (enum), `risk_flags` (list of strings), and `name`.
- **Inventory** records are per `sku` + `warehouse_id`. Compute effective available stock as: `quantity_on_hand − reserved − quarantined`. Do not consume reserved, quarantined, or normal operating-buffer stock when deciding availability.
- A **Warehouse** is keyed by `warehouse_id` (e.g. `WH_NORTH`, `WH_CENTRAL`, `WH_WEST`).
- A **Supplier** has `name`, `quality_status` (enum: `approved`, `watch`, `quality_hold`).
- A **Purchase Order** links a `supplier_id`, `sku`, `warehouse_id`, `quantity`, `status` (e.g. `open`, `confirmed`, `received`), and a date field.
- A **BOM** has a `bom_id`, a `kit_name`, and a list of `components` (each with `sku` and `quantity_per_kit`).
- An **Incident** relates to a `supplier_id` via `sku`. Key fields: `type` (RMA or WORK_ORDER), `severity` (low/medium/high/critical), `status` (open/closed), `open_date`, `close_date`, `resolution_cost`.
- A **Shipping Quote** is obtained per order or per line by calling `/shipping/quote` with relevant parameters (the endpoint returns `zone_distance`, `service_days`, `total_cost_usd`).

### Task Archetypes and Decision Logic

The training data covers five supply-chain desk functions. When you encounter a task, map it to the closest archetype and apply the corresponding reasoning:

#### 1. Expedite / Dispatch Control

Goal: for each order in a wave memo, classify inventory status, customer risk, and produce a fulfillment decision.

**Inventory status** (check all SKUs on an order; take the worst condition):
- `ready` — every SKU has sufficient effective available stock in the requested warehouse.
- `low_stock` — at least one SKU has positive but insufficient stock.
- `shortage` — at least one SKU has zero effective available stock.
- `inactive_sku` — at least one SKU maps to a product with `is_active: false`.
- `inactive_and_shortage` — both inactive and shortage conditions present.

**Customer exception** (check the order's customer record):
- `none` — account in good standing.
- `review_required` — account has a review flag but is not blocked.
- `account_blocked` — account status is blocked.
- `fraud_watch` — risk flags include fraud indicators.
- `credit_watch` — risk flags include credit indicators.

**Final decision** (combine inventory and customer signals):
- `ship_now` — inventory is `ready` or `low_stock`, and customer exception is `none`.
- `delayed_release` — inventory is `low_stock` with no severe customer exception.
- `manual_review` — customer exception requires human review, or inventory has inactive SKUs.
- `backorder` — inventory is `shortage` and customer can accept backorders.
- `reject_hold` — account is blocked, fraud watch, or inventory is `inactive_and_shortage`.

**Next action** — paired with each decision:
- `release_to_pick` → `ship_now`
- `delay_and_monitor` → `delayed_release`
- `send_account_review` → `manual_review` (account-driven)
- `create_backorder` → `backorder`
- `hold_credit_or_fraud` → `reject_hold` (risk-driven)
- `escalate_product_master` → `reject_hold` or `manual_review` (product-driven)

#### 2. Replenishment / Kit Build Planning

Goal: given target BOMs with build quantities and dates at a warehouse, determine which components need transfers, purchase requisitions, or can be excluded.

**For each component SKU across all target BOMs:**
1. Calculate `total_required` = sum of (quantity_per_kit × build_quantity) across all BOMs that use that SKU.
2. Compute `target_effective_available` = effective stock of that SKU at the planning warehouse.
3. Identify `timely_po_qty` = sum of quantities from open/confirmed POs for that SKU at the planning warehouse with delivery before the earliest build date.
4. Determine the gap: needed = total_required − (target_effective_available + timely_po_qty).
5. If gap ≤ 0 → component is covered; final action is `timely_po_covered` or `no_action_stocked`.
6. If gap > 0 → attempt to cover via inter-warehouse transfers first, then purchase requisitions.

**Final action for each component:**
- `no_action_stocked` — sufficient stock on hand.
- `timely_po_covered` — incoming PO(s) cover the requirement.
- `transfer_only` — gap can be fully covered by transfers from other warehouses.
- `purchase_required` — gap requires new purchase requisitions (possibly after partial transfer coverage).
- `overstock_excluded` — component should be excluded (target overstock or already sufficiently stocked).

**Exclusion reasons:**
- `target_overstock` — stock exceeds the build requirement.
- `timely_po_covers_gap` — confirmed PO quantity covers the gap.
- `stocked_no_gap` — stock alone satisfies the requirement.

**Transfer rules:**
- Source warehouse must not be the planning warehouse and must have effective available stock > 0.
- Do not deplete source warehouse below zero.
- If multiple source warehouses can cover, prefer the one with the most available stock.

**Purchase requisition rules:**
- Use the component's primary supplier from the product master.
- `unit_cost` from the product master or the most recent PO.
- `extended_cost` = unit_cost × quantity, rounded to 2 decimals.
- `needed_by` = the earliest build date across BOMs that require this SKU.

#### 3. Supplier Incident Scorecard

Goal: analyze supplier incidents within a date window and assign recommendation codes.

**Filtering:** include only incidents whose `open_date` falls within the analysis window (inclusive).

**Per-supplier metrics:**
- `incident_count` — count of filtered incidents.
- `incident_percentage` — (supplier_incident_count / total_filtered_incidents) × 100, rounded to 1 decimal.
- `total_resolution_cost` — sum of resolution_cost across filtered incidents, rounded to 2 decimals.
- `avg_duration_days` — average of (close_date − open_date) for closed incidents, or (analysis_date − open_date) for open incidents, rounded to 2 decimals.
- `rma_count` — count of incidents with type RMA.
- `work_order_count` — count of incidents with type WORK_ORDER.
- `open_incident_count` — count of incidents with status open.
- `severe_incident_count` — count of incidents with severity `high` or `critical`.

**Recommendation policy** (first matching, highest precedence wins):
1. `ESCALATE_SUPPLIER` — supplier `quality_status` is `quality_hold` AND incident_count ≥ 3, OR any critical RMA exists, OR RMA count ≥ 3 AND total_resolution_cost ≥ 15000.00.
2. `PROCESS_REVIEW` — WORK_ORDER count ≥ 3 AND exceeds RMA count.
3. `WATCHLIST` — supplier `quality_status` is `watch` or `quality_hold`, OR incident_count ≥ 4, OR total_resolution_cost ≥ 12000.00, OR severe_incident_count ≥ 2.
4. `MONITOR` — none of the above apply.

#### 4. Allocation Desk / Transfer Review

Goal: for each order line in a wave, decide whether to ship from the requested warehouse, transfer from another warehouse, backorder, or flag for manual review.

**Per line processing:**
1. Look up the order, the line's SKU, the requested warehouse, and the customer.
2. Check product: if `is_active` is false → `manual_review` with reason `inactive_product`.
3. Check customer: if account is blocked, review-required, or fraud-watched → `manual_review` with the corresponding reason.
4. Compute effective available for the SKU at the requested warehouse.
5. If effective available ≥ line quantity → action `ship`, `ship_quantity` = full line quantity.
6. If effective available < line quantity → scan other warehouses for transfer availability:
   - `ship_quantity` = min(line_quantity, effective_available_at_requested_warehouse).
   - Remaining quantity can be `transfer_quantity` from best source warehouse.
   - If no source can cover the remainder → action `backorder`.

**Line-level primary_reason values:**
- `none` — line can be fulfilled.
- `account_blocked` — customer account blocked.
- `account_review_required` — customer flagged for review.
- `fraud_watch` — customer on fraud watch.
- `inactive_product` — SKU is inactive.
- `insufficient_effective_stock` — stock cannot cover the line even with transfers.

**Order rollup outcome:**
- `ready_to_ship` — all lines are `ship`.
- `needs_transfer` — at least one line is `transfer`, no worse action.
- `has_backorder` — at least one line is `backorder`, no `manual_review`.
- `manual_review` — at least one line is `manual_review`.
- `mixed_actions` — combination of outcomes not covered above.

#### 5. Procurement Quality Control

Goal: review targeted suppliers for recent quality incidents and decide whether to freeze, flag for buyer review, or monitor their replenishment.

**For each target supplier:**
1. Query incidents for the analysis window.
2. Query the supplier's master record for `quality_status`.
3. Query open or confirmed POs for that supplier.
4. Compute: `recent_incident_count`, `recent_rma_count`, `severe_or_critical_count`, `open_incident_count`.
5. Collect `affected_skus` (unique SKUs across all recent incidents for that supplier, sorted).
6. Select up to 5 `sample_incident_ids` (sorted).

**Decision logic:**
- `freeze_new_replenishment` — supplier is on `quality_hold`, OR has ≥ 1 severe/critical RMA in the window, OR has ≥ 2 severe/critical incidents AND at least one is open.
- `buyer_review_required` — supplier `quality_status` is `watch`, OR has ≥ 1 open incident, OR has ≥ 3 recent incidents.
- `monitor_only` — neither of the above conditions are met.

- `held_po_ids` — all open or confirmed POs for a `freeze_new_replenishment` or `buyer_review_required` supplier.
- `release_supplier_ids` — all suppliers whose decision is `monitor_only`.

### General Guardrails

- **Never fabricate data.** Every value in the answer must come from a live API response, a memo file, or a deterministic computation on those.
- **Check entity existence.** If an API returns 404 or an empty response for an expected entity, treat it as a data gap and reflect it in the decision (e.g. inactive product, missing customer).
- **Memo takes priority.** When the task-specific memo contradicts a general rule in this skill, follow the memo.
- **Template is the contract.** The `answer_template.json` is the final authority on output shape. If it requires a key or value not mentioned in this skill, infer its meaning from the memo and API data.
- **Re-entrant.** Do not persist state between tasks. Each task starts fresh with only its `input/` files and the live API.
