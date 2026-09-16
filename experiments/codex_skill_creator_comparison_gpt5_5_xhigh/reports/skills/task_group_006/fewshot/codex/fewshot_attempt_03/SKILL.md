---
name: procureops-reconciliation
description: Solve ProcureOps sourcing, receiving, AP close, change-control, and invoice-release reconciliation tasks. Use when a task provides a local memo or answer_template and asks Codex to query the read-only ProcureOps API, join suppliers, items, programs, contracts, requisitions, purchase orders, receipts, AP invoices/payments, approvals, budgets, and vendor-risk records, compute USD or quantity decisions, and return exact JSON only.
---

# ProcureOps Reconciliation

Use this skill to produce controlled JSON answers for ProcureOps operational review tasks.

## Workflow

1. Read the prompt, `input/payloads/answer_template.json`, and every local payload. Treat the template as the output contract. Treat local payloads as scope, target IDs, dates, and any task-local register data that is not available from the API.
2. Query the API named in the prompt. The API is the source of truth for operational records unless the prompt explicitly says a local payload field is authoritative for a task-local control such as a chargeback register or stale alias note.
3. Build indexes by ID before calculating: suppliers by `supplier_id`, programs by `program_id`, contracts by `contract_id`, requisitions by `requisition_id`, purchase orders by `po_id`, receipts by `receipt_id` and `po_id`, invoices by `invoice_id` and `po_id`, payments by `invoice_id`, approvals by `object_id`, budgets by `program_id`, risks by `supplier_id`.
4. Filter to the task scope from the local payload. For date-bounded tasks, include only records with relevant dates on or before the as-of or close date unless the template asks for future scheduled activity through a stated horizon.
5. Calculate fields from joined records, then shape the result exactly to the template. Use JSON types, enum values, required keys, and list ordering from the template.
6. Return only the final JSON object. Do not include prose, markdown fences, citations, or source notes outside the requested JSON.

## API Helper

Use [scripts/fetch_procureops.py](scripts/fetch_procureops.py) when you need a local dump or quick ID lookup. From the skill root, run:

```bash
python scripts/fetch_procureops.py "$TASK_ENV_BASE_URL" --out /tmp/procureops.json
python scripts/fetch_procureops.py "$TASK_ENV_BASE_URL" --id INVOICE-ID --id PO-ID
```

The script uses only Python standard library modules and the read-only endpoints listed in the task environment.

## Calculation Rules

Read [references/procureops_rules.md](references/procureops_rules.md) before solving any task that requires derived quantities, financial totals, readiness decisions, AP hold/release queues, amendment checks, or receiving exception classifications.

## Guardrails

- Do not assume the local memo is complete. Use it to identify anchors and local-only facts, then verify operational facts against API records.
- Do not answer from memory of another task. Recompute against the current prompt, current payloads, and current API data.
- Preserve nulls where the template permits null; use empty lists for no matching evidence when the template expects a list.
- Round money to cents and percentages/ratios to the precision stated by the template. Prefer decimal arithmetic for currency.
- Sort output arrays exactly as specified. If the template describes a list as a set without a custom order, sort strings ascending for stable output.
