---
name: reflect-3-procureops
description: Use this skill for ProcureOps procurement, receiving, AP close, change-control, nomination-readiness, and release/hold JSON tasks. Trigger when a task provides ProcureOps API records plus local payloads and asks for exact JSON with purchase orders, receipts, invoices, contracts, suppliers, approvals, budgets, payments, vendor risk, chargebacks, or controlled decision queues.
---

# Reflect-3 ProcureOps Workflow

Use this skill to solve structured ProcureOps tasks that combine local packet files with live operational API records. The common failure mode is answering from the memo alone. Treat the memo as the target/control sheet and the API as the system of record for operational facts.

## First Pass

1. Read the prompt, the answer template, and every task-local payload the prompt names.
2. Extract the required output shape, allowed enum values, sort orders, target IDs, review/as-of dates, tax rates, opening balances, payment horizons, and any local control rules.
3. Inspect the API root if endpoint names are uncertain. In this task family, useful records are usually exposed as `ap_invoices`, `approval_events`, `budget_snapshots`, `contracts`, `items`, `payments`, `programs`, `purchase_orders`, `purchase_requisitions`, `receipts`, `suppliers`, and `vendor_risk_events`.
4. Query by the IDs from the local packet first, then follow links from those records: invoice to PO and receipt, PO to requisition/contract/program/supplier, supplier to risk events, program to budget snapshot, and invoice to payments.
5. Build the answer against the template, not against prose memory. Return only the JSON object.

## Source Precedence

- The answer template controls field names, nesting, required keys, enum spelling, nullability, and list ordering.
- The API is authoritative for PO, receipt, invoice, contract, supplier, program, approval, payment, item, budget, and vendor-risk record contents.
- Local payloads are authoritative for the requested slice: target IDs, review dates, business controls, tax-rate assumptions, opening balances, chargeback registers, and notes about stale aliases or generated IDs.
- If a memo gives old family aliases but names generated IDs to use in the shared environment, use the generated IDs. Do not invent missing legacy records.
- Keep target-slice tasks restricted to the named invoices/POs/receipts unless the template asks for same-PO exclusions, broader contract usage, supplier-wide risk, or rollups.

## API Habits

- Start from `GET /` and use the endpoint names it advertises. Prompt prose may use friendly names such as `/ap/invoices`; the live API may expose `ap_invoices`.
- Fetch full linked records before calculating. Do not assume a receipt exists because a note mentions one, or assume an invoice is releasable because it is approved.
- For as-of tasks, filter dated evidence by the as-of date. Receipts after the review date do not support receipt evidence as of that date. Scheduled payments are different: include them only when the task gives a payment horizon and the payment date falls within it.
- Treat list fields marked as sets as exact sets, usually sorted ascending. Use empty lists for no records and `null` only for scalar fields whose template permits null.

## Calculation Conventions

- Quantities:
  - `ordered_qty` comes from the PO line quantity.
  - `billed_qty` comes from the invoice line quantity.
  - `received_qty` comes from the in-scope receipt line quantity; use `0.00` when no receipt exists.
  - `quantity_variance` is billed minus received.
  - `quantity_variance_pct` is variance divided by PO quantity, expressed as a percent.
  - Receipt completion ratios use received divided by ordered.
- Money:
  - Use invoice `total`, `subtotal`, `freight`, and `tax` directly from the invoice record when those fields are requested.
  - Goods exposure is quantity times unit price, before tax and freight.
  - Contract ceiling exposure is line subtotal before tax and freight.
  - Program budget exposure is line subtotal plus estimated tax when the local controls say so; include freight only if the local controls provide freight.
  - Budget headroom is normally budget cap minus committed amount unless the template or local controls say to use pending invoices.
  - Net close balance is invoice total minus scheduled payments within the stated payment horizon.
  - Round USD amounts to cents. For maximum affordable quantity, floor the quantity after applying unit price and tax assumptions.
- Aggregations:
  - Vendor and program summaries usually aggregate target invoices only.
  - Opening balances should come from the local memo when supplied.
  - Scheduled payments reduce close balance but do not erase invoice totals.
  - Release and hold queues should be driven by the invoice-level decisions, then sorted as the template requires.

## Decision Rules

- AP close and release files:
  - Approved three-way matches with full receipt support can be released.
  - Existing scheduled payments within the horizon reduce balance and add the scheduled-payment reason code when the template has one.
  - Missing receipt, pending receipt, quantity variance, or invoice hold status keeps an invoice held unless a local approved chargeback explicitly nets the exception.
  - An approved chargeback can support `release_net_after_approved_chargeback`; net release is invoice total minus approved chargeback.
  - Pending quality review or inspection-hold chargebacks should remain held for quality review.
  - Receipt exception codes should come from the actual receipt status, PO/receipt/invoice quantity mismatch, and any local chargeback reason. Do not add broad exception codes unless the record condition is present.
- Contract/change control:
  - Confirm the contract matches program, SKU, and supplier; otherwise use the contract-mismatch decision if available.
  - Exclude cancelled POs from existing contract usage. Include non-cancelled POs under the contract when computing ceiling usage.
  - Approval is OK only when the latest relevant approval event is one of the locally allowed good actions.
  - Supplier watch ratings are context unless the local controls say they block, or there is a severe open risk event. Open medium events can be listed without making supplier risk fail when controls say watch is context only.
  - Required actions should mirror the actual blockers: budget, approval, supplier risk, or `none`.
- Nomination/readiness packets:
  - Use local anchor IDs to identify the current package lines, then enrich those lines from API records.
  - Common blockers are missing contract, supplier watch, open supplier risk, AP hold, pending receipt, and late due date. Use `none` only when no blocker applies.
  - A line with no blockers is ready/nominate. A line with clearable AP or risk concerns can be conditional. A line missing core commercial or receipt support should be held.
  - Overall readiness should reflect the worst line state: any held line makes the packet not ready; otherwise conditional lines make it at risk.

## Evidence And Risk Fields

- Supplier risk event lists should include open or monitoring events for the supplier as of the review date, sorted by ID. Closed events are context only unless the template asks for them.
- Severe risk lists should include only events whose severity meets the severe/critical threshold implied by the template or controls.
- Evidence/source ID lists should contain actual endpoint record IDs used for the answer. Include local-payload filenames only when the template asks for reviewed payloads or source categories.
- When the template separates authoritative and supporting sources, classify API records and local chargeback registers as authoritative for their domains; classify request notes and stale-alias notes as supporting-only.

## Output Hygiene

- Return plain JSON only, with no prose, Markdown, comments, or trailing explanation.
- Preserve exact enum spellings from the template.
- Use JSON numbers for numbers, booleans for booleans, and `null` for missing nullable scalar values.
- Sort every list whose template gives an ordering; for set-like lists, sort ascending unless the template explicitly says otherwise.
- Do not include extra top-level keys or narrative explanations.
