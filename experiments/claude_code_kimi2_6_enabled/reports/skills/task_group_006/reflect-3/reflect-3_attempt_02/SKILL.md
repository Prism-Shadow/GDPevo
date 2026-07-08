# ProcureOps Skill Guide

## Overview
This skill covers solving procurement operations tasks using the ProcureOps API. The API provides endpoints for purchase orders, receipts, AP invoices, suppliers, programs, contracts, budget snapshots, approval events, and vendor risk events.

## API Usage Habits

### Base URL
Always use the remote API at `http://34.46.77.124:8006` (or the URL specified in `environment_access.md`). Never use localhost unless explicitly directed.

### Key Endpoints
- `GET /purchase_orders` - List/search POs (filter by `po_id`, `program_id`, `contract_id`, `supplier_id`)
- `GET /receipts` - List/search receipts (filter by `receipt_id`, `po_id`, `supplier_id`)
- `GET /ap_invoices` - List/search invoices (filter by `invoice_id`, `po_id`, `receipt_id`, `supplier_id`)
- `GET /suppliers` - List/search suppliers
- `GET /programs` - List programs
- `GET /contracts` - List contracts
- `GET /budget_snapshots` - List budget snapshots (filter by `program_id`)
- `GET /approval_events` - List approval events (filter by `object_id`)
- `GET /vendor_risk_events` - List risk events (filter by `supplier_id`)
- `GET /payments` - List payments (filter by `invoice_id`, `supplier_id`)
- `GET /items` - List items/SKUs
- `GET /purchase_requisitions` - List requisitions

### Query Patterns
Always fetch the full dataset first, then filter locally:
```bash
curl -s "http://34.46.77.124:8006/purchase_orders" | python3 -m json.tool
```

Filter by specific IDs:
```bash
curl -s "http://34.46.77.124:8006/purchase_orders?po_id=PO-AX17-4481"
curl -s "http://34.46.77.124:8006/ap_invoices?po_id=PO-AX17-4481"
curl -s "http://34.46.77.124:8006/receipts?po_id=PO-AX17-4481"
```

## Field Conventions

### Currency and Rounding
- All USD amounts rounded to **2 decimal places** (cents)
- Use `Decimal` with `ROUND_HALF_UP` for precise rounding
- Percentages rounded to **1 decimal place**
- Ratios/precision fields may require 4 decimal places

### Dates
- Format: `YYYY-MM-DD`
- Close dates, review dates, and as-of dates are typically specified in the task prompt or memo

### Sorting
- Unless specified as "set" (unordered), sort all lists **ascending**
- Common sort keys: `invoice_id`, `po_id`, `receipt_id`, `supplier_id`, `program_id`, `sku`

### Status Values
- **PO statuses**: `open`, `confirmed`, `partial_receipt`, `closed`, `cancelled`
- **Receipt statuses**: `accepted`, `accepted_with_note`, `inspection_hold`
- **Invoice statuses**: `approved`, `on_hold`, `pending_receipt`, `paid`
- **Supplier risk ratings**: `low`, `medium`, `watch`, `high`, `critical`
- **Approval actions**: `submitted`, `approved`, `returned`, `escalated`

## Common Calculations

### Three-Way Match
1. Compare `quantity_billed` (invoice) vs `quantity_received` (receipt)
2. Compare `unit_price` (invoice) vs `unit_price` (PO/contract)
3. If receipt missing → `NO_RECEIPT` exception
4. If qty variance → `QTY_VARIANCE` exception
5. If price variance → `PRICE_VARIANCE` exception

### Budget Headroom
```
remaining_budget = budget_cap - committed_amount
```
Note: The API returns `budget_cap` and `committed_amount` but NOT `remaining_budget` directly. Calculate it.

### Contract Ceiling
```
headroom = ceiling_amount - noncancelled_subtotal
requested_subtotal = requested_quantity * unit_price
```
Exclude POs with `status == "cancelled"` from noncancelled subtotal.

### Chargeback Amounts
```
chargeback_amount = basis_quantity * unit_cost
```

### Net Release Amount
```
net_release = invoice_total - approved_chargeback_amount - pending_chargeback_amount
```
For held invoices, net_release is typically `0.0` (not the invoice total).

## Controls and Decision Logic

### AP Close (train_003 pattern)
- **Opening balance**: Treat as `0.00` for slice-based close memos
- **Scheduled payments**: Sum payments with `status == "scheduled"` for the invoice
- **Balance status**:
  - `OPEN_HELD` if held_invoice_total > 0 and close_balance > 0
  - `OPEN_APPROVED` if releasable > 0 and no held
  - `FULLY_SCHEDULED` if close_balance ≈ 0
- **Reason codes** (alphabetical):
  - `APPROVED_THREE_WAY_MATCH` - only when no issues
  - `NO_RECEIPT` - when receipt missing
  - `QTY_VARIANCE` - when billed ≠ received
  - `SCHEDULED_PAYMENT_FOUND` - when payment exists

### Change Request (train_004 pattern)
- **Decision flow**:
  1. Check contract ceiling → `ceiling_ok`
  2. Check budget → `budget_ok` (remaining - requested_total)
  3. Check approval → `approval_ok` (latest action == "approved")
  4. Check supplier risk → `supplier_risk_ok` (no severe open events)
- **Decision enum**: `release_amendment`, `hold_for_budget`, `hold_for_approval`, `hold_for_supplier_risk`, `hold_for_budget_and_approval`, `reject_contract_mismatch`
- **Required actions**: Sort ascending, include `none` if no blockers

### AP Release (train_005 pattern)
- **Decisions**:
  - `release_net_after_approved_chargeback` - when approved chargeback exists
  - `hold_missing_receipt` - when no receipt on PO
  - `hold_pending_quality_chargeback` - when inspection hold or pending chargeback
- **Primary reasons**:
  - `approved_qty_chargeback` - for approved underage qty chargebacks
  - `approved_ap_quantity_variance` - for approved AP qty variance
  - `no_receipt_on_po` - missing receipt
  - `inspection_hold_pending_chargeback` - inspection hold with pending chargeback
- **Net release**: Set to `0.0` for held invoices, not the invoice total

### Receiving Review (train_002 pattern)
- Target specific receipt batch (e.g., `RCV-BLUE-14`)
- Calculate completion ratio: `received_qty / ordered_qty`
- Exception codes: `INVOICE_QTY_EXCEEDS_RECEIPT`, `PARTIAL_RECEIPT`, `SUPPLIER_WATCH_RISK`, `PRICE_MISMATCH`, `DAMAGE_REJECTION`, `NO_EXCEPTION`
- Decision fields: `batch_disposition`, `ap_action`, `receiving_action`, `supplier_action`

## Source Precedence
1. **ProcureOps API** is the system of truth for all live records
2. **Local memos/packets** provide target IDs and business context
3. **Chargeback registers** (when provided) supplement API data
4. **Environment access file** overrides any local URL references

## Pitfalls

### Common Mistakes
1. **Using wrong task_id**: train_001 requires `task_group_006_train_001`, others use `train_00X`
2. **Missing null fields**: `hold_code` can be `null` - include it explicitly
3. **Wrong rounding**: Use `Decimal` with `ROUND_HALF_UP`, not Python `round()`
4. **Forgetting to sort**: Most lists must be sorted ascending unless marked as "set"
5. **Budget remaining**: API doesn't return `remaining_budget` - calculate as `budget_cap - committed_amount`
6. **Net release on hold**: For held invoices, net_release should be `0.0`, not invoice_total minus chargebacks
7. **Missing receipts**: When `receipt_id` is null on invoice, quantity_received = 0
8. **Program scope**: Some tasks are slice-based (only named invoices), not full program
9. **Contract lookup**: PO may have `contract_id: null` - handle gracefully
10. **Approval events**: Filter by `object_type == "requisition"` and `object_id == req_id`

### Data Quality Notes
- PO-73xx style IDs may not exist in shared environment - use available IDs from packet
- Some POs share the same contract_id - aggregate properly
- Invoice `total` includes subtotal + tax + freight
- Receipt `lines` array contains quantity details per SKU
