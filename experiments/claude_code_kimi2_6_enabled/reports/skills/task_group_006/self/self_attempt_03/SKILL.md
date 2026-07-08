# ProcureOps AX17 Review & Close Skill

## Domain Overview
Tasks involve preparing structured JSON review packets for the AX17 procurement program using the **ProcureOps API** and local memo/packet files. There are four review types:

1. **Nomination Review** (`train_001`) – Pre-pay nomination decisions
2. **AP Release / Exception Review** (`train_002`, `train_005`) – Post-receipt release/hold decisions
3. **AP Close Check** (`train_003`) – Month-end close reconciliation
4. **Change Memo Analysis** (`train_004`) – PO change order quantification

All tasks return strict JSON conforming to `input/payloads/answer_template.json`.

---

## 1. API Usage Habits

### Base URL
```
http://127.0.0.1:8006
```

### Likely Endpoints to Discover
Since exact paths are not documented in prompts, probe for REST-style resources:
- `GET /po` or `GET /po/{po_id}` or `GET /po?program_id=PRG-AX17`
- `GET /receipts` or `GET /receipts/{receipt_id}`
- `GET /invoices` or `GET /invoices/{invoice_id}`
- `GET /payments` or `GET /payments?supplier={supplier_name}`
- `GET /suppliers` or `GET /suppliers/{supplier_name}`

**Approach:** Start with a root `GET /` or `GET /docs` to discover available routes. If the API is not running locally, note the expected schema and proceed with provided payload data.

### Query Strategy
1. Identify all `target_ids` from the prompt or local packet (`po_ids`, `receipt_ids`, `invoice_ids`).
2. Fetch each record from ProcureOps individually or in batch.
3. Cross-reference with local memos/packets.
4. **ProcureOps is the system of record** for factual data (quantities, amounts, statuses, payments). Local files provide context (chargeback reasons, release request notes, change reasons) but do not override ProcureOps records.

---

## 2. Handling PO-73xx Alias Notes

A recurring quirk: exact `PO-73xx` receipt identifiers are **not present** in the shared API environment.

**Rule:** Use the generated PO/receipt IDs explicitly named in the local packet or memo. Do not invent or assume `PO-73xx` identifiers exist in ProcureOps.

Example from packet:
```json
"po73xx_alias_note": {
  "use_available_shared_ids": ["PO-00031", "PO-00038"]
}
```

---

## 3. Output Conventions (All Tasks)

### General JSON Rules
- Return **only** a JSON object matching `answer_template.json`.
- **No narrative explanations** outside JSON; use controlled reason codes.
- Sort all ID lists ascending (`list_ordering: "Sort ID lists ascending."`).
- Dates: `YYYY-MM-DD`.
- Currency: USD, rounded to **cents** (two decimal places), represented as `number`.

### Source Categorization
Every summary must classify sources into two buckets:

| `authoritative_sources` | `supporting_only_sources` |
|---|---|
| `procureops_po_records` | `ap_release_request_note` |
| `procureops_receipt_records` | `stale_po73xx_alias_note` |
| `procureops_ap_records` | `local_nomination_memo` |
| `local_chargeback_register` | `local_change_memo` |

**Rule:** Anything fetched from the live API is authoritative. Local text memos and request notes are supporting only.

---

## 4. Business Rules by Review Type

### 4.1 Nomination Review (`nomination_decisions`)

| `decision` | `primary_reason` | Condition |
|---|---|---|
| `release_to_pay` | `approved_qty_chargeback` | Approved chargeback exists, receipt accepted |
| `release_to_pay` | `accepted_no_variance` | No exceptions, clean receipt |
| `hold_inspection` | `inspection_hold_pending_chargeback` | Quality review pending |
| `hold_receipt_gap` | `no_receipt_on_po` | Missing receipt for invoice line |

**Calculations:**
- `approved_chargeback_amount` = Σ(`basis_quantity` × `unit_cost`) for status = `approved`
- `pending_chargeback_amount` = Σ(`basis_quantity` × `unit_cost`) for status = `pending_quality_review`
- `net_release_amount` = `invoice_total` − `approved_chargeback_amount` − `pending_chargeback_amount`

### 4.2 AP Release Review (`release_decisions`)

| `decision` | `primary_reason` | Condition |
|---|---|---|
| `release_net_after_approved_chargeback` | `approved_qty_chargeback` or `approved_ap_quantity_variance` | Chargeback approved, net after deduction |
| `hold_missing_receipt` | `no_receipt_on_po` | No matching receipt found |
| `hold_pending_quality_chargeback` | `inspection_hold_pending_chargeback` | Chargeback pending quality review |

**Same financial calculations as nomination.**

### 4.3 Receiving Exceptions (Shared by Nomination & Release)

| `exception_codes` | `chargeback_status` | `resolution_status` |
|---|---|---|
| `Underage Quantity` | `approved` or `pending_quality_review` | `net_release_ready` or `hold_for_quality_review` |
| `Severe Unmatched Quantity` | `approved` or `pending_quality_review` | `net_release_ready` or `hold_for_quality_review` |
| `Inspection Hold` | `pending_quality_review` | `hold_for_quality_review` |
| `AP Quantity Variance` | `approved` | `net_release_ready` |
| None / clean | `not_applicable` | `accepted_no_receiving_exception` |
| Missing receipt | `not_applicable` | `missing_receipt` |

**Rule:** Map the `reason_code` from the local chargeback register to the `exception_codes` enum. Use the register's `status` field to set `chargeback_status`.

### 4.4 AP Close Check (`close_records`)

**Context:** The May 31 opening AP balance for target suppliers in the slice is `0.00 USD`.

| `close_reason_code` | Condition |
|---|---|
| `fully_paid` | `close_balance` == 0 and invoice fully settled |
| `pending_payment` | Payment scheduled but not yet executed |
| `open_receipt_variance` | Receipt quantity/amount mismatch |
| `awaiting_inspection` | Inspection hold blocking payment |

**Calculations:**
- `prior_paid_amount` = payments already executed through review date
- `scheduled_payments` = payments scheduled through 2026-06-30 (or applicable close date)
- `close_balance` = `invoice_total` − `prior_paid_amount` − `scheduled_payments`

**Rule:** Any payment already scheduled in ProcureOps through the close horizon reduces the close balance for that supplier.

### 4.5 Change Memo Analysis (`change_analysis`)

One entry per PO line changed:

| `change_reason_code` | Condition |
|---|---|
| `price_change` | Unit cost changed, quantity unchanged |
| `quantity_increase` | `revised_order_qty` > `original_order_qty` |
| `quantity_decrease` | `revised_order_qty` < `original_order_qty` |
| `line_cancellation` | Line removed (revised qty = 0 or absent) |
| `new_line` | Line not in original PO |

**Calculations:**
- `net_change_qty` = `revised_order_qty` − `original_order_qty`
- `net_change_amount_usd` = `net_change_qty` × `unit_cost` (use current unit cost for the line)

---

## 5. Common Pitfalls

1. **Forgetting to sort ID lists.** All `po_ids`, `receipt_ids`, `invoice_ids`, and similar arrays must be in ascending lexicographic order.
2. **Mixing authoritative vs. supporting sources.** Do not list `local_change_memo` as authoritative; ProcureOps records always take precedence for factual data.
3. **Rounding errors.** All USD amounts must be rounded to exactly two decimal cents before summing into totals.
4. **PO-73xx confusion.** Do not query the API for `PO-73xx` receipts; use the mapped shared IDs provided in the local packet.
5. **Missing receipt handling.** If a receipt ID is referenced in a memo but does not exist in ProcureOps, set `resolution_status: "missing_receipt"` and `decision: "hold_missing_receipt"`.
6. **Chargeback amount calculation.** Use `basis_quantity × unit_cost` from the chargeback register excerpt; do not recalculate from ProcureOps PO unit costs unless the register is absent.
7. **Close slice scope.** AP close tasks are scoped to the listed invoices only; treat all other supplier activity as out of slice.
8. **Template divergence.** Each task type has a slightly different top-level key (`nomination_decisions`, `release_decisions`, `close_records`, `change_analysis`). Match the template exactly.

---

## 6. Summary Checklist

Before returning JSON, verify:
- [ ] `task_id` matches the current task directory name.
- [ ] `review_as_of` is populated from the prompt/packet (not today's date unless specified).
- [ ] All ID lists are sorted ascending.
- [ ] All currency values are numbers with two decimal places.
- [ ] `authoritative_sources` and `supporting_only_sources` are correctly partitioned.
- [ ] Totals in `summary` match the sum of their constituent line items.
- [ ] `followup_actions` are drawn only from the allowed enum values in the template.
- [ ] No extra keys or narrative text outside the JSON object.
