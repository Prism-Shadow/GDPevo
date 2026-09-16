# ProcureOps Playbook

## Shared record map
- `programs`: program ownership, status, and program identity.
- `suppliers`: supplier identity, active status, and risk rating.
- `items`: SKU and item identity.
- `contracts` and `purchase_orders`: ceilings, usage, quantities, unit prices, and cancellation state.
- `purchase_requisitions` and `approvals`: approval history and latest approval state.
- `receipts`: ordered-versus-received evidence, shortages, rejection, and inspection state.
- `ap/invoices` and `ap/payments`: invoice status, holds, scheduled payments, totals, and release queues.
- `budget_snapshots`: current budget cap, committed amount, and remaining budget.
- `vendor_risk_events`: open and severe supplier-risk context.

## Shared calculations
- `receipt_completion_ratio = received_qty / ordered_qty`
- `quantity_variance = billed_qty - received_qty`
- `quantity_variance_pct = quantity_variance / ordered_qty * 100`
- `close_balance = opening_balance + invoice_total - scheduled_payments`
- `headroom_before_change = ceiling_amount - noncancelled_subtotal`
- `headroom_after_change = headroom_before_change - requested_subtotal`
- `budget_after_change = remaining_budget - requested_total`
- `net_release_amount` is the amount released now; use `0.00` for held invoices unless the template says otherwise.

## 1) Nomination and readiness packets
- Use the memo to identify the program, as-of date, package line SKUs, and any named anchors.
- Reconcile each line against the requisition, contract basis, PO, receipt evidence, invoice exceptions, approval state, budget, and risk records.
- Derive `nomination_decision`, `readiness_status`, `blocker_codes`, and `committee_action` from the live records, not from memo labels.
- Keep line lists, blocker lists, and committee lists sorted the way the template requires.
- Treat missing contract basis, open supplier risk, watch status, pending receipt, late due date, or AP hold as blockers only when the template's fields support that interpretation.

## 2) Receiving closeouts
- Reconcile each PO line across ordered quantity, received quantity, rejected quantity, billed quantity, and contract price.
- Use the invoice, receipt, PO, contract, supplier, and risk records to choose the hold/release disposition.
- Keep `exception_codes`, evidence IDs, and other set-like lists sorted and deduplicated.
- Make the AP action, receiving action, and supplier action match the disposition instead of repeating the same idea in different words.

## 3) AP close reconciliations
- Scope only the named invoices.
- Treat any opening-balance override in the memo as authoritative for the slice.
- Include scheduled payments through the cutoff date when computing close balances.
- Build vendor balances and program summaries from the slice only, then sort the rows by the template ordering.

## 4) Change-control decisions
- Check contract headroom, program budget, approval state, and supplier risk as separate gates.
- Use non-cancelled PO usage for contract exposure.
- Use the latest approval event for the approval check.
- If the memo includes tax or freight rules, apply them exactly and keep all currency fields rounded to cents.
- Let the final decision reflect all blockers that remain, and list the required follow-up actions explicitly.

## 5) AP release and hold files
- Tie each invoice to the receipts and chargebacks in scope.
- Separate approved chargebacks from pending-quality holds.
- Keep alias notes and supporting-only notes out of authoritative source lists unless the template asks for them.
- When a receipt or invoice is missing, say so directly in the structured field rather than trying to infer a substitute.

