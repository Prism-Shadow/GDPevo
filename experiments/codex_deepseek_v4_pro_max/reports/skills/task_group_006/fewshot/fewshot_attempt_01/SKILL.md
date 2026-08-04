 # ProcureOps Procurement Operations Skill

 ## Overview

 This skill covers procurement operations tasks against the ProcureOps API. The API exposes live operational records across the source-to-pay lifecycle: programs, suppliers, items, contracts, purchase requisitions, purchase orders, receipts, AP invoices, AP payments, approvals, budget snapshots, and vendor risk events.

 Tasks arrive with a prompt describing the business question, local payloads providing task-specific context and answer templates, and a configurable base URL for the ProcureOps API. The agent must query the API for live records, cross-reference them with local payloads, compute required business values, and return a JSON answer matching the exact shape of the answer template.

 ## Environment Setup

 The ProcureOps API base URL is provided by the task runner as `TASK_ENV_BASE_URL`. In prompt text, this appears as the placeholder `<TASK_ENV_BASE_URL>`. All API calls must use that live base URL.

 No authentication is required. All endpoints are read-only GET.

 ## API Reference

 ### Endpoints

 | Endpoint | Description |
 |---|---|
 | `GET /manifest` | Lists anchor IDs, record counts, and environment metadata |
 | `GET /suppliers` | Supplier master records (name, status, region, risk_rating, payment_terms) |
 | `GET /items` | Item master records (SKU, description, category, preferred supplier, standard cost) |
 | `GET /programs` | Program records (owner, budget_cap, committed_amount, status, cost_center) |
 | `GET /contracts` | Contract records (supplier, program, SKU, ceiling_amount, unit_price, price_type, status) |
 | `GET /purchase_requisitions` | Requisition records (SKU, quantity, program, requester, need_by, status) |
 | `GET /purchase_orders` | Purchase order records with nested `lines[]` (SKU, quantity, unit_price, line_id) |
 | `GET /receipts` | Receipt records with nested `lines[]` (SKU, quantity_received, quantity_rejected, inspection_status) |
 | `GET /ap/invoices` | AP invoice records with nested `lines[]` (SKU, quantity_billed, unit_price), hold_code, freight |
 | `GET /ap/payments` | AP payment records (invoice_id, amount, scheduled_date, status) |
 | `GET /approvals` | Approval event records (object_id, object_type, action, actor, event_date) |
 | `GET /budget_snapshots` | Budget snapshot records (program_id, budget_cap, committed_amount, pending_invoice_amount) |
 | `GET /vendor_risk_events` | Vendor risk event records (supplier_id, severity, status, event_type, event_date) |

 ### Querying

 **Collection list:** `GET /<collection>` returns `{ "count": N, "results": [...] }`. Always extract the `results` array.

 **By ID:** `GET /<collection>/<id>` returns a single record by its primary key (supplier_id, po_id, receipt_id, invoice_id, contract_id, event_id, etc.).

 **Filters:** Append query parameters for exact-match filtering on top-level or nested fields.
   - Example: `GET /purchase_orders?program_id=<program_id>`
   - Example: `GET /vendor_risk_events?supplier_id=<supplier_id>`
   - Example: `GET /ap/payments?invoice_id=<invoice_id>`
   - Example: `GET /approvals?object_id=<requisition_id>&object_type=requisition`

 **Date filters:** For date-bearing collections, use `start=<YYYY-MM-DD>` and `end=<YYYY-MM-DD>`.
   - Example: `GET /ap/payments?start=2026-06-01&end=2026-06-30`

 ### Key Record Relationships (Foreign Keys)

 - Programs track `program_id` → referenced by purchase_orders, contracts, requisitions, budget_snapshots
 - Suppliers track `supplier_id` → referenced by purchase_orders, receipts, invoices, payments, contracts, vendor_risk_events
 - Purchase orders track `po_id` → referenced by receipts, invoices
 - Invoices track `invoice_id` → referenced by payments
 - Contracts track `contract_id` → referenced by purchase_orders
 - Requisitions track `requisition_id` → referenced by purchase_orders
 - Receipts track `receipt_id` → referenced by invoices

 ## General Workflow

 For every ProcureOps task, follow this sequence:

 1. **Read the prompt** — Identify the task type, target program/supplier/PO/receipt/invoice IDs, the as-of date, and the business question.

 2. **Read all local payloads** — Each task has an `input/payloads/` directory containing:
    - An **answer template** (`answer_template.json`): defines the exact JSON shape to return, including field types, precision rules, allowed values, and list ordering conventions.
    - One or more **task memos/packets** (`.md` or `.json`): provide task-specific target IDs, business rules, chargeback registers, and contextual notes.

 3. **Gather live records from the API** — For every target ID mentioned in the prompt or payloads, fetch the corresponding record by ID. For every program, supplier, or other entity involved, fetch related records using query filters. Always fetch:
    - The target program(s) and their budget snapshots
    - All target purchase orders and their lines
    - All target receipts and their lines
    - All target invoices and their lines
    - Any associated payments
    - Supplier records for every supplier involved
    - Contract records for any contract IDs referenced
    - Vendor risk events for every supplier involved (filter by `supplier_id`)
    - Approval events for relevant requisition or other objects

 4. **Cross-reference records** — Join API records using the foreign-key relationships above. Match POs to receipts, invoices, contracts, and suppliers. Verify that IDs from local payloads exist in the API. Reconcile quantities, prices, and statuses across the lifecycle.

 5. **Compute business values** — Apply the computational rules described in each task-type section below. Use USD rounded to cents (2 decimal places) unless the template specifies a different precision. Treat list fields as unordered sets unless the template specifies sorting.

 6. **Make decisions** — Derive hold/release, nominate/hold, ready/not_ready, or other decisions based on the evidence gathered, following the rules implied by the answer template's allowed values and the business context in the prompt and payloads.

 7. **Produce the answer** — Return exactly the JSON object matching the answer template. Do not include prose outside the JSON. Sort ID lists ascending unless the template says otherwise. Include only IDs that exist and are relevant at the as-of date.

 ## Task-Type Patterns

 ### Pattern A: Sourcing Nomination Readiness (Train 1 style)

 **Goal:** Evaluate whether package-line SKUs are ready for supplier nomination to committee.

 **Key computations:**
 - **Budget headroom:** `program.budget_cap - program.committed_amount` (from the budget snapshot as of the as-of date). Round to cents.
 - **Readiness per SKU:** Check contract existence (`commercial_basis_id`), receipt evidence (receipts on the PO as of the as-of date), invoice exceptions (invoices with non-null hold_code or status `on_hold`), supplier risk events (open or monitoring events as of the as-of date), and PO due date status.
 - **Blocker codes:** Map conditions to the allowed codes. If a PO has no contract → `missing_contract`. If supplier has any open risk events → `open_supplier_risk`. If supplier risk_rating is `watch` → `supplier_watch`. If any invoice on the PO is on hold → `ap_hold`. If no receipts exist for the PO → `pending_receipt`. If PO due_date has passed without full receipt → `late_due_date`.
 - **Nomination decision:** `nominate` if ready with 0 blockers; `conditional_nomination` if at_risk with blockers that don't prevent conditional release; `hold` if not_ready with blocking conditions.

 **API endpoints to query:** `/programs/<id>`, `/budget_snapshots?program_id=<id>`, `/purchase_orders?program_id=<id>`, `/contracts?program_id=<id>`, `/receipts?po_id=<id>` (for each target PO), `/ap/invoices?po_id=<id>` (for each target PO), `/suppliers/<id>` (for each supplier), `/vendor_risk_events?supplier_id=<id>` (for each supplier).

 ### Pattern B: Receiving Control Closeout (Train 2 style)

 **Goal:** Reconcile a receiving batch against the PO, invoice, and supplier risk records, then decide whether to release or hold the associated invoice.

 **Key computations:**
 - **Line reconciliation:** For each PO line, compare `ordered_qty` (from PO), `received_qty` (from receipt), `rejected_qty` (from receipt), and `billed_qty` (from invoice). Compute `short_qty_vs_po = ordered_qty - received_qty`, `unreceived_billed_qty = billed_qty - received_qty`, and `receipt_completion_ratio = received_qty / ordered_qty` (to 4 decimal places).
 - **Price comparison:** Compare `po_unit_price`, `contract_unit_price`, and `invoice_unit_price`. `contract_price_match` is true when they all match.
 - **Financials:** `received_goods_value = received_qty * po_unit_price`; `unreceived_goods_value = short_qty_vs_po * po_unit_price`; `invoice_subtotal` from invoice record; `invoice_freight` and `invoice_tax` from invoice; `invoice_total` from invoice.
 - **Invoice review:** Read `invoice_status`, `hold_code`, `receipt_status`, `po_status` from API records. Derive exception codes from the template's allowed values (e.g., `INVOICE_QTY_EXCEEDS_RECEIPT` when billed > received, `PARTIAL_RECEIPT` when PO not fully received, `SUPPLIER_WATCH_RISK` when supplier has open risk).
 - **Decision:** Derive `batch_disposition`, `ap_action`, `receiving_action`, `supplier_action` from template allowed values based on the reconciliation results.

 **API endpoints to query:** `/receipts/<batch_id>`, `/purchase_orders/<po_id>` (from receipt), `/contracts/<contract_id>` (from PO), `/ap/invoices?receipt_id=<batch_id>`, `/suppliers/<id>`, `/vendor_risk_events?supplier_id=<id>`.

 ### Pattern C: AP Close Invoice Review (Train 3 style)

 **Goal:** Make payment-hold decisions and reconcile supplier balances for a set of target invoices.

 **Key computations:**
 - **Quantity reconciliation:** Compare `quantity_billed` (from invoice lines) and `quantity_received` (from receipt lines). `quantity_variance = billed - received`; `quantity_variance_pct = variance / received` (as a ratio rounded to 4 decimal places).
 - **Hold decision:** If invoice `status` is `approved` and `hold_code` is null → `RELEASE`. If `status` is `on_hold` → `HOLD`. Set `release_to_payment` accordingly.
 - **Supplier balance:** Start from 0.00 opening balance per the memo. For each invoice, add its total (positive = debit). For each payment already scheduled through the close horizon, subtract its amount (credit). `net_balance_impact = invoice_total - scheduled_payment_amount`.
 - **Reason codes:** Use the template's allowed reason codes. `APPROVED_THREE_WAY_MATCH` for clean matches; `QTY_VARIANCE_HOLD` for quantity mismatches; `SCHEDULED_PAYMENT_FOUND` when a payment is found; `NO_RECEIPT_ON_PO` when no receipt exists.
 - **Program totals:** Sum invoice totals and payment amounts per program. Compute close balance per program as `total_invoiced - total_scheduled`.

 **API endpoints to query:** `/ap/invoices/<id>` (for each target invoice), `/purchase_orders/<po_id>` (from each invoice), `/receipts/<receipt_id>` (from each invoice), `/suppliers/<id>`, `/ap/payments?invoice_id=<id>` (for each invoice), `/programs/<id>`, `/budget_snapshots?program_id=<id>`, `/vendor_risk_events?supplier_id=<id>`.

 ### Pattern D: Change-Control Decision (Train 4 style)

 **Goal:** Determine whether a requested modular change (incremental quantity under an existing contract) can be released as an amendment.

 **Key computations:**
 - **Contract ceiling check:** Compute `existing_usage` as the sum of subtotals from all non-cancelled POs under the contract. Compute `ceiling_remaining = contract.ceiling_amount - existing_usage`. Compute `amendment_subtotal = requested_qty * contract.unit_price`. The change fits if `amendment_subtotal <= ceiling_remaining`.
 - **Budget check:** Get the program budget snapshot. `budget_headroom = budget_cap - committed_amount`. Compute `total_exposure = amendment_subtotal + (amendment_subtotal * tax_rate)`. The change fits if `total_exposure <= budget_headroom`. Also compute `max_quantity_with_current_budget = floor(budget_headroom / (unit_price * (1 + tax_rate)))`.
 - **Approval check:** Query approvals for the source requisition ID. `approval_ok` is true only if the latest event has `action` in the allowed `approval_good_actions` list.
 - **Supplier risk check:** Query vendor risk events for the supplier. `supplier_risk_ok` is true if there are no open severe events. Always report open event IDs.

 **API endpoints to query:** `/contracts/<id>`, `/purchase_orders?contract_id=<id>` (exclude cancelled), `/programs/<id>`, `/budget_snapshots?program_id=<id>`, `/suppliers/<id>`, `/vendor_risk_events?supplier_id=<id>`, `/approvals?object_id=<requisition_id>&object_type=requisition`, `/items/<sku>`.

 ### Pattern E: AP Release File (Train 5 style)

 **Goal:** Prepare release/hold decisions for a set of invoices against receiving exceptions, applying chargeback registers and API records.

 **Key computations:**
 - **Release decision per invoice:** For each target invoice, determine whether to release (net of approved chargebacks), hold pending quality review, or hold for missing receipt. The decision depends on:
   - Whether receipts exist for the PO (if none → hold_missing_receipt)
   - Whether chargebacks exist in the local chargeback register
   - The chargeback status (`approved` → release_net; `pending_quality_review` → hold_pending)
 - **Net release amount:** `invoice_total - approved_chargeback_amount - pending_chargeback_amount`
 - **Receipt exceptions:** For each receipt, determine exception codes based on quantity discrepancies and inspection status. Derive chargeback status from the local chargeback register. Derive resolution status from chargeback + exception state.
 - **Receipt-in-scope:** Receipts explicitly tied to an invoice. Exclude same-PO receipts not tied to the invoice.
 - **Summaries:** Totals across all release/hold decisions.

 **API endpoints to query:** `/purchase_orders/<id>` (for each target PO), `/receipts?po_id=<id>` (for each target PO — gather all receipts, then distinguish in-scope vs excluded), `/ap/invoices/<id>` (for each target invoice), `/suppliers/<id>`.

 ## Computational Rules (All Patterns)

 ### Rounding
 - All USD amounts: round to 2 decimal places (cents) unless the template specifies otherwise.
 - Ratios (e.g., `receipt_completion_ratio`, `quantity_variance_pct`): round to 4 decimal places when the template specifies `"precision": 4`.

 ### List Handling
 - Treat ID lists as unordered sets unless the template specifies `"sorted ascending"` or `"Sort ID lists ascending"`.
 - When sorting is specified, sort string IDs lexicographically ascending.

 ### Date Handling
 - Use the as-of date from the prompt or payloads. Records with dates after the as-of date should be considered not yet effective.
 - When the template says "as of as_of_date", include only records dated on or before that date.

 ### Null and Missing Values
 - When a contract is missing for a PO → `commercial_basis_id` is `null`.
 - When no receipts/invoices/risk events exist → return empty arrays `[]`.
 - When `hold_code` is `null` in the API, the invoice is not on hold.

 ### Cancelled/Excluded Records
 - POs with `status: "cancelled"` are excluded from contract usage, budget commitment, and other cumulative calculations unless explicitly included.
 - Vendor risk events with `status: "closed"` are excluded from "open" risk lists, but may be included in "monitoring" lists if the template allows.

 ### Source Attribution
 - Always prefer API records over local payloads for factual data. Local payloads provide targets and business rules, not operational data.
 - When the template includes `authoritative_sources` or `supporting_only_sources`, classify data sources correctly: API endpoints are authoritative; local memos/notes are supporting.

 ## Answer Template Discipline

 The answer template in `input/payloads/answer_template.json` is the contract for the output. Key rules:

 - Match every key, nesting level, and type exactly.
 - Respect `required_value` — if specified, that exact string must appear.
 - Respect `allowed_values` — decisions must come from those lists.
 - Respect `precision` fields — round accordingly.
 - Respect `ordering` annotations — sort lists when required.
 - Do not add extra keys beyond what the template specifies.
 - Do not wrap the result in an extra object layer.
 - Return valid JSON with no trailing commas.

 ## Common Pitfalls

 - **Not fetching enough related records:** When a PO references a contract, always fetch the contract to get the unit price and ceiling. When an invoice references a receipt, always fetch the receipt to reconcile quantities.
 - **Forgetting to exclude cancelled POs:** Many computations (contract usage, budget impact) require excluding POs with `status: "cancelled"`. Read the business controls in the memo carefully.
 - **Including future records:** Respect the as-of date. Payments scheduled after the review horizon, vendor risk events with future dates, etc., should be excluded where the template or memo says "as of" a date.
 - **Mixing up in-scope vs excluded receipts:** When an invoice is tied to one receipt but the PO has multiple receipts, the invoice-scope receipt goes in `receipt_ids_in_scope` and the others go in `excluded_same_po_receipt_ids`.
 - **Using local payload values as operational data:** The API is the system of record. Local payloads provide targets, rules, and chargeback registers — not live PO/receipt/invoice data.
 - **Computing tax incorrectly:** Use the tax amount from the API invoice record. Do not recalculate tax unless the memo explicitly provides a tax rate and instructs you to do so (as in Pattern D where the memo provides `tax_rate_percent`).
 - **Sorting errors:** When the template says "sorted ascending" for string lists, sort lexicographically (case-sensitive). For numeric lists, sort numerically.
