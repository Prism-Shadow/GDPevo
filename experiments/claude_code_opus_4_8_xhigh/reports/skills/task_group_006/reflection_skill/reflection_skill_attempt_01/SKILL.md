---
name: procureops-erp-task
description: >-
  Solve ProcureOps ERP analyst tasks: sourcing nomination readiness, receiving
  closeouts, AP payment-hold / vendor-balance reconciliation, change-control
  decision files, and AP release/hold files with chargeback netting. Use this
  skill WHENEVER a task references the ProcureOps API (http://127.0.0.1:8056 or
  the :8006 mirror), a local procurement memo/packet plus an
  answer_template.json, or asks for procurement/AP/receiving/contract/budget/
  vendor-risk decisions that must be returned as a structured JSON answer.
  Trigger even if the prompt only mentions "the shared API", "the close memo",
  programs like PRG-AX17 / PRG-NOVA, suppliers like SUP-LUMA, POs like PO-AX17-*,
  invoices like AP-*, receipts like RCV-*, or asks for hold/release/nomination/
  amendment decisions with controlled reason/blocker enums.
---

# Solving ProcureOps ERP tasks

ProcureOps is a procurement/AP ERP exposed as a read-only HTTP JSON API. A task
gives you three things: a **prompt**, one or more **local memo/packet payloads**,
and an **`answer_template.json`**. Your job is to produce a single JSON object
that conforms to the template, using the **API as the system of record** and the
memo only for scoping (which anchors to look at) and for task-specific business
rules (rates, cutoffs, opening balances).

The whole game is: (1) read the template field-by-field, (2) pull the right
records from the API, (3) apply the exact derivation rule for each field, (4)
honor the output conventions. Most errors come from subtle rule misreads, not
from missing data. This skill encodes the rules that were verified against
ground-truth answers, including the specific traps a blind pass fell into.

## Step-by-step SOP

1. **Parse the template first, not the prompt.** The template is the contract.
   List every leaf field, its type, its enum domain, and its ordering note
   ("sorted ascending" vs "set; evaluator sorts" vs "sort by X"). Note every
   rounding/precision hint and every `as of <date>` / cutoff phrase. Build your
   answer skeleton from the template before touching data.

2. **Establish scope from the prompt + memo.** Identify: the as-of / close /
   review date; the program(s); the named anchors (requisitions, POs, receipts,
   invoices, suppliers, contracts); any opening balances, tax rates, cutoffs, or
   "good action" lists the memo states. The memo names *what to look at*; the
   API tells you *what is true*. See "Source-of-truth precedence" below.

3. **Pull records by id, then by filter.** Fetch each named anchor by id. Then
   expand via filters: receipts/invoices/POs for a program or PO, risk events
   for a supplier, payments for a supplier, budget snapshot for a program. Use
   the `{count, results}` list shape. Confirm joins (see "Join gotchas").

4. **Derive each field with the verified formula** (see "Business rules").
   Apply date scoping at every list field flagged `as of <date>`.

5. **Apply output conventions** (money to cents, list-as-set vs sorted, enum
   spelling) — see "Output conventions".

6. **Self-check against the traps** in "Mistakes the blind pass made" before
   finalizing. These are the field-level errors that actually occurred.

7. **Write only the JSON** the template asks for. No prose outside the object.

## Using the ProcureOps API

Base URL `http://127.0.0.1:8056` (mirror `:8006`, identical data). Read-only GET.
If the prompt names a different port, prefer the base URL above.

- `GET /health`, `GET /manifest` (record counts, anchor ids, seed).
- Collections, each as list `?filters` or single `/<id>`:
  `/programs`, `/suppliers`, `/items` (key is `sku`), `/contracts`,
  `/purchase_requisitions`, `/purchase_orders`, `/receipts`, `/ap/invoices`,
  `/ap/payments`, `/approval_events`, `/budget_snapshots`, `/vendor_risk_events`.
- **Filtering**: query params match a field **exactly, case-insensitive**,
  including fields nested inside list values (e.g. a line's `sku`). Examples:
  `/purchase_orders?program_id=PRG-AX17`, `/ap/invoices?supplier_id=SUP-LUMA`,
  `/vendor_risk_events?supplier_id=SUP-LUMA`, `/receipts?po_id=PO-AX17-4481`.
- **Date ranges**: `start=` / `end=` apply to each collection's primary date
  field (`receipts.receipt_date`, `ap_invoices.invoice_date`,
  `payments.scheduled_date`, etc.). Prefer pulling broad and filtering dates in
  code so you can reason about inclusivity (cutoffs are inclusive of the date).
- **List shape**: `{"count": n, "results": [...]}`. A single-id fetch returns the
  bare object.

A ready-to-use Python client lives at `scripts/procureops.py` — it wraps GET,
list filtering, and the common joins. Read `references/api_and_data_model.md`
for the field shapes of each record type (line structures, status enums, etc.).

## Output conventions

- **Money to cents.** Round every USD amount to 2 decimals. `84.5` and `84.50`
  are numerically equal and both accepted; precision hints like `precision: 4`
  mean carry that many decimals (e.g. a completion ratio `0.9000`).
- **List ordering is per-field.** Read the template note for each list:
  - `"sorted ascending"` / `"sort ... ascending"` → you must sort (string sort).
  - `"set; evaluator sorts values"` → order does not matter; just include the
    right *members*. The membership (which ids) is what's graded.
  - `"sort by <field>"` for object lists → sort rows by that key.
- **Enums must match the template spelling exactly** (e.g. `on_hold`,
  `pending_receipt`, `OPEN_HELD`, `release_net_after_approved_chargeback`).
  Reason/blocker code lists are usually sorted ascending unless told "set".
- **Echo passthrough fields verbatim** from the template/memo (`task_id`,
  `program_id`, ids) — don't reformat them.
- **Date scoping is inclusive of the as-of/cutoff date.** A record dated exactly
  on the as-of date is *in scope*; a record dated after is *out of scope*.

## Source-of-truth precedence (API over memo)

The memo/packet is a pointer and a rule sheet, **not** a data source for record
values. When the memo and API disagree on a record's value, **the API wins**.
The memo legitimately supplies: which anchors are in scope, the as-of/cutoff
date, tax rates, opening balances ("treat opening as 0.00"), "good action"
lists, and netting/exposure definitions. It does *not* override invoice
statuses, quantities, prices, or risk states — read those live.

Some templates ask you to *classify* the sources you used: API record families
are **authoritative**; the memo's request notes / stale alias notes are
**supporting only**. List them accordingly.

## Business rules (verified formulas)

These were confirmed against ground-truth answers and re-queried live.

### Budget / program headroom
- `budget_headroom` / `remaining_budget` = `budget_cap − committed_amount`.
- Take `budget_cap` and `committed_amount` from the program record OR the
  budget snapshot — they agree. **Do NOT subtract `pending_invoice_amount`**;
  that snapshot field is *not* part of headroom.
- `budget_after_change` = `remaining_budget − requested_total`. Negative ⇒
  `budget_ok = false`.
- `requested_tax` = `requested_subtotal × tax_rate`; `requested_total` =
  `requested_subtotal + requested_tax` (+ freight only if the memo provides it).
- `max_quantity_with_current_budget` = `floor(remaining_budget /
  (unit_price × (1 + tax_rate)))` when the budget rule includes tax. Verify the
  boundary unit by hand (the last qty whose tax-laden cost ≤ remaining).

### Contract ceiling / headroom
- `noncancelled_subtotal` = sum of `subtotal` over POs on the contract **after
  excluding cancelled POs** (exclude `status == "cancelled"`).
- `headroom_before_change` = `ceiling_amount − noncancelled_subtotal`.
- `requested_subtotal` = `requested_quantity × contract.unit_price` (fixed-price
  contract). `headroom_after_change` = `headroom_before_change −
  requested_subtotal`. `ceiling_ok = headroom_after_change ≥ 0`.

### Quantity / price reconciliation
- `ordered_qty` = PO line `quantity`. `received_qty` = sum of receipt-line
  `quantity_received` (scope = the receipt(s) in scope — see date/PO scoping).
  `billed_qty` = invoice line `quantity_billed`.
- `short_qty_vs_po` = `ordered − received`. `unreceived_billed_qty` =
  `billed − received`. `receipt_completion_ratio` = `received / ordered`
  (carry the precision the template asks for).
- `quantity_variance` = `billed − received`. `quantity_variance_pct` =
  `variance / ordered_PO_qty × 100` (percentage is of **PO quantity**, not of
  billed). When there is **no receipt at all**, `received = 0.00` and the
  variance equals the full billed qty (pct relative to PO qty; for a no-receipt
  invoice that often lands at 100% when billed == PO qty).
- `contract_price_match` / price comparisons: compare PO unit price, contract
  unit price, and invoice unit price; equal ⇒ match true.

### AP payment decision, hold codes, vendor & program balances
- An invoice's `hold_decision` = `HOLD` unless its status is `approved` (clean
  three-way match). `release_to_payment = true` only for released/approved.
- `hold_code` is the invoice's own `hold_code` from the API (e.g. `QTY_VARIANCE`,
  `NO_RECEIPT`, `PRICE_VARIANCE`), or `null`.
- `quantity_received` for an invoice uses the invoice's **own linked receipt**
  (`invoice.receipt_id`), not all receipts on the PO. No linked receipt ⇒ `0.00`.
- **Scheduled-payment matching**: a payment counts only if it matches the
  invoice's `invoice_id` AND its `scheduled_date ≤ cutoff` (inclusive). Payments
  for other invoices of the same supplier do not net against this invoice.
  `net_balance_impact` = `invoice_total − scheduled_payment_amount`.
- `vendor_balances.close_balance` = `opening_balance + invoice_total −
  scheduled_payments` (opening per memo, often 0.00). `held_invoice_total` and
  `releasable_invoice_total` split the supplier's invoices by hold/release.
  `balance_status`: `FULLY_SCHEDULED` if close_balance ≈ 0 via scheduling,
  `OPEN_HELD` if held with no schedule, `OPEN_APPROVED` if approved but unpaid.
- `program_summary.net_close_balance` mirrors the vendor formula at program
  grain: `invoice_total − scheduled_payments` over that program's in-scope
  invoices. `total_close_balance` = sum of vendor close_balances.
- **Reason codes** (alphabetical): `APPROVED_THREE_WAY_MATCH` (status approved),
  `SCHEDULED_PAYMENT_FOUND` (qualifying scheduled payment), `QTY_VARIANCE`
  (billed > received with a receipt), `NO_RECEIPT` (no receipt / pending_receipt).
  For a no-receipt invoice, `NO_RECEIPT` is the sole quantity reason — do not
  also emit `QTY_VARIANCE` for the missing-receipt gap.

### Duplicate-invoice / multi-receipt scoping
- A PO can carry **multiple receipts and multiple invoices**. Match an invoice to
  its own `receipt_id`. Other receipts on the same PO that belong to a different
  invoice are **excluded** from this invoice's scope and should be reported in an
  `excluded_same_po_receipt_ids`-style field when the template asks. (A second
  receipt tied to a separate invoice is the "duplicate/extra receipt" to hold.)

### Chargeback netting (AP release file)
- A chargeback amount = `basis_quantity × unit_cost` from the local chargeback
  register (the register is authoritative for chargebacks).
- If the chargeback `status == "approved"`: decision
  `release_net_after_approved_chargeback`; `net_release_amount = invoice_total −
  approved_chargeback_amount`.
- If the chargeback `status == "pending_quality_review"` (or the receipt is on
  inspection hold): decision `hold_pending_quality_chargeback`; the amount goes
  to `pending_chargeback_amount`, `net_release_amount = 0`.
- No receipt on the PO ⇒ `hold_missing_receipt` / `no_receipt_on_po`, all 0.
- Totals: `approved_chargeback_total`, `pending_chargeback_total`, and
  `net_release_total` (= sum of the released nets) aggregate the per-invoice
  values.

### Supplier risk (open / monitoring, as-of-date)
- "Open supplier risk" events = `vendor_risk_events` for the supplier with
  `status` in {`open`, `monitoring`} AND `event_date ≤ as_of`. Exclude `closed`.
- A `risk_rating == "watch"` is **context only** — it raises a `supplier_watch`
  blocker / `SUPPLIER_WATCH_RISK` exception where the template lists one, but it
  does **not** by itself make `supplier_risk_ok = false`. Only an **open severe**
  event (severity high/critical) flips `supplier_risk_ok` to false; collect those
  into `severe_open_event_ids`.

### Approval state
- For a requisition's approval, query `approval_events` for that object id and
  take the **latest** event (by date). `approval_ok = true` only if the latest
  action is in the memo's "good actions" list (typically just `approved`);
  `submitted`/`pending` ⇒ not ok.

## Mistakes the blind pass made (and the corrected rule)

These are the actual field-level misses. Internalize each as a rule.

1. **`pending_receipt` blocker on a partially-received line.** The blind pass
   flagged `pending_receipt` because a line was only partly received (e.g. 216
   of 240). **Wrong.** `pending_receipt` fires **only when there is NO receipt
   evidence as of the date** (zero receipts on the PO in scope). A partial-but-
   accepted receipt counts as evidence and does **not** raise `pending_receipt`.
   - Corrected test: `pending_receipt` ⇔ `count(receipts in scope as_of) == 0`.

2. **`ap_hold` vs invoice-exception membership.** An invoice with status
   `pending_receipt`/`NO_RECEIPT` is still an *exception* (include it in
   `invoice_exception_ids`), but it is **not** an `ap_hold`. The `ap_hold`
   blocker fires **only when an in-scope invoice's status == `on_hold`**.
   - Corrected test: `ap_hold` ⇔ any in-scope invoice has status `on_hold`.
     Exception-id lists include any non-clean invoice (`on_hold` OR
     `pending_receipt`) dated ≤ as_of.

3. **Missing the item/SKU record in an evidence list.** The blind pass listed
   the supplier, contract, PO, receipt, invoice, and risk records but **omitted
   the item SKU record** it actually relied on. When the template asks for
   `endpoint_record_ids` (records consulted), include the **item `sku`** record
   too — it is a first-class record (`/items/<sku>`) and the SKU string is its id.
   - Corrected habit: list *every* endpoint record family you touched, including
     `/items`. Use the raw ids (the SKU is the item id).

4. **Wrong filenames in `task_payloads_reviewed`.** The blind pass used bare
   filenames and **included `answer_template.json`**. The template is the output
   contract, **not** a reviewed input payload. Use the **path as given in the
   prompt** (e.g. `input/payloads/<memo>.md`) and list **only the memo/packet
   payloads**, excluding `answer_template.json`.

5. **Omitting `Severe Unmatched Quantity` on a material underage.** The blind
   pass tagged only `Underage Quantity` when a receipt was short. **Both** codes
   apply when the receiving shortfall is material: a line short by ~10% of
   ordered (e.g. 24 of 240) already counts as **`Severe Unmatched Quantity`** in
   addition to `Underage Quantity`. A receipt with **no receiving shortfall**
   (received == ordered) but an over-bill is purely an `AP Quantity Variance`,
   not a severe-unmatched case.
   - Corrected rule: `Underage Quantity` ⇔ `received < ordered` (any shortfall).
     `Severe Unmatched Quantity` ⇔ a real receiving shortfall that is material
     (≥ ~10% of ordered, or a large absolute gap) — it accompanies, not replaces,
     `Underage Quantity`. `AP Quantity Variance` is billed > received with the
     receipt otherwise complete (no ordered-vs-received shortfall). See
     `references/exception_codes.md` for the worked thresholds.

6. **`null` vs `"MISSING:<po_id>"` placeholder for an absent receipt.** When a
   template row needs a `receipt_id` but no receipt exists, the convention is a
   sentinel string `"MISSING:<po_id>"`, not JSON `null`. Match whatever sentinel
   pattern the surrounding answer set uses; prefer an explicit string sentinel
   over `null` for a "missing receipt" row whose `resolution_status` is
   `missing_receipt`.

7. **Headroom formula temptation.** The blind pass *considered* subtracting
   `pending_invoice_amount` from the cap. Don't. Headroom is strictly
   `cap − committed`. (It got this right but flagged it as uncertain — lock it in.)

## What the blind pass got right (keep doing)
- Money/qty/variance arithmetic, contract ceiling netting (exclude cancelled),
  scheduled-payment matching by invoice id + cutoff, chargeback netting math,
  approval "latest event" logic, and `watch = context only` for risk-ok. These
  are correct; the formulas above codify them.

## Quick reference files
- `references/api_and_data_model.md` — endpoints, record shapes, status enums,
  join map, and the field-by-field SOP checklist.
- `references/exception_codes.md` — receiving/AP exception-code decision table
  with the verified underage/severe thresholds and blocker-vs-exception mapping.
- `scripts/procureops.py` — Python API client (GET, list filters, joins).
