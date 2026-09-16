---
name: clinic-decision-support
description: Protocol-bound clinical decision support for synthetic clinic cases. Use when a task provides a case_id, references a clinic runtime environment, and requires structured JSON output conforming to an answer template. Covers respiratory assessment, pediatric head injury, potassium replacement, care-management routing, and observation-window tasks. Do NOT use for general medical questions outside structured clinic-case workflows.
---

# Clinic Decision Support

## Overview

Produces structured clinical decision-support JSON for synthetic clinic cases by navigating a REST clinic runtime, cross-referencing protocol rules with patient data, and conforming strictly to provided answer templates.

## Core Workflow

Every task in this domain follows the same pattern. Execute these steps in order.

### Step 1: Orient from the Prompt

Read the prompt to extract three critical pieces:

- **case_id**: The target case identifier (e.g. CASE-RESP-102).
- **TASK_ENV_BASE_URL**: The clinic runtime base URL. When the prompt says <TASK_ENV_BASE_URL>, substitute http://task-env:9016/ unless the environment access documentation provides a different value.
- **Answer template path**: The prompt will reference input/payloads/answer_template.json. Read that file to understand the required output schema.

### Step 2: Fetch Case Data

Call `GET {BASE_URL}/api/cases/{case_id}`. This returns a composite JSON object containing all related resources:

| Key | Description |
|-----|-------------|
| `case` | Case metadata (case_id, case_type, patient_id, service_date, status, summary) |
| `patient` | Demographics (patient_id, name, age, birth_date, sex, fhir_id) |
| `findings` | Key-value clinical findings array (finding_key, finding_value, source_id) |
| `observations` | Vital signs, labs, exam results with codes, values, timestamps, status |
| `imaging` | Radiology studies with impressions |
| `medications` | Active medication list |
| `allergies` | Allergy records with allergen, reaction, status |
| `problems` | Active problem list with codes |
| `sdoh` | Social determinants of health |
| `care_registry` | Registry data when present (risk score, utilization, program hints) |

This single endpoint is sufficient for nearly all decision-support tasks. Use the collection endpoints (/api/patients, /api/observations, etc.) only when the case composite does not contain what you need.

### Step 3: Parse the Answer Template

Read input/payloads/answer_template.json. Study every field:

- **required_top_level_keys**: Every key must appear in your output.
- **Field types**: string, enum, list[enum], object, boolean, integer, number, string_or_null, integer_or_null, enum_or_null.
- **allowed_values**: For enum and list[enum] fields — never emit a value outside this set.
- **required_keys**: For object fields — include every listed key.
- **Ordering rules**: Pay attention to stable ordering for evidence_ids and observation lists; otherwise set-based ordering is fine.
- **Numeric precision**: Match the specified decimal places exactly.

### Step 4: Review Applicable Protocols

If the task involves clinical decision rules, fetch the relevant protocol:

1. List protocols: GET {BASE_URL}/api/protocols
2. Get the specific protocol: GET {BASE_URL}/api/protocols/{protocol_id}

Protocols contain threshold values, escalation criteria, medication rules, follow-up timing, and return precaution codes. Use protocol rules to derive decisions from observations, not ad hoc clinical reasoning.

### Step 5: Derive the Structured Answer

Cross-reference the case data against the protocol rules and template schema:

- **Assessment**: Match findings against protocol-defined criteria.
- **Risk level/tier**: Derive from protocol thresholds applied to observation values.
- **Disposition**: Follow protocol escalation rules.
- **Medication plan**: Apply allergy constraints from the case record; avoid implicated allergen classes.
- **Red flags / absent red flags**: Protocol-defined lists; report only what the data supports.
- **Follow-up timing**: Use protocol-specified timeframes.
- **Evidence IDs**: Collect case_id, observation_ids, imaging_ids, protocol_ids used in the decision. List case_id first, then clinical sources.
- **Safety checks**: Boolean guards for findings the evaluator knows are unsupported — set to true when the unsupported finding is correctly absent.

### Step 6: Output the JSON

Return exactly one JSON object. Do not wrap in markdown fences, do not add commentary, do not include extra keys. Every value must conform to the template type and allowed-value constraints.

## Common Patterns and Pitfalls

### Observations

Observations have status: "final" or status: "preliminary". Protocols almost always require final results. An observation code field uses LOINC codes (e.g. 2823-3 for potassium, 4548-4 for HbA1c) or custom codes (e.g. K for potassium in some datasets). Use code for matching, not display.

### Findings

Findings are the primary narrative data. Extract values by finding_key. Common keys include: current_time, chief_complaint, oxygen_room_air_range, dyspnea, pleuritic_chest_pain, confusion, loss_of_consciousness, vomiting, photophobia, registry_risk_score, target_code.

### Allergies

Active allergies constrain medication selection. Check status: "active" records against protocol medication options. List avoided allergen classes in avoid_allergens.

### Timestamps

All timestamps use ISO-8601 UTC with trailing Z. Observation windows are inclusive start, exclusive end.

### Observation Windows

When the task involves a date window for lab results:
- Filter observations by patient_id, code, status=final, and effective_time within the window
- Sort matched by effective_time ascending, then observation_id ascending
- Exclude observations that are preliminary, outside the window, or have wrong codes
- The latest_final is the last matching observation by effective_time

## Reference Files

- **[api_endpoints.md](references/api_endpoints.md)**: Full API endpoint reference with response shapes, field descriptions, and example payloads.
- **[template_guide.md](references/template_guide.md)**: Detailed guidance on interpreting answer template schemas, including type semantics, ordering rules, and edge cases.

Load these references when you need detailed API response structures or template-field interpretation that is not covered inline above.
