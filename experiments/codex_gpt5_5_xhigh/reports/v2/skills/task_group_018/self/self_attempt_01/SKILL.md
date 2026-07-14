# Clerk Operations Packet Solver

Use this skill for court-clerk packet tasks that combine local packet files with the shared Clerk Operations API and require a JSON-only answer.

## First Pass

1. Read the prompt, `environment_access.md`, the packet payloads, and `answer_template.json`.
2. Use only the supplied remote base URL. Do not start a local service.
3. Treat the answer template as binding: required keys, enums, ordering, nullability, precision, and aggregate fields all come from it.
4. Identify target matters before calculating anything. Exclude local rows marked informational, `review_needed: false`, similar-name checks, stale-export carryovers, or contextual queues unless the prompt explicitly says to include them.

## API Habits

The API is plain GET. `GET /docs` lists endpoints. Useful calls:

- `/api/cases/<case_number>` for live case identity, charges, status, counsel, sentence baseline, matter type, and disposition date.
- `/api/citations/<citation_number>` for traffic identity, violation code, plea/disposition, plan request, and first due date.
- `/api/financial-obligations?case_number=<case_number>` for live principal, fee components, restitution, paid credits, balance, plan fields, delinquency, and ledger status.
- `/api/fees?county=<county>&matter_type=<type>&effective_on=<YYYY-MM-DD>` for active fee rows.
- `/api/payment-policies?county=<county>` for minimum/maximum monthly payment, first-due offset, final-payment rule, unknown placeholder, return-to-court timing, and unsupported charge codes.
- `/api/docket?case_number=<case_number>` when docket history affects status, notices, service, or review actions.
- `/api/stale-exports?county=<county>&name=<export_name>` only to identify conflicts or stale rows.
- `/api/search?q=<text>` to locate uncertain case/citation identifiers, then fetch the exact record.

Query the exact case or citation from the packet. Do not merge nearby case numbers, typo-like citation numbers, or same-name records.

## Source Precedence

Use this order when sources conflict:

1. Prompt and answer template for task scope, output shape, enum values, sorting, precision, and aggregate requirements.
2. Current local bench packet, review note, receipt, provider notice, ability-to-pay petition, or counsel confirmation for the current order or requested correction.
3. Live API case/citation/docket records for identity, existing status, charges, live counsel baseline, matter type, and docket history.
4. Live financial obligations for current principal, paid credits, live balance, existing plan data, and delinquency.
5. Live fee schedule and payment policy for allowed fees, amounts, unsupported codes, and plan rules.
6. Stale exports, draft imports, old worksheets, and candidate fee lists only as warnings or exclusion sources.

Stale exports never override a current packet note, live ledger, live docket, or active fee schedule. Candidate import/workpaper fee codes are not assessed unless the current order supports them and the active schedule contains them.

## Charges, Status, And Counsel

- Map bench phrases to template enums, not to free text. For example, a conviction uses the entered plea and a convicted/guilty posture; dismissed plea-agreement counts usually remain `not_entered` with dismissed disposition/verdict when the template separates plea and outcome.
- Use current hearing/review notes to resolve case status when live status has not yet been updated. Warrant-recall notes require the template's recall/status fields to be set even if the live case still says `warrant`.
- Counsel confirmations and attorney verification memos control final representation when they are current. Compare them with live/stale records to set mismatch, discrepancy, supervisor-review, or attorney-update fields.
- If an identity field is unknown and the template permits a placeholder, use the policy/template placeholder exactly, commonly `TBD from case file`; count placeholders when requested.

## Fee And Balance Rules

- Pick fee rows by county, live `matter_type`, and the operative order/disposition date. Do not use today's date, packet creation date, stale export date, or old ledger order date unless that is the order being corrected.
- Assess only fee codes that are both active in the schedule and supported by the order. Mandatory fees still require their `applies_when` condition to be true.
- Optional fees require specific support: probation ordered, restitution ordered, traffic school elected, late fee ordered/triggered, reinstatement requested, return-to-court notice issued, etc.
- Exclude policy `unsupported_charge_codes` and any candidate/import codes that lack schedule/order support. Put them in excluded-code fields when the template asks.
- Principal is the approved fee components plus restitution when the template defines principal that way. Keep restitution separate only when the template does.
- Paid credits and current balance usually come from the live ledger. Packet receipts not on the ledger are corrections: positive `correction_amount` values reduce the live balance when the template uses that convention.
- For delta fields, compute `corrected_assessment_total - current_live_principal` before payments. If the task says no live obligation means zero, use `0.00`; otherwise treat a missing ledger as a review issue.
- Round currency to two decimals at output. Avoid string amounts unless the template says string.

## Payment Plans

- Use explicit judge-approved or live approved monthly amount and first due date when present. If the order says the lowest local amount was approved, use the policy `min_monthly`.
- If no first due date is supplied, set it to `order_date + first_due_days_after_order` from the county policy.
- Choose the plan basis from the task context:
  - `original_principal` for an original sentencing/disposition installment order.
  - `current_balance` or corrected balance for compliance reviews, ability-to-pay revisions, and post-credit plans.
  - `no_plan` or null/zero plan fields when no balance or no plan applies.
- Installment math: divide the plan basis amount by monthly amount. With `allows_final_smaller_payment: true`, use full monthly payments plus one smaller final payment if there is a remainder; if there is no remainder, do not add an extra final payment. With no smaller final allowed, use the template's review/plan status if an exact schedule is impossible.
- Final due date advances monthly from the first due date by the number of installments minus one. Preserve the day when possible.
- For revised plans, use the petition-approved monthly amount only if it is approved and within policy; withdrawn or unsigned petitions do not change the existing plan.

## Output Conventions

- Return only one JSON object. No prose, comments, Markdown, or trailing explanation.
- Preserve required top-level keys and all required item keys, even when values are `null`, `0`, `false`, empty arrays, or placeholders.
- Use exact enum strings from the template. Do not invent statuses.
- Dates are ISO `YYYY-MM-DD`; times are `HH:MM`; booleans are JSON booleans.
- Sort exactly as instructed: commonly case/citation numbers ascending, charges by `charge_id`, fee codes alphabetically or in application order, and aggregate case lists ascending.
- Recompute all aggregate totals and counts from the final rows: included-case count, financial-adjustment count, paid/post-credit cases, revised-plan cases, return-to-court count, principal/balance totals, mismatch lists, and placeholder counts.
- Use the citation number as `account_reference` when the live citation record has no separate case/account number.

## Common Pitfalls

- Do not include non-target packet matters just because they appear in stale exports.
- Do not use draft finance imports, handwritten worksheets, stale principal hints, or candidate fee lists as final amounts.
- Do not assess unsupported or unproved fees such as traffic school when not elected, late fees when not ordered/triggered, failure-to-appear/public-defender codes that are not active schedule rows, or restitution admin fees when no restitution was ordered.
- Do not use obsolete fee amounts for a new current order, and do not use current fee amounts for an old order unless the current task is replacing the old assessment under the current order date.
- Do not let live pre-hearing charge values override the current bench result.
- Do not let a packet receipt reduce balance twice if it is already reflected in the live ledger.
- Do not use stale license/probation dates when the packet says they were copied from another field or pre-disposition snapshot.
