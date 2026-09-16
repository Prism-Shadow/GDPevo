---
name: medbridge-sales-ops
description: Use this skill for MedBridge Sales Ops API tasks that ask for account-ready JSON quote packages, RFQ pricing, freight comparisons, CRM opportunity reconciliation, milestone invoices, revenue recognition, event/voucher follow-up, or strict answer_template.json output. Use it whenever the prompt mentions the MedBridge Sales Ops API, Sales Ops records, catalog tiers, EXW/freight quote decisions, customer payment policies, invoices, payments, revenue journals, opportunities, events, vouchers, or a request to return only JSON matching an input payload template.
---

# MedBridge Sales Ops JSON Reconciler

Use this skill to solve MedBridge Sales Ops tasks by fetching the business records from the task-provided API, reconciling them, and returning only JSON that conforms to the provided template. The evaluator cares about exact values, exact schema shape, and whether the answer is derived from the current API records rather than from assumptions.

## First Pass

1. Read the user prompt and `input/payloads/answer_template.json`.
2. Identify the task-provided API base URL. Prompts may name it as `<TASK_ENV_BASE_URL>`, `BASE_URL`, or similar. Use the actual URL available in the runner/session, not the literal placeholder text.
3. Query `GET /api` to confirm available collections, then fetch records with detail endpoints and `GET /api/search?q=<id-or-name>` as needed.
4. Build the answer from API records and policy records. Do not rely on IDs, amounts, names, dates, or statuses from prior examples.
5. Return only valid JSON. Do not include markdown, comments, explanations, trailing commas, or extra keys.

Useful collections are usually:

- `customers`, `products`, `rfqs`, `quotes`, `freight-quotes`, `policies`
- `opportunities`, `invoices`, `payments`, `revenue-journals`
- `events`, `vouchers`

Prefer exact detail fetches when the prompt gives an ID. Use search for discovery, then verify linked records by exact IDs such as `customer_id`, `quote_id`, `rfq_id`, `opportunity_id`, `invoice_id`, `event_id`, and `voucher_code`.

## Template Discipline

Treat `answer_template.json` as the output contract.

- Preserve the top-level key names and nested object names exactly.
- Keep field order close to the template when practical.
- Expand arrays to the number of real matching records needed for the task; do not leave a single placeholder item if the API has multiple requested lines, freight options, or milestones.
- Use JSON numbers for money and quantities, booleans for flags, and `null` only when the template or prompt allows it.
- For enum-like fields, emit the exact controlled values declared in the template. Convert API values to those enums rather than inventing nearby wording.
- Use ISO `YYYY-MM-DD` dates.
- Round currency calculations to cents when the template asks for cent-level money; otherwise preserve the style implied by the template.
- Before final output, recalculate every total from components and check that linked IDs all point to the same customer/opportunity/quote.

## Record Discovery

Start from IDs and entities in the prompt.

- Quote/RFQ tasks: fetch the quote or RFQ record, the customer, each product line, relevant policies, and freight quotes if freight is requested or the quote has a destination/advisory freight scope.
- Account reconciliation tasks: fetch the opportunity, customer, all invoices/payments/revenue journals linked to the opportunity, and any linked event/voucher requested by prompt or present in the records.
- If search returns distractors, discard records that only share a keyword but do not match the requested exact ID, linked customer, linked opportunity, linked quote, current quote date, destination, or route/product context.
- Use list endpoints to cross-check when a detail endpoint omits a linked collection.

## Catalog Quote And RFQ Logic

For quote revisions and RFQs:

1. Determine requested line items from the quote `line_items`, RFQ `requested_modules`, or prompt-confirmed product/quantity.
2. Fetch each product. Select the catalog tier where `min_qty <= quantity` and either `max_qty` is null or `quantity <= max_qty`.
3. Use the selected tier's `unit_price_usd` and `lead_time_days`; use the product's `article_number` and `shelf_life_months` when the template asks for them.
4. Compute `line_total = quantity * unit_price` and `exw_total` or `grand_total` as the sum of line totals before freight.
5. For module RFQs, quote at module line level unless the prompt explicitly asks for component-level pricing. Ignore component composition notes as distractors for pricing.
6. If a module or product appears more than once in an RFQ and the narrative asks to consolidate, combine quantities before pricing.
7. If the prompt says no confirmed destination or says freight is excluded/EXW only, omit freight options and set the template's freight-excluded or EXW-only controls accordingly.

Payment and quote controls come from policies plus customer profile:

- New customers or new NGO accounts without approved credit normally map to the prepayment policy.
- Recurring customers normally use the net-after-PO policy unless the prompt or grant terms restrict it.
- When the template asks for customer policy, policy terms, or account category, derive the code from the matching customer segment/payment profile and policy record; format it to the template's enum style.
- If the template asks for offer validity, use the quote-validity policy in the API.
- If the template asks for WHO/documentation or compliance flags, derive them from the prompt, RFQ notes, customer notes, product requirements, and policies.

## Freight Logic

When freight options are part of the answer:

1. Fetch freight records linked by exact `quote_id`.
2. Keep the records that match the requested quote, route/destination context, mode, shipment characteristics, and prompt intent.
3. Exclude clear distractors such as old benchmarks, wrong shipment sizes, unrelated destinations, or records whose notes identify them as not current for the requested quote.
4. Keep a stale/expired linked option only when the prompt/template asks to report invalid, stale, or route-risk warnings for that mode; mark it stale rather than recommending it.
5. Compute each `grand_total` as `exw_total + freight_cost_usd`.
6. Use the API's `transit_days_text` when present. Otherwise format min/max transit days consistently with the template.
7. Determine validity on the quote date: a freight record is valid when it is active and `valid_until` is on or after the quote date. It is stale/invalid when status says stale/expired or validity ended before the quote date.
8. Map route risk from API values to template enums. Typical mappings are low -> `LOW`/`NONE`, medium -> `MEDIUM` and a border/customs risk flag when requested, high -> `HIGH` and a warning/control flag.

Recommended mode:

- Do not recommend stale, expired, or high-risk options unless every viable option is worse and the prompt explicitly accepts the risk.
- If the prompt has a delivery deadline, calculate production-ready date as `quote_date + lead_time_days`, then ETA as production-ready date plus the freight option's maximum transit days. Recommend the lowest-risk valid mode that can meet the deadline.
- If no deadline controls the decision, recommend the lowest-cost valid mode with acceptable risk and product support. Sea is often the economical choice when it is valid and risk is acceptable; air can win when speed or deadline compliance matters.
- If freight is explicitly advisory because destination or booking details are not final, keep the advisory status visible in whatever warning/control fields the template provides and require reconfirmation before booking.
- Set freight reconfirmation according to the freight policy. If freight is included, final-order reconfirmation is normally required even when all listed options are currently valid.

Warnings should be concise but specific: name the stale/invalid mode or freight record, say why it is invalid or risky, and state that it needs a fresh quote when applicable.

## Opportunity And Milestone Reconciliation

For account-review tasks:

1. Fetch the opportunity by exact ID and verify the `customer_id`.
2. Fetch invoices, payments, and revenue journals linked by `opportunity_id`; cross-check invoice IDs from opportunity phases.
3. Fetch customer contact data and use the prompt-named contact if present, then verify it belongs to the same customer/opportunity context.
4. Compute phase or milestone total from opportunity phases or linked invoices. Compare it to `won_amount_usd`.
5. Compute total paid from posted payments or invoice `paid_amount_usd`; compute outstanding from linked invoices and compare to opportunity outstanding amount.
6. Order milestones by opportunity phase order, invoice phase order, or numeric milestone ID.

Milestone status rules:

- If the template asks for invoice state, map invoice status to the invoice lifecycle enum: paid -> `PAID`, unpaid/open/overdue -> `OPEN` when that is the available enum, void -> `VOID`, otherwise `UNKNOWN` if allowed.
- If the template asks for payment state or payment status, map by paid amount: fully paid -> `PAID`, partially paid -> `PARTIAL`, unpaid/open/overdue -> `UNPAID`.
- `amount_unpaid = invoice amount - paid amount`.
- A paid/completed milestone with a posted revenue journal is `RECOGNIZED`.
- A paid/completed milestone without a required posted revenue journal is missing required revenue recognition. Use the exact template enum, such as `REQUIRED_MISSING` or `MISSING_REVENUE_JOURNAL`.
- An unpaid future milestone is not yet revenue-recognition-required. Use the template enum such as `NOT_REQUIRED_UNPAID`.
- Overall recognition is complete when all paid/completed milestones have journals; missing when any paid/completed milestone lacks one; not required when there are no paid/completed milestones.

Milestone IDs are template-sensitive:

- If the template declares or examples imply `MS1`, `MS2`, `MS3`, output those normalized IDs by phase order.
- If the template asks for stable phase IDs or invoice milestone IDs without a normalized enum, use the API's phase or invoice milestone identifier consistently.

## Follow-Up Actions

Derive actions from the reconciled state and the exact enum names in the template.

Accounting:

- If a paid/completed milestone is missing revenue recognition, create the accounting action for that milestone. Use deferred revenue as debit and implementation services revenue as credit when the template asks for accounts.
- If the controlled action enum embeds the milestone ID, choose the enum that names the missing milestone, such as a `RECORD_REVENUE_<milestone>` form when present.
- If all required recognition exists, use the template's verify/no-action enum.

Collections:

- For unpaid milestones, use the invoice due date and amount unpaid.
- If the due date is in the future relative to the prompt's business/as-of date, use the template's monitor-not-due action.
- If due or overdue, use the template's collection-notice or collect-unpaid action.
- If no unpaid balance exists, use the template's no-collection action.

Events and vouchers:

- Fetch the event by prompt ID or by linked `opportunity_id`/`customer_id`, then fetch its voucher by code.
- Map event status to template enums: scheduled/confirmed -> `SCHEDULED`, active/live -> `ACTIVE`, completed -> `COMPLETED`, cancelled -> `CANCELLED`, otherwise `UNKNOWN` if allowed.
- Map voucher status to template enums by uppercasing known statuses, otherwise `UNKNOWN` if allowed.
- Use the voucher discount field required by the template. If the API stores a percentage and the template names a discount amount/value, use the numeric discount value from the voucher record without adding a percent sign.
- If an event invitation task needs a due date and the API does not provide one, use the prompt's stated lead time; if none is stated, use three weeks before the event date only when the template requires a due date. Otherwise omit due dates not in the template.

## Final Validation

Before answering:

- Confirm every output value is supported by a fetched API record, an API policy, or a direct arithmetic derivation.
- Confirm all totals: line totals, EXW totals, freight grand totals, milestone totals, paid totals, unpaid balances, and recognized amounts.
- Confirm every included freight, invoice, payment, journal, event, and voucher is linked to the requested customer and quote/opportunity.
- Confirm stale or distractor records are not silently treated as current valid options.
- Confirm no placeholder strings remain from the template.
- Return the JSON object only.
