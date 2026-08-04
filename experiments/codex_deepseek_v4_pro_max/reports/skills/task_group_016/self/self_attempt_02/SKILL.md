 # Synthetic Clinic Protocol Assessment Skill

 ## When to Use

 Use this skill whenever you are asked to prepare a structured, protocol-bound clinical decision-support response for a synthetic clinic case. The task will supply:
 - A prompt with a target case identifier and a clinical domain description.
 - An answer template at `input/payloads/answer_template.json` defining the required JSON output shape.
 - An `environment_access.md` file listing the clinic runtime base URL, available endpoints, and credentials.

 ## Environment Setup

 1. Read `environment_access.md` from the workspace root.
 2. Extract the base URL (typically from a variable like `GDPEVO_ENV_BASE_URL`).
 3. The prompt will reference the runtime environment with a placeholder such as `<TASK_ENV_BASE_URL>`. Replace it with the actual base URL extracted in step 2.
 4. Note the required authentication header (e.g., `X-Clinic-Token`) and its value.

 ## API Endpoints and Access Conventions

 The clinic runtime exposes:
 - **Singular GET endpoints** for retrieving individual resources by ID (e.g., `/api/cases/{case_id}`, `/api/patients/{patient_id}`, `/api/protocols/{protocol_id}`).
 - **Collection GET endpoints** for listing all resources of a type (e.g., `/api/observations`, `/api/medications`, `/api/allergies`, `/api/imaging`).
 - **POST `/api/query`** for custom SQL `SELECT` queries over public tables. This endpoint requires:
   - Header: `Content-Type: application/json`
   - Header: the authentication token as listed in `environment_access.md`
   - JSON body: `{"sql": "<SELECT statement>", "params": [<array of bind parameters>]}`
   - The `sql` field must be a read-only `SELECT` statement referencing public tables.

 Use `curl -sS` with `-H` for headers and `--data` for the JSON body. Prefer `POST /api/query` for filtered or joined lookups; use singular GET endpoints for direct resource lookup by ID.

 ## Data Retrieval Workflow

 Follow this sequence to gather all evidence:

 1. **Resolve the case**: Query the target case by its case ID to obtain the associated patient identifier and any case-level metadata (status, dates, encounter references).
 2. **Retrieve the patient record**: Use the patient ID from step 1 to fetch demographics, problem list, and other patient-level data.
 3. **Collect clinical observations**: Retrieve observations relevant to the clinical domain (e.g., vital signs, lab results, imaging reports). Use `POST /api/query` to filter by patient ID, observation codes, date ranges, or status values.
 4. **Gather supporting resources**: Pull medications, allergies, imaging, problem lists, care-registry data, SDOH (social determinants of health), and protocols as relevant to the case.
 5. **Retrieve protocol materials**: If the case references a specific protocol, fetch it by ID. If not, review the available protocol collection to identify the applicable protocol for the clinical domain.
 6. **Identify evidence identifiers**: Throughout retrieval, collect stable resource identifiers (case IDs, observation IDs, encounter IDs, protocol IDs) to populate the `evidence_ids` field in the output.

 ## Answer Template Processing

 1. Read the answer template from `input/payloads/answer_template.json`.
 2. Identify the `required_top_level_keys` (or `required_keys`). The output JSON must include all of them and no extra top-level keys.
 3. For each field, note:
   - **Type** (`string`, `number`, `boolean`, `enum`, `list`, `object`, `integer`, `string_or_null`, `integer_or_null`, `enum_or_null`).
   - **Allowed values** for enums. Use exactly one of the listed values; do not invent values.
   - **Nullable fields**: Use `null` only where the field specification explicitly allows it (types suffixed with `_or_null`, or fields with a `nullable: true` annotation).
   - **Required sub-keys** for object fields. If a required sub-key is not applicable and the field permits null, set the parent object to `null` rather than omitting sub-keys.
   - **Numeric precision**: Follow any unit and precision annotations (e.g., `one decimal place`, `two decimal places`, `integer`, `whole days`).
   - **Ordering rules**: For set-typed lists, order does not matter and duplicates must be omitted. For ordered arrays, follow the stated sort criteria (e.g., by effective_time ascending, then by ID ascending).
 4. **Task and case identifiers**: The `task_id` and `case_id` fields often have explicit `required_value` or `expected_constant` constraints. Match these exactly before filling other fields.

 ## Output Construction Rules

 - Return **exactly one JSON object**. Do not wrap it in markdown code fences, do not include comments, and do not add explanatory prose before or after the JSON.
 - Every top-level key must come from the answer template's required-keys list. Do not add extra keys.
 - Use **controlled enum values** for all scored status, assessment, disposition, and action fields. Do not substitute free-text descriptions.
 - **Timestamps**: Use ISO-8601 UTC format with a trailing `Z` (e.g., `2026-03-15T10:30:00Z`).
 - **Evidence identifiers**: Populate the `evidence_ids` list with the actual stable identifiers retrieved from the clinic API. Prefer putting the case identifier first, then clinical observation, imaging, or protocol identifiers in descending order of relevance to the determination.
 - **Safety checks**: These are boolean fields confirming that specific findings or claims were *not* present. Set them to `true` only when the actual data supports the absence; set to `false` if the finding *is* present or the data is ambiguous. These fields often use boolean assertions about contraindications or unsupported claims.
 - **Empty collections**: Use an empty list `[]` when no items match. Do not use `null` for list fields unless the schema explicitly permits it.

 ## Validation Before Returning

 Before finalizing the output, verify:
 1. Every required top-level key is present.
 2. Every enum field uses one of the allowed values exactly.
 3. No extra top-level keys exist.
 4. Numeric values respect the stated precision.
 5. Timestamps use ISO-8601 UTC with `Z` suffix.
 6. The `evidence_ids` list references identifiers actually retrieved from the API.
 7. Safety-check booleans are consistent with the clinical data retrieved.
 8. The output is raw JSON with no surrounding text, markdown, or code fences.
 9. Null values appear only where the schema permits them.
 10. Ordering rules are honored for fields that specify explicit sort criteria.

 ## Common Pitfalls to Avoid

 - **Omitting required sub-keys**: If an object field is present, all its required sub-keys must be present, even if some values are null where permitted.
 - **Inventing enum values**: If the template lists a fixed set of allowed values, restrict the output to those values only. Do not generate similar-looking values.
 - **Wrapping output in markdown**: The evaluator expects raw JSON. Code fences, backticks, or prose surrounding the JSON will cause failures.
 - **Using null where not permitted**: Only fields annotated as `_or_null` or `nullable: true` may be null. For all other fields, provide a concrete value.
 - **Ignoring ordering rules**: For fields that specify an explicit sort order (e.g., by effective_time), follow it precisely. For set-typed lists, ordering does not matter but omitting duplicates does.
 - **Inconsistent evidence IDs**: Only include identifiers that were actually retrieved during the data-gathering phase. Do not fabricate IDs.
