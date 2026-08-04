---
name: clinic-decision-support
description: Structured clinical decision-support responses using a synthetic clinic runtime environment. Use when the task provides a prompt.txt describing a clinical scenario, an answer_template.json defining the output schema, and access to the clinic API at <TASK_ENV_BASE_URL>.
---

# Clinic Decision Support Skill

## Overview

This skill handles structured clinical decision-support tasks for a synthetic clinic runtime. Each task supplies a scenario prompt, a JSON answer template, and read-only API access to clinic data. The skill produces a single JSON object matching the template by querying the clinic environment and reasoning clinically over the retrieved data.

## Workflow

### Step 1 — Orient to the task

Read the task prompt (typically `prompt.txt`) to identify:

- The **clinical scenario** and decision being requested
- The **target case identifier** (e.g., `CASE-RESP-102`, `CASE-HEAD-207`)
- Any domain-specific guidance or constraints

### Step 2 — Load the answer template

Read the answer template (typically `answer_template.json`). This document defines:

- **`required_top_level_keys`** or **`required_keys`** — every key the output JSON must include
- **`fields`** — per-field type constraints, allowed values (enums), nullability rules, nesting structure, and ordering rules
- Any **`required_value`** constraints that force specific literal values for fields like `task_id` or `case_id`
- **`additional_properties`** guidance (usually ignored unless they conflict with required fields)

Construct the output object by following the template field-by-field, populating from API data and clinical reasoning.

### Step 3 — Query the clinic runtime environment

All API calls use the base URL provided as `<TASK_ENV_BASE_URL>` (read from `environment_access.md` or equivalent). The environment provides the following endpoints:

#### GET endpoints (read-only resources)

| Endpoint | Purpose |
|---|---|
| `GET /api/patients` | List or search patients |
| `GET /api/patients/{patient_id}` | Single patient record |
| `GET /api/cases` | List or search cases |
| `GET /api/cases/{case_id}` | Single case record with encounter details |
| `GET /api/observations` | Lab results, vitals, clinical observations |
| `GET /api/medications` | Medication records |
| `GET /api/allergies` | Allergy and intolerance records |
| `GET /api/problems` | Problem list / diagnoses |
| `GET /api/imaging` | Imaging studies and reports |
| `GET /api/care-registry` | Care management registry data |
| `GET /api/sdoh` | Social determinants of health |
| `GET /api/protocols` | Available clinical protocols |
| `GET /api/protocols/{protocol_id}` | Single protocol detail |

Use query parameters to filter by `patient_id`, `case_id`, `code`, `date` ranges, or `status` as needed. The API responses are FHIR-like JSON bundles.

#### POST /api/query — SQL access

For complex joins or aggregations not easily expressed through GET filters, use the SQL endpoint:

```
POST /api/query
Content-Type: application/json
X-Clinic-Token: synclinic-readonly
```

Request body:

```json
{
  "sql": "<SELECT statement>",
  "params": []
}
```

Rules:
- `sql` must be a `SELECT` statement over public tables
- `params` provides positional or named bind parameters
- The `X-Clinic-Token: synclinic-readonly` header is required on every call
- Use parameterized queries; do not concatenate user input into SQL strings

Example:

```bash
curl -sS -X POST "$BASE_URL/api/query" \
  -H 'Content-Type: application/json' \
  -H 'X-Clinic-Token: synclinic-readonly' \
  --data '{"sql":"SELECT * FROM cases WHERE case_id = ?","params":["CASE-RESP-102"]}'
```

### Step 4 — Retrieve case-specific data

For a given case, retrieve the relevant clinical record:

1. **Case record**: `GET /api/cases/{case_id}` to obtain the patient link, encounter context, and case metadata
2. **Patient record**: `GET /api/patients/{patient_id}` for demographics and background
3. **Observations**: Filter `GET /api/observations` by patient and/or date range to find relevant lab results, vitals, and clinical scores
4. **Imaging**: `GET /api/imaging` filtered by case or patient for relevant studies
5. **Allergies**: `GET /api/allergies` filtered by patient for contraindication screening
6. **Medications**: `GET /api/medications` filtered by patient for medication history and reconciliation
7. **Protocols**: `GET /api/protocols` or `GET /api/protocols/{protocol_id}` for clinical pathway rules, thresholds, and decision logic
8. **Care Registry**: `GET /api/care-registry` for risk scores, program eligibility, and care-management context
9. **SDOH**: `GET /api/sdoh` for social-context facts affecting care planning
10. **Problems**: `GET /api/problems` for the active problem list

Use the SQL endpoint when you need cross-resource logic, aggregations, or windowed queries not supported by the GET filters.

### Step 5 — Apply clinical reasoning

Use the template's allowed values and the protocol data retrieved from the environment to determine:

- **Primary assessment / diagnosis** — map clinical findings to the template's assessment enum
- **Risk tier / risk level** — apply protocol-defined thresholds (e.g., CURB-65, PECARN, potassium ranges, risk scores)
- **Red flags** — identify which protocol-specified red flags are present, and which are absent
- **Disposition** — determine the correct care setting (outpatient, ED, home observation, etc.)
- **Medication plan** — select medication, dose, route, frequency, and duration from protocol guidance, cross-referencing allergy data
- **Tests / imaging** — identify recommended diagnostics from protocol rules
- **Follow-up** — determine timing and route from protocol and clinical severity
- **Return precautions** — list conditions that should prompt the patient to seek urgent care
- **Evidence identifiers** — cite the specific observation, imaging, case, or protocol IDs that support each decision
- **Safety checks** — assert that dangerous claims are not being made (e.g., no claim of normal CXR when CXR was not performed, no false claim of no loss of consciousness when LOC status is unknown)

### Step 6 — Construct and validate the output JSON

1. Start with the template's required keys in the order specified
2. Fill each field with the appropriate value type from the template definition
3. For enum fields, use only `allowed_values` from the template
4. For nullable fields, use `null` (not the string `"null"`) when the template permits it
5. For numeric values, match the precision and units specified in the template
6. For timestamps, use ISO-8601 UTC format (e.g., `"2026-03-01T00:00:00Z"`)
7. For lists, follow any ordering rule in the template (e.g., sort by `effective_time` ascending, or treat as unordered sets)
8. For nested objects, ensure all `required_keys` are present
9. Validate that safety-check booleans are consistent with the data (e.g., `no_normal_cxr_claim: true` means you are not asserting the CXR was normal)

### Step 7 — Return the JSON object

Output only the JSON object. Do not include narrative text, markdown fences, or explanatory prose outside the JSON. The output must be parseable as a single JSON object.

## Key Principles

- **Do not mutate**: The `/api/query` endpoint is read-only (`SELECT` only). Never attempt to place orders, write data, or modify the runtime.
- **Template-driven**: Let the `answer_template.json` be the sole authority on output shape. If a field is not in the template, do not include it.
- **Evidence-backed**: Every clinical decision must be traceable to a retrieved observation, imaging study, protocol rule, or case fact. Populate `evidence_ids` accordingly.
- **Safety-first**: When the data does not support a claim (e.g., no imaging was done, or a symptom was not assessed), use safety-check booleans to explicitly deny that claim rather than remaining silent.
- **Allergy-aware**: Always cross-reference medication plans against the patient's allergy list and populate `avoid_allergens` or contraindication fields.
- **Window discipline**: When the task specifies a date window for observations, apply inclusive/exclusive boundary rules precisely. Exclude observations outside the window, of non-final status, or with non-target codes, and list them in `excluded_observation_ids`.
- **Protocol hierarchy**: Protocol documents retrieved from the environment take precedence over general clinical knowledge for thresholds, dispositions, and medication choices within this synthetic clinic.

## Common Task Patterns

### Assessment + disposition tasks (respiratory, head injury)

- Retrieve the case → patient → observations, imaging, and relevant protocol
- Map clinical findings to the template's assessment enum
- Determine risk tier from protocol scoring rules
- Select disposition based on risk and red-flag count
- Build a medication plan avoiding documented allergens
- List return precautions from protocol-defined danger signs

### Order-entry decision support (potassium, lab thresholds)

- Retrieve the latest observation for the target analyte
- Compare the value against protocol-defined replacement thresholds
- Determine if replacement is indicated and select the appropriate route/dose
- Schedule follow-up lab timing per protocol
- Screen for contraindications (e.g., dialysis dependence, arrhythmia, low eGFR)
- List urgent actions only if critical or urgent thresholds are met

### Care-management routing

- Retrieve case → patient → registry → SDOH data
- Extract the risk score and numeric anchors (HbA1c, phosphorus, BP, medication count)
- Derive the problem list and priority ranking
- Determine program routing from risk tier and problem complexity
- Select referral codes based on barriers and needs
- Define care-plan minima and escalation condition codes

### Observation-window retrieval and protocol gating

- Parse the target window (inclusive start, exclusive end) from the prompt or template
- Retrieve all observations for the patient filtered by target code
- Partition into matched (final, in-window, correct code) and excluded (out-of-window, non-final status, wrong code)
- Identify the latest final observation by effective_time
- Determine the protocol gate from the value against protocol thresholds
- Recommend repeat lab timing based on the gate result

## Error Handling

- If an API call fails, retry once; if it fails again, report the failure clearly rather than guessing data
- If a required resource (case, patient, protocol) is not found, note the absence and explain the impact on decision-making in any safety-check fields
- If an observation value is missing or malformed, treat it as unavailable rather than assuming a default
- If the template specifies a `required_value` for a field, use that exact value
