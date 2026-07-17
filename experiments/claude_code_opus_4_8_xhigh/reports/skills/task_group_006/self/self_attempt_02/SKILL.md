---
name: self_attempt_02
description: SOP for ProcureOps ERP procure-to-pay tasks (sourcing nomination, receiving control, three-way match, AP hold/release, chargeback netting, contract/budget headroom) using the read-only API as source of truth.
---

# ProcureOps procure-to-pay solver skill

You answer procurement / receiving / accounts-payable questions against the
**ProcureOps** read-only ERP API and a per-task local payload. Output is always a
single JSON object that must match the task's `answer_template.json` shape exactly.

## 0. Golden rules (read first)

1. **The API is the source of truth.** Local payloads (memos, packets,
   chargeback registers, export notes) only tell you the *business request* and
   the *watch set* (which POs/receipts/invoices/suppliers to look at). Whenever a
   number disagrees, trust the API record, not the payload. One documented
   exception: a **local chargeback / credit register** is authoritative for
   chargeback amounts and approval status because those debits do not live in the
   ERP yet (see Task-5 pattern).
2. **Base URL is supplied by the runner / environment_access.md.** The prompt's
   `http://127.0.0.1:8006` or `localhost:8006` is a placeholder — replace it with
   the real base URL from `environment_access.md` (e.g.
   `<remote-env-url>`).
3. **Match the template byte-for-byte.** Same top-level keys, same nested keys,
   same enum spellings (copy enum strings verbatim, including UPPER_SNAKE vs
   lower_snake). Do not add keys the template does not list. Read whether
   `task_id` is a literal `required_value` and emit exactly that string.
4. **Rounding & types.** USD amounts → round to 2 decimals (cents). Ratios with a
   stated precision (e.g. `precision: 4`) → round to that many places. Quantities
   are integers. Percentages → the stated decimals (often 1). Booleans are real
   JSON booleans, not strings.
5. **Lists are sets unless a sort rule is given.** If the template says
   "sorted ascending" / "ordering: X ascending", sort. If it says
   "set; evaluator sorts values", order does not matter but de-duplicate. When in
   doubt, sort ascending — it never hurts a set.
6. **Respect the as-of / close / review date.** Records dated *after* the as-of
   date are out of scope. The date filter is **inclusive** of the as-of day
   (a record dated exactly on the as-of date is IN scope). This is the single
   most common scoping mistake — see §5.

## 1. API usage

Endpoints (GET only):
`GET /` (endpoint list), `GET /health`, `GET /manifest` (counts + anchor IDs),
`GET /<collection>` → `{"count": N, "results": [...]}`,
`GET /<collection>/<id>` → one object (404 if missing).

Collections: `programs`, `suppliers`, `items`, `contracts`,
`purchase_requisitions`, `purchase_orders`, `receipts`, `ap_invoices`,
`payments`, `approval_events`, `budget_snapshots`, `vendor_risk_events`.
Aliases also work: `purchase-orders`, `ap-invoices` / `/ap/invoices`,
`/ap/payments`, `approvals`, `budgets`, `vendor-risks`, `purchase-requests`.

Filtering: append any record field as a query param (case-insensitive), e.g.
`/receipts?po_id=PO-AX17-4481`, `/ap_invoices?supplier_id=SUP-LUMA`,
`/vendor_risk_events?supplier_id=SUP-LUMA`, `/approval_events?object_id=REQ-AX17-141`,
`/purchase_orders?contract_id=CR-LMP-228`, `/purchase_orders?sku=LMP-228`.
Date window via `start`/`end` on the collection's primary date field
(receipts→receipt_date, ap_invoices→invoice_date, payments→scheduled_date,
purchase_orders→order_date, approval_events→event_date,
budget_snapshots→snapshot_date, vendor_risk_events→event_date,
purchase_requisitions→need_by, contracts→effective_date). `end=<as_of>` is the
clean way to scope to the as-of date and it is inclusive.

Workflow: pull the named anchors by ID, then **fan out by filter** (all receipts
for a PO, all invoices for a PO, all risk events for a supplier, all POs for a
contract). Never assume one PO has one receipt or one invoice — multiples are
common and scoping them correctly is where points are won/lost.

## 2. Record schemas (fields you will use)

- **programs**: program_id, name, owner, cost_center, budget_cap,
  committed_amount, priority, status, region.
- **suppliers**: supplier_id, name, risk_rating (`low|watch|medium|high`),
  status (`active|quality_hold`), payment_terms, region.
- **items**: sku, description, category, standard_cost, preferred_supplier_id,
  uom, active.
- **contracts**: contract_id, program_id, sku, supplier_id, status
  (`active|draft|...`), price_type (`fixed|...`), unit_price, ceiling_amount,
  effective_date, expiry_date, buyer.
- **purchase_requisitions**: requisition_id, program_id, sku, quantity, requester,
  need_by, priority, status (`approved|converted|...`).
- **purchase_orders**: po_id, program_id, supplier_id, contract_id (may be null),
  requisition_id, status (`open|confirmed|partial_receipt|received|closed|cancelled`),
  order_date, due_date, ship_to, currency, subtotal, tax, total,
  `lines:[{line_id, sku, description, quantity, unit_price}]`.
- **receipts**: receipt_id, po_id, supplier_id, warehouse_id, receipt_date,
  packing_slip, receiver, status (`accepted|accepted_with_note|inspection_hold`),
  `lines:[{po_line_id, sku, quantity_received, quantity_rejected, inspection_status (`passed|variance`)}]`.
- **ap_invoices**: invoice_id, po_id, supplier_id, receipt_id (may be null),
  invoice_date, status (`approved|paid|on_hold|pending_receipt|entered`),
  hold_code (`null|NO_RECEIPT|PRICE_VARIANCE|QTY_VARIANCE|SUPPLIER_REVIEW`),
  currency, subtotal, freight, tax, total,
  `lines:[{po_line_id, sku, quantity_billed, unit_price}]`.
- **payments**: payment_id, invoice_id, supplier_id, amount, scheduled_date,
  status (`scheduled|...`), currency.
- **approval_events**: event_id, object_id (e.g. a requisition_id), object_type,
  action (`submitted|approved|escalated|returned`), actor, event_date, note_code.
- **budget_snapshots**: snapshot_id, program_id, budget_cap, committed_amount,
  pending_invoice_amount, snapshot_date, currency.
- **vendor_risk_events**: event_id, supplier_id, event_type
  (`bank_change|invoice_variance|late_delivery|duplicate_invoice_review|quality_hold`),
  severity (`low|medium|high`), status (`open|monitoring|closed`),
  related_object_id, event_date.

## 3. Core business rules (transferable)

### 3.1 Three-way match (PO ↔ receipt ↔ invoice)
Match on the same `po_line_id`/`sku`. Compute per line:
- `short_qty_vs_po   = ordered_qty - received_qty` (PO line qty minus receipt qty).
- `unreceived_billed_qty = billed_qty - received_qty` (positive = invoiced more
  than received → the dangerous case).
- `receipt_completion_ratio = received_qty / ordered_qty`.
- `quantity_variance = billed_qty - received_qty`;
  `quantity_variance_pct = variance / PO_line_quantity * 100` (variance is taken
  as a % **of the PO quantity**, not of billed — read the template wording).
A clean three-way match = invoice approved, no hold_code, billed == received ==
ordered (or billed <= received), and prices consistent.

### 3.2 Quantity_received: which receipts count
- For an **invoice-level** reconciliation, the invoice usually carries a
  `receipt_id`. Use that specific receipt's received quantity. If
  `receipt_id` is null → received = 0 and the invoice is effectively NO_RECEIPT.
- For a **PO/receiving-batch** reconciliation, scope to the named batch/receipt
  only (the memo will say "closeout for an already-posted receipt"). Do NOT roll
  in later receipts on the same PO that fall after the as-of/review date.
- Always check whether a PO has *other* receipts: an extra receipt on the same PO
  that is out of the date window or tied to a different invoice goes into an
  **excluded** list (e.g. `excluded_same_po_receipt_ids`), not the in-scope list.

### 3.3 Contract price consistency
`contract_price_match` (or `ceiling_ok` pricing context) = invoice/PO
`unit_price` equals the active contract's `unit_price` for that sku/supplier.
A mismatch → `PRICE_MISMATCH` / `PRICE_VARIANCE`. Find the contract via
`/contracts?sku=...&supplier_id=...`; if none exists the line has **no commercial
basis** (blocker `missing_contract`, commercial_basis_id = null).

### 3.4 Contract ceiling headroom
- `noncancelled_subtotal` = sum of `subtotal` over all POs on the contract whose
  status is **not** `cancelled` (exclude cancelled; list them in
  `excluded_cancelled_po_ids`).
- `headroom_before_change = ceiling_amount - noncancelled_subtotal`.
- `requested_subtotal = requested_quantity * contract_unit_price`.
- `headroom_after_change = headroom_before_change - requested_subtotal`.
- `ceiling_ok = requested_subtotal <= headroom_before_change`
  (equivalently headroom_after >= 0).
- Contract ceiling exposure is **subtotal before tax and freight**.

### 3.5 Program budget headroom
- Use the program's `budget_snapshot` (preferred) or the program record:
  `remaining_budget = budget_cap - committed_amount`.
- Budget exposure = **line subtotal + estimated tax** (freight only if the memo
  supplies a freight figure). `requested_tax = requested_subtotal * tax_rate`;
  `requested_total = requested_subtotal + requested_tax`.
- `budget_after_change = remaining_budget - requested_total`;
  `budget_ok = budget_after_change >= 0`.
- `max_quantity_with_current_budget = floor( remaining_budget /
  (unit_price * (1 + tax_rate)) )` (per-unit cost grossed up for tax; floor it).
- `budget_headroom_usd` for a program summary = `budget_cap - committed_amount`
  (rounded to cents).

### 3.6 Approval gate
Find the requisition's events via `/approval_events?object_id=<requisition_id>`.
Take the **latest by event_date** (tie-break by event_id). `approval_ok` is true
only if the latest action is in the memo's "good actions" set — typically just
`approved`. `submitted`, `escalated`, `returned` do **not** clear the gate.

### 3.7 Supplier-risk policy
- `risk_rating` of `watch`/`medium`/`high` is **context only** and does not by
  itself block a release — unless the rule says so. A `watch` rating commonly
  raises a `supplier_watch` blocker code or a `SUPPLIER_WATCH_RISK` exception
  note in nomination/receiving contexts, but it does not force a HOLD on its own.
- **Open risk events** = events with status `open` or `monitoring` (closed are
  out). Filter by `/vendor_risk_events?supplier_id=...` then keep open/monitoring
  *as of the as-of date* (event_date <= as_of).
- **Severe open event** = an open/monitoring event with severity `high` (treat
  `critical` likewise if present). A severe open event is a real blocker
  (`open_supplier_risk` / hold_for_supplier_risk); `supplier_risk_ok = false`.
  Medium/low open events are usually monitored, not blocking — unless the
  template's logic counts any open event.
- Supplier `status = quality_hold` (vs `active`) is itself a hard supplier block.

### 3.8 AP invoice release vs hold
Default to **HOLD / keep_on_hold** when ANY of:
- invoice `status` is `on_hold` or `pending_receipt`, or any non-null `hold_code`;
- `hold_code = NO_RECEIPT` or the invoice's receipt is missing (received = 0);
- billed_qty > received_qty (`INVOICE_QTY_EXCEEDS_RECEIPT` / QTY_VARIANCE);
- price mismatch vs contract (PRICE_VARIANCE);
- a severe open supplier-risk event / supplier on quality_hold.
**RELEASE** only when the invoice is `approved` with no hold_code, the three-way
match is clean (billed == received), and there is no blocking risk. A
`scheduled` payment in `/payments?invoice_id=...` (with scheduled_date within the
horizon) is evidence to release and adds `SCHEDULED_PAYMENT_FOUND`.

### 3.9 Duplicate-invoice handling
Two non-cancelled invoices on the same PO (especially similar totals, or a
`duplicate_invoice_review` risk event) signal a possible duplicate. Do not blindly
release both — keep the later/unconfirmed one on hold and flag it. When the task
scope names ONE invoice per PO, the *other* invoice/receipt on that PO is excluded
context, not in-scope.

### 3.10 Chargeback / credit netting (AP release with debits)
When a local chargeback register lists debits against an invoice:
- `approved` chargeback → net it now:
  `net_release_amount = invoice_total - approved_chargeback_amount`;
  decision = release_net_after_approved_chargeback.
- `pending_*` chargeback (e.g. pending_quality_review) → do NOT net, HOLD the
  invoice: decision = hold_pending_quality_chargeback, net_release = 0,
  pending_chargeback_amount = the pending debit.
- chargeback amount = `basis_quantity * unit_cost` (round to cents).
- An invoice with no receipt on its PO → hold_missing_receipt, net_release = 0,
  regardless of any release request note.
- A receipt in `inspection_hold` with a pending chargeback → hold for quality.

## 4. Output conventions

- Build the JSON to mirror the template's nesting and key order exactly; emit only
  the keys the template names. If the template is "shape doc" (with `type`,
  `required_keys`, `allowed_values`), produce the *concrete* object those describe,
  not the meta-schema.
- Enums: copy the allowed string verbatim. Reason-code / exception-code lists:
  include only codes that actually apply; if none apply and a `NO_EXCEPTION` /
  `none` sentinel exists, use it.
- Sort every list the template marks "ascending" / "sorted"; de-dup set lists.
- USD → 2 dp; ratios → stated precision; integers for quantities; real booleans.
- For "queue" outputs (hold queue / release queue), list invoice_ids and sort
  ascending; an invoice appears in exactly one queue.
- Evidence/supporting-id lists: include the actual record IDs you read from the
  API; keep authoritative vs supporting-only sources separate when the template
  asks (API records = authoritative; local notes/aliases = supporting-only).

## 5. Common misjudgments (learned from train tasks)

1. **Including out-of-window receipts/invoices.** A PO often has a later receipt
   (e.g. dated 06-08 when as-of is 06-01) — exclude it. Use `end=<as_of>` or
   filter `date <= as_of` yourself. Boundary date == as-of is INCLUDED.
2. **Rolling all receipts on a PO into one invoice's received qty.** Use the
   invoice's own `receipt_id`; treat the rest as excluded/duplicate context.
3. **Treating `watch`/medium risk as an automatic HOLD.** It is context only;
   only a severe (high) open event, supplier `quality_hold` status, or an actual
   match/qty/price failure blocks a release.
4. **Counting cancelled POs in contract usage.** Always exclude `cancelled` from
   noncancelled_subtotal and list them separately.
5. **Approval false-positives.** "submitted"/"escalated"/"returned" are NOT
   approvals; only the configured good action (usually `approved`) clears the gate,
   and you must use the *latest* event.
6. **Variance % base.** Variance percentage is of the **PO quantity**, not billed
   quantity — read the field description.
7. **Tax in budget but not in ceiling.** Contract ceiling exposure = subtotal
   only; program budget exposure = subtotal + tax (+ freight only if memo gives it).
8. **task_id / required_value.** Emit the literal value the template demands
   (e.g. `"train_002"`), not the API-style id.
9. **Local payload numbers vs API.** If the memo and API disagree on a price/qty,
   use the API — except for chargeback debits that live only in the local register.

## 6. Step-by-step SOP for a new task

1. Read `prompt.txt`, the local payload(s), and `answer_template.json`. Note: the
   as-of/close/review date, the exact watch-set IDs, the tax rate, any
   "good actions" / exclusion rules, and the literal `task_id`/required values.
2. Map the template: list every key, its type, enum domain, rounding, and sort/set
   rule. This is your output contract.
3. Pull each named anchor by ID from the API. Then fan out by filter to get every
   related receipt (per PO), invoice (per PO/supplier/program), payment (per
   invoice), approval event (per requisition), risk event (per supplier), and
   contract (per sku+supplier or contract_id).
4. Apply the as-of date scope: drop records dated after the as-of date; keep the
   exact watch-set; separate excluded/duplicate context records.
5. Run the relevant rule set (§3): three-way match, price/contract check, ceiling
   headroom, budget headroom, approval gate, supplier-risk, AP hold/release,
   chargeback netting. Compute every numeric field with explicit rounding.
6. Derive decisions/enums from the computed facts; assemble queues and reason/
   exception code lists (apply, don't over-add).
7. Emit JSON matching the template exactly — right keys, enum spellings, rounding,
   sorted/de-duped lists, real booleans. No prose outside the JSON object.
8. Self-check: keys present == template keys; every amount 2 dp; every "ascending"
   list sorted; every set de-duped; literal task_id correct; decision consistent
   with the blocker/reason codes you emitted (e.g. if any blocker, ready_to_release
   is false and blocker_count matches the count of required actions).
