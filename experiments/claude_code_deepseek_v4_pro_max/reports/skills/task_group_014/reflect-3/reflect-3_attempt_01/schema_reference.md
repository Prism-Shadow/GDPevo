# Northstar Payer Operations — Database Schema Reference

Quick-reference schema for writing SQL queries against the environment.

## Core Tables

### cases
| Column | Type | Notes |
|---|---|---|
| case_id | TEXT PK | Case identifier |
| member_id | TEXT | Links to members |
| provider_id | TEXT | Links to providers |
| request_type | TEXT | prior_authorization, coverage_exception, claim_payment_review, peer_to_peer |
| service_domain | TEXT | physical_therapy, cardiac_imaging, specialty_drug, speech_therapy, occupational_therapy |
| policy_id | TEXT | Links to policies |
| request_date | TEXT | YYYY-MM-DD |
| due_date | TEXT | YYYY-MM-DD |
| current_stage | TEXT | nurse_review, appeals, medical_director, payment_integrity, finance_queue |
| current_status | TEXT | ready_for_determination, packet_incomplete, p2p_complete, needs_repricing |
| urgency | TEXT | routine, standard, expedited, urgent |

### members
| Column | Type |
|---|---|
| member_id | TEXT PK |
| patient_name | TEXT |
| dob | TEXT |
| plan_id | TEXT |
| plan_type | TEXT |
| product | TEXT |
| employer_group | TEXT |
| member_status | TEXT |

### plans
| Column | Type |
|---|---|
| plan_id | TEXT PK |
| payer_name | TEXT |
| plan_type | TEXT |
| state | TEXT |
| network | TEXT |
| effective_start | TEXT |
| effective_end | TEXT |

### policies
| Column | Type |
|---|---|
| policy_id | TEXT PK |
| policy_name | TEXT |
| version | TEXT |
| effective_start | TEXT |
| effective_end | TEXT |
| precedence | INTEGER |
| summary | TEXT |

### policy_criteria
| Column | Type | Notes |
|---|---|---|
| criterion_id | TEXT PK | e.g., PT-ACTIVE, DRUG-FAILURES, PET-IND |
| policy_id | TEXT | |
| criterion_key | TEXT | |
| criterion_text | TEXT | |
| approval_required | INTEGER | 1 = required, 0 = informational |
| result_if_missing | TEXT | pend, deny, uphold |

### case_criteria
| Column | Type |
|---|---|
| case_id | TEXT PK (composite) |
| criterion_id | TEXT PK (composite) |
| result | TEXT |
| evidence_fact_ids | TEXT |
| gap_description | TEXT |
| reviewer_scope | TEXT |

### documents
| Column | Type | Notes |
|---|---|---|
| document_id | TEXT PK | |
| case_id | TEXT | |
| document_type | TEXT | clinical_eval, plan_of_care, stale_export, denial_notice, member_authorization, prescriber_letter, remittance, cardiology_note |
| document_date | TEXT | |
| received_date | TEXT | |
| source_system | TEXT | |
| is_current | INTEGER | 1 = current evidence, 0 = excluded/stale |
| title | TEXT | |
| summary | TEXT | |

### document_facts
| Column | Type | Notes |
|---|---|---|
| fact_id | TEXT PK | |
| document_id | TEXT | |
| case_id | TEXT | |
| fact_key | TEXT | |
| fact_value | TEXT | |
| numeric_value | REAL | nullable |
| unit | TEXT | nullable |
| supports_criteria | TEXT | nullable, criterion ID |

### request_lines
| Column | Type |
|---|---|
| line_id | TEXT PK |
| case_id | TEXT |
| cpt_code | TEXT |
| modifier | TEXT (nullable) |
| service_name | TEXT |
| requested_units | INTEGER |
| requested_start | TEXT |
| requested_end | TEXT |
| diagnosis_codes | TEXT |
| billed_charge | REAL |

### authorizations
| Column | Type |
|---|---|
| auth_id | TEXT PK |
| case_id | TEXT |
| auth_number | TEXT (nullable) |
| status | TEXT |
| approved_units | INTEGER (nullable) |
| approved_start | TEXT (nullable) |
| approved_end | TEXT (nullable) |
| approved_cpt | TEXT (nullable, comma-separated) |
| approved_modifier | TEXT (nullable) |
| denial_reason | TEXT (nullable) |

### claims
| Column | Type |
|---|---|
| claim_id | TEXT PK |
| member_id | TEXT |
| case_id | TEXT |
| payer | TEXT |
| received_date | TEXT |
| claim_status | TEXT |
| auth_number | TEXT (nullable) |
| billed_total | REAL |
| paid_total | REAL |

### claim_lines
| Column | Type |
|---|---|
| claim_line_id | TEXT PK |
| claim_id | TEXT |
| line_number | INTEGER |
| cpt_code | TEXT |
| modifier | TEXT (nullable) |
| units | INTEGER |
| billed_amount | REAL |
| paid_amount | REAL |
| denial_code | TEXT (nullable) |
| service_date | TEXT |

### payment_benchmarks
| Column | Type | Notes |
|---|---|---|
| benchmark_id | TEXT PK | |
| payer | TEXT | |
| plan_type | TEXT | commercial, medicaid, medicare_advantage, workers_comp |
| service_domain | TEXT | |
| cpt_code | TEXT | |
| modifier | TEXT (nullable) | |
| effective_start | TEXT | |
| effective_end | TEXT | |
| allowed_amount | REAL | per-unit allowed |
| source_name | TEXT | Northstar Commercial Imaging Schedule, Legacy Imaging Export, etc. |
| source_version | TEXT | 2026Q2, 2025Q4, etc. |

### appeals
| Column | Type |
|---|---|
| appeal_id | TEXT PK |
| case_id | TEXT |
| denial_date | TEXT |
| received_date | TEXT |
| appeal_type_requested | TEXT |
| appeal_path | TEXT |
| expedited_attestation | TEXT |
| appeal_deadline | TEXT |
| outcome | TEXT |
| owner | TEXT |

### drug_trials
| Column | Type | Notes |
|---|---|---|
| trial_id | TEXT PK | |
| case_id | TEXT | |
| medication | TEXT | lowercase |
| outcome | TEXT | |
| documented | INTEGER | 1 = documented, 0 = unsubstantiated |
| start_date | TEXT | |
| end_date | TEXT | |
| notes | TEXT | |

### assistance_screen
| Column | Type |
|---|---|
| case_id | TEXT PK |
| program_name | TEXT |
| income_percent_fpl | REAL (nullable) |
| insurance_type | TEXT |
| denial_required | INTEGER |
| denial_on_file | INTEGER |
| missing_fields | TEXT |
| assistance_status | TEXT |

### p2p_events
| Column | Type |
|---|---|
| p2p_id | TEXT PK |
| case_id | TEXT |
| scheduled_at | TEXT |
| duration_minutes | INTEGER |
| provider_argument | TEXT |
| new_information | TEXT |
| outcome | TEXT |
| final_status | TEXT |
| reviewer | TEXT |
| notes | TEXT |

### service_margin
| Column | Type | Notes |
|---|---|---|
| month_id | TEXT PK | |
| period | TEXT | YYYY-MM |
| payer | TEXT | |
| payer_segment | TEXT | medicaid, commercial, workers_comp |
| service_domain | TEXT | |
| cpt_code | TEXT | |
| visits | INTEGER | |
| net_revenue | REAL | |
| variable_cost | REAL | |
| fixed_cost_allocated | REAL | |
| charge_sensitive | INTEGER | 1 = flagged |

### providers
| Column | Type |
|---|---|
| provider_id | TEXT PK |
| provider_name | TEXT |
| specialty | TEXT |
| npi | TEXT |
| phone | TEXT |
| fax | TEXT |
| organization | TEXT |

## SQL Query Patterns

```sql
-- Get benchmarks for a specific claim line (match all dimensions)
SELECT * FROM payment_benchmarks
WHERE payer = '<payer>'
  AND plan_type = '<plan_type>'
  AND service_domain = '<domain>'
  AND cpt_code = '<cpt>'
  AND (modifier = '<mod>' OR modifier IS NULL)
  AND effective_start <= '<service_date>'
  AND effective_end >= '<service_date>';

-- Get all facts for a case
SELECT * FROM document_facts WHERE case_id = '<case_id>';

-- Get service margin rows by IDs
SELECT * FROM service_margin WHERE month_id IN ('<id1>', '<id2>', '<id3>');

-- Get drug trials for a case
SELECT * FROM drug_trials WHERE case_id = '<case_id>';
```
