# Operating Rules

Detailed rules that turn fetched evidence into a template-conformant JSON object. Grouped by
concern. These are reusable methods — never hard-code a task's final values.

## 1. Normalization

- **Canonical key = `normalized_key`.** For conditions, medications, and allergies, use the
  record's `normalized_key` field as the join/union/evidence key. Do not key on display name,
  code, or allergen text (those vary across sources/duplicates).
- **Active filter.** "Active" lists include only records with `status == "active"`. Everything
  else (`inactive`, `entered-in-error`, `draft`, `unknown`) is excluded material — route it to
  `excluded_distractors` / `excluded_*_keys` where the template asks.
- **Dedup.** Union two patients' active keys into a sorted set of unique `normalized_key` values.
- **Dates.** Parse `YYYY-MM-DD` for ordering ("recent", "latest", "newest to oldest") and for
  window/recency decisions.
- **Set semantics.** Where the template marks `set_semantics: true`, the evaluator normalizes
  order — but sort the array anyway per the ordering rule so it is stable and reviewable.

## 2. Source reconciliation (merge-readiness archetype)

When a clinical list exists in two places, the patient active-list endpoints win:

- **Authoritative source** = the patient active-list endpoints
  (`/api/patients/{id}/conditions|medications|allergies`), **not** the duplicate candidate's
  `merge_preview`.
- Compute the **union** of active `normalized_key` values across both patients from the active
  endpoints.
- Reconcile against `merge_preview.active_*_keys`: report the keys present in the active endpoints
  but **missing from the preview** (the `*_keys_added_from_active_endpoints` fields). This proves
  the preview was incomplete and the active endpoints were used as the basis.
- **Target/source**: `merge_target_patient_id` = `merge_preview.preferred_target_patient_id`;
  `merge_source_patient_id` = `merge_preview.source_patient_id`. (Null both when the decision is
  do-not-merge, where the template allows null.)

## 3. Merge / identity disposition

Weigh match signals against conflict signals:

- **Ready to merge** ( disposition `ready_to_merge` / `merge_ready`): strong identity match
  (`same_dob`, `same_insurance`, `same_phone`) and no serious conflict. Minor conflicts
  (`address_abbreviation`, `suffix_discrepancy`, `name_variant`) ⇒
  `merge_ready_with_conflict_review` with a review note code.
- **Needs manual review** (`needs_review` / `needs_manual_review`): candidate `status ==
  needs_review`, or match and conflict signals are balanced / ambiguous.
- **Do not merge** (`do_not_merge`): a serious identity conflict is present
  (`different_dob`, `different_insurance`, `opposite_laterality_problem`).
- Emit `reason_codes` / `canonical_reason_codes` as sorted controlled labels describing the
  decision basis (e.g. the signals that drove it). Constrain to the template's vocabulary; map raw
  API signals onto it (see `environment_contract.md`).
- `manual_review_required` is true unless the disposition is an unqualified ready-to-merge.

## 4. ICD-10 code validation

For a diagnosis/referral/reason code, fetch `/api/icd10/{code}`:

- **Not found** ⇒ `invalid_code` / `unknown_code` (issue type `unknown_code`).
- **Found, chapter ≠ expected chapter** for the service line (see the map in
  `environment_contract.md`) ⇒ `wrong_service_chapter` / `out_of_range_chapter`
  (issue type `out_of_range_chapter`, with `actual_chapter` and `expected_chapter`).
- **Found, chapter ok**:
  - `requires_laterality == true` and the narrative lacks the side term ⇒ `missing_laterality`.
  - Narrative side conflicts with the code's side (e.g. code is right-sided, narrative says left)
    ⇒ `opposite_laterality_problem`.
  - Narrative contains none of `expected_terms` (case-insensitive substring) ⇒ `narrative_mismatch`.
  - Otherwise `valid_matches_narrative` (referral code set) / valid.
- `narrative_match` is true iff the narrative contains at least one `expected_terms` substring
  (and, when laterality is required, the correct side).
- `matches_patient_evidence` (service-request reason codes): true iff the patient has an **active**
  condition with that code.

`referral_code_set.icd_validation` enum: `valid_matches_narrative` | `valid_but_narrative_mismatch`
| `invalid_code` | `wrong_service_chapter`.

## 5. Service-code validation

`service_code_valid` is true iff **all** hold: the code exists in `/api/service-codes`, its
`active` flag is true, and its `service_line` matches the service request's performer service line
(derive `performer_service_line` from `/api/providers/{performer_id}`).

## 6. Service-request quality (duplicate-review + SR archetype)

- Map API field names to template names: `requester_id` → `requester_provider_id`,
  `performer_id` → `performer_provider_id`. `performer_service_line` comes from the provider
  directory, not the SR.
- `reason_code_validation`: one entry per `reason_codes` code, sorted by code, with `code`,
  `valid` (ICD-10 exists), `chapter` (from ICD-10, or empty/null if invalid), and
  `matches_patient_evidence` (active condition with that code exists).
- `sbar_coverage`: inspect the SR's `sbar` object. `sections_present` = the keys among
  `situation`/`background`/`assessment`/`recommendation` that are present and non-empty;
  `missing_sections` = the rest; `complete` = all four present.

## 7. Referral coordination readiness

- **Required documents** depend on service line: cardiology ⇒ `echocardiogram` + `office_note`;
  orthopedics ⇒ imaging (`mri`/`chest_xray` as relevant) + `office_note`. Cross-check the
  referral's `documents_received` and the patient's `documents` (by `type` and `status == final`).
  Report `received` booleans, `document_id` (or null), and `missing_required_documents`.
- **Allergy readiness**: empty active allergy list ⇒ `no_known_allergies`; full active records ⇒
  `complete_documented`; missing reaction/severity ⇒ `incomplete_needs_clarification`;
  same allergen with disagreeing severity/status ⇒ `conflicting_allergy_records`.
- **Authorization readiness**: `overall_readiness` =
  - `hold_for_authorization` if `authorization_status` is `missing`/`pending`,
  - `hold_for_missing_documents` if a required document is missing,
  - `hold_for_clinical_clarification` if allergy/code issues are unresolved,
  - `ready_to_send` if none of the above.
  Populate `blocking_issues` from its enum (`authorization_missing`, `echo_missing`,
  `office_note_missing`, `allergy_incomplete`, `provider_missing`, `diagnosis_code_invalid`,
  `clinical_mismatch`).
- **Medication highlights**: include active meds, flag `highlight_reason` by drug class
  (`heart_failure_diuretic`, `blood_pressure_management`, `diabetes_management`, `lipid_management`,
  `other_active_medication`). Put referral-relevant meds first.
- **Receiving provider**: resolve from `/api/providers/{receiving_provider_id}`.
- **Referral-letter `*_choice` enums**: pick the single value that matches the reconciled evidence
  (diagnosis summary, allergy statement, recent encounter, document packet, med summary, recipient,
  authorization statement, readiness). These are forced choices — exactly one each.

## 8. Care-transition handoff (archetype)

- **Handoff encounter selection**: from the patient's encounters, select the four most relevant to
  the transition (e.g., orthopedic surgery). Relevance = encounter `type`/`diagnoses`/`care_plan`
  tied to the service line and within the transition window. Sort selected newest-to-oldest by
  date. Record the selection rule as a normalized `selection_basis` code. Exclude stale,
  out-of-window, and unrelated encounters into `excluded_encounter_ids` (sorted ascending).
- **Latest immunization**: the immunization with the greatest `date`.
- **Disclosure**: the disclosure whose `recipient_provider_id` matches the recipient provider.
  Packet is blocked if its `status != permitted` (`disclosure_not_permitted`).
- **Risk flags**: derive only from the template's allowed set; emit a flag only when active
  condition/medication/allergy/encounter evidence supports it, and cite that evidence in
  `risk_flag_evidence` (condition_keys / medication_keys / encounter_ids, each sorted). Typical
  derivations:
  - `insulin_dependent_diabetes` / `perioperative_glucose_plan_needed` ⇐ diabetes condition +
    insulin-class medication.
  - `hypertension` ⇐ hypertension condition.
  - `latex_allergy` ⇐ latex allergy.
  - `cognitive_memory_loss` ⇐ memory-loss/cognitive condition or care-plan note.
  - `fall_risk_note_required` ⇐ fall-risk signal in encounter `care_plan_notes`.
- **Packet readiness**: `ready` only if patient, recipient, active lists, ≥1 handoff encounter,
  immunization, and a permitted disclosure are all present and disclosure is permitted; otherwise
  emit the matching `blocking_issue_codes` (`missing_patient`, `missing_recipient`,
  `missing_active_lists`, `missing_handoff_encounters`, `missing_immunization`,
  `missing_disclosure`, `disclosure_not_permitted`).

## 9. Referral batch audit (archetype)

- **Batch**: filter `/api/referrals` by `batch_id`. `record_count` = rows in batch;
  `unique_patient_count` = distinct `patient_id`.
- **Invalid / out-of-range code referrals**: per referral, validate `diagnosis_code` against
  ICD-10 (§4). Emit `{referral_id, patient_id, diagnosis_code, actual_chapter, expected_chapter,
  issue_type}` for `out_of_range_chapter` or `unknown_code`.
- **Laterality / narrative mismatch referrals**: for codes that are otherwise in-chapter, emit
  `{referral_id, patient_id, diagnosis_code, diagnosis_narrative, mismatch_types, expected_terms}`
  where `mismatch_types` ⊆ {`laterality_mismatch`, `narrative_mismatch`, `missing_laterality`} and
  `expected_terms` come from the ICD-10 entry.
- **Duplicate groups**: same `patient_id` resubmitted (multiple referrals in the batch for the same
  patient for the same clinical problem) ⇒ one group, `duplicate_type =
  same_patient_resubmission`, `recommended_disposition = consolidate_under_original`,
  `referral_ids` sorted ascending. Sort groups by `group_id`.
- **Duplicate tiering policy**: all rows in a duplicate group are Tier-1 duplicate blockers;
  same-patient referrals that are **separate clinical reviews** are not part of the group (list
  them in `separate_same_patient_referral_ids`).
- **Insurance-patient anomalies**:
  - `shared_insurance_different_patients`: distinct patients sharing one `insurance_id` ⇒
    `recommended_disposition = verify_insurance_membership_do_not_merge`.
  - `same_patient_separate_clinical_referrals`: same patient, genuinely different clinical
    problems ⇒ `recommended_disposition = separate_clinical_review_not_duplicate`.
  Sort anomalies by `anomaly_id`; inner `patient_ids`/`referral_ids` ascending.
- **Follow-up queues** (referral_id arrays, sorted ascending): `authorization_missing`
  (`authorization_status == missing`), `authorization_pending` (`== pending`), `records_request`
  (missing `office_note`), `imaging_follow_up` (missing/pending imaging).
- **Action plan** (every audited referral lands in exactly one tier, or is validated-ready):
  - **Tier 1 immediate** — `primary_reason = urgent_coding_or_duplicate_blocker`: urgent/stat
    referrals or duplicate-group blockers.
  - **Tier 2 short-term** — `primary_reason = routine_coding_auth_or_document_blocker`: routine
    referrals with a coding/auth/document blocker.
  - **Tier 3 administrative** — `primary_reason = administrative_document_completion`: routine
    referrals needing only document completion.
  `owner_provider_id` = the referral's `receiving_provider_id` (or the patient's PCP).
- **Summary counts**: every count equals the length of its corresponding list.
  `validated_ready_no_follow_up_count` = batch rows with no blocker, mismatch, duplicate, or
  follow-up. All tier counts and queue counts must reconcile with the lists above.

## 10. Distractor exclusion

Actively exclude — and where the template asks, enumerate — these:

- Inactive / entered-in-error / draft clinical records (not in active unions).
- Stale or out-of-window encounters (not in handoff selection).
- Unrelated documents (e.g. `chart_summary`, routine labs) and unrelated audit logs (events for
  other patients or other purposes) — not in evidence IDs.
- Procedural notes, narrative SOP text, and explanatory prose — never appear in the JSON.
- Same-patient separate-clinical referrals — **not** duplicates.
- For merge packets: documents that are neither identity nor external-continuity documents are
  excluded (`document_selection_policy.packet_document_basis =
  identity_or_external_continuity_documents_only`); enumerate `excluded_document_types`.

## 11. Output discipline

- Return **one** JSON object. No prose, no markdown fences, no comments, no trailing text.
- Emit **every** required top-level key and sub-key from the template, with correct types.
- **Enums**: constrain every enum field to the template's `allowed_values`. Never invent a value.
- **Nulls**: emit `null` only where the template allows it (e.g. `merge_target_patient_id` on
  do-not-merge; `document_id` when a required document is missing).
- **Fixed values**: copy `required_value` fields (e.g. `task_id`) verbatim.
- **Sorting cheat-sheet**:
  - Sets / ID arrays / `*_keys` / `blocking_issue_codes` / `risk_flags`: ascending.
  - `handoff_encounters` and `selected_encounter_ids`: newest to oldest by date.
  - `excluded_encounter_ids`: ascending.
  - `reason_code_validation`: sort by `code`.
  - `duplicate_groups`: by `group_id`; inner `referral_ids` ascending.
  - `insurance_patient_anomalies`: by `anomaly_id`; inner IDs ascending.
  - Referral-object arrays: by `referral_id` ascending.
  - `risk_flag_evidence`: by `risk_flag`.
- **Counts reconcile** with the categorized lists.
- Use **stable IDs** (referral_id, document_id, audit_id, normalized_key) — never narrative
  explanations — as the values inside evidence and exclusion arrays.
