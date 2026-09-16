# MedBridge Workflow Derivations

These rules are for MedBridge Sales Ops API tasks that request a JSON answer matching a local template. Apply only the sections relevant to the current template.

## Shared API Shape

Common collections:

- `customers`: account identity, contacts, segment, recurrence, payment profile, grant notes.
- `products`: article numbers, price tiers, lead times, shelf life, cold-chain flags, weight and volume.
- `rfqs`: requested modules or products, RFQ date, customer, incoterm, destination status.
- `quotes`: confirmed quote revisions, primary product, confirmed quantity, customer, quote date, incoterm.
- `freight-quotes`: mode, cost, validity, status, destination, risk notes, route risk, shipment size, cold-chain support.
- `policies`: reusable payment, EXW, freight, quote-validity, module, and revenue-recognition rules.
- `opportunities`: won/open/lost CRM opportunities with phases and invoice IDs.
- `invoices`: milestone invoice state, paid and outstanding amounts, due dates.
- `payments`: posted payment records by invoice and opportunity.
- `revenue-journals`: posted recognition records by invoice, phase, or opportunity.
- `events`: linked briefing or celebration events and voucher codes.
- `vouchers`: offer status, discount value, max redemptions, and event linkage.

## Quote Revision With Freight

Use this procedure when the prompt names a quote ID and asks for revised EXW pricing plus freight options.

1. Fetch the quote, customer, primary product or line product, `/policies`, and linked freight candidates.
2. Confirm the product and quantity from the prompt against the quote line. Use the prompt's confirmed quantity if it is explicit, but verify it matches the API.
3. Select the active catalog price tier where `min_qty <= quantity` and either `max_qty` is null or `quantity <= max_qty`.
4. Set unit price, lead time, shelf life, and article/catalog tier fields from the selected product tier and product record.
5. Compute `exw_total = quantity * unit_price`.
6. Select freight candidates with `quote_id` equal to the current quote. Exclude records that clearly mark themselves as distractors, old benchmarks, wrong route/size, or unrelated destinations. If one current route is stale or expired and the template asks for validity or warnings, include it and flag it instead of silently dropping it.
7. Compute `grand_total = exw_total + freight_cost` for each selected freight option.
8. Derive freight validity:
   - `VALID` when status is active and `valid_until >= quote_date`.
   - `STALE` when status is stale, inactive, or `valid_until < quote_date`.
   - `source_is_stale` is true under the same stale conditions.
   - `all_freight_options_valid_on_quote_date` is true only if every selected option is valid through the quote date.
9. Freight reconfirmation is required whenever freight options are included and the policy says freight rates must be reconfirmed at final order. Keep it false for EXW-only RFQs with freight excluded.
10. For risk fields:
   - `risk_level` usually maps `route_risk` to uppercase.
   - `customs_border_risk` should focus on customs or border exposure in `risk_notes`; use high or medium only when the record actually indicates customs/border risk. Otherwise use low even if a route has non-customs logistics concerns.
   - `risk_flag` is `NONE` for low risk. For border/customs concerns, use the template's controlled label pattern such as `<LEVEL>_BORDER_RISK`.
11. Preserve the transit-day format expected by the template. If the template or prompt expects prose, use `transit_days_text`. If it expects compact ranges, use `transit_days_min`-`transit_days_max` without the word `days`.
12. Recommend the lowest total option that is valid, current, compatible with cold-chain requirements, and not high customs/border risk. Do not recommend a stale or expired option just because it is cheaper. If all options have issues, choose the least risky current option and surface the warning fields.

Payment and policy fields:

- Use customer `payment_profile` when it already matches the template's payment-term code.
- New NGO or no approved credit history maps to prepayment when the policy requires it.
- Recurring NGO and recurring commercial quote revisions usually keep net-after-PO terms unless grant terms override them.
- `quote_basis` should mirror the template enum: EXW-only when freight is excluded, otherwise EXW plus freight options.
- `customer_policy` can be derived from customer segment or recurrence when the template asks for a concise account policy code.

## Indicative RFQ Module Quote

Use this procedure when the prompt names an RFQ and asks for an indicative module-level quote.

1. Fetch the RFQ, customer, `/policies`, and each product in `requested_modules` or requested line list.
2. Quote only the requested product/module lines. Ignore product `components` and any composition distractors unless the prompt explicitly asks for component-level pricing.
3. For each requested module, select the product tier matching the requested quantity and compute `line_total = quantity * unit_price`.
4. Fill article number, lead time, shelf life, and unit price from the product record.
5. Sum line totals for the grand total.
6. If destination is pending or the policy/template says EXW only, set freight excluded true and do not invent freight.
7. Use standard quote validity from policy when the template asks for offer validity days.
8. Set documentation booleans from prompt, customer grant terms, product family, and template expectation. Health-kit or NGO donor review prompts often require WHO or donor documentation when the field is present.

## Opportunity, Invoice, Payment, And Revenue Reconciliation

Use this procedure when the prompt names an opportunity and asks for account, finance, milestone, revenue, event, or voucher reconciliation.

1. Fetch the opportunity and customer directly.
2. Search by opportunity ID and collect linked invoices, payments, revenue journals, events, and vouchers. If the prompt names an event ID or voucher code, fetch those directly too.
3. Sort opportunity phases in natural phase order. When the template uses normalized milestone IDs such as `MS1`, `MS2`, `MS3`, map the sorted phases to those IDs. Otherwise use the stable ID requested by the template.
4. Compute `phase_total_amount` from phase amounts and compare it to the opportunity won amount.
5. Compute total paid and outstanding balance from invoices or posted payments, preferring invoice totals when they agree with payments.
6. Stage mapping:
   - `closed_won` -> `WON`
   - open or active stages -> `OPEN`
   - closed lost stages -> `LOST`
7. Invoice and payment state:
   - Fully paid invoice: payment state `PAID`; invoice state `PAID`.
   - Some paid and some outstanding: payment state `PARTIAL`; invoice state usually `OPEN`.
   - No paid amount with outstanding amount: payment state `UNPAID`; invoice state `OPEN` unless the template uses `UNPAID` for invoice state.
   - Void or cancelled invoice: use the template's void/cancelled enum if available.
8. For paid milestones, set due date to null when the template treats paid items as closed. For unpaid/open milestones, use the invoice due date.
9. Revenue recognition:
   - A complete and paid milestone requires a posted revenue journal matching the opportunity plus invoice or phase.
   - If the posted journal exists, mark the milestone recognized and include it in recognized milestones.
   - If the milestone is paid/complete but no matching posted journal exists, mark it missing with the template's label, such as `MISSING_REVENUE_JOURNAL` or `REQUIRED_MISSING`.
   - If the milestone is unpaid, mark it `NOT_REQUIRED_UNPAID`.
   - Overall status is complete only when every paid milestone that requires recognition has a matching posted journal.
10. Revenue amount is the sum of posted recognition journal amounts for recognized paid milestones.

## Follow-Up Actions

Always choose action labels from the current answer template.

Accounting actions:

- If a paid milestone is missing a required revenue journal, create or route the accounting action for that milestone.
- Use normalized account enums when the template asks for debit and credit accounts: deferred revenue as the debit and implementation services revenue as the credit for revenue recognition.
- If no paid milestone is missing recognition, use the template's no-action or verify-only label.

Collection actions:

- For unpaid milestones, include a collection or monitoring task when the template has one.
- If the template has a simple `COLLECT_UNPAID_MILESTONE` action, use it for unpaid milestone follow-up and set the due date to the invoice due date.
- If the template distinguishes due state, compare the invoice due date to the prompt's as-of date or the API `generated_at` date. Use monitor-not-due before the due date, send-collection-notice on or after the due date, and no collection action when nothing is outstanding.

Event and voucher actions:

- Use explicitly named event IDs or voucher codes when present; otherwise use linked records from the opportunity search.
- Map event and voucher statuses to uppercase template enums.
- If the prompt asks to send a briefing, celebration, or invitation and the event/voucher are usable, choose the corresponding send-invite action from the template.
- Copy voucher code, status, discount numeric value, and maximum uses from the voucher record. If the template says discount amount but the API exposes a percent value, use the numeric discount value as provided rather than inventing currency semantics.

## Final Consistency Pass

Before finalizing:

- Recalculate every total from its components.
- Check that each line, freight option, milestone, task, event, and voucher is linked to the requested customer and primary record.
- Check every controlled enum against the template text.
- Remove any fields not present in the template.
- Ensure the response is one JSON object with no surrounding prose.
