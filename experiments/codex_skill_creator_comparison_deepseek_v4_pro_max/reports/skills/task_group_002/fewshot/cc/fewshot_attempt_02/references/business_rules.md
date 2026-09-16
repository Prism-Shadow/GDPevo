# MedBridge Business Rules

This document maps MedBridge policy data to concrete output values. Cross-reference with the live `/api/policies` response; the policy IDs and rules here match the canonical API.

## Price tier matching

Every product in `/api/products/{code}` has a `price_tiers` array. Each tier object has:
- `min_qty` (integer, inclusive lower bound)
- `max_qty` (integer or null, inclusive upper bound; null means no upper limit)
- `unit_price_usd` (float)
- `lead_time_days` (integer)

To match a confirmed quantity Q:
1. Find the tier where `min_qty <= Q` AND (`max_qty >= Q` OR `max_qty` is null).
2. Use exactly one tier. Do not interpolate or blend tiers.
3. The tier's `unit_price_usd` and `lead_time_days` are the values to use.
4. If a product has a single tier with `max_qty: null`, that tier applies at all quantities.

If the quote is a revision and a higher quantity pushes into a new tier, use the new tier's price and lead time even when the prior quote had a different unit price.

## Payment terms derivation

| Customer profile | Policy ID | Terms code |
|-----------------|-----------|------------|
| New NGO / `segment: "new_ngo"` / `payment_profile: "NEW_CLIENT_REVIEW"` | `POL-NEW-CLIENT-PAYMENT` | `PREPAY_100` |
| Recurring NGO / `segment: "recurring_ngo"` / `is_recurring: true` | `POL-RECURRING-NGO-PAYMENT` | `NET_30_AFTER_PO` |
| Recurring commercial / `segment: "recurring_commercial"` | (standard) | `NET_30_AFTER_PO` |
| Implementation services / `segment: "implementation_services"` | (per-milestone) | Determined per invoice; use `MILESTONE_BILLING` as the profile label |

The customer's `grant_terms` field may add nuance (e.g., "requires prepay until credit approved"), but the policy terms code is the primary determinant for the output field.

## EXW scope

Policy `POL-EXW-SCOPE`: EXW excludes freight, insurance, import duty, customs clearance, and last-mile handling unless explicitly added as separate options. When the quote basis is EXW, the unit price and EXW total must not include any of these costs. Freight costs are added separately as `grand_total_usd = exw_total_usd + freight_cost_usd`.

## Indicative quote scope

Policy `POL-INDICATIVE-EXW`: When an RFQ has no confirmed destination or the prompt says "EXW only" / "freight excluded," the quote must be EXW only with no freight options included. Set `freight_excluded: true` and `quote_basis: "EXW_ONLY"` (or an equivalent template value).

## Module granularity

Policy `POL-MODULE-GRANULARITY`: For module RFQs, quote at the module line level. Do not split modules into component SKUs even if the API product record lists `components`. Each `requested_modules` entry becomes one line item.

## Quote validity

Policy `POL-QUOTE-VALIDITY`: Catalog quote pricing is valid for 30 calendar days from the quote date. Use `offer_validity_days: 30` (or the equivalent template field). Freight validity may expire sooner; see the freight rules below.

## Freight validity and staleness

Each freight quote has a `valid_until` date. Compare against the quote date:
- **VALID**: `valid_until >= quote_date`. Set `validity_status: "VALID"` and `source_is_stale: false`.
- **STALE**: `valid_until < quote_date`. Set `validity_status: "STALE"` and `source_is_stale: true`. Do not recommend or rely on stale freight.

When any freight option is stale, add a `freight_warning` field (if the template has one) explaining which freight ID is expired and recommending reconfirmation.

## Freight reconfirmation

Policy `POL-FREIGHT-RECONFIRM`: All freight rates need reconfirmation at final order. Always set `freight_reconfirmation_required: true` in the output unless the task is explicitly EXW-only with no freight at all (in which case omit or set to `false`). The policy note "valid only through the freight quote valid_until date" reinforces the staleness check above.

## Route risk mapping

The freight quote's `route_risk` field uses lowercase values. Map to uppercase for the output:
| API value | Output value |
|-----------|-------------|
| `"low"` | `"LOW"` |
| `"medium"` | `"MEDIUM"` |
| `"high"` | `"HIGH"` |

When the template calls for a `risk_flag` or `customs_border_risk`, use the same mapping. Add a specific flag like `"MEDIUM_BORDER_RISK"` when `route_risk` is `"medium"` and the freight `risk_notes` mention border or customs risk.

## Recommended transport mode

Recommendation logic, in priority order:
1. If cold chain is required (`cold_chain_required: true` on the product) and an AIR freight option exists and is valid, recommend AIR.
2. If cold chain is required and no valid AIR exists but a valid SEA option with `cold_chain_support: true` exists, recommend SEA.
3. Otherwise, recommend the valid freight option with the lowest `route_risk`. Prefer SEA over ROAD when both are LOW risk. Prefer SEA over AIR for cost-sensitive non-urgent shipments.
4. Never recommend a STALE freight option.
5. When the template has a `recommended_mode` field, use the mode code: `"AIR"`, `"SEA"`, or `"ROAD"`.

## Revenue recognition

Policy `POL-REVREC`: When a milestone is complete and paid, create or verify revenue recognition from deferred revenue to income.

For each milestone (phase) linked to an invoice:
- **RECOGNIZED**: The invoice is paid AND a revenue journal exists with matching `invoice_id` and `status: "posted"`. The revenue journal's `debit_account` is `"Deferred Revenue"` and `credit_account` is `"Implementation Services Revenue"`.
- **MISSING_REVENUE_JOURNAL** / **REQUIRED_MISSING**: The invoice is paid but no revenue journal with matching `invoice_id` exists in the `/api/revenue-journals` list.
- **NOT_REQUIRED_UNPAID**: The invoice is unpaid. Revenue recognition is not yet required.

The accounting action for a missing journal:
- `action`: `"RECORD_REVENUE_MS{n}"` (where n is the milestone number)
- `debit_account`: `"DEFERRED_REVENUE"`
- `credit_account`: `"IMPLEMENTATION_SERVICES_REVENUE"`
- `amount`: the invoice's `amount_usd`
- `owner_queue`: `"ACCOUNTING"`

## Collection logic

For milestones with unpaid invoices:
- If the invoice `due_date` is in the future relative to the as-of date: `collection_action` is `"MONITOR_UNPAID_NOT_DUE"`. No collection notice yet.
- If the invoice `due_date` is on or before the as-of date (or the invoice is `"overdue"`): `collection_action` is `"SEND_COLLECTION_NOTICE"`.
- For the Helios-style template, use `next_action: "COLLECT_UNPAID_MILESTONE"` and `task_type: "COLLECTION"`.

## Event and voucher handling

For opportunity reconciliations that include an event:
- Fetch the event by ID or filter `/api/events` by `opportunity_id`.
- Fetch the voucher by `voucher_code` or filter `/api/vouchers` by `event_id`.
- Event statuses: `"scheduled"`, `"confirmed"`, `"live"`, `"completed"`, `"cancelled"`, `"tentative"`. Map to template enums as needed.
- Voucher statuses: `"active"`, `"draft"`, `"expired"`, `"disabled"`. The `discount_percent` field in the API is a percentage (e.g., `50` for 50%), but the `discount_amount` template field varies by template; check what the template expects.
- When the voucher's `discount_percent` is 100 and the template field is `voucher_discount`, use `100.00` (not 1.00).

## Follow-up task routing

Every follow-up task must include:
- The contact name from the prompt (or from the event's `primary_contact` if different)
- The linked `customer_id` and `opportunity_id`
- The specific `milestone_id` (for collection) or `event_id`/`voucher_code` (for invitations)
- An `owner_queue` of `"ACCOUNT_MANAGEMENT"` for customer-facing tasks, `"ACCOUNTING"` for revenue recognition tasks, `"COLLECTIONS"` for overdue collections

## Enum mapping quick reference

### Opportunity stage
| API `stage` | Template enum |
|------------|--------------|
| `"closed_won"` | `"WON"` |
| `"open"` | `"OPEN"` |
| `"closed_lost"` | `"LOST"` |

### Invoice / payment status to milestone state
| Invoice `status` | Payment exists | Milestone state |
|-----------------|---------------|----------------|
| `"paid"` | Yes, `amount_usd` matches | `"PAID"` / `payment_status: "PAID"` |
| `"unpaid"` | No | `"UNPAID"` / `payment_status: "UNPAID"` |
| `"overdue"` | No | `"UNPAID"` / `payment_status: "UNPAID"` |
| `"draft"` | No | `"UNPAID"` / `payment_status: "UNPAID"` |
| `"paid"` | Yes, partial only | `"PARTIAL"` / `payment_status: "PARTIAL"` |

### Freight mode ordering
Always list freight options in this order: AIR, SEA, ROAD. This is descending speed and ascending transit time.
