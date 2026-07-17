# MedBridge Sales Ops API — Quote, Reconciliation & Engagement Skill

## API access pattern

All data lives at `{BASE_URL}/api/{collection}`. The API returns full collections
with a `records` array — dump the whole list and filter client-side. There are
no query parameters or server-side filters.

### Available collections

| Collection | What it holds |
|---|---|
| `customers` | Customer records with contacts, payment profiles, regions, segments |
| `quotes` | Quote headers, line items, quantities, incoterms, revision notes |
| `rfqs` | Inbound RFQs with requested modules, quantities, narrative instructions |
| `products` | Product catalog with article numbers, price tiers, lead times, shelf life |
| `freight-quotes` | Freight options keyed by `quote_id`, with modes, costs, transit, risk, validity |
| `policies` | Business rules for payment terms, quote scope, freight, revenue recognition |
| `opportunities` | CRM opportunities with phases, won amounts, outstanding balances, contacts |
| `invoices` | Invoices keyed by `opportunity_id` and `phase_id`, with payment status |
| `payments` | Payment records keyed by `invoice_id`, with amounts and dates |
| `revenue-journals` | Revenue recognition journal entries keyed by `phase_id` |
| `events` | Client events tied to opportunities, with voucher codes and status |
| `vouchers` | Discount vouchers tied to events, with discount percent, max uses, validity |

---

## Catalog pricing: tier selection

Every product has a `price_tiers` array with `min_qty`, `max_qty`, `unit_price_usd`,
`lead_time_days`, and `shelf_life_months`. When a tier's `max_qty` is `null`, it
has no upper bound.

**Rule**: Match the confirmed quantity to the tier where `min_qty <= quantity <= max_qty`
(or `max_qty` is null). The quote's own `prior_unit_price_usd` is historical only —
always use the catalog tier's current `unit_price_usd`.

**Source precedence**: The quote's `source_notes` field may explicitly direct which
tier to use (e.g. "Use active 900-1199 pack tier"). Follow that instruction.

**Module products** (IEHK-*, CHOL-*, FCLINIC-*) have a single tier starting at
min_qty 1. Use that tier regardless of quantity. The `article_number` field on
each product must be carried into line items.

**Calculation**:
```
exw_total = confirmed_quantity × tier_unit_price
grand_total = exw_total + freight_cost  (when freight applies)
line_total  = quantity × unit_price      (per line item)
```

---

## Freight: finding the right records

Freight records live in `freight-quotes`. Filter by `quote_id` to find options for
a specific quote. **Common pitfall**: the collection contains distractor records
with the same `quote_id` — identified by:

- `id` prefix `FR-DIS-` (distractor)
- `status` of `"stale"` or `"mismatch"`
- `valid_until` dates before the `quote_date`
- `shipment_cbm` or `shipment_weight_kg` that don't match the product's actual
  shipment dimensions
- `forwarder` names that differ from the main set (e.g. "Atlas Freight",
  "BridgePort Forwarding" when the real forwarders are "SkyBridge", "BlueLine",
  "TransAfrica")

**Use only records whose `quote_id` matches AND `status` is `"active"` AND
`valid_until` is on or after the `quote_date`.**

### Freight field mapping

| API field | Output field | Notes |
|---|---|---|
| `id` | `freight_id` | Use as-is |
| `mode` | `mode` | Use lowercase: `air`, `sea`, `road` |
| `cost_usd` | `freight_cost_usd` | |
| `transit_days_text` | `transit_days` | e.g. `"3-5"`, `"28-34"` |
| `valid_until` | `valid_until` | ISO date |
| `route_risk` | `risk_level` / `customs_border_risk` | Uppercase: `LOW`, `MEDIUM`, `HIGH` |
| `status` | `validity_status` | `active` or `stale` |

### Stale freight

A freight record is **stale** when `valid_until < quote_date`. For stale records:
- `validity_status`: `"stale"`
- `source_is_stale`: `true`
- `road_quote_invalid_or_stale`: `true` (when it's the road lane)

The source notes may explicitly tell you to flag stale freight (e.g. "flag stale
road freight").

---

## Freight risk and recommendations

**Risk flags** are derived from `route_risk` and `risk_notes`:
- `low` → `LOW` risk, flag `NONE`
- `medium` + border language in notes → `MEDIUM` risk, flag derived from notes
- `high` → `HIGH` risk

**Recommended mode**: prefer the lowest-cost option that is not stale and has
acceptable risk. Generally:

1. Eliminate any stale/expired freight options
2. Eliminate options with `HIGH` route risk
3. Among remaining, prefer the cheapest (usually `sea`) unless transit time
   conflicts with delivery deadlines or cold-chain shelf-life constraints
4. For cold-chain products, weight the cold_chain_support flag — prefer modes
   that explicitly support it

---

## Customer payment terms

Map the customer's `payment_profile` and `segment` to the correct policy:

| Customer profile | Payment terms | Policy |
|---|---|---|
| `NEW_CLIENT_REVIEW` / `new_ngo` segment | `PREPAY_100` | POL-NEW-CLIENT-PAYMENT |
| `NET_30_AFTER_PO` / recurring NGO | `NET_30_AFTER_PO` | POL-RECURRING-NGO-PAYMENT |
| `NET_30_AFTER_PO` / recurring commercial | `NET_30_AFTER_PO` | same |
| `MILESTONE_BILLING` / implementation services | `MILESTONE_BILLING` | per-milestone |
| `PREPAY_50_BALANCE_BEFORE_SHIP` | as-is | |
| `NET_45_APPROVED` | as-is | |

The applicable policy is the one whose `applies_to` description matches the
customer's segment and credit history.

---

## Quote scope rules

### EXW with freight options
When a quote has a confirmed destination and the incoterm says "EXW plus freight
options": include `exw_total_usd` and all valid freight options with
`grand_total_usd = exw_total + freight_cost`.

### EXW only (indicative / no destination)
When the RFQ or quote has no confirmed destination, or the incoterm is "EXW"
without freight language: quote is EXW only. Set `freight_excluded: true` and
omit freight options. Quote basis: `EXW_ONLY`.

### Module vs. component level
For module RFQs (IEHK, field clinic, cholera response), quote at the **module**
product-code level. Even if the RFQ's `component_composition_distractors` or the
product's `components` field lists sub-items, do NOT split into component SKUs
unless the customer explicitly asks for component-level pricing. Policy
POL-MODULE-GRANULARITY applies.

### Quote validity
Standard catalog quote pricing is valid for **30 calendar days** from the
`quote_date`. Freight validity may expire sooner — always check each freight
record's `valid_until`.

---

## Milestone reconciliation pattern

### Milestone ID convention
Use `MS1`, `MS2`, `MS3` (ascending by phase order) as milestone identifiers,
NOT the internal phase IDs from the API (like `HEL-P1`, `MER-P2`). The phase
ordering is determined by:
- `phase_number` from the answer template
- Chronological order of `completion_date` in the opportunity
- Invoice issue dates

### Revenue recognition status per milestone

| Condition | `recognition_status` |
|---|---|
| Paid AND revenue journal exists | `RECOGNIZED` |
| Paid but NO revenue journal | `MISSING_REVENUE_JOURNAL` |
| Unpaid (regardless of completion) | `NOT_REQUIRED_UNPAID` |

The policy (POL-REVREC): "When a milestone is complete and paid, create or
verify revenue recognition from deferred revenue to income."

### Invoice and payment state mapping

| API invoice `status` | `invoice_state` | `payment_state` |
|---|---|---|
| `paid` | `PAID` | `PAID` |
| `unpaid` | `OPEN` | `UNPAID` |
| `overdue` | `OPEN` | `UNPAID` |
| `draft` | `OPEN` | `UNPAID` |

### Aggregate revenue recognition

| All paid milestones recognized? | `recognition_status` |
|---|---|
| Yes, all paid have journals | `COMPLETE_FOR_PAID_MILESTONES` |
| One or more paid milestones lack journals | `MISSING_FOR_PAID_MILESTONES` |

`recognized_milestones` lists the milestone IDs that have journals.
`missing_required_milestones` lists paid milestones without journals.
`recognized_amount` sums the journal amounts.

### Opportunity matching
`opportunity_matches_milestones` (or `opportunity_matches_phase_total`) is
`true` when `won_amount == sum(phase amounts)`.

---

## Accounting and collection actions

### When to record revenue
Create a `RECORD_REVENUE_MS{n}` action when a milestone is **paid** but has no
revenue journal. The journal entry is:

- **Debit**: `DEFERRED_REVENUE`
- **Credit**: `IMPLEMENTATION_SERVICES_REVENUE`
- **Owner queue**: `ACCOUNTING`
- **Amount**: the milestone's invoice amount

Use `VERIFY_REVENUE_ONLY` when all paid milestones already have journals — just
confirm they're posted. Use `NO_ACCOUNTING_ACTION` when there are no paid
milestones.

### When to collect
Collection tasks are driven by unpaid invoices:

| Due date vs. current date | Action |
|---|---|
| Due date is in the future | `MONITOR_UNPAID_NOT_DUE` |
| Due date has passed | `SEND_COLLECTION_NOTICE` |
| No unpaid invoices | `NO_COLLECTION_ACTION` |

**Owner queue for collection/monitor tasks**: `ACCOUNT_MANAGEMENT`.
**Contact**: use the contact named in the opportunity or prompt.

---

## Event and voucher handling

### Event fields
- `event_status` maps from the API event `status` field. Use uppercase:
  `scheduled` → `SCHEDULED`, `confirmed` → `SCHEDULED`, `live` → `ACTIVE`,
  `completed` → `COMPLETED`, `cancelled` → `CANCELLED`
- `voucher_code` links to the `vouchers` collection by `code`
- `voucher_status` maps the API voucher `status`: `active` → `ACTIVE`,
  `draft` → `DRAFT`, `expired` → `EXPIRED`, `disabled` → `DISABLED`

### Voucher discount
The `discount_amount` (or `voucher_discount`) field is the `discount_percent`
value from the API voucher record. It is not a dollar amount — it's the
percentage number. `max_uses` comes from `max_redemptions`.

### Invitation tasks
When an event is `scheduled` or `confirmed` and the current business date is
before the event date:

- **Action**: `SEND_BRIEFING_INVITE`
- **Owner queue**: `ACCOUNT_MANAGEMENT`
- **Contact**: the event's `primary_contact` or the account contact from the prompt

---

## Common pitfalls

1. **Using prior quote pricing instead of catalog tier.** The quote's
   `prior_unit_price_usd` is a historical reference. Always recalculate from the
   product's current `price_tiers` based on the confirmed quantity.

2. **Including distractor freight records.** Always check that the freight
   record's `quote_id` matches, `status` is `"active"`, and `valid_until` is
   not before `quote_date`. Distractors often have `FR-DIS-` prefix IDs, wrong
   shipment dimensions, or expired dates.

3. **Using internal phase IDs as milestone IDs.** The answer templates expect
   `MS1`, `MS2`, `MS3` — not the API's phase identifiers like `HEL-P1`.

4. **Splitting module RFQs into component line items.** Module products
   (IEHK-*, FCLINIC-*, CHOL-*) have `components` arrays in the catalog, but
   RFQs with `component_composition_distractors` explicitly warn against
   splitting. Quote at the module product-code level only.

5. **Including freight on EXW-only quotes.** When there's no destination or the
   RFQ explicitly says EXW only, set `freight_excluded: true` and omit freight
   options entirely.

6. **Missing revenue recognition for paid milestones.** A paid milestone
   without a matching entry in `revenue-journals` requires a
   `RECORD_REVENUE_MS{n}` accounting action. It's `MISSING_REVENUE_JOURNAL`,
   not `RECOGNIZED`.

7. **Wrong owner queue for collection tasks.** Collection/monitoring tasks go
   to `ACCOUNT_MANAGEMENT`, not `COLLECTIONS`. Accounting journal entries go to
   `ACCOUNTING`.

8. **Assuming all invoices sharing an opportunity are relevant.** Only invoices
   linked to the opportunity's phases matter. Distractor opportunities and their
   invoices (e.g. `OPP-DIS-*`) are for other accounts.

9. **Using uppercase mode strings in templates that expect lowercase.** Always
   check whether the answer template has pre-filled values (use those) or empty
   strings (match the API's lowercase convention for modes).

10. **Forgetting freight reconfirmation.** The universal policy
    POL-FREIGHT-RECONFIRM means `freight_reconfirmation_required` is `true` on
    every quote with freight options. Freight rates always need reconfirmation
    at final order.

---

## End-to-end workflow

### For a freight-inclusive quote revision
1. GET `/api/quotes` → find by `id`
2. GET `/api/customers` → find by quote's `customer_id`
3. GET `/api/products` → find by `primary_product_code`, select correct tier
4. GET `/api/freight-quotes` → filter by `quote_id`, exclude distractors
5. GET `/api/policies` → match payment policy to customer segment
6. Calculate EXW total, grand totals per freight option
7. Determine recommended mode (cheapest non-stale, low/medium risk)
8. Set `freight_reconfirmation_required: true`
9. Flag any stale freight in client warnings

### For an EXW-only indicative module quote
1. GET `/api/rfqs` → find by `id`
2. GET `/api/customers` → find by `customer_id`
3. GET `/api/products` → find each requested module, get article numbers
4. GET `/api/policies` → apply EXW-only, module granularity, new-client payment
5. Build line items at module level only (ignore component distractors)
6. Set `freight_excluded: true`, `offer_validity_days: 30`

### For an engagement reconciliation
1. GET `/api/opportunities` → find by `id`
2. GET `/api/customers` → find by `customer_id`
3. GET `/api/invoices` → filter by `opportunity_id`
4. GET `/api/payments` → filter by `invoice_id`
5. GET `/api/revenue-journals` → filter by `opportunity_id` and `phase_id`
6. GET `/api/events` → find by `opportunity_id`
7. GET `/api/vouchers` → find by event's `voucher_code`
8. Map milestones to MS1/MS2/MS3, compute recognition status per milestone
9. Determine accounting action (record revenue for paid-but-unrecognized)
10. Determine collection action (monitor or collect based on due date vs. current date)
11. Build event invite task if event is scheduled and before the event date

---

## Output conventions

- **Money**: always 2 decimal places (`50000.00`, not `50000`)
- **Dates**: ISO 8601 `YYYY-MM-DD`
- **Enums**: match the answer template's controlled vocabulary exactly (case-sensitive)
- **IDs**: use stable record IDs from the API as-is
- **Customer names**: use the `name` field from the customer record, not the prompt's shorthand
- **Transit days**: use the `transit_days_text` range string (e.g. `"4-6"`, `"28-34"`)
- **Risk levels**: uppercase (`LOW`, `MEDIUM`, `HIGH`)
- **Modes**: lowercase (`air`, `sea`, `road`) unless template pre-fills uppercase
