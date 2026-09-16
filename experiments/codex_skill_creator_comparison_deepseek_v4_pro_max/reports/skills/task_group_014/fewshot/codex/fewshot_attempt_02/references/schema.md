# Northstar Database Schema

19 tables in a shared SQLite-compatible payer-operations database. The SQL endpoint is `POST /sql/query` with bearer token `pa-review-token-014`.

## Table Index

| # | Table | Primary Key | Description |
|---|-------|-------------|-------------|
| 1 | cases | case_id | Authorization and appeal case master records |
| 2 | members | member_id | Member demographics and plan enrollment |
| 3 | providers | provider_id | Rendering/referring provider directory |
| 4 | plans | plan_id | Health plan product definitions |
| 5 | policies | policy_id | Medical and pharmacy policy master |
| 6 | policy_criteria | criterion_id | Individual policy criteria definitions |
| 7 | case_criteria | (case_id, criterion_id) | Criteria review results per case |
| 8 | request_lines | line_id | Service request lines per case |
| 9 | authorizations | auth_id | Authorization decisions per case |
| 10 | documents | document_id | Clinical and administrative documents |
| 11 | document_facts | fact_id | Structured clinical facts extracted from documents |
| 12 | claims | claim_id | Paid and pending claim headers |
| 13 | claim_lines | claim_line_id | Individual claim service lines |
| 14 | payment_benchmarks | benchmark_id | Allowed-amount benchmarks by payer/plan/CPT/modifier |
| 15 | appeals | appeal_id | Member and provider appeal records |
| 16 | drug_trials | trial_id | Prior medication trial records |
| 17 | assistance_screen | case_id | Manufacturer copay/patient assistance screening |
| 18 | p2p_events | p2p_id | Peer-to-peer discussion event records |
| 19 | service_margin | month_id | Monthly therapy service margin summaries |

---

## 1. cases

Authorization and appeal case master records.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| case_id | TEXT | PK | Northstar case identifier |
| member_id | TEXT | NOT NULL | FK to members |
| provider_id | TEXT | NOT NULL | FK to providers |
| request_type | TEXT | NOT NULL | e.g., prior_auth, appeal, claim_review |
| service_domain | TEXT | NOT NULL | e.g., physical_therapy, cardiac_imaging, pharmacy |
| policy_id | TEXT | NOT NULL | FK to policies |
| request_date | TEXT | NOT NULL | YYYY-MM-DD |
| due_date | TEXT | NOT NULL | YYYY-MM-DD |
| current_stage | TEXT | NOT NULL | e.g., nurse_review, md_review, p2p, appeal, closed |
| current_status | TEXT | NOT NULL | e.g., open, pended, approved, denied, paid |
| urgency | TEXT | NOT NULL | standard, expedited, urgent |
| summary | TEXT | NOT NULL | Human-readable case summary |

## 2. members

Member demographics and plan enrollment.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| member_id | TEXT | PK | |
| patient_name | TEXT | NOT NULL | |
| dob | TEXT | NOT NULL | YYYY-MM-DD |
| plan_id | TEXT | NOT NULL | FK to plans |
| plan_type | TEXT | NOT NULL | e.g., commercial, medicaid, medicare |
| product | TEXT | NOT NULL | Plan product name |
| employer_group | TEXT | NULL | |
| member_status | TEXT | NOT NULL | active, inactive, terminated |

## 3. providers

Rendering/referring provider directory.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| provider_id | TEXT | PK | |
| provider_name | TEXT | NOT NULL | |
| specialty | TEXT | NOT NULL | |
| npi | TEXT | NOT NULL | National Provider Identifier |
| phone | TEXT | NULL | |
| fax | TEXT | NULL | |
| organization | TEXT | NULL | |

## 4. plans

Health plan product definitions.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| plan_id | TEXT | PK | |
| payer_name | TEXT | NOT NULL | e.g., Northstar Health Plan |
| plan_type | TEXT | NOT NULL | commercial, medicaid, medicare, workers_comp |
| state | TEXT | NOT NULL | |
| network | TEXT | NOT NULL | |
| effective_start | TEXT | NOT NULL | YYYY-MM-DD |
| effective_end | TEXT | NOT NULL | YYYY-MM-DD |
| notes | TEXT | NULL | |

## 5. policies

Medical and pharmacy policy master.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| policy_id | TEXT | PK | |
| policy_name | TEXT | NOT NULL | |
| version | TEXT | NOT NULL | |
| effective_start | TEXT | NOT NULL | YYYY-MM-DD |
| effective_end | TEXT | NOT NULL | YYYY-MM-DD |
| precedence | INTEGER | NOT NULL | Lower values = higher priority |
| summary | TEXT | NOT NULL | |

## 6. policy_criteria

Individual policy criteria definitions.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| criterion_id | TEXT | PK | |
| policy_id | TEXT | NOT NULL | FK to policies |
| criterion_key | TEXT | NOT NULL | Short key e.g., PT-ACTIVE, DRUG-AUTH, PET-IND |
| criterion_text | TEXT | NOT NULL | Human-readable criterion description |
| approval_required | INTEGER | NOT NULL | 1 if criterion must be met for approval |
| result_if_missing | TEXT | NOT NULL | Default result when evidence is absent |

## 7. case_criteria

Criteria review results per case. Composite primary key (case_id, criterion_id).

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| case_id | TEXT | PK | |
| criterion_id | TEXT | PK | FK to policy_criteria |
| result | TEXT | NOT NULL | met, not_met, unclear, not_applicable |
| evidence_fact_ids | TEXT | NULL | Comma-separated fact_id list |
| gap_description | TEXT | NULL | |
| reviewer_scope | TEXT | NULL | nurse, md, p2p, appeal |

## 8. request_lines

Service request lines per case.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| line_id | TEXT | PK | |
| case_id | TEXT | NOT NULL | FK to cases |
| cpt_code | TEXT | NOT NULL | CPT or HCPCS code |
| modifier | TEXT | NULL | |
| service_name | TEXT | NOT NULL | |
| requested_units | INTEGER | NOT NULL | |
| requested_start | TEXT | NULL | YYYY-MM-DD |
| requested_end | TEXT | NULL | YYYY-MM-DD |
| diagnosis_codes | TEXT | NULL | Comma-separated ICD-10 codes |
| billed_charge | REAL | NOT NULL | USD |

## 9. authorizations

Authorization decisions per case.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| auth_id | TEXT | PK | |
| case_id | TEXT | NOT NULL | FK to cases |
| auth_number | TEXT | NULL | Issued auth number e.g., NPA-2405014 |
| status | TEXT | NOT NULL | approved, denied, pended, partial |
| approved_units | INTEGER | NULL | |
| approved_start | TEXT | NULL | YYYY-MM-DD |
| approved_end | TEXT | NULL | YYYY-MM-DD |
| approved_cpt | TEXT | NULL | Comma-separated CPT codes |
| approved_modifier | TEXT | NULL | |
| denial_reason | TEXT | NULL | |

## 10. documents

Clinical and administrative documents.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| document_id | TEXT | PK | |
| case_id | TEXT | NOT NULL | FK to cases |
| document_type | TEXT | NOT NULL | eval, poc, cardiology_report, pharmacy_claim, appeal_letter, etc. |
| document_date | TEXT | NOT NULL | YYYY-MM-DD |
| received_date | TEXT | NOT NULL | YYYY-MM-DD |
| source_system | TEXT | NOT NULL | EMR, pharmacy_portal, provider_portal, etc. |
| is_current | INTEGER | NOT NULL | 1 = current/active, 0 = stale/superseded |
| title | TEXT | NOT NULL | |
| summary | TEXT | NOT NULL | |

## 11. document_facts

Structured clinical facts extracted from documents.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| fact_id | TEXT | PK | |
| document_id | TEXT | NOT NULL | FK to documents |
| case_id | TEXT | NOT NULL | FK to cases |
| fact_key | TEXT | NOT NULL | e.g., diagnosis_code, deficit_score, visit_count |
| fact_value | TEXT | NOT NULL | |
| numeric_value | REAL | NULL | |
| unit | TEXT | NULL | |
| supports_criteria | TEXT | NULL | Comma-separated criterion IDs this fact supports |

## 12. claims

Paid and pending claim headers.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| claim_id | TEXT | PK | |
| member_id | TEXT | NOT NULL | |
| case_id | TEXT | NULL | FK to cases |
| payer | TEXT | NOT NULL | e.g., Northstar Health Plan |
| received_date | TEXT | NOT NULL | YYYY-MM-DD |
| claim_status | TEXT | NOT NULL | paid, pending, denied |
| auth_number | TEXT | NULL | |
| billed_total | REAL | NOT NULL | USD |
| paid_total | REAL | NOT NULL | USD |

## 13. claim_lines

Individual claim service lines.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| claim_line_id | TEXT | PK | |
| claim_id | TEXT | NOT NULL | FK to claims |
| line_number | INTEGER | NOT NULL | Claim line order (1-based) |
| cpt_code | TEXT | NOT NULL | |
| modifier | TEXT | NULL | |
| units | INTEGER | NOT NULL | |
| billed_amount | REAL | NOT NULL | USD |
| paid_amount | REAL | NOT NULL | USD |
| denial_code | TEXT | NULL | |
| service_date | TEXT | NOT NULL | YYYY-MM-DD |

## 14. payment_benchmarks

Allowed-amount benchmarks by payer/plan/CPT/modifier.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| benchmark_id | TEXT | PK | |
| payer | TEXT | NOT NULL | |
| plan_type | TEXT | NOT NULL | |
| service_domain | TEXT | NOT NULL | |
| cpt_code | TEXT | NOT NULL | |
| modifier | TEXT | NULL | |
| effective_start | TEXT | NOT NULL | YYYY-MM-DD |
| effective_end | TEXT | NOT NULL | YYYY-MM-DD |
| allowed_amount | REAL | NOT NULL | USD per unit |
| source_name | TEXT | NOT NULL | e.g., Northstar Commercial Imaging Schedule, Legacy Imaging Export |
| source_version | TEXT | NOT NULL | e.g., 2026Q2 |

## 15. appeals

Member and provider appeal records.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| appeal_id | TEXT | PK | |
| case_id | TEXT | NOT NULL | FK to cases |
| denial_date | TEXT | NOT NULL | YYYY-MM-DD |
| received_date | TEXT | NOT NULL | YYYY-MM-DD |
| appeal_type_requested | TEXT | NOT NULL | standard_internal, expedited_internal, external_review |
| appeal_path | TEXT | NOT NULL | |
| expedited_attestation | TEXT | NOT NULL | true, false |
| appeal_deadline | TEXT | NOT NULL | YYYY-MM-DD |
| outcome | TEXT | NULL | |
| owner | TEXT | NULL | appeals-rx, um-nurse, medical-director, payment-integrity, member-services |
| notes | TEXT | NULL | |

## 16. drug_trials

Prior medication trial records.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| trial_id | TEXT | PK | |
| case_id | TEXT | NOT NULL | FK to cases |
| medication | TEXT | NOT NULL | drug name (lowercase) |
| outcome | TEXT | NOT NULL | ineffective, adverse_reaction, contraindicated, etc. |
| documented | INTEGER | NOT NULL | 1 = pharmacy fill record present, 0 = self-reported or insufficient |
| start_date | TEXT | NULL | YYYY-MM-DD |
| end_date | TEXT | NULL | YYYY-MM-DD |
| notes | TEXT | NULL | |

## 17. assistance_screen

Manufacturer copay/patient assistance screening.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| case_id | TEXT | PK | |
| program_name | TEXT | NOT NULL | e.g., Vraylar Connect, Dupixent MyWay |
| income_percent_fpl | REAL | NULL | Income as % of Federal Poverty Level |
| insurance_type | TEXT | NOT NULL | commercial, medicaid, medicare |
| denial_required | INTEGER | NOT NULL | 1 if program requires payer denial |
| denial_on_file | INTEGER | NOT NULL | 1 if denial is in the file |
| missing_fields | TEXT | NULL | Comma-separated field identifiers |
| assistance_status | TEXT | NOT NULL | eligible_ready, eligible_missing_information, not_eligible, not_applicable |

## 18. p2p_events

Peer-to-peer discussion event records.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| p2p_id | TEXT | PK | |
| case_id | TEXT | NOT NULL | FK to cases |
| scheduled_at | TEXT | NOT NULL | ISO datetime |
| duration_minutes | INTEGER | NOT NULL | |
| provider_argument | TEXT | NULL | |
| new_information | TEXT | NULL | |
| outcome | TEXT | NULL | overturn_to_approval, uphold_intended_adverse_decision |
| final_status | TEXT | NULL | |
| reviewer | TEXT | NULL | |
| notes | TEXT | NULL | |

## 19. service_margin

Monthly therapy service margin summaries.

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| month_id | TEXT | PK | |
| period | TEXT | NOT NULL | YYYY-MM |
| payer | TEXT | NOT NULL | |
| payer_segment | TEXT | NOT NULL | medicaid, commercial, workers_comp |
| service_domain | TEXT | NOT NULL | physical_therapy, speech_therapy, occupational_therapy |
| cpt_code | TEXT | NOT NULL | |
| visits | INTEGER | NOT NULL | |
| net_revenue | REAL | NOT NULL | USD |
| variable_cost | REAL | NOT NULL | USD |
| fixed_cost_allocated | REAL | NOT NULL | USD |
| charge_sensitive | INTEGER | NOT NULL | 1 = charge patterns flagged, 0 = not flagged |

## Common Query Patterns

### Get case with member and plan info
```sql
SELECT c.*, m.patient_name, m.plan_type, p.policy_name
FROM cases c
JOIN members m ON c.member_id = m.member_id
JOIN policies p ON c.policy_id = p.policy_id
WHERE c.case_id = '<id>'
```

### Get case criteria with policy criteria text
```sql
SELECT cc.*, pc.criterion_key, pc.criterion_text, pc.approval_required
FROM case_criteria cc
JOIN policy_criteria pc ON cc.criterion_id = pc.criterion_id
WHERE cc.case_id = '<id>'
```

### Get current documents only (exclude stale)
```sql
SELECT * FROM documents WHERE case_id = '<id>' AND is_current = 1
```

### Get all documents (current and stale)
```sql
SELECT * FROM documents WHERE case_id = '<id>'
```

### Get claim lines in order
```sql
SELECT * FROM claim_lines WHERE claim_id = '<id>' ORDER BY line_number
```

### Get effective benchmarks for a claim date
```sql
SELECT * FROM payment_benchmarks
WHERE payer = '<payer>' AND plan_type = '<plan_type>'
  AND service_domain = '<domain>' AND cpt_code = '<cpt>'
  AND effective_start <= '<claim_date>' AND effective_end >= '<claim_date>'
```

### Get drug trials for a case
```sql
SELECT * FROM drug_trials WHERE case_id = '<id>'
```

### Get margin rows by IDs
```sql
SELECT * FROM service_margin WHERE month_id IN ('<id1>', '<id2>', '<id3>')
```

### Get appeal with denial info
```sql
SELECT a.*, c.request_date, c.service_domain
FROM appeals a
JOIN cases c ON a.case_id = c.case_id
WHERE a.case_id = '<id>'
```

### SQL output format
The endpoint returns:
```json
{"columns": ["col1", "col2"], "rows": [["val1", "val2"], ...]}
```

Values are strings unless the column type is REAL or INTEGER, in which case they are JSON numbers.
