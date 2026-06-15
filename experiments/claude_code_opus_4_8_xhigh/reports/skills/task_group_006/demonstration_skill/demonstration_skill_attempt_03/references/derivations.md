# ProcureOps derivations reference

Detailed record shapes, computation recipes, and the five task families seen in
this domain. Read this after SKILL.md when you need exact field math. Each task
in this domain is a recombination of the building blocks below, so understanding
the building blocks transfers even when the answer template is new.

## Table of contents
- [Record shapes](#record-shapes)
- [Core derived quantities](#core-derived-quantities)
- [Exception / blocker / reason vocabularies](#exception--blocker--reason-vocabularies)
- [Task family A — sourcing nomination readiness](#task-family-a--sourcing-nomination-readiness)
- [Task family B — receiving / AP reconciliation closeout](#task-family-b--receiving--ap-reconciliation-closeout)
- [Task family C — AP close hold/release + vendor balances](#task-family-c--ap-close-holdrelease--vendor-balances)
- [Task family D — change-control / contract & budget headroom](#task-family-d--change-control--contract--budget-headroom)
- [Task family E — AP release with chargeback netting](#task-family-e--ap-release-with-chargeback-netting)

---

## Record shapes

Fields below are the ones that drive answers. The list endpoints return
`{"count": n, "results": [...]}`; single-id endpoints return the bare object.

**program** (`/programs/<id>`): `program_id, name, owner, status, priority,
budget_cap, committed_amount, cost_center, region`. Budget headroom lives here
directly (`budget_cap - committed_amount`).

**supplier** (`/suppliers/<id>`): `supplier_id, name, status` (active |
quality_hold), `risk_rating` (low | medium | high | watch), `payment_terms,
region`. `risk_rating` is a standing label; it is NOT the same as having an open
risk event.

**item** (`/items/<sku>`): `sku, description, category, uom, standard_cost,
preferred_supplier_id, active`.

**contract** (`/contracts/<id>`): `contract_id, program_id, supplier_id, sku,
status, price_type` (fixed | ...), `unit_price, ceiling_amount, effective_date,
expiry_date, buyer`. The contract is the commercial basis for a line.

**purchase_requisition** (`/purchase_requisitions/<id>`): `requisition_id,
program_id, sku, quantity, status` (converted | ...), `requester, priority,
need_by`.

**purchase_order** (`/purchase_orders/<id>`): `po_id, program_id, supplier_id,
contract_id, requisition_id, status` (open | confirmed | partial_receipt |
received | closed | cancelled), `order_date, due_date, ship_to, currency,
subtotal, tax, total`, and `lines[]` each `{line_id, sku, description, quantity,
unit_price}`.

**receipt** (`/receipts/<id>`): `receipt_id, po_id, supplier_id, warehouse_id,
receipt_date, packing_slip, receiver, status` (accepted | accepted_with_note |
inspection_hold), and `lines[]` each `{po_line_id, sku, quantity_received,
quantity_rejected, inspection_status}` (passed | variance). Primary date field
for `start/end` filtering is `receipt_date`.

**ap invoice** (`/ap/invoices/<id>`): `invoice_id, po_id, supplier_id,
receipt_id` (may be null), `invoice_date, status` (entered | pending_receipt |
on_hold | approved | paid), `hold_code` (null | NO_RECEIPT | QTY_VARIANCE |
PRICE_VARIANCE | SUPPLIER_REVIEW), `currency, subtotal, freight, tax, total`,
and `lines[]` each `{po_line_id, sku, quantity_billed, unit_price}`. Primary
date field is `invoice_date`.

**ap payment** (`/ap/payments/<id>`): `payment_id, invoice_id, supplier_id,
amount, currency, scheduled_date, status` (scheduled | released). Primary date
field is `scheduled_date`.

**approval_event** (`/approval_events/<id>`): `event_id, object_id, object_type`
(requisition | ...), `action` (submitted | approved | returned | ...), `actor,
event_date, note_code`. NOTE the join key is `object_id`, not `requisition_id`.
Filter with `?object_id=REQ-...`.

**budget_snapshot** (`/budget_snapshots/<id>`): `snapshot_id, program_id,
budget_cap, committed_amount, pending_invoice_amount, currency, snapshot_date`.

**vendor_risk_event** (`/vendor_risk_events/<id>`): `event_id, supplier_id,
event_type` (invoice_variance | quality_hold | late_delivery | bank_change |
duplicate_invoice_review), `severity` (low | medium | high), `status` (open |
monitoring | closed), `event_date, related_object_id`.

---

## Core derived quantities

**Budget headroom / remaining budget** = `budget_cap - committed_amount`. The
program record and the program's budget_snapshot normally agree; the snapshot is
the named source when a template asks for `snapshot_id`. `pending_invoice_amount`
is informational and is NOT subtracted into headroom unless a template/memo says
so.

**Contract headroom** = `ceiling_amount - noncancelled_subtotal`, where
`noncancelled_subtotal` = sum of `subtotal` over every PO on that contract whose
status is NOT `cancelled`. Headroom after a change = headroom_before -
requested_subtotal. `requested_subtotal` = requested_qty * contract unit_price.
`ceiling_ok` = headroom_after >= 0.

**Budget impact of a change** = `requested_total` = requested_subtotal +
requested_tax (+ freight only if the memo supplies freight). `requested_tax` =
round(requested_subtotal * tax_rate). `budget_after_change` = remaining_budget -
requested_total; `budget_ok` = budget_after_change >= 0.
`max_quantity_with_current_budget` = the largest integer q such that
`q*unit_price*(1+tax_rate) <= remaining_budget` (floor; freight excluded unless
given). Verify by plugging q and q+1 back in.

**Quantity reconciliation** (per PO line, matched on `po_line_id`):
- `ordered_qty` = PO line quantity.
- `received_qty` = sum of `quantity_received` across receipts on that PO/line
  that are in scope (see duplicate-receipt rule). 0 when no receipt exists.
- `rejected_qty` = sum of `quantity_rejected`.
- `billed_qty` = invoice line `quantity_billed`.
- `short_qty_vs_po` = ordered - received (floor at 0).
- `unreceived_billed_qty` = max(billed - received, 0).
- `quantity_variance` = billed - received.
- `quantity_variance_pct` = round(variance / ordered_qty * 100, 1).
- `receipt_completion_ratio` = round(received / ordered, 4).

**Price reconciliation**: `po_unit_price` from PO line, `contract_unit_price`
from contract, `invoice_unit_price` from invoice line. `contract_price_match` =
(po == contract == invoice) to the cent. A mismatch is a PRICE_MISMATCH /
PRICE_VARIANCE exception.

**Goods value**: `received_goods_value` = received_qty * unit_price;
`unreceived_goods_value` = (billed or ordered, per template) shortfall *
unit_price. `invoice_subtotal/freight/tax/total` come straight off the invoice;
do not recompute tax unless the template asks you to.

**Money rounding**: round every USD amount to cents (2 dp) unless a field's
template note says otherwise (ratios to 4 dp, variance_pct to 1 dp). Compute on
raw numbers, round at the end.

---

## Exception / blocker / reason vocabularies

These enums recur. The exact allowed list is always in the task's
answer_template — copy from there; the rules below tell you when each fires.

**Supplier-risk "open as of date"**: a risk event is in scope when
`status in {open, monitoring}` AND `event_date <= as_of/cutoff date`. `closed`
events are excluded. `monitoring` counts as open. This drives `risk_event_ids`,
`open_supplier_risk_event_ids`, `has_open_supplier_risk`, the `open_supplier_risk`
blocker, and `severe_open_event_ids` (the in-scope subset with `severity == high`).

**Invoice exception / AP-hold**: an invoice is an exception when its `status` is
`on_hold` or `pending_receipt`, or it carries a non-null `hold_code`. `paid` and
clean `approved` invoices are NOT exceptions. `invoice_exception_ids` for a line
= every exception invoice tied to that line's PO(s).

**Duplicate invoice**: two or more invoices on the same `po_id` (often both
on_hold) are a duplicate-invoice exception. Include all of them in the line's
exception id set; do not silently drop the "extra" one.

**Duplicate / extra receipt on a PO**: a PO can have more than one receipt. The
in-scope receipt is the one tied to the invoice/packing slip under review; other
receipts on the same PO go into `excluded_same_po_receipt_ids`. Do not sum their
quantities into the reconciliation.

**Missing receipt**: invoice `receipt_id` is null AND no receipt exists for the
PO. Produces NO_RECEIPT / `pending_receipt` / `no_receipt_on_po` /
`hold_missing_receipt`, and a synthetic receiving-exception row keyed e.g.
`MISSING:<po_id>` with `resolution_status: missing_receipt`.

**Receiving exception codes** (family E): derived from the receipt AND the
chargeback register row for that receipt. The chargeback `reason_code` is the
strongest signal — map it, then add status-based codes:
- An **Underage Quantity** chargeback (a real receipt-vs-PO shortfall,
  received < ordered) yields BOTH `Underage Quantity` AND `Severe Unmatched
  Quantity`. These two travel together — in this data every underage-shortfall
  chargeback line is also flagged severe (seen at 10% and at 34% shortfall), so
  don't gate "severe" on a percentage threshold; gate it on "there is an
  underage/quantity-shortfall chargeback basis".
- An **AP Quantity Variance** chargeback (billed-vs-received gap, but the receipt
  itself is complete — received == ordered) yields only `AP Quantity Variance`,
  NOT the underage/severe pair.
- `Inspection Hold` when receipt `status == inspection_hold` (or a line
  `inspection_status == variance`).
Build the set, let the evaluator sort it.

**Blocker codes** (family A): emit only the ones that apply, sorted ascending:
- `missing_contract` — no active contract / `commercial_basis_id` is null.
- `supplier_watch` — supplier `risk_rating == watch` (or high).
- `open_supplier_risk` — at least one in-scope open/monitoring risk event.
- `ap_hold` — at least one exception/on-hold invoice on the line.
- `pending_receipt` — ordered but no accepted receipt yet.
- `late_due_date` — PO `due_date` (or req `need_by`) is before the as_of date.
- `none` — only when no blocker applies.

---

## Task family A — sourcing nomination readiness

Goal: per package line (sku), pick the supplier, decide
nominate/conditional_nomination/hold, list evidence + exception + risk ids and
blocker codes, then roll up a committee action.

1. Resolve the program; `owner` and `budget_headroom_usd = budget_cap -
   committed_amount`.
2. For each package anchor (sku + requisition + PO from the memo): confirm the
   PO/req against the API, read the contract for that sku (`commercial_basis_id`
   = contract_id, or null if none -> `missing_contract`), and the selected
   supplier (`selected_supplier_id` from the contract/PO).
3. `receipt_evidence_ids` = accepted receipts on the line's PO(s), as of date.
4. `invoice_exception_ids` = on-hold/exception invoices on the PO(s), as of date
   (includes duplicate invoices).
5. `risk_event_ids` = supplier's open/monitoring risk events as of date.
6. `blocker_codes` per the vocabulary above.
7. Decision: `nominate` only when no blockers; `conditional_nomination` when the
   line has soft blockers but a valid contract and some receipt evidence (e.g.
   supplier_watch + ap_hold + open_supplier_risk but contract present);
   `hold` when hard blockers (missing_contract, pending_receipt, late_due_date)
   apply. `readiness_status` mirrors: ready / at_risk / not_ready.
8. `overall_readiness` = worst line status; `not_ready` if any line is
   not_ready.
9. Committee action: bucket supplier ids by decision into
   nominate_now/conditional/hold; `send_to_committee = yes` only if at least one
   line is nominate-now-ready (else `no`); `next_owner` = the owner of the
   binding blocker (ap_team for ap_hold, quality_ops for risk, finance_ops for
   budget, buyer for sourcing, program_owner otherwise).

## Task family B — receiving / AP reconciliation closeout

Goal: reconcile one receiving batch against PO/contract/invoice, decide AP hold
vs release, and report dollars + supplier risk.

- `inspection_summary` straight from the receipt (po_id, program via PO,
  supplier id+name, warehouse, receipt_date, packing_slip, receiver).
- `line_reconciliation` per the quantity & price recipes above, sorted by
  `po_line_id`.
- `invoice_review`: invoice_id, invoice_status, hold_code, receipt_status,
  po_status, and the `exception_codes` set (INVOICE_QTY_EXCEEDS_RECEIPT when
  billed > received; PARTIAL_RECEIPT when po status is partial_receipt;
  SUPPLIER_WATCH_RISK when rating==watch; PRICE_MISMATCH on price gap;
  DAMAGE_REJECTION when rejected>0; else NO_EXCEPTION).
- `financials` per recipe; invoice freight/tax/total verbatim from invoice.
- `decision`: pick the controlled enum that matches — e.g. a billed>received
  shortage with a watch supplier and on-hold invoice =>
  accept_partial_hold_variance / keep_invoice_on_hold /
  record_shortage_follow_up / request_credit_or_remaining_delivery.
- `supplier_risk_context`: rating, has_open_supplier_risk, open event ids.
- `evidence.endpoint_record_ids` = every API record id you actually used
  (supplier, item/contract, PO, receipt, invoice, risk events). `task_payloads_
  reviewed` = the local memo paths you read. Both are sets; evaluator sorts.

## Task family C — AP close hold/release + vendor balances

Goal: for a named set of invoices only, decide HOLD vs RELEASE, reconcile vendor
balances and program totals, and emit hold/release queues.

- Per invoice: `hold_decision = RELEASE` only when status is `approved` AND a
  scheduled payment exists through the memo's cutoff AND quantity matches
  (variance 0); else `HOLD` with the invoice's `hold_code`. `release_to_payment`
  = (decision == RELEASE).
- `quantity_received` = 0.00 when no receipt; `quantity_variance = billed -
  received`; `quantity_variance_pct` = % of PO quantity, 1 dp.
- `scheduled_payment_amount` = sum of payments for that invoice with
  `scheduled_date <= cutoff` (status scheduled or released); else 0.
  `net_balance_impact` = invoice_total - scheduled_payment_amount.
- `reason_codes` (sorted alphabetically): APPROVED_THREE_WAY_MATCH (approved +
  receipt + match), NO_RECEIPT, QTY_VARIANCE, SCHEDULED_PAYMENT_FOUND.
- `vendor_balances`: opening_balance from the memo (often 0.00 for the slice);
  invoice_total/scheduled_payments/held/releasable summed per supplier within
  the slice; `close_balance = opening + invoice_total - scheduled_payments`;
  `balance_status` = FULLY_SCHEDULED (close 0 & all scheduled), OPEN_HELD (held
  amount > 0), else OPEN_APPROVED.
- `program_summary` rolls the same per program. `total_close_balance` = sum of
  net close balances. Queues are the invoice_ids, sorted ascending.
- Stay strictly within the named invoices — do not pull the supplier's other
  invoices into the slice.

## Task family D — change-control / contract & budget headroom

Goal: decide whether a requested incremental buy can be released as an amendment.

- `contract_check`: status, price_type, unit_price, ceiling_amount,
  noncancelled_subtotal (exclude cancelled POs), headroom_before, requested_qty,
  requested_subtotal = qty*unit_price, headroom_after, ceiling_ok.
- `program_budget_check`: snapshot_id, budget_cap, committed_amount,
  remaining_budget, requested_tax, requested_total, budget_after_change,
  budget_ok, max_quantity_with_current_budget (floor).
- `approval_check`: find the requisition's latest approval_event via
  `?object_id=<req_id>` (latest by event_date). approval_ok = latest `action`
  is in the memo's good-actions list (e.g. only `approved`; a `submitted`/
  `returned` latest event => not ok).
- `supplier_risk_check`: supplier_status, risk_rating, open_event_ids
  (open/monitoring), severe_open_event_ids (severity high among open).
  supplier_risk_ok = no SEVERE open event (a plain `watch` rating is context
  only, still ok).
- `supporting_ids`: included_po_ids (non-cancelled on contract),
  excluded_cancelled_po_ids, approval_event_ids — each sorted ascending.
- `decision`: combine the gates. release_amendment only if ceiling_ok AND
  budget_ok AND approval_ok AND supplier_risk_ok. Otherwise pick the matching
  hold_for_* enum (combine e.g. hold_for_budget_and_approval when both fail).
  reject_contract_mismatch if the contract sku/program doesn't match the memo.
- `required_actions` (sorted): obtain_final_requisition_approval (approval not
  ok), raise_budget_exception_or_reduce_quantity (budget not ok),
  resolve_supplier_risk_hold (severe risk), or [none].
- `summary.blocker_count` = number of failed gates; ready_to_release = decision
  is release_amendment.

## Task family E — AP release with chargeback netting

Goal: for named invoices, net approved chargebacks and hold the rest; the LOCAL
chargeback register drives status, the API confirms receipts/totals.

- Source-of-truth precedence: the local `chargeback_register` (and its
  `status`: approved | pending_quality_review) governs whether a chargeback nets
  now. The API confirms invoice totals, PO, and receipts. A stale alias note
  (e.g. PO-73xx that doesn't exist) is supporting-only: use the real generated
  ids the packet provides.
- Per invoice: `receipt_ids_in_scope` = the receipt tied to this invoice;
  `excluded_same_po_receipt_ids` = other receipts on the same PO.
- `approved_chargeback_amount` = basis_quantity * unit_cost for chargebacks with
  status approved on this invoice; `pending_chargeback_amount` likewise for
  pending_quality_review.
- `decision`/`primary_reason`:
  - approved chargeback present, receipt present =>
    release_net_after_approved_chargeback / approved_qty_chargeback (or
    approved_ap_quantity_variance for an AP-variance reason).
  - pending quality chargeback => hold_pending_quality_chargeback /
    inspection_hold_pending_chargeback (net_release 0).
  - no receipt on PO => hold_missing_receipt / no_receipt_on_po.
- `net_release_amount` = invoice_total - approved_chargeback_amount for a
  release; 0 for any hold.
- `receiving_exceptions`: one row per receipt (plus a MISSING:<po> row for a
  missing receipt) with exception_codes, chargeback_status, resolution_status.
- `summary`: release_invoice_ids / hold_invoice_ids; approved & pending
  chargeback totals; net_release_total = sum of net_release_amount over
  releases; classify each source you used into authoritative_sources
  (procureops_* records, local_chargeback_register) vs supporting_only_sources
  (ap_release_request_note, stale_po73xx_alias_note); list followup_actions from
  the allowed enum. All id lists are sets; evaluator sorts.
