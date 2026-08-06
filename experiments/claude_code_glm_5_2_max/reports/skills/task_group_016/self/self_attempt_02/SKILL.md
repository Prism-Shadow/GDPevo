---
name: clinic-runtime-cds
description: Solve synthetic clinic decision-support tasks that run against a read-only clinic runtime API and require a single JSON object conforming to a per-task answer template. Use for any task whose prompt names a CASE-* id, references a clinic runtime environment / <TASK_ENV_BASE_URL>, and asks to return a JSON object matching input/payloads/answer_template.json.
---

# Clinic Runtime Decision-Support Skill

This skill solves a family of structured clinical decision-support (CDS) tasks. Each task points at a target clinic case in a read-only synthetic clinic runtime and demands **exactly one JSON object** that conforms to a per-task `answer_template.json`. The work is: locate the target case in the runtime, gather the relevant chart facts and protocol material, map them onto the template's controlled vocabulary, and emit a schema-valid object.

## When to use

Use this skill when a task has all of:
- A target case identifier (e.g. `CASE-RESP-102`, `CASE-CM-411`) stated in the prompt.
- A reference to a clinic runtime environment / `<TASK_ENV_BASE_URL>`.
- An instruction to return a single JSON object conforming to `input/payloads/answer_template.json`.

Do **not** use this skill for tasks that ask for narrative, free-text, or non-JSON output, or that operate on a different runtime.

## Operating rules (distilled from the training tasks)

### 1. Read the access file before any network call
The runtime base URL, the allowed endpoints, and any required auth header/token are listed **per run** in `environment_access.md` (the file named by the task). Always read it fresh — never hardcode the base URL, endpoints, or token into the response. Substitute the base URL wherever a prompt writes `<TASK_ENV_BASE_URL>`.

### 2. Parse the contract before you fetch
Before touching the runtime, read both:
- `input/prompt.txt` — identifies the target `case_id`, the `task_id`, and what the response must *decide*.
- `input/payloads/answer_template.json` — the authoritative output contract.

From the template, extract and hold these constraints explicitly:
- **Required top-level keys** (exact set; no extra top-level keys unless the template says they are ignored).
- **Fixed/required values** (e.g. `task_id`, `case_id` constants named in the prompt or template — copy them verbatim).
- **Enum allowed-values** for every controlled field. Every value you emit must come from the template's enum; never invent a synonym.
- **Type and nullability** — use `null` *only* where the template permits it (e.g. `string_or_null`, `[integer, null]`). Otherwise the field is required and non-null.
- **Numeric precision and units** — match exactly (e.g. one decimal place for `value_mmol_l`, two for a probability, whole hours/integer days).
- **List ordering rules** — each list field states its own rule. Some normalize as sets (order irrelevant), some require ascending by `effective_time` then `observation_id`, some want "descending relevance," some want a stable order with case id first. Follow each field's rule individually.
- **Safety-check booleans** — these assert the response does *not* make an unsupported claim (e.g. `no_penicillin_or_sulfa`, `no_normal_cxr_claim`, `no_false_loc`, `no_false_vomiting`, `no_false_photophobia`). Set them strictly from chart evidence; they are how the evaluator catches fabrication.
- **Timestamp format** — ISO-8601 UTC with a trailing `Z` unless the template says otherwise.

### 3. Locate the exact target case (beware distractors)
The runtime is seeded with many synthetic records, including **distractor cases** whose summaries literally say "Synthetic distractor." Target cases and distractors share the same `case_type`. Do not guess by type or summary — fetch by the exact `case_id` named in the prompt:
- `GET /api/cases/{case_id}` returns the full case bundle: `case`, `findings` (key/value/source_id triples), `imaging`, `medications`, `allergies`, `problems`, `care_registry`, `sdoh`, etc.
- The bundle's `findings[].source_id` values are your **evidence identifiers** — collect them as you go.
- Cross-check `patient_id` from the case bundle rather than assuming it.

### 4. Gather only the chart facts the template scores
Pull the slices the template asks for, from the right endpoints (see `references/runtime_endpoints.md`). Typical sources:
- **Observations** via `GET /api/observations?patient_id=...` — FHIR-like rows with `code` (LOINC), `display`, `effective_time`, `status`, `value_number`, `value_text`, `interpretation`, `observation_id`, `source`. Filter on `status: final` and on the LOINC/code the protocol names as authoritative.
- **Protocols** via `GET /api/protocols` then `GET /api/protocols/{protocol_id}` — the protocol body carries controlled codes (LOINC/NDC), thresholds, branches, and the exact logic that maps findings to the enum outcomes. Treat the protocol as the source of truth for the decision rules.
- **Allergies / medications / problems / imaging / care-registry / sdoh** from the case bundle or their list endpoints.

### 5. Use POST /api/query for cross-cutting lookups
`POST /api/query` runs SQL over the runtime (read-only) and returns `{columns, rows, count, truncated}`. It requires the header from the access file (`X-Clinic-Token: synclinic-readonly` in the training run — read it from the file, don't hardcode). Use it when you need a precise join/filter that list endpoints make awkward (e.g. "all final serum-potassium observations for a patient in a date window"). Body shape: `{"sql": "SELECT ... FROM <table> WHERE ..."}`. Note the `truncated` flag — page or narrow the query if true.

### 6. Be strictly read-only
Do not mutate the runtime or place orders. Every allowed endpoint is a GET except the read-only `POST /api/query`. If a task says "do not place orders," that is enforced by this skill — emit a *recommendation*, never a side-effecting call.

### 7. Map evidence to the template's vocabulary, then self-validate
- Map each clinical fact to a template enum value, not prose. When a finding is **absent**, the template usually wants it listed under an `absent_red_flags`-style field or reflected in a safety boolean — follow the template's own absent/present split.
- Apply the protocol's decision logic (thresholds, urgent branches, gates) to pick risk tier / disposition / plan / gate result.
- Honor allergy and contraindication screens: if the patient has a relevant active allergy or contraindication, the medication/plan field must avoid that class and the corresponding safety boolean must be true.
- Populate `evidence_ids` with stable identifiers (case id, observation ids, imaging ids, protocol id, finding `source_id`s), ordered per that field's rule.

Before returning, validate the object against the template:
1. Exactly the required top-level keys (unless extras are explicitly ignored).
2. Every enum value is in the allowed set.
3. `null` appears only where permitted; required fields are present and non-null.
4. Numbers match precision/unit; timestamps end in `Z`.
5. Lists follow their per-field ordering rule and contain no duplicates where disallowed.
6. Safety booleans accurately reflect the absence of the unsupported claim.

### 8. Return only the JSON object
Emit exactly one JSON object — no markdown fences, no comments, no explanatory prose, no trailing text. The template's `output_rule`/`format` line is authoritative; if it conflicts with anything else, the format line wins.

## Case-type playbook map
The five task families are documented in `references/case_playbook.md`. Each entry names the case type, the relevant protocol id, the key endpoints, and the decision shape — **without final values**, so it transfers across runs and case ids. Consult it after step 2 to know which protocol and which evidence slices drive that task's enums.

## Files in this skill
- `SKILL.md` — this entry file (read first).
- `references/runtime_endpoints.md` — endpoint reference derived from `environment_access.md`, generalized so it stays valid when the access file changes per run.
- `references/output_contract.md` — the JSON-output contract distilled from the five templates: how to read a template and emit a conforming object.
- `references/case_playbook.md` — per-case-type playbook (respiratory/CAP, pediatric head injury, potassium replacement, care-management routing, observation-window lab retrieval).

## Quick start (per task)
1. Read `environment_access.md` → base URL, endpoints, auth header/token.
2. Read `input/prompt.txt` → target `case_id`, `task_id`, what to decide.
3. Read `input/payloads/answer_template.json` → keys, enums, nullability, precision, ordering, safety booleans.
4. `GET /api/cases/{case_id}` → patient_id, findings (evidence ids), imaging, allergies, meds, problems, registry, sdoh.
5. Pull the named protocol (`GET /api/protocols/{protocol_id}`) and the relevant observations (`GET /api/observations?patient_id=...`). Use `POST /api/query` for precise date/code/status filters.
6. Map findings → template enums via the protocol's logic; set safety booleans; collect `evidence_ids`.
7. Self-validate against the template (the six checks above).
8. Return exactly one JSON object.
