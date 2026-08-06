---
name: clinic-protocol-decision-support
description: Solve synthetic clinic "protocol-bound decision support" tasks. Each task points at one case in a FHIR-like clinic runtime and asks for a single JSON object that conforms to a per-task answer template. Use this skill whenever a task asks you to review a clinic case (respiratory/CAP, pediatric head injury, potassium replacement, care-management routing, or observation-window lab retrieval) against a named protocol and return a structured JSON answer.
---

# Clinic Protocol Decision Support

## What these tasks are

Every task in this family has the same shape:

1. A **prompt** names a target case id (e.g. `CASE-<DOMAIN>-<NNN>`) and a clinical domain.
2. An **answer template** (`input/payloads/answer_template.json`) defines the exact JSON
   schema: required top-level keys, enums, allowed values, list-ordering rules, null rules,
   and numeric precision. The template is the contract — every scored field is enumerated there.
3. A **clinic runtime** (FHIR-like) holds the patient record, encounters, observations,
   imaging, allergies, medications, problems, care-registry, SDOH, and **protocol** material.
   The runtime access (base URL, endpoints, any credentials) is **listed separately for each
   run** — consult that file for the mechanics of calling the runtime. Do not assume a prior
   run's URL or token.

The deliverable is **one JSON object only** — no markdown, no prose, no extra top-level keys.

## Workflow

1. **Read the template first.** Before touching the runtime, read `answer_template.json`
   end-to-end. Note: required keys, enums + allowed values, which fields are `string_or_null`
   vs required, list-ordering rules, numeric precision, and any `expected_constant` /
   `required_value` fields (e.g. `task_id`, `case_id` are usually pinned). The template tells
   you exactly which evidence you must gather.
2. **Pull the case record** for the target case id from the runtime. A case record bundles:
   `case`, `patient`, `findings` (key/value clinical facts with `source_id`), `observations`,
   `imaging`, `medications`, `allergies`, `problems`, `sdoh`, and `care_registry`. This single
   record is usually sufficient; the global list endpoints are mostly distractors.
3. **Pull the matching protocol.** List protocols, then fetch the detail for the one whose
   scope matches the case type. The protocol body is authoritative — it carries the controlled
   LOINC/RxNorm codes, the `authoritative_statuses` (almost always `["final"]`), escalation
   thresholds, dosing rules, follow-up timing, and return-precaution codes. When the template
   and your clinical instinct disagree, **the protocol wins**.
4. **Reconcile data against rules** (see `references/decision_rules.md` for per-domain
   patterns). Apply protocol thresholds literally; do not round, soften, or escalate beyond
   what the protocol states.
5. **Build the JSON** to the template. Use exact enum strings, exact identifier strings copied
   from the runtime, the prescribed numeric precision, and the prescribed list ordering.
6. **Self-check** against `references/checklist.md` before submitting.

## Transferable rules (learned the hard way)

These apply across domains and are where points are lost:

### Observations
- **Final only.** Protocol `authoritative_statuses` is `["final"]`. Exclude `preliminary`,
  `canceled`, and `entered-in-error` observations from any "latest" or "matched" computation.
- **Code identity matters.** The protocol maps each concept to one controlled code. Serum
  potassium is code `K` ("in Serum or Plasma"). A whole-blood / point-of-care potassium
  (e.g. LOINC `6298-4`, "in Blood") is a **different code** and must be excluded even if final.
  Sodium (`NA`), eGFR, HbA1c, phosphate, etc. are all distinct codes — never substitute.
- **Patient identity matters.** Distractor observations for *other* patients are planted inside
  a case. Always filter on the target `patient_id`.
- **"Latest" = latest *final* target-code observation for the target patient**, by
  `effective_time`.

### Observation-window tasks
- Window `from` is **inclusive**, `to` is **exclusive** (the template states this). An
  observation exactly at `to` is out.
- `matched_observation_ids` = final + target code + target patient + inside window, sorted by
  `effective_time` ascending, then `observation_id` ascending.
- `excluded_observation_ids` = relevant distractors that fail to qualify **by date, code, or
  status** — these three reasons only. A **wrong-patient** observation is *not* listed in
  `excluded`; it is simply not relevant to this patient's review. (Including a wrong-patient id
  in `excluded` invalidates the whole set.) Sort excluded by `effective_time` ascending, then
  `observation_id` ascending.
- `protocol_gate`: pick from the enum based on the latest final value (normal →
  `satisfies_recent_final_normal`; low but not critical → repletion; critical/urgent →
  critical; none in window → `no_final_lab_in_window`).
- `repeat_lab`: when the gate is `satisfies_recent_final_normal`, no repeat is needed
  (`recommended: false`, `scheduled_time: null`). Reserve repeats for abnormal/urgent gates.

### Numeric dose & timing conventions
- Follow the protocol's `routine_dose_rule` literally: e.g. `mEq_per_0_1_mmol_l_below_target`
  with `round_to_nearest_mEq` — compute the deficit from `target_potassium_mmol_l`, multiply,
  then round to the stated nearest value.
- "Next morning" follow-up lab = **the next calendar day at 08:00 UTC** (e.g. review
  2026-02-10T10:15Z → `2026-02-11T08:00:00Z`). Use LOINC / NDC codes straight from the
  protocol's `controlled_codes`.
- Numeric precision in the template is exact: one decimal place means `3.2` not `3.20`; two
  decimals means `0.84`. Blood pressure is a string `"systolic/diastolic"` (e.g. `"152/88"`).

### Escalation & disposition
- Escalation thresholds come from the protocol (e.g. respiratory ED escalation at SpO2 < 90,
  RR ≥ 30, SBP < 90, plus listed "other red flags"). **Borderline values that don't cross a
  threshold do not escalate.** SpO2 92–93% is a red flag but not an ED transfer; disposition
  stays `outpatient_close_followup` and `stabilization_actions` stays empty (`[]`) unless a
  threshold is crossed. Do not add `supplemental_oxygen` for borderline-but-not-hypoxic rooms.
- Match `risk_level`/`risk_tier`/`disposition`/`imaging_recommendation`/`stabilization_actions`
  to each other — they are scored for internal consistency. An over-aggressive stabilization
  will also drag down disposition and follow-up.

### Allergies & medication plans
- Use **active** allergies only. Map allergens to the template's `avoid_allergens` enum
  (penicillin, sulfonamide, macrolide, tetracycline). "Sulfonamide antibiotics" → `sulfonamide`.
  Inactive allergies are ignored.
- Pick the antibiotic strategy the protocol supports for the allergy profile (e.g. CAP with
  penicillin + sulfa allergy → `doxycycline_outpatient`; avoid beta-lactam and sulfa classes).
  Set `medication`/`dose`/`route`/`frequency`/`duration_days` consistently with that strategy,
  or `null` where the template permits (e.g. supportive-care or ED-deferred strategies).

### Safety checks
- Safety-check booleans reward **not making false claims**. Only assert a symptom is
  **absent** when the record explicitly documents it as absent (e.g. LOC "absent", vomiting
  0 episodes, "no focal weakness"). For symptoms **never assessed** (e.g. photophobia not
  mentioned), do **not** list them as absent and keep the corresponding `no_false_*` check
  `true`.
- `no_normal_cxr_claim` / `no_clear_lungs_claim`: when imaging shows consolidation, never
  claim the CXR is normal or lungs are clear — set those checks `true` (you correctly avoid the
  false claim).

### Lists that are "sets"
- Where the template says ordering is not meaningful, the evaluator normalizes lists as sets.
  But a set is scored strictly: one wrong element (extra or missing) can zero the whole field.
  Select exactly the codes the protocol/data support — no "just in case" extras.

### evidence_ids
- Follow the per-task ordering rule. Head-injury: case id first, then clinical source ids.
  Potassium: "main observation, renal-function, and case evidence in descending relevance"
  (latest K obs, then renal/eGFR, then case id). Use real `source_id` / `observation_id` /
  `imaging_id` strings from the runtime.

### Care-management routing
- Map each chart fact and disclosure to the **specific** priority-problem / referral code the
  protocol intends. Distinguish near-synonyms by case context: e.g. diastolic HF (HFpEF) with a
  volume-overload admission → `hfpEF_post_volume_overload`; a systolic-HF post-admission case
  → `heart_failure_recent_admission`. Don't select both for one case.
- Referrals are triggered by protocol rules: pharmacist (≥10 active meds, insulin, high-risk
  diuretic/electrolyte regimen), social_worker (≥2 moderate/severe SDOH domains among
  transportation/financial/food/housing), dialysis_care_coordination (ESRD on dialysis),
  transportation_benefits (transportation barrier). Do not add `behavioral_health_monitoring`
  for a mild PHQ-9 screen unless the protocol threshold is met.
- `outreach_stance`: `permission_based_plain_language` when the member is reluctant/refusing
  or when permission-based outreach is explicitly still required despite engagement.
- `source_provenance.chart_facts` = objective registry/lab/vital facts (risk_score, hba1c,
  phosphorus, blood_pressure, active_medication_count, recent_admission, dialysis_schedule,
  egfr *only if an eGFR value exists*). `member_disclosure_needed` = member-stated barriers and
  preferences (transportation_barrier, financial_food_barrier, dialysis_fatigue,
  care_goal_preference). Care-manager-noted facts (e.g. housing from a CM note) are not
  "member-disclosed."

## References
- `references/decision_rules.md` — per-domain decision patterns (respiratory, head injury,
  potassium, care management, observation window).
- `references/checklist.md` — pre-submit verification checklist.
- `references/data_model.md` — shape of the runtime case record and protocol body so you know
  what to extract.
