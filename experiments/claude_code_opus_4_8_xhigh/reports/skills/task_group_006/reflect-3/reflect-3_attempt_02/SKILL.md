---
name: reflect-3_attempt_02
description: SOP for ProcureOps ERP procurement/receiving/AP tasks — pull truth from the remote API, apply three-way-match / hold / chargeback rules, and emit JSON that exactly matches the answer template.
---

# ProcureOps Procurement / Receiving / AP Solver Skill

You produce a single `answer.json` that exactly matches the task's
`input/payloads/answer_template.json`. The ProcureOps **remote HTTP API is the
source of truth**; local payload files only name the watch set / business
request / chargeback register. When a value differs between a local payload and
the API, trust the API (the one documented exception: a *local chargeback
register* is authoritative for chargeback existence/amount/status — see below).

## 0. Read the task before fetching
1. Read `prompt.txt`, every file in `input/payloads/`, and the
   `answer_template.json`. The prompt names the as-of date, the program, and the
   anchor PO/receipt/invoice IDs to focus on.
2. The prompt may print `http://127.0.0.1:8006`. Ignore that. Use the base URL
   the runner provides for the shared API. Treat it as read-only.
3. Note every business control the memo states explicitly (tax rate, "exclude
   cancelled POs", "treat opening balance as 0.00", "freight only if provided",
   "approved actions = [...]", "watch is context-only unless severe"). These
   override generic assumptions. Apply them literally.

## 1. Using the remote API
- `GET /` lists endpoints; `GET /manifest` gives counts/anchors; `GET /health`.
- `GET /<collection>` -> `{"count":N,"results":[...]}`;
  `GET /<collection>/<id>` -> one record (404 if absent).
- Collections: `programs, suppliers, items, contracts, purchase_requisitions,
  purchase_orders, receipts, ap_invoices, payments, approval_events,
  budget_snapshots, vendor_risk_events`. Hyphen/alias forms also work
  (e.g. `purchase-orders`, `ap-invoices`, `/ap/invoices`, `approvals`,
  `budgets`, `vendor-risks`).
- Filter by any record field, case-insensitive, e.g.
  `GET /receipts?po_id=PO-...`, `GET /ap_invoices?program_id=PRG-...`,
  `GET /vendor_risk_events?supplier_id=SUP-...`.
- `start` / `end` filter the collection's primary date field (receipts ->
  receipt_date, ap_invoices -> invoice_date, payments -> scheduled_date,
  purchase_orders -> order_date, contracts -> effective_date,
  purchase_requisitions -> need_by, approval_events -> event_date,
  budget_snapshots -> snapshot_date, vendor_risk_events -> event_date).
- IMPORTANT FILTER NAMES: `approval_events` are keyed by **`object_id`**
  (e.g. `?object_id=REQ-...`), not `requisition_id`. When a filter returns 0,
  try the record's other id fields before concluding "none".
- Always pull the FULL related set, then filter yourself: e.g. for a PO get
  `GET /receipts?po_id=...` (a PO can have several receipts) and
  `GET /ap_invoices?po_id=...` (often a real exception invoice plus a clean/paid
  decoy). Do not stop at the first match.

## 2. Output conventions (these are graded strictly)
- Emit ONLY the JSON object. No prose, no markdown fences.
- `task_id`: use the template's required/literal value verbatim (often
  `train_00X` style or a `task_group_..._...` string given in the template).
- USD amounts rounded to **cents** (2 decimals). Percentages to the precision
  the template states (often 1 decimal). Ratios to stated precision (e.g. 4).
- List fields are **sets** unless the template says "sorted/ordering"; when it
  says sort, sort ascending (string sort) by the stated key. When in doubt,
  sort ascending — it never hurts a set-matched field and satisfies sort fields.
- Copy enum strings **verbatim** from the template's allowed list (exact case,
  underscores, spaces). Human-readable enums like `"Underage Quantity"` keep
  their spaces/caps.
- Booleans are real JSON booleans; nulls are JSON `null` (e.g.
  `contract_id: null`, `quantity_received: 0.00` when no receipt exists — read
  which the template wants).
- Match a row to its schema key (e.g. `evaluator matches by sku` /
  `by invoice_id`). Provide every required key for every row/object.

## 3. Core business rules (transferable)

### Three-way match (PO  <->  Receipt  <->  Invoice)
- ordered_qty = PO line quantity. received_qty = receipt line
  `quantity_received` for the receipt(s) tied to the invoice (0.00 if no
  receipt). billed_qty = invoice line `quantity_billed`.
- short_qty_vs_po = ordered - received. unreceived_billed_qty = billed -
  received. receipt_completion_ratio = received / ordered.
- quantity_variance = billed - received. quantity_variance_pct is a percent of
  **PO quantity** unless told otherwise.
- A line passes (release-eligible) only when: invoice status is approvable, a
  receipt exists, billed <= received, prices match contract/PO, and no open
  hold blocks it.

### AP invoice release / hold logic
- An invoice with `hold_code` set and/or status `on_hold` / `pending_receipt`
  is HELD unless a control resolves it (e.g. an APPROVED chargeback that nets
  the variance, or a confirming receipt the AP ledger had not yet seen).
- Reason / exception codes are driven by the cause:
  - billed > received but a receipt exists -> quantity-variance family.
  - no receipt on the PO -> NO_RECEIPT / no_receipt_on_po.
  - approved + matched + receipt present -> the "approved three-way match" code.
  - a scheduled payment exists -> the "scheduled payment found" code.
- **Exclusion rule (learned):** when an invoice has **no receipt at all**, the
  reason is the *no-receipt* code ONLY. Do NOT additionally emit a
  quantity-variance code merely because (billed - 0) is non-zero. Quantity
  variance is reserved for invoices that DO have a receipt with a mismatch.
- The AP ledger can be stale: an invoice may carry `hold_code: NO_RECEIPT`
  while a receipt actually exists in `/receipts`. Trust the receipt record; if a
  receipt is present and an approved chargeback covers the residual variance,
  the invoice is releasable net of the chargeback.

### Duplicate / multiple receipts on one PO
- A PO can have multiple receipts. The invoice (and any chargeback) references
  one specific receipt. Put that one in `receipt_ids_in_scope`; put the OTHER
  same-PO receipts in `excluded_same_po_receipt_ids`. A later same-PO receipt
  tied to a different/future invoice is excluded, not netted here.

### Chargebacks (when a local chargeback register is provided)
- The register is authoritative for chargeback existence, basis_quantity,
  unit_cost, and status. amount = basis_quantity * unit_cost (round to cents).
- status `approved` -> it nets the invoice now:
  net_release_amount = invoice_total - approved_chargeback_amount; decision =
  release-net-after-approved-chargeback.
- status `pending_quality_review` (or receipt on `inspection_hold`) -> HOLD;
  the amount goes to pending_chargeback_amount, net_release_amount = 0.00,
  decision = hold-pending-quality-chargeback.
- Totals: approved_chargeback_total / pending_chargeback_total / net_release_total
  are sums over the in-scope invoices.

### Sourcing nomination gates (readiness packets)
- Per line, pick selected_supplier_id from the PO/contract/preferred supplier.
- Blocker codes (emit the set, sorted ascending):
  - missing_contract: no active contract for that sku (PO `contract_id` null and
    no contract row for the sku).
  - supplier_watch: supplier `risk_rating == "watch"`.
  - open_supplier_risk: supplier has a vendor_risk_event with status `open`
    (or `monitoring`) as of the as-of date.
  - ap_hold: an invoice on the line is on hold.
  - pending_receipt: PO not fully received as of the as-of date
    (status partial_receipt/open, or received < ordered).
  - late_due_date: need_by / due_date already passed as of the as-of date.
- Decision mapping: a line with a valid contract + receipts but only soft
  issues (watch, AP hold to clear) -> conditional_nomination / at_risk;
  a line missing a contract or with no receipts -> hold / not_ready;
  a fully clean line -> nominate / ready.
- overall_readiness reflects the WORST line: if any line is not_ready/hold, the
  overall is `not_ready` (do not soften to `at_risk`).
- committee buckets: nominate_now / conditional / hold supplier-id lists follow
  the per-line decisions. `next_owner` is the role that clears the dominant
  remaining gap (sourcing/contract gaps -> `buyer`); `send_to_committee` is
  `no` while anything is held.

### Contract price consistency & headroom (change-control / amendments)
- contract_price_match = (invoice_unit_price == contract_unit_price ==
  PO_unit_price). If a contract exists for the sku, contract_unit_price is the
  contract's unit_price even when the PO/invoice agree.
- Contract usage / ceiling: noncancelled_subtotal = sum of line subtotals of
  POs on the contract whose status is NOT cancelled (exclude cancelled when the
  control says so). headroom_before = ceiling - noncancelled_subtotal.
  requested_subtotal = requested_qty * contract unit_price (ceiling exposure is
  subtotal BEFORE tax/freight). headroom_after = headroom_before -
  requested_subtotal. ceiling_ok = headroom_after >= 0.

### Budget / contract headroom (program budget)
- Use the program's `budget_snapshot` when one exists (snapshot_id, budget_cap,
  committed_amount). remaining_budget = budget_cap - committed_amount.
- Budget exposure of a request = requested_subtotal + tax (freight only if the
  memo provides freight). requested_tax = requested_subtotal * tax_rate.
  budget_after_change = remaining_budget - requested_total.
  budget_ok = budget_after_change >= 0.
- max_quantity_with_current_budget = floor(remaining_budget / per-unit exposure),
  where per-unit exposure = unit_price * (1 + tax_rate). Use FLOOR, not round.
- Note budget_headroom for a program is cap - committed; some tasks instead want
  cap minus a snapshot's pending-invoice figure — follow the field's wording and
  prefer the snapshot's own numbers when the snapshot is the named source.

### Approval state
- Find the requisition's approval_events (filter by `object_id`). Take the
  LATEST by event_date for latest_event_id/action/actor/date.
- approval_ok = latest action is in the memo's "approved" action list. A
  `submitted` (or any non-approved) latest action -> approval_ok = false.

### Supplier-risk policy
- open_event_ids = vendor_risk_events with status `open` (and `monitoring` when
  the task counts it) for the supplier; exclude `closed`. Sort ascending.
- severe_open_event_ids = the subset with severity high/critical (severe). A
  `medium` open event is NOT severe.
- supplier_risk_ok: a `watch`/`medium` posture is context-only and stays OK
  UNLESS there is an open SEVERE event. Only an open severe event flips it false.

## 4. Decision enums: combine multiple blockers
When the enum set offers combined values (e.g. `hold_for_budget_and_approval`),
and more than one gate fails, you MUST pick the COMBINED enum, not a single
reason. Count blockers (budget_ok false, approval_ok false, supplier_risk_ok
false, ceiling/price fails) and map to the matching combined enum; set
blocker_count and ready_to_release accordingly. Required-actions lists should
include one action per failed gate (sorted ascending); use the "none" sentinel
only when there are zero blockers.

## 5. Evidence / source-attribution fields
- "endpoint_record_ids" = the API record IDs you actually relied on (receipt,
  PO, invoice, supplier, contract, the open risk event, the budget snapshot,
  the program/requisition). List the load-bearing ones; treat as a set.
- "task_payloads_reviewed" = the payload file(s) you read (the memo). Do not pad.
- authoritative_sources vs supporting_only_sources: API record families and the
  local chargeback register are AUTHORITATIVE; request notes and stale-alias
  notes are SUPPORTING-ONLY. Use the template's exact enum spellings.
- followup_actions: one per unresolved condition (missing receipt to chase,
  duplicate receipt to hold for a separate invoice, quality review to route,
  approved-chargeback netting to post). Use the template's exact spellings.

## 6. Common misjudgments (general rules)
- As-of filtering: exclude receipts/invoices/risk events dated AFTER the as-of
  date when the field says "as of as_of_date". A later receipt on the same PO is
  out of scope for an as-of snapshot.
- Do not invent extra reason/exception codes. Emit only what the cause supports;
  a redundant or spurious code makes an otherwise-correct list field wrong, so
  keep code sets minimal and data-grounded.
- Do not downgrade a combined-blocker decision to a single-blocker enum; when
  multiple gates fail, the single-reason enum is wrong.
- overall/aggregate readiness follows the worst line, not an average.
- Recompute every money figure from primitives (qty * unit_price, subtotal +
  tax) and round at the end; do not copy a total blindly if the template defines
  it as a derived value.
- When you have one row per receipt, also add a row for a PO that is missing its
  receipt if the schema's resolution_status enum includes a "missing_receipt"
  state and a followup asks to chase that receipt.
- If a field's exact membership is genuinely ambiguous (e.g. which detailed
  exception codes apply), pick the codes the data DIRECTLY supports
  (received<ordered -> underage; status inspection_hold -> inspection hold;
  billed>received with a receipt -> AP quantity variance) and keep the set
  minimal and data-grounded.

## 7. Per-task SOP (repeat for each task)
1. Parse template -> list every required key, its type, rounding, sort/set rule,
   and allowed enum values.
2. Resolve anchors from the memo, then pull each anchor and its related records
   from the API (PO -> receipts + invoices + contract + supplier + program +
   requisition; supplier -> risk events; program -> budget snapshot;
   requisition -> approval_events via object_id).
3. Apply as-of filtering and the memo's explicit controls.
4. Compute three-way-match numbers, holds, chargebacks, headroom, approvals,
   and risk per the rules above.
5. Map results to the template's enums; combine multiple blockers; build the
   set/sorted lists; round money to cents.
6. Emit ONLY the JSON object; validate it has every required key and that every
   enum value is copied verbatim from the template.
