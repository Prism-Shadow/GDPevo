---
name: procureops-erp-task
description: >-
  Solve a ProcureOps ERP analyst task end to end: read the prompt + local memo/packet
  + answer_template.json, pull source data from the ProcureOps read-only API, derive the
  required fields with verified formulas, and emit the answer JSON. Use this whenever a
  task involves ProcureOps (or a procurement/AP/receiving/contract/budget/vendor-risk
  ERP at http://127.0.0.1:8056 or :8006) and asks for a structured JSON deliverable —
  nomination/readiness packets, receiving-control closeouts, AP close / payment-hold
  reconciliations, change-control decision files, AP release/hold files, three-way-match
  or chargeback netting, budget/contract headroom, or supplier-risk-as-of-date reviews.
  Reach for it even if the prompt only says "follow the answer template" and names a
  PO/invoice/receipt/contract id.
---

# Solving a ProcureOps ERP task

You are given three things: a **prompt**, one or more **local payloads** (a memo/packet
plus `answer_template.json`), and access to the **read-only ProcureOps API**. Your job is
to produce a single JSON object that conforms to the template. The API is the system of
record; the memo names anchors and supplies business parameters.

These tasks are graded field-by-field. The cheapest points are lost on subtle rule
wording — enum mapping, date scoping, list set-membership, and "which condition fires
which code". Before you finalize, read `references/mistakes.md`; it lists the exact
errors a careful first pass still makes and the corrected rule for each.

## SOP

1. **Parse the template first.** Open `answer_template.json` and treat it as the
   contract. Note every key, its type, its enum allowed-values, its rounding/precision,
   and its ordering note. Build your answer object to the template's shape exactly — do
   not add or drop keys. The `task_id` is usually a fixed required value (e.g.
   `train_00N` or a `task_group_..._00N` string) — copy it verbatim from the template or
   prompt.

2. **Read the memo/packet for anchors and parameters only.** Pull: which program / PO /
   invoice / receipt / contract / requisition ids are in scope, the as-of / close /
   cutoff date, and any business parameters the API does not carry (tax rate, opening
   balance, chargeback register, "exclude cancelled POs", which actions count as
   approved). Do **not** take operational facts (price, qty, status, dates, risk) from
   the memo — those come from the API. (mistakes.md M9.)

3. **Pull source data from the API.** Use exact-match and date-range filters to gather
   everything tied to each anchor — not just the named record. For a PO line you
   typically need: the PO, its contract (if `contract_id`), all receipts for the PO, all
   invoices for the PO, the item/SKU, the supplier, the supplier's vendor-risk events,
   any payments by invoice_id, the program, and the program's budget_snapshot. See
   `references/api_guide.md` for endpoints, the `{count,results}` shape, filter fields,
   and per-collection schemas.

4. **Scope by the as-of / cutoff date.** Most lists are "as of `<date>`". Apply it:
   receipts with `receipt_date <= as_of`; invoices with `invoice_date <= as_of`;
   payments with `scheduled_date <= cutoff` (inclusive); vendor-risk events with
   `event_date <= as_of`. A record dated after the as-of date is excluded even if it
   exists. Re-read the template's note on each list ("as of as_of_date") and honor it.

5. **Derive every field with the exact formula.** Money to cents; quantities and
   variances per `references/formulas.md`. Do not recompute invoice tax/total from
   scratch — read them off the invoice unless the task supplies a rate to apply to a new
   line. Verify budget headroom uses `committed_amount` (not `pending_invoice_amount`).

6. **Map decisions, blockers, reasons, and owners from enums — carefully.** This is
   where most points live. Use the rules in `references/mistakes.md` and the gating logic
   below. Every enum value you emit must be in the template's allowed list, spelled
   exactly.

7. **Format lists correctly.** If the template says "sorted ascending", sort. If it says
   "set; evaluator sorts", emit the complete set (order doesn't matter, completeness
   does). For lists of objects, match the template's ordering key (e.g. "sort by
   po_line_id ascending", "invoice_id ascending"); when none is given, the evaluator
   matches objects by their natural key (sku / invoice_id / receipt_id), so make sure
   each object carries that key.

8. **Self-check against mistakes.md, then emit JSON only.** No prose outside the JSON
   object. Round money to 2 decimals; trailing-zero vs not is numerically identical
   (`68569.6` == `68569.60`).

## Gating logic cheat-sheet (verified rules)

Blockers / exceptions fire on **conditions**, and several conditions can co-exist —
emit every code that applies (lists are sets).

- **ap_hold** ⇐ an invoice on the line has `status == "on_hold"`. A `pending_receipt`
  invoice with `hold_code == NO_RECEIPT` is **not** an AP hold. (M1)
- **pending_receipt** ⇐ **no in-scope receipt at all** for the PO/line. A partially
  received line still has evidence → no pending_receipt. PO status `partial_receipt`
  alone is not a blocker. (M2)
- **missing_contract** ⇐ PO `contract_id` is null.
- **supplier_watch** ⇐ supplier `risk_rating == "watch"`.
- **open_supplier_risk** ⇐ a vendor-risk event with `status in {open, monitoring}` and
  `event_date <= as_of`. "Severe" requires `status == open` AND `severity == "high"`.
- **late_due_date** ⇐ PO `due_date` is later than the requisition `need_by` date.

Decision / readiness ladders (typical shape — always defer to the template's enum list):
- All checks pass → `nominate` / `release_*` / `RELEASE` / `ready`.
- Soft issues (watch, open non-severe risk, AP hold but contract+receipt present) →
  `conditional_nomination` / `at_risk`.
- Hard gaps (missing contract, no receipt, severe risk, budget/approval fail) →
  `hold` / `not_ready` / `HOLD`.

Reason codes:
- No receipt ⇒ `NO_RECEIPT` **only** (do not also add a quantity-variance reason). (M4)
- Receipt exists with billed > received ⇒ the quantity-variance reason.
- Approved three-way match (approved + receipt matches billed) ⇒ the approved-match
  reason (+ scheduled-payment reason if a matching scheduled payment exists).

next_owner ⇐ the team that clears the **gating** blocker: AP holds → `ap_team`;
budget → `finance_ops`/`program_owner`; quality/inspection → `quality_ops`; sourcing/PO
gaps → `buyer`. (M3)

Receiving exception codes (chargeback-driven, they stack):
- underage chargeback ⇒ `Underage Quantity` **and** `Severe Unmatched Quantity`; add
  `Inspection Hold` if the receipt status is inspection_hold. (M5)
- AP-quantity-variance chargeback (PO fully received, billed > received) ⇒
  `AP Quantity Variance` only.
- No receipt row ⇒ use `receipt_id = "MISSING:<po_id>"`, exception_codes `[]`,
  chargeback_status `not_applicable`, resolution `missing_receipt`. (M6)

Chargeback netting: approved → net & release; pending → hold (amount in pending);
no receipt → hold (zeros). Match chargebacks to invoices via the register. Every real
condition (e.g. a duplicate same-PO receipt belonging to another invoice) earns BOTH its
structured flag AND its followup action. (M7)

## Evidence / source fields

- `endpoint_record_ids` = every distinct API record you relied on, **including the
  item/SKU and program records** — not just the obvious PO/invoice. (M8)
- `task_payloads_reviewed` = the data payloads you actually read, in the prompt's path
  form (e.g. `input/payloads/receiving_memo.md`); do **not** list `answer_template.json`.
- `authoritative_sources` = the API record families (`procureops_po_records`,
  `..._receipt_records`, `..._ap_records`) plus `local_chargeback_register` if used.
  `supporting_only_sources` = notes/aliases that are context-only.

## Reference files

- `references/api_guide.md` — endpoints, filters, `{count,results}` shape, and the field
  schema of every collection. Read when pulling data.
- `references/formulas.md` — exact verified derivation formulas (qty, money, headroom,
  budget, netting). Read when computing numeric fields.
- `references/mistakes.md` — the corrected-rule catalogue (M1–M9). Read before
  finalizing; this is where points are recovered.
