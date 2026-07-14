# ClinicProtocol Clinical Decision-Support Skill

## Overview

This skill covers protocol-driven clinical decision-support tasks served by the ClinicProtocol API. Each task provides patient/encounter/case identifiers and expects a single JSON answer object matching a supplied `answer_template.json`. The API exposes patients, encounters, observations, and protocol cards — all decisions are derived by applying the protocol's `local_rules` to the fetched data.

---

## API Reference

All paths are relative to the base URL from `environment_access.md`. The API is a custom Python HTTP server (`ClinicProtocolHTTP/1.0`). Only `GET` is supported; all endpoints return JSON.

### Endpoints

| Endpoint | Returns | Notes |
|---|---|---|
| `GET /api/patients` | `{"patients": [...]}` | Full patient list. Filter client-side by `patient_id`. |
| `GET /api/patients/{patient_id}` | `{"patient": {...}}` | Single patient. Use when you know the exact ID. |
| `GET /api/encounters` | `{"count": N, "encounters": [...]}` | Full encounter list. No individual-encounter endpoint exists. Filter client-side by `encounter_id` or `patient_id`. |
| `GET /api/observations` | `{"count": N, "observations": [...]}` | Full observation list (157+ records). No individual-observation endpoint. Filter client-side. |
| `GET /api/protocols/{protocol_id}` | `{"protocol": {...}}` | Protocol card. Always fetch by the exact `protocol_id` required by the task. |

There is **no** individual endpoint for encounters, observations, or cases. Always fetch the list and filter.

### Patient Record Structure

```json
{
  "patient": {
    "patient_id": "PAT-...",
    "identifier": "MRN-...",
    "name": {"family": "...", "given": "...", "text": "..."},
    "birth_date": "YYYY-MM-DD",
    "sex": "male|female",
    "address": {"line": "...", "city": "...", "state": "...", "postal_code": "..."},
    "phone": "...",
    "allergies": [{"substance": "...", "reaction": "...", "severity": "...", "category": "...", "status": "active|inactive"}],
    "active_problems": [{"code": "...", "display": "...", "recorded": "...", "status": "active|inactive"}],
    "medication_summary": [{"medication": "...", "category": "...", "status": "active|inactive"}]
  }
}
```

**Key fields for decisions:** `allergies` (check substance + severity for contraindications), `active_problems` (check `status` — `inactive` problems are stale and must NOT drive current decisions), `medication_summary` (check `category` for QT-risk, anticoagulant, polypharmacy signals; check `status`).

### Encounter Record Structure

```json
{
  "encounter_id": "ENC-...",
  "patient_id": "PAT-...",
  "clinician": "...",
  "kind": "urgent_care|same_day_clinic|telephone_triage",
  "reason": "...",
  "start": "ISO-8601",
  "status": "in-progress|finished",
  "timezone": "America/Chicago",
  "facts": {
    "symptoms": [...],
    "vitals": {"oxygen_saturation_room_air": N, "heart_rate": N, "respiratory_rate": N, "blood_pressure": "...", "temperature_f": N},
    "exam": {"lung": "...", "mental_status": "..."},
    "imaging": {"chest_xray": "..."},
    "neuro_exam": {"glasgow_coma_scale": N, "gait": "...", "focal_weakness": bool, "speech": "..."},
    "current_anticoagulant_use": bool,
    "current_qt_risk_medication": "...",
    "amnesia_minutes": N,
    "vomiting_episode_count": N,
    "loss_of_consciousness": "...",
    "reliable_observer": bool,
    "mechanism": "...",
    "stale_conflict": "...",
    "waiting_room_observation": "...",
    "walking_observation": "...",
    "headache_course": "..."
  }
}
```

**Key patterns:**
- `stale_conflict` — a note explaining that an old problem-list item is inactive and should not influence the current decision. Read it.
- The `facts` object varies by encounter type (head-injury vs respiratory have different shapes).
- `timezone` is consistently `America/Chicago` (UTC-05:00).

### Observation Record Structure

```json
{
  "id": "OBS-...",
  "patient_id": "PAT-...",
  "encounter_id": "ENC-...|null",
  "resourceType": "Observation",
  "status": "final|preliminary|entered-in-error|cancelled",
  "category": "laboratory|vital_signs|imaging|pulmonary_function|panel_header",
  "code": "K|4548-4|2823-3|...",
  "display": "...",
  "effectiveDateTime": "ISO-8601",
  "value": N|"...",
  "unit": "...",
  "interpretation": "low|high|critical-low|...",
  "panel_header": true|false,
  "notes": "..."
}
```

**Filtering rules (apply in this order):**
1. Match `patient_id` exactly — **beware near-miss IDs** (e.g., `PAT-L-T01` ≠ `PAT-L-T001`, `PAT-L-X01` ≠ `PAT-L-X001`). Observations linked to different-but-similar patient IDs are traps.
2. Match `code` exactly — a different LOINC/code is a different test, even if the display name is similar (e.g., LOINC `2823-3` ≠ local code `K`).
3. Require `status == "final"` — discard `preliminary`, `entered-in-error`, `cancelled`.
4. Require `panel_header == false` and `category != "panel_header"` — panel headers are not individual results.
5. For date-window queries: `effectiveDateTime` must fall within the window boundaries (inclusive of start and end of period).

### Protocol Card Structure

```json
{
  "protocol": {
    "protocol_id": "..._2026",
    "title": "...",
    "version": "2026.N",
    "effective": "YYYY-MM-DD",
    "local_rules": ["rule text...", "rule text..."],
    "outputs": { ... }
  }
}
```

**Key patterns:**
- `local_rules` is an array of natural-language sentences encoding decision thresholds, mappings, and exclusions. Parse each rule literally.
- `outputs` provides structured enums/values (allowed routes, test options, NDC codes, target values, etc.). Use these to constrain your answer to the valid set.
- Protocol IDs always end in `_2026`.

---

## General Workflow

### Step 1: Identify the Task Type

Read the task `prompt.txt`. Extract:
- **Patient ID(s)** — the subject of the decision
- **Encounter ID** (if provided) — the clinical encounter to review
- **Case ID** (if provided) — for care-management tasks
- **Protocol ID** — implied by the task domain (matches `primary_protocol` in the answer template)
- **Current time** — some tasks specify a clinical time; otherwise use encounter `start`
- **Answer template** — located at `input/payloads/answer_template.json`; this defines the exact output schema

### Step 2: Fetch All Relevant Data

Always fetch in parallel where possible:
1. `GET /api/protocols/{protocol_id}` — the protocol card
2. `GET /api/patients/{patient_id}` — the patient (use exact ID from the task)
3. `GET /api/encounters` — then filter for the target `encounter_id` or `patient_id`
4. `GET /api/observations` — then filter for the target `patient_id`

For care-management tasks without a direct case endpoint, the patient record and observations are the primary data sources. Filter observations for the linked patient.

### Step 3: Apply Protocol Rules to the Data

Parse each `local_rules` sentence. Map clinical findings (symptoms, vitals, exam, labs, problem list, allergies, medications) to the rules. The rules encode:
- **Thresholds**: numeric cutoffs (e.g., O2 < 92%, K < 3.5 mEq/L)
- **Combinations**: rule X triggers only when conditions A AND B are met
- **Exclusions**: "unless," "avoid," "do not" clauses
- **Mappings**: finding → action (e.g., repeated vomiting → urgent_ed)

### Step 4: Handle Distractors and Edge Cases

Critical traps to avoid:
- **Inactive problems**: A `status: "inactive"` problem is stale. Do not let it override current findings. Read any `stale_conflict` notes.
- **Wrong patient ID**: Observations with `patient_id` nearly matching the target (off by one character) are linked to different patients — exclude them.
- **Non-final status**: Only `status: "final"` observations count for clinical decisions.
- **Panel headers**: `panel_header: true` or `category: "panel_header"` — these are organizational, not individual results.
- **Wrong code system**: A LOINC code ≠ a local code, even for the same analyte. Match by the exact `code` field value specified in the protocol or query.
- **Stale/old values**: For "latest" or "most recent" queries, sort by `effectiveDateTime` descending among valid final observations, then take the first.

### Step 5: Build the Answer

Fill every `required_top_level_key` from the answer template. Conventions:
- **Enum fields**: Use exactly the string values from the template's `allowed` arrays.
- **List fields with `ordering: "sort_lexicographic"`**: Sort the values alphabetically using standard string comparison.
- **Numeric fields**: Match the specified type and precision (e.g., `{"type": "number", "precision": 1}` means one decimal place).
- **ISO-8601 timestamps**: Include the timezone offset (e.g., `2026-07-06T08:05:00-05:00`).
- **Boolean fields**: Use JSON `true`/`false`, not strings.
- **Object fields**: Include every `required` sub-key.

### Step 6: Construct Evidence IDs

`evidence_ids` is a lexicographically sorted list of resource identifiers that trace the decision. Include:
- The protocol ID (e.g., `HEAD_INJURY_2026`)
- The patient ID
- The encounter ID (if an encounter was reviewed)
- The case ID (if a case was reviewed)
- Every observation ID that was used as a decision input (the selected "latest" value, matched lab results, etc.)

Exclude observations that were filtered out (wrong status, wrong code, wrong patient, panel header). The list must be sorted alphabetically.

---

## Task-Specific Decision Rules

### Head-Injury Triage (`HEAD_INJURY_2026`)

**Red flags** — map encounter symptoms/observations to these enum values:
| Finding | Red Flag Enum |
|---|---|
| Vomited ≥ 2 times OR "repeated vomiting" | `repeated_vomiting` |
| "Hard to keep awake," "drowsy," "increasing drowsiness" | `increasing_drowsiness` |
| Headache described as "worsening" | `worsening_headache` |
| Seizure reported | `seizure` |
| Focal weakness on neuro exam | `focal_weakness` |
| Slurred speech | `slurred_speech` |
| Confusion | `confusion` |
| Amnesia > 30 minutes | `amnesia_gt_30_min` |
| Anticoagulant use = true | `anticoagulant_use` |
| Abnormal gait (not "steady") | `abnormal_gait` |
| Gait + coordination both abnormal | `abnormal_gait_coordination` (use only when BOTH are noted) |
| "Deteriorating mental status" | `deteriorating_mental_status` |

**Route determination:**
- `urgent_ed`: ANY red flag from the urgent set (repeated vomiting, worsening headache, seizure, focal weakness, slurred speech, increasing drowsiness, confusion, amnesia > 30 min, anticoagulant use, abnormal gait/coordination, deteriorating mental status)
- `same_day_clinic`: Low-risk symptoms needing clinician review but NO urgent red flag
- `home_observation`: NO red flags AND normal neuro exam AND reliable adult observer

**CT recommendation:**
- `urgent` when risk_level = `urgent_ed`
- `consider` when risk_level = `same_day_clinic` with persistent symptoms or unreliable observation
- `not_required` when risk_level = `home_observation`

**Disposition** maps directly from risk_level:
- `urgent_ed` → `send_to_ed_now`
- `same_day_clinic` → `same_day_clinic_followup`
- `home_observation` → `home_with_observation`

**Activity plan:**
- `urgent_ed`: school = `no_school_until_evaluated`, sports = `no_sports_until_cleared`, driving = `no_driving_until_symptom_free_cleared`
- `same_day_clinic`: school = `reduced_24_48h`, sports = `no_sports_until_cleared`, driving = `no_driving_until_symptom_free_cleared`
- `home_observation`: school = `routine_as_tolerated`, sports = `routine_as_tolerated`, driving = `routine_as_tolerated`

**Contraindicated actions:** Include `drive_self_home` for any non-home route, `same_day_return_to_play` for any head injury, `unsupervised_home_observation` when risk is above home_observation.

**Follow-up hours:** 24 for urgent/red-flag, 48–72 for same_day_clinic, 72 for home_observation.

### Respiratory Assessment (`RESP_ACUTE_2026`)

**Primary assessment** — based on symptoms + exam + imaging:
- `community_acquired_pneumonia`: fever + cough + (focal crackles OR chest x-ray infiltrate/consolidation)
- `ed_evaluation_required`: O2 < 92% on room air, OR confusion, OR hypotension, OR RR ≥ 24, OR pleuritic chest pain with hypoxia
- `viral_upper_respiratory_infection`: URI symptoms without pneumonia findings
- `copd_asthma_exacerbation`: wheeze without consolidation

**Severity factors** — check each against the encounter vitals/exam:
- `oxygen_below_92`: O2 < 92%
- `oxygen_92_to_94`: O2 92–94%
- `tachypnea`: RR ≥ 24
- `hypotension`: systolic BP < 90
- `confusion`: altered mental status
- `lobar_consolidation`: chest x-ray shows consolidation
- `focal_crackles`: lung exam notes crackles
- `pleuritic_pain`: symptoms include pleuritic chest pain

**Site of care:**
- `ed_evaluation`: O2 < 92% OR confusion OR hypotension OR (RR ≥ 24) OR (pleuritic pain + hypoxia)
- `outpatient_treatment`: O2 ≥ 92% AND no ED criteria AND pneumonia assessment
- `supportive_care`: viral URI without pneumonia, stable

**Antibiotic selection:**
1. Check allergies: `penicillin` allergy → avoid penicillin class. `sulfonamide` / `sulfa` allergy → avoid sulfonamide class.
2. Check QT-risk medications in `medication_summary` (look for `category: "qt_risk"`) or `current_qt_risk_medication` in encounter facts.
3. If QT risk is present: avoid macrolide (azithromycin) and fluoroquinolone classes → use `doxycycline` or `no_antibiotic_protocol`.
4. If no QT risk and no contraindications: choose per protocol outputs.
5. `no_antibiotic_protocol` for viral URI.

**Contraindicated antibiotic classes:** List all that apply based on allergies and QT risk. Check all of: `fluoroquinolone_qt_risk`, `macrolide_qt_risk`, `penicillin`, `sulfonamide`.

**Required tests:** Map clinical findings to test options from protocol `outputs.test_options`.

### Potassium Replacement (`POTASSIUM_REPLETION_2026`)

**Finding the latest potassium:**
1. Filter all observations for the patient.
2. Keep only `code == "K"` (the local code, NOT LOINC `2823-3`).
3. Keep only `status == "final"`.
4. Keep only `panel_header == false`.
5. Sort by `effectiveDateTime` descending; take the first.

**Replacement decision:**
- Target: 3.5 mEq/L (from protocol `outputs.target_mEq_per_L`)
- If `value_meq_l < 3.5`: `replacement_required = true`
- Dose: `ceil((3.5 - value) / 0.1) * 10` mEq, rounded up to the nearest 10 mEq (e.g., 3.2 → 30 mEq, 3.4 → 10 mEq)

**Medication order** (use the exact values when replacement is required):
- `drug`: `"potassium chloride oral repletion"`
- `ndc`: `"40032-917-01"` (from protocol `outputs.ndc`)
- `route`: `"oral"`
- `intent`: `"order"`

**Follow-up lab:**
- `loinc`: `"2823-3"` (from protocol `outputs.follow_up_loinc`)
- `display`: `"Serum potassium"`
- `occurrenceDateTime`: Next calendar day after the current clinical time, at 08:00 in the local timezone (America/Chicago = -05:00)
- `priority`: `"routine_next_morning"`

**Ignored observation IDs:** Every observation for this patient with code K that was NOT selected. This includes:
- Non-final status (preliminary, entered-in-error, cancelled)
- Wrong code (LOINC `2823-3` ≠ code `K`)
- Older final observations (valid but not the most recent)

### FHIR Lab Retrieval (`FHIR_LAB_RETRIEVAL_2026`)

**Query construction:** Use the resource type, code, and month from the task prompt.

**Matching algorithm:**
1. Filter observations by `patient_id == {target}`.
2. Filter by `code == {query.code}`.
3. Filter by `effectiveDateTime` within the query month (inclusive: first day 00:00:00 through last day 23:59:59).
4. Exclude: `status != "final"`, `panel_header == true`, `category == "panel_header"`.
5. Exclude: observations with near-miss patient IDs (linked to different patients).

**Excluded observation IDs:** List observations that matched the code but were excluded by status, panel_header flag, date range, or patient ID mismatch. Include every excluded observation ID — sorted lexicographically.

**Match fields:**
- `has_matching_lab`: `true` if at least one observation passes all filters
- `matched_observation_ids`: sorted lexicographically
- `matched_count`: count of matched IDs
- `first_match_date`: earliest `effectiveDateTime` among matches (date only, YYYY-MM-DD)
- `last_match_date`: latest `effectiveDateTime` among matches (date only, YYYY-MM-DD)
- `resource_type`: `"Observation"`
- `code_checked`: the `code` value from the query

### Complex-Care Escalation (`COMPLEX_CARE_2026`)

There is no separate case endpoint. Derive everything from the linked patient record and observations.

**Chart concerns** — map patient data to enum values:
- Parse `active_problems` for disease codes (DM2 → `uncontrolled_diabetes` if A1C is high, CKD4 → `ckd_stage_4`, COPD → `copd_exacerbation_risk`, HF → `heart_failure_recent_admission`, MDD/behavioral → `behavioral_health_history`)
- Count `medication_summary` entries with `status: "active"` — ≥ 5 → `polypharmacy`
- Check address and notes for SDoH flags: apartment/instability → `housing_instability`, food access mentions → `food_insecurity`, transportation mentions → `transportation_barrier`, utility mentions → `utility_risk`
- Look for gaps: missed follow-up patterns → `missed_nephrology_followup`, `missed_pulmonary_rehab`
- Check observations: A1C ≥ 9.0 → `uncontrolled_diabetes`, eGFR < 30 → `ckd_stage_4`
- Inhaler-related: if patient has respiratory medications → `inhaler_affordability`

**Risk level:**
- `high`: multiple uncontrolled chronic conditions, polypharmacy, behavioral health comorbidity, AND SDoH barriers (housing, food, transportation, utilities). Or explicit high-risk markers.
- `moderate`: some disease burden but fewer SDoH flags.
- `low`: well-controlled, minimal barriers.

**Program type:**
- `complex_care`: meets protocol threshold (registry score ≥ 0.75 implied by high-risk pattern, OR recent high-acuity admission + uncontrolled chronic disease)
- `routine_care_management`: moderate risk, needs coordination but not intensive
- `not_eligible`: low risk

**Assessment domains:** Derive from `chart_concerns` — each concern maps to a domain that needs confirmation with the member.

**Consent strategy codes:** Always include:
- `avoid_guarantees` (protocol explicitly forbids guaranteeing costs, rides, dialysis slots, assistance approval)
- `clear_voluntary_consent`
- `plain_language_condition_schedule`
- Add `permission_before_sensitive_topics` for behavioral health
- Add `reflect_first_refusal` when persona is initially reluctant
- Add `bounded_process_help`
- Add `plain_language_dialysis_schedule` if CKD is present

**Care plan problem set:** Map chart concerns → problem areas. Minimum 3 per protocol.

**Disciplines:** Select from the allowed enum based on clinical needs. Minimum 2. Always include `care_manager`.

**Follow-up cadence:** `weekly` for complex_care per protocol.

**Escalation triggers:** Select the triggers that match the patient's conditions (e.g., glucose extremes for diabetes, dyspnea/weight gain for HF, housing loss for housing instability, PHQ-9 item 9 for behavioral health, rescue inhaler overuse for COPD, missed follow-up for transportation barriers).

**`avoid_unsupported_guarantees`:** Always `true` per protocol rules.

---

## Output Conventions

1. **Single JSON object** — not an array, not newline-delimited JSON.
2. **All `required_top_level_keys` must be present** — even if the value is an empty list `[]` or `false`.
3. **List sorting**: Any field with `"ordering": "sort_lexicographic"` must be sorted alphabetically (standard string sort, case-sensitive). Sort before adding to the final object.
4. **Enum precision**: Use the exact string from the `allowed` array — no synonyms, no abbreviations.
5. **Timestamps**: ISO-8601 with timezone offset. Use the timezone from the encounter or `America/Chicago` (-05:00).
6. **Numbers**: Match the specified `precision` (number of decimal places). Integers must not have a decimal point.
7. **Null vs absent**: Never use `null` for required fields. Use `[]`, `false`, or `0` as appropriate.

---

## Common Pitfalls

1. **Using individual-resource endpoints that don't exist.** Only `/api/patients/{id}` and `/api/protocols/{id}` work for single resources. Encounters and observations are list-only — filter client-side.

2. **Following near-miss patient IDs.** Observations with `patient_id` one character off from the target (e.g., `PAT-L-T01` vs `PAT-L-T001`) are linked to different patients. Always exact-match `patient_id`.

3. **Trusting inactive problems.** A problem with `status: "inactive"` is historical, not current. Look for `stale_conflict` notes that explain why an old label should be disregarded.

4. **Confusing LOINC codes with local codes.** Potassium has both local code `K` and LOINC `2823-3`. The protocol specifies which code system to use — match exactly.

5. **Including non-final observations.** Only `status: "final"` matters for clinical decisions. Discard `preliminary`, `entered-in-error`, `cancelled`.

6. **Including panel headers.** A panel header (`panel_header: true` or `category: "panel_header"`) groups individual results but is not itself a result. Exclude it.

7. **Missing contraindications from QT-risk medications.** Check both `medication_summary` (for `category: "qt_risk"`) and encounter `facts.current_qt_risk_medication`. QT risk constrains antibiotic class choices.

8. **Not reading stale_conflict notes.** These explain why certain data (old COPD labels, inactive concussions) should not influence the current decision.

9. **Forgetting to sort lexicographically.** Every list field with `"ordering": "sort_lexicographic"` must be sorted. This includes `evidence_ids`, `red_flags_present`, `chart_concerns`, etc.

10. **Time zone errors.** The environment uses `America/Chicago` (-05:00). When computing follow-up times ("next calendar day at 08:00"), use this timezone. The `start` field on encounters is in local time.

11. **Case data has no dedicated endpoint.** For complex-care tasks, derive case-level decisions entirely from the linked patient record plus observations. Do not waste time searching for a `/api/cases/{id}` endpoint — it does not exist.

---

## Evidence ID Construction

`evidence_ids` traces every resource that substantiates the decision. Construct as follows:

1. Start with the protocol ID (e.g., `HEAD_INJURY_2026`).
2. Add the patient ID.
3. Add the encounter ID (if an encounter was reviewed).
4. Add the case ID (if a case was referenced in the task prompt).
5. Add every observation ID that was used as a decision input:
   - The selected "latest" potassium observation
   - Matched A1C observations within the query window
   - Vital-sign or imaging observations attached to the encounter
6. Sort the complete list lexicographically.

Do NOT include: observation IDs that were examined but excluded (wrong status, wrong code, wrong patient, panel header, outside date window). Those belong in `excluded_observation_ids` or `ignored_observation_ids` fields — not in `evidence_ids`.
