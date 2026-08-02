# Packet playbooks

One recipe per packet family seen in training. Always let the specific
`answer_template.json` override anything here. These describe *method*, not
answers.

## A. Duplicate-chart merge readiness packet
Inputs: a duplicate-candidate id + two patient ids (± a merge-request payload).
1. Fetch the candidate (`match_signals`, `conflict_signals`, `merge_preview`,
   `status`) and both patient details.
2. **Canonical direction:** target/source = `merge_preview.preferred_target_/
   source_patient_id` when set; otherwise infer from `canonical_status` /
   completeness. If the engine left them null or a hard conflict exists, mark
   `null`/needs-review as the template allows.
3. **Active key unions** = union of active `normalized_key`s from both patients'
   list endpoints (§3.2). Reconciliation fields = keys in the endpoints but absent
   from `merge_preview`. Excluded-distractor fields = inactive/non-merge keys.
4. **Identity signals:** `match_signals`/`conflict_signals` straight from the
   candidate; `demographic_matches`/`conflicts` by comparing patient
   `dob/phone/insurance_id/address/given_name/family_name`.
5. **Evidence:** `final` identity/external-continuity documents only (exclude
   chart_summary etc., listing excluded types); audit ids scoped to these patients
   and this merge event.
6. **Disposition:** map the one decision onto each field's enum. Any real conflict
   (e.g. address/name variance, shared-doc reconciliation) ⇒ conflict-review /
   manual-review-required rather than clean merge; opposite-laterality or identity
   conflicts ⇒ do-not-merge / needs_review.
7. **Contacts:** specialist = provider for the service line driving the shared
   external/continuity document (resolve via `/api/providers`); PCP = patient's
   embedded `primary_care_provider`.

## B. Referral coordination packet (e.g. cardiology letter)
Inputs: a referral id + patient id.
1. Fetch the referral (diagnosis code/narrative, `documents_received`,
   `authorization_status`, `receiving_provider_id`, `status`, `urgency`) and the
   patient's active conditions/medications/allergies + recent encounters.
2. **Active diagnoses** from active conditions; flag `referral_relevant` by
   service-line/narrative fit.
3. **referral_code_set:** validate the referral `diagnosis_code` via ICD-10 (§3.6)
   — chapter vs. service line, narrative match, laterality; set the validation enum
   and `primary_code_chapter`. Supporting codes from other relevant active dx.
4. **Allergy readiness:** summarize active allergies; readiness = documented vs.
   needs-clarification (heed coordination notes like "confirm allergy details").
5. **Encounter evidence:** most recent relevant signed encounter; capture id, date,
   type, provider, `diagnosis_codes`, meds, and a care-plan tag.
6. **Required documents:** derive from `documents_received` (e.g. cardiology needs a
   `final` echo + office note); list any `missing_required_documents`.
7. **Receiving provider** via `/api/providers/{receiving_provider_id}`.
8. **Authorization/readiness:** `ready_to_send` only if auth approved + required
   docs present + allergy documented + code valid; else the matching `hold_for_*`,
   with `blocking_issues` enumerated.
9. **Medication highlights:** active meds relevant to the referral first, tagged by
   reason.
10. **referral_letter_fields:** pick each normalized enum choice consistent with the
    evidence above.

## C. Care-transition handoff packet
Inputs: a patient id + a recipient provider id.
1. Patient identity + recipient provider (name/facility/service_line).
2. Active condition/medication/allergy `normalized_key` sets, sorted ascending.
3. **Handoff encounters:** choose the N most relevant recent signed encounters for
   the transition (template usually fixes the count, newest→oldest). Record a
   normalized `selection_basis`; put reviewed-but-rejected ids in
   `excluded_encounter_ids` (stale / outside-window / off-service).
4. **Latest immunization** (max date); **applicable disclosure** matching the
   recipient (`recipient_provider_id`) and `permitted` status.
5. **Risk flags:** emit only allowed-value codes, each backed by
   `risk_flag_evidence` (the specific active condition/medication keys and
   encounter ids). Sort ascending.
6. **Readiness:** `ready` / `ready_with_risk_flags` / `not_ready` with
   `blocking_issue_codes` for any missing required component or non-permitted
   disclosure.

## D. Duplicate + ServiceRequest validation packet
Inputs: a duplicate-candidate id, two patient ids, a draft ServiceRequest id.
1. **duplicate_review:** candidate `status` → `candidate_status`; decision from
   signals — hard conflicts (opposite laterality, different identity) or null
   preview direction ⇒ `review_hold`/`do_not_merge` with null merge target/source;
   strong matches with no blocking conflict ⇒ `merge`. Emit `match_signals`/
   `conflict_signals` mapped to the template's controlled enum.
2. **service_request:** read the draft SR (status/intent/priority/service_code/
   requester/performer/reason_codes/authored_on/occurrence_date). Validate
   `service_code` via `/api/service-codes` (`service_code_valid`). Derive
   `performer_service_line` from the performer provider. Validate each reason code
   via ICD-10 → `{code, valid, chapter, matches_patient_evidence}` (compare to the
   patient's conditions); sort by code.
3. **sbar_coverage:** `sections_present`/`missing_sections` from `sr.sbar`;
   `complete` iff all four present.

## E. Referral-batch audit
Inputs: a batch id (service line).
1. Fetch all referrals, filter to the batch. `record_count` = rows;
   `unique_patient_count` = distinct patient ids.
2. **Invalid/out-of-range codes:** for each referral look up `diagnosis_code`.
   404 ⇒ `unknown_code`; wrong chapter for the service line ⇒
   `out_of_range_chapter` (expected chapter from §3.6, e.g. orthopedics →
   `Musculoskeletal`). Record actual vs. expected chapter.
3. **Laterality/narrative mismatches:** compare narrative to `expected_terms` and
   the code's laterality → `laterality_mismatch|narrative_mismatch|
   missing_laterality`, with `expected_terms`.
4. **Duplicate groups:** same `patient_id` submitted more than once in the batch ⇒
   `same_patient_resubmission` → `consolidate_under_original`; assign tiering per
   the policy block (all duplicate-group rows = duplicate blockers; genuinely
   separate clinical referrals for the same patient are not part of the group).
5. **Insurance/patient anomalies:** shared insurance across different patients ⇒
   verify-membership-do-not-merge; same patient separate clinical referrals ⇒
   separate-clinical-review.
6. **Follow-up queues:** `authorization_missing`/`_pending` from
   `authorization_status`; `records_request` = missing office note;
   `imaging_follow_up` = missing/pending imaging. Sort ids ascending.
7. **Action plan:** Tier 1 = urgent coding or duplicate blocker; Tier 2 = routine
   coding/auth/document blocker; Tier 3 = administrative document completion.
   `owner_provider_id` = the referral's receiving provider.
8. **summary_counts:** compute every count the template lists (totals, urgent/
   routine, invalid, mismatch, duplicate groups, anomalies, each queue, each tier,
   and validated-ready-no-follow-up). Cross-check they reconcile with the arrays.
