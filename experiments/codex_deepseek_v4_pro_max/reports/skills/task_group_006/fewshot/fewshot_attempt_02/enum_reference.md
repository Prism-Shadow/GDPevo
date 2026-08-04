# ProcureOps Enum Reference

Canonical allowed values for every enumerated field observed across task types.

## Program / Nomination

| Field | Values |
|---|---|
| `overall_readiness` | `ready`, `at_risk`, `not_ready` |
| `nomination_decision` | `nominate`, `conditional_nomination`, `hold` |
| `readiness_status` | `ready`, `at_risk`, `not_ready` |
| `blocker_codes` | `missing_contract`, `supplier_watch`, `open_supplier_risk`, `ap_hold`, `pending_receipt`, `late_due_date`, `none` |
| `next_owner` | `buyer`, `finance_ops`, `quality_ops`, `program_owner`, `ap_team` |
| `send_to_committee` | `yes`, `no` |

## Receiving / Closeout

| Field | Values |
|---|---|
| `batch_disposition` | `accept_partial_hold_variance`, `release_full_invoice`, `reject_batch`, `manual_recount_required` |
| `ap_action` | `keep_invoice_on_hold`, `release_invoice`, `void_invoice` |
| `receiving_action` | `record_shortage_follow_up`, `no_receiving_action`, `reject_all_units` |
| `supplier_action` | `request_credit_or_remaining_delivery`, `no_supplier_action`, `supplier_debit_for_damage` |
| `exception_codes` (receiving) | `INVOICE_QTY_EXCEEDS_RECEIPT`, `PARTIAL_RECEIPT`, `SUPPLIER_WATCH_RISK`, `PRICE_MISMATCH`, `DAMAGE_REJECTION`, `NO_EXCEPTION` |

## AP Close / Payments

| Field | Values |
|---|---|
| `hold_decision` | `HOLD`, `RELEASE` |
| `reason_codes` (AP) | `APPROVED_THREE_WAY_MATCH`, `NO_RECEIPT`, `QTY_VARIANCE`, `SCHEDULED_PAYMENT_FOUND` |
| `balance_status` | `OPEN_HELD`, `OPEN_APPROVED`, `FULLY_SCHEDULED` |

## Change Control / Amendments

| Field | Values |
|---|---|
| `decision` | `release_amendment`, `hold_for_budget`, `hold_for_approval`, `hold_for_supplier_risk`, `hold_for_budget_and_approval`, `reject_contract_mismatch` |
| `required_actions` | `obtain_final_requisition_approval`, `raise_budget_exception_or_reduce_quantity`, `resolve_supplier_risk_hold`, `none` |

## AP Release / Chargebacks

| Field | Values |
|---|---|
| `decision` (release) | `release_net_after_approved_chargeback`, `hold_missing_receipt`, `hold_pending_quality_chargeback` |
| `primary_reason` | `approved_qty_chargeback`, `approved_ap_quantity_variance`, `no_receipt_on_po`, `inspection_hold_pending_chargeback` |
| `exception_codes` (receiving exception) | `Underage Quantity`, `Severe Unmatched Quantity`, `Inspection Hold`, `AP Quantity Variance` |
| `chargeback_status` | `approved`, `pending_quality_review`, `not_applicable` |
| `resolution_status` | `net_release_ready`, `hold_for_quality_review`, `accepted_no_receiving_exception`, `missing_receipt` |
| `authoritative_sources` | `procureops_po_records`, `procureops_receipt_records`, `procureops_ap_records`, `local_chargeback_register` |
| `supporting_only_sources` | `ap_release_request_note`, `stale_po73xx_alias_note` |
| `followup_actions` | action strings describing receiving/AP follow-up steps required after release decisions (e.g., request missing receipts, route quality reviews, post chargeback netting, handle duplicate receipts) |

## Core Entity Statuses

| Entity | Statuses |
|---|---|
| Purchase Order | `open`, `partial_receipt`, `fully_received`, `cancelled`, `closed` |
| Receipt | `accepted`, `pending_inspection`, `rejected` |
| Invoice (AP) | `approved`, `on_hold`, `paid`, `void` |
| Payment | `scheduled`, `paid` |
| Contract | `active`, `expired`, `terminated` |
| Supplier | `active`, `inactive`, `suspended` |
| Approval | `submitted`, `approved`, `rejected` |
| Risk Event | `open`, `monitoring`, `closed`, `resolved` |
| Risk Severity | `low`, `medium`, `high`, `critical` |
| Supplier Risk Rating | `clear`, `watch`, `severe` |
| Requisition | `draft`, `submitted`, `approved`, `rejected` |
