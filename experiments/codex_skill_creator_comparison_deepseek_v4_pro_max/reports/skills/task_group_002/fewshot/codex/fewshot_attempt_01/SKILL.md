---
name: medbridge-sales-ops
description: Prepare quote decision packages, RFQ-to-quote line items, and engagement reconciliations from the MedBridge Sales Ops API. Use for (1) building a quote + freight comparison from a quote ID, (2) generating EXW quote line items from an RFQ ID, (3) reconciling a won opportunity with invoices, payments, revenue journals, events, and vouchers. The API serves humanitarian medical supply CRM data including customers, products with quantity-tier pricing, freight quotes with risk/validity flags, milestones, and policies.
---

# MedBridge Sales Ops

## Overview

This skill covers three core workflows against the shared MedBridge Sales Ops API.
The API base URL is provided by the runner as `<TASK_ENV_BASE_URL>`.
Every response must be valid JSON matching the supplied answer template; include no
markdown or narrative outside the JSON.

Consult [api_endpoints.md](references/api_endpoints.md) for the full endpoint catalog
and entity relationships. Consult [policies.md](references/policies.md) for business
rules on payment terms, freight validity, revenue recognition, and module granularity.

## Workflow 1: Quote + Freight Decision Package

Triggered when given a quote ID and a confirmed quantity/date. The output
includes EXW pricing, three freight modes (air/sea/road) with totals, risk
flags, and policy recommendations.

### Step 1 -- Gather records

Fetch in parallel:
- `GET /api/quotes/<quote_id>`
- `GET /api/customers/<customer_id>` (from quote)
- `GET /api/products/<product_code>` (from quote's `primary_product_code`)
- `GET /api/freight-quotes` (filter by `quote_id` to the target quote)
- `GET /api/policies`

### Step 2 -- Select the catalog tier

From the product's `price_tiers[]`, find the tier where `confirmed_quantity`
falls in `[min_qty, max_qty]`. `max_qty: null` means unbounded upper limit.
Use that tier's `unit_price_usd`, `lead_time_days`. Take `shelf_life_months`
from the product root.

```
exw_total_usd = confirmed_quantity * unit_price_usd
```

### Step 3 -- Filter freight quotes

Keep only records where:
- `quote_id` matches the target quote
- `status` is `active` (discard `stale` and `mismatch`)
- `mode` is one of air, sea, road for the target quote

Ignore distractor freight records tied to other quotes or with wrong shipment
dimensions.

### Step 4 -- Validate and flag freight

For each mode:
- `validity_status`: `VALID` if `valid_until >= quote_date`, else `STALE`
- `source_is_stale`: true if `valid_until < quote_date`
- `risk_flag`: map `route_risk` low->NONE, medium->MEDIUM_BORDER_RISK, high->HIGH
- `grand_total_usd = exw_total_usd + freight_cost_usd`

A stale road quote with high border risk should not be recommended.

### Step 5 -- Apply policy rules

- `recommended_mode`: prefer SEA when valid and low-risk; AIR for urgent
  deadlines; avoid stale/high-risk road
- `freight_reconfirmation_required`: true whenever freight is presented
- `all_freight_options_valid_on_quote_date`: false if any mode is stale
- `payment_terms`: from customer's `payment_profile` or policy match
- `customer_policy`: derive from segment (e.g., `RECURRING_NGO`,
  `RECURRING_COMMERCIAL`, `NEW_CLIENT`, `MILESTONE_BILLING`)

### Validation checklist

- Confirm the total is `confirmed_quantity * unit_price_usd`
- Check every `grand_total_usd = exw_total + freight_cost`
- Verify `payment_terms` matches the customer's payment profile
- Verify freight validity dates are compared against `quote_date`

## Workflow 2: RFQ-to-Quote (Indicative / EXW-Only)

Triggered when given an RFQ ID, typically for a new/prospect customer with no
confirmed destination. Produce EXW-only line items at module granularity.

### Step 1 -- Gather records

Fetch in parallel:
- `GET /api/rfqs/<rfq_id>`
- `GET /api/customers/<customer_id>` (from RFQ)
- `GET /api/policies`
- For each `product_code` in `requested_modules[]`, fetch `GET /api/products/<code>`

### Step 2 -- Build line items

For each `requested_module`:
- Use `product_code` and `quantity` directly from the RFQ
- Get `article_number` from product
- Get `unit_price` from the product's price tier matching `quantity`
- `line_total = quantity * unit_price`
- `lead_time_days` and `shelf_life_months` from the matching tier / product

**Keep modules whole.** The RFQ's `component_composition_distractors[]` and
the product's `components[]` are for medical review only; do not split into
component SKUs.

### Step 3 -- Set quote controls

- `grand_total`: sum of all `line_total` values
- `freight_excluded`: true (no destination -> EXW only)
- `payment_terms`: `PREPAY_100` for new/prospect customers; otherwise from
  customer's `payment_profile`
- `offer_validity_days`: 30
- `who_documentation_required`: true for IEHK-style modules; false otherwise

## Workflow 3: Engagement Reconciliation

Triggered when given an opportunity ID and customer ID. Produces a full
reconciliation with milestone states, revenue recognition gaps, collection
tasks, and event/voucher follow-ups.

### Step 1 -- Gather records

Fetch in parallel:
- `GET /api/opportunities/<opp_id>`
- `GET /api/customers/<customer_id>`
- `GET /api/invoices` (filter by `opportunity_id`)
- `GET /api/payments` (filter by `opportunity_id`)
- `GET /api/revenue-journals` (filter by `opportunity_id`)
- `GET /api/events` (filter by `opportunity_id`)
- `GET /api/vouchers` (find the one matching the event's `voucher_code`)

### Step 2 -- Reconcile milestones

For each phase in `opportunity.phases[]`:

1. Find the matching invoice by `invoice_id` (from phase) or `phase_id`
2. Determine `payment_state`: PAID if `paid_amount_usd == amount_usd`,
   PARTIAL if `0 < paid_amount < amount`, else UNPAID
3. Determine `recognition_status`:
   - If paid and journal exists -> `RECOGNIZED`
   - If paid and journal missing -> `MISSING_REVENUE_JOURNAL`
   - If unpaid -> `NOT_REQUIRED_UNPAID`
4. `due_date` from invoice, or null if paid

### Step 3 -- Revenue recognition summary

- `recognition_status`: `COMPLETE_FOR_PAID_MILESTONES` if every paid milestone
  has a journal; `MISSING_FOR_PAID_MILESTONES` if any paid milestone lacks one
- `recognized_milestones[]`: list of milestone IDs with journals
- `missing_required_milestones[]`: list of paid milestone IDs without journals
- `recognized_amount`: sum of recognized journal amounts

### Step 4 -- Follow-up tasks

Generate tasks for:

**Collections** -- for each unpaid/overdue milestone:
- If `due_date` is in the future: `MONITOR_UNPAID_NOT_DUE`, owner `ACCOUNT_MANAGEMENT`
- If `due_date` is in the past: `SEND_COLLECTION_NOTICE`, owner `COLLECTIONS`

**Revenue recognition** -- for each paid milestone missing a journal:
- Action: `RECORD_REVENUE_MSx`, owner `ACCOUNTING`
- Debit: `DEFERRED_REVENUE`, Credit: `IMPLEMENTATION_SERVICES_REVENUE`

**Event invitations** -- for each event linked to the opportunity that is
`scheduled` or `confirmed` with a future date:
- Action: `SEND_EVENT_INVITATION` or `SEND_BRIEFING_INVITE`
- Include `event_id`, `voucher_code`, contact info
- Owner: `ACCOUNT_MANAGEMENT`

### Step 5 -- Cross-check totals

- `phase_total_amount` = sum of all phase `amount_usd` values
- `total_paid_amount` = sum of all `paid_amount` values from invoices
- `outstanding_balance` = `won_amount - total_paid_amount`
- `opportunity_matches_phase_total`: true if `won_amount == phase_total_amount`

## Common Pitfalls

- **Distractor freight records**: The freight-quotes collection includes records
  for unrelated quotes, with stale/mismatch statuses, wrong dimensions, or
  different `quote_id` values. Always filter by `quote_id` and `status: active`.
- **Component-composition distractors**: RFQs and products list component
  breakdowns that are for medical review only. Quote at the module/product
  level unless the prompt explicitly asks for component-level pricing.
- **Old tier traps**: Prior quotes used different quantities. Always use the
  current `confirmed_quantity` against the product's `price_tiers[]`; never
  reuse `prior_unit_price_usd` from the quote line item.
- **Stale freight validity**: Check `valid_until` against `quote_date` --
  a freight quote expired before the quote date is unusable even if its
  `status` field still says `active`.
- **Missing revenue journals**: A paid milestone without a corresponding
  revenue journal entry is an accounting gap. Flag it, don't assume it exists.
- **New-client payment terms**: Prospect customers always use `PREPAY_100`,
  regardless of what a similar-looking active customer uses.
