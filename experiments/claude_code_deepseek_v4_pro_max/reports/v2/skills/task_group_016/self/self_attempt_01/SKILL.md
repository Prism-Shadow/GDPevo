# ClinicProtocol Decision-Support Skill

## Overview

This skill covers structured clinical decision-support tasks served by a remote ClinicProtocol HTTP API. Each task requires fetching patient records, protocol definitions, and clinical observations from the API, then applying protocol rules to produce a single JSON answer matching a provided answer template.

Always resolve `<TASK_ENV_BASE_URL>` from `environment_access.md` before making any API calls. If the task prompt mentions a local URL, the environment_access.md value overrides it.

---

## API Surface

The ClinicProtocol API exposes exactly three endpoints. There is no discovery endpoint, no search, and no pagination.

### 1. Patient records
```
GET {BASE_URL}/api/patients/{patient_id}
```
Returns `{"patient": {...}}` with demographics, active/inactive problems, allergies, medication summaries, address, and contact info. The `patient_id` field inside the response matches the URL parameter.

### 2. Protocol definitions
```
GET {BASE_URL}/api/protocols/{protocol_name}
```
Returns `{"protocol": {...}}` with `protocol_id`, `title`, `version`, `effective` date, `local_rules` (natural-language decision rules), and `outputs` (allowed enum values and constants). The protocol name is always an UPPER_SNAKE_CASE identifier with a `_2026` year suffix.

### 3. Observations (global list)
```
GET {BASE_URL}/api/observations
```
Returns `{"count": N, "observations": [...]}` — **all** observations for all patients in a single array. There is no per-patient or per-encounter filtering endpoint. You must fetch the full list and filter client-side by `patient_id`, `encounter_id`, `code`, and `status`.

Each observation has: `id`, `patient_id`, `encounter_id` (nullable), `resourceType` ("Observation"), `status`, `category`, `code`, `display`, `effectiveDateTime`, `value`, `unit`, `interpretation`, `panel_header` (boolean), and optional `notes`.

---

## Core Workflow

For every task, follow this sequence:

1. **Read the answer template** (`input/payloads/answer_template.json`) to understand required keys, allowed enum values, and output structure.
2. **Identify the relevant patient(s) and protocol** from the prompt.
3. **Fetch the patient record** via `GET /api/patients/{patient_id}`.
4. **Fetch the protocol definition** via `GET /api/protocols/{protocol_name}`.
5. **Fetch all observations** via `GET /api/observations` and filter to the target patient(s) and/or encounter(s).
6. **Apply protocol rules** to the filtered clinical data to derive each output field.
7. **Assemble the answer JSON** matching the template exactly — every key in `required_top_level_keys` must be present; every enum field must use exactly one of its `allowed` values; every list field must be sorted lexicographically.
8. **Populate `evidence_ids`** with the stable observation IDs (and/or protocol IDs) that directly support the decision.

---

## Observation Filtering Rules

These rules apply every time you filter observations:

### Status filtering
Only `"final"` observations count for clinical decisions. **Always exclude** observations with status:
- `"preliminary"` — unverified, may have incorrect values
- `"entered-in-error"` — explicitly invalid
- `"cancelled"` — voided

### Panel headers
Observations with `"panel_header": true` are grouping/parent resources, not actual results. Always exclude them from matched result sets and from dose selection.

### Code matching
Protocols reference observations by a `code` field (e.g., `"K"` for potassium, `"4548-4"` for HbA1c, `"2823-3"` for LOINC-coded potassium). Match exactly — do not use LOINC codes when the protocol specifies a local code, and vice versa. An observation with a different code is simply not a match, not an "excluded" observation.

### Date window semantics
- A **month window** (e.g., "May 2026") includes all instants from the first day at 00:00:00 through the last day at 23:59:59 in the observation's local timezone (as encoded in `effectiveDateTime`).
- **Most recent** means the latest `effectiveDateTime` among the filtered set.
- **Stale** observations (significantly older than the clinical time window) should not override current data but are not "ignored" — they are simply not the most recent.

### Patient-id matching
Only consider observations whose `patient_id` exactly matches the target patient. Observations for other patients (even with similar IDs like `PAT-L-X001` vs `PAT-L-T001`) are irrelevant.

---

## Protocol Rule Application Patterns

### Route/site-of-care triage
Protocols define escalating routes (e.g., `home_observation` → `same_day_clinic` → `urgent_ed`). Map clinical findings to the **highest** applicable route. Each protocol's `local_rules` specifies the trigger criteria for each route. When multiple criteria are present, the most acute route wins.

### Contraindication cascades
When a patient has allergies or active medications in a risk category, apply prohibitions transitively:
- **Allergy-driven**: If allergic to penicillin → contraindicate `penicillin` class. If allergic to sulfonamides → contraindicate `sulfonamide`.
- **Drug-interaction-driven**: If the patient takes a QT-prolonging medication (category `qt_risk`) → contraindicate both `macrolide_qt_risk` and `fluoroquinolone_qt_risk` for antibiotic selection, unless an ED route overrides.
- Select the **remaining** antibiotic option after removing contraindicated classes.

### Dose calculation
When a protocol specifies a dose formula (e.g., "10 mEq per 0.1 mEq/L below target, rounded up to the next 10 mEq"):
1. Compute the deficit: `target - actual_value`
2. Compute raw dose: `(deficit / step_size) * dose_per_step`
3. Round up to the next multiple of the dose unit (ceil division)

### Follow-up timing
Protocols specify follow-up windows relative to the decision time. The task prompt may provide a reference `current_time` in ISO-8601 with timezone offset. Use that timezone for all derived timestamps. When the protocol says "next calendar day at 08:00," compute from the reference time's date, not UTC.

---

## Output Field Conventions

### Lexicographic sorting
All list fields must be sorted **lexicographically** (standard string sort, not numeric or by length). This applies to `red_flags_present`, `contraindicated_actions`, `evidence_ids`, `matched_observation_ids`, `excluded_observation_ids`, `severity_factors`, `required_tests`, `return_precautions`, `chart_concerns`, `required_assessment_domains`, `consent_strategy_codes`, `care_plan_problem_set`, `disciplines`, `escalation_triggers`, `ignored_observation_ids`, and any other list in the answer template.

### ISO-8601 timestamps
All date/time fields (`current_time`, `effectiveDateTime`, `occurrenceDateTime`, `first_match_date`, `last_match_date`) must use ISO-8601 format. Include the timezone offset when the source data includes it. Date-only fields (`first_match_date`, `last_match_date`) use `YYYY-MM-DD` format.

### Enum strictness
Every enum field in the answer template lists explicit `allowed` values. Use exactly one of those values — do not invent new ones, combine them, or use near-matches. The protocol's `outputs` section often mirrors these enums to confirm available choices.

### Boolean fields
Use JSON `true`/`false` (not strings). Boolean fields include `replacement_required`, `has_matching_lab`, `avoid_unsupported_guarantees`.

### Evidence IDs
`evidence_ids` is always a lexicographically sorted list of strings. Populate it with the **stable observation IDs** (e.g., `"OBS-H-T001-GCS"`) that directly support the clinical decision. Include the observations whose values drove rule application — not every observation for the patient, and not observations that were excluded. The evidence IDs make the decision auditable: someone reviewing the output should be able to find each referenced observation and verify it supports the conclusion.

For protocol-only decisions where no specific observation is the trigger, include the protocol ID (e.g., `"HEAD_INJURY_2026"`) alongside relevant observations.

---

## Common Pitfalls

1. **Forgetting to filter by status** — A `"preliminary"` observation may have a value close to a `"final"` one but must never be used for clinical decisions. Always check `status` before selecting the "most recent" value.

2. **Panel header confusion** — A panel header shares the same `code` and `patient_id` as real results. It will appear in a naive code+patient filter. Always check `panel_header` and exclude `true` entries.

3. **Wrong code matching** — An observation with LOINC code `2823-3` is NOT the same as one with local code `K`, even though both represent potassium. Follow the protocol's exact code specification.

4. **Timezone mishandling** — When the task provides a `current_time` with a timezone offset (e.g., `-05:00`), use that offset for follow-up timestamps. The "next calendar day at 08:00" means 08:00 in that timezone, not UTC.

5. **Ignoring distractor patients** — The observations list contains patients with similar IDs (e.g., `PAT-H-X001` alongside `PAT-H-T001`). The `X` variants typically represent different clinical scenarios and are not relevant. Filter strictly by the target `patient_id`.

6. **Incomplete contraindication lists** — When a patient has both an allergy AND a QT-risk medication, list ALL resulting contraindicated classes, not just one category. Both `penicillin` (from allergy) and `macrolide_qt_risk` + `fluoroquinolone_qt_risk` (from drug interaction) apply simultaneously.

7. **Dose rounding errors** — "Rounded up to the next 10 mEq" means ceiling to the nearest multiple of 10. A raw dose of 30 is already a multiple of 10, so it stays 30. A raw dose of 32 rounds up to 40.

8. **Mixing up "excluded" vs "not matched"** — An observation with a different `code` was never a candidate for matching; it is not "excluded." Reserve `excluded_observation_ids` for observations that matched on `patient_id` + `code` but were filtered out due to status, panel_header, or date window.

9. **Evidence inflation** — Do not include every observation for the patient in `evidence_ids`. Only include the IDs that directly support the decision. Evidence should be sufficient and necessary — someone auditing the output should see exactly which data points drove the conclusion.

10. **Enum value mismatch** — The answer template is authoritative. If the protocol text describes a route as "ED evaluation" but the template enum is `"ed_evaluation"`, use the template's value. Always cross-reference protocol `outputs` with the template `allowed` values.
