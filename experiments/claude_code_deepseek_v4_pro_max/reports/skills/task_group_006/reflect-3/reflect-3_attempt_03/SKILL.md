# ProcureOps Task Solver SOP

## Environment

- Base URL: from `environment_access.md` (GDPEVO_ENV_BASE_URL); overrides any `localhost` or `127.0.0.1` in task text.
- All data comes from the remote ProcureOps API. Do not start a local env.
- Endpoints: `/programs`, `/suppliers`, `/items`, `/contracts`, `/purchase_requisitions`, `/purchase_orders`, `/receipts`, `/ap/invoices`, `/ap/payments`, `/approval_events`, `/budget_snapshots`, `/vendor_risk_events`.
- Every endpoint returns `{"count": N, "results": [...]}`. Always work from `results`.

## Source Precedence

1. **Task-local payloads** (memos, packets, chargeback registers) — provide business context, target IDs, and local-only data like chargeback registers. Treat as authoritative for business rules and target scope.
2. **API records** — source of truth for operational state (PO status, receipt quantities, invoice holds, supplier ratings, budget caps, approval events).
3. **Answer template JSON** — defines required keys, allowed values, ordering, and precision. Match it exactly.

## Field Conventions

### Dates and As-Of Filtering
- All dates are `YYYY-MM-DD` strings.
- "As of `as_of_date`" means records with date **on or before** the as_of date. Records after are excluded.
- Invoice/receipt dates, risk event dates, and approval event dates all respect the as_of cutoff.
- PO `due_date` < as_of_date → the PO is **late**.

### Sorting
- List fields marked "sorted ascending" must be sorted lexicographically (string sort).
- List fields marked "set; evaluator sorts values" can be in any order.
- Nomination lines are matched by `sku`; order within the array does not matter.

### Currency and Precision
- All amounts in USD. Round to **2 decimal places** (cents) unless the template specifies otherwise.
- Ratios use the precision specified (e.g., `receipt_completion_ratio` → 4 decimal places).
- Percentages use the precision specified (e.g., `quantity_variance_pct` → 1 decimal place).
- Use standard rounding (half-up).

### Null vs Missing
- `null` in JSON means the value is explicitly absent (e.g., no contract → `commercial_basis_id: null`).
- Empty arrays `[]` mean no records exist (e.g., no receipts, no risk events).
- `0.00` for financial fields when the value is zero.

## Key Business Rules

### Budget Headroom
- `budget_headroom = budget_cap - committed_amount` (from `/programs` or `/budget_snapshots`).
- Both endpoints agree; either is authoritative.

### Contract Ceiling Usage
- Sum subtotals of all POs under the contract **excluding cancelled** POs.
- "Cancelled" means status `"cancelled"`. "Closed", "confirmed", "partial_receipt", "open" all count as non-cancelled.
- `headroom_before_change = ceiling_amount - noncancelled_subtotal`.
- `ceiling_ok = headroom_after_change >= 0`.

### Approval Gates
- Only action `"approved"` satisfies approval requirements. `"submitted"`, `"returned"`, `"escalated"` do **not** count as approval.
- A requisition status of `"converted"` does not imply approval — check the actual approval events.
- Use the **latest** approval event (by date) for the source requisition.

### Supplier Risk
- Risk events are **supplier-level**, not PO-level. Any open/monitoring event for the supplier counts.
- Filter vendor risk events: status `"open"` or `"monitoring"` as of the as_of date.
- `supplier_risk_ok = true` when there are **no severe** (severity `"high"`) open events.
- A supplier `risk_rating` of `"watch"` is context; it does not by itself block unless there is also a severe open event.

### Invoice and Receipt Reconciliation
- `short_qty_vs_po = ordered_qty - received_qty`.
- `unreceived_billed_qty = billed_qty - received_qty`.
- `receipt_completion_ratio = received_qty / ordered_qty`.
- Invoice exception codes are additive: include all that apply.
- `SUPPLIER_WATCH_RISK` should be included in exception codes when the supplier has any open risk event.

### AP Close Desk
- `opening_balance` is specified by the task memo (often `0.00` for a slice).
- Scheduled payments through the cutoff date reduce the close balance.
- `close_balance = opening_balance + invoice_total - scheduled_payments`.
- `net_balance_impact = invoice_total - scheduled_payment_amount`.
- `quantity_variance_pct = (quantity_variance / PO_quantity) * 100`, rounded to 1 decimal.
- `balance_status`: `"FULLY_SCHEDULED"` when close_balance = 0, `"OPEN_HELD"` when held, `"OPEN_APPROVED"` when approved but not fully scheduled.

### Chargeback Handling
- Chargeback registers in task payloads are **authoritative sources** (not API data).
- `approved_chargeback_amount = basis_quantity × unit_cost` (from chargeback register).
- `pending_chargeback_amount` same formula for pending chargebacks.
- `net_release_amount = invoice_total - approved_chargeback_amount` for release decisions; `0.00` for holds.
- Approved chargebacks → `release_net_after_approved_chargeback`. Pending quality review → `hold_pending_quality_chargeback`.

### Change-Control Budget Exposure
- `requested_subtotal = requested_quantity × contract_unit_price`.
- `requested_tax = requested_subtotal × (tax_rate_percent / 100)`, rounded to cents.
- `requested_total = requested_subtotal + requested_tax` (add freight only if the change memo provides it).
- `budget_after_change = remaining_budget - requested_total`.
- `budget_ok = budget_after_change >= 0`.

## Arithmetic Checks

- Always recompute totals independently; do not assume API subtotals are consistent.
- Tax verification: `tax / subtotal` should equal the stated tax rate (e.g., 0.0725 for 7.25%).
- `invoice_total = subtotal + freight + tax`.
- Budget headroom should be verified against both `/programs` and `/budget_snapshots`.
- When contract and PO unit prices differ, use the **contract** price for ceiling calculations and the **PO** price for PO-level math.

## Output Schema Pitfalls

- **List ordering**: Pay attention to whether lists must be sorted or are sets. Sorted lists use lexicographic string sort.
- **Enum values**: Use exact allowed values from the template. Do not invent or approximate.
- **Null handling**: Use JSON `null` (not `"null"`, not `"none"`, not `""`).
- **Empty arrays vs null**: `[]` for empty lists, `null` for absent single values.
- **Integer vs float**: Quantities are integers; financial amounts are floats with 2 decimal places.
- **Boolean**: Use JSON `true`/`false`, not strings.
- **Date format**: Always `YYYY-MM-DD` strings.
- **Blocker codes**: The list `["none"]` means no blockers. When blockers exist, `"none"` must be absent.

## Exclusion Rules

- **Cancelled POs**: Exclude from contract usage calculations. Check `status` field.
- **Cancelled requisitions**: Ignore for nomination/readiness purposes.
- **Closed/expired risk events**: Exclude from `open_event_ids` and risk checks. Only `"open"` and `"monitoring"` statuses count.
- **Future records**: Receipts, invoices, and events dated after the as_of date are excluded.
- **Out-of-scope invoices**: Only include the invoices explicitly named in the task memo/packet.

## Workflow Pattern

1. Read the task prompt, memo/packet payloads, and answer template.
2. Identify which API endpoints are needed.
3. Fetch all relevant endpoints in parallel.
4. Filter data by program, supplier, SKU, and as_of date.
5. Compute derived values (headroom, variance, ratios).
6. Build the answer JSON matching the template exactly.
7. Validate: check sorting, precision, allowed enum values, null vs empty.
