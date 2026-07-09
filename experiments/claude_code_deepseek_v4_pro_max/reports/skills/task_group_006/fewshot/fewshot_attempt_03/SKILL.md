# ProcureOps Task Group Skill — Sourcing, Receiving, AP, and Change Control

## 1. Environment

- **API base URL**: Use the URL from `environment_access.md` (overrides any `localhost`/`127.0.0.1` in task text).
- **Public endpoints**: `/programs`, `/suppliers`, `/items`, `/contracts`, `/purchase_requisitions`, `/purchase_orders`, `/receipts`, `/ap/invoices`, `/ap/payments`, `/approval_events`, `/budget_snapshots`, `/vendor_risk_events`.
- Query with query parameters for filtering (e.g., `?program_id=PRG-AX17`, `?supplier_id=SUP-LUMA`).

## 2. Source Precedence

1. **ProcureOps API** — system of record for all operational data (POs, receipts, invoices, contracts, suppliers, approvals, budgets, risk events).
2. **Local chargeback register** — authoritative for chargeback statuses and amounts (train_005 pattern). When it exists, use its `status`, `reason_code`, `basis_quantity`, and `unit_cost` over API-derived values.
3. **Task payloads** (memos, packets, templates) — provide target IDs, business parameters (tax rates, as-of dates), and context; do NOT use them to override API facts.
4. When the API and a memo disagree, the API wins. When a chargeback register and the API disagree on chargeback details, the register wins.

## 3. Field Conventions

| Domain | Pattern | Examples |
|--------|---------|----------|
| Program ID | `PRG-XXXX` or `PRG-XXXX-NN` | PRG-AX17, PRG-NOVA-31 |
| Supplier ID | `SUP-XXXX` | SUP-LUMA, SUP-VANTIX |
| PO ID | `PO-XXXX-NNNN` or `PO-NNNNN` | PO-AX17-4481, PO-00031 |
| Receipt ID | `RCV-XXXX-NN` or `RCV-NNNNN` | RCV-BLUE-14, RCV-00017 |
| Invoice ID | `AP-XXXX-NNNN` or `AP-NNNNN` | AP-LUMA-7714, AP-00027 |
| Contract ID | `CR-XXXX-NNN` | CR-LMP-228 |
| Requisition ID | `REQ-XXXX-NNN` | REQ-AX17-141 |
| Risk Event ID | `VRE-NNNNN` | VRE-00005 |
| Approval Event ID | `APR-NNNNN` | APR-00001 |
| Budget Snapshot ID | `BUD-XXXX` | BUD-PRG-AX17 |
| SKU | Alphanumeric; may contain hyphens | LMP-228, DRV-AX17 |

- **All amounts in USD**, rounded to **2 decimal places** (cents). Use `round(x, 2)`.
- **Dates**: `YYYY-MM-DD` strings.
- **ID lists**: sort **ascending** unless the template says "set; evaluator sorts".
- **Missing optional IDs**: use `null`, never empty string `""`.
- **Booleans**: `true`/`false` (not strings).
- **Empty lists**: use `[]`, never `null` for list-typed fields.

## 4. Reusable Business Rules

### 4.1 Three-Way Match (PO ↔ Receipt ↔ Invoice)

```
quantity_variance = billed_qty - received_qty
quantity_variance_pct = round((quantity_variance / billed_qty) * 100, 1)
```
- If no receipt exists: `received_qty = 0`, `quantity_variance = billed_qty`.
- Match is good when `variance == 0`.

### 4.2 Receipt Line Reconciliation

```
short_qty_vs_po = ordered_qty - received_qty
unreceived_billed_qty = billed_qty - received_qty
receipt_completion_ratio = round(received_qty / ordered_qty, 4)
received_goods_value = round(received_qty * unit_price, 2)
unreceived_goods_value = round(short_qty_vs_po * unit_price, 2)
invoice_subtotal = round(billed_qty * unit_price, 2)
invoice_total = round(subtotal + freight + tax, 2)
```

### 4.3 Contract Ceiling Check

```
noncancelled_subtotal = sum of all non-cancelled PO subtotals under the contract
headroom_before_change = ceiling_amount - noncancelled_subtotal
requested_subtotal = round(requested_quantity * unit_price, 2)
headroom_after_change = headroom_before_change - requested_subtotal
ceiling_ok = (headroom_after_change >= 0)
```
- **Exclude cancelled POs** from `noncancelled_subtotal`.
- Subtotal = line items only, before tax and freight.

### 4.4 Program Budget Check

```
remaining_budget = budget_cap - committed_amount
requested_tax = round(requested_subtotal * tax_rate_pct / 100, 2)
requested_total = round(requested_subtotal + requested_tax, 2)
budget_after_change = round(remaining_budget - requested_total, 2)
budget_ok = (budget_after_change >= 0)
max_quantity_with_current_budget = floor(remaining_budget / (unit_price * (1 + tax_rate_pct/100)))
```
- Freight is only added when the task memo explicitly provides a freight amount.

### 4.5 AP Close Balance

```
close_balance = opening_balance + invoice_total - scheduled_payments
held_invoice_total = sum of invoice_totals where hold_decision == "HOLD"
releasable_invoice_total = sum of invoice_totals where hold_decision == "RELEASE"
total_close_balance = sum of all close_balances
```
- `balance_status`: `"FULLY_SCHEDULED"` when close_balance ≈ 0; `"OPEN_HELD"` when held > 0; `"OPEN_APPROVED"` when approved but not fully scheduled.
- Scheduled payments through the end of the close month count toward reducing the balance.

### 4.6 Chargeback Netting (AP Release)

```
net_release_amount = invoice_total - approved_chargeback_amount  (when releasing)
net_release_amount = 0  (when holding)
approved_chargeback_total = sum of all approved chargeback amounts
net_release_total = sum of all net_release_amounts
```

### 4.7 Readiness & Blocker Assessment

Blocker codes (apply per SKU line):
| Code | Trigger |
|------|---------|
| `missing_contract` | No contract found for the SKU-supplier pair |
| `supplier_watch` | Supplier has risk rating `"watch"` |
| `open_supplier_risk` | Supplier has ≥1 open vendor risk event |
| `ap_hold` | Invoice status is `"on_hold"` or `"pending_receipt"` |
| `pending_receipt` | No receipts exist for the PO (or all receipts are after as_of_date) |
| `late_due_date` | PO delivery date is past the as_of_date and not fully received |
| `none` | No blockers apply |

Readiness status: `"ready"` (0 blockers), `"at_risk"` (only `supplier_watch`), `"not_ready"` (any hard blocker).
Nomination decision: `"nominate"` (ready), `"conditional_nomination"` (at_risk), `"hold"` (not_ready).

### 4.8 Approval Check

- Find the latest approval event for the source requisition (by event date).
- `approval_ok = true` ONLY when `latest_action == "approved"`.
- `"submitted"`, `"rejected"`, `"pending"` → `approval_ok = false`.

### 4.9 Supplier Risk Check

- `supplier_risk_ok = true` unless ≥1 **severe** open risk event exists.
- Watch rating alone does not fail the risk check, but it becomes a blocker/warning.
- `open_event_ids`: all open events. `severe_open_event_ids`: only severe open events.

### 4.10 Invoice Hold/Release Decision

| Condition | Decision | Hold Code | Reason Code |
|-----------|----------|-----------|-------------|
| Three-way match, payment scheduled | `RELEASE` | `null` | `APPROVED_THREE_WAY_MATCH`, `SCHEDULED_PAYMENT_FOUND` |
| Qty variance (billed > received) | `HOLD` | `QTY_VARIANCE` | `QTY_VARIANCE` |
| No receipt at all | `HOLD` | `NO_RECEIPT` | `NO_RECEIPT` |
| Receipt underage + pending quality | `HOLD` | — | inspection_hold variants |
| Receipt underage + approved chargeback | Release net | — | approved_qty_chargeback |

### 4.11 Receiving Exception Codes

Use these controlled codes for receiving exception classification:
- `"Underage Quantity"` — received < ordered
- `"Severe Unmatched Quantity"` — significant shortfall
- `"Inspection Hold"` — quality hold on receipt
- `"AP Quantity Variance"` — billed ≠ received

### 4.12 Date-Bounded Filtering

- When an `as_of_date` is given, only include records with dates **≤ as_of_date**.
- Receipts dated after as_of_date are excluded from evidence.
- Risk events opened after as_of_date are excluded.

## 5. Output Schema Pitfalls

1. **Match the answer template exactly** — include every required key; do not add extra keys.
2. **task_id** in the output must match the template's expected value (see template `required_value`).
3. **Lists sorted ascending** unless the template says "set; evaluator sorts".
4. **Null vs empty**: missing optional scalar → `null`; empty list → `[]`.
5. **Enum values must be exact strings** — case-sensitive. Do not invent variant spellings.
6. **Numeric precision**: USD amounts → 2 decimals; ratios → as specified (often 4 decimals for completion ratio, 1 decimal for variance pct).
7. **Committee action**: `send_to_committee: "yes"` only when ≥1 conditional nomination exists AND there are unresolved blockers. Otherwise `"no"`.
8. **next_owner** in committee_action: `"ap_team"` if any blocker is AP-related; `"buyer"` if contract/sourcing issues; `"quality_ops"` if quality/receiving issues; `"program_owner"` if budget/approval issues; `"finance_ops"` for payment scheduling gaps.

## 6. Workflow SOP

### Step 0: Read task inputs
- Read the task prompt, the answer template, AND all payload files under `input/payloads/`.
- Extract: target IDs, as_of_date, business parameters (tax rate, freight, ceiling, budget cap).

### Step 1: Query the API
- Fetch relevant records from the ProcureOps API using the target IDs as filters.
- Use ALL relevant endpoints — a single task typically needs 3-6 different endpoints.
- Always cross-reference: a PO links to a contract, supplier, program, receipts, and invoices.

### Step 2: Reconcile
- Apply the business rules in Section 4 using API data.
- If a chargeback register is present in payloads, use it for chargeback details.
- Check dates against as_of_date for temporal filtering.

### Step 3: Build the answer
- Start from the answer template structure.
- Fill every field; compute derived values using the formulas above.
- Sort all ID lists ascending.
- Round all amounts to the specified precision.

### Step 4: Validate
- All required keys present?
- All amounts in USD rounded to cents?
- All enum values match the allowed set exactly?
- All boolean fields are `true`/`false` not strings?
- No invented IDs — every ID must come from the API or the task payloads.
- Null used for missing optionals, `[]` for empty lists.

## 7. Common Task Archetypes

| Archetype | Key endpoints | Key payload | Distinctive output |
|-----------|--------------|-------------|-------------------|
| Sourcing nomination | programs, contracts, POs, receipts, invoices, suppliers, vendor_risk | nomination memo (target SKUs/POs) | blocker_codes, committee_action |
| Receiving closeout | POs, receipts, contracts, invoices, suppliers, vendor_risk | receiving memo (batch ID) | line_reconciliation, financials, decision |
| AP close desk | invoices, POs, receipts, payments, suppliers, budget_snapshots | close memo (invoice list) | invoice_decisions, vendor_balances, program_summary |
| Change control | contracts, POs, programs, approvals, suppliers, vendor_risk, budget_snapshots | change memo (contract, variant, qty) | contract_check, program_budget_check, approval_check |
| AP release file | POs, receipts, invoices, vendor_risk | release packet (IDs + chargeback register) | release_decisions, receiving_exceptions, chargeback netting |
