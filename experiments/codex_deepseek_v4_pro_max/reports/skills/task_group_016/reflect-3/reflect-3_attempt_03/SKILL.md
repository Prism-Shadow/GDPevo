## When to use

Use this skill when tasked with answering structured clinical decision-support questions backed by a synthetic clinic FHIR-like REST API. The environment exposes patient records, observations, medications, allergies, problems, imaging, care registries, SDOH data, and clinical protocols through GET endpoints and a read-only SQL query interface.

## Core workflow

1. Identify the target `case_id` and the `task_id` from the prompt.
2. Retrieve the case record via `GET /api/cases/{case_id}`. This returns the case metadata, patient info, findings, observations, medications, allergies, imaging, problems, care registry entries, and SDOH data in one payload. Prefer this endpoint over assembling data piecemeal.
3. Look up applicable protocols through `GET /api/protocols` and `GET /api/protocols/{protocol_id}`. Protocol bodies define thresholds, exclusion criteria, escalation rules, medication codes (NDC, LOINC), and follow-up recommendations.
4. Cross-reference any ambiguous data with `POST /api/query` using a `SELECT` over public tables when needed. Always include the `X-Clinic-Token: synclinic-readonly` header.

## Observation status discipline

Every protocol declares an `authoritative_statuses` list — typically `["final"]`. Treat any observation whose `status` is not in that list as non-authoritative for decision making:
- `preliminary` results must be excluded from protocol gates, dose calculations, and window matching.
- `entered-in-error` and `canceled` results carry no clinical weight.

## Observation code matching

Protocols define `controlled_codes` that map clinical concepts (e.g., `"serum_potassium": "K"`) to the exact `code` string used in Observation resources. An observation with the wrong `code` value is a distractor regardless of `display` text or interpretability:
- A whole-blood potassium (`code: "6298-4"`) is not a serum potassium (`code: "K"`) and does not satisfy a serum-potassium protocol gate.
- A sodium observation (`code: "NA"`) does not match a potassium target code.

## Patient-scoping rule

An observation whose `patient_id` does not match the target patient must be excluded entirely — do not place it in `excluded_observation_ids` or any other answer list. Only observations belonging to the target patient can be matched or excluded on grounds of date, code, or status.

## Observation window retrieval

When a protocol defines a time window with inclusive-start / exclusive-end semantics:
- Include observations whose `effective_time` falls inside the window boundaries and whose `patient_id`, `code`, and `status` all match the protocol requirements.
- Sort matched observations by `effective_time` ascending, then by `observation_id` ascending as a tiebreaker.
- Sort excluded (same-patient) observations the same way.
- The `latest_final` is the matched observation with the greatest `effective_time`.

## Protocol gate selection

Gate values encode the clinical decision derived from the latest qualifying observation:
- Compare the observation value against numeric thresholds in the protocol body (e.g., `target_potassium_mmol_l`, `potassium_less_than`).
- If no qualifying observation exists in the window, select the `no_*_in_window` variant.
- Do not let historical problems (e.g., hypokalemia history) override the numeric value of the current observation.

## Medication allergy safety

Always retrieve the patient's active allergies from the case or patient endpoint. When recommending medications:
- Cross every candidate drug class against the active allergy list.
- Record the avoided allergen classes in any `avoid_allergens` field.
- Inactive allergies (e.g., historical reactions marked `inactive`) do not constrain prescribing.
- Prefer drug classes with no overlap with active allergies when multiple strategies are protocol-eligible.

## Protocol arithmetic

When a protocol specifies a dose-calculation rule:
- Compute the difference between the target and the latest eligible observation value.
- Apply the per-unit multiplier exactly (e.g., `mEq_per_0_1_mmol_l_below_target`).
- Round to the stated granularity (`round_to_nearest_mEq`).
- Only apply routine-dose rules when the urgent/contraindication branch has been evaluated and found false.

## Urgent-branch evaluation

Protocol urgent/escalation branches are Boolean AND/OR gates over discrete triggers. Evaluate each trigger against the patient record:
- Numeric comparisons: use the latest authoritative observation value (not preliminary).
- ECG abnormality: check the ECG interpretation text for arrhythmia, U-waves, or acute changes.
- Symptom list: the absence of listed symptoms in the clinical note is sufficient to clear the trigger (do not infer symptoms from lab values alone).
- Renal contraindication: use the most recent eGFR observation. Mildly low eGFR (e.g., 64) without dialysis dependence does not activate severe renal contraindication gates alone.

## Evidence ID ordering

When listing evidence identifiers, order by clinical relevance: the key observation(s) first, then supporting labs/vitals, then the case identifier, then the protocol identifier. The exact order is less important than including the right set of identifiers, but use stable, reproducible ordering.

## Safety-check booleans

Safety-check objects guard against dangerous misstatements. Set each boolean to `true` when the corresponding false claim is indeed avoided:
- `no_penicillin_or_sulfa`: true when the medication plan avoids both penicillin and sulfonamide classes.
- `no_normal_cxr_claim`: true when the assessment does not describe the chest x-ray as normal.
- `no_clear_lungs_claim`: true when lung findings (consolidation, infiltrate) are acknowledged.
- `no_false_loc`, `no_false_vomiting`, `no_false_photophobia`: true when the corresponding symptom is genuinely absent in the record.

## General data-access patterns

- The `/api/cases/{case_id}` endpoint is the richest single source; it nests patient demographics, problems, allergies, medications, observations, imaging, findings, care-registry, and SDOH data.
- The `/api/patients/{patient_id}` endpoint returns patient-level data (demographics, problems, allergies, medications, SDOH) without case-specific findings or observations.
- The `/api/protocols/{protocol_id}` endpoint returns the full protocol body including controlled codes, thresholds, exclusion statuses, escalation rules, and follow-up instructions.
- Use `POST /api/query` with `SELECT * FROM <table> WHERE <condition>` only when the structured endpoints do not expose the needed cross-entity view. Prefer REST endpoints for standard retrievals.
- All GET endpoints and the query endpoint require the header `X-Clinic-Token: synclinic-readonly`.

## Output rules

- Return only the JSON object conforming to the answer template. No narrative text, markdown fences, or explanatory prose outside the JSON.
- Use exactly the enum values listed in the template's `allowed_values` arrays. Do not invent or paraphrase values.
- Use `null` only where the field specification permits it (e.g., nullable dose when no medication is recommended).
- For list-type fields whose ordering is described as "not meaningful," any permutation is accepted; nevertheless, choose a stable, repeatable order.
- Do not include extra top-level keys beyond those declared in the template's `required_keys` or `required_top_level_keys`.
- Boolean fields must be JSON booleans (`true`/`false`), not strings.
