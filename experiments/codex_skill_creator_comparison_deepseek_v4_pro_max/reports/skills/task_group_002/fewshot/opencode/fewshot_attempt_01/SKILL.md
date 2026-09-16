---
name: medbridge-reconciliation
description: Reconcile quotes, RFQs, engagements, and milestones against the MedBridge Sales Ops API to produce account-ready decision-package JSON. Use when the task references MedBridge, reconciliation, quote revision, freight comparison, IEHK or other module RFQs, milestone-to-invoice cross-referencing, revenue recognition journal verification, opportunity-to-phase matching, OR any MedBridge Sales Ops API endpoint. This covers freight-option EXW quotes, indicative module-level quoting, and opportunity-milestone engagement reconciliations with follow-up task routing.
---

# MedBridge Sales Ops Reconciliation

Reconcile CRM, quote, logistics, and milestone engagement data from the MedBridge Sales
Ops API into structured JSON decision packages. This skill covers three workflow families
that share the same API surface but apply different business logic.

Use the shared API base URL the runner provides. In prompts it appears as a placeholder
like `<TASK_ENV_BASE_URL>` or `BASE_URL`. Substitute it into every `GET` call below.

## Quick dispatch

Read the prompt for the task shape and follow the matching workflow:

- **The prompt names a quote ID starting with `Q-TR` and asks for freight options** →
  go to [Quote Revision with Freight](#1-quote-revision-with-freight-comparison).
- **The prompt names an RFQ ID starting with `RFQ-TR`, mentions "IEHK" modules, and
  says EXW only or "no destination"** →
  go to [Indicative Module RFQ](#2-indicative-module-rfq-exw-only).
- **The prompt names an opportunity ID starting with `OPP-TR` and asks for milestone
  reconciliation, invoice matching, revenue recognition, or a contact name** →
  go to [Engagement Reconciliation](#3-engagement-milestone-reconciliation).

Any prompt that does not clearly match one shape is likely a near miss for this skill.
Read the prompt carefully before committing to a workflow.

## Shared ground rules

- The API is read-only. All endpoints are `GET` and return JSON with a `records` array
  on collection endpoints or a single record object on detail endpoints.
- Every entity has a stable `id` field. Use those exact values in output JSON.
- Money values are always in USD with two decimal places.
- Dates are ISO `YYYY-MM-DD`. Use the quote date or "as of" date from the prompt;
  if the prompt doesn't state one, default to `2026-06-01`.
- When the prompt provides a customer ID, product code, opportunity ID, or quote ID,
  call the matching detail endpoint, not just the collection list.
- Output must be pure JSON matching the answer template. No markdown wrapping.

## 1. Quote Revision with Freight Comparison

A customer confirmed a revised quantity for a product on an existing quote.
Return one JSON with quote summary, freight options, and policy flags.

### API calls

Always make these calls, in this order:

1. `GET /api/quotes/<quote_id>` — confirms the quote record, customer ID, product
   code, confirmed quantity, incoterm, prior pricing, and line-item notes.
2. `GET /api/customers/<customer_id>` — confirms customer type, segment,
   payment_profile, recurring status, grant terms, and region. Use the
   `customer_id` field from the quote response.
3. `GET /api/products/<product_code>` — confirms product name, article number,
   price tiers, lead time, shelf life, and cold-chain flag. Use the
   `primary_product_code` from the quote response.
4. `GET /api/freight-quotes` — lists all freight quotes. Filter client-side to
   records whose `quote_id` field matches the quote ID.
5. `GET /api/policies` — confirms payment terms, freight reconfirmation, EXW
   scope, and quote validity rules.

### Catalog tier matching

The product record has a `price_tiers` array. Each tier defines `min_qty`,
`max_qty` (null means unlimited), `unit_price_usd`, `lead_time_days`, and
`shelf_life_months`. Find the tier where `confirmed_quantity` falls within
`[min_qty, max_qty]`. When the quote mentions a customer-confirmed quantity
that differs from the prior quote quantity, the catalog tier may override the
prior unit price — always source the price from the matching tier, not from
the prior quote.

Compute `exw_total_usd = confirmed_quantity * unit_price_usd`.

### Freight option assembly

For each freight quote that matches the quote ID:

- Use the `id`, `mode` (uppercased to AIR/SEA/ROAD), `cost_usd`, and
  `transit_days_text`.
- Map `route_risk` to a display value: `low` → `"LOW"`, `medium` → `"MEDIUM"`,
  `high` → `"HIGH"`.
- Set `risk_flag` from `risk_notes`: if route_risk is `low`, `"NONE"`;
  for `medium`, reflect the concern (e.g. `"MEDIUM_BORDER_RISK"`); for `high`,
  reflect the high-risk concern.
- `grand_total_usd = exw_total_usd + freight_cost_usd`.
- Check `valid_until`: a freight quote is stale when its `valid_until` date is
  before the quote date. Mark it with `"validity_status": "STALE"` and
  `"source_is_stale": true`.

When the output template asks for `validity_status` (like train_004's template),
add it. When the template only asks for `valid_until`, just use that field.

### Policy and recommendation logic

- Payment terms come from the customer's `payment_profile` field, cross-checked
  against matching policy rules. For recurring customers, the policy
  `POL-RECURRING-NGO-PAYMENT` or equivalent applies. For new clients,
  `POL-NEW-CLIENT-PAYMENT` applies.
- `freight_reconfirmation_required` is `true` because policy
  `POL-FREIGHT-RECONFIRM` says rates need reconfirmation at final order.
- `all_freight_options_valid_on_quote_date`: compare each freight quote's
  `valid_until` against the quote date. If all are on or after the quote date,
  set `true`; otherwise `false`.
- **Recommended mode**: prefer the lowest-cost valid option whose `route_risk`
  is `low`. SEA is often the winner for non-time-critical cargo. If the
  prompt mentions delivery timing or a "need-by" date, factor transit days
  into the recommendation. If all modes have some risk, default to the
  cheapest with the least risk.

When the template includes `client_warnings`, generate a freight warning
summarizing any stale or high-risk options.

### Ordering freight options

List in the order AIR, SEA, ROAD, matching the typical template order.

## 2. Indicative Module RFQ (EXW Only)

An RFQ requests indicative pricing for medical modules without a confirmed
destination, so freight is excluded and the quote is EXW only.

### API calls

1. `GET /api/rfqs/<rfq_id>` — confirms the RFQ, customer ID, requested modules
   with `product_code` and `quantity` per module, and request type.
2. `GET /api/customers/<customer_id>` — confirms customer type (new NGO vs
   recurring), segment, and payment_profile.
3. For each module in the RFQ's `requested_modules`, call
   `GET /api/products/<product_code>` to get the product name, article number,
   unit price tier, lead time, and shelf life.
4. `GET /api/policies` — confirms module-level quoting policy
   (`POL-MODULE-GRANULARITY`), EXW-only scope for indicative quotes without
   destination (`POL-INDICATIVE-EXW`), quote validity (`POL-QUOTE-VALIDITY`),
   and payment terms for new clients (`POL-NEW-CLIENT-PAYMENT`).

### Module-level quoting

The RFQ narrative and the policy `POL-MODULE-GRANULARITY` both instruct quoting
at module level only, even when the API exposes `component_composition_distractors`
or product `components` arrays. Each RFQ module becomes one line item with the
module's product code, article number, quantity, and unit price.

When a product has a single price tier covering all quantities (min_qty 1,
max_qty null), use that tier directly. Multiply quantity by unit price for the
line total.

### Payment terms for new NGOs

Check the customer's `payment_profile`. For `"NEW_CLIENT_REVIEW"` or similar,
apply `PREPAY_100` per the new-client policy. For recurring customers with
`NET_30_AFTER_PO`, use that.

### Quote validity

If the output template asks for `offer_validity_days`, use 30 calendar days
per `POL-QUOTE-VALIDITY` (standard catalog quote validity). For
`who_documentation_required`, set `true` when the RFQ involves medical modules
for an NGO — this is the safe default for humanitarian medical supply.

- `freight_excluded` is always `true` for this workflow.

## 3. Engagement & Milestone Reconciliation

A won opportunity has milestone phases with associated invoices, payments,
revenue journals, events, and vouchers. Reconcile everything and produce
follow-up task instructions.

### API calls

1. `GET /api/opportunities/<opportunity_id>` — confirms stage, won amount,
   phases with phase IDs and amounts, contact, customer ID, and any notes.
2. `GET /api/customers/<customer_id>` — confirms customer name and details.
3. `GET /api/invoices` — filter client-side by `opportunity_id` to match the
   opportunity's phases to their invoices.
4. `GET /api/payments` — filter by `opportunity_id` to see which invoices
   have been paid.
5. `GET /api/revenue-journals` — filter by `opportunity_id` to see which
   completed paid milestones have revenue recognition entries.
6. `GET /api/events` — find events whose `opportunity_id` matches. Use the
   event's `primary_contact` and `voucher_code` details.
7. `GET /api/vouchers/<voucher_code>` — confirms voucher status, discount,
   max uses.
8. `GET /api/policies` — confirms revenue recognition rule
   (`POL-REVREC`), payment terms, and quote validity.

### Cross-referencing logic

For each phase in the opportunity:

- Match the phase to its invoice via `invoice_id` on the phase record.
- Match the invoice to payments: if `paid_amount_usd >= amount_usd`, the
  milestone is PAID; if `paid_amount_usd > 0` but less than full, it is
  PARTIAL; otherwise UNPAID.
- Match to revenue journals: look for a journal entry whose `phase_id`
  matches and whose `status` is `"posted"`.

**Revenue recognition status per milestone:**

| Invoice paid? | Revenue journal exists? | Status |
|---|---|---|
| Yes | Yes | `RECOGNIZED` |
| Yes | No | `MISSING_REVENUE_JOURNAL` or `REQUIRED_MISSING` |
| No | N/A | `NOT_REQUIRED_UNPAID` |

**Overall revenue recognition status:**

- If every paid milestone has a revenue journal → `COMPLETE_FOR_PAID_MILESTONES`
- If any paid milestone lacks a journal → `MISSING_FOR_PAID_MILESTONES`
- If no milestones are paid → `NOT_REQUIRED`

**Opportunity-to-phase matching:** sum all phase amounts and compare to
`won_amount_usd`. Set `opportunity_matches_milestones` or
`opportunity_matches_phase_total` to `true` when they are equal.

**Outstanding balance:** sum `outstanding_amount_usd` (or amount unpaid) across
all invoices for the opportunity.

### Follow-up task routing

Produce exactly the tasks the data demands:

**Collection tasks:**
- If any milestone is unpaid with a due date on or before the as-of date, it
  is overdue → action is `COLLECT_UNPAID_MILESTONE` or `SEND_COLLECTION_NOTICE`,
  owner queue is `COLLECTIONS` or `ACCOUNT_MANAGEMENT`.
- If unpaid but not yet due → action is `MONITOR_UNPAID_NOT_DUE`, owner queue
  is `ACCOUNT_MANAGEMENT`.
- If no unpaid milestones exist → `NO_COLLECTION_ACTION`.

**Revenue recognition tasks:**
- If any paid milestone has `MISSING_REVENUE_JOURNAL` → action is
  `RECORD_REVENUE_MS2` (or the specific milestone), debit `DEFERRED_REVENUE`,
  credit `IMPLEMENTATION_SERVICES_REVENUE`, owner queue `ACCOUNTING`.
- If all paid milestones are recognized → `NO_ACCOUNTING_ACTION` or
  `VERIFY_REVENUE_ONLY`.

**Event/invitation tasks:**
- If an event exists with status `scheduled` or `confirmed` and its
  voucher is active → action is `SEND_BRIEFING_INVITE` or
  `SEND_EVENT_INVITATION`, owner queue `ACCOUNT_MANAGEMENT`, contact
  from the event's `primary_contact` field.
- If the event is in the past or completed → `NO_INVITE_ACTION`.

### Accounting action details

When a revenue recognition journal is missing for a paid milestone, produce
the accounting action entry:

- `action`: `RECORD_REVENUE_<milestone_id>` (e.g. `RECORD_REVENUE_MS2`)
- `milestone_id`: the specific milestone ID
- `amount`: the milestone amount
- `debit_account`: `DEFERRED_REVENUE`
- `credit_account`: `IMPLEMENTATION_SERVICES_REVENUE`
- `owner_queue`: `ACCOUNTING`

This mirrors the standard pattern from the revenue recognition policy.

## Error handling

- If an API call returns an empty response or an error, verify the ID and
  retry once. If it still fails, leave the corresponding output field empty
  or at its null/zero default instead of guessing.
- If the prompt names an entity that does not exist in the API, return the
  template with empty fields and include a `_note` field explaining the
  missing record.

## Reference files

- [references/policy-rules.md](references/policy-rules.md) — Full list of
  MedBridge policy rules and how they apply per workflow.
- [references/reconciliation-patterns.md](references/reconciliation-patterns.md) —
  Detailed reconciliation decision tables for milestone, invoice, payment,
  and revenue journal cross-referencing.
- [references/field-mappings.md](references/field-mappings.md) — API field to
  template field mappings for each workflow's common template shapes.

Read a reference when the data demands more detail than the workflow section
above covers. The policy rules reference is especially useful when a task
mentions an unfamiliar policy area.
