# Northstar Payer Operations - Database Schema

Complete table catalog for the Northstar SQLite environment. All tables are read-only.

## Table Index

| Table | Purpose | Primary Key |
|---|---|---|
| `cases` | Prior auth, appeal, claim, and P2P case records | `case_id` |
| `members` | Member demographics and plan enrollment | `member_id` |
| `providers` | Rendering and referring providers | `provider_id` |
| `plans` | Plan product and network definitions | `plan_id` |
| `request_lines` | Requested service lines on a case | `line_id` |
| `policies` | Medical and coverage policies | `policy_id` |
| `policy_criteria` | Individual criteria within a policy | `criterion_id` |
| `case_criteria` | Criteria evaluation results for a case | `(case_id, criterion_id)` |
| `documents` | Clinical and administrative documents | `document_id` |
| `document_facts` | Extracted discrete facts from documents | `fact_id` |
| `authorizations` | Authorization records tied to cases | `auth_id` |
| `appeals` | Appeal intake and tracking records | `appeal_id` |
| `drug_trials` | Medication trial history for drug appeals | `trial_id` |
| `assistance_screen` | Manufacturer assistance program screening | `case_id` |
| `p2p_events` | Peer-to-peer discussion events | `p2p_id` |
| `claims` | Paid claim headers | `claim_id` |
| `claim_lines` | Individual line items on a claim | `claim_line_id` |
| `payment_benchmarks` | Allowable amount schedules by CPT/modifier | `benchmark_id` |
| `service_margin` | Monthly therapy revenue and cost data | `month_id` |

## Column Definitions

### cases

| Column | Type | Notes |
|---|---|---|
| `case_id` | TEXT PK | Business identifier |
| `member_id` | TEXT | Links to members |
| `provider_id` | TEXT | Links to providers |
| `request_type` | TEXT | prior_authorization, coverage_exception, claim_payment_review, peer_to_peer |
| `service_domain` | TEXT | physical_therapy, speech_therapy, occupational_therapy, specialty_drug, cardiac_imaging |
| `policy_id` | TEXT | Links to policies |
| `request_date` | TEXT | YYYY-MM-DD |
| `due_date` | TEXT | YYYY-MM-DD |
| `current_stage` | TEXT | nurse_review, appeals, payment_integrity, p2p_review, finance_review |
| `current_status` | TEXT | ready_for_determination, packet_incomplete, needs_repricing, p2p_complete, queued |
| `urgency` | TEXT | routine, standard, expedited |
| `summary` | TEXT | Case description |

### members

| Column | Type | Notes |
|---|---|---|
| `member_id` | TEXT PK |  |
| `patient_name` | TEXT |  |
| `dob` | TEXT | YYYY-MM-DD |
| `plan_id` | TEXT | Links to plans |
| `plan_type` | TEXT | commercial, medicaid, medicare_advantage, workers_comp |
| `product` | TEXT | Plan product name |
| `employer_group` | TEXT | Nullable |
| `member_status` | TEXT | active, termed |

### providers

| Column | Type | Notes |
|---|---|---|
| `provider_id` | TEXT PK |  |
| `provider_name` | TEXT |  |
| `specialty` | TEXT |  |
| `npi` | TEXT |  |
| `phone` | TEXT | Nullable |
| `fax` | TEXT | Nullable |
| `organization` | TEXT | Nullable |

### plans

| Column | Type | Notes |
|---|---|---|
| `plan_id` | TEXT PK |  |
| `payer_name` | TEXT |  |
| `plan_type` | TEXT | commercial, medicaid, medicare_advantage, workers_comp |
| `state` | TEXT |  |
| `network` | TEXT |  |
| `effective_start` | TEXT | YYYY-MM-DD |
| `effective_end` | TEXT | YYYY-MM-DD |
| `notes` | TEXT | Nullable |

### request_lines

| Column | Type | Notes |
|---|---|---|
| `line_id` | TEXT PK |  |
| `case_id` | TEXT |  |
| `cpt_code` | TEXT | CPT or HCPCS code |
| `modifier` | TEXT | Nullable |
| `service_name` | TEXT |  |
| `requested_units` | INTEGER |  |
| `requested_start` | TEXT | YYYY-MM-DD, nullable |
| `requested_end` | TEXT | YYYY-MM-DD, nullable |
| `diagnosis_codes` | TEXT | Comma-separated, nullable |
| `billed_charge` | REAL | USD |

### policies

| Column | Type | Notes |
|---|---|---|
| `policy_id` | TEXT PK |  |
| `policy_name` | TEXT |  |
| `version` | TEXT |  |
| `effective_start` | TEXT | YYYY-MM-DD |
| `effective_end` | TEXT | YYYY-MM-DD |
| `precedence` | INTEGER | Lower = higher priority |
| `summary` | TEXT |  |

### policy_criteria

| Column | Type | Notes |
|---|---|---|
| `criterion_id` | TEXT PK | e.g., PT-ACTIVE, DRUG-DENIAL |
| `policy_id` | TEXT |  |
| `criterion_key` | TEXT | Short key |
| `criterion_text` | TEXT | Description |
| `approval_required` | INTEGER | 1 = must be met |
| `result_if_missing` | TEXT | deny, pend |

### case_criteria

| Column | Type | Notes |
|---|---|---|
| `case_id` | TEXT PK (composite) |  |
| `criterion_id` | TEXT PK (composite) |  |
| `result` | TEXT | met, not_met, unclear, not_applicable |
| `evidence_fact_ids` | TEXT | Comma-separated, nullable |
| `gap_description` | TEXT | Nullable |
| `reviewer_scope` | TEXT | nurse, md, appeals, nullable |

### documents

| Column | Type | Notes |
|---|---|---|
| `document_id` | TEXT PK |  |
| `case_id` | TEXT |  |
| `document_type` | TEXT | eval, plan_of_care, clinical_note, denial_letter, appeal_form, cardiolite_report, p2p_summary |
| `document_date` | TEXT | YYYY-MM-DD |
| `received_date` | TEXT | YYYY-MM-DD |
| `source_system` | TEXT |  |
| `is_current` | INTEGER | 1 = current, 0 = stale |
| `title` | TEXT |  |
| `summary` | TEXT |  |

### document_facts

| Column | Type | Notes |
|---|---|---|
| `fact_id` | TEXT PK |  |
| `document_id` | TEXT |  |
| `case_id` | TEXT |  |
| `fact_key` | TEXT | diagnosis, functional_score, units_requested, etc. |
| `fact_value` | TEXT |  |
| `numeric_value` | REAL | Nullable |
| `unit` | TEXT | Nullable |
| `supports_criteria` | TEXT | Comma-separated criterion IDs, nullable |

### authorizations

| Column | Type | Notes |
|---|---|---|
| `auth_id` | TEXT PK |  |
| `case_id` | TEXT |  |
| `auth_number` | TEXT | Nullable until issued |
| `status` | TEXT | pending, approved, denied, pended, issued, overturned |
| `approved_units` | INTEGER | Nullable |
| `approved_start` | TEXT | YYYY-MM-DD, nullable |
| `approved_end` | TEXT | YYYY-MM-DD, nullable |
| `approved_cpt` | TEXT | Comma-separated, nullable |
| `approved_modifier` | TEXT | Nullable |
| `denial_reason` | TEXT | Nullable |

### appeals

| Column | Type | Notes |
|---|---|---|
| `appeal_id` | TEXT PK |  |
| `case_id` | TEXT |  |
| `denial_date` | TEXT | YYYY-MM-DD |
| `received_date` | TEXT | YYYY-MM-DD |
| `appeal_type_requested` | TEXT |  |
| `appeal_path` | TEXT | standard_internal, expedited_internal, external_review |
| `expedited_attestation` | TEXT |  |
| `appeal_deadline` | TEXT | YYYY-MM-DD |
| `outcome` | TEXT | Nullable |
| `owner` | TEXT | appeals-rx, um-nurse, medical-director, payment-integrity, member-services |
| `notes` | TEXT | Nullable |

### drug_trials

| Column | Type | Notes |
|---|---|---|
| `trial_id` | TEXT PK |  |
| `case_id` | TEXT |  |
| `medication` | TEXT | Lowercase name |
| `outcome` | TEXT | failed, intolerable sedation, partial response, etc. |
| `documented` | INTEGER | 1 = supported by records, 0 = not |
| `start_date` | TEXT | YYYY-MM-DD, nullable |
| `end_date` | TEXT | YYYY-MM-DD, nullable |
| `notes` | TEXT | Nullable |

### assistance_screen

| Column | Type | Notes |
|---|---|---|
| `case_id` | TEXT PK |  |
| `program_name` | TEXT | Vraylar Connect, Dupixent MyWay, Humira Complete |
| `income_percent_fpl` | REAL | Nullable |
| `insurance_type` | TEXT |  |
| `denial_required` | INTEGER | 1 = denial needed |
| `denial_on_file` | INTEGER | 1 = present |
| `missing_fields` | TEXT | Comma-separated, nullable |
| `assistance_status` | TEXT | eligible_ready, eligible_missing_information, not_eligible |

### p2p_events

| Column | Type | Notes |
|---|---|---|
| `p2p_id` | TEXT PK |  |
| `case_id` | TEXT |  |
| `scheduled_at` | TEXT | ISO datetime |
| `duration_minutes` | INTEGER |  |
| `provider_argument` | TEXT | Nullable |
| `new_information` | TEXT | Nullable |
| `outcome` | TEXT | overturn_to_approval, uphold_intended_adverse_decision, null |
| `final_status` | TEXT | Nullable |
| `reviewer` | TEXT | Nullable |
| `notes` | TEXT | Nullable |

### claims

| Column | Type | Notes |
|---|---|---|
| `claim_id` | TEXT PK |  |
| `member_id` | TEXT |  |
| `case_id` | TEXT | Nullable |
| `payer` | TEXT |  |
| `received_date` | TEXT | YYYY-MM-DD |
| `claim_status` | TEXT | paid, pending, denied |
| `auth_number` | TEXT | Nullable |
| `billed_total` | REAL | USD |
| `paid_total` | REAL | USD |

### claim_lines

| Column | Type | Notes |
|---|---|---|
| `claim_line_id` | TEXT PK |  |
| `claim_id` | TEXT |  |
| `line_number` | INTEGER | Claim line order |
| `cpt_code` | TEXT |  |
| `modifier` | TEXT | Nullable |
| `units` | INTEGER |  |
| `billed_amount` | REAL | USD |
| `paid_amount` | REAL | USD |
| `denial_code` | TEXT | Nullable |
| `service_date` | TEXT | YYYY-MM-DD |

### payment_benchmarks

| Column | Type | Notes |
|---|---|---|
| `benchmark_id` | TEXT PK |  |
| `payer` | TEXT |  |
| `plan_type` | TEXT | commercial, medicaid, medicare_advantage, workers_comp |
| `service_domain` | TEXT |  |
| `cpt_code` | TEXT |  |
| `modifier` | TEXT | Nullable |
| `effective_start` | TEXT | YYYY-MM-DD |
| `effective_end` | TEXT | YYYY-MM-DD |
| `allowed_amount` | REAL | USD |
| `source_name` | TEXT | Northstar Commercial Imaging Schedule, Legacy Imaging Export, etc. |
| `source_version` | TEXT | 2026Q2, 2025Q4, etc. |

### service_margin

| Column | Type | Notes |
|---|---|---|
| `month_id` | TEXT PK |  |
| `period` | TEXT | YYYY-MM |
| `payer` | TEXT |  |
| `payer_segment` | TEXT | medicaid, commercial, workers_comp, medicare_advantage |
| `service_domain` | TEXT | physical_therapy, speech_therapy, occupational_therapy, cardiac_imaging |
| `cpt_code` | TEXT |  |
| `visits` | INTEGER |  |
| `net_revenue` | REAL | USD |
| `variable_cost` | REAL | USD |
| `fixed_cost_allocated` | REAL | USD |
| `charge_sensitive` | INTEGER | 0 or 1 |
