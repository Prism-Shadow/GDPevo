# Skill: MedBridge Sales Ops API Data Reconciliation

## Environment Overview

The remote environment is a **MedBridge Sales Ops** service exposing a REST API. It stores CRM, quote, logistics, and milestone engagement data across multiple linked collections.

### Base URL
- `http://<host>:8002`
- Health check: `GET /health`
- API info: `GET /api` (lists all collections and endpoints)

### Key Collections

| Collection | Endpoint | Purpose |
|---|---|---|
| `opportunities` | `GET /api/opportunities` | Sales opportunities with phases, amounts, stage, contact |
| `invoices` | `GET /api/invoices` | Invoice records per phase with `amount_usd`, `paid_amount_usd`, `outstanding_amount_usd`, `status` |
| `payments` | `GET /api/payments` | Payment records linked to invoices |
| `revenue-journals` | `GET /api/revenue-journals` | Revenue recognition journal entries per phase |
| `events` | `GET /api/events` | Customer events linked to opportunities |
| `vouchers` | `GET /api/vouchers` | Event voucher codes with `discount_percent`, `max_redemptions`, `status` |
| `customers` | `GET /api/customers` | Customer records with nested `contacts` array |
| `quotes`, `rfqs`, `freight-quotes`, `products`, `policies` | Their respective endpoints | Quote and logistics data |

All collections support `GET /<collection>/<id>` for single-record lookup. There is also `GET /api/search?q=<text>` for cross-collection search.

## Data Model Relationships

- **Opportunity** → has many **phases** (each with `phase_id`, `amount_usd`, `invoice_id`)
- **Phase** → linked to one **invoice** (via `invoice_id`)
- **Invoice** → linked to **payments** (via `invoice_id`) and **revenue-journals** (via `invoice_id`)
- **Opportunity** → linked to **events** (via `opportunity_id`)
- **Event** → linked to **voucher** (via `voucher_code`)
- **Customer** → has nested `contacts` array with `name`, `email`, `phone`, `role`

## Field Mapping Rules

When populating answer templates, map API fields to template fields carefully:

| Template Field | API Source | Notes |
|---|---|---|
| `won_amount` | `opportunity.won_amount_usd` | Use exact value; validate it equals sum of phase amounts |
| `outstanding_amount` / `outstanding_balance` | `opportunity.outstanding_amount_usd` or computed from invoices | Use two decimals |
| `total_paid_amount` | Sum of `invoice.paid_amount_usd` or sum of `payment.amount_usd` for the opportunity | Cross-check both sources |
| `phase_total_amount` | Sum of `phase.amount_usd` across all phases | Should match `won_amount` |
| `currency` | `opportunity.currency` | Usually `"USD"` |
| `contact` | `opportunity.contact` | Primary contact name string |
| `customer_name` | `customer.name` | Look up via `customer_id` |

### Status Translations

API statuses often differ from template enum values. Map them explicitly:

| API Status | Template Enum | Context |
|---|---|---|
| `closed_won` | `WON` | `stage` field |
| `proposal`, `negotiation` | `OPEN` | `stage` field |
| `paid` | `PAID` | `invoice_state` |
| `unpaid` | `OPEN` | `invoice_state` |
| `overdue` | `OPEN` | `invoice_state` (still unpaid) |
| `draft` | `VOID` or `UNKNOWN` | `invoice_state` (use judgment) |
| `live` | `ACTIVE` | `event_status` |
| `confirmed` | `SCHEDULED` | `event_status` |
| `scheduled` | `SCHEDULED` | `event_status` |
| `completed` | `COMPLETED` | `event_status` |
| `tentative` | `UNKNOWN` | `event_status` |

## Financial Computations

### Opportunity Reconciliation
1. **Phase total**: Sum `phase.amount_usd` for all phases on the opportunity.
2. **Opportunity match**: `won_amount` should equal phase total (within rounding). Set `opportunity_matches_phase_total` accordingly.
3. **Total paid**: Sum all `paid_amount_usd` from invoices for this opportunity, OR sum all `amount_usd` from payments for this opportunity. Both should agree.
4. **Outstanding balance**: `won_amount` − `total_paid_amount`, OR use `opportunity.outstanding_amount_usd`. Cross-check.

### Milestone State Derivation
For each phase/milestone:
1. Find the linked **invoice** by `invoice_id`.
2. Find all **payments** for that `invoice_id`.
3. Find the **revenue-journal** for that `invoice_id`.
4. **Invoice state**: Map `invoice.status` to template enum.
5. **Payment state**: If `invoice.paid_amount_usd` ≥ `invoice.amount_usd` → `PAID`. If 0 → `UNPAID`. If partial → `PARTIAL`.
6. **Recognition status**:
   - If milestone is paid AND complete AND a revenue-journal exists → `RECOGNIZED`
   - If milestone is paid AND complete BUT no revenue-journal exists → `MISSING_REVENUE_JOURNAL`
   - If milestone is unpaid → `NOT_REQUIRED_UNPAID`
   - Otherwise → `UNKNOWN`

### Action Determination
Based on the reconciliation, derive required actions:

**Accounting Action** (from `invoice_actions.accounting_action`):
- If any paid milestone is missing a revenue journal → `RECORD_REVENUE_MS2` (or appropriate MS#), debit `DEFERRED_REVENUE`, credit `IMPLEMENTATION_SERVICES_REVENUE`
- If all paid milestones have journals → `VERIFY_REVENUE_ONLY`
- Otherwise → `NO_ACCOUNTING_ACTION`

**Collection Action** (from `invoice_actions.collection_task`):
- If any invoice is `unpaid` and past due → `SEND_COLLECTION_NOTICE`, owner `COLLECTIONS`
- If unpaid but not yet due → `MONITOR_UNPAID_NOT_DUE`, owner `ACCOUNT_MANAGEMENT`
- Otherwise → `NO_COLLECTION_ACTION`

**Event Invite Action** (from `event_actions.invite_task`):
- If event is `ACTIVE` or `SCHEDULED` and invite has not been verified → `SEND_BRIEFING_INVITE`, owner `EVENTS`
- If event is `COMPLETED` → `VERIFY_INVITE_SENT` or `NO_INVITE_ACTION`
- For `UNKNOWN`/`CANCELLED` → `NO_INVITE_ACTION`

## Voucher Handling

Vouchers in the API have `discount_percent` and `max_redemptions`.
The answer template expects `discount_amount` (USD, two decimals).

- If `discount_percent` is 100 and there is no explicit ticket price, `discount_amount` may be equal to `discount_percent` (treated as a percentage value) or computed from a known event ticket price if available.
- `max_uses` maps directly from `max_redemptions`.
- `voucher_status` maps from API `status` (`active` → `ACTIVE`, etc.).

## Query Strategy for Test Solvers

1. **Read the prompt** to identify the target record(s) and required output fields.
2. **Query `/api`** to discover available collections and endpoints.
3. **Fetch the primary collection** (e.g., `/api/opportunities` or `/api/opportunities/<id>`).
4. **Identify the correct record** by the criteria in the prompt (ID, amount, stage, etc.). If the prompt references an ID that does not exist verbatim, look for records with matching data patterns (e.g., similar index in list, matching won_amount, or matching customer context).
5. **Fetch all related collections** needed for the answer template:
   - Invoices, payments, revenue-journals for financial reconciliation
   - Events and vouchers for event actions
   - Customers for contact names and customer names
6. **Map and translate** all API fields to the template fields using the rules above.
7. **Compute derived values** (sums, comparisons, states, actions) precisely.
8. **Validate enum values** against the answer template descriptions before returning.

## Common Pitfalls

- Using raw API statuses without translating to template enums.
- Forgetting to cross-check `won_amount` against phase totals.
- Using `invoice.status` directly as `invoice_state` without mapping `unpaid`/`overdue` to `OPEN`.
- Missing the revenue-journal lookup when determining `recognition_status`.
- Returning `discount_percent` instead of `discount_amount` for vouchers.
- Omitting two-decimal precision on all currency fields.
- Using `closed_won` instead of `WON` for the `stage` enum.
