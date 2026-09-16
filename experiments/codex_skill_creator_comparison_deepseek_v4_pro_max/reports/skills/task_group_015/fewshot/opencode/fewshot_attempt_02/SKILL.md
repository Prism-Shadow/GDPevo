---
name: ehr-quality-packet
description: Prepare normalized EHR quality-governance packets from a FHIR-like REST API. Use this skill whenever the task involves assembling clinical reconciliation, referral coordination, care transition, duplicate-chart merge, service-request validation, or referral-audit JSON packets from endpoint families such as patients, conditions, medications, allergies, encounters, documents, immunizations, disclosures, duplicate candidates, referrals, service requests, ICD-10 codes, service codes, providers, and audit logs. Trigger when the user mentions EHR, FHIR, quality governance, clinical reconciliation, referral packet, care transition, duplicate merge, chart audit, or any combination of clinical-list + provider + code-validation API work.
---

# EHR Quality-Governance Packet Preparation

This skill guides the production of a normalized JSON packet from a read-only EHR governance REST API. The API surface is broad (patients, clinical lists, encounters, documents, duplicates, referrals, service requests, ICD-10/service-code directories, providers, audit logs) but the workflow follows a consistent pattern.

## Core principle

Treat the prompt and the supplied `answer_template.json` as the authoritative specification of what the packet must contain. The API is the source of truth for every field value. Never invent clinical data, provider names, or code descriptions -- pull them from the API and cross-reference them.

## Workflow

Follow this sequence for every packet task. Not every step applies to every task; let the answer template tell you which sections are relevant and skip steps that have no matching template key.

### 1. Read the prompt and the answer template

Read the prompt first to identify the primary entity IDs (patient IDs, referral IDs, duplicate candidate IDs, service-request IDs, batch IDs, provider IDs) and the packet type. Then read the supplied `answer_template.json` to understand the exact JSON shape, required keys, enum constraints, and array ordering rules.

Pay attention to these template signals:

- **`required_top_level_keys`** or **`top_level_required_keys`** -- every listed key must appear at the top level.
- **`required_keys`** inside an object -- every listed key must appear in that nested object.
- **`allowed_values`** or **`enum`** -- values must come from the listed set.
- **`set_semantics: true`** or **`ordering: sort ascending`** -- arrays are treated as sets; sort strings alphabetically unless the template explicitly overrides (e.g., "newest to oldest").
- **`required_value`** -- use the literal string given (e.g., `"task_id": "tXYZ"`).
- **`type: [string, null]`** -- the field may be `null` when there is no valid value.

### 2. Fetch the primary entities

Retrieve the core objects the packet is about. Use the API with the IDs from the prompt:

- **Patient**: `GET /api/patients/{patient_id}` -- returns demographics (name, DOB, MRN, insurance, phone, address, PCP, sex).
- **Referral**: `GET /api/referrals/{referral_id}` -- returns batch, service line, diagnosis code, narrative, urgency, authorization status, status, requested date.
- **Duplicate candidate**: `GET /api/duplicates/{candidate_id}` -- returns the two patient IDs, match/conflict signals, status.
- **Service request**: `GET /api/patients/{patient_id}/service-requests` and filter for the specific ID -- returns status, intent, priority, service code, requester, performer, authored date, occurrence date, reason codes.
- **Batch list**: `GET /api/referrals` with filtering to locate all referrals belonging to a batch by batch ID or date.

For tasks involving two patients (merge/reconciliation), fetch both patients independently and compare fields to identify match signals and conflict signals.

### 3. Fetch active clinical lists

For each relevant patient, gather the active clinical picture:

- `GET /api/patients/{patient_id}/conditions` -- each record has `code` (ICD-10), `description`, `normalized_key`, `source`, and `status`.
- `GET /api/patients/{patient_id}/medications` -- each record has `medication`, `dose`, `route`, `frequency`, `normalized_key`, and `status`.
- `GET /api/patients/{patient_id}/allergies` -- each record has `allergen`, `reaction`, `severity`, `normalized_key`, and `status`.

**Union rules**: When merging two patients or building a packet that spans patients, take the union of `normalized_key` values from **active** records only. Sort the union alphabetically. Records with a non-active status (inactive, entered-in-error, resolved) go into excluded/distractor arrays if the template expects them.

**Reconciliation**: If a duplicate-candidate preview provides its own clinical-key lists, cross-check them against the patient active-list endpoints. The authoritative source is the patient active-list endpoints. List any keys present in the patient endpoints but missing from the duplicate preview under the added-from-active-endpoints fields.

### 4. Fetch encounters

`GET /api/patients/{patient_id}/encounters` -- returns encounters with `encounter_id`, `date`, `type`, `provider_id`, `signed_status`, `diagnosis_codes`, and `medications_mentioned`.

**Selection rules**:
- For handoff/transition packets: pick the most recent 4 encounters (or the count specified by the template) that are relevant to the transition purpose. Exclude encounters that are stale, outside the clinical window, or unrelated to the packet's service line.
- For referral packets: identify the single most recent encounter whose diagnosis codes and medications align with the referral purpose.
- Document which encounters were considered but excluded, with reasons, in the `excluded_encounter_ids` field if the template expects it.

### 5. Fetch documents

`GET /api/patients/{patient_id}/documents` -- returns documents with `document_id`, `type`, `date`, and `status`.

**Selection policy**: Include only documents that support identity resolution or external continuity of care. Exclude internal chart summaries, administrative-only documents, and documents unrelated to the packet's service line unless the template explicitly requests them. For referral packets, check whether required document types (echocardiogram, office note, authorization, imaging) are present and final. List missing required documents in the appropriate field.

When the template has an `excluded_distractors.document_ids` array, list the document IDs that were reviewed but not included, sorted alphabetically.

### 6. Fetch other patient-scoped resources

Depending on what the answer template asks for, fetch these additional patient-scoped endpoints:

- **Immunizations**: `GET /api/patients/{patient_id}/immunizations` -- pick the most recent by date. Include only if the template has an immunization section.
- **Disclosures**: `GET /api/patients/{patient_id}/disclosures` -- look for a disclosure whose purpose matches the packet's intent and whose recipient matches the target provider. Include only if the template has a disclosure section.
- **Audit logs**: `GET /api/audit-logs` -- filter by patient ID or the packet's primary entity to find relevant audit entries. In merge packets, include audit entries that document the duplicate detection or record-linking events.

### 7. Validate codes

**ICD-10 codes**: For every diagnosis code that appears in the packet (from conditions, referrals, service-request reason codes, or encounters):

1. Call `GET /api/icd10/{code}` to verify the code exists and retrieve its `chapter` and official `description`.
2. Compare the ICD-10 chapter against the packet's service line. Orthopedic packets expect Musculoskeletal chapter codes. Cardiology packets expect Circulatory chapter codes. Codes from other chapters are `out_of_range_chapter`. Missing codes are `unknown_code`.
3. Compare the ICD-10 narrative against the referral diagnosis narrative or encounter diagnosis text. A `narrative_match` is true when the official ICD-10 description aligns with the clinical narrative. Also check laterality: if the narrative mentions "right knee" but the ICD-10 code specifies left knee, flag a `laterality_mismatch`.

**Service codes**: For service requests, call `GET /api/service-codes/{code}` to validate the service code exists and is appropriate for the service line.

When the template has a `reason_code_validation` array, produce an entry for each reason code with `code`, `valid` (boolean), `chapter`, and `matches_patient_evidence` (boolean). The `matches_patient_evidence` flag is true when the code appears in the patient's active conditions or in a recent relevant encounter.

### 8. Fetch provider directory

`GET /api/providers/{provider_id}` -- returns `provider_id`, `name`, `role`, `service_line`, `facility`, `phone`, and `fax`.

Look up every provider referenced in the packet: the receiving/specialist provider, the primary care provider, the encounter provider, the requester, and the performer. Do not invent provider names -- every provider contact must come from the directory.

For referral and transition packets, identify the correct receiving provider by matching the service line (e.g., `cardiology` for a cardiology referral, `orthopedics` for an orthopedic transition).

For merge packets, the specialist contact is the provider associated with the external continuity document on the source duplicate shell. Include the contact reason in the packet.

### 9. Assess readiness and classify

Readiness answers the question: can this packet be sent/acted on, or are there blockers?

Check these dimensions in order:

1. **Patient identity** -- both patients resolved? Primary entity found?
2. **Recipient/provider** -- receiving provider identified and available?
3. **Clinical lists** -- active condition/medication/allergy data present?
4. **Required documents** -- all required document types received and in final status?
5. **Authorization** -- for referrals, authorization approved? Not missing?
6. **Allergy documentation** -- allergies documented and consistent across sources? If conflicting allergy records exist, flag it.
7. **Code validity** -- diagnosis codes valid, in the correct chapter, and narrative matches?
8. **Disclosure** -- permitted and matches the recipient?

Synthesize these into a readiness enum value (e.g., `ready`, `ready_with_review_note`, `ready_with_risk_flags`, `not_ready`, `blocked`, `hold_for_authorization`, `hold_for_missing_documents`, `hold_for_clinical_clarification`). List any blocking issue codes or required review notes.

**Risk flags** (for transition packets): Derive from clinical evidence. Common flags include:
- `cognitive_memory_loss` -- memory-loss condition present
- `fall_risk_note_required` -- osteoarthritis conditions in lower extremities + pain medications
- `hypertension` -- hypertension condition present
- `insulin_dependent_diabetes` -- diabetes + insulin medication
- `latex_allergy` -- latex allergy on record
- `perioperative_glucose_plan_needed` -- diabetes + insulin + surgical context

Support each risk flag with evidence: which condition keys, medication keys, and encounter IDs justify it.

### 10. Classify referral audit items

For audit batch tasks, iterate over every referral row and classify:

- **Invalid or out-of-range codes**: diagnosis code chapter is not the expected chapter for the batch's service line, or the code is unknown.
- **Laterality or narrative mismatches**: ICD-10 laterality does not match the referral narrative, or the narrative body part/location does not match the code's official description. Classify mismatch types as `laterality_mismatch`, `narrative_mismatch`, or `missing_laterality`.
- **Duplicate groups**: referrals sharing the same patient ID and diagnosis code are potential same-patient resubmissions. Group them under a group ID and assign a `consolidate_under_original` disposition.
- **Insurance anomalies**: referrals from different patients sharing the same insurance ID. Flag but do not merge -- these need membership verification.
- **Follow-up queues**: separate referrals into authorization-missing, authorization-pending, records-request (missing office note), and imaging-follow-up queues.
- **Tier assignments**: 
  - **Tier 1** (immediate): duplicate-blocker referrals + referrals with urgent coding mismatches affecting patient safety.
  - **Tier 2** (short-term): referrals with coding, authorization, or document blockers that are routine.
  - **Tier 3** (administrative): referrals needing only document completion.
- **Summary counts**: count every category and include `validated_ready_no_follow_up_count` (referrals with no issues at all).

### 11. Produce the final JSON

Fill the answer template completely. Follow these formatting rules:

- **Dates**: always `YYYY-MM-DD`.
- **Arrays with set semantics**: sort strings alphabetically ascending. This includes condition keys, medication keys, allergy keys, document IDs, audit IDs, referral IDs, encounter IDs, reason codes, and match/conflict signals.
- **Arrays of objects**: follow the ordering rule stated in the template. Default to sorting by the primary identifier (`referral_id`, `group_id`, `code`).
- **Enums**: use only the exact string values listed in the template's `allowed_values` or `enum` constraints.
- **Booleans**: `true`/`false`, unquoted.
- **Nulls**: use JSON `null` (not the string `"null"`) when the template allows it and no valid value exists.
- **Numbers**: integers without quotes.

Before finalizing, verify that every `required_top_level_key` and `required_key` is present and that every array marked for set semantics is sorted.

## API reference

For detailed endpoint descriptions, field names, and response shapes, see [references/api-surface.md](references/api-surface.md). Load it when you need field-level detail about what a specific endpoint returns.

## Common pitfalls

- **Using duplicate-candidate preview data for clinical lists without cross-checking**. The preview may be stale or incomplete. Always validate against the patient active-list endpoints and treat those as authoritative.
- **Including inactive records in unions**. Only `active` status records belong in clinical union arrays. Records with status `inactive`, `entered-in-error`, or `resolved` go into excluded/distractor arrays.
- **Inventing provider names**. Every provider reference must come from a `GET /api/providers/{id}` call. If the API returns a provider you cannot find, list it under blocking issues rather than guessing.
- **Assuming the chapter from a code's prefix**. Always call the ICD-10 lookup endpoint. Some codes (like S83.241A) map to Injury, not Musculoskeletal, even if they sound orthopedic.
- **Forgetting to encode enums exactly**. The template's enum strings are literal contracts. `ready_to_merge` and `merge_ready` are different values. Use whichever the template specifies.
- **Unsorted set arrays**. Unless the template gives an explicit different ordering rule (like "newest to oldest"), sort alphabetically.
- **Omitting NULL fields the template allows**. If the template type is `["string", "null"]` and there is genuinely no value, use `null` -- don't omit the key.
