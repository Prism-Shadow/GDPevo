# Skill: Payer Operations SQL Audit & Analytics

## Domain

Payer-side (health insurance) revenue cycle and utilization management operations covering:
- **Authorization intake** — waterfall eligibility checks on pre-auth requests
- **Clinical review** — nurse UM review slates with escalation posture
- **Pharmacy appeals** — dual-track medication appeal + manufacturer assistance routing
- **Reimbursement compliance** — paid-rate vs. benchmark variance analysis
- **Outpatient profitability** — payer-service cell margin analysis

---

## SOP: Step-by-Step Workflow

### Phase 1 — Orient & Scope

1. **Read the task prompt** (`input/prompt.txt`) for the role, date, and business context.
2. **Read the worklist/scope payload** (`input/payloads/`) to extract:
   - Target case IDs, clinics, plan types, service categories, date ranges
   - Materiality thresholds (min units, min amount, min %)
   - Active recovery statuses, if applicable
3. **Read the answer template** (`input/payloads/answer_template.json`) — this is your output contract. Every field name, type, and enum value matters. The evaluator validates against this schema.
4. **Note `environment_access.md`** for the `BASE_URL`, `/query` endpoint, and HTTP Basic Auth credentials. Never hardcode host/port.

### Phase 2 — Schema Discovery

Always start with these queries:

```sql
-- List all tables
SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;

-- Inspect each relevant table's columns
PRAGMA table_info(table_name);

-- Sample a few rows to understand data shape and ID formats
SELECT * FROM table_name LIMIT 3;
```

Key tables you will encounter (discover which exist for your task):
- `authorization_requests` — pre-auth cases with member_id, provider_id, service dates, urgency
- `authorization_line_items` — service lines with CPT/HCPCS, units, diagnosis
- `members`, `plans`, `providers`, `facilities` — master data
- `service_code_rules` — covered service / PA-required lookups
- `existing_authorizations` — previously approved auths (for duplicate detection)
- `state_sla_rules` — SLA calendar days by state + plan type + urgency
- `clinical_criteria` — evidence requirements by service category
- `clinical_evidence` — submitted clinical documents per auth
- `drug_requests`, `drug_policy_requirements`, `medication_trial_history` — pharmacy domain
- `appeal_intake_records`, `assistance_program_rules`, `household_financials` — pharmacy domain
- `encounters` — paid claims / encounter records
- `rate_schedules` — contracted benchmark rates by payer + plan + service
- `claim_corrections` — open recovery / underpayment correction records
- `clinic_costs`, `clinic_budgets` — cost and budget margin data by clinic

### Phase 3 — Join & Filter

- **Always filter to the target scope first** (case IDs, clinic IDs, date ranges from payload). Use `IN (...)` for case lists.
- **Join direction matters**: `LEFT JOIN` for optional related data (e.g., claim corrections may not exist for every encounter); `INNER JOIN` when the relationship is required.
- **Aggregation grouping**: Group by the finest granularity the output requires (case_id, clinic+quarter+payer+plan_type+service_category).
- **Date handling**: SQLite stores dates as strings; use `date()` for comparisons and `julianday()` for day arithmetic (SLA deadlines).

### Phase 4 — Apply Business Rules

#### Authorization Intake Waterfall
Check in this exact order; the **first failing check wins**:
1. **Active coverage** — member must have an active plan on the request date
2. **COB completion** — coordination of benefits must be resolved (COB status != `pending`)
3. **Covered service** — CPT/HCPCS must be in plan's covered service list
4. **Network** — provider must be in-network for the plan
5. **Service area** — facility must be in plan's service area
6. **PA required** — service must require prior auth for that plan type
7. **Retrospective submission** — request date must not be after service date (unless retro allowed)
8. **Duplicate** — no existing authorization for same member+service+date range
9. **Gold card** — if all pass, check gold-card eligibility (provider tier, plan type, service, no MD-required)

**Disposition mapping**: Each failing check maps to a specific disposition enum (e.g., `cob_completion` → `cob_hold`, `covered_service` → `noncovered_service_denial`). Find the exact mapping by reading the template's enum values — they are the authoritative list.

**Duplicate handling**: Match on member + CPT + date overlap against `existing_authorizations`. Return the matching existing auth IDs.

**SLA timing**: Compute `sla_due_at` from `request_date + sla_calendar_days` from `state_sla_rules` for the state+plan_type+urgency combination. Format as ISO-8601 `YYYY-MM-DDTHH:MM`.

**Provider item**: Check provider sanctions and credential status — flag if active sanctions or inactive credentials found.

**Notice required**: `true` for denials and halts; `false` for holds (COB). Check the template and gold patterns for the task's exact convention.

#### Clinical Review (Nurse UM)

- **Criteria source**: Map service category to the applicable criteria document (SRCxxx from `clinical_criteria`).
- **Nurse recommendation**: `approve_as_requested` when all criteria are clearly met with complete evidence; `escalate_to_md` otherwise.
- **MD escalation triggers**: experimental therapy, benefit exclusions, criteria not clearly met, adverse multiline requests, mandatory-MD services (e.g., certain DME).
- **Missing evidence keys**: Enumerate what required evidence is absent — `homebound_status`, `physician_plan`, `functional_limitation`, `measurable_progress`, `plan_of_care`, `not_experimental`, `standard_options_failed`.
- **P2P suitable**: `true` when criteria are close but evidence is incomplete — peer-to-peer could resolve it. `false` for MD-mandatory services or clearly failing cases.
- **Approved units**: Non-null only when approving; use `null` (not 0) when escalating.

#### Pharmacy Appeals (Dual Track)

Two independent assessments per medication case:

**Appeal track:**
- `eligibility_status`: `appeal_ready` (all policy requirements met), `appeal_incomplete` (missing policy reqs), `appeal_not_timely` (past deadline)
- `missing_policy_requirements`: From `drug_policy_requirements` — `diagnosis`, `step_therapy`, `tb_screen`, `topical_failure`, etc.
- `expedited_classification`: `expedited_accepted_72h` (urgent and complete), `expedited_requested_needs_evidence` (urgent but incomplete), `standard_30d`
- `filing_deadline`: Computed from denial date + regulatory window
- `deadline_status`: `timely_received` or `late_received`

**Assistance track:**
- Match drug to assistance program via `assistance_program_rules`
- Check eligibility: income thresholds, insurance type requirements (commercial vs government), required documents
- `blocking_reasons`: `income_over_program_limit`, `commercial_insurance_required`, `government_plan_excluded`, `denial_letter_missing`, `assistance_consent_missing`
- `program_owner`: `manufacturer_assistance_team` or `not_routed`

**Path separation**: `appeal_only`, `assistance_only`, `parallel_appeal_and_assistance`, `no_active_route`

#### Reimbursement Compliance

- **Paid vs. benchmark**: For each encounter, look up the applicable `rate_schedules` rate by payer + plan_type + CPT + date range. Compute `benchmark_amount = benchmark_per_unit * units`.
- **Variance**: `paid_amount - benchmark_amount`. Negative = underpayment.
- **Materiality filter**: Apply thresholds from audit_scope — `minimum_paid_units`, `minimum_underpayment_amount`, `minimum_underpayment_pct`. Only flag cells meeting ALL thresholds.
- **Recovery tracking**: Separate from paid-rate compliance. Sum open `claim_corrections` with status in `active_recovery_statuses`. The top recovery opportunity is the single largest `expected_recovery_amount` among open corrections.
- **Exclusion**: Count denied or unpaid encounters separately; exclude from paid analysis.
- **Compliance classification**: `material_underpayment` for flagged cells; `compliant` when no cells flagged; `high_review` for clinic-quarters with flagged cells.

#### Outpatient Profitability

- **Net revenue**: `paid_amount + open_recovery` (recovery from claim corrections)
- **Total cost**: `units * cost_per_unit` from `clinic_costs`
- **Net margin**: `net_revenue - total_cost`
- **Margin %**: `net_margin / net_revenue` — can be negative
- **Budget variance**: Compare `margin_pct` to `budget_margin_pct` from `clinic_budgets`. Classify as `major_shortfall`, `minor_shortfall`, `on_or_above_budget`.
- **Persistence**: Classify cells as `persistent` (recurring pattern) or `noise` (one-off, small sample).
- **Ranking**: Order loss drivers by `net_margin` ascending (most negative first).
- **Recommended actions**: `rate_floor_review` (renegotiate rates), `recover_and_rate_floor_review` (when open recoveries exist), `volume_review`, `cost_review`.

---

## Output Conventions (Universal)

| Convention | Rule |
|---|---|
| **Dollars** | Round to 2 decimal places (`ROUND(x, 2)`) |
| **Percentages** | Round to 4 decimal places as decimals (e.g., `-0.1594`, not `-15.94%`) |
| **Per-unit rates** | Round to 2 decimal places |
| **Sort order** | Ascending by case ID / clinic ID / med case ID — as specified in template |
| **Null vs zero** | Use `null` for "not applicable" (e.g., approved_units when escalating); use `0` or `0.0` for "none" |
| **Empty arrays** | Use `[]` not `null` when a list is expected but empty |
| **Enums** | Use exact string values from the answer template — these are validated as literals |
| **Date format** | ISO-8601 `YYYY-MM-DD` for dates, `YYYY-MM-DDTHH:MM` for timestamps |
| **Summary counts** | Derive from case-level results, never hardcode |

---

## SQL Patterns for This Domain

### Discovery
```sql
-- Always first
SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;
-- Then column details
PRAGMA table_info(authorization_requests);
-- Then sample
SELECT * FROM authorization_requests LIMIT 3;
```

### Date arithmetic (SQLite)
```sql
-- Add calendar days to a date
date(request_date, '+' || sla_calendar_days || ' days')
-- Date comparison
WHERE service_date BETWEEN '2025-01-01' AND '2025-03-31'
```

### Aggregation with materiality
```sql
SELECT payer, plan_type, service_category,
       COUNT(*) AS paid_encounters,
       SUM(units) AS paid_units,
       ROUND(SUM(paid_amount), 2) AS paid_amount,
       ROUND(SUM(benchmark_amount), 2) AS benchmark_amount
FROM ...
GROUP BY payer, plan_type, service_category
HAVING SUM(units) >= :min_units
   AND (SUM(benchmark_amount) - SUM(paid_amount)) >= :min_amount
   AND (SUM(benchmark_amount) - SUM(paid_amount)) / SUM(benchmark_amount) >= :min_pct
```

### Left join for optional relationships
```sql
-- claim_corrections are optional
SELECT e.*, COALESCE(SUM(c.expected_recovery_amount), 0) AS open_recovery
FROM encounters e
LEFT JOIN claim_corrections c
  ON e.encounter_id = c.encounter_id
 AND c.status IN ('open', 'pending documents', 'submitted')
GROUP BY e.encounter_id
```

### First-failing-check waterfall (use CASE with priority)
```sql
SELECT CASE
  WHEN coverage_active = 0 THEN 'active_coverage'
  WHEN cob_pending = 1     THEN 'cob_completion'
  WHEN covered = 0         THEN 'covered_service'
  WHEN in_network = 0      THEN 'network'
  WHEN in_service_area = 0 THEN 'service_area'
  WHEN pa_required = 0     THEN 'pa_required'
  WHEN is_retrospective = 1 THEN 'retrospective_submission'
  WHEN duplicate_count > 0 THEN 'duplicate_authorization'
  WHEN gold_card_eligible = 1 THEN 'none'
  ELSE 'none'
END AS first_failing_check
```

### Subquery for duplicate detection
```sql
SELECT a.case_id, GROUP_CONCAT(e.auth_id) AS duplicate_ids
FROM authorization_requests a
JOIN existing_authorizations e
  ON a.member_id = e.member_id
 AND a.cpt_code = e.cpt_code
 AND a.request_date <= e.auth_end_date
 AND a.request_date >= e.auth_start_date
WHERE a.case_id IN (:targets)
GROUP BY a.case_id
```

---

## Common Pitfalls

1. **Skipping schema discovery** — never assume table/column names. Always `PRAGMA table_info()`.
2. **Hardcoding URLs or ports** — always read from `environment_access.md` or the task prompt's `<TASK_ENV_BASE_URL>` placeholder. Never use `localhost`.
3. **Wrong rounding precision** — percentages to 4 decimals, dollars to 2 decimals. Off-by-one rounding fails validation.
4. **Using `null` where `[]` is expected** — empty arrays must be `[]`, not `null`, when the template expects a list.
5. **Approved units = 0 vs null** — `0` means "zero units approved"; `null` means "not applicable (escalated)". Get this wrong and validation fails.
6. **Missing the worklist filter** — queries must be scoped to the target case/clinic IDs from the payload. Unscoped queries produce wrong answers.
7. **Off-by-one in waterfall** — the intake check order is critical. Check in the exact sequence the template implies.
8. **Conflating appeal and assistance tracks** — pharmacy tasks have two independent assessments. Keep them separate; `path_separation` tells you which tracks are active.
9. **Forgetting HTTP Basic Auth** — every request to `/query` needs the `Authorization` header.
10. **Not reading the answer template before querying** — the template defines the output schema, including exact enum values. Query to fill the template, not the other way around.
11. **Using SQL functions SQLite doesn't support** — no `DATEDIFF`, no `DATEADD`. Use `julianday()` for day differences and `date(x, '+' || N || ' days')` for addition.
12. **Assuming every case has related records** — use `LEFT JOIN` for optional tables (corrections, evidence, trial history, assistance programs). `INNER JOIN` only when the relationship must exist.

---

## Quick Reference: Making HTTP SQL Queries

```bash
curl -s -X POST "${BASE_URL}/query" \
  -H "Content-Type: application/json" \
  -u "payer_ops_solver:revcycle_sql_014" \
  -d '{"sql": "SELECT name FROM sqlite_master WHERE type=\"table\" ORDER BY name", "params": []}'
```

- Use `-s` (silent) to suppress progress output; parse the JSON response with `jq` or equivalent.
- Escape double quotes inside the SQL string with backslashes, or use single quotes for the `-d` body.
- The response is JSON: `{"rows": [...], "columns": [...]}` or similar.

---

## Summary Checklist

- [ ] Read prompt, worklist/scope payload, answer template, environment_access.md
- [ ] Discover schema: list tables → inspect columns → sample rows
- [ ] Filter queries to target scope (case IDs, clinic IDs, date ranges)
- [ ] Build joins: INNER for required, LEFT for optional
- [ ] Apply business rules in the correct order (especially intake waterfall)
- [ ] Derive summary counts from case-level results (never hardcode)
- [ ] Round dollars to 2dp, percentages to 4dp
- [ ] Use exact enum strings from the answer template
- [ ] Sort results as specified (ascending case ID by default)
- [ ] Validate output against answer template structure before submitting
