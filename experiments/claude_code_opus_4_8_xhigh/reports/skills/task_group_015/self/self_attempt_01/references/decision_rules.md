# Reusable decision rules

These rules are derived from the recurring structure of EHR quality-governance packet
and audit tasks. Apply the ones the answer template asks for; the template's key names
and enum lists are always the final contract — when a rule and the template disagree,
follow the template.

## R0. Universal record filters
- **Active only.** When a field asks for "active" conditions/medications/allergies,
  include only records with `status == "active"`. Exclude `inactive`,
  `entered-in-error`, `resolved`, `unknown`, etc.
- **`normalized_key` is the union/dedup key.** Emit the record's `normalized_key`
  verbatim; do not derive keys from the display name/allergen. De-duplicate by
  `normalized_key`, then sort ascending unless the template says otherwise.
  - Caveat: some active records carry a **generic placeholder** key such as
    `baseline_med` or `baseline_allergy` (seeded noise). Emit them as returned for the
    literal "normalized_key values from active records" fields, but re-check the exact
    template wording and any "excluded_distractors"/"non-merge" bucket — a template may
    intend these to be dropped or routed to a distractor list.
- **Final documents only.** For document evidence, require `status == "final"` (exclude
  `preliminary`, `cancelled`, `missing`).
- **Sets vs. ordered lists.** Arrays described as sets → sort ascending (alphabetical /
  by id / by code) and dedupe. Some lists have explicit non-alphabetical order (e.g.
  encounters newest→oldest, "referral-relevant first") — follow the stated ordering.
- **Dates** are `YYYY-MM-DD`. **task_id** = the train folder id when the template
  requires it (e.g. `train_00X`).
- **Output is JSON only** — no prose, SOP text, procedural notes, or narrative outside
  the object. Include exactly the template's top-level keys.

## R1. Duplicate / merge decisions
1. **Canonical target vs source.** Prefer the environment's explicit pointers, which
   corroborate each other:
   - The `duplicate` record's `canonical_patient_id` points at the target; the record
     whose `canonical_status == "active"` (and `canonical_patient_id == null`) is the
     **target**, the `duplicate` record is the **source**.
   - `merge_preview.preferred_target_patient_id` / `source_patient_id` should agree.
   - If both pointers are `null`/absent and status is not confirmed, emit `null` for
     merge target/source and route to review.
2. **Status → decision.** Map `candidate.status` to the template's `candidate_status`
   enum (`open`→typically `confirmed_duplicate` when signals are clean;
   `needs_review`→`needs_review`). Choose the disposition/decision enum from signal
   strength:
   - Strong matches, only cosmetic conflicts (e.g. `address_abbreviation`,
     `name_variant`, `suffix_discrepancy`) ⇒ ready/merge (some templates add a
     "with_conflict_review" variant when any conflict exists).
   - **Hard conflicts** — `opposite_laterality_problem`, `different_given_name`,
     `different_phone`, `different_dob`, `different_insurance` — ⇒ hold / do-not-merge
     and set `manual_review_required = true`. Opposite-laterality problems mean
     clinically distinct entities: do **not** merge.
3. **Match / conflict signals.** Copy the candidate's `match_signals` and
   `conflict_signals` into the template's signal arrays (sorted). For separate
   `demographic_matches` / `demographic_conflicts` fields, compare the two patient
   detail records field-by-field and classify each field:
   - match: identical `dob`, `insurance_id`, `phone`, `family_name`, `sex`, normalized
     `address`.
   - conflict: differing `given_name`/`display_name` (name variant), abbreviated vs
     spelled-out `address`, differing `phone`, etc.
4. **Active-list reconciliation** (`patient_active_list_endpoints_over_duplicate_preview`).
   Build the active-key **union across both patients** from the live
   conditions/medications/allergies endpoints. The
   `*_added_from_active_endpoints` fields = keys in that live union that are **absent
   from** `merge_preview.active_*_keys`. Inactive/`non-merge` keys go to
   `excluded_distractors`.

## R2. Evidence selection (documents & audit logs)
- **Document policy** (`identity_or_external_continuity_documents_only`): keep only
  documents whose `type` denotes identity or external clinical continuity — e.g.
  `identity_verification`, `external_cardiology_note` (external specialty note). Exclude
  routine `chart_summary`/`ehr_export` documents (list them under
  `excluded_document_types`). Require `status:final`.
- **Audit scope.** `/api/audit-logs` is global. Keep only logs whose `patient_id` is in
  the case's patient set **and** whose `event`/`summary` concern this candidate/merge
  (e.g. `identity_review`, `external_import` for these patients). Logs about other
  patients or unrelated merges are distractors → `excluded_distractors.audit_ids`.

## R3. ICD-10 code validation
For a `diagnosis_code`/reason `code`, GET `/api/icd10/{code}`:
- **unknown_code / invalid** — 404.
- **out_of_range_chapter** — `chapter` is outside the case's expected clinical
  chapter(s). Expected chapter comes from the template enum / service line (orthopedics
  ⇒ template pins `expected_chapter: "Musculoskeletal"`; cardiology ⇒ `Circulatory`;
  pulmonology ⇒ `Respiratory`; etc.). Report `actual_chapter` from the lookup.
  Reconcile borderline trauma codes (`S…` = `Injury` chapter, used for knee
  sprain/meniscus) against the template's allowed enum before finalizing.
- **narrative_match** — true iff the referral/encounter `diagnosis_narrative` matches
  one of `expected_terms` (case-insensitive substring/term overlap). Otherwise
  `narrative_mismatch` / `valid_but_narrative_mismatch`.
- **laterality** — if `requires_laterality` and the narrative names a side (left/right)
  opposite to the code's `expected_terms` side ⇒ `laterality_mismatch`; a laterality
  code with no side in the narrative ⇒ `missing_laterality`.
- `matches_patient_evidence` — true iff the code (or its `normalized_key`) appears among
  the patient's active conditions.
- For a referral **code set**: `primary_code` = the referral's own diagnosis code (when
  valid & on-narrative); `supporting_codes` = related active-condition codes.

## R4. Service-request quality signals
- Copy `status, intent, priority, service_code, requester_id→requester_provider_id,
  performer_id→performer_provider_id, authored_on, occurrence_date, reason_codes`.
- `service_code_valid` — code exists, `active:true`, `service_line` matches performer.
- `performer_service_line` — from the performer provider's directory `service_line`.
- `reason_code_validation` — one object per reason code (R3), sorted by code.
- **SBAR coverage** — `sections_present` = the `sbar` keys with non-empty text among
  {situation, background, assessment, recommendation}; `missing_sections` = the rest;
  `complete` = all four present.

## R5. Provider / recipient resolution
- **Recipient / receiving / specialist provider**: resolve from the case's target
  service line via the provider directory, or directly from `receiving_provider_id`
  (referral) / `performer_id` (service request) / the specialty implied by an external
  continuity document. Emit full contact block (`provider_id, name, role, service_line,
  facility, phone, fax`).
- **Primary care provider**: from patient detail `primary_care_provider`.

## R6. Care-transition / handoff encounter selection
- Choose the N encounters (N is fixed by the template, e.g. 4) most relevant to the
  recipient's service line and most recent. Prefer `signed`/`amended` handoff-type
  encounters (`care_transition`, relevant `office_visit`) whose `diagnoses` /
  `care_plan_notes` relate to the transition.
- Exclude stale, out-of-window, or off-topic encounters (unrelated diagnosis codes,
  decoy narratives) → record their ids in `excluded_encounter_ids` (sorted). Selected
  ids go newest→oldest. Set `selection_basis` to the normalized rule code the template
  expects.
- **latest_immunization** = the immunization with the max `date`.
- **disclosure** = the disclosure whose `recipient_provider_id` matches the packet
  recipient (and `status == "permitted"` to be send-ready).

## R7. Risk flags (care-transition packets)
Derive from active clinical data + encounter `care_plan_notes`, then attach evidence
ids. Typical controlled mapping:

| risk_flag | evidence |
|---|---|
| `cognitive_memory_loss` | active condition `memory_loss` (R41.3) |
| `hypertension` | active condition `hypertension` (I10) |
| `insulin_dependent_diabetes` | active `diabetes_type_2` (E11.9) **and** an insulin medication (e.g. `insulin_glargine`) |
| `latex_allergy` | active latex allergy |
| `fall_risk_note_required` | encounter `care_plan_notes` mentioning a fall-risk note requirement |
| `perioperative_glucose_plan_needed` | encounter `care_plan_notes` mentioning a peri-op glucose plan |

Only emit flags in the template's `allowed_values`. `risk_flag_evidence` lists the
supporting `condition_keys` / `medication_keys` / `encounter_ids` per flag (each sorted).

## R8. Referral batch audit (batch-level tasks)
1. **Scope** = all referrals whose `batch_id` matches; `record_count` = rows,
   `unique_patient_count` = distinct `patient_id`.
2. **Invalid / out-of-range codes** — per R3 (`out_of_range_chapter` | `unknown_code`).
3. **Laterality / narrative mismatches** — per R3; `mismatch_types` may combine
   `laterality_mismatch` + `narrative_mismatch` + `missing_laterality`; carry
   `expected_terms` from the ICD lookup.
4. **Duplicate groups** — group referrals by `patient_id`; a repeated
   same-patient referral for the same clinical problem (often flagged in
   `coordination_note`, e.g. "duplicate resubmission", or `-DUP` id suffix) ⇒
   `same_patient_resubmission`, `recommended_disposition: consolidate_under_original`.
   A same patient with a **genuinely different** clinical problem is *not* a duplicate —
   route to `separate_same_patient_referral_ids` / a
   `same_patient_separate_clinical_referrals` anomaly.
5. **Insurance/patient anomalies** — group batch patients by `insurance_id`; the same
   `insurance_id` across **different** patients ⇒ `shared_insurance_different_patients`,
   `verify_insurance_membership_do_not_merge`.
6. **Follow-up queues** (each a referral_id list, sorted): `authorization_missing`
   (`authorization_status == missing`), `authorization_pending` (`== pending`),
   `records_request` (missing `office_note` in `documents_received`), `imaging_follow_up`
   (missing/pending imaging: `mri`/`xray`/`echocardiogram`/`chest_xray` as the service
   line requires).
7. **Tiering / action plan**:
   - **Tier 1 (immediate)** — urgent coding errors or duplicate blockers
     (`urgent_coding_or_duplicate_blocker`).
   - **Tier 2 (short-term)** — routine coding/auth/document blockers.
   - **Tier 3 (administrative)** — administrative document completion only.
   - `owner_provider_id` = the referral's `receiving_provider_id` (or template-specified
     owner).
8. **summary_counts** — compute every count the template lists directly from the arrays
   you built (invalid, mismatch, duplicate groups, anomalies, each queue, each tier,
   urgent vs routine, and `validated_ready_no_follow_up_count` = rows with no flag/queue
   membership). Make counts internally consistent with the arrays.

## R9. Readiness / blocking classification
Set the readiness enum (`ready` / `ready_with_review_note` / `blocked`, or the
referral-letter variants) from whether any blocker holds: missing required document,
missing/pending authorization, incomplete allergy documentation, unresolved code issue,
unresolved identity conflict, missing provider. Populate `blocking_issue(s)` /
`required_review_notes` from the template's controlled code list, and set the boolean
`ready_to_send` accordingly. A conflict that only needs a review note ⇒ the
"…_with_review"/"ready_with_review_note" middle state, not full block.

## Distractor awareness (recurring decoys)
- Inactive / `entered-in-error` clinical records with real-looking keys.
- `chart_summary` / `ehr_export` documents (never packet evidence).
- Audit logs and referrals belonging to **other** patients/batches in the global lists.
- Encounters whose `diagnoses`/narrative don't match the true clinical thread
  (e.g. an oncology or lung code injected into an orthopedic patient's history).
- Generic placeholder `normalized_key`s (`baseline_med`, `baseline_allergy`).
- Third, unrelated duplicate candidates in `/api/duplicates/candidates`.
Always confirm every id you emit is tied to the specific case entities in the prompt.
