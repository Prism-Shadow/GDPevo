# ProcureOps API Task Solver
 
 ## Overview
 
 This skill provides a systematic approach for solving structured business-process tasks backed by a multi-collection REST API (ProcureOps pattern). The API exposes operational records such as programs, suppliers, items, contracts, purchase orders, receipts, invoices, payments, approvals, budget snapshots, and vendor risk events.
 
 ## General Workflow
 
 1. Read all input files: the task prompt, answer template, and any local memos/packets in `input/payloads/`.
 2. Start with `GET /manifest` to see available collections, record counts, and anchor IDs.
 3. Query collections using query-parameter filters on top-level and nested record fields. Date collections support `start=<YYYY-MM-DD>` and `end=<YYYY-MM-DD>`. Records can be fetched by ID with `/<collection>/<id>`.
 4. Cross-reference records across collections by following foreign keys (e.g., PO to contract, receipt to PO, invoice to receipt/PO, risk event to supplier, approval to requisition).
 5. Apply `as_of_date` filtering: exclude records whose date fields are strictly after the target date. Use `<=` semantics.
 6. Fill the answer template with data derived from API records and supporting computations.
 
 ## Data Cross-Referencing Patterns
 
 - **PO to Contract**: `purchase_orders` have `contract_id` (nullable). Join on `contracts` to get `unit_price`, `ceiling_amount`, `price_type`, `status`.
 - **PO to Program**: `purchase_orders` have `program_id`. Join on `programs` for budget info.
 - **Receipt to PO**: `receipts` have `po_id`. Join to get order quantities, prices, and line details.
 - **Invoice to PO/Receipt**: `ap/invoices` have `po_id` and `receipt_id` (nullable). Join to verify three-way match.
 - **Risk Event to Supplier**: `vendor_risk_events` have `supplier_id`. Filter by status (`open`/`closed`) and severity.
 - **Approval to Requisition**: `approvals` have `object_id` and `object_type`. Filter by object type (`requisition`, etc.).
 - **Payment to Invoice**: `ap/payments` have `invoice_id`. Check `scheduled_date` and `status`.
 
 ## Financial Calculation Rules
 
 - All amounts in USD, rounded to cents (2 decimal places).
 - Tax rate is typically provided in the task memo. Multiply subtotal by (tax_rate / 100) and round to cents.
 - Budget headroom = `budget_cap` minus `committed_amount`.
 - For contract ceiling: sum non-cancelled PO subtotals under the contract, then ceiling minus sum = headroom.
 - For three-way match: compare PO quantity/price, receipt quantity, and invoice quantity/price.
 - Quantity variance = billed_qty minus received_qty.
 - Receipt completion ratio = received_qty / ordered_qty (4 decimal places).
 
 ## Date Handling
 
 - Always check `as_of_date` or `close_date` from the task context.
 - Receipts: filter by `receipt_date <= as_of_date`.
 - Invoices: filter by `invoice_date <= as_of_date`.
 - Risk events: include if `event_date <= as_of_date` AND `status == "open"`.
 - Payments: include if `scheduled_date` falls within the stated window.
 
 ## Common Pitfalls
 
 - **Exclude cancelled POs** when computing contract usage, unless the task says otherwise.
 - **Closed POs are NOT cancelled** - include closed POs in usage calculations.
 - **Null contract_id** on a PO means no contract exists for that line; this is a `missing_contract` condition.
 - **Invoice statuses matter**: `on_hold`, `pending_receipt`, `approved`, `paid`. Only `on_hold` and `pending_receipt` indicate blocking conditions.
 - **Supplier risk rating `watch`** means the supplier is on a watchlist. Include supplier risk context but it may not be a hard blocker unless there are open severe events.
 - **Sorting**: IDs should be sorted ascending (lexicographic). Code lists should be sorted alphabetically/lexicographically unless the template specifies otherwise.
 - **Null vs empty**: use `null` for absent values (e.g., `commercial_basis_id`, `hold_code`), empty arrays `[]` for no items.
 - **Precision**: adhere to the precision specified in the template (e.g., 4 decimal places for ratios, 2 for currency).
 
 ## Decision Patterns
 
 When making hold/release/readiness decisions, check these conditions in order:
 
 1. **Contract existence**: Does a non-draft, non-expired contract exist for the SKU-supplier pair?
 2. **Receipt status**: Has the ordered quantity been received? Are receipts in `inspection_hold`?
 3. **Invoice status**: Is the invoice `on_hold`? What is the `hold_code`?
 4. **Three-way match**: Do PO, receipt, and invoice quantities and prices align?
 5. **Supplier risk**: Is the supplier on `quality_hold`? Are there open severe risk events?
 6. **Budget**: Does the requested change fit within the program budget?
 7. **Approvals**: Has the source requisition been approved?
 
 ## API Query Tips
 
 - Filter collections by any top-level field: `?program_id=PRG-AX17`, `?supplier_id=SUP-LUMA`, `?contract_id=CR-LMP-228`.
 - Fetch single records: `/<collection>/<id>`.
 - The API returns JSON with `count` and `results` fields.
 - Always explore related collections when you find a record - follow all foreign keys to build a complete picture.
