# ProcureOps API Reconciliation & Decision Skills

## Environment Setup

- **Always use** the API base URL from `environment_access.md` (e.g., `GDPEVO_ENV_BASE_URL=http://34.46.77.124:8006`).
- **Never** start a local environment, run `env/setup.sh`, or use `localhost` / `127.0.0.1` unless the remote URL itself points there.
- The API root (`GET /`) returns the canonical endpoint list. Inspect it first if endpoints are unknown.

## API Endpoints & Data Model

Standard endpoints (paths map directly from the root list, e.g. `ap_invoices` → `/ap/invoices`):

| Resource | Key Fields | Relationships |
|----------|-----------|---------------|
| `purchase_orders` | `po_id`, `program_id`, `supplier_id`, `contract_id`, `status`, `lines[{sku,quantity,unit_price}]`, `subtotal`, `tax`, `total`, `freight`, `ship_to`, `due_date` | Link to `program_id`, `supplier_id`, `contract_id` |
| `receipts` | `receipt_id`, `po_id`, `supplier_id`, `status`, `lines[{sku,quantity_received,quantity_rejected,inspection_status}]`, `receipt_date` | Link to `po_id` |
| `ap_invoices` | `invoice_id`, `po_id`, `supplier_id`, `status`, `hold_code`, `lines[{sku,quantity_billed,unit_price}]`, `subtotal`, `tax`, `total`, `freight`, `receipt_id` | Link to `po_id`, `supplier_id` |
| `payments` | `payment_id`, `invoice_id`, `supplier_id`, `amount`, `scheduled_date`, `status` (scheduled / released / blocked) | Link to `invoice_id`, `supplier_id` |
| `suppliers` | `supplier_id`, `name`, `risk_rating` (low / medium / watch / high), `status`, `payment_terms` | — |
| `contracts` | `contract_id`, `sku`, `supplier_id`, `unit_price`, `ceiling_amount`, `status`, `effective_date`, `expiry_date` | Link to `sku`, `supplier_id` |
| `items` | `sku`, `standard_cost`, `preferred_supplier_id`, `category`, `active` | — |
| `programs` | `program_id`, `budget_cap`, `committed_amount`, `owner`, `status` | — |
| `budget_snapshots` | `program_id`, `budget_cap`, `committed_amount`, `pending_invoice_amount`, `snapshot_date` | — |
| `purchase_requisitions` | `requisition_id`, `sku`, `program_id`, `quantity`, `status`, `priority` | — |
| `approval_events` | `event_id`, `object_id`, `object_type`, `action`, `actor`, `event_date`, `note_code` | — |
| `vendor_risk_events` | `event_id`, `supplier_id`, `severity`, `status` (open / closed / monitoring), `event_type`, `related_object_id` | — |

**Query patterns:** Many endpoints support query params (e.g., `?sku=LMP-228`, `?program_id=PRG-AX17`). Use them to reduce payload size.

## Cross-Cutting Business Rules

### Three-Way Match & Quantity Variance
- **quantity_variance** = `quantity_billed` − `quantity_received` (use `0.00` when no receipt exists).
- **quantity_variance_pct** = `(quantity_variance / PO_quantity) × 100`, rounded to **1 decimal**.
- Receipt absence (`receipt_id: null`) is a valid exception code: `NO_RECEIPT`.

### Invoice Status Hierarchy
- `approved` → ready for payment (but may still have scheduled payments).
- `on_hold` → blocked by `hold_code` (e.g., `QTY_VARIANCE`, `PRICE_VARIANCE`, `NO_RECEIPT`).
- `pending_receipt` → awaiting receipt.
- `paid` → already settled.

### Receipt Status Semantics
- `accepted` → goods received, inspection passed.
- `accepted_with_note` → received with minor issues, still acceptable.
- `inspection_hold` → quality review pending; blocks downstream AP release.

### Supplier Risk
- `risk_rating` values: `low`, `medium`, `watch`, `high`.
- `vendor_risk_events` with `status: "open"` or `"monitoring"` are active blockers.
- A `watch` or `high` rating, or an open severe event, can trigger `supplier_watch` / `open_supplier_risk` blocker codes.

### Financial Rounding
- All USD amounts: round to **2 decimals** (cents).
- Percentages: round to **1 decimal**.
- Use standard `round(x, 2)`; watch for floating-point drift in large pipelines.

## Task-Type Playbooks

### 1. Nomination / Readiness Reviews (e.g., train_001)
**Goal:** Per SKU, decide `nominate` | `conditional_nomination` | `hold` and readiness `ready` | `at_risk` | `not_ready`.

**Data to fetch:**
- All POs for the program/SKU.
- All receipts for those POs.
- All invoices for those POs (focus on `on_hold` / `pending_receipt` as exception IDs).
- All `vendor_risk_events` for the suppliers.
- Supplier records (risk_rating).
- Contract coverage.

**Decision logic:**
- `not_ready` if any blocker exists; `at_risk` if minor issues; `ready` if clean.
- **Blocker codes** (sorted ascending): `missing_contract`, `supplier_watch`, `open_supplier_risk`, `ap_hold`, `pending_receipt`, `late_due_date`, `none`.
- `nominate` only when `ready` and no blockers.
- `conditional_nomination` when `at_risk`.
- `hold` when `not_ready`.
- All lists (`package_po_ids`, `receipt_evidence_ids`, `invoice_exception_ids`, `risk_event_ids`, `blocker_codes`) sorted **ascending**.

### 2. Receiving Memo / Release-or-Hold (e.g., train_002)
**Goal:** Determine whether the invoice tied to a receipt batch can be released or should remain blocked.

**Data to fetch:**
- Target receipt(s).
- Linked PO, contract, supplier.
- Invoice(s) tied to the PO/receipt.
- Risk events for the supplier.

**Decision logic:**
- If receipt status is `inspection_hold` → blocked.
- If quantity variance exists (billed > received) → blocked (`QTY_VARIANCE`).
- If invoice `hold_code` is set → blocked per that code.
- If supplier has open severe risk events → blocked.
- Otherwise, if three-way match is clean → release.

### 3. AP Close / Vendor Balance Reconciliation (e.g., train_003)
**Goal:** Reconcile invoice-level payment decisions, supplier balances, program totals, and hold/release queues.

**Data to fetch:**
- Target invoices.
- Linked POs and receipts.
- All payments for the target suppliers.
- Supplier records.

**Calculations:**
- **opening_balance** = `0.00` for the close slice (per memo instruction).
- **invoice_total** = invoice `total` (includes tax + freight).
- **scheduled_payment_amount** = sum of `payments` with `status: "scheduled"` and `scheduled_date <= close_date` for that supplier.
- **net_balance_impact** = `invoice_total - scheduled_payment_amount`, rounded to 2 decimals.
- **close_balance** = `opening_balance + invoice_total - scheduled_payments`, rounded to 2 decimals.
- **quantity_received** = receipt line `quantity_received` (or `0.00` if no receipt).

**Hold/Release Decision:**
- `HOLD` if: `NO_RECEIPT`, `QTY_VARIANCE`, or invoice status is `on_hold` / `pending_receipt`.
- `RELEASE` if: three-way match clean (`APPROVED_THREE_WAY_MATCH`), invoice `approved`, and no scheduled payment conflict.
- `release_to_payment` = `true` only for `RELEASE` decisions.

**Reason codes** (alphabetical):
- `APPROVED_THREE_WAY_MATCH`
- `NO_RECEIPT`
- `QTY_VARIANCE`
- `SCHEDULED_PAYMENT_FOUND`

**Balance status enum:**
- `OPEN_HELD` — has held invoices.
- `OPEN_APPROVED` — approved but not fully scheduled.
- `FULLY_SCHEDULED` — all invoices have matching scheduled payments.

### 4. Source Selection / Award (e.g., train_004)
**Goal:** Pick a supplier, determine price-to-award, PO, budget exposure, and contract ceiling impact.

**Data to fetch:**
- Item record (`standard_cost`, `preferred_supplier_id`).
- Active contract for the SKU.
- All POs for the SKU/program (exclude `cancelled` from contract usage).
- Budget snapshot for the program.
- Approval events for the requisition/PO.
- Supplier risk events.

**Calculations:**
- **price_to_award_usd** = contract `unit_price` (or lowest valid quote if multi-quote).
- **line_subtotal** = `quantity × unit_price`.
- **tax** = `line_subtotal × (tax_rate_percent / 100)`.
- **budget_exposure** = `line_subtotal + tax` (+ freight **only if** the memo explicitly provides freight).
- **contract_ceiling_exposure** = `line_subtotal` (before tax and freight).
- **existing_contract_usage** = sum of `total` from all non-cancelled POs under the same contract.
- **remaining_contract_ceiling** = `ceiling_amount - existing_contract_usage - contract_ceiling_exposure`.

**Approval chain check:**
- Verify the requisition has an `approval_events` record with `action: "approved"`.
- `approval_good_actions` = `["approved"]`.
- If no approved event, flag as `approval_gap`.

**Risk status:**
- `winning_supplier_risk_status` = supplier `risk_rating` unless an open severe event changes it.

### 5. Mixed Receiving Exception / AP Release (e.g., train_005)
**Goal:** Produce release decisions and receiving exception resolutions for a packet of POs, receipts, and invoices.

**Data to fetch:**
- All target POs, receipts, invoices from API.
- Local `chargeback_register_excerpt` and `release_request_note` from payload.

**Chargeback logic:**
- `approved_chargeback_amount` = `basis_quantity × unit_cost` for chargebacks with `status: "approved"`.
- `pending_chargeback_amount` = `basis_quantity × unit_cost` for chargebacks with `status: "pending_quality_review"`.
- `net_release_amount` = `invoice_total - approved_chargeback_amount - pending_chargeback_amount`.

**Exception codes** (per receipt):
- `Underage Quantity` — received < PO quantity.
- `Severe Unmatched Quantity` — large variance (context-dependent).
- `Inspection Hold` — receipt status is `inspection_hold`.
- `AP Quantity Variance` — invoice billed ≠ receipt received.

**Chargeback status:**
- `approved` — approved chargeback exists.
- `pending_quality_review` — pending chargeback exists.
- `not_applicable` — no chargeback for this receipt.

**Resolution status:**
- `net_release_ready` — approved chargeback nets out, no other blockers.
- `hold_for_quality_review` — pending chargeback or inspection hold.
- `accepted_no_receiving_exception` — clean receipt, no issues.
- `missing_receipt` — no receipt on PO.

**Release decisions:**
- `release_net_after_approved_chargeback` — when approved chargeback exists and no pending blockers.
- `hold_missing_receipt` — no receipt found for the PO.
- `hold_pending_quality_chargeback` — pending chargeback or inspection hold.

## Output Conventions

- **Return only JSON** matching `answer_template.json` exactly.
- **Sort all ID lists ascending** unless the template specifies another order.
- **task_id** must equal the expected value (e.g., `train_001`, `train_005`).
- **Dates:** `YYYY-MM-DD`.
- **Currency:** USD, rounded to cents (2 decimals).
- **Percentages:** rounded to 1 decimal.
- Use **controlled reason codes / enums**; never substitute free-text narratives.
- For `null` fields in the template, output JSON `null`, not the string `"null"`.

## Common Pitfalls

1. **Wrong API URL:** Using `127.0.0.1:8006` from the task prompt instead of the environment_access.md remote URL.
2. **Unsorted lists:** Forgetting to sort `po_ids`, `receipt_ids`, `invoice_ids`, `blocker_codes`, etc., ascending.
3. **Cancelled PO inclusion:** Always exclude `status: "cancelled"` POs from contract usage and budget calculations.
4. **Freight ambiguity:** Only add freight to `budget_exposure` when the source-selection memo explicitly provides a freight amount.
5. **Receipt null handling:** When `receipt_id` is `null`, use `quantity_received: 0.00` and reason code `NO_RECEIPT`.
6. **Tax base confusion:** Tax is computed on `subtotal` (line items), not on total including freight.
7. **PO-73xx alias trap:** Exact PO-73xx receipt IDs may not exist in the shared environment. Use the generated PO/receipt IDs named in the local packet instead.
8. **Opening balance assumption:** AP close slices often assume `0.00` opening balance for the target suppliers unless the memo states otherwise.
9. **Payment scope:** Only count payments with `status: "scheduled"` and `scheduled_date <= close_date` toward the close balance.
10. **Risk event filtering:** Only `status: "open"` or `"monitoring"` risk events count as active blockers; `"closed"` events are historical.
