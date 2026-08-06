# Clinic Decision Support Skill

Produce protocol-bound clinical decision-support responses by querying a synthetic clinic runtime API and returning a single structured JSON object conforming to a supplied answer template.

## When to use

Invoke this skill when the task involves:
- A clinic case identifier (e.g., `CASE-*-NNN`) in the prompt
- A structured answer template (`answer_template.json`) in the task payloads
- A clinic runtime environment described in a separate environment-access file
- A requirement to return exactly one JSON object with controlled vocabulary

## Operating rules

### Phase 1: Load environment configuration

Read the environment-access file provided alongside the task. It contains:

- `base_url` — the clinic runtime API root (referenced in prompts as `<TASK_ENV_BASE_URL>`)
- `credentials` — authentication headers or tokens (e.g., `X-Clinic-Token`)
- `allowed_endpoints` — the exact set of HTTP method + path patterns available for this run

Only call endpoints listed in `allowed_endpoints`. Use the provided credential on every request.

### Phase 2: Understand the task

Read the prompt (`prompt.txt`) to identify:
- The target **case identifier** (e.g., `CASE-RESP-102`)
- The **clinical domain** (respiratory, head injury, electrolyte, care management, lab window, etc.)
- Any domain-specific instructions or constraints

Read the answer template (`payloads/answer_template.json`) to understand:
- Every **required top-level key** and its type
- All **enum constraints** — every field that takes controlled values lists them explicitly
- **Nullable fields** — which keys permit `null` and under what conditions
- **Numeric precision rules** — decimal places, integer-only fields, units
- **Output rules** — no extra keys, no markdown, no prose outside the JSON object
- **Ordering rules** — most list fields specify that evaluators normalize as sets (order is not meaningful)

### Phase 3: Gather clinical data from the API

Follow this general sequence, adapting to the domain and available endpoints:

1. **Fetch the case** — `GET /api/cases/{case_id}`. Extract the `patient_id` and any case-level metadata.
2. **Fetch the patient** — `GET /api/patients/{patient_id}`. Note demographics and relevant history.
3. **Fetch domain-relevant clinical resources**. Based on the clinical domain, pull from:
   - `GET /api/observations` — lab results, vitals, clinical measurements. Filter by patient, code, date range, and status (`final` vs `preliminary`).
   - `GET /api/medications` — active and historical medication orders.
   - `GET /api/allergies` — documented allergies and intolerances. Cross-reference against any medication plan.
   - `GET /api/imaging` — imaging studies and reports (e.g., CXR for respiratory cases).
   - `GET /api/problems` — active problem list / diagnoses.
   - `GET /api/care-registry` — care management enrollment, risk scores, program eligibility.
   - `GET /api/sdoh` — social determinants of health (transportation, financial, food barriers).
   - `GET /api/protocols` — list available clinical protocols; filter by domain.
   - `GET /api/protocols/{protocol_id}` — retrieve the full text of a relevant protocol for decision thresholds.
   - `POST /api/query` — submit structured or parameterized queries when the GET endpoints lack sufficient filter granularity.

4. **Validate data completeness**. Before synthesizing, confirm:
   - The case and patient records were retrieved successfully
   - All clinical data needed to populate the template's required fields is available
   - Observation values include `effective_time` for temporal reasoning
   - Allergy records have been checked against any planned medication

### Phase 4: Synthesize the response

Apply clinical reasoning within the **exact** vocabulary of the answer template:

- **Match findings to enum values** — never invent values outside the template's `allowed_values` lists. If the clinical picture doesn't perfectly match any allowed value, choose the closest match rather than creating a new term.
- **Cross-reference allergies with medications** — populate `avoid_allergens` or equivalent fields by checking the medication plan against documented allergies. Set safety-check booleans as required by the template.
- **Apply protocol thresholds** — use protocol documents to determine risk tiers, replacement requirements, imaging recommendations, and disposition. When a protocol provides a numeric threshold (e.g., potassium ≤ 3.3 mmol/L → replace), apply it precisely.
- **Handle temporal windows** — when the task specifies a date window (e.g., "March 2026"), compute the ISO-8601 range, filter observations by `effective_time` within that window, and distinguish `final` from non-final statuses.
- **Distinguish matched from excluded observations** — when the template requires both `matched_observation_ids` and `excluded_observation_ids`, exclude observations that fail on code, date window, or status, and explain exclusions only through the structured fields.
- **Populate evidence traceability** — include identifiers for every clinical resource that informed the decision (case, observation, imaging, medication, protocol IDs) in the `evidence_ids` or `source_provenance` fields. Use the case identifier first, then clinical source identifiers in descending relevance.

### Phase 5: Validate and emit

Before returning the response, verify:

1. **Every required key is present** — check against the template's `required_top_level_keys` and any nested `required_keys`.
2. **No extra keys** — the output must not include keys beyond those the template defines.
3. **All enum fields use only allowed values** — scan every field against its `allowed_values` list.
4. **Numeric precision matches** — decimal fields have the correct number of decimal places; integer fields are whole numbers.
5. **Null is used only where permitted** — the template's type declarations (e.g., `["string", "null"]` or `"nullable": true`) define where nulls are valid.
6. **Safety checks are self-consistent** — e.g., a medication plan that avoids penicillin must have `no_penicillin_or_sulfa: true`; a claim of normal CXR must be reflected in the corresponding safety boolean.
7. **Output is exactly one JSON object** — no markdown fences, no leading/trailing prose, no comments.

Return the validated JSON object as the sole response.

## Reusable patterns

### API navigation

Always start from the case endpoint and walk outward. The case provides the patient ID; the patient provides context for filtering observations, medications, and other resources. Use the `POST /api/query` endpoint as a fallback when GET parameter filtering is insufficient — it accepts a JSON body with filter criteria.

### Template conformance

The answer template is the authoritative schema. When in doubt between a clinical judgment and the template's vocabulary, the template wins. If no allowed value captures the clinical picture precisely, select the **closest** allowed value rather than defaulting to null or fabricating a value.

### Allergy-aware medication planning

Before finalizing any medication field:
1. Retrieve the patient's allergy list
2. Check every medication name, class, and cross-reactivity group against documented allergies
3. Populate `avoid_allergens` with the specific allergen classes that are documented
4. If the template has a `no_penicillin_or_sulfa` (or equivalent) safety check, set it to `true` only when neither penicillin nor sulfonamide appears in the medication plan AND the patient has no documented allergy to either class

### Temporal range filtering

When the task specifies a month or date range:
- Compute the inclusive start (`from`) and exclusive end (`to`) as ISO-8601 UTC timestamps
- Filter observations by `effective_time` falling within `[from, to)`
- Only count observations with `status: "final"` unless the template explicitly permits other statuses
- Sort matched results by `effective_time` ascending, then by `observation_id` ascending for deterministic output
- Place observations that are relevant but excluded (wrong date, code, or status) in `excluded_observation_ids`

### Red flag identification

When the template has a `red_flags` field (or equivalent):
- Red flags are clinical findings present in the case that indicate elevated risk
- Select only from the template's `allowed_values` list
- Do not list a red flag that is absent — use `absent_red_flags` or an equivalent field if the template provides one
- No semantic ordering — evaluators normalize as a set

### Safety checks

Safety-check booleans act as assertions about what was NOT found. They are typically phrased as `no_*` or `no_false_*`:
- Set to `true` to assert the finding is absent or the claim is not supported
- Set to `false` to indicate the finding IS present or the claim IS supported
- Never set a safety boolean to `true` if the corresponding finding actually exists in the clinical data

## Reference files

- `references/api-surface.md` — expected clinic API endpoints and their response shapes
- `references/template-format.md` — how answer templates are structured and interpreted
