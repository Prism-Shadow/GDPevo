# Clinic Runtime API & Protocol Reference

Structural reference for the synthetic clinic runtime. Values shown are shapes and
field names, not answers — always read live data and the live protocol body for the
case in front of you. The base URL comes from `environment_access.md`
(`GDPEVO_ENV_BASE_URL`), e.g. `http://task-env:9016/`.

## Endpoints

| Method | Path | Purpose | Notes |
|--------|------|---------|-------|
| GET | `/api/patients` | List patients | `{count, items[], limit, offset}` |
| GET | `/api/patients/{patient_id}` | One patient | demographics |
| GET | `/api/cases` | List cases | each item has `case_id, case_type, patient_id, service_date, status, summary` |
| GET | `/api/cases/{case_id}` | **Full case bundle** | primary source; 404 if unknown |
| GET | `/api/observations` | Observations | filter `?patient_id=`, `?case_id=`, `?code=`, `?status=` |
| GET | `/api/medications` | Medications | filter `?patient_id=` |
| GET | `/api/allergies` | Allergies | filter `?patient_id=` |
| GET | `/api/problems` | Problem list | filter `?patient_id=` |
| GET | `/api/imaging` | Imaging studies | filter `?patient_id=` / `?case_id=` |
| GET | `/api/care-registry` | Care-management registry row | filter `?patient_id=` / `?case_id=` |
| GET | `/api/sdoh` | Social-determinants entries | filter `?patient_id=` |
| GET | `/api/protocols` | List 5 protocols | `protocol_id, title, version` |
| GET | `/api/protocols/{protocol_id}` | Protocol rule `body` | apply these rules |
| POST | `/api/query` | Gated query | needs a clinic token; without it returns `{"error":"invalid or missing clinic token"}` → treat as unavailable |

List endpoints return `{count, items, limit, offset}`. Credentials are usually
`none`; the GET endpoints cover every task.

### Query-param caveats
- `?patient_id=` and `?code=` and `?status=` filter as expected.
- `?from=`/`?to=` on `/api/observations` are **not reliable** for date windowing —
  results can include out-of-window rows. Do window filtering yourself by parsing
  `effective_time`.

## `/api/cases/{case_id}` bundle shape
```
{
  case:          {case_id, case_type, patient_id, service_date, status, summary},
  patient:       {patient_id, fhir_id, name, sex, age, birth_date},
  findings:      [{finding_key, finding_value, source_id}, ...],
  observations:  [Observation, ...],
  medications:   [Medication, ...],
  allergies:     [Allergy, ...],
  problems:      [Problem, ...],
  imaging:       [Imaging, ...],
  care_registry: {…} | null,
  sdoh:          [Sdoh, ...] | []
}
```
`findings` are free-text-ish key/value clinical facts with a `source_id` (a good
evidence id source, e.g. `VISIT-…`, `OBS-…`, `IMG-…`, `ALG-…`).

### Resource shapes (key fields)
- **Observation**: `observation_id, patient_id, case_id, code, display, category,
  status, interpretation, value_number, value_text, unit, effective_time, source`.
- **Medication**: `medication_id, patient_id, name, code, dose, route, frequency,
  status, start_date, end_date, source`.
- **Allergy**: `id, patient_id, allergen, reaction, status` (only `active` counts).
- **Problem**: `id, patient_id, name, code, status, onset_date`.
- **Imaging**: `imaging_id, patient_id, case_id, study, impression, status,
  performed_at`.
- **care_registry**: `risk_score, chronic_condition_count, medication_count,
  dialysis_schedule, recent_admission_date, program_hint`.
- **Sdoh**: `id, patient_id, domain, severity, evidence, source`.

## Distractors (never the target unless the prompt names them)
- Case ids `CASE-D30xx` and patient ids `PAT-D20xx` are synthetic distractor records.
- A case bundle can include an observation whose `patient_id` differs from the case
  patient (cross-patient distractor, e.g. an id containing `WRONGPAT`). Drop it.
- Same-analyte distractors: a different code for the same concept (whole-blood
  potassium `6298-4` vs serum `K`), or a `preliminary`/`entered-in-error` copy.

## Case type → protocol map

| `case_type` | `protocol_id` | Decision focus |
|-------------|---------------|----------------|
| `acute_respiratory` | `RESP-CAP-2026` | assessment (CAP vs viral URI vs pending), risk, disposition, red flags, tests, allergy-aware antibiotic plan, stabilization, follow-up, return precautions, safety checks |
| `pediatric_head_injury` | `PEDS-HEAD-2026` | assessment, risk tier, disposition, imaging recommendation, present/absent red flags, activity/school/driving restrictions, follow-up, safety checks |
| `potassium_repletion` | `K-REPLETION-2026` | latest final serum K, replacement need, oral dose, medication order, follow-up lab timing, urgent escalation, contraindication screen |
| `observation_window` | `OBS-WINDOW-2026` | matched vs excluded observations in a date window for a target code, latest final, protocol gate, repeat-lab recommendation |
| `care_management` | `CM-HIGH-RISK-2026` | risk tier, program routing, priority problems, numeric anchors, referrals, outreach stance, care-plan minima, escalation conditions, chart-vs-member source provenance |

## Protocol `body` fields to read (apply live values)

Read each protocol's `body` at runtime; these are the fields to base logic on. The
numeric constants live in the response — do not hardcode them here.

- **RESP-CAP-2026**: `controlled_codes` (chest_xray, respiratory_viral_pcr,
  oxygen_saturation, pulse_ox_recheck, respiratory_rate, temperature, basic_cbc),
  `authoritative_statuses`, `ed_escalation` (oxygen room-air threshold, respiratory
  rate threshold, systolic BP threshold, other red flags like confusion / sepsis /
  immunocompromise / multilobar), `allergy_rule`, `outpatient_follow_up_hours`,
  `return_precaution_codes`. Decide assessment from imaging impression + findings;
  risk by comparing vitals to `ed_escalation`; antibiotic strategy by allergy
  constraints; map to the template's own enum vocab (which may rename codes).
- **PEDS-HEAD-2026**: `urgent_route_triggers`, `mild_tbi_support`, `follow_up_hours`,
  `restrictions` (driving / return_to_play / school), `authoritative_statuses`.
- **K-REPLETION-2026**: `target_potassium_mmol_l`, `controlled_codes`
  (serum_potassium `K`, egfr, follow_up_lab LOINC, routine_oral_potassium_ndc,
  ecg_summary), `routine_dose_rule` (mEq per 0.1 below target, rounding),
  `routine_follow_up`, `urgent_branch` (potassium threshold, dialysis-dependent
  ESRD, ECG abnormality, severe renal contraindication, symptom list). Urgent branch
  overrides routine oral repletion.
- **OBS-WINDOW-2026**: `controlled_codes`, `status_rule` (only `final` satisfies
  gates), `excluded_statuses` (preliminary / entered-in-error / canceled),
  `same_code_selection` (latest final in window), `ordering` (effective_time asc,
  then observation_id asc).
- **CM-HIGH-RISK-2026**: `high_predictive_risk_min`, `complex_care_supporting_triggers`,
  `pharmacist_referral_triggers`, `social_work_referral` (domains + min
  moderate/severe domain count), `outreach` (permission-based when reluctant),
  `care_plan_minima`. Distinguish **chart facts** (registry/observations) from
  **member-disclosed** facts (sdoh with `source: member-disclosed`) for the
  source-provenance grouping.

## Evidence-id guidance
Prefer stable ids that appear in the data: `observation_id`, `imaging_id`, the
`case_id`, `finding.source_id`. Order them per the template's `ordering` rule (often
case id first then clinical sources, or descending relevance). Only cite ids you
actually relied on.
