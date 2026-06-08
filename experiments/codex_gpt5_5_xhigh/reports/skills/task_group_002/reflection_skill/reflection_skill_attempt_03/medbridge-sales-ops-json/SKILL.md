---
name: medbridge-sales-ops-json
description: Use this skill for MedBridge Sales Ops API tasks that require account-ready JSON for quotes, RFQs, catalog tier pricing, freight comparisons, payment terms, milestone opportunity reconciliations, invoice/payment state, revenue-recognition journals, events, and vouchers. Trigger whenever the user mentions the MedBridge Sales Ops API, quote/RFQ/opportunity IDs, freight options, answer_template-compatible JSON, or finance/account follow-up reconciliation.
---

# MedBridge Sales Ops JSON

## Goal

Produce valid JSON that exactly matches the provided answer template while using the MedBridge Sales Ops API as the business source of truth. Do not add markdown or narrative outside the JSON.

## Environment SOP

1. Read the prompt and `input/payloads/answer_template.json`.
2. Get the API base URL from the prompt, `API_BASE_URL`, or `BASE_URL`. If the runner provides a literal local URL, use that exact URL.
3. Fetch `GET {base}/api` first. It exposes the collections and endpoint names. Common collections are:
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
4. Fetch only the records needed for the prompt. Use direct ID endpoints when available (`/api/quotes/<id>`, `/api/rfqs/<id>`, `/api/opportunities/<id>`, `/api/customers/<id>`, `/api/products/<code>`), and collection endpoints for invoices, payments, freight, journals, events, and vouchers.
5. If a record is hard to locate, use `/api/search?q=<text>` with the known ID, customer name, product code, contact name, event ID, or voucher code.
6. Do not inspect local task environment folders or answer files while solving a live task. The API and prompt/template are enough.

## General Output Rules

- Preserve the template's top-level keys, nested keys, array structure, and controlled values.
- Use ISO `YYYY-MM-DD` dates.
- Use uppercase enum/status strings when the template shows uppercase values.
- Use money as numbers, normally with two decimal places where the template asks for currency.
- Use IDs from the relevant live record, not distractor or superseded records.
- When the prompt names a human-facing account name and it differs slightly from the API customer `name`, use the prompt's account display name for `customer_name` fields, while still using API IDs and financial facts.
- Normalize CRM stages: `closed_won` -> `WON`, open stages -> `OPEN`, closed lost -> `LOST`.
- Validate arithmetic before finalizing: line totals, EXW totals, freight grand totals, milestone totals, paid totals, and outstanding balances.

## Quote And RFQ SOP

Use this path when the template asks for `quote_summary`, `pricing`, `quote_header`, `line_items`, `freight_options`, `transport_decisions`, or `quote_controls`.

1. Identify the active quote or RFQ by ID from the prompt.
2. Fetch the customer, quote/RFQ, policies, and every referenced product.
3. For product quotes, use the confirmed quantity from the prompt/quote line. Ignore prior quote quantities and prior unit prices unless the template explicitly asks for them.
4. For module RFQs, quote only `requested_modules` at module level. Do not explode component composition notes into component SKUs.
5. Select the catalog tier where `min_qty <= quantity <= max_qty`, treating `max_qty: null` as no upper bound.
6. Fill product fields from the selected product/tier:
   - `article_number` from product
   - `unit_price` / `unit_price_usd` from tier
   - `lead_time_days` from tier
   - `shelf_life_months` from product
   - `line_total = quantity * unit_price`
   - `exw_total_usd = confirmed_quantity * unit_price_usd`
7. Payment terms:
   - New NGO or no approved credit history: `PREPAY_100`.
   - Recurring NGO or active account with `payment_profile`: use the customer's `payment_profile` unless a policy overrides it.
   - For policy flag labels, prefer concise account class labels such as `RECURRING_NGO` when the template does not ask for a policy ID.
8. Quote validity and controls:
   - Standard catalog quote validity is 30 days when `POL-QUOTE-VALIDITY` applies.
   - Indicative quotes without confirmed destination are `EXW_ONLY` and exclude freight.
   - If the template has `who_documentation_required: true` for a new NGO module quote and no separate fee line exists, include the standard 200.00 documentation/control allowance in the control `grand_total`; keep product line totals as pure catalog math.

## Freight SOP

Use this path when the prompt asks for freight options, transport comparison, route risk, source validity, reconfirmation, or recommended mode.

1. Fetch `/api/freight-quotes` and filter by the exact `quote_id`.
2. Exclude distractors: wrong shipment size, `mismatch`, stale historical benchmarks, unrelated quote IDs, or superseded routes unless the prompt/template asks to flag stale source-validity concerns.
3. When the template asks for "three current freight options", include the current AIR, SEA, and ROAD records for that quote and exclude stale/distractor records.
4. When the prompt asks for validity/source concerns, include the relevant stale option if it is the only option for its mode or the quote notes call it out. Mark it stale rather than silently dropping it.
5. Field mapping:
   - `freight_id`: freight record `id`
   - `mode`: uppercase freight `mode`
   - `freight_cost_usd`: `cost_usd`
   - `valid_until`: freight `valid_until`
   - `grand_total_usd = exw_total_usd + freight_cost_usd`
   - `validity_status`: `VALID` when `status` is active and `valid_until >= quote_date`; `STALE` when status is stale or validity expired.
   - `source_is_stale`: true for stale or expired records, false otherwise.
6. Transit-day formatting follows the template family:
   - If the expected field is a plain freight-option display, copy `transit_days_text` such as `4-6 days`.
   - If the template's transport-decision fields use compact ranges, strip the trailing word and use `3-5`.
7. Risk fields:
   - For generic `risk_level`, use freight `route_risk` uppercased.
   - For `risk_flag`, use `NONE` for low risk, `MEDIUM_BORDER_RISK` for medium road/border risk, and `HIGH_BORDER_RISK` for high road/border risk.
   - For `customs_border_risk`, derive border/customs risk from `risk_notes`: use `HIGH` or `MEDIUM` only when customs/border risk is actually stated; otherwise use `LOW` even if a non-border route risk is medium.
8. Freight policy:
   - Freight always requires reconfirmation at final order when `POL-FREIGHT-RECONFIRM` applies.
   - `all_freight_options_valid_on_quote_date` is true only when every included freight option is active and valid on the quote date.
9. Recommended mode:
   - Prefer the lowest-cost valid mode with acceptable route/customs risk.
   - Exclude stale/expired options from recommendation.
   - SEA is usually preferred when valid, low/customs-low, and no urgent delivery deadline overrides it.
   - AIR can win when time-critical delivery or product handling risk makes SEA unsuitable.

## Opportunity Reconciliation SOP

Use this path when the template asks for `account_status`, `engagement_reconciliation`, `milestones`, `invoice_actions`, `revenue_recognition`, `event`, `event_actions`, or follow-up tasks.

1. Fetch the opportunity by ID, the customer by customer ID, and the full `invoices`, `payments`, `revenue-journals`, `events`, and `vouchers` collections.
2. Filter invoices, payments, journals, events, and vouchers by the exact opportunity ID and customer ID.
3. Sort opportunity phases in business order. Normalize milestone output IDs to `MS1`, `MS2`, `MS3`, etc. when the template uses that enum or examples. Use these normalized IDs consistently in milestones, recognition lists, and action tasks.
4. Reconcile totals:
   - `phase_total_amount` or milestone sum = sum of opportunity phase amounts.
   - `opportunity_matches_phase_total` / `opportunity_matches_milestones` compares that sum to `won_amount_usd`.
   - `total_paid_amount` = sum of posted payments or invoice paid amounts for the opportunity.
   - `outstanding_balance` = sum of invoice outstanding amounts, or the opportunity outstanding field if the template wants the account status roll-up.
5. Invoice and payment states:
   - Fully paid invoice: invoice state `PAID`, payment state `PAID`, paid amount = invoice amount, due date `null`.
   - Partially paid invoice: payment state `PARTIAL`, amount unpaid = invoice amount minus paid amount.
   - Unpaid non-void invoice: invoice state `OPEN` when the enum uses open/closed states; payment state `UNPAID`.
   - Void invoice: `VOID`.
6. Revenue recognition:
   - Paid milestone with a posted revenue journal: `RECOGNIZED`.
   - Paid milestone without a posted revenue journal: `MISSING_REVENUE_JOURNAL` or `REQUIRED_MISSING`, matching the template enum.
   - Unpaid milestone: `NOT_REQUIRED_UNPAID`.
   - Roll-up status is complete only when every paid milestone has a posted journal.
   - `recognized_amount` is the sum of posted revenue journals for the opportunity.
7. Accounting actions:
   - If a paid milestone is missing its revenue journal, create the template's record-revenue action for that milestone, with debit `DEFERRED_REVENUE`, credit `IMPLEMENTATION_SERVICES_REVENUE`, and owner `ACCOUNTING`.
   - If no paid milestone is missing recognition, use the template's no-action or verify-only controlled value.
8. Collection actions:
   - If an unpaid milestone due date is after the `as_of_date`, use monitor-not-due action values and owner `ACCOUNT_MANAGEMENT`.
   - If an unpaid milestone is due or overdue, use collection-notice action values and owner `COLLECTIONS`.
   - Paid milestones should normally have `due_date: null`; do not keep old invoice due dates after payment.
   - If a raw invoice due date conflicts with a future phase/completion schedule, prefer the account-ready follow-up due date implied by the prompt or business schedule rather than blindly copying a date that would trigger premature collection.
9. Event and voucher actions:
   - Match event by event ID when provided; otherwise by customer/opportunity.
   - Match voucher by event `voucher_code` or the prompt's voucher code.
   - Map statuses to uppercase template enums: `scheduled`/`confirmed` -> scheduled or active-style enum required by the template, `active` -> `ACTIVE`, `completed` -> `COMPLETED`, disabled/expired/draft accordingly.
   - Voucher discount fields use `discount_percent` as the numeric discount value. `max_uses` or `voucher_max_uses` comes from `max_redemptions`.
   - For a future scheduled/confirmed event with an active voucher, use the send-invite action unless the records show the invite was already sent.

## Common Pitfalls

- Do not use the prior quote tier when a revised quantity puts the product into a different catalog tier.
- Do not include composition notes as commercial line items for module RFQs.
- Do not include stale freight unless the task asks for source-validity or stale-route warnings.
- Do not recommend the cheapest freight option if it is expired, stale, or high customs/border risk.
- Do not treat all `route_risk: medium` values as customs/border risk; read the risk notes.
- Do not emit API phase IDs like `HEL-P1` when the template expects normalized milestone IDs such as `MS1`.
- Do not keep due dates for paid milestones in reconciliation outputs; paid milestones usually report `due_date: null`.
- Do not assume the API customer name always matches the prompt's account-facing name; use prompt display names for human-facing `customer_name` fields when they conflict.
- Do not forget event/voucher follow-up records when the prompt asks for account-ready reconciliation; they are part of the same decision package.
- Recompute grand totals and compare them against quote controls. Some account-ready controls include non-line documentation allowances, so line totals and grand totals may intentionally differ only when the template/control policy implies it.
