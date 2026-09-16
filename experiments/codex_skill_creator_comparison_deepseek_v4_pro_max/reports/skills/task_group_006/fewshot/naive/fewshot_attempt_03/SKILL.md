---
name: procureops-solver
description: Solve ProcureOps procurement reconciliation tasks by reading the supplied payloads, fetching live API records, cross-referencing across endpoints, applying business rules, and returning template-conformant JSON.
---

# ProcureOps Reconciliation Skill

## Overview

This skill handles procurement operations tasks that require reconciliation across a ProcureOps API and local task payloads. Every task follows the same pattern: consume a local memo or packet naming target entities, fetch live records from a shared ProcureOps API at `<TASK_ENV_BASE_URL>`, cross-reference those records across multiple endpoints, apply standard business rules, and return a single JSON object that exactly conforms to an answer template supplied in the payloads directory.

## API Access

All tasks use the same ProcureOps API. The base URL is always provided as `<TASK_ENV_BASE_URL>` by the runner. Authentication is none. Use only GET requests.

**Allowed endpoints** (every endpoint is read-only):

| Endpoint             | Description                              |
|----------------------|------------------------------------------|
| `/health`            | Health check                             |
| `/manifest`          | Available record IDs and endpoint map    |
| `/suppliers`         | Supplier master data                     |
| `/items`             | Item/SKU catalog                         |
| `/programs`          | Program metadata and ownership           |
| `/contracts`         | Contract terms, ceilings, status         |
| `/purchase_requisitions` | Requisition records                   |
| `/purchase_orders`   | Purchase order headers and lines         |
| `/receipts`          | Receiving records                        |
| `/ap/invoices`       | AP invoice headers and lines             |
| `/ap/payments`       | Scheduled and completed payments         |
| `/approvals`         | Approval events and statuses             |
| `/budget_snapshots`  | Program budget snapshots                 |
| `/vendor_risk_events`| Supplier risk events                     |

All endpoints return JSON arrays of records. Use the `/manifest` endpoint on first contact to confirm available record IDs and understand the data shape before heavy fetching.

**Fetching strategy:** Query endpoints that match the scope of the task memo. Start with the manifest to see which IDs are live, then fetch the specific collections needed. Use shell tools (`curl`, `jq`) to retrieve and parse records. Avoid fetching every endpoint when the task memo narrows the scope.

## General Workflow

Follow this sequence for every task:

1. **Read the local payloads.** Locate the answer template JSON in `input/payloads/` and read every field, type constraint, allowed value, ordering rule, and required key. The template is the contract; the output must pass every constraint it declares. Also read the memo or packet file that names the target entities (POs, invoices, receipts, SKUs, programs, suppliers).

2. **Fetch API records.** Query endpoints relevant to the named targets. Start with the endpoint that matches the primary entity (e.g., `purchase_orders` for PO-heavy tasks, `ap/invoices` for AP tasks) and expand outward to related endpoints. Fetch the manifest first to confirm which IDs exist.

3. **Cross-reference records.** Join records across endpoints using shared identifiers: `po_id`, `invoice_id`, `receipt_id`, `supplier_id`, `program_id`, `contract_id`, `sku`, `requisition_id`. Treat the API as the system of record; the local memo may be stale or incomplete.

4. **Apply business rules.** Use the standard rules documented below. Do not invent rules not supported by the API data.

5. **Build the answer.** Populate the JSON template field by field. Validate every constraint declared in the template (types, allowed values, ordering, precision, required keys) before finalizing.

6. **Include evidence.** Record every API endpoint ID and local payload path that contributed to the answer in an `evidence` or `supporting_ids` section as the template requires.

## Answer Template Discipline

The answer template in the payloads directory is the authoritative schema. Treat it literally:

- **Required keys:** Every key listed under `required_top_level_keys`, `required_keys`, or equivalent must be present in the output. If a template uses a generic field like `type` alongside `required_value`, the output must match the declared requirement.

- **Allowed values:** When the template lists `allowed_values` or `allowed` arrays, the output must pick only from those values. Do not invent new values.

- **Types and precision:** Honor declared types (`number`, `string`, `boolean`, `integer`). For currency fields, round to two decimal places (`round to cents`). For ratios, use four decimal places (`precision 4`). For percentages, use one decimal place (`precision 1`).

- **List ordering:** When the template says `sort ascending` or `sort by X ascending`, sort the list. When it says `set; evaluator sorts values` or `ordering: set`, treat the list as a set (no duplicates, order does not matter). When a field type is described as `list of string` with no explicit sort instruction, the evaluator generally treats it as a set.

- **Null vs absent:** Use `null` only when a template explicitly marks a field as `string|null` or equivalent. Otherwise, default to empty arrays (`[]`) for list fields and `0.0` for numeric fields that have no data.

- **Dates:** Use `YYYY-MM-DD` format. The `as_of_date` in the task prompt is the cutoff; exclude records dated after that date unless the template specifies a different bound.

## Common Business Rules

Refer to [business_rules.md](business_rules.md) for detailed formulas, exception codes, and decision logic for each operation type: sourcing nomination, receiving closeout, AP close, change control, and AP release.

### Three-Way Match (PO vs Receipt vs Invoice)

Compare purchase order line quantities and unit prices against receipt quantities and invoice billed quantities/unit prices:

- **Quantity match:** `ordered_qty` from PO, `received_qty` from receipt, `billed_qty` from invoice. Compute `short_qty_vs_po = ordered_qty - received_qty` and `unreceived_billed_qty = billed_qty - received_qty` (or `0` when the difference is negative).

- **Price match:** Compare `po_unit_price` against `contract_unit_price` and `invoice_unit_price`. A mismatch is `contract_price_match: false`.

- **Receipt completion ratio:** `received_qty / ordered_qty`, rounded to 4 decimal places.

- **Exception codes for three-way problems:**
  - `INVOICE_QTY_EXCEEDS_RECEIPT` when billed_qty > received_qty
  - `PARTIAL_RECEIPT` when received_qty < ordered_qty
  - `PRICE_MISMATCH` when contract_price_match is false
  - `DAMAGE_REJECTION` when rejected_qty > 0
  - `NO_EXCEPTION` when everything matches

### Financials Calculation

- **Received goods value:** `received_qty * contract_unit_price`, summed across all lines.
- **Unreceived goods value:** `(ordered_qty - received_qty) * contract_unit_price`, summed.
- **Invoice totals:** Sum invoice lines to get `invoice_subtotal`, add `invoice_freight` and `invoice_tax` from the invoice record to produce `invoice_total`.

### Contract Ceiling Check

When a task needs to verify whether a change fits under a contract ceiling:

- Sum the subtotals of all purchase orders on the contract that are **not** cancelled. Do not count cancelled POs against the ceiling.
- `headroom_before_change = ceiling_amount - noncancelled_subtotal`
- `requested_subtotal = requested_quantity * unit_price`
- `headroom_after_change = headroom_before_change - requested_subtotal`
- `ceiling_ok = headroom_after_change >= 0`

### Program Budget Check

- Fetch the budget snapshot for the program. Use `budget_cap` and `committed_amount`.
- `remaining_budget = budget_cap - committed_amount`
- For a requested change: compute `requested_tax = requested_subtotal * (tax_rate_percent / 100)`, `requested_total = requested_subtotal + requested_tax` (add freight only when the local memo explicitly provides freight).
- `budget_after_change = remaining_budget - requested_total`
- `budget_ok = budget_after_change >= 0`
- `max_quantity_with_current_budget = floor(remaining_budget / (unit_price * (1 + tax_rate_percent / 100)))`

### Approval Check

- Fetch the latest approval event for the source requisition from the `/approvals` endpoint. Sort by event date descending and take the top event.
- If the latest action is in the `approval_good_actions` list (e.g., `approved`), the approval is OK. Any other action (e.g., `submitted`) means `approval_ok: false`.

### Supplier Risk Check

- Fetch `/vendor_risk_events` for the supplier. Filter for events where the status indicates open or monitoring.
- `supplier_risk_ok` is `false` only when at least one severe open event exists (check the event's `severity` field). A `watch` rating alone without a severe open event does not block.
- Include open event IDs in the output even when they are not severe.

### AP Hold/Release Logic

For invoice-level decisions:

- **RELEASE** when a matching receipt exists, quantities align, and a matching payment is scheduled. Reason codes: `APPROVED_THREE_WAY_MATCH`, `SCHEDULED_PAYMENT_FOUND`.
- **HOLD** when no receipt exists for the PO (`NO_RECEIPT`), or when billed quantity exceeds received quantity (`QTY_VARIANCE`).
- `release_to_payment` is `true` only when the decision is `RELEASE`.
- `quantity_variance = quantity_billed - quantity_received`
- `quantity_variance_pct = (quantity_variance / po_ordered_qty) * 100`, rounded to one decimal.

### Vendor Balance Reconciliation

- `opening_balance` is provided in the task prompt or memo. Default to `0.00` when the prompt says so.
- `close_balance = opening_balance + invoice_total - scheduled_payments`
- `releasable_invoice_total`: sum of invoice totals with `hold_decision: RELEASE`.
- `held_invoice_total`: sum of invoice totals with `hold_decision: HOLD`.
- `balance_status`:
  - `FULLY_SCHEDULED` when `close_balance == 0` and all invoices are released.
  - `OPEN_APPROVED` when `close_balance > 0` and all invoices are released.
  - `OPEN_HELD` when at least one invoice is held.

### Chargeback Netting

When the task provides a local chargeback register:

- An approved chargeback reduces the net release amount: `net_release_amount = invoice_total - approved_chargeback_amount`.
- A pending chargeback blocks release; `net_release_amount` stays `0.0` and the invoice is held.
- When the chargeback register covers a quantity variance on a receipt that exists, the invoice can be released net of the chargeback.

### Receipt Existence and Deduplication

- Query all receipts for a given `po_id`. If zero receipts exist, the receipt is missing and the invoice should be held with `hold_missing_receipt`.
- When a receipt exists on a PO but a separate invoice references a different receipt on the same PO, exclude the non-matching receipt from scope and note it in `excluded_same_po_receipt_ids`.
- If a local packet notes that an expected receipt ID (like a `PO-73xx` family) is absent from the shared environment, do not fabricate it. Report the missing receipt.

### Blocker and Exception Codification

Always return controlled codes rather than narrative text:

- **Sourcing nomination blockers:** `missing_contract`, `supplier_watch`, `open_supplier_risk`, `ap_hold`, `pending_receipt`, `late_due_date`, `none`.
- **Invoice exception codes:** `INVOICE_QTY_EXCEEDS_RECEIPT`, `PARTIAL_RECEIPT`, `SUPPLIER_WATCH_RISK`, `PRICE_MISMATCH`, `DAMAGE_REJECTION`, `NO_EXCEPTION`.
- **AP reason codes:** `APPROVED_THREE_WAY_MATCH`, `NO_RECEIPT`, `QTY_VARIANCE`, `SCHEDULED_PAYMENT_FOUND`.
- **Change-control required actions:** `obtain_final_requisition_approval`, `raise_budget_exception_or_reduce_quantity`, `resolve_supplier_risk_hold`, `none`.
- **Receiving exception codes:** `Underage Quantity`, `Severe Unmatched Quantity`, `Inspection Hold`, `AP Quantity Variance`.

### Decision Composition

When multiple checks fail, combine them into the appropriate compound decision:

- For change control: `hold_for_budget`, `hold_for_approval`, `hold_for_supplier_risk` each independently. When both budget and approval fail, use `hold_for_budget_and_approval`. When contract ceiling fails, use `reject_contract_mismatch`.
- For sourcing: individual lines get `nominate` (ready), `conditional_nomination` (at_risk), or `hold` (not_ready) based on their blocker list.

## Edge Cases and Conventions

- **Records dated after `as_of_date`:** Exclude them. The cutoff is date-inclusive on the `as_of_date`.
- **Cancelled purchase orders:** Exclude from contract ceiling subtotals and from included PO lists. List them separately in `excluded_cancelled_po_ids`.
- **Multiple receipts on one PO:** Include only the receipt named in the task memo or chargeback register. List other receipts on the same PO in `excluded_same_po_receipt_ids`.
- **Zero records in a collection:** Return `[]` for list fields, not `null`. Return `0.0` for numeric aggregated fields.
- **Unknown supplier names:** Look up the supplier name from `/suppliers` using the `supplier_id`. Do not guess.
- **Invoice status from API:** Use the `status` field from the API invoice record verbatim (e.g., `approved`, `on_hold`, `pending_receipt`). Do not reinterpret.
- **Program IDs:** Always use the exact `program_id` string from the API, not a derived or shortened form.

## Query Patterns

Use `curl -s` with `jq` for API access. Common patterns:

```bash
# Fetch manifest first
curl -s "<TASK_ENV_BASE_URL>/manifest" | jq .

# Fetch a specific collection
curl -s "<TASK_ENV_BASE_URL>/purchase_orders" | jq .

# Filter by program
curl -s "<TASK_ENV_BASE_URL>/purchase_orders" | jq '[.[] | select(.program_id == "PRG-TARGET")]'

# Find receipts for a PO
curl -s "<TASK_ENV_BASE_URL>/receipts" | jq '[.[] | select(.po_id == "PO-TARGET-XXXX")]'

# Check for scheduled payments for an invoice through a date
curl -s "<TASK_ENV_BASE_URL>/ap/payments" | jq '[.[] | select(.invoice_id == "AP-TARGET-XXXX" and .scheduled_date <= "YYYY-MM-DD")]'
```

Always pipe through `jq` to extract the exact fields needed rather than dumping full records into the answer. Use `jq` arithmetic for sums and computations when possible.

## Output Discipline

Return **only** the JSON object. No markdown fences, no prose explanations, no trailing text. The template is the schema; the matching is exact. If a template declares `"type": "object"` and `"required_top_level_keys"`, every one of those keys must be present at the top level of the output.

When the template uses a `description` field alongside required keys, the description is guidance, not a field to populate. Populate only the keys listed under `required_top_level_keys` or equivalent.

## Sanity Check Before Returning

Before finalizing, verify:

- Every required key from the template is present.
- Every numeric field is rounded to the declared precision.
- Every list respects the declared ordering rule.
- Every enum field contains a value from the declared allowed set.
- Source record IDs are traced in evidence/supporting_ids.
- The output is pure JSON with no surrounding text.
