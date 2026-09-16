# MedBridge Sales Ops Policy Rules

Every policy record from `GET /api/policies` encodes a business rule. Apply these
in every quote, freight, and reconciliation workflow. Below are the reusable
derivations from the policy records.

## Payment Terms by Customer Segment

| Customer segment / situation | Payment terms |
|---|---|
| Recurring NGO (`recurring_ngo`) | `NET_30_AFTER_PO` |
| New NGO (`new_ngo`, `prospect`) | `PREPAY_100` |
| Recurring commercial (`recurring_commercial`) | From `payment_profile` field |
| Government program (`government_program`) | From `payment_profile` field |
| Implementation services (`implementation_services`) | From `payment_profile` (`MILESTONE_BILLING`) |
| Distributor | From `payment_profile` field |

To determine terms: check the customer's `payment_profile` field. If it is
`NEW_CLIENT_REVIEW` or the customer is a prospect, default to `PREPAY_100`.
Otherwise use the value of `payment_profile` directly.

## Quote Scope Rules

**EXW baseline**: EXW excludes freight, insurance, import duty, customs clearance,
and last-mile handling. Freight is provided as separate options.

**Indicative quotes without destination**: When an RFQ has no confirmed destination
(e.g., "Destination pending donor allocation"), the quote must be EXW-only and
exclude freight entirely. Set `freight_excluded: true`.

**Module granularity**: When quoting an RFQ with module-level products (IEHK,
field-clinic, cholera), quote at the module line level. Do not split into
component SKUs even if `components[]` or `component_composition_distractors[]`
are present. The `POL-MODULE-GRANULARITY` policy enforces this. Only break into
components if the customer explicitly asks for component-level pricing.

## Freight Rules

**Reconfirmation**: All freight rates must be reconfirmed at final order.
Set `freight_reconfirmation_required: true` whenever freight options are presented.

**Validity**: A freight option is valid for a given `quote_date` only when
`valid_until >= quote_date`. If `valid_until < quote_date`, the freight quote
is expired/stale regardless of its `status` field.

**Risk routing**: Use `route_risk` (low/medium/high) and `risk_notes` to flag
concerns. Road freight with `route_risk: high` should carry a warning.
Stale road quotes should be excluded from recommendations.

**Recommended mode**: Prefer the lowest-risk, valid option that balances cost
and transit time. SEA is often the default recommendation when valid and
low-risk. If the customer has a delivery deadline, factor that in.

## Offer Validity

Catalog quote pricing is valid for 30 calendar days from `quote_date`.
Set `offer_validity_days: 30` unless a different period is specified.
Freight validity may expire sooner than the catalog offer.

## Revenue Recognition (Implementation Services)

When an opportunity is `closed_won` with milestone-service billing:

1. For each phase that is both completed (`completion_date` present) *and* paid
   (payment exists for the invoice), check `GET /api/revenue-journals` for a
   matching journal entry (by `phase_id` or `invoice_id`).
2. If a journal exists: `RECOGNIZED`
3. If a journal is missing: `MISSING_REVENUE_JOURNAL` (requires accounting action:
   debit Deferred Revenue, credit Implementation Services Revenue)
4. If the phase is unpaid: `NOT_REQUIRED_UNPAID`

## Collection and Follow-up Rules

**Unpaid milestones**: When an invoice is `unpaid` or `overdue`:
- If the due date is in the future: `MONITOR_UNPAID_NOT_DUE`
- If the due date is in the past (overdue): `SEND_COLLECTION_NOTICE`

**Event invitations**: When an event is linked to a won opportunity and is
`scheduled` or `confirmed` with a future date, generate a `SEND_EVENT_INVITATION`
task. Include the voucher code and event details.

## New Client Handling

For prospect customers with no credit history:
- Payment terms: `PREPAY_100`
- WHO documentation may be required for IEHK-style modules
- Freight may be excluded when destination is unconfirmed
