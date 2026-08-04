 # EHR Quality-Governance API Skill

 ## Overview
 Use this skill when working with a read-only EHR quality-governance API to produce normalized JSON packets for duplicate-chart merges, referral coordination, care transitions, service-request quality review, and referral-batch audits. The API exposes patient demographics, clinical lists, encounters, documents, audit logs, provider directories, ICD-10 codes, service codes, duplicate candidates, and referral records.

 ## API Endpoints
 All endpoints are GET requests under a base URL provided as an environment variable (`TASK_ENV_BASE_URL` or equivalent).

 ### Patient Demographics
 - `GET /api/patients/{patient_id}` — patient record with demographics, insurance, PCP
 - `GET /api/patients?q=&family=&given=&dob=&insurance_id=` — search patients

 ### Clinical Lists (per patient)
 - `GET /api/patients/{patient_id}/conditions` — condition/problem list
 - `GET /api/patients/{patient_id}/medications` — medication list
 - `GET /api/patients/{patient_id}/allergies` — allergy list
 - `GET /api/patients/{patient_id}/encounters?status=&limit=` — encounter history
 - `GET /api/patients/{patient_id}/immunizations` — immunization records
 - `GET /api/patients/{patient_id}/documents` — document index
 - `GET /api/patients/{patient_id}/disclosures` — disclosure/consent records
 - `GET /api/patients/{patient_id}/service-requests` — service requests

 ### Governance & Lookups
 - `GET /api/duplicates/{candidate_id}` — duplicate candidate detail with match/conflict signals and merge_preview
 - `GET /api/duplicates/candidates` — list duplicate candidates
 - `GET /api/referrals/{referral_id}` — single referral detail
 - `GET /api/referrals?batch=&urgency=&patient=&status=` — search referrals
 - `GET /api/icd10/{code}` — ICD-10 chapter, expected terms, laterality requirement
 - `GET /api/service-codes/{code}` — service code validity, display name, service line
 - `GET /api/providers/{provider_id}` — provider detail
 - `GET /api/providers` — provider directory
 - `GET /api/audit-logs?patient_id=&event=&date_from=&date_to=` — audit trail

 ## Core Workflow

### 1. Gather All Relevant Data First
Before constructing any answer, fetch every endpoint referenced by the task prompt. For patient-centric tasks, pull the patient record plus all clinical list endpoints. For referral tasks, pull the referral, the patient, their clinical lists, the receiving provider, and the ICD-10 code. For duplicate tasks, pull the duplicate candidate and both patients' full records.

### 2. Read the Answer Template
Every task provides an `answer_template.json` (or equivalent schema) in `input/payloads/`. Study it thoroughly:
- Identify all required top-level keys
- Note enum constraints on every field
- Identify arrays marked as "set" (order-independent) vs "ordered"
- Note sort directives (alphabetical, newest-to-oldest, by code, etc.)

### 3. Normalize Clinical Keys
For conditions, medications, and allergies, use the `normalized_key` field from the API response. When computing unions or intersections across patients:
- Only include records with `status: "active"`
- Exclude `inactive`, `entered-in-error`, and other non-active statuses as distractors
- Sort normalized keys alphabetically when the template calls for set ordering

### 4. Reconcile Sources
When a task provides multiple data sources (e.g., duplicate merge_preview vs patient active-list endpoints), prefer the patient active-list endpoints as authoritative. Compute which keys the merge_preview missed and populate the reconciliation fields accordingly.

### 5. Match Signals from API Data
Extract match_signals and conflict_signals arrays directly from the duplicate candidate or referral API response. Map them into the template's allowed enum values. Do not invent signal names; use only the labels returned by the API that match the template's enum.

### 6. Document and Audit Evidence
- For merge packets, select identity-verification and external-continuity documents; exclude chart summaries and other generic EHR exports
- Include audit log IDs that reference identity review or external import events for the patients involved
- For referral packets, check `documents_received` against required document types (echocardiogram, office_note); list missing ones

### 7. Provider Selection
- Use the patient's `primary_care_provider` from the patient record for PCP contact
- For specialist contact, identify the provider referenced by external documents, the referral's `receiving_provider_id`, or the service request's `performer_id`
- Look up the provider in the provider directory for full contact details

### 8. Risk Flag Derivation (Care Transitions)
Map clinical findings to risk flags using the template's allowed_values:
- Active condition with memory loss → `cognitive_memory_loss`
- Encounter care plan mentioning "fall-risk" → `fall_risk_note_required`
- Active hypertension condition → `hypertension`
- Active insulin medication → `insulin_dependent_diabetes`
- Active latex allergy → `latex_allergy`
- Encounter care plan mentioning "glucose plan" → `perioperative_glucose_plan_needed`
Provide evidence linking each risk flag to condition_keys, medication_keys, and encounter_ids.

### 9. Referral Code Validation
- Look up each diagnosis code via `GET /api/icd10/{code}`
- Check the `chapter` field against the expected chapter for the service line (e.g., "Musculoskeletal" for orthopedics)
- Compare the referral's `diagnosis_narrative` against the ICD-10 `expected_terms`
- Flag laterality mismatches when the narrative describes one side but the code specifies the opposite
- Flag narrative mismatches when the narrative describes a different body part or condition entirely

### 10. Audit Construction
For batch audits:
- Count total rows, unique patients, urgency distribution
- Identify invalid/out-of-range codes (wrong chapter for the service line)
- Identify laterality and narrative mismatches by comparing each referral's diagnosis_code and diagnosis_narrative against ICD-10 data
- Detect duplicate groups: same patient_id appearing in multiple referrals
- Build follow-up queues: authorization_missing (status "missing"), records_request (office_note not in documents_received), imaging_follow_up (coordination_note contains "imaging pending")
- Assign tiers: Tier 1 for urgent/duplicate/coding-blocker issues, Tier 2 for auth/document/coding issues on routine referrals, Tier 3 for administrative document completion
- Ensure summary_counts are internally consistent with the arrays they summarize

## General Rules
- **Sort arrays alphabetically** unless the template explicitly specifies a different order (e.g., newest-to-oldest for encounters, by referral_id for audits)
- **Use stable IDs**: Always emit `patient_id`, `encounter_id`, `document_id`, `audit_id`, `referral_id`, `provider_id` as returned by the API
- **No narrative prose**: Answers must be pure JSON objects. Do not include explanations, SOP text, or procedural notes
- **Enum fidelity**: Only use values from the template's allowed enums. Do not invent new enum values
- **Null vs absent**: Use `null` (JSON null) when the template allows null and the data is unavailable. Do not omit required keys
- **Boolean fields**: Use JSON `true`/`false`, not strings
- **Date format**: Always use `YYYY-MM-DD` strings
- **Set semantics**: Arrays marked as sets in the template are order-independent (evaluators normalize them), but sort them alphabetically for consistency
