---
name: medbridge-sales-ops
description: Interact with the MedBridge Sales Ops REST API to prepare quotes, reconcile accounts, and manage customer engagements. Use this skill whenever a task involves MedBridge quote preparation, RFQ pricing, account reconciliation, engagement review, or any workflow that requires calling the MedBridge Sales Ops API endpoints.
---

# MedBridge Sales Ops API Skill

## Overview

The MedBridge Sales Ops API is a RESTful read-only service that exposes customer, product, quote, RFQ, freight, policy, opportunity, invoice, payment, revenue-journal, event, and voucher records. All tasks in this domain follow a common pattern: read the prompt to identify the target entities, fetch related records from the API, apply business rules, and return a single JSON payload matching the supplied answer template.

## API Connection

The API base URL is injected by the task runner as `<TASK_ENV_BASE_URL>` or `BASE_URL`. Always resolve this placeholder before making requests. The API requires no authentication headers.

Use the API root `/api` to confirm connectivity and discover available resource collections. All subsequent lookups chain from resource list endpoints or direct-ID lookups.

## Endpoint Reference

All endpoints are read-only GET requests. Include an `Accept: application/json` header.

### Discovery and Search

| Endpoint | Purpose |
|----------|---------|
| `GET /api` | Root index listing all resource collections available |
| `GET /api/search` | Cross-entity search (query by keyword or ID fragment) |

### Core Entities

| Endpoint | Purpose | Key Fields |
|----------|---------|------------|
| `GET /api/customers` | List all customers | `customer_id`, `name`, `policy_id`, `account_type` (NGO / commercial) |
| `GET /api/customers/{id}` | Single customer detail | Includes linked policy and contact info |
| `GET /api/products` | List all products | `product_code`, `article_number`, `tiers[]` with qty ranges, unit price, lead time, shelf life |
| `GET /api/products/{code}` | Single product detail | Full tier table and composition details |

### Transactional Entities

| Endpoint | Purpose | Key Fields |
|----------|---------|------------|
| `GET /api/rfqs` | List all RFQs | `rfq_id`, `customer_id`, `items[]`, `quote_date` |
| `GET /api/rfqs/{id}` | Single RFQ detail | Requested line items with quantities |
| `GET /api/quotes` | List all quotes | `quote_id`, `customer_id`, `product_code`, `quantity`, `quote_date` |
| `GET /api/quotes/{id}` | Single quote detail | Full quote line items |
| `GET /api/freight-quotes` | List all freight quotes | `freight_id`, `mode`, `cost`, `transit_days`, `valid_until`, `risk_level`, `risk_flag` |
| `GET /api/freight-quotes/{id}` | Single freight detail | Per-mode breakdown |

### Policy and Control Entities

| Endpoint | Purpose | Key Fields |
|----------|---------|------------|
| `GET /api/policies` | List all policies | `policy_id`, `payment_terms`, `freight_reconfirmation_required`, `offer_validity_days`, `who_documentation_required` |
| `GET /api/policies/{id}` | Single policy detail | Full terms and conditions |

### Revenue and Finance Entities

| Endpoint | Purpose | Key Fields |
|----------|---------|------------|
| `GET /api/opportunities` | List all opportunities | `opportunity_id`, `customer_id`, `stage` (WON / OPEN / LOST), `won_amount` |
| `GET /api/opportunities/{id}` | Single opportunity | Linked milestones, contact |
| `GET /api/invoices` | List all invoices | `invoice_id`, `milestone_id`, `opportunity_id`, `total`, `state` (PAID / OPEN / VOID) |
| `GET /api/invoices/{id}` | Single invoice | Payment allocations |
| `GET /api/payments` | List all payments | `payment_id`, `invoice_id`, `amount` |
| `GET /api/payments/{id}` | Single payment detail | |
| `GET /api/revenue-journals` | List all revenue journals | `journal_id`, `milestone_id`, `amount` |
| `GET /api/revenue-journals/{id}` | Single journal entry | |

### Engagement Entities

| Endpoint | Purpose | Key Fields |
|----------|---------|------------|
| `GET /api/events` | List all events | `event_id`, `customer_id`, `status` (SCHEDULED / ACTIVE / COMPLETED / CANCELLED) |
| `GET /api/events/{id}` | Single event | Date, linked voucher |
| `GET /api/vouchers` | List all vouchers | `voucher_code`, `status` (ACTIVE / DRAFT / EXPIRED / DISABLED), `discount_amount`, `max_uses` |
| `GET /api/vouchers/{code}` | Single voucher | |

## Workflow Patterns

### 1. Quote Preparation (with Freight)

Use this workflow when the prompt asks for a quote with pricing and freight options (e.g., train_001, train_004).

**Step-by-step:**

1. Fetch the quote by ID from `/api/quotes/{quote_id}` to confirm the `customer_id`, `product_code`, `quantity`, and `quote_date`.
2. Fetch the customer from `/api/customers/{customer_id}` to get the `policy_id` and account type.
3. Fetch the product from `/api/products/{product_code}`. Find the catalog tier whose `min_quantity` ≤ confirmed quantity ≤ `max_quantity`. Extract `unit_price_usd`, `lead_time_days`, and `shelf_life_months` from the matching tier.
4. Compute `exw_total_usd = unit_price_usd × quantity`.
5. Fetch all freight quotes from `/api/freight-quotes`. Filter to the ones relevant to the quote (matching freight IDs from the product or quote context). If query strings are supported, filter by product; otherwise iterate the list and match by freight ID pattern.
6. For each freight option, compute `grand_total_usd = exw_total_usd + freight_cost_usd`.
7. Fetch the policy from `/api/policies/{policy_id}` to extract `payment_terms` and `freight_reconfirmation_required`.
8. Determine the recommended mode: prefer the lowest-cost option that is valid on the quote date and has a LOW risk level. SEA is typically the best cost/reliability trade-off.
9. Populate the answer template fields using the gathered data.

**Catalog tier matching logic:**
```
For a given quantity Q and product tiers[]:
  matched_tier = tier where tier.min_quantity <= Q <= tier.max_quantity
```
Use the matched tier's `unit_price_usd`, `lead_time_days`, and `shelf_life_months`.

**Freight validity check:**
```
A freight option is VALID on quote_date if:
  quote_date <= freight.valid_until
A freight option is STALE if:
  quote_date > freight.valid_until
```

A stale freight quote must be flagged with `source_is_stale: true`, `validity_status: "STALE"`, and the response should include a warning that the rate requires reconfirmation.

**Risk evaluation:**
- `risk_level: "LOW"`, `risk_flag: "NONE"` → safe to use
- `risk_level: "MEDIUM"`, risk_flag mentions border/customs → include in warnings
- `risk_level: "HIGH"` → flag strongly; recommend against using without a fresh quote

**Recommended mode selection:**
Rank valid (non-stale) freight options by:
1. Lowest `grand_total_usd` among LOW-risk valid options
2. SEA is preferred for its balance of cost and reliability
3. If only HIGH-risk options are valid, recommend the cheapest valid option but flag it

### 2. Quote Preparation (EXW Only, No Freight)

Use this workflow when the prompt explicitly states no destination or EXW-only (e.g., train_002).

**Step-by-step:**

1. Fetch the RFQ by ID from `/api/rfqs/{rfq_id}` to confirm the `customer_id` and line items.
2. Fetch the customer from `/api/customers/{customer_id}`. Note the account type (new/existing NGO, commercial).
3. For each line item in the RFQ, fetch the product from `/api/products/{product_code}`. Use the product's base unit price (no tier matching unless the product has tiers — check product structure).
4. Each line item gets its own `unit_price`, `lead_time_days`, `shelf_life_months`, and `line_total = unit_price × quantity`.
5. Sum all `line_total` values for the `grand_total`.
6. Fetch the policy from `/api/policies/{policy_id}` for `payment_terms`, `offer_validity_days`, and `who_documentation_required`.
7. Set `freight_excluded: true` and `quote_basis: "EXW_ONLY"`.

**Payment terms mapping by account type:**
- New NGO account → `PREPAY_100`
- Recurring/established NGO → `NET_30_AFTER_PO` (from policy)
- Commercial → as defined in customer policy

**Offer validity:** Use the `offer_validity_days` from the customer's policy record. Default to 30 if not specified.

### 3. Account Reconciliation

Use this workflow when the prompt asks to reconcile an opportunity/invoice/payment/revenue state (e.g., train_003, train_005).

**Step-by-step:**

1. Fetch the opportunity from `/api/opportunities/{opportunity_id}`. Record `stage`, `won_amount`, linked milestones, and contact.
2. Fetch the customer from `/api/customers/{customer_id}`.
3. For each milestone linked to the opportunity, fetch its invoice from `/api/invoices/{invoice_id_or_milestone_id}`.
4. For each invoice, fetch payments from `/api/payments` (filter by invoice or milestone).
5. Sum paid amounts per milestone. Determine `payment_status`:
   - Fully paid → `PAID`
   - Partially paid → `PARTIAL`
   - Nothing paid → `UNPAID`
6. For each paid milestone, check `/api/revenue-journals` for a journal entry linked to that milestone. Determine `revenue_recognition_status` / `recognition_status`:
   - PAID + journal exists → `RECOGNIZED`
   - PAID + no journal → `MISSING_REVENUE_JOURNAL` or `REQUIRED_MISSING`
   - UNPAID → `NOT_REQUIRED_UNPAID`
7. Validate that the sum of milestone invoice totals equals `won_amount` (`opportunity_matches_milestones` or `opportunity_matches_phase_total`).
8. Compute `outstanding_balance = sum(amount_unpaid)` or `won_amount - total_paid_amount`.
9. Determine revenue recognition status:
   - All paid milestones recognized → `COMPLETE_FOR_PAID_MILESTONES`
   - Some paid milestones missing journals → `MISSING_FOR_PAID_MILESTONES`
   - No paid milestones → `NOT_REQUIRED`
10. Determine accounting action:
    - If any PAID milestone has `MISSING_REVENUE_JOURNAL` → `RECORD_REVENUE_MS{id}` for the first such milestone
    - If all paid milestones recognized but nothing new to record → `VERIFY_REVENUE_ONLY`
    - If no paid milestones → `NO_ACCOUNTING_ACTION`
11. Determine collection action:
    - If any invoice is OPEN/UNPAID with a future due date → `MONITOR_UNPAID_NOT_DUE`
    - If any invoice is OPEN/UNPAID with a past due date → `SEND_COLLECTION_NOTICE`
    - If all paid → `NO_COLLECTION_ACTION`

**Revenue journal query pattern:**
When checking whether a milestone has a recognized revenue journal entry, look for a journal record whose `milestone_id` matches. The API list endpoint for revenue journals can be filtered by iterating the full list and matching on `milestone_id`.

### 4. Engagement Management (Events and Vouchers)

Use this workflow when the prompt references events, vouchers, or briefing invitations (e.g., train_003, train_005).

**Step-by-step:**

1. Fetch the event from `/api/events/{event_id}`. Record `status`, `event_date`, and linked `voucher_code`.
2. Fetch the voucher from `/api/vouchers/{voucher_code}`. Record `status`, `discount_amount`, and `max_uses`.
3. Determine invite action:
   - Event `SCHEDULED` and voucher `ACTIVE` → `SEND_BRIEFING_INVITE`
   - Event `ACTIVE` or `COMPLETED`, invite already sent → `VERIFY_INVITE_SENT`
   - Event `CANCELLED` or no event → `NO_INVITE_ACTION`
4. Build the invite task with `event_id`, `voucher_code`, `owner_queue` (typically `ACCOUNT_MANAGEMENT`), and the primary contact.

**Voucher status validation:**
- `ACTIVE` → voucher can be sent
- `DRAFT` → voucher not ready; flag for review
- `EXPIRED` → do not send; flag for renewal
- `DISABLED` → do not send

## Output Construction

### General Rules

- Return **only valid JSON** — no markdown fences, no explanatory text outside the JSON structure.
- Match the exact structure of the provided `answer_template.json` file from the task's `input/payloads/` directory. Fill every field; leave no placeholder values.
- Use **ISO 8601 dates** (`YYYY-MM-DD`).
- Use **numeric values** for money fields (floats with two decimal places, e.g., `42480.00` or `2420.00`).
- Use **enum values exactly** as declared in the template's `enum:` annotations.
- Record IDs (`customer_id`, `quote_id`, `freight_id`, `event_id`, etc.) must match the values returned by the API exactly.
- Boolean fields must be JSON `true` or `false` (not strings).

### Field Name Adaptation

Templates may use slightly different field names for the same concept. Map API response fields to template fields by semantic match:
- `invoice.state` → template may call it `invoice_state` or `payment_status`
- `won_amount` → may be `won_amount` or `phase_total_amount`
- `freight_reconfirmation_required` → may be a policy-level or quote-level flag
- Revenue journal presence → `recognition_status`, `revenue_recognition_status`, or `recognition_status` depending on template

Always read the template's `enum:` annotations and field descriptions to understand which API fields map where.

### Common Computations

| Computation | Formula |
|-------------|---------|
| EXW line total | `unit_price × quantity` |
| Grand total (with freight) | `exw_total + freight_cost` |
| Grand total (multi-line) | `sum(line_total)` |
| Outstanding balance | `won_amount - sum(paid_amounts)` or `sum(unpaid_invoice_totals)` |
| Recognized amount | `sum(journal_entry_amounts_for_paid_milestones)` |
| Opportunity/milestone match | `won_amount == sum(milestone_invoice_totals)` |

### Warning and Flag Generation

When constructing `client_warnings` or equivalent sections:
- **Stale freight:** If any freight `valid_until` < `quote_date`, set the stale flag to `true` and include a warning message identifying the stale freight ID, its expiry date, and the risk concern.
- **High-risk route:** If any freight has `risk_level: "HIGH"` or `customs_border_risk: "HIGH"`, include a warning that the route should not be used without a fresh quote.
- **Missing revenue journal:** If any PAID milestone lacks a revenue journal entry, flag `MISSING_REVENUE_JOURNAL` and generate a `RECORD_REVENUE` accounting action.
- **Freight reconfirmation:** If the policy or context requires `freight_reconfirmation_required: true`, include this in output flags and note that rates require reconfirmation at final order.

## Error Handling

- If an API endpoint returns a 404, verify the ID is correct. Check the list endpoint for similarly named entities.
- If a product lacks a catalog tier for the requested quantity, report the available tiers and flag the mismatch.
- If an expected linked entity (freight, policy, event) is missing, note it in the output warnings and use sensible defaults where possible.
- If the API base URL is unreachable, retry once after 2 seconds, then report the failure.

## Task Recognition

This skill applies when the prompt mentions any of:
- MedBridge Sales Ops API
- `<TASK_ENV_BASE_URL>` or `BASE_URL` with MedBridge context
- Quote preparation, RFQ pricing, or freight comparison
- Account reconciliation, opportunity review, or revenue recognition
- MedBridge customer engagement, events, or voucher management
- Entity IDs matching patterns like `Q-TR-*`, `RFQ-TR-*`, `OPP-TR-*`, `CUST-*`, `FR-*`, `EVT-*`

When recognized, follow the workflow that best matches the prompt's request: quote preparation (with or without freight), account reconciliation, or engagement management. Read the supplied `answer_template.json` carefully and map every field from the API responses using the business rules above.
