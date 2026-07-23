# Clinic Protocol Decision Support Skill

## Purpose

Solve structured clinical decision-support tasks that require retrieving synthetic patient data from a clinic runtime API, applying protocol rules to the retrieved facts, and returning a single JSON object that conforms to a provided answer-template schema.

## When to Use

The task prompt will direct you to a synthetic clinic runtime environment, name a target case, reference an answer-template file, and ask for a protocol-bound clinical assessment or routing decision. Use this skill whenever you see that pattern.

## Workflow

### Phase 1 — Gather All Available Data

Before reasoning about the case, retrieve every resource the clinic environment exposes. Cast a wide net first; narrow to the target case second.

1. **List endpoints.** The clinic runtime exposes REST endpoints. Common collections: patients, cases, observations, imaging, medications, allergies, problems, protocols, care-registry, sdoh. Fetch every collection you have access to.

2. **Fetch protocols.** Retrieve the protocol list, then fetch each protocol body. Protocols define the clinical decision rules: trigger thresholds, controlled observation codes, authoritative statuses, escalation criteria, dose formulas, follow-up timing, and referral logic. **Read the relevant protocol first** before analyzing case data — it tells you what to look for.

3. **Fetch the target case.** Use the case detail endpoint (e.g., `GET /api/cases/{case_id}`). The response bundles linked observations, medications, allergies, imaging, problems, findings, patient demographics, care-registry entries, and SDoH records for that case. This is your primary working surface.

### Phase 2 — Read the Answer Template

The answer template is a JSON schema file (typically at `input/payloads/answer_template.json`). It defines:

- **required_top_level_keys** — every key must appear; no extra keys allowed.
- **field types and allowed_values** — for enum fields, use ONLY values from the enumerated list. For string fields, match the described format. For numeric fields, match the stated precision (decimal places, integer vs float).
- **ordering rules** — some list fields are order-independent (evaluated as sets); others require specific ordering (e.g., ascending by effective_time, case identifier first).
- **nullability** — fields marked `string_or_null`, `integer_or_null`, or `enum_or_null` accept null; other fields do not.
- **output rules** — return exactly one JSON object, no markdown, no comments, no extra prose.

Never invent values. If a field is an enum, pick only from `allowed_values`. If a field has `required_value` or `expected_constant`, use exactly that string.

### Phase 3 — Map Protocol Rules to Case Facts

For each template field, trace the data path:

1. **Identifiers** (`task_id`, `case_id`, `patient_id`): Copy from the prompt and case record exactly.

2. **Timestamp fields** (`current_time`, `effective_time`, `scheduled_time`): Use ISO-8601 UTC with trailing Z. Find the clinical review time in the case findings (look for `current_time` or a `TASK-CLOCK` source). For follow-up times, apply the protocol's timing rule (e.g., "next morning" means the following calendar day at a reasonable clinical hour).

3. **Enum assessments** (e.g., `primary_assessment`, `risk_level`, `disposition`, `protocol_gate`): Apply the protocol's decision thresholds to the case facts. If a protocol says "urgent when potassium < 3.0" and the value is 3.2, do not select the urgent option. Do not round or approximate thresholds — use exact comparisons.

4. **List fields** (e.g., `red_flags`, `recommended_tests`, `priority_problems`): Include items supported by case evidence and protocol triggers. Be conservative — adding an unsupported item typically costs more than omitting a borderline one. Remove duplicates.

5. **Medication plans**: Cross-reference the patient's **active** allergies before selecting an antibiotic strategy or medication. A listed allergy with `status: "inactive"` does not constrain the plan. Match medication details (NDC, route, frequency) to protocol-specified values when the protocol provides them. Apply protocol dose formulas exactly — compute the numerical result, then apply any stated rounding rule.

6. **Numeric anchors**: Extract from observations and registry data at the precision the template demands. For blood pressure, format as `"systolic/diastolic"`. For lab values, use the number of decimal places specified (e.g., `3.2`, not `3.20` or `3`).

7. **Safety checks**: These are boolean assertions that the plan correctly avoids specific errors. For example, `no_penicillin_or_sulfa: true` means the recommended medication plan does not include penicillin or sulfonamide drugs. A safety check should be `true` when the constraint is satisfied, `false` when it is violated. Read each safety-check key literally — it states what must NOT happen.

8. **Evidence IDs**: List the case identifier first, then observation, imaging, encounter, and protocol identifiers that substantiate the clinical decisions. Do not include the patient ID here (it is already a top-level field). Use a stable, repeatable order.

### Phase 4 — Observation Filtering Rules

When a task requires selecting observations from a window or identifying the latest value:

1. **Filter by patient.** Only observations where `patient_id` matches the target patient are eligible. Observations for other patients are excluded, even if associated with the same case.

2. **Filter by code.** Use the protocol's controlled observation codes. For serum potassium, the code is `"K"`, not `"6298-4"` (which is whole-blood potassium). For eGFR, use `"33914-3"`. The protocol defines the mapping.

3. **Filter by status.** Only `"final"` observations satisfy protocol gates unless the protocol explicitly says otherwise. Exclude `"preliminary"`, `"canceled"`, and `"entered-in-error"` statuses.

4. **Filter by date window.** When a window is specified (`from` inclusive, `to` exclusive), an observation falls inside only when `from <= effective_time < to`.

5. **Select the latest.** Among qualifying observations, pick the one with the most recent `effective_time`. If two have identical times, use `observation_id` ascending as the tiebreaker.

6. **Excluded observations.** List observations reviewed but rejected, with the reason implied by their exclusion (wrong date, wrong code, wrong patient, wrong status). Sort excluded items by `effective_time` ascending, then `observation_id` ascending.

### Phase 5 — Common Pitfalls

- **Do not add unsupported list items.** Each extra item in `red_flags`, `priority_problems`, `referrals`, or `escalation_conditions` that is not grounded in case data lowers accuracy. Err on the side of omission.

- **Do not confuse similar enum values.** Read every `allowed_values` entry carefully. `"hypoxemia_92_93"` and `"hypoxemia_below_90"` are distinct. `"low"`, `"moderate"`, and `"high"` risk tiers map to different protocol thresholds — use the protocol, not clinical intuition.

- **Do not mix up present vs. absent flags.** A `red_flags` list captures what IS present. An `absent_red_flags` list captures what is NOT present. Filling absent_red_flags with items that ARE present, or vice versa, inverts the clinical meaning.

- **Check allergy status.** Only `"active"` allergies constrain medication choice. An `"inactive"` penicillin allergy does not rule out beta-lactams.

- **Count carefully.** When a field asks for `active_medication_count`, count only medications with `status: "active"` on the patient's list. Do not estimate.

- **Match precision exactly.** If the template says `"precision": "one decimal place"`, output `3.2`, not `3.20` or `3`. If it says `"integer"`, output `7`, not `7.0`.

- **Do not confuse whole-blood and serum labs.** They have different LOINC codes and different reference ranges. Use the controlled code from the protocol.

- **Protocol thresholds are exact.** "Less than 3.0" means `< 3.0`, not `≤ 3.0`. "At least 0.75" means `≥ 0.75`, not `> 0.75`. Apply comparisons literally.

- **Return only the JSON object.** No surrounding markdown fences, no explanatory text, no comments. The output must parse as a single JSON object directly.
