# Clinic Runtime API Reference

Base URL: `http://task-env:9016/`

No authentication required.

## Endpoints

### GET /api/cases

List all cases (includes distractor records).

**Response shape:**
```json
{
  "count": <int>,
  "items": [
    {
      "case_id": "<string>",
      "case_type": "<string>",
      "patient_id": "<string>",
      "service_date": "<string: YYYY-MM-DD>",
      "status": "active | closed",
      "summary": "<string>"
    }
  ]
}
```

**case_type values seen in environment:** acute_respiratory, pediatric_head_injury, potassium_repletion, observation_window, care_management_routing.

### GET /api/cases/{case_id}

Returns a composite object with all resources related to the case. This is the primary data endpoint for decision-support tasks.

**Top-level keys and their shapes:**

#### case
```json
{
  "case_id": "<string>",
  "case_type": "<string>",
  "patient_id": "<string>",
  "service_date": "<string>",
  "status": "active | closed",
  "summary": "<string>"
}
```

#### patient
```json
{
  "patient_id": "<string>",
  "name": "<string>",
  "age": <int>,
  "birth_date": "<string: YYYY-MM-DD>",
  "sex": "male | female | nonbinary",
  "fhir_id": "<string>"
}
```

#### findings
Array of finding objects. Key-value pairs with source attribution.
```json
[
  {
    "finding_key": "<string>",
    "finding_value": "<string>",
    "source_id": "<string>"
  }
]
```

Common `finding_key` values across task types:
- `current_time` — the clinical review timestamp (ISO-8601 UTC)
- `chief_complaint` — presenting complaint narrative
- `oxygen_room_air_range` — e.g. "92-93%", "below 90%"
- `dyspnea` — description of breathing difficulty
- `pleuritic_chest_pain` — chest pain description
- `confusion` — "absent" or description
- `hemoptysis` — "absent" or description
- `loss_of_consciousness` — "no loss of consciousness" or description
- `vomiting` — "denies vomiting" or description
- `photophobia` — "denies" or description
- `head_impact` — mechanism of injury
- `coordination_symptom` — observed coordination issues
- `nausea` — nausea description
- `target_patient_id` — explicit patient ID for observation-window tasks
- `target_code` — observation code for window tasks
- `window_from` / `window_to` — ISO-8601 window boundaries
- `registry_risk_score` — numeric risk score string
- `allergy_constraint` — allergy summary

#### observations
Array of observation resources.
```json
[
  {
    "observation_id": "<string>",
    "case_id": "<string>",
    "patient_id": "<string>",
    "category": "vital-sign | laboratory | exam | imaging",
    "code": "<string: LOINC or custom>",
    "display": "<string>",
    "effective_time": "<string: ISO-8601 UTC>",
    "status": "final | preliminary",
    "interpretation": "normal | high | low | borderline low | borderline high",
    "value_number": <number | null>,
    "value_text": "<string | null>",
    "unit": "<string | null>",
    "source": "<string>"
  }
]
```

Key observation codes:
- `59408-5` — Oxygen saturation (pulse oximetry)
- `9279-1` — Respiratory rate
- `8480-6` — Systolic blood pressure
- `8310-5` — Body temperature
- `2823-3` — Potassium [Moles/volume] in Serum or Plasma (LOINC)
- `K` — Potassium (custom code used in some datasets)
- `4548-4` — Hemoglobin A1c
- `33914-3` — eGFR
- `9269-2` — Glasgow coma score total

Always check `status` — protocols require "final" results. Preliminary observations (status: "preliminary") should be excluded from clinical decisions.

#### imaging
```json
[
  {
    "imaging_id": "<string>",
    "case_id": "<string>",
    "patient_id": "<string>",
    "study": "<string>",
    "impression": "<string>",
    "performed_at": "<string: ISO-8601 UTC>",
    "status": "final | preliminary"
  }
]
```

#### medications
```json
[
  {
    "medication_id": "<string>",
    "patient_id": "<string>",
    "name": "<string>",
    "code": "<string: RXNORM>",
    "dose": "<string>",
    "route": "<string>",
    "frequency": "<string>",
    "start_date": "<string | null>",
    "end_date": "<string | null>",
    "status": "active | inactive",
    "source": "<string>"
  }
]
```

#### allergies
```json
[
  {
    "id": <int>,
    "patient_id": "<string>",
    "allergen": "<string>",
    "reaction": "<string>",
    "status": "active | inactive"
  }
]
```

Only `status: "active"` allergies constrain medication choices. Common allergen classes: penicillin, sulfonamide antibiotics, macrolide, tetracycline, codeine.

#### problems
```json
[
  {
    "id": <int>,
    "patient_id": "<string>",
    "code": "<string: ICD-10>",
    "name": "<string>",
    "onset_date": "<string>",
    "status": "active | inactive"
  }
]
```

#### sdoh
```json
[
  {
    "id": <int>,
    "patient_id": "<string>",
    "domain": "financial | transportation | food | behavioral_health",
    "evidence": "<string>",
    "severity": "mild | moderate | severe",
    "source": "member-disclosed | chart"
  }
]
```

#### care_registry
Present only for care-management cases. Null otherwise.
```json
{
  "case_id": "<string>",
  "patient_id": "<string>",
  "risk_score": <number: 0.0-1.0>,
  "chronic_condition_count": <int>,
  "medication_count": <int>,
  "recent_admission_date": "<string | null>",
  "dialysis_schedule": "<string | null>",
  "program_hint": "<string | null>"
}
```

### GET /api/patients

List all patients. Response shape mirrors /api/cases with count and items.

### GET /api/patients/{patient_id}

Returns a single patient object. Same shape as the patient sub-object from the case composite.

### GET /api/observations

List all observations. Response has count and items.

### GET /api/medications

List all medications.

### GET /api/allergies

List all allergies.

### GET /api/problems

List all problems.

### GET /api/imaging

List all imaging studies.

### GET /api/care-registry

List all care registry entries.

### GET /api/sdoh

List all SDOH records.

### GET /api/protocols

List protocol summaries.
```json
{
  "count": <int>,
  "items": [
    {
      "protocol_id": "<string>",
      "title": "<string>",
      "version": "<string>"
    }
  ]
}
```

Known protocol IDs:
- RESP-CAP-2026 — Adult Respiratory Infection and CAP Assessment
- PEDS-HEAD-2026 — Pediatric Head Injury Clinic Triage
- K-REPLETION-2026 — Potassium Replacement and Escalation
- CM-HIGH-RISK-2026 — High-Risk Care-Management Routing
- OBS-WINDOW-2026 — Observation Window Interpretation

### GET /api/protocols/{protocol_id}

Returns the full protocol body. Protocols define:
- scope — which cases the protocol applies to
- Controlled codes for observations and tests
- Threshold values for risk stratification and escalation
- Medication rules and allergy constraints
- Follow-up timing
- Return precaution codes
- Authoritative statuses (always ["final"])

### POST /api/query

May require authentication in some environments. When available, sends a parameterized query. The case composite endpoint (/api/cases/{case_id}) is preferred for most tasks.

## Distractors

The environment includes synthetic distractor records (cases, patients, observations that are not the target). Always fetch by the specific case_id from the prompt; do not scan or enumerate records to find the target.
