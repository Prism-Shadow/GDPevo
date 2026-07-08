# SKILL — ProcureOps Procurement Supplier & Receiving Control (task_group_006)

Transferable, executable experience for solving ProcureOps procurement-control tasks against the
shared ProcureOps API. Covers four task families that appear in this scenario:

- **Family A — Sourcing nomination readiness packet** (program scope + as-of date, budget/readiness, per-SKU supplier commercial decisions, evidence/blocker sets, committee action).
- **Family B — Receiving-control closeout** (batch identity, receipt scope, ordered↔received↔billed reconciliation, contract/PO/invoice price match, AP hold/release, financial totals, supplier-risk overlay, **chargeback release file**).
- **Family C — AP close / vendor-balance + hold/release settlement** (invoice-level hold/release, qty-variance %, totals & scheduled payments & net balance, vendor balance rows, program close totals, payment hold/release queues).
- **Family D — Change-control contract amendment** (contract status/price/qty, usage & headroom/ceiling, program-budget incremental exposure, requisition approval state, supplier risk, hold actions, final decision).

This is experience, not a restatement of any answer. Follow the recipes; verify every value against the API.

---

## 0. Environment & API reference

### Base URL
- **Remote (use this):** `<remote-env-url>`
- Prompts say `http://127.0.0.1:8006` — that is the **same service** at the remote host. Always use the remote URL.

### Collections (GET list + GET by id)
| Collection | Path | ID field | Date field |
| --- | --- | --- | --- |
| programs | `/programs` | program_id | — |
| suppliers | `/suppliers` | supplier_id | — |
| items | `/items` | sku | — |
| contracts | `/contracts` | contract_id | effective_date |
| purchase_requisitions | `/purchase_requisitions` (aliases `/purchase-requests`, `/purchase-requisitions`) | requisition_id | need_by |
| purchase_orders | `/purchase_orders` (alias `/purchase-orders`) | po_id | order_date |
| receipts | `/receipts` | receipt_id | receipt_date |
| ap_invoices | `/ap_invoices` (also `/ap/invoices`) | invoice_id | invoice_date |
| payments | `/payments` (also `/ap/payments`) | payment_id | scheduled_date |
| approval_events | `/approval_events` (alias `/approvals`) | event_id | event_date |
| budget_snapshots | `/budget_snapshots` (alias `/budgets`) | snapshot_id | snapshot_date |
| vendor_risk_events | `/vendor_risk_events` (alias `/vendor-risks`) | event_id | event_date |

### Query semantics (verified)
- `GET /<coll>/<id>` → returns the single record object directly.
- `GET /<coll>?<field>=<value>` → returns `{"count": N, "results": [...]}`.
- Field filters match **substring, case-insensitive**, including nested list values. Blank values are ignored.
- Date range: `GET /<coll>?start=YYYY-MM-DD&end=YYYY-MM-DD` (inclusive) on that collection's date field.
- Useful filters by relationship: `?po_id=`, `?supplier_id=`, `?invoice_id=`, `?program_id=`, `?contract_id=`, `?sku=`, `?object_id=` (approvals), `?object_type=` (approvals).
- `GET /manifest` → record counts + anchor ids (no task/answer keys). `GET /health` → ok/seed.

### Determining record scope — **as-of date filtering is the #1 source of error**
Many tasks specify an `as_of_date` / `close_date` / `review_as_of`. Apply it consistently:
- **Receipts:** include only `receipt_date <= as_of`.
- **AP invoices:** include only `invoice_date <= as_of`.
- **Budget snapshot:** pick the snapshot with `snapshot_date <= as_of` (latest ≤ as_of). All snapshots here are dated `2026-06-01`.
- **Vendor risk events:** `event_date <= as_of` **AND** `status == "open"` for "open risk". (Do **not** treat `monitoring` or `closed` as open.)
- **Approval events:** `event_date <= as_of`; take the latest by date for "latest action".
- **Payments (AP close):** the close memo defines a payment window (e.g. "scheduled through 2026-06-30"). Include only `status == "scheduled"` payments with `scheduled_date <= window_end`.

### Rounding
- USD amounts → round to 2 decimals (cents) in the final answer. Keep full precision in intermediate steps to avoid cent drift.

---

## 1. Cross-cutting data model & linkage

```
program ──┬── budget_snapshot (snapshot_id=BUD-<program_id>, budget_cap, committed_amount, pending_invoice_amount)
          ├── contracts (program_id, sku, supplier_id, unit_price, ceiling_amount, price_type, status)
          ├── purchase_requisitions (program_id, sku, need_by, status, priority, requester)
          └── purchase_orders (program_id, supplier_id, contract_id, requisition_id, lines[], subtotal/tax/total)

purchase_order ──┬── receipts (po_id, supplier_id, lines[].quantity_received/rejected, status, receipt_date)
                 └── ap_invoices (po_id, supplier_id, receipt_id [nullable], lines[].quantity_billed, hold_code, status, subtotal/freight/tax/total)

ap_invoice ─── payments (invoice_id, amount, scheduled_date, status)

supplier ─── vendor_risk_events (supplier_id, severity, status, event_type, related_object_id)

purchase_requisition ─── approval_events (object_id=requisition_id, object_type="requisition", action, actor, event_date)
```

### Key field facts
- `purchase_orders.lines[]`: `{line_id, sku, description, quantity, unit_price}`. `quantity` = **ordered**. PO also has `subtotal`, `tax`, `total` ( subtotal+tax; **freight lives on the invoice, not the PO** in this data).
- `purchase_orders.status` enum: `open, confirmed, partial_receipt, received, closed, cancelled`. **`cancelled` POs are excluded from contract-usage/nomination scope** but still listed as "excluded".
- `receipts.lines[]`: `{po_line_id, sku, quantity_received, quantity_rejected, inspection_status}`. Receipt-level: `status` = `accepted | accepted_with_note | inspection_hold`.
- `ap_invoices.lines[]`: `{po_line_id, sku, quantity_billed, unit_price}`. Invoice-level: `status` = `on_hold | pending_receipt | approved | paid | entered`; `hold_code` = `QTY_VARIANCE | NO_RECEIPT | PRICE_VARIANCE | SUPPLIER_REVIEW | null`; money = `subtotal` + `freight` + `tax` = `total`.
- `ap_invoices.receipt_id` is **nullable** — a pending_receipt invoice has `receipt_id: null`. To find the matching receipt, query `/receipts?po_id=<po_id>`.
- `contracts.price_type` = `fixed | indexed | not_to_exceed`. `unit_price` is the contract price; `ceiling_amount` is the not-to-exceed spend cap.
- `suppliers.risk_rating` = `low | medium | watch | high`. `vendor_risk_events.severity` = `low | medium | high` (treat `high`—and `critical` if ever present—as **severe**). `vendor_risk_events.status` = `open | monitoring | closed`.
- `approval_events.action` = `submitted | approved | returned | escalated`. `object_type` = `requisition`, `object_id` = requisition_id.
- `payments.status` = `scheduled | released | blocked`.

### Authority of sources (for evidence/source-list fields)
- **Authoritative:** ProcureOps API records (PO, receipt, invoice, payment, contract, supplier, program, budget, approval, vendor-risk) + the **task-local chargeback register** (chargebacks are NOT in the API — they live in the input payload).
- **Supporting-only (narrative, do not net against):** release-request notes, "stale alias" notes (e.g. PO-73xx alias notes), dock-handoff memos. Use them for context/follow-up actions only.

---

## 2. Reconciliation primitives (used by every family)

### Quantity
- `ordered_qty` = `purchase_orders.lines[].quantity` for the PO line.
- `received_qty` = Σ `receipts.lines[].quantity_received` over **in-scope** receipts (as-of filtered) for that PO line.
- `rejected_qty` = Σ `receipts.lines[].quantity_rejected`.
- `billed_qty` = `ap_invoices.lines[].quantity_billed`.
- `short_qty_vs_po` = `ordered_qty − received_qty` (report only if > 0).
- `unreceived_billed_qty` = `billed_qty − received_qty` (only if > 0; i.e. invoice bills more than received).
- `receipt_completion_ratio` = `received_qty / ordered_qty`.
- `quantity_variance` = `billed_qty − received_qty`.
- `quantity_variance_pct` = `quantity_variance / billed_qty × 100`. **Denominator is BILLED, not ordered.** (e.g. billed 240, received 216 → 10.0%; billed 75, received 0 → 100.0%.)

### Price
- `po_unit_price` = `purchase_orders.lines[].unit_price`.
- `contract_unit_price` = `contracts.unit_price` (look up via `po.contract_id`; if `null`, there is no contract).
- `invoice_unit_price` = `ap_invoices.lines[].unit_price`.
- `contract_price_match`:
  - `price_type == "fixed"` → `contract_unit_price == po_unit_price == invoice_unit_price`.
  - `indexed` → PO/invoice price should equal the contract `unit_price` at the indexed point (here they match exactly, e.g. 149.75); treat equality as match.
  - `not_to_exceed` → price is within ceiling; match if `po_unit_price <= contract.unit_price` (or equals). Inspect and apply conservatively.
  - If `po.contract_id` is null → no contract → `contract_price_match` is false / not applicable (and surfaces a `missing_contract` blocker in nomination).

### Money
- `line_subtotal` = `qty × unit_price`.
- `received_goods_value` = `received_qty × unit_price` (use PO/invoice unit price; they match when price matched).
- `unreceived_goods_value` = `short_qty_vs_po × unit_price`.
- `invoice_subtotal` = `ap_invoices.subtotal`; `invoice_freight` = `ap_invoices.freight`; `invoice_tax` = `ap_invoices.tax`; `invoice_total` = `ap_invoices.total` (= subtotal + freight + tax).
- `chargeback_amount` = `basis_quantity × unit_cost` (basis_quantity and unit_cost come from the task-local chargeback register, keyed by invoice_id/receipt_id).

---

## 3. Family A — Sourcing nomination readiness packet

**Inputs:** a program_id, an `as_of_date`, and a memo naming the package line anchors (SKU → requisition_id + PO_id per line). API is source of truth.

### Step recipe
1. `GET /programs/<program_id>` → owner, budget_cap, committed_amount. `budget_headroom_usd = budget_cap − committed_amount` (equiv. latest budget_snapshot ≤ as_of).
2. For each package SKU, take the memo-named PO(s) as `package_po_ids`. `GET /purchase_orders/<po_id>` for each.
3. `selected_supplier_id` = `po.supplier_id`. `primary_requisition_id` = `po.requisition_id`. `commercial_basis_id` = `po.contract_id` (null if none).
4. **Receipt evidence:** `GET /receipts?po_id=<po_id>`, keep `receipt_date <= as_of` → `receipt_evidence_ids` (sorted set).
5. **Invoice exceptions:** `GET /ap_invoices?po_id=<po_id>`, keep `invoice_date <= as_of` **AND** `status in {on_hold, pending_receipt}` → `invoice_exception_ids`. (approved/paid/entered are NOT exceptions.)
6. **Risk events:** `GET /vendor_risk_events?supplier_id=<supplier_id>`, keep `status == "open"` and `event_date <= as_of` → `risk_event_ids`.
7. **Blocker codes** (derive from the above; emit the set):
   - `pending_receipt` — `receipt_evidence_ids` is empty (no in-scope receipt on the PO).
   - `missing_contract` — `po.contract_id` is null.
   - `late_due_date` — `po.due_date > requisition.need_by` (`GET /purchase_requisitions/<po.requisition_id>` for need_by). I.e. the PO promised date slips past the requisition need-by date.
   - `open_supplier_risk` — `risk_event_ids` is non-empty (any open VRE).
   - `supplier_watch` — `suppliers.risk_rating == "watch"`.
   - `ap_hold` — any invoice on the PO has `status == "on_hold"` (generic for any `on_hold` invoice, regardless of hold_code).
   - Anticipated variants if the template expects finer granularity: `price_variance` (invoice hold_code PRICE_VARIANCE), `supplier_review` (hold_code SUPPLIER_REVIEW). Default to the generic `ap_hold` unless the template's option set is finer.
   - A `high`/critical supplier risk_rating may warrant a stronger blocker — inspect the template's option set.
8. **Readiness → decision mapping:**
   - **`ready`** (no blockers; has receipt + contract + no open risk + no on_hold invoice) → `nomination_decision = "nominate"`; readiness `"ready"`.
   - **`at_risk`** (has receipt + contract but soft blockers: `ap_hold`, `supplier_watch`, open **medium** risk, late_due_date without missing receipt) → `nomination_decision = "conditional_nomination"`; readiness `"at_risk"`.
   - **`not_ready`** (hard blockers: `pending_receipt`, `missing_contract`, or any **severe** open risk) → `nomination_decision = "hold"`; readiness `"not_ready"`.
9. **overall_readiness** = `not_ready` if any line not_ready; else `at_risk` if any line at_risk; else `ready`.
10. **committee_action:**
    - `nominate_now_supplier_ids` = suppliers of `ready` lines.
    - `conditional_supplier_ids` = suppliers of `at_risk` lines.
    - `hold_supplier_ids` = suppliers of `not_ready` lines.
    - `next_owner` = `"ap_team"` if any `ap_hold` blocker exists anywhere; else `"procurement"` (sourcing).
    - `send_to_committee` = `"no"` if any line is on `hold` (overall not_ready); else `"yes"`. (In the observed case, a hold line ⇒ "no" / next_owner ap_team.)

### Pitfalls (Family A)
- Forgetting the as-of filter → including a later same-PO receipt (e.g. RCV-00001 dated after as_of) as "evidence". It must be excluded.
- `invoice_exception_ids` must exclude `approved`/`paid` invoices on the same PO.
- `commercial_basis_id` is the **PO's** contract_id, not just any contract for that SKU. null PO.contract_id ⇒ `missing_contract` even if a contract exists elsewhere.
- `late_due_date` compares PO.due_date to **requisition.need_by**, not to as_of. A PO due *after as_of but before need_by* is NOT late.
- Only `status == "open"` VREs count for `open_supplier_risk` (not `monitoring`, not `closed`).

---

## 4. Family B — Receiving-control closeout

Two variants: (B1) single-batch receiving closeout (batch_id given); (B2) multi-invoice AP release + chargeback file (target invoice/receipt/PO id lists given). Both share receipt-scope and reconciliation logic.

### Receipt scope categories (apply in both variants)
- **Target receipt:** the receipt tied to the invoice under review = `invoice.receipt_id` if set; otherwise the receipt(s) found via `GET /receipts?po_id=<po_id>` (as-of filtered if a review_as_of is given).
- **Same-PO-later / other same-PO receipt:** another receipt on the **same PO** that belongs to a **different invoice** (e.g. a second receipt on the PO tied to a different AP invoice). → goes in `excluded_same_po_receipt_ids`; **do not net its quantities** into this invoice's reconciliation.
- **Same-supplier-other-PO:** receipts for the same supplier on a different PO. Out of scope entirely.

### B1 — Single-batch receiving closeout (batch_id = a receipt_id)

`GET /receipts/<batch_id>` → po_id, supplier_id, warehouse_id, receipt_date, packing_slip, receiver, status, lines[].
Then `GET /purchase_orders/<po_id>`, `GET /ap_invoices?po_id=<po_id>` (pick the invoice whose `receipt_id == batch_id`, or the relevant invoice), `GET /contracts/<po.contract_id>` (if any), `GET /suppliers/<supplier_id>`, `GET /vendor_risk_events?supplier_id=<supplier_id>`.

#### `inspection_summary`
po_id, program_id (from PO), supplier_id, supplier_name, warehouse_id, receipt_date, packing_slip, receiver — all literal from the records.

#### `line_reconciliation` (one entry per receipt line)
- `po_line_id`, `sku` (from receipt line).
- `ordered_qty` = PO line quantity for that po_line_id.
- `received_qty` = receipt line quantity_received.
- `rejected_qty` = receipt line quantity_rejected.
- `billed_qty` = invoice line quantity_billed (the invoice tied to this batch).
- `short_qty_vs_po`, `unreceived_billed_qty`, `receipt_completion_ratio` per primitives.
- `po_unit_price`, `contract_unit_price`, `invoice_unit_price`, `contract_price_match` per primitives.

#### `invoice_review`
- `invoice_id`, `invoice_status` (invoice.status), `hold_code` (invoice.hold_code).
- `receipt_status` = receipt.status.
- `po_status` = po.status.
- `exception_codes` (snake_case vocabulary, emit the set):
  - `INVOICE_QTY_EXCEEDS_RECEIPT` — `billed_qty > received_qty`.
  - `PARTIAL_RECEIPT` — `po.status == "partial_receipt"` (equiv. received < ordered).
  - `SUPPLIER_WATCH_RISK` — `supplier.risk_rating == "watch"`.
  - Anticipated: `RECEIPT_INSPECTION_HOLD` (receipt.status == inspection_hold), `PRICE_VARIANCE` (invoice hold_code PRICE_VARIANCE), `SUPPLIER_REVIEW` (hold_code SUPPLIER_REVIEW), `NO_RECEIPT` (invoice pending_receipt / no receipt).

#### `financials`
- `received_goods_value` = received_qty × unit_price.
- `unreceived_goods_value` = short_qty_vs_po × unit_price.
- `invoice_subtotal`, `invoice_freight`, `invoice_tax`, `invoice_total` — literal from the invoice.

#### `decision` (controlled enums)
- `batch_disposition`: `accept_partial_hold_variance` (partial receipt + qty-variance hold). Anticipate: `accept_full_match` (full receipt, no variance), `reject_shortage` (severe shortfall), `hold_inspection` (inspection_hold receipt).
- `ap_action`: `keep_invoice_on_hold` (when invoice on_hold / pending_receipt). Anticipate `release_invoice`.
- `receiving_action`: `record_shortage_follow_up` (shortage vs PO). Anticipate `close_receipt` (full match), `hold_for_inspection` (inspection_hold).
- `supplier_action`: `request_credit_or_remaining_delivery` (shortage). Anticipate `none` (clean match).

#### `supplier_risk_context`
- `supplier_risk_rating` = supplier.risk_rating.
- `has_open_supplier_risk` = any VRE for supplier with `status == "open"` (as-of).
- `open_supplier_risk_event_ids` = those event ids.

#### `evidence`
- `endpoint_record_ids` = sorted set of all API record ids used (invoice, contract, item/sku, PO, receipt, supplier, VRE).
- `task_payloads_reviewed` = list of the input payload file paths you read (e.g. `input/payloads/receiving_memo.md`).

### B2 — AP release + chargeback file (target id lists given)

The target id lists (`po_ids`, `receipt_ids`, `invoice_ids`) come from the input packet (e.g. `ap_release_packet.json`). The **chargeback register** is in the **task-local payload** (NOT in the API) — read `chargeback_register_excerpt` from the packet. Each chargeback entry: `{chargeback_id, invoice_id, po_id, receipt_id, reason_code, basis_quantity, unit_cost, status}` where `status` = `approved | pending_quality_review`.

#### For each target invoice — `release_decisions[]`
1. `GET /ap_invoices/<invoice_id>` → po_id, total, receipt_id.
2. **receipt_ids_in_scope:**
   - If `invoice.receipt_id` is set → `[invoice.receipt_id]`.
   - Else `GET /receipts?po_id=<po_id>`; if exactly one (or the one matching this invoice's line) → `[that receipt_id]`.
   - If no receipts on the PO → `[]` (missing receipt).
3. **excluded_same_po_receipt_ids:** all OTHER receipts on the same PO not in scope (e.g. a second receipt belonging to a different invoice). `GET /receipts?po_id=<po_id>` minus in-scope.
4. Find chargeback entries for this `invoice_id` (and/or its `receipt_id`/`po_id`) in the local register.
   - `approved_chargeback_amount` = Σ `basis_quantity × unit_cost` over entries with `status == "approved"`.
   - `pending_chargeback_amount` = Σ over entries with `status == "pending_quality_review"`.
5. **decision / primary_reason / net_release_amount:**
   - No receipt on PO (`receipt_ids_in_scope == []`) → `decision = "hold_missing_receipt"`, `primary_reason = "no_receipt_on_po"`, `net_release_amount = 0`.
   - Receipt exists, chargeback `approved` (or no pending) → `decision = "release_net_after_approved_chargeback"`, `net_release_amount = invoice_total − approved_chargeback_amount`.
     - `primary_reason`: `"approved_qty_chargeback"` when register reason_code is "Underage Quantity"; `"approved_ap_quantity_variance"` when reason_code is "AP Quantity Variance". (Map the register reason_code to the lower-case enum.)
   - Receipt exists, chargeback `pending_quality_review` (typically with receipt.status == `inspection_hold`) → `decision = "hold_pending_quality_chargeback"`, `primary_reason = "inspection_hold_pending_chargeback"`, `net_release_amount = 0`.

`invoice_total` = ap_invoices.total for that invoice.

#### Per receipt — `receiving_exceptions[]` (one row per in-scope receipt, plus a MISSING row for POs with no receipt)
- `receipt_id`, `po_id`.
- `exception_codes` (Title-Case vocabulary, emit as a set):
  - If `receipt.status == "inspection_hold"` → `"Inspection Hold"`.
  - If `received_qty < ordered_qty` (receipt short vs PO) → `"Severe Unmatched Quantity"`.
  - Add the chargeback register `reason_code` verbatim for this receipt (e.g. `"Underage Quantity"`, `"AP Quantity Variance"`).
  - `accepted` / `accepted_with_note` → no status-derived label.
  - MISSING receipt row (`receipt_id = "MISSING:<po_id>"`) → `exception_codes = []`.
- `chargeback_status`: `"approved"` if the register entry for this receipt is approved; `"pending_quality_review"` if pending; `"not_applicable"` if no receipt / no chargeback.
- `resolution_status`: `"net_release_ready"` (chargeback approved) | `"hold_for_quality_review"` (pending/inspection_hold) | `"missing_receipt"` (no receipt).

#### `summary`
- `release_invoice_ids` = invoices with `release_net_after_approved_chargeback`.
- `hold_invoice_ids` = invoices with `hold_*` decision.
- `approved_chargeback_total` = Σ approved_chargeback_amount across all invoices.
- `pending_chargeback_total` = Σ pending_chargeback_amount.
- `net_release_total` = Σ net_release_amount across all invoices.
- `authoritative_sources` = `["local_chargeback_register", "procureops_ap_records", "procureops_po_records", "procureops_receipt_records"]` (add others you actually used, e.g. procureops_supplier_records).
- `supporting_only_sources` = the narrative notes from the packet (e.g. `ap_release_request_note`, `stale_po73xx_alias_note`).
- `followup_actions`: derive — e.g. `ask_receiving_for_vantix_receipt` (missing receipt), `hold_luma_duplicate_receipt_for_separate_invoice` (excluded same-PO receipt belongs to another invoice), `post_approved_chargeback_netting`, `route_po00031_quality_review` (pending quality review on a specific PO).

### Pitfalls (Family B)
- **Do not net a same-PO-later receipt** that belongs to a different invoice. It goes in `excluded_same_po_receipt_ids`, not into received_qty.
- `billed_qty` for the batch reconciliation is the **invoice tied to that batch** (match on `invoice.receipt_id == batch_id`), not any invoice on the PO.
- The two exception vocabularies are different: B1 uses snake_case (`INVOICE_QTY_EXCEEDS_RECEIPT`...), B2 uses Title Case (`Inspection Hold`, `Severe Unmatched Quantity`...). Do not mix them.
- Chargebacks are **not** in the API — only in the task-local register. If a register entry is missing for an invoice, approved/pending chargeback = 0.
- `invoice_total` includes freight+tax; chargeback `unit_cost` is a unit price (multiply by basis_quantity) — don't confuse with invoice total.
- A receipt can be `accepted` but still short vs PO (`quantity_received < ordered`) → still emits `Severe Unmatched Quantity` / `PARTIAL_RECEIPT`.

---

## 5. Family C — AP close / vendor-balance + hold/release settlement

**Inputs:** a close-slice memo naming **specific invoice_ids** (the slice), a close_date, and a rule that opening balance for the slice suppliers is 0, plus a payment-credit window (e.g. "payments scheduled through 2026-06-30 reduce the close balance").

### Step recipe
For each target invoice:
1. `GET /ap_invoices/<invoice_id>` → status, hold_code, po_id, supplier_id, total, lines[].quantity_billed.
2. `GET /purchase_orders/<po_id>` → program_id, lines[].quantity (ordered), supplier_id.
3. `GET /receipts?po_id=<po_id>` → `quantity_received` = Σ quantity_received over receipts (slice scope; apply as-of if review date given).
4. `GET /suppliers/<supplier_id>` → supplier_name.
5. `GET /payments?invoice_id=<invoice_id>` → find scheduled payments within the close window.

#### `invoice_decisions[]`
- `invoice_id`, `program_id`, `po_id`, `supplier_id`, `supplier_name`, `invoice_status`.
- `quantity_billed`, `quantity_received`, `quantity_variance = billed − received`, `quantity_variance_pct = variance / billed × 100`.
- `invoice_total` = ap_invoices.total.
- `hold_decision`:
  - invoice.status == `approved` AND hold_code == null → `"RELEASE"`, `release_to_payment = true`.
  - invoice.status in {`on_hold`, `pending_receipt`} → `"HOLD"`, `release_to_payment = false`.
  - (Anticipate: `paid`/`entered` → handle per memo; usually not in a close slice.)
- `hold_code` = invoice.hold_code (null if RELEASE).
- `scheduled_payment_amount` = Σ `payment.amount` for this invoice where `status == "scheduled"` AND `scheduled_date <= <window_end>` (window from memo, e.g. 2026-06-30). If none → 0.0.
- `net_balance_impact` = `invoice_total − scheduled_payment_amount`.
- `reason_codes` (emit set):
  - approved + no hold → `APPROVED_THREE_WAY_MATCH`.
  - on_hold → the hold_code itself (`QTY_VARIANCE` / `PRICE_VARIANCE` / `SUPPLIER_REVIEW`).
  - pending_receipt → `NO_RECEIPT`.
  - if `scheduled_payment_amount > 0` → also add `SCHEDULED_PAYMENT_FOUND`.

#### `vendor_balances[]` (one row per supplier in the slice)
- `opening_balance` = 0.0 (per memo assumption; do not invent otherwise).
- `invoice_total` = Σ invoice_total over this supplier's slice invoices.
- `scheduled_payments` = Σ scheduled_payment_amount over this supplier's slice invoices.
- `held_invoice_total` = Σ invoice_total over this supplier's slice invoices with `hold_decision == HOLD`.
- `releasable_invoice_total` = Σ invoice_total over this supplier's slice invoices with `hold_decision == RELEASE`.
- `close_balance` = `invoice_total − scheduled_payments`.
- `balance_status`:
  - `FULLY_SCHEDULED` — close_balance == 0 and scheduled_payments == invoice_total (released + fully scheduled).
  - `OPEN_HELD` — held invoices and close_balance > 0.
  - Anticipated: `OPEN_UNHELD` — released but not yet scheduled (close_balance > 0, held == 0).

#### `program_summary[]` (one row per program in the slice)
- `program_id`, `invoice_count`, `invoice_total` = Σ over slice invoices for that program, `held_total` = Σ invoice_total of HOLD invoices, `released_total` = Σ invoice_total of RELEASE invoices, `net_close_balance` = `invoice_total − released_total` (= held_total, i.e. what remains open). Verify against the totals.

#### Queues & total
- `payment_hold_queue` = list of invoice_ids with `hold_decision == HOLD`.
- `payment_release_queue` = list of invoice_ids with `hold_decision == RELEASE`.
- `total_close_balance` = Σ `close_balance` across vendors (= Σ held invoice totals when opening is 0).

### Pitfalls (Family C)
- `quantity_variance_pct` denominator is **billed** (e.g. 24/240 = 10.0%, not 24/216).
- `scheduled_payment_amount` must respect the memo's window (date ≤ window_end) and `status == "scheduled"`. `released`/`blocked` payments and out-of-window scheduled payments don't count.
- Only the **slice invoices** count toward vendor/program totals — not all the supplier's invoices. AP-0027 (a scheduled LUMA payment) is irrelevant if AP-LUMA-7714 is the slice invoice.
- `net_balance_impact` for a RELEASE invoice with a scheduled payment = 0 (it's covered); for a HOLD invoice = invoice_total (full exposure remains).

---

## 6. Family D — Change-control contract amendment

**Inputs:** a change memo (`change_memo.json`) with: `change_request_id`, `program_id`, `contract_id`, `supplier_id`, `sku`, `variant_code`, `requested_incremental_quantity`, `source_requisition_id`, and `business_controls` (tax_rate_percent, currency, budget_exposure rule, contract_ceiling_exposure rule, `existing_contract_usage = "exclude cancelled"`, `approval_good_actions = ["approved"]`, `supplier_watch_rating = "context only unless an open severe event is found"`).

### Step recipe
1. `GET /contracts/<contract_id>` → status, price_type, unit_price, ceiling_amount.
2. **Contract usage (existing):** `GET /purchase_orders?contract_id=<contract_id>`. Per `existing_contract_usage`, **exclude `status == "cancelled"`**.
   - `included_po_ids` = non-cancelled POs.
   - `excluded_cancelled_po_ids` = cancelled POs.
   - `noncancelled_subtotal` = Σ `po.subtotal` over included POs.
3. `GET /budget_snapshots?program_id=<program_id>` → pick snapshot (latest `snapshot_date ≤ memo_date`); `snapshot_id`, `budget_cap`, `committed_amount`. (Program record carries the same budget_cap/committed_amount; either is acceptable but prefer the snapshot for as-of correctness.)
4. `GET /purchase_requisitions/<source_requisition_id>` and `GET /approval_events?object_id=<source_requisition_id>` (object_type=requisition) → pick latest by event_date ≤ memo_date.
5. `GET /suppliers/<supplier_id>` and `GET /vendor_risk_events?supplier_id=<supplier_id>`.

#### `contract_check`
- `contract_status`, `price_type`, `unit_price`, `ceiling_amount` — from contract.
- `headroom_before_change` = `ceiling_amount − noncancelled_subtotal`.
- `requested_quantity` = memo.requested_incremental_quantity.
- `requested_subtotal` = `requested_quantity × unit_price` (ceiling exposure = **subtotal before tax & freight** per memo rule).
- `headroom_after_change` = `headroom_before_change − requested_subtotal`.
- `ceiling_ok` = `headroom_after_change >= 0`.

#### `program_budget_check`
- `remaining_budget` = `budget_cap − committed_amount`.
- `requested_tax` = `requested_subtotal × tax_rate_percent / 100`.
- `requested_total` = `requested_subtotal + requested_tax` (+ freight **only if** the memo provides a freight figure; normally it does not).
- `budget_after_change` = `remaining_budget − requested_total`.
- `budget_ok` = `budget_after_change >= 0`.
- `max_quantity_with_current_budget` = `floor(remaining_budget / (unit_price × (1 + tax_rate_percent/100)))` when no freight. (If freight is given, subtract it first; solve `q×unit_price×(1+tax) + freight ≤ remaining_budget`.)

#### `approval_check`
- `source_requisition_id`, `latest_event_id`, `latest_action`, `latest_actor`, `latest_event_date` — from the latest approval_event (≤ memo_date).
- `approval_ok` = `latest_action in business_controls.approval_good_actions` (i.e. `"approved"`). `submitted/returned/escalated` ⇒ not ok.

#### `supplier_risk_check`
- `supplier_status` = supplier.status, `supplier_risk_rating` = supplier.risk_rating.
- `open_event_ids` = VREs with `status == "open"` (≤ memo_date).
- `severe_open_event_ids` = open VREs with `severity in {high, critical}`.
- `supplier_risk_ok` = `severe_open_event_ids` is empty (per memo: watch/medium is context only; a severe open event blocks).

#### `supporting_ids`
- `included_po_ids`, `excluded_cancelled_po_ids` (from step 2), `approval_event_ids` (approval events for the requisition).

#### `required_actions` (derive from failing checks)
- `approval_ok == false` → `"obtain_final_requisition_approval"`.
- `budget_ok == false` → `"raise_budget_exception_or_reduce_quantity"`.
- `ceiling_ok == false` → `"reduce_quantity_or_raise_ceiling"`.
- `supplier_risk_ok == false` → `"escalate_supplier_risk"`.

#### `summary` & `decision`
- `blocker_count` = number of failing checks among {ceiling_ok, budget_ok, approval_ok, supplier_risk_ok}.
- `currency` = memo currency, `ready_to_release` = (blocker_count == 0).
- `decision`:
  - all ok → `"release_as_amendment"`.
  - budget_ok false AND approval_ok false → `"hold_for_budget_and_approval"`.
  - only budget → `"hold_for_budget"`; only approval → `"hold_for_approval"`; ceiling false → `"hold_for_ceiling"`; severe supplier risk → `"hold_for_supplier_risk"`. Combine multiple failing checks into a compound hold label matching the template's style.

### Pitfalls (Family D)
- **Exclude cancelled POs** from contract usage. Including them inflates `noncancelled_subtotal` and breaks headroom.
- Ceiling exposure = **subtotal only** (no tax, no freight). Budget exposure = **subtotal + tax** (+ freight only if memo gives it). Don't swap these.
- `approval_ok` uses the **latest** approval action by date; an earlier "approved" doesn't count if a later "submitted"/"returned" exists.
- `supplier_risk_ok`: watch rating / medium severity is **context only** (does not block) per memo. Only a **severe open** event blocks. Do not block on `watch`.
- `max_quantity_with_current_budget` uses the **after-tax unit cost** (`unit_price × (1+tax)`) as the divisor; floor the result.
- `budget_after_change` can be negative — report it as the negative number (don't clamp to 0); `budget_ok = (>= 0)`.

---

## 7. Cross-family pitfalls & common misjudgments

- **As-of leakage:** the single most common error. Re-derive every "current" set (receipts, invoices, risk events, approvals, budget snapshot) with the task's as-of/close/review date. A record dated one day after the cutoff changes the answer.
- **Quantity denominators:** `quantity_variance_pct` divides by **billed**. `receipt_completion_ratio` divides received by **ordered**. Don't interchange.
- **PO total vs invoice total:** PO `total` = subtotal + tax (no freight in this data). Invoice `total` = subtotal + freight + tax. For invoice-facing money fields use the invoice; for PO-facing use the PO.
- **`invoice.receipt_id` nullable:** a `pending_receipt` invoice has `receipt_id: null`. Find the receipt via `?po_id=`. Do not treat null as "missing entirely" if a receipt exists on the PO.
- **Duplicate / parallel receipts on one PO:** a PO can have multiple receipts, each belonging to a different invoice. Scope to the invoice's own receipt; put the others in `excluded_same_po_receipt_ids` and never net them.
- **VRE "open" vs "monitoring":** only `status == "open"` is an open risk. `monitoring` and `closed` are not. Severe = severity `high`/`critical` AND open.
- **Chargebacks are local, not API:** read `chargeback_register_excerpt` from the input payload. No `/chargebacks` endpoint exists.
- **Contract price_type matters:** `fixed`/`indexed` are exact-price matches; `not_to_exceed` is a ceiling check. Don't assert `contract_price_match` equality blindly for not_to_exceed.
- **Cancelled POs:** excluded from contract usage and from nomination scope, but listed explicitly in `excluded_cancelled_po_ids` for traceability.
- **Source authority:** API records + local chargeback register are authoritative. Narrative notes (release requests, alias notes, dock memos) are supporting-only — use for context/follow-ups, never as the basis for a number.
- **Option sets are family-specific:** B1 exception codes are snake_case (`PARTIAL_RECEIPT`); B2 exception codes are Title Case (`Severe Unmatched Quantity`). AP-close reason codes are upper-snake (`APPROVED_THREE_WAY_MATCH`). Use the right vocabulary for each template.
- **Rounding:** compute at full precision, round only the emitted USD values to 2 decimals. Chargeback netting (`invoice_total − approved_chargeback`) must be done before rounding each term.
- **Verify totals:** `total_close_balance` = Σ vendor `close_balance` = Σ held invoice totals (when opening=0). `net_release_total` = Σ net_release. `approved_chargeback_total` = Σ approved. Re-sum as a self-check before emitting.

---

## 8. Final output discipline

- Return **only** the JSON object matching `input/payloads/answer_template.json` — no prose, no markdown fence (unless the template/runner requires it).
- Read `answer_template.json` first: it defines the exact field names, nesting, and which fields are lists/sets vs scalars. Mirror its structure exactly; do not add or omit keys.
- Treat list fields as **sets** (dedupe; sort for determinism unless the template specifies an order).
- Every record id you reference must exist in the API (or the local chargeback register for chargeback ids). If a target id from the packet isn't in the API, surface it as `MISSING:<id>` per the template pattern (e.g. `MISSING:PO-AX17-4519`).
- Always re-derive numbers from the API; do not trust narrative memos for figures.
