# ProcureOps Exception Review Skill

## Overview
Tasks in this group require querying a local ProcureOps API and synthesizing structured JSON exception-review files. There are multiple review types (nomination, receiving inspection, AP close, change exception, AP release). Each task provides an `input/payloads/answer_template.json` that dictates the required output schema. Always read the template and the prompt first to determine which review type is needed.

## Initial Setup
1. Read `input/prompt.txt` to identify the review type and target program/PO/receipt/invoice.
2. Read `input/payloads/answer_template.json` to know the exact output schema, required keys, sort orders, and precision rules.
3. Read any memo/packet/JSON payload files in `input/payloads/` for task-specific parameters (target IDs, chargeback registers, change details, etc.).

## ProcureOps API Conventions
- Base URL: `http://127.0.0.1:8006`
- Endpoints are RESTful and return JSON.
- Common resource paths (try plural first, then singular):
  - `/programs` or `/programs/{program_id}`
  - `/po` or `/po/{po_id}` or `/pos/{po_id}`
  - `/suppliers` or `/suppliers/{supplier_id}`
  - `/contracts` or `/contracts/{contract_id}` — also used for SKU lookups
  - `/receipts` or `/receipts/{receipt_id}`
  - `/ap` or `/ap/{invoice_id}` or `/invoices/{invoice_id}`
  - `/warehouses` or `/warehouse/{warehouse_id}`
  - `/suppliers/{supplier_id}/risk`
- When an exact ID is unknown, list the collection and filter locally by `program_id`, `po_id`, `supplier_id`, etc.
- Record **every** unique ID fetched from the API in `evidence.endpoint_record_ids` (or the task-specific evidence field).
- Record **every** payload file read in `evidence.task_payloads_reviewed`.

## Data Model Relationships
- **Program** (`PRG-*`) owns multiple **POs** (`PO-*`).
- **PO** has lines, each with a `sku` and `ordered_qty`.
- **SKU** is linked to a **Contract** (`CON-*`) and a **Supplier** (`SUP-*`).
- **Receipt** (`RCV-*`) references a PO and records `received_qty` per line.
- **Invoice** (`AP-*`) references a PO and a supplier; has `billed_qty`, `invoice_subtotal`, `freight`, `tax`.
- **Supplier** has a `risk_rating` (e.g., `watch`, `approved`) and may have open **risk events** (`VRE-*`).
- **Warehouse** (`WH-*`) is referenced by receipts.

## Calculation Rules (apply across review types)
- **Shortage**: `short_qty_vs_po = ordered_qty - received_qty`
- **Unreceived billed**: `unreceived_billed_qty = billed_qty - received_qty`
- **Completion ratio**: `receipt_completion_ratio = received_qty / ordered_qty` — round to 4 decimal places.
- **Received value**: `received_goods_value = received_qty * contract_unit_price`
- **Unreceived value**: `unreceived_goods_value = short_qty_vs_po * contract_unit_price`
- **Invoice total**: `invoice_total = invoice_subtotal + invoice_freight + invoice_tax` — round to 2 decimals.
- **Quantity variance**: `quantity_variance = quantity_billed - quantity_received` — round to 2 decimals.
- **Variance percent**: `quantity_variance_pct = (quantity_variance / ordered_qty) * 100` — round to 1 decimal.
- **Net release**: `net_release_amount = invoice_total - approved_chargeback_amount` — round to 2 decimals.
- **Close balance**: `close_balance = opening_balance + invoice_total - scheduled_payments` — round to 2 decimals.
- **Net balance impact**: `net_balance_impact = invoice_total - scheduled_payment_amount` — round to 2 decimals.
- **Unpaid balance**: `unpaid_balance = total_invoice_amount - paid_amount` — round to 2 decimals.
- **Overdue percent**: `overdue_pct = (overdue_invoice_amount / total_unpaid_amount) * 100` — round to 2 decimals.
- **Total contract value**: `sum(unit_price * estimated_qty)` for all contract lines — round to 2 decimals.

## Review-Type-Specific Guidance

### 1. Nomination Review
- Purpose: Evaluate whether nominated suppliers for a program are ready for committee approval.
- Key inputs: nomination memo (lists program, SKUs, suppliers, POs).
- Fetch: program, all POs for the program, suppliers, contracts for each SKU, supplier risk data, receipt and invoice status.
- For each SKU line:
  - `readiness_status` is `ready` if no blockers; `at_risk` if conditional; `not_ready` if blocked.
  - `blocker_codes` (sorted): derive from missing contracts, supplier watch status, open risk events, AP holds, pending receipts, late due dates. Use `none` only when truly empty.
  - `nomination_decision`: `nominate` if ready, `conditional_nomination` if at risk, `hold` if not ready.
  - `package_po_ids` and `receipt_evidence_ids` and `invoice_exception_ids` must be sorted ascending.
- `committee_action`:
  - Group suppliers by their worst nomination_decision across SKUs.
  - `send_to_committee` is usually `yes` if any supplier is nominated.
  - `next_owner` depends on where blockers reside (`buyer`, `finance_ops`, `quality_ops`, `program_owner`, `ap_team`).

### 2. Receiving Inspection Review
- Purpose: Reconcile a single receipt against its PO and invoice.
- Key inputs: receiving memo (lists batch_id, PO, receipt, invoice, receiver, packing slip).
- Fetch: receipt record, PO record, invoice record, contract/SKU record, supplier record, supplier risk.
- `line_reconciliation`: one entry per PO line, sorted by `po_line_id` ascending.
  - `contract_price_match`: true if `po_unit_price == contract_unit_price == invoice_unit_price`.
- `invoice_review.exception_codes` (evaluator sorts these):
  - `INVOICE_QTY_EXCEEDS_RECEIPT` when `billed_qty > received_qty`.
  - `PARTIAL_RECEIPT` when receipt is incomplete.
  - `SUPPLIER_WATCH_RISK` when supplier has `watch` rating or open risk.
  - `PRICE_MISMATCH` when unit prices differ.
  - `DAMAGE_REJECTION` when `rejected_qty > 0`.
  - `NO_EXCEPTION` only when none of the above apply.
- `decision`:
  - `batch_disposition`: `accept_partial_hold_variance` when shortage exists and invoice is on hold; `release_full_invoice` when exact match; `manual_recount_required` when data is ambiguous.
  - `ap_action`: `keep_invoice_on_hold` when variance exists; `release_invoice` when matched.
  - `receiving_action`: `record_shortage_follow_up` when `short_qty_vs_po > 0`.
  - `supplier_action`: `request_credit_or_remaining_delivery` when shortage exists.

### 3. AP Close Review
- Purpose: Generate an AP close summary for a program, deciding which invoices to hold or release.
- Key inputs: AP close memo (lists program, close date, invoices).
- Fetch: all invoices for the program, PO records, receipt records, supplier records.
- `invoice_decisions` (sorted by `invoice_id` ascending):
  - `hold_decision`: `HOLD` if any reason code applies; `RELEASE` for clean three-way matches.
  - `release_to_payment`: true only for clean releases.
  - `reason_codes` (alphabetical): `NO_RECEIPT` when no receipt exists; `QTY_VARIANCE` when billed ≠ received; `SCHEDULED_PAYMENT_FOUND` when a scheduled payment exists; `APPROVED_THREE_WAY_MATCH` when all clear.
  - `quantity_received`: use `0.00` when no receipt exists.
- `vendor_balances` (sorted by `supplier_id` ascending):
  - Aggregate invoices per supplier.
  - `held_invoice_total`: sum of invoices with `hold_decision == HOLD`.
  - `releasable_invoice_total`: sum of invoices with `hold_decision == RELEASE`.
  - `balance_status`: `OPEN_HELD` if held invoices remain; `OPEN_APPROVED` if only releasable remain; `FULLY_SCHEDULED` if fully paid/scheduled.
- `program_summary` (sorted by `program_id` ascending): one row per program, aggregating invoice counts and totals.
- `payment_hold_queue` / `payment_release_queue`: lists of `invoice_id`, each sorted ascending.
- `total_close_balance`: sum of all `close_balance` values across vendors, rounded to 2 decimals.

### 4. Change Exception Review
- Purpose: Evaluate impact of a proposed contract change.
- Key inputs: change memo JSON (includes change type, effective date, affected SKUs, new prices/quantities).
- Fetch: program, POs, suppliers, contracts for affected SKUs, supplier risk.
- `change_impact_description`: copy or paraphrase from memo.
- `requested_change_date`: from memo.
- `price_impact`: fetch from contract endpoint for the affected SKU.
- `supplier_risk_rating` and `watch_list_status` and `open_risk_event_ids`: from supplier risk endpoint.
- `has_open_risk_events`: true if `open_risk_event_ids` is non-empty.
- `affected_skus`: list from contract endpoint; each entry needs `sku`, `contract_id`, `effective_date`, `price_impact`.
- `recommendation`:
  - `approve_with_monitoring` when risk is low.
  - `escalate_to_risk_committee` when supplier is on watch or has open risk events.
  - `reject_change` when impact is severe.
- `overall_impact`: `low`, `medium`, or `high` based on price delta and risk.

### 5. AP Release Review
- Purpose: Multi-invoice release decision using a chargeback register.
- Key inputs: `ap_release_packet.json` (includes target POs, receipts, invoices, chargeback register, and a `po73xx_alias_note` mapping stale PO-73xx IDs to real PO IDs).
- **Important**: The `po73xx_alias_note` maps legacy PO-73xx identifiers to actual PO IDs. Use the mapped IDs when querying the API.
- Fetch: all invoices, POs, receipts in the packet, plus any additional receipts linked to those POs (to populate `excluded_same_po_receipt_ids`).
- `release_decisions` (one per invoice):
  - Match invoice to its PO and receipts via the packet or API.
  - `receipt_ids_in_scope`: receipts explicitly tied to this invoice in the packet.
  - `excluded_same_po_receipt_ids`: other receipts on the same PO not tied to this invoice.
  - `decision`:
    - `release_net_after_approved_chargeback` when chargeback is approved and receipt exists.
    - `hold_pending_quality_chargeback` when chargeback is pending and quality-related.
    - `hold_missing_receipt` when no receipt exists for the PO.
  - `primary_reason`: mirror the decision (`approved_ap_quantity_variance`, `approved_qty_chargeback`, `inspection_hold_pending_chargeback`, `no_receipt_on_po`).
  - `approved_chargeback_amount` and `pending_chargeback_amount` from chargeback register.
  - `net_release_amount = invoice_total - approved_chargeback_amount`.
- `receiving_exceptions` (one per receipt, plus a `MISSING:{po_id}` entry for POs with no receipt):
  - `exception_codes`: from receipt or chargeback data (e.g., `Inspection Hold`, `Severe Unmatched Quantity`, `Underage Quantity`, `AP Quantity Variance`).
  - `chargeback_status`: `approved`, `pending_quality_review`, or `not_applicable`.
  - `resolution_status`: `net_release_ready`, `hold_for_quality_review`, `missing_receipt`.
- `summary`:
  - `release_invoice_ids` and `hold_invoice_ids` sorted ascending.
  - `approved_chargeback_total`, `pending_chargeback_total`, `net_release_total` — all rounded to 2 decimals.
  - `authoritative_sources`: include `local_chargeback_register`, `procureops_ap_records`, `procureops_po_records`, `procureops_receipt_records`.
  - `supporting_only_sources`: include `ap_release_request_note`, `stale_po73xx_alias_note` when present.
  - `followup_actions`: derive from edge cases (missing receipts, pending quality reviews, duplicate receipts).

## Common Pitfalls
- **Sorting**: Many arrays must be sorted ascending. The evaluator sorts some fields itself (e.g., exception codes, endpoint IDs), but others must be pre-sorted (e.g., PO IDs, invoice IDs, SKUs). Check the template comments carefully.
- **Rounding**: Use standard rounding (round half up) to the specified decimal places. Currency = 2 decimals, ratios = 4 decimals, percentages = 1 or 2 decimals as specified.
- **Nulls vs. zero**: Distinguish between `null` and `0.00`. For example, `quantity_received` is `0.00` when no receipt exists, not `null`.
- **Supplier risk**: Always fetch `/suppliers/{id}/risk`. A supplier may have a `watch` rating even when its base record looks clean. Open risk events (`VRE-*`) affect nomination and release decisions.
- **Three-way match**: For AP decisions, the three-way match compares PO qty → receipt qty → invoice billed qty. If any differ, it is a variance.
- **Evidence completeness**: Missing an `endpoint_record_id` or `task_payloads_reviewed` entry can cause validation failures. Include every API ID and every file read.
- **Alias notes**: In AP release tasks, legacy PO-73xx aliases in memos/packets must be resolved to real PO IDs before querying the API.
- **PO status**: A PO can be `partial_receipt` even when a receipt is fully accepted, if ordered > received.
- **Invoice hold codes**: Common codes include `QTY_VARIANCE`, `PRICE_MISMATCH`, `INSPECTION_HOLD`. Use the exact code from the API record when available.

## Execution Order
1. Parse prompt and payload files.
2. Resolve any ID aliases (e.g., PO-73xx → real PO ID).
3. Query the API for the primary records (program, PO, receipt, invoice, supplier).
4. Query related records (contracts, risk events, other POs/receipts on same supplier).
5. Perform all calculations using the formulas above.
6. Populate the answer template, ensuring correct sorting, rounding, and enum values.
7. Validate that every required key from the template is present.
8. Write the final JSON to the required output path.
