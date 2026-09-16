# MedBridge Rules

## API Sources

Use these collections as the source of truth:

- `customers`: account identity, contacts, segment, recurring/new-client indicators, payment profile.
- `products`: `code`, `article_number`, `price_tiers`, `shelf_life_months`, module `components`, physical logistics fields.
- `rfqs`: requested modules, quote date, destination, incoterm, request type, narrative.
- `quotes`: quote revision header, confirmed quantity, destination, line items, quote date, source notes.
- `freight-quotes`: freight records linked by `quote_id`; mode, cost, validity, status, risk, transit range.
- `policies`: payment terms, quote scope, module granularity, freight reconfirmation, quote validity, revenue recognition.
- `opportunities`: won/open/lost stage, phases, won amount, contact, customer, outstanding amount.
- `invoices`, `payments`, `revenue-journals`: milestone billing and recognition evidence.
- `events`, `vouchers`: invite and offer controls linked by event, voucher, customer, or opportunity.

Prefer direct IDs from the prompt. Use `/api/search?q=<text>` only for discovery, then verify with collection or detail records.

## Quote And RFQ Pricing

Select catalog pricing from `product.price_tiers`:

1. Use the prompt-confirmed quantity when given; otherwise use the quote/RFQ line quantity.
2. Select the tier where `min_qty <= quantity <= max_qty`. Treat a missing/null `max_qty` as no upper bound.
3. Use `unit_price_usd` and `lead_time_days` from the selected tier.
4. Use `shelf_life_months` and `article_number` from the product record.
5. Compute `line_total = quantity * unit_price` and `exw_total = sum(line_total)`.

For module RFQs, quote requested module codes as line items. Ignore `components` and composition distractors unless component-level pricing is explicitly requested. If the RFQ repeats the same module code, consolidate quantities before pricing.

## Quote Scope And Payment Terms

- New NGO/prospect/no-credit accounts use `PREPAY_100` when policy records indicate new-client prepayment.
- Recurring approved NGO accounts generally use `NET_30_AFTER_PO` unless a more specific restriction is present.
- If an indicative RFQ has no confirmed destination or the destination is still pending/tentative, keep the offer `EXW_ONLY`, set `freight_excluded: true`, and do not invent freight totals.
- Standard catalog offer validity is 30 days from quote date unless the API or prompt says otherwise.
- Freight rates require reconfirmation at final order when freight options are included.

## Freight Comparison

For quote revisions with freight options:

1. Filter freight records to the requested `quote_id`.
2. Exclude records marked as distractors, old benchmarks, mismatches, wrong shipment sizes, unrelated routes, or destination `"Distractor route"`.
3. Keep the current option for each requested mode. Include a stale/expired option only when it is the actual current route option that must be flagged, not when it is an old benchmark.
4. A freight option is valid on the quote date when `status` is active-like and `valid_until >= quote_date`. Mark it stale/invalid if `status` is stale/mismatch/expired or `valid_until < quote_date`.
5. Compute `grand_total = exw_total + freight.cost_usd`.
6. Use `transit_days_text` when the template shows units such as `"4-6 days"`. If the template gives an empty transit string or examples use numeric ranges, output `transit_days_min-transit_days_max` without the word `days`.
7. Map risk to template fields:
   - `risk_level`: uppercase `route_risk`.
   - `risk_flag`: `NONE` for low risk; `<LEVEL>_BORDER_RISK` for medium/high border or route risk.
   - `customs_border_risk`: use HIGH/MEDIUM only when risk notes mention customs, border, corridor, expiry, or stale source concerns. Non-border operational cautions can remain LOW if the field is specifically customs/border risk.
8. Recommend the cheapest valid low-risk mode unless a delivery deadline, shelf-life/cold-chain constraint, stale source, or high border risk makes it unsuitable. Avoid recommending stale or high-risk options solely because they are cheap. If a need-by date is present, account for product lead time plus max transit days.
9. Client warnings should be concise and mention expired/stale/high-risk freight by freight ID and date when the template has a warning field.

## Opportunity Reconciliation

Match the requested opportunity and customer first, then gather invoices, payments, revenue journals, events, and vouchers linked by opportunity ID, customer ID, invoice ID, phase ID, event ID, or voucher code.

Normalize opportunity stage:

- `closed_won` -> `WON`
- active proposal/negotiation/open stages -> `OPEN`
- closed lost/lost stages -> `LOST`

Milestones:

1. Preserve opportunity phase order.
2. Use canonical output milestone IDs `MS1`, `MS2`, `MS3`, ... when the template asks for MS-style milestones or enum values. Keep the API `phase_id` only if the template explicitly asks for raw phase IDs.
3. Match invoices by `phase_id` or `invoice_id`.
4. Use phase amount/invoice amount as the milestone amount. `phase_total_amount` is the sum of phase amounts.
5. `opportunity_matches_phase_total` is true when `won_amount_usd` equals the phase total to cents.
6. `total_paid_amount` is the sum of paid invoice amounts or posted payments, cross-checked against invoice `paid_amount_usd`.
7. `outstanding_balance` is the sum of unpaid invoice outstanding amounts, cross-checked against the opportunity outstanding amount.

Payment and invoice status:

- Payment status/state is `PAID` when paid amount equals invoice amount, `PARTIAL` when paid is positive but less than amount, and `UNPAID` when paid is zero.
- Invoice state is `PAID` for paid/settled invoices, `OPEN` for active unpaid or overdue invoices, `VOID` for void/cancelled invoices, otherwise `UNKNOWN`.
- For paid milestones, output due date as `null` unless the template explicitly wants historical invoice due dates. For unpaid milestones, use the invoice due date or the task-specific follow-up due date supplied by the source records/prompt.

Revenue recognition:

- A paid completed milestone with a posted revenue journal is `RECOGNIZED`.
- A paid completed milestone without a posted journal is `MISSING_REVENUE_JOURNAL` or `REQUIRED_MISSING`, matching the enum used by the template.
- An unpaid milestone is `NOT_REQUIRED_UNPAID`.
- Overall recognition is complete when every paid milestone has a posted journal, missing when any paid milestone lacks one, and not required only when no paid milestones require recognition.
- Recognized amount is the sum of posted revenue journal amounts linked to the opportunity.

## Follow-Up Actions

Use the template's enum vocabulary exactly.

Accounting:

- If a paid milestone is missing a required revenue journal, route an accounting action for that milestone.
- Use debit `DEFERRED_REVENUE`, credit `IMPLEMENTATION_SERVICES_REVENUE`, and owner queue `ACCOUNTING` when the template asks for accounting entry controls.
- If all paid milestones are recognized, use verify/no-action values from the template.

Collections:

- For unpaid outstanding milestones due on or before the as-of date, use a send/collect notice action when available.
- For unpaid outstanding milestones due after the as-of date, use monitor-not-due when available.
- In simpler templates, create a collection follow-up for each unpaid milestone using the contact, customer, opportunity, milestone, due date, and amount due.

Events and vouchers:

- Prefer the event/voucher IDs named in the prompt. Otherwise choose records linked to the requested opportunity/customer.
- Normalize event status to template enums: scheduled/confirmed -> `SCHEDULED` or active equivalent, live/active -> `ACTIVE`, completed -> `COMPLETED`, cancelled -> `CANCELLED`, unknown/missing -> `UNKNOWN`.
- Normalize voucher status similarly and use `discount_percent` as the numeric discount value when the template asks for voucher discount/discount amount.
- If a future scheduled event has an active voucher and the invite has not been confirmed, use the send-invite action named by the template. If the event is already active/live, prefer a verify-invite action when available.
- When a simpler follow-up task needs an event invitation due date and no date is provided, schedule it before the event rather than on the event date; three weeks before the event is the observed business cadence.

## Final JSON Checks

- Match the template object structure and array ordering.
- Use stable record IDs from the API for IDs, except canonical `MS<n>` milestone IDs when the template calls for them.
- Do not include narrative outside JSON.
- Do not include unrequested records, extra fields, or null placeholders unless the template has those fields.
