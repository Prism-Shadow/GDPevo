# Clinic API Conventions

The clinic runtime exposes a FHIR-inspired REST API. Understanding these
patterns will help you retrieve the right data efficiently.

## Base URL

The base URL is provided via `TASK_ENV_BASE_URL` in the environment access
listing. All endpoints are relative to this base. No authentication headers are
needed for the endpoints listed in the access document.

## Resource Types

### Case (`/api/cases`, `/api/cases/{case_id}`)

The case resource represents a clinical encounter. Key fields:
- `id` -- the case identifier (e.g. `CASE-EX-200`)
- `patient` -- a reference to the patient resource, usually containing the
  patient ID
- `observations` -- array of references to relevant observation resources
- `imaging` -- array of references to relevant imaging studies
- `medications` -- array of references to relevant medication statements
- `allergies` -- array of references to relevant allergy intolerance resources
- `problems` -- array of references to relevant condition/problem resources

Always start with the case; it maps to everything else.

### Patient (`/api/patients`, `/api/patients/{patient_id}`)

Demographics and administrative details. Key fields:
- `id` -- the patient identifier (e.g. `PAT-EX-100`)
- `name`, `birthDate`, `gender` -- demographics
- Extensions may carry risk scores or registry flags.

### Observation (`/api/observations`)

Individual clinical measurements and lab results. Key fields:
- `id` -- observation identifier (e.g. `OBS-EX-SPO2`)
- `code` -- what was measured (e.g. LOINC `2823-3` for potassium, or local codes
  like `K` for potassium, `SPO2` for oxygen saturation)
- `valueQuantity` -- the numeric result with value, unit, and sometimes comparator
- `effectiveDateTime` -- when the observation was taken (ISO-8601)
- `status` -- `final`, `preliminary`, `amended`, `entered-in-error`, etc.
- `subject` -- reference to the patient

**Critical**: Filter by `status: "final"` when the task requires final results.
Preliminary results are not clinically actionable and should be excluded from
matched observation lists (they go to excluded lists instead).

The `code` field may use LOINC codes, local codes, or both. Cross-reference with
the template's `target_code` or the protocol's expected codes.

### Imaging (`/api/imaging`)

Imaging studies and reports. Key fields:
- `id` -- imaging study identifier (e.g. `IMG-EX-CXR`)
- `modality` -- e.g. `CXR` (chest X-ray), `CT-HEAD`
- `findings` -- narrative report text
- `impression` -- summary of findings

### Medication (`/api/medications`)

Medication statements for the patient. Key fields:
- `id`
- `medicationCodeableConcept` -- the medication name/code
- `status` -- `active`, `completed`, `stopped`, etc.
- `dosage` -- dose, route, frequency, and timing

### Allergy (`/api/allergies`)

Allergy intolerance records. Key fields:
- `id`
- `code` -- the allergen (e.g. penicillin, sulfonamide)
- `type` -- `allergy`, `intolerance`
- `reaction` -- manifestations

### Problem (`/api/problems`)

Problem list / condition resources. Key fields:
- `id`
- `code` -- the diagnosis or problem code
- `clinicalStatus` -- `active`, `resolved`, `inactive`, etc.

### Protocol (`/api/protocols`, `/api/protocols/{protocol_id}`)

Clinical decision-support protocols. Key fields:
- `id`
- `title` -- protocol name
- `thresholds` -- numeric cutoffs for risk stratification
- `recommendations` -- structured decision rules (e.g. "if SpO2 below 92% then
  moderate risk")
- `medicationGuidance` -- preferred agents, dosing, and avoidance rules

### Care Registry (`/api/care-registry`)

Care management registry data. Key fields:
- `id`
- `riskScore` -- a numeric probability (0.0 to 1.0)
- `programEligibility` -- flags for care management programs
- `utilization` -- recent admission/ED visit flags

### SDOH (`/api/sdoh`)

Social determinants of health observations. Key fields:
- `id`
- `code` -- the SDOH domain (transportation, financial, food security, etc.)
- `value` -- the finding

## Observation Date Windows

When a template specifies a date window (e.g. `from` / `to` fields for a
lab-window task), the `from` is inclusive and the `to` is exclusive:
`effectiveDateTime >= from AND effectiveDateTime < to`.

Observations that fall outside the window, have a non-matching code, or have a
non-final status should go into the excluded list (when the template asks for
one) rather than the matched list.

## HTTP Details

All endpoints are read-only GET except `POST /api/query` which accepts a JSON
body for parameterized searches. The content type for POST is
`application/json`.

When querying collection endpoints, you may receive paginated results. If an
endpoint returns a `link` header with `rel="next"`, follow it to retrieve the
next page.

Timestamps are always ISO-8601 UTC with trailing `Z`. When computing a future
time (e.g. follow-up scheduling), add the protocol-specified interval to the
current review timestamp.
