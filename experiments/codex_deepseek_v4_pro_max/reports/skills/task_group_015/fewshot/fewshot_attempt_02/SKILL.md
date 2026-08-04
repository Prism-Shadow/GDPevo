 # EHR Quality-Governance API Skill

 ## Overview

 This skill equips an agent to complete EHR (Electronic Health Record) quality-governance and clinical-data coordination tasks against a read-only REST API. The tasks cover duplicate-chart merge readiness, referral coordination, care-transition packets, service-request quality review, and batch referral audits.

 ## Environment Setup

 Read `environment_access.md` from the workspace root to obtain:

- `TASK_ENV_BASE_URL` — the base URL for all API calls
- The list of allowed `GET` endpoints and supported query parameters

All API calls are read-only `GET` requests. No authentication credentials are required.

## Task Workflow

For every task, follow this sequence:

1. **Read the prompt** (`input/prompt.txt`) to identify the task type, patient/referral/candidate IDs, and specific outputs required.
2. **Read the answer template** (`input/payloads/answer_template.json`) to understand the exact JSON schema, required keys, enum values, and ordering rules.
3. **Read any additional staged payloads** (e.g., `merge_packet_request.json`) present in the payloads directory for extra context.
4. **Query the API** to collect all evidence from the environment:
   - Start with the primary entity (patient, duplicate candidate, referral, or service request).
   - Follow with related clinical lists (conditions, medications, allergies).
   - Pull supporting records (encounters, documents, immunizations, disclosures, audit logs, providers).
   - Use ICD-10 and service-code lookups for code validation.
5. **Assemble the normalized JSON** output conforming strictly to the answer template.

## API Endpoint Reference

### Patient Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/patients` | Search patients by `q`, `family`, `given`, `dob`, `insurance_id` |
| `GET /api/patients/{patient_id}` | Patient demographics (name, DOB, sex, MRN, address, phone, insurance, PCP) |
| `GET /api/patients/{patient_id}/conditions` | Active/inactive problem list with `code`, `description`, `normalized_key`, `status` |
| `GET /api/patients/{patient_id}/medications` | Active/inactive medications with `medication`, `dose`, `route`, `frequency`, `normalized_key`, `status` |
| `GET /api/patients/{patient_id}/allergies` | Allergy records with `allergen`, `reaction`, `severity`, `normalized_key`, `status` |
| `GET /api/patients/{patient_id}/encounters` | Encounters with optional `status` and `limit` query params |
| `GET /api/patients/{patient_id}/immunizations` | Immunization records |
| `GET /api/patients/{patient_id}/documents` | Clinical documents |
| `GET /api/patients/{patient_id}/service-requests` | Service request records |
| `GET /api/patients/{patient_id}/disclosures` | Disclosure/consent records |

### Governance & Referral Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/audit-logs` | Audit trail with `patient_id`, `event`, `date_from`, `date_to` filters |
| `GET /api/duplicates/candidates` | List duplicate candidates |
| `GET /api/duplicates/{candidate_id}` | Detail for a duplicate candidate (match/conflict signals, patient links) |
| `GET /api/referrals` | Search referrals by `batch`, `urgency`, `patient`, `status` |
| `GET /api/referrals/{referral_id}` | Single referral detail (diagnosis code, status, authorization, provider, documents) |
| `GET /api/icd10` | ICD-10 code directory |
| `GET /api/icd10/{code}` | Single ICD-10 code detail (description, chapter) |
| `GET /api/providers` | Provider directory |
| `GET /api/providers/{provider_id}` | Provider detail (name, role, facility, phone, fax, service_line) |
| `GET /api/service-codes` | Service code directory |
| `GET /api/service-codes/{code}` | Single service code detail |

## Task-Type Patterns

### Pattern A: Duplicate-Chart Merge Readiness

**Triggers**: `merge_packet_request.json` in payloads, prompt mentions "duplicate candidate", "merge readiness packet".

**API call order**:
1. `GET /api/duplicates/{candidate_id}` — get match/conflict signals, linked patient IDs
2. For each patient: demographics, conditions, medications, allergies, encounters, documents, audit logs
3. `GET /api/providers/{provider_id}` for PCP and any specialist referenced in documents

**Key decisions**:
- **Merge target**: the patient with the richer active clinical record (more conditions/meds/allergies) or the one the duplicate candidate points to as canonical
- **Merge source**: the other (duplicate) patient
- **Disposition**: `ready_to_merge` when identity signals align, source marked duplicate to target, target is active; `needs_review` when conflicting signals exist; `do_not_merge` when clearly different patients
- **Clinical unions**: collect `normalized_key` values from `active` status records only, across both patients, sorted alphabetically
- **Evidence**: include document IDs and audit IDs directly tied to the duplicate detection or merge event; exclude unrelated diagnostic documents
- **Excluded distractors**: inactive clinical items and documents/audit entries unrelated to the merge decision
- **Document selection policy**: include only identity-related or external continuity documents; exclude chart summaries and internal-only records

### Pattern B: Referral Coordination Packet

**Triggers**: Prompt mentions "referral coordination packet", a specific referral ID, and a specific patient ID.

**API call order**:
1. `GET /api/referrals/{referral_id}` — referral detail
2. `GET /api/patients/{patient_id}` — patient demographics
3. Patient clinical lists: conditions, medications, allergies
4. Patient encounters (filter recent, signed)
5. Patient documents (look for required types: echo, office note)
6. `GET /api/icd10/{code}` for diagnosis code validation
7. `GET /api/providers/{provider_id}` for receiving/requester providers

**Key decisions**:
- **Active diagnoses**: include all active conditions; mark referral-relevant ones based on the referral's clinical context
- **Referral code set**: validate the primary diagnosis code against ICD-10 directory; check chapter alignment with the expected service line; verify narrative match with the patient's clinical picture
- **Allergy readiness**: check that allergy records are complete and there are no conflicting entries
- **Recent encounter**: select the most recent signed encounter that aligns with the referral reason
- **Required documents**: verify echo (for cardiology), office note, authorization, medication list, allergy confirmation
- **Authorization**: check referral status, urgency, and authorization status to determine overall readiness
- **Medication highlights**: pull active medications; highlight those relevant to the referral's clinical context

### Pattern C: Care Transition Packet

**Triggers**: Prompt mentions "care transition packet", a patient ID, and a recipient provider ID.

**API call order**:
1. `GET /api/patients/{patient_id}` — demographics
2. Patient clinical lists: conditions, medications, allergies
3. Patient encounters (sort by date descending; select the most recent relevant handoff encounters)
4. Patient immunizations (select most recent)
5. Patient disclosures (find the one matching the recipient provider)
6. Patient documents (optional; for risk-flag evidence)
7. `GET /api/providers/{provider_id}` — recipient detail

**Key decisions**:
- **Handoff encounters**: select the four most recent signed encounters within a reasonable surgical handoff window; exclude stale or unrelated encounters
- **Latest immunization**: pick the most recent by date
- **Disclosure**: match by recipient provider ID and ensure status is `permitted`
- **Risk flags**: derive from active conditions and medications — e.g., diabetes + insulin → `insulin_dependent_diabetes` and `perioperative_glucose_plan_needed`; latex allergy → `latex_allergy`; memory loss condition → `cognitive_memory_loss`; osteoarthritis plus pain meds → `fall_risk_note_required`; hypertension → `hypertension`
- **Risk flag evidence**: for each flag, cite the condition keys, medication keys, and encounter IDs that support it
- **Packet readiness**: `ready` if no blockers; `ready_with_risk_flags` if risk flags exist but no blockers; `not_ready` if required data missing

### Pattern D: Service Request Quality Review with Duplicate Check

**Triggers**: Prompt mentions "duplicate candidate" + "ServiceRequest" + "SBAR coverage".

**API call order**:
1. `GET /api/duplicates/{candidate_id}` — duplicate candidate detail
2. For each linked patient: demographics, conditions
3. `GET /api/patients/{patient_id}/service-requests` — find the specific service request
4. `GET /api/icd10/{code}` for each reason code
5. `GET /api/service-codes/{code}` for service code validation
6. `GET /api/providers/{provider_id}` for requester and performer

**Key decisions**:
- **Duplicate review**: extract match/conflict signals from the duplicate candidate; decide merge/review_hold/do_not_merge based on signal strength
- **Service request**: validate status, intent, priority, service code, reason codes against environment evidence
- **Reason code validation**: for each ICD-10 reason code, check validity, chapter, and whether it matches the patient's active condition list
- **SBAR coverage**: check that the service request note includes all four sections (situation, background, assessment, recommendation)

### Pattern E: Batch Referral Audit

**Triggers**: Prompt mentions "referral audit", a batch ID, and "audit".

**API call order**:
1. `GET /api/referrals?batch={batch_id}` — all referrals in the batch
2. For each referral: `GET /api/referrals/{referral_id}` for detail
3. For each unique diagnosis code: `GET /api/icd10/{code}` for chapter/validity
4. For each unique patient: `GET /api/patients/{patient_id}` for demographics/insurance
5. `GET /api/providers` and `GET /api/providers/{provider_id}` for provider assignment

**Key decisions**:
- **Invalid/out-of-range codes**: referrals where the ICD-10 chapter is not the expected service-line chapter (e.g., orthopedic referrals must be Musculoskeletal chapter) or the code is unknown
- **Laterality/narrative mismatches**: code-narrative pairs where the ICD-10 description conflicts with the referral narrative (e.g., code says "left knee" but narrative says "right knee", or narrative doesn't match the code's clinical meaning)
- **Duplicate groups**: same patient with multiple referrals in the batch; distinguish between resubmissions (consolidate) and separate clinical reviews (keep separate)
- **Insurance anomalies**: different patients sharing the same insurance ID (possible membership issue), or same patient with separate clinical referrals
- **Follow-up queues**: categorize by authorization_missing, authorization_pending, records_request (missing office notes), imaging_follow_up (missing/pending imaging)
- **Action plan tiering**: Tier 1 for urgent coding or duplicate blockers; Tier 2 for routine coding/auth/document blockers; Tier 3 for administrative document completion
- **Summary counts**: compute all counts from the classified results

## Normalization Rules

### Sorting

- Arrays of strings (IDs, keys, codes): sort alphabetically ascending unless the template specifies otherwise.
- Arrays of objects with IDs: sort by the ID field ascending (e.g., `referral_id`, `group_id`, `anomaly_id`).
- Encounter arrays: newest to oldest by date unless the template specifies otherwise.
- Diagnosis arrays: by `code` ascending.

### Clinical Key Normalization

- Use `normalized_key` values from API responses directly. These are snake_case, lowercase identifiers (e.g., `diabetes_type_2`, `right_knee_oa`, `heart_failure_diastolic`).
- Only include items with `status: "active"` unless the task explicitly asks for inactive items in a specific section (e.g., excluded distractors).

### Enum Values

- Always use exactly the enum string values listed in the answer template's schema. Do not invent or paraphrase enum values.
- When a template specifies `allowed_values`, only emit values from that set.

### Dates

- Use `YYYY-MM-DD` format throughout.

### ID Stability

- Use IDs exactly as returned by the API. Do not generate synthetic IDs.
- For group/anomaly IDs in audits, derive stable IDs from the constituent elements (e.g., `DUP-GRP-{patient_id}`).

## Common Pitfalls

- **Do not include procedural notes or narrative text** in the JSON output — return only the normalized JSON object.
- **Read the template carefully**: some tasks have two parallel sections with similar names (e.g., `clinical_unions` vs `active_key_unions`, `merge` vs `merge_decision`). Fill both independently.
- **Cross-reference evidence**: when validating codes, always check both the ICD-10 directory and the patient's actual condition list.
- **Distinguish active from inactive**: many patient lists include both. Filter to `status: "active"` for clinical unions; use inactive items only in excluded-distractor sections.
- **Provider assignment**: for action plans and follow-up queues, assign owner providers based on the referral's performer provider or the batch's default specialist.
- **Handle null fields**: when a template field has type `["string", "null"]`, use `null` when the data is genuinely absent (e.g., no merge target decided yet).

## Output Format

Produce a single JSON object as the final answer. Do not wrap in markdown code fences. Do not include explanatory text before or after the JSON. Arrays marked as sets in the template should be sorted alphabetically unless the template states otherwise.
