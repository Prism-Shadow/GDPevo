# Derivation Rules

## Quote and RFQ Pricing

- For a quote, fetch the quote record, customer, primary product or line products, freight quotes linked by `quote_id`, and relevant policies.
- For an RFQ, fetch the RFQ, customer, and each requested product/module. If no destination is confirmed and the requested scope is indicative EXW, set freight excluded and do not create freight options.
- Select product price tiers with `min_qty <= quantity` and either `quantity <= max_qty` or `max_qty` is null. Use the selected tier's `unit_price_usd` and `lead_time_days`; use product-level `article_number` and `shelf_life_months`.
- Use the current confirmed/requested quantity, not prior quote quantity or prior unit price. Prior values and component lists are distractors unless the template explicitly asks for them.
- Compute each line total as `quantity * unit_price`. Compute EXW/product totals as the sum of line totals.
- Use customer payment profile plus policy records for payment terms. New-client review profiles generally require prepayment; recurring approved accounts generally use the customer's net terms unless policy text says otherwise.
- If the template asks for offer validity, derive it from policy records or RFQ policy fields. Do not guess from the prompt alone if the API provides a policy.
- If the template asks whether health-kit documentation is required, derive it from policy/product family/RFQ scope; emergency health kit module quotes typically require documentation controls.

## Freight Options

- Include only freight records for the exact current quote/RFQ context. Match `quote_id`, requested modes, destination/route, shipment size, and cold-chain need where available.
- Search results may include stale benchmarks or distractors. Exclude records marked as wrong size, old benchmark, unrelated/distractor route, or otherwise not the current option. If the only record for a requested mode is stale/expired, include it only when the template asks for validity/staleness or route-risk concerns.
- A freight option is valid on the quote date when its status is active/current and `valid_until` is on or after the quote date/current business date.
- Set stale/invalid flags when status indicates stale/expired or `valid_until` is before the quote date/current business date.
- Compute freight grand total as `exw_total + freight_cost_usd`.
- Normalize mode to uppercase.
- For generic route risk fields, uppercase the API `route_risk`.
- For customs/border-risk fields, focus on customs or border exposure. Road lanes carry the explicit border/customs risk from route notes; non-road lanes are low unless the record specifically says otherwise.
- Set low-risk flags to `NONE`. For medium/high road or border risk, use the closest enum allowed by the template, such as `MEDIUM_BORDER_RISK` or a high-risk equivalent.
- Freight reconfirmation is required when freight options are included and freight policy says rates must be reconfirmed at final order. It is also required when any included option is stale/expired or high risk.
- Recommend the cheapest valid option with acceptable risk. Do not recommend a stale/expired option or a high customs/border-risk option when a valid lower-risk option exists.

## Opportunity Reconciliation

- Fetch the opportunity, customer, invoices, posted payments, posted revenue journals, linked event, and linked voucher. ID-specific search on the opportunity ID usually returns linked invoice/payment/revenue/event/voucher records.
- Sort opportunity phases/milestones in phase order. When the template expects milestone IDs like `MS1`, `MS2`, map the sorted phase sequence to those ordinal IDs.
- Compare opportunity won amount to the sum of phase or invoice totals at cent precision.
- Invoice amount comes from the linked invoice when present, otherwise from the phase amount. Paid amount comes from invoice `paid_amount_usd` or the sum of posted payments. Unpaid amount is `amount - paid_amount`, bounded at zero.
- Payment status: `PAID` when fully paid, `UNPAID` when paid amount is zero, otherwise `PARTIAL`.
- Invoice state: map paid invoices to `PAID`; open/unpaid invoices with outstanding amount to `OPEN` when the template uses an invoice-state enum; use `VOID` only for voided records.
- Due dates for fully paid milestones are usually not actionable; use `null` when the template allows null. For unpaid or partial milestones, use the invoice due date.
- Paid milestones require a posted revenue journal matching the opportunity and phase or invoice. Mark recognized when such a journal exists. Mark paid-but-unjournaled milestones with the template's missing-recognition enum. Mark unpaid milestones as not required.
- Overall recognition is complete when every paid milestone has a posted journal, missing when any paid milestone lacks one, and not required when no milestone is paid.
- Recognized amount is the sum of posted journal amounts for paid recognized milestones.

## Follow-Up Actions

- If a paid milestone lacks revenue recognition, create the template's accounting action for that milestone. Use deferred revenue as the debit account and implementation services revenue as the credit account when those enums are available.
- If an unpaid milestone has an outstanding balance, create or populate a collection task. If the due date is after the current business date, monitor it; if the due date is on or before the current business date, send/escalate collection according to the template enum.
- Use the named account contact from the prompt when provided; otherwise use the opportunity contact or the customer primary contact.
- For event/voucher tasks, fetch the event and voucher by ID/code or through opportunity search. Normalize statuses to template enums.
- Voucher discount fields use the voucher's numeric discount value, and max-use fields use the voucher redemption limit.
- If an invitation task needs a due date and no API due date exists, use the event follow-up policy if available; otherwise schedule the task ahead of the event by the standard invitation lead time inferred from the records, and never after the event date.
- Owner queues should come from the event/account owner when present, normalized to the template enum. Otherwise use account management for customer-facing event or collection follow-up and accounting for revenue-journal work.
