# EHR Quality-Governance Packet Skill

## Purpose

Produce normalized JSON packets for EHR quality-governance workflows: duplicate-chart merge readiness, referral coordination, care-transition handoffs, duplicate/ServiceRequest validation, and referral-batch audits. All data comes from a read-only EHR API; the output is structured JSON conforming to a task-specific answer template.

## Entry Instructions

### 1. Read the prompt and answer template first

- Parse the task prompt to identify: the object IDs (candidate, patient, referral, batch, service-request, provider), the packet type, and which API endpoint families are relevant.
- Read the answer template (`input/payloads/answer_template.json`) **before** making any API calls. The template defines every required key, field type, enum value, and ordering rule. Treat the template as the schema contract — any missing key or wrong enum value scores zero for that section.

### 2. Fetch all relevant API data systematically

Hit every endpoint that the prompt mentions or that the template implies. The base URL is `<TASK_ENV_BASE_URL>` (replace at solve time with the actual environment base). Required endpoint families:

| Endpoint family | When needed |
|---|---|
| `GET /api/patients/{id}` | Every task with a patient |
| `GET /api/patients/{id}/conditions` | Clinical union, risk flags, diagnosis reconciliation |
| `GET /api/patients/{id}/medications` | Clinical union, medication highlights |
| `GET /api/patients/{id}/allergies` | Allergy readiness, latex/cross-reaction flags |
| `GET /api/patients/{id}/encounters` | Handoff encounter selection, recent evidence |
| `GET /api/patients/{id}/documents` | Document evidence, echo/office-note status |
| `GET /api/patients/{id}/immunizations` | Care-transition packets |
| `GET /api/patients/{id}/disclosures` | Care-transition packets |
| `GET /api/patients/{id}/service-requests` | ServiceRequest validation |
| `GET /api/duplicates/{id}` | Duplicate merge packets |
| `GET /api/referrals` + `GET /api/referrals/{id}` | Referral coordination and batch audits |
| `GET /api/icd10/{code}` | Code validation (chapter, expected_terms, laterality) |
| `GET /api/providers/{id}` | Provider contact details |
| `GET /api/service-codes/{code}` | Service-code validation |
| `GET /api/audit-logs` | Audit evidence for merge packets |

Always fetch **both** patients in a duplicate pair. Always validate every ICD-10 code via `/api/icd10/{code}`.

### 3. Build the answer section by section

Work through the template keys in order. For each section:

#### Duplicate-merge packets
- **Target/source**: The duplicate candidate's `merge_preview.preferred_target_patient_id` is the canonical target. The other patient is the source. If `preferred_target_patient_id` is null, use `canonical_status` (`active` beats `possible_duplicate` / `duplicate`).
- **Merge disposition**: Use `ready_to_merge` when match signals dominate and the only conflict is cosmetic (address abbreviation, nickname vs formal name). Use `needs_review` when laterality conflicts or different given names exist. Use `do_not_merge` only for clear identity mismatches.
- **Clinical unions vs active key unions**: `clinical_unions` reflects the merge-preview keys (often incomplete). `active_key_unions` is the **true union** from live patient active-list endpoints. Always compute `active_key_unions` by deduplicating the sorted set of `normalized_key` values from both patients' active-status records.
- **Active-list reconciliation**: Identify keys present in patient active-list endpoints but missing from the merge preview. Report these in `condition_keys_added_from_active_endpoints`, `medication_keys_added_from_active_endpoints`, and `allergy_keys_added_from_active_endpoints`.
- **Excluded distractors**: Report inactive-condition keys, inactive-medication keys, chart_summary documents, and audit logs for unrelated patients.
- **Document selection**: Include only identity-verification and external-continuity documents (e.g., `external_cardiology_note`, `identity_verification`). Exclude `chart_summary`.
- **Packet contact**: The specialist provider is the one whose service_line matches the shared external document source (e.g., cardiology for an external cardiology note). The PCP comes from the patient record.

#### Referral coordination packets
- **Active diagnoses**: List every active condition for the patient. Mark `referral_relevant` = true if the condition's ICD chapter matches the referral service line, or the condition code appears in the referral's reason codes or encounter diagnoses.
- **Referral code set**: Look up the referral's `diagnosis_code` via `/api/icd10/{code}`. Compare `expected_terms` against `diagnosis_narrative`. If any expected term appears in the narrative, set `narrative_match: true` and `icd_validation: valid_matches_narrative`. Otherwise set `narrative_match: false` and `icd_validation: valid_but_narrative_mismatch`. Supporting codes come from other referral-relevant active diagnoses.
- **Allergy readiness**: If the allergy record has allergen + reaction + severity all populated and status is `active`, use `complete_documented` with `ready_for_letter: true` even if a coordination note says to confirm details; set `follow_up_needed: true`. Use `incomplete_needs_clarification` only when a field is truly missing.
- **Recent encounter evidence**: Choose the encounter whose diagnoses include the referral's diagnosis code and whose care-plan notes mention the referral reason. Report the `care_plan_tag` enum that best matches the encounter context.
- **Document evidence**: Check the referral's `documents_received` list for echo/office_note. Cross-reference with the patient's documents endpoint for IDs. If the documents endpoint doesn't show an office_note document but the referral metadata says `office_note` was received, still set `office_note_received: true`.
- **Medication highlights**: Include every active medication. Classify by highlight_reason: diuretics → `heart_failure_diuretic`, ACE/ARB → `blood_pressure_management`, metformin/insulin → `diabetes_management`, statins → `lipid_management`, else → `other_active_medication`.
- **Authorization/readiness**: If authorization is approved and all required documents received, set `overall_readiness: ready_to_send` and `readiness_choice: send_without_blocker`. If allergy needs clarification, use `hold_for_clinical_clarification` / `hold_for_allergy_clarification` only when allergy fields are actually missing.

#### Care-transition packets
- **Handoff encounters**: Select encounters whose diagnoses include the surgical target condition (e.g., right_hip_oa for orthopedic surgery) or whose type is `care_transition`. Pick the 4 most recent among these. Exclude encounters that are unrelated (e.g., memory-loss follow-up) or stale (older than the surgical window).
- **Risk flags**: Derive from conditions, medications, and encounter notes. Use only the `allowed_values` in the template. Evidence: `condition_keys` from active conditions, `medication_keys` from active meds, `encounter_ids` from encounters that document the risk.
- **Latest immunization**: The most recent by date across all immunization records.
- **Disclosure**: Match the one with `recipient_provider_id` equal to the target provider.
- **Packet readiness**: Use `ready_with_risk_flags` when risk flags exist but no blocking issues. Use `not_ready` only when disclosure is not permitted or required data is missing.

#### Duplicate-review + ServiceRequest validation
- **Duplicate candidate status**: Preserve the API-returned `status` as `candidate_status` (e.g., `needs_review`). Do not override it.
- **Decision**: If match signals are strong (same DOB, same insurance, same address) and conflict signals are only cosmetic (abbreviation, nickname), use `merge`. If there are laterality conflicts, different given names, or different phones, use `review_hold`. If evidence clearly shows two different people, use `do_not_merge`.
- **ServiceRequest**: Copy fields from the API record. Validate `service_code` against `/api/service-codes/{code}` (`service_code_valid` = true if the code exists and matches the service line). Validate each `reason_code` via `/api/icd10/{code}`: check the chapter, set `matches_patient_evidence` based on whether the patient has an active condition with that code.
- **SBAR coverage**: Enumerate which of `situation`, `background`, `assessment`, `recommendation` are present. If all four, `complete: true`.

#### Referral-batch audits
- **Invalid/out-of-range codes**: Any referral whose `diagnosis_code` has an ICD chapter that is not `Musculoskeletal` or `Injury` (for orthopedic batches). `issue_type: out_of_range_chapter` for wrong chapter, `unknown_code` for codes not in the ICD directory.
- **Laterality/narrative mismatches**: For every referral, compare `diagnosis_narrative` against ICD `expected_terms`. Flag `laterality_mismatch` when the narrative says "left" but the code specifies right (or vice versa). Flag `narrative_mismatch` when no expected term appears in the narrative. Flag `missing_laterality` when the code requires laterality but the narrative omits it. **Be thorough**: check every single referral, not just obvious ones.
- **Duplicate groups**: Find patients with multiple referrals in the batch. `duplicate_type: same_patient_resubmission`. `recommended_disposition: consolidate_under_original`.
- **Duplicate tiering policy**: Under `tier_all_duplicate_group_rows_as_duplicate_blockers`, put ALL referral IDs in the duplicate group into `tier_1_duplicate_blocker_referral_ids`. Put same-patient referrals that are clinically separate into `separate_same_patient_referral_ids`.
- **Insurance-patient anomalies**: Find different patients who share the same `insurance_id`. `disposition: verify_insurance_membership_do_not_merge`.
- **Follow-up queues**:
  - `authorization_missing`: referrals with `authorization_status: missing`
  - `authorization_pending`: referrals with `authorization_status: pending`
  - `records_request`: referrals missing `office_note` in `documents_received`
  - `imaging_follow_up`: referrals missing both `mri` and `xray` in `documents_received`
- **Action plan tiering**:
  - Tier 1 (immediate): urgent referrals with coding issues or duplicate-blocker status. Also include both referrals in a duplicate group.
  - Tier 2 (short-term): routine referrals with coding mismatches, auth issues, or narrative problems.
  - Tier 3 (administrative): routine referrals with only missing documents and no coding issues.
- **Summary counts**: Derive all counts from the categorized data above. `validated_ready_no_follow_up_count` = referrals with no coding issues, no auth issues, no missing documents, and not in a duplicate group.

### 4. Sort and normalize arrays

- Arrays described as sets must be sorted alphabetically (ascending) unless the template specifies another order.
- Referral-object arrays in audits: sort by `referral_id` ascending.
- ID arrays within objects: sort ascending.
- Handoff encounters: sort newest-to-oldest by date.
- Use the `normalized_key` field from API records, not free-text descriptions, for condition/medication/allergy key arrays.

### 5. Validate against the template before returning

- Every required top-level key must be present.
- Every enum value must match one of the allowed values in the template exactly (case-sensitive, underscores not hyphens).
- Booleans must be actual `true`/`false`, not strings.
- Null fields must be `null`, not absent or empty string, where the template allows null.
- Dates must be `YYYY-MM-DD` strings.

## Common pitfalls

| Pitfall | Fix |
|---|---|
| Using merge-preview keys instead of live patient-endpoint keys for clinical unions | Always compute `active_key_unions` from both patients' active condition/medication/allergy endpoints |
| Marking allergy as `incomplete_needs_clarification` when all fields are populated | Only mark incomplete when a field is actually missing; coordination notes don't make the data incomplete |
| Selecting the most recent encounters instead of the most relevant for handoff | Prioritize encounters with diagnoses matching the surgical target condition |
| Overriding the duplicate candidate API status | Preserve the API `status` as `candidate_status`; set `decision` separately |
| Missing ICD-10 expected_terms comparison | Look up every diagnosis code; compare against narrative term by term |
| Forgetting to check laterality on laterality-requiring codes | If `requires_laterality: true` and the narrative omits the side, flag `missing_laterality` |
| Classifying a narrative as matching when only a partial term matches | "right knee pain" in narrative ≠ "right medial meniscus tear"; require an expected term to appear as a substring |
| Only checking obvious mismatches and missing subtle ones in batch audits | Systematically compare every referral's narrative against its ICD expected_terms |

## Supporting reference

- `endpoint_map.md` — Full list of API endpoints with parameter descriptions
