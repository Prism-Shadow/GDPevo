---
name: synthetic-clinic-protocol-json
description: Solve synthetic clinic protocol decision-support tasks that provide a prompt, answer_template.json, environment_access.md, and a read-only clinic runtime API. Use for protocol-bound JSON answers involving cases, patients, observations, imaging, allergies, medications, problems, care-management registry/SDOH data, and clinic protocol materials, including respiratory, head injury, potassium replacement, care-management routing, and lab-window gate tasks.
---

# Synthetic Clinic Protocol JSON

Produce exactly one JSON object that conforms to the task's `input/payloads/answer_template.json`. Derive every case-specific value from the current prompt, template, runtime records, and protocol materials. Do not use memorized constants from examples.

## Workflow

1. Read the task prompt and `input/payloads/answer_template.json`.
   - Extract the target case id, task id, required keys, allowed enum values, required nested keys, nullability, numeric precision, and ordering rules.
   - Treat constants in the current template or prompt as authoritative for the current task only.
2. Read the runtime access file supplied with the task.
   - Use only the listed base URL, credentials, and allowed read-only endpoints.
   - Do not call any judge endpoint. Do not create, update, delete, or place orders.
3. Retrieve the target case and all linked clinical context.
   - Start with `/health`, then `/api/cases/{case_id}` when available.
   - Retrieve the patient record by the case's patient id.
   - Fetch relevant observations, medications, allergies, problems, imaging, care registry, SDOH, and protocol resources. If list endpoints are unfiltered, filter locally by `case_id`, `patient_id`, dates, code, and status.
   - Use `POST /api/query` only as a read-only search helper when the listed GET endpoints do not expose the relationship or protocol text clearly.
4. Read the applicable protocol material before deciding.
   - Prefer explicit protocol thresholds, routing rules, contraindications, and timing instructions over general clinical judgment.
   - When multiple protocol resources exist, use the one matching the task domain, case metadata, target code, or protocol id from the case.
5. Build a source table before drafting JSON.
   - Record the exact source id for each decisive fact: target case, patient, observation, imaging, medication/allergy/problem record, registry/SDOH record, and protocol.
   - Include only evidence ids that directly support the output fields, using the ordering rule from the template.

## Domain Checks

For respiratory assessment tasks:
- Use documented symptoms, vitals, imaging, exam findings, allergies, and protocol criteria to classify the assessment, risk level, disposition, tests, red flags, stabilization, follow-up, return precautions, and medication strategy.
- Make medication choices allergy-aware. If antibiotics are indicated, avoid documented allergen classes and fill medication, dose, route, frequency, and duration only when the protocol supports them.
- Set safety booleans by verifying the answer does not claim unsupported normal imaging, clear lungs, or incompatible medication safety.

For pediatric head injury tasks:
- Separate present red flags from explicitly absent red flags. Do not mark a red flag absent unless the record or protocol context supports absence.
- Classify risk tier, disposition, imaging, restrictions, and follow-up from the head-injury protocol. Keep CT recommendations tied to protocol red flags and severity.
- Set false-claim safety booleans by checking the final answer does not invent loss of consciousness, vomiting, photophobia, or other denied findings.

For potassium replacement tasks:
- Select the latest eligible final serum potassium for the target patient and case context. Exclude wrong patient, wrong code, non-final status, and out-of-scope dates.
- Screen renal function, dialysis dependence, arrhythmia symptoms, medication contraindications, and urgent thresholds before recommending replacement.
- Use protocol dosing, medication code, route, frequency, follow-up lab LOINC, and scheduled time exactly as supported. Use the clinical review time from the case/runtime/protocol, not the system clock, unless the task explicitly instructs otherwise.

For care-management routing tasks:
- Combine case context, registry risk, active problems, recent utilization, medications, labs, blood pressure, dialysis or chronic disease facts, and SDOH disclosures.
- Distinguish chart-derived facts from member-disclosed barriers in provenance fields.
- Select risk tier, program, priority problems, referrals, outreach stance, care-plan minima, and escalation conditions from the care-management protocol.

For lab-window protocol gate tasks:
- Parse the target observation code and time window exactly, including inclusive or exclusive boundary rules from the template or protocol.
- Match only final target-code observations for the target patient inside the window. Track relevant exclusions such as wrong code, preliminary status, out-of-window timing, or wrong patient.
- Sort matched and excluded ids exactly as requested. Set `latest_final` to the most recent matched final observation, or `null` only when the template permits it and no match exists.

## JSON Assembly

- Return no markdown, comments, or prose outside the JSON object.
- Use exactly the required top-level keys and nested keys. Do not add extra keys unless the template explicitly permits them and they are useful.
- Use only allowed enum strings. Prefer empty arrays over null for list fields unless the template says otherwise.
- Respect numeric precision and units. Preserve ISO-8601 timestamps with trailing `Z` when required.
- Deduplicate arrays. Apply the template's ordering rule; if order is semantically irrelevant, use a stable order based on the evidence or protocol sequence.
- Before finalizing, compare the JSON against the template field by field: key presence, value type, enum membership, nullability, precision, ordering, and safety booleans.
