# Northstar Payer Operations — Database Schema

All tables live in a shared SQL environment. Access via `POST /sql/query` with bearer authentication.
Query the `/api/tables` endpoint to retrieve the current schema metadata at runtime.
Below is the canonical schema for the 19 known tables.

## Table Reference

### appeals

| Column | Type | Nullable | Key | Description |
|---|---|---|---|---|
| appeal_id | TEXT | Y | PK | Appeal identifier |
| case_id | TEXT | N | | Parent case |
| denial_date | TEXT | N | | Date of original denial |
| received_date | TEXT | N | | Appeal received date |
| appeal_type_requested | TEXT | N | | e.g. coverage_exception |
| appeal_path | TEXT | N | | standard_internal, expedited_internal, external_review |
| expedited_attestation | TEXT | N | | not_requested or provider_attested_serious_health_risk |
| appeal_deadline | TEXT | N | | YYYY-MM-DD |
| outcome | TEXT | Y | | open, approved, denied |
| owner | TEXT | Y | | appeals-rx, um-nurse, etc. |
| notes | TEXT | Y | | Free-text notes |

### assistance_screen

| Column | Type | Nullable | Key | Description |
|---|---|---|---|---|
| case_id | TEXT | Y | PK | Parent case |
| program_name | TEXT | N | | Vraylar Connect, Dupixent MyWay, etc. |
| income_percent_fpl | REAL | Y | | Income as percent of FPL |
| insurance_type | TEXT | N | | commercial, etc. |
| denial_required | INTEGER | N | | 1 = program requires a payer denial |
| denial_on_file | INTEGER | N | | 1 = denial is on file |
| missing_fields | TEXT | Y | | Comma-separated missing field names |
| assistance_status | TEXT | N | | eligible_ready, eligible_missing_information, not_eligible |

### authorizations

| Column | Type | Nullable | Key | Description |
|---|---|---|---|---|
| auth_id | TEXT | Y | PK | Authorization record ID |
| case_id | TEXT | N | | Parent case |
| auth_number | TEXT | Y | | e.g. NPA-2405014 |
| status | TEXT | N | | approved, denied, pending |
| approved_units | INTEGER | Y | | Approved service units |
| approved_start | TEXT | Y | | YYYY-MM-DD |
| approved_end | TEXT | Y | | YYYY-MM-DD |
| approved_cpt | TEXT | Y | | Comma-separated CPT codes |
| approved_modifier | TEXT | Y | | e.g. GP |
| denial_reason | TEXT | Y | | Reason when denied |

### cases

| Column | Type | Nullable | Key | Description |
|---|---|---|---|---|
| case_id | TEXT | Y | PK | Case identifier |
| member_id | TEXT | N | | Reference to members |
| provider_id | TEXT | N | | Reference to providers |
| request_type | TEXT | N | | prior_authorization, coverage_exception, claim_payment_review |
| service_domain | TEXT | N | | physical_therapy, cardiac_imaging, speech_therapy, etc. |
| policy_id | TEXT | N | | Reference to policies |
| request_date | TEXT | N | | YYYY-MM-DD |
| due_date | TEXT | N | | YYYY-MM-DD |
| current_stage | TEXT | N | | intake, nurse_review, appeals, medical_director, etc. |
| current_status | TEXT | N | | open, approved, denied, pended, paid_review, etc. |
| urgency | TEXT | N | | standard, routine, expedited |
| summary | TEXT | N | | Case summary text |

### case_criteria

| Column | Type | Nullable | Key | Description |
|---|---|---|---|---|
| case_id | TEXT | N | PK | Parent case |
| criterion_id | TEXT | N | PK | Reference to policy_criteria |
| result | TEXT | N | | met, not_met, unclear, not_applicable |
| evidence_fact_ids | TEXT | Y | | Comma-separated fact IDs from document_facts |
| gap_description | TEXT | Y | | What is missing or insufficient |
| reviewer_scope | TEXT | Y | | nurse_only or md_required |

### claims

| Column | Type | Nullable | Key | Description |
|---|---|---|---|---|
| claim_id | TEXT | Y | PK | Claim identifier |
| member_id | TEXT | N | | Reference to members |
| case_id | TEXT | Y | | Associated case |
| payer | TEXT | N | | Payer name |
| received_date | TEXT | N | | Claim received date |
| claim_status | TEXT | N | | paid, denied, pending |
| auth_number | TEXT | Y | | Authorization number on claim |
| billed_total | REAL | N | | Total billed amount (USD) |
| paid_total | REAL | N | | Total paid amount (USD) |

### claim_lines

| Column | Type | Nullable | Key | Description |
|---|---|---|---|---|
| claim_line_id | TEXT | Y | PK | Line identifier |
| claim_id | TEXT | N | | Parent claim |
| line_number | INTEGER | N | | 1-based line order |
| cpt_code | TEXT | N | | CPT/HCPCS code |
| modifier | TEXT | Y | | Line modifier, null if absent |
| units | INTEGER | N | | Service units |
| billed_amount | REAL | N | | Billed amount (USD) |
| paid_amount | REAL | N | | Paid amount (USD) |
| denial_code | TEXT | Y | | Denial code if applicable |
| service_date | TEXT | N | | YYYY-MM-DD |

### documents

| Column | Type | Nullable | Key | Description |
|---|---|---|---|---|
| document_id | TEXT | Y | PK | Document identifier |
| case_id | TEXT | N | | Parent case |
| document_type | TEXT | N | | initial_eval, plan_of_care, clinical_note, appeal_packet, etc. |
| document_date | TEXT | N | | Document date YYYY-MM-DD |
| received_date | TEXT | N | | Received date YYYY-MM-DD |
| source_system | TEXT | N | | e.g. provider_portal, payer_edi |
| is_current | INTEGER | N | | 1 = current/active, 0 = stale/superseded |
| title | TEXT | N | | Document title |
| summary | TEXT | N | | Document summary |

### document_facts

| Column | Type | Nullable | Key | Description |
|---|---|---|---|---|
| fact_id | TEXT | Y | PK | Fact identifier |
| document_id | TEXT | N | | Parent document |
| case_id | TEXT | N | | Parent case |
| fact_key | TEXT | N | | Fact name (diagnosis, functional_deficit, plan_of_care, etc.) |
| fact_value | TEXT | N | | Fact value |
| numeric_value | REAL | Y | | Numeric value when applicable |
| unit | TEXT | Y | | Unit of measure |
| supports_criteria | TEXT | Y | | Which criterion ID this fact supports |

### drug_trials

| Column | Type | Nullable | Key | Description |
|---|---|---|---|---|
| trial_id | TEXT | Y | PK | Trial record ID |
| case_id | TEXT | N | | Parent case |
| medication | TEXT | N | | Medication name (lowercase) |
| outcome | TEXT | N | | successful, failed, adverse_event, etc. |
| documented | INTEGER | N | | 1 = documentation on file, 0 = not documented |
| start_date | TEXT | Y | | YYYY-MM-DD |
| end_date | TEXT | Y | | YYYY-MM-DD |
| notes | TEXT | Y | | Free-text notes |

### members

| Column | Type | Nullable | Key | Description |
|---|---|---|---|---|
| member_id | TEXT | Y | PK | Member identifier |
| patient_name | TEXT | N | | Patient full name |
| dob | TEXT | N | | Date of birth |
| plan_id | TEXT | N | | Reference to plans |
| plan_type | TEXT | N | | commercial, medicaid, medicare_advantage, workers_comp |
| product | TEXT | N | | HMO, PPO, EPO |
| employer_group | TEXT | Y | | Employer group name |
| member_status | TEXT | N | | active, inactive |

### p2p_events

| Column | Type | Nullable | Key | Description |
|---|---|---|---|---|
| p2p_id | TEXT | Y | PK | P2P event identifier |
| case_id | TEXT | N | | Parent case |
| scheduled_at | TEXT | N | | Scheduled date-time |
| duration_minutes | INTEGER | N | | Duration |
| provider_argument | TEXT | Y | | Provider argument summary |
| new_information | TEXT | Y | | New info provided (none or free text) |
| outcome | TEXT | Y | | overturn_to_approval, uphold_intended_adverse_decision |
| final_status | TEXT | Y | | approved, denied |
| reviewer | TEXT | Y | | Medical director name |
| notes | TEXT | Y | | Free-text notes |

### payment_benchmarks

| Column | Type | Nullable | Key | Description |
|---|---|---|---|---|
| benchmark_id | TEXT | Y | PK | Benchmark identifier |
| payer | TEXT | N | | Payer name |
| plan_type | TEXT | N | | commercial, medicaid, etc. |
| service_domain | TEXT | N | | cardiac_imaging, etc. |
| cpt_code | TEXT | N | | CPT/HCPCS code |
| modifier | TEXT | Y | | Modifier, null if None |
| effective_start | TEXT | N | | YYYY-MM-DD |
| effective_end | TEXT | N | | YYYY-MM-DD |
| allowed_amount | REAL | N | | Allowed amount (USD) |
| source_name | TEXT | N | | Schedule name |
| source_version | TEXT | N | | Schedule version |

### plans

| Column | Type | Nullable | Key | Description |
|---|---|---|---|---|
| plan_id | TEXT | Y | PK | Plan identifier |
| payer_name | TEXT | N | | Payer |
| plan_type | TEXT | N | | commercial, medicaid, etc. |
| state | TEXT | N | | State code |
| network | TEXT | N | | Network name |
| effective_start | TEXT | N | | YYYY-MM-DD |
| effective_end | TEXT | N | | YYYY-MM-DD |
| notes | TEXT | Y | | Free-text notes |

### policies

| Column | Type | Nullable | Key | Description |
|---|---|---|---|---|
| policy_id | TEXT | Y | PK | Policy identifier |
| policy_name | TEXT | N | | Full policy name |
| version | TEXT | N | | Version string |
| effective_start | TEXT | N | | YYYY-MM-DD |
| effective_end | TEXT | N | | YYYY-MM-DD |
| precedence | INTEGER | N | | Numeric precedence (lower = higher priority) |
| summary | TEXT | N | | Policy summary |

### policy_criteria

| Column | Type | Nullable | Key | Description |
|---|---|---|---|---|
| criterion_id | TEXT | Y | PK | Criterion identifier |
| policy_id | TEXT | N | | Parent policy |
| criterion_key | TEXT | N | | Short key (e.g. ACTIVE, DEFICIT, DX, POC, UNITS) |
| criterion_text | TEXT | N | | Full criterion text |
| approval_required | INTEGER | N | | 1 = must be met for approval, 0 = informational |
| result_if_missing | TEXT | N | | Default result if no evidence: not_met, unclear |

### providers

| Column | Type | Nullable | Key | Description |
|---|---|---|---|---|
| provider_id | TEXT | Y | PK | Provider identifier |
| provider_name | TEXT | N | | Provider/group name |
| specialty | TEXT | N | | cardiology, orthopedics, etc. |
| npi | TEXT | N | | NPI number |
| phone | TEXT | Y | | Phone |
| fax | TEXT | Y | | Fax |
| organization | TEXT | Y | | Organization name |

### request_lines

| Column | Type | Nullable | Key | Description |
|---|---|---|---|---|
| line_id | TEXT | Y | PK | Line identifier |
| case_id | TEXT | N | | Parent case |
| cpt_code | TEXT | N | | CPT/HCPCS code |
| modifier | TEXT | Y | | Modifier |
| service_name | TEXT | N | | Service description |
| requested_units | INTEGER | N | | Requested units |
| requested_start | TEXT | Y | | YYYY-MM-DD |
| requested_end | TEXT | Y | | YYYY-MM-DD |
| diagnosis_codes | TEXT | Y | | Comma-separated ICD codes |
| billed_charge | REAL | N | | Billed charge (USD) |

### service_margin

| Column | Type | Nullable | Key | Description |
|---|---|---|---|---|
| month_id | TEXT | Y | PK | Row identifier |
| period | TEXT | N | | YYYY-MM |
| payer | TEXT | N | | Payer name |
| payer_segment | TEXT | N | | medicaid, commercial, workers_comp |
| service_domain | TEXT | N | | physical_therapy, speech_therapy, occupational_therapy |
| cpt_code | TEXT | N | | CPT code |
| visits | INTEGER | N | | Visit count |
| net_revenue | REAL | N | | Net revenue (USD) |
| variable_cost | REAL | N | | Variable cost (USD) |
| fixed_cost_allocated | REAL | N | | Fixed cost allocation (USD) |
| charge_sensitive | INTEGER | N | | 1 = charge sensitive, 0 = not |

## Foreign Key Conventions

- `cases.case_id` joins most other tables via their `case_id` column.
- `claims.claim_id` joins `claim_lines.claim_id`.
- `policies.policy_id` joins `policy_criteria.policy_id` and `cases.policy_id`.
- `members.plan_id` joins `plans.plan_id`.
- `members.member_id` joins `cases.member_id`.
- `cases.provider_id` joins `providers.provider_id`.

## Document Classification

Use `documents.is_current` to separate active evidence from stale records:
- `is_current = 1` — Current clinical record; may be used as evidence.
- `is_current = 0` — Stale/superseded export; exclude from the evidence set when using the `current_clinical_records_over_stale_export` precedence rule.

## Benchmark Selection

When repricing a claim, match `payment_benchmarks` by payer, plan_type, service_domain, cpt_code, and modifier. Narrow to the row whose `effective_start`/`effective_end` range covers the claim's service date. Prefer the source with the most recent effective date.
