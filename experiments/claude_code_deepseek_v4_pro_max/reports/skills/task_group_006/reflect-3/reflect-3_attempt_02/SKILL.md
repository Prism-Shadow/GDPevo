# ProcureOps Task Solver — Reusable SOP

## Environment

- Use the remote API base URL provided by the task runner (env var or `environment_access.md`). Never hardcode `localhost` or `127.0.0.1`.
- Public endpoints: `/programs`, `/suppliers`, `/items`, `/contracts`, `/purchase_orders`, `/purchase_requisitions`, `/receipts`, `/ap/invoices`, `/ap/payments`, `/approval_events`, `/budget_snapshots`, `/vendor_risk_events`.
- API responses are unpaginated: `{"count": N, "results": [...]}` returns all records in one call.

## Source Precedence

1. **API is the source of truth** for all operational records. Task memos name targets but API data overrides them.
2. Local payloads (`input/payloads/`) provide business controls (tax rates, approval rules, chargeback registers) and answer templates. Use them for structure and business rules, not for record data.

## Output Schema Rules

- **USD amounts**: always round to 2 decimal places (cents).
- **Ratios**: 4 decimal places (e.g., `0.9000` not `0.9`).
- **Percentages**: 1 decimal place (e.g., `10.0` not `10`).
- **List fields**: sort ascending by ID unless the template explicitly says "set; evaluator sorts values". When the evaluator sorts, any order is accepted but keep IDs unique.
- **ID lists**: all IDs should be strings, not numbers.
- **task_id**: match exactly what the template specifies (e.g., `"train_002"`, `"task_group_006_train_001"`).
- **Dates**: `YYYY-MM-DD` string format.
- **Booleans**: JSON `true`/`false`, not strings.

## Date Filtering Conventions

- **"as of" a date**: include records with dates ≤ the as_of_date. Receipts dated after the as_of_date are excluded, even if they share the same PO.
- **"through" a date**: inclusive of the boundary date. "Through 2026-06-30" includes June 30.
- **Invoice dates**: an invoice dated on the as_of_date is included.

## Business Rules

### Budget & Contract
- **Budget headroom** = `budget_cap - committed_amount` from the budget snapshot. Do NOT subtract `pending_invoice_amount`.
- **Contract noncancelled subtotal**: sum `subtotal` of all non-cancelled POs referencing that contract. Exclude POs with status `"cancelled"`.
- **Contract headroom** = `ceiling_amount - noncancelled_subtotal`. Then subtract the requested change subtotal for headroom after change.
- **Contract rate**: unit price × tax rate. `requested_tax = requested_subtotal * tax_rate_pct / 100`. `requested_total = requested_subtotal + requested_tax`. No freight unless the memo provides it.
- **Max quantity with budget**: `floor(remaining_budget / (unit_price * (1 + tax_rate)))`. Verify: round down to integer.

### Receipts & Reconciliation
- **Received goods value** = `received_qty × po_unit_price`.
- **Unreceived goods value** = `(ordered_qty - received_qty) × po_unit_price`.
- **short_qty_vs_po** = `ordered_qty - received_qty`.
- **unreceived_billed_qty** = `billed_qty - received_qty`.
- **receipt_completion_ratio** = `received_qty / ordered_qty` (4 decimal places).
- **quantity_variance** = `billed_qty - received_qty`.
- **quantity_variance_pct** = `(variance / PO_ordered_qty) × 100` (1 decimal place). When no receipt exists, received = 0 and variance = billed, variance_pct = 100.0.

### Three-Way Match
- PO, receipt, and invoice all exist AND quantities match → `APPROVED_THREE_WAY_MATCH`.
- Missing receipt → `NO_RECEIPT`.
- Quantity mismatch → `QTY_VARIANCE`.
- Invoice has a scheduled payment through the cutoff → `SCHEDULED_PAYMENT_FOUND`.

### Approval Events
- Find the **latest** approval event (by date) for the target requisition.
- Only actions listed in business controls' `approval_good_actions` count as approved. Typically only `"approved"` counts; `"submitted"`, `"returned"`, `"escalated"` do not.
- Never fabricate approval event data. Use exact API values.

### Supplier Risk
- `"watch"` risk rating is **context only** — it does not block approval unless an open **severe** (high severity) event exists.
- Non-severe open events still count toward `open_supplier_risk` blocker code and appear in `risk_event_ids`.
- For invoice exception codes: include `SUPPLIER_WATCH_RISK` when the supplier has a `"watch"` rating, regardless of open events.

### Blockers
- Include **all** applicable codes from the allowed set. Do not include `"none"` when real blockers exist.
- `missing_contract`: no contract exists for the SKU-supplier-program combination.
- `supplier_watch`: supplier `risk_rating` is `"watch"` and task rules treat it as a blocker.
- `open_supplier_risk`: any open risk event for the supplier as of the as_of_date.
- `ap_hold`: any invoice for the line is in `on_hold` or `pending_receipt` status.
- `pending_receipt`: PO is not fully received (status is `open`, `partial_receipt`, or `confirmed` with no receipt).
- `late_due_date`: PO `due_date` is before the as_of_date.

### Overall Readiness
- Reflect the **worst** line status. If any line is `"not_ready"`, the overall is `"not_ready"`.
- Only use `"ready"` when all lines are `"ready"`.

### Committee / Escalation
- `next_owner` should be `"program_owner"` when issues span multiple departments (contract, AP, risk).
- `send_to_committee` is `"yes"` when any line is not `"nominate"`.

### Vendor Balances (AP Close)
- Opening balance for a close slice is given by the memo (often `0.00`).
- `scheduled_payments` = sum of payments for the **target invoices only**, scheduled on or before the cutoff date.
- `close_balance` = `opening_balance + invoice_total - scheduled_payments`.
- Status: `FULLY_SCHEDULED` when close_balance = 0, `OPEN_HELD` when all invoices are held, `OPEN_APPROVED` when all are releasable.

### Chargebacks (AP Release)
- `approved_chargeback_amount` = chargeback `basis_quantity × unit_cost` for chargebacks with status `"approved"`.
- `pending_chargeback_amount` = same formula for `"pending_quality_review"` chargebacks.
- `net_release_amount` = `invoice_total - approved_chargeback - pending_chargeback`. For held invoices, net_release = 0.
- Receipt exclusion: list receipts for the same PO that are not in the target receipt scope under `excluded_same_po_receipt_ids`.

### Contract Price Match
- Compare `po_unit_price`, `contract_unit_price`, and `invoice_unit_price`. All three must be equal for `contract_price_match: true`.

## Arithmetic Checks

- Budget headroom ≥ 0 before change → budget_ok.
- Contract headroom ≥ 0 after change → ceiling_ok.
- Verify: received_goods + unreceived_goods = ordered_qty × po_unit_price.
- Verify: billed_qty × invoice_unit_price = invoice_subtotal.
- Verify: close_balance = opening + invoice_total - scheduled_payments (per vendor).
- When max_quantity calculation produces a fractional result, floor it. Verify by plugging back: `floor_q × unit_price × (1 + tax_rate) ≤ remaining_budget` and `(floor_q + 1) × unit_price × (1 + tax_rate) > remaining_budget`.

## Common Pitfalls

- **Do not add freight to budget exposure** unless the change memo explicitly provides freight.
- **"Submitted" is not "approved"** for approval checks unless business controls say otherwise.
- **Do not subtract pending_invoice_amount from budget headroom** — use committed_amount.
- **Receipt dates** filter as_of_date; future-dated receipts are excluded even for the same PO.
- **Exclude cancelled POs** from contract usage and supporting IDs.
- **Lists are ID sets**: no duplicates, sorting matters unless template says "evaluator sorts".
- **Never fabricate API data**. If the API says action is `"submitted"`, write `"submitted"`, not `"approved"`.

## Data Integrity

- Pull all API records before constructing answers. Use the full response — the API returns everything in one call.
- Cross-reference: every invoice's receipt_id should point to a real receipt; if it's `null`, that's intentional.
- Chargeback registers in local payloads reference API records — verify the PO, receipt, and invoice IDs match.
- When a task says "use available shared IDs" or notes that certain identifiers are not in the shared environment, trust the provided mapping.
