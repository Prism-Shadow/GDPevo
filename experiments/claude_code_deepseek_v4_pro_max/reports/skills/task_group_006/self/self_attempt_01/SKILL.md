# ProcureOps Task Solver — SOP

## Environment
- **API base URL**: `http://34.46.77.124:8006` (from environment_access.md; overrides any localhost references in task text).
- **Public endpoints**: `/programs`, `/suppliers`, `/items`, `/contracts`, `/purchase_requisitions`, `/purchase_orders`, `/receipts`, `/ap/invoices`, `/ap/payments`, `/approval_events`, `/budget_snapshots`, `/vendor_risk_events`.
- Never start a local env or run setup scripts. Use the remote API directly.

## Source Precedence (critical)
1. **ProcureOps API is always the system of record.** Local memos name targets and give business rules but never override live API data.
2. **Local payloads** (memos, JSON packets) provide: target IDs, business rules, date parameters, chargeback registers, release notes.
3. **answer_template.json** in each task's `input/payloads/` defines the exact output schema. Match it precisely — every key, every type, every allowed value.

## Workflow for Any Task
1. Read `input/payloads/answer_template.json` first — know the output shape before querying.
2. Read the memo/packet payload to extract: target IDs, as-of date, business rules, control parameters.
3. Query the ProcureOps API for every record type referenced (programs, POs, receipts, invoices, contracts, suppliers, approvals, budgets, risk events). Follow relationships: invoice → PO → receipt → contract → supplier → program.
4. Cross-reference: API data is truth; memo rules determine how to interpret it.
5. Assemble JSON output exactly matching the template. Return ONLY JSON, no prose.

## Field Conventions (universal)
- **Currency**: all amounts in USD, rounded to **2 decimal places** (cents).
- **List ordering**: treat list fields as **sets** (unordered) UNLESS the template says "sorted ascending" or "sort by X ascending." When sorting is specified, sort ascending.
- **Dates**: `YYYY-MM-DD` strings. Filter records to the task's as-of date.
- **IDs**: Copy exact IDs from API responses. Never guess or fabricate.
- **Null vs missing**: Use `null` when the template type is `"string|null"` and no value exists. Use `[]` for empty lists. Use `0.00` for zero amounts.

## Reusable Business Rules

### Three-Way Match
An invoice is clear for release when PO, receipt, and invoice quantities/prices align. Otherwise, apply hold codes.

### Contract & Budget Headroom
- `contract_headroom = ceiling_amount − noncancelled_subtotal` (exclude cancelled POs from usage).
- `budget_headroom = budget_cap − committed_amount`.
- For change requests: `headroom_after = headroom_before − requested_subtotal` (or `− requested_total` for budget, which adds tax).

### Receipt Reconciliation
- `short_qty_vs_po = ordered_qty − received_qty`
- `unreceived_billed_qty = billed_qty − received_qty` (positive = billed more than received)
- `receipt_completion_ratio = received_qty / ordered_qty` (4 decimal places)
- `quantity_variance = quantity_billed − quantity_received`
- `quantity_variance_pct = (quantity_variance / po_quantity) × 100` (1 decimal place)

### Financial Rollups
- `invoice_total = subtotal + freight + tax`
- `received_goods_value = received_qty × po_unit_price`
- `unreceived_goods_value = (ordered_qty − received_qty) × po_unit_price`
- `net_balance_impact = invoice_total − scheduled_payment_amount`
- `close_balance = opening_balance + invoice_total − scheduled_payments`
- `net_release_amount = invoice_total − approved_chargeback_amount − pending_chargeback_amount`

### Chargeback Netting
- **Approved** chargebacks: subtract from invoice total to compute net release.
- **Pending** chargebacks: also subtract but the invoice remains on hold pending quality review.

### Budget Exposure (Change Requests)
- `budget_exposure = line_subtotal + estimated_tax` (add freight only if the memo provides a freight amount).
- `contract_ceiling_exposure = line_subtotal` (before tax and freight).

### Price Matching
- Compare `po_unit_price` vs `contract_unit_price` vs `invoice_unit_price`. Mismatch → `PRICE_MISMATCH` exception.

### Supplier Risk
- Query `/suppliers` for `risk_rating` and `/vendor_risk_events` for open/monitoring events on the supplier.
- An **open severe** risk event → supplier risk hold. A `supplier_watch` rating without open severe events is context-only.
- Filter risk events: open or monitoring as of the task's as-of date.

### Approval State
- Query `/approval_events` for the latest event on the source requisition. Only `"approved"` action counts as approval OK.
- Missing or non-approved latest event → hold for approval.

### Payment Scheduling
- Payments already scheduled through the task's payment-cutoff date reduce the close balance.
- Opening balance for a close slice = `0.00` unless the memo says otherwise.

## Exception & Blocker Codes (canonical sets)

**Nomination blockers** (train_001): `missing_contract`, `supplier_watch`, `open_supplier_risk`, `ap_hold`, `pending_receipt`, `late_due_date`, `none`

**Invoice exceptions** (train_002): `INVOICE_QTY_EXCEEDS_RECEIPT`, `PARTIAL_RECEIPT`, `SUPPLIER_WATCH_RISK`, `PRICE_MISMATCH`, `DAMAGE_REJECTION`, `NO_EXCEPTION`

**AP reason codes** (train_003): `APPROVED_THREE_WAY_MATCH`, `NO_RECEIPT`, `QTY_VARIANCE`, `SCHEDULED_PAYMENT_FOUND`

**Receiving exceptions** (train_005): `Underage Quantity`, `Severe Unmatched Quantity`, `Inspection Hold`, `AP Quantity Variance`

**Release decisions** (train_005): `release_net_after_approved_chargeback`, `hold_missing_receipt`, `hold_pending_quality_chargeback`

**Change decisions** (train_004): `release_amendment`, `hold_for_budget`, `hold_for_approval`, `hold_for_supplier_risk`, `hold_for_budget_and_approval`, `reject_contract_mismatch`

**Required actions** (train_004): `obtain_final_requisition_approval`, `raise_budget_exception_or_reduce_quantity`, `resolve_supplier_risk_hold`, `none`

**Batch dispositions** (train_002): `accept_partial_hold_variance`, `release_full_invoice`, `reject_batch`, `manual_recount_required`

## Output Schema Pitfalls
- **Don't add extra keys.** The template is exhaustive. Extra fields will fail validation.
- **Don't omit `null` fields.** If the template says `"string|null"`, include the key with `null`, not omit it.
- **Enum values are exact strings.** Copy from the template, including underscores and casing.
- **Set vs sorted.** If template says "set; evaluator sorts values," you don't need to sort — but sorting ascending is safe and recommended.
- **`task_id` field** must match the template's expected value exactly (e.g., `"train_003"`, not `"task_group_006_train_003"`).
- **`evidence` objects**: always include `endpoint_record_ids` (every API record ID you used) and `task_payloads_reviewed` (every local payload file you read).

## Exclusion Rules
- Never include prose, explanations, or markdown outside the JSON object.
- Never include records outside the task's scope (wrong program, wrong supplier, post-as-of-date).
- Exclude cancelled POs from contract usage calculations unless the rule says otherwise.
- Exclude receipts not tied to the target PO when scoping receipt evidence.
- Exclude risk events that are closed/resolved before the as-of date.
- When a local note says an ID "is not present in the shared API data," use the substitute IDs provided — don't fabricate the missing ones.
