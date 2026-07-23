---
name: synthetic-clinic-protocol-cds
description: Produce a single schema-conformant JSON clinical decision-support response for a synthetic clinic runtime task. Use when a task points at a target clinic case ID, supplies an answer_template.json schema, and instructs you to query a clinic runtime environment and return only JSON.
---

# Synthetic Clinic Protocol Decision-Support Skill

This skill generates one structured clinical decision-support (CDS) JSON object per task for the Harborview / synthetic clinic runtime. It is task-agnostic: it reads the task's own prompt and `answer_template.json` to decide what to produce, and reads `environment_access.md` to decide how to reach the runtime. It never hard-codes a task's final values.

## Inputs each task provides

Every task is staged under `train_tasks/<task>/input/` (or an equivalent task directory) with:

1. `prompt.txt` — names the target `case_id`, states what clinical question to answer, and points to `<TASK_ENV_BASE_URL>`.
2. `payloads/answer_template.json` — the JSON schema / contract the answer must satisfy (required keys, enums, ordering rules, null rules, numeric precision, output rules).
3. `environment_access.md` (listed separately) — the runtime base URL, allowed endpoints, and any auth headers for THIS run. Endpoints and tokens can change per run, so always read it fresh; never assume.

## Operating procedure

Work the steps in order. Do not skip the template read — the template is the contract, not the prose of the prompt.

### 1. Read the contract first
Read `prompt.txt` and `payloads/answer_template.json` in full before any network call. Extract:
- target `case_id` (and `task_id` if the template fixes it, e.g. `train_004`).
- the full list of `required_top_level_keys`.
- every field's type, `allowed_values` / enum, `required_value` / `expected_constant`, `required_keys` for nested objects, ordering rules, null permissions, and numeric precision.
- the `output_rules` / `output_rule` (almost always: return exactly one JSON object, no markdown, no comments, no prose, no extra top-level keys).

### 2. Read the runtime access
Read `environment_access.md` for THIS run only. Note base URL, the allow-list of endpoints, and the header needed for any authenticated endpoint (e.g. `POST /api/query` requires `X-Clinic-Token: synclinic-readonly`). Use only the endpoints listed; do not invent or reuse endpoints from a prior run.

### 3. Resolve the case → patient
Fetch the target case. `GET /api/cases/{case_id}` returns the case record; from it derive the stable `patient_id`. Carry `case_id` and `patient_id` into the answer verbatim (exact strings from the runtime, not paraphrased).

### 4. Gather evidence across allowed endpoints
Pull the clinical facts the template's fields imply. Typical sources, mapped to the common field families:
- `GET /api/patients/{patient_id}` — demographics, baseline context.
- `GET /api/observations` — labs, vitals (potassium, SpO₂, etc.); filter by patient, code, status, and time window.
- `GET /api/medications` — active meds, NDC, dose/route/frequency, allergy conflicts.
- `GET /api/allergies` — allergens to avoid (drives `avoid_allergens` and safety checks).
- `GET /api/problems` — problem codes for care-management routing.
- `GET /api/imaging` — CXR / CT findings (never claim "normal" or "clear lungs" without a supporting imaging result).
- `GET /api/care-registry` — registry / risk-score anchors.
- `GET /api/sdoh` — social determinants (transport, finance, food, dialysis fatigue).
- `GET /api/protocols` and `GET /api/protocols/{protocol_id}` — the protocol logic that gates disposition, imaging, repletion, escalation, and follow-up timing.
- `POST /api/query` (with the run's token header) — filtered/joined queries when a plain GET list is too broad.

Prefer the targeted `{id}` and filtered `POST /api/query` forms over dumping full collections. Record the identifier of every resource you rely on for `evidence_ids`.

### 5. Do not mutate state
This skill is read-only decision support. Never POST an order, never write back, never "place" a medication or lab. Recommendations go only into the JSON answer as `recommended` / `not_recommended` / `defer_to_urgent_clinician` statuses.

### 6. Apply protocol logic to fill clinical fields
Map evidence → template fields using the protocol material, not free-text clinical guessing:
- Assessment / risk tier / disposition / imaging recommendation: from protocol thresholds (e.g. SpO₂ bands, PECARN-style head-injury criteria, potassium repletion thresholds, care-management risk-score cut-offs).
- Red flags vs absent red flags: list flags the evidence supports; where the template asks, also list the specific absent flags. Never assert a flag that the record does not support.
- Medication / order plan: choose the enum strategy, then fill medication/dose/route/frequency/duration only when the plan actually prescribes; use `null` where the spec permits and no value applies. Honor allergies (`avoid_allergens`) and contraindications.
- Follow-up: `timeframe_hours` is a whole-hour integer drawn from protocol; `route` from the allowed enum.
- Safety checks: set each boolean truthfully from the evidence — these exist to catch fabricated findings (e.g. `no_penicillin_or_sulfa`, `no_normal_cxr_claim`, `no_false_loc`, `no_false_vomiting`, `no_false_photophobia`).

### 7. Observation-window tasks (when the template asks for matched/excluded labs)
When the template has `window`, `matched_observation_ids`, `excluded_observation_ids`, `latest_final`:
- Define the inclusive `from` / exclusive `to` window from the case context (the prompt usually names a month, e.g. "March 2026 window").
- A lab qualifies as matched only if it belongs to the target patient, has the target code (e.g. `K`), is `final` status, and falls inside the window.
- Anything relevant but disqualified by date, code, or status goes in `excluded_observation_ids`.
- Sort both lists exactly as the template specifies (typically `effective_time` ascending, then `observation_id` ascending).
- `latest_final` is required when `lab_found` is true; null/absent otherwise. `protocol_gate` follows from the latest final's value band.

### 8. Conform to the schema exactly
Before returning, validate the draft against the template as if you were the evaluator:
- Exactly the `required_top_level_keys`, no extras (unless the template explicitly says extras are ignored — even then, don't rely on it).
- Every enum value is one of the listed `allowed_values`; every `required_value` / `expected_constant` matches verbatim.
- Lists obey their ordering rule (set-normalized, stable order, case-id-first, or descending-relevance — varies per template; follow that template's rule, not a default).
- Nulls appear only where the spec permits (`string_or_null`, `integer_or_null`, nullable sub-objects).
- Numeric fields use the specified precision (one decimal place for mmol/L / HbA1c / phosphorus; two decimals for a probability risk score; whole hours/days/counts).
- `safety_checks` booleans are all present and true-to-evidence.

### 9. Emit
Return only the single JSON object. No markdown fences, no commentary, no trailing prose. If the template says "do not include narrative text outside the JSON object," that is literal.

## Hard rules (do not violate)

- **Read the template before querying.** The template is the contract; the prompt prose is context.
- **Use only this run's `environment_access.md`.** Endpoints and the clinic token are per-run.
- **Read-only.** No orders, no writes, no state mutation.
- **Exact identifiers.** `case_id`, `patient_id`, observation/medication/protocol ids come verbatim from the runtime.
- **No fabricated findings.** Every clinical claim and every safety-check boolean must trace to a fetched resource; if absent, mark absent / set the safety check accordingly.
- **Schema-faithful output.** One JSON object, required keys only, enums and ordering honored, precision correct.
- **No task-specific final values in the skill.** The skill carries the procedure, never a specific case's answer.

## Supporting references

- `references/runtime_endpoints.md` — endpoint inventory, request patterns, and the auth-header rule, distilled from `environment_access.md`.
- `references/schema_conformance_checklist.md` — field-by-field checklist for producing a template-conformant object.
- `references/field_families.md` — how the recurring field families (identifiers, risk/disposition, red flags, medication plan, follow-up, evidence_ids, safety_checks, provenance) are sourced and filled across task types.
