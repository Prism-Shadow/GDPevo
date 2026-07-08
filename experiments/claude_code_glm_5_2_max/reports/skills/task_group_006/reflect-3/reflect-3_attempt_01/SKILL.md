# ProcureOps ERP Procurement Solver Skill (task_group_006)

Reusable workflow rules for solving ProcureOps procurement-control tasks against the
shared API. The API is the source of truth; local memos only name anchors (PO/receipt/
invoice/contract IDs, dates, as-of dates, business-control rates). All amounts are USD
unless a template field states otherwise; round numbers to the precision each field demands.

## 0. Environment & API recipe (all families)

- Remote API base: `<remote-env-url>` (task prompts say `127.0.0.1:8006` — same service).
- `GET /health`, `GET /manifest` (record counts + anchor ids, no answer keys).
- By id: `GET /<coll>/<id>` -> the record object. List: `GET /<coll>?<field>=<val>` ->
  `{"count":N,"results":[...]}`. Field filters are substring/case-insensitive (incl. nested
  list values); blanks ignored. `start`/`end` filter the collection date field (inclusive).
  There is NO pagination param; unknown query params become field filters returning 0.
- Collections + id field + date field:
  programs(program_id), suppliers(supplier_id), items(sku), contracts(contract_id, effective_date),
  purchase_requisitions(requisition_id, need_by), purchase_orders(po_id, order_date),
  receipts(receipt_id, receipt_date), ap_invoices(invoice_id, invoice_date),
  payments(payment_id, scheduled_date), approval_events(event_id, event_date),
  budget_snapshots(snapshot_id, snapshot_date), vendor_risk_events(event_id, event_date).
- Workflow: (1) read prompt + memo + answer_template (units, enums, ordering per field);
  (2) pull anchors by id, not whole collections; (3) follow links PO->receipts->invoices->payments
  and contract->PO->invoice line prices; (4) scope every list to the as-of / review date;
  (5) sort every list field exactly as the template states; (6) emit only JSON matching the template.

### Reconciliation chains (load-bearing)
- PO -> receipts (same po_id; multiple allowed) -> ap_invoices (invoice.po_id and/or invoice.receipt_id)
  -> payments (payment.invoice_id).
- contract.unit_price == PO line unit_price == invoice line unit_price is the 3-way price anchor.
- contract (contract_id) <-> PO.contract_id; program (program_id) <-> contracts/POs/requisitions/
  budget_snapshots/invoices(via po.program_id); supplier <-> vendor_risk_events/contracts/POs/invoices.
- Approval state of an object: `GET /approval_events?object_id=<id>` (object_type requisition/contract/invoice).

### Date scoping (most common root cause of wrong list fields)
- "as of / as_of / review_as_of / close_date / snapshot as of D": include records whose date field
  (receipt_date / invoice_date / event_date / scheduled_date / snapshot_date) is `<= D`. FUTURE-dated
  receipts on the same PO are EXCLUDED from as-of receipt evidence and from received-qty totals.
- Open supplier risk as of D: vendor_risk_events with status in {open, monitoring} AND event_date <= D.
- Payments reducing a close balance: scheduled_date <= the close cutoff the memo states (e.g. through 2026-06-30).

### Quantity/amount conventions
- Quantities: 2 decimals. Prices: template usually wants USD dollars (2 decimals); read each field.
- received_qty for an invoice = sum over receipts on its PO with receipt_date <= as-of/close date
  (use 0.00 when no receipt exists). billed_qty = invoice line quantity_billed (highest-level value).
- short_qty = ordered - received; unreceived_billed = billed - received; completion = received/ordered.

---

## Family A — Sourcing nomination readiness (program packet, as-of date)

Output template (train_001/test_003): program_id, as_of_date, package_line_skus (sorted asc),
program_summary{owner, budget_headroom_usd, overall_readiness}, nomination_lines[], committee_action{}.

### API queries
- Program: `GET /programs/<program_id>`.
- Per package SKU (from memo anchors): requisition `GET /purchase_requisitions/<req_id>`,
  PO `GET /purchase_orders/<po_id>`, contract lookups `GET /contracts?sku=<sku>` and
  `GET /contracts?program_id=<program_id>` (commercial_basis_id = active contract covering
  sku+supplier+program; null if none).
- Receipts in scope: `GET /receipts?po_id=<po_id>` then filter receipt_date <= as_of.
- Invoice exceptions in scope: `GET /ap_invoices?po_id=<po_id>` then filter invoice_date <= as_of;
  treat as exception any invoice with status `on_hold`/`pending_receipt` OR hold_code != null.
- Supplier + risk: `GET /suppliers/<supplier_id>`; `GET /vendor_risk_events?supplier_id=<supplier_id>`
  (open/monitoring, event_date <= as_of).
- Approval: `GET /approval_events?object_id=<requisition_id>`.

### Field rules
- package_line_skus: sorted ascending (alphabetical).
- budget_headroom_usd: from budget_snapshots for the program with snapshot_date <= as_of (use the
  snapshot dated at/as-of the review date). Compute headroom against the snapshot: the as-of
  budget exposure = committed_amount + pending_invoice_amount vs budget_cap. Report the headroom
  consistent with the snapshot (committed + pending_invoice vs cap). overall_readiness reflects
  that exposure AND line readiness: `ready` only if no blockers anywhere; `at_risk` if salvageable
  (committed headroom positive / conditional lines); `not_ready` if over-exposed or a line is held.
- nomination_lines (one per package SKU):
  - selected_supplier_id: PO supplier (== item.preferred_supplier_id usually).
  - commercial_basis_id: active contract id for the sku/supplier/program, else null.
  - package_po_ids: package POs (sorted asc).
  - receipt_evidence_ids: receipts on package POs with receipt_date <= as_of (sorted asc).
  - invoice_exception_ids: on-hold / held-code invoices on package POs, invoice_date <= as_of (sorted asc).
  - risk_event_ids: open/monitoring supplier risk events (event_date <= as_of) for the line's supplier (sorted asc).
  - blocker_codes (sorted asc) from: `missing_contract` (no active contract covers the sku/supplier),
    `supplier_watch` (supplier.risk_rating == "watch"), `open_supplier_risk` (any open/monitoring
    vendor_risk_event for the supplier as of as_of), `ap_hold` (an on-hold / held-code invoice on a
    package PO as of as_of), `pending_receipt` (PO not fully received / no receipt yet), `late_due_date`
    (PO or requisition need_by/due_date <= as_of), `none`.
  - readiness_status: `ready` iff blocker_codes == [none]; `at_risk` if commercial basis intact (contract
    present) with clearable blockers (pending_receipt partial, ap_hold from a receipt-driven variance,
    supplier_watch, non-severe open risk); `not_ready` if a hard blocker (missing_contract, no receipt
    at all, late_due_date, severe open risk).
  - nomination_decision: `nominate`==ready, `conditional_nomination`==at_risk, `hold`==not_ready.
- committee_action:
  - nominate_now_supplier_ids = suppliers with a `nominate` line; conditional_supplier_ids = `conditional`;
    hold_supplier_ids = `hold` (all sorted asc).
  - next_owner (single): route by the dominant blocker — missing_contract/contract work -> `buyer`;
    AP holds to clear -> `ap_team`; financial/balance -> `finance_ops`; inspection -> `quality_ops`;
    packet ownership/coordination -> `program_owner`.
  - send_to_committee: `yes` when the packet is being delivered for committee review (the memo requests
    committee review); `no` when nothing is nominate-ready and it must be remediated first.

### Pitfalls (Family A)
- Forgetting to exclude FUTURE-dated receipts/invoices from as-of lists.
- Counting a supplier's open risk events that are `closed`/`resolved` as blockers.
- Treating risk_rating "watch" as the only supplier-risk signal (open events also raise open_supplier_risk).
- supplier_watch is context-only in some families (D) but IS a blocker code here.
- Missing the missing_contract blocker when a PO has contract_id null AND no sku contract exists.

---

## Family B — Receiving-control closeout (single batch)

Output template (train_002/test_001/test_004): batch_id, inspection_summary, line_reconciliation[],
invoice_review, financials, decision, supplier_risk_context, evidence.

### API queries
- `GET /receipts/<batch_id>` -> po_id, supplier_id, warehouse_id, receipt_date, packing_slip, receiver,
  status, lines[{po_line_id, sku, quantity_received, quantity_rejected, inspection_status}].
- `GET /purchase_orders/<po_id>` (program_id, status, lines[quantity, unit_price]),
  `GET /contracts/<po.contract_id>` (unit_price anchor).
- The batch's invoice = ap_invoices on the PO whose `receipt_id == <batch_id>` (`GET /ap_invoices?po_id=<po_id>`).
  Use ONLY that invoice (other invoices on the PO belong to other receipts / are excluded).
- `GET /suppliers/<supplier_id>`, `GET /vendor_risk_events?supplier_id=<supplier_id>`.

### Field rules
- inspection_summary: po_id, program_id (from PO), supplier_id, supplier_name, warehouse_id,
  receipt_date, packing_slip, receiver (all from the receipt record).
- line_reconciliation (sort by po_line_id asc), per batch receipt line:
  - ordered_qty = PO line quantity; received_qty = receipt line quantity_received;
    rejected_qty = receipt line quantity_rejected; billed_qty = invoice line quantity_billed.
  - short_qty_vs_po = ordered - received; unreceived_billed_qty = billed - received;
    receipt_completion_ratio = received/ordered (precision 4).
  - po_unit_price, contract_unit_price, invoice_unit_price (precision 2); contract_price_match =
    (contract.unit_price == invoice unit_price) — usually also == PO unit_price.
- invoice_review: invoice_id, invoice_status, hold_code, receipt_status (the receipt's status),
  po_status (the PO's status), exception_codes (set) from:
  [INVOICE_QTY_EXCEEDS_RECEIPT (billed>received), PARTIAL_RECEIPT (received<ordered),
   SUPPLIER_WATCH_RISK (supplier.risk_rating=="watch"), PRICE_MISMATCH (any price differs),
   DAMAGE_REJECTION (quantity_rejected>0), NO_EXCEPTION].
  - **CONFIRMED: include SUPPLIER_WATCH_RISK whenever supplier.risk_rating == "watch"** (dropping it
    lowers the score). It overlaps supplier_risk_context but is still an invoice-review exception.
- financials (USD 2dec): received_goods_value = received_qty * unit_price (PO/contract);
  unreceived_goods_value = short_qty * unit_price; invoice_subtotal/freight/tax/total from the invoice.
- decision enums:
  - batch_disposition: accept_partial_hold_variance | release_full_invoice | reject_batch | manual_recount_required.
  - ap_action: keep_invoice_on_hold | release_invoice | void_invoice.
  - receiving_action: record_shortage_follow_up | no_receiving_action | reject_all_units.
  - supplier_action: request_credit_or_remaining_delivery | no_supplier_action | supplier_debit_for_damage.
  - Pattern: partial receipt with billed>received, no damage, invoice on hold -> accept_partial_hold_variance +
    keep_invoice_on_hold + record_shortage_follow_up + request_credit_or_remaining_delivery.
- supplier_risk_context: supplier_risk_rating; has_open_supplier_risk (any open/monitoring event as of
  the review date); open_supplier_risk_event_ids (sorted asc; only open/monitoring).
- evidence: endpoint_record_ids = API records actually retrieved for this batch (receipt, PO, contract,
  invoice, supplier, risk event); task_payloads_reviewed = the memo filename(s) in input/payloads
  (the answer_template is a schema, not a "payload reviewed" — list only substantive memos).

### Pitfalls (Family B)
- Using the wrong invoice (a different PO invoice whose receipt_id != batch). Match on receipt_id.
- Forgetting SUPPLIER_WATCH_RISK in exception_codes when supplier is on "watch".
- Setting receipt_status to PO status instead of the receipt record's status.
- Including a closed/resolved risk event in open_supplier_risk_event_ids.
- Listing the answer_template.json as a "payload reviewed".

---

## Family C — AP close / vendor-balance + hold/release (invoice slice)

Output template (train_003/test_002): task_id, close_date, invoice_decisions[], vendor_balances[],
program_summary[], payment_hold_queue, payment_release_queue, total_close_balance.

### API queries
- For each target invoice: `GET /ap_invoices/<invoice_id>` -> po_id, supplier_id, status, hold_code,
  total, lines[q.quantity_billed, unit_price].
- `GET /purchase_orders/<po_id>` -> program_id, line quantity (PO qty for variance %).
- `GET /receipts?po_id=<po_id>` -> received qty (sum quantity_received over receipts with
  receipt_date <= close_date; 0 if none).
- `GET /payments?invoice_id=<invoice_id>` -> scheduled payments; sum amounts with scheduled_date <=
  the cutoff the memo states (e.g. through 2026-06-30).
- `GET /suppliers/<supplier_id>` -> name.

### Field rules (CONFIRMED — this family scored 1.0 with these rules)
- invoice_decisions (sort invoice_id asc):
  - invoice_status: raw ProcureOps invoice status (approved / on_hold / pending_receipt / paid / cancelled).
  - hold_decision: `HOLD` if status in {on_hold, pending_receipt} (or hold_code non-null and not approved/paid);
    `RELEASE` if status == approved and 3-way match holds. release_to_payment = (hold_decision == RELEASE).
  - hold_code: the invoice's hold_code (null if none).
  - quantity_billed (2dec); quantity_received (2dec, 0.00 if no receipt; SUM receipts <= close_date);
    quantity_variance = billed - received (2dec); quantity_variance_pct = variance / PO_quantity * 100
    (1 decimal). Use the PO line quantity as the denominator.
  - invoice_total (2dec); scheduled_payment_amount = sum of payments for the invoice with
    scheduled_date <= cutoff (2dec); net_balance_impact = invoice_total - scheduled_payment_amount (2dec).
  - reason_codes (alphabetical) from [APPROVED_THREE_WAY_MATCH, NO_RECEIPT, QTY_VARIANCE, SCHEDULED_PAYMENT_FOUND]:
    - RELEASE + PO/receipt/invoice qty&price match -> APPROVED_THREE_WAY_MATCH.
    - a scheduled payment exists (<= cutoff) -> SCHEDULED_PAYMENT_FOUND.
    - hold_code == QTY_VARIANCE (receipt exists, billed != received) -> QTY_VARIANCE.
    - hold_code == NO_RECEIPT / no receipt on PO -> NO_RECEIPT.
    - **CONFIRMED: when there is NO receipt, use NO_RECEIPT alone (do NOT also add QTY_VARIANCE),
      even though billed != received numerically.** reason_codes are driven by the hold_code + match flags.
- vendor_balances (sort supplier_id asc), one per supplier in the slice:
  - opening_balance: the memo's stated slice opening (0.00 if "treat opening as 0").
  - invoice_total = sum of this slice's invoice totals for the supplier; scheduled_payments = sum of
    scheduled payments (<= cutoff) for those invoices; held_invoice_total = sum of invoice totals where
    hold_decision == HOLD; releasable_invoice_total = sum where hold_decision == RELEASE.
  - close_balance = opening_balance + invoice_total - scheduled_payments (2dec).
  - balance_status: `OPEN_HELD` if any held invoice; `FULLY_SCHEDULED` if close_balance == 0 (scheduled
    payments cover the slice); else `OPEN_APPROVED`.
- program_summary (sort program_id asc): invoice_count, invoice_total, held_total, released_total,
  net_close_balance (= sum of those invoices' close_balances / invoice_total - scheduled).
- payment_hold_queue (invoice_id asc) = invoices with hold_decision == HOLD.
- payment_release_queue (invoice_id asc) = invoices with release_to_payment == true.
- total_close_balance = sum of all vendor close_balances = total invoice_total - total scheduled_payments.

### Pitfalls (Family C)
- Adding QTY_VARIANCE alongside NO_RECEIPT (wrong — NO_RECEIPT alone).
- Using all receipts regardless of date (must scope receipt_date <= close_date for received qty).
- Forgetting SCHEDULED_PAYMENT_FOUND when a payment is scheduled within the cutoff.
- close_balance formula: opening + invoice_total - scheduled_payments (not minus held/releasable).
- balance_status FULLY_SCHEDULED only when close_balance == 0 (payment fully covers slice).

---

## Family D — Change-control contract amendment

Output template (train_004/test_005): change_request_id, program_id, contract_id, sku, supplier_id,
variant_code, decision, contract_check, program_budget_check, approval_check, supplier_risk_check,
supporting_ids, required_actions, summary.

### API queries
- `GET /contracts/<contract_id>` (status, price_type, unit_price, ceiling_amount, supplier_id, sku).
- Existing usage: `GET /purchase_orders?contract_id=<contract_id>` -> all POs on the contract.
  noncancelled = POs with status != cancelled; cancelled = status == cancelled.
- `GET /budget_snapshots?program_id=<program_id>` (snapshot_date <= memo_date; use the as-of snapshot).
- `GET /approval_events?object_id=<source_requisition_id>` (latest event = max event_date).
- `GET /suppliers/<supplier_id>`, `GET /vendor_risk_events?supplier_id=<supplier_id>`.

### Field rules (CONFIRMED — scored 1.0)
- change_request_id = the memo's memo_id (e.g. MCR-...).
- contract_check:
  - contract_status, price_type, unit_price, ceiling_amount (from contract).
  - noncancelled_subtotal = SUM of subtotal over NON-cancelled POs on the contract.
  - requested_quantity = memo's requested_incremental_quantity.
  - requested_subtotal = requested_quantity * unit_price  (ceiling exposure = line subtotal BEFORE tax/freight).
  - headroom_before_change = ceiling_amount - noncancelled_subtotal.
  - headroom_after_change = headroom_before_change - requested_subtotal.
  - ceiling_ok = (headroom_after_change >= 0).
- program_budget_check:
  - snapshot_id, budget_cap, committed_amount from the as-of budget_snapshot.
  - remaining_budget = budget_cap - committed_amount  (**do NOT subtract pending_invoice_amount here —
    change authority is committed-based**).
  - requested_tax = requested_subtotal * (memo tax_rate_percent / 100) (2dec).
  - requested_total = requested_subtotal + requested_tax (+ freight ONLY if the memo provides a freight
    amount; most change memos provide none -> no freight).
  - budget_after_change = remaining_budget - requested_total.
  - budget_ok = (budget_after_change >= 0).
  - max_quantity_with_current_budget = floor(remaining_budget / (unit_price * (1 + tax_rate_percent/100)))
    (integer; no freight unless memo provides it).
- approval_check:
  - source_requisition_id = memo's source_requisition_id.
  - latest_event_id/action/actor/event_date = the approval_event with max event_date.
  - approval_ok = (latest_action is in the memo's approval_good_actions, typically ["approved"]).
    "submitted"/"held"/"rejected" -> not ok.
- supplier_risk_check:
  - supplier_status, supplier_risk_rating (from supplier).
  - open_event_ids = open/monitoring vendor_risk_events (event_date <= memo_date), sorted asc.
  - severe_open_event_ids = subset with severity in {high, critical}, sorted asc.
  - supplier_risk_ok: per memo "supplier_watch_rating: context only unless an open severe event is found"
    -> TRUE if severe_open_event_ids is empty (a "watch" rating alone does NOT fail this check).
- supporting_ids (all sorted asc):
  - included_po_ids = non-cancelled POs on the contract.
  - excluded_cancelled_po_ids = cancelled POs on the contract.
  - approval_event_ids = all approval_events for the source requisition.
- required_actions (sorted asc) from [obtain_final_requisition_approval, raise_budget_exception_or_reduce_quantity,
  resolve_supplier_risk_hold, none]: add one per failing check (approval, budget, supplier-risk). `none` only
  if all checks pass.
- decision: `release_amendment` if all checks ok; `hold_for_budget` if only budget fails; `hold_for_approval`
  if only approval fails; `hold_for_supplier_risk` if only supplier-risk fails; `hold_for_budget_and_approval`
  if both budget and approval fail; `reject_contract_mismatch` if contract ceiling/price cannot cover.
- summary: blocker_count = number of failing checks (= count of non-none required_actions); currency = USD
  (or memo's currency); ready_to_release = (blocker_count == 0).

### Pitfalls (Family D)
- Subtracting pending_invoice_amount from remaining_budget (wrong — use committed_amount only).
- Including cancelled PO subtotals in noncancelled_subtotal (must exclude status == cancelled).
- Including tax in the contract ceiling exposure (ceiling uses subtotal only; budget uses subtotal + tax).
- Setting supplier_risk_ok = false just because risk_rating == "watch" (only severe OPEN events fail it).
- approval_ok from requisition.status instead of the latest approval_event action (use the event action).
- Forgetting freight only when the memo explicitly provides it.

---

## Family B-variant — Receiving/AP release+hold file (multiple POs/receipts/invoices + chargeback register)

Output template (train_005): task_id, review_as_of, target_ids, release_decisions[],
receiving_exceptions[], summary.

### API queries
- target_ids come from the packet (po_ids, receipt_ids, invoice_ids). Fetch each by id:
  `GET /purchase_orders/<po_id>`, `GET /receipts/<receipt_id>`, `GET /ap_invoices/<invoice_id>`.
- For excluded_same_po_receipt_ids: `GET /receipts?po_id=<po_id>` to find ALL receipts on a PO
  (to identify same-PO receipts not in this invoice's scope).
- Chargeback data comes from the LOCAL chargeback_register_excerpt in the packet (not the API) —
  match by invoice_id / po_id / receipt_id.

### Field rules (held-net rule CONFIRMED; chargeback mapping CONFIRMED)
- target_ids: all ID lists sorted ascending (ASCII: digits < uppercase letters, so PO-00031 < PO-AX17-4481).
- release_decisions (one per target invoice):
  - receipt_ids_in_scope: receipts tied to this invoice (invoice.receipt_id, or the PO's in-scope target
    receipts); [] if the invoice/PO has none.
  - excluded_same_po_receipt_ids: other receipts on the same PO that are NOT in this invoice's scope
    (e.g. a same-PO receipt belonging to a different, non-target invoice).
  - approved_chargeback_amount = sum of chargeback basis_qty * unit_cost for chargebacks on this invoice
    with status == approved; pending_chargeback_amount = same for status == pending_quality_review.
  - net_release_amount: for RELEASED invoices = invoice_total - approved_chargeback_amount;
    **for HELD invoices = 0.00 (NOT the prospective invoice-total-minus-chargebacks).**
  - decision / primary_reason mapping (driven by the chargeback register):
    - approved chargeback, reason "Underage Quantity" -> release_net_after_approved_chargeback / approved_qty_chargeback.
    - approved chargeback, reason "AP Quantity Variance" -> release_net_after_approved_chargeback / approved_ap_quantity_variance.
    - chargeback status pending_quality_review (receipt on inspection_hold) -> hold_pending_quality_chargeback / inspection_hold_pending_chargeback.
    - no receipt on the PO (no chargeback) -> hold_missing_receipt / no_receipt_on_po.
- receiving_exceptions (one per target receipt):
  - exception_codes (from [Underage Quantity, Severe Unmatched Quantity, Inspection Hold, AP Quantity Variance]):
    Underage Quantity when received < ordered; Inspection Hold when receipt.status == inspection_hold;
    AP Quantity Variance when invoice billed > received (receipt otherwise clean); Severe Unmatched Quantity
    for large unmatched gaps. (A receipt can carry more than one code; the receiving_exceptions dimension is
    set-tolerant, but prefer the chargeback reason code + the receipt status as the two signals.)
  - chargeback_status: approved | pending_quality_review | not_applicable (mirrors the chargeback register
    line for that receipt; not_applicable if no chargeback references the receipt).
  - resolution_status: net_release_ready (approved chargeback) | hold_for_quality_review (pending/inspection
    hold) | accepted_no_receiving_exception (clean receipt, no chargeback) | missing_receipt (no receipt).
- summary:
  - release_invoice_ids (asc) = invoices with a release_* decision; hold_invoice_ids (asc) = hold_* decisions.
  - approved_chargeback_total = sum of all APPROVED chargeback amounts (across all invoices);
    pending_chargeback_total = sum of all PENDING chargeback amounts.
  - net_release_total = sum of net_release_amount over RELEASED invoices only (held contribute 0).
  - authoritative_sources (from [procureops_po_records, procureops_receipt_records, procureops_ap_records,
    local_chargeback_register]): include each ProcureOps collection you retrieved + local_chargeback_register
    (the chargeback register is authoritative for chargeback amounts, NOT supporting-only).
  - supporting_only_sources (from [ap_release_request_note, stale_po73xx_alias_note]): the packet's
    free-text notes (release request notes, alias notes) — supporting only.
  - followup_actions (from [ask_receiving_for_vantix_receipt, hold_luma_duplicate_receipt_for_separate_invoice,
    route_po00031_quality_review, post_approved_chargeback_netting]): add one per situation present
    (missing receipt -> ask receiving; duplicate same-PO receipt for a separate invoice -> hold it;
    inspection_hold receipt -> route quality review; released-with-approved-chargeback -> post netting).

### Pitfalls (Family B-variant)
- **Setting held invoices' net_release_amount to a prospective (invoice - chargebacks) value — WRONG; held = 0.00.**
- **net_release_total must sum only RELEASED invoices (held are 0).**
- Treating local_chargeback_register as supporting-only (it is authoritative).
- Using the invoice's receipt_id null as "no receipt" when the PO actually has a target receipt in scope
  (use the PO's in-scope target receipt; the invoice may have receipt_id null but the PO/receipt exists).
- Forgetting excluded_same_po_receipt_ids for same-PO receipts belonging to other invoices.
- primary_reason must match the chargeback reason_code (Underage -> approved_qty_chargeback; AP Variance ->
  approved_ap_quantity_variance), not a generic variance label.

---

## Cross-family common mistakes to avoid
1. Date scoping: always filter receipt_date / invoice_date / event_date / scheduled_date / snapshot_date
   to the task's as-of / close / review date. Future records on the same PO are out of scope.
2. Open risk = status in {open, monitoring} (NOT closed/resolved) AND event_date <= as-of.
3. Price match anchor = contract.unit_price; compare to PO line and invoice line unit_price.
4. Read each template field's units/precision/ordering literally (USD cents vs dollars; sort asc; set vs list).
5. ID list sorting is ASCII ascending (digits before uppercase letters): AP-00027 < AP-LUMA-7714 < AP-VANTIX-2188;
   PO-00031 < PO-AX17-4481; RCV-00017 < RCV-BLUE-14.
6. Use the LOCAL memo only for anchors (IDs, dates, rates, requested qty, tax rate, business-control rules);
   pull all operational state from the API. The chargeback register (Family B-variant) is local and authoritative.
7. Emit ONLY the JSON object matching the template — no prose, no extra fields, no judge/test calls.
