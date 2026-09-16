---
name: clinic-decision-support
description: Structured clinical decision-support for a synthetic clinic FHIR-like REST API. Use when the task prompt references a synthetic clinic case ID, a task environment base URL, and an answer_template.json payload — typically for protocol-bound assessments involving respiratory, head-injury, potassium replacement, care-management routing, or observation-window retrieval tasks.
---

# Clinic Decision Support

## Workflow

Every task follows a single general workflow:

1. **Parse the prompt** for the target `case_id` and `task_id`.
2. **Read `input/payloads/answer_template.json`** to understand the exact output
   schema, required keys, enum values, and safety-check fields.
3. **Read `environment_access.md`** for the `<TASK_ENV_BASE_URL>` and allowed
   endpoint list. Use the base URL and endpoint names verbatim.
4. **Fetch the case**: `GET /api/cases/{case_id}` and extract the linked
   `patient_id` (may be a direct field or nested under `subject.reference`).
5. **Fetch the patient**: `GET /api/patients/{patient_id}`.
6. **Fetch supporting clinical data** from the relevant endpoints listed in
   `environment_access.md`. Typical sources: observations, imaging, allergies,
   medications, problems, protocols, care-registry, and SDoH. See
   [references/api_reference.md](references/api_reference.md) for endpoint and
   field details.
7. **Map the clinical facts to the template** using only the allowed enum values.
   See [references/task_patterns.md](references/task_patterns.md) for task-family
   guidance.
8. **Populate `evidence_ids`** with the stable identifiers of every record used
   to reach the clinical conclusions (case, observation, imaging, and protocol
   identifiers).
9. **Populate `safety_checks`** by confirming each boolean assertion against the
   fetched data. If a check asks "no X claim", verify that X is genuinely absent
   from the record before setting `true`.
10. **Output only the JSON object** — no markdown fences, no commentary, no
    extra top-level keys.

## Helper Script

**[scripts/fetch_case.py](scripts/fetch_case.py)** fetches a case and its linked
patient in one call. Run it as:

```bash
python scripts/fetch_case.py <base_url> <case_id>
```

It prints the combined case and patient JSON to stdout, resolving `patient_id`
from either a direct field or a FHIR `subject.reference`.

## Clinical Mapping Rules

### Enum Selection

Select only enum values whose clinical conditions are directly evidenced in the
fetched data. Do not guess or extrapolate beyond what the records show.

### Observation Filtering

Filter observations by:
- Correct code (e.g., `"K"` for potassium, `"SpO2"`, LOINC codes)
- `status` equal to `"final"` — ignore `"preliminary"` and `"corrected"`
- Linked patient
- Applicable time window when specified

### Allergy Awareness

Search allergy records for class keywords: penicillin, sulfonamide/sulfa,
macrolide, tetracycline. Map matches to the corresponding `avoid_allergens`
enum values in the template.

### Evidence Identifiers

Include the case identifier itself plus every observation, imaging, and protocol
identifier that contributed evidence. Use stable, deterministic ordering within
each category.

### Safety Checks

For boolean safety fields like `no_penicillin_or_sulfa`, `no_false_loc`,
`no_normal_cxr_claim`, confirm each condition by cross-referencing the relevant
allergy, observation, and imaging records. Set `true` only when the clinical
data unambiguously supports the claim.

## Output Constraints

- Return exactly the JSON object conforming to the template.
- Use `null` only where the template explicitly allows it.
- Use controlled enum strings, never free-text prose, for scored fields.
- Do not include markdown fences, comments, or extra top-level keys.
