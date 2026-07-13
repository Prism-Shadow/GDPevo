---
name: sql-payer-ops
description: Solve payer-operations SQL tasks that use a remote SQLite query service and require JSON answers for utilization management intake, clinical review, pharmacy appeals and assistance, reimbursement compliance, or rehab profitability. Use when prompts reference payer ops tables such as authorization_requests, auth_lines, medication_cases, encounters, rate_schedules, claim_corrections, clinic_costs, or clinic_budgets and ask for exact answer_template.json output.
---

# SQL Payer Ops

## Operating Procedure

1. Read `environment_access.md`, the task prompt, all payloads, and `answer_template.json`. Do not hard-code the remote host; get the base URL and credentials from `environment_access.md`.
2. Use only the SQL service. Submit read-only SQLite through `POST /query`:

```bash
SQL="SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
jq -n --arg sql "$SQL" '{sql:$sql, params:[]}' \
  | curl -sS -u "$BASIC_USER:$BASIC_PASS" \
      -H 'Content-Type: application/json' --data @- "$BASE_URL/query" \
  | jq .
```

3. Confirm schema before logic:

```sql
SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name;
SELECT * FROM pragma_table_info('authorization_requests');
```

4. Restrict SQL to the target scope from the payload: explicit case IDs, medication case IDs, target bucket, clinics, periods, plan types, and service categories. Avoid broad non-target exploration.
5. Build answer rows from SQL aggregates, then conform exactly to the template: same keys, enum spelling, JSON types, `null` where appropriate, no markdown.
6. Keep calculations unrounded in CTEs; round only final output. Money and per-unit rates usually round to 2 decimals. Percent ratios are decimals, usually rounded to 4 places.

## Core Table Map

- Authorization intake/review: `authorization_requests`, `auth_lines`, `service_codes`, `members`, `plans`, `providers`, `facilities`, `existing_authorizations`, `state_sla_rules`.
- Clinical criteria: `criteria_sources`, `coverage_criteria`, `clinical_facts`, `evidence_documents`, `case_review_events`, `p2p_sessions`.
- Pharmacy: `medication_cases`, `appeals`, `drug_policy_requirements`, `medication_trials`, `assistance_programs`, `household_financials`, plus `members` and `plans`.
- Claims and reimbursement: `encounters`, `rate_schedules`, `claim_corrections`.
- Profitability: `encounters`, `clinic_costs`, `clinic_budgets`, `claim_corrections`.

## Authorization Intake Rules

Join each target case to member, plan, requesting/servicing providers, facility, service lines, service-code rules, existing authorizations, and SLA rules.

Evaluate intake halts before gold-card or review routing:

1. `active_coverage`: request/service date outside member coverage.
2. `cob_completion`: COB processing flag is incomplete.
3. `covered_service`: any requested code is not covered.
4. `network`: requesting or servicing provider is out of network without an exception.
5. `service_area`: facility is outside service area without an exception.
6. `pa_required`: PA is not required or code is notification-only.
7. `retrospective_submission`: service was rendered before submission.
8. `duplicate_authorization`: same member and CPT with an open/approved existing authorization overlapping the requested service window.
9. `none`: clean intake.

Common dispositions: coverage halt, COB hold, noncovered-service denial, network/service-area denial, notification-only close, retrospective halt, duplicate halt, gold-card auto-approval, or ready for review. Duplicate IDs should be sorted and include only matching active/open/approved duplicates.

Gold-card auto approval generally requires plan gold-card eligibility, requesting provider gold-card active, no service gold-card exclusion, no mandatory MD review, and no earlier intake halt. If not auto-approved, route by service-code program: external vendors such as `MedImage Review`, `CareEquip Review`, or `HomeCare Review`; mandatory MD to `Medical Director Review`; otherwise `Nurse Clinical Review`.

Provider follow-up is independent of intake disposition: active sanctions outrank inactive credentials; otherwise `none`.

SLA due dates come from `state_sla_rules` matched by plan/facility state and plan type. Preserve the receipt timestamp time. Use calendar days for `day_type = 'calendar'`; add business days for `day_type = 'business'`; urgent/stat use hours. `sla_basis` should name the state(s), plan type, day type, and duration. If plan and facility states both matter, include both state codes.

Notice flags are usually true for adverse/duplicate/retrospective/noncovered outcomes and false for non-adverse holds such as COB hold unless the prompt says otherwise.

## Clinical Review Rules

For target authorization cases:

- Pick the applicable criteria source by `criteria_sources.precedence_rank`, matching plan type and service category when such filters exist. Then use required rows in `coverage_criteria`.
- A required criterion is satisfied only when the case has `clinical_facts.fact_value` equal to the required value and `confidence_flag = 'clear'`. Treat `partial`, `stale`, `conflicting`, `unclear`, missing, or `not_met` facts as missing evidence.
- Sort `missing_evidence_keys` by the criteria order/key used in SQL.
- Approve as requested only when all required criteria are clearly met and the service is covered with no mandatory MD barrier. Use requested total units for `approved_units`.
- Escalate to MD for benefit exclusions, mandatory MD review, adverse multiline requests, or criteria not clearly met. Use `approved_units: null` when not approving.
- `p2p_suitable` is true for remediable missing clinical evidence, but false for approvals and hard benefit/exclusion or mandatory-MD-only barriers.

Queue counts are simple counts of the case-level decisions. For MD escalations by service category, include only categories with nonzero MD escalations.

## Pharmacy Appeals and Assistance

Keep payer appeal routing separate from manufacturer assistance.

Appeals:

- Join `medication_cases` to `appeals`, member plan type, `drug_policy_requirements`, and documented medication trials.
- Filing deadline is usually 60 calendar days after `adverse_notice_date`; `deadline_status` is timely when the appeal was received on or before that date.
- Required policy keys come from `drug_policy_requirements` matching drug and plan filter. Diagnosis is satisfied by a diagnosis on the medication case. Trial-based requirements need documented, relevant failed therapy or other explicit supporting evidence.
- `appeal_not_timely` outranks missing evidence. Otherwise, missing policy keys make `appeal_incomplete`; no missing keys makes `appeal_ready`.
- If expedited attestation is present and the appeal is ready, classify as `expedited_accepted_72h`; if expedited is requested but evidence is missing, use `expedited_requested_needs_evidence`; otherwise use `standard_30d`.

Manufacturer assistance:

- Join to `assistance_programs` by drug and to `household_financials` by member.
- Use 2025 mainland FPL when no table provides thresholds: household size 1 = 15650, 2 = 21150, 3 = 26650, 4 = 32150; add 5500 for each extra person. Income limit is FPL times `max_income_fpl / 100`.
- Blocking reasons, in stable order: `income_over_program_limit`, `commercial_insurance_required`, `government_plan_excluded`, `denial_letter_missing`, `assistance_consent_missing`.
- Financial or insurance blockers mean `program_owner = 'not_routed'`. If only documents/consent are missing, or the member is otherwise eligible, route to `manufacturer_assistance_team`.
- `path_separation` should reflect active routes: `appeal_only`, `assistance_only`, `parallel_appeal_and_assistance`, or `no_active_route`.

## Reimbursement Compliance

Use the audit scope for clinics, quarters, materiality thresholds, and active recovery statuses.

Paid-rate compliance:

- Include paid encounters in the period and target clinics. Exclude denied/unpaid encounters from paid-rate aggregates; count them separately as `excluded_denied_or_unpaid_encounters`.
- Match `rate_schedules` by payer, plan type, service category, CPT, state, and service date within effective dates.
- Benchmark amount is `SUM(units * benchmark_rate)`.
- Variance amount is `paid_amount - benchmark_amount`; variance percent is `variance_amount / benchmark_amount`.
- A material underpayment cell generally requires paid units at or above threshold, underpayment amount at or above threshold, and underpayment percent at or above threshold.
- Keep recovery opportunities separate from paid-rate compliance. Sum `claim_corrections.expected_recovery_amount` only for statuses listed as active in the scope.

`flagged_variances` are payer/plan/service cells, not whole clinics. Include sorted distinct `rate_schedule_rate_ids`. `top_recovery_opportunity` is the active correction with the largest expected recovery in scope; include encounter and correction details.

## Rehab Profitability

Use the worklist period, clinics, plan types, and service categories.

For each clinic/plan/service cell:

- Aggregate encounters in the period. Revenue is paid amount plus open claim-correction recovery for scoped encounters.
- Cost per unit is `clinic_costs.direct_cost_per_unit + allocated_overhead_per_unit`; total cost is units times cost per unit.
- Net margin is net revenue minus total cost. Margin percent is `net_margin / net_revenue` when net revenue is nonzero.
- Budget margin percent comes from `clinic_budgets` for the clinic, fiscal year, and service category; when multiple budget rows exist for the same service, use the highest expected margin target.
- `on_or_above_budget` when actual margin percent meets the budget target; otherwise use a shortfall class from the template, commonly `major_shortfall`.
- Treat very low-volume shortfalls as `noise`; otherwise shortfalls are `persistent`. In the observed pattern, fewer than 5 encounters was noise.
- Projected improvement to budget is:

```text
total_cost / (1 - budget_margin_pct) - net_revenue
```

Use zero or omit payer action for cells already on/above budget. For shortfall cells, use `recover_and_rate_floor_review` when open recovery exists; otherwise `rate_floor_review`.

Rank top loss drivers by most negative net margin. Sort portfolio rows and payer actions by `clinic_id`, `plan_type`, then `service_category` unless the prompt says otherwise.

## Output Conventions and Pitfalls

- Sort case rows by ascending case ID or medication case ID. Sort clinic-quarter rows by clinic then quarter unless the template/prompt states a different order.
- Use arrays for IDs and missing keys even when empty. Do not emit placeholder strings from templates.
- Use `null`, not `0`, for values that do not apply, such as approved units on escalated clinical cases or absent assistance programs.
- Summary counts must reconcile exactly to detail rows.
- Do not let hidden or non-target buckets influence logic. Query only the target IDs/buckets and schema needed for the task.
- Recheck enum spelling from `answer_template.json`; these tasks are sensitive to exact strings.
