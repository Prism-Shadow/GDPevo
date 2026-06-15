---
name: procureops-control-answers
description: >-
  Produce the required JSON answer for ProcureOps ERP "Procurement Supplier and
  Receiving Control" tasks: sourcing nomination readiness packets, receiving/AP
  three-way reconciliation, AP close hold/release decisions, contract change-control
  decision files, budget/contract headroom checks, vendor-risk scoping, and AP
  release/chargeback netting. Use this skill WHENEVER a task references the
  ProcureOps API (a localhost service exposing /programs, /suppliers, /contracts,
  /purchase_orders, /receipts, /ap/invoices, /ap/payments, /approval_events,
  /budget_snapshots, /vendor_risk_events), asks you to fill an answer_template.json
  against ERP records, or mentions nomination, receiving control, AP hold/release,
  three-way match, chargeback, budget headroom, or supplier-risk-as-of-date — even
  if the words "ProcureOps" or "ERP" are not used but a localhost procurement API
  plus a JSON answer template are involved.
---

# ProcureOps Procurement & Receiving Control — Answer Builder

You are turning a task `prompt.txt` plus a local memo/payload into a single JSON
answer that matches a provided `answer_template.json`, using a live ProcureOps ERP
API as the system of record. The grader compares your JSON field-by-field, so
precision on field names, enums, rounding, set membership, and date scoping is what
matters — not prose.

## Golden rules (the whole skill in five lines)

1. **The API is the source of truth. Local memos/exports only name the anchors
   (which ids to look at) and supply task-only numbers (tax rates, chargeback basis
   quantities, opening balances).** When a memo value disagrees with the API, the
   API wins — except for values the API genuinely does not contain (see "Source
   precedence").
2. **Match the template literally.** Output exactly the keys it lists, with the
   enum values it allows, the rounding it specifies, and the list ordering it
   specifies. Do not add or rename keys.
3. **Scope to the as_of / cutoff / close date.** Records dated *after* the scoping
   date do not exist for your answer. This silently excludes "newer" rows.
4. **Treat list fields as sets (dedupe, then sort ascending) unless the template
   says otherwise.** Most templates say "sorted ascending" or "evaluator sorts";
   either way, emit ascending-sorted, de-duplicated lists.
5. **Money rounds to cents (2 dp). Ratios/percentages use the precision the
   template names (often 4 dp for ratios, 1 dp for percentages).** Round only at
   the end.

## Step-by-step SOP

### 1. Read the three inputs first
- `input/prompt.txt` — the business ask, the base URL, and any scoping date.
- `input/payloads/answer_template.json` — the **contract for your output**. Read it
  twice: once for the key skeleton, once for every `allowed_values`, `ordering`,
  `precision`, `required_value`, and inline note (`"as of as_of_date"`,
  `"use 0.00 when no receipt exists"`, etc.).
- `input/payloads/<memo>` — names the anchor ids (programs, POs, receipts, invoices,
  suppliers, contracts) and any task-only constants. Note its filename; some
  templates ask you to echo it in a `task_payloads_reviewed` / `supporting_only`
  field.

Pull out: the `task_id` (templates often hardcode the exact required value, e.g.
`required_value: "train_NNN"` — copy it verbatim), the program id, the scoping date,
and the explicit list of target ids to restrict the answer to.

### 2. Find the base URL and confirm the API is live
The base URL is in the prompt (commonly `http://127.0.0.1:8006`; a mirror at
`http://127.0.0.1:8056` serves identical data — either works). Confirm with
`GET /health` and skim `GET /manifest` for record counts and anchor ids. Use `curl`
or Python `urllib`/`requests`; all calls are read-only GETs.

### 3. Pull every anchor record, then expand outward
For each anchor id named in the memo, fetch the record by id, then follow its
foreign keys (a PO points to program/supplier/contract/requisition; an invoice
points to PO/receipt/supplier; a receipt points to PO/supplier). See
`references/api_field_map.md` for the exact field on each record type and the
filter keys that actually work (notably: approval events filter on `object_id`, not
`requisition_id`; POs on a contract filter on `contract_id`).

Prefer **id lookups** (`/collection/<id>`) for known anchors and **query filters**
for "all rows matching X" (`/ap/invoices?supplier_id=SUP-LUMA`). Filters match a
field exactly, case-insensitively, including fields nested inside list values. List
responses are shaped `{"count": n, "results": [...]}` — iterate `results`.

### 4. Apply date scoping
Filter every derived list to records dated on/before the as_of/cutoff date. Use the
collection's primary date field (`receipts.receipt_date`, `ap_invoices.invoice_date`,
`payments.scheduled_date`, `vendor_risk_events.event_date`,
`approval_events.event_date`). You can pre-filter on the server with `start=`/`end=`,
but always re-check the boundary yourself — a record dated *after* as_of must be
dropped from "as of" lists (e.g. an on-hold invoice dated after the as_of date is
NOT an exception for that date).

### 5. Compute the derived values
Use the formulas in "Business rules" below. Round only at the very end.

### 6. Assemble and validate the JSON
- Every template key present, no extras, enums exactly as spelled.
- Lists de-duplicated and sorted ascending (string sort is fine for these ids).
- Numbers rounded per the template; integers stay integers (e.g. `quantity` fields).
- Output **only** the JSON object — no markdown fence, no commentary.

A reusable helper is in `scripts/procureops.py` (a tiny GET client + rounding/sort
helpers); import it or copy the snippet. It is optional — plain curl works too.

## Source precedence (API vs. local memo)

| Need | Authoritative source |
| --- | --- |
| Program/supplier/contract/PO/receipt/invoice/payment/budget/approval/risk facts | **API record** |
| Which ids are in scope | Memo names them; verify each exists in the API |
| Tax rate, freight inclusion rule, opening AP balance, "good" approval actions | Memo (task-only business controls) |
| Chargeback basis quantity / unit cost / approval status | **Local chargeback register** in the payload (the API has no chargeback table) |
| Requester comments, "release this please" notes, stale PO-alias notes | **Supporting only** — context, never a decision driver |

When a memo says e.g. "use the generated PO/receipt ids named here because the
PO-73xx ids aren't in the shared data", treat the named ids as the in-scope ids and
treat the stale-alias note as a *supporting_only* source, not authoritative.

## Business rules and derived values

### Budget / program headroom
- `remaining_budget` (a.k.a. budget headroom) `= budget_cap - committed_amount`,
  read from the program record or the matching `budget_snapshot` (they agree; the
  snapshot also carries `snapshot_id` and `snapshot_date`). Do **not** subtract
  `pending_invoice_amount` for headroom.
- `requested_subtotal = requested_quantity * contract_unit_price`.
- `requested_tax = requested_subtotal * tax_rate` (tax rate comes from the memo,
  e.g. 7.25% → multiply by 0.0725). `requested_total = subtotal + tax` (+ freight
  only if the memo supplies freight).
- `budget_after_change = remaining_budget - requested_total`; `budget_ok` is
  `budget_after_change >= 0`.
- `max_quantity_with_current_budget = floor(remaining_budget / (unit_price * (1 + tax_rate)))`
  — i.e. the largest integer quantity whose tax-loaded subtotal still fits the
  remaining budget.

### Contract ceiling / headroom
- `noncancelled_subtotal` = sum of `subtotal` over all POs on the contract whose
  status is **not** `cancelled`. Filter `/purchase_orders?contract_id=<id>`. Keep
  the included PO ids (sorted) and the excluded `cancelled` PO ids (sorted)
  separately when the template asks.
- `headroom_before_change = ceiling_amount - noncancelled_subtotal`.
- `headroom_after_change = headroom_before_change - requested_subtotal`.
- `ceiling_ok` is `headroom_after_change >= 0`.

### Quantity reconciliation (received vs ordered vs billed)
For a PO line with `ordered_qty` (PO line quantity), `received_qty` (sum of accepted
receipt-line `quantity_received`), `rejected_qty` (sum of `quantity_rejected`), and
`billed_qty` (invoice-line `quantity_billed`):
- `short_qty_vs_po = ordered_qty - received_qty`.
- `unreceived_billed_qty = billed_qty - received_qty` (floor at 0 conceptually).
- `receipt_completion_ratio = received_qty / ordered_qty` (4 dp).
- `quantity_variance = billed_qty - received_qty`.
- `quantity_variance_pct = quantity_variance / ordered_qty * 100` (1 dp; PO quantity
  is the denominator, not billed quantity).
- `received_goods_value = received_qty * unit_price`;
  `unreceived_goods_value = (billed_qty - received_qty) * unit_price`.

### Price reconciliation / three-way match
- `po_unit_price` from the PO line, `contract_unit_price` from the contract,
  `invoice_unit_price` from the invoice line. `contract_price_match` is true iff
  invoice price equals contract price.
- A clean three-way match = invoice `status` is `approved`/no hold, billed == received,
  and price matches → release. Anything else holds.

### Invoice financial totals
Use the API invoice fields directly: `invoice_subtotal = subtotal`,
`invoice_freight = freight`, `invoice_tax = tax`, `invoice_total = total`
(`total = subtotal + freight + tax`). Note the **PO** `total` excludes freight while
the **invoice** `total` includes it — don't cross them up.

### AP hold / release decisions
Drive the decision from the invoice's own `status` and `hold_code`, then map to the
template's enum:
- `status = approved`, `hold_code = null`, receipt present, qty matches → RELEASE /
  `release_to_payment=true`; reason like `APPROVED_THREE_WAY_MATCH`.
- `status = on_hold` with `hold_code = QTY_VARIANCE` → HOLD, reason `QTY_VARIANCE`.
- `status = pending_receipt` or `hold_code = NO_RECEIPT` or `receipt_id = null` →
  HOLD, reason `NO_RECEIPT`.
- `PRICE_VARIANCE`, `SUPPLIER_REVIEW` are other real hold codes.
- Add `SCHEDULED_PAYMENT_FOUND` when a matching scheduled payment exists (below).

### Scheduled payments (close balance)
A payment reduces the close/vendor balance only if it matches a target invoice
(`payments.invoice_id`) AND its `scheduled_date` is on/before the cutoff the memo
gives (e.g. "scheduled through 2026-06-30"). Sum `amount` of those.
- `net_balance_impact = invoice_total - scheduled_payment_amount`.
- `close_balance = opening_balance + invoice_total - scheduled_payments` (opening
  balance is the memo-stated slice opening, often 0.00).
- `balance_status`: `FULLY_SCHEDULED` when scheduled covers the total and nothing is
  held; `OPEN_HELD` when the invoice is held; `OPEN_APPROVED` when approved but not
  yet fully scheduled.

### Vendor-risk scoping ("open or monitoring as of date")
`vendor_risk_events.status` is one of `open` / `monitoring` / `closed`. An event
counts as an active/open supplier-risk event iff its status is `open` **or**
`monitoring` and its `event_date` is on/before the as_of date. Exclude `closed`.
- `severe`/high-severity open events = those above plus `severity = high` (used for
  fields like `severe_open_event_ids`; a `watch`-rated supplier with only
  medium/low open events is usually "risk ok" / context-only).
- Supplier `risk_rating` (`low|watch|high`) and `status` (`active|...`) come from the
  supplier record; a `watch` rating alone is context, not a hard blocker, unless the
  template/memo says otherwise.

### Chargeback netting (AP release files)
Chargeback rows live in the **local register** payload, not the API. Each row has a
`reason_code`, `basis_quantity`, `unit_cost`, and `status`.
- chargeback amount `= basis_quantity * unit_cost`.
- If `status = approved` → it is an approved chargeback; `net_release_amount =
  invoice_total - approved_chargeback_amount`; decision
  `release_net_after_approved_chargeback`.
- If `status = pending_quality_review` (or the receipt is on inspection hold) → it is
  a pending chargeback; hold the invoice, `net_release_amount = 0`, decision
  `hold_pending_quality_chargeback`.
- If the invoice's PO has **no receipt** (receipt_id null / none on the PO) → decision
  `hold_missing_receipt`, reason `no_receipt_on_po`, net 0. Represent a missing
  receipt explicitly when the template expects a row (e.g. `"MISSING:<po_id>"`).
- When one PO has multiple receipts, the in-scope receipt is the one the chargeback
  register/invoice points at; the other receipt(s) on that PO go in
  `excluded_same_po_receipt_ids` (a possible duplicate-receipt to hold for a separate
  invoice).

### Receiving exception codes (set per receipt)
Derive from receipt + PO + register, e.g.:
- `Underage Quantity`: received < ordered.
- `Severe Unmatched Quantity`: a large received-vs-ordered gap (a big short).
- `Inspection Hold`: receipt `status = inspection_hold` (or a failed inspection line).
- `AP Quantity Variance`: the register flags an AP qty variance for that receipt.
Map the receipt's chargeback status and resolution to the template enums
(`net_release_ready`, `hold_for_quality_review`, `accepted_no_receiving_exception`,
`missing_receipt`).

### Nomination readiness (sourcing packets)
Per package line, choose the selected supplier (the contract/PO supplier for the
sku), then collect, **as of the as_of date**:
- `package_po_ids` (the line's POs), `receipt_evidence_ids` (accepted receipts on
  those POs), `invoice_exception_ids` (that supplier's on-hold / hold-coded invoices
  relevant to the line, dated ≤ as_of), `risk_event_ids` (open/monitoring events
  ≤ as_of), and `commercial_basis_id` (the governing contract id, or null if none).
- `blocker_codes` (sorted set) from: `missing_contract` (no active contract),
  `supplier_watch` (supplier risk_rating = watch), `open_supplier_risk` (an
  open/monitoring risk event), `ap_hold` (an on-hold invoice), `pending_receipt`
  (billed/ordered but not yet received), `late_due_date` (PO due date passed with no
  receipt). Use `none` only when there are zero blockers.
- `nomination_decision`: `nominate` (no blockers), `conditional_nomination` (only
  soft blockers like supplier_watch / a clearable ap_hold), `hold` (a hard blocker
  like missing_contract, pending_receipt, or open_supplier_risk).
- Roll the line decisions up into the committee buckets and `send_to_committee`
  (`no` if any line is on hold). `overall_readiness` is `not_ready` if any line is
  not_ready, else `at_risk` if any is at_risk, else `ready`.

## Common misjudgments to avoid
- **Trusting the memo's numbers over the API.** Re-derive subtotals/totals/quantities
  from API records; the memo's prose is often rounded or stale.
- **Forgetting the as_of cutoff**, so you include an invoice/receipt/risk event dated
  after the scoping date. Drop anything later than the cutoff.
- **Including closed risk events** or **cancelled POs**. Exclude `closed` events and
  `cancelled` POs from active/headroom rollups (but list cancelled POs in the
  dedicated "excluded" field when asked).
- **Using billed quantity as the variance denominator.** Percentage variance is
  against PO ordered quantity.
- **Mixing PO total (no freight) with invoice total (with freight).**
- **Subtracting pending_invoice_amount when computing headroom.** Headroom is
  `cap - committed` only.
- **Emitting unsorted or duplicated id lists.** Always dedupe + sort ascending unless
  a template explicitly asks for a different order (e.g. "sort by po_line_id").
- **Letting a requester's "please release" note drive a release.** Notes are
  supporting-only; the receipt/PO/AP records and the chargeback status decide.
- **Adding narrative or extra keys.** Return only the JSON the template defines.

## Reference files
- `references/api_field_map.md` — every endpoint, the fields it returns, which filter
  keys work, and the enum value sets (PO/invoice/receipt/risk statuses, hold codes).
  Read it before writing API calls so you query the right field names.
- `scripts/procureops.py` — optional helper: `get(path)`, `get_list(path, **filters)`,
  `money(x)`, `as_set(ids)`. Saves re-writing a GET client per task.
