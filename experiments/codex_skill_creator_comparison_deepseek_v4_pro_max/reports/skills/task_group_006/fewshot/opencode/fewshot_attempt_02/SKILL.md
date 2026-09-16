---
name: procureops
description: |
  Resolve ProcureOps procurement operations tasks by querying a shared REST API
  and producing structured JSON answer files. Use whenever the task mentions
  ProcureOps, a ProcureOps API, procurement readiness, sourcing nomination,
  receiving closeout, AP close desk, change-control decision, AP release file,
  invoice hold/release, three-way match, vendor balance reconciliation,
  chargeback netting, or any procurement operations workflow that requires
  cross-referencing suppliers, items, programs, contracts, purchase
  requisitions, purchase orders, receipts, invoices, payments, approvals,
  budget snapshots, or vendor risk events from a REST API. Trigger on any task
  that provides a ProcureOps base URL or references a "shared ProcureOps API",
  even if the task also includes local memo payloads.
---

# ProcureOps Skill

Use this skill for every task that involves querying the ProcureOps REST API to
produce a structured JSON answer. The API exposes procurement operational
records and the tasks always require cross-referencing multiple endpoints to
build a complete picture.

## Core workflow

Follow this sequence on every task:

1. **Read the answer template** first. It defines the output structure, required
   keys, allowed values, sorting rules, and numeric precision. Match it exactly.

2. **Read all local memo payloads.** Memos name the anchors (program IDs, SKUs,
   POs, receipt IDs, invoice IDs) and may contain business controls (tax rate,
   currency, approval rules, chargeback registers). The memos set the scope, but
   the API is the source of truth for record-level data.

3. **Fetch from every API endpoint needed.** Start with the endpoints that match
   the anchors in the memo, then fan out to related endpoints using foreign-key
   relationships (supplier_id, po_id, program_id, contract_id, receipt_id,
   invoice_id, requisition_id). Common fetch order:

   | Step | Endpoint | Key field(s) |
   |------|----------|-------------|
   | 1 | `/programs` | program_id |
   | 2 | `/suppliers` | supplier_id |
   | 3 | `/items` | sku |
   | 4 | `/contracts` | contract_id, sku, supplier_id, program_id |
   | 5 | `/purchase_requisitions` | requisition_id, program_id, sku |
   | 6 | `/purchase_orders` | po_id, program_id, requisition_id, supplier_id, contract_id |
   | 7 | `/receipts` | receipt_id, po_id, supplier_id |
   | 8 | `/ap/invoices` | invoice_id, po_id, receipt_id, supplier_id |
   | 9 | `/ap/payments` | invoice_id, supplier_id |
   | 10 | `/approvals` | object_id (requisition_id), object_type |
   | 11 | `/budget_snapshots` | program_id, snapshot_id |
   | 12 | `/vendor_risk_events` | supplier_id, related_object_id (po_id) |

   Fetch all endpoints that could supply relevant records -- it is better to
   have data you do not use than to miss a record that changes the answer.
   Filter locally after fetching.

4. **Filter to task scope.** Use the anchors from the memo to filter each
   endpoint's results. Only include records that belong to the named programs,
   suppliers, SKUs, POs, receipts, or invoices. Watch for records that share
   only a partial match (e.g., same supplier but different program) and exclude
   them unless the task explicitly asks for supplier-wide context.

5. **Cross-reference records.** Build the complete picture by joining records
   across endpoints. For example:
   - A PO links to its requisition, contract, supplier, receipts, invoices,
     payments, and risk events.
   - A receipt links to its PO, supplier, invoice, and risk events.
   - A contract links to its program, supplier, SKU, and POs.

6. **Apply the business rules.** See `references/business_rules.md` for the
   fixed-blocker-code logic, decision matrices, exception codes, and numeric
   formulas. Do not invent new codes or decision rules.

7. **Compute derived values.** Calculate headroom, variance, ratios, and totals
   using the formulas in `references/business_rules.md`. Always:
   - Round USD amounts to 2 decimal places (cents).
   - Round ratios to the precision specified in the template.
   - Round percentages to the decimal places specified in the template.

8. **Sort all list fields ascending** unless the answer template explicitly
   specifies a different order. Treat list fields as sets (no duplicates).

9. **Emit only the JSON object.** No prose before, after, or around it. The
   answer must parse as valid JSON and match the structure of the answer
   template.

## Task-type variations

The ProcureOps tasks fall into five families. The answer template and memo
determine which family applies; the skill does not need to classify tasks
explicitly. But these patterns help orient the work:

**Sourcing nomination / readiness** -- Given a program and SKU anchors, determine
whether each line can proceed to committee. Check contracts, POs, receipts,
invoices, supplier risk, and approval state. Produce a nomination_lines array
with readiness_status, blocker_codes, and committee_action.

**Receiving closeout** -- Given a receipt batch, reconcile received vs. ordered
and billed vs. received quantities. Determine AP hold position, dollar exposure,
and disposition. Produce line_reconciliation, invoice_review, financials, and
decision blocks.

**AP close desk** -- Given a set of invoices, make per-invoice hold/release
decisions, reconcile vendor balances, and build payment hold/release queues.
Check three-way match (PO, receipt, invoice), scheduled payments, and quantity
variance. Produce invoice_decisions, vendor_balances, and program_summary.

**Change-control decision** -- Given a contract, program, and requested
incremental quantity, check contract ceiling headroom, program budget headroom,
approval state, and supplier risk. Determine whether the amendment can be
released and what actions are required.

**AP release file** -- Given target POs, receipts, invoices, and a local
chargeback register, determine per-invoice release decisions (release net after
approved chargeback, hold for pending quality, hold for missing receipt).
Produce release_decisions and receiving_exceptions.

## Important conventions

**API base URL.** The task always provides the ProcureOps base URL, typically as
`<TASK_ENV_BASE_URL>` or similar. Replace the placeholder with the actual URL
from the environment. All endpoints are relative to this base and do not require
authentication.

**USD rounding.** Every dollar amount uses `round(value, 2)` -- two decimal
places. Do not use banker's rounding.

**List ordering.** Sort all ID lists, code lists, and string lists in ascending
lexical/numeric order unless the template says otherwise. Even when the template
describes a field as a "set", still sort the output ascending.

**Date filtering.** When the task specifies an `as_of_date` or `review_as_of`,
exclude records with dates after that point. Receipts dated after the as_of
date, risk events opened after the as_of date, and payments scheduled after the
look-ahead window (when specified) must be excluded.

**Missing receipts.** When a PO has no receipts and the template requires
receipt-related fields, use empty lists for receipt IDs and treat
quantity_received as 0. For receipt exception entries that have no receipt,
generate a placeholder with receipt_id like `MISSING:<po_id>`.

**Cancelled POs.** When computing contract ceiling usage, exclude POs with
status "cancelled". Include only non-cancelled POs in subtotals.

**Risk events.** For supplier risk context, consider both "open" and
"monitoring" status events as active. "Closed" events are historical context
only.

## Reference files

- [references/business_rules.md](references/business_rules.md) -- Fixed blocker
  codes, decision logic, exception codes, numeric formulas, and all business
  rules that do not change between tasks.
- [references/endpoints.md](references/endpoints.md) -- Detailed field schemas
  for every ProcureOps API endpoint, including relationships and data types.

Read the endpoint reference before fetching to understand what each endpoint
returns and how records link together. Read the business rules reference before
computing decisions to ensure you use the correct codes and formulas.
