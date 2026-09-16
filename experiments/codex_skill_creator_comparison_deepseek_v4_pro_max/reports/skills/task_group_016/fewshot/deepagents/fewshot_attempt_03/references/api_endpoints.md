# Clinic API Endpoints

Base URL: provided in the task prompt as `<TASK_ENV_BASE_URL>`.

All endpoints are read-only unless noted. No authentication is required in the synthetic environment.

## GET /api/cases

Returns a list of all case records.

**Return shape**: Array of case objects. Each has at minimum `id`, `patientId`, `status`, and `description` fields. Some may embed `presentingComplaint`, `vitalSigns`, or `protocolRefs`.

## GET /api/cases/{case_id}

Returns a single case record.

**Key fields**: `id`, `patientId`, `status`, `description`, `presentingComplaint`, `encounterDate`, `protocolRefs`.

Use this first — the `patientId` unlocks every other endpoint.

## GET /api/patients

Returns a list of all patient records.

**Return shape**: Array of patient objects. Each has `id`, `name` (or `given`/`family`), `birthDate`, `gender`.

## GET /api/patients/{patient_id}

Returns a single patient record.

**Key fields**: `id`, `name`, `birthDate`, `gender`, `address`, `telecom`. Some records embed `careTeam` or `primaryProvider`.

## GET /api/observations

Returns a list of observation resources (lab results, vitals, measurements).

**Key fields per observation**: `id`, `patientId`, `code` (LOINC or local code), `valueQuantity` (with `value` and `unit`), `effectiveDateTime`, `status` (e.g. `final`, `preliminary`, `amended`, `cancelled`).

**Filtering**: The return may be flat. Filter in your code by `patientId` and `code`. Prefer `status: "final"` for clinical decision-making unless `preliminary` is specifically needed.

Common codes:
- `K` — serum potassium (value in mmol/L)
- `2823-3` — serum potassium LOINC
- `SpO2` or `O2Sat` — oxygen saturation (percent)
- `CREAT` or `2160-0` — creatinine
- `EGFR` — estimated GFR
- `HBA1C` or `4548-4` — HbA1c (percent)
- `PHOS` or `2777-1` — phosphorus (mg/dL)
- `BP` — blood pressure (systolic/diastolic)

## GET /api/medications

Returns a list of medication statement/order resources.

**Key fields**: `id`, `patientId`, `medicationCodeableConcept` (with `text` and `coding`), `status` (e.g. `active`, `completed`, `stopped`), `dosage` (with `dose`, `route`, `frequency`), `effectivePeriod`.

## GET /api/allergies

Returns allergy/intolerance resources.

**Key fields**: `id`, `patientId`, `code` (with `text` naming the allergen), `type` (e.g. `allergy`, `intolerance`), `category` (e.g. `medication`, `food`), `criticality`, `reaction` (manifestation descriptions).

Common medication allergens: `penicillin`, `sulfonamide`, `macrolide`, `tetracycline`.

## GET /api/problems

Returns condition/problem resources.

**Key fields**: `id`, `patientId`, `code` (with `text` naming the condition), `clinicalStatus`, `onsetDateTime`.

## GET /api/imaging

Returns imaging study resources.

**Key fields**: `id`, `patientId`, `modality` (e.g. `CXR`, `CT-HEAD`), `bodySite`, `description`, `findings`, `impression`, `performedDateTime`.

## GET /api/care-registry

Returns care-management registry entries.

**Key fields**: `id`, `patientId`, `riskScore` (0–1 probability), `program`, `enrollmentStatus`, `lastContactDate`.

## GET /api/sdoh

Returns social determinants of health observations.

**Key fields**: `id`, `patientId`, `code` (domain like `transportation`, `food-insecurity`, `financial-strain`, `medication-access`), `valueString` or `valueBoolean`.

## GET /api/protocols

Returns a list of protocol resources (clinical decision-support rules).

**Key fields per protocol**: `id`, `title`, `description`, `criteria` (thresholds and conditions), `recommendations` (actions for each branch), `evidenceIds`.

## GET /api/protocols/{protocol_id}

Returns a single protocol with full details including decision logic, thresholds, and care pathways.

## POST /api/query

Accepts a JSON query body with optional `patientId`, `resourceType`, `code`, `dateFrom`, `dateTo`, and `status` filters. Returns matching resources.

**Example body**:

```json
{
  "patientId": "PAT-EXAMPLE",
  "resourceType": "Observation",
  "code": "K",
  "dateFrom": "2026-03-01T00:00:00Z",
  "dateTo": "2026-04-01T00:00:00Z",
  "status": "final"
}
```

Use this when GET endpoints return large unfiltered datasets.
