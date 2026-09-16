---
name: clinic-decision-support
description: Solve protocol-bound clinical decision-support tasks against a synthetic clinic runtime by fetching case data and protocols, applying protocol rules to observations and findings, operating within template-provided enum spaces, and returning a single conformant JSON object.
---

# Clinic Decision Support Skill

Use this skill when a task asks you to prepare a structured clinical
decision-support result against the Harborview Synthetic Clinic runtime. The
task will give you a target case id, a JSON answer template, and access to the
clinic API. Your job is to fetch the right data, apply the right protocol rules,
and return a single JSON object that conforms exactly to the template.

## General workflow

Every task in this family follows the same four-phase pattern. Follow it in
order and do not skip phases.

### Phase 1 -- read the template

The task provides an `answer_template.json` (or the prompt embeds the schema).
Read it first. The template defines:

- Every required top-level key you must populate.
- The exact enum values allowed for each controlled field.
- Numeric precision rules and nullability rules.
- Any output-format constraints (single JSON object, no markdown, no extra keys).

Treat the template as authoritative. If a field has an allowed-values enum, you
must pick exactly one value from that list; never invent a value or use freeform
text for a controlled field.

### Phase 2 -- fetch the case

Use the case id from the prompt to call:

```
GET /api/cases/{case_id}
```

This composite endpoint returns a single JSON object with these sections:

| Section | What it holds | Why it matters |
|---------|--------------|----------------|
| `case` | case id, case type, patient id, service date, status, summary | Identifies the clinical domain and patient. The `case_type` hints at which protocol to look for. |
| `patient` | patient id, name, age, birth date, sex, FHIR id | Demographics used for age-appropriate decisions (pediatric vs adult protocols). |
| `findings` | key/value/source_id triples | Pre-digested clinical facts. Finding keys like `current_time`, `gcs`, `loss_of_consciousness`, `oxygen_room_air_range` encode protocol-relevant facts. Always check findings before raw observations. |
| `observations` | structured lab/vital/exam/procedure results | Each has `code`, `status`, `value_number`, `value_text`, `effective_time`, `interpretation`, `observation_id`, `patient_id`. |
| `imaging` | radiology results | Studies keyed by `imaging_id` with `impression` text and `status`. |
| `medications` | active/inactive medication list | Used for medication reconciliation and contraindication checks. |
| `allergies` | allergen, reaction, status triples | Used for allergy-aware medication planning. Only `status: "active"` allergies constrain plans. |
| `problems` | problem-list entries with ICD codes | Used for problem summaries and risk-tiering. |
| `care_registry` | registry risk score, dialysis schedule, chronic condition count, recent admission | Present for care-management cases; null otherwise. |
| `sdoh` | social-determinant entries with domain/severity/source | Present when social barriers are recorded. |

### Phase 3 -- fetch the relevant protocol

The case's `case_type` field and the findings often name the protocol. Common
mappings (may vary):

| case_type | Likely protocol |
|-----------|----------------|
| `acute_respiratory` | `RESP-CAP-2026` |
| `pediatric_head_injury` | `PEDS-HEAD-2026` |
| `potassium_repletion` | `K-REPLETION-2026` |
| `care_management` | `CM-HIGH-RISK-2026` |
| `observation_window` | `OBS-WINDOW-2026` |

If a finding or template directly references a protocol id, use that. Also check
`GET /api/protocols` to list all available protocols and confirm the match.

Fetch the protocol body:

```
GET /api/protocols/{protocol_id}
```

Every protocol has a `body` object with decision rules. Common protocol fields:

- `scope` -- free-text description of what the protocol covers.
- `authoritative_statuses` -- which observation statuses count (always `["final"]`).
- `controlled_codes` -- LOINC/custom codes used to identify relevant observations.
- Threshold fields -- numeric cutoffs like `oxygen_saturation_room_air_less_than: 90`, `target_potassium_mmol_l: 3.5`, `high_predictive_risk_min: 0.75`.
- `urgent_branch` / `urgent_route_triggers` -- conditions that trigger escalation.
- `allergy_rule` -- how to use active allergies for medication planning.
- `routine_dose_rule` / `routine_follow_up` -- rules for routine pathway dosing and timing.

### Phase 4 -- apply the protocol and fill the template

With the case data and protocol in hand, work through each required template key
left to right. For each key:

1. **Identifier keys** (`task_id`, `case_id`, `patient_id`): copy from the
   prompt or case object. The `patient_id` lives in the `case` or `patient`
   section of the case response.

2. **Enum keys** (`primary_assessment`, `risk_level`, `disposition`, etc.):
   derive from protocol thresholds applied to findings and observations. Pick
   the single best-matching allowed enum value. The protocol's threshold fields
   are your decision rules; the template's allowed-values list is your output
   vocabulary.

3. **List keys** (`red_flags`, `recommended_tests`, `evidence_ids`, etc.): build
   from findings, observation ids, imaging ids, and protocol rules. Lists are
   order-independent unless the template or protocol specifies an ordering rule.

4. **Object keys** (`medication_plan`, `follow_up`, `latest_potassium`, etc.):
   populate every required sub-key. Use `null` only where the template
   explicitly permits it.

5. **Boolean safety checks**: assert that contraindicated or unsupported claims
   do not appear in the data. For example, if the template defines
   `no_penicillin_or_sulfa`, set it to true only when the active allergy list
   confirms both classes; if a finding claims "clear lungs" but imaging shows
   consolidation, set the corresponding safety check to true (no contradictory
   claim present) or false (contradiction present).

## Observation filtering rules

When a protocol or template requires finding a specific observation:

1. Match by `code` using the protocol's `controlled_codes` mapping.
2. Match by `patient_id` against the case's patient.
3. Keep only `status: "final"` observations unless the protocol says otherwise.
   `preliminary`, `entered-in-error`, and `canceled` statuses are always
   excluded from protocol-gate decisions.
4. When a time window is specified (inclusive start, exclusive end), filter on
   `effective_time`.
5. For "latest" resolution: sort by `effective_time` descending, then by
   `observation_id` descending. The first result is the latest final.
6. Observations belonging to other patients (wrong `patient_id`) are distractor
   records and must be excluded from matched sets.
7. Observations with the right code but wrong body fluid or specimen type (e.g.
   whole-blood potassium vs serum potassium) may be excluded when the protocol
   targets serum specifically; check the `display` field and the protocol's
   controlled codes (some use "K" for serum and "6298-4" for whole blood).

## Protocol application patterns by domain

### Respiratory assessment

- Determine risk from oxygen saturation: `oxygen_room_air_range` in findings or
  the SPO2 observation. Values at 92-93% suggest moderate risk; values below the
  protocol's `oxygen_saturation_room_air_less_than` threshold suggest ED
  escalation.
- Red flags include hypoxemia ranges, pleuritic chest pain, confusion,
  hemoptysis, persistent fever, worsening dyspnea.
- Disposition is `outpatient_close_followup` unless ED escalation criteria
  (severe hypoxemia, respiratory rate >=30, systolic BP <90, confusion, sepsis,
  multilobar disease) are met.
- Imaging: CXR impression from imaging or the CXR-2V observation determines
  whether consolidation is present.
- Medication: cross-reference active allergies against the template's allowed
  allergens (penicillin, sulfonamide, macrolide, tetracycline). Choose an
  antibiotic strategy that avoids all active allergen classes. If the patient
  has both penicillin and sulfonamide allergies, doxycycline is the typical
  tetracycline-class outpatient choice.
- Follow-up timing comes from the protocol's `outpatient_follow_up_hours`.
- Return precautions come from the protocol's `return_precaution_codes`.

### Pediatric head injury assessment

- Risk tiering uses GCS score, loss-of-consciousness duration, vomiting count,
  coordination exam, and headache severity.
- "No immediate CT" is appropriate when GCS=15, no LOC, no vomiting, no focal
  weakness, no basilar skull signs, and no worsening severe headache.
- Red flags list findings that are present; absent-red-flags list protocol
  triggers that are confirmed absent.
- Restrictions cover driving, sports, school return-to-learn, and cognitive
  rest.
- Follow-up timing defaults to 48 hours unless the protocol offers a tiered
  range (24 or 48); choose the longer interval for stable intermediate cases.
- Safety checks confirm no false claims about LOC, vomiting, or photophobia.

### Potassium replacement

- Identify the latest final serum potassium observation (code `K`) by
  `effective_time` within the case's observations.
- Compare the value to the protocol's `target_potassium_mmol_l`. Replacement is
  required when the value is below target.
- Check the urgent branch first: is potassium below the urgent threshold? Are
  ECG abnormalities present? Is the patient dialysis-dependent? Are severe
  symptoms (palpitations, syncope) reported? If the urgent branch fires, set
  `potassium_plan` to `urgent_escalation` and populate `urgent_actions`.
- If not urgent: apply the `routine_dose_rule`. The dose in mEq =
  round((target - latest_k_value) / 0.1) * the protocol's mEq per 0.1 step,
  rounded to the nearest protocol-specified increment.
- The medication NDC comes from the protocol's `controlled_codes`.
- Follow-up lab is "next morning" (next calendar day at 8:00 AM local/UTC).
- Contraindication screen: `dialysis_dependent` from problems (code N18.6
  active), `arrhythmia_symptoms` from findings, `egfr` from the latest eGFR
  observation (code `33914-3`).

### Care-management routing

- Risk tier is high when the registry `risk_score` exceeds the protocol's
  `high_predictive_risk_min`. Otherwise moderate or low.
- Program is `complex_care_management` when the case triggers multiple complex
  care criteria (chronic condition count >= 3, recent admission, dialysis,
  heart failure, uncontrolled diabetes). Otherwise `routine_case_management` or
  `not_eligible`.
- Priority problems are derived from active problem-list entries, SDOH entries,
  and relevant observations. Map clinical conditions to the template's
  controlled problem codes (e.g. `uncontrolled_diabetes` when HbA1c > 8.5,
  `esrd_on_hemodialysis` from problem list, `hyperphosphatemia` when phosphorus
  is elevated, `polypharmacy` when medication count is high).
- Numeric anchors pull exact values: risk_score (registry), hba1c_percent
  (A1C observation), phosphorus_mg_dl (phosphate observation), blood_pressure
  (SBP/DBP vitals), active_medication_count (registry).
- Referrals: pharmacist when medication count >= 10 or insulin is present;
  social_worker when SDOH domains at moderate/severe level >= 2;
  dialysis_care_coordination when ESRD on dialysis; transportation_benefits
  when transportation barrier exists.
- Outreach stance: `permission_based_plain_language` when SDOH or call notes
  indicate reluctance or barriers; `standard_scripted_outreach` otherwise.
- Care plan minima: min 3 problems, weekly follow-up, member-stated priority
  required, at least 2 disciplines.
- Escalation conditions: select from template allowed values based on clinical
  risks present (e.g. missed dialysis risk for ESRD patients, PHQ-9 monitoring
  when PHQ-9 is elevated).
- Source provenance: `chart_facts` lists values obtainable from structured data;
  `member_disclosure_needed` lists facts that require patient conversation.

### Observation window retrieval

- The window boundaries come from findings or the case record. Default to
  calendar-month boundaries when the prompt specifies a month.
- Fetch all observations from the case response (already included in the
  composite `/api/cases/{case_id}` response). Filter by:
  - `patient_id` matches the target patient
  - `code` matches the target code (protocol's controlled code)
  - `status` is `final`
  - `effective_time` falls inside the window (inclusive start, exclusive end)
- Sort matched observations by `effective_time` ascending, then `observation_id`
  ascending.
- Collect excluded observations: those with right code and patient but wrong
  status (preliminary), those with right code but wrong patient, those with
  right code but effective_time outside the window, and those with non-target
  codes that appear as nearby distractors.
- `latest_final` is the matched observation with the latest `effective_time`
  (ties broken by `observation_id` descending).
- Protocol gate: `satisfies_recent_final_normal` when the latest value is within
  normal range; `recent_final_low_repletion_needed` when below target;
  `recent_final_critical_or_urgent` when critically low; `no_final_lab_in_window`
  when no matching observation exists.
- Repeat lab: recommended when the latest value is low or no lab found;
  otherwise false.

## Enum discipline

This is the most common failure mode. Be strict:

1. Copy the allowed-values list from the template for every enum field.
2. Pick exactly one value per field (or a subset for multi-select lists).
3. Never use a value because it "sounds close." If the template says
   `worsening_shortness_of_breath` and the chart says "worsening dyspnea," use
   what the template allows: `worsening_shortness_of_breath`. Mapping clinical
   language to template enums is part of the task.
4. When a template value like `coordination_symptom_observe` is available and a
   finding describes mild coordination difficulty, use that enum value even if
   the finding uses different wording.
5. Lists may specify "no semantic ordering" -- this means any order is
   acceptable, but you must not include duplicates.

## Evidence ID patterns

`evidence_ids` lists should include identifiers that anchor the decision:

- The `case_id` itself.
- Observation ids for key vitals, labs, imaging impressions, and protocol-relevant results.
- Imaging ids from the `imaging` array.
- Protocol ids are generally not included unless the template asks for them.

Include only ids that are actually referenced in the decision logic. Sort them
with the case id first, then clinical source ids in descending order of
importance.

## Safety check patterns

Safety-check boolean fields follow a naming convention like
`no_<unsupported_claim>`. Understand what each means:

- `no_penicillin_or_sulfa`: true when the active allergy list contains both
  penicillin and sulfonamide allergies (so a penicillin or sulfa drug would be
  unsafe). The "no" means "no safe use of these classes" -- the contraindication
  is confirmed.
- `no_normal_cxr_claim`: true when there is no claim of a normal CXR (imaging
  shows consolidation). Prevents the false impression that lungs are clear.
- `no_clear_lungs_claim`: similar pattern for lung findings.
- `no_false_loc`: true when LOC is genuinely absent (confirmed zero seconds, not
  misreported).
- `no_false_vomiting`: true when vomiting is genuinely absent.
- `no_false_photophobia`: true when photophobia is genuinely absent.

Always cross-check: read the finding value, read the observation value, confirm
the safety check assertion matches the data.

## API quick reference

These are the endpoints available through the runtime environment. The task
environment configuration lists the exact base URL and any required credentials. For detailed field descriptions see [api_reference.md](api_reference.md).

### GET /health
Database readiness and schema version. Use to confirm the environment is alive.

### GET /api/cases/{case_id}
Composite case bundle. This is the primary data source and includes patient,
findings, observations, medications, allergies, imaging, problems,
care_registry, and sdoh. Always start here.

### GET /api/protocols
List all protocol ids and titles. Use to discover which protocols are relevant.

### GET /api/protocols/{protocol_id}
Full protocol body with decision rules, thresholds, controlled codes, and
clinical pathways.

### GET /api/patients/{patient_id}
Individual patient demographics. Usually unnecessary since `/api/cases/{case_id}`
includes the patient object.

### GET /api/observations, /api/medications, /api/allergies, /api/problems, /api/imaging, /api/care-registry, /api/sdoh
Collection endpoints. Prefer the composite case endpoint instead, which already
scopes these to the relevant case.

### POST /api/query
Structured query endpoint. May require a specific header token. Use only when
the composite case endpoint does not provide sufficient data.

## Common pitfalls

1. **Using preliminary observations for decisions.** Only `status: "final"`
   observations count for protocol gates and lab windows. Preliminary results
   are excluded.

2. **Picking the wrong patient's observation.** Some cases include observations
   from other patients as distractors. Always filter by `patient_id`.

3. **Picking the wrong code's observation.** The protocol's `controlled_codes`
   map codes to semantic roles. A "K" code observation and a "6298-4" code
   observation both measure potassium but in different specimens. Use the code
   the protocol specifies.

4. **Ignoring active vs inactive allergies.** Only `status: "active"` allergies
   constrain the medication plan.

5. **Mixing up window boundaries.** Inclusive start, exclusive end. An
   observation with `effective_time` exactly at the end time is excluded.

6. **Rounding errors on dose calculations.** Follow the protocol's rounding
   rule exactly (nearest 10 mEq, nearest whole day, etc.).

7. **Inventing enum values.** The template's allowed-values lists are
   exhaustive. If the clinical picture doesn't perfectly match any template
   value, pick the best fit from the allowed list; never create a new value.

8. **Omitting null fields.** When the template permits null for a field (e.g.
   `medication: null` when no medication is recommended), use JSON `null`, not
   an empty string or a placeholder.

9. **Forgetting the single-JSON-object output rule.** No markdown fences, no
   explanatory prose, no comments. Return exactly the JSON object.

10. **Sorting mismatches.** When the template or protocol specifies an ordering
    rule (`effective_time ascending`, `observation_id ascending`), follow it
    exactly. When no ordering is specified, any order is acceptable but avoid
    duplicates.

## Step-by-step checklist

When you receive a new task of this family, follow this checklist:

1. [ ] Read the answer template. Note every required key and its type.
2. [ ] Identify the target case id from the prompt.
3. [ ] Call `GET /api/cases/{case_id}` and inspect the response.
4. [ ] Identify which protocol(s) apply from the case type, findings, or
       template references.
5. [ ] Call `GET /api/protocols/{protocol_id}` for each relevant protocol.
6. [ ] For each template key, derive the value:
   - Identity keys: copy from case/prompt.
   - Enum keys: apply protocol thresholds to case findings/observations.
   - List keys: collect matching ids/codes from case data.
   - Object keys: populate every required sub-field.
   - Boolean safety checks: verify data supports the assertion.
7. [ ] Double-check: are all enum values from the template's allowed list?
8. [ ] Double-check: are all observations filtered by status=final,
       patient_id, and code?
9. [ ] Double-check: are null fields correct (null vs omitted vs placeholder)?
10. [ ] Return the single JSON object with no extra text.
