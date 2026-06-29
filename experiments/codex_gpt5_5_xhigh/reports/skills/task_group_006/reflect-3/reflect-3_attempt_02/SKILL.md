---
name: reflect-3
description: Use this skill for ProcureOps procurement, receiving, AP close, AP release, sourcing nomination, contract amendment, budget, supplier-risk, purchase-order, receipt, invoice, payment, and chargeback reconciliation tasks. It is especially useful when the user provides a local memo or packet plus a ProcureOps API and asks for strict JSON matching a template.
---

# Reflect-3 ProcureOps Reconciliation

Use this workflow when a task asks for a controlled ProcureOps decision file or reconciliation JSON. The recurring pattern is: a local prompt and payload define scope and business rules, while the ProcureOps API supplies operational records.

## Source Precedence

1. Read the prompt, answer template, and every task-local payload before querying data.
2. Treat the answer template as the contract for field names, enum values, nullability, ordering, and rounding.
3. Treat local memos or packets as authoritative for scope, target IDs, review/as-of dates, special business rules, chargeback registers, stale-alias notes, and locally supplied control assumptions.
4. Treat the ProcureOps API as authoritative for live program, supplier, item, requisition, contract, PO, receipt, invoice, approval, budget, payment, and vendor-risk facts.
5. If a local note says old aliases are absent from the shared environment and provides generated IDs, use the generated IDs. Do not invent missing legacy IDs.
6. Do not expand a task's target package merely because other historical records share a requisition, contract, supplier, or SKU. Use same-object records only when the template asks for context such as excluded same-PO receipts, contract usage, payment schedules, or supporting evidence.

## API Habits

- Use the environment-provided ProcureOps base URL. If the prompt names localhost but the task environment provides a remote base, use the environment base.
- Check the root endpoint when endpoint names are uncertain. In this environment, public endpoints may use underscores, such as `ap_invoices` and `purchase_orders`, even when prompt prose uses slash-style names.
- Query by the narrowest known ID first: invoice ID, PO ID, receipt ID, contract ID, requisition ID, supplier ID, program ID, or snapshot ID.
- Endpoint filters are not uniform. If a broad filter returns nothing, follow links from records you already have and query by concrete IDs.
- Build a small linked-record map: target invoice -> PO -> program, supplier, contract, receipts, payments; target receipt -> PO, invoice, supplier, risk; contract -> noncancelled POs; requisition -> approval events; program -> budget snapshot.
- When an as-of or review date is present, date-scope operational evidence. Do not use later records as positive evidence unless the task's review date includes them or the field explicitly asks for exclusions/context.

## Output Conventions

- Return only the requested JSON object. No prose, markdown, or comments.
- Use the exact `task_id` or required value from the template.
- Sort ID lists ascending unless the template gives a different order. Treat set-like fields as sets.
- Use `[]` for empty lists and `null` for missing scalar IDs or nullable scalar fields.
- Round USD amounts to cents. Round quantities, ratios, and percentages exactly as the template specifies.
- Preserve API status strings and controlled enum spellings exactly.
- For evidence or source lists, include source categories or record IDs that materially support the answer. Do not list the answer template itself as a business source unless explicitly asked.

## Core Calculations

### Quantity Reconciliation

- `quantity_variance` is billed quantity minus received quantity.
- When no receipt exists, use received quantity `0.00` if the template asks for a numeric quantity.
- `quantity_variance_pct` is the variance divided by the PO quantity, multiplied by 100, then rounded as specified.
- Receipt completion is received quantity divided by PO quantity.
- Short quantity versus PO is ordered quantity minus accepted received quantity, adjusted for rejected quantity only if the template says to.

### Invoice, Payment, and Balance

- Use invoice `total` for invoice-level close and release totals.
- Scheduled payments through the task's cutoff date reduce the supplier close balance and the invoice net balance impact.
- If an invoice is fully scheduled, its close balance impact is zero even though the invoice total is still reported.
- For AP close reason codes, use the most specific cause. A `NO_RECEIPT` condition should not also receive a generic `QTY_VARIANCE` reason unless the template separately requires both.
- An approved three-way match requires an approved/releasable invoice, matching billed and received quantities, and no active hold condition.

### Chargeback Netting

- A local chargeback register is authoritative for approved or pending chargeback amounts when the task includes one.
- Approved chargebacks reduce the net release amount: `invoice_total - approved_chargeback_amount`.
- Pending quality chargebacks keep the invoice on hold; report the pending amount and set net release to zero unless the template says otherwise.
- A missing receipt is an invoice-level hold. Only create a synthetic receiving-exception row for a missing receipt if the template clearly supports rows without real receipt IDs.

### Contract and Budget

- Contract ceiling exposure uses line subtotal before tax and freight.
- Existing contract usage excludes cancelled purchase orders.
- `headroom_before_change` is contract ceiling minus included noncancelled subtotal.
- `headroom_after_change` subtracts the requested subtotal from the before-change headroom.
- Program remaining budget is budget cap minus committed amount, unless the task explicitly defines another basis.
- Budget exposure includes requested line subtotal plus estimated tax when the memo says so; include freight only if the memo provides or instructs it.
- `budget_after_change` is remaining budget minus requested total.
- `max_quantity_with_current_budget` is the floor of available budget divided by per-unit budget exposure, including tax when tax is in budget exposure.

### Approvals

- Use the latest approval event by event date for the specified source object.
- Only actions listed by the local memo or template as good actions make approval OK.
- A submitted, routed, or pending event is not an approval unless the task explicitly treats it as one.

### Supplier Risk

- Use supplier status and risk rating from the supplier record.
- Include open or monitoring supplier-risk events as of the task date; exclude closed events from open-event lists.
- Supplier watch rating can be important context and may populate a supplier-risk exception code when the template offers one.
- Do not turn watch rating alone into a hold when the local business rule says watch is context only. Severe open events can create a risk hold when the template distinguishes severe events.

## Decision Patterns

- Release invoices only when the operational records and any local chargeback or quality register allow release.
- Keep invoices on hold for missing receipts, unresolved AP holds, pending quality chargebacks, missing required approvals, budget failures, contract mismatches, or severe supplier-risk blocks.
- For no-receipt invoices, prefer the specific no-receipt decision/reason over a generic quantity variance.
- For accepted partial receipts with approved chargebacks, release the invoice net of the approved chargeback when the template offers that decision.
- For inspection-hold receipts with pending quality chargebacks, hold for quality review even if the AP ledger status is approved.
- For amendment or change-control decisions, combine blockers. If both budget and approval fail while contract and supplier risk pass, use the combined budget-and-approval hold enum when available.
- Count blockers from the actual failed gates that affect release readiness, not from contextual warnings.

## Common Pitfalls

- Do not use local source files from the environment implementation. Use the public API and task-local payloads only.
- Do not assume all endpoints accept `program_id` or other broad filters.
- Do not treat cancelled POs as contract usage.
- Do not include future receipts or invoices as as-of evidence.
- Do not add every same-requisition PO to a scoped package just because it shares the SKU.
- Do not double-code `NO_RECEIPT` as `QTY_VARIANCE` unless the task explicitly asks for all mathematical variances as reason codes.
- Do not block solely for supplier watch if the local rules say watch is context only.
- Do not release a ledger-approved invoice when the local packet has a pending quality chargeback for the target receipt.
- Do not ignore duplicate same-PO receipts when the template has an exclusion field; list out-of-scope same-PO receipt IDs there.
