# MedBridge Sales Ops Reconciliation Skill

Use this skill for task_group_002 sales-ops quote, RFQ, freight, and account-reconciliation tasks. Return only JSON matching the provided answer template.

## API Sources

- Start from the task-provided API base URL. Confirm available routes with `GET /api` if needed.
- Use `GET /api/search?q=<id-or-name>` to discover linked records, then fetch specific records from:
  - `/api/customers/<customer_id>`
  - `/api/products/<product_code>`
  - `/api/rfqs/<rfq_id>`
  - `/api/quotes/<quote_id>`
  - `/api/freight-quotes` or `/api/freight-quotes/<freight_id>`
  - `/api/policies`
  - `/api/opportunities/<opportunity_id>`
  - `/api/invoices`, `/api/payments`, `/api/revenue-journals`
  - `/api/events`, `/api/vouchers`

## Source Precedence

- The prompt selects the target IDs, current/as-of date, and requested output shape.
- API records are the business source of truth for customer names, statuses, quantities, dates, prices, freight, invoices, journals, events, and vouchers.
- Quote records and quote line items override stale RFQs, prior quantities, and prior unit prices.
- Product catalog tiers override old quoted unit prices; choose the tier whose `min_qty <= quantity <= max_qty`, treating `max_qty: null` as open-ended.
- Policies override customer defaults when directly applicable; otherwise use the customer payment profile.
- The answer template controls field names, enum values, ID conventions, nullability, and whether summary strings or booleans are required.

## Quote And RFQ Rules

- For product quotes, compute `exw_total_usd = confirmed_quantity * unit_price_usd` from the active catalog tier. Keep money as numbers at cent precision.
- For module RFQs, quote requested module lines only. Do not split modules into component SKUs unless the prompt explicitly asks for component pricing.
- Indicative RFQs without a confirmed destination are EXW only, exclude freight, and use the template's EXW-only convention.
- Standard catalog pricing validity is 30 calendar days from quote date unless the task or policy says otherwise.
- New NGO clients use `PREPAY_100`. Recurring NGO accounts generally use `NET_30_AFTER_PO`. Other recurring accounts should use the customer payment profile unless a policy says otherwise.

## Freight Rules

- Match freight by `quote_id` and reject distractors with wrong destination, shipment size, status, or validity.
- Include current requested freight modes when the template asks for a comparison. If a linked option is stale/expired but requested for comparison, include it with stale/invalid flags and warnings.
- `grand_total_usd = exw_total_usd + freight_cost_usd`.
- A freight source is stale when `status` is `stale`/mismatch or `valid_until` is before the quote date. It is valid on the quote date only when active and `valid_until >= quote_date`.
- All freight rates require reconfirmation before final order.
- Never recommend stale or expired freight. Recommend the lowest-cost valid mode that satisfies cold-chain, route-risk, and timing constraints; air is not automatic when an active sea option is valid and acceptable.
- Preserve route risk from freight records as uppercase template values such as `LOW`, `MEDIUM`, or `HIGH`; use explicit warning text for expired road lanes, high border/customs risk, cold-chain shelf-life review, or other route notes.

## Account Reconciliation Rules

- Reconcile opportunities by `opportunity_id` and `customer_id`; ignore similarly named distractors.
- Map opportunity stage to template enums: `closed_won -> WON`, open stages to `OPEN`, lost stages to `LOST`.
- `phase_total_amount` is the sum of opportunity phases. `opportunity_matches_phase_total` is true only when that sum equals the won amount.
- Use posted payments or invoice `paid_amount_usd` for paid totals; use invoice/opportunity outstanding amounts for outstanding balance and collection amounts.
- Follow the template's milestone ID convention. If it declares `MS1`, `MS2`, `MS3`, map phases in ascending phase order to those IDs. Otherwise use stable source phase IDs consistently unless the template explicitly asks for invoice IDs.
- Invoice/payment status mapping:
  - paid invoice and fully posted payment -> `PAID`
  - partial paid amount -> `PARTIAL`
  - open/unpaid/overdue invoice with no payment -> `UNPAID` or template `OPEN` for invoice-state fields
  - void/cancelled -> `VOID`; missing records -> `UNKNOWN`
- Revenue recognition:
  - Paid, completed milestone with a posted revenue journal -> `RECOGNIZED`.
  - Paid, completed milestone without a posted journal -> `MISSING_REVENUE_JOURNAL` or `REQUIRED_MISSING`, per template.
  - Unpaid or not-yet-complete milestone -> `NOT_REQUIRED_UNPAID`.
- Accounting action for a missing paid milestone journal is debit `DEFERRED_REVENUE`, credit `IMPLEMENTATION_SERVICES_REVENUE`, owner `ACCOUNTING`, amount equal to the paid milestone amount.
- Use the prompt's current/as-of business date. Future unpaid milestones are monitored as not due; due or overdue unpaid milestones get collection action according to the template.

## Event And Voucher Rules

- Link events and vouchers by event ID, voucher code, customer ID, and opportunity ID.
- Map event statuses to template enums: scheduled/confirmed -> `SCHEDULED` when the template has scheduled, live/active -> `ACTIVE`, completed -> `COMPLETED`, cancelled -> `CANCELLED`.
- Map voucher status to uppercase template enums. Use `max_redemptions` as max uses.
- Voucher discount fields usually take the numeric discount value from the voucher record, even when the source field is a percent.
- For invite follow-ups, use the event's primary contact and customer ID; prefer `ACCOUNT_MANAGEMENT` when the event record names Account Management as follow-up owner.

## Output Conventions And Pitfalls

- Return valid JSON only, with no markdown or explanatory text.
- Use ISO `YYYY-MM-DD` dates. Use `null` only when the template permits it.
- Use template enum strings, not raw API status strings, unless a field explicitly asks for the raw record value.
- Customer names in prompts may be aliases; resolve the canonical customer name and payment profile from the customer record.
- Search results often include distractors, superseded RFQs, stale freight, old quantities, and unrelated vouchers/events. Filter by all linked IDs before calculating.
- Do not recommend an option merely because it has the lowest nominal cost; validity, cold-chain support, and route risk come first.
- Do not create extra fields. Keep arrays in the order requested by the template or source phases/modules.
