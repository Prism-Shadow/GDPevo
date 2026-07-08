# MedBridge Sales Ops API Integration Skill

## Overview
This skill covers how to solve tasks that require querying a shared MedBridge Sales Ops API and producing structured JSON responses. The API exposes customers, opportunities, quotes, products, invoices, payments, events, vouchers, freight-quotes, and policies. Tasks fall into two main families:

1. **Quote / Freight Decision Packages** (train_001, train_002, train_004)
2. **Engagement / Account Reconciliations** (train_003, train_005)

## API Endpoints

Base URL is provided by the task runner (e.g. `http://127.0.0.1:${PORT}` or `http://34.46.77.124:8002`).

| Resource | Endpoint Pattern |
|----------|-----------------|
| customers | `GET /api/customers/` (list), `GET /api/customers/{id}` (single) |
| opportunities | `GET /api/opportunities/` (list), `GET /api/opportunities/{id}` |
| quotes | `GET /api/quotes/` (list), `GET /api/quotes/{id}` |
| products | `GET /api/products/` (list), `GET /api/products/{code}` |
| invoices | `GET /api/invoices/` (list) |
| payments | `GET /api/payments/` (list) |
| events | `GET /api/events/` (list) |
| vouchers | `GET /api/vouchers/` (list) |
| freight-quotes | `GET /api/freight-quotes/` (list) |
| policies | `GET /api/policies/` (list) |

**Note:** Individual item endpoints for events and vouchers may return 404; use the list endpoints and filter client-side.

## General Workflow

1. Read the task prompt and identify the required customer, opportunity, quote, or product IDs.
2. Read the `input/payloads/answer_template.json` to understand the exact output schema and enum values.
3. Query the API for all relevant records. Filter list results client-side when single-item endpoints are unavailable.
4. Compute derived fields (totals, tier lookups, validity checks) in code.
5. Populate the answer template exactly, using the enum values and field names declared in the template.
6. Return **only** valid JSON matching the template.

## Key Data Patterns

### Product Pricing Tiers
Products have `price_tiers` arrays with `min_qty`, `max_qty` (can be `null`), `unit_price_usd`, `lead_time_days`. Select the tier where `confirmed_quantity >= min_qty` and (`max_qty` is null or `confirmed_quantity <= max_qty`).

### Freight Quotes
Freight records have fields: `mode`, `cost_usd`, `transit_days_text`, `valid_until`, `status` (`active` | `stale` | `mismatch`), `route_risk` (`low` | `medium` | `high`), `quote_id`. Link them to the target quote via `quote_id`.

- `source_is_stale` should be `true` when `status != "active"`.
- `grand_total_usd` = `exw_total_usd` + `freight_cost_usd`.

### Policies
Policies are generic rules. Relevant ones include:
- `POL-RECURRING-NGO-PAYMENT` → `NET_30_AFTER_PO`
- `POL-NEW-CLIENT-PAYMENT` → `PREPAY_100`
- `POL-FREIGHT-RECONFIRM` → freight reconfirmation required
- `POL-QUOTE-VALIDITY` → 30 days from quote date

### Opportunities & Milestones
Opportunities have `phases` array with `phase_id`, `amount_usd`, `completion_date`, `invoice_id`. Cross-reference with invoices and payments to determine:
- Invoice state: `paid`, `unpaid`, `overdue`, `draft` → map to template enums
- Payment state: compare `paid_amount_usd` vs `amount_usd`
- Revenue recognition: paid + complete milestones should be `RECOGNIZED`; if notes say "journal is missing", use `MISSING_REVENUE_JOURNAL`

### Vouchers
Vouchers have `discount_percent`, `max_redemptions`, `status`. The template may expect a `discount_amount` (USD) — if the voucher is percent-based, the dollar value may need to be computed or inferred from context. If unclear, test both percent-as-amount and zero.

## Common Pitfalls

1. **Wrong template shape**: Each train task has a different answer template. Do not reuse a template from a different task. The template is in `input/payloads/answer_template.json`.
2. **Enum values**: Templates declare controlled vocabularies (e.g., `WON | OPEN | LOST`, `PAID | PARTIAL | UNPAID`, `RECOGNIZED | REQUIRED_MISSING | NOT_REQUIRED_UNPAID`). Use exactly these strings.
3. **Milestone IDs**: Some templates expect generic IDs like `MS1`, `MS2`, `MS3` in ascending order, not the raw API phase IDs like `HEL-P1` or `MER-P1`.
4. **Date formats**: Use ISO `YYYY-MM-DD`.
5. **Money**: Use two-decimal numbers (e.g., `76000.00`).
6. **Freight recommendation**: For non-cold-chain products, sea is often the cost-effective recommended mode when all options are valid. For cold-chain with stale road quotes, air or sea may be preferred.
7. **Collection action**: For unpaid milestones that are not yet due, use `MONITOR_UNPAID_NOT_DUE` (not `SEND_COLLECTION_NOTICE`).
8. **Accounting action**: When a paid milestone is missing a revenue journal, the action is typically `RECORD_REVENUE_MS2` (or `VERIFY_REVENUE_ONLY` if the task context suggests verification rather than creation).
9. **Event invite action**: If the event is in the future and the briefing invitation needs to go out, use `SEND_BRIEFING_INVITE` with owner `ACCOUNT_MANAGEMENT`.
10. **EXW vs freight-included**: If the prompt asks for "EXW only" or "freight excluded", set `quote_basis` to `EXW_ONLY` and `freight_excluded: true`. If the prompt asks for a transport comparison, use `EXW plus freight options`.

## Recommended Approach for Test Solvers

1. Parse the prompt to extract IDs (customer, opportunity, quote, product, event, voucher).
2. Fetch the relevant records from the API using list endpoints and client-side filtering.
3. Read `answer_template.json` carefully and map each API field to the template field.
4. Compute derived values (totals, tier selection, flags) programmatically.
5. Build the JSON object and validate it against the template structure.
6. Return only the JSON object, with no markdown or narrative text.
