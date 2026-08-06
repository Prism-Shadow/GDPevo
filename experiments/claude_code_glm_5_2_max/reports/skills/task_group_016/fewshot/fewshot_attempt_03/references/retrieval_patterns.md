# Retrieval Patterns & Evidence Assembly

How to pull the right data out of the runtime and turn it into the identifiers
and structured fields the template asks for.

## Start from the target case

`GET /api/cases/{case_id}` (case_id from the prompt) returns a bundle that
already nests most resources for that case: `case`, `allergies`, `observations`,
`medications`, `imaging`, `problems`, `care_registry`, `sdoh`. Read `patient_id`
from `case.patient_id` (or the bundle's allergies/observations).

The `/api/cases` list contains **distractor cases** with similar case_types and
deliberately mixed data quality. Always anchor on the prompt's `case_id`; never
let a distractor's values bleed into your answer.

## Confirm with dedicated endpoints

The bundle is convenient but may be partial or summary-level. Cross-check with:

- `GET /api/patients/{patient_id}` — demographics / stable identifiers.
- `GET /api/observations` — full observation set; filter by patient, code, and
  status. This is authoritative for lab/vital values and effective times.
- `GET /api/medications` — active medications; drives `active_medication_count`
  and polypharmacy / allergy-cross-checking.
- `GET /api/allergies` — active vs inactive allergens; drives
  `avoid_allergens` and the medication safety check. An *inactive* allergen
  does not constrain the plan.
- `GET /api/problems` — problem list; drives `priority_problems` codes.
- `GET /api/imaging` — imaging studies and findings; drives imaging-dependent
  red flags and the "no normal/normal-claim" safety checks.
- `GET /api/care-registry` — risk scores, program eligibility, registry flags.
- `GET /api/sdoh` — social determinants; drives member-disclosure / barrier
  fields and referral selection.

When a list endpoint returns many patients' data, filter to the target
`patient_id` (and time window where relevant) before using any value.

## Ad-hoc queries

`POST /api/query` (with the run's auth header, body `{"sql": "..."}`) is for
read-only SELECT-style lookups the GET endpoints don't cover directly — e.g.
joining observations to a code across a date range. Keep queries read-only.

## Picking the protocol

`GET /api/protocols` lists protocols by domain; `GET /api/protocols/{protocol_id}`
returns thresholds, red-flag catalogs, escalation rules, and gating logic. Match
the protocol to the case's clinical domain. The protocol — not your general
medical knowledge — defines the exact risk tiers, red flags, and cutoffs to
apply, so the enum values you emit are defensible against the runtime evidence.

## Building evidence_ids

Use real ids from the runtime, never fabricated ones:

- the `case_id` itself,
- `observation_id`s for the labs/vitals you relied on,
- imaging ids,
- protocol ids,
- registry / problem keys where the template groups provenance.

Apply the template's ordering rule (case id first when stated; otherwise by
relevance or time). If a value didn't come from a real resource, it doesn't
belong in `evidence_ids`.

## Observation-window specifics

For templates with `window`, `target_code`, `matched_observation_ids`,
`excluded_observation_ids`, `latest_final`:

1. Take all observations for the `patient_id` with the `target_code`.
2. Split into **final** vs non-final (preliminary/cancelled). Only final,
   in-window observations are "matched".
3. Window is `[from, to)` — `from` inclusive, `to` exclusive. An observation
   exactly at `to` is excluded; one exactly at `from` is included.
4. `matched_observation_ids`: sort by `effective_time` asc, then
   `observation_id` asc.
5. `excluded_observation_ids`: relevant distractors (wrong date, wrong code, or
   wrong status) sorted the same way (by `effective_time` when available).
6. `latest_final`: the last matched observation — include its `observation_id`,
   `value_mmol_l` (one decimal), and `effective_time` (ISO-8601 UTC `Z`). Set to
   `null` only when `lab_found` is false.
7. `protocol_gate` / `repeat_lab`: derive from the latest final value against
   the protocol's thresholds (normal → no repeat; low → repletion/repeat;
   critical → urgent; none in window → `no_final_lab_in_window`).

## Deriving safety_checks

Each boolean corresponds to a specific unsupported claim the answer must avoid
(e.g. prescribing a contraindicated drug class, claiming imaging is normal when
it isn't, asserting a red flag the patient lacks). Verify each against the
runtime evidence and set it `true` only when the answer is clean on that point.
A `false` means you've made the unsupported claim — fix the answer, then set it
`true`. Do not blanket-set all checks to `true` without per-field verification.
