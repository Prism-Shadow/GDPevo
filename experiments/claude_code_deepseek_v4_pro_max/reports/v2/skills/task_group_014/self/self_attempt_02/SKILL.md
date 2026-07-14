# Payer Operations SQL Skill

## Overview

This skill covers five payer-operations task patterns served through a remote SQLite query endpoint. Every task follows the same HTTP contract: POST read-only SQL to `<BASE_URL>/query` with Basic Auth (`payer_ops_solver` / `revcycle_sql_014`) and JSON body `{"sql": "...", "params": []}`. The response is `{"columns": [...], "row_count": N, "rows": [{...}]}`. **Never assume a local database file** — all SQL flows through the service.

The domain is a single-payer (Ticonderoga Health) operations platform spanning utilization management authorization intake, clinical nurse review, pharmacy appeals, clinic reimbursement compliance, and outpatient rehab profitability.

---

## Schema Discovery Habit

Always start every task with:
```sql
SELECT name FROM sqlite_master WHERE type='table' ORDER BY name
```
Then pull CREATE TABLE DDL for tables relevant to the task:
```sql
SELECT sql FROM sqlite_master WHERE type='table' AND name='<table>'
```
Use `DISTINCT` on enum-like columns to discover allowed values before writing business logic. Example: `SELECT DISTINCT plan_type FROM plans` yields Commercial, Medicare Advantage, Medicaid, Exchange, Dual Eligible.

---

## Table Reference

### Core UM Tables
- **authorization_requests** — one row per prior-auth case. Key columns: `case_id` (PK), `member_id`, `request_date`, `receipt_timestamp`, `urgency_attested` (routine/urgent/stat), `submission_channel` (edi/fax/phone/portal), `place_of_service`, `requesting_npi`, `servicing_npi`, `facility_id`, `primary_icd10`, `rendered_before_submission` (0/1), `oon_exception` (0/1), `cob_primary_processed` (0/1), `requested_total_units`, `estimated_total_allowed`, `status`, `current_stage`, `target_bucket`.
- **auth_lines** — line items per case: `case_id`, `line_no`, `cpt_code`, `modifier`, `units`, `service_category`.
- **existing_authorizations** — prior auths for duplicate detection: `existing_auth_id`, `member_id`, `cpt_code`, `service_start`, `service_end`, `status` (open/approved/denied/expired), `original_case_id`.
- **case_review_events** — audit trail: `event_id`, `case_id`, `event_timestamp`, `stage` (intake/clinical_review), `reviewer_role` (intake_coordinator/nurse/medical_director), `event_type` (received/clinical_screen), `outcome` (queued/approve/escalate_to_md/adverse_pending/request_more_info).

### Party Tables
- **members** — `member_id` (PK), `plan_id`, `residence_state`, `coverage_start`, `coverage_end`, `retro_reinstated_date` (nullable), `cob_primary_status` (processed/pending).
- **plans** — `plan_id` (PK), `plan_type` (Commercial/Medicare Advantage/Medicaid/Exchange/Dual Eligible), `plan_tier`, `network_type`, `state`, `routine_sla_days`, `urgent_sla_hours`, `stat_sla_hours`, `formulary_type`, `gold_card_allowed` (0/1).
- **providers** — `npi` (PK), `provider_name`, `specialty`, `state`, `network_status` (in_network/out_of_network), `approval_rate_12m`, `sanctions_active` (0/1), `credentials_active` (0/1), `gold_card_active` (0/1).
- **facilities** — `facility_id` (PK), `facility_name`, `state`, `in_service_area` (0/1).

### Clinical & Criteria Tables
- **service_codes** — `code` (PK, CPT/HCPCS), `description`, `service_category`, `pa_required` (0/1), `covered` (0/1), `notification_only` (0/1), `gold_card_exclusion` (0/1), `delegated_program`, `external_vendor`, `specialty_program`, `mandatory_md_review` (0/1), `estimated_allowed_amount`.
- **criteria_sources** — `source_id` (PK, SRC001–SRC005), `source_name`, `precedence_rank` (1=highest), `plan_type_filter` (ALL/Medicaid/Medicare Advantage), `service_category_filter` (ALL or specific).
- **coverage_criteria** — `service_category`, `criterion_key`, `criterion_label`, `required_value`, `criteria_source_id`, `plan_type_filter`, `is_required_for_approval`.
- **clinical_facts** — `case_id`, `criterion_key`, `fact_value` (met/not_met/unclear), `fact_date`, `source_doc_id`, `source_rank`, `confidence_flag` (clear/conflicting/partial/stale).
- **evidence_documents** — `doc_id`, `case_id`, `doc_type`, `doc_date`, `source_system`, `source_rank`, `is_current` (0/1), `title`, `summary`.

### Pharmacy Tables
- **medication_cases** — `med_case_id` (PK), `member_id`, `drug_name`, `diagnosis_code`, `requested_dose`, `request_date`, `payer_formulary_status` (preferred/non_preferred/excluded_pending_exception), `prescriber_npi`, `target_bucket`.
- **appeals** — `appeal_id` (PK), `case_or_med_case_id`, `appeal_subject_type` (authorization/medication), `adverse_notice_date`, `appeal_received_date`, `expedited_attestation` (0/1), `new_evidence_received` (0/1), `authorized_representative_on_file` (0/1), `original_decision_type`, `plan_type`, `target_bucket`.
- **drug_policy_requirements** — `drug_name`, `plan_type_filter` (always "ALL" in train data), `requirement_key`, `requirement_label`, `required_value`, `source_rank`.
- **medication_trials** — `trial_id`, `med_case_id`, `medication_name`, `drug_class`, `start_date`, `end_date`, `outcome` (failed/partial response), `adverse_effect`, `documented` (0/1).
- **assistance_programs** — `program_id` (PK, AP001–AP005), `drug_name`, `max_income_fpl`, `requires_commercial_insurance` (0/1), `excludes_government_plan` (0/1), `requires_denial` (0/1), `form_name`.
- **household_financials** — `member_id` (PK), `household_size`, `annual_income`, `insurance_type` (commercial/government), `has_denial_letter` (0/1), `assistance_consent_on_file` (0/1).

### Financial Tables
- **encounters** — `encounter_id` (PK), `clinic_id`, `service_date`, `payer`, `plan_type`, `member_id`, `cpt_code`, `service_category`, `units`, `billed_amount`, `paid_amount`, `denial_code` (nullable), `authorization_case_id` (nullable).
- **rate_schedules** — `rate_id` (PK), `payer`, `plan_type`, `service_category`, `cpt_code`, `state`, `effective_start`, `effective_end`, `benchmark_rate`, `benchmark_source` (legacy contract/current contract/future draft).
- **claim_corrections** — `correction_id` (PK), `encounter_id`, `correction_type`, `expected_recovery_amount`, `correction_deadline`, `status` (open/pending documents/submitted/closed unrecovered).
- **clinic_costs** — `cost_id` (PK), `clinic_id`, `fiscal_year`, `service_category`, `direct_cost_per_unit`, `allocated_overhead_per_unit`.
- **clinic_budgets** — `budget_id` (PK), `clinic_id`, `fiscal_year`, `payer`, `service_category`, `expected_units`, `expected_net_revenue`, `expected_margin_pct`.
- **state_sla_rules** — `state`, `plan_type_filter`, `routine_days`, `urgent_hours`, `stat_hours`, `day_type` (calendar/business), `notes`.

---

## Task Pattern 1: Authorization Intake Audit

**Trigger:** Prompt mentions "intake audit," "authorization exception batch," or `worklist_memo.json`.

### Workflow
1. Read `input/payloads/worklist_memo.json` to get `target_case_ids`.
2. Pull target cases from `authorization_requests` WHERE `case_id IN (...)`.
3. For each case, run checks in this exact order (first failing check stops the cascade):

| # | Check | SQL Join / Condition | Failure Enum |
|---|-------|---------------------|--------------|
| 1 | Active coverage | `members.coverage_start <= today AND members.coverage_end >= today`; also check `retro_reinstated_date` if non-null | `active_coverage` |
| 2 | COB completion | `authorization_requests.cob_primary_processed = 1` | `cob_completion` |
| 3 | Covered service | Join `auth_lines` → `service_codes`; `covered = 1` on at least one line | `covered_service` |
| 4 | Network | `providers.network_status = 'in_network'` for both requesting and servicing NPI | `network` |
| 5 | Service area | Facility `in_service_area = 1` AND facility state matches member plan state (or residence state) | `service_area` |
| 6 | PA required | `service_codes.pa_required = 1`; if `notification_only = 1` → skip to `notification_only_close` | `pa_required` |
| 7 | Retrospective | `rendered_before_submission = 0` — if 1, halt | `retrospective_submission` |
| 8 | Duplicate | `existing_authorizations` same member_id, same CPT, overlapping date ranges, status IN ('open','approved') | `duplicate_authorization` |
| 9 | Gold card | All three must be 1: `plans.gold_card_allowed`, `providers.gold_card_active`, `service_codes.gold_card_exclusion = 0` | `none` (pass = gold card) |

### Disposition Mapping
- `coverage_halt` ← check 1 fails
- `cob_hold` ← check 2 fails
- `noncovered_service_denial` ← check 3 fails
- `network_denial` ← check 4 fails
- `service_area_denial` ← check 5 fails
- `notification_only_close` ← check 6 finds notification-only service
- `retrospective_submission_halt` ← check 7 fails
- `duplicate_halt` ← check 8 finds a duplicate
- `gold_card_auto_approval` ← check 9 passes (all three conditions met)
- `ready_for_review` ← all checks pass but gold card not eligible

### SLA Computation
- Determine SLA state: use the **plan's state** (from `plans.state`), not the member's residence state.
- Match `state_sla_rules` on state + `plan_type_filter` = plan's `plan_type`. If no exact match, fall back to the plan's own SLA fields (`routine_sla_days`, `urgent_sla_hours`, `stat_sla_hours`).
- SLA due = `receipt_timestamp` + SLA period. Use `day_type` to determine calendar vs business days.
- `sla_basis` should be a human-readable string like `"CA Commercial: 5 calendar days"`.

### Urgency
- Use `urgency_attested` directly: routine → `routine`, urgent → `urgent`, stat → `stat`.

### Provider Item
- Check `providers.sanctions_active = 1` → `requesting_provider_active_sanction`
- Check `providers.credentials_active = 0` → `requesting_provider_credentials_inactive`
- Otherwise `none`

### Notice Required
- TRUE if disposition is a denial/halt (noncovered_service_denial, network_denial, service_area_denial, retrospective_submission_halt) or if MD review is required downstream.

### Duplicate Handling
- When duplicate found, `duplicate_existing_auth_ids` lists the `existing_auth_id` values of matching duplicates.
- `gold_card_decision` = `not_reached_intake_halt` if any check before gold card fails.

---

## Task Pattern 2: Clinical Nurse Review

**Trigger:** Prompt mentions "nurse reviewer," "clinical review slate," or a `review_date` field.

### Workflow
1. Read `worklist.json` for the review date and case ID source bucket.
2. Pull target cases from `authorization_requests` WHERE `target_bucket = '<bucket>'`.
3. For each case, join `auth_lines` → `service_codes` to get `service_category`.
4. Determine the applicable **criteria source**:
   - Match `criteria_sources` on `plan_type_filter`: exact match on member's plan type wins, then "ALL".
   - Among matching sources, pick the one with **lowest `precedence_rank`** (1 is highest priority).
   - For Medicare Advantage plans, `SRC001` (CMS NCD/LCD) is rank 1 and may add extra criteria.
5. Pull `coverage_criteria` WHERE `criteria_source_id = <selected>` AND `service_category = <case service category>` AND `plan_type_filter` matches the plan type or "ALL".
6. Pull `clinical_facts` for the case. Evaluate each criterion:
   - If `fact_value = 'met'` → criterion satisfied.
   - If `fact_value = 'not_met'` or `'unclear'` → criterion NOT satisfied → goes to `missing_evidence_keys`.
   - Pay attention to `confidence_flag`: `conflicting` or `stale` may indicate unreliable evidence.
7. Also check `service_codes.mandatory_md_review` — if 1, escalate regardless of criteria.

### Nurse Recommendation
- **`approve_as_requested`** if all required criteria are met AND no mandatory MD review flag AND evidence confidence is solid (no conflicting flags on required criteria).
- Otherwise determine appropriate denial/partial-approval posture (the template only shows `approve_as_requested` in the example but the logic supports other recommendations).

### MD Escalation
- `md_escalation_required = true` when: any required criterion not met, OR `mandatory_md_review = 1`, OR conflicting clinical evidence.
- `md_escalation_reason_code`: the first failing criterion key, or `"mandatory_md_review"`, or `"conflicting_evidence"`.

### Missing Evidence Keys
- List of `criterion_key` values where `fact_value != 'met'` or the fact is missing entirely.

### P2P Suitability
- `p2p_suitable = true` for cases that are "close calls" — evidence exists but is partial/stale/conflicting. Not suitable for clear-cut denials or clear-cut approvals.
- Check `p2p_sessions` — if a P2P was already attempted and failed, `p2p_suitable` may be false.

### Approved Units
- When recommending `approve_as_requested`, use `authorization_requests.requested_total_units`.

### Queue Counts
- Aggregate `md_escalations_by_service_category` as a map keyed by service category name.
- `nurse_approval_count` = count of `approve_as_requested` recommendations.
- `p2p_suitable_count` = count of P2P-suitable cases.

### Criteria Source Selection Detail
- `criteria_source_id` in the output is the source actually used (the one with lowest precedence_rank matching the plan type).
- For a Commercial plan: SRC003 (Ticonderoga Medical Policy, rank 2) is typically the best match since SRC001 is Medicare Advantage-only and SRC002 is Medicaid-only. SRC004 (InterQual, rank 3) and SRC005 (MCG, rank 4) are lower-precedence fallbacks.
- For Medicare Advantage: SRC001 (rank 1) adds `cms_specific_indication` criterion on top of the ALL criteria.

---

## Task Pattern 3: Pharmacy Appeal & Manufacturer Assistance

**Trigger:** Prompt mentions "pharmacy appeal," "medication appeal," "manufacturer assistance."

### Workflow
1. Read `worklist.json` for `medication_case_ids`.
2. Pull `medication_cases` for those IDs.
3. For each med case, join → `members` → `plans` to get `plan_type` for the member.
4. Join → `appeals` WHERE `case_or_med_case_id = med_case_id` AND `appeal_subject_type = 'medication'`. If no appeal record exists, eligibility is `appeal_not_timely`.
5. Join → `drug_policy_requirements` WHERE `drug_name = <med case drug>`.
6. Join → `medication_trials` WHERE `med_case_id = <id>` to evaluate step therapy.
7. Join → `assistance_programs` WHERE `drug_name = <drug>`.
8. Join → `household_financials` WHERE `member_id = <member>`.

### Appeal Routing Logic

**Eligibility:**
- `appeal_ready` — appeal record exists, all policy requirements met (trials documented, diagnosis covered), timely filed.
- `appeal_incomplete` — appeal record exists but some policy requirements not met or evidence missing.
- `appeal_not_timely` — no appeal record found for this med case.

**Filing Deadline:** `adverse_notice_date` + 60 days for standard, or based on plan rules.

**Deadline Status:** `timely_received` if `appeal_received_date <= filing_deadline`, else `late_received`.

**Expedited Classification:**
- `expedited_accepted_72h` — `expedited_attestation = 1`, enough evidence exists.
- `expedited_requested_needs_evidence` — attestation present but evidence incomplete.
- `standard_30d` — no expedited attestation.

**Missing Policy Requirements:**
- Map `drug_policy_requirements.requirement_key` values not satisfied by trials/facts:
  - `diagnosis` — check ICD10 against covered indications
  - `step_therapy` — check medication_trials for required drug classes
  - `tb_screen` — specific to Remicade
  - `topical_failure` — specific to Dupixent

### Manufacturer Assistance Routing Logic

**Eligibility Checks (all must pass for `assistance_eligible`):**
1. **Income:** `annual_income / household_size` ≤ FPL threshold for that household size. Use 2025 FPL = $15,060 for household of 1, +$5,380 per additional person. Compare to `max_income_fpl` × relevant FPL.
   - Formula: `(annual_income / (15060 + (household_size - 1) * 5380)) * 100 <= max_income_fpl`
2. **Commercial insurance:** If `requires_commercial_insurance = 1`, `household_financials.insurance_type = 'commercial'`.
3. **Government exclusion:** If `excludes_government_plan = 1`, plan must NOT be Medicare Advantage, Medicaid, or Dual Eligible.
4. **Denial letter:** If `requires_denial = 1`, `has_denial_letter = 1`.
5. **Consent:** `assistance_consent_on_file = 1`.

**Blocking reasons** are the specific checks that failed. Multiple can apply.

**Program owner:** `manufacturer_assistance_team` if eligible, else `not_routed`.

### Path Separation
- `appeal_only` — appeal ready but assistance ineligible.
- `assistance_only` — assistance eligible but no valid appeal.
- `parallel_appeal_and_assistance` — both routes are viable.
- `no_active_route` — neither route viable.

---

## Task Pattern 4: Reimbursement Compliance Audit

**Trigger:** Prompt mentions "reimbursement compliance," "clinic reimbursement," "paid-rate compliance," or `audit_scope.json`.

### Workflow
1. Read `audit_scope.json` for clinics, periods (quarters with start/end dates), and materiality thresholds.
2. Pull `encounters` WHERE `clinic_id IN (...)` AND `service_date BETWEEN start AND end`.
3. For each encounter, find the applicable benchmark rate from `rate_schedules`:
   - Match on `payer`, `plan_type`, `service_category`, `cpt_code`, `state` (clinic state from scope).
   - Pick the rate whose `effective_start <= service_date <= effective_end`.
   - Prefer `benchmark_source = 'current contract'` over `'legacy contract'`.
   - If multiple rates match, use the one with `effective_start` closest to `service_date` without exceeding it.
4. Compute per-encounter: `benchmark_amount = units × benchmark_rate`.
5. Compute `variance_amount = benchmark_amount - paid_amount` (positive = underpayment).
6. Compute `variance_pct = variance_amount / benchmark_amount`.

### Materiality
Apply thresholds from `audit_scope.materiality`:
- `minimum_paid_units`: only consider encounters with `units >= threshold`.
- `minimum_underpayment_amount`: only flag if `variance_amount >= threshold`.
- `minimum_underpayment_pct`: only flag if `variance_pct >= threshold`.
All three must be met for a cell to be `material_underpayment`.

### Clinic-Quarter Results
Aggregate per (clinic, quarter):
- `paid_encounters` — count of encounters with paid_amount > 0 (exclude $0 paid/denied).
- `paid_units` — sum of units.
- `paid_amount` — sum of paid_amount.
- `benchmark_amount` — sum of benchmark amounts.
- `variance_amount` — benchmark - paid.
- `variance_pct` — variance / benchmark.
- `excluded_denied_or_unpaid_encounters` — count of $0 paid encounters.
- `tracked_recovery_amount` — sum of `expected_recovery_amount` from `claim_corrections` WHERE status IN the `active_recovery_statuses` list from scope.
- `material_underpayment_cells` — count of (payer, plan_type, service_category) cells meeting all three materiality thresholds.
- `compliance_classification` — `"compliant"` if no material underpayment cells, else something like `"material_underpayment"` or `"flagged"`.

### Flagged Variances
For each (quarter, clinic, payer, plan_type, service_category) cell that exceeds materiality thresholds:
- `paid_per_unit` = paid_amount / units.
- `benchmark_per_unit` = benchmark_amount / units.
- Include `rate_schedule_rate_ids` — list of `rate_id` values used for this cell.

### Top Recovery Opportunity
- From `claim_corrections` joined to `encounters`, pick the single correction with:
  - Highest `expected_recovery_amount`
  - Status in `active_recovery_statuses`
  - Within the period/clinic scope
- Include full encounter and correction details.

---

## Task Pattern 5: Outpatient Rehab Profitability

**Trigger:** Prompt mentions "profitability action list," "outpatient rehab," "payer-service cells," "loss drivers."

### Workflow
1. Read `worklist_scope.json` for clinics, plan_types, service_categories, and analysis period.
2. Pull `encounters` WHERE clinic, plan_type, service_category in scope AND `service_date` in period.
3. Pull `clinic_costs` WHERE `fiscal_year = <period fiscal year>` AND clinic + service_category match.
4. Pull `clinic_budgets` WHERE `fiscal_year = <period fiscal year>` AND clinic + payer + service_category match.
5. Pull `claim_corrections` for open recoveries related to these encounters.

### Per-Cell Computations
For each (clinic, plan_type, service_category) combination:
- `encounter_count` — count of encounters.
- `units` — sum of units.
- `paid_amount` — sum of paid_amount.
- `open_recovery` — sum of `expected_recovery_amount` from corrections with status = 'open' (join via encounter_id).
- `net_revenue` = paid_amount + open_recovery.
- `cost_per_unit` = `direct_cost_per_unit + allocated_overhead_per_unit` from clinic_costs.
- `total_cost` = units × cost_per_unit.
- `net_margin` = net_revenue - total_cost.
- `margin_pct` = net_margin / net_revenue (guard against division by zero; if net_revenue = 0, margin_pct = 0 or null).
- `budget_margin_pct` — from clinic_budgets (match on clinic, fiscal_year, payer, service_category).
- `budget_variance_class`:
  - `"major_shortfall"` — margin_pct is well below budget (e.g., difference > 0.10 or margin negative).
  - `"minor_shortfall"` — below budget but within a smaller band.
  - `"on_budget"` — near budget target.
  - `"above_budget"` — exceeding budget.

### Persistence Classification
Determine by whether the same cell shows losses across multiple years/quarters or is a one-time event. With only one year of data: check if the pattern exists historically (via fiscal_year in clinic_costs/budgets). If the same clinic-service combo has high costs in prior years, it's `"persistent"`.

### Ranked Loss Drivers
Sort cells by `net_margin` ascending (most negative first). Take top 3. Output rank, clinic, plan_type, service_category, net_margin, margin_pct.

### Payer Actions
For each flagged cell:
- `recommended_action` — `"rate_floor_review"` if margin negative and paid rates look low; `"cost_reduction_review"` if cost_per_unit is the driver; `"volume_negotiation"` if volume is high but rates are thin.
- `projected_improvement_amount` — gap to budget: `(budget_margin_pct - margin_pct) × net_revenue` (positive number; if already above budget, 0).

### Portfolio Summary
- `cells_analyzed` — count of distinct (clinic, plan_type, service_category) combos.
- `flagged_pair_count` — count where budget_variance_class is major_shortfall.
- Aggregate totals for net_revenue, cost, net_margin, open_recovery, projected_improvement.
- `payer_service_results` — one row per cell with all computed fields.

---

## Common Pitfalls

### Joins & Cardinality
- **auth_lines:authorization_requests is 1:N** — use aggregation (GROUP BY case_id) or pick relevant lines; otherwise cases multiply.
- **clinical_facts:authorization_requests is N:1** — multiple facts per case. Use aggregation or pivot.
- **claim_corrections:encounters is 1:1 in theory** — but verify. A LEFT JOIN is safer than assuming one correction per encounter.
- **encounters may have NULL denial_code and NULL authorization_case_id** — always use IS NULL / IS NOT NULL, never `= NULL`.

### Rate Schedule Matching
- Rate schedules have effective date ranges. A service on 2025-03-15 must match `effective_start <= '2025-03-15' <= effective_end`.
- Multiple benchmark_sources exist (legacy contract, current contract, future draft). Prefer `'current contract'` for services within its effective range. Never use `'future draft'` for historical services.
- Match on all dimensions: payer, plan_type, service_category, cpt_code, state.
- If no match on state + cpt_code, try matching on service_category alone as a fallback.

### SLA State Selection
- Use the **plan's state** (`plans.state`), not the member's residence state and not the facility state, for SLA lookups.
- `state_sla_rules` uses `plan_type_filter` which can be more specific than plan_type. For a Dual Eligible plan, match the Dual Eligible rule if it exists, otherwise fall back.
- Remember `day_type`: "business" days means skip weekends/holidays; "calendar" means straight addition.

### Coverage Periods
- Coverage is active when `coverage_start <= reference_date AND coverage_end >= reference_date`.
- `retro_reinstated_date` being non-null may indicate a gap was bridged — check it.
- `cob_primary_status = 'pending'` means coordination of benefits isn't resolved → halt.

### Gold Card Logic
- All three conditions must be simultaneously true:
  1. Plan allows gold card (`plans.gold_card_allowed = 1`)
  2. Provider is gold card active (`providers.gold_card_active = 1`)
  3. Service is not excluded (`service_codes.gold_card_exclusion = 0`)
- Gold card only evaluated after all previous intake checks pass.

### Duplicate Detection
- A duplicate exists when `existing_authorizations` has a row with:
  - Same `member_id`
  - Same `cpt_code` (or overlapping service from auth_lines)
  - Date overlap: `existing.service_start <= request.service_end AND existing.service_end >= request.service_start`
  - Status IN ('open', 'approved')
- List ALL matching `existing_auth_id` values, not just the first.

### P2P & MD Escalation
- P2P is for borderline cases — not for clear denials.
- MD escalation is triggered by unmet criteria OR mandatory MD review service codes.
- Check `case_review_events` for prior review attempts — they may change the posture.

### Pharmacy Appeal Timelines
- Appeal deadline = `adverse_notice_date` + plan-specific days (typically 60 for standard).
- `appeal_received_date` is the filing date — compare to deadline for timely/late.
- Expedited = 72-hour turnaround if attestation + evidence; standard = 30 calendar days.

### FPL & Income for Assistance
- 2025 Federal Poverty Level baseline: $15,060 for household of 1, $20,440 for 2, $25,820 for 3, $31,200 for 4, etc.
- Formula: fpl_pct = income / (15060 + (size-1) × 5380) × 100.
- Compare fpl_pct to `max_income_fpl` from assistance_programs.

### Rounding & Output Conventions
- Money amounts: round to **2 decimal places**.
- Percentages/ratios: round to **4 decimal places** (e.g., 0.1234 = 12.34%).
- Case rows sorted by case ID ascending (AUTH00001 before AUTH00002) or med_case_id ascending.
- JSON output must exactly match the answer_template structure — no extra keys, no missing required keys.
- Arrays should be empty `[]` not null when no items exist.

### General SQL Habits
- Use `DISTINCT` liberally when exploring enum columns.
- `LIMIT 5` when sampling — the service has a 30s timeout.
- Always alias computed columns clearly for JSON output.
- Date comparisons: all dates are ISO 8601 strings (YYYY-MM-DD or YYYY-MM-DDTHH:MM). String comparison works for equality but use proper date functions for ranges when available.
- The SQLite service reports `row_count` — verify aggregation cardinality matches expectations.
