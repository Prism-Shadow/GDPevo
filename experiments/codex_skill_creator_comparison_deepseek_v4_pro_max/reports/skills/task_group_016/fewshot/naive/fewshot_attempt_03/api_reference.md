## Clinic Runtime API

Base URL is given as `<TASK_ENV_BASE_URL>` in task instructions. All endpoints
below are relative to that base.

**Authentication**: GET endpoints require no token. POST `/api/query` requires
header `X-Clinic-Token` with the value listed in environment access instructions.

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health check. Returns `{"status":"ok","database_ready":true}`. Use before other calls. |
| GET | `/api/cases` | Paginated list of all cases. Fields: `case_id`, `case_type`, `patient_id`, `service_date`, `status`, `summary`. |
| GET | `/api/cases/{case_id}` | **Primary data source.** Full case bundle with nested `case`, `patient`, `observations`, `findings`, `medications`, `allergies`, `imaging`, `problems`, `sdoh`, and `care_registry`. |
| GET | `/api/patients` | Paginated patient directory. Fields: `patient_id`, `name`, `age`, `birth_date`, `sex`, `fhir_id`. |
| GET | `/api/patients/{patient_id}` | Single patient with nested `allergies`, `medications`, `problems`, `sdoh`. |
| GET | `/api/observations` | Paginated observations across all cases. Fields: `observation_id`, `case_id`, `patient_id`, `category`, `code`, `display`, `status`, `effective_time`, `value_number`, `value_text`, `interpretation`, `unit`, `source`. |
| GET | `/api/medications` | Paginated medication records. |
| GET | `/api/allergies` | Paginated allergy records. |
| GET | `/api/problems` | Paginated problem-list records. |
| GET | `/api/imaging` | Paginated imaging studies. Fields: `imaging_id`, `case_id`, `patient_id`, `study`, `impression`, `performed_at`, `status`. |
| GET | `/api/care-registry` | Paginated care-registry records. Fields: `risk_score`, `chronic_condition_count`, `medication_count`, `dialysis_schedule`, `recent_admission_date`, `program_hint`. |
| GET | `/api/sdoh` | Paginated social-determinant records. Fields: `domain`, `severity`, `evidence`, `source`, `patient_id`. |
| GET | `/api/protocols` | List of available clinical protocols. |
| GET | `/api/protocols/{protocol_id}` | Full protocol body with decision rules, thresholds, controlled codes, and branch logic. |
| POST | `/api/query` | SQL query against the clinic database. Header: `X-Clinic-Token`. Body: `{"query":"SELECT ..."}`. Use sparingly; prefer structured endpoints. |

### Observation Status Semantics

| Status | Authoritative? | Use |
|--------|---------------|-----|
| `final` | Yes | Only status used for clinical decisions, assessments, and matched observations. |
| `preliminary` | No | Exclude from clinical assessments. Include in `excluded_observation_ids` when relevant. |
| `canceled` | No | Exclude from all assessments. |
| `entered-in-error` | No | Exclude from all assessments. |

### Case Types and Protocols

| case_type | Typical Protocol | Task Domain |
|-----------|-----------------|-------------|
| `acute_respiratory` | `RESP-PROTO-2026` or respiratory protocol | Structured respiratory assessment with imaging, SpO2, allergy-aware antibiotic plan |
| `pediatric_head_injury` | Head-injury protocol | Pediatric head trauma assessment with GCS, LOC, vomiting, coordination |
| `potassium_repletion` / `potassium_repletion` | `K-REPLETION-2026` | Serum potassium replacement with dose calculation, urgent escalation screening |
| `care_management` | `CM-HIGH-RISK-2026` | Care-management routing with registry risk scores, SDoH barriers, referrals |
| `observation_window` | `OBS-WINDOW-2026` | Observation retrieval within date windows, protocol gating, repeat-lab recommendations |

### Sample Data Shapes

Case detail response structure:
```json
{
  "case": {"case_id":"...", "case_type":"...", "patient_id":"...", "service_date":"...", "status":"active", "summary":"..."},
  "patient": {"patient_id":"...", "name":"...", "age":..., "birth_date":"...", "sex":"...", "fhir_id":"..."},
  "observations": [{"observation_id":"...", "code":"...", "status":"final", "value_number":..., "effective_time":"...", ...}],
  "findings": [{"finding_key":"...", "finding_value":"...", "source_id":"..."}],
  "medications": [...],
  "allergies": [{"allergen":"...", "reaction":"...", "status":"active|inactive", ...}],
  "imaging": [{"imaging_id":"...", "impression":"...", "study":"...", "status":"final|preliminary", ...}],
  "problems": [{"code":"...", "name":"...", "status":"active|...", ...}],
  "sdoh": [{"domain":"...", "severity":"...", "evidence":"...", "source":"member-disclosed|care-manager note", ...}],
  "care_registry": {"risk_score":..., "chronic_condition_count":..., "medication_count":..., ...} or null
}
```

Protocol body structure (example from K-REPLETION-2026):
```json
{
  "protocol_id":"...",
  "title":"...",
  "version":"...",
  "body": {
    "authoritative_statuses":["final"],
    "controlled_codes": {"serum_potassium":"K", "egfr":"33914-3", "follow_up_lab":"2823-3", "routine_oral_potassium_ndc":"40032-917-01", ...},
    "target_potassium_mmol_l":3.5,
    "routine_dose_rule": {"mEq_per_0_1_mmol_l_below_target":10, "round_to_nearest_mEq":10},
    "urgent_branch": {"potassium_less_than":3.0, "dialysis_dependent_esrd":true, "ecg_abnormality":true, "severe_renal_contraindication":true, "symptoms":["palpitations","syncope","weakness_with_arrhythmia_concern"]}
  }
}
```
