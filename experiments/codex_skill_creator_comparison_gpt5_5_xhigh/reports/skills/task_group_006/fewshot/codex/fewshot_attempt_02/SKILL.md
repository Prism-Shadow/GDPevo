---
name: procureops-reconciliation
description: Solve ProcureOps sourcing nomination, receiving closeout, AP close, change-control, and release JSON tasks from a local packet or memo plus the live ProcureOps API. Use when a prompt asks for a strict JSON object that reconciles procurement records, budgets, approvals, receipts, invoices, vendor risk, or chargebacks.
---

# ProcureOps Reconciliation

## Overview
Use this skill for packet-driven ProcureOps tasks that must return JSON only. Treat the memo or packet as scoping guidance and the ProcureOps API as the source of truth.

## Workflow
1. Read the prompt and answer template first. Capture required keys, allowed enums, sort order, precision, and the as-of date.
2. Use the packet or memo to identify target IDs, aliases, and any special scope notes. Use live API records for values.
3. Query only the record families the template needs: programs, suppliers, items, requisitions, contracts, purchase orders, receipts, invoices, approvals, payments, budget snapshots, vendor-risk events, and chargebacks or hold records.
4. Populate the JSON directly from the template. Do not add prose, commentary, markdown, or extra keys.
5. Normalize values exactly:
   - Round USD to cents unless the template asks for another precision.
   - Sort ID lists ascending unless the template says they are sets or already sorted by a field.
   - Use `0.00`, `0`, `null`, or `[]` only when the template or prompt calls for them.
   - Keep enum strings exact.
6. Compute common fields from the template basis:
   - Quantities: billed, received, variance, shortage, unreceived billed quantity, ratios, and percentage variances.
   - AP close: `net_balance_impact = invoice_total - scheduled_payment_amount`.
   - Change control: `requested_subtotal = quantity × unit_price`, `requested_tax = subtotal × tax_rate`, `requested_total = subtotal + tax (+ freight only if provided)`, `budget_after_change = remaining_budget - requested_total`, and `max_quantity_with_current_budget = floor(remaining_budget / (unit_price × (1 + tax_rate)))` when no freight is included.
   - Contract usage: exclude cancelled purchase orders when checking usage or headroom.
7. Choose decisions from evidence, not from packet wording alone. Typical failure signals are missing contract, AP hold, pending receipt, late due date, open supplier risk, incomplete approval, budget shortfall, quantity variance, or missing receipt.
8. If the packet distinguishes authoritative and supporting-only sources, keep that distinction literal in the output and use supporting notes only to map aliases or scope.
9. Before answering, verify ordering, precision, IDs, and source classifications one last time.

## Template Shapes
Match the prompt to the output shape before you compute anything.

- Nomination packet: `program_summary`, `nomination_lines`, `committee_action`
- Receiving closeout: `inspection_summary`, `line_reconciliation`, `invoice_review`, `financials`, `decision`, `supplier_risk_context`, `evidence`
- AP close: `invoice_decisions`, `vendor_balances`, `program_summary`, `payment_hold_queue`, `payment_release_queue`, `total_close_balance`
- Change control: `contract_check`, `program_budget_check`, `approval_check`, `supplier_risk_check`, `supporting_ids`, `required_actions`, `summary`
- Release packet: `release_decisions`, `receiving_exceptions`, `summary`
