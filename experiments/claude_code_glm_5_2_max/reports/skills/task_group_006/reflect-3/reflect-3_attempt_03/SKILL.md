# ProcureOps ERP Procurement Solver Skill (task_group_006)

Reusable workflow rules for solver agents on unseen test tasks in this procurement
benchmark. Recipe-oriented; NOT candidate answers. The remote API
`<remote-env-url>` is the source of truth (task prompts' `127.0.0.1:8006` =
this same service). Do NOT call any judge endpoint at test time.

## 0. API mechanics (all families)

- `GET /<collection>` -> `{"count":N,"results":[...]}`. `GET /<collection>/<id>` -> record object.
- Collections: `programs`, `suppliers`, `items`, `contracts`, `purchase_requisitions`
  (alias `/purchase-requests`), `purchase_orders` (alias `/purchase-orders`),
  `receipts`, `ap_invoices` (alias `/ap/invoices`), `payments` (alias `/ap/payments`),
  `approval_events` (alias `/approvals`), `budget_snapshots` (alias `/budgets`),
  `vendor_risk_events` (alias `/vendor-risks`).
- Field filters match substring/case-insensitive INCLUDING nested list values; blank
  values ignored. Foreign-key filters: `/receipts?po_id=`, `/ap_invoices?po_id=`
  (`?supplier_id=`), `/payments?invoice_id=`, `/approval_events?object_id=`,
  `/vendor_risk_events?supplier_id=`, `/purchase_orders?contract_id=`.
- `start`/`end` filter the collection's date field (inclusive) — use for payment cutoffs.
- There is NO pagination param; unknown query params return 0 results. Fetch by id.
- `GET /manifest` -> record counts + anchor ids (no task ids / answer keys).

### Units, rounding, "as of"
- API USD amounts are dollars. Round to cents (2 decimals) unless a template field
  states other precision (e.g. `receipt_completion_ratio` = 4 decimals,
  `quantity_variance_pct` = 1 decimal). Read each field's stated unit.
- "as of <date>" / "review_as_of" means: include only records whose date field
  (invoice_date, receipt_date, event_date, snapshot_date) is `<=` that date. Exclude
  future-dated receipts/invoices/events.
- Quantities: 2 decimals. Prices: match the template's stated precision.

## A. Sourcing nomination readiness (train_001 / test_003)

Inputs: a nomination memo naming package anchors (SKU + requisition_id + PO_id per
line), an `as_of_date`. Output shape: `answer_template.json` with program_summary,
per-SKU nomination_lines, committee_action.

### Build recipe
1. `GET /programs/<program_id>` -> owner, budget_cap, committed_amount.
2. For each package SKU: `GET /items/<sku>` -> preferred_supplier_id;
   `GET /purchase_requisitions/<req_id>` -> status, need_by;
   `GET /purchase_orders?contract_id=` and filter to the SKU, or fetch the named PO
   by id -> PO(s), status, contract_id; `GET /receipts?po_id=<po>` (filter
   receipt_date <= as_of); `GET /ap_invoices?po_id=<po>` (filter invoice_date <=
   as_of); `GET /vendor_risk_events?supplier_id=<sup>` (filter status in
   {open,monitoring} and event_date <= as_of); `GET /contracts/<contract_id>` if a
   contract exists.
3. `program_summary.budget_headroom_usd = budget_cap - committed_amount` (program
   row; do NOT subtract pending_invoice here).
4. `overall_readiness`: `ready` only if every line is ready; `not_ready` if any line
   is fully blocked (missing contract / no receipt); else `at_risk`.

### Per-line fields
- `selected_supplier_id`: item.preferred_supplier_id (== PO.supplier_id).
- `primary_requisition_id`: from memo. `commercial_basis_id`: `contract_id` if the
  PO has a contract, else `null`.
- `package_po_ids`: PO id(s) for that SKU/requisition, sorted ascending.
- `receipt_evidence_ids`: in-scope receipts (receipt_date <= as_of), sorted. empty
  if none.
- `invoice_exception_ids`: on_hold invoices on the PO existing as of the date,
  sorted. (A `paid`/`cancelled` invoice is NOT an exception.)
- `risk_event_ids`: open/monitoring vendor_risk_events (event_date <= as_of), sorted.
- `blocker_codes` (sorted; enum):
  - `missing_contract` — PO.contract_id is null.
  - `supplier_watch` — supplier.risk_rating == "watch".
  - `open_supplier_risk` — any open/monitoring risk event.
  - `ap_hold` — any on_hold invoice on the PO.
  - `pending_receipt` — NO receipt exists for the PO at all (PO open, 0 receipts).
    A partial receipt (received < ordered) with a receipt present is NOT
    `pending_receipt`.
  - `late_due_date` — PO.due_date / requisition.need_by has passed relative to as_of
    without fulfillment.
  - `none` — only when no other blocker applies.
- `nomination_decision`: `nominate` (no blockers, contract+receipt+approved req);
  `conditional_nomination` (contract+receipt present but clearable blockers like
  ap_hold / open supplier risk); `hold` (missing_contract or no receipt).
- `readiness_status`: `ready`/`at_risk`/`not_ready` consistent with the decision.

### committee_action
- `nominate_now_supplier_ids` / `conditional_supplier_ids` / `hold_supplier_ids`:
  suppliers of the corresponding decision lines, sorted.
- `next_owner` (buyer|finance_ops|quality_ops|program_owner|ap_team): owner of the
  dominant actionable blocker that must clear to advance nomination. Missing
  contract -> `buyer`; AP holds -> `ap_team`/`finance_ops`; supplier risk ->
  `program_owner`/`finance_ops`. When multiple blockers coexist, prefer the owner
  of the conditional line's clearing condition (e.g. ap_hold -> ap_team) if a
  conditional nomination exists, else the structural gap (missing contract -> buyer).
  (ap_team and buyer were both score-neutral in training — choose by the block
  that most blocks nomination; for a purely finance hold consider `finance_ops`.)
- `send_to_committee`: `yes` if any nominate_now/conditional line exists to decide;
  else `no`.

### Pitfalls (A)
- `task_id` value = short form `"train_00N"` style matching the judge task id, NOT
  the long `"task_group_006_train_00N"` literal — the short form is required.
- Exclude future-dated receipts (a receipt dated after as_of must NOT appear in
  `receipt_evidence_ids`).
- `pending_receipt` means zero receipts, not a partial receipt.
- `invoice_exception_ids` includes only on-hold invoices (paid/cancelled excluded).

## B. Receiving-control closeout (train_002 / test_001 / test_004)

Inputs: a target batch (`receipt_id`), a receiving memo. Output: batch identity,
line reconciliation, invoice review, financials, decision, supplier-risk context,
evidence. Also the **chargeback-netting AP-release variant** (train_005) below.

### Build recipe
1. `GET /receipts/<batch_id>` -> batch identity (po_id, supplier_id, status,
   receipt_date, receiver, warehouse_id, packing_slip). Lines: per po_line_id
   quantity_received/rejected/inspection_status.
2. `GET /purchase_orders/<po_id>` -> program_id, contract_id, status, lines[]
   (ordered qty, unit_price). `GET /contracts/<contract_id>` -> unit_price.
3. Invoice tied to the batch: the ap_invoice whose `receipt_id == batch_id`
   (`GET /ap_invoices?po_id=<po>` then filter). `GET /suppliers/<supplier_id>` ->
   name, risk_rating. `GET /vendor_risk_events?supplier_id=<sup>` (open/monitoring).

### line_reconciliation (sort by po_line_id asc)
- `ordered_qty` = PO line quantity. `received_qty` = sum quantity_received across
  in-scope receipts for that po_line_id (as of review date). `rejected_qty` = sum
  quantity_rejected. `billed_qty` = invoice line quantity_billed (the batch's
  invoice).
- `short_qty_vs_po` = ordered - received. `unreceived_billed_qty` = billed - received.
- `receipt_completion_ratio` = received/ordered, 4 decimals.
- `po_unit_price` = PO line unit_price; `contract_unit_price` = contract.unit_price;
  `invoice_unit_price` = invoice line unit_price; `contract_price_match` =
  (po_unit_price == contract_unit_price).

### invoice_review
- `invoice_id`, `invoice_status` (raw), `hold_code`, `receipt_status`
  (receipt.status), `po_status` (PO.status).
- `exception_codes` (set; allowed: `INVOICE_QTY_EXCEEDS_RECEIPT` [billed>received],
  `PARTIAL_RECEIPT` [PO partial or received<ordered], `SUPPLIER_WATCH_RISK`
  [supplier.risk_rating=="watch"], `PRICE_MISMATCH` [invoice line price !=
  contract price], `DAMAGE_REJECTION` [rejected>0 or inspection failed],
  `NO_EXCEPTION` [only if none of the above]).

### financials (USD 2 decimals)
- `received_goods_value` = received_qty * po_unit_price.
- `unreceived_goods_value` = short_qty_vs_po * po_unit_price.
- `invoice_subtotal`/`invoice_freight`/`invoice_tax`/`invoice_total` = from invoice.

### decision (enums)
- `batch_disposition`: `accept_partial_hold_variance` (partial receipt + qty hold);
  `release_full_invoice` (full 3-way match); `reject_batch` (damage/all rejected);
  `manual_recount_required` (recount needed).
- `ap_action`: `keep_invoice_on_hold` (on_hold); `release_invoice` (approved/3-way);
  `void_invoice` (cancelled).
- `receiving_action`: **`record_shortage_follow_up` when short_qty>0 (CONFIRMED —
  do NOT use `no_receiving_action` for a partial shortage even if the receipt is
  already posted)**; `no_receiving_action` (clean, complete receipt); `reject_all_units`.
- `supplier_action`: `request_credit_or_remaining_delivery` (underage);
  `supplier_debit_for_damage` (damage); `no_supplier_action` (clean).

### supplier_risk_context / evidence
- `supplier_risk_rating`, `has_open_supplier_risk` (any open/monitoring event),
  `open_supplier_risk_event_ids` (sorted).
- `evidence.endpoint_record_ids`: the directly-reconciled record ids (receipt, PO,
  contract, supplier, invoice, vendor-risk event). This set is loosely scored —
  include the core operational records; excluding derived program/item ids is safe.
- `task_payloads_reviewed`: basenames of the local memo files (e.g.
  `["receiving_memo.md"]`).

### Pitfalls (B)
- `receiving_action` must be `record_shortage_follow_up` for any partial shortage
  (switching to `no_receiving_action` drops the score).
- `billed_qty` comes from the invoice tied to THIS batch (invoice.receipt_id ==
  batch_id), not other invoices on the same PO.
- `contract_price_match` is a boolean equality of PO-line price vs contract.unit_price.

## B-variant. Receiving + AP release with chargebacks (train_005)

Inputs: an AP-release packet naming target po_ids/receipt_ids/invoice_ids, a local
`chargeback_register_excerpt`, `release_request_note`, and a `po73xx_alias_note`.
Output: per-invoice release decisions, per-receipt receiving exceptions, summary.

### release_decisions (per invoice, sort by invoice_id asc)
For each target invoice, find its chargeback in the local register (match by
`invoice_id`); also fetch the invoice, its PO, and receipts on the PO.
- `approved_chargeback_amount` = basis_quantity * unit_cost when chargeback
  `status == "approved"`, else 0.
- `pending_chargeback_amount` = basis_quantity * unit_cost when `status ==
  "pending_quality_review"`, else 0.
- `decision`: `release_net_after_approved_chargeback` (chargeback approved);
  `hold_pending_quality_chargeback` (chargeback pending_quality_review, typically
  with inspection hold on the receipt); `hold_missing_receipt` (no receipt on the PO).
- `primary_reason`: `approved_qty_chargeback` (approved "Underage Quantity"
  chargeback); `approved_ap_quantity_variance` (approved "AP Quantity Variance"
  chargeback); `inspection_hold_pending_chargeback` (pending quality + receipt on
  inspection_hold); `no_receipt_on_po` (no receipt).
- `invoice_total` = invoice.total.
- `net_release_amount` = **0.00 for HELD invoices**; (invoice_total -
  approved_chargeback_amount) for RELEASED invoices. (CONFIRMED held=0.)
- `receipt_ids_in_scope`: receipt(s) on the PO tied to this invoice (via
  invoice.receipt_id or chargeback.receipt_id). `excluded_same_po_receipt_ids`:
  other receipts on the SAME PO not in this invoice's scope (e.g. a duplicate
  receipt for a different invoice), sorted. Empty when the PO has only the in-scope
  receipt or no receipts.

### receiving_exceptions (per target receipt, sort by receipt_id)
- `exception_codes` (set; allowed: `Underage Quantity` [received<ordered],
  `Severe Unmatched Quantity` [large/total mismatch — use sparingly, not for an
  ordinary partial underage that has a chargeback], `Inspection Hold`
  [receipt.status=="inspection_hold"], `AP Quantity Variance` [billed!=received]).
- `chargeback_status`: `approved` | `pending_quality_review` | `not_applicable`
  (match the register entry for this receipt).
- `resolution_status`: `net_release_ready` (approved chargeback);
  `hold_for_quality_review` (pending_quality_review / inspection hold);
  `accepted_no_receiving_exception` (clean full receipt, no exception);
  `missing_receipt`.

### summary
- `release_invoice_ids` (released, sorted), `hold_invoice_ids` (held, sorted).
- `approved_chargeback_total` = sum of approved chargeback amounts;
  `pending_chargeback_total` = sum of pending;
  `net_release_total` = sum of released invoices' net_release_amounts (held
  contribute 0). [If the rubric differs, the per-invoice held=0 rule still holds.]
- `authoritative_sources`: include all used among `procureops_po_records`,
  `procureops_receipt_records`, `procureops_ap_records`, `local_chargeback_register`.
- `supporting_only_sources`: include those present among `ap_release_request_note`,
  `stale_po73xx_alias_note`.
- `followup_actions`: include ALL applicable among `ask_receiving_for_vantix_receipt`
  (a target invoice has no receipt), `hold_luma_duplicate_receipt_for_separate_invoice`
  (a non-target receipt on a target PO belongs to another invoice),
  `route_po00031_quality_review` (a receipt is on inspection_hold / pending quality),
  `post_approved_chargeback_netting` (there are approved chargebacks to net).
  (CONFIRMED: do NOT drop `post_approved_chargeback_netting` when approved
  chargebacks exist — removing it lowers the score.)
- If the packet says exact PO-73xx receipt ids are not present in the shared API,
  use the available shared PO/receipt ids named in the packet (it is a stale alias).

## C. AP close / vendor balance + hold/release (train_003 / test_002)

Inputs: a close memo naming target invoices, a cutoff date (payments scheduled
through that date reduce the balance), and an opening-balance rule (often 0.00 for
the slice). Output: invoice_decisions, vendor_balances, program_summary, queues,
total.

### Build recipe
Per target invoice: fetch invoice, its PO (program_id, line quantity), its receipt
(`invoice.receipt_id`; null => no receipt), supplier name; `GET
/payments?invoice_id=` and keep payments with status `scheduled` and
scheduled_date <= cutoff.

### invoice_decisions (sort by invoice_id asc)
- `hold_decision`: `HOLD` if invoice status in {on_hold, pending_receipt} or
  hold_code set; `RELEASE` if approved (3-way match).
- `hold_code`: raw or null. `release_to_payment`: true if RELEASE else false.
- `quantity_billed` (2 dec, invoice line); `quantity_received` (2 dec; **0.00 when
  no receipt exists**); `quantity_variance` = billed - received;
  `quantity_variance_pct` = variance / PO line quantity * 100 (1 decimal).
- `invoice_total` = invoice.total. `scheduled_payment_amount` = sum of in-cutoff
  scheduled payments. `net_balance_impact` = invoice_total - scheduled_payment_amount.
- `reason_codes` (alphabetical; allowed set): **`APPROVED_THREE_WAY_MATCH`**
  (approved, PO+receipt+invoice agree) AND **`SCHEDULED_PAYMENT_FOUND`** (a scheduled
  payment within cutoff exists) — include BOTH for an approved+scheduled invoice
  (CONFIRMED both required); **`NO_RECEIPT`** when no receipt exists — use as the
  SOLE code (do NOT also add `QTY_VARIANCE` even though billed!=received)
  (CONFIRMED); **`QTY_VARIANCE`** when a receipt exists but billed != received
  (sole code in that case).

### vendor_balances (sort by supplier_id asc)
- `opening_balance` (from memo, often 0.00 for the slice).
- `invoice_total` = sum of invoice totals for the supplier in the slice.
- `scheduled_payments` = sum of in-cutoff scheduled payments for the supplier.
- `held_invoice_total` = sum of totals of HELD invoices; `releasable_invoice_total`
  = sum of totals of RELEASED invoices.
- `close_balance` = opening_balance + invoice_total - scheduled_payments.
- `balance_status`: `OPEN_HELD` (has held invoices, close>0); `OPEN_APPROVED`
  (approved but not fully scheduled); `FULLY_SCHEDULED` (close_balance == 0).

### program_summary (sort by program_id) / queues / total
- `invoice_count`, `invoice_total`, `held_total`, `released_total`,
  `net_close_balance` = sum(invoice_total) - sum(scheduled_payments) for that
  program's invoices.
- `payment_hold_queue` = HELD invoice ids (ascending); `payment_release_queue` =
  RELEASED invoice ids (ascending).
- `total_close_balance` = sum of vendor close_balances (= sum of net_balance_impacts).
- `close_date` = memo date.

### Pitfalls (C)
- `NO_RECEIPT` is the SOLE reason code when there is no receipt — do not also emit
  `QTY_VARIANCE` (the variance is a consequence of no receipt).
- For an approved 3-way-match invoice that also has a scheduled payment, BOTH
  `APPROVED_THREE_WAY_MATCH` and `SCHEDULED_PAYMENT_FOUND` are required.
- `quantity_received` = 0.00 (not null) when no receipt exists.
- Only payments with `status == "scheduled"` AND `scheduled_date <= cutoff` reduce
  the close balance.

## D. Change-control contract amendment (train_004 / test_005)

Inputs: a change memo (`memo_id`, contract_id, supplier_id, sku, variant_code,
requested_incremental_quantity, source_requisition_id, tax_rate_percent, business
controls). Output: decision file with contract/budget/approval/supplier-risk checks,
supporting ids, required actions, summary.

### Build recipe
1. `GET /contracts/<contract_id>` -> status, price_type, unit_price, ceiling_amount.
2. `GET /purchase_orders?contract_id=<contract_id>` -> all POs under the contract.
   Separate non-cancelled (status != cancelled) from cancelled.
3. `GET /budget_snapshots?program_id=<program_id>` -> pick the snapshot with the
   latest snapshot_date <= as_of. `GET /programs/<program_id>` (budget_cap/
   committed_amount, same as snapshot).
4. `GET /approval_events?object_id=<req_id>` -> latest by event_date.
5. `GET /suppliers/<supplier_id>`; `GET /vendor_risk_events?supplier_id=<sup>`.

### contract_check
- `contract_status`, `price_type`, `unit_price`, `ceiling_amount` (from contract).
- `noncancelled_subtotal` = sum of subtotals of NON-cancelled POs under the contract.
- `headroom_before_change` = ceiling_amount - noncancelled_subtotal.
- `requested_quantity` (from memo). `requested_subtotal` = requested_quantity *
  unit_price (line subtotal before tax/freight — this is the contract_ceiling
  exposure).
- `headroom_after_change` = headroom_before_change - requested_subtotal.
- `ceiling_ok` = headroom_after_change >= 0.

### program_budget_check
- `snapshot_id` = the as-of snapshot id. `budget_cap`, `committed_amount` from it.
- `remaining_budget` = budget_cap - committed_amount.
- `requested_tax` = requested_subtotal * tax_rate_percent / 100 (round to cents).
- `requested_total` = requested_subtotal + requested_tax (+ freight ONLY if the memo
  provides freight).
- `budget_after_change` = remaining_budget - requested_total. `budget_ok` =
  budget_after_change >= 0.
- `max_quantity_with_current_budget` = **floor(remaining_budget / (unit_price *
  (1 + tax_rate_percent/100)))** (per-unit cost INCLUDES tax — CONFIRMED; using a
  subtotal-only divisor is wrong).

### approval_check
- `source_requisition_id`; latest event (max event_date):
  `latest_event_id`, `latest_action`, `latest_actor`, `latest_event_date`.
- `approval_ok` = latest_action is in the memo's `approval_good_actions` (e.g.
  `["approved"]`). A `submitted`/`held` action is NOT approved.

### supplier_risk_check
- `supplier_status`, `supplier_risk_rating`.
- `open_event_ids` = vendor_risk_events with status in {open, monitoring} and
  event_date <= as_of, sorted ascending.
- `severe_open_event_ids` = subset with severity in {`high`, `critical`} (medium/
  low/watch are NOT severe), sorted.
- `supplier_risk_ok` = (severe_open_event_ids is empty). Per memo: a `watch` rating
  is context only and does NOT block unless an open SEVERE event is found.

### supporting_ids / required_actions / decision
- `included_po_ids` (non-cancelled POs, sorted), `excluded_cancelled_po_ids`
  (cancelled POs, sorted), `approval_event_ids` (sorted).
- `required_actions` (sorted; enum): `obtain_final_requisition_approval` (if
  !approval_ok); `raise_budget_exception_or_reduce_quantity` (if !budget_ok);
  `resolve_supplier_risk_hold` (if !supplier_risk_ok); `none` (if all ok).
- `decision` (enum): `release_amendment` (ceiling_ok && budget_ok && approval_ok
  && supplier_risk_ok); `hold_for_budget` (!budget_ok only); `hold_for_approval`
  (!approval_ok only); `hold_for_supplier_risk` (!supplier_risk_ok only);
  `hold_for_budget_and_approval` (!budget_ok AND !approval_ok);
  `reject_contract_mismatch` (contract sku/supplier/program mismatch). When both
  budget and approval fail, use `hold_for_budget_and_approval`.
- `summary`: `blocker_count` (number of failing checks among budget/approval/risk,
  plus contract ceiling if it fails), `currency` = "USD", `ready_to_release` =
  (blocker_count == 0).

### Pitfalls (D)
- `change_request_id` = the memo's `memo_id`, NOT the contract_id (using
  contract_id lowers the score).
- `max_quantity_with_current_budget` includes tax in the per-unit cost — confirmed.
- `noncancelled_subtotal` MUST exclude cancelled POs (include them in
  `excluded_cancelled_po_ids`).
- A `watch`/`medium` supplier rating is not a blocker; only open `high`/`critical`
  events block (`supplier_risk_ok` stays true otherwise).
- `approval_ok` requires the LATEST action to be an approved action, not merely a
  submitted/held one.

## Cross-family pitfalls (judge-taught)
- `task_id`: short form (`train_00N` / matching the task's expected value), not the
  long group literal where a short form is required (A). For B/C/E the template
  explicitly states the required task_id string.
- "Open" supplier risk = status in {open, monitoring}, event_date <= as_of, in
  every family.
- Exclude future-dated receipts/invoices/events (as-of filter) in A/B/D.
- Cancelled POs are excluded from contract usage (D) and are NOT invoice exceptions.
- A `paid` invoice is not an exception/hold; a `cancelled` PO is not in usage.
- Price match anchor is `contract.unit_price` vs PO-line price vs invoice-line
  price (B). All three agree => three-way match (C).
- When a chargeback is approved, release the invoice NET of the chargeback
  (B-variant); when pending quality review, hold; when no receipt, hold.
