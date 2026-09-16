---
name: procureops-packet-builder
description: Build structured ProcureOps JSON packets from task-local memos/templates and live API records for sourcing nomination, receiving closeout, AP close reconciliation, contract change control, and AP release or hold workflows. Use when a task mentions ProcureOps, the shared task environment, a local memo or answer template, or asks for a JSON decision file, reconciliation packet, hold or release queue, or nomination packet.
---

# ProcureOps Packet Builder

## Overview
Produce one JSON object that matches the task template exactly. Treat the memo and answer template as the output contract; treat ProcureOps API data as the source of truth for records, IDs, and calculations.

## Workflow
1. Read `input/payloads/answer_template.json` and the local memo first.
2. Extract the scope IDs, dates, and any explicit business rules from the memo.
3. Use the runner-provided ProcureOps base URL and read `/manifest` when you need current anchor IDs or record counts.
4. Fetch only the records in scope from ProcureOps.
5. Cross-check memo claims against live records; prefer live records when they conflict.
6. Compute every field from source data, not from assumptions.
7. Sort set-like lists ascending unless the template says otherwise.
8. Round USD amounts to cents and ratios or percentages to the precision named by the template.
9. Return only the final JSON object. No prose, no markdown, no code fences.

## Common Rules
- Keep `null` values when the template allows them.
- Use only the allowed enum values and controlled codes from the template.
- Deduplicate any set-like list before sorting it.
- Preserve source record IDs exactly as returned by ProcureOps.
- Use task-payload filenames as evidence references when the template asks for reviewed inputs or supporting files.
- If the memo includes stale aliases or placeholder family names, map them to live IDs from ProcureOps and treat the alias note as supporting context only.

## Packet Families

### Sourcing Nomination Packets
- Use the package memo to identify each line SKU, requisition, supplier, contract, PO, receipt, invoice exception, and supplier-risk record in scope.
- Set `nomination_decision` from the full readiness picture, not from a single flag.
- Use `hold` for hard blockers such as missing contract, late due date, pending receipt, or open supplier risk.
- Use `conditional_nomination` when the line is viable but still carries AP hold, supplier-watch, or similar soft constraints.
- Use `nominate` only when the line is clear.
- Keep `blocker_codes` sorted and limited to the template vocabulary.
- Keep `committee_action` aligned with the line decisions and the memo's escalation intent.

### Receiving Closeout Packets
- Reconcile ordered, received, billed, short, and unreceived quantities line by line.
- Use `quantity_received = 0` and `hold_code = NO_RECEIPT` when no receipt exists.
- Compute `received_goods_value`, `unreceived_goods_value`, `invoice_subtotal`, `invoice_freight`, `invoice_tax`, and `invoice_total` from the live quantities and prices.
- Choose the disposition enums to match the reconciliation outcome: partial hold for variance, full release only when the receipt and invoice match, and manual recount or rejection only when the template allows it.
- Keep `exception_codes` limited to the allowed values and sort them alphabetically.

### AP Close Packets
- Sort invoices, supplier balances, and program summaries by the template's ordering rules.
- Set `hold_decision`, `hold_code`, `release_to_payment`, and `scheduled_payment_amount` from invoice status, receipt match, and any payment already scheduled in ProcureOps.
- Compute `net_balance_impact = invoice_total - scheduled_payment_amount`.
- Build vendor balances from opening balance, invoice total, scheduled payments, held invoice total, releasable invoice total, and close balance.
- Keep the hold and release queues in sync with the invoice decisions.

### Contract Change-Control Packets
- Use the memo's requested quantity, tax rate, and source requisition to calculate contract exposure and budget exposure.
- Keep contract ceiling calculations on subtotal before tax and freight.
- Set `decision` to `release_amendment` only when contract, budget, approval, and supplier-risk checks all pass.
- Otherwise choose the narrowest hold enum that matches the blockers.
- Compute `max_quantity_with_current_budget` from the remaining budget and the memo's tax rate.
- Treat watch-level open events as context unless the template or live data says the risk check fails.
- Populate supporting IDs with sorted PO and approval IDs, and list cancelled POs separately when the memo or live data excludes them.

### AP Release and Chargeback Packets
- Treat the chargeback register, request notes, and memo aliases as supporting context; treat live ProcureOps records as authoritative.
- Reconcile each invoice into release, hold pending quality chargeback, or hold missing receipt.
- Separate approved chargebacks from pending chargebacks and use only approved amounts in release totals.
- Capture receipt exceptions with the allowed codes and chargeback statuses.
- Keep authoritative sources distinct from supporting-only sources.
- Record any same-PO or alias-based exclusions explicitly in the excluded-ID fields when the template asks for them.

## Final Check
- Verify every required top-level key from the template exists.
- Verify enum spellings, sorted arrays, nulls, and rounding before returning.
- Return only the JSON object.
