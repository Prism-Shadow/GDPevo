---
name: clinic-protocol-json
description: Use when solving synthetic-clinic protocol tasks that provide environment_access.md, a clinic runtime base URL, and input/payloads/answer_template.json, and require one schema-conformant JSON object for clinical decision support, observation-window retrieval, medication or lab recommendations, respiratory or head-injury assessment, potassium replacement, or care-management routing.
---

# Clinic Protocol JSON

## Core Workflow

Use the prompt, `input/payloads/answer_template.json`, and `environment_access.md` as the task contract. Return exactly one JSON object and no markdown or narrative.

1. Read the prompt and template before fetching data. Extract the target case id, task id, required top-level keys, allowed enum values, nullability, ordering rules, precision rules, and safety-check fields.
2. Read `environment_access.md` for the base URL and allowed endpoints. Fetch only allowed read endpoints. Do not mutate the runtime, place orders, or invent unavailable endpoints.
3. Build a case bundle from runtime facts: case, patient, encounter context, observations, medications, allergies, problems, imaging, care registry, social context, and protocol materials. Match records by case id, patient id, encounter id, protocol id, date windows, observation code, and final/preliminary status as applicable.
4. Apply the clinic protocol text first. Use general clinical knowledge only to interpret protocol terms when the runtime protocol is silent, and keep the answer inside the template's controlled values.
5. Fill every required key and nested required key. Use `null` only where the template permits it. Do not add extra top-level keys.
6. Validate the JSON mechanically before finalizing.

Helpful commands:

```bash
python skill/scripts/fetch_clinic_context.py --env environment_access.md --case CASE_ID --out /tmp/clinic_context.json
python skill/scripts/validate_answer.py input/payloads/answer_template.json /tmp/answer.json
```

## Evidence Handling

Prefer source identifiers from the runtime over descriptive prose. Include only identifiers that directly support the selected assessment, gate, plan, or safety check.

For observation tasks, separate matching and excluded observations explicitly. A final target-code observation inside an inclusive start and exclusive end window qualifies; wrong code, wrong patient, out-of-window, and preliminary or non-final results do not. Sort observation ids exactly as the template states.

For protocol-assessment tasks, evidence usually includes the case id plus the most decisive observation, imaging, registry, or protocol identifiers. If the template requests stable ordering, put the case id first, then clinical sources.

## Decision Patterns

For respiratory assessments, base the assessment and disposition on the protocol, oxygen saturation, respiratory distress, chest symptoms, fever course, imaging, and allergy list. Avoid allergy-conflicting antibiotics. Do not claim normal chest imaging or clear lungs unless the fetched record supports that exact finding.

For head-injury assessments, distinguish present red flags from absent red flags. Count explicitly documented symptoms and mechanism findings as present; include absent dangerous findings only when the record states they are absent. Use the protocol to decide observation, emergency evaluation, CT posture, activity restriction, school restriction, driving restriction, and follow-up timing.

For potassium replacement and lab-gate tasks, use the latest eligible final serum potassium for the requested patient and window. Screen renal function, dialysis dependence, arrhythmia symptoms, and urgent thresholds before recommending routine oral replacement. Pull medication code, route, frequency, dose, repeat-lab code, and timing from the runtime protocol or medication data rather than inventing order details.

For care-management routing, combine registry risk tier, diagnosis/problem facts, recent utilization, medications, labs, dialysis or kidney status, blood pressure, and social-context records. Keep chart-derived facts separate from member-disclosure-needed items. Care-plan minimums, outreach stance, referrals, and escalation conditions should come from the care-management protocol.

## Safety Rules

Treat safety-check booleans as assertions that unsupported or contraindicated claims were avoided. Set them to `true` only after checking the raw facts relevant to that field.

Do not infer absence from a missing endpoint alone when the task asks for absent clinical red flags; prefer explicit negative documentation. Do not include a medication plan that conflicts with documented allergies or contraindications. Do not let plausible clinical defaults override the provided protocol or answer template.

## Validation

Use `scripts/validate_answer.py` to catch schema and enum mistakes. If it flags an issue, fix the JSON answer, not the template. After validation, re-read the final JSON once for clinical consistency: identifiers match the case and patient, evidence ids exist in the runtime data, dates are in the requested window, and numeric precision follows the template.
