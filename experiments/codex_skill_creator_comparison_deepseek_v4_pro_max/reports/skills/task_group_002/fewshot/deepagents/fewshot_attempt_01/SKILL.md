---
name: medbridge-sales-ops
description: "Complete workflow guide for the MedBridge Sales Ops shared REST API covering quote revisions with freight, indicative module quotes, and engagement reconciliations. Use when the task mentions MedBridge Sales Ops, a TASK_ENV_BASE_URL sales-operations API, or reference fields like quote_id, customer_id, product_code, freight-quotes, policies, opportunities, milestones, invoices, payments, revenue-journals, events, or vouchers. Handles three task types: (1) quote revision with freight comparison and risk assessment, (2) indicative EXW-only module quotations from RFQs, (3) opportunity milestone reconciliation with revenue recognition and event/voucher follow-up tasks."
license: MIT
compatibility: deepagents-code
---

# MedBridge Sales Ops API

## Quick start

The runner provides the API base URL as `BASE_URL`. Start every task with a health ping to confirm connectivity:

```bash
curl -s "${BASE_URL}/api"
```

The response lists all collections and endpoints. All endpoints are GET only and return JSON.

## Three task types

This skill covers three distinct task patterns. Identify which one applies from the prompt:

| Signal in prompt | Task type | See |
|---|---|---|
| `quote_id` starting with `Q-`, freight options, transport comparison | Quote revision with freight | [Quote + freight workflow](#quote--freight-workflow) |
| `rfq_id` starting with `RFQ-`, module-level quote, EXW only, no freight | Indicative module quote | [Module quote workflow](#module-quote-workflow) |
| `opportunity_id` starting with `OPP-`, milestones, invoices, payments, revenue recognition, events, vouchers | Engagement reconciliation | [Reconciliation workflow](#reconciliation-workflow) |

## Shared rules for all tasks

- Return **only valid JSON** matching the answer template in `input/payloads/answer_template.json`. No markdown, no explanatory text.
- Money values always have exactly two decimal places (`50000.00`, not `50000`).
- Dates use ISO `YYYY-MM-DD` format.
- Use stable record IDs exactly as the API returns them.
- Use only the controlled enum values declared in the template; do not invent new status strings.
- All policy records come from `GET /api/policies` (list endpoint). Match policies by `applies_to`, `policy_area`, or `terms_code` descriptor.

## API navigation

Start with the list endpoint for a collection, then filter by ID or foreign key. The list endpoints return all records; there is no server-side filtering except `/api/search?q=`. Do client-side filtering of the full response array.

Key cross-collection links:

- `quotes[].customer_id` -> `/api/customers/{customer_id}`
- `quotes[].primary_product_code` -> `/api/products/{product_code}`
- `freight-quotes[].quote_id` -> the quote being costed
- `rfqs[].customer_id` -> `/api/customers/{customer_id}`
- `rfqs[].requested_modules[].product_code` -> `/api/products/{product_code}`
- `opportunities[].customer_id` -> `/api/customers/{customer_id}`
- `invoices[].opportunity_id` -> the parent opportunity
- `payments[].opportunity_id` -> the parent opportunity; `payments[].invoice_id` -> the invoice
- `revenue-journals[].opportunity_id` -> the parent opportunity; `revenue-journals[].invoice_id` -> the invoice
- `events[].opportunity_id` -> the parent opportunity
- `vouchers[].event_id` -> the parent event; `vouchers[].code` -> use in `/api/vouchers/{code}`

For detailed field schemas of every collection, see [references/api_reference.md](references/api_reference.md).

## Quote + freight workflow

Use when the prompt names a `quote_id` (e.g., `Q-TR-WC-1187`) and asks for freight comparison, transport options, or risk flags.

### Step 1: Gather source records

```bash
QUOTE=$(curl -s "${BASE_URL}/api/quotes/<quote_id>")
CUSTOMER_ID=$(echo "$QUOTE" | python3 -c "import sys,json; print(json.load(sys.stdin)['customer_id'])")
PRODUCT_CODE=$(echo "$QUOTE" | python3 -c "import sys,json; print(json.load(sys.stdin)['primary_product_code'])")
CUSTOMER=$(curl -s "${BASE_URL}/api/customers/${CUSTOMER_ID}")
PRODUCT=$(curl -s "${BASE_URL}/api/products/${PRODUCT_CODE}")
FREIGHT=$(curl -s "${BASE_URL}/api/freight-quotes")
POLICIES=$(curl -s "${BASE_URL}/api/policies")
```

Filter `FREIGHT` to records where `.quote_id` matches the target quote. Present in order: AIR, SEA, ROAD.

### Step 2: Resolve catalog pricing tier

The product record has a `price_tiers` array. Each tier has `min_qty`, `max_qty` (nullable), `unit_price_usd`, and `lead_time_days`. Match: `min_qty <= confirmed_quantity <= max_qty` (treat null `max_qty` as unlimited). Use the tier's `unit_price_usd` and `lead_time_days`.

`exw_total_usd = confirmed_quantity * unit_price_usd`

Note: `shelf_life_months` comes from the product root, not the tier.

### Step 3: Evaluate freight options

For each freight record tied to the quote:

- `grand_total_usd = exw_total + freight.cost_usd`
- `transit_days`: use `transit_days_text`
- `valid_until`: compare against the quote date
- `validity_status`: `"VALID"` when `valid_until >= quote_date`, `"STALE"` otherwise
- `source_is_stale`: `true` when stale, `false` when valid
- Route risk: map `route_risk` -> uppercase for risk level; derive risk_flag from `route_risk` and `risk_notes`
  - `low` -> risk_level `LOW`, risk_flag `NONE`
  - `medium` -> risk_level `MEDIUM`, risk_flag `MEDIUM_BORDER_RISK`
  - `high` -> risk_level `HIGH`, risk_flag `HIGH_CUSTOMS_RISK` (or `HIGH_BORDER_RISK` depending on risk_notes)

### Step 4: Policy decisions

See [references/decision_rules.md](references/decision_rules.md) for the complete decision table.

Summary:
- **Recommended mode**: Prefer SEA when valid and low risk. If SEA is risky or the customer needs speed, recommend AIR. Flag ROAD when stale or medium/high risk.
- **Payment terms**: From customer `payment_profile`. New NGO (`NEW_CLIENT_REVIEW`, `new_ngo` segment) -> `PREPAY_100`. Recurring NGO/commercial -> `NET_30_AFTER_PO`. Milestone billing -> check opportunity.
- **Freight reconfirmation**: Always `true` per `POL-FREIGHT-RECONFIRM`.
- **All freight valid on quote date**: `true` only if every freight record's `valid_until >= quote_date`.
- **Customer policy**: Derive from customer `segment` field (e.g., `recurring_ngo`, `new_ngo`, `recurring_commercial`). Map directly or uppercase.
- **Offer validity**: 30 days per `POL-QUOTE-VALIDITY`.

## Module quote workflow

Use when the prompt names an `rfq_id` (e.g., `RFQ-TR-IEHK-204`) and says EXW only, module level, indicative, or no freight.

### Step 1: Gather source records

```bash
RFQ=$(curl -s "${BASE_URL}/api/rfqs/<rfq_id>")
CUSTOMER_ID=$(echo "$RFQ" | python3 -c "import sys,json; print(json.load(sys.stdin)['customer_id'])")
CUSTOMER=$(curl -s "${BASE_URL}/api/customers/${CUSTOMER_ID}")
POLICIES=$(curl -s "${BASE_URL}/api/policies")
```

### Step 2: Quote each requested module

For each entry in `rfq.requested_modules[]`:

```bash
PRODUCT=$(curl -s "${BASE_URL}/api/products/<product_code>")
```

When a product has a single price tier (`min_qty: 1, max_qty: null`), use it directly. Use `article_number`, `lead_time_days`, and `shelf_life_months` from the product/tier.

`line_total = quantity * unit_price_usd`

**Critical: module granularity.** Per `POL-MODULE-GRANULARITY`, quote at module line level only. Ignore `component_composition_distractors` in the RFQ -- do not split modules into component SKUs.

### Step 3: Controls

- `freight_excluded`: `true` per `POL-INDICATIVE-EXW` (no destination -> EXW only)
- `grand_total`: sum of all `line_total` values
- `payment_terms`: `PREPAY_100` for new NGO clients per `POL-NEW-CLIENT-PAYMENT`; verify against customer `payment_profile`
- `offer_validity_days`: 30 per `POL-QUOTE-VALIDITY`
- `who_documentation_required`: `true` for IEHK / emergency health kit products
- `quote_basis`: `"EXW_ONLY"`

## Reconciliation workflow

Use when the prompt names an `opportunity_id` (e.g., `OPP-TR-HELIOS`) and asks for milestone reconciliation, revenue recognition, collections, or event follow-ups.

### Step 1: Gather all related records

```bash
OPPORTUNITY=$(curl -s "${BASE_URL}/api/opportunities/<opportunity_id>")
CUSTOMER_ID=$(echo "$OPPORTUNITY" | python3 -c "import sys,json; print(json.load(sys.stdin)['customer_id'])")
CUSTOMER=$(curl -s "${BASE_URL}/api/customers/${CUSTOMER_ID}")
INVOICES=$(curl -s "${BASE_URL}/api/invoices")
PAYMENTS=$(curl -s "${BASE_URL}/api/payments")
REVJOURNALS=$(curl -s "${BASE_URL}/api/revenue-journals")
EVENTS=$(curl -s "${BASE_URL}/api/events")
POLICIES=$(curl -s "${BASE_URL}/api/policies")
```

Filter invoices, payments, revenue journals, and events by `opportunity_id`. Map each milestone to its invoice via `phase_id` / `invoice_id` cross-reference.

### Step 2: Build milestone table

For each phase in `opportunity.phases[]` (ascending by `phase_id`):

- Find the matching invoice via `invoice_id` from the phase record
- Find the matching payment via `invoice_id` from the invoice record
- Check for a revenue journal entry via `invoice_id`

### Step 3: Revenue recognition status

For each milestone:

| Payment state | Revenue journal exists | Recognition status |
|---|---|---|
| PAID | Yes | `RECOGNIZED` |
| PAID | No | `MISSING_REVENUE_JOURNAL` |
| UNPAID | -- | `NOT_REQUIRED_UNPAID` |

Per `POL-REVREC`: only paid completed milestones need revenue journals.

### Step 4: Accounting and collection actions

See [references/decision_rules.md](references/decision_rules.md) for the full decision matrix.

Summary:
- **Accounting**: If any paid milestone lacks a revenue journal -> `RECORD_REVENUE_MS{N}`. Accounts: debit `DEFERRED_REVENUE`, credit `IMPLEMENTATION_SERVICES_REVENUE`. Owner: `ACCOUNTING`.
- **Collection**: If unpaid milestone past due -> `SEND_COLLECTION_NOTICE`. If unpaid but not yet due -> `MONITOR_UNPAID_NOT_DUE`. Everything paid -> `NO_COLLECTION_ACTION`. Owner: `ACCOUNT_MANAGEMENT` with the opportunity contact.
- **Invite**: If event status is `scheduled` -> `SEND_BRIEFING_INVITE`. Fetch full voucher with `GET /api/vouchers/{code}`. Owner: `ACCOUNT_MANAGEMENT`.

### Step 5: Voucher handling

Voucher records use `discount_percent`. The template may ask for a discount *value* -- use the percent as-is (e.g., `50` from `discount_percent: 50`). Max uses comes from `max_redemptions`. Event status from the event record; expected values are `scheduled`, `confirmed`, `live`, `completed`, `tentative`. Map as needed to template enums.

## Validation checklist

Before returning JSON, verify:

1. All IDs match the API response exactly (case-sensitive)
2. Monetary sums: `exw_total = quantity * unit_price`, `grand_total = exw_total + freight_cost`, `phase_total_amount` = sum of all phase `amount_usd`
3. `opportunity_matches_phase_total`: compare `won_amount` against sum of all phase amounts
4. Dates are not in the future for staleness checks relative to the quote date or current business date
5. No markdown wrapping, no trailing commas, valid JSON
