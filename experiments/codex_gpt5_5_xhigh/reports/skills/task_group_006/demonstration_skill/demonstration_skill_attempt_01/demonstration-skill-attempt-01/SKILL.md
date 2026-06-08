---
name: demonstration-skill-attempt-01
description: Solve ProcureOps procurement, receiving, AP close, change-control, and AP release benchmark tasks by combining task-local payload anchors with the ProcureOps API and returning exact JSON matching the provided answer template.
---

# ProcureOps JSON Reconciliation

Use this skill when a task asks for a ProcureOps sourcing, receiving, invoice/AP, budget, supplier-risk, approval, or change-control packet and provides an `input/payloads/answer_template.json`.

## Workflow

1. Read the task prompt, every file under `input/payloads/`, and the answer template. Extract:
   - target IDs: program, SKU, requisition, PO, receipt, invoice, contract, supplier, packet/change IDs
   - dates: `as_of`, close date, review date, memo date, payment cutoff
   - any local-only registers or business controls, such as chargebacks, tax rate, freight treatment, approval-good actions, or alias notes
2. Query the ProcureOps API. Use the runner-provided base URL when present; otherwise use `http://127.0.0.1:8006`. First call `/` to confirm endpoint names. In this task group the collections are:
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
3. Treat API records as source of truth for operational data. Treat task-local payloads as source of truth only for the task scope, requested controls, chargeback registers, target aliases, and explicitly stated business rules.
4. Build ID indexes from each collection's `results`. Join through PO IDs first, then requisition, contract, supplier, receipt, invoice, program, and SKU as needed.
5. Return only JSON. Match the template keys, enum strings, ordering, and numeric precision exactly. Use sorted ascending order for ID lists unless the template says rows are matched by a key.

Practical curl pattern:

```bash
curl --noproxy '*' -sS "$BASE/purchase_orders"
```

## Common Calculations

- Currency: USD numbers rounded to cents unless the template says otherwise.
- Quantities: keep integers when the template uses integers; use one or two decimal places only when requested.
- Budget headroom: `budget_cap - committed_amount`.
- PO line value: `quantity * unit_price`.
- Invoice total: prefer `invoice.total`; otherwise `subtotal + freight + tax`.
- Receipt quantity for a PO line: sum matching receipt lines in scope unless a single target receipt is specified.
- Quantity variance: `quantity_billed - quantity_received`.
- Quantity variance percent: `(quantity_variance / PO ordered quantity) * 100`.
- Contract usage: sum `subtotal` for POs with the target `contract_id`, excluding status `cancelled`.
- Contract headroom after change: `ceiling_amount - noncancelled_subtotal - requested_subtotal`.
- Budget exposure for change requests: line subtotal plus estimated tax; include freight only when the local memo provides freight.
- Maximum quantity under current budget: `floor(remaining_budget / (unit_price * (1 + tax_rate)))`.
- Chargeback amount: `basis_quantity * unit_cost`, split by local chargeback status.

## Dates And Filtering

- For "as of" evidence, include only records with relevant record dates on or before that date.
- Open supplier risk normally means `status` is `open` or `monitoring`; exclude `closed`. Also exclude events dated after the relevant as-of date.
- Latest approval event is the event for the object with the latest `event_date`; use the event ID as a tie-breaker if needed.
- For payment close work, reduce balances only for payments explicitly in scope, usually `status: scheduled` with `scheduled_date` on or before the cutoff. Do not count blocked payments as reducing AP balance.

## Nomination Readiness Packets

Use local package memos to identify the package line anchors, then use the API for facts.

For each line:

- selected supplier: target PO supplier, falling back to item preferred supplier only if no PO is available.
- commercial basis: PO `contract_id` if a matching active contract exists; otherwise `null`.
- receipt evidence: receipts for package PO IDs with `receipt_date <= as_of`.
- invoice exceptions: AP invoices for package PO IDs dated on or before `as_of` whose status/hold code indicates an exception, such as `on_hold`, `pending_receipt`, `QTY_VARIANCE`, `PRICE_VARIANCE`, `NO_RECEIPT`, or supplier review.
- risk events: supplier risk events with `status in {open, monitoring}` and `event_date <= as_of`.
- blocker codes:
  - `missing_contract`: no active matching contract or PO has no contract.
  - `supplier_watch`: supplier `risk_rating` is `watch`.
  - `open_supplier_risk`: open/monitoring risk events exist.
  - `ap_hold`: an exception invoice is on hold.
  - `pending_receipt`: no in-scope receipt by the as-of date or invoice/PO indicates receipt is pending.
  - `late_due_date`: PO due date is later than the requisition `need_by` date.
  - `none`: only when no other blocker exists.

Readiness mapping: no blockers means `ready`/`nominate`; soft risk or AP-only blockers mean `at_risk`/`conditional_nomination`; missing contract, pending receipt, or late due date means `not_ready`/`hold`. Overall readiness is the worst line status. Committee supplier lists come from each line's decision bucket.

## Receiving Closeout Packets

For a target receipt/batch:

- Join receipt -> PO -> supplier -> invoice(s) with matching receipt or PO -> contract -> risk.
- Line reconciliation fields:
  - `ordered_qty` from PO line quantity.
  - `received_qty` and `rejected_qty` from receipt line.
  - `billed_qty` from target invoice line.
  - `short_qty_vs_po = ordered_qty - received_qty`.
  - `unreceived_billed_qty = max(billed_qty - received_qty, 0)`.
  - `receipt_completion_ratio = received_qty / ordered_qty`, rounded as template requests.
  - Price match is true when PO, invoice, and contract unit prices match.
- Exception codes:
  - `INVOICE_QTY_EXCEEDS_RECEIPT` when billed quantity is greater than received quantity.
  - `PARTIAL_RECEIPT` when received quantity is less than ordered quantity or PO status is partial.
  - `SUPPLIER_WATCH_RISK` when the supplier is watch-rated or has open/monitoring risk.
  - `PRICE_MISMATCH` when invoice price differs from PO/contract price.
  - `DAMAGE_REJECTION` when any rejected quantity or damage/variance inspection is present.
  - `NO_EXCEPTION` only when no other exception exists.
- Hold the invoice for quantity, receipt, inspection, or risk exceptions; release only clean three-way matches.

## AP Close And Vendor Balances

For named invoices only:

- Join invoice -> PO -> supplier -> receipt(s) -> payment(s).
- Use invoice status and hold code directly. Hold invoices with `on_hold`, `pending_receipt`, missing receipt, or quantity variance. Release approved clean matches.
- `scheduled_payment_amount` is the in-scope scheduled payment amount for the invoice.
- `net_balance_impact = invoice_total - scheduled_payment_amount`.
- Reason codes:
  - `APPROVED_THREE_WAY_MATCH`: approved invoice with no quantity variance.
  - `NO_RECEIPT`: no receipt quantity in scope.
  - `QTY_VARIANCE`: billed quantity differs from received quantity.
  - `SCHEDULED_PAYMENT_FOUND`: counted scheduled payment exists.
- Vendor balances use opening balance from the memo, usually zero for the slice:
  - `close_balance = opening_balance + target invoice totals - counted scheduled payments`.
  - `held_invoice_total` sums held decisions.
  - `releasable_invoice_total` sums release decisions.
  - `FULLY_SCHEDULED` when close balance is zero; `OPEN_HELD` when held total remains; otherwise `OPEN_APPROVED`.
- Program summaries aggregate only the target invoices.

## Change-Control Decision Files

For amendment or modular-change requests:

- Validate the memo's contract, program, supplier, SKU, and requisition against API records. If they do not match, use `reject_contract_mismatch`.
- Contract check:
  - Use contract `status`, `price_type`, `unit_price`, and `ceiling_amount`.
  - `noncancelled_subtotal` is all non-cancelled PO subtotals under the contract.
  - `requested_subtotal = requested_quantity * contract.unit_price`.
  - `ceiling_ok = headroom_after_change >= 0`.
- Program budget check:
  - Use the program's budget snapshot.
  - `remaining_budget = budget_cap - committed_amount`.
  - Compute requested tax from the memo tax rate.
  - `budget_ok = budget_after_change >= 0`.
- Approval check:
  - Use approval events for the source requisition.
  - `approval_ok` is true only when the latest action is in the memo's approval-good actions, usually `approved`.
- Supplier risk check:
  - Include open/monitoring event IDs.
  - Severe open events are open/monitoring events with high/severe severity.
  - Watch rating is context only unless the memo says it is a blocker; severe open risk is a blocker.
- Decision precedence:
  - contract mismatch -> `reject_contract_mismatch`
  - budget and approval blockers -> `hold_for_budget_and_approval`
  - budget only -> `hold_for_budget`
  - approval only -> `hold_for_approval`
  - severe supplier risk only -> `hold_for_supplier_risk`
  - no blockers -> `release_amendment`

## AP Release And Chargeback Packets

When a local packet has target PO/receipt/invoice IDs and a chargeback register:

- The local chargeback register is authoritative for chargeback status and amount.
- Scope only the target invoice IDs. For each invoice, include target receipt IDs that belong to the invoice's PO. Same-PO receipts not listed in the packet are `excluded_same_po_receipt_ids`.
- If no target receipt exists for a PO, create the missing receipt row requested by the template, commonly `MISSING:<po_id>`.
- Release decisions:
  - approved chargeback -> `release_net_after_approved_chargeback`; net release is invoice total minus approved chargeback amount.
  - pending quality chargeback or inspection hold -> `hold_pending_quality_chargeback`; net release is zero.
  - no receipt -> `hold_missing_receipt`; net release is zero.
- Receiving exception codes:
  - `Underage Quantity`: received quantity is less than PO ordered quantity.
  - `Severe Unmatched Quantity`: material underage or unmatched quantity variance, especially when the task's local chargeback exists for that variance.
  - `Inspection Hold`: receipt status is inspection hold.
  - `AP Quantity Variance`: invoice billed quantity exceeds received quantity and the chargeback reason indicates AP quantity variance.
- Summary totals are sums over target invoices only. Source labels should distinguish authoritative sources such as ProcureOps AP/PO/receipt records and local chargeback registers from supporting notes or stale aliases.
