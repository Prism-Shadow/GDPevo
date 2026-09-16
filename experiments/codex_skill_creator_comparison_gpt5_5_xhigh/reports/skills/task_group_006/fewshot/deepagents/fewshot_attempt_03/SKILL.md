---
name: procureops-packet-reconciliation
description: Use for ProcureOps API task packets that ask for JSON-only sourcing nomination readiness, receiving closeout, AP invoice hold/release, AP close/vendor-balance reconciliation, or change-control decision files. Guides reading local input/payloads answer_template and memo/packet files, fetching ProcureOps endpoints from TASK_ENV_BASE_URL, joining supplier/item/program/requisition/contract/purchase-order/receipt/invoice/payment/approval/budget/risk records, computing rounded USD and quantity reconciliations, and emitting template-exact JSON.
---

# ProcureOps Packet Reconciliation

## Core Rules

- Read the prompt, `input/payloads/answer_template.json`, and every other file under `input/payloads/` before doing calculations.
- Treat the API as source of truth for operational records. Treat local payloads as the source for task scope, target IDs, special business controls, local chargeback excerpts, alias notes, and requested output template.
- Return only the JSON object requested by the template. Do not include Markdown, comments, or explanatory prose.
- Follow the template over this skill when they disagree: key names, required fields, enum values, list ordering, and precision all come from the template.
- Use native JSON numbers for numeric fields. Round USD amounts to cents, percentages and ratios to the precision named by the template, and sort any list described as sorted or set-like.
- Filter dated evidence using the task's as-of, close, review, or memo date when one is provided. Include records on or before that date unless the template says otherwise.

## Fetching The API

Allowed endpoints are usually `/manifest`, `/suppliers`, `/items`, `/programs`, `/contracts`, `/purchase_requisitions`, `/purchase_orders`, `/receipts`, `/ap/invoices`, `/ap/payments`, `/approvals`, `/budget_snapshots`, and `/vendor_risk_events`.

Endpoint responses are wrapped as `{"count": n, "results": [...]}`. Unwrap `results` before indexing records.

Optional helper: run [scripts/fetch_procureops.py](scripts/fetch_procureops.py) to cache every allowed endpoint:

```bash
python skill/scripts/fetch_procureops.py "$TASK_ENV_BASE_URL" -o /tmp/procureops_snapshot.json
```

Build indexes by the ID fields actually present, especially `supplier_id`, `sku`, `program_id`, `contract_id`, `requisition_id`, `po_id`, `receipt_id`, `invoice_id`, `payment_id`, `event_id`, and `snapshot_id`.

## Record Joins

- Purchase orders connect program, supplier, requisition, contract, ship-to, due date, status, subtotal, tax, total, and line-level `sku`, `quantity`, `unit_price`, `line_id`.
- Receipts connect to POs through `po_id`; receipt lines provide `po_line_id`, `sku`, `quantity_received`, `quantity_rejected`, and `inspection_status`.
- AP invoices connect to POs through `po_id` and sometimes to receipts through `receipt_id`; invoice lines provide `po_line_id`, `sku`, `quantity_billed`, and `unit_price`.
- Contracts connect supplier, program, SKU, price type, unit price, status, and ceiling amount.
- Approval events connect to the controlled object through `object_id`; use the latest event by `event_date` when deciding current approval state.
- Budget snapshots connect to programs; prefer the snapshot requested by the task date when available.
- Vendor risk events connect to suppliers. Treat open or monitoring events dated on or before the as-of date as active evidence. Supplier `risk_rating` is separate context from open event evidence.
- Payments connect to invoices and suppliers. Count only payments with the status/date window requested by the prompt or template.

## Shared Calculations

- Received quantity: sum matching receipt line `quantity_received` for the scoped receipt or PO.
- Rejected quantity: sum matching receipt line `quantity_rejected`.
- Billed quantity: sum matching invoice line `quantity_billed` for the scoped invoice and PO line.
- Short quantity vs PO: `ordered_qty - received_qty`.
- Unreceived billed quantity: `max(0, billed_qty - received_qty)`.
- Receipt completion ratio: `received_qty / ordered_qty` when ordered is nonzero.
- Quantity variance: `billed_qty - received_qty`.
- Quantity variance percent: `quantity_variance / ordered_qty * 100`.
- Received goods value: `received_qty * PO unit_price`.
- Unreceived goods value: `unreceived_billed_qty * PO unit_price` unless the template defines another basis.
- Invoice total fields should come from the invoice record. Recompute only when the task asks for chargeback, budget, or contract exposure.
- Chargeback amount: `basis_quantity * unit_cost`, grouped by chargeback status when the local packet provides a register.
- Contract usage: sum subtotals of non-cancelled POs for the scoped contract. Exclude cancelled POs unless the task says otherwise.
- Contract headroom before change: `ceiling_amount - noncancelled_subtotal`; after change subtract the requested subtotal.
- Requested subtotal: requested quantity times the applicable contract or PO unit price.
- Requested tax: requested subtotal times the tax rate in the local memo.
- Requested budget total: requested subtotal plus requested tax, plus freight only when the local memo supplies freight or says to include it.
- Program remaining budget: use the budget snapshot or program `budget_cap - committed_amount`.
- Max quantity with current budget: floor of remaining budget divided by per-unit total exposure, after any fixed freight the memo says to include.

Use `Decimal` or equivalent exact arithmetic for money and round at output boundaries, not after every intermediate operation.

## Packet Workflows

### Sourcing Nomination Readiness

Use local memo anchors to identify package requisitions, POs, and SKUs. For each package line:

- Select the supplier from the scoped PO unless the task defines a different nomination source.
- Use an active matching contract as `commercial_basis_id`; use null when no active basis exists.
- Receipt evidence is receipt IDs for the scoped PO dated on or before the as-of date.
- Invoice exceptions are AP invoices for the scoped PO dated on or before the as-of date whose status or hold code indicates an unresolved exception.
- Risk evidence is active vendor-risk event IDs for the selected supplier.
- Derive blocker codes from missing contract, supplier watch rating, active supplier risk, on-hold AP invoice, missing receipt evidence, pending-receipt invoice state, and PO due date later than the linked requisition need-by date.
- Use `none` only when no blockers exist. Map no blockers to ready/nominate, remediable blockers to at-risk/conditional, and release-blocking commercial, receipt, due-date, or severe-risk issues to not-ready/hold.

For the committee summary, group supplier IDs by line decision, set overall readiness to the worst line readiness, and choose the next owner from the dominant unresolved blocker using template owner values.

### Receiving-Control Closeout

Scope to the target receipt batch. Join its receipt, PO, supplier, contract, invoice, and active supplier-risk records.

- Produce one reconciliation row per PO line in template order.
- Compare PO, contract, and invoice unit prices for price-match fields.
- Use invoice status, hold code, receipt status, PO status, quantity variance, rejected quantity, and supplier risk to choose the template exception codes.
- Keep AP on hold when billed quantity exceeds received quantity, receipt is partial or under inspection, price mismatch exists, or active supplier risk/hold context requires review.
- Financial exposure should separate goods received from goods billed but not received, then copy invoice subtotal, freight, tax, and total from the invoice.
- Evidence lists should contain only record IDs and local payload filenames actually used.

### AP Close And Vendor Balances

Scope to the target invoice IDs named by the memo. Do not include other invoices from the same supplier or program unless the template explicitly asks.

- For each invoice, join PO, supplier, receipt evidence, and scheduled payments.
- Use linked receipt quantity when present; use zero when the invoice has no receipt and no scoped receipt evidence.
- Hold when there is no receipt, a positive quantity variance, or the invoice status/hold code says it is on hold. Release only when the invoice is approved and three-way quantity evidence matches.
- Scheduled payment amount is the sum of qualifying payments for that invoice through the date window named by the prompt.
- Net balance impact is invoice total minus scheduled payment amount.
- Reason codes should be controlled template values, sorted alphabetically.
- Vendor balances start from the opening balance in the memo, then add scoped invoice totals and subtract qualifying scheduled payments.
- Program summaries and hold/release queues are aggregates of scoped invoice decisions only.

### Change-Control Decision Files

Use the local change memo for requested quantity, variant code, tax rules, exposure rules, approval-good actions, and supplier-risk controls. Join contract, supplier, program/budget snapshot, approvals, risk events, and POs.

- Reject contract mismatch when the memo contract, supplier, program, SKU, status, or price basis cannot support the request.
- Ceiling check uses active contract unit price and non-cancelled existing PO subtotals for that contract.
- Budget check uses the requested exposure rule from the memo. If remaining budget cannot cover the requested total, compute the maximum affordable quantity using the same exposure rule.
- Approval check uses the latest approval event for the source object. Treat only memo-listed good actions as approval-ok.
- Supplier-risk check should block only for inactive/blocked suppliers or severe active events unless the memo/template says watch status itself is a blocker.
- Choose the combined decision enum that exactly matches the active blockers, list required actions for those blockers, and set `ready_to_release` true only when contract, budget, approval, and supplier-risk checks all pass.

### AP Release Or Hold With Chargebacks

Use local target IDs and chargeback registers to scope the review. API PO, receipt, and AP records remain authoritative for operational status; local chargeback registers are authoritative for chargeback status and basis amounts.

- For each target invoice, join its PO and all target receipt IDs on the same PO. If no scoped receipt exists, use an explicit missing-receipt row if the template expects receiving exceptions.
- List same-PO receipts outside the packet as excluded when the template asks for excluded receipt IDs.
- Approved chargebacks reduce the net release amount. Pending quality chargebacks hold the invoice. Missing receipt evidence holds the invoice.
- For receiving exceptions, mark underage when received quantity is below ordered quantity, AP quantity variance when billed quantity exceeds received quantity, inspection hold when receipt status or inspection status requires quality review, and severe unmatched quantity when an underage receipt is material or the template/local register describes it as severe.
- Summary totals are sums of approved chargebacks, pending chargebacks, and net releases across target invoices only.
- Classify source lists carefully: API records and local chargeback registers are authoritative; alias notes and requester comments are supporting-only unless the template elevates them.

## Final JSON Check

Before responding, verify:

- Every required key from `answer_template.json` is present and no unexpected prose is included.
- Each enum value is copied exactly from the template.
- Numeric precision matches the template.
- IDs and lists are scoped to target records only and sorted when required.
- Dates respect the as-of or review date.
- The output parses as JSON.
