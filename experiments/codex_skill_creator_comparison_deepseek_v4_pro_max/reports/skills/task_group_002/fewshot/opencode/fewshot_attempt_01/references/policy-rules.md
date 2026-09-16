# MedBridge Policy Rules Reference

This file documents the MedBridge Sales Ops policy rules and how they apply
across the three reconciliation workflows.

## Policy list

| Policy ID | Name | Policy Area | Rule Summary | Terms Code |
|---|---|---|---|---|
| `POL-NEW-CLIENT-PAYMENT` | New client prepayment | payment_terms | New NGO clients require PREPAY_100 before production release. | `PREPAY_100` |
| `POL-RECURRING-NGO-PAYMENT` | Recurring NGO payment terms | payment_terms | Recurring NGO customers can use NET_30_AFTER_PO unless restricted grant terms say otherwise. | `NET_30_AFTER_PO` |
| `POL-INDICATIVE-EXW` | Indicative EXW quote scope | quote_scope | Indicative quotes without destination must be EXW only and exclude freight. | `EXW_ONLY_EXCLUDE_FREIGHT` |
| `POL-FREIGHT-RECONFIRM` | Freight rate reconfirmation | freight | Freight rates need reconfirmation at final order and are valid only through the freight quote valid_until date. | `RECONFIRM_AT_ORDER` |
| `POL-MODULE-GRANULARITY` | Module RFQ granularity | quote_lines | Module RFQs should be quoted at module line level unless the customer asks for component-level pricing. | `MODULE_LINES` |
| `POL-REVREC` | Milestone revenue recognition | revenue_recognition | When a milestone is complete and paid, create or verify revenue recognition from deferred revenue to income; unpaid future milestones should remain outstanding and drive collection tasks when due or overdue. | `RECOGNIZE_PAID_COMPLETE_MILESTONES` |
| `POL-QUOTE-VALIDITY` | Standard quote validity | quote_validity | Catalog quote pricing is valid for 30 calendar days from quote date; freight validity may expire sooner. | `QUOTE_VALID_30_DAYS` |
| `POL-EXW-SCOPE` | EXW commercial scope | incoterms | EXW excludes freight, insurance, import duty, customs clearance, and last-mile handling unless explicitly added as separate options. | `EXW_EXCLUSIONS` |

## Workflow applicability

### Quote Revision with Freight (Workflow 1)

- `POL-RECURRING-NGO-PAYMENT` or `POL-NEW-CLIENT-PAYMENT`: determine payment terms from the customer's `payment_profile`.
- `POL-FREIGHT-RECONFIRM`: sets `freight_reconfirmation_required` to true and validates freight quote staleness.
- `POL-EXW-SCOPE`: confirms EXW basis, freight is separate options only.
- `POL-QUOTE-VALIDITY`: 30-day pricing validity for the quote, but freight validity dates may be shorter.

### Indicative Module RFQ (Workflow 2)

- `POL-INDICATIVE-EXW`: freight is excluded; quote basis is EXW_ONLY.
- `POL-MODULE-GRANULARITY`: quote at module level, ignore component arrays.
- `POL-NEW-CLIENT-PAYMENT` or `POL-RECURRING-NGO-PAYMENT`: payment terms from the customer record.
- `POL-QUOTE-VALIDITY`: sets 30-day offer validity.

### Engagement Reconciliation (Workflow 3)

- `POL-REVREC`: drives the revenue recognition logic -- recognize completed paid milestones, leave unpaid ones outstanding, generate collection tasks for overdue unpaid milestones.
- `POL-RECURRING-NGO-PAYMENT` or equivalent: may inform payment terms if the template asks for them.

## Payment terms mapping

| Customer payment_profile | Effective terms |
|---|---|
| `NET_30_AFTER_PO` | `NET_30_AFTER_PO` |
| `NEW_CLIENT_REVIEW` | `PREPAY_100` |
| `PREPAY_100` | `PREPAY_100` |
| Any profile matching a policy `terms_code` | Use the policy's terms_code |
