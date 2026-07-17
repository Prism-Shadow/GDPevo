# MedBridge Sales Ops API — Skill for Quote & Reconciliation Packages

## Environment

All API calls go to the shared MedBridge Sales Ops base URL. The task runner provides it
as `API_BASE_URL`, `BASE_URL`, or the task environment base URL. There is no local server;
the remote API is the only data source.

## API Overview

| Collection       | Key endpoints                                                        |
| ---------------- | -------------------------------------------------------------------- |
| customers        | `GET /api/customers`, `GET /api/customers/<id>`                       |
| products         | `GET /api/products`, `GET /api/products/<code>`                       |
| quotes           | `GET /api/quotes`, `GET /api/quotes/<id>`                             |
| freight-quotes   | `GET /api/freight-quotes` (filter client-side by `quote_id`)          |
| policies         | `GET /api/policies`                                                  |
| rfqs             | `GET /api/rfqs`, `GET /api/rfqs/<id>`                                 |
| opportunities    | `GET /api/opportunities`, `GET /api/opportunities/<id>`               |
| invoices         | `GET /api/invoices` (filter client-side by `customer_id`/`opportunity_id`) |
| payments         | `GET /api/payments` (filter client-side)                              |
| revenue-journals | `GET /api/revenue-journals` (filter client-side)                      |
| events           | `GET /api/events` (filter client-side)                                |
| vouchers         | `GET /api/vouchers` (filter client-side)                              |
| search           | `GET /api/search?q=<text>`                                            |

All collections return `{"collection": "...", "count": N, "records": [...]}`.
Single-record endpoints return the object directly. There is no server-side filtering
beyond the single-record lookups and search; filter multi-record results in your code.

## Data Source Precedence

1. **API records are always authoritative.** A prompt narrative may use a colloquial
   customer name (e.g. "Health Horizon Aid") while the API customer record holds the
   canonical name ("HealthHands Alliance"). Use the API values for all structured fields
   (`customer_id`, `customer_name`, `product_code`, amounts, dates, status enums).

2. **Quote records override prior quotes.** The quote object carries `confirmed_quantity`,
   `quote_date`, `source_notes`, and line items. Use these for the current revision; do
   not carry forward prior unit prices or quantities from older RFQs or quote history.

3. **Product catalog tiers are the source of truth for unit price, lead time, and shelf
   life.** Match the confirmed quantity to the tier whose `min_qty ≤ quantity ≤ max_qty`
   (treat a `null` max_qty as unbounded). Do not use the `prior_unit_price_usd` from the
   quote — the quote's `source_notes` may explicitly say "catalog tier overrides prior
   unit price."

4. **Policies define payment terms and quote controls.** Look up the policy whose
   `applies_to` matches the customer segment. The policy `terms_code` is the canonical
   value for `payment_terms` fields.

## Product Pricing Rules

### Tier Selection

Each product has a `price_tiers` array. For a given `confirmed_quantity`:

```
tier = product.price_tiers.find(t => quantity >= t.min_qty && (t.max_qty === null || quantity <= t.max_qty))
```

Use `tier.unit_price_usd`, `tier.lead_time_days`, `tier.shelf_life_months`.

### EXW Total

```
exw_total_usd = round(confirmed_quantity × tier.unit_price_usd, 2)
```

All money fields use two decimal places.

### Module / Kit Quotes

- **Module RFQs** (e.g. IEHK, field clinic, cholera): quote at the module level only.
  Use `product_code` and `article_number` from the product record. Ignore
  `component_composition_distractors` in the RFQ — they are for medical review, not
  line-item pricing.
- Line items appear in the same order as the RFQ `requested_modules` list.
- Module products have a single price tier (min_qty 1, max_qty null); no volume breaks.

### Quote Validity

Per `POL-QUOTE-VALIDITY`: catalog pricing is valid for **30 calendar days** from
`quote_date`. Set `offer_validity_days: 30`.

## Freight & Transport Rules

### Finding the Right Freight Quotes

Filter the `/api/freight-quotes` collection by `quote_id`. Then exclude distractors:

| Exclusion reason  | How to detect                                            |
| ----------------- | -------------------------------------------------------- |
| Stale / expired   | `status === "stale"` or `valid_until < quote_date`       |
| Wrong shipment    | `status === "mismatch"` or notes mention wrong quantity  |
| Wrong quote_id    | `quote_id` doesn't match the target quote                |
| "Old" / archived  | Notes say "old route", "benchmark", or "distractor"      |

Only keep records whose `status === "active"` AND `valid_until >= quote_date`.  A
record can be `active` but already expired — `status` alone is not enough.

### Freight Field Mapping

| Template field          | API source                   | Notes                                        |
| ----------------------- | ---------------------------- | -------------------------------------------- |
| `freight_id`            | `id`                         |                                              |
| `mode`                  | `mode` → uppercase           | `air`→`AIR`, `sea`→`SEA`, `road`→`ROAD`     |
| `freight_cost_usd`      | `cost_usd`                   |                                              |
| `transit_days`          | `transit_days_text`          | e.g. `"4-6 days"`, `"28-34 days"`            |
| `valid_until`           | `valid_until`                | ISO date                                     |
| `validity_status`       | `status` → `"valid"` or      | `active`→`"valid"`, `stale`→`"expired"`      |
|                         | `"expired"`                  |                                              |
| `source_is_stale`       | `valid_until < quote_date`   | boolean                                      |
| `customs_border_risk`   | `route_risk`                 | lowercase: `"low"`, `"medium"`, `"high"`     |
| `risk_level`            | `route_risk` → uppercase     | `low`→`LOW`, `medium`→`MEDIUM`, `high`→`HIGH`|
| `risk_flag`             | Derived from `risk_notes`    | `NONE` for low, `MEDIUM_BORDER_RISK` for     |
|                         |                              | medium border notes, varies by context       |
| `grand_total_usd`       | `exw_total + freight_cost`   |                                              |

### Recommended Mode

- **Non-cold-chain products**: recommend the cheapest mode with low risk (usually **SEA**).
- **Cold-chain products** (product has `cold_chain_required: true`): recommend **SEA** when
  transit time fits comfortably within shelf life. Only recommend **AIR** when transit time
  plus a buffer would exceed a material fraction of shelf life, or when the destination
  has an urgent delivery deadline.
- **ROAD** is never recommended when it carries a medium or high border risk, or when the
  quote is stale/expired.

### Freight Validity & Reconfirmation

- `all_freight_options_valid_on_quote_date`: `true` only when **every** active freight
  quote has `valid_until >= quote_date`.
- `freight_reconfirmation_required`: `true` when (a) any freight quote has a border risk
  note saying "reconfirm before PO", (b) any quote expires within 14 days of the quote
  date, or (c) the policy `POL-FREIGHT-RECONFIRM` applies.
- `road_quote_invalid_or_stale`: `true` when the road freight is stale (`valid_until <
  quote_date`) or has `status !== "active"`.

### Freight Warning Text

When road freight is stale or has high border risk, include a `freight_warning` like:
`"Road freight quote expired; high customs risk."` Add a note about sea transit if the
product is cold-chain and sea transit exceeds ~14 days.

## Payment Terms Rules

| Customer segment / type          | Policy                          | `payment_terms` value     |
| -------------------------------- | ------------------------------- | ------------------------- |
| New NGO (no credit history)      | `POL-NEW-CLIENT-PAYMENT`        | `PREPAY_100`              |
| Recurring NGO                    | `POL-RECURRING-NGO-PAYMENT`     | `NET_30_AFTER_PO`         |
| Recurring commercial             | (customer `payment_profile`)    | `NET_30_AFTER_PO`         |
| Milestone billing (services)     | (customer `payment_profile`)    | `MILESTONE_BILLING`       |

For quote-style tasks, the `payment_terms` field uses the policy `terms_code` or the
customer's `payment_profile` value. When a specific policy matches the customer segment,
use the policy's `terms_code`.

## Reconciliation Rules (Opportunities, Invoices, Revenue)

### Opportunity Stage Mapping

The API returns verbose stage values. Map them to the template enum:

| API `stage`      | Template `stage` / `opportunity_stage` |
| ---------------- | -------------------------------------- |
| `closed_won`     | `WON`                                  |
| `open`           | `OPEN`                                 |
| `closed_lost`    | `LOST`                                 |

### Milestone / Phase Mapping

- Milestones use `MS1`, `MS2`, `MS3` as milestone IDs, ordered by phase number ascending.
- Map `phase_id` from the opportunity (e.g. `MER-P1`, `MER-P2`, `MER-P3`) to `MS1`/`MS2`/`MS3`
  based on phase order.
- Reference invoices by the milestone's invoice_id; look up the corresponding invoice record
  for payment status and amounts.

### Invoice State Mapping

| API invoice `status` | Template `invoice_state` | Template `payment_state` |
| -------------------- | ------------------------ | ------------------------ |
| `paid`               | `PAID`                   | `PAID`                   |
| `unpaid`             | `OPEN`                   | `UNPAID`                 |
| `overdue`            | `OPEN`                   | `UNPAID`                 |
| `draft`              | `OPEN`                   | `UNPAID`                 |

### Revenue Recognition Status Per Milestone

For each milestone, determine `recognition_status`:

| Condition                                                  | `recognition_status`         |
| ---------------------------------------------------------- | ---------------------------- |
| Paid AND has a matching revenue-journal entry              | `RECOGNIZED`                 |
| Paid (or partially paid) but NO matching revenue-journal   | `MISSING_REVENUE_JOURNAL`    |
| Not paid (regardless of completion)                        | `NOT_REQUIRED_UNPAID`        |

Match revenue journals to milestones by `invoice_id` or `phase_id`.

### Overall Revenue Recognition Status

| Condition                                                   | `recognition_status`              |
| ----------------------------------------------------------- | --------------------------------- |
| All paid milestones have journal entries                    | `COMPLETE_FOR_PAID_MILESTONES`    |
| Any paid milestone lacks a journal entry                    | `MISSING_FOR_PAID_MILESTONES`     |
| No paid milestones exist                                    | `NOT_REQUIRED`                    |

### Accounting Action (for Missing Revenue Recognition)

When a milestone is paid but has `MISSING_REVENUE_JOURNAL`:

```
accounting_action:
  action: RECORD_REVENUE_MS2           # or RECORD_REVENUE_MS1, etc.
  milestone_id: MS2                    # the milestone with the gap
  amount: <paid_amount>
  debit_account: DEFERRED_REVENUE
  credit_account: IMPLEMENTATION_SERVICES_REVENUE
  owner_queue: ACCOUNTING
```

The `primary_accounting_action` matches the action field (`RECORD_REVENUE_MS2`, etc.).
When all paid milestones are recognized, use `VERIFY_REVENUE_ONLY` or
`NO_ACCOUNTING_ACTION`.

### Collection Action

| Invoice state                            | Due date vs. current date | Action                     |
| ---------------------------------------- | ------------------------- | -------------------------- |
| Unpaid, not yet due                      | `due_date > today`        | `MONITOR_UNPAID_NOT_DUE`   |
| Unpaid and overdue                       | `due_date ≤ today`        | `SEND_COLLECTION_NOTICE`   |
| All paid                                 | —                         | `NO_COLLECTION_ACTION`     |

### Phase Total vs Won Amount

```
phase_total = sum of all milestone amounts from the opportunity phases
opportunity_matches_phase_total = (phase_total === won_amount)
```

### Outstanding Balance

The `outstanding_balance` equals the sum of `outstanding_amount_usd` or `amount_unpaid`
across all unpaid invoices for the opportunity.

### Total Paid Amount

Sum of `paid_amount_usd` from all payments linked to the opportunity's invoices.

## Event & Voucher Rules

### Event Fields

| Template field    | API source                          |
| ----------------- | ----------------------------------- |
| `event_id`        | `id`                                |
| `event_date`      | `event_date`                        |
| `event_status`    | `status` → UPPERCASE                |
| `voucher_code`    | `voucher_code` from event record    |

### Voucher Fields

| Template field      | API source                          |
| -------------------- | ----------------------------------- |
| `voucher_code`       | `code`                              |
| `voucher_status`     | `status` → UPPERCASE                |
| `voucher_discount` / | `discount_percent`                  |
| `discount_amount`    | (the percentage number itself)      |
| `voucher_max_uses` / | `max_redemptions`                   |
| `max_uses`           |                                     |

When a voucher has a percentage discount (`discount_percent`) but the template asks for a
numeric `discount_amount` / `voucher_discount`, use the percentage value directly (e.g.
`50` for 50%, `100` for 100%).

### Invitation Logic

| Event status  | Voucher status | `invite_action`          |
| ------------- | -------------- | ------------------------ |
| `SCHEDULED`   | `ACTIVE`       | `SEND_BRIEFING_INVITE`   |
| `COMPLETED`   | (any)          | `NO_INVITE_ACTION`       |
| `CANCELLED`   | (any)          | `NO_INVITE_ACTION`       |

The `invite_task` mirrors the `invite_action` and populates:
- `owner_queue`: `ACCOUNT_MANAGEMENT` (from the event's `follow_up_owner`)
- `contact_name`: the opportunity/customer primary contact
- `customer_id`: the customer linked to the opportunity

### Follow-Up Tasks (Event Invitation)

When an event is scheduled and its voucher is active, create an `EVENT_INVITATION`
follow-up task:
- `task_type`: `EVENT_INVITATION`
- `next_action`: `SEND_EVENT_INVITATION`
- `due_date`: a reasonable lead time before the event date (typically 3 weeks before)
- Link to `event_id` and `voucher_code`

### Follow-Up Tasks (Collection)

Create a `COLLECTION` follow-up task when an unpaid milestone's due date has passed or
is imminent:
- `task_type`: `COLLECTION`
- `next_action`: `COLLECT_UNPAID_MILESTONE`
- `due_date`: the invoice due date
- `milestone_id`: the unpaid milestone
- `amount_due`: the unpaid amount

## Common Pitfalls

1. **Distractor freight quotes.** The freight collection contains records with wrong
   `quote_id`, wrong shipment dimensions, stale status, and distractor notes. Always
   filter by exact `quote_id` match AND active/non-stale status.

2. **Customer name mismatch.** The prompt narrative may use a different name than the
   API. The API `name` field is authoritative for `customer_name` in output.

3. **Component distractors in module RFQs.** RFQs for IEHK, field clinic, and cholera
   modules include `component_composition_distractors` listing individual medicines/supplies.
   Ignore these; quote at the module level only.

4. **Prior-tier pricing.** Quote `line_items` may carry `prior_unit_price_usd` and
   `prior_quote_quantity`. These are historical; always use the current catalog tier
   based on `confirmed_quantity`.

5. **Road freight is often problematic.** Road quotes frequently have medium/high border
   risk, short validity windows, or are already stale by the quote date. Always check
   `valid_until` against `quote_date` before including road freight as a viable option.

6. **`status: "active"` doesn't mean the freight quote is still valid.** An active freight
   quote can have a `valid_until` date before the quote date. Always check both status
   and date.

7. **Invoice `status: "unpaid"` maps to `invoice_state: "OPEN"`, not `"UNPAID"`.** The
   template enum for invoice state is `PAID | OPEN | VOID | UNKNOWN`. `payment_state`
   separately captures `PAID | PARTIAL | UNPAID`.

8. **Missing revenue journal for a paid milestone is the critical accounting gap.**
   The opportunity notes may flag this explicitly. Always cross-reference invoices
   (paid) against revenue-journals (recognized).

9. **`discount_amount` for vouchers is the percentage value, not a dollar amount.**
   Even when the template says "USD, two decimals", use the `discount_percent` number.

10. **EXW quotes exclude freight by definition.** When `quote_basis` is `EXW` or
    `EXW_ONLY`, do not include freight in the core pricing. Freight options, when
    present, are additive and listed separately.

11. **Indicative quotes without a destination are EXW-only.** Per `POL-INDICATIVE-EXW`,
    set `freight_excluded: true` and do not include freight options.

12. **New NGO accounts require prepayment.** Per `POL-NEW-CLIENT-PAYMENT`, use
    `PREPAY_100` as payment terms regardless of what the customer record's
    `payment_profile` field says.

## Output Field Conventions

- **Dates**: ISO `YYYY-MM-DD` format.
- **Money**: numbers with exactly two decimal places (e.g. `50000.00`, not `50000`).
- **Enums**: UPPERCASE for template enums (`WON`, `PAID`, `RECOGNIZED`); lowercase for
  API-derived risk/customs values (`"low"`, `"medium"`, `"high"`).
- **Record IDs**: use the exact ID from the API (`quote_id`, `customer_id`, `freight_id`,
  `milestone_id`, `event_id`, `voucher_code`). Do not generate or transform IDs.
- **Transit days**: use the `transit_days_text` string verbatim (e.g. `"4-6 days"`).
- **Booleans**: JSON `true`/`false`, never strings.
