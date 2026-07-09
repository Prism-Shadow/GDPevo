# MedBridge Sales Ops API — Transferable SOP

## Environment

Base URL comes from the runner via `API_BASE_URL`, `BASE_URL`, or the task environment.
The API is read-only (GET only). All responses are JSON. No authentication is required
in the evaluation harness. The API's `/health` endpoint confirms the service name
`"MedBridge Sales Ops"` and returns the seed.

### Endpoint catalog

```
GET /api                           — list all collections and endpoints
GET /api/customers                 — all customers
GET /api/customers/<customer_id>
GET /api/products                  — all products (price tiers, lead times, shelf life, components)
GET /api/products/<product_code>
GET /api/quotes                    — all quotes
GET /api/quotes/<quote_id>
GET /api/rfqs                      — all RFQs (Request for Quote)
GET /api/rfqs/<rfq_id>
GET /api/freight-quotes            — all freight quotes
GET /api/freight-quotes/<freight_id>
GET /api/policies                  — all business policies
GET /api/opportunities             — all CRM opportunities
GET /api/opportunities/<opp_id>
GET /api/invoices                  — all invoices
GET /api/payments                  — all payments
GET /api/revenue-journals          — all revenue recognition journal entries
GET /api/events                    — all client celebration/briefing events
GET /api/vouchers                  — all event voucher codes
GET /api/search?q=<text>           — full-text search across collections (case-insensitive)
```

Single-record GETs return the record object directly (not wrapped in `{collection, records}`).
List GETs return `{collection, count, records: [...]}`.

---

## Workflow 1: Quote + Freight Decision Package (Tasks 001, 004)

This covers requests like: "revised quote Q-TR-XXXX for Y units of PRODUCT on DATE,
need EXW pricing, freight comparison, route risks, recommended mode, payment terms."

### Step 1: Resolve the quote

Fetch `/api/quotes/<quote_id>`. Key fields:

| Field | Meaning |
|---|---|
| `id` | Quote ID (use verbatim in output) |
| `customer_id` | Link to customer record |
| `quote_date` | Business date for the quote |
| `primary_product_code` | The product to price |
| `line_items[].confirmed_quantity` | The **actual** quantity to use (NOT `prior_quote_quantity`) |
| `line_items[].prior_quote_quantity` | Superseded — do NOT use this for pricing |
| `line_items[].prior_unit_price_usd` | Superseded — do NOT use this for pricing |
| `source_notes` | Hints about correct tier, distractor warnings |
| `incoterm` | Usually `"EXW plus freight options"` for freight-comparison quotes |

**Pitfall:** `prior_quote_quantity` and `prior_unit_price_usd` are historical values
from the *previous* version of this quote. The catalog tier **always overrides** the
prior unit price. Use `confirmed_quantity` against the **product catalog** to determine
the current price.

### Step 2: Look up the product and select the correct price tier

Fetch `/api/products/<product_code>`. Each product has `price_tiers[]`:

```json
{
  "min_qty": 300, "max_qty": 499, "unit_price_usd": 118.00,
  "lead_time_days": 28, "lead_time_weeks": 4.0
}
```

**Tier selection rule:** The confirmed quantity must satisfy `min_qty <= qty <= max_qty`.
`max_qty: null` means "no upper bound." Tiers never overlap — exactly one tier matches.

**Also capture from the product:**
- `article_number` — needed for some output templates
- `shelf_life_months` — may be `null` for services
- `cold_chain_required` — drives transport recommendations
- `components[]` — informational only; do NOT split module quotes into components

**EXW total = confirmed_quantity × tier unit_price_usd.** Always use the tier price;
never use the prior quote price.

### Step 3: Look up the customer and derive payment terms

Fetch `/api/customers/<customer_id>`.

**Payment terms logic (check policies + customer profile):**

| Customer segment | Default terms | Policy ID |
|---|---|---|
| `new_ngo` / prospect | `PREPAY_100` | `POL-NEW-CLIENT-PAYMENT` |
| `recurring_ngo` | `NET_30_AFTER_PO` | `POL-RECURRING-NGO-PAYMENT` |
| `recurring_commercial` | From `payment_profile` field | — |
| `implementation_services` | `MILESTONE_BILLING` (from `payment_profile`) | — |

The `payment_profile` field on the customer record is the **authoritative** source.
For new NGO customers (`segment: "new_ngo"`, `status: "prospect"`), the policy
`POL-NEW-CLIENT-PAYMENT` mandates `PREPAY_100`. For recurring NGOs, use `NET_30_AFTER_PO`
unless the `grant_terms` field says otherwise.

**The customer `name` field** in the API record is the canonical name. The prompt
may use a shorthand (e.g., "Health Horizon Aid" → API has "HealthHands Alliance").
Match by `customer_id` from the quote, not by name from the prompt.

### Step 4: Find freight quotes linked to this quote

Fetch `/api/freight-quotes` and filter by `quote_id == <quote_id>`.

**CRITICAL — filter out distractors:**
1. Freight records with `status: "stale"` AND `valid_until` before `quote_date` are **invalid**.
   Flag them as stale/invalid. They should NOT contribute to grand totals if expired.
2. Freight records with `status: "mismatch"` are for wrong shipment sizes — ignore entirely.
3. Distractor freight records (risk_notes like "Wrong shipment size benchmark",
   "Expired sea quote", "Old route benchmark", "Archived destination estimate",
   "Based on 420-kit prior count") — these are NOT the current freight options.
   They are identifiable by:
   - `id` starting with `FR-DIS-` (FR-DIS-WC-*, FR-DIS-LD-*, etc.)
   - risk_notes that say "Wrong", "Expired", "Old", "Archived", "Distractor",
     or reference a prior/obsolete quantity
   - `valid_until` before the quote date

**The legitimate freight options** for a quote have:
- `id` matching the pattern `FR-<product_abbrev>-<mode>` (e.g., FR-WC-AIR, FR-LD-SEA)
- `status: "active"`
- risk_notes that describe the actual route (not calling out wrong data)
- `valid_until` >= quote_date

**For each valid freight option, capture:**
- `id` → freight_id
- `mode` → air / sea / road
- `cost_usd` → freight_cost_usd
- `transit_days_text` → transit_days (use the text version, e.g., "4-6 days")
- `valid_until` → valid_until date
- `route_risk` → risk_level (map: `low` → `LOW`, `medium` → `MEDIUM`, `high` → `HIGH`)
- `risk_notes` → risk_flag (map: medium border risk → `MEDIUM_BORDER_RISK`,
  high customs risk → `HIGH_CUSTOMS_RISK`, low → `NONE`)
- `cold_chain_support` → whether temperature-controlled transport is available

**Grand total = EXW total + freight cost.**

### Step 5: Determine validity and staleness

A freight option is **valid on the quote date** if `valid_until >= quote_date`.
A freight option is **stale** if `status == "stale"` OR `valid_until < quote_date`.

### Step 6: Recommend transport mode

Priority order:
1. **Cold-chain required?** Filter to modes with `cold_chain_support: true`.
2. **Risk:** Prefer lowest `route_risk`. LOW beats MEDIUM beats HIGH.
3. **Validity:** Stale quotes cannot be recommended.
4. **Speed:** Among equal-risk options, prefer faster transit.
5. **Cost:** Among equal-speed options, prefer lower cost.

### Step 7: Policy flags

From `/api/policies`:

| Policy | Meaning |
|---|---|
| `POL-FREIGHT-RECONFIRM` | Freight reconfirmation is always required at final order |
| `POL-QUOTE-VALIDITY` | Catalog pricing valid 30 days from quote date (offer_validity_days: 30) |
| `POL-EXW-SCOPE` | EXW excludes freight, insurance, import duty, customs clearance |
| `POL-RECURRING-NGO-PAYMENT` | Recurring NGOs get NET_30_AFTER_PO |
| `POL-NEW-CLIENT-PAYMENT` | New NGOs require PREPAY_100 |

**`freight_reconfirmation_required`** is ALWAYS `true` per `POL-FREIGHT-RECONFIRM`.
**`quote_basis`** is `"EXW"` for EXW quotes.

---

## Workflow 2: RFQ / Indicative Module Quote (Task 002)

### Key differences from Quote workflow

1. **Start with `/api/rfqs/<rfq_id>`**, not quotes. RFQs have `requested_modules[]` with
   `product_code` and `quantity` for each module.

2. **Module granularity rule** (POL-MODULE-GRANULARITY): Quote at the **module** level.
   Do NOT split modules into their `components[]` from the product catalog. The API may
   list `component_composition_distractors[]` on the RFQ — these are planning notes,
   NOT instructions to itemize.

3. **No destination → EXW only, no freight** (POL-INDICATIVE-EXW): If the RFQ has
   `destination` containing "pending" or no confirmed destination, quote EXW only
   and set `freight_excluded: true`.

4. **Multiple line items:** An RFQ with multiple `requested_modules` produces
   multiple line items in the quote output. Each gets its own `product_code`,
   `article_number`, `quantity`, `unit_price` (single-tier or tier-matched),
   `lead_time_days`, `shelf_life_months`, and `line_total`.

5. **Payment terms for new NGOs:** `PREPAY_100` per `POL-NEW-CLIENT-PAYMENT`.
   The customer record's `payment_profile: "NEW_CLIENT_REVIEW"` maps to `PREPAY_100`.

6. **Offer validity:** 30 calendar days from quote date per `POL-QUOTE-VALIDITY`.

7. **WHO documentation:** For IEHK-style modules (`family: "emergency_health_kit"`),
   set `who_documentation_required: true`.

---

## Workflow 3: Account Reconciliation + Milestone Revenue (Tasks 003, 005)

### Step 1: Resolve the opportunity

Fetch `/api/opportunities/<opportunity_id>`.

Map `stage` to the template enum:
- `closed_won` → `WON`
- `proposal` → `OPEN`
- `negotiation` → `OPEN`

### Step 2: Verify opportunity total against phases

Sum all `phases[].amount_usd`. Compare to `won_amount_usd`.
`opportunity_matches_milestones` (or `opportunity_matches_phase_total`) is `true` iff they match exactly.

### Step 3: Gather invoices, payments, revenue journals

For each phase in the opportunity:
- Match invoice by `phase_id` → `/api/invoices` filtered by `phase_id`
- Match payment by `invoice_id` → `/api/payments`
- Match revenue journal by `phase_id` → `/api/revenue-journals`

### Step 4: Determine milestone state

For each milestone (phase):

**Invoice state:**
- Invoice `status: "paid"` → `PAID`
- Invoice `status: "unpaid"` → `OPEN` (not yet due, or due date in the future)
- Invoice `status: "overdue"` → `OPEN` (due date in the past, still unpaid —
  this MUST trigger `SEND_COLLECTION_NOTICE` in the collection action)
- Invoice `status: "draft"` → `VOID` or `UNKNOWN`

**Payment state:**
- If `paid_amount_usd == amount_usd` → `PAID`
- If `0 < paid_amount_usd < amount_usd` → `PARTIAL`
- If `paid_amount_usd == 0` → `UNPAID`

**Revenue recognition status (critical business rule):**

The trigger for revenue recognition is **payment**, not phase completion.
A completed phase with an unpaid invoice still requires no revenue journal.

The enum values differ by template — always match the template's declared enum:

| Condition | Train 003 template | Train 005 template |
|---|---|---|
| PAID + journal exists | `RECOGNIZED` | `RECOGNIZED` |
| PAID + journal missing | `REQUIRED_MISSING` | `MISSING_REVENUE_JOURNAL` |
| UNPAID (any completion state) | `NOT_REQUIRED_UNPAID` | `NOT_REQUIRED_UNPAID` |
| Draft / no invoice | `NOT_REQUIRED_UNPAID` | `UNKNOWN` |

Even when a phase has a `completion_date` in the records, if the invoice is unpaid,
the recognition status is `NOT_REQUIRED_UNPAID` — only paid milestones need journals.

**The revenue recognition policy** (`POL-REVREC`): "When a milestone is complete and paid,
create or verify revenue recognition from deferred revenue to income; unpaid future
milestones should remain outstanding and drive collection tasks when due or overdue."

### Step 5: Revenue recognition summary

- `COMPLETE_FOR_PAID_MILESTONES` — all PAID milestones have revenue journals
- `MISSING_FOR_PAID_MILESTONES` — at least one PAID milestone lacks a revenue journal
- `recognized_milestones[]` — list of `phase_id` values with posted revenue journals
- `missing_required_milestones[]` — list of `phase_id` values that are PAID but lack revenue journals
- `recognized_amount` — sum of amounts from posted revenue journals

### Step 6: Collection and accounting actions

**Accounting action** (primary): If any PAID milestone is missing a revenue journal:
- Action: `RECORD_REVENUE_MS2` (or MS1/MS3 — match the milestone_id)
- Debit: `DEFERRED_REVENUE`
- Credit: `IMPLEMENTATION_SERVICES_REVENUE`
- Owner: `ACCOUNTING`

If all paid milestones are recognized: `VERIFY_REVENUE_ONLY` or `NO_ACCOUNTING_ACTION`.

**Collection action:**
- Unpaid invoice with `due_date` in the past (relative to business date) → `SEND_COLLECTION_NOTICE`
- Unpaid invoice with `due_date` in the future → `MONITOR_UNPAID_NOT_DUE`
- All paid → `NO_COLLECTION_ACTION`

### Step 7: Events and vouchers

Events link to opportunities via `opportunity_id` and to customers via `customer_id`.

**Event status mapping:**
- `confirmed` → `SCHEDULED` (or keep as-is depending on template enum)
- `scheduled` → `SCHEDULED`
- `live` → `ACTIVE`
- `completed` → `COMPLETED`
- `tentative` → `SCHEDULED` (or `UNKNOWN`)

**Voucher mapping:**
- `status: "active"` → `ACTIVE`
- `discount_percent` → the discount amount/value (the field name varies by template)
- `max_redemptions` → the max uses

**Invite action:** When an event is `scheduled`/`confirmed` and linked to the opportunity:
- Action: `SEND_BRIEFING_INVITE`
- Owner: `ACCOUNT_MANAGEMENT`
- Contact: use the `primary_contact` from the event record

---

### Milestone ID conventions (template-dependent)

Some templates expect **ordinal** milestone IDs (`MS1`, `MS2`, `MS3`), others expect
**raw phase IDs** (`HEL-P1`, `MER-P2`). Check the template enum declaration:

- Template says `"enum: MS1 | MS2 | MS3"` → map phases in order: first phase → `MS1`,
  second → `MS2`, third → `MS3`. Sort phases by their natural order in the array.
- Template says `"string, stable phase or invoice milestone id"` → use the raw `phase_id`
  from the opportunity.

The same mapping applies when `milestone_id` appears in action tasks: use `MS1`/`MS2`/`MS3`
when the template's accounting/collection actions use that enum, or the raw `phase_id`
when the template accepts free-form strings.

### Event status canonicalization

The API event `status` field uses lowercase values. Map to template enums:

| API status | Template enum |
|---|---|
| `scheduled` | `SCHEDULED` |
| `confirmed` | `SCHEDULED` (for templates with `SCHEDULED` enum) |
| `live` | `ACTIVE` |
| `completed` | `COMPLETED` |
| `cancelled` | `CANCELLED` |
| `tentative` | `UNKNOWN` |

### Voucher discount field mapping

The API voucher record stores `discount_percent` (a number, not a dollar amount).
Output templates name this field differently:
- `voucher_discount` (number) — use `discount_percent` verbatim
- `discount_amount` ("number, USD, two decimals") — use `discount_percent` formatted to
  2 decimal places (e.g., `50` → `50.00`). This is a percentage value carried in a
  USD-formatted field; do not multiply by any dollar amount.

---

## Cross-cutting Rules

### Source precedence (always follow this order)

1. **Product catalog** (price_tiers) — overrides any prior quote unit price
2. **Quote `confirmed_quantity`** — overrides `prior_quote_quantity`
3. **Customer `payment_profile`** — the authoritative payment terms source
4. **Policy rules** — apply universally unless a specific customer override exists
5. **Quote `source_notes`** — contains explicit hints about which tier/distractors to use/avoid

### Distractor detection

The API contains deliberate distractor records. Common patterns:

| Distractor type | How to detect |
|---|---|
| Stale/expired freight | `status: "stale"` or `valid_until` before quote date |
| Wrong shipment size | risk_notes mention "Wrong shipment size", different cbm/kg from actual |
| Old tier reference | risk_notes mention prior quantity (e.g., "Based on 420-kit prior count") |
| Superseded RFQ | RFQ `status: "closed_lost"`, `"superseded"`, or `"archived"` |
| Wrong customer | Customer record mismatch (prompt name ≠ API name — trust the API ID link) |
| Component distractors | `component_composition_distractors[]` on RFQs — these are medical review notes, NOT pricing instructions |

### Date handling

- All dates use ISO 8601 format: `YYYY-MM-DD`
- `quote_date` from the quote/RFQ record is the business date
- `valid_until` on freight is the last day the rate is usable (inclusive comparison)
- `as_of_date` for reconciliations is the current business date (typically 2026-06-01
  unless the task says otherwise)

### Currency

All monetary values are in `USD`. Use exactly 2 decimal places (e.g., `42480.00`,
not `42480` or `42480.0`).

### ID conventions

- Quote IDs: `Q-TR-<abbrev>-<number>` or `Q-TE-<abbrev>-<number>` (TR=train, TE=test, DIS=distractor)
- Customer IDs: `CUST-<abbrev>`
- Freight IDs: `FR-<product_abbrev>-<mode>` (active) or `FR-DIS-*` (distractor)
- Invoice IDs: `INV-<customer_abbrev>-P<phase>`
- Payment IDs: `PAY-<customer_abbrev>-P<phase>`
- Revenue journal IDs: `RJ-<customer_abbrev>-P<phase>`
- Event IDs: `EVT-<customer_abbrev>-<type>`
- Voucher codes: short uppercase strings like `HELIOSVIP100`, `MERIDIANBRIEF50`
- Opportunity IDs: `OPP-TR-<abbrev>` or `OPP-TE-<abbrev>` or `OPP-DIS-<abbrev>`

### Risk flag taxonomy

| route_risk | risk_level output | risk_flag output |
|---|---|---|
| `low` | `LOW` | `NONE` |
| `medium` (border-related) | `MEDIUM` | `MEDIUM_BORDER_RISK` |
| `medium` (general) | `MEDIUM` | depends on risk_notes text |
| `high` (customs) | `HIGH` | `HIGH_CUSTOMS_RISK` |
| `high` (general) | `HIGH` | depends on risk_notes text |

### Payment terms lookup table

| Customer payment_profile | Output payment_terms |
|---|---|
| `NET_30_AFTER_PO` | `NET_30_AFTER_PO` |
| `NET_45_APPROVED` | `NET_45_APPROVED` |
| `NEW_CLIENT_REVIEW` | `PREPAY_100` |
| `MILESTONE_BILLING` | `MILESTONE_BILLING` |
| `PREPAY_50_BALANCE_BEFORE_SHIP` | `PREPAY_50_BALANCE_BEFORE_SHIP` |

### Edge cases and gotchas

1. **Stale freight still gets listed.** Even if a freight option is stale/invalid
   (e.g., FR-LD-ROAD with `valid_until: "2026-05-25"` against a `2026-06-01` quote date),
   include it in the freight_options array with `source_is_stale: true` and
   `validity_status: "STALE"`. Set `road_quote_invalid_or_stale: true` in client_warnings.
   The stale option's grand_total should still be computed (EXW + stale freight cost)
   since the template expects it — but it cannot be the recommended mode.

2. **Customer name mismatch.** The prompt may use a colloquial name that differs from
   the API customer `name` field. Always use the API customer `name` in output.
   The `customer_id` link from the quote/RFQ/opportunity is the authoritative link.

3. **RFQ template array expansion.** When a template shows `line_items: [{...}]` with
   a single sample element but the RFQ has 5 requested modules, expand to 5 elements.
   The single entry is structural, not a limit.

4. **Future completion dates.** A phase with `completion_date` after the business date
   (e.g., MER-P3 completes 2026-06-25, business date 2026-06-01) is not yet complete.
   But revenue recognition depends on **payment**, not completion — if the invoice
   exists and is unpaid, status is `NOT_REQUIRED_UNPAID` regardless.

5. **Due date vs. business date for collections.** An invoice due 2026-06-27 with
   business date 2026-06-01 is NOT overdue — use `MONITOR_UNPAID_NOT_DUE`.
   An invoice due 2026-05-20 (status: "overdue") IS overdue and must trigger
   `SEND_COLLECTION_NOTICE`.

6. **Null shelf_life_months.** Services (e.g., `CC-LOG-SVC`) have `shelf_life_months: null`.
   Pass `null` through to the output; do not default to 0.

7. **Distractor freight with quote_id match.** Some distractor freight records share
   the same `quote_id` as legitimate options (e.g., FR-DIS-WC-OLD-AIR has
   `quote_id: "Q-TR-WC-1187"`). Filtering by `quote_id` alone is insufficient —
   you MUST also check `status` and risk_notes for distractor signals.

8. **Payment amount precision.** Use `paid_amount_usd` and `outstanding_amount_usd`
   from the invoice record directly. Do not recalculate from opportunity phases —
   the invoice is the system of record for payment state.

### Template adaptation notes

- When a template shows an array with one example element, expand to include all
  actual records (e.g., multiple line items for multi-module RFQs, multiple freight options).
- Template enum values are case-sensitive and must match exactly.
- String fields use the exact API record values (IDs, names, codes) — do not paraphrase.
- Boolean fields: use JSON `true`/`false`, never strings.
- `null` is used for fields that genuinely have no value (e.g., `due_date: null` for
  milestones not yet invoiced, `milestone_id: null` for event-only tasks).

---

## Quick-start recipe per task pattern

### Pattern A: Quote + Freight (Tasks 001, 004)
1. GET `/api/quotes/<quote_id>` → extract customer_id, product_code, confirmed_quantity, source_notes
2. GET `/api/products/<product_code>` → match price tier by quantity → unit_price, lead_time, shelf_life
3. GET `/api/customers/<customer_id>` → payment_profile → payment_terms
4. GET `/api/freight-quotes` → filter by quote_id, exclude distractors (FR-DIS-*, stale, mismatch)
5. Compute EXW total, grand totals, validity, risks, recommended mode
6. Apply POL-FREIGHT-RECONFIRM (always true), POL-QUOTE-VALIDITY (30 days)

### Pattern B: RFQ Module Quote (Task 002)
1. GET `/api/rfqs/<rfq_id>` → extract customer_id, requested_modules[], destination
2. GET `/api/customers/<customer_id>` → new NGO → PREPAY_100
3. For each requested module: GET `/api/products/<product_code>` → unit_price (first tier), lead_time, shelf_life, article_number
4. Sum line totals → grand_total
5. Set freight_excluded=true, who_documentation_required=true (IEHK modules)
6. Set offer_validity_days=30 per POL-QUOTE-VALIDITY

### Pattern C: Account Reconciliation (Tasks 003, 005)
1. GET `/api/opportunities/<opp_id>` → phases[], won_amount, stage, contact
2. For each phase: find invoice by phase_id, payment by invoice_id, revenue journal by phase_id
3. Compute paid/unpaid/revenue-recognition state per milestone
4. GET `/api/events` → filter by opportunity_id → event status, voucher
5. GET `/api/vouchers` → filter by voucher_code → discount, max_uses, status
6. Determine accounting action (revenue journal missing → RECORD_REVENUE_MSx)
7. Determine collection action (unpaid + past due → SEND_COLLECTION_NOTICE; unpaid + future due → MONITOR_UNPAID_NOT_DUE)
8. Determine invite action (event scheduled → SEND_BRIEFING_INVITE)
