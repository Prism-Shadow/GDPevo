---
name: procureops-reconciliation
description: Build JSON-only ProcureOps sourcing, receiving, AP close, AP release, contract-change, budget, approval, and supplier-risk reconciliation answers from task-local payloads plus the shared ProcureOps API. Use when prompts mention ProcureOps endpoints, purchase orders, receipts, invoices, payments, contracts, budgets, approvals, vendor risk, sourcing nomination readiness, receiving closeout, AP hold/release queues, or change-control decision files.
---

# ProcureOps Reconciliation

## Workflow

1. Read the prompt, every file under `input/payloads/`, and the answer template before calling the API. Treat local payloads as the source for target IDs, dates, chargeback/register excerpts, and task-specific business rules. Treat ProcureOps API records as the operational source of truth.
2. Fetch the required API collections from the base URL supplied by the task runner. The helper at [scripts/fetch_procureops.py](scripts/fetch_procureops.py) can download the standard collections into one JSON file.
3. Read [references/procureops_rules.md](references/procureops_rules.md) when computing joins, quantities, money, risk state, approval state, AP decisions, nomination readiness, receiving exceptions, or change-control decisions.
4. Build the answer object directly from the template. Preserve required top-level keys and controlled enum strings. Add no prose outside the final JSON.
5. Sort list fields ascending unless the template says records are matched by a key or treated as sets. Round USD amounts to cents and percentages or ratios to the template precision.

## API Handling

Use only endpoints allowed by the task environment. Standard ProcureOps responses wrap records as:

```json
{"count": 0, "results": []}
```

Index records by their native IDs (`supplier_id`, `sku`, `program_id`, `contract_id`, `requisition_id`, `po_id`, `receipt_id`, `invoice_id`, `payment_id`, `event_id`, `snapshot_id`) and keep nested PO, receipt, and invoice lines available for line-level calculations.

## Answer Discipline

Do not assume memo IDs are sufficient evidence. Cross-check each target against API records, and note missing operational records only in fields the template provides for that purpose. Use the template's exact `required_value` for `task_id` when present. Omit explanatory text unless the template explicitly asks for narrative fields.
