---
name: clinic-decision-support
description: Solve clinic decision-support tasks by retrieving structured case data from a synthetic clinic FHIR-like REST API, interpreting protocol rules, and mapping clinical facts into schema-constrained JSON answer templates. Covers respiratory, head-injury, potassium-repletion, care-management, and observation-window domains.
---

# Clinic Decision-Support Skill

Use this skill when a task provides a clinic case identifier, read-only API
access to a synthetic clinic runtime, and a JSON answer template with
schema-constrained output. The skill covers structured protocol assessment,
order-entry decision support, care-management routing, and observation-window
retrieval tasks.

## Core Workflow

1. Identify the target `case_id` from the prompt.
2. Read the answer template (`input/payloads/answer_template.json`) and
   internalize every required key, allowed enum value, numeric precision rule,
   and nullability constraint before retrieving data.
3. Pull case detail from `GET /api/cases/{case_id}`. This bundles the patient
   record, observations, findings, medications, allergies, imaging, problems,
   SDoH, and care-registry data for the case.
4. If the task references a protocol (respiratory, potassium, head-injury,
   care-management, or observation-window), fetch the relevant protocol from
   `GET /api/protocols` or `GET /api/protocols/{protocol_id}` and apply its
   decision rules against the case data.
5. Map findings and observations to template fields using only controlled enum
   values from the schema. Use clinical reasoning that is grounded in protocol
   rules, not speculation.
6. Return exactly one JSON object matching the template. No markdown, no
   commentary, no extra top-level keys.

## API Reference

See [api_reference.md](api_reference.md) for endpoint details, data model,
authentication, and status semantics.

## Observation Filtering

- Only observations with `status: "final"` are authoritative for clinical
  decision-making. Exclude `preliminary`, `canceled`, and `entered-in-error`
  observations from final assessments, but include them in
  `excluded_observation_ids` when a template asks for excluded items.
- Observation codes distinguish analytes: `"K"` is serum potassium, `"NA"` is
  sodium, `"33914-3"` is eGFR, `"4548-4"` is HbA1c, `"2777-1"` is phosphate.
  Non-standard codes like `"SARS_FLU_RSV_PCR"`, `"CXR-2V"`, `"PULSE_OX_RECHECK"`
  are domain-specific.
- When a template asks for `latest_potassium` or similar, pick the most recent
  `final` observation meeting the code and patient constraints.

## Observation Window Tasks

When the task defines a date window (e.g., March 2026 for potassium labs):
- Match observations by `patient_id`, `code`, `status: "final"`, and
  `effective_time` within the window (inclusive start, exclusive end).
- Exclude observations that fail any of those filters: wrong patient, wrong
  code, non-final status, or effective time outside the window.
- Sort matched observations by `effective_time` ascending, then by
  `observation_id` ascending.
- Derive `protocol_gate` from the latest matched observation's value against
  protocol thresholds.

## Protocol-Driven Clinical Domains

### Respiratory Protocol

- Red flags: hypoxemia (SpO2 92-93% or below 90%), pleuritic chest pain,
  respiratory distress, confusion, hemoptysis, persistent fever, worsening SOB.
- Risk level: moderate when stable vitals with borderline SpO2 and focal
  consolidation; high when severe hypoxemia or multilobar disease.
- Disposition: outpatient if moderate with no severe red flags; ED transfer for
  high-risk or severe hypoxemia.
- Medication plan must respect active allergies. Avoid penicillin and
  sulfonamide antibiotics when `allergies` shows active reactions to those
  classes.
- Safety checks: `no_penicillin_or_sulfa` is true when the plan avoids those;
  `no_normal_cxr_claim` is true when the CXR shows consolidation (not normal).

### Potassium Repletion

- Retrieve the protocol from `GET /api/protocols/K-REPLETION-2026` (or the
  protocol ID indicated in case data).
- Key protocol fields: `target_potassium_mmol_l` (typically 3.5), `routine_dose_rule`,
  `urgent_branch` criteria, `controlled_codes`.
- Only `final` serum potassium (`code: "K"`) observations count.
- Urgent branch triggers: `dialysis_dependent_esrd`, `ecg_abnormality`,
  `potassium_less_than` threshold, `severe_renal_contraindication`, or
  `symptoms` matching protocol criteria (palpitations, syncope, weakness with
  arrhythmia concern).
- Routine oral dose: compute `(target - value) * 10 mEq per 0.1 mmol/L below
  target`, round to nearest 10 mEq. Use `routine_dose_rule.mEq_per_0_1_mmol_l_below_target`
  and `routine_dose_rule.round_to_nearest_mEq` from the protocol.
- Follow-up lab LOINC: `2823-3` for serum potassium. Schedule per protocol (next
  morning when routine).
- Urgent actions are empty for routine cases. For urgent cases, populate with
  `urgent_clinician_notification`, `ekg_now`, or `telemetry_or_ed_evaluation`
  in clinical action sequence order.

### Pediatric Head Injury

- Red flags: head impact (always present in these cases), mild nausea,
  coordination symptoms (observe), LOC, repeated vomiting, seizure, focal
  weakness, worsening headache, basilar skull signs, photophobia.
- `absent_red_flags` lists the serious flags confirmed absent (LOC, vomiting,
  seizure, focal weakness, worsening headache, basilar skull signs,
  photophobia). Only include flags that are genuinely absent from the case.
- Risk tier: low when all serious flags are absent and exam is normal;
  intermediate when coordination issues or mild symptoms are present despite
  GCS 15; high when LOC, repeated vomiting, or focal deficits are present.
- Imaging: `no_immediate_ct` for low/intermediate with no high-risk features;
  `ct_or_ed_per_protocol` when concerning but not urgent; `urgent_ct` for
  severe.
- Restrictions include cognitive/physical rest, return-to-learn
  accommodations, no high-risk sports, no driving until symptom-free, and
  normal activity as tolerated, depending on severity.
- Safety checks: `no_false_loc`, `no_false_vomiting`, `no_false_photophobia`
  are true when the assessment does not falsely claim these findings.

### Care-Management Routing

- Retrieve the protocol from `GET /api/protocols/CM-HIGH-RISK-2026`.
- `risk_tier`: derived from registry `risk_score` (≥0.7 is high, 0.5-0.7
  moderate, <0.5 low) combined with admission recency and chronic condition
  count.
- `program`: `complex_care_management` for high-risk with ESRD, recent
  admission, uncontrolled diabetes, or heart failure; `routine_case_management`
  for moderate risk; `not_eligible` for low risk.
- `priority_problems`: select from the template's allowed problem codes based
  on active conditions, lab values, and barriers.
- `numeric_anchors`: pull `risk_score`, `hba1c_percent`, `phosphorus_mg_dl`,
  `blood_pressure` (format as systolic/diastolic), and `active_medication_count`
  from registry and observation data.
- `referrals`: map SDoH barriers and clinical needs to referral codes.
- `outreach_stance`: `permission_based_plain_language` when member has barriers
  and disclosed preferences; `standard_scripted_outreach` for routine cases;
  `directive_clinician_instruction` for urgent clinical need.
- `care_plan_minima`: set min problem count, weekly follow-up requirement,
  member-stated priority requirement, and min disciplines based on risk tier
  and complexity.
- `source_provenance`: separate `chart_facts` (data from registry/labs/vitals)
  from `member_disclosure_needed` (data from SDoH and member interviews).

### Observation-Window and Lab Gating

- Exactly match patient, code, status (final only), and date window.
- Distractors come in predictable forms: observations for other patients,
  observations with wrong analyte codes, observations outside the date window,
  non-final observations (preliminary, canceled, entered-in-error).
- `protocol_gate` values:
  - `satisfies_recent_final_normal`: latest final value at or above target (e.g., K ≥ 3.5).
  - `recent_final_low_repletion_needed`: latest final value below target but above critical threshold.
  - `recent_final_critical_or_urgent`: latest final value below critical threshold.
  - `no_final_lab_in_window`: no qualifying observation found.
- `repeat_lab`: recommend when current lab is outside normal range; set
  `scheduled_time` based on protocol recheck timing.

## Evidence IDs

- Every `evidence_ids` entry must reference a specific API resource identifier:
  case IDs, observation IDs, imaging IDs, or protocol IDs.
- Order is not scored unless the template says otherwise, but place the case
  identifier first when included, then clinical source identifiers.

## Safety Checks

- Safety checks are boolean validations that confirm the assessment does not
  make false claims. For example, `no_penicillin_or_sulfa` being true means the
  medication plan genuinely avoids penicillin and sulfonamide classes.
- Set each safety check to `true` when the corresponding false claim is indeed
  absent from the assessment; set to `false` only when the assessment actually
  makes the claim being checked.

## Data Access Pattern

Prefer the case detail endpoint (`GET /api/cases/{case_id}`) as the primary
data source -- it returns a unified bundle of case, patient, observations,
findings, medications, allergies, imaging, problems, SDoH, and care-registry
data. Use supplementary endpoints (`/api/patients/{id}`, `/api/observations`,
`/api/allergies`, etc.) only when the case detail bundle is insufficient for
the task.

Always fetch protocols before making clinical decisions. Protocol bodies
contain `authoritative_statuses`, `controlled_codes`, threshold rules, and
branching logic that govern the assessment.

## Output Rules

- Return a single JSON object.
- Every required top-level key from the answer template must be present.
- Use null only where the template schema explicitly permits null.
- Use controlled enum values rather than free-text prose for scored status and
  action fields.
- Respect all numeric precision rules (integer vs decimal places).
- Do not include markdown, comments, or extra top-level keys.
