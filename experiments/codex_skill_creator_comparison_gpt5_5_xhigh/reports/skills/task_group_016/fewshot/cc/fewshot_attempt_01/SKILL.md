---
name: synthetic-clinic-protocol-json
description: Use this skill whenever a task asks for a structured JSON clinical decision-support, protocol assessment, care-management routing, potassium/lab gate, respiratory, or pediatric head-injury response from the synthetic clinic runtime environment. It is especially relevant when the prompt mentions Harborview Synthetic Clinic, a CASE-* id, input/payloads/answer_template.json, environment_access.md, or a requirement to return only one JSON object.
---

# Synthetic Clinic Protocol JSON

Use this skill to produce protocol-bound JSON from the synthetic clinic runtime. The core task is not free-text medical advice: it is structured extraction, protocol application, and template-conformant serialization.

## Workflow

1. Read the user prompt, `environment_access.md`, and `input/payloads/answer_template.json`.
2. Extract the target `case_id`, the required `task_id` if one is stated or encoded in the template, and the runtime `base_url`.
3. Use only endpoints allowed by `environment_access.md`. Fetch `GET /api/cases/{case_id}` first; it normally bundles the case, patient, findings, observations, imaging, allergies, medications, problems, care registry, and SDOH facts needed for scoring.
4. Fetch `/api/protocols`, select the protocol matching the case type or prompt theme, then fetch `/api/protocols/{protocol_id}`. Apply protocol thresholds and status rules before filling template fields.
5. Build the answer by the template, not by prose intuition. Preserve exactly the required top-level keys, enum spellings, nullability, and numeric precision. Do not add extra top-level keys unless the template explicitly permits them.
6. Return only a JSON object. Do not include markdown, explanations, citations outside `evidence_ids`, or comments.

For detailed field mapping, read [clinical_runtime_protocols.md](references/clinical_runtime_protocols.md). For a deterministic first draft, you may run:

```bash
python skill/scripts/clinic_protocol_helper.py \
  --base-url "$TASK_ENV_BASE_URL" \
  --case-id "$CASE_ID" \
  --template input/payloads/answer_template.json \
  --task-id "$TASK_ID"
```

Always inspect and correct the helper output against the prompt, template, fetched case record, and protocol. The helper is a draft generator, not a substitute for final verification.

## Rules That Prevent Common Failures

- Treat observations as usable only when `status` is `final`, unless the template asks you to list excluded or distractor observations.
- Keep the target patient isolated. Ignore wrong-patient records when deciding a match; include them in excluded lists only if the prompt explicitly asks for cross-patient distractors.
- Use the protocol's controlled codes. For serum potassium, `code="K"` is serum/plasma potassium; a whole-blood potassium code is not the same target.
- Do not infer absent symptoms from silence. Put a condition in an `absent_*` field only when the record explicitly says it is absent or a numeric observation proves absence.
- Active allergies matter; inactive allergies do not. Convert allergy names to the enum class required by the template.
- Evidence identifiers should be stable source ids for the actual facts used. Prefer case ids, observation ids, imaging ids, protocol ids, registry ids, or source ids from findings.
- Safety-check booleans mean your output avoids unsupported claims, not that the patient has no risk. Set them true only after checking you did not invent the prohibited finding.

## Final Verification

Before answering, check:

- The JSON parses.
- The top-level key set matches the template.
- Every enum value is copied exactly from the template.
- Required nulls are `null`, not empty strings.
- Lists are deduplicated. When the template gives ordering rules, follow them; otherwise use stable clinical order.
- The final response contains no narrative text outside the JSON object.
