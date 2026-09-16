# Clinic REST API Endpoints

This reference describes each available REST endpoint and its typical response shape. The exact endpoints available vary per task run; consult the environment access document for the current run.

Base URL is provided via `<TASK_ENV_BASE_URL>` or `environment_access.md`. No credentials are required for these synthetic endpoints.

## Endpoint Reference

### GET /api/cases

Returns a list of all clinic cases.

**Typical response shape:**
```json
[
  {
    "id": "CASE-RESP-001",
    "patient_id": "PAT-9001",
    "status": "active",
    "type": "respiratory",
    "created": "2025-06-15T08:00:00Z",
    "description": "Community-acquired pneumonia evaluation"
  }
]
```

Key fields: `id` (case identifier), `patient_id` (patient link), `status`, `type` (clinical domain), `description`, `created`.

### GET /api/cases/{case_id}

Returns a single case by its identifier.

**Typical response shape:** Same as above, single object.

Always call this first to get the `patient_id` and understand the case domain.

### GET /api/patients

Returns a list of all patients.

**Typical response shape:**
```json
[
  {
    "id": "PAT-9001",
    "name": "Synthetic Patient",
    "birth_date": "1958-04-12",
    "gender": "female"
  }
]
```

### GET /api/patients/{patient_id}

Returns a single patient by identifier.

**Typical response shape:** Same as above, single object.

Call this after retrieving the case to confirm the patient identifier.

### GET /api/observations

Returns clinical observations (lab results, vitals, measurements). This is the most data-rich endpoint.

**Typical response shape:**
```json
[
  {
    "id": "OBS-K-001-20250701-0800",
    "patient_id": "PAT-9002",
    "code": "K",
    "display": "Serum Potassium",
    "value": 3.2,
    "unit": "mmol/L",
    "effective_time": "2025-06-15T08:00:00Z",
    "status": "final",
    "loinc": "2823-3"
  }
]
```

**Key fields to extract:**
- `id` — the observation identifier (use in `evidence_ids` and `observation_id` references)
- `code` — the observation code (e.g., `K` for potassium, `SPO2` for oxygen saturation, `EGFR` for renal function)
- `value` — the numeric result value
- `unit` — the unit of measure
- `effective_time` — when the observation was taken (ISO-8601 UTC with Z)
- `status` — `final`, `preliminary`, `corrected`, `entered-in-error`. Only `final` observations count for clinical decisions unless the protocol says otherwise.
- `loinc` — the LOINC code for ordering follow-up labs

**Filtering observations:**
- Always filter by `patient_id` to the target patient
- Filter by `code` to isolate the lab or measurement you need
- For window-based tasks, apply `effective_time >= from` AND `effective_time < to`
- Sort by `effective_time` when the template demands chronological ordering
- The most recent `final` observation with the target code is usually the one that drives the clinical decision

**Distinguishing distractor observations:**
Observations that don't qualify for inclusion may still need to be listed in `excluded_observation_ids`. An observation is excluded when:
- Its `effective_time` falls outside the target window
- Its `status` is not `final` (e.g., `preliminary`)
- Its `code` doesn't match the target code (e.g., `NA` when looking for `K`)
- It belongs to a different patient

### GET /api/medications

Returns medication records for patients.

**Typical response shape:**
```json
[
  {
    "id": "MED-001",
    "patient_id": "PAT-9002",
    "medication": "lisinopril",
    "ndc": "12345-678-90",
    "status": "active",
    "route": "PO",
    "dose": "10 mg",
    "frequency": "once daily"
  }
]
```

### GET /api/allergies

Returns allergy records. **Always consult this before recommending any medication.**

**Typical response shape:**
```json
[
  {
    "id": "ALL-001",
    "patient_id": "PAT-9001",
    "allergen": "penicillin",
    "reaction": "rash",
    "severity": "moderate"
  }
]
```

Map the `allergen` field to `avoid_allergens` enum values: `penicillin`, `sulfonamide`, `macrolide`, `tetracycline`.

### GET /api/problems

Returns the patient's problem list and chronic conditions.

**Typical response shape:**
```json
[
  {
    "id": "PRB-001",
    "patient_id": "PAT-9003",
    "code": "uncontrolled_diabetes",
    "display": "Uncontrolled Type 2 Diabetes",
    "status": "active"
  }
]
```

### GET /api/imaging

Returns imaging reports and radiology findings.

**Typical response shape:**
```json
[
  {
    "id": "IMG-RESP-001-CXR",
    "patient_id": "PAT-9001",
    "type": "CXR",
    "findings": "Right lower lobe infiltrate consistent with pneumonia",
    "impression": "Community-acquired pneumonia",
    "effective_time": "2025-06-15T10:00:00Z"
  }
]
```

The `id` field is used in `evidence_ids`. The `findings` and `impression` drive clinical assessment decisions.

### GET /api/care-registry

Returns care management registry data including risk scores, program eligibility, and utilization metrics.

**Typical response shape:**
```json
[
  {
    "id": "REG-001",
    "patient_id": "PAT-9003",
    "risk_score": 0.84,
    "hba1c_percent": 9.4,
    "recent_admission": true,
    "dialysis_schedule": "MWF"
  }
]
```

Fields like `risk_score`, `hba1c_percent`, `phosphorus_mg_dl`, `blood_pressure`, `active_medication_count`, `egfr`, and `recent_admission` populate numeric anchors and source provenance.

### GET /api/sdoh

Returns social determinants of health data.

**Typical response shape:**
```json
[
  {
    "id": "SDOH-001",
    "patient_id": "PAT-9003",
    "transportation_barrier": true,
    "financial_food_barrier": false,
    "financial_medication_barrier": true,
    "dialysis_fatigue": true,
    "behavioral_health_need": false
  }
]
```

SDOH data drives priority problem codes, referral codes, escalation conditions, and member disclosure provenance.

### GET /api/protocols

Returns all available clinical protocols.

**Typical response shape:**
```json
[
  {
    "id": "PROTO-RESP-001",
    "domain": "respiratory",
    "title": "Adult Community-Acquired Pneumonia Protocol",
    "version": "1.2"
  }
]
```

### GET /api/protocols/{protocol_id}

Returns a specific protocol with detailed decision rules, thresholds, and escalation criteria.

**Typical response shape:**
```json
{
  "id": "PROTO-RESP-001",
  "domain": "respiratory",
  "title": "Adult Community-Acquired Pneumonia Protocol",
  "criteria": {
    "red_flags": ["hypoxemia_below_90", "confusion", "respiratory_distress"],
    "antibiotic_guidance": {
      "first_line": "doxycycline_outpatient",
      "avoid_with_allergies": ["penicillin", "sulfonamide"]
    },
    "follow_up": "48 hours primary care recheck",
    "imaging": "CXR-2V required"
  }
}
```

Always read the protocol(s) relevant to the case domain. The protocol defines thresholds, escalation criteria, and medication guidance that drive your clinical decisions.

### POST /api/query

A parameterized query endpoint for filtered lookups.

**Typical request body:**
```json
{
  "resource": "observations",
  "patient_id": "PAT-9004",
  "code": "K",
  "status": "final",
  "effective_from": "<WINDOW_START>",
  "effective_to": "<WINDOW_END>"
}
```

Use this when direct GET filtering on a list endpoint is insufficient to narrow results by date range, code, and status simultaneously.

## Query Strategy

1. Start narrow: `GET /api/cases/{case_id}` gives you the patient and domain
2. Branch wide: query observations, medications, allergies, problems, imaging, and protocols in parallel
3. Use `POST /api/query` for filtered lookups when GET endpoints return too many results to filter manually
4. Always read the relevant protocol(s) last, after gathering clinical data, to apply rules to known facts

## Common Response Patterns

- **Observation timing**: the `effective_time` from the most recent `final` observation of the target code determines clinical decisions
- **Lab windows**: month-bounded windows use inclusive start, exclusive end (`from <= effective_time < to`)
- **Numeric precision in API responses**: mmol/L values typically come with one decimal place; percentages with one; risk scores with two
