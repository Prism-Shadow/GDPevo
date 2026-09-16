# Cedar Ridge Intake Portal — Data Model Reference

This documents every JSON endpoint available on the Cedar Ridge Intake Coordination Portal, their query parameters, and response shapes. The portal runs at a single base URL (provided as `<TASK_ENV_BASE_URL>` in prompts).

All endpoints return JSON. All are read-only GET, except `POST /query`.

---

## GET / (Home)

Returns an HTML dashboard. Use this page to discover available search forms if you are unsure which endpoint to use, but prefer the API endpoints directly for automated work.

---

## GET /patients

List/search patients.

**Query parameters:**
- `q` — search by name or patient ID (substring match)
- `limit` — max results (default varies)

**Response:**
```json
{
  "count": <int>,
  "patients": [
    {
      "patient_id": "Pnnn",
      "first_name": "...",
      "last_name": "...",
      "dob": "YYYY-MM-DD",
      "address": "..." | null,
      "phone": "..." | null,
      "email": "..." | null,
      "language": "...",
      "emergency_contact_present": 0 | 1,
      "existing_chart": 0 | 1,
      "preferred_contact": "portal" | "email" | "phone" | "sms"
    }
  ]
}
```

---

## GET /patients/{patient_id}

Full patient detail. This is the most important single endpoint for patient-level intake work. It nests linked coverage, PBM, pharmacy, referrals, transfers, rosters, program candidates, documents, lifestyle, clinical history, and chart data.

**Response sections:**

### patient
Basic demographics (same fields as list).

### coverage[] 
Insurance coverage records for this patient.
```json
{
  "coverage_id": <int>,
  "payer": "BlueCross" | "Aetna" | "Cigna" | "Humana" | "Medicare" | "United",
  "policy_number": "POLnnnnn",
  "group_number": "GRPnn",
  "status": "active" | "inactive" | "pending",
  "network_status": "in_network" | "out_of_network",
  "service_lines": "comma,separated,list",
  "effective_date": "YYYY-MM-DD",
  "termination_date": "YYYY-MM-DD"
}
```

### pbm[]
Pharmacy benefit manager records.
```json
{
  "pbm_id": <int>,
  "payer": "...",
  "policy_number": "...",
  "active": 0 | 1,
  "status": "approved" | "rejected" | "pending",
  "formulary_status": "covered" | "not_found",
  "specialty_required": 0 | 1
}
```

### pharmacies[]
Preferred pharmacies for this patient, ranked by preference_rank.
```json
{
  "pharmacy_id": "RXnnn",
  "name": "...",
  "address": "...",
  "phone": "..." | null,
  "network_status": "in_network" | "out_of_network",
  "preference_rank": <int>
}
```

### lifestyle
```json
{
  "patient_id": "...",
  "smoking_status": "Current" | "Former" | "Never",
  "alcohol_use": "Heavy" | "Moderate" | "Light" | "None",
  "exercise_frequency": "None" | "1-2" | "3-4" | "5+",
  "sleep_hours": <float>
}
```

### clinical_history
```json
{
  "patient_id": "...",
  "chronic_conditions": "comma,separated,list" | "",
  "allergy_count": <int>,
  "medication_count": <int>,
  "surgeries": "..." | "none",
  "recent_hospitalization": 0 | 1,
  "risk_flags": "..." | ""
}
```

### referrals[]
All referrals for this patient (may include other batches — filter by batch_id).
```json
{
  "referral_id": "REFnnnn",
  "patient_id": "...",
  "batch_id": "...",
  "service_line": "orthopedics" | "pulmonary" | "cardiology" | "primary_care" | ...,
  "date_received": "YYYY-MM-DD",
  "icd10_code": "...",
  "diagnosis_description": "...",
  "referral_reason": "...",
  "urgency": "urgent" | "routine" | "admin",
  "referring_physician": "...",
  "referring_practice": "...",
  "referring_phone": "...",
  "referring_fax": "...",
  "assigned_physician": "...",
  "payer": "...",
  "insurance_id": "INS-...",
  "auth_required": 0 | 1,
  "auth_status": "approved" | "denied" | "pending" | "not_required",
  "records_received": 0 | 1,
  "imaging_received": 0 | 1,
  "appointment_scheduled": 0 | 1,
  "appointment_date": "YYYY-MM-DD" | null,
  "notes": "..."
}
```

### rosters[]
Intake rosters this patient appears on.
```json
{
  "roster_id": "...",
  "patient_id": "...",
  "service_line": "...",
  "requested_service_date": "YYYY-MM-DD",
  "source_note": "..."
}
```

### transfers[]
Transfers for this patient.
```json
{
  "transfer_id": "TRnnnn",
  "patient_id": "...",
  "batch_id": "...",
  "modality": "in_center_hemodialysis" | ...,
  "days_requested": "Mon/Wed/Fri" | "Tue/Thu/Sat",
  "chair_window": "morning" | "midday" | "evening",
  "requested_start_date": "YYYY-MM-DD",
  "requested_end_date": "YYYY-MM-DD",
  "referring_facility": "...",
  "transportation": "..." | null,
  "status_note": "..."
}
```

### program_candidates[]
Program candidate records.
```json
{
  "program_code": "...",
  "patient_id": "...",
  "target_condition": "...",
  "consent_status": "signed" | "declined" | "missing",
  "source": "registry" | "payer_file" | "provider_panel",
  "candidate_date": "YYYY-MM-DD",
  "adherence_score": <int 0-100>,
  "preferred_outreach": "portal" | "email" | "phone" | "sms"
}
```

### documents[]
Documents linked to this patient.
```json
{
  "document_id": "DOCnnnnn",
  "patient_id": "...",
  "doc_type": "allergy_list" | "face_sheet" | "flu_vaccine" | "hbsag" | "hep_b_antibody_core" | "history_physical" | "insurance_proof" | "medication_list" | "monthly_labs" | "physician_orders" | "pneumonia_vaccine" | "ppd_or_cxr" | "transportation" | "treatment_flowsheets" | "vascular_access_report" | ...,
  "content_tag": "transfer_packet" | ...,
  "received_date": "YYYY-MM-DD",
  "finalized": 0 | 1,
  "status": "final" | "draft",
  "transfer_id": "..." | null,
  "referral_id": "..." | null,
  "service_date": "..." | null
}
```

### chart_artifacts[]
Names of artifacts present in the patient's chart (string array). Common values: `active_problems`, `vitals`, `labs`, `medications`, `allergies`, `consent`, `demographics`.

### active_problems[], meds_allergies[], recent_vitals_labs[]
Additional chart detail arrays — may be empty when data is missing.

---

## GET /referrals

List/search referrals.

**Query parameters:**
- `batch_id` — exact batch match (e.g., `ORTHO-JUN-01`, `PULM-JUN-02`)
- `service_line` — filter by service (e.g., `orthopedics`, `pulmonary`)
- `limit` — max results

**Response:**
```json
{
  "count": <int>,
  "referrals": [ <same shape as referrals[] in /patients/{id}> ]
}
```

---

## GET /referrals/{referral_id}

Single referral detail. Returns the referral object plus linked `patient` demographics, `icd` metadata, and `documents` array.

**icd section:**
```json
{
  "code": "S83.512A",
  "chapter": "S00-T88" | "M00-M99" | "J00-J99" | "I00-I99" | "R00-R99" | ...,
  "description": "...",
  "laterality": "left" | "right" | "bilateral" | null,
  "service_family": "orthopedics" | "pulmonary" | "cardiology" | ...
}
```

---

## GET /transfers

List/search transfers.

**Query parameters:**
- `batch_id` — exact batch match (e.g., `DIAL-WINTER-01`)
- `limit` — max results

**Response:**
```json
{
  "count": <int>,
  "transfers": [ <same shape as transfers[] in /patients/{id}> ]
}
```

---

## GET /transfers/{transfer_id}

Single transfer detail. Returns the transfer plus linked `patient`, `documents` array, and `capacity` array.

**capacity section:**
```json
[
  {
    "location_id": "CRIC-MAIN" | "CRIC-NORTH",
    "date": "YYYY-MM-DD",
    "modality": "in_center_hemodialysis",
    "open_chairs": <int>
  }
]
```
Capacity records cover dates near the transfer's requested_start_date. Sum `open_chairs` across all locations for the target date (or the nearest date where the patient's `days_requested` falls) to get `open_chairs_total`.

---

## GET /documents

List/search documents.

**Query parameters (observed):**
- `patient_id`
- `transfer_id`
- `referral_id`

**Response:**
```json
{
  "count": <int>,
  "documents": [ <same shape as documents[] in /patients/{id}> ]
}
```

---

## GET /chart/{patient_id}

Patient chart detail. Returns `patient` demographics, `clinical_history`, `chart_artifacts` (list of artifact names present), `active_problems`, `meds_allergies`, `recent_vitals_labs`.

Use this endpoint to assess chart completeness. An empty `chart_artifacts` array means no chart exists (chart not active). Specific artifacts are missing if their name does not appear in the array.

---

## GET /programs/{program_code}/candidates

List candidates for a chronic-care program.

**Response:**
```json
{
  "program_code": "DMHTN-2026A",
  "count": <int>,
  "candidates": [
    {
      "patient_id": "...",
      "program_code": "...",
      "target_condition": "diabetes_hypertension" | "copd" | ...,
      "consent_status": "signed" | "declined" | "missing",
      "source": "registry" | "payer_file" | "provider_panel",
      "candidate_date": "YYYY-MM-DD",
      "adherence_score": <int 0-100>,
      "preferred_outreach": "portal" | "email" | "phone" | "sms",
      "first_name": "...",
      "last_name": "...",
      "dob": "YYYY-MM-DD",
      "email": "..." | null,
      "phone": "..." | null,
      "existing_chart": 0 | 1
    }
  ]
}
```

---

## GET /icd/{code}

ICD-10 code metadata.

**Response:**
```json
{
  "icd": {
    "code": "...",
    "chapter": "...",
    "description": "...",
    "laterality": "left" | "right" | "bilateral" | null,
    "service_family": "..."
  }
}
```

---

## GET /pharmacies

List all pharmacies in the Cedar Ridge network.

**Response:**
```json
{
  "count": <int>,
  "pharmacies": [
    {
      "pharmacy_id": "RXnnn",
      "name": "...",
      "address": "...",
      "phone": "..." | null,
      "network_status": "in_network" | "out_of_network"
    }
  ]
}
```

---

## POST /query

Read-only SQL endpoint for cross-table queries.

**Request:**
```json
{"sql": "SELECT ... FROM <table> WHERE ..."}
```

**Response:**
```json
{
  "columns": ["col1", "col2", ...],
  "rows": [{"col1": ..., "col2": ...}, ...],
  "row_count": <int>,
  "truncated": false
}
```

**Known tables:** `intake_rosters` (columns: roster_id, patient_id, requested_service_date, service_line, source_note). Other tables exist; use `SELECT * FROM <table> LIMIT 1` to discover columns.

---

## Cross-Entity Relationships

- A **patient** links to: coverage[], pbm[], pharmacies[], referrals[], transfers[], rosters[], program_candidates[], documents[], clinical_history, lifestyle
- A **referral** links to: patient, icd, documents[]
- A **transfer** links to: patient, documents[], capacity[]
- A **chart** (/chart/{patient_id}) links to: patient, clinical_history, chart_artifacts[]
- A **program candidate** links to: patient (via /patients/{patient_id} for full detail)

The detail endpoints (/patients/{id}, /referrals/{id}, /transfers/{id}) include nested linked records — use them as the primary data source.
