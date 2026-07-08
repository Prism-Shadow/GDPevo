# SKILL — ProcureOps ERP Procurement Reconciliation (task_group_006)

Transferable execution skill for the ProcureOps procurement benchmark. Covers four task families: sourcing nomination readiness, receiving-control closeout, AP close / vendor-balance + hold-release, and change-control contract amendment. All rules below were verified against the live API on 2026-07-02.

## 0. API conventions (read first)

- Base URL: `<remote-env-url>` (prompts say `127.0.0.1:8006` — same service at the remote host).
- List: `GET /<coll>` → `{"count":N,"results":[...]}`. **No `_limit`/pagination param** — unknown params are treated as field filters; an unknown param name returns 0 results. Only filter by real field names.
- By id: `GET /<coll>/<id>` → the record object.
- Field filters match **substring, case-insensitive**, including nested list values (e.g. `?po_id=PO-AX17-4481`). Combine `?field=value` with `&start=YYYY-MM-DD&end=YYYY-MM-DD` for the collection's date field (inclusive).
- Each collection has ONE date field that `start`/`end` apply to: receipts→`receipt_date`, ap_invoices→`invoice_date`, payments→`scheduled_date`, vendor_risk_events→`event_date`, purchase_orders→`order_date`, budget_snapshots→`snapshot_date`, approval_events→`event_date`.
- Do NOT pull whole collections. Fetch by id, or by one foreign-key filter (`po_id`, `contract_id`, `supplier_id`, `invoice_id`, `object_id`, `program_id`, `sku`), then filter client-side.

### Reconciliation chain (memorize)
PO → receipts (same `po_id`, multiple allowed) → invoices (`invoice.po_id` AND/OR `invoice.receipt_id`) → payments (`payment.invoice_id`).
Contract `unit_price` is the price-match anchor for PO line `unit_price` AND invoice line `unit_price`.
Program ↔ contracts/requisitions/POs/budget_snapshots/invoices (via `po.program_id`).
Supplier ↔ vendor_risk_events ↔ contracts/POs/invoices/payments.

### Amount / unit conventions (CRITICAL — read each template field)
- API amounts are **USD dollars** (e.g. `budget_cap 285000.0`).
- In these tasks every template amount field is "USD, rounded to cents" / "precision 2". That means a **2-decimal dollar value** (e.g. `22070.30`), NOT integer cents. Do **not** multiply by 100. Verify the template's wording per field; only convert if a field literally says "USD cents (integer)".
- Quantities: 2 decimals where the template asks; integer where it says integer.
- "Rounded to cents" = round half-up to 2 decimals.

## 1. Query recipes (by goal)

| Goal | Recipe |
|---|---|
| Program budget | `GET /programs/<program_id>` (budget_cap, committed_amount, owner) + `GET /budget_snapshots/<snapshot_id>` or filter `?program_id=` and pick `snapshot_date` ≤ as_of |
| Contract for a SKU/program | `GET /contracts?sku=<sku>` then keep the record with matching `program_id`, `supplier_id`, `status=="active"` |
| All POs under a contract | `GET /purchase_orders?contract_id=<contract_id>` (then split by `status=="cancelled"`) |
| Receipts for a PO | `GET /receipts?po_id=<po_id>` |
| Invoices for a PO | `GET /ap_invoices?po_id=<po_id>` |
| Payments for an invoice | `GET /payments?invoice_id=<invoice_id>` |
| Open supplier risk as of date | `GET /vendor_risk_events?supplier_id=<id>&end=<as_of>` then keep `status in {open, monitoring}` |
| Approval state of req/contract/invoice | `GET /approval_events?object_id=<id>` then sort by `event_date` (latest = current state) |
| Requisition | `GET /purchase_requisitions/<id>` (need_by drives late-due-date) |

## 2. Cross-cutting reconciliation rules

- **Ordered qty** = PO line `quantity`. **Received qty** = sum of `quantity_received` across in-scope receipt lines for that `po_line_id` (or 0 if no receipt). **Billed qty** = invoice line `quantity_billed`.
- **short_qty_vs_po** = ordered − received. **unreceived_billed_qty** = billed − received (≥0 when invoice bills beyond receipt).
- **receipt_completion_ratio** = received / ordered, 4 decimals.
- **quantity_variance** (AP) = billed − received. **quantity_variance_pct** = quantity_variance / ordered × 100, 1 decimal. (Denominator is the PO ordered qty, NOT billed.)
- **Price match**: `contract.unit_price` must equal PO line `unit_price` and invoice line `unit_price`. Mismatch → PRICE_MISMATCH / PRICE_VARIANCE.
- **Three-way match** = PO.qty == receipt.qty == invoice.qty AND all three unit prices agree AND a receipt exists.
- **Supplier risk**: `suppliers.risk_rating` (`watch`/`medium`/`low`/`critical`) is a *static* field. *Open* risk = vendor_risk_events with `status in {open, monitoring}` and `event_date <= as_of`. These are independent: a `low`-rated supplier can still have an open risk event (verified: SUP-VANTIX rating `low` but VRE-00009 open). **Severe** = `severity in {high, critical}` (medium is NOT severe).

---

## FAMILY A — Sourcing nomination readiness (train_001 → test_003)

### Inputs
- `as_of_date` (e.g. 2026-06-01) from the memo/prompt.
- Package anchors: per SKU, a `requisition_id` and `po_id` from the local memo. The API is source of truth.

### Per-line derivation (one nomination_line per package SKU)
1. `selected_supplier_id` = the package PO's `supplier_id` (cross-check `items.preferred_supplier_id`).
2. `primary_requisition_id` = the named requisition.
3. `commercial_basis_id`: `GET /contracts?sku=<sku>`; if an active contract exists for this program+supplier+sku → its `contract_id`, else `null`.
4. `package_po_ids`: the package PO id(s) for the line (sorted asc).
5. `receipt_evidence_ids`: `GET /receipts?po_id=<po_id>`, keep `receipt_date <= as_of_date`. Sorted asc. (Later receipts are excluded — verified: RCV-00001 dated after as_of is dropped.)
6. `invoice_exception_ids`: `GET /ap_invoices?po_id=<po_id>`; keep `invoice_date <= as_of_date` AND invoice is an exception (`hold_code != null` OR `status in {on_hold, pending_receipt}`). Paid/approved/cancelled with no hold are NOT exceptions. Sorted asc.
7. `risk_event_ids`: open/monitoring vendor_risk_events for `selected_supplier_id` with `event_date <= as_of_date`. Sorted asc.

### blocker_codes (enum, sorted asc; include `none` only if empty)
- `missing_contract` — `commercial_basis_id` is null.
- `pending_receipt` — no in-scope receipt exists for the package PO (PO `status` in {open, …} and `receipt_evidence_ids` empty).
- `late_due_date` — PO `due_date` > requisition `need_by` (PO will deliver after need-by). Compare dates only.
- `open_supplier_risk` — `risk_event_ids` non-empty (any open/monitoring event, regardless of severity).
- `supplier_watch` — `suppliers.risk_rating == "watch"` (static field, independent of open events).
- `ap_hold` — `invoice_exception_ids` non-empty.
- `none` — no blockers.

### readiness_status / nomination_decision mapping
- Any of {`missing_contract`, `pending_receipt`, `late_due_date`, severe `open_supplier_risk`} present → `not_ready` / `hold`.
  (Severe open risk = an open event with severity high/critical. A non-severe open event alone does NOT force `hold`.)
- Only soft blockers remain (`ap_hold`, `supplier_watch`, non-severe `open_supplier_risk`) → `at_risk` / `conditional_nomination`.
- No blockers (`none`) → `ready` / `nominate`.

### program_summary
- `owner` = programs.owner.
- `budget_headroom_usd` = `programs.budget_cap − programs.committed_amount`, 2 decimals. (Use the programs row, NOT the snapshot's pending_invoice_amount.)
- `overall_readiness`: `not_ready` if any line not_ready; else `at_risk` if any line at_risk; else `ready`.

### committee_action
- `nominate_now_supplier_ids` = suppliers of `nominate` lines (asc).
- `conditional_supplier_ids` = suppliers of `conditional_nomination` lines (asc).
- `hold_supplier_ids` = suppliers of `hold` lines (asc).
- `next_owner` (priority): if any conditional/at-risk line has `ap_hold` → `ap_team`; else if `open_supplier_risk`/`supplier_watch` only → `finance_ops`; else if `missing_contract` → `buyer`; else if `pending_receipt` → `quality_ops`/`receiving`; else `program_owner`.
- `send_to_committee`: `yes` iff `nominate_now_supplier_ids` non-empty (something fully ready), else `no`.

### Pitfalls (Family A)
- Don't use `pending_invoice_amount` from budget_snapshots for headroom — it double-counts and breaks readiness.
- Don't treat `risk_rating==watch` alone as `open_supplier_risk`; don't treat an open event on a `low`-rated supplier as absent.
- Filter receipts AND invoices by `<= as_of_date`; a same-PO later receipt (e.g. RCV-00001) is out of scope.
- `invoice_exception_ids` scope = the package PO(s), NOT all the supplier's invoices.
- `commercial_basis_id` only for an ACTIVE contract matching program+supplier+sku; expired/null contract → `missing_contract`.

---

## FAMILY B — Receiving-control closeout (train_002 → test_001 / test_004)

### Inputs
- `batch_id` (= receipt_id) from memo. as_of = memo export date.

### inspection_summary (from the batch receipt)
po_id, program_id (via PO), supplier_id, supplier_name (via /suppliers), warehouse_id, receipt_date, packing_slip, receiver — all copied from the receipt and its PO.

### line_reconciliation (one row per receipt line; sort by po_line_id asc)
- `ordered_qty` = PO line quantity for that po_line_id.
- `received_qty` = receipt line `quantity_received`.
- `rejected_qty` = receipt line `quantity_rejected`.
- `billed_qty` = invoice line `quantity_billed` for that po_line_id (from the invoice linked by `invoice.receipt_id` == batch, else `?po_id=`).
- `short_qty_vs_po` = ordered − received.
- `unreceived_billed_qty` = billed − received.
- `receipt_completion_ratio` = received / ordered (4 decimals).
- `po_unit_price` = PO line `unit_price`; `contract_unit_price` = contract.unit_price (contract via `po.contract_id`); `invoice_unit_price` = invoice line `unit_price`.
- `contract_price_match` = (contract_unit_price == po_unit_price == invoice_unit_price). Boolean.

### invoice_review (the invoice tied to the batch via invoice.receipt_id) and invoice_review
- `invoice_id`, `invoice_status`, `hold_code` (may be null), `receipt_status` (receipt.status), `po_status` (PO.status).
- `exception_codes` (set; allowed: INVOICE_QTY_EXCEEDS_RECEIPT, PARTIAL_RECEIPT, SUPPLIER_WATCH_RISK, PRICE_MISMATCH, DAMAGE_REJECTION, NO_EXCEPTION):
  - `INVOICE_QTY_EXCEEDS_RECEIPT` — billed > received.
  - `PARTIAL_RECEIPT` — PO.status == partial_receipt OR received < ordered.
  - `SUPPLIER_WATCH_RISK` — supplier.risk_rating == "watch".
  - `PRICE_MISMATCH` — invoice.unit_price != contract.unit_price (or PO unit_price).
  - `DAMAGE_REJECTION` — quantity_rejected > 0 OR any inspection_status == failed.
  - If none apply → `NO_EXCEPTION`.

### financials (USD, 2 decimals)
- `received_goods_value` = Σ(received_qty × po_unit_price).
- `unreceived_goods_value` = Σ((ordered − received) × po_unit_price).
- `invoice_subtotal`, `invoice_freight`, `invoice_tax`, `invoice_total` = copied from invoice record.

### decision (enums)
- `batch_disposition` [accept_partial_hold_variance | release_full_invoice | reject_batch | manual_recount_required]:
  - partial receipt + qty variance + accepted → `accept_partial_hold_variance`
  - full receipt + 3-way match + no hold → `release_full_invoice`
  - damage/rejection → `reject_batch`
  - disputed counts → `manual_recount_required`
- `ap_action` [keep_invoice_on_hold | release_invoice | void_invoice]: keep if invoice.status==on_hold or hold_code!=null; release if approved/3-way; void if rejected/duplicate.
- `receiving_action` [record_shortage_follow_up | no_receiving_action | reject_all_units]: shortage if received<ordered; none if clean; reject all if damage.
- `supplier_action` [request_credit_or_remaining_delivery | no_supplier_action | supplier_debit_for_damage]: credit/remaining delivery on shortage; debit on damage.

### supplier_risk_context
- `supplier_risk_rating` = suppliers.risk_rating.
- `has_open_supplier_risk` = any open/monitoring event with event_date <= as_of.
- `open_supplier_risk_event_ids` (set).

### evidence
- `endpoint_record_ids` = set of every record id touched (PO, receipt, invoice, contract, item sku, supplier, risk event). Evaluator sorts as a set — emit sorted.
- `task_payloads_reviewed` = set of payload file paths (e.g. `input/payloads/receiving_memo.md`).

### Receiving exception code derivation (also used by Family D-style release files)
When a local chargeback register is provided (Family B closeout may not have one; Family C-style release files do), tie exceptions to the chargeback row matching the receipt_id (or po_id):
- chargeback `reason_code=="Underage Quantity"` AND/OR received<ordered → add `Underage Quantity`.
- chargeback `reason_code=="Underage Quantity"` (receiving-side shortfall) AND billed>received → add `Severe Unmatched Quantity`.
- chargeback `reason_code=="AP Quantity Variance"` (AP-side billed>received, received==ordered case) → add `AP Quantity Variance`.
- receipt.status == `inspection_hold` → add `Inspection Hold`.
- chargeback basis: `Underage Quantity` = ordered − received; `AP Quantity Variance` = billed − received.

### Pitfalls (Family B)
- A receipt with `status="accepted_with_note"` still counts as a valid received receipt (don't exclude it).
- `packing_slip`/`receiver`/`warehouse_id` come from the receipt, not the PO.
- A same-PO later receipt is a DIFFERENT batch; do not merge its quantities into the batch under review.
- `unreceived_billed_qty` can be positive even when `short_qty_vs_po` is zero (AP over-bill).

---

## FAMILY C — AP close / vendor-balance + hold-release (train_003 → test_002)

### Inputs
- Target invoice ids (from memo). `close_date` = memo date. Memo states opening AP balance per supplier = 0.00.
- Payment cutoff: the memo names it (e.g. "through 2026-06-30"). Use that date, NOT close_date, for the scheduled-payment filter.

### invoice_decisions (one per target invoice; sort invoice_id asc)
For each invoice fetch: invoice, its PO, its receipt (invoice.receipt_id; if null → no receipt), its payments.
- `program_id`, `po_id`, `supplier_id`, `supplier_name` (via /suppliers), `invoice_status` (invoice.status).
- `quantity_billed` = invoice line qty. `quantity_received` = receipt line qty if receipt exists else `0.00`.
- `quantity_variance` = billed − received (2 decimals).
- `quantity_variance_pct` = quantity_variance / PO ordered × 100 (1 decimal). 0.0 when match; 100.0 when no receipt and full billed.
- `invoice_total` = invoice.total.
- `scheduled_payment_amount` = Σ payments.amount where `status in {scheduled, paid}` AND `scheduled_date <= cutoff` (0.00 if none).
- `net_balance_impact` = invoice_total − scheduled_payment_amount.
- `hold_code` = invoice.hold_code (null if none).
- `hold_decision` [HOLD | RELEASE]: `RELEASE` iff invoice.status=="approved" AND hold_code is null; else `HOLD`. (A non-approved status — on_hold, pending_receipt, cancelled — or any non-null hold_code forces HOLD. Three-way match governs the reason code below, not the release decision.)
- `release_to_payment` = (hold_decision == RELEASE).
- `reason_codes` (enum, sorted alphabetically; allowed: APPROVED_THREE_WAY_MATCH, NO_RECEIPT, QTY_VARIANCE, SCHEDULED_PAYMENT_FOUND):
  - `APPROVED_THREE_WAY_MATCH` — status approved AND three-way match (qty & price across PO/receipt/invoice).
  - `NO_RECEIPT` — invoice.receipt_id is null/empty (no linked receipt).
  - `QTY_VARIANCE` — hold_code=="QTY_VARIANCE" OR (receipt exists AND billed != received).
  - `SCHEDULED_PAYMENT_FOUND` — scheduled_payment_amount > 0.
  - (A single invoice can carry several codes; e.g. approved+matched+paid → [APPROVED_THREE_WAY_MATCH, SCHEDULED_PAYMENT_FOUND].)

### vendor_balances (one per supplier in slice; sort supplier_id asc)
- `opening_balance` = 0.00 (memo) unless memo says otherwise.
- `invoice_total` = Σ invoice_total for that supplier's invoices in slice.
- `scheduled_payments` = Σ scheduled_payment_amount for that supplier.
- `held_invoice_total` = Σ invoice_total where hold_decision==HOLD.
- `releasable_invoice_total` = Σ invoice_total where hold_decision==RELEASE.
- `close_balance` = opening_balance + invoice_total − scheduled_payments (2 decimals).
- `balance_status` [OPEN_HELD | OPEN_APPROVED | FULLY_SCHEDULED]:
  - `OPEN_HELD` if held_invoice_total > 0.
  - else `FULLY_SCHEDULED` if scheduled_payments >= invoice_total.
  - else `OPEN_APPROVED`.

### program_summary (one per program in slice; sort program_id asc)
- `invoice_count`, `invoice_total` = Σ invoice_total.
- `held_total` = Σ invoice_total where HOLD. `released_total` = Σ where RELEASE.
- `net_close_balance` = invoice_total − scheduled_payments (for that program).

### payment_hold_queue / payment_release_queue
- Lists of invoice_id strings: HOLD invoices / RELEASE invoices, each sorted asc.

### total_close_balance
- Σ vendor_balances.close_balance (== Σ program_summary.net_close_balance), 2 decimals.

### Pitfalls (Family C)
- Use the **payment cutoff date from the memo** (e.g. 2026-06-30), not close_date, for scheduled_date filter.
- `quantity_received` = 0.00 when invoice.receipt_id is null even if a receipt exists elsewhere on the PO (AP unlinked).
- `quantity_variance_pct` denominator is PO ordered qty, not billed.
- An `accepted_with_note` receipt is still a valid receipt for three-way match.
- Opening balance is 0.00 only because the memo says so; do not assume other slices.
- `pending_receipt` invoice status with no receipt → both `NO_RECEIPT` reason and `HOLD` decision; do NOT also emit `QTY_VARIANCE` unless hold_code==QTY_VARIANCE.

---

## FAMILY D — Change-control contract amendment (train_004 → test_005)

### Inputs
- `change_memo.json`: change_request_id, program_id, contract_id, supplier_id, sku, variant_code, `requested_incremental_quantity`, source_requisition_id, requested_ship_to, business_controls.
- business_controls give: `tax_rate_percent`, `currency`, approval_good_actions (e.g. ["approved"]), supplier_watch rule ("context only unless an open severe event is found"), existing_contract_usage = "exclude cancelled purchase orders", budget_exposure = line subtotal + tax (+freight only if memo provides freight), contract_ceiling_exposure = line subtotal before tax/freight.

### contract_check
- Fetch contract. `contract_status`, `price_type`, `unit_price`, `ceiling_amount` from it.
- `noncancelled_subtotal`: `GET /purchase_orders?contract_id=<contract_id>`; for each PO with `status != "cancelled"`, add `line.quantity × line.unit_price`. (Confirmed: statuses `confirmed`, `partial_receipt`, `received`, etc. are all INCLUDED; only `cancelled` excluded.)
- `headroom_before_change` = ceiling_amount − noncancelled_subtotal.
- `requested_quantity` = memo `requested_incremental_quantity`.
- `requested_subtotal` = requested_quantity × unit_price.
- `headroom_after_change` = headroom_before_change − requested_subtotal.
- `ceiling_ok` = headroom_after_change >= 0.

### program_budget_check
- `snapshot_id`: `GET /budget_snapshots?program_id=<program_id>`, pick `snapshot_date <= memo_date` (latest). (If a single canonical snapshot id like BUD-PRG-AX17 exists, use it.)
- `budget_cap`, `committed_amount` from that snapshot (== programs row values).
- `remaining_budget` = budget_cap − committed_amount.
- `requested_tax` = requested_subtotal × tax_rate_percent / 100 (2 decimals).
- `requested_total` = requested_subtotal + requested_tax (+ freight ONLY if the memo provides a freight figure; default no freight).
- `budget_after_change` = remaining_budget − requested_total.
- `budget_ok` = budget_after_change >= 0.
- `max_quantity_with_current_budget` = floor(remaining_budget / (unit_price × (1 + tax_rate_percent/100))). Integer, floor (not round).

### approval_check
- `GET /approval_events?object_id=<source_requisition_id>`. Sort by event_date asc; latest = current.
- `latest_event_id`, `latest_action`, `latest_actor`, `latest_event_date`.
- `approval_ok` = latest_action ∈ memo `approval_good_actions` (e.g. == "approved"). `submitted`/`held`/`rejected` → false.

### supplier_risk_check
- `supplier_status`, `supplier_risk_rating` from /suppliers.
- `open_event_ids`: open/monitoring events with event_date <= memo_date, sorted asc.
- `severe_open_event_ids`: subset with severity in {high, critical}, sorted asc.
- `supplier_risk_ok` = severe_open_event_ids is empty (per memo: watch rating is context only; only a severe open event blocks).

### supporting_ids (all sorted asc)
- `included_po_ids` = non-cancelled POs under the contract.
- `excluded_cancelled_po_ids` = cancelled POs under the contract.
- `approval_event_ids` = all approval_events for the source requisition.

### decision (enum: release_amendment | hold_for_budget | hold_for_approval | hold_for_supplier_risk | hold_for_budget_and_approval | reject_contract_mismatch)
Priority logic:
1. If `!ceiling_ok` → `reject_contract_mismatch` (contract cannot absorb the change).
2. Else if `!budget_ok` AND `!approval_ok` → `hold_for_budget_and_approval`.
3. Else if `!budget_ok` → `hold_for_budget`.
4. Else if `!approval_ok` → `hold_for_approval`.
5. Else if `!supplier_risk_ok` → `hold_for_supplier_risk`.
6. Else → `release_amendment`.

### required_actions (enum: obtain_final_requisition_approval | raise_budget_exception_or_reduce_quantity | resolve_supplier_risk_hold | none; sorted asc)
- `!approval_ok` → `obtain_final_requisition_approval`.
- `!budget_ok` → `raise_budget_exception_or_reduce_quantity`.
- `!supplier_risk_ok` → `resolve_supplier_risk_hold`.
- If none → `none`.

### summary
- `blocker_count` = count of false gates among {ceiling_ok, budget_ok, approval_ok, supplier_risk_ok}. (For decision purposes ceiling_ok=false counts; tune to the action set if ambiguous — train anchor: budget+approval false → 2.)
- `currency` = memo currency (USD).
- `ready_to_release` = (decision == release_amendment).

### Pitfalls (Family D)
- `noncancelled_subtotal` excludes ONLY `status=="cancelled"`; `confirmed`/`partial_receipt`/`received` POs count.
- `max_quantity_with_current_budget` floors and uses tax-inclusive unit cost; do not round up.
- `requested_total` includes freight ONLY if the memo carries freight; the change memo normally omits freight.
- `supplier_risk_ok` ignores `watch` rating and ignores non-severe (medium/low) open events.
- `approval_ok` uses the LATEST event action, not just any prior approval.
- Budget uses committed_amount (same as programs row), NOT committed + pending_invoice_amount.

---

## 3. Cross-cutting common misjudgments (avoid)
1. **Mixing headroom bases**: Family A/D budget headroom = budget_cap − committed_amount. Never subtract pending_invoice_amount.
2. **Risk double-counting**: `risk_rating` (static) vs open vendor_risk_events (dynamic) are separate; `open_supplier_risk` blocker/event-list uses the dynamic events; `supplier_watch` uses the static rating.
3. **Severity thresholds**: only high/critical are "severe"; medium open events do not block and do not force `hold`.
4. **Date scoping**: receipts and invoices are filtered by `<= as_of_date`; payments by the memo's payment cutoff (often month-end, NOT close_date).
5. **Cancelled-only exclusion**: contract usage excludes only `status=="cancelled"` POs; every other status counts toward subtotal/headroom.
6. **accepted_with_note receipts** are valid for three-way match and receiving evidence.
7. **Chargeback basis differs by reason**: Underage = ordered−received; AP Quantity Variance = billed−received.
8. **Quantity_variance_pct denominator** = PO ordered qty (not billed, not received).
9. **Exception invoice scope** = the package PO(s), not the whole supplier history.
10. **Amount units**: all templates here use 2-decimal USD dollars; "rounded to cents" ≠ integer cents. Don't ×100.

## 4. Output compliance checklist
- Return ONLY the JSON object matching the template; no prose.
- Fill every required key; use null where the template allows null (e.g. hold_code, commercial_basis_id).
- Sort every list unless the template says "set" (then still emit deduped; evaluator sorts).
- Round exactly as specified per field (2 decimals money, 4 decimals ratio, 1 decimal pct, integer counts/quantities where asked).
- `task_id` must equal the template's required value (e.g. `train_002`, `train_005`) — copy it verbatim.
- `evidence.endpoint_record_ids` / `authoritative_sources` etc. must list the actual records/sources used.
