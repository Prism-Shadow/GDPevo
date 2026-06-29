---
name: reflect-3_attempt_03
description: SOP and business rules for solving ProcureOps ERP procurement/receiving/AP tasks against the read-only API, emitting answer.json that exactly matches each task template.
---

# ProcureOps ERP Solver Skill

You solve procurement / receiving / accounts-payable tasks in the ProcureOps ERP
domain. Each task gives you `input/prompt.txt`, one or more local payload files,
and `input/payloads/answer_template.json`. You must return a single JSON object
that matches that template exactly.

## 0. Golden rules (read first)

1. **The API is the source of truth.** Local payload memos/packets describe the
   business request and name the "anchors" (program/PO/receipt/invoice/contract
   IDs, watch sets, chargeback registers, tax rates, business-control flags).
   For any *record value* (quantity, price, status, date, supplier rating)
   defer to the live API record, never the memo's prose.
2. **The template is a contract.** Produce every required key, with the exact
   types, enum spellings, rounding, and ordering the template states. Do not add
   keys that are not requested; do not omit required keys.
3. **Copy enum strings verbatim** from the template's allowed list (e.g.
   `accept_partial_hold_variance`, `release_net_after_approved_chargeback`,
   `OPEN_HELD`). Case and underscores matter.
4. **Money rounded to cents** (2 decimals) unless a field says otherwise. Other
   precisions are stated per-field (e.g. ratio precision 4, variance pct 1).
5. **List fields are sets** the evaluator sorts, UNLESS the template gives a sort
   rule — then sort exactly as told (usually ascending by ID). When in doubt,
   sort ascending; it never hurts a set-compared field.
6. **Respect "as of" dates.** When a field says "as of as_of_date", filter
   records whose primary date is `<= as_of_date`. Receipts/invoices dated AFTER
   the as-of cutoff are out of scope even if they exist in the API.

## 1. Remote API

Base URL is given in `environment_access.md` (it REPLACES any localhost URL in
the prompt). It is read-only HTTP, GET only.

- `GET /manifest` — counts + anchor IDs (good sanity check).
- `GET /<collection>` -> `{"count":N,"results":[...]}`
- `GET /<collection>/<id>` -> single record (404 if absent)
- Filter with query params matching record fields (case-insensitive), e.g.
  `/receipts?po_id=PO-AX17-4481`, `/ap_invoices?program_id=PRG-AX17`.
- Date-window params `start`/`end` filter each collection's primary date field
  (receipts->receipt_date, ap_invoices->invoice_date, payments->scheduled_date,
  purchase_orders->order_date, contracts->effective_date, requisitions->need_by,
  approval_events->event_date, budget_snapshots->snapshot_date,
  vendor_risk_events->event_date).

Collections: `programs, suppliers, items, contracts, purchase_requisitions,
purchase_orders, receipts, ap_invoices, payments, approval_events,
budget_snapshots, vendor_risk_events`.

**Efficient workflow:** download all 12 collections once to local JSON, then
filter/join in a script (Python). Re-fetch only if you suspect staleness.

### Record shapes (key fields)
- program: program_id, owner, budget_cap, committed_amount, status, priority.
- supplier: supplier_id, name, risk_rating(low|medium|high|watch),
  status(active|quality_hold), payment_terms.
- item: sku, standard_cost, preferred_supplier_id.
- contract: contract_id, sku, supplier_id, program_id, status(active|draft|expired),
  price_type(fixed|indexed|not_to_exceed), unit_price, ceiling_amount, dates.
- purchase_requisition: requisition_id, sku, program_id, quantity, need_by,
  status(draft|approved|converted|cancelled).
- purchase_order: po_id, contract_id(may be null), program_id, supplier_id,
  requisition_id, status(open|confirmed|partial_receipt|received|closed|cancelled),
  lines[{line_id,sku,quantity,unit_price}], subtotal, tax, total, due_date.
- receipt: receipt_id, po_id, supplier_id, warehouse_id, receipt_date, receiver,
  packing_slip, status(accepted|accepted_with_note|inspection_hold),
  lines[{po_line_id,sku,quantity_received,quantity_rejected,inspection_status}].
- ap_invoice: invoice_id, po_id, receipt_id(may be null), supplier_id,
  status(entered|pending_receipt|on_hold|approved|paid),
  hold_code(null|NO_RECEIPT|QTY_VARIANCE|PRICE_VARIANCE|SUPPLIER_REVIEW),
  lines[{po_line_id,sku,quantity_billed,unit_price}], subtotal, freight, tax, total.
- payment: payment_id, invoice_id, supplier_id, amount, scheduled_date,
  status(scheduled|released|blocked).
- approval_event: event_id, object_id, object_type, action(submitted|approved|
  returned|escalated), actor, event_date, note_code.
- budget_snapshot: snapshot_id, program_id, budget_cap, committed_amount,
  pending_invoice_amount, snapshot_date.
- vendor_risk_event: event_id, supplier_id, related_object_id,
  event_type(bank_change|invoice_variance|quality_hold|late_delivery|
  duplicate_invoice_review), severity(low|medium|high), status(open|monitoring|closed).

## 2. Core business rules (transferable)

### Three-way match (PO vs Receipt vs Invoice)
For each PO line, match `quantity` (ordered), `quantity_received` (receipt), and
`quantity_billed` (invoice).
- `short_qty_vs_po = ordered - received`.
- `unreceived_billed_qty = max(billed - received, 0)`.
- `receipt_completion_ratio = received / ordered` (watch precision).
- A clean three-way match = billed == received == ordered, prices consistent, no
  rejection -> invoice is releasable.

### AP invoice release vs hold
- **RELEASE** only when invoice `status == "approved"` AND `hold_code` is null
  (and the three-way match is clean / any variance has an approved disposition).
- **HOLD** for any of: `status` in {on_hold, pending_receipt, entered, disputed},
  a non-null `hold_code`, billed > received (qty variance), no receipt where one
  is required, price mismatch, or an unresolved supplier review.
- Map hold reasons to the template's reason/exception enums. Typical hold codes:
  `NO_RECEIPT`, `QTY_VARIANCE`, `PRICE_VARIANCE`, `SUPPLIER_REVIEW`.

### Quantity variance / NO_RECEIPT mutual exclusion (IMPORTANT)
When an invoice has **no receipt** (`receipt_id` null and no receipt on the PO),
emit only the NO_RECEIPT-style reason. **Do NOT also emit a QTY_VARIANCE-style
code** in that case — you cannot compute a real quantity variance without a
receipt to compare against. Quantity-variance codes apply only when a receipt
exists and `billed != received`. (This single exclusion was the difference
between partial and full credit on a close task.)

### Duplicate invoice / duplicate receipt handling
- A PO can have multiple receipts. An invoice usually references ONE receipt
  (`receipt_id`). Receipts on the same PO that the invoice does NOT reference are
  "excluded same-PO receipts" — list them in the excluded field, not the in-scope
  field. A second/duplicate receipt for the same PO is typically held for a
  separate invoice, not netted into the current one.
- `duplicate_invoice_review` risk events and SUPPLIER_REVIEW holds flag possible
  duplicates; keep such invoices on hold.

### Chargeback netting (receiving exceptions feeding AP)
When a local chargeback register is provided:
- chargeback amount = `basis_quantity * unit_cost` (round to cents).
- **approved** chargeback -> net it against the invoice:
  `net_release_amount = invoice_total - approved_chargeback`, decision = release
  net after approved chargeback.
- **pending/under-review** chargeback -> HOLD the invoice (net release 0),
  decision = hold pending quality chargeback; this pairs with a receipt whose
  status is `inspection_hold`.
- An invoice with no receipt and no receipt on its PO -> HOLD missing receipt
  (net 0), follow-up = ask receiving for the missing receipt.
- Totals: approved_chargeback_total and pending_chargeback_total are summed
  separately; net_release_total sums only the released invoices' net amounts.

### Receiving exception classification
- Receipt `inspection_status`/receipt `status == inspection_hold` -> Inspection
  Hold code; route to quality review; resolution = hold for quality review.
- Short receipt (received < ordered): moderate shortfall -> "Underage Quantity";
  large shortfall (roughly a third or more of ordered qty missing) -> "Severe
  Unmatched Quantity". Use the receipt's own observed gap, which can differ from
  the chargeback register's label.
- `quantity_rejected > 0` -> damage/rejection exception; consider supplier debit.
- Bill > receipt with full physical receipt -> "AP Quantity Variance".
- Create receiving-exception rows for ACTUAL receipts; a missing-receipt
  situation is represented in the release/hold decision, not as a phantom
  receiving row with a blank receipt id.

### Sourcing nomination gates
Classify each line by blockers, then map to decision/readiness:
- **Hard gate -> hold / not_ready**: missing/absent commercial basis
  (no active contract for the sku AND PO `contract_id` is null). `commercial_basis_id`
  is the PO's contract_id, else the matching active contract, else null.
- **Soft conditions -> conditional_nomination / at_risk**: supplier on `watch`,
  an open/monitoring supplier-risk event, an AP hold on the package invoice, a
  partial/pending receipt. These are "clear-before-release" conditions, not hard
  rejections.
- **No blockers -> nominate / ready.**
- Roll up `overall_readiness`: not_ready if any line not_ready; else at_risk if
  any at_risk; else ready.
- Committee buckets group supplier_ids by their line decision. A line missing a
  contract routes next work to the **buyer** (buyers source contracts), not the
  program owner.
- blocker_codes are a sorted set from the template's allowed list
  (e.g. missing_contract, supplier_watch, open_supplier_risk, ap_hold,
  pending_receipt, late_due_date, none). Use `none` only when there are zero
  blockers. `late_due_date` only when a due/need-by date is already past the
  as-of date.

### Contract price consistency & headroom
- `contract_unit_price` from the active contract for the sku; PO and invoice unit
  prices should match it. `contract_price_match = (invoice_unit_price == contract
  unit_price)` within a cent.
- **Contract ceiling headroom**: `ceiling_amount - sum(subtotal of non-cancelled
  POs on the contract)`. **Always exclude `cancelled` POs** from contract usage.
  `headroom_after_change = headroom_before - requested_subtotal`
  (requested_subtotal = requested_qty * contract unit_price, before tax/freight).
  `ceiling_ok = headroom_after >= 0`.

### Program budget headroom
- `remaining_budget = budget_cap - committed_amount` (from program or
  budget_snapshot; prefer the snapshot the task names).
- Budget exposure of a change = subtotal + tax (tax = subtotal * tax_rate);
  add freight only if the memo provides freight.
- `budget_after_change = remaining_budget - requested_total`;
  `budget_ok = budget_after_change >= 0`.
- `max_quantity_with_current_budget = floor(remaining_budget /
  (unit_price * (1 + tax_rate)))`.

### Approval gate
- Find approval_events for the source requisition (object_id == requisition_id);
  take the LATEST by event_date (tie-break event_id). `approval_ok` is true only
  when the latest action is an approved/"good" action (per the memo, usually
  exactly `approved`). `submitted`, `returned`, `escalated` are NOT approved.

### Supplier-risk policy
- `open_event_ids` = supplier's vendor_risk_events with status in
  {open, monitoring} (supplier-wide, not just this PO), sorted ascending.
- `severe_open_event_ids` = those with severity in {high, critical} (and
  "severe" if present). A `watch` rating or a medium open event is **context
  only** — it does not by itself block a release.
- `supplier_risk_ok = (no severe open events)`. Supplier `status ==
  quality_hold` is a hard supplier block.

### Composite decision from gates
When a task asks for one overall decision from multiple gates, compose it from
the failing gates, e.g.: contract ceiling fail -> reject/contract mismatch;
else supplier-risk severe -> hold for supplier risk; else budget AND approval
both fail -> hold for budget and approval; else budget only / approval only ->
the single hold; else release. `blocker_count` = number of failed gates;
`ready_to_release = (decision == release)`. `required_actions` is a sorted set
mapping each failed gate to its remediation enum; use `none` only when no gate
failed.

## 3. Output conventions checklist
- Set `task_id` to the exact value the template requires (often `train_00X`/the
  task-group id literally shown in the template — copy it).
- Numbers: USD to cents; ratios/percentages to the stated precision; integers
  stay integers (qty fields).
- Booleans are real JSON booleans, not strings.
- `null` where the template allows null (e.g. `commercial_basis_id`, `hold_code`).
- Sort every list the template tells you to sort (ascending by ID is the default
  rule); leave set fields as plain arrays (the evaluator sorts them) but sorting
  them anyway is safe.
- Use 0.00 (not null) for "received quantity when no receipt exists" and similar
  "use 0" instructions.
- Evidence/source lists: include the record IDs you actually used (PO, receipt,
  invoice, contract, supplier, open-risk events). For "sources" enum fields,
  separate authoritative (procureops_* records, local registers that drive
  numbers) from supporting-only (advisory notes, stale/alias notes).

## 4. Step-by-step SOP for any task
1. Read prompt.txt + every payload file. Note: target IDs, as-of/close/review
   date, business-control flags (tax rate, "exclude cancelled", "approved =
   good", opening balance, pay-through date), and which sources are advisory.
2. Read answer_template.json end to end. List every required key, its type,
   enum domain, rounding, and ordering. This defines your output exactly.
3. Pull the needed records from the API (filter by program_id/po_id/etc.).
   Cross-check memo anchors against live records; trust the API on values.
4. Apply the relevant rules from section 2 (three-way match, hold/release,
   chargeback netting, gates, headroom, risk). Apply as-of date filtering.
5. Compute money to cents, derive variances/ratios at stated precision.
6. Assemble JSON exactly to template: correct keys, verbatim enums, sorted
   lists, real booleans/nulls, exact task_id.
7. Self-review against the template field list before returning. Re-verify any
   exclusion rules (cancelled POs excluded; NO_RECEIPT suppresses QTY_VARIANCE;
   out-of-scope/after-as-of receipts excluded; duplicate same-PO receipts moved
   to the excluded list).

## 5. Common misjudgments to avoid
- Including cancelled POs in contract/budget usage. Exclude them.
- Emitting both NO_RECEIPT and a quantity-variance code for the same invoice.
- Treating a `watch` rating or a medium/open (non-severe) risk event as a hard
  block — it is context only; only severe open events / quality_hold status block.
- Counting receipts or invoices dated after the as-of cutoff.
- Netting a duplicate same-PO receipt into the current invoice instead of
  excluding it / holding it for its own invoice.
- Using the memo's stated numbers when the API record differs.
- Routing a missing-contract nomination to the program owner instead of the buyer.
- Wrong rounding/precision, stringified booleans, or paraphrased enum values.
- Adding extra keys or phantom list rows the template did not ask for.
