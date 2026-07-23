# Synthetic Clinic Protocol Decision Support Skill

## Purpose

This skill produces a structured, protocol-bound clinical decision-support JSON response for a synthetic clinic case. It retrieves clinical data from a read-only clinic runtime REST API, cross-references that data with applicable protocol materials, and returns a single JSON object that conforms exactly to the supplied answer template schema.

## Input Files

Before making any API calls, read these three input files in the task directory:

1. **`input/prompt.txt`** — Identifies the target case ID, the clinical domain (respiratory, head injury, electrolyte replacement, care management, lab-window retrieval, etc.), and any domain-specific requirements. It also names the answer template to use.

2. **`input/payloads/answer_template.json`** — The output schema. It defines:
   - Required top-level keys
   - Allowed enum values for every controlled field
   - Numeric precision rules
   - Object shapes with required sub-keys
   - Safety-check boolean fields
   - Evidence ID list rules
   - The output rule: "Return exactly one JSON object … Do not include markdown, comments, or explanatory prose."

3. **`environment_access.md`** (provided at the workspace root or alongside the task) — Contains:
   - `base_url`: the clinic runtime base URL
   - `credentials`: HTTP headers (e.g., `X-Clinic-Token`)
   - `allowed_endpoints`: the exact set of `METHOD /api/path` routes available

**Constraint**: You may only call endpoints listed in `allowed_endpoints`. Do not mutate the runtime environment — all operations are read-only.

## Clinic Runtime API

### Authentication

Include the credentials header from `environment_access.md` in every request:

```
X-Clinic-Token: <value>
```

### Core Endpoints

The clinic runtime typically exposes these read-only endpoints. Confirm the exact list from `environment_access.md` on each run; assume nothing beyond what is listed.

| Method | Path | Returns |
|--------|------|---------|
| GET | `/api/patients` | List of all patients |
| GET | `/api/patients/{patient_id}` | Single patient record |
| GET | `/api/cases` | List of all cases |
| GET | `/api/cases/{case_id}` | Single case record (links to patient, encounters, protocol references) |
| GET | `/api/observations` | List of all observations (lab results, vitals, clinical scores) |
| GET | `/api/medications` | List of all medication records |
| GET | `/api/allergies` | List of allergy/intolerance records |
| GET | `/api/problems` | List of problem-list / diagnosis records |
| GET | `/api/imaging` | List of imaging study records |
| GET | `/api/care-registry` | Care-management registry data (risk scores, utilization) |
| GET | `/api/sdoh` | Social determinants of health data |
| GET | `/api/protocols` | List of all clinical protocols |
| GET | `/api/protocols/{protocol_id}` | Single protocol definition |
| POST | `/api/query` | Parameterized cross-resource query (see below) |

### POST /api/query

When you need to filter observations by patient, code, date range, or status, or to search across resources efficiently, use `POST /api/query`. The request body accepts parameters such as:

- `resource` — the FHIR-adjacent resource type (e.g., `"Observation"`)
- `patient` — patient ID
- `code` — LOINC or internal observation code (e.g., `"K"` for potassium)
- `status` — observation status (e.g., `"final"`, `"preliminary"`)
- `date` — date range filter with `from` and `to` (ISO-8601)
- `category` — observation category

Adapt the query parameters to what the endpoint actually accepts; the runtime returns matching resources.

## Data Retrieval Workflow

Follow this sequence for every task:

### Step 1: Retrieve the Target Case

```
GET /api/cases/{case_id}
```

The case record provides:
- `patient_id` — the patient to look up
- `encounter_ids` or embedded encounter references
- `protocol_id` or protocol references
- Case-level metadata (status, dates, reason codes)

### Step 2: Retrieve the Patient

```
GET /api/patients/{patient_id}
```

The patient record provides demographics and may surface linked problems, allergies, or care-registry entries.

### Step 3: Retrieve Protocol Material

If the case references a protocol (by ID or by category), fetch it:

```
GET /api/protocols/{protocol_id}
```

If the task domain is clear but no specific protocol ID is embedded in the case, list all protocols and locate the relevant one by name or category:

```
GET /api/protocols
```

The protocol defines decision thresholds, risk tiers, recommended actions, medication strategies, follow-up timing, and escalation rules.

### Step 4: Retrieve Clinical Data

Based on the clinical domain and the fields required by the answer template, fetch the relevant resources. Typical data needs:

- **Observations** — lab results (potassium, eGFR, HbA1c, phosphorus), vital signs (SpO2, blood pressure, GCS), clinical scores. Filter with `POST /api/query` by patient, code, date window, and status.
- **Imaging** — CXR, CT reports. Use `GET /api/imaging` and filter by patient or case.
- **Medications** — Active medication list for polypharmacy assessment or allergy cross-reference. Use `GET /api/medications`.
- **Allergies** — Intolerance records for medication-plan safety checks. Use `GET /api/allergies`.
- **Problems** — Active problem list / diagnoses. Use `GET /api/problems`.
- **Care Registry** — Risk scores, utilization history, care-management eligibility. Use `GET /api/care-registry`.
- **SDOH** — Social-determinant barriers (transportation, financial, food). Use `GET /api/sdoh`.

### Step 5: Cross-Reference Data Against the Protocol

Apply the protocol's decision rules to the retrieved clinical data:

- **Risk tiering**: Map observation values (e.g., SpO2, potassium level, GCS, risk score) to the protocol's risk thresholds.
- **Red flags**: Identify which protocol-defined red flags are present and which are absent. Use the exact enum values from the answer template.
- **Disposition**: Determine the appropriate care setting from the protocol's disposition logic.
- **Medication plan**: Select medication, dose, route, frequency, and duration per protocol guidance, while cross-referencing the patient's allergy list. Populate `avoid_allergens` from known allergies.
- **Follow-up**: Derive timeframe and route from the protocol's follow-up rules.
- **Referrals / escalation**: Map clinical and social findings to referral codes and escalation conditions.

### Step 6: Assemble Evidence IDs

Collect stable identifiers from the resources actually used to form the clinical decision. Include the case ID when the template expects it. Order by descending relevance: case → primary observation(s) → supporting observations → imaging → protocol.

Use the resource's native ID field (e.g., `id`, `observation_id`, `case_id`). Never invent identifiers.

### Step 7: Populate Safety Checks

The answer template includes boolean safety-check fields. These guard against unsupported claims:
- Set to `true` when the corresponding unsafe claim is **absent** from the data (i.e., the claim was not made).
- Set to `false` when data actually supports the claim.

Match each safety-check field to its clinical meaning and verify against the retrieved data before setting.

## Response Construction Rules

### Strict Schema Compliance

- Return **exactly** the top-level keys listed in `answer_template.json` — no extra keys.
- Use only the **exact enum values** defined in the template. Do not paraphrase, abbreviate, or invent new values.
- Where a field is typed `string_or_null` or `enum_or_null`, use `null` (JSON null) when the clinical context does not require a value — but never substitute an empty string `""` for null.
- Match **numeric precision**: one decimal place for mmol/L values, integer hours for follow-up timeframes, integer days for medication duration, two decimal places for risk scores.
- All ISO-8601 timestamps must include seconds and the trailing `Z` (UTC).

### Lists

- Where the template says ordering is not meaningful, use any stable order (sorted alphabetically by enum value is a safe default).
- Where the template specifies an ordering rule (e.g., ascending by `effective_time`), follow it exactly.
- Omit duplicates — each value appears at most once per list.

### Evidence IDs

- Use stable, resource-level identifiers as they appear in API responses.
- Order as the template specifies (typically by descending relevance or as "case first, then clinical sources").

### Safety Checks

- Each boolean field encodes a "no false X" or "no Y claim" guard.
- Map the field name to the corresponding clinical claim, search the retrieved data for evidence of that claim, and set `true` if the claim is unsupported (safe) or `false` if data actually supports it.

## General Constraints

1. **No narrative text.** Return only the JSON object. Do not wrap it in markdown fences. Do not include comments, explanations, or preamble.
2. **Read-only.** Do not attempt to create, update, or delete resources. All API calls must use GET or the read-only POST /api/query endpoint.
3. **Use only listed endpoints.** The `allowed_endpoints` in `environment_access.md` is authoritative. If an endpoint you need is not listed, work with what is available.
4. **Controlled vocabulary.** Every scored/status/action field must use the exact enum strings from the answer template. Never substitute free-text prose for a controlled value.
5. **Evidence-backed.** Every clinical assertion (assessment, risk tier, red flags, medication strategy) must be traceable to specific retrieved resources. Include those resource IDs in `evidence_ids`.
6. **Allergy-aware.** Before recommending a medication, check the patient's allergy list. Populate `avoid_allergens` and confirm the chosen medication does not conflict.
