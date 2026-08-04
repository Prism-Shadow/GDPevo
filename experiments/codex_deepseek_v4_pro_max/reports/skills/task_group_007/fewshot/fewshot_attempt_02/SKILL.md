# Northwind Components ERP Operations Skill

## Overview

This skill provides reusable instructions for completing Northwind Components operational tasks using the shared ERP API. Tasks typically involve reading a local memo or request payload, querying live ERP records through the REST API, applying business logic, and returning a structured JSON answer.

## API Access

The ERP API is accessible at the base URL provided by the task runner as `<TASK_ENV_BASE_URL>`. All endpoints are read-only GET requests with no authentication required.

### Available Endpoints

`/manifest` — API manifest or index
`/products` and `/products/{product_id}` — Product master data
`/inventory` and `/inventory/{sku}` — Current inventory levels by warehouse
`/warehouses` and `/warehouses/{warehouse_id}` — Warehouse locations and details
`/orders` and `/orders/{order_id}` — Sales orders with line items
`/customers` and `/customers/{customer_id}` — Customer accounts and status flags
`/suppliers` and `/suppliers/{supplier_id}` — Supplier profiles and quality status
`/purchase_orders` and `/purchase_orders/{po_id}` — Purchase order headers and status
`/boms` and `/boms/{bom_id}` — Bill-of-materials with components and quantities
`/incidents` and `/incidents/{incident_id}` — Quality incidents with severity, status, and dates
`/shipping/quote` — Shipping rate quotes (requires query parameters for warehouse, destination, service speed, and order or SKU details)

### API Query Patterns

- Collection endpoints (e.g. `/orders`, `/incidents`) may support query parameters for filtering. Inspect the `/manifest` endpoint or response shapes to discover available filter fields.
- When a task references specific IDs (orders, suppliers, BOMs), fetch each individually if needed, or use collection-level filters when available.
- Always prefer direct lookups by ID (e.g. `/orders/{order_id}`) when working from a known identifier.
- Use `/inventory/{sku}` to get per-warehouse stock levels for a specific SKU.
- Use `/purchase_orders/{po_id}` to check PO status, warehouse, supplier, line items, and delivery dates.
- Use `/incidents/{incident_id}` for severity, type (RMA vs. WORK_ORDER), open/close dates, resolution cost, and associated supplier/SKU.

## Task Workflow

### 1. Read Input Files

Every task provides input files under `input/`:
- `prompt.txt` — Task description and scope
- `payloads/` — One or more JSON or Markdown files containing task parameters (memos, target lists, date windows, decision policies, answer templates)

Read the prompt first to understand the task type, then read all payload files. The answer template defines the exact output shape.

### 2. Query the API

Use the API endpoints to fetch live records referenced by the task. Common patterns:
- **Order tasks**: Fetch each order by ID, then fetch the associated customer, each line's product, and inventory for each SKU. Fetch a shipping quote when required.
- **BOM/Kit tasks**: Fetch each BOM by ID to get component SKUs and quantities, then fetch inventory for each component SKU, along with purchase orders and supplier data.
- **Incident/Quality tasks**: Fetch the incidents collection filtered by date range or supplier, then fetch supplier details. Compute supplier-level aggregates from incident records.

### 3. Apply Business Logic

Business rules are typically described in the memo payload and answer template. Common decision patterns:

**Inventory Status Classification:**
- `ready` — Effective available quantity at requested warehouse meets or exceeds required quantity
- `low_stock` — Available but below safety or order quantity
- `shortage` — Effective available is negative or insufficient
- `inactive_sku` — Product master shows the SKU is not active
- `inactive_and_shortage` — Both inactive SKU and shortage conditions apply

**Effective Available Calculation:**
- Use on-hand quantity minus reserved, quarantined, or protected buffer stock
- The API response fields indicate which quantities are available vs. reserved
- Do not treat reserved or protected stock as freely available

**Customer Exception Classification:**
- Inspect customer account status, flags for blocked, fraud_watch, or review_required
- `none` — No account flags
- `review_required` — Account has a review flag
- `account_blocked` — Account is blocked
- `fraud_watch` — Account is on fraud watch
- `credit_watch` — Account is on credit watch

**Transfer Sourcing:**
- When a requested warehouse cannot fulfill a line, check inventory at other warehouses
- Choose the source warehouse with sufficient effective available stock
- Prefer the warehouse with the most available stock for the SKU
- Do not use protected stock from any warehouse

**Purchase Order Coverage:**
- Check open or confirmed POs for the same warehouse and SKU
- A PO is "timely" if its expected delivery date is on or before the target build/need date
- POs in draft, cancelled, or completed status do not count as coverage

**Incident/Quality Decisions:**
- Filter incidents by date range using the `open_date` field
- Classify incidents by type (RMA, WORK_ORDER) and severity
- Apply recommendation policies in precedence order as specified in the task memo
- Count open incidents (no close_date or close_date in the future), severe incidents, and compute resolution costs

### 4. Format the Output

Return only a single JSON object matching the answer template. Follow these formatting rules:

- **Sorting**: Sort lists by ID ascending (order_id, supplier_id, SKU, warehouse_id) unless otherwise specified. For multi-key sorts, apply the exact ordering from the template.
- **Currency**: Round all monetary values to exactly 2 decimal places. Use standard arithmetic rounding.
- **Percentages**: Round to 1 decimal place when specified.
- **Durations**: Round to 2 decimal places when specified.
- **Nulls vs. Empty**: Use `null` for absent optional fields (e.g. `transfer_from` when no transfer) and empty arrays `[]` for absent lists.
- **Enum values**: Use exactly the string values defined in the answer template's allowed enums.
- **Dates**: Format as `YYYY-MM-DD` strings.

### 5. Verify Completeness

Before finalizing, check:
- All required top-level keys are present
- All records/lines from the task memo are included
- All lists are sorted as specified
- All currency and percentage precision rules are followed
- Summary counts are consistent with record-level data
- No narrative text or commentary outside the JSON

## Task Type Reference

### Expedite Queue Decision
**Inputs**: Queue memo with order IDs, operator notes
**Key Endpoints**: `/orders`, `/products`, `/customers`, `/inventory`, `/warehouses`, `/shipping/quote`
**Output**: Per-order inventory status, customer exception, fulfillment decision, next action, SKU exception lists, shipping quote; wave summary

### Kit Build Replenishment
**Inputs**: Production memo with BOM IDs, target quantities, dates
**Key Endpoints**: `/boms`, `/products`, `/inventory`, `/warehouses`, `/purchase_orders`, `/suppliers`
**Output**: Kit targets, component plan (total_required, effective_available, PO coverage, transfers, purchase reqs), transfer requests, purchase requisitions, exclusions, summary

### Supplier Incident Scorecard
**Inputs**: Scorecard request with date filter, recommendation policy
**Key Endpoints**: `/incidents`, `/suppliers`
**Output**: Analysis window, supplier-level metrics (counts, percentages, costs, durations), recommendation codes, top escalation list, highest cost/share supplier

### Allocation Desk Transfer Review
**Inputs**: Allocation memo with wave ID, allowed actions
**Key Endpoints**: `/orders`, `/products`, `/customers`, `/inventory`, `/warehouses`
**Output**: Per-line actions (ship/transfer/backorder/manual_review), transfer requests, blocked orders, order rollup, summary counts

### Quality Hold Review
**Inputs**: Review memo with target supplier IDs, analysis window, decision policy
**Key Endpoints**: `/incidents`, `/suppliers`, `/purchase_orders`
**Output**: Per-supplier quality assessment (incident counts, severity, affected SKUs), replenishment decision, held PO list, summary

## Error Handling

- If an API endpoint returns an error or unexpected shape, inspect the response and adjust the request. Try the singular endpoint if the collection endpoint fails, or vice versa.
- If inventory data for a SKU is missing, check whether the SKU exists in `/products` first — it may be inactive or not carried at the requested warehouse.
- If a shipping quote fails, verify the required query parameters (origin warehouse, destination, items) are all provided.
- Round only at the final step; compute all intermediate values with full precision.
