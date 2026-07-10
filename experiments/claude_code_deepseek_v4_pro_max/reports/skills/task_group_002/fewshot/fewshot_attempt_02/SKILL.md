# MedBridge Sales Ops — Quote & Engagement Reconciliation

## Environment

The MedBridge Sales Ops API is a read-only JSON API that provides CRM, quote,
logistics, product catalog, and milestone engagement data. The runner supplies
the base URL as `API_BASE_URL` or `BASE_URL`.  Construct all requests as
`GET {base_url}/api/...`.

## API surface

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/api` | List all collections |
| `GET` | `/api/customers` | All customer records |
| `GET` | `/api/customers/<id>` | Single customer |
| `GET` | `/api/products` | All product catalog records |
| `GET` | `/api/products/<code>` | Single product |
| `GET` | `/api/quotes` | All quotes |
| `GET` | `/api/quotes/<id>` | Single quote |
| `GET` | `/api/freight-quotes` | All freight quotes |
| `GET` | `/api/freight-quotes/<id>` | Single freight quote |
| `GET` | `/api/rfqs` | All RFQs |
| `GET` | `/api/rfqs/<id>` | Single RFQ |
| `GET` | `/api/policies` | All policies (collection only; no single-record endpoint) |
| `GET` | `/api/opportunities` | All opportunities |
| `GET` | `/api/opportunities/<id>` | Single opportunity |
| `GET` | `/api/invoices` | All invoices |
| `GET` | `/api/payments` | All payments |
| `GET` | `/api/revenue-journals` | All revenue journals |
| `GET` | `/api/events` | All events |
| `GET` | `/api/vouchers` | All vouchers |
| `GET` | `/api/search?q=<text>` | Full-text search across all collections |

There is no pagination, no filtering query parameters, and no write endpoints.
Always fetch the full collection list and filter client-side by the relevant
foreign key (`quote_id`, `customer_id`, `opportunity_id`, `invoice_id`).

## Core procedures

### Procedure A — Quote with freight comparison

Used when the task describes a **quote revision** that asks for **EXW pricing
plus freight options** (train 001, train 004).

**1. Resolve identifiers from the prompt.**
Extract the quote id (e.g. `Q-TR-WC-1187`), the product code, the confirmed
quantity, and the quote date.  The customer id may be embedded in the prompt
or discoverable from the quote record.

**2. Fetch the quote** — `GET /api/quotes/<quote_id>`.
From the quote record capture `customer_id`, `primary_product_code`,
`confirmed_quantity`, `quote_date`, `quote_type`, and `source_notes`.
The `source_notes` field often tells you which price tier to use and flags
special freight conditions.

**3. Fetch the customer** — `GET /api/customers/<customer_id>`.
Capture `name`, `segment`, `payment_profile`, `customer_type`, `is_recurring`,
`contacts`, and `notes`.

**4. Fetch the product and select the price tier.**
`GET /api/products/<product_code>`.  The product has a `price_tiers` array;
each tier has `min_qty`, `max_qty` (null = no upper bound), `unit_price_usd`,
and `lead_time_days`.  **Select the single tier where
`confirmed_quantity` falls in `[min_qty, max_qty]`.**  Never use a prior
quote's tier — the customer's new confirmed quantity determines the tier.
Also capture `shelf_life_months` and `article_number` from the product.

**5. Fetch freight quotes** and filter to the target `quote_id`.
`GET /api/freight-quotes` → keep only records whose `quote_id` matches the
target quote.  **Skip distractor freight quotes** whose `quote_id` is wrong,
whose `status` is `"stale"` or `"mismatch"`, or whose `shipment_cbm` /
`shipment_weight_kg` don't match the expected shipment (the distractor notes
often say things like "Old route benchmark" or "Wrong shipment size").

Each valid freight quote yields:

| Output field | Source |
|---|---|
| `freight_id` | `id` |
| `mode` | `mode`, uppercased: `air`→`AIR`, `sea`→`SEA`, `road`→`ROAD` |
| `freight_cost_usd` | `cost_usd` |
| `transit_days` | `transit_days_text` (the pre-formatted range string) |
| `valid_until` | `valid_until` (ISO date) |
| `risk_level` | `route_risk`, uppercased |
| `risk_flag` | Derived from `route_risk`: `"low"`→`"NONE"`, `"medium"`→`"MEDIUM_BORDER_RISK"`, `"high"`→`"HIGH_CUSTOMS_RISK"` |
| `grand_total_usd` | `exw_total_usd + cost_usd` |

For the variant with `validity_status`/`source_is_stale`/`customs_border_risk`
fields (train 004 template), add:

| Output field | Rule |
|---|---|
| `validity_status` | `"VALID"` if `status == "active"` AND `valid_until >= quote_date`; `"STALE"` if `status == "stale"` OR `valid_until < quote_date` |
| `source_is_stale` | `true` when `status == "stale"` OR `valid_until < quote_date` |
| `customs_border_risk` | **Derived from `risk_notes` text, not `route_risk`.**  Inspect the `risk_notes` string: if it contains "customs" or "border" and indicates a risk level, use that level uppercased (`"MEDIUM"`, `"HIGH"`).  If the `risk_notes` says nothing about customs or border risks, default to `"LOW"`.  Examples: "Temperature-controlled air lane with data logger support." → `"LOW"`; "Reefer LCL available; longer transit requires shelf-life review." → `"LOW"`; "customs risk high and expired before quote date" → `"HIGH"`. |

**Important distinction:** The `risk_level`/`risk_flag` pair uses the API's
`route_risk` enum directly.  The `customs_border_risk` field uses a
**keyword-based extraction from `risk_notes`** — a freight quote can have
`route_risk: "medium"` but `customs_border_risk: "LOW"` when the medium risk
is about transit time, not customs.

**6. Compute EXW total.**
`exw_total_usd = unit_price_usd × confirmed_quantity`

**7. Determine policy flags.**

| Field | Rule |
|---|---|
| `recommended_mode` | Prefer `"SEA"` when valid and low/medium risk (best cost-transit balance). Use `"AIR"` when transit urgency or cold-chain demands it. Never recommend a `STALE` or `HIGH`-risk option. |
| `freight_reconfirmation_required` | Always `true` — policy `POL-FREIGHT-RECONFIRM` requires reconfirmation at final order. |
| `all_freight_options_valid_on_quote_date` | `true` iff every freight option's `valid_until >= quote_date` |
| `customer_policy` | Derived from customer `segment`: `"recurring_ngo"`→`"RECURRING_NGO"`, `"new_ngo"`→`"NEW_NGO"`, `"recurring_commercial"`→`"RECURRING_COMMERCIAL"`, `"government_program"`→`"GOVERNMENT_PROGRAM"` |
| `payment_terms` | From the customer's `payment_profile` field directly (e.g. `"NET_30_AFTER_PO"`) |

For the template variant with `client_warnings` (train 004):

| Field | Rule |
|---|---|
| `road_quote_invalid_or_stale` | `true` if the ROAD freight's `valid_until < quote_date` OR `status == "stale"` OR `route_risk == "high"` |
| `freight_warning` | Compose a sentence listing any stale/expired freight ids with dates and any high-risk flags. |
| `policy_terms.quote_basis` | `"EXW_PLUS_FREIGHT_OPTIONS"` |
| `policy_terms.payment_terms` | Same as `payment_terms` above. |
| `policy_terms.freight_reconfirmation_required` | `true` |

### Procedure B — Module / IEHK indicative RFQ (EXW only, no freight)

Used when the task describes an **RFQ with modules** and the customer has
**no confirmed destination**, meaning freight must be excluded (train 002).

**1. Resolve identifiers.** Extract `rfq_id` and `quote_date` from the prompt.

**2. Fetch the RFQ** — `GET /api/rfqs/<rfq_id>`.
Capture `customer_id` and `requested_modules` (array of `{product_code, quantity}`).

**3. Fetch the customer** — `GET /api/customers/<customer_id>`.
Capture `segment`, `payment_profile`, `customer_type`.

**4. For each requested module, fetch the product** (`GET /api/products/<code>`)
and build a line item:

| Output field | Source |
|---|---|
| `product_code` | From RFQ `requested_modules[].product_code` |
| `article_number` | Product `article_number` |
| `quantity` | From RFQ `requested_modules[].quantity` |
| `unit_price` | `price_tiers[0].unit_price_usd` (module products typically have one tier with `min_qty: 1, max_qty: null`) |
| `lead_time_days` | `price_tiers[0].lead_time_days` |
| `shelf_life_months` | Product `shelf_life_months` |
| `line_total` | `unit_price × quantity` |

**IMPORTANT — Module granularity rule:** Even if the RFQ or product record
lists `component_composition_distractors` or `components`, quote at the
**module level only**.  Do NOT split into component SKUs or individual items.
Policy `POL-MODULE-GRANULARITY` enforces this.

**5. Compute controls.**

| Field | Rule |
|---|---|
| `grand_total` | Sum of all `line_total` values, rounded to 2 decimal places |
| `freight_excluded` | `true` (no destination → policy `POL-INDICATIVE-EXW`) |
| `payment_terms` | `"PREPAY_100"` when `customer.segment == "new_ngo"` (policy `POL-NEW-CLIENT-PAYMENT`); otherwise use the customer's `payment_profile` |
| `offer_validity_days` | `30` (policy `POL-QUOTE-VALIDITY`) |
| `who_documentation_required` | `true` for IEHK-family products; check the product family or the response template hints |

**6. Set `quote_basis`** to `"EXW_ONLY"` in the header.

### Procedure C — Account / milestone reconciliation with event invite

Used when the task asks to reconcile a **won opportunity** with its milestone
invoices, payments, revenue recognition, linked events, and vouchers, and to
generate follow-up tasks (train 003, train 005).

**1. Resolve identifiers.** Extract `opportunity_id`, `customer_id`, the
contact name, and the business date (defaults to the quote date if not stated)
from the prompt.

**2. Fetch the opportunity** — `GET /api/opportunities/<opportunity_id>`.
Capture `stage`, `won_amount_usd`, `phases`, `contact`, `customer_id`, `notes`.
Map the stage: `"closed_won"`→`"WON"`, `"proposal"`/`"negotiation"`→`"OPEN"`.

**3. Fetch supporting records** (fetch all collections and filter client-side):

| Collection | Filter by | Purpose |
|---|---|---|
| `customers` | `id == customer_id` | Customer name, contacts |
| `invoices` | `opportunity_id` | Invoice amounts, status, due dates |
| `payments` | `opportunity_id` | Payment amounts and dates |
| `revenue-journals` | `opportunity_id` | Revenue recognition postings |
| `events` | `opportunity_id` | Linked celebration/briefing events |
| `vouchers` | `opportunity_id` (or `event_id`) | Voucher codes and limits |

**4. Build milestones.** Merge data from opportunity `phases`, invoices,
payments, and revenue journals. Match on `phase_id` ↔ invoice `phase_id` ↔
payment `invoice_id` ↔ journal `phase_id`/`invoice_id`.

For each milestone determine:

| Field | Rule |
|---|---|
| `invoice_state` / `payment_status` | From invoice `status`: `"paid"`→`"PAID"`, `"unpaid"`→`"UNPAID"`, `"overdue"`→`"UNPAID"` |
| `paid_amount` | From payment record `amount_usd` when invoice is paid; `0.00` otherwise |
| `amount_unpaid` / `outstanding` | `invoice_total - paid_amount` |
| `due_date` | Invoice `due_date` when unpaid; `null` when paid |
| `recognition_status` | See revenue recognition rules below |

**5. Revenue recognition rules** (policy `POL-REVREC`):

| Invoice state | Journal exists? | Recognition status |
|---|---|---|
| PAID | Yes, posted | `"RECOGNIZED"` |
| PAID | No | `"MISSING_REVENUE_JOURNAL"` (or `"REQUIRED_MISSING"`, per template) |
| UNPAID | — | `"NOT_REQUIRED_UNPAID"` |

**6. Compute summary fields:**

| Field | Rule |
|---|---|
| `phase_total_amount` | Sum of all phase `amount_usd` from the opportunity |
| `opportunity_matches_phase_total` / `opportunity_matches_milestones` | `true` iff `won_amount == phase_total_amount` |
| `total_paid_amount` | Sum of all payment `amount_usd` linked to this opportunity |
| `outstanding_balance` | `won_amount - total_paid_amount` |

**7. Revenue recognition roll-up:**

| Field | Rule |
|---|---|
| `recognition_status` | `"COMPLETE_FOR_PAID_MILESTONES"` if all PAID milestones have journals; `"MISSING_FOR_PAID_MILESTONES"` if any PAID milestone lacks a journal |
| `recognized_milestones` | List of milestone IDs with journal entries |
| `missing_required_milestones` | List of milestone IDs that are PAID but have no journal |
| `recognized_amount` | Sum of amounts for recognized milestones |

**8. Generate follow-up tasks.**

**COLLECTION task** — create when a milestone has `payment_status == "UNPAID"`:
- `task_type`: `"COLLECTION"`
- `task_title`: `"Milestone <N> collection - <customer_name>"`
- `due_date`: The invoice `due_date` (or a derived date per template convention)
- `next_action`: `"COLLECT_UNPAID_MILESTONE"` when overdue or approaching; `"MONITOR_UNPAID_NOT_DUE"` when not yet due
- `amount_due`: The `amount_unpaid`

**EVENT_INVITATION task** — create for the linked event:
- `task_type`: `"EVENT_INVITATION"`
- `task_title`: `"Send <event_type> invite - <customer_name>"`
- `due_date`: A reasonable lead time before the event date (often ~21 days before, or as specified by the template)
- `next_action`: `"SEND_EVENT_INVITATION"` or `"SEND_BRIEFING_INVITE"` per template
- `event_id` and `voucher_code` linked to the event

**9. Invoice actions / accounting journal entries** (for template variants with
`invoice_actions` and `accounting_action` blocks, train 005):

| Condition | `primary_accounting_action` | Journal entry |
|---|---|---|
| Paid milestone with no revenue journal | `"RECORD_REVENUE_MS2"` (use the specific milestone) | Debit: `"DEFERRED_REVENUE"`, Credit: `"IMPLEMENTATION_SERVICES_REVENUE"`, Owner: `"ACCOUNTING"` |
| All paid milestones recognized | `"VERIFY_REVENUE_ONLY"` | — |

| Collection state | `collection_action` |
|---|---|
| Unpaid but not yet due | `"MONITOR_UNPAID_NOT_DUE"` |
| Unpaid and overdue | `"SEND_COLLECTION_NOTICE"` |

## Output format & conventions

Always return **only valid JSON** — no markdown fences, no explanatory text.
Match the exact structure of the answer template provided in
`input/payloads/answer_template.json`.

### Money
All monetary values are in USD with **two decimal places** (e.g. `42480.00`).
Use `0.00` for zero amounts, never `0`.

### Dates
ISO 8601 `YYYY-MM-DD` format.  Use `null` (not the string `"null"`) for
absent dates.

### Enums
Always UPPER_SNAKE_CASE.  Match the controlled vocabulary declared in the
answer template's type hints exactly — do not invent new enum values.

### IDs
Use stable record IDs from the API (`id` fields).  Do not construct or
guess IDs.

## Field mapping reference

### Products — price tier selection

```
confirmed_quantity = 360
tier where min_qty <= 360 AND (max_qty >= 360 OR max_qty IS NULL)
→ unit_price_usd, lead_time_days
```

Price tiers are checked in array order; select the **first** matching tier.
A `null` `max_qty` means "no upper bound."

### Freight validity

A freight quote is **valid on the quote date** when:
`valid_until >= quote_date` AND `status == "active"`.

A freight quote is **stale** when:
`valid_until < quote_date` OR `status == "stale"`.

### Customer payment terms

| Customer segment | Typical payment_profile | Policy |
|---|---|---|
| `new_ngo` | `NEW_CLIENT_REVIEW` | `PREPAY_100` |
| `recurring_ngo` | `NET_30_AFTER_PO` | `NET_30_AFTER_PO` |
| `recurring_commercial` | `NET_30_AFTER_PO` | `NET_30_AFTER_PO` |
| `government_program` | `NET_30_AFTER_PO` or `MILESTONE_BILLING` | Per customer record |
| `implementation_services` | `MILESTONE_BILLING` | Per customer record |

### Risk level mapping

**For `risk_level` and `risk_flag`** (train 001-style templates) — use the API's
`route_risk` field directly:

| API `route_risk` | Output `risk_level` | Output `risk_flag` |
|---|---|---|
| `"low"` | `"LOW"` | `"NONE"` |
| `"medium"` | `"MEDIUM"` | `"MEDIUM_BORDER_RISK"` |
| `"high"` | `"HIGH"` | `"HIGH_CUSTOMS_RISK"` |

**For `customs_border_risk`** (train 004-style templates) — keyword-match the
`risk_notes` text instead.  Search for "customs" or "border" in the notes;
use the associated risk level if found, otherwise default to `"LOW"`.  Never
copy `route_risk` into this field — it captures a different signal.

## Common pitfalls

1. **Wrong price tier.**  The customer's *new confirmed quantity* sets the
   tier, not the prior quote quantity or a previously used tier.  A quantity
   of 360 for WC-KIT-A uses the 300–499 tier ($118.00), not the 150–299 tier
   ($124.00) that a prior 240-unit order used.

2. **Distractor freight quotes.**  The freight-quotes collection contains
   records for *every* quote in the system, including distractor quotes from
   other products.  Always filter by the target `quote_id` and verify the
   record's `status` is `"active"`.  Ignore records where `status` is
   `"stale"` or `"mismatch"` or where the `quote_id` doesn't match.

3. **Module granularity leaks.**  When an RFQ lists `component_composition_
   distractors` (e.g. "Paracetamol tabs listed under basic module"), do NOT
   break the quote into component line items.  Quote at the module product
   code level only.

4. **Freight exclusion when destination is pending.**  If the customer RFQ
   says "destination pending" or the prompt says "no destination for a
   transport estimate," set `freight_excluded: true` and do not include
   freight options.  Policy `POL-INDICATIVE-EXW` enforces this.

5. **Revenue journal lookup scope.**  A paid invoice without a corresponding
   revenue-journal entry means revenue has NOT been recognized for that
   milestone.  This drives the `MISSING_REVENUE_JOURNAL` status and the
   `RECORD_REVENUE_*` accounting action.

6. **Invoice status `"overdue"` vs `"unpaid"`.** Both mean the invoice is
   unpaid; `"overdue"` means `due_date` has passed relative to the business
   date.  In the output, both map to payment status `"UNPAID"`, but the
   collection action should escalate for overdue invoices.

7. **Voucher amounts are discount percentages, not dollar amounts.**  The API
   voucher `discount_percent` field is a percentage (e.g. 100 means 100% off,
   50 means 50% off).  Some answer templates expect a `voucher_discount` or
   `discount_amount` in dollars — use the value from the API voucher record
   as-is unless the template explicitly asks for a different unit.

8. **Contact linking.**  Always tie the contact person named in the prompt to
   all follow-up tasks, even when other contacts exist on the customer record.
   The prompt-named contact is the account owner for the current request.

9. **The `payment_profile` directly names the payment terms for non-NGO
   clients.**  For recurring commercial and government customers, the
   `payment_profile` field IS the `payment_terms` output value (e.g.
   `"NET_30_AFTER_PO"`, `"MILESTONE_BILLING"`).  Only new NGO clients get
   the policy-driven override to `"PREPAY_100"`.

10. **Always use the template structure.**  The `answer_template.json` in
    `input/payloads/` defines the exact JSON shape, including field names
    and enum values.  Match it precisely — do not rename fields, add extra
    fields, or change the casing of enum values from what the template
    declares.

## Entity relationship map

```
customers.id ─── rfqs.customer_id
    │            quotes.customer_id
    │            opportunities.customer_id
    │            invoices.customer_id
    │            payments.customer_id
    │            events.customer_id
    │            vouchers.customer_id
    │
products.code ─── rfqs.requested_modules[].product_code
    │             quotes.line_items[].product_code
    │
quotes.id ─── freight-quotes.quote_id
    │
opportunities.id ─── invoices.opportunity_id
    │                payments.opportunity_id
    │                revenue-journals.opportunity_id
    │                events.opportunity_id
    │                vouchers.opportunity_id
    │
opportunities.phases[].phase_id ─── invoices.phase_id
    │                               revenue-journals.phase_id
    │
invoices.id ─── payments.invoice_id
    │           revenue-journals.invoice_id
    │
events.id ─── vouchers.event_id
```

When working on Procedure C (reconciliation), use `opportunity_id` as the
primary join key to pull invoices, payments, revenue journals, events, and
vouchers in one sweep.  Then match sub-records by `phase_id` and
`invoice_id` to build the per-milestone view.
