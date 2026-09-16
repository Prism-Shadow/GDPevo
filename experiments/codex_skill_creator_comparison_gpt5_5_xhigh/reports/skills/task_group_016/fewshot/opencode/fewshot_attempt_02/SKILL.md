---
name: synthetic-clinic-protocol-json
description: Use this skill whenever a task asks for a protocol-bound JSON clinical decision-support answer from a synthetic clinic runtime, a target case id, environment_access.md, and input/payloads/answer_template.json. It helps retrieve the case/protocol evidence, apply clinic-specific rules instead of outside medical knowledge, preserve source identifiers, avoid unsupported clinical claims, and return schema-only JSON.
---

# Synthetic Clinic Protocol JSON

Use this skill for synthetic clinic tasks where the answer must be one JSON object that conforms to a provided `answer_template.json`. The key risk is not general medical reasoning; it is missing a clinic-specific protocol detail, using a preliminary or wrong-patient record, or drifting from the exact schema.

## Required Inputs

Read these before deciding:

- The user prompt, especially the target case id and the requested clinical domain.
- `environment_access.md` for the base URL and allowed endpoints.
- `input/payloads/answer_template.json` for required keys, enum values, nullability, ordering, constants, and numeric precision.
- The runtime case record and the applicable protocol material.

Do not use memorized example outcomes. Solve from the current runtime data and the current template.

## Workflow

1. Parse the template first. Write down the required top-level keys, nested required keys, allowed enum values, fields that permit `null`, ordering rules, and any required constants.
2. Fetch the target case bundle. Prefer `GET /api/cases/{case_id}` because the clinic runtime may return a case-scoped bundle with patient, findings, observations, medications, allergies, problems, imaging, registry, and SDOH records.
3. Fetch protocol material. Use `GET /api/protocols` to identify candidate protocols by case type, prompt language, title, scope, and controlled codes. Fetch the selected details with `GET /api/protocols/{protocol_id}`.
4. Build an evidence table before filling JSON. For each candidate fact, track the value, source id, status, effective time, patient id, case id, and whether it supports an included or excluded output field.
5. Apply protocol rules only to eligible evidence. Final/authoritative statuses matter; wrong-patient, wrong-code, out-of-window, preliminary, canceled, or entered-in-error observations usually become exclusions or are ignored depending on the template.
6. Fill the template with controlled values, not prose. Use only enum values from the template. Preserve boolean safety checks as claims about the output, not as extra clinical findings.
7. Validate the final JSON locally before responding. Return only the JSON object, with no markdown fence or narrative text.

## Helpful Scripts

If this skill package is available on disk, use these optional helpers:

- `scripts/fetch_case_bundle.py`: fetches a case bundle and protocol records into one JSON file.
- `scripts/validate_answer_shape.py`: checks a draft answer against the local template for required keys, constants, basic types, enum values, and unexpected keys.

Example use from the skill directory:

```bash
python scripts/fetch_case_bundle.py --env /path/to/environment_access.md --case-id CASE-ID --out /tmp/case_bundle.json
python scripts/validate_answer_shape.py --template /path/to/input/payloads/answer_template.json --answer /tmp/answer.json
```

If script paths are inconvenient, manually follow the same workflow with `curl` or another HTTP client.

## Clinical Protocol Heuristics

Read [references/protocol-workflow.md](references/protocol-workflow.md) when the task involves:

- Respiratory infection or pneumonia disposition.
- Pediatric head injury or concussion triage.
- Potassium replacement, urgent escalation, or follow-up lab scheduling.
- Care-management routing from registry, problem, medication, and SDOH evidence.
- Observation-window matching and protocol gates.

## Output Discipline

- Use the case id and patient id from the runtime record, not from assumptions.
- Include evidence identifiers that directly support the decision; prefer stable case, observation, imaging, registry, or protocol-related source ids requested by the template.
- For set-like arrays, include each selected code once. For ordered arrays, follow the template ordering rule.
- Use numbers at the precision requested by the template.
- Use `null` only when the template permits it.
- Do not add top-level keys unless the template explicitly permits additional properties.
- Do not mention absent red flags unless the runtime record or protocol evidence supports their absence.
- Do not claim normal imaging, clear lungs, no vomiting, no loss of consciousness, no photophobia, or similar negatives unless those facts are explicitly documented.
