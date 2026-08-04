 # MedBridge Sales Ops API Skill

 ## Overview
 Use the MedBridge Sales Ops API (`<TASK_ENV_BASE_URL>`) to resolve quote, freight, reconciliation, and engagement decision-package tasks. The API is read-only (GET only) and returns JSON across standard collections.

 ## Available Endpoints
 - `GET /api` — list collections
 - `GET /api/search?q=<text>` — search across all collections
 - `GET /api/customers` / `GET /api/customers/<id>` — customer records
 - `GET /api/products` / `GET /api/products/<code>` — product catalog with price tiers
 - `GET /api/quotes` / `GET /api/quotes/<id>` — quotes with line items
 - `GET /api/rfqs` / `GET /api/rfqs/<id>` — RFQs with requested modules
 - `GET /api/freight-quotes` / `GET /api/freight-quotes/<id>` — freight options
 - `GET /api/policies` / `GET /api/policies/<id>` — business rules and policies
 - `GET /api/opportunities` / `GET /api/opportunities/<id>` — CRM opportunities with phases
 - `GET /api/invoices` / `GET /api/invoices/<id>` — invoices
 - `GET /api/payments` / `GET /api/payments/<id>` — payments
 - `GET /api/revenue-journals` / `GET /api/revenue-journals/<id>` — revenue recognition entries
 - `GET /api/events` / `GET /api/events/<id>` — client events
 - `GET /api/vouchers` / `GET /api/vouchers/<code>` — event vouchers

 ## Core Workflows

 ### 1. Quote Decision Package (quote + freight + policies)
 **Applies when:** A quote ID and product code are given with a confirmed quantity and quote date.

 **Steps:**
 1. Fetch the quote by ID (`GET /api/quotes/<id>`) to confirm customer, product, quantity, and destination.
 2. Fetch the product by code (`GET /api/products/<code>`) and select the correct price tier where `min_qty <= confirmed_quantity <= max_qty` (null max means unlimited).
 3. Compute `exw_total = confirmed_quantity × unit_price_usd`.
 4. Fetch freight quotes (`GET /api/freight-quotes`) and filter records whose `quote_id` matches the target quote.
 5. For each matching freight option, compute `grand_total = exw_total + freight_cost_usd`.
 6. Compare each freight option's `valid_until` date against the `quote_date`. A freight quote is stale/expired if `valid_until < quote_date`.
 7. Determine `risk_level` from API `route_risk`: `low` → `LOW`, `medium` → `MEDIUM`, `high` → `HIGH`.
 8. Fetch customer (`GET /api/customers/<customer_id>`) for payment profile, segment, and type.
 9. Fetch policies (`GET /api/policies`) for applicable payment and freight rules.
 10. Select recommended transport mode considering cost-effectiveness, risk, transit time, and cold-chain requirements.
 11. Set `freight_reconfirmation_required` to `true` per policy.
 12. Reference applicable policy by its `id` field (e.g., `POL-RECURRING-NGO-PAYMENT`), not by the terms code.

 ### 2. Indicative Module Quote (RFQ-based, EXW only)
 **Applies when:** An RFQ ID is given for a module-level indicative quote without a confirmed destination.

 **Steps:**
 1. Fetch the RFQ (`GET /api/rfqs/<id>`) for the list of requested modules and quantities.
 2. Fetch each requested product by code for pricing; use the module-level product codes (e.g., `IEHK-BASIC`), not individual components.
 3. Build line items with `product_code`, `article_number`, `quantity`, `unit_price`, `lead_time_days`, `shelf_life_months`, and `line_total = quantity × unit_price`.
 4. Sum all line totals for the `grand_total`.
 5. Set `freight_excluded: true` and `quote_basis: "EXW_ONLY"`.
 6. Apply the new-client payment policy: `PREPAY_100` for new NGO clients without approved credit.
 7. Set `offer_validity_days: 30` per standard quote validity policy.
 8. Set `who_documentation_required: true` for IEHK and medical supply modules.

 ### 3. Account Reconciliation (opportunity, milestones, invoices, payments, revenue)
 **Applies when:** An opportunity ID and customer ID are given for a reconciliation review.

 **Steps:**
 1. Fetch the opportunity for stage, won_amount, phases, and outstanding_amount.
 2. Fetch all invoices linked to the opportunity (filter by `opportunity_id`).
 3. Fetch all payments linked to the opportunity.
 4. Fetch all revenue journals linked to the opportunity.
 5. Fetch events and vouchers linked to the opportunity/customer.
 6. Map `stage`: `closed_won` → `WON`, `open` → `OPEN`, `closed_lost` → `LOST`.
 7. For each milestone phase:
    - Set `payment_status` based on invoice payment state: fully paid → `PAID`, partially paid → `PARTIAL`, nothing paid → `UNPAID`.
    - Set `revenue_recognition_status`:
      - Has a posted revenue journal → `RECOGNIZED`
      - Is paid but missing revenue journal → `MISSING_REVENUE_JOURNAL`
      - Is unpaid and not yet due → `NOT_REQUIRED_UNPAID`
      - Is unpaid and past due → `REQUIRED_MISSING` (if the milestone is complete)
 8. For the overall revenue recognition summary:
    - Count recognized and missing milestones.
    - Sum recognized amounts.
 9. Generate follow-up tasks:
    - Collection tasks for unpaid milestones that are due or approaching due.
    - Event invitation tasks when events are linked and scheduled.
 10. For accounting actions:
     - `RECORD_REVENUE_MS<N>` when a paid milestone lacks a revenue journal entry.
     - Debit: `DEFERRED_REVENUE`, Credit: `IMPLEMENTATION_SERVICES_REVENUE`.
     - Owner queue: `ACCOUNTING` for revenue entries, `ACCOUNT_MANAGEMENT` for monitoring/collection.

 ## Key Business Rules (from Policies)
 - **Payment Terms:** New NGO clients require `PREPAY_100`. Recurring NGO clients may use `NET_30_AFTER_PO`. Commercial recurring clients use `NET_30_AFTER_PO`.
 - **Quote Validity:** Catalog pricing valid for 30 calendar days from quote date. Freight validity may expire sooner based on `valid_until`.
 - **Freight Reconfirmation:** All freight rates require reconfirmation at final order (`POL-FREIGHT-RECONFIRM`).
 - **Revenue Recognition:** When a milestone is complete AND paid, recognize revenue from Deferred Revenue to Implementation Services Revenue (`POL-REVREC`).
 - **Module RFQs:** Quote at module line level unless customer requests component-level pricing (`POL-MODULE-GRANULARITY`).
 - **Indicative Quotes:** Without a confirmed destination, quotes must be EXW only and exclude freight (`POL-INDICATIVE-EXW`).

 ## Data Mapping Conventions
 - **Money values:** Always two decimal places (e.g., `50000.00`).
 - **Dates:** ISO 8601 `YYYY-MM-DD` format.
 - **Status casing:** Use UPPERCASE for controlled enum values unless the API value is directly mapped (e.g., `low` → `LOW`).
 - **Policy references:** When a field asks for a policy, use the policy `id` (e.g., `POL-RECURRING-NGO-PAYMENT`), not the `terms_code`.
 - **Milestone IDs:** Map sequential phases to `MS1`, `MS2`, `MS3` in ascending order.
 - **Freight validity:** A freight record with `valid_until` before the `quote_date` is stale/expired.
 - **Catalog tier selection:** Use the tier where `min_qty <= confirmed_quantity` and (`max_qty` is null or `confirmed_quantity <= max_qty`).

 ## Common Pitfalls to Avoid
 - Do not split module products into component-level line items unless explicitly requested.
 - Do not use the terms code when a field expects the policy ID.
 - Do not recommend a freight mode that has expired or is stale.
 - Do not mark a milestone as requiring revenue recognition unless it is both complete AND paid.
 - Verify that phase/invoice totals sum to the opportunity won_amount before declaring a match.
 - Filter freight quotes by the target `quote_id` field; unrelated freight records share the same collection.
