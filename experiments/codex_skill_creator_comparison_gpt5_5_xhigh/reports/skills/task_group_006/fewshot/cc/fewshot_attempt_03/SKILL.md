---
name: procureops-json-reconciler
description: Solve ProcureOps packet tasks that combine a local memo/packet with the shared ProcureOps API and require exact JSON output for nomination readiness, receiving closeout, AP close, change-control, or release/hold decisions. Use this whenever a prompt asks for a structured JSON answer from ProcureOps records, especially when the packet names target IDs, a date slice, or an answer template.
---

# ProcureOps Packet Reconciler

Use this skill for ProcureOps tasks where the answer is a strict JSON object built from a local packet plus the shared ProcureOps API.

## Core Workflow

1. Read the prompt, all packet files under `input/payloads/`, and the answer template before you look at the API.
2. Treat the packet as the scope definition and the API as the source of truth. If they conflict, trust the API for record facts and the packet for task scope.
3. Identify the task family: nomination readiness, receiving closeout, AP close, change-control, or AP release/hold.
4. Start from the IDs named in the packet, then walk outward through linked records: program, supplier, item, requisition, contract, PO, receipt, invoice, payment, approval, budget, and vendor risk.
5. Use `/manifest` first only when you need a quick inventory of anchor IDs or record counts.
6. Build the output to match the template exactly. Preserve key names, nesting, enum values, rounding, and list ordering.
7. Return JSON only. No prose, markdown, or extra wrapper text.

## Common Endpoints

- Program and budget: `/programs`, `/budget_snapshots`
- Supplier and risk: `/suppliers`, `/vendor_risk_events`
- Sourcing and receiving: `/purchase_requisitions`, `/purchase_orders`, `/receipts`
- AP: `/ap/invoices`, `/ap/payments`
- Approval and contract context: `/approvals`, `/contracts`, `/items`

## Output Rules

- Follow the template schema literally. If it says `required_keys`, `allowed_values`, `precision`, or `ordering`, treat that as binding.
- Sort lists exactly when asked. If the template says set semantics, dedupe first, then sort.
- Round money to cents and keep intermediate precision until the final writeout.
- Use `null` only when the template allows it.
- Do not invent IDs. Only use record IDs that are supported by the packet or the API.
- Keep all derived totals internally consistent across sections.

## Common Calculations

- `short_qty_vs_po = ordered_qty - received_qty`
- `unreceived_billed_qty = billed_qty - received_qty`
- `receipt_completion_ratio = received_qty / ordered_qty`
- `quantity_variance = quantity_billed - quantity_received`
- `quantity_variance_pct = quantity_variance / po_qty * 100`
- `received_goods_value = received_qty * unit_price`
- `unreceived_goods_value = (ordered_qty - received_qty) * unit_price`
- `close_balance = opening_balance + invoice_total - scheduled_payments`
- `net_balance_impact = invoice_total - scheduled_payment_amount`
- `requested_subtotal = requested_quantity * unit_price`
- `requested_tax = requested_subtotal * tax_rate`
- `requested_total = requested_subtotal + requested_tax`
- `budget_after_change = remaining_budget - requested_total`
- `headroom_before_change = ceiling_amount - noncancelled_subtotal`
- `headroom_after_change = headroom_before_change - requested_subtotal`
- `approved_chargeback_amount = basis_quantity * unit_cost` when the chargeback is approved
- `pending_chargeback_amount = basis_quantity * unit_cost` when the chargeback is pending review
- `net_release_amount = invoice_total - approved_chargeback_amount` when release is allowed

## Family-Specific Notes

### Nomination readiness packets

- Build one line per package SKU and match evaluator keys exactly, usually by `sku`.
- Trace each line from requisition to PO to receipt to invoice to supplier risk.
- Classify the line by unresolved blockers. Use the narrowest blocker set that is still true.
- Mark a line `hold` when it cannot proceed, `conditional_nomination` when it can move only with a remaining condition, and `nominate` only when the line is clear.
- Set program readiness from the strictest unresolved line: one held line generally makes the program not ready; residual but manageable issues usually make it at risk.
- Populate committee action buckets from the line decisions and make `next_owner` the function that can clear the dominant blocker.

### Receiving closeout packets

- Reconcile ordered, received, rejected, and billed quantities line by line.
- Use the receipt and invoice records to decide whether the batch is accepted, partially held, or requires recount or quality follow-up.
- Derive exception codes from the actual mismatch type: quantity shortfall, invoice quantity over receipt, supplier risk, or damage/inspection issues.
- Compute financials from the received and unreceived quantities, then reconcile invoice subtotal, freight, tax, and total.

### AP close packets

- Limit the analysis to the target invoices named in the packet.
- Compare invoice totals to scheduled payments through the requested close date.
- Aggregate vendor balances by supplier, not by invoice.
- Keep hold and release queues aligned with the invoice decisions.
- Sum program summaries from the same target slice only.

### Change-control packets

- Validate contract status, ceiling usage, program budget impact, approval state, and supplier risk before choosing a release decision.
- Release only when contract, budget, approval, and supplier risk checks all pass.
- If anything blocks release, choose the narrowest hold reason allowed by the template and list the required actions that clear it.
- Exclude cancelled POs or other packet-specified exclusions from usage totals.

### AP release/hold packets

- Limit scope to the packet's target PO, receipt, and invoice IDs.
- Separate approved chargebacks from pending ones.
- For each invoice, decide whether the release is net of an approved chargeback or should stay on hold for missing receipt or pending quality work.
- Record receiving exceptions only for receipts that are truly in scope.
- Keep the release and hold summary consistent with the invoice-level decisions and the chargeback register.

## Practical Checks

- If the packet uses alias language such as a family of generated IDs that is not present in the shared API, use the actual shared IDs named in the packet.
- If the template asks for evidence or source IDs, include only records you actually used.
- If a field is a list of IDs, sort by the key the template names; if no key is named, use a stable ascending sort.
- Before finalizing, verify that every required field is present and every enum value comes from the template, not from the memo prose.
