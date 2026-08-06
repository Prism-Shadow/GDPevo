---
name: clinic-protocol-decision-support
description: >-
  Produce a single strict-JSON answer for a protocol-bound clinical decision-support
  task against the synthetic Harborview / GDPEVO clinic runtime. Use whenever a prompt
  names a target case id like CASE-XXX-NNN, points to a runtime at <TASK_ENV_BASE_URL>
  with GET /api/... endpoints, and requires output conforming to
  input/payloads/answer_template.json. Covers adult respiratory / CAP assessment,
  pediatric head injury triage, potassium repletion, observation-window / protocol-gate
  retrieval, and care-management routing — and generalizes to unseen case types that
  follow the same shape.
---

# Clinic protocol decision-support (GDPEVO synthetic clinic)

## What these tasks look like

Every task in this family shares one shape:

1. A `prompt.txt` names exactly **one target case id** (e.g. `CASE-RESP-102`) and tells
   you to review it in a runtime environment at `<TASK_ENV_BASE_URL>`.
2. `input/payloads/answer_template.json` is a **strict contract**: required top-level
   keys, enum-constrained values, types, null rules, numeric precision, and ordering
   rules. This file — not your medical judgment about wording — defines every allowed
   value. Read it first and last.
3. A separate `environment_access.md` lists the base URL, credentials (usually `none`),
   and the exact allowed endpoints for this run.

Your deliverable is **exactly one JSON object** that satisfies the template. No markdown,
no code fences, no prose outside the object, no extra top-level keys.

## Operating procedure

Do these in order for any task:

1. **Extract identifiers from the prompt.** Note the target `case_id`. Determine
   `task_id`: if the template pins it (`expected_constant` / `required_value`, e.g.
   `"train_004"`), use that exact string; otherwise use the task's own directory / run
   name. Never invent an unrelated id.

2. **Read the template as a schema.** List every required key, every enum's allowed
   values, every `*_or_null` field, every precision rule, and every `ordering` /
   `ordering_rule`. Build your answer to hit those keys and only those keys. Enum fields
   must contain a value from the allowed list verbatim — if your clinical reading has no
   matching enum, you have misread the case, not found a gap in the template.

3. **Read `environment_access.md` for this run.** Take the base URL and endpoint list
   from it — do not hardcode a host. Credentials are typically `none`.

4. **Pull the case bundle — the one call that matters.**
   `GET <base>/api/cases/{case_id}` returns a fully joined record for that case:
   `case`, `patient`, `findings` (key/value/source_id), `observations`, `medications`,
   `allergies`, `problems`, `imaging`, `care_registry`, `sdoh`. This bundle is the
   authoritative, case-scoped evidence. Prefer it over the global list endpoints.
   Read `patient.patient_id` here — that is the `patient_id` for your answer.

5. **Fetch the governing protocol.** Map `case.case_type` → `protocol_id` and
   `GET <base>/api/protocols/{protocol_id}`. The protocol `body` holds the thresholds,
   controlled codes, status rules, and routing logic you must apply. Use the **live**
   protocol values; treat `references/protocol-logic.md` only as a fast orientation
   guide. Case-type → protocol mapping and endpoint details are in
   `references/endpoints.md` and `references/protocol-logic.md`.

6. **Select evidence and filter distractors** (see "Distractor discipline" below).

7. **Apply the protocol** to the filtered evidence to fill each template field. When a
   field is genuine clinical judgment within the enum set, choose the value the protocol
   thresholds support and cite the driving observation in `evidence_ids`.

8. **Run the safety checks** (below), then emit one JSON object and stop.

## Distractor discipline (this is where tasks are won or lost)

The runtime is seeded with decoys. Filter every piece of evidence against the target:

- **Wrong patient.** A row may carry the target `case_id` yet a different `patient_id`
  (e.g. a potassium result stamped with another patient's id). Keep only rows whose
  `patient_id` equals the target patient from the bundle.
- **Wrong code.** "Serum potassium" is a specific controlled code (`K`); a whole-blood
  potassium (`6298-4`) or a sodium (`NA`) is **not** the target code even though it looks
  similar. Match the protocol's `controlled_codes` exactly.
- **Wrong status.** Only `status = "final"` observations satisfy protocol gates. Exclude
  `preliminary`, `entered-in-error`, `canceled`. (Protocols state this explicitly.)
- **Wrong time window.** When a task defines a window, treat `from` as inclusive and `to`
  as **exclusive** (a March-2026 window is `2026-03-01T00:00:00Z` ≤ t <
  `2026-04-01T00:00:00Z`). Drop observations outside it.
- **Distractor cases/patients.** Ids like `CASE-D30xx` and `PAT-D20xx` and any
  "generated distractor feed" source are never your target. The global lists
  (`/api/observations`, `/api/medications`, …) are dominated by these; if you use a list
  endpoint, filter it hard (`?patient_id=&code=&status=`) and cross-check against the
  bundle.
- **`POST /api/query` is unusable here.** It demands a clinic token that a
  `credentials: none` run does not have (returns `invalid or missing clinic token`).
  Do everything with the GET endpoints.

When a task asks you to report both matched and **excluded** observation ids, the excluded
list is the *relevant near-misses* you filtered out (wrong date/code/status/patient) — not
every unrelated row in the database. Sort exactly as the template's `ordering` says
(typically `effective_time` ascending, then `observation_id` ascending). When picking a
single "latest" value, choose the latest qualifying **final** effective_time.

## Evidence ids

Populate `evidence_ids` (or `source_provenance`) with the **stable identifiers you
actually relied on**: `observation_id`s, `imaging_id`s, the `source_id` from findings, the
protocol id, and the case id. Follow any stated ordering (e.g. "case id first," or
"descending relevance"). Do not pad with ids you did not use.

## Output-contract rules

- Emit **only** the required top-level keys. Extra keys are at best ignored, at worst a
  failure; omit them.
- Use enum values **verbatim**. Booleans are real booleans, not strings.
- Honor numeric precision exactly: "one decimal place" → `3.5` (not `3.50` or `3`);
  integer fields → integers; keep units out of numeric fields unless the field is a
  string like `blood_pressure: "152/88"`.
- Use `null` **only** where the field type permits it (`*_or_null`, `["integer","null"]`,
  nullable objects). Never send `null` for a plain required field, and never invent a
  placeholder string where `null` is meant.
- Timestamps: ISO-8601 UTC with trailing `Z` when the field asks for it.
- Empty is a valid answer: use `[]` for a list when the protocol yields no items, not a
  fabricated entry.

## Safety checks (do not fabricate reassuring findings)

Several templates carry `safety_checks` booleans and forbid unsupported claims. The
recurring rule: **never assert a normal/negative finding you did not observe.**

- Do not claim a "normal CXR" or "clear lungs" when imaging shows consolidation; set the
  corresponding `no_normal_cxr_claim` / `no_clear_lungs_claim` to `true` only because your
  answer genuinely avoids that claim.
- Do not claim absent loss-of-consciousness / vomiting / photophobia unless the record
  supports absence; the `no_false_*` booleans assert your answer did not fabricate them.
- **Allergy-aware medication selection:** read active allergies from the bundle and avoid
  every implicated class. If penicillin and sulfonamide allergies are active, do not
  recommend a beta-lactam or sulfa drug; pick an enum-allowed alternative the patient
  tolerates, and list the avoided classes in `avoid_allergens`. Set
  `no_penicillin_or_sulfa` true only when your plan truly avoids them.
- When the protocol's urgent/ED-escalation thresholds are **not** met, do not escalate;
  when they **are** met, defer definitive treatment as the protocol directs (e.g. defer
  antibiotic choice to the ED) rather than improvising.
- Do not mutate the environment or "place orders" — these are read-only assessments.

## Final self-check before returning

- [ ] `task_id`, `case_id`, `patient_id` match the prompt/template (pinned constants used
      where required).
- [ ] Every required key present; no extra top-level keys; all enums from the allowed set.
- [ ] Evidence filtered by patient + code + status + window; distractors excluded.
- [ ] Numeric precision, null rules, and list ordering obey the template.
- [ ] `evidence_ids` cite only ids you used; ordering rule followed.
- [ ] Safety booleans reflect an answer that makes no unsupported normal/negative claim,
      and any medication plan is allergy-aware.
- [ ] Output is a single JSON object — no markdown, comments, or surrounding text.
