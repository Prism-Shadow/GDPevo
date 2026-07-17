# SKILL — ProcureOps Procurement Reconciliation (task_group_006)

Executable recipes for the four task families in this benchmark. The remote API is
the single source of truth; local memos only name the target IDs and business rules.
Work each task by: (1) read memo → extract target IDs + business controls + as-of date,
(2) fetch each linked API record by exact id, (3) reconcile, (4) fill the template.

## 0. API access rules (read first — these bite)

- Base URL: `<remote-env-url>`. Task prompts say `127.0.0.1:8006` = same service.
- List: `GET /<coll>` → `{"count":N,"results":[...]}`. By id: `GET /<coll>/<id>` → the record object.
- **FILTERS REQUIRE THE FULL EXACT ID STRING.** `?po_id=PO-AX17-4481` works; `?po_id=AX17`
  and `?po_id=4481` return `count:0`. Do NOT trust "substring" claims — always pass the
  complete id. Unknown query params are silently treated as field filters and yield 0.
- Date range on a collection's date field: `?start=YYYY-MM-DD&end=YYYY-MM-DD` (inclusive).
  Date field per collection: contracts=effective_date, requisitions=need_by,
  purchase_orders=order_date, receipts=receipt_date, ap_invoices=invoice_date,
  payments=scheduled_date, approval_events=event_date, budget_snapshots=snapshot_date,
  vendor_risk_events=event_date.
- Endpoint aliases: `/ap_invoices`==`/ap/invoices`; `/payments`==`/ap/payments`;
  `/budget_snapshots`==`/budgets`; `/approval_events`==`/approvals`;
  `/vendor_risk_events`==`/vendor-risks`; `/purchase_requisitions`==`/purchase-requisitions`==`/purchase-requests`;
  `/purchase_orders`==`/purchase-orders`.
- Collections: programs, suppliers, items, contracts, purchase_requisitions,
  purchase_orders, receipts, ap_invoices, payments, approval_events, budget_snapshots,
  vendor_risk_events. ID fields: program_id, supplier_id, sku, contract_id,
  requisition_id, po_id, receipt_id, invoice_id, payment_id, event_id, snapshot_id.
- Health: `GET /health`. Manifest (record counts + anchor ids, no answers): `GET /manifest`.

## 1. Cross-cutting reconciliation & conventions

Record field shapes (verified):
- programs: program_id, name, owner, status, priority, region, cost_center, budget_cap, committed_amount.
- suppliers: supplier_id, name, status, region, risk_rating, payment_terms.
- items: sku, description, category, uom, standard_cost, active, preferred_supplier_id.
- contracts: contract_id, supplier_id, program_id, sku, status, price_type, unit_price,
  ceiling_amount, effective_date, expiry_date, buyer.
- purchase_requisitions: requisition_id, program_id, sku, quantity, need_by, priority, requester, status.
- purchase_orders: po_id, supplier_id, program_id, contract_id, requisition_id, status,
  order_date, due_date, currency, ship_to, buyer, subtotal, tax, total, lines[].
  line = {line_id, sku, description, quantity, unit_price}.
- receipts: receipt_id, po_id, supplier_id, status, receipt_date, receiver, warehouse_id,
  packing_slip, lines[]. line = {po_line_id, sku, quantity_received, quantity_rejected, inspection_status}.
- ap_invoices: invoice_id, po_id, supplier_id, receipt_id, status, invoice_date, currency,
  subtotal, tax, freight, total, hold_code, lines[]. line = {po_line_id, sku, quantity_billed, unit_price}.
- payments: payment_id, invoice_id, supplier_id, amount, currency, status, scheduled_date.
- approval_events: event_id, object_type, object_id, action, actor, event_date, note_code.
- budget_snapshots: snapshot_id, program_id, snapshot_date, budget_cap, committed_amount, pending_invoice_amount, currency.
- vendor_risk_events: event_id, supplier_id, event_type, severity, status, event_date, related_object_id.

Chain: PO → receipts (same po_id, multiple allowed) → invoices (invoice.po_id and/or
invoice.receipt_id) → payments (payment.invoice_id). Contract ↔ PO.contract_id ↔
PO-line.unit_price ↔ invoice-line.unit_price; contract.unit_price is the price-match
anchor. Program ↔ contracts/requisitions/POs/invoices(via po.program_id)/budget_snapshots.

**Enum sets (use exactly):**
- PO status: `partial_receipt` `received` `open` `cancelled` `confirmed` `closed`
- invoice status: `on_hold` `approved` `pending_receipt` `paid` `entered`
- invoice hold_code: `QTY_VARIANCE` `NO_RECEIPT` `PRICE_VARIANCE` `SUPPLIER_REVIEW` `null`
- receipt status: `accepted` `accepted_with_note` `inspection_hold` (also expect `rejected`/`partial`)
- receipt inspection_status: `passed` `failed` `pending`
- payment status: `scheduled` `released` `blocked`
- contract status: `active` `expired` `draft` ; price_type: `fixed` `indexed` `not_to_exceed`
- requisition status: `converted` `approved` `cancelled` `draft`
- approval action: `submitted` `approved` `returned` `escalated`
- vendor_risk severity: `low` `medium` `high` (`critical` possible); status: `open` `monitoring` `closed` `resolved`
- vendor_risk event_type: `bank_change` `quality_hold` `late_delivery` `invoice_variance` `duplicate_invoice_review` (also `quality_alert`/`financial_distress`/`delivery_disruption`)
- supplier risk_rating: `low` `medium` `high` `watch`

**Amount/precision rules (read each template's per-field unit):**
- USD money: round to cents (2 dp) unless a field says "USD cents" (integer cents) — none
  of the 5 train templates actually request integer cents; all use decimal USD to 2 dp.
  Confirm against the live template.
- Quantities: 2 dp where the template says "rounded to 2 decimals"; integer where it says integer.
- receipt_completion_ratio: 4 dp. quantity_variance_pct: 1 dp. ratio = received/ordered.
- Sort ID lists ascending unless told "set; evaluator sorts" (then order isignoredby evaluator, but emit sorted anyway).

**Common as-of scoping:** most tasks scope evidence to `as_of_date` (the memo date).
Apply cutoffs: receipts with receipt_date <= as_of; invoices with invoice_date <= as_of;
risk events with status in {open,monitoring} AND event_date <= as_of; budget snapshot with
snapshot_date <= as_of (latest). Always state the as_of in the answer.

**hold_code vs reality:** the API hold_code label can lag or mislabel the actual
discrepancy (e.g. an invoice with hold_code `NO_RECEIPT` that actually HAS a receipt, or
`PRICE_VARIANCE` where the line unit_price matches the contract). Always recompute the
discrepancy from quantities/prices; treat hold_code as a label, not as ground truth.

---

## 2. Family A — Sourcing nomination readiness (train_001 / test_003)

### Inputs
- Memo names the program (PRG-AX17) and, per package anchor SKU, a primary requisition_id
  + purchase_order_id. `as_of_date` = memo date.
- Template keys: task_id, program_id, as_of_date, package_line_skus, program_summary
  {owner, budget_headroom_usd, overall_readiness}, nomination_lines[] (one per SKU),
  committee_action {nominate_now_supplier_ids, conditional_supplier_ids,
  hold_supplier_ids, next_owner, send_to_committee}.

### Fetch recipe (per anchor SKU / PO)
1. `GET /programs/<program_id>` → owner, budget_cap, committed_amount.
2. `GET /budget_snapshots?program_id=<program_id>` → pick snapshot with snapshot_date <= as_of
   (latest). budget_headroom_usd = budget_cap − committed_amount (use snapshot's figures;
   they match the programs row). **Do NOT subtract pending_invoice_amount from headroom**
   (pending_invoice_amount is context only; train_004's remaining_budget also excludes it).
3. Per PO: `GET /purchase_orders/<po_id>` → contract_id, status, due_date, lines, requisition_id, supplier_id.
4. `GET /receipts?po_id=<po_id>` (exact) → receipts; keep those with receipt_date <= as_of as receipt evidence.
5. `GET /ap_invoices?po_id=<po_id>` (exact) → invoices; keep invoice_date <= as_of.
6. `GET /suppliers/<supplier_id>` → risk_rating. `GET /vendor_risk_events?supplier_id=<supplier_id>` → open/monitoring events as of as_of.
7. `GET /contracts/<contract_id>` only if PO.contract_id non-null (commercial basis).
8. `GET /purchase_requisitions/<requisition_id>` → need_by (for late_due_date).
9. `GET /approval_events?object_id=<requisition_id>` → approval state (context; not a listed blocker but informs readiness).

### Per-line blocker matrix (blocker_codes, sorted ascending; enum fixed)
- `missing_contract` — PO.contract_id is null/empty (no commercial basis). HARD.
- `supplier_watch` — supplier.risk_rating == "watch". SOFT.
- `open_supplier_risk` — ≥1 vendor_risk_event for the supplier with status in {open,monitoring}
  and event_date <= as_of. HARD. (Related_object_id may point at a different PO — still counts;
  open supplier risk is supplier-wide.)
- `ap_hold` — ≥1 invoice for the PO (invoice_date <= as_of) with status in {on_hold, pending_receipt}
  OR hold_code non-null. HARD.
- `pending_receipt` — PO not fully received as of as_of: sum(quantity_received across in-scope
  receipts) < PO line quantity, OR no in-scope receipt at all. SOFT→HARD if no receipt.
- `late_due_date` — PO.due_date < as_of_date (contractual delivery already past) while not fully
  received. (Cross-check requisition.need_by < as_of as secondary signal.)
- `none` — only when no other blocker applies.

### Readiness / decision mapping
- readiness_status = `not_ready` if any HARD blocker (missing_contract, open_supplier_risk, ap_hold);
  else `at_risk` if any SOFT blocker (supplier_watch, pending_receipt, late_due_date); else `ready` (blockers==[none]).
- nomination_decision = `nominate` if ready; `conditional_nomination` if at_risk; `hold` if not_ready.
- program_summary.overall_readiness: `not_ready` if budget_headroom_usd < 0 OR any line not_ready;
  `at_risk` if any line at_risk and none not_ready; `ready` if all lines ready and headroom > 0.

### Per-line output fields
- selected_supplier_id = PO.supplier_id (the nominated supplier).
- primary_requisition_id = PO.requisition_id.
- commercial_basis_id = PO.contract_id (the contract id) or null if missing_contract.
- package_po_ids = [po_id] from memo (sorted). (If multiple POs share the SKU, include all named.)
- receipt_evidence_ids = in-scope receipt_ids (receipt_date <= as_of), sorted.
- invoice_exception_ids = in-scope invoice_ids with status in {on_hold,pending_receipt} or
  hold_code non-null, sorted.
- risk_event_ids = open/monitoring event_ids for the supplier as of as_of, sorted.
- blocker_codes as above, sorted ascending; use `none` only if empty.

### committee_action
- nominate_now_supplier_ids = suppliers whose line decision == nominate (sorted).
- conditional_supplier_ids = conditional_nomination (sorted).
- hold_supplier_ids = hold (sorted).
- next_owner priority (pick the dominant hard blocker's owner): ap_hold→`ap_team`;
  missing_contract→`buyer`; open_supplier_risk→`finance_ops`; supplier_watch+pending_receipt→`buyer`;
  if no blockers→`program_owner`. When multiple lines disagree, pick the owner of the most
  blocking issue across all lines; quality holds→`quality_ops`.
- send_to_committee = `yes` if any line is hold/conditional OR overall not_ready/at_risk; else `no`.

### Pitfalls (Family A)
- Forgetting the as_of cutoff: later receipts/invoices (e.g. a second receipt dated after the
  memo) must be EXCLUDED from evidence but the PO status may already reflect them.
- Treating pending_invoice_amount as reducing headroom — it does not (per train_004 consistency).
- Counting a closed/resolved risk event as open — only {open,monitoring} count.
- `open_supplier_risk` is supplier-wide even if related_object_id names another PO.
- Dual receipts on one PO: only the receipt(s) <= as_of count as evidence; the other is a
  separate-invoice follow-up, not nomination evidence.

---

## 3. Family B — Receiving-control closeout (train_002 / test_001 / test_004)

### Inputs
- Memo names one **batch = receipt_id** (e.g. RCV-BLUE-14) and the invoice tied to that batch
  (the invoice whose `receipt_id` == batch_id). as_of = batch receipt_date (or memo's review date).
- Template keys: task_id, batch_id, inspection_summary {po_id, program_id, supplier_id,
  supplier_name, warehouse_id, receipt_date, packing_slip, receiver}, line_reconciliation[]
  (per po_line_id), invoice_review {invoice_id, invoice_status, hold_code, receipt_status,
  po_status, exception_codes}, financials, decision, supplier_risk_context, evidence.

### Fetch recipe
1. `GET /receipts/<batch_id>` → po_id, supplier_id, status(receipt_status), receipt_date, warehouse_id, packing_slip, receiver, lines[].
2. `GET /purchase_orders/<po_id>` → program_id, contract_id, status(po_status), lines[] (ordered_qty, po_unit_price).
3. `GET /ap_invoices?po_id=<po_id>` (exact) → find the invoice whose `receipt_id` == batch_id
   (the tied invoice). If none, the batch has no tied invoice (flag).
4. `GET /contracts/<contract_id>` (if non-null) → contract_unit_price (price-match anchor).
5. `GET /suppliers/<supplier_id>` → name, risk_rating. `GET /vendor_risk_events?supplier_id=<supplier_id>` → open/monitoring events as of receipt_date.

### line_reconciliation (sort by po_line_id ascending) — per receipt line
For each PO line that has a receipt line in this batch:
- ordered_qty = PO line quantity.
- received_qty = receipt line quantity_received (this batch only, NOT other receipts).
- rejected_qty = receipt line quantity_rejected.
- billed_qty = tied-invoice line quantity_billed for that po_line_id (0 if invoice has no line).
- short_qty_vs_po = ordered_qty − received_qty.
- unreceived_billed_qty = billed_qty − received_qty (can be negative if under-billed).
- receipt_completion_ratio = received_qty / ordered_qty, 4 dp.
- po_unit_price = PO line unit_price; contract_unit_price = contract.unit_price; invoice_unit_price = invoice line unit_price.
- contract_price_match = (contract.unit_price == invoice line unit_price) AND (contract.unit_price == PO line unit_price). true when all three agree.

### invoice_review.exception_codes (set; allowed values)
- `INVOICE_QTY_EXCEEDS_RECEIPT` — billed_qty > received_qty for any line.
- `PARTIAL_RECEIPT` — received_qty < ordered_qty for any line (incomplete receipt).
- `SUPPLIER_WATCH_RISK` — supplier.risk_rating == "watch" OR an open/monitoring risk event for the supplier as of receipt_date.
- `PRICE_MISMATCH` — contract_unit_price != invoice_unit_price (or != po_unit_price).
- `DAMAGE_REJECTION` — rejected_qty > 0.
- `NO_EXCEPTION` — only when none of the above apply.
Emit all that apply (set; evaluator sorts). Do not emit NO_EXCEPTION alongside others.

### financials (currency USD, 2 dp) — from the tied invoice + receipt quantities
- received_goods_value = Σ(received_qty × po_unit_price) across lines. (Use po/contract unit price; they match when contract_price_match.)
- unreceived_goods_value = Σ(short_qty_vs_po × po_unit_price).
- invoice_subtotal = tied invoice subtotal.
- invoice_freight = tied invoice freight.
- invoice_tax = tied invoice tax.
- invoice_total = tied invoice total.

### decision (enums)
- batch_disposition: `accept_partial_hold_variance` (partial receipt + qty/price variance held),
  `release_full_invoice` (full receipt, prices match, no exceptions), `reject_batch` (damage/damage_rejection
  dominant), `manual_recount_required` (qty discrepancy unresolvable without recount).
- ap_action: `keep_invoice_on_hold` (invoice on_hold or exceptions present), `release_invoice`
  (full 3-way match, no exceptions), `void_invoice` (duplicate/invalid).
- receiving_action: `record_shortage_follow_up` (short_qty>0), `no_receiving_action` (full receipt),
  `reject_all_units` (damage/damage_rejection).
- supplier_action: `request_credit_or_remaining_delivery` (shortage/underage), `no_supplier_action`
  (clean), `supplier_debit_for_damage` (damage_rejection).
Rule of thumb for a partial receipt with qty-variance hold (the common train case):
batch_disposition=accept_partial_hold_variance, ap_action=keep_invoice_on_hold,
receiving_action=record_shortage_follow_up, supplier_action=request_credit_or_remaining_delivery.

### supplier_risk_context
- supplier_risk_rating = supplier.risk_rating.
- has_open_supplier_risk = (≥1 open/monitoring event as of receipt_date).
- open_supplier_risk_event_ids = sorted list of those event_ids.

### evidence
- endpoint_record_ids = set of all API ids used (po_id, receipt_id, contract_id, invoice_id,
  supplier_id, risk event_ids, program_id). sorted.
- task_payloads_reviewed = the local memo filename(s) reviewed, e.g. "receiving_memo.md".

### Pitfalls (Family B)
- Pulling billed_qty from ALL PO invoices instead of the ONE invoice tied to this batch
  (match invoice.receipt_id == batch_id). Other invoices on the same PO belong to other batches.
- Summing received_qty across multiple receipts — use only THIS batch's receipt line.
- Forgetting contract_price_match checks all three prices (contract↔PO↔invoice).
- exception_codes is a SET — duplicates not allowed; NO_EXCEPTION only when empty.
- A second receipt on the same PO (e.g. RCV-00001 on PO-AX17-4481) is out of scope for this
  batch's reconciliation but is relevant to Family D / train_005 follow-ups.

---

## 4. Family C — AP close / vendor-balance + hold-release (train_003 / test_002)

### Inputs
- Memo names target invoice_ids (a slice), a close_date (memo date), and rules: opening AP
  balance for the slice suppliers = 0.00; any payment already scheduled in ProcureOps through
  a cutoff (e.g. 2026-06-30) reduces the close balance.
- Template keys: task_id, close_date, invoice_decisions[], vendor_balances[], program_summary[],
  payment_hold_queue, payment_release_queue, total_close_balance.

### Fetch recipe (per invoice)
1. `GET /ap_invoices/<invoice_id>` → po_id, supplier_id, status, hold_code, lines[] (quantity_billed), total, invoice_date.
2. `GET /purchase_orders/<po_id>` → program_id, lines[] (PO quantity for variance_pct).
3. `GET /receipts?po_id=<po_id>` (exact) → received qty. Sum quantity_received across receipts
   with receipt_date <= close_date (or all receipts if no date cutoff specified). Use 0 if none/no receipt_id.
4. `GET /payments?invoice_id=<invoice_id>` (exact) → scheduled payments with scheduled_date <= cutoff, status in {scheduled, released}. Sum amounts.
5. `GET /suppliers/<supplier_id>` → name.

### invoice_decisions (sort by invoice_id ascending)
- program_id = PO.program_id; po_id; supplier_id; supplier_name.
- invoice_status = invoice.status (from ProcureOps).
- hold_decision: `RELEASE` if invoice.status == "approved" AND hold_code is null AND
  quantity_received >= quantity_billed (clean three-way match); `HOLD` otherwise
  (status in {on_hold, pending_receipt, entered} or any blocking hold_code or qty mismatch).
- hold_code = invoice.hold_code (string) or null.
- release_to_payment = (hold_decision == RELEASE).
- quantity_billed = Σ invoice line quantity_billed (2 dp).
- quantity_received = Σ receipt quantity_received for the PO as of cutoff (0.00 if none).
- quantity_variance = quantity_billed − quantity_received (2 dp).
- quantity_variance_pct = (quantity_variance / PO line quantity) × 100, 1 dp. (PO quantity =
  Σ PO line quantity for the matching sku/line; use the PO line(s) the invoice lines reference.)
- invoice_total = invoice.total (2 dp).
- scheduled_payment_amount = Σ payment.amount for payments scheduled_date <= cutoff,
  status in {scheduled, released} (2 dp).
- net_balance_impact = invoice_total − scheduled_payment_amount (2 dp).
- reason_codes (alphabetical, enum): `APPROVED_THREE_WAY_MATCH` (status approved & hold null &
  received>=billed), `NO_RECEIPT` (no receipt / received==0), `QTY_VARIANCE` (quantity_variance != 0),
  `SCHEDULED_PAYMENT_FOUND` (scheduled_payment_amount > 0). Emit all that apply (can be empty
  only if none match — but QTY_VARIANCE or APPROVED_THREE_WAY_MATCH usually applies).

### vendor_balances (sort by supplier_id ascending) — group invoice_decisions by supplier
- opening_balance = 0.00 (per memo for the slice).
- invoice_total = Σ invoice_total for that supplier's slice invoices.
- scheduled_payments = Σ scheduled_payment_amount for that supplier.
- held_invoice_total = Σ invoice_total where hold_decision == HOLD.
- releasable_invoice_total = Σ invoice_total where hold_decision == RELEASE.
- close_balance = opening_balance + invoice_total − scheduled_payments (2 dp).
- balance_status: `OPEN_HELD` if held_invoice_total > 0; else `FULLY_SCHEDULED` if
  scheduled_payments >= invoice_total (within 0.005); else `OPEN_APPROVED`.

### program_summary (sort by program_id ascending) — group by PO.program_id
- invoice_count, invoice_total, held_total (Σ held invoice_total), released_total (Σ released),
  net_close_balance = Σ close_balance of the supplier rows for invoices in that program
  (equivalently Σ net_balance_impact for the program's invoices, since opening=0).

### queues (sorted ascending)
- payment_hold_queue = invoice_ids with hold_decision == HOLD.
- payment_release_queue = invoice_ids with hold_decision == RELEASE.
- total_close_balance = Σ vendor_balances.close_balance (2 dp). (Equals Σ net_balance_impact
  across all invoices when opening balances are 0.)

### Pitfalls (Family C)
- variance_pct denominator is the **PO quantity**, not quantity_billed. 24 short / 240 PO = 10.0%.
- A `pending_receipt` invoice (status pending_receipt, hold_code NO_RECEIPT) is a HOLD, not a
  release, even though status isn't literally "on_hold".
- Include `released` payments (already disbursed) in scheduled_payment_amount, not just `scheduled`.
  Exclude `blocked` payments.
- Do NOT carry over real-world opening balances — the memo forces 0.00 for the slice suppliers.
- net_balance_impact can be 0.00 when fully scheduled (invoice_total == scheduled_payment_amount).
- A supplier can appear in only one balance_status row; held takes precedence over fully-scheduled.

---

## 5. Family D — Change-control contract amendment (train_004 / test_005)

### Inputs
- change_memo.json names: program_id, contract_id, supplier_id, sku, variant_code,
  requested_incremental_quantity, source_requisition_id, requested_ship_to, and
  business_controls (currency, tax_rate_percent, budget_exposure rule, contract_ceiling_exposure
  rule, existing_contract_usage rule "exclude cancelled POs", approval_good_actions e.g. ["approved"],
  supplier_watch_rating "context only unless an open severe event is found").
- as_of = memo_date.
- Template keys: change_request_id (= memo_id), program_id, contract_id, sku, supplier_id,
  variant_code, decision, contract_check, program_budget_check, approval_check,
  supplier_risk_check, supporting_ids, required_actions, summary.

### Fetch recipe
1. `GET /contracts/<contract_id>` → status, price_type, unit_price, ceiling_amount, supplier_id, program_id, sku.
2. `GET /purchase_orders?contract_id=<contract_id>` (exact) → all POs on the contract. Partition
   into non-cancelled (status != cancelled) and cancelled (status == cancelled).
3. `GET /budget_snapshots?program_id=<program_id>` → snapshot with snapshot_date <= as_of (latest).
4. `GET /purchase_requisitions/<source_requisition_id>` → status. `GET /approval_events?object_id=<source_requisition_id>` → approval history for the requisition.
5. `GET /suppliers/<supplier_id>` → status, risk_rating. `GET /vendor_risk_events?supplier_id=<supplier_id>` → open/monitoring events.
6. `GET /programs/<program_id>` → budget_cap, committed_amount (cross-check against snapshot).

### contract_check
- contract_status, price_type, unit_price (from contract).
- ceiling_amount (from contract).
- noncancelled_subtotal = Σ PO.subtotal for non-cancelled POs on the contract.
  (Use PO.subtotal, NOT PO.total — ceiling exposure is "line subtotal before tax and freight".)
- headroom_before_change = ceiling_amount − noncancelled_subtotal.
- requested_quantity = memo.requested_incremental_quantity.
- requested_subtotal = requested_quantity × unit_price (contract unit price; before tax/freight).
- headroom_after_change = headroom_before_change − requested_subtotal.
- ceiling_ok = (headroom_after_change >= 0).

### program_budget_check
- snapshot_id, budget_cap, committed_amount (from snapshot <= as_of).
- remaining_budget = budget_cap − committed_amount (do NOT subtract pending_invoice_amount).
- requested_tax = requested_subtotal × (tax_rate_percent / 100), 2 dp.
- requested_total = requested_subtotal + requested_tax (+ freight ONLY if the memo provides a
  freight figure; the train memo does not, so freight = 0). budget_exposure = subtotal + tax.
- budget_after_change = remaining_budget − requested_total.
- budget_ok = (budget_after_change >= 0).
- max_quantity_with_current_budget = floor(remaining_budget / (unit_price × (1 + tax_rate_percent/100)))
  — i.e. how many whole units fit at the taxed per-unit cost. (If freight were provided and
  proportional, fold it in; here freight is lump/zero so per-unit = unit_price×(1+tax).)

### approval_check
- source_requisition_id (from memo).
- From approval_events for that requisition (object_id == requisition_id), pick the latest by
  event_date: latest_event_id, latest_action, latest_actor, latest_event_date.
- approval_ok = (latest_action ∈ approval_good_actions, e.g. == "approved"). A requisition
  status of "approved" is supportive but the approval_events latest action is authoritative.
  Note: requisition.status == "converted" with only a "submitted" event ⇒ NOT approved.

### supplier_risk_check
- supplier_status = supplier.status; supplier_risk_rating = supplier.risk_rating.
- open_event_ids = vendor_risk events for supplier with status in {open,monitoring} and
  event_date <= as_of, sorted ascending.
- severe_open_event_ids = subset of open_event_ids with severity in {high, critical}, sorted.
- supplier_risk_ok: per the memo's rule "supplier_watch_rating: context only unless an open
  severe event is found" → supplier_risk_ok = (severe_open_event_ids is empty). A `watch` rating
  or a non-severe (low/medium) open event does NOT block.

### decision (enum)
- `release_amendment` — contract_ok(ceiling_ok) AND budget_ok AND approval_ok AND supplier_risk_ok.
- `hold_for_budget` — budget_ok false only.
- `hold_for_approval` — approval_ok false only.
- `hold_for_supplier_risk` — supplier_risk_ok false only (severe open event).
- `hold_for_budget_and_approval` — both budget and approval fail (common when over budget AND
  requisition not approved). Combine: if budget AND approval both fail → hold_for_budget_and_approval;
  if budget AND supplier_risk both fail → use hold_for_budget (budget dominates) unless template
  offers a combined code (it does not); pick the most-blocking single/combined code available.
- `reject_contract_mismatch` — contract status not active/expired mismatch, or unit_price mismatch
  vs the SKU, or contract_id null. Use only when the contract itself is the blocker.

### supporting_ids (all sorted ascending)
- included_po_ids = non-cancelled PO ids on the contract.
- excluded_cancelled_po_ids = cancelled PO ids on the contract.
- approval_event_ids = all event_ids for the source requisition (object_id match).

### required_actions (enum; sort ascending)
- `obtain_final_requisition_approval` — emit if approval_ok false.
- `raise_budget_exception_or_reduce_quantity` — emit if budget_ok false.
- `resolve_supplier_risk_hold` — emit if supplier_risk_ok false (severe open event).
- `none` — emit only when all checks pass.
Emit all that apply (sorted); do not emit `none` alongside others.

### summary
- blocker_count = count of failed checks among {ceiling_ok(no), budget_ok, approval_ok, supplier_risk_ok}.
  (ceiling_ok false → counts as a blocker too, but typically maps to reject_contract_mismatch or
  is captured via budget; if ceiling_ok false independently, count it.)
- currency = memo currency (USD).
- ready_to_release = (decision == release_amendment).

### Pitfalls (Family D)
- noncancelled_subtotal uses PO.subtotal, NOT PO.total (ceiling exposure excludes tax/freight).
- remaining_budget excludes pending_invoice_amount (matches the template field semantics).
- requested_total for budget exposure INCLUDES tax (memo: "line subtotal plus estimated tax"),
  but requested_subtotal for ceiling exposure EXCLUDES tax/freight. Keep the two exposures separate.
- max_quantity uses the taxed per-unit cost (unit_price × (1+tax)); floor to integer.
- approval_ok is driven by the latest approval_event action, NOT by requisition.status alone
  (a "converted" requisition with only "submitted" events is NOT approved).
- supplier `watch` rating is context-only (does not block) per the memo; only severe (high/critical)
  OPEN events block. A closed/monitoring non-severe event does not.
- Exclude cancelled POs from both included_po_ids AND the noncancelled_subtotal, but DO list them
  in excluded_cancelled_po_ids.
- If a PO on the contract is `confirmed` (not yet received), it still counts toward ceiling usage
  (only `cancelled` is excluded).

---

## 6. Cross-family: Family B+D hybrid — Receiving/AP release & chargeback (train_005 / test-style)

train_005 blends B and C with a **local chargeback register**. Apply when the packet names POs,
receipts, invoices AND a chargeback_register_excerpt.

### release_decisions (per invoice, sort by invoice_id)
- po_id = invoice.po_id.
- receipt_ids_in_scope = receipts whose po_id == invoice.po_id AND are referenced by a chargeback
  row for this invoice, or the invoice.receipt_id if present. (The receipt the chargeback is built on.)
- excluded_same_po_receipt_ids = OTHER receipts on the same PO not tied to this invoice/chargeback
  (e.g. a second/duplicate receipt). Sorted.
- decision (enum):
  - `release_net_after_approved_chargeback` — receipt accepted, chargeback status == approved
    (net the approved chargeback amount out of the invoice).
  - `hold_missing_receipt` — no receipt exists for the PO (invoice.receipt_id null AND no receipts
    for po_id).
  - `hold_pending_quality_chargeback` — receipt status == inspection_hold OR chargeback status ==
    pending_quality_review.
- primary_reason (enum): `approved_qty_chargeback` (approved underage/qty chargeback),
  `approved_ap_quantity_variance` (approved AP-quantity-variance chargeback),
  `no_receipt_on_po` (no receipt), `inspection_hold_pending_chargeback` (inspection hold / pending review).
- invoice_total = invoice.total.
- approved_chargeback_amount = Σ (basis_quantity × unit_cost) for chargebacks on this invoice with
  status == approved. (0.00 if none.)
- pending_chargeback_amount = Σ (basis_quantity × unit_cost) for chargebacks with status ==
  pending_quality_review. (0.00 if none.)
- net_release_amount = (decision == release_net_after_approved_chargeback)
  ? invoice_total − approved_chargeback_amount : 0.00.

### receiving_exceptions (per receipt in target_ids)
- exception_codes (enum, zero or more): `Underage Quantity` (received < ordered),
  `Severe Unmatched Quantity` (billed severely exceeds received/ordered — large gap),
  `Inspection Hold` (receipt.status == inspection_hold), `AP Quantity Variance` (billed > received).
  Use the chargeback reason_code as the authoritative classification when available.
- chargeback_status (enum): `approved` / `pending_quality_review` / `not_applicable` (no chargeback row).
- resolution_status (enum): `net_release_ready` (chargeback approved), `hold_for_quality_review`
  (inspection hold or pending_quality_review), `accepted_no_receiving_exception` (full receipt, no
  chargeback, no exception), `missing_receipt` (no receipt row for a PO that needs one).

### summary
- release_invoice_ids / hold_invoice_ids = sorted by decision.
- approved_chargeback_total = Σ approved_chargeback_amount (released invoices).
- pending_chargeback_total = Σ pending_chargeback_amount (held invoices).
- net_release_total = Σ net_release_amount.
- authoritative_sources (enum set): `procureops_po_records`, `procureops_receipt_records`,
  `procureops_ap_records`, `local_chargeback_register` — emit all that were actually consulted.
- supporting_only_sources (enum set): `ap_release_request_note` (requester comments in the packet),
  `stale_po73xx_alias_note` (the packet's po73xx_alias_note when it says those ids are absent).
- followup_actions (enum set): `ask_receiving_for_vantix_receipt` (invoice with no receipt on its PO),
  `hold_luma_duplicate_receipt_for_separate_invoice` (a second receipt on a PO tied to a different
  invoice), `route_po00031_quality_review` (inspection_hold receipt → quality), `post_approved_chargeback_netting`
  (when approved chargebacks are netted). Emit the ones that match the situation.

### Pitfalls (train_005 hybrid)
- The packet's `po73xx_alias_note` says exact PO-73xx ids are NOT in the shared API — use the
  `use_available_shared_ids` list instead; mark `stale_po73xx_alias_note` as supporting-only.
- approved_chargeback_amount uses basis_quantity × unit_cost from the LOCAL chargeback register,
  not from the API (the API has no chargebacks collection).
- A receipt can be `accepted` yet still carry an Underage/AP-qty chargeback → net_release_ready,
  NOT a hold. Only inspection_hold or pending_quality_review cause a hold.
- excluded_same_po_receipt_ids matters: PO-AX17-4481 has TWO receipts (RCV-BLUE-14 in scope,
  RCV-00001 excluded → its own invoice AP-00001 is the "duplicate receipt for separate invoice" follow-up).

---

## 7. Quick reference — common misjudgments to avoid

1. **Substring filters**: never use partial ids in `?field=`. Always full exact id. Verify with a
   direct `GET /<coll>/<id>` if a filter returns 0 unexpectedly.
2. **as_of cutoffs**: receipts/invoices/risk-events dated AFTER as_of are excluded from evidence
   but may still appear in PO.status — recompute from dated records, don't trustrolled-up status.
3. **hold_code labels lag reality**: recompute qty/price discrepancies from line items; a
   `NO_RECEIPT` hold_code may coexist with an existing receipt; a `PRICE_VARIANCE` may have matching prices.
4. **billed_qty source**: Family B uses the invoice TIED to the batch (invoice.receipt_id==batch_id),
   not all PO invoices. Family C uses each invoice's own lines.
5. **received_qty source**: Family B uses only THIS batch's receipt line. Family C sums all in-scope
   receipts for the PO. Family D ceiling uses PO.subtotal (not total).
6. **headroom/remaining_budget excludes pending_invoice_amount** (consistent across A and D).
7. **approval state**: the latest approval_event action is authoritative; requisition.status alone
   is not (a "converted" requisition may only have "submitted" events ⇒ not approved).
8. **supplier risk severity**: only `high`/`critical` OPEN/monitoring events block Family D; `watch`
   rating and `low`/`medium` open events are context-only there. But in Family A, ANY open/monitoring
   event triggers `open_supplier_risk` (the A blocker enum has no severity gate).
9. **cancelled POs**: exclude from contract ceiling usage AND from included_po_ids; list them in
   excluded_cancelled_po_ids. A `confirmed` PO still counts (only `cancelled` is excluded).
10. **enum casing**: API uses snake_case statuses; the Family B exception_codes and Family 5
    exception_codes use UPPER_SNAKE / Title Case as given in each template — copy the exact strings.
11. **set vs list**: when the template says "set; evaluator sorts", still emit sorted & deduped.
12. **opening balance**: Family C forces 0.00 for slice suppliers per the memo — do not infer from
    the wider ledger.
13. **tax in budget exposure, not in ceiling exposure**: requested_total (budget) = subtotal + tax
    (+ freight if memo gives it); requested_subtotal (ceiling) = qty × unit_price only.
14. **max_quantity**: floor(remaining_budget / (unit_price × (1+tax%))). Integer.
15. **dual receipts / duplicate invoices**: a PO with two receipts drives two invoices — only the
    in-scope batch's invoice is reconciled in Family B; the other is a follow-up in Family-5-style tasks.

## 8. Worked ID map (anchors, for orientation — NOT answers)

- PRG-AX17 (owner Elena Marsh, budget_cap 285000, committed 216430.4). Snapshot BUD-PRG-AX17 dated 2026-06-01 (pending_invoice_amount 224946.47, context only).
- CR-LMP-228 (active, fixed, unit_price 84.5, ceiling 185000). POs on it: PO-AX17-4481 (partial_receipt, 20280), PO-00027 (confirmed, 21125), PO-00031 (partial_receipt, 24589.5); cancelled: PO-00008, PO-00041.
- SUP-LUMA (LumaPro Industrial, risk_rating watch). Open risk: VRE-00005 (medium, invoice_variance, related PO-00016).
- SUP-VANTIX (Vantix Controls, risk_rating low). Open risk: VRE-00009 (medium, invoice_variance, related PO-00025).
- SUP-HEXEL (Hexel Motion, risk_rating medium). Open risks incl. VRE-00002/00010/00016 (high) — relevant to severity gating in Family D-style checks.
- RCV-BLUE-14 (PO-AX17-4481, accepted, 216 of 240 LMP-228, 2026-05-30). Tied invoice AP-LUMA-7714 (on_hold QTY_VARIANCE, billed 240, total 22070.30). Second receipt RCV-00001 (2026-06-08, after as_of) → invoice AP-00001.
- PO-AX17-4519 (open, DRV-AX17, 75 @ 318.0, no contract, supplier SUP-VANTIX). Invoice AP-VANTIX-2188 (pending_receipt, NO_RECEIPT, no receipt).
- PO-00031 (partial_receipt, LMP-228, 291 @ 84.5, CR-LMP-228, SUP-LUMA). Receipt RCV-00017 (inspection_hold, 192 of 291). Invoice AP-00027 (approved, billed 305 — over PO qty).
- PO-00038 (closed, DRV-AX17, 88 @ 295.94, no contract, SUP-VANTIX). Receipt RCV-00020 (accepted, 88). Invoice AP-00032 (on_hold NO_RECEIPT label but receipt exists; billed 92 > 88).
- PO-NOVA-3107 / RCV-GOLD-27 / AP-HEXEL-3309 (approved, 180@149.75, three-way match). Payment PAY-00001 (scheduled 2026-06-30, 28909.24).

Use this map only to validate fetches; recompute every output field from live records.
