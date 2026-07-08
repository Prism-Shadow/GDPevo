# ProcureOps GraphQL Analysis & Output Skill

## Overview

Tasks in this group require querying a ProcureOps GraphQL API (`https://graphql-procureops.internal/v1`) and producing structured JSON outputs that follow a provided answer template. The domain spans procurement programs, supplier nominations, purchase orders, receipts, invoices, accounts payable, contract changes, and supplier risk.

## GraphQL Endpoint & Querying

- **Endpoint**: `https://graphql-procureops.internal/v1`
- **Auth**: Header `x-internal-auth: test-token`
- **Tool**: Use `curl` with `-s -S` and `-H` flags for the auth header and `Content-Type: application/json`
- **Method**: Always POST with a JSON body containing `{"query": "..."}`
- **Query style**: The schema exposes singular lookup fields by ID (e.g., `program(id: "PRG-AX17")`, `po(id: "PO-AX17-4481")`, `receipt(id: "RCV-BLUE-14")`, `invoice(id: "AP-LUMA-7714")`, `contract(id: "CR-LMP-228")`) and collection fields (`allPrograms`, `allSuppliers`, `allPurchaseOrders`, `allRequisitions`, `allInvoices`, `allReceipts`, `allContracts`, `allRiskEvents`, `allBudgetSnapshots`, `allApprovalEvents`).
- **Field selection**: Request only the fields needed; large nested queries can time out. For collection queries, use filters (`filter: { programId: "PRG-AX17" }`) to narrow results.
- **Aliases**: Use GraphQL aliases when you need to fetch the same type with different IDs in one query.
- **Related lookups**: Traverse relationships using their foreign-key IDs (e.g., a `po` node has `supplierId`, `programId`; fetch the supplier separately if needed).

## Core Entities & Key Fields

Learn the essential fields for each entity. Missing fields in answers usually come from incomplete queries.

### Program
- `id`, `name`, `owner` (string, e.g. "Elena Marsh")
- `budgetCap`, `committedAmount`, `remainingBudget`
- `targetCommitmentDate`
- `skus`: list of SKU codes tied to the program
- `purchaseOrderIds`, `requisitionIds`

### Supplier
- `id`, `name`, `status` (e.g. "active"), `riskRating` (e.g. "low", "medium", "watch", "critical")
- `openRiskEventIds`

### Purchase Order (PO)
- `id`, `programId`, `supplierId`, `status` (e.g. "open", "closed", "cancelled")
- `lines`: array with `lineId`, `sku`, `quantity`, `unitPrice`, `lineTotal`
- `receiptIds`, `invoiceIds`
- `targetDeliveryDate`, `contractId`

### Receipt
- `id`, `poId`, `programId`, `supplierId`, `warehouseId`
- `receiptDate`, `receiver`, `packingSlip`
- `lines`: array with `sku`, `quantityReceived`, `quantityRejected`
- `inspectionStatus`, `exceptionCodes`

### Invoice (AP)
- `id`, `poId`, `programId`, `supplierId`, `supplierName`
- `status` (e.g. "approved", "on_hold", "pending_receipt")
- `holdCode` (e.g. "QTY_VARIANCE", "NO_RECEIPT", "PRICE_MISMATCH")
- `quantityBilled`, `quantityReceived`, `quantityVariance`, `quantityVariancePct`
- `invoiceSubtotal`, `invoiceFreight`, `invoiceTax`, `invoiceTotal`
- `scheduledPaymentAmount`, `paymentStatus`
- `exceptionCodes`

### Contract
- `id`, `sku`, `supplierId`, `programId`
- `status` (e.g. "active", "draft", "expired")
- `priceType` (e.g. "fixed", "variable")
- `unitPrice`, `ceilingAmount`
- `poIds` (linked purchase orders)

### Risk Event
- `id`, `supplierId`, `severity` (e.g. "low", "medium", "high", "severe")
- `status` (e.g. "open", "closed")

### Budget Snapshot
- `id`, `programId`, `budgetCap`, `committedAmount`, `remainingBudget`, `currency`

### Approval Event
- `id`, `requisitionId`, `action` (e.g. "submitted", "approved", "rejected")
- `actor`, `eventDate`

### Chargeback
- `id`, `receiptId`, `poId`, `status` (e.g. "approved", "pending", "rejected")
- `chargebackAmount`, `reasonCode`

## Task-Specific Patterns

Each task provides a prompt, an `answer_template.json`, and one or more payload files (memos or JSON). The payload provides narrative or partial context; **always cross-check payload claims against GraphQL data** because payloads may be stale or incomplete.

### 1. Supplier Nomination (Template: program-level with `nomination_lines`)

**Goal**: Evaluate each SKU line under a program and decide `nominate_now`, `conditional_nomination`, or `hold`.

**Query strategy**:
1. Fetch the program by ID.
2. For each SKU, find the primary requisition, selected supplier, active contract, POs, receipts, invoices, and open risk events.
3. Compute `budget_headroom_usd` = `budgetCap` - `committedAmount`.

**Decision logic**:
- `nominate_now`: contract exists, receipt evidence present, no open invoice exceptions, no open severe supplier risk, and due date is not past `as_of_date`.
- `conditional_nomination`: some non-fatal issues exist (e.g. supplier watch rating, minor AP hold, partial receipt but some evidence).
- `hold`: any fatal blocker — missing contract (`commercial_basis_id` null), no receipt evidence, late due date, open severe risk, or invoice in severe exception state.

**Readiness mapping**:
- `ready` → no blockers
- `at_risk` → non-fatal blockers only
- `not_ready` → any fatal blocker

**Blocker codes to emit** (always use exact strings):
- `late_due_date` — `target_commitment_date` < `as_of_date`
- `missing_contract` — `commercial_basis_id` is null
- `open_supplier_risk` — supplier has open risk events
- `pending_receipt` — `receipt_evidence_ids` is empty
- `ap_hold` — invoice status is "on_hold"
- `supplier_watch` — `supplier.riskRating == "watch"` or worse

**Committee action**:
- Populate `nominate_now_supplier_ids`, `conditional_supplier_ids`, `hold_supplier_ids` based on line decisions.
- `send_to_committee`: "yes" if any line is `hold` or `conditional_nomination`, else "no".
- `next_owner`: route to `"ap_team"` when there are holds, `"procurement_committee"` when conditional, or `"buyer"` if all clear.

### 2. Receiving Inspection (Template: batch-level with `line_reconciliation`)

**Goal**: Reconcile a receipt batch against its PO and invoice, compute financials, and recommend disposition.

**Query strategy**:
1. Fetch the receipt by batch ID.
2. Fetch its PO and all linked invoices.
3. Fetch the contract for price validation.

**Reconciliation per line**:
- `ordered_qty` = PO line quantity
- `received_qty` = receipt line quantity received
- `rejected_qty` = receipt line quantity rejected
- `billed_qty` = invoice quantity billed
- `short_qty_vs_po` = `ordered_qty` - `received_qty`
- `unreceived_billed_qty` = `billed_qty` - `received_qty`
- `receipt_completion_ratio` = `received_qty / ordered_qty` (round to 1 decimal place if needed)
- `contract_price_match` = `po_unit_price == contract_unit_price == invoice_unit_price`

**Financials**:
- `received_goods_value` = `received_qty * unit_price`
- `unreceived_goods_value` = `short_qty_vs_po * unit_price`
- `invoice_subtotal`, `invoice_freight`, `invoice_tax`, `invoice_total` — taken directly from the invoice node

**Invoice review**:
- `invoice_status` and `hold_code` from the invoice node.
- `exception_codes` from the invoice’s `exceptionCodes` array.
- `receipt_status`: "accepted" if no severe exceptions, else "rejected" or "partial".
- `po_status`: "partial_receipt" if `received_qty < ordered_qty`.

**Disposition decisions**:
- If invoice qty exceeds receipt and risk is open → `batch_disposition: "accept_partial_hold_variance"`, `ap_action: "keep_invoice_on_hold"`
- If qty matches and no exceptions → `batch_disposition: "accept_full"`, `ap_action: "release_to_payment"`
- If severe inspection hold → `batch_disposition: "quarantine"`, `ap_action: "hold_pending_resolution"`

### 3. AP Close (Template: list of `invoice_decisions`, `vendor_balances`, `program_summary`)

**Goal**: Decide for each invoice whether to RELEASE or HOLD, compute vendor balances, and summarize by program.

**Query strategy**:
1. Fetch all invoices matching the close scope (by date range or explicit IDs).
2. For each invoice, fetch its PO, receipt(s), and contract.
3. Fetch all chargebacks and scheduled payments.

**Invoice decision logic**:
- **RELEASE** (`"hold_decision": "RELEASE"`) when:
  - `invoice.status == "approved"`
  - Three-way match: `quantity_billed == quantity_received` and prices match contract
  - `scheduledPaymentAmount > 0`
  - No open exceptions
- **HOLD** (`"hold_decision": "HOLD"`) when:
  - `invoice.status == "on_hold"` or `"pending_receipt"`
  - Qty variance > 0
  - No receipt
  - Open exception codes present

**Fields per invoice**:
- `quantity_variance` = `quantity_billed - quantity_received`
- `quantity_variance_pct` = `(quantity_variance / quantity_billed) * 100` (round to 1 decimal)
- `scheduled_payment_amount` = invoice’s scheduled payment if releasing, else `0.0`
- `net_balance_impact` = `invoice_total - scheduled_payment_amount`
- `release_to_payment` = `true` only for RELEASE decisions
- `reason_codes`: use exact enum strings like `"APPROVED_THREE_WAY_MATCH"`, `"QTY_VARIANCE"`, `"NO_RECEIPT"`, `"SCHEDULED_PAYMENT_FOUND"`

**Vendor balances**:
For each supplier with invoices in scope:
- `opening_balance` = usually `0.0` for a close-run starting point
- `invoice_total` = sum of all invoice totals for that supplier
- `scheduled_payments` = sum of released invoice scheduled payments
- `held_invoice_total` = sum of invoice totals for held invoices
- `releasable_invoice_total` = sum of invoice totals for released invoices
- `close_balance` = `opening_balance + invoice_total - scheduled_payments`
- `balance_status`:
  - `"FULLY_SCHEDULED"` if `close_balance == 0` and all invoices released
  - `"OPEN_HELD"` if `held_invoice_total > 0`
  - `"PARTIAL"` if mix of released and held

**Program summary**:
- Group invoices by `program_id`.
- `invoice_count`, `invoice_total`, `held_total`, `released_total`, `net_close_balance`

**Queues**:
- `payment_hold_queue`: list of invoice IDs with `hold_decision == "HOLD"`
- `payment_release_queue`: list of invoice IDs with `hold_decision == "RELEASE"`
- `total_close_balance`: sum of all `net_balance_impact` for held invoices

### 4. Contract Change Request (Template: `contract_check`, `program_budget_check`, `approval_check`, `supplier_risk_check`)

**Goal**: Evaluate whether a requested quantity increase or contract modification can proceed.

**Query strategy**:
1. Fetch the contract by ID.
2. Fetch all POs linked to the contract; filter out cancelled POs.
3. Fetch the program budget snapshot.
4. Fetch the latest approval event for the source requisition.
5. Fetch supplier risk events.

**Contract check**:
- `noncancelled_subtotal` = sum of `lineTotal` for all non-cancelled POs under the contract
- `headroom_before_change` = `ceiling_amount - noncancelled_subtotal`
- `requested_subtotal` = `requested_quantity * unit_price`
- `headroom_after_change` = `headroom_before_change - requested_subtotal`
- `ceiling_ok` = `headroom_after_change >= 0`

**Program budget check**:
- `budget_after_change` = `remaining_budget - requested_total` (where `requested_total` includes tax if specified)
- `budget_ok` = `budget_after_change >= 0`
- `max_quantity_with_current_budget` = `floor(remaining_budget / unit_price)` when budget is the binding constraint

**Approval check**:
- Find the latest approval event for the source requisition.
- `approval_ok` = `latest_action == "approved"` (not `"submitted"`)

**Supplier risk check**:
- `supplier_risk_ok` = `true` if no open severe risk events (`severity == "severe"` or `"high"`). Watch/medium ratings with non-severe events are acceptable.
- `severe_open_event_ids`: filter open risk events by severity.

**Decision**:
- `"release_change"` if all checks pass (`ceiling_ok && budget_ok && approval_ok && supplier_risk_ok`)
- `"hold_for_budget_and_approval"` if budget or approval fails
- `"reject"` if ceiling fails or severe risk exists

**Supporting IDs**:
- `included_po_ids`: non-cancelled POs under the contract
- `excluded_cancelled_po_ids`: cancelled POs under the contract
- `approval_event_ids`: all events for the source requisition

### 5. AP Release Review (Template: `release_decisions` per invoice, `receiving_exceptions` per receipt)

**Goal**: Determine which invoices can be released for payment after applying approved chargebacks and reviewing receipt exceptions.

**Query strategy**:
1. Fetch all invoices in the target program (or explicit list).
2. For each invoice, fetch its PO and all receipts for that PO.
3. Fetch the chargeback register (local or via GraphQL) for each receipt.
4. Distinguish receipts that are explicitly in scope for the invoice vs. duplicate/other receipts for the same PO.

**Receipt scoping per invoice**:
- `receipt_ids_in_scope`: receipts explicitly tied to this invoice or matching its PO within the review window.
- `excluded_same_po_receipt_ids`: other receipts for the same PO that belong to different invoices (avoid double-counting).

**Chargeback application**:
- `approved_chargeback_amount` = sum of chargeback amounts with status `"approved"` for receipts in scope.
- `pending_chargeback_amount` = sum of chargeback amounts with status `"pending"` (e.g. pending quality review).
- `net_release_amount` = `invoice_total - approved_chargeback_amount`

**Decision logic**:
- `"release_net_after_approved_chargeback"`:
  - Receipt(s) exist and accepted (or exception is just qty variance with approved chargeback)
  - No pending quality holds
  - `net_release_amount > 0`
- `"hold_pending_quality_chargeback"`:
  - Receipt has exception codes like `"Inspection Hold"`, `"Severe Unmatched Quantity"`, `"Underage Quantity"`
  - Chargeback status is `"pending_quality_review"`
- `"hold_missing_receipt"`:
  - No receipt found for the PO (`receipt_ids_in_scope` is empty)

**Receiving exceptions**:
- One entry per receipt (plus a synthetic `MISSING:PO-ID` entry when no receipt exists).
- `exception_codes`: from receipt node or chargeback register.
- `chargeback_status`: `"approved"`, `"pending_quality_review"`, `"not_applicable"`.
- `resolution_status`: `"net_release_ready"`, `"hold_for_quality_review"`, `"missing_receipt"`.

**Summary**:
- `release_invoice_ids` and `hold_invoice_ids`
- `approved_chargeback_total`, `pending_chargeback_total`, `net_release_total`
- `authoritative_sources`: always include `"local_chargeback_register"`, `"procureops_ap_records"`, `"procureops_po_records"`, `"procureops_receipt_records"`
- `supporting_only_sources`: any memo or note files that are not primary system data
- `followup_actions`: actionable next steps (e.g. `"ask_receiving_for_vantix_receipt"`)

## Common Calculation Formulas

Use exact floating-point arithmetic; do not round intermediate values unless the output field explicitly calls for rounding.

| Output Field | Formula |
|---|---|
| `budget_headroom_usd` | `budget_cap - committed_amount` |
| `short_qty_vs_po` | `ordered_qty - received_qty` |
| `unreceived_billed_qty` | `billed_qty - received_qty` |
| `receipt_completion_ratio` | `received_qty / ordered_qty` |
| `received_goods_value` | `received_qty * unit_price` |
| `unreceived_goods_value` | `short_qty_vs_po * unit_price` |
| `quantity_variance` | `quantity_billed - quantity_received` |
| `quantity_variance_pct` | `(quantity_variance / quantity_billed) * 100.0` |
| `headroom_before_change` | `ceiling_amount - noncancelled_subtotal` |
| `headroom_after_change` | `headroom_before_change - requested_subtotal` |
| `budget_after_change` | `remaining_budget - requested_total` |
| `max_quantity_with_current_budget` | `floor(remaining_budget / unit_price)` |
| `close_balance` | `opening_balance + invoice_total - scheduled_payments` |
| `net_release_amount` | `invoice_total - approved_chargeback_amount` |

## Output Conventions

1. **Follow the template exactly**: Include all top-level keys in the order shown in `answer_template.json`. Do not add extra keys unless the template has them.
2. **Null handling**: Use `null` (JSON literal) for missing IDs or values, not empty strings. E.g. `"commercial_basis_id": null`.
3. **Empty arrays**: Use `[]` for lists with no items, never omit the key.
4. **Booleans**: Use JSON `true`/`false`, not strings.
5. **Currency**: All monetary values are USD unless the template says otherwise. Use exact values from GraphQL; only round when the formula demands it (e.g. ratios to 1 decimal place, percentages to 1 decimal place).
6. **Date strings**: Keep ISO-8601 or `YYYY-MM-DD` format as provided by the API.
7. **ID fields**: Preserve exact IDs from the system; never fabricate IDs except for synthetic missing-receipt placeholders (`MISSING:PO-ID`).
8. **Enums/codes**: Use the exact strings defined by the system. Common ones:
   - Hold codes: `QTY_VARIANCE`, `NO_RECEIPT`, `PRICE_MISMATCH`
   - Status: `approved`, `on_hold`, `pending_receipt`, `active`, `cancelled`, `open`, `closed`
   - Risk ratings: `low`, `medium`, `watch`, `critical`
   - Balance status: `FULLY_SCHEDULED`, `OPEN_HELD`, `PARTIAL`

## Source Precedence & Pitfalls

1. **GraphQL is authoritative**: Always query the live system. Payload memos may contain outdated or incomplete information.
2. **Cross-check memos**: If a memo says an invoice is "approved" but GraphQL says `"on_hold"`, trust GraphQL.
3. **Stale aliases**: Some payloads reference old IDs or aliases (e.g. `PO-73xx` series). Map them to current IDs via the system.
4. **Cancelled POs**: When summing PO totals for contract or budget checks, explicitly exclude POs with `status == "cancelled"`.
5. **Partial receipts**: A receipt with `quantityReceived < ordered_qty` is valid; do not reject the batch outright unless exceptions are severe.
6. **Supplier risk severity**: Distinguish between `riskRating` (watch/critical) and open risk event `severity` (low/medium/high/severe). A supplier can be on "watch" without a severe open event.
7. **Approval events**: The *latest* event for a requisition determines approval readiness. `action == "submitted"` is not approved.
8. **Chargeback netting**: Only subtract *approved* chargebacks from the invoice total. Pending chargebacks block release.
9. **Budget vs. contract ceiling**: These are separate constraints. An order can fit under the contract ceiling but blow the program budget, or vice versa. Check both independently.
10. **Three-way match**: Requires PO price == contract price == invoice price, AND billed qty == received qty. Any mismatch is a variance.
