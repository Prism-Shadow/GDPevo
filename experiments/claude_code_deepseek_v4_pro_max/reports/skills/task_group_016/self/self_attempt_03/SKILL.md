# Synthetic Clinic Protocol Decision-Support Skill

## Purpose

Execute clinical protocol decision-support tasks against a synthetic clinic runtime environment. This skill covers reading a structured task prompt and answer template, querying the clinic API for case and patient data, applying protocol rules to determine assessments and recommendations, and returning a strict JSON output with no extraneous text.

## When to Use

Invoke this skill when the task involves:
- A synthetic clinic case identifier (e.g., `CASE-RESP-102`, `CASE-HEAD-207`, `CASE-K-303`, `CASE-CM-411`, `CASE-LAB-518`)
- A runtime environment reference (`<TASK_ENV_BASE_URL>`)
- A structured JSON answer template (`input/payloads/answer_template.json`)
- Clinical decision-support domains: respiratory protocol, head injury, potassium replacement, care management routing, or lab observation retrieval

## Operating Rules

### Rule 1 — Environment Setup

Read the file `environment_access.md` at the workspace root. Extract the following and treat them as the authoritative runtime configuration for the entire task:

- **`base_url`**: The clinic API base URL. Strip any trailing slash before use.
- **`credentials`**: HTTP headers to include on every API request. Apply the exact key-value pairs listed.
- **`allowed_endpoints`**: The exhaustive list of endpoints available for this run. Do not call any endpoint not listed here, even if you know it exists. Respect HTTP method constraints exactly (GET vs POST).

### Rule 2 — Input Reading

For each task, read exactly two input files from the input directory:

1. **`prompt.txt`** — contains the natural-language task description. Extract:
   - The target case identifier (always explicitly named)
   - The clinical domain or protocol being assessed
   - Any specific instructions about what to retrieve or determine
   - The output constraint (always: return only a JSON object matching the answer template)

2. **`payloads/answer_template.json`** — defines the exact JSON schema for the output. Extract:
   - `required_top_level_keys`: every key that must appear in the response object
   - `fields` (or `field_specification`): type definitions, allowed enum values, nullability rules, required sub-keys, ordering rules, and precision constraints for every field
   - Output rules: constraints on extra keys, null usage, prose avoidance, and format

### Rule 3 — API Data Retrieval

Query the clinic API to gather all data needed to fill the answer template. Follow these constraints:

- **Authentication**: Include all credentials from `environment_access.md` as headers on every request.
- **Endpoint discipline**: Only call GET endpoints listed in `allowed_endpoints`. Never POST, PUT, PATCH, or DELETE unless `allowed_endpoints` explicitly permits it. The one exception is `POST /api/query` when listed — use it only for structured queries when the endpoint is present.
- **Case-first retrieval**: Start by retrieving the target case (`GET /api/cases/{case_id}`). Use the returned data to identify the associated patient ID, then retrieve the patient record.
- **Context-driven expansion**: Based on the clinical domain in the prompt, retrieve supplementary resources (observations, medications, allergies, problems, imaging, care-registry, sdoh, protocols). Prefer targeted retrieval by ID when the case record provides references; fall back to collection endpoints (`GET /api/observations`, etc.) only when needed.
- **Protocol lookup**: When the prompt references a protocol, retrieve it explicitly (`GET /api/protocols/{protocol_id}`). Use the protocol's rules to guide clinical decisions — not general medical knowledge.

### Rule 4 — Clinical Mapping

Translate raw API responses into the structured output by applying these principles:

- **Enum discipline**: Use only the `allowed_values` listed in the answer template for each enum field. Never invent values, even if they seem clinically appropriate. If no listed value fits, re-examine the data — a listed value always applies.
- **Null discipline**: Only set a field to `null` when the template's type definition explicitly permits it (e.g., `"type": ["string", "null"]`). For medication plan fields like `medication`, `dose`, `route`, `frequency`, `duration_days`, set to `null` only when the clinical plan is "no medication recommended" or the template permits null.
- **Evidence traceability**: Populate `evidence_ids` with the actual resource identifiers (case IDs, observation IDs, imaging IDs, protocol IDs) used to reach each decision. Use a stable order: case identifier first, then clinical source identifiers in descending relevance.
- **Safety checks**: Boolean safety-check fields (`no_penicillin_or_sulfa`, `no_false_loc`, `no_false_vomiting`, etc.) must reflect what the data actually supports — true means "the data confirms this finding is absent" or "the data confirms this claim would be unsupported." Derive these exclusively from API data, not assumptions.
- **Numeric precision**: Respect the precision rules declared in the template (e.g., "one decimal place" for mmol/L values, "two decimal places" for probability scores, "integer hours" for follow-up timeframes, "whole days" for medication duration).

### Rule 5 — Output Production

Return exactly one JSON object. Follow these strict output rules:

- **No markdown**: Do not wrap the JSON in triple-backtick fences.
- **No comments**: Do not include `//` or `/* */` comments in the output.
- **No prose**: Do not add any explanatory text before, after, or around the JSON object.
- **No extra keys**: Do not include any top-level key not listed in `required_top_level_keys`.
- **Required keys only**: Every key in `required_top_level_keys` must be present, even if its value is an empty list, `null` (where permitted), or a default boolean.
- **Ordering rules**: For list fields where the template says "order is not meaningful," use a stable but arbitrary order. For list fields with explicit ordering rules (e.g., "sort by effective_time ascending, then observation_id ascending"), follow the rule exactly.
- **Empty lists vs null**: Use `[]` for empty lists; never use `null` for a list field unless the template's type explicitly allows it.

### Rule 6 — Error Handling

If the API returns an error or an expected resource is missing:

- Do not fabricate data. If a required value cannot be retrieved, note the limitation but still produce the best-effort JSON output.
- If the case ID from the prompt does not match any API resource, report the mismatch rather than using a different case.
- If a protocol or reference resource is unavailable, use only the data available from the case and patient records.

## Task-Type Specific Guidance

### Respiratory Protocol Assessment
- Retrieve case, patient, observations (vitals, O2 saturation, respiratory findings), imaging (CXR), allergies, medications, and the respiratory protocol.
- Map SpO2 values to red-flag thresholds: hypoxemia at 92–93% and below 90%.
- The medication plan must be allergy-aware — cross-reference allergies before recommending antibiotics, and populate `avoid_allergens` accordingly.
- Stabilization actions (supplemental oxygen, urgent ED transfer) are driven by red-flag severity.

### Head Injury Assessment
- Retrieve case, patient, observations, imaging, and the head-injury protocol.
- Distinguish `red_flags` (findings present) from `absent_red_flags` (findings explicitly absent and notable by their absence).
- Map loss of consciousness duration, vomiting episodes, and neurological findings to the risk tier and imaging recommendation.
- Restrictions cover activity, school/return-to-learn, sports, and driving — select based on severity tier.

### Potassium Replacement
- Retrieve case, patient, observations (filter for serum potassium LOINC codes), medications, allergies, problems, and renal function data.
- Identify the latest final serum potassium result within the relevant clinical window.
- Map the potassium value to the replacement plan: routine oral repletion, no replacement, urgent escalation, or hold due to contraindication.
- The medication order requires an NDC code, route, frequency, and status — populate only when replacement is recommended.
- Follow-up lab scheduling depends on the replacement plan and potassium level.
- Contraindications include dialysis dependence, arrhythmia symptoms, and eGFR — pull these from the patient's problem list and renal labs.

### Care Management Routing
- Retrieve case, patient, care-registry data, SDOH (social determinants of health), problems, medications, and the care-management protocol.
- The risk tier determines program eligibility and outreach stance.
- Priority problems aggregate clinical conditions (e.g., uncontrolled diabetes, ESRD, heart failure) and social barriers (transportation, financial).
- Numeric anchors require exact values from the registry and observations: risk score, HbA1c, phosphorus, blood pressure, active medication count.
- Source provenance separates chart-derived facts from facts requiring member disclosure — these are distinct and non-overlapping.

### Lab Observation Retrieval (Protocol Gate)
- Retrieve case, patient, and observations for the target patient.
- Filter observations by: (a) target LOINC code, (b) final status, (c) effective time falling within the specified window (inclusive start, exclusive end).
- Sort matching observations by effective_time ascending, then observation_id ascending.
- Distinguish excluded observations: same patient and code but wrong date, wrong status, or otherwise disqualified.
- The protocol gate classification depends on whether a final lab was found and its value relative to clinical thresholds.
- The repeat-lab recommendation includes a boolean and an ISO-8601 scheduled time (or null).

## Integration Pattern

When invoked for a new task, follow this sequence:

1. Read `environment_access.md` from the workspace root to configure the runtime.
2. Read `prompt.txt` from the task's input directory. Identify the case ID and clinical domain.
3. Read `payloads/answer_template.json` from the same input directory. Internalize every required key, allowed value, nullability rule, and precision constraint.
4. Query the clinic API in case-first order: case → patient → domain-specific resources (observations, medications, allergies, problems, imaging, care-registry, sdoh, protocols).
5. Apply protocol rules (from retrieved protocol resources, not general knowledge) to map clinical data to structured output fields.
6. Return exactly one JSON object — no markdown, no comments, no prose.
