## Overview

This skill handles EHR (Electronic Health Record) quality-governance and clinical data normalization tasks against a read-only FHIR-aligned REST API. It covers merge-readiness packets, referral coordination, care-transition summaries, duplicate review, ServiceRequest quality validation, and batch referral audits. Every task produces strictly normalized JSON output conforming to a supplied answer template.

## Environment

- Base URL: `<TASK_ENV_BASE_URL>` (also aliased as `<GDPEVO_ENV_BASE_URL>`).
- All endpoints are **GET only**. No authentication is required.
- Query parameters: use only the supported parameters listed below; do not invent additional filters. Append them as standard URL query strings (e.g. `?status=active&limit=10`).

### Endpoint Reference

**Patient endpoints**

| Endpoint | Supported Query Parameters |
|---|---|
| `GET /api/patients` | `q`, `family`, `given`, `dob`, `insurance_id` |
| `GET /api/patients/{patient_id}` | none |
| `GET /api/patients/{patient_id}/conditions` | `status` |
| `GET /api/patients/{patient_id}/medications` | `status` |
| `GET /api/patients/{patient_id}/allergies` | `status` |
| `GET /api/patients/{patient_id}/encounters` | `status`, `limit` |
| `GET /api/patients/{patient_id}/immunizations` | none |
| `GET /api/patients/{patient_id}/documents` | `status` |
| `GET /api/patients/{patient_id}/service-requests` | none |
| `GET /api/patients/{patient_id}/disclosures` | none |

**Audit and governance endpoints**

| Endpoint | Supported Query Parameters |
|---|---|
| `GET /api/audit-logs` | `patient_id`, `event`, `date_from`, `date_to` |
| `GET /api/duplicates/candidates` | none |
| `GET /api/duplicates/{candidate_id}` | none |

**Referral endpoints**

| Endpoint | Supported Query Parameters |
|---|---|
| `GET /api/referrals` | `batch`, `urgency`, `patient`, `status` |
| `GET /api/referrals/{referral_id}` | none |

**Reference-data endpoints**

| Endpoint | Supported Query Parameters |
|---|---|
| `GET /api/icd10` | none |
| `GET /api/icd10/{code}` | none |
| `GET /api/providers` | none |
| `GET /api/providers/{provider_id}` | none |
| `GET /api/service-codes` | none |
| `GET /api/service-codes/{code}` | none |

## Workflow: General Task Execution

1. **Read the prompt** → identify the task type and the primary entities (patient IDs, referral IDs, duplicate candidate IDs, ServiceRequest IDs, batch IDs).
2. **Read the answer template** (`input/payloads/answer_template.json`) → understand the required output shape, field types, enums, and ordering rules.
3. **Fetch primary entity data** → use the relevant detail endpoint (patient, referral, duplicate candidate, ServiceRequest).
4. **Fetch related clinical data** → chain from the primary entity: conditions, medications, allergies, encounters, immunizations, documents, disclosures, audit logs.
5. **Fetch reference data** → ICD-10 codes, providers, service codes as needed for validation.
6. **Cross-reference and validate** → confirm codes exist in directories, verify laterality, detect mismatches, reconcile data sources.
7. **Build the normalized output** → follow all sorting, filtering, and enum rules from the template. Return only JSON.

## Data Normalization Rules

### Clinical Record Keys

- Use the **`normalized_key`** field from condition, medication, and allergy records as the canonical identifier.
- Never construct your own keys or use raw display names as keys.

### Active vs. Inactive Filtering

- When a template or prompt calls for **active** clinical lists (conditions, medications, allergies), filter records where `status` equals `"active"` (case-sensitive).
- Records with status `"inactive"`, `"resolved"`, `"entered-in-error"`, or any other value are **excluded** from active sets unless a template explicitly instructs otherwise.

### Sorting Rules (Default)

| Data Shape | Default Sort |
|---|---|
| Array of strings (e.g. keys, IDs) | Alphabetical ascending (case-sensitive) |
| Array of objects with an ID field | By that ID field ascending |
| Array of date-tagged objects | Newest-to-oldest by date, or as specified in template |
| Sets (order-independent per template) | Still apply alphabetical sort unless template says order-independent |

- If a template states "order-independent" or "set semantics", still emit sorted output defensively.
- For `referral_id` arrays: sort ascending.
- For `patient_id` arrays: sort ascending.

### Deduplication

- When merging clinical keys from two or more patients (e.g. duplicate merge), produce a **set union**: include each distinct key once, sorted alphabetically.
- When merging objects, deduplicate by the primary identifier field (e.g. `code`, `document_id`).

### Date Format

- All dates use **YYYY-MM-DD** format.

## Exclusion & Distractor Rules

- **Exclude** records belonging to patients not named in the task.
- **Exclude** inactive/resolved/entered-in-error clinical items from active lists.
- **Exclude** documents, audit log entries, and encounters that are unrelated to the task's clinical context or time window.
- When a template provides a distractor section, list every item that was reviewed and excluded, with a clear exclusion reason implied by the section it belongs to.

## Validation Patterns

### ICD-10 Code Validation

1. Look up every diagnosis code via `GET /api/icd10/{code}`.
2. If the endpoint returns data, the code is **valid**; capture its `chapter` and `description`.
3. If the endpoint returns an error or empty response, the code is **invalid/unknown**.
4. For service-line-specific tasks (e.g. orthopedics, cardiology), verify the ICD-10 chapter matches the expected service chapter. Flag `out_of_range_chapter` mismatches.

### Laterality & Narrative Checking

- Compare the diagnosis code's laterality properties (from the ICD-10 directory) with the patient's clinical evidence.
- When the ICD-10 description contains laterality terms (left, right, bilateral) that conflict with patient conditions or the referral narrative, flag a `laterality_mismatch`.
- When the ICD-10 description/text does not match the diagnosis narrative in the referral, flag a `narrative_mismatch`.
- When laterality is expected but absent, flag `missing_laterality`.

### Service Code Validation

- Look up service codes via `GET /api/service-codes/{code}`.
- Flag any code that does not resolve in the directory.

### Provider Validation

- Look up providers via `GET /api/providers/{provider_id}`.
- Confirm the provider's `service_line` matches the task context (e.g. orthopedics for an orthopedic referral).
- Extract provider contact details (name, facility, phone, fax, role) for output.

## Duplicate & Merge Handling

1. Fetch the duplicate candidate via `GET /api/duplicates/{candidate_id}`.
2. Extract match signals and conflict signals from the candidate record.
3. Independently fetch both patients via `GET /api/patients/{patient_id}`.
4. Compare demographic fields: DOB, given name, family name, address, phone, insurance. Record matches and conflicts.
5. Fetch active clinical lists for both patients. Compute the sorted union of `normalized_key` values from both sets.
6. **Reconcile** the duplicate preview data with the authoritative patient active-list endpoints. The patient endpoints are authoritative; any keys present in patient endpoints but missing from the duplicate preview must be noted as added.
7. Determine disposition:
   - `ready_to_merge` / `merge_ready`: strong match signals, no blocking conflicts.
   - `needs_review` / `merge_ready_with_conflict_review`: merge-appropriate but some conflicts need human review.
   - `do_not_merge` / `needs_manual_review`: conflicts or evidence suggest the records are not duplicates.
8. Select the merge target (the patient ID that survives) and source (the ID to be absorbed). Typically the patient with more complete records is the target.

## Referral Coordination Patterns

1. Fetch the referral via `GET /api/referrals/{referral_id}`.
2. Fetch the patient, their active conditions/medications/allergies, recent encounters, and documents.
3. Validate referral diagnosis codes against the ICD-10 directory.
4. Identify the receiving (performing) provider from the referral, and fill provider details from the provider directory.
5. Assess authorization status from the referral record (approved, pending, denied, not_required).
6. Determine overall readiness: `ready_to_send`, `hold_for_authorization`, `hold_for_missing_documents`, `hold_for_clinical_clarification`.
7. Select normalized letter-field choices that match the clinical evidence (not generic defaults).

## Batch Audit Patterns

1. Fetch all referrals in the batch via `GET /api/referrals?batch={batch_id}`.
2. For each referral, validate its diagnosis code(s) against the ICD-10 directory.
3. Classify issues:
   - **Invalid/out-of-range**: code unknown or wrong chapter.
   - **Laterality/narrative mismatch**: code description conflicts with patient evidence or referral narrative.
   - **Duplicate group**: same patient, same clinical context, submitted more than once.
   - **Insurance anomaly**: shared insurance across different patients, or same patient with separate clinical referrals.
4. Build follow-up queues keyed by issue type: `authorization_missing`, `authorization_pending`, `records_request`, `imaging_follow_up`.
5. Assign tiered action plans:
   - **Tier 1** (immediate): urgent coding errors or duplicate blockers.
   - **Tier 2** (short-term): routine coding, authorization, or document blockers.
   - **Tier 3** (administrative): document completion tasks.
6. Produce summary counts for every tracked category.
7. For duplicate groups: assign a `group_id`, list all referral IDs in the group, classify the duplicate type, and recommend disposition (typically `consolidate_under_original`).

## Care Transition Patterns

1. Fetch the patient, recipient provider, and all clinical lists (conditions, medications, allergies).
2. Extract only `active` records; exclude inactive/resolved items.
3. Select handoff encounters: choose the most recent encounters relevant to the transition's clinical context. Exclude stale encounters beyond a reasonable recency window and encounters unrelated to the transition reason.
4. Identify the latest immunization record.
5. Locate the applicable disclosure record for the recipient provider, checking that its status is `permitted`.
6. Derive risk flags from clinical evidence: use active condition keys, medication keys, and encounter evidence to justify each flag. Every flag must cite supporting evidence.
7. Determine packet readiness: `ready` (no blocking issues), `ready_with_risk_flags` (sendable but flags present), or `not_ready` (blocking issues prevent sending).

## SBAR Coverage Assessment

- SBAR sections are: `situation`, `background`, `assessment`, `recommendation`.
- Evaluate whether each section is present in the relevant documentation (e.g. a ServiceRequest or clinical note).
- Report `complete: true` only when all four sections are present and none are missing.

## Output Format Rules

- **Return only JSON.** No narrative prose, markdown fences, explanatory text, or procedural notes outside the JSON object.
- Conform exactly to the answer template's top-level keys, field types, and enum values.
- Use the exact enum string values from the template. Do not paraphrase or substitute.
- Boolean fields must be JSON `true` or `false` (not strings).
- `null` is an accepted value when a template field is nullable and data is genuinely missing. Do not use empty strings or `"N/A"`.
- Every decision in the output must be defensible from API evidence: cite record IDs, codes, and keys in the output where the template provides slots for them.

## Anti-Patterns

- Do **not** assume data consistency: always verify against canonical endpoints even when a preview/summary endpoint provides similar data.
- Do **not** invent diagnosis codes, provider IDs, document IDs, or any identifier not present in the API responses.
- Do **not** skip ICD-10 directory lookups and assume codes are valid.
- Do **not** include inactive clinical records in active lists.
- Do **not** output narrative explanations when the template calls for structured JSON.
- Do **not** modify the template's key names, structure, or enum vocabulary.
- Do **not** use a duplicate preview as the authoritative source for active clinical lists when the patient-specific endpoints are available.
