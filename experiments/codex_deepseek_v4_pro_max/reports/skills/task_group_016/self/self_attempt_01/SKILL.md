## Harborview Synthetic Clinic — Clinical Decision Support

Use this skill when a task directs you to a **synthetic clinic runtime environment** (Harborview Synthetic Clinic) and asks you to return a **structured JSON response** conforming to an answer template. The runtime provides read-only REST endpoints and a parameterized SQL query endpoint for retrieving patient, case, observation, medication, allergy, problem, imaging, registry, social-determinant, and protocol data.

### When to activate

Activate this skill when the task prompt includes any of these signals:

- `<TASK_ENV_BASE_URL>` or an equivalent runtime-environment placeholder
- A reference to `environment_access.md` or a clinic-runtime access listing
- A target case ID of the form `CASE-*`
- An `answer_template.json` payload defining the required JSON output schema

### Environment setup

1. Locate `environment_access.md` in the workspace. It defines:
   - `GDPEVO_ENV_BASE_URL` — the base URL for all API calls
   - Allowed GET endpoints
   - The POST `/api/query` endpoint signature, required headers, and JSON body format
2. Resolve `<TASK_ENV_BASE_URL>` to the value of `GDPEVO_ENV_BASE_URL`.
3. Every API call must target this base URL. Use `curl` or an equivalent HTTP client.

### API reference

**GET endpoints** (read-only clinical resources):

| Endpoint | Returns |
|---|---|
| `/api/patients` | Patient list |
| `/api/patients/{patient_id}` | Single patient record |
| `/api/cases` | Case list |
| `/api/cases/{case_id}` | Single case record |
| `/api/observations` | Observation resources |
| `/api/medications` | Medication resources |
| `/api/allergies` | Allergy/intolerance resources |
| `/api/problems` | Problem-list resources |
| `/api/imaging` | Imaging-study resources |
| `/api/care-registry` | Care-registry/risk resources |
| `/api/sdoh` | Social-determinants-of-health resources |
| `/api/protocols` | Protocol list |
| `/api/protocols/{protocol_id}` | Single protocol resource |

**POST `/api/query`** — parameterized SQL SELECT over public tables:

```
POST {GDPEVO_ENV_BASE_URL}/api/query
Content-Type: application/json
X-Clinic-Token: synclinic-readonly

{"sql": "<SELECT statement>", "params": []}
```

- `sql` must be a read-only `SELECT` statement.
- `params` must be an array (or object) of bind values.
- Use this endpoint when you need to filter, join, or aggregate data that the GET endpoints do not serve directly (e.g., finding observations within a date window for a specific patient).

### Workflow

Follow this sequence for every task:

#### 1. Parse the task prompt

Extract:

- **Target case ID** — always present in the prompt (e.g., `CASE-RESP-102`).
- **Clinical domain** — respiratory, head-injury, potassium/electrolyte, care-management, lab-observation-window, etc. This determines which GET endpoints and protocol resources are relevant.
- **Answer template path** — always `input/payloads/answer_template.json` relative to the task input directory.

#### 2. Read and internalize the answer template

Open the template file. It is a JSON schema with:

- `required_top_level_keys` — every key in this list must appear in your output.
- `fields` (or `field_specification`) — each field's type, allowed enum values, required sub-keys, and ordering rules.

Pay special attention to:

- **Enum fields** — your output must use exactly one of the `allowed_values`. Never invent a value.
- **Nullable fields** — only use `null` where the schema explicitly permits it (look for `"type": ["string", "null"]` or `"type": "integer_or_null"`).
- **Ordering rules** — for lists, follow the stated ordering (e.g., "sort by effective_time ascending"). When the schema says "no semantic ordering," any order is acceptable.
- **Boolean safety checks** — these are ground-truth assertions; derive them from data, not assumptions.

#### 3. Gather data from the clinic API

Start with the case and its patient:

```
GET /api/cases/{case_id}
```

The case record contains the `patient_id`. Use it to fetch the patient:

```
GET /api/patients/{patient_id}
```

Then retrieve related clinical data. The relevant endpoints depend on the clinical domain:

| Domain | Typical endpoints |
|---|---|
| Respiratory | observations, medications, allergies, imaging, protocols |
| Head injury | observations, imaging, protocols |
| Potassium / electrolytes | observations, medications, problems, protocols |
| Care management | care-registry, sdoh, observations, medications, problems, protocols |
| Lab observation window | observations (use `/api/query` for windowed retrieval) |

Use the POST `/api/query` endpoint for precise retrieval:

- **Windowed observations**: `SELECT * FROM observations WHERE patient_id = ? AND code = ? AND effective_time >= ? AND effective_time < ? AND status = 'final'`
- **Cross-resource lookups**: join-style queries that the flat GET endpoints cannot express.

**Important**: Every `/api/query` call requires the header `X-Clinic-Token: synclinic-readonly`.

#### 4. Apply protocol logic

Read the relevant protocol resource when the task references a protocol:

```
GET /api/protocols/{protocol_id}
```

Use the protocol's rules — thresholds, risk-stratification criteria, contraindication screens, escalation conditions — to drive your clinical decisions. Map clinical data values to the protocol's decision tree and select the appropriate enum value for each output field.

#### 5. Build the JSON response

Construct a single JSON object that:

- Contains **every key** from `required_top_level_keys`.
- Contains **no extra top-level keys**.
- Uses **only allowed enum values** for each typed field.
- Includes **evidence identifiers** — observation IDs, case IDs, protocol IDs, imaging IDs — so the response is auditable.
- Formats timestamps as **ISO-8601 UTC** with a trailing `Z` (e.g., `2026-03-15T10:30:00Z`).
- Formats numeric values to the **precision specified** in the template (e.g., one decimal place for mmol/L values).
- Uses **empty arrays `[]`** when a list field has no applicable items (unless the schema explicitly requires `null`).

#### 6. Validate before returning

- Does the JSON parse without errors?
- Are all `required_top_level_keys` present?
- Are all enum values drawn from the template's `allowed_values`?
- Are all `required_keys` inside nested objects present?
- Do boolean safety-check values match the clinical data?

### Constraints

- **Read-only**: Never use `POST`, `PUT`, `PATCH`, or `DELETE` on resource endpoints. Only `GET` and the read-only `POST /api/query`.
- **JSON-only output**: Return exactly one JSON object. No markdown fences, no explanatory prose, no comments.
- **No mutations**: Do not place orders or modify data through the API.
- **Template fidelity**: The answer template is the contract. If a field is not in the template, do not include it. If a value is not in the allowed list, do not use it.

### Quick-reference curl patterns

```bash
# Fetch a case
curl -sS "${GDPEVO_ENV_BASE_URL}/api/cases/CASE-RESP-102"

# Fetch a patient
curl -sS "${GDPEVO_ENV_BASE_URL}/api/patients/PAT-12345"

# Fetch observations (list)
curl -sS "${GDPEVO_ENV_BASE_URL}/api/observations"

# SQL query — windowed observations for a specific patient and code
curl -sS -X POST "${GDPEVO_ENV_BASE_URL}/api/query" \
  -H 'Content-Type: application/json' \
  -H 'X-Clinic-Token: synclinic-readonly' \
  --data '{"sql":"SELECT * FROM observations WHERE patient_id = ? AND code = ? AND effective_time >= ? AND effective_time < ? AND status = ?","params":["PAT-12345","K","2026-03-01T00:00:00Z","2026-04-01T00:00:00Z","final"]}'
```

### Common failure modes

- **Missing the auth header** on `/api/query` calls — the endpoint requires `X-Clinic-Token: synclinic-readonly`.
- **Using free text instead of enum values** — every categorical field in the template has an `allowed_values` list; pick from it.
- **Including extra top-level keys** — the evaluator may reject the response.
- **Wrong timestamp format** — always ISO-8601 with trailing `Z`.
- **Misreading nullable fields** — check whether the schema permits `null` before using it.
- **Forgetting evidence_ids** — always include the identifiers of the resources that support your decisions.
