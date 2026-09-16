---
name: medbridge-sales-ops
description: |
  Build account-ready JSON decision packages from the MedBridge Sales Ops API.
  Use this skill whenever the user asks you to prepare a quote, quote revision,
  RFQ response, account reconciliation, engagement reconciliation, freight
  comparison, payment review, revenue recognition check, or any MedBridge
  CRM/quote/logistics decision. The API is always at the base URL the user
  provides as `<TASK_ENV_BASE_URL>`. The user always provides an
  `answer_template.json` payload that defines the exact JSON shape; fill it by
  pulling records from the API and applying the business rules described here.
---

# MedBridge Sales Ops

## Overview

This skill covers the MedBridge Sales Ops shared API, which provides CRM,
quote, logistics, and milestone engagement data for preparing account-ready
decision packages. Your job is to verify records through the API, apply
business rules, and fill the user-provided answer template with accurate
values - returning **only valid JSON** with no markdown or explanation.

The API base URL is provided in the user prompt as `<TASK_ENV_BASE_URL>`.
Use it for all API calls. The API is read-only GET; no write endpoints are
available.

## Task families

There are two broad families - identify which one the user is asking for:

1. **Quote / RFQ packages** - verify a customer, product catalog, quote/RFQ
   record, freight quotes, and policies, then output pricing, transport
   options, and policy flags.
2. **Account / engagement reconciliations** - verify an opportunity, its
   milestone invoices, payments, revenue journals, linked events, and
   vouchers, then output reconciliation status, accounting actions, and
   follow-up tasks.

Extract the entity IDs from the prompt (`quote_id`, `rfq_id`,
`opportunity_id`, `customer_id`, `product_code`, `voucher_code`,
`event_id`) before making calls.

## Step 1 - Gather records from the API

Use `curl -s` against `{TASK_ENV_BASE_URL}/api/{collection}` or
`.../api/{collection}/{id}`. Parallelize reads.

**For quote/RFQ tasks**:
- `GET /api/quotes/{quote_id}` or `GET /api/rfqs/{rfq_id}`
- `GET /api/customers/{customer_id}`
- `GET /api/products/{product_code}` for every product involved
- `GET /api/freight-quotes` (the full list; filter client-side by
  `quote_id`)
- `GET /api/policies`

**For reconciliation tasks**:
- `GET /api/opportunities/{opportunity_id}`
- `GET /api/customers/{customer_id}`
- `GET /api/invoices`, `GET /api/payments`, `GET /api/revenue-journals`
  (the full lists; filter client-side by `opportunity_id` or `invoice_id`)
- `GET /api/events` (filter by `opportunity_id` or specific `event_id`)
- `GET /api/vouchers` (filter by `voucher_code` or `opportunity_id`)
- `GET /api/policies`

**Filtering**: collection endpoints return all records. Use `python3 -c`
with `json.loads()` and list comprehensions to filter on fields like
`quote_id`, `opportunity_id`, `customer_id`, `invoice_id`. The
`GET /api/search?q=...` endpoint accepts a free-text query as a fallback.

## Step 2 - Price-tier selection (quote/RFQ tasks)

Every product has a `price_tiers` array. Each tier has `min_qty`, `max_qty`
(`null` means no upper limit), `unit_price_usd`, and `lead_time_days`.

Select the single tier where:

  min_qty <= confirmed_quantity <= max_qty  (null max_qty = infinity)

For a quote revision, the record may carry `prior_quote_quantity` and
`prior_unit_price_usd` - ignore those for pricing; always use the tier
matching the **confirmed quantity**. The new quantity can change the tier.

Some products have only one tier (e.g. `min_qty: 1, max_qty: null`) -
that tier applies at any quantity.

Take `shelf_life_months` directly from the product record. Compute
`exw_total_usd` as `confirmed_quantity x unit_price_usd`, rounded to
two decimals.

## Step 3 - Freight quote handling (quote tasks with freight)

Collect freight quotes linked to the parent quote by filtering the freight
list on `quote_id`. Typically there are three (air, sea, road). For each:

- `id`, `mode`, `cost_usd`, `transit_days_text`, `valid_until`,
  `route_risk` (`low` / `medium` / `high`), `risk_notes`,
  `cold_chain_support`

Compute **grand total**: `exw_total_usd + freight_cost_usd` (two decimals).

**Validity**: a freight quote is valid on the quote date if
`valid_until >= quote_date`. If `valid_until < quote_date`, the quote is
**stale** - mark it stale in output and do not recommend it. Note the
expiration date in any warning text.

**Route risk / flags**: map the API `route_risk` and `risk_notes` to the
controlled vocabulary the answer template expects. Read `risk_notes` for
context - it often contains the specific risk description (e.g. border
risk, port congestion, customs).

**Recommended mode**: among **valid** freight quotes only, recommend the
one with the lowest `cost_usd`. Skip stale quotes for this calculation.

**Cold chain**: when the product has `cold_chain_required: true`, prefer a
freight quote with `cold_chain_support: true` if one exists; note the
requirement in risk/warning fields.

## Step 4 - Revenue recognition (reconciliation tasks)

For each phase in `opportunity.phases`, cross-reference with invoices,
payments, and revenue journals:

1. **Find the invoice** - match on `phase.invoice_id` = `invoice.id`.
2. **Payment state** - if `invoice.outstanding_amount_usd == 0` the invoice
   is fully paid. If `invoice.paid_amount_usd == 0` it is unpaid.
   Otherwise partial.
3. **Revenue journal** - look for a journal entry whose `invoice_id` or
   `phase_id` matches. Revenue journals debit `Deferred Revenue` and credit
   `Implementation Services Revenue`.
4. **Assign recognition status**:
   - Paid AND journal exists -> `RECOGNIZED`
   - Paid AND no journal -> `MISSING_REVENUE_JOURNAL`
   - Unpaid -> `NOT_REQUIRED_UNPAID`

**Opportunity totals**: when the stage is `closed_won`, verify that
`won_amount_usd` equals the sum of all phase `amount_usd` values. Report
whether they match. Compute **outstanding balance** as the sum of all
`outstanding_amount_usd` across invoices for this opportunity.

## Step 5 - Policy interpretation

Read all policies from `GET /api/policies`. Match each policy to the task
by its `applies_to` and `policy_area` fields. Key policies to check:

- **Payment terms** - match customer segment (`new NGO` vs
  `recurring NGO` vs `recurring commercial`). New NGO accounts require
  `PREPAY_100`. Recurring accounts use `NET_30_AFTER_PO` unless grant terms
  restrict further. Check the customer record's `payment_profile` and
  `grant_terms` fields for overrides.

- **Quote scope** - if the RFQ or quote has no confirmed destination,
  quote EXW-only with freight excluded. If destination is present, use
  EXW plus freight options.

- **Freight reconfirmation** - freight rates must be reconfirmed at final
  order. This flag is always true; include it even when all freight quotes
  are currently valid.

- **Module granularity** - when quoting from an RFQ, stay at the
  module/product level. Do **not** break products into their `components`
  arrays unless the prompt or RFQ explicitly asks for component-level
  pricing. The API may list `components` and
  `component_composition_distractors` - these are for medical review and
  should not expand the quote lines.

- **Revenue recognition** - paid and completed milestones must have a
  matching revenue journal entry. Unpaid future milestones remain
  outstanding and drive collection tasks when due or overdue.

- **Quote validity** - catalog pricing is valid for 30 calendar days from
  the quote date. Use this for `offer_validity_days` when the template
  asks for it.

## Step 6 - Event and voucher handling (reconciliation tasks)

Events link to an opportunity via `opportunity_id` and to a customer via
`customer_id`. Vouchers link to events via `event_id` and to an opportunity
via `opportunity_id`.

- Map event `status` to the template's controlled vocabulary (uppercase
  the API value: `scheduled` -> `SCHEDULED`,
  `confirmed` -> `SCHEDULED`).
- Voucher `discount_percent` -> the discount amount field in the template.
- Voucher `max_redemptions` -> max uses field.
- Check `valid_until` for voucher currency.

**Invite actions**: if the event is active/scheduled/confirmed and the
template requires an invite action, use `SEND_BRIEFING_INVITE` (or the
template's equivalent). Assign the follow-up owner to `ACCOUNT_MANAGEMENT`
unless the API event record's `follow_up_owner` says otherwise.

## Step 7 - Follow-up / collection tasks (reconciliation tasks)

For each unpaid milestone whose `due_date` is in the future (relative to
the current business date), create a **monitor** task
(`MONITOR_UNPAID_NOT_DUE`). For overdue unpaid milestones, create a
**collection** task (`SEND_COLLECTION_NOTICE`).

For each milestone that is **paid but missing a revenue journal**, create an
**accounting action** (`RECORD_REVENUE_MS{n}`) with:

- `debit_account`: `DEFERRED_REVENUE`
- `credit_account`: `IMPLEMENTATION_SERVICES_REVENUE`
- `owner_queue`: `ACCOUNTING`

Assign collection tasks to `ACCOUNT_MANAGEMENT` and include the contact
name from the opportunity record.

## Step 8 - Fill the template and output

Read `input/payloads/answer_template.json` thoroughly. It defines the exact
field names, nesting, controlled vocabulary, and data types. Fill every
field with values from the API or computed using the rules above.

**Formatting rules**:

- All money values: USD with exactly two decimal places (trailing zeros
  required - a value like `12345.6` is wrong; use `12345.60`).
- All dates: ISO `YYYY-MM-DD`.
- All booleans: JSON `true` / `false`.
- All enum/status fields: match the controlled vocabulary shown in the
  template's `enum: ...` annotations exactly.
- `null` only where the template explicitly shows a null or `string or
  null` annotation.
- Use the exact record IDs the API returns - never invent them.
- Sort arrays (milestones by milestone_id ascending, line items by the
  order in the template, freight options by mode or as the template
  implies).

Return **only the raw JSON**. No markdown fences, no explanatory text, no
surrounding prose. The output must parse as valid JSON directly.
