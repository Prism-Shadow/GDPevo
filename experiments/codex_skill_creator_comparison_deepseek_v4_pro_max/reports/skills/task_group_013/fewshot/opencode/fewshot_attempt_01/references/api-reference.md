# Cedar Ridge Intake Coordination Portal — API Reference

Complete field-level documentation for every available endpoint. All endpoints return JSON unless noted.

---

## GET `/`

Returns the portal landing page as HTML. Not used for data extraction.

---

## GET `/patients`

List or search patients.

**Query parameters:**
- `q` — search by name or patient_id
- `limit` — max results (default appears to be unbounded; set high to get all)

**Response shape:**
```json
{
  "count": 100,
  "patients": [
    {
      "patient_id": "P001",
      "first_name": "Avery",
      "last_name": "Bennett",
      "dob": "1949-02-04",
      "email": "avery.bennett1@example.test",
      "phone": "555-013-0001",
      "address": "101 Cedar Ridge Ave",
      "language": "English",
      "preferred_contact": "portal",
      "emergency_contact_present": 1,
      "existing_chart": 0
    }
  ]
}
```

**Fields:**
- `patient_id` — string, e.g. "P001"
- `first_name`, `last_name` — string
- `dob` — date string YYYY-MM-DD
- `email` — string or null
- `phone` — string or null
- `address` — string or null
- `language` — string
- `preferred_contact` — "portal", "email", "phone", "sms"
- `emergency_contact_present` — 0 or 1
- `existing_chart` — 0 or 1

---

## GET `/patients/{patient_id}`

Full composite patient record. This is the richest single endpoint.

**Response shape:**
```json
{
  "patient": { ... },
  "coverage": [ ... ],
  "pbm": [ ... ],
  "pharmacies": [ ... ],
  "lifestyle": { ... },
  "clinical_history": { ... },
  "rosters": [ ... ],
  "referrals": [ ... ],
  "transfers": [ ... ],
  "program_candidates": [ ... ],
  "chart_artifacts": [ ... ],
  "documents": [ ... ]
}
```

### `patient` object
Same fields as the `/patients` list item above.

### `coverage[]` — insurance coverage records
```json
{
  "coverage_id": 1,
  "patient_id": "P001",
  "payer": "BlueCross",
  "policy_number": "POL00917",
  "group_number": "GRP01",
  "status": "active",
  "effective_date": "2025-01-01",
  "termination_date": "2026-12-31",
  "network_status": "in_network",
  "service_lines": "chronic_care,pulmonary,primary_care,cardiology"
}
```
- `status` — "active", "expired", "pending", "terminated"
- `service_lines` — comma-separated string of covered service lines
- `network_status` — "in_network" or "out_of_network"

### `pbm[]` — pharmacy benefit manager records
```json
{
  "pbm_id": 1,
  "patient_id": "P001",
  "payer": "BlueCross",
  "policy_number": "POL00917",
  "status": "approved",
  "active": 1,
  "formulary_status": "covered",
  "specialty_required": 0
}
```
- `status` — "approved", "rejected", "pending"
- `active` — 0 or 1
- `formulary_status` — "covered", "not_found", "review"
- `specialty_required` — 0 or 1

### `pharmacies[]` — preferred pharmacy records
```json
{
  "pharmacy_id": "RX004",
  "name": "Cedar Pharmacy 4",
  "address": "704 Wellness Pkwy",
  "phone": "555-019-0004",
  "network_status": "out_of_network",
  "preference_rank": 1
}
```
- `network_status` — "in_network" or "out_of_network"
- `preference_rank` — integer, 1 is most preferred

### `lifestyle` object
```json
{
  "patient_id": "P001",
  "alcohol_use": "Moderate",
  "smoking_status": "Current",
  "exercise_frequency": "None",
  "sleep_hours": 5.8
}
```
- `alcohol_use` — "None", "Occasional", "Moderate", "Heavy"
- `smoking_status` — "Never", "Former", "Current"
- `exercise_frequency` — "None", "1-2", "3-4", "5+" or null
- `sleep_hours` — float

### `clinical_history` object
```json
{
  "patient_id": "P001",
  "chronic_conditions": "cad,asthma",
  "allergy_count": 1,
  "medication_count": 2,
  "recent_hospitalization": 0,
  "surgeries": "none",
  "risk_flags": ""
}
```
- `chronic_conditions` — comma-separated condition codes
- `recent_hospitalization` — 0 or 1
- `risk_flags` — string, may contain flags like "complex_medication_reconciliation"
- `surgeries` — string

### `rosters[]` — intake roster entries
```json
{
  "roster_id": "NPI-JUN-01",
  "patient_id": "P001",
  "requested_service_date": "2026-06-18",
  "service_line": "primary_care",
  "source_note": "new patient intake roster"
}
```

### `referrals[]` — referral records (same shape as `/referrals` list items)

### `transfers[]` — transfer records (same shape as `/transfers` list items)

### `program_candidates[]` — program candidate entries
```json
{
  "program_code": "DMHTN-2026A",
  "patient_id": "P026",
  "target_condition": "diabetes_hypertension",
  "consent_status": "signed",
  "adherence_score": 40,
  "source": "registry",
  "candidate_date": "2026-06-20",
  "preferred_outreach": "portal"
}
```
- `consent_status` — "signed", "declined", "missing"
- `target_condition` — program-specific condition code
- `source` — "registry", "payer_file", "provider_panel"
- `preferred_outreach` — "portal", "phone", "email", "sms"

### `chart_artifacts[]` — chart artifact records
```json
{
  "artifact_id": 6,
  "patient_id": "P026",
  "artifact_type": "active_problems",
  "status": "current",
  "last_updated": "2025-12-15",
  "value_summary": "active_problems summary for P026"
}
```
- `artifact_type` — "active_problems", "consent", "labs", "medications", "vitals", "demographics", "care_plan", "allergies", "imaging"
- `status` — "current" or "stale"

### `documents[]` — document records
```json
{
  "document_id": "DOC00042",
  "patient_id": "P017",
  "doc_type": "insurance_proof",
  "content_tag": "transfer_packet",
  "received_date": "2026-12-05",
  "status": "draft",
  "finalized": 0,
  "transfer_id": "TR0004",
  "referral_id": null,
  "service_date": null,
  "notes": "generated transfer document"
}
```
- `doc_type` — see the document type list in decision-logic.md
- `content_tag` — "transfer_packet", "referral_record", etc.
- `status` — "draft", "final"
- `finalized` — 0 or 1

---

## GET `/referrals`

List or search referrals.

**Query parameters:**
- `batch_id` — filter by batch
- `service_line` — "orthopedics", "pulmonary", "cardiology", "neurology", etc.
- `limit` — max results

**Response shape:**
```json
{
  "count": 9,
  "referrals": [
    {
      "referral_id": "REF0001",
      "batch_id": "ORTHO-JUN-01",
      "patient_id": "P040",
      "service_line": "orthopedics",
      "urgency": "urgent",
      "date_received": "2026-06-03",
      "icd10_code": "S83.512A",
      "diagnosis_description": "specialty consultation",
      "referral_reason": "pain evaluation",
      "referring_physician": "Dr. Patel",
      "referring_practice": "Cedar Ridge PCP",
      "referring_phone": "555-020-0001",
      "referring_fax": "555-021-0001",
      "assigned_physician": "C. Singh",
      "insurance_id": "INS-P040",
      "payer": "Humana",
      "auth_required": 0,
      "auth_status": "approved",
      "records_received": 1,
      "imaging_received": 1,
      "appointment_scheduled": 0,
      "appointment_date": null,
      "notes": "batch intake"
    }
  ]
}
```

**Key fields:**
- `urgency` — "urgent", "routine", "admin"
- `auth_status` — "approved", "denied", "pending", "not_required", "not_submitted"
- `auth_required` — 0 or 1
- `records_received` — 0 or 1
- `imaging_received` — 0 or 1
- `appointment_scheduled` — 0 or 1
- `appointment_date` — date or null

---

## GET `/referrals/{referral_id}`

Returns a single referral record with the same shape as a list item.

---

## GET `/transfers`

List or search transfers.

**Query parameters:**
- `batch_id` — filter by batch
- `limit` — max results

**Response shape:**
```json
{
  "count": 6,
  "transfers": [
    {
      "transfer_id": "TR0001",
      "batch_id": "DIAL-WINTER-01",
      "patient_id": "P014",
      "modality": "in_center_hemodialysis",
      "referring_facility": "Lakeside Kidney Center",
      "days_requested": "Mon/Wed/Fri",
      "chair_window": "midday",
      "requested_start_date": "2026-12-08",
      "requested_end_date": "2027-01-05",
      "transportation": "family",
      "status_note": "seasonal visitor packet"
    }
  ]
}
```

**Key fields:**
- `modality` — "in_center_hemodialysis"
- `chair_window` — "morning", "midday", "evening"
- `days_requested` — e.g. "Mon/Wed/Fri", "Tue/Thu/Sat"
- `transportation` — "family", "ride_share", "medical_transport" or null
- `status_note` — free text

---

## GET `/transfers/{transfer_id}`

Returns a single transfer record.

---

## GET `/documents`

List or search documents.

**Response shape:**
```json
{
  "count": 100,
  "documents": [
    {
      "document_id": "DOC00042",
      "patient_id": "P017",
      "doc_type": "insurance_proof",
      "content_tag": "transfer_packet",
      "received_date": "2026-12-05",
      "status": "draft",
      "finalized": 0,
      "transfer_id": "TR0004",
      "referral_id": null,
      "service_date": null,
      "notes": "generated transfer document"
    }
  ]
}
```

Documents link to patients and optionally to a `transfer_id` or `referral_id`. The `content_tag` indicates the document category ("transfer_packet", "referral_record"). Documents with `finalized: 0` or `status: "draft"` are incomplete and should be treated as absent when checking packet completeness.

---

## GET `/chart/{patient_id}`

Detailed chart view for a patient.

**Response shape:**
```json
{
  "patient": { ... },
  "clinical_history": { ... },
  "active_problems": [ ... ],
  "chart_artifacts": [ ... ],
  "meds_allergies": [ ... ],
  "recent_vitals_labs": [ ... ]
}
```

- `active_problems[]` — subset of chart_artifacts where artifact_type is "active_problems"
- `meds_allergies[]` — subset where artifact_type is "medications" or "allergies"
- `recent_vitals_labs[]` — subset where artifact_type is "vitals" or "labs"
The chart endpoint includes artifacts organized by category, making it easier to determine what's present, missing, or stale for chart-activation workflows. Artifact status "stale" means the artifact exists but is outdated. Artifact status "current" means it's up to date.

---

## GET `/programs/{program_code}/candidates`

Returns all candidates for a given program.

**Response shape:**
```json
{
  "program_code": "DMHTN-2026A",
  "count": 10,
  "candidates": [
    {
      "program_code": "DMHTN-2026A",
      "patient_id": "P026",
      "first_name": "Finley",
      "last_name": "Hughes",
      "dob": "1959-03-25",
      "email": "finley.hughes26@example.test",
      "phone": "555-013-0026",
      "existing_chart": 1,
      "target_condition": "diabetes_hypertension",
      "consent_status": "signed",
      "adherence_score": 40,
      "source": "registry",
      "candidate_date": "2026-06-20",
      "preferred_outreach": "portal"
    }
  ]
}
```

This endpoint returns a flat list of candidates with basic demographics plus program-specific fields. For detailed clinical and coverage data, follow up with `/patients/{patient_id}` and `/chart/{patient_id}`.

---

## GET `/icd/{code}`

ICD-10 code metadata.

**Response shape:**
```json
{
  "icd": {
    "code": "S83.512A",
    "chapter": "S00-T88",
    "description": "Sprain of anterior cruciate ligament of left knee",
    "laterality": "left",
    "service_family": "orthopedics"
  }
}
```

- `chapter` — ICD-10 chapter range, e.g. "S00-T88", "M00-M99", "J00-J99", "I00-I99", "R00-R99"
- `service_family` — clinical domain: "orthopedics", "pulmonary", "cardiology", etc.
- `laterality` — "left", "right", "bilateral", or null

---

## GET `/pharmacies`

Pharmacy directory.

**Response shape:**
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

## POST `/query`

Read-only SQL endpoint. Send a JSON body with the SQL statement.

**Request:**
```json
{"sql": "SELECT * FROM intake_rosters WHERE roster_id = 'NPI-JUN-01'"}
```

**Response:**
```json
{
  "columns": ["roster_id", "patient_id", "requested_service_date", "service_line", "source_note"],
  "rows": [ ... ],
  "row_count": 6,
  "truncated": false
}
```

Tables include: `patients`, `coverage`, `pbm`, `pharmacies`, `lifestyle`, `clinical_history`, `intake_rosters`, `referrals`, `transfers`, `documents`, `chart_artifacts`, `program_candidates`. Discover the full schema with `SELECT name FROM sqlite_master WHERE type='table'`.

Use this endpoint when:
- You need to cross-reference records across tables that don't join naturally via the REST endpoints.
- You need aggregate counts that the REST endpoints don't provide directly.
- The REST endpoints don't expose a column you need (some tables have columns not surfaced in REST responses).

Always use read-only SELECT statements. INSERT, UPDATE, DELETE, and DDL will fail.
