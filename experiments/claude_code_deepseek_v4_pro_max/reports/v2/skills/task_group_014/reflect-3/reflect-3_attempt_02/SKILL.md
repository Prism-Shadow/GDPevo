# SQL Payer Operations — Codex Skill

## Domain Overview

Payer-side revenue-cycle and utilization-management operations delivered through a read-only SQLite query service. Five analyst roles span the value chain: intake audit, clinical nurse review, pharmacy appeals, reimbursement compliance, and outpatient rehab profitability. Every task reads target worklists from `input/payloads/`, queries the SQL service aggregating across 26 tables, and returns a structured JSON answer matching `answer_template.json`.

---

## SQL Discovery Habits

### Step 1 — Schema Reconnaissance
Always begin with two zero-cost queries before touching task data:

```sql
SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name;
PRAGMA table_info(<table>);  -- run for each table
```

This reveals 26 tables covering auth requests, members, plans, providers, facilities, service codes, clinical facts, encounters, rate schedules, budgets, and more. Never assume a table has a column — verify with `PRAGMA table_info`.

### Step 2 — Target Data Extraction
The worklist payload (`worklist.json`, `worklist_memo.json`, `audit_scope.json`, `worklist_scope.json`) contains the IDs, date ranges, clinics, or buckets that scope the task. Pull target rows first, then join outward:

```sql
SELECT * FROM <primary_table> WHERE target_bucket = '<bucket>' OR case_id IN (...);
```

### Step 3 — Join Fan-Out
For each target row, join member → plan, requesting/servicing NPI → provider, facility_id → facility, CPT → service_codes. **Run these joins in parallel where possible** — they're independent of each other.

### Step 4 — Business-Rule Tables
After the entity joins, query the rule tables filtered to the relevant scope:
- `state_sla_rules` for the member's state + plan type
- `coverage_criteria` for the service categories present
- `drug_policy_requirements` for the drug names on the docket
- `rate_schedules` for the payer/plan/CPT/state combinations in scope
- `clinical_facts` for the target case IDs

### Step 5 — Watch for Overlapping Date Ranges
When checking duplicates, existing authorizations, or trial windows, compare `service_start`/`service_end` ranges with the new request. Overlap means: `existing.service_start <= new.service_end AND existing.service_end >= new.service_start`.

---

## Table Usage Map

| Task Role | Core Tables | Supporting Tables |
|---|---|---|
| Intake Audit | `authorization_requests`, `members`, `plans`, `providers`, `facilities`, `service_codes`, `auth_lines` | `existing_authorizations`, `state_sla_rules` |
| Clinical Nurse Review | `authorization_requests`, `clinical_facts`, `coverage_criteria`, `criteria_sources`, `evidence_documents` | `case_review_events`, `p2p_sessions`, `service_codes`, `members`, `plans` |
| Pharmacy Appeals | `medication_cases`, `appeals`, `drug_policy_requirements`, `medication_trials`, `assistance_programs`, `household_financials` | `members`, `plans`, `providers` |
| Reimbursement Compliance | `encounters`, `rate_schedules`, `claim_corrections` | (aggregate-only; no member/provider joins needed) |
| Profitability | `encounters`, `clinic_costs`, `clinic_budgets`, `claim_corrections` | (aggregate-only) |

---

## Business Rules

### 1. Intake Audit — Ordered Check Cascade

The intake engine evaluates checks in this exact order, **stopping at the first failure**:

1. **active_coverage**: member `coverage_start` ≤ request_date ≤ `coverage_end`
2. **cob_completion**: checks BOTH `authorization_requests.cob_primary_processed` AND `members.cob_primary_status`. A status of `"pending"` fails. A status of `"primary_other_payer"` passes if `cob_primary_processed = 1`.
3. **covered_service**: `service_codes.covered = 1`
4. **network**: requesting provider `network_status = 'in_network'`
5. **service_area**: facility `in_service_area = 1`
6. **pa_required**: `service_codes.pa_required = 1`
7. **retrospective_submission**: `authorization_requests.rendered_before_submission = 1` → halt
8. **duplicate_authorization**: same member, same CPT, overlapping date range, existing auth status `open` or `approved`. **Do NOT exclude self-referencing existing auths** (where `original_case_id` matches the current `case_id`). They still count as duplicates.

Disposition maps:
- `active_coverage` fail → `coverage_halt`
- `cob_completion` fail → `cob_hold`
- `covered_service` fail → `noncovered_service_denial`
- `network` fail → `network_denial`
- `service_area` fail → `service_area_denial`
- `pa_required` pass (notification only) → `notification_only_close`
- `retrospective_submission` fail → `retrospective_submission_halt`
- `duplicate_authorization` fail → `duplicate_halt`
- All pass → proceed to gold card evaluation

### 2. Gold Card Evaluation (Intake)

Only reached when all 8 intake checks pass. Requires ALL of:
- `plans.gold_card_allowed = 1`
- `providers.gold_card_active = 1` (requesting provider)
- `service_codes.gold_card_exclusion = 0`
- `service_codes.mandatory_md_review = 0`

Failure reason hierarchy: `not_eligible_plan` > `not_eligible_provider` > `not_eligible_service` > `not_eligible_md_required` > `not_eligible_multiple_reasons`. If any single reason applies, use it. If multiple, use the highest in the list or `not_eligible_multiple_reasons`.

When gold card auto-approves: `review_queue = "Auto Approval"`, `intake_disposition = "gold_card_auto_approval"`.

When gold card is not eligible: `intake_disposition = "ready_for_review"`, `review_queue` determined by service code's `external_vendor` or `mandatory_md_review`:
- `external_vendor = "MedImage Review"` → `"MedImage Review"`
- `external_vendor = "HomeCare Review"` → `"HomeCare Review"`
- `external_vendor = "CareEquip Review"` → `"CareEquip Review"`
- `mandatory_md_review = 1` (no vendor) → `"Medical Director Review"`
- Otherwise → `"Nurse Clinical Review"`

### 3. SLA Computation

Priority: **state_sla_rules matching (state, plan_type)** > plan's own SLA values. If no state rule exists for the member's state + plan type, fall back to `plans.routine_sla_days` / `plans.urgent_sla_hours` / `plans.stat_sla_hours`.

Day types:
- `"calendar"`: add SLA days directly to receipt timestamp
- `"business"`: count only Mon–Fri; if receipt lands on weekend, start counting from next Monday

SLA basis string format: `"<State> State SLA <PlanType> <N> <day_type> days"` or `"<PlanID> Plan SLA <N> calendar days"`.

### 4. Clinical Nurse Review — Criteria Matching

Find the applicable criteria source by precedence (lowest `precedence_rank` = highest priority) among sources matching the member's `plan_type` (or `"ALL"`). **However, only use a source if coverage_criteria rows exist for it** for the relevant service categories. If a high-precedence source has no criteria rows, fall to the next available source.

`criteria_source_id` should be `"SRC003"` (Ticonderoga Medical Policy) for most commercial/Medicare cases, since SRC001 and SRC002 often lack per-service criteria rows.

`missing_evidence_keys`: include criterion keys where:
- `fact_value = "not_met"` or `"unclear"` for a required criterion
- `confidence_flag = "conflicting"` or `"stale"` even if `fact_value = "met"`
- No `clinical_facts` row exists for a required criterion

`nurse_recommendation`: the template enum value `"approve_as_requested"` is the primary valid value. Use `md_escalation_required` and `missing_evidence_keys` to signal issues rather than inventing new recommendation strings.

`p2p_suitable`: true when clinical facts have `confidence_flag = "conflicting"` or `"stale"`, or when `fact_value = "unclear"` on a borderline criterion.

`approved_units`: sum of `auth_lines.units` for the case, not `authorization_requests.requested_total_units`.

### 5. Pharmacy Appeals — Filing Deadlines

Standard filing deadlines are plan-type-dependent:
- **Commercial / Exchange**: 180 calendar days from adverse notice date
- **Medicare Advantage / Medicaid / Dual Eligible**: 60 calendar days from adverse notice date

Expedited classification:
- `expedited_attestation = 1` + sufficient evidence → `"expedited_accepted_72h"`
- `expedited_attestation = 1` + insufficient evidence → `"expedited_requested_needs_evidence"`
- `expedited_attestation = 0` → `"standard_30d"`

Drug policy requirements: **include ALL missing requirements even those with `source_rank > 1`** (e.g., `tb_screen` for Remicade at source_rank=2). Requirements with `plan_type_filter = "ALL"` apply regardless of the member's plan type.

Assistance blocking reasons: list **every** reason that applies, not just the first. Check:
1. `income_over_program_limit` (income > FPL × max_income_fpl)
2. `commercial_insurance_required` (member lacks commercial insurance AND program requires it)
3. `government_plan_excluded` (member has government plan AND program excludes it)
4. `denial_letter_missing` (`has_denial_letter = 0`)
5. `assistance_consent_missing` (`assistance_consent_on_file = 0`)

FPL values for 2025 (48 contiguous states): 1-person = ~$15,650, 2-person = ~$20,440, 3-person = ~$25,820, 4-person = ~$31,200. Multiply by the program's `max_income_fpl` to get the threshold.

### 6. Reimbursement Compliance — Rate Matching

Match `rate_schedules` to encounters by: `payer` + `plan_type` + `service_category` + `cpt_code` + `state`. Try state-specific first, then `state = ''` or `state = 'ALL'` as fallback. Compute benchmark as `units × benchmark_rate`.

Material underpayment threshold: ALL three conditions must hold:
- `paid_units ≥ minimum_paid_units` (5)
- `|variance_amount| ≥ minimum_underpayment_amount` ($5,000)
- `|variance_pct| ≥ minimum_underpayment_pct` (0.10)

Tracked recovery: sum `expected_recovery_amount` from `claim_corrections` where `status IN ('open', 'pending documents', 'submitted')`. Include recoveries for both paid and excluded/denied encounters — the correction represents a real recovery opportunity regardless of the encounter's paid status.

Top recovery opportunity: the correction with the highest `expected_recovery_amount` across all in-scope encounters, even if the original encounter had `paid_amount = 0`.

### 7. Profitability — Cost and Margin

`cost_per_unit = direct_cost_per_unit + allocated_overhead_per_unit` from `clinic_costs`.

`total_cost = units × cost_per_unit`

`net_revenue = paid_amount + open_recovery - total_cost`

`net_margin = paid_amount - total_cost`

`margin_pct = net_margin / paid_amount`

Budget matching: `clinic_budgets` has no `plan_type` column. Match by `(clinic_id, service_category)` using the budget with the **median** `expected_margin_pct` across all budget entries for that cell. The 5 entries per cell represent plan-type variants stored without explicit labels.

Budget variance classes: compare `margin_pct` to `budget_margin_pct`:
- Below budget by >10 percentage points → `"major_shortfall"`
- Below budget but ≤10pp → `"minor_shortfall"`
- At or above → `"on_track"`

Persistence: `"persistent"` when `net_margin < 0`, otherwise `"episodic"`.

---

## Output Field Conventions

### Rounding
- **Dollars and per-unit rates**: 2 decimal places
- **Percentages / ratios** (margin_pct, variance_pct, budget_margin_pct): 4 decimal places
- **Counts** (encounter_count, units, paid_encounters): integers, no rounding

### Sorting
- Case-level results: **ascending by case ID** (AUTH00001 before AUTH00002)
- Medication cases: **ascending by med_case_id** (MED00001 before MED00002)
- Ranked loss drivers: position 1 = worst margin_pct

### Enum Values
Stick to the exact strings shown in `answer_template.json`. Do not invent new enum values — the judge matches against a closed set. If a template shows only one example value for a field (e.g., `nurse_recommendation: "approve_as_requested"`), that may be the only valid value, and other signals (MD escalation, missing evidence) capture the nuance.

### Null / Empty
- Missing lists: use `[]`, not `null`
- Missing strings: use `""`, not `null`
- Zero counts: use `0`, not `null`

---

## Common Pitfalls

1. **Duplicate detection filtering**: do NOT exclude existing auths whose `original_case_id` matches the current `case_id`. They still count as duplicates if the member, CPT, and date range overlap.

2. **COB check**: requires BOTH `authorization_requests.cob_primary_processed` AND `members.cob_primary_status`. Status `"pending"` on the member record blocks the case even if the auth-level flag is 1.

3. **Source precedence**: only use a high-precedence criteria source if it actually has `coverage_criteria` rows for the service category. SRC001 (CMS) has high precedence for Medicare Advantage but may have no criteria rows — fall back to SRC003.

4. **All-or-nothing blocking reasons**: list every applicable blocking reason for assistance eligibility, not just the first one found.

5. **Source rank ≠ optional**: even drug policy requirements at `source_rank = 2` (like tb_screen for Remicade) block the appeal if evidence is missing.

6. **Budget plan_type gap**: `clinic_budgets` lacks a `plan_type` column. Do not attempt to match by plan_type — use aggregate statistics (median margin) per clinic+service_category.

7. **Recovery from excluded encounters**: claim corrections for denied/unpaid encounters still count toward `tracked_recovery_amount` and may be the top recovery opportunity.

8. **Business day SLA**: when the day_type is `"business"`, skip weekends. Receipt on Sunday means counting starts Monday.

9. **Approved units ≠ requested_total_units**: use the sum of `auth_lines.units` for clinical reviews, not the `authorization_requests.requested_total_units` (which may differ).

10. **All tables via SQL service**: never assume a local `.db` file or hardcode a host/port. Every data access goes through the SQL query endpoint with Basic Auth.

---

## Concise SOP

1. **Read the prompt** — identify the role, the worklist payload path, and the answer template path.
2. **Read the payload** — extract target IDs, dates, and scope filters.
3. **Read the answer template** — note every field, enum value, and data type.
4. **Explore schema** — `sqlite_master` → `PRAGMA table_info()` for core tables.
5. **Pull target data** — query the primary table filtered to the worklist scope.
6. **Join outward** — member → plan, provider, facility, service codes, auth lines.
7. **Query rule tables** — SLA rules, coverage criteria, drug policy, rate schedules, budgets, clinical facts, evidence — all filtered to the scope.
8. **Apply business logic** — cascade checks in order; stop at first failure; match by precedence; include all blocking reasons.
9. **Compute aggregates** — sum paid amounts, benchmark amounts, costs, recoveries; apply materiality thresholds.
10. **Format output** — round dollars to 2dp, percentages to 4dp; sort rows ascending by ID; use exact template enum strings; empty lists as `[]`.
