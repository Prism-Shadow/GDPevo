---
name: clerk-ops-json-solver
description: Solve Clerk Operations court-record tasks that require combining local hearing packets with the shared clerk API to produce strict JSON answers. Use for criminal, traffic, DUI/probation, misdemeanor, compliance, fee-schedule, ledger-credit, payment-plan, stale-export, and docket-entry reconciliation tasks.
---

# Clerk Operations JSON Solver

## Start Every Task

1. Read the prompt, `answer_template.json`, and task-local packet files first. The template controls required keys, enum values, nullability, precision, and ordering.
2. Read `environment_access.md` for the remote base URL. Use only that service; do not start or inspect a local environment. There is no judge endpoint.
3. Identify the target matters from the prompt/packet, not by broad API search. Exclude informational, similar-name, `review_needed: false`, stale-only, or nearby-number records unless the prompt explicitly includes them.
4. For each target, pull live records from the API and reconcile them with the local packet before writing output.

Useful API pattern:

```bash
BASE=<TASK_ENV_BASE_URL>
curl -s "$BASE/docs"
curl -s "$BASE/api/cases/<case_number>"
curl -s "$BASE/api/citations/<citation_number>"
curl -s "$BASE/api/financial-obligations?case_number=<case_number>"
curl -s "$BASE/api/docket?case_number=<case_number>"
curl -s "$BASE/api/fees?county=<county>&matter_type=<type>&effective_on=<YYYY-MM-DD>"
curl -s "$BASE/api/payment-policies?county=<county>"
curl -s "$BASE/api/stale-exports?county=<county>&name=<export_name>"
curl -s "$BASE/api/search?q=<text>"
```

API list endpoints usually return `{count, offset, returned, results}`. Cases/citations return direct objects. URL-encode query values when needed.

## Source Precedence

- Template and prompt: output shape, target scope, sorting, allowed values, and date/currency formats.
- Current judge minutes, bench sheets, compliance packets, counsel confirmations, receipts, provider notices, and ability-to-pay orders: new outcomes, sentences, recalls, service completions, approved petitions, and attorney corrections.
- Live API: current case/citation identity, matter type, court, docket history, ledger principal, payments/credits, balances, existing payment plans, active fee schedules, and county payment policies.
- Counsel/status verification memos or packet confirmations can override stale/live captions when they are clearly later or specifically filed for the hearing; mark the relevant mismatch/review fields.
- Stale exports, draft finance imports, candidate fee workpapers, and old worksheets are warning/conflict sources. Do not use their status, counsel, principal, or fee codes when they conflict with current packet notes, live ledgers, or active schedules.
- If required identity fields are unknown, use the county policy placeholder such as `TBD from case file` when the template calls for a placeholder; use `null` only where the template permits it.

## Outcomes And Status

- Bench/current packet outcomes override live pending values. "Conviction entered" with a guilty or no-contest plea becomes disposition `convicted` and verdict `guilty` when a verdict field is required.
- Dismissed plea-agreement charges usually keep plea `not_entered`, disposition `dismissed`, and verdict `dismissed`.
- Amended charges use `amended`; charges with "no separate fee/sentence" should be excluded from financial assessments when the template has an excluded-code field.
- Set case status from the resolved posture: probation ordered means `probation_active`; no plea/disposition after a recall remains `open` or `pending_no_disposition`; deferred matters remain `deferred`; closed matters remain `closed` when no new action changes them.
- Warrant recalls affect docket action fields and status conflicts, but do not create convictions or fees by themselves.

## Fees And Balances

1. Query `/api/fees` using the county, matter type, and the order/disposition date that created the assessment. Do not use today's date unless the task asks for a current review date assessment.
2. Include mandatory schedule rows when their `applies_when` condition is triggered. Include optional rows only when the hearing/order/packet supports them; if the packet says a separate probation/restitution/late fee was not pronounced, exclude it.
3. Use only codes supported by the active schedule and current order. Put unsupported or unentered candidate codes in the template's excluded list, sorted as required.
4. Filing assessments can apply to filed criminal matters even without a new conviction when the template asks for approved principal cleanup. Conviction assessments require a resolved conviction. Probation, treatment, license, late, school, and restitution-admin fees require the matching order or condition.
5. Restitution is part of principal/balance when ordered, but it is not a fee schedule component unless the template explicitly asks for restitution as a component. Add any separate restitution administration fee only when the schedule and order support it.
6. Compute principal as approved fees plus restitution when applicable. Compute corrected balance from the corrected principal minus live `amount_paid`/credits, then apply packet receipts or adjustments as directed. Round currency numbers to two decimals.
7. Compare corrected principal to live ledger principal for delta fields; if no live obligation exists, use `0.00` when the template says so.

## Payment Plans

- Always query `/api/payment-policies?county=<county>`. Use `min_monthly`, `max_monthly`, `first_due_days_after_order`, `allows_final_smaller_payment`, and `unknown_field_placeholder`.
- Use an existing live/approved monthly amount and first due date when the packet says the plan was already recorded. If the judge approved the lowest local amount or no amount was announced, use the policy minimum unless the task gives another approved amount.
- Choose the plan basis from the template/task: traffic plans usually use the assessed total; DUI probation examples can use original principal; compliance revised plans usually use corrected current balance.
- Installment math:
  - `full_payment_count` or `regular_payment_count` is `floor(plan_basis / monthly_amount)`.
  - `final_payment_amount` is the remaining cents after full payments.
  - `total_payment_count` or `total_installments` is full payments plus one when the remainder is positive, otherwise the full-payment count.
  - `final_due_date` is the first due date advanced by `total_count - 1` monthly due dates.
- If no payment plan applies, use the template's null/zero convention: commonly `monthly_payment_amount: null`, counts `0`, and due dates `null`.

## Compliance Reviews

- Include only packet matters that require review. Exclude name-similarity checks and informational stale-export carryovers.
- A receipt not posted to the live ledger is a positive `correction_amount` that reduces the live balance; if it pays the balance, use the paid-after-credit/post-credit-close style values allowed by the template.
- Approved ability-to-pay petitions revise the plan. Withdrawn or unsigned petitions do not change the plan.
- For service notices, subtract verified completed hours from ordered hours in the live case/sentence; never let remaining hours go below `0.0`.
- Restitution is `paid_or_disbursed` only when live/packet trust records confirm it; use `open` when restitution remains unresolved and `none` when not ordered.
- Return-to-court actions usually require delinquency, service shortfall, or an unresolved restitution/compliance issue without an approved revised plan.

## Output Conventions

- Return only the completed JSON object. Do not include markdown, comments, explanations, or trailing text.
- Preserve exactly the template's top-level keys and field names. Use only enum values from the template.
- Sort rows by case/citation number unless the template says otherwise. Sort charges by `charge_id`; fee codes alphabetically when requested; excluded candidate codes ascending.
- Use ISO dates `YYYY-MM-DD`, times `HH:MM`, currency as JSON numbers rounded to two decimals, and service hours to one decimal where requested.
- Aggregate fields must be recomputed from the emitted rows: counts, sums, mismatch lists, all-plans booleans, post-credit lists, revised-plan lists, and nonzero financial-delta counts.

## Common Pitfalls

- Do not copy stale export statuses, old principal hints, or draft-import fee amounts into final fields.
- Do not merge nearby citation/case numbers or similar defendant names.
- Do not include candidate fees just because they appear in a workpaper; verify `applies_when`, order support, and unsupported-code policy.
- Do not omit live ledger credits when calculating corrected balance.
- Do not list restitution as a fee component unless the template explicitly requires that representation.
- Do not use packet date instead of disposition/order date for fee-schedule effectiveness unless the task is explicitly a review-date compliance task.
- Use the citation number as `account_reference` when no separate live case/account number exists.
