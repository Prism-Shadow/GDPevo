## When to Use

Use this skill whenever you need to solve structured business-operations tasks against a shared REST API that exposes CRM, quoting, logistics, invoicing, payment, revenue-recognition, event, and policy records. Typical task types include:

- Preparing quote decision packages with product pricing, freight comparisons, and policy flags.
- Reconciling won opportunities against milestone invoices, payments, and revenue journals.
- Building finance-ready engagement summaries that combine opportunity state, accounting actions, collection tasks, and event/voucher follow-ups.

## API Discovery and Navigation

Every task provides a base URL. Begin by calling the API root to confirm the service and list available collections:

```
GET {base_url}/api
```

The response includes a `collections` array and an `endpoints` list. Use these to plan which records you need.

### Primary Lookup Endpoints

All collection-level lists and individual-record lookups follow the pattern:

```
GET {base_url}/api/{collection}
GET {base_url}/api/{collection}/{id}
```

### Cross-Reference with Search

When you need all records tied to a customer, opportunity, or quote, use the search endpoint. It returns matching records across every collection:

```
GET {base_url}/api/search?q={text}
```

Pass a customer ID, opportunity ID, quote ID, or any identifying token. The response groups results by `collection` and includes the full record under `record`. This is the fastest way to gather invoices, payments, revenue journals, events, and vouchers linked to a single engagement.

### Collections Reference

| Collection | Key Fields | Used For |
|---|---|---|
| `customers` | id, name, customer_type, is_recurring, payment_profile, segment, country, region, contacts | Identifying the account, determining payment terms, finding primary contacts |
| `products` | code, article_number, price_tiers, lead_time_days, shelf_life_months, cold_chain_required, components | Pricing by quantity tier, lead times, shelf-life checks |
| `quotes` | id, customer_id, quote_date, line_items, confirmed_quantity, primary_product_code, status | Quote revision data, product and quantity confirmation |
| `rfqs` | id, customer_id, requested_modules, quote_date, incoterm_requested | Indicative quote requests, module-level pricing |
| `freight-quotes` | id, quote_id, mode, cost_usd, transit_days_text, valid_until, route_risk, status, cold_chain_support, risk_notes | Freight cost comparison, validity checks, route risk assessment |
| `policies` | id, policy_area, rule, terms_code, applies_to | Determining payment terms, quote scope, freight reconfirmation, revenue recognition rules |
| `opportunities` | id, customer_id, stage, won_amount_usd, phases, outstanding_amount_usd, contact | Reconciliation source-of-truth for won deals |
| `invoices` | id, customer_id, opportunity_id, amount_usd, status, paid_amount_usd, outstanding_amount_usd, due_date, phase_id | Milestone billing state |
| `payments` | id, invoice_id, opportunity_id, amount_usd, status, payment_date | Payment verification against invoices |
| `revenue-journals` | id, invoice_id, opportunity_id, phase_id, amount_usd, debit_account, credit_account, status | Revenue recognition state per milestone |
| `events` | id, customer_id, opportunity_id, event_date, status, voucher_code, primary_contact | Event follow-up routing |
| `vouchers` | code, event_id, discount_percent, max_redemptions, status, valid_until | Voucher controls for event invitations |

## Price Tier Matching

Products expose a `price_tiers` array. Each tier defines a quantity bracket:

```
{
  "min_qty": N,
  "max_qty": M | null,
  "unit_price_usd": P,
  "lead_time_days": D,
  "shelf_life_months": S
}
```

**Matching rule**: Find the single tier where `min_qty <= confirmed_quantity <= max_qty`. A `null` `max_qty` means no upper bound. Use that tier's `unit_price_usd`, `lead_time_days`, and `shelf_life_months`. Report the tier boundaries (`min_quantity`, `max_quantity`) alongside the pricing when the output template asks for catalog-tier details.

**EXW total**: `confirmed_quantity × unit_price_usd`.

**Grand total with freight**: `exw_total_usd + freight_cost_usd`.

## Freight Quote Processing

### Finding Relevant Freight Quotes

Freight quotes link to their parent quote via `quote_id`. Filter the freight-quotes collection or search results by matching `quote_id` to the quote being processed. Expect exactly one freight record per mode (air, sea, road) for a given quote.

### Validity Check

Compare each freight quote's `valid_until` date against the quote date (`quote_date`):

- **Valid**: `valid_until >= quote_date` → the quote is current for the requested date.
- **Stale/Expired**: `valid_until < quote_date` → the quote was already expired when the quote was requested. Flag these explicitly.

Some freight records carry an explicit `status` field with values like `active`, `stale`, or `mismatch`. A `stale` status always means the quote is invalid.

### Route Risk Assessment

Use the `route_risk` field (values: `low`, `medium`, `high`) and `risk_notes` to populate risk flags and warnings:

- `low` → no risk flag (or `NONE`)
- `medium` → flag with the specific concern mentioned in `risk_notes` (e.g., border risk, port congestion)
- `high` → flag as high risk; typically accompanies stale quotes

### Freight Comparison Output

For each mode, report:
- `freight_id`, `mode`, `freight_cost_usd`, `transit_days` (use `transit_days_text`)
- `valid_until`, validity status (VALID / STALE / EXPIRED)
- Whether the source is stale (`source_is_stale`: true when `status` is `stale` or `valid_until < quote_date`)
- Customs/border risk level derived from `route_risk`
- `grand_total_usd` = EXW total + freight cost

### Recommended Mode

Among valid (non-stale) freight options, recommend the mode with the lowest `route_risk` that balances cost. If multiple valid options exist with the same risk level, prefer the one with lower cost. Never recommend a stale/expired freight option. If the only low-risk option is significantly more expensive, the cheaper medium-risk option may be the practical recommendation — let cost-effectiveness guide the choice when risk is moderate.

### Freight Reconfirmation

The `POL-FREIGHT-RECONFIRM` policy states that all freight rates require reconfirmation at final order. Always set `freight_reconfirmation_required` to `true` and include a warning when any freight option is stale or has elevated route risk.

## Policy Application

Policies are stored in the `policies` collection and encode business rules. Match policies to the customer and quote context:

### Payment Terms

1. Check `customers.is_recurring` and `customers.customer_type`.
2. **New NGO** (`is_recurring: false`, `customer_type: "NGO"`): apply `PREPAY_100` (policy `POL-NEW-CLIENT-PAYMENT`).
3. **Recurring NGO** (`is_recurring: true`, `customer_type: "NGO"`): use the customer's `payment_profile` (typically `NET_30_AFTER_PO`; policy `POL-RECURRING-NGO-PAYMENT`).
4. **Commercial / Government Program**: use the customer's `payment_profile` directly (e.g., `NET_30_AFTER_PO`, `MILESTONE_BILLING`).
5. If the customer has `grant_terms` that impose restrictions, note them but use the standard policy unless a specific policy overrides.

### Quote Scope

- **EXW with freight options**: quote type `quote_revision_with_freight` → include both EXW pricing and freight comparisons.
- **Indicative / EXW-only**: when no destination is confirmed or `incoterm_requested` is `EXW` without freight → quote basis is `EXW_ONLY`, exclude freight, set `freight_excluded: true`.
- **Module-level quotes**: when an RFQ requests modules, quote at the module product-code level. Do not split modules into their `components` unless explicitly asked. Policy `POL-MODULE-GRANULARITY`.

### Quote Validity

Standard quote pricing is valid for 30 calendar days from `quote_date` (policy `POL-QUOTE-VALIDITY`). Use `offer_validity_days: 30` as the default.

### WHO Documentation

When quoting WHO-standard kits (IEHK modules, emergency health kits), set `who_documentation_required: true`.

## Revenue Reconciliation

When reconciling a won opportunity, follow this systematic approach:

### Phase-to-Milestone Mapping

Each phase in the opportunity maps to a milestone. Use `phase_id` as the milestone identifier. The `amount_usd` from the phase is the milestone amount. Sum all phase amounts and compare to `won_amount_usd` to confirm they agree.

### Invoice and Payment State

For each milestone, find its invoice by matching `phase_id` or `invoice_id`:
- **Invoice state**: derived from invoice `status` (`paid` → PAID, `unpaid` → OPEN/UNPAID, `draft` → OPEN).
- **Payment state**: if a payment record exists for the invoice with `status: "posted"`, the milestone is PAID. If `paid_amount_usd < amount_usd`, it is PARTIAL. Otherwise UNPAID.

### Revenue Recognition State

For each milestone, look for a revenue journal (`revenue-journals` collection) matching the `phase_id` or `invoice_id`:

- **RECOGNIZED**: A posted revenue journal exists for the milestone.
- **MISSING_REVENUE_JOURNAL**: The milestone invoice is PAID but no revenue journal exists. This requires an accounting action to record revenue.
- **NOT_REQUIRED_UNPAID**: The milestone is not yet paid. Revenue recognition is not yet required.

The policy `POL-REVREC` governs this: "When a milestone is complete and paid, create or verify revenue recognition from deferred revenue to income."

### Accounting Actions

When a paid milestone lacks a revenue journal:
- **Action**: `RECORD_REVENUE_MS{n}` for the affected milestone.
- **Journal entry**: Debit `DEFERRED_REVENUE`, Credit `IMPLEMENTATION_SERVICES_REVENUE`.
- **Owner queue**: `ACCOUNTING`.
- **Amount**: the milestone amount.

When all paid milestones are recognized and unpaid milestones are not yet due:
- **Action**: `VERIFY_REVENUE_ONLY` or `NO_ACCOUNTING_ACTION` depending on the template.

### Collection Follow-Up

- **Due and unpaid**: `SEND_COLLECTION_NOTICE` for overdue unpaid milestones.
- **Not yet due**: `MONITOR_UNPAID_NOT_DUE` for future-dated unpaid milestones.
- **Fully paid**: `NO_COLLECTION_ACTION`.
- **Owner queue**: `ACCOUNT_MANAGEMENT` for monitoring; `COLLECTIONS` for active collection.
- Always include the primary contact name from the opportunity or customer record.

## Event and Voucher Integration

When an opportunity has linked events and vouchers:

1. Match events by `opportunity_id` and/or `customer_id`.
2. For each event, retrieve the linked voucher by `voucher_code`.
3. Report the event status (`scheduled`, `confirmed`, `active`, `completed`, `cancelled`).
4. Report voucher details: code, status (`active`, `draft`, `expired`, `disabled`), discount value (use `discount_percent` as the numeric discount amount), `max_uses` (from `max_redemptions`).
5. For scheduled/confirmed events with active vouchers, create an invitation follow-up task:
   - **Action**: `SEND_BRIEFING_INVITE` (or `VERIFY_INVITE_SENT` if already sent).
   - **Owner queue**: `ACCOUNT_MANAGEMENT` (the event's `follow_up_owner` field may guide this).
   - **Contact**: the event's `primary_contact` or the opportunity's contact.

## Systematic Resolution Checklist

For every task, work through these steps in order:

1. **Read the prompt** carefully. Identify the task type (quote package, indicative quote, reconciliation, engagement summary) and note all IDs, dates, quantities, and contact names mentioned.
2. **Start with the root record**: the quote, RFQ, or opportunity identified in the prompt.
3. **Pull the linked customer** to get payment_profile, customer_type, is_recurring, contacts, and country.
4. **Pull product(s)** and match price tiers by quantity.
5. **Search for all related records** using the customer ID or opportunity ID to gather invoices, payments, revenue journals, events, vouchers, and freight quotes in one call.
6. **Pull policies** and match the applicable rules to the customer profile and task context.
7. **Compute pricing**: EXW totals, freight-inclusive grand totals.
8. **Validate freight**: check validity dates, assess route risks, identify stale quotes, recommend a mode.
9. **Reconcile milestones**: verify phase totals match won amount, check invoice/payment state, check revenue journal coverage.
10. **Determine actions**: accounting actions for missing revenue journals, collection actions for unpaid invoices, event invitation actions for scheduled events.
11. **Fill the template**: use exact field names from the answer template. Ensure money values have two decimal places. Use ISO dates. Use controlled enum values exactly as declared in the template. Do not include markdown or explanatory text outside the JSON.
