---
name: procureops-erp-answers
description: >-
  Produce the required JSON answer for a ProcureOps ERP "Procurement Supplier &
  Receiving Control" task — sourcing nomination readiness, receiving/AP
  reconciliation, AP close hold-or-release with vendor balances, change-control
  contract & budget-headroom decisions, and AP release with chargeback netting.
  Use this whenever a task hands you a ProcureOps API base URL plus a local
  memo/payload and an answer_template.json and asks for a decision packet, close
  file, reconciliation, readiness review, release/hold queue, nomination
  decision, or vendor-risk-as-of analysis over programs, suppliers, items,
  contracts, requisitions, purchase orders, receipts, AP invoices, payments,
  approvals, budget snapshots, or vendor-risk events. Trigger even when the word
  "ProcureOps" is absent but the inputs are an ERP procurement/AP/receiving API
  + a memo + a JSON template to fill.
---

# ProcureOps ERP answer builder

You turn a task prompt + a local memo/payload + an `answer_template.json` into a
single JSON object that matches the template, grounded in the live ProcureOps
ERP API. The API is the source of truth; the local memo names anchors and
business rules but can be stale.

This is a *judgment* task wearing a *data* costume. The arithmetic is simple
(sums, differences, rounding); the value is in scoping records correctly,
applying the right business rule, and not including records that don't belong.
Slow down on scoping and exclusions — that is where answers go wrong.

## Operating loop

1. **Read everything local first.** The prompt, the `answer_template.json`, and
   every file in `input/payloads/`. The template is your contract: it names the
   exact keys, enums, ordering, and rounding. Build your output to mirror it
   field-for-field. The memo names the anchor ids (program, PO, requisition,
   invoice, batch, contract) and any task-specific rules (tax rate, opening
   balance, cutoff date, which actions count as "approved", freight handling).

2. **Identify the task family** so you know the derivation pattern. Match on the
   template's top-level keys:
   - nomination_lines / committee_action → **A. sourcing nomination**
   - line_reconciliation / invoice_review / inspection_summary → **B. receiving/AP reconciliation**
   - invoice_decisions / vendor_balances / payment_hold_queue → **C. AP close**
   - contract_check / program_budget_check / approval_check → **D. change-control**
   - release_decisions / receiving_exceptions / chargeback → **E. AP release netting**

   You will also meet NEW templates that recombine these blocks. Don't pattern
   match rigidly — read the field names and the per-field notes in the template,
   then assemble from the building blocks in `references/derivations.md`.

3. **Pull the records from the API** (see "Using the API" below). Resolve each
   anchor id, then walk the graph the task needs: PO → its receipts + invoices +
   payments; supplier → risk events; requisition → approval events; program →
   budget snapshot + contract. The `scripts/probe.py` helper does the common
   walks (`bundle <po_id>`, `supplier <sid>`) so you don't hand-roll curl.

4. **Reconcile API vs local memo. The API wins** for any record you can fetch
   (quantities, prices, statuses, totals, dates). The memo wins only for things
   the API doesn't carry: task-supplied constants (tax rate, opening balance,
   cutoff), local registers (chargebacks), and which ids are in scope. If the
   memo references an id the shared API doesn't have (e.g. a "PO-73xx" alias),
   treat that note as supporting-only and use the real ids the packet provides.

5. **Compute derived values** with the recipes in `references/derivations.md`
   (budget/contract headroom, quantity & price reconciliation, variance,
   chargeback netting, max-quantity-within-budget). Compute on raw numbers,
   round at the very end.

6. **Apply the as-of / cutoff scope.** Almost every task has a date (`as_of`,
   `close_date`, `review_as_of`, snapshot date). Records dated after it are out
   of scope. The big one: a vendor-risk event is "open as of date" when
   `status ∈ {open, monitoring}` AND `event_date <= as_of`. `closed` is out;
   `monitoring` counts as open.

7. **Emit JSON only.** Match the template's keys exactly, fill the literal
   `task_id`/required values it specifies, honor enums verbatim, and write
   nothing outside the JSON object.

## Using the API

Base URL comes from the prompt; default `http://127.0.0.1:8056` (mirror at
`:8006` serves identical data — either works regardless of which port the prompt
prints). Read-only GET, JSON.

- **Fetch one:** `/<collection>/<id>` returns the bare object.
- **List + filter:** `/<collection>?field=value` — exact, case-insensitive
  match, and it matches fields nested inside list values too (e.g.
  `/ap/invoices?sku=DRV-AX17` matches the sku inside invoice `lines`). List
  responses are `{"count": n, "results": [...]}` — read `results`.
- **Date range:** `?start=YYYY-MM-DD&end=YYYY-MM-DD` filters each collection's
  primary date field (receipts.receipt_date, ap_invoices.invoice_date,
  payments.scheduled_date, etc.). Bounds are inclusive.
- **Collections:** programs, suppliers, items (by sku), contracts,
  purchase_requisitions, purchase_orders, receipts, ap/invoices, ap/payments,
  approval_events, budget_snapshots, vendor_risk_events. Also `/manifest`
  (counts + anchor ids) and `/health`.
- **Watch the join keys.** Most children carry the parent id directly
  (`po_id`, `supplier_id`, `program_id`, `contract_id`). The exception:
  **approval_events join on `object_id`, not `requisition_id`** — filter with
  `?object_id=REQ-...`.

Helper: `python3 scripts/probe.py {get|list|bundle|supplier} ... [--base URL]`.
Always pass `--base` if the prompt names a non-default port.

## Output conventions (hold these across all templates)

- **Money** rounds to cents (2 dp). Ratios to 4 dp, percentages to 1 dp, unless
  the field note says otherwise. Round once, at the end.
- **List fields are sets** — include each id once, order doesn't matter and the
  evaluator sorts — UNLESS the template says "sorted ascending"/"alphabetical"/
  "sort by X", in which case you sort exactly as instructed.
- **Enums verbatim.** Use only the allowed values the template lists, spelled
  and cased exactly. When several could apply, pick the one the business rule
  selects (see derivations); for combined-blocker enums (e.g.
  `hold_for_budget_and_approval`) compose per the template's allowed list.
- **Nulls** where the template allows them (e.g. `commercial_basis_id` /
  `hold_code` is null when there's no contract / no hold). Don't invent ids.
- **`task_id` and other required literal values** come from the template
  (`required_value`) — write them exactly, don't derive them from the prompt.
- **Evidence/source lists**: include every API record id you actually used and
  the local payload paths you read; classify into authoritative (API records,
  local registers the task says to trust) vs supporting-only (request notes,
  stale aliases) when the template asks for that split.

## High-leverage rules and common misjudgments

- **Headroom = cap − committed.** Budget headroom = `budget_cap −
  committed_amount` (program or its snapshot). Contract headroom = `ceiling −
  sum(subtotal of non-cancelled POs on the contract)`. Always **exclude
  cancelled POs** from contract usage; never exclude them silently from an
  `excluded_*` list the template asks for.
- **"Open risk as of date" is the most-missed scope.** open OR monitoring, and
  `event_date <= as_of`. Don't count closed events; don't forget monitoring.
- **`risk_rating` ≠ open risk event.** A supplier can be rated `watch`/`high`
  with no open event, or rated `low` with an open event (both happen in this
  data). `supplier_watch` blocker keys off the rating; `open_supplier_risk` keys
  off in-scope events. Keep them separate.
- **Duplicate invoices on one PO are an exception, not noise.** If two invoices
  hit the same PO, both belong in the line's exception id set.
- **Extra receipt on one PO is excluded, not summed.** Pick the receipt tied to
  the invoice/batch under review; route others to `excluded_same_po_receipt_ids`
  and don't fold their quantities into the reconciliation.
- **Missing receipt → explicit hold.** receipt_id null and no receipt for the PO
  ⇒ NO_RECEIPT / hold_missing_receipt / a `MISSING:<po_id>` exception row;
  received_qty = 0.00, full quantity is the variance.
- **Trust the controlling status, not the stale flag.** In netting/release
  tasks the local chargeback register's `status` (approved vs
  pending_quality_review) decides whether the chargeback nets now, even if the
  invoice's API `status` looks different. Confirm totals/receipts against the API.
- **Stay inside the named scope.** When a task says "these invoices only" / "this
  batch only", do not pull the supplier's or program's other records into the
  rollup.
- **Take invoice tax/freight/total verbatim** from the invoice; don't recompute
  tax unless the template/memo explicitly defines a rate to apply (change-control
  is the case where you DO compute requested_tax from the memo's rate).
- **`send_to_committee` / `ready_to_release` are conservative.** Only "yes"/true
  when nothing blocks. Any hard blocker ⇒ "no"/false.

For exact field-by-field math and the per-family recipes, read
`references/derivations.md`. Verify any arithmetic with a quick Python check
before writing it into the answer — a wrong cent fails the match.
