# MedBridge Mapping Rules

## General Output Rules

- Return only JSON that validates against `input/payloads/answer_template.json`.
- Preserve template shape. Arrays in templates are examples, not fixed length; expand them to the matching source records when the task calls for multiple lines, milestones, or freight options.
- Use source record IDs and ISO dates exactly as the API gives them after verifying they match the prompt's target account or transaction.
- Normalize enum-like strings to the template casing. For example, API values such as `closed_won`, `paid`, `active`, and `scheduled` usually map to uppercase template enums.
- Use `null` where the template permits null and there is no applicable source value. Do not substitute empty strings for nullable fields.

## Source Matching

Use strict joins before calculating:

- Customer tasks: match `customer_id` and, when available, customer name/contact.
- Quote tasks: match `quote.id`, `quote.customer_id`, quote date, product code, and confirmed quantity.
- RFQ tasks: match `rfq.id`, `rfq.customer_id`, quote date, and requested module/product lines.
- Freight tasks: match `freight.quote_id` plus route/destination and shipment dimensions. Keep stale target-route options if the template asks for current comparison or warnings; exclude records explicitly marked as distractor, mismatch, archived, old benchmark, wrong size, or unrelated route.
- Opportunity tasks: match `opportunity.id`, `customer_id`, invoices/payments/journals by `opportunity_id`, and events/vouchers by both `customer_id` and `opportunity_id`.

## Catalog Pricing

1. Determine the authoritative requested quantity from the prompt and quote/RFQ record. If both are present and conflict, prefer the prompt when it explicitly says confirmed/revised quantity, then verify the quote line supports that revision.
2. Fetch every product or module code required by the template.
3. Select the product tier where `min_qty <= quantity` and either `max_qty` is null or `quantity <= max_qty`.
4. Use:
   - `unit_price_usd` from the selected tier.
   - `lead_time_days` from the selected tier.
   - `shelf_life_months` and `article_number` from the product record.
5. Compute `line_total = quantity * unit_price` and `exw_total_usd = sum(line_total values)`.

## Policy Mapping

Read the policy collection and apply records by `policy_area`:

- `payment_terms`: choose the policy that matches customer status/account type in the customer, quote, or RFQ record.
- `quote_scope` and `incoterms`: decide whether the basis is EXW-only or EXW plus separate freight options.
- `quote_lines`: keep module RFQs at module-line granularity unless the prompt explicitly asks for component pricing.
- `freight`: set reconfirmation flags and validity warnings.
- `quote_validity`: compute offer validity days from quote date when the template asks for offer validity.
- `revenue_recognition`: paid, completed milestones need recognition journals; unpaid future milestones do not.

## Freight Mapping

For each applicable freight record:

- `freight_id`: API `id`.
- `mode`: uppercase API `mode`.
- `freight_cost_usd`: API `cost_usd`.
- `transit_days`: use `transit_days_text` when the template wants text. If the template examples omit the word "days", follow that template style.
- `valid_until`: API `valid_until`.
- `risk_level`, `risk_flag`, or `customs_border_risk`: derive from `route_risk`, normalized to uppercase. Use `NONE` only when the template expects a risk flag and the risk is low.
- `validity_status`: `VALID` when active and valid through the quote date; `STALE` when expired or source-stale; otherwise use the closest enum available in the template.
- `source_is_stale`: true for stale status, expired validity, or stale/expired notes.
- `grand_total_usd`: EXW total plus freight cost.

Recommendation rule: choose the lowest grand total among valid, non-stale, non-mismatch options that do not have high customs or border risk. If all options are risky or invalid, choose the least risky valid option and make reconfirmation/warnings explicit.

## Engagement Reconciliation

Milestone ordering:

- Prefer the template's required milestone identifiers when it specifies them.
- Otherwise order by phase number, phase ID, invoice issue date, or invoice ID in that priority.

Money:

- `phase_total_amount` is the sum of milestone/invoice amounts.
- `total_paid_amount` is the sum of posted payments or invoice paid amounts.
- `outstanding_balance` is the sum of unpaid invoice amounts.
- Journal recognized amount is the sum of posted revenue-journal amounts for paid completed milestones.

Statuses:

- Opportunity stage: `closed_won` -> `WON`; open-like stages -> `OPEN`; lost-like stages -> `LOST`.
- Invoice state: paid invoices -> `PAID`; unpaid/open/overdue invoices -> `OPEN` when the template uses invoice state, unless a more exact enum is available.
- Payment state: fully paid -> `PAID`; partially paid -> `PARTIAL`; unpaid -> `UNPAID`.
- Recognition status: paid milestone with matching posted journal -> `RECOGNIZED`; paid milestone with no matching journal -> use the template's missing-journal enum; unpaid milestone -> `NOT_REQUIRED_UNPAID`.

Actions:

- Missing revenue for a paid milestone: set the accounting action to the template's record-revenue action for that milestone when available, with debit `DEFERRED_REVENUE`, credit `IMPLEMENTATION_SERVICES_REVENUE`, and owner `ACCOUNTING`.
- No missing revenue: use the template's verify/no-accounting action as appropriate.
- Unpaid milestones: if due date is before the as-of date, send a collection notice when that enum exists; otherwise monitor unpaid not due. Populate contact, amount, milestone, and due date from joined records.
- Events and vouchers: use the event/voucher joined to the opportunity and customer. Active or scheduled future events usually require sending the invite unless the template or API says it was already sent.
