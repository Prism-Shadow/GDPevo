---
name: task-group-014-sql-payer-ops
description: Operating procedure for task_group_014_sql_payer_ops SQL tasks involving payer operations, utilization management intake and clinical review, pharmacy appeals and manufacturer assistance, reimbursement compliance, and rehab profitability. Use when Codex must solve these tasks through the provided read-only SQLite query service and return strict JSON matching task payload templates.
---

# SQL Payer Ops Procedure

## Ground Rules

Read `environment_access.md` first. Use the SQL endpoint, Basic Auth, and read-only SQLite statements exactly as described there. Do not hard-code the concrete host or port and do not assume a local database file.

Use only the task's staged input payloads for target IDs, buckets, dates, clinics, plan types, service categories, thresholds, and output schema. If the database contains rows labeled for other batches, ignore them unless the current payload names them.

Always inspect `input/payloads/answer_template.json` before querying deeply. Return one JSON object with exactly the requested keys and value conventions. Sort case-level arrays by ascending `case_id` or `med_case_id`; sort financial cells deterministically by the fields implied by the template or ranking rule. Reconcile all summary counts and totals back to detail rows.

## SQL Workflow

Use small discovery queries before writing final SQL:

```sql
SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name;

SELECT m.name AS table_name, p.cid, p.name AS column_name, p.type, p.pk
FROM sqlite_master AS m
JOIN pragma_table_info(m.name) AS p
WHERE m.type = 'table'
ORDER BY m.name, p.cid;
```

Profile scoped vocabularies with `SELECT DISTINCT` for statuses, buckets, service categories, plan types, correction statuses, criteria keys, and template enum candidates. Prefer CTEs that mirror the payload scope over broad database scans.

Common table groups:

- Authorization intake and clinical review: `authorization_requests`, `auth_lines`, `service_codes`, `members`, `plans`, `providers`, `facilities`, `existing_authorizations`, `state_sla_rules`, `coverage_criteria`, `criteria_sources`, `clinical_facts`, `evidence_documents`, `case_review_events`, `p2p_sessions`.
- Medication appeals and assistance: `medication_cases`, `appeals`, `drug_policy_requirements`, `medication_trials`, `assistance_programs`, `household_financials`.
- Finance and profitability: `encounters`, `rate_schedules`, `claim_corrections`, `clinic_costs`, `clinic_budgets`.

SQLite tips:

- Use `date(...)`, `datetime(...)`, `julianday(...)`, and `strftime(...)` for dates.
- Use `COALESCE(rate.effective_end, '9999-12-31')` for open-ended rate schedules.
- Build payload-only scope CTEs with `VALUES` when scope data, such as clinic state, exists in JSON but not in a SQL table.
- Use `ROUND(x, 2)` for money and per-unit rates; use `ROUND(x, 4)` for decimal percentages. Emit percentages as decimals, not strings or whole percents.

## Authorization Intake

Scope cases from the worklist payload, usually by explicit IDs or `authorization_requests.target_bucket`.

Build one base row per case from:

- `authorization_requests` to `members` to `plans`
- requesting and servicing `providers`
- `facilities`
- rolled-up `auth_lines` joined to `service_codes`
- overlapping `existing_authorizations`
- applicable `state_sla_rules`

Apply intake checks in the template's order, stopping at the first failure:

1. `active_coverage`: service/request dates must fall within coverage; handle null coverage ends and retro reinstatement dates carefully.
2. `cob_completion`: fail if member COB status is not processed or the request indicates primary processing is incomplete.
3. `covered_service`: fail if any requested service code is not covered.
4. `network`: fail for out-of-network requesting or servicing providers unless an OON exception applies.
5. `service_area`: fail when facility/service area is outside scope.
6. `pa_required`: notification-only or non-PA services close without clinical review.
7. `retrospective_submission`: fail when rendered before submission.
8. `duplicate_authorization`: match same member, same CPT, active/approved existing authorization, and overlapping service dates.
9. `none`: proceed to gold-card or review routing.

For duplicate IDs, return an empty array when none and sorted existing auth IDs when present.

Gold-card auto approval requires all applicable conditions, not just provider status: plan allows gold card, requesting provider has active gold-card status, service is not gold-card-excluded, and no requested line mandates MD review. If the case is halted earlier, use a `not_reached_intake_halt` style decision when the template expects it.

Review queue routing generally follows delegated/vendor and clinical flags: external vendors such as imaging vendors get their vendor queue, specialty programs get the matching specialty queue, mandatory MD review goes to Medical Director Review, otherwise nurse review. Provider follow-up item comes from requesting provider sanctions or inactive credentials.

SLA due time starts from `receipt_timestamp`. Prefer `state_sla_rules` matching facility state and plan type, falling back to plan defaults. Add urgent/stat in hours. Add routine in calendar days unless `day_type = 'business'`, in which case count weekdays. Format as `YYYY-MM-DDTHH:MM`.

## Clinical Review

Scope from the worklist bucket/date. Determine service category and requested units from `auth_lines`; do not rely blindly on `authorization_requests.requested_total_units` if it conflicts with line detail.

Select criteria by joining `coverage_criteria` to the case service category and `plan_type_filter IN (case_plan_type, 'ALL')`, then tie to `criteria_sources`. Use the lowest `precedence_rank` source that has applicable required criteria for the service; do not choose a plan-specific source merely because it exists if it has no matching criterion rows.

Compare required criteria to `clinical_facts`:

- A required key is missing if no fact exists.
- It is incomplete if `fact_value` does not equal `required_value`.
- Treat `stale`, `conflicting`, and usually `partial` confidence flags as not clean nurse-approval evidence unless the prompt gives a contrary rule.
- Use current evidence documents (`is_current = 1`) to support whether facts are usable.

Recommend nurse approval only when all required criteria are met with usable current evidence and no mandatory MD/vendor issue exists. Otherwise require MD escalation and put the unresolved criterion keys in `missing_evidence_keys`. Use existing `case_review_events` and `p2p_sessions` as supporting context, not as a substitute for criteria comparison. Count MD escalations by service category exactly from the produced case rows.

## Medication Appeals And Assistance

Keep payer appeal routing and manufacturer assistance routing independent.

For appeal routing, join target `medication_cases` to `appeals` by `case_or_med_case_id`. Use `drug_policy_requirements` only as the list of requirements; it does not prove the requirement was satisfied. Determine missing policy requirements from case facts and documented `medication_trials`:

- `diagnosis`: compare diagnosis/formulary context to the drug requirement.
- `step_therapy`: look for documented failed/partial-response preferred, biosimilar, conventional, or required-step trials as appropriate for the drug.
- `topical_failure`: look for documented topical/conventional therapy failure.
- `tb_screen`: require explicit support if the drug policy requires it; do not infer it from unrelated trials.

Use appeal dates to determine timeliness. When no task-specific appeal rule table exists, medication appeals commonly use a 60-day filing deadline from `adverse_notice_date`; still verify the active prompt and data before applying it. `appeal_not_timely` overrides readiness. For timely appeals, missing policy evidence or administrative prerequisites make the appeal incomplete; otherwise it is appeal-ready.

For expedited classification, separate an attestation from support. `expedited_attestation = 1` with adequate urgency evidence supports a 72-hour expedited route; attestation without support is an expedited request needing evidence; no attestation is standard.

For assistance routing, join `assistance_programs` by drug and `household_financials` by member. Evaluate all blocking reasons independently:

- income exceeds `max_income_fpl`
- commercial insurance required but absent
- government plan excluded
- denial letter missing
- assistance consent missing

If no FPL table is supplied, use the task year and standard 48-state FPL formula after checking task context; for 2025, base household size 1 is 15650 and each additional person adds 5500. `program_owner` is the manufacturer team only when the assistance route is active/eligible; otherwise use not-routed values from the template. Set `path_separation` from the active appeal route and active assistance route, not from appeal readiness alone.

## Reimbursement Compliance

Build the audit scope from `audit_scope.json`: clinics, states, quarters, materiality thresholds, and active recovery statuses. If clinic state is only in the payload, make a scoped `clinics(clinic_id, clinic_name, state)` CTE.

For paid-rate compliance, join clean paid encounters to rates on payer, plan type, service category, CPT, state, and service date between effective dates. Define the paid cohort explicitly; when the template asks for excluded denied or unpaid encounters, use `paid_amount > 0 AND denial_code IS NULL` for paid-rate cells and count `paid_amount <= 0 OR denial_code IS NOT NULL` separately.

Cell formulas:

- `benchmark_amount = SUM(units * benchmark_rate)`
- `paid_per_unit = paid_amount / paid_units`
- `benchmark_per_unit = benchmark_amount / paid_units`
- `variance_amount = paid_amount - benchmark_amount`
- `variance_pct = variance_amount / benchmark_amount`
- Material underpayment when paid units, underpayment amount, and underpayment percent all meet payload thresholds.

Underpayments have negative `variance_amount` and `variance_pct` under this convention. Label material underpayment cells separately from compliant/non-material cells according to template enums.

Recovery opportunities are separate from paid-rate variance. Join `claim_corrections` to scoped encounters and include only payload active statuses such as `open`, `pending documents`, and `submitted`. The top opportunity is the active correction with the largest expected recovery, with deterministic tie-breaks by deadline and correction ID.

## Rehab Profitability

Build the scope from `worklist_scope.json`: analysis period, clinics, plan types, and service categories. Use all scoped encounters in the period, not only clean paid encounters, because profitability uses paid revenue plus open recovery opportunities.

Aggregate one payer-service result per `clinic_id`, `plan_type`, and `service_category`:

- `paid_amount = SUM(encounters.paid_amount)`
- `open_recovery = SUM(expected_recovery_amount)` for `claim_corrections.status = 'open'`
- `cost_per_unit = direct_cost_per_unit + allocated_overhead_per_unit`
- `total_cost = units * cost_per_unit`
- `net_revenue = paid_amount + open_recovery`
- `net_margin = net_revenue - total_cost`
- `margin_pct = net_margin / net_revenue`

Join `clinic_costs` by clinic, fiscal year, and service category. Inspect `clinic_budgets` before joining: in this dataset it may provide repeated clinic-service budget rows without a plan-type column. In that case, derive a clinic-service budget margin target once, such as a weighted or average expected margin, and avoid duplicating encounter rows by joining directly to repeated budget rows.

Rank the top three loss drivers by most negative `net_margin`, with stable tie-breaks. Flag payer-service cells below budget margin. A projected improvement amount should represent the dollars needed to bring the cell back to budget; for a margin target, use a consistent formula such as `max(0, total_cost / (1 - budget_margin_pct) - net_revenue)` and validate totals against the portfolio summary.

For persistence, compare quarterly margins for the same clinic-plan-service cell against the budget target. Mark persistent when the shortfall recurs across multiple active quarters; otherwise use the template's intermittent/transient/non-shortfall vocabulary if present.

## Final Validation Checklist

Before returning JSON:

- Validate with `jq` or equivalent JSON parsing.
- Confirm every key from `answer_template.json` is present and no explanatory text is included.
- Recompute summary counts from detail rows.
- Check case ordering and ranking order.
- Check null versus empty array conventions.
- Check timestamps, money, per-unit rates, and decimal percentages.
- Check that no non-target batch rows leaked into the answer.
