# Clinic Decision-Support Skill

Use the synthetic clinic runtime environment to produce structured, protocol-bound
clinical decision-support answers from patient data exposed through a REST API.

## When to use this skill

The task will provide:
- A **prompt** naming a target case identifier and describing the clinical question.
- An **answer template** (`input/payloads/answer_template.json`) defining the exact
  JSON output shape: required top-level keys, field types, allowed enum values,
  numeric precision rules, and safety-check requirements.
- **Environment access details** (`environment_access.md` or equivalent) listing
  the base URL, credentials, and allowed API endpoints for the run.

Use this skill whenever you must retrieve clinical data from the runtime and
return a single JSON object conforming to a supplied template.

## Core workflow

### 1. Read the inputs

Read all three input files before making any API call:

- The **prompt** — identifies the target case, the clinical domain, and what
  decisions or assessments are expected.
- The **answer template** — the authoritative schema for the response. Every
  key, type constraint, and enum value comes from here; never invent values.
- The **environment access document** — the base URL, any credentials, and the
  exact list of allowed endpoints.

### 2. Connect to the clinic API

The runtime exposes REST endpoints under the base URL. Authentication, when
required, is provided as an HTTP header (e.g. `X-Clinic-Token`).

Include the credential header on every request. The API speaks JSON.

**Available endpoint classes** (exact paths may vary by run):

| Method | Path pattern              | Purpose                              |
|--------|---------------------------|--------------------------------------|
| GET    | `/api/patients`           | List or search patients              |
| GET    | `/api/patients/{id}`      | Single patient record                |
| GET    | `/api/cases`              | List or search cases                 |
| GET    | `/api/cases/{id}`         | Single case record                   |
| GET    | `/api/observations`       | List or search observations          |
| GET    | `/api/medications`        | List medications                     |
| GET    | `/api/allergies`          | List allergies                       |
| GET    | `/api/problems`           | List problem-list items              |
| GET    | `/api/imaging`            | List imaging studies                 |
| GET    | `/api/care-registry`      | Care registry / program enrollment   |
| GET    | `/api/sdoh`               | Social determinants of health        |
| GET    | `/api/protocols`          | List clinical protocols              |
| GET    | `/api/protocols/{id}`     | Single protocol detail               |
| POST   | `/api/query`              | Structured query / search            |

Use `GET /api/cases/{case_id}` first to anchor on the target case and learn the
linked patient identifier. Then fan out to the other endpoints to collect every
data element the template requires.

### 3. Gather all relevant evidence

Work outward from the case:

1. **Get the case** → yields `patient_id`, encounter references, and coded
   problems or diagnoses.
2. **Get the patient** → yields demographics, care-team links, and registry
   status.
3. **Pull observations** — filter by patient, code, date range, and status.
   Pay attention to `status: "final"` vs `"preliminary"` or `"amended"`;
   templates often distinguish final results from other statuses.
4. **Pull imaging, medications, allergies, problems** — for allergy-aware
   prescribing, drug-interaction checks, and problem-list-based risk
   stratification.
5. **Pull protocols** — where the template asks for protocol-gate results,
   protocol-driven recommendations, or evidence identifiers anchored in a
   specific protocol version.
6. **Pull registry and SDOH** — when risk-tier, program-routing, or
   outreach-stance fields ask for social-context and care-eligibility data.

Keep a running list of every resource identifier you consult; these become
`evidence_ids` (or equivalent) in the response.

### 4. Interpret the answer template

The template is a machine-readable JSON Schema-like document. Key patterns:

- **`required_top_level_keys`** — every key in this list must appear in your
  output, even if its value is `null` (when the template permits null).
- **`type: "enum"`** — the value must be exactly one of the listed strings;
  do not paraphrase, abbreviate, or invent alternatives.
- **`type: "list"` with item enum** — collect only allowed values. Use each
  value at most once unless the template says otherwise. Order does not matter
  unless an explicit ordering rule is given.
- **`type: "object"` with `required_keys`** — every listed sub-key must be
  present.
- **Numeric precision** — match the stated precision (e.g. one decimal place
  for mmol/L, two decimal places for probability scores, integer for counts).
- **`type: "string_or_null"` / `type: ["enum", "null"]`** — null is a valid
  value, but only where the template says so; do not null out required strings.
- **Safety-check booleans** — these are protocol guardrails; set each to
  `true` only when you have confirmed the condition holds from the data, and
  `false` otherwise. They often assert that a contraindicated finding (e.g.
  a normal CXR when the protocol requires an abnormal one) is absent.
- **`output_rule` / `output_rules`** — follow these exactly (no markdown, no
  extra keys, no prose outside the JSON object).

When a template key maps to an enum whose value must be *derived* from the data
(rather than copied verbatim), apply the protocol definitions from the retrieved
protocol resources. Do not guess.

### 5. Assemble the response

Build the JSON object key by key in the order of `required_top_level_keys`:

- Use `task_id` from the template's `expected_constant` or from the prompt.
- Use `case_id` from the prompt.
- Use `patient_id` as returned by `GET /api/cases/{case_id}`.
- Fill every other key with data-derived or protocol-derived values.
- When the template asks for window-based observation search, construct the
  window from the prompt or case metadata, apply the target LOINC/code filter,
  and separate matched observations (correct code, correct patient, correct
  date window, correct status) from excluded ones (right patient but wrong
  code, date, or status).
- For medication plans: cross-reference the patient's allergy list and populate
  `avoid_allergens` with every allergen class the patient has on record.
- For follow-up timing: read the relevant protocol for the recommended
  recheck interval; express it as integer hours.
- For evidence identifiers: list every case, observation, imaging, protocol,
  and registry resource you used to reach your conclusions.

### 6. Validate before returning

Before outputting the JSON, run these checks:

1. **Key completeness** — every required key is present.
2. **Enum compliance** — every string value is from the allowed list.
3. **Type correctness** — integers are integers, not strings; booleans are
   `true`/`false`, not `"true"`/`"false"`; numbers have correct precision.
4. **Null discipline** — null appears only where the template permits it.
5. **No extra keys** — the top-level object has exactly the required keys.
6. **No markdown or prose** — return the raw JSON object only.

### 7. Traceability principle

Every clinical assertion in the response must be traceable to a specific
resource retrieved from the runtime. If the template includes `evidence_ids`,
`source_provenance`, or similar tracing fields, they must list every resource
that contributed to the answer. This includes:

- The case resource itself
- Observation resources used for lab values or vitals
- Imaging resources used for radiological findings
- Protocol resources used for gating or recommendation logic
- Registry or SDOH resources used for risk or program routing

## Anti-patterns

- **Do not** guess patient identifiers — always retrieve them from the API.
- **Do not** hard-code values from the training examples; every run has its
  own data.
- **Do not** use a value outside the template's allowed enum list, even if it
  seems clinically more precise.
- **Do not** include markdown fences, trailing commas, or explanatory text in
  the output.
- **Do not** mutate server state — GET and POST `/api/query` only; no PUT,
  PATCH, or DELETE.
- **Do not** skip allergen cross-referencing when the template includes
  `avoid_allergens` or `no_penicillin_or_sulfa` checks.
- **Do not** return a medication plan without verifying the patient's allergy
  list first.
