# ProcureOps Procurement Control — Solver Skill (task_group_006)

Reusable workflow rules for solving Procurement Supplier & Receiving Control tasks against the shared ProcureOps API. Recipe-oriented experience; not candidate answers. Applies to all four task families: A Sourcing nomination, B Receiving-control closeout, C AP close / vendor-balance, D Change-control amendment, plus the cross-family Receiving/AP release file.

## 0. Environment & API mechanics

- Remote API (system of record): `<remote-env-url>`. Prompts that say `http://127.0.0.1:8006` mean THIS SAME remote service — always call the remote URL.
- Collections (GET list -> `{"count":N,"results":[...]}`; GET `/<coll>/<id>` -> the record object): `programs`, `suppliers`, `items`, `contracts`, `purchase_requisitions` (aliases `/purchase-requests`, `/purchase-requisitions`), `purchase_orders` (alias `/purchase-orders`), `receipts`, `ap_invoices` (alias `/ap/invoices`), `payments` (alias `/ap/payments`), `approval_events` (alias `/approvals`), `budget_snapshots` (alias `/budgets`), `vendor_risk_events` (alias `/vendor-risks`).
- Query filters match substring/case-insensitive (incl. nested list values); blank values ignored. `start`/`end` filter the collection's date field inclusively. There is NO pagination/`_limit` param — unknown params become field filters returning 0. Fetch by id from the memo/template; do not dump whole collections.
- `GET /manifest` gives record counts + anchor ids (no task ids / answer keys). `GET /health` confirms liveness.
- Reconciliation chain: Program -> contracts/requisitions/POs/budget_snapshots/invoices(via po.program_id). PO -> receipts(same po_id, multiples allowed) -> invoices(invoice.po_id / invoice.receipt_id) -> payments(payment.invoice_id). Contract(contract_id) <-> PO(po.contract_id) <-> PO line unit_price <-> invoice line unit_price (contract.unit_price is the price-match anchor).
- Units: USD amounts in records are DOLLARS. Read each answer_template's per-field unit/precision (some want cents, most want 2-decimal USD; qty 2 decimals; pct 1 decimal; ratios 4 decimals). Sort every ID list ascending; list fields marked "set" are compared as sets.

## Universal solver workflow
1. Read the prompt + the task-local memo/packet + `answer_template.json`. Extract: program_id, as-of/review date, target ids (POs/receipts/invoices/requisition/contract/supplier/sku), and any business-control rules (tax rate, approval good-actions, ceiling/budget exposure definitions, cancel-exclusion, supplier-watch policy).
2. Fetch each target id directly by id; fetch related records via filter (`?po_id=`, `?supplier_id=`, `?contract_id=`, `?sku=`, `?object_id=`, `?program_id=`, `?invoice_id=`). Fetch ALL POs on a contract (`?contract_id=`) and ALL receipts on a PO (`?po_id=`) — there can be multiple, including cancelled POs and duplicate/later receipts.
3. Apply the as-of date filter to every time-sensitive set: receipts (receipt_date <= as_of), invoices (invoice_date <= as_of), vendor_risk_events (event_date <= as_of AND status in {open, monitoring}), budget_snapshots (snapshot_date <= as_of, pick the latest), payments (scheduled_date <= cutoff given in memo, e.g. "through 2026-06-30").
4. Derive the fields per the family recipes below, using the enum/option sets EXACTLY as allowed. Round to the template's precision. Sort all lists.
5. Emit only the JSON object matching the template. No prose.

---

## Family A — Sourcing nomination readiness (scope + as-of, budget, per-SKU supplier decision, evidence/blockers, committee action)

Template shape: `task_id` ("task_group_006_train_001" / "task_group_006_test_003" pattern — use the exact required_value), `program_id`, `as_of_date` (memo date), `package_line_skus` (sorted), `program_summary` {owner, budget_headroom_usd, overall_readiness}, `nomination_lines[]` (matched by sku), `committee_action`.

Recipes:
- `as_of_date` = the memo date.
- `program_summary.owner` = programs.owner. `budget_headroom_usd` = `budget_cap - committed_amount` (programs row). `overall_readiness` = **WORST-CASE across the package lines** — if ANY anchor line is `not_ready`, overall = `not_ready`. Do NOT soften a not_ready line into an overall `at_risk` (confirmed: softening dropped the score).
- Per line (one per package anchor SKU):
  - `selected_supplier_id` = the PO's supplier_id (or item.preferred_supplier_id when no PO).
  - `primary_requisition_id` = the memo-named requisition (== po.requisition_id).
  - `commercial_basis_id` = the contract_id linked to the PO (`po.contract_id`); `null` when the PO has no contract.
  - `package_po_ids` = POs for this SKU/line (sorted).
  - `receipt_evidence_ids` = receipts for the PO with `receipt_date <= as_of` (sorted). Exclude later receipts.
  - `invoice_exception_ids` = invoices for the PO that are in AP-hold state as of as_of (sorted). Key on AP-hold status (see blocker note below).
  - `risk_event_ids` = vendor_risk_events for the supplier with status in {open, monitoring} AND event_date <= as_of (sorted). Supplier-level — include any open event for the supplier regardless of related_object_id.
  - `blocker_codes` (sorted) from this set: `missing_contract` (po.contract_id is null), `supplier_watch` (supplier.risk_rating == "watch"), `open_supplier_risk` (>=1 open/monitoring risk event as of as_of), `ap_hold` (an invoice for the PO has status == "on_hold"), `pending_receipt` (PO not fully received — no receipt OR received < ordered), `late_due_date` (po.due_date or requisition.need_by < as_of), `none`.
  - `nomination_decision`: `nominate` (no blockers; contract+receipt present) / `conditional_nomination` (commercial basis contract exists + receipt evidence present, but clearable exceptions like AP hold / partial receipt) / `hold` (hard blocker: missing_contract or no receipt).
  - `readiness_status`: `ready` (no blockers) / `at_risk` (clearable blockers, contract+receipt present) / `not_ready` (hard blocker).
- `committee_action`: `nominate_now_supplier_ids` (lines with nominate), `conditional_supplier_ids` (conditional_nomination), `hold_supplier_ids` (hold), all sorted. `next_owner` in {buyer, finance_ops, quality_ops, program_owner, ap_team}. `send_to_committee` in {yes, no}.
- CRITICAL blocker flag rule (confirmed across families): `ap_hold` keys on invoice status == `on_hold`. An invoice with status `pending_receipt` / hold_code `NO_RECEIPT` is a RECEIVING issue -> use the `pending_receipt` blocker, NOT `ap_hold`. Do not double-flag.

Pitfalls: overall_readiness must be worst-case (not a blend). missing_contract is a hard blocker -> hold/not_ready. A requisition may be `converted` while the approval_events show only `submitted` (see Family D) — for nomination, rely on the PO/contract/receipt evidence, not approval status. Watch-rated supplier with only a `medium` open risk still gets `supplier_watch` + `open_supplier_risk` blockers but is not a hard hold.

---

## Family B — Receiving-control closeout (batch identity, receipt scope, ordered/received/billed reconciliation, price match, AP hold/release, financials, supplier-risk overlay, chargeback)

Template shape: `task_id`, `batch_id`, `inspection_summary`, `line_reconciliation[]` (sort by po_line_id), `invoice_review`, `financials`, `decision`, `supplier_risk_context`, `evidence`.

Recipes:
- `batch_id` = the receipt under review (from the memo).
- The invoice in scope = the `ap_invoice` whose `receipt_id == batch_id` (fetch `?po_id=` for the batch's PO, pick the invoice tied to this receipt). Other invoices on the same PO tie to OTHER receipts -> out of scope for this batch.
- `inspection_summary`: po_id, supplier_id, warehouse_id, receipt_date, packing_slip, receiver from the BATCH receipt; program_id from the PO; supplier_name from the supplier.
- `line_reconciliation` per po_line_id present in the BATCH receipt:
  - `ordered_qty` = PO line quantity.
  - `received_qty` = **the BATCH's receipt line `quantity_received`** (NOT cumulative across all PO receipts; only this batch, and only receipts with receipt_date <= review).
  - `rejected_qty` = batch receipt line `quantity_rejected`.
  - `billed_qty` = the in-scope invoice line `quantity_billed`.
  - `short_qty_vs_po` = ordered - received. `unreceived_billed_qty` = billed - received.
  - `receipt_completion_ratio` = received / ordered (4 decimals).
  - `po_unit_price` (PO line) / `contract_unit_price` (contract.unit_price for po.contract_id) / `invoice_unit_price` (invoice line). `contract_price_match` = (contract_unit_price == po_unit_price).
- `invoice_review`: invoice_id, invoice_status, hold_code (string or null), receipt_status (the BATCH receipt.status), po_status (PO.status), `exception_codes` (set; evaluator sorts).
- `exception_codes` (allowed: INVOICE_QTY_EXCEEDS_RECEIPT, PARTIAL_RECEIPT, SUPPLIER_WATCH_RISK, PRICE_MISMATCH, DAMAGE_REJECTION, NO_EXCEPTION) — include EVERY true condition:
  - INVOICE_QTY_EXCEEDS_RECEIPT: billed > received.
  - PARTIAL_RECEIPT: received < ordered.
  - SUPPLIER_WATCH_RISK: supplier.risk_rating == watch (and/or an open risk event). **INCLUDE this code even though supplier_risk_context separately reports risk** (confirmed: dropping it lowered the score).
  - PRICE_MISMATCH: contract/PO/invoice unit prices differ.
  - DAMAGE_REJECTION: quantity_rejected > 0 or inspection failure.
  - NO_EXCEPTION: only when none of the above apply.
- `financials` (USD, 2 decimals): `received_goods_value` = received_qty × po_unit_price; `unreceived_goods_value` = (ordered - received) × po_unit_price (equivalently (billed - received) × price when billed=ordered); `invoice_subtotal`/`invoice_freight`/`invoice_tax`/`invoice_total` from the in-scope invoice record.
- `decision`:
  - `batch_disposition` (accept_partial_hold_variance / release_full_invoice / reject_batch / manual_recount_required): partial receipt accepted with an invoice qty-variance hold -> `accept_partial_hold_variance`.
  - `ap_action` (keep_invoice_on_hold / release_invoice / void_invoice): qty-variance hold -> `keep_invoice_on_hold`.
  - `receiving_action` (record_shortage_follow_up / no_receiving_action / reject_all_units): shortage (received < ordered) -> `record_shortage_follow_up`.
  - `supplier_action` (request_credit_or_remaining_delivery / no_supplier_action / supplier_debit_for_damage): underage (billed but unreceived) -> `request_credit_or_remaining_delivery`; damage -> `supplier_debit_for_damage`.
- `supplier_risk_context`: `supplier_risk_rating`, `has_open_supplier_risk` (>=1 open/monitoring event as of review), `open_supplier_risk_event_ids` (sorted).
- `evidence.endpoint_record_ids`: include the core records used (PO, receipt, invoice, contract, supplier, program, risk event). This field is subset-checked (extras tolerated; missing required ones hurt). `task_payloads_reviewed`: the memo filename(s).

Pitfalls: received_qty is the BATCH's only — do not sum later/duplicate receipts. Only the invoice with receipt_id == batch_id is in scope. exception_codes is a comprehensive flag set; include SUPPLIER_WATCH_RISK for watch suppliers. For an accepted partial receipt with billed>received (underage): accept_partial_hold_variance / keep_invoice_on_hold / record_shortage_follow_up / request_credit_or_remaining_delivery (this matches an approved "Underage Quantity" chargeback).

---

## Family C — AP close / vendor-balance + hold/release (invoice hold/release, qty-variance %, totals & scheduled payments & net balance, vendor balance rows, program close totals, payment queues)

Template shape: `task_id`, `close_date`, `invoice_decisions[]` (invoice_id ascending), `vendor_balances[]` (supplier_id ascending), `program_summary[]` (program_id ascending), `payment_hold_queue`, `payment_release_queue`, `total_close_balance`.

Recipes (slice = the named target invoices only):
- `close_date` = memo date. Opening AP balance for target suppliers in this slice = `0.00` (per memo). Scheduled payments through the memo cutoff (e.g. 2026-06-30) reduce the close balance.
- `invoice_decisions` per target invoice:
  - `hold_decision`: invoice.status `approved` -> `RELEASE`; `on_hold` -> `HOLD`; `pending_receipt` -> `HOLD`.
  - `hold_code`: from invoice (string or null).
  - `release_to_payment`: true for RELEASE, false for HOLD.
  - `quantity_billed` = invoice line quantity_billed (2 decimals).
  - `quantity_received` = the invoice's receipt line quantity_received (invoice.receipt_id -> receipt line); **`0.00` when receipt_id is null / no receipt**.
  - `quantity_variance` = billed - received.
  - `quantity_variance_pct` = variance / **PO quantity** × 100 (PO line quantity is the denominator), 1 decimal.
  - `invoice_total` = invoice.total.
  - `scheduled_payment_amount` = sum of payments for this invoice with status `scheduled` AND scheduled_date <= cutoff (memo "through YYYY-MM-DD").
  - `net_balance_impact` = invoice_total - scheduled_payment_amount.
  - `reason_codes` (alphabetical; allowed: APPROVED_THREE_WAY_MATCH, NO_RECEIPT, QTY_VARIANCE, SCHEDULED_PAYMENT_FOUND):
    - APPROVED_THREE_WAY_MATCH: PO qty == received == billed AND all unit prices match -> RELEASE reason.
    - SCHEDULED_PAYMENT_FOUND: a scheduled payment exists for this invoice (affects net balance).
    - NO_RECEIPT: invoice has no receipt (receipt_id null). **NO_RECEIPT SUBSUMES QTY_VARIANCE — when there is no receipt, emit `[NO_RECEIPT]` ONLY; do NOT also emit QTY_VARIANCE** (the variance is a consequence of no receipt). Confirmed: this was the single fix to reach a perfect score.
    - QTY_VARIANCE: receipt exists but billed != received.
  - 3-way match test: PO line qty == receipt qty == invoice billed qty AND PO/contract/invoice unit prices all equal.
- `vendor_balances` per target supplier (one row each):
  - `opening_balance` = 0.00 (slice).
  - `invoice_total` = sum of this supplier's target invoice totals.
  - `scheduled_payments` = sum of this supplier's target invoices' scheduled payments (through cutoff).
  - `held_invoice_total` = sum of HOLD-decision invoice totals (includes on_hold AND pending_receipt invoices — both are blocked).
  - `releasable_invoice_total` = sum of RELEASE-decision (approved) invoice totals.
  - `close_balance` = opening_balance + invoice_total - scheduled_payments.
  - `balance_status` (OPEN_HELD / OPEN_APPROVED / FULLY_SCHEDULED): approved AND a scheduled payment fully covers it -> `FULLY_SCHEDULED`; approved but not yet scheduled -> `OPEN_APPROVED`; has any held invoice -> `OPEN_HELD`.
- `program_summary` per program (group target invoices by po.program_id):
  - `invoice_count`, `invoice_total` (sum), `held_total` (HOLD invoices), `released_total` (RELEASE invoices), `net_close_balance` = sum of that program's supplier close_balances (= invoice_total - scheduled_payments for the program).
- `payment_hold_queue` = HOLD-decision invoice_ids (ascending). `payment_release_queue` = RELEASE-decision invoice_ids (ascending).
- `total_close_balance` = sum of all vendor close_balances.

Pitfalls: variance_pct denominator is PO quantity (not received/billed). received=0 when no receipt. NO_RECEIPT subsumes QTY_VARIANCE. held_invoice_total includes pending_receipt invoices. FULLY_SCHEDULED requires the scheduled payment to cover the approved invoice. A "converted" requisition is irrelevant here — use the invoice/receipt/payment records.

---

## Family D — Change-control contract amendment (contract status/price/qty, usage & headroom/ceiling, program-budget incremental exposure, requisition approval state, supplier risk, hold actions, final decision)

Template shape: `change_request_id`, `program_id`, `contract_id`, `sku`, `supplier_id`, `variant_code`, `decision`, `contract_check`, `program_budget_check`, `approval_check`, `supplier_risk_check`, `supporting_ids`, `required_actions`, `summary`.

Recipes:
- `change_request_id` = memo `memo_id`.
- `contract_check`:
  - `contract_status`, `price_type`, `unit_price`, `ceiling_amount` from the contract.
  - `noncancelled_subtotal` = sum of **line subtotals (qty × unit_price)** of NON-CANCELLED POs on the contract (fetch `?contract_id=`; exclude status == `cancelled`). This is the "contract ceiling exposure = line subtotal before tax and freight" per memo business_controls.
  - `requested_quantity` = memo `requested_incremental_quantity`.
  - `requested_subtotal` = requested_quantity × contract unit_price (no price change unless the memo states one).
  - `headroom_before_change` = ceiling_amount - noncancelled_subtotal.
  - `headroom_after_change` = ceiling_amount - (noncancelled_subtotal + requested_subtotal).
  - `ceiling_ok` = headroom_after_change >= 0.
- `program_budget_check`:
  - `snapshot_id` = budget_snapshot for the program with snapshot_date <= memo_date (latest). `budget_cap`, `committed_amount` from that snapshot.
  - `remaining_budget` = budget_cap - committed_amount.
  - `requested_tax` = requested_subtotal × tax_rate_percent (memo business_controls.tax_rate_percent, e.g. 7.25 -> 0.0725).
  - `requested_total` = requested_subtotal + requested_tax (+ freight ONLY if the memo provides freight).
  - `budget_after_change` = remaining_budget - requested_total.
  - `budget_ok` = budget_after_change >= 0.
  - `max_quantity_with_current_budget` = floor(remaining_budget / (unit_price × (1 + tax_rate_percent))) — per-unit cost includes tax.
- `approval_check`:
  - `source_requisition_id` = memo source requisition.
  - Fetch `approval_events?object_id=<requisition_id>`. `latest_event_id`/`latest_action`/`latest_actor`/`latest_event_date` = the latest event.
  - `approval_ok` = latest_action is in memo `business_controls.approval_good_actions` (e.g. `["approved"]`). **Use approval_events, NOT the requisition status** — a requisition may be `converted` while its latest approval event is only `submitted` -> approval_ok = false (confirmed).
- `supplier_risk_check`:
  - `supplier_status`, `supplier_risk_rating` from supplier.
  - `open_event_ids` = vendor_risk_events for the supplier with status in {open, monitoring} AND event_date <= memo_date (sorted).
  - `severe_open_event_ids` = open events with severity `high` or `critical` (medium/low are NOT severe) (sorted).
  - `supplier_risk_ok` = (severe_open_event_ids is empty). Per memo: a `watch` rating is **context only** unless an OPEN SEVERE event exists — so a watch supplier with only a `medium` open event is still `supplier_risk_ok = true`.
- `supporting_ids`: `included_po_ids` (non-cancelled POs on the contract, sorted), `excluded_cancelled_po_ids` (cancelled POs on the contract, sorted), `approval_event_ids` (for the requisition, sorted).
- `decision` (release_amendment / hold_for_budget / hold_for_approval / hold_for_supplier_risk / hold_for_budget_and_approval / reject_contract_mismatch):
  - `ceiling_ok` false -> `reject_contract_mismatch`.
  - else combine failing checks: budget + approval both fail -> `hold_for_budget_and_approval`; budget only -> `hold_for_budget`; approval only -> `hold_for_approval`; supplier risk only -> `hold_for_supplier_risk`; all ok -> `release_amendment`.
- `required_actions` (sorted; allowed: obtain_final_requisition_approval, raise_budget_exception_or_reduce_quantity, resolve_supplier_risk_hold, none): add one per failing check (approval -> obtain_final_requisition_approval; budget -> raise_budget_exception_or_reduce_quantity; risk -> resolve_supplier_risk_hold); `none` only when all ok.
- `summary`: `blocker_count` = number of failing checks (ceiling/budget/approval/supplier_risk — but ceiling_ok false is reject_contract_mismatch, counted as a blocker too); `currency` = USD; `ready_to_release` = (blocker_count == 0).

Pitfalls: noncancelled_subtotal excludes cancelled POs (a contract can have several POs, some cancelled). approval_ok is event-based, not status-based. supplier_risk_ok needs an OPEN SEVERE event; medium doesn't block. requested_total includes estimated tax at the memo's tax_rate; include freight only if the memo provides it. max_quantity divides remaining budget by the tax-inclusive per-unit cost.

---

## Cross-family — Receiving/AP release file (per-invoice release decision net of chargebacks, receiving exceptions, chargeback netting, source classification, followups)

Template shape: `task_id`, `review_as_of`, `target_ids` (sorted), `release_decisions[]`, `receiving_exceptions[]`, `summary`.

This family combines a LOCAL chargeback register excerpt (in the packet) with ProcureOps PO/receipt/AP records. Map each chargeback row to its invoice + receipt + PO.

Recipes:
- `release_decisions` per target invoice (sorted by invoice_id):
  - `decision`: `release_net_after_approved_chargeback` (chargeback status `approved` -> release invoice net of the approved chargeback) / `hold_missing_receipt` (no receipt on the PO, no chargeback) / `hold_pending_quality_chargeback` (chargeback status `pending_quality_review` and/or receipt status `inspection_hold`).
  - `primary_reason`: `approved_qty_chargeback` (chargeback reason "Underage Quantity", approved) / `approved_ap_quantity_variance` (chargeback reason "AP Quantity Variance", approved) / `no_receipt_on_po` (no receipt) / `inspection_hold_pending_chargeback` (pending quality / inspection hold).
  - `approved_chargeback_amount` = basis_quantity × unit_cost for the invoice's chargeback with status `approved`.
  - `pending_chargeback_amount` = basis_quantity × unit_cost for the invoice's chargeback with status `pending_quality_review`.
  - `net_release_amount` = **0.00 for HELD invoices** (hold_missing_receipt / hold_pending_quality_chargeback); = invoice_total - approved_chargeback_amount for RELEASED invoices. Confirmed: using the computed net for held invoices lowered the score — held releases nothing.
  - `receipt_ids_in_scope` = the target receipt(s) tied to this invoice (via the invoice's receipt_id OR the chargeback's receipt_id), sorted.
  - `excluded_same_po_receipt_ids` = other receipts on the same PO that are NOT in the packet's target receipt set (e.g. a duplicate receipt for a separate invoice), sorted.
- `receiving_exceptions` per target receipt (sorted by receipt_id):
  - `exception_codes` (zero or more of: Underage Quantity, Severe Unmatched Quantity, Inspection Hold, AP Quantity Variance): map from the chargeback reason + receipt status. "Underage Quantity" -> Underage Quantity (received < ordered). "AP Quantity Variance" -> AP Quantity Variance (billed > received with received == ordered). Receipt status `inspection_hold` -> add Inspection Hold. Sort alphabetically within the list.
  - `chargeback_status` (approved / pending_quality_review / not_applicable) = the chargeback's status for this receipt's invoice.
  - `resolution_status` (net_release_ready / hold_for_quality_review / accepted_no_receiving_exception / missing_receipt): approved chargeback -> `net_release_ready`; pending_quality_review / inspection_hold -> `hold_for_quality_review`; no exception -> `accepted_no_receiving_exception`; no receipt on the PO -> `missing_receipt`.
- `summary`:
  - `release_invoice_ids` (RELEASE decisions, sorted), `hold_invoice_ids` (HOLD decisions, sorted).
  - `approved_chargeback_total` = sum of approved_chargeback_amount across all invoices.
  - `pending_chargeback_total` = sum of pending_chargeback_amount across all invoices.
  - `net_release_total` = sum of net_release_amount **for RELEASED invoices only** (= released nets; held contribute 0).
  - `authoritative_sources` (one or more of: procureops_po_records, procureops_receipt_records, procureops_ap_records, local_chargeback_register): include the ProcureOps record sources AND `local_chargeback_register` (the chargeback register drives the netting — it is authoritative, not supporting).
  - `supporting_only_sources` (one or more of: ap_release_request_note, stale_po73xx_alias_note): requester comment notes and stale alias notes are supporting/context only.
  - `followup_actions` (one or more of: ask_receiving_for_vantix_receipt, hold_luma_duplicate_receipt_for_separate_invoice, route_po00031_quality_review, post_approved_chargeback_netting): include each applicable action — ask receiving for a missing receipt; hold/segregate a duplicate same-PO receipt for its separate invoice; route an inspection-hold receipt to quality review; post the approved-chargeback netting for released invoices. Sort ascending.

Pitfalls: net_release_amount is 0 for held invoices (not invoice - chargeback). net_release_total sums only released. A receipt can be `accepted` but still have an Underage Quantity chargeback (received < ordered) -> net_release_ready. received == ordered but billed > received -> AP Quantity Variance (not Underage). A receipt on `inspection_hold` adds Inspection Hold to exception_codes. The local chargeback register is authoritative for chargeback amounts. When a PO-73xx-style receipt is mentioned but no id exists, treat as no receipt (hold_missing_receipt) and ask receiving for the receipt.

---

## Quick decision-logic reference (confirmed by judge feedback)
- AP-hold judgment keys on invoice status `on_hold`; `pending_receipt`/`NO_RECEIPT` is a receiving (pending_receipt) issue, not an AP hold.
- exception_codes (receiving) is comprehensive — include SUPPLIER_WATCH_RISK for watch suppliers even though supplier_risk_context reports risk separately.
- reason_codes (AP close): NO_RECEIPT subsumes QTY_VARIANCE — never emit both for one invoice.
- overall nomination readiness = worst line readiness (no softening).
- approval_ok uses approval_events latest action (submitted != approved), regardless of requisition status.
- supplier_risk_ok requires an OPEN SEVERE (high/critical) event; watch rating + medium event does NOT block.
- noncancelled_subtotal excludes cancelled POs.
- net_release_amount is 0 for held release-file invoices.
- received_qty in a batch closeout is the batch's own receipt qty (date-filtered), not cumulative.
