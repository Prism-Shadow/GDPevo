---
name: demonstration-skill-attempt-02
description: Solve ProcureOps demonstration benchmark tasks that require reading task-local payloads, querying the ProcureOps API, reconciling procurement/AP/receiving records, and returning only schema-conformant JSON.
---

# ProcureOps Input-Output Skill

Use this skill for tasks that provide local `input/payloads/*` files plus an `answer_template.json`, and ask for a procurement, receiving, AP close, change-control, nomination, or AP release JSON answer using the ProcureOps API.

## Guardrails

- Read only the task prompt, task-local payloads, and `answer_template.json` for the task being solved.
- Use the API as the source of truth for operational records unless the prompt says a local payload supplies a register, exception list, alias, or other non-API evidence.
- Return only the final JSON object. No prose, markdown, comments, or trailing text.
- Preserve all required keys from the template. Sort lists when the template says sorted, alphabetical, ascending, or set-like.
- Round USD amounts to cents unless the template specifies another precision. Round ratios/percentages exactly as specified.

## API Workflow

Base URL is usually provided by the runner; otherwise use `<environment_base_url>`.

Probe the service:

```bash
curl --noproxy '*' -sS "$BASE_URL/"
```

Known collection endpoints:

- `/programs`
- `/suppliers`
- `/items`
- `/contracts`
- `/purchase_requisitions`
- `/approval_events`
- `/budget_snapshots`
- `/purchase_orders`
- `/receipts`
- `/ap/invoices`
- `/ap/payments`
- `/vendor_risk_events`

Fetch full collections and filter locally by IDs from the prompt/payload. Join on these keys:

- `program_id`: programs, budgets, POs, contracts, requisitions
- `supplier_id`: suppliers, POs, invoices, receipts, risk events, payments
- `sku`: items, contract lines, PO lines, receipt lines, invoice lines
- `po_id`: POs, receipts, invoices, risk related objects
- `requisition_id`: POs, requisitions, approval events through `object_id`
- `receipt_id`: receipts and invoice `receipt_id`
- `invoice_id`: invoices and payments
- `contract_id`: contracts and POs

## General Extraction Pattern

1. Read the prompt and local payloads to identify the task type, target IDs, dates, and special local rules.
2. Read `answer_template.json` and use it as the output contract.
3. Pull all relevant API collections, then build indexes by ID.
4. Filter to target records only. Do not include unrelated records in rollups unless a rule explicitly says to compute usage/history across a contract, supplier, or program.
5. Apply date cutoffs such as `as_of`, `review_as_of`, or `close_date`: include records dated on or before the cutoff unless the prompt gives a different horizon, such as payments scheduled through month end.
6. Produce controlled enum values exactly as in the template.
7. Validate JSON syntax before finalizing, for example with `python3 -m json.tool`.

## Core Calculations

- Program headroom: `budget_cap - committed_amount` from the current program or budget snapshot.
- PO line ordered quantity/unit price: use the PO `lines[]` row matching `po_line_id` or `sku`.
- Receipt quantity: sum `quantity_received` for in-scope receipt lines; for a single batch review, use only that receipt.
- Rejected quantity: sum `quantity_rejected` for in-scope receipt lines.
- Invoice billed quantity/unit price: use invoice `lines[]`.
- Quantity variance: `quantity_billed - quantity_received`.
- Quantity variance percent: `quantity_variance / PO ordered quantity * 100`.
- Receipt completion ratio: `received_qty / ordered_qty`.
- Received goods value: `received_qty * PO unit_price`.
- Unreceived billed value: `max(quantity_billed - received_qty, 0) * PO unit_price`.
- Invoice total: prefer invoice `total`; invoice subtotal/freight/tax come from invoice fields.
- Contract price match: invoice or PO unit price equals contract unit price for the matching contract/SKU.
- Scheduled payment amount: sum payments for the invoice that match the prompt horizon and acceptable payment statuses, usually `scheduled` through the requested close date/month end.
- Net balance impact: `invoice_total - scheduled_payment_amount`.
- Chargeback amount: `basis_quantity * unit_cost`, separated by local chargeback status (`approved` versus pending statuses).
- Net release amount: `invoice_total - approved_chargeback_amount` when release is allowed; otherwise `0.00`.

## Nomination Readiness

Use this for sourcing nomination packets with package anchors such as SKUs, requisitions, and POs.

For each package line:

- Selected supplier comes from the package PO supplier.
- Commercial basis is the PO `contract_id`; use `null` if absent.
- Receipt evidence is receipts for the package PO dated on or before `as_of_date`.
- Invoice exceptions are invoices for the package PO dated on or before `as_of_date` with hold-like status or non-null `hold_code`.
- Risk events are supplier events with status `open` or `monitoring` dated on or before `as_of_date`.
- `missing_contract`: no active contract/commercial basis.
- `supplier_watch`: supplier `risk_rating` is `watch`.
- `open_supplier_risk`: any open/monitoring supplier risk event.
- `ap_hold`: invoice status is `on_hold` or there is a hold code other than a pure missing-receipt condition.
- `pending_receipt`: no receipt evidence exists for the package PO as of the cutoff, or the invoice/PO is explicitly pending receipt.
- `late_due_date`: PO `due_date` is later than the source requisition `need_by`.
- If no blockers, use blocker code `none`.

Decision guidance:

- `ready` / `nominate`: no blockers.
- `at_risk` / `conditional_nomination`: only conditional blockers such as supplier watch, open medium/low supplier risk, or AP hold with receipt evidence.
- `not_ready` / `hold`: blocking issues such as missing contract, no receipt, late due date, severe supplier risk, or missing approval.
- Committee queues contain supplier IDs grouped by line decision. Choose `send_to_committee: "yes"` only when at least one line can be nominated or conditionally nominated and no required blocking cleanup prevents review.

## Receiving-Control Reviews

Use this for a target receipt/batch closeout.

- The local memo identifies the receipt ID; the API receipt controls PO, supplier, warehouse, receiver, date, and lines.
- Match the PO by `receipt.po_id`, supplier by `supplier_id`, contract by `po.contract_id`, and invoice by `receipt_id` or same PO when the prompt asks for the tied AP item.
- `INVOICE_QTY_EXCEEDS_RECEIPT`: billed quantity is greater than received quantity.
- `PARTIAL_RECEIPT`: received quantity is less than ordered quantity or PO status is partial receipt.
- `SUPPLIER_WATCH_RISK`: supplier risk rating is `watch` or prompt treats watch as a control exception.
- `PRICE_MISMATCH`: invoice unit price differs from PO or contract unit price.
- `DAMAGE_REJECTION`: rejected quantity is greater than zero or inspection status indicates damage/rejection.
- `NO_EXCEPTION`: only when no exception codes apply.
- Keep invoice on hold when quantity, receipt, price, damage, or supplier-control exceptions remain unresolved.

## AP Close Reconciliation

Use this for a named list of invoices and close balances.

- Target invoices come from the local close memo; ignore non-target invoices in invoice-level decisions and rollups.
- Opening balance is whatever the memo says, often `0.00`.
- For each invoice, use the invoice PO and receipt. If invoice `receipt_id` is null, quantity received is `0.00` for close decision purposes unless the prompt explicitly permits matching other receipts.
- `RELEASE` when the invoice is approved and quantities match the receipt/PO controls.
- `HOLD` when invoice status or hold code indicates no receipt, quantity variance, or another unresolved exception.
- Reason codes:
  - `APPROVED_THREE_WAY_MATCH`: approved invoice, PO, and receipt quantities match.
  - `NO_RECEIPT`: no receipt is attached or invoice status/hold code says pending/no receipt.
  - `QTY_VARIANCE`: billed and received quantities differ.
  - `SCHEDULED_PAYMENT_FOUND`: an eligible payment exists within the prompt horizon.
- Vendor balance: `opening_balance + invoice_total - scheduled_payments`.
- Balance status:
  - `FULLY_SCHEDULED`: close balance is zero because scheduled payments cover the slice.
  - `OPEN_HELD`: supplier has held target invoices.
  - `OPEN_APPROVED`: open balance remains for releasable/approved invoices.
- Program summaries aggregate only target invoices by `program_id`.

## Change-Control Decisions

Use this for contract amendment or modular change requests.

- Local change payload supplies requested quantity, tax-rate rule, contract, supplier, SKU, program, and requisition.
- Contract check:
  - Match the API contract by `contract_id`; verify SKU, supplier, program, and active status.
  - Contract usage is the sum of PO `subtotal` for matching contract POs, excluding cancelled POs.
  - Requested subtotal is `requested_quantity * contract.unit_price`.
  - Headroom before change is `ceiling_amount - noncancelled_subtotal`.
  - Headroom after change is `headroom_before_change - requested_subtotal`.
  - `ceiling_ok` is true when headroom after change is non-negative.
- Budget check:
  - Use the current budget snapshot for the program.
  - Remaining budget is `budget_cap - committed_amount`.
  - Requested tax is `requested_subtotal * tax_rate_percent / 100`.
  - Requested total is subtotal plus tax plus freight only if the payload provides freight.
  - Budget after change is `remaining_budget - requested_total`.
  - `max_quantity_with_current_budget` is the floor of remaining budget divided by per-unit total cost including the payload tax rule.
- Approval check:
  - Collect approval events where `object_id` is the source requisition.
  - Latest event is by latest `event_date`, with event ID as a deterministic tie-breaker.
  - Approval is OK only if latest action is in the payload's good actions, usually `approved`.
- Supplier risk:
  - Open event IDs are supplier risk events with status `open` or `monitoring`.
  - Severe open events are usually open/monitoring events with `severity: high`.
  - Supplier watch rating can be context-only when the payload says so; severe open risk or supplier hold status blocks release.
- Decision:
  - Use `release_amendment` only when contract, budget, approval, and supplier risk checks are all OK.
  - Use the most specific hold enum for failed checks, such as budget, approval, supplier risk, or combined budget and approval.
  - Use `reject_contract_mismatch` for wrong/missing contract, supplier, SKU, or program.

## AP Release / Chargeback Files

Use this for receiving/AP release packets with local target IDs and chargeback registers.

- Local packet target IDs define the program, POs, receipts, and invoices in scope.
- Use API records for PO, receipt, invoice amounts/statuses; use local chargeback register for chargeback status and amount.
- For each target invoice:
  - In-scope receipts are target receipt IDs whose `po_id` matches the invoice PO.
  - Excluded same-PO receipt IDs are API receipts for the invoice PO that are not in the target receipt list.
  - If no in-scope receipt exists, decision is `hold_missing_receipt` and primary reason `no_receipt_on_po`.
  - If a pending quality chargeback or inspection-hold receipt exists, decision is `hold_pending_quality_chargeback`.
  - If an approved chargeback resolves the quantity/AP variance, decision is `release_net_after_approved_chargeback`.
- Receiving exception codes:
  - `Underage Quantity`: received quantity is less than PO ordered quantity, or local chargeback reason says underage.
  - `Severe Unmatched Quantity`: material underage/unmatched quantity remains; include when the local register or receipt evidence indicates a significant underage.
  - `Inspection Hold`: receipt status is `inspection_hold`.
  - `AP Quantity Variance`: invoice billed quantity exceeds received quantity, especially when the local chargeback reason says AP quantity variance.
- Missing receipt rows use a synthetic receipt ID such as `MISSING:<po_id>` when the template pattern requires a receiving exception row.
- Summary totals are sums over target invoices only. Follow-up actions should map directly from unresolved conditions: missing receipt, pending quality review, approved chargeback netting, or duplicate/out-of-scope receipt handling.

## Output Checks

Before final answer:

- Confirm every target ID requested in the payload appears in the appropriate output section or is explicitly represented as missing/excluded if the template expects that.
- Confirm no non-target invoice/PO/receipt leaked into target-only queues or rollups.
- Confirm all enum values exactly match `answer_template.json`.
- Confirm `null` is used only where the template permits it.
- Confirm numeric precision and list ordering.
- Return only JSON.
