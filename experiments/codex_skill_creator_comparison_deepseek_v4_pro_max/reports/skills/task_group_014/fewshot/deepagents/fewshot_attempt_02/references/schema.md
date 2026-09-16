# Northstar Database Schema

Schema is also available live via `GET /api/tables`. This reference documents the key tables and their join relationships.

## Table Index

| Table | Primary Key | Key Joins |
|-------|-------------|-----------|
| `cases` | `case_id` | ↔ members (member_id), providers (provider_id), policies (policy_id) |
| `members` | `member_id` | ↔ plans (plan_id) |
| `plans` | `plan_id` | |
| `providers` | `provider_id` | |
| `policies` | `policy_id` | ↔ policy_criteria (policy_id) |
| `policy_criteria` | `criterion_id` | ↔ policies (policy_id), case_criteria (criterion_id) |
| `request_lines` | `line_id` | ↔ cases (case_id) |
| `documents` | `document_id` | ↔ cases (case_id), document_facts (document_id) |
| `document_facts` | `fact_id` | ↔ documents (document_id), cases (case_id) |
| `case_criteria` | `case_id` + `criterion_id` | ↔ cases (case_id), policy_criteria (criterion_id) |
| `authorizations` | `auth_id` | ↔ cases (case_id) |
| `appeals` | `appeal_id` | ↔ cases (case_id) |
| `drug_trials` | `trial_id` | ↔ cases (case_id) |
| `assistance_screen` | `case_id` | ↔ cases (case_id) |
| `claims` | `claim_id` | ↔ cases (case_id), claim_lines (claim_id) |
| `claim_lines` | `claim_line_id` | ↔ claims (claim_id) |
| `payment_benchmarks` | `benchmark_id` | |
| `p2p_events` | `p2p_id` | ↔ cases (case_id) |
| `service_margin` | `month_id` | |

## Column Reference

### cases
| Column | Type | Notes |
|--------|------|-------|
| `case_id` | TEXT PK | Business identifier |
| `member_id` | TEXT | Join to members |
| `provider_id` | TEXT | Join to providers |
| `request_type` | TEXT | e.g. prior_authorization, appeal, claim_review |
| `service_domain` | TEXT | e.g. physical_therapy, cardiac_imaging, pharmacy |
| `policy_id` | TEXT | Join to policies |
| `request_date` | TEXT | YYYY-MM-DD |
| `due_date` | TEXT | YYYY-MM-DD |
| `current_stage` | TEXT | e.g. nurse_review, md_review, p2p, closed |
| `current_status` | TEXT | e.g. open, pending, approved, denied |
| `urgency` | TEXT | standard, expedited |
| `summary` | TEXT | Case description |

### members
| Column | Type | Notes |
|--------|------|-------|
| `member_id` | TEXT PK | |
| `patient_name` | TEXT | |
| `dob` | TEXT | YYYY-MM-DD |
| `plan_id` | TEXT | Join to plans |
| `plan_type` | TEXT | commercial, medicaid, medicare |
| `product` | TEXT | |
| `employer_group` | TEXT | Nullable |
| `member_status` | TEXT | active, inactive |

### plans
| Column | Type | Notes |
|--------|------|-------|
| `plan_id` | TEXT PK | |
| `payer_name` | TEXT | e.g. Northstar Health Plan |
| `plan_type` | TEXT | |
| `state` | TEXT | Two-letter code |
| `network` | TEXT | |
| `effective_start` | TEXT | YYYY-MM-DD |
| `effective_end` | TEXT | YYYY-MM-DD |
| `notes` | TEXT | Nullable |

### providers
| Column | Type | Notes |
|--------|------|-------|
| `provider_id` | TEXT PK | |
| `provider_name` | TEXT | |
| `specialty` | TEXT | |
| `npi` | TEXT | |
| `phone` | TEXT | Nullable |
| `fax` | TEXT | Nullable |
| `organization` | TEXT | Nullable |

### policies
| Column | Type | Notes |
|--------|------|-------|
| `policy_id` | TEXT PK | |
| `policy_name` | TEXT | |
| `version` | TEXT | |
| `effective_start` | TEXT | YYYY-MM-DD |
| `effective_end` | TEXT | YYYY-MM-DD |
| `precedence` | INTEGER | Lower = higher priority |
| `summary` | TEXT | |

### policy_criteria
| Column | Type | Notes |
|--------|------|-------|
| `criterion_id` | TEXT PK | e.g. PT-ACTIVE, PET-IND |
| `policy_id` | TEXT | Join to policies |
| `criterion_key` | TEXT | Shortcode |
| `criterion_text` | TEXT | Full criterion description |
| `approval_required` | INTEGER | 1 = must be met |
| `result_if_missing` | TEXT | Default when no evidence |

### request_lines
| Column | Type | Notes |
|--------|------|-------|
| `line_id` | TEXT PK | |
| `case_id` | TEXT | Join to cases |
| `cpt_code` | TEXT | |
| `modifier` | TEXT | Nullable |
| `service_name` | TEXT | |
| `requested_units` | INTEGER | |
| `requested_start` | TEXT | Nullable |
| `requested_end` | TEXT | Nullable |
| `diagnosis_codes` | TEXT | Nullable, comma-separated |
| `billed_charge` | REAL | |

### documents
| Column | Type | Notes |
|--------|------|-------|
| `document_id` | TEXT PK | |
| `case_id` | TEXT | Join to cases |
| `document_type` | TEXT | evaluation, plan_of_care, clinical_note |
| `document_date` | TEXT | YYYY-MM-DD |
| `received_date` | TEXT | YYYY-MM-DD |
| `source_system` | TEXT | |
| `is_current` | INTEGER | 1 = current, 0 = stale |
| `title` | TEXT | |
| `summary` | TEXT | |

### document_facts
| Column | Type | Notes |
|--------|------|-------|
| `fact_id` | TEXT PK | |
| `document_id` | TEXT | Join to documents |
| `case_id` | TEXT | Join to cases |
| `fact_key` | TEXT | e.g. diagnosis, deficit_score, visit_frequency |
| `fact_value` | TEXT | |
| `numeric_value` | REAL | Nullable |
| `unit` | TEXT | Nullable |
| `supports_criteria` | TEXT | Comma-separated criterion IDs |

### case_criteria
| Column | Type | Notes |
|--------|------|-------|
| `case_id` | TEXT PK (part) | |
| `criterion_id` | TEXT PK (part) | |
| `result` | TEXT | met, not_met, unclear |
| `evidence_fact_ids` | TEXT | Comma-separated fact IDs |
| `gap_description` | TEXT | Nullable |
| `reviewer_scope` | TEXT | Nullable |

### authorizations
| Column | Type | Notes |
|--------|------|-------|
| `auth_id` | TEXT PK | |
| `case_id` | TEXT | |
| `auth_number` | TEXT | Nullable |
| `status` | TEXT | approved, denied, pending |
| `approved_units` | INTEGER | Nullable |
| `approved_start` | TEXT | Nullable |
| `approved_end` | TEXT | Nullable |
| `approved_cpt` | TEXT | Nullable, comma-separated |
| `approved_modifier` | TEXT | Nullable |
| `denial_reason` | TEXT | Nullable |

### appeals
| Column | Type | Notes |
|--------|------|-------|
| `appeal_id` | TEXT PK | |
| `case_id` | TEXT | |
| `denial_date` | TEXT | YYYY-MM-DD |
| `received_date` | TEXT | YYYY-MM-DD |
| `appeal_type_requested` | TEXT | |
| `appeal_path` | TEXT | standard_internal, expedited_internal, external_review |
| `expedited_attestation` | TEXT | yes, no |
| `appeal_deadline` | TEXT | YYYY-MM-DD |
| `outcome` | TEXT | Nullable |
| `owner` | TEXT | Nullable |
| `notes` | TEXT | Nullable |

### drug_trials
| Column | Type | Notes |
|--------|------|-------|
| `trial_id` | TEXT PK | |
| `case_id` | TEXT | |
| `medication` | TEXT | |
| `outcome` | TEXT | failed_efficacy, adverse_event, successful |
| `documented` | INTEGER | 1 = documented, 0 = not |
| `start_date` | TEXT | Nullable |
| `end_date` | TEXT | Nullable |
| `notes` | TEXT | Nullable |

### assistance_screen
| Column | Type | Notes |
|--------|------|-------|
| `case_id` | TEXT PK | |
| `program_name` | TEXT | |
| `income_percent_fpl` | REAL | Nullable |
| `insurance_type` | TEXT | |
| `denial_required` | INTEGER | |
| `denial_on_file` | INTEGER | |
| `missing_fields` | TEXT | Comma-separated |
| `assistance_status` | TEXT | |

### claims
| Column | Type | Notes |
|--------|------|-------|
| `claim_id` | TEXT PK | |
| `member_id` | TEXT | |
| `case_id` | TEXT | Nullable |
| `payer` | TEXT | |
| `received_date` | TEXT | |
| `claim_status` | TEXT | |
| `auth_number` | TEXT | Nullable |
| `billed_total` | REAL | |
| `paid_total` | REAL | |

### claim_lines
| Column | Type | Notes |
|--------|------|-------|
| `claim_line_id` | TEXT PK | |
| `claim_id` | TEXT | Join to claims |
| `line_number` | INTEGER | |
| `cpt_code` | TEXT | |
| `modifier` | TEXT | Nullable |
| `units` | INTEGER | |
| `billed_amount` | REAL | |
| `paid_amount` | REAL | |
| `denial_code` | TEXT | Nullable |
| `service_date` | TEXT | |

### payment_benchmarks
| Column | Type | Notes |
|--------|------|-------|
| `benchmark_id` | TEXT PK | |
| `payer` | TEXT | |
| `plan_type` | TEXT | |
| `service_domain` | TEXT | |
| `cpt_code` | TEXT | |
| `modifier` | TEXT | Nullable |
| `effective_start` | TEXT | YYYY-MM-DD |
| `effective_end` | TEXT | YYYY-MM-DD |
| `allowed_amount` | REAL | |
| `source_name` | TEXT | |
| `source_version` | TEXT | |

### p2p_events
| Column | Type | Notes |
|--------|------|-------|
| `p2p_id` | TEXT PK | |
| `case_id` | TEXT | |
| `scheduled_at` | TEXT | |
| `duration_minutes` | INTEGER | |
| `provider_argument` | TEXT | Nullable |
| `new_information` | TEXT | Nullable |
| `outcome` | TEXT | Nullable |
| `final_status` | TEXT | Nullable |
| `reviewer` | TEXT | Nullable |
| `notes` | TEXT | Nullable |

### service_margin
| Column | Type | Notes |
|--------|------|-------|
| `month_id` | TEXT PK | |
| `period` | TEXT | YYYY-MM |
| `payer` | TEXT | |
| `payer_segment` | TEXT | medicaid, commercial, workers_comp |
| `service_domain` | TEXT | physical_therapy, speech_therapy, occupational_therapy |
| `cpt_code` | TEXT | |
| `visits` | INTEGER | |
| `net_revenue` | REAL | |
| `variable_cost` | REAL | |
| `fixed_cost_allocated` | REAL | |
| `charge_sensitive` | INTEGER | 1 = yes |
