 # ProcureOps Skill

 You are working inside a ProcureOps shared API environment (a mock procurement-operations ERP). This skill describes the reusable operating rules, data model, and analysis patterns distilled from the ProcureOps task corpus. Every ProcureOps task follows the conventions below; apply them unless the task-specific prompt or local memo explicitly overrides a rule.

 ## Environment and API

 - The API base URL is provided by the runner as `<TASK_ENV_BASE_URL>`. Never hardcode it; always substitute it at runtime.
 - All endpoints are **read-only GET**.
 - Collections return arrays under `results` with a `count` wrapper. Fetch by ID with `/<collection>/<id>` when the record id is known.
 - **Filtering** uses exact-match query parameters on top-level or nested record fields. Date collections also accept `start=<YYYY-MM-DD>` and `end=<YYYY-MM-DD>` range filters.
 - **No authentication** is required.

 ### Available collections

 | Endpoint                   | Key fields                                                               |
 |----------------------------|--------------------------------------------------------------------------|
 | `/suppliers`               | supplier_id, name, status, risk_rating, payment_terms, region            |
 | `/items`                   | sku, description, category, standard_cost, preferred_supplier_id, uom    |
 | `/programs`                | program_id, name, owner, budget_cap, committed_amount, status, priority  |
 | `/contracts`               | contract_id, program_id, supplier_id, sku, status, unit_price, price_type, ceiling_amount, effective_date, expiry_date |
 | `/purchase_requisitions`   | requisition_id, program_id, sku, quantity, requester, status, need_by    |
 | `/purchase_orders`         | po_id, requisition_id, program_id, supplier_id, contract_id, status, lines (line_id, sku, quantity, unit_price), subtotal, tax, total, due_date |
 | `/receipts`                | receipt_id, po_id, supplier_id, status, warehouse_id, receipt_date, packing_slip, receiver, lines (po_line_id, sku, quantity_received, quantity_rejected, inspection_status) |
 | `/ap/invoices`             | invoice_id, po_id, supplier_id, receipt_id, status, hold_code, lines (po_line_id, sku, quantity_billed, unit_price), subtotal, freight, tax, total |
 | `/ap/payments`             | payment_id, invoice_id, supplier_id, amount, status, scheduled_date      |
 | `/approvals`               | event_id, object_id, object_type, action, actor, event_date, note_code   |
 | `/budget_snapshots`        | snapshot_id, program_id, budget_cap, committed_amount, pending_invoice_amount, snapshot_date |
 | `/vendor_risk_events`      | event_id, supplier_id, event_type, severity, status (open/closed/monitoring), related_object_id, event_date |

 ## Data Model Relationships

 ```
 Program ──┬── BudgetSnapshot
           ├── PurchaseRequisition ──┬── Approval (object_type="requisition")
           │                         └── PurchaseOrder ──┬── Receipt
           │                                             │      └── lines (quantity_received, quantity_rejected)
           │                                             ├── APInvoice
           │                                             │      └── lines (quantity_billed, unit_price)
           │                                             └── APPayment
           └── Contract ── PurchaseOrder (referenced by contract_id)

 Supplier ──┬── Contract
            ├── PurchaseOrder
            ├── Receipt
            ├── APInvoice
            ├── APPayment
            └── VendorRiskEvent
 ```

 ## Input Conventions

 Every task supplies these local payloads:

 - **`prompt.txt`**: the task instruction with `<TASK_ENV_BASE_URL>` placeholder, target entities, and which answer template to use.
 - **Local memo** (e.g. `*_memo.md`, `change_memo.json`, `ap_release_packet.json`): names target entities (program, SKUs, PO IDs, receipt IDs, invoice IDs) and business-control parameters. **The memo is a reference only; the API is always the system of record.**
 - **`answer_template.json`**: the exact output schema the answer must conform to. Field types, required keys, precision rules, sort orders, and allowed enum values are all specified here.
 - **Local chargeback registers** (when present): supplement API data with chargeback records that may not exist in the API. Their statuses (`approved`, `pending_quality_review`) drive downstream decisions.

 ## Output Conventions

 - **Return only JSON** matching the answer template exactly. No prose, no markdown fences—just the raw JSON object.
 - **USD amounts**: always rounded to two decimal places (`round(x, 2)`).
 - **Percentages**: rounded to the precision specified in the template (e.g. one decimal for variance pct).
 - **Ratios**: rounded to the template precision (e.g. receipt completion ratio to 4 decimals).
 - **List fields**: treated as sets (unordered) unless the template explicitly says "sorted ascending". When sorted, use natural string sort.
 - **Enum fields**: use exactly the allowed values in the template. Never invent new codes.
 - **Dates**: always `YYYY-MM-DD` format.
 - **Null handling**: use `null` (JSON null) for absent optional values, not empty strings or zeros.

 ## Core Computational Rules

 ### Contract Ceiling Analysis

 1. Collect all POs referencing the target contract_id. **Exclude cancelled POs** (status = `cancelled`).
 2. `noncancelled_subtotal` = sum of `subtotal` from all non-cancelled POs.
 3. `headroom_before_change` = `ceiling_amount` − `noncancelled_subtotal`.
 4. `requested_subtotal` = `requested_quantity` × `contract_unit_price`.
 5. `headroom_after_change` = `headroom_before_change` − `requested_subtotal`.
 6. `ceiling_ok` = `headroom_after_change >= 0`.

 ### Program Budget Analysis

 1. Fetch the latest budget snapshot for the program (by `snapshot_date`).
 2. `remaining_budget` = `budget_cap` − `committed_amount`.
 3. Compute tax-inclusive requested total: `requested_subtotal` + (`requested_subtotal` × `tax_rate_percent` / 100), adding freight only if the local memo specifies it.
 4. `budget_after_change` = `remaining_budget` − `requested_total` (tax-inclusive).
 5. `budget_ok` = `budget_after_change >= 0`.
 6. `max_quantity_with_current_budget` = floor(`remaining_budget` / (`unit_price` × (1 + `tax_rate_percent` / 100))).

 ### Three-Way Match (PO ↔ Receipt ↔ Invoice)

 1. Join PO lines, receipt lines, and invoice lines on `po_line_id` and `sku`.
 2. For each line:
    - `short_qty_vs_po` = `ordered_qty` − `received_qty`.
    - `unreceived_billed_qty` = `billed_qty` − `received_qty` (cap at `billed_qty`).
    - `receipt_completion_ratio` = `received_qty` / `ordered_qty` (to 4 decimals).
 3. **Contract price matching**: invoice `unit_price` must equal contract `unit_price` exactly. POs may reference a contract_id but their line unit_price is the committed price.
 4. **Quantity variance**: `quantity_variance` = `quantity_billed` − `quantity_received`. `quantity_variance_pct` = `quantity_variance` / PO `quantity` × 100.

 ### Financial Computations

 - **Received goods value** = sum(received_qty × po_unit_price) across lines.
 - **Unreceived goods value** = sum(short_qty_vs_po × po_unit_price) across lines.
 - **PO subtotal** = sum(po_line.quantity × po_line.unit_price) — already computed on the PO record.
 - **Invoice subtotal** = sum(line.quantity_billed × line.unit_price) — already computed on the invoice record.
 - **Invoice total** = subtotal + freight + tax.
 - **Net release amount** = invoice_total − approved_chargeback_amount.

 ### Approval Chain

 1. Filter `/approvals` by `object_id` = target requisition_id and `object_type` = `requisition`.
 2. Find the latest event by `event_date` (or `event_id` as tiebreaker).
 3. `approval_ok` = latest action is in the set of good actions specified by the memo (typically `["approved"]`).
 4. The latest event's `actor`, `action`, `event_date`, and `event_id` are the approval context.

 ### Supplier Risk Assessment

 1. Fetch supplier record for `risk_rating` (low, medium, watch, high, etc.) and `status` (active, quality_hold).
 2. Fetch open vendor risk events (`status` ≠ closed). Monitor events (`status` = monitoring) also count as open for blocker decisions.
 3. **Severe events**: severity = `high` or `critical`. These always block unless the memo says otherwise.
 4. **Watch rating**: a supplier with `risk_rating` = `watch` triggers `supplier_watch` attention but does not automatically block unless an open severe event exists.
 5. `supplier_risk_ok` = no open severe events AND supplier status is not `quality_hold`.

 ### Invoice Hold/Release Decisions

 1. Check invoice `status` and `hold_code`.
 2. Cross-reference with receipt existence and quantities.
 3. Check for scheduled payments via `/ap/payments` filtered by `invoice_id`.
 4. **Reason codes** (alphabetical): `APPROVED_THREE_WAY_MATCH`, `NO_RECEIPT`, `QTY_VARIANCE`, `SCHEDULED_PAYMENT_FOUND`.
 5. **Release decision**: `RELEASE` when invoice is approved, three-way match passes, and there are QTY_VARIANCE exceptions handled by approved chargebacks. `HOLD` otherwise.
 6. `release_to_payment` = true when hold_decision is RELEASE and any scheduled payments exist or the invoice is approved.

 ### Exception Codes (Receiving/AP)

 Use only the allowed values from the answer template. Common patterns:

 - `INVOICE_QTY_EXCEEDS_RECEIPT`: billed > received.
 - `PARTIAL_RECEIPT`: received < ordered.
 - `SUPPLIER_WATCH_RISK`: supplier has watch or worse risk rating or open risk events.
 - `PRICE_MISMATCH`: invoice unit_price ≠ contract/PO unit_price.
 - `DAMAGE_REJECTION`: quantity_rejected > 0.
 - `NO_EXCEPTION`: none of the above.

 From the receiving perspective: `Underage Quantity`, `Severe Unmatched Quantity`, `Inspection Hold`, `AP Quantity Variance`.

 ### Blocker Codes (Nomination Readiness)

 Assemble blockers from data checks:
 - `missing_contract`: PO has no contract_id or contract is not active.
 - `supplier_watch`: supplier risk_rating is `watch` or higher.
 - `open_supplier_risk`: open or monitoring vendor risk events exist for the supplier.
 - `ap_hold`: invoice is on hold (status = `on_hold` or `pending_receipt`).
 - `pending_receipt`: PO has no receipt or receipt status is not `accepted`.
 - `late_due_date`: PO due_date is before the as_of_date.
 - `none`: no blockers.

 Sort blocker codes ascending. Use `none` alone when the list would otherwise be empty.

 ## Task-Type Patterns

 ### Sourcing Nomination Readiness (train_001)

 1. Read the local memo for package anchor SKU-requisition-PO triples.
 2. Fetch the program, its budget snapshot, and all related POs, receipts, invoices, contracts, suppliers.
 3. For each SKU line:
    - Determine selected_supplier_id from the PO.
    - Check contract existence and active status.
    - Gather receipt evidence IDs as of as_of_date.
    - Gather invoice exception IDs as of as_of_date.
    - Gather open/monitoring supplier risk event IDs.
    - Compute blocker codes.
    - Set nomination_decision: `nominate` if no blockers, `conditional_nomination` if only `supplier_watch`, `hold` otherwise.
    - Set readiness_status: `ready` if `nominate`, `at_risk` if `conditional_nomination`, `not_ready` if `hold`.
 4. Aggregate committee_action: group supplier_ids by decision, set next_owner based on the most critical blocker, set send_to_committee.

 ### Receiving Closeout (train_002)

 1. Fetch the receipt by batch_id along with its PO, contract, supplier, invoices, and risk events.
 2. Reconcile each PO line: ordered vs received vs rejected vs billed.
 3. Compute financials: received/unreceived goods value, invoice totals.
 4. Determine exception codes from the reconciliation.
 5. Decide batch_disposition, ap_action, receiving_action, supplier_action based on findings.
 6. Include supplier risk context and evidence record IDs.

 ### AP Close Desk (train_003)

 1. Fetch target invoices and their linked POs, receipts, suppliers, payments, and program budget snapshots.
 2. For each invoice: determine hold/release, reason codes, quantity variances, net balance impact.
 3. Aggregate vendor balances: opening (0.00 for the close slice), invoice totals, scheduled payments, held totals, releasable totals, close_balance.
 4. Compute program summary: per-program invoice totals and held/released breakdowns.
 5. Build payment_hold_queue and payment_release_queue.
 6. Compute total_close_balance across all target invoices.

 ### Change Control (train_004)

 1. Read the change memo for requested contract, supplier, SKU, variant, quantity, source requisition, and business controls.
 2. Run contract ceiling analysis (exclude cancelled POs).
 3. Run program budget analysis with the tax rate from the memo.
 4. Run approval check on the source requisition.
 5. Run supplier risk check.
 6. Determine decision based on which checks fail.
 7. Build required_actions and supporting_ids.

 ### AP Release / Exception Review (train_005)

 1. Read the release packet for target PO, receipt, and invoice IDs.
 2. Cross-reference local chargeback register with API data.
 3. For each invoice: determine release decision based on chargeback status and receipt evidence.
 4. For each receipt: catalog exception codes and chargeback/resolution status.
 5. Compute summary: release/hold IDs, approved/pending/net totals.
 6. Distinguish authoritative sources (API records) from supporting-only sources (local notes, alias notes).
 7. Enumerate follow-up actions.

 ## General Operating Rules

 1. **API is authoritative.** Local memos name entities but the API is always the source of truth for record fields.
 2. **Filter precisely.** Use the most specific available query parameter (e.g. `program_id`, `supplier_id`, `po_id`) to minimize result sets.
 3. **Cross-reference by ID.** Join records across collections using the foreign-key fields documented above.
 4. **Handle missing data gracefully.** If a receipt, invoice, or payment doesn't exist, use 0 / null / empty arrays as appropriate for the template.
 5. **Sort consistently.** When the template says "sorted ascending", sort strings lexicographically and numbers numerically ascending.
 6. **Deduplicate.** When aggregating IDs across collections, use sets to avoid duplicates.
 7. **Date filtering.** Use the `start`/`end` query parameters on date-bearing collections when the task specifies an `as_of_date` or `close_date`.
 8. **Chargeback arithmetic.** Approved chargebacks reduce the net release amount. Pending chargebacks are tracked separately and do not reduce net release until approved.
 9. **Budget vs contract ceiling.** Contract ceiling is evaluated on subtotal (pre-tax, pre-freight). Program budget is evaluated on tax-inclusive total (plus freight if the memo provides freight).
 10. **Cancelled records.** Cancelled POs are excluded from contract ceiling accumulation and from included_po_ids. Cancelled records are noted under excluded_cancelled_po_ids.
 11. **Set semantics.** When the template says list fields are sets, use the evaluator's sort. This means order doesn't matter but deduplicate values.
 12. **Always validate against the answer template.** Before returning output, verify every required key is present, every enum value is from the allowed list, and every numeric field has the correct precision.
