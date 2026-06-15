---
name: procureops-erp-task-solver
description: >-
  Solve ProcureOps ERP analyst tasks that ask for a JSON answer derived from a prompt,
  a local memo/payload, and an answer_template.json, using the read-only ProcureOps API
  (programs, suppliers, items, contracts, requisitions, purchase orders, receipts, AP
  invoices, payments, approval events, budget snapshots, vendor-risk events). Use this
  whenever a task references ProcureOps, the http://127.0.0.1:8056 (or :8006) API, a
  sourcing-nomination / receiving-closeout / AP-close / change-control / AP-release packet,
  or any procurement reconciliation that mixes a local payload with a "source of truth"
  ERP API and a strict answer_template.json. It encodes the verified derivation formulas,
  enum/blocker mappings, date-scoping rules, and the specific mistakes that are easy to make.
---

# ProcureOps ERP Task Solver

ProcureOps tasks give you three things: a **prompt** (the business ask), one or more
**local payloads** (a memo, packet, or change request in `input/payloads/`), and an
**answer_template.json** that defines the exact output shape. Your job is to produce a
single JSON object that conforms to the template, deriving every value from the live API
(the system of record) plus whatever scope/anchor IDs the local payload supplies.

These tasks are graded field-by-field. Most errors come not from arithmetic but from
**scoping, enum mapping, and set-membership** decisions. This skill front-loads the rules
that are easy to get wrong. Read `references/rules.md` for the full formula/enum tables and
the catalogued mistakes; the body below is the operating procedure.

## Standard operating procedure

1. **Read all three inputs fully** before querying anything. The prompt sets the business
   goal and the `as_of`/close/review date. The payload supplies anchor IDs (program, POs,
   receipts, invoices, contract, requisition) and sometimes business-control parameters
   (tax rate, "exclude cancelled POs", opening balance, ceiling-exposure definition). The
   answer_template defines every output key, its enum domain, rounding, and list ordering.

2. **Treat the API as the source of truth; treat the payload as scope + controls.**
   When the payload and the API disagree on a *fact* (a price, status, quantity, date),
   the API wins. The payload is authoritative only for: which records are in scope, the
   business-control parameters it explicitly states, and any local-only register the task
   says to use (e.g. a chargeback register). See the source-precedence rule in
   `references/rules.md`.

3. **Pull every anchor record by ID, then expand via exact-match filters.**
   Base URL `http://127.0.0.1:8056` (mirror `http://127.0.0.1:8006`). All GET, read-only.
   - Fetch one: `/purchase_orders/PO-AX17-4481`, `/ap/invoices/AP-LUMA-7714`, etc.
   - List + filter (exact match, case-insensitive, matches fields nested in list values):
     `/ap/invoices?po_id=PO-AX17-4481`, `/vendor_risk_events?supplier_id=SUP-LUMA`,
     `/budget_snapshots?program_id=PRG-AX17`, `/purchase_orders?program_id=...&contract_id=...`
   - Date range on the collection's primary date field:
     `/ap/payments?start=2026-06-01&end=2026-06-30` (payments use `scheduled_date`,
     receipts `receipt_date`, invoices `invoice_date`).
   - Every list response is `{"count": n, "results": [...]}`. Always read `results`.
   - Do not assume one record per join. A PO can have several invoices and several
     receipts; always list and then filter to the right one (see receipt/invoice join
     gotcha in `references/rules.md`).

4. **Derive each field with the verified formula, not intuition.** Money is rounded to
   cents (2 dp) unless the template says otherwise; ratios/percentages use the precision
   the template states (e.g. completion ratio at 4 dp, variance pct at 1 dp). The exact
   formulas for budget headroom, contract headroom, max-quantity-with-budget, qty/price
   reconciliation, variance, vendor balances, and chargeback netting live in
   `references/rules.md` — use them verbatim.

5. **Scope every list field by date and status before emitting it.** "as of `as_of_date`"
   and "through `cutoff`" are filters: include a child record only if its primary date is
   `<= as_of` (receipts after the as-of date are *not yet evidence*; payments after the
   cutoff don't reduce the close balance). Open/monitoring risk events exclude `closed`.
   Cancelled POs are excluded from contract usage. Get the membership rules right — this
   is where the blind pass lost the most points.

6. **Map enums and decision/blocker codes from the template's allowed set only.** Never
   invent a value. For each enum field, find the template's `allowed_values` and pick from
   it using the decision rules in `references/rules.md`. Several codes look applicable but
   are mutually exclusive (e.g. NO_RECEIPT vs QTY_VARIANCE — see mistakes).

7. **Order lists exactly as the template says.** Default to treating list fields as **sets
   sorted ascending**. But honor explicit instructions: "set; evaluator sorts values" means
   ordering doesn't matter; "sort by po_line_id ascending" means sort by that key. When in
   doubt, sort ascending — it's the safe default and the evaluator usually sorts anyway.

8. **Build the answer to match the template key-for-key**, fill `task_id`/`*_id` constants
   the template hard-codes, and emit **only** the JSON object (no prose).

9. **Self-check before finishing:** every template key present; money at 2 dp; lists sorted
   per spec; date-scoped lists actually filtered; enums in-domain; cross-field invariants
   hold (e.g. `net_balance_impact == invoice_total - scheduled_payment_amount`,
   `total_close_balance == sum(close_balance)`, `blocker_count == number of failed checks`).

## The mistakes this skill exists to prevent

These are the concrete errors a careful-but-unguided pass made. Each has a corrected rule;
full detail and the underlying records are in `references/rules.md`.

- **`ap_hold` blocker is status-gated, not hold-code-gated.** An invoice flags `ap_hold`
  only when its **status == `on_hold`**. An invoice with `status=pending_receipt` and
  `hold_code=NO_RECEIPT` is *not* an `ap_hold` — it drives a `pending_receipt` blocker
  instead. (Blind wrongly added `ap_hold` for a pending_receipt invoice.)

- **`pending_receipt` blocker means *no receipt at all*, not "partial".** A line with a
  posted receipt (even a partial one, e.g. 216/240) does **not** get `pending_receipt`.
  Only a line/PO with zero receipts does. (Blind wrongly added it to a partially-received
  line.)

- **`late_due_date` compares PO `due_date` against the requisition `need_by`, not against
  the as-of date.** Flag late when `po.due_date > requisition.need_by`. Both being after
  the as-of date is irrelevant. (Blind missed `late_due_date` because it tested the wrong
  pair of dates.)

- **NO_RECEIPT excludes QTY_VARIANCE.** When an invoice has no receipt, `quantity_received`
  is 0 and the variance equals the full billed qty — but the reason code is **just
  `NO_RECEIPT`**. Do not also add `QTY_VARIANCE`; the absence of a receipt is the single
  controlling exception. (Blind added both.)

- **`invoice_exception_ids` (the evidence list) is broader than the `ap_hold` blocker.**
  The exception/evidence list includes any non-clean invoice in scope (status `on_hold`
  *or* `pending_receipt`, dated `<= as_of`), even though only `on_hold` triggers the
  `ap_hold` blocker. Keep these two concepts separate.

- **`next_owner` routing follows a precedence, and an open AP hold routes to `ap_team`.**
  When the gating issue is an unresolved on-hold invoice, the next owner is `ap_team`, not
  `program_owner`. Route to the owner of the *highest-precedence open blocker* (see the
  precedence ladder in `references/rules.md`), not to a generic "mixed issues → program
  owner" default.

- **`endpoint_record_ids` evidence includes the item/SKU record, not just the
  PO/receipt/invoice/contract/supplier/risk IDs.** If you looked up `/items/<sku>` (or the
  SKU is a first-class record you relied on), include the SKU in the evidence set. (Blind
  omitted the item SKU.)

- **`task_payloads_reviewed` uses the path the template/prompt references and lists only
  payloads actually consumed.** Match the reference style the inputs use (e.g. the full
  `input/payloads/<file>` path) and do **not** list `answer_template.json` as a reviewed
  payload — it defines the output, it isn't a source you reconciled. (Blind used a bare
  filename and wrongly added the template.)

- **"Severe Unmatched Quantity" is added on top of "Underage Quantity" for large
  shortfalls.** A receiving underage gets `Underage Quantity`; when the shortfall is large
  (double-digit basis quantity / a sizable fraction of the order, ~>=10% or >=10 units),
  it *also* gets `Severe Unmatched Quantity`. A small AP-only over-bill (e.g. basis 4) gets
  only `AP Quantity Variance` and no severe/underage code. Recompute these from the
  chargeback register reason + magnitude rather than guessing one code per receipt. (Blind
  dropped `Severe Unmatched Quantity` on both large-shortfall receipts.)

- **Emit a row for the *missing* receipt, don't skip it.** When a scoped PO has no receipt,
  the receiving-exceptions list still needs a placeholder row (`receipt_id` like
  `MISSING:<po_id>`, empty exception_codes, `chargeback_status=not_applicable`,
  `resolution_status=missing_receipt`). Absence is itself a reportable exception. (Blind
  produced no row for the missing receipt.)

- **A duplicate/second receipt on the same PO drives both an exclusion and a follow-up.**
  When two receipts sit on one PO and the invoice in scope maps to one of them, exclude the
  other (`excluded_same_po_receipt_ids`) *and* raise the corresponding follow-up action
  (e.g. "hold the duplicate receipt for its separate invoice"). Don't just exclude it
  silently. (Blind excluded the receipt but forgot the follow-up action.)

## Things the blind pass got right — keep doing these

These were verified correct against the standard answers and are reliable defaults:

- **Budget headroom / remaining budget = `budget_cap - committed_amount`** (from the
  program record or its budget snapshot). Do **not** use `pending_invoice_amount`.
- **Contract headroom = `ceiling_amount - noncancelled_subtotal`**, where the subtotal sums
  PO subtotals on the contract **excluding cancelled POs**. Requested subtotal = qty x
  contract unit price.
- **`max_quantity_with_current_budget = floor(remaining_budget / (unit_price * (1+tax)))`**
  — the per-unit cost is **tax-loaded**, then floored.
- **`supplier_risk_ok = true` for a `watch` rating** as long as there's no *open severe*
  (high/critical) event; `watch` is context-only otherwise. Open events list excludes
  `closed`.
- **Qty reconciliation:** `short_qty_vs_po = ordered - received`;
  `unreceived_billed_qty = billed - received`; `completion_ratio = received/ordered`;
  `quantity_variance = billed - received`; `variance_pct = variance / PO_qty * 100`.
- **Scheduled-payment netting:** a payment reduces the close balance only when it matches
  the invoice by `invoice_id` and its `scheduled_date <= cutoff`. `close_balance =
  opening + invoice_total - scheduled_payments`.
- **Chargeback netting:** `net_release_amount = invoice_total - approved_chargeback_amount`;
  only **approved** chargebacks net; **pending_quality_review** chargebacks hold the
  invoice (net release 0). Chargeback amount = `basis_quantity * unit_cost`.

See `references/rules.md` for the full tables, the field-by-field formula reference, and the
endpoint/join cheatsheet.
