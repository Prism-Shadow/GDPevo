# Northstar Schema Map

Full table catalog with join paths for the Northstar payer-operations environment.
Always confirm the live schema via GET /api/tables before using these references,
as column availability may vary.

## Core Entity Tables

### cases
Primary case record. The central entity for most work items.

| Column | Type | Notes |
|--------|------|-------|
| case_id | TEXT PK | Target business ID for most tasks |
| member_id | TEXT | Join to members.member_id |
| provider_id | TEXT | Join to providers.provider_id |
| request_type | TEXT | prior_authorization, peer_to_peer, coverage_exception, claim_payment_review |
| service_domain | TEXT | physical_therapy, cardiac_imaging, specialty_drug, speech_therapy, occupational_therapy, payment_review |
| policy_id | TEXT | Join to policies.policy_id and policy_criteria.policy_id |
| request_date | TEXT | YYYY-MM-DD |
| due_date | TEXT | YYYY-MM-DD |
| current_stage | TEXT | intake, nurse_review, medical_director, appeals, p2p, payment_review |
| current_status | TEXT | ready_for_determination, closed, approved, denied, needs_information, paid_review |
| urgency | TEXT | routine, standard, expedited |
| summary | TEXT | Human-readable case description |

### members
Patient/member demographics and coverage.

| Column | Type | Notes |
|--------|------|-------|
| member_id | TEXT PK | Join from cases.member_id or claims.member_id |
| patient_name | TEXT | Full name |
| dob | TEXT | YYYY-MM-DD |
| plan_id | TEXT | Join to plans.plan_id |
| plan_type | TEXT | commercial, medicaid, medicare_advantage, workers_comp |
| product | TEXT | Plan product name |
| employer_group | TEXT | May be null |
| member_status | TEXT | active, inactive, termed |

### providers
Rendering or referring provider.

| Column | Type | Notes |
|--------|------|-------|
| provider_id | TEXT PK | Join from cases.provider_id |
| provider_name | TEXT | Organization or individual name |
| specialty | TEXT | physical_therapy, cardiology, nuclear_medicine, psychiatry, dermatology, orthopedics, speech_therapy |
| npi | TEXT | National Provider Identifier |
| phone | TEXT | May be null |
| fax | TEXT | May be null |
| organization | TEXT | May be null |

### plans
Benefit plan and payer information.

| Column | Type | Notes |
|--------|------|-------|
| plan_id | TEXT PK | Join from members.plan_id |
| payer_name | TEXT | Payer organization name |
| plan_type | TEXT | commercial, medicaid, medicare_advantage, workers_comp |
| state | TEXT | Plan state |
| network | TEXT | Network identifier |
| effective_start | TEXT | YYYY-MM-DD |
| effective_end | TEXT | YYYY-MM-DD |
| notes | TEXT | May be null |

## Policy and Criteria Tables

### policies
Medical or pharmacy policy.

| Column | Type | Notes |
|--------|------|-------|
| policy_id | TEXT PK | Join from cases.policy_id |
| policy_name | TEXT | Policy title |
| version | TEXT | Version string |
| effective_start | TEXT | YYYY-MM-DD |
| effective_end | TEXT | YYYY-MM-DD |
| precedence | INTEGER | Numeric precedence (lower = higher priority) |
| summary | TEXT | Policy summary |

### policy_criteria
Individual criteria rules within a policy.

| Column | Type | Notes |
|--------|------|-------|
| criterion_id | TEXT PK | e.g., PT-ACTIVE, PET-IND |
| policy_id | TEXT | Join to policies.policy_id |
| criterion_key | TEXT | Short key like PT-ACTIVE |
| criterion_text | TEXT | Full criterion text |
| approval_required | INTEGER | 1 = must be met for approval |
| result_if_missing | TEXT | deny, pend, warn |

### case_criteria
Per-case criteria evaluation results.

| Column | Type | Notes |
|--------|------|-------|
| case_id | TEXT PK (part) | Join from target case |
| criterion_id | TEXT PK (part) | e.g., PT-ACTIVE, DRUG-FAILURES, PET-FACTOR |
| result | TEXT | met, not_met, unclear, not_applicable, partial |
| evidence_fact_ids | TEXT | Comma-separated list of fact_id references |
| gap_description | TEXT | May be null; explains why criterion is not met |
| reviewer_scope | TEXT | May be null; nurse, md, p2p |

## Request and Authorization Tables

### request_lines
Service lines requested for authorization.

| Column | Type | Notes |
|--------|------|-------|
| line_id | TEXT PK | Unique line identifier |
| case_id | TEXT | Join from target case |
| cpt_code | TEXT | CPT or HCPCS code |
| modifier | TEXT | May be null |
| service_name | TEXT | Human-readable service description |
| requested_units | INTEGER | Units requested |
| requested_start | TEXT | YYYY-MM-DD, may be null |
| requested_end | TEXT | YYYY-MM-DD, may be null |
| diagnosis_codes | TEXT | Comma-separated, may be null |
| billed_charge | REAL | Billed amount in USD |

### authorizations
Authorization decisions linked to cases.

| Column | Type | Notes |
|--------|------|-------|
| auth_id | TEXT PK | Authorization record ID |
| case_id | TEXT | Join from target case |
| auth_number | TEXT | e.g., NPA-2405014 |
| status | TEXT | approved, denied, pended, draft |
| approved_units | INTEGER | May be null |
| approved_start | TEXT | YYYY-MM-DD, may be null |
| approved_end | TEXT | YYYY-MM-DD, may be null |
| approved_cpt | TEXT | Comma-separated CPT list, may be null |
| approved_modifier | TEXT | May be null |
| denial_reason | TEXT | May be null |

## Clinical Evidence Tables

### documents
Clinical documents attached to a case.

| Column | Type | Notes |
|--------|------|-------|
| document_id | TEXT PK | e.g., DOC-TR-001-EVAL |
| case_id | TEXT | Join from target case |
| document_type | TEXT | eval, poc, progress_note, cardiology_report, export_batch |
| document_date | TEXT | YYYY-MM-DD |
| received_date | TEXT | YYYY-MM-DD |
| source_system | TEXT | provider_portal, fax, export_batch, emr |
| is_current | INTEGER | 1 = current/active, 0 = stale/superseded |
| title | TEXT | Document title |
| summary | TEXT | Document summary |

### document_facts
Structured clinical facts extracted from documents.

| Column | Type | Notes |
|--------|------|-------|
| fact_id | TEXT PK | Referenced by case_criteria.evidence_fact_ids |
| document_id | TEXT | Join to documents.document_id |
| case_id | TEXT | Join from target case |
| fact_key | TEXT | Fact label (e.g., functional_deficit, diagnosis, plan_of_care) |
| fact_value | TEXT | Fact value |
| numeric_value | REAL | May be null |
| unit | TEXT | May be null |
| supports_criteria | TEXT | Comma-separated criterion IDs this fact supports |

## Pharmacy-Specific Tables

### drug_trials
Medication trial history for pharmacy appeals.

| Column | Type | Notes |
|--------|------|-------|
| trial_id | TEXT PK | e.g., TRIAL-TR-002-1 |
| case_id | TEXT | Join from target case |
| medication | TEXT | Lowercase drug name |
| outcome | TEXT | failed, intolerable, ineffective, unknown, pending, partial |
| documented | INTEGER | 1 = documented in record, 0 = undocumented |
| start_date | TEXT | YYYY-MM-DD, may be null |
| end_date | TEXT | YYYY-MM-DD, may be null |
| notes | TEXT | May be null |

### appeals
Appeal records for coverage denials.

| Column | Type | Notes |
|--------|------|-------|
| appeal_id | TEXT PK | e.g., APL-TR-002 |
| case_id | TEXT | Join from target case |
| denial_date | TEXT | YYYY-MM-DD |
| received_date | TEXT | YYYY-MM-DD |
| appeal_type_requested | TEXT | coverage_exception, medical_necessity |
| appeal_path | TEXT | standard_internal, expedited_internal, external_review |
| expedited_attestation | TEXT | true or false (string) |
| appeal_deadline | TEXT | YYYY-MM-DD |
| outcome | TEXT | May be null |
| owner | TEXT | appeals-rx, um-nurse, medical-director, payment-integrity, member-services |
| notes | TEXT | May be null |

### assistance_screen
Manufacturer assistance program screening.

| Column | Type | Notes |
|--------|------|-------|
| case_id | TEXT PK | Join from target case |
| program_name | TEXT | Vraylar Connect, Dupixent MyWay, Humira Complete |
| income_percent_fpl | REAL | Income as percentage of federal poverty level, may be null |
| insurance_type | TEXT | commercial, medicaid, medicare |
| denial_required | INTEGER | 1 = denial on file required |
| denial_on_file | INTEGER | 1 = denial is on file |
| missing_fields | TEXT | Comma-separated list of missing field names |
| assistance_status | TEXT | eligible_ready, eligible_missing_information, not_eligible, not_applicable |

## Payment Integrity Tables

### claims
Paid claims for payment review.

| Column | Type | Notes |
|--------|------|-------|
| claim_id | TEXT PK | Target ID for claim repricing tasks |
| member_id | TEXT | Join to members.member_id |
| case_id | TEXT | May be null; join to cases.case_id |
| payer | TEXT | Payer name |
| received_date | TEXT | YYYY-MM-DD |
| claim_status | TEXT | paid, denied, pending |
| auth_number | TEXT | May be null |
| billed_total | REAL | Total billed amount |
| paid_total | REAL | Total paid amount |

### claim_lines
Individual lines within a claim.

| Column | Type | Notes |
|--------|------|-------|
| claim_line_id | TEXT PK | e.g., CL-TR-003-1 |
| claim_id | TEXT | Join from target claim |
| line_number | INTEGER | Claim line order (1-based) |
| cpt_code | TEXT | CPT/HCPCS code |
| modifier | TEXT | May be null |
| units | INTEGER | Service units |
| billed_amount | REAL | Billed amount for this line |
| paid_amount | REAL | Paid amount for this line |
| denial_code | TEXT | May be null |
| service_date | TEXT | YYYY-MM-DD |

### payment_benchmarks
Rate schedules for payment comparison.

| Column | Type | Notes |
|--------|------|-------|
| benchmark_id | TEXT PK | e.g., BM-TR-003-78452 |
| payer | TEXT | Payer name |
| plan_type | TEXT | commercial, medicaid, medicare_advantage, workers_comp |
| service_domain | TEXT | cardiac_imaging, physical_therapy, etc. |
| cpt_code | TEXT | CPT/HCPCS code |
| modifier | TEXT | May be null |
| effective_start | TEXT | YYYY-MM-DD |
| effective_end | TEXT | YYYY-MM-DD |
| allowed_amount | REAL | Allowed amount per unit |
| source_name | TEXT | Schedule name (e.g., Northstar Commercial Imaging Schedule) |
| source_version | TEXT | Version (e.g., 2026Q2) |

## Peer-to-Peer Table

### p2p_events
Peer-to-peer discussion records.

| Column | Type | Notes |
|--------|------|-------|
| p2p_id | TEXT PK | e.g., P2P-TR-004-E1 |
| case_id | TEXT | Join from target case |
| scheduled_at | TEXT | ISO datetime |
| duration_minutes | INTEGER | Discussion length |
| provider_argument | TEXT | May be null; provider clinical argument |
| new_information | TEXT | May be null; new patient-specific info disclosed |
| outcome | TEXT | overturned, upheld, may be null |
| final_status | TEXT | approved, denied, may be null |
| reviewer | TEXT | Medical director name, may be null |
| notes | TEXT | May be null |

## Margin Queue Table

### service_margin
Monthly margin data by payer segment, service domain, and CPT.

| Column | Type | Notes |
|--------|------|-------|
| month_id | TEXT PK | e.g., SM-TR-005-MCD |
| period | TEXT | YYYY-MM |
| payer | TEXT | Payer name |
| payer_segment | TEXT | medicaid, commercial, workers_comp |
| service_domain | TEXT | physical_therapy, speech_therapy, occupational_therapy |
| cpt_code | TEXT | CPT code |
| visits | INTEGER | Visit count for the period |
| net_revenue | REAL | Revenue in USD |
| variable_cost | REAL | Variable cost in USD |
| fixed_cost_allocated | REAL | Allocated fixed cost in USD |
| charge_sensitive | INTEGER | 1 = charge sensitive, 0 = not |

## Join Path Quick Reference

| From | To | Via |
|------|----|-----|
| cases | members | cases.member_id = members.member_id |
| cases | providers | cases.provider_id = providers.provider_id |
| cases | policies | cases.policy_id = policies.policy_id |
| cases | policy_criteria | cases.policy_id = policy_criteria.policy_id |
| cases | case_criteria | cases.case_id = case_criteria.case_id |
| cases | request_lines | cases.case_id = request_lines.case_id |
| cases | documents | cases.case_id = documents.case_id |
| cases | document_facts | cases.case_id = document_facts.case_id |
| cases | authorizations | cases.case_id = authorizations.case_id |
| cases | drug_trials | cases.case_id = drug_trials.case_id |
| cases | appeals | cases.case_id = appeals.case_id |
| cases | assistance_screen | cases.case_id = assistance_screen.case_id |
| cases | p2p_events | cases.case_id = p2p_events.case_id |
| members | plans | members.plan_id = plans.plan_id |
| document_facts | documents | document_facts.document_id = documents.document_id |
| claims | claim_lines | claims.claim_id = claim_lines.claim_id |
| claims | members | claims.member_id = members.member_id |
| claims | cases | claims.case_id = cases.case_id |
| claims | authorizations | claims.auth_number = authorizations.auth_number |
