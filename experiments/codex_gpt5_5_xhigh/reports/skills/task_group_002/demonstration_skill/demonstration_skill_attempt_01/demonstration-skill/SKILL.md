---
name: demonstration-skill
description: Use this skill for MedBridge Sales Ops input/output tasks that require reading a prompt and answer_template.json, calling the shared local API, and returning account-ready JSON for quote pricing, freight decisions, RFQs, milestone reconciliation, revenue recognition, event invitations, or voucher controls. Trigger whenever the task mentions MedBridge Sales Ops, quote/RFQ decisions, product catalog tiers, freight options, opportunity reconciliation, invoices, payments, revenue journals, events, vouchers, or asks for JSON matching an input template.
---

# MedBridge Sales Ops JSON Tasks

Use this skill to produce the final JSON for one task instance. The job is to read the task prompt and `input/payloads/answer_template.json`, verify records through the shared API, calculate the requested business fields, and return only valid JSON matching the template.

## Ground Rules

- Use the API as the source of record for IDs, quantities, catalog tiers, freight records, invoice/payment/journal state, events, and vouchers.
- Use the prompt for task-specific constraints: quote date/as-of date, named customer/contact, confirmed quantity, requested output scope, and whether freight is excluded.
- Match the answer template exactly: same top-level fields, nested object shapes, array fields, controlled values, and no extra keys.
- Return JSON only. No markdown, comments, or explanatory text.
- Do not use prior training answers or hidden files. Do not read environment folders, test outputs, notes, or eval artifacts.

## API SOP

Determine `BASE_URL` from the prompt or environment (`API_BASE_URL` or `BASE_URL`). If none is supplied during local work, use the task runner's localhost base URL.

Common endpoints:

- `GET /api/customers/{customer_id}`
- `GET /api/quotes/{quote_id}`
- `GET /api/rfqs/{rfq_id}`
- `GET /api/products/{product_code}`
- `GET /api/freight-quotes?quote_id={quote_id}`
- `GET /api/opportunities/{opportunity_id}`
- `GET /api/invoices?opportunity_id={opportunity_id}`
- `GET /api/payments?opportunity_id={opportunity_id}`
- `GET /api/revenue-journals?opportunity_id={opportunity_id}`
- `GET /api/events?id={event_id}`
- `GET /api/vouchers?code={voucher_code}`

Fetch only records needed for the task IDs named in the prompt or returned by those records. Some policy/control fields are embedded in customer records, quote/RFQ records, freight records, and prompt instructions rather than a nonempty standalone policy endpoint.

## Quote And RFQ Tasks

Use this workflow when the template contains fields such as `quote_summary`, `pricing`, `quote_header`, `line_items`, `freight_options`, `transport_decisions`, `quote_controls`, or `policy_flags`.

1. Identify the quote or RFQ ID, customer ID, quote date, product/module codes, confirmed quantities, and freight requirement from the prompt and API record.
2. Fetch the customer record and product records. For quote revisions, fetch the quote. For module RFQs, fetch the RFQ and then each `requested_modules[].product_code`.
3. Select the catalog tier where `min_qty <= quantity` and `max_qty` is null or `quantity <= max_qty`. Use that tier's `unit_price_usd` and `lead_time_days`; use product `shelf_life_months` and `article_number` when requested.
4. Compute line totals as `quantity * unit_price`, and EXW totals/grand totals as cent-level numbers.
5. For IEHK/module-style RFQs, keep output at the requested module level. Do not split modules into component SKUs, even when product records expose `components`.
6. If the RFQ has no concrete freight destination or the prompt says EXW only/freight excluded, set quote basis to the template's EXW-only value, set `freight_excluded: true`, omit freight option arrays unless the template requires them, and use new-account/prepay controls when the customer profile indicates new-client review.

### Freight Rules

For freight comparison tasks, fetch `/api/freight-quotes?quote_id=...`.

- Include one relevant option per requested mode, usually AIR, SEA, and ROAD, in the order implied by the template or prompt.
- Exclude distractor routes, old benchmark records, records with mismatched destination/shipment details, and records explicitly marked as unrelated.
- Include a stale current-lane record when the prompt/template asks for validity, source-staleness, route-risk, or road-quote warnings. Mark it stale; do not recommend it.
- Validity is based on `valid_until >= quote_date` and record status. Use `VALID`/`STALE`, `source_is_stale`, or `all_freight_options_valid_on_quote_date` according to the template.
- Normalize `mode` and risk fields to the template convention: usually uppercase mode (`AIR`, `SEA`, `ROAD`) and uppercase risk (`LOW`, `MEDIUM`, `HIGH`).
- Compute `grand_total_usd = exw_total + freight_cost_usd`.
- Recommend the lowest-cost valid mode that satisfies route-risk and policy constraints. Do not recommend stale, expired, or high-risk road freight simply because it is cheapest. Sea is often the best valid low-cost option when air is expensive and road is stale/risky.
- Set freight reconfirmation required when the template/policy asks for freight controls, when any included route is stale/expired, or when route notes/risk require reconfirmation.

### Payment And Quote Controls

- Map customer `payment_profile` and prompt context to the template's payment terms. New/prospect NGO review generally uses `PREPAY_100`; recurring accounts with a net profile use `NET_30_AFTER_PO`; milestone billing belongs to reconciliation tasks.
- Use template-specific quote basis strings such as `EXW`, `EXW_ONLY`, or `EXW_PLUS_FREIGHT_OPTIONS`; do not blindly copy raw API incoterm prose.
- If the template asks for `customer_policy`, derive a concise controlled label from customer segment/type and recurrence, for example recurring NGO versus new NGO, using the template's style.
- If the template asks for WHO documentation, set it from the prompt/product family/customer context; emergency health kit module RFQs commonly require it.

## Opportunity Reconciliation Tasks

Use this workflow when the template contains `account_status`, `engagement_reconciliation`, `milestones`, `revenue_recognition`, `invoice_actions`, `event_actions`, or `follow_up_tasks`.

1. Extract opportunity ID, customer ID, contact name, current/as-of date, event ID, and voucher code from the prompt.
2. Fetch customer, opportunity, invoices, payments, revenue journals, event, and voucher records.
3. Join opportunity phases to invoices by `invoice_id` or `phase_id`. Output stable milestone IDs as `MS1`, `MS2`, `MS3` in ascending phase order unless the template explicitly asks for API phase IDs.
4. Compute phase total, total paid, outstanding balance, and whether the opportunity won amount matches the phase total.
5. Normalize opportunity stage: `closed_won` -> `WON`, open values -> `OPEN`, lost values -> `LOST`.
6. Prefer the prompt-facing account/customer name in output when the prompt gives a clear display name and the API customer name differs; still use API IDs and linked records for verification.

### Invoice, Payment, And Revenue Rules

- For each milestone, use the invoice amount, paid amount, outstanding amount, due date, and invoice/payment status.
- Paid milestones require a posted revenue journal matched by phase or invoice. If present, mark `RECOGNIZED`; if paid but missing, mark `MISSING_REVENUE_JOURNAL` or `REQUIRED_MISSING` depending on the template; if unpaid, mark `NOT_REQUIRED_UNPAID`.
- Aggregate revenue status:
  - All paid milestones recognized: `COMPLETE_FOR_PAID_MILESTONES`
  - One or more paid milestones missing journals: `MISSING_FOR_PAID_MILESTONES`
  - No paid milestones require recognition: `NOT_REQUIRED`
- Recognized amount is the sum of posted revenue journal amounts included for the opportunity.
- If an accounting action is required for a paid milestone missing recognition, use the template's action value (for example `RECORD_REVENUE_MS2`), amount from the paid invoice, debit `DEFERRED_REVENUE`, credit `IMPLEMENTATION_SERVICES_REVENUE`, and owner queue `ACCOUNTING`.

### Collections, Events, And Vouchers

- Create collection/follow-up output for unpaid milestones when the template asks for tasks or invoice actions. If the template offers both monitor and notice values, use `MONITOR_UNPAID_NOT_DUE` for unpaid milestones not yet due and `SEND_COLLECTION_NOTICE` for overdue items. If the template only offers a generic collection value, use that value for the unpaid milestone.
- Event records are fetched with `/api/events?id=...`; voucher records are fetched with `/api/vouchers?code=...`.
- Normalize event and voucher statuses to uppercase template enums. `scheduled` or `confirmed` events with active vouchers generally need an invite/send action unless the API shows the invite is already handled.
- Voucher discount fields usually come from `discount_percent`; max-use fields come from `max_redemptions`.
- Convert owner text such as `Account Management` to enum style such as `ACCOUNT_MANAGEMENT`.

## Output Field Conventions

- Dates: ISO `YYYY-MM-DD`; use `null` for nullable dates, not an empty string.
- Money: JSON numbers, rounded to cents. Do not quote currency amounts.
- Enums: use the exact controlled values in the template. Normalize API lowercase values to template uppercase values.
- Arrays: preserve the business order requested by the template or prompt. For freight, use mode order if shown; for milestones, use ascending phase/milestone order; for RFQ line items, preserve RFQ requested module order.
- Transit days: follow the template convention. If the template sample includes `"days"`, keep API `transit_days_text`; if the placeholder is empty or terse, output the numeric range without a trailing `" days"` when that better matches the template style.
- String IDs: use stable API IDs for quote, RFQ, customer, freight, invoice-linked milestone, event, and voucher fields unless the template asks for normalized milestone labels like `MS1`.

## Common Pitfalls

- Do not use `prior_unit_price_usd`; catalog tier pricing overrides prior quote pricing.
- Do not recommend the cheapest freight option if it is stale, expired, a distractor, or high-risk.
- Do not include component composition details for module-level RFQs.
- Do not fail when `/api/policies?...` is empty; derive controls from customer profile, quote/RFQ context, freight status, and template values.
- Do not copy raw API statuses such as `closed_won`, `paid`, `unpaid`, `scheduled`, or `active` when the template expects uppercase controlled enums.
- Do not add explanation outside the JSON, even when the prompt asks for an account-ready decision package.

## Final Check

Before returning, validate that:

- Every template field is present and no extra fields were added.
- All IDs and amounts trace to the API records or explicit prompt constraints.
- Totals equal the sum/product of their source numbers.
- Stale freight and missing revenue journals are flagged in the exact fields the template provides.
- The response parses as valid JSON.
