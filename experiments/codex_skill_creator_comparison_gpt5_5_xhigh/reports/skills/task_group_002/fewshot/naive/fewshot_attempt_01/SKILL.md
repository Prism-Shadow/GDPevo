---
name: medbridge-sales-ops-json
description: Prepare JSON-only MedBridge Sales Ops quote and engagement reconciliation packages from the task API.
---

# MedBridge Sales Ops JSON Packages

Use this skill when a task asks for an account-ready MedBridge Sales Ops response involving quotes, RFQs, freight options, product catalog tiers, policies, opportunities, milestone invoices, payments, revenue journals, events, or vouchers.

## First Steps

1. Read the user prompt and every file under `input/payloads/`. If an `answer_template.json` or schema file is present, treat it as authoritative for top-level keys, nested field names, field order, null handling, and controlled values.
2. Resolve the API base URL from the runner placeholder, environment variable, or prompt wording. Use only the MedBridge business API endpoints exposed by the task environment.
3. Extract stable identifiers and constraints from the prompt: quote/RFQ/opportunity/customer/event/voucher IDs, product codes, quantities, business date, destination/freight requirements, named contact, and any instruction to exclude freight or avoid component expansion.
4. Query exact record endpoints first. If a record is not directly named, use `/api/search?q=<text>` and relevant collection lists. Collection responses are wrapped as `{"collection": ..., "count": ..., "records": [...]}`.
5. Return only valid JSON. Do not include markdown, prose, citations, or calculation notes outside the JSON object.

## API Records To Join

For quote decision packages, gather:

- Customer record: account status, segment/type, recurrence, contacts, and payment profile.
- Quote or RFQ record: customer, quote date, requested products/modules, quantities, destination, incoterm, status, and source notes.
- Product catalog records: product code, article number, shelf life, cold-chain fields, component list, and price tiers.
- Freight quotes: records matching the quote or route, including mode, cost, transit days, validity date, status, cold-chain support, and route risk.
- Policies: payment terms, freight controls, offer validity, documentation requirements, and account-type rules.

For engagement reconciliation packages, gather:

- Customer and opportunity records, including stage, won amount, contact, owner, outstanding amount, and phases.
- Invoices by opportunity/customer/phase.
- Payments by opportunity and invoice.
- Revenue journals by opportunity, invoice, and phase.
- Related events and vouchers named in the prompt or linked by opportunity/customer.

## Quote And RFQ Rules

- Use the quantity and quote date specified by the prompt unless the API record supplies the same values more specifically. If they disagree, prefer the prompt for the requested scenario but verify the related record identity.
- Select the product price tier where the requested quantity falls within the tier bounds. Treat a missing upper bound as unbounded. Map API tier names such as minimum quantity, maximum quantity, unit price, and lead time into the exact output field names required by the template.
- Compute product totals as `quantity * unit_price`. Compute grand totals as product EXW total plus the freight cost for that option. Preserve cent-level numeric precision; do not stringify money unless the template requires strings.
- For RFQs that request module-level quoting, quote only the requested module lines. Do not expand product components or RFQ composition/distractor lists unless the prompt explicitly asks for component pricing.
- If the prompt says there is no destination or asks for EXW-only pricing, set the template's freight-excluded control and omit freight option calculations.
- Use product catalog metadata for article numbers, lead time, shelf life, cold-chain requirements, and unit details. Do not invent missing catalog fields.
- Derive payment terms and offer controls from the customer payment profile plus matching policy records. Copy controlled policy codes exactly from the API/template rather than paraphrasing them.

## Freight And Recommendation Rules

- Freight validity is date based: an option is current on the quote date when its validity date is on or after the quote date and the record status is usable. Mark expired or unusable records with the template's stale/invalid value.
- Include all freight options requested by the prompt/template. For each option, include the stable freight ID, mode, cost, transit-day text or range, validity date, risk level/flag, and grand total as required.
- Prefer valid, low-risk transport options for recommendations. A cheaper option with expired validity or high border/customs risk should not be recommended without an explicit prompt override.
- If multiple valid low-risk options remain, choose the option that best matches the business request: usually lowest total cost for non-urgent shipments, faster transport for urgent or short shelf-life constraints, and cold-chain-capable transport when the product requires it.
- Set freight reconfirmation flags when required by policy, when any quoted option is expired/stale, when route risk is elevated, or when the prompt asks for final-order freight controls.
- When the template has client warnings, keep them concise and factual: name the invalid/stale mode or freight record, the expiry or risk reason, and the need for reconfirmation.

## Engagement Reconciliation Rules

- Compare the won opportunity amount to the sum of opportunity phases or milestone invoices. Use cent-level equality and expose the template's match boolean.
- Build milestone rows from opportunity phases joined to invoices. Include invoice amount, invoice/payment state, amount paid, amount unpaid, due date, and revenue recognition status under the exact field names requested.
- Determine paid and unpaid amounts from invoice fields when present, cross-checking against posted/successful payments. Unpaid amount is invoice total minus paid amount, clamped at zero.
- A paid milestone requires matching revenue journal coverage. If a posted/current revenue journal covers the invoice or phase for the paid amount, mark it recognized. If the milestone is paid but journal coverage is missing, use the template's missing-revenue-journal status and create the accounting follow-up the template expects. If the milestone is unpaid, mark revenue recognition as not required while unpaid.
- Outstanding balance is the sum of unpaid invoice amounts unless the opportunity record provides a verified outstanding amount matching the invoices. Total paid is the sum of paid invoice amounts.
- For collection follow-up, create a task/action for unpaid milestones. If the due date is in the future relative to the business date, use the template's monitor-not-due action; if due now or overdue, use the collection action.
- For accounting follow-up, create a revenue-recording action for each paid milestone missing journal coverage, including the milestone/phase ID, amount, debit account, credit account, and owner queue when the API/template provides those fields.
- Use the named account contact from the prompt when present; otherwise use the opportunity contact or customer primary contact. Link every follow-up to the customer and opportunity IDs.

## Event And Voucher Rules

- Fetch the event and voucher by the IDs or codes in the prompt. If only one is named, use the event/voucher cross-links to retrieve the other.
- Include event ID, status/date, voucher code, voucher status, discount, max uses/redemptions, owner queue, contact, and invite action only when the template asks for them.
- Convert voucher fields into the template vocabulary: for example, max redemptions may become max uses, and discount percent or fixed discount amount should match the expected output field.
- Create the invitation follow-up when the prompt asks for the event invite/briefing/celebration to proceed and the event/voucher records are active or scheduled.

## Output Discipline

- Preserve the template's shape exactly: keys, arrays, null placeholders, booleans, controlled status strings, and numeric-vs-string types.
- Use ISO `YYYY-MM-DD` dates and stable record IDs from the API.
- Keep arrays in the natural business order unless the template implies another order: quote line order from RFQ/quote records, freight option order from the API or requested mode sequence, and milestone phase order by phase number/name/date.
- Validate the final object with a JSON parser such as `jq` before responding.
- Do not include training-example-specific customer names, record IDs, amounts, or reconstructed answer records in the skill output or final task response unless those values are present in the current task's API records and prompt.
