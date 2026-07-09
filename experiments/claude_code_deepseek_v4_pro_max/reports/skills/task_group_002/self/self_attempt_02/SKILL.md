# MedBridge Sales Ops API — Transferable SKILL.md

## 1. Environment & API Entrypoint

- The API base URL is provided by the runner (env, `API_BASE_URL`, `BASE_URL`, `http://34.46.77.124:8002`, etc.). Always use the runner-provided URL.
- All endpoints are read-only `GET`. No authentication required in this staging environment.
- **Root discovery**: `GET /api` returns the collection list and all available endpoints.

## 2. API Collections & Navigation Pattern

| Collection | Endpoint | Join Keys |
|---|---|---|
| `customers` | `/api/customers`, `/api/customers/<id>` | `id` |
| `products` | `/api/products`, `/api/products/<code>` | `code` |
| `rfqs` | `/api/rfqs`, `/api/rfqs/<id>` | `id`, `customer_id` |
| `quotes` | `/api/quotes`, `/api/quotes/<id>` | `id`, `customer_id` |
| `freight-quotes` | `/api/freight-quotes`, `/api/freight-quotes/<id>` | `id`, `quote_id` |
| `policies` | `/api/policies` | `id`, `terms_code` |
| `opportunities` | `/api/opportunities`, `/api/opportunities/<id>` | `id`, `customer_id` |
| `invoices` | `/api/invoices` | `id`, `customer_id`, `opportunity_id`, `phase_id` |
| `payments` | `/api/payments` | `id`, `customer_id`, `invoice_id`, `opportunity_id` |
| `revenue-journals` | `/api/revenue-journals` | `id`, `invoice_id`, `opportunity_id`, `phase_id` |
| `events` | `/api/events` | `id`, `customer_id`, `opportunity_id` |
| `vouchers` | `/api/vouchers` | `code`, `customer_id`, `event_id`, `opportunity_id` |
| `search` | `/api/search?q=<text>` | Cross-collection full-text search |

**Usage habit**: First fetch the collection list, then directly fetch individual records by their known IDs. For multi-entity tasks, use `/api/search?q=<id>` to pull all records linked to a customer, quote, or opportunity in one call.

## 3. Product Catalog & Price Tier Resolution

### Tier Selection Rule
Every product has `price_tiers[]` with `min_qty`, `max_qty`, and `unit_price_usd`. To select the correct tier:

1. Find the tier where `confirmed_quantity` falls in `[min_qty, max_qty]`. `max_qty: null` means no upper bound.
2. **Catalog tier always overrides any prior unit price.** A quote's `prior_unit_price_usd` is historical context only — never use it for the current quote. The `source_notes` field on quotes often explicitly states this ("catalog tier overrides prior unit price").
3. Single-tier products (min_qty=1, max_qty=null) are common for IEHK and cholera modules — no tier logic needed.

### Fields Retrieved from the Matched Tier
- `unit_price_usd` → unit price for the quote
- `lead_time_days` → lead time in days
- Also required from product root: `shelf_life_months`, `article_number`, `cold_chain_required`

### Calculation: EXW Total
```
exw_total_usd = confirmed_quantity × unit_price_usd
```
Round to 2 decimal places (cents). All amounts are in USD.

## 4. Freight Quote Filtering & Validation

### Primary Filter
Freight records link to quotes via `freight-quotes.quote_id`. **Always filter freight by `quote_id` matching the quote being processed.**

### Status-Based Filtering
Freight records have a `status` field:
- `active` — valid for use; check `valid_until` against `quote_date`
- `stale` — expired, do not use; its `valid_until` is before `quote_date`
- `mismatch` — wrong shipment size/weight (based on prior quantity); do not use

**Rule**: Only use freight where `status == "active"` AND `valid_until >= quote_date`. If `valid_until < quote_date`, the freight is stale/invalid regardless of `status` value.

### Distractor Detection
The API contains distractor freight records (IDs prefixed `FR-DIS-*`) that share a `quote_id` with the target quote but have:
- Wrong `shipment_cbm` or `shipment_weight_kg` (mismatched to actual shipment)
- `status: "stale"` with `valid_until` before the quote date
- Different `forwarder` or `destination` than the real routes
- `route_risk` notes indicating they are benchmarks or archived estimates

**Pitfall**: Freight for a given `quote_id` returns ALL records — not just the 3 valid ones. You MUST filter by status and valid_until.

### Validity Status Label
For each freight option, determine:
- `"valid"` — status is `active` AND `valid_until >= quote_date`
- `"stale"` — `valid_until < quote_date` OR status is `stale`
- `source_is_stale: true` when `valid_until < quote_date`

### Grand Total Calculation
```
grand_total_usd = exw_total_usd + freight_cost_usd
```

## 5. Route Risk & Mode Recommendation

### Risk Assessment
- `route_risk: "low"` → `risk_level: "LOW"`, no flag
- `route_risk: "medium"` → `risk_level: "MEDIUM"`, flag based on notes (e.g., `MEDIUM_BORDER_RISK`)
- `route_risk: "high"` → `risk_level: "HIGH"`, flag based on notes (e.g., `HIGH_BORDER_RISK`, `CUSTOMS_RISK`)
- `risk_flag: "NONE"` for low-risk routes

### Recommended Mode Heuristic
1. If any freight is stale/invalid, it disqualifies that mode
2. Prefer mode with lowest risk → then fastest transit
3. For cold-chain products (`cold_chain_required: true`), air is strongly preferred (temperature control, shorter transit within shelf-life window)
4. If road has border risk or is stale, do not recommend road
5. Sea is rarely recommended for cold-chain or urgent deliveries due to long transit

### Freight Reconfirmation
Policy `POL-FREIGHT-RECONFIRM`: All freight rates must be reconfirmed at final order. The `freight_reconfirmation_required` flag should be `true` when any freight has a `valid_until` that could expire before the customer's PO date, or when road risks are flagged. In practice, this is almost always `true` for revision quotes.

### All-Freight-Valid Check
Check whether ALL freight options are valid on the quote date:
```
all_valid = all(f.valid_until >= quote_date AND f.status == "active" for f in freight_options)
```

## 6. Customer Record & Payment Terms

### Customer Lookup
- Start from the quote/RFQ/opportunity's `customer_id`, then fetch `/api/customers/<customer_id>`
- The `segment` field determines policy application: `recurring_ngo`, `new_ngo`, `recurring_commercial`, `government_program`, `implementation_services`, etc.

### Payment Term Resolution
Match the customer's `payment_profile` and `segment` against policies:

| Customer Segment/Payment Profile | Payment Terms | Policy |
|---|---|---|
| `new_ngo` / `NEW_CLIENT_REVIEW` | `PREPAY_100` | POL-NEW-CLIENT-PAYMENT |
| `recurring_ngo` / `NET_30_AFTER_PO` | `NET_30_AFTER_PO` | POL-RECURRING-NGO-PAYMENT |
| `recurring_commercial` / `NET_30_AFTER_PO` | `NET_30_AFTER_PO` | (from payment_profile) |
| `government_program` / `NET_30_AFTER_PO` | `NET_30_AFTER_PO` | (from payment_profile) |
| `implementation_services` / `MILESTONE_BILLING` | `MILESTONE_BILLING` | (from payment_profile) |
| `distributor` / `NET_45_APPROVED` | `NET_45_APPROVED` | (from payment_profile) |

**Precedence**: The customer's `payment_profile` field is authoritative. Cross-reference with policies for the `terms_code`.

### Name Discrepancy Warning
Task text may use a different human-readable customer name than the API record's `name` field. **Always use the API record's `name` as authoritative.** For example, a task may say "Health Horizon Aid" for `CUST-HHA` whose API name is "HealthHands Alliance", or "GreenHarvest Labs" for `CUST-GHL` whose API name is "Global Health Laboratories". Match by `customer_id`, not by name string.

## 7. Quote Types & Scope Rules

### Quote Types
- `quote_revision_with_freight`: Revised pricing with transport comparison (tasks 001, 004)
- `indicative_module_quote`: RFQ-based, EXW only, no freight (task 002)
- `module_quote_with_freight_advisory`: Advisory freight only (destination uncertain)
- Product quotes, freight comparisons, etc.

### Indicative/NGO Module Quotes (Task 002 Pattern)
- **EXW only, freight excluded** — policy POL-INDICATIVE-EXW
- **Module granularity** — quote at module line level only, do NOT split into components (policy POL-MODULE-GRANULARITY)
- RFQ `requested_modules[]` drives the line items; each module `product_code` → product catalog → single price tier
- `quote_basis: "EXW_ONLY"`, `freight_excluded: true`
- `payment_terms`: Look up customer segment → policy
- `offer_validity_days: 30` (policy POL-QUOTE-VALIDITY)
- `who_documentation_required: true` for IEHK-family products
- Use `article_number` from the product record

## 8. Opportunity Reconciliation (Tasks 003, 005)

### Data Assembly
For a given `opportunity_id`:

1. **Fetch opportunity** → get `stage`, `won_amount_usd`, `phases[]`, `customer_id`, `contact`
2. **Fetch customer** → get name, contacts, payment_profile
3. **Fetch invoices** → filter by `opportunity_id`, match to phases via `phase_id`
4. **Fetch payments** → filter by `opportunity_id`, match to invoices via `invoice_id`
5. **Fetch revenue-journals** → filter by `opportunity_id`, match to phases via `phase_id`
6. **Fetch events** → filter by `opportunity_id`
7. **Fetch vouchers** → filter by `opportunity_id` or `event_id`

### Won Amount vs Phase Total
```
phase_total = sum(phase.amount_usd for phase in opportunity.phases)
opportunity_matches_phases = (won_amount_usd == phase_total)
```

### Milestone/Invoice State Mapping
Join opportunity phases → invoices → payments → revenue journals:

| Invoice Status | Payment | Revenue Journal | Recognition Status |
|---|---|---|---|
| `paid` | posted with full amount | exists for phase | `RECOGNIZED` |
| `paid` | posted with full amount | missing | `MISSING_REVENUE_JOURNAL` |
| `unpaid` | none | — | `NOT_REQUIRED_UNPAID` |
| `overdue` | none | — | `NOT_REQUIRED_UNPAID` (but drives collection) |

### Payment State
- `PAID` — invoice status is `paid`, payment posted and matches
- `PARTIAL` — payment exists but less than invoice amount
- `UNPAID` — no payment or invoice status is `unpaid`/`overdue`

### Revenue Recognition Accounting Rule (POL-REVREC)
When a milestone is **complete AND paid**, a revenue journal must exist:
- **Debit**: `Deferred Revenue`
- **Credit**: `Implementation Services Revenue`
- This moves the amount from the balance-sheet liability to the P&L income line.

### Revenue Recognition Summary
- `COMPLETE_FOR_PAID_MILESTONES` — all paid phases have journals
- `MISSING_FOR_PAID_MILESTONES` — at least one paid phase is missing its journal
- `NOT_REQUIRED` — no phases are paid (nothing to recognize)

### Outstanding Balance
Sum of `invoice.outstanding_amount_usd` across all invoices for the opportunity, or use `opportunity.outstanding_amount_usd`.

### Collection Task Logic
| Condition | Action |
|---|---|
| Unpaid, due date > business date (future) | `MONITOR_UNPAID_NOT_DUE` |
| Unpaid, due date ≤ business date (past/overdue) | `SEND_COLLECTION_NOTICE` |
| Paid in full | `NO_COLLECTION_ACTION` |

Business date defaults to the quote date or `2026-06-01` unless specified.

### Accounting Action Logic
| Condition | Action |
|---|---|
| Paid milestone with missing revenue journal | `RECORD_REVENUE_<MILESTONE>` (e.g., `RECORD_REVENUE_MS2`) |
| All paid milestones have journals | `VERIFY_REVENUE_ONLY` |
| No paid milestones | `NO_ACCOUNTING_ACTION` |

Journal entry template for `RECORD_REVENUE_*`:
- `debit_account: "DEFERRED_REVENUE"`
- `credit_account: "IMPLEMENTATION_SERVICES_REVENUE"`
- `amount`: the paid-but-unrecognized milestone amount
- `owner_queue: "ACCOUNTING"`

### Event & Voucher Integration
- Match event to opportunity via `opportunity_id`
- Match voucher to event via `event_id` or `voucher_code` on event → voucher `code`
- Voucher `discount_percent` is the discount value (e.g., 50 means 50% off)
- Voucher `max_redemptions` (called `max_uses` in some templates)
- Event statuses: `scheduled`, `confirmed`, `live`, `completed`, `cancelled`
- Voucher statuses: `active`, `draft`, `expired`, `disabled`

### Invite Action Logic
| Event Status | Voucher Status | Action |
|---|---|---|
| `scheduled` or `confirmed` | `active` | `SEND_BRIEFING_INVITE` or `SEND_EVENT_INVITATION` |
| Already in past or completed | — | `VERIFY_INVITE_SENT` |
| No event linked | — | `NO_INVITE_ACTION` |

## 9. Common Pitfalls & Edge Cases

### Distractor Records
- **Freight**: Records with `FR-DIS-*` ID prefix are distractors; they share a `quote_id` but have wrong dimensions, stale status, or mismatched forwarder/destination. Always cross-check `shipment_cbm`/`shipment_weight_kg` against the actual order.
- **RFQs**: Older RFQs (e.g., `RFQ-DIS-004` through `RFQ-DIS-010`) with different quantities, dates, or statuses (`superseded`, `closed_lost`, `archived`) are distractors. Only use the RFQ explicitly named in the task.
- **Quotes**: Distractor quotes exist for other customers/products/dates. Match by exact `quote_id` or `rfq_id`.
- **Component composition distractors**: RFQs and quotes may have `component_composition_distractors[]` listing sub-components — these are for medical/operations review only. Quote at the module/product level.

### Prior Price vs Catalog Tier
Quotes carry `prior_unit_price_usd` from earlier revisions with lower quantities. **Never carry forward the prior price.** The catalog tier at the new `confirmed_quantity` always wins. The `source_notes` often explicitly states this.

### RFQ Quantity Override for Consolidation
When an RFQ's narrative mentions a quantity discrepancy (e.g., "ORS appears twice in the field note as 8 plus 4"), use the consolidated quantity from the `requested_modules[]` array — that is the authoritative source.

### Milestone Completion Dates
For milestones with future `completion_date` (after the business date), treat as not yet complete. Only completed-and-paid milestones require revenue recognition. Future-phase invoices that are unpaid do not need recognition yet.

### Cold-Chain Products
Products with `cold_chain_required: true` (e.g., `LD-REAGENT-44`) require:
- Cold-chain-capable freight (freight has `cold_chain_support: true`)
- Shorter transit to stay within shelf-life
- Air recommendation is stronger (temperature-controlled lanes)
- Shelf-life check: product shelf-life must exceed transit time significantly

### IEHK & WHO Documentation
Products in the `emergency_health_kit` family require `who_documentation_required: true` on quotes. This is a standard compliance flag for IEHK-style modules.

### Currency
All monetary values are in USD. Always output with 2 decimal places (cents). Use `0.00` for zero amounts, never `0`.

### Date Format
All dates use ISO 8601 `YYYY-MM-DD`. This applies to: `quote_date`, `valid_until`, `due_date`, `event_date`, `completion_date`, `as_of_date`.

### Quote Validity
Per policy POL-QUOTE-VALIDITY: standard quote pricing is valid for 30 calendar days from `quote_date`. Freight validity (`valid_until`) may be shorter.

## 10. Task-to-API Mapping Summary

| Task Pattern | Starting Entity | Navigation Path |
|---|---|---|
| Quote revision with freight | `quote_id` → quote → customer + product + freight | quote → product (tier by qty), freight (filter by quote_id + status), customer → policy/payment |
| Indicative RFQ quote | `rfq_id` → RFQ → customer + requested_modules[] | RFQ → product per module (single tier), customer → policy, NO freight |
| Opportunity reconciliation | `opportunity_id` → opportunity + invoices + payments + revenue + events + vouchers | opportunity → phases → invoices → payments + revenue-journals; opportunity → events → vouchers |
| Engagement reconciliation | Same as opportunity + events/vouchers deeply integrated | Same as above with additional event-action routing logic |

## 11. Output Structure Rules

- Match the `answer_template.json` structure exactly — field names, nesting, and enum values
- Enum values are uppercase with underscores (`PAID`, `RECOGNIZED`, `MISSING_REVENUE_JOURNAL`)
- Null fields: use `null` (JSON null) when not applicable; use `"NONE"` for enum-style "none" sentinels
- Money: always a number with 2 decimal places, not a string
- Arrays: ordered as specified (freight: AIR → SEA → ROAD; milestones: ascending by phase number or milestone ID)
- Boolean fields: `true`/`false` (JSON literals, not strings)
- Always use the stable IDs from API records (`id`, `code`, `phase_id`, `invoice_id`) — don't generate synthetic IDs

## 12. API Behavior Notes

- The API returns `collection`, `count`, and `records[]` for list endpoints
- Single-record endpoints return the record object directly (no wrapper)
- Search (`/api/search?q=`) normalizes query to lowercase and matches across all collections
- The `generated_at` timestamp on `/api` is fixed per seed — data is static
- All collections are read-only; the API is a staging/seed data source
