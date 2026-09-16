# Decision Rules

## Source Selection

- Prefer direct `GET /api/<collection>/<id>` calls for IDs named in the prompt. Use collection endpoints or `/api/search?q=<text>` to find related records only when direct IDs are missing.
- Cross-check linked IDs: quote/RFQ/customer/product for quote work; opportunity/customer/invoice/payment/revenue/event/voucher for reconciliation work.
- Ignore records that are clearly distractors: unrelated customer or opportunity, superseded or archived requests, old quantities, mismatched shipment size, `status: mismatch`, destinations marked as distractor, or IDs/notes that indicate a distractor benchmark.
- Do not split product modules into component SKUs unless the prompt explicitly asks for component-level pricing.

## Product Pricing

- For a quote revision, use the quote record's `line_items` and confirmed quantity. Ignore prior quantity and prior unit price fields except as evidence that a revision occurred.
- For an RFQ/module quote, use `requested_modules`; if the same product code appears more than once, consolidate quantities before pricing unless the template requires original request lines.
- Select the product price tier where `min_qty <= quantity` and either `max_qty` is `null` or `quantity <= max_qty`.
- `unit_price` is the selected tier's `unit_price_usd`.
- `line_total` or `exw_total_usd` is `quantity * unit_price`.
- Product lead time and shelf life come from the selected tier and product record, not from prompt prose.
- Catalog quote validity is normally 30 calendar days from quote date when the standard quote-validity policy applies.

## Freight

- Include freight records linked by `quote_id` that are current for the requested quote. Include a non-distractor stale option when the prompt/template asks for source validity, stale flags, or invalid road/route warnings.
- Exclude freight records that have the right `quote_id` but are old benchmarks, wrong shipment-size records, distractor routes, or mismatch records.
- `grand_total_usd = exw_total_usd + freight.cost_usd`.
- Preserve the API's `transit_days_text` when the template expects a human-readable range. If the template style omits the word `days`, use the numeric range from `transit_days_min` and `transit_days_max`.
- A freight option is valid on the quote date when `valid_until >= quote_date` and the freight status is not stale or mismatch.
- Set `validity_status` to `VALID` for active, unexpired options; `STALE` for expired or stale options; and `MISMATCH` for mismatch records if a template requires exposing them.
- Set `source_is_stale` true when the freight status is stale or `valid_until` is before the quote date.
- Map route risk to template language. For generic risk fields, use `route_risk.upper()`. For customs or border-specific fields, use `HIGH` or `MEDIUM` only when the notes or route risk indicate customs or border risk; otherwise use `LOW`.
- For `risk_flag`, use `NONE` for low risk; use a template-compatible border risk flag for medium/high border risk.
- Freight reconfirmation is required for freight-option quotes because the freight policy says rates must be reconfirmed at final order. Separately report whether all included options are valid on the quote date when the template asks.
- Recommend the cheapest valid, non-stale mode that satisfies stated constraints. Prefer sea when it is valid, materially cheaper, and no delivery deadline or cold-chain constraint makes it unsuitable. Do not recommend a stale, mismatch, or high border-risk road option when a valid lower-risk alternative exists. If a delivery need-by date is present, compare quote date plus product lead time plus maximum transit days against that date.

## Payment And Quote Policies

- Use customer `payment_profile` as the base payment term. Apply policy overrides where a policy clearly matches the customer or quote context.
- New NGO clients without approved credit history use `PREPAY_100`.
- Recurring NGO or recurring approved accounts generally keep the customer payment profile such as net terms unless restricted grant terms override it.
- Indicative quotes without confirmed destination are `EXW_ONLY`, exclude freight, and should not invent freight totals.
- Module RFQs stay at module line level unless the customer explicitly asks for components.
- EXW excludes freight, insurance, import duty, customs clearance, and last-mile handling unless the template asks for separate freight options.

## Opportunity Reconciliation

- Use the opportunity as the spine. Pull invoices, payments, revenue journals, events, and vouchers by `opportunity_id`; also verify `customer_id`.
- Map opportunity stage to template enum: `closed_won` -> `WON`, open/proposal/negotiation-style stages -> `OPEN`, closed-lost/lost stages -> `LOST`.
- `phase_total_amount` is the sum of opportunity phase amounts. `opportunity_matches_phase_total` is true when it equals the won amount at cent precision.
- Order milestones by opportunity phase order, invoice due date, or invoice ID as the template instructs. When the template expects `MS1`, `MS2`, `MS3`, map the ordered phases to those stable milestone IDs instead of exposing API-specific phase IDs.
- Invoice amount, due date, paid amount, and outstanding amount come from the invoice record; posted payments are a cross-check.
- Payment status: paid in full -> `PAID`; zero paid -> `UNPAID`; otherwise `PARTIAL`.
- Invoice state templates that use `OPEN` should map unpaid or overdue invoices to `OPEN`, paid invoices to `PAID`, void invoices to `VOID`, and unclear states to `UNKNOWN`.
- Revenue recognition is required for completed, paid milestones. If a posted revenue journal exists for the invoice/phase, the milestone is `RECOGNIZED`. If paid but no posted journal exists, use the template's missing-recognition enum. If unpaid, use `NOT_REQUIRED_UNPAID`.
- Recognized amount is the sum of posted revenue journals for included milestones. Missing required milestones are paid milestones without posted revenue journals.

## Follow-Up And Event Actions

- For missing revenue journals on paid milestones, route an accounting action to record revenue from deferred revenue to implementation services revenue when the template exposes those accounts.
- For unpaid milestones, create collection or monitoring actions according to the template. If due date is after the current/as-of date, monitor; if due or overdue, send a collection notice. Templates with simpler collection enums may still require a collection task for every unpaid milestone.
- Use the named contact from the opportunity, customer contact record, or prompt after cross-checking consistency.
- Fetch events by prompt `event_id` or by linked opportunity/customer. Fetch vouchers by prompt code, event `voucher_code`, or linked opportunity/customer.
- Event status mapping: scheduled or confirmed -> `SCHEDULED`; live or active -> `ACTIVE`; completed -> `COMPLETED`; cancelled -> `CANCELLED`; otherwise `UNKNOWN`.
- Voucher status should be uppercased when the template uses uppercase enums. Use `discount_percent` as the numeric discount value when the template asks for voucher discount or discount amount.
- If an upcoming scheduled/confirmed event has an active voucher and the template includes invite actions, create the send-invite action named by that template and route it to account management unless the API says another owner.

## Final JSON Check

- Compare the final object against the template before responding. Remove fields not present in the template and fill all required placeholders.
- Use empty arrays only when the template logically permits no matching records; otherwise include each matching source record.
- Avoid explanatory strings unless the template has a warning or task-title field. Warning strings should summarize specific validity or risk issues using current task records.
