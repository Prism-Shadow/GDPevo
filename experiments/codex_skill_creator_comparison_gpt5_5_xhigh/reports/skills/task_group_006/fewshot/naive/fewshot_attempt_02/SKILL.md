---
name: procureops-control-files
description: Solve ProcureOps business-control JSON tasks that require combining local packet or memo anchors with the shared read-only ProcureOps API for sourcing nomination readiness, receiving/AP reconciliation, payment hold/release closeout, contract amendment change control, supplier risk context, budget checks, and chargeback-based AP release files.
---

# ProcureOps Control Files

Use this skill for ProcureOps tasks that ask for a JSON control file from local payloads plus the ProcureOps API. Always produce only the JSON object requested by the task.

## Core Workflow

1. Read `input/prompt.txt`, every file under `input/payloads/`, and especially `answer_template.json`.
2. Treat the local memo or packet as the source for scope: target program IDs, invoice IDs, PO IDs, receipt IDs, requisitions, contracts, dates, tax rates, chargeback registers, and allowed output labels.
3. Treat the API as the source of truth for operational records: suppliers, items, programs, contracts, requisitions, purchase orders, receipts, invoices, payments, approvals, budgets, and vendor risk.
4. Fetch only needed read-only endpoints from `<TASK_ENV_BASE_URL>`. Endpoint responses use `{ "count": n, "results": [...] }`; index `results` by ID.
5. Join records by stable IDs first, then by PO, requisition, supplier, SKU, program, and dates. Do not trust a local narrative when it conflicts with an API record, except for local-only registers such as chargeback excerpts.
6. Apply the template exactly: required keys, enum labels, ordering, numeric precision, and whether list fields are sets.
7. Use date cutoffs from the task (`as_of`, `close_date`, `review_as_of`) when evaluating receipts, invoices, approvals, payments, budget snapshots, and risk events unless the template explicitly asks for current records.

## Endpoint Map

- `/suppliers`: `supplier_id`, `name`, `status`, `risk_rating`, payment terms.
- `/items`: `sku`, description, preferred supplier, standard cost, active flag.
- `/programs`: owner, budget cap, committed amount, status, priority.
- `/contracts`: `contract_id`, supplier, program, SKU, status, unit price, ceiling, price type.
- `/purchase_requisitions`: requisition status, program, SKU, quantity, need-by date.
- `/purchase_orders`: PO status, requisition, supplier, contract, program, due date, ship-to, currency, subtotal, tax, total, nested lines.
- `/receipts`: receipt status, date, PO, supplier, warehouse, packing slip, receiver, nested received/rejected lines.
- `/ap/invoices`: invoice status, hold code, PO, optional receipt ID, supplier, freight, tax, total, nested billed lines.
- `/ap/payments`: invoice, supplier, amount, status, scheduled date.
- `/approvals`: approval event history by `object_type` and `object_id`.
- `/budget_snapshots`: budget cap, committed amount, pending invoice amount by program and snapshot date.
- `/vendor_risk_events`: supplier, status, severity, event type, date, related object.

## Numeric Rules

- Round currency amounts to cents only for output. Keep intermediate arithmetic unrounded when possible.
- For percentages, use the precision requested by the template.
- `remaining_budget = budget_cap - committed_amount`.
- `close_balance = opening_balance + invoice_total - scheduled_payments`.
- `net_balance_impact = invoice_total - scheduled_payment_amount`.
- `requested_subtotal = requested_quantity * contract_unit_price`.
- `requested_tax = requested_subtotal * tax_rate_percent / 100`.
- `requested_total = requested_subtotal + requested_tax + explicit freight if the memo says freight applies`.
- `max_quantity_with_current_budget = floor(remaining_budget / per_unit_budget_exposure)`.
- `chargeback_amount = basis_quantity * unit_cost`.
- `net_release_amount = invoice_total - approved_chargeback_amount`, but use `0.00` when the invoice remains on hold.

## Sorting And Evidence

- Sort ID lists ascending unless the template says lists are sets or specifies another order.
- Sort line rows by the explicit key from the template, commonly SKU, invoice ID, PO line ID, supplier ID, or program ID.
- Include evidence IDs only for records actually used to derive fields. Include local payload names when the template asks for reviewed payloads.
- If no blockers or exceptions exist and the template allows a sentinel like `none` or `NO_EXCEPTION`, emit only that sentinel rather than an empty mixed list.

## Readiness And Sourcing Rules

For sourcing nomination packets:

- Identify package lines from local anchors, then verify each requisition, PO, supplier, SKU, and contract through the API.
- Use the selected supplier from the anchored PO when present; otherwise use the matched active contract supplier or preferred supplier only if the task permits.
- `commercial_basis_id` is the matched active contract for the line; use `null` when no active contract matches the supplier, SKU, and program.
- Receipt evidence is accepted receipt IDs for the package PO/SKU with `receipt_date <= as_of`.
- Invoice exceptions are AP invoices for the in-scope PO/SKU with `invoice_date <= as_of` and an active hold condition such as hold code, `on_hold`, or `pending_receipt`.
- Supplier risk IDs are open or monitoring vendor-risk events for the selected supplier as of the cutoff. Include severe/high events separately when the template asks.
- Use blocker codes from the template. Typical mappings:
  - missing active contract: `missing_contract`
  - supplier `risk_rating` watch/high: `supplier_watch`
  - open or monitoring supplier risk: `open_supplier_risk`
  - held or exception AP invoice: `ap_hold`
  - no accepted receipt evidence by cutoff: `pending_receipt`
  - PO due date later than the requisition need-by date: `late_due_date`
- Classify as ready only when no blockers remain. Classify as at risk for clearable AP or watch-risk conditions. Classify as not ready for missing contract, missing receipt, due-date lateness, severe supplier risk, or hard API status blockers.
- Committee queues follow the line decisions. Choose the next owner from the dominant blocker: AP holds to `ap_team`, budget to `finance_ops`, supplier quality/risk to `quality_ops`, missing contract or delivery timing to `buyer`, final business approval to `program_owner`.

## Receiving Reconciliation Rules

For receiving closeout or batch reviews:

- Use the target receipt/batch ID from the memo. Join receipt to PO, supplier, contract, and in-scope invoice.
- For each PO line, compute:
  - `short_qty_vs_po = ordered_qty - received_qty`
  - `unreceived_billed_qty = max(billed_qty - received_qty, 0)`
  - `receipt_completion_ratio = received_qty / ordered_qty`
  - received goods value from received quantity times the invoice or PO unit price requested by the template
  - unreceived goods exposure from unreceived billed quantity times the same unit price
- Compare invoice, PO, and contract unit prices. A contract price match requires the relevant unit prices to agree to cents.
- Exception code mappings:
  - billed quantity greater than received: invoice quantity exceeds receipt
  - PO short or partial status: partial receipt
  - supplier watch/high rating or active risk event: supplier watch/risk
  - unit price disagreement: price mismatch
  - rejected quantity or inspection variance: damage/rejection
- Keep the invoice on hold when quantity, price, receipt, inspection, or supplier-risk exceptions remain. Release only for a complete three-way match without active holds.

## AP Close And Vendor Balance Rules

For AP close slices:

- Target only the invoice IDs named by the local memo.
- Join each invoice to its PO, supplier, receipt evidence as of the close date, and payments.
- Quantity received should come from the invoice receipt when valid and within cutoff; otherwise aggregate receipts for the PO/SKU within cutoff. Use zero when no receipt exists.
- `quantity_variance = quantity_billed - quantity_received`.
- `quantity_variance_pct = quantity_variance / PO ordered quantity * 100`.
- Scheduled payment amount is the sum of non-blocked payments for the invoice within the memo's payment horizon. If the memo says "scheduled through" a date, include scheduled or released payments through that date and exclude blocked payments.
- Hold decisions:
  - `HOLD` for `on_hold`, `pending_receipt`, hold codes, no receipt, or positive quantity variance.
  - `RELEASE` for approved invoices with complete receipt coverage and no active hold.
- Reason codes should be controlled labels from the template, such as approved three-way match, no receipt, quantity variance, and scheduled payment found.
- Vendor balances group target invoices by supplier. Program summaries group target invoices by program. Release and hold queues are sorted invoice IDs.

## Change-Control Rules

For contract amendment or modular change requests:

- Verify the local request's program, contract, supplier, and SKU against the API. If the contract does not match the requested supplier/SKU/program, use the template's contract-mismatch rejection.
- Contract usage is the sum of non-cancelled PO subtotals for the contract unless the memo says otherwise. Exclude cancelled POs but list their IDs if requested.
- Contract headroom is ceiling minus non-cancelled usage before the change, then minus requested subtotal after the change. Contract ceiling exposure is before tax and freight unless specified otherwise.
- Use the budget snapshot matching the requested program and appropriate cutoff date. Budget exposure includes line subtotal plus estimated tax and explicit freight only when the memo says freight applies.
- Approval state comes from the latest approval event for the source requisition. `approval_ok` is true only if the latest action is in the memo's allowed good actions.
- Supplier risk is OK when the supplier is active and no open/monitoring severe event blocks release. A watch rating is context unless the memo or template makes it blocking.
- Decision priority: contract mismatch, then combined budget and approval hold, then budget hold, approval hold, supplier-risk hold, otherwise release amendment.
- Required actions mirror failed checks and use only enum values allowed by the template.

## AP Release And Chargeback Rules

For receiving/AP release packets:

- Use target IDs from the local packet for scope. If the packet says old aliases are unavailable, use the generated/shared IDs it names.
- API records remain authoritative for PO, receipt, and invoice totals/status. Local chargeback registers are authoritative for chargeback reason, basis quantity, unit cost, and approval status when those fields are not in the API.
- For each target invoice, join invoice to PO and in-scope receipts from the packet. Same-PO receipts not in the packet can be listed as excluded if the template requests them.
- Approved chargebacks reduce release amount. Pending chargebacks keep the invoice held with zero net release.
- Hold missing-receipt invoices when no in-scope receipt exists for the PO.
- Receiving exception labels should be derived from PO/receipt/invoice mismatches and local chargeback reasons:
  - received less than ordered: underage quantity
  - invoice billed more than received or a material unmatched quantity exists: severe unmatched or AP quantity variance, using the template's labels
  - receipt status inspection hold: inspection hold
- Summary totals are sums over target invoices only. Follow-up actions should be selected from the template's allowed labels based on missing receipts, pending quality chargebacks, excluded duplicate receipts, and approved chargeback netting.

## Final Check

Before returning, re-open the produced JSON mentally against the template: every required key is present, values use allowed enums, sorted fields are sorted, numbers are rounded to the requested precision, no prose surrounds the JSON, and no records outside the local task scope are included.
