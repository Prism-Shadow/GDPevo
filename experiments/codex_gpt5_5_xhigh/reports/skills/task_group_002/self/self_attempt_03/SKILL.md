---
name: medbridge-sales-ops-sop
description: Operational SOP for MedBridge Sales Ops quote, RFQ, freight, and milestone reconciliation tasks.
---

# MedBridge Sales Ops SOP

Use this skill for MedBridge Sales Ops tasks that ask for account-ready JSON based on the shared API. The answer must match the provided `input/payloads/answer_template.json` exactly: no markdown, no extra keys, no explanatory text.

## API workflow

- Use the API base URL supplied by the task runner or prompt. First check `GET /health` and `GET /api` if unsure which routes are available.
- Public routes normally include `customers`, `products`, `rfqs`, `quotes`, `freight-quotes`, `policies`, `opportunities`, `invoices`, `payments`, `revenue-journals`, `events`, `vouchers`, and `search`.
- Use direct lookups for authoritative primary records:
  - `GET /api/customers/<customer_id>`
  - `GET /api/products/<product_code>`
  - `GET /api/rfqs/<rfq_id>`
  - `GET /api/quotes/<quote_id>`
  - `GET /api/opportunities/<opportunity_id>`
  - `GET /api/freight-quotes/<freight_id>` when a freight ID is known.
- Use `GET /api/search?q=<id-or-name>` to gather linked records quickly. Searching a quote ID commonly returns its freight records; searching an opportunity ID commonly returns invoices, payments, revenue journals, event, and voucher records.
- Always fetch `GET /api/policies` for payment terms, EXW/freight scope, quote validity, freight reconfirmation, module granularity, and revenue-recognition rules.

## Source precedence

1. The answer template controls the exact JSON shape, field names, enum vocabulary, booleans, and whether lists are expected.
2. The prompt controls the requested IDs, requested date/as-of date, customer intent, and whether freight is included or excluded.
3. API records are the source of truth for customer status, product tiers, quote/RFQ lines, freight validity, invoices, payments, revenue journals, events, and vouchers.
4. Policy records resolve commercial rules such as payment terms, EXW scope, freight reconfirmation, quote validity, module granularity, and revenue recognition.
5. Derived calculations fill totals, match flags, outstanding balances, validity flags, and action routing.

Do not use prior quote quantities or prior prices when a quote revision supplies a confirmed quantity and the catalog tier changes. Do not use component composition as line items when the RFQ asks for module-level pricing.

## Quote revisions with freight

- Fetch the quote, customer, product, policies, and freight records linked by `quote_id`.
- Use the quote line's current confirmed quantity and product code. Select the product price tier where `min_qty <= quantity` and `max_qty` is null or `quantity <= max_qty`.
- Fill unit price, lead time, shelf life, quote basis, and EXW total from the selected tier: `exw_total = quantity * unit_price`.
- Freight records must match the quote and the intended route/shipment. Exclude distractor freight records with wrong shipment size, route, destination, stale benchmark labels, or unrelated IDs unless the template specifically asks to report stale/source-validity issues for that mode.
- If the template expects one row per mode, choose the canonical linked record for each requested mode. Include stale or expired mode records only when the task asks to compare validity/risk; mark them stale instead of treating them as current.
- Freight validity is based on both `status` and `valid_until` against the quote date: stale if `status != active` or `valid_until < quote_date`.
- Grand total per freight option is `exw_total + freight_cost`.
- Use `transit_days_text` for string transit fields. Normalize modes and risk fields to the template style, often uppercase (`AIR`, `SEA`, `ROAD`, `LOW`, `MEDIUM`, `HIGH`).
- Recommended mode is not simply the cheapest option. Prefer a valid, active mode that satisfies product constraints such as cold-chain support and has acceptable route risk; do not recommend stale/expired/high-risk options when a valid lower-risk option exists.
- Freight reconfirmation is normally required for freight-inclusive quotes because policy says rates must be reconfirmed at final order.

## Indicative RFQs and module quotes

- Fetch the RFQ, customer, all requested product modules, and policies.
- Quote exactly the RFQ's requested modules as line items. Do not split module products into components unless the customer explicitly requested component pricing.
- For each module, use the matching product's active tier for the requested quantity, usually the open-ended tier for module products.
- Use product `article_number`, `lead_time_days`, `shelf_life_months`, and `unit_price_usd`. Compute each `line_total = quantity * unit_price`.
- If the RFQ has no confirmed destination or policy says indicative quotes without destination are EXW only, set the quote basis to the template's EXW-only value and exclude freight.
- For new NGO/prospect customers without approved credit, use the new-client prepayment policy rather than the customer's free-text notes.
- Standard catalog quote validity is 30 calendar days unless a policy or template says otherwise.

## Opportunity, invoice, and revenue reconciliation

- Fetch the opportunity and customer directly, then use search on the opportunity ID to gather linked invoices, payments, revenue journals, events, and vouchers.
- Sum opportunity phases and compare with `won_amount_usd` for match flags. Use the opportunity/customer IDs and contact named by the opportunity or prompt.
- Reconcile milestones by joining:
  - opportunity `phases[].phase_id` and `invoice_id`
  - invoice `phase_id`, `invoice_id`, `paid_amount_usd`, `outstanding_amount_usd`, `status`, and `due_date`
  - posted payments by `invoice_id`
  - posted revenue journals by `opportunity_id`, `invoice_id`, and `phase_id`
- Payment state:
  - `PAID` when invoice paid amount covers the invoice and outstanding is zero.
  - `PARTIAL` when paid amount is greater than zero but outstanding remains.
  - `UNPAID` when no payment is posted and outstanding remains.
  - Use `UNKNOWN` only when the template allows it and source records are missing or contradictory.
- Revenue-recognition state:
  - Paid/completed milestones require a posted revenue journal.
  - A matching posted journal means `RECOGNIZED`.
  - Paid/completed with no matching posted journal means missing revenue recognition.
  - Unpaid or not-yet-due future milestones normally do not require revenue recognition yet.
- Outstanding balance should come from invoice outstanding amounts and be cross-checked against the opportunity outstanding amount.
- Accounting actions should follow the template's enum values: record revenue for paid milestones missing journals, verify only when all required journals exist, otherwise no accounting action.
- Collection actions depend on due date and payment state: send collection notice for unpaid due/overdue invoices, monitor unpaid invoices not yet due, and no collection action when fully paid.
- Event/voucher sections come from linked event and voucher records. Copy stable IDs/codes, event status, voucher status, max uses/redemptions limit, and numeric discount value from the API; do not invent a cash discount from a percent field.

## Output conventions

- Return valid JSON only, exactly matching the answer template.
- Use numeric JSON values for money, not strings. Round USD calculations to two decimals.
- Use ISO `YYYY-MM-DD` dates; use `null` only where the template permits null.
- Keep stable API IDs exactly as records provide them.
- Normalize API lowercase statuses into the template's controlled enums:
  - opportunity `closed_won` -> `WON`; open/lost map to `OPEN`/`LOST` when applicable.
  - invoice `paid`/`unpaid` -> template payment or invoice states such as `PAID`, `UNPAID`, or `OPEN` according to the template wording.
  - event and voucher statuses normally become uppercase template values.
  - route risk becomes uppercase risk level.
- Preserve template-specific spelling: examples include `EXW`, `EXW_ONLY`, `PREPAY_100`, `NET_30_AFTER_PO`, `RECORD_REVENUE_MS2`, `MONITOR_UNPAID_NOT_DUE`, and `SEND_BRIEFING_INVITE`.
- Booleans must be true JSON booleans, not strings.

## Common traps

- Prior quote price is a distractor when the confirmed quantity moves into a new catalog tier.
- Freight search results may include distractor routes, wrong shipment sizes, old benchmarks, or stale records. Match by quote ID, route/shipment relevance, mode, status, and validity date.
- Expired freight can still be shown if the template asks for validity warnings, but it should not be treated as current or recommended.
- Cheapest freight is not necessarily recommended when cold-chain support, route risk, or stale validity conflicts with policy or product requirements.
- EXW-only RFQs should not include freight totals, even if product weights/CBM would allow estimation.
- Module RFQs stay at module line level; component lists are usually medical-review context, not quote lines.
- Revenue journals are required for paid/completed milestones, not merely for every phase listed on an opportunity.
- Paid invoice status should be cross-checked with payments and outstanding amounts; do not rely on one field if the template asks for reconciliation.
- Voucher fields may be named as discounts in the template even when the API stores a percentage. Use the source numeric discount value and do not calculate a nonexistent dollar amount.
