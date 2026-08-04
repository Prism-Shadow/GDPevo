---
name: clinic-decision-support
description: Query a synthetic clinic FHIR-style REST API to retrieve case records, observations, medications, imaging, protocols, and other clinical data, then produce structured JSON decision-support answers conforming to a provided answer template. Use this skill whenever the task involves a clinic case ID, a runtime environment at TASK_ENV_BASE_URL, and a prompt asking for a protocol-bound clinical assessment or decision-support response.
---

# Clinic Decision-Support Skill

## Overview

This skill handles structured clinical decision-support tasks against a synthetic clinic runtime API. The API exposes patient records, encounter details, observations, medications, allergies, problems, imaging, care registries, social determinants of health (SDOH), and clinical protocols. Each task provides a specific case ID, a target clinical domain, and a JSON answer-template schema. The agent must query the API, apply the relevant protocol, and return a single JSON object that matches the template exactly—no narrative text outside the JSON.

## Workflow

### 1. Orient to the task

From the task prompt, extract:
- **Case ID** (e.g., `CASE-RESP-102`)
- **Clinical domain** (e.g., respiratory, head injury, potassium management, care management, lab)
- **Answer template path** — typically `input/payloads/answer_template.json` in the task input directory
- **Runtime base URL** — always provided as `<TASK_ENV_BASE_URL>`; replace it with the actual value from the separate environment-access listing
- **Allowed endpoints and credentials** — listed in the separate environment-access document for this run (headers like `X-Clinic-Token`)

Read the answer template file to understand the exact JSON schema required.

### 2. Retrieve case and patient data

Use the case ID to fetch the foundational records. Start with:

```
GET {TASK_ENV_BASE_URL}/api/cases/{case_id}
```

From the case response, extract the `patient_id` and any linked observation, imaging, medication, allergy, or problem identifiers. Then retrieve the patient record:

```
GET {TASK_ENV_BASE_URL}/api/patients/{patient_id}
```

### 3. Retrieve related clinical data

Depending on the clinical domain, query the relevant resource collections. Common patterns:

- **Observations (labs, vitals, scores):**
  ```
  GET {TASK_ENV_BASE_URL}/api/observations
  ```
  Filter by patient, code (e.g., LOINC), and date range as needed.

- **Imaging:**
  ```
  GET {TASK_ENV_BASE_URL}/api/imaging
  ```

- **Medications:**
  ```
  GET {TASK_ENV_BASE_URL}/api/medications
  ```

- **Allergies:**
  ```
  GET {TASK_ENV_BASE_URL}/api/allergies
  ```

- **Problems / diagnoses:**
  ```
  GET {TASK_ENV_BASE_URL}/api/problems
  ```

- **Care registry:**
  ```
  GET {TASK_ENV_BASE_URL}/api/care-registry
  ```

- **SDOH (social determinants):**
  ```
  GET {TASK_ENV_BASE_URL}/api/sdoh
  ```

When the available GET endpoints are insufficient for precise filtering, use the SQL query endpoint:

```
POST {TASK_ENV_BASE_URL}/api/query
Content-Type: application/json
X-Clinic-Token: {token}
Body: {"sql": "<SELECT statement>", "params": []}
```

Always include the `X-Clinic-Token` header as specified in the environment-access listing. Use parameterized queries (`?` placeholders with the `params` array) to avoid injection and to match the endpoint's expected format.

### 4. Retrieve and apply protocols

Fetch available protocols:

```
GET {TASK_ENV_BASE_URL}/api/protocols
```

If the prompt references a specific protocol (e.g., by domain or code), fetch it directly:

```
GET {TASK_ENV_BASE_URL}/api/protocols/{protocol_id}
```

Apply the protocol's decision logic to the retrieved clinical data. This typically involves:
- Identifying red flags / contraindications
- Determining risk tier or severity
- Selecting the appropriate disposition, medication plan, or routing
- Computing follow-up timing and route
- Generating evidence identifiers (reference the source observation, imaging, and case IDs)
- Performing safety checks (boolean assertions that rule out unsupported findings)

### 5. Fill the answer template

Read `input/payloads/answer_template.json` and populate every field. Important rules:

- **Do not add extra keys** beyond what the template defines.
- **Do not omit any required field** — if a field has no applicable value, use `[]`, `null`, `false`, or `{}` as appropriate to the field's type.
- **Use exact identifiers** from the API responses (observation IDs, imaging IDs, case IDs, NDC codes, LOINC codes).
- **Include an `evidence_ids` array** referencing the specific API resources that support the assessment.
- **Include a `safety_checks` object** with boolean assertions that guard against unsupported or contradictory findings.

### 6. Return the result

Return **only** the JSON object. Do not wrap it in markdown fences unless the task instructions explicitly permit it. Do not include narrative summaries, disclaimers, or conversational text. The output must be parseable as a single JSON object.

## API Reference

### Base URL

`{TASK_ENV_BASE_URL}` — always provided per-run in the separate environment-access listing.

### Common headers

- `Content-Type: application/json` (for POST)
- `X-Clinic-Token: {value}` (for POST /api/query; value provided in environment-access listing)

### GET endpoints

| Endpoint | Returns |
|---|---|
| `/api/patients` | List of patients |
| `/api/patients/{patient_id}` | Single patient record |
| `/api/cases` | List of cases |
| `/api/cases/{case_id}` | Single case record with encounter details |
| `/api/observations` | List of observation resources (labs, vitals, scores) |
| `/api/medications` | List of medication resources |
| `/api/allergies` | List of allergy/intolerance resources |
| `/api/problems` | List of problem/diagnosis resources |
| `/api/imaging` | List of imaging study resources |
| `/api/care-registry` | Care registry / program enrollment data |
| `/api/sdoh` | Social determinants of health data |
| `/api/protocols` | List of clinical protocols |
| `/api/protocols/{protocol_id}` | Single protocol resource |

### POST /api/query

Run a read-only SQL SELECT against the public schema.

```
POST {TASK_ENV_BASE_URL}/api/query
Content-Type: application/json
X-Clinic-Token: {token}

{
  "sql": "SELECT column FROM table WHERE condition = ?",
  "params": ["value"]
}
```

Required JSON fields: `sql` (string), `params` (array or object).

## Safety rules

- **Read-only access**: Never attempt to mutate resources (no PUT, PATCH, DELETE, or INSERT/UPDATE/DELETE SQL). The API token is read-only.
- **Allergy-aware**: Always check the patient's allergies before recommending medications. Exclude contraindicated drug classes and document the exclusion in `safety_checks`.
- **Evidence provenance**: Every clinical assertion in the answer must be traceable to a specific API resource. Include those resource IDs in `evidence_ids`.
- **No fabrication**: Do not invent observation values, imaging findings, or patient history. If data is missing from the API, reflect that honestly in the answer (e.g., empty arrays, null values, or `false` safety checks where appropriate).
- **Template fidelity**: The answer template is authoritative for field names, types, and structure. Do not rename, restructure, or embellish.
