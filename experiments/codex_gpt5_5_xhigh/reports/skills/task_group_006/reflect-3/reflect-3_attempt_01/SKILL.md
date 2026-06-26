---
name: reflect-3-procureops-controls
description: Solve ProcureOps control, reconciliation, sourcing-readiness, AP-close, change-control, and AP-release JSON tasks using task inputs plus the remote ProcureOps API.
---

# Reflect-3 ProcureOps Controls

Use this skill when a task asks for a JSON control file or reconciliation packet from ProcureOps records.

## Operating Rules

- Read the task prompt, answer template, and task-local payloads first. The answer template is the output contract: preserve required keys, enum values, ordering rules, nullability, rounding, and JSON-only output.
- Use the ProcureOps API as the system of record for operational entities: programs, suppliers, items, requisitions, approvals, contracts, purchase orders, receipts, invoices, payments, budgets, and vendor-risk events.
- Treat local payloads as authoritative for task scope, requested as-of/review dates, target IDs, local-only registers, alias notes, and business-control assumptions. Do not broaden the scope beyond memo-named anchors or target IDs unless the prompt explicitly asks for a wider search.
- If a task-level environment note conflicts with a prompt example URL, follow the environment note or runner-provided base URL.
- Return only the JSON object requested. Do not add prose, citations, diagnostics, or extra fields.

## Source Precedence

1. The answer template controls shape, enum spelling, precision, and list ordering.
2. The prompt and local payloads control target scope, review/as-of dates, local registers, aliases, and business rules not present in the API.
3. ProcureOps API records control live operational values and statuses.
4. Derived calculations come last and should be traceable to the scoped local IDs and API records.

When local memo anchors name a current package, use those anchors for package-level fields. Same-requisition or same-supplier records are supporting context only unless the template asks for them, such as excluded same-PO receipts or supplier-level risk context.

## Record Joining

- Join invoices to POs by `po_id`; join invoice lines and PO lines by `po_line_id` and `sku`.
- Join receipts by `receipt_id` when present; otherwise use `po_id` only when the task names that receipt or asks for same-PO receipt context.
- Join contracts by `contract_id`, then verify supplier, SKU, status, price type, and unit price.
- Join suppliers by `supplier_id`; supplier name, status, payment terms, and risk rating come from the supplier record.
- Join approval events by requisition/object ID and use the latest event by date for approval-state checks.
- Join payments by `invoice_id`; apply the task's cutoff date and payment status rules.
- Use budget snapshots for dated budget checks when available; otherwise use program budget fields.

## Time And Scope Filters

- Apply the requested as-of or review date to receipts, invoices, risk events, approvals, and scheduled payments.
- For payment close tasks, only payments scheduled through the stated cutoff reduce the close balance.
- For risk context, include open or monitoring supplier-risk events as of the review date; exclude closed events and future events.
- Keep target slices narrow: named invoices, POs, receipts, requisitions, and programs only, unless a field explicitly asks for related or excluded records.

## Calculation Conventions

- Round USD amounts to cents. Use the template precision for quantities, ratios, and percentages.
- Receipt reconciliation:
  - `short_qty_vs_po = ordered_qty - received_qty`.
  - `unreceived_billed_qty = max(billed_qty - received_qty, 0)`.
  - `receipt_completion_ratio = received_qty / ordered_qty`.
  - Goods exposure uses the PO unit price unless the template says to use invoice or contract price.
  - Contract price match compares contract unit price to PO or invoice unit price as requested.
- AP invoice close:
  - `quantity_variance = quantity_billed - quantity_received`.
  - `quantity_variance_pct` is the variance divided by PO quantity, expressed as a percent.
  - A no-receipt invoice should use the `NO_RECEIPT` reason code without also adding `QTY_VARIANCE` unless the template separately requires both.
  - `net_balance_impact = invoice_total - scheduled_payment_amount`.
  - Supplier close balance is opening balance plus scoped invoice totals minus scoped scheduled payments.
- Change control:
  - Contract usage excludes cancelled purchase orders.
  - Contract exposure is usually line subtotal before tax and freight.
  - Budget exposure is line subtotal plus tax unless the local business rules include freight.
  - Remaining budget is budget cap minus committed amount.
  - Maximum affordable quantity is the floor of remaining budget divided by unit cost including applicable tax.
  - Use the latest approval event and the payload's allowed good actions to set approval status.
  - Supplier watch ratings are context unless the payload says they block release; severe open supplier-risk events usually block release.
- AP release with chargebacks:
  - Local chargeback registers can be authoritative when the API has no chargeback endpoint.
  - Approved chargebacks reduce the releasable invoice amount.
  - Pending quality chargebacks keep the invoice on hold and do not contribute to release totals.
  - Missing receipts keep the invoice on hold and should trigger receiving follow-up.
  - Same-PO receipts outside the target packet belong in excluded/supporting fields when requested, not in in-scope receipt lists.

## Decision Habits

- Prefer controlled codes over narrative explanations.
- Use `HOLD`/hold decisions for open AP holds, missing receipts, unresolved quality holds, pending chargebacks, missing contracts, failed budget checks, and failed approvals.
- Use release decisions only when the scoped invoice has a clean match or an approved netting mechanism.
- For sourcing readiness, treat active contracts, approved/latest-good approvals, sufficient budget, receipts, clean AP status, and no blocking supplier risk as readiness signals; classify missing contracts or missing receipts as not-ready conditions.
- For committee or workflow owner fields, choose the team responsible for clearing the dominant blocker: buyer for commercial basis gaps, AP team for invoice holds, quality/receiving for receipt or inspection issues, finance/program owner for budget or approval gaps.

## Output Hygiene

- Sort lists when the template says to sort or treat them as sets. For IDs, use lexicographic ascending order unless a different order is specified.
- Use `null` for nullable scalar fields and `[]` for empty lists.
- Keep enum casing exactly as shown in the template.
- Include local payload filenames or source labels only when the template requests evidence/source lists.
- Do not include judge endpoints, judge feedback, train answers, gold answers, evaluator details, or test-time judge usage in outputs or generated skills.
