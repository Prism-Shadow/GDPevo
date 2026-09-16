---
name: court-closeout-reconciliation
description: Reconcile court closeout packets into schema-valid JSON using local payloads and Court Operations Portal records. Use for criminal sentencing closeouts, traffic violation dispositions, payment petitions, installment plans, probation referrals, license suspension orders, fee schedule and payment-policy checks, unsupported-fee exclusions, placeholder handling, docket/register actions, and batch totals.
---

# Court Closeout Reconciliation

Use this skill when a task asks for a clerk-ready JSON closeout packet based on local court materials plus a Court Operations Portal. The output must follow the provided `answer_template.json`, not a prose summary.

## Workflow

1. Read the prompt, `answer_template.json`, and every local payload.
2. Identify the target matters, jurisdiction, hearing/disposition dates, named portal endpoints, required sort rules, enums, placeholder text, and currency/date formatting rules.
3. Resolve the portal base URL from the task materials. Fetch each endpoint named in the prompt. If endpoint filtering is available, query by target case, citation, petition, jurisdiction, or form family; otherwise fetch and filter locally. Use `/api/search` to cross-check identities, stale references, or records not obvious from endpoint names.
4. Build a source table per matter:
   - local hearing or sentencing notes
   - petition or financial worksheet data
   - portal case/citation/charge/docket records
   - current fee schedules and payment policies
   - current form metadata
   - known stale, draft, or unsupported local notes
5. Reconcile conflicts, compute financials and dates, then populate the template exactly.
6. Sort every list according to the template. If no explicit sort is given, use ascending matter identifier.
7. Return JSON only. Use numeric money values rounded to cents, ISO dates, ISO local datetimes, `null` where the schema calls for it, and enum values exactly as written.

## Authority Rules

- Prefer signed/final hearing results, current portal records, current fee schedules, current payment policies, and current form metadata over draft worksheets, carried-forward finance queues, old local schedules, sticky notes, obsolete form footers, or intake scratchpads.
- Do not enter a disposition or post financials for a matter that was continued, unsigned, deferred for lack of final order, or otherwise pending. Mark it as held/excluded using the schema's status/action fields, set financial posting to zero, and use `null` disposition or entry dates when required.
- Use portal/CMS identity data when verified. When a required identifier or contact detail is genuinely absent, do not infer it from similar names or surrounding records; use the exact placeholder required by the materials and list the placeholder field if the schema asks.
- Classify counsel from the reliable record, not abbreviations alone. Treat appointed-private counsel separately from public defender representation, especially when deciding public-defender user-fee eligibility.
- Use hearing notes to resolve plea, finding, conviction count, dismissed/amended-away count, sentence, and departure status when the portal or worksheet carries a stale draft value.

## Financial Reconciliation

- Start from the final disposition and current schedule/policy. Add only fees, fines, costs, assessments, surcharges, restitution, or account charges supported by the final order, active fee schedule, active payment policy, or current form instructions.
- Exclude unsupported post-disposition charges such as late, collection, DMV, returned-check, traffic-school, account-management, restitution, attorney, reporter, copy, certification, or other add-ons unless a current policy/order supplies the triggering event and amount.
- Use current schedule amounts for date-sensitive assessments and violation fines; do not use archived amounts or statutory-maximum notes as the starting balance unless the current schedule/policy specifically says to.
- Add controlled-substance or lab assessments only when the final conviction still qualifies. Omit them when the controlled-substance count was amended away or no qualifying conviction was entered.
- Public-defender user fees require both actual public-defender representation and current fee/policy support. Do not apply them to retained or appointed-private counsel.
- For each matter, compute line-item totals from the included fee items. Batch totals must equal the sum of posted matter totals only; held or excluded matters contribute zero unless the schema says otherwise.

## Payment Plans

- Classify petitions from the materials and portal policy: initial installment, subsequent review, deferred payment, exempt/no payment, or the task's equivalent enum.
- Use the approved or policy-selected installment amount, down payment, interval, first due date, return date, and application order from the petition and current payment policy.
- Compute the scheduled balance as `total_due - down_payment`.
- For installment plans, calculate:
  - `full_installment_count = floor(scheduled_balance / regular_installment_amount)`
  - `remainder = scheduled_balance - full_installment_count * regular_installment_amount`
  - If the remainder is greater than zero, add one final installment for that amount.
  - If the remainder is zero, the final payment amount is the regular installment amount and total installments equals the full installment count.
- Compute the final due date by advancing from the first due date by `total_installments - 1` intervals, preserving the day of month when possible and using the task's interval rules.
- Compare the selected installment with disposable income and policy minimum/maximum bands to choose the support classification. Do not override the template's enum vocabulary.
- If restitution is present and policy or petition materials direct priority payment, set the payment application order accordingly; otherwise use fines-and-costs-only or the applicable policy enum.
- Exclude account fees when current policy does not authorize them, even if an old counter note or form copy shows a fee row.

## Form Packets

- Use current portal form metadata when available; local excerpts are supporting evidence, not substitutes for current form identity.
- For probation referral forms, prepare the referral only when supervised probation was ordered. If no referral order was signed, mark the form as not ordered or not applicable per schema.
- For license suspension/payment-order forms, use the basis stated by the disposition or policy. For DUI-style license consequences, conviction date usually controls unless the authoritative materials say release date or petition date controls.
- Use the citation number, case number, or account number as the account reference according to current form instructions. If no separate account exists and the form allows citation-as-account, use the citation/matter identifier.
- Preserve missing driver-license numbers, SSNs, addresses, phone numbers, probation officers, office locations, and similar absent details as placeholders rather than inventing values.

## Quality Checks

- Validate that all required top-level keys and nested required keys from `answer_template.json` are present.
- Verify every enum value appears in the template or source materials.
- Recalculate every matter total, installment count, final payment amount, final due date, and batch total after populating the object.
- Check that excluded fees are not also included in totals.
- Check that pending/held matters have no posted financial total.
- Check list ordering immediately before final output.
