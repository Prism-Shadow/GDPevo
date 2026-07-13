---
name: sql-payer-ops
description: Operating procedure for payer operations SQL tasks covering UM intake, clinical review, medication appeals, reimbursement compliance, and rehab profitability.
---

# SQL Payer Ops

Use this skill when a task asks for payer operations analysis through the shared SQLite query service. The task usually provides a prompt, scoped payload, and answer template. Your job is to return one JSON object matching the template exactly.

## Ground Rules

- Read `environment_access.md` for the query URL and Basic Auth. Do not hard-code the runtime host.
- Use only read-only SQL through the service: `POST /query` with `{"sql":"SELECT ...","params":[]}`.
- Start from the staged payload, not from database inventories. Put case IDs, target buckets, clinics, periods, plan types, and service categories from the payload into CTEs and join through those CTEs.
- Inspect schema with `sqlite_master` and, when needed, `PRAGMA table_info(table_name)`. Then run narrow joins on the target scope.
- Treat `NULL` and text sentinel values like `ALL` as wildcard filters in criteria, policy, and source tables.
- Preserve the answer template's field names, nested objects, enum spelling, booleans, arrays, and scalar types. Sort case rows by case ID or medication case ID when requested.

## Core Schema Map

- Authorization intake and clinical review: `authorization_requests`, `auth_lines`, `service_codes`, `members`, `plans`, `providers`, `facilities`, `existing_authorizations`, `state_sla_rules`, `coverage_criteria`, `criteria_sources`, `clinical_facts`, `evidence_documents`, `case_review_events`, `p2p_sessions`.
- Medication appeals and assistance: `medication_cases`, `appeals`, `members`, `plans`, `drug_policy_requirements`, `medication_trials`, `household_financials`, `assistance_programs`.
- Reimbursement and profitability: `encounters`, `rate_schedules`, `claim_corrections`, `clinic_costs`, `clinic_budgets`.

## Authorization Intake

Build one row per target `authorization_requests.case_id`. Join line items to `service_codes`, member coverage to `members` and `plans`, requesting and servicing providers to `providers`, facility service area to `facilities`, and duplicate candidates to `existing_authorizations`.

Apply intake gates in template order:

1. `active_coverage`: request or service dates outside member coverage, unless the data explicitly shows reinstatement that covers the date.
2. `cob_completion`: COB status or processed flag indicates the primary payer work is not complete.
3. `covered_service`: any requested service code has `covered = 0`.
4. `network`: required provider/facility network checks fail and no out-of-network exception applies.
5. `service_area`: facility is outside service area.
6. `pa_required`: no PA is required or the line is notification-only.
7. `retrospective_submission`: rendered-before-submission or service already occurred before receipt, according to task wording.
8. `duplicate_authorization`: same member and CPT already has an active or approved authorization whose service dates overlap the requested service window.
9. `none`: all intake gates pass.

Map the first failing gate to the corresponding `intake_disposition`. Use `duplicate_existing_auth_ids` as a sorted array; use `[]` when none. If an intake gate fails, set `gold_card_decision` to `not_reached_intake_halt` and `review_queue` to `No Review - Intake Halt`.

Gold card is reached only after intake passes. Auto-approve only when the plan allows gold carding, the requesting provider is gold-card active, and no requested service line has a gold-card exclusion or mandatory MD review. Otherwise choose the most specific not-eligible enum, or multiple-reasons when more than one blocker exists.

Queue assignment comes from service-code flags after intake/gold-card handling:

- External or specialty vendors map to queues such as `MedImage Review`, `CareEquip Review`, or `HomeCare Review`.
- `mandatory_md_review = 1` maps to `Medical Director Review`.
- Otherwise use `Nurse Clinical Review`.

For SLA, take urgency from the request. Prefer a matching `state_sla_rules` row by state and plan type, treating `ALL` as wildcard; fall back to plan SLA columns. Calendar rules add elapsed days or hours directly to `receipt_timestamp`; business-day rules must skip weekends. Populate `sla_basis` with the rule source and duration. Set provider follow-up from requesting provider sanctions or inactive credentials. Count summaries from the finished case rows.

## Clinical Review Slate

Scope cases by the payload's target bucket or case IDs. For each case, derive one service category from `auth_lines`; when multiple lines share the same category, sum requested units.

Criteria logic:

- Choose criteria sources effective on or before the review date. Match plan type and service category with `ALL` or `NULL` as wildcard. Lower `precedence_rank` is stronger.
- Use `coverage_criteria` rows for the selected source and service category. Required criteria have `is_required_for_approval = 1`.
- Compare to current evidence by joining `clinical_facts` to `evidence_documents` and preferring `is_current = 1` plus the best source rank.
- A requirement is satisfied only when `fact_value` equals the required value, usually `met`. Values like `unclear`, `not_met`, absent facts, or non-current evidence belong in `missing_evidence_keys`.

Recommend nurse approval only when all required criteria are met and there is no mandatory MD or prior adverse posture. Set approved units to requested units for approvals, otherwise `0` unless the task gives a partial-approval rule. Escalate to MD when a service code mandates it, a policy requirement is not met, the category is experimental/nonstandard, or review history already indicates adverse or MD posture. Mark P2P suitable for cases where missing or unclear clinical evidence could plausibly resolve the issue; avoid P2P for pure administrative intake failures.

Build `queue_counts` from the completed case review rows, keyed by service category exactly as returned.

## Medication Appeals And Assistance

Keep payer appeal routing separate from manufacturer assistance routing.

For each target `med_case_id`, join:

- `medication_cases` to `members` and `plans` for member plan type.
- `appeals` where `appeal_subject_type` is medication and `case_or_med_case_id` matches.
- `drug_policy_requirements` by drug and plan type, treating `ALL` or `NULL` as wildcard.
- `medication_trials` for documented step therapy, topical failure, TB screen, or other requirement evidence.
- `household_financials` and `assistance_programs` by member and drug.

Appeal routing:

- Filing deadline is driven by the adverse notice date and the task's appeal window; if no other rule is provided, payer appeals commonly use 60 calendar days.
- `deadline_status` is based on received date versus filing deadline.
- `missing_policy_requirements` are required policy keys lacking matching, documented evidence. Do not let undocumented trials satisfy a requirement.
- Use `appeal_not_timely` for late appeals. Use `appeal_incomplete` when timely but missing policy evidence, required representation, or expedited evidence. Use `appeal_ready` only when timely and administratively complete.
- Expedited classification follows the appeal record: accept 72-hour expedited handling only when expedited is requested and supporting clinical/new-evidence requirements are present; otherwise use the needs-evidence or standard enum from the template.

Assistance routing:

- Check program gates independently: income/FPL threshold, commercial-insurance requirement, government-plan exclusion, denial-letter requirement, and assistance consent.
- Populate `blocking_reasons` from the template enum only. If no blockers remain, route to `manufacturer_assistance_team` with program ID and form name; otherwise use `not_routed`.
- `path_separation` is `parallel_appeal_and_assistance` when both paths are active, `appeal_only` or `assistance_only` when just one is active, and `no_active_route` otherwise.

Summaries are simple counts from the finished medication case rows.

## Reimbursement Compliance

Use the audit payload as the source of clinics, clinic states, periods, materiality thresholds, and active recovery statuses. Embed clinic state in a CTE if no clinic dimension table exists.

Rate comparison:

- Paid-rate compliance uses paid encounters only, usually `paid_amount > 0`. Count denied or unpaid encounters separately for `excluded_denied_or_unpaid_encounters`.
- Join `rate_schedules` by payer, plan type, service category, CPT code, clinic state, and service date within effective dates.
- `benchmark_amount = units * benchmark_rate`.
- `variance_amount = paid_amount - benchmark_amount`; underpayments are negative.
- `variance_pct = variance_amount / benchmark_amount`.
- A material underpayment cell must meet all task materiality thresholds: minimum paid units, minimum underpayment dollars, and minimum underpayment percentage.

Keep recovery opportunities separate from paid-rate compliance. Sum `claim_corrections.expected_recovery_amount` only for active statuses from the payload. Pick `top_recovery_opportunity` by highest expected recovery, with deterministic ties by deadline and correction ID.

Sort clinic-quarter results by clinic and quarter. Sort flagged variance rows deterministically, typically by quarter, clinic, payer, plan type, service category, then largest underpayment if the template or prompt does not specify otherwise. Money and rates round to 2 decimals; percentages round to 4 decimals.

## Rehab Profitability Action List

Scope by the payload's analysis period, clinics, plan types, and service categories.

Aggregate before joining:

- Encounters: paid revenue and units by clinic, payer, plan type, and service category.
- Corrections: open or active expected recovery by the same cell. Use the task's status wording; if it says open claim recovery, do not include closed corrections.
- Costs: `cost_per_unit = direct_cost_per_unit + allocated_overhead_per_unit` from `clinic_costs`.
- Budgets: `clinic_budgets` may have multiple rows per clinic/payer/service and no plan-type column. Aggregate it first by clinic, payer, fiscal year, and service category. Use revenue-weighted expected margin when multiple budget rows exist.

Profitability formulas:

- `net_revenue = paid_amount + open_recovery`.
- `total_cost = units * cost_per_unit`.
- `net_margin = net_revenue - total_cost`.
- `margin_pct = net_margin / net_revenue`.
- `projected_improvement_amount = max(0, budget_margin_pct * net_revenue - net_margin)`.

Classify budget variance from the gap between actual and budget margin. Use explicit task thresholds if given; otherwise `at_or_above_budget` when actual margin meets budget, `shortfall` for below-budget cells, and `major_shortfall` for large negative gaps. A practical default for major is at least 20 percentage points below budget or negative margin against a positive budget.

Classify persistence by checking the same clinic, payer or plan type, and service category over subperiods when dates allow it: `persistent` if the cell is below budget in multiple quarters or repeated periods, otherwise `emerging`. Rank top loss drivers by most negative `net_margin`, then stable tie-breakers.

Recommended actions should be controlled payer operations actions, for example:

- `rate_floor_review` for structurally underpaid payer-service cells.
- `claims_recovery_workqueue` when recoveries drive the improvement opportunity.
- `utilization_or_cost_review` when cost per unit is the main driver.

## Final JSON Checks

- Return only JSON, no prose, for task answers.
- Keep arrays present even when empty.
- Do not output `null` unless the template explicitly allows it.
- Recompute all summary counts from detail rows.
- Recheck rounding after aggregation, not before.
- Verify no duplicate rows were introduced by many-to-one joins, especially rates, criteria, corrections, and budgets.
