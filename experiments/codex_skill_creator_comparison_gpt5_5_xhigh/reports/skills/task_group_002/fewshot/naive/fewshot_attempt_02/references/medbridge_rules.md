# MedBridge Sales Ops Rules

Use these rules after fetching the relevant MedBridge Sales Ops API records and reading the answer template.

## Template-First Mapping

- Treat `answer_template.json` as the required schema, key set, array organization, data types, and enum vocabulary.
- Preserve key order when practical.
- Expand an example array item into all records requested by the prompt and supported by API data.
- Prefer exact API field values for IDs, names, dates, statuses, article numbers, lead times, shelf life, risk labels, policies, and payment terms.
- Derive booleans and totals from API facts when no direct field exists.

## Quote and RFQ Pricing

1. Confirm the quote or RFQ, customer, quote date, product/module lines, requested quantities, catalog details, and policies.
2. For product tiers, select the tier whose minimum and maximum quantity bounds contain the confirmed quantity. Treat a missing maximum as open-ended.
3. If the prompt asks for module-level quoting, quote only the requested module lines even if product records expose component composition.
4. Compute each line total as `quantity * unit_price`.
5. Compute EXW total or grand total as the sum of applicable line totals before freight.
6. Use the policy record, customer account type, or quote record for payment terms, quote basis, offer validity, documentation flags, and freight-control flags.
7. If no destination or transport estimate is requested or available, mark freight as excluded and use the EXW-only basis required by the template.

## Freight Decisions

- Fetch freight quotes linked to the quote/RFQ, product, customer, route, or destination requested by the prompt.
- Include the current transport options requested by the prompt; common modes are AIR, SEA, and ROAD.
- A freight quote is valid on the quote date when `valid_until >= quote_date`. Mark it stale or invalid when `valid_until < quote_date`.
- Compute each freight grand total as `exw_total + freight_cost`.
- Copy transit windows exactly from the API. Do not invent units; use the template style when it implies one.
- Copy risk fields from the freight record or route policy. Map only as needed to the template's enum names.
- Set `all_freight_options_valid_on_quote_date` true only if every included option is valid on the quote date.
- Set stale/invalid warning booleans true when any included option is expired, stale, or explicitly invalid.
- Set freight reconfirmation required when a policy requires it, when any selected option is stale/expired, or when the route has material risk requiring confirmation.
- Recommend the lowest-cost valid option that satisfies policy and risk constraints. Avoid stale, expired, invalid, high-risk, or warned options unless the prompt or policy explicitly requires them. If policy names a preferred mode, use it when it is valid and not disqualified by risk.

## Opportunity Reconciliation

1. Confirm opportunity, customer, named contact, invoices or milestones, payments, revenue journals, and any linked event/voucher.
2. Sort milestones by phase number or milestone ID when the template requests stable ordering.
3. Compute phase or invoice total as the sum of milestone/invoice amounts.
4. `opportunity_matches_milestones` or equivalent is true when the won amount equals the phase/invoice total after cent-level rounding.
5. Compute paid amount per milestone from payment records. Compute unpaid amount as `invoice_total - amount_paid`, floored at zero after rounding.
6. Payment state:
   - `PAID`: paid amount is at least the invoice total.
   - `PARTIAL`: paid amount is greater than zero and less than the invoice total.
   - `UNPAID`: paid amount is zero.
   - `UNKNOWN`: required invoice/payment data is absent or contradictory.
7. Invoice state should come from the invoice record when the template has separate invoice and payment states.
8. Outstanding balance is the sum of unpaid amounts, or won amount minus total paid when that is the only reliable basis.

## Revenue Recognition

- Revenue recognition is required for paid milestones.
- Mark a paid milestone `RECOGNIZED` when a matching revenue journal covers it.
- Mark a paid milestone missing when payment is complete but the required journal is absent. Use the exact enum required by the template, such as `REQUIRED_MISSING` or `MISSING_REVENUE_JOURNAL`.
- Mark unpaid milestones with the template's unpaid/no-recognition-required enum, such as `NOT_REQUIRED_UNPAID`.
- Recognized amount is the sum of recognized paid milestone amounts or journal amounts, using the API's reliable monetary field.
- Overall recognition status is complete only when every paid milestone has required journal coverage.

## Follow-Up and Action Values

- Use controlled action values declared in the template; do not invent near-synonyms.
- For unpaid milestones, create collection tasks when the template includes follow-up tasks. Use the contact named in the prompt or linked customer contact.
- If an unpaid milestone is not yet due as of the business date, use a monitor action when available. If it is due or past due, use a collection notice action when available.
- For paid milestones missing revenue journals, create or select the accounting action for recording revenue. Use the milestone-specific enum if the template provides one.
- Use accounting accounts from the template enums and policy context. For implementation/service revenue release, debit deferred revenue and credit implementation services revenue when those enum values exist.
- For events and vouchers, copy event status, event date, voucher status, discount, max uses, event ID, and voucher code from API records.
- Choose the invite action requested by the template for scheduled or active customer events when the prompt asks to route an invitation and no API fact indicates it is already complete.

## Final Checks

- Re-read the prompt for any instruction to exclude freight, quote at module level, include a named event/voucher, or treat a stated date as the business date.
- Re-read the template for exact field names and enum spelling.
- Ensure totals add up and booleans agree with the dates, policies, and selected records.
- Return a single JSON value and nothing else.
