---
name: harborview-clinic-decision-support
description: Protocol-bound clinical decision support for the Harborview Synthetic Clinic. Use when solving structured assessment tasks for respiratory, head-injury, potassium-replacement, care-management, or observation-window cases that require cross-referencing clinic records with decision protocols and returning a template-conformant JSON answer.
---

# Harborview Clinic Decision Support

Solve protocol-bound clinical decision-support tasks for Harborview Synthetic
Clinic by reading the target case, retrieving all related clinical data,
cross-referencing findings against the applicable protocol, and returning a
single JSON object that conforms exactly to the provided answer template.

## When to use this skill

Use this skill when the task prompt asks you to prepare a structured
clinical-decision-support result for a Harborview Synthetic Clinic case,
references `<TASK_ENV_BASE_URL>`, and includes an `answer_template.json`
payload. The task will direct you to retrieve a specific case, review clinic
data through allowed endpoints, apply a relevant protocol, and output a clean
JSON response.

## Overall workflow

Follow this sequence on every task. Do not skip steps.

1. **Read the prompt** to extract the target `case_id` and the task type.
2. **Read `input/payloads/answer_template.json`** in full. Memorize every
   required top-level key, every allowed enum value, and every data type
   constraint before you start retrieving data. The template is the
   single source of truth for the output shape.
3. **Retrieve the case** from `GET /api/cases/{case_id}`. This returns the
   case record, patient identifier, findings, observations, medications,
   allergies, imaging, care-registry entries, and SDOH data in one response.
4. **Identify the protocol** from the case type:
   - `acute_respiratory` → `RESP-CAP-2026`
   - `pediatric_head_injury` → `PEDS-HEAD-2026`
   - `potassium_repletion` → `K-REPLETION-2026`
   - `care_management` → `CM-HIGH-RISK-2026`
   - `observation_window` → `OBS-WINDOW-2026`

   Retrieve it with `GET /api/protocols/{protocol_id}`.
5. **Cross-reference findings against protocol rules.** The protocol defines
   decision thresholds (numeric cutoffs, trigger lists, dosing formulas),
   and the case findings provide the values to evaluate. Apply protocol
   rules strictly; do not invent thresholds or assessments that the
   protocol does not support.
6. **Fill the answer template** with values derived from the case data and
   protocol rules. Use only the exact enum strings, field names, and types
   defined in the template.
7. **Return exactly one JSON object.** No markdown fences, no explanatory
   prose outside the JSON, no extra top-level keys.

## Retrieving case data

The primary endpoint is `GET /api/cases/{case_id}`. It aggregates all
relevant records for the case in a single response:

| Key in response | Contents |
|---|---|
| `case` | Case metadata (id, type, patient_id, service_date, status, summary) |
| `findings` | Structured clinical findings as `finding_key`/`finding_value`/`source_id` triples |
| `observations` | FHIR-like Observation resources with `observation_id`, `code`, `effective_time`, `status`, `value_number`, `unit`, `interpretation` |
| `medications` | Active and historical medications with `medication_id`, `name`, `code`, `dose`, `route`, `frequency`, `status` |
| `allergies` | Active allergies with `allergen`, `reaction`, `status` |
| `imaging` | Imaging study references when present |
| `care_registry` | Registry data for care-management cases (risk_score, dialysis_schedule, medication_count, recent_admission_date) |

Use the findings `source_id` values and observation `observation_id` values
when populating `evidence_ids` in the answer template.

### Bulk SQL queries

For observation-window and other tasks that require filtering across
observations by code, date range, or status, use the SQL endpoint:

```
POST /api/query
Content-Type: application/json
X-Clinic-Token: synclinic-readonly

{"sql": "SELECT ... FROM observations WHERE ..."}
```

Available tables include `observations`, `medications`, `patients`, `cases`,
`allergies`, `imaging`. Column names match the JSON field names in the REST
responses (e.g. `observation_id`, `code`, `effective_time`, `status`,
`value_number`, `interpretation`, `patient_id`, `case_id`).

Prefer `POST /api/query` when you need sorted, filtered result sets across
multiple records. Use the case detail endpoint for the primary case review.

## Protocol-driven decision rules

Protocols returned by `GET /api/protocols/{protocol_id}` contain a `body`
object with decision rules. Apply them as follows:

### Reading numeric thresholds

A protocol field like `"oxygen_saturation_room_air_less_than": 90` means that
an O2 sat strictly below 90 triggers that branch. Use the numeric
`value_number` from the matching observation, not the finding text.

### Reading trigger lists

A protocol field like `"urgent_route_triggers": ["repeated_vomiting",
"seizure", ...]` means any matching finding value triggers that path. Compare
the `finding_value` or observation `interpretation` against the trigger
keywords. Use clinical judgment for fuzzy matches (e.g. "mild" nausea does
not match "repeated_vomiting").

### Dosing formulas

The K-REPLETION-2026 protocol defines a dose rule:

```
routine_dose_rule:
  applies_only_when_urgent_branch_false: true
  mEq_per_0_1_mmol_l_below_target: 10
  round_to_nearest_mEq: 10
  target_potassium_mmol_l: 3.5
```

Calculate as: `dose = round((target - latest_K) * 10 * mEq_per_0_1, nearest
rounding_unit)`. For example, `3.5 - 3.3 = 0.2`, `0.2 * 10 * 10 = 20 mEq`,
rounded to nearest 10 → 20.

### Excluded statuses

Protocols declare excluded observation statuses (e.g. `"excluded_statuses":
["preliminary", "entered-in-error", "canceled"]`). Only observations with
`status = "final"` count for protocol gates, dose calculations, and lab
window matching. Preliminary observations are distractors.

## Allergy-aware medication planning

When the case includes active allergies, cross-reference the allergen names
against the medication classes you plan to recommend. The answer template's
`avoid_allergens` list must reflect all active allergies relevant to the
medication plan.

Common mappings for this clinic:

- penicillin allergy → avoid penicillin-class antibiotics (beta-lactams)
- sulfonamide allergy → avoid sulfa-class antibiotics
- macrolide allergy → avoid macrolide antibiotics
- tetracycline allergy → avoid tetracycline-class antibiotics

Select `antibiotic_strategy` values that are compatible with the patient's
allergy profile. For example, a patient with active penicillin and sulfa
allergies cannot receive `standard_outpatient_beta_lactam_plus_macrolide`.

## Enum compliance

Every field that lists `allowed_values` in the answer template must be filled
with one of those exact strings. Do not paraphrase, abbreviate, or invent
values. This applies to:

- Assessment and risk-level enums
- Disposition and imaging enums
- Red-flag and absent-red-flag lists
- Medication plan enums (strategy, route, frequency)
- Follow-up enums
- Return-precaution enums
- Referral, problem, and escalation-condition codes
- Protocol-gate and repeat-lab enums

If a finding does not clearly map to any allowed enum value, prefer
omitting that value (for optional list fields) or choosing the closest match
supported by the protocol, rather than guessing.

## Evidence IDs and safety checks

### Evidence IDs

Populate `evidence_ids` with stable identifiers from the data you used to
make decisions. Include the case identifier and relevant observation,
imaging, or protocol identifiers. Use the exact `source_id` from findings
and `observation_id` from observations. Order is generally not scored, but
place the case identifier first when included.

### Safety checks

The answer template defines boolean safety-check keys. These verify that you
did not fabricate findings. Set each to `true` only when you can confirm the
claim from the case data:

- `no_penicillin_or_sulfa`: true when the medication plan avoids penicillin
  and sulfonamide classes, matching the patient's actual allergies.
- `no_normal_cxr_claim`: true when you did not describe a CXR as normal if
  the imaging shows consolidation or other abnormalities.
- `no_clear_lungs_claim`: true when you did not describe lungs as clear if
  findings contradict that.
- `no_false_loc`: true when you did not claim loss of consciousness when
  findings show it was absent.
- `no_false_vomiting`: true when you did not claim vomiting when findings
  show it was absent.
- `no_false_photophobia`: true when you did not claim photophobia when
  findings do not support it.

Set each safety-check boolean to `true` if the corresponding fabrication was
avoided (i.e. your output is truthful). If you inadvertently claimed
something unsupported, set it to `false`. In practice, following the findings
and protocol strictly should produce all `true`.

## Time and window handling

- Use `current_time` from the findings (key `current_time`) as the clinical
  review timestamp when the template requires it.
- For observation-window tasks, the window bounds come from the findings
  (`window_start`, `window_end`). Apply inclusive start, exclusive end.
- Follow-up `timeframe_hours` is an integer; derive it from the protocol's
  `follow_up_hours` or `outpatient_follow_up_hours` field.
- Observation `effective_time` is always ISO-8601 UTC with trailing `Z`.

## Output discipline

The answer template's `output_rule` or `output_rules` section is
non-negotiable:

- Return exactly one JSON object.
- Do not wrap it in markdown code fences.
- Do not include comments, explanatory prose, or extra top-level keys.
- Use `null` only where the template explicitly permits it.
- Use controlled enum values rather than prose for all scored status and
  action fields.

## Task-type quick reference

| Task type | Case type | Protocol | Key decisions |
|---|---|---|---|
| Respiratory | `acute_respiratory` | `RESP-CAP-2026` | CAP vs viral URI, O2-sat-based risk, allergy-aware antibiotics, CXR, return precautions |
| Head injury | `pediatric_head_injury` | `PEDS-HEAD-2026` | mTBI vs concussion vs severe, GCS, LOC/vomiting/neuro red flags, activity/school/driving restrictions |
| Potassium | `potassium_repletion` | `K-REPLETION-2026` | Latest K, dose calculation (10 mEq per 0.1 below 3.5), NDC 40032-917-01, follow-up lab LOINC 2823-3, urgent branch, eGFR contraindication |
| Care management | `care_management` | `CM-HIGH-RISK-2026` | Risk score ≥ 0.75, chronic conditions ≥ 3, referrals (pharmacist at ≥ 10 meds, social work at ≥ 2 SDOH domains), outreach stance, escalation conditions, source provenance |
| Observation window | `observation_window` | `OBS-WINDOW-2026` | Final-only K observations within date window, exclude pre-window/prelim/non-K distractors, protocol gate from latest value |

## Common failure modes

Avoid these errors seen across training tasks:

1. **Using non-final observations for protocol decisions.** Always filter by
   `status = "final"`.
2. **Recommending medications the patient is allergic to.** Check the
   allergies array before finalizing the medication plan.
3. **Inventing enum values.** If a finding does not map cleanly to an
   allowed enum, re-read the protocol and template; the mapping is always
   present in the protocol body.
4. **Including distractor observations in matched lists.** For
   observation-window tasks, exclude observations outside the window, with
   wrong codes, or with non-final status.
5. **Miscalculating the potassium dose.** Apply the protocol formula
   exactly: `(3.5 - latest_K) * 100`, rounded to nearest 10 mEq.
6. **Forgetting to include `task_id` and `case_id`** as the first two keys
   in the output JSON.
7. **Wrapping JSON in markdown.** The evaluator parses raw JSON; markdown
   fences cause parse failures.
8. **Using prose instead of enum values** for `status`, `route`, and
   `frequency` fields in medication orders.
