# Clerk Operations Reconciliation Skill

Use this skill for county clerk tasks that combine a local hearing/review packet with the shared clerk operations API. The goal is a clerk-ready JSON object matching the task's `answer_template.json`.

## Core Workflow

1. Read `prompt.txt`, every task-local payload named by the prompt, and `answer_template.json`.
2. Build the target list from the prompt/local packet, not from broad API searches. Exclude local rows marked informational, name-similarity only, or `review_needed: false` unless the prompt says otherwise.
3. Query the shared environment for each target's live case/citation, current ledger, county fee schedule, payment policy, attorney data, and stale exports if relevant.
4. Resolve facts by source precedence, compute fees/payment plans, then fill exactly the template keys and enum values.
5. Validate ordering, dates, nulls, currency, aggregate totals, and that the response is JSON only.

## API Habits

Base URL comes from `environment_access.md` (`GDPEVO_ENV_BASE_URL`). Use only that remote service.

Useful endpoints:

- `GET /api/cases`
- `GET /api/citations`
- `GET /api/financial-obligations`
- `GET /api/fees`
- `GET /api/payment-policies`
- `GET /api/stale-exports`
- `GET /api/attorneys`

`limit` and `offset` are supported. Some endpoints ignore field filters, especially `cases`, `citations`, and `attorneys`, so fetch the needed page/set and filter client-side. `financial-obligations?case_number=...`, `fees?county=...&matter_type=...`, and `payment-policies?county=...` are reliable habits.

Prefer structured filtering with `jq`, for example:

```bash
BASE=<TASK_ENV_BASE_URL>
curl -sS "$BASE/api/cases?limit=200" | jq '.results[] | select(.case_number=="...")'
curl -sS "$BASE/api/financial-obligations?case_number=25-ABC-00001"
curl -sS "$BASE/api/fees?county=Lane&matter_type=traffic"
curl -sS "$BASE/api/payment-policies?county=Lane"
```

## Source Precedence

- The prompt and `answer_template.json` control scope, required fields, enum spellings, ordering, and output format.
- Current local bench sheets, judge minutes, counsel confirmations, compliance packets, and review notes control the current clerk action even when the live case still shows an older status.
- Live API case/citation records control identity, court/county, baseline charges, live status, existing disposition dates, and current representation unless a task-local verification expressly supersedes them.
- Live financial obligations control current principal, paid credits, balance, missed payments, existing plans, and ledger status. Do not trust draft finance imports or stale ledger snapshots for final money.
- The fee schedule API controls fee amounts. Use the row active on the relevant filing, disposition, order, or review date.
- Stale exports and draft workpapers are conflict warnings and candidate-code sources. Use them to flag mismatches or excluded codes, not as final values when contradicted by live records or current local packets.

## Output Conventions

- Return one JSON object only. Do not include explanations.
- Preserve template keys exactly. Use only controlled enum values from the template.
- Sort rows exactly as requested, usually ascending by `case_number` or `citation_number`. Sort charges by `charge_id`. Sort fee codes or excluded codes alphabetically unless the template says to keep application order.
- Dates are `YYYY-MM-DD`; times are `HH:MM`. Use `null` only where the template permits it.
- Currency fields are JSON numbers rounded to two decimals. Counts, months, and installment counts are integers. Community-service remaining hours may require one decimal.
- For unknown identity fields, use the county payment policy's `unknown_field_placeholder` when the template asks for a placeholder.

## Disposition and Status Rules

- Bench/current packet outcomes override stale or live pending values for plea, disposition, sentence, warrant recall, and current review actions.
- A conviction with probation normally resolves to `probation_active`; a recalled warrant with no plea/disposition remains `open`; a true deferred judgment resolves to `deferred`; a completed non-probation matter may be `closed`.
- Dismissed charges usually get `plea: "not_entered"`, `disposition: "dismissed"`, and `verdict: "dismissed"` when no plea was taken.
- No-contest and guilty convictions produce `disposition: "convicted"` and `verdict: "guilty"` unless the template has a more specific DUI/deferred category.
- Counsel confirmations/verifications supersede stale exports and live captions for corrected attorney/type fields. Mark representation mismatch when the stale/live record differs from the corrected local confirmation.
- Docket action fields are action flags: enter only the actions needed by the current packet. Sentence-review or finance-review-only rows should not invent new plea/sentence actions.

## Fee Rules

- Pick fee rows where `effective_start <= relevant_date` and `effective_end` is null or after that date.
- Use the correct `matter_type`: `criminal`, `dui`, `traffic`, or `compliance`.
- Apply mandatory fee rows only when their `applies_when` condition is met. Apply optional rows only when the order/local packet supports them.
- Criminal principal normally includes filing plus conviction fees when there is a conviction. Add probation setup only when probation is ordered and not expressly waived or omitted. Add restitution admin only when restitution is ordered and supported.
- Restitution itself is part of principal when ordered, even though it is not a fee code.
- Do not assess unsupported or dismissed charge codes as fees merely because they appear in draft imports. Put such candidate codes in excluded-code fields when requested.
- Traffic: assess `TR-BASE` for convicted/deferred violations. Add `TR-SPEED`, `TR-SCHOOL`, or `TR-LATE` only when the active schedule and the order facts support them.
- For correction tasks, `corrected_assessment_total` or `principal_amount` is before payments. `financial_delta` is corrected principal minus current live ledger principal; use `0.00` as current principal if no live obligation exists.
- `corrected_balance_due` is corrected principal minus live `amount_paid`, further reduced by valid local receipt/credit corrections. Do not subtract stale hints.

## Payment Plan Rules

- Pull the county policy for `min_monthly`, `max_monthly`, `first_due_days_after_order`, and `allows_final_smaller_payment`.
- If the judge/live citation/ledger already approved a monthly amount or first due date, use it unless the current packet approves a revised plan.
- If a requested monthly amount is below the county minimum, use the minimum when the judge approved the lowest amount allowed by policy.
- If no first due date was announced or recorded, compute `order_date + first_due_days_after_order`.
- Compute installments from the plan basis required by the template: often original principal/assessed total for new orders, current balance for compliance replans.
- When smaller final payments are allowed: full payments are `floor(total / monthly_amount)`, final payment is the remainder if nonzero, and total installments add the final smaller payment. If the balance is less than one monthly payment, use one installment with final payment equal to the balance.
- Final due date is the first due date plus `total_installments - 1` calendar months on the same day of month.
- For no plan, use `null` for plan amounts/dates where allowed and `0` for installment counts.

## Compliance Review Rules

- Include only packet matters requiring review.
- Community-service remaining hours are ordered hours from the live case minus verified completed hours from the packet, floored at zero. Status is `not_ordered`, `complete`, `partial`, or `unknown` per template.
- Restitution is `none` when no restitution is ordered, `open` when live/local trust records show unpaid or undistributed restitution, and `paid_or_disbursed` when the packet confirms full disbursement/payment.
- Local cashier receipts not on the live ledger become positive correction amounts that reduce the live balance.
- Approved ability-to-pay petitions create revised plans; withdrawn petitions do not.
- Use source-conflict codes literally: receipt-vs-ledger credits, petition-driven plan changes, and service shortfalls map to their corresponding enum values.

## Final Checklist

- Target list matches the packet scope and excludes informational decoys.
- Local current action, live records, fee schedule, payment policy, and stale/draft conflicts have all been considered.
- Every enum value comes from the template.
- Aggregates equal the row values after rounding: case counts, review counts, balances, deltas, payment counts, lists, and booleans.
- No stale export, draft import, or candidate fee code was used as final truth without live/current support.
