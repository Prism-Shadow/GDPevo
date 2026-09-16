---
name: medbridge-sales-ops-solver
description: Solve MedBridge Sales Ops API tasks that require quote/freight decisions or account, invoice, revenue, event, and voucher reconciliations.
---

# MedBridge Sales Ops Solver

Use this skill when a task references the MedBridge Sales Ops API and asks for an account-ready JSON package for quotes, RFQs, freight options, opportunity milestones, invoices, payments, revenue recognition, events, or vouchers.

## Operating Rules

- Return only valid JSON matching the supplied `input/payloads/answer_template.json`; do not add markdown, comments, or explanatory text.
- Treat the answer template as the output contract. Preserve its object shape, field names, controlled enum values, array intent, date format, and nullability.
- Use the task runner's API base URL as the business source of truth. Do not infer customer, catalog, quote, freight, policy, invoice, payment, revenue, event, or voucher values from memory.
- Extract identifiers, names, quantities, quote dates, current business dates, contacts, event IDs, and voucher codes from the prompt, then verify them through the API.
- Keep product/RFQ outputs at the requested item level. If the API exposes component composition for a module but the prompt asks for module-level quoting, do not expand components unless the template explicitly requires them.
- Use cent-level arithmetic for money. JSON numbers may omit trailing zeroes, but calculations should be exact to cents.
- Prefer stable record IDs from the API. Do not invent IDs, customer names, status values, payment terms, policy codes, or warning text facts.

## API Access

The allowed API is read-only and normally exposes these resource collections:

- `/api/search`
- `/api/customers`
- `/api/products`
- `/api/rfqs`
- `/api/quotes`
- `/api/freight-quotes`
- `/api/policies`
- `/api/opportunities`
- `/api/invoices`
- `/api/payments`
- `/api/revenue-journals`
- `/api/events`
- `/api/vouchers`

Most records can also be fetched directly as `/<collection>/<id>` under `/api`, for example `/api/quotes/{id}` or `/api/vouchers/{code}`. When in doubt, call `/api/search?q=<identifier-or-name>` and then fetch the related records directly.

Optional helper: [`tools/fetch_medbridge.py`](tools/fetch_medbridge.py) can dump selected collections, direct resources, and search results using only Python's standard library.

Example usage:

```bash
python skill/tools/fetch_medbridge.py "$TASK_ENV_BASE_URL" --search "<id-or-customer-name>" --resource "quotes/<quote_id>"
```

## General Workflow

1. Read the prompt and answer template before querying data.
2. Identify the task family:
   - Quote/RFQ/freight decision package.
   - Opportunity, milestone, invoice, payment, revenue, event, and voucher reconciliation.
3. Query the API for the primary record named in the prompt, then query linked records by IDs and foreign keys.
4. Cross-check prompt assertions against API data. Use the prompt only for explicit requested quantities, business dates, requested contacts, and output scope when those are the user-confirmed decision inputs.
5. Populate the template fields from verified records and deterministic calculations.
6. Validate the final response as JSON and check that every enum value appears in the template's allowed values.

## Quote And RFQ Packages

Fetch and reconcile:

- Customer record and customer/account policy.
- Quote or RFQ header and requested line items.
- Product catalog records and price tiers.
- Freight quotes when transport comparison is requested.
- Policy records controlling quote basis, payment terms, offer validity, documentation requirements, and freight reconfirmation.

Pricing rules:

- Select the catalog tier where the confirmed quantity falls within `min_quantity` and `max_quantity`, inclusive. If a tier has no upper bound, treat it as open-ended.
- Use the selected tier's `unit_price`, `lead_time_days`, and `shelf_life_months`.
- `line_total = quantity * unit_price`.
- `exw_total = sum(line_total)` for multi-line RFQs, or `confirmed_quantity * unit_price` for a single quote line.
- `grand_total = exw_total + freight_cost` for each freight option.
- Quote/RFQ currency should come from the template/policy/API; the observed MedBridge tasks use USD.

Freight and recommendation rules:

- Include the freight options requested by the template or prompt. When the template implies modes, preserve that mode order; otherwise use the API's relevant option order.
- Preserve API values for freight ID, mode, cost, transit-days text, validity date, route risk, and risk flags unless the template requests a normalized enum.
- A freight quote is valid on the quote date when `valid_until >= quote_date`.
- Mark stale or invalid freight when `valid_until` is before the quote date, or when the API source status says the rate is stale/invalid.
- `all_freight_options_valid_on_quote_date` is true only if every included freight option is valid on the quote date.
- `freight_reconfirmation_required` is true when the applicable policy requires reconfirmation or any included freight quote is stale/expired.
- Do not recommend a stale, expired, invalid, or high border-risk mode when a valid low-risk option exists.
- Prefer the lowest total valid low-risk option that satisfies policy and request constraints. A cheaper stale/high-risk road quote should be warned about rather than recommended.
- If no destination or transport estimate is available, quote EXW only, set freight-excluded controls from the template, and omit freight options unless the template requires an empty list.
- Warning strings should be concise and fact-based: cite reconfirmation requirements, expired `valid_until` dates, and high route/customs risk only when those facts are present in the API data.

Policy fields:

- Fill `payment_terms`, `customer_policy`, `quote_basis`, `offer_validity_days`, documentation flags, and freight controls from the matched customer/account/quote policy.
- New-account NGO style policies may require prepayment and documentation; recurring-account policies may allow net terms. Always verify the exact values from policy/customer records.

## Opportunity And Engagement Reconciliations

Fetch and reconcile:

- Customer record and named contact.
- Opportunity record and stage/won amount.
- Milestone or invoice phase records linked to the opportunity.
- Payments linked to each invoice or milestone.
- Revenue journals linked to paid milestones.
- Event and voucher records named in the prompt or linked to the account.

Milestone and balance rules:

- Sort milestones by phase number or milestone ID when the template asks for ordered phases.
- `phase_total_amount = sum(milestone or invoice amounts)`.
- `opportunity_matches_phase_total` or equivalent is true when the won amount equals the milestone total to cents.
- `total_paid_amount = sum(payments applied to included milestones)`.
- `outstanding_balance = sum(invoice amount - paid amount)` or equivalently `won_amount - total_paid_amount` when all milestones are included.
- Payment status:
  - `PAID` when paid amount equals invoice/milestone amount.
  - `PARTIAL` when paid amount is greater than zero and less than the amount due.
  - `UNPAID` when paid amount is zero and the invoice/milestone remains open.
  - Use `UNKNOWN` only if the template allows it and the API lacks enough state to decide.
- Paid milestones should normally have `due_date: null` when the template uses due date as an unpaid follow-up date; otherwise preserve the API due date if the template semantics require invoice due dates.

Revenue recognition rules:

- A paid milestone requires a matching revenue journal.
- Use the template's enum vocabulary:
  - recognized paid milestone with journal: `RECOGNIZED`.
  - paid milestone missing a journal: `REQUIRED_MISSING` or `MISSING_REVENUE_JOURNAL`, whichever enum the template declares.
  - unpaid milestone: `NOT_REQUIRED_UNPAID`.
- `recognized_milestones` contains only paid milestones with matching journals.
- `missing_required_milestones` contains paid milestones missing required journals.
- `recognized_amount` is the sum of recognized paid milestone amounts or journal amounts, using the API's accounting records when supplied.
- Overall recognition is complete only when every paid milestone has revenue journal coverage; it is missing when any paid milestone lacks required coverage.

Follow-up and action routing:

- Create collection follow-ups for unpaid or partially paid milestones when the template asks for tasks/actions.
- If an unpaid milestone is not yet due as of the business date, use the template's monitoring action. If it is due or overdue, use the template's collection notice/action. If nothing is unpaid, use the no-action enum.
- For a missing revenue journal on a paid milestone, use the template's accounting action for that milestone, with accounting as owner. When debit/credit accounts are requested for implementation-service revenue recognition, debit deferred revenue and credit implementation services revenue unless API policy says otherwise.
- Event invitation tasks should use the verified event ID/status and voucher code/status. Send or route the invitation when the event is scheduled/active, the voucher is active, and the prompt asks for the invite/briefing/celebration task.
- When a follow-up task needs a due date but the API does not provide a task due date, use a defensible business date from the related record: invoice due date for collections; an invitation lead date from the event policy if present. If no policy exists, derive the invitation due date from the event date only when the template examples/fields require a concrete date.
- Use the prompt-named contact only after verifying the contact is linked to the customer/opportunity. Populate contact fields exactly as the API records spell the name.

## Final JSON Checklist

- The output parses as JSON.
- No field from the template is missing unless the template itself makes it optional.
- Every enum value is one of the values declared in the template.
- Every money total reconciles to cents.
- Every date is ISO `YYYY-MM-DD` or `null` where allowed.
- Arrays are ordered by template intent: product line order, mode order, milestone order, then action priority.
- The response contains no task-solving notes, markdown, citations, or unrequested fields.
