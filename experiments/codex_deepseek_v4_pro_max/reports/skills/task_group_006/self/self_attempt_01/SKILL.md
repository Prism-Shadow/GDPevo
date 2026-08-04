## When to Use

Use this skill whenever the task operates against a **ProcureOps REST API** and involves procurement-domain workflows: sourcing nominations, receiving closeouts, AP/finance reconciliations, change-control decisions, or exception-release processing. The skill provides the agent with the entity model, API query conventions, task-flow template, and output-formatting rules needed to reliably produce structured JSON answers from live ProcureOps records.

---

## ProcureOps Entity Model

The API surfaces these collections via `GET /<collection>` and `GET /<collection>/<id>`:

| Collection                | Purpose                                                        |
|---------------------------|----------------------------------------------------------------|
| `manifest`                | List available collections.                                     |
| `suppliers`               | Supplier profiles, names, risk ratings.                        |
| `items`                   | SKU/item master.                                               |
| `programs`                | Procurement programs (budget, owner).                          |
| `contracts`               | Contracts: status, unit price, ceiling amount.                 |
| `purchase_requisitions`   | Requisitions (approval lifecycle).                             |
| `purchase_orders`         | Purchase orders: lines, quantities, unit prices, status.       |
| `receipts`                | Receipt records: received qty, rejected qty, receipt date.     |
| `ap/invoices`             | AP invoices: status, hold code, totals.                        |
| `ap/payments`             | Scheduled/executed payments.                                   |
| `approvals`               | Approval events: action, actor, date.                          |
| `budget_snapshots`        | Budget caps and committed amounts per program.                 |
| `vendor_risk_events`      | Supplier risk events: severity, status (open/closed/monitoring).|

---

## API Query Conventions

- **Base URL**: The runner provides the API base URL as `<TASK_ENV_BASE_URL>`. Always construct endpoints as `<TASK_ENV_BASE_URL>/<collection>`.
- **Authentication**: None required.
- **Exact-match filtering**: Append `?field=value` query parameters. Works on top-level and nested record fields.
- **Date-range filtering**: Use `start=<YYYY-MM-DD>` and `end=<YYYY-MM-DD>` on date-bearing collections.
- **ID lookup**: Fetch a single record with `/<collection>/<id>`.
- **Source of truth**: The API is always the authoritative source. Local memos or packets name anchors/targets but the API determines current state.

---

## Task Execution Flow

Follow this ordered workflow for every ProcureOps task:

### Step 1 — Read local inputs
Read every file in `input/payloads/`. This always includes:
- An **answer template** (`answer_template.json`) — the exact JSON shape to produce.
- One or more **local memos/packets** — anchors the task to specific programs, suppliers, POs, receipts, invoices, or contracts.

### Step 2 — Read the prompt
The task prompt names the procurement workflow and any boundary conditions (e.g., as-of date, scope limit, currency rules, tax rate). Treat prompt-level rules as overriding defaults.

### Step 3 — Discover and fetch API records
Use the memo's anchors to query the relevant collections. Common strategy:
1. Fetch the program by ID or filter to confirm ownership/budget.
2. Fetch contracts by program or ID.
3. Fetch POs by program, supplier, or explicit IDs from the memo.
4. Fetch receipts by PO or batch ID.
5. Fetch invoices by PO, supplier, or explicit IDs.
6. Fetch payments by supplier or invoice.
7. Fetch approvals by requisition ID.
8. Fetch budget snapshots by program.
9. Fetch vendor risk events by supplier.

Always prefer fetching by ID when the memo provides one. Use query-parameter filters when searching across a collection.

### Step 4 — Cross-reference and reconcile
Map memo entities to live API records. Reconcile:
- Ordered vs. received vs. billed quantities.
- Unit prices across contract, PO, and invoice.
- Budget caps vs. committed spend.
- Approval states vs. required gates.
- Risk events vs. supplier status.

### Step 5 — Produce the output JSON
Construct the answer strictly adhering to the template. Apply all formatting rules, then return only the JSON object — no prose, no markdown fences, no commentary.

---

## Output Formatting Rules

Apply these rules universally across all ProcureOps task outputs:

- **Currency**: All monetary values in USD, rounded to **two decimal places** (cents).
- **List ordering**: Sort string IDs and enumerated values **ascending** (lexicographic for strings, numeric for integers) unless the template explicitly specifies a different sort order.
- **Set semantics**: Treat list fields as sets — no duplicate entries.
- **Enumerated values**: Use the exact enum strings defined in the template. Do not invent alternatives.
- **Null vs. empty**: Use `null` for absent scalar values; use `[]` for absent lists.
- **Date format**: Always `YYYY-MM-DD`.
- **Boolean fields**: Use JSON `true` / `false`, never strings.
- **Precision**: Follow template precision hints (`precision: 2` for currency, `precision: 4` for ratios, etc.).

---

## Domain-Specific Conventions

### Quantity reconciliation
- `quantity_received` → from receipt records.
- `quantity_billed` → from invoice records.
- `ordered_qty` → from PO line records.
- `rejected_qty` → from receipt records (damage/reject).
- Short/over calculations: `ordered_qty − received_qty`, `billed_qty − received_qty`.

### Contract and budget exposure
- **Contract ceiling exposure**: Line subtotal before tax and freight.
- **Budget exposure**: Line subtotal plus estimated tax (use the tax rate from the memo or prompt if provided, otherwise compute from invoice data). Include freight only when the memo or packet provides freight amounts.
- **Existing contract usage**: Sum non-cancelled PO subtotals. Exclude cancelled POs.
- **Budget headroom**: `budget_cap − committed_amount`.

### Approval interpretation
- An approval is "good" / "ok" when its latest action is `approved`. All other actions (`pending`, `rejected`, `returned`) are blocking.

### Supplier risk interpretation
- A supplier risk event is "open" when its status is `open` or `monitoring`.
- A risk event is "severe" when its severity is `severe` (or equivalent) and status is open.
- Supplier watch rating from the supplier record is contextual unless an open severe event is found.

### Receipt date scoping
- When the task specifies an `as_of_date`, only include receipts dated on or before that date.
- Invoice exceptions should also be scoped to the as-of date.

### Payment scheduling
- Scheduled payments through a given close date reduce the supplier's outstanding balance.
- Treat the opening AP balance as `0.00 USD` unless the prompt or memo provides a different opening figure.

---

## Error Handling and Edge Cases

- **Missing receipt for an invoice**: Set `quantity_received` to `0.00`, flag with `NO_RECEIPT`.
- **Cancelled PO**: Exclude from contract usage and budget commitment calculations.
- **No matching API record for a memo anchor**: Omit the entity from the output; include a note in `evidence` or supporting fields if the template provides them.
- **Multiple records match a filter**: Use the most recent by date; if ambiguous, prefer the record with the most complete data.
- **Invoice quantity exceeds receipt quantity**: Flag as `INVOICE_QTY_EXCEEDS_RECEIPT` or `QTY_VARIANCE`.

---

## Reference

For a consolidated view of the API collections, filter syntax, and common schema shapes, see `skill/api_reference.md`.
