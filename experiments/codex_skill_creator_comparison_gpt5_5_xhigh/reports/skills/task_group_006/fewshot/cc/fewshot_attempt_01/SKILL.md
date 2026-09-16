---
name: procureops-packets
description: Solve ProcureOps packet tasks that ask for a readiness packet, closeout reconciliation, change-control decision, AP release file, AP close, or similar structured JSON output built from the shared ProcureOps API and task-local payloads. Use this whenever a prompt mentions ProcureOps, TASK_ENV_BASE_URL, input/payloads/answer_template.json, or one of those packet types.
---

# ProcureOps Packets

Use this skill for structured ProcureOps JSON tasks. The output contract is always the same: read the local payloads and answer template, query the live ProcureOps API, compute the requested fields, and return JSON only.

## Workflow

1. Read `input/prompt.txt`, every file under `input/payloads/`, and `input/payloads/answer_template.json` first. Treat the template as the schema contract.
2. Read `environment_access.md` to get `TASK_ENV_BASE_URL`.
3. Fetch `GET /manifest` if you need to confirm the environment or record counts.
4. Query only the endpoints the packet needs: `/items`, `/suppliers`, `/programs`, `/contracts`, `/purchase_requisitions`, `/purchase_orders`, `/receipts`, `/ap/invoices`, `/ap/payments`, `/approvals`, `/budget_snapshots`, `/vendor_risk_events`.
5. Build an evidence map keyed by the IDs named in the memo and template. Prefer live records over local notes when they conflict.
6. Compute the derived fields from live records and the template rules.
7. Serialize the final object exactly to the template shape. No prose, no markdown, no extra keys.
8. Before returning, sort, deduplicate, and round exactly as requested.

## Packet Families

- Nomination or readiness packet: combine program, supplier, item, requisition, contract, PO, receipt, invoice, approval, budget, and risk records. Derive line readiness, blocker codes, and committee actions from the strongest unresolved blocker.
- Receiving or AP closeout: reconcile ordered vs received vs billed quantities, invoice hold state, supplier risk, and financial exposure.
- AP close: reconcile invoice decisions, scheduled payments, supplier balances, and program totals. Use the payment cutoff in the prompt, not the calendar date.
- Change-control: compare requested contract usage and program budget against live contract, approval, and risk state. Release only when all blocker checks pass.
- AP release file: net approved chargebacks against invoice totals, keep pending-quality items on hold, and separate authoritative record sources from supporting-only notes.

## Calculation Rules

See [references/procureops_workflow.md](references/procureops_workflow.md) for the recurring formulas and field-level checks.

## Final Checks

- Every required top-level key is present.
- Every list follows the template's ordering rule.
- Every ID matches a live record or an explicitly named local payload item.
- Every supporting note stays out of authoritative totals unless the template explicitly asks for it.
- Every enum value comes from the template's allowed set.
- If a record is missing, represent that only in the slot the template allows.
