# EHR Quality-Governance Skill

This skill provides a reusable methodology for EHR quality-governance tasks. It teaches an agent how to read task prompts and answer templates, query a read-only EHR API, cross-reference clinical and administrative records, and produce normalized JSON answers.

## Setup

Every task supplies:
- A prompt file (`input/prompt.txt`) describing the case, identifiers, and expected outputs.
- An answer template (`input/payloads/answer_template.json`) defining the exact JSON shape to return.
- An environment access file (`environment_access.md`) with the base URL and available API endpoints.

Read all three inputs before making any API calls. Map the prompt's identifiers (patient IDs, candidate IDs, referral IDs, batch IDs, provider IDs, ServiceRequest IDs) to the fields described in the answer template.

## Environment & API

The EHR environment is a read-only REST API reachable at the base URL from the environment access file. All endpoints use `GET`. Replace path placeholders (`{patient_id}`, `{referral_id}`, `{candidate_id}`, `{code}`, `{provider_id}`) with runtime values.

### Endpoint Reference

| Endpoint | Purpose |
|---|---|
| `/api/patients?q=&family=&given=&dob=&insurance_id=` | Search patients |
| `/api/patients/{patient_id}` | Patient demographics |
| `/api/patients/{patient_id}/conditions` | Active/inactive problem list |
| `/api/patients/{patient_id}/medications` | Active/inactive medications |
| `/api/patients/{patient_id}/allergies` | Allergy records |
| `/api/patients/{patient_id}/encounters?status=&limit=` | Encounter history |
| `/api/patients/{patient_id}/immunizations` | Immunization records |
| `/api/patients/{patient_id}/documents` | Clinical documents |
| `/api/patients/{patient_id}/service-requests` | Ordered service requests |
| `/api/patients/{patient_id}/disclosures` | Disclosure authorizations |
| `/api/audit-logs?patient_id=&event=&date_from=&date_to=` | Audit trail |
| `/api/duplicates/candidates` | List duplicate candidates |
| `/api/duplicates/{candidate_id}` | Single candidate detail |
| `/api/referrals?batch=&urgency=&patient=&status=` | Referral search |
| `/api/referrals/{referral_id}` | Single referral detail |
| `/api/icd10/{code}` | ICD-10 code metadata |
| `/api/providers/{provider_id}` | Provider directory |
| `/api/service-codes/{code}` | Service code validation |

### Base URL Resolution

The prompt references `<TASK_ENV_BASE_URL>` or `$TASK_ENV_BASE_URL`. Resolve this to the actual base URL from the environment access file before calling endpoints.

## Answer Format Rules

- Return **only** the JSON object. Do not include explanatory prose, narrative notes, or SOP text outside the JSON.
- All arrays annotated as sets in the template must be sorted **alphabetically** (ascending by string value) unless the template states a different ordering rule.
- Dates use `YYYY-MM-DD` format.
- Use `null` (not the string `"null"`) for missing optional fields.
- Boolean fields use JSON `true`/`false`.
- Enum fields must match one of the allowed values exactly.
- Referral-object arrays are sorted by `referral_id` ascending unless otherwise specified.
- Duplicate groups are sorted by `group_id` ascending, with internal `referral_ids` sorted ascending.

## Data Collection Strategy

### Standard Patient Data Collection

For any patient ID mentioned in the prompt, collect:
1. **Demographics**: `GET /api/patients/{patient_id}` for name, DOB, MRN, sex, insurance, address, phone, PCP.
2. **Active conditions**: `GET /api/patients/{patient_id}/conditions` — filter for `status: active`. Extract `normalized_key` values.
3. **Active medications**: `GET /api/patients/{patient_id}/medications` — filter for `status: active`. Extract `normalized_key` values.
4. **Active allergies**: `GET /api/patients/{patient_id}/allergies` — filter for `status: active`. Extract `normalized_key` values.
5. **Encounters**: `GET /api/patients/{patient_id}/encounters` — note date, type, signed status, provider, diagnosis codes.
6. **Documents**: `GET /api/patients/{patient_id}/documents` — note document ID, type, date, status.
7. **Immunizations**: `GET /api/patients/{patient_id}/immunizations` — find most recent by date.
8. **Disclosures**: `GET /api/patients/{patient_id}/disclosures` — match to relevant provider or purpose.
9. **Service Requests**: `GET /api/patients/{patient_id}/service-requests` — if referenced in the task.

### Cross-Reference Validation

When validating diagnosis codes:
1. Call `GET /api/icd10/{code}` for each code to retrieve the chapter, description, and validity.
2. Compare the code's chapter against the expected chapter for the service line (e.g., `Musculoskeletal` for orthopedics).
3. Check that the code's description aligns with the patient's active condition list (look for `normalized_key` matches).
4. Flag codes as invalid if the ICD-10 endpoint returns an error or the chapter is out of range.

### Duplicate Candidate Analysis

When a duplicate candidate is referenced:
1. Call `GET /api/duplicates/{candidate_id}` to retrieve match/conflict signals, status, and the patient pair.
2. Collect full demographic data for BOTH patients.
3. Compare identity fields: DOB, insurance ID, phone, address, name (given/family), sex, PCP ID.
4. Look for external/continuity documents linking the two records (e.g., documents shared across both patient IDs).
5. Determine merge target (the patient with more complete/active records) and source.

### Referral Analysis

For referral tasks:
1. Call `GET /api/referrals/{referral_id}` for detail: diagnosis code, narrative, urgency, batch, status, authorization, receiving provider.
2. Cross-reference the referral's diagnosis code with `GET /api/icd10/{code}` for chapter, validity, and laterality information.
3. Compare the code's narrative against the patient's known conditions for narrative-match validation.
4. Check for required documents: echocardiogram (cardiology), office notes, imaging.
5. Check authorization status from the referral record.

### Batch Audit Analysis

When auditing a referral batch:
1. Call `GET /api/referrals?batch={batch_id}` to retrieve all rows.
2. For each referral, validate the diagnosis code against ICD-10.
3. Group referrals by patient to detect duplicates (same patient, same code, overlapping dates = resubmission).
4. Check for shared insurance IDs across different patients (possible membership or identity issue).
5. Categorize each referral into follow-up queues: authorization missing, authorization pending, records request, imaging follow-up.
6. Assign tiers: Tier 1 for urgent coding/duplicate blockers, Tier 2 for routine coding/auth/document blockers, Tier 3 for administrative document completion.
7. Assign each referral to an owner provider (typically from the provider directory or the referral's performer).

## Task-Type Patterns

### Merge Readiness Packet (Duplicate Merge)

**Core outputs:** merge target/source, disposition, clinical key unions, identity signals, evidence IDs, provider contacts, packet readiness.

**Key steps:**
1. Pull the duplicate candidate to get match/conflict signals and the patient pair.
2. Collect active clinical lists (conditions, medications, allergies) from BOTH patients.
3. Compute the union of normalized keys across both patients — this is the preserved clinical set after merge.
4. Reconcile the duplicate candidate's preview data against the patient active-list endpoints; note any keys found only via direct endpoints.
5. Identify match signals (fields that agree) and conflict signals (fields that differ).
6. Select evidence documents: identity-related documents and external continuity documents. Exclude routine chart summaries and unrelated documents.
7. Collect audit log entries relevant to the merge candidate.
8. Identify the specialist provider associated with any external continuity document and the primary care provider.
9. Determine readiness: ready if all evidence is present and signals strongly support merge; blocked if critical conflicts exist.

**Key exclusions:**
- Inactive conditions/medications (status not `active`) are distractors and go into `excluded_distractors`.
- Documents that are not identity or external continuity documents are excluded.
- Audit entries unrelated to the duplicate candidate are excluded.

### Referral Coordination Packet

**Core outputs:** patient referral info, active diagnoses, referral code set validation, allergy readiness, encounter evidence, document evidence, receiving provider, authorization readiness, medication highlights, referral letter fields.

**Key steps:**
1. Pull the referral detail to get diagnosis code, batch, service line, urgency, authorization status.
2. Pull the patient's active conditions and cross-reference with the referral's primary diagnosis code.
3. Validate the primary code via ICD-10 lookup: check validity, chapter, narrative match against patient evidence.
4. Collect allergy records from the patient. Determine readiness: complete if active allergies are documented; incomplete if conflicting or missing.
5. Find the most recent encounter that is relevant to the referral reason (look for matching diagnosis codes and care-plan alignment).
6. Check for required documents (e.g., echocardiogram for cardiology, office note). Flag any missing required documents.
7. Identify the receiving provider from the referral record or provider directory.
8. Collect active medications and highlight those relevant to the referral's clinical domain (e.g., diuretics for heart failure, antihypertensives for blood pressure).
9. Produce referral letter field choices: each field maps to a normalized enum value reflecting the evidence collected.
10. Determine overall readiness: `ready_to_send` if no blockers; `hold_for_*` if authorization, documents, or clinical clarification needed.

### Care Transition Packet

**Core outputs:** patient demographics, recipient provider, active clinical keys, recent handoff encounters, immunization, disclosure, risk flags with evidence, packet readiness.

**Key steps:**
1. Pull patient demographics and the recipient provider from the provider directory.
2. Collect active condition, medication, and allergy normalized keys.
3. Select the most relevant recent encounters (typically 4) for the care transition. Prefer signed encounters with relevant clinical content. Encounters should be ordered newest to oldest.
4. Exclude stale encounters (outside the handoff window or clearly unrelated to the transition).
5. Find the most recent immunization by date.
6. Find the disclosure authorization that matches the recipient provider and transition purpose. Check status is `permitted`.
7. Derive risk flags from the clinical picture. Each risk flag needs evidence: condition keys, medication keys, and encounter IDs that support it.
8. Risk flag evidence items are sorted by risk flag name ascending; internal arrays sorted ascending.
9. Packet readiness: `ready` if no flags and all data present; `ready_with_risk_flags` if flags present but no blockers; `not_ready` if critical data missing.

### Duplicate + Service Request Quality Review

**Core outputs:** duplicate review decision, service request validation, SBAR coverage assessment.

**Key steps:**
1. Pull the duplicate candidate and evaluate match/conflict signals. Determine if the pair is a confirmed duplicate, needs review, or is not a duplicate.
2. If there are strong match signals but also significant conflicts (different given names, opposite laterality), the decision is `review_hold`.
3. Pull the service request detail, then validate each reason code against ICD-10: check validity, chapter, and whether it matches the patient's active condition evidence.
4. Validate the service code against the service-codes endpoint.
5. Check that the performer provider's service line matches the expected service line.
6. Assess SBAR coverage: check if the service request or related documentation includes situation, background, assessment, and recommendation sections.

### Referral Batch Audit

**Core outputs:** batch summary, invalid-code referrals, mismatch referrals, duplicate groups, insurance anomalies, follow-up queues, tiered action plan, summary counts.

**Key steps:**
1. Pull all referrals in the batch.
2. For each referral, look up the diagnosis code in ICD-10. Flag as `out_of_range_chapter` if the chapter is not the expected service-line chapter (e.g., not `Musculoskeletal` for orthopedics). Flag as `unknown_code` if the ICD-10 lookup fails entirely.
3. Compare the diagnosis code's ICD-10 description with the referral's narrative text and the patient's condition list. Check for laterality agreement (left vs right), narrative alignment, and missing laterality.
4. Detect duplicate groups: referrals with the same patient and same diagnosis code, where one is a resubmission of another. The duplicate(s) get `REF-*-DUP` style IDs.
5. Check for insurance anomalies: different patients sharing the same insurance ID (possible identity issue) or same patient with separate non-duplicate referrals.
6. Build follow-up queues from the referral data: authorization missing/pending, records (office notes) needed, imaging follow-up needed.
7. Build the tiered action plan: Tier 1 for urgent coding blockers + duplicate blockers, Tier 2 for routine coding/auth/document blockers, Tier 3 for administrative document completion.
8. Assign each referral to its performing/owner provider.
9. Compute summary counts: total rows, unique patients, urgency counts, issue counts, tier counts, and the validated-ready-with-no-follow-up count.

## Common Pitfalls

- **Do not include inactive records** in active key unions unless the template explicitly asks for them. Filter by status.
- **Do not include routine chart summaries** as merge evidence documents; only identity and external continuity documents.
- **Validate every ICD-10 code** against the directory before using it; an invalid code should be flagged, not silently accepted.
- **Sort consistently**: use alphabetical/numeric ascending sort for string arrays unless the template specifies otherwise.
- **Distinguish separate clinical referrals from duplicates**: same patient with different diagnosis codes or clinical intent = separate referrals, not duplicates.
- **Check laterality in both code and narrative**: an ICD-10 code like `M17.11` (right knee) paired with narrative "left knee osteoarthritis" is a laterality mismatch.
- **Authoritative source for clinical lists**: prefer patient active-list endpoints over the duplicate-candidate preview when reconciling, as the endpoints contain the ground truth.
