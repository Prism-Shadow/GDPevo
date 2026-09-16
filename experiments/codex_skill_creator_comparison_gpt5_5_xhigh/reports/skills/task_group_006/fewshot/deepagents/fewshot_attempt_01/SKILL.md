---
name: procureops-control-packets
description: Read ProcureOps task prompts and payloads, query the live ProcureOps API, and produce strict JSON packets for sourcing nominations, receiving and AP closeouts, change-control decisions, release or hold queues, budget checks, and related procurement operations.
---

# ProcureOps Control Packets

## Overview
Produce exact JSON that matches the task template. Treat the local prompt and payloads as the schema contract; treat the ProcureOps API as the source of truth.

## Workflow
1. Read `prompt.txt`, every file under `input/payloads/`, and `answer_template.json`.
2. Extract the task date, anchor IDs, required sorts, enum values, and any notes marked as supporting only.
3. Query only the records needed from the live ProcureOps API:
   - `/manifest`
   - `/programs`
   - `/suppliers`
   - `/items`
   - `/contracts`
   - `/purchase_requisitions`
   - `/purchase_orders`
   - `/receipts`
   - `/ap/invoices`
   - `/ap/payments`
   - `/approvals`
   - `/budget_snapshots`
   - `/vendor_risk_events`
4. Build an evidence map keyed by record ID. Prefer API records over memo text whenever they conflict.
5. Populate the template exactly. Preserve required key order, nested field order, and any list ordering rules from the template.
6. Return JSON only.

## Core Rules
- Use the task date or review date as the cutoff for open items, approvals, receipts, payments, and risk events.
- Treat set-like lists as deduplicated sets, then sort only when the template says sorted or ascending.
- Round USD amounts to cents unless the template asks for different precision.
- Keep ratios and percentages at the precision requested by the template.
- Use canonical IDs from the API. Do not invent surrogate IDs.
- Use `null` only where the template allows it.
- When a memo names a stale alias or supporting-only note, use it only as a hint.

## Common Calculations
- `quantity_variance = billed_qty - received_qty`
- `quantity_variance_pct = quantity_variance / po_qty * 100`
- `receipt_completion_ratio = received_qty / ordered_qty`
- `received_goods_value = received_qty * unit_price`
- `unreceived_goods_value = short_qty * unit_price`
- `invoice_total = subtotal + freight + tax`
- `net_balance_impact = invoice_total - scheduled_payment_amount`
- `close_balance = opening_balance + invoice_total - scheduled_payments`
- `approved_chargeback_amount = basis_quantity * unit_cost`
- `net_release_amount = invoice_total - approved_chargeback_amount`

## Packet Patterns
### Sourcing nomination
- Identify the current package anchors from the local memo.
- Resolve one supplier per line from live records.
- Classify each line by contract coverage, requisition approval, PO/receipt/invoice state, budget headroom, and supplier risk.
- Derive line blockers from the actual unresolved conditions, not from memo wording.
- Roll line decisions into committee queues only after the line status is known.

### Receiving and AP close
- Reconcile ordered, received, rejected, and billed quantities per line.
- Separate invoice holds caused by quantity variance, missing receipt, price mismatch, or supplier risk.
- Use scheduled payments through the close date to reduce the supplier close balance.
- Keep held invoices off the release queue unless the template says otherwise.

### Change control
- Compare requested quantity and requested subtotal against contract headroom and budget remaining.
- Fail the release if approval is missing, budget goes negative, or supplier risk requires a hold.
- Report only the blocker-driven decision and the required actions that clear it.

### Release and chargeback files
- Split approved chargebacks from pending chargebacks.
- Keep receipt scope narrow: include only receipts tied to the invoice under review.
- Exclude same-PO receipts only when the packet asks for them explicitly.
- Compute net release amounts after approved chargebacks only.

## Final Checks
- Verify every required top-level key exists.
- Verify every required nested key exists.
- Verify list order against the template.
- Verify numeric precision before emitting JSON.
- Do not include prose outside the JSON object.
