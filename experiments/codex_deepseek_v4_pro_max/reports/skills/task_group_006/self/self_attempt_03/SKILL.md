## When to use this skill

Use this skill when the task involves a ProcureOps-style procurement API — sourcing, receiving, accounts-payable, change-control, or release-file workflows where you must query a shared REST API, cross-reference local payloads with live records, apply procurement business rules, and return structured JSON matching an answer template.

## Core operating model

The ProcureOps API is always the **system of record**. Local payloads (memos, packets, registers) name anchors — program IDs, PO IDs, invoice IDs, suppliers, receipts — and describe the business request, but every live fact (quantities, statuses, prices, dates, balances, risk events) comes from the API. Never trust a local payload over an API response for a live operational fact. When they conflict, the API wins and the local payload is the request intent.

## Phase 1 — Orient

1. **Read every local payload** in `input/payloads/` before touching the API. These include:
   - Answer templates (the output shape you must match exactly)
   - Task-specific memos or packets naming target IDs and business controls
   - Optional registers or excerpt files containing task-local facts (e.g., chargeback records, alias notes)

2. **Note the named anchors** from the local payloads: program IDs, contract IDs, supplier IDs, PO IDs, receipt IDs, invoice IDs, SKUs, variant codes, requisition IDs, and any as-of dates or reference dates.

3. **Fetch the API manifest** (`GET /manifest`) to confirm which collections and fields are available in this environment. The manifest may vary between deployments.

## Phase 2 — Gather records

Use these query patterns against the ProcureOps API:

| Pattern | Usage |
|---|---|
| `GET /<collection>` | List all records in a collection |
| `GET /<collection>/<id>` | Fetch a single record by its ID |
| `GET /<collection>?field=value` | Exact-match filter on top-level or nested fields |
| `GET /<collection>?start=YYYY-MM-DD&end=YYYY-MM-DD` | Date range (for date-indexed collections) |

**Efficiency rule**: When local payloads give you specific IDs, fetch those records directly by ID rather than listing the whole collection. Fall back to filtered listing only when you need records by a non-ID attribute or the task requires a full-collection scan.

**Relational chaining**: Follow foreign keys to build a complete picture. Common chains include:
- PO → supplier, contract, program, requisition
- Invoice → PO → receipt, supplier
- Receipt → PO → supplier, contract
- Approval → requisition
- Contract → supplier, program

**Date scoping**: When a task specifies an as-of date, filter date-indexed collections to that date or earlier. Payments scheduled through a future cutoff date (e.g., end of quarter) reduce close balances; payments beyond that cutoff do not.

## Phase 3 — Cross-reference and reconcile

1. **Match local anchors to API records**: Confirm every ID from the local payloads resolves to an actual API record. If a local payload names an ID that does not exist, read any alias notes provided in the payloads and fall back to the nearest available ID.

2. **Validate local assertions**: If a local memo asserts a fact about a record (e.g., supplier name, program owner, quantity), verify it against the API and use the API value.

3. **Reconcile quantities across the chain**:
   - Ordered (PO line quantity) vs Received (receipt quantity) vs Billed (invoice quantity)
   - `short_qty_vs_po = ordered_qty − received_qty`
   - `unreceived_billed_qty = billed_qty − received_qty` (positive means billed more than received)
   - `receipt_completion_ratio = received_qty / ordered_qty` (to 4 decimal places)

## Phase 4 — Apply business rules

### Contract check

- Use the contract's **status**, **price_type**, and **unit_price** from the API.
- Compute `noncancelled_subtotal` = sum of (unit_price × quantity) for all non-cancelled POs on the contract.
- Compute `headroom_before_change = ceiling_amount − noncancelled_subtotal`.
- Compute `requested_subtotal = unit_price × requested_quantity`.
- Compute `headroom_after_change = headroom_before_change − requested_subtotal`.
- `ceiling_ok` is true when `headroom_after_change ≥ 0`.

### Budget check

- Use the most recent budget snapshot for the program.
- Compute `remaining_budget = budget_cap − committed_amount`.
- `requested_total = requested_subtotal + tax` (tax = subtotal × tax_rate_percent / 100).
- `budget_after_change = remaining_budget − requested_total`.
- `budget_ok` is true when `budget_after_change ≥ 0`.
- `max_quantity_with_current_budget = floor(remaining_budget / (unit_price × (1 + tax_rate_percent/100)))`.

### Approval check

- Find the latest approval event for the source requisition.
- `approval_ok` is true when the latest action is in the set of approval-good actions (e.g., `approved`).
- Otherwise the change must not proceed until approval is obtained.

### Supplier risk check

- Pull vendor risk events for the supplier.
- Filter to events with status `open`.
- `supplier_risk_ok` is true when there are **no** open severe-risk events. Non-severe open events are context only and do not block on their own.

### Three-way match (AP / receiving)

- For each invoice line, compare billed quantity to received quantity.
- If billed > received and no receipt exists: `NO_RECEIPT`.
- If billed > received and a receipt exists: `QTY_VARIANCE` or `INVOICE_QTY_EXCEEDS_RECEIPT`.
- If billed = received and both match the PO: `APPROVED_THREE_WAY_MATCH`.
- Price match: compare invoice unit price to contract unit price.

## Phase 5 — Decide

Apply the decision framework most relevant to the task:

| Task domain | Decision axis | Values |
|---|---|---|
| Sourcing nomination | per-line nomination | `nominate`, `conditional_nomination`, `hold` |
| Readiness | overall / per-line | `ready`, `at_risk`, `not_ready` |
| AP hold/release | per-invoice | `HOLD`, `RELEASE` |
| Batch disposition | single batch | `accept_partial_hold_variance`, `release_full_invoice`, `reject_batch`, `manual_recount_required` |
| Change control | single CR | `release_amendment`, `hold_for_budget`, `hold_for_approval`, `hold_for_supplier_risk`, `hold_for_budget_and_approval`, `reject_contract_mismatch` |
| AP release file | per-invoice | `release_net_after_approved_chargeback`, `hold_missing_receipt`, `hold_pending_quality_chargeback` |

**Blocker codes** (use `none` when no blockers exist):
- `missing_contract` — no active contract covers the SKU/supplier
- `supplier_watch` — supplier has a monitoring or watch status
- `open_supplier_risk` — supplier has an open risk event
- `ap_hold` — invoice is on AP hold
- `pending_receipt` — goods not yet received
- `late_due_date` — delivery is past the due date

**Committee / next-owner routing**:
- `buyer` — missing contract or commercial basis
- `finance_ops` — budget or ceiling issues
- `quality_ops` — supplier risk or quality events
- `program_owner` — scope or requirement issues
- `ap_team` — invoice hold or payment issues

## Phase 6 — Format the answer

1. **Match the answer template exactly**. Do not add keys, remove keys, or rename keys.
2. **Return only JSON**. No prose, no markdown fences, no trailing text.
3. **Round all USD amounts to cents** (2 decimal places). Use standard rounding.
4. **Sorting rules**:
   - When the template says "sorted ascending" for a list, sort the values.
   - When the template says "set" or says nothing about ordering, treat the list as unordered (the evaluator will sort).
   - Sort string IDs lexicographically ascending.
   - Sort numeric IDs numerically ascending.
5. **Null vs empty**: Use `null` for absent single values. Use `[]` for absent lists.
6. **Booleans**: Use JSON `true` / `false`, never strings.
7. **Date format**: `YYYY-MM-DD` throughout.
8. **Enum values**: Use exactly the allowed values from the template. Do not invent new ones.

## API endpoint reference

See `skill/api_reference.md` for the canonical endpoint list and query patterns. Always prefer the live manifest over the reference when they differ.
