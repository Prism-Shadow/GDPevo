# MedBridge Sales Ops API Task Skill

## Overview
Tasks in this benchmark require querying a shared MedBridge Sales Ops API and producing JSON answers that match a strict `answer_template.json` schema. The API exposes collections: `customers`, `products`, `quotes`, `rfqs`, `freight-quotes`, `opportunities`, `invoices`, `payments`, `revenue-journals`, `events`, `vouchers`, and `policies`.

## General Approach
1. **Read the prompt and template first.** The prompt names a customer, quote/RFQ/opportunity ID, and product. The `input/payloads/answer_template.json` dictates the exact shape, field names, and enums of the answer.
2. **Fetch base collections** (`/api/customers`, `/api/products`, `/api/policies`) once, then query specific records by ID (`/api/quotes/<id>`, `/api/rfqs/<id>`, `/api/opportunities/<id>`, etc.).
3. **Use `/api/search?q=<text>`** when the prompt uses a name variant that does not match the API `customer_name` exactly.
4. **Derive all numbers from the API** (unit prices, freight costs, totals, balances). Do not hard-code.
5. **Match the template exactly.** Missing keys, extra keys, or wrong enum values lower the score even if the data is conceptually correct.

## Data Mapping Patterns

### Quotes / RFQs with Product Pricing
- Look up the product in `/api/products` by `product_code`.
- Select the price tier whose `min_qty` ≤ confirmed quantity ≤ `max_qty` (if `max_qty` is `null`, it means unlimited).
- `exw_total_usd = confirmed_quantity * unit_price_usd`.
- `lead_time_days` and `shelf_life_months` come from the matched tier / product record.
- If the RFQ requests multiple modules, create one line item per module.

### Freight Options
- Fetch all `freight-quotes` for the quote ID.
- **Exclude distractor freight records** (IDs often prefixed `FR-DIS-…`, status `stale`, or wrong shipment size/destination).
- Include the three standard modes when available: **AIR**, **SEA**, **ROAD**.
- `grand_total_usd = exw_total_usd + freight_cost_usd`.
- Check `valid_until` against the `quote_date`. If `valid_until < quote_date`, mark `source_is_stale = true` / `road_quote_invalid_or_stale = true`.
- Risk fields map directly from the freight quote `route_risk` and `risk_notes`.

### Payment Terms & Policies
- Customer `payment_profile` is the source of truth for `payment_terms`.
- Cross-check with `/api/policies`:
  - New NGOs without credit history → `PREPAY_100`
  - Recurring NGOs → `NET_30_AFTER_PO`
  - Milestone-billing accounts → `MILESTONE_BILLING`
- Quote validity: catalog quotes are typically valid **30 calendar days** from `quote_date`.
- Freight always requires **reconfirmation at final order** per policy `POL-FREIGHT-RECONFIRM`.

### Opportunity / Milestone Reconciliation
- Map opportunity `phases` to template milestones. Some templates expect milestone IDs like `MS1`, `MS2`, `MS3` in ascending order.
- `opportunity_matches_phase_total` = `won_amount == sum(phase.amount_usd)`.
- `total_paid_amount` = sum of payments linked to the opportunity.
- `outstanding_balance` = opportunity `outstanding_amount_usd` or sum of unpaid invoice amounts.

### Invoice & Payment States
- Invoice `status` values in API: `paid`, `unpaid`, `overdue`, `draft`.
- Template enums may use `PAID`, `OPEN`, `VOID`, `UNKNOWN` for `invoice_state` and `PAID`, `PARTIAL`, `UNPAID`, `UNKNOWN` for `payment_state`.
- A milestone is `PAID` only when the linked invoice `status == "paid"`.

### Revenue Recognition
- Check `/api/revenue-journals` for a journal matching the `opportunity_id` and `phase_id`.
- If a paid milestone has **no** matching revenue journal → `MISSING_REVENUE_JOURNAL`.
- If a paid milestone has a posted journal → `RECOGNIZED`.
- If a milestone is unpaid → `NOT_REQUIRED_UNPAID`.

### Events & Vouchers
- Events and vouchers are linked by `event_id` / `voucher_code`.
- Event `status` in API may be `scheduled`, `confirmed`, `completed`, etc.; templates expect enums like `SCHEDULED`, `ACTIVE`, `COMPLETED`, `CANCELLED`, `UNKNOWN`.
- Voucher `discount_percent` from the API maps to `discount_amount` or `voucher_discount` in the template (usually as a numeric value, not a formatted string).

### Follow-Up / Action Tasks
- Derive tasks from actual state:
  - Unpaid milestone with due date in the future → `MONITOR_UNPAID_NOT_DUE` / `COLLECTION`
  - Unpaid milestone past due → `SEND_COLLECTION_NOTICE`
  - Missing revenue journal on paid milestone → `RECORD_REVENUE_MS2` (or corresponding milestone) / accounting action
  - Event scheduled but not yet sent → `SEND_BRIEFING_INVITE`
- Use the **contact name from the prompt or opportunity record** for task `contact_name`.

## Common Pitfalls
- **Wrong customer mapping:** Prompts may use name variants (e.g., "Health Horizon Aid" vs. "HealthHands Alliance"). Use the quote/RFQ/opportunity ID to resolve the correct `customer_id`.
- **Ignoring distractor records:** The API contains stale freight quotes, old RFQs, and invoices for unrelated opportunities. Filter by the ID referenced in the prompt.
- **Using the wrong price tier:** Always match quantity against `min_qty`/`max_qty`; do not use a prior quote’s unit price.
- **Mismatched enums:** Templates define strict enums (e.g., `WON | OPEN | LOST`, `PAID | PARTIAL | UNPAID`). Use uppercase exactly as specified.
- **Date arithmetic:** Treat the current business date as `2026-06-01` unless the prompt states otherwise.
- **JSON formatting:** When submitting answers via `curl`, write the JSON to a file and use `--data-binary @file` to avoid shell-escaping errors.

## Quick Reference: Typical Endpoints
- `GET /api/customers/<id>`
- `GET /api/products/<code>`
- `GET /api/quotes/<id>`
- `GET /api/rfqs/<id>`
- `GET /api/freight-quotes` (filter by `quote_id` client-side)
- `GET /api/opportunities/<id>`
- `GET /api/invoices` (filter by `opportunity_id` or `customer_id`)
- `GET /api/payments` (filter by `opportunity_id`)
- `GET /api/revenue-journals` (filter by `opportunity_id`)
- `GET /api/events` (filter by `opportunity_id` or `customer_id`)
- `GET /api/vouchers` (filter by `event_id`)
- `GET /api/policies`
- `GET /api/search?q=<text>`
