---
name: clinic-decision-support
description: Use for synthetic-clinic decision-support tasks that require querying a
  FHIR-like REST API at TASK_ENV_BASE_URL and producing a structured JSON response
  conforming to a supplied answer_template.json. Always use this skill when the prompt
  mentions a synthetic clinic case ID (CASE-*), a clinic runtime environment, protocol-bound
  clinical assessments, order-entry decision support, care-management routing, or lab-observation
  window retrieval tasks. This skill is essential whenever the task combines a clinic API
  with a JSON answer template containing enum-constrained fields.
compatibility: Requires HTTP access to the task environment base URL and the ability to
  read local files (prompt.txt, answer_template.json, environment_access.md).
---

# Clinic Decision Support Skill

When a task asks you to query a clinic runtime API and return a structured JSON
decision-support response, follow the two-pass process described here. The
templates are dense and the enum constraints are tight; a systematic approach
avoids drift.

## Core Principle

**Read everything before you query anything.** The answer template, the
environment access listing, and the prompt together define every field you will
need. If you start calling the API before you understand what the template
requires, you will miss data or call the wrong endpoints and have to backtrack.

## Two-Pass Workflow

### Pass 1 - Understand What Is Required

1. **Read the prompt.** Extract the case ID and note which clinical domain the
   task targets (respiratory, head-injury, potassium, care-management, or
   lab-window). The prompt tells you *which* case to look up but only hints at
   the output fields; the template is authoritative on structure.

2. **Read the answer template** (`input/payloads/answer_template.json`) slowly
   and systematically. For every top-level key:
   - Note its type (string, enum, list, object, boolean, integer, number).
   - If it is an enum, read the full list of allowed values. These are the only
     values the evaluator will accept for that field.
   - If it is a list, note whether ordering is required or free. When the
     template says "No semantic ordering is required; evaluators normalize this
     as a set," do not waste time on order. When it gives an explicit ordering
     rule (e.g. "Sort by effective_time ascending"), follow it exactly.
   - If it is an object, drill into its required keys and their own constraints.
   - Note every nullable field and every conditionally-required field (e.g.
     "required_when lab_found is true"). These govern when you may use `null`.

3. **Read the environment access listing** (the separate `environment_access.md`
   or equivalent). Note the base URL and every allowed endpoint. You can only
   call endpoints on this list.

4. **Build a retrieval plan.** For each template field that requires clinical
   data, identify which endpoint(s) can supply it. Common mappings:

   | Template needs | Typical endpoint |
   |---|---|
   | Patient identifier, demographics | `GET /api/patients/{patient_id}` |
   | Case details, linked resources | `GET /api/cases/{case_id}` |
   | Observations, vitals, labs | `GET /api/observations` |
   | Imaging reports | `GET /api/imaging` |
   | Medications | `GET /api/medications` |
   | Allergies | `GET /api/allergies` |
   | Problem list / diagnoses | `GET /api/problems` |
   | Protocols / clinical guidelines | `GET /api/protocols` or `GET /api/protocols/{id}` |
   | Care registry / risk scores | `GET /api/care-registry` |
   | Social determinants | `GET /api/sdoh` |
   | Complex cross-resource queries | `POST /api/query` |

   The case endpoint often returns references to related resources (observation
   IDs, imaging IDs, etc.). Use those references to target your follow-up GETs
   rather than scanning every collection endpoint.

### Pass 2 - Gather Data and Fill the Template

1. **Start with the case.** Call `GET /api/cases/{case_id}` first. The case
   resource usually links to the patient and to the clinical resources
   (observations, imaging, medications, allergies) that are relevant to this
   encounter. Record the case ID, patient ID, and the IDs of every linked
   resource.

2. **Retrieve linked resources.** Use the IDs from the case response to call the
   specific resource endpoints:
   - `GET /api/patients/{patient_id}`
   - `GET /api/observations` (filter or scan for the referenced IDs)
   - `GET /api/imaging` (for the referenced imaging studies)
   - And so on for medications, allergies, problems.

   When an endpoint returns a collection, filter by patient and by the dates or
   codes relevant to the template. Do not assume every returned resource belongs
   to the case; verify the patient ID and effective dates match.

3. **Retrieve protocol materials.** If the template asks for protocol-gated
   decisions (assessment level, risk tier, disposition, medication strategy),
   call `GET /api/protocols` or `GET /api/protocols/{protocol_id}`. The protocol
   resource will define thresholds (e.g. oxygen saturation cutoffs, potassium
   ranges, risk-score bands) that determine which enum value to select.

4. **Use `POST /api/query` for complex filters.** When you need observations
   within a date window, or observations matching a specific code and status,
   and the collection endpoint does not support sufficient query parameters,
   use the POST query endpoint with a structured request body. This is
   especially important for tasks that require precise temporal windowing with
   inclusion/exclusion logic.

5. **Resolve each template field against the data.** Work through the template
   top-level keys in order:

   - For **string fields** like `task_id`, `case_id`, `patient_id`: copy the
     exact identifier from the prompt or from the API response. Do not invent
     or approximate.
   - For **enum fields**: find the clinical data point that governs the choice
     (e.g. SpO2 value for risk_level, GCS score for risk_tier, potassium value
     for potassium_plan), then select the single allowed enum value that matches
     the data against the protocol thresholds. If multiple enum values seem
     plausible, re-read the protocol thresholds; one should be unambiguously
     correct.
   - For **list[enum] fields**: go through the clinical facts and add every
     allowed enum value that applies. Do not add values that are not in the
     allowed list even if they seem clinically relevant. If the template says
     ordering is not meaningful, do not spend effort on order.
   - For **boolean fields** (especially safety_checks): these are usually
     confirmations that certain findings are *absent* or that certain
     contraindications do *not* apply. Derive them from the clinical data by
     checking that the relevant finding or allergen is indeed not present.
   - For **numeric fields**: extract the exact value from the API response.
     Match the precision specified in the template (e.g. "one decimal place",
     "two decimal places", "integer"). Do not round differently.
   - For **object fields**: populate every required key. If a key is nullable
     and the clinical situation does not provide a value, use `null` -- but only
     when the template explicitly allows it.
   - For **temporal fields** formatted as ISO-8601: copy the `effectiveTime` or
     equivalent from the API response. Use the `Z` suffix for UTC. When the
     template requires a computed time (e.g. follow-up lab scheduled_time),
     calculate it from the current review time plus the protocol-specified
     interval.

6. **Collect evidence IDs.** The `evidence_ids` field expects the stable
   identifiers of the resources you used to reach your conclusions -- case IDs,
   observation IDs, imaging IDs, protocol IDs. List them in the order the
   template specifies (typically case first, then clinical sources). Include
   only resources you actually consulted and that directly support the
   decision.

### Output Rules

These rules apply to every task in this domain. Violating any of them will
cause the response to fail structural validation before clinical evaluation
begins.

- **Return exactly one JSON object.** No markdown fences, no surrounding prose,
  no comments, no trailing text. The first character of your response must be
  `{` and the last must be `}`.
- **Include every required top-level key.** The template lists them under
  `required_top_level_keys`. Missing keys are a hard failure.
- **Do not add extra top-level keys.** Even if the data seems interesting, the
  evaluator may reject the output for containing unrecognized keys.
- **Use only allowed enum values.** Any string that is not in the template's
  `allowed_values` list will be scored as incorrect, even if clinically
  plausible.
- **Match numeric precision exactly.** If the template says "one decimal place,"
  output `3.2` not `3.20` or `3`. If it says integer, output `5` not `5.0`.
- **Respect nullability.** Never use `null` for a field the template marks as
  required-non-null. Only use `null` where the type field explicitly says
  `"type": ["string", "null"]` or equivalent.
- **Order lists only when the template requires it.** When ordering is
  specified (e.g. "Sort by effective_time ascending"), implement it. When the
  template says ordering is not meaningful, any order is fine.

### Before You Submit: The Validation Pass

After filling every field, do a quick validation pass before returning the
JSON:

1. Count the top-level keys and confirm they match `required_top_level_keys`
   exactly (no missing, no extra).
2. Spot-check three enum fields against their allowed-values list.
3. Verify that every `null` value is in a position the template permits.
4. Confirm the output starts with `{` and ends with `}` with no surrounding
   text.
5. Check that every evidence ID you listed corresponds to a resource you
   actually retrieved and used.

### Common Mistakes

- **Querying the API before reading the template.** This leads to missing
  critical data because you did not know it was required.
- **Using a clinically reasonable value that is not in the allowed enum list.**
  The allowed-values list is exhaustive; if a value is not there, it is wrong
  for this task regardless of clinical merit.
- **Forgetting to retrieve protocol materials.** Many enum decisions depend on
  protocol-defined thresholds that are not embedded in the observation or case
  resources. If the template mentions risk levels or disposition, there is
  almost certainly a protocol resource you need to read.
- **Including preliminary or non-final results in matched observations.** When
  the template asks for "final" results, exclude preliminary, amended, or
  entered-in-error observations. Check the status field on each observation.
- **Rounding numeric values differently from the template specification.**
  Copy the value as-is from the API, then format digits to the exact precision
  the template requires.
- **Omitting safety-check booleans.** These are scored fields; leaving them
  out or guessing is worse than deriving them carefully from the data.

## Reference

Read [references/api-conventions.md](references/api-conventions.md) when you
need more detail about the FHIR-like API patterns used by the clinic runtime,
including how resources link to one another and how to interpret observation
codes, statuses, and effective times.
