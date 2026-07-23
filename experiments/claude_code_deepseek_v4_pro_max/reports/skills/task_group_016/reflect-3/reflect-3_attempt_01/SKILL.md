# Clinic Decision-Support Skill

Apply this skill when solving structured clinical decision-support tasks against a synthetic
clinic runtime environment. The tasks require retrieving patient case data, applying protocol
rules, and returning JSON answers that conform to a supplied template.

## 1. Orient to the task

Read the prompt first. It names the target case identifier, describes the clinical domain, and
points to an answer template. Before fetching anything, read the answer template to understand
every required key, its type, allowed enum values, and any ordering or nullability rules. The
template is the single source of truth for the output shape.

Then fetch the target case. The case endpoint returns a composite payload that bundles the
patient record, encounter findings, observations, medications, allergies, imaging, problems,
care-registry data, and SDOH flags — all in one response. There is rarely a need to call
separate patient or observation endpoints; the case payload is complete.

## 2. Retrieve and apply the protocol

Protocols are listed at the protocols index endpoint. Match the protocol whose scope or title
aligns with the task domain (respiratory, head-injury, potassium, care-management, or
observation-window). Fetch the protocol body — it contains the decision thresholds, escalation
triggers, medication rules, follow-up timing, and controlled code mappings you need.

Map every protocol rule to a template field:
- Assessment and risk-tier enums are driven by protocol criteria, not general clinical
  intuition. If the protocol defines a threshold (e.g., oxygen saturation below a certain
  value triggers escalation), honour it literally.
- Medication rules (allergy avoidance, dose formulas, route, frequency, NDC codes) come from
  the protocol's controlled-codes and dose-rule sections. Calculate doses using the protocol
  formula exactly — do not substitute textbook doses.
- Follow-up timing and route come from the protocol, not generic guidelines.

## 3. Filter and match observations rigorously

Clinical observations require three independent checks before use:

1. **Status**: Only `"final"` status observations count for protocol gates. Preliminary,
   entered-in-error, and cancelled observations are excluded — even if their values would
   change the clinical picture.
2. **Code**: Match the exact observation code. A protocol may specify `"K"` for serum
   potassium; a whole-blood potassium with code `"6298-4"` is a different test and does not
   qualify. Similarly, `"NA"` (sodium) is not `"K"` (potassium) even when both are
   electrolytes drawn in the same window.
3. **Patient**: Verify the `patient_id` on every observation matches the target patient.
   Observations belonging to other patients — even when attached to the same case payload —
   are distractors and must be excluded.

When multiple observations satisfy all three checks, sort them by effective-time ascending
(and then by observation-id ascending as a tiebreaker). The latest effective-time among them
is the actionable result.

## 4. Respect window boundaries

When the task defines a search window (e.g., "March 2026"), the start is inclusive and the
end is exclusive. An observation whose effective-time equals the window start qualifies; one
whose effective-time equals the window end does not.

## 5. Build the answer

- **Enum fields**: Use only the exact string values listed in the template. Do not paraphrase,
  abbreviate, or substitute.
- **Numeric precision**: Follow the template's precision spec (one decimal place for lab
  values, integer for doses and hours, two decimal places for probability scores).
- **Null handling**: Use `null` only where the field type explicitly permits it (e.g.,
  `"string_or_null"`, `"integer_or_null"`, `"enum_or_null"`). A medication dose is `null`
  when no medication is recommended; it is a non-null string when one is.
- **Empty collections**: Use `[]` when no items apply (no stabilisation actions, no urgent
  actions, no red flags present). Do not use `null` for list-typed fields.
- **Ordering in sets**: When the template says "no semantic ordering," any order is acceptable
  — the evaluator normalises the set. When it specifies an ordering rule (e.g., effective-time
  ascending, clinical action sequence), follow that rule exactly.
- **Boolean safety checks**: These are direct mappings from the clinical record. If the record
  says a condition is absent, the corresponding `no_false_*` field is `true`. If it was never
  assessed and there is no evidence for it, it is still `true` (no false claim is being made).
- **Evidence IDs**: Include the case identifier first, then the most clinically salient
  observation, imaging, and protocol identifiers. Include every source that substantiates a
  scored field.

## 6. Cross-validate before finalising

Before returning the answer, run these cross-checks:

- **Allergy-medication conflict**: The medication plan must list every allergen class the
  patient needs to avoid, and the chosen medication must not belong to any of those classes.
- **Disposition consistency**: If the disposition is outpatient, stabilisation actions should
  not include urgent escalation. If the disposition is ED transfer, the medication strategy
  should defer to ED and the follow-up route should point to the emergency department.
- **Risk-tier coherence**: The risk tier must be consistent with the disposition and red-flag
  list. A "high" risk patient with multiple red flags should not have a "home observation"
  disposition unless the protocol explicitly allows it.
- **Absent red flags completeness**: Every red flag in the template that the patient does NOT
  exhibit should appear in the absent-red-flags list. Conversely, do not list a red flag as
  absent if it was never assessed or is ambiguous — the template may expect only confirmed
  absences.
- **Observation-window self-consistency**: The `lab_found` boolean must agree with
  `matched_observation_ids` (non-empty ↔ true, empty ↔ false). The `latest_final` must be the
  last entry in `matched_observation_ids` when sorted by effective-time. Every observation ID
  in the excluded list must have a reason for exclusion (wrong code, wrong patient, wrong
  status, or outside the window).
