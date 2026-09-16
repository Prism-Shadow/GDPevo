---
name: procureops
description: Complete ProcureOps procurement API tasks including sourcing nomination readiness, receiving closeout, AP payment-hold reconciliation, change-control decisions, and AP release files. Use when the task references a ProcureOps API base URL, mentions procurement records (suppliers, contracts, POs, receipts, invoices, payments, approvals, budget snapshots, vendor risk events), asks for a JSON answer following an answer template, or involves any ProcureOps workflow such as nomination readiness, 3-way match reconciliation, AP hold/release queues, contract/budget headroom analysis, or chargeback processing against receiving exceptions.
---

# ProcureOps

## Overview

This skill covers the ProcureOps procurement API and the five standard workflow patterns that appear in procurement operational tasks. The API exposes 13 read-only endpoints across the procure-to-pay lifecycle. Every task provides a local payload (memo, packet, or register) naming the target records and an answer template describing the expected JSON output.

## Core Workflow

Follow this sequence for any ProcureOps task:

1. **Read the local payload(s)** -- memos, packets, and chargeback registers name the target records and provide business controls (tax rates, budget exposure rules, approval criteria, chargebacks).
2. **Read the answer template** -- this defines required keys, field types, allowed enum values, rounding rules, sort order, and set/list semantics. The template is the contract for output shape.
3. **Fetch all API endpoints** -- pull every endpoint listed in [references/api_endpoints.md](references/api_endpoints.md) using `<TASK_ENV_BASE_URL>`. See [references/api_endpoints.md](references/api_endpoints.md) for the endpoint catalog, ID prefix conventions, and cross-entity join keys.
4. **Join and reconcile** -- use the join keys from the endpoint reference to cross-match records by `program_id`, `po_id`, `supplier_id`, `contract_id`, `requisition_id`, `invoice_id`, `sku`, or `po_line_id` as appropriate. See [references/domain_concepts.md](references/domain_concepts.md) for entity relationships and computation formulas.
5. **Apply business rules** -- honor all controls named in the local payload: tax rates, ceiling exposure rules (exclude cancelled POs), approval-good actions, risk tiers, and chargeback statuses.
6. **Build the JSON output** -- populate every field from live API data, rounding monetary values to cents, percentages to 1 decimal place, and ratios to 4 decimal places. Sort list fields as sets unless the template specifies ascending sort. Use only enum values allowed by the template.

## Workflow Patterns

The skill covers five standard workflow patterns. Each has its own computation and decision logic. See [references/domain_concepts.md](references/domain_concepts.md) for detailed formulas, risk tiers, and approval-chain rules.

### Sourcing Nomination Readiness

For each SKU in a program, determine whether the line can be nominated to committee. The local memo names the SKUs and their requisition/PO anchors.

**Data needed**: programs, suppliers, requisitions, contracts, POs, receipts, invoices, vendor risk events, budget snapshots.

**Per-SKU logic**:
- Identify the nominated supplier from the requisition or PO
- Check contract existence via `po.contract_id`; `null` or missing = `missing_contract` blocker
- Check PO status and due-date (past-due or near-due = `late_due_date`)
- Check receipt evidence (no receipts for the PO = `pending_receipt` blocker)
- Check invoice status (hold or exception = `ap_hold` blocker)
- Check supplier risk (open events = `open_supplier_risk`, watch rating = `supplier_watch`)
- Combine blockers into `nominate` (none), `conditional_nomination` (advisory only), or `hold` (any blocking)

**Committee action**: route to `buyer`, `finance_ops`, `quality_ops`, `program_owner`, or `ap_team` based on the dominant blocker type.

### Receiving Closeout

Reconcile a specific receipt batch against its PO, contract, and invoice. The local memo names the batch ID.

**Data needed**: receipts, POs, contracts, invoices, suppliers, vendor risk events.

**Key steps**:
- Match the receipt to its PO by `po_id`
- Match line items by `po_line_id` across PO, receipt, and invoice lines
- Perform 3-way match: ordered vs received vs billed
- Compute dollar values: received goods, unreceived goods, invoice totals
- Check invoice status and hold code
- Check supplier risk rating and open events
- Determine disposition and AP/receiving/supplier actions

### AP Payment-Hold Reconciliation

For a targeted set of invoices, compute payment decisions and vendor balances. The local memo names specific invoice IDs.

**Data needed**: invoices, POs, receipts, suppliers, programs, payments.

**Key steps**:
- For each invoice, find its PO, supplier, and program
- Match receipts to compute received vs billed quantities
- Check for scheduled payments (through the next month-end) that offset the balance
- Compute vendor-level balances: opening + invoices - scheduled = close
- Compute program-level summaries
- Separate invoices into hold and release queues
- Use only controlled reason codes: `APPROVED_THREE_WAY_MATCH`, `NO_RECEIPT`, `QTY_VARIANCE`, `SCHEDULED_PAYMENT_FOUND`

### Change Control

Evaluate a modular change request against an existing contract and program budget. The local memo provides the requested quantity, tax rate, and business control rules.

**Data needed**: contracts, POs, programs, budget snapshots, requisitions, approvals, suppliers, vendor risk events.

**Key steps**:
- Verify contract status, price type, and unit price
- Compute contract headroom: ceiling minus non-cancelled PO subtotals
- Compute budget headroom: cap minus committed
- Check approval chain: latest approval event for the source requisition
- Assess supplier risk (watch + no severe events = ok; severe = block)
- Combine into a composite decision and list required actions

### AP Release File

Process mixed AP holds against receiving exceptions and chargebacks. The local packet provides target PO/receipt/invoice IDs and an optional chargeback register.

**Data needed**: POs, receipts, invoices, suppliers, vendor risk events, plus the local chargeback register.

**Key steps**:
- Cross-match each invoice to its PO and receipt(s)
- Identify exception codes from receipt inspection data
- Map chargeback records (from the local register or derived from API data) to invoices
- Compute net release: `invoice_total - approved_chargeback_amount`
- Pending chargebacks block release; approved chargebacks reduce the release amount
- List receiving exceptions with their chargeback and resolution status
- Include followup actions for unresolved items

## General Rules

### Numeric Precision
- USD amounts: round to 2 decimal places (cents)
- Percentages: round to 1 decimal place
- Ratios (e.g. completion): round to 4 decimal places
- Quantities: integers unless the template says otherwise

### List Ordering
- Treat list fields as sets (evaluator sorts values) unless the template explicitly says "sorted ascending"
- When the template says "sorted ascending", sort the list

### Null Handling
- Use `null` (not `"null"`) for missing commercial-basis/contract IDs
- Use `0.0` for numeric fields when there is no data (e.g. received quantity when no receipt exists)
- Use empty lists `[]` when no records match (receipts, risk events, exception codes)

### ID Lists
- Include only IDs from live API data, not from local payloads unless the payload is the authoritative source (e.g. chargeback register)
- When listing evidence endpoint record IDs, include all IDs used from API responses but not local memo-only IDs

### Cancelled POs
- Exclude cancelled POs from contract usage and budget calculations
- Report excluded cancelled PO IDs separately when the template requires it

### Risk Assessment
- Always check both the supplier's `risk_rating` and its open `vendor_risk_events`
- A `watch` rating alone is advisory; block only when a `severe` rating or severe open event exists
- Report all open event IDs and separately report severe open event IDs

### Resources

- [references/api_endpoints.md](references/api_endpoints.md) -- full endpoint catalog, ID prefixes, join keys, line-level data structure, and status values
- [references/domain_concepts.md](references/domain_concepts.md) -- entity relationships, workflow patterns with detailed formulas, supplier risk tiers, approval chain rules, and chargeback processing logic

### Scripts

- [scripts/fetch_all.py](scripts/fetch_all.py) -- fetches all 13 ProcureOps endpoints in one pass. Use `python3 scripts/fetch_all.py <BASE_URL> --outdir /tmp/data` to save to disk, or omit `--outdir` for stdout JSON.
