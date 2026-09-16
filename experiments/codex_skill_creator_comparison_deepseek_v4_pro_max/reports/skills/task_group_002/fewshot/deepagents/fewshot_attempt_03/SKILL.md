---
name: medbridge-sales-ops
description: "Complete MedBridge Sales Ops API integration for humanitarian and medical supply quoting, pricing, freight comparison, account reconciliation, and engagement milestone tracking. Use when the task involves: (1) Building quote revision packages with EXW pricing, freight options, and policy-driven recommendations, (2) Processing indicative RFQ/quote requests with module-level line items and EXW-only scope, (3) Reconciling won opportunities against milestone invoices, payments, and revenue recognition journals, (4) Producing engagement reconciliations with accounting actions and event invitation tasks, (5) Any MedBridge Sales Ops data retrieval across customers, products, quotes, RFQs, freight-quotes, invoices, payments, revenue-journals, events, vouchers, or opportunities via the MedBridge REST API."
---

# MedBridge Sales Ops

## Overview

The MedBridge Sales Ops API surfaces shared CRM, quote, logistics, and milestone engagement data for humanitarian and medical supply workflows. Use it to build quote decision packages, indicative pricing responses, account reconciliations, and engagement follow-ups.

## API Setup

The API base URL is provided as `<TASK_ENV_BASE_URL>` by the task runner. All endpoints are read-only GET. Use `curl` for all API calls and `python3 -c "import json"` or `python3 -m json.tool` for JSON formatting.

**Collection endpoints:**

| Endpoint | Description |
|---|---|
| `GET /api` | List all collections |
| `GET /api/search?q=<text>` | Full-text search across all collections |
| `GET /api/customers` | All customer records |
| `GET /api/customers/<id>` | Single customer |
| `GET /api/products` | All product catalog entries |
| `GET /api/products/<code>` | Single product by code |
| `GET /api/quotes` | All quotes |
| `GET /api/quotes/<id>` | Single quote |
| `GET /api/rfqs` | All RFQs |
| `GET /api/rfqs/<id>` | Single RFQ |
| `GET /api/freight-quotes` | All freight quotes |
| `GET /api/freight-quotes/<id>` | Single freight quote |
| `GET /api/policies` | All business policies |
| `GET /api/opportunities` | All opportunities |
| `GET /api/opportunities/<id>` | Single opportunity |
| `GET /api/invoices` | All invoices |
| `GET /api/invoices/<id>` | Single invoice |
| `GET /api/payments` | All payments |
| `GET /api/payments/<id>` | Single payment |
| `GET /api/revenue-journals` | All revenue journals |
| `GET /api/revenue-journals/<id>` | Single revenue journal |
| `GET /api/events` | All events |
| `GET /api/events/<id>` | Single event |
| `GET /api/vouchers` | All vouchers |
| `GET /api/vouchers/<code>` | Single voucher by code |

Always fetch related collections in parallel. For a quote revision, fetch the quote, customer, product, freight-quotes, and policies simultaneously. For an opportunity reconciliation, fetch the opportunity, its customer, invoices, payments, revenue-journals, events, and vouchers together.

## Core Workflows

### 1. Quote Revision with Freight

Use when the user asks for a revised quote decision package with EXW pricing and freight comparisons.

**Steps:**

1. Fetch the quote, customer, product, freight quotes, and policies in parallel.
2. Identify the correct product price tier: match `confirmed_quantity` to the tier where `min_qty <= quantity <= max_qty` (null `max_qty` means unlimited). Use the tier's `unit_price_usd`, `lead_time_days`, and `shelf_life_months`.
3. Compute `exw_total_usd = confirmed_quantity * unit_price_usd`.
4. Filter freight quotes by `quote_id` matching the quote. Sort modes as AIR, SEA, ROAD. For each, compute `grand_total_usd = exw_total_usd + freight_cost_usd`.
5. Assess freight validity: a freight quote is STALE when `valid_until` is before the `quote_date`. Route risk levels map to risk flags: `low`→`NONE`, `medium`→`MEDIUM_BORDER_RISK`, `high`→`HIGH_BORDER_RISK`.
6. Determine the recommended mode: prefer SEA when it has low risk and is valid. Set `freight_reconfirmation_required: true` per policy POL-FREIGHT-RECONFIRM.
7. Derive payment terms from the customer's `payment_profile` or the applicable policy (see [business_rules.md](references/business_rules.md)).
8. Check `all_freight_options_valid_on_quote_date` — false if any freight option has `valid_until` before the quote date.
9. Add a `freight_warning` when any freight option is stale or has high border risk.

**Example output shape:** See [business_rules.md](references/business_rules.md) for field mapping and value derivation rules.

### 2. Indicative RFQ / Module Quote

Use when the user asks for an indicative EXW-only quote from an RFQ, especially for module-level products.

**Steps:**

1. Fetch the RFQ, customer, and products in parallel. Also fetch policies.
2. For each module in the RFQ's `requested_modules`, fetch the product by code for pricing, `article_number`, `lead_time_days`, and `shelf_life_months`.
3. Quote at the module level only — do not split into components or sub-SKUs unless the prompt explicitly requests it. This follows policy POL-MODULE-GRANULARITY.
4. Since the RFQ has no confirmed destination, exclude freight entirely. Set `quote_basis: "EXW_ONLY"` and `freight_excluded: true`.
5. For new NGO customers (`segment: "new_ngo"`), use `PREPAY_100` payment terms. For other customer types, match their `payment_profile`.
6. Set `offer_validity_days: 30` per POL-QUOTE-VALIDITY.
7. Each line item: `line_total = quantity * unit_price`. Sum all line totals for `grand_total`.
8. Products where `price_tiers` has only one entry use that tier directly; no quantity matching is needed since the RFQ specifies the quantity.

### 3. Account Reconciliation

Use when the user asks to reconcile a won opportunity against invoices, payments, and revenue recognition, plus event/voucher linkage.

**Steps:**

1. Fetch the opportunity, its customer, invoices, payments, revenue-journals, events, and vouchers in parallel. Use the search endpoint or direct ID lookups.
2. Map opportunity phases to invoices by `phase_id` or invoice ID reference. For each phase:
   - Determine `invoice_state`: `paid` / `unpaid`
   - Determine `payment_state`: from payment records linked by `invoice_id`
   - Look up revenue recognition: a revenue journal entry linked by `invoice_id` means RECOGNIZED
   - For paid milestones with no revenue journal, status is `MISSING_REVENUE_JOURNAL`
   - For unpaid milestones, status is `NOT_REQUIRED_UNPAID`
3. Verify `opportunity_matches_milestones`: `won_amount` equals sum of all phase `amount_usd` values.
4. Compute `outstanding_balance`: sum of unpaid amounts across phases.
5. Link the event by `customer_id` or `opportunity_id`. Retrieve the voucher by `voucher_code`.
6. Generate follow-up tasks:
   - **Collection task** for each unpaid milestone with a due date, linked to the opportunity and contact.
   - **Event invitation task** when the event is scheduled/confirmed, linked to the contact.

See [business_rules.md](references/business_rules.md) for complete status enum values and task routing rules.

### 4. Engagement Reconciliation with Accounting Actions

Use when the user asks for finance-ready reconciliation with accounting journal entries and collection routing.

**Steps:**

1. Follow the same data gathering as workflow 3 (account reconciliation).
2. For each milestone, compute detailed states:
   - `invoice_state`: from invoice `status` field (paid/unpaid)
   - `payment_state`: from payments linked to the invoice
   - `recognition_status`: cross-reference revenue journals by `invoice_id`
3. Determine the primary accounting action:
   - If any paid milestone lacks a revenue journal → `RECORD_REVENUE_MS2` (target the specific milestone ID)
   - If all paid milestones have journals → `VERIFY_REVENUE_ONLY`
   - If no paid milestones → `NO_ACCOUNTING_ACTION`
4. Build the accounting action detail with the correct `debit_account` (`DEFERRED_REVENUE`), `credit_account` (`IMPLEMENTATION_SERVICES_REVENUE`), and `owner_queue` (`ACCOUNTING`).
5. Build the collection task: if unpaid milestone is not yet past due → `MONITOR_UNPAID_NOT_DUE` with `owner_queue: ACCOUNT_MANAGEMENT`. If past due → `SEND_COLLECTION_NOTICE` with `owner_queue: COLLECTIONS`.
6. Build the event invite task: `SEND_BRIEFING_INVITE` when the event is `scheduled` or equivalent, with `owner_queue: ACCOUNT_MANAGEMENT`.

## Data Relationships

See [api_reference.md](references/api_reference.md) for the complete field reference for each collection.

**Key joins:**
- Quote → Customer (`customer_id`), Product (`line_items[].product_code`), Freight Quotes (`id` matches `quote_id`)
- RFQ → Customer (`customer_id`), Products (`requested_modules[].product_code`)
- Opportunity → Customer (`customer_id`), Invoices (via `phases[].invoice_id`), Payments (`invoice_id`), Revenue Journals (`invoice_id`), Events (`opportunity_id`), Vouchers (`opportunity_id`)
- Event → Voucher (`voucher_code`)
- Customer → Payment terms via `payment_profile` or segment‑to‑policy mapping

## Business Rules

See [business_rules.md](references/business_rules.md) for:
- Policy‑to‑action mappings (POL-NEW-CLIENT-PAYMENT, POL-RECURRING-NGO-PAYMENT, POL-FREIGHT-RECONFIRM, POL-MODULE-GRANULARITY, POL-REVREC, POL-QUOTE-VALIDITY, POL-EXW-SCOPE, POL-INDICATIVE-EXW)
- Price tier matching logic
- Freight validity, risk level, and staleness rules
- Payment term derivation by customer segment
- Revenue recognition journal requirements
- Follow‑up task routing by state

## Output Requirements

Always return only valid JSON matching the supplied `answer_template.json`. Do not include markdown fences, explanatory text, or commentary outside the JSON. Use USD with two decimals for all money fields. Use ISO `YYYY-MM-DD` for all dates. Use the exact enum values from the template. Map API field names to the template key names precisely.
