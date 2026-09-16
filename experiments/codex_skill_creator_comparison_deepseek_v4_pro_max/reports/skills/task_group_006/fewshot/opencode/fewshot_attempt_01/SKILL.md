---
name: procureops-solver
description: Reusable solver for ProcureOps procurement operations tasks. Use this skill whenever the user mentions ProcureOps, procurement operations, sourcing nomination, receiving control, AP close, change control, invoice release, three-way match, supplier risk, contract headroom, budget checking, or any procurement API-based analysis task that references purchase orders, receipts, invoices, contracts, or vendor risk. This skill covers the full P2P lifecycle and should be used even when the user does not explicitly name the domain — any task involving supplier records, purchase orders, three-way matching, or procurement decision-support JSON output likely needs this workflow.
---

# ProcureOps Solver

A reusable workflow for completing ProcureOps procurement operations tasks. The solver queries a shared REST API, cross-references live operational records, applies domain business rules, and produces precisely structured JSON per a provided answer template.

## When to use this skill

Any task that involves querying a ProcureOps API (or a similarly named procurement REST API) and producing structured JSON decisions around sourcing, receiving, AP, contracts, budgets, approvals, or supplier risk. The user may call it ProcureOps, a procurement API, or describe the business workflow directly (nomination packet, AP close reconciliation, change-control decision, invoice release file, receiving closeout).

## Core workflow

Follow this sequence for every ProcureOps task:

### Step 1: Read the task payloads

Read every file provided alongside the prompt. Typical payloads include:

- **answer_template.json**: The exact JSON structure the solver must produce. Study every field name, type, enum value, ordering rule, and precision constraint. The output must match this template character-for-character on field names.
- **Memos / packets / registers**: Local documents that name target records, supply business-control parameters (tax rates, approval good-actions, excluded IDs), or provide data not available from the API (chargeback registers, alias notes).

### Step 2: Fetch all relevant API records

The task environment supplies the API base URL as `<TASK_ENV_BASE_URL>`. The ProcureOps API is read-only; all endpoints accept GET requests with no authentication. Available endpoints:

```
GET /manifest
GET /suppliers
GET /items
GET /programs
GET /contracts
GET /purchase_requisitions
GET /purchase_orders
GET /receipts
GET /ap/invoices
GET /ap/payments
GET /approvals
GET /budget_snapshots
GET /vendor_risk_events
```

Fetch every endpoint whose records intersect with the task. At minimum, query all endpoints that the answer template references. When a task memo names specific target IDs, also fetch the endpoints those IDs belong to. Prefer fetching all records from each endpoint and filtering locally rather than making many targeted calls — the datasets are small and batch retrieval avoids missing indirect relationships.

Use a script or parallel shell calls to fetch all endpoints. Parse each response as JSON immediately.

### Step 3: Cross-reference and join records

Build a coherent view by joining records across endpoints. The common join keys are:

| Key | Joins |
|-----|-------|
| `supplier_id` | suppliers ↔ contracts, purchase_orders, ap/invoices, vendor_risk_events |
| `program_id` | programs ↔ purchase_requisitions, purchase_orders, budget_snapshots |
| `po_id` | purchase_orders ↔ receipts, ap/invoices, ap/payments |
| `contract_id` | contracts ↔ purchase_orders, items |
| `sku` / `item_id` | items ↔ contracts, purchase_orders, purchase_requisitions |
| `invoice_id` | ap/invoices ↔ ap/payments |
| `requisition_id` | purchase_requisitions ↔ approvals |
| `receipt_id` | receipts ↔ ap/invoices |

When records share a parent ID (e.g., several receipts for one PO), collect all children. When the template says "exclude cancelled", filter on the appropriate status field.

### Step 4: Apply business rules

Apply the relevant rules from [references/rules.md](references/rules.md). Key rule families:

- **Three-way match**: Compare ordered, received, and billed quantities per PO line. Flag variances.
- **Contract ceiling**: Check headroom against ceiling by summing noncancelled PO subtotals.
- **Budget headroom**: Compare committed/spent against budget cap.
- **Supplier risk**: Check vendor_risk_events for open or monitoring events tied to the supplier.
- **Approval state**: Check latest approval event action against the allowed good-actions list.
- **Nomination readiness**: Assemble blocker codes from contract status, risk, AP holds, receipt state, and due dates.
- **AP hold/release**: Decide based on match state, chargeback status, and exception codes.
- **Chargeback netting**: Apply approved chargebacks as deductions from invoice totals.

Read `references/rules.md` when any of these families apply; it contains field paths and decision logic for each.

### Step 5: Produce the JSON output

Build the JSON object that matches the answer template exactly.

- Use the exact key names, types, and nesting from the template.
- Respect enum values precisely (do not invent new values or rephrase existing ones).
- **Precision**: USD amounts to 2 decimal places unless the template says otherwise. Ratios like `receipt_completion_ratio` to the precision specified (typically 4 decimal places). Percentages like `quantity_variance_pct` to 1 decimal place.
- **Sorting**: Every list field that says "sorted ascending" must be sorted ascending. Fields described as "set; evaluator sorts values" should also be sorted ascending (it is never wrong to sort). String sorting is lexicographic. Integer sorting is numeric.
- **Null vs empty**: Use `null` only when the template explicitly allows it. Use `[]` for empty lists (never omit the field). Use `0.0` or `0` for empty numeric defaults unless the template says otherwise.
- **Dates**: Format as `YYYY-MM-DD`.
- **Booleans**: Lowercase `true` / `false`.

### Step 6: Include evidence and source IDs

Many templates require an `evidence` or `supporting_ids` section that lists which record IDs were inspected. Include every record ID you used directly in producing the answer. Sort these ascending. Also list which local payload files were reviewed. This transparency lets evaluators verify coverage without inspecting the solver transcript.

## JSON output conventions (general)

These conventions apply across all ProcureOps tasks and supplement any specific template rules:

- **Field names**: Exact match to the template. Case-sensitive. No extra fields.
- **List ordering**: Sort ascending unless the template explicitly states a different order.
- **Numeric precision**: Round after each arithmetic operation, not only at the end. Use standard rounding (half-up).
- **Currency**: Always USD. Always rounded to cents (2 decimal places). When computing totals that involve tax or freight, compute the subtotal first, round it, then add rounded tax/freight.
- **Empty vs missing**: An empty list is `[]`, not omitted. A zero value is `0` or `0.0`, not omitted. A null contract ID is `null` only when the template allows it.

## Reference files

- [references/endpoints.md](references/endpoints.md): Detailed field listings and join keys for every ProcureOps API endpoint.
- [references/rules.md](references/rules.md): Complete business-rule definitions with field paths, decision logic, and blocker-code assignments.
