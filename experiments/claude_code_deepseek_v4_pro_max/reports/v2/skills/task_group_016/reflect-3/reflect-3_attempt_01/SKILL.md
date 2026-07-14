# ClinicProtocol Decision Support — Task Group Skill

## Overview

This skill covers protocol-driven clinical decision-support tasks served through a ClinicProtocol HTTP API. Every task requires fetching structured patient, encounter, observation, protocol, and/or case-management data from the API, applying protocol rules to that data, and returning a single JSON answer object whose shape is defined by a staged `answer_template.json`.

## Workflow

### Phase 1 — Gather all relevant data

Before reasoning about any decision, fetch every piece of data the API offers for the task's entities:

1. **Fetch the protocol(s).** `GET /api/protocols` returns every available protocol with its `protocol_id`, `local_rules` (natural-language decision rules), and `outputs` (allowed enum values, thresholds, codes). Read the rules for the protocol named in the task prompt — they are the ground truth for every decision field.

2. **Fetch the patient.** `GET /api/patients/{patient_id}` returns demographics, active problems, allergies (substance, reaction, severity), and medication summaries. Note which problems are `active` vs `inactive` — inactive problems should not drive current decisions unless the protocol explicitly says otherwise.

3. **Fetch the encounter (when applicable).** `GET /api/encounters?patient_id={patient_id}` returns the encounter object. Key sub-structures:
   - `facts.symptoms` — presented symptoms
   - `facts.vitals` — vital signs (BP, HR, O2 sat, RR, temp)
   - `facts.exam` — physical exam findings
   - `facts.neuro_exam` — neurological exam (GCS, gait, speech, focal weakness)
   - `facts.mechanism` — injury mechanism for trauma protocols
   - `facts.current_anticoagulant_use` / `facts.current_qt_risk_medication` — medication risk flags
   - `start` / `timezone` — encounter timing
   - `status` — encounter state

4. **Fetch observations.** `GET /api/observations?patient_id={patient_id}` returns all Observation resources. Filter carefully (see Observation Filtering Rules below).

5. **Fetch care cases (when applicable).** `GET /api/care_cases` returns all care-management cases with risk scores, chart concerns, recent admissions, SDoH flags, member persona, and service context.

### Phase 2 — Apply protocol rules

Read every `local_rule` in the protocol and map it to the concrete data. The rules are written in plain English but are mechanically precise:

- **Risk/severity routing rules** use pattern: `"<route> when <condition>"` — if the condition matches the patient+encounter data, that route applies.
- **Treatment selection rules** describe which options are available and which are contraindicated by allergy or drug interaction.
- **Calculation rules** give exact formulas with rounding behaviour.
- **Exclusion rules** tell you what to ignore (panel headers, preliminary status, linked-but-different patients, stale data, inactive problems).

Always prefer the most recent data point. When a protocol says "most recent final," sort by `effectiveDateTime` descending within the filtered set and take the first.

### Phase 3 — Build the answer object

Start from the staged `answer_template.json`. Every field marked `required` must be present. Enum fields must use one of the listed `allowed` values exactly. List fields marked `"ordering": "sort_lexicographic"` must be sorted with standard string comparison.

Fill fields in this order:
1. Identifiers (`case_id`, `patient_id`, `primary_protocol`)
2. Single-value decision fields (`risk_level`, `primary_assessment`, `site_of_care`, etc.)
3. List fields (derive from data, then sort)
4. Nested objects (`activity_plan`, `medication_order`, `follow_up_lab`, `query`, `latest_potassium`)
5. `evidence_ids` — always last, after the decision is complete

## Observation Filtering Rules

When a protocol or task references Observation resources, apply these filters in order:

1. **Exact patient match.** `patient_id` must equal the target patient exactly. Records for linked/similar patients (e.g. `PAT-L-T01` vs `PAT-L-T001`) are **not** matches and should not appear in `matched_observation_ids` or `excluded_observation_ids` for the target patient query.

2. **Exact code match.** The Observation `code` must match the protocol's expected code (e.g. local code `"K"` for potassium, LOINC `"4548-4"` for A1c). Observations with different codes were never candidates — they do not belong in `excluded_observation_ids`.

3. **Final status only.** Only `"status": "final"` counts as a valid result. Reject `"preliminary"`, `"entered-in-error"`, and `"cancelled"`.

4. **Exclude panel headers.** Observations with `"panel_header": true` are structural containers, not results.

5. **Date-window matching.** When a month or date range is specified, match using `effectiveDateTime`. A month window includes all instants from the first day at 00:00:00 through the last day at 23:59:59 in the encounter's local timezone.

6. **Stale vs. current.** Prefer the most recent observation by `effectiveDateTime`. An observation that is final and code-correct but older is still valid — it just isn't the *most recent*.

### What goes in `ignored_observation_ids` vs `excluded_observation_ids`

- **`ignored_observation_ids`** (potassium-style tasks): Every observation returned for the patient that was *reviewed but not selected* as the primary data point. Include wrong-status, wrong-code, and stale observations. Sort lexicographically.

- **`excluded_observation_ids`** (FHIR retrieval tasks): Only observations that *could have matched* (same patient, same code) but were rejected for a specific reason: wrong month, non-final status, or panel header. Do **not** include observations with a different code or from a different patient — those were never candidates for the query.

## Enum Selection Guidelines

### Diagnosis vs. Disposition

When a template has separate fields for clinical assessment and care site (e.g. `primary_assessment` and `site_of_care`), use the clinical diagnosis for the assessment field and the routing decision for the site field. A patient can have `community_acquired_pneumonia` as the diagnosis AND `ed_evaluation` as the site of care — these are independent axes.

### List fields — include only what the data supports

When populating a list field from an enum, include an item only when there is explicit evidence in the patient/encounter/case data. Do not add items "just to be safe" or because they seem generally applicable. Every list item must trace back to a specific data point or protocol rule.

### Allergy and drug-interaction cross-referencing

When a protocol says "avoid X class with Y allergy" or "avoid X when QT-risk medication is active":
- Check `patient.allergies[].substance` for the allergen.
- Check `encounter.facts.current_qt_risk_medication` or `patient.medication_summary` for QT-prolonging drugs.
- Only flag a class as contraindicated when there is a **documented** allergy or interaction. Do not add a contraindication without evidence.

## Evidence ID Conventions

`evidence_ids` is a sorted list of strings that identifies the stable data points supporting the decision. These are typically Observation `id` values from the API responses.

Rules:
- Include the observation(s) whose values directly drove the decision (e.g. the potassium result that determined the dose, the A1c and eGFR that confirmed uncontrolled disease).
- Sort lexicographically.
- Do not include encounter IDs, case IDs, or protocol IDs here — use only Observation `id` strings.
- If no observations exist for the patient, the list may need to include encounter-fact-derived identifiers or be empty — check the protocol's `outputs` for guidance.

## Common Pitfalls

1. **Inactive problems masquerading as active.** Always check `problem.status`. An inactive concussion from 2023 is not relevant to a 2026 head injury. An inactive outside-COPD label does not make the patient a COPD patient.

2. **Linked-patient confusion.** The API may return patients with near-identical IDs (e.g. `PAT-L-T001` and `PAT-L-T01`). Observations for the linked patient must not be attributed to the target patient. The name, birth date, and MRN are hints — but the `patient_id` field is authoritative.

3. **Stale-conflict notes.** Encounters and observations may carry notes like `"Stale normal potassium"` or `"stale_conflict": "Old concussion problem is inactive..."`. Trust these annotations — they explicitly flag data that should not drive the current decision.

4. **Rounding in dose calculations.** When a protocol says "rounded up to the next 10 mEq," apply ceiling division: `ceil((target - value) / step) * dose_per_step`. A value already at a multiple of the rounding unit stays there (30 remains 30 when rounding up to next 10).

5. **Over-including in list fields.** Adding extra enum values that seem "reasonable" but lack explicit evidence lowers accuracy. Every list entry needs a specific data source or protocol rule citation.

6. **Timezone assumptions.** Encounter `start` times and observation `effectiveDateTime` values include timezone offsets. Follow-up timing ("next calendar day at 08:00") must use the encounter's local timezone, not UTC.

7. **Sort order.** Fields marked `"ordering": "sort_lexicographic"` use standard string sort (ASCII/Unicode codepoint order). Sort only after building the complete list.

## Decision-Specific Patterns

### Head-injury triage

- Map symptoms to red flags literally. `"vomited twice"` with `vomiting_episode_count: 2` = `repeated_vomiting`. Drowsiness that progressed to "hard to keep awake" = `increasing_drowsiness`.
- Risk routes upward: any single red flag → `urgent_ed`. Only when zero red flags AND normal neuro exam AND reliable observer → `home_observation`.
- CT follows risk: `urgent` for urgent_ed, `consider` for same_day_clinic, `not_required` for home_observation.
- Follow-up hours: 24 for urgent/red-flag, 48-72 for clinic, 72 for home.
- Activity restrictions follow the protocol's explicit prohibitions (no same-day return to play, no driving with symptoms, school pending evaluation for urgent cases).

### Respiratory assessment

- Primary assessment is the clinical diagnosis. Site of care is the disposition. They can differ.
- Contraindicated antibiotic classes come from TWO sources: allergies (penicillin allergy → penicillin class) AND drug interactions (active QT-risk medication → macrolide and fluoroquinolone classes). Do not add a class without evidence for either.
- Severity factors include exam findings (focal crackles), imaging results (lobar consolidation/infiltrate), vital-sign thresholds (O2 below 92, tachypnea), and symptoms (pleuritic pain).

### Potassium replacement

- Filter to the local code (e.g. `"K"`), not LOINC, for dose selection.
- Ignore entered-in-error, preliminary, wrong-code, and older observations — all go in `ignored_observation_ids`.
- Dose formula: `dose_meq = ceil((target - current_value) / 0.1) * 10`, then round up to next 10 if not already a multiple.
- Follow-up lab uses the LOINC code from the protocol's `outputs`, with `occurrenceDateTime` set to the next calendar day at 08:00 in the encounter timezone.

### FHIR lab retrieval

- Match on exact patient ID AND exact code.
- Month windows are inclusive: first day 00:00:00 to last day 23:59:59.
- `excluded_observation_ids` only contains same-code, same-patient observations rejected for status, date, or panel_header reasons — not observations with different codes or from linked patients.
- `first_match_date` and `last_match_date` are `YYYY-MM-DD` extracted from the earliest and latest matching `effectiveDateTime`.

### Complex-care escalation

- Risk level: map the registry risk score and admission history to the protocol thresholds. Score ≥ 0.75 with multiple high-acuity admissions → `high`.
- Program type: `complex_care` when risk score ≥ 0.75 OR (recent high-acuity admission + uncontrolled chronic disease).
- Chart concerns come from the case's `chart_concerns` array AND the patient's active problems AND SDoH flags — but only include items that map to the template's enum.
- Assessment domains must be grounded in chart or referral cues — do not add domains for conditions the patient doesn't have.
- `consent_strategy_codes` for an `initially_refuses` persona: include `reflect_first_refusal`, `avoid_guarantees`, and permission-based approaches. Only include `plain_language_dialysis_schedule` when dialysis is actually part of the patient's treatment.
- Escalation triggers: only conditions actually at risk. Don't add housing-loss triggers without housing instability evidence.
- `avoid_unsupported_guarantees` is always `true` for complex-care programs.
