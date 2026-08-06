# Cedar Ridge Intake Coordination Portal — API & data model

The portal is a **read-only** HTTP service. The base URL is given to you at run time and is
never hard‑coded: the environment file (`environment_access.md`, variable
`GDPEVO_ENV_BASE_URL`) holds it, and prompts refer to it with the placeholder
`<TASK_ENV_BASE_URL>`. Substitute the real base URL before making requests.

## Reaching it

```
BASE=$GDPEVO_ENV_BASE_URL          # e.g. http://task-env:9013/
curl -s "$BASE"                    # HTML landing page (confirms reachability)
curl -s "$BASE/health"             # liveness
```

No credentials are required. Allowed endpoints (all `GET` unless noted):

| Endpoint | Returns |
|---|---|
| `GET /patients?q=&limit=` | patient search |
| `GET /patients/{patient_id}` | one patient |
| `GET /referrals?batch_id=&service_line=&limit=` | referral rows |
| `GET /referrals/{referral_id}` | one referral |
| `GET /transfers?batch_id=&limit=` | transfer rows |
| `GET /transfers/{transfer_id}` | one transfer |
| `GET /documents?...` | packet / referral documents |
| `GET /chart/{patient_id}` | chart artifacts for a patient |
| `GET /programs/{program_code}/candidates` | program candidate list |
| `GET /icd/{code}` | ICD metadata for one code |
| `GET /pharmacies` | pharmacy directory |
| `POST /query` | **read-only SQL** (body `{"sql": "SELECT ..."}`) |

## The SQL endpoint is the workhorse

Prefer `POST /query` for everything except quick spot checks — it is the fastest way to pull a
whole batch plus its joined rows in one shot. Only `SELECT` is allowed.

```bash
q() { curl -s -X POST "$BASE/query" -H 'Content-Type: application/json' \
        -d "{\"sql\": \"$1\"}"; }
q "SELECT * FROM referrals WHERE batch_id='<BATCH>' ORDER BY referral_id"
```

Response shape: `{"columns": [...], "row_count": N, "rows": [ {col: val, ...} ], "truncated": bool}`.
Watch `truncated`; page with `LIMIT/OFFSET` if a batch is large.

Discover the schema any time with:
```sql
SELECT name FROM sqlite_master WHERE type='table';
SELECT sql  FROM sqlite_master WHERE name='<table>';
```

## Tables (SQLite)

| Table | Key columns you will use |
|---|---|
| `patients` | patient_id, dob, phone, email, address, language, **existing_chart** (0/1), preferred_contact, **emergency_contact_present** (0/1) |
| `intake_rosters` | (roster_id, patient_id) PK, **requested_service_date**, **service_line**, source_note |
| `coverage` | patient_id, payer, effective_date, termination_date, network_status, **service_lines** (comma list), **status** (active/expired/pending) |
| `pbm` | patient_id, payer, **active** (0/1), **formulary_status** (covered/review/not_found), **specialty_required** (0/1), **status** (approved/pending/rejected) |
| `patient_pharmacy` | (patient_id, pharmacy_id) PK, **preference_rank** (1 = preferred) |
| `pharmacies` | pharmacy_id, name, **network_status** (in_network/out_of_network) |
| `lifestyle` | patient_id, smoking_status (Current/Former/Never), alcohol_use (Heavy/Moderate/Occasional/None), exercise_frequency (None/1-2/3-4/5+/NULL), sleep_hours (REAL) |
| `clinical_history` | patient_id, chronic_conditions (comma list), surgeries, medication_count, allergy_count, **recent_hospitalization** (0/1), **risk_flags** (comma list) |
| `referrals` | referral_id, batch_id, service_line, date_received, patient_id, payer, insurance_id, icd10_code, diagnosis_description, referral_reason, urgency (urgent/routine/admin), **records_received**, **imaging_received**, **auth_required**, **auth_status** (approved/pending/denied/not_submitted), **appointment_scheduled**, appointment_date, notes |
| `icd_codes` | code (PK), description, **chapter**, **service_family**, laterality (left/right/NULL) |
| `documents` | document_id, patient_id, referral_id, transfer_id, doc_type, status (final/draft), **finalized** (0/1), received_date, content_tag, notes |
| `transfer_requests` | transfer_id, batch_id, patient_id, referring_facility, **requested_start_date**, modality, days_requested, chair_window, **transportation** |
| `facility_capacity` | (location_id, date, modality) PK, **open_chairs** (INT) |
| `chart_artifacts` | artifact_id, patient_id, **artifact_type**, **status** (current/stale/draft), last_updated, value_summary |
| `program_candidates` | (program_code, patient_id) PK, candidate_date, source, **consent_status** (signed/missing/declined), **preferred_outreach**, **adherence_score**, **target_condition** |

## Reference constants observed in the data (stable across batches)

**ICD `service_family` → `chapter` map** (used to decide the *accepted* chapters per service line):

| service_family | chapter(s) |
|---|---|
| cardiology | I00-I99 |
| chronic_care | E00-E89, I00-I99, N00-N99 |
| dialysis | Z00-Z99 |
| orthopedics | M00-M99 (disease), S00-T88 (injury) |
| pulmonary | J00-J99, R00-R99 |

**Dialysis facilities** (in-center hemodialysis): `CRIC-MAIN`, `CRIC-NORTH`; modality string
`in_center_hemodialysis`. Open-chair capacity for a date = the SUM of `open_chairs` across both
locations for that date and modality (0 if no rows).

**Chart artifact types** present: demographics, active_problems, medications, allergies, vitals,
labs, consent, care_plan, outreach_preference. `status` is one of current / stale / draft.

> These constants describe the *engine*, not any single answer. Always re-confirm the controlled
> vocabulary for the current task from that task's `answer_template.json`, and if you meet a
> service line / program / modality not covered above, rediscover its facts with a quick SQL
> query before applying a rule.
