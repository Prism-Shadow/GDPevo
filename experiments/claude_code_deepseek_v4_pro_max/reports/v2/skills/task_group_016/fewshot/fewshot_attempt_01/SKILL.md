# ClinicProtocol Decision-Support Skill

## Environment

- Base URL: `GDPEVO_ENV_BASE_URL` (set in environment). No localhost or alternate endpoints.
- All patient, encounter, case, observation, and protocol-card data is retrieved through the ClinicProtocol HTTP API at that base URL.
- Do not read env source files, run setup scripts, or use localhost.

## Workflow

### 1. Read the Answer Template First

Before any API calls, read `input/payloads/answer_template.json`. This file defines:
- Every required top-level key (never omit or add keys)
- The allowed enum values for each field (never use a value outside the enumerated set)
- The ordering rule for every list field (always `sort_lexicographic`)
- Nested object structures and their required sub-keys

The answer you return must be a single JSON object whose shape exactly matches the template.

### 2. Identify Task Type from the Template

The `primary_protocol` enum reveals the task domain. Common protocol values seen in training:

| Protocol | Task Domain |
|---|---|
| `HEAD_INJURY_2026` | Head-injury triage (encounter-based risk and disposition) |
| `RESP_ACUTE_2026` | Acute respiratory visit (assessment, severity, antibiotics) |
| `POTASSIUM_REPLETION_2026` | Lab-driven potassium replacement with medication order |
| `FHIR_LAB_RETRIEVAL_2026` | FHIR-style Observation query with date/code filtering |
| `COMPLEX_CARE_2026` | Complex-care management escalation (case-based) |

The template's required keys tell you what data to extract. Examples of task-type signals:
- Templates with `latest_potassium`, `dose_meq`, `follow_up_lab` → lab-replacement task
- Templates with `query`, `has_matching_lab`, `matched_observation_ids` → FHIR retrieval task
- Templates with `chart_concerns`, `consent_strategy_codes`, `program_type` → care-management task
- Templates with `risk_level`, `ct_recommendation`, `red_flags_present` → triage task

### 3. Retrieve Protocol Cards from the API

Each prompt states: "The relevant local protocol cards are available through the same API." Use the API to fetch the protocol cards that correspond to the `primary_protocol` value. The protocol cards contain the decision rules, thresholds, and mappings needed to populate the answer.

Protocol cards define:
- Clinical thresholds (e.g., potassium ranges → dose amounts, red-flag combinations → risk levels)
- Decision trees (findings → assessment → site of care → actions)
- Contraindication rules (patient factors that block certain treatments)
- Timing rules (follow-up windows, lab recheck intervals)
- Enum-to-enum mappings (severity factors → required tests, chart concerns → assessment domains)

### 4. Fetch Patient / Encounter / Case Data

Use the API to retrieve all resources referenced in the prompt:
- **Patient** resources by patient ID
- **Encounter** resources by encounter ID (if the prompt mentions one)
- **Case** resources by case ID (if the prompt mentions one)
- **Observation** resources linked to the patient (lab results, vitals, etc.)

Stable resource IDs from the API responses are the ground truth — never invent IDs.

### 5. Apply Protocol Rules to the Retrieved Data

Map the clinical data onto the protocol rules:
- For **triage tasks**: count red flags, determine risk route, derive CT recommendation, disposition, and contraindicated actions from the protocol's decision table.
- For **lab-replacement tasks**: find the latest valid (final, correct LOINC, in-range) observation, check its value against protocol thresholds, determine dose, build the medication order and follow-up lab timing per protocol.
- For **FHIR retrieval tasks**: filter observations by code, month, and status; separate matched from excluded; extract date bounds.
- For **care-management tasks**: map chart findings to concerns, assessment domains, disciplines, consent codes, and escalation triggers per the protocol's care-model rules.

### 6. Build the Answer Object

Follow these conventions when populating fields:

#### General Field Conventions

- **All keys and enum string values** use `snake_case`.
- **All list fields** must be sorted lexicographically (ascending, case-sensitive).
- **Boolean fields** use JSON `true`/`false` (not strings).
- **Integer fields** use JSON numbers (not strings).
- **ISO-8601 timestamps** include the timezone offset when one is given in the prompt; use the prompt's `current_time` exactly when provided.

#### evidence_ids

When the answer template includes an `evidence_ids` field, populate it with the stable resource identifiers that directly support the decision. Typical contents:
- The encounter ID (if an encounter was evaluated)
- The observation IDs of lab results or clinical findings that drove the protocol decision

Do NOT include:
- IDs that were considered but excluded (those go in `ignored_observation_ids` or `excluded_observation_ids`)
- Every observation on the patient — only the ones the protocol decision rests on
- Protocol card IDs or other metadata

Sort evidence_ids lexicographically.

#### ignored_observation_ids / excluded_observation_ids

When these fields are present, list every observation ID that was retrieved but filtered out, with the reason implied by the protocol rules. Common exclusion reasons:
- **Wrong code/LOINC**: observation measures something other than the target analyte
- **Wrong date range**: outside the query window (too old, wrong month)
- **Preliminary status**: not yet final/validated
- **Error status**: entered in error or otherwise invalid
- **Panel/grouped**: part of a panel rather than a standalone result

Sort these lexicographically.

#### Time and Date Fields

- `current_time`: use the exact ISO-8601 string from the prompt.
- `effectiveDateTime` / `occurrenceDateTime`: use the timestamp from the API resource.
- `first_match_date` / `last_match_date`: use `YYYY-MM-DD` format (date only).
- `follow_up_lab.occurrenceDateTime`: compute from protocol rules (typically next calendar day at a fixed morning hour, preserving the prompt's timezone).
- `month` (in query): use `YYYY-MM` format.

#### Nested Objects

When the template defines a nested object (e.g., `activity_plan`, `medication_order`, `follow_up_lab`, `query`, `latest_potassium`), every required sub-key must be present and must use an allowed enum value. Do not add extra keys.

#### Enum Selection Rules

- For **single-value enums** (e.g., `drug`, `ndc`, `route`, `intent`, `loinc`, `display`, `priority`, `resourceType`): use the sole allowed value — it is a fixed constant for that protocol.
- For **multi-choice enums** (risk_level, assessment, site_of_care, etc.): select the single value that best matches the clinical data against the protocol rules.
- For **multi-choice enum lists** (red_flags_present, severity_factors, chart_concerns, etc.): include every applicable value from the allowed set, sorted lexicographically.

### 7. Verify Before Returning

Before finalizing the answer:
- Confirm every key in the template's `required_top_level_keys` is present.
- Confirm no extra keys beyond those in the template.
- Confirm every enum value is exactly as spelled in the template (including underscores and casing).
- Confirm every list is sorted lexicographically.
- Confirm nested objects have all their required sub-keys.
- Confirm counts match: `matched_count` equals `len(matched_observation_ids)`.
- Confirm date fields are in the correct format (ISO-8601 for timestamps, YYYY-MM-DD for dates).
- Confirm boolean fields are JSON booleans, not strings.
- Confirm integer fields are JSON numbers, not strings.

## Common Pitfalls

1. **Missing the template**: Skipping the answer template read leads to wrong keys, missing fields, or invented enum values. Always read the template first.

2. **Enum value drift**: Using a value that is close but not exact (e.g., `home_observation` vs `home_with_observation`, `urgent_ed` vs `ed_urgent`). Match the template's allowed values character-for-character.

3. **Wrong sort order**: Lists must be lexicographically sorted. Unsorted lists are wrong even if the set of values is correct.

4. **Including excluded observations in evidence**: `evidence_ids` should only contain the resources that support the decision, not every observation fetched. Excluded/filtered-out observations go in the excluded/ignored list.

5. **Wrong date format**: Using ISO-8601 when the field expects `YYYY-MM-DD`, or omitting the timezone when the prompt provides one.

6. **Ignoring protocol thresholds**: Doses, risk levels, and dispositions are determined by protocol thresholds (e.g., potassium below X → dose Y). Apply the protocol rules exactly rather than guessing.

7. **Forgetting nested required keys**: Objects like `activity_plan`, `medication_order`, and `follow_up_lab` have required sub-keys — missing one breaks the schema.

8. **Type errors**: Booleans as strings (`"true"`), integers as strings (`"24"`), or numbers where integers are expected.

9. **Over-inclusion in enum lists**: Including every possible enum value in a list field just to be safe. Only include values that the clinical data and protocol rules actually support.

10. **Not using the prompt's current_time**: When the prompt gives a `current_time`, use it verbatim rather than generating a new timestamp or using the system clock.
