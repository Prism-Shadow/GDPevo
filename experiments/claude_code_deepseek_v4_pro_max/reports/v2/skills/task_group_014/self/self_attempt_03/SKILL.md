# Payer Operations SQL Skill

## Overview

This skill covers payer-side operations tasks on a SQLite database exposed via a REST query endpoint. The five task domains are:

1. **Intake audit** — authorization case gate checks (coverage, COB, network, duplicate detection, gold-card, SLA)
2. **Clinical review** — nurse reviewer evaluation of clinical evidence against criteria sources
3. **Pharmacy appeal + assistance** — medication appeal routing and manufacturer assistance eligibility
4. **Reimbursement compliance** — paid-rate vs benchmark variance analysis with recovery tracking
5. **Outpatient rehab profitability** — payer-service P&L with budget comparison and action recommendations

---

## Connecting to the SQL Service

Every request uses HTTP Basic Auth. The endpoint is a `POST /query` with JSON body:

```json
{"sql": "<query>", "params": []}
```

The service returns `{"columns": [...], "row_count": N, "rows": [{...}]}`. All queries are read-only SELECT.

**Never** assume a local database file, a hardcoded host, or a port. The environment document always provides the base URL.

---

## Schema Discovery SOP

1. **List all tables first** — `SELECT name FROM sqlite_master WHERE type='table' ORDER BY name`
2. **Inspect each table** — `PRAGMA table_info(<table>)` to get column names and types
3. **Sample rows** — `SELECT * FROM <table> LIMIT 3` to understand value patterns and enum domains
4. **Check target data** — Filter by `target_bucket` for auth/med tasks; filter by `clinic_id`/date range for encounter tasks
5. **Verify join cardinality** — Run a join with COUNT to confirm 1:1 vs 1:N relationships before flattening results

### Key Discovery Queries

```sql
-- Find all enum values for a column
SELECT DISTINCT <col>, COUNT(*) FROM <table> GROUP BY <col> ORDER BY <col>;

-- Check which rows belong to your target bucket
SELECT target_bucket, COUNT(*) FROM authorization_requests GROUP BY target_bucket;
SELECT target_bucket, COUNT(*) FROM medication_cases GROUP BY target_bucket;

-- Verify join doesn't multiply rows
SELECT a.case_id, COUNT(*) FROM authorization_requests a
JOIN auth_lines l ON a.case_id = l.case_id
WHERE a.target_bucket = '...' GROUP BY a.case_id;
```

---

## Table Reference

### Core Authorization Tables

| Table | Purpose | Key columns |
|---|---|---|
| `authorization_requests` | Inbound PA requests | `case_id`, `member_id`, `request_date`, `receipt_timestamp`, `urgency_attested`, `requesting_npi`, `servicing_npi`, `facility_id`, `rendered_before_submission`, `oon_exception`, `cob_primary_processed`, `status`, `target_bucket` |
| `auth_lines` | Line items on a request | `case_id`, `line_no`, `cpt_code`, `modifier`, `units`, `service_category` |
| `existing_authorizations` | Prior auths already on file | `existing_auth_id`, `member_id`, `cpt_code`, `service_start`, `service_end`, `status`, `original_case_id` |

### Member / Plan / Provider / Facility

| Table | Key columns |
|---|---|
| `members` | `member_id`, `plan_id`, `residence_state`, `coverage_start`, `coverage_end`, `cob_primary_status`, `retro_reinstated_date` |
| `plans` | `plan_id`, `plan_type`, `plan_tier`, `network_type`, `state`, `routine_sla_days`, `urgent_sla_hours`, `stat_sla_hours`, `gold_card_allowed` |
| `providers` | `npi`, `specialty`, `network_status`, `sanctions_active`, `credentials_active`, `gold_card_active`, `approval_rate_12m` |
| `facilities` | `facility_id`, `state`, `in_service_area` |

### Service Rules

| Table | Key columns |
|---|---|
| `service_codes` | `code` (CPT/HCPCS), `service_category`, `pa_required`, `covered`, `notification_only`, `gold_card_exclusion`, `mandatory_md_review`, `external_vendor`, `specialty_program` |
| `state_sla_rules` | `state`, `plan_type_filter`, `routine_days`, `urgent_hours`, `stat_hours`, `day_type` (calendar vs business) |
| `coverage_criteria` | `service_category`, `criterion_key`, `criterion_label`, `required_value`, `criteria_source_id`, `is_required_for_approval` |
| `criteria_sources` | `source_id`, `source_name`, `precedence_rank`, `plan_type_filter`, `service_category_filter`, `effective_date` |

### Clinical / Evidence

| Table | Key columns |
|---|---|
| `clinical_facts` | `case_id`, `criterion_key`, `fact_value` (met/not_met/unclear), `confidence_flag` (clear/conflicting/partial/stale), `source_doc_id`, `source_rank` |
| `evidence_documents` | `doc_id`, `case_id`, `doc_type`, `doc_date`, `source_system`, `source_rank`, `is_current`, `summary` |
| `case_review_events` | `event_id`, `case_id`, `event_timestamp`, `stage`, `reviewer_role`, `event_type`, `outcome` |

### Medication / Appeal / Assistance

| Table | Key columns |
|---|---|
| `medication_cases` | `med_case_id`, `member_id`, `drug_name`, `diagnosis_code`, `request_date`, `payer_formulary_status`, `target_bucket` |
| `appeals` | `appeal_id`, `case_or_med_case_id`, `appeal_subject_type`, `adverse_notice_date`, `appeal_received_date`, `expedited_attestation`, `new_evidence_received`, `authorized_representative_on_file`, `original_decision_type`, `plan_type` |
| `drug_policy_requirements` | `drug_name`, `plan_type_filter`, `requirement_key`, `requirement_label`, `required_value`, `source_rank` |
| `medication_trials` | `trial_id`, `med_case_id`, `medication_name`, `drug_class`, `outcome`, `adverse_effect`, `documented` |
| `assistance_programs` | `program_id`, `drug_name`, `max_income_fpl`, `requires_commercial_insurance`, `excludes_government_plan`, `requires_denial`, `form_name` |
| `household_financials` | `member_id`, `household_size`, `annual_income`, `insurance_type`, `has_denial_letter`, `assistance_consent_on_file` |

### Finance / Encounters

| Table | Key columns |
|---|---|
| `encounters` | `encounter_id`, `clinic_id`, `service_date`, `payer`, `plan_type`, `cpt_code`, `service_category`, `units`, `billed_amount`, `paid_amount`, `denial_code`, `authorization_case_id` |
| `rate_schedules` | `rate_id`, `payer`, `plan_type`, `service_category`, `cpt_code`, `state`, `effective_start`, `effective_end`, `benchmark_rate`, `benchmark_source` |
| `claim_corrections` | `correction_id`, `encounter_id`, `correction_type`, `expected_recovery_amount`, `correction_deadline`, `status` |
| `clinic_budgets` | `budget_id`, `clinic_id`, `fiscal_year`, `payer`, `service_category`, `expected_units`, `expected_net_revenue`, `expected_margin_pct` |
| `clinic_costs` | `cost_id`, `clinic_id`, `fiscal_year`, `service_category`, `direct_cost_per_unit`, `allocated_overhead_per_unit` |

### Additional

| Table | Key columns |
|---|---|
| `p2p_sessions` | `p2p_id`, `case_id`, `scheduled_at`, `completed_at`, `requesting_provider_joined`, `new_information`, `outcome` |

---

## Common Join Patterns

### Authorization → Everything
```
authorization_requests
  ├─ members ON member_id
  ├─ plans ON members.plan_id
  ├─ providers (requesting) ON requesting_npi = providers.npi
  ├─ providers (servicing) ON servicing_npi = providers.npi
  ├─ facilities ON facility_id
  ├─ auth_lines ON case_id
  │    └─ service_codes ON auth_lines.cpt_code = service_codes.code
  ├─ existing_authorizations ON member_id (+ cpt_code + date overlap)
  ├─ clinical_facts ON case_id
  ├─ evidence_documents ON case_id
  └─ case_review_events ON case_id
```

### Medication → Everything
```
medication_cases
  ├─ members ON member_id
  ├─ plans ON members.plan_id
  ├─ appeals ON med_case_id = case_or_med_case_id
  ├─ medication_trials ON med_case_id
  ├─ drug_policy_requirements ON drug_name
  ├─ household_financials ON member_id
  └─ assistance_programs ON drug_name
```

### Encounter → Everything
```
encounters
  ├─ rate_schedules ON payer, plan_type, service_category, cpt_code, state
  │    (+ effective date range: encounter.service_date BETWEEN rate.effective_start AND rate.effective_end)
  ├─ claim_corrections ON encounter_id
  ├─ clinic_costs ON clinic_id, fiscal_year, service_category
  └─ clinic_budgets ON clinic_id, fiscal_year, payer, service_category
```

---

## Business Rules by Task Domain

### Task 1: Intake Audit (Checks Applied in Order)

The checks stop at the **first failure**. The chain is:

1. **Active coverage** — `coverage_start <= request_date <= coverage_end`. If `retro_reinstated_date` exists, coverage is re-activated from that date. COB check: if `cob_primary_processed = 0` at request time, it's a COB hold.
2. **Covered service** — Join `auth_lines.cpt_code → service_codes.code`. If `covered = 0`, it's a non-covered service. Each line's code must be checked.
3. **Network** — `providers.network_status = 'in_network'` for the requesting NPI. Check OON exception flag.
4. **Service area** — Facility `in_service_area = 1`. If the facility state differs from the member's residence state, check for out-of-area rules.
5. **PA required** — If `notification_only = 1`, close as notification only (not a full PA). If `pa_required = 0`, it doesn't need PA. Otherwise proceed.
6. **Retrospective submission** — `rendered_before_submission = 1` means service was already delivered. Check retro rules.
7. **Duplicate detection** — Same member, overlapping service dates, same CPT with an existing auth that has status `open` or `approved`. A duplicate should reference the `existing_auth_id`.
8. **Gold-card** — Requires ALL of: `plans.gold_card_allowed = 1`, `providers.gold_card_active = 1`, and `service_codes.gold_card_exclusion = 0`. If all true → auto-approve. If any false → move to review.

**SLA calculation**: Use `urgency_attested` (routine/urgent/stat). Source the timing from `plans` (plan-level SLA) or `state_sla_rules` (state-level, matched by `state` + `plan_type_filter`). For `stat`, use hours. For `routine`, use days. The SLA due timestamp = `receipt_timestamp + SLA_duration` (using the correct `day_type`: calendar or business days).

**Notice required**: Set to `true` whenever the disposition is a denial, halt, or requires member notification.

**Disposition mapping**:
- Coverage gap → `coverage_halt`
- COB not processed → `cob_hold`
- Non-covered service → `noncovered_service_denial`
- Out of network → `network_denial`
- Out of service area → `service_area_denial`
- Notification only → `notification_only_close`
- Retrospective → `retrospective_submission_halt`
- Duplicate → `duplicate_halt`
- Gold card eligible → `gold_card_auto_approval`
- Passed all checks → `ready_for_review`

**Review queue assignment**: Based on `service_codes.external_vendor` and `specialty_program`. If `external_vendor = 'MedImage Review'` → `MedImage Review`. If `external_vendor = 'CareEquip Review'` → `CareEquip Review`. If `external_vendor = 'HomeCare Review'` → `HomeCare Review`. If `mandatory_md_review = 1` → `Medical Director Review`. Otherwise → `Nurse Clinical Review`.

### Task 2: Clinical Review (Nurse Reviewer)

1. **Get service category** — From `auth_lines`, take the primary service category. If multiple lines, use the one from line 1, or the one requiring the highest scrutiny.
2. **Select criteria source** — Match `criteria_sources` by `plan_type_filter` (exact match or `ALL`) and `service_category_filter` (exact match or `ALL`), then pick the one with the **lowest `precedence_rank`** (1 = highest precedence, e.g., CMS/LCD beats internal policy).
3. **Evaluate coverage criteria** — For the selected `criteria_source_id`, find all `coverage_criteria` rows for the `service_category`. For each criterion, look up `clinical_facts` for that `case_id` + `criterion_key`. The fact's `fact_value` must match the criterion's `required_value` (usually `'met'`).
4. **Confidence assessment** — Check `confidence_flag` across all facts:
   - `clear` = strong evidence
   - `conflicting` = contradictory sources → needs MD escalation
   - `partial` = incomplete evidence → missing evidence key
   - `stale` = old evidence → may need updated documentation
5. **Nurse recommendation**: If all required criteria are `met` with `clear` or `partial` confidence and no `conflicting` → `approve_as_requested`. Otherwise flag for MD review.
6. **MD escalation**: Required when any `confidence_flag = 'conflicting'`, any required criterion is `not_met`, `mandatory_md_review = 1`, or the service is `experimental`.
7. **Missing evidence**: Any criterion where `fact_value != required_value` or where `confidence_flag IN ('partial', 'stale')` and the fact is outdated.
8. **P2P suitable**: The case has `requesting_provider_joined = 1` in `p2p_sessions` or has `new_information = 1`, indicating a peer-to-peer discussion could resolve outstanding questions.
9. **Approved units**: If approving, set to the lesser of requested units and what the evidence supports. Check `auth_lines.units` and `authorization_requests.requested_total_units`.

### Task 3: Pharmacy Appeal + Assistance

**Appeal routing:**

1. **Timeliness** — The appeal deadline is typically `adverse_notice_date + 60 days` (check per plan type). If `appeal_received_date <= deadline` → `timely_received`, else `late_received`.
2. **Eligibility status**:
   - `appeal_ready` — timely, has required documents
   - `appeal_incomplete` — missing policy requirements (from `drug_policy_requirements`)
   - `appeal_not_timely` — past filing deadline
3. **Missing policy requirements** — Compare `drug_policy_requirements` (for the drug, filtered by plan_type) against what's documented in `medication_trials` and the case facts. Common keys: `diagnosis`, `step_therapy`, `tb_screen`, `topical_failure`.
4. **Expedited** — If `expedited_attestation = 1` → `expedited_accepted_72h` (72-hour turnaround). If expedited requested but evidence missing → `expedited_requested_needs_evidence`. Otherwise → `standard_30d`.
5. **Filing deadline** — `adverse_notice_date + appeal_window_days` (often 60 days for standard, varies by plan).
6. **Next step** — Action-oriented: `"submit_to_clinical_review"`, `"request_missing_documents"`, `"close_as_untimely"`, etc.

**Manufacturer assistance routing:**

1. **Income check** — `annual_income / household_size` compared against FPL thresholds. The `max_income_fpl` field in `assistance_programs` is a percentage of FPL (e.g., 500 = 500% FPL). FPL 2024 baseline: ~$15,060 for individual, ~$20,440 for couple, etc. The income as % FPL = `annual_income / (FPL_for_household_size) * 100`. If this exceeds `max_income_fpl` → `income_over_program_limit`.
2. **Insurance type** — If `requires_commercial_insurance = 1` and `insurance_type != 'commercial'` → blocked. If `excludes_government_plan = 1` and `plan_type IN ('Medicare Advantage', 'Medicaid', 'Dual Eligible')` → `government_plan_excluded`.
3. **Denial letter** — If `requires_denial = 1` and `has_denial_letter = 0` → `denial_letter_missing`.
4. **Consent** — If `assistance_consent_on_file = 0` → `assistance_consent_missing`.
5. **Eligibility** — All checks pass → `assistance_eligible` with `program_owner = 'manufacturer_assistance_team'`, `form_name` from the program. Any block → `assistance_ineligible` with blocking reasons enumerated.

**Path separation** — Each case can be:
- `appeal_only` — appeal ready, not eligible for assistance
- `assistance_only` — assistance eligible, appeal not available/timely
- `parallel_appeal_and_assistance` — both tracks active
- `no_active_route` — neither track works

### Task 4: Reimbursement Compliance

1. **Filter encounters** — By `clinic_id`, `service_date` range, and exclude `denied/unpaid` encounters (those with `paid_amount = 0` AND a `denial_code IS NOT NULL` are excluded from paid analysis but tracked separately).
2. **Match rate schedules** — Join `encounters` to `rate_schedules` on `payer`, `plan_type`, `service_category`, `cpt_code`, and `state`, with `service_date BETWEEN effective_start AND effective_end`. If multiple rates apply (legacy vs current), use the one whose effective range covers the service date. If `benchmark_source = 'future draft'`, exclude it (not yet in effect).
3. **Compute variance** — `benchmark_amount = benchmark_rate * units`. `variance_amount = benchmark_amount - paid_amount` (positive = underpayment). `variance_pct = variance_amount / benchmark_amount`.
4. **Materiality filter** — Flag a cell when ALL of: `paid_units >= minimum_paid_units`, `variance_amount >= minimum_underpayment_amount`, `variance_pct >= minimum_underpayment_pct` (as a decimal, e.g., 0.1 = 10%).
5. **Tracked recovery** — Sum `claim_corrections.expected_recovery_amount` where `status IN ('open', 'pending documents', 'submitted')` for encounters in the analysis scope.
6. **Compliance classification** — `material_underpayment` for cells meeting materiality thresholds; `compliant` otherwise.
7. **Top recovery opportunity** — Single largest `expected_recovery_amount` from an open active correction in the scope. Join back to the encounter for service_date, CPT, payer, plan_type, etc.

### Task 5: Outpatient Rehab Profitability

1. **Revenue** — `SUM(encounters.paid_amount)` grouped by `(clinic_id, plan_type, service_category)` for the analysis period.
2. **Open recovery** — `SUM(claim_corrections.expected_recovery_amount)` for active corrections (`status IN ('open', 'pending documents', 'submitted')`) on encounters in scope.
3. **Costs** — Join `clinic_costs` on `clinic_id`, `fiscal_year`, `service_category`. `cost_per_unit = direct_cost_per_unit + allocated_overhead_per_unit`. `total_cost = cost_per_unit * SUM(units)`.
4. **Net revenue** — `net_revenue = paid_amount + open_recovery - total_cost`. (Alternatively, `net_revenue = paid_amount - total_cost` with recovery tracked separately — follow the template definition.)
5. **Margin** — `net_margin = (paid_amount + open_recovery) - total_cost`. `margin_pct = net_margin / (paid_amount + open_recovery)`.
6. **Budget comparison** — From `clinic_budgets`: `expected_margin_pct`. Classify variance:
   - `major_shortfall` — margin_pct is significantly below budget (e.g., negative or below some threshold like budget * 0.5)
   - `minor_shortfall` — below budget but not severely
   - `on_target` — meets or exceeds budget
7. **Persistence** — If a cell has been underperforming across multiple periods → `persistent`; otherwise `current_period_only` or similar.
8. **Recommended actions** — Based on the root cause:
   - Low paid rates → `rate_floor_review` (contract renegotiation)
   - High denials → `denial_root_cause_review`
   - Low volume → `referral_partnership_review`
   - High costs → `cost_reduction_initiative`
9. **Ranked loss drivers** — Top 3 cells by largest negative `net_margin`, ranked 1-3.

---

## Output Conventions

### Always
- **Sort order**: Cases in ascending `case_id` or `med_case_id` order unless the template specifies otherwise
- **JSON only**: Return exactly one JSON object matching the answer template shape — no explanatory text outside the JSON
- **Empty arrays**: Use `[]`, not `null`, for missing items in array fields

### Numbers & Formatting
- **Money**: Round to 2 decimal places (`ROUND(val, 2)`)
- **Percentages**: As decimals rounded to 4 places (0.1234 = 12.34%)
- **Counts**: Integers, no decimals
- **Dates/times**: ISO 8601 format (`YYYY-MM-DD` or `YYYY-MM-DDTHH:MM`)
- **SLA timestamps**: Include time component when hours matter (`YYYY-MM-DDTHH:MM`)

### Enum Values
- Use the **exact string** from the template — no synonyms or abbreviations
- `plan_type`: One of `Commercial`, `Medicare Advantage`, `Medicaid`, `Exchange`, `Dual Eligible`
- `urgency_class`: `routine`, `urgent`, `stat`
- `review_queue`: Exact names from the template (`Nurse Clinical Review`, `Medical Director Review`, etc.)
- `nurse_recommendation`: `approve_as_requested` or specific denial/carve-out codes
- `compliance_classification`: `compliant` or `material_underpayment`

### Null Handling
- Use SQL `COALESCE` liberally: `COALESCE(SUM(x), 0)` to avoid null aggregates
- Boolean template fields (`true`/`false`): never null — default to `false`
- String fields: use `""` when there is no value (not `null`) unless the template expects `null`

---

## Common Pitfalls

### SQL Pitfalls
1. **One-to-many join explosion**: Always check if `auth_lines` has multiple rows per case before joining — if the template expects one row per case, either aggregate the lines or use `GROUP BY case_id`.
2. **Date overlap logic**: When checking for duplicate authorizations, the overlap condition is `existing.service_start <= new.service_end AND existing.service_end >= new.service_start`. Don't just compare start or end dates in isolation.
3. **Rate schedule effective dates**: A service on `2025-03-15` matches a rate where `effective_start <= '2025-03-15' AND effective_end >= '2025-03-15'`. If multiple rates match (legacy + current), prefer `benchmark_source = 'current contract'` over `'legacy contract'`. Exclude `'future draft'`.
4. **plan_type_filter = 'ALL'**: In `criteria_sources`, `coverage_criteria`, `drug_policy_requirements`, and `state_sla_rules`, the filter `'ALL'` means "applies to all plan types" — but a more specific match (exact plan_type) should take precedence.
5. **SLA day_type**: `calendar` days include weekends/holidays; `business` days exclude them. When computing SLA deadlines, check `day_type` to decide whether to count calendar days or business days.
6. **NULL vs 0 in integer flags**: Fields like `cob_primary_processed`, `gold_card_allowed` are INTEGER (0/1) but may contain NULL. Treat NULL as 0 (not processed / not allowed).

### Business Logic Pitfalls
1. **Intake check ordering matters**: The checks are sequential — stop at the **first failure**. If coverage is lapsed, don't evaluate network status or gold card.
2. **Gold-card eligibility is ALL-OR-NOTHING**: Plan must allow it, provider must be active, AND the service must not be excluded. Any one missing → gold card does not apply.
3. **Duplicate detection scope**: Check for duplicates at the **member** level (same member_id), not the case level. Different members don't constitute duplicates even if the service is identical.
4. **Notification-only services**: If `service_codes.notification_only = 1`, the case should be closed as `notification_only_close`, not routed to clinical review. Don't apply gold-card logic to notification-only services.
5. **Expedited appeal ≠ automatic**: Having `expedited_attestation = 1` classifies the case as expedited, but it still requires evidence completeness. An expedited case missing documents is `expedited_requested_needs_evidence`, not `expedited_accepted_72h`.
6. **Assistance income threshold**: `max_income_fpl` is a **percentage** of FPL (e.g., 400 = 400% FPL). Compute the household's income as a percentage of FPL for that household size, then compare. FPL base for 2024: individual ~$15,060. Rough formula: `annual_income / (15060 + (household_size-1)*5380) * 100 <= max_income_fpl`.
7. **Recovery amounts are additive**: Open recovery from `claim_corrections` is added to paid revenue when assessing net position. Don't double-count closed/unrecovered corrections.
8. **Paid-rate benchmark sources**: The `benchmark_source` field indicates contract status. Only use rates that are actually in effect during the service date. `'future draft'` rates should be excluded from current-period analysis.

### Template Pitfalls
1. **Don't invent field names**: The answer template JSON is the schema contract. Every key must appear with the exact name and type from the template. Don't add extra fields.
2. **Array of strings vs single string**: Fields like `duplicate_existing_auth_ids` and `missing_evidence_keys` are arrays. Even when empty, use `[]`.
3. **Summary counts must be internally consistent**: If a summary says `auto_approved_count: 2`, there must be exactly 2 cases with `gold_card_decision: "auto_approve"` in the case array.
4. **Case-level arrays must match the case count**: Every case in the target list must appear in the output array. Don't skip cases, even if they error — represent their status accurately.

---

## Task Execution SOP

### Before Any Query
1. Read the `input/payloads/*.json` files thoroughly — they contain the target case IDs, date ranges, filter criteria, and materiality thresholds
2. Read the `input/payloads/answer_template.json` — it defines every output field and its type
3. Inspect the complete schema: `PRAGMA table_info(...)` on every relevant table
4. Sample a few rows from each table to see actual values, not just column types

### During Analysis
1. Start with narrow queries scoped to the target cases/dates — verify you get the right rows before building complex joins
2. For each business rule check, write a focused query, validate results, then move to the next check
3. When computing derived values (SLA timestamps, variance amounts, FPL percentages), test the formula on one case first
4. Use subqueries or CTEs for multi-step logic rather than trying to cram everything into one massive JOIN

### Before Submitting
1. Verify row counts: the output array length must equal the input target case count
2. Verify summary counts sum correctly (manually cross-check against the case rows)
3. Verify sort order (ascending case ID for case-level arrays)
4. Verify numeric formatting: money to 2 decimals, percentages to 4 decimals
5. Verify no field is missing from the template — every key must be present
