---
name: clinic-decision-support
description: Query a synthetic clinic REST API to retrieve clinical data and produce protocol-bound decision-support results as structured JSON. Use this skill whenever the task references a clinic runtime environment (TASK_ENV_BASE_URL), asks you to review patient records or clinical protocols, requires a JSON output conforming to a provided answer template, or mentions clinical decision support, medical protocol assessment, care management routing, potassium replacement, respiratory assessment, head injury triage, lab result interpretation, or FHIR-style API queries — even if the user does not name these terms explicitly.
---

# Clinic Decision Support

This skill covers how to work with a synthetic clinic REST API to retrieve clinical data and produce structured decision-support JSON outputs that conform to a provided answer template.

## Core workflow

When a task asks you to produce a clinical decision-support result, follow these steps in order.

### 1. Gather the inputs before calling the API

Read three things first:

- **The prompt** — it identifies the target case ID, the clinical domain, and what decision to produce. It also tells you where the answer template lives (usually `input/payloads/answer_template.json`) and references a runtime environment URL via `<TASK_ENV_BASE_URL>`.
- **The answer template** — a JSON schema that defines every required top-level key, allowed enum values per field, data types, numeric precision, ordering rules, and nullability. Read it completely. Every field in your final output must comply with this schema.
- **The environment access file** — lists the actual base URL and the available REST endpoints. Substitute `<TASK_ENV_BASE_URL>` with this base URL in every API call.

### 2. Navigate the clinical data

Start from the case ID given in the prompt. Query these endpoints in a logical sequence:

1. `GET /api/cases/{case_id}` — the case record links to the patient and related clinical resources.
2. `GET /api/patients/{patient_id}` — patient demographics and context.
3. `GET /api/observations` — lab results, vitals, and other measurements. Filter by patient, observation code, date range, or status as the template and protocol require.
4. `GET /api/protocols` or `GET /api/protocols/{protocol_id}` — the clinical protocol that governs the decision. The protocol defines thresholds, risk tiers, red flags, medication guidance, and follow-up rules.
5. Use other endpoints as the template demands: `/api/medications`, `/api/allergies`, `/api/imaging`, `/api/problems`, `/api/care-registry`, `/api/sdoh`.
6. The `POST /api/query` endpoint is available for more complex queries if needed.

Each API call returns JSON. Inspect the response structure to understand the resource fields before trying to extract values — field names may differ from what the template calls them.

### 3. Apply the protocol to the data

Decisions are **protocol-bound**, not freeform judgment. This means:

- Compare patient observations against the protocol's explicit thresholds.
- Map each finding to one of the enum values defined in the answer template.
- Every field that has a restricted set of allowed values must use exactly one of those values — do not invent new enum members or use prose.

**Key reasoning rules:**

- **Evidence tracing**: Every determination must trace back to a specific observation, imaging result, or protocol rule. Collect resource identifiers and include them in the `evidence_ids` field.
- **Red flags**: The protocol defines what counts as a red flag. Check each protocol-defined red flag against the patient's data. When the template asks for `absent_red_flags`, list the protocol-defined red flags the patient does NOT exhibit.
- **Allergies before medications**: Always check the patient's allergies before recommending any medication. When the template includes an `avoid_allergens` field, populate it with every allergen class the patient has on record that is relevant to the medication plan.
- **Safety checks**: Templates often include boolean safety fields (e.g., `no_penicillin_or_sulfa`, `no_false_loc`). These guard against unsafe or incorrect claims. Set each to `true` when the constraint is satisfied — meaning the dangerous condition is absent or the false claim was avoided.
- **Risk tiers**: Map clinical severity to one of the template's allowed risk levels based on the protocol's criteria, not on intuition.
- **Numeric precision**: Respect every precision constraint from the template (e.g., "one decimal place", "integer hours", "two decimal places").
- **Timestamps**: Use ISO-8601 UTC format with a trailing `Z` wherever the template requires it.
- **Nulls**: Use `null` only for fields where the template explicitly permits it (marked `"type": ["string", "null"]` or `"type": ["integer", "null"]` or similar).

### 4. Produce the JSON output

Build exactly one JSON object. Follow these rules:

- Include every key listed in the template's `required_top_level_keys`.
- Use only allowed enum values for restricted fields.
- For lists marked "No semantic ordering is required", any order is acceptable but do not duplicate items. For lists that specify a sort order (e.g., "Sort by effective_time ascending"), comply.
- Do not add extra top-level keys beyond what the template requires.
- Return the raw JSON object — no markdown fences, no surrounding prose, no comments.

## Common template structures

Clinic decision-support templates share these recurring patterns:

- **`task_id` / `case_id`**: Fixed constants. Set them to the values specified in the template or prompt; do not derive them from API data.
- **`patient_id`**: Retrieved from the case record or the patients endpoint.
- **`evidence_ids`**: Resource identifiers that supported the decision — observation IDs, imaging IDs, case IDs, protocol references. List them in the order the template specifies (often descending relevance or case-first).
- **`safety_checks`**: Boolean assertions that confirm unsafe patterns were avoided (e.g., no penicillin was prescribed to a penicillin-allergic patient, no claim of normal imaging was made when imaging was abnormal).
- **`follow_up`**: An object with `timeframe_hours` and `route`. Derive the route from protocol guidance; derive the timeframe from protocol-recommended recheck windows.
- **`medication_plan` / `medication_order`**: Structured medication recommendations with NDC codes, medication names, doses, routes, frequencies, and durations. The `status` field (e.g., `"recommended"`, `"not_recommended"`, `"defer_to_urgent_clinician"`) signals whether the medication is actionable now.
- **`stabilization_actions` / `urgent_actions`**: Lists of immediate actions when the patient is unstable. Use an empty list when no action is needed.
- **`contraindications`**: Boolean or numeric fields (e.g., `dialysis_dependent`, `arrhythmia_symptoms`, `egfr`) that control whether a medication or plan is safe. Populate these from patient data.

## Handling ambiguity and missing data

- If an API endpoint returns an error, retry once with the same parameters. If it still fails, note what is missing and proceed with the data you have rather than guessing.
- If the protocol is ambiguous at a decision boundary, prefer the more conservative (safer) interpretation that stays within the template's allowed values.
- If a required data point is genuinely unavailable from the API, use `null` only when the template marks that field as nullable. Otherwise choose the allowed value that best reflects "unknown" or "pending" while remaining clinically safe.
- When the template has an `excluded_observation_ids` or similar exclusion list, include observations that are relevant to the case review but do not qualify because of date, code, status, or patient mismatch — this shows you considered them and made a deliberate exclusion.
