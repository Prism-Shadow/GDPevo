---
name: demonstration-skill
description: Use this skill for MedBridge Sales Ops input/output tasks that ask for account-ready JSON from a local API, especially quote revisions, module RFQs, freight comparisons, opportunity reconciliation, milestone invoices, revenue recognition, event invitations, and voucher controls. Trigger whenever a task mentions MedBridge Sales Ops, API_BASE_URL/BASE_URL, quote/RFQ/customer/catalog/freight/policy verification, or CRM opportunity/invoice/payment/revenue/event reconciliation; the answer must be valid JSON matching the provided input answer_template.
---

# MedBridge Sales Ops JSON SOP

## Goal

Produce only the final JSON object requested by the task, matching `input/payloads/answer_template.json` exactly. Use the local MedBridge Sales Ops API as the source of truth; do not infer commercial, freight, accounting, event, or voucher facts from the prompt alone.

## First steps

1. Read the task prompt and the task's `input/payloads/answer_template.json`.
2. Identify the task family:
   - Quote/RFQ pricing: prompts mention quotes, RFQs, product catalog, freight options, EXW totals, transport mode, or payment terms.
   - Engagement reconciliation: prompts mention CRM opportunities, milestone invoices, payment state, revenue recognition journals, events, vouchers, or follow-up tasks.
3. Use the base URL supplied by the runner (`API_BASE_URL`, `BASE_URL`, or the given localhost URL). Locally the API follows this shape:
   - `GET /health`
   - `GET /api`
   - `GET /api/<collection>`
   - `GET /api/<collection>/<record_id>` for single customers, products, RFQs, quotes, and opportunities
   - `GET /api/search?q=<text>` for discovery across collections
4. Keep the template's object names, nesting, arrays, field names, controlled enum values, and nullability. Return no markdown and no explanation outside the JSON.

## API Collections

Call `GET /api` if unsure which collections are available. Expected collections include:

- `customers`
- `products`
- `rfqs`
- `quotes`
- `freight-quotes`
- `policies`
- `opportunities`
- `invoices`
- `payments`
- `revenue-journals`
- `events`
- `vouchers`

Use `GET /api/search?q=<identifier-or-name>` when the prompt gives a partial customer name, quote ID, RFQ ID, event ID, voucher code, or contact. Then fetch or filter the exact collection records.

## Quote and RFQ Pricing Workflow

Use this SOP when the template contains fields such as `quote_summary`, `quote_header`, `line_items`, `pricing`, `transport_decisions`, `freight_options`, `quote_controls`, or `policy_flags`.

1. Fetch the commercial request.
   - For quote revisions, use `quotes` and match the exact `quote_id`.
   - For indicative module requests, use `rfqs` and match the exact `rfq_id`.
   - Confirm `customer_id`, `quote_date`, currency, requested/confirmed quantities, incoterm, destination, and product codes from the API record.
2. Fetch the customer from `customers`.
   - New NGO/prospect accounts generally use `PREPAY_100` when the payment policy requires new-client prepayment.
   - Recurring approved accounts generally use the customer's `payment_profile`, often `NET_30_AFTER_PO`.
   - Do not override explicit task/template policy fields with customer notes unless an API policy supports it.
3. Fetch each product from `products`.
   - Select the price tier whose `min_qty <= quantity` and whose `max_qty` is either null or `quantity <= max_qty`.
   - Use the selected tier's `unit_price_usd` and `lead_time_days`.
   - Use product `article_number` and `shelf_life_months` when the template asks for them.
   - Quote module RFQs at the module/product-code level. Ignore component composition details unless the customer explicitly asks for component-level pricing.
4. Calculate product totals.
   - `line_total = quantity * unit_price`.
   - `exw_total_usd` or `grand_total` without freight is the sum of line totals.
   - Use cent-level numeric values; do not stringify money unless the template literally asks for strings.
5. Apply quote scope policies from `policies`.
   - Indicative quotes without a confirmed destination are `EXW_ONLY`/freight excluded.
   - EXW excludes freight unless freight is requested as separate options.
   - Standard catalog offer validity is usually 30 days from quote date when the template asks for validity days.
   - Module RFQs stay at module line granularity.

## Freight Decisions

Use `freight-quotes` for freight comparison tasks. Filter by the exact quote ID/RFQ-linked quote ID and then choose only applicable records.

1. Exclude freight distractors before calculating:
   - `status` values such as `mismatch` or old/stale distractor records that do not represent a requested option.
   - Records whose shipment size, route, destination, or notes clearly describe a wrong benchmark or distractor.
   - Records for unrelated quotes or older superseded requests.
2. Include the current mode options the task asks for, commonly air, sea, and road. Normalize modes to the template convention, for example `AIR`, `SEA`, `ROAD` if uppercase values are shown.
3. Freight validity:
   - A freight quote is valid on the quote date when `valid_until >= quote_date` and the record is not stale/mismatch.
   - Mark stale or expired records with the template's stale/invalid convention, for example `STALE`, `source_is_stale: true`, or a client warning.
   - `freight_reconfirmation_required` is true for freight-option tasks because the freight policy requires reconfirmation at final order.
4. Risk fields:
   - Map `route_risk` to the template's expected casing (`LOW`, `MEDIUM`, `HIGH` or lowercase text as shown).
   - If the template asks for `risk_flag`, use `NONE` for low risk and a specific flag such as `MEDIUM_BORDER_RISK` or `HIGH_BORDER_RISK` for border/customs risks when supported by the record notes.
   - If the template asks for `customs_border_risk`, use the route risk level.
5. Calculate `grand_total_usd = exw_total_usd + freight_cost_usd` for each included option, even for stale options if the template displays them with a warning.
6. Recommend a mode using business judgment:
   - Prefer the lowest valid, usable, low/medium-risk option when no deadline overrides it.
   - Do not recommend stale/expired/high-risk options just because they are cheapest.
   - If the prompt includes a delivery deadline or grant need-by date, ensure the recommended transit range can plausibly meet it; choose air if sea/road timing is too risky.
   - For cold-chain products, prefer freight records with cold-chain support and avoid risky/stale road options.

## Opportunity Reconciliation Workflow

Use this SOP when the template contains fields such as `account_status`, `engagement_reconciliation`, `milestones`, `invoice_actions`, `revenue_recognition`, `event_actions`, or `follow_up_tasks`.

1. Fetch the opportunity from `opportunities` by exact `opportunity_id` and confirm the `customer_id`.
2. Fetch the customer from `customers` and verify the named contact against the customer contacts and the opportunity contact.
3. Filter `invoices`, `payments`, and `revenue-journals` by the exact opportunity ID and invoice/phase IDs.
4. Reconcile phase totals:
   - `phase_total_amount` is the sum of opportunity phase amounts.
   - The opportunity matches phases when the phase sum equals `won_amount_usd`.
   - Outstanding balance should match the sum of invoice outstanding amounts, and often the opportunity's `outstanding_amount_usd`.
5. Build milestones in phase order.
   - If the template wants generic IDs (`MS1`, `MS2`, `MS3`), map the opportunity phases in ascending order to those labels while preserving invoice/phase amounts.
   - If the template wants stable phase or invoice IDs, use the template's convention from examples/instructions; do not invent verbose labels.
   - `invoice_total`/`amount` comes from the invoice or phase amount.
   - `amount_paid`/`paid_amount` comes from posted payments or invoice `paid_amount_usd`.
   - `amount_unpaid` is invoice amount minus paid amount, or invoice `outstanding_amount_usd`.
   - Use `due_date: null` for fully paid milestones when the template examples use null; otherwise use the invoice due date as requested.
6. Normalize status values to the template.
   - Opportunity `closed_won` becomes `WON`; open proposal/negotiation becomes `OPEN`; closed lost becomes `LOST`.
   - Invoice status `paid` becomes `PAID`; `unpaid` or open invoice becomes `OPEN` or `UNPAID` according to the template; overdue can drive a collection action.
   - Payment status is `PAID` when paid in full, `PARTIAL` for partial payment, `UNPAID` when no posted payment exists, and `UNKNOWN` only when the source data is insufficient.
7. Revenue recognition:
   - A paid and complete milestone requires a posted revenue journal.
   - If a paid/completed milestone has a matching posted journal, status is `RECOGNIZED`.
   - If a paid/completed milestone lacks a journal, status is `MISSING_REVENUE_JOURNAL` or `REQUIRED_MISSING`, matching the template.
   - Unpaid future milestones usually use `NOT_REQUIRED_UNPAID`.
   - `recognized_amount` is the sum of posted revenue journals for the opportunity.
   - Overall recognition is complete only when every paid/completed milestone has a posted journal.
8. Accounting and collection actions:
   - If a paid milestone is missing revenue recognition, create/route an accounting action to record revenue for that milestone. Use deferred revenue as the debit account and implementation services revenue as the credit account when the template asks for accounts.
   - If unpaid amount is due in the future, use a monitor action owned by account management when the template supports it.
   - If unpaid amount is due or overdue as of the business date, use a collection notice/collection task and the collections or account-management owner required by the template.
   - If there is no accounting or collection issue, use the template's `NO_*` controlled values and `NONE`/null placeholders.

## Events and Vouchers

1. Filter `events` by the exact event ID, opportunity ID, or customer ID from the prompt.
2. Filter `vouchers` by exact voucher code or event ID.
3. Normalize statuses to the template's enum casing:
   - `scheduled` or `confirmed` generally maps to `SCHEDULED` when the template uses high-level event status.
   - `live` maps to `ACTIVE` or the closest allowed active/scheduled value in the template.
   - `active` voucher status maps to `ACTIVE`.
4. Use voucher `discount_percent` when the template says discount value/amount for event access vouchers, unless the template explicitly asks for a dollar amount.
5. Create event invitation follow-up when the prompt asks to send an invite and the event is upcoming/active with an active voucher. Use the named contact, linked customer ID, event ID, and voucher code.

## Output Field Conventions

- Return a single valid JSON object and nothing else.
- Preserve the template's keys and nesting. Omit fields only if the template omits them.
- Preserve array order expected by the template:
  - Quote freight options usually follow air, sea, road.
  - Milestones usually follow phase order (`MS1`, `MS2`, `MS3`).
  - Module RFQ line items follow the API `requested_modules` order unless the task says otherwise.
- Use ISO `YYYY-MM-DD` dates.
- Use JSON numbers for money and quantities. Round to two decimals for currency, but `76000.0` and `76000.00` are both numeric JSON; consistency matters more than formatting.
- Use JSON `null` for unavailable optional values when the template allows null. Do not use `"null"`, `"N/A"`, or blank strings unless the template shows blank strings.
- Match controlled enum strings exactly as declared in the template, including case and underscores.
- Use stable API record IDs (`quote_id`, `rfq_id`, `customer_id`, `freight_id`, `event_id`, voucher code) rather than display names.

## Common Pitfalls

- Do not use prior quote quantities or prior unit prices when the task says a customer confirmed a revised quantity. Re-select the catalog tier from the current quantity.
- Do not split module RFQs into component SKUs because the API includes component composition details. Those are often distractors.
- Do not include freight for EXW-only or no-destination indicative quotes.
- Do not recommend a stale/expired/high-risk freight option purely because its cost is lower.
- Do not include freight distractors with IDs or notes indicating old, wrong-size, archived, unrelated, mismatch, or superseded records.
- Do not copy CRM stage or status casing directly from the API when the template declares enums.
- Do not treat a paid invoice as fully reconciled until a required revenue journal is present.
- Do not create collection tasks for paid milestones; do create accounting tasks for paid milestones missing revenue recognition.
- Do not ignore the prompt's business date. Use it to decide stale freight, overdue invoices, and whether unpaid milestones are future-due or overdue.
- Do not add explanatory prose to the JSON response.

## Final Verification

Before returning, check:

1. Every identifier in the output can be traced to an API record or the prompt.
2. Product pricing uses the current quantity's tier and line totals multiply correctly.
3. Freight grand totals add correctly and validity/risk/reconfirmation flags are consistent.
4. Opportunity phase totals, paid totals, outstanding balances, and revenue journal totals reconcile.
5. Event/voucher fields are linked to the same customer/opportunity.
6. The JSON parses, contains no comments, and matches the template's structure and controlled values.
