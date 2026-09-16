---
name: procureops
description: "Industrial procurement operations analysis using the ProcureOps REST API. Use
  when the task involves: (1) sourcing nomination readiness for programs or SKUs,
  (2) receiving-control closeout and AP invoice reconciliation, (3) AP close-desk
  payment-hold and vendor-balance reconciliation, (4) contract change-control impact
  analysis and amendment decisions, (5) AP release and receiving exception review with
  chargeback netting, or (6) any cross-entity procurement query spanning suppliers,
  items, programs, contracts, requisitions, purchase orders, receipts, invoices,
  payments, approvals, budget snapshots, and vendor risk events."
license: MIT
compatibility: designed for deepagents-code
---

# ProcureOps

## Quick Start

The ProcureOps API base URL is provided as `<TASK_ENV_BASE_URL>`. No credentials
are required. All endpoints return `{"count": N, "results": [...]}`.

Available endpoints:

- `/manifest`
- `/suppliers`
- `/items`
- `/programs`
- `/contracts`
- `/purchase_requisitions`
- `/purchase_orders`
- `/receipts`
- `/ap/invoices`
- `/ap/payments`
- `/approvals`
- `/budget_snapshots`
- `/vendor_risk_events`

Fetch each needed endpoint once per task. The API has no query parameters or
filters, so fetch the full result set and filter/slice in memory. See
[api_schemas.md](references/api_schemas.md) for every field and type.

## Workflow

### 1. Read the task prompt and payloads

Every task includes a `prompt.txt` and optional payload files under
`input/payloads/`. The payloads name the target entities (programs, SKUs, POs,
receipts, invoices) and may include an answer template JSON, a memo with
business controls, chargeback register excerpts, or release request notes.

Always read the payloads first to understand what records to target and which
template to fill.

### 2. Fetch the API records you need

Fetch the endpoints relevant to the task. Most tasks require suppliers, items,
programs, contracts, purchase orders, receipts, invoices, and vendor risk
events. Approval, payment, and budget snapshot endpoints are needed for
change-control and AP close tasks.

### 3. Navigate the entity graph

The API has no joins. Navigate by matching foreign keys across result sets:

- PO to Contract via `contract_id`, Supplier via `supplier_id`, Program via `program_id`
- Receipt to PO via `po_id`
- Invoice to PO via `po_id`, Receipt via `receipt_id`
- Payment to Invoice via `invoice_id`, Supplier via `supplier_id`
- Approval to Object via `object_id` and `object_type`
- Budget Snapshot to Program via `program_id`
- Risk Event to Supplier via `supplier_id`

### 4. Apply the business rules for your task type

See [business_rules.md](references/business_rules.md) for the complete
cross-entity reconciliation rules, decision matrices, blocker codes, and
calculation formulas. The reference covers:

- Sourcing nomination readiness (blocker codes, readiness tiers, nomination decisions)
- Receiving reconciliation (quantity variances, receipt completion ratios)
- Three-way match and invoice hold logic
- AP close reconciliation (vendor balances, reason codes, hold/release queues)
- Contract change control (ceiling headroom, budget impact, approval checks)
- AP release with chargeback netting (exception codes, release decisions)

### 5. Build and return the JSON output

- Follow the answer template exactly: key names, types, enum values, and list orders.
- Round all USD amounts to 2 decimal places (cents).
- Treat list fields as sets (unordered) unless the template specifies a sort order.
- Sort string IDs ascending lexicographically. Sort numeric values ascending.
- Use `null` for missing optional fields, `[]` for empty lists.
- Return only the JSON object, no prose outside it.

## Key Conventions

- **Currencies**: All amounts are USD. Round to cents.
- **Statuses**: PO statuses are `open`, `partial_receipt`, `received`, `cancelled`.
  Invoice statuses are `approved`, `on_hold`, `pending_receipt`.
- **As-of dates**: Filter records by date fields (receipt_date, invoice_date,
  event_date) against the task's as_of_date. Records dated after the as_of_date
  are excluded from calculations.
- **Cancelled POs**: Exclude `cancelled` POs from contract headroom and budget
  calculations. They consume no ceiling.
- **Receipts per PO**: A single PO may have multiple receipts. Sum quantities
  across all receipts on the same PO when reconciling against invoices.
