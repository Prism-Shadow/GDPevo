# ProcureOps Rules, Formulas, and Join Reference

Table of contents
1. API and endpoints cheatsheet
2. Join gotchas (the joins that bite)
3. Source-of-truth precedence
4. Date/status scoping rules
5. Money, rounding, and list-ordering conventions
6. Verified derivation formulas
7. Decision / blocker / reason enum logic
8. Catalogued blind-pass mistakes (root cause -> corrected rule)
9. Per-task-archetype SOP checklists

---

## 1. API and endpoints cheatsheet

Base URL `http://127.0.0.1:8056` (identical mirror at `:8006`). All read-only HTTP GET.
Responses for list endpoints are `{"count": n, "results": [...]}`. Single-record fetches
return the bare object.

| Collection | List / filter | By id | Primary date field (for start=/end=) |
|---|---|---|---|
| programs | `/programs` | `/programs/<program_id>` | - |
| suppliers | `/suppliers` | `/suppliers/<supplier_id>` | - |
| items | `/items` | `/items/<sku>` | - |
| contracts | `/contracts` | `/contracts/<contract_id>` | - |
| purchase_requisitions | `/purchase_requisitions` | `/purchase_requisitions/<id>` | - |
| purchase_orders | `/purchase_orders` | `/purchase_orders/<po_id>` | order_date |
| receipts | `/receipts` | `/receipts/<receipt_id>` | receipt_date |
| ap/invoices | `/ap/invoices` | `/ap/invoices/<invoice_id>` | invoice_date |
| ap/payments | `/ap/payments` | `/ap/payments/<payment_id>` | scheduled_date |
| approval_events | `/approval_events` | `/approval_events/<event_id>` | event_date |
| budget_snapshots | `/budget_snapshots` | `/budget_snapshots/<snapshot_id>` | snapshot_date |
| vendor_risk_events | `/vendor_risk_events` | `/vendor_risk_events/<event_id>` | event_date |

Filtering:
- `?field=value` is an **exact**, case-insensitive match, and it also matches values nested
  inside list fields of a record (e.g. filtering on a sku that appears in a line array).
- Common, reliable filters: `?program_id=`, `?supplier_id=`, `?po_id=`, `?contract_id=`,
  `?status=`. Combine with `&`.
- `?start=YYYY-MM-DD&end=YYYY-MM-DD` filters on the collection's primary date field only.
- `/manifest` gives record counts, anchor ids, and the seed if you need a sanity check.

Useful query patterns:
- All invoices on a PO: `/ap/invoices?po_id=PO-AX17-4481` (often returns >1).
- All receipts on a PO: `/receipts?po_id=PO-AX17-4481` (often returns >1).
- Open risk for a supplier: `/vendor_risk_events?supplier_id=SUP-LUMA` then filter
  `status in {open, monitoring}` and `event_date <= as_of`.
- Budget for a program: `/budget_snapshots?program_id=PRG-AX17` (use the snapshot whose
  date matches the as-of, or the only one).
- Payments funding an invoice: `/ap/payments?supplier_id=...` then match by `invoice_id`.

---

## 2. Join gotchas (the joins that bite)

- **One PO -> many invoices.** A single PO commonly has multiple AP invoices (e.g. an
  older PRICE_VARIANCE invoice plus a current QTY_VARIANCE invoice). Pull them all with
  `/ap/invoices?po_id=...` and decide membership by status/date, not by taking the first.
- **One PO -> many receipts.** A PO can have two receipts (e.g. an accepted batch and a
  later `accepted_with_note` batch). The invoice carries a `receipt_id` pointing at the one
  it bills; the *other* receipt on the same PO is "same-PO" and is typically excluded from
  that invoice's scope (and may need a follow-up). Always reconcile receipt-to-invoice via
  the invoice's `receipt_id`, then treat siblings as excluded.
- **Invoice line vs PO line vs receipt line.** Quantities live on line objects:
  `invoice.lines[].quantity_billed`, `po.lines[].quantity`, `receipt.lines[].quantity_received`
  (and `quantity_rejected`). Match by `po_line_id`/`sku`.
- **`receipt_id: null` means no receipt** -> `quantity_received = 0`. This is the NO_RECEIPT
  case, distinct from a partial receipt.
- **Requisition <-> PO** join is via `po.requisition_id`; the requisition holds `need_by`,
  `priority`, `quantity`, `status` (converted/approved/etc.).
- **Approval events** attach to a requisition; the "latest" event is the one with the max
  `event_date` for that requisition. The action enum (submitted/approved/...) on the latest
  event drives `approval_ok`.

---

## 3. Source-of-truth precedence

The API is the **system of record** for every operational fact: price, status, quantity,
date, rating, ceiling, budget. The local payload (memo/packet/change request) is
authoritative only for:
- **Scope** — which program/PO/receipt/invoice/contract IDs are under review.
- **Business controls it explicitly states** — tax rate, "exclude cancelled POs",
  ceiling-exposure = subtotal-before-tax, opening balance = 0.00, payment cutoff date.
- **Local-only registers the task tells you to use** — e.g. a chargeback register excerpt
  that exists only in the packet. Treat these as authoritative for chargeback amounts/status.

When a payload narrative conflicts with an API fact (e.g. "AP ledger shows approved" but the
receipt is on inspection hold; or a "stale" alias note), the **controlled API/record state
wins** and the narrative becomes `supporting_only` evidence. Tag sources accordingly when the
template asks for `authoritative_sources` vs `supporting_only_sources`.

---

## 4. Date/status scoping rules

- **`as_of_date` / review date is an inclusive upper bound.** A child record counts only if
  its primary date is `<= as_of`. Receipts dated *after* the as-of date are **not yet
  evidence** and are excluded from receipt-evidence lists. Invoices dated after are excluded
  from exception lists.
- **Payment cutoff (`through <date>`)** for AP close: a scheduled payment reduces the close
  balance only if `scheduled_date <= cutoff` (and it matches the invoice). Payments scheduled
  after the cutoff are ignored for that slice.
- **Open / monitoring only:** risk events, holds, etc. that are `closed` are excluded from
  "open" lists. "Open or monitoring as of as_of" = `status in {open, monitoring}` AND
  `event_date <= as_of`.
- **Cancelled exclusion:** cancelled POs are excluded from contract usage / noncancelled
  subtotal and from "included" PO lists; track them separately in
  `excluded_cancelled_po_ids` when asked.

---

## 5. Money, rounding, and list-ordering conventions

- **Money -> cents (2 dp)** unless a field says otherwise. Compute in full precision, round
  only the emitted value.
- **Ratios/percentages** use the template's stated precision: completion ratio often 4 dp,
  `quantity_variance_pct` 1 dp. Read each field's precision note.
- **List ordering — honor the template literally:**
  - "sorted ascending" / "sort IDs ascending" -> sort the list ascending.
  - "set; evaluator sorts values" -> ordering doesn't matter (still fine to sort).
  - "sort by <key> ascending" (e.g. `po_line_id`) -> sort by that key.
  - No instruction -> default to **set, sorted ascending** (safe; evaluator usually sorts).
- **Hard-coded constants:** fill `task_id`, `*_id`, `currency` exactly as the template's
  `required_value` / fixed string dictates.
- **Emit only the JSON object** — no surrounding prose, no markdown fences in the answer.

---

## 6. Verified derivation formulas

All of the following were confirmed correct against standard answers.

### Budget
- `remaining_budget = budget_cap - committed_amount`. (From the program record or its budget
  snapshot. Do **not** subtract `pending_invoice_amount` — that field is a red herring.)
- `budget_headroom_usd` = same as remaining_budget.
- `requested_tax = requested_subtotal * tax_rate` (tax_rate from the payload, e.g. 0.0725).
- `requested_total = requested_subtotal + requested_tax` (+ freight only if the memo
  provides freight).
- `budget_after_change = remaining_budget - requested_total`.
- `budget_ok = budget_after_change >= 0`.
- `max_quantity_with_current_budget = floor(remaining_budget / (unit_price * (1 + tax_rate)))`.
  The per-unit divisor is **tax-loaded**, then floored to an integer.

### Contract / ceiling
- `noncancelled_subtotal = sum(po.subtotal for POs on the contract if status != cancelled)`.
  Identify POs on the contract via `?contract_id=` (and/or the contract's program/sku scope).
- `headroom_before_change = ceiling_amount - noncancelled_subtotal`.
- `requested_subtotal = requested_quantity * contract.unit_price` (for fixed-price contracts).
- `headroom_after_change = headroom_before_change - requested_subtotal`.
- `ceiling_ok = headroom_after_change >= 0`.
- `included_po_ids` = noncancelled POs (sorted asc); `excluded_cancelled_po_ids` = cancelled
  ones (sorted asc).

### Qty / price reconciliation (receiving)
- `ordered_qty = po.lines[].quantity`; `received_qty = receipt.lines[].quantity_received`
  (0 if no receipt); `rejected_qty = receipt.lines[].quantity_rejected`;
  `billed_qty = invoice.lines[].quantity_billed`.
- `short_qty_vs_po = ordered_qty - received_qty`.
- `unreceived_billed_qty = billed_qty - received_qty`.
- `receipt_completion_ratio = received_qty / ordered_qty` (precision per template).
- `received_goods_value = received_qty * unit_price`.
- `unreceived_goods_value = unreceived_billed_qty * unit_price`.
- `contract_price_match = (po_unit_price == contract_unit_price == invoice_unit_price)`.

### Variance (AP close)
- `quantity_received = receipt qty, or 0.00 if no receipt`.
- `quantity_variance = quantity_billed - quantity_received`.
- `quantity_variance_pct = quantity_variance / PO_quantity * 100` (1 dp). Denominator is
  **PO quantity**, not billed quantity.

### Vendor balance / close
- `opening_balance` per the memo (often 0.00 for the slice).
- `invoice_total` = sum of in-scope invoice totals for that supplier.
- `scheduled_payments` = sum of payments matched by `invoice_id` with `scheduled_date <= cutoff`.
- `held_invoice_total` = sum of totals for invoices decided HOLD; `releasable_invoice_total`
  = sum for invoices decided RELEASE.
- `close_balance = opening_balance + invoice_total - scheduled_payments`.
- `total_close_balance = sum of all vendor close_balance` (== sum of net balance impacts).
- Program rollups: `held_total`, `released_total`, `net_close_balance` summed over the
  program's in-scope invoices.

### Chargeback netting (AP release)
- `chargeback_amount = basis_quantity * unit_cost` (from the local register).
- Only **approved** chargebacks net the invoice:
  `net_release_amount = invoice_total - approved_chargeback_amount`.
- A **pending_quality_review** chargeback (or an inspection-hold receipt) holds the invoice:
  `net_release_amount = 0`, chargeback counted in `pending_chargeback_total`.
- `approved_chargeback_total` / `pending_chargeback_total` = sums across the slice.
- `net_release_total` = sum of `net_release_amount` for invoices decided to release.

---

## 7. Decision / blocker / reason enum logic

Always pick from the template's `allowed_values`. Key mappings:

### Sourcing nomination (blocker_codes; per line)
A line accumulates blockers; emit the set, sorted ascending. Triggers:
- `missing_contract` — line/PO has no contract (`contract_id == null`) and no active
  commercial basis for the sku.
- `supplier_watch` — supplier `risk_rating == watch`. (A `low` supplier gets none.)
- `open_supplier_risk` — supplier has an open/monitoring risk event as of as_of.
- `ap_hold` — an in-scope invoice has **status == on_hold**. (NOT just a hold_code.)
- `pending_receipt` — the line/PO has **no receipt at all** (zero receipts). A partial
  receipt does NOT trigger this.
- `late_due_date` — `po.due_date > requisition.need_by`.
- `none` — no blockers.

Line decision/readiness (typical mapping):
- `nominate` / `ready` — contract present, no blockers.
- `conditional_nomination` / `at_risk` — has contract + some evidence but holds/risk present.
- `hold` / `not_ready` — missing contract or no receipt or hard blockers.

Program `overall_readiness` = worst line readiness (any `not_ready` line => program not_ready).

`committee_action`:
- buckets suppliers by their line decision (nominate_now / conditional / hold), sorted asc.
- `send_to_committee = yes` only if a line is fully ready/nominate; else `no`.
- `next_owner` precedence (route to owner of the highest-precedence open blocker):
  `ap_hold -> ap_team`, then AP/finance issues -> `finance_ops`, quality/inspection ->
  `quality_ops`, contract/buyer issues -> `buyer`, otherwise `program_owner`. An open AP hold
  outranks "mixed issues -> program_owner".

### Receiving closeout (exception_codes)
- `INVOICE_QTY_EXCEEDS_RECEIPT` — billed > received.
- `PARTIAL_RECEIPT` — received < ordered.
- `SUPPLIER_WATCH_RISK` — supplier rating watch.
- `PRICE_MISMATCH` — prices disagree.
- `DAMAGE_REJECTION` — rejected qty > 0.
- `NO_EXCEPTION` — none of the above.
`receipt_status` = the receipt's own `status` value (e.g. `accepted`), not a recomputed label.

### AP close (reason_codes; alphabetical)
- `APPROVED_THREE_WAY_MATCH` — status approved, qtys match.
- `SCHEDULED_PAYMENT_FOUND` — a matching payment within the cutoff exists.
- `QTY_VARIANCE` — billed != received **and a receipt exists**.
- `NO_RECEIPT` — no receipt exists. **When NO_RECEIPT applies, do NOT also add
  QTY_VARIANCE**, even though billed > received(=0).
- `hold_decision`: HOLD when status on_hold/pending_receipt or unresolved variance; RELEASE
  when approved/clean.
- `balance_status`: `FULLY_SCHEDULED` when scheduled >= invoice_total (close_balance 0);
  `OPEN_HELD` when held; `OPEN_APPROVED` when approved but unpaid.

### Change control (decision / required_actions)
- `decision` combines the failing checks: `hold_for_budget`, `hold_for_approval`,
  `hold_for_budget_and_approval`, `hold_for_supplier_risk`, `release_amendment`,
  `reject_contract_mismatch`.
- `approval_ok = (latest approval action == "approved")`. "submitted" is NOT ok.
- `supplier_risk_ok = true` for watch with no open severe (high/critical) event.
- `required_actions` map 1:1 to failing checks (sorted asc); `none` if all pass.
- `blocker_count = number of failed checks`; `ready_to_release = (blocker_count == 0)`.

### AP release (decision / primary_reason / receiving exception codes)
- `release_net_after_approved_chargeback` + `approved_qty_chargeback` /
  `approved_ap_quantity_variance` — receipt exists, chargeback approved -> net release.
- `hold_pending_quality_chargeback` + `inspection_hold_pending_chargeback` — receipt on
  inspection_hold / chargeback pending_quality_review -> hold, net 0.
- `hold_missing_receipt` + `no_receipt_on_po` — PO has no receipt -> hold, net 0, AND emit a
  `MISSING:<po_id>` receiving-exception row.
- Receiving `exception_codes`:
  - `Underage Quantity` — received < ordered (underage chargeback reason).
  - `Severe Unmatched Quantity` — **add on top of Underage when the shortfall is large**
    (double-digit basis qty / ~>=10% of order). Small AP-only over-bills do not get it.
  - `Inspection Hold` — receipt status inspection_hold.
  - `AP Quantity Variance` — billed-vs-received over-bill (AP-quantity chargeback reason),
    used alone for small over-bills with a complete receipt.
- `resolution_status`: `net_release_ready` (approved), `hold_for_quality_review` (pending),
  `missing_receipt` (no receipt), `accepted_no_receiving_exception`.

---

## 8. Catalogued blind-pass mistakes (root cause -> corrected rule)

| # | Field / context | Blind error | Root cause | Corrected rule |
|---|---|---|---|---|
| 1 | nomination `blocker_codes` (no-receipt invoice) | added `ap_hold` | confused hold_code with status | `ap_hold` only when invoice **status == on_hold**; a `pending_receipt`/`NO_RECEIPT` invoice drives `pending_receipt`, not `ap_hold` |
| 2 | nomination `blocker_codes` (partial receipt) | added `pending_receipt` to a partially-received line | over-broad rule "not fully received" | `pending_receipt` = **zero receipts**; partial receipt does not trigger it |
| 3 | nomination `blocker_codes` | missed `late_due_date` | compared due_date to as_of instead of need_by | `late_due_date` = `po.due_date > requisition.need_by` |
| 4 | AP-close `reason_codes` (no receipt) | added `QTY_VARIANCE` alongside `NO_RECEIPT` | treated billed>received(0) as a qty variance | with no receipt the only code is `NO_RECEIPT` |
| 5 | nomination `next_owner` | chose `program_owner` | no routing precedence; defaulted to "mixed" | open AP hold routes to `ap_team`; route by highest-precedence open blocker |
| 6 | receiving `endpoint_record_ids` | omitted the item SKU | forgot the item is a first-class record | include `/items/<sku>` id in evidence when relied upon |
| 7 | receiving `task_payloads_reviewed` | bare filename + included answer_template | wrong path style; treated template as a source | use the referenced path style (`input/payloads/<file>`); exclude `answer_template.json` |
| 8 | AP-release receiving `exception_codes` | dropped `Severe Unmatched Quantity` on large shortfalls | only mapped one code per receipt | add `Severe Unmatched Quantity` on top of `Underage Quantity` for large shortfalls |
| 9 | AP-release `receiving_exceptions` | no row for the missing-receipt PO | treated absence as nothing to report | emit a `MISSING:<po_id>` row with empty codes / `not_applicable` / `missing_receipt` |
| 10 | AP-release `followup_actions` | omitted the duplicate-receipt follow-up | excluded the sibling receipt but forgot the action | a second same-PO receipt -> exclusion **and** a "hold duplicate for separate invoice" follow-up |

Verified-correct defaults that should be reused: budget remaining = cap - committed;
max_qty uses tax-loaded floor; noncancelled subtotal excludes cancelled POs; watch +
no-severe-open => supplier_risk_ok true; scheduled payment nets only when invoice_id matches
and date <= cutoff; approved chargebacks net, pending hold.

---

## 9. Per-task-archetype SOP checklists

**Sourcing nomination packet** (program, lines by sku):
program/owner/budget -> per line: requisition, PO(s), contract (commercial_basis), receipts
(<= as_of), invoices (exceptions), open risk -> blockers per the trigger list -> line
decision/readiness -> committee buckets + next_owner precedence + send_to_committee.

**Receiving closeout** (one batch):
receipt -> PO -> contract -> invoice(by receipt_id) -> supplier risk -> reconcile qtys/prices
-> exception_codes -> financials -> decision quartet -> evidence (include item sku; correct
payload path; no template).

**AP close** (named invoices only):
per invoice: PO, receipt(or none), payment(by invoice_id, <= cutoff) -> hold/release + reason
codes (NO_RECEIPT excludes QTY_VARIANCE) -> vendor balances (opening from memo) -> program
rollups -> hold/release queues -> total_close_balance = sum(close_balance).

**Change control** (amendment vs contract):
contract check (noncancelled subtotal, headroom) -> budget check (cap-committed, tax-loaded
max qty) -> approval check (latest action == approved) -> supplier risk (watch ok unless open
severe) -> decision = combination of failing checks -> required_actions + blocker_count +
ready_to_release.

**AP release / chargeback netting** (mixed exceptions):
target ids (sorted) -> per invoice: receipt(s) on PO (scope vs excluded sibling), chargeback
from local register (approved nets, pending holds) -> decision/primary_reason -> net amounts
-> receiving_exceptions (incl. MISSING rows, Severe on large shortfalls) -> summary
(release/hold ids, chargeback totals, net_release_total, authoritative vs supporting sources,
follow-ups incl. duplicate-receipt action).
