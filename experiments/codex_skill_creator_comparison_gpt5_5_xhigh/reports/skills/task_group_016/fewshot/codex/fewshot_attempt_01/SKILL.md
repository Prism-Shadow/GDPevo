---
name: clinic-protocol-json
description: Produce schema-constrained JSON answers for synthetic clinic runtime tasks that require reviewing case records, observations, medications, allergies, imaging, care-registry, SDOH, and protocol materials from allowed clinic API endpoints. Use for protocol-bound clinical decision-support, observation-window retrieval, lab replacement, respiratory, head-injury, and care-management routing tasks that provide an answer_template.json and TASK_ENV_BASE_URL-style access.
---

# Clinic Protocol JSON

## Core Workflow

1. Read the user prompt and `input/payloads/answer_template.json` completely before calling the runtime. Treat the template as the output contract: required keys, enum values, nullability, precision, sorting, constants, and "no extra keys" rules override prose habits.
2. Extract the `task_id`, target `case_id`, runtime base URL, and any explicit window, target code, protocol scope, or endpoint limits from the prompt and environment access file.
3. Retrieve the target case first:

```bash
python scripts/collect_clinic_context.py --base-url "$TASK_ENV_BASE_URL" --case-id "$CASE_ID" --out /tmp/clinic_context.json
```

Use the generated context as source material, not as an answer. If the case bundle already contains patient, findings, observations, medications, allergies, problems, imaging, registry, or SDOH sections, prefer those over broad collection scans. Use collection endpoints only to fill missing pieces or verify distractors.

4. Retrieve protocol material from `/api/protocols` and `/api/protocols/{protocol_id}`. Match protocol relevance by case type, prompt wording, protocol title/scope, and source IDs in findings. The live protocol is authoritative for thresholds, target codes, urgency branches, medication rules, follow-up timing, and controlled terminology.
5. Build a short evidence table before drafting JSON: field to fill, candidate value, source record ID, protocol rule, and uncertainty. Resolve uncertainty by rereading the source record or protocol; do not fill fields from general medical memory when the environment is silent.
6. Draft only the JSON object. Validate it against the template before final output:

```bash
python scripts/check_answer_shape.py input/payloads/answer_template.json /tmp/answer.json
```

## Runtime Retrieval Rules

- Use only read-only allowed endpoints unless the task explicitly permits otherwise. These tasks are decision-support tasks; do not mutate records or place orders.
- Prefer `GET /api/cases/{case_id}` because it may return an aggregated case bundle with `case`, `patient`, `findings`, `observations`, `medications`, `allergies`, `problems`, `imaging`, `care_registry`, and `sdoh`.
- Keep patient identity strict. A record with the target case ID but a different `patient_id` is not patient evidence. Include wrong-patient records in an excluded list only when the template or prompt explicitly asks for wrong-patient distractors.
- Treat `status: "final"` as authoritative for labs, imaging, and exams unless the protocol names other statuses. Preliminary, canceled, and entered-in-error records usually do not satisfy protocol gates.
- Preserve source IDs. `evidence_ids` should contain stable case, observation, imaging, registry, encounter, or protocol identifiers that directly support scored conclusions. Do not cite records that were merely present but unused.

## Template-Filling Rules

- Constants in the template or prompt must be copied exactly for `task_id`, `case_id`, target codes, and fixed windows.
- Use enum labels exactly as written in the template. Map clinical facts to those labels only when there is direct support from case findings, observations, protocols, or active records.
- Use `null` only where the template permits it. Use empty arrays for optional action lists when no action is indicated and the template allows a list.
- Round numeric fields to the precision requested by the template. Keep ISO timestamps in UTC with a trailing `Z` when requested.
- For unordered sets, omit duplicates and choose a stable order: case-level identifiers first for evidence, clinical sequence for actions, and otherwise template or source order.
- For sorted observation lists, obey the template sort rule exactly. Common observation-window tasks sort by `effective_time` ascending, then observation ID ascending.
- Safety-check booleans usually mean "the answer does not make this unsupported claim." Set them true only after confirming the JSON avoids that false claim.

## Clinical Mapping Patterns

- **Observation windows:** Filter by target patient, target code, status, and inclusive start/exclusive end timestamps. `latest_final` is the qualifying final observation with the greatest `effective_time`. Excluded IDs are relevant distractors that fail date, code, or status rules according to the prompt/template.
- **Potassium replacement:** Use final serum potassium observations for status; ignore preliminary values and non-serum potassium codes unless explicitly requested. Apply the live protocol's urgent branch first. If urgent criteria are false, compute routine oral dose from the protocol target and dose rule, then schedule follow-up from the protocol wording and case clock.
- **Respiratory/CAP:** Combine symptoms, oxygen saturation, respiratory rate, blood pressure, viral testing, and chest imaging. Escalate only when protocol urgent triggers are present. Use active allergies to avoid medication classes; inactive allergies do not constrain the plan. Do not claim a normal chest image or clear lungs unless the source says so.
- **Pediatric head injury:** Separate present red flags from explicitly absent red flags. Mild symptoms with normal or near-normal neurologic status usually route differently from protocol urgent triggers such as repeated vomiting, seizure, focal deficit, low GCS, skull signs, or prolonged loss of consciousness. Activity, school, sport, and driving restrictions should follow the protocol and symptom status.
- **Care-management routing:** Combine registry risk, active problems, recent utilization, medication count, observations, and member-disclosed SDOH. Keep provenance split between chart facts and member disclosures. Referral codes should be justified by protocol triggers, not by diagnosis names alone.

## Final Output

Return exactly one JSON object and no markdown, comments, or explanatory prose. Before finalizing, compare every populated value to: the template, the case bundle, the selected protocol, and the safety checks.
