---
name: medbridge-sales-ops-json
description: Use this skill for MedBridge Sales Ops API tasks that require strict account-ready JSON for quotes, RFQs, EXW catalog pricing, freight comparisons, customer payment terms, milestone invoice/payment/revenue recognition reconciliation, or event and voucher follow-up. Trigger whenever the prompt mentions the MedBridge Sales Ops API, an answer_template.json file, quote/RFQ IDs, opportunities, invoices, payments, revenue journals, freight quotes, policies, events, vouchers, or asks for JSON-only business reconciliation.
---

# MedBridge Sales Ops JSON

Use this skill to solve MedBridge Sales Ops tasks by collecting API evidence, applying the business rules, and returning only JSON that matches the provided template.

## Required Workflow

1. Read the user prompt and `input/payloads/answer_template.json` first. Treat the template as the output contract: same top-level keys, nested keys, array shapes, enum spelling, dates, nulls, and number types.
2. Use the task's supplied API base URL. Do not hardcode a host. Confirm the service with `GET /api`, then fetch only records needed for identifiers in the prompt and their direct links.
3. Collect source records from these endpoints as needed: `customers`, `products`, `rfqs`, `quotes`, `freight-quotes`, `policies`, `opportunities`, `invoices`, `payments`, `revenue-journals`, `events`, and `vouchers`.
4. Prefer direct endpoint fetches for exact IDs. Use `GET /api/search?q=<exact id or exact account text>` to find linked records such as freight for a quote, invoices/payments/journals for an opportunity, or event/voucher records. Keep searches narrow to identifiers or names in the task.
5. Compute values from API records and policy records. Do not paste raw source records or explain the result. Final output must be valid JSON only.

Optional helper:

```bash
python skill/scripts/collect_medbridge.py \
  --base-url "$TASK_ENV_BASE_URL" \
  --prompt input/prompt.txt \
  --template input/payloads/answer_template.json \
  --out /tmp/medbridge_evidence.json
```

The helper gathers relevant records and derived checks. Read `/tmp/medbridge_evidence.json`, then fill the template yourself. The helper is not a final-answer generator.

For field-level details, read `references/field_rules.md` when the task includes quote pricing, freight validity, milestone revenue recognition, or event/voucher actions.

## Quote and RFQ Packages

Use the prompt's quote date, as-of date, confirmed quantity, and requested product/module level as constraints. Verify them against the API; when the prompt asks for a revised confirmed quantity, use that confirmed quantity and choose the matching catalog tier.

For product pricing:

- Fetch the quote or RFQ record, then fetch every referenced product.
- Select the price tier where `min_qty <= quantity` and `quantity <= max_qty`; a null `max_qty` means no upper bound.
- `unit_price` comes from the selected tier. `line_total` is `quantity * unit_price`. EXW total or grand total is the sum of line totals before freight.
- Include product article number, lead time, and shelf life only when the template asks for them.
- For module RFQs, quote the `requested_modules` lines only. Product `components` can help verify context, but do not split module lines into component SKUs unless the user explicitly asks for component-level pricing.

For freight:

- Search by the exact quote ID to find freight records. Include freight records whose `quote_id` matches and whose route/mode is part of the current requested comparison.
- Exclude distractor, benchmark, wrong-size, old-route, or unrelated records even if they mention the same quote ID.
- Do not drop a stale freight quote if it is the current route/mode the template asks you to assess. Mark it stale or invalid instead.
- `grand_total_usd = exw_total_usd + freight_cost_usd`.
- A freight record is valid on the quote date only when its status is active and `valid_until >= quote_date`.
- `source_is_stale` is true when status is stale, validity expired before the quote date, or notes identify the source as stale.
- Use API `transit_days_text` when the target field expects prose. If the template's surrounding schema uses compact route-comparison strings, derive `min-max` from `transit_days_min` and `transit_days_max`.
- For `risk_level`, use `route_risk` uppercased. For fields specifically named `customs_border_risk`, look for customs or border risk in `risk_notes`; otherwise use LOW even when the general route risk is about shelf-life or congestion.
- Recommend the lowest-cost valid option that satisfies stated constraints and avoids high customs/border risk. Exclude stale options from recommendation unless no valid option exists. If there is an explicit urgency or cold-chain constraint, apply that before cost.

For payment and quote policy:

- Fetch `/api/policies` and apply policy records by `policy_area`, customer segment/type, payment profile, RFQ scope, quote basis, and freight status.
- New NGO or unapproved-credit accounts usually map to prepayment. Recurring approved accounts usually keep net terms after PO unless a stricter grant or prompt instruction overrides it.
- Indicative quotes without confirmed destination should be EXW only with freight excluded.
- Freight options generally require reconfirmation at final order; expired or risky options should also set warning/reconfirmation flags.

## Engagement Reconciliation

Use this flow for opportunities, implementation milestones, invoices, payments, revenue journals, and event/voucher follow-up.

1. Fetch the opportunity and customer. Search the exact opportunity ID and customer/account text to collect linked invoices, payments, revenue journals, events, and vouchers.
2. Sort opportunity phases in business order. When the template uses milestone IDs like `MS1`, `MS2`, or phase numbers, map the first phase to `MS1`, second to `MS2`, and so on. If the template explicitly asks for API phase IDs or invoice IDs, preserve those instead.
3. Sum phase amounts and compare them to the opportunity won amount. Sum posted payments or invoice `paid_amount_usd` for total paid. Outstanding balance is invoice amount minus paid amount, or the API outstanding value when it is already reconciled.
4. Normalize stages and statuses to the template enums. For example, closed-won opportunities become `WON`; paid invoices become `PAID`; unpaid open invoices become `OPEN` for invoice state and `UNPAID` for payment state.
5. For fully paid milestones, output `due_date: null` when due date is used for follow-up work. For unpaid or partial milestones, use the invoice due date.
6. A paid milestone needs a posted revenue journal matched by opportunity plus invoice or phase. If present, mark it recognized. If missing, mark it with the template's missing-journal enum. Unpaid milestones are not required for revenue recognition yet.
7. Recognized amount is the sum of matched posted revenue journals. Missing-required milestones are paid milestones with no matched posted journal.
8. If a paid milestone is missing revenue recognition, create the accounting action requested by the template using deferred revenue as the debit and implementation services revenue as the credit.
9. For unpaid milestones, create or route the collection task requested by the template. If the due date is after the as-of date, monitor it; if due or overdue, send a collection notice.
10. Fetch event and voucher records when the prompt or linked search results identify them. Map event and voucher status to uppercase template enums. Voucher discount fields use the numeric discount value from the voucher record. If the template asks for an invitation task due date and the API has only an event date, schedule it before the event using the account/event policy implied by the records and prompt.

When the prompt gives a business-facing customer or contact name that differs from the CRM record, use the prompt's display name for display fields but continue to use API IDs and financial facts for reconciliation.

## Final JSON Checklist

Before replying:

- The response is only JSON: no markdown, prose, comments, or code fences.
- Every required template key is present, with no extra keys unless the template allows them.
- Enums match the template spelling exactly.
- Money is numeric, not string. Use cent-level values when requested.
- Dates are ISO `YYYY-MM-DD` or null where the template permits null.
- Totals recompute correctly from line items, freight costs, invoices, payments, and journals.
- Freight validity is evaluated against the quote date or as-of date from the task, not the current real-world date.
- The recommendation and warning fields explain the computed risk only through the requested JSON fields.
