---
name: reflection-skill-attempt-03
description: Use for ProcureOps benchmark tasks that require preparing JSON procurement, receiving, AP close, change-control, or AP release decisions from task-local payloads plus the shared ProcureOps API.
---

# ProcureOps Decision JSON

## Scope

Use this skill when a task asks for a JSON answer from ProcureOps records. These tasks usually combine:

- A prompt and task-local payload that name target programs, POs, receipts, invoices, requisitions, contracts, or review dates.
- An `answer_template.json` that defines exact output keys, allowed enum values, sorting, precision, and evidence requirements.
- A shared ProcureOps API as the source of truth for operational records.

Return only JSON matching the template. Do not include prose in the answer.

## Environment

1. Use the API base URL from the runner or prompt. The local default is `http://127.0.0.1:8006`.
2. Bypass shell proxies for local calls when needed:

```bash
curl --noproxy '*' -sS http://127.0.0.1:8006/
```

3. The API root lists collections. Typical endpoints:

```text
/programs
/suppliers
/contracts
/items
/purchase_requisitions
/approval_events
/budget_snapshots
/purchase_orders
/receipts
/ap/invoices
/ap/payments
/vendor_risk_events
```

4. Treat API records as authoritative over local memos except where the prompt says a local packet provides task-only records, aliases, chargebacks, or review instructions.

## Standard Workflow

1. Read the prompt, local payloads, and `answer_template.json`.
2. Extract target IDs, review/as-of dates, required sort order, precision, allowed enums, and whether list fields are sets.
3. Query every API collection needed to connect the target records:
   - Program and budget snapshot by `program_id`.
   - Supplier by `supplier_id`.
   - Contract by `contract_id` or `(program_id, supplier_id, sku)`.
   - Requisition and approval events by requisition ID.
   - PO by `po_id`, requisition, program, supplier, or SKU.
   - Receipt by `receipt_id` and by same `po_id` when the task needs same-PO exclusions.
   - AP invoices by `invoice_id`, `po_id`, and `receipt_id`.
   - Payments by `invoice_id` and cutoff date.
   - Vendor risk events by supplier, not only by PO.
4. Join records using stable IDs, not names:
   - PO -> program, supplier, contract, requisition, lines.
   - Invoice -> PO, supplier, receipt, invoice lines, totals, hold code.
   - Receipt -> PO, supplier, warehouse, quantities, inspection state.
   - Contract -> supplier, program, SKU, unit price, ceiling.
   - Approval event -> requisition via `object_id` or equivalent requisition field.
5. Apply as-of dates before deriving evidence IDs unless the template or packet says to review all named records. Exclude future receipts, invoices, approvals, payments, and risk events from as-of evidence.
6. Calculate fields from source records, round only final numeric outputs to the requested precision, then sort arrays exactly as the template requires.
7. Validate that every enum value is from the template and that all required evidence/source ID lists are complete.

## Field Definitions and Calculations

### Quantities

- `ordered_qty`: PO line quantity.
- `received_qty`: matching receipt line quantity; use `0.00` or `0` when no in-scope receipt exists and the template requires a number.
- `rejected_qty`: receipt line `quantity_rejected`; do not infer damage when the memo says no visible damage unless the receipt records a rejection or inspection issue.
- `billed_qty`: invoice line quantity.
- `short_qty_vs_po`: `ordered_qty - received_qty`.
- `unreceived_billed_qty`: `max(billed_qty - received_qty, 0)`.
- `receipt_completion_ratio`: `received_qty / ordered_qty`, rounded to template precision.
- `quantity_variance`: `quantity_billed - quantity_received`.
- `quantity_variance_pct`: `quantity_variance / PO quantity * 100`.

### Money

- Use USD amounts from API records and round to cents unless the template says otherwise.
- `received_goods_value`: `received_qty * PO unit price`.
- `unreceived_goods_value`: `unreceived_billed_qty * PO unit price`.
- Invoice subtotal, freight, tax, and total come from the AP invoice record, not from recomputing unless no total is provided.
- AP close `net_balance_impact`: `invoice_total - scheduled_payment_amount`.
- Supplier close balance: `opening_balance + target invoice totals - scheduled payments through the cutoff`.
- Program budget headroom: `budget_cap - committed_amount` from the budget snapshot or program, as specified.
- Change-control contract ceiling exposure excludes tax and freight: use line subtotal.
- Change-control budget exposure includes line subtotal plus tax; include freight only if the memo provides it.
- `max_quantity_with_current_budget`: floor of `remaining_budget / (unit_price * (1 + tax_rate))` when budget exposure includes tax.

### Contract and Commercial Basis

- `commercial_basis_id` is the matching active contract ID when a contract covers the line; use `null` when no matching contract exists.
- Contract ceiling usage for amendment checks uses non-cancelled POs only. Exclude cancelled POs from `noncancelled_subtotal` and list them separately when requested.
- Contract price match compares invoice/PO unit price with contract unit price.

### Approvals

- Use the latest approval event for the source requisition by event date.
- Only actions explicitly listed as good by the task controls count as approval OK. In the train pattern, `approved` is OK; `submitted`, `returned`, or `escalated` are not.
- Include all approval event IDs for the target requisition when the template asks for supporting IDs.

### Supplier Risk

- Supplier `risk_rating` is context even when no open event exists.
- Open risk events are supplier-wide unless the task narrows them. Do not require `related_object_id` to match the target PO.
- Include events with status `open` or `monitoring` as active risk context when the prompt says open or monitoring.
- Severe supplier risk usually means high-severity open/monitoring events. A watch-rated supplier alone is not a severe open event unless the task says so.

### Receipts and AP Release

- For an invoice tied to a named receipt, use that receipt as in scope even if other same-PO receipts exist.
- Same-PO receipts outside the packet or outside the review date may need `excluded_same_po_receipt_ids`; do not net them into the target invoice unless instructed.
- If no receipt exists for a target PO/invoice, output the template's missing-receipt marker when required, such as `MISSING:<po_id>`.
- Approved chargeback amount: `basis_quantity * unit_cost` from the local chargeback register when the prompt makes it task-local authority.
- Pending chargebacks block release; approved chargebacks reduce the net release amount.
- `net_release_amount`: `invoice_total - approved_chargeback_amount` for release decisions, otherwise `0.00`.

## Decision Rules

### Nomination Readiness

- `ready`: contract/commercial basis exists, no AP hold, receipt evidence is present if required, no active supplier risk blocker, and no late/pending operational blocker.
- `at_risk`: can be conditionally nominated but has clearable issues such as AP hold, supplier watch, or open supplier-risk context.
- `not_ready`: missing contract, missing receipt for billed goods, pending receipt, due-date or approval blocker, or material AP hold requiring clearance.
- Overall readiness is the worst status across nomination lines.
- Committee `next_owner` should reflect the main blocker class. AP holds generally point to `ap_team`; receipt shortages to receiving/quality; budget to program/finance.

### Receiving Closeout

- Keep AP hold when billed quantity exceeds received quantity or PO is partial receipt.
- Use `PRICE_MISMATCH` only when invoice/PO/contract unit prices differ.
- Use `DAMAGE_REJECTION` only for rejected or damaged receipt records, not for memo silence.
- Supplier watch risk can add a risk exception even if the receipt passed.

### AP Close

- Limit all totals to the target invoices only.
- Opening AP balance is task-specific; if the memo says opening balance is zero, do not include other supplier invoices.
- Scheduled payments through the cutoff reduce balances only for the target invoices.
- Approved three-way match plus a scheduled payment is releasable and may produce zero close balance.
- Held or pending-receipt invoices go to the hold queue even if a supplier has other scheduled payments.

### Change Control

- Reject only for actual contract mismatch; otherwise choose the most specific hold decision from budget, approval, and severe supplier-risk blockers.
- Budget blocker exists when requested budget exposure exceeds remaining budget.
- Contract ceiling can pass even when program budget fails because ceiling excludes tax while budget may include tax.
- Required actions should map one-to-one to blockers and omit `none` when any real action exists.

### AP Release

- Release only invoices with in-scope receiving evidence and approved chargeback coverage for the variance.
- Hold missing-receipt invoices even when requester comments mention an alias or generated receipt that is not in the API.
- Hold pending-quality chargebacks until quality review completes.
- Summary release/hold queues follow the invoice-level decisions, not invoice status alone.

## Evidence and Ordering

- Include source record IDs used to make the decision when requested: invoice, PO, receipt, contract, supplier, SKU/item, and risk event IDs.
- Evidence lists should not include records reviewed only as stale notes unless the template has a supporting-only source field.
- Sort IDs lexicographically unless the template says rows are matched by key or ordered by another field.
- Sort invoice decisions by invoice ID and PO line rows by line ID when specified.
- For set fields, de-duplicate values before sorting.

## Common Pitfalls

- Counting future receipts in an as-of packet. A receipt after the review date may be a same-PO exclusion, not evidence.
- Looking for risk events only on the target PO. Supplier-wide open or monitoring events can be required evidence.
- Treating supplier `watch` as an automatic severe risk hold. It is usually context or a conditional blocker unless a severe open event exists.
- Recomputing invoice totals from subtotal/tax and forgetting freight. Prefer the invoice total field.
- Including cancelled POs in contract usage.
- Using all supplier invoices in AP close when the memo limits the slice to named invoices.
- Marking an invoice releasable because AP status is approved while the local chargeback register says quality review is still pending.
- Omitting `null` for missing contract/hold fields where the template requires `null` instead of an empty string.
- Returning narrative text or extra keys outside the template.
