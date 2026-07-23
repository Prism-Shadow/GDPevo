# EHR Quality Governance Packet

Use a read-only EHR quality-governance REST API to build normalized JSON packets for clinical-quality workflows: duplicate-chart merge readiness, referral coordination, care transitions, duplicate review with service-request validation, and batch referral audits.

## Environment

The API lives at a base URL provided in the task prompt via the `<TASK_ENV_BASE_URL>` placeholder (or in an `environment_access.md` file if one is present). No authentication is required. The following read-only GET endpoints are available:

| Endpoint | Returns |
|---|---|
| `/api/patients` | List of patients; supports `?name=` and `?mrn=` query params |
| `/api/patients/{patient_id}` | Patient demographics (name, dob, sex, address, phone, insurance, primary_care_provider_id, duplicate_status, etc.) |
| `/api/patients/{patient_id}/conditions` | Active and inactive conditions with ICD-10 codes, descriptions, normalized_keys, status, onset dates |
| `/api/patients/{patient_id}/medications` | Active and inactive medications with names, doses, routes, frequencies, normalized_keys, status |
| `/api/patients/{patient_id}/allergies` | Active and inactive allergies with allergen, reaction, severity, normalized_keys, status |
| `/api/patients/{patient_id}/encounters` | Encounters with dates, types, providers, signed_status, diagnoses, care_plan_tags, medications mentioned |
| `/api/patients/{patient_id}/immunizations` | Immunization records with vaccine names, dates |
| `/api/patients/{patient_id}/documents` | Clinical documents with types, dates, statuses |
| `/api/patients/{patient_id}/service-requests` | ServiceRequest resources with status, intent, priority, codes, reason codes, performer/requester providers |
| `/api/patients/{patient_id}/disclosures` | Disclosure/consent records with status, purpose, recipient |
| `/api/audit-logs` | Audit log entries with action types, patient references, timestamps |
| `/api/duplicates/candidates` | List of duplicate-candidate records |
| `/api/duplicates/{candidate_id}` | Duplicate candidate detail with patient_ids, match_signals, conflict_signals, status |
| `/api/referrals` | Referral list with optional `?batch_id=` filter |
| `/api/referrals/{referral_id}` | Referral detail with diagnosis codes, narratives, authorization, urgency, documents |
| `/api/icd10` | ICD-10 code directory list |
| `/api/icd10/{code}` | ICD-10 code detail: description, chapter, laterality, valid flag |
| `/api/providers` | Provider directory list |
| `/api/providers/{provider_id}` | Provider detail: name, role, service_line, facility, phone, fax |
| `/api/service-codes` | Service code directory list |
| `/api/service-codes/{code}` | Service code detail: description, category, valid flag |

## General workflow

1. **Read the task prompt** for the task type, entity IDs (patient IDs, candidate IDs, referral IDs, batch IDs, provider IDs), and the path to the answer template.

2. **Read the answer template** (`input/payloads/answer_template.json` or equivalent) to understand the exact output shape, required keys, enum values, field types, array ordering rules, and set semantics. The template is your schema contract — every field in the template must appear in the output with the correct type and constraints.

3. **Query the API** to gather all relevant data. Map each template section to the endpoints that supply its data. Common mappings:
   - Patient info → `/api/patients/{id}`
   - Active clinical lists → `/api/patients/{id}/conditions` + `/medications` + `/allergies`
   - Encounters → `/api/patients/{id}/encounters`
   - Documents → `/api/patients/{id}/documents`
   - Duplicate candidates → `/api/duplicates/{id}`
   - Referrals → `/api/referrals/{id}` or `/api/referrals?batch_id=...`
   - ICD-10 validation → `/api/icd10/{code}`
   - Providers → `/api/providers/{id}`
   - Service codes → `/api/service-codes/{code}`
   - Audit logs → `/api/audit-logs` (filter by patient references)
   - Disclosures → `/api/patients/{id}/disclosures`
   - Immunizations → `/api/patients/{id}/immunizations`
   - Service requests → `/api/patients/{id}/service-requests`

   Run independent endpoint calls in parallel — patient lookups, code lookups, and directory queries don't depend on each other.

4. **Reconcile and normalize** the collected data against the template requirements. This is the core reasoning step — you must:
   - Filter to active records only (status=active) for clinical key unions unless the template specifies otherwise
   - Cross-reference between endpoints (e.g., verify a referral's diagnosis codes appear in the patient's active conditions; check that documents referenced by a referral actually exist on the patient)
   - Validate codes against the ICD-10 directory (valid, correct chapter, laterality/narrative match)
   - Identify match and conflict signals from demographic and clinical comparisons
   - Select and order evidence (documents, audit entries, encounters) by relevance and recency
   - Exclude distractors: inactive conditions/medications/allergies, unrelated documents, stale encounters, audit entries for other patients

5. **Apply ordering rules** from the template:
   - String arrays marked as sets: sort alphabetically (ascending) by the string value itself
   - Object arrays: sort by the key specified in the template (usually `referral_id`, `code`, `encounter_id`, or date)
   - Encounter/date-ordered arrays: newest-to-oldest means descending by date; oldest-to-newest means ascending
   - ID arrays: sort strings ascending (lexicographic)

6. **Output only the JSON object** — no markdown fences, no explanatory prose, no narrative text. The output must be a single valid JSON object that can be parsed directly.

## Task-type specific guidance

### Duplicate-chart merge readiness

When the task involves a duplicate candidate and two patient IDs:
- Fetch both patients' demographics, active clinical lists, documents, and audit logs
- Fetch the duplicate candidate detail for pre-computed match/conflict signals
- Determine canonical target (typically the patient NOT marked as a duplicate, or the one with the richer active clinical record, or the one the duplicate record points to) and source
- Compute clinical key unions: take the union of active condition/medication/allergy normalized_keys from both patients
- Reconcile by also checking each patient's own active-list endpoints against any duplicate candidate preview data
- Identity signals: collect match signals and conflict signals from the duplicate candidate plus any additional demographic comparisons you discover
- Evidence: include documents from both patients that are relevant to identity or external continuity of care; exclude chart summaries and unrelated documents
- Audit evidence: select audit log entries that reference either patient and relate to merge/duplicate actions
- Identify a specialist provider if one is associated with an external continuity-of-care document
- Set the primary care provider from whichever patient is the target

### Referral coordination packet

When the task involves a referral ID and a patient ID:
- Fetch the referral detail, patient demographics, active conditions/medications/allergies, encounters, documents, and relevant providers
- Build the active diagnosis list from the patient's active conditions, marking which are referral-relevant (match the referral's diagnosis narrative or reason codes)
- Validate the referral's primary diagnosis code against ICD-10: check validity, chapter, and whether the ICD-10 description matches the referral narrative
- Assess allergy readiness: collect all allergies, determine if documentation is complete or needs follow-up
- Select the most recent relevant encounter (look for one with a care_plan_tag matching the referral intent, or with matching diagnosis codes)
- Check for required documents: echocardiogram for cardiology referrals, office notes, authorizations; report which are missing
- Identify the receiving provider from the referral's performer or specialist designation
- Classify authorization status from the referral record
- Highlight medications relevant to the referral's clinical context (diuretics for heart failure, antihypertensives, etc.)
- Choose the normalized referral-letter field values that match the evidence

### Care transition packet

When the task involves a patient ID and a target provider:
- Fetch patient demographics, active clinical lists, encounters, immunizations, disclosures, and documents
- The recipient is the target provider mentioned in the prompt
- Active condition/medication/allergy keys: extract `normalized_key` values from active records only, sorted alphabetically
- Handoff encounters: select the most recent relevant encounters (typically 4) based on a clinical handoff window. Prefer care_transition, office_visit, and surgical consult types. Exclude encounters older than the handoff window or clearly unrelated. Sort newest to oldest.
- Document the selection basis (a normalized code describing the rule) and list both selected and excluded encounter IDs
- Latest immunization: the most recent by date from the patient's immunization records
- Disclosure: find a disclosure record matching the recipient provider and purpose (e.g., surgical handoff), checking it is in `permitted` status
- Risk flags: derive from active conditions, medications, and encounter evidence. Common risk categories:
  - Cardiac/BP flags from hypertension or cardiac conditions
  - Diabetes flags from diabetes conditions plus insulin medications
  - Allergy flags from active allergies (especially latex, which is perioperative-relevant)
  - Cognitive flags from memory loss or cognitive conditions
  - Fall risk flags from musculoskeletal conditions affecting mobility (hip/knee OA) plus pain medications
  - Perioperative planning flags from diabetes + insulin
- Risk flag evidence: for each flag emitted, cite the specific condition keys, medication keys, and encounter IDs that support it
- Readiness: `ready` if no blockers; `ready_with_risk_flags` if all data is present but risk flags exist; `not_ready` if required data (patient, recipient, active lists, encounters, immunization, disclosure) is missing

### Duplicate review with ServiceRequest validation

When the task involves a duplicate candidate, two patient IDs, and a ServiceRequest:
- Fetch the duplicate candidate detail, both patients, the ServiceRequest, and any relevant ICD-10/service-code lookups
- Duplicate review section: report the candidate's status and your decision (merge if confirmed duplicate with strong match, review_hold if conflicting signals, do_not_merge if not a duplicate)
- Match signals and conflict signals: use the candidate's pre-computed signals plus any additional observations from comparing the two patient records directly
- If the duplicate status is not confirmed, set merge target/source to null
- ServiceRequest section: report all fields from the ServiceRequest resource, validate the service_code against `/api/service-codes/{code}`, and validate each reason_code against ICD-10 (check validity, chapter, and whether the code matches the patient's active conditions or the duplicate/referral narrative)
- SBAR coverage: check if the referral/note narrative contains all four SBAR sections (situation, background, assessment, recommendation); report which are present and which are missing

### Batch referral audit

When the task involves a batch ID for referral auditing:
- Fetch all referrals in the batch via `/api/referrals?batch_id=...`
- For each referral, fetch the patient, the ICD-10 details for its diagnosis codes, and any related provider records
- **Invalid/out-of-range codes**: for each referral, look up the diagnosis code in ICD-10. If the code's chapter does not match the expected chapter for the service line (e.g., orthopedics → Musculoskeletal), flag it as `out_of_range_chapter`. If the code is not found in the ICD-10 directory, flag it as `unknown_code`.
- **Laterality/narrative mismatches**: compare the referral's diagnosis narrative text against the ICD-10 description for that code. Flag `laterality_mismatch` when the narrative mentions the opposite side from the code (e.g., narrative says "left knee" but the code is for right knee). Flag `narrative_mismatch` when the narrative describes a different condition entirely from what the code represents. Flag `missing_laterality` when the code has a laterality component but the narrative doesn't specify a side. Include the ICD-10 description terms as `expected_terms`.
- **Duplicate groups**: identify referrals with the same patient_id that appear to be resubmissions of the same clinical referral. Group them with a composite group ID, mark the duplicate type as `same_patient_resubmission`, and recommend consolidation under the original.
- **Insurance anomalies**: detect cases where different patients share the same insurance ID (possible membership issue), or where the same patient has separate clinical referrals (not duplicates but worth noting).
- **Follow-up queues**: categorize each referral that needs action — missing authorization, pending authorization, missing records (office notes), missing/pending imaging. Sort referral IDs ascending in each queue.
- **Action plan**: assign every referral that needs follow-up to a tier:
  - **Tier 1** (immediate): urgent coding issues (chapter mismatch + laterality/code mismatch) or duplicate blockers. Owner is a provider from the orthopedics service line.
  - **Tier 2** (short-term): routine coding/auth/document blockers. Owner is a provider from the orthopedics service line.
  - **Tier 3** (administrative): administrative document completion only. Owner is a provider from the orthopedics service line.
- **Summary counts**: compute all count fields from the assembled data.

## Distractors and exclusions

Every task type involves excluding irrelevant data. Common exclusion rules:
- **Conditions/medications/allergies**: only include active records in clinical unions; inactive, resolved, or entered-in-error records are distractors unless the template explicitly asks for them
- **Documents**: exclude chart summaries (internal documents not relevant to external coordination). Exclude documents belonging to unrelated patients or unrelated clinical contexts
- **Audit logs**: only include entries that directly reference the relevant patient(s) and relate to duplicate, merge, referral, or transition actions
- **Encounters**: exclude encounters older than the relevant clinical window, or with care_plan_tags unrelated to the current task
- **Duplicate candidate signals**: use the candidate's own match/conflict signals as your primary source; supplement but don't fabricate

## Output rules

- Return **only** the JSON object — no markdown code fences, no explanation before or after
- Every key in the answer template must appear in the output
- String values must match the template's enum constraints exactly
- Arrays marked as sets should be sorted alphabetically unless the template specifies a different order
- Use the same key names and nesting structure as the template
- Dates must be in YYYY-MM-DD format
- `null` is the valid value for optional fields that have no data (not omitted, not empty string)
- Boolean fields must be actual booleans, not strings
