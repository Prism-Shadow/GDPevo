---
name: synthetic-clinic-protocol-json
description: Solve synthetic clinic protocol tasks that require querying a read-only clinic runtime, applying patient/case/protocol evidence, and returning exactly one JSON object matching an answer_template.json schema. Use for respiratory CAP, pediatric head injury, potassium replacement, observation-window lab gates, care-management routing, or similar Harborview Synthetic Clinic decision-support tasks.
---

# Synthetic Clinic Protocol JSON

## Core Workflow

1. Read the user prompt, `input/payloads/answer_template.json`, and the run's environment access file before querying anything.
2. Extract the required `task_id`, target `case_id`, output schema, required keys, allowed enum values, ordering rules, nullability, and numeric precision from the template.
3. Query only the allowed read-only clinic runtime endpoints. Never call judge or mutation/order endpoints.
4. Retrieve the target case first, then use its `patient_id`, `case_type`, service/review time, and protocol references to gather relevant patient, observation, medication, allergy, problem, imaging, registry, SDOH, and protocol evidence.
5. Apply the protocol material from the runtime to the target patient's facts. Do not infer unsupported positives or negatives from the few-shot examples.
6. Build the response directly from the template. Return exactly one JSON object with required keys, no markdown, no comments, and no extra narrative.

## Optional Evidence Collector

Use `scripts/collect_clinic_context.py` when you want a deterministic first pass over the runtime data:

```bash
python /path/to/skill/scripts/collect_clinic_context.py \
  --env environment_access.md \
  --case-id CASE-ID-HERE \
  --out /tmp/clinic_context.json
```

The script reads the base URL and token from the environment access file, fetches the target case and related patient-scoped resources, and includes all protocol details. Treat its output as a review aid, not as a replacement for reading the template and protocol text.

## Evidence Handling

- Prefer resources whose `case_id` matches the target case or whose `patient_id` matches the target patient. Include same-patient distractors when the task asks for excluded observations or source-provenance grouping.
- Use final/eligible observations only when the protocol or template requires final status. Keep preliminary, wrong-code, wrong-patient, and outside-window observations available for exclusion lists when requested.
- For "latest" lab decisions, sort eligible observations by effective time and use the most recent final result. For matched observation lists, follow the template's explicit ordering rule.
- For evidence IDs, include stable identifiers from the case, clinical facts, protocol-linked observations, imaging, registry records, or other source resources actually used. Do not invent IDs.
- Separate chart-proven facts from member-disclosed facts when the output schema distinguishes them.

## Protocol Patterns To Check

Use these as checklists while still deriving the final values from the runtime protocol and patient facts:

- Respiratory/CAP: assess symptoms, oxygen saturation, imaging, distress, red flags, allergy-safe antibiotic strategy, stabilization need, diagnostic tests, follow-up interval, and return precautions. Avoid beta-lactams, sulfonamides, macrolides, or tetracyclines only when the patient's allergies require it.
- Pediatric head injury: distinguish observed symptoms from absent red flags; check loss of consciousness, repeated vomiting, seizure, focal deficits, worsening headache, basilar skull signs, photophobia, coordination symptoms, activity/school/driving restrictions, CT/ED criteria, and follow-up route.
- Potassium replacement: identify the latest eligible final serum potassium, renal function, dialysis dependence, arrhythmia symptoms, critical/urgent thresholds, routine oral dose, medication code/details, follow-up lab timing, and contraindications.
- Observation-window gates: identify the target code, inclusive start and exclusive end timestamps, final status, matched observations, relevant excluded observations, latest final result, protocol gate, and repeat-lab recommendation.
- Care-management routing: combine registry risk, diagnoses/problems, recent admissions, dialysis or CKD facts, diabetes control, phosphate/BP/medication-count anchors, medication or food/transport barriers, referral needs, outreach stance, care-plan minima, escalation triggers, and provenance grouping.

## Output Discipline

- Use only enum values allowed by the current template. If the protocol wording differs, map it to the closest allowed enum and verify the mapping against evidence.
- Preserve template-required nulls and booleans exactly. Use `null` only where permitted.
- Round numeric fields to the requested precision and use ISO-8601 UTC timestamps with trailing `Z` when required.
- For unordered sets, omit duplicates. For ordered lists, follow the template's stated sort or relevance rule.
- Set safety-check booleans to `true` only after confirming the response does not assert the prohibited unsupported finding.
- Before final output, compare the JSON keys against `required_top_level_keys` or `required_keys`, validate it parses, and ensure no training-case identifiers, observations, timestamps, numeric values, or answer records were hardcoded.
