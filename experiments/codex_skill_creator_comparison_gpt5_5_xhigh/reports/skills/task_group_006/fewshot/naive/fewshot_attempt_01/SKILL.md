---
name: solve-procureops-json
description: Solve ProcureOps operational reconciliation tasks that require JSON-only answers from a task prompt, local payload files, an answer template, and the shared ProcureOps API. Use for procurement sourcing readiness, receiving/AP variance closeout, AP payment holds, change-control budget/approval checks, supplier risk checks, chargeback net-release files, and similar tasks involving suppliers, items, programs, contracts, purchase requisitions, purchase orders, receipts, AP invoices, payments, approvals, budget snapshots, or vendor risk events.
---

# ProcureOps JSON Solver

## Operating Rules

Read the prompt, every file under `input/payloads/`, and the answer template before calling the API. Treat local payloads as the scope, business-rule overrides, and target ID source; treat the API as authoritative for operational records. Return only the JSON object requested by the template.

Do not reuse IDs, dates, names, amounts, or conclusions from prior examples. Derive every output value from the current task's prompt, payloads, template, and API responses.

## API Snapshot

Use the base URL supplied by the task runner or prompt. Fetch full endpoint lists and build local indexes by ID:

```bash
BASE="$TASK_ENV_BASE_URL"
for path in \
  suppliers items programs contracts purchase_requisitions purchase_orders receipts \
  ap/invoices ap/payments approvals budget_snapshots vendor_risk_events; do
  curl -sS "$BASE/$path"
done
```

The endpoints return JSON objects with `results` arrays. If an endpoint path contains a slash, keep that exact path. Join records by the ID fields present in the current task:

- Programs and budget snapshots: `program_id`
- Suppliers and vendor risk events: `supplier_id`
- Contracts: `contract_id`, and cross-check `program_id`, `supplier_id`, and `sku`
- Purchase requisitions: `requisition_id`
- Purchase orders: `po_id`, `program_id`, `supplier_id`, `contract_id`, `requisition_id`, and line `sku`/`line_id`
- Receipts: `receipt_id`, `po_id`, `supplier_id`, and line `po_line_id`/`sku`
- AP invoices and payments: `invoice_id`, `po_id`, `receipt_id`, and `supplier_id`
- Approvals: `object_id` with `object_type`, usually requisition approvals

## General Workflow

1. Extract target scope from the prompt and payloads: task ID, as-of or close date, program IDs, PO IDs, receipt IDs, invoice IDs, requisitions, contracts, suppliers, SKUs, quantities, tax rules, opening balances, aliases, chargeback rows, and any allowed controlled values.
2. Fetch all ProcureOps endpoints once. Filter records to the target scope plus directly linked records. Include same-PO or same-supplier records only when the template or business logic asks for exceptions, risk context, balances, or excluded evidence.
3. Build one normalized work table per target line or invoice. Keep the source IDs beside each computed value so evidence lists and queues can be generated without re-searching.
4. Compute with exact arithmetic, then round only output amounts to the template precision. Use cents for USD, quantity percentages as requested, and deterministic sorting for every set/list field.
5. Fill the template exactly. Do not add narrative fields. Validate required keys, enum values, null handling, and list ordering before final output.

## Common Calculations

- Budget headroom or remaining budget: `budget_cap - committed_amount`.
- Requested subtotal: `requested_quantity * contract_or_po_unit_price`.
- Requested tax: `requested_subtotal * tax_rate_percent / 100`.
- Requested total: subtotal plus tax, plus freight only when the task payload says to include freight and provides the freight amount.
- Max quantity under current budget: floor of `remaining_budget / (unit_price * (1 + tax_rate))`, adjusted if freight is fixed and included.
- Contract usage: sum non-cancelled PO subtotals for the target contract unless the payload gives a different rule. Track cancelled POs separately when asked.
- Contract headroom: `ceiling_amount - noncancelled_subtotal`; after change subtract requested subtotal before tax/freight.
- Received goods value: `sum(received_qty * PO unit_price)` for in-scope lines.
- Unreceived goods value: `sum(max(ordered_qty - received_qty, 0) * PO unit_price)` or, for billed exposure, `max(billed_qty - received_qty, 0) * invoice_or_po_unit_price` as the template specifies.
- Receipt completion ratio: `received_qty / ordered_qty`.
- Quantity variance: billed minus received. Quantity variance percent: variance divided by PO ordered quantity times 100.
- Scheduled payment amount: sum payments for the target invoice that count under the prompt's date and status rule; use zero when no qualifying payment exists.
- Net balance impact: invoice total minus qualifying scheduled payments.
- Chargeback amount: `basis_quantity * unit_cost`, grouped by invoice and status from the local chargeback register.
- Net release amount: invoice total minus approved chargebacks; use zero for held invoices.

## Decision Patterns

Use template enums exactly. These patterns are reusable defaults; override them when the prompt or payload states a stricter rule.

**Sourcing readiness**

- A line has a missing-contract blocker when no active, matching contract supports the PO line or requested SKU/supplier/program.
- A pending-receipt blocker applies when no in-scope receipt exists by the as-of date or the invoice/PO is explicitly pending receipt.
- A late-due-date blocker applies when the PO due date is later than the requisition need-by date.
- `ap_hold` applies to AP invoices that are on hold; pending-receipt invoices should use the receipt blocker when the template separates those concepts.
- `supplier_watch` applies to watch-rated suppliers when the template treats watch as a blocker or context flag.
- Open supplier risk means supplier risk events with status `open` or `monitoring` as of the review date, unless the task narrows the status set.
- Use ready/at-risk/not-ready from the blockers: no blockers is ready; soft supplier/AP/risk context is at risk; missing contract, missing receipt, failed approval, failed budget, severe supplier risk, or late due dates usually make the item not ready.

**Receiving and invoice variance**

- Reconcile each PO line to receipt lines and invoice lines by `po_line_id` and `sku`.
- Flag invoice quantity exceeding receipt when billed quantity is greater than received quantity.
- Flag partial receipt when received quantity is below ordered quantity or the PO status indicates partial receipt.
- Flag price mismatch when PO, contract, and invoice unit prices do not agree where a contract exists.
- Flag damage or inspection rejection when receipt rejected quantity is positive or receipt/line inspection status indicates a hold or variance.
- Keep an invoice on hold when unresolved quantity, receipt, price, inspection, or supplier-risk exceptions remain. Release only when the template's release conditions and record statuses are satisfied.

**AP close and vendor balances**

- Work only the invoice IDs named by the task. Do not include other supplier invoices in slice balances unless the prompt says to.
- Use invoice status and receipt match to set hold/release decisions. Approved three-way matches release; on-hold, pending-receipt, no-receipt, or quantity-variance cases hold.
- Add reason codes from observed conditions, not prose: approved match, no receipt, quantity variance, scheduled payment found, or the template's equivalent values.
- Group vendor balances by supplier. Opening balance comes from the memo/prompt; invoice totals and scheduled payments come only from in-scope invoices/payments.
- Program summaries group by program ID and should reconcile to invoice decisions and total close balance.

**Change-control release checks**

- Confirm the contract matches the requested contract, supplier, SKU, and program and is active. Reject or hold on mismatch according to the template.
- Use budget snapshot values when present; otherwise use program budget fields if the task permits.
- Approval state is the latest approval event for the source object by event date, with ties resolved deterministically by event ID. Approval is good only when the latest action is in the payload's allowed-good-action list.
- Supplier risk is acceptable when the supplier is active and there are no disqualifying open severe events under the task's rule. Treat watch ratings as context if the payload says watch is not itself a hold.
- Decision and required actions should be the direct combination of failed checks: budget failure, approval failure, supplier-risk failure, contract mismatch, or release when all checks pass.

**AP release with chargebacks**

- For each target invoice, join its PO, invoice, in-scope receipts, and local chargebacks. Use same-PO API receipts outside the payload receipt list only as excluded or supporting context when requested.
- Approved quantity or AP-quantity chargebacks allow release of the invoice net of approved chargeback amount.
- Pending quality chargebacks or inspection-hold receipts should hold the invoice with zero net release.
- Missing receipt on the invoice PO should hold the invoice and emit the template's missing-receipt placeholder when required.
- Receiving exception codes come from receipt status, line inspection/rejection, under-receipt versus PO quantity, billed-versus-received variance, and local chargeback reason/status.
- Summary totals must equal the sums of the release-decision rows.

## Output Validation

Before finalizing:

- Check that top-level keys exactly match the requested template.
- Sort lists that represent sets; preserve explicit template order only where requested.
- Use `null` instead of empty strings when the template permits a missing linked record.
- Include evidence/source IDs only for records actually used in the calculation.
- Recompute summary totals from detail rows after rounding row amounts.
- Ensure the final response contains JSON only, with no Markdown fences or explanation.
