# ProcureOps API Task Group Skill

## Overview

Tasks in this group require querying a shared ProcureOps API and producing structured JSON outputs for procurement operations: nomination reviews, receiving/AP exception reviews, AP close files, and change requests. The API is the **authoritative source of truth**; local memos and packets provide context and anchors but must be cross-checked against live API records.

## API Access

- **Base URL**: Provided by the task runner, or start the local environment at `http://127.0.0.1:8006`.
- **Expected endpoints** (discover dynamically via root path or OpenAPI docs if available):
  - `/programs` or `/programs/{program_id}`
  - `/purchase_orders` or `/purchase_orders/{po_id}`
  - `/receipts` or `/receipts/{receipt_id}`
  - `/ap/invoices` or `/ap/invoices/{invoice_id}`
  - `/ap/payments` or `/ap/payments?invoice_id={id}`
  - `/suppliers` or `/suppliers/{supplier_id}`
  - `/contracts` or `/contracts/{contract_id}`
  - `/budget_snapshots` or `/budget_snapshots/{snapshot_id}`
  - `/items/{sku}`
  - `/requisitions` or `/requisitions/{id}`
  - `/approvals` or `/approval_events`
  - `/vendor_risk_events` or `/vendor_risk_events?supplier_id={id}`

### SOP: API Exploration

1. Probe the root URL (`GET /`) to discover available endpoints or an OpenAPI spec.
2. If the service is not running, start it per the task environment instructions (e.g., Docker, script, or direct launch).
3. Query endpoints with filters (e.g., `?program_id=AX17`) to narrow records rather than fetching everything.
4. Cache responses locally to avoid redundant calls during analysis.

## Source Precedence Hierarchy

1. **ProcureOps API records** — absolute source of truth for all quantities, statuses, prices, and IDs.
2. **Local chargeback register** (if present in task payloads) — authoritative for approved/pending chargeback amounts.
3. **Local memos / packets** — provide narrative context, PO aliases, and target anchors. Treat as **supporting only**, not as overrides for API data.
4. If a memo references IDs not found in the API (e.g., PO-73xx aliases), follow any explicit ID mapping provided in the local packet.

## Task Type Identification

| Task Pattern | Output Template Shape | Key Focus |
|--------------|----------------------|-----------|
| Nomination review | `nomination_lines[]`, `committee_action` | Supplier readiness, blockers, risk events |
| Receiving batch review | `inspection_summary`, `line_reconciliation[]`, `invoice_review`, `decision` | Receipt-to-PO-to-invoice three-way reconciliation |
| AP close | `invoice_decisions[]`, `vendor_balances[]`, `payment_hold_queue`, `payment_release_queue`, `total_close_balance` | Post-inspection payment release/hold decisions |
| Receiving/AP release (packet-based) | `release_decisions[]`, `receiving_exceptions[]`, `summary` | Exception review with chargeback netting |
| Change request | `contract_check`, `program_budget_check`, `approval_check`, `supplier_risk_check`, `required_actions[]` | Contract ceiling, budget headroom, approval status, risk gates |

Always read `input/prompt.txt` and `input/payloads/answer_template.json` to confirm the exact required output shape for the task at hand.

## Universal Output Conventions

- **ID lists**: Always sort ascending (lexicographically for strings).
- **Dates**: Use `YYYY-MM-DD` format.
- **Currency**: USD, rounded to **2 decimal places** (cents).
- **Ratios**: Round to **4 decimal places** (e.g., `0.9867`).
- **Percentages**: Round to **1 decimal place**.
- **Boolean fields**: Use literal JSON booleans (`true`/`false`), not strings.
- **Enums**: Use exact allowed strings from the template; casing matters.
- **Sets / lists with set semantics**: The evaluator may sort values; you should still sort ascending before emitting.
- **task_id**: Emit exactly the value specified in the answer template (e.g., `train_005`).

## Business Rules by Domain

### 1. Quantity Reconciliation (Receiving / AP Release)

For each PO line or receipt:
- `ordered_qty` ← from PO record
- `received_qty` ← sum of accepted quantities from receipt records
- `rejected_qty` ← sum of rejected / inspection-hold quantities
- `billed_qty` ← from AP invoice line
- `short_qty_vs_po` = `ordered_qty - received_qty`
- `unreceived_billed_qty` = `billed_qty - received_qty` (when positive)
- `receipt_completion_ratio` = `received_qty / ordered_qty` (4 decimals)

**Exception code mapping** (apply zero or more):
- **Underage Quantity** — `received_qty < ordered_qty`
- **Severe Unmatched Quantity** — large discrepancy (context-dependent, often >10% or memo-defined threshold)
- **Inspection Hold** — any units pending quality review
- **AP Quantity Variance** — `billed_qty != received_qty`

### 2. Invoice Release Decisions

Per invoice, evaluate:
1. Does a receipt exist for the PO? If **no** → `hold_missing_receipt`, reason `no_receipt_on_po`.
2. Is there an approved chargeback? If **yes** → `release_net_after_approved_chargeback`, reason `approved_qty_chargeback`.
3. Is there a pending quality/chargeback hold? If **yes** → `hold_pending_quality_chargeback`, reason `inspection_hold_pending_chargeback`.
4. Is there an AP quantity variance? If **yes** → decide based on magnitude and approval status.

**Financial calculations**:
- `invoice_total` ← from API invoice record
- `approved_chargeback_amount` ← sum of approved chargebacks from local register or API
- `pending_chargeback_amount` ← sum of pending chargebacks
- `net_release_amount` = `invoice_total - approved_chargeback_amount`

**Important**: `net_release_amount` does **not** subtract `pending_chargeback_amount`. Pending amounts keep the invoice on hold; approved amounts are netted for release.

### 3. Chargeback Status Rules

| Scenario | chargeback_status | resolution_status |
|----------|-------------------|-------------------|
| Chargeback approved | `approved` | `net_release_ready` |
| Quality review pending with chargeback request | `pending_quality_review` | `hold_for_quality_review` |
| No discrepancy, no hold | `not_applicable` | `accepted_no_receiving_exception` |
| No receipt on file | `not_applicable` | `missing_receipt` |

### 4. AP Close File Rules

For each invoice in scope:
- `quantity_billed` vs `quantity_received`
- `quantity_variance` = `quantity_billed - quantity_received`
- `quantity_variance_pct` = `(quantity_variance / ordered_qty) * 100` (1 decimal)
- **Reason codes** (alphabetical):
  - `APPROVED_THREE_WAY_MATCH` — all quantities align
  - `NO_RECEIPT` — no receipt exists
  - `QTY_VARIANCE` — billed ≠ received
  - `SCHEDULED_PAYMENT_FOUND` — payment already scheduled

**Hold / release logic**:
- `HOLD` if any exception exists (no receipt, variance, pending hold).
- `RELEASE` if three-way match is clean or exceptions are approved.
- `release_to_payment` = `true` only for `RELEASE` decisions.

**Vendor balance**:
- `close_balance` = `opening_balance + invoice_total - scheduled_payments`
- `balance_status`:
  - `OPEN_HELD` — has held invoices
  - `OPEN_APPROVED` — all invoices releasable
  - `FULLY_SCHEDULED` — payments cover all invoices

### 5. Change Request Rules

**Contract check**:
- `headroom_before_change` = `ceiling_amount - noncancelled_subtotal`
- `requested_subtotal` = `requested_quantity * unit_price`
- `headroom_after_change` = `headroom_before_change - requested_subtotal`
- `ceiling_ok` = `headroom_after_change >= 0`

**Program budget check**:
- `remaining_budget` = `budget_cap - committed_amount`
- `requested_total` = `requested_subtotal + requested_tax`
- `budget_after_change` = `remaining_budget - requested_total`
- `budget_ok` = `budget_after_change >= 0`
- `max_quantity_with_current_budget` = `floor(remaining_budget / unit_price)`

**Approval check**:
- Find latest approval event for the source requisition.
- `approval_ok` = latest action is `approved` or equivalent.

**Supplier risk check**:
- `supplier_risk_ok` = no `severe` open risk events.
- Sort `open_event_ids` ascending.

**Decision matrix**:
- If `!ceiling_ok` → `reject_contract_mismatch`
- If `!budget_ok && !approval_ok` → `hold_for_budget_and_approval`
- If `!budget_ok` → `hold_for_budget`
- If `!approval_ok` → `hold_for_approval`
- If `!supplier_risk_ok` → `hold_for_supplier_risk`
- Else → `release_amendment`

### 6. Nomination Review Rules

For each SKU / supplier line:
- Gather POs, receipts, invoices, and risk events from API.
- `readiness_status`:
  - `ready` — contract in place, receipt evidence exists, no open risk, no AP hold
  - `at_risk` — minor issues (e.g., partial receipt, conditional approval)
  - `not_ready` — major blockers
- `blocker_codes` (sorted ascending; use `none` if no blockers):
  - `missing_contract`
  - `supplier_watch`
  - `open_supplier_risk`
  - `ap_hold`
  - `pending_receipt`
  - `late_due_date`
- `committee_action`:
  - `nominate_now_supplier_ids` — all `ready` lines
  - `conditional_supplier_ids` — `at_risk` lines
  - `hold_supplier_ids` — `not_ready` lines
  - `send_to_committee` = `yes` if any line is not `ready`

## Common Pitfalls

1. **PO-73xx alias trap**: Exact PO-73xx or RC-44xx IDs may not exist in the shared API environment. When a local packet provides generated IDs (e.g., `po_luma_ax17_7321`, `rc_luma_ax17_4401`), use those for API queries and output. Do not fabricate IDs.

2. **Unit price changes**: If a PO was modified (e.g., AX12 from $150 to $165), chargebacks and variances use the **current/modified unit price**, not the original. Verify against the live PO record.

3. **Duplicate receipt risk**: When a memo indicates a Vantix receipt (e.g., RC-3854) may have been received under a Luma receipt (e.g., RC-4401), flag this in `followup_actions` as `hold_luma_duplicate_receipt_for_separate_invoice` or `ask_receiving_for_vantix_receipt`.

4. **Quantity vs. value chargebacks**: Chargeback amounts are monetary (USD), not unit counts. Compute as `rejected_qty * unit_price` unless the local register specifies an exact amount.

5. **Sorting**: Many evaluator checks sort lists internally, but you should still emit them sorted ascending. Do not rely on evaluator sorting for pass/fail.

6. **Empty lists vs. null**: When a field expects a list and there are no items, emit `[]` (empty array), not `null`.

7. **Inspection hold timing**: An inspection hold may be mentioned in a memo but not yet reflected in ProcureOps. If the API shows no hold but the memo/local packet says there is one pending, use the local context for decision logic and note the discrepancy in follow-up actions.

8. **Currency rounding**: Perform all arithmetic at full precision, then round the **final result** to 2 decimals. Do not round intermediate values.

9. **Three-way match definition**: Match PO quantity → Receipt quantity → Invoice quantity. A variance at any leg is an exception.

10. **Evidence tracking**: For receiving batch reviews, record which endpoint record IDs and task payloads were reviewed in the `evidence` object. This supports auditability.

## Calculation Quick Reference

```
short_qty_vs_po          = ordered_qty - received_qty
unreceived_billed_qty    = max(0, billed_qty - received_qty)
receipt_completion_ratio = received_qty / ordered_qty   [round to 4 decimals]
quantity_variance        = quantity_billed - quantity_received
quantity_variance_pct    = (quantity_variance / ordered_qty) * 100  [round to 1 decimal]
net_release_amount       = invoice_total - approved_chargeback_amount
close_balance            = opening_balance + invoice_total - scheduled_payments
headroom_after_change    = ceiling_amount - noncancelled_subtotal - requested_subtotal
budget_after_change      = budget_cap - committed_amount - requested_total
max_quantity_with_budget = floor(remaining_budget / unit_price)
```

## Workflow Checklist

1. [ ] Read `input/prompt.txt` and identify task type.
2. [ ] Read `input/payloads/answer_template.json` to understand exact output schema.
3. [ ] Read local memo / packet / JSON for context and ID anchors.
4. [ ] Discover and query ProcureOps API endpoints.
5. [ ] Cross-reference API data with local context; resolve alias mappings.
6. [ ] Compute quantities, variances, financials, and decisions.
7. [ ] Populate all required output fields per template.
8. [ ] Sort all ID lists ascending.
9. [ ] Round all currency to 2 decimals, ratios to 4, percentages to 1.
10. [ ] Emit **only** the JSON object (no markdown, no extra text).
