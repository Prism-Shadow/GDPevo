# Per-task-type playbooks

Read the task's own `answer_template.json` for the exact keys/enums — it always wins.
These playbooks say *how to derive* each field. All example enum names below are the
kinds of values templates use; emit only values allowed by the template in front of you.

---

## 1. Duplicate-chart merge-readiness packet

Case objects: a duplicate `candidate_id` and two `patient_ids`. Sometimes an extra
`merge_packet_request.json` restates the requested outputs — treat it as a checklist,
not new data.

Evidence: `/api/duplicates/{candidate_id}`, both `/api/patients/{id}` details, both
patients' active `conditions`/`medications`/`allergies`, `documents`, `audit-logs`
(for the involved patients), and provider lookups.

Derive:
- **Canonical target vs source** — target = the active canonical record
  (`merge_preview.preferred_target_patient_id`); source = `merge_preview.source_patient_id`.
- **Disposition** (map the candidate `status` + signals to the template's enum):
  - `open` with a strong identity match, a preferred target set, and no blocking
    conflict → *merge ready* (`ready_to_merge` / `merge_ready`);
    `manual_review_required = false`.
  - `needs_review` / meaningful conflict signals (e.g. `opposite_laterality_problem`,
    `different_given_name`) → *review hold* (`needs_review` / `review_hold` /
    `needs_manual_review`); set merge target & source to `null` and
    `manual_review_required = true`.
  - `confirmed_duplicate` → merge; `not_duplicate` → `do_not_merge`.
- **Reason codes** — standardized snake_case labels, each expressing one fact that
  drove the disposition (strength of the identity match, the candidate being an
  active/open duplicate, the source already resolving to the target, the target being
  the active canonical record, or — for a hold — the specific conflict). Emit only
  labels justified by evidence you fetched; if the template enumerates allowed values
  use those, otherwise coin stable descriptive codes. Sort alphabetically.
- **Clinical unions** — active `normalized_key` set-union across both patients
  (conditions/medications/allergies), sorted. Fill every union-shaped key the template
  has (e.g. both `clinical_unions` and `active_key_unions`) from the same computation.
- **Active-list reconciliation** — keys present in the active endpoints but missing
  from `merge_preview`, per list.
- **Identity signals** — candidate `match_signals` / `conflict_signals`, plus the
  demographic match/conflict comparison of the two patient records.
- **Evidence IDs** — `document_ids`: identity / external-continuity documents on the
  involved patients (exclude `chart_summary` and other admin exports);
  `audit_ids`: `identity_review` / `external_import` logs for the involved patient_ids.
  Put unrelated-patient documents/audits (and inactive clinical keys) under
  `excluded_distractors`. Sort all id lists.
- **Document-selection policy** — basis = identity/external-continuity only; list the
  excluded document types (e.g. `chart_summary`).
- **Packet readiness** — `ready` when the disposition is merge-ready with no open
  review note; otherwise `ready_with_review_note` / `blocked` with the note codes.
- **Packet contact** — specialist provider from the external-continuity document's
  source/service line (via `/api/providers`); primary_care_provider from patient detail.

---

## 2. Specialty referral coordination packet

Case objects: a `referral_id` and a `patient_id`.

Evidence: `/api/referrals/{id}`, patient `conditions`/`medications`/`allergies`/
`encounters`/`documents`, `/api/icd10/{code}`, `/api/providers/{receiving_provider_id}`.

Derive:
- **patient_referral** — echo `patient_id`, `referral_id`, `batch_id`, `service_line`,
  `requested_date` from the referral.
- **active_diagnoses** — active problem-list conditions plus any referral-intake
  diagnosis; set `referral_relevant = true` for those matching the referral's clinical
  focus (the specialty's system + the presenting complaint), false otherwise.
- **referral_code_set** — `primary_code` = referral `diagnosis_code`; validate via
  ICD-10 (chapter fit + narrative/laterality). `icd_validation` picks the enum
  (`valid_matches_narrative` / `valid_but_narrative_mismatch` / `invalid_code` /
  `wrong_service_chapter`); `primary_code_chapter` and `narrative_match` from the lookup;
  `supporting_codes` = other relevant active/intake codes.
- **allergy_readiness** — active allergies with `severity`/`status`/`source`.
  `complete_documented` + `ready_for_letter = true` when documented and unambiguous;
  a `coordination_note` asking to confirm details ⇒ consider follow-up.
- **recent_encounter_evidence** — the most relevant recent encounter for the referral
  reason: `encounter_id`, `date`, `type`, `provider_id`, `signed_status`,
  `diagnosis_codes`, `medications_mentioned`, and the matching `care_plan_tag`.
- **required_document_evidence** — from `documents_received` / the documents endpoint:
  echo (final?), office note; list any `missing_required_documents`.
- **receiving_provider** — `/api/providers/{receiving_provider_id}`.
- **authorization_readiness** — map `authorization_status`, referral `status`,
  `urgency`; `overall_readiness = ready_to_send` only when there are no
  `blocking_issues`; otherwise a matching hold + the blocking-issue enums.
- **medication_highlights** — active meds relevant to the referral first, each tagged
  with a `highlight_reason`; treated as a set by lowercased medication name.
- **referral_letter_fields** — choose each enum consistent with the packet above
  (diagnosis summary, allergy statement, recent encounter, document packet,
  medication summary, recipient, authorization statement, readiness).

---

## 3. Care-transition handoff packet

Case objects: a `patient_id` and a recipient `provider_id` (a service line).

Evidence: patient detail, active `conditions`/`medications`/`allergies`, `encounters`,
`immunizations`, `disclosures`, `/api/providers/{provider_id}`.

Derive:
- **patient** / **recipient** — demographics; recipient from the provider directory
  (include `service_line`).
- **active_*_keys** — active `normalized_key` values, sorted ascending.
- **handoff_encounters** — select the template-specified number (e.g. 4) of the most
  relevant recent handoff encounters for this transition, **newest→oldest**. Include
  the designated handoff/care-transition series within the window; **exclude** stale
  (out-of-window) visits and unrelated distractors (random-hex-ID one-offs,
  telehealth/amended visits not part of the handoff). Record `source_selection`
  (`selection_basis` code, `selected_encounter_ids` newest→oldest,
  `excluded_encounter_ids` sorted ascending).
- **latest_immunization** — the max-`date` immunization.
- **disclosure** — the disclosure matching the recipient/purpose; note its `status`
  (a non-`permitted` status is a blocking issue).
- **risk_flags** — derive from active clinical evidence, restricted to the template's
  `allowed_values`, e.g.: an insulin medication ⇒ `insulin_dependent_diabetes` **and**
  `perioperative_glucose_plan_needed`; a latex allergy ⇒ `latex_allergy`; OA / mobility
  conditions (esp. for a surgical elderly patient) ⇒ `fall_risk_note_required`; a
  memory-loss condition ⇒ `cognitive_memory_loss`; hypertension ⇒ `hypertension`.
  Sort ascending.
- **risk_flag_evidence** — for each flag, the supporting `condition_keys`,
  `medication_keys`, and `encounter_ids` (each sorted); ordered by `risk_flag`.
  Evidence encounters may include ones excluded from the handoff list.
- **packet_readiness** — `ready_with_risk_flags` when flags exist but nothing blocks;
  `ready` when clean; `not_ready` with `blocking_issue_codes` when a required component
  is missing or the disclosure is not permitted.

---

## 4. ServiceRequest quality review (often bundled with a duplicate review)

Case objects: a duplicate `candidate_id` + two patients, and a draft ServiceRequest id.

Evidence: `/api/duplicates/{candidate_id}`, both patient details/conditions,
the patient's `service-requests`, `/api/service-codes/{code}`, `/api/icd10/{code}`,
provider lookups.

Derive:
- **duplicate_review** — `candidate_status` from the candidate `status`; `decision`
  mapped from it (`confirmed_duplicate`→`merge`, `needs_review`→`review_hold`,
  `not_duplicate`→`do_not_merge`); `merge_target/source` = ids when merging, else
  `null`; `match_signals` / `conflict_signals` from the candidate, filtered to the
  template's `allowed_values`.
- **service_request** — read the SR **from the live record** (don't assume its
  `status`): `status`, `intent`, `priority`, `service_code`, `requester_id`→
  `requester_provider_id`, `performer_id`→`performer_provider_id`, `authored_on`,
  `occurrence_date`, `reason_codes`. `service_code_valid` from
  `/api/service-codes/{code}` (`active` + service line); `performer_service_line`
  from the performer provider. `reason_code_validation`: per code, `valid` (200 vs
  404), `chapter`, and `matches_patient_evidence` (does the patient have an active
  condition / related evidence for it); sort by `code`.
- **sbar_coverage** — from the SR's `sbar` object: `sections_present` = the sections
  present and non-empty (`situation`/`background`/`assessment`/`recommendation`);
  `missing_sections` = the rest; `complete = true` iff all four present.
- Include the `task_id` `required_value` verbatim.

---

## 5. Referral-batch coding audit

Case object: a referral `batch_id`.

Evidence: `/api/referrals` (fetch all, then **filter client-side by `batch_id`** —
the query param is ignored), `/api/icd10/{code}` per diagnosis, `/api/patients` /
detail for insurance/patient checks, `/api/providers`.

Derive:
- **batch** — `batch_id`, `service_line`, a representative `requested_date`,
  `record_count` = rows in the batch, `unique_patient_count` = distinct `patient_id`.
- **invalid_or_out_of_range_code_referrals** — per referral, ICD-10 chapter vs the
  batch's expected chapter (orthopedics ⇒ `Musculoskeletal`): wrong chapter ⇒
  `out_of_range_chapter`; 404 ⇒ `unknown_code`.
- **laterality_or_narrative_mismatch_referrals** — per referral, compare
  `diagnosis_narrative` to the code's `expected_terms` and laterality:
  `laterality_mismatch`, `narrative_mismatch`, and/or `missing_laterality`; carry
  `expected_terms`.
- **duplicate_groups** — same `patient_id` resubmitted ⇒ `same_patient_resubmission`,
  disposition `consolidate_under_original`; group id derived stably from the patient.
  Fill `duplicate_tiering_policy` (all duplicate-group rows are Tier-1 duplicate
  blockers; genuinely separate same-patient clinical referrals are not part of the group).
- **insurance_patient_anomalies** — shared `insurance_id` across *different* patients ⇒
  `shared_insurance_different_patients` / `verify_insurance_membership_do_not_merge`;
  same patient with separate clinical referrals ⇒ `same_patient_separate_clinical_referrals`
  / `separate_clinical_review_not_duplicate`.
- **follow_up_queues** — `authorization_missing` / `authorization_pending` from
  `authorization_status`; `records_request` when an office note is missing from
  `documents_received`; `imaging_follow_up` when required imaging (mri/x-ray/echo) is
  missing or pending. Each list sorted ascending.
- **action_plan** — Tier 1 = `urgent_coding_or_duplicate_blocker` (urgent urgency or
  duplicate-group rows); Tier 2 = `routine_coding_auth_or_document_blocker`; Tier 3 =
  `administrative_document_completion` (only minor admin follow-up). `owner_provider_id`
  = the referral's `receiving_provider_id`. Sort each tier by `referral_id`.
- **summary_counts** — compute every count so it matches the arrays above (row/patient
  totals, urgency split, invalid/mismatch counts, duplicate/insurance-anomaly counts,
  each follow-up queue length, tier counts, and validated-ready-no-follow-up).
