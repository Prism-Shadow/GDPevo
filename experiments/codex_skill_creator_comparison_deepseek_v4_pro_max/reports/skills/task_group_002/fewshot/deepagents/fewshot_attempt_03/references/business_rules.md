# MedBridge Business Rules

## Price Tier Matching

Products use quantity-based price tiers. To find the correct tier for a given quantity:

1. Iterate through `price_tiers` array.
2. Select the tier where `min_qty <= quantity <= max_qty`.
3. A `null` `max_qty` means no upper limit.
4. Use the tier's `unit_price_usd`, `lead_time_days`, and `shelf_life_months`.
5. For products with a single tier (no quantity-dependent pricing), use that tier directly regardless of quantity.

Compute `exw_total_usd` as `confirmed_quantity * unit_price_usd`, rounded to 2 decimals.

## Freight Validity and Risk

### Validity Assessment

Compare each freight quote's `valid_until` against the quote's `quote_date`:
- `valid_until >= quote_date` → VALID
- `valid_until < quote_date` → STALE; set `source_is_stale: true`

The `validity_status` field takes values `VALID` or `STALE`.

### Route Risk Mapping

Map the freight quote's `route_risk` field to standard risk levels:

| route_risk | risk_level | risk_flag | customs_border_risk |
|---|---|---|---|
| low | LOW | NONE | LOW |
| medium | MEDIUM | MEDIUM_BORDER_RISK | MEDIUM |
| high | HIGH | HIGH_BORDER_RISK | HIGH |

### Mode Recommendation

- Prefer SEA when available, valid, and low-risk (lowest cost/risk ratio).
- If SEA is stale or high-risk, prefer AIR if valid and low-risk.
- Never recommend a STALE or HIGH-risk freight option.
- Always set `freight_reconfirmation_required: true` per POL-FREIGHT-RECONFIRM.

### All Options Valid Check

`all_freight_options_valid_on_quote_date` is `true` only when every freight option has `valid_until >= quote_date`. If any option is stale, this flag is `false`.

### Grand Total Calculation

For each freight option: `grand_total_usd = exw_total_usd + freight_cost_usd`.

## Payment Term Derivation

Determine payment terms from customer record and applicable policies:

| Customer segment / type | Payment terms | Policy |
|---|---|---|
| new_ngo (first-time NGO) | PREPAY_100 | POL-NEW-CLIENT-PAYMENT |
| recurring_ngo | NET_30_AFTER_PO | POL-RECURRING-NGO-PAYMENT |
| recurring_commercial | NET_30_AFTER_PO | (standard) |
| implementation_services / milestone_billing | MILESTONE_BILLING | (per-phase) |
| Any customer with payment_profile | Use the profile value directly | |

Customer `payment_profile` values:
- `NET_30_AFTER_PO` → net 30 after purchase order
- `PREPAY_100` → 100% prepayment before production
- `NEW_CLIENT_REVIEW` → treat as PREPAY_100
- `MILESTONE_BILLING` → per-phase milestone invoicing

## Revenue Recognition Rules

Per POL-REVREC: When a milestone is complete and paid, create or verify revenue recognition from deferred revenue to income.

### Recognition Status per Milestone

| Condition | recognition_status |
|---|---|
| Invoice paid AND revenue journal exists for the invoice | RECOGNIZED |
| Invoice paid AND no revenue journal exists | MISSING_REVENUE_JOURNAL |
| Invoice unpaid | NOT_REQUIRED_UNPAID |

### Overall Recognition Status

| Condition | recognition_status |
|---|---|
| All paid milestones have revenue journals | COMPLETE_FOR_PAID_MILESTONES |
| At least one paid milestone lacks a revenue journal | MISSING_FOR_PAID_MILESTONES |
| No paid milestones exist | NOT_REQUIRED |

### Accounting Action Determination

| Condition | primary_accounting_action |
|---|---|
| Paid milestone(s) missing revenue journal | RECORD_REVENUE_MSn (target the specific milestone) |
| All paid milestones have journals | VERIFY_REVENUE_ONLY |
| No paid milestones | NO_ACCOUNTING_ACTION |

### Journal Entry Template

When recording revenue for a paid milestone:
- `action`: `RECORD_REVENUE_MSn`
- `debit_account`: `DEFERRED_REVENUE`
- `credit_account`: `IMPLEMENTATION_SERVICES_REVENUE`
- `amount`: milestone invoice amount
- `owner_queue`: `ACCOUNTING`

## Collection Task Routing

| Condition | collection_action | owner_queue |
|---|---|---|
| Unpaid and due date is in the future (not yet past due relative to as-of date) | MONITOR_UNPAID_NOT_DUE | ACCOUNT_MANAGEMENT |
| Unpaid and due date is on or before as-of date (overdue) | SEND_COLLECTION_NOTICE | COLLECTIONS |
| All paid | NO_COLLECTION_ACTION | NONE |

## Event and Voucher Linking

- Events link to opportunities via `opportunity_id` and customers via `customer_id`.
- Vouchers link to events via `event_id`; retrieve by `voucher_code`.
- Event status mapping: `scheduled`/`confirmed` → send invitation; `live` → verify sent; `completed`/`cancelled` → no action.
- Voucher `discount_percent` represents the discount amount. In templates that ask for `voucher_discount` or `discount_amount`, use the `discount_percent` value directly.
- Voucher `max_redemptions` maps to `max_uses` or `voucher_max_uses`.

### Invite Task Routing

| Event status | invite_action | owner_queue |
|---|---|---|
| scheduled, confirmed, tentative | SEND_BRIEFING_INVITE (or SEND_EVENT_INVITATION) | ACCOUNT_MANAGEMENT |
| live | VERIFY_INVITE_SENT | ACCOUNT_MANAGEMENT |
| completed, cancelled | NO_INVITE_ACTION | NONE |

## Module Quote Rules

Per POL-MODULE-GRANULARITY: Module RFQs are quoted at module line level. Do not split modules into component SKUs.

- Use the module product code from `requested_modules[].product_code`.
- Fetch each product by code for `article_number`, `unit_price_usd`, `lead_time_days`, `shelf_life_months`.
- Compute `line_total = quantity * unit_price` and sum for `grand_total`.
- Per POL-INDICATIVE-EXW: When destination is pending, quote EXW only and exclude freight.
- Per POL-QUOTE-VALIDITY: Set `offer_validity_days: 30`.

## EXW Scope

Per POL-EXW-SCOPE: EXW excludes freight, insurance, import duty, customs clearance, and last-mile handling unless explicitly added as separate options. Set `quote_basis: "EXW"` or `"EXW_ONLY"` accordingly.

## Quote Validity

Per POL-QUOTE-VALIDITY: Catalog quote pricing is valid for 30 calendar days from quote date. Freight validity may expire sooner and takes precedence.

## Stage/Milestone Count Mapping

When templates use MS1/MS2/MS3 milestone IDs, map phases in order:
- First phase → MS1
- Second phase → MS2
- Third phase → MS3

## Follow-Up Task Construction

### Collection Task Fields
- `task_type`: `COLLECTION`
- `task_title`: "Milestone N collection - Customer Name" (use the milestone number)
- `linked_customer_id`: from opportunity
- `linked_opportunity_id`: from opportunity
- `contact_name`: from opportunity or customer contacts
- `due_date`: invoice due_date
- `next_action`: `COLLECT_UNPAID_MILESTONE`
- `milestone_id`: the milestone identifier
- `amount_due`: unpaid amount

### Event Invitation Task Fields
- `task_type`: `EVENT_INVITATION`
- `task_title`: "Send event invite - Customer Name" (or event-specific title)
- `linked_customer_id`: from event/opportunity
- `linked_opportunity_id`: from event/opportunity
- `contact_name`: from event primary_contact
- `due_date`: reasonable lead time before event_date (e.g. 7-21 days prior)
- `next_action`: `SEND_EVENT_INVITATION`
- `event_id`: from event
- `voucher_code`: from event/voucher
