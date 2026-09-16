# MedBridge Business Rules

## Price Tier Selection

Given a product and a confirmed quantity Q:

1. Iterate through `product.price_tiers` in order.
2. Select the first tier where `tier.min_qty <= Q` and (`tier.max_qty` is `null` or `Q <= tier.max_qty`).
3. From that tier, extract: `unit_price_usd`, `lead_time_days`, `shelf_life_months`.

Do not use `prior_unit_price_usd` from a quote line item — always use the current catalog tier matched to the confirmed quantity.

## EXW Total

`exw_total_usd = confirmed_quantity * unit_price_usd`

Use two-decimal precision.

## Freight Option Construction

For each freight record with `quote_id` matching the target quote:

1. **Filter out** records where `status` is `stale` or `mismatch`, or where `quote_id` does not match.
2. **Determine validity:** `validity_status = "VALID"` if `valid_until >= quote_date`, otherwise `"STALE"`. `source_is_stale = true` when stale.
3. **Compute grand total:** `grand_total_usd = exw_total_usd + freight.cost_usd`.
4. **Risk mapping:** Uppercase `route_risk`: `"low"` -> `"LOW"`, `"medium"` -> `"MEDIUM"`, `"high"` -> `"HIGH"`. For `risk_flag`, use route_risk plus any specific flagged concern from `risk_notes`.
5. Collect exactly the modes present in the template (typically AIR, SEA, ROAD).

## Freight Mode Recommendation

Recommend the mode with the lowest freight cost among **valid** (non-stale) options, unless:
- The customer grant_terms or notes require speed (then prefer AIR).
- A valid option has `route_risk: "high"` — flag it and do not recommend it.
- Default: lowest-cost valid option.

## Payment Terms Resolution

1. If the customer `segment` is `new_ngo` and `is_recurring` is `false`: `PREPAY_100`.
2. If the customer `segment` is `recurring_ngo`: use the customer's `payment_profile` (e.g., `NET_30_AFTER_PO`).
3. If the customer `segment` is `recurring_commercial`: use the customer's `payment_profile` (e.g., `NET_30_AFTER_PO`).
4. Policy `POL-FREIGHT-RECONFIRM` always applies: `freight_reconfirmation_required = true` whenever freight options are included.

## EXW-Only (No Freight) Conditions

- No destination confirmed (e.g., "Destination pending donor allocation").
- RFQ `incoterm_requested` is `"EXW"` and the prompt says no freight.
- Policy `POL-INDICATIVE-EXW` applies: quote must be EXW only, freight excluded.

## Module-Level Quoting

- For module RFQs (request_type contains `module`), quote at the module product code level.
- Do **not** split modules into their `components` for separate line items.
- Use `requested_modules[].product_code` and `requested_modules[].quantity` directly.

## Quote Offer Validity

- Standard catalog quote pricing is valid for 30 calendar days from `quote_date` (per POL-QUOTE-VALIDITY).
- `offer_validity_days = 30` on indicative quotes.
- Freight validity may expire sooner, governed by each freight record's `valid_until`.

## WHO Documentation

When quoting emergency health kits (IEHK), cholera response modules, or field clinic bundles: `who_documentation_required = true`.

## Milestone Reconciliation

### Matching Check
Sum `opportunity.phases[].amount_usd` and compare to `opportunity.won_amount_usd`. If equal, `opportunity_matches_milestones = true`.

### Invoice Payment State
For each phase, look up the invoice by `phase.invoice_id`:
- `invoice.status`: `"paid"` -> PAID, `"unpaid"` -> UNPAID, `"overdue"` -> UNPAID (overdue), `"draft"` -> UNPAID.
- `paid_amount = invoice.paid_amount_usd`.
- `unpaid_amount = invoice.outstanding_amount_usd`.

### Revenue Recognition
For each paid invoice:
- If a revenue journal exists for that `phase_id` or `invoice_id`: `RECOGNIZED`.
- If paid but no revenue journal exists: `MISSING_REVENUE_JOURNAL`.
- If unpaid: `NOT_REQUIRED_UNPAID`.

### Revenue Recognition Summary
- If every paid milestone has a journal: `COMPLETE_FOR_PAID_MILESTONES`.
- If any paid milestone lacks a journal: `MISSING_FOR_PAID_MILESTONES`.
- If no paid milestones: `NOT_REQUIRED`.

### Outstanding Balance
Sum of `invoice.outstanding_amount_usd` across all opportunity invoices.

### Accounting Action
When a paid milestone lacks a revenue journal:
- `action`: `RECORD_REVENUE_MS<N>` (where N is the milestone number).
- `debit_account`: `DEFERRED_REVENUE`.
- `credit_account`: `IMPLEMENTATION_SERVICES_REVENUE`.
- `owner_queue`: `ACCOUNTING`.

### Collection Task
When an invoice is unpaid:
- If `due_date` is in the future relative to the business date: `MONITOR_UNPAID_NOT_DUE`.
- If `due_date` is past: `SEND_COLLECTION_NOTICE`.
- `owner_queue`: `ACCOUNT_MANAGEMENT` for monitoring, `COLLECTIONS` for overdue.

### Event and Voucher Linking
- Look up events by `opportunity_id`.
- For each event, look up the linked voucher by `voucher_code`.
- If event status is `scheduled` or `confirmed`: invite action is `SEND_<TYPE>_INVITE`.
- Invite task `owner_queue`: `ACCOUNT_MANAGEMENT`.
- Include the voucher code and discount in the invite task.

### Follow-Up Task Due Dates
- For collection tasks: use the invoice `due_date`.
- For invitation tasks: use a date reasonably before the event (typically 7-21 days before, or the current business date if the event is sooner).
