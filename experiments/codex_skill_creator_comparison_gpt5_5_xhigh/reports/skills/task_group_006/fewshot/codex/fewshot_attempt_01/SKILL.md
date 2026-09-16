---
name: procureops-task-solver
description: Solve ProcureOps task-group JSON packets from local memos and the shared task API. Use when prompts reference ProcureOps, the task environment, and templates for nomination readiness, receiving closeout, AP close, change-control, or AP release decisions.
---

# ProcureOps Task Solver

## Overview
Use this skill to turn a task-local memo or packet plus the ProcureOps API into the exact JSON requested by the template.

## Procedure
1. Read the prompt, the answer template, and every local payload file first.
2. Read `environment_access.md` to get the task API base URL and allowed endpoints.
3. Call `GET /manifest` first, then fetch only the record collections needed for the packet.
4. Treat the API as source of truth. Use local payloads for target IDs, dates, aliases, chargeback excerpts, and other task-scoped hints.
5. Resolve IDs outward from the memo to programs, suppliers, items, requisitions, contracts, purchase orders, receipts, invoices, approvals, budget snapshots, payments, and vendor-risk events.
6. Fill the answer template exactly. Return JSON only.

## Shared Rules
- Preserve field names, enum spellings, and required ordering from the template.
- Sort IDs and row arrays exactly as requested.
- Treat set-like lists as deduplicated sets unless the template says otherwise.
- Round USD to cents; keep ratios, percentages, and counts at the template precision.
- Prefer live record IDs over stale aliases or supporting notes. Put non-authoritative clues only in fields meant for support records.
- Copy required fixed values from the template exactly; do not invent new keys.
- When the template includes source-tracking fields, place live API record IDs in authoritative/evidence fields and local payload filenames in support-only fields.

## Nomination Readiness Packets
- Find the nominated supplier, requisition, contract basis, package PO(s), receipts, invoice exceptions, approvals, budget headroom, and open supplier risk.
- Classify each line with the strongest blocker present.
- Use `hold` or `not_ready` for hard blockers such as missing contract, no receipt, late due date, or unresolved risk.
- Use `conditional_nomination` or `at_risk` when the line is otherwise supportable but still has AP, watch, or exception clearance issues.
- Set committee action from the line-level outcomes and overall readiness.

## Receiving Closeouts
- Reconcile ordered, received, rejected, and billed quantities.
- Compare PO, contract, and invoice prices and mark the price match explicitly.
- Compute received goods value, unreceived value, invoice totals, and AP hold status.
- Choose batch disposition, supplier action, and exception codes from the live records.

## AP Close Reconciliations
- For each target invoice, compare invoice total to scheduled payments through the close date.
- Use opening balance plus invoice total minus scheduled payments for close balance.
- Put released invoices in the payment release queue and held invoices in the payment hold queue.
- Use controlled reason codes only, and keep them sorted when required.

## Change-Control Files
- Compare the requested change against the active contract, ceiling, requisition approval trail, budget snapshot, and supplier risk.
- Calculate requested subtotal, tax, total, remaining budget, and blocker count from the live records.
- Release only when contract, budget, approval, and risk checks all pass.

## AP Release Files
- Use the chargeback register plus the memo to separate approved from pending chargebacks.
- Release invoices only when the net amount is ready and no hard receipt hold remains.
- Treat missing receipt as a hold.
- Keep supporting alias notes separate from authoritative sources when the template asks for both.

## Output
Return a single JSON object only. Do not add prose, markdown, or code fences.
