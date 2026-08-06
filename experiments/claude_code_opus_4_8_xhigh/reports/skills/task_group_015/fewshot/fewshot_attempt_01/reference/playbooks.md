# Task-family playbooks

Pick the family from the template's top-level keys (SKILL.md §0). Each recipe
maps template sections to endpoints + rules. The template is authoritative for
field names/enums/ordering; if a template key here doesn't exist in your run,
skip it, and if your template has a key not listed here, populate it by the same
evidence-driven logic. Never copy an ID/value across runs — re-derive everything.

---

## A. Duplicate-chart merge-readiness packet
*Signals: `merge`, `merge_decision`, `clinical_unions`, `active_key_unions`,
`identity_signals`, `packet_contact`.*

1. **Candidate**: `GET /api/duplicates/{candidate_id}` → status, patient_ids,
   match/conflict signals, merge_preview.
2. **Patients**: `GET /api/patients/{id}` for both. Confirm merge direction: the
   source has `canonical_status == "duplicate"` and `canonical_patient_id ==`
   target; target has `canonical_status == "active"`. Target = preferred target /
   canonical; source = the duplicate shell.
3. **Disposition**: open candidate + strong identity match + source already
   points at target ⇒ merge-ready (`manual_review_required = false`).
   `needs_review` candidate / null preferred target / unresolved conflicts ⇒
   manual-review hold with **null** merge target & source. Emit whichever exact
   enum strings the template lists for each disposition field; build
   `reason_codes` from the observed drivers (active/open candidate, duplicate
   record already points to target, strong identity match, …), sorted.
4. **Active key unions**: union the `status=="active"` `normalized_key`s across
   **both** patients' conditions/medications/allergies, de-duped, sorted. Fill
   both `clinical_unions` and `active_key_unions` if the template has both.
   Inactive keys → `excluded_distractors`.
5. **Reconciliation**: `*_added_from_active_endpoints` = active-endpoint keys not
   present in the candidate `merge_preview`. `authoritative_source` = the
   template's fixed "patient endpoints over preview" enum.
6. **Identity signals**: `match_signals`/`conflict_signals` = candidate's signal
   lists (sorted). `demographic_matches`/`demographic_conflicts` = compare the two
   patient records field-by-field (dob, insurance_id, phone, sex,
   primary_care_provider_id, given_name, address); equal fields → matches,
   differing → conflicts (e.g. address_abbreviation, given_name_variant).
7. **Evidence**: `GET /api/patients/{id}/documents` for both — keep only identity /
   external-continuity docs with `status=="final"` (identity_verification,
   external specialty notes); routine chart_summary/ehr_export → distractors +
   `excluded_document_types`. `GET /api/audit-logs`, keep entries for the case
   patients/identity events → `audit_ids`; unrelated ones → distractors.
8. **Contact**: specialist = provider tied to the external-continuity document /
   case service line (`GET /api/providers/{id}` for the full block, incl.
   `contact_reason`). PCP = patient `primary_care_provider`.
9. **Readiness**: ready when disposition is merge-ready and no blockers; otherwise
   `ready_with_review_note` / `blocked` with sorted note codes. Set the required
   constant `task_id` if the template demands one.

---

## B. Referral coordination packet
*Signals: `referral_code_set`, `allergy_readiness`, `referral_letter_fields`.*

1. **Referral**: `GET /api/referrals/{id}` → patient, batch_id, service_line,
   requested_date, diagnosis_code/narrative, receiving_provider_id,
   authorization_status, status, urgency, documents_received, coordination_note.
   Fill `patient_referral`.
2. **Active diagnoses**: patient conditions (active) + any referral-intake
   diagnosis; each `{code, description, normalized_key, source, referral_relevant}`.
   `referral_relevant = true` for the diagnoses that justify *this* specialty
   referral (e.g. the cardiac/dyspnea codes for a cardiology letter), false for
   incidental comorbidities.
3. **Code set**: `primary_code` = the referral's driving diagnosis;
   `supporting_codes` = other relevant codes. Validate each via `/api/icd10/{code}`
   → set `primary_code_chapter`, `narrative_match`, and the `icd_validation` enum
   (valid+match / valid-but-narrative-mismatch / invalid / wrong-chapter).
4. **Allergy readiness**: patient allergies (+ referral-form allergy). Map each to
   `{allergen, reaction, severity, status, source}`; set `readiness_status`,
   `ready_for_letter`, `follow_up_needed` (a coordination note asking to confirm
   an allergy ⇒ clarification needed unless the record is already complete).
5. **Recent encounter evidence**: choose the encounter that supports the referral
   (matching diagnoses/meds, signed) → id, date, type, provider_id, signed_status,
   diagnosis_codes, medications_mentioned, `care_plan_tag`.
6. **Required documents**: from `documents_received` — e.g. echo received? office
   note received? `missing_required_documents` from the template's enum.
7. **Receiving provider**: `GET /api/providers/{receiving_provider_id}`.
8. **Authorization readiness**: map `authorization_status`, `status`, `urgency`;
   `overall_readiness` = ready only when authorized + required docs present + no
   clinical mismatch; else the matching hold enum with `blocking_issues`.
9. **Medication highlights**: active meds relevant to the specialty first, each
   with a `highlight_reason` enum.
10. **`referral_letter_fields`**: for each choice field, pick the single enum
    option consistent with the evidence you assembled above. These enums are
    task-specific — read them from the template and match, do not guess.

---

## C. Care-transition handoff packet
*Signals: `handoff_encounters`, `risk_flags`, `risk_flag_evidence`, `disclosure`,
`latest_immunization`.*

1. **Patient / recipient**: patient detail; recipient provider via `/api/providers`
   (service_line should match the transition, e.g. orthopedics).
2. **Active key sets**: active condition/medication/allergy `normalized_key`s,
   sorted.
3. **Handoff encounters**: from patient encounters, select the N (template says
   how many, e.g. 4) most **relevant** to the target-specialty handoff — prefer
   sequential case encounters and those whose type/`care_plan_notes` concern the
   transition; **exclude** stale, out-of-window, unrelated, or hash-ID
   distractors even if they are more recent. Order newest→oldest. Record the
   selection rule in `source_selection.selection_basis`, list selected ids
   (newest→oldest) and excluded ids (sorted).
4. **Latest immunization**: max-date immunization.
5. **Disclosure**: the disclosure whose `recipient_provider_id`/`purpose` matches
   the transition; include status (must be `permitted` to be non-blocking).
6. **Risk flags**: derive from active conditions/meds/allergies + encounter notes,
   restricted to the template's `allowed_values`. Typical derivations: insulin med
   ⇒ insulin-dependent-diabetes (+ perioperative-glucose-plan for a surgical
   handoff); latex allergy ⇒ latex-allergy; a memory/cognitive condition ⇒
   cognitive-memory-loss; hypertension condition ⇒ hypertension; surgical handoff
   with weight-bearing OA / a fall-risk note ⇒ fall-risk-note-required. Sort.
7. **`risk_flag_evidence`**: for each flag, cite the exact
   condition_keys/medication_keys/encounter_ids that justify it (each sorted).
8. **Readiness**: `ready`/`ready_with_risk_flags`/`not_ready` + `ready_to_send` +
   `blocking_issue_codes` (missing patient/recipient/lists/encounters/immunization/
   disclosure, or disclosure_not_permitted).

---

## D. Duplicate + ServiceRequest quality review
*Signals: `duplicate_review`, `service_request`, `sbar_coverage`.*

1. **Duplicate review**: as in Playbook A steps 1–2, but output the review shape:
   `candidate_status` (confirmed_duplicate / needs_review / not_duplicate — from
   candidate `status` + patient canonical fields), `decision`
   (merge / review_hold / do_not_merge), primary & possible-duplicate patient ids
   (from the prompt), and merge target/source (**null** unless a confirmed merge
   direction exists). `match_signals`/`conflict_signals` mapped to the template
   enums (sets).
2. **ServiceRequest**: `GET /api/patients/{patient}/service-requests`, select the
   named `SR-…`. Map status/intent/priority/service_code/authored_on/
   occurrence_date/reason_codes; `requester_id`→`requester_provider_id`,
   `performer_id`→`performer_provider_id`. `performer_service_line` from the
   performer's provider record.
3. **`service_code_valid`**: `/api/service-codes/{code}` exists and `active`.
4. **`reason_code_validation`**: per reason code → `/api/icd10/{code}` for `valid`
   (404⇒false) and `chapter`; `matches_patient_evidence` = the code (or its
   normalized_key) appears in the patient's conditions/encounters. Sort by code.
5. **`sbar_coverage`**: from the SR's `sbar` object — `sections_present` = the
   non-empty sections among {situation, background, assessment, recommendation};
   `missing_sections` = the rest; `complete` = nothing missing.
6. Set the required constant `task_id`. Omit narrative/SOP text entirely.

---

## E. Referral-batch audit
*Signals: `invalid_or_out_of_range_code_referrals`, `laterality_or_narrative_mismatch_referrals`,
`duplicate_groups`, `follow_up_queues`, `action_plan`, `summary_counts`.*

1. **Batch rows**: `GET /api/referrals`, filter locally to the batch id. Compute
   `record_count` (rows) and `unique_patient_count` (distinct patient_id).
2. **Invalid / out-of-range codes**: `/api/icd10/{diagnosis_code}` per row. 404 ⇒
   `unknown_code`; chapter ≠ the service line's expected chapter (orthopedics ⇒
   Musculoskeletal) ⇒ `out_of_range_chapter`. Emit actual vs expected chapter.
3. **Laterality / narrative mismatches**: compare each row's `diagnosis_narrative`
   to the code's `expected_terms`/laterality (definitions in api_reference.md):
   collect `laterality_mismatch` / `narrative_mismatch` / `missing_laterality`,
   plus `expected_terms` from the directory.
4. **Duplicate groups**: same-patient resubmissions within the batch →
   `duplicate_groups` (referral_ids sorted) + the template's tiering-policy fields
   (duplicate-blocker ids vs separate same-patient clinical reviews).
5. **Insurance/patient anomalies**: cross-check `/api/patients` — different
   patients sharing an `insurance_id` (verify-do-not-merge) vs one patient with
   separate clinical referrals; ids sorted.
6. **Follow-up queues** (all id-lists sorted):
   - `authorization_missing` = `authorization_status == "missing"`
   - `authorization_pending` = `authorization_status == "pending"`
   - `records_request` = rows lacking `office_note` in `documents_received`
   - `imaging_follow_up` = rows whose required imaging study for the diagnosis is
     missing or pending. This one is subtle — derive it, then reconcile against
     `summary_counts.imaging_follow_up_count` and the tier assignments; do not
     hard-code.
7. **Action plan**: Tier 1 = urgent-coding / duplicate-blocker rows; Tier 2 =
   routine coding/auth/document blockers; Tier 3 = purely administrative
   document completion. `owner_provider_id` = the row's receiving provider. Use
   the exact tier/reason enums from the template.
8. **`summary_counts`**: recompute **every** count from your own arrays
   (rows, unique patients, urgent/routine, invalid, mismatch, duplicate groups,
   anomalies, each queue, each tier, and the validated-ready-no-follow-up
   remainder) and make them internally consistent.
