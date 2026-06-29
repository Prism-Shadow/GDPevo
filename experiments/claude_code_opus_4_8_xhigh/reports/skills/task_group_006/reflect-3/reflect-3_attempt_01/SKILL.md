---
name: reflect-3_attempt_01
description: SOP for ProcureOps ERP procurement/receiving/AP tasks — pull records from the read-only API as source of truth, apply sourcing/receiving/three-way-match/AP-release rules, and emit answer.json that exactly matches the task template.
---

# ProcureOps Procurement / Receiving / AP Solver Skill

You answer ERP "decision packet" tasks in the ProcureOps domain (sourcing
nomination, receiving closeout, AP close/hold-release, change-control, chargeback
netting). Each task gives you `input/prompt.txt`, local payload files (memos,
registers, watch sets), and an `answer_template.json`. Your job: gather the
authoritative records, apply the business rules, and return ONE JSON object that
matches the template exactly.

---

## 1. The remote API is the source of truth

Base URL (ignore any `localhost`/`127.0.0.1:8006` in the prompt — use this):

    <remote-env-url>

GET-only. Collections: `programs`, `suppliers`, `items`, `contracts`,
`purchase_requisitions`, `purchase_orders`, `receipts`, `ap_invoices`,
`payments`, `approval_events`, `budget_snapshots`, `vendor_risk_events`.

Patterns:
- `GET /<collection>` -> `{"count": N, "results": [...]}`
- `GET /<collection>/<id>` -> single object (404 if missing)
- Filter by any record field (case-insensitive), e.g.
  `GET /receipts?po_id=PO-AX17-4481`, `GET /ap_invoices?po_id=...`,
  `GET /payments?invoice_id=...`, `GET /vendor_risk_events?supplier_id=...`,
  `GET /purchase_orders?contract_id=...`, `GET /contracts?sku=...`.
- `start`/`end` filter the collection's primary date field.

Rules of engagement:
- Local payload files name the *scope* (target IDs, watch set, business request,
  chargeback register, tax rate). The API gives the *values*. When they
  disagree, trust the API for record values; trust the local register for things
  that ONLY exist locally (e.g., chargeback approvals, tax rate, opening balances).
- A filtered query often returns MORE than the one record you expect (e.g. a PO
  can have several receipts and several invoices, some old/paid/cancelled).
  Always fetch the full set and then apply the task's date/scope filters
  yourself. Do not assume one-to-one.
- Verify each target ID actually resolves; if a referenced ID is absent, treat it
  as "missing receipt / no record" (that is itself a decision input), and use the
  fallback IDs the payload provides.

### Record shapes (key fields)
- program: `budget_cap`, `committed_amount`, `owner`, `status`, `priority`.
- supplier: `risk_rating` (low|medium|watch|...), `status`, `name`, `payment_terms`.
- contract: `status`, `price_type`, `unit_price`, `ceiling_amount`, `sku`,
  `supplier_id`, `program_id`, `effective/expiry_date`.
- purchase_order: `status` (open|confirmed|partial_receipt|received|closed|
  cancelled), `lines[]` (line_id, sku, quantity, unit_price), `subtotal`, `tax`,
  `total`, `contract_id` (may be null), `requisition_id`.
- receipt: `status` (accepted|accepted_with_note|inspection_hold|...),
  `lines[]` (po_line_id, sku, quantity_received, quantity_rejected,
  inspection_status), `receipt_date`, `packing_slip`, `receiver`, `warehouse_id`.
- ap_invoice: `status` (approved|on_hold|pending_receipt|paid|...), `hold_code`
  (QTY_VARIANCE|PRICE_VARIANCE|NO_RECEIPT|null), `lines[]`
  (po_line_id, sku, quantity_billed, unit_price), `subtotal`, `freight`, `tax`,
  `total`, `receipt_id` (may be null).
- payment: `invoice_id`, `amount`, `scheduled_date`, `status` (scheduled|...).
- approval_event: `object_id`, `object_type`, `action` (submitted|approved|...),
  `actor`, `event_date`, `event_id`, `note_code`.
- budget_snapshot: `snapshot_id`, `budget_cap`, `committed_amount`,
  `pending_invoice_amount`, `snapshot_date`.
- vendor_risk_event: `supplier_id`, `severity` (low|medium|high|critical),
  `status` (open|monitoring|closed), `event_type`, `related_object_id`,
  `event_date`, `event_id`.

---

## 2. Output conventions (these decide most of your score)

1. **Match the template structure EXACTLY.** Emit every required key, with the
   exact key names, nesting, and enum spelling shown in the template. Return ONLY
   the JSON object — no prose.
2. **Copy literal record values verbatim.** Fields like `invoice_status`,
   `hold_code`, `receipt_status`, `po_status`, `contract_status`, `price_type`,
   `supplier_risk_rating`, `*_action`/`*_actor` must be the EXACT string from the
   API record. Do NOT derive or "clean up" a status (e.g. do not turn a receipt's
   literal `accepted` into `partial`; that loses points). If the template asks for
   a status that is literally a record field, echo the record field.
3. **Enums are closed sets — copy them character-for-character** from the
   template's allowed list. Never invent a value or change case/underscores.
4. **USD amounts rounded to cents (2 decimals).** Ratios/percentages to the
   precision the template states (e.g. completion ratio to 4, variance_pct to 1).
   Compute on raw numbers, round only the final field.
5. **List fields are SETS unless the template states a sort rule.** When a sort is
   stated ("sorted ascending", "by po_line_id ascending", "invoice_id ascending"),
   sort exactly that way. When it says "set; evaluator sorts", order doesn't
   matter but membership does — include every required element and nothing extra.
6. **Null vs empty:** use `null` when a value is genuinely absent (e.g. no
   contract → `commercial_basis_id: null`; no hold → `hold_code: null`), and `[]`
   for an empty list. Use `0.00` for a money/qty field that the template says
   defaults to zero (e.g. quantity_received when no receipt exists).
7. **as_of / review_as_of date filtering:** include only records dated on or
   before the as-of date. A later-dated receipt/invoice is OUT of scope even if it
   exists. Apply this before building any evidence/exception list.

---

## 3. Business rules (transferable)

### 3a. Three-way match (PO ↔ receipt ↔ invoice)
- Match on po_id + po_line_id + sku. Compare `quantity` (PO ordered),
  `quantity_received` (receipt), `quantity_billed` (invoice), and unit prices
  (PO vs contract vs invoice).
- `short_qty_vs_po = ordered - received`. `unreceived_billed = max(billed - received, 0)`.
- `receipt_completion_ratio = received / ordered`.
- A clean three-way match = billed == received == ordered AND prices match AND a
  receipt exists AND invoice not on hold → release / APPROVED_THREE_WAY_MATCH.

### 3b. Quantity / variance reconciliation
- `quantity_variance = billed - received`. `quantity_variance_pct = variance / PO_qty`.
- If NO receipt exists, `received = 0` and the variance equals the billed qty, but
  the controlling exception is **NO_RECEIPT**, NOT a quantity-variance code.
  Do NOT also stack a QTY_VARIANCE reason on a no-receipt invoice — the missing
  receipt supersedes it. (Conversely, a receipted-but-short invoice IS a qty
  variance.)

### 3c. AP invoice release / hold logic
- RELEASE only when: invoice status is approved (or otherwise clear), a valid
  receipt exists, quantities reconcile (within approved chargeback), and prices
  match. A scheduled payment found in `/payments` is a supporting RELEASE signal.
- HOLD when any of: `status` is on_hold / pending_receipt; `hold_code` is set;
  no receipt; unresolved quantity or price variance; receipt in inspection_hold;
  only a *pending* (not approved) chargeback exists.
- Reason/exception codes for an invoice = the union of the conditions that are
  actually true for it, chosen from the template's allowed set, then sorted/setted
  per the template. Add a code only when its condition holds.

### 3d. Duplicate-invoice / duplicate-receipt handling
- One PO can carry multiple receipts and multiple invoices. Tie an invoice to its
  own `receipt_id`. Other same-PO receipts that the invoice does not reference are
  **excluded from this invoice's scope** — list them in any
  `excluded_same_po_receipt_ids`-style field and flag a follow-up to hold the
  duplicate for its own/separate invoice. Do not net one invoice against another
  invoice's receipt.

### 3e. Contract price consistency
- `contract_price_match` = invoice unit_price == contract unit_price (for the SKU
  on an active contract). PO price should also equal contract price; a mismatch is
  a PRICE_VARIANCE/PRICE_MISMATCH exception. A SKU with no contract record →
  `contract_unit_price` absent and `commercial_basis_id: null`, blocker
  `missing_contract`.

### 3f. Contract & budget headroom (change-control / new buys)
- Program/budget headroom = `budget_cap - committed_amount` (from the program or
  the matching `budget_snapshot`; prefer the snapshot the task names).
- Contract ceiling usage = sum of `subtotal` of NON-cancelled POs on that contract
  (EXCLUDE `status == cancelled`). `headroom_before = ceiling - noncancelled_subtotal`.
- Requested exposure: **contract/ceiling exposure = line subtotal (qty × unit_price,
  before tax & freight)**; **budget exposure = subtotal + tax** (add freight only if
  the memo supplies freight). Use the memo's tax rate.
- `headroom_after = headroom_before - requested_subtotal`; `ceiling_ok = headroom_after >= 0`.
- `budget_after = remaining_budget - requested_total`; `budget_ok = budget_after >= 0`.
- `max_quantity_with_current_budget = floor(remaining_budget / per_unit_total)`
  where per_unit_total = unit_price × (1 + tax_rate).
- Decision = combine the failing gates: budget-fail + approval-fail →
  `hold_for_budget_and_approval`; single failures map to the single-gate hold enum;
  contract SKU/price mismatch → `reject_contract_mismatch`; all gates pass →
  `release_amendment`. `blocker_count` = number of failing gates;
  `ready_to_release` = (blocker_count == 0).

### 3g. Approval gates (sourcing nomination & change-control)
- Find the latest approval_event for the source requisition
  (`/approval_events?object_id=<REQ>`), by `event_date`.
- `approval_ok` is TRUE only if the latest action is in the memo's
  "good actions" (typically just `approved`). A requisition whose latest action is
  `submitted` is NOT approved → `approval_ok=false`, action
  `obtain_final_requisition_approval`. (Requisition `status: converted` or
  `approved` on the requisition record is not the same as an approval *event* —
  follow whatever the task keys off.)

### 3h. Supplier-risk policy
- `supplier_risk_rating` = supplier.risk_rating verbatim. A rating of `watch` is a
  soft signal/blocker (`supplier_watch`), NOT an automatic hard hold — it's
  "context only" unless an OPEN SEVERE event exists.
- "Open" risk events = `status` in {open, monitoring}; exclude `closed`.
  Filter by `supplier_id` and by as-of date.
- "Severe" = severity high or critical. `supplier_risk_ok` is FALSE only when a
  severe OPEN event exists; medium/low open events are context (still listed in
  `open_event_ids`, but not in `severe_open_event_ids`, and don't fail the gate).

### 3i. Sourcing nomination gates & readiness
- Per line, collect: selected supplier, primary requisition, commercial basis
  (active contract id or null), package PO ids, receipt evidence (≤ as-of),
  invoice exceptions (on-hold/exception invoices ≤ as-of), open/monitoring risk
  events (≤ as-of), and blocker codes.
- Blocker codes (sorted ascending, from the allowed set): `missing_contract`,
  `supplier_watch`, `open_supplier_risk`, `ap_hold`, `pending_receipt`,
  `late_due_date`; `none` only when there are zero blockers.
- Readiness/decision mapping that scored best:
  - A line with a valid contract whose only blockers are *clearable/soft*
    (supplier_watch, an open non-severe risk event, an AP hold pending variance
    clearance) → `at_risk` + `conditional_nomination`.
  - A line with a *hard* blocker (missing_contract, pending_receipt / no receipt,
    no commercial basis) → `not_ready` + `hold`.
  - A clean line → `ready` + `nominate`.
- Roll-up: `overall_readiness` is the WORST line state — if ANY line is
  `not_ready`/`hold`, the program is `not_ready` and `send_to_committee = "no"`.
  Do NOT upgrade the program to `at_risk` or set committee="yes" just because one
  line is conditional while another is held. Committee buckets
  (nominate_now/conditional/hold supplier ids) follow each line's decision.

### 3j. Chargeback netting (receiving/AP release file)
- Approved chargeback → net it off the invoice:
  `net_release_amount = invoice_total - approved_chargeback_amount`, decision
  `release_net_after_approved_chargeback`. Chargeback amount =
  `basis_quantity × unit_cost` from the register.
- Pending (e.g. `pending_quality_review`) chargeback or a receipt in
  `inspection_hold` → HOLD (`hold_pending_quality_chargeback` /
  `inspection_hold_pending_chargeback`); net release 0; the amount goes to
  `pending_chargeback_amount`, not approved.
- No receipt on the PO → `hold_missing_receipt` / `no_receipt_on_po`; net 0.
- `primary_reason` should reflect the chargeback's `reason_code`
  (e.g. "Underage Quantity" → approved_qty_chargeback; "AP Quantity Variance" →
  approved_ap_quantity_variance).
- Receiving-exception codes per receipt come from the register reason_code plus
  the receipt status (e.g. inspection_hold → "Inspection Hold").
- Totals: `approved_chargeback_total`/`pending_chargeback_total` = sums of the
  respective amounts; `net_release_total` = sum of net amounts of RELEASED
  invoices only. Release/hold invoice-id lists follow each decision.
- Sources: API record families are authoritative
  (procureops_po_records, procureops_receipt_records, procureops_ap_records) plus
  the local chargeback register; request notes and stale-alias notes are
  supporting-only.

### 3k. Vendor balance / AP close
- Per supplier: `close_balance = opening_balance + invoice_total - scheduled_payments`
  (use the opening balance the memo states, often 0.00). A payment scheduled
  through the close window reduces the balance.
- `balance_status`: `FULLY_SCHEDULED` when scheduled covers the invoices and none
  held; `OPEN_HELD` when any invoice is on hold; else `OPEN_APPROVED`.
- Program summary aggregates invoice_total / held_total / released_total /
  net_close_balance per program. Hold/release queues = invoice ids by decision,
  sorted ascending. `total_close_balance` = sum of supplier close balances.

---

## 4. Step-by-step SOP for a new task

1. Read `prompt.txt` and every payload file. Extract: target IDs / watch set,
   the as-of date, tax rate, opening balances, chargeback register, and any
   business-control notes (what to exclude, what counts as a "good" approval).
2. Open `answer_template.json` and list every required key, its type, enum sets,
   rounding precision, and sort/set rules. This is your output contract.
3. Pull the authoritative records from the API for each target ID, then fan out:
   for each PO get its receipts (`?po_id=`) and invoices (`?po_id=`); for each
   invoice get payments (`?invoice_id=`); for the supplier get risk events
   (`?supplier_id=`); for the contract get POs (`?contract_id=`); plus
   program/budget/approval records as needed.
4. Apply the as-of/scope filter and the relevant rules from section 3.
5. Compute money fields on raw numbers; round only at the end. Sort/ set lists
   per the template.
6. Assemble the JSON. Echo literal record statuses verbatim; copy enums exactly;
   use null/[]/0.00 per section 2.6.
7. Self-check before finalizing:
   - Every required key present, no extras, correct nesting.
   - Enums spelled exactly as allowed; no invented values.
   - Lists sorted where required; sets complete and minimal.
   - Money to cents; ratios/percentages to stated precision.
   - Roll-ups reconcile (queues vs decisions, totals vs line sums, worst-case
     readiness, blocker_count vs failing gates).
   - No-receipt invoices use NO_RECEIPT (not a stacked qty-variance code).
   - Literal statuses copied, not derived.

---

## 5. Common misjudgments to avoid

- Deriving/renaming a literal status field instead of echoing the API value.
- Stacking a quantity-variance reason on a no-receipt invoice (use NO_RECEIPT only).
- Treating `supplier_watch` (or a medium/low open risk event) as a hard hold — it
  is conditional context, not an automatic block; only a severe OPEN event fails
  the supplier-risk gate.
- Upgrading program-level readiness / committee routing because one line is
  conditional while another is held — the worst line governs the roll-up
  (any hold ⇒ not_ready, send_to_committee=no).
- Including cancelled POs in contract-usage / ceiling math (always exclude them).
- Confusing budget exposure (subtotal + tax) with contract/ceiling exposure
  (subtotal only, before tax/freight).
- Counting a requisition record's `status` as an approval; follow the latest
  approval *event* action against the memo's allowed "good" actions.
- Including records dated after the as-of date in evidence/exception lists.
- Netting an invoice against another invoice's receipt, or against a PENDING
  (not approved) chargeback.
- Missing the duplicate same-PO receipt that belongs to a separate invoice.
- Adding extra IDs to a "set" list (membership must be exact) or forgetting to
  sort a list that specifies ordering.
