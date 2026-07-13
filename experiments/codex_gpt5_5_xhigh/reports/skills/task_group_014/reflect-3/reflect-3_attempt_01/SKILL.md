---
name: task-group-014-sql-payer-ops
description: Solve task_group_014_sql_payer_ops tasks that require producing JSON answers from the payer operations SQLite query service, including UM intake, clinical review, pharmacy appeals, reimbursement compliance, and rehab profitability analyses.
---

# SQL Payer Ops Procedure

## Start Every Task

Read `environment_access.md`, the task prompt, the staged payload, and `answer_template.json`. Use the SQL query service described in `environment_access.md`; do not hard-code its host. Submit only read-only SQLite.

Derive scope only from staged inputs: explicit case IDs, target bucket/worklist labels, clinic IDs, dates, quarters, plan types, service categories, materiality, and active statuses. Do not inventory unrelated buckets.

Inspect schema with:

```sql
SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;
PRAGMA table_info(table_name);
```

Common table names: `authorization_requests`, `auth_lines`, `members`, `plans`, `providers`, `facilities`, `service_codes`, `existing_authorizations`, `state_sla_rules`, `coverage_criteria`, `criteria_sources`, `clinical_facts`, `evidence_documents`, `case_review_events`, `p2p_sessions`, `medication_cases`, `appeals`, `medication_trials`, `drug_policy_requirements`, `assistance_programs`, `household_financials`, `encounters`, `rate_schedules`, `claim_corrections`, `clinic_costs`, `clinic_budgets`.

## Output Discipline

Return exactly the template shape, no extra keys. Preserve native JSON booleans/nulls. Sort case rows by ascending case ID or medication case ID; sort finance cells by the requested period/clinic/payer/plan/service order unless the prompt says otherwise.

Round money, rates, and per-unit amounts to 2 decimals. Round percentage ratios as decimal numbers to 4 decimals. Use `YYYY-MM-DD` and `YYYY-MM-DDTHH:MM` exactly when requested.

## UM Intake

Scope cases from explicit `target_case_ids` or the staged `target_bucket`. Join request header, member, plan, requesting/servicing providers, facility, auth lines, service codes, existing authorizations, and SLA rules.

Apply intake checks in template order: active coverage, COB completion, covered service, network, service area, PA/notification, retrospective submission, duplicate authorization, then no intake failure. Do not rely on `authorization_requests.status` alone; it can reflect later workflow state.

Useful rules:

- Active coverage: service dates must sit inside member coverage dates, considering retro reinstatement if present.
- COB: use both member COB status and request-level processed flag.
- Covered/PA: roll up all lines; one noncovered line is enough for a service denial.
- Duplicate: match member and CPT to approved/active `existing_authorizations` with overlapping service dates; return existing auth IDs sorted.
- Provider item is independent of final disposition: active sanctions and inactive credentials should still be surfaced.
- Gold card is considered only after intake passes: plan allows gold card, requesting provider is gold-card active, service is not gold-card excluded, and no mandatory MD condition applies. Multiple failed gold-card gates should use the multiple-reasons enum if available.
- Review queue: intake halt -> `No Review - Intake Halt`; auto approval -> `Auto Approval`; external vendor values map directly when present (`MedImage Review`, `CareEquip Review`, `HomeCare Review`); mandatory MD -> `Medical Director Review`; otherwise use nurse review.
- SLA: choose `state_sla_rules` by applicable state and plan type, honor calendar vs business-day rule, and compute from receipt timestamp.

## Clinical Review

Scope from the worklist bucket. Join auth header/lines, plan type, service code flags, coverage criteria, criteria sources, clinical facts, evidence documents, prior review events, and P2P rows.

Choose a criteria source that actually has applicable `coverage_criteria` rows for the service and plan type; use `criteria_sources.precedence_rank` to break ties. Do not select a high-precedence source if it has no criteria rows for that service.

For each required criterion, compare `clinical_facts.fact_value` to `coverage_criteria.required_value`. Missing evidence keys should be the policy keys that are absent, unclear, not met, stale, or conflicting enough to prevent nurse approval. Keep key order stable, usually criteria order.

Nurse approval is appropriate only when all required evidence is current and met and no mandatory MD/vendor rule blocks nurse approval. Escalate to MD for mandatory MD services, adverse/non-met criteria, unresolved conflicts, or cases already in an MD-review posture. P2P is usually for adverse clinical posture where discussion could resolve the issue, not for simple document collection.

Use approved units only for approvals. Check whether the local task wants header `requested_total_units` or summed `auth_lines.units`; if they conflict, state one convention internally and use it consistently.

## Pharmacy Appeals And Assistance

Scope medication cases from staged medication IDs or target docket. Join `medication_cases` to `members`/`plans`, `appeals`, `drug_policy_requirements`, `medication_trials`, `assistance_programs`, and `household_financials`.

Keep payer appeal routing separate from manufacturer assistance routing:

- Member plan type comes from member/plan facts; appeal records may carry a separate governing plan field.
- Missing policy requirements come only from `drug_policy_requirements.requirement_key` values. Validate diagnosis from the med case diagnosis; validate step therapy/topical failure/TB screen from documented trials or other available evidence.
- Timeliness starts from `adverse_notice_date`; calculate filing deadline by the applicable plan rule in the task/data and compare `appeal_received_date`.
- Expedited classification depends on expedited attestation and supporting/new evidence. Without expedited support, classify as standard.
- Manufacturer assistance checks are separate: income vs program FPL limit, commercial-insurance requirement, government-plan exclusion, denial-letter requirement, and assistance consent.
- `program_owner` should be `manufacturer_assistance_team` only when the case is actually routed or needs manufacturer follow-up; otherwise `not_routed`.
- `path_separation` should describe active routes: appeal only, assistance only, parallel, or no active route.

## Reimbursement Compliance

Use scoped clinics and periods only. For paid-rate compliance, join paid encounters to rate schedules on payer, plan type, service category, CPT, clinic/state, and effective date. Inspect unmatched paid CPTs; do not let them silently distort flagged variance cells.

For a paid-rate cell:

```text
benchmark_amount = SUM(units * benchmark_rate)
variance_amount = benchmark_amount - paid_amount
variance_pct = variance_amount / benchmark_amount
```

Flag only positive underpayments meeting all materiality gates: minimum paid units, minimum underpayment amount, and minimum underpayment percent. Keep rate schedule IDs distinct and sorted.

Clinic-quarter results should keep paid-rate compliance separate from recovery opportunities. Count denied/unpaid exclusions separately. Use the active recovery statuses supplied in the audit scope for tracked recovery and top recovery opportunity. Top recovery is the largest expected recovery amount among active scoped corrections.

## Rehab Profitability

Scope by staged fiscal year/date range, clinics, plan types, and service categories. Aggregate encounters by clinic, plan type, and service category.

Use:

```text
open_recovery = SUM(claim_corrections.expected_recovery_amount where status = 'open')
cost_per_unit = direct_cost_per_unit + allocated_overhead_per_unit
total_cost = units * cost_per_unit
net_revenue = paid_amount + open_recovery
net_margin = net_revenue - total_cost
margin_pct = net_margin / net_revenue
projected_improvement_amount = max(0, budget_margin_pct * net_revenue - net_margin)
```

If the prompt explicitly supplies active statuses, use those statuses instead of literal `open`. Otherwise, do not sweep in `pending documents` or `submitted`.

`clinic_budgets.payer` may be the payer name, not a plan type. If multiple budget rows exist per clinic/service, inspect row blocks before joining. A common generated order is Commercial, Medicare Advantage, Medicaid, Exchange, Dual Eligible across repeated service-category blocks; verify against local data before using it. Do not blindly join `clinic_budgets.payer = encounters.plan_type`.

Rank loss drivers by lowest `net_margin`, ascending, and return only the top requested count. Flag payer actions for cells below budget margin; use `major_shortfall` for large negative gaps and a non-flagged class for cells at/above budget. Portfolio totals should reconcile to the payer-service rows.

## Common Pitfalls

- `status` columns often reflect downstream workflow; derive requested classifications from business rules and scoped facts.
- Do not mix appeal routing with manufacturer assistance eligibility.
- Do not count recovery dollars as paid-rate compliance variance.
- Use benchmark denominator for reimbursement variance percent unless the prompt explicitly says otherwise.
- Treat template strings as strict enums. Reuse template spellings exactly.
- Build summaries from the rows you return, not from a separate broader query.
