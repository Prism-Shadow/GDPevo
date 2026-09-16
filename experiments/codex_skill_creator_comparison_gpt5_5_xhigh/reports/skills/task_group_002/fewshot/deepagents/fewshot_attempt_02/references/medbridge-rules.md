# MedBridge Rules

## Collections And Links

Use these read-only collections: `customers`, `products`, `rfqs`, `quotes`, `freight-quotes`, `policies`, `opportunities`, `invoices`, `payments`, `revenue-journals`, `events`, and `vouchers`.

Important link fields:

- Quote tasks: `quotes.id` -> `freight-quotes.quote_id`; `quotes.customer_id` -> `customers.id`; quote `line_items[].product_code` -> `products.code`.
- RFQ tasks: `rfqs.customer_id` -> `customers.id`; `rfqs.requested_modules[].product_code` -> `products.code`.
- Reconciliation tasks: `opportunities.id` -> invoice/payment/journal/event/voucher `opportunity_id`; invoice `id` -> payment/journal `invoice_id`; phase `phase_id` links opportunity phases to invoices and journals.
- Events and vouchers: `events.voucher_code` -> `vouchers.code`; `vouchers.event_id` -> `events.id`.

## Quote And RFQ Pricing

Choose the current commercial record by explicit quote or RFQ ID. When only customer/product details are supplied, search and then verify that customer, product, quote date, status, and requested quantity match the prompt.

For each product line:

1. Use the prompt-confirmed quantity if stated; otherwise use the current quote/RFQ line quantity.
2. Select the catalog price tier where `min_qty <= quantity` and `quantity <= max_qty`, treating null `max_qty` as no upper limit.
3. Set unit price, lead time, shelf life, article number, and product code from the selected product/tier.
4. Compute `line_total = quantity * unit_price` and `exw_total` or `grand_total` as the sum of line totals.

RFQ/module quote tasks should remain at requested module/product-code granularity. Do not split `components` or component distractor notes into separate output lines.

Use policy records and customer payment profile for quote controls:

- New NGO or new-client-review payment profile: `PREPAY_100`.
- Recurring active accounts with net profile: use the customer `payment_profile`, usually a net-after-PO code.
- Catalog quote validity: 30 calendar days from quote date when the template asks for offer validity days.
- Indicative quotes without a confirmed destination: EXW only, freight excluded.
- EXW excludes freight unless the prompt/template asks for separate freight options.

## Freight Options

Start from freight records whose `quote_id` equals the selected quote ID. Exclude obvious distractors: IDs or notes marked as distractor, old, wrong-size, prior-count, benchmark-only, `mismatch`, or destination-only placeholders unrelated to the current quote. Keep stale canonical options when the template asks for validity or stale-source status.

For each included freight option:

- Normalize `mode` to uppercase.
- Use `cost_usd` for freight cost.
- Compute `grand_total = exw_total + cost_usd`.
- Validity is valid when `status` is active and `valid_until` is on or after the quote date/business date. It is stale when `status` is stale or `valid_until` is before that date.
- `source_is_stale` is true for stale status or expired validity.
- Use `transit_days_text` when the template expects text with units. Use `"{transit_days_min}-{transit_days_max}"` when the target template uses compact range strings.
- Use `route_risk` uppercased for broad route-risk fields.
- For customs/border-specific fields, report LOW unless `risk_notes` mention customs or border; then use the uppercased risk level.
- For risk flags, use `NONE` for low risk, `MEDIUM_BORDER_RISK` for medium customs/border risk, and `HIGH_BORDER_RISK` for high customs/border risk when those values fit the template.

Recommended mode:

- Prefer the lowest total valid option that is not stale and not high customs/border risk.
- If the quote has a delivery need-by date, include product lead time plus max transit days and choose the cheapest valid mode that can meet the deadline.
- If the cheapest option is stale, expired, mismatched, or high-risk, choose the next valid lower-risk option.
- Freight reconfirmation is required when freight is included and policy says freight must be reconfirmed at final order, or when any included option is stale/expired.

## Opportunity Reconciliation

Fetch the opportunity, customer, all invoices, payments, revenue journals, event, and voucher linked by `opportunity_id` and `customer_id`.

Normalize stages:

- `closed_won` -> `WON`
- open proposal or negotiation states -> `OPEN`
- closed lost states -> `LOST`

Milestone rules:

- Sort opportunity phases in source order or by phase suffix.
- Use template-required milestone IDs. If the template uses `MS1 | MS2 | MS3`, map the sorted phases to `MS1`, `MS2`, `MS3`.
- Phase total is the sum of opportunity phase amounts. Opportunity matches phase total when that sum equals won amount.
- Use invoice amounts, paid amounts, outstanding amounts, due dates, and status from matching invoices. Cross-check posted payments when needed.
- For paid invoices, output due date as null unless the template explicitly requires original invoice due dates.
- Payment status: PAID when fully paid or outstanding is zero; PARTIAL when some but not all paid; UNPAID when no payment; UNKNOWN only when records are missing.
- Invoice state: paid -> PAID; unpaid or overdue -> OPEN when the enum uses invoice-state wording; draft/void map only if the template allows those values.

Revenue recognition:

- A paid completed milestone requires a posted revenue journal linked by invoice or phase.
- Recognized if a posted journal exists for the paid milestone.
- Missing when the milestone is paid and complete but no posted journal exists.
- Not required for unpaid milestones.
- Sum recognized amount from posted journals for the selected opportunity.
- Overall recognition is complete when every paid milestone has a posted journal, missing when at least one paid milestone lacks one, and not required when no milestone is paid.

## Accounting, Collection, Event, And Voucher Actions

Select action enum values from the target template.

Accounting:

- If a paid milestone lacks a revenue journal, choose the record-revenue action for that milestone, amount equal to the paid milestone amount, debit deferred revenue, credit implementation services revenue, owner accounting.
- If all paid milestones are recognized, choose verify-only or no-action according to the available enum and prompt wording.

Collection:

- Create a collection or monitoring task for unpaid outstanding milestones when the template asks for follow-ups.
- If due date is after the business/as-of date, monitor unpaid not due. If due date is on/before the business date or invoice status is overdue, send/collect.
- Use the account contact named in the prompt or opportunity/customer record.

Event and voucher:

- Prefer explicit event ID and voucher code from the prompt. Otherwise use the linked event/voucher for the opportunity.
- Normalize event status to template enums: scheduled or confirmed -> SCHEDULED; live or active -> ACTIVE; completed -> COMPLETED; cancelled -> CANCELLED.
- Normalize voucher status by uppercasing when the template uses enum values.
- Use voucher `discount_percent` for discount fields unless the template clearly asks for a currency amount.
- Use `max_redemptions` for max-uses fields.
- For upcoming scheduled/confirmed events with an active voucher, choose the send-invite action when the prompt asks to route an invite.
