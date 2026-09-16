---
name: clinic-decision-support
description: Protocol-bound clinical decision support for synthetic clinic environments with a FHIR-like REST API. Use when the task involves a clinic case ID, structured answer templates, and a clinic runtime API at a base URL for respiratory assessment, head-injury protocols, potassium replacement, care-management routing, or lab-window retrieval. Triggers on prompts mentioning answer_template.json, protocol assessment, clinical decision support, order-entry support, care-management routing, or synthetic clinic case identifiers.
---

# Clinic Decision Support

## Overview

Solve structured clinic decision-support tasks that require querying a synthetic-clinic FHIR-like REST API, cross-referencing the returned clinical data against a JSON answer template, applying protocol rules, and returning a single valid JSON object.

## Workflow

Follow these steps in order. Do not skip steps or return before the JSON answer is complete.

### Step 1: Read the prompt and the answer template

Extract these facts from the prompt:
- The target case ID (e.g. `CASE-EXAMPLE-101`).
- The task ID (e.g. `task-001`), which may be listed in the answer template instead of the prompt.
- The runtime base URL (look for `<TASK_ENV_BASE_URL>` in the prompt text).

Read `input/payloads/answer_template.json` completely. Memorize:
- Every required top-level key.
- Every enum value set.
- Every `required_keys` constraint on nested objects.
- Every `nullable` and type constraint.
- Every ordering or normalization rule.

### Step 2: Gather clinical data from the runtime API

Use the endpoints listed in [API Endpoints](references/api_endpoints.md). Query in this order:

1. `GET /api/cases/{case_id}` — the case record, which gives you the patient ID and any embedded clinical context.
2. `GET /api/patients/{patient_id}` — patient demographics.
3. `GET /api/observations` — lab results, vitals, and clinical measurements. Filter for the target patient; the API return may be paginated or filtered by patient.
4. `GET /api/medications` — active and historical medications for the patient.
5. `GET /api/allergies` — allergy/intolerance records.
6. `GET /api/problems` — problem list or condition codes.
7. `GET /api/imaging` — imaging study records and findings.
8. `GET /api/care-registry` — care-management registry data.
9. `GET /api/sdoh` — social determinants of health.
10. `GET /api/protocols` and `GET /api/protocols/{protocol_id}` — clinical protocol rules that define assessment criteria, thresholds, and decision logic.

Query only the endpoints relevant to the task. A respiratory assessment needs observations, imaging, allergies, medications, and respiratory protocols. A care-management routing needs care-registry, sdoh, problems, and medications.

Use `POST /api/query` for complex filtered searches when the standard GET endpoints return too much unrelated data.

### Step 3: Cross-reference data against the template

Map each required template field to clinical data:

- **Enum fields**: Match the clinical facts to the allowed enum values. Choose the value that best describes the actual data, never defaulting or guessing.
- **Boolean fields**: Derive from explicit presence or absence of a clinical fact.
- **Numeric fields**: Pull the exact value and precision from the observation record.
- **List fields**: Include only values with evidence in the data; omit unsupported values.
- **Object fields**: Fill every `required_keys` sub-field.

When the template says "ordering is not meaningful" or "evaluators normalize this as a set", order does not matter but do not include duplicates.

### Step 4: Apply protocol rules

Protocol resources from `/api/protocols` contain decision thresholds, risk-tier criteria, and care pathways. Apply them to the clinical data:

- A protocol may define a risk tier from a combination of lab values, vital signs, and findings.
- A medication recommendation from a protocol must be checked against the patient's allergy list. Include the relevant allergens in `avoid_allergens`.
- Disposition and follow-up timing come from protocol-defined pathways, not generic defaults.
- Use the protocol's evidence identifiers in the `evidence_ids` field.

### Step 5: Validate and return the JSON

Before returning:

- Confirm every required top-level key is present.
- Confirm every enum value is from the allowed set.
- Confirm every `required_keys` child field inside nested objects is present.
- Confirm `null` is used only where the template explicitly permits it.
- Confirm numeric precision matches the template (e.g. one decimal place for mmol/L, two decimal places for probability, integer for hours and days).
- Confirm ISO-8601 timestamps have the trailing `Z`.
- Confirm list fields contain no duplicates.

Return a single JSON object with no markdown fences, no surrounding prose, no comments, and no extra top-level keys.

## Template-Filling Rules

### Enum selection

When clinical data could map to multiple enum values, select the most specific one that matches the documented finding. Never invent values outside the allowed set.

### List composition

Build lists from concrete evidence only. If a red-flag or problem list item is absent from the clinical record, omit it — do not include it as a negative.

### Safety checks

Safety-check booleans typically guard against claiming findings that are not supported by the data. For example, `no_penicillin_or_sulfa: true` means the record does not show penicillin or sulfonamide allergy. Set these based strictly on what the API data contains or lacks.

### Numeric precision

Always match the precision demanded by the template. Use the observation value as-is from the API; round only when the template specifies a precision that differs from the stored value.

## Output Discipline

- Return **only** a single JSON object.
- No markdown code fences (no ```json ... ```).
- No explanatory text before or after the JSON.
- No comments inside the JSON.
- No extra top-level keys beyond those listed in the template's `required_top_level_keys`.

## Resources

### scripts/probe_env.py

Quick probe script that fetches a case, its patient, and related observations, medications, allergies, and problems. Run it to get a rapid data dump before making clinical decisions. Usage: `python3 scripts/probe_env.py <base_url> <case_id>`.

### references/api_endpoints.md

Complete reference for every available clinic API endpoint: path, method, purpose, return shape, and usage notes. Read this when you need detail on a specific endpoint.
