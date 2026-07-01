---
name: task-group-006-fewshot-attempt-03
description: Solve ProcureOps procurement, receiving, AP close, change-control, and release-decision tasks that provide local input payloads plus a shared ProcureOps API, returning strict JSON matching the task answer template.
---

# ProcureOps JSON Answer Skill

Use this skill for task-group prompts that ask for a JSON answer from local payload files and the ProcureOps API. The local payload names the target records and sometimes adds business controls; the API is normally the source of truth for operational records.

## Core Workflow

1. Read the prompt, every file under the task's `input/payloads/`, and the answer template.
2. Query the ProcureOps service. Use the base URL from the prompt/runner, commonly `<environment_base_url>`. If localhost curl uses a proxy, call it as `curl --noproxy '*' -sS "$BASE/<endpoint>"`.
3. Extract only records in scope:
   - IDs explicitly named in the prompt or local payload.
   - Records linked to those IDs by `po_id`, `receipt_id`, `invoice_id`, `supplier_id`, `program_id`, `contract_id`, `requisition_id`, or `sku`.
   - For slice/close tasks, do not include unrelated records just because they share a supplier or program unless the template asks for aggregated context.
4. Derive fields and controlled decisions from the template wording. Return only one JSON object. Do not include prose.
5. Sort all ID lists ascending unless the template says otherwise. Treat set fields as de-duplicated. Round USD amounts to cents; use requested quantity precision for quantities and percentages.

## API Map

The API root returns endpoint names. Common endpoints and key fields:

- `/programs`: `program_id`, `owner`, `budget_cap`, `committed_amount`, `status`, `priority`.
- `/budget_snapshots`: `snapshot_id`, `program_id`, `snapshot_date`, `budget_cap`, `committed_amount`, `pending_invoice_amount`, `currency`.
- `/suppliers`: `supplier_id`, `name`, `status`, `risk_rating`, `payment_terms`, `region`.
- `/items`: `sku`, `description`, `preferred_supplier_id`, `standard_cost`, `uom`, `active`.
- `/contracts`: `contract_id`, `program_id`, `sku`, `supplier_id`, `status`, `price_type`, `unit_price`, `ceiling_amount`, dates.
- `/purchase_requisitions`: `requisition_id`, `program_id`, `sku`, `quantity`, `need_by`, `status`, `priority`, `requester`.
- `/approval_events`: `event_id`, `object_type`, `object_id`, `action`, `actor`, `event_date`, `note_code`.
- `/purchase_orders`: `po_id`, `program_id`, `supplier_id`, `contract_id`, `requisition_id`, `status`, `due_date`, `subtotal`, `tax`, `total`, `lines[]`.
- `/receipts`: `receipt_id`, `po_id`, `supplier_id`, `status`, `receipt_date`, `warehouse_id`, `packing_slip`, `receiver`, `lines[]`.
- `/ap_invoices`: `invoice_id`, `po_id`, `receipt_id`, `supplier_id`, `status`, `hold_code`, `invoice_date`, `subtotal`, `freight`, `tax`, `total`, `lines[]`.
- `/payments`: `payment_id`, `invoice_id`, `supplier_id`, `amount`, `scheduled_date`, `status`.
- `/vendor_risk_events`: `event_id`, `supplier_id`, `related_object_id`, `event_type`, `severity`, `status`, `event_date`.

Nested PO lines use `line_id`, `sku`, `quantity`, `unit_price`. Receipt lines use `po_line_id`, `sku`, `quantity_received`, `quantity_rejected`, `inspection_status`. Invoice lines use `po_line_id`, `sku`, `quantity_billed`, `unit_price`.

## General Derivations

- Program budget headroom or remaining budget: `budget_cap - committed_amount`, preferably from `/budget_snapshots` when a snapshot field is requested; otherwise `/programs` is equivalent in the examples.
- Latest approval event: filter `approval_events` by `object_id` and choose max `event_date`; if tied, use stable ID ordering. Approval is OK only when the latest action is one of the prompt's good actions, usually `approved`.
- Open supplier risk: supplier events with `status` in `open` or `monitoring` and `event_date` on or before the review/as-of date when one is provided. Severe open events are normally open/monitoring events with `severity == "high"`.
- Supplier watch context: `supplier.risk_rating == "watch"`. Treat it as contextual unless the template says it is a blocker; open severe events are blockers in change-control tasks.
- Contract match: match by `contract_id` when supplied, otherwise by same `program_id`, `sku`, and `supplier_id` with active status. Missing/null contract on a PO is a missing-contract blocker.
- Receipt quantity for a PO line: sum in-scope receipt line `quantity_received` for matching `po_id` and `po_line_id`/`sku`. For a specific batch, use only that receipt.
- Billed quantity: sum target invoice line `quantity_billed` for matching `po_line_id`/`sku`.
- Received goods value: accepted received quantity times PO unit price. Unreceived value: max(`billed_qty - received_qty`, 0) times PO unit price unless the template supplies chargeback unit cost.
- Invoice total usually equals `subtotal + freight + tax`; prefer API `total` if present.

## Nomination Readiness Packets

Use local memo anchors to identify package SKUs, primary requisitions, and package POs. For each SKU:

- Selected supplier is the package PO supplier.
- Commercial basis is the PO `contract_id`, or `null` if absent.
- Receipt evidence IDs are receipts for the package PO on or before the as-of date.
- Invoice exception IDs are target PO invoices on or before the as-of date with a non-null `hold_code` or non-release status such as `on_hold`/`pending_receipt`.
- Risk event IDs are supplier-level open or monitoring risk events on or before the as-of date.
- Blockers:
  - `missing_contract`: package PO has no contract.
  - `supplier_watch`: supplier risk rating is `watch`.
  - `open_supplier_risk`: any open/monitoring supplier risk event.
  - `ap_hold`: any AP invoice exception not already better represented by pending receipt.
  - `pending_receipt`: no receipt evidence, or invoice/PO state indicates pending receipt.
  - `late_due_date`: PO due date is later than requisition `need_by`.
  - `none`: only when no other blockers apply.
- Line status/decision: no blockers means `ready`/`nominate`; blocking commercial or receiving issues such as missing contract, pending receipt, or late due date mean `not_ready`/`hold`; AP/risk/watch-only issues usually mean `at_risk`/`conditional_nomination`.
- Overall readiness is the worst line readiness. Committee queues are supplier IDs grouped by decision. `send_to_committee` is `yes` only when all lines can at least proceed under the template's criteria.

## Receiving Control Reviews

For a target receipt batch:

- Join receipt -> PO -> supplier -> contract -> invoice(s) tied to the receipt/PO.
- Sort reconciliation lines by `po_line_id`.
- `short_qty_vs_po = ordered_qty - received_qty`.
- `unreceived_billed_qty = max(billed_qty - received_qty, 0)`.
- `receipt_completion_ratio = received_qty / ordered_qty`, rounded as requested.
- `contract_price_match` compares PO unit price and contract unit price.
- Exception codes:
  - `INVOICE_QTY_EXCEEDS_RECEIPT` when billed exceeds received.
  - `PARTIAL_RECEIPT` when received is less than ordered or PO status is partial.
  - `SUPPLIER_WATCH_RISK` when supplier risk rating is watch or open risk exists and the template includes that code.
  - `PRICE_MISMATCH` when invoice, PO, and contract unit prices do not align.
  - `DAMAGE_REJECTION` when rejected quantity is positive or inspection indicates damage/rejection.
  - `NO_EXCEPTION` only when no other exception applies.
- Keep an invoice on hold for quantity variance, price mismatch, supplier hold, or pending receipt. Release only clean full matches.

## AP Close and Payment-Hold Reconciliation

For target invoice IDs only:

- Join invoice -> PO -> supplier -> receipts -> payments.
- Scheduled payment amount includes payments for that invoice with `status == "scheduled"` and `scheduled_date` on or before the task horizon. Do not count blocked payments; count released only if the prompt says released payments reduce the balance.
- Quantity received is the matching receipt quantity for the invoice receipt/PO; use `0.00` when no receipt exists.
- Quantity variance is billed minus received. Quantity variance percent is variance divided by PO ordered quantity times 100.
- Hold/release:
  - `RELEASE` when invoice is approved/clean, three-way match holds, and payment can be released.
  - `HOLD` when invoice status/hold code indicates `NO_RECEIPT`, `QTY_VARIANCE`, price variance, or other unresolved exception.
- Reason codes: `NO_RECEIPT`, `QTY_VARIANCE`, `APPROVED_THREE_WAY_MATCH`, `SCHEDULED_PAYMENT_FOUND`, sorted alphabetically.
- Vendor close balance starts from any local opening balance instruction, then `opening + target invoice total - counted scheduled payments`.
- Vendor balance status: `FULLY_SCHEDULED` when close balance is zero due to scheduled payments; `OPEN_HELD` when held target invoices remain; otherwise `OPEN_APPROVED`.
- Program summary totals are grouped over target invoices only.

## Change-Control Decisions

Use local change memo fields as the requested change, then verify against API records.

- Contract ceiling exposure is requested line subtotal before tax/freight: `requested_quantity * contract.unit_price`.
- Existing contract usage excludes cancelled POs. Sum non-cancelled PO subtotals for the same contract unless the template narrows scope.
- `headroom_before_change = ceiling_amount - noncancelled_subtotal`.
- `headroom_after_change = headroom_before_change - requested_subtotal`.
- Budget exposure follows the memo. In examples it is requested subtotal plus estimated tax; freight is included only if provided locally.
- `requested_tax = requested_subtotal * tax_rate_percent / 100`.
- `budget_after_change = remaining_budget - requested_total`.
- `max_quantity_with_current_budget = floor(remaining_budget / (unit_price * (1 + tax_rate)))` when tax is included.
- Approval OK depends on the latest approval event for the source requisition.
- Supplier risk OK is false for severe open/monitoring events or supplier hold status; watch rating alone can be context-only when the memo says so.
- Decision priority: contract mismatch -> `reject_contract_mismatch`; budget and approval blockers -> `hold_for_budget_and_approval`; single blockers -> corresponding hold; otherwise `release_amendment`.
- Required actions mirror blockers and use `none` only when no action is required.

## AP Release With Chargebacks

For release packets containing target POs, receipts, invoices, and a local chargeback register:

- Use target IDs from the local packet as scope. If the packet says aliases are stale or absent, use the concrete shared IDs listed in the packet.
- For each invoice, find target receipts in scope for its PO. Other API receipts for the same PO go in `excluded_same_po_receipt_ids`.
- Approved/pending chargeback amount is `basis_quantity * unit_cost`, grouped by invoice and chargeback status.
- Decisions:
  - `release_net_after_approved_chargeback` when an approved chargeback resolves the receiving/AP variance.
  - `hold_pending_quality_chargeback` when the chargeback is pending quality review or the receipt is on inspection hold.
  - `hold_missing_receipt` when no in-scope receipt exists for the PO.
- Primary reasons map to the chargeback/receipt condition: `approved_qty_chargeback`, `approved_ap_quantity_variance`, `inspection_hold_pending_chargeback`, or `no_receipt_on_po`.
- Net release amount is invoice total minus approved chargeback amount for released invoices, otherwise `0.00`.
- Receiving exception codes:
  - `Underage Quantity`: received quantity is less than PO ordered quantity.
  - `Severe Unmatched Quantity`: material shortfall; examples include large underage and 10% short receipt.
  - `Inspection Hold`: receipt status is `inspection_hold`.
  - `AP Quantity Variance`: invoice billed quantity exceeds receipt quantity while the PO receipt itself may be complete.
- Add a synthetic missing receipt row such as `MISSING:<po_id>` when the template expects receiving exceptions for a PO with no receipt.

## Final Checks

- Validate every required key from the answer template is present.
- Use exact controlled values from the template; do not invent enum strings.
- Ensure numeric rounding matches the template.
- Sort list rows by the template key, commonly invoice ID, supplier ID, program ID, PO line ID, SKU, or receipt ID.
- Return JSON only.
