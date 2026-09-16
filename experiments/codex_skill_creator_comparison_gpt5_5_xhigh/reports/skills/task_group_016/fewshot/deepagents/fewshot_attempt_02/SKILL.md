---
name: synthetic-clinic-cds
description: Produce strict JSON clinical decision-support answers for synthetic clinic runtime tasks. Use when a prompt provides a target case id, an answer_template.json schema, and task environment API access for protocol-bound assessments such as respiratory infection, pediatric head injury, potassium replacement, care-management routing, or observation-window lab gates.
---

# Synthetic Clinic CDS

## Workflow

1. Read the task prompt, the runtime access file, and `input/payloads/answer_template.json` before fetching data or drafting an answer.
2. Extract the target `case_id`, the required `task_id`, any requested time window or target code, and every required key, enum, nullability, ordering rule, and precision rule from the template.
3. Fetch the target case from the runtime API, then resolve the patient and gather case-scoped facts from patients, observations, medications, allergies, problems, imaging, care registry, SDOH, and the applicable protocol records. Use [scripts/collect_context.py](scripts/collect_context.py) when a local context bundle is useful:

```bash
python skill/scripts/collect_context.py --base-url "$TASK_ENV_BASE_URL" --case-id "$CASE_ID" > context.json
```

4. Treat the API records and protocol material as authoritative. Do not use training-example constants, memorized thresholds, or unsupported clinical assumptions.
5. Fill exactly the required JSON object. Do not include markdown, comments, narrative text, extra top-level keys, or enum values outside the template.

## Evidence Handling

- Scope every clinical fact to the target `case_id` and resolved `patient_id`; ignore distractor cases and records for other patients.
- Prefer final, dated, code-matching observations for lab decisions. Exclude observations with the wrong patient, wrong code, wrong date window, non-final status, or otherwise disqualifying protocol criteria.
- Follow template ordering instructions exactly. When no order is meaningful, still emit stable, duplicate-free arrays.
- Use the record identifiers that directly support the answer. Include case, observation, imaging, protocol, registry, or social-context IDs when they materially determine the result and the template permits them.
- For absent findings and safety booleans, require explicit support. Do not mark a symptom absent, a contraindication absent, or a safety check true until the relevant record has been checked.

## Clinical Patterns

For respiratory/CAP tasks, combine symptoms, pulse oximetry, imaging, allergies, current medications, and the respiratory protocol. Classify red flags and disposition from protocol criteria; choose tests and medications from the protocol; screen allergies before recommending antibiotics; and avoid claims such as normal imaging or clear lungs unless directly supported.

For pediatric head-injury tasks, distinguish observed symptoms from severe red flags. Use protocol criteria for risk tier, CT/ED routing, home observation, follow-up timing, return-to-learn, activity, sports, and driving restrictions. Do not infer loss of consciousness, vomiting, photophobia, seizure, focal weakness, or worsening headache unless documented.

For potassium replacement tasks, identify the latest eligible final serum potassium for the target patient and case context, then apply the potassium protocol using renal function, dialysis status, arrhythmia symptoms, medications, and contraindications. Use protocol or medication records for dose, route, frequency, medication code, urgent actions, and follow-up lab timing.

For care-management routing tasks, combine registry risk, active problem list, recent utilization, observations, medication count, dialysis or chronic-disease context, and SDOH records. Separate chart-derived facts from member-disclosed or outreach-dependent barriers, and use the protocol for program tier, care-plan minima, referral codes, outreach stance, and escalation conditions.

For observation-window lab tasks, apply the exact requested code and time window. Treat the start as inclusive and the end as exclusive unless the prompt or protocol states otherwise. Sort matching and excluded observations as the template requires, choose `latest_final` from qualified final matches only, and derive the protocol gate and repeat-lab recommendation from the fetched protocol.

## Final Checks

Before returning:

- Parse the response as JSON.
- Compare the top-level keys against the template.
- Confirm every enum, null, number precision, timestamp, and boolean is allowed by the template.
- Recheck that each positive finding, absent finding, safety check, medication recommendation, and evidence ID is supported by retrieved records.
- Return only the JSON object.
