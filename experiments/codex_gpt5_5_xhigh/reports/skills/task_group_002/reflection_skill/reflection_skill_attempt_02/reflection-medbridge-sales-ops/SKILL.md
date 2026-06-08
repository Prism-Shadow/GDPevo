---
name: reflection-medbridge-sales-ops
description: Use this skill for MedBridge Sales Ops API tasks that ask for account-ready JSON quote packages, RFQ module quotes, freight comparisons, payment terms, milestone invoice reconciliation, revenue-recognition coverage, event/voucher follow-up actions, or any response that must match a provided answer_template.json. Always use this skill when the prompt mentions MedBridge, Sales Ops API, quotes, RFQs, freight, opportunities, invoices, payments, revenue journals, vouchers, or engagement reconciliation.
---

# MedBridge Sales Ops JSON Workflow

## Scope

Produce only valid JSON matching the supplied `input/payloads/answer_template.json`. Use the shared API as the business source of truth, but let the prompt and template control output shape, enum spelling, display names, and whether a field wants an operational ID, a normalized milestone label, or a business code.

## Environment Usage

1. Read the task prompt and `answer_template.json`.
2. Resolve the API base URL from the prompt or runner variables such as `API_BASE_URL`, `BASE_URL`, or the provided localhost URL.
3. Inspect `GET {base}/api` if endpoint names are unknown.
4. Prefer targeted searches:
   - `GET {base}/api/search?q=<quote_id>`
   - `GET {base}/api/search?q=<rfq_id>`
   - `GET {base}/api/search?q=<opportunity_id>`
   - `GET {base}/api/search?q=<customer_id>`
5. Fetch direct records when needed:
   - `/api/customers/<customer_id>`
   - `/api/products/<product_code>`
   - `/api/rfqs/<rfq_id>`
   - `/api/quotes/<quote_id>`
   - `/api/opportunities/<opportunity_id>`
   - `/api/freight-quotes/<freight_id>`
   - `/api/policies`

Do not rely on a direct quote or opportunity record alone; the search endpoint usually surfaces linked freight, invoice, payment, revenue-journal, event, and voucher records.

## Quote And RFQ SOP

1. Confirm the requested quote/RFQ ID, customer ID, quote date, product/module codes, and quantities from the prompt and API.
2. For each product line, fetch the product and choose the active price tier where `min_qty <= quantity <= max_qty`; treat `max_qty: null` as no upper bound.
3. Use the selected tier for `unit_price`, `unit_price_usd`, and `lead_time_days`. Use product `shelf_life_months` and `article_number`.
4. Compute `line_total = quantity * unit_price` and `exw_total = confirmed_quantity * unit_price`.
5. For module RFQs, quote at module line level. Ignore component-composition details unless the prompt explicitly asks for component pricing.
6. For missing destination or indicative EXW RFQs, set the basis to the template's EXW-only code, set `freight_excluded: true`, and omit freight lines.
7. For freight comparisons, use freight records linked to the quote ID and requested route/mode. Exclude obvious distractors such as wrong route, wrong shipment size, superseded status, or IDs/notes marking them as distractors.
8. Include stale or expired freight only when the prompt/template asks for validity warnings or a specific stale mode. Mark it stale rather than recommending it.
9. Compute `grand_total = exw_total + freight_cost`.
10. Return modes and risk fields in the template's enum style, usually uppercase.

## Freight Field Rules

- `validity_status`: `VALID` when status is active and `valid_until >= quote_date`; `STALE` or the template's invalid enum when status is stale or `valid_until < quote_date`.
- `source_is_stale`: true only for stale/expired source records.
- `all_freight_options_valid_on_quote_date`: true only if every included freight option is valid on the quote date.
- `freight_reconfirmation_required`: true whenever freight rates are included or a freight reconfirmation policy applies.
- `risk_level` / `customs_border_risk`: map API route risk to uppercase. Use `LOW` for active low-risk freight. For medium road or border risk, use the template's medium border flag if available. High customs or border risk should be `HIGH`.
- `risk_flag`: use `NONE` for low risk. Use a specific border/customs flag only when the template provides or implies one.
- `transit_days`: preserve the template's convention. In plain freight-option arrays, API text such as `4-6 days` is acceptable. In compact transport-decision objects, prefer the range without the word `days` when standards use terse ranges.
- `recommended_mode`: choose the lowest-cost valid mode that satisfies route, risk, and special handling constraints. Do not recommend stale options. Cold-chain alone does not force air if a valid lower-cost cold-chain mode is acceptable and the route risk is not disqualifying.

## Payment And Quote Policy Rules

- New NGO/prospect/new-client-review accounts: `PREPAY_100`.
- Recurring NGO accounts with approved terms: `NET_30_AFTER_PO`.
- Recurring commercial accounts with a net payment profile: `NET_30_AFTER_PO`.
- Use business codes in output fields, not policy record IDs, unless the template explicitly asks for policy IDs.
- Common quote-basis codes: `EXW`, `EXW_ONLY`, `EXW_PLUS_FREIGHT_OPTIONS`.
- Offer validity for catalog pricing is normally 30 calendar days when the template asks for validity days.
- WHO/documentation-required flags come from the prompt, template, product family, or policy context; keep them boolean.

## Engagement Reconciliation SOP

1. Search by opportunity ID. Collect the opportunity, customer, milestone phases, invoices, payments, revenue journals, related event, and voucher.
2. Map stage values to template enums: closed/won -> `WON`, open/negotiation -> `OPEN`, lost/closed_lost -> `LOST`.
3. Prefer the prompt's customer display name when it clearly names the same customer ID and differs only from an API alias. Otherwise use the API customer name.
4. Sum phase amounts and compare with `won_amount`. Sum posted payments or invoice `paid_amount` for total paid. Outstanding balance is the API opportunity outstanding amount when present, otherwise the sum of invoice outstanding amounts.
5. Order milestones by phase order. If the template uses or mentions `MS1`, `MS2`, `MS3`, normalize milestone IDs to `MS<n>` even if the API phase IDs differ. Use raw phase IDs only when the template explicitly asks for `phase_id`.
6. For paid milestones, set milestone `due_date` to null when the output is a reconciliation status; due dates remain relevant for unpaid/open collection items.
7. Determine payment state:
   - paid amount equals invoice amount -> `PAID`
   - paid amount is greater than zero but less than invoice amount -> `PARTIAL`
   - paid amount is zero and invoice is open/unpaid -> `UNPAID`
   - missing/unclear data -> `UNKNOWN`
8. Determine invoice state from the template enum. Paid invoices are `PAID`; unpaid active invoices are usually `OPEN`; void records are `VOID`.
9. Revenue recognition:
   - Paid/completed milestone with posted revenue journal -> `RECOGNIZED`
   - Paid/completed milestone without a revenue journal -> `MISSING_REVENUE_JOURNAL` or `REQUIRED_MISSING`, matching the template
   - Unpaid milestone -> `NOT_REQUIRED_UNPAID`
10. Recognition summary:
   - All paid milestones have journals -> `COMPLETE_FOR_PAID_MILESTONES`
   - Any paid milestone lacks a required journal -> `MISSING_FOR_PAID_MILESTONES`
   - No paid milestone needs recognition -> `NOT_REQUIRED`

## Follow-Up And Action Rules

- Missing revenue for a paid milestone creates an accounting action. Use `RECORD_REVENUE_MS<n>` when the template supports milestone-specific action codes; debit `DEFERRED_REVENUE`, credit `IMPLEMENTATION_SERVICES_REVENUE`, owner `ACCOUNTING`.
- Unpaid milestones create collection or monitoring work:
  - Due or overdue as of the business date -> collection/send-notice action.
  - Not yet due -> monitor action when the template has one; otherwise create the simple collection follow-up expected by the template.
- Tie all tasks to the named contact from the prompt/opportunity.
- Event and voucher fields:
  - Uppercase event/voucher statuses to match enums.
  - Map voucher `discount_percent` to `voucher_discount` or `discount_amount`.
  - Map `max_redemptions` to `voucher_max_uses` or `max_uses`.
  - If an event-invitation task needs a due date and the API has none, use a conservative pre-event task date, commonly 21 calendar days before the event, unless the prompt states otherwise.
- Send invitation actions when the event is scheduled/confirmed and the voucher is active.

## Field Definitions

- `quote_id`, `rfq_id`, `customer_id`, `opportunity_id`, `event_id`, `voucher_code`: stable IDs from the prompt/API.
- `confirmed_quantity` / `quantity`: requested quantity for the current task, not prior/superseded quantities.
- `catalog_tier`: selected product tier containing the current quantity; include min/max exactly as the tier represents them.
- `unit_price` / `unit_price_usd`: selected tier price, not a prior quote price.
- `lead_time_days`: selected tier lead time.
- `shelf_life_months`: product shelf life.
- `exw_total_usd`, `line_total`, `grand_total`, `won_amount`, `recognized_amount`, `amount_due`: numeric USD values; use two-decimal-compatible numbers.
- `payment_terms`: controlled business term code.
- `freight_cost_usd`: linked freight quote cost.
- `valid_until`: ISO date from freight quote.
- `source_is_stale`: boolean indicating stale/expired freight source.
- `opportunity_matches_milestones`: true when won amount equals summed milestone amounts.
- `recognition_status`: controlled status derived from paid milestone journal coverage.
- `owner_queue`: controlled uppercase owner enum from the business function.

## Common Pitfalls From Training Reflection

- Do not use prior quote quantities or prior prices when the prompt confirms a revised quantity.
- Do not split module RFQs into component SKUs; component lists are often distractors.
- Do not include every search result. Filter out superseded RFQs, distractor records, wrong routes, wrong shipment sizes, and stale freight unless the prompt asks to flag stale freight.
- Do not use stale freight as the recommended mode just because it is cheapest.
- Do not output policy IDs where the template wants business labels such as `RECURRING_NGO` or payment-term codes.
- Do not blindly trust API display names when the prompt gives the account-ready customer name for the same ID.
- Normalize milestone IDs to `MS<n>` when the template uses phase numbers or MS enums; raw API phase IDs can fail template expectations.
- Paid milestone due dates are often null in reconciliation outputs even when invoices have historical due dates.
- Voucher discount fields may be named like currency amounts but still expect the percentage value when the API voucher is percentage-based.
- Recompute arithmetic totals and cross-check them against line totals. If a total appears inconsistent, look for an explicit fee or policy source before inventing one.

## Final Output Checklist

Before responding, verify:

1. The JSON parses and contains no markdown or explanation.
2. All required template keys are present and no unrelated narrative fields were added.
3. Enums are exactly the template's uppercase spelling.
4. Dates are ISO `YYYY-MM-DD` or null where the template allows null.
5. Money fields are numeric, not strings.
6. Totals reconcile with selected line items, freight, invoices, payments, and journals.
