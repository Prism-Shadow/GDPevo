# EHR Domain Patterns

Reusable rules, conventions, and mappings for EHR quality-governance tasks. Load when the task involves clinical key normalization, ICD-10 validation, duplicate detection, risk flag derivation, or document/encounter selection policies.

## Normalized Key Derivation

Every condition, medication, and allergy record has a `normalized_key` field. When a record lacks this field, derive it:

1. Take the item's `code` or `description` field.
2. Lowercase it.
3. Replace spaces and hyphens with underscores.
4. Strip punctuation (periods, parentheses).
5. Collapse consecutive underscores.

### Known Condition Keys

| ICD-10 | Key |
|---|---|
| I10 | `hypertension` |
| I50.32 | `heart_failure_diastolic` |
| E11.9 | `diabetes_type_2` |
| J44.9 | `copd` |
| M17.11 | `right_knee_oa` |
| M17.12 | `left_knee_oa` |
| M16.11 | `right_hip_oa` |
| M25.561 | `right_knee_pain` |
| M25.562 | `left_knee_pain` |
| R06.02 | `dyspnea` |
| I25.10 | `coronary_artery_disease` |
| R41.3 | `memory_loss` or `amnestic_disorder` |

### Known Medication Keys

| Medication | Key |
|---|---|
| aspirin | `aspirin` |
| metformin | `metformin` |
| furosemide | `furosemide` |
| lisinopril | `lisinopril` |
| acetaminophen | `acetaminophen` |
| insulin glargine | `insulin_glargine` |
| naproxen | `naproxen` |
| atorvastatin | `atorvastatin` |

### Known Allergy Keys

| Allergen | Key |
|---|---|
| penicillin | `penicillin` |
| iodinated contrast | `iodinated_contrast` |
| latex | `latex` |
| sulfa antibiotics | `sulfa_antibiotics` |

### Distinguishing Active from Inactive

Only records with `status` = `active` (or `clinical_status` = `active`) belong in active-key unions. Records with `status` = `inactive`, `resolved`, `completed`, or `entered-in-error` are excluded from clinical unions and included only in excluded-distractor arrays when the template requires them.

## Clinical Union Computation

For merge tasks that require clinical-key unions across two patients:

1. Collect all active condition/medication/allergy keys from **both** patients.
2. Take the union (deduplicate).
3. Sort alphabetically.

For active-list reconciliation:
- Keys present in patient active-list endpoints but **not** in the duplicate preview go into `*_keys_added_from_active_endpoints`.
- The authoritative source is always `patient_active_list_endpoints_over_duplicate_preview`.

## ICD-10 Validation

### Service Line to Expected Chapter

| Service Line | Expected ICD-10 Chapter(s) |
|---|---|
| orthopedics | Musculoskeletal |
| cardiology | Circulatory |
| pulmonology | Respiratory |
| neurology | Nervous System |
| oncology | Neoplasms |
| skilled_nursing | Factors Influencing Health Status |

### Validation Steps

1. **Existence check**: `GET /api/icd10/{code}` — 404 means invalid/unknown.
2. **Chapter check**: The returned `chapter` must match the expected chapter for the service line.
3. **Narrative match**: The `description` from ICD-10 should conceptually align with the referral's `diagnosis_narrative` and patient evidence (active conditions).
4. **Laterality check**: Compare code laterality against the narrative for orthopedics codes.

### Laterality Codes

| Code | Laterality | ICD-10 Description (typical) |
|---|---|---|
| M17.11 | Right knee | Unilateral primary osteoarthritis, right knee |
| M17.12 | Left knee | Unilateral primary osteoarthritis, left knee |
| M16.11 | Right hip | Unilateral primary osteoarthritis, right hip |
| M16.12 | Left hip | Unilateral primary osteoarthritis, left hip |
| M25.561 | Right knee | Pain in right knee |
| M25.562 | Left knee | Pain in left knee |
| S83.241A | Right knee | Tear of medial meniscus, current injury, right knee |
| S83.242A | Left knee | Tear of medial meniscus, current injury, left knee |

### Narrative Extraction for Mismatch Detection

- If the referral narrative mentions "right" but the code specifies left (or vice versa), flag `laterality_mismatch`.
- If the referral narrative does not specify laterality at all but the code does, flag `missing_laterality`.
- If the referral narrative describes a completely different condition than the code (e.g., "lumbar radiculopathy" for a knee code), flag `narrative_mismatch`.
- Generate `expected_terms` from the ICD-10 `description`, splitting on commas; include the last segment as a separate term when it represents a key concept.

### Issue Types for Batch Audits

| Issue Type | Condition |
|---|---|
| `out_of_range_chapter` | ICD-10 code chapter does not match the expected chapter for the service line |
| `unknown_code` | ICD-10 code returns 404 |

### Reason Code Validation (ServiceRequest tasks)

For each reason code on a ServiceRequest:
- `valid`: boolean, true if the ICD-10 code lookup succeeds (not 404)
- `chapter`: the ICD-10 chapter string
- `matches_patient_evidence`: boolean, true if the code description appears among the patient's active conditions

## Identity Signals and Duplicate Detection

### Match Signals

| Signal | Detection Rule |
|---|---|
| `same_dob` | Both patients share identical DOB |
| `same_insurance` | Both patients share identical `insurance_id` |
| `same_phone` | Both patients share identical phone number |
| `similar_address` | Addresses are substantially similar (same street, city) but may differ in minor formatting |
| `same_given_name` | Given name is identical or clearly the same person |
| `name_variant` | Names are recognizably the same person (e.g., Thomas/Tom) but not identical |
| `shared_external_cardiology_document` | An external document (e.g., cardiology) references one patient but appears in the other's document list |
| `shared_external_orthopedic_document` | Same pattern for orthopedics |

### Conflict Signals

| Signal | Detection Rule |
|---|---|
| `different_given_name` | Given names are clearly different people |
| `different_phone` | Phone numbers differ |
| `different_dob` | DOB differs |
| `different_insurance` | Insurance IDs differ |
| `different_address` | Addresses are in different locations |
| `opposite_laterality_problem` | One patient has right-side condition, the other left-side (e.g., right knee OA vs left knee OA) |
| `address_abbreviation` | Same address but abbreviated differently (minor conflict, not a blocker alone) |
| `given_name_variant` | Same person but name spelled differently (minor conflict, not a blocker alone) |

### Demographic Fields Compared

| Field | Match Type |
|---|---|
| `dob` | Exact match or not |
| `insurance_id` | Exact match or not |
| `phone` | Exact match or not |
| `address` | Similarity comparison (semantic, not just string equality) |
| `sex` | Exact match or not |
| `primary_care_provider_id` | Exact match or not |
| `given_name` | Name comparison (normalize, compare given vs family) |

### Merge Disposition Logic

| Disposition | Condition |
|---|---|
| `ready_to_merge` | Strong identity match (multiple matching signals), duplicate already designated with target/source, target is canonical/active |
| `needs_review` | Conflicting signals present; merge cannot proceed automatically |
| `do_not_merge` | Strong evidence the patients are different individuals |

### Merge Decision Reason Codes

| Code | Meaning |
|---|---|
| `active_duplicate_candidate` | The duplicate candidate exists and is active |
| `duplicate_record_already_points_to_target` | The duplicate already has a designated merge target |
| `strong_identity_match` | Demographic and identity signals strongly indicate same patient |

### Duplicate Status Mapping

| candidate_status | decision |
|---|---|
| `confirmed_duplicate` | `merge` |
| `needs_review` | `review_hold` |
| `not_duplicate` | `do_not_merge` |

## Document Selection Policy

### Evidence Documents

Only documents of type `external_record` or documents that establish patient identity or external clinical continuity belong in the evidence document array. Exclude:
- `chart_summary` (always excluded)
- Internal-only documents that do not relate to the specific quality-governance task

### Excluded Document Types

The `excluded_document_types` array always includes `chart_summary`. Other exclusions depend on the task but never remove a document needed for the identity match.

### Packet Document Basis

Always `identity_or_external_continuity_documents_only`.

## Audit Log Selection

For merge packets, select audit log entries whose `action` or `details` reference the duplicate candidate or merge operation. Do not include unrelated audit entries.

## Encounter Selection

### Care Transition Handoff

- Select the 4 most recent signed encounters of types relevant to the surgical handoff: `care_transition`, `office_visit`.
- Sort newest-to-oldest by `date`.
- Exclude encounters that are stale (outside the handoff window, typically >90 days from the transition date unless directly relevant) or unrelated (type does not serve the handoff purpose).
- Document excluded encounter IDs in `excluded_encounter_ids` sorted ascending.

### Referral Coordination

- Select the most recent signed encounter whose `care_plan_tag` matches the referral purpose (e.g., `cardiology_referral_for_hfpef_dyspnea`).
- If no tagged encounter matches, take the most recent signed office visit.

## Risk Flag Derivation

### Flag Catalog and Derivation Rules

| Risk Flag | Conditions | Medications | Notes |
|---|---|---|---|
| `cognitive_memory_loss` | `memory_loss` or `amnestic_disorder` | — | Flag if patient has an active cognitive condition |
| `fall_risk_note_required` | `right_knee_oa`, `left_knee_oa`, `right_hip_oa`, `left_hip_oa` | pain management meds (e.g., `acetaminophen`) | Flag if patient has lower-extremity OA with pain management |
| `hypertension` | `hypertension` | — | Flag if hypertension is active |
| `insulin_dependent_diabetes` | `diabetes_type_2` | `insulin_glargine` or any insulin | Flag only when diabetes is combined with insulin therapy |
| `latex_allergy` | — | — | Flag if latex allergy is active in the allergy list |
| `perioperative_glucose_plan_needed` | `diabetes_type_2` | `insulin_glargine` or any insulin | Flag when diabetic patient on insulin needs perioperative glucose management |

### Risk Flag Evidence

For each flag emitted, build an evidence object linking it to the supporting clinical items:
- `condition_keys`: active condition keys that support the flag (sorted ascending)
- `medication_keys`: active medication keys that support the flag (sorted ascending)
- `encounter_ids`: encounter IDs that document the condition or risk (sorted ascending)

If a risk flag derives solely from allergy data (e.g., latex_allergy), emit it with empty `condition_keys`, `medication_keys`, and `encounter_ids` arrays.

## Packet Readiness

### Merge Packets

| Status | Condition |
|---|---|
| `ready` | All required evidence present, no blocking issues |
| `ready_with_review_note` | Minor ambiguities in identity signals but merge can proceed |
| `blocked` | Critical data missing (patient, duplicate candidate, clinical lists) |

### Care Transition Packets

| Status | Condition |
|---|---|
| `ready` | No risk flags, all required sections present |
| `ready_with_risk_flags` | Risk flags present but no blocking issues |
| `not_ready` | Blocking issues present |

### Referral Packets

| Overall Readiness | Condition |
|---|---|
| `ready_to_send` | No blocking issues |
| `hold_for_missing_documents` | Required documents missing |
| `hold_for_authorization` | Authorization not approved |
| `hold_for_clinical_clarification` | Diagnosis code or allergy issues need resolution |

## Referral Letter Field Selection

Enum choices for referral letter fields are selected based on evidence:

| Field | Selection Logic |
|---|---|
| `diagnosis_summary_choice` | Match the primary referral diagnosis + narrative to the relevant enum; e.g., `hfpef_with_exertional_dyspnea` when I50.32 + R06.02 are present |
| `allergy_statement_choice` | Based on active allergy records and completeness: `active_sulfa_antibiotics_rash_moderate` if sulfa allergy active, `no_known_allergies` if allergy list is empty, `allergy_details_incomplete` if some but not all allergies documented |
| `recent_encounter_choice` | Based on the most recent relevant encounter: e.g., `pcp_2026_02_11_hfpef_dyspnea` |
| `document_packet_choice` | Based on required document availability: `final_echo_and_office_note_available` if both present |
| `medication_summary_choice` | Based on active meds with referral relevance: e.g., `include_furosemide_and_lisinopril` |
| `recipient_choice` | Based on receiving provider: e.g., `renee_okafor_summit_heart_center` |
| `authorization_statement_choice` | Based on authorization status: `authorization_approved`, `authorization_pending`, `authorization_denied`, `authorization_unknown` |
| `readiness_choice` | Based on overall readiness: `send_without_blocker`, `hold_for_missing_document`, etc. |

## ServiceRequest Validation

### SBAR Coverage

A ServiceRequest is SBAR-complete when it contains all four sections:
- `situation`
- `background`
- `assessment`
- `recommendation`

Check `sbar_sections` on the ServiceRequest object. If all four are present and populated, SBAR is complete.

### Service Code Validation

Check `GET /api/service-codes/{code}`. If it returns a record (not 404), the code is valid. Also verify the code's service line matches the expected specialty.

## Duplicate Tiering Policy

For batch audits:
- All referral rows in a duplicate group (same patient, same clinical referral) are assigned to `tier_1_duplicate_blocker_referral_ids`.
- Scope: `tier_all_duplicate_group_rows_as_duplicate_blockers` — the entire group is flagged, not just the duplicate.
- Same-patient referrals that are clinically separate (different body parts, different service lines) go into `separate_same_patient_referral_ids`, not the duplicate group.

## Insurance Anomalies

| Anomaly Type | Detection | Disposition |
|---|---|---|
| `shared_insurance_different_patients` | Same `insurance_id` appears on different `patient_id` values within the same batch | `verify_insurance_membership_do_not_merge` — flag for verification but do not merge the patients |
| `same_patient_separate_clinical_referrals` | Same patient has multiple referrals for different clinical reasons | `separate_clinical_review_not_duplicate` — each referral is a separate clinical event |

## Action Plan Tiering

| Tier | Primary Reason | Typical Assignment |
|---|---|---|
| Tier 1 (immediate) | `urgent_coding_or_duplicate_blocker` | Duplicate group rows and urgent-coded referrals with mismatches |
| Tier 2 (short-term) | `routine_coding_auth_or_document_blocker` | Referrals with invalid/out-of-range codes, laterality/narrative mismatches, or missing authorizations/documents |
| Tier 3 (administrative) | `administrative_document_completion` | Referrals missing only administrative documents (office notes, records) with otherwise valid codes |

## Sorting Conventions

| Context | Sort Order |
|---|---|
| Set arrays (match_signals, conflict_signals, keys) | Ascending alphabetical |
| Encounter arrays | Newest-to-oldest by date |
| ID arrays inside objects | Ascending alphabetical |
| Referral object arrays | Ascending by `referral_id` |
| reason_code_validation arrays | Ascending by `code` |
| duplicate_groups | Ascending by `group_id` |
| insurance_patient_anomalies | Ascending by `anomaly_id` |
| risk_flag_evidence | Ascending by `risk_flag` |

## Specialist Provider Identification

For merge packets and referral packets:

- The **specialist provider** is the author of the key external continuity document or the receiving provider on the referral. Look up the provider via `GET /api/providers/{provider_id}`.
- The **primary care provider** comes from the patient's `primary_care_provider_id` field.
- If the task requires a `contact_reason` for the specialist, derive it from the context: e.g., "External cardiology continuity document on the source duplicate shell" or the referral service line.
