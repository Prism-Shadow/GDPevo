# Clerk Operations JSON Tasks

Use this skill for Clerk Operations tasks that combine task-local clerk packets with the shared Clerk Operations API to produce a template-conforming JSON answer.

## Standard Workflow

1. Read the prompt, `input/payloads/answer_template.json`, and every task-local payload named by the prompt.
2. Extract the target county, court, dates, case numbers, citation numbers, packet IDs, and required ordering rules from the local materials.
3. Query the live API only for the target records and their directly relevant county records.
4. Resolve the answer from both source sets, then validate every key, enum, sort order, date, null, boolean, and currency field against the template.
5. Return only the completed JSON object when the task asks for JSON only.

## API Habits

Base URL comes from `environment_access.md` or the prompt. Common endpoints:

- `GET /api/cases/<case_number>` or `/api/cases?county=<county>&matter_type=<type>&status=<status>`
- `GET /api/citations/<citation_number>`
- `GET /api/docket?case_number=<case_number>`
- `GET /api/financial-obligations?case_number=<case_number>`
- `GET /api/fees?county=<county>&matter_type=<type>&effective_on=<YYYY-MM-DD>`
- `GET /api/payment-policies?county=<county>`
- `GET /api/stale-exports?county=<county>&name=<export_name>`
- `GET /api/search?q=<text>` only when a packet gives an ambiguous name or identifier.

Prefer exact case or citation endpoints over broad searches. Use `matter_type` from the live case or prompt (`criminal`, `traffic`, `dui`, `compliance`) when pulling fee schedules. For fees, always pass the operative order, disposition, filing, or review date required by the packet, not today's date.

## Source Precedence

- Current local bench/hearing/order packets control newly announced pleas, dispositions, sentence terms, warrant recalls, restitution orders, community service completion, receipt corrections, and approved ability-to-pay changes.
- Live case records control identity, caption, existing status, filed charges, court, historical disposition dates, and whether a case/citation exists.
- Live financial obligations control current principal, amount paid, balance due, existing plan amount/due date, and ledger credits.
- Live fee schedules and payment policies control fee amounts, unsupported codes, minimum monthly amounts, first-due offsets, and placeholder text.
- Attorney/counsel confirmation memos in the local packet control representation corrections when they conflict with stale exports or older live captions.
- Stale exports, draft imports, old worksheets, queue hints, and nearby similar names are warning/context sources only. Do not use them over live records or current packet orders.

## Fee Rules

- Build assessed fees from active schedule rows whose `applies_when` is satisfied by the current order. Mandatory schedule rows still need the triggering event.
- Include filing fees when the case/account has a filing assessment basis, even if no new conviction occurred.
- Include conviction fees only for convicted/amended-convicted outcomes, not dismissed, deferred, pending, or no-disposition rows unless the template/source explicitly says otherwise.
- Include probation setup/monitoring fees only when probation was ordered and the packet does not say no separate probation fee was pronounced.
- Include restitution administration fees only when restitution is ordered; add the restitution amount itself to principal totals/balances when the template asks for financial totals.
- Exclude unsupported policy codes and candidate workpaper/import codes not supported by both the order and fee schedule. Put excluded codes in the template's excluded-code field, sorted as instructed.
- If no live financial obligation exists and the template asks for current ledger principal, use `0.00`.
- `corrected_balance_due = corrected principal or corrected total - live amount_paid`, unless the template defines a different adjustment formula.
- For adjustment/review tasks, `financial_delta = corrected_assessment_total - current_ledger_principal`.

## Payment Plan Rules

- Pull the county payment policy for `min_monthly`, `max_monthly`, `allows_final_smaller_payment`, and `first_due_days_after_order`.
- Use a judge-approved or live approved monthly amount when present; otherwise use the approved requested amount clamped to policy limits, or the county minimum when the packet says the lowest allowed amount was approved.
- Use an existing live first due date when the packet says the existing plan was approved. Otherwise compute `order_date + first_due_days_after_order`.
- Compute installment schedules from the stated basis: original principal, current/corrected balance, or no plan. Do not assume current balance when the output has a `plan_basis`.
- When smaller final payments are allowed, full payment count is floor(`basis / monthly_amount`), final payment is the remainder, and total installments adds one only if the remainder is greater than zero.
- If no plan applies, use `null` for payment amount/date fields and `0` for counts where the template says so.
- For compliance replans, schedule from corrected balance after packet credits; for keep-existing plans, preserve live plan amount and due date.

## Output Conventions

- Follow the answer template exactly; do not add explanatory fields.
- Sort rows by `case_number` or `citation_number` ascending unless the template says otherwise. Sort charges by `charge_id`; sort fee-code lists as specified.
- Use ISO dates (`YYYY-MM-DD`) and times (`HH:MM`). Use JSON `null` where the schema allows nulls; do not write `"null"`.
- Currency values are numbers rounded to two decimals. Community service remaining hours may require one decimal. Counts and months are integers.
- Use only template enum values. Map plain-language bench notes to the closest allowed enum after resolving the source conflict.
- Use the county policy `unknown_field_placeholder` for missing identity/contact/probation officer fields when the template calls for a placeholder.
- Aggregate totals must be recalculated from the emitted rows, not copied from source summaries.

## Common Pitfalls

- Do not include context-only, name-similarity, or `review_needed: false` packet rows.
- Do not merge nearby stale citation/case numbers with the target record.
- Do not let live pending/warrant status override a current hearing packet that entered a plea, recall, or sentence.
- Do not let a stale export override a live ledger balance or a current counsel confirmation.
- Do not include optional late, school, public defender, return-to-court, or unsupported charges merely because a draft import listed them.
- Do not forget restitution in principal/balance totals when ordered.
- Do not use stale principal hints or obsolete fee rows unless the effective date actually falls in that schedule period.
- Do not count a case as needing financial replacement/adjustment when the corrected total equals the live ledger principal.
