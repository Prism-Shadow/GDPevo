---
name: procureops-json-reconciliation
description: Solve ProcureOps procurement, receiving, AP, budget, approval, supplier-risk, and change-control tasks that require schema-exact JSON outputs from the ProcureOps API plus task-local input payloads.
---

# ProcureOps JSON Reconciliation

Use this skill when a task asks for a procurement/receiving/AP/control packet from the ProcureOps API and requires returning only JSON matching a task-local template.

## Ground Rules

- Treat the task prompt, `input/payloads/*`, and live ProcureOps API records as the only task evidence.
- The API is the system of record for operational records: programs, suppliers, items, requisitions, contracts, POs, receipts, invoices, payments, approvals, budgets, and vendor-risk events.
- Use local payloads for target IDs, chargeback/register excerpts, memo-specific tax/freight rules, controlled enums, and output schema. Do not let a memo override an API record unless it is explicitly a local-only control source.
- Never use judge endpoints, evaluator files, prior answers, reports, notes, runs, or generated skills.
- Final output must be a single JSON value when requested: no prose, no Markdown, no comments.

## API Access Pattern

1. Read the prompt, the answer template, and every relevant file under `input/payloads/`.
2. Get the API root with `GET /` and use the endpoint names it returns. In this environment the public collection endpoints are typically:
   - `/programs`
   - `/suppliers`
   - `/items`
   - `/contracts`
   - `/purchase_requisitions`
   - `/purchase_orders`
   - `/receipts`
   - `/ap_invoices`
   - `/payments`
   - `/approval_events`
   - `/budget_snapshots`
   - `/vendor_risk_events`
3. Fetch whole collections and filter locally by IDs from the packet. Responses are shaped as `{ "count": number, "results": [...] }`.
4. Build lookup maps by durable IDs:
   - `program_id`, `supplier_id`, `sku`, `contract_id`, `requisition_id`, `po_id`, `receipt_id`, `invoice_id`, `payment_id`, `event_id`, `snapshot_id`.
5. Use exact endpoint names from the root. If a prompt mentions slash-style aliases like `/ap/invoices` or `/ap/payments`, confirm against `GET /`; the collection endpoints may be underscore-style.

## Core Joins

- Program: join `programs` and `budget_snapshots` by `program_id`.
- Supplier: join suppliers by `supplier_id`; add vendor-risk events by `supplier_id`, and sometimes by `related_object_id` when the task wants PO-specific risk context.
- Item: join by `sku`; `preferred_supplier_id` is context, not automatically the selected supplier if the PO/contract says otherwise.
- Requisition: join POs by `requisition_id`; approvals by `approval_events.object_id == requisition_id`.
- Contract: join by `contract_id`; also verify `program_id`, `supplier_id`, and `sku` when a task asks for contract fit.
- PO: join receipts and invoices by `po_id`; line quantities/prices live under `po.lines`.
- Receipt: join to PO by `po_id`; receipt lines carry `quantity_received`, `quantity_rejected`, `po_line_id`, `sku`, and `inspection_status`.
- AP invoice: join to PO by `po_id`, supplier by `supplier_id`, receipt by `receipt_id` when present, and payments by `invoice_id`.
- Payment: filter by `invoice_id`; apply the task's cutoff date and payment-status wording before reducing balances.

## Date And Scope Discipline

- Use the review/as-of/close date from the prompt or packet.
- Include receipts, invoices, approvals, budget snapshots, and vendor-risk events only when they are in scope for that date if the task says "as of" or gives a close cutoff.
- For risk, active events usually mean `status` in `open` or `monitoring`; closed events are context only unless the template asks for all history.
- For approvals, choose the latest event by `event_date` and then stable ID ordering if needed. Approval is OK only when the latest action is in the task's allowed good actions, often `approved`.
- When the packet warns that requested legacy/generated IDs are absent, use the available IDs named in the packet and keep stale/alias notes as supporting-only evidence if the template asks.

## Quantity And Money Calculations

- Ordered quantity: sum matching `po.lines[].quantity` for the SKU/line in scope.
- Received quantity: sum matching receipt-line `quantity_received` across in-scope receipts.
- Rejected quantity: sum matching receipt-line `quantity_rejected`.
- Billed quantity: sum matching invoice-line `quantity_billed`.
- Short quantity vs PO: ordered minus received, normally floored at zero unless the template wants signed variance.
- Unreceived billed quantity: billed minus received, normally floored at zero for exception quantities.
- Quantity variance: billed minus received; keep signed when a template asks for variance.
- Quantity variance percent: divide quantity variance by PO ordered quantity, then multiply by 100; round to the template's precision.
- Receipt completion ratio: received divided by ordered; round to the template's precision, often 4 decimals.
- Goods value: quantity times the relevant unit price. Use PO, contract, or invoice unit price according to the field name.
- Invoice totals: prefer API `subtotal`, `freight`, `tax`, and `total` values. Remember `total` can include freight in addition to subtotal and tax.
- Round USD amounts to cents as numbers, not strings. Use the template's required precision for ratios and percentages.

## Contract And Budget Checks

- Contract fit requires matching `contract_id`, `program_id`, `supplier_id`, and `sku`, plus acceptable `status`.
- Contract unit price is `contracts.unit_price`; compare PO and invoice line prices against it when a price-match flag or variance code is requested.
- Contract ceiling usage should sum PO `subtotal` for the same contract, excluding cancelled POs unless the task explicitly says otherwise.
- Contract headroom before change: `ceiling_amount - noncancelled_subtotal`.
- Requested subtotal: requested quantity times contract unit price.
- Headroom after change: headroom before change minus requested subtotal.
- Budget remaining: `budget_cap - committed_amount` from the relevant budget snapshot unless the template defines another basis.
- Requested tax: requested subtotal times the packet's tax rate. Include freight only when the memo/payload explicitly provides freight for budget exposure.
- Requested total: requested subtotal plus requested tax plus included freight.
- Budget after change: remaining budget minus requested total.
- Max quantity with current budget: floor the budget available divided by per-unit cost including required tax/freight treatment.

## AP Close And Release Logic

- Restrict AP close tasks to the target invoice IDs from the packet; do not let same-supplier non-target invoices leak into the slice.
- Opening balance may be specified locally. If the memo says opening balance is `0.00`, use that for the target slice.
- Scheduled payment amount: sum payments tied to the target invoice that meet the task's date cutoff and status rule. Do not count blocked or out-of-window payments unless instructed.
- Net balance impact: invoice total minus scheduled payment amount.
- Supplier close balance: opening balance plus target invoice totals minus qualifying scheduled payments.
- Release only when the invoice is approved/releasable and quantity, receipt, supplier-risk, and inspection conditions pass under the template.
- Hold for missing receipts, pending receipt status, quantity variance, inspection hold, pending quality chargeback, supplier hold/review, or unresolved severe risk when those are in scope.
- Local chargeback registers are authoritative only for their listed chargeback amounts/statuses. Approved chargebacks can net against invoice release; pending quality chargebacks usually keep the invoice on hold.
- Net release amount: invoice total minus approved chargeback amount; do not subtract pending chargebacks into a release amount unless the template says to.

## Readiness And Decision Codes

Use the template's controlled enums exactly. Common decision dimensions:

- Missing commercial basis: no matching active contract or required contract ID.
- Supplier watch: supplier has a watch/high risk rating. Treat as context-only if the memo says watch rating alone is not a blocker.
- Open supplier risk: open or monitoring risk events in scope; severe/high open events are stronger blockers.
- AP hold: target invoice status/hold code blocks release.
- Pending receipt: no in-scope receipt or PO remains unreceived when receipt evidence is required.
- Late due date: PO due date has passed as of the review date and receipt/release is still incomplete.
- None: use only when no blocker code applies; do not mix `none` with real blockers.

When deciding queue placement:

- Release queue: IDs with all required controls satisfied.
- Hold queue: IDs with any unresolved blocker.
- Conditional queue: IDs that can proceed only after named clearances.
- Sort queue/list fields ascending unless the template says lists are sets.

## Evidence And Output Hygiene

- Preserve every required key from the template, even when a value is `null`, `0`, `false`, or an empty list.
- Use the template's required `task_id` or literal values exactly.
- Use booleans for boolean fields, numbers for money/quantities, and `null` for missing nullable IDs/codes.
- Sort deterministic lists: IDs ascending, line rows by `po_line_id`, invoices by `invoice_id`, suppliers by `supplier_id`, programs by `program_id`, or as specified.
- Include source/evidence IDs only from records actually used. Keep local payload filenames or local source labels only when the schema asks for them.
- Validate the final answer with a JSON parser before submitting. Check for trailing prose, wrong enum capitalization, stringified numbers, missing required keys, and accidental extra narrative fields.

## Common Pitfalls

- Do not infer receipt completion from PO status alone; sum actual receipt lines.
- Do not assume `invoice.receipt_id` proves a valid three-way match; compare quantities and line SKUs.
- Do not use future-dated receipts, invoices, approvals, or risk events in an as-of packet.
- Do not include cancelled POs in contract ceiling usage unless the task explicitly asks for all POs.
- Do not treat all supplier risk events as blockers; closed events and watch ratings may be context only depending on the memo.
- Do not include same-supplier or same-program records outside the target IDs in close-slice tasks.
- Do not invent missing receipt IDs from comments. If the packet says a named alias family is absent, use the generated/shared IDs it provides.
- Do not output explanations when the prompt says "Return only JSON."
