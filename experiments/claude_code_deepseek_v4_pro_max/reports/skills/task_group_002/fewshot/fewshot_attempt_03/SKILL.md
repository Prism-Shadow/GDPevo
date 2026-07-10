# MedBridge Sales Ops — Condition Fewshot Skill

## Environment

```
API_BASE_URL=http://34.46.77.124:8002
```

All task prompts reference `API_BASE_URL`, `BASE_URL`, or a localhost placeholder. Always resolve to the remote base above. The API is a read-only shared data source with 12 collections.

### API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api` | List all collections and endpoints |
| GET | `/api/health` | Health check |
| GET | `/api/customers` | List all customers |
| GET | `/api/customers/<id>` | Single customer |
| GET | `/api/products` | List all products |
| GET | `/api/products/<code>` | Single product with price tiers |
| GET | `/api/quotes` | List all quotes |
| GET | `/api/quotes/<id>` | Single quote with line items |
| GET | `/api/rfqs` | List all RFQs |
| GET | `/api/rfqs/<id>` | Single RFQ with requested modules |
| GET | `/api/freight-quotes` | List all freight quotes |
| GET | `/api/freight-quotes/<id>` | Single freight quote |
| GET | `/api/policies` | List all business policies |
| GET | `/api/opportunities` | List all opportunities |
| GET | `/api/opportunities/<id>` | Single opportunity with phases |
| GET | `/api/invoices` | List all invoices |
| GET | `/api/payments` | List all payments |
| GET | `/api/revenue-journals` | List all revenue journals |
| GET | `/api/events` | List all events |
| GET | `/api/vouchers` | List all vouchers |
| GET | `/api/search?q=<text>` | Text search across collections |

The API is deterministic (fixed seed per task group). All monetary values are in USD with two decimal places. Dates are ISO 8601 (`YYYY-MM-DD`).

---

## Task Type 1: Quote Revision with Freight

**Trigger:** Prompt mentions a quote ID (e.g., `Q-TR-WC-1187`, `Q-TR-LD-5521`), a product code, a confirmed quantity, and asks for EXW pricing plus freight comparison.

### Step-by-step procedure

1. **Fetch the quote** — `GET /api/quotes/<quote_id>`. Extract `customer_id`, `quote_date`, `primary_product_code`, `confirmed_quantity`.

2. **Fetch the customer** — `GET /api/customers/<customer_id>`. Determine payment terms from `payment_profile`:
   - `NET_30_AFTER_PO` → used for recurring NGO and commercial accounts
   - `PREPAY_100` → used for new/unapproved clients
   - `MILESTONE_BILLING` → used for implementation services accounts

3. **Fetch the product** — `GET /api/products/<product_code>`. Match the confirmed quantity to the correct price tier:
   - Each tier has `min_qty`, `max_qty` (nullable for the top tier), `unit_price_usd`, `lead_time_days`.
   - Select the tier where `min_qty <= confirmed_quantity <= max_qty` (treat `null` max_qty as infinity).
   - Also capture `shelf_life_months`.

4. **Calculate EXW total** — `confirmed_quantity × unit_price_usd`.

5. **Fetch all freight quotes** — `GET /api/freight-quotes`. Filter to records where `quote_id` matches the current quote. Exclude distractors:
   - Records whose `id` doesn't follow the expected naming pattern for this quote
   - Records with status `"stale"` whose `valid_until` is before the `quote_date` — these are still listed but flagged

6. **Process each freight option:**
   - Use `mode` (normalize: `"air"` → `"AIR"`, `"sea"` → `"SEA"`, `"road"` → `"ROAD"`)
   - `freight_cost_usd` comes from `cost_usd`
   - `transit_days` comes from `transit_days_text`
   - `valid_until` is the freight quote expiry
   - **Validity check:** If `valid_until < quote_date`, the freight is STALE (`validity_status: "STALE"`, `source_is_stale: true`). Otherwise `"VALID"`, `false`.
   - **Risk assessment** — read `risk_notes` text, NOT `route_risk` alone:
     - If `risk_notes` mentions "customs" or "border" AND "high" → `customs_border_risk: "HIGH"`
     - If `risk_notes` mentions "border" AND "medium" → `customs_border_risk: "MEDIUM"` or use template-specific field like `risk_level: "MEDIUM"`, `risk_flag: "MEDIUM_BORDER_RISK"`
     - If `risk_notes` mentions only transit-time, shelf-life, or capacity concerns → `customs_border_risk: "LOW"` / `risk_level: "LOW"`, `risk_flag: "NONE"`
   - **Grand total:** `exw_total_usd + freight_cost_usd`

7. **Determine recommended mode** — Default to `"SEA"` (lowest cost valid option). Override if the only valid options have concerns.

8. **Freight reconfirmation** — Always `true` per policy POL-FREIGHT-RECONFIRM: "Freight rates need reconfirmation at final order."

9. **Policy flags / warnings:**
   - `all_freight_options_valid_on_quote_date`: `true` if every freight option's `valid_until >= quote_date`
   - `road_quote_invalid_or_stale`: `true` if the ROAD freight is stale or invalid
   - `freight_warning`: Compose a warning string mentioning any stale freight and high-risk routes
   - `quote_basis`: `"EXW"` for template v1, `"EXW_PLUS_FREIGHT_OPTIONS"` for template v4
   - `customer_policy`: Use `segment` field from customer, uppercased (e.g., `recurring_ngo` → `"RECURRING_NGO"`)

### Template-specific output notes

**Template v1 (train_001 style):** Top-level `quote_summary` with `unit_price_usd`, `lead_time_days`, `shelf_life_months`, `quote_basis: "EXW"`, `exw_total_usd`. Then `freight_options` array (always 3: AIR, SEA, ROAD) with `risk_level` / `risk_flag`. Then `policy_flags` with `recommended_mode`, `freight_reconfirmation_required`, `all_freight_options_valid_on_quote_date`, `customer_policy`, `payment_terms`.

**Template v4 (train_004 style):** Top-level `pricing` with nested `catalog_tier` object (including `min_quantity`, `max_quantity`). Then `transport_decisions` with `freight_options` array using `validity_status`, `source_is_stale`, `customs_border_risk`. Then `client_warnings` with `road_quote_invalid_or_stale`, `freight_warning` string, and `policy_terms` block.

---

## Task Type 2: Indicative RFQ / Module Quote (No Freight)

**Trigger:** Prompt mentions an RFQ ID (e.g., `RFQ-TR-IEHK-204`), asks for indicative EXW-only pricing, often mentions a new NGO account or no destination.

### Step-by-step procedure

1. **Fetch the RFQ** — `GET /api/rfqs/<rfq_id>`. Extract `customer_id`, `quote_date`, `requested_modules` array (each has `product_code`, `quantity`).

2. **Fetch the customer** — `GET /api/customers/<customer_id>`. New NGO (`is_recurring: false`, `segment: "new_ngo"`) → `PREPAY_100`. Check `customer_type: "NGO"`.

3. **Fetch each module product** — `GET /api/products/<product_code>` for each requested module. Capture:
   - `article_number`
   - `unit_price_usd` from price tiers (IEHK modules typically have a single tier with `min_qty: 1, max_qty: null`)
   - `lead_time_days`
   - `shelf_life_months`

4. **Calculate line totals** — `quantity × unit_price_usd` for each module.

5. **Calculate grand total** — Sum of all `line_total` values.

6. **Quote controls:**
   - `quote_basis: "EXW_ONLY"` — no destination means no freight
   - `freight_excluded: true`
   - `offer_validity_days: 30` — per policy POL-QUOTE-VALIDITY
   - `who_documentation_required: true` — for IEHK/emergency health kit products
   - `payment_terms`: `"PREPAY_100"` for new NGO clients

### Critical rule: Module-level quoting

Per policy POL-MODULE-GRANULARITY, quote at the module level only. Do NOT expand into component SKUs even though the API returns `components` arrays on products and the RFQ may include `component_composition_distractors`. The `narrative` field on the RFQ may explicitly say "do not split into component SKUs" — always respect this.

---

## Task Type 3: Opportunity Reconciliation with Event/Voucher

**Trigger:** Prompt mentions an opportunity ID (e.g., `OPP-TR-HELIOS`, `OPP-TR-MERIDIAN`), a customer, a contact name, and asks for reconciliation of milestones, invoices, payments, revenue recognition, and linked events/vouchers.

### Step-by-step procedure

1. **Fetch the opportunity** — `GET /api/opportunities/<opportunity_id>`. Extract:
   - `stage` (normalize: `"closed_won"` → `"WON"`)
   - `won_amount_usd`
   - `customer_id`
   - `contact` name
   - `phases` array (each has `phase_id`, `amount_usd`, `completion_date`, `invoice_id`)

2. **Fetch the customer** — `GET /api/customers/<customer_id>`. Get `name`, verify contact.

3. **Fetch invoices** — `GET /api/invoices`. Filter by `opportunity_id` matching the current opportunity. Each invoice has `id`, `amount_usd`, `status` (`"paid"`, `"unpaid"`, `"draft"`, `"overdue"`), `due_date`, `paid_amount_usd`, `outstanding_amount_usd`, `phase_id`.

4. **Fetch payments** — `GET /api/payments`. Filter by `opportunity_id`. Cross-reference with invoices via `invoice_id`.

5. **Fetch revenue journals** — `GET /api/revenue-journals`. Filter by `opportunity_id`. Each journal has `phase_id`, `invoice_id`, `status`, `debit_account`, `credit_account`, `amount_usd`.

6. **Fetch events** — `GET /api/events`. Filter by `opportunity_id` or `customer_id`. Get `id`, `event_date`, `status`, `voucher_code`, `primary_contact`.

7. **Fetch vouchers** — `GET /api/vouchers`. Filter by `opportunity_id` or match by `event_id`. Get `code`, `discount_percent`, `max_redemptions`, `status`.

### Revenue recognition logic

For each milestone/phase, determine `recognition_status` by cross-referencing invoice payment state with revenue journal existence:

| Invoice Paid? | Revenue Journal Exists? | Recognition Status |
|---------------|------------------------|--------------------|
| Yes | Yes | `RECOGNIZED` |
| Yes | No | `MISSING_REVENUE_JOURNAL` or `REQUIRED_MISSING` |
| No | — | `NOT_REQUIRED_UNPAID` |

**Revenue recognition summary:**
- `recognition_status`: `"COMPLETE_FOR_PAID_MILESTONES"` if every paid milestone has a revenue journal; `"MISSING_FOR_PAID_MILESTONES"` if any paid milestone lacks one
- `recognized_milestones`: array of milestone IDs that are RECOGNIZED
- `missing_required_milestones`: array of milestone IDs that are PAID but MISSING a revenue journal
- `recognized_amount`: sum of amounts for recognized milestones

### Invoice / accounting actions

Identify the primary accounting action:

- If any paid milestone lacks a revenue journal → action is `RECORD_REVENUE_MS2` (or whichever milestone ID is missing), with:
  - `debit_account: "DEFERRED_REVENUE"`
  - `credit_account: "IMPLEMENTATION_SERVICES_REVENUE"`
  - `owner_queue: "ACCOUNTING"`
  - `amount`: the milestone amount
- If all paid milestones are recognized → `VERIFY_REVENUE_ONLY` or `NO_ACCOUNTING_ACTION`

### Collection logic

For unpaid invoices with future `due_date` (relative to the as-of date, typically `2026-06-01`):
- Action: `MONITOR_UNPAID_NOT_DUE`
- Owner: `ACCOUNT_MANAGEMENT`

For unpaid invoices with past `due_date`:
- Action: `COLLECT_UNPAID_MILESTONE` or `SEND_COLLECTION_NOTICE`
- Owner: `COLLECTIONS`

### Event / voucher actions

- If the event is associated with the opportunity and has status `"scheduled"` or `"confirmed"` → action is `SEND_EVENT_INVITATION` or `SEND_BRIEFING_INVITE`
- Voucher values:
  - `discount_amount`: the `discount_percent` value from the voucher (NOT a computed discount; just the percent number itself)
  - `max_uses`: `max_redemptions` from the voucher
  - `voucher_status`: uppercase the status (`"active"` → `"ACTIVE"`)
- Invite task owner: `ACCOUNT_MANAGEMENT`

### Follow-up task construction

Each task object needs:
- `task_type`: `"COLLECTION"` or `"EVENT_INVITATION"`
- `task_title`: Descriptive title mentioning the action and customer name
- `linked_customer_id` / `linked_opportunity_id`: from the opportunity
- `contact_name`: from the opportunity or prompt
- `due_date` for collection: from the invoice `due_date`; for events: typically 21 days before the event date
- `next_action`: controlled vocabulary per template
- Nullable fields (`milestone_id`, `amount_due`, `event_id`, `voucher_code`): fill only what's relevant to the task type

### Key validations

- **Opportunity matches milestones:** `won_amount == sum(phase amounts)` → `true`
- **Outstanding balance:** Sum of all unpaid invoice amounts (or `won_amount - total_paid`)
- **Phase total amount:** Sum of all phase/milestone amounts

---

## Task Type 4: Engagement Reconciliation (Full Accounting View)

**Trigger:** Similar to Task Type 3 but uses a different output template with `engagement_reconciliation`, `invoice_actions`, and `event_actions` top-level keys. Often mentions an "as of" date.

### Additional template-specific rules

The output structure has three major sections:

**`engagement_reconciliation`:**
- `as_of_date`: the current business date (usually `2026-06-01` unless specified)
- `phase_total_amount`: sum of all milestone phase amounts from the opportunity
- `total_paid_amount`: sum of paid amounts across all invoices
- `outstanding_balance`: `won_amount - total_paid_amount`
- `milestones` array: ordered ascending by milestone ID (MS1, MS2, MS3...)
  - `invoice_state`: map invoice status (`"paid"` → `"PAID"`, `"unpaid"` → `"OPEN"`, `"draft"` → `"VOID"`/`"OPEN"`)
  - `payment_state`: map from payment data (`"PAID"` if payment posted, `"UNPAID"` if no payment)
  - `paid_amount`: actual amount paid from the payment record

**`invoice_actions`:**
- `primary_accounting_action`: derived from the most critical accounting need
- `collection_action`: derived from whether any unpaid invoices exist and their due dates
- `accounting_action` nested object with full journal entry details
- `collection_task` nested object with collection follow-up details

**`event_actions`:**
- `invite_action`: `"SEND_BRIEFING_INVITE"` for scheduled/confirmed events
- `invite_task` with action, event_id, voucher_code, owner_queue, contact_name, customer_id

---

## Cross-Cutting Business Rules

### Payment terms by customer segment

| Customer Segment | Payment Profile | Terms Code |
|-----------------|----------------|------------|
| `new_ngo` | `NEW_CLIENT_REVIEW` | `PREPAY_100` |
| `recurring_ngo` | `NET_30_AFTER_PO` | `NET_30_AFTER_PO` |
| `recurring_commercial` | `NET_30_AFTER_PO` | `NET_30_AFTER_PO` |
| `implementation_services` | `MILESTONE_BILLING` | Based on milestone due dates |

### Price tier selection

Products have a `price_tiers` array. Each tier defines a quantity bracket `[min_qty, max_qty]` with `max_qty` possibly `null` (meaning no upper bound). Select the single tier where `min_qty <= quantity <= max_qty`. Derive `unit_price_usd`, `lead_time_days`, and `shelf_life_months` from the matched tier.

### Freight validity staleness

A freight quote is stale when `valid_until < quote_date`. Stale freight:
- Still listed in the freight options array
- Marked with `validity_status: "STALE"`, `source_is_stale: true`
- Should trigger a warning in `freight_warning` / `client_warnings`
- Should NOT be the recommended mode

### Freight distractor detection

The `freight-quotes` collection may include records linked to the quote but that are distractors:
- Wrong CBM / shipment dimensions compared to the actual product × quantity
- Status `"stale"` with `valid_until` far in the past
- Different `destination` or `forwarder` not matching the quote's known lanes
- IDs not matching the expected naming pattern for the quote

Filter by exact `quote_id` match first, then sanity-check the records.

### Risk classification from risk_notes

Do NOT mechanically map `route_risk` to output risk fields. Instead, read the `risk_notes` text:

| risk_notes contains | Output risk |
|--------------------|-------------|
| "customs" or "border" + "high" | `"HIGH"` |
| "border" + "medium" | `"MEDIUM"` + flag `"MEDIUM_BORDER_RISK"` |
| only transit/shelf-life/capacity mentions | `"LOW"`, flag `"NONE"` |

### Revenue recognition account pair

When recording missing revenue:
- **Debit:** `DEFERRED_REVENUE`
- **Credit:** `IMPLEMENTATION_SERVICES_REVENUE`

This pair is consistent across all templates.

### Offer validity

Standard offer validity is 30 calendar days from quote date (policy POL-QUOTE-VALIDITY). Freight validity may expire sooner.

### Controlled value enums

**quote_basis:** `"EXW"`, `"EXW_ONLY"`, `"EXW_PLUS_FREIGHT_OPTIONS"`

**payment_terms:** `"NET_30_AFTER_PO"`, `"PREPAY_100"`

**opportunity_stage / stage:** `"WON"`, `"OPEN"`, `"LOST"`

**payment_status / invoice_state:** `"PAID"`, `"OPEN"`, `"UNPAID"`, `"PARTIAL"`, `"VOID"`, `"UNKNOWN"`

**recognition_status (milestone):** `"RECOGNIZED"`, `"MISSING_REVENUE_JOURNAL"`, `"NOT_REQUIRED_UNPAID"`, `"REQUIRED_MISSING"`

**recognition_status (summary):** `"COMPLETE_FOR_PAID_MILESTONES"`, `"MISSING_FOR_PAID_MILESTONES"`, `"NOT_REQUIRED"`

**risk_level / customs_border_risk:** `"LOW"`, `"MEDIUM"`, `"HIGH"`

**risk_flag:** `"NONE"`, `"MEDIUM_BORDER_RISK"`

**validity_status:** `"VALID"`, `"STALE"`

**task_type:** `"COLLECTION"`, `"EVENT_INVITATION"`

**next_action / action:** `"COLLECT_UNPAID_MILESTONE"`, `"SEND_EVENT_INVITATION"`, `"SEND_BRIEFING_INVITE"`, `"MONITOR_UNPAID_NOT_DUE"`, `"RECORD_REVENUE_MS2"`, `"VERIFY_REVENUE_ONLY"`, `"NO_ACCOUNTING_ACTION"`, `"NO_COLLECTION_ACTION"`

**event_status:** `"SCHEDULED"`, `"ACTIVE"`, `"COMPLETED"`, `"CANCELLED"`, `"UNKNOWN"`

**voucher_status:** `"ACTIVE"`, `"DRAFT"`, `"EXPIRED"`, `"DISABLED"`, `"UNKNOWN"`

**debit_account / credit_account:** `"DEFERRED_REVENUE"`, `"IMPLEMENTATION_SERVICES_REVENUE"`, `"ACCOUNTS_RECEIVABLE"`, `"CASH"`, `"NONE"`

**owner_queue:** `"ACCOUNTING"`, `"ACCOUNT_MANAGEMENT"`, `"COLLECTIONS"`, `"EVENTS"`, `"NONE"`

**quote_type:** `"quote_revision_with_freight"`, `"indicative_module_quote"`

---

## Common Pitfalls

1. **Wrong price tier.** Always match the confirmed quantity to the correct `min_qty`/`max_qty` bracket. The `prior_unit_price_usd` in the quote's line items is the OLD price — the new tier overrides it.

2. **Including distractor freight records.** Not every freight record with a matching `quote_id` belongs. Check `id` naming patterns, `shipment_cbm` consistency, and `status`. The API may include old/stale records from other lanes.

3. **Mapping route_risk directly to risk output.** The `route_risk` field (`"low"`/`"medium"`/`"high"`) is a general indicator. Customs/border risk specifically comes from reading `risk_notes`. A SEA shipment with `route_risk: "medium"` due to transit time should still have `customs_border_risk: "LOW"`.

4. **Splitting modules into components.** RFQ responses for IEHK-style modules must stay at the module level. The API returns `components` arrays as medical review information only — do not expand them into line items unless the prompt explicitly requests component-level pricing.

5. **Missing freight reconfirmation flag.** Per policy POL-FREIGHT-RECONFIRM, every freight-inclusive quote needs `freight_reconfirmation_required: true`. This is not conditional.

6. **Confusing EXW and EXW_ONLY.** `"EXW"` means the quote includes freight options alongside EXW pricing. `"EXW_ONLY"` means freight is excluded entirely (no destination). Don't mix them.

7. **Revenue recognition gaps.** A milestone that is PAID but has no matching revenue journal entry is `MISSING_REVENUE_JOURNAL` — this drives the primary accounting action. An UNPAID milestone is always `NOT_REQUIRED_UNPAID` regardless of journal existence.

8. **Voucher discount_amount confusion.** The `discount_percent` from the voucher API is output as `discount_amount` in the response, but it's the raw percent number (e.g., 50, 100), not a calculated discount value. The field name in the template says `discount_amount` but it carries the percent.

9. **Event due dates.** The due_date for an event invitation task is typically set to 21 days before the event date (e.g., event on 2026-07-22 → due 2026-07-01). Collection task due dates come from the invoice `due_date` or the opportunity phase `completion_date` plus an offset.

10. **Currency and number format.** All USD amounts use exactly two decimal places (`42480.00`, not `42480`). Use `null` for optional date/number fields when no value exists, not empty strings or zero.

---

## Response Format

Return only valid JSON matching the provided `answer_template.json`. No markdown fences, no explanatory text outside the JSON. Use the exact field names, nesting structure, and controlled vocabulary values from the template.

Always resolve entity IDs from API data rather than hardcoding. All monetary fields are numbers (not strings). All dates are ISO 8601 strings. Boolean fields use `true`/`false` (not strings).
