---
name: sql-payer-ops
description: Use for payer-operations SQL tasks that require querying the shared SQLite service to produce JSON answers for utilization management intake, clinical review, medication appeals and assistance routing, reimbursement compliance, or rehab profitability analyses.
---

# SQL Payer Ops

## Operating Workflow

1. Read the task prompt, `environment_access.md`, every staged payload, and the answer template. Copy fixed constants from the payload/template, not from memory.
2. Use only the scope values provided in staged input files: explicit case IDs, medication case IDs, target buckets, clinics, periods, plan types, service categories, materiality thresholds, and active statuses. Do not inventory unrelated `target_bucket` values.
3. Query through the service described in `environment_access.md`. Do not hard-code the runtime host or port in code or final notes. Use read-only SQL.
4. Discover schema before calculating:

```sql
SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;
SELECT m.name AS table_name, p.*
FROM sqlite_master AS m
JOIN pragma_table_info(m.name) AS p
WHERE m.type='table'
ORDER BY m.name, p.cid;
```

5. Build CTEs at the required output grain, then assemble JSON manually against the template. Validate row ordering, enum spelling, summary counts, and rounding before finalizing.

Useful request pattern:

```bash
BASE=$(awk -F= '/GDPEVO_ENV_BASE_URL/{print $2}' environment_access.md)
AUTH_USER=$(awk -F'`' '/username/{print $2}' environment_access.md)
AUTH_PASS=$(awk -F'`' '/password/{print $2}' environment_access.md)
SQL="SELECT ..."
jq -nc --arg sql "$SQL" '{sql:$sql,params:[]}' \
  | curl -s -u "$AUTH_USER:$AUTH_PASS" -H 'Content-Type: application/json' -d @- "$BASE/query"
```

## Table Map

- UM intake: `authorization_requests`, `auth_lines`, `members`, `plans`, `providers`, `facilities`, `service_codes`, `existing_authorizations`, `state_sla_rules`.
- Clinical review: intake tables plus `criteria_sources`, `coverage_criteria`, `clinical_facts`, `evidence_documents`, `case_review_events`, `p2p_sessions`.
- Medication appeals: `medication_cases`, `members`, `plans`, `appeals`, `drug_policy_requirements`, `medication_trials`, `assistance_programs`, `household_financials`.
- Finance/reimbursement: `encounters`, `rate_schedules`, `claim_corrections`, `clinic_costs`, `clinic_budgets`.

## UM Intake Rules

Evaluate intake checks in this order unless the prompt overrides it:

1. `active_coverage`: requested service window must fall inside member coverage dates. Treat retro reinstatement fields as possible coverage evidence only if the dates support it.
2. `cob_completion`: hold when request/member COB indicators show pending, unprocessed, or otherwise incomplete primary-payer processing.
3. `covered_service`: any requested CPT with `service_codes.covered=0` is a noncovered-service denial.
4. `network`: requesting/servicing provider network failures matter unless an OON exception applies. Check plan network type and both NPIs.
5. `service_area`: facility must be inside service area.
6. `pa_required`: if no requested line needs PA and service is notification-only, close as notification-only.
7. `retrospective_submission`: `rendered_before_submission=1` halts after earlier checks pass.
8. `duplicate_authorization`: same member, same CPT, active existing auth, overlapping service dates.
9. `none`: eligible for gold-card or review routing.

Duplicate overlap idiom:

```sql
SELECT ar.case_id, group_concat(DISTINCT ea.existing_auth_id) AS duplicate_existing_auth_ids
FROM authorization_requests ar
JOIN auth_lines l ON l.case_id=ar.case_id
JOIN existing_authorizations ea
  ON ea.member_id=ar.member_id
 AND ea.cpt_code=l.cpt_code
 AND ea.status='active'
 AND NOT (date(ea.service_end)<date(ar.service_start)
          OR date(ea.service_start)>date(ar.service_end))
GROUP BY ar.case_id;
```

Gold-card auto-approval is reached only after intake checks pass. Require plan allowance, requesting provider gold-card status, no active sanctions/credential issue, no service gold-card exclusion, and no mandatory MD/vendor review. Otherwise set the most specific not-eligible reason. Provider follow-up items are only for requesting-provider active sanctions or inactive credentials.

Review queue routing: vendor/program fields on `service_codes` can map directly to queues such as imaging, DME, home care, or specialty review. Mandatory MD review routes to Medical Director when not externally delegated; otherwise use Nurse Clinical Review. Auto approvals and intake halts use the no-review queues required by the template.

SLA due time starts from `authorization_requests.receipt_timestamp`. Normalize urgency to `routine`, `urgent`, or `stat`; prefer `state_sla_rules` matching plan state and exact plan type, then `ALL`; fall back to plan SLA columns. Honor `day_type` for routine day math, and emit timestamps as `YYYY-MM-DDTHH:MM`.

## Clinical Review Rules

Scope cases from explicit IDs or the staged `authorization_requests.target_bucket`. Derive service category from `auth_lines` and plan type from member plan.

Choose the criteria source with the highest applicable precedence, but only among sources that actually have required criteria rows for the case service and plan:

```sql
WITH cases AS (...),
source_choice AS (
  SELECT c.case_id, cs.source_id,
         row_number() OVER (
           PARTITION BY c.case_id
           ORDER BY
             CASE WHEN cs.plan_type_filter=c.plan_type THEN 0
                  WHEN cs.plan_type_filter='ALL' THEN 1 ELSE 2 END,
             cs.precedence_rank,
             cs.effective_date DESC
         ) AS rn
  FROM cases c
  JOIN criteria_sources cs
    ON (cs.service_category_filter=c.service_category OR cs.service_category_filter='ALL')
   AND (cs.plan_type_filter=c.plan_type OR cs.plan_type_filter='ALL')
   AND date(cs.effective_date)<=date(:review_date)
  WHERE EXISTS (
    SELECT 1 FROM coverage_criteria cc
    WHERE cc.criteria_source_id=cs.source_id
      AND cc.service_category=c.service_category
      AND cc.is_required_for_approval=1
      AND (cc.plan_type_filter=c.plan_type OR cc.plan_type_filter='ALL')
  )
)
```

Missing evidence keys come from required `coverage_criteria` where no matching `clinical_facts` row exists, `fact_value` differs from `required_value`, confidence is low, or current-document rules in the prompt are not met. Preserve criterion-key spelling and produce an empty array when none are missing.

Nurse approval requires all required criteria satisfied and no MD/vendor escalation trigger. Requested units are the approved units when approving as requested. MD escalation counts must be grouped from final case-level rows, not raw joined rows. P2P suitability is separate from escalation; use prior adverse/request-more-info events and whether a P2P could supply new information.

## Medication Appeal And Assistance Rules

Keep payer appeal routing separate from manufacturer assistance routing.

Appeal workflow:

- Join `medication_cases` to `members`/`plans` for member plan type, and to `appeals` on `case_or_med_case_id` with medication subject.
- Filing deadline is usually adverse notice date plus the appeal window implied by the task or plan context; if no task-specific override appears, use the standard 60-day appeal window and label late receipts as `late_received`.
- `appeal_not_timely` outranks completeness. Otherwise, missing drug-policy requirements or missing required appeal intake facts produce `appeal_incomplete`; complete timely files are `appeal_ready`.
- Drug policy requirements match by drug and exact plan type or `ALL`. Use documented medication trials and other available facts to satisfy keys such as `diagnosis`, `step_therapy`, `tb_screen`, and `topical_failure`.
- Expedited classification: attestation plus supporting/new evidence is `expedited_accepted_72h`; attestation without evidence is `expedited_requested_needs_evidence`; no attestation is `standard_30d`.

Assistance workflow:

- Join `assistance_programs` by `drug_name` and `household_financials` by member.
- Blockers map directly to template keys: income over program FPL limit, commercial-insurance requirement unmet, government plan excluded, denial letter missing, consent missing.
- If no program or hard blockers remain, use `not_routed`; if assistance can proceed or needs manufacturer-team follow-up, use `manufacturer_assistance_team` per the template.
- `path_separation` is based on active appeal route and assistance route independently: appeal only, assistance only, parallel, or no active route.

If no FPL table is present, make the income-percent assumption explicit in working notes and apply it consistently; compare computed FPL percent to `assistance_programs.max_income_fpl`.

## Reimbursement Compliance Rules

Use the audit payload for clinic IDs, periods, materiality, and active recovery statuses. Do not mix compliance variance with recovery tracking.

Rate benchmark join:

```sql
SELECT e.*, r.rate_id, r.benchmark_rate,
       e.units * r.benchmark_rate AS benchmark_amount
FROM encounters e
JOIN rate_schedules r
  ON r.payer=e.payer
 AND r.plan_type=e.plan_type
 AND r.service_category=e.service_category
 AND r.cpt_code=e.cpt_code
 AND date(e.service_date) BETWEEN date(r.effective_start) AND date(r.effective_end);
```

For paid-rate compliance, include paid encounters/units where `paid_amount>0`; count denied or unpaid encounters separately. Compute:

- `benchmark_amount = SUM(units * benchmark_rate)`
- `variance_amount = paid_amount - benchmark_amount` as a signed value
- `variance_pct = variance_amount / benchmark_amount`
- material underpayment when paid units meet the minimum and positive shortfall `benchmark_amount - paid_amount` meets both dollar and percent thresholds

`rate_schedule_rate_ids` must be distinct and stable. Clinic-quarter totals roll up the same paid rows used for cells. `tracked_recovery_amount` and `top_recovery_opportunity` come only from `claim_corrections` with payload active statuses; choose the top opportunity by expected recovery, with deterministic tie-breakers such as deadline and encounter ID.

## Rehab Profitability Rules

Use the scope payload for analysis period, fiscal year, clinics, plan types, and service categories.

At payer-service grain:

- `paid_amount = SUM(encounters.paid_amount)` for scoped encounters.
- `open_recovery = SUM(claim_corrections.expected_recovery_amount)` for active/open recovery statuses only.
- `net_revenue = paid_amount + open_recovery`.
- `cost_per_unit = clinic_costs.direct_cost_per_unit + clinic_costs.allocated_overhead_per_unit`.
- `total_cost = units * cost_per_unit`.
- `net_margin = net_revenue - total_cost`.
- `margin_pct = net_margin / net_revenue` when revenue is nonzero.

`clinic_budgets` may be at payer/service grain rather than plan-type grain. Do not invent an unstated join key. If multiple budget rows exist for the output grain, aggregate expected revenue and use a revenue-weighted expected margin percent:

```sql
SUM(expected_net_revenue * expected_margin_pct) / SUM(expected_net_revenue)
```

Classify budget variance from final margins. If no explicit thresholds are provided, use `major_shortfall` for at least 10 percentage points below budget, `below_budget` for any deficit below budget, and `at_or_above_budget` otherwise. Projected improvement is the amount needed to reach budget margin:

```sql
MAX((budget_margin_pct * net_revenue) - net_margin, 0)
```

Rank loss drivers by most negative `net_margin`, then deterministic ties by clinic, plan type, and service category. Persistence should be supported by time-sliced evidence, typically shortfall in multiple quarters/months; otherwise use the task's available convention and note the assumption in working notes. Recommended payer actions should be controlled payer actions: rate-floor review for structural underpayment, claim-recovery push where open recoveries are material, and no action for cells at/above budget unless the template requires all cells.

## Output Conventions And Pitfalls

- Return exactly one JSON object and no explanatory text for task answers.
- Preserve all template keys. Use empty arrays instead of `null` for list fields; use `null` only where the template allows it, such as absent assistance program fields.
- Sort case rows by ascending case ID or med case ID. Sort clinic/quarter rows and variance rows deterministically using the prompt's grain.
- Round money, per-unit rates, and counts after aggregation: money/rates to 2 decimals, percent ratios as decimals to 4 decimals.
- Summaries must be computed from the final output rows, not from raw joins.
- De-duplicate one-to-many joins before aggregation. Pre-aggregate line items, criteria, corrections, and rate IDs in CTEs.
- Treat `ALL` filters as uppercase unless schema inspection shows otherwise.
- Watch signed underpayment values: materiality usually uses positive shortfall, while output variance is commonly signed `paid - benchmark`.
- Do not rely on answer-template example enum values as the full set; infer from prompt plus observed columns, but spell output enums exactly as the template requires.
