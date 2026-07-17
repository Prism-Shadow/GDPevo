# MedBridge Sales Ops SOP

Use this skill for MedBridge Sales Ops tasks that ask for quote/RFQ pricing packages or opportunity finance reconciliations. Use only the task-provided API base URL.

## API Habits

- Start with `GET /health` and `GET /api` to confirm the service and route list.
- Detail routes: `GET /api/customers/<customer_id>`, `/products/<product_code>`, `/rfqs/<rfq_id>`, `/quotes/<quote_id>`, `/opportunities/<opportunity_id>`.
- Use `GET /api/search?q=<anchor_id>` for linked records. Searching the quote ID reliably surfaces freight quote rows; searching the opportunity ID surfaces invoices, payments, revenue journals, events, and vouchers.
- Use `GET /api/policies` for payment terms, quote scope, freight reconfirmation, quote validity, module granularity, and revenue recognition rules.
- Avoid judge/evaluator routes. Do not use unrelated records as evidence; filter linked collections by the task's explicit quote, RFQ, opportunity, customer, event, or voucher IDs.

## Source Precedence

- The answer template controls schema, field names, enum spelling, ordering hints, and nullability.
- The prompt controls the requested business date, quote date, confirmed customer request, required contact, and which records to reconcile.
- API records are the business source for customer status, product catalog tiers, freight rows, opportunity phases, invoices, payments, journals, events, vouchers, and policies.
- For quote revisions, prior quote quantity or prior unit price is history only. Reprice from the active product catalog tier for the confirmed quantity.
- If a prompt says quote at module level, keep RFQ lines at requested module codes even when product records expose component lists.

## Quote And RFQ Pricing

- Read the quote or RFQ, then customer, product(s), policies, and any freight records linked by quote ID.
- Select a catalog tier where `min_qty <= quantity` and `quantity <= max_qty`; treat `max_qty: null` as no upper bound. Use that tier's `unit_price_usd` and `lead_time_days`; use product `article_number` and `shelf_life_months`.
- Compute `line_total` or `exw_total_usd` as quantity times unit price. Compute every freight-inclusive `grand_total_usd` as EXW total plus freight cost.
- For RFQs without a confirmed destination, apply EXW-only policy: `quote_basis` like `EXW_ONLY`, `freight_excluded: true`, and no freight options.
- Payment terms come from customer profile plus policies: new NGO/prospect/no credit history normally maps to `PREPAY_100`; recurring approved accounts normally keep their payment profile such as `NET_30_AFTER_PO`.
- Offer validity for catalog quotes comes from policy, usually 30 calendar days from quote date when the template asks for a day count.

## Freight Decisions

- Include only freight rows linked to the target quote and matching the requested shipment/mode context. Ignore distractor rows with wrong shipment size, stale benchmark notes, or unrelated routes unless the task specifically asks to flag that option.
- If the task expects air/sea/road comparison, keep the mode order `AIR`, `SEA`, `ROAD` when the template implies it.
- A freight row is valid on the quote date only when it is not stale and `valid_until >= quote_date`. Expired or `status: stale` rows should be marked stale/invalid and should trigger reconfirmation warnings.
- Freight reconfirmation is required for freight-inclusive quotes because freight is valid only through its `valid_until` date and must be reconfirmed at final order. For EXW-only/no-destination quotes, freight is excluded instead.
- Map `mode` and `route_risk` to template enums in uppercase. Derive risk flags from `route_risk` and `risk_notes`; low risk is usually `NONE`, border/customs/stale notes should be surfaced in the template's warning fields.
- Recommend a mode by balancing validity, policy fit, route risk, cold-chain support, transit, and cost. Do not recommend an expired/stale option even if it is cheapest.

## Opportunity Reconciliation

- Read the opportunity detail and search by opportunity ID for all linked invoices, payments, revenue journals, event, and voucher records. Read the customer for the canonical name/contact context.
- Sum opportunity phases and compare with `won_amount_usd`. Use invoice totals and outstanding amounts to compute paid, unpaid, and outstanding balances.
- Payment status: full posted payment or zero outstanding means `PAID`; some paid and some outstanding means `PARTIAL`; no paid amount and outstanding balance means `UNPAID`.
- Revenue recognition is required for completed, paid milestones. A matching posted revenue journal by phase or invoice means `RECOGNIZED`; paid without a journal means missing/required; unpaid future milestones are `NOT_REQUIRED_UNPAID`.
- Recognized amount is the sum of matching posted revenue journals for the reconciled opportunity.
- Collection action depends on due date versus the task's as-of date: unpaid and not yet due means monitor; due or overdue means send collection; no unpaid balance means no collection action.
- Accounting action depends on missing required revenue journals. Use only enum values declared in the template, mapping API account labels to template enums such as `DEFERRED_REVENUE` and `IMPLEMENTATION_SERVICES_REVENUE`.
- Event/voucher fields come from linked event and voucher records. Keep the requested contact attached to follow-up or invite tasks. If a voucher exposes `discount_percent` but the template asks for a generic discount number, use the numeric API discount value without inventing a currency conversion.

## Output Conventions

- Return only valid JSON matching the provided template. Do not add markdown, comments, extra keys, or explanatory text.
- Use stable API IDs exactly. If the template requires normalized milestone IDs such as `MS1`, `MS2`, `MS3`, order phases ascending and map them consistently.
- Use ISO `YYYY-MM-DD` dates. Use `null` only where the template permits it.
- Money fields should be numeric values at cent precision. Prefer `0.0`/`0.00` style numbers over strings.
- Convert API lowercase/status words to the template's controlled uppercase enums exactly, for example opportunity `closed_won` to `WON`, event `scheduled` to `SCHEDULED`, voucher `active` to `ACTIVE`.
- Preserve template array order when shown; otherwise use business order: RFQ requested module order, freight by mode, milestones by phase, then follow-up tasks by urgency/accounting before invite work.

## Common Traps

- Do not use prior quote prices on revised quantities.
- Do not split module RFQs into component SKUs.
- Do not add freight to EXW-only/no-destination RFQs.
- Do not treat every freight search result as usable; filter out distractors and flag stale linked options.
- Do not mark paid milestones complete for accounting unless the revenue journal exists.
- Do not create collection notices for unpaid milestones that are not due yet unless the template or prompt explicitly asks for that escalation.
- Do not invent enum values; adapt the reasoning to the exact enum set in the answer template.
