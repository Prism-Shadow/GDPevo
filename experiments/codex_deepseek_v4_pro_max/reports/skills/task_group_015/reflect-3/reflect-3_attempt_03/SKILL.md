 # EHR Quality-Governance API Skill

 ## Overview
 Use this skill when working with a read-only EHR quality-governance REST API that exposes patient records, clinical lists, duplicate candidates, referrals, ICD-10 codes, providers, service codes, audit logs, and related healthcare data. The API returns normalized JSON. Tasks involve reconciling records across endpoints, validating clinical data, preparing structured packets (merge, referral, care-transition, audit), and producing normalized JSON outputs that conform to supplied answer templates.

 ## Core Workflow

 ### 1. Read the Prompt and Template First
 Before making any API call, read the task prompt and the answer template (`input/payloads/answer_template.json`). The template defines every required key, allowed enum values, array sort orders, and field types. Conform exactly to the template shape — do not add, omit, or rename keys.

 ### 2. Map Prompt Entities to Endpoints
 Identify every entity ID mentioned in the prompt (patient IDs, candidate IDs, referral IDs, provider IDs, batch IDs) and plan which endpoints to call. Common patterns:
 - **Duplicate merge packets**: GET the duplicate candidate, both patients, their conditions/medications/allergies/encounters/documents, audit logs for both patient IDs, and the provider directory.
 - **Referral coordination**: GET the referral, the patient, all clinical lists, encounters, documents, the ICD-10 code, and the receiving provider.
 - **Care transition**: GET the patient, recipient provider, clinical lists, encounters, immunizations, disclosures.
 - **Audit**: GET the referral batch, ICD-10 codes for every diagnosis code in the batch, patient records for every patient in the batch, and provider records.

 ### 3. Always Fetch the Authoritative Source
 Never rely on aggregate or preview data alone. When a duplicate candidate provides a `merge_preview` with clinical keys, always cross-check against the actual patient endpoints (`/api/patients/{id}/conditions`, etc.). The preview may be stale or incomplete. Reconcile by computing the union of active records from both patients' endpoints and identifying keys present in the endpoints but missing from the preview.

 ### 4. Normalize and Deduplicate Clinical Keys
 Clinical records use `normalized_key` fields. When building unions across patients:
 - Include only records with `"status": "active"`.
 - Deduplicate by `normalized_key` (the same key may appear from multiple sources for the same patient).
 - Sort alphabetically unless the template states otherwise.
 - Exclude inactive/stale records and list them in `excluded_distractors` sections if the template requires it.

 ### 5. Validate ICD-10 Codes Against the Directory
 For every diagnosis code, call `/api/icd10/{code}` to retrieve:
 - `chapter`: The ICD-10 chapter (e.g., "Musculoskeletal", "Circulatory", "Injury", "Respiratory").
 - `expected_terms`: Canonical descriptions for the code.
 - `requires_laterality`: Whether the code encodes a left/right distinction.

 Use this to:
 - Flag codes whose `chapter` does not match the expected service-line chapter (e.g., non-Musculoskeletal codes in an orthopedics batch are `out_of_range_chapter`).
 - Detect laterality mismatches: if the code implies right but the narrative says left (or vice versa).
 - Detect narrative mismatches: if the narrative text does not match any `expected_terms` for the code.
 - Detect missing laterality: if the code requires laterality but the narrative mentions neither side.

 ### 6. Analyze Duplicate Candidates Systematically
 For duplicate review:
 - Extract `match_signals` and `conflict_signals` from the duplicate candidate endpoint.
 - Cross-reference patient demographics (DOB, phone, address, insurance, name) to classify `demographic_matches` and `demographic_conflicts`.
 - Check clinical laterality: if one patient has right-knee conditions and the other has left-knee conditions, `opposite_laterality_problem` is a strong signal against merging.
 - The merge decision (`merge`, `review_hold`, `do_not_merge`) should weigh the number and clinical significance of conflict signals against match signals. An address abbreviation difference alone is typically minor; opposite clinical laterality is major.

 ### 7. Build Referral Packets with Clinical Context
 For referral coordination:
 - The `active_diagnoses` array should include all active conditions; mark each as `referral_relevant` based on whether the condition relates to the referral's service line and diagnosis.
 - The `referral_code_set.primary_code` is the referral's diagnosis code; `supporting_codes` are related active condition codes.
 - For `allergy_readiness`: if the referral's `coordination_note` mentions clarifying allergies, check whether sufficient allergy detail exists in the patient record. If details are present, the readiness may be `complete_documented` despite the note.
 - The `recent_encounter_evidence` should reference the encounter whose `care_plan_notes` explicitly mentions the referral reason.
 - Check `documents_received` against required documents (echocardiogram for cardiology, office_note, etc.).

 ### 8. Identify Risk Flags for Care Transitions
 When preparing a care-transition packet, scan active conditions, medications, allergies, and encounter notes for risk signals. Common flags include:
 - `insulin_dependent_diabetes`: active diabetes condition + insulin medication.
 - `latex_allergy`: active latex allergy.
 - `cognitive_memory_loss`: active memory-loss condition.
 - `fall_risk_note_required` / `perioperative_glucose_plan_needed`: mentioned in encounter `care_plan_notes`.
 - `hypertension`: active hypertension condition.
 Provide evidence by linking each risk flag to the condition keys, medication keys, and encounter IDs that support it.

 ### 9. Audit Batch Analysis
 When auditing a referral batch:
 - **Invalid/out-of-range codes**: Compare every diagnosis code's `chapter` to the expected chapter for the service line. For orthopedics, only "Musculoskeletal" chapter codes are in range; "Injury", "Respiratory", "Nervous system", etc. are out of range.
 - **Laterality/narrative mismatches**: For in-range codes, compare the code's laterality and expected terms against the narrative.
 - **Duplicate groups**: Group referrals for the same patient where one is marked as a resubmission (check `coordination_note` for "duplicate").
 - **Insurance anomalies**: Identify different patient IDs sharing the same `insurance_id`.
 - **Follow-up queues**: `authorization_missing` (auth status = "missing"), `records_request` (no office_note in documents), `imaging_follow_up` (coordination note mentions "imaging pending").
 - **Tier assignment**: Tier 1 = urgent with coding/duplicate issues. Tier 2 = routine with coding/auth issues. Tier 3 = administrative/doc completion only. Referrals with no issues are counted as `validated_ready_no_follow_up`.

 ### 10. Sort Arrays as Specified
 The answer template defines sort orders. Common rules:
 - Arrays of strings (IDs, keys): sort alphabetically/ascending.
 - Arrays of objects: sort by a designated field (`referral_id`, `code`, `risk_flag`, `group_id`, `anomaly_id`).
 - `handoff_encounters`: sort newest-to-oldest by date.
 - `selected_encounter_ids`: newest-to-oldest; `excluded_encounter_ids`: ascending.

 ### 11. Enum Values Are Closed Sets
 Every enum field has a finite set of allowed values listed in the template. Never invent new values. If the template lists `ready | ready_with_review_note | blocked`, those are the only valid choices. Match the exact casing and spelling.

 ### 12. General API Usage
 - Base URL is provided as `<TASK_ENV_BASE_URL>` in the prompt; substitute with the actual environment variable or URL.
 - All endpoints are GET only.
 - Replace path placeholders (`{patient_id}`, `{code}`, etc.) with actual IDs.
 - Supported query parameters: `q`, `family`, `given`, `dob`, `insurance_id` on patient search; `status` and `limit` on encounters; `patient_id`, `event`, `date_from`, `date_to` on audit logs; `batch`, `urgency`, `patient`, `status` on referrals.

 ## Common Pitfalls
 - **Trusting the duplicate preview**: The preview's clinical keys may be stale. Always validate against the patient endpoints.
 - **Missing distractor exclusion**: Inactive conditions, inactive medications, and unrelated documents/audit logs belong in `excluded_distractors`.
 - **Wrong chapter for Injury codes**: S83.* codes are "Injury" chapter, not "Musculoskeletal" — flag them as out of range for orthopedic audits.
 - **Missing laterality in narrative**: If a code requires laterality but the narrative is generic (e.g., "meniscus tear" without "left" or "right"), flag as `missing_laterality`.
 - **Overlooking coordination notes**: The referral's `coordination_note` field contains critical instructions (allergy confirmation needed, duplicate resubmission, imaging pending).
 - **Skipping insurance anomaly checks**: When the same insurance ID appears on different patient records, flag it — it may indicate a duplicate identity or data error.
 - **Including all active medications in referral highlights**: Only include medications with a clinical reason relevant to the referral (e.g., diuretics for heart failure, not statins).
