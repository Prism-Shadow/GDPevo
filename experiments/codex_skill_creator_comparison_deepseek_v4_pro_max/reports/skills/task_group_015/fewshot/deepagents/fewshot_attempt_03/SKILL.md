---
name: ehr-governance-solver
description: Solve EHR quality-governance tasks against a FHIR-like REST API. Use when the prompt references an EHR/clinical governance API, patient duplicate merge readiness, referral coordination packets, care transition packets, duplicate-review with ServiceRequest validation, referral batch audits, answer templates with normalized_key arrays, ICD-10 code validation, or active clinical list reconciliation. Covers API endpoint usage patterns, normalized JSON output rules, and evidence-based reconciliation workflows.
license: MIT
compatibility: designed for deepagents-code
---

# EHR Governance Solver

## Quick Start

Every task supplies a prompt, an `answer_template.json` payload, and a base URL placeholder `<TASK_ENV_BASE_URL>`. Follow this sequence:

1. Read the prompt and `answer_template.json`.
2. Resolve `<TASK_ENV_BASE_URL>` to `http://task-env:9015`.
3. Call the relevant API endpoints to collect evidence.
4. Produce one JSON object conforming exactly to the answer template.

Return only the JSON object. Do not include narrative text, explanations, or markdown wrappers outside the JSON.

## Core Rules

### JSON Output

- The answer template is authoritative: match its keys, types, enums, sorting rules, and set semantics exactly.
- Arrays declared as sets must be sorted alphabetically unless the template specifies a different ordering.
- Use `YYYY-MM-DD` for all date strings.
- Include every required top-level key from the template.
- When a field has no data, emit an empty array `[]` for arrays, `null` for nullable scalars, and `false` for booleans.

### API Calls

- Use `curl -s` to call endpoints. Always pipe through `python3 -m json.tool` or `jq` for readable parsing.
- The API is read-only (GET only). All endpoints return JSON.
- Fetch patient detail, conditions, medications, allergies, encounters, documents, immunizations, disclosures, and service requests through the patient-scoped endpoints.
- For bulk lookups (referral lists, audit logs, duplicate candidates, providers, ICD-10, service codes), use the collection endpoints.
- The API returns `normalized_key` values on clinical records (conditions, medications, allergies). Use these keys directly.

### Clinical List Handling

- Filter to `status` equals `active` for conditions, medications, and allergies unless the task specifies otherwise.
- Use `normalized_key` values from the API responses. Do not invent keys.
- Sort `normalized_key` arrays alphabetically ascending.
- When reconciling duplicate candidate data against patient endpoint data, prefer the patient-active-list endpoints.

### ICD-10 Validation

- Look up each diagnosis code against `GET /api/icd10/{code}`.
- Record the `chapter` from the ICD-10 response.
- A code is valid if the endpoint returns a match (non-404).
- Narrative match: compare the ICD-10 description against the patient's active condition descriptions and the referral narrative.
- For orthopedic referrals, the expected chapter is `Musculoskeletal`. Codes from `Injury`, `Respiratory`, or other non-Musculoskeletal chapters are out-of-range.

### Evidence Reconciliation

- When a duplicate candidate preview exists, cross-check it against the live patient condition/medication/allergy endpoints. Items present in the live endpoints but absent from the duplicate preview must be reported as added.
- For merge packets, the target is the patient with the more complete/active record; the source is the duplicate shell.
- Document evidence: include only documents relevant to the packet purpose (continuity of care, identity verification). Exclude internal chart summaries and unrelated clinical documents.

### Sorting Conventions

- Arrays of string IDs: ascending alphabetical.
- Arrays of objects keyed by an ID field (`referral_id`, `encounter_id`, `group_id`): sort by that field ascending.
- Encounter arrays: newest-to-oldest by date unless the template says otherwise.
- Risk flag arrays: alphabetical by flag code.

## API Endpoints

See [references/api-endpoints.md](references/api-endpoints.md) for the complete endpoint catalog with field descriptions.

## Workflow Patterns

See [references/workflows.md](references/workflows.md) for step-by-step patterns for each task type: merge readiness packets, referral coordination, care transitions, duplicate-review with ServiceRequest, and batch audits.
