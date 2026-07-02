# SKILL — ProcureOps ERP Procurement Reconciliation (task_group_006)

Executable recipes for the four task families in this group. The API is the source of truth; the local memo/packet only names IDs and business rules. Always re-derive state from the live API, never trust a memo number.

## 0. Environment & API mechanics

- Base URL: `<remote-env-url>`. Prompts that say `http://127.0.0.1:8006` mean THIS SAME service — substitute the remote URL.
- `GET /<collection>` → `{"count":N,"results":[...]}`. **No pagination, no `_limit`.** Unknown query params become substring/case-insensitive field filters (they also match inside nested list values), so an unknown filter returns 0 — only filter on real field names.
- `GET /<collection>/<id>` → the record object.
- Useful link filters: `?po_id=`, `?supplier_id=`, `?program_id=`, `?contract_id=`, `?sku=`, `?invoice_id=`, `?receipt_id=`, `?object_id=` (for approval_events).
- `start`/`end` filter the collection's *primary date field* inclusively. **Do not rely on this for as-of scoping** — instead fetch by link filter (e.g. `?po_id=X`) then filter client-side by the relevant date `<= as_of`. This avoids ambiguity about which date field is filtered.
- Collections: `programs, suppliers, items, contracts, purchase_requisitions, purchase_orders, receipts, ap_invoices, payments, approval_events, budget_snapshots, vendor_risk_events`.
- Amounts in API records are USD **dollars** (floats). Most answer templates want USD **cents** for unit prices OR dollars-rounded-to-cents for totals — read each template field's stated unit. Quantities carry 2 decimals.

## 1. Cross-cutting reconciliation rules

- **as_of scoping** (applies to every family): a record is "as of" the review date only if its dated field (`receipt_date`, `invoice_date`, `event_date`, `snapshot_date`, `scheduled_date`) is `<= as_of`. Records dated AFTER as_of are excluded even if they link to the target PO/invoice. Example: for as_of 2026-06-01, a receipt dated 2026-06-08 on the same PO is OUT of scope.
- **Open supplier risk** = `vendor_risk_events` with `status` in `{monitoring, open}` AND `event_date <= as_of`. `closed`/`resolved` events are NOT open, even if recent. Severity values: `low, medium, high, critical`.
- **Severe** open risk = severity in `{high, critical}`. `medium` is NOT severe.
- **Three-way match** = PO line + receipt line + invoice line agree on quantity AND unit price, with a non-null receipt link.
- **Price-match anchor** = `contract.unit_price`. Compare to PO line `unit_price` and invoice line `unit_price`. All three should agree when a contract exists.
- **Which invoice backs a receipt/batch**: match on `ap_invoices.receipt_id == receipt_id` (not just `po_id`). Multiple invoices can share a PO; only the one whose `receipt_id` equals the batch is in scope for that batch's billed-qty/price reconciliation.
- Reconciliation chain: `PO → receipts(same po_id) → invoices(invoice.po_id and/or invoice.receipt_id) → payments(payment.invoice_id)`. Contract anchors price: `contract ↔ po.contract_id ↔ po line unit_price ↔ invoice line unit_price`.
- Rounding: round USD totals to cents (2 dp); ratios to the precision the template states (e.g. 4 dp for completion ratio, 1 dp for variance %). Sort ID lists ascending unless told otherwise.

---

## 2. Family A — Sourcing nomination readiness (train_001 / test_003)

**Trigger:** "sourcing nomination readiness packet", "as of <date>", a program_id, and a memo naming package anchors (SKU + requisition_id + po_id per line).

### Query recipe
1. `GET /programs/<program_id>` (owner, budget_cap, committed_amount).
2. `GET /budget_snapshots?program_id=<pg>` → pick the snapshot with `snapshot_date <= as_of` (latest such). Gives `pending_invoice_amount`.
3. For each package line (SKU + REQ + PO from memo):
   - `GET /purchase_orders/<po_id>` (supplier_id, contract_id, status, due_date, lines qty/unit_price).
   - `GET /purchase_requisitions/<req_id>` (status, need_by).
   - If `po.contract_id` non-null → `GET /contracts/<contract_id>` (status, unit_price, ceiling). Else `GET /contracts?sku=<sku>` to confirm no contract exists.
   - `GET /items/<sku>` (preferred_supplier_id — sanity check vs PO supplier).
   - `GET /suppliers/<supplier_id>` (risk_rating).
   - `GET /receipts?po_id=<po_id>` → client-filter `receipt_date <= as_of` → receipt evidence.
   - `GET /ap_invoices?po_id=<po_id>` → client-filter `invoice_date <= as_of` → filter to exception invoices (see below).
   - `GET /vendor_risk_events?supplier_id=<sid>` → open events as of as_of.
   - `GET /approval_events?object_id=<req_id>` (informational; not a blocker code in this family).

### Output fields & enums
- `package_line_skus`: all package SKUs, sorted ascending.
- `program_summary`: `owner` (from program), `budget_headroom_usd` = `budget_cap − committed_amount` (programs row, dollars, NOT minus pending), `overall_readiness` ∈ {`ready`,`at_risk`,`not_ready`}.
- Per `nomination_lines[]` (one per SKU, matched by sku):
  - `selected_supplier_id` = PO.supplier_id (the nominated supplier).
  - `nomination_decision` ∈ {`nominate`,`conditional_nomination`,`hold`}.
  - `readiness_status` ∈ {`ready`,`at_risk`,`not_ready`}.
  - `primary_requisition_id` = the memo's requisition_id.
  - `commercial_basis_id` = `contract_id` if a contract exists else `null`.
  - `package_po_ids` = the memo's PO(s) for the line, sorted.
  - `receipt_evidence_ids` = receipt_ids on the PO with `receipt_date <= as_of`, sorted.
  - `invoice_exception_ids` = invoice_ids on the PO with `invoice_date <= as_of` that are in a hold/exception state: `status` ∈ {`on_hold`,`pending_receipt`} OR `hold_code` non-null. Exclude `paid`/`approved`-clean/`cancelled`. Sorted.
  - `risk_event_ids` = open vendor_risk_events as of as_of, sorted.
  - `blocker_codes` ∈ {`missing_contract`,`supplier_watch`,`open_supplier_risk`,`ap_hold`,`pending_receipt`,`late_due_date`,`none`} sorted.

### Blocker decision rules
- `missing_contract`: PO.contract_id is null AND no contract record exists for the SKU/program.
- `supplier_watch`: `supplier.risk_rating == "watch"`.
- `open_supplier_risk`: ≥1 open vendor_risk_event as of as_of.
- `ap_hold`: ≥1 invoice_exception on the PO as of as_of.
- `pending_receipt`: ZERO receipts on the PO as of as_of (no receipt evidence at all). A partial receipt is NOT `pending_receipt` (it is evidenced).
- `late_due_date`: PO `due_date <= as_of` AND PO not in `{closed, received}` (the need-by/due date has passed unmet). If `due_date > as_of`, do not set.
- `none`: no blockers apply (use only when the set is empty — some graders want `["none"]`, others want `[]`; prefer `["none"]` per the enum).

### Readiness / decision mapping
- `ready` / `nominate`: blocker set is `{none}` (clean contract + receipt + no holds + no open risk + not late).
- `at_risk` / `conditional_nomination`: has evidence (contract exists, has receipt or pending receipt expected) but has clearable blockers (supplier_watch, ap_hold, open non-severe risk). Can proceed once cleared.
- `not_ready` / `hold`: `missing_contract`, OR no path to clear (e.g. severe open risk, pending receipt with no contract). 

### Committee action
- `nominate_now_supplier_ids` = suppliers whose line decision is `nominate`.
- `conditional_supplier_ids` = `conditional_nomination` suppliers.
- `hold_supplier_ids` = `hold` suppliers.
- `next_owner` ∈ {`buyer`,`finance_ops`,`quality_ops`,`program_owner`,`ap_team`}: route by the dominant *actionable* blocker across the packet — `missing_contract`→`buyer`; `ap_hold`/invoice holds dominate→`ap_team`; supplier-risk severe→`program_owner`; quality/damage→`quality_ops`; budget→`finance_ops`. When mixed, prefer the blocker that blocks the most lines / is most fundamental (missing_contract before ap_hold).
- `send_to_committee` ∈ {`yes`,`no`}: `yes` if any line is `nominate` or `conditional_nomination`; `no` only if every line is `hold`.

### Pitfalls (Family A)
- **Excluding future-dated receipts/invoices by as_of is the #1 error.** A later receipt on the same PO (e.g. a 2026-06-08 receipt when as_of is 2026-06-01) must NOT appear in `receipt_evidence_ids`.
- Include ALL exception invoices as of as_of, not just the newest. An older `PRICE_VARIANCE` hold invoice (e.g. dated 2026-04-29) on the same PO still counts as `ap_hold` and in `invoice_exception_ids`.
- `budget_headroom_usd` is `cap − committed` only; but `overall_readiness` must consider the snapshot's `pending_invoice_amount` — if `committed + pending_invoice > budget_cap`, the program is `not_ready` even though headroom looks positive.
- `missing_contract` requires confirming NO contract record exists (query `?sku=`), not just that `po.contract_id` is null.
- `pending_receipt` ≠ partial receipt. Partial receipt (PO status `partial_receipt`) still has evidence → not a `pending_receipt` blocker.
- Do NOT count `closed`/`resolved` vendor_risk_events as open.
- `supplier_watch` (rating) and `open_supplier_risk` (events) are independent blockers; both can be set on the same line.
- Approval state of the requisition is informational here (no `approval` blocker code exists in this family). Use it only for context.
- `DRV-AX17`-style lines (no contract anywhere) → `hold`/`not_ready` regardless of other evidence.

---

## 3. Family B — Receiving-control closeout + AP release/chargeback (train_002, train_005 / test_001, test_004)

Two sub-shapes share one reconciliation core.

### 3A. Single-batch closeout (train_002 shape: one receipt_id)

**Query recipe**
1. `GET /receipts/<batch_id>` (po_id, supplier_id, warehouse_id, receipt_date, packing_slip, receiver, status, lines[]).
2. `GET /purchase_orders/<po_id>` (program_id, status, lines[] qty/unit_price).
3. `GET /contracts/<po.contract_id>` if non-null (unit_price, ceiling).
4. `GET /suppliers/<supplier_id>` (name, risk_rating); `GET /vendor_risk_events?supplier_id=<sid>` (open as of review date).
5. `GET /ap_invoices?po_id=<po_id>` → pick the invoice whose `receipt_id == batch_id` (the others belong to other batches). Use its `lines[]` for billed_qty and `unit_price`, and its `status`/`hold_code`/`subtotal`/`freight`/`tax`/`total`.

**Reconciliation (per `po_line_id`, sorted ascending)**
- `ordered_qty` = PO line `quantity`.
- `received_qty` = receipt line `quantity_received` (for THIS batch only; do not sum other receipts).
- `rejected_qty` = receipt line `quantity_rejected`.
- `billed_qty` = invoice line `quantity_billed` (invoice linked to THIS batch via `receipt_id`).
- `short_qty_vs_po` = `ordered_qty − received_qty`.
- `unreceived_billed_qty` = `billed_qty − received_qty` (signed; positive = billed but not received).
- `receipt_completion_ratio` = `received_qty / ordered_qty`, 4 dp.
- `po_unit_price` = PO line unit_price; `contract_unit_price` = contract.unit_price; `invoice_unit_price` = invoice line unit_price.
- `contract_price_match` = (contract.unit_price == invoice line unit_price) when a contract exists (extend to PO line too; if any differ, false).

**exception_codes** (set; allowed: `INVOICE_QTY_EXCEEDS_RECEIPT, PARTIAL_RECEIPT, SUPPLIER_WATCH_RISK, PRICE_MISMATCH, DAMAGE_REJECTION, NO_EXCEPTION`):
- `INVOICE_QTY_EXCEEDS_RECEIPT`: `billed_qty > received_qty`.
- `PARTIAL_RECEIPT`: `received_qty < ordered_qty` (or PO status `partial_receipt`).
- `SUPPLIER_WATCH_RISK`: `supplier.risk_rating == "watch"`.
- `PRICE_MISMATCH`: contract/PO/invoice unit prices differ.
- `DAMAGE_REJECTION`: `rejected_qty > 0` OR receipt line `inspection_status == "failed"` OR receipt status `rejected`.
- `NO_EXCEPTION`: none of the above (use alone).

**financials** (USD, 2 dp): `received_goods_value` = Σ `received_qty × po_unit_price`; `unreceived_goods_value` = Σ `(ordered_qty − received_qty) × po_unit_price`; `invoice_subtotal/freight/tax/total` from the invoice object.

**decision** (allowed sets in template):
- `batch_disposition`: `accept_partial_hold_variance` (partial + qty variance, receipt accepted), `release_full_invoice` (clean 3-way), `reject_batch` (damage/failed inspection), `manual_recount_required` (unexplained qty gap needing recount).
- `ap_action`: `keep_invoice_on_hold` (any hold_code / variance), `release_invoice` (clean 3-way), `void_invoice` (duplicate/unlinked).
- `receiving_action`: `record_shortage_follow_up` (short_qty > 0), `no_receiving_action` (clean), `reject_all_units` (damage).
- `supplier_action`: `request_credit_or_remaining_delivery` (shortage), `no_supplier_action` (clean), `supplier_debit_for_damage` (damage).

**supplier_risk_context**: `supplier_risk_rating` (from supplier), `has_open_supplier_risk` (bool), `open_supplier_risk_event_ids` (open events as of review date, as a set).

**evidence**: `endpoint_record_ids` = set of all API record IDs touched (program, PO, contract, receipt, invoice, supplier, risk events, items); `task_payloads_reviewed` = set of local payload filenames (memo, answer_template).

### 3B. Multi-invoice release + chargeback (train_005 shape: a packet with po_ids/receipt_ids/invoice_ids + a `chargeback_register_excerpt`)

**Query recipe**: fetch every PO, receipt, invoice named in `target_ids`; fetch the chargeback_register from the local packet (authoritative source `local_chargeback_register`). The `ap_release_request_note` and any `po73xx_alias_note` are **supporting-only**, not authoritative.

**Per-invoice `release_decisions[]`:**
- `receipt_ids_in_scope` = receipts on the invoice's PO that are <= review_as_of AND link to this invoice's line scope. Normally = `[invoice.receipt_id]` when populated; `[]` when null.
- `excluded_same_po_receipt_ids` = OTHER receipts on the same PO (different receipt_id) not in scope for this invoice — e.g. a duplicate/later receipt tied to a different invoice. Sorted.
- Use the chargeback register to find chargebacks matching this `invoice_id`/`po_id`/`receipt_id`.
- `approved_chargeback_amount` = Σ (`basis_quantity × unit_cost`) for chargebacks with `status == "approved"`.
- `pending_chargeback_amount` = Σ for `status == "pending_quality_review"`.
- `net_release_amount` = `invoice_total − approved_chargeback_amount` (pending chargebacks do NOT reduce net; they cause a hold).
- `decision` ∈ {`release_net_after_approved_chargeback`,`hold_missing_receipt`,`hold_pending_quality_chargeback`}; `primary_reason` ∈ {`approved_qty_chargeback`,`approved_ap_quantity_variance`,`no_receipt_on_po`,`inspection_hold_pending_chargeback`}.

**Decision rules:**
- `hold_missing_receipt` / `no_receipt_on_po`: invoice.receipt_id is null AND no receipt exists on the PO (verify `GET /receipts?po_id=`). AP-VANTIX-style: PO has zero receipts.
- `hold_pending_quality_chargeback` / `inspection_hold_pending_chargeback`: a matching chargeback has `status == "pending_quality_review"` OR the in-scope receipt has `status == "inspection_hold"`. AP ledger status "approved" does NOT override a receiving quality hold.
- `release_net_after_approved_chargeback` / (`approved_qty_chargeback` | `approved_ap_quantity_variance`): a matching chargeback is `approved`. Pick `approved_ap_quantity_variance` when the chargeback `reason_code` is "AP Quantity Variance" (billed > received/PO), `approved_qty_chargeback` when it's "Underage Quantity" (received < ordered).
- **Data-quirk handling:** an invoice may carry `hold_code: "NO_RECEIPT"` while `receipt_id` is actually populated and a receipt exists. Do NOT treat as missing-receipt — inspect the real receipt linkage and qty variance; if an approved AP-quantity-variance chargeback exists, release net of it.

**`receiving_exceptions[]` (per receipt_id in target):**
- `exception_codes` (zero or more of: `Underage Quantity, Severe Unmatched Quantity, Inspection Hold, AP Quantity Variance`):
  - `Underage Quantity`: `received_qty < po_qty`.
  - `Severe Unmatched Quantity`: large unexplained over/under (judgment; use sparingly).
  - `Inspection Hold`: receipt `status == "inspection_hold"`.
  - `AP Quantity Variance`: `billed_qty > received_qty` (or billed > PO qty).
- `chargeback_status` ∈ {`approved`,`pending_quality_review`,`not_applicable`} from the matching chargeback (else `not_applicable`).
- `resolution_status` ∈ {`net_release_ready`,`hold_for_quality_review`,`accepted_no_receiving_exception`,`missing_receipt`}: `net_release_ready` if chargeback approved and no inspection hold; `hold_for_quality_review` if pending chargeback or inspection_hold; `accepted_no_receiving_exception` if receipt clean with no chargeback; `missing_receipt` only for a PO with no receipt (and then there is no receipt_id to key the row — do NOT fabricate a row).

**summary:** `release_invoice_ids`/`hold_invoice_ids` (sorted); `approved_chargeback_total`/`pending_chargeback_total`/`net_release_total` (net_release_total = Σ net_release_amount over RELEASED invoices); `authoritative_sources` ⊆ {`procureops_po_records`,`procureops_receipt_records`,`procureops_ap_records`,`local_chargeback_register`}; `supporting_only_sources` ⊆ {`ap_release_request_note`,`stale_po73xx_alias_note`}; `followup_actions` ⊆ {`ask_receiving_for_vantix_receipt`,`hold_luma_duplicate_receipt_for_separate_invoice`,`route_po00031_quality_review`,`post_approved_chargeback_netting`} — include each that applies.

### Pitfalls (Family B)
- The invoice for a batch is the one with `receipt_id == batch_id`, NOT any invoice on the PO. Other receipts on the same PO (e.g. a later `accepted_with_note` receipt) belong to a different invoice/batch.
- For single-batch closeout, exclude receipts dated after the export/review date even if on the same PO.
- `billed_qty` is per the invoice line, not the PO qty. Billed can exceed ordered (AP Quantity Variance) — don't clamp.
- A receipt's `status: "accepted"` does not mean the invoice is releasable — the invoice may still be `on_hold` for QTY_VARIANCE (billed > received). Keep it on hold.
- `hold_code: "NO_RECEIPT"` on an invoice whose `receipt_id` is populated is a data quirk: resolve by the actual receipt + chargeback, not the literal hold code.
- Damage rejection requires `quantity_rejected > 0` or `inspection_status: "failed"` — a memo note saying "no visible damage" means do NOT infer DAMAGE_REJECTION.
- `net_release_amount` subtracts only APPROVED chargebacks; pending chargebacks leave the invoice held at full total.
- `excluded_same_po_receipt_ids` is non-empty only when another receipt on the same PO exists for a different invoice (duplicate-receipt scenario). When the PO has a single receipt, it's `[]`.
- `supporting_only_sources` must stay out of `authoritative_sources` (requester comments and alias notes are not authoritative).
- Don't create a `receiving_exceptions` row keyed by a missing receipt_id; the missing-receipt case lives in `release_decisions` + `followup_actions`.

---

## 4. Family C — AP close / vendor balance / hold-release (train_003 / test_002)

**Trigger:** "AP close", "vendor-balance reconciliation", a list of invoice_ids, a close_date, memo stating opening balance (often 0.00) and a payment cutoff (e.g. "payments scheduled through 2026-06-30 reduce the close balance").

### Query recipe
For each target `invoice_id`:
1. `GET /ap_invoices/<invoice_id>` (po_id, supplier_id, status, hold_code, total, lines[]→quantity_billed, invoice_date).
2. `GET /purchase_orders/<po_id>` (program_id, lines[]→quantity — the PO qty, for variance %).
3. `GET /receipts/<invoice.receipt_id>` if non-null (lines[]→quantity_received). If null → no receipt.
4. `GET /suppliers/<supplier_id>` (name).
5. `GET /payments?invoice_id=<invoice_id>` → scheduled payments within the cutoff (`scheduled_date <= cutoff`, status `scheduled`/`paid` typically; follow the memo's cutoff rule).

### invoice_decisions[] (sorted by invoice_id)
- `hold_decision` ∈ {`HOLD`,`RELEASE`}. `RELEASE` when `status == "approved"` (clean) AND three-way match holds. `HOLD` when `status ∈ {on_hold, pending_receipt}` or hold_code non-null or no receipt.
- `hold_code`: invoice.hold_code or null.
- `release_to_payment`: boolean = (hold_decision == RELEASE).
- `quantity_billed` = Σ invoice line `quantity_billed` (2 dp).
- `quantity_received` = Σ receipt line quantity_received if a receipt exists else `0.00`.
- `quantity_variance` = `quantity_billed − quantity_received` (2 dp).
- `quantity_variance_pct` = `quantity_variance / PO_quantity × 100` (1 dp). Use the PO line quantity as denominator. When no receipt, this is billed/PO (can be 100%).
- `invoice_total` = invoice.total.
- `scheduled_payment_amount` = Σ payment.amount for payments within the cutoff (0.00 if none).
- `net_balance_impact` = `invoice_total − scheduled_payment_amount` (2 dp).
- `reason_codes` (alphabetical; allowed: `APPROVED_THREE_WAY_MATCH, NO_RECEIPT, QTY_VARIANCE, SCHEDULED_PAYMENT_FOUND`):
  - `NO_RECEIPT`: invoice.receipt_id is null / no receipt exists.
  - `QTY_VARIANCE`: a receipt exists but `quantity_billed != quantity_received`.
  - `APPROVED_THREE_WAY_MATCH`: status approved, receipt exists, billed==received, price matches (clean release).
  - `SCHEDULED_PAYMENT_FOUND`: a scheduled/paid payment within the cutoff exists.
  - Rule of thumb: `NO_RECEIPT` and `QTY_VARIANCE` are alternative root-cause codes (no receipt → NO_RECEIPT; receipt but mismatched → QTY_VARIANCE). A clean released invoice carries `APPROVED_THREE_WAY_MATCH` + `SCHEDULED_PAYMENT_FOUND` (if a payment exists).

### vendor_balances[] (sorted by supplier_id)
Per supplier in the slice:
- `opening_balance` = memo's stated opening (e.g. 0.00).
- `invoice_total` = Σ invoice_total for that supplier's invoices in the slice.
- `scheduled_payments` = Σ scheduled_payment_amount.
- `held_invoice_total` = Σ invoice_total where hold_decision == HOLD.
- `releasable_invoice_total` = Σ invoice_total where hold_decision == RELEASE.
- `close_balance` = `opening_balance + invoice_total − scheduled_payments` (2 dp).
- `balance_status` ∈ {`OPEN_HELD`,`OPEN_APPROVED`,`FULLY_SCHEDULED`}: `FULLY_SCHEDULED` when scheduled_payments == invoice_total (net 0); `OPEN_HELD` when any held invoice; else `OPEN_APPROVED`.

### program_summary[] (sorted by program_id)
Per program in the slice:
- `invoice_count`, `invoice_total` (Σ), `held_total` (Σ held invoice totals), `released_total` (Σ released invoice totals), `net_close_balance` = `invoice_total − scheduled_payments` for that program.

### Queues & total
- `payment_hold_queue` = invoice_ids with hold_decision HOLD, sorted ascending.
- `payment_release_queue` = invoice_ids with hold_decision RELEASE, sorted ascending.
- `total_close_balance` = Σ vendor close_balance (= Σ net_balance_impact across invoices), 2 dp.

### Pitfalls (Family C)
- `quantity_variance_pct` denominator is the **PO quantity**, not received or billed. Round to 1 decimal.
- A scheduled payment reduces the close balance only if it falls within the memo's cutoff (e.g. `scheduled_date <= 2026-06-30`); earlier/later payments may not count.
- `pending_receipt` invoice status with `hold_code: NO_RECEIPT` is a HOLD (not release) — quantity_received = 0.00, variance = billed, variance% = 100%.
- `approved` status with a matching scheduled payment → RELEASE and `FULLY_SCHEDULED` vendor balance (net 0), not OPEN_APPROVED.
- The slice is the named invoices only — do not pull other invoices for the same supplier/program into vendor_balances/program_summary.
- `total_close_balance` must equal both Σ vendor close_balances and Σ invoice net_balance_impacts — use this as a self-check.
- opening_balance is per the memo (0.00 here) — do not infer from API.

---

## 5. Family D — Change-control contract amendment (train_004 / test_005)

**Trigger:** "change-control decision", an amendment memo (`change_memo.json`) with program_id, contract_id, supplier_id, sku, `requested_incremental_quantity`, tax_rate_percent, and `business_controls` rules.

### Query recipe
1. `GET /contracts/<contract_id>` (status, price_type, unit_price, ceiling_amount, effective/expiry).
2. `GET /programs/<program_id>` (budget_cap, committed_amount).
3. `GET /budget_snapshots?program_id=<pg>` → snapshot with `snapshot_date <= memo_date` (latest).
4. `GET /purchase_orders?contract_id=<contract_id>` → ALL POs on the contract; split by `status == cancelled` (excluded) vs the rest (included).
5. `GET /purchase_requisitions/<source_requisition_id>` (status) + `GET /approval_events?object_id=<req_id>` (latest event).
6. `GET /suppliers/<supplier_id>` (status, risk_rating) + `GET /vendor_risk_events?supplier_id=<sid>` (open as of memo_date).

### contract_check
- `contract_status`, `price_type`, `unit_price`, `ceiling_amount` from contract.
- `noncancelled_subtotal` = Σ `po.subtotal` for POs on contract with `status != cancelled`. (Dollar-based, not quantity-based.)
- `headroom_before_change` = `ceiling_amount − noncancelled_subtotal`.
- `requested_quantity` = memo's `requested_incremental_quantity`.
- `requested_subtotal` = `requested_quantity × unit_price` (this is the `contract_ceiling_exposure` — subtotal BEFORE tax & freight, per memo).
- `headroom_after_change` = `headroom_before_change − requested_subtotal`.
- `ceiling_ok` = `headroom_after_change >= 0`.

### program_budget_check
- `snapshot_id`, `budget_cap`, `committed_amount` from the as-of snapshot.
- `remaining_budget` = `budget_cap − committed_amount` (do NOT subtract `pending_invoice_amount`).
- `requested_tax` = `requested_subtotal × tax_rate_percent / 100`.
- `requested_total` = `requested_subtotal + requested_tax` (+ freight ONLY if the memo provides a freight amount; the AX17 memo provides none).
- `budget_after_change` = `remaining_budget − requested_total`.
- `budget_ok` = `budget_after_change >= 0`.
- `max_quantity_with_current_budget` = `floor(remaining_budget / (unit_price × (1 + tax_rate_percent/100)))` — integer, tax-inclusive per the memo's budget_exposure rule.

### approval_check
- `source_requisition_id` from memo.
- `latest_event_id/action/actor/event_date` = the approval_event with max `event_date` for the requisition (often only one).
- `approval_ok` = `latest_action` ∈ memo's `approval_good_actions` (here `["approved"]`). `submitted`/`held`/`rejected` → false.
- **Do NOT use requisition.status as the approval signal** — a requisition can be `converted` while its approval event is only `submitted`. The approval_events trail is authoritative.

### supplier_risk_check
- `supplier_status`, `supplier_risk_rating` from supplier.
- `open_event_ids` = open vendor_risk_events as of memo_date, sorted.
- `severe_open_event_ids` = those with severity ∈ {`high`,`critical`} (medium/low excluded), sorted.
- `supplier_risk_ok` = `severe_open_event_ids` is empty (per memo: watch rating is "context only unless an open severe event is found"). A `watch` rating alone does NOT make this false.

### decision (enum)
`release_amendment | hold_for_budget | hold_for_approval | hold_for_supplier_risk | hold_for_budget_and_approval | reject_contract_mismatch`
- `reject_contract_mismatch`: contract missing/inactive/expired, or contract.sku ≠ memo sku, or contract.program_id ≠ memo program.
- Else combine failing checks: contract `ceiling_ok` is a gate but typically not a separate hold label (if ceiling fails with otherwise-ok, it forces reduce-quantity → `hold_for_budget`). Map:
  - budget not ok + approval not ok → `hold_for_budget_and_approval`.
  - only budget → `hold_for_budget`; only approval → `hold_for_approval`; only severe risk → `hold_for_supplier_risk`.
  - none failing (ceiling_ok, budget_ok, approval_ok, supplier_risk_ok, contract active/matching) → `release_amendment`.

### required_actions (enum, sorted ascending)
`obtain_final_requisition_approval | raise_budget_exception_or_reduce_quantity | resolve_supplier_risk_hold | none`
- `obtain_final_requisition_approval` if approval not ok.
- `raise_budget_exception_or_reduce_quantity` if budget not ok (or ceiling exceeded).
- `resolve_supplier_risk_hold` if severe open risk.
- `none` only when all ok (and then it's the sole entry).

### supporting_ids (sorted ascending)
- `included_po_ids` = non-cancelled POs on the contract.
- `excluded_cancelled_po_ids` = cancelled POs on the contract.
- `approval_event_ids` = all approval_events for the source requisition.

### summary
- `blocker_count` = number of failing checks among {budget, approval, supplier_risk( severe)} (ceiling/contract mismatch counts separately if present). For the AX17 memo: 2 (budget + approval).
- `currency` = "USD".
- `ready_to_release` = (decision == `release_amendment`).

### Pitfalls (Family D)
- **Exclude cancelled POs** from `noncancelled_subtotal` (cancelled POs on the contract must be in `excluded_cancelled_po_ids`, not summed). Including them understates headroom.
- **Headroom is dollar-based** (ceiling − Σ subtotal), not quantity-based. Don't sum PO quantities.
- `remaining_budget` = `budget_cap − committed_amount` only. The snapshot's `pending_invoice_amount` is informational and is NOT subtracted here.
- Use the **snapshot** dated <= memo_date for budget figures, not the live `programs.committed_amount` (they usually agree, but the snapshot is the as-of truth).
- Approval state comes from `approval_events`, NOT `purchase_requisitions.status`. A `converted`/`approved` requisition status does not guarantee a final `approved` event — check the latest action against `approval_good_actions`.
- `watch` risk rating is context only and does NOT block; only an open **severe** (high/critical) event blocks. Medium open events do not.
- `max_quantity_with_current_budget` is tax-inclusive (floor to integer). Compare to `requested_quantity` to confirm the overrun.
- `requested_subtotal` for the ceiling check excludes tax/freight; `requested_total` for the budget check includes tax (+ freight if memo provides). Don't mix the two.
- `ceiling_ok` can be true while `budget_ok` is false (contract has room; program budget does not) — the AX17 memo is exactly this case.

---

## 6. Cross-family misjudgment checklist
1. as_of scoping: fetch by link filter, then client-filter dates `<= as_of`. Future receipts/invoices/events excluded.
2. Open risk = status `{monitoring, open}` only; `closed`/`resolved` never count. Severe = `{high, critical}`.
3. Multi-receipt POs: pick the receipt by `receipt_id` match, not by PO alone. Duplicate/later receipts are `excluded_same_po_receipt_ids` or out-of-scope.
4. Multi-invoice POs: billed_qty/price come from the invoice whose `receipt_id` matches the batch, not any PO invoice.
5. Amounts: API dollars vs template cents — convert per field. Quantities 2 dp; variance% 1 dp; completion ratio 4 dp.
6. Payment cutoff: only payments within the memo's cutoff reduce close balance.
7. Don't trust invoice `hold_code` literally when `receipt_id` is populated — verify against the receipt + chargeback.
8. AP status `approved` ≠ releasable when a receiving `inspection_hold` or `pending_quality_review` chargeback exists.
9. Budget: `headroom`/`remaining_budget` use `cap − committed`; readiness/budget_ok may additionally weigh `pending_invoice_amount` (Family A) or the requested exposure (Family D) — don't conflate the two computations.
10. Approval: use `approval_events` latest action vs the memo's `approval_good_actions`; ignore requisition.status for final-approval decisions.
11. Sort all ID lists ascending unless the template says otherwise; treat list fields as sets unless sorting is specified.
12. `authoritative_sources` = API record families + local chargeback register; requester comments / alias notes are `supporting_only_sources` only.
