# MedBridge Derivation Rules

These rules summarize reusable patterns for MedBridge Sales Ops API tasks. They are intentionally generic and should be applied to the current task records, not to remembered example values.

## Quote and RFQ Pricing

Use quote or RFQ records as the source of requested products and quantities.

- Quote revisions usually use `quotes/<id>` or `/api/search?q=<quote_id>`.
- Indicative module RFQs usually use `rfqs/<id>` or `/api/search?q=<rfq_id>`.
- For each line item, fetch the product catalog record and select the price tier whose `min_qty <= quantity <= max_qty`; treat `max_qty: null` as no upper bound.
- Use the selected tier's `unit_price_usd` and `lead_time_days`.
- Use the product record's `article_number` and `shelf_life_months` when the template asks for them.
- Compute `line_total = quantity * unit_price` and `exw_total` or `grand_total` as the sum of line totals before freight.
- Do not split module RFQs into component SKUs unless the prompt explicitly asks for component-level pricing. Product `components` and RFQ component notes are often clinical or distractor context.

Payment and scope controls:

- New NGO or new-client-review profiles generally require `PREPAY_100`.
- Recurring approved customers generally use the customer or policy payment terms, often net terms after purchase order.
- Indicative EXW quotes without a confirmed destination exclude freight and should keep freight controls set to excluded.
- Catalog quote validity is usually 30 calendar days from the quote date when the template asks for offer validity.
- If the template asks for WHO documentation or medical documentation controls, infer it from the prompt, RFQ narrative, product family, and policies rather than inventing a value.

## Freight Options

Use freight records linked to the target quote ID.

Filtering:

- Include records whose `quote_id` equals the target quote.
- Exclude obvious distractors, such as records marked as distractor routes, wrong shipment sizes, or superseded benchmark records.
- Do not exclude a stale freight record merely because it is stale if the prompt asks to flag stale or route-risk concerns. Include it with stale flags.

Derived fields:

- `freight_cost_usd` comes from `cost_usd`.
- `grand_total_usd = exw_total_usd + freight_cost_usd`.
- Use `transit_days_text` when the template expects a text range. If the template examples or field wording favor compact numeric ranges, format from `transit_days_min` and `transit_days_max`.
- A freight option is valid on the quote date when its status is active and `valid_until >= quote_date`.
- Mark stale or invalid when the status is stale, the validity date is before the quote date, or the source notes say it is stale.
- Freight reconfirmation is required when freight options are presented unless the task explicitly says freight is excluded.

Risk and recommendation:

- Normalize mode strings to the template's enum style, commonly uppercase.
- Normalize route risk to the template's enum style.
- For a generic `risk_flag`, use `NONE` for low risk and a descriptive controlled value for medium or high border/customs risk when the template provides or implies one.
- For `customs_border_risk`, distinguish customs or border risk from general transit or shelf-life risk. A medium route risk caused by long transit is not automatically medium customs risk.
- Recommend the cheapest valid option that is not stale and does not carry disqualifying high border/customs risk. If the cheapest option is stale or high risk, choose the next valid lower-risk option.

## Opportunity, Invoice, Payment, and Revenue Reconciliation

Start from the opportunity ID, then gather linked invoices, posted payments, posted revenue journals, customer, event, and voucher records.

Opportunity status:

- Map `closed_won` to `WON`.
- Map open pipeline stages to `OPEN`.
- Map lost stages to `LOST`.

Milestones:

- Sort opportunity phases in business order.
- When the template asks for `MS1`, `MS2`, or `MS3`, create those canonical milestone IDs from the sorted phase order. Use raw API `phase_id` only when the template explicitly asks for a phase ID.
- The phase total is the sum of phase amounts.
- `opportunity_matches_phase_total` is true when the won amount equals the phase total.
- Match each phase to its invoice via the phase's `invoice_id`.

Payment state:

- Prefer invoice totals and paid/outstanding amounts over narrative notes.
- Paid amount comes from invoice `paid_amount_usd` and should agree with posted payments.
- Outstanding amount comes from invoice `outstanding_amount_usd` or `invoice_total - amount_paid`.
- `PAID` means the invoice is fully paid.
- `PARTIAL` means some amount has been paid but an amount remains unpaid.
- `UNPAID` means no posted payment has been applied.
- For invoice-state enums, use the template's wording. Some templates want `OPEN` for unpaid invoices; others want payment status such as `UNPAID`.

Revenue recognition:

- A complete, paid milestone needs a posted revenue journal unless the template or policy says recognition is not required.
- If a paid milestone has a matching posted journal, mark it recognized.
- If a paid milestone lacks a matching posted journal, mark it missing using the template's controlled value, such as `MISSING_REVENUE_JOURNAL` or `REQUIRED_MISSING`.
- If a milestone is unpaid, revenue recognition is usually not required yet; use the template's unpaid/not-required value.
- Aggregate revenue recognition is complete when every paid milestone has a posted journal. It is missing when any paid milestone lacks a required journal.
- Recognized amount is the sum of posted revenue journal amounts for the target opportunity and matching paid milestones.

Follow-up actions:

- If a paid milestone is missing a required revenue journal, route an accounting action to record revenue for that milestone. Use the template's exact enum for the action, milestone, owner queue, debit account, and credit account.
- If an unpaid milestone is not yet due as of the task's business date, monitor it rather than sending a collection notice unless the template says otherwise.
- If an unpaid milestone is due or overdue, route a collection action to the account management or collections queue as declared by the template.
- Use the prompt's named contact when provided, but verify that it matches the customer or opportunity record.

## Events and Vouchers

When the template asks for an event or invite action:

- Fetch or search the event ID from the prompt or opportunity-linked search results.
- Fetch or search the voucher code referenced by the event.
- Verify event and voucher cross-links by `event_id`, `voucher_code`, `customer_id`, and `opportunity_id` when fields are available.
- Normalize event and voucher statuses to the template's enum style.
- Use the API's discount field according to the template. A percent-based API field may be represented as a numeric discount value when the template asks for a generic voucher discount.
- If the event is scheduled, active, or confirmed and the voucher is active, create the invite action requested by the template using the exact enum names it declares.

## Template Mapping Tips

- Do not assume every task uses the same field names. Map the current records to the current template.
- If the template includes nested action objects, keep top-level action summary fields and nested action fields consistent.
- If the template declares specific enum names, copy those enum names exactly.
- If the prompt gives an as-of or current business date, use that for due-date decisions and validity checks. Otherwise use the quote date or task date provided by the API records.
- Do not output internal notes about missing or conflicting records unless the template has a warning or notes field for them.
