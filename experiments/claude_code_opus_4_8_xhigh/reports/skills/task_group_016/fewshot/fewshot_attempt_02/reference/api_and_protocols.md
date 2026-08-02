# Reference: clinic API shape and protocol → answer mapping

Generic structural notes for the synthetic-clinic runtime. Read protocol
constants live from the environment; the values below describe *shape and
which fields feed which answer section*, not any task's answer.

## Endpoints (use only those the environment-access file lists)

- `GET /api/patients`, `GET /api/patients/{patient_id}` — demographics,
  problems, allergies, medications, sdoh for a patient.
- `GET /api/cases`, `GET /api/cases/{case_id}` — the case **bundle** (see
  below). The list endpoint returns many cases; most are distractors.
- `GET /api/observations` — flat, filterable observation list (e.g. by
  `patient_id`); same records as appear in the bundle.
- `GET /api/medications`, `/api/allergies`, `/api/problems`, `/api/imaging`,
  `/api/care-registry`, `/api/sdoh` — topical lists.
- `GET /api/protocols`, `GET /api/protocols/{protocol_id}` — protocol catalog
  and the decision-rule `body`.
- `POST /api/query` — may be listed but typically rejects with "invalid or
  missing clinic token"; when no token is supplied, rely on the GET endpoints.

## Case bundle keys (`GET /api/cases/{case_id}`)

`case` (`patient_id`, `case_type`, `service_date`, `status`, `summary`),
`findings` (`{finding_key, finding_value, source_id}`), `observations`,
`imaging`, `medications`, `allergies`, `problems`, `sdoh`, `care_registry`.
Any section may be `null` or empty. `findings[].source_id` and resource ids
(`observation_id`, `imaging_id`, `medication_id`, `case_id`) are candidate
`evidence_ids`.

### Observation object
`observation_id`, `code` (analyte/LOINC-style, e.g. potassium `K`, sodium
`NA`, an eGFR/renal code, or a vitals code),
`display`, `status` (`final` | `preliminary` | `entered-in-error` |
`canceled`), `effective_time` (ISO-8601 Z), `value_number` / `value_text`,
`unit`, `interpretation`, `patient_id`, `case_id`.

## case_type → protocol

| case_type             | protocol id (match by title/scope) |
|-----------------------|------------------------------------|
| acute_respiratory     | Adult Respiratory Infection / CAP  |
| pediatric_head_injury | Pediatric Head Injury Clinic Triage|
| potassium_repletion   | Potassium Replacement & Escalation |
| care_management       | High-Risk Care-Management Routing  |
| observation_window    | Observation Window Interpretation  |

Confirm the mapping against the live `GET /api/protocols` list — select by
title/scope rather than assuming an id string.

## What each protocol body typically supplies (read live values)

- **Respiratory / CAP:** `controlled_codes` (map raw tests/vitals to template
  test enums), ED-escalation thresholds (SpO2, respiratory rate, systolic BP,
  other red flags) → risk level & disposition, `outpatient_follow_up_hours`,
  `return_precaution_codes`, allergy rule (avoid implicated classes) →
  antibiotic strategy and `avoid_allergens`, `authoritative_statuses`.
- **Pediatric head injury:** `urgent_route_triggers` and `mild_tbi_support`
  → assessment / risk tier / imaging recommendation; `follow_up_hours`
  options; `restrictions` (driving / return-to-play / school). Present vs.
  absent triggers drive `red_flags` vs. `absent_red_flags` and the safety
  "no false ..." booleans.
- **Potassium replacement:** `target_potassium_mmol_l`, `urgent_branch`
  criteria (K threshold, dialysis/ESRD, ECG abnormality, symptoms, renal
  contraindication), `routine_dose_rule` (mEq per 0.1 below target, rounding),
  `controlled_codes` (serum potassium, eGFR, follow-up-lab LOINC, oral KCl
  NDC), `routine_follow_up` timing. Pick the latest `final` potassium; screen
  contraindications from renal/ECG/symptom findings.
- **Care-management routing:** `high_predictive_risk_min` vs. registry
  `risk_score` → tier/program; `complex_care_supporting_triggers`,
  `pharmacist_referral_triggers`, `social_work_referral` domain rule →
  referrals; `care_plan_minima`. Split `source_provenance` into chart-derived
  facts (registry/labs/vitals) vs. member-disclosed sdoh barriers.
- **Observation window:** `status_rule` / `excluded_statuses`,
  `same_code_selection` (latest final in window), `ordering`
  (effective_time asc, then observation_id asc). Window is commonly `from`
  inclusive, `to` exclusive. Matched = target-patient, target-code, `final`,
  in-window; excluded = same-patient records disqualified by date/code/status;
  wrong-patient records are dropped entirely (not listed as excluded).

## Recurring distractors to reject
Wrong-patient observations sharing the target code; `preliminary` / prelim-id
results; wrong analyte codes; out-of-window dates; closed or unrelated
distractor cases in the case list; inactive allergies/medications when a rule
asks about active ones.
