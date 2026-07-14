# Clerk Operations JSON Skill

Use this skill for clerk operations tasks that combine local packet materials with the shared Clerk Operations API. Produce the exact JSON object requested by the task template; do not add Markdown, comments, explanations, or extra fields.

## Core Workflow

1. Read the prompt, `answer_template.json`, and the packet payloads. Treat the template as the output contract: keys, enum spellings, row ordering, null rules, dates, times, money precision, and aggregate fields all come from it.
2. Identify target matters from the packet before querying broadly. Include only rows the packet asks for, such as listed citations, docket matters, or `review_needed: true` compliance items. Exclude context rows, similar names, stale-export carryovers, and unrelated queues.
3. For each target, pull live records from the API:
   - `GET /api/cases/<case_number>` for case identity, current status, charges, counsel, sentence fields, and matter type.
   - `GET /api/citations/<citation_number>` for traffic citation identity and any live plan fields.
   - `GET /api/financial-obligations?case_number=<case_number>` for current principal, paid credits, balance, restitution amount, plan, and ledger status.
   - `GET /api/docket?case_number=<case_number>` for live docket history when status or disposition timing matters.
   - `GET /api/fees?county=<county>&matter_type=<type>&effective_on=<YYYY-MM-DD>` for the active fee schedule.
   - `GET /api/payment-policies?county=<county>` for minimum monthly payments, default first due dates, placeholders, and unsupported codes.
   - `GET /api/stale-exports?county=<county>&name=<export_name>` only when the prompt names a stale export or conflict queue.
   - `GET /api/search?q=<text>` is useful for uncertain case/citation identifiers, but verify with exact record endpoints.
4. Resolve the row, then compute aggregates from the finalized rows rather than from stale exports or drafts.

The API root may 404; `/docs` lists endpoints and `/health` confirms availability. Use the base URL supplied in `environment_access.md` or the prompt.

## Source Precedence

Use this precedence when records conflict:

1. `answer_template.json` controls output shape and allowed values.
2. Current local bench sheets, minute cards, hearing notes, counsel confirmations, review flags, receipts, provider notices, and petitions control what happened in the packet.
3. Live API records control identity, court/county, current pre-update case status, charges, docket history, ledger credits, current principal, payment plans, fee schedules, attorney metadata, and payment policy.
4. Stale exports, stale order extracts, draft finance imports, trainee workpapers, and queue hints are warning sources only. They can explain discrepancies or excluded candidates, but they do not override current packet orders or live fee/ledger records.

If a local post-hearing packet says a plea, dismissal, warrant recall, counsel substitution, or revised plan was ordered, use that as the new outcome even if the live case/citation still shows pending or warrant. Use the live record as the before-state for mismatch flags, review actions, deltas, and credits.

## Fee Rules

- Always query the fee schedule with the correct county, matter type, and effective date. Use the disposition/order date unless the prompt explicitly says to use a filing date, review date, or current schedule.
- Apply a fee only when both the schedule and the facts support it. Common triggers:
  - conviction assessment: a conviction is entered.
  - filing assessment: the case/citation filing fee applies under the active schedule.
  - probation fee: probation was ordered and the packet/template supports entering it.
  - restitution administration fee: restitution was ordered; do not enter it when restitution is zero or expressly not ordered.
  - DUI treatment/license fees: treatment or license suspension was ordered.
  - traffic base fine: traffic violation convicted or deferred.
  - speed, traffic school, late fees: only when the active schedule contains the code and the order/facts trigger it.
- Do not assess candidate codes just because they appear in a draft import. Exclude unsupported or untriggered candidates in the output when the template asks.
- Use policy `unsupported_charge_codes` as a warning. A charge code listed there is not an assessment unless an active fee row and the order independently support it.
- Restitution is part of the principal/balance when ordered, even if the template lists only fee codes separately.
- For replacement financial entries, compute corrected balance as corrected principal minus live `amount_paid`; do not discard live paid credits.
- For delta fields, use `corrected_assessment_total - current_ledger_principal`. If no live financial obligation exists, current principal is `0.00` when the template says so.

## Payment Plan Rules

- Use an existing approved live plan when the packet says to keep or use the recorded plan.
- If the judge approves the lowest local amount, use `payment-policies.min_monthly`.
- If a petition/requested amount is approved, use that amount when it is within policy limits; otherwise follow the template's review enum.
- If no first due date was announced, set it to `order_date + first_due_days_after_order` from the county payment policy. For compliance reviews, use the review order date unless the packet gives another order date.
- Compute installments on the plan basis required by the template:
  - new disposition plans usually use original approved principal before payments when requested that way.
  - compliance/revised plans usually use current or corrected balance after credits.
  - if the template has `plan_basis`, set it explicitly.
- When smaller final payments are allowed, use:
  - `full_payment_count = floor(plan_amount / monthly_amount)`
  - `final_payment_amount = remainder rounded to 2 decimals`
  - `total_payment_count = full_payment_count + 1` when the remainder is positive, otherwise `full_payment_count`
  - `final_due_date` is the due date of the last installment, advancing by calendar months from `first_due_date`.
- When no plan applies, use the template's null/zero convention exactly.

## Output Conventions

- Return one JSON object only.
- Use exact enum strings from the template; never invent synonyms.
- Sort rows exactly as required, commonly ascending by `case_number` or `citation_number`. Sort nested charges by `charge_id`; sort fee components/codes by the template rule, often by `fee_code`.
- Use ISO dates `YYYY-MM-DD`, times `HH:MM`, and money rounded to two decimals.
- Use the citation number as `account_reference` when no separate case number exists.
- For unknown identity fields, use the policy/template placeholder such as `TBD from case file` only when the template calls for a placeholder; otherwise use `null` if allowed.
- Count aggregate fields from included finalized records only.
- For compliance corrections, a positive `correction_amount` reduces the live balance. `corrected_balance_due = max(0, ledger_balance_before_adjustment - correction_amount)` unless the template says otherwise.

## Common Pitfalls

- Including stale-export rows, similar-name records, nearby citation numbers, or `review_needed: false` items.
- Trusting draft finance amounts instead of the active fee schedule and live ledger credits.
- Adding optional probation, restitution-admin, public-defender, late, school, or speed fees without both a schedule row and an order/factual trigger.
- Using stale license-suspension starts copied from probation appointment dates. If no delayed surrender date is given, use the judgment/order date.
- Treating live pending/warrant status as final when the packet is a current post-hearing order.
- Dropping live `amount_paid` when replacing principal.
- Forgetting mismatch/review flags when counsel, status, or financial rows differ between live records and the current packet.
- Emitting extra prose, wrong enum casing, unsorted rows, or aggregates copied from source files instead of recomputed.
