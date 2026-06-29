# MedBridge Sales Ops Task Skill

Use the task-provided API base URL as the source of truth. Start with `GET /api` when unsure, then query only the records needed: `/api/search?q=...`, `/api/customers/<id>`, `/api/products/<code>`, `/api/rfqs/<id>`, `/api/quotes/<id>`, `/api/freight-quotes`, `/api/policies`, `/api/opportunities/<id>`, `/api/invoices`, `/api/payments`, `/api/revenue-journals`, `/api/events`, and `/api/vouchers`.

## Source Precedence

- Obey the staged prompt for confirmed IDs, quantities, dates, as-of dates, and requested output shape.
- Use API records for customer names, product tiers, freight status, invoice/payment/journal state, events, and vouchers.
- Use policy records for payment, EXW scope, quote validity, freight reconfirmation, module granularity, and revenue-recognition rules.
- Treat older RFQs, prior quote quantities/prices, component tables, wrong shipment-size freight, stale benchmarks, and distractor routes as distractors unless the prompt explicitly asks to report source-validity concerns.
- Preserve the answer template's field names, enum casing, and literal conventions; do not expand a template literal into a policy terms code unless the template asks for that code.

## Quote And RFQ Rules

- For quote revisions, use the quote's confirmed quantity and product code. Ignore prior line-item quantity and prior unit price when the catalog tier now differs.
- Select the product price tier whose min/max contains the confirmed quantity. `max_qty: null` means no upper bound.
- Compute EXW line totals as `quantity * unit_price`; compute freight grand totals as `exw_total + freight_cost`.
- For module RFQs, quote the requested module lines only. Do not split module RFQs into component SKUs unless the customer explicitly asks for component pricing.
- Indicative RFQs without a confirmed destination are EXW only and exclude freight.
- New NGO clients without approved credit use `PREPAY_100`. Recurring NGO accounts generally use `NET_30_AFTER_PO`. If a customer record has an explicit `payment_profile`, use it unless a policy or prompt restriction overrides it.
- Standard catalog offer validity is 30 calendar days from the quote date.

## Freight Rules

- Match freight by `quote_id`; reject unrelated quote IDs, wrong shipment size, mismatch status, and distractor routes.
- Include only active freight for ordinary comparisons. If the prompt asks for validity/risk concerns, include linked stale/expired options but flag them clearly.
- A freight option is stale/invalid if its status is `stale` or `valid_until` is before the quote date. Active options with `valid_until >= quote_date` are valid on the quote date.
- Freight rates require reconfirmation at final order.
- Copy transit text from `transit_days_text`; use ISO dates from `valid_until`.
- Map route risk to uppercase controlled values when required. Road routes with high or medium border/customs notes should be surfaced as risk flags.
- Recommend the lowest-cost valid active option that satisfies the product's handling needs. Do not recommend stale/expired freight. Medium-risk sea can be acceptable when active, cold-chain-capable, and materially cheaper; low-risk air may be preferred when speed or cold-chain risk dominates.

## Account Reconciliation Rules

- Map opportunity `closed_won` to `WON`; use template enums for other stage/status values.
- Confirm `won_amount` against the sum of opportunity phases or milestone invoices. Set the match boolean from that comparison.
- Use invoice records for due dates, invoice totals, paid amounts, and outstanding balances; use posted payment records to corroborate paid state.
- Payment state: fully paid is `PAID`, some payment is `PARTIAL`, no payment on an open/unpaid invoice is `UNPAID`.
- Invoice state: paid invoices are `PAID`; unpaid issued invoices are usually `OPEN`; void/draft/unknown records map only when the template exposes those enums.
- Revenue recognition is required only for milestones that are both complete and paid. A posted revenue journal means `RECOGNIZED`; a paid complete milestone without a journal is missing/required; unpaid milestones are `NOT_REQUIRED_UNPAID`.
- Revenue actions should use template-specific controlled actions, debit deferred revenue, credit implementation services revenue, and route accounting work to `ACCOUNTING`.
- For unpaid milestones not due as of the prompt's business date, use monitor-style collection actions when available; send collection notices only when due or overdue. Tie follow-up contacts to the account contact named in the prompt/API.
- Use the template's milestone identifier convention. If it declares aliases such as `MS1`, `MS2`, `MS3`, output those in ascending order; otherwise use the stable phase or invoice IDs requested by the template.

## Event And Voucher Rules

- Link events and vouchers by customer ID and opportunity ID as well as the explicit event/voucher IDs.
- Map event and voucher statuses to the template's uppercase enums.
- Use voucher `discount_percent` as the numeric discount value unless the task supplies a true currency discount; use `max_redemptions` as max uses.
- If an invite has not gone out and the event is scheduled/active, use the template's send-invite action and attach the voucher code, event ID, customer ID, and named contact.
- Prefer `follow_up_owner` from the event record for owner queue when it matches a template enum.

## Formatting And Pitfalls

- Return only valid JSON. No markdown, prose, comments, or extra keys.
- Use USD numbers at cent precision where the template asks for money.
- Use ISO `YYYY-MM-DD` dates; use `null` only when the template permits it and no applicable source date exists.
- Keep enum strings uppercase exactly as declared in the template.
- Do not let search results override direct record endpoints; search is useful for discovery but may include distractors.
- Use only the staged prompt, answer template, business API records, and policy records; do not rely on external answer sources.
