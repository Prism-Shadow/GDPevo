# Clerk Operations JSON Skill

Use this skill for court-clerk post-hearing packets that combine local payloads with the shared clerk operations API.

## Workflow

1. Read the prompt, local packet, and `answer_template.json` first. The template controls required keys, enum values, ordering, nullability, date/time formats, and whether amounts are principal, balance, delta, or correction values.
2. Extract only the target matters named by the packet. Exclude context rows, stale-export lookalikes, and items marked informational or not needing review.
3. Query the live environment for each target:
   - `/api/cases/<case_number>` or `/api/citations/<citation_number>`
   - `/api/financial-obligations?case_number=...`
   - `/api/docket?case_number=...`
   - `/api/fees?county=...&matter_type=...&effective_on=YYYY-MM-DD`
   - `/api/payment-policies?county=...`
   - `/api/stale-exports?county=...` only for conflict checks
   - `/api/search?q=...` only to look for missing live context
4. Build the answer object exactly in template shape. Return JSON only.

## Source Precedence

- Local hearing minutes, bench packets, counsel confirmations, provider notices, receipts, and petitions control the current order when live records are stale.
- Live case/citation records control identity, current status baseline, charges, counsel, and citation details unless a newer local order or confirmation overrides them.
- Live ledgers control current principal, amount paid, balance due, existing monthly amount, and existing first/next due date.
- Fee schedules and payment policies control which fee codes and installment terms are allowed.
- Stale exports are low-precedence warnings. Do not use stale values over live/local records, and never merge similar names, nearby case numbers, or nearby citation numbers.
- If a required identity field is missing everywhere and the template gives an unknown placeholder, use that exact placeholder rather than inventing data.

## Output Conventions

- Sort rows exactly as the template says, usually by case number or citation number ascending. Sort charges by charge id. Sort excluded codes ascending. Sort fee codes alphabetically unless the template asks for application sequence.
- Use ISO `YYYY-MM-DD` dates, `HH:MM` times, numeric currency rounded to two decimals, and hour fields at the requested precision.
- Recompute all aggregate totals from the rows you output.
- Use the citation number as the account reference when no separate case/account number exists.
- A recalled warrant is usually a docket action or status discrepancy; if a plea/sentence creates probation, closure, or another final posture, keep the final status disposition-based.
- `representation_mismatch` is true when the resolved counsel or defense type differs from live or stale records. Local counsel confirmations can override live/stale counsel.

## Fee Rules

- Query fees with the matter type that matches the live matter, such as `traffic`, `dui`, `criminal`, or `compliance`; do not default DUI or traffic matters to generic criminal fees.
- Use the effective date required by the packet: order/disposition date for new dispositions, filing date for filing-only assessments, or review date when the prompt says current review schedule.
- Assess only codes that are both active in the schedule and supported by the order facts. Candidate import codes, quick-picks, and unsupported charge codes are excluded unless the order and schedule support them.
- Include restitution in principal when ordered. Add a restitution administration fee only when restitution was ordered and the active schedule supports it.
- Add conviction, filing, probation, or treatment/license fees only when the schedule condition is met. If the packet says no separate probation, restitution, or financial event was pronounced, do not add that optional fee.
- For review-only matters, keep the existing approved filing principal if no new disposition or financial event was ordered; use live ledger principal as the before-correction baseline and report deltas from it.

## Payment And Compliance Rules

- Use approved monthly amounts from live records or the packet. If the court approved the lowest allowed amount, use the county policy `min_monthly`.
- If no first due date was announced, add the policy `first_due_days_after_order` to the order/review date. If a live approved first/next due date exists for a kept plan, use it.
- Compute installment schedules from the template basis:
  - traffic assessments: assessed total;
  - initial installment orders with `plan_basis: original_principal`: original principal, while still reporting live paid and balance fields;
  - revised compliance plans: corrected current balance.
- Full or regular payment count is `floor(basis / monthly_amount)`. If a remainder exists and smaller final payments are allowed, final amount is the remainder and total installments include it. Final due date is first due date plus `total_installments - 1` months.
- When no payment plan applies, use `null` date/amount fields and `0` counts.
- Positive correction amounts reduce a live balance. A packet receipt not on the live ledger is a positive credit, making corrected balance `ledger_balance_before_adjustment - correction_amount`.
- Approved ability-to-pay petitions create revised plans. Withdrawn or denied petitions do not; keep the existing plan or send the matter back to court according to the packet action.
- Community service remaining hours are ordered hours minus verified completed hours. Mark restitution open until paid or disbursed is confirmed.

## Common Pitfalls

- Do not include `review_needed: false`, stale-only, or context-only matters.
- Do not treat stale extracts as authoritative records.
- Do not assess late, school, speed, public-defender, failure-to-appear, or other quick-pick codes unless the active schedule and order explicitly support them.
- Do not use current-year fee rows for an older citation or order unless the prompt specifically says to use the current schedule.
- Do not count payments as reducing principal. Principal is before payments; balance is after credits/payments.
- Do not leave invalid candidate codes in assessed components; put excluded candidates in the excluded-code field when the template asks for it.
