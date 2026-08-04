# ProcureOps Business Rules Reference

Detailed business-logic patterns for each procurement workflow. Use this alongside `SKILL.md` to resolve specific computation, decision, and formatting questions.

## General Conventions

### Currency

- All monetary amounts are in USD.
- Round to two decimal places (cents) using standard rounding (half-up).
- When computing subtotals, apply rounding only at the final step (e.g., `round(qty * unit_price, 2)`).
- Tax is computed as `round(subtotal * rate, 2)` where rate is a decimal (e.g., 7.25% → 0.0725).

### Date Handling

- All dates use `YYYY-MM-DD` format.
- The as-of date (`end` parameter) means "on or before this date." Records with dates after the as-of date are excluded.
- Date comparisons: a PO is "late" if `due_date < as_of_date`.
- When sorting approval events by date, use chronological order (earliest first); the "latest" event is the one with the maximum date.

### ID Formats

These ID prefixes appear throughout the system:

| Prefix      | Entity                          |
| ----------- | ------------------------------- |
| `PRG-`      | Program                         |
| `SUP-`      | Supplier                        |
| `CR-`       | Contract                        |
| `REQ-`      | Purchase Requisition            |
| `PO-`       | Purchase Order                  |
| `RCV-`      | Receipt / Receiving Batch       |
| `AP-`       | AP Invoice                      |
| `PAY-`      | AP Payment                      |
| `APR-`      | Approval Event                  |
| `BUD-`      | Budget Snapshot                 |
| `VRE-`      | Vendor Risk Event               |
| `CB-`       | Chargeback (local register)     |
| `MCR-`      | Material Change Request (memo)  |
| `WH-`       | Warehouse                       |
| `PK-`       | Packing Slip                    |

### Enum Values

#### Readiness / Decision

| Context                    | Values                                                                 |
| -------------------------- | ---------------------------------------------------------------------- |
| Nomination decision        | `nominate`, `conditional_nomination`, `hold`                           |
| Readiness status           | `ready`, `at_risk`, `not_ready`                                       |
| Batch disposition          | `accept_partial_hold_variance`, `release_full_invoice`, `reject_batch`, `manual_recount_required` |
| AP action                  | `pay_now`, `defer`, `hold`, `void`, `release_invoice`, `keep_invoice_on_hold` |
| Receiving action           | `record_shortage_follow_up`, `no_receiving_action`, `reject_all_units` |
| Supplier action            | `request_credit_or_remaining_delivery`, `no_supplier_action`, `supplier_debit_for_damage` |
| Release decision (AP)      | `release_net_after_approved_chargeback`, `hold_missing_receipt`, `hold_pending_quality_chargeback` |
| Change-order decision      | `release_amendment`, `hold_for_budget`, `hold_for_approval`, `hold_for_supplier_risk`, `hold_for_budget_and_approval`, `reject_contract_mismatch` |
| Overall readiness          | `ready`, `at_risk`, `not_ready`                                       |

#### Blocker Codes (Sourcing Nomination)

| Code                    | Condition                                                              |
| ----------------------- | ---------------------------------------------------------------------- |
| `missing_contract`      | No active contract links supplier to SKU                               |
| `supplier_watch`        | Supplier risk rating is "watch" (no open severe event)                 |
| `open_supplier_risk`    | ≥1 open vendor risk event for the supplier                            |
| `ap_hold`               | Invoice status is on hold (not paid/approved)                          |
| `pending_receipt`       | No receipt exists for the PO as of the as-of date                      |
| `late_due_date`         | PO due date is before the as-of date                                   |
| `none`                  | No blockers                                                            |

#### Exception Codes (Receiving)

| Code                          | Condition                                   |
| ----------------------------- | ------------------------------------------- |
| `INVOICE_QTY_EXCEEDS_RECEIPT` | Billed quantity > received quantity         |
| `PARTIAL_RECEIPT`             | Received < ordered on any line              |
| `SUPPLIER_WATCH_RISK`         | Supplier has open vendor risk events        |
| `PRICE_MISMATCH`              | PO unit price ≠ contract unit price         |
| `DAMAGE_REJECTION`            | Rejected quantity > 0 on any line           |
| `NO_EXCEPTION`                | None of the above apply                     |

#### Receiving Exception Codes (AP Release)

| Code                        | Meaning                                           |
| --------------------------- | ------------------------------------------------- |
| `Underage Quantity`         | Received less than ordered; chargeback filed      |
| `Severe Unmatched Quantity` | Large discrepancy between received and ordered    |
| `Inspection Hold`           | Receipt held pending quality inspection           |
| `AP Quantity Variance`      | Invoice quantity differs from receipt quantity    |

#### Chargeback / Resolution Status

| Chargeback Status           | Resolution Status                  |
| --------------------------- | ---------------------------------- |
| `approved`                  | `net_release_ready`                |
| `pending_quality_review`    | `hold_for_quality_review`          |
| `not_applicable`            | `accepted_no_receiving_exception`  |
| (no receipt)                | `missing_receipt`                  |

#### Supplier Risk

| Field        | Values                                        |
| ------------ | --------------------------------------------- |
| `status`     | `active`, `inactive`, `suspended`             |
| `risk_rating`| `low`, `watch`, `high`, `critical`            |
| `severity`   | `low`, `medium`, `severe`, `critical`         |
| Event status | `open`, `monitoring`, `closed`                |

#### Contract

| Field         | Values                                  |
| ------------- | --------------------------------------- |
| `status`      | `active`, `expired`, `cancelled`        |
| `price_type`  | `fixed`, `variable`, `tbd`              |

#### PO / Requisition / Receipt / Invoice Status

| Entity       | Common statuses                                              |
| ------------ | ------------------------------------------------------------ |
| PO           | `open`, `closed`, `cancelled`, `partially_received`          |
| Requisition  | `submitted`, `approved`, `rejected`, `pending`               |
| Receipt      | `posted`, `pending_inspection`, `accepted`, `rejected`       |
| Invoice      | `submitted`, `approved`, `paid`, `on_hold`, `void`           |
| Payment      | `scheduled`, `completed`, `failed`                           |
| Approval     | `submitted`, `approved`, `rejected`                          |

## Process-Specific Computation Details

### Sourcing Nomination

**Budget headroom**:
```
headroom = budget_snapshot.budget_cap - budget_snapshot.committed_amount
```

**Overall program readiness**: The worst status across all nomination lines:
- `not_ready` if any line is `not_ready`
- `at_risk` if any line is `at_risk` and none are `not_ready`
- `ready` only if all lines are `ready`

**Committee action next_owner routing**:
1. If any line has `ap_hold` as the most severe unresolved blocker → `ap_team`
2. If any line has `missing_contract` → `buyer`
3. If any line has `open_supplier_risk` → `quality_ops`
4. If budget headroom is negative → `finance_ops`
5. Otherwise → `program_owner`

### Receiving Closeout

**Receipt completion ratio**: `received_qty / ordered_qty` rounded to 4 decimal places. If `ordered_qty == 0`, the ratio is `0.0`.

**Goods value**:
```
received_goods_value = sum(received_qty * po_unit_price for each line)
unreceived_goods_value = sum((ordered_qty - received_qty) * po_unit_price for each line)
```

**Invoice totals**: Use the invoice record's `subtotal`, `freight`, `tax`, and `total` fields directly from the API. Validate that `subtotal + freight + tax ≈ total` (within rounding tolerance).

### Change-Order Review

**Contract noncancelled subtotal**: Sum of `quantity * unit_price` for all POs under the contract where `status != "cancelled"`. Use the contract's `unit_price`.

**Budget max quantity**:
```
max_qty = floor(remaining_budget / (unit_price * (1 + tax_rate/100)))
```

**Decision matrix** (priority order — first match wins):
| ceiling_ok | budget_ok | approval_ok | supplier_risk_ok | decision                        |
|:----------:|:---------:|:-----------:|:----------------:| ------------------------------- |
| false      | *         | *           | *                | `reject_contract_mismatch`      |
| true       | false     | false       | *                | `hold_for_budget_and_approval`  |
| true       | false     | true        | true             | `hold_for_budget`               |
| true       | true      | false       | true             | `hold_for_approval`             |
| true       | true      | true        | false            | `hold_for_supplier_risk`        |
| true       | true      | true        | true             | `release_amendment`             |

### AP Release Review

**Chargeback amount**:
```
amount = chargeback.basis_quantity * chargeback.unit_cost
```

**Net release**:
```
net = invoice.total - approved_chargeback_amount - pending_chargeback_amount
```
If decision is `hold_*`, `net_release_amount` is `0.0`.

**Receipt-to-PO matching**:
- A receipt belongs to a PO if `receipt.po_id == po.id`.
- `receipt_ids_in_scope`: Receipts for the PO that appear in the target receipt ID list.
- `excluded_same_po_receipt_ids`: Receipts for the same PO that are NOT in the target list (e.g., duplicates held for separate invoices).

**Summary totals**:
- `approved_chargeback_total`: Sum of approved chargeback amounts across all invoices.
- `pending_chargeback_total`: Sum of pending chargeback amounts across all invoices.
- `net_release_total`: Sum of net release amounts for `release_*` decisions only (hold decisions contribute `0.0`).

## Evidence and Traceability

Every answer must be traceable to source records. When the template includes an `evidence` or `endpoint_record_ids` block:

- List every API record ID that contributed to the analysis (POs, receipts, invoices, contracts, approvals, risk events, budget snapshots, supplier records).
- List every local payload file that was consulted (memos, chargeback registers, request notes).
- Do not include IDs from records that were fetched but not used in the final answer.

## Common Pitfalls

1. **Forgetting the as-of date filter**: Always pass `?end={as_of_date}` to date-scoped collections. Records dated after the cutoff must not influence the answer.
2. **Mixing up ordered vs received vs billed quantities**: These come from different records (PO for ordered, receipt for received, invoice for billed). Never assume they are equal.
3. **Double-counting chargebacks**: A chargeback applies to exactly one `(invoice_id, po_id, receipt_id)` tuple. Sum only the chargebacks matching the invoice under review.
4. **Tax on freight**: Tax applies to the line subtotal, not to freight, unless the memo explicitly states otherwise.
5. **Cancelled POs in headroom**: Exclude cancelled POs when computing contract noncancelled subtotal and budget committed amounts.
