# EHR Quality-Governance Skill

## When to use

Invoke this skill when the task involves preparing a normalized JSON packet from an EHR (Electronic Health Record) quality-governance API. The task prompt will reference `<TASK_ENV_BASE_URL>`, an `input/payloads/answer_template.json`, and one or more case objects (patient IDs, duplicate candidate IDs, referral IDs, provider IDs, batch IDs, or service request IDs).

## Pre-flight — read these files first

1. **`environment_access.md`** — Resolves `<TASK_ENV_BASE_URL>` to the actual `base_url`. Lists every `allowed_endpoints` the API exposes. Treat this as the authoritative endpoint catalog; do not call endpoints not listed here.

2. **`input/payloads/answer_template.json`** — The exact JSON shape to return. It defines required top-level keys, field types, enum allowed values, set semantics, and ordering rules. Every field you emit must conform to the constraints in this template.

3. **The task prompt** (`prompt.txt` or equivalent) — Identifies the task type and provides the specific case-object identifiers. Read it to understand which endpoints are relevant and what domain the task falls into.

4. **Any supplementary payloads** in `input/payloads/` beyond `answer_template.json` — Some tasks include additional request objects (e.g., `merge_packet_request.json`) that carry structured parameters. Read all payload files present; do not assume only the answer template exists.

## API query strategy

The API is read-only. All calls are `GET`. Use the endpoints listed in `environment_access.md`.

### Resolve identifiers from the prompt

Extract every case-object identifier from the prompt before querying. Common identifier types and the endpoints they map to:

| Identifier type | Primary endpoint |
|---|---|
| `patient_id` | `GET /api/patients/{patient_id}` |
| `candidate_id` | `GET /api/duplicates/{candidate_id}` |
| `referral_id` | `GET /api/referrals/{referral_id}` |
| `provider_id` | `GET /api/providers/{provider_id}` |
| `service_request_id` | Use `GET /api/patients/{patient_id}/service-requests` and locate by ID |
| `batch_id` | `GET /api/referrals` with query/filter parameters |
| ICD-10 `code` | `GET /api/icd10/{code}` |
| service `code` | `GET /api/service-codes/{code}` |

### Gather evidence by domain

For each patient involved, fetch these resources in parallel where the endpoints are allowed:

- **Patient detail**: `GET /api/patients/{patient_id}`
- **Active clinical lists**: `conditions`, `medications`, `allergies` (one call each per patient)
- **Encounters**: `GET /api/patients/{patient_id}/encounters`
- **Documents**: `GET /api/patients/{patient_id}/documents`
- **Immunizations**: `GET /api/patients/{patient_id}/immunizations`
- **Disclosures**: `GET /api/patients/{patient_id}/disclosures`
- **Service requests**: `GET /api/patients/{patient_id}/service-requests`

For cross-cutting lookups:

- **Duplicate candidates**: `GET /api/duplicates/candidates` (list) or `GET /api/duplicates/{candidate_id}` (detail)
- **Referrals**: `GET /api/referrals` (search/list) or `GET /api/referrals/{referral_id}` (detail)
- **Providers**: `GET /api/providers` (directory) or `GET /api/providers/{provider_id}` (detail)
- **ICD-10**: `GET /api/icd10/{code}` for each diagnosis code encountered
- **Service codes**: `GET /api/service-codes/{code}` for validation
- **Audit logs**: `GET /api/audit-logs`

### Task-type query priorities

- **Duplicate merge readiness**: Start with the duplicate candidate detail, then fetch both patients' full clinical picture in parallel. Cross-reference demographic fields for match/conflict signals. Pull documents and audit logs relevant to both patients.
- **Referral coordination**: Start with the referral detail and the patient. Validate every diagnosis code against ICD-10. Pull encounters, documents, and the receiving provider. Check authorization and document completeness.
- **Care transition / handoff**: Start with the patient and the recipient provider. Fetch all active clinical lists, encounters (filter for relevance to the transition service line), immunizations, and disclosures.
- **Quality governance (duplicate + service request)**: Fetch the duplicate candidate and both patients, then the service request. Validate service codes and reason codes against their respective directories. Assess SBAR coverage on the service request.
- **Referral audit (batch)**: List all referrals for the batch, then for each referral fetch the patient and validate the diagnosis code against ICD-10. Group duplicates, detect anomalies, and assign action-plan tiers.

## Evidence reconciliation rules

### Clinical keys

Use `normalized_key` values from API responses when populating condition, medication, and allergy key arrays. Only include records with `status: "active"` unless the template explicitly calls for a different scope. Exclude stale, inactive, or entered-in-error records.

### Identity and match signals

When comparing two patient records (duplicate review):
- **Match signals**: Derive from demographic fields that are identical or equivalent (same DOB, same insurance, similar address, same phone, same given name).
- **Conflict signals**: Derive from demographic fields that differ materially (different DOB, different insurance, different address, different phone, different given name, opposite laterality in problem lists).

### Diagnosis code validation

For every ICD-10 code encountered:
- Look it up via `GET /api/icd10/{code}`.
- If the endpoint returns a result, the code is valid; record its chapter.
- Compare the chapter against the expected service line (e.g., `Musculoskeletal` for orthopedics).
- Check whether the code's narrative matches the patient's active conditions.

### Document and authorization checks

- A document or imaging study marked `final` counts as received and complete.
- A document marked `preliminary`, `cancelled`, or absent counts as missing.
- Authorization statuses (`approved`, `pending`, `denied`, `not_required`) determine readiness.
- Blocking issues are derived from missing required documents, missing authorization, incomplete allergy documentation, invalid diagnosis codes, or clinical mismatches.

### Encounter selection

When selecting a fixed number of encounters (e.g., "the four most relevant recent handoff encounters"):
- Filter to encounters relevant to the service line (by type, diagnosis codes, or care plan tags).
- Select the most recent N by date.
- If fewer than N relevant encounters exist, include all that qualify; note the shortfall in readiness.
- Exclude encounters that are stale (outside the relevant window) or unrelated.

### Risk flag derivation

Derive risk flags from the patient's active clinical picture:
- Map condition keys and medication keys to known risk categories (e.g., insulin + diabetes → `insulin_dependent_diabetes`; latex allergy → `latex_allergy`; fall-risk documentation → `fall_risk_note_required`).
- Each risk flag must be evidenced by at least one condition key, medication key, or encounter.

## Output construction rules

### JSON only

Return a single JSON object. Do not emit explanatory prose, markdown fences, or narrative text outside the JSON. The top-level keys must exactly match the `required_top_level_keys` (or `top_level_required_keys`) from the answer template.

### Enums

Every field with an `enum` constraint must use exactly one of the listed values. When the template provides `allowed_values` for an array of enums, only emit values from that list.

### Set semantics and ordering

Unless the template specifies a different ordering:
- Arrays described as sets or with `set_semantics: true` must be sorted alphabetically (case-sensitive, string order).
- Arrays of objects with a natural key must be sorted by that key (e.g., by `referral_id`, by `code`, by `risk_flag`).
- Arrays of encounter-like objects with dates must be sorted newest-to-oldest when the template says so.

### Dates

All date fields use `YYYY-MM-DD` format. Derive dates from API response fields; do not fabricate them.

### Booleans

Use JSON `true`/`false` (not strings). A boolean is `true` only when evidence directly supports it; default to `false` when evidence is absent or inconclusive.

### Null handling

Use `null` (not the string `"null"`) when a field is optional and no value can be determined. Only use `null` where the template's type allows it (e.g., `["string", "null"]`).

### Normalized keys

When populating `condition_keys`, `medication_keys`, or `allergy_keys` arrays, use the exact `normalized_key` string from the API response. Do not transform, truncate, or invent keys.

### Excluded distractors

When the template includes an `excluded_distractors` or similar section, populate it with items you reviewed but determined are not relevant: inactive conditions, non-merge medications, unrelated documents, or audit entries outside scope.

## Quality checklist

Before returning the JSON, verify:

1. Every required top-level key is present.
2. Every enum field uses an allowed value.
3. Set-semantics arrays are sorted.
4. All patient IDs, provider IDs, document IDs, and other references match values returned by the API.
5. Count fields are consistent with the corresponding arrays (e.g., `invalid_or_out_of_range_count` equals the length of the `invalid_or_out_of_range_code_referrals` array).
6. Boolean readiness fields are consistent with the presence or absence of blocking issues.
7. No task-specific narrative or procedural text appears in the output.
8. Dates are in `YYYY-MM-DD` format and are drawn from API evidence.
