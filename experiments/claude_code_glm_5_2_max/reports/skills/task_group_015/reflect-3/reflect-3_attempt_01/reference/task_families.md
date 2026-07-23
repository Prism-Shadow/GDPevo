# Task-family field checklists

Quick checklist per packet/audit family. These are the fields that most commonly go wrong and the rule that
resolves each. All values come from fetched EHR records; nothing here is a fixed answer.

## Duplicate-chart merge readiness packet
- `candidate_id`, `patient_ids`: from the duplicate candidate record.
- `merge.target_patient_id` / `source_patient_id`: the active/canonical patient is the target; the
  `canonical_status: duplicate` patient is the source. Both null only when on hold (see below).
- `merge.disposition` / `merge_decision.disposition`: benign conflict + confirmed link →
  `ready_to_merge` / `merge_ready_with_conflict_review` (acknowledge the conflict in `reason_codes` and
  `required_review_notes`). Serious/contradictory conflicts → `needs_review` / `review_hold` with target/
  source = `null`.
- `clinical_unions` AND `active_key_unions`: **both** = endpoint active-key union (sorted).
- `active_list_reconciliation`: endpoint union − `merge_preview` union; `authoritative_source` =
  `patient_active_list_endpoints_over_duplicate_preview`.
- `identity_signals.match_signals` / `conflict_signals`: copy verbatim from the candidate.
- `evidence.document_ids` / `audit_ids`: identity + external-continuity docs and case-matching audit logs.
- `excluded_distractors`: inactive condition/med keys, chart_summary doc ids, unrelated-patient audit ids.
- `document_selection_policy`: `identity_or_external_continuity_documents_only`; excluded types listed.
- `packet_contact.specialist_provider`: the provider behind the shared external document match signal;
  `primary_care_provider`: from the patient record.

## Specialty referral coordination packet (e.g. cardiology)
- `patient_referral`: id, referral_id, batch_id, service_line, requested_date from the referral record.
- `active_diagnoses`: every active condition with `code`, `description`, `normalized_key`, `source`,
  `referral_relevant`. `referral_relevant` true for the primary dx + directly supporting symptom dx +
  cardiac comorbidities actively medicated; false for unrelated (e.g. orthopedic) conditions.
- `referral_code_set.primary_code` = referral `diagnosis_code`; `supporting_codes` = only the directly
  supporting symptom code(s) (match the `diagnosis_summary_choice`); `icd_validation` via lookup
  (`valid_matches_narrative` when an expected term appears in the narrative); `primary_code_chapter` from
  lookup; `narrative_match` boolean.
- `allergy_readiness`: `complete_documented` when fully populated; hold the letter only if a coordination
  note demands confirmation. `allergies` echoes the documented allergen/reaction/severity/status/source.
- `recent_encounter_evidence`: the encounter whose note ties to the referral (e.g. "cardiology referral for
  …"); `care_plan_tag` from the enum.
- `required_document_evidence`: `echo` with the real document_id/type/date/status; `office_note_received`
  true when the referral lists it (an office visit encounter stands in for the note even if no separate
  document object exists).
- `receiving_provider`: from the provider directory (`receiving_provider_id`).
- `authorization_readiness`: status/urgency/referral_status from the referral; `overall_readiness` and
  `readiness_choice` reflect the binding hold (allergy clarification > missing doc > authorization > code).
- `medication_highlights`: only the referral-relevant meds with the matching `highlight_reason`; the
  `medication_summary_choice` names exactly those.
- `referral_letter_fields`: each `*_choice` picks the enum that matches the documented evidence.

## Care-transition packet (e.g. orthopedic surgery)
- `patient` (id, mrn, display_name, dob), `recipient` (provider_id, name, facility, service_line).
- `active_condition_keys` / `active_medication_keys` / `active_allergy_keys`: endpoint active unions, sorted.
- `handoff_encounters`: 4 most-recent **relevant** encounters (exclude opposite-laterality/unrelated and
  stale), newest→oldest; each with id/date/type/signed_status.
- `source_selection`: selected ids newest→oldest; excluded ids sorted ascending.
- `latest_immunization`: the immunization with the max date.
- `disclosure`: the one matching the recipient (purpose/surgical handoff, recipient_provider_id, status).
- `risk_flags`: only from the allowed enum; derive each from condition/med/encounter evidence in
  `risk_flag_evidence` (sorted by flag; empty arrays when evidence type doesn't apply).
- `packet_readiness`: `ready_with_risk_flags`, `ready_to_send: true`, `blocking_issue_codes: []` when
  structurally complete (risk flags are not blockers).

## Duplicate-review + ServiceRequest validation
- `duplicate_review`: `candidate_id`, `primary_patient_id` (active), `possible_duplicate_patient_id`
  (possible_duplicate), `match_signals`/`conflict_signals` verbatim, `merge_target/source_patient_id`
  (null when not merging or on hold).
- `candidate_status` / `decision`: confirmed+benign → `confirmed_duplicate`/`merge`; ambiguous (serious
  conflicts + strong matches) → `needs_review`/`review_hold`; clearly different → `not_duplicate`/`do_not_merge`.
- `service_request`: every field copied from the ServiceRequest (status, intent, priority, service_code,
  requester/performer ids, authored_on, occurrence_date, reason_codes). `service_code_valid` from the
  service-code directory (`active: true`). `performer_service_line` from the provider or service-code.
- `reason_code_validation`: one entry per reason code, sorted by code, with `valid`, `chapter` (from ICD-10
  lookup), `matches_patient_evidence` (true when the code appears in the patient's conditions or encounters).
- `sbar_coverage`: `complete` true iff all four sections (situation/background/assessment/recommendation)
  are present and non-empty.

## Batch referral audit
- `batch`: id, service_line, requested_date (the shared referral date), record_count, unique_patient_count.
- `invalid_or_out_of_range_code_referrals`: codes whose ICD-10 chapter ≠ expected (strict — Injury and
  Respiratory chapters are out of range for a Musculoskeletal batch); `issue_type: out_of_range_chapter`
  (or `unknown_code` if the code isn't in the directory). `actual_chapter` from lookup.
- `laterality_or_narrative_mismatch_referrals`: only **in-range** codes whose narrative fails the simple
  expected-term / laterality check; `mismatch_types` from the enum; `expected_terms` from lookup.
- `duplicate_groups`: same patient, multiple referrals → `same_patient_resubmission` /
  `consolidate_under_original`.
- `duplicate_tiering_policy`: scope = `tier_all_duplicate_group_rows_as_duplicate_blockers`; list the group's
  referral ids; `separate_same_patient_referral_ids` for same-patient referrals that are distinct clinical
  reviews.
- `insurance_patient_anomalies`: shared insurance across different patients →
  `shared_insurance_different_patients` / `verify_insurance_membership_do_not_merge`; same patient with
  distinct clinical referrals → `same_patient_separate_clinical_referrals` /
  `separate_clinical_review_not_duplicate`.
- `follow_up_queues`: authorization_missing / authorization_pending / records_request (no office_note) /
  imaging_follow_up (no mri and no xray); each sorted ascending.
- `action_plan`: Tier 1 urgent + duplicate blockers; Tier 2 routine coding/auth; Tier 3 administrative
  document completion. `owner_provider_id` = receiving provider.
- `summary_counts`: every count derived from the lists above; `validated_ready_no_follow_up_count` =
  referrals in no issue list.
