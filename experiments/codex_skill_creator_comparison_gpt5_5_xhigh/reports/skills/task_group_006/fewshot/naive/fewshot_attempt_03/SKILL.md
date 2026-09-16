---
name: procureops-reconcile
description: Solve ProcureOps sourcing, receiving, AP hold/release, payment close, contract-change, budget, and vendor-risk reconciliation tasks. Use when a task references the ProcureOps API, TASK_ENV_BASE_URL, local input/payloads memos, or an answer_template JSON and asks for a JSON operational decision packet.
---

# ProcureOps Reconciliation

## Required Workflow

1. Read the prompt and every file under `input/payloads/`. Treat `answer_template.json` as the required output contract and local memos/packets as the scoping source for target programs, POs, receipts, invoices, requisitions, SKUs, dates, chargebacks, and special exceptions.
2. Query ProcureOps as the operational source of truth. Use the API base URL from `TASK_ENV_BASE_URL` or from the prompt. A deterministic fetch helper is available at [scripts/fetch_procureops_snapshot.py](scripts/fetch_procureops_snapshot.py). From the directory containing this `SKILL.md`, run:

   ```bash
   python scripts/fetch_procureops_snapshot.py --base-url "$TASK_ENV_BASE_URL" --out /tmp/procureops_snapshot.json
   ```

3. Build local indexes by ID before reasoning: supplier, item, program, contract, requisition, PO, receipt, invoice, payment, approval, budget snapshot, and vendor-risk event.
4. Scope tightly. Include only target records named by the prompt/payload unless a calculation requires related records, such as all non-cancelled POs consuming a contract, all payments for target invoices through a close date, or all open/monitoring risk events for a target supplier.
5. Calculate from records, then fill the template exactly. Return only valid JSON, with no prose, comments, Markdown, or trailing commas.

## Endpoint Map

Fetch these read-only endpoints when available:

- `/programs`: `program_id`, owner, budget and status fields.
- `/suppliers`: `supplier_id`, name, status, risk rating, payment terms.
- `/items`: SKU, preferred supplier, standard cost, active flag.
- `/contracts`: contract, supplier, SKU, program, status, price type, unit price, ceiling.
- `/purchase_requisitions`: requisition, program, SKU, quantity, need-by date, requester, status.
- `/purchase_orders`: PO, requisition, contract, program, supplier, status, due date, subtotal/tax/total, line quantities and prices.
- `/receipts`: receipt, PO, supplier, warehouse, status, receipt date, line received/rejected quantities.
- `/ap/invoices`: invoice, PO, receipt, supplier, status, hold code, subtotal/freight/tax/total, billed lines.
- `/ap/payments`: payment status, invoice, supplier, amount, scheduled date.
- `/approvals`: approval events where `object_id` usually joins to a requisition.
- `/budget_snapshots`: program budget cap, committed amount, pending invoice amount, snapshot date.
- `/vendor_risk_events`: supplier risk events with status and severity.

Important joins:

- PO lines join invoice and receipt lines by `po_line_id` and SKU.
- Invoices join POs by `po_id`; `receipt_id` may be null.
- Receipts join POs by `po_id`; a task may scope to a subset of same-PO receipts.
- Payments join invoices by `invoice_id`.
- Approvals join requisitions by `object_id`.
- Budget snapshots and programs join by `program_id`.
- Supplier risk joins by `supplier_id`; use the task date when the prompt says "as of".

## General Calculations

- Round USD amounts to cents. Use numeric JSON values, not strings.
- Prefer API `total`, `subtotal`, `tax`, and `freight` fields when present. Compute missing line amounts as `quantity * unit_price`.
- Sort lists ascending when the template says sorted or set-like. Keep row ordering exactly as the template specifies.
- For date-scoped evidence, ignore records after the as-of or close date unless the local packet explicitly asks for future scheduled items through a later cutoff.
- Treat status values literally. Do not infer paid/released/scheduled equivalence unless the prompt says to.

## Receiving And Invoice Reconciliation

For each scoped PO line:

- `ordered_qty`: PO line quantity.
- `received_qty`: sum scoped receipt line `quantity_received`; use zero when no receipt exists.
- `rejected_qty`: sum scoped receipt line `quantity_rejected`; use zero when absent.
- `billed_qty`: invoice line `quantity_billed`.
- `short_qty_vs_po`: `ordered_qty - received_qty`.
- `unreceived_billed_qty`: `max(billed_qty - received_qty, 0)`.
- `receipt_completion_ratio`: `received_qty / ordered_qty`.
- `received_goods_value`: `received_qty * PO unit_price`.
- `unreceived_goods_value`: `unreceived_billed_qty * PO unit_price`.

Common exception code logic:

- Invoice quantity exceeds receipt when billed quantity is greater than scoped received quantity.
- Partial receipt when received quantity is less than ordered quantity or the PO status indicates a partial receipt.
- Price mismatch when PO, contract, and invoice unit prices do not match under the template's expected basis.
- Damage or inspection exceptions when rejected quantity is positive or receipt status/line inspection shows an inspection hold or failure.
- Supplier watch/risk exceptions when the supplier risk rating is watch or the task asks risk to affect AP disposition.
- Use the template's exact enum labels; do not invent labels.

Typical disposition:

- Keep an invoice on hold when there is no receipt, billed quantity exceeds receipt, pending quality/inspection action, or an unresolved hold code.
- Release when the invoice has a complete three-way match or the only remaining variance is covered by an approved chargeback/netting instruction.
- When no receipt exists for a target PO, emit a missing-receipt evidence row if the template has a receiving-exception section.

## Payment Close And Vendor Balances

For target invoices only:

- `quantity_variance`: billed quantity minus scoped received quantity.
- `quantity_variance_pct`: `quantity_variance / PO ordered_qty * 100`, rounded as the template requires.
- `scheduled_payment_amount`: sum payments for the invoice that match the prompt's cutoff and allowed payment status. For wording such as "payment already scheduled through DATE", count `scheduled` payments through that date and exclude `blocked`.
- `net_balance_impact`: invoice total minus scheduled payment amount.
- Supplier opening balance is the memo value when provided; otherwise derive only if the template asks.
- Supplier close balance is opening balance plus target invoice totals minus counted payments.
- Held totals are invoices whose decision remains hold. Released totals are invoices approved for payment or already scheduled under the prompt's rule.

Reasoning cues:

- Approved invoice plus counted scheduled payment usually releases with reason codes for three-way match and scheduled payment.
- On-hold quantity variance remains hold unless the local packet provides an approved chargeback.
- Pending receipt or null receipt remains hold with a no-receipt reason.

## Sourcing Nomination Readiness

For each package line named by the local memo:

- Use the requisition and PO from the local memo as anchors; verify supplier, SKU, program, quantities, due/need dates, and status through the API.
- The selected supplier normally comes from the target PO; item preferred supplier is supporting context.
- `commercial_basis_id` is the matching contract only when an active contract covers the supplier, SKU, and program, or the target PO names a valid contract.
- Receipt evidence is scoped to the target PO and as-of date.
- Invoice exception IDs are AP invoices tied to the target PO that are on hold, pending receipt, or otherwise exception-status as of the date.
- Risk event IDs are supplier risk events with open or monitoring status as of the date.

Reusable blocker logic:

- `missing_contract`: no active commercial basis for the line.
- `supplier_watch`: supplier risk rating is watch when the template exposes that blocker.
- `open_supplier_risk`: any open or monitoring supplier risk event is relevant.
- `ap_hold`: any scoped AP invoice has a hold code or exception status.
- `pending_receipt`: no receipt evidence or PO/receipt status shows incomplete receiving.
- `late_due_date`: PO due date is later than the requisition need-by date.
- `none`: only when no blockers apply and the template requires a placeholder.

Decision cues:

- Missing contract, missing receipt, or late due-date blockers generally produce a hold.
- Complete contract/receipt evidence with AP or watch-risk exceptions generally produces a conditional nomination.
- No blockers produces nominate/ready.
- Overall program readiness is the worst line readiness: not ready beats at risk, which beats ready.
- Choose the next owner from the blocker with the most immediate clearing action, prioritizing AP holds, missing contract/budget, receiving/quality, program approval, then buyer action.

## Contract Change And Budget Controls

Use the memo's requested quantity, tax rate, contract, SKU, supplier, program, and source requisition. Then:

- Verify contract identity, active status, supplier, SKU, program, price type, unit price, and ceiling.
- Contract usage is the subtotal of non-cancelled POs that consume the contract, excluding cancelled POs.
- `headroom_before_change`: contract ceiling minus current non-cancelled usage.
- `requested_subtotal`: requested quantity times contract unit price.
- `headroom_after_change`: headroom before change minus requested subtotal.
- `ceiling_ok`: true when headroom after change is non-negative and the contract matches.
- Budget remaining is budget cap minus committed amount from the relevant snapshot.
- Requested budget exposure is requested subtotal plus estimated tax, plus freight only when the memo provides freight.
- `budget_after_change`: remaining budget minus requested budget exposure.
- `budget_ok`: true when budget after change is non-negative.
- `max_quantity_with_current_budget`: floor of remaining budget divided by the all-in per-unit budget exposure.
- Use the latest approval event for the source requisition by event date, then event ID. Approval is OK only when the action is in the memo's good-action list or the template says otherwise.
- Supplier watch rating is context only unless the memo/template says it blocks. Open high/severe events block supplier-risk release.

Decision cues:

- Contract mismatch or inactive/nonmatching contract produces contract-mismatch rejection.
- Budget failure and approval failure together produce the combined budget-and-approval hold if that enum exists.
- Single failures use the corresponding hold enum.
- Ready to release only when contract, budget, approval, and supplier-risk checks all pass.

## AP Release With Local Chargebacks

When the local packet includes a chargeback register:

- Treat the register as authoritative for chargeback status, reason, basis quantity, unit cost, and receipt linkage.
- Still use ProcureOps for invoice totals, PO/receipt existence, supplier/program joins, and AP status.
- Chargeback amount is basis quantity times unit cost.
- Approved chargeback: release net amount as invoice total minus approved chargeback amount, unless another scoped blocker remains.
- Pending quality-review chargeback or receipt inspection hold: hold the invoice and report pending chargeback amount.
- No scoped receipt for the target PO: hold missing receipt with zero release amount.
- Receipts on the same PO but outside the packet's receipt IDs are supporting/excluded evidence, not release evidence for the target invoice.
- Build summary queues and totals from the invoice-level release decisions.

For receiving-exception rows:

- Use the scoped receipt ID when present; otherwise use the template's missing-receipt convention if one is implied.
- Add underage quantity when received quantity is less than ordered quantity.
- Add unmatched or AP quantity variance when billed quantity exceeds scoped receipt quantity or the chargeback reason says so.
- Add inspection hold when receipt status, inspection status, or chargeback status shows quality review.
- Map chargeback status and resolution status by meaning using the template's exact allowed labels.

## Final Checks

Before returning the answer:

- Validate the JSON parses.
- Confirm every required top-level and nested key from the template is present.
- Confirm no placeholder strings from the template remain.
- Confirm all calculations use scoped records only.
- Confirm all record IDs came from the task payload or live API, not from prior examples.
- Confirm all amounts, ratios, and percentages use the requested precision.
