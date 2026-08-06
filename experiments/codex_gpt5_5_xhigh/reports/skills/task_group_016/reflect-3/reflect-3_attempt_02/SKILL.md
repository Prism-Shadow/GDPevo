---
name: synthetic-clinic-protocol-json
description: Build strict JSON answers for protocol-bound synthetic clinic tasks that require retrieving a target case, patient-linked clinical records, observations, registry/SDoH facts, and protocol rules; applying controlled enums, time windows, status filters, safety checks, and evidence provenance exactly as requested by an answer template.
---

# Synthetic Clinic Protocol JSON

Use this skill for synthetic clinic decision-support tasks where the user provides a prompt, an answer template, and runtime access to case, patient, observation, medication, allergy, problem, registry, SDoH, imaging, or protocol records. The goal is a single schema-conformant JSON object, not a narrative.

## Workflow

1. Read the prompt and answer template first. Treat the template as the contract: required keys, enum values, object shapes, precision, ordering rules, nullable fields, and extra-key restrictions override normal prose instincts.
2. Identify the target case id, task id, expected case type, target patient id if supplied, clinical review time, target observation codes, and any time windows.
3. Retrieve the target case first, then use its patient id to gather only patient-linked records needed by the template and the applicable protocol. Keep distractors separate from qualifying evidence.
4. Read the relevant protocol material before deciding any assessment, disposition, routing, replacement plan, observation gate, follow-up timing, or medication strategy.
5. Build the JSON from the template outward. Fill identifiers and raw anchors first, then derived protocol decisions, then provenance and safety checks.
6. Validate the final object against the template before answering: no markdown, no comments, no extra top-level keys unless the template explicitly permits them, and no prose where an enum is required.

## Evidence Rules

- Prefer final/authoritative records. Exclude preliminary, canceled, and entered-in-error observations from clinical decisions unless the template specifically asks to list excluded records.
- Match observations by patient id, case relevance, exact target code, status, and time window. Do not treat similar codes as interchangeable; for example, serum and whole-blood lab codes can represent different targets.
- For time windows, honor inclusivity exactly. If the template says the start is inclusive and the end is exclusive, use `start <= effective_time < end`.
- Sort lists exactly as specified. Common patterns are matched observations by effective time ascending, then observation id ascending; latest-final fields by maximum final effective time; and provenance by the template’s relevance or stability instruction.
- Include excluded observation ids only for the exclusion reasons requested by the template. If the field describes exclusions by date, code, or status, do not add wrong-patient records unless the schema explicitly includes patient mismatch.
- Use evidence ids that directly support the answer. Avoid padding with loosely related protocol ids, imaging ids, or source ids unless the template requests them or they are needed to justify an answer field.

## Protocol Application

- Apply escalation and contraindication branches before routine plans. If any urgent trigger is present under the protocol, use the urgent disposition/action fields and defer routine outpatient or medication details when the template allows.
- Derive medication plans from active allergies, contraindications, medication lists, and protocol-controlled medication rules. Avoid active allergen classes and set allergy/safety booleans based on what the answer actually avoids or claims.
- Calculate numeric protocol outputs from the protocol rule, not from memory. Preserve required precision, units, integer rounding, and nullability.
- Use the case’s clinical review time for scheduling when provided. If a protocol gives a relative timing rule, convert it to the requested ISO-8601 UTC timestamp only when the rule is specific enough; otherwise use the template’s permitted null/defer value.
- For respiratory assessments, distinguish outpatient caution from emergency escalation by the protocol thresholds. Supported consolidation plus infectious symptoms can establish pneumonia, while oxygen, respiratory rate, blood pressure, confusion, and imaging extent drive risk and disposition.
- For pediatric head injury, separate documented present findings from documented absent urgent red flags. Do not infer loss of consciousness, vomiting, photophobia, focal weakness, or skull-base signs without a source. Restrictions should follow the protocol’s return-to-learn, sports, activity, and driving branches for the selected risk tier.
- For potassium tasks, select the latest eligible final serum potassium result for status and dosing. Exclude wrong code, wrong status, wrong patient, or out-of-window observations according to the template. Screen renal failure, dialysis dependence, ECG findings, and arrhythmia symptoms before routine replacement.
- For care-management routing, combine registry risk, active problems, final labs/vitals, medication burden, recent admissions, dialysis/advanced kidney disease, heart failure, uncontrolled diabetes, and member-disclosed barriers. Keep chart-derived facts separate from facts requiring member disclosure.

## Safety Checks

- Treat safety-check booleans as claims about the output, not as generic clinical facts. Set them true only when the answer avoids the unsupported claim named by the field.
- Do not claim normal imaging, clear lungs, absent symptoms, normal neurologic findings, or no contraindication unless a source supports it.
- When the record has mild or borderline findings, preserve that nuance in the controlled fields instead of upgrading to severe findings or erasing the concern.
- If the template has `absent_*` fields, include only findings documented as absent or directly negated by measurements. Leave merely undocumented findings out unless the prompt/template clearly defines absence as no evidence in the reviewed record.

## JSON Assembly Checklist

- Required top-level keys all present, spelled exactly.
- Enum values copied exactly from the template.
- Lists deduplicated and ordered according to the template.
- Dates and times use the requested ISO-8601 UTC form.
- Numbers use the requested precision and type.
- Null appears only where allowed.
- Patient id comes from the target case or patient record, not from a distractor.
- Evidence ids are stable source identifiers for facts actually used.
- Final response is only the JSON object.
