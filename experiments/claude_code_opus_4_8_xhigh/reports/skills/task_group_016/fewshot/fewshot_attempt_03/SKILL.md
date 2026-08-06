---
name: clinic-protocol-cds
description: >-
  Use when a task asks you to produce a structured JSON clinical-decision-support
  answer for a synthetic Harborview clinic case and gives you an
  input/payloads/answer_template.json to conform to, backed by a read-only clinic
  runtime API (endpoints listed in an environment_access file). Covers all five
  case families — adult respiratory / CAP, pediatric head injury, potassium
  repletion, care-management routing, and observation-window retrieval — by
  pulling the case bundle, applying the matching protocol, and emitting exactly
  one template-conformant JSON object with no prose.
---

# Clinic Protocol CDS

Answer a single synthetic-clinic decision-support task by grounding every field
in the runtime record and the matching protocol, then returning **exactly one
JSON object** that conforms to the task's `answer_template.json`.

## What each task gives you

- `input/prompt.txt` — names a **target case id** (e.g. `CASE-RESP-102`), the case
  family in prose, and the fields to populate. It references
  `<TASK_ENV_BASE_URL>` for the runtime and says the environment access is
  "listed separately".
- `input/payloads/answer_template.json` — a **schema descriptor** (not a fill-in
  form). It defines `required_top_level_keys`, per-field `type`, `allowed_values`
  (enums), numeric `precision`, `unit`, nullability, `ordering` rules, and
  sometimes an `expected_constant` / `required_value` for `task_id` / `case_id`.
- An environment-access file (e.g. `environment_access.md`) — gives the base URL
  as `GDPEVO_ENV_BASE_URL=...`, the credentials (often **none**), and the exact
  **allowed endpoints** for this run. Use it only to reach the network.

Your output must contain **only** the JSON object — no markdown, no comments, no
prose, no extra top-level keys.

## Procedure (case-family agnostic)

1. **Read the template first.** Extract the ordered `required_top_level_keys`,
   every enum's `allowed_values`, precision/unit, which fields may be `null`, and
   all `ordering` rules. Note any `expected_constant`/`required_value` for
   `task_id`, `case_id`. The template is the contract; the output shape is driven
   entirely by it, not by this doc.

2. **Set the identifiers.**
   - `task_id`: use the template's `expected_constant`/`required_value` when
     given; otherwise use the task's own identifier (the input/run/directory id).
   - `case_id`: the target case id from the prompt (confirm against any template
     constant).
   - `patient_id`: **read it from the case record** — never assume or reuse a
     value from an example.

3. **Pull the case bundle.** `GET {base}/api/cases/{case_id}` returns one bundle
   with `case`, `patient`, `findings[]`, `observations[]`, `imaging[]`,
   `medications[]`, `allergies[]`, `problems[]`, `care_registry`, `sdoh[]`. This
   is usually all you need. `case.case_type` selects the protocol (see
   `reference/protocol_playbook.md`).
   - The `findings[]` array (`finding_key` / `finding_value` / `source_id`) is the
     curated evidence layer — most enum decisions and `evidence_ids` come from it.
   - For patient-wide retrieval (observation-window tasks especially), also
     `GET {base}/api/observations?patient_id={patient_id}` so you catch every
     eligible and distractor observation, not just those already attached to the
     bundle. `GET {base}/api/patients/{patient_id}` gives patient-level allergies,
     meds, and problems.

4. **Fetch and apply the protocol.** `GET {base}/api/protocols` then
   `GET {base}/api/protocols/{protocol_id}`. **Read it at runtime** and use its
   thresholds/codes/status rules — do not rely on memorized constants; versions
   change. `reference/protocol_playbook.md` summarizes the current bodies and the
   case_type→protocol map as an orientation, but the live protocol wins.

5. **Derive each templated field from evidence + protocol.** Map findings and
   final observations onto the template's enums. Choose enum values only from the
   template's `allowed_values`. Honor precision, units, nullability, and ordering.

6. **Emit one JSON object** with exactly the required keys, then run the
   verification checklist below before returning.

## Environment access

- Base URL comes from the environment-access file's `GDPEVO_ENV_BASE_URL`. Do not
  hardcode a host; read it per run. Endpoints join as `{base}/api/...`.
- **Read-only.** Never mutate the environment or place orders. Only the `GET`
  endpoints are usable when `Credentials: none` — `POST /api/query` requires a
  clinic token that is not provided and returns `invalid or missing clinic token`.
  Everything needed is reachable via the `GET` endpoints, chiefly
  `GET /api/cases/{case_id}`.
- List endpoints (`/api/observations`, `/api/medications`, `/api/allergies`,
  `/api/problems`, `/api/imaging`, `/api/care-registry`, `/api/sdoh`) return
  `{count, items, limit, offset}` and accept filters like `?patient_id=`.
- Helper: `scripts/fetch_clinic_case.py <CASE-ID>` pulls the bundle,
  patient-filtered observations, and all protocol bodies into one JSON blob to
  work from (reads the base URL from `GDPEVO_ENV_BASE_URL` or `--base`).

## Cross-cutting output rules

- **Ground everything; fabricate nothing.** Every asserted finding, value, and id
  must trace to the record. If the record does not support a red flag / symptom /
  normal result, do not claim it. The `safety_checks` booleans exist to attest you
  did **not** assert unsupported findings (e.g. no false loss-of-consciousness, no
  "normal CXR" claim when imaging is abnormal) — set each to `true` only when your
  answer genuinely honors that constraint, which a grounded answer always does.
- **Enums only.** For scored/status/action fields, emit a value from the
  template's `allowed_values` — never free prose.
- **Only `final` observations satisfy protocol gates.** Every protocol lists
  `authoritative_statuses: [final]`. Exclude `preliminary`, `entered-in-error`,
  `canceled`, and any non-`final` status from matches, latest-value selection, and
  clinical conclusions.
- **Allergy-awareness.** Use **active** allergies only (ignore `inactive`). Map
  them to the template's allergen classes for `avoid_allergens`, and pick a
  medication/antibiotic strategy that avoids every implicated class.
- **Numeric precision & units.** Round exactly as the template says (e.g. one
  decimal for mmol/L, two decimals for a risk probability, integer hours/days/
  mEq). Keep the specified unit semantics.
- **Timestamps.** ISO-8601 UTC with a trailing `Z` (e.g. `2026-03-20T07:45:00Z`).
  Use the record's `current_time` finding as the clinical review time when a
  field needs "now". For date windows: **`from` inclusive, `to` exclusive** (a
  calendar month → first day 00:00:00Z of the month to first day 00:00:00Z of the
  next month).
- **Ordering.** Most lists are sets — "no semantic ordering", emit each value at
  most once. Where the template specifies a sort (e.g. observations by
  `effective_time` ascending then `observation_id` ascending; evidence with case
  id first), apply it exactly. When an "excluded" list mixes same-target-code and
  other-code distractors, group same-target-code exclusions before other-code
  ones, each still ordered by the template's key.
- **Nullability.** Use `null` only where the field spec permits it (e.g. no
  medication in this setting → `null` dose/route). Do not invent placeholder
  strings for absent data.
- **`evidence_ids`.** List the **stable identifiers you actually used** to support
  the decision — typically the case id plus the specific observation / imaging /
  registry / protocol `source_id`s (from `findings[].source_id` and resource ids),
  not every record present. Follow any template ordering (case id first when
  included).
- **No extra keys.** Include every required key and nothing beyond what the
  template allows.

## Distractor traps to avoid

- **Distractor cases** `CASE-D30xx` and unrelated real cases share case types —
  only operate on the prompt's target case id and its patient.
- **Wrong patient / wrong case** observations: cross-check `patient_id` (and
  `case_id` where relevant) on every resource.
- **Non-`final` status** results (e.g. a `preliminary` potassium) look eligible
  but are excluded.
- **Wrong code**: an observation for a different analyte (sodium when you need
  potassium `K`; a blood potassium code vs. the controlled serum `K` code) is a
  distractor. Use the protocol's `controlled_codes` for the exact code.
- **Out-of-window dates**: a `final`, correct-code result dated outside the window
  does not qualify.
- **Inactive allergies / resolved problems**: filter by `status`.

## Verification checklist (before returning)

- [ ] Exactly one JSON object; no prose/markdown/comments; no extra top-level keys.
- [ ] All `required_top_level_keys` present, in a valid shape.
- [ ] `task_id` / `case_id` match any template constant; `patient_id` came from the record.
- [ ] Every enum value is in the template's `allowed_values`.
- [ ] Numbers meet precision/units; timestamps are ISO-8601 `Z`; windows are `[from, to)`.
- [ ] Only `final` observations used for gates; correct controlled codes; in-window.
- [ ] Active allergies avoided; medication plan consistent with them.
- [ ] Lists respect set-vs-ordered rules; no duplicates in sets.
- [ ] `evidence_ids` are real ids actually used; ordering rule applied.
- [ ] `safety_checks` booleans truthfully reflect that no unsupported claim was made.
- [ ] Nothing fabricated: every asserted value traces to the retrieved record.
