# Payer Operations SQL Skill

## Environment Setup

- **Endpoint**: `{ENV_BASE_URL}/query` — submit read-only SQL via HTTP POST.
- **Request shape**: `{"sql": "<query>", "params": []}` (JSON body).
- **Auth**: HTTP Basic Auth. Credentials are provided in `environment_access.md` — read them from there each session; do not hard-code.
- **No local DB**: Do not assume a local SQLite file. Every query goes through the HTTP service.

## SOP: Solving a Payer Ops SQL Task

### Phase 1 — Orient

1. **Read the prompt** to identify the **role** (intake lead, nurse reviewer, pharmacy coordinator, revenue-cycle analyst, rehab analyst) and the **type of output** expected.
2. **Read `input/payloads/answer_template.json`** — this IS the output schema. Every key, enum value, and nesting shape is specified. Your final output must match the template structure exactly, with real values substituted in.
3. **Read the worklist/scope payload** (named `worklist.json`, `worklist_memo.json`, `worklist_scope.json`, `audit_scope.json`, etc.). It provides:
   - Target case IDs (usually `target_case_ids`, `medication_case_ids`, etc.)
   - Filter scopes (clinics, plan types, service categories, date ranges, materiality thresholds)
   - A `case_id_source` for filtering (e.g. `"authorization_requests.target_bucket"` — this means `WHERE target_bucket = '<worklist_label>'`)

### Phase 2 — Discover Schema

4. **List all tables**: `SELECT name FROM sqlite_master WHERE type='table' ORDER BY name`
5. **Inspect table columns**: `PRAGMA table_info(<table>)` for every table that seems relevant. Pay attention to:
   - Which columns are foreign keys joining to other tables
   - TEXT vs INTEGER vs REAL types (affects filtering and arithmetic)
   - Date/time columns (often TEXT in `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM` format)

### Phase 3 — Build Queries Incrementally

6. **Filter to target cases first**. Use `WHERE case_id IN (...)` or `WHERE target_bucket = '...'` per the worklist. Verify you get the expected number of rows before joining.
7. **Join outward**, one table at a time, verifying row counts don't explode:
   - Member/patient demographics: join on `member_id`
   - Plan/product details: join on `plan_id`
   - Provider/facility: join on `provider_id` or `facility_id`
   - Service lines: join on `case_id`/`auth_id` — watch for one-to-many; aggregate or pick the first line if the template expects one row per case
   - Rules/reference tables: join on codes (service codes, CPT codes, diagnosis codes)

### Phase 4 — Apply Business Rules

Business rules are encoded in **join conditions** and **CASE expressions**. Do not guess — let the data tell you:

- For each check/enum in the template, query the relevant column and inspect its distinct values: `SELECT DISTINCT <col> FROM <table> WHERE <target filter>`.
- Trace foreign-key chains to find the rule that applies to a given case. Example: `authorization_requests → plans → state_sla_rules` (join on state + plan_type + product_line).
- When a template has a closed enum (e.g. `first_failing_check`), the order of checks matters — failures earlier in the chain short-circuit later checks. Use a `CASE WHEN` ladder ordered by business priority (coverage before network before service before PA, etc.).
- For timeliness (appeal deadlines, SLA due dates): compute from the submission date plus business days per the applicable rule. Use calendar days unless the rule says "business days."

### Phase 5 — Assemble Output

8. **Sort case rows by case ID ascending** — nearly every template requires this.
9. **Round money and per-unit rates to 2 decimal places**, percentages to 4 decimal places (as decimals, e.g. 0.1594 not 15.94%).
10. **Compute summary aggregations** from the case-level data (counts, sums). Do NOT re-query — derive summaries from the same rows you already produced. This ensures consistency.
11. **Fill in every template field** — even fields like `duplicate_existing_auth_ids` that default to `[]`. Use `null` (not the string `"null"`) for absent numeric values like `approved_units` when a case is not approved.

## Table Usage Guide

These tables recur across task variants. When the prompt mentions them, here is what they typically provide:

| Table | Typical Columns | When Used |
|---|---|---|
| `authorization_requests` | case_id, member_id, plan_id, provider_id, facility_id, request_date, urgency, target_bucket, status | Auth intake, clinical review |
| `authorization_lines` / `service_lines` | line_id, case_id, service_code, cpt_code, units, requested_date | Line-item detail for auth cases |
| `members` | member_id, name, dob, state, gender | Member demographics, state for SLA lookup |
| `plans` | plan_id, plan_name, plan_type (Commercial/Medicaid/Medicare Advantage/Exchange/Dual Eligible), product_line, state | Plan classification, SLA, gold-card eligibility |
| `providers` | provider_id, name, npi, state, sanction_status, credential_status | Provider checks (sanctions, credentials) |
| `facilities` | facility_id, name, state, network_status | Network and service-area checks |
| `service_code_rules` | service_code, category, requires_pa, covered_service, gold_card_eligible | Service-level gate checks |
| `existing_authorizations` | existing_auth_id, member_id, service_code, status, start_date, end_date | Duplicate detection |
| `state_sla_rules` | state, plan_type, product_line, urgency, sla_days, sla_calendar_type | SLA deadline computation |
| `clinical_criteria` / `criteria_sources` | criteria_id, service_category, evidence_keys, criteria_source_id | Clinical review criteria matching |
| `review_events` | review_id, case_id, reviewer_role, recommendation, review_date | Prior review history |
| `medication_requests` / `drug_requests` | med_case_id, member_id, drug_name, plan_id, denial_date, request_date | Pharmacy appeals |
| `drug_policies` / `medication_policies` | drug_name, plan_type, policy_requirements (step_therapy, tb_screen, etc.) | Policy requirement checks |
| `appeal_intake` / `appeal_records` | appeal_id, med_case_id, filing_date, status | Appeal timeliness and status |
| `assistance_programs` | program_id, drug_name, income_limit, insurance_required, form_name | Manufacturer assistance routing |
| `household_financials` | member_id, household_income, household_size | Income vs. program limits |
| `medication_trials` | member_id, drug_class, trial_drug, trial_date, outcome | Step-therapy verification |
| `encounters` | encounter_id, clinic_id, payer, plan_type, service_category, cpt_code, units, paid_amount, service_date, denial_code, status | Reimbursement compliance, profitability |
| `rate_schedules` | rate_id, payer, plan_type, service_category, cpt_code, contracted_rate, effective_start, effective_end | Benchmark rate comparison |
| `claim_corrections` | correction_id, encounter_id, correction_type, expected_recovery_amount, status, deadline | Recovery tracking |
| `clinic_costs` | clinic_id, service_category, cost_per_unit, effective_date | Cost allocation |
| `clinic_budgets` | clinic_id, plan_type, service_category, budget_margin_pct, fiscal_year | Budget variance analysis |

## Key Business Rules by Domain

### Authorization Intake
- **Check order** (short-circuit): active coverage → COB completion → covered service → network → service area → PA required → retrospective submission → duplicate → gold card.
- **Duplicate detection**: same member + same service_code + overlapping date range with an existing auth that is active/approved.
- **Gold card**: requires plan gold-card eligible AND provider gold-card eligible AND service eligible AND no MD-required flag. If any factor fails, gold card is not eligible for that specific reason.
- **SLA due date**: submission_date + sla_days from the matching `state_sla_rules` row (join on state + plan_type + product_line + urgency). If `sla_calendar_type = "business"`, skip weekends and a fixed holiday set; if `"calendar"`, count consecutive days.
- **Provider items**: check `providers.sanction_status` for active sanctions; check `providers.credential_status` for inactive credentials.
- **Notice required**: true for any denial or halt disposition (not for approvals/gold-card).

### Clinical Review
- **Criteria source matching**: join service_category from the auth line to `criteria_sources` to find the applicable `criteria_source_id`.
- **Nurse recommendation**: `approve_as_requested` when all evidence keys are satisfied, criteria clearly met, and no benefit-exclusion rules apply. Otherwise `escalate_to_md`.
- **MD escalation reasons**: `benefit_exclusion_or_mandatory_md` (experimental/investigational, cosmetic), `criteria_not_clearly_met` (evidence gaps), `adverse_multiline_request` (multiple service lines with conflicting or high-risk patterns).
- **P2P suitable**: true only when the gap is a clinical judgment call (missing evidence that a peer discussion could resolve), not for bright-line exclusions.
- **Approved units**: number of units the nurse would approve; `null` when escalating to MD (not the nurse's decision).

### Pharmacy Appeals
- **Appeal eligibility**: check if all `drug_policies.policy_requirements` are met. If any are missing, `appeal_incomplete` with those keys listed. If all met, `appeal_ready`.
- **Appeal timeliness**: `filing_date` vs. `denial_date` + appeal window (typically 180 calendar days for standard, varies by plan). `timely_received` if within window.
- **Expedited classification**: `expedited_accepted_72h` if the request qualifies and all evidence is present. `expedited_requested_needs_evidence` if expedited is requested but evidence incomplete. `standard_30d` otherwise.
- **Assistance eligibility**: join to `assistance_programs` on drug_name. Check:
  - `household_income ≤ program.income_limit` (else `income_over_program_limit`)
  - `plan_type` matches `program.insurance_required` (else `commercial_insurance_required` or `government_plan_excluded`)
  - Required documents (denial letter, consent form) are present
- **Path separation**: `appeal_only`, `assistance_only`, `parallel_appeal_and_assistance`, or `no_active_route`.

### Reimbursement Compliance
- **Benchmark amount** = `units × contracted_rate` from the matching `rate_schedules` row (join on payer + plan_type + service_category + cpt_code, with service_date inside effective range).
- **Variance** = `paid_amount − benchmark_amount`. Negative = underpayment.
- **Materiality filter**: only flag cells where `paid_units ≥ minimum_paid_units` AND `|variance_amount| ≥ minimum_underpayment_amount` AND `|variance_pct| ≥ minimum_underpayment_pct`.
- **Compliance classification**: `material_underpayment` when all materiality thresholds are crossed and variance is negative. `high_review` for clinic-quarter when ≥1 cell is flagged. `compliant` otherwise.
- **Top recovery opportunity**: max `expected_recovery_amount` from open `claim_corrections` (status in `active_recovery_statuses`) within the audit period.
- **Excluded encounters**: denied or unpaid encounters (status ≠ 'paid') are counted but excluded from paid aggregates.

### Outpatient Profitability
- **Net revenue** = `paid_amount + open_recovery` (open claim corrections for that payer-service cell).
- **Total cost** = `units × cost_per_unit` from `clinic_costs` (join on clinic_id + service_category).
- **Net margin** = `net_revenue − total_cost`.
- **Margin percentage** = `net_margin / net_revenue` (can be negative; use the same formula consistently).
- **Budget variance**: compare `margin_pct` to `clinic_budgets.budget_margin_pct`. `major_shortfall` when actual is materially below budget. `on_or_above_budget` when at or above.
- **Persistence**: when a cell appears in prior-period data with the same shortfall pattern, classify as `persistent`. Low-volume cells with erratic swings are `noise`. Cells at/above budget are `acceptable`.
- **Ranked loss drivers**: order by `net_margin` ascending (most negative first), pick top 3.
- **Projected improvement**: amount needed to bring `net_margin` to meet `budget_margin_pct × net_revenue`. If recovery opportunities exist, incorporate them into the recommendation.

## Output Conventions (All Tasks)

| Convention | Rule |
|---|---|
| Money ($) | Round to 2 decimal places |
| Per-unit rates | Round to 2 decimal places |
| Percentages / ratios | Round to 4 decimal places, expressed as decimals (e.g. -0.1594, not -15.94%) |
| Case ordering | Ascending by case ID (string sort, typically zero-padded like AUTH00001) |
| Empty arrays | Use `[]`, not `null` |
| Missing numeric values | Use `null` (JSON null), not `0` |
| Date strings | `YYYY-MM-DD` for dates, `YYYY-MM-DDTHH:MM` for datetimes |
| Enum values | Match the template exactly (snake_case, exact strings) |

## Common Pitfalls

1. **Not reading the template first** — the template tells you every field, enum value, and structure. Read it before writing any SQL.
2. **Forgetting the worklist filter** — always scope to the target case IDs or target_bucket. Unfiltered queries return data for cases not in scope.
3. **One-to-many join explosions** — `authorization_requests → authorization_lines` is one-to-many. If the template expects one row per case, either pick the first line or aggregate. Always verify row counts after each join.
4. **Date range matching for rate schedules** — `rate_schedules` are effective-dated. Join with `service_date BETWEEN effective_start AND effective_end`, not just on payer/plan/code.
5. **Mixing up plan_type and product_line** — `plan_type` (Commercial, Medicaid, Medicare Advantage, Exchange) is different from `product_line` (HMO, PPO, EPO). SLA rules may key on either or both.
6. **Using wrong SLA calendar** — check `sla_calendar_type` before computing. "business" days skip weekends and holidays; "calendar" days don't.
7. **Not handling nulls in arithmetic** — `paid_amount + open_recovery` where `open_recovery` is null should use `COALESCE(open_recovery, 0)`.
8. **Hard-coding credentials or URLs** — always read from `environment_access.md` or the prompt's `<TASK_ENV_BASE_URL>` placeholder.
9. **Skipping schema exploration** — table schemas vary between task variants. Always run `PRAGMA table_info()` on new tables; don't assume column names from a previous task.
10. **Re-querying for summaries** — derive summary counts/sums from the case-level results in application code, not via separate SQL queries. This prevents drift between detail and summary.
11. **Rounding too early** — keep full precision through intermediate calculations. Only round at the final output step.
12. **Assuming sorted results from SQL** — always add `ORDER BY case_id ASC` (or `ORDER BY med_case_id ASC`). SQLite does not guarantee insertion order.
