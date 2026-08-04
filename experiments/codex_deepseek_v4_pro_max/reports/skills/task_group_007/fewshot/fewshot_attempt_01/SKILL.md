---
name: northwind-erp-desk
description: Solve Northwind Components ERP operations-desk tasks by querying a shared REST API and producing structured JSON decisions. Use for expedite-queue dispatch, replenishment planning, supplier incident scorecards, allocation-desk transfer reviews, and procurement quality-hold reviews.
---

# Northwind ERP Operations Desk

Resolve operations-desk tasks for the fictional Northwind Components ERP by querying its shared REST API and assembling a structured JSON answer that conforms to the task's `answer_template.json`.

## General Workflow

1.  **Read the prompt and payloads.**
    - Open `<task_dir>/input/prompt.txt` for the task description.
    - Open every file under `<task_dir>/input/payloads/`. There will always be an `answer_template.json` and at least one memo or request file that carries business rules, filter dates, or target identifiers.

2.  **Discover the API surface.**
    - The ERP base URL is supplied via the placeholder `<TASK_ENV_BASE_URL>` (e.g., `http://task-env:9007/`).
    - Start with `GET /manifest` to confirm the current list of available endpoints.
    - All endpoints are read-only `GET`. No authentication headers are required.

3.  **Collect live data.**
    - Use list endpoints first (`/orders`, `/customers`, `/suppliers`, `/products`, `/inventory`, `/warehouses`, `/purchase_orders`, `/boms`, `/incidents`) then drill into individual records as needed.
    - For inventory, compute *effective available* as `on_hand − reserved − quarantined`. Do not treat protected quantities as freely available.
    - Use `/shipping/quote` for parcel quotes.
    - Use `/incidents` filtered by date range and supplier for quality tasks.

4.  **Apply business logic from the task memo.**
    - The memo or request JSON in `payloads/` defines the decision rules, thresholds, and allowed actions. Apply them exactly — do not invent additional policy.
    - Common statuses to inspect per record: customer account status (`account_blocked`, `review_required`, `fraud_watch`, `credit_watch`), product active/inactive flag, and warehouse inventory availability.

5.  **Assemble the output.**
    - Match the exact key set, types, enums, and sort orders declared in `answer_template.json`.
    - Currency values must be rounded to **two decimal places** (standard banker's rounding — round half to even).
    - Percentages where specified are rounded to **one decimal place**.
    - Durations are rounded to **two decimal places**.
    - Lists of IDs, SKUs, or order IDs must be sorted ascending unless a different ordering is specified.
    - Use `null` (JSON null) for optional fields declared as nullable in the template; never use empty strings or zeroes as null substitutes.

6.  **Deliver the answer.**
    - Return a single valid JSON object. No narrative, markdown fences, or explanatory text outside the JSON.

## Task Family Reference

The skill supports these recurring Northwind Components desk workflows. Each follows the same general workflow above; the differences are in which API endpoints matter and how the decision logic flows.

### Expedite Queue (Dispatch Control)

**What it does:** Reviews a list of sales orders and classifies each as ready, short, or blocked, then assigns a fulfillment decision.

**Key API endpoints:** `/orders`, `/customers`, `/products`, `/inventory`, `/warehouses`, `/shipping/quote`

**Decision flow:**
- Check product master for each order-line SKU. If **any** SKU is inactive, mark the line with `inactive_sku` status.
- Compute effective available inventory at the order's requested warehouse for every line SKU.
- If any line cannot be fully fulfilled from effective available, the order has a `shortage`.
- If all lines can be fulfilled but remaining stock after allocation drops below a safe threshold, classify as `low_stock`.
- Evaluate customer account status: `account_blocked` → `reject_hold`; `credit_watch` or `fraud_watch` → `manual_review`; otherwise check for review flags.
- Combine inventory status and customer exception to pick the `final_decision` and `next_action` using the precedence implied by the template's allowed values.

### Replenishment Planning (Kit Build / Production)

**What it does:** For a set of BOMs, computes component-level coverage from warehouse stock and open purchase orders, then proposes transfers and purchase requisitions.

**Key API endpoints:** `/boms`, `/products`, `/inventory`, `/warehouses`, `/purchase_orders`, `/suppliers`

**Decision flow:**
- Expand each BOM to its components and multiply by the target build quantity to get `total_required`.
- For each component SKU at the target warehouse, compute `target_effective_available` from current inventory.
- If effective available is already at or above `total_required`, the component is overstock or fully stocked — exclude it from replenishment.
- Check open/confirmed POs for the same SKU and warehouse. If a PO's delivery date is before the build date, count its quantity as `timely_po_qty`.
- After applying timely POs, compute the remaining gap. Cover it first with feasible inter-warehouse transfers (from warehouses that have surplus effective available), then with a purchase requisition.
- Assign `final_action` per component: `no_action_stocked`, `transfer_only`, `purchase_required`, `timely_po_covered`, or `overstock_excluded`.

### Supplier Incident Scorecard (Quality)

**What it does:** Filters incidents for a date window, groups them by supplier, computes per-supplier statistics, and assigns a recommendation code based on a precedence policy.

**Key API endpoints:** `/incidents`, `/suppliers`

**Decision flow:**
- Fetch all incidents and filter by `open_date` within the requested window (inclusive).
- Group by supplier. For each supplier compute: incident count, percentage of total filtered population, total resolution cost, average duration (closed: `close_date − open_date`; open: `analysis_date − open_date`), RMA vs. work-order split, open count, and severe-or-critical count.
- Apply the recommendation policy in the exact precedence order given (e.g., ESCALATE_SUPPLIER → PROCESS_REVIEW → WATCHLIST → MONITOR). Evaluate each code's conditions and pick the first match.
- Identify the highest-cost supplier and highest-incident-share supplier from the scorecard.

### Allocation Desk (Transfer / Mixed-Warehouse)

**What it does:** Evaluates every order line in a wave against available inventory at the requested warehouse and decides ship, transfer, backorder, or manual review.

**Key API endpoints:** `/orders`, `/customers`, `/products`, `/inventory`, `/warehouses`

**Decision flow:**
- For each order line, check customer account status first. Blocked, review-required, or fraud-watch accounts force `manual_review` for every line on that order.
- Check product master: inactive products force `manual_review` for that line.
- Compute `requested_effective_available` at the requested warehouse. If it is at least the requested line quantity, action is `ship`.
- If the requested warehouse cannot cover the line, check other warehouses for the same SKU. If another warehouse has sufficient effective available, action is `transfer` (choose one source warehouse; ship whatever the requested warehouse can provide as `ship_quantity`).
- If no warehouse can cover the line, action is `backorder`.

### Procurement Quality Hold (Replenishment Control)

**What it does:** Reviews recent quality incidents for a list of suppliers and decides whether to freeze, require buyer review, or monitor.

**Key API endpoints:** `/incidents`, `/suppliers`, `/purchase_orders`, `/products`

**Decision flow:**
- Fetch recent incidents (RMA and work-order) for the target suppliers within the analysis window.
- For each supplier, collect: quality status, recent incident count, RMA count, severe/critical count, open-incident count, affected SKUs, and open/confirmed POs.
- Assign a decision per supplier based on the severity and count of incidents:
  - **freeze_new_replenishment**: suppliers on quality-hold with significant open incidents or multiple RMAs.
  - **buyer_review_required**: suppliers with watch status, multiple recent incidents, or at least one severe/critical incident.
  - **monitor_only**: suppliers with low incident counts and no severe/critical flags.
- Collect all held PO IDs across suppliers and identify release suppliers (those with `monitor_only`).

## Data Conventions

- **Effective available inventory** = `on_hand − reserved − quarantined`. Never use raw `on_hand` for allocation decisions.
- **Timely purchase orders**: a PO is "timely" when its `delivery_date` (or `expected_delivery`) falls on or before the required date and its status is `open` or `confirmed`.
- **Customer risk flags**: inspect `status`, `account_status`, or equivalent fields on customer records for `blocked`, `review_required`, `fraud_watch`, and `credit_watch`.
- **Product active flag**: a product is inactive when its `status` field is anything other than `active` (typically `inactive` or `discontinued`).
- **Shipping quotes**: call `/shipping/quote` with the required parameters. The response includes `zone_distance`, `service_days`, and `total_cost_usd`.
- **Incident severity**: `high` and `critical` are the severe values used for escalation logic.

## Sorting and Precision Rules

- Sort lists of IDs, SKUs, and strings **ascending** unless a different order is specified in the answer template.
- **Currency**: round to two decimal places (round half to even).
- **Percentages**: round to one decimal place.
- **Durations**: round to two decimal places.
- When a template says "sort by X ascending, then Y descending", apply that exact multi-key sort.

## Error Handling

- If an API endpoint returns an empty list or a 404 for a specific ID, treat it as "record not found" and include the absence in the decision (e.g., a missing customer means the order cannot be verified → manual review).
- If the API is unreachable, report the connection failure and stop — do not fabricate data.
- Do not use `/health`, any `reset`/`reseed` endpoint, or any judge endpoint.
