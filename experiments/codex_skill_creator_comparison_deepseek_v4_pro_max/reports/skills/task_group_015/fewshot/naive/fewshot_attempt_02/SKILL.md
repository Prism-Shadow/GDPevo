---
name: ehr-quality-governance
description: Workflows for EHR quality governance tasks — duplicate merge readiness, referral coordination, care transition packets, service request validation, and batch referral audits — using a read-only FHIR-aligned REST API.
---

# EHR Quality Governance Skill

## Environment

All tasks use a read-only EHR quality-governance REST API at the base URL
provided in the task prompt as `<TASK_ENV_BASE_URL>`. The API returns JSON.
No authentication is required.

### Endpoints

| Endpoint | Returns |
|---|---|
| `GET /health` | Record counts and environment status |
| `GET /api/patients` | List of all patients (array under `patients`) |
| `GET /api/patients/{id}` | Single patient detail |
| `GET /api/patients/{id}/conditions` | Active/inactive conditions array under `conditions` |
| `GET /api/patients/{id}/medications` | Active/inactive medications array under `medications` |
| `GET /api/patients/{id}/allergies` | Active/inactive allergies array under `allergies` |
| `GET /api/patients/{id}/encounters` | Encounters array under `encounters` |
| `GET /api/patients/{id}/immunizations` | Immunizations array under `immunizations` |
| `GET /api/patients/{id}/documents` | Documents array under `documents` |
| `GET /api/patients/{id}/service-requests` | ServiceRequests array under `service_requests` |
| `GET /api/patients/{id}/disclosures` | Disclosures array under `disclosures` |
| `GET /api/audit-logs` | Audit log entries array under `audit_logs` |
| `GET /api/duplicates/candidates` | All duplicate candidates |
| `GET /api/duplicates/{candidate_id}` | Single duplicate candidate detail |
| `GET /api/referrals` | All referrals (array under `referrals`) |
| `GET /api/referrals/{referral_id}` | Single referral detail |
| `GET /api/icd10` | All ICD-10 directory entries |
| `GET /api/icd10/{code}` | Single ICD-10 entry (chapter, expected_terms, requires_laterality) |
| `GET /api/providers` | All providers (array under `providers`) |
| `GET /api/service-codes` | All service codes (array under `service_codes`) |

## Task Workflows

### 1. Duplicate Merge Readiness Packet

**Goal:** Determine whether two patients flagged as a duplicate candidate should be
merged, produce the canonical target/source, union their clinical lists, and
assemble packet metadata.

**Workflow:**

1. Fetch the duplicate candidate from `GET /api/duplicates/{candidate_id}`.
   This gives `match_signals`, `conflict_signals`, `merge_preview`, `patient_ids`, and `status`.

2. Fetch both patients from `GET /api/patients/{id}`. Compare demographic fields:
   `dob`, `insurance_id`, `phone`, `sex`, `primary_care_provider_id`, `address`, `given_name`, `family_name`.

3. Fetch active conditions, medications, and allergies for each patient from their
   respective `GET /api/patients/{id}/conditions`, `/medications`, `/allergies`.

4. Fetch documents for each patient from `GET /api/patients/{id}/documents`.

5. Fetch audit logs from `GET /api/audit-logs`. Filter to entries matching the
   patient IDs and the merge event.

6. Fetch the provider directory from `GET /api/providers`.

**Merge decision rules:**
- If `merge_preview.preferred_target_patient_id` is set, use it as the canonical target.
  The other patient is the source.
- If the target's `canonical_status` is `active` and the source's `canonical_status`
  is `duplicate`, and the source's `canonical_patient_id` points to the target —
  that is a strong merge signal.
- Disposition `ready_to_merge` / `merge_ready` when signals align and no blocking
  conflicts exist. Use `needs_review` / `merge_ready_with_conflict_review` when
  conflicts exist but the weight of evidence still favors merge. Use
  `do_not_merge` / `needs_manual_review` when conflicts are severe.

**Clinical union rules:**
- Start with the `merge_preview` keys (condition, medication, allergy).
- Complement with entries from each patient's active endpoint lists that are
  **not** already in the merge preview. This forms the complete union.
- Only `status: "active"` records count. Inactive records are distractors.
- Include the `normalized_key` field from each active record.
- Sort alphabetically.

**Identity signals:**
- `match_signals` and `conflict_signals` come primarily from the duplicate
  candidate endpoint. Supplement with demographic comparison if the candidate
  fields are incomplete.
- `demographic_matches`: list field names where both patients have the same value.
- `demographic_conflicts`: list field names where values differ (treat near-matches
  like "Alder St" vs "Alder Street" as an address_abbreviation conflict, and
  "Samuel" vs "Sam" as a given_name_variant conflict).

**Evidence selection:**
- Include documents that support identity verification (type `identity_verification`)
  or external continuity of care (type `external_*_note`).
- Exclude `chart_summary` documents — they are chart-internal and not merge-packet
  evidence.
- Include audit log entries that reference the merge candidate patients and are
  about the merge or identity review event.
- Exclude unrelated audit logs (different patient IDs, unrelated merge events).

**Distractor exclusion:**
- Inactive conditions/medications from either patient.
- `chart_summary` documents.
- Audit log entries for unrelated patients or unrelated events.

**Contact determination:**
- The specialist provider is whoever is associated with external clinical
  documents on the source duplicate shell (e.g., the provider at the facility
  that sent an external cardiology note). Look at the document source field
  and cross-reference with the provider directory.
- The PCP is taken from the target patient's `primary_care_provider` block.

### 2. Referral Coordination Packet

**Goal:** Reconcile a referral record with the patient's active chart and build a
specialist coordination packet.

**Workflow:**

1. Fetch the referral from `GET /api/referrals/{referral_id}`.
2. Fetch the patient from `GET /api/patients/{patient_id}`.
3. Fetch active conditions, medications, allergies from patient endpoints.
4. Fetch encounters from `GET /api/patients/{patient_id}/encounters`.
5. Fetch documents from `GET /api/patients/{patient_id}/documents`.
6. Fetch the ICD-10 entry for the referral's `diagnosis_code`.
7. Fetch providers from `GET /api/providers`.

**Active diagnoses assembly:**
- Include every active condition (all sources: `problem_list`, `referral_intake`,
  `cardiology_import`, etc.).
- Add the referral's own intake condition if its `diagnosis_code` and
  `diagnosis_narrative` describe a symptom not already in the patient's problem
  list (e.g., a `referral_intake` condition for dyspnea).
- Mark `referral_relevant: true` when the condition's code chapter matches the
  referral's `service_line` (cardiology → Circulatory chapter) or the condition
  appears in the referral's own narrative.
- Sort by `code` ascending.

**Referral code set:**
- `primary_code` is the referral's `diagnosis_code`.
- `supporting_codes` are additional codes from active diagnoses that are
  referral-relevant (excluding the primary code itself).
- Validate via ICD-10 lookup: confirm the code exists, note its `chapter`, and
  compare its `expected_terms` against the referral's `diagnosis_narrative`.
- `icd_validation`: `valid_matches_narrative` when code valid and narrative
  aligns with expected_terms. `valid_but_narrative_mismatch` when code valid
  but narrative doesn't match. `invalid_code` when code not in ICD-10 directory.
  `wrong_service_chapter` when chapter doesn't match the service line's expected
  chapter.
- `narrative_match`: true if the referral narrative contains or aligns with
  the ICD-10 expected_terms.

**Allergy readiness:**
- Collect all active allergies from the patient endpoint. Also check the
  referral form itself — if the referral mentions allergies, include them.
- `readiness_status`: `complete_documented` when allergies are present and
  sourced. `incomplete_needs_clarification` when the referral coordination_note
  suggests allergy follow-up. `no_known_allergies` when zero active allergies.
- `ready_for_letter`: false when clarification is needed.

**Recent encounter evidence:**
- Find the most recent encounter whose `care_plan_notes` or diagnosis codes
  match the referral's purpose (e.g., "cardiology referral" mentions).
- The encounter's `diagnoses` should overlap with the referral's clinical
  context.
- If multiple candidates, take the most recent by date.
- Extract medications mentioned in that encounter's `medications_mentioned`.

**Required document evidence:**
- Check the referral's `documents_received` list.
- Check patient documents for matching types (echocardiogram, office_note, etc.).
- For cardiology referrals, check for an echocardiogram. For orthopedics,
  check for MRI/X-ray.
- `missing_required_documents`: list required doc types not present.

**Receiving provider:**
- From `GET /api/providers/{referral.receiving_provider_id}`.

**Authorization readiness:**
- Pull `authorization_status`, `status`, `urgency` from the referral.
- `overall_readiness`: `ready_to_send` when authorization is approved, required
  documents are present, and no clinical mismatches block sending.
  `hold_for_authorization` when authorization is missing/pending.
  `hold_for_missing_documents` when required docs are absent.
  `hold_for_clinical_clarification` when allergy or code issues exist.
- `blocking_issues`: enumerate specific blockers (see template enum values).

**Medication highlights:**
- Select active medications where the medication name or class is clinically
  relevant to the referral service line:
  - Cardiology: diuretics (furosemide), ACE inhibitors (lisinopril), beta blockers,
    statins.
  - Orthopedics: pain management (acetaminophen, NSAIDs), anticoagulants.
  - Diabetes: insulin, metformin.
  - Hypertension: ACE inhibitors, ARBs, calcium channel blockers.
- Assign `highlight_reason` based on the medication's clinical role.
- Sort referral-relevant meds first.

**Referral letter fields:**
- Choose the enum value that best describes each reconciled finding.
- `diagnosis_summary_choice`: derived from the primary diagnosis narrative.
- `allergy_statement_choice`: derived from allergy_readiness.
- `recent_encounter_choice`: derived from the selected encounter.
- `document_packet_choice`: derived from required_document_evidence.
- `medication_summary_choice`: derived from medication_highlights.
- `recipient_choice`: derived from receiving_provider.
- `authorization_statement_choice`: derived from authorization_readiness.
- `readiness_choice`: derived from overall_readiness.

### 3. Care Transition Packet

**Goal:** Assemble a surgical handoff or care transition packet for a specific
patient and receiving provider.

**Workflow:**

1. Fetch patient from `GET /api/patients/{patient_id}`.
2. Fetch the receiving provider from `GET /api/providers/{provider_id}`.
3. Fetch active conditions, medications, allergies.
4. Fetch encounters from `GET /api/patients/{patient_id}/encounters`.
5. Fetch immunizations from `GET /api/patients/{patient_id}/immunizations`.
6. Fetch disclosures from `GET /api/patients/{patient_id}/disclosures`.

**Active clinical keys:**
- Collect all `normalized_key` values from active conditions, medications, and
  allergies. Sort alphabetically.

**Handoff encounter selection:**
- Filter encounters to the relevant surgical handoff window — typically the
  most recent 90 days, prioritizing those with diagnoses matching the transition's
  clinical focus (e.g., orthopedic codes for orthopedic transition).
- Select the 4 most relevant recent encounters by date (newest first).
- Exclude encounters that are clearly stale (too old, e.g. > 120 days), or have
  diagnoses completely unrelated to the service line.
- `selection_basis`: label describing the selection rule (e.g.,
  "orthopedic_surgical_handoff_window").
- `excluded_encounter_ids`: list IDs that were reviewed but excluded, with reason.

**Latest immunization:**
- Pick the immunization with the most recent `date`.

**Disclosure:**
- Find the disclosure where `recipient_provider_id` matches the receiving provider
  and `purpose` aligns with the transition type (e.g., "surgical handoff").

**Risk flags:**
- Derive from the active clinical picture:
  - `hypertension`: active condition with normalized_key `hypertension`.
  - `insulin_dependent_diabetes`: active condition `diabetes_type_2` + active
    medication containing insulin.
  - `latex_allergy`: active allergy with allergen latex.
  - `cognitive_memory_loss`: active condition with normalized_key `memory_loss`.
  - `fall_risk_note_required`: bilateral or lower-extremity orthopedic conditions
    (hip OA, knee OA) + pain medication.
  - `perioperative_glucose_plan_needed`: diabetes + insulin + surgical context.
- Sort risk flag codes alphabetically.

**Risk flag evidence:**
- For each emitted risk flag, list the supporting `condition_keys`,
  `medication_keys`, and `encounter_ids` that justify it.
- Encounter evidence can come from encounters mentioning relevant diagnoses or
  care plan notes referencing the risk.

**Packet readiness:**
- `ready_to_send: true` when all required sections have data.
- `status`: `ready` when no risk flags; `ready_with_risk_flags` when risk flags
  exist but no hard blockers; `not_ready` when required sections are missing.

### 4. Duplicate Review + ServiceRequest Quality Check

**Goal:** Validate a duplicate candidate review outcome and the quality signals
of an associated ServiceRequest.

**Workflow:**

1. Fetch the duplicate candidate from `GET /api/duplicates/{candidate_id}`.
2. Fetch both patients from `GET /api/patients/{id}`.
3. Fetch the ServiceRequest from `GET /api/patients/{patient_id}/service-requests`
   and locate the one matching the given service request ID.
4. Fetch ICD-10 entries for each reason code in the ServiceRequest.
5. Fetch the service code directory from `GET /api/service-codes`.
6. Fetch providers from `GET /api/providers`.

**Duplicate review rules:**
- `candidate_status`: from the duplicate candidate's `status` field.
- `decision`: `merge` when status is `open` with strong match signals and a
  preferred target. `review_hold` when status is `needs_review` or conflicts
  are significant. `do_not_merge` when conflicts clearly outweigh matches.
- `merge_target_patient_id` / `merge_source_patient_id`: null when not merging.
- `match_signals`: from the candidate, limited to the enum values in the template.
- `conflict_signals`: from the candidate, limited to the enum values.
- `opposite_laterality_problem` is a conflict signal when the two patients have
  conditions with opposite laterality (e.g., one has left knee OA, the other
  has right knee conditions only).

**ServiceRequest validation rules:**
- Check `service_code` against `GET /api/service-codes`: the code must exist
  and be `active: true`.
- Check `performer_id` against `GET /api/providers`: verify the performer's
  `service_line` matches the service code's `service_line`.
- For each `reason_code`:
  - Look up the ICD-10 entry.
  - `valid: true` when the code exists in the ICD-10 directory.
  - `chapter`: from the ICD-10 entry.
  - `matches_patient_evidence`: true when the patient's active conditions include
    that code or a condition with matching normalized_key context.

**SBAR coverage:**
- Check that the ServiceRequest's `sbar` object has all four sections:
  `situation`, `background`, `assessment`, `recommendation`.
- `complete: true` when all four are present and non-empty.
- `sections_present`: list the ones present.
- `missing_sections`: list the ones absent or empty.

### 5. Batch Referral Audit

**Goal:** Audit a batch of referrals for a specific service line and date,
identifying code validity issues, narrative/laterality mismatches, duplicates,
anomalies, and building a tiered action plan.

**Workflow:**

1. Fetch all referrals from `GET /api/referrals`.
2. Filter to the target `batch_id`.
3. For every referral in the batch, fetch its ICD-10 code from
   `GET /api/icd10/{code}`.
4. (Optional) Fetch patient details for duplicate/anomaly checking.

**Invalid or out-of-range code detection:**
- For an orthopedic batch, the expected ICD-10 chapter is **Musculoskeletal** (M codes).
- Any referral whose ICD-10 chapter is NOT "Musculoskeletal" is out-of-range.
  Common culprits: `S83.xxx` codes (Injury chapter), `J44.9` (Respiratory),
  `C34.91` (Neoplasms).
- `issue_type`: `out_of_range_chapter` for wrong-chapter codes. Use `unknown_code`
  only if the code is absent from the ICD-10 directory entirely.
- Sort this list by `referral_id` ascending.

**Laterality or narrative mismatch detection:**
- Compare the ICD-10 entry's `expected_terms` against the referral's
  `diagnosis_narrative`.
- `laterality_mismatch`: when the ICD-10 code implies one side (e.g., M17.11 =
  right knee, M17.12 = left knee, M25.561 = right knee pain, M25.562 = left knee
  pain, M16.11 = right hip) but the narrative describes the opposite side.
- `narrative_mismatch`: when the narrative describes a body part or condition
  fundamentally different from the ICD-10 expected_terms (e.g., code for knee
  but narrative says "lumbar radiculopathy" or "hip arthritis").
- `missing_laterality`: when the ICD-10 code has `requires_laterality: true` but
  the narrative doesn't specify a side.
- `expected_terms`: list the ICD-10 expected_terms that would correctly describe
  the code.
- Sort this list by `referral_id` ascending.

**Laterality quick reference for common orthopedic codes:**
| Code | Laterality | Expected narrative |
|---|---|---|
| M17.11 | Right | right knee OA / right knee |
| M17.12 | Left | left knee OA / left knee |
| M16.11 | Right | right hip OA / right hip |
| M16.12 | Left | left hip OA / left hip |
| M25.561 | Right | right knee pain |
| M25.562 | Left | left knee pain |
| S83.241A | Right | right medial meniscus tear |
| S83.242A | Left | left medial meniscus tear |

**Duplicate group detection:**
- Group referrals by `patient_id`. Any patient with more than one referral in
  the same batch forms a duplicate group.
- `duplicate_type`: `same_patient_resubmission`.
- `recommended_disposition`: `consolidate_under_original` — keep the first
  referral and flag the later ones as duplicates.
- `group_id`: a stable identifier like `DUP-REF-{BATCH}-P{patient_id}`.

**Duplicate tiering policy:**
- All referral IDs in a duplicate group go to the Tier 1 duplicate-blocker list.

**Insurance patient anomalies:**
- Group referrals by `insurance_id` (fetched from patient records). When the same
  insurance ID appears across different patients, flag as an anomaly.
- `anomaly_type`: `shared_insurance_different_patients`.
- `recommended_disposition`: `verify_insurance_membership_do_not_merge`.

**Follow-up queues:**
- `authorization_missing`: referrals with `authorization_status: "missing"`.
- `authorization_pending`: referrals with `authorization_status: "pending"`.
- `records_request`: referrals missing `office_note` from `documents_received`.
- `imaging_follow_up`: referrals missing both `mri` and `xray` from
  `documents_received` (OR missing one of the two that is commonly needed).
  **Rule:** A referral needs imaging follow-up if it lacks MRI or lacks X-ray
  (i.e., if `documents_received` does not include at least one key imaging type
  relevant to orthopedics). Check: if neither `mri` nor `xray` is in
  `documents_received`, or if only one is present but the clinical context
  suggests both are needed.

**Action plan tiering:**
- **Tier 1 (Immediate):** Referrals with:
  - Duplicate-blocker status (part of a duplicate group).
  - Any referral that is both out-of-range AND has a mismatch AND is missing
    authorization — assign the ortho provider for that batch.
  - `primary_reason`: `urgent_coding_or_duplicate_blocker`.
  - Owner from the batch's orthopedic providers (PRV-ORTHO-010, PRV-ORTHO-011).
- **Tier 2 (Short-term):** Referrals with:
  - Out-of-range chapter, narrative/laterality mismatch, missing authorization,
    missing records, or missing imaging — that are NOT in Tier 1.
  - `primary_reason`: `routine_coding_auth_or_document_blocker`.
  - Distribute across both orthopedic providers.
- **Tier 3 (Administrative):** Referrals with:
  - Only document completion issues (missing office_note or imaging) but valid
    codes and no mismatches.
  - `primary_reason`: `administrative_document_completion`.

**Summary counts:**
- Count totals exactly: number of referral rows in the batch, unique patients,
  counts of each issue type, counts per tier.
- `validated_ready_no_follow_up_count`: count referrals with no issues at all
  (valid code in correct chapter, no mismatch, authorization approved, all
  documents received, no duplicate, no anomaly).

## General Business Rules

### Active vs Inactive
- Only records with `status: "active"` count as active clinical data for union
  lists, risk flags, and referral coordination.
- Inactive records (status `inactive`, `resolved`, `entered-in-error`) are
  distractors to be excluded.

### Distractor Identification
Every task includes distractors — records that are present in the API but should
not appear in the output. Common distractors:
- Inactive conditions/medications from either patient.
- `chart_summary` documents (internal chart exports, not clinical evidence).
- Audit log entries for unrelated patients or unrelated events.
- Encounters outside the relevant time window or with diagnosis codes unrelated
  to the service line.
- Immunizations that are not the latest.
- Providers not relevant to the task.

### Sorting Conventions
- ID arrays (document_ids, audit_ids, encounter_ids, referral_ids): sort
  alphabetically/lexicographically ascending.
- Clinical key arrays (condition_keys, medication_keys, allergy_keys): sort
  alphabetically by the normalized_key string.
- Referral object arrays: sort by `referral_id` ascending.
- Encounter arrays: sort by `date` descending (newest first), unless the
  template specifies otherwise.
- Risk flag arrays: sort alphabetically by flag code.

### Enum Value Discipline
Each answer template defines allowed enum values. Match them exactly —
do not invent new codes or paraphrases. Copy-paste the exact enum string from
the template where applicable.

### Null vs Omitted
- Use `null` (JSON null) for fields that are explicitly nullable in the template.
- Use empty arrays `[]` for array fields that have no items.
- Do not include extra keys not defined in the answer template.

### Provider Directory
The environment has 9 providers across 7 service lines. Common providers:

| ID | Name | Service Line |
|---|---|---|
| PRV-PCP-001 | Dr. Alina Chow | primary_care |
| PRV-PCP-002 | Dr. Marcus Hale | primary_care |
| PRV-ORTHO-010 | Dr. Priya Nair | orthopedics |
| PRV-ORTHO-011 | Dr. Victor Huang | orthopedics |
| PRV-CARD-020 | Dr. Renee Okafor | cardiology |
| PRV-PULM-030 | Dr. Leo Navarro | pulmonology |
| PRV-NEURO-040 | Dr. Hannah Stern | neurology |
| PRV-SNF-050 | Kelsey Morgan, RN | skilled_nursing |
| PRV-ONC-060 | Dr. Isabel Becker | oncology |

### ICD-10 Chapter Reference

| Code Prefix | Chapter |
|---|---|
| C | Neoplasms |
| E | Endocrine |
| G | Nervous System |
| I | Circulatory |
| J | Respiratory |
| M | Musculoskeletal |
| R | Symptoms/Signs |
| S | Injury |
| Z | Factors influencing health status |

Service-line chapter expectations:
- **Cardiology** → Circulatory (I codes)
- **Orthopedics** → Musculoskeletal (M codes)
- **Pulmonology** → Respiratory (J codes)
- **Neurology** → Nervous System (G codes)
- **Oncology** → Neoplasms (C codes)

### Normalized Key Patterns
Normalized keys are lower_snake_case identifiers. Common ones:

| Condition | normalzied_key |
|---|---|
| Type 2 diabetes | `diabetes_type_2` |
| Hypertension | `hypertension` |
| Right knee OA | `right_knee_oa` |
| Left knee OA | `left_knee_oa` |
| Right hip OA | `right_hip_oa` |
| COPD | `copd` |
| Coronary artery disease | `coronary_artery_disease` |
| Heart failure (diastolic) | `heart_failure_diastolic` |
| Shortness of breath | `dyspnea` |
| Memory loss | `memory_loss` |

For medications: the key is typically the generic drug name (`aspirin`,
`metformin`, `furosemide`, `lisinopril`, `acetaminophen`, `insulin_glargine`)
or `baseline_med` for nonspecific maintenance medications.

For allergies: the key is typically the allergen name (`penicillin`,
`iodinated_contrast`, `latex`, `sulfa_antibiotics`) or `baseline_allergy`.

### Duplicate Merge Preview Reconciliation
The duplicate candidate's `merge_preview` contains a subset of clinical keys.
The patient active-list endpoints may contain additional active keys not captured
in the preview. Always use the patient endpoints as the authoritative source
and add any missing keys to the union. The reconciliation list documents only
the keys that were added from the endpoints beyond what the preview already had.

### Service Line to Document Mapping
| Service Line | Key Document Types |
|---|---|
| Cardiology | echocardiogram, office_note, stress_test |
| Orthopedics | mri, xray, office_note, physical_therapy_note |
| General | insurance_card, office_note |

### Encounter Selection Heuristic
When selecting encounters for a packet:
1. Filter to encounters within a clinically relevant window (typically 90–120 days).
2. Prioritize encounters whose `diagnoses` contain codes matching the packet's
   service line chapter.
3. Prefer signed encounters over unsigned/amended.
4. Look for `care_plan_notes` that mention the packet's purpose (referral,
   surgery, handoff, transition).
5. If the task specifies a fixed count (e.g., 4), take the top N by date.

### Authorization Status Mapping
| API Value | Meaning |
|---|---|
| `approved` | Authorization granted, no blocker |
| `pending` | Awaiting decision, follow up |
| `missing` | Never submitted, needs action |
| `denied` | Rejected, needs appeal or alternative |
| `not_required` | No auth needed for this referral type |

## Task Execution Checklist

1. **Read the prompt** — identify the task type, the IDs involved, and the
   answer template path.
2. **Read the answer template** — note every required key, enum constraint,
   array ordering rule, and nullability hint.
3. **Fetch data** — call every relevant API endpoint. Do not skip endpoints
   that could contain evidence. Always fetch patient sub-resources even if the
   duplicate preview seems complete.
4. **Identify distractors** — scan all fetched records and mentally tag
   inactive, unrelated, or stale entries.
5. **Apply business rules** — use the rules in this skill for reconciliation,
   matching, and validation.
6. **Build output** — start from the template structure, fill in every field,
   enforce sorting, use exact enum values.
7. **Self-check** — verify no distractors leaked in, all arrays are sorted
   correctly, all required keys are present, and enum values match the template.
