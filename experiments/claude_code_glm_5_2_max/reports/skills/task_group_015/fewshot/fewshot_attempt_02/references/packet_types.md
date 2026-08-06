# Packet-Type Playbooks

Identify the packet type from `prompt.txt`, then apply the matching playbook. All
logic is evidence-driven: classify from fetched records, never from assumptions.
Enum literals below come from the templates' `allowed_values`; free-form labels must
be derived from the evidence, not copied from another task.

## A. Duplicate-merge readiness packet
Trigger: prompt names a duplicate candidate id and two patient ids and asks for a
"merge readiness packet".

1. Resolve the candidate (`/api/duplicates/{id}`); confirm its two patient ids.
2. Fetch both patients' demographics, active conditions / medications / allergies,
   encounters, documents, and the relevant audit logs.
3. Target / source: the canonical target is the patient that is the active canonical
   record and that the candidate points the source toward; the source is the
   duplicate shell. If the candidate does not confirm duplication, target and source
   are `null` and the disposition is `needs_review` / `do_not_merge`.
4. Disposition: `ready_to_merge` when the identity match is strong, the candidate
   points source → target, and there are no blocking conflicts; otherwise
   `needs_review` or `do_not_merge`. Mirror into `merge_decision` with
   `manual_review_required` and reason codes (derived from the evidence).
5. Clinical unions: union of active `normalized_key`s across both patients.
   Authoritative source = patient active-list endpoints over the duplicate preview;
   report keys present in the active endpoints but missing from the preview.
6. Identity signals: collect `match_signals` and `conflict_signals` from the
   candidate and the corroborating demographic comparison; map the matching vs
   conflicting demographic fields to `demographic_matches` /
   `demographic_conflicts`. Where the template enumerates allowed signal values, use
   only those; where it leaves them as labels, derive normalized labels from the
   field comparison.
7. Evidence: `document_ids` = identity or external-continuity documents only
   (exclude internal summary-type and unrelated documents, per
   `document_selection_policy`); `audit_ids` = audit entries tied to the merge /
   identity event.
8. Packet contact: the specialist provider tied to an external-continuity document
   on the source shell, plus the patient's primary care provider (both from the
   provider directory).
9. Readiness: `ready` / `ready_with_review_note` / `blocked` with review-note codes.

## B. Referral coordination packet
Trigger: prompt names a referral id and patient id and asks for a "coordination
packet" / "referral letter" preparation.

1. Resolve the referral (`/api/referrals/{id}`): batch, service_line,
   requested_date, receiving provider, urgency, authorization status, narrative,
   reason codes.
2. Fetch the patient's active conditions, medications, allergies, encounters,
   documents; look up each reason code via `/api/icd10/{code}`; resolve the
   receiving provider.
3. Active diagnoses: one entry per active condition, each with code, description,
   `normalized_key`, source (problem_list vs referral_intake), and a
   `referral_relevant` flag (true when the code matches the referral's clinical
   narrative / service line).
4. Referral code set: `primary_code` = the referral-relevant code that matches the
   narrative; `supporting_codes` = the rest. `icd_validation` from the ICD-10
   lookup (`valid_matches_narrative` / `valid_but_narrative_mismatch` /
   `invalid_code` / `wrong_service_chapter`); record `primary_code_chapter` and
   `narrative_match`.
5. Allergy readiness: aggregate active allergies; `ready_for_letter` is false when
   records conflict or are incomplete.
6. Recent encounter evidence: the recent encounter whose diagnosis / plan matches
   the referral reason (not necessarily the latest visit); record signed_status, dx
   codes, meds mentioned, and a `care_plan_tag` from the template's allowed values.
7. Required document evidence: are the echo / echocardiogram and office note
   received? List any missing required documents.
8. Receiving provider from the provider directory.
9. Authorization readiness: auth_status, referral_status, urgency,
   overall_readiness, blocking_issues.
10. Medication highlights: referral-relevant active meds, each with a
    `highlight_reason` from the template's allowed values.
11. Referral letter fields: choose the enum for each field that matches the evidence.

## C. Care-transition packet
Trigger: prompt names a patient and a recipient provider and asks for a "care
transition" / "handoff" packet.

1. Resolve patient and recipient provider.
2. Active condition / medication / allergy keys (active only, sorted).
3. Handoff encounters: select the most relevant recent encounters within the
   surgical / transition handoff window; exclude stale, out-of-window, or unrelated
   encounters. Emit newest-to-oldest. Record `selection_basis`, selected ids, and
   excluded ids.
4. Latest immunization (most recent date).
5. Applicable disclosure: the one permitted for the recipient and transition
   purpose.
6. Risk flags: from the template's allowed set only; for each flag, cite the
   condition_keys / medication_keys / encounter_ids that evidence it (empty arrays
   when the flag is set from a non-clinical source).
7. Packet readiness: status, ready_to_send, blocking_issue_codes (missing patient /
   recipient / active lists / handoff encounters / immunization / disclosure, or
   disclosure not permitted).

## D. ServiceRequest / duplicate review
Trigger: prompt names a duplicate candidate, a primary patient, a possible-duplicate
patient, and a draft ServiceRequest id.

1. Resolve the duplicate candidate and both patients; resolve the ServiceRequest
   (`/api/patients/{id}/service-requests`).
2. Duplicate review: `candidate_status` (`confirmed_duplicate` / `needs_review` /
   `not_duplicate`), `decision` (`merge` / `review_hold` / `do_not_merge`),
   target / source (`null` unless merging), and `match_signals` /
   `conflict_signals` from the candidate (only the template's allowed values).
3. ServiceRequest fields: status, intent, priority, service_code +
   `service_code_valid` (via `/api/service-codes/{code}`), requester / performer
   providers, `performer_service_line`, authored_on, occurrence_date, reason_codes.
4. `reason_code_validation`: for each reason code, look it up via
   `/api/icd10/{code}`; record `valid`, `chapter`, and `matches_patient_evidence`
   (true when the patient's active conditions / encounters support that code). Sort
   by code.
5. SBAR coverage: which of situation / background / assessment / recommendation are
   present in the request and supporting records.

## E. Referral-batch audit
Trigger: prompt names a batch id and asks for a batch "audit" with tiers and counts.

1. Resolve the batch via referral search; collect every referral row, service_line,
   requested_date. `record_count` = rows audited; `unique_patient_count` = distinct
   patients.
2. For each referral, look up its diagnosis code via `/api/icd10/{code}`:
   - `invalid_or_out_of_range_code_referrals`: code whose chapter differs from the
     expected chapter for the batch's service line, or an unknown code.
   - `laterality_or_narrative_mismatch_referrals`: compare the code's expected
     laterality / terms to the referral's diagnosis narrative; flag
     `laterality_mismatch`, `narrative_mismatch`, `missing_laterality` as
     applicable; list `expected_terms`.
3. Duplicate groups: same-patient resubmissions (same patient, same clinical reason)
   → `consolidate_under_original`; tier every row in the group as a duplicate
   blocker. Same-patient referrals that are distinct clinical reviews are NOT
   duplicates — list them in `separate_same_patient_referral_ids`.
4. Insurance-patient anomalies: a shared insurance_id across different patients →
   `verify_insurance_membership_do_not_merge`; same patient with separate clinical
   referrals → `separate_clinical_review_not_duplicate`.
5. Follow-up queues: `authorization_missing`, `authorization_pending`,
   `records_request` (missing office note), `imaging_follow_up` (missing / pending
   imaging).
6. Action plan: Tier 1 = urgent coding issue or duplicate blocker; Tier 2 = routine
   coding / auth / document blocker; Tier 3 = administrative document completion.
   Assign an `owner_provider_id` per referral.
7. Summary counts: every count the template lists, derived from the rows above.
