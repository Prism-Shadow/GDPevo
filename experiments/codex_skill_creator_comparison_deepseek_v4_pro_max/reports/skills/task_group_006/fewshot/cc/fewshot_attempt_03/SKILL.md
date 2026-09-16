---
name: procureops-analyst
description: Analyze ProcureOps procurement records from a shared REST API to produce structured JSON answers for sourcing nomination, receiving closeout, AP close, change-control, and AP release workflows. Use this skill whenever the task mentions ProcureOps, a ProcureOps API, procurement readiness, receiving closeout, AP close, change control, sourcing nomination, AP release, vendor reconciliation, purchase orders, requisitions, contracts, budget snapshots, invoices, payments, or any supplier-facing procurement data analysis that references a shared task-environment API.
---

# ProcureOps Analyst

Produces structured JSON answers for procurement workflows by fetching ProcureOps REST API records, cross-referencing them by foreign key, and applying task-specific computation rules.

## How to use this skill

When a task references the ProcureOps API at a task-environment base URL, follow the workflow below. Read [references/api_schema.md](references/api_schema.md) when you need endpoint shapes or field details.

Start by reading the task prompt and every local payload file under the input directory. Then fetch the API records you need, cross-reference them by their foreign keys, compute the required values, and produce a single JSON answer matching the task's answer template.

## Workflow

### 1. Read the task and local inputs

Read the task prompt first. It tells you the task type, which record IDs matter (programs, POs, receipts, invoices, batches), and which local payload files to review. Then read every file under the input directory:

- **Memos** (`.md` or `.json`) carry human context about what the requester wants
- **Answer templates** (`.json`) define the required output structure, allowed values, and list-ordering rules
- **Chargeback registers or release packets** (`.json`) supply locally-staged exceptions, chargebacks, or alias notes not present in the API

Use the API as the source of truth for operational records. Trust local payload data only for request-specific information like chargeback statuses or alias mappings that do not exist in the API.

### 2. Fetch API records

The ProcureOps API is a read-only REST service at the base URL provided by the task runner as `<TASK_ENV_BASE_URL>`. No authentication is required.

Every GET endpoint returns `{ "count": N, "results": [...] }`. The entire dataset fits in a single response with no pagination. Call as many endpoints as the task needs, typically in parallel to reduce wait time.

Endpoint list and the key fields in each record:

| Endpoint | Key fields |
|---|---|
| `/manifest` | anchor_ids, record_counts |
| `/suppliers` | supplier_id, name, status, risk_rating |
| `/items` | sku, description, category, preferred_supplier_id, standard_cost |
| `/programs` | program_id, name, owner, budget_cap, committed_amount, cost_center |
| `/purchase_requisitions` | requisition_id, program_id, sku, quantity, status |
| `/contracts` | contract_id, program_id, supplier_id, sku, price_type, unit_price, ceiling_amount, status |
| `/purchase_orders` | po_id, program_id, requisition_id, contract_id, supplier_id, status, subtotal, tax, total, lines[], due_date |
| `/receipts` | receipt_id, po_id, supplier_id, status, receipt_date, packing_slip, lines[], warehouse_id |
| `/ap/invoices` | invoice_id, po_id, receipt_id, supplier_id, status, hold_code, subtotal, freight, tax, total, lines[] |
| `/ap/payments` | payment_id, invoice_id, supplier_id, amount, status, scheduled_date |
| `/approvals` | event_id, object_type, object_id, action, actor, event_date |
| `/budget_snapshots` | snapshot_id, program_id, budget_cap, committed_amount, pending_invoice_amount, snapshot_date |
| `/vendor_risk_events` | event_id, supplier_id, event_type, severity, status, related_object_id, event_date |

Fetch all endpoints relevant to the task. A sourcing nomination touches nearly every endpoint; an AP close may only need invoices, payments, POs, receipts, suppliers, and budgets.

### 3. Cross-reference records

Build lookup maps (dicts keyed by ID) from the full response arrays. This lets you resolve relationships in O(1) time without re-scanning arrays.

Common foreign-key chains:

- `program_id` links programs, requisitions, POs, contracts, budget snapshots
- `supplier_id` links suppliers, contracts, POs, invoices, receipts, vendor risk events
- `sku` links items, requisitions, contracts, and PO/receipt/invoice lines
- `po_id` links receipts, invoices, and (via related_object_id) vendor risk events to a PO
- `requisition_id` links POs and (via object_id when object_type is "requisition") approval events
- `contract_id` links POs to contracts
- `receipt_id` links invoices to receipts
- `invoice_id` links payments to invoices

When a task names a specific record, start there and walk outward: receipt, then PO, contract, program, budget snapshot, supplier, risk events, invoices, payments. Build only the lookup maps the task actually needs.

### 4. Compute task-specific values

**Budget headroom:** `budget_cap - committed_amount` from the program or budget-snapshot record. Use a budget snapshot when the template specifies a snapshot_id; use the program record otherwise. Round to cents.

**Financial calculations:** Round all USD amounts to 2 decimal places with standard rounding. Compute totals from line-level data (quantity times unit_price) rather than reusing precomputed API totals for derived values. Add freight and tax to subtotals for invoice totals.

**Quantity reconciliation (PO line vs receipt line vs invoice line):**
- `short_qty_vs_po = ordered_qty - received_qty`
- `unreceived_billed_qty = max(0, billed_qty - received_qty)`
- `receipt_completion_ratio = received_qty / ordered_qty` (4 decimal places)
- `quantity_variance = billed_qty - received_qty`
- `quantity_variance_pct = (absolute(billed_qty - received_qty) / ordered_qty) * 100` (1 decimal place)

**Contract ceiling check:**
- Sum subtotals of all non-cancelled POs under the contract (exclude POs where status is "cancelled")
- `headroom_before = ceiling_amount - noncancelled_subtotal`
- `headroom_after = headroom_before - requested_subtotal`
- `ceiling_ok = headroom_after >= 0`

**Approval check:**
- Find all approval events where object_type is "requisition" and object_id matches the requisition_id
- The latest event is the one with the most recent event_date
- `approval_ok = true` when the latest action is listed as a good action by the task (typically "approved")

**Supplier risk check:**
- Find all vendor risk events for the supplier
- Filter for open or monitoring status events as of the task's date cutoff
- Treat "high" severity open events as severe blockers; "medium" and "low" severity is contextual
- `supplier_risk_ok = true` when there are no open severe events for that supplier

**Vendor balance reconciliation (AP close tasks):**
- Opening balance is typically 0.00 unless the task specifies otherwise
- Scheduled payments are payments with status "scheduled" or "released" whose scheduled_date falls within the task's date window
- `close_balance = opening_balance + invoice_total - scheduled_payments`
- `balance_status`: "FULLY_SCHEDULED" when close_balance is 0, "OPEN_HELD" when all invoices are held, "OPEN_APPROVED" when at least one invoice is releasable

**Invoice hold/release logic:**
- Release when three-way match succeeds (PO, receipt, and invoice quantities align), no hold codes block, and the supplier has no open severe risk events
- Hold when quantities mismatch, no receipt exists, a hold code is present, or supplier risk blocks
- When chargebacks exist: `net_release_amount = invoice_total - approved_chargeback_amount`

### 5. Produce the JSON output

The answer must be a single JSON object matching the task's answer template exactly.

- Use the template's field names and nesting. Do not add or omit keys.
- Round all USD amounts to 2 decimal places.
- Sort list fields ascending when the template says "sorted ascending" or specifies an explicit sort order. When the template says "set" or "evaluator sorts", any order is fine but avoid duplicates.
- Use `null` for missing values when the field type permits it. Never use empty strings or "N/A".
- Output only the raw JSON object, no markdown fences, no commentary, no trailing text.
- When the template calls for an evidence section, list the specific record IDs you read from the API and the local filenames you reviewed.

### 6. Validate before returning

Before delivering the answer, check these points:

- Every required top-level key from the template is present
- All USD values are numbers (not strings), rounded to 2 decimals
- All list fields are valid JSON arrays with no empty-string entries
- All enum fields use one of the allowed values from the template
- All record IDs (PO, receipt, invoice, contract, payment, risk event, approval) come from actual API records, never invented
- Date fields use `YYYY-MM-DD` format
- No placeholder values remain ("string", 0 for fields that should be non-zero)

## Data integrity rules

**API is the source of truth.** Even when a local memo names specific quantities or amounts, verify them against the API. If they conflict, the API value is authoritative.

**Do not fabricate record IDs.** Every ID in the output must appear in the API responses. If a record referenced in a memo does not exist in the API, note it as missing rather than inventing an ID.

**Filter by date context.** When the task specifies an as_of or review date, exclude records dated after that cutoff unless the task explicitly includes future-dated records (e.g., scheduled payments within a window).

**Exclude cancelled POs from contract usage.** When computing contract ceiling consumption, count only POs whose status is not "cancelled".

**Match by foreign key, not guesswork.** Use the explicit foreign-key fields (po_id, receipt_id, etc.). Never match records by date proximity or name similarity alone.

**Handle multiple receipts per PO correctly.** A PO can have multiple receipts. When the task names a specific receipt batch, include only that receipt's data in the reconciliation, but list other receipts on the same PO in excluded lists when the template asks for them.

**Missing receipt handling.** When a PO has no receipts but an invoice exists, the invoice status is typically "pending_receipt" with hold_code "NO_RECEIPT". Quantities received are 0.00. The decision is hold.

**Missing contract handling.** When a PO has `contract_id: null`, the commercial_basis_id in the output is null, and "missing_contract" becomes a blocker code if that code is in the template's allowed values.

**Supplier watch vs. block.** A "watch" risk rating alone is a flag, not necessarily a hard block. A hard block requires an open "high" severity risk event. The template's allowed blocker codes and decision values define the exact rules for each task.

**Future-dated risk events.** When the as_of date falls before a risk event's event_date, exclude that event from the review since it had not occurred yet.

**Tax computation.** When the task requires computing tax on a new subtotal, use the tax rate from the task payload (not from any API record). Multiply subtotal by the rate, then round to 2 decimal places.

**Chargeback netting.** When a chargeback register is provided, use it to compute approved and pending chargeback amounts per invoice. Net release amount is `invoice_total - approved_chargeback_amount`. Do not net pending chargebacks.

## Task-type reference

| Task type | What it decides | Endpoints most likely needed |
|---|---|---|
| Sourcing nomination | Nominate, conditionally nominate, or hold each SKU line | programs, items, requisitions, contracts, POs, receipts, invoices, approvals, budget_snapshots, vendor_risk_events, suppliers |
| Receiving closeout | Accept, reject, or hold a receipt batch | receipts, POs, contracts, invoices, suppliers, vendor_risk_events |
| AP close | Hold or release each invoice for payment | invoices, POs, receipts, payments, suppliers, budget_snapshots |
| Change control | Release, hold, or reject a contract amendment | contracts, POs, programs, budget_snapshots, approvals, suppliers, vendor_risk_events |
| AP release | Release or hold invoices net of chargebacks | POs, receipts, invoices, suppliers, vendor_risk_events, plus local chargeback register |

For detailed endpoint schemas, see [references/api_schema.md](references/api_schema.md).
