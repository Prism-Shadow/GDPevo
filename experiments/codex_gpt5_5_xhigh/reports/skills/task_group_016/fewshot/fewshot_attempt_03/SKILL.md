---
name: synthetic-clinic-protocol-json
description: Produce protocol-bound structured JSON answers for synthetic clinic decision-support tasks. Use when a task provides a clinic runtime base URL, a target case identifier, and an answer_template.json requiring fields such as assessment, disposition, labs, medications, care-management routing, observation-window gates, evidence IDs, and safety checks.
---

# Synthetic Clinic Protocol JSON

## Core Workflow

1. Read the task prompt and `input/payloads/answer_template.json` before calling the runtime.
2. Extract the target `case_id`, `task_id`, required keys, exact enum values, nullability, ordering rules, numeric precision, and any required constants from the template.
3. Read the runtime access file for the base URL and allowed endpoints. Use only that base URL for network calls.
4. Fetch the target case first:
   - `GET /api/cases/{case_id}` when available.
   - Otherwise `GET /api/cases` and filter exactly by `case_id`.
5. Use the case's `patient_id` as the primary join key. Fetch the patient and all relevant clinical collections:
   - patients, observations, medications, allergies, problems, imaging, care registry, SDOH, and protocols.
6. Filter runtime data strictly to the target patient and target case. Treat records for other patients or other cases as distractors unless a protocol explicitly says otherwise.
7. Select the applicable protocol from the prompt and case type, then fetch its detail. Common protocol families include adult respiratory infection/CAP, pediatric head injury, potassium replacement, observation-window interpretation, and care-management routing.
8. Derive every output field from the runtime record plus the protocol. Do not reuse values from training examples or infer unsupported findings.
9. Return exactly one JSON object matching the template. Do not include markdown, comments, explanatory prose, or extra top-level keys.

## Evidence Handling

- Prefer stable source identifiers from the records that directly support the scored decisions.
- Include the case identifier only when the template or ordering guidance supports it.
- For observations, cite the exact observation identifiers used for abnormal values, latest-final decisions, neuro checks, oxygen saturation, imaging, or renal function.
- For care-management summaries, separate chart-derived facts from member-disclosed barriers when the template asks for provenance grouping.
- Do not cite records that were reviewed but excluded unless the template has an explicit excluded-observation or provenance field.

## Template Fidelity

- Copy required constants from the prompt/template, not from prior examples.
- Use enum strings exactly as listed in the active template.
- Use `null` only where the active template permits it.
- Preserve required object shapes even when a recommendation is not made.
- Deduplicate set-like arrays. Apply the template's ordering rule when one is stated; otherwise use a stable clinically sensible order.
- Match numeric precision exactly: integer hours/days, one decimal place, two decimal places, or ISO-8601 UTC timestamps as requested.
- Set safety-check booleans to reflect that unsupported claims were avoided. Example: a "no false vomiting" check is true only if the answer does not assert vomiting without evidence.

## Runtime Retrieval Pattern

Use direct endpoint retrieval and local filtering as the default. A typical pass is:

```text
GET /api/cases/{case_id}
GET /api/patients/{patient_id}
GET /api/observations
GET /api/medications
GET /api/allergies
GET /api/problems
GET /api/imaging
GET /api/care-registry
GET /api/sdoh
GET /api/protocols
GET /api/protocols/{protocol_id}
```

If `POST /api/query` is available, use it only as a secondary aid for locating facts. Verify query output against source records before using it in the final JSON.

## Domain Checks

### Adult Respiratory / CAP

- Reconcile symptoms, vital signs, oxygen saturation, lung exam, imaging, allergies, medications, and respiratory protocol criteria.
- Distinguish viral upper respiratory illness from community-acquired pneumonia using focal findings, consolidation, fever, sputum, and protocol thresholds.
- Treat hypoxemia, respiratory distress, confusion, hemoptysis, pleuritic chest pain, persistent fever, and worsening dyspnea according to the active protocol.
- Choose outpatient follow-up versus emergency transfer from protocol severity criteria.
- Build an allergy-aware medication plan. Avoid any allergen classes documented for the patient; do not recommend beta-lactams, sulfonamides, macrolides, or tetracyclines when contraindicated.
- Do not claim a normal chest x-ray or clear lungs unless the corresponding source record explicitly supports it.

### Pediatric Head Injury

- Reconcile mechanism, GCS, neuro exam, symptoms, vomiting count, loss of consciousness, seizure, focal weakness, worsening headache, basilar skull signs, photophobia, and coordination symptoms.
- Classify risk and imaging from the active pediatric head-injury protocol. Do not overcall CT when protocol supports observation, and do not undercall ED/CT escalation when high-risk findings are present.
- Put present findings in red flags and explicitly denied high-risk findings in absent red flags only when the record supports absence.
- Apply activity, return-to-learn, sports, and driving restrictions from the protocol.
- Safety checks should prevent unsupported assertions of loss of consciousness, vomiting, or photophobia.

### Potassium Replacement

- Identify the latest eligible final serum potassium for the target patient/case. Exclude preliminary, wrong-code, wrong-patient, wrong-window, and superseded observations.
- Screen contraindications and escalation factors, especially dialysis dependence, severe renal impairment, arrhythmia symptoms, and critical potassium thresholds.
- Select no replacement, routine oral replacement, urgent escalation, or hold-for-contraindication from the protocol.
- When replacement is recommended, populate order-ready medication fields from the active protocol or runtime medication reference. When not recommended, preserve the object shape with permitted nulls/status values.
- Schedule follow-up labs from protocol timing and the clinical review time, using the requested timestamp precision.
- Order urgent action arrays by clinical sequence when escalation is needed.

### Observation Window Gate

- Derive the inclusive start and exclusive end of the target window from the prompt, template, case context, or protocol.
- Filter observations by patient, target code, final status, and window boundaries.
- Sort matching observations by effective time ascending, then identifier ascending.
- Put relevant distractors in the excluded list only when the template asks for them; include wrong date, wrong code, preliminary status, or other explicitly relevant exclusions.
- Set `latest_final` from the latest qualifying final observation when found; otherwise use the template's nullable form.
- Map the final result to the protocol gate and repeat-lab recommendation from the active protocol.

### Care Management Routing

- Combine case summary, registry risk, problems, observations, medication count, recent admissions, dialysis context, and SDOH facts.
- Route program and risk tier using the care-management protocol, not summary text alone.
- Populate priority problems from documented clinical and social needs. Avoid including barriers that are not documented or disclosed.
- Use numeric anchors exactly from source records, rounded only as the template requires.
- Select referrals, outreach stance, care-plan minimums, and escalation conditions from protocol criteria.
- Keep member-disclosed barriers separate from chart facts when source provenance is requested.

## Final Validation

Before finalizing:

1. Compare top-level keys against the template.
2. Validate every enum value against the active template.
3. Recheck patient and case joins to exclude distractors.
4. Recheck date windows, final/preliminary status, and latest-observation selection.
5. Confirm medication recommendations do not conflict with allergies or contraindications.
6. Confirm evidence IDs actually support the selected findings.
7. Confirm the response is parseable JSON and contains no prose outside the object.
