# Synthetic Clinic Protocol-Driven Decision Support

Solve structured clinical decision-support tasks against a synthetic clinic runtime.
Each task supplies a case identifier, an answer template with controlled enum values, and access to a FHIR-like REST API plus protocol documents.

## Step 1 — Retrieve the case bundle

Call `GET /api/cases/{case_id}`. The response bundles the case metadata, patient demographics, findings, observations, imaging, medications, allergies, problems, care-registry entries, and SDOH records in a single payload so you rarely need separate entity lookups.

## Step 2 — Retrieve the relevant protocol

List protocols with `GET /api/protocols`, then fetch the target protocol with `GET /api/protocols/{protocol_id}`.

Protocol documents define:
- `authoritative_statuses` — which observation statuses count (almost always `["final"]`)
- `controlled_codes` — the exact observation codes to match
- Clinical decision thresholds (e.g. oxygen saturation cutoffs, potassium targets, risk-score minima)
- Medication rules (NDC codes, dose formulas, allergen-avoidance rules)
- Follow-up timing and escalation triggers

## Step 3 — Filter observations with surgical precision

**Status filtering**: Exclude every observation whose `status` is not in the protocol's `authoritative_statuses`. Common distractor statuses are `preliminary`, `entered-in-error`, and `canceled`.

**Code matching**: Only observations whose `code` equals a protocol `controlled_codes` value are candidates. Ignore observations with near-miss codes (e.g. whole-blood potassium `6298-4` when the protocol specifies serum potassium `K`; sodium `NA` when the target is potassium).

**Patient matching**: Verify `patient_id` on every candidate observation. The case payload may contain observations belonging to other patients — exclude them.

**Date-window boundaries**: When a task defines an inclusive-start / exclusive-end window, apply it exactly. Observations with `effective_time` before the start or at/after the end do not qualify.

**Ordering for array fields**: When the template prescribes an ordering (e.g. "Sort by effective_time ascending, then observation_id ascending"), produce exactly that ordering. When it says "No semantic ordering is required; evaluators normalize this as a set", any order is acceptable.

## Step 4 — Map clinical findings to controlled enum values

Every scored field in the answer template has a fixed set of allowed values. Map findings to enums mechanically:

- Read the `finding_key` and `finding_value` from the findings array.
- Cross-reference against the protocol's triggers, thresholds, and rules.
- Prefer protocol-defined mappings over clinical intuition. For example, if the protocol says "oxygen saturation below 90% triggers ED escalation" and the patient's SpO2 is 92%, do **not** flag ED escalation — use the exact protocol threshold.
- When a finding clearly matches an enum value (e.g. `finding_key: "pleuritic_chest_pain"` → `"pleuritic_chest_pain"`), use it.
- When a finding is explicitly absent (value is "absent" or "none"), list it under `absent_red_flags` (or the equivalent absent/negative field), not under present flags.

## Step 5 — Compute protocol-driven numeric outputs

Follow dose formulas, risk-score thresholds, and target values exactly as stated:

- **Dose calculations**: Apply the formula (e.g. `mEq = round((target - current) / step × mEq_per_step)`) and respect the rounding rule (e.g. "round to nearest 10 mEq").
- **Risk tiers**: Compare the patient's numeric values against protocol thresholds (e.g. risk_score ≥ 0.75 → high risk).
- **Numeric precision**: Match the template's declared precision (e.g. `"precision": "one decimal place"` means `3.2`, not `3.20`; `"precision": "two decimal places"` means `0.84`).
- **Integer vs float**: When the template says `"type": "integer"`, output a whole number.

## Step 6 — Build the medication plan

- Check active allergies first; include the implicated allergen classes in `avoid_allergens`.
- Select an antibiotic strategy / medication that avoids all active allergens.
- Use the protocol's NDC code when one is provided.
- When the protocol says "defer to ED" or "no medication recommended", set medication name, dose, route, frequency to `null` and use the corresponding strategy enum.

## Step 7 — Collect evidence identifiers

Gather stable identifiers from the sources you consulted and include them in `evidence_ids`:
- The case identifier
- Visit / encounter identifiers
- Observation identifiers for key labs and vitals
- Imaging identifiers
- Protocol identifiers
- Registry / care-registry identifiers when applicable

## Step 8 — Set safety-check booleans

Safety checks are boolean assertions confirming that certain findings were **not** falsely claimed. For each check:
- If the corresponding finding is truly absent in the record → `true`
- If it was falsely reported → `false`

## Step 9 — Validate the answer before submission

Before submitting:
1. Every required top-level key from the answer template is present.
2. Every enum field uses an exact allowed value (no synonyms, no abbreviations).
3. Arrays follow the prescribed ordering rules.
4. `null` appears only where the field specification explicitly permits it.
5. No extra top-level keys are present.
6. Timestamps use ISO-8601 UTC format with trailing `Z`.
7. The response is a single JSON object with no markdown, comments, or surrounding prose.

## Common pitfalls

- **Preliminary results**: A preliminary observation with the right code and patient is still excluded — status must be `final`.
- **Wrong-patient observations**: The case payload may bundle observations from multiple patients for realism. Always match `patient_id`.
- **Near-miss codes**: A "Potassium in Blood" (code `6298-4`) is not the same as "Potassium in Serum" (code `K`). Match the exact protocol code.
- **Boundary conditions**: "Exclusive end" means an observation at exactly `window.to` is excluded.
- **Allergy blind spots**: Even inactive allergies may be relevant if the template asks for a complete `avoid_allergens` list. Check the template's intent.
- **Protocol scope**: Use only the protocol rules provided for the task. Do not import external clinical guidelines.
