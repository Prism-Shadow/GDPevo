# ProcureOps Task Group — Solver SOP

## Environment

- **API base URL**: `http://34.46.77.124:8006` (from `environment_access.md`).
- Always use this URL — override any `localhost`/`127.0.0.1:8006` references in task text.
- Do NOT start a local env or run setup scripts. The remote API is already live.

## Source Precedence (always follow this order)

1. **Answer template** (`answer_template.json`) — the output contract. Every required key must be present. Every enum value must match exactly. List ordering must match the template's spec (sorted-ascending vs set/unordered).
2. **ProcureOps API** — system of record for all operational entities (programs, suppliers, items, contracts, POs, requisitions, receipts, invoices, payments, approval events, budget snapshots, vendor risk events).
3. **Local memo/packet** — provides task-specific context (target IDs, business rules, close dates, chargeback excerpts, requester notes). Use these to scope your API queries but NOT as the source of truth for quantities, prices, statuses, or amounts.

## Public API Endpoints

```
/programs               /suppliers              /items
/contracts              /purchase_requisitions  /purchase_orders
/receipts               /ap/invoices            /ap/payments
/approval_events        /budget_snapshots       /vendor_risk_events
```

Use query parameters (`?program_id=`, `?supplier_id=`, `?po_id=`, etc.) to filter. Fetch related records by their IDs — cross-reference PO lines to receipts, invoices to POs, etc.

## Field & Output Conventions

### Numbers
- **Monetary amounts**: always USD, always rounded to 2 decimal places (cents). Use standard rounding.
- **Ratios**: match the template's stated precision (e.g. `receipt_completion_ratio` = 4 decimals; `quantity_variance_pct` = 1 decimal).
- **Quantities**: integers for line-item qty; 2-decimal floats for invoice billed qty.

### Strings & Enums
- **Enum values**: must match the template's `allowed_values` exactly — case-sensitive. Never invent a value.
- **Dates**: `YYYY-MM-DD` format.
- **IDs**: preserve case and format as returned by the API.

### Lists
- **Sorting**: when the template says "sorted ascending" or "sort ascending", sort alphabetically/numerically. When it says "set; evaluator sorts values", order doesn't matter but use a consistent order (ascending is safe).
- **Empty vs null**: empty array `[]` ≠ `null`. Use whichever the template implies. When a field says `"string|null"`, use `null` if no value exists.

### Booleans
- Use JSON `true`/`false`, NOT strings `"yes"`/`"no"` — unless the template explicitly uses `"yes"|"no"` (e.g. `send_to_committee`).

## Reusable Business Rules

### Three-Way Match
- PO line → Receipt line → Invoice line. Check: ordered qty ≥ received qty, received qty ≥ billed qty.
- `INVOICE_QTY_EXCEEDS_RECEIPT` when `billed_qty > received_qty`.
- `PRICE_MISMATCH` when `po_unit_price ≠ contract_unit_price` or `po_unit_price ≠ invoice_unit_price`.

### Quantity Reconciliation
```
short_qty_vs_po        = ordered_qty - received_qty
unreceived_billed_qty  = billed_qty - received_qty   (positive = billed more than received)
receipt_completion_ratio = received_qty / ordered_qty  (4 decimal places)
quantity_variance       = quantity_billed - quantity_received
quantity_variance_pct   = (quantity_variance / po_quantity) * 100  (1 decimal place)
```

### Financial Arithmetic
```
received_goods_value   = Σ (received_qty × po_unit_price) per line
invoice_subtotal       = Σ (billed_qty × invoice_unit_price) per line
invoice_total          = invoice_subtotal + invoice_freight + invoice_tax
net_balance_impact     = invoice_total - scheduled_payment_amount
close_balance          = opening_balance + invoice_total - scheduled_payments
```

### Contract Ceiling Check
```
noncancelled_subtotal  = Σ (qty × unit_price) for all POs under the contract, excluding cancelled POs
headroom_before_change = ceiling_amount - noncancelled_subtotal
requested_subtotal     = requested_quantity × unit_price
headroom_after_change  = headroom_before_change - requested_subtotal
ceiling_ok             = headroom_after_change >= 0
```

### Budget Check
```
remaining_budget       = budget_cap - committed_amount
requested_tax          = requested_subtotal × (tax_rate_percent / 100)
requested_total        = requested_subtotal + requested_tax  (+ freight only if memo provides it)
budget_after_change    = remaining_budget - requested_total
budget_ok              = budget_after_change >= 0
max_quantity_with_current_budget = floor(remaining_budget / (unit_price × (1 + tax_rate / 100)))
```

### AP Hold/Release Logic
- **HOLD** when: no receipt exists (`NO_RECEIPT`), quantity variance is material, supplier has open severe risk events, or invoice has an existing hold code.
- **RELEASE** when: three-way match passes, no open severe supplier risk, and invoice is in an approved/validated status.
- `release_to_payment: true` only when `hold_decision = "RELEASE"` and invoice status supports it.

### Supplier Risk
- **Watch rating** is context-only unless an **open severe event** exists → then it becomes a blocker.
- Open vendor risk events with `status = "open"` trigger `open_supplier_risk` blocker codes.
- `supplier_risk_ok = false` when any severe open event exists on that supplier.

### Approval Check
- Query `/approval_events` for the source requisition.
- Look for the latest event by date. `approval_ok = true` only when the latest action is in the approved set (e.g. `"approved"`).
- The memo's `approval_good_actions` list defines which actions count as approved.

### Chargeback Netting (Release Calculations)
```
net_release_amount = invoice_total - approved_chargeback_amount
```
- Approved chargebacks reduce the net release amount.
- Pending chargebacks (e.g. `pending_quality_review`) keep the invoice on hold — do NOT include them in net release.
- Chargeback data comes from the local packet (chargeback register), not the API.

### Readiness & Blocker Codes
```
missing_contract   — no contract found for the line's supplier+SKU
supplier_watch     — supplier has watch rating (contextual, not always blocking)
open_supplier_risk — supplier has open (non-severe) risk events
ap_hold            — invoice is on hold
pending_receipt    — receipt not yet posted or incomplete
late_due_date      — PO due date is past as_of_date without full receipt
none               — no blockers; line is clear
```

## Exclusion Rules

- **Cancelled POs**: always exclude from contract usage (noncancelled_subtotal) and PO lists where the context is "active" POs.
- **Time-scoped**: receipts/invoices/risk events are scoped to `as_of_date` — exclude records after that date.
- **Scope discipline**: only include the target IDs named in the memo/packet. Don't pull in unrelated suppliers, POs, or invoices even if they share a program.
- **Same-PO receipts not in scope**: when a packet names specific receipt IDs, exclude other receipts on the same PO — list them under `excluded_same_po_receipt_ids`.

## Output Schema Pitfalls

| Pitfall | Fix |
|---|---|
| Missing a required top-level key | Cross-check every key in the template's `required_top_level_keys` or `top_level_required_keys` before finalizing |
| Enum value not in allowed list | Copy-paste from the template's `allowed_values`; never paraphrase |
| Wrong precision | Check per-field precision: `receipt_completion_ratio` = 4dp, most dollar amounts = 2dp, `quantity_variance_pct` = 1dp |
| List sorted when template says "set" | Sets can be any order but ascending is safest default |
| List unsorted when template says "sorted ascending" | MUST sort ascending |
| `null` vs `[]` | Template annotations like `"string|null"` mean use `null` for missing; `"string"` with empty list `[]` means use empty array |
| Boolean vs string | `true`/`false` in JSON, `"yes"`/`"no"` only where template explicitly uses strings |
| Invoice total ≠ subtotal + freight + tax | Always verify: `invoice_total = invoice_subtotal + invoice_freight + invoice_tax` |
| Using cancelled POs in sums | Filter by PO status — exclude `cancelled` |
| Forgetting scheduled payments reduce balance | Query `/ap/payments` for payments through the close period and subtract from balance |

## Workflow Checklist

1. **Read the answer template** first — understand every required field, its type, and constraints.
2. **Read the memo/packet** — extract target IDs, as_of_date, business rules, and any local data (chargebacks, notes).
3. **Query the API** — fetch all relevant records using the target IDs. Cross-reference across endpoints.
4. **Reconcile** — apply the business rules above. Compute quantities, financials, and decisions.
5. **Validate** — check all required keys present, all enums match, all lists sorted as required, all arithmetic is consistent.
6. **Output** — return ONLY the JSON object. No prose, no markdown wrapping, no commentary.
