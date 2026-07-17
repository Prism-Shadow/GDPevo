# SKILL — Procurement Supplier & Receiving Control (task_group_006)

Executable recipes for solver agents on unseen test tasks in this benchmark. The
benchmark has FOUR task families (A sourcing-nomination, B receiving-control
closeout, C AP close / vendor-balance, D change-control amendment). Test tasks
map to these families; train_001/003↔test_003, train_002↔test_001/test_004,
train_003↔test_002, train_004↔test_005 (families overlap). Apply the matching
family section plus the cross-cutting rules at the bottom.

## 0. Environment & API (verified 2026-07-02)

- Remote API (source of truth): `<remote-env-url>`. Prompts' `127.0.0.1:8006`
  == this same service. Use curl.
- List: `GET /<coll>` -> `{"count":N,"results":[...]}`. By id: `GET /<coll>/<id>` ->
  the object directly. Field filters match substring/case-insensitive, including
  nested list values; `?start=&end=` filter the collection date field inclusively.
- NEVER pass `_limit`/`page`/`per_page` — unknown params are treated as field
  filters and return 0 rows.
- Collections + ID/date fields:
  `programs`(program_id), `suppliers`(supplier_id), `items`(sku),
  `contracts`(contract_id, effective_date), `purchase_requisitions`(requisition_id, need_by)
  [aliases `/purchase-requests`,`/purchase-requisitions`],
  `purchase_orders`(po_id, order_date) [alias `/purchase-orders`],
  `receipts`(receipt_id, receipt_date), `ap_invoices`(invoice_id, invoice_date)
  [also `/ap/invoices`], `payments`(payment_id, scheduled_date) [also `/ap/payments`],
  `approval_events`(event_id, event_date) [alias `/approvals`],
  `budget_snapshots`(snapshot_id, snapshot_date) [alias `/budgets`],
  `vendor_risk_events`(event_id, event_date) [alias `/vendor-risks`].
- Discovery: `GET /health`, `GET /`, `GET /manifest` (counts + anchor ids, no answers).

## Golden rules (read every time)
1. The memo/payload names the target IDs and scope anchors. API is source of truth
   for record content. Cross-reference by the IDs in the payload — do NOT pull whole
   collections when you have specific IDs.
2. Round USD to cents (2 dp); qty to 2 dp; ratios to 4 dp; pct to 1 dp. Read EACH
   template field's stated unit (some want USD-cents integer; most want USD dollars).
3. Sort list fields ascending unless the template says "set".
4. As-of filtering: evidence (receipts, invoices, risk events, payments) is filtered
   by date <= the task's as_of/close_date/review_as_of. Later same-PO receipts are
   EXCLUDED from "as of" evidence lists (but may appear as excluded_same_po receipts).
5. Cancelled POs are EXCLUDED from contract usage / committed totals (memo control
   "exclude cancelled purchase orders"). For evidence lists, include unless told.

---

## Family A — Sourcing nomination readiness (train_001 / test_003)

### Inputs (from prompt + memo)
- `program_id`, `as_of_date` (e.g. PRG-AX17, 2026-06-01) from prompt.
- `package_line_skus` + anchor requisition/PO per SKU come from the nomination memo's
  "package anchors" list — NOT from querying all program SKUs. Use exactly those SKUs.
- Template: answer_template.json top-level keys `program_id, as_of_date,
  package_line_skus, program_summary{owner,budget_headroom_usd,overall_readiness},
  nomination_lines[], committee_action{...}`.

### Query recipe (per program + per SKU anchor)
1. `GET /programs/<program_id>` -> owner, budget_cap, committed_amount, status.
2. `GET /budget_snapshots?program_id=<pg>` -> pick snapshot with snapshot_date <= as_of
   (for budget readiness). `GET /contracts?program_id=<pg>` -> contract per SKU.
3. `GET /purchase_orders?program_id=<pg>` -> POs; group by line sku to get package_po_ids
   per SKU. (Decide cancelled inclusion per `package_po_ids` — prefer non-cancelled active
   POs for the anchor; document cancelled as out-of-scope if template only wants active.)
4. `GET /purchase_requisitions?program_id=<pg>` -> anchor requisition per SKU (match sku).
5. Per anchor PO: `GET /receipts?po_id=<po>`; keep receipt_date <= as_of -> receipt_evidence_ids.
6. Per supplier: `GET /ap_invoices?supplier_id=<sup>`; keep invoice_date <= as_of AND
   (status=="on_hold" OR hold_code!=null) AND po/line sku matches -> invoice_exception_ids.
7. `GET /vendor_risk_events?supplier_id=<sup>`; keep status in {open,monitoring} AND
   event_date <= as_of -> risk_event_ids (any related_object_id, not just package PO).
8. `GET /suppliers/<sup>` -> risk_rating (drive supplier_watch).

### Field definitions
- `package_line_skus`: the memo's anchor SKUs, sorted ascending.
- `program_summary.budget_headroom_usd` = `programs.budget_cap - committed_amount`
  (program row). overall_readiness also considers the as-of snapshot
  (`committed + pending_invoice_amount vs budget_cap`): overrun -> not_ready/at_risk.
- `nomination_lines[].selected_supplier_id`: contract.supplier_id if contract active,
  else the anchor PO's supplier_id.
- `commercial_basis_id`: contract_id if an ACTIVE contract exists for SKU+program, else null.
- `primary_requisition_id`: anchor requisition_id (the converted/approved one for the SKU).
- `package_po_ids`: POs for the SKU in the program (sorted asc).
- `receipt_evidence_ids`, `invoice_exception_ids`, `risk_event_ids`: as-of filtered, sorted.

### Blocker codes (enum: missing_contract|supplier_watch|open_supplier_risk|ap_hold|pending_receipt|late_due_date|none)
- `missing_contract`: commercial_basis_id == null (no active contract for SKU).
- `supplier_watch`: supplier.risk_rating == "watch".
- `open_supplier_risk`: risk_event_ids non-empty.
- `ap_hold`: invoice_exception_ids non-empty (on_hold invoice <= as_of).
- `pending_receipt`: zero receipts as of as_of, OR received < ordered (partial). [A
  partial accepted receipt still counts as pending if the PO is incomplete; if a full
  receipt exists, no pending_receipt.]
- `late_due_date`: anchor requisition need_by (or PO due_date) <= as_of (overdue).
- `none`: no blockers. Sort blocker_codes ascending; use ["none"] when clear.

### nomination_decision (enum: nominate|conditional_nomination|hold) & readiness_status (ready|at_risk|not_ready)
- `nominate` / `ready`: blocker_codes == ["none"].
- `conditional_nomination` / `at_risk`: only SOFT blockers (supplier_watch, ap_hold,
  pending_receipt-partial, open non-severe risk) AND contract present.
- `hold` / `not_ready`: any HARD blocker (missing_contract, late_due_date, OR a severe
  [high/critical] open risk event).

### committee_action (enum next_owner: buyer|finance_ops|quality_ops|program_owner|ap_team; send_to_committee: yes|no)
- `nominate_now_supplier_ids` = suppliers of nominate lines; `conditional_supplier_ids`
  = conditional; `hold_supplier_ids` = hold (all sorted asc, dedup).
- `next_owner`: ap_team if ap_hold is the dominant blocker; buyer if
  missing_contract/pending_receipt/late_due_date; quality_ops for inspection; finance_ops
  for budget overrun; program_owner default.
- `send_to_committee`: "yes" if any conditional or hold line (needs review); "no" if all nominate.

### Pitfalls (Family A)
- Don't derive SKUs by listing the program's items — use the memo anchors.
- invoice_exception_ids = on_hold invoices only. An approved/paid invoice on the same
  PO is NOT an exception.
- risk events apply at the SUPPLIER level (related_object_id may be a different PO) —
  include all open/monitoring events for the selected supplier as of as_of.
- open RISK of severity medium does NOT by itself force `hold` (only severe does); but
  it does set the `open_supplier_risk` blocker code and at_risk.
- budget_headroom uses the program row (budget_cap - committed_amount); do not subtract
  pending_invoice in that field (it's a readiness signal, not the headroom number).

---

## Family B — Receiving-control closeout

Two sub-variants: **B1 single-batch closeout** (train_002 / test_001, test_004) and
**B2 multi-invoice AP release** (train_005 / test_005). Both reconcile ordered/received/billed.

### B1 Single-batch closeout (batch_id from memo, e.g. RCV-BLUE-14)

#### Query recipe
1. `GET /receipts/<batch_id>` -> po_id, supplier_id, program_id(via PO), warehouse_id,
   receipt_date, packing_slip, receiver, status, lines[].
2. `GET /purchase_orders/<po_id>` -> program_id, status, contract_id, lines[] (ordered qty, unit_price).
3. `GET /contracts/<contract_id>` -> unit_price (price-match anchor), status.
4. `GET /ap_invoices?po_id=<po_id>` -> the invoice(s) whose `receipt_id == batch_id` is
   IN SCOPE. Other invoices on the PO (different receipt_id) are out of scope for this batch.
5. `GET /suppliers/<supplier_id>` -> name, risk_rating. `GET /vendor_risk_events?supplier_id=<sup>`
   -> open/monitoring events as of review date.

#### line_reconciliation (sort by po_line_id asc) — per po_line_id
- `ordered_qty` = PO line quantity; `received_qty` = receipt line quantity_received;
  `rejected_qty` = receipt quantity_rejected; `billed_qty` = in-scope invoice line quantity_billed.
- `short_qty_vs_po` = ordered - received. `unreceived_billed_qty` = billed - received (>=0).
- `receipt_completion_ratio` = received/ordered (4 dp).
- `po_unit_price` (PO line), `contract_unit_price` (contract.unit_price),
  `invoice_unit_price` (invoice line). `contract_price_match` =
  (po_unit_price == contract_unit_price) AND (invoice_unit_price == contract_unit_price).

#### invoice_review.exception_codes (set; allowed: INVOICE_QTY_EXCEEDS_RECEIPT|PARTIAL_RECEIPT|SUPPLIER_WATCH_RISK|PRICE_MISMATCH|DAMAGE_REJECTION|NO_EXCEPTION)
- INVOICE_QTY_EXCEEDS_RECEIPT: billed > received.
- PARTIAL_RECEIPT: PO.status == partial_receipt OR received < ordered.
- SUPPLIER_WATCH_RISK: supplier.risk_rating == "watch".
- PRICE_MISMATCH: po_unit_price != contract_unit_price OR invoice_unit_price != contract_unit_price.
- DAMAGE_REJECTION: rejected_qty > 0.
- NO_EXCEPTION: only if none of the above.

#### financials (USD, 2 dp)
- `received_goods_value` = sum(received_qty * po_unit_price).
- `unreveived_goods_value` = sum((ordered - received) * po_unit_price) [short value].
- `invoice_subtotal`, `invoice_freight`, `invoice_tax`, `invoice_total` from the in-scope invoice.

#### decision (allowed sets in template)
- `batch_disposition`: accept_partial_hold_variance (partial receipt + qty variance,
  batch accepted) | release_full_invoice (full receipt, no variance) | reject_batch
  (damage/rejection) | manual_recount_required (severe mismatch).
- `ap_action`: keep_invoice_on_hold (invoice on_hold) | release_invoice (approved/3-way) | void_invoice (duplicate).
- `receiving_action`: record_shortage_follow_up (short>0) | no_receiving_action (complete) | reject_all_units (damage).
- `supplier_action`: request_credit_or_remaining_delivery (shortage) | supplier_debit_for_damage (damage) | no_supplier_action (complete).

#### supplier_risk_context
- supplier_risk_rating (from supplier), has_open_supplier_risk (any open/monitoring event
  as of review), open_supplier_risk_event_ids (sorted).

#### evidence
- endpoint_record_ids: all IDs you fetched (PO, receipt, contract, supplier, invoice,
  risk events) as a set. task_payloads_reviewed: the memo filename(s).

### B2 Multi-invoice AP release (train_005 / test_005 — packet with target_ids + chargeback register)

#### Inputs (from packet JSON)
- `review_as_of`, `target_ids{program_id, po_ids[], receipt_ids[], invoice_ids[]}`
  (sort all ID lists ascending).
- `chargeback_register_excerpt[]`: local, AUTHORITATIVE when provided. Each row:
  chargeback_id, invoice_id, po_id, receipt_id, reason_code, basis_quantity, unit_cost, status.
- `release_request_note[]`, `po73xx_alias_note` (supporting-only; see pitfalls).

#### Query recipe
1. For each invoice_id in packet: `GET /ap_invoices/<inv>` -> po_id, receipt_id,
   status, hold_code, total, lines.
2. For each po_id: `GET /purchase_orders/<po>` -> ordered qty, lines.
3. For each po_id: `GET /receipts?po_id=<po>` -> all receipts on the PO.
4. Cross-reference chargeback register by invoice_id to get chargeback per invoice:
   `chargeback_amount = basis_quantity * unit_cost`; status approved/pending_quality_review.

#### release_decisions (per invoice) — decision enum: release_net_after_approved_chargeback|hold_missing_receipt|hold_pending_quality_chargeback
- `receipt_ids_in_scope`: receipts on the invoice's PO that are (a) in the packet target
  receipt_ids AND (b) match the invoice (invoice.receipt_id if present, else the
  chargeback register's receipt_id for that invoice).
- `excluded_same_po_receipt_ids`: OTHER receipts on the same PO not in scope (e.g. a later
  receipt belonging to a different invoice). Must be within target receipt set or actual PO receipts.
- Decision logic:
  - `release_net_after_approved_chargeback`: chargeback status == approved AND a receipt
    is in scope. `primary_reason`: `approved_qty_chargeback` (reason Underage Quantity) or
    `approved_ap_quantity_variance` (reason AP Quantity Variance).
  - `hold_missing_receipt`: PO has ZERO receipts AND invoice.receipt_id null AND no
    chargeback mapping. `primary_reason`: `no_receipt_on_po`.
  - `hold_pending_quality_chargeback`: chargeback status == pending_quality_review OR
    receipt.status == inspection_hold. `primary_reason`: `inspection_hold_pending_chargeback`.
- `invoice_total` = invoice.total. `approved_chargeback_amount` = sum approved chargebacks
  for the invoice. `pending_chargeback_amount` = sum pending chargebacks.
- `net_release_amount`: for release decisions = invoice_total - approved_chargeback_amount;
  for hold decisions = 0 (nothing released now).

#### receiving_exceptions (per target receipt) — exception_codes (0+ of: Underage Quantity|Severe Unmatched Quantity|Inspection Hold|AP Quantity Variance)
- `Underage Quantity`: received < ordered (basis = ordered - received).
- `AP Quantity Variance`: billed > received (over-bill).
- `Severe Unmatched Quantity`: billed vastly exceeds received/ordered (use sparingly).
- `Inspection Hold`: receipt.status == inspection_hold.
- `chargeback_status`: approved | pending_quality_review | not_applicable (none in register).
- `resolution_status`: net_release_ready (approved chargeback) | hold_for_quality_review
  (pending/inspection_hold) | accepted_no_receiving_exception (full match, no chargeback)
  | missing_receipt (PO has no receipt).

#### summary
- `release_invoice_ids` / `hold_invoice_ids` from decisions (sorted asc).
- `approved_chargeback_total` / `pending_chargeback_total` = sums.
- `net_release_total` = sum of net_release_amount (held contribute 0).
- `authoritative_sources`: procureops_po_records | procureops_receipt_records |
  procureops_ap_records | local_chargeback_register (use all that apply).
- `supporting_only_sources`: ap_release_request_note | stale_po73xx_alias_note (NOT authoritative).
- `followup_actions` (allowed: ask_receiving_for_vantix_receipt |
  hold_luma_duplicate_receipt_for_separate_invoice | route_po00031_quality_review |
  post_approved_chargeback_netting): pick those matching the holds/missing/duplicate found.

### Pitfalls (Family B)
- In-scope invoice = the one whose receipt_id == batch_id (B1) or the chargeback-mapped
  receipt (B2). Do NOT aggregate all PO invoices into one batch review.
- `excluded_same_po_receipt_ids`: later receipts on the same PO for OTHER invoices must be
  listed as excluded, not folded in (e.g. RCV-00001 on PO-AX17-4481 belongs to AP-00001).
- Stale alias notes (PO-73xx): if the packet says exact IDs aren't in the shared API and
  gives replacement IDs (PO-00031/PO-00038), use those; never fabricate the aliased IDs.
  Mark the alias note as supporting_only_sources.
- Hold-code can be stale: an invoice may have hold_code NO_RECEIPT while invoice.receipt_id
  is populated (or a chargeback maps a receipt). Verify via receipt_id + chargeback register,
  not hold_code alone.
- Chargeback `basis_quantity` for Underage Quantity = ordered - received (not billed - received).
  For AP Quantity Variance = billed - received (the over-bill qty).
- contract_price_match compares BOTH po and invoice line prices to contract.unit_price.

---

## Family C — AP close / vendor-balance + hold/release (train_003 / test_002)

### Inputs (from memo)
- `close_date` (e.g. 2026-06-01) + target invoice list from memo.
- Memo may set opening balances (e.g. "treat May 31 opening AP balance as 0.00 USD" for
  the slice) and a payment cutoff (e.g. "scheduled through 2026-06-30"). Honor exactly.

### Query recipe (per target invoice)
1. `GET /ap_invoices/<inv>` -> po_id, supplier_id, receipt_id, status, hold_code, total, lines.
2. `GET /purchase_orders/<po_id>` -> ordered qty (PO line quantity) for variance%.
3. If invoice.receipt_id: `GET /receipts/<rcpt>` -> quantity_received; else received = 0.
4. `GET /payments?invoice_id=<inv>` -> payments (status, scheduled_date, amount); keep
   scheduled_date <= cutoff (2026-06-30) for scheduled_payment_amount.
5. `GET /suppliers/<sup>` -> name. `GET /programs/<po.program_id>` if needed.

### invoice_decisions (sort invoice_id asc)
- `hold_decision`: HOLD if (status == on_hold OR hold_code != null OR no receipt /
  hold_code == NO_RECEIPT); else RELEASE.
- `release_to_payment`: true iff hold_decision == RELEASE (approved/paid + 3-way match).
- `quantity_billed` (invoice line), `quantity_received` (0.00 if no receipt),
  `quantity_variance` = billed - received, `quantity_variance_pct` =
  (quantity_variance / PO_ordered_quantity) * 100, 1 dp. **Base is PO quantity, not received.**
- `invoice_total` = invoice.total. `scheduled_payment_amount` = sum of qualifying payment.amount.
- `net_balance_impact` = invoice_total - scheduled_payment_amount.
- `reason_codes` (alphabetical; allowed: APPROVED_THREE_WAY_MATCH|NO_RECEIPT|QTY_VARIANCE|SCHEDULED_PAYMENT_FOUND):
  - APPROVED_THREE_WAY_MATCH: status approved and PO+receipt+invoice agree on qty & price.
  - NO_RECEIPT: no receipt / hold_code NO_RECEIPT.
  - QTY_VARIANCE: hold_code QTY_VARIANCE OR billed != received.
  - SCHEDULED_PAYMENT_FOUND: a qualifying scheduled payment exists.

### vendor_balances (sort supplier_id asc) — one row per target supplier
- `opening_balance`: from memo (0.00 if slice says so).
- `invoice_total`: sum of target invoice totals for that supplier.
- `scheduled_payments`: sum of qualifying scheduled payments for that supplier's target invoices.
- `held_invoice_total`: sum of invoice totals where hold_decision == HOLD.
- `releasable_invoice_total`: sum where hold_decision == RELEASE.
- `close_balance` = opening_balance + invoice_total - scheduled_payments.
- `balance_status` (OPEN_HELD|OPEN_APPROVED|FULLY_SCHEDULED):
  - OPEN_HELD: held invoices, scheduled payments don't cover.
  - OPEN_APPROVED: approved but not yet scheduled.
  - FULLY_SCHEDULED: scheduled payments cover the invoice total.

### program_summary (sort program_id asc) — one row per program of target invoices
- `invoice_count`, `invoice_total`, `held_total` (HOLD invoices), `released_total`
  (RELEASE invoices), `net_close_balance` = invoice_total - scheduled_payments
  (equivalently sum of net_balance_impact for that program's invoices).

### queues & total
- `payment_hold_queue`: target invoice_ids with HOLD (sorted asc).
- `payment_release_queue`: target invoice_ids with RELEASE (sorted asc).
- `total_close_balance` = sum of vendor close_balances (= sum of net_balance_impacts,
  given opening 0). USD 2 dp.

### Pitfalls (Family C)
- quantity_variance_pct base = PO ordered quantity, NOT received or billed.
- Only consider payments for the TARGET invoices (close-slice), through the memo's cutoff.
- opening_balance comes from the memo (often 0 for the slice), not from any API field.
- A scheduled payment (status scheduled) counts even if not yet paid, as long as
  scheduled_date <= cutoff.
- balance_status: if a held invoice has no scheduled payment -> OPEN_HELD even if another
  released invoice is fully scheduled (per-supplier rollup of the SLICE).

---

## Family D — Change-control contract amendment (train_004 / test_005)

### Inputs (from change_memo.json)
- `program_id, contract_id, supplier_id, sku, variant_code, source_requisition_id,
  requested_incremental_quantity, requested_ship_to`.
- `business_controls`: currency, tax_rate_percent, contract_ceiling_exposure ("line
  subtotal before tax and freight"), budget_exposure ("line subtotal plus estimated tax;
  freight only if memo provides freight"), existing_contract_usage ("exclude cancelled
  purchase orders"), approval_good_actions (["approved"]), supplier_watch_rating
  ("context only unless an open severe event is found").

### Query recipe
1. `GET /contracts/<contract_id>` -> status, price_type, unit_price, ceiling_amount, sku.
   If contract.status != active OR contract.sku != memo sku -> decision reject_contract_mismatch.
2. `GET /purchase_orders?contract_id=<contract_id>` -> POs. Split into included
   (status != cancelled) and excluded_cancelled (status == cancelled).
3. `GET /budget_snapshots?program_id=<pg>` -> snapshot with snapshot_date <= memo_date.
4. `GET /approval_events?object_id=<source_requisition_id>` -> approval history; take
   the LATEST event (by event_date).
5. `GET /suppliers/<supplier_id>` -> status, risk_rating. `GET /vendor_risk_events?supplier_id=<sup>`
   -> open/monitoring events (severe = high|critical).

### contract_check
- `contract_status`, `price_type`, `unit_price`, `ceiling_amount` from contract.
- `noncancelled_subtotal` = sum of PO.subtotal (or sum line qty*unit_price) for INCLUDED
  (non-cancelled) POs on the contract.
- `headroom_before_change` = ceiling_amount - noncancelled_subtotal.
- `requested_quantity` = requested_incremental_quantity. `requested_subtotal` =
  requested_quantity * unit_price.
- `headroom_after_change` = headroom_before_change - requested_subtotal.
- `ceiling_ok` = headroom_after_change >= 0.

### program_budget_check
- `snapshot_id`, `budget_cap`, `committed_amount` from the as-of snapshot.
- `remaining_budget` = budget_cap - committed_amount.
- `requested_tax` = requested_subtotal * tax_rate_percent / 100 (2 dp).
- `requested_total` = requested_subtotal + requested_tax (+ freight ONLY if memo provides it).
- `budget_after_change` = remaining_budget - requested_total.
- `budget_ok` = budget_after_change >= 0.
- `max_quantity_with_current_budget` = floor(remaining_budget / (unit_price * (1 + tax_rate/100))).

### approval_check
- `source_requisition_id` from memo. `latest_event_id`, `latest_action`, `latest_actor`,
  `latest_event_date` from the latest approval_event (by event_date).
- `approval_ok` = latest_action is in approval_good_actions (["approved"]).
  "submitted"/"held"/"rejected" -> NOT ok.

### supplier_risk_check
- `supplier_status`, `supplier_risk_rating` from supplier.
- `open_event_ids` = vendor_risk_events with status in {open,monitoring} and
  event_date <= memo_date (sorted asc).
- `severe_open_event_ids` = subset with severity in {high, critical} (sorted asc).
- `supplier_risk_ok` = severe_open_event_ids is empty (watch/medium is context only).

### supporting_ids (all sorted asc)
- `included_po_ids`: non-cancelled POs on the contract.
- `excluded_cancelled_po_ids`: cancelled POs on the contract.
- `approval_event_ids`: all approval events for the source requisition.

### required_actions (sort asc; allowed: obtain_final_requisition_approval|raise_budget_exception_or_reduce_quantity|resolve_supplier_risk_hold|none)
- obtain_final_requisition_approval if approval_ok false.
- raise_budget_exception_or_reduce_quantity if budget_ok false.
- resolve_supplier_risk_hold if supplier_risk_ok false.
- ["none"] if all checks ok.

### decision (enum: release_amendment|hold_for_budget|hold_for_approval|hold_for_supplier_risk|hold_for_budget_and_approval|reject_contract_mismatch)
- reject_contract_mismatch if contract status inactive / sku mismatch.
- Combine failed checks: budget+approval -> hold_for_budget_and_approval; single fails
  -> the matching hold_for_*; none -> release_amendment.

### summary
- `blocker_count` = number of failed checks among {budget_ok, approval_ok,
  supplier_risk_ok} (+1 if contract_mismatch). `currency` = "USD".
  `ready_to_release` = (decision == release_amendment).

### Pitfalls (Family D)
- EXCLUDE cancelled POs from contract usage (noncancelled_subtotal). Including them
  overstates usage and wrongly fails ceiling_ok.
- remaining_budget = budget_cap - committed_amount (snapshot/program committed), NOT
  budget_cap - committed - pending_invoice. The pending_invoice field is a separate
  readiness signal, not part of the amendment budget baseline.
- requested_total = subtotal + estimated tax (rate from memo); add freight ONLY if the
  memo explicitly provides a freight value. Default no freight.
- max_quantity floor to integer (no fractional units).
- approval_ok requires the LATEST action to be "approved"; a "submitted" event (even with
  note_code EXPEDITE) does NOT satisfy approval.
- Only HIGH/CRITICAL open risk events block change-control (supplier_risk_ok). A medium
  open event sets context but does not block; watch rating alone does not block.
- contract ceiling exposure is subtotal (pre-tax, pre-freight); program budget exposure is
  subtotal + tax (+ freight if provided). Don't mix the two.

---

## Cross-cutting exclusion & misjudgment rules (all families)
1. **As-of date**: filter receipts (receipt_date), invoices (invoice_date), risk events
   (event_date), payments (scheduled_date) by <= the task's as_of/close_date/cutoff.
2. **Cancelled POs**: exclude from contract usage & committed totals (Family D). For
   evidence/po lists, follow the template; default to listing active POs for anchors.
3. **Invoice exception = on_hold or hold_code != null**: approved/paid invoices are never
   exceptions, even on the same PO.
4. **In-scope receipt per invoice/batch**: match by invoice.receipt_id (or chargeback
   mapping). Don't merge all PO receipts into one review; list other-PO receipts as excluded.
5. **Price anchor = contract.unit_price**: contract_price_match compares both PO and
   invoice line prices to it.
6. **Variance % base = PO ordered quantity** (Family C), not received/billed.
7. **Budget headroom vs readiness**: program-row headroom (budget_cap - committed_amount)
   is the headroom NUMBER; snapshot (committed + pending_invoice vs cap) is the readiness
   SIGNAL. Don't conflate.
8. **Stale aliases**: use the shared IDs the packet provides (PO-00031/PO-00038 for
   PO-73xx). Mark alias/request notes as supporting_only_sources, never authoritative.
9. **Chargeback register is authoritative when provided**: cross-reference by
   invoice_id/po_id/receipt_id; don't recompute chargebacks from the API alone.
10. **Stale hold_code**: an invoice may show hold_code NO_RECEIPT with a populated
    receipt_id — verify via receipt_id + chargeback register.
11. **Severe risk threshold**: only high/critical OPEN events block change-control and
    force `hold` in nomination. Medium/watch is context-only.
12. **Approval "good" action = approved only** (memo-specified). Use the LATEST event by date.
13. **Tax/freight in budget exposure**: subtotal + estimated tax (rate from memo); freight
    only if memo provides it. Ceiling exposure is subtotal only.
14. **Rounding**: USD 2 dp; qty 2 dp; ratio 4 dp; pct 1 dp; max_quantity floored to int.
    Match each template's stated unit per field (some want integer USD cents).
15. **Sorting**: list fields ascending by string unless "set"; committees/queues ascending.
16. **Endpoint aliases & params**: use the documented aliases; never pass
    _limit/page/per_page (returns 0). By-id returns the object; list returns {count,results}.

## Quick ID anchor参考 (do NOT hardcode; verify live)
- PRG-AX17 (Axis refresh line 17, owner Elena Marsh, budget_cap 285000, committed 216430.40).
- CR-LMP-228 (active, fixed, unit_price 84.5, ceiling 185000, SUP-LUMA, LMP-228).
- SUP-LUMA (LumaPro, risk_rating watch, NET30); SUP-VANTIX (Vantix Controls, low, NET45);
  SUP-HEXEL (Hexel Motion, medium, NET30).
- RCV-BLUE-14 (PO-AX17-4481, 216/240 LMP-228 received, accepted); RCV-00001 (later same PO,
  2026-06-08, excluded as-of 2026-06-01); RCV-GOLD-27 (PO-NOVA-3107, 180/180 SEN-NOVA);
  RCV-00017 (PO-00031, inspection_hold); RCV-00020 (PO-00038, accepted).
- Verify all IDs live before trusting; anchor refs are for orientation only.
