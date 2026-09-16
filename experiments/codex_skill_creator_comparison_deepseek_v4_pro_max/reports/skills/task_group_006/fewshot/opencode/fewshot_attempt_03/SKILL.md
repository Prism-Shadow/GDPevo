---
name: procureops-solver
description: Solve ProcureOps operational-data tasks using the shared ProcureOps REST API. Use this skill whenever the task involves ProcureOps records (programs, suppliers, items, contracts, purchase orders, receipts, AP invoices, payments, approvals, budgets, vendor risk events) or references a ProcureOps API base URL. Trigger on mentions of procurement, sourcing, receiving, AP close, change control, chargebacks, nomination packets, exception review, or any ProcureOps domain term. Do not attempt to solve these tasks without this skill.
---

# ProcureOps Solver

Solve structured procurement-operations tasks that require querying a shared
ProcureOps REST API, cross-referencing records across endpoints, applying
business rules, and filling a JSON answer template.

## Core Workflow

Every ProcureOps task follows this sequence:

1. **Parse the prompt and payloads.** Identify which API endpoints are needed,
   what local memos constrain the scope, and what the answer template requires.
   The prompt may name specific programs, suppliers, receipts, invoices, or POs;
   treat those as the initial scope anchor.

2. **Read the answer template.** It lives in the payloads directory (named in
   the prompt, typically `input/payloads/answer_template.json`). The template
   defines the exact output shape: required keys, field types, enum sets, sort
   orders, numeric precision, and list semantics. Fill every required key.

3. **Query all relevant API endpoints.** The API base URL is provided by the
   runner as `<TASK_ENV_BASE_URL>` in the prompt text. Never hardcode it.
   Query every endpoint that could supply records for the task scope. The API
   returns results with a `count` field and a `results` array; read the full
   result set in one pass since record counts are modest.

   Endpoints are listed in [references/api-schemas.md](references/api-schemas.md).
   Consult it for the exact field shape of each record type before building
   cross-reference logic.

4. **Cross-reference records.** Join records across endpoints by shared
   identifiers. The primary join keys are:
   - `program_id` -- links programs, contracts, POs, requisitions, budget snapshots
   - `supplier_id` -- links suppliers, contracts, POs, receipts, invoices, payments, risk events
   - `po_id` -- links POs to receipts, invoices, and risk events (via `related_object_id`)
   - `sku` -- links items to contracts, PO lines, receipt lines, requisitions
   - `requisition_id` -- links requisitions to POs and approval events (via `object_id`)
   - `invoice_id` -- links invoices to payments and chargeback packets
   - `contract_id` -- links contracts to POs

   When joining, prefer exact matches. Treat `null` contract_id or receipt_id
   as a data gap that should surface in decisions and blocker codes.

5. **Apply business rules.** Derive decisions, codes, and statuses from the
   data. Common rule patterns are described below. Do not invent rules that
   are not implied by the data or template.

6. **Fill the template exactly.** Populate every field required by the template.
   Respect enum sets, sort orders, numeric precision, and list semantics
   documented in the template. Return only the JSON object -- no markdown
   fences, no prose outside the object.

7. **Include evidence.** When the template has an `evidence` section or
   `supporting_ids`, list every API record ID (and local payload filename)
   that contributed to the answer. This is audit trail, not decoration.

## Cross-Referencing Patterns

### Line-Level Reconciliation (PO, Receipt, Invoice)

When a task asks for quantity reconciliation at the line level, match
records by `po_id` and `po_line_id` across POs, receipts, and invoices:

- PO lines carry the ordered quantity and unit price.
- Receipt lines carry the received and rejected quantities.
- Invoice lines carry the billed quantity and billed unit price.

Calculate:
- `short_qty_vs_po` = ordered_qty - received_qty
- `unreceived_billed_qty` = billed_qty - received_qty (when billed exceeds received)
- `receipt_completion_ratio` = received_qty / ordered_qty (rounded to 4 decimal places)

When no receipt exists for a PO, treat all quantities as 0 received.

### Contract Headroom

When calculating contract ceiling headroom for a change or nomination:

1. Find the contract by `contract_id`.
2. Sum the `subtotal` of all POs linked to that contract whose status is
   **not** `cancelled`. Exclude cancelled POs from usage.
3. `headroom` = `ceiling_amount` - noncancelled_subtotal.
4. Requested subtotal = requested_quantity x contract unit_price.
5. `headroom_after_change` = headroom - requested_subtotal.
6. `ceiling_ok` is true when headroom_after_change >= 0.

### Budget Capacity

When checking program budget for a change:

1. Use the latest budget snapshot (highest `snapshot_date`) for the program.
2. `remaining_budget` = `budget_cap` - `committed_amount`.
3. Requested total = requested_subtotal + estimated_tax (apply the tax rate
   given in the payload; do not add freight unless the payload explicitly
   provides a freight amount).
4. `budget_after_change` = remaining_budget - requested_total.
5. `budget_ok` is true when budget_after_change >= 0.
6. `max_quantity_with_current_budget` = floor(remaining_budget / (unit_price x (1 + tax_rate/100))).

### Invoice Payment Hold/Release

For AP close tasks:

- Query `/ap/payments` filtered by the target invoice IDs to find scheduled payments.
- A payment is in scope if it is scheduled on or before the look-ahead date
  (given in the prompt or payload).
- `net_balance_impact` = invoice_total - scheduled_payment_amount.
- Derive reason codes from data conditions:
  - `APPROVED_THREE_WAY_MATCH` -- invoice status is `approved` with a matching receipt and no hold code.
  - `NO_RECEIPT` -- invoice has no receipt_id or receipt_id is null.
  - `QTY_VARIANCE` -- billed quantity differs from received quantity.
  - `SCHEDULED_PAYMENT_FOUND` -- a payment is scheduled for this invoice.
- An invoice is `RELEASE` when no hold conditions exist and three-way match is clean;
  otherwise `HOLD`.

### Supplier Risk Filtering

When assessing supplier risk context for a task as-of a given date:

- Query `/vendor_risk_events` for the supplier.
- Include events with `status` of `open` or `monitoring` that have an `event_date`
  on or before the as-of date.
- A severe open event is one with `severity` = `high` and `status` = `open`.
- The supplier baseline `risk_rating` comes from `/suppliers`.

### Approval State

When checking approval for a requisition:

- Query `/approvals` filtered by `object_id` matching the requisition ID and
  `object_type` = `requisition`.
- The latest event (by `event_date`) determines the current state.
- `approval_ok` is true when the latest action is `approved`; false otherwise.
  (The payload may define allowable actions via an `approval_good_actions` list.)

### Chargeback Reconciliation

When a local chargeback register accompanies the task:

- Match chargebacks to invoices by `invoice_id` and to receipts by `receipt_id`.
- `approved_chargeback_amount` sums chargebacks with status `approved`.
- `pending_chargeback_amount` sums chargebacks with status `pending_quality_review`.
- `net_release_amount` = invoice_total - approved_chargeback_amount.
- Release when all chargebacks are approved; hold when any are pending quality review.

## Financial Rules

- All monetary values are in USD, rounded to cents (2 decimal places).
- Use arithmetic rounding (Python `round(x, 2)` or equivalent).
- Subtotal = quantity x unit_price.
- Tax = subtotal x (tax_rate_percent / 100), unless the API record already
  provides a tax value (prefer the API value for existing records).
- Total = subtotal + tax + freight (freight from the API or payload, 0 if absent).
- When the template asks for `invoice_total`, use the API `total` field
  directly rather than recomputing.

## Quantity Rules

- Quantities are integers for discrete items (EA, KIT).
- When no receipt exists: received_qty = 0, rejected_qty = 0.
- A PO with multiple receipts: sum received quantities across all receipts
  for that PO, per line. Be careful not to double-count.
- `quantity_variance` = billed_qty - received_qty.
- `quantity_variance_pct` = (variance / ordered_qty) x 100, rounded to 1 decimal.
  When ordered_qty is 0 (should not happen), treat variance_pct as 0.

## Decision Derivation

When the template asks for a multi-factor decision (e.g., `release_amendment`,
`hold_for_budget`, `hold_for_approval`), evaluate each factor independently and
combine:

1. Contract ceiling: `ceiling_ok` must be true.
2. Budget: `budget_ok` must be true.
3. Approval: `approval_ok` must be true.
4. Supplier risk: `supplier_risk_ok` must be true (no severe open events).

The decision is the most restrictive applicable hold. If multiple holds apply,
use the combined decision code from the template enum (e.g.,
`hold_for_budget_and_approval`).

For nomination readiness (`nominate`, `conditional_nomination`, `hold`):
- `nominate` -- all blockers clear, no risk events, contract exists, receipts complete.
- `conditional_nomination` -- some watch-level risk events or AP holds exist
  that can be cleared externally.
- `hold` -- missing contract, open severe risk, no receipt, or late due date.

## Blocker and Exception Codes

Derive codes from data conditions, not from the prompt narrative:

- `missing_contract` -- PO has no contract_id or contract is not active.
- `supplier_watch` -- supplier risk_rating is `watch` or `high`.
- `open_supplier_risk` -- at least one open supplier risk event exists.
- `ap_hold` -- invoice exists with status `on_hold` or `pending_receipt`.
- `pending_receipt` -- PO has no matching receipt or receipt status is not `accepted`.
- `late_due_date` -- PO due_date is before the as_of_date and PO is not fully received.
- `none` -- no blockers found.

For receiving exceptions:
- `INVOICE_QTY_EXCEEDS_RECEIPT` -- billed > received on any line.
- `PARTIAL_RECEIPT` -- received < ordered but > 0.
- `SUPPLIER_WATCH_RISK` -- supplier has active watch/high risk events.
- `PRICE_MISMATCH` -- invoice unit price differs from contract or PO unit price.
- `DAMAGE_REJECTION` -- receipt has rejected quantity > 0.
- `NO_EXCEPTION` -- none of the above.

## Output Formatting

- Return only the JSON object. No markdown fences, no explanatory text outside
  the object.
- Sort list fields as the template specifies: if `sorted ascending`, sort;
  if `set`, use sorted ascending as the default stable order.
- Enum strings must match the template allowed values exactly (case-sensitive).
- `null` is valid for optional fields; use it (not the string "null") when
  a value is genuinely absent.
- Empty lists use `[]`, not `null`, when the template expects an array.
- Dates are `YYYY-MM-DD` strings.
- Monetary values are numbers (not strings), rounded to cents.
- Quantities are integers for line items.

## Evidence and Audit Trail

Every answer should record which sources contributed. The template may have
a dedicated `evidence` or `supporting_ids` section. When it does:

- `endpoint_record_ids`: list every API record ID queried (PO IDs, receipt IDs,
  invoice IDs, contract IDs, supplier IDs, risk event IDs, approval event IDs,
  budget snapshot IDs, requisition IDs).
- `task_payloads_reviewed`: list every local payload file read.
- Sort all ID lists ascending.

When the template lacks an explicit evidence section but asks for
`supporting_ids`, include the IDs of records that directly informed the
decision (POs, approvals, risk events).

## Scope Discipline

- Only include records within the task scope as defined by the prompt and
  payloads. If a memo names specific POs or invoices, limit analysis to those
  and records directly linked to them.
- Time-bound queries: use the as_of_date or close_date from the prompt/payload
  to filter records. Receipts after the as_of_date are out of scope. Payments
  scheduled after the look-ahead date are out of scope.
- When a payload provides explicit opening-balance or slice rules (e.g., treat
  opening balance as 0.00), apply them literally.

## Handling the API

- The API base URL is always provided in the prompt as `<TASK_ENV_BASE_URL>`.
  Substitute it at runtime.
- All endpoints are GET with no authentication required.
- Endpoints return `{"count": N, "results": [...]}`. Read the full results.
- See [references/api-schemas.md](references/api-schemas.md) for the complete
  field reference for every endpoint. Read it before querying unfamiliar
  endpoints.

## Task Archetypes

The training examples cover five recurring ProcureOps task patterns. When a
task resembles one of these, follow the same analytical structure:

### Nomination Packet (sourcing readiness)

Given a program and package-line SKUs, cross-reference suppliers, contracts,
requisitions, POs, receipts, invoices, and risk events to determine per-line
readiness. Output blocker codes, a nomination decision per supplier, and a
committee action summary.

### Receiving Closeout

Given a receipt batch ID, reconcile received vs. ordered vs. billed quantities
line-by-line. Compute financial exposure, invoice hold position, and the
controlled disposition (accept variance, release, reject, manual recount).
Include supplier risk context.

### AP Close Reconciliation

Given a set of invoice IDs, compute per-invoice payment hold/release decisions,
vendor balance reconciliation (opening balance + invoices - scheduled payments),
program-level rollups, and the final hold/release queues.

### Change Control Decision

Given a change memo payload naming a contract, SKU, and requested incremental
quantity, check contract ceiling, program budget, requisition approval, and
supplier risk. Output a single decision code, quantified blockers, and required
actions.

### AP/Receiving Release File

Given a release packet with target PO, receipt, and invoice IDs plus a
chargeback register, produce per-invoice release decisions (release after
approved chargeback, hold pending quality, hold missing receipt), per-receipt
exception codes and resolution statuses, and a summary with totals and
follow-up actions.
