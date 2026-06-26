---
name: self_attempt_01
description: SOPs and business rules for solving ProcureOps procurement/receiving/AP tasks (nomination gates, three-way match, AP hold/release, chargeback netting) against the live read-only ERP API.
---

# ProcureOps Procurement / Receiving / AP Solver Skill

This skill helps you answer ProcureOps ERP tasks: sourcing-nomination readiness,
inbound receiving closeout, three-way match, AP invoice hold/release, vendor-balance
close, contract/budget change-control, and chargeback netting. The same data model
and rules recur across tasks; learn them once and apply them to unseen prompts.

---

## 0. Golden rules (read first)

1. **The remote API is the source of truth.** Local payload/memo/export files only
   name the *anchors* (target programs, POs, receipts, invoices, watch-set IDs) and
   describe the business request. Whenever a number in a memo/export disagrees with
   the API record, USE THE API VALUE. Never copy dollar amounts, quantities, statuses,
   or prices out of a memo as the answer — re-derive them from API records.
2. **Output must match the task's `answer_template.json` EXACTLY**: same top-level keys,
   same nested keys, same list-element schema, same enum spellings. Do not add or drop
   keys. Do not rename. Return ONLY the JSON object, no prose.
3. **Copy enum strings verbatim** from the template's `allowed_values`. They are
   case- and underscore-sensitive (e.g. `release_full_invoice`, `keep_invoice_on_hold`,
   `APPROVED_THREE_WAY_MATCH`, `hold_for_budget_and_approval`).
4. **Rounding:** USD amounts to cents (2 dp). Ratios/percentages to the precision the
   template states (e.g. `receipt_completion_ratio` precision 4; `quantity_variance_pct`
   1 dp). Quantities are integers.
5. **List fields are SETS** unless the template gives a sort rule. When a sort is
   stated ("sorted ascending", "invoice_id ascending", "sort IDs ascending"), output a
   sorted list. When it says "set; evaluator sorts values", order does not matter but
   still emit clean unique values.
6. **Respect the as-of / review date.** Most tasks have an as-of date (in the prompt,
   memo, or template field). Records dated AFTER the as-of date are OUT of scope. This
   is a frequent trap: a later receipt or invoice exists in the API but must be ignored
   because it postdates the cutoff.
7. **Use the exact IDs the local packet names** for scope. The task tells you which POs/
   receipts/invoices/suppliers are in scope. Do not pull the whole collection into the
   answer; reconcile only the named scope (plus their directly related records).

---

## 1. Remote API usage

Base URL (overrides any `127.0.0.1:8006` / `localhost` in the prompt):

    <remote-env-url>

GET-only. Patterns:

    curl -s <remote-env-url>manifest
    curl -s <remote-env-url><collection>            # {"count":N,"results":[...]}
    curl -s <remote-env-url><collection>/<id>       # single object, 404 if absent
    curl -s "<remote-env-url>receipts?po_id=PO-AX17-4481"

Collections: `programs`, `suppliers`, `items`, `contracts`,
`purchase_requisitions`, `purchase_orders`, `receipts`, `ap_invoices`,
`payments`, `approval_events`, `budget_snapshots`, `vendor_risk_events`.

### Filtering tips (learned)
- Filter by any record field, case-insensitive: `?po_id=`, `?supplier_id=`,
  `?program_id=`, `?contract_id=`, `?invoice_id=`.
- **`approval_events` is keyed by `object_id`, NOT `requisition_id`.** Use
  `?object_id=REQ-...`. Each event has `action` (submitted/approved/returned/...),
  `actor`, `event_date`, `note_code`, `object_type`.
- **`payments` filter by `?invoice_id=`.** A scheduled/released payment for an invoice
  reduces the close balance. `status` can be `scheduled` or `released`.
- Date windows: `?start=YYYY-MM-DD&end=YYYY-MM-DD` filter the collection's primary date
  field (receipts->receipt_date, ap_invoices->invoice_date, payments->scheduled_date,
  purchase_orders->order_date, contracts->effective_date, requisitions->need_by,
  approval_events->event_date, budget_snapshots->snapshot_date, vendor_risk_events->event_date).
  You can also just pull all related records and filter on date yourself.
- Always pull *all* receipts/invoices for a PO (`?po_id=`) — there are often multiple,
  and you must decide which are in scope by date and by the receipt_id the invoice cites.

### Record fields you will use (observed shapes)
- **programs**: program_id, name, owner, status, priority, budget_cap, committed_amount,
  cost_center, region.
- **suppliers**: supplier_id, name, status (active/...), risk_rating
  (low/medium/watch/high), payment_terms, region.
- **items**: sku, standard_cost, preferred_supplier_id, category, uom, active.
- **contracts**: contract_id, supplier_id, program_id, sku, status (active/...),
  price_type (fixed/...), unit_price, ceiling_amount, effective_date, expiry_date.
- **purchase_requisitions**: requisition_id, program_id, sku, quantity, need_by,
  priority, requester, status (approved/converted/...).
- **purchase_orders**: po_id, program_id, supplier_id, contract_id (may be null),
  requisition_id, status (open/confirmed/partial_receipt/received/closed/cancelled),
  order_date, due_date, ship_to, lines[{line_id, sku, quantity, unit_price, description}],
  subtotal, tax, total.
- **receipts**: receipt_id, po_id, supplier_id, warehouse_id, receipt_date, packing_slip,
  receiver, status (accepted/accepted_with_note/inspection_hold/...),
  lines[{po_line_id, sku, quantity_received, quantity_rejected, inspection_status}].
- **ap_invoices**: invoice_id, po_id, supplier_id, receipt_id (may be null), invoice_date,
  status (approved/on_hold/pending_receipt/paid/...), hold_code
  (null/QTY_VARIANCE/PRICE_VARIANCE/NO_RECEIPT/...), subtotal, freight, tax, total,
  lines[{po_line_id, sku, quantity_billed, unit_price}].
- **payments**: payment_id, invoice_id, supplier_id, amount, scheduled_date,
  status (scheduled/released).
- **approval_events**: event_id, object_id, object_type, action, actor, event_date, note_code.
- **budget_snapshots**: snapshot_id, program_id, budget_cap, committed_amount,
  pending_invoice_amount, snapshot_date, currency.
- **vendor_risk_events**: event_id, supplier_id, event_type, severity (low/medium/high/...),
  status (open/monitoring/closed), event_date, related_object_id.

---

## 2. Core business rules (transferable)

### 2.1 Three-way match (PO ↔ Receipt ↔ Invoice)
For a PO line, compare:
- ordered_qty = PO line.quantity
- received_qty = sum of receipt line.quantity_received for receipts IN SCOPE
- rejected_qty = sum of receipt line.quantity_rejected
- billed_qty   = invoice line.quantity_billed
Derived:
- short_qty_vs_po       = ordered_qty − received_qty
- unreceived_billed_qty = max(0, billed_qty − received_qty)  (billed beyond receipt)
- receipt_completion_ratio = received_qty / ordered_qty
A clean match (received == ordered == billed, no rejects, prices equal, no risk) →
`APPROVED_THREE_WAY_MATCH` / no exception.

### 2.2 Receiving exceptions (what each condition means)
- billed_qty > received_qty            -> INVOICE_QTY_EXCEEDS_RECEIPT / AP Quantity Variance
- received_qty < ordered_qty (partial) -> PARTIAL_RECEIPT / Underage Quantity
- receipt status `inspection_hold`     -> Inspection Hold (blocks release pending quality)
- quantity_rejected > 0 (damage)       -> DAMAGE_REJECTION
- supplier risk_rating == watch        -> SUPPLIER_WATCH_RISK
- invoice unit_price != contract/PO    -> PRICE_MISMATCH / PRICE_VARIANCE
- none of the above                    -> NO_EXCEPTION

### 2.3 Contract price consistency
Compare invoice line `unit_price` against the active contract `unit_price` for that
sku/supplier (and against PO line unit_price). `contract_price_match` is TRUE only when
invoice price equals the contract price (within cents). If the PO has `contract_id: null`,
there is no contract to match against — treat as `missing_contract` and there is no
contract price (decide per template: null or PO price; prefer null/contract-absent
handling that the template implies).

### 2.4 AP invoice hold vs release
Hold/release is driven by the invoice's own `status`/`hold_code` AND the match:
- `status == approved` and no hold_code and three-way clean and (payment scheduled if the
  task ties release to payment) -> RELEASE.
- `status == on_hold` (hold_code like QTY_VARIANCE / PRICE_VARIANCE) -> HOLD.
- `status == pending_receipt` or `hold_code == NO_RECEIPT` or `receipt_id == null` and no
  in-scope receipt -> HOLD (missing receipt). Never release an invoice with no receipt.
- `status == paid` -> already settled (out of the open close population unless asked).
Map to the template enums for the specific task (e.g. `HOLD`/`RELEASE`, or
`keep_invoice_on_hold`/`release_invoice`, or `release_full_invoice`/
`accept_partial_hold_variance`).

### 2.5 Quantity / variance reconciliation
- quantity_variance = quantity_billed − quantity_received (use received 0.00 if no receipt).
- quantity_variance_pct = variance / PO quantity * 100 (template said "percentage of PO
  quantity"), rounded to 1 dp. (Read each template — it states the denominator.)

### 2.6 Vendor / supplier-balance close
- opening_balance: use the value the memo states (often 0.00 for a close slice).
- close_balance = opening_balance + invoice_total − scheduled_payments.
- A payment that is scheduled/released within the stated window reduces the balance and
  flips the invoice toward "scheduled". balance_status enums map: held invoices ->
  OPEN_HELD; approved but unpaid -> OPEN_APPROVED; fully paid/scheduled -> FULLY_SCHEDULED.
- Reason codes are controlled enums: emit codes (e.g. APPROVED_THREE_WAY_MATCH, NO_RECEIPT,
  QTY_VARIANCE, SCHEDULED_PAYMENT_FOUND) sorted as the template requires, not prose.

### 2.7 Contract & budget headroom (change-control)
- noncancelled_subtotal = sum of line subtotals for all POs on the contract whose status
  is NOT `cancelled`. **Always exclude cancelled POs** from contract usage.
- headroom_before_change = ceiling_amount − noncancelled_subtotal.
- requested_subtotal = requested_qty × contract unit_price (subtotal basis, before tax/freight).
- headroom_after_change = ceiling_amount − noncancelled_subtotal − requested_subtotal.
- ceiling_ok = (noncancelled_subtotal + requested_subtotal) <= ceiling_amount.
- Budget: from the program's budget_snapshot. remaining_budget = budget_cap − committed_amount.
- requested_tax = requested_subtotal × tax_rate (memo gives the rate, e.g. 7.25%).
  requested_total = requested_subtotal + requested_tax (+ freight only if the memo provides freight).
- budget_after_change = remaining_budget − requested_total. budget_ok = requested_total <= remaining_budget.
- max_quantity_with_current_budget = floor(remaining_budget / (unit_price × (1 + tax_rate))).
- Contract-exposure basis is subtotal-only (no tax/freight); budget-exposure basis
  includes tax (and freight only if supplied). Read the memo's `business_controls`.

### 2.8 Approval gate
A requisition/change is "approved" only if its latest/relevant `approval_events` record
has `action == approved` (the memo lists "approval_good_actions", usually just `approved`).
`submitted`/`returned`/`pending` is NOT approved. Pull events with `?object_id=REQ-...`,
read latest by `event_date`. Report latest_event_id, latest_action, latest_actor,
latest_event_date, approval_ok.

### 2.9 Supplier-risk policy
- Open / monitoring vendor_risk_events count as active risk; `closed` events do NOT.
  Filter `?supplier_id=` then keep status in {open, monitoring}.
- supplier_risk_ok is FALSE when there is a SEVERE open event (severity high/critical) —
  a `watch` rating alone is context-only unless an open severe event exists (per memos).
- supplier_watch blocker triggers when supplier.risk_rating == `watch`.
- severe_open_event_ids = open events with high/critical severity; sort ascending.

### 2.10 Chargeback netting (AP release with chargebacks)
- A local chargeback register lists chargeback_id, invoice_id, po_id, receipt_id,
  reason_code, basis_quantity, unit_cost, status.
- chargeback_amount = basis_quantity × unit_cost.
- status `approved`  -> nets the invoice now: net_release_amount = invoice_total − approved_chargeback,
  decision `release_net_after_approved_chargeback`.
- status `pending_quality_review` (or the related receipt is `inspection_hold`) -> do NOT
  release; decision `hold_pending_quality_chargeback`, primary_reason
  `inspection_hold_pending_chargeback`; the pending amount goes to pending_chargeback_total.
- primary_reason mapping by reason_code: "Underage Quantity" -> approved_qty_chargeback;
  "AP Quantity Variance" -> approved_ap_quantity_variance; no receipt -> no_receipt_on_po;
  inspection-hold/pending -> inspection_hold_pending_chargeback.
- The register is "local_chargeback_register" (authoritative for chargebacks); PO/receipt/
  AP records are authoritative ERP sources; the request note / stale-alias note are
  supporting-only.

---

## 3. Scope inclusion / exclusion rules (common misjudgments)

- **Receipt scope for an invoice closeout:** include only the receipt(s) the task names
  as the batch under review and/or the receipt_id the invoice cites. A PO can have
  MULTIPLE receipts; a second receipt on the same PO that belongs to a different invoice
  must be EXCLUDED (record it in `excluded_same_po_receipt_ids` when the template asks).
- **As-of date exclusion:** drop receipts/invoices dated after the as-of/review date even
  though they exist in the API. (E.g. a receipt dated after the cutoff is not evidence yet.)
- **Cancelled POs:** excluded from contract usage / headroom math (list them in
  `excluded_cancelled_po_ids` when asked).
- **Closed risk events:** excluded from open-risk lists.
- **Status that BLOCKS vs only NOTES:** `inspection_hold` and `NO_RECEIPT`/no-receipt BLOCK
  a release. `accepted_with_note` and a supplier `watch` rating typically only NOTE (add an
  exception/blocker code) but do not by themselves void; follow the template's decision enums.
- **Missing receipt = hold, always.** An invoice with receipt_id null and no in-scope
  receipt cannot be released; emit the missing-receipt hold/decision and a follow-up action
  (e.g. ask receiving for the missing receipt).
- **Do not invent IDs.** If the packet says certain generated PO-73xx-style IDs are not in
  the shared API, use only the available shared IDs the packet lists; record the alias note
  as supporting-only.

---

## 4. Nomination readiness (sourcing) SOP

For each package line (sku + its primary requisition + package PO):
1. selected_supplier_id = the PO's supplier (or item.preferred_supplier_id).
2. Gather: requisition (approval state), PO (status, contract_id), contract (exists &
   active & price match), in-scope receipts, in-scope invoice exceptions (on_hold/
   pending_receipt with hold_code), open/monitoring risk events, supplier risk_rating.
3. Compute blocker_codes (sorted ascending), from this controlled set:
   - missing_contract   : PO.contract_id is null / no active contract for sku.
   - supplier_watch     : supplier.risk_rating == watch.
   - open_supplier_risk : >=1 open/monitoring vendor_risk_event for the supplier as of as_of.
   - ap_hold            : an in-scope invoice on_hold / pending_receipt / hold_code set.
   - pending_receipt    : not fully received as of as_of (received < ordered) / no receipt.
   - late_due_date      : PO due_date / requisition need_by past as_of with line not received.
   - none               : no blockers.
4. readiness_status: ready (no blockers) / at_risk (soft blockers, e.g. watch only) /
   not_ready (hard blockers: missing_contract, open_supplier_risk, ap_hold, pending_receipt).
5. nomination_decision: nominate (ready) / conditional_nomination (clearable soft issues) /
   hold (hard blockers). Bucket suppliers into nominate_now / conditional / hold.
6. overall_readiness and committee send_to_committee follow from the line decisions
   (any hold -> not_ready; mixed -> at_risk; all ready -> ready). next_owner per the team
   that must clear the dominant blocker (buyer/finance_ops/quality_ops/program_owner/ap_team).
7. budget_headroom_usd = program.budget_cap − program.committed_amount (or from the
   budget_snapshot). Round to cents.

---

## 5. Step-by-step SOP for any task

1. Read prompt.txt + every file in input/payloads/ (memo + answer_template.json). Identify:
   the as-of/review date, the in-scope IDs, the tax rate / opening-balance conventions, and
   the exact output schema + enums.
2. Hit `/manifest` to confirm anchors and seed. Then pull each in-scope record by ID and by
   `?po_id=`/`?supplier_id=`/`?invoice_id=`/`?object_id=` to get all related rows.
3. Reconcile per the rules in section 2; apply scope exclusions in section 3.
4. Do all arithmetic from API values; round per template precision.
5. Build the JSON to match the template key-for-key. Sort lists where required; treat others
   as sets. Copy enum strings verbatim. Include any required literal field values (e.g.
   `task_id` "train_00X" / the exact required_value the template gives) and evidence/source
   ID lists.
6. Self-check: every template key present? enums spelled exactly? amounts at cents? dates
   YYYY-MM-DD? lists sorted where stated? no out-of-scope/cancelled/closed/after-cutoff
   records leaked in? Return ONLY the JSON object.

---

## 6. Worked patterns observed (mechanics, not answers)

- Three-way mismatch with partial receipt + billed>received + supplier watch -> invoice
  stays on hold; receiving records a shortage follow-up; supplier action is request
  credit / remaining delivery; financials split received vs unreceived goods value at the
  PO/contract unit price.
- AP close slice: opening 0; approved invoice with a scheduled payment in-window -> RELEASE,
  net balance impact 0 (invoice_total − scheduled_payment); held/no-receipt invoices ->
  HOLD, full balance impact; program totals are per-program sums; total_close_balance is the
  sum of close balances.
- Change-control: ceiling may pass while budget fails (or vice versa); decision combines
  both (e.g. hold_for_budget vs hold_for_budget_and_approval). max_quantity uses tax-grossed
  unit cost and floors. Exclude cancelled POs from usage.
- AP release with chargebacks: approved chargebacks net immediately; pending/inspection-hold
  chargebacks force a hold; missing-receipt invoices hold; sum approved vs pending vs net
  totals; classify sources as authoritative vs supporting-only; emit concrete follow-ups.

Apply the rules, not the memos' numbers. The API wins every time.
