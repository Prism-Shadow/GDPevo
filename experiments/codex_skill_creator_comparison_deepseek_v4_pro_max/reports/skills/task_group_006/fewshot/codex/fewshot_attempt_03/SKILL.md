---
name: procureops
description: ProcureOps procurement operations analysis. Use when Codex needs to query a ProcureOps REST API, cross-reference operational records (programs, suppliers, contracts, POs, receipts, invoices, payments, approvals, budgets, vendor-risk events), apply procurement business rules, and produce structured JSON decision files for sourcing nomination, receiving closeout, AP close desk, change control, or AP release workflows. Triggered by tasks that reference a ProcureOps API base URL, task-local memos/payloads, and a JSON answer template.
---

 # ProcureOps

 ## Overview

 ProcureOps is a shared procurement operations environment with a REST API exposing
 source-of-truth records. All tasks follow the same general pattern: read a
 task-local memo or packet, pull relevant records from the API, apply business
 rules, and return a JSON object matching a provided answer template.

 ## General Workflow

 For any ProcureOps task:

 1. Read the task prompt, memo/packet payloads, and the answer template.
 2. Identify the target record IDs (program, PO, receipt, invoice, contract, SKU,
    requisition) from the prompt and payloads.
 3. Pull relevant API endpoints using `curl`. Fetch full endpoint results and
    filter client-side by matching IDs or join keys. The API reference is in
    [references/api_endpoints.md](references/api_endpoints.md).
 4. Cross-reference records by the join keys documented in the API reference.
 5. Apply business rules from [references/business_rules.md](references/business_rules.md).
 6. Populate the answer template with computed values. Round USD amounts to cents.
    Sort list fields ascending unless the template specifies set semantics.
 7. Return only the JSON object; no prose outside it.

 ## API Quick Start

 The API base URL is always provided as `<TASK_ENV_BASE_URL>`. All endpoints
 return `{"count": N, "results": [...]}`. No auth required.

 ```bash
 # Pull all records from endpoints likely relevant to the task
 curl -s <TASK_ENV_BASE_URL>/programs
 curl -s <TASK_ENV_BASE_URL>/suppliers
 curl -s <TASK_ENV_BASE_URL>/contracts
 curl -s <TASK_ENV_BASE_URL>/purchase_orders
 curl -s <TASK_ENV_BASE_URL>/receipts
 curl -s <TASK_ENV_BASE_URL>/ap/invoices
 curl -s <TASK_ENV_BASE_URL>/ap/payments
 curl -s <TASK_ENV_BASE_URL>/purchase_requisitions
 curl -s <TASK_ENV_BASE_URL>/approvals
 curl -s <TASK_ENV_BASE_URL>/budget_snapshots
 curl -s <TASK_ENV_BASE_URL>/vendor_risk_events
 curl -s <TASK_ENV_BASE_URL>/items
 ```

 Use the helper script [scripts/procureops_client.py](scripts/procureops_client.py)
 for filtered queries:

 ```bash
 python3 /work/skill/scripts/procureops_client.py <TASK_ENV_BASE_URL> purchase_orders --ids PO-AX17-4481,PO-AX17-4519
 python3 /work/skill/scripts/procureops_client.py <TASK_ENV_BASE_URL> ap/invoices --by-field supplier_id SUP-LUMA
 ```

 ## Task Workflows

 Select the workflow below that matches the task prompt. Each workflow lists
 the endpoints to pull, the business rules to apply, and the output shape.

 ### Sourcing Nomination Readiness

 **When**: Prompt asks for nomination readiness, committee packet, or sourcing
 decision for a program and package-line SKUs.

 **Input payloads**: A memo naming program ID, target SKUs, primary requisition
 IDs, and package PO IDs. An answer template with nomination lines, program
 summary, and committee action.

 **Endpoints to pull**: `programs`, `suppliers`, `contracts`, `purchase_orders`,
 `receipts`, `ap/invoices`, `vendor_risk_events`, `budget_snapshots`, `approvals`,
 `purchase_requisitions`.

 **Key joins**: Match POs by `po_id`. Match invoices by `po_id` or `supplier_id`.
 Match receipts by `po_id`. Match risk events by `supplier_id`. Match contracts
 by `contract_id` on the PO. Match requisitions by `requisition_id` on the PO.
 Match budgets by `program_id`.

 **Business rules**: Nomination readiness section in
 [references/business_rules.md](references/business_rules.md). Determine blocker
 codes, readiness status, and nomination decision per line. Compute program
 budget headroom (budget_cap - committed_amount from the program's budget
 snapshot). Assign `next_owner` and `send_to_committee`.

 **Output**: Populate the answer template's `nomination_lines` array (one entry
 per SKU, sorted ascending), `program_summary`, `committee_action`, and
 `package_line_skus`.

 ### Receiving Control Closeout

 **When**: Prompt asks for receiving batch review, dock closeout, or
 received-vs-billed reconciliation for a specific receipt batch.

 **Input payloads**: A receiving memo naming the target batch (receipt ID). An
 answer template with inspection summary, line reconciliation, invoice review,
 financials, decision, supplier risk context, and evidence.

 **Endpoints to pull**: `receipts`, `purchase_orders`, `contracts`, `suppliers`,
 `ap/invoices`, `vendor_risk_events`.

 **Key joins**: Match receipt by `receipt_id`, then join to PO by `po_id`, to
 contract by `contract_id` on PO, to supplier by `supplier_id`, to invoices by
 `po_id`. Risk events by `supplier_id`.

 **Business rules**: Quantity reconciliation, three-way match, exception codes,
 financial calculations in [references/business_rules.md](references/business_rules.md).

 **Output**: Populate inspection_summary from receipt and PO fields.
 For `line_reconciliation`, iterate receipt and PO lines joined by `po_line_id`.
 Compute ordered_qty, received_qty, rejected_qty, billed_qty, short_qty,
 unreceived_billed_qty, and receipt_completion_ratio (to 4 decimals). Check
 contract_price_match. For `invoice_review`, populate invoice status, hold_code,
 and exception codes. Compute `financials` values. Determine batch disposition
 and actor actions. Include all consulted record IDs in `evidence`.

 ### AP Close Desk

 **When**: Prompt asks for payment-hold reconciliation, vendor balance close,
 or AP invoice review for named invoices.

 **Input payloads**: A close memo listing target invoice IDs. An answer template
 with invoice_decisions, vendor_balances, program_summary, payment queues.

 **Endpoints to pull**: `ap/invoices`, `purchase_orders`, `receipts`,
 `ap/payments`, `suppliers`, `programs`, `budget_snapshots`.

 **Key joins**: Match invoices by `invoice_id`. Join to PO by `po_id`, to receipt
 by `receipt_id` on invoice, to supplier by `supplier_id`, to payments by
 `invoice_id`. Programs by `program_id` on PO.

 **Business rules**: AP invoice decision rules and vendor balance reconciliation
 in [references/business_rules.md](references/business_rules.md). Opening balance
 starts at the value given in the memo (often 0.00). Scheduled payments through
 the date window specified in the prompt reduce the close balance.

 **Output**: For each target invoice, compute hold_decision, release_to_payment,
 quantity_billed, quantity_received, quantity_variance, quantity_variance_pct,
 invoice_total, scheduled_payment_amount, net_balance_impact, and reason_codes.
 Aggregate vendor_balances per supplier. Summarize by program. Populate
 payment_hold_queue and payment_release_queue. Compute total_close_balance.

 ### Change Control Decision

 **When**: Prompt asks for change-control decision, contract amendment, or
 modular change request against a named contract.

 **Input payloads**: A change memo (JSON) with memo_id, contract_id, program_id,
 SKU, variant_code, requested quantity, requisition_id, business controls
 (tax rate, budget exposure rules, approval criteria). An answer template with
 contract_check, program_budget_check, approval_check, supplier_risk_check,
 decision, required_actions, and summary.

 **Endpoints to pull**: `contracts`, `programs`, `budget_snapshots`, `approvals`,
 `suppliers`, `vendor_risk_events`, `purchase_orders`, `purchase_requisitions`.

 **Key joins**: Match contract by `contract_id`. Match program and budget by
 `program_id`. Match approvals by `object_id` == requisition_id where
 `object_type` == `requisition`. Match supplier by `supplier_id` on contract.
 Match POs by `contract_id` (exclude cancelled). Risk events by `supplier_id`.

 **Business rules**: Contract headroom, budget headroom, tax computation,
 approval checks, supplier risk, change-control decision flow in
 [references/business_rules.md](references/business_rules.md).

 **Output**: Compute `noncancelled_subtotal` from all non-cancelled POs using
 that contract. Compute headroom, check ceiling_ok. Get budget snapshot for
 program, compute remaining budget, requested total (subtotal + tax at given
 rate), budget_ok, max_quantity_with_current_budget. Find latest approval event
 for the requisition; approval_ok when action is `approved`. Check supplier
 risk: supplier_risk_ok is false only when open severe events exist. Determine
 decision by the priority in business rules. List required actions. Populate
 supporting_ids with included/excluded POs and approval event IDs.

 ### AP Release File

 **When**: Prompt asks for AP release file, exception review, or
 receiving/AP release decisions for a set of POs, receipts, and invoices.

 **Input payloads**: A release packet (JSON) with target POs, receipts, invoices,
 and optionally a chargeback register. An answer template with release_decisions,
 receiving_exceptions, and summary.

 **Endpoints to pull**: `receipts`, `purchase_orders`, `ap/invoices`, `suppliers`,
 `vendor_risk_events`.

 **Key joins**: Match by the target IDs listed in the packet. Join receipts to
 POs by `po_id`, invoices to POs by `po_id` and `receipt_id`.

 **Business rules**: AP release decisions with chargebacks and receiving
 exception codes in [references/business_rules.md](references/business_rules.md).
 The local chargeback register (in the payload packet) is authoritative for
 chargeback amounts and statuses. Never derive chargebacks from API data.

 **Output**: For each target invoice, determine decision
 (release_net_after_approved_chargeback, hold_pending_quality_chargeback,
 hold_missing_receipt), primary_reason, and net_release_amount. For each receipt,
 list exception codes, chargeback_status, and resolution_status. If a PO has no
 receipt in the API, create a synthetic entry with receipt_id
 `MISSING:<po_id>` and resolution_status `missing_receipt`. Aggregate summary
 totals, queues, sources, and followup actions.

 ## Output Conventions

 - **Currency**: All amounts in USD, rounded to 2 decimal places.
 - **Lists**: Treated as sorted sets unless the template specifies ordering.
   Sort ascending by the natural ID field. List field ordering from the
   template takes priority.
 - **Nulls**: Use `null` in JSON for absent values (not the string "null").
 - **Booleans**: Lowercase `true`/`false`.
 - **Integers**: Whole numbers without decimal points.
 - **Strings**: Use the exact values from API records or template allowed-values
   enums. Do not invent string values not present in the template.
 - **Dates**: YYYY-MM-DD format.
 - **Evidence**: When the template requires evidence or source IDs, list every
   consulted record ID (from API and local payloads) as a sorted set.

 ## Common Pitfalls

 - **Not pulling all relevant endpoints**: Pull all endpoints that could contain
   related records, even if the prompt only mentions a few. Cross-references
   often surface unexpected data.
 - **Missing cancelled-PO exclusion**: Always check PO status; cancelled POs do
   not count toward contract usage or nomination readiness.
 - **Receipt time-gating**: Only receipts dated on or before the as_of_date.
   The same applies to invoices and risk events.
 - **Tax handling**: When a task payload specifies a tax rate, use it. Otherwise
   use the tax value from the PO or invoice record directly.
 - **Multiple receipts per PO**: Sum quantities across all receipts for the same
   PO line when reconciling received_qty.
 - **Same-PO duplicate receipts**: When a PO has multiple receipts, check which
   receipt the invoice is linked to via `receipt_id` on the invoice. Exclude
   other same-PO receipts from the in-scope set when the question is about a
   specific receipt batch.
