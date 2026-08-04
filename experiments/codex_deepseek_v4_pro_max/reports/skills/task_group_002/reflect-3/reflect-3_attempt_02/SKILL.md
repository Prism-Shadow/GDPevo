 # MedBridge Sales Ops API — Quote & Reconciliation Skill

 ## Overview

 Solve MedBridge Sales Ops API tasks that require querying a shared CRM/quote/logistics/milestone-engagement API and producing structured JSON answers from provided answer templates. The API is read-only (GET only). Every task follows the same pattern: parse the prompt, query the relevant API endpoints, extract exact values from API responses, and fill the answer template.

 ## Environment

 - Base URL: use the `<TASK_ENV_BASE_URL>` value provided by the runner (e.g. `http://task-env:9002`).
 - No credentials required.
 - All endpoints are GET-only.

 Endpoints:
 - `GET /api` — list collections
 - `GET /api/customers` / `GET /api/customers/{id}`
 - `GET /api/products` / `GET /api/products/{code}`
 - `GET /api/quotes` / `GET /api/quotes/{id}`
 - `GET /api/rfqs` / `GET /api/rfqs/{id}`
 - `GET /api/freight-quotes` / `GET /api/freight-quotes/{id}`
 - `GET /api/policies` / `GET /api/policies/{id}`
 - `GET /api/opportunities` / `GET /api/opportunities/{id}`
 - `GET /api/invoices` / `GET /api/invoices/{id}`
 - `GET /api/payments` / `GET /api/payments/{id}`
 - `GET /api/revenue-journals` / `GET /api/revenue-journals/{id}`
 - `GET /api/events` / `GET /api/events/{id}`
 - `GET /api/vouchers` / `GET /api/vouchers/{code}`
 - `GET /api/search?q={text}`

 ## General Workflow

 1. **Read the prompt** to identify the task type (quote/freight, RFQ/indicative quote, or reconciliation) and the key entities (customer IDs, quote IDs, RFQ IDs, opportunity IDs).
 2. **Read the answer template** (`input/payloads/answer_template.json`) to understand the exact JSON structure and controlled enum values expected.
 3. **Query the API** — fetch all relevant records:
    - For quote tasks: quote, customer, product, freight-quotes, policies.
    - For RFQ tasks: RFQ, customer, products, policies.
    - For reconciliation tasks: opportunity, customer, invoices, payments, revenue-journals, events, vouchers, policies.
 4. **Filter by relationship** — not all API records are relevant. Always filter by the primary entity:
    - Freight quotes: filter by `quote_id`.
    - Invoices/payments/revenue-journals/events/vouchers: filter by `opportunity_id` and `customer_id`.
 5. **Map API values to template enums** using the mapping rules below.
 6. **Output only valid JSON** matching the template. No markdown, no explanatory text.

 ## Value Mapping Rules

 ### Identifier & Date Fields

 - Use exact IDs from the API (quote ID, customer ID, product code, RFQ ID, opportunity ID, invoice IDs, event ID, voucher code).
 - Dates: always ISO `YYYY-MM-DD` format (e.g. `"2026-06-01"`).
 - Money: always two decimal places (e.g. `42480.00`). Compute line totals and grand totals from API unit prices and quantities.

 ### Customer Name

 - **Always use the `name` field from the API customer record**, never a name mentioned in the prompt. The prompt may use a colloquial name that differs from the official record.

 ### Product Catalog & Price Tiers

 - Find the correct price tier by matching `confirmed_quantity` against the tier's `min_qty`–`max_qty` range. Use `null` max_qty as unlimited upper bound.
 - Extract `unit_price_usd`, `lead_time_days`, and `shelf_life_months` from the matching tier.
 - EXW total = `confirmed_quantity × unit_price_usd`.

 ### Freight Option Fields

 - `mode`: uppercase — `"AIR"`, `"SEA"`, `"ROAD"`.
 - `risk_level`: uppercase — `"LOW"`, `"MEDIUM"`, `"HIGH"` (map from API `route_risk`: `"low"`→`"LOW"`, `"medium"`→`"MEDIUM"`, `"high"`→`"HIGH"`).
 - `risk_flag`: if `route_risk` is `"low"` and no specific concern → `"NONE"`. If medium border risk → `"MEDIUM_BORDER_RISK"`. If high stale risk → derive from `risk_notes`.
 - `validity_status`: `"valid"` when `valid_until >= quote_date`, `"stale"` when `valid_until < quote_date`.
 - `source_is_stale`: `true` when API `status` is `"stale"` or `valid_until` is before the quote date, otherwise `false`.
 - `customs_border_risk`: uppercase — `"LOW"`, `"MEDIUM"`, `"HIGH"` (from `route_risk`).
 - `grand_total_usd` = EXW total + freight_cost_usd.
 - `transit_days`: use the API `transit_days_text` verbatim.

 ### Recommended Freight Mode

 - Prefer `"SEA"` over `"AIR"` when sea freight has:
   - Sufficient shelf-life margin (product shelf life ≫ sea transit days), AND
   - Low or medium risk level, AND
   - A valid (not stale) quote, AND
   - Reefer/cold-chain support if the product requires it.
 - Choose `"AIR"` only when cold-chain urgency, very short shelf life, or high-risk sea/road routes force it.
 - Never recommend stale or high-risk freight.

 ### Freight Reconfirmation & Validity

 - `freight_reconfirmation_required`: always `true` (policy POL-FREIGHT-RECONFIRM applies to all freight quotes).
 - `all_freight_options_valid_on_quote_date`: `true` only if every freight option's `valid_until` is ≥ the quote date.
 - `road_quote_invalid_or_stale`: `true` if any road freight quote has status `"stale"` or `valid_until < quote_date`.

 ### Payment Terms

 Determine from customer type and policies:
 - **New NGO clients** (`is_recurring: false`, `customer_type: "NGO"`) → `"PREPAY_100"` (POL-NEW-CLIENT-PAYMENT).
 - **Recurring NGO clients** (`is_recurring: true`, `customer_type: "NGO"`) → `"NET_30_AFTER_PO"` (POL-RECURRING-NGO-PAYMENT), unless grant terms say otherwise.
 - **Recurring Commercial clients** → `"NET_30_AFTER_PO"` (from customer `payment_profile`).
 - Use the policy that matches the customer segment; customer `payment_profile` is the fallback.

 ### Opportunity Stage

 Map API `stage` to template enum:
 - `"closed_won"` → `"WON"`
 - `"open"` → `"OPEN"`
 - `"closed_lost"` → `"LOST"`

 ### Milestone/Phase Fields (Reconciliation)

 - `milestone_id`: use `"MS1"`, `"MS2"`, `"MS3"` in ascending order (not phase IDs like `HEL-P1`).
 - `phase_number`: 1, 2, 3 corresponding to MS1/MS2/MS3.
 - `amount`: the phase `amount_usd` from the opportunity.
 - `invoice_total`: the invoice `amount_usd` for that milestone.
 - `invoice_state`: map from invoice `status`:
   - `"paid"` → `"PAID"`
   - `"unpaid"` or `"overdue"` → `"OPEN"`
   - `"draft"` → `"OPEN"`
 - `payment_state`:
   - Fully paid (`paid_amount_usd == amount_usd`) → `"PAID"`
   - Partially paid → `"PARTIAL"`
   - No payment → `"UNPAID"`
 - `paid_amount`: total `paid_amount_usd` from the invoice or sum of payments for that milestone.
 - `amount_unpaid`: `invoice_total - amount_paid` (for reconciliation template in train_003).
 - `due_date`: the invoice `due_date`, or `null` if none.

 ### Revenue Recognition Status (Milestone Level)

 For each milestone, check the revenue-journals collection:
 - **Paid AND has a revenue journal** → `"RECOGNIZED"` (or `"RECOGNIZED"` for train_003).
 - **Paid but NO revenue journal** → `"MISSING_REVENUE_JOURNAL"` (train_005) or `"REQUIRED_MISSING"` (train_003).
 - **Unpaid** (regardless of journal) → `"NOT_REQUIRED_UNPAID"`.

 ### Revenue Recognition Summary

 - `recognition_status`:
   - All paid milestones have journals → `"COMPLETE_FOR_PAID_MILESTONES"`
   - One or more paid milestones missing journals → `"MISSING_FOR_PAID_MILESTONES"`
   - No paid milestones → `"NOT_REQUIRED"`
 - `recognized_milestones`: list of milestone IDs that have revenue journals.
 - `missing_required_milestones`: list of paid milestone IDs that lack revenue journals.
 - `recognized_amount`: sum of recognized journal amounts.

 ### Accounting Actions (train_005)

 - `primary_accounting_action`:
   - Any paid milestone missing revenue journal → `"RECORD_REVENUE_MS{n}"` (where n is the first such milestone).
   - All paid milestones recognized → `"VERIFY_REVENUE_ONLY"`.
   - No paid milestones → `"NO_ACCOUNTING_ACTION"`.
 - `accounting_action.action`: same as `primary_accounting_action`.
 - `accounting_action.debit_account`: `"DEFERRED_REVENUE"`.
 - `accounting_action.credit_account`: `"IMPLEMENTATION_SERVICES_REVENUE"`.
 - `accounting_action.owner_queue`: `"ACCOUNTING"`.

 ### Collection Actions (train_005)

 - `collection_action`:
   - Unpaid AND due date is past → `"SEND_COLLECTION_NOTICE"`.
   - Unpaid AND due date is in the future → `"MONITOR_UNPAID_NOT_DUE"`.
   - All paid → `"NO_COLLECTION_ACTION"`.
 - `collection_task.action`: same as `collection_action`.
 - `collection_task.owner_queue`: `"ACCOUNT_MANAGEMENT"` for monitoring, `"COLLECTIONS"` for collection notices, `"NONE"` for no action.

 ### Event & Voucher Fields

 - `event_status`: uppercase the API status — `"scheduled"`→`"SCHEDULED"`, `"active"`→`"ACTIVE"`, `"confirmed"`→`"SCHEDULED"`, `"completed"`→`"COMPLETED"`, `"cancelled"`→`"CANCELLED"`.
 - `voucher_status`: uppercase — `"active"`→`"ACTIVE"`, `"draft"`→`"DRAFT"`, `"expired"`→`"EXPIRED"`, `"disabled"`→`"DISABLED"`.
 - `discount_amount` / `voucher_discount`: the `discount_percent` value from the API voucher record (e.g. 50 for 50%, 100 for 100%).
 - `max_uses`: the `max_redemptions` value from the voucher.
 - `invite_action`: `"SEND_BRIEFING_INVITE"` when an event is scheduled/future and invite hasn't been sent; `"VERIFY_INVITE_SENT"` when event is live/completed; `"NO_INVITE_ACTION"` otherwise.

 ### Follow-Up Tasks (train_003)

 - Collection task: when a milestone is unpaid (`payment_status: "UNPAID"`), create a `COLLECTION` task with `next_action: "COLLECT_UNPAID_MILESTONE"`, the milestone's `due_date`, and `amount_due` set to `amount_unpaid`.
 - Event invitation task: when there is an associated future event, create an `EVENT_INVITATION` task with `next_action: "SEND_EVENT_INVITATION"` and the event's date as `due_date`.

 ### Offer Validity & WHO Documentation

 - `offer_validity_days`: `30` (standard catalog quote validity from POL-QUOTE-VALIDITY).
 - `who_documentation_required`: `true` for IEHK/WHO-standard medical modules.

 ### RFQ / Indicative Quote Specifics

 - `quote_basis`: use `"EXW_ONLY"` when the RFQ has no confirmed destination.
 - `freight_excluded`: `true` when destination is pending or quote basis is EXW_ONLY.
 - Quote at module level only: use the `product_code` and quantities from the RFQ's `requested_modules` array. Do not expand into component SKUs even if the API shows component composition.
 - Line items: iterate over `requested_modules` in the order they appear. For each, look up the product by `product_code`, use the single price tier (most IEHK modules have one tier), and compute `line_total = quantity × unit_price`.

 ## Common Pitfalls

 1. **Wrong customer name**: never use the prompt's colloquial name — always use the API `name` field.
 2. **Wrong price tier**: always match `confirmed_quantity` to the correct tier range.
 3. **Stale freight not flagged**: always check `valid_until` against the quote date.
 4. **Air vs Sea recommendation**: don't default to AIR just because of cold-chain — check if SEA has reefer support and sufficient shelf-life margin.
 5. **Revenue journal check**: a paid milestone without a revenue journal needs `MISSING_REVENUE_JOURNAL` status and drives a `RECORD_REVENUE` accounting action.
 6. **Milestone ID naming**: use `MS1`/`MS2`/`MS3` not the phase IDs from the API for templates that specify the MS{n} enum.
 7. **Invoice state for unpaid**: use `"OPEN"` not `"UNPAID"` (UNPAID is not in the invoice_state enum).
 8. **Collection for future due dates**: use `"MONITOR_UNPAID_NOT_DUE"`, not `"SEND_COLLECTION_NOTICE"` and not `"NO_COLLECTION_ACTION"`.
 9. **Voucher discount**: the `discount_amount` field takes the percent value (e.g. `50.00` for 50%), not a computed dollar amount.
 10. **Enum case**: all controlled vocabulary values are UPPERCASE (e.g. `"WON"`, `"PAID"`, `"LOW"`, `"AIR"`).
