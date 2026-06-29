---
name: self_attempt_03
description: SOP and business rules for solving ProcureOps ERP procurement/receiving/AP tasks (nomination, three-way match, AP hold/release, change control) using the live read-only API as source of truth.
---

# ProcureOps ERP Solver Skill

You solve procurement / receiving / accounts-payable (AP) tasks against a read-only
ProcureOps ERP API. Each task gives you a `prompt.txt`, a local memo/packet payload,
and an `answer_template.json`. You must return ONE JSON object that matches the
template exactly. There is no answer key — derive every number/decision from the live
API and the rules below.

---

## 0. THE API IS SOURCE OF TRUTH

Base URL (overrides any `127.0.0.1:8006` / `localhost` in the prompt):

    <remote-env-url>

- `GET /<collection>` -> `{"count": N, "results": [...]}`
- `GET /<collection>/<id>` -> single object (404 if missing)
- Collections: `programs`, `suppliers`, `items`, `contracts`,
  `purchase_requisitions`, `purchase_orders`, `receipts`, `ap_invoices`,
  `payments`, `approval_events`, `budget_snapshots`, `vendor_risk_events`.
- Filter by any record field (case-insensitive), e.g.
  `GET /receipts?po_id=PO-AX17-4481`, `GET /ap_invoices?supplier_id=SUP-LUMA`.
- Date filters `start`/`end` apply to each collection's primary date field
  (receipts->receipt_date, ap_invoices->invoice_date, payments->scheduled_date,
  purchase_orders->order_date, contracts->effective_date,
  purchase_requisitions->need_by, approval_events->event_date,
  budget_snapshots->snapshot_date, vendor_risk_events->event_date).
  `end=<as_of_date>` keeps records on/before that date (verified: it drops
  future-dated events). Use this for any "as of <date>" requirement.

RULE: Local payload files (memo.md, packet.json, chargeback registers, export
values) describe the *business request / watch set* (which IDs to look at, what
opening balances to assume, business-control flags). They DO NOT override ERP
record values. If a payload's number disagrees with the API record, use the API.
Exception: a payload may legitimately *supply* data that is not in the ERP at all
(e.g. a `chargeback_register_excerpt`, an assumed `opening_balance`, a tax_rate) —
use those as given because they are inputs, not overrides.

---

## 1. RECORD SHAPES (field names that bite you)

- **programs**: program_id, name, owner, budget_cap, committed_amount,
  cost_center, priority, region, status.
- **suppliers**: supplier_id, name, payment_terms, region, risk_rating
  (`low|medium|watch|high`...), status (`active`...).
- **items**: sku, description, standard_cost, preferred_supplier_id, category, uom, active.
- **contracts**: contract_id, supplier_id, sku, program_id, price_type
  (`fixed`...), unit_price, ceiling_amount, status (`active|draft|...`),
  effective_date, expiry_date, buyer.
- **purchase_orders**: po_id, program_id, supplier_id, contract_id (MAY BE null),
  requisition_id, status (`open|confirmed|partial_receipt|received|closed|cancelled`),
  order_date, due_date, ship_to, currency, subtotal, tax, total,
  lines:[{line_id, sku, quantity, unit_price, description}].
- **purchase_requisitions**: requisition_id, program_id, sku, quantity, requester,
  priority, need_by, status (`converted|approved|...`).
- **receipts**: receipt_id, po_id, supplier_id, warehouse_id, receipt_date,
  packing_slip, receiver, status (`accepted|accepted_with_note|inspection_hold|...`),
  lines:[{po_line_id, sku, quantity_received, quantity_rejected, inspection_status}].
- **ap_invoices**: invoice_id, po_id, supplier_id, receipt_id (MAY BE null),
  invoice_date, status (`approved|on_hold|pending_receipt|paid|...`),
  hold_code (`QTY_VARIANCE|NO_RECEIPT|null|...`), subtotal, freight, tax, total,
  lines:[{po_line_id, sku, quantity_billed, unit_price}].
- **payments**: payment_id, invoice_id, supplier_id, amount, scheduled_date,
  status (`scheduled|paid|...`).
- **approval_events**: event_id, object_id, object_type (`requisition`...), action
  (`submitted|approved|rejected|...`), actor, event_date, note_code.
  ⚠ KEY: filter by `object_id=REQ-...`, NOT `requisition_id`. (`?requisition_id=`
  returns 0 results.)
- **budget_snapshots**: snapshot_id (e.g. `BUD-PRG-AX17`), program_id, budget_cap,
  committed_amount, pending_invoice_amount, currency, snapshot_date.
- **vendor_risk_events**: event_id, supplier_id, related_object_id, event_type
  (`bank_change|invoice_variance|quality_hold|late_delivery|...`), severity
  (`low|medium|high|critical`), status (`open|monitoring|closed`), event_date.

---

## 2. CORE BUSINESS RULES (transferable)

### 2.1 Three-way match (PO ↔ Receipt ↔ Invoice)
Match on po_id + po_line_id + sku. For each line:
- ordered_qty = PO line.quantity
- received_qty = sum of receipt line.quantity_received **for the batch/scope in
  question** (see 2.7 scoping). 0 if no receipt.
- rejected_qty = receipt line.quantity_rejected
- billed_qty = invoice line.quantity_billed
- short_qty_vs_po = ordered_qty − received_qty
- unreceived_billed_qty = max(billed_qty − received_qty, 0) (billing ahead of receipt)
- receipt_completion_ratio = received_qty / ordered_qty (round to 4 decimals)
- A clean three-way match = invoice approved AND received_qty == billed_qty AND
  received_qty == ordered_qty (or PO `received`) AND no price mismatch.

### 2.2 Price consistency / contract price
- po_unit_price = PO line.unit_price
- contract_unit_price = contract.unit_price for that sku+supplier (null/none if no
  contract). contract_price_match = (po_unit_price == contract_unit_price ==
  invoice_unit_price). If there is no contract for the sku, there is no contract
  price to match (treat as missing_contract, not a price mismatch).
- invoice_unit_price = invoice line.unit_price.
- PRICE_MISMATCH only when the prices actually differ.

### 2.3 AP invoice hold vs release
- The invoice's own `status` and `hold_code` are authoritative for current state:
  `on_hold` / `pending_receipt` => HOLD; `approved` => releasable (subject to
  match); `paid` => already settled.
- Common hold codes: `QTY_VARIANCE` (billed > received), `NO_RECEIPT` (no receipt
  posted / receipt_id null).
- RELEASE only when: invoice approved AND received_qty covers billed_qty AND no
  open blocking exception. Otherwise HOLD.
- A scheduled payment (payments.status == scheduled, scheduled_date within the
  task's window) means the invoice is being paid: it reduces the close/vendor
  balance and is reason code `SCHEDULED_PAYMENT_FOUND`. Respect any date cutoff in
  the memo (e.g. "scheduled through 2026-06-30").

### 2.4 Quantity variance reconciliation (AP close)
- quantity_billed = invoice billed qty; quantity_received = receipt received qty
  (0.00 if no receipt — say so with reason `NO_RECEIPT`).
- quantity_variance = quantity_billed − quantity_received.
- quantity_variance_pct = variance as a percentage **of PO quantity**
  (variance / PO_line.quantity × 100), rounded to 1 decimal — read the template;
  it specified "percentage of PO quantity", not of billed.
- Any nonzero variance => reason code `QTY_VARIANCE` and typically HOLD.
- reason_codes are a controlled enum, output **alphabetical** if the template says so.

### 2.5 Vendor balance / program rollups (AP close slice)
- opening_balance: use the value the memo tells you (often 0.00 for the slice).
- close_balance = opening_balance + invoice_total − scheduled_payments
  (apply the template's exact formula verbatim).
- held_invoice_total / releasable_invoice_total split by hold_decision.
- balance_status enum: FULLY_SCHEDULED (scheduled covers invoices),
  OPEN_HELD (has held invoices), OPEN_APPROVED (approved, not yet scheduled).
- Program summary: group by program_id; invoice_count, invoice_total, held_total,
  released_total, net_close_balance. Only include the TARGET invoices named in the
  memo — this is a "close-slice", not the whole ledger.

### 2.6 Sourcing nomination gates (readiness packet)
For each package line (sku + its requisition + its PO):
- selected_supplier_id = the PO's supplier (or the item's preferred_supplier_id).
- Compute blocker_codes (controlled enum, sorted ascending):
  - `missing_contract`: no active contract for that sku+supplier (PO.contract_id
    null AND no contract record found). 
  - `supplier_watch`: supplier.risk_rating == `watch` (or worse, per task).
  - `open_supplier_risk`: ≥1 vendor_risk_event with status in {open, monitoring}
    for that supplier, as of the as_of_date.
  - `ap_hold`: an AP invoice on this PO is on_hold / pending_receipt.
  - `pending_receipt`: PO not fully received (status open/partial_receipt) or no
    receipt yet but expected.
  - `late_due_date`: PO due_date / requisition need_by past the as_of_date and not
    fulfilled.
  - `none`: no blockers (use alone).
- readiness_status: `ready` (no blockers) / `at_risk` (soft blockers like watch /
  monitoring, but can proceed conditionally) / `not_ready` (hard blockers like
  missing_contract, ap_hold, no receipt, open severe risk).
- nomination_decision: `nominate` (ready), `conditional_nomination` (at_risk,
  clearable), `hold` (not_ready).
- Evidence lists (receipt_evidence_ids, invoice_exception_ids, risk_event_ids) are
  filtered "as of as_of_date" — use the `end=<as_of_date>` filter or drop records
  whose primary date is after as_of_date. Treat each as a SET, sort ascending.
- commercial_basis_id = the contract_id backing the line (null if none).
- committee_action: bucket suppliers into nominate_now / conditional / hold by
  decision; send_to_committee yes/no per whether anything is ready/conditional.

### 2.7 Receiving closeout SCOPE (critical exclusion rule)
- A receiving-batch closeout ("batch RCV-XXX") reconciles **only that batch's
  receipt lines** — NOT the cumulative of all receipts on the PO. If the same PO
  has another receipt (e.g. a later RCV-#### batch), it is a SEPARATE batch:
  exclude it from this batch's received_qty, and list it under any
  "excluded_same_po_receipt_ids" field. (Seen: PO-AX17-4481 has RCV-BLUE-14 and a
  separate RCV-00001 — the closeout for RCV-BLUE-14 uses only 216, not 216+157.)
- A closeout review of an already-posted receipt does NOT create a new receipt;
  "no visible damage reported" in the memo does NOT add DAMAGE_REJECTION unless the
  receipt's quantity_rejected > 0.
- DAMAGE_REJECTION only when quantity_rejected > 0.
- PARTIAL_RECEIPT when received_qty < ordered_qty.
- INVOICE_QTY_EXCEEDS_RECEIPT when billed_qty > received_qty.
- SUPPLIER_WATCH_RISK when supplier.risk_rating == `watch`.
- NO_EXCEPTION only when none of the above apply.

### 2.8 Change-control / contract amendment (release vs hold)
- **Contract headroom (ceiling)**: noncancelled_subtotal = Σ subtotal of all POs on
  the contract whose status != `cancelled` (EXCLUDE cancelled POs explicitly; list
  them in excluded_cancelled_po_ids). headroom_before = ceiling_amount −
  noncancelled_subtotal. requested_subtotal = requested_qty × contract.unit_price.
  headroom_after = headroom_before − requested_subtotal. ceiling_ok =
  (headroom_after >= 0).
- **Program budget**: from budget_snapshots for the program. remaining_budget =
  budget_cap − committed_amount. requested_tax = requested_subtotal × tax_rate
  (tax_rate from the memo, e.g. 7.25%). requested_total = requested_subtotal +
  requested_tax (freight only if the memo provides freight). budget_after_change =
  remaining_budget − requested_total. budget_ok = (budget_after_change >= 0).
  max_quantity_with_current_budget = floor(remaining_budget / (unit_price ×
  (1 + tax_rate))).
- **Approval**: find the latest approval_event for the source requisition
  (filter `object_id=REQ-...`, take max event_date). approval_ok = latest action is
  in the memo's "approval_good_actions" (e.g. `approved`). A `submitted` (not yet
  approved) => approval_ok=false => action obtain_final_requisition_approval.
- **Supplier risk**: supplier_risk_ok is true unless there is an OPEN event whose
  severity is severe (`high`/`critical`). A `watch` rating alone is context only
  (per memo) and does NOT block. severe_open_event_ids = open AND severe; open_event_ids
  = all status==open for that supplier.
- **Decision enum**: combine the gates:
  - all ok => `release_amendment`
  - budget fail only => `hold_for_budget`
  - approval fail only => `hold_for_approval`
  - budget AND approval fail => `hold_for_budget_and_approval`
  - supplier severe-risk fail => `hold_for_supplier_risk`
  - contract sku/price mismatch => `reject_contract_mismatch`
- required_actions: enum list, sorted ascending, one per failed gate
  (`raise_budget_exception_or_reduce_quantity`,
  `obtain_final_requisition_approval`, `resolve_supplier_risk_hold`); `none` if all ok.
- summary.blocker_count = number of failed gates; ready_to_release = (decision ==
  release_amendment).

### 2.9 Duplicate-invoice / chargeback netting (AP release file)
- A chargeback nets against the invoice it references. If chargeback.status ==
  `approved`: net_release_amount = invoice_total − approved_chargeback_amount;
  decision `release_net_after_approved_chargeback`; reason maps to the chargeback's
  reason_code (Underage Quantity => `approved_qty_chargeback`; AP Quantity Variance
  => `approved_ap_quantity_variance`).
- If chargeback.status == `pending_quality_review` (or the receipt is on
  inspection_hold): decision `hold_pending_quality_chargeback`; reason
  `inspection_hold_pending_chargeback`; the amount goes to pending_chargeback_total,
  net_release_amount = 0.00 (held, not released).
- Chargeback amount = basis_quantity × unit_cost from the register (the register is
  an input; use its numbers, but verify the referenced invoice/PO/receipt exist in
  the API).
- Invoice with receipt_id null AND no receipt on the PO: decision
  `hold_missing_receipt`, reason `no_receipt_on_po`, net 0.00.
- Duplicate/second receipt on the same PO that belongs to a different invoice:
  list under excluded_same_po_receipt_ids and add the corresponding followup
  (e.g. hold_luma_duplicate_receipt_for_separate_invoice).
- authoritative_sources = the procureops_* record families you actually used;
  supporting_only_sources = the note/alias payloads (request notes, stale-alias
  notes) — they are context, not authority.
- If the packet references generated/aliased PO-73xx IDs that don't exist in the
  API, use the real IDs the packet maps them to (use_available_shared_ids); flag
  the alias note as supporting_only and add the appropriate followup.

---

## 3. OUTPUT CONVENTIONS (get these exactly right)

1. Return ONLY the JSON object — no prose, no markdown fences around it.
2. Match the answer_template's keys, nesting, and enums EXACTLY. Templates come in
   two styles:
   - **Value-shape** (task 1/5): keys map to placeholder strings ("string",
     "YYYY-MM-DD") — emit those keys with real values.
   - **Schema-style** (task 2/3/4): keys like `required_keys`, `row_keys`,
     `allowed_values`, `item_schema`, `field_rules` DESCRIBE the output. Build the
     real object/list from those descriptions; do NOT echo the schema words.
3. task_id: use the template's required/expected value verbatim
   (e.g. `train_002`, `train_003`, or the value embedded in the template).
4. USD amounts rounded to **2 decimals (cents)**. Ratios/percentages to the
   precision the template states (e.g. completion_ratio 4 dp, variance_pct 1 dp).
   Round only at output; carry full precision in intermediate math.
5. Enum strings: copy VERBATIM from the template's allowed list (exact casing,
   underscores). Never invent a value outside the allowed set.
6. List fields: treat as SETS (dedupe) and SORT ascending unless the template
   gives a specific ordering ("sort by po_line_id ascending", "invoice_id
   ascending", "alphabetical"). When the template says "set; evaluator sorts
   values", still emit sorted for safety.
7. null vs empty: use `null` where the template allows it (e.g. hold_code null,
   commercial_basis_id null); use `[]` / `0.00` where a value is required but
   absent (e.g. quantity_received 0.00 when no receipt).
8. Booleans are real JSON booleans (true/false), not strings.

---

## 4. STEP-BY-STEP SOP FOR A NEW TASK

1. Read prompt.txt + the local payload(s). Note: the as_of/close/review date, the
   exact target IDs (POs, receipts, invoices, suppliers, programs), the scope
   ("only these invoices", "this batch"), and any business-control flags
   (tax rate, opening balance, good actions, exclusion rules).
2. Read answer_template.json end-to-end. List every output key, its type, its
   enum allowed-values, and its ordering rule. This defines exactly what to compute.
3. Pull the live records by ID first (`/collection/<id>`), then pull related sets
   by filter (`/receipts?po_id=`, `/ap_invoices?po_id=`, `/payments?invoice_id=`,
   `/approval_events?object_id=`, `/vendor_risk_events?supplier_id=`,
   `/budget_snapshots?program_id=`, `/purchase_orders?contract_id=`).
4. Apply date scoping: anything "as of <date>" => filter primary date <= as_of_date
   (use `end=`). Future-dated records are excluded.
5. Apply scope inclusion/exclusion: target IDs only; exclude cancelled POs from
   contract usage; exclude other-batch receipts from a batch closeout; exclude
   non-target invoices from a close-slice.
6. Run the relevant rule set from section 2 (three-way match, hold/release,
   variance, nomination gates, change-control gates, chargeback netting).
7. Compute money with full precision, round at the end to cents.
8. Assemble the JSON to the template's exact shape; verify every enum is from the
   allowed list and every list is deduped + correctly ordered.
9. Sanity check: do the rollups add up (program totals = sum of line items;
   net_balance = total − scheduled; net_release = total − approved chargeback)?
   Does each decision enum follow from its gates?

---

## 5. COMMON MISJUDGMENTS TO AVOID

- Filtering approval_events by `requisition_id` (use `object_id`).
- Treating `submitted` as approved (it is not — approval gate fails).
- Counting cancelled POs in contract usage / headroom.
- Summing all receipts on a PO when only one batch is in scope.
- Adding DAMAGE_REJECTION because a memo mentions damage — only quantity_rejected>0
  counts.
- Letting a `watch` supplier rating block a change-control release — it is context
  only unless an OPEN severe event exists.
- Including future-dated risk/approval events in an "as of" snapshot.
- variance_pct base: it is % of PO quantity (per template wording), not % of billed.
- Echoing template schema words (`required_keys`, `row_keys`, `allowed_values`)
  into the answer instead of real values.
- Overriding live API record values with stale numbers from the local memo/export.
- Releasing an invoice that is on_hold / pending_receipt or has a pending (not
  approved) chargeback / inspection_hold receipt.
- Forgetting to sort/dedupe list fields, or emitting an enum string with wrong
  casing.
