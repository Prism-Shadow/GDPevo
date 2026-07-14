# ClinicProtocol Decision-Support Skill

## Overview

You solve synthetic protocol-bound clinical decision-support tasks using the **ClinicProtocol API** at the base URL provided in the task (default: `http://34.46.77.124:9016`). Every task asks you to review a patient, encounter, or case against a named protocol, then return a single JSON object matching a supplied answer template (`answer_template.json`).

These are structured classification/retrieval tasks: interpret FHIR-style observations, apply a protocol card's decision thresholds, and emit templated JSON with lexicographically sorted lists.

---

## Workflow

### 1. Read the task inputs

Every task directory contains:
- `input/prompt.txt` — the clinical question, patient/encounter/case IDs, the protocol to use, and any situational parameters (e.g., current clinical time).
- `input/payloads/answer_template.json` — the exact JSON schema you must conform to. It defines required keys, allowed enum values, list item ordering (`sort_lexicographic`), and field types.

### 2. Explore the API

The ClinicProtocol API is the sole source of truth. Use it to fetch:
- **Patient resources** (demographics, history, allergies)
- **Encounter resources** (visit context, chief complaint, vital signs)
- **Observation resources** (lab results, imaging findings, clinical scores like GCS)
- **Case resources** (care-management case records with linked patient data)
- **Protocol cards** — the decision-logic documents that define risk thresholds, red-flag criteria, dose tables, exclusion rules, and escalation pathways

Start by fetching the protocol card named in the prompt (e.g., `HEAD_INJURY_2026`). Then fetch the patient, encounter, and any referenced observations. Use the protocol card's rules to filter observations (final vs. preliminary/erroneous), classify severity, and populate the output fields.

### 3. Apply the protocol card's logic

Protocol cards are the decision engine. They define:
- **Thresholds** — e.g., potassium below 3.5 mEq/L triggers replacement; GCS below certain values triggers CT.
- **Red-flag / severity-factor lists** — which observation findings map to which risk levels.
- **Exclusion rules** — which observations to ignore (preliminary status, wrong LOINC code, out-of-range dates, error-flagged).
- **Dose tables** — e.g., potassium replacement mEq based on the serum level.
- **Disposition pathways** — home observation, same-day clinic, ED referral.
- **Care-management escalation rules** — chart concerns, consent strategies, disciplines, cadence.

Derive every output field from the protocol card applied to the patient's data. Never guess thresholds or enum values.

### 4. Fill the answer template

Produce a single JSON object whose keys exactly match `required_top_level_keys` in order. Obey every constraint:
- **Enums**: pick only from `allowed` values.
- **Lists**: items must come from the given `items_enum`, and **must be sorted lexicographically** (standard string sort).
- **Nested objects**: populate all `required` sub-fields.
- **Types**: use the declared JSON type (string, integer, number, boolean).

---

## API Conventions

### Endpoint discovery
The API may use RESTful or FHIR-style paths. Probe common patterns when the prompt doesn't spell them out:
- `/Patient/{id}`, `/Encounter/{id}`, `/Observation/{id}`
- `/Case/{id}`
- `/Protocol/{name}` or `/card/{name}`
- Query parameters like `?patient={id}&category=laboratory`

If a direct resource path returns 404, try the resource-type-as-collection pattern (`/Patient?_id={id}`) or a `/search` endpoint. The server identifies itself as `ClinicProtocolHTTP/1.0 Python/3.11.2` in response headers.

### Observation resource conventions
- Every observation has an **`id`**, a **`status`** (usually `final` or `preliminary`), a **`code`** (LOINC), an **`effectiveDateTime`**, and a **`valueQuantity`** or **`valueCodeableConcept`**.
- **Only `final` status observations count for decision-making.** Preliminary, entered-in-error, and unknown-status observations are ignored.
- When an observation has a mismatched LOINC code (e.g., a sodium result returned when searching for potassium), exclude it and record its id in any `ignored_observation_ids` / `excluded_observation_ids` field.
- When multiple final observations for the same code exist, use the **most recent** (by `effectiveDateTime`).

### Protocol card structure
A protocol card is a structured JSON document. Expect fields like:
- `name` / `id` — matches the protocol constant (e.g., `HEAD_INJURY_2026`).
- `criteria` / `rules` — decision thresholds.
- `redFlags` / `severityFactors` — mappings from observation findings to risk.
- `doseTable` — lookup tables for medication dosing.
- `followUp` — timing rules for follow-up labs or visits.
- `exclusions` — conditions under which observations should be discarded.

---

## Output Field Conventions

### evidence_ids
- **Always include the primary resource id**: the encounter id, case id, or the observation id that is the basis for the decision.
- **Include observation ids for every clinical finding that drove the decision** — e.g., the GCS observation that revealed a red flag, the CXR that confirmed consolidation, the potassium result that triggered replacement.
- **Sort lexicographically.**
- Do NOT include ignored/excluded observation ids. Do NOT include the patient id unless it is also the encounter/case id.

### ignored_observation_ids / excluded_observation_ids
- List every observation that was fetched but **not used** in the decision, along with the reason category:
  - `status: "preliminary"` — not yet final.
  - `status: "entered-in-error"` — erroneous.
  - **Wrong LOINC code** — the observation's code doesn't match the target analyte.
  - **Outside the date window** — e.g., April result when querying May.
  - **Panel/parent observation** — a grouping resource, not an individual result.
- Sort lexicographically.

### List fields
- All list-type fields use **lexicographic (alphabetical) sort**. Apply `Array.sort()` with default string comparison.
- Every item must come from the template's `items_enum`. Never invent new values.
- If no items apply, return an empty array `[]`, not `null` or omitted.

### Enum fields
- Pick exactly one value from the template's `allowed` list.
- Match the protocol card's logic to the patient's data to choose the right enum value.
- Risk levels and dispositions must be consistent: if risk is `urgent_ed`, disposition should be `send_to_ed_now`; if risk is `home_observation`, disposition should be `home_with_observation`.

### Dates and times
- Use **ISO-8601** format with timezone offset when the template specifies it (e.g., `2026-07-06T09:00:00-05:00`).
- Use **YYYY-MM-DD** for date-only fields.
- When the prompt gives a `current_time`, use it as the reference for "now" — do not use the system clock.
- Follow-up timing (e.g., `occurrenceDateTime` for a lab order) should be computed from the protocol card's rules (e.g., "next morning" = next day at 08:00 in the same timezone).

### Numeric precision
- Float values that specify `"precision": 1` must be written with exactly one decimal place (e.g., `3.2`, not `3.20` or `3`).
- Integer fields (`dose_meq`, `matched_count`, `follow_up_hours`) must be whole numbers.

### Nested objects
- Populate every `required` sub-field. If a field's value is contingent (e.g., medication order when replacement is not required), check the template — some nested objects are only present when a boolean parent field is `true`.

---

## Decision Rules by Protocol Type

### Head Injury Triage (HEAD_INJURY_2026)
- Apply red-flag criteria from the protocol card to the encounter's observations (GCS, neuro exam, vomiting history, etc.).
- Map red flags → risk level → CT recommendation → disposition.
- Activity restrictions (school, sports, driving) depend on risk level.
- All risk levels above `home_observation` get the maximum restrictions and all three contraindicated actions.
- `follow_up_hours` is typically 24 for ED cases, longer for lower acuity.

### Respiratory Assessment (RESP_ACUTE_2026)
- Classify severity factors from vitals (O2 sat, respiratory rate), exam findings (crackles, consolidation), and systemic signs (confusion, hypotension).
- Site of care and primary assessment are coupled: CAP with hypoxia → ED evaluation; viral URI with normal vitals → supportive care.
- Antibiotic plan must respect allergy contraindications found in the patient record. The protocol card lists which antibiotic classes are contraindicated for which allergies.
- `contraindicated_antibiotic_classes` lists classes that cannot be used due to patient allergies, NOT the class of the chosen antibiotic.

### Potassium Replacement (POTASSIUM_REPLETION_2026)
- Find the most recent **final** potassium observation with a valid LOINC code before the current time.
- Filter out: preliminary results, wrong-LOINC observations, error-flagged observations, and old-final results superseded by a newer final.
- Apply the protocol's dose table: potassium value → mEq dose.
- `replacement_required` is `true` when the value is below the protocol's threshold.
- The medication order fields (`drug`, `ndc`, `route`, `intent`) are fixed constants from the protocol card.
- Follow-up lab timing: compute from the protocol's rule (typically next morning at 08:00 local time).

### FHIR Lab Retrieval (FHIR_LAB_RETRIEVAL_2026)
- Query for a specific LOINC code within a calendar month.
- Match only **final** observations whose `effectiveDateTime` falls within the month.
- Exclude: observations outside the month, preliminary results, panel/parent resources, observations with different codes.
- `first_match_date` and `last_match_date` are the earliest and latest `effectiveDateTime` among matched observations (date-only).
- `matched_count` must equal the length of `matched_observation_ids`.
- `code_checked` should match the `code` in the query object.

### Complex Care Escalation (COMPLEX_CARE_2026)
- Chart concerns are derived from the patient's diagnoses, recent utilization, and social determinants of health found in the case/patient record.
- Assessment domains map to chart concerns but may be a subset (focus on actionable domains).
- Consent strategy codes follow a hierarchy: always include `avoid_guarantees`, `clear_voluntary_consent`, and `bounded_process_help`; add condition-specific codes based on chart concerns.
- Care-plan problem set is the actionable subset of chart concerns, translated to plan language.
- Disciplines are the team roles needed; always include `care_manager` for complex care, add specialists matching the problem areas.
- `follow_up_cadence`: `weekly` for high risk, `biweekly` for moderate, `monthly` for low.
- `avoid_unsupported_guarantees` is always `true`.

---

## Common Pitfalls

1. **Using preliminary observations for decisions.** Always check `status: "final"`. Preliminary and error observations go into ignored/excluded lists, never into evidence_ids.

2. **Wrong LOINC codes.** When fetching by LOINC, the API may return observations with different codes (e.g., a panel that contains the target code). Check the actual `code` field, not just the query parameter. Mismatched observations are excluded.

3. **Forgetting to sort lists.** Every list field in every template specifies `"ordering": "sort_lexicographic"`. Unsorted lists are incorrect even if the items are right.

4. **Inconsistent risk/disposition coupling.** Risk level and disposition must be a valid pair from the protocol card. Don't pick `urgent_ed` risk with `home_with_observation` disposition.

5. **Missing observation in evidence_ids.** Every observation that contributed to a clinical finding (red flag, severity factor, lab result) must appear in evidence_ids. The encounter/case id itself is also evidence.

6. **Timezone handling.** When the prompt provides a clinical time with timezone (e.g., `-05:00`), compute follow-up times in the same timezone. Don't strip the offset or convert to UTC.

7. **Over-including ignored observations.** The `ignored_observation_ids` / `excluded_observation_ids` fields should contain every fetched-but-discarded observation. Missing one means the filtering logic was incomplete.

8. **Using system time instead of prompt time.** When the prompt specifies `current_time`, use it as the reference for "now" and for computing follow-up windows. Ignore the actual wall clock.

9. **Antibiotic allergy logic.** For respiratory tasks, the `contraindicated_antibiotic_classes` are the classes the patient CANNOT take due to documented allergies — not the class of the chosen antibiotic. The `antibiotic_plan` is the chosen drug that is safe given those contraindications.

10. **Exact enum spelling.** Enum values use underscores and specific casing. `send_to_ed_now` is not `send_to_ER_now`. Copy enum values verbatim from the template's `allowed` list.
