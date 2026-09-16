# Clinic REST API Reference

## Base URL

All requests target `${TASK_ENV_BASE_URL}` as provided in the task prompt.

## Authentication

No authentication is required for any endpoint.

## Endpoints

### GET /api/cases/{case_id}

**Primary clinical data source.** Returns a composite object that bundles the case, patient, observations, findings, imaging, medications, allergies, problems, care-registry, and SDOH records.

Response shape:

```json
{
  "case": {
    "case_id": "string",
    "case_type": "acute_respiratory | pediatric_head_injury | potassium_repletion | care_management | observation_window",
    "patient_id": "string",
    "service_date": "string (YYYY-MM-DD)",
    "status": "active | closed",
    "summary": "string"
  },
  "patient": {
    "patient_id": "string",
    "fhir_id": "string",
    "name": "string",
    "age": "integer",
    "birth_date": "string (YYYY-MM-DD)",
    "sex": "female | male | nonbinary"
  },
  "observations": [
    {
      "observation_id": "string",
      "case_id": "string",
      "patient_id": "string",
      "category": "laboratory | vital-sign | exam | procedure | imaging | survey",
      "code": "string (LOINC or controlled code)",
      "display": "string",
      "effective_time": "string (ISO-8601 UTC)",
      "status": "final | preliminary | canceled | entered-in-error",
      "interpretation": "string | null",
      "value_number": "number | null",
      "value_text": "string | null",
      "unit": "string | null",
      "source": "string"
    }
  ],
  "findings": [
    {
      "finding_key": "string",
      "finding_value": "string",
      "source_id": "string"
    }
  ],
  "imaging": [
    {
      "imaging_id": "string",
      "case_id": "string",
      "patient_id": "string",
      "study": "string",
      "impression": "string",
      "performed_at": "string (ISO-8601 UTC)",
      "status": "final | preliminary"
    }
  ],
  "medications": [
    {
      "medication_id": "string",
      "patient_id": "string",
      "name": "string",
      "code": "string (RXNORM)",
      "dose": "string",
      "route": "string",
      "frequency": "string",
      "start_date": "string",
      "end_date": "string | null",
      "status": "active | inactive",
      "source": "string"
    }
  ],
  "allergies": [
    {
      "id": "integer",
      "patient_id": "string",
      "allergen": "string",
      "reaction": "string",
      "status": "active | inactive"
    }
  ],
  "problems": [
    {
      "id": "integer",
      "patient_id": "string",
      "code": "string (ICD-10)",
      "name": "string",
      "onset_date": "string",
      "status": "active | inactive"
    }
  ],
  "care_registry": {
    "case_id": "string",
    "patient_id": "string",
    "risk_score": "number",
    "program_hint": "string",
    "chronic_condition_count": "integer",
    "medication_count": "integer",
    "recent_admission_date": "string | null",
    "dialysis_schedule": "string | null"
  } | null,
  "sdoh": [
    {
      "id": "integer",
      "patient_id": "string",
      "domain": "financial | transportation | food | housing",
      "severity": "mild | moderate | severe",
      "evidence": "string",
      "source": "member-disclosed | care-manager note"
    }
  ]
}
```

### GET /api/protocols/{protocol_id}

Returns a specific protocol document. Protocol IDs: `RESP-CAP-2026`, `PEDS-HEAD-2026`, `K-REPLETION-2026`, `CM-HIGH-RISK-2026`, `OBS-WINDOW-2026`.

Response shape:

```json
{
  "protocol_id": "string",
  "title": "string",
  "version": "string",
  "body": {
    "scope": "string",
    "authoritative_statuses": ["final"],
    "controlled_codes": { "...": "string" },
    "...": "protocol-specific decision rules"
  }
}
```

Protocol body contents vary by protocol type. Always read the full body and apply its rules literally.

### GET /api/patients

Lists all patients. Returns `{ "count": N, "items": [...] }`. Each item has: `patient_id`, `name`, `age`, `birth_date`, `sex`, `fhir_id`.

### GET /api/patients/{patient_id}

Returns a single patient record.

### GET /api/cases

Lists all cases. Returns `{ "count": N, "items": [...] }`. Each item has: `case_id`, `case_type`, `patient_id`, `service_date`, `status`, `summary`.

### GET /api/observations

Lists all observations across all cases. Returns `{ "count": N, "items": [...] }`.

### GET /api/medications

Lists all medications across all patients. Returns `{ "count": N, "items": [...] }`.

### GET /api/allergies

Lists all allergies across all patients. Returns `{ "count": N, "items": [...] }`.

### GET /api/problems

Lists all problems across all patients. Returns `{ "count": N, "items": [...] }`.

### GET /api/imaging

Lists all imaging studies. Returns `{ "count": N, "items": [...] }`.

### GET /api/care-registry

Lists all care registry entries. Returns `{ "count": N, "items": [...] }`.

### GET /api/sdoh

Lists all SDOH entries. Returns `{ "count": N, "items": [...] }`.

### GET /api/protocols

Lists available protocol IDs and titles. Returns `{ "count": N, "items": [{ "protocol_id", "title", "version" }] }`.

### POST /api/query

Requires a clinic token. Not available in the standard task environment.

## Key Conventions

- **Patient filtering**: Always match observations, medications, allergies, imaging, problems, and SDOH on `patient_id` from the target case, not just `case_id`.
- **Distractor records**: IDs matching `CASE-D####` or `PAT-D####` are synthetic distractors. Target cases use semantic IDs like `CASE-RESP-102`.
- **Status filtering**: Protocol rules and template logic refer only to `status: "final"` observations and imaging unless otherwise stated.
- **Timestamps**: All timestamps are ISO-8601 UTC with trailing `Z`. Sort chronologically by `effective_time`.
