---
name: sql-payer-ops
description: Solve task_group_014_sql_payer_ops tasks by querying the provided SQLite service for utilization management, pharmacy appeals, reimbursement compliance, and payer-service profitability outputs.
---

# SQL Payer Ops

Use this skill for payer-operations SQL tasks where the input folder contains a prompt, an answer template, and a scoped payload. The work is to query the remote SQLite service documented in `environment_access.md` and return one JSON object matching the template.

## Operating Procedure

1. Read `environment_access.md`, the task prompt, the scope/worklist payload, and `answer_template.json`. Do not hard-code the runtime host; use the environment access file.
2. Extract only staged scope values: case IDs, medication case IDs, target bucket, clinics, periods, plan types, service categories, materiality thresholds, and active statuses.
3. Discover schema through the SQL service before writing business SQL:
   ```sql
   SELECT name, sql
   FROM sqlite_master
   WHERE type = 'table'
   ORDER BY name;
   ```
4. Build narrow CTE queries scoped to the payload values. Prefer one joined fact query and one targeted rule/aggregate query over row browsing.
5. Produce JSON with exactly the template keys, sorted deterministically. Sort case lists by case ID or medication case ID when requested; otherwise sort reporting rows by quarter, clinic, payer/plan type, and service category.
6. Round money and per-unit amounts to 2 decimals. Round percentages/ratios to 4 decimals. Keep percentages as decimals, not 0-100 values.

## Core Tables

Common tables:
- Authorization: `authorization_requests`, `auth_lines`, `members`, `plans`, `providers`, `facilities`, `service_codes`, `existing_authorizations`, `state_sla_rules`.
- Clinical review: `coverage_criteria`, `criteria_sources`, `clinical_facts`, `evidence_documents`, `case_review_events`, `p2p_sessions`.
- Medication appeals: `medication_cases`, `appeals`, `drug_policy_requirements`, `medication_trials`, `assistance_programs`, `household_financials`.
- Finance: `encounters`, `rate_schedules`, `claim_corrections`, `clinic_costs`, `clinic_budgets`.

## Authorization Intake

Evaluate intake failures in template order: active coverage, COB completion, covered service, network, service area, PA/notification, retrospective submission, duplicate authorization, then none.

Useful checks:
- Active coverage: member coverage dates must include the requested service/request timing. Watch for retro reinstatement fields.
- COB: compare request-level and member-level COB fields when both exist; do not assume they always agree.
- Covered service and PA: inspect every `auth_lines` CPT against `service_codes`. A notification-only code is usually closed without clinical review; a noncovered code is an intake denial.
- Network/service area: use requesting/servicing provider network and facility service-area facts; handle explicit out-of-network exceptions before denying.
- Retrospective submission: `rendered_before_submission` is an intake halt if reached.
- Duplicates: match same member and CPT to active/approved `existing_authorizations` with overlapping service dates.
- Gold card: require plan gold-card allowance, provider gold-card status, no service exclusion, no mandatory MD review, and all lines eligible. If any intake halt happens first, gold card is not reached.
- Review queue: route by `external_vendor`, `specialty_program`, and `mandatory_md_review`; otherwise use nurse clinical review. Intake halts have no clinical review; gold-card cases use auto approval.
- SLA: join `state_sla_rules` by state and applicable plan type. Use urgency to choose routine days, urgent hours, or stat hours. Respect `day_type` for business-day vs calendar-day due times.

## Clinical Review

Start from scoped `authorization_requests.target_bucket` or listed case IDs. Aggregate requested units from `auth_lines` at the case/service-category level.

Criteria source selection:
- `criteria_sources.service_category_filter` may be `ALL`; include both service-specific and `ALL` rows.
- Prefer plan-specific sources over `ALL` when applicable, then lowest `precedence_rank`.
- Join `coverage_criteria` on `criteria_source_id`, `service_category`, and compatible `plan_type_filter`.

Evidence rules:
- Required criteria are missing when the case lacks the key, the `fact_value` does not equal the required value, or the supporting evidence is stale/unclear/conflicting.
- Approve as requested only when all required criteria are cleanly met; `approved_units` is the requested line-unit total.
- Escalate to MD for criteria not met, adverse clinical posture, mandatory MD categories, or insufficient evidence that cannot be handled as a simple information request.
- P2P suitability is usually for adverse or MD-escalated cases where provider discussion could add information, not for clean approvals.
- Queue counts must align with row-level `md_escalation_required`, `nurse_recommendation`, and `p2p_suitable`.

## Medication Appeals And Assistance

Keep payer appeal routing separate from manufacturer assistance routing.

Appeal workflow:
- Join medication case to member plan, appeal intake, policy requirements, and medication trials.
- Timeliness is based on `adverse_notice_date`, `appeal_received_date`, and the applicable appeal window. If no rule table is present, use the prompt/business context rather than assuming a commercial-only 180-day rule.
- Policy missing keys come from `drug_policy_requirements`: diagnosis, step therapy, TB screen, topical failure, etc. Map diagnosis from case diagnosis and therapy requirements from documented trials/evidence.
- Expedited classification depends on the expedited request/attestation and whether evidence supports the request; otherwise use standard 30-day.

Assistance workflow:
- Join `assistance_programs` and `household_financials`.
- Evaluate income against the program FPL threshold, commercial-insurance requirements, government-plan exclusions, denial-letter requirements, and assistance consent.
- If any blocking reason exists, `program_owner` is `not_routed`; otherwise route to the manufacturer assistance team.
- `path_separation` reflects active routes: appeal only, assistance only, parallel, or no active route.

## Reimbursement Compliance

Use the audit payload for clinics, quarters, materiality, and active recovery statuses.

Paid-rate compliance:
- Join `encounters` to `rate_schedules` by payer, plan type, service category, CPT, clinic state, and service-date effective range.
- Separate paid-rate compliance from recovery tracking. Denied/unpaid encounters should be counted in exclusions and not allowed to distort paid-per-unit compliance metrics.
- Aggregate paid cells by quarter, clinic, payer, plan type, and service category.
- `variance_amount = benchmark_amount - paid_amount`; underpayment is positive.
- Flag material cells only when paid units, underpayment dollars, and underpayment percentage all meet the payload thresholds.
- `paid_per_unit = paid_amount / paid_units`; `benchmark_per_unit = benchmark_amount / paid_units`.

Recovery:
- Use only active statuses supplied by the payload.
- `tracked_recovery_amount` is separate from paid-rate variance.
- Top recovery opportunity is the scoped active correction with the largest `expected_recovery_amount`, with the encounter details copied through.

Clinic-quarter summaries:
- Include paid encounters/units/amounts, benchmark amount, variance, excluded denied/unpaid count, active tracked recovery, material cell count, and classification.
- Keep summary totals consistent with the flagged rows and recovery rows.

## Payer-Service Profitability

Scope by fiscal year/date range, clinics, plan types, and service categories from the worklist.

Cell math:
- Aggregate by clinic, plan type, and service category.
- `open_recovery` should follow the prompt wording: if it says open opportunities, use `status = 'open'`; if it provides active statuses, use those.
- `net_revenue = paid_amount + open_recovery`.
- `cost_per_unit = direct_cost_per_unit + allocated_overhead_per_unit`.
- `total_cost = units * cost_per_unit`.
- `net_margin = net_revenue - total_cost`.
- `margin_pct = net_margin / net_revenue` when revenue is nonzero.

Budget targets:
- `clinic_budgets` may have multiple rows per clinic/service without a plan-type column. Never select a non-grouped budget field from a grouped SQLite query.
- If no unique budget row matches the output grain, aggregate budget rows first. A defensible default target is expected-net-revenue-weighted margin:
  ```sql
  SUM(expected_net_revenue * expected_margin_pct) / SUM(expected_net_revenue)
  ```
- Flag cells whose `margin_pct` is below `budget_margin_pct`.

Actions and rankings:
- Rank loss drivers by most negative `net_margin`; return the top three.
- `projected_improvement_amount = max(0, net_revenue * budget_margin_pct - net_margin)`.
- Include all analyzed cells in `payer_service_results`, not only flagged cells.
- Keep `payer_actions`, `flagged_pair_count`, and `total_projected_improvement` internally consistent.

## Pitfalls

- Do not inventory unrelated `target_bucket` values. Query only buckets and IDs from the staged input.
- Do not rely on SQLite's arbitrary value for columns that are neither grouped nor aggregated.
- Do not mix appeal and assistance eligibility; a case can have a payer appeal route while manufacturer assistance is blocked.
- Do not count recovery dollars as paid-rate compliance variance.
- Do not round intermediate values before grouping; round only final JSON values.
- Keep enum-like output strings close to the template and prompt language. Avoid inventing verbose prose for fields intended as compact action/status codes.
