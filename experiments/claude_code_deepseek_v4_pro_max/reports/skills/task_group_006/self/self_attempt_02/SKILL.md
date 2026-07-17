# ProcureOps Task Group — Solver SOP

## 1. Environment

- **Base URL**: `http://34.46.77.124:8006` (from `environment_access.md`). This overrides ANY `127.0.0.1:8006` or localhost reference in task text.
- **Available endpoints**: `/programs`, `/suppliers`, `/items`, `/contracts`, `/purchase_requisitions`, `/purchase_orders`, `/receipts`, `/ap/invoices`, `/ap/payments`, `/approval_events`, `/budget_snapshots`, `/vendor_risk_events`.
- **Always hit these endpoints live**; memo/packet files provide context but the API is the authoritative source of record.

## 2. Source Precedence

1. **ProcureOps API records** — authoritative for all operational data (POs, receipts, invoices, contracts, budgets, approvals, suppliers, risk events).
2. **Task-local payloads** (memos, JSON packets, chargeback registers) — provide target IDs, business rules, and contextual annotations. Use them to scope API queries but never substitute API data.
3. **Answer template JSON** — defines the exact output schema. Every field, type, precision, ordering rule, and enum constraint is mandatory.

Rule: when a memo claim and an API record conflict, the API wins.

## 3. Field & Format Conventions

### Currency
- All amounts in **USD**, rounded to **2 decimal places** (cents) unless noted.
- **Ratios** like `receipt_completion_ratio` use **4 decimal places**.

### Dates
- Always `YYYY-MM-DD` format.
- "As of" dates act as a cutoff: exclude records dated after the as_of date. Future-dated payments through a specified horizon (e.g., "through 2026-06-30") count as scheduled and reduce balances.

### Lists
- Treated as **sets** (duplicate-free) unless the template explicitly specifies sorting.
- When sorted, use **ascending** order: lexicographic for strings, numeric for numbers.
- Empty lists use `[]`, never `null` or omitted keys.

### IDs
- Entity IDs follow known prefixes: `PRG-` (program), `SUP-` (supplier), `PO-` (purchase order), `REQ-` (requisition), `RCV-` (receipt), `AP-` (invoice), `CR-` (contract), `CB-` (chargeback), `WH-` (warehouse), `LMP-` / `DRV-` / `SKU-` (SKUs).

### Output Format
- **Return only JSON** — no prose, no markdown fences, no commentary.
- Every key in the answer template must be present in the output.

## 4. Reusable Business Rules

### Three-Way Match (PO ↔ Receipt ↔ Invoice)
- `quantity_billed` must not exceed `quantity_received` for a clean match.
- `quantity_variance = quantity_billed - quantity_received` (positive = overbilled).
- `quantity_variance_pct = (variance / PO ordered quantity) * 100`, rounded to **1 decimal**.
- `short_qty_vs_po = ordered_qty - received_qty`.
- `unreceived_billed_qty = billed_qty - received_qty` (clamped to ≥ 0).
- `receipt_completion_ratio = received_qty / ordered_qty` (4 decimal places).

### Contract Ceiling
- Ceiling check uses **line subtotal before tax and freight**.
- **Exclude cancelled POs** from existing contract usage.
- `noncancelled_subtotal` + `requested_subtotal` ≤ `ceiling_amount` → ceiling OK.
- `headroom_before_change = ceiling_amount - noncancelled_subtotal`.
- `headroom_after_change = headroom_before_change - requested_subtotal`.

### Budget Headroom
- Budget exposure includes **line subtotal + estimated tax** (freight only if the memo provides it).
- `budget_after_change = remaining_budget - requested_total`.
- Tax rate from the memo/change payload (e.g., 7.25%). Compute `requested_tax = requested_subtotal * (tax_rate / 100)`.
- `max_quantity_with_current_budget = floor(remaining_budget / (unit_price * (1 + tax_rate/100)))`.

### Supplier Risk
- Check `/vendor_risk_events` for the supplier. Filter to **open** events.
- An **open severe** event is a blocker → `supplier_risk_ok = false`.
- Non-severe open events are context only unless the task explicitly says they block.
- `supplier_risk_rating` comes from the supplier record, not risk events.
- `supplier_status` is from the supplier record (`active`, `inactive`, etc.).

### Approval State
- Query `/approval_events` for the relevant requisition or PO.
- Filter to actions matching the memo's `approval_good_actions` (typically `"approved"`).
- `approval_ok = true` only if the latest matching event action is in the good-actions set.
- A missing approval event or a non-approved latest event → `approval_ok = false`.

### AP Hold & Release
- Invoice status + receipt status + PO status determine hold codes.
- A scheduled payment (found in `/ap/payments` through the cutoff date) reduces close balance.
- `net_balance_impact = invoice_total - scheduled_payment_amount`.
- Hold decision: `HOLD` if any exception condition exists (no receipt, qty variance, price mismatch, supplier risk); `RELEASE` only if all clear.

### Supplier Balance Reconciliation
- `close_balance = opening_balance + invoice_total - scheduled_payments`.
- Balance status: `FULLY_SCHEDULED` if close_balance ≈ 0 and all invoices are paid/scheduled; `OPEN_HELD` if any held invoices remain; `OPEN_APPROVED` if approved but unscheduled.
- Opening balance for a slice: `0.00` unless stated otherwise.

### Chargeback Netting (AP Release)
- `net_release_amount = invoice_total - approved_chargeback_amount`.
- `pending_chargeback_amount` does NOT reduce the net release — it remains held.
- Chargeback statuses: `approved` → nets out; `pending_quality_review` → hold.
- Approved chargebacks with reason `Underage Quantity` or `AP Quantity Variance` support partial release.

## 5. Common Exception & Reason Codes

| Code | Meaning |
|---|---|
| `NO_RECEIPT` | No receipt record exists for the invoice's PO |
| `QTY_VARIANCE` | Billed quantity ≠ received quantity |
| `APPROVED_THREE_WAY_MATCH` | PO, receipt, and invoice quantities align |
| `SCHEDULED_PAYMENT_FOUND` | A payment is already scheduled for this invoice |
| `INVOICE_QTY_EXCEEDS_RECEIPT` | Billed > received on at least one line |
| `PARTIAL_RECEIPT` | Received < ordered (not all goods arrived) |
| `PRICE_MISMATCH` | Invoice unit price ≠ PO or contract unit price |
| `DAMAGE_REJECTION` | Receipt has rejected/damaged quantity > 0 |
| `SUPPLIER_WATCH_RISK` | Supplier has open risk events |
| `NO_EXCEPTION` | No issues found |
| `missing_contract` | No active contract for the SKU/supplier |
| `supplier_watch` | Supplier has monitoring-level risk |
| `open_supplier_risk` | Supplier has an open risk event |
| `ap_hold` | Invoice is on AP hold |
| `pending_receipt` | Receipt not yet fully posted |
| `late_due_date` | Delivery is past the due date |

## 6. Blocker Codes (Nomination Readiness)

These are the canonical blocker codes from train_001:
- `missing_contract` — no contract found for the line item
- `supplier_watch` — supplier risk rating is elevated
- `open_supplier_risk` — open vendor risk events exist (especially severe)
- `ap_hold` — associated invoice is on hold
- `pending_receipt` — receipt not fully complete
- `late_due_date` — PO delivery date has passed
- `none` — no blockers

## 7. Decision Enums

### Nomination Decisions
- `nominate` — all clear, proceed
- `conditional_nomination` — minor issues, can proceed with caveats
- `hold` — blocked, cannot nominate

### Readiness Status
- `ready` — no blockers
- `at_risk` — non-critical issues exist
- `not_ready` — blocked by one or more issues

### Change Control Decisions
- `release_amendment` — all checks pass
- `hold_for_budget` — budget insufficient
- `hold_for_approval` — requisition not approved
- `hold_for_supplier_risk` — supplier has open severe risk
- `hold_for_budget_and_approval` — both budget and approval fail
- `reject_contract_mismatch` — contract doesn't cover the SKU/supplier

### Batch Disposition (Receiving)
- `accept_partial_hold_variance` — some variance exists but batch is acceptable
- `release_full_invoice` — everything matches, release
- `reject_batch` — unrecoverable issues
- `manual_recount_required` — quantities need physical verification

### AP Actions
- `keep_invoice_on_hold`, `release_invoice`, `void_invoice`

### Receiving Actions
- `record_shortage_follow_up`, `no_receiving_action`, `reject_all_units`

### Supplier Actions
- `request_credit_or_remaining_delivery`, `no_supplier_action`, `supplier_debit_for_damage`

## 8. Cross-Check Rules (Arithmetic Validation)

Before outputting, verify:
1. **Sum of line items** = header totals (invoice subtotals + freight + tax = invoice total).
2. **Contract headroom**: `headroom_before - requested_subtotal = headroom_after`.
3. **Budget**: `remaining_budget - requested_total = budget_after_change`.
4. **Close balance**: `opening_balance + invoice_total - scheduled_payments = close_balance`, and `sum of vendor close_balances = total_close_balance`.
5. **Net release**: `invoice_total - approved_chargeback_amount = net_release_amount`.
6. **Held + Released = Invoice Total** in program_summary.
7. **Hold/Release queues**: every invoice appears in exactly one queue (hold or release), and the queues' union equals the invoice_decisions list.
8. **Quantity**: `received + rejected ≤ ordered` for a given PO line.

## 9. Output Schema Pitfalls

- **Do not omit keys** — even if a value is `null`, `[]`, `0.00`, or `false`, include the key.
- **Do not reorder** list fields unless the template says to sort; when it does, sort **ascending**.
- **Enum values must match exactly** — case-sensitive, underscores, no synonyms.
- **Integer vs number**: `ordered_qty`, `received_qty`, `rejected_qty`, `billed_qty` are integers; ratios and money are numbers.
- **`null` vs `""`**: use `null` for absent single values (e.g., no commercial_basis_id), use `""` only if the template constrains to string-type and a value is absent (rare).
- **Booleans**: use JSON `true`/`false`, not strings.
- **`task_id`**: must match the exact string the template expects (e.g., `"train_003"`, not `"task_group_006_train_003"`).

## 10. Exclusion Rules

- **Cancelled POs**: excluded from contract ceiling usage calculations. Include them in `excluded_cancelled_po_ids` but NOT in `included_po_ids`.
- **Future-dated records**: receipts, invoices, risk events, and approval events dated after the as_of date are excluded from the review scope.
- **Same-PO receipts not in scope**: when a task targets specific receipt IDs, receipts on the same PO but with different receipt IDs go in `excluded_same_po_receipt_ids`.
- **Duplicate receipts**: if two receipts reference the same PO lines, only the one named in the task scope is authoritative.

## 11. Entity Relationship Quick Reference

```
Program (PRG-*)
 └── Contract (CR-*) — linked by SKU + supplier + program
      └── Purchase Requisition (REQ-*)
           └── Purchase Order (PO-*) — references supplier, SKU, contract
                ├── Receipt (RCV-*) — references PO, warehouse
                ├── AP Invoice (AP-*) — references PO, supplier
                └── AP Payment — references invoice
Supplier (SUP-*)
 └── Vendor Risk Event — references supplier
Approval Event — references requisition or PO
Budget Snapshot — references program
```

## 12. Execution Checklist

1. Read the task prompt. Identify: task type (nomination / receiving / AP close / change control / release), target program/PO/invoice IDs, as_of date.
2. Read all payload files in `input/payloads/`. Note target IDs and business rules.
3. Read the answer template. Memorize required keys, types, precision, and enum values.
4. Query the API endpoints needed, using filters (e.g., `?program_id=PRG-AX17`, `?supplier_id=SUP-LUMA`).
5. Cross-reference API data with memo claims; API wins on conflicts.
6. Compute all derived values using the formulas in Section 4.
7. Apply the decision logic matching the task type.
8. Run the arithmetic cross-checks from Section 8.
9. Serialize to JSON matching the template exactly.
10. Return only the JSON object.
