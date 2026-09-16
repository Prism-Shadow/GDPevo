---
name: clinic-protocol-solver
description: Solve structured clinical protocol decision-support tasks that query a synthetic clinic REST API, apply protocol logic to patient data, and return strictly-typed JSON conforming to a supplied answer template. Use this skill whenever the task mentions a clinic runtime environment, a TASK_ENV_BASE_URL, FHIR resources (Patient, Observation, Case, Medication, Allergy, etc.), clinical decision support, protocol assessments, care management routing, lab-result gating, or returning JSON that conforms to an answer_template.json file with controlled enumerations.
---

# Clinic Protocol Solver

This skill provides a reliable workflow for solving structured clinical protocol
tasks against a synthetic clinic FHIR-like REST API. The tasks all follow the
same pattern: query the clinic API for patient and case data, reason through a
clinical protocol, and produce a strictly-typed JSON answer that conforms to a
supplied template.

## When to use this skill

Use this skill whenever the task involves all of these signals:

- A clinic runtime environment referenced at `<TASK_ENV_BASE_URL>`
- An `input/payloads/answer_template.json` that defines required keys, allowed
  enum values, types, and ordering rules
- A target case identifier (e.g. `CASE-RESP-102`)
- A requirement to return a single JSON object with no narrative text

## Workflow

Follow these steps in order. Each step produces information the next step needs.
Do not skip ahead.

### Step 1: Read the answer template first

Before touching the API, read `input/payloads/answer_template.json`. This is the
contract you must satisfy. Pay attention to:

- **required_top_level_keys** — every one must appear in your output
- **type** — enforce the correct JSON type (string, integer, number, boolean,
  object, array, null)
- **allowed_values** / **enum** — use only these exact strings; never invent new
  values
- **ordering_rules** — follow sort or no-ordering rules (set-semantic fields
  often say "no semantic ordering is required")
- **required_keys** inside nested objects
- **nullable** / **type: ["string", "null"]** — use `null` only where the schema
  explicitly permits it
- **numeric_precision** — respect decimal places and integer rules

The template tells you everything you need to know about the output shape. If
any field is unclear, resolve it against the template, not against what the
prompt text implies.

### Step 2: Identify the target case and fetch the case record

The prompt gives a case ID (usually `CASE-XXXX-NNN`). Use the environment's
`/api/cases/{case_id}` endpoint to retrieve it. The case record links to a
patient and often contains context about the clinical scenario.

From the case response, extract:
- `patient_id` — you need this for patient-scoped queries
- Any case-level clinical context (presenting complaint, protocol
  applicability, time window, etc.)

### Step 3: Gather all relevant clinical data

Use the case and patient IDs to pull every category of data the template's
fields imply. The environment access document lists your available endpoints.
Typical endpoints include:

- `/api/patients/{patient_id}` — demographics
- `/api/observations` — lab results (look for LOINC codes, values, effective
  times, and status)
- `/api/medications` — active and past medications
- `/api/allergies` — allergy/intolerance records (critical for medication
  plans)
- `/api/imaging` — radiology reports and findings
- `/api/problems` — problem list / diagnoses
- `/api/care-registry` — care management registry data
- `/api/sdoh` — social determinants of health
- `/api/protocols` — protocol definitions and clinical guidance
- `/api/protocols/{protocol_id}` — specific protocol details
- `POST /api/query` — structured queries when you need filtered data

**Filter by patient and case where possible.** Observations and other resources
often contain many records; filter by patient ID and relevant date windows to
avoid noise.

**Read protocol material** when the task involves protocol-gated decisions. Use
`/api/protocols` to list available protocols and `/api/protocols/{id}` to read
the specific protocol that governs the decision. The protocol defines thresholds
for risk tiers, imaging gates, lab result interpretation, replacement
eligibility, and referral criteria.

### Step 4: Apply the protocol and make the clinical determination

Now map the clinical data to the template's allowed values. For each field:

**Enum fields** — choose the single value from `allowed_values` that best
matches the clinical facts. The choice must be defensible from the protocol and
the data. Never pick a value just because it exists; each value has a specific
clinical meaning.

**List fields** — assemble a set of relevant enum values. Do not include values
that are absent or unsupported. Use each value at most once. Follow the
ordering rule (sorted ascending, clinical sequence, or no ordering).

**Boolean safety checks** — these guard against false claims. For example,
`no_penicillin_or_sulfa: true` means you verified no penicillin or sulfa allergy
in the allergy data. These are factual assertions, not clinical opinions.

**Numeric fields** — pull exact numbers from observations. Do not round unless
the template specifies a precision. When the template says "one decimal place",
use exactly one decimal place.

**Timestamps** — use ISO-8601 UTC format with trailing `Z` from the source data
when available. For computed times (e.g. follow-up scheduling), use the same
format and add the offset to the current clinical review time.

**Null fields** — use `null` only when the schema explicitly permits it (a type
like `["string", "null"]` or `["integer", "null"]`). When medication is not
recommended, medication fields that permit null should be null, not empty
strings or zero.

### Step 5: Assemble and verify the output

Build the JSON object with every required top-level key present. Before
finalizing, run these checks:

1. Every key in `required_top_level_keys` is present
2. No extra top-level keys beyond what the template defines (some templates
   explicitly warn against this)
3. Every enum value appears exactly in the `allowed_values` list
4. Every nested object has all `required_keys`
5. Null is used only where the schema permits null
6. Numbers match the specified precision
7. List items are unique (no duplicates)
8. Timestamps follow ISO-8601 with trailing `Z`
9. The JSON is valid — no trailing commas, no comments, no markdown fences

**Output format:** Return only the JSON object. No markdown code fences, no
explanatory prose, no comments. The evaluator expects raw JSON.

### Step 6: Handle edge cases and missing data

- **Missing observation window match:** If no eligible observation falls in the
  target window, set `lab_found: false`, make `latest_final: null`, and set
  `protocol_gate` to the "no final lab in window" value.
- **No medication needed:** Set medication fields to null (when schema permits),
  `status` to `"not_recommended"`, and the antibiotic/medication strategy to the
  appropriate "no medication" or "defer" enum value.
- **No stabilization actions:** Use an empty list `[]`, not null.
- **Multiple matching observations:** Pick the most recent final (non-preliminary)
  result by effective_time. Sort by time ascending when the ordering rule asks
  for ascending order.
- **Allergy contraindications:** When a patient has an allergy to a class
  included in `avoid_allergens`, include that class. When no allergies are
  relevant, `avoid_allergens` should be an empty list `[]` unless the template
  requires otherwise.
- **Unavailable numeric values:** When a numeric field is required but the data
  is unavailable, check the schema for nullability. If null is not permitted,
  search broader (e.g. recent observations outside the primary window may still
  provide the value).

## Key principles

**The template is the authority.** When the prompt text and the template seem to
conflict, the template wins. The template defines what the evaluator checks.

**Protocol over intuition.** Clinical decisions must be traceable to protocol
material or structured data, not to general medical knowledge. Cite evidence
through `evidence_ids` — these are the case, observation, imaging, or protocol
identifiers that support your determinations.

**Controlled vocabulary only.** Every string value in the output must appear in
the template's `allowed_values` for that field. Inventing a value, even a
clinically plausible one, will fail evaluation.

**One JSON object, nothing else.** The evaluator expects a raw JSON object. Do
not wrap it in markdown fences, do not add commentary, do not include trailing
explanations.

## Reference files

- [references/api-endpoints.md](references/api-endpoints.md) — Details on each REST API endpoint used by clinic protocol tasks.
- [references/template-reading.md](references/template-reading.md) — Guide to reading `answer_template.json` field specifications.
- [references/common-patterns.md](references/common-patterns.md) — Patterns that recur across different clinical domains.
