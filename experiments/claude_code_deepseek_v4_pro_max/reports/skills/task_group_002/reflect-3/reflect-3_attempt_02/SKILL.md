# MedBridge Sales Ops — Quote & Engagement Reconciliation

## Overview

The MedBridge Sales Ops API serves shared CRM, product-catalog, quoting, freight,
invoice, payment, revenue-recognition, event, and voucher data. Use it to build
quote decision packages and account-ready reconciliations from a single source of
truth. Every response field that names an ID, code, date, amount, or controlled
status must come from API records — never invent identifiers or infer statuses
from task narrative alone.

---

## API conventions

### Base URL

The task runner provides the base URL. All endpoints are read-only `GET` under
`/api/`.

### Collections

| Endpoint | Key entity |
|---|---|
| `/api/customers[/<id>]` | Customer record |
| `/api/products[/<code>]` | Product with price tiers |
| `/api/quotes[/<id>]` | Quote header and line items |
| `/api/rfqs[/<id>]` | RFQ header and requested modules |
| `/api/freight-quotes` | All freight records (filter by `quote_id`) |
| `/api/policies` | Business rules |
| `/api/opportunities[/<id>]` | CRM opportunity with phases |
| `/api/invoices` | Invoices (filter by `opportunity_id` or `customer_id`) |
| `/api/payments` | Payment records |
| `/api/revenue-journals` | Revenue recognition journal entries |
| `/api/events` | Client events |
| `/api/vouchers` | Event voucher/discount codes |
| `/api/search?q=<text>` | Full-text search across all collections |

---

## Quote workflows

### 1. Resolve the customer

Fetch the customer by the `customer_id` embedded in the quote or RFQ record.

**Payment terms** are decided by the customer's `payment_profile` and the
applicable policy — see [Payment terms](#payment-terms) below.

### 2. Select the product and price tier

Fetch the product by `product_code`. Each product has a `price_tiers` array.
Pick the tier where `confirmed_quantity` falls in `[min_qty, max_qty]`. When
`max_qty` is `null`, the tier is unbounded above.

**Tier fields to capture:**
- `unit_price_usd` — always from the matched tier, NOT from a prior quote's
  `prior_unit_price_usd` (the quote's `source_notes` or catalog tier overrides
  any prior price)
- `lead_time_days` — from the matched tier
- `shelf_life_months` — product-level field, not tier-specific

**EXW total:** `confirmed_quantity × unit_price_usd` (no rounding tricks; keep
two decimals).

### 3. Freight options

The `/api/freight-quotes` endpoint returns **all** freight records across all
quotes. Filter by `quote_id` to get only records for the current quote, then
select the three mode records (air, sea, road).

**How to identify the correct three records:**
- Match on `quote_id` for the current quote
- The correct records typically have IDs following the pattern `FR-<prefix>-<MODE>`
  (e.g. `FR-WC-AIR`, `FR-WC-SEA`, `FR-WC-ROAD`)
- Distractor records share the same `quote_id` but have any of:
  - `status: "stale"` with `valid_until` before the quote date AND wrong
    shipment dimensions
  - Wrong `shipment_cbm` or `shipment_weight_kg` that doesn't match the quote's
    scale
  - Different destination or forwarder that is clearly a benchmark/test record
  - IDs with `DIS` or `OLD` markers

**Freight option fields from the API:**
| Output field | API source | Notes |
|---|---|---|
| `freight_id` | `id` | As-is |
| `mode` | `mode` | Uppercase: `air`→`AIR`, `sea`→`SEA`, `road`→`ROAD` |
| `freight_cost_usd` | `cost_usd` | As-is |
| `transit_days` | `transit_days_text` | The pre-formatted string, e.g. `"4-6 days"` |
| `valid_until` | `valid_until` | ISO date as-is |
| `risk_level` | `route_risk` | Uppercase: `low`→`LOW`, `medium`→`MEDIUM`, `high`→`HIGH` |
| `risk_flag` / `customs_border_risk` | `route_risk` | Uppercase; use `NONE` for low-risk routes; for medium road risk use the appropriate flag |
| `grand_total_usd` | Calculated | `exw_total_usd + freight_cost_usd` |

**Validity checks:**
- A freight quote is **stale** when `valid_until < quote_date` or when
  `status` is `"stale"` in the API.
- `source_is_stale: true` when the record's `valid_until` falls before the
  quote date.
- `all_freight_options_valid_on_quote_date: true` only when every freight
  option's `valid_until >= quote_date` AND none have `status: "stale"`.

### 4. Recommended transport mode

Pick the lowest-risk, viable mode. Decision priority:
1. Eliminate any stale/invalid option.
2. Among remaining, prefer the lowest `route_risk`.
3. When risk is equal, prefer lower cost.
4. For **cold-chain products** (`cold_chain_required: true`): shorter transit
   matters; the faster low-risk mode may be preferred even when more expensive.
   Balance cost against shelf-life headroom.

### 5. Policy flags

Fetch `/api/policies` and apply the relevant policies:

| Policy ID | When it applies | Effect |
|---|---|---|
| `POL-FREIGHT-RECONFIRM` | All freight quotes | `freight_reconfirmation_required: true` |
| `POL-QUOTE-VALIDITY` | All catalog quotes | `offer_validity_days: 30` |
| `POL-INDICATIVE-EXW` | Quotes without confirmed destination | `quote_basis: "EXW_ONLY"`, `freight_excluded: true` |
| `POL-MODULE-GRANULARITY` | Module RFQs | Quote at module level; do NOT split into components |
| `POL-NEW-CLIENT-PAYMENT` | New NGO / prospect clients | Payment terms = `PREPAY_100` |
| `POL-RECURRING-NGO-PAYMENT` | Recurring NGO customers | Payment terms = `NET_30_AFTER_PO` |

### 6. Payment terms

Derive from the **customer record** combined with **policy rules**:

| Customer segment | `payment_profile` | Payment terms |
|---|---|---|
| `new_ngo` / prospect | `NEW_CLIENT_REVIEW` | `PREPAY_100` |
| `recurring_ngo` | `NET_30_AFTER_PO` | `NET_30_AFTER_PO` |
| `recurring_commercial` | `NET_30_AFTER_PO` | `NET_30_AFTER_PO` |
| `implementation_services` | `MILESTONE_BILLING` | Depends on milestone context — use the invoice/payment state |

**Important:** When the task prompt names a customer differently from the API's
`name` field (e.g. the prompt says "GreenHarvest Labs" but the API says "Global
Health Laboratories"), use the **API `name`** as the authoritative value. The
prompt narrative is for orientation; the API is the system of record.

---

## Module RFQ workflow (EXW only, no freight)

When the request type is `indicative_module_quote` or the RFQ explicitly states
no destination:
1. Quote each requested module as a separate line item.
2. Use the **module** product code and article number — do NOT descend into
   `components` arrays. The policy `POL-MODULE-GRANULARITY` forbids
   component-level splits unless the customer requests them.
3. `quote_basis: "EXW_ONLY"`, `freight_excluded: true`.
4. Payment terms follow the customer's segment (see table above).
5. `offer_validity_days: 30` (POL-QUOTE-VALIDITY).

---

## Opportunity & engagement reconciliation

### 1. Opportunity header

- Map stage values: `closed_won` → `WON`, `open` → `OPEN`, `closed_lost` → `LOST`.
- `won_amount` = `won_amount_usd` from the opportunity.
- `phase_total_amount` = sum of all phase `amount_usd` values.
- `opportunity_matches_phase_total` = `won_amount == phase_total_amount`.
- `outstanding_balance` = sum of `outstanding_amount_usd` across invoices, OR
  the opportunity's `outstanding_amount_usd` field (they should agree).
- `total_paid_amount` = sum of `paid_amount_usd` across all invoices.

### 2. Milestone naming

Use canonical milestone identifiers from the invoice or phase data. When the
template expects `MS1`/`MS2`/`MS3`-style sequential IDs, order phases by
their natural sequence (phase number or completion date) and assign `MS1` for
phase 1, `MS2` for phase 2, `MS3` for phase 3.

When the template uses phase IDs directly (e.g. `HEL-P1`), use the
`phase_id` from the opportunity's phase array.

**When in doubt about the ID format**, check the template's enum constraint.
If the template declares `"enum: MS1 | MS2 | MS3"`, use that sequential
format regardless of what the API calls the phases.

### 3. Invoice state mapping

| API `status` | Output `invoice_state` |
|---|---|
| `paid` | `PAID` |
| `unpaid` | `OPEN` |
| `void` | `VOID` |

### 4. Payment state mapping

Derive from `paid_amount_usd` vs `amount_usd` on the invoice:
- Fully paid (`paid_amount == amount`): `PAID`
- Partially paid (`0 < paid_amount < amount`): `PARTIAL`
- No payment (`paid_amount == 0`): `UNPAID`

### 5. Revenue recognition status (per milestone)

Look up the `/api/revenue-journals` collection and match on `invoice_id` or
`phase_id`. A **posted** revenue journal entry means the milestone is recognized.

| Condition | `recognition_status` |
|---|---|
| Invoice paid AND revenue journal posted | `RECOGNIZED` |
| Invoice paid BUT no revenue journal | `MISSING_REVENUE_JOURNAL` |
| Invoice unpaid | `NOT_REQUIRED_UNPAID` |

### 6. Overall revenue recognition summary

- `COMPLETE_FOR_PAID_MILESTONES` — every paid milestone has a revenue journal.
- `MISSING_FOR_PAID_MILESTONES` — at least one paid milestone lacks a journal.
- `recognized_milestones` — list of milestone IDs with journals.
- `missing_required_milestones` — list of paid milestone IDs without journals.
- `recognized_amount` — sum of amounts for recognized milestones only.

### 7. Accounting actions

When a paid milestone is missing its revenue journal (`MISSING_REVENUE_JOURNAL`):
- **Primary action:** `RECORD_REVENUE_MS<N>` (where N is the phase number).
- **Debit:** `DEFERRED_REVENUE`
- **Credit:** `IMPLEMENTATION_SERVICES_REVENUE`
- **Owner queue:** `ACCOUNTING`

When all paid milestones are recognized, use `VERIFY_REVENUE_ONLY`.

### 8. Collection actions

Check unpaid invoice due dates against the current business date:

| Condition | Action |
|---|---|
| Unpaid AND `due_date < current_date` (overdue) | `SEND_COLLECTION_NOTICE` |
| Unpaid AND `due_date >= current_date` (future) | `MONITOR_UNPAID_NOT_DUE` |
| Nothing unpaid or due | `NO_COLLECTION_ACTION` |

Collection task owner: `ACCOUNT_MANAGEMENT`.

### 9. Events and vouchers

- **Event status mapping:** `scheduled` → `SCHEDULED`, `confirmed` →
  `SCHEDULED`, `active` → `ACTIVE`, `completed` → `COMPLETED`, `cancelled` →
  `CANCELLED`.
- **Voucher status mapping:** `active` → `ACTIVE`, `draft` → `DRAFT`,
  `expired` → `EXPIRED`, `disabled` → `DISABLED`.
- `discount_amount` (USD) = `discount_percent` from the voucher record
  (used directly as the numeric value).
- `max_uses` = `max_redemptions` from the voucher record.
- **Invite action:** `SEND_BRIEFING_INVITE` when the event is scheduled and
  hasn't passed; use `VERIFY_INVITE_SENT` when invitation was already sent;
  `NO_INVITE_ACTION` for past or cancelled events.
- Invite task owner: `ACCOUNT_MANAGEMENT` (matches the event's
  `follow_up_owner` field).

### 10. Follow-up task routing

Every follow-up task must include:
- `linked_customer_id` and `linked_opportunity_id` from the parent records
- `contact_name` from the opportunity's `contact` field or the customer's
  primary contact
- `owner_queue` matching the responsible department

Two standard follow-up types:
1. **Collection** — for unpaid milestones. Includes `milestone_id` and
   `amount_due`; `event_id` and `voucher_code` are `null`.
2. **Event invitation** — for upcoming client events. Includes `event_id`
   and `voucher_code`; `milestone_id` and `amount_due` are `null`.

---

## Source precedence

1. **API records** are authoritative for all IDs, codes, names, dates, and
   amounts. Task narrative text is orientation only — it may use shorthand
   names or approximate descriptions.
2. **Product price tiers** override any `prior_unit_price_usd` on the quote.
3. **Customer `payment_profile` + policy rules** together determine payment
   terms — not the task narrative's description of the customer.
4. **Invoice and payment records** determine paid/unpaid state, not the
   opportunity's summary fields alone (though they should agree).
5. **Revenue journal presence** (matching on invoice/phase) determines
   recognition status — not assumptions from the invoice state.

---

## Common pitfalls

- **Using the wrong price tier.** Always match `confirmed_quantity` against
  tier boundaries. A quantity of 360 lands in `[300, 499]`, not `[150, 299]`.
- **Including distractor freight records.** The `/api/freight-quotes` list
  includes stale benchmarks, wrong-size shipments, and unrelated quotes. Filter
  strictly by `quote_id` and then by mode/size plausibility.
- **Stale freight validity.** Check `valid_until` against `quote_date`. A
  freight record that expired before the quote date is not valid and must be
  flagged.
- **Splitting module RFQs into components.** The policy is explicit: keep
  module-level granularity unless the customer asks otherwise. Ignore
  the `components` array on the product.
- **Confusing customer names.** Use the API's `name` field, not the task's
  informal customer label.
- **Incorrect milestone ID format.** Check the answer template's enum
  constraints. When the template says `MS1 | MS2 | MS3`, use that sequential
  form — don't pass through raw `phase_id` values.
- **Missing revenue recognition for paid milestones.** A paid invoice without
  a corresponding revenue journal entry is an actionable gap — it drives
  `RECORD_REVENUE_MS<N>` accounting actions, not `VERIFY_REVENUE_ONLY`.
- **Miscalculating grand totals.** `exw_total + freight_cost = grand_total`.
  Do not add tax, insurance, or duties unless the freight record includes them.
- **Forgetting freight reconfirmation.** `POL-FREIGHT-RECONFIRM` applies to
  every quote with freight options — always set
  `freight_reconfirmation_required: true`.
- **Event date vs task due date.** The invite should be sent before the event.
  The task due date for an invitation is typically well ahead of the event date.
  Use the event's `event_date` and schedule the task reasonably before it.
