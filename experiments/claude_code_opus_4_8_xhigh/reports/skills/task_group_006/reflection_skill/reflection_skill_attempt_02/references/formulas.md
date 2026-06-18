# ProcureOps Derivation Formulas (verified)

Every formula below was re-verified against the live API during reflection. Use these
exact definitions; the wording differences are where the blind pass lost points.

## Quantities

- `ordered_qty` = PO line `quantity`.
- `received_qty` = sum of receipt-line `quantity_received` for that PO line that are
  **in scope** for the as-of date (receipt_date <= as_of). If no receipt exists, use
  `0`.
- `billed_qty` = invoice line `quantity_billed`.
- `rejected_qty` = sum of receipt-line `quantity_rejected`.
- `short_qty_vs_po` = `ordered_qty - received_qty` (PO-vs-receipt shortfall).
- `unreceived_billed_qty` = `billed_qty - received_qty` (AP-vs-receipt gap).
- `quantity_variance` = `billed_qty - received_qty`.
- `quantity_variance_pct` = `100 * quantity_variance / ordered_qty`
  (**percentage of PO quantity**, not of billed). Round per template (often 1 decimal).
  When there is no receipt: received = 0, so variance = billed and pct = 100% of the
  ordered-vs-billed basis the template names. Read the template's wording exactly.
- `receipt_completion_ratio` = `received_qty / ordered_qty`, rounded to the template's
  precision (e.g. precision 4). Emit it as a plain number; 0.9 and 0.9000 are the same
  numeric value.

## Prices and matching

- `po_unit_price` = PO line `unit_price`.
- `contract_unit_price` = contract `unit_price` (only if the PO has a `contract_id`).
- `invoice_unit_price` = invoice line `unit_price`.
- `contract_price_match` = `invoice_unit_price == contract_unit_price` (and usually ==
  PO price). `PRICE_MISMATCH` exception fires only when they differ.

## Money (financials)

- `received_goods_value` = `received_qty * unit_price`.
- `unreceived_goods_value` = `unreceived_billed_qty * unit_price`
  (billed-but-not-received units * price).
- `invoice_subtotal / freight / tax / total` come straight from the invoice record;
  do not recompute tax unless the task gives you a tax rate to apply.
- All money rounds to cents (2 decimals).

## Contract ceiling / headroom

- `noncancelled_subtotal` = sum of line subtotals across all POs on the contract whose
  status is **not** `cancelled` (include open/confirmed/partial/closed). Use each PO's
  `subtotal`.
- `headroom_before_change` = `ceiling_amount - noncancelled_subtotal`.
- `requested_subtotal` = `requested_quantity * contract_unit_price` (before tax/freight).
- `headroom_after_change` = `headroom_before_change - requested_subtotal`.
- `ceiling_ok` = `headroom_after_change >= 0`.

## Program budget (change-control)

- Use the dated `budget_snapshot`.
- `remaining_budget` = `budget_cap - committed_amount` (NOT pending_invoice_amount).
- `requested_tax` = `requested_subtotal * tax_rate` (rate from the memo, e.g. 7.25%).
- `requested_total` = `requested_subtotal + requested_tax` (+ freight only if the memo
  supplies freight; otherwise no freight).
- `budget_after_change` = `remaining_budget - requested_total`.
- `budget_ok` = `budget_after_change >= 0`.
- `max_quantity_with_current_budget` = `floor(remaining_budget / per_unit_loaded)`
  where `per_unit_loaded = unit_price * (1 + tax_rate)`.

## Scheduled-payment netting (AP close)

- A scheduled payment counts toward an invoice when its `invoice_id` matches the target
  invoice AND `scheduled_date <= cutoff` (cutoff inclusive, e.g. 2026-06-30 counts).
- Match by `invoice_id`, never by supplier. Other invoices' payments do not reduce
  this invoice's balance.
- `net_balance_impact` = `invoice_total - scheduled_payment_amount`.
- `close_balance` (vendor) = `opening_balance + invoice_total - scheduled_payments`.

## Chargeback netting (AP release)

- The local chargeback register gives `basis_quantity`, `unit_cost`, `reason_code`,
  `status` per chargeback. `chargeback_amount = basis_quantity * unit_cost`.
- Approved chargeback → net it: `net_release_amount = invoice_total - approved_chargeback`,
  decision `release_net_after_approved_chargeback`.
- Pending (e.g. `pending_quality_review`) chargeback → hold; net_release = 0, the amount
  goes to `pending_chargeback_amount`, decision `hold_pending_quality_chargeback`.
- No receipt on the PO → hold; all amounts 0, decision `hold_missing_receipt`.
- Totals: sum approved across releasing invoices for `approved_chargeback_total`,
  sum pending for `pending_chargeback_total`, sum nets for `net_release_total`.
