---
name: demonstration-skill
description: Use this skill for MedBridge Sales Ops evaluation tasks that ask for account-ready JSON from a local API and an input/payloads/answer_template.json file. It covers quote/RFQ pricing, freight decisions, customer payment policies, opportunity milestone reconciliation, revenue recognition, invoice follow-ups, events, and vouchers. Always use this when the task mentions MedBridge Sales Ops, API_BASE_URL or BASE_URL, quote/RFQ IDs, freight options, opportunities, milestones, revenue journals, or JSON matching an answer template.
---

# MedBridge Sales Ops JSON SOP

Produce only the final JSON object requested by the prompt. Read the task prompt and `input/payloads/answer_template.json`, fetch facts from the MedBridge Sales Ops API, calculate the requested totals/statuses, and return JSON with exactly the template's keys, nesting, ordering style, enum values, numeric types, and null conventions.

## API Workflow

1. Resolve the API base URL from the task prompt or runner environment. Prompts may name it `API_BASE_URL`, `BASE_URL`, or show `http://127.0.0.1:<PORT>`.
2. Use `GET {BASE_URL}/api` if you need the route index. Common routes:
   - `GET /api/search?q=<id-or-text>`
   - `GET /api/customers/<customer_id>`
   - `GET /api/products/<product_code>`
   - `GET /api/rfqs/<rfq_id>`
   - `GET /api/quotes/<quote_id>`
   - `GET /api/opportunities/<opportunity_id>`
   - Collections: `/api/freight-quotes`, `/api/invoices`, `/api/payments`, `/api/revenue-journals`, `/api/events`, `/api/vouchers`, `/api/policies`
3. Prefer targeted lookups:
   - Search by the quote, RFQ, opportunity, event, voucher, product, and customer IDs named in the prompt.
   - Fetch product records directly for every requested product/module.
   - Fetch the customer directly when a customer name, segment, payment profile, or contact must be verified.
4. Treat records returned by search as candidates, not automatic inclusions. Keep only records whose IDs and linkage fields match the task: `quote_id`, `rfq_id`, `opportunity_id`, `customer_id`, `invoice_id`, `event_id`, or `voucher_code`.

## Output Rules

- Return valid JSON only. No markdown, comments, or explanatory text.
- Preserve the answer template shape. Do not add fields that are not in the template.
- Use JSON numbers for money and quantities, not strings. Use cents when the template requests two-decimal USD values.
- Use ISO dates (`YYYY-MM-DD`) and `null` where the template allows null.
- Convert enums exactly to the template's controlled values. Usually API lowercase status/mode values become uppercase output values.
- Use the business date, quote date, or as-of date named in the prompt. If none is supplied, use the relevant API record date, not the real-world current date.
- If the prompt supplies a display name or contact that differs slightly from the API customer/contact record, use the prompt's explicit name in human-facing output fields and keep stable IDs from the API.

## Quote and RFQ Pricing

Use this flow for quote revisions, RFQs, module quotes, freight comparisons, and payment/quote-control packages.

1. Identify the commercial source:
   - Quote revisions use `/api/quotes/<quote_id>`.
   - Indicative module requests use `/api/rfqs/<rfq_id>`.
2. Confirm customer, quote/RFQ date, currency, product codes, and quantities from the API and prompt. Prompt-confirmed quantities override prior or superseded values.
3. For each product, fetch `/api/products/<product_code>`.
4. Select the price tier where `min_qty <= quantity` and either `quantity <= max_qty` or `max_qty` is null. Never use `prior_unit_price_usd` or older RFQ quantities for a revised quote.
5. Compute:
   - `line_total = quantity * unit_price`
   - `exw_total = sum(line_total)`
   - `grand_total = exw_total + freight_cost` when freight is included
6. Copy product facts from the product record: `article_number`, selected tier `lead_time_days`, product `shelf_life_months`, and selected tier bounds when requested.
7. For module-level RFQs, quote the requested modules only. Do not explode `components` or `component_composition_distractors` into line items.
8. If the task says destination is pending or asks for EXW only, set freight-excluded fields to true and do not invent freight.

## Freight Decisions

1. Search by quote ID to get linked freight records. Include freight only when `record.quote_id` exactly matches the task quote.
2. Exclude distractors:
   - IDs or RFQs marked as distractors, superseded, draft, closed-lost, or stale benchmarks unrelated to the requested route.
   - Freight with a mismatched route, destination, shipment size, product family, or quote/RFQ linkage.
3. Include stale/expired freight only when it is one of the task's requested current-mode comparisons and the prompt asks for source-validity, stale-source, or route-risk concerns. Mark it stale rather than silently dropping it.
4. Validity:
   - Valid when `status` is active and `valid_until >= quote_date`.
   - Stale/expired when `status` is stale or `valid_until < quote_date`.
   - `source_is_stale` is true for stale/expired records.
   - `all_freight_options_valid_on_quote_date` is true only when every included option is valid on the quote date.
5. Risk fields:
   - `risk_level` usually comes from `route_risk` uppercased.
   - `risk_flag` is `NONE` for low risk, `MEDIUM_BORDER_RISK` for medium border/customs risk, and the template's high-risk equivalent for high border/customs risk.
   - If the output asks specifically for customs or border risk, read `risk_notes`; default to `LOW` unless the notes mention medium/high customs or border risk.
6. Transit days:
   - Use `transit_days_text` if the template expects text such as `"4-6 days"`.
   - Use a min-max string without the word "days" only if the template examples or field style show that convention.
7. Recommended mode:
   - Prefer the lowest-cost valid freight option that satisfies stated constraints and avoids medium/high border risk when a comparable valid low-risk option exists.
   - Do not recommend stale or expired freight unless the prompt explicitly asks to accept it.
   - When the cheapest option is stale/high-risk, recommend the next valid practical mode.
8. `freight_reconfirmation_required` is true when freight options are included and the policy/prompt requires reconfirmation, or when any included option is stale, expired, medium/high risk, or near expiry.

## Payment and Quote Policies

Use customer `segment`, `customer_type`, `is_recurring`, and `payment_profile`, plus `/api/policies` or targeted policy search when needed.

- New NGO or new-client-review profiles: payment terms are `PREPAY_100`; set new-client controls such as `who_documentation_required` when the template asks for them.
- Recurring approved NGO/commercial/government accounts with `NET_30_AFTER_PO`: use `NET_30_AFTER_PO` unless a policy or prompt says the grant restricts credit.
- EXW-only module quotes use quote basis values like `EXW_ONLY`.
- Quote revisions with freight options use the template's EXW-plus-freight basis value, often `EXW_PLUS_FREIGHT_OPTIONS`; quote summary fields may simply use `EXW`.
- Offer validity is commonly a policy/template field; use the policy value if available, otherwise use the task/template convention.

## Opportunity Reconciliation

Use this flow for CRM/account reconciliation, milestone invoices, payments, revenue recognition, and follow-up actions.

1. Search by `opportunity_id`; collect the opportunity, linked invoices, payments, revenue journals, events, and vouchers. Fetch the customer record for `customer_name` and contact validation.
2. Keep only records linked to the requested `opportunity_id` and `customer_id`.
3. Convert opportunity stage:
   - `closed_won` -> `WON`
   - open pipeline stages such as negotiation/open -> `OPEN`
   - lost/closed_lost -> `LOST`
4. Sort milestones by opportunity phase order. If the template uses `MS1`, `MS2`, `MS3`, assign those labels by sorted phase order even when API phase IDs have account-specific prefixes.
5. Match each phase to its invoice by `invoice_id`. Compute:
   - `phase_total_amount = sum(phase.amount_usd)`
   - `opportunity_matches_phase_total = won_amount_usd == phase_total_amount`
   - `total_paid_amount = sum(invoice.paid_amount_usd)`
   - `outstanding_balance = sum(invoice.outstanding_amount_usd)` or the opportunity outstanding amount when the template wants account status.
6. Invoice/payment status:
   - Paid in full: `PAID`
   - Partial payment: `PARTIAL`
   - No payment and outstanding amount: `UNPAID`
   - For invoice-state templates, map paid invoices to `PAID`, unpaid/open invoices to `OPEN`, void to `VOID`, and missing/unclear records to `UNKNOWN`.
7. Revenue recognition:
   - A paid, complete milestone requires a posted revenue journal.
   - If a matching posted journal exists by invoice, phase, or opportunity: `RECOGNIZED`.
   - If paid and complete but no matching posted journal: use the template's missing value, such as `MISSING_REVENUE_JOURNAL` or `REQUIRED_MISSING`.
   - Unpaid milestones are `NOT_REQUIRED_UNPAID`.
   - Overall recognition is complete only when every paid complete milestone has a journal; otherwise use the template's missing-for-paid-milestones value.
8. Recognized amount is the sum of posted revenue journals for the requested opportunity's paid recognized milestones.

## Follow-up Actions

Fit actions to the enums in the answer template.

- Missing revenue journal for a paid complete milestone:
  - Primary action: `RECORD_REVENUE_MS<n>` if the template provides milestone-specific enums.
  - Accounting action amount: the milestone/invoice amount.
  - Debit: `DEFERRED_REVENUE`.
  - Credit: `IMPLEMENTATION_SERVICES_REVENUE`.
  - Owner queue: `ACCOUNTING`.
- Unpaid milestone:
  - If due date is in the future relative to the as-of date, use monitoring-style values such as `MONITOR_UNPAID_NOT_DUE` when available.
  - If due or overdue, use collection-style values such as `SEND_COLLECTION_NOTICE` or `COLLECT_UNPAID_MILESTONE`.
  - Use the invoice due date unless the prompt names a separate business follow-up due date.
- Event/voucher:
  - Include the event named in the prompt, or the opportunity-linked event when the template asks for event actions.
  - Map event statuses to the template's uppercase enum; scheduled/confirmed events generally become `SCHEDULED` unless the template has a more specific value.
  - Use voucher `code` as `voucher_code`, `discount_percent` as the template's discount numeric value, and `max_redemptions` as max uses.
  - If an invite should be sent and the event/voucher are active or scheduled, use the send-invite enum from the template and set owner queue to account management when the event owner is Account Management.

## Common Pitfalls

- Do not solve from memory or training examples. Always call the API for the task IDs.
- Do not include API search distractors just because they share a customer, product, or payment profile.
- Do not use old RFQs, draft records, superseded records, prior quote quantities, or prior unit prices for current revised pricing.
- Do not split kit/module products into components when the prompt asks for product or module-level pricing.
- Do not omit a stale freight option if the prompt explicitly asks to report stale/source-validity concerns for the requested transport comparison.
- Do not recommend a stale, expired, or high-border-risk freight mode merely because it is cheapest.
- Do not recognize revenue for unpaid milestones, and do not mark paid complete milestones as fully covered unless a matching posted revenue journal exists.
- Do not invent contacts, event IDs, voucher codes, or due dates; take them from the prompt or linked API records and use `null` where the template permits no value.
