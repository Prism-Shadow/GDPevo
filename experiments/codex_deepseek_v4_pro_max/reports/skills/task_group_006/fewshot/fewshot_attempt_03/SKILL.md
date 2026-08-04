 # ProcureOps Procurement Workflow Automation

 Automate procurement business-process reviews using a shared ProcureOps REST API. This skill covers sourcing nomination, receiving closeout, AP invoice review, change-order evaluation, and AP release/hold workflows. The agent acts as a procurement operations analyst: query operational records, cross-reference them with task-local memos, apply business rules, and produce strictly templated JSON answers.

 ## Environment

 The task prompt provides a `<TASK_ENV_BASE_URL>` placeholder. Resolve it from `environment_access.md` (the file at the workspace root lists the `Base URL`). The API is unauthenticated and read-only. Every analysis must treat the API as the authoritative data source; task-local memos and packets provide targeting context but can be stale or incomplete.

 ### API Endpoints

 All collections are reachable at `{base}/{collection}`. A listing of available endpoints is at `GET /manifest`.

 | Collection               | Key fields / notes                                                                 |
 | ------------------------ | ---------------------------------------------------------------------------------- |
 | `suppliers`              | `id`, `name`, `status`, `risk_rating`                                             |
 | `items`                  | `sku`, `description`, `unit_price`                                                |
 | `programs`               | `id`, `name`, `owner`, `budget_cap`                                               |
 | `contracts`              | `id`, `supplier_id`, `status`, `price_type`, `unit_price`, `ceiling_amount`       |
 | `purchase_requisitions`  | `id`, `program_id`, `sku`, `status`                                               |
 | `purchase_orders`        | `id`, `program_id`, `supplier_id`, `sku`, `status`, `due_date`, `line_items`      |
 | `receipts`               | `id`, `po_id`, `batch_id`, `status`, `line_items` (qty received/rejected)         |
 | `ap/invoices`            | `id`, `po_id`, `supplier_id`, `status`, `hold_code`, `line_items`, `total`        |
 | `ap/payments`            | `id`, `invoice_id`, `status`, `amount`                                            |
 | `approvals`              | `id`, `requisition_id`, `action`, `actor`, `event_date`                           |
 | `budget_snapshots`       | `id`, `program_id`, `budget_cap`, `committed_amount`                              |
 | `vendor_risk_events`     | `id`, `supplier_id`, `severity`, `status` (open / monitoring / closed)            |

 ### Query Patterns

- **Filter by field**: `?field=value` for exact matches on any top-level or nested field (e.g. `?program_id=PRG-AX17`, `?supplier_id=SUP-LUMA`).
- **Date range**: Date collections (`receipts`, `ap/invoices`, `ap/payments`, `approvals`, `vendor_risk_events`) support `?start=YYYY-MM-DD&end=YYYY-MM-DD`. Use `end` as the task as-of date to scope records.
- **By ID**: Append `/{id}` to any collection path to fetch a single record.
- **Fetch all first**: When a filter returns multiple records, fetch the full collection without filters to audit counts and ensure completeness.

 ## Workflow

### Step 1 — Parse the Task

 Read the task prompt, the local memo/packet payload, and the answer template. Identify:

 - **Business process** — nomination, receiving closeout, AP closeout, change-order review, or AP release.
 - **Target IDs** — program, contract, supplier, SKU, PO, receipt, invoice, batch IDs named in the memo.
 - **As-of date** — the review cutoff date; scope all date-filtered queries to this date.
 - **Template structure** — every required key, enum constraint, list ordering rule, and precision requirement.

### Step 2 — Query the ProcureOps API

 Map each target ID from the memo to the correct collection. Typical query sequence:

 1. Fetch `/manifest` to confirm available endpoints.
 2. Fetch the program record (`/programs/{program_id}`) for owner and budget cap.
 3. Fetch supplier records (`/suppliers/{supplier_id}`) for status and risk rating.
 4. Fetch contracts (`/contracts?supplier_id=...` or by ID) for price terms and ceiling.
 5. Fetch purchase orders (`/purchase_orders?program_id=...` or by PO ID) for line items, status, due dates.
 6. Fetch receipts (`/receipts?po_id=...&end={as_of_date}`) for receiving evidence.
 7. Fetch invoices (`/ap/invoices?po_id=...&end={as_of_date}`) for billing status and holds.
 8. Fetch approvals (`/approvals?requisition_id=...&end={as_of_date}`) for workflow status.
 9. Fetch budget snapshots (`/budget_snapshots?program_id=...`) for financial position.
 10. Fetch vendor risk events (`/vendor_risk_events?supplier_id=...`) for open or monitoring events as of the as-of date.

 Cross-reference every API record against the memo targets. If a memo references an ID not found in the API, treat it as missing (e.g., `null` commercial basis, empty receipt list).

### Step 3 — Apply Business Rules

 See `references/business_rules.md` for process-specific rules. General principles:

 - **Amounts**: All USD values rounded to cents (two decimal places). Use standard arithmetic rounding.
 - **Lists as sets**: Unless the template says "sorted ascending" or another explicit ordering, treat list fields as unordered sets. Evaluators may sort them; output them sorted ascending for determinism.
 - **Dates**: Use `YYYY-MM-DD` format. Compare dates chronologically (earlier dates are "before").
 - **Status evaluation**: Map API status values to template enums. When the API uses a different vocabulary, infer the closest match based on business meaning.
 - **Null vs empty**: Use `null` for absent single values, `[]` for absent lists. Do not use `"null"` or `"none"` as string values unless the template explicitly allows them.

### Step 4 — Produce the Answer

 Follow the answer template exactly:

 - Include every key defined in the template, even if its value is `null` or `[]`.
 - Do not add extra keys beyond the template.
 - Match the enum values precisely (case-sensitive).
 - Format numbers to the specified precision.
 - Sort list fields as directed.

 ## Common Business Processes

### Sourcing Nomination (train_001 pattern)

 **Goal**: Assess readiness of program lines for supplier nomination committee review.

 **Key API sources**: programs, suppliers, contracts, requisitions, POs, receipts, invoices, vendor risk events, budget snapshots.

 **Readiness per line** is determined by blocker codes:
 - `missing_contract` — No active contract found for the supplier-SKU pair.
 - `supplier_watch` — Supplier risk rating is "watch" (but no open severe event).
 - `open_supplier_risk` — At least one open vendor risk event exists for the supplier.
 - `ap_hold` — Invoice is on hold (status not "paid" or "approved").
 - `pending_receipt` — No receipt found for the PO as of the as-of date.
 - `late_due_date` — PO due date is before the as-of date.
 - `none` — No blockers; line is fully ready.

 **Nomination decision**:
 - `nominate` — Zero blockers.
 - `conditional_nomination` — Blockers are limited to `supplier_watch` and/or `ap_hold` (no structural blockers).
 - `hold` — Any structural blocker (missing_contract, open_supplier_risk, pending_receipt, late_due_date).

 **Readiness status**:
 - `ready` — nomination_decision is `nominate`.
 - `at_risk` — nomination_decision is `conditional_nomination`.
 - `not_ready` — nomination_decision is `hold`.

 **Budget headroom**: `budget_cap - committed_amount` from the program's budget snapshot.

 **Committee action**:
 - `send_to_committee`: `"yes"` if any line has `nominate` decision; otherwise `"no"`.
 - `next_owner`: Route to the team that can resolve the most severe blocker (`ap_team` for AP holds, `buyer` for missing contracts, `quality_ops` for risk events, `finance_ops` for budget issues, `program_owner` otherwise).

### Receiving Closeout (train_002 pattern)

 **Goal**: Reconcile received quantities against ordered and billed quantities for a single receipt batch.

 **Key API sources**: receipts (by batch ID), purchase orders, contracts, suppliers, invoices, vendor risk events.

 **Line reconciliation** (per PO line):
 - `ordered_qty`: From the PO line item.
 - `received_qty`: Sum of accepted quantities from receipt line items for that PO line.
 - `rejected_qty`: Sum of rejected quantities from receipt line items for that PO line.
 - `billed_qty`: Sum of invoiced quantities from AP invoice line items for that PO line.
 - `short_qty_vs_po`: `ordered_qty - received_qty` (positive means shortage).
 - `unreceived_billed_qty`: `billed_qty - received_qty` (positive means billed for unreceived goods).
 - `receipt_completion_ratio`: `received_qty / ordered_qty`, rounded to 4 decimal places.
 - `contract_price_match`: `true` if `po_unit_price == contract_unit_price`, else `false`.

 **Exception codes** (invoice review):
 - `INVOICE_QTY_EXCEEDS_RECEIPT` — billed > received on any line.
 - `PARTIAL_RECEIPT` — any line has `received_qty < ordered_qty`.
 - `SUPPLIER_WATCH_RISK` — supplier has open vendor risk events.
 - `PRICE_MISMATCH` — any line has `contract_price_match == false`.
 - `DAMAGE_REJECTION` — any line has `rejected_qty > 0`.
 - `NO_EXCEPTION` — none of the above apply.

 **Financials**: Sum PO line subtotals for received/unreceived goods value. Invoice total includes subtotal, freight, and tax from the API invoice record.

### AP Closeout (train_003 pattern)

 **Goal**: Review supplier invoices and recommend pay/hold/defer/void actions.

 **Key API sources**: invoices, POs, receipts, suppliers, vendor risk events, payments, approvals.

 **Invoice review fields**: PO status, receipt status, payment status, approval status, hold codes, supplier risk context. Derive `ap_action` from the combination of these statuses.

### Change-Order Review (train_004 pattern)

 **Goal**: Evaluate a contract amendment against contract ceiling, program budget, requisition approvals, and supplier risk.

 **Key API sources**: contracts (by ID), budget snapshots (by program), approvals (by requisition), suppliers, vendor risk events, purchase orders (by contract/supplier).

 **Contract check**:
 - `noncancelled_subtotal`: Sum of `quantity * unit_price` for all non-cancelled POs under the contract.
 - `headroom_before_change`: `ceiling_amount - noncancelled_subtotal`.
 - `requested_subtotal`: `requested_quantity * unit_price`.
 - `headroom_after_change`: `headroom_before_change - requested_subtotal`.
 - `ceiling_ok`: `headroom_after_change >= 0`.

 **Budget check**:
 - `remaining_budget`: `budget_cap - committed_amount`.
 - `requested_tax`: `requested_subtotal * (tax_rate_percent / 100)`, rounded to cents.
 - `requested_total`: `requested_subtotal + requested_tax` (add freight only if the memo provides it).
 - `budget_after_change`: `remaining_budget - requested_total`.
 - `budget_ok`: `budget_after_change >= 0`.
 - `max_quantity_with_current_budget`: `floor(remaining_budget / (unit_price * (1 + tax_rate/100)))`.

 **Approval check**:
 - Find the latest approval event for the source requisition (by `event_date`).
 - `approval_ok`: The latest action is in the memo's `approval_good_actions` list (typically `"approved"`).

 **Supplier risk check**:
 - `supplier_risk_ok`: No open vendor risk events with `severity == "severe"` for the supplier. (Watch rating alone does not block.)

 **Decision**: Combine the four boolean checks:
 - `release_amendment`: All four OK.
 - `hold_for_budget`: `budget_ok == false`, others OK.
 - `hold_for_approval`: `approval_ok == false`, others OK.
 - `hold_for_supplier_risk`: `supplier_risk_ok == false`, others OK.
 - `hold_for_budget_and_approval`: Both `budget_ok` and `approval_ok` are false.
 - `reject_contract_mismatch`: `ceiling_ok == false`.

### AP Release Review (train_005 pattern)

 **Goal**: Decide release vs. hold for invoices with receiving exceptions, applying chargeback netting.

 **Key data sources**: invoices, POs, receipts (API) + chargeback register and release request notes (local payload).

 **Release decision per invoice**:
 - Match the invoice to its PO and find all receipts for that PO (scoped to target receipt IDs if applicable).
 - Check for chargebacks in the local chargeback register matching `(invoice_id, po_id, receipt_id)`.
 - `approved_chargeback_amount`: Sum of `basis_quantity * unit_cost` for chargebacks with `status == "approved"`.
 - `pending_chargeback_amount`: Sum of `basis_quantity * unit_cost` for chargebacks with `status == "pending_quality_review"`.
 - `net_release_amount`: `invoice_total - approved_chargeback_amount - pending_chargeback_amount`. If the decision is a hold, `net_release_amount` is `0.0`.

 **Decision logic**:
 - `hold_missing_receipt`: No receipts found for the PO in the target receipt set.
 - `hold_pending_quality_chargeback`: Receipts exist but at least one chargeback is `pending_quality_review`.
 - `release_net_after_approved_chargeback`: Receipts exist, all chargebacks are `approved` (or none exist), net release amount is the invoice total minus approved chargebacks.

 **Receiving exceptions** (per receipt):
 - Derive `exception_codes` from the chargeback `reason_code` and receipt inspection data.
 - `chargeback_status`: From the chargeback register (`approved`, `pending_quality_review`, or `not_applicable` if no chargeback).
 - `resolution_status`: `net_release_ready` (approved), `hold_for_quality_review` (pending), `missing_receipt` (no receipt), `accepted_no_receiving_exception` (no exceptions).

 ## Anti-Patterns

 - **Do not trust memo data over API data.** The API is authoritative. If the memo says a PO exists but the API returns nothing, the PO is missing.
 - **Do not hallucinate IDs.** Every ID in the answer must come from the API or the local payloads. Never invent receipt, invoice, PO, or event IDs.
 - **Do not skip cross-referencing.** Always verify that a record from one endpoint (e.g., an invoice) properly links to records from other endpoints (e.g., its PO and receipts).
 - **Do not add template keys.** The answer must match the template structure exactly with no extra fields.
 - **Do not confuse as-of dates.** All date-scoped queries use the task's as-of/review date, not the current date.
