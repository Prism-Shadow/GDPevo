# Clinic Decision-Support Skill

## Purpose

Generate protocol-bound clinical decision-support JSON responses for synthetic clinic cases. Each task presents a case identifier, an answer template, and access to a clinic runtime environment with patient records, observations, protocols, and related clinical data.

## Core Workflow

Follow these steps in order for every task:

### 1. Orient to the Task

Read the task prompt to identify:
- The target case identifier (e.g., `CASE-XXX-NNN`)
- The answer template file at `input/payloads/answer_template.json`
- Any task-specific instructions about which clinical domain applies

Read the answer template completely. Note every required top-level key, every enum's allowed values, every numeric precision requirement, and every ordering rule. The template is the authoritative schema — your output must conform to it exactly.

### 2. Gather Clinical Data

Query the runtime environment for all relevant data. Start broad, then narrow:

a. **Fetch the case**: This returns the patient_id, findings, and often embedded observations, medications, allergies, imaging, problems, and SDOH data in a single consolidated response. The findings array contains structured key-value pairs that summarize the clinical picture.

b. **Fetch the patient**: Confirms demographics and may include additional medications, allergies, problems, and SDOH.

c. **Fetch observations by patient**: Use patient-scoped endpoints to get all observations, then filter programmatically. Do not trust a quick scan — examine every observation's code, status, effective_time, patient_id, and value.

d. **Fetch supporting data**: Retrieve medications, allergies, imaging, problems, and SDOH records. Check each for active vs. inactive status.

e. **Fetch the relevant protocol**: Protocols define the clinical decision rules. Read the protocol body completely — it specifies thresholds, triggers, controlled observation codes, medication NDCs, follow-up LOINC codes, escalation criteria, and formula-based calculations.

### 3. Apply Protocol Rules

Protocols are the decision engine. Apply them systematically:

- **Status filtering**: Only observations with `status: "final"` are authoritative for protocol gates. Exclude `preliminary`, `canceled`, and `entered-in-error`. Every protocol declares an `authoritative_statuses` list — use it.

- **Code matching**: Use the protocol's `controlled_codes` map to identify relevant observations by code. A serum potassium observation uses code `"K"`; a whole-blood potassium with code `"6298-4"` is a different test and should be handled according to the protocol's scope.

- **Threshold checks**: Apply numeric thresholds exactly as stated. "Less than" means strictly less than; "at least" means greater than or equal to. Do not round or fudge thresholds.

- **Trigger evaluation**: Protocols define escalation or urgency triggers as Boolean conditions. Check each trigger against the patient's data. If any trigger is met, the urgent branch applies.

- **Formula application**: When a protocol provides a formula (e.g., dose calculation), apply it exactly. Use the precision and rounding rules stated in the protocol.

- **Allergy rules**: Before recommending any medication, check active allergies. Map allergen classes to medication classes — the protocol's `allergy_rule` tells you to avoid implicated medication classes based on active allergies.

### 4. Fill the Template

Translate clinical decisions into template values:

- **Use exact enum values**: Every enum field in the template has a fixed set of allowed string values. Copy them verbatim — no synonyms, no abbreviations, no clinical paraphrasing. If the template says `"hypoxemia_92_93"`, do not write `"mild_hypoxia"` or `"low_oxygen"`.

- **Respect null constraints**: Some fields permit `null` only under specific conditions (e.g., medication details are null when no medication is recommended). The template's `type` field tells you whether a value is `"string_or_null"`, `"integer_or_null"`, or `"enum_or_null"`.

- **Match numeric precision**: If the template says `"precision": "one decimal place"`, provide exactly one decimal place (e.g., `3.2`, not `3.20` or `3`). For integers, provide whole numbers.

- **Follow ordering rules**: Check each list field's ordering instruction:
  - "No semantic ordering is required" → order does not matter; the evaluator normalizes as a set.
  - "Sort by effective_time ascending, then observation_id ascending" → apply that exact sort.
  - "Order is not meaningful; use each code at most once" → no duplicates, any order.
  - "List in descending relevance" → most important first.

- **Include relevant evidence IDs**: The evidence_ids field should reference the case identifier and the specific observation, imaging, and other source identifiers that support the clinical decisions. Use the exact IDs from the API responses.

### 5. Verify Safety Checks

Safety check fields are Boolean validations that confirm certain false claims are NOT being made. They should be `true` when the claim is indeed false (safe) and `false` when the claim is true (unsafe):

- A check like `"no_normal_cxr_claim"` should be `true` when the CXR is NOT normal (i.e., it's abnormal, so claiming it's normal would be wrong).
- A check like `"no_false_loc"` should be `true` when there is genuinely no loss of consciousness (so claiming LOC would be false).
- Think of these as: "Is it correct that we are NOT making this false claim?" — answer `true` when the false claim is avoided.

### 6. Validate Before Returning

Before finalizing:
- Every required top-level key is present.
- Every enum value matches the template's allowed list exactly.
- Numeric values use the specified precision.
- List fields that normalize as sets contain no duplicates.
- List fields with ordering rules are sorted correctly.
- Null is used only where the schema permits it.
- The output is a single JSON object with no markdown wrappers, no comments, and no explanatory prose.

## Common Pitfalls

1. **Using non-final observations**: A preliminary, canceled, or entered-in-error observation is not authoritative. Always filter by the protocol's `authoritative_statuses`.

2. **Wrong observation code**: Different lab methods produce different codes. A whole-blood potassium (code `6298-4`) is not the same as a serum potassium (code `K`). Match against the protocol's `controlled_codes`.

3. **Wrong patient observations**: Observation lists may include results from other patients associated with the case. Always verify `patient_id` matches the target patient.

4. **Over-including tests**: The recommended_tests field asks which tests are indicated by the protocol, not which tests happen to have been performed. Protocols define which tests apply.

5. **Misapplying allergy constraints**: An inactive allergy is not a contraindication. Check the allergy `status` field — only `active` allergies constrain medication choices.

6. **Rounding errors in dose calculations**: When a protocol says "round to nearest 10 mEq," apply standard rounding. 30 mEq stays 30; 34 mEq rounds to 30; 35 mEq rounds to 40.

7. **Enum string mismatch**: `"BID"` is not `"twice daily"`. `"PO"` is not `"oral"`. Use the exact string from the template's allowed_values list.

8. **Incomplete data gathering**: The consolidated case endpoint may not include all observations. Always cross-check by querying the patient-scoped observation endpoint as well.

9. **Ignoring SDOH and registry data**: For care-management tasks, social determinants of health (SDOH) and care registry data are often critical to program routing and referral decisions.

10. **Missing protocol details**: The protocol body contains NDC codes, LOINC codes, follow-up timeframes, and other controlled identifiers. Extract these exactly — do not substitute from general knowledge.
