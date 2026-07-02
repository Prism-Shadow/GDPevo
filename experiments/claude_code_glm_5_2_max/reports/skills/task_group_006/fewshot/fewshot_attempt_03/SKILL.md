# ProcureOps ERP Procurement Control — Solver Skill (task_group_006)

Executable experience for the ProcureOps shared API. Distilled from 5 train tasks
across 4 families: A sourcing-nomination readiness, B receiving-control closeout
(+ chargeback-release sub-pattern), C AP close / vendor balance + hold-release,
D change-control contract amendment. Recipe-oriented; not a restatement of train answers.

## 0. Environment & API mechanics

- Base URL: `<remote-env-url>` (prompts' `http://127.0.0.1:8006` == this service). Use `curl`.
- By id: `GET /<coll>/<id>` -> the record object. List: `GET /<coll>` -> `{"count":N,"results":[...]}`.
- There is NO pagination / `_limit` param. Unknown query params are treated as **field filters**
  (substring, case-insensitive, including nested list values) and a non-matching filter returns 0.
  Do not invent params like `limit`/`page`. Use real field filters: `?po_id=`, `?supplier_id=`,
  `?program_id=`, `?invoice_id=`, `?object_id=`. Date ranges: `?start=YYYY-MM-DD&end=YYYY-MM-DD`
  on the collection's date field (inclusive).
- Collections (id field / date field): programs(`program_id`) · suppliers(`supplier_id`) ·
  items(`sku`) · contracts(`contract_id` / `effective_date`) · purchase_requisitions(`requisition_id` / `need_by`)
  · purchase_orders(`po_id` / `order_date`) · receipts(`receipt_id` / `receipt_date`) ·
  ap_invoices(`invoice_id` / `invoice_date`) · payments(`payment_id` / `scheduled_date`) ·
  approval_events(`event_id` / `event_date`) · budget_snapshots(`snapshot_id` / `snapshot_date`) ·
  vendor_risk_events(`event_id` / `event_date`). Alias paths exist (`/ap/invoices`, `/budgets`, `/approvals`, etc.).
- Discovery: `GET /manifest` (record counts + anchor ids, no answers), `GET /` (endpoint list), `GET /health`.
- Fetch by id from the memo/template anchors rather than pulling whole collections (cheatsheet is pre-verified).

### Cross-cutting conventions
- **Units:** every API amount is USD **dollars**. All 5 train templates used USD dollars rounded to **2 decimals**
  (the phrase "round to cents" means 2-dp dollars, NOT integer cents). If a test template field literally says
  "USD cents"/"integer cents", convert dollars -> cents (`×100`, rounded). Read each template field's stated unit;
  do not assume.
- **Quantities:** 2-dp in general; PO/receipt/invoice line quantities in this group are integers — emit integers
  where the template declares `integer`, else 2-dp.
- **As-of / date gating** (critical — almost every bug is a date-gate bug):
  - receipts: `receipt_date <= as_of`
  - invoices: `invoice_date <= as_of` (or `<= review_as_of`)
  - vendor_risk_events: `event_date <= as_of` AND `status in {open, monitoring}` = "open supplier risk"
  - payments: `scheduled_date <= cutoff` (close desk names the cutoff, e.g. "through 2026-06-30")
  - budget_snapshots: `snapshot_date <= as_of`, take the **latest** (snapshot_id convention `BUD-<program_id>`)
  - approval_events: take the **latest by event_date** for a given `object_id`
  - contracts: `effective_date <= as_of <= expiry_date` AND `status==active` for a "current" contract
- **Open supplier risk** = vendor_risk_events with `status in {open, monitoring}` and `event_date <= as_of`.
  **Severe** = additionally `severity in {high, critical}`. `related_object_id` may reference a PO/contract.
- **Reconciliation chain:** PO -> receipts (same `po_id`; multiple allowed incl. later duplicates) -> invoices
  (`invoice.po_id` and `invoice.receipt_id`) -> payments (`payment.invoice_id`). Contract (`contract_id`) links
  PO (`po.contract_id`) and is the **price-match anchor**: `contract.unit_price == PO line.unit_price ==
  invoice line.unit_price`. Cancelled POs (`status==cancelled`) are excluded from contract-usage totals.
- **Three-way match** = PO + receipt + invoice agree on qty & price AND `invoice.receipt_id` is non-null/linked.
- **Sorting:** list fields ascending unless template says otherwise. Fields marked "set" are evaluator-sorted
  (emit any order; still prefer ascending). Booleans lowercase JSON. `null` not `"null"`.

---

## A. Sourcing nomination readiness  (train_001 pattern; test_003)

**Goal:** per package SKU, name the nominated supplier, a nomination decision, evidence/exception id sets,
and blocker codes; then a committee action block. As-of date is the readiness snapshot date.

### Query recipe
1. `GET /programs/<program_id>` -> owner, budget_cap, committed_amount.
2. For each package SKU + its package PO (from memo): `GET /purchase_orders/<po_id>` (lines, due_date,
   contract_id, requisition_id, supplier_id). `GET /purchase_requisitions/<requisition_id>` (need_by, status).
3. Contract lookup: `GET /contracts?program_id=<prg>` then pick the one with matching `sku`+`supplier_id`,
   `status==active`, dates covering as_of; else no contract. (Or fetch a contract_id directly if memo gives it.)
4. `GET /receipts?po_id=<po_id>` -> filter `receipt_date <= as_of` = receipt_evidence.
5. `GET /ap_invoices?po_id=<po_id>` (or `?supplier_id=` then filter po) -> invoice exceptions as of date.
6. `GET /vendor_risk_events?supplier_id=<sup>` -> open/monitoring events as of date.
7. `GET /suppliers/<supplier_id>` -> risk_rating (drives `supplier_watch`).

### Field rules
- `program_summary.owner` = programs.owner. `budget_headroom_usd` = `budget_cap - committed_amount` (use the
  **programs row**, not the snapshot's pending-inclusive figure). Round 2dp.
- `overall_readiness` = **worst** of line `readiness_status` (ready < at_risk < not_ready).
- `package_line_skus`: sorted ascending.
- Per line:
  - `selected_supplier_id` = PO.supplier_id (the nominated supplier for that SKU/PO).
  - `primary_requisition_id` = PO.requisition_id.
  - `commercial_basis_id` = active contract_id for sku+supplier+program as of date, else `null`.
  - `package_po_ids` = the package PO id(s) for the SKU (sorted).
  - `receipt_evidence_ids` = receipts on the package PO with `receipt_date <= as_of` (sorted). Empty if none.
  - `invoice_exception_ids` = invoices on the package PO with non-clean status
    (`status in {on_hold, pending_receipt}` OR `hold_code != null`) AND `invoice_date <= as_of`. Sorted.
    (Approved/paid/cancelled invoices are NOT exceptions.)
  - `risk_event_ids` = open/monitoring VRE for the supplier with `event_date <= as_of`. Sorted.
  - `blocker_codes` (sorted ascending, use `none` if empty):
    - `missing_contract` — no active contract covering sku+supplier as of date (commercial_basis_id null).
    - `pending_receipt` — `receipt_evidence_ids` is empty (goods not yet received on the package PO as of date).
    - `late_due_date` — **PO.due_date > requisition.need_by** (PO promises delivery after the needed-by date).
      *Not* as-of vs need_by; it is PO-due vs req-need_by.
    - `ap_hold` — any invoice exception with `status == on_hold` (explicit AP hold). pending_receipt invoices do
      NOT set this (they set `pending_receipt`).
    - `open_supplier_risk` — any open/monitoring VRE for the supplier as of date.
    - `supplier_watch` — `supplier.risk_rating == "watch"`.
    - `none` — no blockers.
- `readiness_status`: **not_ready** if any hard blocker (`missing_contract`, `pending_receipt`,
  `late_due_date`); else **at_risk** if any soft blocker (`ap_hold`, `open_supplier_risk`, `supplier_watch`);
  else **ready**.
- `nomination_decision`: ready->`nominate`, at_risk->`conditional_nomination`, not_ready->`hold`.

### committee_action
- `nominate_now_supplier_ids` = suppliers of lines with decision `nominate` (sorted).
- `conditional_supplier_ids` = suppliers of `conditional_nomination` lines (sorted).
- `hold_supplier_ids` = suppliers of `hold` lines (sorted).
- `next_owner` (enum `buyer|finance_ops|quality_ops|program_owner|ap_team`): pick from **conditional lines
  first, else not_ready lines**; map the dominant blocker: `ap_hold`->`ap_team`;
  `missing_contract`/`pending_receipt`/`late_due_date`/`supplier_watch`/`open_supplier_risk`->`buyer`;
  budget shortfall->`finance_ops`; inspection/quality->`quality_ops`; all ready->`program_owner`.
  (train: conditional LMP-228 has ap_hold -> `ap_team`.)
- `send_to_committee`: `yes` iff `hold_supplier_ids` is empty (no not_ready line); else `no`.

### Pitfalls (A)
- Do NOT count approved/paid/cancelled invoices as exceptions. Do NOT count receipts/invoices dated after as_of.
- `late_due_date` is PO-due vs req-need_by, not as-of vs need_by (a future need_by with a later PO due still triggers).
- `pending_receipt` blocker keys off **receipts** (no goods received), not the invoice `pending_receipt` status.
- An invoice on_hold for PRICE_VARIANCE still sets `ap_hold` (any on_hold invoice counts).
- Use the programs row for headroom, not budget_snapshot (pending_invoice_amount is informational here).

---

## B. Receiving-control closeout  (train_002 pattern; test_001/test_004)

Two sub-patterns: (B1) single-batch receiving closeout (train_002); (B2) chargeback-release packet across
multiple POs/receipts/invoices (train_005). Both reconcile ordered/received/billed and decide AP hold/release.

### B1. Single-batch closeout (train_002)

**Query recipe:** `GET /receipts/<batch_id>` -> po_id, supplier_id, warehouse_id, receipt_date, packing_slip,
receiver, status, lines[]. Then `GET /purchase_orders/<po_id>` (program_id, status, contract_id, lines ordered
qty + unit_price, due_date). `GET /contracts/<contract_id>` (unit_price anchor). Find the invoice(s) for the PO:
`GET /ap_invoices?po_id=<po_id>`; pick the one tied to this batch (`invoice.receipt_id == batch_id`) if multiple.
`GET /suppliers/<supplier_id>` (risk_rating). `GET /vendor_risk_events?supplier_id=` (open as of export date).

**inspection_summary** = receipt identity fields (po_id, program_id [from PO], supplier_id, supplier_name
[from suppliers], warehouse_id, receipt_date, packing_slip, receiver).

**line_reconciliation** (sort by po_line_id ascending), one row per PO line matched to the receipt line +
invoice line:
- `ordered_qty` = PO line.quantity; `received_qty` = receipt line.quantity_received;
  `rejected_qty` = receipt line.quantity_rejected; `billed_qty` = invoice line.quantity_billed.
- `short_qty_vs_po` = ordered - received. `unreceived_billed_qty` = billed - received (clamped >= 0).
- `receipt_completion_ratio` = received / ordered, precision 4.
- `po_unit_price`, `contract_unit_price` (from contract; null/omit if no contract), `invoice_unit_price`
  — precision 2 USD. `contract_price_match` = (po_unit_price == contract_unit_price) when contract exists.

**invoice_review**: invoice_id, invoice_status, hold_code, receipt_status (receipt.status), po_status (PO.status),
`exception_codes` (set; allowed: `INVOICE_QTY_EXCEEDS_RECEIPT`, `PARTIAL_RECEIPT`, `SUPPLIER_WATCH_RISK`,
`PRICE_MISMATCH`, `DAMAGE_REJECTION`, `NO_EXCEPTION`):
- `INVOICE_QTY_EXCEEDS_RECEIPT` — billed > received.
- `PARTIAL_RECEIPT` — received < ordered (or PO.status == partial_receipt / open).
- `SUPPLIER_WATCH_RISK` — supplier.risk_rating == watch (or an open risk event for the supplier).
- `PRICE_MISMATCH` — po_unit_price != contract_unit_price OR != invoice_unit_price.
- `DAMAGE_REJECTION` — quantity_rejected > 0.
- `NO_EXCEPTION` — none of the above.

**financials** (USD 2dp): `received_goods_value` = received × po_unit_price; `unreceived_goods_value` =
(ordered - received) × po_unit_price; `invoice_subtotal`/`invoice_freight`/`invoice_tax`/`invoice_total` from
the invoice record.

**decision** (enums):
- `batch_disposition`: `accept_partial_hold_variance` (partial receipt + AP hold on variance, no damage) |
  `release_full_invoice` (full receipt, three-way match, prices match) | `reject_batch` (damage/rejection) |
  `manual_recount_required` (severe unmatched qty needing recount).
- `ap_action`: `keep_invoice_on_hold` (invoice on_hold / variance / price mismatch) | `release_invoice`
  (three-way match, approved) | `void_invoice` (duplicate/unlinked).
- `receiving_action`: `record_shortage_follow_up` (short_qty_vs_po > 0) | `no_receiving_action` (complete) |
  `reject_all_units` (damage).
- `supplier_action`: `request_credit_or_remaining_delivery` (shortage -> credit or backfill) |
  `no_supplier_action` (complete, clean) | `supplier_debit_for_damage` (damage).
- Mapping for partial+hold+watch (train_002): accept_partial_hold_variance / keep_invoice_on_hold /
  record_shortage_follow_up / request_credit_or_remaining_delivery.

**supplier_risk_context**: supplier_risk_rating (suppliers.risk_rating), has_open_supplier_risk (bool),
open_supplier_risk_event_ids (open/monitoring VRE as of export date, set).

**evidence.endpoint_record_ids** = set of every record id you fetched (PO, receipt, contract, item, supplier,
invoice, risk events). `task_payloads_reviewed` = set of relative payload paths read (e.g. `input/payloads/receiving_memo.md`).

### B2. Chargeback-release packet  (train_005 pattern)

A packet gives `target_ids` (program_id, po_ids[], receipt_ids[], invoice_ids[]) plus a local
`chargeback_register_excerpt` (authoritative for chargebacks) and `release_request_note` (supporting-only
requester comments). Produce per-invoice release decisions + per-receipt receiving exceptions + a summary.

**Query recipe:** for each invoice_id: `GET /ap_invoices/<id>` (po_id, total, status, hold_code, lines).
For each po_id: `GET /purchase_orders/<po_id>` (lines ordered qty + unit_price, contract_id). For each
receipt_id in target_ids: `GET /receipts/<id>` (lines received, status). Also `GET /receipts?po_id=<po_id>` to
discover ALL receipts on each PO (to compute `excluded_same_po_receipt_ids` and detect missing receipts).
Resolve chargebacks from the **local register excerpt** (do NOT expect a chargebacks API endpoint).

**release_decisions** (one per target invoice, ordering = invoice_id ascending):
- `receipt_ids_in_scope` = receipts r with `r.po_id == invoice.po_id` AND `r.receipt_id ∈ target_ids.receipt_ids`.
- `excluded_same_po_receipt_ids` = receipts r with `r.po_id == invoice.po_id` AND `r.receipt_id ∉ target_ids`
  (duplicate / separate-invoice receipts on the same PO).
- Decision tree:
  - No receipt exists on the PO at all -> `hold_missing_receipt`, `primary_reason` `no_receipt_on_po`,
    approved/pending chargeback 0, `net_release_amount` 0.
  - Receipt(s) exist but any linked chargeback has `status != approved` (e.g. `pending_quality_review`) ->
    `hold_pending_quality_chargeback`, `primary_reason` `inspection_hold_pending_chargeback`, net 0.
  - Approved chargeback exists -> `release_net_after_approved_chargeback`,
    `primary_reason` = `approved_qty_chargeback` if the chargeback reason is `Underage Quantity`,
    `approved_ap_quantity_variance` if reason is `AP Quantity Variance`. `net_release_amount` =
    `invoice_total - approved_chargeback_amount`.
  - (Clean three-way match, no chargeback -> release full; primary_reason accordingly.)
- `approved_chargeback_amount` = sum over the in-scope receipt's chargebacks where `status==approved` of
  `basis_quantity × unit_cost`. `pending_chargeback_amount` = sum where `status != approved`.
- **Chargeback basis/unit conventions** (from register): `Underage Quantity` -> basis = ordered - received,
  unit_cost = PO/contract unit_price. `AP Quantity Variance` -> basis = billed - received, unit_cost = PO line
  unit_price. Amount = basis × unit_cost.

**receiving_exceptions** (one row per target receipt + one `MISSING:<po_id>` row for any PO with no receipt):
- `exception_codes` derived per receipt from the PO/receipt/invoice trio (set, ordering irrelevant/evaluator sorts):
  - `Underage Quantity` — ordered > received.
  - billed > received AP-side code:
    - `Severe Unmatched Quantity` — when ordered > received (shortage also present, compound).
    - `AP Quantity Variance` — when ordered == received (PO complete, AP over-bill only).
  - `Inspection Hold` — `receipt.status == inspection_hold` (or status contains "hold").
- `chargeback_status` = the register chargeback status for that receipt (`approved` | `pending_quality_review`
  | ...); `not_applicable` for the MISSING row.
- `resolution_status`: `net_release_ready` (approved chargeback) | `hold_for_quality_review` (pending/inspection)
  | `missing_receipt` (no receipt on PO).

**summary**: `release_invoice_ids` (decisions == release_net..., sorted) · `hold_invoice_ids` (hold decisions,
sorted) · `approved_chargeback_total` (sum approved_chargeback_amount over release decisions) ·
`pending_chargeback_total` (sum pending over hold decisions) · `net_release_total` (sum net_release_amount over
releases) · `authoritative_sources` = `procureops_ap_records`, `procureops_po_records`,
`procureops_receipt_records`, `local_chargeback_register` · `supporting_only_sources` =
`ap_release_request_note`, `stale_po73xx_alias_note` (requester comments / alias notes — never authoritative) ·
`followup_actions`: `ask_receiving_for_vantix_receipt` (missing receipt), `hold_luma_duplicate_receipt_for_separate_invoice`
(excluded same-PO receipt), `post_approved_chargeback_netting`, `route_<po>_quality_review` (pending chargeback).

### Pitfalls (B)
- **AP "approved" does not override a receiving hold / pending chargeback** (train_005 AP-00027: invoice
  approved but receipt inspection_hold + pending chargeback -> held). The receiving/chargeback status governs.
- **Verify requester receipt claims against the API.** A requester may mention a "PO-73xx-style generated
  receipt" that does not exist; if no receipt record is on the PO, `hold_missing_receipt`. The alias note is
  supporting-only; use the available shared PO ids it points to.
- Multiple receipts can share a `po_id`; later duplicate receipts not in the packet scope go to
  `excluded_same_po_receipt_ids`, not in_scope.
- prices: use contract.unit_price as anchor when a contract exists; PO-00038 / PO-AX17-4519 have
  `contract_id == null` (no contract) — price-match still compares PO line vs invoice line unit_price.
- `received_goods_value` uses **po_unit_price**, not standard_cost and not invoice unit_price.
- Do not double-count chargebacks: only chargebacks whose status maps to approved reduce the net release;
  pending ones hold the invoice at full value.

---

## C. AP close / vendor balance + hold-release  (train_003 pattern; test_002)

**Goal:** for a named slice of invoices, per-invoice payment decision, per-supplier balance, per-program
totals, and the hold/release queues. Opening balance for the slice is given as 0 (or the memo's value).

### Query recipe
1. For each invoice_id: `GET /ap_invoices/<id>` -> po_id, supplier_id, status, hold_code, total, lines[].
2. `GET /purchase_orders/<po_id>` -> program_id, lines ordered qty + unit_price.
3. `GET /receipts?po_id=<po_id>` -> received qty (sum quantity_received across receipt lines for the SKU; 0 if none).
   If `invoice.receipt_id` non-null, prefer that receipt for the linked-receipt check.
4. `GET /suppliers/<supplier_id>` -> name.
5. `GET /payments?invoice_id=<invoice_id>` -> scheduled payments; filter `scheduled_date <= cutoff` and
   `status in {scheduled, paid}`.

### invoice_decisions (ordering: invoice_id ascending)
- `program_id` from PO; `po_id`, `supplier_id`, `supplier_name`; `invoice_status` (raw API status).
- `hold_decision` enum `HOLD|RELEASE`:
  - `RELEASE` when `invoice.status == approved` AND three-way match (qty & price agree, receipt linked).
  - `HOLD` when `status in {on_hold, pending_receipt}` or `hold_code != null`.
- `hold_code` = invoice.hold_code (e.g. `QTY_VARIANCE`, `NO_RECEIPT`) or `null`.
- `release_to_payment` = (hold_decision == RELEASE) — boolean.
- `quantity_billed` = invoice line.quantity_billed; `quantity_received` = received qty (0.00 if no receipt);
  `quantity_variance` = billed - received; `quantity_variance_pct` = variance / **PO quantity** × 100, 1 decimal.
- `invoice_total` = invoice.total (USD 2dp).
- `scheduled_payment_amount` = sum of payment.amount for this invoice with `scheduled_date <= cutoff` and
  status scheduled/paid (0.00 if none).
- `net_balance_impact` = invoice_total - scheduled_payment_amount (2dp).
- `reason_codes` (alphabetical; allowed: `APPROVED_THREE_WAY_MATCH`, `NO_RECEIPT`, `QTY_VARIANCE`,
  `SCHEDULED_PAYMENT_FOUND`):
  - `APPROVED_THREE_WAY_MATCH` — status approved + three-way match.
  - `NO_RECEIPT` — invoice pending_receipt / receipt_id null / no receipt on PO.
  - `QTY_VARIANCE` — invoice on_hold with hold_code QTY_VARIANCE (or billed != received beyond tolerance).
  - `SCHEDULED_PAYMENT_FOUND` — a scheduled/paid payment within cutoff exists.
  - Emit all that apply (an approved+released invoice with a scheduled payment gets both APPROVED_THREE_WAY_MATCH
    and SCHEDULED_PAYMENT_FOUND).

### vendor_balances (ordering: supplier_id ascending)
- `opening_balance` = memo's slice opening (0.00 in train).
- `invoice_total` = sum of invoice.total for that supplier's invoices in the slice.
- `scheduled_payments` = sum of scheduled_payment_amount for that supplier.
- `held_invoice_total` = sum of invoice_total where hold_decision == HOLD.
- `releasable_invoice_total` = sum of invoice_total where hold_decision == RELEASE.
- `close_balance` = opening_balance + invoice_total - scheduled_payments (2dp).
- `balance_status` enum `OPEN_HELD|OPEN_APPROVED|FULLY_SCHEDULED`:
  - `FULLY_SCHEDULED` — released and fully scheduled (close_balance == 0, scheduled_payments == invoice_total).
  - `OPEN_HELD` — any held invoice (held_invoice_total > 0).
  - `OPEN_APPROVED` — released but not yet scheduled (close_balance > 0, no holds).

### program_summary (ordering: program_id ascending)
- `invoice_count`, `invoice_total` (sum), `held_total` (sum of invoice_total where HOLD),
  `released_total` (sum where RELEASE), `net_close_balance` (sum of net_balance_impact).

### queues & total
- `payment_hold_queue` = invoice_ids with hold_decision HOLD (ascending).
- `payment_release_queue` = invoice_ids with hold_decision RELEASE (ascending).
- `total_close_balance` = sum of vendor close_balance (== sum of program net_close_balance), 2dp.

### Pitfalls (C)
- `quantity_variance_pct` denominator is **PO quantity**, not billed quantity.
- `scheduled_payment_amount` is gated by the **cutoff date** the close desk names; a payment scheduled after
  cutoff does NOT reduce the close balance.
- `close_balance` formula uses opening + invoice_total - scheduled_payments (NOT minus held). Held invoices
  remain in the balance (they're still owed/disputed).
- Do not net chargebacks here (that is family B2). Family C is pure AP/scheduler reconciliation.
- Use the slice's named invoices only; do not pull the supplier's full invoice history.

---

## D. Change-control contract amendment  (train_004 pattern; test_005)

**Goal:** approve/hold a quantity-increment change request against a contract ceiling AND program budget AND
requisition approval AND supplier risk. Output contract check, budget check, approval check, risk check,
supporting ids, required actions, decision.

### Query recipe
1. From the change memo: program_id, contract_id, supplier_id, sku, requested_incremental_quantity,
   source_requisition_id, tax_rate_percent, business_controls (ceiling vs budget exposure definitions,
   approval_good_actions, supplier_watch policy).
2. `GET /contracts/<contract_id>` -> status, price_type, unit_price, ceiling_amount, dates.
3. `GET /purchase_orders?contract_id=<contract_id>` (or list and filter) -> all POs under the contract.
   Split into included (status != cancelled) vs excluded_cancelled (status == cancelled).
4. `GET /budget_snapshots?program_id=<program_id>` -> latest with `snapshot_date <= memo_date`
   (snapshot_id `BUD-<program_id>`); fetch budget_cap, committed_amount.
5. `GET /approval_events?object_id=<source_requisition_id>` -> latest by event_date.
6. `GET /suppliers/<supplier_id>` + `GET /vendor_risk_events?supplier_id=` -> open + severe-open as of memo_date.

### contract_check
- `contract_status`, `price_type`, `unit_price`, `ceiling_amount` from contract.
- `noncancelled_subtotal` = sum of `po.subtotal` for POs under the contract with `status != cancelled`
  (ceiling exposure = line subtotal before tax/freight, per memo's `contract_ceiling_exposure`).
- `headroom_before_change` = ceiling_amount - noncancelled_subtotal.
- `requested_quantity` = memo.requested_incremental_quantity.
- `requested_subtotal` = requested_quantity × unit_price (memo's contract_ceiling_exposure = line subtotal).
- `headroom_after_change` = headroom_before_change - requested_subtotal.
- `ceiling_ok` = headroom_after_change >= 0.

### program_budget_check
- `snapshot_id`, `budget_cap`, `committed_amount` from the snapshot; `remaining_budget` = budget_cap - committed_amount.
  (Uses committed_amount, NOT committed + pending_invoice. pending_invoice_amount is informational.)
- `requested_tax` = requested_subtotal × tax_rate_percent/100 (2dp).
- `requested_total` = requested_subtotal + requested_tax (memo's `budget_exposure` = line subtotal + estimated
  tax; add freight only if the memo provides freight — train memo had none).
- `budget_after_change` = remaining_budget - requested_total.
- `budget_ok` = budget_after_change >= 0.
- `max_quantity_with_current_budget` = floor(remaining_budget / (unit_price × (1 + tax_rate_percent/100)))
  (the largest integer qty whose tax-inclusive total fits the remaining budget).

### approval_check
- `source_requisition_id`; `latest_event_id`, `latest_action`, `latest_actor`, `latest_event_date` from the
  latest approval_events row for that object_id.
- `approval_ok` = `latest_action ∈ memo.business_controls.approval_good_actions` (train: `["approved"]`;
  `submitted`/`held`/`rejected` -> false).

### supplier_risk_check
- `supplier_status`, `supplier_risk_rating`.
- `open_event_ids` = open/monitoring VRE for supplier, event_date <= memo_date.
- `severe_open_event_ids` = those with severity in {high, critical}.
- `supplier_risk_ok` = `severe_open_event_ids` is empty (memo: watch rating is context-only unless an open
  severe event is found). A `watch`/`medium` rating alone does NOT block.

### supporting_ids
- `included_po_ids` = POs under contract with status != cancelled (sorted).
- `excluded_cancelled_po_ids` = POs under contract with status == cancelled (sorted).
- `approval_event_ids` = the approval events reviewed (the latest, or all for the requisition).

### decision & actions
- `decision` enum (seen: `hold_for_budget_and_approval`; others by failing gate: `approve`,
  `hold_for_budget`, `hold_for_approval`, `hold_for_supplier_risk`, `hold_for_ceiling`). Rule: if all four
  gates ok -> `approve`; else concatenate the failing gates (budget+approval -> `hold_for_budget_and_approval`).
- `required_actions` from failing gates: budget -> `raise_budget_exception_or_reduce_quantity`; approval ->
  `obtain_final_requisition_approval`; ceiling -> `reduce_quantity_to_ceiling` / `obtain_contract_amendment`;
  severe supplier risk -> `request_severe_risk_review` / `confirm_supplier_risk_clearance`.
- `summary.blocker_count` = number of failing gates; `currency` USD; `ready_to_release` = (blocker_count == 0).

### Pitfalls (D)
- Contract ceiling exposure and program budget exposure differ: **ceiling uses line subtotal only** (no tax,
  no freight); **budget uses subtotal + estimated tax** (+ freight only if memo provides it). Don't mix them.
- Exclude **cancelled POs** from contract usage (status == cancelled). Include partial_receipt/open/confirmed/received.
- `max_quantity_with_current_budget` is tax-inclusive: divide by `unit_price × (1+tax%)`, then floor.
- Use the **budget snapshot** dated <= memo_date (latest); the programs row gives the same committed figure but
  the snapshot is the time-point source of record. Do not add pending_invoice_amount into committed.
- `approval_ok` requires the LATEST action to be in `approval_good_actions`; a prior approved event superseded
  by a later `submitted`/`held` is NOT ok.
- `supplier_risk_ok` is driven by **severe open** events only; `watch` rating and `medium`/open events are
  context, not a blocker.

---

## Universal pitfalls & misjudgments
- **Date gating** is the #1 error source: every "as of" list (receipts, invoices, risk events, payments,
  snapshots) must be filtered `<= as_of`/cutoff. Re-read which date field each collection uses.
- **Status-as-exception vs clean:** `approved`/`paid`/`cancelled` invoices are clean; `on_hold`/`pending_receipt`
  are exceptions. `on_hold` -> ap_hold blocker / HOLD decision; `pending_receipt` -> pending_receipt blocker /
  NO_RECEIPT reason, NOT ap_hold.
- **AP-approved ≠ releasable** when receiving/chargeback holds exist (family B2). Receiving governs over AP.
- **Requester comments & alias notes are supporting-only.** Verify every claim (receipt existence, PO id) against
  the API. PO-73xx-style ids may not exist; use the shared ids the alias note points to.
- **Cancellation:** exclude `status==cancelled` POs from contract-usage sums; do not exclude them blindly from
  other contexts.
- **Price anchor:** `contract.unit_price` when a contract exists; otherwise PO line unit_price. Three-way match
  compares PO line, receipt (qty only), invoice line on qty & price.
- **Money:** API dollars; train templates are 2-dp dollars. Only convert to integer cents if a field explicitly
  demands it. Round at the end, not mid-calculation.
- **List endpoint:** no pagination; unknown params become filters returning 0. Use real field filters + start/end.
- **Endpoint id-only returns the object; list returns `{count,results}`** — handle both shapes.
- **No judge/test endpoints are used at solve time.** Do not call any `/judge` or eval endpoint.
