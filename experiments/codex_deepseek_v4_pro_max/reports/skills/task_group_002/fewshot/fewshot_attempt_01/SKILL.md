## When to Use This Skill

Use this skill whenever a user asks you to work with the **MedBridge Sales Ops API** — a read‑only REST API that surfaces business records for a medical‑supply sales and logistics platform. The user will provide a task‑specific prompt requiring you to look up customers, products, quotes, RFQs, freight, policies, opportunities, invoices, payments, revenue journals, events, or vouchers, and then produce a structured JSON response.

The runner provides the API base URL through an environment variable or placeholder such as `<TASK_ENV_BASE_URL>` or `BASE_URL`. Use that exact URL for every request.

## Available Endpoints (all GET, read‑only)

### Discovery
- `GET /api` — top‑level index with entity list summaries
- `GET /api/search` — full‑text search across entities

### Core Business Records
- `GET /api/customers` — list all customers
- `GET /api/customers/{id}` — single customer detail (e.g. `CUST-ABC`)
- `GET /api/products` — list all products
- `GET /api/products/{code}` — single product with catalog tiers (e.g. `PROD-001`)
- `GET /api/quotes` — list all quotes
- `GET /api/quotes/{id}` — single quote (e.g. `Q-TR-0001`)
- `GET /api/rfqs` — list all RFQs
- `GET /api/rfqs/{id}` — single RFQ (e.g. `RFQ-TR-0001`)
- `GET /api/freight-quotes` — list all freight quotes
- `GET /api/freight-quotes/{id}` — single freight quote (e.g. `FR-ABC-AIR`)
- `GET /api/policies` — list all policies
- `GET /api/policies/{id}` — single policy record

### Financial & Engagement Records
- `GET /api/opportunities` — list all opportunities
- `GET /api/opportunities/{id}` — single opportunity (e.g. `OPP-TR-0001`)
- `GET /api/invoices` — list all invoices
- `GET /api/invoices/{id}` — single invoice
- `GET /api/payments` — list all payments
- `GET /api/payments/{id}` — single payment
- `GET /api/revenue-journals` — list all revenue‑recognition journal entries
- `GET /api/revenue-journals/{id}` — single journal entry
- `GET /api/events` — list all CRM events
- `GET /api/events/{id}` — single event (e.g. `EVT-ABC-0001`)
- `GET /api/vouchers` — list all vouchers
- `GET /api/vouchers/{code}` — single voucher by code (e.g. `VOUCHER001`)

## Workflow

**Step 1 — Read the user prompt carefully.** Identify:
- Which entities the user names explicitly (customer, quote, RFQ, product, opportunity, event, voucher).
- The business date and confirmed quantities the user provides.
- Whether freight is needed (most quote tasks) or excluded (EXW‑only tasks).
- Whether the task is a "decision package" (pricing + freight + policy), an "account reconciliation" (opportunity + milestones + revenue + events/vouchers), or an "engagement reconciliation" (opportunity + milestones + accounting actions + event actions).

**Step 2 — Read the answer template.** Every task includes a template at `input/payloads/answer_template.json` (or a similar path). The template declares the exact JSON shape, field names, enum values, and units expected. Your output MUST:
- Match the template key names exactly.
- Use the declared enum values wherever they appear.
- Use two‑decimal USD numbers for monetary fields.
- Use ISO `YYYY‑MM‑DD` dates.
- Use stable record IDs from the API (never invent IDs).

**Step 3 — Call the API endpoints.** Always start with the entity‑specific endpoints named in the prompt. Then follow cross‑references to pull related records:

### Entity Cross‑References

| Entity | Links to | Join key / pattern |
|---|---|---|
| Quote | Customer, Product, Freight Quotes, Policy | `customer_id`, `product_code`, freight‑quote IDs from product or quote, `policy_id` or customer‑based policy lookup |
| RFQ | Customer, Products (line items), Policy | `customer_id`, product codes in line items, `policy_id` |
| Customer | Policies, Opportunities, Invoices, Events | `id` used as `customer_id` elsewhere |
| Product | Catalog tiers, Freight Quotes | `code` used as `product_code`; tiers keyed by quantity range |
| Freight Quote | Quote / Product | freight‑quote IDs embedded in quote lines or product freight maps |
| Opportunity | Customer, Invoices, Revenue Journals, Events | `customer_id`, milestone IDs → invoice IDs → payment records; `id` used in event and voucher payloads |
| Invoice | Payments, Revenue Journals, Milestones | `invoice_id` → payments; `milestone_id` → revenue journals |
| Event | Voucher, Customer, Opportunity | `event_id` → voucher; `customer_id`, `opportunity_id` |
| Voucher | Event | `code` lookup; event payload references voucher |

**Step 4 — Cross‑reference and compute.** Join the records from Step 3:
- Match quotes to their customer, product, freight options, and policies.
- Match opportunities to their milestones, invoices, payments, and revenue journals.
- Match events to their vouchers and customer/opportunity context.
- Apply catalog‑tier logic: products may have quantity‑based pricing tiers with `min_quantity`, `max_quantity`, `unit_price_usd`, `lead_time_days`, and `shelf_life_months`. Select the tier whose range contains the confirmed quantity.
- Compute `exw_total_usd` = `confirmed_quantity × unit_price_usd`.
- Compute `grand_total_usd` = `exw_total_usd + freight_cost_usd` for each freight option.

**Step 5 — Apply business rules for status fields.**

### Freight Validity
- Compare each freight quote's `valid_until` date to the quote date.
- A freight quote is **STALE** if `valid_until` < quote date.
- A freight quote is **VALID** if `valid_until` ≥ quote date.
- Set `source_is_stale: true` for stale freight quotes and `false` for valid ones.
- Set `all_freight_options_valid_on_quote_date` to `true` only if every freight option is valid on the quote date.

### Freight Risk Flags
Freight records carry a `risk_level` and optional `risk_flag`. Common values:
- `risk_level`: `LOW`, `MEDIUM`, `HIGH`
- `risk_flag`: `NONE`, `MEDIUM_BORDER_RISK`, or a descriptive string
- For customs/border risk fields, surface the risk level: `LOW`, `MEDIUM`, or `HIGH`.

### Recommended Transport Mode
The policy record typically declares a `recommended_mode` — use that value (`AIR`, `SEA`, `ROAD`). If no policy exists, default to the lowest‑cost valid freight option.

### Freight Reconfirmation
Set `freight_reconfirmation_required` based on the policy record's `freight_reconfirmation_required` flag. When `true`, include a client warning that freight rates require reconfirmation at final order and call out any stale road quotes with their expiry date.

### Payment Terms
Common values: `NET_30_AFTER_PO`, `PREPAY_100`, `NET_30`. Source from the policy record or the customer record.

### Revenue Recognition Status (per milestone)
| Invoice/Payment State | Revenue Journal Exists? | Status |
|---|---|---|
| PAID (full payment received) | Yes | `RECOGNIZED` |
| PAID (full payment received) | No | `MISSING_REVENUE_JOURNAL` |
| UNPAID / PARTIAL | N/A | `NOT_REQUIRED_UNPAID` |

### Revenue Recognition Summary
- `COMPLETE_FOR_PAID_MILESTONES` — every fully‑paid milestone has a revenue journal.
- `MISSING_FOR_PAID_MILESTONES` — at least one fully‑paid milestone lacks a revenue journal.
- `NOT_REQUIRED` — no milestones are fully paid.

### Accounting Actions (engagement reconciliations)
Based on revenue recognition gaps:
- **RECORD_REVENUE_MSx**: A specific paid milestone is missing its revenue journal. Debit `DEFERRED_REVENUE`, credit `IMPLEMENTATION_SERVICES_REVENUE`, owner `ACCOUNTING`.
- **VERIFY_REVENUE_ONLY**: All paid milestones have journals; only verification is needed.
- **NO_ACCOUNTING_ACTION**: No accounting work required.

### Collection Actions
- **SEND_COLLECTION_NOTICE**: An unpaid milestone has a past‑due date (due_date < current business date).
- **MONITOR_UNPAID_NOT_DUE**: An unpaid milestone has a future due date or no due date.
- **NO_COLLECTION_ACTION**: All milestones are fully paid.

### Opportunity‑Milestone Matching
- Sum the milestone phase amounts and compare to `won_amount`. Set `opportunity_matches_milestones` (or `opportunity_matches_phase_total`) to `true` when the totals match, `false` otherwise.
- Compute `outstanding_balance` = sum of unpaid amounts across all milestones.
- Compute `total_paid_amount` = sum of all payments received.

### Event & Voucher Actions
- For events linked to a won opportunity, generate an invitation follow‑up task with `next_action: SEND_EVENT_INVITATION` (or `SEND_BRIEFING_INVITE` for briefings).
- The invite task owner is `ACCOUNT_MANAGEMENT`, tied to the named contact.
- For collection tasks on unpaid milestones, include the contact name, due date, amount, and set `next_action: COLLECT_UNPAID_MILESTONE`.
- Voucher status: `ACTIVE`, `DRAFT`, `EXPIRED`, `DISABLED`. Surface discount amount and max uses from the voucher record.
- Event status: `SCHEDULED`, `ACTIVE`, `COMPLETED`, `CANCELLED`.

**Step 6 — Assemble the final JSON.** Populate every field from the template with the API‑derived values. Leave no placeholder strings (`"string"`, `"YYYY-MM-DD"`, `"<rfq_id>"`, `0`, `0.0`) in the final output — every field must contain a concrete value from the API or a value computed from API data.

## Task‑Type Quick Reference

| Task Type | Key Entities | Required API Calls |
|---|---|---|
| **Quote + Freight Decision Package** | Quote, Customer, Product, Freight Quotes, Policy | `GET /api/quotes/{id}`, `GET /api/customers/{id}`, `GET /api/products/{code}`, `GET /api/freight-quotes` (filter by product), `GET /api/policies` |
| **RFQ EXW‑Only Quote** | RFQ, Customer, Products (line items), Policy | `GET /api/rfqs/{id}`, `GET /api/customers/{id}`, `GET /api/products/{code}` (one per line item), `GET /api/policies` |
| **Account Reconciliation** | Opportunity, Customer, Invoices, Payments, Revenue Journals, Event, Voucher | `GET /api/opportunities/{id}`, `GET /api/customers/{id}`, `GET /api/invoices` (filter by opp), `GET /api/payments` (per invoice), `GET /api/revenue-journals` (per milestone), `GET /api/events/{id}`, `GET /api/vouchers/{code}` |
| **Engagement Reconciliation** | Opportunity, Customer, Invoices, Payments, Revenue Journals, Event, Voucher | Same as Account Reconciliation but with accounting‑action and invite‑task generation |

## Important Rules

1. **Never invent data.** Every value must come directly from an API response or be computed deterministically from API values.
2. **Read the template first.** The template defines the exact field names, enum sets, and structure. Your output JSON must conform precisely.
3. **Use the provided base URL.** Do not hardcode any hostname or port. Use exactly the URL given as `<TASK_ENV_BASE_URL>` or `BASE_URL`.
4. **Currency formatting.** All monetary values must have exactly two decimal places (`12345.00`, not `12345` or `12345.0`).
5. **Date formatting.** All dates must be ISO 8601 `YYYY-MM-DD` format.
6. **Freight exclusion.** When the prompt says "EXW only" or "freight excluded," set `freight_excluded: true`, omit freight options, and return only the EXW line items and totals.
7. **Module‑level quoting.** When the prompt says "keep the quote at the requested module level only," do not explode module components into separate line items. Use the module product codes directly from the RFQ.
8. **Contact linking.** Always verify that the named contact in the prompt matches the contact record linked to the customer and opportunity in the API. Surface the contact name in the response exactly as it appears in the prompt.
9. **Output format.** Return only raw JSON — no markdown fences, no explanatory text. If the template path is `input/payloads/answer_template.json`, your output must be valid JSON parseable as that schema.
