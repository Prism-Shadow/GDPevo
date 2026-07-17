# ProcureOps Task Group 006 — Reusable Solve Skill

## Environment & Sources

1. **API base URL**: Use the environment-provided `GDPEVO_ENV_BASE_URL`. Never use localhost unless that is the actual remote target.
2. **API is source of truth**: Task memos/payloads provide anchors (IDs, scope) and business rules. Operational data (quantities, prices, statuses, dates, risk events) comes from the API only.
3. **Endpoints used**: `/programs`, `/suppliers`, `/items`, `/contracts`, `/purchase_requisitions`, `/purchase_orders`, `/receipts`, `/ap/invoices`, `/ap/payments`, `/approval_events`, `/budget_snapshots`, `/vendor_risk_events`.
4. **API data is flat**: All endpoints return full result sets — use client-side filtering, not query params.

## Field Conventions

5. **Sort ascending** for: SKU lists, ID lists (PO, receipt, invoice, supplier, risk event), nomination lines (by SKU), invoice_decisions (by invoice_id), vendor_balances (by supplier_id), program_summary (by program_id), payment hold/release queues.
6. **List fields are sets**: Unless sorting is specified in the template, the evaluator sorts. Still produce deterministic output.
7. **USD to cents**: All currency amounts rounded to 2 decimal places with standard rounding. Include `.00` suffix for whole-dollar values.
8. **Precision by field**: Ratios (receipt_completion_ratio) to 4 decimal places; percentages (quantity_variance_pct) to 1 decimal.
9. **task_id format**: Use the exact value from the answer template's `required_value` or `task_id` field. Match the template convention.

## Date & Time Filtering

10. **as_of_date is a hard cutoff**: Exclude receipts, invoices, risk events, and approval events dated after the as_of_date.
11. **Receipts dated after as_of_date are invisible**: They don't count toward receipt_evidence_ids or quantity_received calculations.
12. **Scheduled payments through the cutoff**: Only payments with `scheduled_date` on or before the stated cutoff date (e.g., 2026-06-30) count.

## Arithmetic & Business Rules

### Budget & Contract
13. **Budget headroom** = `budget_cap` − `committed_amount` (from program endpoint or budget snapshot — they agree).
14. **Contract noncancelled_subtotal**: Sum `subtotal` of all POs under the contract with any status EXCEPT `cancelled`.
15. **Contract ceiling exposure**: Before tax and freight. Only the line subtotal counts against the contract ceiling.
16. **Program budget exposure**: Line subtotal plus estimated tax. Freight only if the change memo/payload explicitly provides it.
17. **Tax rate**: From the task memo's `tax_rate_percent` or business_controls (typically 7.25%). Apply to subtotal, round to cents.
18. **requested_total** = requested_subtotal + requested_tax (no freight unless provided).
19. **budget_after_change** = remaining_budget − requested_total.
20. **max_quantity_with_current_budget** = floor(remaining_budget / (unit_price × (1 + tax_rate))).

### Receipt & Invoice Reconciliation
21. **Received vs ordered**: `short_qty_vs_po = ordered_qty − received_qty` (positive = shortage).
22. **Billed vs received**: `unreceived_billed_qty = billed_qty − received_qty`.
23. **Receipt completion ratio** = received_qty / ordered_qty (to 4 decimal places).
24. **Three-way match**: PO unit_price vs contract unit_price vs invoice unit_price. `contract_price_match = true` when contract and invoice prices agree.
25. **Invoice exception codes**: Derive from discrepancies — `INVOICE_QTY_EXCEEDS_RECEIPT` when billed > received; `PARTIAL_RECEIPT` when PO status signals partial; `SUPPLIER_WATCH_RISK` when supplier has watch rating with open risk; `PRICE_MISMATCH` when prices differ; `DAMAGE_REJECTION` when rejected_qty > 0.

### Payment & Close
26. **opening_balance for close slices**: Use the memo-stated value (often 0.00 for target-invoice-only slices).
27. **scheduled_payments**: Sum of payment amounts for TARGET invoices only, scheduled through the cutoff date. Do NOT include payments for non-target invoices even if the same supplier.
28. **vendor close_balance** = opening_balance + invoice_total − scheduled_payments.
29. **net_balance_impact** (per invoice) = invoice_total − scheduled_payment_amount.
30. **total_close_balance** = sum of vendor close_balances across the slice.
31. **held_invoice_total**: Sum invoice_total for invoices with hold_decision = HOLD.
32. **releasable_invoice_total**: Sum invoice_total for invoices with hold_decision = RELEASE.
33. **balance_status**: `FULLY_SCHEDULED` when close_balance = 0; `OPEN_HELD` when held_invoice_total > 0; `OPEN_APPROVED` when releasable but not yet scheduled.

### Chargebacks & Release
34. **Chargeback amount** = basis_quantity × unit_cost (from the chargeback register, not the API).
35. **net_release_amount** = invoice_total − approved_chargeback_amount (when releasing net of chargeback).
36. **approved_chargeback_total** = sum of approved_chargeback_amount across all invoices.
37. **pending_chargeback_total** = sum of pending_chargeback_amount across all invoices.

### Supplier Risk
38. **Risk events are supplier-scoped**: Include all `open` or `monitoring` events for the supplier, regardless of which PO/SKU they relate to.
39. **Severe events**: Only events with `severity: "high"` count as severe. `medium` and `low` do not.
40. **Supplier risk_rating contexts**: `watch` → `supplier_watch` blocker. `high` → supplier risk blocker. Both are advisory unless a severe open event exists.

### Approval
41. **Check only `good_actions`**: From business_controls. Normally only `"approved"`. `"submitted"`, `"returned"`, `"escalated"` do NOT count as approved.
42. **Latest event only**: Sort by event_date descending; the most recent event's action determines approval_ok.

### Nomination & Package
43. **Package line SKUs**: From the memo anchors, sorted ascending.
44. **package_po_ids**: Only the anchor POs named in the memo, not all program POs for the SKU.
45. **commercial_basis_id**: The contract_id from the PO, or `null` if the PO has no contract.
46. **Blockers for nomination lines**: Check each of: `missing_contract` (no active contract), `supplier_watch` (risk_rating=watch), `open_supplier_risk` (any open risk event), `ap_hold` (invoice status=on_hold with hold_code), `pending_receipt` (received < ordered), `late_due_date` (PO due_date < as_of_date).
47. **overall_readiness**: `not_ready` if any line is `not_ready`; `at_risk` if any line is `at_risk` but none `not_ready`; `ready` only if all lines are `ready`.

### Change Control
48. **Decision precedence**: Check contract → budget → approval → supplier risk. Combine blockers if multiple fail.
49. **Contract check uses the contract's own POs**: Noncancelled_subtotal and included_po_ids are scoped to the specific contract_id.
50. **Program budget check**: Uses the program's budget_snapshot.

### Receiving Exceptions
51. **exception_codes**: `Underage Quantity` (received < ordered), `AP Quantity Variance` (billed ≠ received/ordered), `Inspection Hold` (receipt status = inspection_hold), `Severe Unmatched Quantity` (large billed vs received gap).
52. **chargeback_status**: From the local chargeback register: `approved`, `pending_quality_review`, or `not_applicable`.
53. **resolution_status**: `net_release_ready` when approved chargeback covers the gap; `hold_for_quality_review` when pending; `accepted_no_receiving_exception` when no exceptions; `missing_receipt` when no receipt exists.

## Output Schema Pitfalls

54. **Do not fabricate IDs**: Every ID in the answer must come from the API responses or task payloads.
55. **Empty arrays not null**: Use `[]` for empty ID lists, never `null`.
56. **Booleans**: Use JSON `true`/`false`, not strings.
57. **Null vs empty**: `null` for missing references (e.g., no contract, no receipt, no hold_code). `[]` for empty lists.
58. **Evidence section**: Include the actual API record IDs you queried (POs, receipts, invoices, contracts, risk events). Also list the task payload files reviewed.
59. **reason_codes**: Only include codes that genuinely apply. Use alphabetical sort.

## Task-Specific Patterns

60. **Receiving closeout (train_002)**: One batch, one PO, one receipt, one invoice. Focus on the quantity variance and supplier risk context. Exception codes include the PO-level status flags.
61. **AP close desk (train_003)**: Slice is limited to named invoices. Opening balances are 0.00 for the slice. Scheduled payments only count for target invoices through the cutoff window.
62. **Change control (train_004)**: Separate contract ceiling check (before tax) from program budget check (after tax). Contract noncancelled_subtotal is across all non-cancelled POs under that contract.
63. **AP release (train_005)**: Chargeback amounts from the local register. Exclude receipts for the same PO that aren't linked to the invoice (`excluded_same_po_receipt_ids`). Followup actions should include `hold_luma_duplicate_receipt_for_separate_invoice` when a receipt exists for the PO but the invoice doesn't reference it.
