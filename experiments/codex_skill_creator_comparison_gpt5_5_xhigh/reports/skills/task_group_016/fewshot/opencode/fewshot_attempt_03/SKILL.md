---
name: synthetic-clinic-protocol-json
description: Solve synthetic clinic runtime tasks that ask for a protocol-bound clinical, care-management, observation-window, medication, imaging, or safety decision as one schema-exact JSON object. Use when a prompt provides a clinic task environment URL plus an answer_template.json and asks Codex to retrieve patient/case data, apply clinic protocol material, cite evidence identifiers, and return only controlled JSON.
---

# Synthetic Clinic Protocol JSON

Use this skill for read-only synthetic clinic tasks where the answer must be a single JSON object matching a provided `input/payloads/answer_template.json`.

## Core Workflow

1. Read the user prompt and `input/payloads/answer_template.json` before fetching data.
   Extract the `task_id`, target `case_id`, required top-level keys, enum values, nullable fields, numeric precision, ordering rules, and safety-check booleans from the template.

2. Read the task's environment access note for the base URL and allowed endpoints.
   Use only read-only access. Do not mutate the runtime or place orders. `POST /api/query` may be used only as a read-only query mechanism if the task environment exposes it for retrieval.

3. Fetch the target case, patient, and all relevant clinical collections.
   Start with the case record, then gather patient details, observations, medications, allergies, problems, imaging, care registry, social-context data, and protocols as relevant to the task domain. The helper [scripts/fetch_clinic_bundle.py](scripts/fetch_clinic_bundle.py) can fetch the standard GET endpoints into local JSON files.

4. Build a short evidence ledger before drafting the answer.
   Record each fact with its source identifier: case id, encounter id, observation id, imaging id, medication id, allergy id, registry id, protocol id, or other stable source id. Prefer source ids from the runtime over prose labels.

5. Select and apply the applicable protocol from the runtime.
   Match by case domain, requested decision, condition, lab code, medication type, or protocol id mentioned in the case. Use protocol thresholds and action rules from the runtime rather than general medical memory.

6. Fill the template exactly.
   Use only required top-level keys unless the template explicitly allows extras. Use enum strings exactly as written. Use `null` only where allowed. Use the requested numeric precision and ISO timestamp format. Return only JSON, with no markdown or explanatory prose.

7. Validate before final response.
   Check JSON syntax, required keys, enum membership, nullability, evidence ids, safety booleans, and ordering rules. The helper [scripts/check_json_answer.py](scripts/check_json_answer.py) performs a structural pass against common template shapes; still manually verify clinical logic and task-specific ordering.

Useful command pattern:

```bash
python3 skill/scripts/fetch_clinic_bundle.py --base-url "$TASK_ENV_BASE_URL" --case-id "$CASE_ID" --out-dir /tmp/clinic_bundle
python3 skill/scripts/check_json_answer.py input/payloads/answer_template.json /tmp/draft_answer.json
```

## Retrieval Pattern

Use the base URL from the task environment note. Typical endpoints are:

- `/api/cases` and `/api/cases/{case_id}` for the target case and patient linkage
- `/api/patients` and `/api/patients/{patient_id}` for demographics/context
- `/api/observations` for vitals, labs, neurologic findings, symptom observations, and renal function
- `/api/medications`, `/api/allergies`, and `/api/problems` for treatment eligibility and contraindication checks
- `/api/imaging` for radiology evidence and imaging recommendations
- `/api/care-registry` and `/api/sdoh` for care-management routing and member-disclosed barriers
- `/api/protocols` and `/api/protocols/{protocol_id}` for decision thresholds, red-flag definitions, follow-up timing, and controlled action rules

If a collection includes multiple cases or patients, filter by the target case, inferred patient id, related encounter ids, and source references. Keep relevant distractors visible until the answer is complete; some tasks ask for excluded observation ids or absent red flags.

## Domain Checks

Use these checks when the template/domain calls for them:

- Respiratory protocol: distinguish pneumonia-like assessment, viral/supportive pathway, and ED transfer from protocol criteria. Screen hypoxemia, respiratory distress, chest pain, fever course, imaging, allergies, and medication contraindications. Do not claim normal imaging or clear lungs unless the runtime supports it.
- Pediatric head injury: separate present red flags from explicitly absent red flags. Loss of consciousness, repeated vomiting, seizure, focal weakness, worsening headache, skull signs, photophobia, and coordination symptoms must come from documented evidence, not assumption. Activity, school, sports, and driving restrictions should follow the protocol tier.
- Potassium replacement: identify the latest eligible final serum potassium result, renal function, dialysis status, arrhythmia symptoms, urgent thresholds, oral dose rules, medication code, and follow-up lab timing from the protocol. Preliminary, wrong-code, wrong-patient, or out-of-window observations do not qualify.
- Lab-window gate: apply the requested inclusive/exclusive time window, code, status, and patient filters exactly. Sort matched and excluded observations as the template specifies, and derive the latest final only from qualifying matches.
- Care management: separate chart facts from member-disclosed needs. Use numeric anchors exactly from the runtime. Route program eligibility, priority problems, referrals, outreach stance, care-plan minima, and escalation conditions through the care-management protocol.

For `current_time`, follow-up timestamps, and scheduled lab times, use the case/protocol/runtime clinical time anchors. Do not use the system clock unless the prompt or runtime protocol explicitly defines that as the review time source.

## Evidence And Safety

Evidence identifiers should be stable ids from the runtime and should support the decisive fields in the answer. Include the target case id when the template expects case provenance; include observation or imaging ids for measured findings; include protocol ids when useful and allowed by the evidence field description.

Safety-check booleans usually mean "the answer did not make this unsupported or contraindicated claim." Set them only after checking the relevant source data. For example, an allergy safety check requires confirming the medication plan avoids documented allergens; a false-finding safety check requires confirming the answer did not assert an undocumented symptom, normal image, or negative finding.

## Common Failure Modes

- Do not copy values from previous examples or infer identifiers from naming patterns.
- Do not use general clinical defaults when the protocol or case gives a controlled enum pathway.
- Do not treat "not mentioned" as absent unless the case or protocol material explicitly documents absence or the template asks for absent findings supported by negative documentation.
- Do not include raw narrative, comments, citations outside fields, extra keys, or markdown fences.
- Do not let helper-script output become the answer; the final JSON must be reasoned from the runtime facts, protocol, and template.
