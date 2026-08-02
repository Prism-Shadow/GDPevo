---
name: clinic-protocol-answer
description: >-
  Produce a protocol-bound clinical decision-support JSON answer for a synthetic
  clinic case served by a read-only FHIR-like runtime API. Use this whenever a
  task names a target case id (e.g. CASE-RESP-102, CASE-HEAD-207, CASE-K-303,
  CASE-CM-411, CASE-LAB-518), points at a runtime environment via
  GDPEVO_ENV_BASE_URL / <TASK_ENV_BASE_URL>, and asks for a single JSON object
  that conforms to an input/payloads/answer_template.json. Covers respiratory/CAP
  assessment, pediatric head-injury triage, potassium replacement, care-management
  routing, observation-window retrieval, and similar template-driven answers with
  controlled enums, numeric-precision fields, evidence_ids, and safety_checks.
---

# Clinic protocol answer

These tasks all share one shape: a synthetic clinic exposes a read-only,
FHIR-like REST API; the prompt names one **target case** and requires a **single
JSON object** that conforms exactly to a per-task `answer_template.json`. The
correct output is derived by applying the **applicable protocol's logic** to the
**facts in the case record**. Your job is a faithful data-retrieval-and-mapping
task, not free clinical reasoning: read the schema, read the data, apply the
protocol, fill the template.

Do not invent values. Every scored field must be either copied from the
environment, chosen from the template's `allowed_values`, or computed by the
protocol's stated rule. Never assert a finding the record does not support.

## Inputs to read first

For the task you are solving, read (paths are relative to the task's input dir):

1. `prompt.txt` — gives the **target case id**, the clinical domain, and any
   hard constraints ("do not mutate", "do not place orders", "return only JSON").
2. `payloads/answer_template.json` — the **authoritative output contract**:
   `required_top_level_keys`, per-field `type`, `allowed_values` (enums),
   `precision`/`unit`, `ordering` rules, nullability (`*_or_null`,
   `["string","null"]`, `nullable`), and any `required_value` / `expected_constant`
   for fixed fields. Obey this exactly — do not add or drop top-level keys.
3. The separately-provided environment access file (e.g. `environment_access.md`)
   — the base URL, credentials, and the **allowed endpoint list** for this run.

## Environment access

- Resolve the base URL from `GDPEVO_ENV_BASE_URL` in the access file; the prompt's
  `<TASK_ENV_BASE_URL>` placeholder refers to the same value.
- Use **only** the endpoints listed as allowed for the run. The API is
  **read-only** — GET only. Do **not** POST orders or otherwise mutate state.
  (`POST /api/query`, when listed, is typically clinic-token-gated; when
  credentials are "none" it returns an auth error, so rely on the GET endpoints.)
- The one call that returns everything for a case is
  `GET /api/cases/{case_id}`. It returns a bundle with these keys:
  `case`, `patient`, `findings`, `observations`, `allergies`, `medications`,
  `problems`, `imaging`, `care_registry`, `sdoh`.
  Standalone list endpoints (`/api/patients`, `/api/observations`,
  `/api/medications`, `/api/allergies`, `/api/problems`, `/api/imaging`,
  `/api/care-registry`, `/api/sdoh`) exist for cross-checking and usually accept a
  `patient_id` query filter.
- `GET /api/protocols` lists protocols; `GET /api/protocols/{protocol_id}` returns
  the **protocol `body`** — the decision logic (see below).

A read-only helper, `scripts/clinic.py`, wraps these GET calls; see
"Helper script" at the end.

## Procedure

1. **Fetch the case bundle:** `GET /api/cases/{case_id}`. Record `patient_id`
   from `case.patient_id` / `patient.patient_id`.
2. **Locate the current/review time** when the answer needs one: look in
   `findings` for a `current_time` entry (its `source_id` is usually a task-clock
   id). Timestamps you emit should be ISO-8601 UTC with a trailing `Z`.
3. **Select the applicable protocol.** Match the case's `case_type`/domain to a
   protocol from `GET /api/protocols`, then fetch its `body`. The `body` is the
   single source of truth for thresholds, code mappings, and gating. Typical
   `body` contents:
   - `controlled_codes` — maps clinical concepts to the exact codes/enums the
     template expects (test codes, NDC, LOINC, etc.). Copy these verbatim.
   - `authoritative_statuses` / `status_rule` — usually only `status == "final"`
     observations count toward gates; `preliminary`, `entered-in-error`,
     `canceled` are excluded distractors.
   - thresholds and branches (e.g. target values, escalation cutoffs, red-flag
     lists, dose rules, follow-up hours, ordering rules). Apply them literally.
4. **Gather the evidence facts.** Read `findings` (key/value/`source_id`),
   `observations` (code, `status`, `interpretation`, `value_number`,
   `effective_time`, `observation_id`), `allergies` (active vs inactive),
   `medications`, `problems`, `imaging` (`impression`, `status`, `imaging_id`),
   `care_registry`, and `sdoh`. Note each fact's identifier — you will cite it.
5. **Compute each template field** by applying the protocol rule to the facts:
   - Enums: pick only from that field's `allowed_values`. If no rule fires, use
     the template's provided "pending/none/not-eligible/no-*" style value.
   - Numbers: honor `precision` (e.g. one decimal, two decimals, integer) and
     `unit`. Round exactly as the protocol's dose/rounding rule states.
   - Booleans (e.g. `replacement_required`, gate flags): set from the protocol
     comparison against the observed value.
   - Lists: include each qualifying code once (dedupe). Distinguish
     **present** vs **absent** lists when the template asks for both (e.g.
     `red_flags` vs `absent_red_flags`) — an "absent" list holds protocol red
     flags the record explicitly rules out.
6. **Apply ordering rules per field.** Some lists are sets ("no semantic
   ordering; normalize as a set") — any order, but no duplicates. Others require
   a stable sort (e.g. observations by `effective_time` ascending then
   `observation_id` ascending; evidence "case id first, then sources", or
   "descending relevance"). Follow the exact note on each field.
7. **Fill identifiers.** Set `task_id`, `case_id`, `patient_id`. If the template
   pins a `required_value`/`expected_constant` for a field, use it verbatim;
   `task_id` is the task's run identifier. Otherwise take `case_id`/`patient_id`
   from the prompt and case record.
8. **Build `evidence_ids`** from real resource identifiers actually used:
   `case_id`, `observation_id`s, `imaging_id`s, and finding `source_id`s that
   support your conclusions — ordered per the field's ordering note.
9. **Set `safety_checks`.** Each boolean asserts the answer *avoided* a specific
   unsupported or contraindicated claim (e.g. "did not recommend a drug class the
   patient is actively allergic to", "did not claim a normal image when imaging
   shows a finding", "did not fabricate an absent symptom"). Verify against the
   retrieved data and set `true` only when your answer genuinely honors the
   constraint — which it should, if you followed steps 4–6 faithfully.
10. **Emit exactly one JSON object** with only the required top-level keys, using
    `null` only where the field spec permits it. No markdown, comments, or prose
    outside the object.

## Allergy- and contraindication-awareness

When the template drives a medication/replacement plan: cross-check the patient's
**active** allergies and any protocol contraindication/urgent branch *before*
choosing a strategy. Choose the strategy enum that avoids implicated classes,
populate any `avoid_allergens`/`contraindications` field from the record, and let
a contraindication or urgent branch override the routine plan (e.g. defer/hold/
escalate) when its conditions are met.

## Observation-window tasks

When the task is a window retrieval: parse the window (`from` inclusive, `to`
exclusive), then partition the patient's observations. **Matched** = correct
target code, `status == "final"`, `effective_time` within the window. **Excluded**
= otherwise-relevant distractors that fail on date, code, or status (e.g. a
preliminary result, a different analyte, an out-of-window date). `latest_final`
is the matched observation with the greatest `effective_time`. Set the
`protocol_gate` enum and `repeat_lab` from the protocol using that latest final
value; sort id lists as the window protocol specifies.

## Validation checklist before returning

- [ ] Output is a single JSON object; top-level keys == `required_top_level_keys`
      (none added, none missing).
- [ ] Every enum value is in that field's `allowed_values`.
- [ ] Numeric fields match required precision/unit; `null` only where permitted.
- [ ] List fields are deduped and ordered per each field's rule.
- [ ] `task_id`/`case_id`/`patient_id` match any pinned `required_value`.
- [ ] `evidence_ids` are real identifiers from the environment.
- [ ] `safety_checks` reflect claims actually avoided; no unsupported finding.
- [ ] No mutating requests were made; no prose outside the JSON.

## Helper script

`scripts/clinic.py` performs the read-only GETs (no external dependencies). Set
`GDPEVO_ENV_BASE_URL` (or pass `--base`) and run, e.g.:

```
export GDPEVO_ENV_BASE_URL=http://task-env:9016/
python3 scripts/clinic.py case CASE-RESP-102      # full case bundle
python3 scripts/clinic.py protocols               # list protocols
python3 scripts/clinic.py protocol RESP-CAP-2026  # one protocol body
python3 scripts/clinic.py obs PAT-3303            # observations for a patient
python3 scripts/clinic.py get /api/allergies?patient_id=PAT-1002
```

It only issues GET requests; treat its output as read-only evidence.
