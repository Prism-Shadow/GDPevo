---
name: clinic-protocol-json
description: Solve synthetic clinic runtime tasks that ask for protocol-bound clinical decision-support or care-management results as a strict JSON object. Use this whenever a prompt provides a TASK_ENV_BASE_URL, environment_access.md, a target clinic case id, and an input/payloads/answer_template.json schema for respiratory, head-injury, potassium, lab-window, care-management, or similar structured clinic protocol assessments.
---

# Clinic Protocol JSON

Use this skill to turn a target synthetic clinic case into the exact JSON object required by the task's answer template. The runtime API is the source of facts; the template is the output contract; the applicable protocol is the decision rulebook.

## Workflow

1. Read the user prompt and `input/payloads/answer_template.json` before deciding any field. Extract the target `case_id`, `task_id`, required keys, enum values, numeric precision, ordering rules, nullability, and any safety-check meanings.
2. Read `environment_access.md` for the base URL and allowed endpoints. Use only read-only calls unless the task explicitly permits otherwise; these tasks usually say not to mutate or place orders.
3. Collect target context from the runtime. If Python is available, run the bundled collector from the skill directory:

   ```bash
   python scripts/collect_clinic_context.py --env-file /path/to/environment_access.md --case-id TARGET_CASE_ID > /tmp/clinic_context.json
   ```

   If not using the collector, manually call the same API surfaces: target case, patient, observations, medications, allergies, problems, imaging, care registry, social context, and protocol list/details.
4. Filter aggressively. Use the target case to identify the patient, then keep records that match the target `case_id` or target `patient_id`. Treat broad collection endpoints as full of distractors.
5. Fetch protocol details with `GET /api/protocols/{protocol_id}`. Choose the protocol whose title/id/scope matches the case type or prompt. Protocol thresholds, eligible statuses, code mappings, medication choices, follow-up timing, and escalation branches override intuition.
6. Build a small evidence table before drafting JSON: record id, source endpoint, patient id, case id, code/display, status, effective time, value, and whether it qualifies. This prevents mixing target evidence with distractors.
7. Apply the protocol to eligible facts only, then fill every required template field using the template's exact enum spelling and shape. Use `null` only where allowed.
8. Return exactly one JSON object. Do not include markdown, comments, explanations, extra keys, or unrequested narrative.

## Eligibility Rules

- Prefer source identifiers over prose for provenance. Include the evidence ids that directly support scored decisions; do not pad with unrelated records.
- Honor status rules. If a protocol or template requires final results, exclude preliminary, canceled, and entered-in-error records. Include excluded ids only when the template asks for them.
- For observation windows, apply the exact target code, patient, status, and inclusive/exclusive time window from the prompt, case, protocol, or template. Sort matched and excluded records as specified by the template.
- For latest-result fields, choose the latest qualifying effective time after filtering, not the latest-looking distractor in the global collection.
- For active medications, allergies, and problems, check status. Active items usually drive decisions; inactive or historical items usually do not unless the task specifically asks for them.
- For safety-check booleans, answer from the chart review. A `true` safety check usually means the final JSON avoids a known unsupported or unsafe claim.

## Domain Patterns

- Respiratory/CAP tasks: combine symptoms from the case, oxygen saturation and recheck observations, final chest imaging, viral testing, allergies, and the respiratory protocol. Do not call imaging normal or lungs clear unless the record supports that. Allergy-aware antibiotic selection matters.
- Pediatric head-injury tasks: separate present red flags from explicitly absent red flags. Loss of consciousness, vomiting, seizure, focal weakness, worsening headache, basilar signs, and photophobia require direct support before marking present or absent. Imaging and restrictions come from the protocol tier.
- Potassium replacement tasks: identify the latest eligible final serum potassium for the target patient/case, screen renal function and urgent contraindications, then compute route, dose, follow-up lab timing, and urgent actions from the protocol. Do not use the system clock as clinical review time if the case provides one.
- Observation-window lab tasks: distinguish wrong date, wrong code, wrong status, and wrong patient/case. The downstream gate follows the latest qualifying final result or the absence of one.
- Care-management routing tasks: combine registry risk, active problems, recent admissions, observations, active medication count, dialysis context, and social-context records. Separate chart-derived facts from member-disclosed barriers when the template asks for provenance grouping.

## Final Check

Before answering, compare the JSON against the template:

- All required top-level keys are present and no extra keys are present unless the template permits them.
- Lists use allowed enum values once each, with template-specific ordering where required.
- Numeric values use requested precision and units.
- Timestamps are ISO strings with `Z` when required.
- Evidence ids are real ids from the runtime and support the selected fields.
- Safety checks align with the claims made in the JSON.
