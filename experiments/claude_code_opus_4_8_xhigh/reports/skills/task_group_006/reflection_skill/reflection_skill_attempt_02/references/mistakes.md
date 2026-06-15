# Mistakes the blind pass made, and the corrected rule

This is the heart of the skill. Each entry is a real error from the first pass, the
root cause, and the rule that fixes it. Internalize these — they are the cheapest
points to recover.

## M1 — Treating any hold_code as an AP hold ("ap_hold")

**Mistake:** Tagged a line with the `ap_hold` blocker because its invoice carried a
`hold_code` (e.g. `NO_RECEIPT`), even though the invoice status was `pending_receipt`.

**Root cause:** Conflated "invoice has a hold_code" with "invoice is on AP hold".

**Corrected rule:** `ap_hold` applies **only** when an invoice `status == "on_hold"`.
A `pending_receipt` invoice (typically `hold_code == NO_RECEIPT`) is a missing-receipt
condition, captured by `pending_receipt`, not `ap_hold`. Check `status`, not the
presence of a hold_code.

## M2 — Adding "pending_receipt" whenever a PO is partially received

**Mistake:** Tagged a line `pending_receipt` because the PO status was
`partial_receipt`, even though an in-scope receipt existed for the line.

**Root cause:** Used PO status as the trigger instead of "is there receipt evidence?".

**Corrected rule:** `pending_receipt` applies when there is **no in-scope receipt at
all** against the PO/line (zero receipt evidence as of the as-of date). A line that is
partially received still HAS receipt evidence → no `pending_receipt`. (`partial_receipt`
PO status alone is not a blocker.)

## M3 — Routing AP-hold programs to finance_ops instead of ap_team

**Mistake:** Chose `next_owner = finance_ops` when the dominant blockers were AP holds.

**Root cause:** Mapped "money problem" → finance generically.

**Corrected rule:** When the binding blockers are AP holds / invoice exceptions, the
next owner is `ap_team` (the team that clears AP holds). Map the owner to the team that
owns the **specific** blocker:
- AP holds / invoice exceptions → `ap_team`
- budget overage → `finance_ops` / `program_owner` per template
- inspection / quality holds → `quality_ops`
- sourcing / requisition / PO gaps → `buyer`
Pick the team that resolves the gating blocker, not a generic finance bucket.

## M4 — Doubling up reason codes when there is no receipt (NO_RECEIPT + QTY_VARIANCE)

**Mistake:** For an invoice with no receipt, emitted both `NO_RECEIPT` and
`QTY_VARIANCE` (because billed - received = full billed qty, which looks like a
variance).

**Root cause:** Mechanically computed variance from received = 0 and added the variance
reason on top of NO_RECEIPT.

**Corrected rule:** When there is no receipt, the only reason is `NO_RECEIPT`. The
quantity-variance reason is **subsumed** and not emitted — a variance reason requires a
receipt to exist (a real billed-vs-received discrepancy on received goods). No receipt
⇒ `NO_RECEIPT` alone.

## M5 — Receiving exception codes: underage and severe co-exist; both stay

**Mistake:** On an underage receipt, emitted only `Underage Quantity` (dropping
`Severe Unmatched Quantity`), and on an inspection-hold underage receipt dropped
`Underage Quantity` (kept only `Inspection Hold` + `Severe Unmatched Quantity`).

**Root cause:** Treated the quantity codes as mutually exclusive / picked one.

**Corrected rule:** These codes stack, they don't replace each other. A quantity-underage
chargeback on a receipt produces **both** `Underage Quantity` **and**
`Severe Unmatched Quantity`. If the receipt is also on inspection hold, add
`Inspection Hold` too. An `AP Quantity Variance` chargeback (PO fully received but
billed > received) produces only `AP Quantity Variance`. Derive codes from the
chargeback register's `reason_code` plus the receipt state, and keep every code that
applies. (Lists are sets; the evaluator sorts.)

## M6 — Missing-receipt placeholder id

**Mistake:** For a receiving-exception row representing a PO with no receipt, used the
bare PO id (`PO-AX17-4519`) as the `receipt_id`.

**Root cause:** Needed a string but had no receipt id; guessed the PO id.

**Corrected rule:** Use an explicit missing marker, `MISSING:<po_id>` (e.g.
`MISSING:PO-AX17-4519`), so the row is unambiguously a no-receipt placeholder rather
than a real receipt id.

## M7 — Dropping a followup action that the data implied

**Mistake:** Omitted `hold_luma_duplicate_receipt_for_separate_invoice` from
`followup_actions`, reasoning that the duplicate same-PO receipt was already captured
in `excluded_same_po_receipt_ids`.

**Root cause:** Assumed the structured field "covered" the followup, so the narrative
followup was redundant.

**Corrected rule:** A condition that earns a structured flag ALSO earns its matching
followup action — they are independent outputs. If you excluded a duplicate same-PO
receipt because it belongs to a separate invoice, also emit the corresponding
"hold ... for separate invoice" followup. Enumerate one followup per real condition;
do not deduplicate across structured vs narrative fields.

## M8 — Evidence list completeness and payload path form

**Mistake (endpoint_record_ids):** Listed the PO, contract, supplier, receipt,
invoice, risk event, but **omitted the item/SKU record** even though the item endpoint
was consulted to confirm the line.

**Corrected rule:** `endpoint_record_ids` is the full set of every distinct API record
you actually relied on — including the **item/SKU** record and any program record. When
in doubt, include the record whose data appears in your answer.

**Mistake (task_payloads_reviewed):** Listed bare filenames and included
`answer_template.json`.

**Corrected rule:** List the **data** payloads you actually consulted, using the path
form the prompt uses (e.g. `input/payloads/receiving_memo.md`). The
`answer_template.json` is the output schema, not a data payload — do not list it as a
reviewed payload.

## M9 — Source-of-truth precedence (API over memo)

**Standing rule (the pass got this right; keep doing it):** The API is the system of
record. Local memos/packets name anchors (which PO, which invoice, which chargeback
register) and supply business parameters (tax rate, opening balance, cutoff date), but
any operational fact (price, quantity, status, dates, risk) comes from the API. If a
memo value conflicts with an API record, the API wins. Memo-only inputs (chargeback
register, opening balances, requested quantities, tax rates) are authoritative only for
the things the API does not carry.
