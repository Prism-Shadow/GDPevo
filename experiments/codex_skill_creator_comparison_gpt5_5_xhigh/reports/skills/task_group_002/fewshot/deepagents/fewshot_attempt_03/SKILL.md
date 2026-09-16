---
name: medbridge-sales-ops
description: Prepare JSON-only MedBridge Sales Ops API decision packages. Use for tasks that ask Codex to verify customers, RFQs, quotes, product catalog tiers, freight quotes, policies, opportunities, invoices, payments, revenue journals, events, or vouchers from a provided task environment base URL and return an account-ready quote, transport, finance, reconciliation, or follow-up JSON matching a supplied answer template.
---

# MedBridge Sales Ops

## Core Workflow

1. Read the prompt and `input/payloads/answer_template.json` before calling the API.
2. Extract all explicit identifiers, dates, customer names, product codes, quantities, contacts, event IDs, voucher codes, and quote basis instructions from the prompt.
3. Use the base URL supplied by the runner or prompt. Fetch `/api` first when route shapes or field names are unclear.
4. Retrieve records from the relevant endpoint families: customers, products, RFQs, quotes, freight quotes, policies, opportunities, invoices, payments, revenue journals, events, and vouchers.
5. Cross-check linked IDs rather than trusting a single record. Match customers to quotes/RFQs/opportunities, products to requested lines, freight to quote or destination context, invoices/payments/revenue journals to milestone or opportunity IDs, and events to vouchers.
6. Fill the exact template shape. Preserve key names, controlled enum spelling, required ordering hints, nullability, and JSON-only output.

Do not use memorized example values. Derive every final value from the current prompt, current template, and current API records.

## API Retrieval

Prefer direct ID lookups when the prompt gives a stable ID:

```bash
curl -s "$BASE_URL/api/quotes/$QUOTE_ID"
curl -s "$BASE_URL/api/customers/$CUSTOMER_ID"
curl -s "$BASE_URL/api/products/$PRODUCT_CODE"
```

When links are not obvious, fetch the collection endpoint and filter locally. Use `/api/search` only as a discovery aid if direct routes do not reveal the needed records.

Normalize the base URL so route joins do not drop or duplicate slashes. Treat dates as ISO `YYYY-MM-DD`. Compare dates as dates, not strings with missing padding.

## Quote And Freight Packages

For quote, RFQ, catalog, and freight tasks:

- Confirm the customer, quote or RFQ, quote date, requested product/module codes, quantities, currency, and quote basis.
- Use product catalog pricing at the requested level. If a module-level RFQ also exposes component composition, quote only the requested module lines unless the prompt explicitly asks for components.
- Select the catalog tier whose quantity range contains the confirmed quantity. Use the tier price, lead time, shelf life, and article number fields required by the template.
- Compute `line_total` as `quantity * unit_price`. Compute `exw_total` or `grand_total` as the sum of line totals. Keep money as JSON numbers and round only to the cent where the template asks for cent-level currency.
- If the prompt or RFQ has no destination or says freight is excluded, return EXW-only fields and do not invent freight options.
- For freight comparisons, include only freight records linked to the current quote/RFQ/customer/destination context. Preserve the template's mode order when it is explicit; otherwise use the API order or a stable mode order.
- Compute each freight `grand_total` as `exw_total + freight_cost`.
- Mark a freight quote valid on the quote date when `valid_until` is on or after the quote date. Mark it stale or invalid when `valid_until` is before the quote date or the API has an equivalent stale/expired status.
- Set source-staleness, all-options-valid, road-invalid, and warning fields from date validity plus API risk fields. High customs or border risk is a client warning even when the price is low.
- Recommend the mode from an explicit policy when present. Otherwise choose the cheapest valid low-risk option; never recommend an expired/stale option when a valid alternative exists, and avoid high-risk routes when a valid low-risk route exists.
- Set freight reconfirmation from policy controls first. Also require reconfirmation when any included option is stale/expired or has material route risk.
- Use account or policy payment terms exactly as controlled by the records and template.

## Opportunity Reconciliations

For opportunity, invoice, payment, revenue, event, and voucher tasks:

- Fetch the customer and opportunity by the prompt IDs, then collect all invoices or milestones linked to that opportunity and customer.
- Sort milestones by explicit phase number or milestone ID when the template requires ordered output.
- Compute phase total as the sum of milestone or invoice amounts. Compare it to the opportunity won amount using cent-level equality.
- Compute paid amount per milestone from linked payments and invoice state. Use `PAID` when paid amount equals invoice total, `PARTIAL` when it is greater than zero but less than total, and `UNPAID` when no payment is posted, unless the template declares a different invoice/payment enum.
- Compute unpaid amount as `invoice_total - amount_paid`; clamp tiny rounding noise to zero. Compute outstanding balance as the sum of unpaid milestone amounts.
- Use `null` for due dates when the record has no applicable due date or the template expects no due date for fully paid milestones.
- For paid milestones, revenue recognition is required. Mark a milestone recognized only when a revenue journal covers that milestone or invoice. Mark paid milestones without coverage using the missing-revenue enum declared by the template. Unpaid milestones use the template's not-required-unpaid enum.
- Summarize revenue recognition as complete when every paid milestone has journal coverage, missing when one or more paid milestones lack coverage, and not required when no paid milestones require recognition.
- Include the named contact from the prompt or linked account record, and keep customer/opportunity links consistent in every nested task object.

## Follow-Up Actions

Derive tasks from unresolved states, using only enum values declared in the template:

- Create collection follow-ups for unpaid or partial milestones when the template asks for invoice or follow-up tasks. If the due date is after the as-of date, monitor rather than send a collection notice when that enum is available. If the due date is on or before the as-of date, use the collection-notice enum when available.
- Create accounting follow-ups for paid milestones that are missing required revenue journals. Use the action enum that names the affected milestone when such an enum exists; otherwise use the nearest declared record-revenue enum.
- Use accounting debit and credit accounts from the template's controlled values and the API's revenue context. For deferred implementation revenue, record recognition by debiting deferred revenue and crediting implementation services revenue when those enum values are available.
- Include event and voucher controls when the prompt names or links them. Fetch both records and report status, discount, and max-use fields from the API.
- Send or verify event invitations according to the event status, voucher status, existing invite evidence, and template enum names. A scheduled/active event with an active voucher and no sent-invite evidence normally produces the send-invite action.
- For generated task titles, use concise account-ready titles built from the action, milestone/event type, and customer name. Do not add narrative text outside JSON.

## Output Discipline

Return exactly one valid JSON object. Do not wrap it in markdown. Do not add comments, explanations, provenance notes, or fields absent from the template.

Before finalizing, check:

- Every required field in the template is present.
- Every enum value is one of the declared values in the template.
- Every ID and name came from the prompt or API records.
- All arithmetic totals reconcile.
- Freight validity was evaluated against the quote date, not the current system date, unless the prompt explicitly defines an as-of business date.
- Opportunity payment and revenue states are internally consistent.
