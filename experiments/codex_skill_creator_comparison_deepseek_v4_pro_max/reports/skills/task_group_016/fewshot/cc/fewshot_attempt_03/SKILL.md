---
name: clinic-decision-support
description: Protocol-bound clinical decision-support task. Use when solving a task that asks for a structured JSON response based on synthetic-clinic runtime data accessed via REST endpoints, including case/patient reviews, protocol assessments, lab-based decisions, care-management routing, or observation-window retrieval. Trigger whenever the prompt mentions a clinic runtime environment, an answer template, a case identifier, or structured clinical decision support with enumerated output fields.
---

# Clinic Decision Support Skill

Use this skill for any task that involves querying a synthetic clinic REST runtime to produce a protocol-bound structured JSON clinical decision-support response.

## Workflow

Follow this sequence for every task. The steps are ordered to keep data fetches parallel where possible and to fill the output template correctly on the first pass.

### 1. Read the answer template first

The prompt always references an input payload template (`input/payloads/answer_template.json` or similar). Read it before you read anything else from the runtime. The template defines:

- Every required top-level key
- Allowed enumeration values for each controlled field
- Nullable vs. required sub-fields
- Numeric precision constraints
- Boolean safety checks
- Ordering rules (when field ordering matters vs. when sets are normalized)

Do not guess at output structure. The template is authoritative.

### 2. Discover the runtime endpoints

Read the environment access file (`environment_access.md` or similarly named) to learn the base URL and the allowed business endpoints. The base URL appears as `http://task-env:<PORT>/` with endpoints like `/api/patients`, `/api/cases/{case_id}`, etc. Only use the endpoints listed there.

### 3. Fetch all relevant data in parallel

Using the case ID from the prompt, fan out your data fetches. At minimum, fetch the case and patient records. Then fetch the supporting resources listed in the template's evidence or numeric-anchor fields: observations, medications, allergies, problems, imaging, protocols, registry data, SDOH records, care-registry, etc. Do not fetch endpoints that are not listed in the environment access file.

When the template references a specific observation code or window, construct the retrieval by fetching the relevant observation endpoint and filtering client-side against the template's target code, date window, and status constraints.

### 4. Map clinical facts to template enumerations

Once all data is in hand, work through the template fields one at a time:

- **Identifiers**: Pull `patient_id` from the case record. Use the stable `task_id` and `case_id` values given in the prompt or template.
- **Enum selections**: Match clinical findings to the closest allowed enumeration value. When the data supports multiple values (e.g., red flags, problem codes, referrals), include every value that is clinically justified. When the data does not support a value, do not include it.
- **Risk/assessment tiers**: Derive from the clinical data, not from the case metadata alone. Combine lab values, vital signs, problem-list severity, and protocol thresholds before choosing low, moderate/intermediate, or high.
- **Numeric anchors**: Copy exact values from the fetched observations. Respect the precision rules in the template (decimal places, integer vs. float). For blood pressure, format as `systolic/diastolic` with no extra spaces or units inside the string.
- **Boolean safety checks**: These are gate assertions. Set to `true` only when the underlying evidence confirms the safety condition; otherwise `false`. For example, `no_penicillin_or_sulfa` is `true` only when the medication plan avoids both penicillin and sulfonamide allergens and the patient's allergy list supports that exclusion.
- **Null fields**: Use `null` only where the template explicitly permits it. Never substitute a string like `"N/A"` or `"none"` for a null.
- **Empty lists**: Use `[]` for list-typed fields that require no entries, not `null`.
- **Evidence IDs**: Include the case identifier plus the specific observation, imaging, protocol, or registry identifiers that substantiate key decisions. List case identifier first when the template prescribes ordering, then sort remaining IDs in a consistent clinical-source order.

### 5. Apply protocol-gate logic

When the template includes a protocol-gate or decision-field that selects among protocol states (e.g., `protocol_gate`, `potassium_plan`, `disposition`), apply the decision rules implied by the template's enumeration descriptions and the clinical data. Do not invent rules beyond what the enumeration labels, the protocol materials fetched from the runtime, and standard clinical thresholds indicate.

### 6. Write the JSON output

Produce exactly one JSON object. No markdown fences, no comments, no leading or trailing prose. Validate:

- Every required top-level key is present
- Every enum value is a member of the template's allowed set
- Numeric values respect the template's precision rules
- Booleans are `true` or `false`, never `"true"`
- Lists use array syntax even when empty
- Timestamps use ISO-8601 UTC with trailing `Z`

## Common pitfalls

- **Reading the template late**: The template constrains what answers are valid. Read it first so you know which enumerations and precision rules apply before you start reasoning clinically.
- **Missing the patient ID**: The patient identifier lives in the case record. Always cross-reference.
- **Confusing lab windows**: When a template defines a search window with `from` (inclusive) and `to` (exclusive), respect the boundary semantics exactly.
- **Including unsupported red flags**: Only select enumeration values when there is positive clinical evidence for them. Do not include values just because the enumeration allows them.
- **Omitting null fields**: A nullable field still must appear as a key with a `null` value when the template requires the key and the condition does not apply.
- **Mixing up ordering rules**: Some fields in templates specify they are normalized as sets (ordering does not matter); others prescribe a stable sort. Pay attention to which is which.
- **Forgetting to include evidence IDs**: Every decision-support output needs a clear chain back to the source data. Include the observation, imaging, and protocol identifiers that substantiate the key clinical choices.

## Example structure (generic)

A typical decision-support JSON will have this shape, though the specific keys and enumerations vary per template:

```json
{
  "task_id": "...",
  "case_id": "...",
  "patient_id": "...",
  "primary_assessment": "<enum from template>",
  "risk_level": "<low | moderate | high>",
  "disposition": "<enum from template>",
  "red_flags": ["<enum>"],
  "recommended_tests": ["<enum>"],
  "medication_plan": {
    "medication": "...",
    "dose": "...",
    "route": "<enum-or-null>",
    "frequency": "...",
    "duration_days": 5,
    "avoid_allergens": ["<enum>"]
  },
  "stabilization_actions": [],
  "follow_up": {
    "timeframe_hours": 48,
    "route": "<enum>"
  },
  "return_precautions": ["<enum>"],
  "evidence_ids": ["..."],
  "safety_checks": {
    "no_penicillin_or_sulfa": true,
    "no_normal_cxr_claim": true,
    "no_clear_lungs_claim": true
  }
}
```

The exact keys, enumerations, and nullable rules are always defined in the task's answer template. Read that template and use only the values it allows.
