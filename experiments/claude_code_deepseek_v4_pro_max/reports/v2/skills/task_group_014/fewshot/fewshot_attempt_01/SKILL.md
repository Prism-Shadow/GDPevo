# Payer Operations SQL Analytics Skill

## Overview

This skill covers payer-side healthcare operations queries across five domains: authorization intake auditing, clinical review slates, pharmacy appeal and manufacturer assistance routing, reimbursement compliance, and outpatient rehab profitability. All work is done against a remote SQLite query service via HTTP POST with Basic Auth.

## Environment Setup

- **Base URL**: Read from `environment_access.md` — no hard-coded host or port.
- **Query endpoint**: `POST <BASE_URL>/query` with JSON body `{"sql": "...", "params": []}`.
- **Auth**: HTTP Basic Auth; credentials provided in `environment_access.md`.
- **No local DB**: Every query goes through the HTTP service. Never assume a local SQLite file path.

## SQL Discovery SOP

Follow this order for every new task:

1. **List all tables**: `SELECT name FROM sqlite_master WHERE type='table' ORDER BY name`
2. **Inspect schema per relevant table**: `PRAGMA table_info('<table_name>')`
3. **Spot-check distinct values** on categorical columns: `SELECT DISTINCT <col> FROM <table> ORDER BY <col>`
4. **Trace foreign keys**: Join through ID columns (`member_id`, `plan_id`, `provider_id`, `facility_id`, `case_id`, `encounter_id`, `clinic_id`, etc.) to understand the entity graph.
5. **Sample a few rows** to confirm shape: `SELECT * FROM <table> LIMIT 3`

## Core Table Catalog (by domain)

### Authorization Intake (train_001)
| Table | Key columns |
|---|---|
| `authorization_requests` | case_id, member_id, plan_id, provider_id, facility_id, service_date, request_date, urgency, target_bucket |
| `authorization_line_items` | case_id, cpt_code, service_category, units, diagnosis_code |
| `members` | member_id, coverage_active, cob_primary_payer, state |
| `plans` | plan_id, plan_type, state, line_of_business |
| `providers` | provider_id, sanctions_active, credentials_status, gold_card_eligible |
| `facilities` | facility_id, network_status, service_area |
| `service_code_rules` | cpt_code, service_category, pa_required, covered_service_flag |
| `existing_authorizations` | existing_auth_id, member_id, cpt_code, service_date, status |
| `state_sla_rules` | state, plan_type, urgency, calendar_business, sla_days |

### Clinical Review (train_002)
| Table | Key columns |
|---|---|
| `authorization_requests` | case_id, member_id, review_status |
| `authorization_line_items` | case_id, service_category, units, cpt_code |
| `clinical_evidence` | case_id, evidence_key, evidence_value, evidence_present |
| `criteria_sources` | criteria_source_id, service_category, criteria_name |
| `prior_reviews` | case_id, prior_review_id, review_outcome |

### Pharmacy Appeals (train_003)
| Table | Key columns |
|---|---|
| `medication_requests` | med_case_id, member_id, drug_name, drug_id |
| `appeal_intake` | med_case_id, filing_date, expedited_requested, expedited_granted |
| `medication_trial_history` | member_id, drug_class, trial_drug, trial_completed, trial_failed |
| `drug_policies` | drug_id, policy_requirement (diagnosis, step_therapy, tb_screen, topical_failure) |
| `assistance_programs` | program_id, drug_id, income_limit, insurance_required, form_name |
| `household_financials` | member_id, household_income, household_size, fpl_pct |
| `members` / `plans` | (same as above — plan_type determines government exclusion) |

### Reimbursement Compliance (train_004)
| Table | Key columns |
|---|---|
| `encounters` | encounter_id, clinic_id, payer, plan_type, service_category, cpt_code, service_date, paid_amount, paid_units, denial_code, claim_status, quarter |
| `rate_schedules` | rate_schedule_id, clinic_id, payer, plan_type, service_category, cpt_code, contracted_rate_per_unit, effective_start, effective_end |
| `claim_corrections` | correction_id, encounter_id, correction_type, expected_recovery_amount, status, correction_deadline |

### Outpatient Rehab Profitability (train_005)
| Table | Key columns |
|---|---|
| `encounters` | encounter_id, clinic_id, plan_type, service_category, paid_amount, units, service_date |
| `clinic_costs` | clinic_id, service_category, cost_per_unit |
| `clinic_budgets` | clinic_id, plan_type, service_category, budget_margin_pct |
| `claim_corrections` | correction_id, encounter_id, expected_recovery_amount, status |

## Business Rules Encyclopedia

### Intake Gate Sequence (train_001)
Gates are checked in the order below. Stop at the **first** failure:

1. **active_coverage** — member `coverage_active` flag; fail → `coverage_halt`
2. **cob_completion** — `cob_primary_payer` must be resolved; fail → `cob_hold`
3. **covered_service** — join `authorization_line_items` → `service_code_rules.covered_service_flag`; fail → `noncovered_service_denial`
4. **network** — facility `network_status` must be in-network; fail → `network_denial`
5. **service_area** — facility must be in plan's service area; fail → `service_area_denial`
6. **pa_required** — `service_code_rules.pa_required`; if false → `notification_only_close`
7. **retrospective_submission** — `request_date` after `service_date`; fail → `retrospective_submission_halt`
8. **duplicate_authorization** — same member, same/similar CPT, overlapping timeframe, existing auth in approved/active status; fail → `duplicate_halt`

If ALL gates pass → check gold card eligibility. If gold card eligible → `gold_card_auto_approval` / `ready_for_review` (nurse queue).

### Gold Card Rules
- Gold card applies **only** when plan type supports it, provider is gold-card-eligible, service is gold-card-eligible, and no MD signature is required.
- `gold_card_decision` enum values: `auto_approve`, `not_eligible_plan`, `not_eligible_provider`, `not_eligible_service`, `not_eligible_md_required`, `not_eligible_multiple_reasons`, `not_reached_intake_halt`.

### SLA Timing
- Join `members.state` + `plans.plan_type` + `authorization_requests.urgency` → `state_sla_rules`.
- `calendar_business` field: `"calendar"` = calendar days, `"business"` = business days.
- `sla_due_at` = request_date + sla_days (adjusted for business days if applicable).
- `sla_basis` format: `"{state} {plan_type} {calendar|business} {sla_days} days"` (e.g., `"CA Commercial calendar 5 days"`).

### Notice Requirements
- `notice_required: true` for denials (noncovered_service, network, service_area) and most halts except COB holds.
- `notice_required: false` for COB holds (pending info, not a final denial).

### Provider Items
- Check `providers.sanctions_active` and `providers.credentials_status`.
- Flag `requesting_provider_active_sanction` or `requesting_provider_credentials_inactive` when relevant.
- `"none"` when clean.

### Nurse Clinical Review (train_002)
- Match `criteria_source_id` to the relevant criteria for the service category.
- Check `clinical_evidence` for required evidence keys per the criteria.
- `nurse_recommendation`: `approve_as_requested` if all evidence present and criteria met; `escalate_to_md` otherwise.
- `md_escalation_reason_code`:
  - `benefit_exclusion_or_mandatory_md` — plan benefit exclusion or policy requires MD sign-off (e.g., Experimental Therapy)
  - `criteria_not_clearly_met` — evidence gaps prevent clear determination
  - `adverse_multiline_request` — multi-line request where not all lines are approvable
  - `none` — when not escalating
- `missing_evidence_keys`: list of evidence keys absent from clinical_evidence.
- `p2p_suitable`: true when the gap could be resolved by a peer-to-peer conversation.
- `approved_units`: null when escalating; the requested units when approving.
- `queue_counts.md_escalations_by_service_category`: aggregate MD escalations by service category.

### Pharmacy Appeals (train_003)
**Appeal routing:**
- Check each drug_policies.policy_requirement against medication_trial_history and other records.
- `appeal_incomplete` if any policy requirement is unmet; `appeal_ready` if all met; `appeal_not_timely` if past deadline.
- `expedited_classification`: `expedited_accepted_72h` if expedited_granted; `expedited_requested_needs_evidence` if requested but not yet granted; `standard_30d` otherwise.
- `filing_deadline`: compute from appeal filing date + plan appeal window.
- `deadline_status`: `timely_received` if filed before deadline; `late_received` if past.

**Manufacturer assistance routing:**
- Check `assistance_programs` against member plan_type and household financials.
- Blocking reasons: `income_over_program_limit` (household_income > income_limit), `commercial_insurance_required` (plan_type not Commercial), `government_plan_excluded` (Medicaid/Medicare Advantage), `denial_letter_missing`, `assistance_consent_missing`.
- If **any** blocking reason → `assistance_ineligible`. `program_owner` = `not_routed` unless at least one route is clear.
- `path_separation`: `appeal_only` if only appeal is viable, `parallel_appeal_and_assistance` if both tracks are open.

### Reimbursement Compliance (train_004)
**Per cell (clinic × quarter × payer × plan_type × service_category):**
- Aggregate `encounters` where `claim_status = 'paid'`. Exclude denied/unpaid encounters.
- `benchmark_amount` = sum over each encounter's units × applicable `rate_schedules.contracted_rate_per_unit`.
- `variance_amount` = `paid_amount` - `benchmark_amount` (negative = underpayment).
- `variance_pct` = `variance_amount / benchmark_amount`.
- `compliance_classification` = `material_underpayment` when ALL three materiality thresholds met:
  - `paid_units >= minimum_paid_units`
  - `abs(variance_amount) >= minimum_underpayment_amount`
  - `abs(variance_pct) >= minimum_underpayment_pct`
- Otherwise `compliant` (low-volume cells) or `high_review` (clinic-quarter aggregates with material underpayments).
- `rate_schedule_rate_ids`: collect all `rate_schedule_id` values that applied to encounters in that cell.

**Recovery Opportunities:**
- From `claim_corrections` with status in active_recovery_statuses (`open`, `pending documents`, `submitted`).
- `top_recovery_opportunity`: the single correction with the largest `expected_recovery_amount`.

### Outpatient Rehab Profitability (train_005)
**Per cell (clinic × plan_type × service_category):**
- `net_revenue` = sum of `paid_amount` + sum of `open_recovery` from claim_corrections.
- `total_cost` = `units` × `cost_per_unit` from `clinic_costs`.
- `net_margin` = `net_revenue - total_cost`.
- `margin_pct` = `net_margin / net_revenue` (can be negative; compute as decimal).
- `budget_variance_class`: `on_or_above_budget` if `margin_pct >= budget_margin_pct`; `major_shortfall` otherwise.
- `persistence_class`: `persistent` if the cell appears in multiple periods with shortfall; `noise` if single-period; `acceptable` if on/above budget.

**Payer actions:**
- `rate_floor_review` — renegotiate rates with payer.
- `recover_and_rate_floor_review` — pursue open corrections AND renegotiate.
- `projected_improvement_amount` = `(budget_margin_pct × total_cost) - net_margin` (the gap to close to reach budget).

**Ranked loss drivers:** Top 3 cells by most negative `net_margin`.

## Output Formatting Rules

### Numeric Precision
- **Dollar amounts**: round to 2 decimal places (`395362.70`, not `395362.7`).
- **Per-unit rates**: round to 2 decimal places.
- **Percentages**: express as **decimals** rounded to 4 decimal places (`-0.1594`, not `-15.94%`).
- **Counts**: integers, no decimals.

### Sorting
- Case-level rows: **ascending by case ID** (AUTH00001, AUTH00002, ...).
- Medication cases: **ascending by med_case_id** (MED00001, MED00002, ...).
- Ranked loss drivers: by descending loss severity (most negative margin first).

### Enumerated Values
- Every string field with constrained values must use **exactly** the enum value from the answer template's schema comment, not a free-text variation.
- `first_failing_check` must match: `active_coverage | cob_completion | covered_service | network | service_area | pa_required | retrospective_submission | duplicate_authorization | none`
- `intake_disposition` must match the template's enum set exactly.
- `review_queue`, `gold_card_decision`, etc. all constrained.

### Null vs Empty
- `approved_units`: use `null` (JSON null) when not applicable, not `0`.
- `duplicate_existing_auth_ids`: use `[]` when no duplicates, not `null`.
- `missing_evidence_keys`: use `[]` when none missing.

### Aggregation Counts
- `sla_summary` / `queue_counts` / `appeal_summary` / `assistance_summary` / `summary`: these are derived by counting across the case-level output rows. Ensure internal consistency — counts in the summary block must match the cases array.

## Common Pitfalls

1. **Gate order matters.** Don't check duplicate before COB — the gates have a defined sequence. First failure wins.
2. **COB hold is not a denial.** `notice_required: false` for COB holds. They are informational holds, not adverse determinations.
3. **Retrospective detection.** Compare `request_date` to `service_date`, not the current date. Retro = requested after service was already rendered.
4. **Duplicate matching scope.** Match on `member_id` + similar `cpt_code` (same code family) + overlapping service windows. Don't flag different members or entirely different procedures.
5. **SLA business-day calculation.** When `calendar_business = 'business'`, count only weekdays (Mon–Fri), skipping weekends. Calendar days include all days.
6. **Gold card only after all gates pass.** Gold card eligibility is assessed only for cases that clear intake gates 1–8. If any gate halts, gold_card_decision = `not_reached_intake_halt`.
7. **Multiple rate schedules per cell.** A payer-service-category cell may map to multiple `rate_schedule` rows (different CPTs, effective periods). Collect all applicable rate IDs.
8. **Exclude denied encounters from paid-rate analysis.** Only `claim_status = 'paid'` encounters contribute to paid/benchmark amounts. Denied encounters are counted separately as `excluded_denied_or_unpaid_encounters`.
9. **Materiality is AND, not OR.** A variance is only `material_underpayment` if it meets ALL three thresholds simultaneously (units, amount, percentage).
10. **Plan type drives government exclusion.** Medicaid and Medicare Advantage members are excluded from most manufacturer assistance programs. Check `plan_type` not just income.
11. **Expedited classification depends on both request AND grant.** `expedited_requested` alone is not enough — check whether `expedited_granted` is true for `expedited_accepted_72h`.
12. **net_revenue includes open recoveries.** In profitability tasks, `net_revenue = paid_amount + open_recovery`, not just paid_amount. Missing this inflates losses.
13. **cost_per_unit is per clinic × service_category.** It comes from `clinic_costs`, not computed from encounters. Don't divide total_cost by units — use the stored rate.

## Task-Type Quick Reference

| Task Type | Key Input | Primary Tables | Key Output |
|---|---|---|---|
| Auth Intake | worklist_memo.json (case IDs) | authorization_requests, members, plans, providers, facilities, service_code_rules, existing_authorizations, state_sla_rules | cases[] with first_failing_check, intake_disposition, SLA, provider items |
| Clinical Review | worklist.json (review_date) | authorization_requests, line_items, clinical_evidence, criteria_sources, prior_reviews | case_reviews[] with nurse_recommendation, missing_evidence_keys, p2p |
| Pharmacy Appeal | worklist.json (med_case_ids) | medication_requests, appeal_intake, medication_trial_history, drug_policies, assistance_programs, household_financials, members, plans | medication_cases[] with appeal{} and assistance{} blocks |
| Reimbursement Compliance | audit_scope.json (clinics, periods, materiality) | encounters, rate_schedules, claim_corrections | clinic_results[], flagged_variances[], top_recovery_opportunity |
| Outpatient Profitability | worklist_scope.json (clinics, plan_types, service_categories) | encounters, clinic_costs, clinic_budgets, claim_corrections | ranked_loss_drivers[], payer_actions[], portfolio_summary |

## Workflow Template

```
1. Read prompt.txt — understand role and deliverables
2. Read input/payloads/* — extract target scope (case IDs, clinics, dates, materiality)
3. Read input/payloads/answer_template.json — note every field, enum, and structure
4. SQL discovery: sqlite_master → PRAGMA table_info → DISTINCT spot-checks
5. Build queries: start with the target IDs from the worklist, LEFT JOIN outward
6. Validate: spot-check 1-2 rows against raw SQL output
7. Format output: match template exactly, sort, round, use correct enums
8. Verify internal consistency: summary counts match case array lengths
```
