## When to Use

Use this skill when the task involves answering a clinical decision-support, protocol-assessment, or lab-retrieval query against a synthetic clinic FHIR-inspired REST runtime. The skill applies whenever a task provides:

- A `TASK_ENV_BASE_URL` or environment access file listing clinic API endpoints
- A JSON answer template (`answer_template.json`) that defines the required output schema
- A target case or patient identifier

## Environment Discovery

1. Locate and read the environment access file (commonly `environment_access.md` or a task block listing endpoints and credentials).
2. Extract the base URL (e.g. `GDPEVO_ENV_BASE_URL`) and the set of allowed `GET` and `POST` endpoints.
3. Note any required headers (typically `X-Clinic-Token`) and their values.
4. If the environment access file lists only GET endpoints and one `POST /api/query`, use that query endpoint for any complex filtered retrieval.

## API Interaction Pattern

### GET Endpoints

The API serves FHIR-like resources. Common resources include:

- `/api/patients` and `/api/patients/{patient_id}`
- `/api/cases` and `/api/cases/{case_id}`
- `/api/observations`
- `/api/medications`
- `/api/allergies`
- `/api/problems`
- `/api/imaging`
- `/api/care-registry`
- `/api/sdoh` (social determinants of health)
- `/api/protocols` and `/api/protocols/{protocol_id}`

Retrieve a resource by constructing a GET request:

```bash
curl -sS "<BASE_URL>/api/<resource>/<id>"
```

When no id filter is provided, the endpoint returns all records. Use id-filtered endpoints first for target entities, then query broader lists when the template requires population-level or windowed retrieval.

### POST /api/query

For SQL-based access use the query endpoint:

```bash
curl -sS -X POST "<BASE_URL>/api/query" \
  -H "Content-Type: application/json" \
  -H "X-Clinic-Token: <TOKEN>" \
  --data '{"sql":"<SELECT statement>","params":["<value>",...]}'
```

Rules for `POST /api/query`:

- The `sql` field must contain a `SELECT` statement over public tables (no DML, no DDL).
- The `params` field must be a JSON array (or object) of bind values, even if empty: `"params":[]`.
- Use positional `?` placeholders in the SQL string, matching the order of `params` array entries.
- Both `sql` (string) and `params` (array or object) are required in the JSON body.
- Include the `Content-Type: application/json` header.
- Include the `X-Clinic-Token` header with the value from the environment access file.

## Data Gathering Strategy

Work top-down from the most specific resource to supporting records:

1. **Case record** — `GET /api/cases/{case_id}` to confirm the case exists and extract the linked `patient_id`.
2. **Patient record** — `GET /api/patients/{patient_id}` to retrieve demographics and context.
3. **Clinical data** — Based on the task domain, retrieve relevant resources:
   - Respiratory assessment → observations, imaging, allergies, medications, protocols
   - Head injury → observations, imaging, protocols
   - Lab/replacement → observations (lab results), medications, problems, protocols
   - Care management → care-registry, sdoh, problems, medications, observations
   - Observation window → observations (by code, date range, and patient)
4. **Protocols** — `GET /api/protocols` or `GET /api/protocols/{protocol_id}` for protocol-bound decision rules.
5. **Complex queries** — Use `POST /api/query` when you need joins, date-range filters, status filters, or code-based filtering across resource types.

Prefer direct GET lookups by id over full-list scans. Use the query endpoint only when direct GET filters are insufficient.

## Output Conformance

Every task provides an `answer_template.json` that governs the output. Follow these rules without exception:

### Schema Adherence

- Include every key listed under `required_top_level_keys` (or `required_keys`).
- Do not include extra top-level keys beyond those listed.
- Use `null` only where the field specification explicitly permits it (check `type` for `"null"` or `"string_or_null"` / `"integer_or_null"`).
- For `enum` fields, choose only from the listed `allowed_values`. Never invent a value.
- For `list` fields, include each item at most once unless the template states otherwise.

### Array Ordering

- When the template says "No semantic ordering is required" or "Order is not meaningful", any stable order is acceptable; use alphabetical or insertion order for consistency.
- When the template specifies an ordering rule (e.g. "Sort by effective_time ascending, then observation_id ascending"), follow it exactly.
- When the template says "Sort by clinical action sequence", order actions from most acute/immediate to least.
- When the template says "case identifier first when included, then clinical source identifiers", place the case id in position 0.
- When the template says "List the main … evidence identifiers in descending relevance", order from most directly supporting to least.

### Numeric Precision

- Respect `precision` hints: "one decimal place" means values like `3.4`, "two decimal places" means `0.85`.
- Integer fields must have no decimal portion.
- Timestamps must use ISO-8601 UTC format with a trailing `Z` (e.g. `"2026-03-15T10:30:00Z"`).

### Output Format

- Return a **single JSON object** — no array wrapping, no markdown fences, no prose.
- If the template includes `output_rule` or `output_rules`, obey them.
- Do not pretty-print unless the template demands it; compact JSON is acceptable.

## Safety Constraints

- **Read-only**: Never mutate the runtime environment. Do not POST, PUT, PATCH, or DELETE to resource endpoints. The `POST /api/query` endpoint is read-only by design (SELECT only).
- **No orders placed**: Even when a task describes "order-entry decision support," do not attempt to create orders in the environment.
- **Credentials**: Use the exact token from the environment access file; do not guess or rotate it.
- **Idempotency**: Repeated identical requests should produce identical results; the environment is synthetic and stable.

## Evidence Tracking

When the output schema includes an `evidence_ids` field:

- Include identifiers for the case, relevant observations, imaging studies, protocol documents, and any other resource records that directly informed the decision.
- Use the stable identifier strings as returned by the API (e.g. `case_id`, `observation_id`, `protocol_id`).
- Follow the ordering rule stated in the template for that field.

## Workflow Summary

1. Read `environment_access.md` (or equivalent) to obtain the base URL, allowed endpoints, and credentials.
2. Read the task prompt to identify the target case id and clinical domain.
3. Read `answer_template.json` to understand the required output shape, enums, and precision rules.
4. Retrieve the case record, then the patient record.
5. Gather domain-specific clinical data using GET endpoints and POST /api/query as needed.
6. Cross-reference protocol materials when the task is protocol-bound.
7. Construct the JSON output strictly following the template schema, enum values, and ordering rules.
8. Output exactly one JSON object with no surrounding text.
