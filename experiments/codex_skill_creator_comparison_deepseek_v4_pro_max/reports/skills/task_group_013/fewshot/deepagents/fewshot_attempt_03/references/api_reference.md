# Cedar Ridge Intake Coordination Portal — API Reference

Base URL: `<TASK_ENV_BASE_URL>`
Authentication: none required. All endpoints are read-only GET except the SQL endpoint.

## REST Endpoints

### GET /
Portal landing page (HTML). Provides a UI for manual browsing but is not used programmatically.

### GET /patients
List all patients with optional query parameters:
- `q` — search by name or patient ID (substring match)
- `limit` — max results (default 10)

Returns: `{ "count": N, "patients": [...] }`

Patient object fields:
| Field | Type | Description |
|---|---|---|
| patient_id | string | Unique identifier (P001, P002, ...) |
| first_name | string | |
| last_name | string | |
| dob | string | Date of birth, YYYY-MM-DD |
| address | string or null | Street address |
| phone | string or null | |
| email | string or null | |
| language | string | Preferred language |
| preferred_contact | string | "portal", "phone", "email", or "sms" |
| emergency_contact_present | integer | 1 if present, 0 if missing |
| existing_chart | integer | 1 if chart exists, 0 if not |

### GET /patients/{patient_id}
Single patient record. Same fields as the list endpoint.

### GET /chart/{patient_id}
Complete chart bundle for a patient. Returns:

| Key | Type | Description |
|---|---|---|
| patient | object | Same patient fields as above |
| chart_artifacts | array | List of chart artifact objects |
| active_problems | array | Active problem artifacts |
| meds_allergies | array | Medication and allergy artifacts |
| recent_vitals_labs | array | Vitals and labs artifacts |
| clinical_history | object | See below |
| coverage | array | Insurance coverage rows |
| lifestyle | object | See below |
| documents | array | Documents linked to the patient |
| pbm | array | Pharmacy benefit manager records |

**clinical_history** fields:
| Field | Type | Description |
|---|---|---|
| patient_id | string | |
| chronic_conditions | string | Comma-separated condition list |
| medication_count | integer | |
| allergy_count | integer | |
| recent_hospitalization | integer | 1 if recent, 0 otherwise |
| surgeries | string | |
| risk_flags | string | |

**lifestyle** fields:
| Field | Type | Description |
|---|---|---|
| patient_id | string | |
| smoking_status | string | "Current", "Former", "Never" |
| alcohol_use | string | "None", "Light", "Moderate", "Heavy" |
| exercise_frequency | string | "None", "Irregular", "Regular" |
| sleep_hours | number | Average nightly sleep |

**coverage** row fields:
| Field | Type | Description |
|---|---|---|
| coverage_id | integer | |
| patient_id | string | |
| payer | string | Insurance payer name |
| policy_number | string | |
| group_number | string | |
| status | string | "active", "pending", "expired", "terminated" |
| effective_date | string | YYYY-MM-DD |
| termination_date | string | YYYY-MM-DD or null |
| network_status | string | |
| service_lines | string | Comma-separated (e.g. "primary_care,cardiology") |

**pbm** row fields:
| Field | Type | Description |
|---|---|---|
| patient_id | string | |
| active | integer | 1 = active, 0 = inactive |
| formulary_status | string | |
| policy_number | string | Should match coverage policy |
| group_number | string | |

**chart_artifacts** fields:
| Field | Type | Description |
|---|---|---|
| artifact_id | integer | |
| patient_id | string | |
| artifact_type | string | e.g. "active_problems", "vitals", "labs", "medications", "consent" |
| status | string | "current", "stale", etc. |
| last_updated | string | YYYY-MM-DD |
| value_summary | string | |

### GET /referrals
List referrals with optional filters:
- `batch_id` — exact batch filter
- `service_line` — e.g. "orthopedics", "pulmonary", "cardiology"
- `limit` — max results

Returns: `{ "count": N, "referrals": [...] }`

Referral object fields:
| Field | Type | Description |
|---|---|---|
| referral_id | string | Unique (REF0001, ...) |
| batch_id | string | Batch grouping |
| patient_id | string | |
| service_line | string | |
| icd10_code | string | |
| diagnosis_description | string | |
| referral_reason | string | |
| urgency | string | "urgent", "routine", "admin" |
| date_received | string | YYYY-MM-DD |
| referring_physician | string | |
| referring_practice | string | |
| referring_phone | string or null | |
| referring_fax | string or null | |
| assigned_physician | string | |
| auth_required | integer | 0 or 1 |
| auth_status | string | "approved", "pending", "denied", "not_required" |
| records_received | integer | 0 or 1 |
| imaging_received | integer | 0 or 1 |
| appointment_scheduled | integer | 0 or 1 |
| appointment_date | string or null | |
| insurance_id | string | |
| payer | string | |
| notes | string | |

### GET /referrals/{referral_id}
Single referral with patient info, ICD metadata, and linked documents.

Returns referral object plus:
- `patient` — patient object
- `icd` — ICD code metadata (chapter, code, description, laterality, service_family)
- `documents` — array of document objects linked to this referral

### GET /transfers
List transfers with optional filters:
- `batch_id` — exact batch filter
- `limit` — max results

Transfer object fields:
| Field | Type | Description |
|---|---|---|
| transfer_id | string | Unique (TR0001, ...) |
| batch_id | string | |
| patient_id | string | |
| modality | string | |
| days_requested | string | |
| chair_window | string | |
| requested_start_date | string | YYYY-MM-DD |
| requested_end_date | string | YYYY-MM-DD |
| referring_facility | string | |
| transportation | string or null | |
| status_note | string | |

### GET /transfers/{transfer_id}
Single transfer with patient info, documents, and capacity data.

Returns transfer object plus:
- `patient` — patient object
- `documents` — array of document objects
- `capacity` — array of facility capacity records

**document** fields:
| Field | Type | Description |
|---|---|---|
| document_id | string | |
| doc_type | string | Type code (e.g. "hbsag", "monthly_labs", "face_sheet") |
| content_tag | string | "transfer_packet" or "referral_packet" |
| patient_id | string | |
| transfer_id | string or null | |
| referral_id | string or null | |
| received_date | string | YYYY-MM-DD |
| finalized | integer | 1 = final, 0 = draft |
| status | string | "final" or "draft" |
| notes | string | |
| service_date | string or null | |

**capacity** record fields:
| Field | Type | Description |
|---|---|---|
| date | string | YYYY-MM-DD |
| location_id | string | e.g. "CRIC-MAIN", "CRIC-NORTH" |
| modality | string | |
| open_chairs | integer | Available chairs for that date+location |

### GET /documents
List all documents.

### GET /icd/{code}
Look up a single ICD-10 code. Returns:
| Field | Type | Description |
|---|---|---|
| chapter | string | ICD chapter range (e.g. "S00-T88", "J00-J99") |
| code | string | The ICD-10 code |
| description | string | Clinical description |
| laterality | string or null | "left", "right", "bilateral", null |
| service_family | string | e.g. "orthopedics", "pulmonary", "cardiology" |

### GET /programs/{program_code}/candidates
Returns candidate list for a program: `{ "candidates": [...] }`

Candidate fields:
| Field | Type | Description |
|---|---|---|
| patient_id | string | |
| first_name | string | |
| last_name | string | |
| dob | string | |
| email | string or null | |
| phone | string | |
| program_code | string | |
| target_condition | string | |
| consent_status | string | "signed", "declined", or absent |
| adherence_score | integer | |
| preferred_outreach | string | |
| existing_chart | integer | 0 or 1 |
| candidate_date | string | |
| source | string | |

### GET /pharmacies
List all pharmacies.

Pharmacy fields:
| Field | Type | Description |
|---|---|---|
| pharmacy_id | string | Unique (RX001, ...) |
| name | string | |
| address | string | |
| phone | string or null | |
| network_status | string | "in_network" or "out_of_network" |

### POST /query
Read-only SQL endpoint. POST JSON body: `{ "sql": "SELECT ..." }`.

Returns: `{ "columns": [...], "row_count": N, "rows": [...] }`

Only SELECT statements are allowed.

## SQL Tables

| Table | Key columns | Notes |
|---|---|---|
| patients | patient_id | Demographics |
| intake_rosters | roster_id, patient_id | Roster assignments with requested_service_date, service_line |
| coverage | coverage_id, patient_id | Insurance coverage |
| pbm | patient_id | Pharmacy benefit manager |
| patient_pharmacy | patient_id, pharmacy_id | Links patients to pharmacies |
| pharmacies | pharmacy_id | Pharmacy directory with network_status |
| lifestyle | patient_id | Smoking, alcohol, exercise, sleep |
| clinical_history | patient_id | Conditions, hospitalization, surgeries |
| chart_artifacts | artifact_id, patient_id | Chart artifact records |
| referrals | referral_id, batch_id, patient_id | Referral records |
| icd_codes | code | ICD-10 metadata |
| documents | document_id, patient_id, transfer_id, referral_id | All documents |
| transfer_requests | transfer_id, batch_id, patient_id | Dialysis transfers |
| facility_capacity | date, location_id | Chair capacity |
| program_candidates | patient_id, program_code | Program enrollment candidates |

## Cross-table Joins

Common join patterns:
- Patients + coverage: `patients.patient_id = coverage.patient_id`
- Patients + PBM: `patients.patient_id = pbm.patient_id`
- Patients + lifestyle: `patients.patient_id = lifestyle.patient_id`
- Patients + clinical_history: `patients.patient_id = clinical_history.patient_id`
- Patients + pharmacy: `patient_pharmacy JOIN pharmacies ON patient_pharmacy.pharmacy_id = pharmacies.pharmacy_id`
- Referrals + documents: `referrals.referral_id = documents.referral_id`
- Transfers + documents: `transfer_requests.transfer_id = documents.transfer_id`
- Transfers + capacity: match `requested_start_date` against `facility_capacity.date`
