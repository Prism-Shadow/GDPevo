---
name: ehr-governance-packet
description: Produces normalized JSON governance/coordination packets from a read-only EHR API — duplicate-chart merge readiness, referral coordination letters, care-transition handoffs, referral batch audits, and duplicate-review / ServiceRequest quality validation. Use whenever a task supplies an answer_template.json schema, case-object IDs (patient / referral / candidate / batch / service-request / provider), and an environment_access.md pointing at a network EHR API, and asks for "normalized JSON only". Trigger terms — EHR quality-governance, duplicate merge packet, referral coordination/audit, care transition / handoff, ServiceRequest validation, answer_template.json, TASK_ENV_BASE_URL, normalized_key, set semantics.
---

# EHR Governance Packet Generation

You are producing a **normalized JSON packet** that conforms to a task-specific
`answer_template.json`, using evidence read from a read-only EHR environment
reached **over the network only**. The task shapes this skill covers:

- duplicate-chart **merge readiness** packets
- **referral coordination** packets (e.g. specialty referral letters)
- **care-transition / handoff** packets
- **referral batch audits** (coding, laterality, duplicates, tiering)
- **duplicate-review + ServiceRequest** quality validation

The schemas differ per task; the **method** is the same: read the template for
the schema, read the environment for the evidence, normalize, and emit JSON only.

## Hard rules

1. **The template is the contract.** Read `input/payloads/answer_template.json`
   first. Every required top-level key, field type, enum value, nullability
   rule, and ordering rule lives there. Emit exactly those keys; use only enum
   values the template lists; never invent fields or enum members.
2. **The network API is the only source of truth for environment data.** Read
   `environment_access.md` (staged in the working directory) to get the base URL
   and the allowed `GET` endpoints. Do **not** read local source files for
   environment data. Use `GET` requests only; no authentication.
3. **Output is JSON only.** Return a single JSON object conforming to the
   template. No prose, no narrative SOP text, no explanatory comments outside
   the object. Use stable IDs, not narrative. Dates are `YYYY-MM-DD`.
4. **Derive every value from evidence.** Never hardcode IDs, codes, counts, enum
   choices, or contact details from memory — fetch them from the API and map
   them into the template.

## Workflow

### 1. Triage the task inputs
- `prompt.txt` → the case objects (patient / referral / candidate / batch /
  service-request / provider IDs) and what the packet must contain. Note any
  framing constraints ("exclude stale records", "do not include narrative").
- `input/payloads/answer_template.json` → the exact output schema. Note:
  required top-level keys, enum vocabularies, which arrays have **set
  semantics** vs ordered arrays, ordering keys, nullability, and any
  `required_value` fields (e.g. a `task_id` that must be a specific literal).
- Any **extra payload** files in `input/payloads/` (e.g. a request packet) →
  additional case parameters. Read every file in that directory; do not assume
  only the template exists.
- `environment_access.md` → base URL + allowed endpoints.

### 2. Gather evidence broadly
For every case-object ID, fetch the endpoint families that bear on the packet —
and gather the **full active chart**, not just the obvious records, so
distractors can be identified by contrast. See `references/endpoint_guide.md`
for which family serves which evidence need and how to cross-reference. The
exact paths come from `environment_access.md` at runtime; do not hardcode them.

### 3. Normalize into the template
Apply the reusable rules in `references/normalization_playbook.md`. Recurring
patterns:

- Clinical records (conditions / medications / allergies) expose a
  `normalized_key`. Wherever the template asks for "keys", emit the
  `normalized_key` — not the code or free-text name.
- **Active-list unions**: include only active-status records; union across the
  relevant patients (e.g. both sides of a duplicate candidate); sort as a set.
- **Authoritative source**: patient active-list endpoints win over any
  duplicate-preview / chart-summary. Where the template asks, report the keys
  the active endpoints added that the preview lacked.
- **Sets & ordering**: set-semantic arrays are sorted (alphabetically / by the
  key the template names); ordered object arrays follow the template's ordering
  rule (e.g. by id, newest-to-oldest, fixed length).
- **Distractor exclusion**: stale / outside-window / inactive / unrelated
  records are excluded; where the template has an `excluded_*` section, list
  their IDs/keys (sorted).
- **Enum derivation**: classify disposition / readiness / decision / validation
  from evidence, using only the template's enum vocabularies.
- **Code validation**: validate ICD-10 via the ICD-10 endpoint (chapter,
  expected terms, laterality) and service codes via the service-code endpoint.
- **Contacts**: resolve provider directory entries for any contact block.

### 4. Verify and emit
- Every required key present; every enum value template-allowed; nulls only
  where allowed; booleans are real booleans; arrays sorted per template.
- Cross-check summary counts against the rows you actually placed in each
  bucket; cross-check that excluded distractors are genuinely absent from the
  included sets.
- Emit the single JSON object. Nothing else.

## When evidence is missing
If a record the template expects is absent from the API, emit the template's
missing / null / empty-array representation rather than inventing data, and set
any readiness / blocking field the template provides to reflect the gap. Do not
pad with guessed values, and do not substitute a different record for the one
named in the prompt.
