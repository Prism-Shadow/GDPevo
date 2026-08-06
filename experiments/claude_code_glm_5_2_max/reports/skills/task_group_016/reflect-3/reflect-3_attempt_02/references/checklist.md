# Pre-Submit Checklist

Run through this before emitting the final JSON. Every item below has cost points in practice.

## Schema
- [ ] Every `required_top_level_keys` field is present; no extra top-level keys.
- [ ] `task_id` / `case_id` match the template's `expected_constant` / `required_value`.
- [ ] `patient_id` is the target patient from the case record (not a distractor).
- [ ] Every enum value is copied verbatim from the template's `allowed_values`.
- [ ] `null` used only where the field spec permits (`string_or_null`, `integer_or_null`,
      nullable objects); required fields are never null.
- [ ] Numeric precision matches the template (1 dp, 2 dp, whole hours/days, integer counts).
- [ ] Lists follow the prescribed ordering rule; sets have no duplicates.

## Observation filtering
- [ ] Only `final` observations used for "latest" / "matched" / protocol gates.
- [ ] Target concept code matched exactly (e.g. serum K = `K`, not whole-blood `6298-4`;
      not `NA`).
- [ ] Filtered to the target `patient_id` (no wrong-patient distractors).
- [ ] Window boundaries respected: `from` inclusive, `to` exclusive.
- [ ] `excluded_observation_ids` contains only date/code/status disqualifications —
      **no wrong-patient ids** — sorted by effective_time then observation_id.

## Clinical consistency
- [ ] Escalation fields (`risk_level`/`disposition`/`imaging_recommendation`/
      `stabilization_actions`/`urgent_actions`) are mutually consistent and driven by protocol
      thresholds, not by clinical caution alone.
- [ ] Borderline values that don't cross a threshold do not escalate (e.g. SpO2 92–93% →
      outpatient, empty stabilization_actions).
- [ ] Allergy plan avoids active allergen classes; `avoid_allergens` lists active classes only.
- [ ] Dose computed from the protocol's `routine_dose_rule` with correct rounding.
- [ ] Follow-up timing/LOINC/NDC taken from the protocol's `controlled_codes` / timing fields;
      "next morning" = next day 08:00 UTC.

## Safety checks
- [ ] `absent_red_flags` lists only symptoms explicitly documented as absent.
- [ ] Unassessed symptoms (e.g. photophobia) are NOT claimed absent; `no_false_*` booleans true.
- [ ] `no_normal_cxr_claim` / `no_clear_lungs_claim` true when imaging is abnormal.
- [ ] `no_penicillin_or_sulfa` true when the medication plan avoids those classes.

## Evidence
- [ ] `evidence_ids` use real `source_id` / `observation_id` / `imaging_id` strings.
- [ ] Ordering matches the template's rule (case id first for head injury; descending relevance
      for potassium).

## Output
- [ ] Output is exactly one JSON object — no markdown fences, no comments, no trailing prose.
