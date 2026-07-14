# Payer Operations SQL Query Skill

## Overview
This skill covers SQL-based payer operations workflows: authorization intake, clinical utilization review, pharmacy appeals, reimbursement compliance, and service-line profitability analysis. All queries run against a remote SQLite service authenticated with HTTP Basic Auth. The skill assumes read-only SQL access to ~26 tables spanning authorizations, members, plans, providers, facilities, service codes, encounters, rate schedules, corrections, budgets, and clinical evidence.

---

## Schema Discovery SOP

### Step 1 — List all tables
```sql
SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;
```
Expect ~26 tables in a standard payer-ops deployment. Key domain groups:

| Domain | Tables |
|---|---|
| Authorization | `authorization_requests`, `auth_lines`, `existing_authorizations` |
| Member/Plan | `members`, `plans`, `household_financials` |
| Provider/Facility | `providers`, `facilities` |
| Clinical | `clinical_facts`, `evidence_documents`, `case_review_events`, `p2p_sessions`, `coverage_criteria`, `criteria_sources` |
| Pharmacy | `medication_cases`, `medication_trials`, `drug_policy_requirements`, `appeals`, `assistance_programs` |
| Financial | `encounters`, `rate_schedules`, `claim_corrections`, `clinic_costs`, `clinic_budgets` |
| Rules | `service_codes`, `state_sla_rules` |

### Step 2 — Inspect each relevant table
```sql
PRAGMA table_info(<table_name>);
```

### Step 3 — Sample data to understand value domains
```sql
SELECT DISTINCT <column> FROM <table> ORDER BY <column>;
```
Always check for `target_bucket` columns on task-scoped tables — they filter to the exact cases/clinics/members you need.

### Step 4 — Join from the task's entry point table
Each task provides a worklist file (`.json`) specifying target case IDs, clinic IDs, or batch names. Use these to filter your starting query, then join outward.

---

## Table Usage by Task Type

### Authorization Intake Audit
**Entry table**: `authorization_requests` (filter by `target_bucket` from worklist)
**Join chain**: `authorization_requests` → `members` → `plans`, `providers` (on `requesting_npi` AND `servicing_npi`), `facilities`, `auth_lines` → `service_codes`, `existing_authorizations`, `state_sla_rules`

**Key columns**:
- `authorization_requests.cob_primary_processed` — whether COB was run on this auth
- `authorization_requests.rendered_before_submission` — retro flag (1 = services already performed)
- `authorization_requests.oon_exception` — out-of-network exception flag
- `members.cob_primary_status` — values: `processed`, `pending`, `primary_other_payer`, `not_applicable`
- `members.coverage_start` / `coverage_end` — for active-coverage check
- `providers.sanctions_active`, `providers.credentials_active`, `providers.gold_card_active`, `providers.network_status`
- `facilities.in_service_area` — 0 or 1
- `service_codes.covered`, `service_codes.pa_required`, `service_codes.gold_card_exclusion`, `service_codes.mandatory_md_review`, `service_codes.external_vendor`
- `plans.gold_card_allowed`, `plans.plan_type`, `plans.state`
- `existing_authorizations` — check `member_id` + `cpt_code` with overlapping `service_start`/`service_end` and `original_case_id` ≠ current case

**Intake waterfall order** (first failure wins):
1. `active_coverage` — member coverage spans service dates
2. `cob_completion` — COB is resolved
3. `covered_service` — all CPTs have `covered=1`
4. `network` — providers are `in_network`
5. `service_area` — facility `in_service_area=1`
6. `pa_required` — service codes require PA
7. `retrospective_submission` — not rendered before submission
8. `duplicate_authorization` — no overlapping existing auth for same member+CPT
9. `none` — all clear → check gold card eligibility

**Gold card eligibility** (all must be true):
- Plan: `gold_card_allowed=1`
- Requesting provider: `gold_card_active=1`
- Service codes: `gold_card_exclusion=0` and `mandatory_md_review=0`

**SLA calculation**: Match `plan.state` + `plan.plan_type` against `state_sla_rules`. Use `day_type` (calendar vs business). For business-day SLAs, shift weekend receipt dates to Monday before counting.

### Clinical Utilization Review
**Entry table**: `authorization_requests` (filter by `target_bucket`)
**Key tables**: `clinical_facts`, `evidence_documents`, `coverage_criteria`, `criteria_sources`, `case_review_events`, `p2p_sessions`, `auth_lines` → `service_codes`

**Criteria matching rule**: Match `coverage_criteria` by `service_category`. For each required criterion (`is_required_for_approval=1`), check `clinical_facts` for `criterion_key` + `fact_value`. Required value must equal `"met"`.

**Confidence interpretation**:
- `clear` → strong evidence, no concerns
- `partial` → some evidence, needs more
- `conflicting` → contradictory evidence across sources
- `stale` → evidence is too old

**Criteria source selection**: Use `criteria_sources` ordered by `precedence_rank`, filtered by `plan_type_filter` (matches plan type or `ALL`). The lowest-numbered precedence source that applies to the plan type is the governing source. `SRC003` (Ticonderoga Medical Policy) is the universal fallback at precedence 2.

**Nurse approval logic**: Nurse can approve when ALL required criteria have `fact_value="met"` and confidence is not `conflicting`. Otherwise escalate to MD.

**MD escalation triggers**:
- Any required criterion not met (`fact_value` ≠ `"met"`)
- Conflicting confidence on any criterion
- `service_codes.mandatory_md_review=1`
- Prior nurse event with `outcome="adverse_pending"`

**Review queue assignment**: Map `service_codes.external_vendor` to queue:
- `"MedImage Review"` → `"MedImage Review"`
- `"CareEquip Review"` → `"CareEquip Review"`
- `"HomeCare Review"` → `"HomeCare Review"`
- `"none"` + no MD required → `"Nurse Clinical Review"`
- `"none"` + MD required → `"Medical Director Review"`

### Pharmacy Appeals & Assistance
**Entry table**: `medication_cases` (filter by `target_bucket` from worklist)
**Join chain**: `medication_cases` → `members` → `plans`, `medication_trials`, `drug_policy_requirements`, `appeals`, `assistance_programs`, `household_financials`

**Drug policy matching**: Join `drug_policy_requirements` on `drug_name`. For each requirement (`requirement_key`, `required_value="met"`), verify against:
- `medication_cases.diagnosis_code` matching covered indication
- `medication_trials` showing appropriate step therapy attempts
- Other documentation requirements

**Appeal classification**:
- `expedited_classification`: `expedited_accepted_72h` (attestation + evidence), `expedited_requested_needs_evidence` (attestation but no new evidence), `standard_30d` (no attestation)
- `deadline_status`: compare `appeal_received_date` vs `adverse_notice_date` + filing window (60-180 days depending on plan type)
- `eligibility`: `appeal_ready` (all policy requirements met), `appeal_incomplete` (requirements missing), `appeal_not_timely` (past deadline)

**Assistance program matching** (`assistance_programs`):
1. Match on `drug_name`
2. Check `excludes_government_plan` against member insurance type (Medicare Advantage, Medicaid, Dual Eligible → government)
3. Check `requires_commercial_insurance` against member insurance
4. Check `requires_denial` against `household_financials.has_denial_letter`
5. Check income against `max_income_fpl` × FPL for household size
6. Check `assistance_consent_on_file`

**FPL reference (2025)**: Household of 1=$15,060, 2=$20,440, 3=$26,700, 4=$31,200, each additional +$5,380.

**Member plan type**: Use `members.plan_id` → `plans.plan_type`. Do NOT use `appeals.plan_type` as authoritative — it may differ from the member's actual enrollment.

### Reimbursement Compliance Audit
**Entry tables**: `encounters` (filter by `clinic_id`, `service_date` range from audit scope)
**Join chain**: `encounters` → `rate_schedules` (match on `payer`, `plan_type`, `service_category`, `cpt_code`, and state), `claim_corrections`

**Rate schedule matching**: CRITICAL — include state matching:
```sql
JOIN rate_schedules rs ON
  e.payer = rs.payer
  AND e.plan_type = rs.plan_type
  AND e.service_category = rs.service_category
  AND e.cpt_code = rs.cpt_code
  AND e.service_date BETWEEN rs.effective_start AND rs.effective_end
  AND rs.state = CASE WHEN e.clinic_id = 'CLN001' THEN 'CA' WHEN e.clinic_id = 'CLN002' THEN 'NY' END
```
The `facilities` table uses `facility_id` (FAC001-FAC006), NOT `clinic_id` (CLN001-CLN004). Map clinic to state manually from the audit scope JSON.

**Benchmark calculation**: For each encounter, `benchmark_amount = units × benchmark_rate`. Aggregate by clinic-quarter-payer-plan_type-service_category.

**Variance**: `benchmark_amount - paid_amount`. Positive = underpayment. Flag cells meeting ALL materiality thresholds (min units, min amount, min % from scope).

**Recovery tracking**: `claim_corrections` where `status IN ('open', 'pending documents', 'submitted')` — these are active recovery opportunities. Sum `expected_recovery_amount` per clinic-quarter.

### Service-Line Profitability
**Entry tables**: `encounters` (filter by `clinic_id`, `plan_type`, `service_category`, date range)
**Join chain**: `encounters` → `clinic_costs` (match on `clinic_id`, `fiscal_year`, `service_category`), `clinic_budgets` (match on `clinic_id`, `fiscal_year`, `service_category`), `claim_corrections`

**Cost calculation**: `cost_per_unit = direct_cost_per_unit + allocated_overhead_per_unit` from `clinic_costs`

**Margin calculation**:
- `net_revenue = paid_amount + open_recovery` (total revenue including expected recoveries)
- `total_cost = units × cost_per_unit`
- `net_margin = net_revenue - total_cost`
- `margin_pct = net_margin / net_revenue`

**Budget comparison**: `clinic_budgets` has multiple rows per clinic+service_category. The `payer` column in budgets is always "Ticonderoga Health" — use `service_category` matching and pick the budget with closest `expected_units` to actual units.

**Rounding**: Dollars to 2 decimal places (`ROUND(x, 2)`). Percentages/ratios as decimals rounded to 4 places.

---

## Common Pitfalls

1. **State matching for rate schedules**: The `facilities` table uses `facility_id` (FACxxx), NOT `clinic_id` (CLNxxx). Encounters use `clinic_id`. Manually map clinic→state from the audit scope, or use CASE expressions when joining rate schedules.

2. **COB check ambiguity**: `authorization_requests.cob_primary_processed=1` does NOT guarantee COB is resolved. Also check `members.cob_primary_status`. Values of `"pending"` and `"primary_other_payer"` indicate unresolved COB.

3. **Duplicate authorization detection**: Check `existing_authorizations` for same `member_id` + same `cpt_code` with overlapping date ranges. Exclude entries where `original_case_id` matches the current case (self-referencing records are NOT duplicates).

4. **Gold card — servicing provider**: The servicing provider's `gold_card_active` status may also gate gold-card eligibility, not just the requesting provider. Check both.

5. **Appeal plan_type vs member plan_type**: The `appeals.plan_type` may differ from the member's actual enrollment plan type. Always use `members.plan_id → plans.plan_type` as the source of truth.

6. **Budget plan_type matching**: `clinic_budgets` has no `plan_type` column. When multiple budgets exist for the same clinic+service_category, use `expected_units` proximity to actual units as the selection heuristic.

7. **SLA day counting**: For business-day SLAs, shift weekend receipt dates to the next Monday. For calendar-day SLAs, add the number of days directly. The `state_sla_rules.day_type` column governs this.

8. **Evidence document staleness**: Even if clinical facts show `"met"`, check `evidence_documents.is_current` and the fact's `confidence_flag`. Stale or conflicting evidence may require MD escalation despite seemingly met criteria.

9. **Always use target_bucket filtering**: Every task provides a worklist with a batch name or target bucket. Always filter your entry table by this to avoid pulling in unrelated data.

10. **Rounding precision matters**: Financial tasks (004, 005) require precise rounding — dollars to 2 decimals, percentages/ratios to 4 decimals. Use SQL `ROUND()` for consistency.

---

## Output Convention: Always Sorted

When the answer template specifies case-level or medication-case-level rows, ALWAYS sort by the ID field in ascending order (`ORDER BY case_id` or `ORDER BY med_case_id`). Summary/aggregate sections should be separate from per-row sections.

---

## One-Join-at-a-Time Development

Build queries incrementally:
1. Start with the entry table filtered by the task's target scope
2. Join one related table at a time and verify row counts don't multiply unexpectedly
3. Check for unexpected JOIN explosions (e.g., rate_schedules multiplying rows due to missing state match)
4. Only aggregate after all joins are verified correct
5. Test with LIMIT 5 before removing the limit

---

## Quick Reference: Key ID Patterns

| Entity | ID Pattern | Example |
|---|---|---|
| Authorization cases | AUTHxxxxx | AUTH00001 |
| Medication cases | MEDxxxxx | MED00001 |
| Members | MBRxxxx | MBR0001 |
| Plans | PLNxxx | PLN001 |
| Providers (NPI) | 145xxxxxxx | 1450000000 |
| Facilities | FACxxx | FAC001 |
| Clinics | CLNxxx | CLN001 |
| Rate schedules | RATExxxxx | RATE00001 |
| Claim corrections | CORRxxxxxx | CORR000086 |
| Evidence documents | DOCxxxxx_x | DOC00007_1 |
| Existing authorizations | EXAxxxxx | EXA00001 |
| Criteria sources | SRCxxx | SRC003 |
| Assistance programs | APxxx | AP001 |
