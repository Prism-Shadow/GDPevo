---
name: medbridge-sales-ops
description: >-
  Reusable skill for MedBridge Sales Ops API workflows: quote decision packages,
  indicative RFQ quotes, account reconciliations, and engagement reconciliations.
  Covers data verification, pricing, freight, policy checks, revenue recognition,
  milestone tracking, event/voucher handling, and controlled JSON outputs.
---

# MedBridge Sales Ops – Reusable Operating Rules

## 1. API Configuration

- **Base URL**: Provided by the runner as `<TASK_ENV_BASE_URL>`.
- **Auth**: No credentials required for the read-only endpoints listed below.
- **Method**: All endpoints are `GET` only. No mutation endpoints are available.

### Available Endpoints

| Resource | List | By ID |
|---|---|---|
| API root | `GET /api` | — |
| Search | `GET /api/search` | — |
| Customers | `GET /api/customers` | `GET /api/customers/{id}` |
| Products | `GET /api/products` | `GET /api/products/{code}` |
| RFQs | `GET /api/rfqs` | `GET /api/rfqs/{id}` |
| Quotes | `GET /api/quotes` | `GET /api/quotes/{id}` |
| Freight Quotes | `GET /api/freight-quotes` | `GET /api/freight-quotes/{id}` |
| Policies | `GET /api/policies` | `GET /api/policies/{id}` |
| Opportunities | `GET /api/opportunities` | `GET /api/opportunities/{id}` |
| Invoices | `GET /api/invoices` | `GET /api/invoices/{id}` |
| Payments | `GET /api/payments` | `GET /api/payments/{id}` |
| Revenue Journals | `GET /api/revenue-journals` | `GET /api/revenue-journals/{id}` |
| Events | `GET /api/events` | `GET /api/events/{id}` |
| Vouchers | `GET /api/vouchers/{code}` | — |

## 2. Task Classification

Read the prompt and classify into one of four task types before fetching data:

### Type A – Quote Decision Package
**Triggers**: Prompt mentions "quote" (not RFQ), "freight options", "transport comparison", "decision package".
**Scope**: Verify customer, quote, product/catalog tier, freight records, policies. Return EXW pricing, freight comparison, risk flags, recommended mode, payment terms.

### Type B – Indicative RFQ Quote (EXW Only)
**Triggers**: Prompt mentions "RFQ", "EXW only", "freight excluded", "module level only".
**Scope**: Verify RFQ, customer, product catalog, policies. Return EXW line items only. Do NOT include freight. Keep at requested module/product level even if the API returns component details.

### Type C – Account Reconciliation
**Triggers**: Prompt mentions "reconciliation", "opportunity" (without "engagement"), "milestone invoices", "revenue recognition", "voucher".
**Scope**: Verify opportunity, customer, invoices, payments, revenue journals, events, vouchers. Return account status, milestones, revenue recognition state, event/voucher info, follow-up tasks.

### Type D – Engagement Reconciliation
**Triggers**: Prompt mentions "engagement reconciliation", "milestone", "invoice actions", "event actions", "briefing".
**Scope**: Verify opportunity, customer, milestones, invoices, payments, revenue journals, events, vouchers. Return engagement reconciliation, invoice/accounting actions, collection tasks, event/invite actions.

## 3. Data Verification Protocol

For every task, **fetch all relevant records from the API before constructing the answer**. Never assume values; always read from API responses.

1. Parse record IDs from the prompt (quote ID, RFQ ID, customer ID, opportunity ID, event ID, voucher code).
2. Fetch the identifying record first, then use linked fields to discover related records.
3. Cross-reference: verify that linked IDs (customer on quote, opportunity on invoice, etc.) are consistent.
4. Fetch policy records using the customer or quote's linked policy ID.

### Endpoint Discovery

- If the prompt provides a quote ID (e.g., `Q-TR-WC-1187`), fetch `/api/quotes/{id}` first.
- If the prompt provides an RFQ ID (e.g., `RFQ-TR-IEHK-204`), fetch `/api/rfqs/{id}` first.
- If the prompt provides an opportunity ID (e.g., `OPP-TR-HELIOS`), fetch `/api/opportunities/{id}` first.
- Customer IDs typically follow the pattern `CUST-XXXX`; fetch `/api/customers/{id}`.
- Product codes (e.g., `WC-KIT-A`, `LD-REAGENT-44`, `IEHK`) are fetched from `/api/products/{code}`.

## 4. Domain Rules

### Pricing

- **Quote basis**: Always EXW (Ex Works) unless explicitly stated otherwise.
- **EXW total** = `unit_price_usd × confirmed_quantity`.
- **Catalog tiers**: Products may have quantity-based tier pricing. Match the confirmed quantity to the correct `min_quantity`/`max_quantity` range to get `unit_price_usd`, `lead_time_days`, and `shelf_life_months`.
- **Line total** (Type B) = `unit_price × quantity`.
- **Grand total** (Types A, B, D) = sum of all line totals, or EXW total for single-item quotes. For Type A, grand total per freight option = `exw_total_usd + freight_cost_usd`.

### Freight

- Fetch all freight quotes linked to the quote or customer.
- Common modes: `AIR`, `SEA`, `ROAD`.
- **Validity check**: Compare `valid_until` to the quote date. If `valid_until < quote_date`, the freight quote is stale/invalid.
- **Risk levels**: `LOW` by default. `ROAD` mode may carry `MEDIUM` risk with `MEDIUM_BORDER_RISK` flag.
- **Reconfirmation**: Mark `freight_reconfirmation_required: true` if any freight option is stale on the quote date or if policy dictates it.
- For Type B (RFQ EXW-only), set `freight_excluded: true` and do NOT include freight options.

### Policies

- Fetch `/api/policies/{id}` for the customer or quote's policy.
- Extract: `payment_terms`, `quote_basis`, `offer_validity_days`, `freight_reconfirmation_required`, `who_documentation_required`.
- Payment terms common values: `PREPAY_100`, `NET_30`, `NET_60`, etc.

### Opportunities & Milestones

- **Stages**: `WON`, `OPEN`, `LOST`.
- **Milestone phases**: Typically `MS1`, `MS2`, `MS3`. Sum milestone amounts and compare to `won_amount` for `opportunity_matches_milestones` or `opportunity_matches_phase_total`.
- Outstanding balance = sum of unpaid amounts across milestones.

### Invoices & Payments

- **Invoice states**: `PAID`, `OPEN`, `VOID`, `UNKNOWN`.
- **Payment states**: `PAID`, `PARTIAL`, `UNPAID`, `UNKNOWN`.
- Determine payment state per milestone by comparing `invoice_total` to `amount_paid` or checking payment records.
- For each paid milestone, check if a corresponding revenue journal entry exists.

### Revenue Recognition

- **Recognition status per milestone**:
  - `RECOGNIZED` → revenue journal entry exists for the milestone.
  - `MISSING_REVENUE_JOURNAL` → milestone is paid but no revenue journal entry exists.
  - `NOT_REQUIRED_UNPAID` → milestone is unpaid, no recognition required.
  - `UNKNOWN` → cannot determine.
- **Overall status**:
  - `COMPLETE_FOR_PAID_MILESTONES` → all paid milestones have recognition entries.
  - `MISSING_FOR_PAID_MILESTONES` → at least one paid milestone lacks a recognition entry.
  - `NOT_REQUIRED` → no milestones are paid.

### Events & Vouchers

- Fetch `/api/events/{id}` for the linked event.
- Fetch `/api/vouchers/{code}` for the linked voucher.
- **Event statuses**: `SCHEDULED`, `ACTIVE`, `COMPLETED`, `CANCELLED`, `UNKNOWN`.
- **Voucher statuses**: `ACTIVE`, `DRAFT`, `EXPIRED`, `DISABLED`, `UNKNOWN`.

### Contacts

- Verify the contact name from the prompt matches the contact linked to the customer/opportunity in the API.
- Use the contact for follow-up task assignments.

## 5. Answer Construction

### Output Format

- **Return only valid JSON.** No markdown fences, no explanatory text outside the JSON object.
- Match the structure of the provided `answer_template.json` exactly.
- Use the controlled enum values declared in the template (do not invent new statuses).

### Number Formatting

- All monetary values: USD with exactly 2 decimal places (e.g., `1250.00`).
- Quantities: integers.
- Use numbers, not strings, for numeric fields.

### Date Formatting

- All dates: ISO 8601 `YYYY-MM-DD` format.
- Use `null` (not the string `"null"`) for absent dates.

### ID Stability

- Use the exact record IDs returned by the API. Do not truncate, transform, or guess IDs.

### Action Enums (Type D)

- **`primary_accounting_action`**: `RECORD_REVENUE_MS2`, `VERIFY_REVENUE_ONLY`, `NO_ACCOUNTING_ACTION`.
- **`collection_action`**: `MONITOR_UNPAID_NOT_DUE`, `SEND_COLLECTION_NOTICE`, `NO_COLLECTION_ACTION`.
- **`invite_action`**: `SEND_BRIEFING_INVITE`, `VERIFY_INVITE_SENT`, `NO_INVITE_ACTION`.
- **Owner queues**: `ACCOUNTING`, `ACCOUNT_MANAGEMENT`, `COLLECTIONS`, `EVENTS`, `NONE`.
- **Debit accounts**: `DEFERRED_REVENUE`, `ACCOUNTS_RECEIVABLE`, `CASH`, `NONE`.
- **Credit accounts**: `IMPLEMENTATION_SERVICES_REVENUE`, `DEFERRED_REVENUE`, `ACCOUNTS_RECEIVABLE`, `NONE`.

### Follow-Up Tasks (Type C)

- **Task types**: `COLLECTION`, `EVENT_INVITATION`.
- **Next actions**: `COLLECT_UNPAID_MILESTONE`, `SEND_EVENT_INVITATION`.
- Assign `COLLECTION` tasks for milestones with unpaid amounts past due.
- Assign `EVENT_INVITATION` tasks when an event and voucher exist.

## 6. Workflow Summary

1. **Classify** the task type from the prompt (A, B, C, or D).
2. **Extract** all record IDs from the prompt text.
3. **Fetch** the primary record, then cascade to linked records (customer, product, freight, policies, invoices, payments, journals, events, vouchers).
4. **Cross-reference** all linked IDs for consistency.
5. **Compute** financial values: EXW totals, grand totals, outstanding balances, recognition state.
6. **Determine** flags: validity, risk, reconfirmation requirements.
7. **Populate** the answer template JSON with stable API values, computed numbers, and controlled enums.
8. **Output** only the completed JSON.
