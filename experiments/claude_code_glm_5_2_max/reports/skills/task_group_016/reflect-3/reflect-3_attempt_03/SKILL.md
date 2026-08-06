---
name: clinic-protocol-cds
description: Solve synthetic clinic protocol decision-support tasks — retrieve a case + protocol from the clinic runtime, apply the protocol's rules to derive a single structured JSON answer that conforms to the task's answer template. Use for tasks that name a clinic case id (CASE-...) and a runtime environment, ask for a protocol-bound assessment / decision-support / routing / lab-window result, and require a JSON object matching a provided answer_template.json.
---

# Clinic Protocol Decision-Support

These tasks give you a **case id** (of the form `CASE-...`), a **clinic runtime environment** (access details are provided separately for each run), and an **answer template** (`input/payloads/answer_template.json`). Your job is to return **exactly one JSON object** that conforms to the template, derived by applying the matching **protocol** to the case data.

## Core procedure

1. **Read the prompt and template first.** Identify the target `case_id`, the required top-level keys, every field's type/enum/allowed values, nullability, precision, and any ordering rules. The template is the contract — every enum value, key name, and precision note is enforced.
2. **Fetch the case record** from the runtime environment: the case detail endpoint returns the case, patient, `findings`, `observations`, `imaging`, `medications`, `allergies`, `problems`, `sdoh`, and `care_registry` together. Do not call piecemeal endpoints when the bundled case view exists.
3. **Fetch the matching protocol.** The protocols list shows protocol ids; pick the one whose scope matches the case type (respiratory/CAP, pediatric head injury, potassium repletion, care-management routing, observation-window). The protocol body holds the authoritative rules and controlled codes.
4. **Derive each field from the protocol + case data**, not from generic clinical memory. The protocol is the source of truth for thresholds, codes, dose formulas, follow-up timing, and gates.
5. **Emit exactly one JSON object** — no markdown, no comments, no extra top-level keys, no prose. Use `null` only where the template explicitly permits it.

## How to read the case record

- **`findings`** is the ground-truth clinical narrative. Each finding has a `finding_key`, `finding_value`, and `source_id`. The `source_id`s are your **evidence identifiers** — collect the relevant ones for `evidence_ids`.
- **`current_time`** finding = the clinical review timestamp. Use it verbatim (ISO-8601 UTC with trailing `Z`) wherever a review time is required.
- **`observations`** each carry `code`, `status`, `effective_time`, `value_number`, `interpretation`, `patient_id`, `observation_id`. Status and code matter enormously — see below.
- Distractor observations are deliberately embedded (wrong date, wrong code, wrong patient, non-final status). Filter rigorously.

## Observation filtering (the most common source of error)

Protocols state **authoritative/excluded statuses** and **controlled codes**. Apply them strictly:

- **Status:** only `status = "final"` satisfies protocol gates. Exclude `preliminary`, `entered-in-error`, `canceled` (and anything non-final) from matched sets and from "latest" selection — *even if* a non-final result is newer or more abnormal.
- **Code:** match the protocol's controlled code exactly. `K` (serum/plasma potassium) is **not** the same as `6298-4` (potassium in whole blood / point-of-care). A whole-blood or point-of-care result with a different LOINC does **not** satisfy a serum-potassium gate.
- **Patient:** the observation's `patient_id` must equal the target patient. (Note: a wrong-patient observation is excluded from `matched`, but see the exclusion-list rule below.)
- **Window:** inclusive `from`, exclusive `to`, both ISO-8601 UTC. An otherwise-valid result outside the window does not qualify.
- **Latest final:** among observations that pass status+code+patient+window, pick the one with the greatest `effective_time` (then `observation_id`) as the "latest final."

### `matched_observation_ids` vs `excluded_observation_ids`

- **matched** = all final, target-code, target-patient observations inside the window. Sort by `effective_time` ascending, then `observation_id` ascending.
- **excluded** = *relevant distractor* observations that do not qualify. **Read the template's wording for the exclusion reasons carefully** — it lists specific failure categories (typically **date, code, or status**). Only list distractors that fail for a *listed* reason. A wrong-patient observation is excluded from `matched`, but if "patient" is not among the template's listed exclusion reasons, **do not put it in `excluded_observation_ids`**. When in doubt, follow the template's enumerated reasons literally rather than "common sense."
- Sort `excluded` by `effective_time` ascending (then `observation_id` ascending) when the template asks for it.

## Protocol gates and downstream results

Map the **latest final** target value to the gate enum using the protocol's thresholds (e.g. normal vs. low-repletion vs. critical/urgent vs. no-final-lab-in-window). The gate then drives the repeat-lab / disposition / plan:

- A **normal** latest final that satisfies the gate ⇒ repeat-lab typically **not recommended** (`recommended: false`, `scheduled_time: null`).
- A **low** latest final ⇒ repletion plan + a scheduled repeat.
- **No final lab in window** ⇒ recommend obtaining one.
- Use the protocol's exact gate labels; do not invent intermediate states.

## Medication and allergy safety

- Pull **active** allergies only (ignore `status: inactive`). Map allergens to the template's allergen enum and populate `avoid_allergens`.
- Choose the antibiotic/medication **strategy** from the allowed enum such that it avoids the patient's active allergen classes (e.g. a penicillin- and sulfa-allergic patient cannot use a beta-lactam-based outpatient regimen — select the non-cross-reactive alternative the enum offers).
- **Safety-check booleans** assert you did *not* make unsupported claims: e.g. no penicillin/sulfa in the plan, no claim of a normal CXR when imaging is abnormal, no claim of "clear lungs," no false LOC/vomiting/photophobia. Set these `true` only when your answer genuinely avoids the false claim.
- **Stabilization actions** are reserved for cases meeting escalation thresholds (e.g. SpO2 < 90, respiratory rate ≥ 30, systolic BP < 90, or other protocol red flags). For an outpatient case above those thresholds, use an **empty list** — do not add supplemental oxygen for borderline-but-non-escalating vitals.

## Recommended tests

List the diagnostic tests that are **actually performed/documented** in the case (the protocol's controlled codes that appear as observations/imaging). Do **not** pad the list with controlled codes that have no corresponding result in the case record — an unperformed test is not a "recommended test" for scoring purposes unless the protocol explicitly requires ordering it.

## Numeric derivations

Apply the protocol's dose/numeric rules **exactly as written** — formula, target, and rounding:

- Example pattern: `dose = (target − current) / 0.1 × mEq_per_0.1_below_target`, then round to the protocol's nearest-mEq increment. Use the **latest final** value as `current`, not a preliminary or wrong-code value.
- Respect precision in the template (one decimal place for lab values, two for probabilities, integer hours/days/counts). Format blood pressure as `systolic/diastolic` (e.g. `140/90`).
- **Timestamps**: ISO-8601 UTC with trailing `Z`. "Next morning" follow-up = the next calendar day at `08:00:00Z`. The review `current_time` comes from the case finding verbatim.

## Set-valued fields

- Evaluators normalize most lists as **sets** (order-independent) unless the template specifies an ordering. Sorting correctly never hurts; over-inclusion **does** hurt — each false-positive element lowers the score. Select only codes with direct evidence in the case/protocol.
- Map case facts to the enum codes precisely (e.g. diastolic HF + a volume-overload admission ⇒ the specific HFpEF/volume-overload code; SDOH "choosing between renal diet foods and utility bill" ⇒ a *food* financial barrier, not a medication barrier).
- For source-provenance grouping, distinguish **chart facts** (registry/lab/vital/imaging data) from **member-disclosed** facts (SDOH and member-reported barriers/preferences). Include a chart fact only if it actually appears in the record (e.g. do not list `egfr` if no eGFR observation exists for the case).

## Final checks before emitting

- Every required top-level key present; no extra top-level keys.
- Every enum value is spelled exactly as in the template.
- `null` used only where permitted; integers/numbers at the specified precision.
- `evidence_ids` populated with stable identifiers (case id first when the template says so, then clinical source ids).
- Single JSON object only — no surrounding text, no markdown fences.
