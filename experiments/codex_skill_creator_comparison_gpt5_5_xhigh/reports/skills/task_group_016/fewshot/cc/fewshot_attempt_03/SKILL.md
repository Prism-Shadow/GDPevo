---
name: synthetic-clinic-json
description: Solve synthetic clinic decision-support tasks that require reading a runtime clinic API, applying case-specific protocol material, and returning only a schema-conformant JSON object. Use for prompts mentioning synthetic clinic cases, TASK_ENV_BASE_URL, answer_template.json, protocol-bound routing or assessment, lab window gates, medication/repletion decisions, red flags, disposition, or evidence identifiers.
---

# Synthetic Clinic JSON

Use this skill for synthetic clinic tasks where the user provides a case id, a runtime API base URL, and an `input/payloads/answer_template.json` schema. The goal is to retrieve only the target case's evidence, apply the applicable protocol, and emit one valid JSON object with no prose.

## Workflow

1. Read the task prompt and `input/payloads/answer_template.json` before querying the runtime. Treat the template as the output contract: required keys, enum values, nullability, numeric precision, ordering notes, and whether extra keys are forbidden.
2. Read the runtime access file for the base URL and allowed endpoints. Use only the listed read-only endpoints unless the task explicitly allows a read-only query endpoint.
3. Extract the target case id from the prompt. Use `scripts/fetch_runtime.py` to collect a filtered bundle:

   ```bash
   python skill/scripts/fetch_runtime.py --base-url "$TASK_ENV_BASE_URL" --case-id "$CASE_ID" --out runtime_case.json
   ```

   If the task uses a different relative path to the skill, adjust the script path. The script uses only Python standard-library modules and read-only GET requests.
4. Inspect `runtime_case.json`, then make any additional allowed GET requests needed for missing protocol details or linked records. Do not place orders, create records, or mutate the runtime.
5. Build a short evidence table for yourself before writing the answer: patient id, encounter/case facts, observations with code/status/effective time/value, imaging, allergies, active medications, problems, registry or social-context data, protocol thresholds, current review time, and source ids.
6. Apply the protocol to the evidence. Prefer explicit protocol criteria over clinical intuition when they differ. Distinguish present findings from absent or unsupported findings.
7. Produce the final response as exactly one JSON object. Do not include markdown fences, comments, or narrative text.

## Reasoning Rules

- Derive identifiers from the runtime, not from examples. Use the prompt/template for constants such as task id and case id when the template requires them.
- Use final observations only when the task asks for final lab results. Exclude preliminary, wrong-code, wrong-patient, or out-of-window observations and report them only in fields meant for excluded ids.
- For time windows, honor inclusive/exclusive boundaries stated in the template or protocol. Sort matched observations by the template's rule, commonly effective time then id.
- For "latest" labs, choose the latest eligible final result by effective time; keep the reported value precision required by the template.
- For medication or replacement plans, screen contraindications and allergies first. Do not recommend a medication that conflicts with documented allergies or protocol contraindications.
- For respiratory, head-injury, care-management, and lab-gate tasks, map findings to the template's controlled enum values. Do not invent synonyms.
- Set safety-check booleans according to the answer's factual support. A `true` safety check means the response avoided the unsupported claim named by that field.
- Populate `evidence_ids` and provenance fields with stable source identifiers that directly support the selected facts. Do not cite ids you did not inspect.

## JSON Assembly Checklist

Before finalizing, verify:

- Every required top-level key is present exactly once.
- No extra top-level keys are present when the template forbids them.
- Enum fields use one of the allowed values exactly as written.
- Lists are de-duplicated and sorted when the template gives an ordering rule.
- Numbers use the requested precision and units are not added unless the field is a string designed to include them.
- `null` appears only in fields where the template permits it.
- ISO timestamps include `Z` when required.
- The output is parseable JSON and nothing else.
