---
name: procureops-analyst
description: Solve ProcureOps procurement analytics tasks by querying the ProcureOps REST API, traversing the procurement domain model, and filling structured answer templates with reconciled finance, risk, and supply-chain data.
---

# ProcureOps Analyst

Solve procurement analytics tasks in the ProcureOps domain. Use the shared ProcureOps REST API as the system of record, cross-reference local task memos or packets, and produce structured JSON answers that conform to a supplied answer template.

## Quick Start

When a ProcureOps task arrives:

1. Read the task prompt, the local memo/packet payloads, and the answer template.
2. Fetch all relevant records from the ProcureOps API. The API base URL is given in the prompt as a runner-supplied variable, typically `<TASK_ENV_BASE_URL>`. Resolve it from the environment.
3. Traverse the procurement domain model (see [reference/domain_model.md](reference/domain_model.md)) to connect entities across endpoints.
4. Apply the business rules in [reference/business_rules.md](reference/business_rules.md) to compute readiness, decisions, financials, and exceptions.
5. Fill the answer template faithfully, following all formatting conventions.
6. Return the completed JSON object and nothing else outside it.

## API Endpoints

All endpoints return JSON arrays under a `results` key, with a `count` of total records. No pagination parameters are needed; each endpoint returns its full dataset.

| Endpoint | Returns |
|---|---|
| `GET /suppliers` | Supplier records with risk_rating, status, payment_terms |
| `GET /items` | Item master records with SKU, category, preferred_supplier_id, standard_cost |
| `GET /programs` | Program records with budget_cap, committed_amount, owner, cost_center |
| `GET /purchase_requisitions` | Requisition records with program_id, sku, quantity, status |
| `GET /contracts` | Contract records with ceiling_amount, unit_price, price_type, supplier_id, program_id, status |
| `GET /purchase_orders` | PO records with lines (sku, quantity, unit_price), status, subtotal, tax, total, supplier_id, program_id, contract_id, requisition_id |
| `GET /receipts` | Receipt records with lines (po_line_id, sku, quantity_received, quantity_rejected, inspection_status), status, po_id, supplier_id, receipt_date |
| `GET /ap/invoices` | AP invoice records with lines (po_line_id, quantity_billed, unit_price), status, hold_code, subtotal, freight, tax, total, po_id, receipt_id, supplier_id |
| `GET /ap/payments` | Payment records with invoice_id, amount, scheduled_date, status |
| `GET /approvals` | Approval event records with object_id (requisition_id), action, actor, event_date |
| `GET /budget_snapshots` | Budget snapshot records with program_id, budget_cap, committed_amount, pending_invoice_amount, snapshot_date |
| `GET /vendor_risk_events` | Vendor risk event records with supplier_id, event_type, severity, status, related_object_id, event_date |

See [reference/record_schemas.md](reference/record_schemas.md) for the exact field shapes returned by each endpoint.

## Processing Workflow

### Phase 1: Gather

Fetch all endpoints. You will need the full dataset for most tasks because entity relationships cross endpoint boundaries. Use parallel requests to minimize latency.

### Phase 2: Anchor

Identify the target entities from the local memo or packet. These are the starting anchors: a program_id, a set of SKUs, PO IDs, receipt IDs, or invoice IDs. Use the exact identifier strings from the memo to look up matching API records.

### Phase 3: Traverse

Follow reference chains outward from the anchors. For example:

- Given a SKU, find the item, its preferred_supplier_id, the supplier, contracts for that supplier+SKU, POs with that contract/supplier, receipts for those POs, invoices for those POs, payments, and risk events for that supplier.

Filter by as_of_date when the task provides one. Exclude records dated after the as_of_date. For receipts and invoices, include only those with dates on or before the as_of_date. For risk events, include open or monitoring events regardless of date (they represent active concerns).

When a task references "PO-73xx" POs or other aliases not present in the API, the local payload contains the mapping. Use the mapped IDs and note the alias in evidence/notes, not in computed values.

### Phase 4: Compute

Apply the business rules from [reference/business_rules.md](reference/business_rules.md) to derive:

- Budget headroom, contract headroom
- Quantity reconciliations (ordered vs received vs billed)
- Financial subtotals, totals, and net amounts
- Readiness and blocker assessments
- Exception codes
- Hold/release decisions
- Chargeback netting

All USD amounts round to cents (2 decimal places). All percentages round to 1 decimal place. Ratios (like receipt_completion_ratio) use 4 decimal places.

### Phase 5: Fill Template

Read the answer template carefully. It defines required keys, allowed enum values, data types, sort orders, and precision.

- String values: use exact record IDs/names from the API
- List fields: treat as sets (no duplicates) and sort as specified (typically ascending)
- Enum fields: use only allowed values, exactly as spelled in the template
- Nullable fields: use `null` (JSON null), not the string "null", when no value exists
- Boolean fields: use `true`/`false`, not strings

**Never invent IDs or values.** Every ID, name, amount, and status code must come from API records or from arithmetic on API values. The only exception is the task_id field, which the template specifies.

Build the output object to match the template's shape exactly. Do not add extra keys. Do not omit required keys unless the template marks them optional.

### Phase 6: Validate

Before returning, verify:

- Every referenced ID exists in the API records
- Arithmetic is correct (subtotals sum to totals, tax rates applied consistently)
- All lists are sorted as specified
- All enum values match the template's allowed set
- No task-specific final answers are hardcoded from memory

## Formatting Conventions

- **USD amounts**: round to 2 decimal places (cents)
- **Percentages**: round to 1 decimal place
- **Ratios**: round to 4 decimal places (e.g., 0.9000)
- **Sorting**: string IDs ascending (lexicographic); numeric codes ascending; SKUs ascending
- **Sets**: remove duplicates before sorting
- **Dates**: format as YYYY-MM-DD
- **JSON**: valid strict JSON, no trailing commas, no comments, no prose outside the JSON object

## Domain Model

See [reference/domain_model.md](reference/domain_model.md) for the full entity-relationship diagram and traversal patterns.

## Business Rules

See [reference/business_rules.md](reference/business_rules.md) for all computation rules, blocker and exception code assignments, readiness determination, and decision logic.

## Record Schemas

See [reference/record_schemas.md](reference/record_schemas.md) for the field-by-field shape of every API endpoint response.
