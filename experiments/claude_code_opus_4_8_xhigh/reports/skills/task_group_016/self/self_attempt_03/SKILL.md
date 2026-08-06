---
name: clinic-protocol-decision-support
description: >-
  Produce protocol-bound clinical decision-support JSON for a synthetic FHIR-like
  clinic runtime. Use when a task supplies a target clinic case id (e.g.
  CASE-XXX-NNN) plus an answer_template.json schema and asks for one structured
  JSON assessment — adult respiratory / CAP, pediatric head injury, potassium
  repletion, serum-lab observation-window retrieval, or care-management routing —
  built strictly from a read-only clinic HTTP API. Triggers on prompts that say
  "synthetic clinic runtime", "<TASK_ENV_BASE_URL>", "conforms to
  input/payloads/answer_template.json", or "Return only a JSON object".
---

# Clinic Protocol Decision Support

## What this task family is

Each task gives you exactly two things:

1. A **prompt** (`input/prompt.txt`) naming one target **case id** (`CASE-...`) and
   the clinical decision to make.
2. An **answer template** (`input/payloads/answer_template.json`) — the strict
   schema your output must satisfy.

You read a **read-only clinic API** (base URL supplied separately in the run's
environment-access notes), apply the matching **clinic protocol**, and return
**exactly one JSON object** conforming to the answer template. No prose, no
markdown fences, no extra top-level keys, no narrative outside the JSON.

The answer template is the contract; the protocol body is the rulebook; the case
bundle is the evidence. Never invent values — every field is derived from
retrieved data or the template's own constants.

## Environment access (read carefully, every run)

The run's environment-access file (e.g. `environment_access.md`) gives:

- `GDPEVO_ENV_BASE_URL` — substitute this for `<TASK_ENV_BASE_URL>` in the prompt.
- `Credentials:` — typically `none`.
- The **allowed endpoints** for this run. Only use endpoints listed there.

Observed facts about this runtime (re-verify per run; do not assume):

- All useful reads are **GET** endpoints under `/api/...`. They need no auth.
- `POST /api/query` requires a clinic token that is **not** provided and returns
  `{"error":"invalid or missing clinic token"}`. Do **not** depend on it; get
  everything from GET endpoints.
- The task is **read-only**. Never place orders, never mutate state, even when a
  prompt mentions "order-entry" or "order-ready" details — those describe the
  JSON you return, not an action to perform.

### Primary endpoint

`GET /api/cases/{case_id}` returns a consolidated bundle — your main source:

```
{
  case:          { case_id, case_type, patient_id, service_date, status, summary },
  patient:       { patient_id, name, age, sex, birth_date, fhir_id },
  findings:      [ { finding_key, finding_value, source_id }, ... ],   # narrative + evidence source ids
  observations:  [ { observation_id, code, display, status, effective_time,
                     value_number, value_text, unit, interpretation,
                     patient_id, case_id, category }, ... ],
  medications: [...], allergies: [...], problems: [...], imaging: [...],
  care_registry: {...}|null, sdoh: [...]
}
```

Supporting GET endpoints (filterable, e.g. `?patient_id=&code=`) give a clean
per-patient view and let you cross-check the bundle: `/api/patients`,
`/api/patients/{id}`, `/api/cases`, `/api/observations`, `/api/medications`,
`/api/allergies`, `/api/problems`, `/api/imaging`, `/api/care-registry`,
`/api/sdoh`, `/api/protocols`, `/api/protocols/{protocol_id}`.

### Protocols are the rulebook

`GET /api/protocols` lists them; `GET /api/protocols/{id}` returns a `body` with
thresholds, `controlled_codes`, `authoritative_statuses`, escalation triggers,
follow-up timing, etc. **Always fetch the live protocol and treat its `body` as
the source of truth.** The case's `case_type` selects the protocol:

| case_type              | protocol id         |
| ---------------------- | ------------------- |
| acute_respiratory      | RESP-CAP-2026       |
| pediatric_head_injury  | PEDS-HEAD-2026      |
| potassium_repletion    | K-REPLETION-2026    |
| observation_window     | OBS-WINDOW-2026     |
| care_management        | CM-HIGH-RISK-2026   |

Per-family decision logic and the protocol→template vocabulary mapping are in
`reference/protocol_playbook.md`. Read it, but reconcile against the live body.

## Core workflow

1. **Read the whole answer template first.** Extract, per field: `type`,
   `allowed_values` (enums), nullability (`_or_null`, `["string","null"]`),
   numeric `precision`/`unit`, timestamp `format`, `ordering` rules, and any
   `expected_constant` / `required_value` / `required_when`. This is your output
   checklist.
2. **Resolve identifiers.** `case_id` = from the prompt. Fetch the case bundle;
   `patient_id` = `case.patient_id`. Set `task_id`: if the template pins it via
   `expected_constant`/`required_value`, use that exact string; otherwise use this
   task's own id from the task context (e.g. `train_003`, or the test id) — never
   invent one.
3. **Fetch the matching protocol body** by `case_type`.
4. **Establish the clock.** Find `current_time` in `findings`
   (`finding_key == "current_time"`, or a task-clock finding like
   `TASK-CLOCK-*`). For window tasks, read `window_start`/`window_end` (or
   `from`/`to`) from findings. All scheduled/relative times are computed from this
   clock per the protocol (e.g. "+48h", "next morning").
5. **Select real evidence; reject distractors.** Bundles deliberately include
   distractor rows. For any observation used in a gate, require ALL of:
   `patient_id == case.patient_id` (bundles can carry another patient's row),
   `code` == the protocol's controlled code for that concept (not a look-alike,
   e.g. serum `K` vs whole-blood `6298-4`), `status` in the protocol's
   `authoritative_statuses` (usually `final`; exclude `preliminary`,
   `entered-in-error`, `canceled`), and inside the required time window when one
   applies. When two finals share a code, pick the latest `effective_time`.
6. **Apply protocol logic** to compute each clinical field (assessment, risk,
   disposition, tests, plan, flags, escalation, follow-up). Map protocol wording
   to the **template's** enum vocabulary — they differ; only ever emit a value
   that appears in that field's `allowed_values`.
7. **Collect evidence ids.** Use the `source_id` of each finding you relied on and
   the `observation_id` / `imaging_id` / `case_id` / `protocol_id` of each
   resource. Respect the template's evidence ordering rule (some say "case id
   first"; some are unordered).
8. **Assemble, validate, emit.** Run the pre-submit checklist, then print exactly
   one JSON object.

## Output discipline (the ways these tasks are failed)

- **Enums only from the template.** For every enum/list-of-enum field, emit only
  strings from that field's `allowed_values`. Translate protocol/chart wording
  into the nearest allowed value; if nothing fits, that value is not selected.
- **No extra top-level keys.** Include every `required_top_level_keys` entry.
  Omit anything not in the schema unless the template explicitly ignores extras.
- **Numeric precision & type.** Honor stated precision (e.g. one/two decimals) and
  integer-vs-number typing. Apply protocol rounding rules (e.g. round dose to the
  nearest step). Use numbers, not strings, for numeric fields.
- **Timestamps.** ISO-8601 UTC. Include the trailing `Z` whenever the format says
  so. Compute relative times from `current_time`, not "now".
- **Nulls only where allowed.** Use `null` solely for fields typed
  `*_or_null` / `["...","null"]`. Fill sibling keys consistently (e.g. when a
  medication is not recommended, null out its `dose`/`route` per the spec and set
  `status` to the correct enum).
- **Ordering.** Set-normalized lists: dedupe, order-free. Explicitly ordered lists:
  apply exactly (e.g. `effective_time` ascending then `observation_id` ascending;
  evidence "case id first, then clinical sources").
- **Booleans are real booleans** (`true`/`false`), never strings.
- **Safety-check booleans mean "I did not fabricate."** Set them so they assert
  that your output makes no unsupported claim: e.g. `no_normal_cxr_claim: true`
  means you did not assert a normal chest X-ray; `no_false_loc: true` means you
  did not assert a loss of consciousness the record doesn't support;
  `no_penicillin_or_sulfa: true` means the plan avoids those classes. Base every
  clinical claim strictly on retrieved evidence, then set these accordingly.
- **Allergy awareness.** Read `allergies` with `status == "active"`. Avoid every
  implicated medication class; reflect them in any `avoid_allergens`/
  contraindication field, and choose a compliant medication (or defer) per protocol.

## Pre-submit checklist

- [ ] Output is one JSON object, no markdown/comments/prose.
- [ ] All `required_top_level_keys` present; no extra top-level keys.
- [ ] `task_id`/`case_id`/`patient_id` correct (constants honored; patient from bundle).
- [ ] Every enum value ∈ that field's `allowed_values`.
- [ ] Numbers at required precision/type; rounding rules applied.
- [ ] Timestamps ISO-8601 UTC with `Z`; relative times computed from `current_time`.
- [ ] `null` used only where permitted; dependent keys consistent.
- [ ] List ordering rules applied (set vs sorted).
- [ ] Only patient-matched, correct-code, authoritative-status, in-window
      observations used for gates; distractors excluded (and listed in an
      `excluded_*` field if the template asks).
- [ ] `evidence_ids` are real `source_id`/resource ids in the required order.
- [ ] Safety-check booleans reflect that no unsupported claim was made.
- [ ] Nothing was mutated; only GET endpoints used.
