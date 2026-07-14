# Payer Operations SQL Skill — Codex/Claude Task Group 014

## Overview

This skill covers payer-side revenue-cycle and utilization-management tasks served through a remote SQLite query endpoint. The domain spans authorization intake, nurse clinical review, pharmacy appeals, reimbursement compliance, and outpatient rehab profitability analysis. All tasks follow the same pattern: read the SQL schema, issue read-only POST queries with HTTP Basic Auth, and return a JSON object matching the provided `answer_template.json`.

## Environment

- **Endpoint:** `{TASK_ENV_BASE_URL}/query` — the task prompt provides the base URL. Read it from the prompt or `environment_access.md`; never hard-code.
- **Auth:** HTTP Basic Auth; credentials are in the task prompt or `environment_access.md`.
- **Request shape:** `POST` with `Content-Type: application/json`; body `{"sql": "<query>", "params": []}`.
- **Response shape:** `{"columns": [...], "row_count": N, "rows": [{...}, ...]}`.
- **Database flavor:** SQLite. Standard SQLite functions work (`strftime`, `date`, `julianday`, `COALESCE`, `ROUND`, aggregate functions). No stored procedures or CTE recursion limits beyond SQLite defaults.

## Schema Discovery SOP

**Always start by listing all tables:**
```sql
SELECT name FROM sqlite_master WHERE type='table' ORDER BY name
```

**Then inspect each table's columns:**
```sql
PRAGMA table_info(<table_name>)
```

**Then sample rows to understand data shapes:**
```sql
SELECT * FROM <table> LIMIT 3
```

**Check distinct enum values for every categorical column** — this is critical for mapping output enums correctly:
```sql
SELECT DISTINCT <col> FROM <table> ORDER BY <col>
```

**Check join cardinalities early.** Before building complex queries, verify whether joins are 1:1, 1:many, or many:many. Use `GROUP BY ... HAVING COUNT(*) > 1` to find multi-row situations that would inflate aggregates.

## Core Tables and Their Purposes

### Authorization Workflow (Tasks 1–2)
| Table | Purpose |
|---|---|
| `authorization_requests` | Payer intake case header. Key: `case_id`. Has `target_bucket` for filtering worklists. |
| `auth_lines` | Line items per authorization: `case_id` + `line_no`. Maps to `cpt_code` via `service_codes`. |
| `members` | Member demographics: `member_id`, `plan_id`, `residence_state`, `coverage_start/end`, `cob_primary_status`. |
| `plans` | Plan metadata: `plan_id`, `plan_type` (Commercial/Medicare Advantage/Medicaid/Exchange/Dual Eligible), `state`, `gold_card_allowed`, SLA fields. |
| `providers` | Provider profiles: `npi` key. Has `network_status`, `sanctions_active`, `credentials_active`, `gold_card_active`. |
| `facilities` | Facility info: `facility_id`, `state`, `in_service_area`. |
| `service_codes` | CPT/HCPCS code metadata: `code`, `service_category`, `pa_required`, `covered`, `notification_only`, `gold_card_exclusion`, `mandatory_md_review`, `external_vendor`, `delegated_program`. |
| `existing_authorizations` | Prior auths: `existing_auth_id`, `member_id`, `cpt_code`, `status`, `service_start/end`, `original_case_id`. |
| `state_sla_rules` | Regulatory SLA timelines by `state` + `plan_type_filter`. Fields: `routine_days`, `urgent_hours`, `stat_hours`, `day_type` (calendar vs business). |

### Clinical Review (Task 2, also supports Task 1)
| Table | Purpose |
|---|---|
| `case_review_events` | Review audit trail: `case_id`, `stage`, `reviewer_role`, `event_type`, `outcome`, `notes`. |
| `clinical_facts` | Extracted structured facts: `case_id`, `criterion_key`, `fact_value`, `confidence_flag` (clear/partial/conflicting/stale), `source_doc_id`, `source_rank`. |
| `evidence_documents` | Clinical documentation: `case_id`, `doc_id`, `doc_type`, `is_current`, `source_system`, `source_rank`. |
| `coverage_criteria` | Medical policy criteria: `service_category`, `criterion_key`, `required_value`, `criteria_source_id`, `plan_type_filter`, `is_required_for_approval`. |
| `criteria_sources` | Policy source hierarchy: `source_id`, `precedence_rank`, `plan_type_filter`, `service_category_filter`. |

### Pharmacy Appeals (Task 3)
| Table | Purpose |
|---|---|
| `medication_cases` | Drug auth cases: `med_case_id`, `member_id`, `drug_name`, `payer_formulary_status`, `target_bucket`. |
| `medication_trials` | Step therapy / trial history: `med_case_id`, `medication_name`, `drug_class`, `outcome`, `documented`. |
| `drug_policy_requirements` | Drug-specific UM criteria: `drug_name`, `plan_type_filter`, `requirement_key`, `required_value`. |
| `appeals` | Appeal records: `appeal_id`, `case_or_med_case_id`, `appeal_subject_type` (authorization/medication), `expedited_attestation`, `new_evidence_received`, `adverse_notice_date`, `appeal_received_date`. |
| `assistance_programs` | Manufacturer copay/patient assistance: `program_id`, `drug_name`, `max_income_fpl`, `requires_commercial_insurance`, `excludes_government_plan`, `requires_denial`, `form_name`. |
| `household_financials` | Member financial data: `member_id`, `household_size`, `annual_income`, `insurance_type` (commercial/government), `has_denial_letter`, `assistance_consent_on_file`. |

### Revenue Cycle / Reimbursement (Tasks 4–5)
| Table | Purpose |
|---|---|
| `encounters` | Paid/billed claim encounters: `encounter_id`, `clinic_id`, `service_date`, `payer`, `plan_type`, `cpt_code`, `service_category`, `units`, `paid_amount`, `billed_amount`, `denial_code`. |
| `claim_corrections` | Open recovery / adjustment items: `correction_id`, `encounter_id`, `correction_type`, `expected_recovery_amount`, `status` (open/pending documents/submitted/closed unrecovered), `correction_deadline`. |
| `rate_schedules` | Contracted benchmark rates: `rate_id`, `payer`, `plan_type`, `service_category`, `cpt_code`, `state`, `effective_start`, `effective_end`, `benchmark_rate`, `benchmark_source` (current contract/legacy contract/future draft). |
| `clinic_costs` | Clinic unit cost basis: `clinic_id`, `fiscal_year`, `service_category`, `direct_cost_per_unit`, `allocated_overhead_per_unit`. |
| `clinic_budgets` | Budget targets: `clinic_id`, `fiscal_year`, `payer`, `service_category`, `expected_units`, `expected_net_revenue`, `expected_margin_pct`. |

## Task-Specific SOPs

### Task 1: Authorization Intake Audit

**Goal:** Apply a cascading gate check for each authorization case and classify disposition.

**Intake gate order (stop at first failure):**
1. **Active coverage** — `coverage_start <= request_date <= coverage_end`. Check `retro_reinstated_date` if present.
2. **COB completion** — `cob_primary_processed = 1` on the auth request AND `cob_primary_status != 'pending'` AND `cob_primary_status != 'primary_other_payer'` on the member record. A pending or unresolved primary-payer COB means `cob_hold`.
3. **Covered service** — `service_codes.covered = 1`. If `covered = 0`, it's `noncovered_service_denial`.
4. **Network** — requesting provider: `providers.network_status = 'in_network'`. Also check servicing provider.
5. **Service area** — `facilities.in_service_area = 1`. The facility state must match the plan state or have `in_service_area = 1`.
6. **PA required** — `service_codes.pa_required = 1`. If `notification_only = 1` and `pa_required = 0`, it's `notification_only_close`.
7. **Retrospective submission** — if `rendered_before_submission = 1`, it's `retrospective_submission_halt`.
8. **Duplicate check** — query `existing_authorizations` for same `member_id` + same `cpt_code` + overlapping `service_start/end` dates. If found, it's a `duplicate_halt`.
9. **Gold Card review** — only reached if all prior gates pass. Requires ALL of: `plan.gold_card_allowed = 1`, `provider.gold_card_active = 1`, `service_codes.gold_card_exclusion = 0`, `service_codes.mandatory_md_review = 0`.

**Review queue assignment:**
- Intake halt → `"No Review - Intake Halt"`
- Gold Card passed → `"Auto Approval"`
- Otherwise: check `service_codes.external_vendor` — `"MedImage Review"`, `"CareEquip Review"`, `"HomeCare Review"`, or fallback to `mandatory_md_review = 1` → `"Medical Director Review"` else `"Nurse Clinical Review"`.

**SLA timing:**
- Join `state_sla_rules` on the **member's residence state** (from `members.residence_state` joined to `state_sla_rules.state`) AND the **plan type** (matched to `state_sla_rules.plan_type_filter`).
- SLA clock starts at `receipt_timestamp` on the auth request. Compute `sla_due_at` by adding `routine_days` (calendar or business days per `day_type`), `urgent_hours`, or `stat_hours` based on `urgency_attested`.
- **SLA rule matching priority:** Exact plan_type match first; if no match, try state-level fallbacks.

**Provider item check:**
- `sanctions_active = 1` → `"requesting_provider_active_sanction"`
- `credentials_active = 0` → `"requesting_provider_credentials_inactive"`
- Otherwise: `"none"`

**Notice flag:** `true` when intake disposition is not `gold_card_auto_approval` and not `notification_only_close`.

**Duplicate handling:** For the `duplicate_existing_auth_ids` array, collect `existing_auth_id` values where the same member, same CPT, and the service date ranges overlap.

### Task 2: Nurse Clinical Review

**Goal:** Evaluate clinical evidence against coverage criteria and produce a nurse recommendation with escalation posture.

**Key steps:**
1. Filter `authorization_requests` by `target_bucket` from `worklist.json`.
2. Look up service category via `auth_lines` → `service_codes`.
3. Find applicable `criteria_sources` — precedence-ranked by `plan_type_filter` and `service_category_filter`.
4. Match `coverage_criteria` to the case's service category and plan type.
5. Examine `clinical_facts` for each criterion — check `fact_value` against `required_value`.
6. Assess `evidence_documents` for recency, `source_rank`, and `is_current`.
7. Check `case_review_events` for prior review stage/outcome.
8. Check `p2p_sessions` — if a P2P is scheduled and requesting provider joined but no-showed, it affects P2P suitability.

**Nurse recommendation decision rules:**
- All required criteria met with `confidence_flag = 'clear'` → `approve_as_requested`.
- Criteria with `confidence_flag = 'conflicting'` or `'stale'` → escalate.
- Missing evidence for required criteria → flag in `missing_evidence_keys`.

**MD escalation:**
- `mandatory_md_review = 1` on `service_codes` → automatic MD escalation.
- Clinical facts with `confidence_flag = 'conflicting'` on required criteria → MD escalation.
- `md_escalation_reason_code` values include `mandatory_md`, `conflicting_evidence`, `stale_evidence`, `partial_evidence`, `none`.

**P2P suitability:** True when evidence is partial but not clearly negative — the provider could supply missing documentation.

**Criteria source selection:** Use the lowest `precedence_rank` that matches the plan type. For Medicare Advantage, CMS NCD/LCD (SRC001) has priority. For Medicaid, State Medicaid UM Manual (SRC002). For all others, Ticonderoga Medical Policy (SRC003) rank 2, InterQual (SRC004) rank 3, MCG (SRC005) rank 4.

### Task 3: Pharmacy Appeal & Manufacturer Assistance

**Goal:** For each medication case, determine appeal routing and manufacturer assistance eligibility — two separate paths.

**Appeal path:**
1. Match `medication_cases` (filtered by `target_bucket`) to `appeals` on `case_or_med_case_id`.
2. Verify appeal timeliness: `appeal_received_date` vs `adverse_notice_date`. Typical deadline is 60 days from adverse notice for standard, 72 hours for expedited.
3. Check `drug_policy_requirements` for the drug — `plan_type_filter = 'ALL'` or matching the member's plan type.
4. Cross-reference `medication_trials` to find documented step therapy / trial outcomes.
5. Check if all policy requirements are met or missing. Map missing requirements to the enum keys: `diagnosis`, `step_therapy`, `tb_screen`, `topical_failure`.

**Appeal classification:**
- `expedited_accepted_72h`: `expedited_attestation = 1` on the appeal AND all required evidence present.
- `expedited_requested_needs_evidence`: `expedited_attestation = 1` but missing policy requirements.
- `standard_30d`: `expedited_attestation = 0`.

**Timeliness:** Compute days between `adverse_notice_date` and `appeal_received_date`. Standard is within 60 calendar days. Expedited within 72 hours.

**Assistance path (separate from appeal):**
1. Look up `assistance_programs` by `drug_name`.
2. Check `household_financials` — compute income as % of Federal Poverty Level: `annual_income / (household_size * FPL_base)`. FPL for 2025: household of 1 = ~$15,060. Scale by household size.
3. Income check: income % FPL ≤ `max_income_fpl`.
4. Insurance check: if `requires_commercial_insurance = 1` and `insurance_type = 'government'` → blocked.
5. Government plan exclusion: if `excludes_government_plan = 1` and plan is Medicare/Medicaid/Dual → blocked.
6. Denial requirement: if `requires_denial = 1` and `has_denial_letter = 0` → blocked.
7. Consent requirement: `assistance_consent_on_file = 1` needed.

**Blocking reasons enum:** `income_over_program_limit`, `commercial_insurance_required`, `government_plan_excluded`, `denial_letter_missing`, `assistance_consent_missing`.

**Path separation:** `appeal_only`, `assistance_only`, `parallel_appeal_and_assistance`, or `no_active_route`.

**Member plan type mapping:**
- From `members.plan_id` → `plans.plan_type` → one of: `Commercial`, `Medicare Advantage`, `Medicaid`, `Exchange`, `Dual Eligible`.

### Task 4: Reimbursement Compliance

**Goal:** Compare paid encounter amounts against contracted benchmark rates, flag material variances, and identify top recovery opportunities.

**Key join chain:**
```
encounters → rate_schedules
  ON encounters.payer = rate_schedules.payer
  AND encounters.plan_type = rate_schedules.plan_type
  AND encounters.service_category = rate_schedules.service_category
  AND encounters.cpt_code = rate_schedules.cpt_code
  AND encounters.service_date BETWEEN rate_schedules.effective_start AND rate_schedules.effective_end
```

**State matching for rates:** Join the encounter's clinic to a facility or use the clinic's state to match `rate_schedules.state`. The `audit_scope.json` provides clinic→state mapping.

**Rate source priority:** `benchmark_source = 'current contract'` takes precedence. Fall back to `legacy contract`. Exclude `future draft`.

**Exclude denied encounters:** Encounters with non-null `denial_code` and `paid_amount = 0` are excluded from paid-rate analysis but counted in `excluded_denied_or_unpaid_encounters`.

**Materiality filters:** Apply `minimum_paid_units`, `minimum_underpayment_amount`, and `minimum_underpayment_pct` from `audit_scope.json`. Only flag cells/variance where ALL thresholds are met.

**Variance calculation:**
- `variance_amount = benchmark_amount - paid_amount` (positive = underpayment)
- `variance_pct = variance_amount / benchmark_amount`
- `paid_per_unit = paid_amount / units`
- `benchmark_per_unit = benchmark_rate` (per unit from rate_schedules)

**Recovery tracking:** LEFT JOIN `claim_corrections` on `encounter_id`. Only include corrections with `status IN ('open', 'pending documents', 'submitted')` for tracked recovery amounts.

**Top recovery opportunity:** Sort by `expected_recovery_amount DESC` among open corrections in the period, pick the largest.

**Output rounding:** Money and per-unit rates → 2 decimals. Percentage ratios → 4 decimals.

### Task 5: Outpatient Rehab Profitability

**Goal:** Compute payer-service cell profitability and flag underperforming cells against budget.

**Key tables:** `encounters`, `claim_corrections`, `clinic_costs`, `clinic_budgets`.

**Cell definition:** `(clinic_id, plan_type, service_category)` — group encounters by these three dimensions.

**Computation per cell:**
```
paid_amount = SUM(encounters.paid_amount) WHERE denial_code IS NULL
open_recovery = SUM(claim_corrections.expected_recovery_amount) WHERE status IN ('open','pending documents','submitted')
total_revenue = paid_amount + open_recovery
cost_per_unit = direct_cost_per_unit + allocated_overhead_per_unit (from clinic_costs)
total_cost = SUM(encounters.units) * cost_per_unit
net_revenue = total_revenue
net_margin = total_revenue - total_cost
margin_pct = net_margin / NULLIF(total_revenue, 0)
```

**Budget comparison:**
- Match `clinic_budgets` on `(clinic_id, payer, service_category, fiscal_year)`.
- If multiple budget rows exist per combination, use the **average** of `expected_margin_pct` across them.
- `budget_variance_class`: Compare `margin_pct` to `expected_margin_pct` (budget margin). Typical thresholds:
  - `major_shortfall`: margin_pct < expected_margin_pct - 0.10
  - `minor_shortfall`: margin_pct < expected_margin_pct but within 0.10
  - `on_target`: margin_pct >= expected_margin_pct

**Persistence classification:** Compare across multiple periods if available. A cell underperforming in consecutive quarters is `persistent`.

**Payer actions:**
- `rate_floor_review`: major shortfall driven by low paid rates.
- `contract_renegotiation`: persistent underperformance.
- `volume_reallocation`: high-volume loss driver.
- `cost_reduction_review`: cost-driven margin erosion.

**Ranked loss drivers:** Top 3 cells by lowest `net_margin` (or `margin_pct`).

**Output rounding:** Dollars → 2 decimals. Percentages → 4 decimals.

## Common Pitfalls

### Join Pitfalls
1. **Multiple auth_lines per case:** `authorization_requests` to `auth_lines` is 1:many. For intake checks, aggregate or pick the first line. The service category is at line level — if a case has multiple lines with different categories, use `GROUP_CONCAT(DISTINCT ...)` or pick the most restrictive.
2. **Existing authorizations join:** When checking duplicates, match on `member_id` + `cpt_code` with overlapping date ranges, not just `original_case_id`. Use: `existing.member_id = auth.member_id AND existing.cpt_code = auth_lines.cpt_code AND existing.service_start <= auth.service_end AND existing.service_end >= auth.service_start`.
3. **Rate schedule matching must include state:** `rate_schedules` are state-specific. An encounter in CA must match a CA rate row. If no state match, the rate doesn't apply.
4. **Rate schedule effective date range:** Always check `service_date BETWEEN effective_start AND effective_end`. Multiple rates may exist for the same CPT/payer/plan — pick the one effective on the service date.
5. **Clinic budgets have multiple rows per combination:** 5 rows per (clinic, payer, service_category, fiscal_year). Aggregate with AVG on `expected_margin_pct` and SUM on `expected_units`/`expected_net_revenue`.

### Data Quality Pitfalls
6. **NULL handling:** `denial_code` in encounters distinguishes paid vs denied. But a NULL denial_code with `paid_amount = 0` is also effectively unpaid. Filter both: `WHERE denial_code IS NULL AND paid_amount > 0` for revenue calculations.
7. **Stale/conflicting clinical facts:** A criterion might have multiple `clinical_facts` rows with different `fact_value` values. Use the one with highest `source_rank` or most recent `fact_date`, and note `confidence_flag` — `conflicting` and `stale` are escalation triggers.
8. **COB status has two fields:** The `authorization_requests.cob_primary_processed` (0/1) tells if the submitter checked the box. The `members.cob_primary_status` tells the actual state (`processed`/`pending`/`primary_other_payer`). Both matter: if `cob_primary_processed = 0`, the gate fails regardless. If `cob_primary_processed = 1` but `cob_primary_status = 'pending'`, it still fails (COB hold).
9. **SLA rule matching is not always exact:** If no `state_sla_rules` row matches a specific `plan_type_filter` for the member's state, try matching on state alone. Some state rules only exist for specific plan types. Check `state_sla_rules` early to know which states are covered.
10. **Rendered-before-submission is retrospective:** `rendered_before_submission = 1` means service already happened — this is a hard intake halt, regardless of other gates.

### Enum/Value Pitfalls
11. **Plan type values are exact strings:** `Commercial`, `Medicare Advantage`, `Medicaid`, `Exchange`, `Dual Eligible`. Case-sensitive. Same as stored in the database.
12. **Review queue values are exact:** `"No Review - Intake Halt"`, `"Auto Approval"`, `"Nurse Clinical Review"`, `"Medical Director Review"`, `"MedImage Review"`, `"CareEquip Review"`, `"HomeCare Review"`.
13. **Gold card decision enum:** Use `"not_reached_intake_halt"` when any prior gate fails, `"auto_approve"` when all gold card conditions pass, otherwise a specific ineligibility reason.
14. **Appeal eligibility status values:** `appeal_ready`, `appeal_incomplete`, `appeal_not_timely`.
15. **Missing policy requirement keys:** `diagnosis`, `step_therapy`, `tb_screen`, `topical_failure` — match exactly the `requirement_key` from `drug_policy_requirements`.

### Output Conventions
16. **Sort case arrays** as specified — usually ascending by `case_id` or `med_case_id`.
17. **Rounding:** Money → 2 decimals (`ROUND(x, 2)`). Percentages → 4 decimals (`ROUND(x, 4)`). Use `ROUND()` in SQL, not Python — the template expects numbers already rounded.
18. **Empty arrays vs null:** Use `[]` not `null` for empty lists (`missing_evidence_keys`, `blocking_reasons`, `duplicate_existing_auth_ids`).
19. **Include summary/count fields:** Every task has a summary block at the JSON root or within subsections. Compute these from the case-level results, not from separate SQL queries — they must be consistent.
20. **Date format:** `YYYY-MM-DDTHH:MM` for timestamps (ISO 8601 without seconds). `YYYY-MM-DD` for dates only.

## Recommended Query Workflow

1. **Read the answer template and payload files first** — they define the output shape and task parameters.
2. **List and inspect all tables** mentioned in the prompt. Don't assume column names.
3. **Run small exploration queries** — check distinct values, join counts, date ranges.
4. **Build the main query incrementally** — start with the target filtering (worklist/scope), add joins one at a time, verify row counts.
5. **Use SQLite date functions:** `date()`, `strftime()`, `julianday()` for date math. For SLA due dates: `datetime(receipt_timestamp, '+' || days || ' days')`.
6. **Aggregate after joining** — join first, then GROUP BY at the right granularity. Avoid premature aggregation.
7. **Verify each case/row** against the answer template structure before final submission.
8. **Check summary totals** against case-level results for internal consistency.

## Self-Verification Checklist

Before submitting:
- [ ] All case IDs from the worklist/scope are present in the output.
- [ ] Case rows are sorted in the specified order.
- [ ] Summary counts match the case-level data.
- [ ] All enum string values match the template exactly (case-sensitive).
- [ ] Numbers are rounded to the specified precision.
- [ ] Empty arrays use `[]`, not `null`.
- [ ] The output is valid JSON (single object, no trailing commas).
- [ ] `sla_due_at` is computed from the correct state/plan SLA rule and `receipt_timestamp`.
- [ ] Duplicate checks use overlapping date ranges, not exact matches.
- [ ] Gold card decisions only apply when all prior intake gates pass.
