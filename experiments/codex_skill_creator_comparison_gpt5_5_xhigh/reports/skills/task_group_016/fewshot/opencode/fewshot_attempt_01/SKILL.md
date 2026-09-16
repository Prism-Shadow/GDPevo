---
name: clinic-protocol-json
description: Solve synthetic clinic runtime tasks that require a protocol-bound JSON answer from a case id, environment_access.md, and input/payloads/answer_template.json. Use this when the user asks for structured clinical decision support, clinic protocol assessment, observation-window retrieval, care-management routing, medication or lab follow-up decision support, or any task that says to use <TASK_ENV_BASE_URL> and return only JSON conforming to an answer template.
---

# Clinic Protocol JSON

Use this skill for synthetic clinic tasks where the output is a single JSON object scored against `input/payloads/answer_template.json`.

The work is schema-first. Build the answer from the target case, patient-scoped runtime records, and applicable protocol material. Do not rely on clinical intuition when a protocol or template gives controlled values.

## Required Inputs

Read these files before querying the runtime:

1. The task prompt.
2. `input/payloads/answer_template.json`.
3. `environment_access.md`.

Extract the target `case_id`, `task_id`, and any explicit date/window/code constraints from the prompt or template. Treat constants in the template such as `required_value` or `expected_constant` as authoritative.

## Runtime Collection

Use only endpoints allowed in `environment_access.md`. Prefer case-scoped data first:

```bash
python skill/scripts/collect_clinic_context.py --environment-access environment_access.md --case-id CASE-...
```

The script fetches `GET /api/cases/{case_id}` and matching protocol details, then prints one JSON bundle. If the script path differs because the skill is elsewhere, run the same script from that skill directory.

Manual fallback:

1. `GET /api/cases/{case_id}` for the case bundle. This usually includes `case`, `patient`, `findings`, `observations`, `imaging`, `medications`, `allergies`, `problems`, `care_registry`, and `sdoh`.
2. `GET /api/protocols`, then `GET /api/protocols/{protocol_id}` for the protocol whose title/scope matches the case type and answer template.
3. Use broad list endpoints only when the case bundle is missing something. When using broad lists, filter by both `case_id` and `patient_id` unless the template explicitly asks for distractors.

Do not mutate the environment or place orders. Avoid `POST /api/query` unless the environment explicitly provides usable credentials and the task requires it.

## Answer Construction

Create a draft object with exactly the required top-level keys from the template, unless the template explicitly permits extras. Preserve nested required keys and use `null` only when the template permits it.

For enum and list fields:

- Use only allowed values from the template.
- Omit duplicates.
- Treat lists as unordered sets unless the template gives an ordering rule.
- For ordered evidence or observation lists, follow the exact ordering rule in the template.

For evidence:

- Use stable identifiers from records actually used for the decision: case ids, observation ids, imaging ids, protocol ids, registry/source ids, or visit/source ids.
- Do not cite values that were not used.
- Put the case id first only when the template or task wording asks for it.

For safety checks:

- Set booleans based on what the final JSON claims, not on what might be clinically plausible.
- A `no_false_*` or `no_unsupported_*` check should be `true` only when the answer avoids making that unsupported claim.

## Domain Patterns

Use these patterns as reminders, then defer to the fetched protocol and template.

### Respiratory Assessment

- Determine viral URI vs community-acquired pneumonia from symptoms, oxygen saturation, respiratory rate, temperature, and imaging/impression records.
- Escalate disposition only when protocol urgent triggers are met, such as severe hypoxemia, unstable vitals, confusion, respiratory distress, or other protocol red flags.
- Include recommended tests when the protocol and available workup support them.
- Make medication choices allergy-aware. Active allergies can rule out whole medication classes; inactive allergies should not.
- Do not claim a normal chest x-ray or clear lungs unless the record supports it.

### Pediatric Head Injury

- Separate present red flags from explicitly absent red flags. Absence requires evidence from findings or observations, not silence.
- Use GCS, neurologic exam, vomiting count, loss of consciousness, headache course, seizure, focal weakness, basilar skull signs, and photophobia evidence.
- Urgent imaging or ED routing requires protocol urgent triggers; otherwise choose observation/follow-up per protocol.
- Restrictions should reflect symptoms and protocol guidance for cognitive rest, school accommodations, sports, and driving.

### Potassium Replacement

- Use final serum potassium observations with the protocol's serum potassium code. Exclude preliminary, canceled, entered-in-error, whole-blood, or wrong-code observations unless the template asks to list them.
- Pick the latest eligible final serum potassium by `effective_time`.
- Screen urgent branch and contraindications before routine oral replacement: severe renal contraindication, dialysis dependence, arrhythmia symptoms, ECG abnormality, or protocol critical potassium threshold.
- If routine oral repletion applies, calculate dose from the fetched protocol's target and dose rule; use the medication code/order details supplied by the protocol.
- Schedule follow-up lab timing from the protocol and case clock, not from the current system date.

### Care Management Routing

- Use registry fields, active problems, observations, medication count, recent admissions, and SDOH/member disclosures together.
- Choose risk tier and program from protocol thresholds and supporting triggers.
- Priority problem codes should be backed by active diagnoses, registry facts, observations, or member disclosures.
- Keep `source_provenance.chart_facts` separate from `member_disclosure_needed`: chart/registry/lab/vital facts are not the same as member-reported barriers or preferences.
- Permission-based outreach applies when the record says the member is reluctant, refusing, or wants contact handled on their terms.

### Observation Window Tasks

- Derive `window.from`, `window.to`, and `target_code` from the prompt, case findings, or protocol. Treat start as inclusive and end as exclusive unless the template says otherwise.
- A matched observation must belong to the target patient, use the target code, have an eligible status, and fall inside the window.
- Sort matched observations exactly as instructed, commonly by `effective_time` ascending and then observation id.
- `latest_final` is the latest matched final target-code observation, or `null` if no match exists.
- For excluded observations, include only distractors the template asks for. If the stated exclusion reasons are date, code, or status, do not add wrong-patient observations unless patient mismatch is explicitly named as an exclusion reason.

## Validation

Before finalizing, save or pipe the JSON into a local file and run:

```bash
python skill/scripts/check_answer_against_template.py input/payloads/answer_template.json answer.json
```

Fix all errors and review warnings. Then parse the final answer as strict JSON one more time. The final response must contain only the JSON object, with no markdown fence or narrative text.
