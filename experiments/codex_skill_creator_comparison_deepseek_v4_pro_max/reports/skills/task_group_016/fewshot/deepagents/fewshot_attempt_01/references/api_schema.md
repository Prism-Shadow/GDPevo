## API Schema Reference

### GET /api/patients

Returns `count` and `items`, each item having `age`, `birth_date`, `fhir_id`,
`name`, `patient_id`, `sex`. `patient_id` is the stable key for joining across
all resources.

### GET /api/patients/{patient_id}

Returns a single patient object (same shape as items in the list).

### GET /api/cases

Returns `count` and `items`, each with `case_id`, `case_type`, `patient_id`,
`service_date`, `status`, `summary`.

Known `case_type` values: `acute_respiratory`, `pediatric_head_injury`,
`potassium_repletion`, `care_management`, `observation_window`.

### GET /api/cases/{case_id} (composite endpoint)

Returns one JSON object with these keys:

| Key | Type | Description |
|-----|------|-------------|
| `case` | object | The case summary |
| `patient` | object | The linked patient record |
| `observations` | array | All observations for this case |
| `findings` | array | Clinical finding key-value pairs with source IDs |
| `imaging` | array | Imaging studies for this case |
| `medications` | array | Active/inactive medications for the patient |
| `allergies` | array | Allergy records for the patient |
| `problems` | array | Problem-list entries for the patient |
| `care_registry` | object or null | Care-management registry entry |
| `sdoh` | array | Social determinants of health records |

#### observations

Each observation has:

| Field | Type | Notes |
|-------|------|-------|
| `observation_id` | string | Stable identifier |
| `patient_id` | string | Patient reference |
| `case_id` | string | Case reference |
| `category` | string | `vital-sign`, `laboratory`, `imaging`, `procedure` |
| `code` | string | LOINC or controlled code |
| `display` | string | Human-readable label |
| `status` | string | `final`, `preliminary`, `canceled`, `entered-in-error` |
| `effective_time` | string | ISO-8601 UTC timestamp |
| `interpretation` | string | `normal`, `low`, `high`, `abnormal`, `borderline_low`, `negative`, `mildly_low` |
| `value_number` | number or null | Numeric result |
| `value_text` | string or null | Text result |
| `unit` | string or null | Unit of measure |
| `source` | string | Origin system |

Important codes:
- `"K"` = serum potassium
- `"59408-5"` = SpO2 (oxygen saturation)
- `"33914-3"` = eGFR
- `"9279-1"` = respiratory rate
- `"8310-5"` = body temperature
- `"8480-6"` = systolic blood pressure
- `"CXR-2V"` = chest x-ray result
- `"SARS_FLU_RSV_PCR"` = respiratory viral panel
- `"PULSE_OX_RECHECK"` = pulse oximetry recheck
- `"ECG-SUMMARY"` = ECG interpretation
- `"NA"` = sodium
- `"2823-3"` = potassium follow-up lab (LOINC)

#### findings

Each finding has `finding_key`, `finding_value`, and `source_id`. Used for
non-observation clinical facts: `current_time`, `chief_complaint`, symptoms,
allergy constraints, registry data, SDOH barriers.

#### imaging

| Field | Type |
|-------|------|
| `imaging_id` | string |
| `patient_id` | string |
| `case_id` | string |
| `study` | string |
| `impression` | string |
| `status` | `final` or `preliminary` |
| `performed_at` | ISO-8601 timestamp |

#### medications

| Field | Type |
|-------|------|
| `medication_id` | string |
| `patient_id` | string |
| `name` | string |
| `code` | string (RxNorm) |
| `dose` | string |
| `route` | string |
| `frequency` | string |
| `status` | `active` or `inactive` |
| `start_date` | string |
| `end_date` | string or null |

#### allergies

| Field | Type |
|-------|------|
| `id` | integer |
| `patient_id` | string |
| `allergen` | string (e.g. "penicillin", "sulfonamide antibiotics") |
| `reaction` | string |
| `status` | `active` or `inactive` |

#### problems

| Field | Type |
|-------|------|
| `id` | integer |
| `patient_id` | string |
| `code` | string (ICD-10) |
| `name` | string |
| `onset_date` | string |
| `status` | `active` or `inactive` |

#### care_registry

| Field | Type |
|-------|------|
| `patient_id` | string |
| `case_id` | string |
| `risk_score` | number (0-1 probability) |
| `chronic_condition_count` | integer |
| `medication_count` | integer |
| `recent_admission_date` | string or null |
| `dialysis_schedule` | string or null |
| `program_hint` | string |

#### sdoh

| Field | Type |
|-------|------|
| `id` | integer |
| `patient_id` | string |
| `domain` | string (`financial`, `transportation`, `food`, `housing`) |
| `severity` | string (`mild`, `moderate`, `severe`) |
| `evidence` | string |
| `source` | string (`member-disclosed`, `care-manager note`) |

### GET /api/protocols

Returns list of protocols with `protocol_id`, `title`, `version`.

### GET /api/protocols/{protocol_id}

Returns a protocol document with `protocol_id`, `title`, `version`, and `body`
(the decision rules). See protocol_guide.md for interpretation.

### Other list endpoints

`/api/observations`, `/api/medications`, `/api/allergies`, `/api/problems`,
`/api/imaging`, `/api/care-registry`, `/api/sdoh`: each returns `count` and
`items`. Items match the shapes described above under the case composite.
