# Cedar Ridge API Reference

## Base URL

Replace `<TASK_ENV_BASE_URL>` with the actual URL from the task prompt. All endpoints are read-only JSON. No authentication is required.

---

## GET /patients

Returns patient demographic records.

### Query Parameters

| Param | Type | Description |
|---|---|---|
| `q` | string | Search by name or patient ID |
| `limit` | integer | Max results (default 10) |

### Response shape
```json
{
  "count": 100,
  "patients": [
    {
      "address": "101 Cedar Ridge Ave",
      "dob": "1949-02-04",
      "email": "avery.bennett1@example.test",
      "emergency_contact_present": 1,
      "existing_chart": 0,
      "first_name": "Avery",
      "language": "English",
      "last_name": "Bennett",
      "patient_id": "P001",
      "phone": "555-013-0001",
      "preferred_contact": "portal"
    }
  ]
}
```

### Field notes

- `address`: nullable string; null means missing address
- `email`: nullable string
- `phone`: nullable string
- `emergency_contact_present`: 0 or 1
- `preferred_contact`: "portal", "phone", "email", "sms"

---

## GET /patients/{patient_id}

Returns a single patient record. Same shape as a `patients` array element.

---

## GET /referrals

Returns referral records. Use query params for filtering.

### Query Parameters

| Param | Type | Description |
|---|---|---|
| `batch_id` | string | Filter by batch ID |
| `service_line` | string | orthopedics, pulmonary, cardiology, etc. |
| `limit` | integer | Max results |

### Response shape
```json
{
  "count": 81,
  "referrals": [
    {
      "referral_id": "REF0001",
      "batch_id": "<BATCH_ID>",
      "service_line": "orthopedics",
      "date_received": "2026-06-03",
      "patient_id": "P040",
      "payer": "Humana",
      "insurance_id": "INS-P040",
      "referring_physician": "Dr. Patel",
      "referring_practice": "Cedar Ridge PCP",
      "referring_phone": "555-020-0001",
      "referring_fax": "555-021-0001",
      "icd10_code": "S83.512A",
      "diagnosis_description": "specialty consultation",
      "referral_reason": "pain evaluation",
      "urgency": "urgent",
      "records_received": 1,
      "imaging_received": 1,
      "auth_required": 0,
      "auth_status": "approved",
      "appointment_scheduled": 0,
      "appointment_date": null,
      "assigned_physician": "C. Singh",
      "notes": "batch intake"
    }
  ]
}
```

### Field notes

- `records_received`: 0 or 1 — 0 means blocker "records_missing"
- `imaging_received`: 0 or 1 — 0 means blocker "imaging_missing"
- `auth_status`: "approved", "denied", "pending", "not_required"
- `appointment_scheduled`: 0 or 1 — 1 means "already_scheduled" or "scheduled_before_clearance"
- `appointment_date`: nullable string (YYYY-MM-DD)
- `notes`: string — "possible duplicate" or "batch intake" are common values
- `urgency`: "urgent", "routine", "admin"

---

## GET /referrals/{referral_id}

Returns a single referral record.

---

## GET /transfers

Returns dialysis transfer records.

### Query Parameters

| Param | Type | Description |
|---|---|---|
| `batch_id` | string | Filter by batch ID |
| `limit` | integer | Max results |

### Response shape
```json
{
  "count": 6,
  "transfers": [
    {
      "transfer_id": "TR0001",
      "batch_id": "<BATCH_ID>",
      "patient_id": "P014",
      "modality": "in_center_hemodialysis",
      "requested_start_date": "2026-12-08",
      "requested_end_date": "2027-01-05",
      "days_requested": "Mon/Wed/Fri",
      "chair_window": "midday",
      "transportation": "family",
      "referring_facility": "Lakeside Kidney Center",
      "status_note": "seasonal visitor packet"
    }
  ]
}
```

### Field notes

- `modality`: "in_center_hemodialysis"
- `chair_window`: "morning", "midday", "evening"
- `transportation`: nullable string
- `days_requested`: e.g. "Mon/Wed/Fri", "Tue/Thu/Sat"

---

## GET /transfers/{transfer_id}

Returns a single transfer record.

---

## GET /documents

Returns document inventory. Filter by patient and transfer.

### Query Parameters

| Param | Type | Description |
|---|---|---|
| `patient_id` | string | Filter by patient |
| `transfer_id` | string | Filter by transfer |

### Response shape
```json
{
  "count": 14,
  "documents": [
    {
      "document_id": "DOC00001",
      "patient_id": "P014",
      "transfer_id": "TR0001",
      "doc_type": "face_sheet",
      "content_tag": "transfer_packet",
      "received_date": "2026-11-29",
      "status": "final",
      "finalized": 1,
      "referral_id": null,
      "service_date": null,
      "notes": "generated transfer document"
    }
  ]
}
```

### Field notes

- `doc_type`: one of the fifteen transfer packet document types
- `content_tag`: "transfer_packet" for dialysis documents
- `status`: "final" or "draft" — draft documents are not considered received
- `finalized`: 0 or 1 — 0 means the document is a draft, not valid

---

## GET /chart/{patient_id}

Master patient record. Returns the richest dataset — use this as the primary source for patient-level decisions.

### Response shape (selected keys)
```json
{
  "patient": { /* same as GET /patients/{id} */ },
  "chart_artifacts": [
    {
      "artifact_id": 1,
      "artifact_type": "demographics",
      "last_updated": "2026-01-15",
      "patient_id": "P001",
      "status": "current",
      "value_summary": "..."
    }
  ],
  "active_problems": [ /* subset of chart_artifacts with artifact_type active_problems */ ],
  "meds_allergies": [ /* subset with artifact_type medications */ ],
  "recent_vitals_labs": [ /* vitals and labs artifacts */ ],
  "coverage": [
    {
      "coverage_id": 1,
      "patient_id": "P001",
      "payer": "BlueCross",
      "policy_number": "POL00917",
      "group_number": "GRP01",
      "effective_date": "2025-01-01",
      "termination_date": "2026-12-31",
      "network_status": "in_network",
      "service_lines": "chronic_care,pulmonary,primary_care,cardiology",
      "status": "active"
    }
  ],
  "pbm": [
    {
      "pbm_id": 1,
      "patient_id": "P001",
      "payer": "BlueCross",
      "policy_number": "POL00917",
      "active": 1,
      "status": "approved",
      "formulary_status": "covered",
      "specialty_required": 0
    }
  ],
  "pharmacies": [
    {
      "pharmacy_id": "RX004",
      "name": "Cedar Pharmacy 4",
      "address": "704 Wellness Pkwy",
      "phone": "555-019-0004",
      "network_status": "out_of_network",
      "preference_rank": 1
    }
  ],
  "lifestyle": {
    "patient_id": "P001",
    "smoking_status": "Current",
    "alcohol_use": "Moderate",
    "exercise_frequency": "None",
    "sleep_hours": 5.8
  },
  "clinical_history": {
    "patient_id": "P001",
    "chronic_conditions": "cad,asthma",
    "allergy_count": 1,
    "medication_count": 2,
    "recent_hospitalization": 0,
    "surgeries": "none",
    "risk_flags": ""
  },
  "referrals": [ /* patient's referrals */ ],
  "rosters": [ /* patient's rosters */ ],
  "transfers": [ /* patient's transfers */ ],
  "documents": [ /* patient's documents */ ],
  "program_candidates": [ /* programs the patient is a candidate for */ ]
}
```

### Chart artifacts

`artifact_type` values seen in the system: "demographics", "active_problems", "vitals", "labs", "medications", "allergies", "consent"

Each artifact has a `status`: "current" or "stale". Stale artifacts need updating.

Use `chart_artifacts` (full list), `active_problems`, `meds_allergies`, and `recent_vitals_labs` to determine which artifacts exist and their freshness.

---

## GET /programs/{program_code}/candidates

Returns the candidate list for a chronic-care program.

### Response shape
```json
{
  "program_code": "<PROGRAM_CODE>",
  "count": 10,
  "candidates": [
    {
      "patient_id": "P026",
      "program_code": "<PROGRAM_CODE>",
      "first_name": "Finley",
      "last_name": "Hughes",
      "dob": "1959-03-25",
      "email": "finley.hughes26@example.test",
      "phone": "555-013-0026",
      "candidate_date": "2026-06-20",
      "source": "registry",
      "target_condition": "diabetes_hypertension",
      "consent_status": "signed",
      "adherence_score": 40,
      "existing_chart": 1,
      "preferred_outreach": "portal"
    }
  ]
}
```

### Field notes

- `target_condition`: must match the program's condition domain
- `consent_status`: "signed", "declined", or "missing"
- `adherence_score`: integer 0-100, lower = worse adherence
- `source`: "registry", "payer_file", or "provider_panel"
- `preferred_outreach`: "portal", "phone", "email", "sms"

---

## GET /icd/{code}

Returns ICD-10 code metadata.

### Response shape
```json
{
  "icd": {
    "code": "J44.9",
    "description": "Chronic obstructive pulmonary disease",
    "chapter": "J00-J99",
    "laterality": null,
    "service_family": "pulmonary"
  }
}
```

### Field notes

- `chapter`: ICD-10 chapter range (e.g. "J00-J99", "M00-M99", "S00-T88", "I00-I99", "R00-R99")
- `service_family`: clinical domain ("orthopedics", "pulmonary", "cardiology", etc.)
- `laterality`: null or "left"/"right" for codes with sidedness

---

## GET /pharmacies

Returns the pharmacy directory.

### Response shape
```json
{
  "count": 35,
  "pharmacies": [
    {
      "pharmacy_id": "RX001",
      "name": "Cedar Pharmacy 1",
      "address": "701 Wellness Pkwy",
      "phone": "555-019-0001",
      "network_status": "in_network"
    }
  ]
}
```

---

## POST /query

Read-only SQL endpoint. Accepts JSON body with `{"sql": "..."}`.

### Response shape
```json
{
  "columns": ["referral_id", "batch_id", "patient_id"],
  "rows": [ { "referral_id": "REF0001", "..." : "..." } ],
  "row_count": 9,
  "truncated": false
}
```

### Known tables

- `intake_rosters`: roster_id, patient_id, requested_service_date, service_line
- `referrals`: same columns as GET /referrals response fields
- `transfers`: same columns as GET /transfers response fields
- `patients`: same columns as GET /patients response fields

Use SELECT only. ORDER BY, GROUP BY, COUNT, and WHERE are supported.
