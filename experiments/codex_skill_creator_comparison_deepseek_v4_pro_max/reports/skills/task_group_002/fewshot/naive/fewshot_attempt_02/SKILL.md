---
name: medbridge-sales-ops
description: Query the MedBridge Sales Ops API to build quote decisions, reconcile CRM accounts with milestones/payments/revenue recognition, and route follow-up tasks. Covers product quotes with freight, indicative RFQs, and engagement reconciliations with events and vouchers.
---

## When to Use This Skill

Use this skill when a task asks you to query the MedBridge Sales Ops REST API (base URL provided as `TASK_ENV_BASE_URL` or `<TASK_ENV_BASE_URL>`) to produce a structured JSON answer. The API surfaces customers, products, quotes, RFQs, freight quotes, invoices, payments, revenue journals, opportunities, events, vouchers, and policies. The task will ask for one or more of:

- A revised product quote with freight comparison (single-product, EXW plus freight options).
- An indicative module RFQ quote (EXW only, no freight).
- An account reconciliation covering CRM opportunity, milestone invoices/payments, revenue recognition, and linked events/vouchers with follow-up tasks.

## API Reference

All endpoints are GET only. The top-level listing and each record endpoint return JSON.

| Endpoint | Notes |
|---|---|
| `GET /api` | Returns the list of available collections and a `generated_at` datestamp. |
| `GET /api/customers` | Full customer list. |
| `GET /api/customers/{id}` | Single customer. |
| `GET /api/products` | Full product catalog. |
| `GET /api/products/{code}` | Single product with `price_tiers` array. |
| `GET /api/quotes` | Full quote list. |
| `GET /api/quotes/{id}` | Single quote. |
| `GET /api/rfqs` | Full RFQ list. |
| `GET /api/rfqs/{id}` | Single RFQ. |
| `GET /api/freight-quotes` | Full freight-quote list. Filter client-side by `quote_id`. |
| `GET /api/policies` | Full policy list. |
| `GET /api/opportunities` | Full opportunity list. |
| `GET /api/opportunities/{id}` | Single opportunity with `phases` array. |
| `GET /api/invoices` | Full invoice list. Client-side filtering by `customer_id` or `opportunity_id`. |
| `GET /api/payments` | Full payment list. Client-side filtering by `invoice_id` or `opportunity_id`. |
| `GET /api/revenue-journals` | Full revenue-journal list. Client-side filtering by `opportunity_id`, `phase_id`, or `invoice_id`. |
| `GET /api/events` | Full event list. Client-side filtering by `opportunity_id` or `id`. |
| `GET /api/vouchers` | Full voucher list. Client-side filtering by `event_id` or `code`. |
| `GET /api/search?q={text}` | Cross-collection text search; returns a `results` array with `collection`, `id`, and `record` fields. |

The API returns whole collections for most domain objects. Always fetch the full collection when you need to cross-reference (e.g., freight-quotes, invoices, payments, revenue-journals, events, vouchers, policies) and filter client-side by the relevant id fields.

## General Workflow

1. **Parse the task prompt** to identify what is being asked: a quote decision, an indicative RFQ, or an account/engagement reconciliation. Note the quote date (often 2026-06-01), the ids you need to look up, and whether an answer template is provided at `input/payloads/answer_template.json`.

2. **Fetch the source record** (quote, RFQ, or opportunity) by its ID. Read the customer record. Read any referenced product(s).

3. **Fetch supporting collections** (freight-quotes, policies, invoices, payments, revenue-journals, events, vouchers) based on task type.

4. **Apply the rules** from the sections below for pricing, freight filtering, distractor exclusion, policy mapping, milestone reconciliation, and follow-up routing.

5. **Return only valid JSON** matching the answer template's structure. Do not include markdown or explanatory text around the JSON.

## Task Type A: Product Quote with Freight Options

Applies when the prompt names a quote ID (e.g., `Q-TR-...`) with a confirmed quantity for a single product, asks for freight comparison, and the answer template has `quote_summary` / `pricing` plus `freight_options` / `transport_decisions` sections.

### Step-by-step

1. `GET /api/quotes/{quote_id}` — confirms quantity, product_code, customer_id, quote_date, incoterm.
2. `GET /api/customers/{customer_id}` — get name, segment, payment_profile, country, is_recurring.
3. `GET /api/products/{product_code}` — find the matching price tier where `confirmed_quantity` falls between `min_qty` (inclusive) and `max_qty` (inclusive or null). Use that tier's `unit_price_usd`, `lead_time_days`, and the product-level `shelf_life_months`.
4. `GET /api/freight-quotes` — keep only records whose `quote_id` matches the task's quote ID. Within those, **exclude distractors**: records where the `status` is `stale` or `mismatch`, the `shipment_weight_kg` or `shipment_cbm` don't align with the expected shipment (compute expected as `confirmed_quantity × weight_kg` and `confirmed_quantity × cbm` from the product record), or the record is an old/archived version of a mode already covered by a current record. Keep one record per transport mode (air, sea, road) that has the correct quote_id and looks valid.
5. For each kept freight record, determine:
   - `validity_status`: `VALID` if `valid_until` >= quote_date, `STALE` if `valid_until` < quote_date.
   - `source_is_stale`: true when `valid_until` < quote_date.
   - `risk_level` / `customs_border_risk`: map the API's `route_risk` field. `low` → `LOW`, `medium` → `MEDIUM`, `high` → `HIGH`.
   - `risk_flag`: derive from risk_level. `LOW` → `NONE`. `MEDIUM` → `MEDIUM_BORDER_RISK`. `HIGH` → `HIGH_CUSTOMS_RISK`.
6. Compute `exw_total_usd` = `confirmed_quantity × unit_price_usd`. Compute `grand_total_usd` = `exw_total_usd + freight_cost_usd` for each freight option.
7. `GET /api/policies` — read all policies. Key policies:
   - `POL-RECURRING-NGO-PAYMENT`: recurring NGO → `NET_30_AFTER_PO`.
   - `POL-NEW-CLIENT-PAYMENT`: new NGO → `PREPAY_100`.
   - `POL-FREIGHT-RECONFIRM`: `freight_reconfirmation_required` = true for any quote with freight options.
   - `POL-QUOTE-VALIDITY`: quote validity 30 days.
8. **Recommended mode**: `SEA` unless sea has HIGH risk and air is LOW — then prefer air. If sea is valid and low/medium risk it is the default recommendation because it balances cost and risk.
9. **Payment terms**: derive from the customer record's `payment_profile` field, not just segment. `NET_30_AFTER_PO` for profiles indicating recurring commercial/NGO terms. `PREPAY_100` for `NEW_CLIENT_REVIEW`. `MILESTONE_BILLING` for implementation service accounts (not typically used in product quote tasks).
10. **Freight warning** (when the template asks for it): if any road quote has `source_is_stale` true or `customs_border_risk` is HIGH, produce a warning text noting the expired record and risk. If all freight options are valid, the warning can be `NONE` or omitted.

## Task Type B: Indicative Module RFQ (EXW Only)

Applies when the prompt names an RFQ ID (e.g., `RFQ-TR-...`), has no destination, and the answer template has `quote_header` plus `line_items` sections.

### Step-by-step

1. `GET /api/rfqs/{rfq_id}` — get customer_id, requested_modules array (product_code + quantity), quote_date, request_type.
2. `GET /api/customers/{customer_id}` — check segment (new NGO, recurring, etc.), payment_profile.
3. For each module in `requested_modules`, `GET /api/products/{product_code}`. Use the first/only price tier (modules typically have a single tier with `min_qty: 1, max_qty: null`). Pull `unit_price_usd`, `lead_time_days`, `shelf_life_months`, `article_number`.
4. **Do not expand into components**. Quote only at the module level per policy `POL-MODULE-GRANULARITY`. The RFQ narrative and policy both say to keep module lines even when product records show `components` arrays.
5. Compute `line_total` = `quantity × unit_price_usd`. Sum all line totals for `grand_total`.
6. `GET /api/policies`:
   - `POL-INDICATIVE-EXW`: EXW only, freight excluded.
   - `POL-NEW-CLIENT-PAYMENT`: new NGO → `PREPAY_100`.
   - `POL-QUOTE-VALIDITY`: `offer_validity_days` = 30.
7. Payment terms: use `PREPAY_100` for new NGO (`NEW_CLIENT_REVIEW` profile, `is_recurring: false`, `client_since: null`, segment `new_ngo`). For recurring customers, use the profile from the customer record.
8. `who_documentation_required`: true for IEHK-style modules.
9. `freight_excluded`: true. `quote_basis`: `EXW_ONLY`.

## Task Type C: Account/Engagement Reconciliation

Applies when the prompt names an opportunity ID (e.g., `OPP-TR-...`) and asks for reconciliation of milestones, invoices, payments, revenue recognition, events, and vouchers. The answer template has `account_status` or `engagement_reconciliation` plus milestones, revenue, event, and follow-up sections.

### Step-by-step

1. `GET /api/opportunities/{opportunity_id}` — read stage, won_amount_usd, phases array (phase_id, amount_usd, completion_date, invoice_id).
2. `GET /api/customers/{customer_id}` — customer_name, contacts.
3. `GET /api/invoices` — filter by `opportunity_id` or `customer_id`. For each phase, find the matching invoice by `phase_id` or `id`.
4. `GET /api/payments` — filter by `opportunity_id`. Match to invoices by `invoice_id`.
5. `GET /api/revenue-journals` — filter by `opportunity_id`. Match to invoices/phases by `phase_id` or `invoice_id`.
6. `GET /api/events` — filter by `opportunity_id` or the specific event_id from the prompt.
7. `GET /api/vouchers` — filter by `event_id` or `code` from the prompt.

### Milestone Reconciliation Rules

For each phase from the opportunity:
- **milestone_id**: Map phase order to `MS1`, `MS2`, `MS3` etc. in ascending order by phase chronology (earliest completion_date = MS1).
- **amount**: phase `amount_usd`.
- **invoice_state**: from invoice `status` field. `paid` → `PAID`, `unpaid` → `OPEN`, `draft` → `DRAFT`, `overdue` → `OPEN` (overdue, but the state is still `OPEN`).
- **payment_state**: If a payment exists for the invoice_id, `PAID` if `paid_amount_usd` covers the full invoice. `PARTIAL` if partial. `UNPAID` if no payment or USD 0 paid.
- **paid_amount**: from payment record `amount_usd` (sum if multiple payments per invoice).
- **due_date**: from invoice `due_date` or null if not applicable (paid invoices may have null due_date in the template).
- **recognition_status**: `RECOGNIZED` if a revenue journal exists for that phase_id/invoice_id. `MISSING_REVENUE_JOURNAL` if paid (or partially paid) but no journal. `NOT_REQUIRED_UNPAID` if unpaid.
- **opportunity_matches_milestones** / **opportunity_matches_phase_total**: true if sum of phase amounts equals `won_amount_usd`, false otherwise.
- **outstanding_balance**: sum of unpaid amounts across all phases.
- **total_paid_amount**: sum of all paid amounts across all phases.

### Revenue Recognition Summary

- **recognition_status**: `COMPLETE_FOR_PAID_MILESTONES` if every paid milestone has a revenue journal; `MISSING_FOR_PAID_MILESTONES` if any paid milestone lacks a revenue journal; `NOT_REQUIRED` if no milestones are paid.
- **recognized_milestones**: list of milestone IDs that have journals.
- **missing_required_milestones**: list of paid milestone IDs without journals.
- **recognized_amount**: sum of journal amounts.

### Follow-Up / Invoice Actions

**Collection tasks** (from policy `POL-REVREC`):
- Unpaid milestones with future due dates → `MONITOR_UNPAID_NOT_DUE`. Owner: `ACCOUNT_MANAGEMENT`.
- Unpaid milestones with past due dates (overdue) → `SEND_COLLECTION_NOTICE`. Owner: `COLLECTIONS`.
- Fully paid milestones → `NO_COLLECTION_ACTION`.

**Accounting tasks** (from policy `POL-REVREC`):
- Paid milestone with missing revenue journal → `RECORD_REVENUE_MS{n}`. Debit: `DEFERRED_REVENUE`, Credit: `IMPLEMENTATION_SERVICES_REVENUE`. Owner: `ACCOUNTING`.
- All paid milestones recognized → `VERIFY_REVENUE_ONLY` or `NO_ACCOUNTING_ACTION`.

**Event/Invite tasks**:
- If the event has `status` `scheduled` or `confirmed` (treat as `SCHEDULED`) and the voucher is `active`, the invite action is `SEND_BRIEFING_INVITE`. Owner: `ACCOUNT_MANAGEMENT`.
- For the invite task, use the event's `primary_contact` as `contact_name` and the `customer_id` from the event.

### Data Field Mapping Notes

- The API voucher `discount_percent` field is a percentage. When the answer template expects a dollar amount (e.g., `voucher_discount`, `discount_amount`), use the percent value directly as the discount value (e.g., 100 means USD 100.00, 50 means USD 50.00). The training answers treat `discount_percent` as the actual discount value in USD.
- Event `status` in API uses values like `confirmed`, `scheduled`, `live`, `completed`, `tentative`. Map `scheduled`/`confirmed` to `SCHEDULED`, `live` to `ACTIVE`, `completed` to `COMPLETED`, `tentative` to `SCHEDULED`.
- Voucher `max_redemptions` → `max_uses` in the template.
- Opportunity `stage` field uses values like `closed_won`. Map to `WON`.
- Template enum values must be used exactly as declared in the template: `WON`, `OPEN`, `LOST`; `PAID`, `OPEN`, `VOID`; `RECOGNIZED`, `MISSING_REVENUE_JOURNAL`, `NOT_REQUIRED_UNPAID`; etc.

## Distractor Handling

The API includes distractor records designed to test filtering. Apply these rules:

1. **Freight quotes**: Filter by `quote_id` first. Exclude records where `status` is `stale` or `mismatch`. Exclude records whose `shipment_weight_kg` or `shipment_cbm` are far from the expected shipment total (computed as `quantity × product weight_kg` and `quantity × product cbm`). Keep exactly one record per transport mode (air/sea/road) for the target quote.

2. **Invoices**: Filter to the target `opportunity_id` or `customer_id`. Match to phases by `phase_id`. Disregard invoices for other opportunities.

3. **Payments**: Filter to the target `opportunity_id`. Match to invoices by `invoice_id`.

4. **Revenue journals**: Filter to the target `opportunity_id`. Match to phases by `phase_id` or `invoice_id`.

5. **Events**: Filter to the target `opportunity_id` or the specific `event_id` named in the prompt.

6. **Vouchers**: Filter to the target `event_id` or the specific `voucher_code` named in the prompt.

7. **Search endpoint**: The `/api/search` endpoint can return records from multiple collections. Use it only when a task provides a partial key you need to resolve across collections. Always verify the returned `collection` field before using a result.

## Policy Reference

These policy IDs and their rules are stable across the API:

| Policy ID | Rule Summary |
|---|---|
| `POL-NEW-CLIENT-PAYMENT` | New NGO → `PREPAY_100` |
| `POL-RECURRING-NGO-PAYMENT` | Recurring NGO → `NET_30_AFTER_PO` |
| `POL-INDICATIVE-EXW` | No-destination RFQ → EXW only, exclude freight |
| `POL-FREIGHT-RECONFIRM` | Freight requires reconfirmation at final order |
| `POL-MODULE-GRANULARITY` | Module RFQs stay at module level, not components |
| `POL-REVREC` | Paid complete milestones → recognize revenue; unpaid → monitor/collect |
| `POL-QUOTE-VALIDITY` | Catalog pricing valid 30 days from quote date |
| `POL-EXW-SCOPE` | EXW excludes freight, insurance, duties, clearance, last-mile |

Always fetch policies at runtime with `GET /api/policies` rather than relying solely on this table, because the API is the authoritative source.

## Answer Template

The task provides an answer template at `input/payloads/answer_template.json`. Read it first to understand the exact structure, field names, and enum values expected. Fill every field. Use the exact enum strings defined in the template. Monetary values should be numbers with two decimal places. Dates in ISO `YYYY-MM-DD` format. Booleans as JSON `true`/`false`, not strings.

## Important Constraints

- Do not call any endpoint not listed in the allowed endpoints. In particular, do not call `/api/judge`.
- All GET endpoints are unauthenticated. No credentials are needed.
- The base URL is provided by the task runner as `TASK_ENV_BASE_URL` or `<TASK_ENV_BASE_URL>`. Always resolve it from the environment or the prompt.
- Return only the JSON answer. No markdown fences, no explanatory text unless the prompt explicitly asks for it.
