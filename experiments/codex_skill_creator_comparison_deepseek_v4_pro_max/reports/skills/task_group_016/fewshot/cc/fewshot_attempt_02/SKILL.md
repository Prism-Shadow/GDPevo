---
name: clinic-protocol-assessor
description: Use when preparing structured clinical decision-support responses for synthetic clinic cases. Triggers on prompts mentioning clinic protocol assessments, clinical decision-support tasks, structured clinical responses, answer templates with enumerated fields, synthetic clinic cases, or tasks that require querying a clinic REST API runtime and returning a conformant JSON object. Use this whenever the prompt references a case ID, an answer template, a task environment base URL, or clinical protocol terminology — even if the user does not explicitly ask for a protocol assessment.
---

# Clinic Protocol Assessor

You prepare structured clinical decision-support responses for synthetic clinic cases. Every task provides a prompt, an answer template JSON, and access to a clinic REST API runtime. Your output is always a single JSON object that conforms exactly to the template.

## Core Workflow

Follow this sequence for every task. Do not skip or reorder steps.

### Step 1 — Gather Input Artifacts

Read these documents from the workspace:

- The **task prompt** — contains the case identifier, domain context, and any task-specific instructions
- The **answer template** (`answer_template.json` or inline in the prompt) — the required output schema with keys, allowed enum values, types, nullability rules, ordering rules, and numeric precision constraints
- The **environment access** — base URL and allowed REST endpoints for this run (provided in `environment_access.md` or inline)

### Step 2 — Parse the Template Thoroughly

The answer template is the binding specification. Before any API call, extract every constraint:

- **`required_top_level_keys`** — your output object must include exactly these keys and no extras
- **Allowed enum values** under `allowed_values` for every field — your selections come only from these lists
- **Nullability rules** — use `null` only where the field specification explicitly permits it (check `type` for `"null"` or `["string", "null"]` or `["integer", "null"]` patterns)
- **Ordering rules** — when a list says "no semantic ordering" you may use any order; when it says "sort by effective_time ascending" or similar, follow that exactly
- **Numeric precision rules** — one decimal place for mmol/L and percentages, integer values for dose mEq, duration days, and timeframe hours
- **`required_keys` within nested objects** — every sub-object key listed as required must be present
- **`output_rules` or `additional_properties` blocks** — follow all constraints in these sections

### Step 3 — Query the Clinic API Systematically

Use the REST endpoints exposed by the environment. Start with the case and fan out to gather supporting clinical data.

**Query chain:**

1. `GET /api/cases/{case_id}` — retrieve the target case; extract the `patient_id` and any case-level flags
2. `GET /api/patients/{patient_id}` — retrieve patient demographics and identifiers
3. Fan out to independent clinical endpoints in parallel:
   - `GET /api/observations` — filter by patient and code to find lab results, vitals, and clinical measurements; for window-based tasks filter by effective date range
   - `GET /api/medications` — active medications, medication history
   - `GET /api/allergies` — allergy list (always check before recommending any medication)
   - `GET /api/problems` — problem list and chronic conditions
   - `GET /api/imaging` — imaging reports and radiology findings
   - `GET /api/care-registry` — risk scores and program eligibility data
   - `GET /api/sdoh` — social determinants: transportation, financial, food barriers
   - `GET /api/protocols` or `GET /api/protocols/{protocol_id}` — protocol decision rules, thresholds, and escalation criteria
   - `POST /api/query` — use for parameterized lookups when direct GET filtering is insufficient

**Observation filtering rules:**
- Pay attention to observation `status` — only `final` results count for clinical decisions unless the template or protocol explicitly allows preliminary values
- Sort by `effective_time` when the template requires chronological ordering
- Filter observations to the patient identified from the case record
- When the task defines a date window, apply inclusive start and exclusive end boundary filtering

**Parse API responses carefully.** Each response is structured JSON. Note observation codes, effective times, value quantities with units, and status fields.

### Step 4 — Apply Protocol Reasoning

This is the clinical judgment step. For domain-specific reasoning patterns and decision thresholds, consult `references/clinical_domains.md`.

Principles that apply across all domains:

- **Evidence-driven decisions.** Every clinical assertion must trace to specific observation IDs, case facts, or protocol rules. Populate `evidence_ids` with the actual identifiers — observation IDs, case IDs, imaging IDs — that support your conclusions.
- **Allergy-aware prescribing.** Before recommending any medication, cross-reference the patient's allergy list. Set `avoid_allergens` to match the patient's actual allergies. Select antibiotic strategies that avoid listed allergens.
- **Safety checks are assertions about what was NOT found.** A safety check like `no_false_loc` means "it is true that loss of consciousness was absent from the record." Set it to `true` when the clinical data confirms the finding is absent, `false` when the finding is present.
- **Enum values are exhaustive.** Every clinical decision maps to one of the allowed values. If uncertain, re-read the protocol material and clinical data — the answer is determinable from the available evidence.
- **Timestamps use ISO-8601 UTC with trailing Z.** Extract timestamps from observation `effective_time` fields or case metadata. All datetime fields must end in `Z`.
- **Numeric precision.** One decimal place for mmol/L, percentages, and mg/dL values. Integer precision for dose mEq, duration days, timeframe hours, and counts. Do not add extra decimal places.
- **Empty lists use `[]`, not `null`.** Unless the schema explicitly permits null for a list field, use an empty array when no items apply.
- **Stabilization actions are immediate.** Only include stabilization actions when the clinical data shows acute danger — hypoxemia, critical lab values, altered mental status, or protocol-specified urgent criteria.
- **Absent red flags.** When a template has both `red_flags` (findings present) and `absent_red_flags` (findings confirmed absent), review the full allowed-values list and place each value in exactly one of the two lists.

### Step 5 — Build the Output JSON

Assemble your JSON with exactly the required top-level keys.

- No markdown fences, no comments, no explanatory text — return only the JSON object
- List ordering: follow any explicit sort rule; for "no semantic ordering" lists, maintain internal consistency
- Nested objects: verify every `required_keys` sub-key is present
- All enum values come from the allowed lists — never invent a value

### Step 6 — Validate Before Returning

Run these checks before finalizing:

1. Every `required_top_level_key` is present; no extra top-level keys exist
2. Every enum field uses only allowed values from the template
3. All timestamps end in `Z` and use ISO-8601 format
4. `evidence_ids` contain only real identifiers found in API responses
5. Safety check booleans are consistent with the clinical data — they do not contradict findings
6. Allergy lists match the patient's actual allergies from the API
7. `null` is used only where the schema permits it
8. Numeric precision matches the schema specification

## Output Rule

Return exactly one JSON object. No markdown fences, no trailing characters, no explanation.

## Reference Files

- `references/api_endpoints.md` — detailed description of each REST endpoint and its response shape
- `references/clinical_domains.md` — domain-specific protocol patterns for respiratory, head injury, potassium replacement, care management, and lab observation tasks

