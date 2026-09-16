# Northstar Environment Reference

## Access

The task prompt and `task_context.json` provide the environment base URL and SQL token. If the base URL is shown as a placeholder, use the staged environment access file for the actual URL. The SQL endpoint accepts JSON with an `sql` field and a bearer token:

```bash
curl -sS -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  --data-binary '{"sql":"select * from cases where case_id = '\''CASE-ID'\''"}' \
  "${BASE_URL%/}/sql/query"
```

Use `GET /api/tables` to inspect columns. Use business endpoints for direct records:

- `GET /api/cases/{case_id}`
- `GET /api/policies/{policy_id}`
- `GET /api/documents/{document_id}`
- `GET /api/rate-schedules`
- `GET /api/appeals`
- `POST /sql/query`

## Table Map

- `cases`: case metadata, member/provider/plan IDs, service domain, request type, stage, status, urgency, dates.
- `members`, `plans`, `providers`: member eligibility, plan type, payer/network, provider attributes.
- `request_lines`: authorization/service request lines with CPT, modifier, units, dates, diagnosis codes, charges.
- `documents`: clinical or operational documents with current/stale flag, type, dates, source, summary.
- `document_facts`: extracted facts tied to documents and criteria.
- `policies`, `policy_criteria`: policy version, effective dates, criterion text, missing-result behavior.
- `case_criteria`: per-case criterion result, facts, gaps, reviewer scope.
- `authorizations`: authorization numbers, status, approved units/dates/CPTs/modifier, denial reason.
- `appeals`: appeal path, type, denial date, received date, deadline, expedited attestation, owner, notes.
- `drug_trials`: medication trial evidence and whether each trial is documented.
- `assistance_screen`: manufacturer assistance program status, denial requirement, missing fields.
- `claims`, `claim_lines`: claim header, totals, line order, CPT/modifier/units/service date/paid amount.
- `payment_benchmarks`: rate schedules by payer, plan type, service domain, CPT, modifier, effective dates, source/version.
- `p2p_events`: P2P discussion record, new information, outcome, final status, reviewer, notes.
- `service_margin`: monthly payer-service finance rows with revenue, variable cost, fixed allocation, charge sensitivity.

## Common SQL Patterns

Fetch target service margin rows while preserving task order in your final JSON:

```sql
select *
from service_margin
where month_id in (...)
```

Fetch claim lines in source order:

```sql
select *
from claim_lines
where claim_id = :claim_id
order by line_number
```

Fetch candidate benchmarks:

```sql
select *
from payment_benchmarks
where payer = :payer
  and plan_type = :plan_type
  and service_domain = :service_domain
  and cpt_code = :cpt_code
  and ((modifier is null and :modifier is null) or modifier = :modifier)
  and effective_start <= :service_date
  and effective_end >= :service_date
order by effective_start desc
```

SQLite does not support bound parameters through the HTTP endpoint; substitute escaped literal values yourself and keep filters narrow.

## Prior Authorization Summary

Use the case record, request lines, policy, criteria, documents, facts, and authorization record.

- Evidence documents: current documents whose facts support required criteria.
- Excluded documents: stale or irrelevant case documents, usually `is_current = 0`.
- Criteria: use all required template criterion IDs; gaps determine pend, MD review, partial approval, or denial.
- Approval path: when all nurse-scope criteria are met and an authorization recommends approval, use nurse approval route, approval letter, and issue-approval action.
- Approved CPTs: split comma-separated authorization CPTs, sort when the template requires ascending code order.

## Pharmacy Appeal and Assistance

Use appeal, criteria, current packet documents, drug trials, and assistance screen together.

- Appeal path, expedited flag, deadline, and owner come from the appeal record.
- Required packet items can appear in appeal notes, policy summary, document types, or the template choices.
- Missing packet items come from criterion gaps, undocumented trials, absent required documents, and assistance missing fields.
- Documented failures are lowercased medication names where `drug_trials.documented = 1`; undocumented or insufficient failures have documented false or missing fill evidence.
- Assistance status comes from `assistance_screen.assistance_status`, normalized to the template enum. Include assistance missing fields sorted as required.
- Choose the next action for the highest-priority gap: payer appeal evidence gaps before assistance-only gaps.

## Claim Repricing

Use claim header, claim lines, member or case plan type, service domain, and effective payment benchmarks.

1. Match each claim line to a benchmark by payer, plan type, service domain, CPT, modifier/null, and service date within effective dates.
2. Reject expired or stale sources even if their amount equals the paid amount.
3. Calculate `correct_allowed_amount = allowed_amount * units`.
4. Calculate `recovery_amount = correct_allowed_amount - paid_amount`; positive means upward correction, negative means downward correction, zero means no change.
5. Sum paid amounts and corrected allowed amounts across lines for top-level totals.
6. Use the selected benchmark source/version when all selected lines share one source; otherwise follow the template's route for mixed sources.

## P2P Authorization Closure

Use current criteria, current clinical evidence, request line, authorization status, and the completed P2P event.

- Requested CPT comes from the request line.
- P2P outcome and final status come from the P2P event or final authorization when consistent.
- New information changes review only when it supplies patient-specific facts that change a required criterion result.
- Unresolved criteria are required criteria with `not_met` or `unclear` final results, ordered as the template specifies.
- Missing PET-over-SPECT factors are the listed PET factors still unsupported by documents or P2P new information.
- For adverse final results, calculate the internal appeal deadline from the adverse determination date and the plan/prompt appeal window. Use calendar-day addition.
- Recommend the lower-intensity or policy-supported alternative when the requested service is denied and the evidence supports an alternative.

## Therapy Margin Queue

Use only the queue row IDs in `task_context`. Keep final rows in that same order.

For each row:

- `total_cost = variable_cost + fixed_cost_allocated`, unless context provides another definition.
- `margin = net_revenue - total_cost`.
- `revenue_to_cost_ratio = net_revenue / total_cost`.
- `below_threshold = ratio < threshold`.
- `charge_sensitive = charge_sensitive` converted to a boolean.
- `recommended_action = payer_contract_review` for below-threshold rows; otherwise `monitor_charge_sensitive` for charge-sensitive rows; otherwise `monitor_no_action`.

For summary fields:

- `below_threshold_segments`: payer segments below threshold, alphabetical by enum value.
- `charge_sensitive_segments`: charge-sensitive segments, alphabetical by enum value.
- `top_issue`: the below-threshold row with the largest positive dollar gap to the threshold, formatted according to the template choices; use `none` when no row is below threshold.
- `gap_to_120pct` or equivalent threshold gap: `max(0, threshold * total_cost - net_revenue)` for the top issue, rounded to cents.

## Normalization

- Use JSON numbers for money and ratios, not strings.
- Use `null` for absent modifier fields or absent dates only when the template allows null.
- Convert comma-separated fields into arrays where the template requires lists.
- Sort only when the template says to sort; otherwise preserve source order or task-context order.
- Do not include patient names, DOBs, provider phone/fax, or narrative summaries unless the template asks for them.
