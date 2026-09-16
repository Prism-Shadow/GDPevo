---
name: procureops-casework
description: Resolve ProcureOps procurement casework into strict JSON from a task memo and the live ProcureOps API. Use this whenever the user asks for a sourcing nomination packet, receiving or AP closeout, contract or budget change-control file, invoice release decision, or any similar procurement reconciliation grounded in live ProcureOps records, even if they only mention AP holds, receipts, purchase orders, vendor risk, or budget snapshots.
compatibility: Requires network access to the runner-provided ProcureOps base URL and standard JSON-aware shell tooling.
---

# ProcureOps Casework

Use this skill for structured procurement tasks where the answer must be a JSON object matching a local template and backed by live ProcureOps records.

## Workflow

1. Read the task prompt, every file under `input/payloads/`, and the answer template before you query anything.
2. Identify the target IDs, date, program, supplier, PO, receipt, invoice, requisition, contract, batch, or change-request scope from the memo and template.
3. Treat the ProcureOps API as the source of truth. If the task exposes a manifest or anchor map, read it first to confirm the environment, then query the smallest set of endpoints that can satisfy the template.
4. Build a record map keyed by exact IDs. Cross-check linked records before you compute derived fields.
5. Fill the template literally. Preserve required values, allowed enums, nullability, and any requested sort order.
6. Validate every derived number and list ordering before you answer.
7. Return raw JSON only. No prose, no markdown, no code fences.

## Common endpoint families

Use only the record families the template actually needs:

- `/programs` and `/budget_snapshots` for owner, budget cap, committed amount, remaining budget, and snapshot IDs.
- `/suppliers` and `/vendor_risk_events` for supplier status, risk rating, open events, and severe events.
- `/contracts`, `/purchase_requisitions`, and `/purchase_orders` for requisition lineage, contract usage, ceiling exposure, and PO scope.
- `/receipts` for ordered-versus-received reconciliation and receipt status.
- `/ap/invoices` and `/ap/payments` for invoice totals, holds, release queues, and scheduled payments.
- `/approvals` for the latest approval event and approval state.
- `/items` when the template needs SKU-level mapping or line reconciliation.

## Decision patterns

Most ProcureOps tasks in this family reduce to one of these shapes:

- Sourcing nomination and readiness: identify the selected supplier for each line, the current blocker set, and whether the line is ready, at risk, or held.
- Receiving and AP closeout: reconcile ordered, received, billed, and rejected quantities; carry forward hold codes and exception records; separate release-ready from blocked invoices.
- AP close and vendor balance: compute invoice totals, scheduled payments, hold and release queues, supplier balances, and program totals.
- Change control and amendment review: compare requested quantity or spend against contract ceiling and program budget, then fold in approval state and supplier-risk context.
- Release/hold packets: combine receiving exceptions, chargebacks, AP holds, and net release amounts without inventing new IDs.

## Arithmetic and ordering

- Use live values, not memo prose, for every derived field.
- Round currency to cents unless the template says otherwise.
- Round percentages and ratios to the precision requested by the template.
- Common formulas:
  - `ordered - received` for shortage
  - `billed - received` for billed-versus-received variance
  - `received / ordered` for completion ratio
  - `subtotal + freight + tax` for invoice total
  - `invoice_total - scheduled_payment_amount` for net balance impact
  - `budget_cap - committed_amount` for remaining budget
  - `headroom_before_change - requested_subtotal` for contract headroom after change
  - `remaining_budget - requested_total` for budget after change
- Sort set-like lists deterministically, usually ascending by ID, and deduplicate them before output.
- If the template says a field is `null` or `none`, use that literal sentinel instead of fabricating a value.
- Keep every record ID exact and case-sensitive.

## Template discipline

- Treat the answer template as the contract.
- Do not add fields that are not in the template.
- Do not omit required fields.
- Use only the allowed enum values and reason codes.
- If the memo notes an alias, stale identifier, or missing family of IDs, use the shared live IDs from ProcureOps and reflect the mapping only in the fields the template provides for evidence or supporting sources.

## Final check

Before responding, verify:

- The output schema matches the template exactly.
- Every ID came from the live API or the task payloads.
- Every computed amount reconciles.
- Every list is in the required order.
- The final message is JSON only.
