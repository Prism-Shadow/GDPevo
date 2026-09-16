---
name: medbridge-sales-ops-json
description: Use this skill for MedBridge Sales Ops API tasks that require an account-ready JSON answer for quotes, RFQs, freight comparisons, customer policies, opportunity milestone reconciliation, revenue recognition, payments, events, or vouchers. Use it whenever the prompt mentions the MedBridge Sales Ops API, quote/RFQ decision packages, EXW pricing, freight validity or route risk, milestone invoices, accounting follow-ups, or asks for JSON matching an answer_template.json.
---

# MedBridge Sales Ops JSON

Use this skill to produce the final JSON for MedBridge Sales Ops tasks. The API is the business source of truth, and the task's `input/payloads/answer_template.json` is the output schema.

## Core Workflow

1. Read the user prompt and `input/payloads/answer_template.json` first.
2. Extract every requested identifier and constraint from the prompt: customer, quote, RFQ, opportunity, product/module codes, event, voucher, quote date or as-of date, confirmed quantities, destination/freight scope, named contact, and any requested controlled statuses.
3. Resolve the API base URL from the prompt or runner environment variables such as `TASK_ENV_BASE_URL` or `BASE_URL`. Do not hard-code a creator-side URL.
4. Discover the API with `GET /api`, then use `GET /api/search?q=<id-or-name>` for broad record discovery.
5. Fetch exact records when available: `/api/customers/{id}`, `/api/products/{code}`, `/api/rfqs/{id}`, `/api/quotes/{id}`, `/api/freight-quotes/{id}`, `/api/policies/{id}`, and `/api/opportunities/{id}`. Some finance/event detail routes may not exist; if an exact route returns `not_found`, use `/api/search` and collection endpoints such as `/api/invoices`, `/api/payments`, `/api/revenue-journals`, `/api/events`, and `/api/vouchers`, then filter locally.
6. Build the response in the exact template shape. Preserve key order and nesting, add no extra keys, and return only valid JSON.

Use exact ID joins over name matches. When using search results, reject distractors by checking the linking fields: `customer_id`, `quote_id`, `rfq_id`, `opportunity_id`, `invoice_id`, `event_id`, `voucher_code`, product code, destination, shipment size, status, and dates.

## Quote and RFQ Packages

For quote revisions:

- Get the quote and customer, then get each quoted product.
- Use the prompt's confirmed quantity when it is explicit, and verify it against the quote line. Otherwise use the quote or RFQ record quantity.
- Select the catalog tier where `min_qty <= quantity` and `max_qty` is null or `quantity <= max_qty`.
- Use the tier's `unit_price_usd` and `lead_time_days`; use product `article_number`, `shelf_life_months`, and cold-chain fields when the template asks for them.
- Compute line totals and EXW totals as numeric USD values: `quantity * unit_price`.

For module RFQs:

- Quote the `requested_modules` at module line level unless the prompt explicitly asks for component pricing.
- Do not split product `components` into line items when the customer requested module-level pricing.
- If the RFQ has no confirmed destination or the prompt says freight is excluded, set EXW-only fields and leave freight out.
- Apply payment and validity policies from the customer and policy records. New/prospect NGO accounts generally map to prepayment; recurring approved accounts generally map to net terms after PO. Standard catalog quote validity is 30 calendar days when the template asks for offer validity.
- If the template asks for medical or WHO documentation controls, derive them from the RFQ narrative, product family, customer type, and policy context; NGO medical-module quotes under donor or health-kit review usually require the documentation flag.

For freight options:

- Select freight records linked to the exact `quote_id` and relevant shipment/destination. Exclude old-route, wrong-size, or unrelated route benchmarks even when they share the quote id.
- Include a stale matching freight option when the task asks for source validity, route-risk concerns, or a transport comparison that must show why an option is not recommended. Otherwise prefer current active records for the same mode.
- Format mode values in uppercase (`AIR`, `SEA`, `ROAD`) unless the template requires another form.
- Use `transit_days_text` when the template expects a human-readable transit string. If the surrounding schema clearly uses compact ranges, derive `min-max` from `transit_days_min` and `transit_days_max` consistently.
- A freight option is stale when `status` is stale/inactive or `valid_until` is before the quote date. Otherwise it is valid on the quote date.
- `grand_total` or EXW-plus-freight total is `exw_total + freight_cost`.

Freight decision rules:

- Recommend the lowest-cost valid option that satisfies the requested shipment constraints.
- Do not recommend stale freight or a route with high customs/border risk just because it is cheapest.
- When the lowest valid option has a non-customs operational risk but remains acceptable, it can still be recommended if the prompt asks for a practical freight option set.
- `freight_reconfirmation_required` is true whenever a freight-reconfirmation policy applies or any selected freight option is stale/risky.
- `all_freight_options_valid_on_quote_date` is true only when every selected freight option is valid through the quote date.
- For `risk_level`, uppercase the freight `route_risk`.
- For `risk_flag`, use `NONE` for low risk; otherwise use a controlled flag that matches the risk type in the template, commonly `<LEVEL>_BORDER_RISK` when notes mention border/customs risk.
- For fields named `customs_border_risk`, focus on customs or border concerns in `risk_notes`; do not turn an unrelated medium operational risk into a customs/border warning.
- If the template asks for a client warning, make it concise and specific: cite the policy need to reconfirm freight, any expired freight id/date, and any high customs/border issue.

Payment and quote policy fields should come from policies and customer records, not from assumptions. Use customer payment profile, customer segment/type, and matching policy `terms_code` to populate fields such as payment terms, quote basis, customer policy, freight exclusion, and documentation requirements.

## Opportunity Reconciliation

For opportunity/account tasks:

- Fetch the opportunity, customer, invoices, payments, revenue journals, events, and vouchers tied to the requested opportunity/customer.
- Map opportunity stages to template enums, for example closed-won to `WON`, open stages to `OPEN`, and lost stages to `LOST`.
- Sum opportunity phases to produce the phase/milestone total; compare it to `won_amount_usd`.
- Use posted payments only when computing paid amounts. Use invoice `paid_amount_usd` and `outstanding_amount_usd` when present, then cross-check against payment records.
- Sort milestones by phase order. If the template uses `MS1`, `MS2`, `MS3` style milestone IDs or includes `phase_number`, output those stable ordered IDs; otherwise use the API phase or invoice milestone identifier requested by the template.
- For invoice state, map paid invoices to `PAID`, unpaid/open outstanding invoices to `OPEN` when the enum uses invoice state, and voided invoices to `VOID`.
- For payment state/status, use `PAID` when fully paid, `PARTIAL` when some but not all is paid, and `UNPAID` when no amount is paid.
- Use invoice due dates for unpaid milestone due dates unless the prompt or a more specific milestone/payment record supplies a different due date.

Revenue recognition:

- A paid completed milestone requires a posted revenue journal for the same opportunity and invoice or phase.
- If a matching posted journal exists, the milestone recognition status is `RECOGNIZED`.
- If the milestone is paid but no matching posted journal exists, use the template's missing-journal enum, such as `MISSING_REVENUE_JOURNAL` or `REQUIRED_MISSING`.
- If the milestone is unpaid, revenue recognition is not required yet; use `NOT_REQUIRED_UNPAID` when available.
- Overall recognition is complete when all paid milestones have posted journals, missing when any paid milestone lacks one, and not required only when no paid milestone requires recognition.
- Recognized amount is the sum of recognized posted journal amounts, using the same milestone IDs used in the milestone array.

Follow-up actions:

- Create accounting actions only for paid milestones that are missing required revenue recognition. Use deferred revenue as debit and implementation services revenue as credit when the template asks for accounts.
- Create collection actions for unpaid balances. If an as-of date is before the due date, monitor the unpaid-not-due milestone; if it is on or after the due date, send a collection notice. Use the prompt's named contact or the opportunity contact.
- Include event invitation actions when the prompt asks for a linked event or voucher. Fetch the event and voucher, map event/voucher statuses to uppercase template enums, and carry through event id, voucher code, discount value, max uses, customer id, and contact.
- When a voucher record stores `discount_percent`, use that numeric value for template fields named voucher discount or discount amount unless the API provides a more specific discount amount field.
- If event status is `scheduled` or `confirmed` and the template enum has `SCHEDULED`, use `SCHEDULED`.

## Output Discipline

- Return JSON only: no markdown fence, no explanation, no trailing prose.
- Use the template's controlled enum values exactly.
- Use `null` where the template calls for null or where no value applies; do not substitute empty strings for null fields.
- Keep money as numeric USD values. Use cent-level precision when the prompt or template requests it.
- Recalculate every total before finalizing: line totals, EXW total, freight grand totals, phase totals, total paid, outstanding balance, recognized amount, and voucher controls.
- Before final answer, validate the JSON with a parser such as `jq`, check that every requested ID is tied to the same customer/opportunity/quote, and confirm no template fields are missing.
