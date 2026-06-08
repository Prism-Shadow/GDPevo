---
name: reflection-skill
description: Use this skill for MedBridge Sales Ops API tasks that ask Codex to prepare strict JSON quote packages, RFQ module quotes, freight decisions, milestone invoice reconciliations, revenue-recognition checks, or event/voucher follow-up actions. Trigger whenever the prompt mentions a Sales Ops API base URL, MedBridge, quotes/RFQs, catalog tiers, freight options, CRM opportunities, invoices, payments, revenue journals, milestones, or account-ready JSON; this skill is especially important when an answer_template.json defines controlled fields.
---

# MedBridge Sales Ops JSON Workflow

## Goal

Produce account-ready JSON from the task input template using the local MedBridge Sales Ops API as the business source of truth. The work is mostly record reconciliation: fetch the named API records, apply catalog/freight/payment/revenue policies, normalize fields to the template, and return JSON only.

Respect harness boundaries. Read only the task prompt and input payload/template unless the harness explicitly allows training-answer reflection. Do not enter task-group `env` folders, do not inspect test outputs/notes/eval files, and do not solve test tasks while creating or evaluating a skill.

## API Environment

Use the base URL supplied by the prompt or runner, such as `API_BASE_URL`, `BASE_URL`, or `http://127.0.0.1:<PORT>`. Prefer targeted requests by IDs named in the prompt.

Common endpoints:

- `GET /api/customers/{customer_id}`
- `GET /api/quotes/{quote_id}`
- `GET /api/rfqs/{rfq_id}`
- `GET /api/products/{product_code}`
- `GET /api/freight-quotes?quote_id={quote_id}`
- `GET /api/policies`
- `GET /api/opportunities/{opportunity_id}`
- `GET /api/invoices?opportunity_id={opportunity_id}`
- `GET /api/payments?opportunity_id={opportunity_id}`
- `GET /api/revenue-journals?opportunity_id={opportunity_id}`
- `GET /api/events?customer_id={customer_id}` or `GET /api/events?opportunity_id={opportunity_id}`
- `GET /api/vouchers?customer_id={customer_id}` or `GET /api/vouchers?opportunity_id={opportunity_id}`

Some collections list records with filters, while direct `/{id}` lookups return `Endpoint not found`. If a voucher-code query returns no rows, query by customer or opportunity and match the voucher code locally. `/api/policies` is a general list; filters may return empty even when relevant policy records exist.

When using zsh for quick endpoint probes, avoid naming a loop variable `path`; it can shadow command lookup.

## Standard Operating Procedure

1. Read the prompt and `answer_template.json`.
2. Extract all stable IDs, quote/RFQ dates, customer names, product codes, quantities, event IDs, voucher codes, and contact names from the prompt.
3. Fetch only the named or directly related API records. Do not rely on prompt prose for values that the API can verify.
4. Fill the template exactly: same top-level keys, same nested object names, same array purpose, and only controlled enum values requested by the template.
5. Normalize text to the template style. Modes, risk levels, statuses, and action enums are usually uppercase with underscores.
6. Recalculate totals and statuses from source records, then run a final consistency pass before returning JSON.

## Quote And RFQ Rules

For catalog pricing:

- Select the product price tier where `min_qty <= confirmed_quantity <= max_qty`; treat `max_qty: null` as open-ended.
- Use the confirmed quantity from the quote/RFQ/prompt, not a prior quantity or old quote value.
- `line_total` and `exw_total_usd` are normally `quantity * unit_price`.
- Preserve article numbers, lead time, and shelf life from the product record.
- `quote_basis` follows the commercial scope requested by the prompt/template: `EXW`, `EXW_ONLY`, or `EXW_PLUS_FREIGHT_OPTIONS`.

For module RFQs:

- Keep requested modules at module line level. Ignore `components` and any composition/distractor lists unless the customer explicitly requests component-level pricing.
- Preserve the requested module order.
- If no confirmed destination is available, quote `EXW_ONLY`, set freight excluded, and do not invent freight.
- New NGO/prospect accounts without approved credit use `PREPAY_100`.
- Catalog quote validity is 30 calendar days unless a more specific policy is supplied.
- When `who_documentation_required` is true for IEHK-style module quotes, include the documentation control in the quote-controls grand total. In this task family that control is `100.00` and does not appear as a separate line item.

## Freight Rules

Fetch freight with `GET /api/freight-quotes?quote_id={quote_id}`. The result can include distractors, stale records, or wrong shipment-size benchmarks.

Filter and classify freight options this way:

- Include options tied to the requested `quote_id` and current route/shipment.
- For ordinary "current freight options", include active current options and exclude stale distractors.
- If the prompt asks for stale, validity, road, customs, or route-risk concerns, include the relevant stale option in the comparison and mark it clearly.
- A freight option is valid on the quote date when `status` is active and `valid_until >= quote_date`.
- `source_is_stale` is true for stale/expired records or `valid_until < quote_date`.
- `validity_status` should be `VALID` or `STALE` unless the template declares other values.
- Freight grand total is `EXW total + freight cost`.
- Freight reconfirmation is true when policy `RECONFIRM_AT_ORDER` applies, even if all options are currently valid.

Risk and recommendation judgment:

- Convert API `mode` to uppercase: `AIR`, `SEA`, `ROAD`.
- Convert risk fields to uppercase controlled values.
- For simple `risk_level`, copying the route risk is usually fine.
- For `customs_border_risk`, read `risk_notes` and the field name. Do not blindly copy generic `route_risk`; a sea option may have medium operational/shelf-life risk but low customs/border risk.
- Use `NONE` for low-risk quote templates that ask for a `risk_flag`; use specific flags such as `MEDIUM_BORDER_RISK` when the risk is explicitly border/customs related.
- Recommend the cheapest valid option that satisfies urgency, cold-chain, route-risk, and policy constraints. Do not recommend a stale/expired option. If no urgency is stated and sea is valid, low enough risk, and materially cheaper, sea is usually preferred. If cold-chain timing or urgency makes slow freight unsuitable, prefer air.
- Follow the template family for transit text. Quote-summary freight options can use API text such as `4-6 days`; compact transport-decision fields may use `4-6` without the word `days`.

## Finance Reconciliation Rules

Fetch the opportunity, customer, invoices, payments, revenue journals, events, and vouchers by opportunity/customer. Revenue journals are safest to query by `opportunity_id`.

Normalize opportunity and milestone state:

- Map `closed_won` to `WON`, open stages to `OPEN`, and lost stages to `LOST`.
- `won_amount` comes from the opportunity; phase total is the sum of opportunity phases or invoice totals as requested by the template.
- `opportunity_matches_milestones` is true when the won amount equals the phase/milestone total at cent precision.
- Use prompt/customer-facing account names when the prompt supplies a display name and the API uses a variant legal name; keep stable IDs from the API.
- When the template declares milestone IDs as `MS1`, `MS2`, `MS3`, normalize phase IDs into that form and order ascending. Do not output raw phase IDs such as `MER-P1` unless the template asks for phase IDs.

Invoice and payment state:

- Invoice `paid` maps to `PAID`; unpaid/open invoices map to `UNPAID` for payment status and `OPEN` for invoice state when the template separates the two.
- Paid amount and unpaid amount come from invoice/payment records; compute outstanding balance from unpaid invoice amounts when needed.
- For paid/recognized milestones, set action-facing `due_date` fields to `null` unless the template explicitly asks for historical invoice due dates.
- For unpaid milestones, preserve the collection due date used by the requested business workflow. If records conflict, prefer the milestone/account workflow date over a stale invoice benchmark.

Revenue recognition:

- Paid plus posted revenue journal means `RECOGNIZED`.
- Paid without a posted revenue journal means `MISSING_REVENUE_JOURNAL` or `REQUIRED_MISSING`, depending on the template enum.
- Unpaid milestones are `NOT_REQUIRED_UNPAID`.
- If every paid milestone is recognized, use `COMPLETE_FOR_PAID_MILESTONES`; if any paid milestone is missing a journal, use `MISSING_FOR_PAID_MILESTONES`.
- Recognized amount is the sum of posted revenue journals for the opportunity.

Follow-up actions:

- Missing revenue for a paid milestone creates an accounting action such as `RECORD_REVENUE_MS2`, with debit `DEFERRED_REVENUE`, credit `IMPLEMENTATION_SERVICES_REVENUE`, and owner `ACCOUNTING`.
- An unpaid milestone not yet due creates `MONITOR_UNPAID_NOT_DUE` owned by `ACCOUNT_MANAGEMENT`.
- An unpaid milestone due or overdue creates a collection notice/action owned by the collections/account-management queue declared by the template.
- If no accounting or collection work is needed, use the template's `NO_*` enum values and `NONE` placeholders.

## Event And Voucher Rules

- Select the event and voucher named in the prompt, or the only event/voucher tied to the requested customer/opportunity.
- Map event status to uppercase enums such as `SCHEDULED`, `ACTIVE`, `COMPLETED`, or `CANCELLED`.
- Map voucher status to uppercase and convert `discount_percent` into the template's discount field when no currency amount exists.
- Use `max_redemptions` for max-use fields.
- If the prompt asks for an invitation or briefing/celebration follow-up and the event is scheduled/confirmed, create `SEND_*_INVITE` action fields with the named contact, customer, event, and voucher.
- Use the API follow-up owner when it maps cleanly; otherwise account-facing event invite tasks usually belong to `ACCOUNT_MANAGEMENT`.

## Field Definitions

- `quote_date` / `as_of_date`: ISO `YYYY-MM-DD` dates from the prompt or API record.
- `unit_price_usd`, `line_total`, `exw_total_usd`, `grand_total`, `won_amount`, `paid_amount`, `outstanding_balance`: USD numbers, cent precision.
- `confirmed_quantity`: final requested quantity, not prior quote quantity.
- `catalog_tier.min_quantity` / `max_quantity`: selected tier bounds; preserve `null` if the tier is open-ended and the template allows null.
- `payment_terms`: policy terms code, commonly `PREPAY_100`, `NET_30_AFTER_PO`, or milestone billing terms when declared.
- `freight_reconfirmation_required`: true when freight rates are quoted as options and policy says reconfirm at final order.
- `all_freight_options_valid_on_quote_date`: true only when all included options are active and valid through the quote date.
- `source_is_stale`: true for expired/stale freight source records, even if the cost is shown for comparison.
- `recommended_mode`: uppercase mode selected by business judgment, never a stale option.

## Final Validation Checklist

Before returning:

- The response is valid JSON only, with no markdown or explanatory text.
- Every key in the answer template is present, and no extra keys are added unless the template allows them.
- Arrays are ordered naturally: RFQ request order, freight comparison order `AIR`, `SEA`, `ROAD` when all are present, and milestones ascending.
- All controlled enum values match the template exactly.
- Product totals, freight totals, paid/unpaid amounts, phase totals, and recognized amounts have been recalculated.
- Freight distractors, component-level distractors, old quote quantities, and stale benchmark records are excluded unless the prompt/template asks to flag them.
- Paid milestones do not accidentally carry historical due dates into action fields.
- Voucher-code filters have been verified by customer/opportunity query if direct lookup returns no records.

## Common Pitfalls From Training Reflection

- Do not trust broad freight query results at face value. They can include stale records and wrong-route or wrong-shipment distractors under the same quote ID.
- Do not split IEHK-style module RFQs into their product components. The customer asked for module-level commercial lines.
- Do not forget the non-line-item WHO documentation control when the template marks WHO documentation as required.
- Do not recommend the cheapest freight option if it is stale or expired. Mark it as stale and choose a valid mode.
- Do not copy generic route risk into `customs_border_risk` without reading the risk note.
- Do not output API phase IDs when the template enumerates `MS1`, `MS2`, and `MS3`.
- Do not include due dates for already paid milestones in action-oriented reconciliation templates.
- Do not query revenue journals only by customer; query by opportunity to avoid missing posted journals.
- Do not assume prompt display names and API legal names always match. Use stable IDs for linkage and the business-facing name expected by the requested account package.
