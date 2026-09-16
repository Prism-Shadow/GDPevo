# ProcureOps Domain Concepts

## Entity Relationships

The ProcureOps domain models a procurement lifecycle:

```
Program -> Requisition -> Contract -> Purchase Order -> Receipt -> Invoice -> Payment
                |              |             |              |           |
                v              v             v              v           v
           Approvals      Supplier      Supplier      Vendor Risk  Supplier
```

Each PO belongs to one program, one contract (optional), and one supplier. Receipts, invoices, and payments flow from POs. Risk events attach to suppliers.

## Workflow Types

### Sourcing Nomination Readiness
Determine whether each line/SKU within a program can be nominated to committee. For each SKU:
- Identify the nominated supplier from the requisition or PO
- Check contract existence (missing contract = blocker)
- Check PO status and due-date liveness
- Check receipt evidence (missing receipt = blocker)
- Check invoice status (holds/exceptions = blocker)
- Check supplier risk events (open events = blocker)
- Combine into a `nominate | conditional_nomination | hold` decision

### Receiving/AP Closeout
Reconcile a specific receipt batch against its PO, contract, and invoice:
- Verify the batch against its receipt record (date, quantities, status)
- Perform line-level 3-way match: PO ordered vs receipt received vs invoice billed
- Calculate variances, completion ratios, and dollar exposure
- Determine disposition: accept/block/reject
- Flag AP hold position based on quantity and price variances
- Include supplier risk context

### AP Payment-Hold Reconciliation
For a targeted set of invoices:
- Determine the program, PO, supplier for each invoice
- Match receipts to compute received vs billed quantities
- Check for scheduled payments that offset balances
- Compute per-vendor balance (opening + invoices - scheduled = close)
- Compute per-program totals
- Sort invoices into hold and release queues
- Use controlled reason codes (not narrative)

### Change Control
Evaluate a modular change request against an existing contract:
- Verify the contract is active with correct supplier and SKU
- Compute contracted headroom: ceiling minus non-cancelled PO subtotals
- Compute budget headroom: cap minus committed
- Check the approval chain for the source requisition
- Assess supplier risk (watch is advisory, severe is blocking)
- Combine into a release/hold/reject decision with required actions

### AP Release File
Process mixed AP holds against receiving exceptions and chargebacks:
- Cross-match each invoice to its PO and receipt(s)
- For each receipt, identify exception codes from inspection
- Map chargeback records (local or API-derived) to invoices
- Compute net release amounts (invoice total minus approved chargebacks)
- Segregate release vs hold decisions
- Track approved vs pending chargeback totals
- Include followup actions for unresolved items

## Key Computations

### 3-Way Match (line level)
1. `ordered_qty` from PO lines
2. `received_qty` from receipt lines
3. `billed_qty` from invoice lines
4. `short_qty_vs_po` = `ordered_qty - received_qty`
5. `unreceived_billed_qty` = `billed_qty - received_qty`
6. `receipt_completion_ratio` = `received_qty / ordered_qty`
7. `quantity_variance` = `billed_qty - received_qty`
8. `quantity_variance_pct` = `(quantity_variance / ordered_qty) * 100`

### Dollar Values
- `received_goods_value` = sum(received_qty * unit_price) for all lines
- `unreceived_goods_value` = sum((ordered_qty - received_qty) * unit_price)
- `invoice_subtotal` from invoice record
- `invoice_total` = subtotal + freight + tax
- `net_balance_impact` = invoice_total - scheduled_payment_amount

### Contract Headroom
- `noncancelled_subtotal` = sum of subtotals for all non-cancelled POs under the contract
- `headroom_before_change` = `ceiling_amount - noncancelled_subtotal`
- `requested_subtotal` = `requested_quantity * unit_price`
- `headroom_after_change` = `headroom_before_change - requested_subtotal`

### Budget Headroom
- `budget_cap` from budget snapshot
- `committed_amount` from budget snapshot
- `remaining_budget` = `budget_cap - committed_amount`
- `requested_tax` = `requested_subtotal * tax_rate / 100`
- `requested_total` = `requested_subtotal + requested_tax`
- `budget_after_change` = `remaining_budget - requested_total`

## Supplier Risk Tiers

| Rating | Meaning | Action |
|---|---|---|
| `low` | No known issues | No blocking impact |
| `watch` | Advisory concern | Flag but do not block unless severe events exist |
| `severe` | Active severe event | Block until resolved |

When checking risk, separately report all open event IDs and severe open event IDs. A `watch` rating with only non-severe open events should flag but not block. A `severe` rating or any severe open event should block.

## Approval Chain

Approvals are event-driven. The latest approval event for a requisition determines the state:
- `submitted` = not yet approved, needs action
- `approved` = ready to proceed
- `rejected` = blocked

Only the latest event (by date) matters for readiness.

## Chargeback Processing

When local chargeback registers are provided alongside API data:
- Approved chargebacks reduce the net releasable amount for an invoice
- Pending chargebacks block release until resolved
- `net_release_amount` = `invoice_total - approved_chargeback_amount`
- Pending chargebacks may come from quality inspection holds
