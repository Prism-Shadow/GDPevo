# Case-Type Playbook

Each task belongs to one of five case-type families. This file names, for each family, the case_type, the relevant protocol id, the key evidence slices, and the decision shape the template scores. It contains **no task-specific final values** (no patient ids, doses, scores, or chosen enum outcomes) — those are derived per run from the live case and protocol. Use it to know *which* protocol and *which* slices drive a task's enums.

Use the case_type from `GET /api/cases/{case_id}` (or the prompt) to pick the family.

---

## 1. Adult respiratory / CAP assessment
- **case_type:** `acute_respiratory`
- **Protocol:** fetch via `GET /api/protocols`, then `GET /api/protocols/{protocol_id}` for the CAP protocol (id shaped `RESP-CAP-<YEAR>`).
- **Key evidence:** case bundle `findings` (SpO₂ range, fever, cough, dyspnea, pleuritic pain, confusion, occupational exposure), `imaging` (CXR impression — consolidation/effusion/multilobar), `allergies` (active penicillin/sulfonamide screen), `observations` (vitals).
- **Decision shape:** `primary_assessment` (CAP vs viral URI vs pending), `risk_level` (low/moderate/high), `disposition` (outpatient close follow-up vs ED transfer), `red_flags` list, `recommended_tests` list (CXR-2V, viral PCR, pulse-ox recheck, CBC), `medication_plan` (allergy-aware antibiotic strategy + med/dose/route/frequency/duration + `avoid_allergens`), `stabilization_actions`, `follow_up` (hours + route), `return_precautions`, `evidence_ids`, `safety_checks` (`no_penicillin_or_sulfa`, `no_normal_cxr_claim`, `no_clear_lungs_claim`).
- **Watch for:** SpO₂ 92–93 vs <90 drives a specific red-flag enum and often the disposition; active penicillin/sulfa allergy forces a non–beta-lactam/sulfa strategy and sets `no_penicillin_or_sulfa` true.

## 2. Pediatric head injury triage
- **case_type:** `pediatric_head_injury`
- **Protocol:** pediatric head injury protocol (id shaped `PEDS-HEAD-<YEAR>`).
- **Key evidence:** case bundle `findings` (mechanism/impact, LOC, vomiting count, seizure, focal weakness, headache trajectory, basilar skull signs, photophobia, coordination symptoms, nausea), patient `age` (confirm pediatric), `imaging` if present.
- **Decision shape:** `primary_assessment`, `risk_tier` (low/intermediate/high), `disposition` (home observation vs ED/CT), `imaging_recommendation` (no immediate CT / CT-or-ED per protocol / urgent CT), `red_flags` list **and** `absent_red_flags` list (the template splits present vs absent — record absent ones explicitly, do not just omit them), `restrictions` (cognitive/physical rest, return-to-learn, sports/driving), `follow_up` (hours + route), `evidence_ids`, `safety_checks` (`no_false_loc`, `no_false_vomiting`, `no_false_photophobia`).
- **Watch for:** the absent-vs-present red-flag split is the main scoring axis; a false "present" on LOC/vomiting/photophobia flips a safety boolean false.

## 3. Potassium replacement + follow-up lab
- **case_type:** `potassium_repletion`
- **Protocol:** potassium replacement/escalation protocol (id shaped `K-REPLETION-<YEAR>`). The protocol body carries `controlled_codes` (serum potassium code `K`, follow-up lab LOINC, NDC, eGFR LOINC, ECG summary), `target_potassium_mmol_l`, `routine_dose_rule` (mEq per 0.1 mmol/L below target, rounding), `routine_follow_up` timing, and an `urgent_branch` (dialysis-dependent ESRD, ECG abnormality, K < threshold, severe renal contraindication, arrhythmia symptoms).
- **Key evidence:** `observations` filtered to `code:"K"`, `status:"final"`, latest in-window; renal function (eGFR) observation; ECG summary; case `findings` for `current_time`; contraindication flags (dialysis dependence, arrhythmia symptoms).
- **Decision shape:** `latest_potassium` (observation_id, value to one decimal, effective_time), `replacement_required` bool, `potassium_plan` enum (routine oral / none / urgent escalation / hold-for-contraindication), `oral_dose_mEq` (integer or null via the dose rule), `medication_order` (ndc/medication/route/frequency/status), `follow_up_lab` (LOINC + scheduled_time), `urgent_actions` list (clinician notification / EKG now / telemetry-or-ED, ordered by action sequence, `[]` if none), `contraindications` (dialysis_dependent, arrhythmia_symptoms, egfr integer-or-null), `evidence_ids` (descending relevance).
- **Watch for:** the urgent branch supersedes the routine dose rule — if any urgent criterion is met, plan is `urgent_escalation`, dose/med fields null where the spec permits, and `urgent_actions` is populated. `current_time` is a finding (`current_time`), not the wall clock.

## 4. Care-management routing
- **case_type:** care-management (target case id shaped `CASE-CM-*`)
- **Protocol:** high-risk care-management routing protocol (id shaped `CM-HIGH-RISK-<YEAR>`).
- **Key evidence:** case bundle + `care_registry`, `problems`, `medications` (active count), `sdoh` (transportation/financial/food/medication-access barriers, dialysis fatigue, care-goal preference), `observations` (HbA1c, phosphorus, BP, eGFR, risk score), recent admission / dialysis schedule facts.
- **Decision shape:** `risk_tier`, `program` (complex / routine / not eligible), `priority_problems` (each code at most once), `numeric_anchors` (risk_score 2dp, hba1c 1dp, phosphorus 1dp, blood_pressure "sys/dia", active_medication_count int), `referrals` (each at most once), `outreach_stance`, `care_plan_minima` (min_problem_count, weekly_follow_up, requires_member_stated_priority, min_disciplines), `escalation_conditions`, `source_provenance` (`chart_facts` vs `member_disclosure_needed` — split facts that come from the chart from those requiring member self-disclosure, e.g. SDOH barriers and care-goal preferences).
- **Watch for:** the `source_provenance` split — SDOH-derived barriers and care-goal preferences generally belong in `member_disclosure_needed`, not `chart_facts`. Numeric anchors must match each field's precision exactly.

## 5. Observation-window lab retrieval + protocol gate
- **case_type:** `observation_window`
- **Protocol:** observation-window interpretation protocol (id shaped `OBS-WINDOW-<YEAR>`). Defines the authoritative `status` (final), the target code (`K`), window semantics, and the gate mapping (recent final normal / low-repletion / critical-urgent / no-final-in-window).
- **Key evidence:** `observations` for the patient filtered by `code`, `status:"final"`, and `effective_time` within `[window.from, window.to)`; plus relevant distractor observations that are *excluded* (wrong date/code/status) for the `excluded_observation_ids` list.
- **Decision shape:** `window` {from, to} (ISO-8601 UTC), `target_code` (`K`), `lab_found` bool (≥1 final target-code obs in window for the patient), `matched_observation_ids` (sorted by effective_time asc then observation_id asc), `excluded_observation_ids` (relevant distractors, sorted by effective_time asc then observation_id asc), `latest_final` (nullable; required when `lab_found` true — observation_id, value to one decimal, effective_time), `protocol_gate` enum, `repeat_lab` {recommended bool, scheduled_time string-or-null}.
- **Watch for:** exclusions must be *relevant distractors* (same patient, plausibly related) that fail on date/code/status — not every other observation in the system. Sorting is strict and deterministic; ties broken by `observation_id` ascending. `lab_found` is false only when no qualifying final in-window observation exists, which forces `protocol_gate: no_final_lab_in_window`.

---

## Cross-cutting reminders
- Always confirm `case_type` from the case bundle; the same `case_type` is shared by distractors, so the case_id (not the type) selects the record.
- For every family, the protocol body is the source of truth for thresholds/codes/branches — read it before deciding enums.
- `current_time` and similar review timestamps come from the case `findings`, not the system clock.
- Evidence ids are real runtime ids (case/observation/imaging/protocol/finding source ids); copy them verbatim into `evidence_ids` per that field's ordering rule.
