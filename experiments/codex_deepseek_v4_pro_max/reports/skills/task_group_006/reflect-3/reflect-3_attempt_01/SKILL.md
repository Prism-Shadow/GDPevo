# ProcureOps Task Solver

## Overview
This skill provides a reusable approach for solving ProcureOps procurement-analysis tasks. ProcureOps is a simulated ERP API exposing operational records for programs, suppliers, items, contracts, purchase orders, receipts, invoices, payments, approvals, budget snapshots, and vendor risk events.

## Workflow

### 1. Read task inputs
- Read the task prompt for the business objective and any entity anchors (program IDs, PO IDs, invoice IDs, receipt IDs, contract IDs).
- Read **all** local payload files referenced in the prompt (memos, answer templates, packets). These name the specific records in scope and define the exact output schema.
- Read the environment description to learn the API base URL and available collection endpoints.

### 2. Query the API systematically
- Fetch the `/manifest` to understand the record landscape and seed identifiers.
- Fetch broad collections first (`/suppliers`, `/items`, `/programs`, `/contracts`) to build a lookup map.
- Then fetch the collections most relevant to the task: `/purchase_orders`, `/receipts`, `/ap/invoices`, `/ap/payments`, `/vendor_risk_events`, `/approvals`, `/budget_snapshots`, `/purchase_requisitions`.
- When the task names specific IDs, use collection filters (query params) to narrow results. Always also fetch by ID (`/<collection>/<id>`) to confirm single-record details.
- For date-bounded tasks, use `start=` and `end=` query parameters where available. For other collections, filter in memory by comparing record date fields against the task's effective as-of date.

### 3. Cross-reference records
- Trace the procurement chain: requisition → purchase order → receipt → invoice → payment.
- Match records by shared keys: `po_id`, `receipt_id`, `invoice_id`, `contract_id`, `supplier_id`, `program_id`, `sku`, `requisition_id`.
- For POs under a contract, fetch all POs with that `contract_id` and exclude cancelled ones when computing contract usage, unless the task explicitly directs otherwise.
- For supplier risk, collect all vendor risk events for the target supplier. Filter to open or monitoring status as of the task's effective date. Pay attention to severity levels when the task distinguishes "severe" from other events.

### 4. Compute financial and quantity values
- **Currency amounts**: always round to cents (2 decimal places) in USD. Use `subtotal` for line-item goods value (excludes freight and tax). Use `total` for the all-in amount.
- **Quantity reconciliation**: compare `quantity_billed` (from invoice lines) against `quantity_received` (from receipt lines) and `quantity` (from PO lines). Compute variances as differences, not absolute values.
- **Contract ceiling headroom**: `ceiling_amount` minus the sum of `subtotal` from all non-cancelled POs under that contract.
- **Budget headroom**: `budget_cap` minus `committed_amount` from the program or its latest budget snapshot.
- **Tax computation**: when a tax rate is given, apply it to the line subtotal only: `subtotal * (tax_rate_percent / 100)`, rounded to cents.
- **Max affordable quantity**: `remaining_budget / (unit_price * (1 + tax_rate))`, floored to an integer.

### 5. Make structured decisions
- Decisions must come from the allowed enum values in the answer template. Never invent a value.
- **Readiness / nomination decisions**: consider contract existence and status, receipt completion, invoice hold codes, supplier risk rating and open risk events, and PO due dates relative to the as-of date.
- **Hold vs. release**: an invoice is releasable only when all blocking conditions are resolved. Blockers include: missing receipt, quantity variance with no approved chargeback, pending inspection/quality review, and missing or mismatched contract.
- **Reason codes**: use the smallest sufficient set. When `NO_RECEIPT` applies, omit `QTY_VARIANCE` — the absence of a receipt subsumes the quantity discrepancy. Prefer alphabetical ordering when the template specifies it.
- **Blocker codes**: a supplier's `risk_rating` of "watch" alone is enough for `supplier_watch`. Open risk events for that supplier trigger `open_supplier_risk`. Check PO due dates against the as-of date for `late_due_date`.
- **Approval checks**: inspect the latest approval event (by `event_date`) for the target requisition. The action must match one of the task's defined good actions ("approved", etc.) for approval to be OK.

### 6. Format the output
- Produce **only** the JSON object described by the answer template. Do not wrap in extra keys, add prose, or include markdown fences unless the task prompt explicitly requests them.
- Match the template's field names, types, and ordering exactly. Sort list fields ascending unless the template says "set" (evaluator sorts).
- Include `task_id` exactly as specified in the template — some templates use short forms, others use fully-qualified forms.
- Use `null` (not the string `"null"`) for absent optional values like a missing contract ID or empty hold code.
- Empty lists use `[]`, not `null`.
- Boolean fields use JSON `true`/`false`.
- Numeric precision: follow the template's stated precision (cents = 2 decimals, ratios = 4 decimals, percentages = 1 decimal).

### 7. Evidence and traceability
- The `evidence` or `supporting_ids` sections should list every API record ID you consulted to build the answer. Use the exact IDs as returned by the API. Sort them ascending.
- The `task_payloads_reviewed` field should name every local payload file you read, using its filename exactly as it appears in the input directory.

## Common patterns by task type

### Sourcing nomination / readiness packet
1. Identify the program, package SKUs, and anchor POs from the memo.
2. For each SKU: find the item, preferred supplier, contract (if any), requisition, PO, receipts, invoices, and risk events as of the effective date.
3. Evaluate readiness: contract coverage, receipt completion ratio, invoice exceptions, supplier risk posture, and budget headroom.
4. Assign blocker codes and a committee action.

### Receiving closeout / invoice reconciliation
1. Locate the target receipt by ID. Pull its PO, supplier, and linked invoice.
2. Build a line reconciliation: ordered vs. received vs. billed. Compute short quantities and completion ratios.
3. Review the invoice for hold codes, status, and exception conditions.
4. Compute financial exposure: received goods value, unreceived value, and invoice totals.
5. Determine batch disposition, AP action, receiving action, and supplier action from the template's allowed values.

### AP close / payment-hold reconciliation
1. For each target invoice, pull the PO, receipt, supplier, and any scheduled payments through the close window.
2. Compute per-invoice: quantity variance, hold decision, scheduled payment amount, net balance impact, and reason codes.
3. Roll up by supplier: opening balance + invoice total - scheduled payments = close balance. Classify balance status.
4. Roll up by program: invoice count, totals, held vs. released.
5. Build hold and release queues as sorted lists of invoice IDs.

### Change control / amendment decision
1. Pull the contract, compute noncancelled PO subtotals, and determine ceiling headroom before and after the requested quantity.
2. Pull the program budget snapshot and compute remaining budget vs. requested total (subtotal + tax).
3. Check the source requisition's latest approval event against the good-action list.
4. Check the supplier for severe open risk events; treat non-severe watch ratings as context only unless the task says otherwise.
5. Combine findings into a single decision from the template's enum.

### AP release / exception review
1. Cross-reference the chargeback register (from local packet) with API invoice, PO, and receipt data.
2. For each invoice: determine if there is an approved chargeback (→ net release), a pending chargeback (→ hold), or no receipt at all (→ hold).
3. Compute approved chargeback amount as `basis_quantity * unit_cost`, pending similarly.
4. Net release amount = `invoice_total - approved_chargeback_amount`. For held invoices, net release is 0.
5. For each target receipt: assign exception codes based on inspection status, quantity shortfalls, and chargeback reasons.
6. Summarize with release/hold invoice ID lists and aggregated dollar totals.

## Key reminders
- The API is the source of truth. Local memos may name anchors but the API holds the live data.
- Date filtering: use `start=`/`end=` on date collections; for others, filter in memory by comparing date fields against the as-of date (inclusive on the as-of date).
- Cancelled POs: exclude from contract usage and budget computation unless the task says otherwise.
- Payments through a date window: include any payment with `scheduled_date` on or before the window end date.
- When a supplier has no open severe risk events, `supplier_risk_ok` is `true` even if their rating is "watch" or "medium".
- For "three-way match" (PO-receipt-invoice), all three quantities must align and prices must match for a clean approval.
