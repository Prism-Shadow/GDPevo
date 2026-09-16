---
name: medbridge-sales-ops
description: Solve MedBridge Sales Ops API tasks for quote decision packages, indicative RFQ module quotes, and opportunity engagement reconciliations.
---

Use this skill when the task asks you to verify, reconcile, or build a decision
package from the MedBridge Sales Ops API. The skill covers three workflows:
quote revision with freight, indicative module quotes from RFQs, and
opportunity engagement reconciliation with accounting follow-ups.

## Setup

The runner provides a task environment base URL. Read it from the prompt
(referenced as `<TASK_ENV_BASE_URL>`, `BASE_URL`, or similar placeholder) and
use it for every API call. Example:

```bash
BASE_URL="http://task-env:9002"
```

All endpoints are read-only GET. No credentials required. Verify the service is
healthy before starting:

```bash
curl -s "$BASE_URL/health"
```

## API Reference

See [reference/api.md](reference/api.md) for the full endpoint listing and
field reference. The critical collections are:

- `/api/customers` and `/api/customers/<id>` — customer records, segments, payment profiles
- `/api/products` and `/api/products/<code>` — product catalog with price tiers
- `/api/quotes` and `/api/quotes/<id>` — quote headers, line items, confirmed quantities
- `/api/rfqs` and `/api/rfqs/<id>` — RFQ headers, requested modules with quantities
- `/api/freight-quotes` and `/api/freight-quotes/<id>` — freight costs, validity, risk
- `/api/policies` — business rules governing payment terms, freight, quotes, revenue
- `/api/opportunities` and `/api/opportunities/<id>` — won opportunities, phases
- `/api/invoices` — milestone invoices with status (paid, unpaid, overdue, draft)
- `/api/payments` — posted payments linked to invoices
- `/api/revenue-journals` — posted revenue recognition entries
- `/api/events` — scheduled events tied to opportunities
- `/api/vouchers` and `/api/vouchers/<code>` — discount vouchers for events
- `/api/search?q=<text>` — full-text search across all collections

## Workflow selection

Read the prompt to decide which workflow applies:

1. **Quote Decision Package** — the prompt names a quote ID starting with
   `Q-TR-`, a customer ID, a product code, and a confirmed quantity. Usually
   describes a "revision" or "revised quote" and asks for EXW pricing plus
   freight comparison. Follow [Workflow A](#workflow-a-quote-decision-package).

2. **Indicative RFQ Module Quote** — the prompt names an RFQ ID starting with
   `RFQ-TR-`, a customer, and says to quote at "module level" or EXW only
   without freight. Follow [Workflow B](#workflow-b-indicative-rfq-module-quote).

3. **Engagement Reconciliation** — the prompt names an opportunity ID starting
   with `OPP-TR-`, a customer ID, a contact name, and asks to reconcile
   milestones, invoices, payments, revenue recognition, and events. Follow
   [Workflow C](#workflow-c-engagement-reconciliation).

Always match the output schema exactly to the `answer_template.json` provided
in the task payloads directory.

---

## Workflow A — Quote Decision Package

Use when the task provides a quote ID (e.g. `Q-TR-...`), a confirmed quantity,
and asks for EXW pricing plus freight comparison.

### Step A1 — Gather source records

Fetch in parallel:

```bash
curl -s "$BASE_URL/api/quotes/<quote_id>"
curl -s "$BASE_URL/api/customers/<customer_id>"
curl -s "$BASE_URL/api/products/<product_code>"
curl -s "$BASE_URL/api/freight-quotes"   # then filter by quote_id
curl -s "$BASE_URL/api/policies"
```

### Step A2 — Select the catalog price tier

Each product has a `price_tiers` array. Each tier has `min_qty`, `max_qty`
(`null` means no upper bound), `unit_price_usd`, `lead_time_days`, and
`shelf_life_months`. Find the tier where:

```
tier.min_qty <= confirmed_quantity AND (tier.max_qty is null OR confirmed_quantity <= tier.max_qty)
```

If `confirmed_quantity` straddles multiple tiers, use the highest applicable
tier (largest min_qty). The quote record's `source_notes` often confirms the
tier to use; cross-check it.

### Step A3 — Compute EXW values

```
unit_price_usd    = matched tier's unit_price_usd
exw_total_usd     = unit_price_usd * confirmed_quantity
lead_time_days    = matched tier's lead_time_days
shelf_life_months = product's shelf_life_months
```

### Step A4 — Filter freight quotes

From the `GET /api/freight-quotes` listing, select records where:

1. `quote_id` matches the target quote ID
2. `status` is `active` (reject `stale`, `mismatch`, or expired records)
3. The freight quote's `shipment_cbm` and `shipment_weight_kg` plausibly match
   the product's `cbm` × confirmed_quantity and `weight_kg` × confirmed_quantity

Watch for distractor freight records with the same `quote_id` but wrong
dimensions or status.

### Step A5 — Classify each freight option

For each active freight option, compute:

- **valid_until**: from the freight record. A quote is valid on the quote date
  if `valid_until >= quote_date`.
- **validity_status**: `VALID` if `valid_until >= quote_date`, otherwise
  `STALE`.
- **source_is_stale**: `true` if `valid_until < quote_date`.
- **risk_level**: map the freight record's `route_risk` field:
  - `low` → `LOW`
  - `medium` → `MEDIUM`
  - `high` → `HIGH`
- **risk_flag**: derive from `route_risk` and `risk_notes`:
  - `low` → `NONE` or `LOW`
  - `medium` → `MEDIUM_BORDER_RISK` or similar
  - `high` → `HIGH` or specific customs/border risk text
- **customs_border_risk**: same as `risk_level` mapping
- **grand_total_usd**: `exw_total_usd + freight_cost_usd`

### Step A6 — Select the recommended mode

Priority order:
1. Reject any freight option that is stale or has `route_risk: "high"`.
2. Among remaining active options, prefer the lowest-risk mode.
3. If risk is equal, prefer SEA (cost-efficient) unless the prompt demands
   speed (e.g. cold chain with shelf-life urgency, grant delivery deadlines).
4. If SEA transit threatens shelf-life or delivery deadlines, recommend AIR.

### Step A7 — Policy checks

Look up these policies by scanning the policies collection:

- **payment_terms**: match customer's `segment` to policy `terms_code`:
  - `new_ngo` → `PREPAY_100`
  - `recurring_ngo` → `NET_30_AFTER_PO`
  - `recurring_commercial` → `NET_30_AFTER_PO`
  - `implementation_services` → `MILESTONE_BILLING`
  - `government_program` → `NET_30_AFTER_PO`
  - `distributor` → `NET_45_APPROVED`
  - `regional_hospital` → `PREPAY_50_BALANCE_BEFORE_SHIP`

- **freight_reconfirmation_required**: always `true` per `POL-FREIGHT-RECONFIRM`.
- **all_freight_options_valid_on_quote_date**: `true` if every active freight
  option's `valid_until >= quote_date`.
- **customer_policy**: the customer's `segment` field.
- **quote_basis**: `EXW` or `EXW_PLUS_FREIGHT_OPTIONS` (reflects incoterm from
  quote record).

### Step A8 — Client warnings

When building the output schema variant that includes `client_warnings`:

- **road_quote_invalid_or_stale**: `true` if any ROAD freight is stale or has
  `route_risk: "high"`.
- **freight_warning**: human-readable summary of stale/risky freight records
  with dates and specific risk concerns. Include the expired freight ID and its
  `valid_until` date.
- **policy_terms**: mirror the policy flags block with `quote_basis`,
  `payment_terms`, and `freight_reconfirmation_required`.

---

## Workflow B — Indicative RFQ Module Quote

Use when the task provides an RFQ ID (e.g. `RFQ-TR-...`) and says to quote at
module level, EXW only, without freight.

### Step B1 — Gather source records

```bash
curl -s "$BASE_URL/api/rfqs/<rfq_id>"
curl -s "$BASE_URL/api/customers/<customer_id>"
curl -s "$BASE_URL/api/policies"
```

### Step B2 — Quote at module level only

The RFQ's `requested_modules` array lists `product_code` and `quantity` per
module. Do **not** descend into a product's `components` field even when the
RFQ has `component_composition_distractors`. Fetch each module's product
record:

```bash
curl -s "$BASE_URL/api/products/<product_code>"
```

The policy `POL-MODULE-GRANULARITY` confirms: module RFQs stay at module line
level.

### Step B3 — Build line items

For each requested module, look up the product. Each module product has a
single price tier (min_qty: 1, max_qty: null). Compute:

```
unit_price        = product.price_tiers[0].unit_price_usd
line_total        = unit_price * requested_quantity
lead_time_days    = product.price_tiers[0].lead_time_days
shelf_life_months = product.shelf_life_months
article_number    = product.article_number
```

### Step B4 — Quote controls

- **grand_total**: sum of all `line_total` values.
- **freight_excluded**: `true`. Per `POL-INDICATIVE-EXW`, no destination means
  no freight quote.
- **payment_terms**: `PREPAY_100` for new clients (`new_ngo` segment).
- **offer_validity_days**: `30` per `POL-QUOTE-VALIDITY`.
- **who_documentation_required**: `true` when the customer type is NGO.

---

## Workflow C — Engagement Reconciliation

Use when the task provides an opportunity ID (e.g. `OPP-TR-...`), a customer,
a contact, and asks to reconcile milestones, payments, revenue recognition,
and events.

### Step C1 — Gather all source records

```bash
curl -s "$BASE_URL/api/opportunities/<opportunity_id>"
curl -s "$BASE_URL/api/customers/<customer_id>"
curl -s "$BASE_URL/api/invoices"
curl -s "$BASE_URL/api/payments"
curl -s "$BASE_URL/api/revenue-journals"
curl -s "$BASE_URL/api/events"
curl -s "$BASE_URL/api/vouchers/<voucher_code>"   # if voucher named in prompt
```

Filter invoices, payments, and revenue journals to those matching the target
`opportunity_id`. The listing endpoints return all records; filter
client-side.

### Step C2 — Build the engagement summary

- **stage**: map opportunity `stage` to the template enum:
  - `closed_won` → `WON`
  - `proposal` or `negotiation` → `OPEN`
- **won_amount** / **phase_total_amount**: sum the opportunity `phases`
  `amount_usd` values.
- **opportunity_matches_phase_total**: `won_amount_usd == sum(phases amounts)`.
- **total_paid_amount**: sum of all payment `amount_usd` for this opportunity.
- **outstanding_balance**: `won_amount_usd - total_paid_amount`.
- **primary_contact**: from customer's `contacts` matching the named contact,
  or the opportunity's `contact` field.

### Step C3 — Build milestone rows

For each phase in the opportunity, cross-reference its `invoice_id` with the
invoices collection and its payment/revenue-journal records. For each phase,
ordered by `phase_id` ascending (MS1, MS2, MS3):

- **milestone_id**: `MS1`, `MS2`, `MS3` (derived from phase ordinal, not the
  raw phase_id).
- **amount**: the phase `amount_usd`.
- **invoice_state**: from the invoice's `status` field:
  - `paid` → `PAID`
  - `unpaid` → `OPEN` (or `UNPAID` depending on template enum)
  - `overdue` → `OPEN` with overdue flag visible in payment_state
  - `draft` → `OPEN`
- **payment_state**: derive from invoice status and payment records:
  - If invoice `paid_amount_usd == invoice amount_usd` → `PAID`
  - If invoice `paid_amount_usd > 0` but less than total → `PARTIAL`
  - If invoice `paid_amount_usd == 0` and status is `overdue` → `UNPAID`
  - If invoice `paid_amount_usd == 0` and status is `unpaid` → `UNPAID`
- **paid_amount**: `invoice.paid_amount_usd` (0 if no payments).
- **due_date**: `invoice.due_date` (null if paid and due date passed).
- **recognition_status**: cross-reference revenue journals by `phase_id`:
  - If a posted revenue journal exists for this phase → `RECOGNIZED`
  - If the invoice is paid but no revenue journal exists → `MISSING_REVENUE_JOURNAL`
  - If the invoice is unpaid → `NOT_REQUIRED_UNPAID`

### Step C4 — Revenue recognition summary

- **recognition_status**: `COMPLETE_FOR_PAID_MILESTONES` if all paid phases
  have revenue journals, `MISSING_FOR_PAID_MILESTONES` otherwise.
- **recognized_milestones**: list of milestone IDs with posted revenue
  journals.
- **missing_required_milestones**: list of paid milestone IDs without revenue
  journals.
- **recognized_amount**: sum of `amount_usd` from revenue journals for this
  opportunity.

### Step C5 — Accounting action (revenue recognition)

If any paid, completed milestone lacks a revenue journal:

- **action**: `RECORD_REVENUE_MS2` (or phase-specific).
- **milestone_id**: the missing milestone.
- **amount**: the phase `amount_usd`.
- **debit_account**: `DEFERRED_REVENUE`.
- **credit_account**: `IMPLEMENTATION_SERVICES_REVENUE`.
- **owner_queue**: `ACCOUNTING`.

The standard journal entry: Debit Deferred Revenue, Credit Implementation
Services Revenue, for the milestone amount. This follows `POL-REVREC`.

If all paid milestones are recognized, the accounting action is
`VERIFY_REVENUE_ONLY` or `NO_ACCOUNTING_ACTION` depending on template.

### Step C6 — Collection action

For unpaid milestones:

- If the invoice `due_date` is in the future relative to the business date
  (2026-06-01): `MONITOR_UNPAID_NOT_DUE`. Queue: `ACCOUNT_MANAGEMENT`.
- If the invoice `due_date` is in the past: `SEND_COLLECTION_NOTICE`. Queue:
  `COLLECTIONS`.
- If no unpaid milestones: `NO_COLLECTION_ACTION`.

### Step C7 — Event and invitation

Look up the event by ID from the prompt. Check its `status`:
- `scheduled` → `SCHEDULED`
- `confirmed` → `SCHEDULED` (or `ACTIVE` depending on template)
- `live` → `ACTIVE`
- `completed` → `COMPLETED`
- `tentative` → `SCHEDULED`

Look up the voucher by code. Map fields:
- `discount_amount`: voucher's `discount_percent` (the percent value itself,
  not a computed amount).
- `max_uses`: voucher's `max_redemptions`.
- `voucher_status`: voucher's `status` field (`active` → `ACTIVE`, etc.)

Decide the invite action:
- If event is `scheduled` or `confirmed` and voucher is `active`:
  `SEND_BRIEFING_INVITE` (or `SEND_EVENT_INVITATION`).
- If event is already live or completed: `NO_INVITE_ACTION`.

### Step C8 — Build follow-up tasks

The tasks array contains one entry per required action:

1. **Collection task** (when applicable): includes milestone ID, amount due,
   contact name, due date (the invoice due date), and `COLLECT_UNPAID_MILESTONE`
   action. The `task_title` describes the customer and phase.

2. **Event invitation task** (when applicable): includes event ID, voucher
   code, contact name, customer ID, and `SEND_EVENT_INVITATION` action. The
   `task_title` describes the event.

---

## General rules

### Price tier matching

Products with multiple price tiers use quantity-based brackets. Always match
`confirmed_quantity` to the tier whose `min_qty <= quantity` and
`(max_qty is null or quantity <= max_qty)`. Never use a prior quote's tier if
the confirmed quantity now lands in a different bracket.

### Freight filtering

- **Active vs stale**: freight status `active` and `valid_until >= quote_date`
  is valid. Status `stale` or `valid_until < quote_date` is stale.
- **Distractor detection**: freight records with the right `quote_id` but wrong
  `shipment_cbm`/`shipment_weight_kg` (not matching product dimensions × qty)
  are distractors. Also discard records with `forwarder` names that don't match
  the expected trio per mode.
- **Mismatch status**: some freight records carry `status: "mismatch"` and
  reference prior quote quantities. Skip these.

### Policy application

Always check the policies collection. Key policies:

| Policy ID | Rule summary |
|---|---|
| `POL-NEW-CLIENT-PAYMENT` | New NGOs prepay 100% |
| `POL-RECURRING-NGO-PAYMENT` | Recurring NGOs get NET_30_AFTER_PO |
| `POL-INDICATIVE-EXW` | No destination = EXW only, no freight |
| `POL-FREIGHT-RECONFIRM` | Freight reconfirmation required at order |
| `POL-MODULE-GRANULARITY` | Module RFQs stay at module line level |
| `POL-REVREC` | Recognize revenue for paid, completed milestones |
| `POL-QUOTE-VALIDITY` | Catalog quotes valid 30 days |
| `POL-EXW-SCOPE` | EXW excludes freight, insurance, duties |

### Currency and number formatting

All monetary values in USD. Use two decimal places (e.g. `10000.00`). No
currency symbols in JSON values.

### Dates

Always ISO 8601 `YYYY-MM-DD`. The default business date when none is given is
`2026-06-01`.

### Template matching

Every task includes an `answer_template.json` in the payloads directory. Read
it first, then produce JSON that exactly matches its structure, keys, and enum
values. Do not add extra keys or omit required ones.

### Record ID stability

Use the stable IDs from API records verbatim: `quote_id`, `customer_id`,
`product_code`, `freight_id`, `rfq_id`, `opportunity_id`, `milestone_id`,
`event_id`, `voucher_code`. Do not synthesize or abbreviate them.
