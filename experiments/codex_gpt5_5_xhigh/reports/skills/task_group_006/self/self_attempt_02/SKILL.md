---
name: procureops-reconciliation
description: Use this skill whenever the user asks for a ProcureOps procurement, receiving, AP invoice, payment-hold, sourcing nomination, contract-change, budget, supplier-risk, or strict JSON decision file based on the ProcureOps API and local input payloads. This is especially important when the task mentions purchase orders, receipts, AP invoices, contracts, requisitions, budget snapshots, approval events, chargebacks, vendor risk, controlled reason codes, or an answer_template.json.
---

# ProcureOps Reconciliation SOP

Use this skill to solve ProcureOps tasks that combine a task-local memo or packet with the live ProcureOps API and require a strict JSON answer. The API is the system of record; local payloads define scope, date, requested IDs, business rules, and output schema.

## First Pass

1. Read the prompt, every task-local payload referenced by the prompt, and the answer template before querying records.
2. Extract the scope anchors:
   - as-of or close date
   - target program, PO, receipt, invoice, requisition, contract, supplier, SKU, batch, packet, or chargeback IDs
   - explicit inclusion/exclusion rules
   - enum values, ordering requirements, rounding precision, and required keys from the template
3. Use the ProcureOps base URL provided by the environment or runner. If a prompt mentions local service URLs, still prefer the provided environment access details for the actual run.
4. Confirm the live endpoint list with `GET /`. Public endpoint names use underscores, for example `/ap_invoices` and `/payments`; prompts may use prose such as `/ap/invoices`, but the live endpoint is `/ap_invoices`.
5. Fetch complete endpoint lists when needed and filter locally by IDs. The result shape is usually `{ "count": n, "results": [...] }`.

Do not use local environment source files, generated answers, judge APIs, or evaluator feedback.

## Endpoint Map

- `programs`: `program_id`, `owner`, `budget_cap`, `committed_amount`, status, priority, cost center.
- `budget_snapshots`: dated budget records with `snapshot_id`, `program_id`, `budget_cap`, `committed_amount`, `pending_invoice_amount`, `currency`, `snapshot_date`.
- `suppliers`: `supplier_id`, `name`, `status`, `risk_rating`, payment terms, region.
- `items`: `sku`, description, category, UOM, standard cost, preferred supplier.
- `contracts`: `contract_id`, `program_id`, `sku`, `supplier_id`, `status`, `price_type`, `unit_price`, `ceiling_amount`, effective and expiry dates.
- `purchase_requisitions`: `requisition_id`, `program_id`, `sku`, `quantity`, `status`, `need_by`, priority, requester.
- `purchase_orders`: `po_id`, `program_id`, `supplier_id`, `contract_id`, `requisition_id`, `status`, `due_date`, `subtotal`, `tax`, `total`, and `lines[]` with `line_id`, `sku`, `quantity`, `unit_price`.
- `receipts`: `receipt_id`, `po_id`, `supplier_id`, `status`, `receipt_date`, warehouse, packing slip, receiver, and `lines[]` with `po_line_id`, `sku`, `quantity_received`, `quantity_rejected`, `inspection_status`.
- `ap_invoices`: `invoice_id`, `po_id`, `receipt_id`, `supplier_id`, `status`, `hold_code`, `subtotal`, `freight`, `tax`, `total`, and `lines[]` with `po_line_id`, `sku`, `quantity_billed`, `unit_price`.
- `payments`: scheduled or posted payments with `payment_id`, `invoice_id`, `supplier_id`, `amount`, `scheduled_date`, `status`.
- `approval_events`: events keyed by `object_id` and `object_type`; sort by `event_date` then `event_id` to find the latest action.
- `vendor_risk_events`: `event_id`, `supplier_id`, `related_object_id`, `status`, `severity`, `event_type`, `event_date`.

## Scope Discipline

Local packets often name a narrow review slice while the API contains additional records for the same PO, supplier, contract, SKU, or program. Keep these roles separate:

- **Target records** drive decisions and totals only when their IDs are in scope or the template explicitly asks for all records in a broader slice.
- **Supporting records** provide context, such as supplier name, contract basis, budget snapshot, risk state, or same-PO receipt exclusions.
- **Out-of-scope same-PO records** should not silently change invoice totals, release queues, or chargeback totals. Include them only in explicit fields such as excluded receipt IDs or supporting evidence.
- **As-of dates** filter dated evidence. Use records dated on or before the as-of date unless the task says to include a future cutoff, such as scheduled payments through month-end.

When a template says list fields are sets, sort IDs ascending and remove duplicates before output.

## Common Joins

- Join invoice -> PO by `po_id`.
- Join invoice line -> PO line by `po_line_id` and `sku`.
- Join invoice -> receipt by `receipt_id` when present; otherwise use task-scoped receipt IDs for the same PO only if the packet says they are in scope.
- Join receipt -> PO by `po_id`; receipt quantities live under `receipt.lines[]`.
- Join PO -> requisition by `requisition_id`.
- Join PO or requisition -> program by `program_id`.
- Join PO or contract -> supplier by `supplier_id`.
- Join PO -> contract by `contract_id`; a null or missing contract can be a commercial-basis blocker.
- Join approval events by `object_id`, often a requisition ID.
- Join supplier risk by `supplier_id`; use `related_object_id` only to explain context unless the template narrows risk by object.

## Calculations

Round currency amounts to cents at the end of each calculation. Match non-currency precision from the template.

### Receiving and Invoice Reconciliation

- `ordered_qty`: PO line quantity.
- `received_qty`: sum in-scope receipt line `quantity_received` for the matching PO line/SKU.
- `rejected_qty`: sum in-scope receipt line `quantity_rejected`.
- `billed_qty`: invoice line `quantity_billed`.
- `short_qty_vs_po`: `ordered_qty - received_qty`.
- `unreceived_billed_qty`: `max(billed_qty - received_qty, 0)`.
- `receipt_completion_ratio`: `received_qty / ordered_qty` when ordered quantity is nonzero.
- `received_goods_value`: received quantity multiplied by PO unit price unless the template directs otherwise.
- `unreceived_goods_value`: unreceived billed quantity multiplied by the applicable PO or invoice unit price; when the prices match, either source gives the same exposure.
- `contract_price_match`: compare PO or invoice unit price to the contract unit price for the same commercial basis.

Useful exception mapping:

- invoice hold `NO_RECEIPT` or null invoice receipt with no in-scope receipt -> `NO_RECEIPT`, `pending_receipt`, or `hold_missing_receipt` depending on the template.
- billed quantity greater than received quantity -> quantity variance, partial receipt, or invoice quantity exceeds receipt.
- PO not fully received -> partial receipt unless the template limits the exception to invoice quantity.
- invoice/PO price different from contract price -> price mismatch.
- receipt status or inspection status showing hold/rejection -> receiving or quality hold exception.

### AP Close and Vendor Balances

- Use only target invoices for invoice decisions, vendor balances, program summaries, and hold/release queues unless the memo says otherwise.
- Treat opening balance as the memo specifies; many close-slice tasks set it to zero.
- Scheduled payments reduce supplier close balance only when they match target invoice IDs and fall within the requested cutoff date.
- `quantity_variance`: billed quantity minus received quantity. Use `0.00` received quantity when no receipt exists.
- `quantity_variance_pct`: quantity variance divided by PO quantity, then converted to percent.
- `scheduled_payment_amount`: sum in-scope scheduled payment amounts for the invoice.
- `net_balance_impact`: invoice total minus scheduled payment amount.
- Supplier close balance: opening balance plus target invoice totals minus in-scope scheduled payments.
- Hold decisions should follow invoice status, hold code, receipt evidence, and quantity match. Approved three-way matches release; missing receipt or quantity variance holds unless the template supplies another controlled outcome.

### Contract Change and Budget Checks

Separate contract exposure from budget exposure:

- Contract ceiling exposure is usually line subtotal before tax and freight.
- Program budget exposure follows the memo; if it says subtotal plus estimated tax, exclude freight unless the memo provides freight.
- Existing contract usage should exclude cancelled POs when instructed. Include noncancelled POs with the target `contract_id`.
- `headroom_before_change`: contract ceiling minus included existing PO subtotal.
- `requested_subtotal`: requested quantity times contract unit price.
- `headroom_after_change`: headroom before change minus requested subtotal.
- `remaining_budget`: budget cap minus committed amount from the selected snapshot or program record.
- `requested_tax`: requested subtotal times tax rate.
- `requested_total`: requested subtotal plus requested tax, plus freight only if instructed.
- `budget_after_change`: remaining budget minus requested total.
- `max_quantity_with_current_budget`: floor of remaining budget divided by unit price plus applicable per-unit tax/freight burden.

For approvals, sort approval events by event date then event ID. The latest action is acceptable only if it appears in the memo's approved/good action list. A requisition status such as converted or approved is useful context, but approval-event instructions in the memo should govern the output.

Decision priority for change files:

1. Reject contract mismatch if the target contract, SKU, supplier, or program does not align.
2. Hold for severe open supplier risk if the template treats severe supplier events as blocking.
3. Hold for budget and/or approval when those checks fail.
4. Release only when contract, budget, approval, and supplier-risk checks are all acceptable.

### Supplier Risk

- Supplier `risk_rating` of `watch` is often context, not automatically a blocker.
- Open or monitoring vendor-risk events are active for readiness context; closed events are historical.
- Severe open events are stronger blockers when the template asks for severe events.
- Apply as-of dates to event dates when the task is as-of controlled.

### Receiving/AP Release With Local Chargebacks

Some release packets include a local chargeback register that is not in the API. Treat it as an authoritative source only for chargeback IDs, reasons, basis quantities, unit costs, and chargeback statuses when the template says so.

- Chargeback amount: basis quantity times unit cost.
- Approved chargebacks can net against invoice release amounts.
- Pending quality-review chargebacks keep the invoice or receipt on hold when the packet ties them to the target invoice/receipt.
- Missing receipt decisions apply when the target invoice has no receipt and no packet-scoped receipt resolves the PO.
- For same-PO receipts not included in the packet scope, list them as excluded only when the template asks; do not use them to clear the target invoice.

Common release-file outcomes:

- `release_net_after_approved_chargeback`: invoice can release after subtracting approved chargebacks.
- `hold_missing_receipt`: no receipt evidence is in scope for the invoice/PO.
- `hold_pending_quality_chargeback`: receipt or local chargeback still requires quality disposition.

## Readiness and Decision Coding

Use the template's enums exactly. When selecting controlled codes:

- Missing or null contract basis -> missing contract or commercial-basis blocker.
- Supplier watch rating -> supplier watch context; use an open risk blocker only for active risk events.
- Invoice on hold, quantity variance, or missing receipt -> AP hold / pending receipt / quantity variance codes.
- Due date before the as-of date with unresolved delivery evidence -> late due date where that code exists.
- No blocker field should use `none` only when no other blocker codes apply.

Overall readiness should reflect the worst relevant line or required check:

- `ready`: all required evidence and controls clear.
- `at_risk`: proceed only conditionally or with nonblocking risk/context.
- `not_ready`: a blocking hold, missing required evidence, failed approval, failed budget, severe risk, or missing receipt prevents release.

## Evidence Ledger

Before writing JSON, keep a small ledger of the records used:

- task payload filenames reviewed
- API endpoint record IDs used for each decision
- target IDs included in totals
- same-PO or same-supplier records deliberately excluded
- latest approval event and active risk events
- local chargeback IDs and statuses, if any

Populate evidence fields from this ledger. This prevents accidental inclusion of broader API context in target-only totals.

## Output Checklist

Before finalizing:

1. Confirm every required top-level key and nested key exists.
2. Confirm all enum strings exactly match the template.
3. Sort all ID lists and rows as specified, commonly by invoice ID, PO line ID, supplier ID, program ID, SKU, or ascending ID.
4. Round USD to two decimals, ratios and percentages to the requested precision.
5. Use JSON numbers for amounts and quantities unless the template explicitly asks for strings.
6. Use `null` only where the template allows it.
7. Return only the JSON object, with no prose or Markdown.
