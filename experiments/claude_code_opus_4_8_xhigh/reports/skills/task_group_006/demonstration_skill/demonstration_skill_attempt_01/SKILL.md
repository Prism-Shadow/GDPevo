---
name: procureops-erp-answers
description: >-
  Produce the required JSON answer for ProcureOps ERP "Procurement Supplier and
  Receiving Control" tasks: sourcing nomination readiness, receiving/AP
  three-way reconciliation, AP close hold/release queues, contract + budget
  change-control decisions, and AP release/chargeback netting. Use this whenever
  a task points at the ProcureOps API (a localhost service exposing /programs,
  /suppliers, /contracts, /purchase_orders, /receipts, /ap/invoices,
  /ap/payments, /approval_events, /budget_snapshots, /vendor_risk_events) and
  asks for a JSON answer matching an answer_template.json, even if the prompt
  only says "nomination packet", "receiving closeout", "AP close", "change
  control decision file", "release file", "budget headroom", "vendor risk", or
  "reconciliation". Treat the live API as the source of truth over any local
  memo/export. Reach for this skill before hand-rolling any procurement/AP/ERP
  computation.
---

# ProcureOps ERP answer builder

You are turning a task prompt plus a local memo/payload into one JSON object that
matches a provided `answer_template.json`, using the live ProcureOps ERP API as
the system of record. The five task families you will see are nomination
readiness, receiving/AP reconciliation, AP close, change-control decision, and
AP release/chargeback netting — but the *mechanics* below transfer to any
unseen task in this domain. Lead with the rules, not with memorized answers.

## Golden rules (true for every task)

1. **The API is the source of truth; the local memo is a pointer, not data.**
   Memos and exports name the anchors (program, POs, invoices, receipts) and
   give business controls (tax rate, cutoff date, "exclude cancelled POs",
   opening balance). Whenever a quantity, price, status, or amount differs
   between a stale local file and the API, the API wins. Pull every figure you
   put in the answer from the API record, not from the memo's narrative.
2. **Match the template exactly.** Output *only* the JSON object, with the keys,
   nesting, and enum spellings the template specifies. Copy the literal
   `task_id` / `required_value` the template names. Do not add commentary keys.
3. **Money is rounded to cents** (2 decimals) unless a field says otherwise
   (e.g. `receipt_completion_ratio` precision 4, `quantity_variance_pct` 1
   decimal). Use the API's own `total`/`subtotal`/`tax`/`freight` fields rather
   than recomputing them — they are authoritative and already rounded.
4. **List fields are sets** (order-insensitive, deduped) **unless** the template
   says "sorted ascending" / "ordering: ... ascending" / "alphabetical". When it
   says sorted, sort ascending as strings. When it says "set; evaluator sorts",
   you may still emit sorted for readability.
5. **Everything is scoped to an as-of / cutoff date.** Read it from the prompt
   ("as of YYYY-MM-DD"), the memo, or the template's date field. Exclude records
   dated after it. "Open or monitoring as of date" means status filtering AND
   `event_date <= as_of`.
6. **Scope to the named targets only.** If the memo lists specific invoices /
   POs / SKUs, answer for exactly those, in the template's order. Do not pull in
   the supplier's other invoices unless the task asks for a vendor-wide balance.

## Step-by-step SOP

1. **Read the prompt, the memo/payload, and `answer_template.json`** in
   `input/payloads/`. The template is your contract: list its required keys,
   note every enum's allowed values, note each field's rounding/ordering, and
   note the literal `task_id`. Identify which task family this is from the keys
   (see `references/task_families.md`).
2. **Extract anchors and controls** from the memo: program_id, target POs /
   invoices / receipts / SKUs, the as-of/cutoff date, the tax rate, the opening
   balance, and any explicit rule ("exclude cancelled POs", "payment scheduled
   through DATE reduces balance", "approved actions = [approved]").
3. **Pull the live records.** For each anchor, GET it by id; for set-based needs
   (all POs on a contract, all receipts on a PO, all payments for a supplier,
   all risk events for a supplier), use list endpoints with query filters. See
   the API cheatsheet below.
4. **Compute the derived values** using the business rules in
   `references/business_rules.md`. The recurring computations — budget headroom,
   contract ceiling headroom, qty reconciliation, variance, chargeback netting,
   open-risk filtering — are defined there with exact formulas.
5. **Decide the enums** (decision / disposition / hold_decision / reason &
   blocker codes) from the rules. Decisions are deterministic functions of the
   computed checks; do not editorialize.
6. **Assemble and validate** with `scripts/validate_answer.py` (checks the JSON
   parses, top-level keys/enums look right, money is 2dp, sorted lists are
   sorted). Fix anything it flags. Emit only the JSON.

## ProcureOps API cheatsheet

Base URL comes from the prompt (commonly `http://127.0.0.1:8056`, mirror at
`:8006`; both serve identical data). Read-only GET, JSON.

- Fetch one record: `/<collection>/<id>` returns the bare object.
- List with filters: `/<collection>?field=value` returns
  `{"count": n, "results": [ ... ]}`. Filters match a field **exactly,
  case-insensitive**, including fields nested inside list values.
- Date range: `start=` and `end=` filter the collection's primary date field
  (`receipts.receipt_date`, `ap_invoices.invoice_date`,
  `payments.scheduled_date`, `vendor_risk_events.event_date`, etc.).

Collections: `/programs`, `/suppliers`, `/items` (by `sku`), `/contracts`,
`/purchase_requisitions`, `/purchase_orders`, `/receipts`, `/ap/invoices`,
`/ap/payments`, `/approval_events`, `/budget_snapshots`, `/vendor_risk_events`.
`/manifest` gives record counts and anchor ids; `/health` confirms it is up.

**Filter gotcha:** approval events are keyed by `object_id` + `object_type`, NOT
`requisition_id`. Use `/approval_events?object_id=REQ-...` (filtering by
`requisition_id` returns 0). When a filter unexpectedly returns `count: 0`,
re-check the actual field name on a sample record before concluding "no data".

Record shapes and the full field list are in `references/api_fields.md`.

## Derived-value quick reference (full detail in references/business_rules.md)

- **Budget headroom / remaining budget** = `budget_cap − committed_amount`
  (from the program or its `budget_snapshots` record; they agree). NOT minus
  pending_invoice_amount.
- **Contract ceiling headroom** = `ceiling_amount − Σ(subtotal of non-cancelled
  POs on that contract)`. Exclude `status == "cancelled"` POs. A requested line
  fits if `headroom_after_change = headroom_before − requested_subtotal >= 0`.
- **Quantity reconciliation** for a PO line: `received_qty` = sum of
  `quantity_received` across that PO's receipt lines (in scope per the task);
  `short_qty_vs_po = ordered − received`; `unreceived_billed_qty = max(0,
  billed − received)`; `quantity_variance = billed − received`;
  `quantity_variance_pct = round(variance / ordered_qty * 100, 1)`.
- **No receipt** → `quantity_received = 0`, variance = billed, pct = 100; the
  invoice holds with reason `NO_RECEIPT` / `no_receipt_on_po`.
- **Open / monitoring risk as of date** = vendor_risk_events for the supplier
  with `status in {open, monitoring}` and `event_date <= as_of`. "Severe" =
  `severity == "high"`. Closed events are excluded.
- **Scheduled payment reduces balance** only if its `scheduled_date <=` the
  memo's cutoff (commonly month-end). Sum matching payment `amount`s.
- **Chargeback netting**: `net_release = invoice_total − approved_chargeback`
  where approved chargeback = `basis_quantity × unit_cost` summed over register
  rows with `status == approved`. Pending (e.g. `pending_quality_review`)
  chargebacks do NOT net — they force a hold.
- **Duplicate / out-of-scope receipts**: if a PO has more than one receipt but
  the task scopes one, list the others under the "excluded same-PO receipt ids"
  field and hold them for their own invoice — do not net them here.

## Common misjudgments to avoid

- Using the **memo's** numbers when the **API's** differ (the API wins).
- Recomputing invoice/PO totals by hand and getting penny drift — use the
  record's `total`/`tax`/`freight` fields directly.
- Forgetting freight: invoice `total` includes freight; PO `total` may not.
- Subtracting `pending_invoice_amount` from the budget cap — headroom is just
  `cap − committed`.
- Counting **cancelled** POs in contract usage, or counting receipts/risk
  events dated after the as-of date.
- Treating a `submitted`/`escalated`/`returned` approval as approved — only the
  *latest* event with `action == approved` clears the approval gate.
- Letting a pending (not yet approved) chargeback net the invoice down — pending
  means HOLD, only approved chargebacks reduce the release amount.
- Pulling a supplier's unrelated invoices into a scoped, named-targets answer.
- Emitting prose outside the JSON, or dropping/renaming a required key.

When you need the precise decision tables, enum-to-condition mappings, and the
per-task field walkthroughs, read the two reference files. They are the heart of
this skill — open them before composing the answer.
