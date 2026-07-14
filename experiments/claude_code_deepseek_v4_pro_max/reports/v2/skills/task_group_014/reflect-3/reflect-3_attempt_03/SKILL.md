# Payer Operations SQL Skill

## When to Use
Any payer operations task involving authorization intake, clinical review, pharmacy appeals, reimbursement compliance, or outpatient profitability analysis against the payer operations SQL service.

## SQL Discovery Habits

### Schema Exploration
Always start with `SELECT name FROM sqlite_master WHERE type='table' ORDER BY name` to discover all 26 tables. Then `PRAGMA table_info(<name>)` on each relevant table before querying data. Never assume column names — verify with PRAGMA.

### Key Table Relationships
- `authorization_requests` ↔ `auth_lines` on `case_id` (one auth, many line items)
- `authorization_requests` → `members` on `member_id` → `plans` on `plan_id`
- `authorization_requests` → `providers` on `requesting_npi` and `servicing_npi`
- `authorization_requests` → `facilities` on `facility_id`
- `medication_cases` → `medication_trials` on `med_case_id`
- `medication_cases` → `appeals` on `case_or_med_case_id`
- `medication_cases` → `members` → `household_financials` on `member_id`
- `encounters` → `claim_corrections` on `encounter_id`
- `encounters` → `rate_schedules` matched on payer, plan_type, service_category, cpt_code, state, AND date range
- `coverage_criteria` → `criteria_sources` on `criteria_source_id`

### Filtering by Task Scope
Every task provides a target bucket or worklist. Always filter by `target_bucket`, `target_bucket` field, or explicit case ID lists. Never query unfiltered tables — the DB contains data for unrelated batches.

## Business Rules by Task Type

### Authorization Intake Audit (train_001 pattern)
**Check order matters.** The intake pipeline checks in this exact sequence:
1. `active_coverage` — member coverage_start/end must bracket request_date
2. `cob_completion` — check the auth record's `cob_primary_processed` field (auth-level, not member-level)
3. `covered_service` — all line-item CPT codes must have `service_codes.covered = 1`
4. `network` — requesting and servicing providers must have `network_status = 'in_network'`
5. `service_area` — facility `in_service_area` must be 1
6. `pa_required` — the service code must require PA (pa_required=1 means it proceeds)
7. `retrospective_submission` — `rendered_before_submission = 1` halts intake
8. `duplicate_authorization` — existing auth for same member, same CPT, overlapping dates, AND `original_case_id` differs from current case

**First failing check** determines the `intake_disposition`. The `duplicate_existing_auth_ids` should be reported even if an earlier check fails first.

**Gold card auto-approval** requires ALL of:
- Plan `gold_card_allowed = 1`
- Requesting provider `gold_card_active = 1`
- No service code has `gold_card_exclusion = 1`
- No mandatory MD review on any service code
- Provider has no sanctions, active credentials

**SLA rules**: Match plan state AND plan_type to `state_sla_rules`. Use `day_type` (calendar vs business). SLA due = receipt_timestamp + N days/hours based on urgency class.

**Review queue** for ready_for_review cases: use the service code's `external_vendor` or `specialty_program` to determine queue (e.g., "MedImage Review", "CareEquip Review", "HomeCare Review"). Gold card → "Auto Approval". Any intake halt → "No Review - Intake Halt".

### Clinical Review (train_002 pattern)
**Criteria source selection**: Use the highest-precedence `criteria_source` that has entries for the service category AND matches the plan type. For most plan types, `SRC003` (Ticonderoga Medical Policy, rank 2, ALL) is the default. Only use `SRC001` (CMS) for Medicare Advantage, `SRC002` (Medicaid) for Medicaid — but only if those sources actually have criteria for the service category. Check `coverage_criteria` to confirm.

**Criteria evaluation**: Check each `criterion_key` against `clinical_facts`. A criterion is "met" only when `fact_value = required_value`. Criteria with `fact_value = 'unclear'` or `'not_met'` are missing. Add them to `missing_evidence_keys`.

**MD escalation**: Required when any criterion is not met. The `md_escalation_reason_code` should reference the failing criterion key.

**P2P suitability**: True when evidence is conflicting or when the case involves experimental/non-standard therapy where provider discussion could clarify.

**Approved units**: Use the requested units from `auth_lines` when all criteria are met. When criteria are incomplete, exercise judgment — the field represents the nurse's preliminary recommendation.

### Pharmacy Appeal Routing (train_003 pattern)
**Appeal eligibility**: Check ALL drug policy requirements, not just the ones related to the original denial reason. Requirements with `source_rank=2` (like `tb_screen` for Remicade) are still required even if the original denial was for a rank-1 requirement.

**Appeal filing deadlines**: Standard = 60 calendar days from `adverse_notice_date`. Received within window → `timely_received`, after → `late_received`.

**Expedited classification**: `expedited_attestation=1` + `new_evidence_received=1` → `expedited_accepted_72h`. Attestation=1 but no new evidence → `expedited_requested_needs_evidence`. Attestation=0 → `standard_30d`.

**Assistance eligibility — check ALL conditions**:
1. Income: `annual_income / household_size` must be ≤ `max_income_fpl` × FPL for that household size
2. Insurance: `requires_commercial_insurance=1` means `insurance_type` must be "commercial"
3. Government exclusion: `excludes_government_plan=1` rejects government insurance types
4. Denial letter: `requires_denial=1` needs `has_denial_letter=1`
5. Consent: `assistance_consent_on_file=1` required

**Path separation**: Use `appeal_only` when appeal is the viable route (even if incomplete), `assistance_only` when only assistance applies, `parallel_appeal_and_assistance` when both are eligible, `no_active_route` when neither path is viable.

### Reimbursement Compliance (train_004 pattern)
**Rate matching is the hardest part.** For each encounter, find the rate_schedule where:
- `payer`, `plan_type`, `service_category`, `cpt_code` match exactly
- `state` matches the clinic's state (not the member's)
- `service_date` falls within `effective_start` ≤ date ≤ `effective_end`
- Use the CURRENT contract rate for the period (e.g., effective 2025-01-01 for 2025 dates)

**Benchmark amount** = `benchmark_rate` × encounter `units`. Sum per cell (clinic+quarter+payer+plan_type+service_category).

**Materiality thresholds** are applied per cell: all three must be met:
- `paid_units ≥ minimum_paid_units`
- `variance_amount ≥ minimum_underpayment_amount`
- `variance_pct ≥ minimum_underpayment_pct`

**Excluded encounters**: Count encounters where `paid_amount = 0` OR `denial_code IS NOT NULL` as `excluded_denied_or_unpaid_encounters`.

**Tracked recovery**: Sum `expected_recovery_amount` from `claim_corrections` with `status IN ('open', 'pending documents', 'submitted')` for ALL encounters in the period — including denied/unpaid ones.

**Rate IDs in flagged variances**: Include only the active/matching rate schedule IDs, not legacy or future ones. Use rate IDs for the specific payer+plan_type+service_category+CPT+state combination.

**Top recovery opportunity**: The single claim correction with the highest `expected_recovery_amount` among active corrections (`open`, `pending documents`, `submitted`). It may be for a denied encounter — that's valid.

### Outpatient Profitability (train_005 pattern)
**Cost computation**: Use `clinic_costs` for the matching `fiscal_year`, `clinic_id`, and `service_category`. Total cost per unit = `direct_cost_per_unit + allocated_overhead_per_unit`. Total cell cost = cost_per_unit × paid units.

**Budget matching**: The `clinic_budgets` table lacks a `plan_type` column but has multiple rows per clinic+payer+service_category. These rows correspond to plan types in a fixed order. Match carefully.

**Revenue**: Net revenue = `paid_amount` (from paid, non-denied encounters) + `open_recovery` (from active claim corrections).

**Margin**: Net margin = net revenue − total cost. Margin % = net margin / net revenue.

**Loss drivers**: Rank by net margin (most negative first). Top 3 are the ranked loss drivers.

**Budget variance**: Compare actual margin_pct to budget's `expected_margin_pct`. Negative actual margin with positive budget expectation → `major_shortfall`.

**Persistence**: Mark as `persistent` when the pattern appears across the full analysis period.

## Output Field Conventions

1. **Money**: Round to 2 decimal places. Use 0.0 for zero amounts, not null.
2. **Percentages/ratios**: Round to 4 decimal places (e.g., 0.1548, not 15.48%).
3. **Case ordering**: Sort by case ID ascending unless the template specifies otherwise.
4. **Empty arrays vs null**: Use `[]` for empty lists, not `null`.
5. **Dates**: Format as `YYYY-MM-DD` or `YYYY-MM-DDTHH:MM`.
6. **Boolean fields**: Use JSON `true`/`false`, not 0/1.
7. **Enum strings**: Use exact values from the answer template. Don't invent new enum values.
8. **Summary counts**: Must be internally consistent with case-level data. Double-check that sums match.

## Common Pitfalls

1. **COB check confusion**: The auth record's `cob_primary_processed` field is the intake check, not the member's `cob_primary_status`. These can differ.
2. **Service area vs facility state**: The facility's `in_service_area` flag is the check, not state matching between facility and member.
3. **Duplicate detection over-filtering**: Don't exclude duplicates just because `original_case_id` matches — only exclude when it matches the CURRENT case.
4. **Criteria source over-selection**: Don't use plan-type-specific sources (SRC001, SRC002) unless they actually have entries for the service category. SRC003 is the safe default.
5. **Missing secondary policy requirements**: Always check ALL requirements for a drug/service, including lower-ranked ones.
6. **Rate matching missing date ranges**: Always verify `service_date` falls within the rate schedule's effective period. Legacy rates with expired effective_end should not be used.
7. **All rate IDs vs active rate IDs**: Include only active/matching rate IDs in flagged variance cells, not every rate ID that ever existed for that combination.
8. **Recovery tracking scope**: Include active corrections for ALL encounters (paid and denied), not just paid ones.
9. **Budget plan-type matching**: The budget table lacks plan_type; the rows are ordered by plan type. Verify the ordering matches the expected plan type sequence.

## Concise SOP

1. **Read the prompt and payloads** — identify the task type, target scope, and answer template shape.
2. **Explore the schema** — PRAGMA table_info on every table mentioned or likely needed.
3. **Query target data** — filter by target_bucket, worklist, or explicit case IDs from the payload.
4. **Join related records** — members, plans, providers, facilities, service codes, existing auths, clinical facts, etc.
5. **Apply business rules in order** — for intake, follow the check sequence. For clinical, match criteria sources. For pharmacy, check all policy requirements. For reimbursement, match rates on payer+plan+CPT+state+date.
6. **Compute aggregates** — for compliance/profitability tasks, compute per-cell (clinic+quarter+payer+plan_type+service_category) aggregates before applying materiality thresholds.
7. **Validate internal consistency** — do summary counts match case-level data? Do totals add up?
8. **Format precisely** — round money to 2 decimals, percentages to 4 decimals, use exact template enum values.
9. **Submit and learn** — if scored feedback is available, identify which sections changed the score and refine only those dimensions.
