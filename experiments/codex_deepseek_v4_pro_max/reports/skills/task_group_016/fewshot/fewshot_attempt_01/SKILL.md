## When to Use This Skill

Use this skill whenever you are given a task that involves:
- A structured clinical decision-support or protocol-assessment prompt referencing a synthetic clinic runtime environment at `<TASK_ENV_BASE_URL>`.
- A JSON answer template (payload) defining the exact output schema with required keys, enum fields, typed values, and ordering rules.
- A case identifier and an instruction to return a JSON object conforming to the template.

---

## Workflow

Follow these steps in order. Each step is mandatory unless marked optional.

### 1. Orient from the Prompt

Read the task prompt carefully and extract:
- **Task identifier**: usually a string like `train_001`; may also be `task_id` or an explicit constant in the template.
- **Case identifier**: the target case ID for the clinical-review task.
- **Template location**: the path to the answer-template payload (e.g. `input/payloads/answer_template.json`).
- **Clinical domain**: the clinical area the task targets (respiratory, head injury, potassium, care management, lab-window retrieval, etc.).

### 2. Parse the Answer Template

The answer template is the **contract** for your output. Read it fully and identify:
- **`required_top_level_keys`** (or `required_keys`): every key named here **must** appear in your output JSON.
- **Field definitions** inside `fields` (or `field_specification`): each field's type, allowed enum values, nullability rules, and ordering rules.
- **Required constants**: some fields may have a `required_value` — use that exact value.
- **Special rules**: `output_rule`, `numeric_precision`, `additional_properties`, or `extra_keys` notes.

Do **not** add extra top-level keys beyond those declared as required. Do **not** include markdown, prose, or comments outside the JSON object.

### 3. Discover the Runtime Environment

Read the environment-access file (typically `environment_access.md`) provided alongside the task. Extract:
- **Base URL**: from the `GDPEVO_ENV_BASE_URL` value.
- **Allowed endpoints**: the list of GET and POST endpoints available.
- **Authentication**: any required headers such as `X-Clinic-Token` and their values.
- **Query endpoint**: if `POST /api/query` is available, note the required JSON body fields (`sql`, `params`) and the content type.

### 4. Gather Clinical Data from the API

Use only the endpoints listed in the environment-access file. Construct requests as follows:

**GET endpoints** — retrieve resources by path:
- `/api/cases/{case_id}` — the case record and linked patient
- `/api/patients/{patient_id}` — patient demographics and context
- `/api/observations` — observation resources; filter client-side by patient, code, date, and status
- `/api/medications` — active and historical medications
- `/api/allergies` — allergy/intolerance records
- `/api/problems` — problem-list / condition resources
- `/api/imaging` — imaging study resources
- `/api/protocols/{protocol_id}` — protocol decision-support definitions
- `/api/care-registry` — care-management registry entries
- `/api/sdoh` — social determinants of health

**POST /api/query** — run SQL SELECT statements over public tables:
- Set `Content-Type: application/json`.
- Include the required authentication header (`X-Clinic-Token`).
- Body: `{"sql": "<SELECT statement>", "params": []}`.
- Use parameterized queries with `?` placeholders when filtering by values.
- Do **not** run INSERT, UPDATE, DELETE, DROP, or schema-modifying statements. The token is read-only.

When gathering data, prefer direct GET requests for known resource paths. Use the SQL query endpoint only when you need to join across tables or filter with complex conditions not supported by a single GET endpoint.

### 5. Cross-Reference Data with the Template

For each required field in the template, determine the clinical facts needed:

- **Identifiers** (`case_id`, `patient_id`): extract directly from the case record.
- **Enum fields**: choose the single legal value that matches the clinical facts. Read all `allowed_values` and pick the one best supported by the data.
- **List fields with enum items**: include each relevant value at most once. Use empty lists when no items apply. Order does not matter unless the template specifies an ordering rule.
- **Nested objects**: satisfy every `required_key` of the nested object.
- **Nullable fields**: use `null` only when the field specification explicitly permits it and the clinical scenario does not warrant a value.
- **Numeric fields**: respect the stated precision (decimal places, integer vs float).
- **Timestamps**: use ISO-8601 UTC format with the trailing `Z` (e.g. `2026-03-01T00:00:00Z`).
- **Booleans**: use JSON `true` / `false`.

### 6. Apply Clinical Protocol Logic

The template's enum values often encode clinical decision rules. Derive your selection from the data:

- **Risk / severity tiers** (`risk_level`, `risk_tier`): determine from vital signs, lab values, comorbidity burden, and protocol thresholds.
- **Disposition**: choose based on severity, red-flag presence, and protocol guidance.
- **Medication plans**: check allergies before recommending any drug. If the patient has a documented allergy to a drug class, add that class to `avoid_allergens` and select an alternative strategy.
- **Safety checks**: verify that no unsupported clinical claims are made. For example, if the patient did not lose consciousness, do not report loss of consciousness.
- **Protocol gates** (`protocol_gate`): match lab values against protocol-defined thresholds (normal, low, critical, absent).

When the data is ambiguous, prefer the more conservative (safety-oriented) enum value.

### 7. Build and Validate the Output

Construct the JSON object by:
1. Starting with an empty JSON object.
2. Adding every required top-level key in the order declared by the template.
3. Filling each value with the clinically-derived selection.
4. Verifying every `required_value` constant is used exactly.
5. Checking that numeric precision matches the template specification.
6. Ensuring no extra keys are present.
7. Removing any markdown fences or surrounding text — the output must be raw JSON.

### 8. Common Pitfalls

- **Extra keys**: never add keys not listed in the template's required set.
- **Wrong enum case**: enum values are exact strings; copy them verbatim from the template.
- **Incorrect null usage**: only use `null` where the field type is explicitly `*_or_null` or `["string", "null"]`.
- **Missing allergy cross-check**: always check `/api/allergies` before recommending a medication.
- **Unordered lists**: unless an ordering rule is specified, list order is normalized by evaluators. Do not waste effort on arbitrary ordering.
- **Misreading windows**: date windows are typically `[from, to)` (inclusive start, exclusive end). Respect this when filtering observations by effective time.
- **SQL injection**: always use parameterized queries with `?` placeholders and the `params` array. Never concatenate user-provided values into the SQL string.
- **Preliminary vs final observations**: check observation status; only `final` observations count for most clinical decisions unless the template explicitly allows preliminary results.
