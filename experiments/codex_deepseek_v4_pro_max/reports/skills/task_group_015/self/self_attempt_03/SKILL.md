---
name: ehr-quality-governance
description: Reusable workflow for EHR quality-governance API tasks. Covers duplicate-chart merge readiness, referral coordination, care-transition packets, service-request quality review, and batch referral audits. Normalizes API evidence gathering, ICD-10 validation, identity-signal reconciliation, tiered action planning, and JSON-only output against supplied answer templates.
---

# EHR Quality-Governance Skill

Use this skill whenever the task involves an EHR (Electronic Health Record) quality-governance or referral-coordination workflow backed by a read-only REST API at `<TASK_ENV_BASE_URL>`. The skill encodes reusable operating rules distilled from common task families: duplicate-chart merge readiness, referral coordination packets, care-transition summaries, service-request quality reviews, and batch referral audits.

## Core Workflow

Every task follows the same high-level pipeline:

1. **Parse the prompt** (`prompt.txt`) to extract task-specific IDs (patient, referral, candidate, batch, provider, service-request) and the objective.
2. **Load the answer template** (`payloads/answer_template.json`) to understand the required output shape, field types, enum constraints, and ordering rules.
3. **Gather evidence** from the EHR API by issuing GET requests against every relevant endpoint.
4. **Validate and cross-reference** results: ICD-10 lookup, provider directory, active-list reconciliation, identity signals, duplicate detection, authorization/document readiness.
5. **Assemble the output** as a single normalized JSON object conforming exactly to the answer template. Output JSON only — no explanatory prose, no narrative commentary, no markdown wrapping.

## Environment & API

Base URL: `<TASK_ENV_BASE_URL>` (also available as `<GDPEVO_ENV_BASE_URL>`). No authentication required.

### Endpoint Catalog

| Family | Endpoints |
|--------|-----------|
| Patients | `GET /api/patients` (query: `q`, `family`, `given`, `dob`, `insurance_id`), `GET /api/patients/{patient_id}` |
| Clinical lists | `GET /api/patients/{patient_id}/conditions` (query: `status`), `GET /api/patients/{patient_id}/medications` (query: `status`), `GET /api/patients/{patient_id}/allergies` (query: `status`) |
| Encounters | `GET /api/patients/{patient_id}/encounters` (query: `status`, `limit`) |
| Documents | `GET /api/patients/{patient_id}/documents` |
| Immunizations | `GET /api/patients/{patient_id}/immunizations` |
| Disclosures | `GET /api/patients/{patient_id}/disclosures` |
| Service Requests | `GET /api/patients/{patient_id}/service-requests` |
| Duplicates | `GET /api/duplicates/candidates`, `GET /api/duplicates/{candidate_id}` |
| Audit Logs | `GET /api/audit-logs` (query: `patient_id`, `event`, `date_from`, `date_to`) |
| Referrals | `GET /api/referrals` (query: `batch`, `urgency`, `patient`, `status`), `GET /api/referrals/{referral_id}` |
| ICD-10 | `GET /api/icd10`, `GET /api/icd10/{code}` |
| Providers | `GET /api/providers`, `GET /api/providers/{provider_id}` |
| Service Codes | `GET /api/service-codes`, `GET /api/service-codes/{code}` |

Always replace path-placeholders (`{patient_id}`, `{referral_id}`, `{candidate_id}`, `{code}`, `{provider_id}`) with runtime IDs extracted from the prompt or returned by prior API calls.

## Evidence-Gathering Rules

### Active vs. Inactive Records

- Filter clinical lists (conditions, medications, allergies) to `status=active` when the template or prompt asks for "active" lists.
- Record inactive/stale entries in the appropriate `excluded_distractors` or exclusion fields when the template provides them.
- When a duplicate-candidate preview contains clinical-key lists, reconcile those against the patient-level active-list endpoints. The **patient active-list endpoints are the authoritative source**. Record any keys found only via the patient endpoints in the `active_list_reconciliation` section.

### Selecting Encounters for Handoff / Transition

- Choose the most recent encounters relevant to the target service line (e.g., orthopedics, cardiology). Exclude encounters that are stale, outside a reasonable window, or clinically unrelated.
- Sort handoff encounters from newest to oldest by encounter date.
- Record excluded encounter IDs with a brief exclusion reason in `source_selection` when the template supports it.

### Document Evidence

- Cross-reference required document types (echo, office note, authorization letter, imaging) against the patient's document list.
- Flag missing documents in `missing_required_documents` or equivalent fields.
- Distinguish document status: `final`, `preliminary`, `cancelled`, or `missing`.
- When the template has a `document_selection_policy`, limit packet documents to identity or external-continuity documents only. Exclude internal operational documents.

### Identity & Conflict Signals (Duplicate Review)

When evaluating a duplicate candidate, compare the two patient records for:

**Match signals**: same DOB, same insurance, similar address, same phone, same given name.

**Conflict signals**: different given name, different phone, opposite laterality problem, different DOB, different insurance, different address.

Emit match and conflict signals as sorted string arrays. Record demographic matches and conflicts separately when the template distinguishes them.

## ICD-10 Validation Rules

For any diagnosis code referenced in a referral, service request, or patient condition:

1. **Look up the code** via `GET /api/icd10/{code}`.
2. **Verify chapter alignment** with the target service line:
   - Orthopedics → expected chapter: Musculoskeletal (Chapter XIII, codes M00–M99)
   - Cardiology → expected chapter: Circulatory (Chapter IX, codes I00–I99)
   - Other service lines: verify against the chapter returned by the ICD-10 lookup.
3. **Flag mismatches**:
   - `out_of_range_chapter`: code exists but belongs to a chapter outside the expected service-line chapter.
   - `unknown_code`: code not found in the ICD-10 directory.
   - `valid_matches_narrative`: code is valid and its narrative matches patient evidence.
   - `valid_but_narrative_mismatch`: code is valid but its description conflicts with patient evidence.
   - `invalid_code`: code does not exist in the ICD-10 directory.
4. **Laterality checks**: when the diagnosis narrative or patient conditions indicate a specific side (left/right/bilateral), verify that the ICD-10 code is consistent. Flag `laterality_mismatch`, `narrative_mismatch`, or `missing_laterality` as appropriate.

## Referral Audit Patterns

When auditing a referral batch:

### Invalid or Out-of-Range Codes
- For each referral, look up the attached diagnosis code against ICD-10.
- If the chapter is not the expected chapter for the service line, classify as `out_of_range_chapter`.
- If the code does not exist, classify as `unknown_code`.

### Laterality & Narrative Mismatches
- Compare the ICD-10 description and its laterality against the referral's diagnosis narrative.
- Collect `expected_terms` from the ICD-10 directory entry.

### Duplicate Detection
- Scan the batch for multiple referrals for the same patient with the same diagnosis.
- Classify as `same_patient_resubmission`.
- Assign group IDs and recommend `consolidate_under_original`.

### Insurance & Patient Anomalies
- Detect patients sharing the same insurance ID (`shared_insurance_different_patients`): recommend `verify_insurance_membership_do_not_merge`.
- Detect same-patient referrals that are separate clinical reviews (`same_patient_separate_clinical_referrals`): recommend `separate_clinical_review_not_duplicate`.

### Follow-Up Queues
Build four queues of referral IDs:
- `authorization_missing`: referrals with no authorization record.
- `authorization_pending`: referrals with a pending authorization.
- `records_request`: referrals missing required office-note documents.
- `imaging_follow_up`: referrals missing or with pending imaging.

### Tiered Action Plan
| Tier | Label | Primary Reason | Owner |
|------|-------|----------------|-------|
| Tier 1 | Immediate | `urgent_coding_or_duplicate_blocker` | provider managing the referral |
| Tier 2 | Short-term | `routine_coding_auth_or_document_blocker` | provider managing the referral |
| Tier 3 | Administrative | `administrative_document_completion` | provider managing the referral |

## Readiness Assessment

For any packet (merge, referral, transition), assess:

- **ready**: all required data present, no blockers.
- **ready_with_review_note** / **ready_with_risk_flags**: data is complete but carries review notes or risk flags that should accompany the packet.
- **blocked** / **hold_for_*** / **not_ready**: one or more blockers prevent sending. Identify blocking issue codes (e.g., `authorization_missing`, `echo_missing`, `office_note_missing`, `allergy_incomplete`, `provider_missing`, `diagnosis_code_invalid`, `clinical_mismatch`, `missing_disclosure`, `disclosure_not_permitted`).

## Provider Resolution

- Look up providers via `GET /api/providers/{provider_id}`.
- Extract: `provider_id`, `name`, `role`, `service_line`, `facility`, `phone`, `fax`.
- For care-transition or referral packets, identify both the specialist/recipient provider and the primary care / requester provider as applicable.

## Output Normalization Rules

1. **Pure JSON only.** No markdown fences, no explanatory prose, no procedural notes. The answer must parse as a single JSON object.
2. **Dates**: `YYYY-MM-DD` format throughout.
3. **Sorting (defaults, unless the answer template says otherwise for a specific array)**:
   - Arrays marked as "sets": sort strings alphabetically ascending.
   - Arrays of referral objects: sort by `referral_id` ascending.
   - Arrays of IDs (patient, document, audit, immunization, disclosure): sort strings ascending.
   - Duplicate groups array: sort by `group_id` ascending; `referral_ids` inside each group sorted ascending.
   - Insurance/patient anomalies array: sort by `anomaly_id` ascending; IDs inside each anomaly sorted ascending.
   - Handoff encounter arrays: sort by date newest to oldest.
   - Risk flag arrays: sort ascending by risk-flag code string.
   - Risk flag evidence: sort ascending by `risk_flag`.
4. **Normalized keys**: use `normalized_key` values (not raw descriptions or codes) for condition, medication, and allergy references whenever the template asks for "keys."
5. **Empty arrays**: emit `[]`, not `null`, when no items exist.
6. **Null vs. missing**: use `null` only when the template explicitly types a field as `string or null`. Otherwise prefer empty arrays or omit the field as the template dictates.
7. **Task ID**: when the template specifies a `required_value` for `task_id`, use the exact value from the prompt/template.

## Task Family Quick Reference

| Task Family | Key Identifiers in Prompt | Signature Template Sections |
|-------------|---------------------------|----------------------------|
| Duplicate Merge Readiness | candidate ID, two patient IDs, `merge_packet_request.json` | `merge`, `merge_decision`, `clinical_unions`, `active_key_unions`, `active_list_reconciliation`, `identity_signals`, `evidence`, `excluded_distractors`, `packet_readiness`, `packet_contact` |
| Referral Coordination Packet | referral ID, patient ID, service line | `patient_referral`, `active_diagnoses`, `referral_code_set`, `allergy_readiness`, `recent_encounter_evidence`, `required_document_evidence`, `receiving_provider`, `authorization_readiness`, `medication_highlights`, `referral_letter_fields` |
| Care Transition Packet | patient ID, recipient provider ID, service line | `patient`, `recipient`, `active_condition_keys`, `active_medication_keys`, `active_allergy_keys`, `handoff_encounters`, `source_selection`, `latest_immunization`, `disclosure`, `risk_flags`, `risk_flag_evidence`, `packet_readiness` |
| Service Request Quality Review | duplicate candidate ID, two patient IDs, service request ID | `task_id`, `duplicate_review`, `service_request`, `sbar_coverage` |
| Batch Referral Audit | batch ID, service line | `batch`, `invalid_or_out_of_range_code_referrals`, `laterality_or_narrative_mismatch_referrals`, `duplicate_groups`, `duplicate_tiering_policy`, `insurance_patient_anomalies`, `follow_up_queues`, `action_plan`, `summary_counts` |

## Typical API Call Sequence

For most tasks, query in this order to build a complete evidence picture:

1. **Primary entity**: patient(s) by ID, referral by ID, duplicate candidate by ID, or batch referrals by batch ID.
2. **Clinical lists**: conditions, medications, allergies for each patient (filter `status=active` unless gathering distractors).
3. **Encounters**: for each patient, then filter to relevant service line and recency.
4. **Documents**: for each patient, then cross-reference against required document checklist.
5. **Diagnosis validation**: for every ICD-10 code encountered, look up against the ICD-10 directory.
6. **Providers**: for every provider ID referenced (requester, performer, recipient, specialist, PCP).
7. **Supporting**: immunizations, disclosures, service requests, audit logs, duplicate candidates as needed.
8. **Service codes**: for service-request quality tasks.

## Risk Flag Identification

When the task requires risk-flag classification, scan active clinical lists for evidence of:

| Risk Flag | Evidence Sources |
|-----------|-----------------|
| `cognitive_memory_loss` | conditions or encounter notes mentioning cognitive decline, memory loss, dementia |
| `fall_risk_note_required` | conditions or encounters indicating fall history, balance issues |
| `hypertension` | active condition with hypertension diagnosis |
| `insulin_dependent_diabetes` | active condition + medication evidence of insulin therapy |
| `latex_allergy` | active allergy record with latex allergen |
| `perioperative_glucose_plan_needed` | diabetes condition + upcoming surgery context |

For each emitted risk flag, populate `risk_flag_evidence` with the backing condition keys, medication keys, and encounter IDs.

## Exclusion & Distractor Handling

- **Inactive clinical records**: place inactive condition/medication/allergy keys into `excluded_distractors`.
- **Unrelated documents**: documents not relevant to the packet purpose (e.g., internal administrative forms, unrelated visit notes) go into `excluded_distractors.document_ids`.
- **Irrelevant audit entries**: audit logs unrelated to the merge/referral candidate go into `excluded_distractors.audit_ids`.
- **Stale encounters**: encounters outside the relevant clinical window or for unrelated service lines go into `source_selection.excluded_encounter_ids`.
