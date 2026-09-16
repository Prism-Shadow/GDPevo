---
name: procureops
description: ProcureOps procurement operations skill. Use for sourcing nomination readiness, receiving closeout, AP payment-hold reconciliation, contract change control, AP release and exception review, or any task that requires cross-referencing ProcureOps purchase orders, receipts, invoices, contracts, suppliers, budgets, approvals, and risk events. Use this skill whenever the user mentions ProcureOps, procurement data, purchase orders, AP holds, receiving reconciliation, vendor risk, or budget/contract analysis against operational records.
---

# ProcureOps Procurement Operations

Analyze ProcureOps operational data by cross-referencing entities across the REST API and applying procurement-domain decision rules.

## Quick start

Every ProcureOps task follows the same core pattern:

1. **Read payload files** -- local memos, packets, or templates under `input/payloads/` that identify target entities (PO IDs, receipt IDs, invoice IDs, program IDs) and business rules.
2. **Query the API** -- fetch all relevant records from the ProcureOps endpoints listed in `references/api_schema.md`. Always fetch full endpoint collections; filter client-side by the IDs named in payloads or discovered through cross-referencing.
3. **Cross-reference entities** -- use `references/computations.md` to trace entity relationships (PO to receipt to invoice to payment, program to budget, supplier to risk events, requisition to approvals).
4. **Compute and decide** -- apply formulas from `references/computations.md` for financials, headroom, variances, and decision rules.
5. **Produce JSON** -- return only JSON matching the provided answer template. No prose outside the JSON object.

## When the answer template is provided as a schema

If the template uses `"type"`, `"required_keys"`, `"allowed_values"`, and `"ordering"` fields (a schema-style template), use it as a structural spec rather than literal default values. Produce JSON that satisfies the schema exactly:

- Include every `required_key` in the specified object.
- Use only values from `allowed_values` or `allowed` arrays where present.
- Sort lists according to the `ordering` instruction.

If the template is a literal JSON with placeholder strings like `"string"` or `"YYYY-MM-DD"`, fill in real values while preserving the structure, key order, and field types.

## Cross-referencing entities

Entity relationships in ProcureOps form natural chains. Start from the target IDs in the payload and trace outward.

**Chains to extract:**
- `po_id` to purchase order: lines, supplier_id, contract_id, requisition_id, program_id, subtotal, tax, total, status, due_date
- `receipt_id` to receipt: po_id, lines (with received/rejected quantities), supplier_id, warehouse_id, status
- `invoice_id` to invoice: po_id, receipt_id, lines, status, hold_code, subtotal, freight, tax, total
- `supplier_id` to supplier: name, risk_rating, status, payment_terms
- `program_id` to program: budget_cap, committed_amount, owner, status
- `contract_id` to contract: ceiling_amount, unit_price, price_type, supplier_id, sku, status
- `requisition_id` to approvals (filter where object_id = requisition_id): latest action, actor, event_date

**When an ID is not directly available** (e.g., finding all POs for a program), iterate the full collection and filter by the linking field.

## Handling missing or incomplete records

- If a PO has no contract (`contract_id: null`), treat the commercial basis as absent. Set `commercial_basis_id` to `null`.
- If an invoice has no associated receipt (`receipt_id: null`), the invoice is `pending_receipt` and no three-way match is possible. Use `0.00` for received quantity and `0.0` for receipt completion ratio.
- If a supplier has no open risk events, the event list is empty.
- Treat receipt quantities of 0 as "no receipt" evidence.
- When a receipt ID exists for a PO under a different invoice (e.g., duplicate receipts for the same PO), list it as an `excluded_same_po_receipt_ids` entry on the release decision.
- When a PO has no receipt at all in the API, represent the missing receipt with a synthetic receipt entry using the resolution_status `missing_receipt`.

## Financial precision

All USD amounts must be rounded to cents (2 decimal places). Ratios like `receipt_completion_ratio` use 4 decimal places unless the template specifies otherwise. Percentage fields like `quantity_variance_pct` use 1 decimal place.

Use standard rounding (round half up). Compute tax as `subtotal * (tax_rate_percent / 100)` and round to cents. Total = subtotal + freight + tax.

## Sources and authority

The ProcureOps API is the system of record. Local payload files provide task-specific target IDs and business context only, not operational data. When a local memo's claim conflicts with API data, the API wins.

For tasks with a chargeback register in the local payload, the register is authoritative for chargeback amounts and statuses. Use it to net against invoice totals.

When a local payload provides an `answer_template.json`, adhere to it exactly for structure, field names, types, enums, and ordering.

## References

- [references/api_schema.md](references/api_schema.md): Endpoint-by-endpoint field reference for all 12 ProcureOps collections.
- [references/computations.md](references/computations.md): Formulas, decision rules, blocker logic, and cross-referencing patterns.
